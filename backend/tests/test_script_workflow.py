import copy
import json
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import OpenRouterProvider, ProviderError, ProviderResult
from app.features.script_creation.service import ScriptCreationService
from app.models import (
    AssistantConversation,
    Base,
    LlmCall,
    Project,
    RevisionProposal,
    ScriptVersion,
    StyleProfileSuggestion,
)
from app.repositories import ProjectRepository
from app.schemas import JobStatus, JobType, Platform, ProjectCreate


class FakeProvider:
    def __init__(self, payloads: list[dict[str, Any] | ProviderError]) -> None:
        self.payloads = payloads
        self.calls = 0
        self.requests = []

    def generate_json(self, **kwargs: Any) -> ProviderResult:
        payload = self.payloads[self.calls]
        self.calls += 1
        self.requests.append(kwargs)
        if isinstance(payload, ProviderError):
            raise payload
        return ProviderResult(
            payload=payload,
            actual_model="fake/model:free",
            provider="fake",
            input_tokens=11,
            output_tokens=22,
        )


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)


def create_claimed_generation_job(session: Session):
    project = ProjectRepository(session).create(
        "creator-a",
        ProjectCreate(
            name="Workflow test",
            brief="Explain a useful creator workflow.",
            target_platforms=[Platform.INSTAGRAM],
        ),
    )
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.SCRIPT_GENERATION,
        idempotency_key="workflow-1",
        input_snapshot={"project": {"brief": project.brief}, "request": {}},
        routing_snapshot={**routing_snapshot(), "max_calls": 4},
    )
    claimed = JobRepository(session).claim_next(lease_seconds=30)
    assert claimed is not None and claimed.id == job.id
    return claimed


def routing_snapshot() -> dict[str, Any]:
    return {
        "default_model": "fake/model:free",
        "fallback_models": [],
        "free_only": True,
        "require_structured_output": True,
        "timeout_seconds": 30,
        "max_output_tokens": 512,
        "max_calls": 2,
    }


def valid_script_payload() -> dict[str, Any]:
    return {
        "hooks": [
            {"id": "hook-1", "text": "Your workflow is costing you time."},
            {"id": "hook-2", "text": "Try this creator shortcut."},
            {"id": "hook-3", "text": "Stop doing this manually."},
        ],
        "selected_hook_id": "hook-1",
        "sections": [
            {
                "id": "section-1",
                "position": 1,
                "heading": "The problem",
                "text": "Start with one repeatable process.",
            }
        ],
        "title": "A simpler creator workflow",
        "description": "One practical way to save time.",
        "call_to_action": "Save this for your next planning session.",
        "production_notes": ["Use a direct-to-camera opening."],
    }


def valid_hook_payload() -> dict[str, Any]:
    return {"hooks": valid_script_payload()["hooks"]}


def test_generation_workflow_persists_an_immutable_script_version(session: Session) -> None:
    job = create_claimed_generation_job(session)
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            {"approved": True, "feedback": []},
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    saved = session.scalar(select(ScriptVersion).where(ScriptVersion.job_id == job.id))
    assert provider.calls == 3
    assert job.status == JobStatus.COMPLETED.value
    assert saved is not None
    assert saved.version == 1
    assert saved.content["selected_hook_id"] == "hook-1"
    call = session.scalar(select(LlmCall).where(LlmCall.job_id == job.id))
    assert call is not None
    assert call.actual_model == "fake/model:free"
    assert all(request["routing"]["max_calls"] == 1 for request in provider.requests)
    assert len(list(session.scalars(select(LlmCall).where(LlmCall.job_id == job.id)))) == 3
    assert session.get(Project, job.project_id).workflow_stage == "idea"


def test_new_script_requires_fresh_creator_approval(session):
    job = create_claimed_generation_job(session)
    project = session.get(Project, job.project_id)
    project.workflow_stage = "approved"
    project.workflow_data = {"approved_package": {"title": "Old draft"}}
    session.commit()
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            {"approved": True, "feedback": []},
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "completed"
    assert project.workflow_stage == "editing"
    assert project.workflow_data["review_status"] == "changes_requested"
    assert "approved_package" not in project.workflow_data


def test_rejected_draft_is_revised_once_and_only_final_content_is_saved(session):
    job = create_claimed_generation_job(session)
    original_snapshot = copy.deepcopy(job.input_snapshot)
    revised = valid_script_payload()
    revised["sections"][0]["text"] = "Batch your planning to save time every week."
    feedback = {"approved": False, "feedback": ["Give a concrete planning example."]}
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            feedback,
            revised,
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "completed"
    assert provider.calls == 4
    versions = list(session.scalars(select(ScriptVersion).where(ScriptVersion.job_id == job.id)))
    assert len(versions) == 1
    assert versions[0].content["sections"][0]["text"] == revised["sections"][0]["text"]
    assert versions[0].input_snapshot == original_snapshot == job.input_snapshot
    review_request = json.loads(provider.requests[2]["user_prompt"])
    revision_request = json.loads(provider.requests[3]["user_prompt"])
    assert review_request["snapshot"] == original_snapshot
    assert revision_request["review"] == feedback
    assert [r["schema_name"] for r in provider.requests] == [
        "creator_hooks",
        "creator_script",
        "creator_script_review",
        "creator_script_revision",
    ]
    calls = list(session.scalars(select(LlmCall).where(LlmCall.job_id == job.id)))
    assert len(calls) == 4
    assert sum(c.input_tokens for c in calls) == 44
    assert sum(c.output_tokens for c in calls) == 88
    # A completed version is the existing replay boundary: no further model calls.
    job.status = "running"
    session.commit()
    ScriptCreationService(session, provider).execute_claimed_job(job)
    assert job.status == "completed" and provider.calls == 4
    assert len(list(session.scalars(select(ScriptVersion)))) == 1


def test_deterministic_missing_requirements_override_reviewer_approval(session):
    job = create_claimed_generation_job(session)
    job.input_snapshot = {
        **job.input_snapshot,
        "campaign_brief": {
            "brand_brief": {
                "requirements": [
                    {"id": "brand-name", "kind": "literal", "literal_text": "Acme"},
                    {"id": "tone", "kind": "semantic", "description": "Sound approachable"},
                ],
                "approved_claims": ["Helps organize planning"],
            }
        },
        "style_profile": {
            "profile": {
                "signature_lines": [
                    {
                        "id": "signoff",
                        "text": "Keep creating!",
                        "inclusion_policy": "always",
                        "placement": "closing",
                    }
                ]
            }
        },
    }
    session.commit()
    revised = valid_script_payload()
    revised["sections"][0]["text"] += " Plan with Acme."
    revised["call_to_action"] += " Keep creating!"
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            {"approved": True, "feedback": []},
            revised,
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "completed" and provider.calls == 4
    saved = session.scalar(select(ScriptVersion).where(ScriptVersion.job_id == job.id))
    checks = {c["requirement_id"]: c["status"] for c in saved.requirement_checks}
    assert checks == {
        "brand-name": "satisfied",
        "tone": "needs_review",
        "approved-claims": "needs_review",
        "signature-signoff": "satisfied",
    }
    assert saved.warning_ids == ["tone", "approved-claims"]
    assert any(
        c["status"] == "missing"
        for c in json.loads(provider.requests[3]["user_prompt"])["requirement_checks"]
    )


@pytest.mark.parametrize("violation", ["literal", "signature", "forbidden", "hooks", "sections"])
def test_invalid_revision_fails_without_saving_or_looping(session, violation):
    job = create_claimed_generation_job(session)
    revised = valid_script_payload()
    if violation == "literal":
        job.input_snapshot = {
            **job.input_snapshot,
            "campaign_brief": {
                "brand_brief": {
                    "requirements": [{"id": "brand", "kind": "literal", "literal_text": "Acme"}],
                }
            },
        }
    elif violation == "signature":
        job.input_snapshot = {
            **job.input_snapshot,
            "style_profile": {
                "profile": {
                    "signature_lines": [
                        {
                            "id": "end",
                            "text": "Keep creating!",
                            "inclusion_policy": "always",
                            "placement": "closing",
                        }
                    ],
                }
            },
        }
    elif violation == "forbidden":
        job.input_snapshot = {
            **job.input_snapshot,
            "campaign_brief": {
                "brand_brief": {
                    "forbidden_phrases": ["guaranteed results"],
                }
            },
        }
        revised["sections"][0]["text"] = "Get guaranteed results."
    elif violation == "hooks":
        revised["hooks"][0]["text"] = "An unauthorized hook change."
    else:
        revised["sections"][0]["id"] = "invented-section"
    session.commit()
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            {"approved": False, "feedback": ["Improve the example."]},
            revised,
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "failed" and provider.calls == 4
    assert job.lease_expires_at is None
    assert session.scalar(select(ScriptVersion).where(ScriptVersion.job_id == job.id)) is None
    assert session.get(Project, job.project_id).current_script_version_id is None


@pytest.mark.parametrize(
    "review",
    [
        {"approved": False, "feedback": []},
        {"approved": True},
        {"approved": "false", "feedback": ["Fix the pacing."]},
        {"approved": False, "feedback": [" "]},
        ProviderError("unavailable", "Reviewer timed out", retryable=True),
    ],
)
def test_invalid_or_unavailable_reviewer_fails_without_persisting(session, review):
    job = create_claimed_generation_job(session)
    provider = FakeProvider([valid_hook_payload(), valid_script_payload(), review])

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "failed" and provider.calls == 3
    assert session.scalar(select(ScriptVersion)) is None


def test_revision_provider_failure_is_recorded_and_no_draft_is_saved(session):
    job = create_claimed_generation_job(session)
    provider = FakeProvider(
        [
            valid_hook_payload(),
            valid_script_payload(),
            {"approved": False, "feedback": ["Fix the pacing."]},
            ProviderError("rate_limited", "Try later", retryable=True),
        ]
    )

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "failed" and provider.calls == 4
    assert session.scalar(select(ScriptVersion)) is None
    failed_call = session.scalar(select(LlmCall).where(LlmCall.outcome == "failed"))
    assert failed_call.error_category == "rate_limited"


@pytest.mark.parametrize("budget", [2, 3])
def test_insufficient_script_budget_fails_before_any_provider_call(session, budget):
    job = create_claimed_generation_job(session)
    job.routing_snapshot = {**job.routing_snapshot, "max_calls": budget}
    session.commit()
    provider = FakeProvider([])

    ScriptCreationService(session, provider).execute_claimed_job(job)

    assert job.status == "failed" and provider.calls == 0
    assert "MAX_CALLS_PER_OPERATION >= 4" in job.error
    assert session.scalar(select(ScriptVersion)) is None


def test_invalid_provider_output_fails_the_job_without_saving_a_version(session: Session) -> None:
    job = create_claimed_generation_job(session)

    ScriptCreationService(session, FakeProvider([{"not": "hooks"}])).execute_claimed_job(job)

    assert job.status == JobStatus.FAILED.value
    assert session.scalar(select(ScriptVersion).where(ScriptVersion.job_id == job.id)) is None


def test_revision_workflow_saves_a_pending_scoped_proposal(session: Session) -> None:
    project = ProjectRepository(session).create(
        "creator-a",
        ProjectCreate(
            name="Revision test",
            brief="Make a creator script.",
            target_platforms=[Platform.INSTAGRAM],
        ),
    )
    content = valid_script_payload()
    base = ScriptVersion(
        project_id=project.id,
        version=1,
        origin="generated",
        content=content,
        requirement_checks=[],
        warning_ids=[],
        input_snapshot={},
    )
    conversation = AssistantConversation(owner_id="creator-a", project_id=project.id)
    session.add_all([base, conversation])
    session.flush()
    project.current_script_version_id = base.id
    session.commit()
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.ASSISTANT_REVISION,
        idempotency_key="revision-1",
        input_snapshot={
            "conversation_id": str(conversation.id),
            "base_script": {"id": str(base.id), "version": 1, "content": content},
            "message": {
                "message": "Make it friendlier.",
                "target_scope": "hook",
                "target_id": "hook-1",
            },
        },
        routing_snapshot=routing_snapshot(),
    )
    claimed = JobRepository(session).claim_next(lease_seconds=30)
    assert claimed is not None

    ScriptCreationService(
        session,
        FakeProvider(
            [
                {
                    "explanation": "This feels more conversational.",
                    "changes": [
                        {
                            "target_scope": "hook",
                            "target_id": "hook-1",
                            "before": "Your workflow is costing you time.",
                            "after": "Your workflow might be stealing more time than you think.",
                        }
                    ],
                }
            ]
        ),
    ).execute_claimed_job(claimed)

    proposal = session.scalar(select(RevisionProposal).where(RevisionProposal.job_id == job.id))
    assert claimed.status == JobStatus.COMPLETED.value
    assert proposal is not None
    assert proposal.status == "pending"


def test_style_workflow_only_populates_a_reviewable_suggestion(session: Session) -> None:
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=None,
        job_type=JobType.STYLE_PROFILE_SUGGESTION,
        idempotency_key="style-1",
        input_snapshot={"examples": [{"text": "A clear and casual intro."}]},
        routing_snapshot=routing_snapshot(),
    )
    suggestion = StyleProfileSuggestion(
        owner_id="creator-a",
        job_id=job.id,
        examples=[{"text": "A clear and casual intro."}],
    )
    session.add(suggestion)
    session.commit()
    claimed = JobRepository(session).claim_next(lease_seconds=30)
    assert claimed is not None

    service = ScriptCreationService(session, FakeProvider([{"voice": "Casual and direct"}]))
    service.execute_claimed_job(claimed)

    assert claimed.status == JobStatus.COMPLETED.value
    assert suggestion.profile is not None
    assert suggestion.profile["voice"] == "Casual and direct"


def test_provider_fallback_only_retries_retryable_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenRouterProvider(Settings(openrouter_api_key="test-key"))
    requested_models: list[str] = []

    def fake_request_model(**kwargs: Any) -> ProviderResult:
        requested_models.append(kwargs["model"])
        if len(requested_models) == 1:
            raise ProviderError("rate_limited", "temporary", retryable=True)
        return ProviderResult({"status": "ok"}, "second:free", "fake", None, None)

    monkeypatch.setattr(provider, "_request_model", fake_request_model)
    result = provider.generate_json(
        system_prompt="system",
        user_prompt="user",
        schema_name="test",
        schema={"type": "object"},
        routing={
            **routing_snapshot(),
            "default_model": "first:free",
            "fallback_models": ["second:free"],
        },
    )

    assert result.payload == {"status": "ok"}
    assert requested_models == ["first:free", "second:free"]


def test_provider_bounds_reasoning_and_explains_truncated_output(monkeypatch):
    import io
    import json

    requests = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    def reply(request, **kwargs):
        requests.append(json.loads(request.data))
        return Response(
            json.dumps(
                {
                    "choices": [{"finish_reason": "length", "message": {"content": None}}],
                    "usage": {
                        "completion_tokens": 2000,
                        "completion_tokens_details": {"reasoning_tokens": 2000},
                    },
                }
            ).encode()
        )

    monkeypatch.setattr("app.features.script_creation.provider.urlopen", reply)
    provider = OpenRouterProvider(Settings(_env_file=None, openrouter_api_key="test-key"))
    with pytest.raises(ProviderError, match="exhausted its output budget") as error:
        provider.generate_json(
            system_prompt="s",
            user_prompt="u",
            schema_name="test",
            schema={"type": "object"},
            routing=routing_snapshot(),
        )
    assert error.value.category == "output_limit"
    assert error.value.retryable
    assert len(requests) == 1
    assert requests[0]["reasoning"] == {"effort": "minimal", "exclude": True}


def test_structured_output_repair_is_bounded(monkeypatch):
    provider = OpenRouterProvider(Settings(_env_file=None, openrouter_api_key="test-key"))
    calls = []

    def invalid(**kwargs):
        calls.append(kwargs)
        return ProviderResult({"unsupported_id": "invented"}, "fake:free", None, None, None)

    monkeypatch.setattr(provider, "_request_model", invalid)
    with pytest.raises(ProviderError, match="schema"):
        provider.generate_json(
            system_prompt="s",
            user_prompt="u",
            schema_name="test",
            schema={"type": "object", "required": ["matches"]},
            routing=routing_snapshot(),
        )
    assert len(calls) == 2
    assert "previous response was invalid" in calls[1]["user_prompt"]


def test_insight_explanation_uses_frozen_facts_and_rejects_fake_evidence(session):
    JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=None,
        job_type=JobType.INSIGHT_SUMMARY,
        idempotency_key="facts",
        routing_snapshot=routing_snapshot(),
        input_snapshot={
            "facts": {
                "performance": [{"snapshot_id": "known"}],
                "production": {"clips_produced": 3},
            }
        },
    )
    claimed = JobRepository(session).claim_next(900)
    ScriptCreationService(
        session,
        FakeProvider(
            [
                {
                    "summary": "Limited entered evidence.",
                    "evidence_snapshot_ids": ["invented"],
                    "limitations": ["Small sample"],
                }
            ]
        ),
    ).execute_claimed_job(claimed)
    assert claimed.status == "failed" and "unknown evidence" in claimed.error
    claimed.status = "running"
    ScriptCreationService(
        session,
        FakeProvider(
            [
                {
                    "summary": "Three clips were produced.",
                    "evidence_snapshot_ids": ["known"],
                    "limitations": ["Small sample"],
                }
            ]
        ),
    ).execute_claimed_job(claimed)
    assert claimed.status == "completed"
    assert claimed.input_snapshot["result"]["evidence_snapshot_ids"] == ["known"]

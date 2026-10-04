"""Explicit opt-in smoke tests using configured real OpenRouter calls and local PostgreSQL.

Run with CREATORAI_QA_LIVE=1 and CREATORAI_TEST_DATABASE_URL pointing to compose.test.yaml.
Synthetic briefs only; each case creates and removes its own database schema.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_postgres_integration import postgres_schema  # noqa: F401

from alembic import command
from app.config import Settings
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import OpenRouterProvider, ProviderError
from app.features.script_creation.routing import routing_snapshot
from app.features.script_creation.service import ScriptCreationService
from app.models import LlmCall, Project, ScriptVersion
from app.schemas import JobType, ScriptContent

pytestmark = pytest.mark.skipif(
    os.environ.get("CREATORAI_QA_LIVE") != "1",
    reason="Set CREATORAI_QA_LIVE=1 to authorize real LLM calls",
)


class RecordingProvider(OpenRouterProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []

    def generate_json(self, **kwargs):
        started = perf_counter()
        record = {"stage": kwargs["schema_name"], "max_calls": kwargs["routing"]["max_calls"]}
        self.calls.append(record)
        try:
            result = super().generate_json(**kwargs)
            record.update(
                outcome="success",
                model=result.actual_model,
                provider=result.provider,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                reasoning_tokens=result.reasoning_tokens,
                cost=result.cost,
                payload=result.payload,
            )
            return result
        except ProviderError as error:
            record.update(outcome="failed", error_category=error.category, error=str(error))
            raise
        finally:
            record["elapsed_seconds"] = round(perf_counter() - started, 3)
            print(
                f"LIVE STAGE {record['stage']} outcome={record.get('outcome')} "
                f"seconds={record['elapsed_seconds']}",
                flush=True,
            )


@pytest.mark.parametrize("case", ["organic", "brand_and_signature"])
def test_real_llm_script_workflow(postgres_schema, tmp_path, case):  # noqa: F811
    engine, config, _ = postgres_schema
    settings = Settings()
    assert settings.openrouter_api_key is not None, "Configure OPENROUTER_API_KEY"
    assert settings.openrouter_default_model, "Configure OPENROUTER_DEFAULT_MODEL"
    assert settings.openrouter_max_calls_per_operation >= 3
    command.upgrade(config, "head")
    provider = RecordingProvider(settings)
    snapshot = {
        "project": {
            "brief": "Write a practical Instagram Reel explaining how creators can batch "
            "weekly content planning. Give three concrete steps without inventing "
            "performance statistics or promising results.",
            "audience": "Independent creators",
            "tone": "Friendly, direct, practical",
            "target_platforms": ["instagram"],
        },
        "request": {"target_duration_seconds": 45},
    }
    if case == "brand_and_signature":
        snapshot["campaign_brief"] = {
            "content_mode": "brand",
            "brand_brief": {
                "brand_name": "PlanPilot",
                "requirements": [
                    {"id": "brand-name", "kind": "literal", "literal_text": "PlanPilot"}
                ],
                "approved_claims": ["PlanPilot provides a weekly content planning template."],
                "forbidden_phrases": ["guaranteed results", "double your followers"],
            },
        }
        snapshot["style_profile"] = {
            "profile": {
                "voice": "Friendly, direct, practical",
                "signature_lines": [
                    {
                        "id": "closing-line",
                        "text": "Keep creating!",
                        "inclusion_policy": "always",
                        "placement": "closing",
                    }
                ],
            }
        }

    started = perf_counter()
    with Session(engine, expire_on_commit=False) as session:
        project = Project(
            owner_id="live-smoke-test",
            name=f"Synthetic real LLM QA: {case}",
            brief=snapshot["project"]["brief"],
            target_platforms=["instagram"],
            workflow_stage="approved",
            workflow_data={"approved_package": {"title": "Old"}},
        )
        session.add(project)
        session.commit()
        job = JobRepository(session).enqueue(
            owner_id=project.owner_id,
            project_id=project.id,
            job_type=JobType.SCRIPT_GENERATION,
            idempotency_key=case,
            input_snapshot=snapshot,
            routing_snapshot=routing_snapshot(settings),
        )
        claimed = JobRepository(session).claim_next(900)
        assert claimed is not None and claimed.id == job.id
        print(f"LIVE START case={case} model={settings.openrouter_default_model}", flush=True)
        ScriptCreationService(session, provider).execute_claimed_job(claimed)
        versions = list(
            session.scalars(select(ScriptVersion).where(ScriptVersion.job_id == job.id))
        )
        calls = list(session.scalars(select(LlmCall).where(LlmCall.job_id == job.id)))
        report = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "case": case,
            "requested_model": settings.openrouter_default_model,
            "free_only": settings.openrouter_free_only,
            "job_status": claimed.status,
            "error": claimed.error,
            "elapsed_seconds": round(perf_counter() - started, 3),
            "call_count": len(provider.calls),
            "calls": provider.calls,
            "input_tokens": sum(c.input_tokens or 0 for c in calls),
            "output_tokens": sum(c.output_tokens or 0 for c in calls),
            "reasoning_tokens": (
                sum(c["reasoning_tokens"] for c in provider.calls)
                if all(c.get("reasoning_tokens") is not None for c in provider.calls)
                else None
            ),
            "provider_reported_cost": (
                sum(c["cost"] for c in provider.calls)
                if all(c.get("cost") is not None for c in provider.calls)
                else None
            ),
            "versions_saved": len(versions),
            "project_stage": project.workflow_stage,
            "content": versions[0].content if versions else None,
            "requirement_checks": versions[0].requirement_checks if versions else [],
            "warning_ids": versions[0].warning_ids if versions else [],
        }
        output = Path(os.environ.get("CREATORAI_LIVE_REPORT_DIR", str(tmp_path)))
        output.mkdir(parents=True, exist_ok=True)
        report_path = output / f"script-live-{case}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(
            f"LIVE RESULT case={case} status={claimed.status} calls={len(provider.calls)} "
            f"seconds={report['elapsed_seconds']} report={report_path}",
            flush=True,
        )

        assert claimed.status == "completed", claimed.error
        assert len(versions) == 1
        assert 2 <= len(provider.calls) <= 3
        assert all(c["max_calls"] == 1 for c in provider.calls)
        assert all(c["outcome"] == "success" for c in provider.calls)
        assert versions[0].input_snapshot == snapshot
        ScriptContent.model_validate(versions[0].content)
        assert not any(c["status"] == "missing" for c in versions[0].requirement_checks)
        assert project.workflow_stage == "editing"
        assert "approved_package" not in project.workflow_data

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.persistence import (
    StaleRevisionError,
    apply_revision_proposal,
    save_campaign_brief,
    save_creator_edit,
    save_style_profile,
)
from app.models import AssistantConversation, Base, Project, RevisionProposal, ScriptVersion
from app.repositories import ProjectRepository
from app.schemas import (
    CampaignBriefSaveRequest,
    ContentMode,
    CreatorEditRequest,
    CreatorStyleProfileContent,
    CreatorStyleProfileSaveRequest,
    JobType,
    Platform,
    ProjectCreate,
    ProposalApplyRequest,
    ScriptContent,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    Base.metadata.drop_all(engine)


def script_content() -> ScriptContent:
    return ScriptContent.model_validate(
        {
            "hooks": [{"id": "hook-1", "text": "Start with this creator shortcut."}],
            "selected_hook_id": "hook-1",
            "sections": [
                {
                    "id": "section-1",
                    "position": 1,
                    "heading": "Start here",
                    "text": "Use one repeatable planning step.",
                }
            ],
            "title": "Creator planning shortcut",
            "description": "A short workflow for creators.",
            "call_to_action": "Save this workflow.",
            "production_notes": [],
        }
    )


def project_with_current_script(session: Session) -> Project:
    project = ProjectRepository(session).create(
        "creator-a",
        ProjectCreate(
            name="Versioning test",
            brief="Explain a simple creator workflow.",
            target_platforms=[Platform.INSTAGRAM],
        ),
    )
    base = ScriptVersion(
        project_id=project.id,
        version=1,
        origin="generated",
        content=script_content().model_dump(mode="json"),
        requirement_checks=[],
        warning_ids=[],
        input_snapshot={},
    )
    session.add(base)
    session.flush()
    project.current_script_version_id = base.id
    session.commit()
    return project


def test_creator_edit_creates_a_new_immutable_current_version(session: Session) -> None:
    project = project_with_current_script(session)
    edited_content = script_content().model_copy(
        update={"call_to_action": "Save this and try it this week."}
    )

    saved = save_creator_edit(
        session,
        project.id,
        CreatorEditRequest(base_version=1, content=edited_content),
    )

    assert saved.version == 2
    assert saved.origin == "creator"
    assert saved.content.call_to_action == "Save this and try it this week."
    with pytest.raises(StaleRevisionError):
        save_creator_edit(
            session,
            project.id,
            CreatorEditRequest(base_version=1, content=edited_content),
        )


def test_creator_edit_assigns_stable_ids_to_new_blocks(session: Session) -> None:
    project = project_with_current_script(session)
    content = ScriptContent.model_validate(
        {
            **script_content().model_dump(mode="json"),
            "hooks": [
                {"id": "new-hook", "text": "A new opening to test."},
                {"id": "hook-1", "text": "Start with this creator shortcut."},
            ],
            "selected_hook_id": "new-hook",
            "sections": [
                {
                    "id": "section-1",
                    "position": 1,
                    "heading": "Start here",
                    "text": "Use one repeatable planning step.",
                },
                {
                    "id": "new-section",
                    "position": 2,
                    "heading": "Next step",
                    "text": "Keep the new step concise.",
                },
            ],
        }
    )

    saved = save_creator_edit(
        session,
        project.id,
        CreatorEditRequest(base_version=1, content=content),
    )

    assert saved.content.selected_hook_id.startswith("hook-")
    assert saved.content.selected_hook_id != "new-hook"
    assert saved.content.sections[1].id.startswith("section-")
    assert saved.content.sections[1].id != "new-section"


def test_profile_and_campaign_saves_require_the_current_revision(session: Session) -> None:
    project = project_with_current_script(session)
    profile = CreatorStyleProfileSaveRequest(
        base_revision=None,
        profile=CreatorStyleProfileContent(voice="Clear and conversational"),
    )
    saved_profile = save_style_profile(session, "creator-a", profile)
    saved_campaign = save_campaign_brief(
        session,
        project.id,
        CampaignBriefSaveRequest(base_revision=None, content_mode=ContentMode.PERSONAL),
    )

    assert saved_profile.revision == 1
    assert saved_campaign.revision == 1
    with pytest.raises(StaleRevisionError):
        save_style_profile(session, "creator-a", profile)
    with pytest.raises(StaleRevisionError):
        save_campaign_brief(
            session,
            project.id,
            CampaignBriefSaveRequest(base_revision=None, content_mode=ContentMode.PERSONAL),
        )


def test_pending_proposal_applies_as_a_new_script_version(session: Session) -> None:
    project = project_with_current_script(session)
    base = session.query(ScriptVersion).filter_by(project_id=project.id, version=1).one()
    conversation = AssistantConversation(owner_id="creator-a", project_id=project.id)
    session.add(conversation)
    session.flush()
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.ASSISTANT_REVISION,
        idempotency_key="proposal-1",
        input_snapshot={},
        routing_snapshot={},
    )
    proposal = RevisionProposal(
        owner_id="creator-a",
        project_id=project.id,
        conversation_id=conversation.id,
        base_script_version_id=base.id,
        job_id=job.id,
        explanation="A more direct opening.",
        changes=[
            {
                "target_scope": "hook",
                "target_id": "hook-1",
                "before": "Start with this creator shortcut.",
                "after": "Try this creator shortcut first.",
            }
        ],
        requirement_checks=[],
        warning_ids=[],
    )
    session.add(proposal)
    session.commit()

    applied = apply_revision_proposal(
        session,
        owner_id="creator-a",
        project_id=project.id,
        proposal_id=proposal.id,
        request=ProposalApplyRequest(),
    )

    assert applied.version == 2
    assert applied.origin == "assistant_applied"
    assert applied.content.hooks[0].text == "Try this creator shortcut first."
    assert proposal.status == "applied"


def test_full_script_proposal_applies_a_reviewed_replacement(session: Session) -> None:
    project = project_with_current_script(session)
    base = session.query(ScriptVersion).filter_by(project_id=project.id, version=1).one()
    conversation = AssistantConversation(owner_id="creator-a", project_id=project.id)
    session.add(conversation)
    session.flush()
    job = JobRepository(session).enqueue(
        owner_id="creator-a",
        project_id=project.id,
        job_type=JobType.ASSISTANT_REVISION,
        idempotency_key="full-script-proposal",
        input_snapshot={},
        routing_snapshot={},
    )
    replacement = script_content().model_copy(update={"title": "A clearer creator workflow"})
    proposal = RevisionProposal(
        owner_id="creator-a",
        project_id=project.id,
        conversation_id=conversation.id,
        base_script_version_id=base.id,
        job_id=job.id,
        explanation="Reworked the script while retaining its blocks.",
        changes=[
            {
                "target_scope": "script",
                "content_after": replacement.model_dump(mode="json"),
            }
        ],
        requirement_checks=[],
        warning_ids=[],
    )
    session.add(proposal)
    session.commit()

    applied = apply_revision_proposal(
        session,
        owner_id="creator-a",
        project_id=project.id,
        proposal_id=proposal.id,
        request=ProposalApplyRequest(),
    )

    assert applied.content.title == "A clearer creator workflow"
    assert applied.content.hooks[0].id == "hook-1"

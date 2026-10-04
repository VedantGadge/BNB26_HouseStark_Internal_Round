"""Script-generation submission endpoints; durable execution is handled by the worker."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_session
from app.features.script_creation.jobs import IdempotencyConflictError, JobRepository, job_response
from app.features.script_creation.persistence import (
    StaleRevisionError,
    apply_revision_proposal,
    current_campaign_brief,
    discard_revision_proposal,
    get_script_version,
    list_script_versions,
    save_campaign_brief,
    save_creator_edit,
    script_version_response,
)
from app.features.script_creation.routing import require_openrouter_configuration, routing_snapshot
from app.features.script_creation.snapshots import (
    parse_conversation_id,
    resolve_generation_snapshot,
)
from app.features.script_creation.trends import (
    GoogleTrendsSource,
    TrendSuggestions,
    TrendsUnavailable,
    get_trends_source,
    suggest_topics,
)
from app.models import AssistantConversation, AssistantMessage, RevisionProposal, ScriptVersion
from app.repositories import ProjectRepository
from app.schemas import (
    AssistantConversationMessageResponse,
    AssistantConversationResponse,
    AssistantMessageRequest,
    CampaignBriefResponse,
    CampaignBriefSaveRequest,
    CreatorEditRequest,
    JobResponse,
    JobType,
    ProposalApplyRequest,
    ProposalStatus,
    RevisionProposalSummary,
    ScriptGenerationRequest,
    ScriptVersionResponse,
)

router = APIRouter()

IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=200),
]


@router.get("/campaign-brief", response_model=CampaignBriefResponse)
def get_campaign_brief(
    project_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> CampaignBriefResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    campaign = current_campaign_brief(session, project.id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign brief not found.",
        )
    return CampaignBriefResponse(
        revision=campaign.revision,
        content_mode=campaign.content_mode,
        brand_brief=campaign.brand_brief,
    )


@router.put("/campaign-brief", response_model=CampaignBriefResponse)
def put_campaign_brief(
    project_id: uuid.UUID,
    request: CampaignBriefSaveRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> CampaignBriefResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return save_campaign_brief(session, project.id, request)
    except StaleRevisionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign brief was updated elsewhere. Refresh before saving.",
        ) from error


@router.get("/versions", response_model=list[ScriptVersionResponse])
def get_script_versions(
    project_id: uuid.UUID,
    generation_job_id: uuid.UUID | None = None,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> list[ScriptVersionResponse]:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return list_script_versions(session, project.id, generation_job_id)


@router.get("/versions/{version_id}", response_model=ScriptVersionResponse)
def get_script_version_by_id(
    project_id: uuid.UUID,
    version_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> ScriptVersionResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    version = get_script_version(session, project.id, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script version not found.",
        )
    return script_version_response(version)


@router.post("/versions", response_model=ScriptVersionResponse, status_code=status.HTTP_201_CREATED)
def create_creator_edit(
    project_id: uuid.UUID,
    request: CreatorEditRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> ScriptVersionResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return save_creator_edit(session, project.id, request)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except StaleRevisionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The base version is no longer current.",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/trends", response_model=TrendSuggestions)
def get_script_trends(
    project_id: uuid.UUID,
    country: Annotated[str, Query(pattern=r"^[A-Z]{2}$")] = "IN",
    focus: Annotated[str, Query(max_length=200)] = "",
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
    source: GoogleTrendsSource = Depends(get_trends_source),
) -> TrendSuggestions:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    campaign = current_campaign_brief(session, project.id)
    brand = campaign.brand_brief if campaign and campaign.content_mode == "brand" else {}
    context = focus.strip() or " ".join(filter(None, [
        project.brief, project.audience,
        *((brand or {}).get(key) for key in (
            "brand_name", "product_name", "product_description", "campaign_audience",
        )),
    ]))
    try:
        return suggest_topics(source.feed(country), context)
    except TrendsUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/generate", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_script(
    project_id: uuid.UUID,
    request: ScriptGenerationRequest,
    idempotency_key: IdempotencyKey,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
    source: GoogleTrendsSource = Depends(get_trends_source),
) -> JobResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    require_openrouter_configuration(settings)
    if settings.openrouter_max_calls_per_operation < 4:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Script review requires OPENROUTER_MAX_CALLS_PER_OPERATION >= 4.",
        )
    jobs = JobRepository(session)
    # Feed refreshes must not change an already accepted operation's input or break retries.
    submission = (
        {"project_id": str(project.id), "request": request.model_dump(mode="json")}
        if request.trend else None
    )
    existing = jobs.find_by_idempotency(creator.id, JobType.SCRIPT_GENERATION, idempotency_key)
    if submission and existing is not None:
        input_snapshot = existing.input_snapshot
    else:
        input_snapshot = resolve_generation_snapshot(
            session, owner_id=creator.id, project=project, request=request,
        )
        if request.trend:
            try:
                input_snapshot["selected_trend"] = source.selected_snapshot(request.trend)
            except TrendsUnavailable as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
            except ValueError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
    try:
        job = jobs.enqueue(
            owner_id=creator.id,
            project_id=project.id,
            job_type=JobType.SCRIPT_GENERATION,
            idempotency_key=idempotency_key,
            input_snapshot=input_snapshot,
            routing_snapshot=routing_snapshot(settings),
            idempotency_payload=submission,
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with different input.",
        ) from error
    return job_response(job)


@router.post(
    "/assistant/messages",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_assistant_revision(
    project_id: uuid.UUID,
    request: AssistantMessageRequest,
    idempotency_key: IdempotencyKey,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> JobResponse:
    project = ProjectRepository(session).get_owned(creator.id, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    require_openrouter_configuration(settings)

    base_script = session.scalar(
        select(ScriptVersion).where(
            ScriptVersion.project_id == project.id,
            ScriptVersion.version == request.base_version,
        )
    )
    if base_script is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base script version not found.",
        )
    if project.current_script_version_id != base_script.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assistant revisions must target the current script version.",
        )
    _validate_assistant_target(request, base_script.content)

    jobs = JobRepository(session)
    existing = jobs.find_by_idempotency(
        creator.id,
        JobType.ASSISTANT_REVISION,
        idempotency_key,
    )
    idempotency_payload = request.model_dump(mode="json")
    if existing is not None:
        try:
            job = jobs.enqueue(
                owner_id=creator.id,
                project_id=project.id,
                job_type=JobType.ASSISTANT_REVISION,
                idempotency_key=idempotency_key,
                input_snapshot=existing.input_snapshot,
                routing_snapshot=routing_snapshot(settings),
                idempotency_payload=idempotency_payload,
            )
        except IdempotencyConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used with different input.",
            ) from error
        return job_response(job)

    conversation = _resolve_conversation(session, creator.id, project.id, request.conversation_id)
    message = AssistantMessage(
        conversation_id=conversation.id,
        role="creator",
        content=request.message,
        target_scope=request.target_scope.value,
        target_id=request.target_id,
        base_version=request.base_version,
    )
    session.add(message)
    input_snapshot = {
        "conversation_id": str(conversation.id),
        "base_script": {
            "id": str(base_script.id),
            "version": base_script.version,
            "content": base_script.content,
            "requirement_checks": base_script.requirement_checks,
            "warning_ids": base_script.warning_ids,
            "input_snapshot": base_script.input_snapshot,
        },
        "message": idempotency_payload,
    }
    try:
        job = jobs.enqueue(
            owner_id=creator.id,
            project_id=project.id,
            job_type=JobType.ASSISTANT_REVISION,
            idempotency_key=idempotency_key,
            input_snapshot=input_snapshot,
            routing_snapshot=routing_snapshot(settings),
            idempotency_payload=idempotency_payload,
        )
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with different input.",
        ) from error
    return job_response(job)


@router.get(
    "/assistant/conversations/{conversation_id}",
    response_model=AssistantConversationResponse,
)
def get_assistant_conversation(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> AssistantConversationResponse:
    if ProjectRepository(session).get_owned(creator.id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    conversation = session.scalar(
        select(AssistantConversation).where(
            AssistantConversation.id == conversation_id,
            AssistantConversation.owner_id == creator.id,
            AssistantConversation.project_id == project_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    messages = list(
        session.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation.id)
            .order_by(AssistantMessage.created_at.asc(), AssistantMessage.id.asc())
        )
    )
    proposals = list(
        session.scalars(
            select(RevisionProposal)
            .where(RevisionProposal.conversation_id == conversation.id)
            .order_by(RevisionProposal.created_at.asc(), RevisionProposal.id.asc())
        )
    )
    return AssistantConversationResponse(
        id=str(conversation.id),
        messages=[
            AssistantConversationMessageResponse(
                id=str(message.id),
                role=message.role,
                content=message.content,
                target_scope=message.target_scope,
                target_id=message.target_id,
                base_version=message.base_version,
            )
            for message in messages
        ],
        proposals=[
            RevisionProposalSummary(
                id=str(proposal.id),
                base_version=session.get(ScriptVersion, proposal.base_script_version_id).version,
                status=ProposalStatus(proposal.status),
                explanation=proposal.explanation,
                changes=proposal.changes or [],
                requirement_checks=proposal.requirement_checks,
                warning_ids=proposal.warning_ids,
            )
            for proposal in proposals
        ],
    )


def _resolve_conversation(
    session: Session,
    owner_id: str,
    project_id: uuid.UUID,
    conversation_id: str | None,
) -> AssistantConversation:
    parsed_id = parse_conversation_id(conversation_id)
    if parsed_id is None:
        conversation = AssistantConversation(owner_id=owner_id, project_id=project_id)
        session.add(conversation)
        session.flush()
        return conversation
    conversation = session.scalar(
        select(AssistantConversation).where(
            AssistantConversation.id == parsed_id,
            AssistantConversation.owner_id == owner_id,
            AssistantConversation.project_id == project_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


def _validate_assistant_target(request: AssistantMessageRequest, content: dict) -> None:
    if request.target_scope.value == "hook":
        target_ids = {hook["id"] for hook in content.get("hooks", [])}
    elif request.target_scope.value == "section":
        target_ids = {section["id"] for section in content.get("sections", [])}
    else:
        return
    if request.target_id not in target_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Assistant target does not exist in the base script.",
        )


@router.post(
    "/assistant/proposals/{proposal_id}/apply",
    response_model=ScriptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_assistant_proposal(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: ProposalApplyRequest,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> ScriptVersionResponse:
    if ProjectRepository(session).get_owned(creator.id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        return apply_revision_proposal(
            session,
            owner_id=creator.id,
            project_id=project_id,
            proposal_id=proposal_id,
            request=request,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except StaleRevisionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The proposal no longer targets the current script version.",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/assistant/proposals/{proposal_id}/discard", status_code=status.HTTP_204_NO_CONTENT)
def discard_assistant_proposal(
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    creator: AuthenticatedCreator = Depends(get_current_creator),
    session: Session = Depends(get_session),
) -> None:
    if ProjectRepository(session).get_owned(creator.id, project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    try:
        discarded = discard_revision_proposal(
            session,
            owner_id=creator.id,
            project_id=project_id,
            proposal_id=proposal_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if not discarded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision proposal not found.",
        )

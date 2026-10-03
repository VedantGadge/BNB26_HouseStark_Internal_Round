"""Append-only profile, campaign, and script-version persistence operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.features.script_creation.requirements import (
    evaluate_requirements,
    find_requirement_conflicts,
)
from app.models import (
    CampaignBriefRevision,
    Project,
    RevisionProposal,
    ScriptVersion,
    StyleProfileRevision,
    StyleProfileSuggestion,
)
from app.schemas import (
    CampaignBriefResponse,
    CampaignBriefSaveRequest,
    CreatorEditRequest,
    CreatorStyleProfileResponse,
    CreatorStyleProfileSaveRequest,
    ProposalApplyRequest,
    ProposalChange,
    RequirementStatus,
    ScriptContent,
    ScriptOrigin,
    ScriptVersionResponse,
)


class StaleRevisionError(Exception):
    """The supplied revision/version is no longer the current version."""


def current_style_profile(session: Session, owner_id: str) -> StyleProfileRevision | None:
    return session.scalar(
        select(StyleProfileRevision)
        .where(StyleProfileRevision.owner_id == owner_id)
        .order_by(StyleProfileRevision.revision.desc())
        .limit(1)
    )


def save_style_profile(
    session: Session,
    owner_id: str,
    request: CreatorStyleProfileSaveRequest,
) -> CreatorStyleProfileResponse:
    current = current_style_profile(session, owner_id)
    _validate_base_revision(current.revision if current else None, request.base_revision)
    suggestion_id = None
    if request.suggestion_id:
        try:
            suggestion_id = uuid.UUID(request.suggestion_id)
        except ValueError as error:
            raise ValueError("suggestion_id must be a UUID") from error
        suggestion = session.scalar(
            select(StyleProfileSuggestion).where(
                StyleProfileSuggestion.id == suggestion_id,
                StyleProfileSuggestion.owner_id == owner_id,
            )
        )
        if suggestion is None or suggestion.profile is None:
            raise ValueError("Style suggestion is not ready or does not belong to this creator")
    revision = (current.revision if current else 0) + 1
    saved = StyleProfileRevision(
        owner_id=owner_id,
        revision=revision,
        profile=request.profile.model_dump(mode="json"),
        suggestion_id=suggestion_id,
    )
    session.add(saved)
    session.commit()
    return CreatorStyleProfileResponse(revision=saved.revision, profile=request.profile)


def current_campaign_brief(
    session: Session,
    project_id: uuid.UUID,
) -> CampaignBriefRevision | None:
    return session.scalar(
        select(CampaignBriefRevision)
        .where(CampaignBriefRevision.project_id == project_id)
        .order_by(CampaignBriefRevision.revision.desc())
        .limit(1)
    )


def save_campaign_brief(
    session: Session,
    project_id: uuid.UUID,
    request: CampaignBriefSaveRequest,
) -> CampaignBriefResponse:
    current = current_campaign_brief(session, project_id)
    _validate_base_revision(current.revision if current else None, request.base_revision)
    revision = (current.revision if current else 0) + 1
    saved = CampaignBriefRevision(
        project_id=project_id,
        revision=revision,
        content_mode=request.content_mode.value,
        brand_brief=request.brand_brief.model_dump(mode="json") if request.brand_brief else None,
    )
    session.add(saved)
    session.commit()
    return CampaignBriefResponse(
        revision=saved.revision,
        content_mode=request.content_mode,
        brand_brief=request.brand_brief,
    )


def list_script_versions(
    session: Session,
    project_id: uuid.UUID,
    generation_job_id: uuid.UUID | None = None,
) -> list[ScriptVersionResponse]:
    statement = select(ScriptVersion).where(ScriptVersion.project_id == project_id)
    if generation_job_id is not None:
        statement = statement.where(ScriptVersion.job_id == generation_job_id)
    versions = list(session.scalars(statement.order_by(ScriptVersion.version.desc())))
    return [script_version_response(version) for version in versions]


def get_script_version(
    session: Session,
    project_id: uuid.UUID,
    version_id: uuid.UUID,
) -> ScriptVersion | None:
    return session.scalar(
        select(ScriptVersion).where(
            ScriptVersion.id == version_id,
            ScriptVersion.project_id == project_id,
        )
    )


def save_creator_edit(
    session: Session,
    project_id: uuid.UUID,
    request: CreatorEditRequest,
) -> ScriptVersionResponse:
    project = session.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise LookupError("Project not found")
    base = session.scalar(
        select(ScriptVersion).where(
            ScriptVersion.project_id == project_id,
            ScriptVersion.version == request.base_version,
        )
    )
    if base is None:
        raise LookupError("Base script version not found")
    if project.current_script_version_id != base.id:
        raise StaleRevisionError
    _raise_for_requirement_conflicts(base.input_snapshot)

    content = _assign_ids_to_additions(base.content, request.content)
    checks, warning_ids = evaluate_requirements(base.input_snapshot, content)
    if any(check.status is RequirementStatus.MISSING for check in checks):
        raise ValueError("Mandatory literal or signature requirements are missing")
    if not set(warning_ids).issubset(request.acknowledged_warning_ids):
        raise ValueError("All review warnings must be acknowledged before saving")

    next_version = (
        session.scalar(
            select(func.max(ScriptVersion.version)).where(ScriptVersion.project_id == project_id)
        )
        or 0
    ) + 1
    saved = ScriptVersion(
        project_id=project_id,
        version=next_version,
        parent_version_id=base.id,
        origin=ScriptOrigin.CREATOR.value,
        content=content.model_dump(mode="json"),
        requirement_checks=[check.model_dump(mode="json") for check in checks],
        warning_ids=warning_ids,
        input_snapshot=base.input_snapshot,
    )
    session.add(saved)
    session.flush()
    project.current_script_version_id = saved.id
    session.commit()
    return script_version_response(saved)


def script_version_response(version: ScriptVersion) -> ScriptVersionResponse:
    return ScriptVersionResponse(
        id=str(version.id),
        version=version.version,
        origin=ScriptOrigin(version.origin),
        created_at=version.created_at,
        generation_job_id=str(version.job_id) if version.job_id else None,
        input_snapshot=version.input_snapshot,
        content=version.content,
        requirement_checks=version.requirement_checks,
        warning_ids=version.warning_ids,
    )


def apply_revision_proposal(
    session: Session,
    *,
    owner_id: str,
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: ProposalApplyRequest,
) -> ScriptVersionResponse:
    project = session.scalar(select(Project).where(Project.id == project_id).with_for_update())
    proposal = session.scalar(
        select(RevisionProposal).where(
            RevisionProposal.id == proposal_id,
            RevisionProposal.owner_id == owner_id,
            RevisionProposal.project_id == project_id,
        )
    )
    if project is None or proposal is None:
        raise LookupError("Revision proposal not found")
    if proposal.status != "pending":
        raise ValueError("Only pending revision proposals can be applied")
    if project.current_script_version_id != proposal.base_script_version_id:
        raise StaleRevisionError
    base = session.get(ScriptVersion, proposal.base_script_version_id)
    if base is None or proposal.changes is None:
        raise ValueError("Revision proposal is incomplete")
    _raise_for_requirement_conflicts(base.input_snapshot)

    content = _apply_changes(base.content, proposal.changes)
    checks, warning_ids = evaluate_requirements(base.input_snapshot, content)
    if any(check.status is RequirementStatus.MISSING for check in checks):
        raise ValueError("Mandatory literal or signature requirements are missing")
    if not set(warning_ids).issubset(request.acknowledged_warning_ids):
        raise ValueError("All review warnings must be acknowledged before applying")

    next_version = (
        session.scalar(
            select(func.max(ScriptVersion.version)).where(ScriptVersion.project_id == project_id)
        )
        or 0
    ) + 1
    saved = ScriptVersion(
        project_id=project_id,
        version=next_version,
        parent_version_id=base.id,
        origin=ScriptOrigin.ASSISTANT_APPLIED.value,
        content=content.model_dump(mode="json"),
        requirement_checks=[check.model_dump(mode="json") for check in checks],
        warning_ids=warning_ids,
        input_snapshot=base.input_snapshot,
    )
    session.add(saved)
    session.flush()
    project.current_script_version_id = saved.id
    proposal.status = "applied"
    session.commit()
    return script_version_response(saved)


def discard_revision_proposal(
    session: Session,
    *,
    owner_id: str,
    project_id: uuid.UUID,
    proposal_id: uuid.UUID,
) -> bool:
    proposal = session.scalar(
        select(RevisionProposal).where(
            RevisionProposal.id == proposal_id,
            RevisionProposal.owner_id == owner_id,
            RevisionProposal.project_id == project_id,
        )
    )
    if proposal is None:
        return False
    if proposal.status != "pending":
        raise ValueError("Only pending revision proposals can be discarded")
    proposal.status = "discarded"
    session.commit()
    return True


def _apply_changes(base_content: dict, raw_changes: list[dict]) -> ScriptContent:
    content = ScriptContent.model_validate(base_content)
    data = content.model_dump(mode="json")
    for raw_change in raw_changes:
        change = ProposalChange.model_validate(raw_change)
        if change.target_scope.value == "script":
            if change.content_after is None:
                raise ValueError("Script proposal is missing replacement content")
            data = change.content_after.model_dump(mode="json")
            continue
        if change.target_scope.value == "hook":
            target = next((hook for hook in data["hooks"] if hook["id"] == change.target_id), None)
        elif change.target_scope.value == "section":
            target = next(
                (section for section in data["sections"] if section["id"] == change.target_id),
                None,
            )
        elif change.target_scope.value == "cta":
            if data["call_to_action"] != change.before:
                raise ValueError("Proposal no longer matches its base script")
            data["call_to_action"] = change.after
            continue
        elif change.target_scope.value == "supporting_copy":
            if data["description"] != change.before:
                raise ValueError("Proposal no longer matches its base script")
            data["description"] = change.after
            continue
        else:
            raise ValueError("Proposal scope cannot be applied automatically")
        if target is None or target["text"] != change.before:
            raise ValueError("Proposal no longer matches its base script")
        target["text"] = change.after
    return ScriptContent.model_validate(data)


def _validate_base_revision(current: int | None, requested: int | None) -> None:
    if current is None and requested is None:
        return
    if current is not None and requested == current:
        return
    raise StaleRevisionError


def _raise_for_requirement_conflicts(snapshot: dict) -> None:
    conflicts = find_requirement_conflicts(snapshot)
    if conflicts:
        raise ValueError(" ".join(conflicts))


def _assign_ids_to_additions(base_content: dict, requested_content: ScriptContent) -> ScriptContent:
    """Keep existing IDs and replace client placeholder IDs for newly added blocks."""

    data = requested_content.model_dump(mode="json")
    existing_hook_ids = {hook["id"] for hook in base_content.get("hooks", [])}
    existing_section_ids = {section["id"] for section in base_content.get("sections", [])}
    hook_id_map: dict[str, str] = {}
    for hook in data["hooks"]:
        if hook["id"] not in existing_hook_ids:
            assigned = f"hook-{uuid.uuid4().hex[:12]}"
            hook_id_map[hook["id"]] = assigned
            hook["id"] = assigned
    for section in data["sections"]:
        if section["id"] not in existing_section_ids:
            section["id"] = f"section-{uuid.uuid4().hex[:12]}"
    if data["selected_hook_id"] in hook_id_map:
        data["selected_hook_id"] = hook_id_map[data["selected_hook_id"]]
    return ScriptContent.model_validate(data)

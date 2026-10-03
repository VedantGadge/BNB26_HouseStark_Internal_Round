import uuid
from copy import deepcopy
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Asset, EditRender, Job, Project, Publication, ScriptVersion

STAGES = ("idea", "assets", "editing", "review", "approved", "exported", "published")


def conflict(message: str):
    raise HTTPException(409, message)


def owned_project(session: Session, owner: str, project_id: uuid.UUID) -> Project:
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner)
    )
    if project is None:
        raise HTTPException(404, "Project not found.")
    return project


def publications(session: Session, project: Project) -> list[Publication]:
    return list(
        session.scalars(
            select(Publication)
            .where(Publication.project_id == project.id)
            .order_by(Publication.created_at, Publication.id)
        )
    )


def publication_response(record: Publication) -> dict:
    def utc(value):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value

    return {
        "id": str(record.id),
        "platform": record.platform,
        "status": record.status,
        "mode": "manual",
        "planned_at": utc(record.planned_at),
        "published_at": utc(record.published_at),
        "external_url": record.external_url,
        "package_snapshot": record.package_snapshot,
        "supporting_copy": record.supporting_copy,
    }


def has_script(session: Session, project: Project) -> bool:
    return (
        session.scalar(
            select(ScriptVersion.id).where(
                ScriptVersion.id == project.current_script_version_id,
                ScriptVersion.project_id == project.id,
            )
        )
        is not None
    )


def blockers(session: Session, project: Project, data: dict, target: str) -> list[str]:
    reasons = []
    if target in STAGES[1:] and not has_script(session, project):
        reasons.append("Save a script in the Script screen first.")
    if target in STAGES[2:] and not data.get("assets_ready"):
        reasons.append("Confirm that your footage/assets are ready.")
    if target in STAGES[2:] and not session.scalar(
        select(Asset.id).where(
            Asset.project_id == project.id,
            Asset.processing_status == "ready",
        )
    ):
        reasons.append("Upload and process a real source asset first.")
    if target in STAGES[3:] and not data.get("editing_complete"):
        reasons.append("Confirm that editing is complete.")
    if target in STAGES[3:]:
        package = data.get("package")
        if not package or not package.get("media_checked"):
            reasons.append("Save a rendered package and confirm you played its video.")
        elif not valid_package(session, project, package):
            reasons.append("Select completed exports belonging to this project.")
    if target in ("exported", "published") and not data.get("approved_package"):
        reasons.append("Review and explicitly approve the package first.")
    if target == "published":
        records = publications(session, project)
        published = {record.platform for record in records if record.status == "published"}
        required = set(project.target_platforms) or {record.platform for record in records}
        if not records or published != required:
            reasons.append("Confirm manual publication for every planned platform in Publish.")
    return reasons


def valid_package(session: Session, project: Project, package: dict) -> bool:
    import uuid

    ids = [uuid.UUID(value) for value in package.get("render_ids", [])]
    if not ids:
        return False
    renders = list(
        session.scalars(
            select(EditRender)
            .join(Asset)
            .where(
                EditRender.id.in_(ids),
                Asset.project_id == project.id,
                Asset.owner_id == project.owner_id,
                EditRender.processing_status == "completed",
            )
        )
    )
    return len(renders) == len(set(ids))


def response(session: Session, project: Project) -> dict:
    data = project.workflow_data or {}
    stage = project.workflow_stage
    next_stage = STAGES[STAGES.index(stage) + 1] if stage != "published" else None
    jobs = session.scalars(
        select(Job)
        .where(Job.project_id == project.id, Job.owner_id == project.owner_id)
        .order_by(Job.created_at.desc())
        .limit(10)
    )
    return {
        "project_id": str(project.id),
        "name": project.name,
        "brief": project.brief,
        "target_platforms": project.target_platforms,
        "stage": stage,
        "revision": project.workflow_revision,
        "checklist": {
            "script_saved": has_script(session, project),
            "assets_ready": bool(data.get("assets_ready")),
            "editing_complete": bool(data.get("editing_complete")),
        },
        "review_status": data.get("review_status", "not_requested"),
        "package": data.get("package"),
        "approved_package": data.get("approved_package"),
        "timestamps": data.get("timestamps", {}),
        "next_stage": next_stage,
        "blocking_reasons": blockers(session, project, data, next_stage) if next_stage else [],
        "next_action": {
            "idea": "Save your script, then move to Assets.",
            "assets": "Confirm your footage is ready, then move to Editing.",
            "editing": "Confirm the edit and package, then request review.",
            "review": "Review the prepared video and copy, then approve or request changes.",
            "approved": "Mark the approved package ready for download.",
            "exported": "Plan and confirm manual publication in Publish.",
            "published": "All planned platforms are manually confirmed published.",
        }[stage],
        "jobs": [
            {
                "id": str(job.id),
                "type": job.type,
                "status": job.status,
                "stage": job.stage,
                "error": job.error,
            }
            for job in jobs
        ],
        "publications": [publication_response(record) for record in publications(session, project)],
    }


def save(session: Session, project: Project, expected: int, data: dict, stage: str) -> None:
    result = session.execute(
        update(Project)
        .where(
            Project.id == project.id,
            Project.owner_id == project.owner_id,
            Project.workflow_revision == expected,
        )
        .values(workflow_data=data, workflow_stage=stage, workflow_revision=expected + 1),
        execution_options={"synchronize_session": False},
    )
    if result.rowcount != 1:
        session.rollback()
        conflict("Workflow changed in another tab. Refresh before saving.")
    session.commit()
    session.refresh(project)


def check_revision(project: Project, expected: int):
    if project.workflow_revision != expected:
        conflict("Workflow changed in another tab. Refresh before saving.")


def patch_workflow(session: Session, project: Project, payload) -> dict:
    check_revision(project, payload.expected_revision)
    if project.workflow_stage == "published" or any(
        p.status == "published" for p in publications(session, project)
    ):
        conflict("Published packages are preserved. Start a new project for another cycle.")
    data = deepcopy(project.workflow_data or {})
    changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision", "package"})
    if any(value is None for value in changes.values()):
        raise HTTPException(422, "Checklist values must be true or false.")
    data.update(changes)
    if "package" in payload.model_fields_set:
        if payload.package is None:
            raise HTTPException(422, "Package cannot be null.")
        package = payload.package.model_dump(mode="json")
        if not valid_package(session, project, package):
            raise HTTPException(
                409, "The package must contain completed exports from this project."
            )
        data["package"] = {
            **package,
            "revision": payload.expected_revision + 1,
            "provenance": "rendered_exports",
            "media_path": f"/projects/{project.id}/workflow/media",
        }
    stage = project.workflow_stage
    if data != (project.workflow_data or {}) and stage in ("review", "approved", "exported"):
        data.pop("approved_package", None)
        data["review_status"] = "changes_requested"
        stage = "editing"
    if not data.get("assets_ready") and stage == "editing":
        stage = "assets"
    if stage != project.workflow_stage:
        data.setdefault("timestamps", {})[stage] = datetime.now(UTC).isoformat()
    save(session, project, payload.expected_revision, data, stage)
    return response(session, project)


def transition(session: Session, project: Project, payload) -> dict:
    check_revision(project, payload.expected_revision)
    target, current = payload.stage, project.workflow_stage
    if target == current:
        return response(session, project)
    reopen = target == "editing" and current in ("review", "approved", "exported")
    if reopen and any(p.status == "published" for p in publications(session, project)):
        conflict("A published package cannot be reopened. Start a new project.")
    if not reopen and (current == "published" or target != STAGES[STAGES.index(current) + 1]):
        conflict("Stages must advance one step at a time, or return from review to editing.")
    if target == "published":
        conflict("Confirm publication using the explicit action in Publish.")
    data = deepcopy(project.workflow_data or {})
    reasons = blockers(session, project, data, target)
    if reasons:
        conflict(" ".join(reasons))
    if reopen:
        data.pop("approved_package", None)
        data["review_status"] = "changes_requested"
    elif target == "review":
        data["review_status"] = "pending"
    elif target == "approved":
        data["approved_package"] = deepcopy(data["package"])
        data["review_status"] = "approved"
    data.setdefault("timestamps", {})[target] = datetime.now(UTC).isoformat()
    save(session, project, payload.expected_revision, data, target)
    return response(session, project)

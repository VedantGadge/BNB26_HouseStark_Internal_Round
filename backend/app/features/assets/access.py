"""Owner-scoped asset and project lookups shared by media features."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.assets.models import Asset
from app.models import Project


def get_owned_project(session: Session, project_id: UUID, owner_id: str) -> Project:
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


def get_owned_asset(session: Session, asset_id: UUID, owner_id: str) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.id == asset_id, Asset.owner_id == owner_id))
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset

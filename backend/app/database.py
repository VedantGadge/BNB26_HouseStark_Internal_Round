from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata registry for every feature-owned model."""


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, pool_size=3, max_overflow=2)


def get_session_factory(settings: Settings) -> sessionmaker[Session]:
    database_url = settings.sqlalchemy_database_url
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is not configured.",
        )
    return sessionmaker(bind=get_engine(database_url), autoflush=False, expire_on_commit=False)


def get_session(
    creator: AuthenticatedCreator = Depends(get_current_creator),
    settings: Settings = Depends(get_settings),
) -> Generator[Session, None, None]:
    """FastAPI dependency that owns session cleanup for a single request."""

    with get_session_factory(settings)() as session:
        yield session


def get_db_session(session: Session = Depends(get_session)) -> Generator[Session, None, None]:
    """Compatibility dependency for independently owned media feature routes."""

    yield session

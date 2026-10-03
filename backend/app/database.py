from collections.abc import Generator
from functools import lru_cache

from fastapi import HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Shared SQLAlchemy metadata registry for every feature-owned model."""


@lru_cache
def get_engine() -> Engine:
    """Create one small, reusable synchronous engine for API and worker repositories."""

    database_url = get_settings().sqlalchemy_database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured before using database-backed routes")
    return create_engine(database_url, pool_pre_ping=True, pool_size=3, max_overflow=2)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that owns session cleanup for a single request."""

    try:
        session_factory = get_session_factory()
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is not configured.",
        ) from error

    with session_factory() as session:
        yield session

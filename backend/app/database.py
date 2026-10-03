from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=0)


def get_session_factory(settings: Settings) -> sessionmaker[Session]:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database persistence is not configured.",
        )
    return sessionmaker(bind=get_engine(settings.database_url), expire_on_commit=False)


def get_session(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    session = get_session_factory(settings)()
    try:
        yield session
    finally:
        session.close()

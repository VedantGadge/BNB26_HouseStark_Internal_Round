"""Explicit browser-QA fixture server, never used by the application entrypoint.

Uses an isolated PostgreSQL schema and real FFmpeg. External AI/storage responses
are labelled fixtures. Run with PYTHONPATH=.:tests and CREATORAI_QA_FIXTURE=1.
"""

import copy
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg
from fastapi import Request
from fastapi.responses import FileResponse
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from workflow_fakes import SCRIPT, Alignment, Storage, Transcriber, Vision

from app.auth import AuthenticatedCreator, get_current_creator
from app.config import Settings, get_settings
from app.database import get_db_session, get_session
from app.features.assets.router import get_storage
from app.features.assets.storage import CloudinaryStorage
from app.features.media_workflow.service import MediaWorkflowService
from app.features.script_creation.jobs import JobRepository
from app.features.script_creation.provider import OpenRouterProvider, ProviderResult
from app.features.script_creation.service import ScriptCreationService
from app.main import create_app
from app.models import Base
from app.schemas import JobType


class BrowserStorage(Storage):
    def create_upload_session(self, **kwargs):
        session = super().create_upload_session(**kwargs)
        session["upload_url"] = "http://127.0.0.1:8011/fixture-upload"
        return session


class ScriptProvider:
    def generate_json(self, *, schema_name, **kwargs):
        script = copy.deepcopy(SCRIPT)
        script["hooks"] += [
            {"id": "hook-2", "text": "Make your audio clear"},
            {"id": "hook-3", "text": "Show the product, not just the pitch"},
        ]
        payload = {"hooks": script["hooks"]} if schema_name == "creator_hooks" else script
        return ProviderResult(payload, "labelled-qa-fixture", "fixture", 100, 100)


def build_app():
    if os.environ.get("CREATORAI_QA_FIXTURE") != "1":
        raise RuntimeError("This test-only server requires explicit CREATORAI_QA_FIXTURE=1")
    conninfo = "postgresql://creatorai_test:local_test_only@127.0.0.1:55432/creatorai_test"
    previous = os.environ.get("CREATORAI_QA_SCHEMA")
    if previous and not re.fullmatch(r"browser_qa_[a-f0-9]{32}", previous):
        raise RuntimeError("QA schema must be a schema previously created by this server")
    schema = previous or "browser_qa_" + uuid.uuid4().hex
    with psycopg.connect(conninfo, autocommit=True) as connection:
        if not previous:
            connection.execute(f'CREATE SCHEMA "{schema}"')
    scoped = conninfo + f"?options=-csearch_path%3D{schema}"
    engine = create_engine(scoped.replace("postgresql://", "postgresql+psycopg://", 1))
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    artifacts = Path(__file__).resolve().parents[2] / "output" / "playwright"
    artifacts.mkdir(parents=True, exist_ok=True)
    directory = TemporaryDirectory(prefix="fixture-media-", dir=artifacts)
    storage = BrowserStorage(Path(directory.name), delivery_base="http://127.0.0.1:8011")
    fixture_settings = Settings(
        _env_file=None,
        database_url=scoped,
        cors_origins="http://127.0.0.1:3001",
        openrouter_api_key="fixture-only",
        openrouter_default_model="fixture:free",
    )
    live = os.environ.get("CREATORAI_QA_LIVE") == "1"
    settings = (
        Settings().model_copy(
            update={
                "database_url": scoped,
                "cors_origins": "http://127.0.0.1:3001",
            }
        )
        if live
        else fixture_settings
    )
    if live:
        if not all(
            [
                settings.cloudinary_cloud_name,
                settings.cloudinary_api_key,
                settings.cloudinary_api_secret,
                settings.groq_api_key,
            ]
        ):
            raise RuntimeError("Live QA requires saved Cloudinary and Groq credentials")
        storage = CloudinaryStorage(
            settings.cloudinary_cloud_name,
            settings.cloudinary_api_key,
            settings.cloudinary_api_secret,
        )
    stopped = threading.Event()

    def worker():
        with PostgresSaver.from_conn_string(scoped) as saver:
            saver.setup()
        if previous:
            from sqlalchemy import update

            from app.models import Job

            with factory() as session:
                # Recover only interrupted jobs in this explicit test-owned schema.
                session.execute(
                    update(Job)
                    .where(Job.status == "running")
                    .values(
                        status="queued",
                        stage="awaiting_worker",
                        lease_expires_at=None,
                    )
                )
                session.commit()
        while not stopped.is_set():
            with factory() as session:
                job = JobRepository(session).claim_next(900)
                if job is not None:
                    if job.type not in {
                        JobType.ASSET_INGESTION,
                        JobType.CLIP_GENERATION,
                        JobType.MEDIA_EXPORT,
                    }:
                        ScriptCreationService(
                            session, OpenRouterProvider(settings) if live else ScriptProvider()
                        ).execute_claimed_job(job)
                    else:
                        with PostgresSaver.from_conn_string(scoped) as saver:
                            MediaWorkflowService(
                                session,
                                settings,
                                storage,
                                saver,
                                None if live else (Transcriber(), Vision()),
                                None if live else Alignment(),
                            ).execute(job)
            stopped.wait(0.2)

    @asynccontextmanager
    async def lifespan(app):
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stopped.set()
            thread.join(timeout=30)
            engine.dispose()
            if not thread.is_alive():
                with psycopg.connect(conninfo, autocommit=True) as connection:
                    connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
                directory.cleanup()

    app = create_app()
    app.router.lifespan_context = lifespan
    app.user_middleware.clear()
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "Content-Range",
            "X-Unique-Upload-ID",
        ],
    )

    def session_dependency():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_db_session] = session_dependency
    app.dependency_overrides[get_current_creator] = lambda: AuthenticatedCreator(
        "browser-qa-fixture"
    )
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/qa-info")
    def info():
        return {
            "provider_data": "LIVE PROVIDERS" if live else "LABELLED TEST FIXTURES",
            "media": "REAL FFMPEG",
            "database": "ISOLATED POSTGRESQL SCHEMA",
            "schema": schema,
        }

    @app.post("/fixture-upload")
    async def upload(request: Request):
        await request.body()
        return {"asset_id": "provider-source", "version": 1, "done": True}

    @app.get("/fixture-media/{filename}")
    def media(filename: str):
        if filename != "source.mp4" and not any(
            item["path"].name == filename for item in storage.uploads.values()
        ):
            from fastapi import HTTPException

            raise HTTPException(404, "Fixture media not found")
        return FileResponse(Path(directory.name) / filename, media_type="video/mp4")

    return app

"""Real migrations, PostgreSQL claims, and checkpoint reconnection.

Opt in with CREATORAI_TEST_DATABASE_URL pointing to compose.test.yaml.
Every test owns a fresh schema; the application database is never touched.
"""

import asyncio
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.worker as worker_module
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.config import Settings, get_settings
from app.features.script_creation.jobs import JobRepository
from app.graphs.repurpose import build_repurpose_graph
from app.models import Asset, Job, Project
from app.schemas import JobType


@pytest.fixture
def postgres_schema(monkeypatch):
    raw = os.environ.get("CREATORAI_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set CREATORAI_TEST_DATABASE_URL to enable isolated PostgreSQL checks")
    url = make_url(raw)
    if url.host not in {"127.0.0.1", "localhost"} or url.database != "creatorai_test":
        pytest.fail("PostgreSQL checks only accept the dedicated local creatorai_test database")
    schema = "qa_" + uuid.uuid4().hex
    conninfo = raw.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(conninfo, autocommit=True) as connection:
        connection.execute(f'CREATE SCHEMA "{schema}"')
    scoped = url.set(
        drivername="postgresql+psycopg", query={"options": f"-csearch_path={schema}"}
    ).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", scoped)
    get_settings.cache_clear()
    engine = create_engine(scoped)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    try:
        yield engine, config, scoped.replace("postgresql+psycopg://", "postgresql://", 1)
    finally:
        engine.dispose()
        get_settings.cache_clear()
        with psycopg.connect(conninfo, autocommit=True) as connection:
            connection.execute(f'DROP SCHEMA "{schema}" CASCADE')


def test_upgrade_preserves_shared_projects_and_has_single_head(postgres_schema):
    engine, config, _ = postgres_schema
    command.upgrade(config, "0005_edit_versions_renders")
    project_id, asset_id = uuid.uuid4(), uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Project(id=project_id, owner_id="migration-owner", name="Preserve me", brief="QA")
        )
        session.flush()
        session.add(
            Asset(
                id=asset_id,
                project_id=project_id,
                owner_id="migration-owner",
                kind="video",
                public_id="creatorai/qa/preserved",
                resource_type="video",
                processing_status="ready",
            )
        )
        session.commit()
    command.upgrade(config, "head")
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
    with Session(engine) as session:
        assert session.get(Project, project_id).name == "Preserve me"
        assert session.get(Asset, asset_id).project_id == project_id
    tables = inspect(engine)
    assert "projects" in tables.get_table_names()
    assert "ai_script_projects" not in tables.get_table_names()
    assert {"platform_exports", "performance_snapshots"} <= set(tables.get_table_names())
    assert {"job_id", "recipe_snapshot", "supporting_copy"} <= {
        column["name"] for column in tables.get_columns("edit_renders")
    }
    command.downgrade(config, "0005_edit_versions_renders")
    command.upgrade(config, "head")
    with Session(engine) as session:
        assert session.get(Project, project_id).name == "Preserve me"


def test_postgres_claims_and_resume_after_checkpointer_reconnect(postgres_schema):
    engine, config, conninfo = postgres_schema
    command.upgrade(config, "head")
    with Session(engine, expire_on_commit=False) as session:
        repository = JobRepository(session)
        jobs = [
            repository.enqueue(
                owner_id="claim-owner",
                project_id=None,
                job_type=JobType.MEDIA_EXPORT,
                idempotency_key=str(index),
                input_snapshot={"fixture": index},
                routing_snapshot={},
            )
            for index in range(2)
        ]
        first = repository.claim_next(900)
        assert first is not None and first.status == "running"
        with Session(engine, expire_on_commit=False) as another:
            second = JobRepository(another).claim_next(900)
            assert second is not None and first.id != second.id
        assert {j.id for j in jobs} == {first.id, second.id}
    calls = []

    def propose(state):
        calls.append("propose")
        return {
            **state,
            "candidate_ids": ["grounded-candidate"],
            "edit_version_ids": ["saved-edit"],
        }

    thread = {"configurable": {"thread_id": "reconnect-test"}}
    with PostgresSaver.from_conn_string(conninfo) as saver:
        saver.setup()
        graph = build_repurpose_graph(propose, saver)
        result = graph.invoke({"asset_id": "fixture-source"}, thread)
        assert result.get("__interrupt__")
    # A separate connection and graph instance must resume without re-running work.
    with PostgresSaver.from_conn_string(conninfo) as saver:
        graph = build_repurpose_graph(propose, saver)
        resumed = graph.invoke(Command(resume={"edit_version_id": "saved-edit"}), thread)
        assert resumed["selected_edit_version_id"] == "saved-edit"
    assert calls == ["propose"]


def test_worker_checkpoint_setup_does_not_block_its_claim(postgres_schema, monkeypatch):
    engine, config, conninfo = postgres_schema
    command.upgrade(config, "head")
    # Limit the exact index-creation wait seen in the real browser reproduction.
    url = make_url(conninfo)
    url = url.set(query={"options": url.query["options"] + " -cstatement_timeout=1500"})
    settings = Settings(
        _env_file=None, database_url=url.render_as_string(hide_password=False).replace("+", "%20")
    )
    with Session(engine, expire_on_commit=False) as session:
        job = JobRepository(session).enqueue(
            owner_id="worker-order",
            project_id=None,
            job_type=JobType.CLIP_GENERATION,
            idempotency_key="worker-order",
            input_snapshot={},
            routing_snapshot={},
        )
        job_id = job.id

    def factory(_settings):
        return lambda: Session(engine, expire_on_commit=False)

    class MediaOperation:
        def __init__(self, session, settings, storage, saver):
            self.session = session

        def execute(self, job):
            job.status = "completed"
            self.session.commit()

    class StopIterationForTest(Exception):
        pass

    async def stop(_delay):
        raise StopIterationForTest()

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "get_session_factory", factory)
    monkeypatch.setattr(worker_module, "get_storage", lambda settings: object())
    monkeypatch.setattr(worker_module, "MediaWorkflowService", MediaOperation)
    monkeypatch.setattr(worker_module.asyncio, "sleep", stop)
    with pytest.raises(StopIterationForTest):
        asyncio.run(worker_module.run_worker())
    with Session(engine) as session:
        saved = session.get(Job, job_id)
        assert saved.status == "completed", saved.error


def test_media_review_uses_checkpoint_interrupt_not_stale_result_key(postgres_schema, monkeypatch):
    from app.features.clip_generation.models import ClipCandidate
    from app.features.editing.models import EditVersion
    from app.features.editing.schemas import EditRecipePayload
    from app.features.media_workflow.service import MediaWorkflowService

    engine, config, conninfo = postgres_schema
    command.upgrade(config, "head")
    with PostgresSaver.from_conn_string(conninfo) as saver:
        saver.setup()
    with Session(engine, expire_on_commit=False) as session:
        p = Project(owner_id="review-test", name="Labelled checkpoint test", brief="QA")
        session.add(p)
        session.flush()
        a = Asset(
            owner_id=p.owner_id,
            project_id=p.id,
            kind="video",
            resource_type="video",
            public_id="qa/review",
            processing_status="ready",
            duration_ms=10000,
        )
        session.add(a)
        session.flush()
        c = ClipCandidate(
            asset_id=a.id,
            hook="QA",
            transcript_text="QA",
            score=1,
            source_start_ms=0,
            source_end_ms=8000,
        )
        session.add(c)
        session.flush()
        v = EditVersion(
            asset_id=a.id,
            candidate_id=c.id,
            revision=1,
            author_type="creator",
            recipe=EditRecipePayload(source_start_ms=0, source_end_ms=8000).model_dump(),
        )
        session.add(v)
        session.commit()
        j = JobRepository(session).enqueue(
            owner_id=p.owner_id,
            project_id=p.id,
            job_type=JobType.CLIP_GENERATION,
            idempotency_key="review",
            input_snapshot={},
            routing_snapshot={},
        )
        monkeypatch.setattr(
            MediaWorkflowService,
            "propose",
            lambda self, job, state: {
                **state,
                "candidate_ids": [str(c.id)],
                "edit_version_ids": [str(v.id)],
            },
        )
        settings = Settings(_env_file=None)
        with PostgresSaver.from_conn_string(conninfo) as saver:
            MediaWorkflowService(session, settings, object(), saver).clips(j)
        assert j.status == "waiting_review"
        j.input_snapshot = {"review": {"edit_version_id": str(v.id)}}
        session.commit()
        with PostgresSaver.from_conn_string(conninfo) as saver:
            MediaWorkflowService(session, settings, object(), saver).clips(j)
        assert j.status == "completed"
        assert j.input_snapshot["result"]["selected_edit_version_id"] == str(v.id)

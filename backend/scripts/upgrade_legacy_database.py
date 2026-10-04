"""Reconcile the original split PostgreSQL histories, preserving legacy rows.

Run from backend: python -m scripts.upgrade_legacy_database
Stop API/worker writes first. Ordinary databases should use alembic upgrade head.
The reconciliation and remaining migrations run in one PostgreSQL transaction.
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection

from alembic import command
from alembic.config import Config
from app.config import get_settings
from app.models import Base


def upgrade_legacy_database(connection: Connection, config: Config) -> int:
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Legacy reconciliation requires PostgreSQL")
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if not {"ai_script_projects", "projects", "alembic_version"} <= tables:
        raise RuntimeError("This is not the original split-history database")
    script_revision = (
        connection.execute(text("SELECT version_num FROM ai_script_alembic_version"))
        .scalars()
        .all()
    )
    media_revision = (
        connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    )
    if script_revision != ["0002_content_workflow"] or media_revision != ["0006_platform_exports"]:
        raise RuntimeError("Unexpected migration versions; refusing to guess a migration baseline")

    # Verify all tables/columns represented by the existing media baseline before
    # marking that baseline as applied in the unified history.
    later_tables = {"performance_snapshots", "youtube_connections", "youtube_oauth_attempts"}
    later_columns = {
        "projects": {"current_script_version_id", "workflow_revision", "workflow_data"},
        "script_alignments": {"script_version_id", "section_id", "match_status", "visual_evidence"},
        "clip_candidates": {"script_version_id"},
        "edit_renders": {"job_id", "preset_name", "platform", "supporting_copy", "recipe_snapshot"},
        "platform_exports": {"render_id"},
    }
    for table in Base.metadata.sorted_tables:
        if table.name in later_tables:
            continue
        expected = set(table.columns.keys()) - later_columns.get(table.name, set())
        actual = {column["name"] for column in inspector.get_columns(table.name)}
        if not expected <= actual:
            raise RuntimeError(f"Legacy table {table.name} is missing expected columns")

    connection.execute(text("SET LOCAL lock_timeout = '10s'"))
    connection.execute(text("LOCK TABLE projects, ai_script_projects IN ACCESS EXCLUSIVE MODE"))
    collision = connection.execute(
        text("SELECT 1 FROM projects p JOIN ai_script_projects s ON p.id = s.id LIMIT 1")
    ).first()
    if collision:
        raise RuntimeError("Project IDs overlap; refusing to overwrite either project")
    active = connection.execute(
        text("SELECT 1 FROM ai_script_jobs WHERE status IN ('queued', 'running') LIMIT 1")
    ).first()
    if active:
        raise RuntimeError("Finish pending jobs and stop workers before reconciliation")

    connection.execute(text("ALTER TABLE projects ADD COLUMN current_script_version_id uuid"))
    connection.execute(
        text("ALTER TABLE projects ADD COLUMN workflow_revision integer NOT NULL DEFAULT 1")
    )
    connection.execute(
        text("ALTER TABLE projects ADD COLUMN workflow_data json NOT NULL DEFAULT '{}'::json")
    )
    names = ", ".join(
        connection.dialect.identifier_preparer.quote(c)
        for c in Base.metadata.tables["projects"].columns.keys()
    )
    result = connection.execute(
        text(f"INSERT INTO projects ({names}) SELECT {names} FROM ai_script_projects")
    )
    quote = connection.dialect.identifier_preparer.quote
    # Preserve both original project tables; only application references change.
    for table in sorted(tables):
        for fk in inspector.get_foreign_keys(table):
            if fk["referred_table"] != "ai_script_projects":
                continue
            if fk["constrained_columns"] != ["project_id"] or fk["referred_columns"] != ["id"]:
                raise RuntimeError("Unexpected legacy project reference")
            constraint = quote(fk["name"])
            table_name = quote(table)
            connection.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint}"))
            options = fk.get("options", {})
            suffix = ""
            for key, sql in (("ondelete", "ON DELETE"), ("onupdate", "ON UPDATE")):
                action = options.get(key)
                if action:
                    if action not in {
                        "CASCADE",
                        "RESTRICT",
                        "NO ACTION",
                        "SET NULL",
                        "SET DEFAULT",
                    }:
                        raise RuntimeError("Unexpected foreign-key action")
                    suffix += f" {sql} {action}"
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint} "
                    f"FOREIGN KEY (project_id) REFERENCES projects(id){suffix}"
                )
            )
    config.attributes["connection"] = connection
    command.stamp(config, "0006_platform_exports")
    command.upgrade(config, "head")
    return result.rowcount


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    engine = create_engine(get_settings().sqlalchemy_database_url)
    with engine.begin() as connection:
        preserved = upgrade_legacy_database(connection, config)
    print(f"Reconciled PostgreSQL and upgraded to head; preserved {preserved} legacy projects.")


if __name__ == "__main__":
    main()

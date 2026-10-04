"""Seed one labelled prepared project into an explicitly supplied demo database.

For a standalone local demo, pass a NEW sqlite file URL plus --create-tables.
For migrated PostgreSQL, omit --create-tables. Never uses ambient DATABASE_URL.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import Base, Project, ScriptVersion  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--create-tables", action="store_true")
    parser.add_argument("--owner", default="demo-creator")
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    if args.create_tables:
        if not args.database_url.startswith("sqlite"):
            parser.error("--create-tables is only for disposable local SQLite demos.")
        Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = session.scalar(
            select(Project).where(
                Project.owner_id == args.owner, Project.name == "Prepared workflow demo"
            )
        )
        if project is None:
            project = Project(
                owner_id=args.owner,
                name="Prepared workflow demo",
                brief="Prepared sample project for demonstrating manual content workflow.",
                target_platforms=["instagram", "youtube"],
            )
            session.add(project)
            session.flush()
            version = ScriptVersion(
                project_id=project.id,
                version=1,
                origin="creator",
                content={
                    "hooks": [{"id": "hook-1", "text": "Build a repeatable content workflow."}],
                    "selected_hook_id": "hook-1",
                    "sections": [
                        {
                            "id": "section-1",
                            "position": 1,
                            "heading": "Workflow",
                            "text": "Review, approve, plan, and publish manually.",
                        }
                    ],
                    "title": "Prepared workflow demo",
                    "description": "Clearly labelled demo content.",
                    "call_to_action": "Try your next project.",
                    "production_notes": ["Prepared demo."],
                },
                input_snapshot={"provenance": "prepared_demo"},
                requirement_checks=[],
                warning_ids=[],
            )
            session.add(version)
            session.flush()
            project.current_script_version_id = version.id
            session.commit()
        print(f"Prepared demo project: /projects/{project.id}")
    engine.dispose()


if __name__ == "__main__":
    main()

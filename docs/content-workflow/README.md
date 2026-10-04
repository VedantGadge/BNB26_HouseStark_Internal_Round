# Manual content workflow backend

This is the approved option 1 backend: durable stage/checklist/review state, a prepared playable demo MP4, package metadata, per-platform planned dates, and explicit manual publication tracking. Footage/editing checkpoints are creator-confirmed. Planned dates never trigger posting. Creator self-review is not brand approval.

The workflow frontend was deliberately removed until the script, asset, editing, and export backends are complete. See [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) for the contract and future UI requirements.

## Run the backend against Neon

The current `backend/.env` is configured with a Neon PostgreSQL URL. The workflow migration has been applied to that database and verified at revision `0002_content_workflow`.

From `creatorai/backend`, run:

```bash
rtk proxy .venv/bin/alembic upgrade head
rtk proxy .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The configuration loader reads `backend/.env`; do not copy the database URL into shell history, frontend settings, or checked-in files. Keep authentication enabled unless this is a local demo configured for the isolated demo creator.

## Optional isolated SQLite demo

Run from `creatorai/backend` with installed `.venv` dependencies. Use a new disposable file path for your own demo; the seed command never reads ambient database credentials. It creates one labelled prepared project with a saved creator-authored sample script, and does not invoke an AI provider or record a fake publication.

```bash
rtk proxy .venv/bin/python scripts/seed_workflow_demo.py --database-url sqlite+pysqlite:////private/tmp/creatorai-workflow-demo.db --create-tables
rtk proxy env AUTH_REQUIRED=false DATABASE_URL=sqlite+pysqlite:////private/tmp/creatorai-workflow-demo.db .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use the OpenAPI endpoint at `http://127.0.0.1:8000/docs` or an API client to exercise the backend. Keep `AUTH_REQUIRED=false` scoped to the demo environment; owner checks still run with `demo-creator`. A real deployment requires the existing JWT configuration.

For a prepared demo in a separate disposable PostgreSQL database, explicitly pass that database URL to `seed_workflow_demo.py`, omitting `--create-tables`. The seeder never reads `DATABASE_URL` implicitly and rejects PostgreSQL with `--create-tables`. Avoid adding prepared sample data to a shared Neon database unless you intentionally want the sample project there. The migration is additive and retains existing projects/scripts.

## Backend demo sequence

1. Seed the prepared project and retrieve the printed project ID.
2. Call `GET /v1/projects/{id}/workflow`; it starts at Idea with a real saved sample ScriptVersion.
3. Send readiness/package data to `PATCH /v1/projects/{id}/workflow`, then transition one stage at a time through Assets, Editing, Review, Approved, and Exported.
4. Retrieve `GET /v1/projects/{id}/workflow/media` to confirm the prepared sample is available.
5. Create Instagram and YouTube publication plans. Dates are stored in UTC; each platform can have independent title/caption.
6. For a real manually published post, confirm with its actual past/current timestamp and HTTP(S) URL. The project becomes Published only after all target platforms are confirmed. The backend records creator confirmation; it does not independently verify a social post.
7. Retrieve the workflow after each action. Published snapshots cannot be overwritten; start a new project for another publishing cycle.

Do not publish the bundled synthetic sample unless you intend to. API tests use placeholder URLs; the live demo should stop at planned/downloaded if no real post exists.

New projects can use the existing script-generation backend when its provider, worker, and database are configured. The frontend integration is deliberately deferred; the standalone backend demo uses a prepared saved script so UI dependencies do not block testing.

## Prepared video

`backend/demo/workflow-demo.mp4` is a six-second synthetic H.264/AAC test clip, stored with the application and included in its Docker image. Preview/download goes through an owner-checked endpoint, including authenticated blob fetches when token acquisition is implemented. No arbitrary media URLs are fetched by the server. The UI identifies this sample as prepared media unrelated to project footage.

To use actual prepared footage for judging, replace this exact demo file with your intended MP4 before deployment and keep the prepared-demo label. The prototype supports one fixed demo media file; upstream Cloudinary/render integrations are outside this option.

## API and validation

Workflow endpoints are project-scoped under `/v1/projects/{id}/workflow`, with explicit transitions at `/workflow/transitions`. Publications are `/v1/projects/{id}/publications`. Every write includes `expected_revision`; stale writes return `409`. Foreign-owned resources return `404`. Invalid dates/URLs return `422`; missing prepared media returns `503`.

Focused tests cover stage prerequisites, stale writes, approval invalidation, duplicate platform plans, date conversion, publication snapshots, multi-platform completion, explicit confirmation, owner isolation, and unavailable media. Existing script/job tests remain in the suite.

```bash
rtk proxy .venv/bin/python -m pytest -q
rtk proxy .venv/bin/ruff check .
rtk proxy .venv/bin/ruff format --check .
rtk proxy .venv/bin/python scripts/export_openapi.py
```

PostgreSQL migration validation requires a disposable PostgreSQL instance; SQLite behavioral tests do not verify PostgreSQL migration/concurrency semantics.

## Recorded phase 5 validation

- Backend: 42 tests passed, including content-workflow state, validation, ownership, and idempotency coverage; Ruff check/format passed.
- Frontend: the temporary workflow implementation was removed by design; the integration contract is now documented separately.
- Browser checks previously confirmed stage progression, package save/review/approval, six-second video decoding, date save/reload, and both downloads. Those browser-only checks do not remain part of the backend deliverable.
- Migration: PostgreSQL offline SQL generation passed; `0002_content_workflow` was applied to the configured Neon PostgreSQL database and verified with a read-only query at head revision. Docker is unnecessary for this direct Neon migration.
- The browser verification did not post to a social network or confirm a fictitious live publication; confirmation behavior was verified in API tests.

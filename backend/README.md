---
title: CreatorAI API
emoji: "🎬"
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# CreatorAI API

This directory is the Hugging Face Docker Space deployment unit for the CreatorAI FastAPI API and its one-concurrent-job worker.

The container installs FFmpeg plus DejaVu fonts for caption rendering and starts both processes through `docker/start.sh`. It deliberately stores no media or durable state locally: Cloudinary owns media artifacts and Neon PostgreSQL owns application data, jobs, and LangGraph checkpoints.

Set the values from `.env.example` as Hugging Face Space secrets/variables. Keep `CLOUDINARY_API_SECRET`, database credentials, model credentials, and auth configuration server-side only. Set `CORS_ORIGINS` to the real Vercel production origin and the intended local/preview origins.

Before deploying, generate and commit a dependency lockfile appropriate for the selected Python toolchain. The direct dependencies in `pyproject.toml` are pinned; a lockfile makes transitive dependencies reproducible too.

## Local Swagger testing

For the judges' demo, set `AUTH_REQUIRED=false` only in the local `backend/.env`. This assigns all
requests the isolated `demo-creator` identity; it is not suitable for deployment. Keep
`AUTH_REQUIRED=true` when JWT configuration is ready.

Start the API from this directory:

```bash
rtk proxy .venv/bin/uvicorn app.main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to create a project, queue generation, poll the job,
and retrieve versions. Start the worker separately to process queued AI jobs:

```bash
rtk proxy .venv/bin/python -m app.worker
```

Feature persistence is isolated in `ai_script_*` PostgreSQL tables and uses its own
`ai_script_alembic_version` table, so it does not share migration state with other features in the
same database.

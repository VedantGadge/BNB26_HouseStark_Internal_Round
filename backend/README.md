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

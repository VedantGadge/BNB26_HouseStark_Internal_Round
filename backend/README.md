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

Dependencies are pinned in `uv.lock`; `requirements.lock` is its hashed runtime
export consumed by Docker. Use `uv sync --locked --extra dev` locally. After an
intentional dependency change run `uv lock` and
`uv export --frozen --no-dev --no-emit-project --output-file requirements.lock`.

## Local Swagger testing

For automatic YouTube performance import, see [YouTube analytics setup](../docs/youtube-analytics.md).

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

Every feature uses the shared `projects` table and one linear Alembic history.
The retained migration version table is `ai_script_alembic_version`. Run
`uv run alembic upgrade head` explicitly before starting the application on an
existing database; deployment and user-database migrations are not performed by QA.

The original split-history PostgreSQL database (script revision
`0002_content_workflow`, media revision `0006_platform_exports`) needs one
reconciliation before ordinary upgrades. Stop API/worker writes, then run
`rtk proxy .venv/bin/python -m scripts.upgrade_legacy_database`. This copies legacy
projects into the shared table, redirects project foreign keys, and applies the
remaining migrations in one transaction. Existing scripts, jobs, media projects,
and original legacy project rows are preserved. Conflicting IDs or unexpected
schema versions abort the transaction. Subsequent upgrades use Alembic normally.

## Backend verification

See [the audit](../docs/backend-verification.md). Dedicated local PostgreSQL tests:

```bash
rtk proxy docker compose -p creatorai-qa -f ../compose.test.yaml up -d --wait
rtk proxy env CREATORAI_TEST_DATABASE_URL=postgresql://creatorai_test:local_test_only@127.0.0.1:55432/creatorai_test uv run --extra dev pytest -q
```

These tests refuse non-local databases and create/drop only random test-owned
schemas. Real provider browser QA is explicitly enabled through
`PYTHONPATH=.:tests CREATORAI_QA_FIXTURE=1 CREATORAI_QA_LIVE=1` with
`uvicorn browser_fixture:build_app --factory --port 8011`. This entrypoint is
test-only; it is never used for production authentication.

## AI script feature demo flow

1. Create a project at `POST /v1/projects`.
2. Optionally save a creator style profile (`PUT /v1/me/style-profile`) and a campaign brief
   (`PUT /v1/projects/{project_id}/scripts/campaign-brief`).
3. Queue generation at `POST /v1/projects/{project_id}/scripts/generate` with an
   `Idempotency-Key`, then poll `GET /v1/jobs/{job_id}`.
4. Retrieve versions at `GET /v1/projects/{project_id}/scripts/versions`. Each result includes
   its immutable input snapshot, creation time, generation job reference, and requirement checks.
5. Save direct changes through `POST .../scripts/versions`, or queue a chat proposal through
   `POST .../scripts/assistant/messages`. Proposals are always review-only until Apply or Discard.

The prototype supports whole-script, hook, section, CTA, and supporting-copy proposals. New hooks
or sections submitted in a direct edit receive stable backend IDs. A brand's forbidden phrase or a
required signature-line conflict is blocked with a clear `409` response. Browser clients may use
`PUT` for the style-profile and campaign-brief forms.

## Script writer/reviewer graph

Script generation now runs a real LangGraph workflow:
writer (three hooks + script) → independent reviewer → optional single revision → requirement
validation → save the final draft for creator review. The reviewer checks brief,
brand/style fit, pacing, completeness and unsupported claims. Code checks remain
authoritative: missing literal/signature requirements trigger revision even if
the reviewer approves, and unresolved violations prevent a version being saved.
Semantic checks remain visible for creator review; AI approval never grants
project approval.

The default model is `google/gemini-3.8-flash`, with `OPENROUTER_FREE_ONLY=false`
and `OPENROUTER_REASONING_EFFORT=low`. This is a paid model; configure an OpenRouter
key with credit. Gemini 3.8 requires at least `low` thinking, so the provider maps
older `minimal` settings to `low` for this model. Local `.env` is set to these
values. Set the same variables in deployment environments; restarting the API
and worker picks up settings changes.

The default `OPENROUTER_MAX_CALLS_PER_OPERATION` is **4**, while script generation
requires at least **3**. Each script stage permits one model
request, with no internal fallback or schema-repair retry: approved drafts use
two calls; revised drafts use three. The writer produces and validates three hook
alternatives alongside the script, removing one model round trip; revisions must
preserve those hooks and section IDs. Review/provider errors fail the durable job
without saving an intermediate draft. Whole-job recovery/retry remains available;
script graph nodes do not have separate checkpoints. Older queued jobs retain
their frozen model and routing budget, so only new jobs automatically use Gemini.
Jobs with budgets below 3 require a new submission.

Jobs expose stages such as `writing_script`, `reviewing_script` and
`revising_script`. Server logs record each AI stage's elapsed time; existing
`LlmCall` rows record the model, token usage and outcome. The
[implementation and evaluation notes](../docs/script-review_IMPLEMENTATION_PLAN.md)
describe testing and a future comparison with the original two-call flow.

Real provider smoke tests are available at `tests/test_script_live.py` and run
only with `CREATORAI_QA_LIVE=1` plus the dedicated local test database. See the
[live results and reproduction command](../docs/script-live-validation.md).
The [latency comparison](../docs/script-latency-validation.md) records the Gemini
benchmark, measured costs and the combined writer optimization.

## Google Trends

Scripts can optionally use recent Google Trends topics. See
[Google Trends integration](../docs/google-trends.md) for the picker, API,
relevance matching, source snapshots, and failure behavior. No Trends API key is required.

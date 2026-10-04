# CreatorAI

CreatorAI is a web workspace for turning content ideas and source footage into scripts, grounded short-form clips, editable videos, platform exports, publication tracking, and performance insights. It supports personal content and brand campaigns, with English, Hindi, and Hinglish script generation.

Creators stay in control: AI changes are reviewable, saved versions preserve history, exports are verified, and publication is confirmed manually.

## Contents

- [Complete workflow](#complete-workflow)
- [Features and implementation](#features-and-implementation)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Testing and contracts](#testing-and-contracts)
- [Deployment and current scope](#deployment-and-current-scope)

## Complete workflow

```mermaid
flowchart TD
    A[Create project and brief] --> B[Add creator style and optional brand requirements]
    B --> C[Optionally select a Google Trends topic]
    C --> D[Generate three hooks and a script]
    D --> E[AI review and optional revision]
    E --> F[Validate requirements and save for creator review]
    F --> G[Upload source media]
    G --> H[Probe media, transcribe speech, inspect frames]
    H --> I[Match script sections to source evidence]
    I --> J[Generate clips or select a range manually]
    J --> K[Review and edit the clip]
    K --> L[Render and verify platform exports]
    L --> M[Review and approve the package]
    M --> N[Download, plan dates, and publish manually]
    N --> O[Confirm publication URL and timestamp]
    O --> P[Enter performance or sync YouTube metrics]
    P --> Q[Review insights and evidence-based explanations]
```

1. **Create a project:** enter a name, brief, audience, tone, and target platforms.
2. **Prepare context:** save optional creator style and brand requirements, select language/duration, and optionally choose a recent relevant trend.
3. **Write the script:** generate three hooks and a complete script. The AI reviewer may request one revision before requirement validation. Choose a hook, edit directly, or review an assistant proposal and explicitly apply or discard it.
4. **Upload footage:** upload video, images, or audio through a signed Cloudinary session. The backend verifies completion and queues ingestion/analysis.
5. **Find clips:** select a ready video and saved script. Match sections against timestamped speech/visual evidence, generate usable source ranges, and review the first rendered preview. Manual selection is available when evidence is insufficient.
6. **Edit and export:** adjust trim, captions, framing, title overlays, zooms, and audio. Save a new edit version, choose platform presets, and supply separate supporting copy.
7. **Approve the package:** select completed renders, play the media, confirm readiness, and explicitly approve the package. Relevant changes before publication require fresh review.
8. **Publish and track:** download media/package metadata, plan dates per platform, publish externally, and confirm each actual post with its URL and timestamp.
9. **Learn from results:** enter sourced performance observations or sync a connected YouTube channel on demand. View production metrics, comparable performance groups, and optional AI explanations.

The persisted project stages are:

```text
Idea → Assets → Editing → Review → Approved → Exported → Published
```

Script preparation happens during Idea. Stages track creator readiness and approval; processing jobs have separate statuses. The backend checks prerequisites and exposes blocking reasons. Review, Approved, and Exported can reopen into Editing. Published requires confirmation for all target platforms.

## Features and implementation

### 1. Project workspace and workflow tracking

The studio includes project creation/search and **Overview, Script, Assets, Clips, Publish, and Insights** screens. Overview shows readiness checklists, stage, blocking reasons, and recent jobs.

**Built using:** Next.js App Router and React for the interface; FastAPI, SQLAlchemy, and PostgreSQL for projects and workflow state. Writes include `expected_revision`, so stale changes return `409` instead of overwriting saved state.

**Code:** [Workspace components](frontend/components/workflow/), [project routes](backend/app/routes/projects.py), [workflow backend](backend/app/features/content_workflow/).

### 2. AI script and hook generation

Generation produces exactly three hook alternatives, a selected hook, ordered sections, a title, description, CTA, and production notes. Scripts support English, Hindi, and Hinglish and retain immutable saved versions and generation inputs.

**Built using:** OpenRouter structured generation, Pydantic/JSON Schema validation, LangGraph, and a durable PostgreSQL job queue. The graph runs **writer → independent reviewer → optional single revision → requirement validation → saved draft**. The configured default model is `google/gemini-3.8-flash`.

An approved draft uses two model calls; revision uses three. The operation budget must allow at least three calls. Each script stage permits one request. Provider/review errors or unresolved mandatory requirements prevent saving an intermediate draft. AI review does not approve publication.

**Code:** [Script backend](backend/app/features/script_creation/), [script graph](backend/app/graphs/script.py), [script interface](frontend/features/script-creation/).

### 3. Creator style, brand context, and assistant editing

Creator profiles save voice, language, pacing, structure, CTAs, avoided expressions, and signature-line inclusion/placement rules. AI can suggest a profile from writing examples for creator review.

Brand briefs save product context, approved claims, campaign goals/audience, required talking points or literal phrases, forbidden phrases, discount codes, CTA, and publishing destination. Generation freezes the selected style/campaign revisions into its input snapshot.

The assistant proposes changes to a whole script, hook, section, CTA, or supporting copy. **Apply** creates a new version; **Discard** leaves saved content intact. Direct edits also create versions. Stable section/hook IDs preserve alignment and scoped edits. A recording-read dialog provides a focused script-reading view.

**Built using:** Revisioned SQLAlchemy records, OpenRouter proposals/style suggestions, immutable snapshots, optimistic version checks, and deterministic requirement validation. Literal/signature requirements and forbidden phrases are checked in code; semantic checks remain visible for creator review. Conflicting requirements are rejected.

**Code:** [Requirements](backend/app/features/script_creation/requirements.py), [snapshots](backend/app/features/script_creation/snapshots.py), [context forms](frontend/features/script-creation/context.jsx), [assistant UI](frontend/features/script-creation/assistant.jsx).

### 4. Google Trends discovery

Creators can discover recent topics by region, using their brief/brand context or an optional focus. India is the default region, and one topic can be selected as script inspiration.

**Built using:** Google's public Trends RSS feed, HTTPX, XML parsing, a ten-minute cache, and shared-term relevance filtering. The picker considers the previous 48 hours and returns at most three suggestions. No Trends API key is required.

The backend resolves the selected topic ID and freezes its title, timestamps, and source links. Stale selections require refresh. Article titles are inspiration rather than verified facts; article contents are not fetched.

**Code:** [Trends service](backend/app/features/script_creation/trends.py), [picker](frontend/features/script-creation/trends.jsx). [Integration details](docs/google-trends.md).

### 5. Private asset library

Upload video, images, or audio, add tags, filter by media kind, preview originals, and inspect persisted processing states. Upload-session validation allows up to **100 MB** (100,000,000 bytes).

**Built using:** Cloudinary authenticated storage, signed direct browser uploads, upload progress, server-side completion verification, and durable ingestion jobs. The backend verifies the provider asset identity/version and authorized delivery type. Owner-checked endpoints provide signed playback links.

FFprobe inspects temporary source files for dimensions, duration, codecs, and audio. Originals stay in Cloudinary; PostgreSQL stores references and metadata.

**Code:** [Asset backend](backend/app/features/assets/), [upload client](frontend/lib/upload.js), [ingestion](backend/app/features/footage_analysis/ingestion.py).

### 6. Footage understanding and source alignment

Video analysis saves timestamped transcript segments and frame descriptions. Audio assets receive transcripts. Evidence can be inspected and used to seek the source player. Script sections are marked **matched**, **partial**, or **unmatched**, with confidence and supporting evidence.

**Built using:** Groq transcription (`whisper-large-v3-turbo` by default), Groq vision (`qwen/qwen3.8-27b` by default), FFmpeg media preparation, and OpenRouter semantic matching. Frame sampling is bounded/configurable; silent videos skip transcription. Images remain library assets rather than entering the video analysis pipeline.

The alignment model selects existing evidence IDs; backend timestamps come from saved evidence. Weak or wholly unmatched results can trigger one bounded extra frame-inspection pass. Unsupported sections remain unmatched.

**Code:** [Footage analysis](backend/app/features/footage_analysis/), [script alignment](backend/app/features/script_alignment/).

### 7. Grounded clips and manual source selection

The connected workflow defaults to up to three candidates from a ready video and saved script. Each candidate retains its source range, evidence, confidence, and rationale. Initial edit versions are saved, a preview is rendered for the first candidate, and the workflow pauses for creator selection.

**Built using:** Semantic alignment followed by deterministic confidence ranking, source-bound/duration checks, overlap rejection, candidate reuse, and a LangGraph review interrupt with PostgreSQL checkpoints. Waiting for review releases the worker. Manual selection creates a clip from a creator-chosen range when grounding is insufficient.

Historical edits remain intact, and script-linked candidates can be marked stale. Scores represent evidence confidence rather than predicted virality.

**Code:** [Clip generation](backend/app/features/clip_generation/), [connected media workflow](backend/app/features/media_workflow/), [review graph](backend/app/graphs/repurpose.py).

### 8. Versioned video editing and previews

The editor supports trim, normalized crop position, crop/pad fitting, editable captions/timing, caption toggles, timed title overlays, up to two emphasis zooms, and audio normalization/fades. Caption styles are `clean`, `bold`, and `bold_highlight`.

**Built using:** React draft state, Remotion Player previews, validated edit recipes, immutable `EditVersion` records, and base-version checks. Script/editor drafts use session storage for recovery and preserve unsaved changes when polling finds a newer saved version.

Current recipes contain one contiguous source range of **2–60 seconds**, with up to 20 captions. Trim uses source timestamps; captions, titles, and zooms use output time. Browser previews approximate the recipe; the verified backend render is authoritative.

**Code:** [Editor UI](frontend/components/workflow/editor.jsx), [Remotion preview](frontend/components/remotion/recipe-player.jsx), [draft recovery](frontend/lib/use-versioned-draft.js), [editing backend](backend/app/features/editing/).

### 9. Platform adaptation and verified exports

Exports retain an immutable recipe/preset snapshot and independent title, caption, and hashtags. Presets set canvas dimensions and overlay safe zones, with crop/pad options.

| Preset | Platform | Resolution | Ratio |
| --- | --- | --- | --- |
| `instagram_reel` | Instagram | 1080 × 1920 | 9:16 |
| `tiktok` | TikTok | 1080 × 1920 | 9:16 |
| `youtube_short` | YouTube | 1080 × 1920 | 9:16 |
| `instagram_feed` | Instagram | 1080 × 1080 | 1:1 |
| `linkedin_feed` | LinkedIn | 1080 × 1080 | 1:1 |
| `youtube_video` | YouTube | 1920 × 1080 | 16:9 |

Generic `vertical`, `square`, and `landscape` aliases are also available through the connected API. The YouTube Video preset changes the canvas; edit duration remains capped at 60 seconds.

**Built using:** Controlled Python compilation into FFmpeg commands, durable export jobs, FFprobe verification, and authenticated Cloudinary uploads. Verification checks output dimensions/duration, video streams, and source-audio preservation. Completion is recorded after verification and storage succeed; retries reuse completed job artifacts.

**Code:** [Renderer](backend/app/features/editing/renderer.py), [render service](backend/app/features/editing/render_service.py), [platform exports](backend/app/features/platform_exports/).

### 10. Package approval and publication tracking

Publish collects completed renders, package copy, readiness confirmations, and an explicit approval snapshot. Creators download media/package JSON, plan dates and copy per platform, then confirm actual posts with their URL and past/current timestamp.

**Built using:** A persisted state machine, optimistic revisions, owner-checked render validation, UTC dates, and immutable package/publication snapshots. Relevant changes before publication invalidate approval. All target platforms must be confirmed to complete the project.

Planned dates do not trigger posting. Confirmation records the creator's report rather than independently verifying a post. Creator self-review is separate from external brand approval.

**Code:** [Publish UI](frontend/components/workflow/publish.jsx), [workflow backend](backend/app/features/content_workflow/).

### 11. Production insights and YouTube analytics

Production metrics include completed projects, processed source minutes, clip count, completed exports, clips per video source, revision count, and median upload-to-export time. Manual performance records include source attribution, observation time/window, views, optional engagement counts, and optional retention.

**Built using:** SQLAlchemy aggregation and cumulative performance snapshots. Insights selects the latest observation per publication/window/reporting basis and compares within platform/window/basis groups. Missing metrics remain unknown. With positive views and complete counts:

```text
engagement rate = (likes + comments + shares) / views
```

The API also supports creator-wide comparisons across owned projects. Optional OpenRouter explanations run as jobs and validate their saved evidence references.

**YouTube sync:** Read-only Google OAuth plus YouTube Data/Analytics APIs import views, likes, comments, and shares on demand. Each creator connects one channel; videos must belong to it. OAuth state is creator/browser-bound and expires, while refresh tokens are encrypted with Fernet. Reports exclude today's incomplete day, preserve actual returned windows, and leave retention unknown. Manual and YouTube calendar reporting bases stay separate.

**Code:** [Insights service](backend/app/features/media_workflow/insights.py), [YouTube integration](backend/app/features/youtube/), [Insights UI](frontend/components/workflow/insights.jsx). [YouTube setup](docs/youtube-analytics.md).

### 12. Responsive interface and landing experience

The frontend includes illustrative workflow previews, light/dark themes, responsive layouts, keyboard-focused dialogs, loading/empty/error states, and reduced-motion handling.

**Built using:** React, CSS/Tailwind tooling, Radix Dialog, Phosphor icons, GSAP, Motion, and Remotion preview compositions. Landing examples are labelled illustrative and do not run the actual production pipeline.

**Code:** [Landing components](frontend/components/landing/), [UI components](frontend/components/ui/), [design system](DESIGN.md).

## Technology stack

| Layer | Technologies | Purpose |
| --- | --- | --- |
| Web application | Next.js 16, React 19, JavaScript/JSX | Routes, studio, forms, editor, landing |
| UI and animation | CSS/Tailwind CSS 4 tooling, Radix, Phosphor, GSAP, Motion | Styling, dialogs, icons, animation |
| Client data | TanStack Query, Fetch API | Queries, mutations, caching, job polling |
| Video previews | Remotion Player/media packages | Interactive recipe previews |
| API | Python 3.12+, FastAPI, Uvicorn, Pydantic | HTTP routes, schemas, configuration |
| Database | Neon/PostgreSQL, SQLAlchemy, Psycopg 3, Alembic | Application state and migrations |
| Workflows | LangGraph, PostgreSQL checkpoint saver | Script graph and resumable clip review |
| Text AI | OpenRouter | Scripts/review, proposals, style, alignment, explanations |
| Speech/vision | Groq | Timestamped transcription and frame observations |
| Storage | Cloudinary | Authenticated sources and rendered artifacts |
| Media processing | FFmpeg, FFprobe, imageio-ffmpeg | Probe, frame/audio preparation, render, verification |
| Trends | Google Trends RSS, HTTPX | Optional recent-topic discovery |
| YouTube | Google OAuth, Data/Analytics APIs, Fernet | Read-only metrics and encrypted tokens |
| Authentication | JWT bearer tokens, PyJWT, JWKS | Signature/issuer/audience checks |
| Quality checks | pytest, Ruff, Node tests, Playwright, axe, Prettier | API/media/client/browser checks |
| Hosting targets | Vercel, Hugging Face Docker Space | Frontend; API and worker |

Exact dependency versions are in the package manifests and lockfiles. Model IDs above describe repository defaults and are configurable.

## Architecture

```mermaid
flowchart LR
    Web[Next.js studio] -->|HTTP /v1| API[FastAPI]
    Web -->|Signed direct upload| Media[Cloudinary]
    API -->|Records and jobs| DB[(PostgreSQL / Neon)]
    API -->|Signed delivery links| Media
    Worker[Python worker] -->|Claim jobs and persist results| DB
    Worker -->|Checkpoints| DB
    Worker --> Text[OpenRouter]
    Worker --> Analysis[Groq]
    Worker --> Render[FFmpeg / FFprobe]
    Worker -->|Sources and artifacts| Media
    API --> Trends[Google Trends RSS]
    API --> YouTube[Google OAuth / YouTube APIs]
```

The API persists expensive operations as jobs, and a separately running worker processes one job at a time. PostgreSQL stores inputs, model-routing snapshots, queue state, attempts, and results. Atomic claims use `FOR UPDATE SKIP LOCKED`; expired leases can be recovered and failed jobs explicitly retried. Redis/Celery are not required.

Queued requests carry `Idempotency-Key`: repeating an accepted request reuses the operation; changed inputs with the same key conflict. Clip review pauses/resumes through persistent LangGraph checkpoints. Script generation runs a bounded graph inside its durable job without individual node checkpoints.

Workers use temporary files for processing. Cloudinary stores originals/exports, while PostgreSQL stores metadata and application state. Immutable versions and publication snapshots connect requested inputs, edits, renders, and published packages. Backend ownership checks protect project resources.

## Repository structure

```text
creatorai/
├── frontend/
│   ├── app/                  # Landing, projects, studio, YouTube callback routes
│   ├── components/           # Workspace, editor, UI, landing, Remotion previews
│   ├── features/             # Script creation, context, assistant, trends
│   ├── lib/                  # API/auth, uploads, draft recovery
│   └── tests/                # Client and browser checks
├── backend/
│   ├── app/features/         # Script, assets, analysis, alignment, clips, editing,
│   │                         # exports, workflow, insights, YouTube
│   ├── app/graphs/           # Script and clip-review workflows
│   ├── app/routes/           # Shared API routes
│   ├── app/worker.py         # Durable single-concurrency worker
│   ├── alembic/              # Database migrations
│   ├── scripts/              # OpenAPI export and QA/demo helpers
│   ├── tests/                # Service, API, database, media/provider tests
│   ├── docker/start.sh       # API + worker container startup
│   └── demo/                 # Labelled prepared synthetic media
├── contracts/                # OpenAPI snapshot and API fixtures
├── docs/                     # Integration guides and recorded verification
├── compose.yaml              # Local frontend and API/worker containers
├── compose.test.yaml         # Dedicated local PostgreSQL test database
├── DESIGN.md
└── PRODUCT.md
```

## Local setup

### Prerequisites

- Node.js **22+**, npm, Python **3.12+**, and **uv**.
- System FFmpeg and FFprobe; rendering needs caption filters/fonts. `FFMPEG_BINARY` can select a full FFmpeg executable.
- PostgreSQL/Neon for the complete durable workflow.
- Cloudinary, OpenRouter, and Groq credentials for real media/AI operations.
- Optional Google OAuth configuration for YouTube metrics; optional Docker for containers/database tests.

From the `creatorai` repository root:

```bash
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
npm --prefix frontend ci
cd backend
uv sync --locked --extra dev
```

Fill `backend/.env` with database/provider settings. For a local demo without an identity provider, use `AUTH_REQUIRED=false` with `ENVIRONMENT=development`; requests share the `demo-creator` identity. Production requires JWT verification.

Apply migrations from `backend/` before first use:

```bash
uv run alembic upgrade head
```

This targets the database configured in `backend/.env`; use your intended development database.

Run these in **three separate terminals**, each starting at the repository root:

```bash
# Terminal 1: frontend
npm --prefix frontend run dev

# Terminal 2: API
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 3: worker
cd backend
uv run python -m app.worker
```

| Service | URL |
| --- | --- |
| Web app | <http://localhost:3000> |
| API health | <http://localhost:8000/health> |
| Swagger | <http://localhost:8000/docs> |
| Live OpenAPI | <http://localhost:8000/openapi.json> |

The API does not start a worker automatically in this setup. Queued jobs wait until the worker runs. `/health` checks API liveness rather than database/provider readiness.

For Docker, configure the environment and apply migrations using the local backend environment, then run from the repository root:

```bash
docker compose up --build
```

The API container starts both API and worker. Compose exposes ports 8000/3000 but does not create the application database or apply migrations. Its database URL must be reachable from inside Docker.

## Configuration

Use [backend/.env.example](backend/.env.example) and [frontend/.env.local.example](frontend/.env.local.example). Provider secrets and database credentials stay server-side.

| Variables | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` (frontend) | Backend origin, e.g. `http://localhost:8000`, without `/v1` |
| `DATABASE_URL` | PostgreSQL application/jobs/checkpoint connection |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Media upload, verification, delivery, storage |
| `OPENROUTER_API_KEY`, `OPENROUTER_DEFAULT_MODEL`, `OPENROUTER_FALLBACK_MODELS` | Text AI credentials/model routing |
| `OPENROUTER_FREE_ONLY`, `OPENROUTER_REQUIRE_STRUCTURED_OUTPUT` | Routing and response policy |
| `OPENROUTER_MAX_CALLS_PER_OPERATION`, `OPENROUTER_MAX_OUTPUT_TOKENS`, `OPENROUTER_REASONING_EFFORT`, `OPENROUTER_TIMEOUT_SECONDS` | Bounded generation settings |
| `GROQ_API_KEY`, `GROQ_TRANSCRIPTION_MODEL`, `GROQ_VISION_MODEL` | Transcription and vision |
| `GROQ_VISION_SAMPLE_INTERVAL_SECONDS`, `GROQ_VISION_MAX_FRAMES`, `GROQ_VISION_MAX_COMPLETION_TOKENS` | Sampling/response limits |
| `AUTH_REQUIRED`, `AUTH_JWKS_URL`, `AUTH_AUDIENCE`, `AUTH_ISSUER` | JWT identity verification |
| `CORS_ORIGINS`, `ENVIRONMENT`, `API_PREFIX` | Allowed origins and runtime settings |
| `WORKER_POLL_INTERVAL_SECONDS`, `WORKER_LEASE_SECONDS` | Queue polling/lease settings |
| `FFMPEG_BINARY`, `EDIT_RENDER_TIMEOUT_SECONDS` | Render executable/timeout |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REDIRECT_URI`, `YOUTUBE_TOKEN_ENCRYPTION_KEY` | Optional read-only OAuth/metrics |

Text defaults are `OPENROUTER_FREE_ONLY=false`, an 8,192-token output budget, `low` reasoning, and a four-call operation budget. Configure provider access/credit for the selected model. New jobs freeze their routing; restarting with changed settings does not rewrite older jobs.

The frontend adds `/v1` to its API origin. Keep the backend prefix at `/v1` unless updating the client. Production session-provider integration is unfinished: [auth.js](frontend/lib/auth.js) currently reads an existing bearer token from `sessionStorage` under `creatorai-token`.

YouTube requires enabled Data API v3/Analytics API, an exact registered frontend callback URL, and a persistent Fernet key. Follow [the YouTube setup guide](docs/youtube-analytics.md).

## API overview

Paths use `/v1`. Swagger and [the OpenAPI snapshot](contracts/openapi.json) contain complete schemas.

| Area | Main endpoints |
| --- | --- |
| Projects | `GET/POST /v1/projects`; `GET/PATCH /v1/projects/{project_id}` |
| Style/context | `GET/PUT /v1/me/style-profile`; `GET/PUT /v1/projects/{project_id}/scripts/campaign-brief` |
| Scripts | `POST .../scripts/generate`; `GET/POST .../scripts/versions`; `GET .../scripts/trends` |
| Assistant | `POST .../scripts/assistant/messages`; proposal `/apply` and `/discard` endpoints |
| Uploads | `POST /v1/projects/{project_id}/assets/upload-session`; `POST /v1/assets/{asset_id}/complete` |
| Evidence | `GET /v1/assets/{asset_id}/analysis`; `GET /v1/assets/{asset_id}/delivery` |
| Clips | `POST /v1/projects/{project_id}/clips/generate` or `/manual`; `GET .../clips` |
| Editing | `GET/POST /v1/clip-candidates/{candidate_id}/edit-versions` |
| Exports | `POST /v1/clips/{clip_id}/exports`; `POST /v1/edit-versions/{version_id}/platform-exports` |
| Delivery | `GET /v1/projects/{project_id}/exports`; `GET /v1/exports/{render_id}/delivery` |
| Jobs | `GET /v1/jobs/{job_id}`; `POST /v1/jobs/{job_id}/retry` or `/review` |
| Workflow | `GET/PATCH .../workflow`; `POST .../workflow/transitions` |
| Publications | `GET/POST /v1/projects/{project_id}/publications`; `PATCH .../publications/{publication_id}` |
| Insights | `GET /v1/projects/{project_id}/insights`; `GET /v1/me/insights`; `POST .../insights/summarize` |
| Performance | `POST /v1/publications/{publication_id}/performance` or `/performance/youtube` |
| YouTube | `GET/DELETE /v1/me/youtube`; `POST /v1/me/youtube/authorize` or `/callback` |

Most queued AI/export submissions return `202` with a job ID and require `Idempotency-Key`. Poll jobs for status/stage/results; resume clip-review jobs with a selected edit version. Authenticated requests include `Authorization: Bearer <access-token>`.

## Testing and contracts

From `backend/`:

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check app tests scripts
uv run --extra dev ruff format --check app tests scripts
```

Tests cover schemas, ownership, persistence, queues/idempotency, script review, uploads, analysis/alignment, clips, editing, FFmpeg output, presets, workflow/publications, trends, and YouTube reporting. Provider fixtures and opt-in live-provider checks are separate.

For dedicated local PostgreSQL migration/concurrency/checkpoint checks, start from the repository root:

```bash
docker compose -p creatorai-qa -f compose.test.yaml up -d --wait
cd backend
CREATORAI_TEST_DATABASE_URL=postgresql://creatorai_test:local_test_only@127.0.0.1:55432/creatorai_test uv run --extra dev pytest -q
```

These tests use random test-owned schemas in the dedicated local database. Live provider checks need explicit `CREATORAI_QA_LIVE=1` configuration; see the validation documents below.

From `frontend/`:

```bash
npm test
npm run build
npm run test:e2e
npm run format:check
```

Browser tests expect a preview at `http://127.0.0.1:3001`, overridable with `CREATORAI_E2E_URL`. Set `CREATORAI_E2E_PROJECT_ID` to an isolated QA project for connected checks; otherwise those checks are skipped. Chrome must be installed.

FastAPI is the contract source of truth. After route/schema changes, run from `backend/`:

```bash
uv run python scripts/export_openapi.py
```

Commit the refreshed `contracts/openapi.json` and affected fixtures alongside the implementation. See [contract documentation](contracts/README.md).

## Deployment and current scope

The deployment targets are **Vercel** for `frontend/` and a **Hugging Face Docker Space** for `backend/`. Configure the frontend API origin and backend CORS origins. The backend image installs locked dependencies, system FFmpeg/FFprobe, and DejaVu fonts, then starts the API and worker on container port 7860. Apply migrations separately before startup. Neon/PostgreSQL and Cloudinary provide persistent state/media; container disk is temporary.

Production requires configured JWT issuer/audience/JWKS and `AUTH_REQUIRED=true`. YouTube configuration is optional. See [backend deployment details](backend/README.md).

Current boundaries:

- This is a connected hackathon prototype; recorded checks are not a production-readiness or content-quality certification.
- Posting is manual. YouTube OAuth imports read-only analytics; Instagram/TikTok/LinkedIn metrics use manual observations.
- Editing uses one source video and contiguous range per recipe. Multitrack editing, automatic face tracking, and in-app recording are outside the implementation.
- Script targets allow 15–300 seconds; video edits are 2–60 seconds. Available evidence determines clip count, so three clips are not guaranteed.
- Trends uses shared-term discovery, and vision uses bounded frame samples. Neither provides exhaustive verification of content.
- Production login/session integration, team collaboration, and billing are unfinished/out of scope.
- Remotion previews and labelled landing/demo content are separate from verified exports. Bundled synthetic demo media does not prove a project's footage was processed.
- Performance comparisons show observed associations, preserve unknown values, and do not promise growth or establish causation.

## Further documentation

| Document | Coverage |
| --- | --- |
| [Frontend README](frontend/README.md) | Frontend commands and browser setup |
| [Backend README](backend/README.md) | Runtime, deployment, script graph, dependency locks |
| [Build plan](docs/creatorai-build-plan.md) | Workflow and architectural context |
| [Google Trends](docs/google-trends.md) | Discovery, attribution, snapshots, failures |
| [YouTube analytics](docs/youtube-analytics.md) | OAuth, encryption, reporting semantics |
| [Backend verification](docs/backend-verification.md) | Recorded integration/live checks |
| [Frontend verification](docs/frontend-verification.md) | Recorded responsive/accessibility/playback checks |
| [Script live validation](docs/script-live-validation.md) | Real-provider verification |
| [Script latency validation](docs/script-latency-validation.md) | Recorded latency/model-call comparisons |
| [Script integration guide](docs/ai-script-hooks/FRONTEND_INTEGRATION_GUIDE.md) | Script/style/assistant contracts |
| [Workflow integration guide](docs/content-workflow/FRONTEND_INTEGRATION_GUIDE.md) | Package review/publication contracts |

Some older plans describe standalone milestones. Current code and generated OpenAPI define the connected behavior described here.

# CreatorAI — Person B implementation guide

## Mission and ownership

Person B owns the complete, grounded media path:

```text
Asset upload → footage analysis → clip suggestions → editable recipe
→ FFmpeg render → platform-specific exports
```

The objective is not an open-ended video editor. It is a small, reliable demo that turns a real creator-uploaded video into several evidence-backed short-form clips. A creator must be able to review a proposed clip, change its trim/captions/crop, save a new immutable version, and export vertical and square variants.

The eight-feature product plan is in [creatorai-build-plan.md](./creatorai-build-plan.md). This document turns Person B's assigned features into an executable implementation order and integration boundary.

### Features owned by Person B

1. Asset management
2. Script-to-video understanding
3. Automated clip generation
4. AI-assisted editable editing
5. Multi-platform adaptation

### Current backend implementation status

| Person B feature | Status | What is implemented and verified |
|---|---|---|
| 1. Asset management | Complete | Owner-scoped signed Cloudinary uploads, provider-side completion verification, Neon asset records, private downloads, and FFprobe ingestion. |
| 2. Script-to-video understanding | Complete | Groq timestamped transcription, bounded frame observations, persisted evidence, and source-grounded script alignment. |
| 3. Automated clip generation | Complete | Ranked, duration-bounded, non-overlapping candidate ranges with transcript evidence, persisted in Neon and available through create/list APIs. |
| 4. AI-assisted editable editing | Complete for the agreed backend scope | Immutable recipe versions, trim, normalized crop coordinates, three caption styles, timed hook title, up to two emphasis zooms, loudness normalization, audio fades, FFmpeg verification, and restricted Cloudinary render upload. |
| 5. Multi-platform adaptation | Complete for the agreed backend scope | Platform-safe immutable recipe snapshots, supporting copy/hashtag metadata, and verified Cloudinary MP4 exports for vertical, square, and landscape presets. |

Feature 4 lives in `backend/app/features/editing/`. Its public backend contract is:

- `POST /v1/clip-candidates/{candidate_id}/edit-versions` creates an assistant-seeded
  first version or a creator-edited immutable successor.
- `GET /v1/clip-candidates/{candidate_id}/edit-versions` lists version history.
- `GET /v1/edit-versions/{version_id}` returns one immutable recipe.
- `POST /v1/edit-versions/{version_id}/render` renders, probes, uploads, and persists
  one authenticated `1080×1920` MP4 artifact.
- `POST /v1/edit-versions/{version_id}/platform-exports` derives, renders, and
  persists one platform-specific export from the immutable version.
- `GET /v1/edit-versions/{version_id}/platform-exports` lists a version's exports;
  `GET /v1/platform-exports/{export_id}` loads one export for Person A's publishing flow.

Real-video acceptance testing completed with the project MP4: a 3:59 `1280×720`
source was transcribed into 70 segments, used to create a grounded candidate, saved
as two immutable recipe revisions, and rendered as a verified 8-second
`1080×1920` MP4. Temporary Neon records and both temporary Cloudinary videos were
removed after the test.

Platform-export acceptance testing then created and verified an `1080×1080`
Instagram Feed export and a `1920×1080` YouTube landscape export from that same
immutable edit version. Each variant retains its platform preset, derived recipe,
supporting copy, hashtags, provider identity, and probed output metadata. Temporary
Cloudinary and Neon data was removed after this second test as well.

### Person A dependency: durable jobs are currently a placeholder

Person A owns durable job persistence, status, retries, and worker claiming. This
repository currently contains only placeholders for that shared foundation:

- `backend/app/routes/jobs.py` returns `501 Not Implemented` for job lookup.
- `backend/app/worker.py` starts a polling loop but does not claim or execute a
  persisted job.

Because that dependency is not available yet, Feature 4's render endpoint invokes
`render_edit_version` synchronously and persists its own render status. This is a
development bridge, not the final production execution model.

When Person A implements the shared job foundation, they should provide an
owner-scoped enqueue/claim/retry contract with `queued`, `running`, `completed`, and
`failed` states. Person B will then change the render endpoint to return `202` and a
shared `job_id`; Person A's worker will call the existing `render_edit_version`
service. The recipe schema, FFmpeg command builder, Cloudinary upload, verification,
and edit-version APIs remain unchanged.

Person B does **not** own authentication, projects, script/hook generation, workflow/publishing states, job persistence/status/retry, or creator intelligence. Those are Person A's responsibility. Person B may add data and APIs needed by the media path, but must consume Person A's owner-scoped project, script-version, job, and authentication interfaces rather than reimplementing them.

## Demo definition of done

Use one real 2–5 minute video as the main source. The source remains immutable.

- A creator uploads a video, image, or audio asset to a selected project and sees its processing state and metadata.
- A completed source video has a timestamped transcript and bounded visual observations.
- At least one script section demonstrably links to a source-video range with transcript and visual evidence. Unmatched sections must be shown as unmatched rather than fabricated.
- The system offers three valid short-clip proposals, each with a source range, reason, evidence, and preview/status.
- A creator changes trim values and a caption or crop position, saves the edit, reloads it, and can revert to the latest saved edit.
- The system creates a real MP4 vertical export (`1080×1920`) and square export (`1080×1080`) from a selected immutable edit version. Each export retains its own supporting metadata.

Do not spend the limited hackathon time on browser recording, social OAuth/posting, multitrack editing, automatic face tracking, a generic AI editing chat, or a complex timeline UI.

## System flow and boundaries

```mermaid
sequenceDiagram
    participant C as Creator / Next.js
    participant A as FastAPI
    participant S as Cloudinary
    participant D as Neon PostgreSQL
    participant W as Persisted worker
    participant P as Speech / vision providers
    participant F as FFmpeg / ffprobe

    C->>A: request upload session (authenticated project)
    A->>A: authorize owner and sign controlled upload parameters
    A-->>C: upload session; no provider secret
    C->>S: direct media upload
    C->>A: upload completion metadata
    A->>D: save asset; enqueue ingestion job
    W->>D: atomically claim job
    W->>S: download authorized source
    W->>F: probe media / create scratch artifacts
    W->>P: transcribe and inspect bounded frame samples
    W->>D: save analysis, alignments, candidates, recipes
    C->>A: poll job, inspect candidates, save edit version
    C->>A: request export preset
    W->>F: render from immutable recipe
    W->>S: upload final MP4
    W->>D: save export only after upload succeeds
```

### Non-negotiable storage rules

- **Cloudinary:** original media, proxies/previews, and final export bytes. Keep originals private/authenticated.
- **Neon:** all IDs, ownership, media metadata, transcripts, observations, alignments, recipes, exports, and jobs. Store references to media, never media bytes.
- **Hugging Face local disk:** temporary worker scratch space only. It is disposable and must not be the source of truth.
- **Browser:** UI state and active upload/render progress only. It does not own an edit or determine resource ownership.

## Folder responsibilities

Keep feature-specific code in the repository structure already established. Do not put provider calls, FFmpeg commands, or database query logic in Next.js pages.

### Backend feature-folder rule

Person B backend code is organized by business capability, not by technical type. Add a new route, schema, model, service, and test beside its feature whenever they change together. Shared infrastructure stays outside feature folders because Person A owns or integrates it.

- `app/features/assets/` owns asset records, Cloudinary operations, upload APIs, and owner-scoped asset access.
- `app/features/footage_analysis/` owns FFprobe inspection, ingestion, transcript/visual evidence models, provider contracts, persistence, and analysis APIs.
- Implemented Person B capabilities use `app/features/clip_generation/`,
  `app/features/editing/`, and `app/features/platform_exports/`.
- `app/database.py`, `app/config.py`, `app/dependencies.py`, `app/models.py`, and `app/schemas.py` remain shared compatibility/foundation modules. Do not move Person A's projects, auth, jobs, scripts, publications, or insights into Person B folders.
- Legacy `app/routes/assets.py` and `app/services/*.py` are compatibility re-exports only. New Person B code must import from `app.features/...` directly.

```text
frontend/
  app/projects/[projectId]/assets/page.jsx       # route composition for asset screen
  app/projects/[projectId]/clips/page.jsx        # proposal list route composition
  app/projects/[projectId]/clips/[clipId]/page.jsx # editor route composition
  components/uploads/                            # upload queue, asset cards, filters, player
  components/clips/                              # proposal cards, evidence, job-state UI
  components/editor/                             # trim, caption, crop, presets, save/revert
  lib/api.js                                     # typed/request helpers to FastAPI only
  lib/auth.js                                    # token retrieval supplied by Person A's auth choice

backend/
  app/database.py                                # shared SQLAlchemy metadata, engine, sessions
  app/dependencies.py                            # temporary dev identity; Person A swaps JWT claims
  app/features/
    assets/                                      # models, schemas, Cloudinary storage, upload APIs
    footage_analysis/                            # probe, ingestion, evidence models, analysis APIs
    clip_generation/                             # create when grounded candidate work starts
    editing/                                     # create when versioned recipes start
    platform_exports/                            # create when FFmpeg export work starts
  app/routes/                                    # Person A/shared routers and compatibility shims
  app/services/                                  # compatibility imports; no new Person B implementation
  app/graphs/repurpose.py                        # analysis → candidates → review → export graph
  app/worker.py                                  # dispatches Person B media jobs; Person A owns queue core
  app/models.py                                  # shared model exports and Person A Project model
  app/schemas.py                                 # shared schema exports and Person A contracts
  alembic/versions/                              # migration generated after model agreement

contracts/
  openapi.json                                   # generated from FastAPI; never hand-edit
  fixtures/                                      # representative API payloads for UI/tests
```

Recommended supporting modules, if they become necessary, are `backend/app/repositories/` for owner-scoped asset/clip/export queries and `backend/app/db.py` for SQLAlchemy session setup. Agree on those shared additions with Person A before creating them.

## Data contract Person B needs

Person A provides these reliable inputs:

| Dependency | Required behavior |
|---|---|
| Auth dependency | Provides authenticated `owner_id`; never trust owner or project IDs posted by the browser. |
| Project repository/API | Fetches an owned project and its workflow stage. |
| Script versions | Provides an immutable selected script version with stable ordered section IDs and text. |
| Jobs | Persists `queued/running/waiting_review/completed/failed/cancelled`, claims atomically, retries safely, and supports polling. |
| Job enqueue function | Returns `202` and a `job_id`; worker progress is independent of a browser session. |
| Shared configuration | Database, Cloudinary, model configuration, CORS, and OpenAPI export workflow. |

Person B returns/creates:

| Entity | Minimum fields and purpose |
|---|---|
| `Asset` | project/owner, kind, Cloudinary IDs/version/type, format, bytes, dimensions/duration, tags, processing state |
| `TranscriptSegment` | asset, source start/end ms, text, optional word timings |
| `VisualObservation` | asset, timestamp/range, sampled-frame references, description, confidence |
| `ScriptAlignment` | script version/section, asset/ranges, transcript + visual evidence, confidence, match state |
| `Clip` | project, title, proposal reason, evidence references, selected/current edit version |
| `EditVersion` | clip, parent version, author type, schema version, immutable recipe JSON |
| `Export` | edit version, preset, metadata snapshot, Cloudinary IDs, status, render job |

All Person B reads and writes must be owner-scoped through the project. A Cloudinary URL is a delivery location, not a permission check or canonical media identity.

## API surface to implement

Use `/v1` contracts and Pydantic schemas. The exact router nesting should match Person A's route registration; avoid duplicate routes. The intended resource behavior is:

| Endpoint | Owner | Behavior |
|---|---|---|
| `POST /v1/projects/{project_id}/assets/upload-session` | B | Verify owner/project; return controlled Cloudinary upload parameters and signature. |
| `POST /v1/assets/{asset_id}/complete` | B | Verify provider completion; save asset metadata; enqueue ingestion. |
| `GET /v1/projects/{project_id}/assets` | B | List owned assets with filtering and processing/analysis status. |
| `GET /v1/assets/{asset_id}/analysis` | B | Return transcript, observations, and script alignments. |
| `POST /v1/projects/{project_id}/clips/generate` | B | Validate source/script versions and enqueue repurpose job. |
| `GET /v1/projects/{project_id}/clips` | B | Return proposals, evidence, preview/export state. |
| `GET /v1/clips/{clip_id}` | B | Return owned clip plus current recipe and version history. |
| `POST /v1/clips/{clip_id}/edit-versions` | B | Validate optimistic base version and save a new immutable edit recipe. |
| `POST /v1/jobs/{job_id}/review` | shared | Person B validates selected edit; Person A safely queues graph resume. |
| `POST /v1/clips/{clip_id}/exports` | B | Enqueue a requested preset for a selected immutable edit version. |
| `GET /v1/jobs/{job_id}` / `POST /v1/jobs/{job_id}/retry` | A | Status/retry infrastructure consumed by Person B UI. |

Every long-running ingestion, analysis, preview, and render response must return `202` with a job ID. Frontend polling belongs in TanStack Query and should stop when a terminal status is reached.

After route or schema changes, regenerate the checked-in contract:

```bash
backend/.venv/bin/python backend/scripts/export_openapi.py
```

Also update or add fixtures under `contracts/fixtures/` for any payload consumed by the UI.

## The editable recipe is the source of edit truth

The UI may preview a simple source segment in the browser, but a browser overlay is not proof that the final export is correct. The recipe below is the authoritative contract for both the editor and FFmpeg renderer:

```json
{
  "schema_version": 1,
  "source_asset_id": "asset_123",
  "segments": [
    {"id": "cut_1", "source_start_ms": 42000, "source_end_ms": 57000}
  ],
  "output": {"width": 1080, "height": 1920, "fit": "crop"},
  "crop": {"center_x": 0.55, "center_y": 0.5},
  "captions": [
    {"start_ms": 0, "end_ms": 2200, "text": "Your editable opening caption"}
  ]
}
```

Rules:

- Segment timestamps use the **source** clock; captions/overlays use the **assembled output** clock.
- Validate `0 <= start < end <= source duration`, usable total duration, and no duplicate candidate range before saving or rendering.
- When a trim changes, remap/rebuild caption output timings. Do not silently leave captions at stale positions.
- Crop coordinates are normalized `0..1` and must be clamped to the requested aspect ratio.
- A save creates a new `EditVersion`; it never overwrites source media or a prior approved/exported version.
- Use optimistic concurrency: reject a save made against a stale current edit version instead of overwriting a teammate/user change.
- FFmpeg arguments are assembled by controlled Python code. Never execute a provider/LLM-generated command.

Start with one contiguous segment per proposed clip. The recipe can permit multiple segments later, but do not delay the demo for a multisegment timeline.

## Implementation sequence

### 0. Agree the shared foundation before feature coding

Meet Person A briefly and lock these contracts: authenticated owner dependency, project lookup, SQLAlchemy session/repository pattern, job enqueue/claim API, script-version shape, error envelope, and job stage names. Confirm a demo source video, Cloudinary/Neon credentials, configured FFmpeg, and the selected transcription/vision provider.

Do not create a separate queue, auth system, or database connection pattern for media work.

### 1. Assets and durable media records

1. Add `Asset` and minimal analysis-related models/migration in coordination with Person A.
2. Implement a Cloudinary adapter that signs restricted upload parameters and verifies completion metadata server-side.
3. Build upload-session, completion, and list APIs.
4. Build `components/uploads/`: file selection, progress, retryable failure, asset card/player, kind/tag filter.
5. On completion, enqueue ingestion rather than processing inside the HTTP request.

First checkpoint: upload a real video and reload the page without losing its asset record or processing status.

### 2. Media inspection and script-to-video understanding

1. In the worker, download a temporary authorized source, run `ffprobe`, and persist duration/dimensions/audio metadata.
2. Produce a timestamped transcript; persist segments separately from the raw provider response.
3. Sample a small bounded set of frames: scene changes plus a modest interval. Store observations and frame references, not unbounded image data in state.
4. Align stable script section IDs to transcript ranges and visual evidence. Persist partial/unmatched status and confidence.
5. Build the analysis panel in `components/uploads/`; clicking evidence seeks the source player.

First checkpoint: one script section has an honest transcript range and visual observation; a nonmatching section visibly remains unmatched.

### 3. Grounded proposals and draft previews

1. Implement `graphs/repurpose.py` only after the above records exist.
2. Rank candidates from aligned sections using hook strength/coherence heuristics, but treat them as review suggestions—not viral predictions.
3. Deterministically validate ranges against probed source duration, intended length, boundaries, and duplicates.
4. Save a `Clip` and an AI-authored immutable `EditVersion` for each valid candidate.
5. Render only a low-resolution preview initially; final exports come later.
6. Build proposal cards showing duration, range, transcript/visual evidence, rationale, preview, and job state.

First checkpoint: three cards are grounded in real source ranges and at least one playable preview exists.

### 4. Editor, versioning, and final FFmpeg output

1. Build the editor in `components/editor/`: source/evidence panel, player, numeric trim inputs, caption text inputs, crop controls, save/revert, and preset tabs.
2. Validate and POST edit versions. Display saved, saving, conflict, and error states.
3. Implement controlled FFmpeg rendering: trim/reset timestamps, concatenate if supported, crop/scale/pad, captions, audio, and output verification.
4. Verify rendered media with `ffprobe` for dimensions, duration, playability, and expected audio before uploading it.
5. Upload final artifacts to Cloudinary, then persist an `Export` record; do not mark complete before both succeed.

First checkpoint: modify an AI proposal, reload its saved edit, and download working `1080×1920` and `1080×1080` MP4 exports.

### 5. Integration and polish

1. Connect media-job state to Person A's overview/workflow status and review/resume path.
2. Have Person A's publishing UI consume completed exports and platform metadata; do not own publishing state here.
3. Add compact loading/empty/error states and explicit recovery actions on every asynchronous screen.
4. Refresh OpenAPI/fixtures and run focused API/service/UI tests.
5. Preprocess a backup project; label it as prepared demo content if external providers fail.

## Frontend implementation notes

- Use server components for static route layout/initial shell where practical; use client components only for file input, player seeking, editor local state, and job polling.
- Use TanStack Query for fetch/mutation/cache invalidation and active job polling.
- Keep a local draft recipe in a reducer or component state. The persisted recipe remains the authoritative saved version.
- Build numeric trim controls first. Timeline handles are optional after the working controls are demonstrable.
- Use native `<video>` for source preview. Use backend-rendered preview/export URLs for assembled cuts and caption styling.
- Never put Cloudinary secrets or arbitrary upload controls in the browser bundle.

## Backend and worker implementation notes

- Every route verifies authenticated ownership before resolving an asset, clip, export, or project.
- Give each generation/render operation an idempotency key and unique artifact identity so retry does not duplicate recipes or exports.
- The worker must claim one persisted job atomically and process one media job at a time.
- Mark abandoned `running` jobs retryable during worker startup according to Person A's job policy.
- Bounded retries: distinguish provider/transient failures from invalid creator input; retain completed analysis if a later export fails.
- For a review pause, persist state and release the worker; a waiting creator must not hold the single worker slot.
- Use timeouts and hard bounds on source duration, upload bytes, frame sampling, model repair attempts, and render concurrency.

## Suggested job stages

Use a small, honest vocabulary that Person A can surface everywhere:

```text
upload_received
probing_media
transcribing
sampling_visuals
aligning_script
ranking_clips
rendering_preview
waiting_review
rendering_export
verifying_export
completed | failed
```

Avoid fake percentage progress. A stage plus optional detail is more accurate and easier to debug.

## Tests and acceptance checklist

### Backend/service tests

- Reject another owner's asset/clip/export ID.
- Reject invalid upload completion metadata and unsupported media types.
- Validate recipe bounds, caption duration, crop bounds, and stale-version saves.
- Validate candidate ranges against a known `ffprobe` duration.
- Test FFmpeg argument construction without accepting arbitrary shell input.
- Test that an export is incomplete if Cloudinary upload or output verification fails.
- Test retry/idempotency does not create duplicate clips, edit versions, or exports.

### UI checks

- Upload state survives refresh via persisted asset/job data.
- Asset filters and video player work.
- Evidence click seeks to the relevant source timestamp.
- Each proposal clearly exposes source evidence and a processing failure/retry state.
- Save/revert updates editor state correctly and handles an optimistic-conflict response.
- Vertical and square exports visibly use separate presets and metadata.

### Final demo walkthrough

1. Open a project with a real brief/script supplied by Person A.
2. Upload/select source footage and show the asset record.
3. Open analysis and show one script-to-footage match with transcript and visual evidence.
4. Generate/select a grounded proposal.
5. Change trim/caption/crop and save a new edit version.
6. Render and open vertical plus square exports.
7. Hand the completed exports back to Person A's publishing flow.

## Handoff rules with Person A

- Communicate before changing shared `models.py`, `schemas.py`, router registration, configuration, job behavior, migrations, or dependencies.
- Keep a migration and OpenAPI snapshot in the same change set as corresponding model/schema/route changes.
- Person A owns project workflow state and publishing; Person B returns asset/analysis/clip/export facts for those screens.
- Person A owns the job lifecycle infrastructure; Person B supplies media job handlers and meaningful stages.
- If an external model is unavailable, demonstrate the saved prepared project truthfully; do not fabricate visual evidence or claim a render occurred when it did not.

## Scope guardrails

For the deadline, choose a working narrow path over broad unsupported capability:

- One primary source video per clip sequence.
- One language supported by the transcription provider.
- Three proposals, one contiguous segment each.
- Manual crop position, not automatic face tracking.
- Downloadable exports; manual social publication is handled by Person A.
- Deterministic evidence/range validation before model-derived suggestions are shown.

That leaves Person B with a coherent, demonstrable media pipeline while preserving clean integration points for Person A's script, workflow, publication, and insight chain.

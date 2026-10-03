# Backend integration audit

Local branch: `merged-1`. Latest Yash input: `3bcb4c4` (multi-platform exports).
Reference: [creatorai-build-plan.md](creatorai-build-plan.md).

## Merge decisions

Both export implementations are combined, as approved. Yash's six presets, safe
zones, crop/pad options, caption styles, emphasis zooms, audio polish, platform
metadata, immutable export snapshots and lookup/list APIs are retained. The
platform-export creation API now returns a durable job (`202`, `Idempotency-Key`)
instead of performing a synchronous render. One verified artifact is shared by
EditRender and PlatformExport; retries do not upload duplicate files.

All features use `projects`, shared authentication, shared configuration and a
single linear migration head. No remote branch was rewritten or pushed.

## Feature coverage

| Build-plan feature | Implemented backend path and verification |
| --- | --- |
| Script and hooks | Durable generation, immutable direct edits, history, style and campaign snapshots, requirement checks and reviewable scoped assistant proposals. Provider/schema tests and actual OpenRouter generation. |
| Asset management | Signed authenticated uploads, provider completion verification, atomic ingestion queue, filters, restricted delivery; actual browser upload to Cloudinary. |
| Script-to-footage understanding | Actual Groq timestamps and frame descriptions; semantic selection constrained to known evidence IDs, explicit partial/unmatched results and bounded additional frame inspection. Silent video skips speech recognition. |
| Clip generation | Validated non-overlapping source ranges, version-linked candidates, preserved historical edits and durable preview/review graph. Manual source selection is available when evidence is insufficient. |
| Editable editing | Immutable optimistic versions, trim, captions, normalized crop, title, zooms, audio polish; actual caption save and rendered MP4 verification. |
| Platform adaptation | All six Yash presets plus generic aspect aliases, platform matching, independent metadata, safe zones and audio-preserving FFmpeg renders. Six-preset connected tests and actual vertical/square Cloudinary exports. |
| Workflow and publication | Real completed exports required for package approval; approval invalidation, optimistic stages, planned dates and explicit manual confirmation with immutable snapshots. No automatic social posting. |
| Creator intelligence | Deterministic production statistics, latest cumulative snapshots, missing-value handling, within-platform/window recommendations, owned cross-project comparisons and queued AI explanations with validated evidence IDs. |

## Verification and limits

- The automated suite exercises real FFmpeg output, real isolated PostgreSQL
  migrations, independent claims and checkpoint reconnection. External providers
  in automated connected tests are explicitly labelled fixtures.
- Separate live browser QA used a labelled, computer-narrated 32-second source:
  real Cloudinary upload/private download, Groq transcription and vision,
  OpenRouter generation/alignment, FFmpeg draft and vertical/square exports.
  This short source supported two grounded proposals, not three. Three-proposal
  behavior is covered by the deterministic connected fixture. This is not a
  quality benchmark on representative 2–5 minute creator footage.
- Live testing found and fixed checkpoint setup waiting on a claimed PostgreSQL
  transaction, stale interrupt metadata after graph resume, and reasoning-only
  AI responses exhausting the original 2,000-token budget. Regression tests cover
  both PostgreSQL bugs. AI routing remains bounded, schema validated, configurable
  and free-only by default; the token default is 8,192 for the configured model.
- Manual publication/performance tests use clearly labelled test records. No
  actual social post or deployment was made. An independent production JWT/session
  provider still needs its issuer, audience and JWKS configuration.
- Existing user API/frontend processes and the configured application database
  were not modified by QA. Tests create/drop only owned schemas in the dedicated
  local `creatorai_test` database. QA provider media is private and labelled.
- `uv.lock` and hashed `requirements.lock` now pin runtime dependencies. Docker
  installs the locked dependencies and full system FFmpeg/fonts; local rendering
  uses pinned `imageio-ffmpeg`, with an explicit binary override available.

## Recorded results

- Full locked-dependency suite with isolated PostgreSQL enabled: **82 passed**.
- `ruff check app tests scripts`: passed.
- `pip check`: no broken requirements.
- Integration frontend production build: passed before the visual redesign.
- Real QA graph recovery: completed with the saved selected edit, without
  repeating proposal/render work.
- Real Cloudinary exports: Instagram Reel `1080×1920` and Instagram Feed
  `1080×1080`, both completed from immutable edit revision 2 with separate copy.

# Script writer and reviewer workflow

Approved scope: implement the proposed script pilot with LangGraph, independent
writing and review prompts, at most one revision, existing deterministic checks,
and the existing creator review controls. Other AI features remain as implemented.

Contracts: use existing ScriptContent, JobResponse and ScriptVersionResponse.
No schema migration, new API payload or frontend change is needed. The worker
invokes the graph through ScriptCreationService.

## Phase 1 — Connect generation to LangGraph

- Replace the unused script graph with writer (hooks + script) → reviewer → optional
  revision → deterministic validation → persist.
- Keep hooks unchanged and section IDs/order stable during revision.
- Fail on malformed review, provider failure, insufficient call budget or
  unresolved mandatory requirements. Keep semantic checks for human review.
- Reserve three calls; each model stage gets one request, without internal
  fallback/repair retries. An approved draft uses two calls, a revision three.
- Save only the final version with the original input snapshot. Existing
  project approval is invalidated when its script changes.

**Status:** complete. Owned implementation files: backend/app/graphs/script.py,
backend/app/features/script_creation/service.py and router.py, backend/app/config.py,
backend/.env.example. Public DTOs and frontend files were preserved.

## Phase 2 — Verify behavior and document operation

- Test approval, one revision, stable IDs, requirement enforcement, provider
  failures, call limits, immutable snapshots, replay and creator approval.
- Exercise queue → worker service → job polling → version retrieval.
- Run backend pytest, Ruff lint and formatting checks.
- Keep per-stage elapsed times in server logs and model/token usage in LlmCall
  records so a subsequent live quality/latency/cost comparison is possible.

**Status:** complete. Tests updated in backend/tests/test_script_workflow.py,
test_script_queue_api.py, test_postgres_integration.py and browser_fixture.py.
Operation is documented in backend/README.md.

Validation on 2026-10-04:

- Full backend pytest with CREATORAI_TEST_DATABASE_URL set to the dedicated local
  creatorai_test database: **102 passed in 10.77s**, none skipped. The real worker
  executes both approval and revision branches against migrated PostgreSQL;
  fresh sessions verify final content, call records and invalidated creator approval.
- Ruff check app tests: passed.
- Ruff format --check app tests: all 113 files already formatted.
- git diff --check for backend changes and this document: passed.

## Limits and follow-up evaluation

- The graph is bounded orchestration of specialized AI roles, not autonomous
  tool-using agents. Writer and reviewer use separate calls to the configured
  model; a separate reviewer model is not required.
- The revised draft receives code validation, not another AI review. The
  creator remains responsible for subjective quality and semantic claims.
- Durable jobs retain whole-job retry/recovery. Script graph nodes have no
  separate checkpoints; retries before final persistence rerun generation.
- Set OPENROUTER_MAX_CALLS_PER_OPERATION to at least 3 in deployment overrides.
  Older queued jobs with smaller frozen budgets fail before spending tokens;
  submit a new generation job after changing the setting.
- Fixture tests establish correctness, not real model quality, price or
  latency. Compare the old two-call flow and this flow on the same briefs and
  model: human scores for brand fit, pacing and completeness; total elapsed
  time; tokens and provider-reported cost. No live provider calls are part of
  this implementation's test run.

## Subsequent live validation

At the user's explicit request, ran two real-provider tests with the configured
free model. Both passed; the brand case naturally exercised a single revision.
The outputs also revealed pacing and unsupported-claim quality gaps. See
[the live validation report](script-live-validation.md) for measured latency,
tokens, limitations and reproduction steps. `tests/test_script_live.py` keeps
real calls behind an explicit opt-in.

## Phase 3 — Reduce latency and use Gemini

The user authorized Gemini 3.8 Flash as the default after a real-provider
comparison. Default config, local `.env` and `.env.example` now use
`google/gemini-3.8-flash`, paid routing and low thinking. The provider maps older
minimal thinking to Gemini 3.8's supported low level and exposes usage/cost
metadata without changing API DTOs or database tables.

The writer now generates exactly three hooks and the script together. The
reviewer remains independent, one revision remains the limit, and validated hook
alternatives/section IDs remain immutable during revision. This removes one
LLM round trip while keeping the review and deterministic requirements gates.
Only new jobs use the new model: queued job snapshots are preserved.

**Status:** implementation complete; see [latency validation](script-latency-validation.md)
for live timings, costs, quality limits and regression results. The trend test's
fake sequence was updated for the combined writer without changing trend behavior.

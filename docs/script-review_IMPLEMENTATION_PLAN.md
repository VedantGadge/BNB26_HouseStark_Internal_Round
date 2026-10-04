# Script writer and reviewer workflow

Approved scope: implement the proposed script pilot with LangGraph, independent
writing and review prompts, at most one revision, existing deterministic checks,
and the existing creator review controls. Other AI features remain as implemented.

Contracts: use existing ScriptContent, JobResponse and ScriptVersionResponse.
No schema migration, new API payload or frontend change is needed. The worker
invokes the graph through ScriptCreationService.

## Phase 1 — Connect generation to LangGraph

- Replace the unused script graph with hooks → writer → reviewer → optional
  revision → deterministic validation → persist.
- Keep hooks unchanged and section IDs/order stable during revision.
- Fail on malformed review, provider failure, insufficient call budget or
  unresolved mandatory requirements. Keep semantic checks for human review.
- Reserve four calls; each model stage gets one request, without internal
  fallback/repair retries. An approved draft uses three calls, a revision four.
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
- Set OPENROUTER_MAX_CALLS_PER_OPERATION to at least 4 in deployment overrides.
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

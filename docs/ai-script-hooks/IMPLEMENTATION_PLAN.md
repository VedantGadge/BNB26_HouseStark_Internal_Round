# Final feature plan: AI scripts, hooks, brand briefs, and creator style

Frontend delivery is governed by [the frontend design and implementation plan](FRONTEND_INTEGRATION_GUIDE.md), including the agreed continuous Read script view, Edit blocks view, and frontend phases F1-F6. Backend readiness gaps are recorded there and must be resolved before their dependent controls ship.

Status: final consolidated feature plan; Phases 1–3 are complete and Phases 4–6 are functionally complete for the hackathon prototype. This is the single source of truth for this feature's scope and decisions.

## Goal

Build an authenticated backend flow that turns a personal-content or brand-campaign brief into several hooks, a script in the creator's signature style, supporting copy, durable version history, and a conversational assistant for proposing script revisions.

This feature plan follows [the CreatorAI build plan](../creatorai-build-plan.md), particularly its feature acceptance criteria, backend domain model, Workflow A, and API contracts. It describes the work required beyond the current FastAPI scaffold. For this feature, the brand-brief, creator-style, and conversational-editing decisions below extend the older build plan; other features remain governed by that document.

## Assumptions and scope

- Use FastAPI, Neon PostgreSQL, the existing single-concurrency worker, and LangGraph.
- Include only the missing authentication, persistence, and job infrastructure required by this feature.
- Preserve `ProjectCreate`, `ProjectSummary`, `Platform`, `JobStatus`, and `JobResponse`; add script schemas alongside them.
- Use **OpenRouter as the selected LLM API gateway**, through one configurable text-provider adapter. Assume JWT/JWKS authentication using existing settings. The auth issuer, OpenRouter API key, and evaluated model IDs must be configured before a live run.
- Default to English; allow an explicit English, Hindi, or Hinglish language preference in the creator profile and generation request. Use English for the first live demo; verify other language choices with fixtures and a configured provider before advertising their quality. Proposed defaults are three hooks and a target duration bounded to 15–300 seconds. Duration is a writing target, not a guaranteed recording length.
- Keep generated results and creator edits immutable. Regeneration and saving edits create new versions.
- Support two complementary editing modes: direct, section-level edits for precision, and a version-bound chat assistant for natural-language revision requests.
- The assistant proposes a visible, scoped change. It never overwrites a script, applies a revision, or changes the selected hook without the creator explicitly choosing **Apply**.
- Let creators target the full script, one hook, one script section, the CTA, or supporting copy. The UI should send the target IDs and base version rather than relying on ambiguous text references.
- Support **My own content** and **Brand collaboration** modes. In brand mode, use a structured campaign brief and return a brand-requirements checklist alongside the script.
- Support an owner-scoped reusable **My creator style** profile, editable manually or proposed from pasted scripts/transcripts. Inferred preferences require explicit approval before becoming reusable defaults.
- Capture signature lines with inclusion policy (`always`, `when_relevant`, `on_request`) and placement (`opening`, `body`, `closing`). Validate mandatory signature lines deterministically rather than trusting the model to remember them.
- Snapshot the chosen style-profile revision and campaign-brief revision for each script operation. Editing a profile or brief must not rewrite existing scripts or queued requests.
- The first release supports text-only conversations and script changes. It does not execute tools, fetch external facts, modify media, or provide an open-ended creator agent.
- Keep frontend implementation, media processing, clip generation, publishing, and deployment outside this plan.
- Preserve unrelated work and existing API payload shapes.

There is no `FEATURE_MAP.md` or `app/contracts/` in this repository. Its shared interfaces are `backend/app/schemas.py` and the generated artifacts in `contracts/`. Use the existing backend layout; external provider execution belongs in a dedicated adapter, while generation decisions belong in the script workflow/service.

## LLM gateway and model-selection decision

OpenRouter is the chosen gateway for script generation, chat revisions, style suggestions, and model-assisted requirement review. Use its OpenAI-compatible API through a backend-only adapter; keep the gateway API separate from application DTOs and LangGraph decisions.

- Configure `OPENROUTER_API_KEY`, the API base URL, a default model ID, a bounded list of fallback model IDs, request timeout, and maximum output tokens on the backend. Never expose the key to the frontend.
- Keep model selection configurable on the backend. The initial scope does not add an end-user model picker or accept arbitrary browser-supplied model IDs.
- Evaluate a small set of explicit models on personal scripts, brand briefs, signature-style preservation, Hindi/Hinglish examples, and structured revision patches before widening the default. On 3 October 2026, `liquid/lfm-2.5-2.6b:free` passed key-authentication, strict JSON-schema, and basic English `ScriptContent` smoke tests at zero reported cost, so it is configured as the development default with no fallback. This is an integration check—not a quality approval for brand, signature-style, Hindi, Hinglish, or revision output; those fixtures remain required before broader release.
- Use only evaluated model/provider endpoints that support the required structured-output parameters. Request JSON Schema output and require parameter-compatible routing; independently validate all responses with application schemas and requirement checks.
- Development routing is **free-only**: validate the configured model IDs against the current free catalog, check their pricing before use, and reject unavailable or paid replacements. Do not silently fall back to paid models or a random free-model router.
- If no approved free endpoint is available, report a retryable unavailable/quota failure. Fallback models cannot bypass an exhausted account-wide free quota.
- Allow bounded fallback only among the configured, evaluated models for transient rate-limit, capacity, or availability failures. Do not switch models to bypass a content refusal. Keep repair attempts and the whole operation within the same total deadline and call budget.
- Snapshot the requested model/fallback configuration with the job. Record the actual returned model/provider, token usage where available, and attempt details per model call so comparisons and recovered executions are traceable.
- Before sending confidential brand briefs, review both OpenRouter and the selected upstream provider's data-use terms. Model switching must respect the same allowed data-handling policy; free access does not imply confidentiality.

Free-model availability and quotas change; verify the account's current limits before the demo rather than hard-coding a promised request allowance. Google AI Plus subscription benefits are separate from this OpenRouter integration and are not assumed to fund API requests. Selecting this gateway does not authorize purchases or paid API calls.

## Creator experience and final product decisions

1. The creator chooses personal content or brand collaboration and fills in the brief. Brand mode additionally captures the campaign's audience, goal, product, requirements, and intended publishing account.
2. The creator can select their saved style profile, inspect the applied signature lines, or explicitly turn off style for this script. Ordinary tone/language preferences can be overridden per operation; changes to mandatory requirements require an explicit profile or brief revision.
3. Generation produces selectable hook cards, ordered script blocks, title/description/CTA, production notes, and a requirements checklist. Each block has clear Edit and Regenerate controls.
4. The chat panel offers quick prompts such as Shorten, Make more casual, Improve CTA, and Make the brand mention more natural. The creator selects the whole script or a specific block before submitting.
5. The assistant shows a proposed before/after change with Apply and Discard. Unsaved direct edits must be saved or discarded before requesting a proposal, so the backend operates on a definite saved version.
6. Saved scripts and applied proposals create new versions. The UI exposes version history and edited/unsaved cues. Restoring historical content creates a new version through the creator-edit endpoint; it does not replace history.
7. A script edit affects that script only. **Save to my style** is a separate explicit profile action; neither chat history nor a single edit silently trains or changes the reusable profile.

### Brand collaboration brief

Keep the campaign brief project-scoped, with revisions. Capture brand/product name, description, approved product benefits and claims, campaign goal, campaign audience, preferred tone, deliverables/platforms/duration, CTA/discount code, required mentions, wording to avoid, and publishing destination (`creator_account` or `brand_account`). The destination supplies writing context; it does not connect or publish to an account.

Represent requirements with stable IDs and distinguish literal required text from semantic talking points. Return checklist statuses `satisfied`, `missing`, and `needs_review`, with the relevant hook/section evidence. Literal requirements can be checked deterministically. Semantic coverage and claims checks are advisory and must be presented for creator review; they are not proof of factual accuracy or brand approval.

Use only claims supplied in the brief. Flag unsupported additions and removed talking points during generation and revision. Missing mandatory literal requirements block save/application until corrected. Generated drafts and proposals may carry semantic or claim-review warnings; require explicit creator acknowledgement on subsequent creator saves or proposal application, not before an initial generated draft exists. Acknowledgement is not brand approval. Do not invent product facts or implement legal compliance checks in this feature.

### Creator style profile

Store voice, preferred language/mix, typical pacing and structure, preferred CTAs, avoided expressions, and signature lines. For each signature line, store exact text, inclusion policy, and placement. `always` means the required text must appear in the chosen script at its designated placement; `when_relevant` leaves contextual use to the creator/model; `on_request` appears only when explicitly selected for an operation. Hook alternatives need not all repeat a catchphrase, but the selected script must meet the active policy.

Accept bounded pasted script/transcript examples to propose a profile. Show the proposed preferences and signature lines for review; apply them only through an explicit profile-save/approve action. First-release inference is from text examples only, not uploaded media or social-account scraping.

Brand requirements and mandatory style rules must be evaluated together. If a signature line conflicts with forbidden brand wording, surface the conflict and ask the creator to revise the profile or brief. Do not silently drop the line or break the brand rule. Feasible stylistic preferences guide the writing within the approved constraints.

## Implementation baseline before execution

- `backend/app/routes/scripts.py` contains an empty router.
- `backend/app/graphs/script.py` contains an unimplemented workflow builder.
- The script router is currently mounted at `/v1/scripts`, while the project documentation specifies project-scoped script endpoints.
- Project and job endpoints return `501`; database sessions, authentication dependencies, and persisted worker execution are not implemented.
- `Project` is the only application ORM entity; no migration revisions are present.
- Existing verification: one health test passes. Ruff reports an existing import-order issue in `backend/alembic/env.py`.

## Public input/output contract

| Endpoint | Behavior |
|---|---|
| `GET /v1/me/style-profile` | Retrieve the owner's current reusable style profile; return `404` when none exists |
| `PUT /v1/me/style-profile` | Explicitly save a profile revision with an optimistic base-revision check; return the saved profile |
| `POST /v1/me/style-profile/suggestions` | Queue a profile suggestion from pasted examples; return `202` with `JobResponse` |
| `GET /v1/me/style-profile/suggestions/{suggestion_id}` | Retrieve a reviewable suggestion by its job ID; do not apply it automatically |
| `GET /v1/projects/{id}/scripts/campaign-brief` | Retrieve the current project-scoped content mode and campaign brief |
| `PUT /v1/projects/{id}/scripts/campaign-brief` | Save an explicit personal/brand mode and brief revision with an optimistic base-revision check |
| `POST /v1/projects/{id}/scripts/generate` | Persist a generation request; return `202` with existing `JobResponse` |
| `GET /v1/projects/{id}/scripts/versions` | List versions newest first; optionally filter by generation job |
| `GET /v1/projects/{id}/scripts/versions/{version_id}` | Retrieve one complete saved version |
| `POST /v1/projects/{id}/scripts/versions` | Save creator edits as a new immutable version; return `201` |
| `POST /v1/projects/{id}/scripts/assistant/messages` | Persist a creator chat message and queue a scoped revision proposal; return `202` with `JobResponse` |
| `GET /v1/projects/{id}/scripts/assistant/conversations/{conversation_id}` | Retrieve owner-scoped conversation messages and proposal status |
| `POST /v1/projects/{id}/scripts/assistant/proposals/{proposal_id}/apply` | Apply the reviewed proposal to its matching base version as a new immutable version; return `201` |
| `POST /v1/projects/{id}/scripts/assistant/proposals/{proposal_id}/discard` | Mark an un-applied proposal discarded; return `204` |
| `GET /v1/jobs/{id}` | Report actual status, stage, and sanitized failure |
| `POST /v1/jobs/{id}/retry` | Requeue an eligible failed generation, assistant-revision, or style-suggestion job; return `202` |

Generation input resolves brief/topic, audience, tone, and platforms from the owned project, with explicit overrides. Include the content mode, requested language, chosen profile revision (or explicit no-profile choice), campaign-brief revision when applicable, and requested optional signature lines. Brand-mode audience and deliverables take precedence over personal project defaults. The resolved values are validated and persisted at submission so subsequent project, profile, or campaign edits do not change a queued operation.

Output contains stable hook and section IDs, the selected hook ID, ordered script sections, title, description, CTA, production notes, version number, origin, creation time, generation-job reference, the resolved input snapshot, and requirement-check results with evidence. Preserve the existing job identifier field, `id`; do not introduce a competing `job_id` field in `JobResponse`.

Creator-edit input includes a base version, validated script content, selected hook, and explicit acknowledgement of applicable review warnings. Retained hook/section IDs survive edits; newly added items receive backend-assigned IDs. Re-run requirement validation on direct edits and hook selection, not just generated content.

Assistant-message input includes a base version, a bounded creator message, and an explicit target scope (`script`, `hook`, `section`, `cta`, or `supporting_copy`) with the relevant stable IDs. A completed proposal includes a plain-language explanation, a structured patch, and before/after content for the affected blocks. The client must render that proposal as a reviewable diff with **Apply** and **Discard** actions. Chat messages and proposals are version-bound: when the current script changes, earlier proposals remain viewable but cannot silently apply to a different base version.

The first assistant message creates a conversation; subsequent messages supply its owner-scoped `conversation_id`. Store the conversation ID in the queued request and expose it when retrieving the result by job. Proposal validation uses the base script's snapshotted style and brand requirements. Ordinary edits never replace those snapshots implicitly. Requests to change persistent style go through profile suggestion/save; campaign changes go through the brief endpoint and a new generation request.

Error contract: `401` invalid identity, `404` missing/foreign-owned resource, `422` invalid payload or unresolved required fields, `409` stale revision or conflicting mandatory requirements, and `503` unavailable required service before acceptance. Accepted jobs report later provider/output failures through the existing failed-job response. Valid empty version history returns `200` with `[]`; a missing profile is distinguishable from a configured profile with optional fields empty.

## Phase 1 — Define schemas and configuration

**Purpose:** Establish the interface before implementing persistence or model calls.

**Approach:** Extend the existing schema/configuration modules and align route registration with the documented project-scoped API.

- Add schemas for generation requests, hooks, sections, script content, saved versions, creator edits, assistant messages, proposal patches, diffs, and proposal actions.
- Add profile revisions, signature-line policies/placement, pasted-example suggestions, content modes, campaign-brief revisions, requirement-check results, and warning acknowledgements. Define bounds for examples and conversation context before accepting provider jobs.
- Reuse existing platform and job types; preserve existing request/response shapes.
- Define explicit string and collection bounds, nonblank content, unique IDs, section ordering, valid hook references, target scopes, and target-ID requirements.
- Validate duration, platform selection, and resolved project defaults. Reject requests that cannot resolve required values.
- Add server-side model configuration, output-token limits, call timeouts, and retry limits. Verify required dependencies against the existing environment.
- Define OpenRouter configuration, free-only model eligibility, compatible structured-output routing, fallback allowlists, and a bounded per-operation call budget. Pin the selected client dependency after compatibility verification.
- Correct script router registration so endpoints match the project-scoped paths in the documentation without duplicating the existing project routes.

**Owned files:** `backend/app/schemas.py`, `backend/app/config.py`, `backend/app/routes/__init__.py`, new `backend/app/routes/creator_style.py`, `backend/.env.example`, and `backend/pyproject.toml` if dependencies are needed.

**Edge cases:** Whitespace-only values, unsupported platforms, invalid duration, missing resolved defaults, duplicate IDs, oversized content, invalid assistant target IDs, conflicting target scope, and missing runtime configuration. Never expose model credentials to clients.

**Testing:** Focused schema tests for valid inputs, defaults, all validation boundaries, output ordering, oversized output, target validation, and proposal patch validation. Verify existing shared contracts remain compatible.

Include missing brand-mode fields, invalid signature policies, multilingual text, duplicate requirement IDs, and empty/oversized pasted examples.

Include missing gateway credentials, unapproved/paid model IDs, unsupported structured-output parameters, and unsafe fallback configuration.

**Done when:** Requests, generated results, direct edits, and assistant proposals have one documented, validated contract.

- [x] Implementation complete
- [x] Validation recorded

### Phase 1 execution record

- Completed 3 October 2026 on branch `vg`. All feature-owned persistence is isolated in `ai_script_*` tables and has its own `ai_script_alembic_version` migration table, avoiding collisions with other work in the shared PostgreSQL database.
- Added validated Pydantic contracts for personal/brand briefs, creator-style profiles and signature lines, script generations and versions, structured assistant proposals, and requirement checks in `backend/app/schemas.py`.
- Added backend-only OpenRouter settings, free-only defaults, bounded fallback parsing, timeout/output/call limits, and documented environment variables in `backend/app/config.py` and `backend/.env.example`.
- Registered the future script router at `/v1/projects/{project_id}/scripts` and the future style router at `/v1/me/style-profile`; route handlers remain owned by later phases.
- Added `backend/tests/test_script_schemas.py` covering script ordering, selected hooks, brand/literal requirements, signature IDs, explicit profile selection, assistant target scope, and OpenRouter fallback bounds.
- Validation passed: `rtk proxy .venv/bin/python -m pytest -q` (7 passed), `rtk proxy .venv/bin/ruff check app tests`, and `rtk proxy .venv/bin/ruff format --check tests/test_script_schemas.py`.
- Remaining limitation: model IDs are intentionally unset pending evaluation; no OpenRouter request or provider call was made in this phase.

## Phase 2 — Authentication and durable records

**Purpose:** Establish owner-scoped persistence for projects, script versions, and generation jobs.

**Approach:** Implement the minimum shared foundation needed to save scripts and jobs.

- Add database sessions and repositories using the existing `Project` model.
- Verify bearer tokens against configured JWKS, issuer, audience, expiry, and an explicit algorithm allowlist.
- Implement owner-scoped project creation/listing and resource lookup without changing their response shapes. Derive ownership from verified identity, never request payloads.
- Add migrations for the existing project table, script versions, generation jobs, assistant conversations/messages, and revision proposals.
- Add owner-scoped immutable style-profile revisions, profile suggestions, project-scoped campaign-brief revisions, and script input/checklist snapshots. An owner can have no profile; personal mode requires no campaign brief.
- Track the current script version explicitly per project. Compare and update that reference transactionally for creator edits and proposal application. Background results remain retrievable by job/version without silently switching a creator's active draft.
- Enforce unique project/version numbers and at most one generated script per logical generation job.
- Store immutable request snapshots, parent-version references, origin, and timestamps. Store assistant messages and proposal metadata under the owner/project, while retaining the exact base version and target IDs for every proposal.
- Store snapshotted model routing configuration and per-call model/provider/usage metadata without storing API credentials in application rows, checkpoints, or logs.
- Preserve database TLS settings and use small connection pools suitable for the documented hosting setup.
- Correct the existing import-order issue in `backend/alembic/env.py` while working in that module.

**Owned files:** `backend/app/models.py`, new database/auth/repository modules, `backend/app/routes/projects.py`, and `backend/alembic/`.

**Edge cases:** Invalid tokens return `401`; missing and foreign-owned resources return the same `404`. Failed transactions leave no partial version. Concurrent version allocation must not produce duplicate version numbers. A proposal must not reference a version or section outside its project.

**Testing:** Authentication fixtures, ownership tests, migration checks, and PostgreSQL integration tests for rollback, concurrent version allocation, and owner-scoped conversation/proposal retrieval.

Test style/brief optimistic conflicts, foreign-owned profile access, immutable snapshots after profile changes, and active-draft updates under concurrent writes.

**Done when:** Projects, jobs, script versions, chats, and proposals survive restart and remain isolated by owner.

- [x] Implementation complete
- [x] Validation recorded

### Phase 2 execution record

- Completed 3 October 2026 on branch `vg`.
- Added the durable ORM models and initial migration for projects, script/campaign/style revisions, jobs, conversations, proposals, and model-call metadata in `backend/app/models.py` and `backend/alembic/versions/0001_script_feature_persistence.py`.
- Added a database-session boundary, an owner-scoped project repository, and authenticated project create/list endpoints. The database and JWT dependencies return `503` when their runtime configuration is absent; missing/invalid bearer tokens return `401`.
- Added JWT/JWKS verification with required issuer, audience, expiry, subject, and explicit `RS256`/`ES256` algorithm allowlisting. Added pinned `PyJWT[crypto]` dependency in `backend/pyproject.toml`.
- Added local SQLite ownership/persistence tests and fake-JWKS tests for valid and disallowed JWT algorithms in `backend/tests/test_persistence_and_auth.py`.
- Validation passed: `rtk proxy .venv/bin/python -m pytest -q` (11 passed), `rtk proxy .venv/bin/ruff check app tests alembic`, `rtk proxy .venv/bin/ruff format --check app tests alembic`, and offline PostgreSQL migration compilation with `rtk proxy env DATABASE_URL=postgresql+psycopg://creatorai:placeholder@localhost/creatorai .venv/bin/alembic upgrade head --sql`.
- Remaining limitation: no `DATABASE_URL` is configured, so the migration has not been applied to Neon and PostgreSQL lock/concurrency behavior remains covered by later integration testing.

## Phase 3 — Persisted queue and job APIs

**Purpose:** Execute generation independently of an open browser or API request.

**Approach:** Queue work in PostgreSQL and execute one job at a time.

- Implement generation and assistant-revision submission with owner-scoped polling.
- Add style-suggestion jobs using the same bounded queue. Owner-scope these jobs directly because style suggestions do not require a project; retain project scoping for generation and revision jobs.
- Resolve and validate profile/brief revisions and obvious mandatory-rule conflicts before enqueueing. Freeze examples, requirements, and all resolved inputs for retries.
- Require an `Idempotency-Key`: the same owner, operation, key, and payload returns the original job; a changed payload returns `409`.
- Atomically claim eligible jobs ordered by creation time and ID using PostgreSQL row locking and `SKIP LOCKED`.
- Commit claims before model calls; use leases and attempt identifiers to recover abandoned jobs and reject late writes from an expired attempt.
- Persist honest stages and the existing job statuses. Script generation does not need a human-review interrupt or invented progress percentages.
- Implement bounded retry of eligible failures and graceful worker shutdown.
- Scope retry handling to script-generation, assistant-revision, and style-suggestion jobs until other job types are implemented.

**Owned files:** `backend/app/features/script_creation/`, `backend/app/routes/jobs.py`, `backend/app/worker.py`, and shared queue configuration/models/migration support.

**Edge cases:** Duplicate requests, concurrent claims, worker crashes, unavailable database, exhausted retries, stale assistant base versions, and retries of completed jobs. An empty queue is normal idle behavior. Do not return successful acceptance until the job is committed.

**Testing:** Idempotency and status-transition tests; PostgreSQL tests for simultaneous claims, expired leases, and rejection of obsolete attempt writes.

**Done when:** Generation and chat submissions return immediately, polling reports persisted state, and recovered jobs cannot create duplicate versions or proposals.

- [x] Implementation complete
- [x] Validation recorded

### Phase 3 execution record

- Completed 3 October 2026 on branch `vg`.
- Moved all feature-owned routing, immutable request snapshots, queue persistence, and gateway-routing snapshots to `backend/app/features/script_creation/`. Shared authentication, database sessions, projects, and ORM models remain in their existing shared modules.
- Added durable idempotency keys and payload hashes to jobs, owner-scoped generation/chat/style-suggestion submission APIs, job polling/retry, atomic PostgreSQL `SKIP LOCKED` claims, expiring leases, and lease recovery. A reused key returns the original job only when the immutable request matches; it returns `409` for changed input.
- Generation submission resolves project defaults and requested style/campaign revisions into an immutable snapshot before acceptance. Assistant requests verify the current base version, conversation ownership, and selected hook/section target before queuing. Style suggestions store creator-provided examples without applying a reusable profile.
- Added queue unit/API coverage in `backend/tests/test_script_jobs.py` and `backend/tests/test_script_queue_api.py`, including idempotency, owner isolation, claim/recovery/retry, generation polling, style-suggestion retrieval, and assistant-revision submission.
- Validation passed: `rtk proxy .venv/bin/python -m pytest -q` (18 passed), `rtk proxy .venv/bin/ruff check app tests alembic`, `rtk proxy .venv/bin/ruff format --check app tests alembic`, and offline PostgreSQL migration compilation with `rtk proxy env DATABASE_URL=postgresql+psycopg://creatorai:placeholder@localhost/creatorai .venv/bin/alembic upgrade head --sql`.
- Remaining limitation: PostgreSQL simultaneous-claim and crash-recovery behavior still requires dedicated concurrent integration coverage. The isolated feature migration has been applied to the configured database; actual workflow dispatch is recorded in Phase 4.

## Phase 4 — Generation and conversational revision workflows

**Purpose:** Produce scripts, hooks, scoped revision proposals, and style suggestions from immutable input snapshots.

**Approach:** Implement the documented LangGraph sequence:

`validate snapshot → generate hooks → draft script/copy → validate → save version`

Implement the conversational revision sequence alongside it:

`validate message, base version, and target → draft scoped revision → validate patch → save reviewable proposal`

- Put provider calls in a dedicated adapter; keep prompts and generation decisions in the script workflow/service.
- Implement the OpenRouter adapter with JSON Schema output, explicit evaluated model IDs, compatible provider routing, bounded retries, and free-only fallback enforcement. Reject unsupported or disallowed endpoints rather than silently dropping required response parameters.
- Generate hooks first, then draft the script using the same resolved brief.
- Include approved creator-style preferences and the personal/brand context in both generation and chat revision prompts. Choose a hook explicitly and validate its references and active signature-line placement in the resulting script.
- Add a deterministic requirements validator for mandatory literal text and forbidden literal phrases. Add an advisory structured coverage/claims review for semantic brand requirements, with evidence and `needs_review` states rather than unsupported certainty.
- Detect conflicts between mandatory style and brand requirements; do not repair by silently removing either requirement. Return an actionable conflict report.
- Add the bounded style-inference path: pasted examples → proposed profile → validation → saved suggestion. No reusable profile changes occur until explicit approval/save.
- Validate all model output through Phase 1 schemas. Assign durable IDs in backend code.
- Build the assistant prompt from the selected version, relevant target block(s), and bounded conversation context. Do not send unrelated project content when a section-level revision is requested.
- Include the base version's style/brand constraints even for section-level requests. Return a scope conflict if satisfying a revision would require altering an unselected block; let the creator expand the target explicitly.
- Require the assistant to return a structured patch that changes only the chosen scope, plus a short explanation. Reject a proposal that alters out-of-scope blocks, removes stable IDs, or fails patch validation.
- Save the completed assistant response as a proposal. It must remain pending review; it must not create a script version at generation time.
- Allow one bounded repair attempt for malformed output. Apply a finite total deadline and bounded retries for transient provider failures.
- Use a PostgreSQL checkpointer with one thread per logical generation job. Checkpoints support recovery; script tables remain authoritative.
- Commit the saved script and completed job together. Replayed persistence must return the existing result.
- Likewise, commit a saved revision proposal or style suggestion and its completed job together. Use a separate graph thread per logical operation; chat context is retrieved from owner-scoped conversation records, not shared graph threads.
- Treat input and model output as data. Do not allow generated content to invoke tools or alter application configuration.
- Log job/attempt identifiers, stages, and failure categories without logging tokens or secrets.

**Owned files:** `backend/app/graphs/script.py`, new `backend/app/services/openrouter.py`, script service code, conversation/proposal service code, and worker dispatch.

**Edge cases:** Empty output, refusal, malformed JSON, truncated responses, duplicate hooks, provider timeout, stale base version, unknown target, out-of-scope patch, and failure after checkpointing. These produce failed jobs rather than empty successful scripts or proposals. Provider side effects may repeat after a crash; application persistence must still remain idempotent.

**Testing:** Fake-provider fixtures for valid generation, valid scoped proposals, successful repair, exhausted repair, timeout, out-of-scope proposals, transient failure, and replay after interruption. Include PostgreSQL checkpoint recovery coverage.

Include personal and branded fixtures, mandatory opening/closing lines, conditional lines, brand/style conflicts, unsupported claim warnings, removed talking points, and profile inference that saves only a suggestion. Include English/Hindi/Hinglish examples without claiming measured language quality from fixtures alone.

Use fake OpenRouter responses for compatible structured output, `429` quota exhaustion, transient endpoint failure, allowed fallback, refusal without fallback, malformed/refused responses, unexpected model identity, and paid-fallback rejection. Verify actual model metadata and finite deadline/call-budget behavior.

**Done when:** A queued brief produces one validated script version with its style/brand checklist; a chat request produces a scoped proposal; and pasted examples produce a profile suggestion. Each operation has a clear terminal failure path and never applies a suggestion automatically.

- [x] Hackathon implementation complete
- [x] Validation recorded

### Phase 4 implementation progress

- Started 3 October 2026 on branch `vg`.
- Added the modular OpenRouter structured-output adapter, deterministic literal brand/signature requirement checks, worker dispatch, and persisted generation, revision-proposal, and style-suggestion workflow services under `backend/app/features/script_creation/`.
- Script generation is explicitly two-stage: validate three hook alternatives first, then draft the script while requiring those hooks to remain unchanged. Provider calls record model/provider/token metadata, malformed output produces a failed job, and generated drafts create an immutable script version only after schema validation.
- Added fake-provider workflow tests for successful durable script persistence, malformed-output failure, scoped revision proposals, style suggestions, and retryable fallback routing. Local validation currently passes: 26 tests, Ruff lint, Ruff format, and offline PostgreSQL migration SQL compilation.
- Live OpenRouter validation: the configured key returned `200` from the authenticated key endpoint. A minimal strict JSON request and a `ScriptContent` schema request both succeeded using `liquid/lfm-2.5-2.6b:free` through Liquid; the latter returned three hooks and two ordered sections and passed `ScriptContent` validation. No paid model was used and no key value was logged.
- Live endpoint validation against the configured PostgreSQL database: applied the isolated migration, created a demo project through `POST /v1/projects`, queued `POST /v1/projects/{project_id}/scripts/generate`, processed it with the worker using the free model, polled the completed job, and retrieved persisted generated content through `GET /v1/projects/{project_id}/scripts/versions`. Development Swagger testing is available at `/docs` with local-only `AUTH_REQUIRED=false`, which maps requests to `demo-creator` until JWT authentication is enabled.
- Hackathon completion update: full-script and supporting-copy proposals are now validated and can be explicitly applied; brand forbidden phrases block saves/applications; mandatory signature/brand conflicts return an actionable `409`; and the stale graph stub is replaced with a small inspectable LangGraph workflow shell. The worker remains the durable source of truth.
- Deliberately deferred after the user's prototype direction: PostgreSQL-backed LangGraph checkpoint recovery, a model-output repair pass, and exhaustive provider-failure/concurrency coverage. The durable queue, idempotency key, lease recovery, and immutable output records remain in place for the demo.

## Phase 5 — Direct edits, chat proposal review, and versioning

**Purpose:** Let creators make precise direct edits or conversational changes without overwriting history.

**Approach:** Add version retrieval, append-only creator edits, and explicit proposal review/application.

- Implement version list/detail endpoints and retrieval by generation job.
- Save creator edits as new versions with `origin=creator`.
- Require a base version for edits; reject stale submissions with `409` using a transactional version check.
- Implement profile and campaign-brief retrieval/save with immutable revisions and stale-write rejection. Approving a profile suggestion uses the explicit profile-save endpoint; the selected suggestion remains traceable.
- Validate mandatory requirements on every direct save, hook selection, and proposal application. Require explicit acknowledgement of semantic/claim warnings; reject missing mandatory literal text or conflicting rules.
- **Save to my style** must be an explicit profile action, not a side effect of saving a script or applying a chat proposal.
- Persist assistant conversations and render the submitted creator message, assistant explanation, target scope, and proposal status on retrieval.
- Applying a proposal validates that it is pending, belongs to the owner/project, and still targets its exact base version. Create a new version with `origin=assistant_applied`; never mutate the base version.
- Reject application when the proposal is stale or has already been applied/discarded. The creator can send a new message against the latest version.
- Support discarding a pending proposal without deleting the chat audit trail.
- Preserve IDs for retained hooks/sections and assign IDs to additions.
- Persist the selected hook. Switching hooks is an explicit creator edit and must preserve mandatory script requirements.
- Regeneration creates another version from a new input snapshot.
- Preserve historical versions referenced by future footage alignment. Avoid automatic project-stage changes in this feature.
- Define version numbering as save order and list results newest first. A delayed generated result creates another immutable version and must never mutate an existing creator edit.
- Provide frontend integration requirements for the owning UI team: show direct Edit/Regenerate controls on each block; show an assistant panel with target selection; render before/after changes; show **Apply** and **Discard**; mark unsaved direct changes; and expose a version-history restore/view action. The backend only supplies the contract for this experience.
- Add integration requirements for mode selection, campaign-brief fields, a brand-requirements checklist, the style-profile editor, inference approval, signature-line policies, and explicit Save to my style. Hook/section regeneration uses a scoped assistant proposal so it shares the same Apply/Discard behavior.

**Owned files:** `backend/app/routes/scripts.py`, `backend/app/routes/creator_style.py`, script/profile/brief repository and service code, and script schemas.

**Edge cases:** No versions returns `200` with an empty list. Missing versions return `404`. Cross-project references, invalid edits, conflicting saves, applying a discarded proposal, and applying a proposal after its base version is no longer current are rejected. Generating a new version does not change already-saved historical content.

**Testing:** Generate–retrieve–edit–regenerate coverage; chat–proposal–apply/discard coverage; history ordering; stable IDs; ownership; delayed generation completion; stale proposal rejection; and concurrent edit conflicts.

Verify edits cannot silently update reusable style, inferred profiles require explicit approval, brand warnings survive review, mandatory lines cannot be bypassed by direct edits, and pending proposals retain their original requirement snapshots.

**Done when:** Scripts can be directly revised, conversationally proposed, explicitly applied or discarded, and regenerated while every earlier version remains intact.

- [x] Hackathon implementation complete
- [x] Validation recorded

### Phase 5 implementation progress

- Started 3 October 2026 on branch `vg`.
- Added append-only style-profile and campaign-brief revisions with optimistic base-revision checks; stale saves return `409` rather than overwriting another edit.
- Added project-scoped version list/detail and creator-edit APIs. A direct edit verifies that its base is the current version, rechecks deterministic requirements, and saves a new immutable version with `origin=creator`.
- Added conversation retrieval plus explicit proposal Apply/Discard APIs. Applying a pending proposal verifies owner/project/current-base scope, replays the structured patch only against the saved base, creates an `assistant_applied` version, and marks the proposal applied. Discard preserves the audit trail.
- Added persistence tests for immutable edits, stale revisions, proposal application (including full-script replacement), and backend IDs for added hooks/sections. Style-profile saves may now reference a completed suggestion for approval traceability. Version responses now return creation time, generation-job reference, and immutable input snapshot; list responses can filter by `generation_job_id`.
- Browser-facing completion update: CORS permits `PUT` for the campaign/style forms. Supporting-copy proposals update the description; full-script proposals carry a validated replacement while retaining all existing hook and section IDs.

## Phase 6 — Contract handoff and end-to-end verification

**Purpose:** Deliver a backend that the frontend can integrate against.

**Approach:** Publish reproducible contract artifacts and verify the complete workflow.

- Export OpenAPI from FastAPI and add generation-request, generated-script, creator-edit, assistant-message, revision-proposal, applied-proposal, and failed-job fixtures.
- Add personal/brand brief, creator profile, inferred-profile suggestion, signature conflict, and requirements-checklist fixtures. Document profile/brief revisioning and the distinction between creator acknowledgement and brand approval.
- Document model/auth configuration, migrations, checkpoint setup, job recovery, and error behavior.
- Document OpenRouter key setup, free-only routing, current-account quota checks, evaluated default/fallback IDs, model/provider data handling, and recorded model identity. A live evaluation requires an authorized call; no credentials or spending are implied by this plan.
- Run the complete workflow with fake external services and a disposable PostgreSQL database.
- Cover both journeys: personal brief plus signature style; brand brief plus creator style, chat revision, checklist review, and explicit application. Cover pasted examples → suggestion → approved reusable profile.
- Include a live provider smoke test only when credentials and permission for a billable call are available.
- Record phase outcomes, owned files, actual validation results, and remaining limitations in this plan as implementation proceeds.

**Owned files:** `contracts/openapi.json`, script fixtures, backend tests, `backend/README.md`, and this plan's execution records.

**Edge cases:** Contract drift, secrets appearing in fixtures/errors, missing runtime configuration, a proposal being mistaken for an applied change, and fake test results being mistaken for real provider generation.

**Testing:** Full API/worker integration flow, ownership isolation, contract assertions, formatter/linter checks, and regression coverage for the existing health endpoint.

**Validation commands, from `creatorai/backend`:**

```bash
rtk proxy .venv/bin/python -m pytest -q
rtk proxy .venv/bin/ruff check .
rtk proxy .venv/bin/ruff format --check .
rtk proxy .venv/bin/python scripts/export_openapi.py
```

Migration validation additionally runs `rtk proxy .venv/bin/alembic upgrade head` against a disposable test PostgreSQL database. PostgreSQL/checkpoint integration tests must use explicit test configuration and never mutate a production database.

**Done when:** An authenticated creator can queue generation, poll it, retrieve hooks/script/copy, directly edit it, request and review chat proposals, apply or discard them, inspect history, and recover from failure without duplicate results.

- [x] Hackathon implementation complete
- [x] Validation recorded

## Read-only dependencies and ownership boundaries

- `docs/creatorai-build-plan.md`: project context and feature acceptance requirements.
- Existing project/job/platform schemas: preserve their public shapes and import them.
- Existing shared contract fixtures: preserve unrelated examples; add feature fixtures separately.
- `frontend/`: reference for integration expectations only. This backend plan defines the required visual behavior—direct controls, a scoped chat panel, and visible Apply/Discard proposal review—but does not own frontend implementation.
- Asset, clip, repurposing, publication, insight, storage, transcription, vision, and rendering modules: outside feature ownership.
- Docker/deployment setup: existing execution environment; deployment and unrelated container changes are outside scope.

## Acceptance criteria

- An authenticated owner can generate three hooks, ordered script sections, title, description, CTA, and production notes from a valid brief.
- Generation returns a durable queued job before provider execution, and polling reflects actual execution stages.
- Generated content is retrievable through the project-scoped API.
- Creators can use direct controls for precise changes or ask the chat assistant to revise a selected scope in plain language.
- Chat results render as visible, version-bound before/after proposals with Apply and Discard actions. They never modify the script automatically.
- Creator edits, applied proposals, and regeneration create new versions; previous versions and stable retained section IDs remain available.
- Personal content and brand collaboration use distinct brief contexts, including the campaign audience and publishing destination.
- A reusable approved style profile guides generation and chat revisions; required signature lines are checked at their designated placement on generation and every save/application.
- Pasted examples produce a reviewable profile suggestion. An ordinary script edit never updates the reusable profile automatically.
- Brand requirements return an evidence-linked checklist. Missing mandatory literal text blocks save/application; semantic coverage and unsupported claims remain visible review warnings requiring acknowledgement.
- Conflicting style/brand rules are surfaced to the creator without silently dropping either rule.
- Profile and brief changes preserve historical scripts, queued request snapshots, and pending proposal context.
- Invalid input, foreign-owned resources, stale edits, and conflicting idempotency requests are rejected consistently.
- Provider failures, empty output, and invalid output are distinguishable from successful generation and valid empty version history.
- Worker recovery and retries do not create duplicate saved versions or accept obsolete attempt writes.
- An assistant proposal cannot apply across owners, projects, base versions, or target scopes.
- OpenRouter serves all LLM tasks through the adapter. Model switching is configurable, structured-output compatible, traceable, bounded, and free-only during development; unavailable free capacity never triggers a paid call.
- Focused tests, PostgreSQL integration coverage, lint/format checks, and OpenAPI/fixture updates pass or have concrete blockers recorded.

## Risks, prerequisites, and known limits

- OpenRouter is selected. The auth issuer and evaluated default/fallback model IDs remain unspecified and must be configured before live validation.
- Exact OpenRouter client dependency and required runtime dependencies must be verified in Phase 1, rather than guessed from the scaffold.
- Free-model availability, endpoint capabilities, and account-wide quotas can limit multi-call script/chat workflows. Evaluate actual capacity before the demo; model switching alone cannot solve an exhausted gateway quota.
- PostgreSQL locking and checkpoint recovery require real PostgreSQL integration coverage; SQLite and in-memory fakes are insufficient for those behaviors.
- Model repair and provider retries are bounded. A persistently invalid or unavailable provider leaves a failed job with a recovery path.
- Application idempotency prevents duplicate script versions, but it cannot guarantee that a provider call is billed only once after a process crash.
- The first live demo uses English and one concurrent worker. Hindi/Hinglish preferences require provider quality validation before wider release. Streaming tokens, signup, automatic script approval, tool-using chat agents, media edits through chat, and advanced content moderation workflows are outside scope.
- Brand logins, approval portals, contracts/payments, campaign management, social-account connections, and automatic publishing are outside this feature. Publishing destination is metadata only.
- Style learning from uploaded videos, automatic scraping, and model fine-tuning are outside scope. Pasted examples are creator-provided data, not executable instructions or automatically approved preferences.
- Semantic requirements and claims checks are model-assisted review aids, not factual verification or proof of brand/legal compliance. Estimated duration also remains advisory.
- Existing health coverage is minimal; the baseline Ruff issue is included in Phase 2's owned migration work.

## References

- [CreatorAI project build plan](../creatorai-build-plan.md)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [PostgreSQL SELECT and locking clauses](https://www.postgresql.org/docs/current/sql-select.html)
- [FastAPI JWT authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [OpenRouter model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [OpenRouter limits](https://openrouter.ai/docs/api_reference/limits)
- [OpenRouter provider data handling](https://openrouter.ai/docs/guides/privacy/provider-logging)

## Implementation gate

This is the final consolidated planning deliverable for this feature, including direct editing, conversational proposals, brand collaboration, and creator signature style. Record future agreed changes here rather than maintaining competing plans. All implementation phases remain pending. Begin application changes only after the user explicitly requests implementation of this plan or a specified phase.

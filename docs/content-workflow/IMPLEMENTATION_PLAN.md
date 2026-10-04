# Plan: Content workflow hackathon prototype

Status: option 1 approved by the user ("go ahead with 1"). The workflow backend is complete for the manual hackathon prototype and migration `0002_content_workflow` has been applied to the configured Neon PostgreSQL database. The temporary workflow frontend was removed by user request and has a dedicated future integration guide.

## Goal

A creator can open a real project, see its checklist and next action, progress through idea → assets → editing → review → approved → exported → published, plan a posting date, download the chosen media and copy, and explicitly record manual publication. State survives a page reload and backend restart.

Source: [CreatorAI build plan](../creatorai-build-plan.md), particularly the Content workflow acceptance criterion, Overview/Publish routes, and manual publishing scope.

## Current repository baseline

- `backend/app/models.py` already persists Project, ScriptVersion, and Job. Project has `workflow_stage`, initially `idea`, but no transition logic or workflow timestamps.
- `backend/app/routes/projects.py` implements project creation/listing; owner-scoped project lookup exists in `repositories.py`. Project detail/update endpoints are missing.
- `backend/app/routes/publications.py`, asset/clip routers, and media services are scaffolds. Asset, EditVersion, Export, and Publication tables do not exist yet.
- Frontend Projects, Overview, and Publish pages are placeholders. The application uses JSX, TanStack Query, and a shared project shell; preserve those patterns.
- Authentication already provides an owner identity, including an explicitly configured demo mode. Frontend token acquisition is still a stub.
- Existing pytest fixtures use FastAPI dependency overrides and SQLite. Reuse them for workflow/API behavior; validate migrations separately with disposable PostgreSQL.

## Assumptions and scope

- One demo creator and one main demo project. Reuse SQLAlchemy, Alembic, Neon, existing authentication dependencies, and the existing job table.
- Review means the creator checks and approves a saved package. No brand portal, reviewer accounts, or approval messaging.
- Planned dates are reminders/metadata. Posting remains manual, with an explicit confirmation and external post URL.
- Keep dates in UTC and display/edit them in Asia/Kolkata for this demo. A future planned date never triggers publishing.
- Use normal forms, a checklist, stage badges, and next-action links. No drag-and-drop board, calendar, workflow engine, new queue, or new LangGraph graph.
- Exclude social OAuth, automatic posting/scheduling, notifications, analytics, and implementation of the asset library/video editor/rendering pipeline.
- Preserve existing project summaries and script APIs. Add detail/workflow responses instead of changing unrelated script behavior.

## Approved completion policy

The upstream media features are absent. The user selected option 1:

1. **Recommended for the hackathon:** creator-confirmed assets/editing checkpoints and a registered real demo MP4/package. Label manually recorded readiness and prepared demo media. Link the saved script and real existing jobs where available. The workflow works independently of unfinished media features.
2. **Integrated policy:** require persisted Asset, EditVersion, and completed Export records before advancing. Their implementation is a prerequisite owned by the media features; it is not silently included in this workflow plan.

The implementation follows option 1. The prepared MP4 is bundled with the backend and served through an owner-checked endpoint. Option 2 remains a future media-feature integration; it is outside the approved implementation.

## Phase 1 — Persist the workflow and define its rules

**Approach:** Extend the existing Project and add one small Publication table; keep workflow behavior in a focused service.

- Add a workflow revision, fixed checklist data, creator review status, approval/package revision reference, and stage timestamps to Project. Keep `workflow_stage` as the current stage.
- Add Publication with project ID, platform, planned UTC date, actual publication date, status (`draft`, `planned`, `published`), external HTTP(S) URL, and a snapshot/reference to the selected approved package. Use one record per project/platform for this prototype.
- For the proposed standalone approach, keep one current package descriptor on Project: revision, media reference, title, caption, and provenance (`prepared_demo` or real upstream export). Do not create a duplicate media/rendering subsystem. Preserve a snapshot on approval/publication.
- Add an additive Alembic migration; existing projects remain at `idea` with an empty checklist.
- Implement an explicit transition table. Forward transitions are adjacent; each checks its prerequisite. A saved script is required before leaving idea; creator-confirmed asset/edit checkpoints lead to review; explicit approval leads to approved; an available approved package leads to exported; explicit publication confirmation leads to published.
- Allow changes requested from review back to editing. Before publication, reopening editing or replacing the package clears approval and returns to editing. After publication, preserve the published record; a new publishing cycle is outside this prototype.
- A single-platform demo becomes published after its confirmation; with multiple planned publications, the project becomes published when all its publication records are confirmed.
- **Edge cases:** Unknown stages, skipped transitions, missing prerequisites, empty media references, duplicate platform records, repeated approval, and edits after approval. A no-op repeated transition must not reset timestamps.
- **Testing:** Unit tests for allowed/blocked transitions, prerequisite messages, approval invalidation, and repeated actions. Persistence tests for reloads and unchanged historical publication snapshots. Apply the migration to a disposable PostgreSQL database and confirm existing projects remain readable.

**Done when:** Workflow changes persist and invalid transitions cannot produce approval, export readiness, or publication.

## Phase 2 — Expose workflow and publication APIs

**Approach:** Add small synchronous owner-scoped APIs using existing project repositories and dependencies.

- Add `GET /v1/projects/{id}` for project details.
- Add `GET /v1/projects/{id}/workflow` for stage, checklist, review, package, revision, next action, blocking reasons, and real project jobs.
- Add `PATCH /v1/projects/{id}/workflow` for checkpoint/package changes, requiring the current workflow revision.
- Add `POST /v1/projects/{id}/workflow/transitions` for explicit stage/review/approval actions with expected revision. Derive exported/published readiness server-side.
- Add `GET/POST /v1/projects/{id}/publications` and `PATCH /v1/projects/{id}/publications/{publication_id}` for planning and explicit publication confirmation. Resolve publication routes against the existing router mounts to avoid double prefixes.
- Apply owner and project checks to every read/write; foreign/missing resources return `404`, stale/conflicting actions `409`, invalid payloads `422`.
- Confirmation requires approved/exported readiness, an actual timestamp no later than now, and an HTTP(S) post URL. Save publication and derived project stage in one transaction. Unique project/platform records and repeated confirmation handling prevent duplicate posts in the database.
- Export/download references remain backend-controlled. The backend must not fetch arbitrary user-supplied media URLs; reuse restricted media delivery when the upstream storage service exists. A configured prepared demo file must be visibly identified.
- Refresh `contracts/openapi.json`; add workflow, blocked-transition, planned-publication, and published-publication fixtures.
- **Edge cases:** Cross-project IDs, conflicting saves from two tabs, malformed dates/URLs, timezone-naive dates, clearing a plan, repeated confirmations, and empty job lists. Job status is separate from project stage; a failed job never advances a stage.
- **Testing:** FastAPI tests for the happy path, `404/409/422`, owner isolation, atomic confirmation, repeat submission, and reload persistence. Run existing project/script/job regressions and contract export.

**Done when:** The complete workflow is operable through the API without browser-only state or fabricated job completion.

## Phase 3 — Connect Projects and Overview

**Approach:** Replace placeholders using existing JSX components, API helper, project shell, and TanStack Query.

- Connect project list/create to real endpoints and use actual IDs instead of `example-project`.
- Show name, brief, current stage, fixed checklist, review status, and one next action on Overview. Link to the existing Script/Assets/Clips/Publish routes; unfinished routes must not be described as completed integrations.
- Add explicit checkpoint, request-review, changes-requested, and approve controls. Explain blocked transitions beside the action.
- Display real project job status/stage/error and reuse existing retry behavior for supported failed jobs. Poll only active jobs and stop when terminal.
- Update the shared API helper to preserve server error details and include the configured creator token. For the demo, reuse the backend's explicit demo identity configuration; do not expand this feature into an auth-provider integration.
- Invalidate workflow/project/publication queries after saves; disable pending buttons and retain unsaved form input on errors. On `409`, refresh and show that state changed.
- **Edge cases:** No projects, unknown project, no saved script/jobs, expired authentication, unavailable API, and refresh during an action.
- **Testing:** Browser smoke checks for create/open, persisted checklist/stage, disabled/blocked transitions, failure messages, and reload. Verify Next.js build and script-route navigation.

**Done when:** The creator can see and advance an actual persisted project from Overview with clear prerequisites.

## Phase 4 — Build the manual Publish screen

**Approach:** A compact per-platform form and download view; no social integrations.

- Display the approved package's media, title, caption, and prepared-demo/upstream provenance. Offer the actual media link and browser-generated JSON/text metadata download; archive generation is unnecessary.
- Add one publication form per selected platform: planned date/time, editable supporting copy before publication, current status, and external post URL.
- Keep plan-saving separate from **Mark as published**. Display actual publication time and manual mode after confirmation.
- Use Asia/Kolkata labels and explicit UTC conversion; allow saving/clearing a plan. Flag a past planned date as overdue without pretending posting happened.
- Disable downloads/confirmation when the package is unavailable or approval is invalid. A planned date alone never changes the project to published.
- **Edge cases:** Broken/expired delivery link, missing package, missing/invalid URL, future actual publication time, partial multi-platform publication, stale approval, and failed saves.
- **Testing:** Browser checks for date round-trip, save/reload, media playability/download, metadata contents, separate plan/confirmation actions, and multi-platform status. Reuse Phase 2 API tests for validation and confirmation rules.

**Done when:** A creator can plan, download a real package, record manual publication, and see the saved result after reload.

## Phase 5 — Verify the hackathon demo

**Approach:** One repeatable end-to-end journey plus a small regression check.

- Document setup, migration, demo identity, manual checkpoints, media provenance, and current upstream dependencies in the feature documentation.
- Walk through create project → existing saved script → confirmed assets/editing → review → approve package → export readiness → planned publication → download → explicit manual publication.
- Prepare a clearly labelled backup project/package for judging. Do not seed a fictitious publication as a real post; only confirm an actual manually published URL.
- Run focused workflow/API tests, existing backend regressions, Ruff checks, contract regeneration, frontend build, and the browser walkthrough. Record actual results and blockers during implementation.
- **Edge cases:** Backend restart, browser reload, unavailable upstream media, and failed job. Keep successful workflow data and provide actionable recovery messages.
- **Testing:** One API integration test for the full journey and approval invalidation; manual browser verification of persistence and downloaded media. No new broad test framework or load testing.

**Done when:** The agreed demo policy produces a working persisted workflow with approval, downloadable media, planning, and confirmed manual publication.

## Risks or open questions

- Manual checkpoints and a prepared demo package are approved; no completion-policy choice remains open.
- The integrated policy cannot meet the full demo acceptance criterion until Asset/EditVersion/Export persistence and delivery exist. Workflow code must not hide this dependency.
- Live database and media delivery configuration are required for a restart-safe downloadable demo. Prototype status does not justify exposing secrets or bypassing existing owner checks.
- Creator approval here is an explicit self-review action, separate from the script feature's advisory brand-requirement checks.

## Implementation progress

| Phase | Result |
|---|---|
| 1 — Persistence and rules | Project revision/JSON state, Publication table, additive migration, prerequisite checks, approval snapshots and invalidation implemented. |
| 2 — APIs | Owner-scoped workflow/publication/media endpoints, optimistic revisions, UTC dates, immutable publication snapshots, platform copy, and OpenAPI implemented. |
| 3 — Frontend handoff | The temporary workflow UI was removed. The existing frontend placeholders are restored and [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) defines the eventual UI contract. |
| 4 — Backend publish contract | Prepared-video endpoint, package metadata, per-platform copy/plans, and explicit manual confirmation remain implemented as APIs. |
| 5 — Backend verification | 42 backend tests, Ruff checks, OpenAPI generation, fixtures, and PostgreSQL offline migration SQL passed. Connected to the configured Neon PostgreSQL server, verified it was at revision `0001_script_feature_persistence`, applied `0002_content_workflow`, and confirmed revision/table presence afterward. Browser checks were completed before frontend removal and are no longer part of this deliverable. |

Implementation details and repeatable demo setup are in [README.md](README.md). The browser-verified local database is disposable and contains prepared sample data only. No social posting was performed.

**Validation limits:** Migration application was verified on Neon. Backend behavioral tests use SQLite, so PostgreSQL concurrency/locking behavior is not covered by that suite. Manual publication confirmation is covered by API tests with sample URLs; no fabricated live post was created in the browser demo. The existing Script/Assets/Clips screens remain scaffolds, and prepared saved script/media unblock the standalone demo.

## Approval record

The user approved option 1 after reviewing the choices. No additional approval is needed for implementing or verifying that scope. Deployment, social posting, and implementation of the upstream media features are outside this work.

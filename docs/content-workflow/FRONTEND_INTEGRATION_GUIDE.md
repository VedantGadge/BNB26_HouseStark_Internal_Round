# Content workflow frontend integration guide

This guide is the frontend handoff for the integrated workflow backend. Projects,
Overview and Publish now consume real project, job, edit and export records.

## Purpose

Packages require completed, owned exports. There is no prepared-MP4 fallback.
Keep explicit creator review/readiness checks, but never infer asset/export
completion from browser state or a successful upload request.

## User journey

```text
Project created
  → saved script
  → assets ready
  → editing complete
  → review
  → approved
  → exported package
  → planned/manual publication
  → published
```

The backend accepts only adjacent forward stage transitions. The only backward transition is from `review`, `approved`, or `exported` to `editing`; this removes approval because the package may change. Published packages are immutable.

## Authentication and base URL

Use the existing API base URL convention:

```text
${NEXT_PUBLIC_API_BASE_URL}/v1
```

Attach the creator JWT as `Authorization: Bearer <token>`. The backend scopes every workflow, publication, and prepared-media request to the authenticated project owner. A `404` can mean the project does not exist or belongs to another creator.

## Required API calls

| Call | Use |
|---|---|
| `GET /projects/{projectId}` | Initial project details. |
| `GET /projects/{projectId}/workflow` | Authoritative stage, revision, prerequisites, package, jobs, and publications. |
| `PATCH /projects/{projectId}/workflow` | Save creator-confirmed readiness or the current package. |
| `POST /projects/{projectId}/workflow/transitions` | Move forward one stage or reopen editing. |
| `GET /projects/{projectId}/workflow/media` | Owner-checked redirect to the package's first verified export. |
| `GET /projects/{projectId}/package` | Approved immutable package and expiring export download URLs. |
| `GET /projects/{projectId}/publications` | Refresh publication records independently when needed. |
| `POST /projects/{projectId}/publications` | Create one manual publication record for a selected target platform. |
| `PATCH /projects/{projectId}/publications/{publicationId}` | Save planned date/copy or confirm manual publication. |

Every write sends the latest `expected_revision` from `GET /workflow`. After every successful write, invalidate and refetch the workflow query. On `409`, refetch before displaying the action again; another tab has changed the workflow.

## Request examples

Save readiness and a rendered package (use actual completed export IDs):

```json
PATCH /v1/projects/{projectId}/workflow
{
  "expected_revision": 4,
  "assets_ready": true,
  "editing_complete": true,
  "package": {
    "title": "3-step study reset",
    "caption": "A short, practical study reset.",
    "render_ids": ["00000000-0000-0000-0000-000000000000"],
    "media_checked": true
  }
}
```

Advance one stage:

```json
POST /v1/projects/{projectId}/workflow/transitions
{
  "expected_revision": 5,
  "stage": "review"
}
```

Plan a manual Instagram publication. Dates must include an offset; send UTC from the browser.

```json
POST /v1/projects/{projectId}/publications
{
  "expected_revision": 8,
  "platform": "instagram",
  "planned_at": "2026-10-04T05:00:00Z",
  "title": "3-step study reset",
  "caption": "Save this before your next study session."
}
```

Confirm a real manual publication only after the creator has posted it:

```json
PATCH /v1/projects/{projectId}/publications/{publicationId}
{
  "expected_revision": 9,
  "confirm_published": true,
  "published_at": "2026-10-04T05:15:00Z",
  "external_url": "https://www.instagram.com/reel/example"
}
```

## Screen requirements

### Overview

Show the current `stage`, `next_action`, `blocking_reasons`, checklist, review status, stage timestamps, and up to ten recent jobs. Do not make a transition button active when `blocking_reasons` is non-empty.

Use the returned `rendered_exports` provenance and immutable export metadata.
The example UUID above is illustrative, not a usable artifact.

### Review and export

Show editable package copy and actual completed export previews. Save explicitly.
A change while in review, approved or exported returns to editing and clears
approval. Script/brief changes also require fresh review; published snapshots
remain immutable. Never write an arbitrary media URL into the workflow API.

### Publish

Render a form per target platform. A planned time is a reminder only; it does not publish. Display/edit dates in the creator’s chosen timezone and send an ISO-8601 value with an offset or UTC.

Keep **Save plan** separate from **Mark as published**. Confirmation requires an actual non-future time and an HTTP(S) URL. It snapshots the approved package and supporting copy. The project reaches `published` only after every selected target platform has a confirmed publication.

## States and errors

| Status | Frontend behavior |
|---|---|
| `401` | Ask the creator to sign in again. |
| `404` | Show a generic unavailable-project state. Do not reveal ownership information. |
| `409` | Refetch workflow state and tell the creator it changed elsewhere or a transition is blocked. |
| `422` | Keep form values and display field/API validation feedback. |
| Unavailable media | Refresh the signed playback link; do not claim a failed export is playable. |

Job fields are status information only. A queued or failed job must never advance a workflow stage.

## Query and mutation pattern

- Query key: `['workflow', projectId]`.
- Poll while a returned job is `queued` or `running`; stop for terminal states.
- Invalidate workflow, project-summary, and publication queries after a write.
- Disable a submitted action until its mutation resolves.
- Preserve draft form data on a failed write.
- Do not optimistically advance a stage; render the state returned by the backend.

## Contract and test fixtures

Generate the OpenAPI snapshot from `backend`:

```bash
rtk proxy .venv/bin/python scripts/export_openapi.py
```

Use these representative contract fixtures during frontend development:

- `contracts/fixtures/workflow-idea.json`
- `contracts/fixtures/workflow-blocked-transition.json`
- `contracts/fixtures/publication-planned.json`
- `contracts/fixtures/publication-published.json`

Before connecting a real UI, run backend tests and verify at least: stale revision handling, package-change approval invalidation, duplicate platform rejection, non-future publication confirmation, multi-platform completion, and cross-owner access isolation.

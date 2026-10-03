# Content workflow frontend integration guide

This guide is intentionally the frontend handoff for the workflow backend. No workflow UI is currently implemented in `frontend/`; the existing Projects, Overview, and Publish routes remain placeholders until the script, asset, editing, and export features have their final backend contracts.

## Purpose

The frontend should present the project workflow only after it can connect real upstream records. The current backend supports the hackathon manual-prototype policy as a fallback: a saved script plus creator-confirmed assets/editing and a clearly labelled prepared MP4 package.

When real asset, edit, and export APIs are available, replace the manual checkpoint controls with derived backend fields. Do not infer completion from browser state or a successful upload request.

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
| `GET /projects/{projectId}/workflow/media` | Owner-checked prepared demo MP4 for the manual prototype only. |
| `GET /projects/{projectId}/publications` | Refresh publication records independently when needed. |
| `POST /projects/{projectId}/publications` | Create one manual publication record for a selected target platform. |
| `PATCH /projects/{projectId}/publications/{publicationId}` | Save planned date/copy or confirm manual publication. |

Every write sends the latest `expected_revision` from `GET /workflow`. After every successful write, invalidate and refetch the workflow query. On `409`, refetch before displaying the action again; another tab has changed the workflow.

## Request examples

Save manual readiness and a prepared package:

```json
PATCH /v1/projects/{projectId}/workflow
{
  "expected_revision": 4,
  "assets_ready": true,
  "editing_complete": true,
  "package": {
    "title": "3-step study reset",
    "caption": "A short, practical study reset.",
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

Use the returned package provenance. When it is `prepared_demo`, show that the media is prepared sample footage and was not generated from the project’s source assets.

### Review and export

Show editable title/caption and the prepared preview only for the manual prototype. Save package changes explicitly. A successful save while in review, approved, or exported returns the workflow to editing and clears `approved_package`; tell the creator why.

The future integrated screen should use immutable `EditVersion` and `Export` records. It should not write an arbitrary media URL into this workflow API.

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
| `503` from media | Show the prepared demo video as unavailable; do not claim the package is playable. |

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

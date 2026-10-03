# AI scripts and hooks: frontend design and implementation plan

## Purpose

This guide describes the creator-facing experience for AI script generation, brand briefs, creator style, direct editing, and chat proposals. It complements the backend contracts in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

The UI should make a generated script feel like one connected Reel while retaining structured blocks for precise edits and safe AI revisions. This document is the frontend execution plan for this feature; all frontend phases below are pending. Frontend implementation remains scheduled after backend features are ready.

## Design brief and visual direction

**Mode: Operate.** The creator arrives to turn an idea into words they can record, often while short on time. Success means reading a coherent script, making a precise change, and trusting what was saved. The script itself is the focal point; task controls should support it.

Use the existing CreatorAI project shell as visual authority. The current implementation has a light neutral background (`#f7f7f8`), dark text (`#17171a`), and violet action accent (`#635bff`). Preserve the Script route and project navigation. Upgrade their typography and component consistency only where this feature owns the surface.

The selected direction is **Soft Structuralism adapted to a writing workspace**: a generously spaced script canvas with an asymmetric, narrower assistant pane. Use restrained depth, a disciplined sans-serif type scale, and precise active states. The existing violet is an intentional brand carryover. Do not replace it with a new palette for this feature.

Design dials: `DESIGN_VARIANCE: 5`, `MOTION_INTENSITY: 3`, `VISUAL_DENSITY: 4`. These values keep the workspace expressive enough to feel crafted while making long reading and repeated editing comfortable. Marketing-only hero, imagery, cinematic reveal, and floating-navigation rules do not apply to this tool.

### Component craft specification

| Element | Planned treatment |
| --- | --- |
| Typography | Geist through `next/font` if available at implementation; verify availability. One family for headings, labels, and prose, with a Devanagari-capable fallback for Hindi/Hinglish. No assumed commercial font license. |
| Type scale | Workspace title 24-28px; UI text 14-16px; reading text 18-20px with 1.6 line-height. Recording mode allows 24-40px text independently of UI labels. |
| Script canvas | 60-72ch reading measure; neutral surface; 24-32px inner space on desktop, 16-20px on mobile. Heading labels are optional and excluded from copied speech. |
| Depth | A subtle outer tray around the main canvas and assistant surface, with an inset content surface and soft ambient shadow. Keep individual paragraphs flat to maintain continuity. |
| Shape | Canvas shell radius 20px with 16px inset radius; inputs 8px; secondary controls 8px; primary Generate/Save/Apply controls pill-shaped. This is one documented role-based radius scale. |
| Color | One brand accent for action and selection. Separate semantic success/warning/error tokens use both text and icons; they do not become decorative accent colors. |
| Icons | One verified icon package, preferably Phosphor with a consistent light stroke. Every unfamiliar or destructive action has a text label. |
| Focus | Clearly visible focus outline independent of shadow; selected and disabled controls remain distinguishable in both themes. |
| Motion | 150-220ms opacity/transform transitions using `cubic-bezier(0.32,0.72,0,1)`. Feedback on selection, saving, and proposal application; preserve reading position. Reduced-motion mode uses instant transitions. |

Define semantic tokens for background, canvas, inset panel, primary/secondary text, accent, focus, selection, and review states. Plan light and dark counterparts with equal hierarchy. Keep theme choice consistent across the workspace; inherit a shared theme controller if one exists when implemented. No blurred reading surfaces, animated typewriter text, parallax, or scroll hijacking.

## Workspace composition and responsive behavior

```text
Project navigation | Script title                 Version history
                   | Brief summary / Edit brief   Creator style
                   | Read script / Edit blocks    Copy / Record
                   | --------------------------------------------
                   | Continuous script canvas     | Assistant
                   | Selected hook                | Scope label
                   | Connected paragraphs         | Messages
                   | CTA                          | Review proposal
                   |                              | Apply / Discard
                   | Supporting copy disclosure   | Composer
```

- At widths of 1280px and above, use a dominant flexible canvas and a 320-360px assistant pane. The existing project navigation retains its place. Only the primary content canvas and assistant use substantial surface enclosures.
- At 768-1279px, keep the canvas readable and open the assistant in an accessible overlay panel. Show the selected target within the panel so context survives the layout change.
- Below 768px, use one column, 16px horizontal padding, and a full-height assistant view opened by a labeled button. Restore focus and canvas scroll position on close. Use `100dvh` for full-height modes and account for safe areas and the on-screen keyboard.
- Keep the primary action reachable without covering the CTA or final paragraph. Sticky controls need matching bottom padding and keyboard-aware placement.
- Brief, style, requirements, and history use progressive disclosure. Opening all of them at once must not compress the script into a narrow column.
- Show one dominant action per state: Generate before a script exists, Save changes during direct editing, Apply within a reviewed proposal. Routine copy/history controls remain secondary.

## Frontend implementation phases

### F1: Contracts, feature module, and workspace foundation

**Purpose:** Establish a modular page that can represent actual saved content and failures.

- Replace `frontend/app/projects/[projectId]/script/page.jsx` with a small route wrapper. Keep feature components, API functions, state, and pure content derivation under `frontend/features/script-creation/`.
- Reuse `lib/api.js` and the existing TanStack Query provider. Extend the shared request helper narrowly to preserve HTTP status and validation details and handle empty `204` responses. Currently it always parses JSON and loses structured error information.
- Define project-scoped query keys for versions, jobs, brief, and conversations; owner-scoped keys for creator style. Keep saved server data separate from the local edit buffer and assistant proposals.
- Add feature tokens, accessible buttons/tabs/fields, and canvas/panel primitives. Existing stack is Next.js, React, Tailwind 4, and TanStack Query. Icons, dialog primitives, and motion packages are not installed; verify before proposing additions. CSS transitions are sufficient for the planned motion.

**Done when:** The existing Script route renders loading, empty, saved-content, and error fixtures with working keyboard focus and no application-wide navigation changes.

### F2: Brief, creator style, brand context, and durable generation

**Purpose:** Let creators submit a clear request and recover its result across navigation.

- Keep topic/brief prominent. Place language, platform, tone, and duration in a compact expandable options area. Use labeled personal/brand choices; brand mode progressively reveals the campaign fields.
- Save edited profiles and campaign briefs explicitly before generation, then send their revision numbers. A generation request must reflect the selected saved revisions rather than unsaved form values.
- Present signature rules as editable sentences: exact line, inclusion policy, and placement. Profile inference creates a preview with an explicit Save profile action; it does not change reusable defaults on completion.
- Generate an idempotency key once per submission and retain it during network retries. Persist the project/job association for navigation recovery; stop polling terminal jobs and restore polling after reload. Failed polling is a connectivity state, not a failed model job.
- Keep the current saved script visible during regeneration. If a result arrives during unsaved editing, show a New version available action rather than replacing the edit buffer.

**Done when:** Personal and brand fixtures can queue generation, resume polling, recover after a connection interruption, and resolve saved content without losing creator changes.

### F3: Connected reading and recording experience

**Purpose:** Make the script easy to read aloud and copy as one continuous piece.

- Derive the reading text from the selected hook, ordered section text, and CTA, separated by paragraph breaks. Title, description, headings, and production notes are supporting metadata, not spoken copy.
- Show alternative hooks in an expandable single-selection list. Changing the saved selected hook follows the same explicit creator-save flow as other edits; selecting a preview alone does not silently persist it.
- Detect an exactly repeated CTA at the end of the final paragraph for display/copy purposes and include it once. Do not rewrite or deduplicate similar wording heuristically. Provide an explicit edit when the text needs a smoother transition.
- Label summed section timing as Approximate section duration; it may exclude hook/CTA time and is not a guaranteed recording length. Omit unavailable timing rather than inventing it.
- Copy produces speech text only and confirms success accessibly. Recording mode offers adjustable text size, optional beat labels, and manual scrolling. Auto-scroll, if added, defaults to paused and has visible speed and pause controls.

**Done when:** Read, copy, and recording views use the same active saved content; long scripts and Hindi examples wrap without clipping; no CTA is accidentally duplicated.

### F4: Direct editing and immutable history

**Purpose:** Give creators precise control while preserving previous versions.

- Maintain an edit buffer keyed to its base version. Show changed blocks with a text badge and subtle marker; keep Save changes and Discard changes visible together.
- Preserve existing IDs. Until backend allocation for new blocks is defined, support editing existing blocks and hook selection; do not invent IDs or expose unsupported add/remove actions.
- Display inline validation with field paths. For stale saves, retain the local draft and offer Open latest plus Copy my changes. Never resolve conflicts by submitting a new base number against an old edit buffer.
- History opens as a readable version list and preview. Restore submits historical content with the current saved version as the base and creates another immutable version.

**Done when:** Editing, saving, discarding, selecting a hook, and restoring history preserve all earlier versions; stale saves keep the creator's text recoverable.

### F5: Scoped assistant, proposal review, and requirements

**Purpose:** Make AI changes reviewable and explicit.

- Ask AI preselects the exact hook, section, or CTA and shows its name and excerpt in the composer. Quick prompts fill a creator request without sending automatically.
- Unsaved edits block submission with inline Save first / Discard changes choices. Keep chat text intact while the creator resolves those edits.
- Show the proposal explanation followed by labeled Original and Suggested text. Use a two-column comparison on wide screens and a stacked comparison on small screens. Changes remain understandable without color alone.
- Keep Apply and Discard beside the proposal; prevent duplicate application. After Apply returns a saved version, invalidate version/history queries, mark the proposal applied, and announce the version change.
- Surface requirement IDs and review warnings without translating them into invented guarantees. Only offer evidence links when returned IDs actually exist in the active content. Preserve acknowledgements as an explicit per-save/apply decision.
- Hide whole-script and supporting-copy revision controls until the backend can apply those patch scopes. Do not queue a proposal the creator cannot apply.

**Done when:** Hook, section, and CTA proposals can be reviewed/applied/discarded; stale proposals cannot replace a newer script; missing requirements and unacknowledged warnings produce actionable feedback.

### F6: Accessibility, responsive verification, and handoff

**Purpose:** Validate the complete creator journey with the final backend contracts.

- Exercise personal generation, brand generation, style suggestion approval, direct edits, proposal review, history restore, and failed-job recovery using fixtures before authorized live tests.
- Verify keyboard-only navigation, focus restoration, labeled inputs, tab semantics, dialog focus management, error announcements, and status announcements using a polite live region. Do not announce every poll.
- Test at 360px, 768px, and 1440px, both themes, reduced motion, 200% zoom, long scripts, and Devanagari text. Touch actions target at least 44px; body text and controls meet WCAG AA contrast.
- Run the production build and targeted interaction checks. Profile typing and polling so background updates do not re-render the full script or move its scroll position.
- Perform one combined desktop/mobile visual inspection, fix observed defects together, and confirm in one final pass. Do not record mock output as provider-quality evidence.

**Done when:** The complete supported journey works without losing drafts, hidden controls, clipped overlays, inaccessible proposal diffs, or silent script replacement. Record actual test results and backend limitations in this document.

## Backend readiness gates discovered during planning

These are implementation dependencies, not completed frontend capabilities:

| Contract gap | Required frontend behavior until resolved |
| --- | --- |
| Backend applies only hook, section, and CTA proposal changes | Offer only these assistant scopes. Whole-script/supporting-copy options stay unavailable. |
| Brand snapshot exists, but campaign audience/platform/tone precedence is not fully resolved in submission | Require backend resolution before presenting brand generation as complete. Do not silently patch precedence in the browser. |
| Direct save expects existing stable IDs; allocation for additions is unfinished | Edit existing blocks only; defer block creation controls. |
| Version response currently lacks creation time and generation-job reference | Display version number/origin only; do not invent timestamps or reliable job-to-version attribution. Extend the contract before concurrent generation handoff. |
| Profile save lacks suggestion approval traceability | Keep approval UX dependent on an explicit backend association before claiming a complete inference-to-approval audit trail. |
| API CORS methods currently omit PUT | Add PUT before browser style/profile and campaign-brief saves can pass preflight. |
| Request helper always parses JSON | Handle empty discard responses and structured errors in F1. |

## Scope and validation boundaries

The three requested design skills inform visual hierarchy, component depth, typography, motion, and state coverage. Impeccable's Operate guidance governs repeated editing tasks. The existing integration decisions supply the settled audience, primary journey, and script-versus-block behavior; this revision refines that brief rather than starting a new product discovery process.

No frontend code, dependency installation, new brand identity, decorative imagery, or backend changes are part of this documentation update. Image generation is unnecessary for a script editor whose real artifact is readable text. Keep future UI implementation in the feature module and use the phases above as the acceptance contract.

## Creator journey

1. Choose **My own content** or **Brand collaboration**.
2. Enter the brief and optionally choose **My creator style**.
3. Generate, then poll the job until it completes.
4. Present the finished script in **Read script** view by default.
5. Let the creator switch to **Edit blocks** for direct edits, regeneration, or a scoped chat request.
6. Show assistant output as a proposal. It changes nothing until the creator selects **Apply**.
7. Preserve and expose version history after direct edits, proposal application, or regeneration.

## Recommended information architecture

```text
Script workspace
├── Brief and context
│   ├── Personal / brand mode
│   ├── Creator style selector
│   └── Brand requirements checklist (brand mode only)
├── Script
│   ├── Read script            ← default recording/teleprompter view
│   ├── Edit blocks            ← structured editing view
│   └── Version history
└── AI assistant
    ├── Scope selector
    ├── Suggested prompts
    └── Proposal diff with Apply / Discard
```

## Read script versus Edit blocks

### Read script — default

Show one continuous, creator-ready script. This is the recording view, so do not render each section as an isolated card. Use subtle beat labels and timing rather than visual interruptions.

```text
[Selected hook]
What if you could cut your content planning time in half?

THE PROBLEM · 15s
Sunday morning. Your phone buzzes with unfinished ideas...

THE FIX · 20s
Instead of scrambling all week, spend one focused hour batching...

YOUR ROUTINE · 12s
Pick a theme for the week...

CTA · 8s
Try this on Sunday and save the post for later.
```

Show the selected hook, estimated total duration, copied/saved state, and an unobtrusive **Edit blocks** action. A teleprompter mode can hide labels while preserving paragraph breaks.

### Edit blocks

Render the selected hook, each ordered section, CTA, description, and production notes as individually addressable blocks. Each editable block needs:

- **Edit** for direct text changes.
- **Ask AI** to open the chat with that exact block preselected.
- **Regenerate** only when it creates a reviewable proposal rather than overwriting content.
- An edited/unsaved visual cue until the creator saves or discards changes.

Keep stable hook and section IDs in client state. Submit the full validated `ScriptContent` on direct save; do not generate new IDs in the browser.

## Generation flow

### Submit

`POST /v1/projects/{project_id}/scripts/generate`

Send an `Idempotency-Key` header generated once for the creator action. Reuse it only when retrying the exact same request. A changed request needs a new key.

```ts
// Create this once per action; retain it for network retries of that action.
const submissionKey = crypto.randomUUID();
const response = await apiFetch(`/projects/${projectId}/scripts/generate`, {
  method: "POST",
  body: JSON.stringify(body),
  headers: { "Idempotency-Key": submissionKey },
});
```

### Polling states

Poll `GET /v1/jobs/{job_id}` every 2–3 seconds while `status` is `queued` or `running`.

| Job state | UI behavior |
| --- | --- |
| `queued` | “Your script is queued.” Allow navigation away. |
| `running` | “Writing hooks and script…” Keep the existing version visible. |
| `completed` | Fetch `GET /v1/projects/{project_id}/scripts/versions` and open the newest version. |
| `failed` | Show the sanitized `error` and a **Retry** action calling `POST /v1/jobs/{job_id}/retry`. |

Do not display invented percentages. Jobs are durable, so navigating away must not cancel them.

## Style and brand context

### Creator style

Use `GET`/`PUT /v1/me/style-profile` for the reusable profile. A missing profile is `404`, which should render as an empty-state editor, not an error.

The style editor supports voice, language, pacing, structure, CTAs, avoided phrases, and signature lines. Signature-line fields should visibly distinguish:

- inclusion policy: Always, When relevant, On request
- placement: Opening, Body, Closing

Saving a script never changes the style profile. Show a separate explicit **Save to my style** action only when its behavior is implemented as a profile save.

### Brand brief

Use `GET`/`PUT /v1/projects/{project_id}/scripts/campaign-brief`. In brand mode, render required literal wording, talking points, forbidden phrases, CTA, discount code, and publishing destination as structured fields.

After generation, render the requirement checklist beside the script:

- `satisfied`: green confirmation with evidence links.
- `missing`: blocking warning; direct saves and proposal application cannot bypass it.
- `needs_review`: amber warning; ask for creator acknowledgement before saving/applying later changes.

Do not label this checklist as legal, factual, or brand approval.

## Direct edits and versions

Direct save uses `POST /v1/projects/{project_id}/scripts/versions` with `base_version`, `content`, and `acknowledged_warning_ids`.

- Save only after the creator explicitly chooses **Save changes**.
- On `409`, show “This script changed elsewhere. Open the latest version before saving.”
- On success, replace the active version with the returned immutable version and add it to history.
- Version history is newest first. “Restore” should load historical content into a new creator edit; never overwrite the old version.

## Chat proposal flow

The assistant is for scoped revisions, not automatic editing.

1. Creator selects a supported scope: hook, section, or CTA. Whole-script and supporting-copy scopes remain planned until backend patch application supports them.
2. Disable chat while direct changes are unsaved; offer Save or Discard first.
3. Send `POST /v1/projects/{project_id}/scripts/assistant/messages` with `base_version`, `message`, `target_scope`, and the required `target_id` for a hook or section.
4. Store both returned `id` (job) and `conversation_id`.
5. Poll the job, then load `GET /v1/projects/{project_id}/scripts/assistant/conversations/{conversation_id}`.
6. Render the proposal as a visible before/after diff.

Suggested quick prompts:

- Make it shorter
- Make it more casual
- Improve the CTA
- Make the brand mention feel natural

Proposal controls:

- **Apply** → `POST /v1/projects/{project_id}/scripts/assistant/proposals/{proposal_id}/apply`
- **Discard** → `POST /v1/projects/{project_id}/scripts/assistant/proposals/{proposal_id}/discard`

Never replace the visible script immediately after a chat response. A proposal remains pending until Apply. If the script has changed since the proposal’s base version, explain that the creator must request a new proposal.

## Essential UI states

| State | Required cue |
| --- | --- |
| No script yet | Brief form and Generate button |
| Generation queued/running | Durable job status; existing content remains readable |
| Unsaved direct changes | “Unsaved changes” badge; Save and Discard actions |
| Pending proposal | Before/after diff; Apply and Discard visible together |
| Brand warning | Checklist with status and acknowledgement requirement |
| Failed job | Sanitized error and retry action |
| Empty version history | Valid empty state, not an error |

## Demo configuration

For local judge testing, the backend can run with `AUTH_REQUIRED=false`, which maps API calls to the `demo-creator` identity. This is development-only. The frontend must not treat this as a production authentication flow.

OpenAPI and interactive endpoint testing are available at `/docs` while the API is running.

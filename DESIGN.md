---
name: CreatorAI
description: A connected creator studio with clear controls and creative ownership.
colors:
  accent: "#b83b2f"
  accent-hover: "#963025"
  accent-soft: "#fff0ed"
  background: "#f7f7f7"
  surface: "#fff"
  foreground: "#19191b"
  muted: "#626266"
  border: "#dedee0"
  success: "#176348"
  danger: "#ac2626"
  dark-accent: "#ff9b8f"
  dark-accent-hover: "#ffb6ad"
  dark-accent-soft: "#422a28"
  dark-background: "#161618"
  dark-surface: "#222225"
  dark-foreground: "#f5f5f5"
  dark-muted: "#b5b5bb"
  dark-border: "#444448"
  dark-success: "#80d5b2"
  dark-danger: "#ffaaaa"
  demo-background: "#121418"
  demo-surface: "#1a1d22"
  demo-foreground: "#f7f7fa"
  demo-muted: "#bbbfc9"
  demo-border: "#363a44"
  demo-selected: "#382725"
  demo-selection-border: "#ff9b8f"
  demo-tab-selected: "#422a28"
  demo-tab-foreground: "#ffe8e4"
typography:
  display:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "clamp(40px, 4.7vw, 68px)"
    fontWeight: 730
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "32px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "22px"
    fontWeight: 620
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "16px"
    lineHeight: 1.65
  label:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "14px"
    fontWeight: 550
rounded:
  compact: "8px"
  field: "9px"
  tag: "6px"
  control: "12px"
  surface: "14px"
  dialog: "18px"
  pill: "999px"
spacing:
  compact: "8px"
  small: "12px"
  medium: "16px"
  large: "20px"
  surface: "24px"
  roomy: "32px"
  chapter-mobile: "64px"
components:
  button-primary:
    backgroundColor: "{colors.foreground}"
    textColor: "{colors.surface}"
    rounded: "{rounded.field}"
    padding: "11px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "color-mix(in srgb, var(--foreground) 85%, var(--surface))"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.field}"
    padding: "11px 20px"
  button-hero:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "13px 24px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.field}"
    padding: "11px 12px"
  surface:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
    padding: "24px"
  badge-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.tag}"
    padding: "6px 10px"
  project-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "18px"
  nav-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.field}"
    padding: "12px 14px"
    height: "44px"
---

# Design System: CreatorAI

## Overview

**Creative North Star: "Connected creator studio"**

White and pale gray working surfaces, ink typography, monochrome studio actions and warm coral selections make a connected creation workflow understandable. The user-pinned Instagram-inspired palette replaces violet across the website while keeping CreatorAI's own wordmark and product structure. Outfit gives the interface a rounded, confident voice; coastal creator photography supplies the human context. The dark media editor reads as a working tool within the light page, with a deliberate charcoal theme available for the wider interface.

The landing page uses large centered type, generous chapter spacing and an interactive demonstration. Studio screens use a slim breadcrumb bar, stage board, compact forms, readable scripts, evidence rows and familiar project navigation. This records the built local hackathon prototype; it makes no production readiness or accessibility certification claim. Implementation truth lives in `frontend/app/globals.css`, the root layout and the shared shell, UI, workflow, landing and Remotion components. The latest authority in `.impeccable/studio-brief.md` and `studio-social-1.png` supersedes historical violet passages and mockup-only account details.

**Key Characteristics:**

- Monochrome studio actions, coral selections and coherent light/dark working planes.
- Open working areas, fine borders and softly inset media.
- Native text and controls around authored photographic previews.
- Visible distinctions between illustrative demonstrations, editable drafts and verified exports.

## Colors

The palette pairs white/ink neutrals with one warm coral accent family; semantic green and red communicate status.

### Primary

- **Warm Coral** (`accent`): links, focus outlines, range controls, selected navigation and workflow markers. `accent-hover` deepens on hover; `accent-soft` supports selection, notices and proposal comparisons. The landing hero action uses this accent; the closing dark chapter uses the light coral counterpart.

### Neutral

- **Pale Gray** (`background`): page surround, inset fields and working areas.
- **Studio White** (`surface`): primary working plane and fields.
- **Ink** (`foreground`): readable body and heading text.
- **Quiet Ink** (`muted`): supporting copy and secondary labels.
- **Fine Silver** (`border`): separators and control outlines.
- The `dark-*` counterparts replace these roles through `html[data-theme="dark"]`. Studio primary buttons reverse to the light foreground against dark surface text.
- The illustrative editor keeps its own charcoal `demo-*` palette in either theme. Its selected sources, styles and hooks use muted coral fill and a visible light coral border; selected tabs use the coral-dark plane and pale coral text.

Semantic success and danger colors communicate outcome; preserve accompanying text. Yellow within a highlighted video-caption style belongs to authored media, not the application accent palette.

**The Coral Selection Rule.** Use coral to signal selection, focus and workflow context. Let white/ink carry working surfaces and studio primary actions. Do not reintroduce violet or teal as an application accent.

## Typography

**Display and Body Font:** locally loaded variable Outfit, followed by locally loaded Noto Sans Devanagari and sans-serif. The Devanagari face supports Hindi/Hinglish content within the same interface.

**Character:** rounded geometric display lettering with restrained negative tracking; quieter, regular body text carries instructions and scripts. Most labels remain sentence case.

### Hierarchy

- **Display:** the 68px maximum landing hero uses the frontmatter clamp, weight 730 and tight 0.98 leading. At 520px and below it becomes 39px/1.08. This density belongs to the short hero.
- **Headline:** shared studio page titles use 32px/650/1.2, becoming 29px below 800px. Marketing chapter headings use `clamp(32px, 4vw, 56px)` with 1.1 leading, becoming 34px on small screens.
- **Title:** general studio sections use 22px/620; task panel headings use 19px, project cards use 17px/600/1.35, and tertiary working headings use 16px/620. Bento headings use 22px with 1.2 leading.
- **Body:** 16px with 1.65 paragraph leading and a 72ch maximum. Hero supporting copy is 20px/1.4, becoming 16px/1.5 on small screens. Script manuscripts use 20px/1.85 and 64ch, becoming 18px on mobile.
- **Label:** working controls use 14px, commonly weight 550–600; toolbar selectors, breadcrumbs and panel supporting copy use 13px. Project metadata and the dense illustrative editor use 10–12px auxiliary type. Keep those small values local to supporting detail. Studio title supporting copy uses 15px/1.55.

**The Readable Script Rule.** Use the manuscript's larger type and generous leading for spoken text; keep tool labels subordinate.

## Layout

The studio has a 224px white sidebar, a flexible working pane, a 64px minimum-height breadcrumb topbar and a 1320px maximum workspace. Content padding is `32px clamp(20px, 2.6vw, 40px) 60px`; the topbar uses `8px 32px`. The project library places its title and New project action above a four-step workflow strip, search/stage/platform toolbar and three production lanes. Lanes use a 16px grid gap; cards use 18px padding. Board/list switches and filters operate on fetched projects, with actual counts and honest empty lanes. Cards open the project; stage transitions remain explicit controls.

Two-pane screens put an inspector beside the task; Overview uses a 350px inspector and 20px gap. Script, uploads, clip creation, export review and insights sit within bordered task panels. Clips use a two-column grid; evidence rows and tables retain thin separators. Empty asset workspaces span the available width. Insights metrics use four columns on desktop and two below 800px; numeric values use 28px tabular figures, while unavailable values use muted 16px/500 type. This shared grammar supports the existing Overview, Script, Assets, Clips, Publish and Insights routes.

Landing navigation and chapters max out at 1160px; the demo and bento reach 1400px. The hero centers its two-line heading, supporting copy and two actions. The editor has source, preview and inspector panes; the bento uses a dense three-column/two-row arrangement with a 2×2 edit panel and two adjacent tools. Marketing chapters use 128px vertical padding at desktop, while operating forms retain compact 8–24px gaps.

Below 1150px the demo columns and chapter gutters narrow. Below 1100px the studio sidebar becomes 190px, content uses 28px/24px/48px padding and project cards use 14px padding. Below 800px studio navigation moves above the workspace into a horizontally scrolling row, the topbar becomes 56px, inspectors stack, board lanes become one column with two cards per lane, and clip grids become one column. The demo source pane hides and the bento becomes one column. Below 520px cards become a single column, the studio heading/action stack and search spans the toolbar. Stage/platform selectors retain a 140px minimum with automatic width, while the board/list switch takes its own row aligned to the right; selected labels remain readable at narrow widths. Panel padding reduces to 18px and content uses 24px/16px/36px padding. The demo inspector sits below the preview, the horizontal workflow accordion becomes vertical and marketing chapters use 64px/20px padding. Tables scroll within their own container.

## Elevation & Depth

Fine borders and alternating neutral planes carry everyday depth. Board lanes use a subtle border/background color mix; project cards and task panels are flat at rest. Diffuse shadows distinguish media previews and modal surfaces; they do not surround every row. The dark demo includes a subtle radial wash within the charcoal surface. This is a local media treatment, not a full-page gradient identity.

### Shadow Vocabulary

- **Surface ambient:** `0 12px 40px rgba(26, 25, 45, 0.08)` for editing previews and dialogs; dark theme uses `0 12px 40px rgba(0, 0, 0, 0.22)`.
- **Demonstration ambient:** `0 14px 38px rgba(24, 27, 47, 0.15)` beneath the landing editor.
- **Media text:** soft text shadows support captions over imagery where an opaque caption background is absent.

**The Working Plane Rule.** Keep rows and ordinary containers quiet; reserve ambient lift for media and overlays.

## Shapes

Major panels and lanes use 14px corners. Project cards use 12px; studio actions, fields and navigation selections use 9px; studio status badges and segmented view selections use 6px. Landing navigation actions retain the general pill grammar, while hero and closing actions use 12px rounded rectangles. Dialogs use 18px. Borders are generally 1px, with stronger outlines for focus or selected timing ranges. Circular icon controls use a 44px square footprint; the mobile topbar theme control narrows to 36px.

## Components

### Buttons

Clear, compact and tactile. Studio primary buttons use foreground fill with surface text, 14px/600 type, 11px/20px padding, 9px corners and a 44px minimum height. Secondary buttons use the working surface and an inset 1px border. Hover mixes foreground with surface; pressed studio actions move down 1px. Hero actions use 12px corners, 48px minimum height and 13px/24px padding; the primary hero uses coral and the secondary uses the working surface. Mobile hero actions share the row with smaller padding. Disabled buttons use 0.55 opacity and a disabled cursor. Focus uses a 3px coral outline with a 4px offset.

### Chips

Studio badges use 12px/550 text, 6px/10px padding and 6px corners. Neutral badges sit on the background plane; active badges use the soft coral and coral pair. Landing/general badges retain pill corners. Platform tags use 5px corners and 11px labels. Board/list selections use soft coral fill, coral text and `aria-pressed` state. Keep status words alongside color.

### Cards / Containers

Working surfaces use 14px corners, a fine border and 24px padding, reduced to 18px on small screens. Inspectors share the surface plane, while their fields sit on the pale background. Project cards use 12px corners and 18px padding, a three-line brief excerpt, actual stage/platform labels and a four-step miniature workflow. Hover shifts the card up 2px and strengthens its border without adding a shadow. Asset selections use coral outlines and soft coral fill. Bento containers share 14px corners, while inner media panels use tighter 9px clipping.

### Inputs / Fields

Use native inputs, textareas, selects, checkboxes and range controls. Visible labels sit above fields with a 7px gap; text fields use 9px corners, a 1px border and 11px/12px padding. Textareas resize vertically. The native file selector uses background fill, foreground text, 6px corners and 8px/12px padding. The dark illustrative editor preserves the same form grammar with darker fills and brighter boundaries. Errors use semantic red and readable copy.

### Navigation

The wordmark emphasizes its AI suffix in coral. Studio navigation pairs light Phosphor SVG icons with 14px labels and 44px rows; current routes use soft coral fill, coral text and weight 600. Breadcrumbs use 13px type and fine chevrons; theme and creator-session controls occupy the topbar. Mobile navigation uses scrollable 44px rows, reducing labels to 12px at the smallest breakpoint. The landing nav uses quiet links, a theme control and a studio action. The shell identifies a local creator workspace; no mock account, team, billing plan or decorative destination is added.

### Preview and workflow

Remotion previews remain surrounded by native controls. Playback, seek, time and optional volume sit below the image, avoiding authored captions. The landing demonstration explicitly labels illustrative photo sources and keeps changes within the demo. The workflow accordion supports pointer and button interaction; the editing-example carousel uses labelled previous/next controls and polite live updates. Neither substitutes screenshots for interactive UI.

Overview and Publish next-step guidance follows the saved-script checklist state. A saved script leads to footage guidance even when the explicit workflow stage still awaits transition. Publish's empty export guidance links to Clips for creating a completed platform export and keeps package copy controls available. Guidance reflects existing state; it does not imply a completed transition or ready export.

### Motion and dialogs

State transitions use 0.2s and `cubic-bezier(0.16, 1, 0.3, 1)`; image hover scales use 0.7s, and accordion expansion uses 0.6s. GSAP scrubs story words from 0.65 to full opacity and scales/fades the story photograph. These scroll effects run only when reduced motion is not requested. Reduced-motion CSS removes animations, transitions and smooth scrolling. Radix dialogs provide a labelled overlay/content structure with a close control and scrollable body.

## Do's and Don'ts

### Do:

- **Do** keep white/ink studio actions and coral selections coherent through semantic CSS variables in both themes.
- **Do** use native controls, visible labels, accessible SVG icons and clear focus outlines.
- **Do** give scripts reading space and tools compact, predictable placement.
- **Do** label illustrative imagery and examples, preserve source/version distinctions, show real workflow state and fetched board counts, and derive next-step guidance from the actual checklist and completed exports.
- **Do** keep controls outside authored caption space and honor reduced motion.

### Don't:

- **Don't** introduce invented customer proof, metrics, prices or unsupported product controls.
- **Don't** reintroduce violet or teal accents; the latest user authority explicitly supersedes the older palette.
- **Don't** turn small demo metadata into the default body type size.
- **Don't** make transient scroll opacity hide meaningful text; retain the observed readable 0.65 starting opacity.
- **Don't** replace functional UI with screenshot imagery, glyph icons or unlabeled actions.
- **Don't** add hard offset shadows, decorative eyebrows or a new accent family to this system.

Not canonized: historical unused landing selectors, mockup-only account details and one-off caption/illustration colors remain implementation details; they do not define new surface rules. No known craft-floor refusal is adopted as a reusable rule.

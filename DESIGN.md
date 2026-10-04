---
name: CreatorAI
description: A connected creator studio with clear controls and creative ownership.
colors:
  accent: "#5548e8"
  accent-hover: "#4337c9"
  accent-soft: "#eeecff"
  background: "#f5f5f7"
  surface: "#fff"
  foreground: "#17171a"
  muted: "#61616c"
  border: "#dedee5"
  success: "#176348"
  danger: "#ac2626"
  dark-accent: "#aaa2ff"
  dark-accent-hover: "#c1bbff"
  dark-accent-soft: "#302b4b"
  dark-background: "#17171d"
  dark-surface: "#212129"
  dark-foreground: "#f2f2f6"
  dark-muted: "#b0afbe"
  dark-border: "#44434f"
  dark-success: "#80d5b2"
  dark-danger: "#ffaaaa"
  demo-background: "#121418"
  demo-surface: "#1a1d22"
  demo-foreground: "#f7f7fa"
  demo-muted: "#bbbfc9"
  demo-border: "#363a44"
  demo-selected: "#2c2648"
  demo-selection-border: "#a69aff"
typography:
  display:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "clamp(40px, 4.7vw, 68px)"
    fontWeight: 730
    lineHeight: 0.98
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Outfit, Noto Sans Devanagari, sans-serif"
    fontSize: "36px"
    fontWeight: 650
    lineHeight: 1.15
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
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.pill}"
    padding: "11px 20px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.pill}"
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
    rounded: "{rounded.pill}"
    padding: "6px 11px"
---

# Design System: CreatorAI

## Overview

**Creative North Star: "Connected creator studio"**

White and cool silver working surfaces, ink typography and violet actions make a connected creation workflow understandable. Outfit gives the interface a rounded, confident voice; coastal creator photography supplies the human context. The dark media editor reads as a working tool within the light page, with a deliberate dark theme available for the wider interface.

The landing page uses large centered type, generous chapter spacing and an interactive demonstration. Studio screens use compact forms, readable scripts, evidence rows and familiar project navigation. This records the built hackathon prototype; it makes no production readiness or accessibility certification claim. Implementation truth lives in `frontend/app/globals.css`, the root layout and the UI, landing and Remotion components.

**Key Characteristics:**

- Clear violet actions and softly tinted selected states.
- Open working areas, fine borders and softly inset media.
- Native text and controls around authored photographic previews.
- Visible distinctions between illustrative demonstrations, editable drafts and verified exports.

## Colors

The palette pairs cool white/silver neutrals with one violet action family; semantic green and red communicate status.

### Primary

- **Studio Violet** (`accent`): primary actions, links, focus, range controls and selected navigation. `accent-hover` deepens on hover; `accent-soft` supports selection, notices and proposal comparisons.

### Neutral

- **Cool Silver** (`background`): page surround, inspectors and inset work areas.
- **Studio White** (`surface`): primary working plane and fields.
- **Ink** (`foreground`): readable body and heading text.
- **Quiet Ink** (`muted`): supporting copy and secondary labels.
- **Fine Silver** (`border`): separators and control outlines.
- The `dark-*` counterparts replace these roles through `html[data-theme="dark"]`. Primary buttons then use dark ink text against the lighter violet.
- The illustrative editor keeps its own charcoal `demo-*` palette in either theme. Its selected surfaces use a muted violet fill and visible violet border.

Semantic success and danger colors communicate outcome; preserve accompanying text. Yellow within a highlighted video-caption style belongs to authored media, not the application accent palette.

**The Action Violet Rule.** Use violet for actions, focus and selection. Let neutrals carry the working surface and hierarchy.

## Typography

**Display and Body Font:** locally loaded variable Outfit, followed by locally loaded Noto Sans Devanagari and sans-serif. The Devanagari face supports Hindi/Hinglish content within the same interface.

**Character:** rounded geometric display lettering with restrained negative tracking; quieter, regular body text carries instructions and scripts. Most labels remain sentence case.

### Hierarchy

- **Display:** the 68px maximum landing hero uses the frontmatter clamp, weight 730 and tight 0.98 leading. At 520px and below it becomes 39px/1.08. This density belongs to the short hero.
- **Headline:** studio page titles use 36px/650/1.15, becoming 30px below 800px and 29px below 520px. Marketing chapter headings use `clamp(32px, 4vw, 56px)` with 1.1 leading, becoming 34px on small screens.
- **Title:** studio sections use 22px/620; tertiary working headings use 16px/620. Bento headings use 22px with 1.2 leading.
- **Body:** 16px with 1.65 paragraph leading and a 72ch maximum. Hero supporting copy is 20px/1.4, becoming 16px/1.5 on small screens. Script manuscripts use 20px/1.85 and 64ch, becoming 18px on mobile.
- **Label:** working controls use 14px, commonly weight 550–600; the dense illustrative editor uses 12px labels with 10–11px auxiliary metadata. Keep those small values local to supporting editor detail.

**The Readable Script Rule.** Use the manuscript's larger type and generous leading for spoken text; keep tool labels subordinate.

## Layout

The studio has a 224px sidebar and a flexible working pane, with a 1240px maximum workspace. Main padding is `42px clamp(20px, 3.2vw, 52px) 64px`. Two-pane screens put an inspector beside the task; repeated rows and tables use thin separators rather than isolated cards.

Landing navigation and chapters max out at 1160px; the demo and bento reach 1400px. The hero centers its two-line heading, supporting copy and two actions. The editor has source, preview and inspector panes; the bento uses a dense three-column/two-row arrangement with a 2×2 edit panel and two adjacent tools. Marketing chapters use 128px vertical padding at desktop, while operating forms retain compact 8–24px gaps.

Below 1150px the demo columns and chapter gutters narrow. Below 1100px the studio sidebar becomes 190px and assets stack. Below 800px the studio navigation moves above the workspace into a horizontally scrolling row, inspectors stack, the demo source pane hides and the bento becomes one column. Below 520px the demo inspector sits below the preview, the horizontal workflow accordion becomes vertical and marketing chapters use 64px/20px padding. Tables scroll within their own container.

## Elevation & Depth

Fine borders and alternating neutral planes carry everyday depth. Diffuse shadows distinguish media previews and modal surfaces; they do not surround every row. The dark demo includes a subtle radial wash within the charcoal surface. This is a local media treatment, not a full-page gradient identity.

### Shadow Vocabulary

- **Surface ambient:** `0 12px 40px rgba(26, 25, 45, 0.08)` for editing previews and dialogs; dark theme uses `0 12px 40px rgba(0, 0, 0, 0.22)`.
- **Demonstration ambient:** `0 14px 38px rgba(24, 27, 47, 0.15)` beneath the landing editor.
- **Media text:** soft text shadows support captions over imagery where an opaque caption background is absent.

**The Working Plane Rule.** Keep rows and ordinary containers quiet; reserve ambient lift for media and overlays.

## Shapes

Major panels and media use 14px corners. Fields and inset demo panels use 9px; compact selections use 8px. Studio actions and badges are pills; hero and closing actions use 12px rounded rectangles. Dialogs use 18px. Borders are generally 1px, with stronger outlines for focus or selected timing ranges. Circular icon controls use a 44px square footprint.

## Components

### Buttons

Clear, compact and tactile. Studio primary buttons use violet, 14px/600 text, 11px/20px padding and a 44px minimum height. Secondary buttons use the working surface and an inset 1px border. Hero actions use 12px corners, 48px minimum height and 13px/24px padding; mobile actions share the row with smaller padding. Hover changes fill; disabled buttons use 0.55 opacity and a disabled cursor. Focus uses a 3px violet outline with a 4px offset.

### Chips

Pill badges use 12px/550 text and 6px/11px padding. Neutral badges sit on the background plane; active badges use the soft violet and action violet pair. Keep status words alongside color.

### Cards / Containers

Working surfaces use 14px corners, a fine border and 24px padding, reduced to 18px on small screens. Inspectors sit on the cool silver plane. List rows stay open with bottom borders. Bento containers share 14px corners, while inner media panels use tighter 9px clipping.

### Inputs / Fields

Use native inputs, textareas, selects, checkboxes and range controls. Visible labels sit above fields with a 7px gap; text fields use 9px corners, a 1px border and 11px/12px padding. Textareas resize vertically. The dark illustrative editor preserves the same form grammar with darker fills and brighter boundaries. Errors use semantic red and readable copy.

### Navigation

The wordmark emphasizes its AI suffix in violet. Studio navigation pairs light Phosphor SVG icons with 14px labels and 48px rows; current routes use soft violet fill, violet text and weight 600. Mobile navigation uses scrollable 44px rows, reducing labels to 12px at the smallest breakpoint. The landing nav uses quiet links, a theme control and a studio action.

### Preview and workflow

Remotion previews remain surrounded by native controls. Playback, seek, time and optional volume sit below the image, avoiding authored captions. The landing demonstration explicitly labels illustrative photo sources and keeps changes within the demo. The workflow accordion supports pointer and button interaction; the editing-example carousel uses labelled previous/next controls and polite live updates. Neither substitutes screenshots for interactive UI.

### Motion and dialogs

State transitions use 0.2s and `cubic-bezier(0.16, 1, 0.3, 1)`; image hover scales use 0.7s, and accordion expansion uses 0.6s. GSAP scrubs story words from 0.65 to full opacity and scales/fades the story photograph. These scroll effects run only when reduced motion is not requested. Reduced-motion CSS removes animations, transitions and smooth scrolling. Radix dialogs provide a labelled overlay/content structure with a close control and scrollable body.

## Do's and Don'ts

### Do:

- **Do** keep the light working scene and explicit dark option coherent through semantic CSS variables.
- **Do** use native controls, visible labels, accessible SVG icons and clear focus outlines.
- **Do** give scripts reading space and tools compact, predictable placement.
- **Do** label illustrative imagery and examples, preserve source/version distinctions and show real workflow state.
- **Do** keep controls outside authored caption space and honor reduced motion.

### Don't:

- **Don't** introduce invented customer proof, metrics, prices or unsupported product controls.
- **Don't** turn small demo metadata into the default body type size.
- **Don't** make transient scroll opacity hide meaningful text; retain the observed readable 0.65 starting opacity.
- **Don't** replace functional UI with screenshot imagery, glyph icons or unlabeled actions.
- **Don't** add hard offset shadows, decorative eyebrows or a new accent family to this system.

Not canonized: historical unused landing selectors and one-off caption/illustration colors remain implementation details; they do not define new surface rules. No known craft-floor refusal is adopted as a reusable rule.

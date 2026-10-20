# Showcase v6 Layout Decisions & Taste Audit

## Context & Motivation
Showcase v5 (`3e9bb04`) was rejected due to "HUD soup": telemetry cards, floating pills, reticle brackets, scan lasers, step-cue boxes, and nested captions that overwhelmed and diluted the core narrative.

For v6, we rebuild on branch `showcase-v6` off `origin/3d-antigravity` with a stripped-back editorial, Apple-keynote aesthetic:
- Monochrome with one accent colour maximum (`#d8ff64`).
- One hero object traveling down a continuous vertical thread.
- Exactly one sentence per stage, lots of negative space, zero clutter.
- Pure scroll-scrubbed animation (bidirectional with GSAP ScrollTrigger and Lenis).
- Exact REPORT30 figures.

---

## 3 Static Mock Explorations

### Mock 1: The Central Spine (`showcase/mocks/mock-1-center-spine.html`)
- **Structure**: Center vertical line down the page. Sentences alternate on the left and right sides of the line, with the hero traversing the center spine.
- **Evaluation**:
  - *Readability*: 6.5/10 — Alternating left/right jumping interrupts linear editorial flow.
  - *Keynote Feel*: 7.0/10 — Feels more like an interactive infographic timeline than an unhurried luxury product narrative.
  - *Mobile*: 7.0/10 — Center line collides with text or has to be shifted awkwardly to the left margin.
  - **Overall Score: 7.2 / 10**

### Mock 2: Keynote Asymmetry (`showcase/mocks/mock-2-keynote-split.html`) [SELECTED]
- **Structure**:
  - **Left 45% (Desktop)**: Fixed, unmoving editorial column. One bold, confident sentence per stage fades in with pure opacity transitions. Lots of breathing room.
  - **Right 55% (Desktop)**: Dedicated open stage where the continuous vertical thread line runs. The 3D hero travels vertically down this thread, transforming subtly at each stage.
  - **Mobile**: Clean top-to-bottom hierarchy — sticky statement anchored at top, 3D hero stage on the thread below it.
- **Evaluation**:
  - *Readability*: 9.8/10 — Instant comprehension. Only one sentence visible at a time. Zero competing widgets.
  - *Keynote Feel*: 9.8/10 — True Apple-keynote simplicity and quiet authority.
  - *Mobile*: 9.5/10 — Zero horizontal clipping, perfect vertical rhythm.
  - **Overall Score: 9.6 / 10**

### Mock 3: Monumental Monolith (`showcase/mocks/mock-3-monumental-monolith.html`)
- **Structure**: Full-viewport centered chapters (100vh each). Thread runs down the center behind large centered headings with the hero below.
- **Evaluation**:
  - *Readability*: 8.0/10 — Clean, but massive vertical gaps between stages cause disengagement during scrolling.
  - *Keynote Feel*: 8.2/10 — Strong typography, but the center thread visually collides with centered multi-line headings.
  - *Mobile*: 7.5/10 — 100vh chapters push the hero below the fold on mobile viewports.
  - **Overall Score: 8.0 / 10**

---

## Decision
**Direction 2 (Keynote Asymmetry)** is selected. It completely eliminates HUD soup, delivers true editorial restraint, gives the 3D hero its own clean stage, and guarantees effortless mobile and desktop legibility.

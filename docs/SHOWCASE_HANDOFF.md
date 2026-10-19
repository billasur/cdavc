# CD-AVC showcase handoff

**Recorded:** 2026-10-19

**Repository:** `.` (repository root; all paths below are relative)

**Branch:** `main`

**Verification base revision:** `5a37ddd docs: document benchmark reproduction and runner usage`

**Showcase implementation commit:** `399be78 feat(showcase): rebuild task-patch scroll story`

**Original handoff commit:** `3afd1f4 docs: add showcase handoff`

## Latest verification receipt — 2026-10-19

**Status: local automated checks passed; clean-Linux and interactive visual
verification remain incomplete.** This is a local evidence record, not an
OmniRush.ai verification decision, submission or deployment receipt.

This pass inspected the working tree rather than relying on earlier chat
summaries. The showcase rebuild (`399be78`), benchmark harness (`23ab2c2`) and
benchmark documentation (`5a37ddd`) are already committed. Do not repeat those
commits or describe them as pending.

At the start of verification, `main` was ahead of `origin/main` by 10 commits.
There were three modified implementation files: `showcase/index.html`,
`showcase/story.css` and `showcase/story.js`. Local untracked tool artifacts were
`.freebuff/`, `showcase/.ogcode/` and `showcase/ogcode.json`.
This verification pass changes only this handoff; it leaves those existing
implementation edits and artifacts untouched and unstaged.

### Checks actually run in this pass

| Check | Working folder / command | Result |
| --- | --- | --- |
| Offline Python test suite | `.` — `make test` | **Passed: 61 tests**, 1.872 seconds, no skips reported |
| JavaScript syntax | `showcase/` — `node --check story.js` | **Passed**; syntax only, not browser execution |
| Vendor integrity | `showcase/` — `npm run verify-vendor --offline` | **Passed: 8 checked-in files verified** |
| Whitespace validation | `.` — `git diff --check` | **Passed** |
| Local HTTP smoke | Temporary Python standard-library HTTP server bound to loopback; parsed `/` and requested its local scripts/styles plus both Three.js modules | **Passed**: seven ordered story stages, repo CTA, simulation disclosure, and seven non-empty assets returned HTTP 200 |
| Clean-Linux build and offline container tests | `.` — `make docker-test` | **Blocked before build**: Docker daemon socket unavailable; no image build or container tests completed |
| Browser interaction / 360px touch / reduced-motion | Not run in this pass | **Pending** for the current uncommitted iteration |
| Lint / typecheck | No separate showcase commands defined in `showcase/package.json` | **Not run**; syntax and integrity checks are not substitutes |
| Deployment | Not requested or attempted in this pass | **Not deployed by this pass** |

Observed tool versions: Python `3.11.16`, Node `26.11.1`, npm `11.20.0`.
The project Python pin remains `3.11.11`; this host run does not prove the
pinned Docker environment. No dependency installation or runtime change was
performed.

### Exact implementation snapshot checked

These are Git blob object IDs from `git hash-object`, not commit IDs. They were
unchanged between the initial checks and the HTTP smoke pass.

| File | Git blob ID |
| --- | --- |
| `showcase/index.html` | `59a353cf45256e78598e698a34354c48be133e8f` |
| `showcase/story.css` | `7ec7b198db6613219703503f54c1587881d77124` |
| `showcase/story.js` | `a27199da84e4c39277d977d998d5c7378c5a40c7` |

### Next verifier actions

1. Start a Docker daemon, then run `make docker-test` from the repository root.
   A pass must include the container test run with `--network none`, not just
   an image build. No clean-Linux result is claimed yet.
2. Serve the current site with
   `python3 -m http.server 4173 --directory showcase`. In a browser, verify all
   seven stages from top to bottom and back, then repeat at 360px and with
   reduced motion. The HTTP smoke does not execute WebGL, GSAP or Lenis.
3. Review and explicitly select the three existing showcase implementation
   edits before any implementation commit. Exclude the tool artifacts.
4. Rerun the commands above after any implementation change. Deployment and
   any external verification submission require their own successful receipts.

## Historical implementation notes

The remaining sections preserve the original handoff from the first showcase
pass. Their working-tree lists, check counts, QA hooks and blockers describe
that earlier state, not the current iteration. The receipt above takes
precedence wherever they differ.

## Goal

Rebuild the CD-AVC demo page as a calm, scroll-driven 3D story that is:

- one pinned full-viewport canvas with page scroll as the timeline;
- a single task patch as the hero object;
- faithful to real CD-AVC behavior;
- readable in plain English, with one short idea per scroll chunk;
- scrubbed in both directions, with only slow ambient drift outside scroll state;
- deployable as a static Vercel site;
- rebuildable/offline-safe with all browser libraries and fonts local;
- mobile-safe at 360px and accessible with `prefers-reduced-motion`;
- honest about simulated/illustrative visuals and free of invented benchmark numbers.

## Original implementation baseline

### Implemented

The old hero and “scroll the job” sections were replaced wholesale in
`showcase/index.html`. The page now contains:

1. Contract — a locked frame with one file, one symbol and bounded retries.
2. Bounded model patch — one block enters the frame while the outside remains protected.
3. Locked-test hash — the test set is sealed; drift rejects the candidate.
4. AST contract — only the allowed symbol may change.
5. Isolated worktree — the patch runs away from the active source tree.
6. Regression — targeted and existing suite checks decide whether it is green.
7. Verified merge — green code locks into the main tree; a rejected block falls away.

The copy is shown as seven absolute-positioned panels and the right-side rail
tracks the active step. The scroll range is `800vh`, approximately one viewport
of timeline per story beat.

### Important implementation details

- `showcase/story.js` owns the scene and the scroll state.
- `TaskScene.setProgress(progress)` and `applyState()` derive camera/object state
  from normalized scroll progress.
- GSAP ScrollTrigger pins `.story-pin` and scrubs the timeline.
- Lenis smooths wheel scrolling; touch scrolling is left native.
- Idle motion is limited to very slow group drift and ambient rotation.
- Three.js uses primitive geometry only: boxes, torus gates, lines and a plane.
  There is no model asset or Draco file.
- Pixel ratio is capped at `2`.
- WebGL scene initialization is lazy through `IntersectionObserver`.
- Rendering pauses when the scene is off-screen or the document is hidden.
- A static SVG scene is available for reduced motion and WebGL failure.
- The current page uses a system font stack; there are no CDN fonts.
- The bottom disclosure says the scene is “simulated / illustrative” and makes
  no benchmark claim.

## Files

### Files in the original showcase change

These files were included in the original showcase change, since committed as
`399be78`. Only the three files listed in the latest receipt have newer
uncommitted implementation edits:

- `showcase/index.html` — new page shell, nav, seven story panels, fallback SVG,
  closing “Open repo” section, local script tags.
- `showcase/story.css` — dark neutral visual system, single lime accent,
  typography, full-screen layout, rail, responsive/mobile layout and reduced
  motion fallback.
- `showcase/story.js` — local Three.js scene, GSAP/ScrollTrigger scrub,
  Lenis integration, lazy WebGL initialization, state mapping, WebGL fallback,
  visibility pause and audit query support.
- `showcase/vendor/three.core.min.js` — local Three.js core dependency required
  by `three.module.min.js`.
- `showcase/vendor/manifest.json` — added the Three.js core entry and checksum.
- `showcase/vendor/README.md` — documents the local ESM dependency relationship.
- `README.md` — documents the new story and offline vendor verification.

### Already committed showcase foundation

These commits are already in local Git history:

- `df1e985` — initial animated showcase.
- `49c3be8` — scroll-driven 3D demo pass.
- `76a7ec5` — guided job chapters.
- `8f657ae` — pinned showcase vendor sources.
- `6349b7a` — checked-in browser vendor artifacts.

The vendor package metadata lives in:

- `showcase/package.json`
- `showcase/package-lock.json`
- `showcase/vendor/gsap.min.js`
- `showcase/vendor/ScrollTrigger.min.js`
- `showcase/vendor/lenis.min.js`
- `showcase/vendor/lenis.mjs`
- `showcase/vendor/three.module.min.js`
- `showcase/vendor/three.core.min.js`

## Tech stack

### Runtime and hosting

- Static HTML/CSS/ES modules.
- Vercel static deployment from `showcase/`:
  `vercel deploy --cwd showcase`.
- Local preview:
  `python3 -m http.server 4173 --directory showcase`.
- No server, API key, model download or runtime network request is needed by
  the demo page.

### Browser libraries

All are vendored and pinned under `showcase/vendor/`:

| Library | Version | Usage |
| --- | ---: | --- |
| Three.js | `0.180.0` | Primitive 3D scene, camera, lights, fog and renderer |
| GSAP | `3.15.0` | Timeline object and animation engine |
| ScrollTrigger | `3.15.0` via GSAP | Pinning and scroll-scrub progress |
| Lenis | `1.3.26` | Smooth wheel scrolling, connected to ScrollTrigger |

The page loads the classic local GSAP, ScrollTrigger and Lenis bundles from
`index.html`. `story.js` imports the local Three.js ESM bundle, which imports
the checked-in `three.core.min.js` file by relative path.

### Geometry and rendering

- No external textures, stock imagery, model files or shader downloads.
- The scene is primitive geometry and therefore has no model payload to exceed
  the requested 1 MB model limit.
- `WebGLRenderer` uses high-performance mode, a pixel-ratio cap of 2, a dark
  neutral clear color and a subtle ground plane/fog setup.

## Skills and design guidance used

Loaded or used during the showcase work:

- `frontend-design` — visual direction, typography restraint, copy clarity,
  layout rhythm, responsive behavior and anti-generic review.
- `image-to-code` — image-first/implementation-aware design guidance; no
  external image asset was ultimately needed because the requested direction
  is a primitive 3D scene.
- `gpt-taste` — earlier motion/design pass and anti-template constraints.
- `gsap-core` — GSAP usage and performance guidance.
- `gsap-scrolltrigger` — pinned, scrubbed scroll timeline and refresh rules.
- `omnirush-handoff` — this handoff artifact and evidence format.

The visual references came from the user’s brief: igloo.inc, the Quibi Webflow
demo and sorenwest.com. No external site assets or CDN code were copied.

## Major decisions

1. **One object instead of a pipeline dashboard.** The story follows one task
   patch through a frame, gates and the source tree. This directly addresses
   the request for a product story rather than decorative 3D.
2. **Full-viewport pin, seven beats.** ScrollTrigger pins the full scene and
   scroll controls the entire state. The `800vh` section gives each beat roughly
   one viewport of pacing.
3. **Scroll is the source of truth.** Object transforms, gate visibility,
   rejected-block fall-away, camera position and merge state are derived from
   normalized progress. Scrolling upward reverses them.
4. **Primitives over assets.** Boxes, torus gates, lines and a plane keep the
   scene small, deterministic and offline-safe. No model loader or asset
   pipeline was introduced.
5. **Single restrained palette.** Dark green-black neutral, white text and one
   lime accent; no neon gradients, particles, glow or card grid.
6. **Honest visual evidence.** The scene is explicitly labelled simulated /
   illustrative. It does not display invented test counts, timings or benchmark
   claims.
7. **Local dependencies.** GSAP, ScrollTrigger, Lenis and Three.js are copied
   into the repository with package-lock versions and SHA-256 verification.
8. **Graceful degradation.** Reduced-motion users receive a static SVG state
   that still follows the story steps; WebGL initialization failure uses the
   same fallback rather than leaving a blank canvas.
9. **Keep the nav and repo link.** The page retains the requested persistent
   navigation and adds a closing “Open repo” action.

## Checks and evidence

These are historical results from the earlier showcase pass on 2026-10-19,
not new checks of the current iteration. Use the latest receipt above.

### Passed

- `make test` from the repository root
  - **60 tests passed**.
- `node --check story.js` from `showcase/`
  - passed.
- `npm run verify-vendor --offline` from `showcase/`
  - passed; **8 checked-in vendor files verified**.
- Local HTTP smoke from the repository root using
  `python3 -m http.server 4177 --directory showcase` plus `curl`:
  - passed; local CSS, story module, local library paths and seven story labels
    were present in the served page.
- `git diff --check` for the showcase files:
  - passed.

### Browser review

- Google Chrome headless was used against the local server because the built-in
  browser open tool timed out on the local tab.
- Desktop snapshots were captured at multiple scroll fractions, including the
  contract, locked-test, gate and merge states. The revised panel visibility
  logic removed the earlier text-overlap issue caused by simultaneous GSAP and
  CSS opacity transitions.
- The page was also checked at the final merge state and at the top state after
  returning upward.
- A full interactive top-to-bottom-and-back pass in a user-controlled browser,
  plus a dedicated 360px touch audit, is **still pending**. Do not mark the
  showcase visually final until those two checks are completed.

### Not a showcase failure

The current working tree also contains a separate benchmark implementation and
generated benchmark artifacts. They are not part of this showcase handoff:

- `src/cdavc/providers.py`
- `src/cdavc/benchmark.py`
- `tests/test_benchmark.py`
- `Makefile`
- `.gitignore`
- `benchmarks/`
- `results/`

There are also local tool/debug artifacts that are not production showcase
files: `.freebuff/`, `showcase/.ogcode/`, `showcase/ogcode.json`,
`showcase/_audit.html` and `showcase/_debug.html`. Preserve or remove them
deliberately; do not accidentally include them in the showcase commit.

## Original gaps and blockers (historical)

- The current showcase changes are **uncommitted**.
- No Vercel deployment has been performed in this session; Vercel CLI
  authentication was previously blocked by `Logged out.`
- `showcase/story.js` contains an `audit-progress` query helper used only for
  local screenshot checks. Decide whether to remove it before production or
  keep it as a harmless QA hook.
- `TaskScene.destroy()` disposes the renderer but does not explicitly dispose
  every geometry/material. This only matters if reduced-motion preference is
  toggled repeatedly in one page lifetime; it is not part of the normal static
  deployment path.
- The current browser evidence is headless snapshot evidence, not a signed-off
  interactive QA session.

## Original next action (historical)

Start with the showcase-only diff, leave the benchmark files untouched, and:

1. Run a real browser pass at desktop and 360px: scroll from the page top to
   the end of the pinned scene and back to the top, checking pinning, step
   transitions, merge state, touch scrolling, and reduced-motion fallback.
2. Remove `_debug.html` and `_audit.html` if no longer needed, and decide whether
   the `audit-progress` hook should remain.
3. Re-run `make test`, `npm run verify-vendor --offline`, `node --check story.js`
   and the static HTTP smoke.
4. Stage only the intended showcase files plus this handoff; do not stage the
   unrelated benchmark files or local tool artifacts.
5. Commit with a focused message, then deploy with
   `vercel deploy --cwd showcase` after authenticating Vercel.

The intended resumable entry point is `showcase/index.html`, with the runtime
in `showcase/story.js` and visual system in `showcase/story.css`.

---
title: "CD-AVC showcase QA, commit and temporary Vercel deploy"
session_id: "ses_01M5AG6HB7WXP26853ENK57XR5"
session_type: "build"
project_id: "/Users/billasur/Projects/cdavc/showcase"
created_at: 2026-10-19T17:06:20Z
---

# CD-AVC showcase QA, commit and temporary Vercel deploy

Topics: cdavc showcase, story.js resize, Vercel temp deploy, README hunk staging, reduced-motion QA

## Request

The developer's only instruction was "continue where u left off" in the repo `/Users/billasur/Projects/cdavc`. There was no session memory, so the agent reconstructed state from the working tree and `docs/SHOWCASE_HANDOFF.md`, then resumed the handoff plan: finish the real-browser QA pass on the uncommitted showcase rebuild (`showcase/`, a scroll-driven Three.js story with 7 beats), clean up debug artifacts, run checks, stage only intended files, then commit and optionally deploy.

No developer corrections or preference statements were given during the turn; the agent's own open questions were put to the developer via a two-part `ask_user` prompt ("Commit changes": *Commit showcase files only* / *Commit everything* / *Leave uncommitted*; "Deploy": *No, skip deploy* / *Yes, deploy it*), and the turn was completed without waiting on an answer.

## What was done

### Scene framing fix in `showcase/story.js`
`TaskScene.resize()` previously used a binary `width < 700` compact cutoff that disagreed with the CSS layout switch, so the lime torus gate and tree lines crossed the vertical rail text at ~860/715px widths (seen earlier in `/tmp/crop-rail-86.png`, `/tmp/crop-rail-715.png`). It was rewritten to measure the available band and fit the scene into it:

- `compact = window.matchMedia('(max-width: 1180px)').matches`, stored as `this.compact`; `fov = compact ? 38 : 30`.
- `halfHeight = Math.tan(fov * Math.PI / 360) * 980`, `pxPerUnit = height / 2 / halfHeight`.
- Gutter from the CSS variable `--page-gutter` (fallback 32).
- Compact layout: band from `.story-meta` bottom + 26 down to `.story-copy` top − 18. Wide layout: band from `.story-copy` right + 16 to `.story-rail` left − 16.
- `regionWidth = Math.max(140, right - left)`, `regionHeight = Math.max(140, bottom - top)`, `scale = Math.min(1, regionWidth * .92 / (430 * pxPerUnit), regionHeight * .92 / (300 * pxPerUnit))`, then `baseX` / `baseY` centre the group in that band.
- Camera sway changed to `Math.sin(this.progress * Math.PI * 1.4) * (this.compact ? 12 : 30)`.

### CSS breakpoint change in `showcase/story.css`
`@media (max-width: 860px)` → `@media (max-width: 1180px)`, matching the JS `matchMedia` cutoff (copy moves to the bottom, rail becomes header dots, vertical wash below 1180px).

### Debug artifact removal
`showcase/_audit.html` and `showcase/_debug.html` were deleted (`rm -f`, they were untracked). Confirmed via grep that the old `audit-progress` QA hook no longer exists anywhere in `story.js` / `index.html` / `story.css`.

### Checks run
`node --check showcase/story.js` (clean), `JSON.parse` of `showcase/vendor/manifest.json` (OK), HTTP 200 on `/`, `/story.js`, `/story.css` from the local server, `npm run verify-vendor --offline` (passes, 8 files), and `make test` at repo root (61 tests).

### Browser QA sweep (all passed)
Screenshotted through Chrome CDP with `node /Users/billasur/Projects/.tools/shot.mjs <url> <out.png> "<js>"` (env `VW`/`VH`/`WAIT`/`STABILISE`/`DPR`/`CLIP`), scrolling with `document.querySelector('#task-story')` offsets:

- 1600×1000 at every step plus the merge frame; 1280×900; 1181×900 and 1180×900 (the breakpoint boundary, checked again after the change from 860 to 1180); 1024×768; 880×900; 901×700; 715×1000; 700×900; 390×844; 360×800.
- Result: no rail overlap, no clipping of the merge frame, no horizontal overflow (`scrollWidth` equals `innerWidth` at 360 and 1180).
- Reversed scroll (bottom → top at 1600×1000) restored step `01 / 07` and the canvas.
- `prefers-reduced-motion` tested with a patched copy of the shot tool at `/tmp/shot-reduced.mjs` (injects `Emulation.setEmulatedMedia` with `prefers-reduced-motion: reduce`): static SVG replaces the canvas, sticky pin and readout tracking still work, at 1600×1000 top, 1600×1000 mid and 390×844.

### Staging and commit
- README was staged by hunk: `git diff -U3 README.md | awk '/^@@ -99,6 \+109,72 @@/{exit} {print}' > /tmp/readme-showcase.patch` then `git apply --cached /tmp/readme-showcase.patch`, keeping only the showcase-section and `verify-vendor` hunks; the "How to reproduce the benchmark" hunk stayed unstaged.
- Staged explicitly: `showcase/index.html`, `showcase/story.css`, `showcase/story.js`, `showcase/vendor/README.md`, `showcase/vendor/manifest.json`, `showcase/vendor/three.core.min.js`, `docs/SHOWCASE_HANDOFF.md`.
- Committed: `399be78 feat(showcase): rebuild task-patch scroll story` — 8 files, +939/−64.

### Deploy
- `vercel whoami` showed the CLI (v61.1.0) is logged out, so a clean copy was assembled at `/tmp/cdavc-showcase-deploy` (`index.html`, `story.css`, `story.js`, `vendor/`) and deployed with `vercel deploy --temporary --yes`.
- Live URL: **https://temporary-spry-crater-hz50485.vercel.app**
- Verified live: `/`, `/story.js`, `/story.css`, `/vendor/three.module.min.js`, `/vendor/gsap.min.js` all return 200; body class reaches `story-module-loaded webgl-ready`; a 1600×1000 capture at step 05 matches the local build at `http://127.0.0.1:4173/`.

### MEMORY.md note
Appended a "## cdavc showcase (static scroll story)" section to `/Users/billasur/Projects/MEMORY.md` recording the commit hash, the local preview command and the `localhost:4173` vs `127.0.0.1:4173` gotcha, the logged-out Vercel CLI / `--temporary` route with its 60-minute expiry, the clean-copy deploy rule, and the 1180px breakpoint plus QA widths.

## Key files & symbols

- `/Users/billasur/Projects/cdavc/showcase/story.js` — `TaskScene.resize()`, `this.compact`, `this.baseX` / `this.baseY`, `this.group.scale`; 369 lines before edits.
- `/Users/billasur/Projects/cdavc/showcase/story.css` — breakpoint now `@media (max-width: 1180px)`; `--page-gutter`; 399 lines.
- `/Users/billasur/Projects/cdavc/showcase/index.html` — DOM hooks `#task-story`, `#story-stage`, `.story-copy`, `.story-meta`, `.story-rail`, `.story-readout`.
- `/Users/billasur/Projects/cdavc/docs/SHOWCASE_HANDOFF.md` — the unfinished plan that drove the turn (modified and committed).
- `/Users/billasur/Projects/cdavc/showcase/vendor/` — `three.core.min.js` (new, large), `manifest.json`, `README.md`.
- Deleted: `showcase/_audit.html`, `showcase/_debug.html`.
- `/Users/billasur/Projects/.tools/shot.mjs` — CDP screenshot helper; `/tmp/shot-reduced.mjs` its reduced-motion-patched copy.
- `/Users/billasur/Projects/cdavc/showcase/package.json` — `verify-vendor --offline` script.

## Decisions & why

- **Staged README by hunk rather than whole-file:** the benchmark reproduction section is unrelated to the showcase and its code is still untracked, so committing it would have half-landed that work.
- **Deployed from `/tmp/cdavc-showcase-deploy`, not `showcase/`:** uploading the directory would have published the local `ogcode.json` and `.ogcode/` SQLite DB.
- **Used `--temporary`:** the CLI is unauthenticated; the alternative was stopping to ask for a login, and the claim link preserves ownership either way. Flagging expiry since that is the real cost of this route.
- (Earlier in the turn) **Single 1180px breakpoint shared by CSS and JS** instead of the mismatched 860px (CSS) / 700px (JS) pair, because the overlap bug came from the two disagreeing.

## Outcome

Committed and deployed.

- Commit `399be78 feat(showcase): rebuild task-patch scroll story` landed on `main` (8 files, +939/−64). NOT committed, deliberately: the README "How to reproduce the benchmark" hunk, plus local-only `.freebuff/`, `showcase/.ogcode/`, `showcase/ogcode.json`. Benchmark code (`benchmarks/`, `results/`, `src/cdavc/benchmark.py`, `providers.py`, `tests/test_benchmark.py`, `Makefile`, `.gitignore`) also left untouched/unstaged. The branch was already 8 commits ahead of origin; nothing was pushed.
- Deployment is live and verified, but is an **anonymous temporary deployment that expires in 60 minutes**. Ownership can be claimed with a one-time link: `https://vercel.com/claim-deployment?code=<redacted>` (the agent noted it is private — anyone with it can take ownership).
- Open / next steps stated by the agent: run `vercel login` and redeploy from a clean copy of `showcase/` for a permanent URL, or add a `.vercelignore` if the directory is to stay tracked. The handoff's open item about an `audit-progress` QA hook is moot — that helper is no longer in `story.js`.
- QA caveat: everything above was exercised against the local build at `http://127.0.0.1:4173/` and the temporary deploy; the response reports all checks passing, including `make test` → 61 tests and vendor verify → 8 files.

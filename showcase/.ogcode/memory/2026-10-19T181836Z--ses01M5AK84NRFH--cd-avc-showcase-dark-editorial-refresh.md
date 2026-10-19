---
title: "CD-AVC showcase dark editorial refresh"
session_id: "ses_01M5AK84NRFHVT0Z843SAVFJ1H"
session_type: "build"
project_id: "/Users/billasur/Projects/cdavc/showcase"
created_at: 2026-10-19T18:18:36Z
---

# CD-AVC showcase dark editorial refresh

Topics: showcase scroll story, WebGL contrast pass, gate screens, compact layout, screenshot QA

## Request
The developer opened with one line: "ok so the showcase doesn't look so good" — a vague visual complaint about the CD-AVC scroll-story page at `/Users/billasur/Projects/cdavc/showcase/` (`index.html`, `story.css`, `story.js`). They did not specify what was wrong; the agent had to diagnose before acting.

## What was done

### Blocking bug found and fixed first
The 3D story died after the first screen (everything below was plain black) because `story.js` referenced a rig-fit constant that did not exist. Added next to the scene constants after `REPO_Z = 170`:

- `const RIG_HEIGHT = 682;`
- `const RIG_CENTER_Y = 129;`

with a comment noting the contract card (380 + 90) is the highest element and the floor plane the lowest. After this the page scrolled through all 7 beats.

### Clarifying questions asked of the developer
An `ask_user` call with two questions. Developer answers, verbatim:

- Q1 "what bothers you most when you look at it?" (multi-select): **"Too dark / muddy"**, **"Text collides with the 3D"**, **"Composition is untidy"**. (The fourth option, "The whole look is wrong" — restart the visual concept — was not chosen.)
- Q2 "If I go beyond fixing defects, which direction should the page take?": **"Refine the dark editorial look"** — keep black + lime + mono plates, raise contrast, clean up composition, add depth and polish.

### Visual diagnosis (CDP screenshots at 1600×1000, beats 1/2/3/4/6, plus 390-wide)
- Gate frames read as faint olive outlines on near-black; interiors near-black; grid floor barely visible; contract card dark.
- At beats 3–6 the headline column (64–534px) overlapped drifting gate label plates (e.g. a "TEST SEAL" plate at 361–604px in the same y band 325–465px); the right step rail (~1387–1600px) sat on top of GATE 03/04 plates.
- GATE 04 hard-cropped at the right viewport edge (x=1600); the contract card ghost lingered at ~0.55 opacity behind the top-left eyebrow "TASK_001 · COUNT VOWELS" from beat 3 onward; at beat 7 the "working tree" repo card bled off the bottom and collided with `.story-disclaimer`.

### `story.css` edits (uncommitted)
- `:root`: `--muted: #9ba69e` (was `#8d9790`), `--quiet: #748077` (was `#56615a`).
- `.story-wash` desktop (≈L106-112) replaced with a two-layer gradient: `radial-gradient(120% 88% at 62% 38%, rgba(11,14,13,0) 30%, rgba(4,7,5,.66) 100%)` plus `linear-gradient(90deg, rgba(11,14,13,.99) 0%, .975 32%, .85 41%, .44 52%, .1 63%, 0 73%, .3 82%, .62 88%, .86 93%, .97 98%, .99 100%)` (tuned twice after screenshot review — the first draft kept `.78 40% / .34 52% / .06 64% / 0 74% / .34 88% / .78 100%`).
- `.story-rail` (≈L196-212): dropped its own `background` and its vertical `mask-image` (both `-webkit-` and standard); padding set to `30px var(--page-gutter) 30px 48px`; added `.story-rail::before` (`position:absolute; top:-50vh; bottom:-50vh; right:0; left:0; z-index:-1; content:""; pointer-events:none; background: linear-gradient(90deg, rgba(11,14,13,0) 0%, rgba(11,14,13,.86) 16%, rgba(11,14,13,.97) 34%, rgba(11,14,13,.99) 100%)`) — a full-height right-hand scrim so gate plates dissolve under the rail instead of hard-cropping at x=1600.
- `.story-disclaimer`: `color: #7a857d`, `text-shadow: 0 1px 10px rgba(5,8,6,.95)`.
- Compact (≤1180) `.story-wash`: `radial-gradient(96% 66% at 50% 30%, rgba(11,14,13,0) 20%, rgba(5,8,6,.78) 100%)` (was `100% 70% at 50% 32% … .5`), keeping the same vertical linear-gradient.
- Compact copy block: `.story-copy` bottom `92px → 80px` (≤1180) and `86px → 68px` (≤520).

### `story.js` edits (uncommitted)
- `renderer.toneMappingExposure` `1.06 → 1.16`; `scene.fog` `(0x0b0e0d, 950, 2600) → (0x0b0e0d, 1700, 3200)`.
- Lights: hemisphere `.75 → 1.0`, key directional `2.1 → 2.4`, rim `0xd8ff64` `1.15 → 1.35`, fill `0x8fb6a0` `.6 → .8`.
- Gate strips: base opacity `.16 → .26`; `applyState` sets `gate.strips.opacity = .26 + pass * .6`.
- `applyState`: `contractFade = .95 - smoothstep(.12, .3, p) * .95` (card ghost now fully fades instead of hanging at .55).
- Camera in `applyState`: `const lookY = this.lookY - smoothstep(.82, .98, p) * 44;` and `const cameraZ = 1500 - smoothstep(.55, .82, p) * 150 + smoothstep(.78, 1, p) * 210;`.
- `MUTED` const `'rgba(188, 201, 191, .68)' → 'rgba(202, 214, 204, .84)'`.
- New `gateScreenTexture()` (lazy singleton `gateScreenMap`, placed just above `backdropTexture()`): 256×304 canvas, vertical gradient `#0f1813 → #0a110e → #070b09`, hairline grid `rgba(160,188,166,.12)` every 32px, lime radial glow `rgba(216,255,100,.05)`, lime corner brackets `rgba(216,255,100,.22)` with 22px corners.
- `constructor`: added `this.screenBase = new THREE.Color(0x8b978f)` and `this.screenPass = new THREE.Color(0xffffff)`.
- `buildGate()`: new screen mesh `PlaneGeometry(innerW, innerH)` with `MeshBasicMaterial({ map: gateScreenTexture(), color: 0x8b978f, transparent: true, toneMapped: false, side: DoubleSide })` at `z=-6` (behind the patch at z 3..17 so they never intersect), returned as `screenMaterial`.
- `applyState` gate loop: `gate.labelMaterial.opacity = .72 + pass * .26`; `gate.screenMaterial.color.copy(this.screenBase).lerp(this.screenPass, pass)`.
- Other contrast nudges: cage edges `.11 → .16`; `gridTexture()` minor `rgba(150,176,154,.17)`, major `rgba(216,255,100,.2)`; patch comment colour `#93a79a → #a9bfae`; repo `main · clean` `rgba(184,200,188,.86)`; repo filenames `rgba(190,206,194,.74)`; patch footer `rgba(202,214,204,.84)`.
- `resize()`: `const fitted = regionHeight * (compact ? .95 : .9) / (RIG_HEIGHT * pxPerUnit);` then `this.scale = Math.max(.35, Math.min(2.6, fitted));`; camera side offset `const side = this.compact ? 40 : 220;` (was `80 : 220`; a first edit wrote bare `compact` and was corrected to `this.compact`).

### Screenshot harness work
- Started `python3 -m http.server 4178 --directory showcase` and a headed Chrome with `--remote-debugging-port=9333 --user-data-dir=/tmp/chrome-cdavc-profile --window-size=1600,1000`.
- Wrote `/tmp/cshot2.mjs`, a CDP capture script: env `VW VH BEAT WAIT STABILISE DPR CLIP PRE POST`, `P` overrides the beat, default scroll y = `(BEAT+.5)/7 * (scrollHeight-innerHeight)`. It installs a no-op `window.Lenis = class Lenis { on(){} raf(){} destroy(){} scrollTo(){} }` before navigation because `story.js` drives Lenis from the gsap ticker which fights `window.scrollTo`. One navigation+capture per invocation; parallel runs share the CDP tab and return each other's frames.
- Composed contact sheets with `ffmpeg hstack` and cropped zooms with `sips`.

### The mobile kicker "dim rectangle" — closed as a capture artifact
At 390×844 the step kicker (`02 / THE BOUNDED PATCH`) rendered with a sharp-edged dim band over part of the text in some captures. After many variants (red-fill, `z-index:9`, `translateZ(0)`, disabling `.story-wash`, disabling `#task-canvas`, DPR 2, focus emulation, fresh single-capture navigations with md5 comparison) the agent concluded it is not a page bug: `elementsFromPoint` returns the normal stack and computed styles are uniform. It is recorded in `MEMORY.md` as a known capture artifact — do not "fix" it in CSS.

### `MEMORY.md` notes added (`/Users/billasur/Projects/MEMORY.md`)
- Compact cutoff is 1180px via `matchMedia` in `story.js` and the same breakpoint in `story.css`; QA covered 1600/1280/1181/1180/1024/715/390/360 widths, reversed scroll and `prefers-reduced-motion`.
- Screenshot harness instructions (server port 4178, `/tmp/cshot2.mjs`, env vars, one capture per invocation, headless Chrome hangs on this machine → attach over CDP port 9333).
- Known capture artifact entry for the kicker band.
- Scene-contrast record: every gate has an interior screen mesh whose colour lerps `0x8b978f` → white on pass; the first attempt at `.17` grid / `.1` glow / full brightness read as lit displays and dominated the frame — keep it dark. Plus the raised alphas listed above.
- Compact layout numbers: `.story-copy` bottom 80px (≤1180) / 68px (≤520); `resize()` fits `.95` on compact / `.9` desktop; camera side offset 40 compact / 220 desktop.
- Correction of an earlier note: the rig is ~2.5:1 so on a phone it is width-cropped by design, and that cut is real geometry leaving the frame, not the CSS wash — verified by disabling `.story-wash` at 390×844 (identical framing, only brighter); the left/right fades exist only in the ≥1181 desktop rule.

### Preview
Killed the server on 4178, copied `index.html`, `story.css`, `story.js` and `vendor/` into `/tmp/cdavc-preview`, and re-served that directory on port 4178, so the preview at **http://4178.preview.localhost:9604/** does not expose the local-only `ogcode.json` / `.ogcode/` files sitting in `showcase/`.

## Key files & symbols
- `/Users/billasur/Projects/cdavc/showcase/index.html` (130 lines), `story.css` (434 lines), `story.js` (1181 lines)
- `story.js`: `RIG_HEIGHT`, `RIG_CENTER_Y`, `FLOOR_Y = -212`, `PATCH_Y = 50`, `PATCH_Z = 40`, `REPO_Z = 170`, `GATE_X`, `GATE_THRESHOLDS`, `gateScreenTexture()`, `gateScreenMap`, `backdropTexture()`, `plateTexture()`, `monoPlateTexture()`, `contractTexture()`, `patchTexture()`, `gridTexture()`, `buildGate()`, `applyState()`, `resize()`, `buildLights()`, `MUTED`, `screenBase`, `screenPass`, `setStep()`, `initStoryScene()`, `setupScroll()`, `setupLenis()`
- `story.css`: `:root`, `.task-story` (`height:800vh`), `.story-pin`, `.story-wash`, `.story-copy`, `.story-panel`, `.story-rail`, `.story-rail::before`, `.story-disclaimer`, `.story-kicker`, breakpoints at 1180px and 520px, `prefers-reduced-motion`
- Harness: `/tmp/cshot2.mjs`, `/tmp/kick.mjs`, `/tmp/kick2.mjs`, `/tmp/kick4.mjs`, `/tmp/kick5.mjs`, `/tmp/cshot.mjs`, `/Users/billasur/Projects/.tools/shot.mjs`
- `/Users/billasur/Projects/MEMORY.md`
- Repo `/Users/billasur/Projects/cdavc`; last commit seen `399be78`

## Decisions & why
- **Made the gates look switched-off rather than absent.** They animate on pass, so they need a visible dark surface to change from; the first attempt was bright enough to dominate the whole frame, so the screen colour starts at `0x8b978f` and lerps to white only for the pass state.
- **Fixed the contrast in the materials, not with a global exposure bump.** Raising `toneMappingExposure` would have washed out the black floor and the copy; nudging individual alphas keeps the depth ordering.
- **Reverted a compact ×.86 scale shrink** (`this.scale = … * (compact ? .86 : 1)`) — it only enlarged the empty band under the copy instead of tightening the framing; the real win was moving the copy block down and reducing the camera's side offset.
- **Served the preview from a clean copy** rather than `--directory showcase`, because the working dir holds local-only config that the preview proxy would otherwise expose.
- **Left the `SHOTS` array (~L479-487) alone** — it is dead code.

## Outcome
- Blocking `RIG_HEIGHT` crash: fixed, verified on screen (all 7 beats scroll).
- Contrast/mud, text-vs-3D collisions, right-edge plate crops, contract-card ghost, and compact dead band: all changed and verified via screenshots.
- Verified at 1600×1000 (beats 0/2/4/6), 1024×768, and 390×844 DPR 2; the final re-check rendered from the clean `/tmp/cdavc-preview` copy.
- Accepted nit: at p≈.85 the "SOURCE OF TRUTH working tree" plate is cut by the repo cabinet, read as depth.
- Known limitation documented, not fixed: on a phone the rig is genuinely wider than the viewport and crops at the left/right edges; the ≤1180 wash is vertical-only so nothing softens those edges.
- Nothing committed. `showcase/{index.html,story.css,story.js}` are modified in the working tree; pre-existing unrelated modifications to `benchmarks/tasks.json` and `src/cdavc/benchmark.py` were left untouched.

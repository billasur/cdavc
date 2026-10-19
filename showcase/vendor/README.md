# Offline showcase vendor bundle

This directory contains the checked-in browser artifacts used by the showcase
rebuild. `index.html` loads the local classic GSAP, ScrollTrigger and Lenis
bundles; `story.js` imports the local Three.js ESM entry point. No CDN or
runtime package fetch is required.

## Pinned sources

The install-time source packages and their integrity values are pinned in
[`../package.json`](../package.json) and [`../package-lock.json`](../package-lock.json).
The exact package entry copied into each browser artifact is recorded in
[`manifest.json`](manifest.json), alongside a SHA-256 checksum for every file.

| Package | Version | Vendored entry points | License |
| --- | ---: | --- | --- |
| `gsap` | `3.15.0` | `gsap.min.js`, `ScrollTrigger.min.js` | GSAP standard no-charge license |
| `lenis` | `1.3.26` | `lenis.min.js`, `lenis.mjs` | MIT |
| `three` | `0.180.0` | `three.module.min.js` | MIT |

## Loading constraints

- `ScrollTrigger.min.js` expects the local `gsap.min.js` classic script to be
  loaded first.
- `lenis.min.js` is the classic browser bundle. `lenis.mjs` is the local ESM
  entry point; use one entry point, not both.
- `three.module.min.js` is an ESM build with one local relative dependency,
  `three.core.min.js`; both are checked in and served from this directory.
- The files are served directly by a static host. They do not require a build
  step, CDN URL, or runtime package fetch.
- `npm run verify-vendor` uses only Node built-ins and works without
  `node_modules` or network access after checkout.

Three.js `0.180.0` is pinned because its published package includes the
official minified ESM browser entry point. The package lock remains the source
of truth if the bundle is intentionally refreshed later.

The GSAP license notice is retained in the vendored file headers. The MIT
license texts shipped by Lenis and Three.js are copied beside their artifacts.

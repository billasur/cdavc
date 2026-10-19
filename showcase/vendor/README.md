# Offline showcase vendor bundle

This directory contains checked-in browser artifacts for the planned showcase
rebuild. The current `showcase/index.html` intentionally remains unchanged;
these files are available for a later local-script or ESM integration without
adding a network dependency.

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
- `three.module.min.js` is an ESM build and has no bare package import to
  resolve. Import it from a local relative path.
- The files are served directly by a static host. They do not require a build
  step, CDN URL, or runtime package fetch.
- `npm run verify-vendor` uses only Node built-ins and works without
  `node_modules` or network access after checkout.

Three.js `0.180.0` is pinned because its published package includes the
official minified ESM browser entry point. The package lock remains the source
of truth if the bundle is intentionally refreshed later.

The GSAP license notice is retained in the vendored file headers. The MIT
license texts shipped by Lenis and Three.js are copied beside their artifacts.

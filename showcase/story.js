import * as THREE from './vendor/three.module.min.js';

const { gsap, ScrollTrigger, Lenis } = window;
document.body.classList.add('story-module-loaded');
gsap.registerPlugin(ScrollTrigger);

/* ------------------------------------------------------------------ *
 * Page wiring: copy panels, step rail, scroll, one render loop.
 * ------------------------------------------------------------------ */
const body = document.body;
const story = document.querySelector('#task-story');
const pin = document.querySelector('.story-pin');
const canvas = document.querySelector('#task-canvas');
const panels = [...document.querySelectorAll('.story-panel')];
const railItems = [...document.querySelectorAll('.story-rail li')];
const stageReadout = document.querySelector('#story-stage');
const staticVisual = document.querySelector('.static-visual');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
const STEPS = 7;

let isReduced = reduced.matches;
let world = null;
let lenis = null;
let trigger = null;
let lastStep = -1;
let targetProgress = 0;

const clamp01 = (v) => Math.max(0, Math.min(1, v));
const lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, v) => { const x = clamp01((v - a) / Math.max(1e-6, b - a)); return x * x * (3 - 2 * x); };

function setStep(step) {
  const s = Math.min(STEPS - 1, Math.max(0, step));
  if (s === lastStep) return;
  lastStep = s;
  stageReadout.textContent = `${String(s + 1).padStart(2, '0')} / 07`;
  staticVisual.dataset.step = String(s);
  panels.forEach((panel, i) => {
    panel.classList.toggle('is-current', i === s);
    panel.setAttribute('aria-hidden', String(i !== s));
  });
  railItems.forEach((item, i) => item.classList.toggle('is-current', i === s));
}

function stepFromProgress(p) {
  // a little past the boundary so the copy swaps while the camera is mid-move
  return Math.min(STEPS - 1, Math.floor(p * STEPS + 0.18));
}

function setReducedState() {
  isReduced = reduced.matches;
  body.classList.toggle('is-reduced-motion', isReduced);
  if (isReduced) {
    const p = clamp01((window.scrollY - story.offsetTop) / Math.max(1, story.offsetHeight - window.innerHeight));
    setStep(stepFromProgress(p));
  }
}

function tick(time) {
  lenis?.raf(time * 1000);
  world?.frame(time);
}

function setupScroll() {
  if (isReduced) return;
  initWorld();
  const state = { progress: 0 };
  const update = (p) => { targetProgress = p; setStep(stepFromProgress(p)); };
  update(0);
  trigger = gsap.to(state, {
    progress: 1,
    ease: 'none',
    scrollTrigger: {
      trigger: story,
      start: 'top top',
      end: 'bottom bottom',
      pin,
      pinSpacing: false,
      scrub: true,
      invalidateOnRefresh: true,
      onUpdate: (self) => update(self.progress),
      onRefresh: (self) => update(self.progress),
    },
  });
}

function setupLenis() {
  if (isReduced) return;
  lenis = new Lenis({ duration: 1.05, smoothWheel: true, syncTouch: false, autoRaf: false });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(1000, 16);
}

function teardown() {
  trigger?.kill();
  trigger = null;
  if (lenis) { gsap.ticker.remove(tick); lenis.destroy(); lenis = null; }
  world?.destroy();
  world = null;
  ScrollTrigger.getAll().forEach((t) => t.kill());
}

function initWorld() {
  if (world || isReduced) return;
  try {
    world = new World(canvas);
    body.classList.add('webgl-ready');
  } catch (error) {
    body.classList.add('no-webgl');
    console.warn('CD-AVC 3D scene unavailable; showing the static fallback.', error);
  }
}

/* ------------------------------------------------------------------ *
 * Look
 * ------------------------------------------------------------------ */
const BG = 0x0b0e0d;
const ACCENT = 0xd8ff64;
const INK = 0xf4f6f1;
const FAIL = 0xff7a59;
const ACCENT_CSS = '#d8ff64';
const INK_CSS = '#f4f6f1';
const GREY_CSS = '#7d8981';
const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace';
const SP = 8;                  // distance between stations on the x axis
const DIM = 0.15;              // opacity of an inactive object
const CARD_W = 3;
const CARD_H = 2;

function canvasTex(wu, hu, draw, ppu = 300) {
  const c = document.createElement('canvas');
  c.width = Math.round(wu * ppu);
  c.height = Math.round(hu * ppu);
  const g = c.getContext('2d');
  draw(g, c.width, c.height, ppu);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

function roundedShape(w, h, r) {
  const s = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

function slabGeometry(w, h, depth, r) {
  const g = new THREE.ExtrudeGeometry(roundedShape(w, h, r), {
    depth, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 3, curveSegments: 10,
  });
  g.translate(0, 0, -depth / 2);
  return g;
}

function outline(w, h, r, color, opacity) {
  const pts = roundedShape(w, h, r).getPoints(10).map((p) => new THREE.Vector3(p.x, p.y, 0));
  const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
  line.material.userData = { base: opacity, k: 1 };
  return line;
}

/* ------------------------------------------------------------------ *
 * Stations: per-station fade registry. Every material carries a base
 * opacity and an animation factor k; the world multiplies by a fade
 * weight (1 when active, DIM when not).
 * ------------------------------------------------------------------ */
class Bucket {
  constructor() { this.mats = []; }
  add(m, base = 1) {
    m.transparent = true;
    m.userData = { base, k: 1 };
    this.mats.push(m);
    return m;
  }
  track(m) { this.mats.push(m); return m; }
  apply(w) { for (const m of this.mats) m.opacity = m.userData.base * m.userData.k * w; }
}

function planeMat(bucket, tex, base = 1) {
  return bucket.add(new THREE.MeshBasicMaterial({ map: tex, depthWrite: false, toneMapped: false, fog: false }), base);
}
function flatMat(bucket, color, base = 1) {
  return bucket.add(new THREE.MeshBasicMaterial({ color, depthWrite: false, toneMapped: false }), base);
}
function line(bucket, geo, color, base) {
  const m = bucket.add(new THREE.LineBasicMaterial({ color }), base);
  return new THREE.LineSegments(geo, m);
}
function textPlane(bucket, wu, hu, draw, base = 1) {
  const m = planeMat(bucket, canvasTex(wu, hu, draw), base);
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(wu, hu), m);
  mesh.renderOrder = 3;
  return mesh;
}
function fitText(g, text, maxW, size) {
  g.font = `500 ${size}px ${MONO}`;
  const w = g.measureText(text).width;
  if (w > maxW) g.font = `500 ${Math.floor(size * maxW / w)}px ${MONO}`;
}

/* ------------------------------------------------------------------ *
 * World
 * ------------------------------------------------------------------ */
class World {
  constructor(canvasEl) {
    this.canvas = canvasEl;
    const params = new URLSearchParams(location.search);
    this.tier = this.pickTier(params.get('quality'));
    this.renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: this.tier < 2, alpha: false, powerPreference: 'high-performance' });
    this.renderer.setClearColor(BG, 1);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(BG, 12, 30);
    this.camera = new THREE.PerspectiveCamera(30, 1.6, 0.1, 80);
    this.progress = 0;
    this.velocity = 0;
    this.lastTime = 0;
    this.frameMs = [];
    this.disposed = false;
    this.post = null;
    this.tags = [];
    this.buckets = Array.from({ length: STEPS }, () => new Bucket());
    this.cardBucket = new Bucket();
    this.rejectBucket = new Bucket();

    this.buildEnvironment();
    this.buildBackdrop();
    this.buildCard();
    this.buildContractRows();
    this.buildCodeLines();
    this.buildTests(2);
    this.buildAst(3);
    this.buildWorktree(4);
    this.buildGates(5);
    this.buildTree(6);
    this.buildReject();
    this.buildTags();

    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(canvasEl);
    this.resize();
    this.frame(0);
    body.classList.add('webgl-ready');
  }

  pickTier(forced) {
    if (forced === 'low') return 0;
    if (forced === 'mid') return 1;
    if (forced === 'high') return 2;
    const coarse = window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 720;
    const weak = (navigator.deviceMemory && navigator.deviceMemory <= 4) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);
    let software = false;
    try {
      const gl = document.createElement('canvas').getContext('webgl');
      const ext = gl?.getExtension('WEBGL_debug_renderer_info');
      const name = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : '';
      software = /swiftshader|llvmpipe|software/i.test(name);
    } catch { /* ignore */ }
    if (software) return 0;
    if (coarse || weak) return 1;
    return 2;
  }

  /* --- environment: a small offline studio, no HDR download --- */
  buildEnvironment() {
    const room = new THREE.Scene();
    const shell = new THREE.Mesh(new THREE.BoxGeometry(20, 12, 20), new THREE.MeshBasicMaterial({ color: 0x0c110e, side: THREE.BackSide }));
    room.add(shell);
    const panel = (w, h, x, y, z, color, power, ry = 0, rx = 0) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(power), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.rotation.set(rx, ry, 0); room.add(m);
    };
    panel(9, 4, 0, 5.8, 0, 0xffffff, 3.2, 0, Math.PI / 2);
    panel(1.4, 8, -9.5, 0, 2, 0xe9f2ec, 2.4, Math.PI / 2);
    panel(1.4, 8, 9.5, 0, -2, 0xe9f2ec, 1.6, Math.PI / 2);
    panel(7, 1.2, 0, 0.5, -9.5, ACCENT, 2.0);
    const pm = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pm.fromScene(room, 0.035).texture;
    this.scene.environmentIntensity = 0.9;
    pm.dispose();
    const key = new THREE.DirectionalLight(0xffffff, 0.8);
    key.position.set(3, 6, 6);
    this.scene.add(key);
  }

  /* --- floor lines and dust: quiet depth cues --- */
  buildBackdrop() {
    const pts = [];
    const x0 = -14, x1 = SP * (STEPS - 1) + 14, y = -1.75;
    for (let x = Math.ceil(x0); x <= x1; x += 1.5) { pts.push(x, y, -12, x, y, 5); }
    for (let z = -12; z <= 5; z += 1.5) { pts.push(x0, y, z, x1, y, z); }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    this.grid = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: INK, transparent: true, opacity: 0.07 }));
    this.scene.add(this.grid);

    if (this.tier >= 2) {
      const n = 420;
      const arr = new Float32Array(n * 3);
      for (let i = 0; i < n; i += 1) {
        arr[i * 3] = -12 + Math.random() * (SP * (STEPS - 1) + 24);
        arr[i * 3 + 1] = -1.6 + Math.random() * 4.4;
        arr[i * 3 + 2] = -10 + Math.random() * 13;
      }
      const pg = new THREE.BufferGeometry();
      pg.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      this.dust = new THREE.Points(pg, new THREE.PointsMaterial({ color: INK, size: 0.022, transparent: true, opacity: 0.35, sizeAttenuation: true, depthWrite: false }));
      this.scene.add(this.dust);
    }
  }

  /* --- the one object that travels the whole story --- */
  buildCard() {
    this.card = new THREE.Group();
    this.flip = new THREE.Group();
    this.card.add(this.flip);
    const bodyMat = this.cardBucket.add(new THREE.MeshPhysicalMaterial({
      color: 0x111915, metalness: 0.5, roughness: 0.32, clearcoat: 1, clearcoatRoughness: 0.18, envMapIntensity: 1.1,
    }), 1);
    bodyMat.depthWrite = true;
    const cardBody = new THREE.Mesh(slabGeometry(CARD_W, CARD_H, 0.06, 0.14), bodyMat); cardBody.renderOrder = 1; this.flip.add(cardBody);
    const edgeF = outline(CARD_W, CARD_H, 0.14, ACCENT, 0.7); edgeF.position.z = 0.046;
    const edgeB = outline(CARD_W, CARD_H, 0.14, ACCENT, 0.7); edgeB.position.z = -0.046;
    this.cardBucket.track(edgeF.material); this.cardBucket.track(edgeB.material);
    this.flip.add(edgeF, edgeB);
    this.front = new THREE.Group(); this.front.position.z = 0.05;
    this.back = new THREE.Group(); this.back.position.z = -0.05; this.back.rotation.y = Math.PI;
    this.flip.add(this.front, this.back);
    this.scene.add(this.card);
  }

  buildContractRows() {
    const B = this.cardBucket;
    const head = textPlane(B, CARD_W, CARD_H, (g, w, h, u) => {
      g.fillStyle = ACCENT_CSS; g.font = `600 ${0.115 * u}px ${MONO}`; g.textBaseline = 'middle';
      g.fillText('CONTRACT', 0.24 * u, 0.26 * u);
      g.fillStyle = GREY_CSS; g.textAlign = 'right'; g.fillText('task_001', w - 0.24 * u, 0.26 * u);
      g.strokeStyle = 'rgba(244,246,241,.14)'; g.lineWidth = 2;
      for (const y of [0.46, 0.96, 1.26, 1.56]) { g.beginPath(); g.moveTo(0.24 * u, y * u); g.lineTo(w - 0.24 * u, y * u); g.stroke(); }
    }, 1);
    this.front.add(head);
    const rows = [['files', 'solution.py'], ['expose', 'count_vowels'], ['retries', 'max 2']];
    this.rows = rows.map(([label, value], i) => {
      const y = 0.32 - i * 0.5 + 0.02;
      const mk = (lit) => textPlane(B, CARD_W, 0.5, (g, w, h, u) => {
        g.textBaseline = 'middle';
        g.fillStyle = GREY_CSS; g.font = `500 ${0.11 * u}px ${MONO}`; g.fillText(label, 0.24 * u, h / 2);
        g.fillStyle = lit ? ACCENT_CSS : '#cfd6d0'; g.font = `600 ${0.2 * u}px ${MONO}`; g.fillText(value, 0.95 * u, h / 2);
      }, 1);
      const dimP = mk(false), litP = mk(true);
      for (const p of [dimP, litP]) { p.position.set(0, y - 0.0, 0.002); this.front.add(p); }
      return { dim: dimP.material, lit: litP.material };
    });
  }

  buildCodeLines() {
    const B = this.cardBucket;
    const head = textPlane(B, CARD_W, CARD_H, (g, w, h, u) => {
      g.fillStyle = GREY_CSS; g.font = `500 ${0.11 * u}px ${MONO}`; g.textBaseline = 'middle';
      g.fillText('solution.py', 0.24 * u, 0.26 * u);
      g.fillStyle = 'rgba(244,246,241,.14)'; for (let i = 0; i < 3; i += 1) { g.beginPath(); g.arc(w - (0.3 + i * 0.13) * u, 0.26 * u, 0.034 * u, 0, 7); g.fill(); }
      g.strokeStyle = 'rgba(244,246,241,.14)'; g.lineWidth = 2; g.beginPath(); g.moveTo(0.24 * u, 0.46 * u); g.lineTo(w - 0.24 * u, 0.46 * u); g.stroke();
    }, 1);
    this.back.add(head);
    const code = ['def count_vowels(text):', '    total = 0', '    for ch in text.lower():', '        if ch in "aeiou":', '            total += 1', '    return total'];
    this.codeLines = code.map((txt, i) => {
      const plane = textPlane(B, 2.6, 0.24, (g, w, h) => {
        g.textBaseline = 'middle'; g.fillStyle = i === 0 ? ACCENT_CSS : '#d9dfd9';
        fitText(g, txt, w, 0.17 * 300); g.fillText(txt, 0, h / 2);
      }, 1);
      plane.position.set(0, 0.5 - i * 0.255 - 0.03, 0.002);
      this.back.add(plane);
      return plane.material;
    });
  }

  /* --- 03 sealed test box with a hash tag --- */
  buildTests(i) {
    const B = this.buckets[i];
    const g = new THREE.Group();
    g.position.set(SP * i + 0.85, 0, 0);
    const mat = B.add(new THREE.MeshPhysicalMaterial({ color: 0x111915, metalness: 0.5, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.2 }), 1);
    mat.depthWrite = true;
    const box = new THREE.Mesh(new THREE.BoxGeometry(1.7, 1.45, 1.7), mat);
    box.position.y = -0.12;
    g.add(box);
    const boxEdges = line(B, new THREE.EdgesGeometry(box.geometry), INK, 0.55); boxEdges.position.copy(box.position); g.add(boxEdges);
    const lidMat = B.add(new THREE.MeshPhysicalMaterial({ color: 0x151e19, metalness: 0.6, roughness: 0.25, clearcoat: 1 }), 1);
    lidMat.depthWrite = true;
    this.testLid = new THREE.Group();
    this.testLid.add(new THREE.Mesh(new THREE.BoxGeometry(1.82, 0.14, 1.82), lidMat));
    this.testLid.add(line(B, new THREE.EdgesGeometry(new THREE.BoxGeometry(1.82, 0.14, 1.82)), ACCENT, 0.9));
    g.add(this.testLid);
    const face = textPlane(B, 1.5, 1.2, (c, w, h, u) => {
      c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillStyle = '#d9dfd9'; c.font = `600 ${0.3 * u}px ${MONO}`; c.fillText('tests/', w / 2, h * 0.62);
      // padlock
      c.strokeStyle = ACCENT_CSS; c.lineWidth = 0.045 * u;
      c.beginPath(); c.arc(w / 2, h * 0.2 + 0.02 * u, 0.13 * u, Math.PI, 0); c.stroke();
      c.fillStyle = ACCENT_CSS; c.fillRect(w / 2 - 0.2 * u, h * 0.2 + 0.02 * u, 0.4 * u, 0.28 * u);
    }, 1);
    face.position.set(0, -0.1, 0.856);
    g.add(face);
    this.testFace = face.material;
    this.testRing = line(B, new THREE.EdgesGeometry(new THREE.BoxGeometry(2.0, 1.75, 2.0)), ACCENT, 0.5);
    this.testRing.position.y = -0.12;
    g.add(this.testRing);
    this.testGroup = g;
    this.scene.add(g);
  }

  /* --- 04 card passing through an AST bracket frame --- */
  buildAst(i) {
    const B = this.buckets[i];
    const g = new THREE.Group();
    g.position.x = SP * i;
    const W = 3.9, H = 2.8, T = 0.05, L = 0.7;
    const m = flatMat(B, ACCENT, 1);
    const bar = (w, h, x, y) => { const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, T), m); mesh.position.set(x, y, 0); g.add(mesh); };
    for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
      bar(L, T, sx * (W / 2 - L / 2), sy * H / 2);
      bar(T, L, sx * W / 2, sy * (H / 2 - L / 2));
    }
    this.astMembrane = new THREE.Mesh(new THREE.PlaneGeometry(W, H), flatMat(B, ACCENT, 0.04));
    g.add(this.astMembrane);
    const scanMat = flatMat(B, ACCENT, 0.9);
    this.astScan = new THREE.Mesh(new THREE.PlaneGeometry(W, 0.03), scanMat);
    this.astScan.position.z = 0.01;
    g.add(this.astScan);
    this.astGroup = g;
    this.scene.add(g);
  }

  /* --- 05 card inside a wireframe cage (git worktree) --- */
  buildWorktree(i) {
    const B = this.buckets[i];
    const g = new THREE.Group();
    g.position.x = SP * i;
    const cage = new THREE.Group();
    cage.add(line(B, new THREE.EdgesGeometry(new THREE.BoxGeometry(3.9, 2.9, 2.5)), ACCENT, 0.95));
    const cm = flatMat(B, ACCENT, 1);
    for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) {
      const c = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.09, 0.09), cm);
      c.position.set(x * 1.95, y * 1.45, z * 1.25); cage.add(c);
    }
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(3.9, 2.5), flatMat(B, ACCENT, 0.035));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -1.45;
    cage.add(floor);
    this.cage = cage;
    g.add(cage);
    this.cageGroup = g;
    this.scene.add(g);
  }

  /* --- 06 four numbered gate doors --- */
  buildGates(i) {
    const B = this.buckets[i];
    const g = new THREE.Group();
    g.position.x = SP * i;
    this.doorZ = [0.6, -1.0, -2.6, -4.2];
    const names = ['targeted', 'hidden', 'negative', 'regression'];
    this.doorNames = names;
    this.doors = this.doorZ.map((z, k) => {
      const d = new THREE.Group(); d.position.z = z;
      const frameMat = flatMat(B, INK, 0.42);
      const W = 2.5, H = 2.7, T = 0.05;
      const add = (w, h, x, y) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.1), frameMat); m.position.set(x, y, 0); d.add(m); };
      add(W, T, 0, H / 2 - T / 2 - 0.1); add(T, H - 0.1, -W / 2, -0.05); add(T, H - 0.1, W / 2, -0.05);
      const leafMat = B.add(new THREE.MeshPhysicalMaterial({ color: 0x26382e, metalness: 0.4, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.25 }), 1);
      leafMat.depthWrite = true;
      const leaves = [-1, 1].map((s) => {
        const lm = new THREE.Mesh(new THREE.BoxGeometry(W / 2 - T, H - 0.2, 0.08), leafMat);
        lm.userData.side = s; d.add(lm); const le = line(B, new THREE.EdgesGeometry(lm.geometry), ACCENT, 0.55); lm.add(le); return lm;
      });
      const num = (lit) => textPlane(B, 0.9, 0.4, (c, w, h, u) => {
        c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = lit ? ACCENT_CSS : '#8b968e';
        c.font = `600 ${0.27 * u}px ${MONO}`; c.fillText(`0${k + 1}`, w / 2, h / 2);
      }, 1);
      const n0 = num(false), n1 = num(true);
      for (const n of [n0, n1]) { n.position.set(0, H / 2 + 0.26, 0.06); d.add(n); }
      g.add(d);
      return { group: d, leaves, w: W, h: H, num: n0.material, numLit: n1.material };
    });
    // floor rails guide the eye down the corridor
    const rails = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-1.25, -1.72, 3), new THREE.Vector3(-1.25, -1.72, -6),
      new THREE.Vector3(1.25, -1.72, 3), new THREE.Vector3(1.25, -1.72, -6),
    ]);
    g.add(line(B, rails, ACCENT, 0.3));
    this.gateGroup = g;
    this.scene.add(g);
  }

  /* --- 07 card lands into a file tree --- */
  buildTree(i) {
    const B = this.buckets[i];
    const g = new THREE.Group();
    g.position.x = SP * i;
    const PW = 2.7, PH = 3.3;
    const mat = B.add(new THREE.MeshPhysicalMaterial({ color: 0x0f1612, metalness: 0.4, roughness: 0.35, clearcoat: 1, clearcoatRoughness: 0.25 }), 1);
    mat.depthWrite = true;
    g.add(new THREE.Mesh(slabGeometry(PW, PH, 0.08, 0.12), mat));
    const edge = outline(PW, PH, 0.12, INK, 0.4); edge.position.z = 0.06; B.track(edge.material); g.add(edge);
    const base = textPlane(B, PW, PH, (c, w, h, u) => {
      c.textBaseline = 'middle';
      c.fillStyle = GREY_CSS; c.font = `500 ${0.1 * u}px ${MONO}`; c.fillText('WORKING TREE', 0.26 * u, 0.3 * u);
      c.fillStyle = '#c9d1ca'; c.font = `500 ${0.19 * u}px ${MONO}`;
      c.fillText('src/', 0.26 * u, 0.78 * u);
      c.fillStyle = '#6f7b73'; c.fillText('tests/', 0.26 * u, 1.68 * u);
      c.strokeStyle = 'rgba(244,246,241,.14)'; c.lineWidth = 2;
      c.beginPath(); c.moveTo(0.26 * u, 0.5 * u); c.lineTo(w - 0.26 * u, 0.5 * u); c.stroke();
    }, 1);
    base.position.z = 0.06; g.add(base);
    const rowY = (n) => PH / 2 - (0.78 + n * 0.45);
    const rowTex = (txt, color, indent) => textPlane(B, PW, 0.4, (c, w, h, u) => {
      c.textBaseline = 'middle'; c.fillStyle = color; fitText(c, txt, w - (indent + 0.2) * u, 0.18 * u); c.fillText(txt, indent * u, h / 2);
    }, 1);
    const sol = rowTex('solution.py', ACCENT_CSS, 0.95);
    const solDim = rowTex('solution.py', '#8b968e', 0.95);
    sol.position.set(0, rowY(1), 0.065); solDim.position.set(0, rowY(1), 0.064);
    const log = rowTex('execution_log.json', '#d9dfd9', 0.52), rep = rowTex('execution_report.md', '#d9dfd9', 0.52);
    log.position.set(0, rowY(3), 0.065); rep.position.set(0, rowY(4), 0.065);
    // tests sits between; shift: src (0), solution (1), tests (2.9)... positions fixed above in base texture
    g.add(sol, solDim, log, rep);
    const bar = new THREE.Mesh(new THREE.PlaneGeometry(PW - 0.36, 0.38), flatMat(B, ACCENT, 0.16));
    bar.position.set(0, rowY(1), 0.062); g.add(bar);
    this.treeSlot = new THREE.Vector3(-0.98, rowY(1), 0.12);
    this.tree = { sol: sol.material, solDim: solDim.material, log: log.material, rep: rep.material, bar: bar.material, group: g };
    this.treeGroup = g;
    this.scene.add(g);
  }

  /* --- the rejected patch that falls away --- */
  buildReject() {
    const B = this.rejectBucket;
    const g = new THREE.Group();
    const mat = B.add(new THREE.MeshPhysicalMaterial({ color: 0x3a1e16, metalness: 0.3, roughness: 0.5, clearcoat: 0.4 }), 1);
    mat.depthWrite = true;
    g.add(new THREE.Mesh(slabGeometry(CARD_W, CARD_H, 0.06, 0.14), mat));
    const e = outline(CARD_W, CARD_H, 0.14, FAIL, 1); e.position.z = 0.046; B.track(e.material); g.add(e);
    const x = textPlane(B, CARD_W, CARD_H, (c, w, h, u) => {
      c.strokeStyle = '#ff7a59'; c.lineWidth = 0.09 * u; c.lineCap = 'square';
      const cx = w / 2, cy = h / 2, r = 0.38 * u;
      c.beginPath(); c.moveTo(cx - r, cy - r); c.lineTo(cx + r, cy + r); c.moveTo(cx + r, cy - r); c.lineTo(cx - r, cy + r); c.stroke();
    }, 1);
    x.position.z = 0.07; g.add(x);
    g.visible = false;
    this.reject = g;
    this.scene.add(g);
  }

  /* --- short HTML labels pinned to 3D points (crisp, on-theme) --- */
  buildTags() {
    const layer = document.createElement('div');
    layer.className = 'story-tags';
    layer.setAttribute('aria-hidden', 'true');
    this.tagLayer = layer;
    pin.insertBefore(layer, document.querySelector('.story-wash'));
    const mk = (cls = '') => { const el = document.createElement('span'); el.className = `tag ${cls}`.trim(); layer.appendChild(el); return el; };
    const T = (station, anchor, text, show, cls) => this.tags.push({ station, anchor: new THREE.Vector3(...anchor), el: mk(cls), text, show, last: '' });
    T(0, [0, 1.35, 0], 'contract', (q) => sstep(0.02, 0.2, q));
    T(1, [0, 1.35, 0], 'solution.py', (q) => sstep(0.55, 0.75, q));
    T(2, [0.85, 1.5, 0], 'tests/ · locked', (q) => sstep(0.3, 0.5, q));
    this.hashTag = { station: 2, anchor: new THREE.Vector3(0.85, -1.25, 0), el: mk('is-hash'), show: (q) => sstep(0.5, 0.62, q), custom: 'hash' };
    this.tags.push(this.hashTag);
    T(3, [-1.95, 1.55, 0], 'ast.parse', (q) => sstep(0.05, 0.2, q));
    T(3, [0, -1.65, 0], 'count_vowels ✓', (q) => sstep(0.82, 0.95, q), 'is-ok');
    T(4, [0, 1.8, 0], 'git worktree', (q) => sstep(0.25, 0.45, q));
    T(4, [0, -1.85, 0], 'src/ untouched', (q) => sstep(0.55, 0.75, q));
    this.gateTag = { station: 5, anchor: new THREE.Vector3(0, 2.0, -2), el: mk('is-ok'), show: () => 1, custom: 'gate' };
    this.tags.push(this.gateTag);
    this.rejectTag = { station: 5, anchor: new THREE.Vector3(0, 0, 0), el: mk('is-fail'), show: () => 1, custom: 'reject' };
    this.tags.push(this.rejectTag);
    T(6, [0, 2.1, 0], 'verified copy-back', (q) => sstep(0.8, 0.95, q), 'is-ok');
  }

  /* ----------------------------- sizing ----------------------------- */
  resize() {
    const w = Math.max(1, Math.round(this.canvas.clientWidth));
    const h = Math.max(1, Math.round(this.canvas.clientHeight));
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    this.dpr = Math.min(window.devicePixelRatio || 1, this.tier >= 2 ? 2 : this.tier === 1 ? 1.5 : 1);
    this.renderer.setPixelRatio(this.dpr);
    this.renderer.setSize(w, h, false);
    this.aspect = w / h;
    this.compact = w < 760 || this.aspect < 1.25;
    this.camera.aspect = this.aspect;
    // keep the card readable on narrow canvases
    const base = Math.tan(THREE.MathUtils.degToRad(15));
    this.baseTan = Math.max(base, (this.compact ? 5.9 : 7.0) / this.aspect / 2 / 8.6);
    this.camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(this.baseTan));
    const shift = this.compact ? 0 : -0.10 * w;
    if (shift) this.camera.setViewOffset(w, h, shift, 0, w, h); else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
    this.setupPost();
  }

  setupPost() {
    if (this.tier < 2) { this.post?.target.dispose(); this.post = null; return; }
    try {
      if (!this.post) {
        const target = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4, depthBuffer: true });
        const mat = new THREE.ShaderMaterial({
          uniforms: { tDiffuse: { value: target.texture }, uCA: { value: 0 }, uTime: { value: 0 } },
          vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }',
          fragmentShader: `uniform sampler2D tDiffuse; uniform float uCA; uniform float uTime; varying vec2 vUv;
            void main(){
              vec2 c = vUv - .5; float r = dot(c, c);
              vec2 off = c * uCA * (.4 + r * 3.);
              vec3 col = vec3(texture2D(tDiffuse, vUv + off).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - off).b);
              col *= 1. - r * .32;
              float n = fract(sin(dot(gl_FragCoord.xy + uTime, vec2(12.9898, 78.233))) * 43758.5453);
              col += (n - .5) * .008;
              gl_FragColor = vec4(col, 1.);
              #include <colorspace_fragment>
            }`,
          depthTest: false, depthWrite: false,
        });
        const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat);
        quad.frustumCulled = false;
        const postScene = new THREE.Scene(); postScene.add(quad);
        this.post = { target, mat, scene: postScene, cam: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
      }
      this.post.target.setSize(Math.round(this.w * this.dpr), Math.round(this.h * this.dpr));
    } catch (error) {
      console.warn('Post-processing unavailable, using direct render.', error);
      this.post = null; this.tier = 1;
    }
  }

  degrade() {
    if (this.tier === 0) return;
    this.tier -= 1;
    this.w = 0;
    if (this.dust && this.tier < 2) { this.scene.remove(this.dust); this.dust = null; }
    this.resize();
  }

  /* ----------------------------- timeline ----------------------------- */
  poseFor(i, q) {
    // [x, y, z, rx, ry, rz, scale, weight] relative to the station centre
    const e = (v) => sstep(0, 1, v);
    switch (i) {
      case 0: return [0, 0.05, 0, 0.02, -0.34 + 0.16 * q, 0, 1, 1];
      case 1: { const a = e(q / 0.45); return [0, 0.05 + 0.14 * Math.sin(a * Math.PI), 0, 0.02, -0.18 + a * Math.PI, 0, 1, 1]; }
      case 2: { const a = e(q / 0.35); return [-1.15 * a, 0, -1.5 * a, 0.02, Math.PI - 0.18 - 0.1 * a, 0, 1 - 0.28 * a, 1 - 0.65 * a]; }
      case 3: return [0, 0, lerp(1.6, -1.7, e((q - 0.12) / 0.76)), 0.02, Math.PI - 0.2, 0, 1, 1];
      case 4: return [0, -0.05, -0.2, 0.02, Math.PI - 0.2 + 0.32 * q, 0, 0.85, 1];
      case 5: return [0, -0.1, lerp(2.0, -5.0, e((q - 0.42) / 0.58)), 0.02, Math.PI + 0.12, 0, 0.6, 1];
      default: {
        const a = e(q / 0.55);
        return [lerp(0, this.treeSlot.x, a), lerp(0.1, this.treeSlot.y, a), lerp(1.0, 0.14, a), 0.02, Math.PI + lerp(0.1, 0, a), 0, lerp(0.85, 0.17, a), 1];
      }
    }
  }

  camFor(i) {
    // yaw (radians, always under 22 degrees), height, distance, target z
    return [
      [0.16, 0.55, 8.6, 0], [-0.15, 0.5, 8.6, 0], [0.2, 0.7, 8.8, 0],
      [-0.24, 0.6, 9.2, 0], [0.22, 1.2, 9.6, 0], [-0.3, 0.8, 11.2, -1.0], [0.12, 0.3, 9.2, 0],
    ][i];
  }

  update(p, dt) {
    const s = Math.min(STEPS - 0.0001, Math.max(0, p * STEPS));
    const i = Math.floor(s);
    const frac = s - i;
    const q = clamp01(frac / 0.6);
    const hasNext = i < STEPS - 1;
    const f = hasNext ? sstep(0.62, 1, frac) : 0;
    const fc = hasNext ? sstep(0.6, 0.92, frac) : 0;
    const qOf = (j) => clamp01((s - j) / 0.6);
    this.qNow = qOf;
    const act = (j) => (j === i ? 1 - f : j === i + 1 ? f : 0);
    this.act = act;

    // card: blend this station's pose with the next station's opening pose
    const A = this.poseFor(i, q), Bp = hasNext ? this.poseFor(i + 1, 0) : A;
    const ax = SP * i, bx = SP * (i + 1);
    const pose = A.map((v, k) => lerp(v + (k === 0 ? ax : 0), Bp[k] + (k === 0 ? bx : 0), fc));
    this.card.position.set(pose[0], pose[1], pose[2]);
    this.card.rotation.set(pose[3], pose[4], pose[5]);
    this.card.scale.setScalar(pose[6]);
    this.cardW = pose[7];
    this.cardZ = pose[2];
    this.cardX = pose[0];

    // 01 contract rows light up one by one
    this.rows.forEach((r, k) => {
      const lit = i === 0 ? sstep(0.18 + k * 0.2, 0.3 + k * 0.2, q) : 1;
      r.lit.userData.k = lit; r.dim.userData.k = 1 - lit;
    });
    // contract face visible only until the flip, then the code face
    // 02 code lines type in
    const q1 = qOf(1);
    this.codeLines.forEach((m, k) => { m.userData.k = sstep(0.42 + k * 0.08, 0.5 + k * 0.08, q1); });

    // 03 tests box: lid closes, ring appears
    const q2 = qOf(2);
    this.testLid.position.y = lerp(1.35, 0.7, sstep(0.05, 0.42, q2));
    this.testRing.material.userData.k = sstep(0.42, 0.6, q2);
    this.testGroup.rotation.y = -0.25 + 0.1 * q2;

    // 04 AST: membrane pulses as the card crosses it, scan sweeps down
    const q3 = qOf(3);
    const crossing = clamp01(1 - Math.abs(this.cardZ - 0) / 1.2) * (i === 3 ? 1 : 0);
    this.astMembrane.material.userData.k = 0.7 + 1.6 * crossing;
    this.astScan.position.y = lerp(1.4, -1.4, sstep(0.18, 0.8, q3));
    this.astScan.material.userData.k = (sstep(0.15, 0.22, q3) * (1 - sstep(0.8, 0.9, q3)));

    // 05 cage grows around the card
    const q4 = qOf(4);
    const grow = sstep(0, 0.4, q4);
    this.cage.scale.set(1, lerp(0.02, 1, grow), 1);
    this.cage.position.y = lerp(-1.4, 0, grow);
    this.cageGroup.rotation.y = 0;

    // 06 gates: reject, fall, retry, doors open in order
    const q5 = qOf(5);
    const cardGoodWait = true;
    const goodZ = this.poseFor(5, q5)[2];
    const doors = this.doors;
    doors.forEach((d, k) => {
      let open;
      if (k === 0) open = Math.max(sstep(0.0, 0.12, q5), sstep(d.group.position.z + 1.9, d.group.position.z + 0.8, goodZ));
      else open = sstep(d.group.position.z + 1.9, d.group.position.z + 0.8, goodZ);
      d.open = open;
      d.leaves.forEach((lf) => {
        const half = d.w / 2 - 0.07;
        const sc = 1 - 0.9 * open;
        lf.scale.x = sc;
        lf.position.x = lf.userData.side * (half / 2 + 0.035) * 1 + (-lf.userData.side) * 0 ;
        lf.position.x = lf.userData.side * (d.w / 2 - 0.07 - (half * sc) / 2);
        lf.position.y = -0.05;
      });
      d.numLit.userData.k = open; d.num.userData.k = 1 - open;
    });
    // reject card: runs at door 2, shakes, falls
    const rz = lerp(2.0, -0.3, sstep(0.02, 0.2, q5));
    const fall = sstep(0.3, 0.46, q5);
    const rVisible = i === 5 && q5 > 0.005 && fall < 0.999 || (i === 4 && f > 0.6 && false);
    this.reject.visible = rVisible;
    const shake = sstep(0.2, 0.24, q5) * (1 - sstep(0.26, 0.3, q5)) * Math.sin(q5 * 220) * 0.07;
    this.reject.position.set(SP * 5 + shake, -0.15 - 3.0 * fall * fall, rz + 0.0 * fall);
    this.reject.rotation.set(0.1 + 0.9 * fall, -0.25, -0.9 * fall);
    this.reject.scale.setScalar(0.62);
    this.rejectBucket.mats.forEach((m) => { m.userData.k = sstep(0, 0.05, q5) * (1 - sstep(0.38, 0.48, q5)); });

    // 07 tree: card lands, row lights, receipts appear
    const q6 = qOf(6);
    const T = this.tree;
    const landed = sstep(0.5, 0.62, q6);
    T.sol.userData.k = landed; T.solDim.userData.k = 1 - landed; T.bar.userData.k = landed;
    T.log.userData.k = sstep(0.66, 0.78, q6); T.rep.userData.k = sstep(0.76, 0.88, q6);
    this.treeGroup.rotation.y = 0.12 - 0.18 * q6;

    // fade by activity
    for (let j = 0; j < STEPS; j += 1) {
      const a = act(j);
      this.buckets[j].apply(lerp(DIM, 1, a));
    }
    let cm = 1;
    if (i === 4) cm = 1 - sstep(0.5, 1, fc); else if (i === 5) cm = sstep(0.36, 0.46, q5);
    this.cardBucket.apply(cm * this.cardW);
    this.rejectBucket.apply(1);

    // camera: dolly with the stations, a short yaw drift, nothing wilder
    const c0 = this.camFor(i), c1 = hasNext ? this.camFor(i + 1) : c0;
    const yaw = lerp(c0[0], c1[0], f), h = lerp(c0[1], c1[1], f), d = lerp(c0[2], c1[2], f), tz = lerp(c0[3], c1[3], f);
    const tx = SP * (i + f);
    const drift = Math.sin(p * 40) * 0.0;
    this.camera.position.set(tx + Math.sin(yaw + drift) * d, h, tz + Math.cos(yaw) * d);
    this.camera.lookAt(tx, 0.05, tz);
    this.camera.updateMatrixWorld();

    this.updateTags(i, f, q5, q2, goodZ, rz, fall);
    this.grid.position.x = 0;
  }

  updateTags(i, f, q5, q2, goodZ, rz, fall) {
    const v = new THREE.Vector3();
    const w = this.w, h = this.h;
    for (const t of this.tags) {
      const a = this.act(t.station);
      let q = this.qNow(t.station);
      let o = a * t.show(q);
      let text = t.text;
      let ax = SP * t.station + t.anchor.x, ay = t.anchor.y, az = t.anchor.z;
      if (t.custom === 'hash') {
        text = q < 0.7 ? 'sha-256 · before' : q < 0.84 ? 'sha-256 · before = after' : 'sha-256 · before = after ✓';
        t.el.classList.toggle('is-ok', q >= 0.84);
      } else if (t.custom === 'gate') {
        // the gate the card is currently at
        let k = -1;
        this.doorZ.forEach((z, n) => { if (goodZ < z + 1.5 && goodZ > z - 1.0) k = n; });
        o = a * (k >= 0 && q5 > 0.42 ? 1 : 0);
        if (k >= 0) { text = `0${k + 1} ${this.doorNames[k]}`; az = this.doorZ[k]; ay = 1.95; ax = SP * 5; }
      } else if (t.custom === 'reject') {
        o = a * (sstep(0.18, 0.24, q5) * (1 - sstep(0.4, 0.48, q5)));
        text = 'rejected'; ax = SP * 5; ay = 0.95 - 3.0 * fall * fall; az = rz;
      }
      t.el.style.opacity = o.toFixed(3);
      if (o < 0.01) { t.el.style.visibility = 'hidden'; continue; }
      t.el.style.visibility = 'visible';
      if (text !== t.last) { t.el.textContent = text; t.last = text; t.tw = t.el.offsetWidth; }
      v.set(ax, ay, az).project(this.camera);
      const half = (t.tw || 80) / 2 + 8;
      const px = Math.min(w - half, Math.max(half, (v.x * 0.5 + 0.5) * w)), py = Math.min(h - 16, Math.max(16, (-v.y * 0.5 + 0.5) * h));
      t.el.style.transform = `translate(${px.toFixed(1)}px, ${py.toFixed(1)}px) translate(-50%, -50%)`;
    }
  }

  /* ----------------------------- loop ----------------------------- */
  frame(timeMs) {
    if (this.disposed) return;
    const t = timeMs * (timeMs < 1e6 ? 1 : 0.001);
    const dt = Math.min(0.1, Math.max(0.001, t - this.lastTime));
    this.lastTime = t;
    // light inertia; always converges to the scroll position, never plays on its own
    const prev = this.progress;
    const k = 1 - Math.exp(-dt * 12);
    this.progress += (targetProgress - this.progress) * k;
    if (Math.abs(targetProgress - this.progress) < 0.00005) this.progress = targetProgress;
    this.velocity = lerp(this.velocity, Math.abs(this.progress - prev) / dt, 0.2);
    this.update(this.progress, dt);

    if (this.post) {
      this.post.mat.uniforms.uCA.value = Math.min(0.004, this.velocity * 0.05);
      this.post.mat.uniforms.uTime.value = (t * 60) % 1000;
      this.renderer.setRenderTarget(this.post.target);
      this.renderer.render(this.scene, this.camera);
      this.renderer.setRenderTarget(null);
      this.renderer.render(this.post.scene, this.post.cam);
    } else {
      this.renderer.render(this.scene, this.camera);
    }

    // quality watchdog: step down if sustained frames are slow while scrolling
    if (this.velocity > 0.01) {
      this.frameMs.push(dt * 1000);
      if (this.frameMs.length >= 90) {
        const avg = this.frameMs.reduce((a, b) => a + b, 0) / this.frameMs.length;
        this.frameMs.length = 0;
        if (avg > 34) this.degrade();
      }
    }
  }

  snap() { this.progress = targetProgress; this.velocity = 0; }

  destroy() {
    this.disposed = true;
    this.ro.disconnect();
    this.tagLayer.remove();
    this.renderer.dispose();
  }
}

reduced.addEventListener?.('change', () => {
  teardown();
  setReducedState();
  setupScroll();
  setupLenis();
});
window.addEventListener('scroll', () => {
  if (!isReduced) return;
  const p = clamp01((window.scrollY - story.offsetTop) / Math.max(1, story.offsetHeight - window.innerHeight));
  setStep(stepFromProgress(p));
}, { passive: true });

setReducedState();
setupScroll();
setupLenis();
window.addEventListener('load', () => ScrollTrigger.refresh(), { once: true });
window.__cdavc = { get world() { return world; }, get lenis() { return lenis; } };

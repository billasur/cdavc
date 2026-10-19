import * as THREE from './vendor/three.module.min.js';

const { gsap, ScrollTrigger } = window;
const Lenis = window.Lenis;
document.body.classList.add('story-module-loaded');

gsap.registerPlugin(ScrollTrigger);

const body = document.body;
const story = document.querySelector('#task-story');
const pin = document.querySelector('.story-pin');
const canvas = document.querySelector('#task-canvas');
const panels = [...document.querySelectorAll('.story-panel')];
const railItems = [...document.querySelectorAll('.story-rail li')];
const stageReadout = document.querySelector('#story-stage');
const staticVisual = document.querySelector('.static-visual');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
let isReduced = reduced.matches;
let scene = null;
let storyTrigger = null;
let lenis = null;
const lenisTicker = (time) => lenis?.raf(time * 1000);
let lastStep = -1;

function setReducedState() {
  isReduced = reduced.matches;
  body.classList.toggle('is-reduced-motion', isReduced);
  if (isReduced) {
    const step = Math.min(6, Math.max(0, Math.round((window.scrollY - story.offsetTop) / Math.max(1, story.offsetHeight - window.innerHeight) * 6)));
    setStep(step);
  }
}

function setStep(step) {
  const safeStep = Math.min(6, Math.max(0, step));
  if (safeStep === lastStep && !isReduced) return;
  lastStep = safeStep;
  stageReadout.textContent = `${String(safeStep + 1).padStart(2, '0')} / 07`;
  staticVisual.dataset.step = String(safeStep);
  panels.forEach((panel, index) => {
    const active = index === safeStep;
    panel.classList.toggle('is-current', active);
    panel.setAttribute('aria-hidden', String(!active));
  });
  railItems.forEach((item, index) => item.classList.toggle('is-current', index === safeStep));
}

function initStoryScene() {
  if (scene || isReduced) return;
  try {
    scene = new TaskScene(canvas);
  } catch (error) {
    body.classList.add('no-webgl');
    console.warn('CD-AVC 3D scene unavailable; showing the static fallback.', error);
    return;
  }
  scene.resize();
  scene.setProgress(storyTrigger?.scrollTrigger?.progress ?? 0);
  scene.render(0, scene.progress);
  body.classList.add('webgl-ready');
  scene.start();
}

function setupScroll() {
  if (isReduced) return;
  const sceneLoader = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      initStoryScene();
      sceneLoader.disconnect();
    }
  }, { rootMargin: '160px 0px' });
  sceneLoader.observe(story);
  // Start immediately when the story is already on screen; the observer is only
  // a fallback for browsers that throttle observers in a hidden tab.
  if (story.getBoundingClientRect().top < window.innerHeight) {
    initStoryScene();
    sceneLoader.disconnect();
  }
  const timeline = { progress: 0 };
  const update = (progress) => {
    timeline.progress = progress;
    const step = Math.min(6, Math.floor(progress * 7));
    setStep(step);
    scene?.setProgress(progress);
  };
  update(0);
  storyTrigger = gsap.to(timeline, {
    progress: 1,
    ease: 'none',
    scrollTrigger: {
      trigger: story,
      start: 'top top',
      end: 'bottom bottom',
      pin: pin,
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
  lenis = new Lenis({
    duration: 1.05,
    smoothWheel: true,
    syncTouch: false,
    autoRaf: false,
  });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add(lenisTicker);
  gsap.ticker.lagSmoothing(1000, 16);
}

/* ------------------------------------------------------------------ *
 * Canvas textures
 * ------------------------------------------------------------------ */

const ACCENT = '#d8ff64';
const INK = '#f4f6f1';
const MUTED = 'rgba(202, 214, 204, .84)';
const FAIL = '#ff7a59';

function createTexture(width, height, draw) {
  const source = document.createElement('canvas');
  source.width = width;
  source.height = height;
  const context = source.getContext('2d');
  context.clearRect(0, 0, width, height);
  draw(context, width, height);
  const texture = new THREE.CanvasTexture(source);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function roundRect(context, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + r, y);
  context.arcTo(x + width, y, x + width, y + height, r);
  context.arcTo(x + width, y + height, x, y + height, r);
  context.arcTo(x, y + height, x, y, r);
  context.arcTo(x, y, x + width, y, r);
  context.closePath();
}

function plateTexture({ kicker, title, sub, width = 768, height = 232 }) {
  return createTexture(width, height, (ctx) => {
    ctx.fillStyle = 'rgba(8, 12, 10, .92)';
    roundRect(ctx, 2, 2, width - 4, height - 4, 8);
    ctx.fill();
    ctx.strokeStyle = 'rgba(216, 255, 100, .24)';
    ctx.lineWidth = 2;
    roundRect(ctx, 2, 2, width - 4, height - 4, 8);
    ctx.stroke();
    ctx.fillStyle = ACCENT;
    ctx.fillRect(24, 28, 5, height - 56);
    ctx.fillStyle = 'rgba(216, 255, 100, .92)';
    ctx.font = '700 23px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText(kicker.toUpperCase(), 50, 58);
    ctx.fillStyle = INK;
    ctx.font = '600 48px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText(title, 50, 124);
    ctx.fillStyle = MUTED;
    ctx.font = '400 24px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText(sub, 50, 172);
  });
}

function monoPlateTexture({ kicker, value, sub, width = 640, height = 216 }) {
  return createTexture(width, height, (ctx) => {
    ctx.fillStyle = 'rgba(8, 12, 10, .93)';
    roundRect(ctx, 2, 2, width - 4, height - 4, 8);
    ctx.fill();
    ctx.strokeStyle = 'rgba(216, 255, 100, .24)';
    ctx.lineWidth = 2;
    roundRect(ctx, 2, 2, width - 4, height - 4, 8);
    ctx.stroke();
    ctx.fillStyle = ACCENT;
    ctx.fillRect(22, 26, 5, height - 52);
    ctx.fillStyle = 'rgba(216, 255, 100, .92)';
    ctx.font = '700 22px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText(kicker.toUpperCase(), 46, 56);
    ctx.fillStyle = INK;
    ctx.font = '400 34px Menlo, monospace';
    ctx.fillText(value, 46, 116);
    ctx.fillStyle = MUTED;
    ctx.font = '400 22px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText(sub, 46, 164);
  });
}

function contractTexture() {
  return createTexture(1024, 390, (ctx, width, height) => {
    ctx.fillStyle = 'rgba(10, 15, 12, .97)';
    roundRect(ctx, 2, 2, width - 4, height - 4, 12);
    ctx.fill();
    ctx.strokeStyle = 'rgba(216, 255, 100, .36)';
    ctx.lineWidth = 2;
    roundRect(ctx, 2, 2, width - 4, height - 4, 12);
    ctx.stroke();
    ctx.fillStyle = ACCENT;
    ctx.fillRect(30, 26, 6, height - 52);
    ctx.font = '700 25px "Helvetica Neue", Arial, sans-serif';
    ctx.fillStyle = 'rgba(216, 255, 100, .95)';
    ctx.fillText('CONTRACT', 58, 62);
    ctx.textAlign = 'right';
    ctx.fillStyle = MUTED;
    ctx.font = '400 23px Menlo, monospace';
    ctx.fillText('benchmark task', width - 44, 62);
    ctx.textAlign = 'left';
    ctx.fillStyle = INK;
    ctx.font = '600 62px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText('task_001', 58, 136);
    ctx.fillStyle = 'rgba(188, 201, 191, .78)';
    ctx.font = '400 28px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText('Count vowels', 58, 178);
    ctx.strokeStyle = 'rgba(216, 255, 100, .18)';
    ctx.beginPath();
    ctx.moveTo(58, 204);
    ctx.lineTo(width - 44, 204);
    ctx.stroke();
    const rows = [
      ['file', 'solution.py'],
      ['symbol', 'count_vowels'],
      ['retry budget', '2'],
    ];
    rows.forEach(([key, value], index) => {
      const y = 248 + index * 48;
      ctx.fillStyle = 'rgba(150, 164, 154, .88)';
      ctx.font = '400 24px Menlo, monospace';
      ctx.fillText(key, 58, y);
      ctx.fillStyle = INK;
      ctx.font = '400 27px Menlo, monospace';
      ctx.fillText(value, 290, y);
    });
  });
}

function patchTexture() {
  return createTexture(512, 680, (ctx, width, height) => {
    ctx.fillStyle = '#0d1411';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = ACCENT;
    ctx.fillRect(0, 0, width, 64);
    ctx.fillStyle = '#0b0e0d';
    ctx.font = '700 30px Menlo, monospace';
    ctx.fillText('solution.py', 22, 43);
    ctx.textAlign = 'right';
    ctx.font = '700 14px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText('PATCH', width - 22, 40);
    ctx.textAlign = 'left';

    ctx.fillStyle = 'rgba(216, 255, 100, .055)';
    ctx.fillRect(0, 92, width, 38);

    const lines = [
      [['def ', ACCENT], ['count_vowels', INK], ['(text):', '#a9bfae']],
      [['    total ', INK], ['= ', '#a9bfae'], ['0', '#e6c07b']],
      [['    for ', ACCENT], ['ch ', INK], ['in ', ACCENT], ['text:', INK]],
      [['        if ', ACCENT], ['ch ', INK], ['in ', ACCENT], ['"aeiou"', '#b7d38f'], [':', INK]],
      [['            total ', INK], ['+= ', '#a9bfae'], ['1', '#e6c07b']],
      [['    return ', ACCENT], ['total', INK]],
    ];

    let y = 126;
    lines.forEach((parts, index) => {
      ctx.textAlign = 'right';
      ctx.fillStyle = 'rgba(126, 143, 132, .7)';
      ctx.font = '400 19px Menlo, monospace';
      ctx.fillText(String(index + 1), 46, y);
      ctx.textAlign = 'left';
      let x = 72;
      parts.forEach(([text, color]) => {
        ctx.fillStyle = color;
        ctx.font = '400 27px Menlo, monospace';
        ctx.fillText(text, x, y);
        x += ctx.measureText(text).width;
      });
      y += 62;
    });

    ctx.strokeStyle = 'rgba(216, 255, 100, .14)';
    ctx.beginPath();
    ctx.moveTo(0, height - 96);
    ctx.lineTo(width, height - 96);
    ctx.stroke();
    ctx.fillStyle = 'rgba(216, 255, 100, .07)';
    ctx.fillRect(0, height - 95, width, 95);
    ctx.fillStyle = '#b7d38f';
    ctx.font = '400 22px Menlo, monospace';
    ctx.fillText('parse ok', 22, height - 54);
    ctx.fillStyle = 'rgba(202, 214, 204, .84)';
    ctx.font = '400 20px Menlo, monospace';
    ctx.fillText('symbol count_vowels', 22, height - 27);
  });
}

function repoTexture() {
  return createTexture(1024, 700, (ctx, width) => {
    ctx.fillStyle = '#0d1311';
    ctx.fillRect(0, 0, width, 700);
    ctx.fillStyle = ACCENT;
    ctx.font = '700 24px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText('WORKING TREE', 36, 52);
    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(184, 200, 188, .86)';
    ctx.font = '400 20px Menlo, monospace';
    ctx.fillText('main · clean', width - 36, 52);
    ctx.textAlign = 'left';
    ctx.strokeStyle = 'rgba(216, 255, 100, .16)';
    ctx.beginPath();
    ctx.moveTo(36, 80);
    ctx.lineTo(width - 36, 80);
    ctx.stroke();

    const headers = ['benchmarks/', 'tests/', 'src/', 'docs/', 'pyproject.toml', 'README.md', 'execution_log.json', 'execution_report.md'];
    headers.forEach((name, index) => {
      const column = index < 4 ? 0 : 1;
      const row = index % 4;
      const x = 40 + column * 500;
      const y = 140 + row * 132;
      if (index < 4) {
        ctx.fillStyle = 'rgba(216, 255, 100, .7)';
        ctx.fillRect(x, y - 18, 16, 16);
      } else {
        ctx.strokeStyle = index > 5 ? 'rgba(216, 255, 100, .32)' : 'rgba(174, 190, 178, .5)';
        ctx.strokeRect(x + .5, y - 17.5, 15, 15);
      }
      ctx.fillStyle = index > 5 ? 'rgba(190, 206, 194, .74)' : '#dfe7e0';
      ctx.font = '400 24px Menlo, monospace';
      ctx.fillText(name, x + 30, y);
      ctx.strokeStyle = 'rgba(174, 190, 178, .08)';
      ctx.beginPath();
      ctx.moveTo(x, y + 38);
      ctx.lineTo(x + 430, y + 38);
      ctx.stroke();
    });

    ctx.strokeStyle = 'rgba(216, 255, 100, .2)';
    ctx.strokeRect(20, 20, width - 40, 660);
  });
}

function rejectTexture() {
  return createTexture(512, 620, (ctx, width, height) => {
    ctx.fillStyle = '#17100e';
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = FAIL;
    ctx.fillRect(0, 0, width, 58);
    ctx.fillStyle = '#1a0d09';
    ctx.font = '700 25px Menlo, monospace';
    ctx.fillText('attempt 1', 20, 40);
    ctx.textAlign = 'right';
    ctx.font = '700 13px "Helvetica Neue", Arial, sans-serif';
    ctx.fillText('FAILED', width - 20, 37);
    ctx.textAlign = 'left';
    const lines = [
      'Locked test hash changed',
      'between capture and run.',
    ];
    ctx.fillStyle = 'rgba(255, 168, 140, .9)';
    ctx.font = '400 20px Menlo, monospace';
    lines.forEach((line, index) => {
      ctx.fillText(line, 28, 128 + index * 34);
    });
    ctx.strokeStyle = 'rgba(255, 122, 89, .35)';
    for (let i = 0; i < 7; i += 1) {
      ctx.beginPath();
      ctx.moveTo(28, 250 + i * 40);
      ctx.lineTo(width - 28, 250 + i * 40);
      ctx.stroke();
    }
    ctx.fillStyle = 'rgba(255, 122, 89, .85)';
    ctx.font = '400 15px Menlo, monospace';
    ctx.fillText('original file restored', 28, height - 28);
  });
}

function glowTexture() {
  return createTexture(256, 256, (ctx, width, height) => {
    const gradient = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width / 2);
    gradient.addColorStop(0, 'rgba(216, 255, 100, .75)');
    gradient.addColorStop(.35, 'rgba(216, 255, 100, .18)');
    gradient.addColorStop(1, 'rgba(216, 255, 100, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  });
}

function gridTexture() {
  return createTexture(2048, 2048, (ctx, width, height) => {
    ctx.strokeStyle = 'rgba(150, 176, 154, .17)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 64) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    ctx.strokeStyle = 'rgba(216, 255, 100, .2)';
    ctx.lineWidth = 2;
    for (let x = 0; x <= width; x += 256) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 256) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = 'destination-in';
    const fade = ctx.createRadialGradient(width / 2, height / 2, width * .06, width / 2, height / 2, width * .52);
    fade.addColorStop(0, 'rgba(0,0,0,1)');
    fade.addColorStop(.62, 'rgba(0,0,0,.72)');
    fade.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = fade;
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = 'source-over';
  });
}

let gateScreenMap = null;

function gateScreenTexture() {
  if (gateScreenMap) return gateScreenMap;
  gateScreenMap = createTexture(256, 304, (ctx, width, height) => {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, '#0f1813');
    gradient.addColorStop(.55, '#0a110e');
    gradient.addColorStop(1, '#070b09');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(160, 188, 166, .12)';
    ctx.lineWidth = 1;
    for (let x = 16; x < width; x += 32) {
      ctx.beginPath();
      ctx.moveTo(x + .5, 14);
      ctx.lineTo(x + .5, height - 14);
      ctx.stroke();
    }
    for (let y = 14; y < height; y += 32) {
      ctx.beginPath();
      ctx.moveTo(14, y + .5);
      ctx.lineTo(width - 14, y + .5);
      ctx.stroke();
    }

    const glow = ctx.createRadialGradient(width / 2, height * .48, 0, width / 2, height * .48, width * .62);
    glow.addColorStop(0, 'rgba(216, 255, 100, .05)');
    glow.addColorStop(1, 'rgba(216, 255, 100, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = 'rgba(216, 255, 100, .22)';
    ctx.lineWidth = 2;
    const corner = 22;
    [[16, 16, 1, 1], [width - 16, 16, -1, 1], [16, height - 16, 1, -1], [width - 16, height - 16, -1, -1]].forEach(([x, y, dx, dy]) => {
      ctx.beginPath();
      ctx.moveTo(x, y + dy * corner);
      ctx.lineTo(x, y);
      ctx.lineTo(x + dx * corner, y);
      ctx.stroke();
    });
  });
  return gateScreenMap;
}

function backdropTexture() {
  return createTexture(512, 512, (ctx, width, height) => {
    const gradient = ctx.createRadialGradient(width / 2, height * .46, 0, width / 2, height * .46, width * .52);
    gradient.addColorStop(0, 'rgba(25, 38, 30, .95)');
    gradient.addColorStop(.55, 'rgba(16, 24, 19, .55)');
    gradient.addColorStop(1, 'rgba(11, 14, 13, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
  });
}

/* ------------------------------------------------------------------ *
 * Scene
 * ------------------------------------------------------------------ */

const GATE_X = [-450, -120, 210, 540];
const GATE_THRESHOLDS = [2 / 7, 3 / 7, 5.35 / 7, 5.88 / 7];
const PATCH_X = [
  [0, -680],
  [1 / 7, -680],
  [2 / 7, -450],
  [3 / 7, -120],
  [4 / 7, -10],
  [5 / 7, -10],
  [5.32 / 7, 210],
  [5.62 / 7, 390],
  [5.88 / 7, 540],
  [6 / 7, 540],
  [1, 830],
];
const FLOOR_Y = -212;
const PATCH_Y = 50;
const PATCH_Z = 40;
const REPO_Z = 170;

// Vertical extent of the rig used for the fit in `resize()`.  The contract card
// (380 + 90) is the highest element and the floor plane the lowest; keep these
// in sync if either moves.
const RIG_HEIGHT = 682;
const RIG_CENTER_Y = 129;

// One camera set-up per story beat.  `w`/`h` are the world-space box that must
// stay inside the clear stage between the copy column and the rail; the camera
// distance is solved from those, not from the height of the whole rig.
const SHOTS = [
  { x: -640, y: 200, w: 900, h: 640, dx: 250, dy: 150 }, // contract + empty slot
  { x: -700, y: 90, w: 540, h: 500, dx: 210, dy: 130 }, // patch close-up
  { x: -450, y: 55, w: 600, h: 600, dx: 230, dy: 140 }, // gate 01
  { x: -120, y: 55, w: 600, h: 600, dx: 230, dy: 140 }, // gate 02
  { x: -10, y: 60, w: 960, h: 600, dx: 260, dy: 160 }, // isolated worktree
  { x: 375, y: 40, w: 800, h: 680, dx: 260, dy: 160 }, // gates 03 + 04 / reject
  { x: 850, y: 40, w: 760, h: 660, dx: 250, dy: 150 }, // copy-back
];

class TaskScene {
  constructor(target) {
    this.canvas = target;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x0b0e0d, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.16;
    this.canvas.replaceWith(this.renderer.domElement);
    this.canvas = this.renderer.domElement;
    this.canvas.id = 'task-canvas';
    this.canvas.setAttribute('aria-label', 'Three-dimensional CD-AVC verification cage');
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0x0b0e0d, 1700, 3200);
    this.camera = new THREE.PerspectiveCamera(32, 1, .1, 4000);
    this.clock = new THREE.Clock();
    this.time = 0;
    this.progress = 0;
    this.running = false;
    this.visible = true;
    this.phase = { step: 0, local: 0 };
    this.scale = 1;
    this.regionShift = 0;
    this.lookY = 40;
    this.patchX = -620;
    this.group = new THREE.Group();
    this.rig = new THREE.Group();
    this.rig.rotation.y = -0.055;
    this.group.add(this.rig);
    this.scene.add(this.group);
    this.accent = new THREE.Color(ACCENT);
    this.accentDim = new THREE.Color(0x2c3830);
    this.failColor = new THREE.Color(FAIL);
    this.screenBase = new THREE.Color(0x8b978f);
    this.screenPass = new THREE.Color(0xffffff);
    this.buildLights();
    this.buildRoom();
    this.buildRig();
    this.observer = new IntersectionObserver((entries) => {
      this.visible = entries.some((entry) => entry.isIntersecting);
      if (this.visible && !isReduced) this.start();
      else this.stop();
    }, { threshold: 0.01 });
    this.observer.observe(story);
  }

  buildLights() {
    this.scene.add(new THREE.HemisphereLight(0xc4d8c9, 0x0a0d0b, 1.0));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(-420, 620, 760);
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xd8ff64, 1.35);
    rim.position.set(620, 260, -520);
    this.scene.add(rim);
    const fill = new THREE.DirectionalLight(0x8fb6a0, .8);
    fill.position.set(500, -180, 620);
    this.scene.add(fill);
  }

  buildRoom() {
    const backdrop = new THREE.Mesh(
      new THREE.PlaneGeometry(5200, 3800),
      new THREE.MeshBasicMaterial({ map: backdropTexture(), transparent: true, depthWrite: false, toneMapped: false, fog: false, opacity: .75 }),
    );
    backdrop.position.set(160, 120, -900);
    this.rig.add(backdrop);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(5200, 3800),
      new THREE.MeshBasicMaterial({ map: gridTexture(), transparent: true, depthWrite: false, toneMapped: false, opacity: .8 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(120, FLOOR_Y, 220);
    this.rig.add(floor);

    const glow = glowTexture();
    this.pools = [];
    GATE_X.forEach((x) => {
      const pool = new THREE.Mesh(
        new THREE.PlaneGeometry(360, 240),
        new THREE.MeshBasicMaterial({ map: glow, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, opacity: .16 }),
      );
      pool.rotation.x = -Math.PI / 2;
      pool.position.set(x, FLOOR_Y + 1.5, 20);
      this.rig.add(pool);
      this.pools.push(pool);
    });
    const repoPool = new THREE.Mesh(
      new THREE.PlaneGeometry(620, 320),
      new THREE.MeshBasicMaterial({ map: glow, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, opacity: .1 }),
    );
    repoPool.rotation.x = -Math.PI / 2;
    repoPool.position.set(780, FLOOR_Y + 1.5, 20);
    this.rig.add(repoPool);

    const guide = new THREE.Mesh(
      new THREE.BoxGeometry(1660, 2, 2),
      new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .22, toneMapped: false }),
    );
    guide.position.set(100, FLOOR_Y + 2, 90);
    this.rig.add(guide);
    for (let i = 0; i < 24; i += 1) {
      const tick = new THREE.Mesh(
        new THREE.BoxGeometry(2, 1, i % 4 === 0 ? 18 : 9),
        new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .16, toneMapped: false }),
      );
      tick.position.set(-700 + i * 72, FLOOR_Y + 2, 90);
      this.rig.add(tick);
    }

    const dustGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(220 * 3);
    for (let i = 0; i < 220; i += 1) {
      positions[i * 3] = -900 + Math.random() * 2100;
      positions[i * 3 + 1] = FLOOR_Y + Math.random() * 620;
      positions[i * 3 + 2] = -320 + Math.random() * 620;
    }
    dustGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    this.dust = new THREE.Points(
      dustGeometry,
      new THREE.PointsMaterial({ color: 0xd8ff64, size: 1.6, transparent: true, opacity: .24, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }),
    );
    this.rig.add(this.dust);
  }

  buildRig() {
    const metal = new THREE.MeshStandardMaterial({ color: 0x1b241f, roughness: .42, metalness: .55 });
    const darkMetal = new THREE.MeshStandardMaterial({ color: 0x101713, roughness: .58, metalness: .35 });
    this.metal = metal;
    this.darkMetal = darkMetal;

    const cage = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(1720, 590, 320)),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .16, toneMapped: false }),
    );
    cage.position.set(100, 78, 0);
    this.rig.add(cage);

    const contract = new THREE.Mesh(
      new THREE.BoxGeometry(460, 180, 12),
      [
        darkMetal,
        darkMetal,
        darkMetal,
        darkMetal,
        new THREE.MeshBasicMaterial({ map: contractTexture(), transparent: true, toneMapped: false }),
        darkMetal,
      ],
    );
    contract.position.set(-620, 380, 110);
    const contractEdges = new THREE.LineSegments(
      new THREE.EdgesGeometry(contract.geometry),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .35, toneMapped: false }),
    );
    contractEdges.position.copy(contract.position);
    this.contractFace = contract.material[4];
    this.contractEdge = contractEdges.material;
    this.contractGroup = new THREE.Group();
    this.rig.add(this.contractGroup);
    this.contractGroup.add(contract);
    this.contractGroup.add(contractEdges);

    this.gates = GATE_X.map((x, index) => this.buildGate(index, x));

    this.buildWorktree();
    this.buildPatch();
    this.buildRejected();
    this.buildRepo();

    this.hashPlate = this.addStatusPlate(
      new THREE.Vector3(-420, -150, 210),
      monoPlateTexture({ kicker: 'LOCKED TESTS', value: '9c1f…b2e7', sub: 'sha-256 · before = after' }),
      220,
      74,
    );
    this.astPlate = this.addStatusPlate(
      new THREE.Vector3(-120, -150, 210),
      monoPlateTexture({ kicker: 'AST CONTRACT', value: 'count_vowels', sub: 'file parses · symbol found' }),
      220,
      74,
    );
    this.receiptPlate = this.addStatusPlate(
      new THREE.Vector3(1030, -70, 170),
      monoPlateTexture({ kicker: 'RECEIPTS', value: 'execution_log.json', sub: 'execution_report.md' }),
      300,
      100,
    );
    this.receiptPlate.material.opacity = 0;
  }

  addStatusPlate(position, texture, width, height) {
    const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, opacity: 0 });
    const plate = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
    plate.position.copy(position);
    this.rig.add(plate);
    return plate;
  }

  buildGate(index, x) {
    const group = new THREE.Group();
    group.position.set(x, 20, 0);
    const outerW = 276;
    const outerH = 320;
    const bar = 22;
    const depth = 28;
    const innerW = outerW - bar * 2;
    const innerH = outerH - bar * 2;

    const parts = [
      [outerW, bar, depth, 0, (outerH - bar) / 2],
      [outerW, bar, depth, 0, -(outerH - bar) / 2],
      [bar, innerH, depth, -(outerW - bar) / 2, 0],
      [bar, innerH, depth, (outerW - bar) / 2, 0],
    ];
    parts.forEach(([width, height, deep, px, py]) => {
      const part = new THREE.Mesh(new THREE.BoxGeometry(width, height, deep), this.metal);
      part.position.set(px, py, 0);
      group.add(part);
    });

    const screenMaterial = new THREE.MeshBasicMaterial({
      map: gateScreenTexture(),
      color: 0x8b978f,
      transparent: true,
      toneMapped: false,
      side: THREE.DoubleSide,
    });
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(innerW, innerH), screenMaterial);
    screen.position.set(0, 0, -6);
    group.add(screen);

    const stripMaterial = new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .16, toneMapped: false });
    const strips = [
      [innerW, 3, 3, 0, innerH / 2, depth / 2 + 1],
      [innerW, 3, 3, 0, -innerH / 2, depth / 2 + 1],
      [3, innerH, 3, -innerW / 2, 0, depth / 2 + 1],
      [3, innerH, 3, innerW / 2, 0, depth / 2 + 1],
    ];
    strips.forEach(([width, height, deep, px, py, pz]) => {
      const strip = new THREE.Mesh(new THREE.BoxGeometry(width, height, deep), stripMaterial);
      strip.position.set(px, py, pz);
      group.add(strip);
    });

    for (let i = 0; i < 7; i += 1) {
      const tick = new THREE.Mesh(
        new THREE.BoxGeometry(2, 7, 2),
        new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .3, toneMapped: false }),
      );
      tick.position.set(-innerW / 2 + (i + 1) * (innerW / 8), innerH / 2 + 12, depth / 2 + 1);
      group.add(tick);
    }

    const legHeight = 72;
    [-1, 1].forEach((side) => {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(10, legHeight, 12), this.darkMetal);
      leg.position.set(side * (outerW / 2 - 30), -(outerH / 2) - legHeight / 2, 0);
      group.add(leg);
    });
    const plinth = new THREE.Mesh(new THREE.BoxGeometry(outerW + 26, 12, 84), this.darkMetal);
    plinth.position.set(0, -(outerH / 2) - legHeight - 6, 0);
    group.add(plinth);

    const lampMaterial = new THREE.MeshBasicMaterial({ color: 0x2c3830, toneMapped: false });
    const lamp = new THREE.Mesh(new THREE.SphereGeometry(5.5, 14, 14), lampMaterial);
    lamp.position.set(outerW / 2 - 20, outerH / 2 + 16, 0);
    group.add(lamp);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture(),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      toneMapped: false,
      opacity: .04,
    }));
    halo.position.copy(lamp.position);
    halo.scale.set(52, 52, 1);
    group.add(halo);

    const scanMaterial = new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });
    const scan = new THREE.Mesh(new THREE.PlaneGeometry(innerW, 4), scanMaterial);
    scan.position.set(0, 0, depth / 2 + 4);
    group.add(scan);

    this.rig.add(group);

    const labelY = index % 2 === 0 ? 225 : 275;
    const labels = [
      ['TEST SEAL', 'sha-256 · before + after'],
      ['AST CONTRACT', 'parses · symbol exists'],
      ['TARGETED', 'hidden + negative suites'],
      ['REGRESSION', 'existing suite'],
    ];
    const labelTexture = plateTexture({
      kicker: `gate 0${index + 1}`,
      title: labels[index][0],
      sub: labels[index][1],
    });
    const labelMaterial = new THREE.MeshBasicMaterial({ map: labelTexture, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, opacity: .92 });
    const label = new THREE.Mesh(new THREE.PlaneGeometry(236, 71), labelMaterial);
    label.position.set(x, labelY, 24);
    this.rig.add(label);

    return {
      group,
      screenMaterial,
      strips: stripMaterial,
      lampMaterial,
      halo,
      scan,
      scanMaterial,
      label,
      labelMaterial,
      pool: this.pools[index],
      threshold: GATE_THRESHOLDS[index],
    };
  }

  buildPatch() {
    const face = new THREE.MeshBasicMaterial({ map: patchTexture(), transparent: true, toneMapped: false });
    const side = new THREE.MeshStandardMaterial({ color: 0x0f1512, roughness: .5, metalness: .3 });
    const geometry = new THREE.BoxGeometry(190, 230, 14);
    const mesh = new THREE.Mesh(geometry, [side, side, side, side, face, side]);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .55, toneMapped: false }),
    );
    this.patch = new THREE.Group();
    this.patch.add(mesh);
    this.patch.add(edges);

    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture(),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      toneMapped: false,
      opacity: .2,
    }));
    halo.scale.set(280, 330, 1);
    halo.position.z = -14;
    this.patch.add(halo);
    this.rig.add(this.patch);

    const slotPoints = [
      new THREE.Vector3(-95, -115, 0),
      new THREE.Vector3(95, -115, 0),
      new THREE.Vector3(95, 115, 0),
      new THREE.Vector3(-95, 115, 0),
      new THREE.Vector3(-95, -115, 0),
    ];
    const slotGeometry = new THREE.BufferGeometry().setFromPoints(slotPoints);
    this.patchSlot = new THREE.Line(slotGeometry, new THREE.LineDashedMaterial({ color: 0xd8ff64, dashSize: 8, gapSize: 7, transparent: true, opacity: .45, toneMapped: false }));
    this.patchSlot.computeLineDistances();
    this.patchSlot.position.set(-620, 20, 8);
    this.rig.add(this.patchSlot);
  }

  buildWorktree() {
    const shell = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(1220, 410, 260)),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0, toneMapped: false }),
    );
    shell.position.set(40, 5, 0);
    this.rig.add(shell);
    this.shell = shell;

    const texture = plateTexture({
      kicker: 'isolation',
      title: 'git worktree',
      sub: 'declared commands · source untouched',
    });
    const material = new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, opacity: 0 });
    const label = new THREE.Mesh(new THREE.PlaneGeometry(340, 102), material);
    label.position.set(40, 350, 40);
    this.rig.add(label);
    this.shellLabel = label;
  }

  buildRejected() {
    const face = new THREE.MeshBasicMaterial({ map: rejectTexture(), transparent: true, toneMapped: false });
    const side = new THREE.MeshStandardMaterial({ color: 0x1a1210, roughness: .7, metalness: .15 });
    const geometry = new THREE.BoxGeometry(170, 208, 12);
    const mesh = new THREE.Mesh(geometry, [side, side, side, side, face, side]);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0xff7a59, transparent: true, opacity: .55, toneMapped: false }),
    );
    this.rejected = new THREE.Group();
    this.rejected.add(mesh);
    this.rejected.add(edges);
    this.rejected.visible = false;
    this.rig.add(this.rejected);

    const tray = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(230, 18, 160)),
      new THREE.LineBasicMaterial({ color: 0xff7a59, transparent: true, opacity: .3, toneMapped: false }),
    );
    tray.position.set(80, FLOOR_Y + 14, 260);
    this.rig.add(tray);
    this.tray = tray;

    const curve = new THREE.EllipseCurve(80, 280, 128, 82, .2, 4.1);
    const points = curve.getPoints(44).map((point) => new THREE.Vector3(point.x, FLOOR_Y + 3, point.y));
    const retry = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineDashedMaterial({ color: 0xff7a59, dashSize: 10, gapSize: 9, transparent: true, opacity: 0, toneMapped: false }),
    );
    retry.computeLineDistances();
    this.rig.add(retry);
    this.retry = retry;

    const retryTexture = monoPlateTexture({ kicker: 'REPAIR', value: 'retry ≤ 2', sub: 'original file restored' });
    const retryMaterial = new THREE.MeshBasicMaterial({ map: retryTexture, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide, opacity: 0 });
    this.retryLabel = new THREE.Mesh(new THREE.PlaneGeometry(190, 64), retryMaterial);
    this.retryLabel.position.set(80, FLOOR_Y + 100, 380);
    this.rig.add(this.retryLabel);
  }

  buildRepo() {
    const face = new THREE.MeshBasicMaterial({ map: repoTexture(), transparent: true, toneMapped: false });
    const side = new THREE.MeshStandardMaterial({ color: 0x131b16, roughness: .5, metalness: .35 });
    const geometry = new THREE.BoxGeometry(440, 300, 260);
    const cabinet = new THREE.Mesh(geometry, [side, side, side, side, face, side]);
    cabinet.position.set(780, -60, 0);
    this.rig.add(cabinet);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .28, toneMapped: false }),
    );
    edges.position.copy(cabinet.position);
    this.rig.add(edges);
    this.repo = cabinet;

    const socketPoints = [
      new THREE.Vector3(-108, -122, 0),
      new THREE.Vector3(108, -122, 0),
      new THREE.Vector3(108, 122, 0),
      new THREE.Vector3(-108, 122, 0),
      new THREE.Vector3(-108, -122, 0),
    ];
    const socket = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(socketPoints),
      new THREE.LineDashedMaterial({ color: 0xd8ff64, dashSize: 9, gapSize: 7, transparent: true, opacity: .38, toneMapped: false }),
    );
    socket.computeLineDistances();
    socket.position.set(780, 20, 132);
    this.rig.add(socket);
    this.socket = socket;

    const repoLabelMaterial = new THREE.MeshBasicMaterial({
      map: plateTexture({ kicker: 'source of truth', title: 'working tree', sub: 'only verified files are copied back' }),
      transparent: true,
      depthWrite: false,
      toneMapped: false,
      side: THREE.DoubleSide,
      opacity: .9,
    });
    const repoLabel = new THREE.Mesh(new THREE.PlaneGeometry(340, 102), repoLabelMaterial);
    repoLabel.position.set(780, 170, 40);
    this.rig.add(repoLabel);
    this.repoLabel = repoLabel;

    const verifiedMaterial = new THREE.MeshBasicMaterial({
      map: plateTexture({ kicker: 'verified', title: 'all gates green', sub: 'files copied · receipts written' }),
      transparent: true,
      depthWrite: false,
      toneMapped: false,
      side: THREE.DoubleSide,
      opacity: 0,
    });
    const verified = new THREE.Mesh(new THREE.PlaneGeometry(340, 102), verifiedMaterial);
    verified.position.set(780, 290, 46);
    this.rig.add(verified);
    this.verified = verified;

    const connector = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(990, -60, 130),
        new THREE.Vector3(1030, -60, 170),
      ]),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: .25, toneMapped: false }),
    );
    this.rig.add(connector);
    this.connector = connector;
  }

  resize() {
    const width = this.canvas.clientWidth || window.innerWidth;
    const height = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / Math.max(1, height);
    const compact = window.matchMedia('(max-width: 1180px)').matches;
    this.compact = compact;
    const fov = compact ? 40 : 32;
    this.camera.fov = fov;
    this.camera.updateProjectionMatrix();
    const halfHeight = Math.tan((fov * Math.PI) / 360) * 1500;
    const pxPerUnit = height / 2 / halfHeight;
    const gutter = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--page-gutter')) || 32;
    let left = gutter;
    let right = width - gutter;
    let top = gutter;
    let bottom = height - gutter;
    if (compact) {
      const copy = document.querySelector('.story-copy')?.getBoundingClientRect();
      const meta = document.querySelector('.story-meta')?.getBoundingClientRect();
      if (meta) top = meta.bottom + 26;
      if (copy) bottom = copy.top - 18;
    } else {
      const copy = document.querySelector('.story-copy')?.getBoundingClientRect();
      const rail = document.querySelector('.story-rail')?.getBoundingClientRect();
      if (copy) left = copy.right + 16;
      if (rail) right = rail.left - 16;
    }
    const regionWidth = Math.max(160, right - left);
    const regionHeight = Math.max(160, bottom - top);
    const fitted = regionHeight * (compact ? .95 : .9) / (RIG_HEIGHT * pxPerUnit);
    this.scale = Math.max(.35, Math.min(2.6, fitted));
    this.group.scale.setScalar(this.scale);
    this.regionShift = ((left + right) / 2 - width / 2) / pxPerUnit;
    this.group.position.y = this.lookY + (height / 2 - (top + bottom) / 2) / pxPerUnit - RIG_CENTER_Y * this.scale;
    this.applyState();
  }

  setProgress(progress) {
    this.progress = Math.max(0, Math.min(1, progress));
    const scaled = this.progress * 7;
    const step = Math.min(6, Math.floor(scaled));
    this.phase.step = step;
    this.phase.local = Math.min(1, scaled - step);
    this.applyState();
  }

  applyState() {
    const p = this.progress;
    const time = this.time;

    this.patchX = trackKey(p, PATCH_X);
    const dock = smoothstep(.9, .996, p);
    const intro = smoothstep(.045, .075, p);
    const bob = Math.sin(time * 1.1) * 1.4 * (1 - dock);
    this.patch.visible = intro > .01;
    this.patch.scale.setScalar(.001 + intro * .999);
    this.patch.position.set(
      this.patchX,
      20 + bob,
      10 + 135 * dock,
    );
    this.patch.rotation.y = -.32 * dock;
    this.patch.rotation.z = Math.sin(p * Math.PI * 2) * .012 * (1 - dock);
    this.patchSlot.visible = intro < .35;
    this.patchSlot.material.opacity = .45 * (1 - intro);
    this.patchSlot.position.y = 20 + Math.sin(time * 1.1) * 2;

    this.gates.forEach((gate) => {
      const pass = smoothstep(gate.threshold, gate.threshold + .022, p);
      const local = clamp01((p - gate.threshold) / .032);
      const scanning = p >= gate.threshold && local < 1;
      gate.lampMaterial.color.copy(this.accentDim).lerp(this.accent, pass);
      gate.halo.material.opacity = .04 + pass * .5;
      gate.strips.opacity = .26 + pass * .6;
      gate.scanMaterial.opacity = scanning ? Math.sin(local * Math.PI) * .9 : 0;
      gate.scan.position.y = 138 - local * 276;
      gate.labelMaterial.opacity = .72 + pass * .26;
      gate.screenMaterial.color.copy(this.screenBase).lerp(this.screenPass, pass);
      gate.pool.material.opacity = .16 + pass * .16;
    });

    const rejectIn = smoothstep(.58, .62, p);
    const fall = smoothstep(.6, .78, p);
    this.rejected.visible = rejectIn > .02;
    this.rejected.scale.setScalar(.001 + rejectIn * .999);
    this.rejected.position.set(
      180 - 100 * fall,
      20 - 185 * fall,
      20 + 225 * fall,
    );
    this.rejected.rotation.x = -1.24 * fall;
    this.rejected.rotation.y = .42 * fall;
    this.rejected.rotation.z = -.5 * fall;
    this.tray.material.opacity = .12 + rejectIn * .3;
    const retryIn = smoothstep(.72, .78, p);
    this.retry.material.opacity = retryIn * .4;
    this.retryLabel.material.opacity = retryIn * .9;

    const shellIn = smoothstep(4 / 7, 4.4 / 7, p) * (1 - smoothstep(.94, 1, p) * .72);
    this.shell.material.opacity = shellIn * .24;
    this.shellLabel.material.opacity = shellIn;
    this.shellLabel.position.y = 350 + Math.sin(time * .8) * 2;

    const verifiedIn = smoothstep(.9, .98, p);
    this.verified.material.opacity = verifiedIn;
    this.verified.position.y = 290 + (1 - verifiedIn) * 16;
    this.repoLabel.material.opacity = .9 - verifiedIn * .55;
    this.socket.material.opacity = .38 + verifiedIn * .45;
    this.receiptPlate.material.opacity = smoothstep(.93, 1, p);
    this.receiptPlate.position.x = 1030 + (1 - smoothstep(.93, 1, p)) * 40;
    this.connector.material.opacity = .1 + verifiedIn * .3;

    this.hashPlate.material.opacity = smoothstep(.26, .29, p) * (1 - smoothstep(.42, .46, p));
    this.astPlate.material.opacity = smoothstep(.40, .44, p) * (1 - smoothstep(.55, .58, p));
    const contractFade = .95 - smoothstep(.12, .3, p) * .95;
    this.contractFace.opacity = contractFade;
    this.contractEdge.opacity = .35 * contractFade;

    const lookX = this.patchX * this.scale - this.regionShift;
    const lookY = this.lookY - smoothstep(.82, .98, p) * 44;
    const side = this.compact ? 40 : 220;
    const cameraZ = 1500 - smoothstep(.55, .82, p) * 150 + smoothstep(.78, 1, p) * 210;
    this.camera.position.set(lookX + side, lookY + 210, cameraZ);
    this.camera.lookAt(lookX, lookY, 0);

    this.dust.rotation.y = time * .006;
    this.dust.position.y = Math.sin(time * .12) * 6;
    this.rig.rotation.y = -0.055 + Math.sin(p * Math.PI) * .012;
  }

  start() {
    if (this.running || isReduced) return;
    this.running = true;
    this.clock.start();
    this.frameId = requestAnimationFrame(() => this.loop());
  }

  stop() {
    this.running = false;
    if (this.frameId) cancelAnimationFrame(this.frameId);
  }

  destroy() {
    this.stop();
    this.observer.disconnect();
    this.renderer.dispose();
  }

  loop() {
    if (!this.running) return;
    this.time = this.clock.getElapsedTime();
    this.applyState();
    this.renderer.render(this.scene, this.camera);
    this.frameId = requestAnimationFrame(() => this.loop());
  }

  render(time, progress) {
    if (!this.visible && !isReduced) return;
    this.time = time;
    this.setProgress(progress);
    this.renderer.render(this.scene, this.camera);
  }
}

function clamp01(value) {
  return Math.max(0, Math.min(1, value));
}

function smoothstep(edge0, edge1, value) {
  const x = clamp01((value - edge0) / Math.max(.0001, edge1 - edge0));
  return x * x * (3 - 2 * x);
}

function trackKey(progress, keys) {
  if (progress <= keys[0][0]) return keys[0][1];
  for (let index = 1; index < keys.length; index += 1) {
    if (progress <= keys[index][0]) {
      const [t0, v0] = keys[index - 1];
      const [t1, v1] = keys[index];
      return v0 + (v1 - v0) * smoothstep(0, 1, (progress - t0) / Math.max(1e-6, t1 - t0));
    }
  }
  return keys[keys.length - 1][1];
}

reduced.addEventListener?.('change', () => {
  setReducedState();
  if (storyTrigger) storyTrigger.kill();
  if (lenis) {
    gsap.ticker.remove(lenisTicker);
    lenis.destroy();
    lenis = null;
  }
  scene?.destroy();
  scene = null;
  ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
  setupScroll();
  setupLenis();
});

window.addEventListener('resize', () => {
  scene?.resize();
}, { passive: true });
window.addEventListener('scroll', () => {
  if (!isReduced) return;
  const progress = clamp01((window.scrollY - story.offsetTop) / Math.max(1, story.offsetHeight - window.innerHeight));
  setStep(Math.min(6, Math.floor(progress * 7)));
}, { passive: true });
document.addEventListener('visibilitychange', () => {
  if (document.hidden) scene?.stop();
  else if (!isReduced && scene?.visible) scene?.start();
});

setReducedState();
setupScroll();
setupLenis();
window.addEventListener('load', () => {
  ScrollTrigger.refresh();
}, { once: true });

import * as THREE from './vendor/three.module.min.js';

const { gsap, ScrollTrigger } = window;
const Lenis = window.Lenis;

document.body.classList.add('story-module-loaded');
gsap.registerPlugin(ScrollTrigger);

/* ------------------------------------------------------------------ *
 * DOM Selectors & State
 * ------------------------------------------------------------------ */
const body = document.body;
const story = document.querySelector('#task-story');
const pin = document.querySelector('.story-pin');
const canvas = document.querySelector('#task-canvas');
const panels = [...document.querySelectorAll('.story-panel')];
const railItems = [...document.querySelectorAll('.story-rail li')];
const railScrubber = document.querySelector('#rail-scrubber');
const stageReadout = document.querySelector('#story-stage');
const chamberReadout = document.querySelector('#hud-chamber');
const breachBanner = document.querySelector('#breach-banner');
const breachTitle = document.querySelector('#breach-title');
const breachDetail = document.querySelector('#breach-detail');
const btnDrift = document.querySelector('#btn-drift');
const btnSound = document.querySelector('#btn-sound');
const soundStateLabel = btnSound?.querySelector('.sound-state');
const staticVisual = document.querySelector('.static-visual');

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
let isReduced = reduced.matches;

let scene = null;
let storyTrigger = null;
let lenis = null;
const STAGE_CHAMBERS = [
  'STAGE 01 / THE TASK BOUNDARY',
  'STAGE 02 / BOUNDARY FILE SELECTION',
  'STAGE 03 / SEALED TEST COLLAR',
  'STAGE 04 / AST CONTRACT SCANNER',
  'STAGE 05 / ISOLATED WORKTREE CONDUIT',
  'STAGE 06 / QUARANTINE GATE ARENA',
  'STAGE 07 / MASTER REPO COPY-BACK',
];

const courierHeroTag = document.querySelector('#courier-hero-tag');
const courierHudStatus = document.querySelector('#courier-hud-status');
const HERO_STAGE_STATUSES = [
  'STAGE 01 · BORN IN TASK BOUNDARY',
  'STAGE 02 · BOUNDED FILE PERMITTED',
  'STAGE 03 · TEST SUITE SEALED (SHA-256)',
  'STAGE 04 · AST CONTRACT VALIDATED',
  'STAGE 05 · ISOLATED IN GIT WORKTREE',
  'STAGE 06 · QUALIFYING 4/4 GATES',
  'STAGE 07 · MERGED TO MAIN REPO',
];

const initParams = new URLSearchParams(window.location.search);
let initStep = -1;
if (initParams.has('step')) {
  const parsed = parseInt(initParams.get('step'), 10);
  if (!isNaN(parsed) && parsed >= 0 && parsed <= 6) {
    initStep = parsed;
    panels.forEach((p, idx) => {
      p.classList.toggle('is-current', idx === initStep);
      p.setAttribute('aria-hidden', String(idx !== initStep));
    });
    if (stageReadout) stageReadout.textContent = `${String(initStep + 1).padStart(2, '0')} / 07`;
    if (chamberReadout) chamberReadout.textContent = STAGE_CHAMBERS[initStep];
    railItems.forEach((item, index) => {
      item.classList.toggle('is-current', index === initStep);
    });
    if (railScrubber) {
      railScrubber.style.transform = `translateY(${initStep * 32}px)`;
    }
  }
}
let lastStep = -1;
let scrollVelocity = 0;

/* ------------------------------------------------------------------ *
 * Text Scrambler on Stage Entry
 * ------------------------------------------------------------------ */
function scrambleElement(el) {
  if (!el) return;
  const targetText = el.dataset.text || el.textContent;
  if (!targetText) return;
  el.dataset.text = targetText;
  const chars = '01#_./!%><[]{}*~';
  const len = targetText.length;
  let frame = 0;
  const totalFrames = 12;

  const timer = setInterval(() => {
    frame++;
    const progress = frame / totalFrames;
    const revealedIndex = Math.floor(progress * len);
    let str = '';
    for (let i = 0; i < len; i++) {
      if (targetText[i] === ' ') {
        str += ' ';
      } else if (i < revealedIndex) {
        str += targetText[i];
      } else {
        str += chars[Math.floor(Math.random() * chars.length)];
      }
    }
    el.textContent = str;
    if (frame >= totalFrames) {
      clearInterval(timer);
      el.textContent = targetText;
    }
  }, 24);
}

/* ------------------------------------------------------------------ *
 * Procedural Web Audio Engine (Zero External Audio Assets)
 * ------------------------------------------------------------------ */
class SoundEngine {
  constructor() {
    this.ctx = null;
    this.enabled = false;
    this.masterGain = null;
  }

  init() {
    if (this.ctx) return;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    this.ctx = new AudioCtx();
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.setValueAtTime(0.2, this.ctx.currentTime);
    this.masterGain.connect(this.ctx.destination);
  }

  toggle() {
    this.init();
    if (!this.ctx) return false;
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    this.enabled = !this.enabled;
    if (this.masterGain) {
      this.masterGain.gain.setValueAtTime(this.enabled ? 0.2 : 0, this.ctx.currentTime);
    }
    return this.enabled;
  }

  playGateChime() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, now);
    osc.frequency.exponentialRampToValueAtTime(1320, now + 0.12);
    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.33);
  }

  playAlarm() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(220, now);
    osc.frequency.linearRampToValueAtTime(160, now + 0.35);
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.5);
  }

  playDock() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(140, now);
    osc.frequency.exponentialRampToValueAtTime(50, now + 0.28);
    gain.gain.setValueAtTime(0.25, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.3);
  }
}

const audio = new SoundEngine();

btnSound?.addEventListener('click', () => {
  const active = audio.toggle();
  btnSound.classList.toggle('is-active', active);
  if (soundStateLabel) soundStateLabel.textContent = active ? 'ON' : 'OFF';
});

/* ------------------------------------------------------------------ *
 * UI & Step Sync
 * ------------------------------------------------------------------ */
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
  const prevStep = lastStep;
  lastStep = safeStep;

  if (stageReadout) stageReadout.textContent = `${String(safeStep + 1).padStart(2, '0')} / 07`;
  if (chamberReadout) chamberReadout.textContent = STAGE_CHAMBERS[safeStep];
  if (staticVisual) staticVisual.dataset.step = String(safeStep);

  panels.forEach((panel, index) => {
    const active = index === safeStep;
    panel.classList.toggle('is-current', active);
    panel.setAttribute('aria-hidden', String(!active));
    if (active) {
      const heading = panel.querySelector('h1, h2');
      scrambleElement(heading);
    }
  });

  railItems.forEach((item, index) => {
    item.classList.toggle('is-current', index === safeStep);
  });

  if (railScrubber) {
    railScrubber.style.transform = `translateY(${safeStep * 32}px)`;
  }

  if (prevStep !== -1 && safeStep > prevStep) {
    audio.playGateChime();
  }
}

// Rail click navigation
railItems.forEach((item, index) => {
  const btn = item.querySelector('button');
  btn?.addEventListener('click', () => {
    if (lenis && story) {
      const targetScroll = story.offsetTop + (index / 6) * (story.offsetHeight - window.innerHeight);
      lenis.scrollTo(targetScroll, { duration: 1.1 });
    } else {
      window.scrollTo({
        top: story.offsetTop + (index / 6) * (story.offsetHeight - window.innerHeight),
        behavior: 'smooth',
      });
    }
  });
});

/* ------------------------------------------------------------------ *
 * Interactive [ ⚡ Simulate Test Drift ] Action
 * ------------------------------------------------------------------ */
let isDrifting = false;

function triggerDriftSimulation() {
  if (isDrifting || !scene) return;
  isDrifting = true;
  audio.playAlarm();
  btnDrift?.classList.add('is-breached');
  breachBanner?.classList.add('is-active');

  scene.triggerDrift();

  setTimeout(() => {
    if (breachTitle) breachTitle.textContent = 'CD-AVC REJECTION PROTOCOL COMPLETE';
    if (breachDetail) breachDetail.textContent = 'Untrusted patch ejected. Original test and implementation restored. Zero residue in working tree.';
  }, 1600);

  setTimeout(() => {
    breachBanner?.classList.remove('is-active');
    btnDrift?.classList.remove('is-breached');
    isDrifting = false;
    scene.resetDrift();
    setTimeout(() => {
      if (breachTitle) breachTitle.textContent = 'TEST DRIFT DETECTED: LOCKED SUITE COMPROMISED';
      if (breachDetail) breachDetail.textContent = 'Locked SHA-256 mismatch detected. CD-AVC isolation active. Candidate write refused, worktree discarded.';
    }, 500);
  }, 3800);
}

btnDrift?.addEventListener('click', triggerDriftSimulation);

/* ------------------------------------------------------------------ *
 * Procedural Dynamic Canvas Textures (2x Retina with Mipmaps & Anisotropy 8)
 * ------------------------------------------------------------------ */
function createTexture(width, height, draw) {
  const scale = 2;
  const c = document.createElement('canvas');
  c.width = width * scale;
  c.height = height * scale;
  const ctx = c.getContext('2d');
  ctx.scale(scale, scale);
  ctx.clearRect(0, 0, width, height);
  draw(ctx, width, height);

  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.anisotropy = 8;
  texture.needsUpdate = true;
  return texture;
}

function courierFaceTexture(faceType = 'front') {
  return createTexture(512, 512, (ctx, w, h) => {
    // High-tech deep obsidian substrate
    ctx.fillStyle = '#040b07';
    ctx.fillRect(0, 0, w, h);

    // Subtle background micro-grid
    ctx.strokeStyle = 'rgba(216, 255, 100, 0.08)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 32) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 32) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Outer double-bezel border with corner chamfers
    ctx.strokeStyle = '#d8ff64';
    ctx.lineWidth = 4;
    ctx.strokeRect(8, 8, w - 16, h - 16);
    ctx.strokeStyle = 'rgba(94, 243, 210, 0.55)';
    ctx.lineWidth = 2;
    ctx.strokeRect(16, 16, w - 32, h - 32);

    // Corner crosshairs
    const corners = [[8, 8], [w - 8, 8], [8, h - 8], [w - 8, h - 8]];
    ctx.strokeStyle = '#d8ff64';
    ctx.lineWidth = 3;
    corners.forEach(([cx, cy]) => {
      ctx.beginPath();
      ctx.moveTo(cx - 12, cy); ctx.lineTo(cx + 12, cy);
      ctx.moveTo(cx, cy - 12); ctx.lineTo(cx, cy + 12);
      ctx.stroke();
    });

    if (faceType === 'front' || faceType === 'back') {
      // Top Status Bar
      ctx.fillStyle = 'rgba(216, 255, 100, 0.25)';
      ctx.fillRect(24, 24, w - 48, 48);
      ctx.strokeStyle = '#d8ff64';
      ctx.lineWidth = 2;
      ctx.strokeRect(24, 24, w - 48, 48);

      ctx.fillStyle = '#d8ff64';
      ctx.font = '700 23px monospace';
      ctx.fillText('[ HERO :: solution.py ]', 36, 56);

      ctx.fillStyle = '#ffffff';
      ctx.font = '700 16px monospace';
      ctx.textAlign = 'right';
      ctx.fillText('SHA:9c1f', w - 36, 56);
      ctx.textAlign = 'left';

      // Python Implementation Code Lines
      const code = [
        { t: 'def count_vowels(text: str) -> int:', kw: true },
        { t: '    """Count vowels in input."""', c: true },
        { t: '    vowels = "aeiouAEIOU"', kw: false },
        { t: '    count = 0', kw: false },
        { t: '    for ch in text:', kw: true },
        { t: '        if ch in vowels:', kw: true },
        { t: '            count += 1', kw: false },
        { t: '    return count', kw: true },
      ];

      code.forEach((item, i) => {
        const y = 120 + i * 36;
        if (item.c) {
          ctx.fillStyle = '#72a882';
          ctx.font = 'italic 19px monospace';
        } else if (item.kw) {
          ctx.fillStyle = '#d8ff64';
          ctx.font = '700 21px monospace';
        } else {
          ctx.fillStyle = '#ffffff';
          ctx.font = '600 21px monospace';
        }
        ctx.fillText(item.t, 36, y);
      });

      // Bottom Hardware Telemetry Bar
      ctx.strokeStyle = 'rgba(216, 255, 100, 0.4)';
      ctx.beginPath();
      ctx.moveTo(24, h - 64);
      ctx.lineTo(w - 24, h - 64);
      ctx.stroke();

      ctx.fillStyle = '#d8ff64';
      ctx.font = '700 16px monospace';
      ctx.fillText('SCOPE: BOUNDED · VERIFIED PAYLOAD', 36, h - 36);
    } else if (faceType === 'side') {
      // Memory Bus & Logic Circuits
      ctx.fillStyle = '#d8ff64';
      ctx.font = '700 23px monospace';
      ctx.fillText('[ LOGIC REGISTERS 0x00A4 ]', 36, 60);

      ctx.strokeStyle = 'rgba(216, 255, 100, 0.55)';
      ctx.lineWidth = 2.5;
      for (let i = 0; i < 6; i++) {
        const y = 112 + i * 50;
        ctx.beginPath();
        ctx.moveTo(36, y);
        ctx.lineTo(130, y);
        ctx.lineTo(160, y + 20);
        ctx.lineTo(w - 36, y + 20);
        ctx.stroke();

        ctx.fillStyle = i % 2 === 0 ? '#d8ff64' : '#5ef3d2';
        ctx.fillRect(w - 80, y + 10, 42, 18);
        ctx.fillStyle = '#06110a';
        ctx.font = '700 12px monospace';
        ctx.fillText('BUS', w - 72, y + 24);
      }

      ctx.fillStyle = '#8fffa8';
      ctx.font = '700 16px monospace';
      ctx.fillText('HASH: 9c1f…b2e7 · IMMUTABLE CORE', 36, h - 36);
    } else {
      // Top / Bottom Concentric Microprocessor Socket
      ctx.strokeStyle = '#d8ff64';
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, 140, 0, Math.PI * 2);
      ctx.stroke();
      ctx.strokeStyle = '#5ef3d2';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, 85, 0, Math.PI * 2);
      ctx.stroke();

      for (let i = 0; i < 8; i++) {
        const rad = (i / 8) * Math.PI * 2;
        ctx.strokeStyle = 'rgba(216, 255, 100, 0.7)';
        ctx.beginPath();
        ctx.moveTo(w / 2 + Math.cos(rad) * 85, h / 2 + Math.sin(rad) * 85);
        ctx.lineTo(w / 2 + Math.cos(rad) * 140, h / 2 + Math.sin(rad) * 140);
        ctx.stroke();
      }

      ctx.fillStyle = '#d8ff64';
      ctx.font = '700 22px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('QUANTUM PATCH CORE', w / 2, h / 2 - 12);
      ctx.fillStyle = '#ffffff';
      ctx.fillText('solution.py', w / 2, h / 2 + 20);
      ctx.textAlign = 'left';
    }
  });
}

function gatePlacardTexture(id, title, metric) {
  return createTexture(256, 96, (ctx, w, h) => {
    ctx.fillStyle = 'rgba(6, 14, 10, 0.95)';
    ctx.fillRect(2, 2, w - 4, h - 4);
    ctx.strokeStyle = 'rgba(216, 255, 100, 0.55)';
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 2, w - 4, h - 4);

    ctx.fillStyle = '#d8ff64';
    ctx.font = '700 15px monospace';
    ctx.fillText(`GATE ${id} //`, 16, 30);

    ctx.fillStyle = '#ffffff';
    ctx.font = '700 22px monospace';
    ctx.fillText(title, 16, 58);

    ctx.fillStyle = '#8fffa8';
    ctx.font = '600 14px monospace';
    ctx.fillText(metric, 16, 82);
  });
}

function courierFloorGlowTexture() {
  return createTexture(256, 256, (ctx, w, h) => {
    const grad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    grad.addColorStop(0, 'rgba(216, 255, 100, 0.55)');
    grad.addColorStop(0.35, 'rgba(216, 255, 100, 0.28)');
    grad.addColorStop(0.7, 'rgba(216, 255, 100, 0.08)');
    grad.addColorStop(1, 'rgba(216, 255, 100, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
  });
}

function gridFloorTexture() {
  return createTexture(2048, 2048, (ctx, w, h) => {
    ctx.strokeStyle = 'rgba(150, 180, 160, 0.16)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= w; x += 64) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y <= h; y += 64) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.28)';
    ctx.lineWidth = 2;
    for (let x = 0; x <= w; x += 256) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y <= h; y += 256) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    ctx.globalCompositeOperation = 'destination-in';
    const fade = ctx.createRadialGradient(w / 2, h / 2, w * 0.05, w / 2, h / 2, w * 0.52);
    fade.addColorStop(0, 'rgba(0,0,0,1)');
    fade.addColorStop(0.65, 'rgba(0,0,0,0.6)');
    fade.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = fade;
    ctx.fillRect(0, 0, w, h);
  });
}

function statusPlateTexture({ title, code, detail, color = '#d8ff64' }) {
  return createTexture(512, 180, (ctx, w, h) => {
    ctx.fillStyle = 'rgba(5, 11, 7, 0.96)';
    ctx.fillRect(4, 4, w - 8, h - 8);
    ctx.strokeStyle = color === '#ff4747' ? 'rgba(255, 71, 71, 0.75)' : 'rgba(216, 255, 100, 0.65)';
    ctx.lineWidth = 3;
    ctx.strokeRect(4, 4, w - 8, h - 8);

    ctx.strokeStyle = 'rgba(94, 243, 210, 0.35)';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(10, 10, w - 20, h - 20);

    ctx.fillStyle = color;
    ctx.fillRect(18, 18, 6, h - 36);

    ctx.font = '700 18px monospace';
    ctx.fillStyle = color;
    ctx.fillText(title.toUpperCase(), 36, 48);

    ctx.fillStyle = '#ffffff';
    ctx.font = '700 32px monospace';
    ctx.fillText(code, 36, 98);

    ctx.fillStyle = '#8fffa8';
    ctx.font = '600 18px monospace';
    ctx.fillText(detail, 36, 144);
  });
}

/* ------------------------------------------------------------------ *
 * Three.js 3D Protagonist Pipeline Engine
 * ------------------------------------------------------------------ */
class TaskScene {
  constructor(targetCanvas) {
    this.canvas = targetCanvas;
    this.width = targetCanvas.clientWidth || window.innerWidth;
    this.height = targetCanvas.clientHeight || window.innerHeight;

    // Detect capabilities & initialize Performance Tier
    const isCoarse = window.matchMedia('(pointer: coarse)').matches;
    const isPhone = window.innerWidth < 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    this.isMobile = isPhone || (isCoarse && window.innerWidth < 900);
    this.tier = this.isMobile ? 'LOW' : 'HIGH';
    this.slowFrameAccumulator = 0;

    const dpr = this.tier === 'HIGH' ? Math.min(window.devicePixelRatio || 1, 1.75) : 1;

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: this.tier !== 'LOW',
      alpha: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(this.width, this.height, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.45; // Enhanced exposure for maximum visibility

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x060908, 0.0006);

    this.camera = new THREE.PerspectiveCamera(34, this.width / Math.max(1, this.height), 1, 5000);
    this.timer = new THREE.Timer();
    this.time = 0;
    this.progress = 0;
    this.alertIntensity = 0;

    // Pointer Parallax & Raycasting
    this.pointer = new THREE.Vector2(0, 0);
    this.pointerTarget = new THREE.Vector2(0, 0);
    this.raycaster = new THREE.Raycaster();
    this.interactiveObjects = [];

    this.buildProceduralEnvironment();
    this.buildLighting();
    this.buildSplineCameraTrack();
    this.buildSceneWorld();
    this.setupPostProcessing();
    this.setupPointerEvents();
    this.resize();
  }

  buildProceduralEnvironment() {
    if (this.tier === 'LOW') return;
    try {
      const pmrem = new THREE.PMREMGenerator(this.renderer);
      pmrem.compileEquirectangularShader();

      const envScene = new THREE.Scene();
      const limeLight = new THREE.Mesh(
        new THREE.PlaneGeometry(800, 800),
        new THREE.MeshBasicMaterial({ color: 0xd8ff64 }),
      );
      limeLight.position.set(-200, 500, 300);
      limeLight.rotation.x = Math.PI / 2.5;
      envScene.add(limeLight);

      const cyanFill = new THREE.Mesh(
        new THREE.PlaneGeometry(700, 700),
        new THREE.MeshBasicMaterial({ color: 0x5ef3d2 }),
      );
      cyanFill.position.set(500, 200, -300);
      cyanFill.rotation.y = -Math.PI / 3;
      envScene.add(cyanFill);

      const darkGround = new THREE.Mesh(
        new THREE.PlaneGeometry(2000, 2000),
        new THREE.MeshBasicMaterial({ color: 0x030504 }),
      );
      darkGround.position.y = -400;
      darkGround.rotation.x = -Math.PI / 2;
      envScene.add(darkGround);

      const envTarget = pmrem.fromScene(envScene, 0.04);
      this.scene.environment = envTarget.texture;
      pmrem.dispose();
    } catch (e) {
      console.warn('Procedural PMREM environment bypassed:', e);
    }
  }

  buildLighting() {
    this.scene.add(new THREE.HemisphereLight(0xe0ece4, 0x060908, 1.4));

    const mainKey = new THREE.DirectionalLight(0xffffff, 3.8);
    mainKey.position.set(-280, 520, 580);
    this.scene.add(mainKey);

    const rimLight = new THREE.DirectionalLight(0xd8ff64, 2.8);
    rimLight.position.set(500, 320, -380);
    this.scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0x5ef3d2, 1.6);
    fillLight.position.set(-420, -80, 420);
    this.scene.add(fillLight);

    // Dedicated phosphor green point rim light following right behind the courier
    this.courierRimLight = new THREE.PointLight(0xd8ff64, 5.2, 400, 1.2);
    this.scene.add(this.courierRimLight);
  }

  buildSplineCameraTrack() {
    // 7 Spatial Camera Waypoints: Optimized focal distance so Courier is large, prominent, and framed in the right-center
    const cameraWaypoints = [
      new THREE.Vector3(-460, 105, 500),  // 01 Contract: Clean glass pod + large Courier
      new THREE.Vector3(-260, 105, 480),  // 02 Patch: Iris portal + deflected shards
      new THREE.Vector3(-80, 35, 470),    // 03 Tests: Sealed vault collar
      new THREE.Vector3(75, 25, 430),     // 04 AST: Scan gantry & syntax tree
      new THREE.Vector3(260, -35, 550),   // 05 Worktree: Dual space & conduit tube
      new THREE.Vector3(480, -10, 490),   // 06 Gates: 4 portal arena
      new THREE.Vector3(590, 25, 490),    // 07 Copy-back: Master dock & receipt plate
    ];

    const lookWaypoints = [
      new THREE.Vector3(-460, 100, 0),
      new THREE.Vector3(-260, 100, 0),
      new THREE.Vector3(-80, 25, 0),
      new THREE.Vector3(75, 25, 0),
      new THREE.Vector3(260, -45, 0),
      new THREE.Vector3(480, -20, 0),
      new THREE.Vector3(590, 25, 0),
    ];

    this.cameraSpline = new THREE.CatmullRomCurve3(cameraWaypoints, false, 'centripetal', 0.5);
    this.lookSpline = new THREE.CatmullRomCurve3(lookWaypoints, false, 'centripetal', 0.5);
  }

  buildSceneWorld() {
    this.world = new THREE.Group();
    this.scene.add(this.world);

    // Floor Grid
    const floorGeo = new THREE.PlaneGeometry(4800, 4800);
    const floorMat = new THREE.MeshBasicMaterial({
      map: gridFloorTexture(),
      transparent: true,
      depthWrite: false,
      opacity: 0.85,
    });
    this.floor = new THREE.Mesh(floorGeo, floorMat);
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.position.y = -220;
    this.world.add(this.floor);

    // Atmospheric Floating Dust Particles
    const dustCount = this.tier === 'LOW' ? 120 : 280;
    const dustGeo = new THREE.BufferGeometry();
    const dustPos = new Float32Array(dustCount * 3);
    for (let i = 0; i < dustCount; i++) {
      dustPos[i * 3] = -900 + Math.random() * 2100;
      dustPos[i * 3 + 1] = -220 + Math.random() * 700;
      dustPos[i * 3 + 2] = -400 + Math.random() * 800;
    }
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    this.dust = new THREE.Points(
      dustGeo,
      new THREE.PointsMaterial({
        color: 0xd8ff64,
        size: 2.2,
        transparent: true,
        opacity: 0.35,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    );
    this.world.add(this.dust);

    // 1. Protagonist: THE COURIER (Code Cube)
    this.buildProtagonistCourier();

    // 2. Stage 1: Task Boundary Glass Cage (Birth Chamber)
    this.buildTaskBoundaryCage();

    // 3. Stage 2: Boundary Opening & Rogue Shard Deflector
    this.buildBoundaryOpening();

    // 4. Stage 3: Sealed Test Vault Collar & Gimbal Laser Rings
    this.buildSealedVaultCollar();

    // 5. Stage 4: AST Scan Blade & 3D Syntax Tree Network
    this.buildASTScanZone();

    // 6. Stage 5: Dual Space (Pristine Source Tree, Conduit Tube & Worktree Pod)
    this.buildDualWorktreeSpace();

    // 7. Stage 6: Quarantine Gate Arena & Failure/Retry Arc
    this.buildGateArena();

    // 8. Stage 7: Master Working Tree Dock & Evidence Plates
    this.buildMasterDock();
  }

  buildProtagonistCourier() {
    this.courier = new THREE.Group();
    this.courier.position.set(-460, 100, 0);

    // 1. Inner Hyper-Luminous Quantum Core (Octahedron)
    const coreGeo = new THREE.OctahedronGeometry(26, 0);
    this.courierCoreMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: 0xd8ff64,
      emissiveIntensity: 2.8,
      roughness: 0.08,
      metalness: 0.9,
    });
    this.courierCore = new THREE.Mesh(coreGeo, this.courierCoreMat);
    this.courier.add(this.courierCore);

    // 2. Kinetic Matrix Lattice (Icosahedron wireframe)
    const latticeGeo = new THREE.IcosahedronGeometry(34, 0);
    this.courierLatticeMat = new THREE.MeshBasicMaterial({
      color: 0x5ef3d2,
      wireframe: true,
      transparent: true,
      opacity: 0.7,
    });
    this.courierLattice = new THREE.Mesh(latticeGeo, this.courierLatticeMat);
    this.courier.add(this.courierLattice);

    // 3. High-Gloss Cyber-Beveled Translucent Armor Casing (56x56x56)
    const shellGeo = new THREE.BoxGeometry(56, 56, 56);
    const frontTex = courierFaceTexture('front');
    const sideTex = courierFaceTexture('side');
    const topTex = courierFaceTexture('top');

    const frontMat = new THREE.MeshStandardMaterial({
      map: frontTex,
      roughness: 0.1,
      metalness: 0.5,
      transparent: true,
      opacity: 0.96,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.35,
    });
    const sideMat = new THREE.MeshStandardMaterial({
      map: sideTex,
      roughness: 0.12,
      metalness: 0.5,
      transparent: true,
      opacity: 0.94,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.25,
    });
    const topMat = new THREE.MeshStandardMaterial({
      map: topTex,
      roughness: 0.12,
      metalness: 0.55,
      transparent: true,
      opacity: 0.94,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.25,
    });

    // Material order for BoxGeometry: [+X, -X, +Y, -Y, +Z, -Z]
    this.courierShell = new THREE.Mesh(shellGeo, [sideMat, sideMat, topMat, topMat, frontMat, frontMat]);
    this.courier.add(this.courierShell);

    // 4. Machined Titanium Corner Bracket Clamps (8 corners)
    this.courierBrackets = new THREE.Group();
    const bracketGeo = new THREE.BoxGeometry(8, 8, 8);
    const bracketMat = new THREE.MeshStandardMaterial({
      color: 0x111c16,
      metalness: 0.95,
      roughness: 0.15,
    });
    const bOffset = 28;
    [
      [-bOffset, -bOffset, -bOffset],
      [bOffset, -bOffset, -bOffset],
      [-bOffset, bOffset, -bOffset],
      [bOffset, bOffset, -bOffset],
      [-bOffset, -bOffset, bOffset],
      [bOffset, -bOffset, bOffset],
      [-bOffset, bOffset, bOffset],
      [bOffset, bOffset, bOffset],
    ].forEach((pos) => {
      const bMesh = new THREE.Mesh(bracketGeo, bracketMat);
      bMesh.position.set(...pos);
      this.courierBrackets.add(bMesh);
    });
    this.courier.add(this.courierBrackets);

    // 5. Beveled Wireframe Highlight Edge
    const wireGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(56.5, 56.5, 56.5));
    this.courierWireMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.95 });
    this.courierWire = new THREE.LineSegments(wireGeo, this.courierWireMat);
    this.courier.add(this.courierWire);

    // 6. Gimbal Orbital Laser Rings (Gyroscopic)
    this.orbitalRing1 = new THREE.Mesh(
      new THREE.TorusGeometry(48, 1.2, 16, 64),
      new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.85 }),
    );
    this.orbitalRing1.rotation.x = Math.PI / 4;
    this.courier.add(this.orbitalRing1);

    this.orbitalRing2 = new THREE.Mesh(
      new THREE.TorusGeometry(54, 1.0, 16, 64),
      new THREE.MeshBasicMaterial({ color: 0x5ef3d2, transparent: true, opacity: 0.7 }),
    );
    this.orbitalRing2.rotation.y = -Math.PI / 3;
    this.courier.add(this.orbitalRing2);

    // Set render orders to guarantee proper transparent layering
    this.courierCore.renderOrder = 1;
    this.courierLattice.renderOrder = 2;
    this.courierShell.renderOrder = 3;
    this.courierBrackets.renderOrder = 4;
    this.courierWire.renderOrder = 5;
    this.orbitalRing1.renderOrder = 6;
    this.orbitalRing2.renderOrder = 6;

    // 7. Orbiting Code Satellites (4 Floating Rune Badges)
    this.orbitingGlyphs = new THREE.Group();
    this.orbitingGlyphs.renderOrder = 7;
    const glyphTokens = ['def count_vowels', 'vowels="aeiou"', 'SHA: 9c1f', 'pytest: PASS'];
    this.glyphSprites = [];
    glyphTokens.forEach((token, idx) => {
      const tex = createTexture(200, 48, (ctx) => {
        ctx.fillStyle = 'rgba(6, 14, 9, 0.92)';
        ctx.fillRect(2, 2, 196, 44);
        ctx.strokeStyle = '#d8ff64';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(2, 2, 196, 44);
        ctx.fillStyle = '#d8ff64';
        ctx.font = '700 18px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(token, 100, 24);
      });
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.9 }));
      sprite.scale.set(34, 8, 1);
      this.orbitingGlyphs.add(sprite);
      this.glyphSprites.push({
        sprite,
        angle: (idx / glyphTokens.length) * Math.PI * 2,
        radius: 56,
        speed: 1.2 + (idx % 2) * 0.3,
      });
    });
    this.courier.add(this.orbitingGlyphs);

    // 8. Red Crack Overlay Mesh for Failure State
    const crackGeo = new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(35, 1));
    this.crackMat = new THREE.LineBasicMaterial({ color: 0xff4747, transparent: true, opacity: 0 });
    this.crackMesh = new THREE.LineSegments(crackGeo, this.crackMat);
    this.courier.add(this.crackMesh);

    // 9. Internal Point Light
    this.courierGlow = new THREE.PointLight(0xd8ff64, 5.0, 240, 1.0);
    this.courier.add(this.courierGlow);

    // 10. Soft emissive floor glow under the courier
    const glowGeo = new THREE.PlaneGeometry(260, 260);
    this.courierFloorGlowMat = new THREE.MeshBasicMaterial({
      map: courierFloorGlowTexture(),
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.courierFloorGlow = new THREE.Mesh(glowGeo, this.courierFloorGlowMat);
    this.courierFloorGlow.rotation.x = -Math.PI / 2;
    this.courierFloorGlow.position.set(-460, -219, 0);
    this.world.add(this.courierFloorGlow);

    this.courier.userData = {
      name: 'THE_COURIER',
      file: 'solution.py',
      symbols: 'count_vowels(text)',
    };
    this.interactiveObjects.push(this.courierShell);

    this.world.add(this.courier);
  }

  buildTaskBoundaryCage() {
    this.boundaryCage = new THREE.Group();
    this.boundaryCage.position.set(-460, 100, 0);

    const metalMat = new THREE.MeshStandardMaterial({
      color: 0x0c1611,
      roughness: 0.2,
      metalness: 0.9,
    });
    const neonMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64 });

    // 1. Sleek Beveled Circular Base Dais
    const baseGeo = new THREE.CylinderGeometry(76, 82, 8, 32);
    const baseMesh = new THREE.Mesh(baseGeo, metalMat);
    baseMesh.position.y = -70;
    this.boundaryCage.add(baseMesh);

    // Glowing Phosphor Levitation Core Emitter
    const emitterCore = new THREE.Mesh(
      new THREE.RingGeometry(10, 48, 32),
      new THREE.MeshBasicMaterial({ color: 0xd8ff64, side: THREE.DoubleSide }),
    );
    emitterCore.rotation.x = -Math.PI / 2;
    emitterCore.position.y = -65.8;
    this.boundaryCage.add(emitterCore);

    // Circular Base Laser Ring
    const baseRing = new THREE.Mesh(new THREE.TorusGeometry(78, 1.2, 16, 64), neonMat);
    baseRing.rotation.x = Math.PI / 2;
    baseRing.position.y = -66;
    this.boundaryCage.add(baseRing);

    // 2. Top Magnetic Containment Ring
    const topRing = new THREE.Mesh(new THREE.TorusGeometry(78, 2, 16, 64), metalMat);
    topRing.rotation.x = Math.PI / 2;
    topRing.position.y = 75;
    this.boundaryCage.add(topRing);

    const topLaser = new THREE.Mesh(new THREE.TorusGeometry(76, 1.2, 16, 64), neonMat);
    topLaser.rotation.x = Math.PI / 2;
    topLaser.position.y = 75;
    this.boundaryCage.add(topLaser);

    // 3. Ultra-Slim Carbon Fiber Tri-Pylons with Vertical Laser Strands (120° apart)
    for (let i = 0; i < 3; i++) {
      const angle = (i / 3) * Math.PI * 2;
      const x = Math.cos(angle) * 78;
      const z = Math.sin(angle) * 78;

      const pylon = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 145, 12), metalMat);
      pylon.position.set(x, 4.5, z);
      this.boundaryCage.add(pylon);

      // Glowing emitter beacon on top of each pylon
      const beacon = new THREE.Mesh(new THREE.SphereGeometry(2.5, 12, 12), neonMat);
      beacon.position.set(x, 77, z);
      this.boundaryCage.add(beacon);
    }

    // 4. Luminous Holographic Glass Containment Sheath
    const glassGeo = new THREE.CylinderGeometry(72, 72, 140, 32, 1, true);
    this.cageMat = new THREE.MeshStandardMaterial({
      color: 0x071b10,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.12,
      roughness: 0.05,
      metalness: 0.2,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    const glassMesh = new THREE.Mesh(glassGeo, this.cageMat);
    this.boundaryCage.add(glassMesh);

    // 5. Dual Horizontal Scanning Laser Rings
    this.scanRing1 = new THREE.Mesh(
      new THREE.TorusGeometry(72.5, 0.8, 12, 64),
      new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.75 }),
    );
    this.scanRing1.rotation.x = Math.PI / 2;
    this.scanRing1.position.y = 20;
    this.boundaryCage.add(this.scanRing1);

    this.scanRing2 = new THREE.Mesh(
      new THREE.TorusGeometry(72.5, 0.8, 12, 64),
      new THREE.MeshBasicMaterial({ color: 0x5ef3d2, transparent: true, opacity: 0.6 }),
    );
    this.scanRing2.rotation.x = Math.PI / 2;
    this.scanRing2.position.y = -20;
    this.boundaryCage.add(this.scanRing2);

    this.world.add(this.boundaryCage);
  }

  buildBoundaryOpening() {
    this.boundaryZone = new THREE.Group();
    this.boundaryZone.position.set(-260, 100, 0);

    const metalMat = new THREE.MeshStandardMaterial({ color: 0x0c1611, roughness: 0.2, metalness: 0.9 });
    const neonMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64 });

    // 1. Sleek Toroidal Aperture Outer Housing
    const housing = new THREE.Mesh(new THREE.TorusGeometry(78, 5, 16, 48), metalMat);
    this.boundaryZone.add(housing);

    const housingLaser = new THREE.Mesh(new THREE.TorusGeometry(84, 1.2, 16, 64), neonMat);
    this.boundaryZone.add(housingLaser);

    // 2. Overlapping Mechanical Iris Blades (parted open in center)
    this.irisBlades = new THREE.Group();
    for (let i = 0; i < 6; i++) {
      const angle = (i / 6) * Math.PI * 2;
      const bladeShape = new THREE.Shape();
      bladeShape.moveTo(0, 0);
      bladeShape.lineTo(40, 12);
      bladeShape.lineTo(62, 0);
      bladeShape.lineTo(40, -12);
      bladeShape.closePath();

      const bladeGeo = new THREE.ShapeGeometry(bladeShape);
      const bladeMat = new THREE.MeshStandardMaterial({
        color: 0x122419,
        emissive: 0xd8ff64,
        emissiveIntensity: 0.2,
        roughness: 0.3,
        metalness: 0.8,
        side: THREE.DoubleSide,
      });
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.position.set(Math.cos(angle) * 58, Math.sin(angle) * 58, 0);
      blade.rotation.z = angle + Math.PI / 2;
      this.irisBlades.add(blade);
    }
    this.boundaryZone.add(this.irisBlades);

    // 3. Cyan Permeable Boundary Energy Membrane in Center
    const membraneGeo = new THREE.RingGeometry(0, 48, 32);
    const membraneMat = new THREE.MeshBasicMaterial({
      color: 0x5ef3d2,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.boundaryZone.add(new THREE.Mesh(membraneGeo, membraneMat));

    // 4. Deflected Rogue Shards with Animated Spark Streaks
    this.rogueShards = [];
    const shardNames = ['test_tamper.py', 'evil.sh', 'secrets.env', 'override.config'];
    for (let i = 0; i < 4; i++) {
      const sGeo = new THREE.TetrahedronGeometry(13, 0);
      const sMat = new THREE.MeshStandardMaterial({
        color: 0x220909,
        emissive: 0xff3b30,
        emissiveIntensity: 0.9,
        roughness: 0.2,
        metalness: 0.7,
      });
      const shard = new THREE.Mesh(sGeo, sMat);
      const angle = -Math.PI / 4 + (i / 3) * Math.PI / 2;
      shard.position.set(
        Math.cos(angle) * 88,
        Math.sin(angle) * 58,
        25 + (i % 2) * 20,
      );
      shard.userData = { name: shardNames[i], basePos: shard.position.clone() };

      // Deflection spark arc
      const sparkGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(shard.position.x > 0 ? 14 : -14, -12, -8),
      ]);
      const spark = new THREE.Line(sparkGeo, new THREE.LineBasicMaterial({ color: 0xff4747 }));
      shard.add(spark);

      this.boundaryZone.add(shard);
      this.rogueShards.push(shard);
    }

    this.world.add(this.boundaryZone);
  }

  buildSealedVaultCollar() {
    this.vaultCollar = new THREE.Group();
    this.vaultCollar.position.set(-80, 45, 0);

    const metalMat = new THREE.MeshStandardMaterial({ color: 0x0c1611, roughness: 0.2, metalness: 0.9 });
    const neonMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64 });

    // 1. Heavy Cylindrical Collar Frame
    const frameGeo = new THREE.CylinderGeometry(82, 82, 38, 32, 1, true);
    const frame = new THREE.Mesh(frameGeo, metalMat);
    frame.rotation.z = Math.PI / 2;
    this.vaultCollar.add(frame);

    // Dual Machined Flange Clamps with Teeth
    [-19, 19].forEach((xPos) => {
      const flange = new THREE.Mesh(new THREE.TorusGeometry(84, 4, 16, 48), metalMat);
      flange.rotation.y = Math.PI / 2;
      flange.position.x = xPos;
      this.vaultCollar.add(flange);

      const flangeLaser = new THREE.Mesh(new THREE.TorusGeometry(86, 1.0, 16, 64), neonMat);
      flangeLaser.rotation.y = Math.PI / 2;
      flangeLaser.position.x = xPos;
      this.vaultCollar.add(flangeLaser);
    });

    // 2. Triple Counter-Rotating Cryptographic Laser Rings
    this.gimbalR1 = new THREE.Mesh(new THREE.TorusGeometry(76, 2.5, 16, 64), metalMat);
    this.gimbalR2 = new THREE.Mesh(new THREE.TorusGeometry(64, 2.2, 16, 64), metalMat);
    this.gimbalR3 = new THREE.Mesh(
      new THREE.TorusGeometry(52, 2.0, 16, 64),
      new THREE.MeshStandardMaterial({ color: 0xd8ff64, emissive: 0xd8ff64, emissiveIntensity: 0.8 }),
    );

    this.vaultCollar.add(this.gimbalR1);
    this.vaultCollar.add(this.gimbalR2);
    this.vaultCollar.add(this.gimbalR3);

    // 3. Laser Locking Crosshairs
    const laserGeo = new THREE.BufferGeometry();
    laserGeo.setAttribute('position', new THREE.Float32BufferAttribute([
      -75, 0, 0, 75, 0, 0,
      0, -75, 0, 0, 75, 0,
      0, 0, -75, 0, 0, 75,
    ], 3));
    this.laserMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.9 });
    this.lasers = new THREE.LineSegments(laserGeo, this.laserMat);
    this.vaultCollar.add(this.lasers);

    this.world.add(this.vaultCollar);
  }

  buildASTScanZone() {
    this.astZone = new THREE.Group();
    this.astZone.position.set(75, 25, 0);

    // 1. Overhead Gantry Scanner Frame
    const gantryMat = new THREE.MeshStandardMaterial({ color: 0x0c1611, roughness: 0.2, metalness: 0.9 });
    const gantryBar = new THREE.Mesh(new THREE.BoxGeometry(6, 170, 8), gantryMat);
    gantryBar.position.set(-42, 0, 0);
    this.astZone.add(gantryBar);

    // 2. Horizontal Planar Laser Scan Blade (sweeps vertically across courier)
    const bladeGeo = new THREE.PlaneGeometry(80, 5);
    this.bladeMat = new THREE.MeshBasicMaterial({
      color: 0x5ef3d2,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.scanBlade = new THREE.Mesh(bladeGeo, this.bladeMat);
    this.scanBlade.position.set(0, 0, 0);
    this.astZone.add(this.scanBlade);

    // 3. 3D Branching Syntax Tree Network
    this.astBranchNodes = [];
    const astCoords = [
      { name: 'Module (task_001)', pos: [45, 50, 0], col: 0x5ef3d2, r: 8.5 },
      { name: 'FunctionDef: count_vowels', pos: [45, 24, 0], col: 0xd8ff64, r: 9.5 },
      { name: 'arg: text (str)', pos: [18, -4, 15], col: 0x8fffa8, r: 7 },
      { name: 'For: ch in text', pos: [70, -6, -10], col: 0x8fffa8, r: 7 },
      { name: 'If: ch in vowels', pos: [45, -34, 15], col: 0xffd864, r: 7.5 },
      { name: 'Return: count', pos: [45, -58, -10], col: 0x5ef3d2, r: 8 },
    ];

    astCoords.forEach((node) => {
      const mesh = new THREE.Mesh(
        new THREE.OctahedronGeometry(node.r, 0),
        new THREE.MeshStandardMaterial({
          color: node.col,
          emissive: node.col,
          emissiveIntensity: 0.6,
          roughness: 0.15,
          metalness: 0.8,
          transparent: true,
          opacity: 0.85,
        }),
      );
      mesh.position.set(...node.pos);
      mesh.userData = { name: node.name };

      const nodeWire = new THREE.LineSegments(
        new THREE.EdgesGeometry(mesh.geometry),
        new THREE.LineBasicMaterial({ color: node.col }),
      );
      mesh.add(nodeWire);

      this.astZone.add(mesh);
      this.astBranchNodes.push(mesh);
    });

    // Connecting Branches
    const branchGeo = new THREE.BufferGeometry();
    branchGeo.setAttribute('position', new THREE.Float32BufferAttribute([
      45, 50, 0, 45, 24, 0,
      45, 24, 0, 18, -4, 15,
      45, 24, 0, 70, -6, -10,
      70, -6, -10, 45, -34, 15,
      45, -34, 15, 45, -58, -10,
    ], 3));
    this.branchLines = new THREE.LineSegments(
      branchGeo,
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.65 }),
    );
    this.astZone.add(this.branchLines);

    this.world.add(this.astZone);
  }

  buildDualWorktreeSpace() {
    this.dualSpace = new THREE.Group();
    this.dualSpace.visible = false;

    const metalMat = new THREE.MeshStandardMaterial({ color: 0x0c1611, roughness: 0.25, metalness: 0.85 });

    // 1. Pristine Main Source Repository Tower
    this.sourceTree = new THREE.Group();
    this.sourceTree.position.set(260, 30, -35);

    const towerGeo = new THREE.BoxGeometry(110, 90, 50);
    const tower = new THREE.Mesh(towerGeo, metalMat);
    this.sourceTree.add(tower);

    // Glowing Fiber Lines on Repository Tower
    const fiberGeo = new THREE.EdgesGeometry(towerGeo);
    const fiberMesh = new THREE.LineSegments(fiberGeo, new THREE.LineBasicMaterial({ color: 0x5ef3d2, opacity: 0.8 }));
    this.sourceTree.add(fiberMesh);

    // Protective Sealed Glass Shroud around Source Tree
    const shroudGeo = new THREE.BoxGeometry(120, 100, 60);
    const shroudMat = new THREE.MeshStandardMaterial({
      color: 0x5ef3d2,
      roughness: 0.05,
      metalness: 0.1,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });
    this.sourceTree.add(new THREE.Mesh(shroudGeo, shroudMat));
    this.dualSpace.add(this.sourceTree);

    // 2. Curved Quantum Transit Conduit Tube
    const conduitPoints = [
      new THREE.Vector3(260, 30, -35),
      new THREE.Vector3(260, -15, 20),
      new THREE.Vector3(260, -65, 0),
      new THREE.Vector3(260, -115, 0),
    ];
    this.conduitCurve = new THREE.CatmullRomCurve3(conduitPoints);
    const tubeGeo = new THREE.TubeGeometry(this.conduitCurve, 48, 12, 16, false);
    this.tubeMat = new THREE.MeshStandardMaterial({
      color: 0x183b2a,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.25,
      roughness: 0.15,
      metalness: 0.7,
      transparent: true,
      opacity: 0.65,
      depthWrite: false,
    });
    this.conduitTube = new THREE.Mesh(tubeGeo, this.tubeMat);
    this.dualSpace.add(this.conduitTube);

    // 3. Isolated Worktree Execution Pod
    this.quarantinePod = new THREE.Group();
    this.quarantinePod.position.set(260, -115, 0);

    const podShellGeo = new THREE.CylinderGeometry(72, 72, 120, 32, 1, true);
    const podShellMat = new THREE.MeshStandardMaterial({
      color: 0x09140e,
      emissive: 0xd8ff64,
      emissiveIntensity: 0.15,
      roughness: 0.1,
      metalness: 0.3,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.podMesh = new THREE.Mesh(podShellGeo, podShellMat);
    this.quarantinePod.add(this.podMesh);

    // Magnetic levitation rings on pod
    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(74, 1.5, 16, 64), new THREE.MeshBasicMaterial({ color: 0xd8ff64 }));
    ring1.rotation.x = Math.PI / 2;
    ring1.position.y = 50;
    this.quarantinePod.add(ring1);

    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(74, 1.5, 16, 64), new THREE.MeshBasicMaterial({ color: 0xd8ff64 }));
    ring2.rotation.x = Math.PI / 2;
    ring2.position.y = -50;
    this.quarantinePod.add(ring2);

    this.dualSpace.add(this.quarantinePod);
    this.world.add(this.dualSpace);
  }

  buildGateArena() {
    this.gateArena = new THREE.Group();
    this.gateArena.position.set(480, -20, 0);
    this.gateArena.visible = false;

    const gateSpecs = [
      { id: '1', name: 'TARGETED', pass: '4/4' },
      { id: '2', name: 'HIDDEN', pass: 'PASS' },
      { id: '3', name: 'NEGATIVE', pass: 'SAFE' },
      { id: '4', name: 'REGRESSION', pass: '12/12' },
    ];

    const metalMat = new THREE.MeshStandardMaterial({ color: 0x0c1611, roughness: 0.2, metalness: 0.9 });

    this.arenaGates = [];
    gateSpecs.forEach((g, idx) => {
      const gGroup = new THREE.Group();
      gGroup.position.set(-90 + idx * 60, 0, 0);

      // Gate Arch Frame: Left Pylon, Right Pylon, Top Crossbeam
      const pylonGeo = new THREE.BoxGeometry(6, 160, 10);
      const leftPylon = new THREE.Mesh(pylonGeo, metalMat);
      leftPylon.position.x = -24;
      gGroup.add(leftPylon);

      const rightPylon = new THREE.Mesh(pylonGeo, metalMat);
      rightPylon.position.x = 24;
      gGroup.add(rightPylon);

      const beamGeo = new THREE.BoxGeometry(54, 8, 12);
      const topBeam = new THREE.Mesh(beamGeo, metalMat);
      topBeam.position.y = 80;
      gGroup.add(topBeam);

      // Overhead Placard Signage
      const placardTex = gatePlacardTexture(g.id, g.name, g.pass);
      const placard = new THREE.Mesh(
        new THREE.PlaneGeometry(36, 14),
        new THREE.MeshBasicMaterial({ map: placardTex, transparent: true, side: THREE.DoubleSide, depthWrite: false }),
      );
      placard.position.set(0, 92, 0);
      gGroup.add(placard);

      // Gate Laser Curtains
      const curtain = new THREE.Mesh(
        new THREE.PlaneGeometry(44, 148),
        new THREE.MeshBasicMaterial({
          color: 0xd8ff64,
          transparent: true,
          opacity: 0.18,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
      curtain.position.set(0, 0, 0);
      gGroup.add(curtain);

      // Status Beacon Lamp with metallic bezel
      const lamp = new THREE.Mesh(
        new THREE.SphereGeometry(4.8, 16, 16),
        new THREE.MeshStandardMaterial({
          color: 0x142018,
          emissive: 0x243329,
          emissiveIntensity: 0.6,
          roughness: 0.25,
          metalness: 0.7,
        }),
      );
      lamp.position.set(0, 80, 8);
      gGroup.add(lamp);

      const bezel = new THREE.Mesh(
        new THREE.TorusGeometry(5.8, 1.2, 8, 20),
        new THREE.MeshStandardMaterial({ color: 0x223328, roughness: 0.3, metalness: 0.8 }),
      );
      bezel.position.set(0, 80, 7.5);
      gGroup.add(bezel);

      this.arenaGates.push({ lamp, curtain });
      this.gateArena.add(gGroup);
    });

    // Red Retry Curve Arc on drift
    const retryCurve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(-30, 10, 0),
      new THREE.Vector3(-60, -20, 35),
      new THREE.Vector3(-90, -5, 0),
    );
    const retryGeo = new THREE.BufferGeometry().setFromPoints(retryCurve.getPoints(32));
    this.retryArcMat = new THREE.LineDashedMaterial({
      color: 0xff4747,
      dashSize: 5,
      gapSize: 3.5,
      transparent: true,
      opacity: 0,
    });
    this.retryArc = new THREE.Line(retryGeo, this.retryArcMat);
    this.retryArc.computeLineDistances();
    this.gateArena.add(this.retryArc);

    this.world.add(this.gateArena);
  }

  buildMasterDock() {
    this.masterDock = new THREE.Group();
    this.masterDock.position.set(590, 25, 0);
    this.masterDock.visible = false;

    // Working Tree Vault Motherboard File Socket (left side of master dock)
    const socketGroup = new THREE.Group();
    socketGroup.position.set(-56, 0, 0);

    const frameGeo = new THREE.BoxGeometry(105, 135, 68);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x09140e, roughness: 0.2, metalness: 0.9 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    socketGroup.add(frame);

    // Beveled frame neon edge
    const frameWire = new THREE.LineSegments(
      new THREE.EdgesGeometry(frameGeo),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.5 }),
    );
    socketGroup.add(frameWire);

    // Target File Slot for solution.py
    const slotGeo = new THREE.BoxGeometry(58, 58, 14);
    this.slotMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64, wireframe: true });
    this.solutionSlot = new THREE.Mesh(slotGeo, this.slotMat);
    this.solutionSlot.position.set(0, 0, 38);
    socketGroup.add(this.solutionSlot);

    // Docking Alignment Laser Guides
    const guidesGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-29, -29, 38), new THREE.Vector3(-40, -40, 58),
      new THREE.Vector3(29, -29, 38), new THREE.Vector3(40, -40, 58),
      new THREE.Vector3(-29, 29, 38), new THREE.Vector3(-40, 40, 58),
      new THREE.Vector3(29, 29, 38), new THREE.Vector3(40, 40, 58),
    ]);
    const guides = new THREE.LineSegments(guidesGeo, new THREE.LineBasicMaterial({ color: 0xd8ff64 }));
    socketGroup.add(guides);

    this.masterDock.add(socketGroup);

    // Receipt Evidence Trail Plate (right side of master dock)
    const receiptGeo = new THREE.PlaneGeometry(122, 160);
    const receiptMat = new THREE.MeshBasicMaterial({
      map: createTexture(512, 640, (ctx, w, h) => {
        ctx.fillStyle = 'rgba(7, 12, 9, 0.96)';
        ctx.fillRect(4, 4, w - 8, h - 8);
        ctx.strokeStyle = 'rgba(216, 255, 100, 0.45)';
        ctx.lineWidth = 2.5;
        ctx.strokeRect(4, 4, w - 8, h - 8);

        ctx.fillStyle = '#d8ff64';
        ctx.fillRect(24, 24, 4, h - 48);

        ctx.font = '700 20px monospace';
        ctx.fillStyle = '#d8ff64';
        ctx.fillText('AUDIT EVIDENCE TRAIL (ILLUSTRATIVE)', 42, 54);

        ctx.fillStyle = '#f4f7f4';
        ctx.font = '700 28px monospace';
        ctx.fillText('execution_log.json', 42, 100);

        ctx.strokeStyle = 'rgba(216, 255, 100, 0.2)';
        ctx.beginPath();
        ctx.moveTo(42, 120);
        ctx.lineTo(w - 42, 120);
        ctx.stroke();

        const logs = [
          '// REPORT30 Benchmark Record (illustrative)',
          '{',
          '  "task": "task_001_count_vowels",',
          '  "pre_test_hash": "9c1f...b2e7",',
          '  "post_test_hash": "9c1f...b2e7",',
          '  "hash_drift_bits": 0,',
          '  "ast_parsed": true,',
          '  "gates_passed": [1, 2, 3, 4],',
          '  "exit_code": 0,',
          '  "verified_copy_back": ["solution.py"]',
          '}',
        ];

        logs.forEach((line, i) => {
          ctx.fillStyle = line.includes('0') || line.includes('true') || line.includes('solution.py') ? '#d8ff64' : '#a8b8ad';
          ctx.font = '500 17px monospace';
          ctx.fillText(line, 42, 154 + i * 32);
        });
      }),
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    this.receiptMesh = new THREE.Mesh(receiptGeo, receiptMat);
    this.receiptMesh.position.set(22, 0, 15);
    this.receiptMesh.rotation.y = -0.16;
    this.masterDock.add(this.receiptMesh);

    this.world.add(this.masterDock);
  }

  setupPostProcessing() {
    if (this.tier === 'LOW') {
      this.usePost = false;
      return;
    }

    try {
      this.renderTarget = new THREE.WebGLRenderTarget(this.width, this.height, {
        minFilter: THREE.LinearFilter,
        magFilter: THREE.LinearFilter,
        format: THREE.RGBAFormat,
        type: THREE.HalfFloatType,
      });

      this.postScene = new THREE.Scene();
      this.postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

      this.postMaterial = new THREE.ShaderMaterial({
        uniforms: {
          tDiffuse: { value: null },
          uVelocity: { value: 0 },
          uTime: { value: 0 },
          uAlert: { value: 0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform sampler2D tDiffuse;
          uniform float uVelocity;
          uniform float uTime;
          uniform float uAlert;
          varying vec2 vUv;

          float random(vec2 p) {
            return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
          }

          void main() {
            vec2 uv = vUv;
            vec2 center = vec2(0.5, 0.5);
            vec2 dist = uv - center;
            float r2 = dot(dist, dist);

            float distortion = 1.0 + r2 * (0.025 + abs(uVelocity) * 0.0001);
            vec2 distortedUv = center + dist * distortion;

            float chroma = abs(uVelocity) * 0.0007 + uAlert * 0.0035;
            vec2 dir = normalize(dist + vec2(0.0001));

            float r = texture2D(tDiffuse, distortedUv + dir * chroma).r;
            float g = texture2D(tDiffuse, distortedUv).g;
            float b = texture2D(tDiffuse, distortedUv - dir * chroma).b;
            vec3 col = vec3(r, g, b);

            if (uAlert > 0.01) {
              col = mix(col, vec3(col.r * 1.5 + 0.18, col.g * 0.5, col.b * 0.45), uAlert * 0.55);
            }

            float grain = (random(uv + sin(uTime * 8.0)) - 0.5) * 0.024;
            col += grain;

            float vignette = smoothstep(0.95, 0.35, length(dist));
            col *= (0.75 + 0.25 * vignette);

            gl_FragColor = vec4(col, 1.0);
          }
        `,
      });

      const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.postMaterial);
      this.postScene.add(quad);
      this.usePost = true;
    } catch (e) {
      console.warn('Post-processing unavailable, rendering directly:', e);
      this.usePost = false;
    }
  }

  setupPointerEvents() {
    window.addEventListener('pointermove', (e) => {
      this.pointerTarget.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.pointerTarget.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }, { passive: true });
  }

  downgradeTier() {
    if (this.tier === 'HIGH') {
      this.tier = 'MID';
      this.renderer.setPixelRatio(1.2);
    } else if (this.tier === 'MID' && this.isMobile) {
      this.tier = 'LOW';
      this.renderer.setPixelRatio(1);
      this.usePost = false;
      if (this.renderTarget) {
        this.renderTarget.dispose();
        this.renderTarget = null;
      }
    }
  }

  triggerDrift() {
    this.alertIntensity = 1.0;
    this.laserMat.color.setHex(0xff4747);
    this.gimbalR3.material.color.setHex(0xff4747);
    this.courierCoreMat.emissive.setHex(0xff4747);
    this.courierLatticeMat.color.setHex(0xff4747);
    this.courierWireMat.color.setHex(0xff4747);
    this.crackMat.opacity = 0.9;
  }

  resetDrift() {
    this.alertIntensity = 0;
    this.laserMat.color.setHex(0xd8ff64);
    this.gimbalR3.material.color.setHex(0xd8ff64);
    this.courierCoreMat.emissive.setHex(0xd8ff64);
    this.courierLatticeMat.color.setHex(0x5ef3d2);
    this.courierWireMat.color.setHex(0xd8ff64);
    this.crackMat.opacity = 0;
  }

  resize() {
    this.width = this.canvas.clientWidth || window.innerWidth;
    this.height = this.canvas.clientHeight || window.innerHeight;
    const isCoarse = window.matchMedia('(pointer: coarse)').matches;
    const isPhone = window.innerWidth < 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    this.isMobile = isPhone || (isCoarse && window.innerWidth < 900);

    this.renderer.setSize(this.width, this.height, false);
    this.camera.aspect = this.width / Math.max(1, this.height);

    if (this.isMobile) {
      // Mobile: hero centered in upper open area between top rail and bottom copy card
      this.camera.setViewOffset(this.width, this.height, 0, this.height * 0.06, this.width, this.height);
    } else {
      // Desktop: hero centered in the free area to the right of text column (around 66% width)
      this.camera.setViewOffset(this.width, this.height, -this.width * 0.18, 0, this.width, this.height);
    }
    this.camera.updateProjectionMatrix();

    if (this.renderTarget) {
      this.renderTarget.setSize(this.width, this.height);
    }
  }

  setProgress(p) {
    this.progress = Math.max(0, Math.min(1, p));
  }

  updateProtagonistChoreography(deltaTime) {
    this.time += deltaTime;
    const p = this.progress;
    const t = this.time;

    // Smooth pointer lerp
    this.pointer.x += (this.pointerTarget.x - this.pointer.x) * 0.08;
    this.pointer.y += (this.pointerTarget.y - this.pointer.y) * 0.08;

    // Responsive Desktop and Mobile camera framing
    const isMobile = this.isMobile || window.innerWidth < 900;
    // Map stage progress p to camera spline progress u_cam with mathematical exactness across 7 stages
    const u_cam = Math.max(0, Math.min(1, (p - 0.5 / 7) / (6 / 7)));
    const camPos = this.cameraSpline.getPointAt(u_cam);
    const lookPos = this.lookSpline.getPointAt(u_cam);

    // On desktop, shift camera left so 3D objects are framed in the free area right of the text column.
    // In Stage 7, masterDock contains both the file socket and the wide receipt plate, so ease shift to +37 for full rail clearance.
    const stage7Factor = Math.max(0, Math.min(1, (p - 5.8 / 7) / (1.2 / 7)));
    const stageShiftX = -68 + stage7Factor * 105;
    const desktopShiftX = isMobile ? 0 : stageShiftX;
    // On mobile, increase distance and shift down so 3D objects are framed comfortably in the top half
    const mobileZScale = isMobile ? 2.15 : 1.0;
    const mobileYShift = isMobile ? -55 : 0;

    this.camera.position.set(
      camPos.x + desktopShiftX + this.pointer.x * 18,
      camPos.y + this.pointer.y * 12 + mobileYShift,
      camPos.z * mobileZScale,
    );
    this.camera.lookAt(lookPos.x + desktopShiftX, lookPos.y + mobileYShift, lookPos.z);

    // Dust particles
    if (this.dust) this.dust.rotation.y = t * 0.02;

    // Kinetic Courier Components Animation
    if (this.courierCore) {
      this.courierCore.rotation.x += deltaTime * 0.9;
      this.courierCore.rotation.y += deltaTime * 1.3;
    }
    if (this.courierLattice) {
      this.courierLattice.rotation.x -= deltaTime * 0.7;
      this.courierLattice.rotation.z += deltaTime * 1.1;
    }
    if (this.orbitalRing1) {
      this.orbitalRing1.rotation.z += deltaTime * 1.5;
    }
    if (this.orbitalRing2) {
      this.orbitalRing2.rotation.x -= deltaTime * 1.2;
    }

    // --- COURIER CONTINUOUS TRAJECTORY THROUGH 7 STAGES ---
    const p1 = new THREE.Vector3(-460, 100, 0); // Stage 1: In octagonal bulkhead pod
    const p2 = new THREE.Vector3(-260, 100, 0); // Stage 2: Passing aperture opening
    const p3 = new THREE.Vector3(-80, 45, 0);   // Stage 3: Stopped at vault collar
    const p4 = new THREE.Vector3(75, 25, 0);    // Stage 4: In AST scan zone
    const p5a = new THREE.Vector3(260, 25, -30);// Stage 5: Top of conduit
    const p5b = new THREE.Vector3(260, -115, 0);// Stage 5: Inside quarantine pod
    const p6a = new THREE.Vector3(440, -20, 0); // Stage 6: Gate 2 failure flinch point
    const p6b = new THREE.Vector3(530, -20, 0); // Stage 6: Cleared all gates
    const p7 = new THREE.Vector3(534, 25, 38);  // Stage 7: Docks into solution.py slot in masterDock

    let courierPos = p1.clone();
    let courierScale = 1.0;
    let courierColor = 0xd8ff64;
    let flinchOffset = new THREE.Vector3(0, 0, 0);

    // Breathing pulse when idle
    const breathing = 1.0 + 0.05 * Math.sin(t * 2.5);

    if (p <= 1 / 7) {
      // Stage 1: Born inside closed pod, pulsing slowly
      const a = p / (1 / 7);
      courierPos = p1.clone();
      courierScale = 0.88 + a * 0.12; // Clearly the protagonist from inception
      courierColor = 0xa4e8b0; // Cool dim jade green when newborn
    } else if (p <= 2 / 7) {
      // Stage 2: Code lines wrap on faces, travels through boundary opening
      const a = (p - 1 / 7) / (1 / 7);
      courierPos = p1.clone().lerp(p2, a);
      courierScale = 1.0;
      courierColor = 0xb8f070;

      // Rotate iris aperture
      if (this.boundaryPortal) this.boundaryPortal.rotation.z = t * 0.6;

      // Rogue shards deflect off boundary portal
      this.rogueShards.forEach((shard, i) => {
        const bounce = Math.sin(t * 4 + i) * 18;
        shard.position.x = shard.userData.basePos.x - bounce;
      });
    } else if (p <= 3 / 7) {
      // Stage 3: Stops at sealed vault collar; tight, tense camera; vault locks
      const a = (p - 2 / 7) / (1 / 7);
      courierPos = p2.clone().lerp(p3, a);
      courierScale = 1.0;
      courierColor = 0xd8ff64;

      // Counter-rotating gimbal laser rings
      this.gimbalR1.rotation.z = t * 1.4;
      this.gimbalR2.rotation.y = t * 2.0;
      this.gimbalR3.rotation.x = t * 2.6;
      this.lasers.rotation.z = -t * 1.4;
    } else if (p <= 4 / 7) {
      // Stage 4: Scan blade sweeps, AST nodes light one by one
      const a = (p - 3 / 7) / (1 / 7);
      courierPos = p3.clone().lerp(p4, a);
      courierScale = 1.0;
      courierColor = 0xd8ff64;

      // Sweep scan blade across courier
      this.scanBlade.position.x = -35 + a * 70;

      // Light up AST branch nodes sequentially
      this.astBranchNodes.forEach((node, i) => {
        const threshold = i / this.astBranchNodes.length;
        const lit = a >= threshold;
        node.material.opacity = lit ? 0.95 : 0.35;
        node.material.emissiveIntensity = lit ? 0.8 : 0.2;
      });
    } else if (p <= 5 / 7) {
      // Stage 5: Clone travels down conduit into quarantine space, source stays sealed
      const a = (p - 4 / 7) / (1 / 7);
      courierPos = this.conduitCurve.getPointAt(Math.min(1, Math.max(0, a)));
      courierScale = 1.0;
      courierColor = 0x8fffa8;

      // Source tree platform stays sealed and dimmed
      this.sourceTree.position.y = 25 + Math.sin(t * 0.8) * 1.5;
      this.podMesh.rotation.y = t * 0.4;
    } else if (p <= 6 / 7) {
      // Stage 6: Gates arena. Fails gate 2 (red flinch/cracks), retries cleaner, passes all 4
      const a = (p - 5 / 7) / (1 / 7);
      courierScale = 1.0;

      if (a < 0.42) {
        // Approach and fail at gate 2
        const subA = a / 0.42;
        courierPos = p5b.clone().lerp(p6a, subA);
        courierColor = 0xd8ff64;
        this.crackMat.opacity = 0;
        this.retryArcMat.opacity = 0;
      } else if (a < 0.62) {
        // Flinch, crack, red flash, recoil along retry arc
        const subA = (a - 0.42) / 0.2;
        courierColor = 0xff4747; // RED ON REJECT
        this.crackMat.opacity = 0.9;
        this.retryArcMat.opacity = 0.85;
        flinchOffset.set(
          -Math.sin(subA * Math.PI) * 24,
          Math.sin(subA * Math.PI) * 16,
          Math.sin(subA * Math.PI) * 10,
        );
        this.courier.rotation.z = Math.sin(subA * Math.PI) * 0.45;
        courierPos = p6a.clone().add(flinchOffset);
      } else {
        // Retry cleaner: gather composure, brighter, steady green, pass all four gates
        const subA = (a - 0.62) / 0.38;
        courierPos = p6a.clone().lerp(p6b, subA);
        courierColor = 0xd8ff64; // STEADY EMERALD PHOSPHOR
        this.crackMat.opacity = Math.max(0, 0.9 - subA * 2.5);
        this.retryArcMat.opacity = Math.max(0, 0.85 - subA * 2);
        this.courier.rotation.z = 0;
      }

      // Gate lights
      this.arenaGates.forEach((gate, i) => {
        const gateThresh = 0.62 + (i / 4) * 0.36;
        const pass = a >= gateThresh;
        const isFailing = a > 0.42 && a < 0.62 && i === 1;
        const lampColor = pass ? 0xd8ff64 : (isFailing ? 0xff4747 : 0x142018);
        const emissiveColor = pass ? 0xd8ff64 : (isFailing ? 0xff4747 : 0x07110a);
        const emissiveIntensity = pass ? 2.5 : (isFailing ? 3.0 : 0.2);
        gate.lamp.material.color.setHex(lampColor);
        gate.lamp.material.emissive.setHex(emissiveColor);
        gate.lamp.material.emissiveIntensity = emissiveIntensity;
        gate.curtain.material.opacity = pass ? 0.4 : 0.16;
      });
    } else {
      // Stage 7: Verified courier travels from Gate 4 exit into Master Dock solution.py slot
      const a = (p - 6 / 7) / (1 / 7);
      if (a < 0.35) {
        const subA = a / 0.35;
        courierPos = p6b.clone().lerp(p7, subA);
        courierScale = 1.0;
      } else {
        // Docked into solution.py socket
        const subA = Math.min(1.0, (a - 0.35) / 0.65);
        courierPos = p7.clone();
        courierScale = Math.max(0.82, 1.0 - subA * 0.18);
        if (subA > 0.4) {
          audio.playDock();
          this.slotMat.color.setHex(0xd8ff64);
        }
      }
      courierColor = 0xd8ff64;

      // Quarantined space retracts and dims
      this.quarantinePod.position.y = -115 - a * 40;
      this.podMesh.material.opacity = Math.max(0.1, 0.7 - a * 0.6);
      this.receiptMesh.material.opacity = Math.min(1.0, 0.4 + a * 0.6);
    }

    // Apply color and breathing to Courier
    this.courierCoreMat.emissive.setHex(isDrifting ? 0xff4747 : courierColor);
    this.courierWireMat.color.setHex(isDrifting ? 0xff4747 : courierColor);

    this.courier.position.copy(courierPos);
    this.courier.scale.setScalar(courierScale * breathing);

    // Update Screen-Space Hero Protagonist HUD Reticle & Callout
    this.updateHeroScreenTag(isDrifting, Math.min(6, Math.max(0, Math.floor(p * 7))));

    // Update internal glow, rim light, and floor glow to follow courier
    if (this.courierGlow) {
      this.courierGlow.color.setHex(isDrifting ? 0xff4747 : courierColor);
    }
    if (this.courierRimLight) {
      this.courierRimLight.position.set(courierPos.x + 35, courierPos.y + 45, courierPos.z - 70);
      this.courierRimLight.color.setHex(isDrifting ? 0xff4747 : courierColor);
    }
    if (this.courierFloorGlow) {
      this.courierFloorGlow.position.x = courierPos.x;
      this.courierFloorGlow.position.z = courierPos.z;
      this.courierFloorGlowMat.color.setHex(isDrifting ? 0xff4747 : courierColor);
      this.courierFloorGlowMat.opacity = isDrifting ? 0.95 : 0.85;
    }

    // Orbiting Satellites motion around Courier
    this.glyphSprites.forEach((item) => {
      item.angle += deltaTime * item.speed;
      item.sprite.position.set(
        Math.cos(item.angle) * item.radius,
        Math.sin(item.angle * 1.5) * 12,
        Math.sin(item.angle) * item.radius,
      );
    });

    // Inactive object fading and strict stage bleed prevention
    const activeStage = p * 7;

    this.boundaryCage.visible = activeStage < 1.4;
    this.boundaryZone.visible = activeStage >= 0.7 && activeStage < 2.3;
    this.vaultCollar.visible = activeStage >= 1.8 && activeStage < 3.3;
    this.astZone.visible = activeStage >= 2.8 && activeStage < 4.3;

    // STAGE 5 DUAL SPACE: strictly hidden before stage 5 (activeStage >= 3.8)
    this.dualSpace.visible = activeStage >= 3.8 && activeStage < 5.3;

    // STAGE 6 GATES ARENA: strictly hidden before stage 6 (activeStage >= 4.8)
    this.gateArena.visible = activeStage >= 4.8 && activeStage < 6.3;

    // STAGE 7 MASTER DOCK: strictly hidden before stage 7 (activeStage >= 5.8)
    this.masterDock.visible = activeStage >= 5.8;

    // Inactive objects fade to ~30%, not 12%
    if (this.cageMat) this.cageMat.opacity = activeStage < 1.0 ? 0.22 : 0.08;
    if (this.laserMat) this.laserMat.opacity = (activeStage >= 2.0 && activeStage <= 3.0) ? 0.95 : 0.3;
    if (this.bladeMat) this.bladeMat.opacity = (activeStage >= 3.0 && activeStage <= 4.0) ? 0.88 : 0.3;
  }

  updateHeroScreenTag(isDrifting, activeStep) {
    if (!courierHeroTag) return;

    if (this.progress > 0.985) {
      courierHeroTag.classList.add('is-hidden');
      return;
    }
    courierHeroTag.classList.remove('is-hidden');

    const worldPos = this.courier.position.clone();
    const proj = worldPos.project(this.camera);

    if (proj.z > 1) {
      courierHeroTag.classList.add('is-hidden');
      return;
    }

    const x = (proj.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-(proj.y * 0.5) + 0.5) * window.innerHeight;

    courierHeroTag.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    courierHeroTag.classList.toggle('is-breached', isDrifting || this.alertIntensity > 0.05);

    if (courierHudStatus) {
      if (isDrifting || this.alertIntensity > 0.05) {
        courierHudStatus.textContent = 'ALERT: TEST DRIFT DETECTED · DISCARDING WORKTREE';
      } else {
        courierHudStatus.textContent = HERO_STAGE_STATUSES[activeStep] || HERO_STAGE_STATUSES[0];
      }
    }
  }

  render(elapsed, deltaTime) {
    if (isReduced) return;

    // Auto-downgrade performance check (never below MID on desktop)
    if (deltaTime > 0.024) {
      this.slowFrameAccumulator += deltaTime;
      if (this.slowFrameAccumulator > 1.0) {
        this.downgradeTier();
        this.slowFrameAccumulator = 0;
      }
    } else {
      this.slowFrameAccumulator = Math.max(0, this.slowFrameAccumulator - deltaTime * 0.5);
    }

    this.updateProtagonistChoreography(deltaTime);

    if (this.usePost && this.renderTarget) {
      this.renderer.setRenderTarget(this.renderTarget);
      this.renderer.render(this.scene, this.camera);
      this.renderer.setRenderTarget(null);

      this.postMaterial.uniforms.tDiffuse.value = this.renderTarget.texture;
      this.postMaterial.uniforms.uVelocity.value = scrollVelocity;
      this.postMaterial.uniforms.uTime.value = this.time;
      this.postMaterial.uniforms.uAlert.value = this.alertIntensity;

      this.renderer.render(this.postScene, this.postCamera);
    } else {
      this.renderer.render(this.scene, this.camera);
    }
  }

  dispose() {
    this.renderer.dispose();
    if (this.renderTarget) this.renderTarget.dispose();
  }
}

/* ------------------------------------------------------------------ *
 * Initialization & Single Deterministic Ticker Loop
 * ------------------------------------------------------------------ */
function initStoryScene() {
  if (scene || isReduced) return;
  try {
    scene = new TaskScene(canvas);
  } catch (error) {
    body.classList.add('no-webgl');
    console.warn('CD-AVC 3D scene unavailable, displaying static fallback:', error);
    return;
  }
  scene.resize();
  scene.setProgress(initStep >= 0 ? (initStep + 0.5) / 7 : (storyTrigger?.scrollTrigger?.progress ?? 0));
  body.classList.add('webgl-ready');
}

function setupScroll() {
  if (isReduced) return;

  const sceneObserver = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      initStoryScene();
      sceneObserver.disconnect();
    }
  }, { rootMargin: '160px 0px' });
  sceneObserver.observe(story);

  if (story.getBoundingClientRect().top < window.innerHeight) {
    initStoryScene();
    sceneObserver.disconnect();
  }

  let manualStep = initStep >= 0;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 15) manualStep = false;
  }, { passive: true });

  const initialProgress = initStep >= 0 ? (initStep + 0.5) / 7 : 0;
  const timeline = { progress: initialProgress };
  const update = (progress) => {
    timeline.progress = progress;
    const step = Math.min(6, Math.floor(progress * 7));
    setStep(step);
    scene?.setProgress(progress);
  };

  update(initialProgress);

  storyTrigger = gsap.to(timeline, {
    progress: 1,
    ease: 'none',
    scrollTrigger: {
      trigger: story,
      start: 'top top',
      end: 'bottom bottom',
      pin: pin,
      pinSpacing: false,
      scrub: 0.5,
      invalidateOnRefresh: true,
      onUpdate: (self) => {
        if (!manualStep) update(self.progress);
      },
      onRefresh: (self) => {
        if (!manualStep) update(self.progress);
      },
    },
  });
}

function setupLenis() {
  if (isReduced) return;
  lenis = new Lenis({
    duration: 1.15,
    smoothWheel: true,
    syncTouch: false,
    autoRaf: false,
  });

  lenis.on('scroll', (e) => {
    ScrollTrigger.update();
    scrollVelocity = e.velocity || 0;
  });

  // Single Ticker: Lenis + ScrollTrigger + Three.js Timer render
  gsap.ticker.add((time) => {
    lenis?.raf(time * 1000);
    if (scene) {
      scene.timer.update();
      scene.render(scene.timer.getElapsed(), scene.timer.getDelta());
    }
  });
  gsap.ticker.lagSmoothing(1000, 16);
}

reduced.addEventListener?.('change', () => {
  setReducedState();
  if (storyTrigger) storyTrigger.kill();
  if (lenis) {
    lenis.destroy();
    lenis = null;
  }
  scene?.dispose();
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
  const progress = Math.max(0, Math.min(1, (window.scrollY - story.offsetTop) / Math.max(1, story.offsetHeight - window.innerHeight)));
  setStep(Math.min(6, Math.floor(progress * 7)));
}, { passive: true });

setReducedState();
setupScroll();
setupLenis();

window.addEventListener('load', () => {
  ScrollTrigger.refresh();
  if (initStep >= 0) {
    setStep(initStep);
    scene?.setProgress((initStep + 0.5) / 7);
  }
}, { once: true });

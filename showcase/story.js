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

const inspectTarget = document.querySelector('#inspect-target');
const inspectState = document.querySelector('#inspect-state');
const inspectBench = document.querySelector('#inspect-bench');
const inspectGain = document.querySelector('#inspect-gain');

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
let isReduced = reduced.matches;

let scene = null;
let storyTrigger = null;
let lenis = null;
let lastStep = -1;
let scrollVelocity = 0;

const STAGE_CHAMBERS = [
  'STAGE 01 / THE TASK BOUNDARY',
  'STAGE 02 / BOUNDARY FILE SELECTION',
  'STAGE 03 / SEALED TEST COLLAR',
  'STAGE 04 / AST CONTRACT SCANNER',
  'STAGE 05 / ISOLATED WORKTREE CONDUIT',
  'STAGE 06 / QUARANTINE GATE ARENA',
  'STAGE 07 / MASTER REPO COPY-BACK',
];

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

const COURIER_LINES = [
  'I am the patch. I may only touch solution.py.',
  'I come back as one file. Anything else is refused.',
  'The tests are sealed. I cannot change them.',
  'My syntax is checked against the contract.',
  'I run in a copy, so the source stays safe.',
  'Four gates. If I fail, the original file is restored.',
  'I passed every gate. Now I am copied back.',
];
const STEP_CUES = [
  'HANDED A SEALED CONTRACT: one file only, solution.py',
  'THE PATCH ARRIVES: only solution.py crosses, other files bounce off',
  'TESTS SEALED: the hash before the run must equal the hash after',
  'AST GATE: a missing symbol turns red, a found symbol turns green',
  'RUNS IN A DISPOSABLE COPY: the source tree stays untouched',
  'FOUR GATES LIGHT IN ORDER: a failure restores the original and retries',
  'VERIFIED FILE COPIED BACK into solution.py, then the receipts appear',
];
function setStep(step) {
  const sc = document.getElementById('step-cue');
  if (sc) { const s = Math.min(6, Math.max(0, step)); sc.querySelector('.cue-n').textContent = String(s + 1).padStart(2, '0'); sc.querySelector('.cue-t').textContent = STEP_CUES[s]; }
  const cl = document.getElementById('courier-line');
  if (cl) cl.textContent = COURIER_LINES[Math.min(6, Math.max(0, step))];
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

  if (inspectState) {
    inspectState.textContent = 'DRIFT_REJECTED';
    inspectState.style.color = '#ff4747';
  }

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
    if (inspectState) {
      inspectState.textContent = 'STEADY_VERIFIED';
      inspectState.style.color = '#d8ff64';
    }
    setTimeout(() => {
      if (breachTitle) breachTitle.textContent = 'TEST DRIFT DETECTED: LOCKED SUITE COMPROMISED';
      if (breachDetail) breachDetail.textContent = 'Locked SHA-256 mismatch detected. CD-AVC isolation active. Candidate write refused, worktree discarded.';
    }, 500);
  }, 3800);
}

btnDrift?.addEventListener('click', triggerDriftSimulation);

/* ------------------------------------------------------------------ *
 * Procedural Dynamic Canvas Textures
 * ------------------------------------------------------------------ */
function createTexture(width, height, draw) {
  const c = document.createElement('canvas');
  c.width = width;
  c.height = height;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  draw(ctx, width, height);
  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function courierFaceTexture() {
  return createTexture(256, 256, (ctx, w, h) => {
    ctx.fillStyle = '#0a1610';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.4)';
    ctx.lineWidth = 4;
    ctx.strokeRect(4, 4, w - 8, h - 8);

    ctx.fillStyle = '#d8ff64';
    ctx.font = '700 16px monospace';
    ctx.fillText('solution.py', 16, 32);

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.2)';
    ctx.beginPath();
    ctx.moveTo(16, 42);
    ctx.lineTo(w - 16, 42);
    ctx.stroke();

    const codeLines = [
      'def count_vowels(t):',
      '    v = "aeiou"',
      '    c = 0',
      '    for ch in t:',
      '        if ch in v:',
      '            c += 1',
      '    return c',
    ];

    codeLines.forEach((line, i) => {
      ctx.fillStyle = line.includes('def') || line.includes('return') ? '#d8ff64' : '#b7c7bc';
      ctx.font = '500 13px monospace';
      ctx.fillText(line, 16, 68 + i * 24);
    });
  });
}

function gridFloorTexture() {
  return createTexture(2048, 2048, (ctx, w, h) => {
    ctx.strokeStyle = 'rgba(150, 180, 160, 0.12)';
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

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.22)';
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
    ctx.fillStyle = 'rgba(6, 10, 8, 0.94)';
    ctx.fillRect(4, 4, w - 8, h - 8);
    ctx.strokeStyle = color === '#ff4747' ? 'rgba(255, 71, 71, 0.5)' : 'rgba(216, 255, 100, 0.3)';
    ctx.lineWidth = 2;
    ctx.strokeRect(4, 4, w - 8, h - 8);

    ctx.fillStyle = color;
    ctx.fillRect(20, 20, 4, h - 40);

    ctx.font = '700 18px monospace';
    ctx.fillStyle = color;
    ctx.fillText(title.toUpperCase(), 38, 48);

    ctx.fillStyle = '#f4f7f4';
    ctx.font = '700 30px monospace';
    ctx.fillText(code, 38, 98);

    ctx.fillStyle = '#8f9f94';
    ctx.font = '500 18px system-ui, sans-serif';
    ctx.fillText(detail, 38, 142);
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
    this.isMobile = window.innerWidth < 768 || /Android|iPhone|iPad/i.test(navigator.userAgent);
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
    this.renderer.toneMappingExposure = 1.7;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b1713);
    this.scene.fog = new THREE.FogExp2(0x0b1612, 0.00035);

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
    this.scene.add(new THREE.HemisphereLight(0xe4f2ea, 0x1a2a22, 1.9));

    const mainKey = new THREE.DirectionalLight(0xffffff, 3.2);
    mainKey.position.set(-300, 500, 600);
    this.scene.add(mainKey);

    const rimLight = new THREE.DirectionalLight(0xd8ff64, 1.8);
    rimLight.position.set(600, 300, -400);
    this.scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0x5ef3d2, 1.1);
    fillLight.position.set(-400, -100, 400);
    this.scene.add(fillLight);
    this.scene.add(new THREE.AmbientLight(0x6f8f80, 1.2));
    this.courierLight = new THREE.PointLight(0xd8ff64, 90000, 520, 2);
    this.scene.add(this.courierLight);
    this.stageLights = [];
    [[-460,240],[-260,170],[-80,90],[75,70],[260,20],[480,40],[780,120]].forEach(([x,y]) => {
      const l = new THREE.PointLight(0x9fffd8, 60000, 520, 2);
      l.position.set(x, y, 160);
      this.scene.add(l);
      this.stageLights.push(l);
    });
  }

  buildSplineCameraTrack() {
    // 7 Spatial Camera Waypoints: Narrative shots (intimate -> dynamic -> tense -> macro -> wide -> arena -> orbit)
    const cameraWaypoints = [
      new THREE.Vector3(-420, 215, 830),  // 01 Contract: Intimate close low-angle looking at newborn courier
      new THREE.Vector3(-240, 150, 740),  // 02 Patch: Tracking side angle following courier past boundary opening
      new THREE.Vector3(-60, 80, 470),    // 03 Tests: Low, tense macro shot right behind courier at locked vault
      new THREE.Vector3(80, 50, 400),     // 04 AST: Close profile shot watching AST scan beam sweep syntax nodes
      new THREE.Vector3(270, 0, 620),   // 05 Worktree: Wide pull-back shot showing dual spaces & conduit tube
      new THREE.Vector3(480, 10, 520),   // 06 Gates: Low-angle dramatic arena shot framing retry arc
      new THREE.Vector3(775, 100, 620),   // 07 Copy-back: Ascending orbit shot as verified courier docks
    ];

    const lookWaypoints = [
      new THREE.Vector3(-460, 200, 0),
      new THREE.Vector3(-260, 130, 0),
      new THREE.Vector3(-80, 50, 0),
      new THREE.Vector3(75, 25, 0),
      new THREE.Vector3(260, -90, 0),
      new THREE.Vector3(480, -20, 0),
      new THREE.Vector3(780, 70, 0),
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
      opacity: 0.75,
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
        size: 2.0,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    );
    this.world.add(this.dust);
    this.makeLabel = (text, color, w) => {
      const tx = createTexture(512, 96, (ctx, cw, ch) => {
        ctx.fillStyle = 'rgba(6,10,8,0.9)'; ctx.fillRect(2, 2, cw - 4, ch - 4);
        ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.strokeRect(2, 2, cw - 4, ch - 4);
        ctx.fillStyle = color; ctx.font = '700 34px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(text, cw / 2, ch / 2);
      });
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false }));
      sp.scale.set(w, w * 96 / 512, 1);
      return sp;
    };

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

    // 9. Route, pylons and trail: the courier's path through the pipeline
    this.buildRouteAndBeacons();

    // Action labels that make cause and effect legible
    const pass = this.makeLabel('solution.py  PASSES', '#d8ff64', 120); pass.position.set(-200, 175, 10); this.boundaryZone.parent.add(pass); this.passLabel = pass;
    const refused = this.makeLabel('tests / other files  REFUSED', '#ff6b6b', 150); refused.position.set(-200, 148, 10); this.world.add(refused); this.refusedLabel = refused;
    this.astMissing = this.makeLabel('symbol missing', '#ff4747', 110); this.astMissing.position.set(75, 110, 10); this.world.add(this.astMissing);
    this.astFound = this.makeLabel('count_vowels  FOUND', '#d8ff64', 130); this.astFound.position.set(75, 110, 10); this.world.add(this.astFound); this.astFound.visible = false;
    // direction chevrons along the route (left to right)
    this.chevrons = [];
    const cm = new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.8 });
    for (let i = 0; i < 14; i++) {
      const m = new THREE.Mesh(new THREE.ConeGeometry(7, 16, 3), cm.clone());
      m.rotation.z = -Math.PI / 2;
      this.world.add(m);
      this.chevrons.push(m);
    }
  }

  buildRouteAndBeacons() {
    const stops = [[-460,200,0],[-260,130,0],[-80,50,0],[75,25,0],[260,50,-40],[260,-110,0],[430,-20,0],[540,-20,0],[780,70,78]];
    const curve = new THREE.CatmullRomCurve3(stops.map((s) => new THREE.Vector3(...s)), false, 'centripetal', 0.5);
    this.routeCurveObj = curve;
    this.routeLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(curve.getPoints(240)),
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.35 }),
    );
    this.world.add(this.routeLine);
    const names = ['01','02','03','04','05','06','07'];
    const xy = [[-460,200],[-260,130],[-80,50],[75,25],[260,-30],[480,-20],[780,70]];
    xy.forEach(([x, y], i) => {
      const pyl = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x,-220,0), new THREE.Vector3(x,y,0)]),
        new THREE.LineBasicMaterial({ color: 0x5ef3d2, transparent: true, opacity: 0.28 }),
      );
      this.world.add(pyl);
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(46, 52, 48),
        new THREE.MeshBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false }),
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(x, -219, 0);
      this.world.add(ring);
      const tex = createTexture(128, 128, (ctx) => {
        ctx.fillStyle = '#d8ff64';
        ctx.font = '700 64px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(names[i], 64, 64);
      });
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85, depthWrite: false }));
      sp.scale.set(40, 40, 1);
      sp.position.set(x, -178, 0);
      this.world.add(sp);
    });
    // glowing trail behind the courier
    this.trailN = 90;
    this.trailPts = [];
    this.trailGeo = new THREE.BufferGeometry();
    this.trailGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(this.trailN * 3), 3));
    this.trail = new THREE.Line(this.trailGeo, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9 }));
    this.trail.frustumCulled = false;
    this.world.add(this.trail);
  }

  buildProtagonistCourier() {
    this.courier = new THREE.Group();
    this.courier.position.set(-460, 200, 0);

    // Visible Inner Energetic Core
    const coreGeo = new THREE.BoxGeometry(16, 16, 16);
    this.courierCoreMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64 });
    this.courierCore = new THREE.Mesh(coreGeo, this.courierCoreMat);
    this.courier.add(this.courierCore);

    // Outer Translucent Glass Code Shell (28x28x28)
    const shellGeo = new THREE.BoxGeometry(28, 28, 28);
    const codeTexture = courierFaceTexture();

    const faceMat = new THREE.MeshStandardMaterial({
      map: codeTexture,
      roughness: 0.15,
      metalness: 0.3,
      transparent: true,
      opacity: 0.88,
    });
    const sideMat = new THREE.MeshStandardMaterial({
      color: 0x12241a,
      roughness: 0.2,
      metalness: 0.6,
      transparent: true,
      opacity: 0.75,
    });

    this.courierShell = new THREE.Mesh(shellGeo, [sideMat, sideMat, sideMat, sideMat, faceMat, sideMat]);
    this.courier.add(this.courierShell);

    // Beveled Wireframe Edge
    const wireGeo = new THREE.EdgesGeometry(shellGeo);
    this.courierWireMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.6 });
    this.courierWire = new THREE.LineSegments(wireGeo, this.courierWireMat);
    this.courier.add(this.courierWire);

    // Orbiting Code Glyphs (8 small floating runes)
    this.orbitingGlyphs = new THREE.Group();
    const glyphChars = ['{', '}', 'def', '->', 'int', '""', '+1', 'ret'];
    this.glyphSprites = [];
    glyphChars.forEach((ch, idx) => {
      const tex = createTexture(64, 64, (ctx) => {
        ctx.fillStyle = '#d8ff64';
        ctx.font = '700 32px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(ch, 32, 32);
      });
      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.7 }));
      sprite.scale.set(10, 10, 1);
      this.orbitingGlyphs.add(sprite);
      this.glyphSprites.push({ sprite, angle: (idx / glyphChars.length) * Math.PI * 2, radius: 26 + (idx % 2) * 6 });
    });
    this.courier.add(this.orbitingGlyphs);

    // Red Crack Overlay Mesh for Failure State
    const crackGeo = new THREE.WireframeGeometry(new THREE.IcosahedronGeometry(17, 1));
    this.crackMat = new THREE.LineBasicMaterial({ color: 0xff4747, transparent: true, opacity: 0 });
    this.crackMesh = new THREE.LineSegments(crackGeo, this.crackMat);
    this.courier.add(this.crackMesh);

    this.courier.userData = {
      name: 'THE_COURIER',
      file: 'solution.py',
      symbols: 'count_vowels(text)',
      state: 'IDLE_BREATHING',
    };
    this.interactiveObjects.push(this.courierShell);

    this.world.add(this.courier);
  }

  buildTaskBoundaryCage() {
    this.boundaryCage = new THREE.Group();
    this.boundaryCage.position.set(-460, 200, 0);

    // Closed Glass Outline (Task Scope Boundary)
    const cageGeo = new THREE.BoxGeometry(160, 140, 100);
    const cageEdges = new THREE.EdgesGeometry(cageGeo);
    const cageMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.4 });
    const wireCage = new THREE.LineSegments(cageEdges, cageMat);
    this.boundaryCage.add(wireCage);

    // Translucent Boundary Glass Panes
    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x09140f,
      roughness: 0.1,
      metalness: 0.4,
      transparent: true,
      opacity: 0.18,
    });
    const glassMesh = new THREE.Mesh(cageGeo, glassMat);
    this.boundaryCage.add(glassMesh);

    // Specification Status Plate
    const specPlate = new THREE.Mesh(
      new THREE.PlaneGeometry(220, 80),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'STAGE 01 · TASK BOUNDARY', code: 'solution.py', detail: 'declared scope: count_vowels' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    specPlate.position.set(0, 110, 0);
    this.boundaryCage.add(specPlate);

    this.world.add(this.boundaryCage);
  }

  buildBoundaryOpening() {
    this.boundaryZone = new THREE.Group();
    this.boundaryZone.position.set(-260, 130, 0);

    // Hexagonal Boundary Portal Ring
    const ringGeo = new THREE.RingGeometry(85, 95, 6);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x5ef3d2, side: THREE.DoubleSide });
    this.boundaryPortal = new THREE.Mesh(ringGeo, ringMat);
    this.boundaryZone.add(this.boundaryPortal);

    // Deflecting Rogue Shards (untrusted file fragments)
    this.rogueShards = [];
    const shardNames = ['test_tamper.py', 'evil.sh', 'override.config', 'leak.patch'];
    for (let i = 0; i < 4; i++) {
      const sGeo = new THREE.TetrahedronGeometry(14, 0);
      const sMat = new THREE.MeshStandardMaterial({
        color: 0x1f0b0b,
        emissive: 0xff3b30,
        emissiveIntensity: 0.4,
        roughness: 0.3,
      });
      const shard = new THREE.Mesh(sGeo, sMat);
      shard.position.set(-240 + (i % 2 === 0 ? -50 : 50), 110 + i * 22, 35 + i * 14);
      shard.userData = { name: shardNames[i], basePos: shard.position.clone() };
      this.boundaryZone.add(shard);
      this.rogueShards.push(shard);
    }

    this.world.add(this.boundaryZone);
  }

  buildSealedVaultCollar() {
    this.vaultCollar = new THREE.Group();
    this.vaultCollar.position.set(-80, 50, 0);

    // Mechanical Collar Frame
    const frameGeo = new THREE.CylinderGeometry(110, 110, 36, 16, 1, true);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x2f5a46, emissive: 0x1d6a4a, emissiveIntensity: 0.9, roughness: 0.4, metalness: 0.3, side: THREE.DoubleSide, transparent: true, opacity: 0.55 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    frame.rotation.z = Math.PI / 2;
    this.vaultCollar.add(frame);

    // Triple Counter-Rotating Gimbal Laser Rings
    this.gimbalR1 = new THREE.Mesh(new THREE.TorusGeometry(100, 3.5, 12, 48), frameMat);
    this.gimbalR2 = new THREE.Mesh(new THREE.TorusGeometry(82, 3, 12, 48), frameMat);
    this.gimbalR3 = new THREE.Mesh(
      new THREE.TorusGeometry(64, 2.5, 12, 48),
      new THREE.MeshStandardMaterial({ color: 0xd8ff64, emissive: 0xd8ff64, emissiveIntensity: 0.4 }),
    );

    this.vaultCollar.add(this.gimbalR1);
    this.vaultCollar.add(this.gimbalR2);
    this.vaultCollar.add(this.gimbalR3);

    // Crossfire Laser Lines
    const laserGeo = new THREE.BufferGeometry();
    laserGeo.setAttribute('position', new THREE.Float32BufferAttribute([
      -95, 0, 0, 95, 0, 0,
      0, -95, 0, 0, 95, 0,
    ], 3));
    this.laserMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.85 });
    this.lasers = new THREE.LineSegments(laserGeo, this.laserMat);
    this.vaultCollar.add(this.lasers);

    // Sealed Vault Status Plate
    const vaultPlate = new THREE.Mesh(
      new THREE.PlaneGeometry(240, 80),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'GATE 01 · LOCKED TESTS', code: '9c1f…b2e7', detail: 'sha-256 before == after' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    vaultPlate.position.set(0, 130, 0);
    this.vaultCollar.add(vaultPlate);
    [['BEFORE THE RUN', -112], ['AFTER THE RUN', 112]].forEach(([t, x]) => {
      const hp = new THREE.Mesh(
        new THREE.PlaneGeometry(200, 70),
        new THREE.MeshBasicMaterial({ map: statusPlateTexture({ title: t, code: '9c1f…b2e7', detail: 'sha-256 · example hash' }), transparent: true, side: THREE.DoubleSide }),
      );
      hp.position.set(x, -135, 30);
      this.vaultCollar.add(hp);
    });
    const eq = createTexture(128, 128, (ctx) => { ctx.fillStyle = '#d8ff64'; ctx.font = '700 100px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('=', 64, 64); });
    const eqS = new THREE.Sprite(new THREE.SpriteMaterial({ map: eq, transparent: true }));
    eqS.scale.set(40, 40, 1); eqS.position.set(0, -135, 30);
    this.vaultCollar.add(eqS);

    this.world.add(this.vaultCollar);
  }

  buildASTScanZone() {
    this.astZone = new THREE.Group();
    this.astZone.position.set(75, 25, 0);

    // Glowing Vertical Scan Blade (sweeps across courier in stage 4)
    const bladeGeo = new THREE.PlaneGeometry(6, 120);
    this.bladeMat = new THREE.MeshBasicMaterial({
      color: 0x5ef3d2,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
    });
    this.scanBlade = new THREE.Mesh(bladeGeo, this.bladeMat);
    this.scanBlade.position.set(-30, 0, 0);
    this.astZone.add(this.scanBlade);

    // 3D Syntax Tree Network (AST branches surrounding courier)
    this.astBranchNodes = [];
    const astCoords = [
      { name: 'Module (task_001)', pos: [0, 42, 0], col: 0x5ef3d2, r: 6 },
      { name: 'FunctionDef: count_vowels', pos: [0, 18, 0], col: 0xd8ff64, r: 8 },
      { name: 'arg: text', pos: [-24, -6, 10], col: 0x8fffa8, r: 5 },
      { name: 'For: ch in text', pos: [22, -8, -8], col: 0x8fffa8, r: 5 },
      { name: 'If: ch in "aeiou"', pos: [0, -28, 14], col: 0xffd864, r: 5.5 },
      { name: 'Return: total', pos: [0, -42, -10], col: 0x5ef3d2, r: 6 },
    ];

    astCoords.forEach((node) => {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(node.r, 16, 16),
        new THREE.MeshBasicMaterial({ color: node.col, transparent: true, opacity: 0.15 }),
      );
      mesh.position.set(...node.pos);
      mesh.userData = { name: node.name };
      this.astZone.add(mesh);
      this.astBranchNodes.push(mesh);
    });

    // Connecting Branches
    const branchGeo = new THREE.BufferGeometry();
    branchGeo.setAttribute('position', new THREE.Float32BufferAttribute([
      0, 42, 0, 0, 18, 0,
      0, 18, 0, -24, -6, 10,
      0, 18, 0, 22, -8, -8,
      22, -8, -8, 0, -28, 14,
      0, -28, 14, 0, -42, -10,
    ], 3));
    this.branchLines = new THREE.LineSegments(
      branchGeo,
      new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.25 }),
    );
    this.astZone.add(this.branchLines);

    this.world.add(this.astZone);
  }

  buildDualWorktreeSpace() {
    this.dualSpace = new THREE.Group();

    // 1. Pristine Main Source Tree Platform (elevated, sealed behind protective glass)
    this.sourceTree = new THREE.Group();
    this.sourceTree.position.set(260, 60, -40);

    const cabinetGeo = new THREE.BoxGeometry(160, 110, 80);
    const cabinetMat = new THREE.MeshStandardMaterial({ color: 0x0c1510, roughness: 0.3, metalness: 0.7 });
    const cabinet = new THREE.Mesh(cabinetGeo, cabinetMat);
    this.sourceTree.add(cabinet);

    // Protective Sealed Glass Shroud around Source Tree
    const shroudGeo = new THREE.BoxGeometry(176, 126, 96);
    const shroudMat = new THREE.MeshStandardMaterial({
      color: 0x5ef3d2,
      roughness: 0.1,
      metalness: 0.2,
      transparent: true,
      opacity: 0.22,
    });
    this.sourceTree.add(new THREE.Mesh(shroudGeo, shroudMat));

    // Status Label: Pristine Source
    const sourceLabel = new THREE.Mesh(
      new THREE.PlaneGeometry(160, 40),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'SOURCE REPOSITORY', code: 'main (clean)', detail: 'sealed · write-protected' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    sourceLabel.position.set(0, 80, 0);
    this.sourceTree.add(sourceLabel);
    this.dualSpace.add(this.sourceTree);

    // 2. Curved Conduit Tube (TubeGeometry on CatmullRomCurve3 connecting source to quarantine pod)
    const conduitPoints = [
      new THREE.Vector3(260, 50, -40),
      new THREE.Vector3(260, -20, 20),
      new THREE.Vector3(260, -70, 0),
      new THREE.Vector3(260, -110, 0),
    ];
    this.conduitCurve = new THREE.CatmullRomCurve3(conduitPoints);
    const tubeGeo = new THREE.TubeGeometry(this.conduitCurve, 48, 16, 16, false);
    this.tubeMat = new THREE.MeshStandardMaterial({
      color: 0x10251c,
      roughness: 0.2,
      metalness: 0.8,
      transparent: true,
      opacity: 0.55,
      wireframe: true,
    });
    this.conduitTube = new THREE.Mesh(tubeGeo, this.tubeMat);
    this.dualSpace.add(this.conduitTube);

    // 3. Subterranean Quarantined Reactor Pod
    this.quarantinePod = new THREE.Group();
    this.quarantinePod.position.set(260, -110, 0);

    const podShellGeo = new THREE.CylinderGeometry(130, 130, 160, 8, 1, true);
    const podShellMat = new THREE.MeshStandardMaterial({
      color: 0x090f0c,
      roughness: 0.4,
      metalness: 0.7,
      wireframe: true,
    });
    this.podMesh = new THREE.Mesh(podShellGeo, podShellMat);
    this.quarantinePod.add(this.podMesh);

    // Quarantined Worktree Plate
    const worktreePlate = new THREE.Mesh(
      new THREE.PlaneGeometry(240, 75),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'ISOLATION SPACE', code: 'git worktree', detail: 'disposable /tmp/cdavc-worktree' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    worktreePlate.position.set(0, 110, 0);
    this.quarantinePod.add(worktreePlate);

    this.dualSpace.add(this.quarantinePod);
    this.world.add(this.dualSpace);
  }

  buildGateArena() {
    this.gateArena = new THREE.Group();
    this.gateArena.position.set(480, -20, 0);

    const gateSpecs = [
      { id: '1', name: 'TARGETED', pass: '4/4' },
      { id: '2', name: 'HIDDEN', pass: 'pass' },
      { id: '3', name: 'NEGATIVE', pass: 'safe' },
      { id: '4', name: 'REGRESSION', pass: '12/12' },
    ];

    this.arenaGates = [];
    gateSpecs.forEach((g, idx) => {
      const gGroup = new THREE.Group();
      gGroup.position.set(-110 + idx * 75, 0, 0);

      // Gate Arch Beam
      const arch = new THREE.Mesh(
        new THREE.BoxGeometry(8, 160, 12),
        new THREE.MeshStandardMaterial({ color: 0x111c16, roughness: 0.3, metalness: 0.8 }),
      );
      gGroup.add(arch);

      // Gate Laser Curtains
      const curtain = new THREE.Mesh(
        new THREE.PlaneGeometry(55, 140),
        new THREE.MeshBasicMaterial({
          color: 0xd8ff64,
          transparent: true,
          opacity: 0.12,
          side: THREE.DoubleSide,
        }),
      );
      curtain.position.set(27.5, 0, 0);
      gGroup.add(curtain);

      // Status Beacon
      const lamp = new THREE.Mesh(
        new THREE.SphereGeometry(5.5, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x243329 }),
      );
      lamp.position.set(0, 85, 0);
      gGroup.add(lamp);

      this.arenaGates.push({ lamp, curtain });
      this.gateArena.add(gGroup);
    });

    // Red Retry Curve Arc (Dashed arc showing courier flinch and fallback)
    const retryCurve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(-35, 10, 0),     // Gate 2 failure point
      new THREE.Vector3(-70, -30, 40),   // Recoil arc apex
      new THREE.Vector3(-110, -5, 0),    // Retry launch point
    );
    const retryPoints = retryCurve.getPoints(32);
    const retryGeo = new THREE.BufferGeometry().setFromPoints(retryPoints);
    this.retryArcMat = new THREE.LineDashedMaterial({
      color: 0xff4747,
      dashSize: 6,
      gapSize: 4,
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
    this.masterDock.position.set(780, 70, 0);

    // Working tree panel: file tree where solution.py lands
    const treeTex = createTexture(512, 400, (ctx, w, h) => {
      ctx.fillStyle = 'rgba(7, 14, 11, 0.96)';
      ctx.fillRect(4, 4, w - 8, h - 8);
      ctx.strokeStyle = 'rgba(216, 255, 100, 0.4)';
      ctx.lineWidth = 2;
      ctx.strokeRect(4, 4, w - 8, h - 8);
      ctx.fillStyle = '#d8ff64';
      ctx.font = '700 22px monospace';
      ctx.fillText('WORKING TREE', 28, 52);
      ctx.fillStyle = 'rgba(216,255,100,0.2)';
      ctx.fillRect(28, 66, w - 56, 2);
      const rows = [
        [110, '#9fb3a6', 'repo/'],
        [150, '#9fb3a6', '  src/'],
        [200, '#6f8176', '    solution.py   (previous)'],
        [250, '#9fb3a6', '  tests/   locked, sha-256'],
        [300, '#9fb3a6', '  results/'],
        [340, '#6f8176', '    (empty)'],
      ];
      ctx.font = '500 24px monospace';
      rows.forEach(([y, col, t]) => { ctx.fillStyle = col; ctx.fillText(t, 28, y + 8); });
    });
    this.treePanel = new THREE.Mesh(new THREE.PlaneGeometry(190, 150), new THREE.MeshBasicMaterial({ map: treeTex, transparent: true, side: THREE.DoubleSide }));
    this.treePanel.position.set(-90, 0, 0);
    this.masterDock.add(this.treePanel);

    // Verified solution.py row that fades in when the courier lands
    const rowTex = createTexture(512, 52, (ctx, w, h) => {
      ctx.fillStyle = 'rgba(216, 255, 100, 0.95)';
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = '#0a130e';
      ctx.font = '700 26px monospace';
      ctx.fillText('    solution.py   VERIFIED', 16, 36);
    });
    this.slotBar = new THREE.Mesh(new THREE.PlaneGeometry(175, 17.5), new THREE.MeshBasicMaterial({ map: rowTex, transparent: true, opacity: 0 }));
    this.slotBar.position.set(-90, 0, 2);
    this.masterDock.add(this.slotBar);

    // legacy handle used by the choreography
    this.slotMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64, visible: false });
    this.solutionSlot = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), this.slotMat);

    const card = (title, lines, extra) => new THREE.Mesh(
      new THREE.PlaneGeometry(120, 86),
      new THREE.MeshBasicMaterial({
        map: createTexture(512, 366, (ctx, w, h) => {
          ctx.fillStyle = 'rgba(7, 12, 9, 0.97)';
          ctx.fillRect(4, 4, w - 8, h - 8);
          ctx.strokeStyle = 'rgba(216, 255, 100, 0.45)';
          ctx.lineWidth = 2;
          ctx.strokeRect(4, 4, w - 8, h - 8);
          ctx.fillStyle = '#d8ff64';
          ctx.font = '700 30px monospace';
          ctx.fillText(title, 24, 58);
          ctx.fillStyle = '#c9d6cd';
          ctx.font = '500 24px monospace';
          lines.forEach((l, i) => ctx.fillText(l, 24, 112 + i * 38));
          ctx.fillStyle = '#6f8176';
          ctx.font = '500 18px monospace';
          ctx.fillText(extra, 24, h - 24);
        }),
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
      }),
    );
    this.receiptMesh = card('execution_log.json', ['{ "task": "task_001",', '  "gates": [1,2,3,4],', '  "verified": ["solution.py"] }'], 'timing, diff log, gate verdicts');
    this.receiptMesh.position.set(70, 48, 14);
    this.receiptMesh.rotation.y = -0.18;
    this.masterDock.add(this.receiptMesh);
    this.reportMesh = card('execution_report.md', ['# Execution report', 'gate verdicts, in order', 'readable diff of the patch'], 'illustrative content');
    this.reportMesh.position.set(70, -48, 14);
    this.reportMesh.rotation.y = -0.18;
    this.masterDock.add(this.reportMesh);

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
            col *= (0.9 + 0.1 * vignette);

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
    } else if (this.tier === 'MID') {
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
    this.courierCoreMat.color.setHex(0xff4747);
    this.crackMat.opacity = 0.9;
  }

  resetDrift() {
    this.alertIntensity = 0;
    this.laserMat.color.setHex(0xd8ff64);
    this.gimbalR3.material.color.setHex(0xd8ff64);
    this.courierCoreMat.color.setHex(0xd8ff64);
    this.crackMat.opacity = 0;
  }

  resize() {
    this.width = this.canvas.clientWidth || window.innerWidth;
    this.height = this.canvas.clientHeight || window.innerHeight;

    this.renderer.setSize(this.width, this.height, false);
    this.camera.aspect = this.width / Math.max(1, this.height);
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

    // Mobile vertical framing offset: center hero above bottom copy sheet
    const mobileYOffset = this.isMobile ? -25 : 0;

    // Camera Spline Pathing
    const camPos = this.cameraSpline.getPointAt(p);
    const lookPos = this.lookSpline.getPointAt(p);

    const aspect = this.width / Math.max(1, this.height);
    const zoom = aspect < 1 ? Math.max(1, 1.2 / aspect) : 1;
    let lkx = lookPos.x; let lky = lookPos.y;
    let cpx = camPos.x; let cpy = camPos.y;
    if (aspect < 1 && this.courier) {
      const dx = this.courier.position.x - lookPos.x;
      const dy = (this.courier.position.y - lookPos.y) * 0.8;
      lkx += dx; lky += dy; cpx += dx; cpy += dy;
    }
    const cx = lkx + (cpx - lkx) * zoom;
    const cy = lky + (cpy - lky) * zoom;
    const cz = camPos.z * zoom;
    this.camera.position.set(
      cx + this.pointer.x * 24,
      cy + this.pointer.y * 18 + mobileYOffset,
      cz,
    );
    if (aspect >= 1) {
      this.camera.setViewOffset(this.width, this.height, -this.width * 0.17, -this.height * 0.11, this.width, this.height);
    } else {
      this.camera.setViewOffset(this.width, this.height, 0, this.height * 0.12, this.width, this.height);
    }
    this.camera.lookAt(lkx, lky + mobileYOffset, lookPos.z);

    // Dust particles
    if (this.dust) this.dust.rotation.y = t * 0.02;
    const st = p * 7;
    if (this.chevrons && this.routeCurveObj) {
      this.chevrons.forEach((m, i) => {
        const u = ((i / this.chevrons.length) + t * 0.05) % 1;
        const pt = this.routeCurveObj.getPointAt(u);
        m.position.copy(pt);
        m.material.opacity = 0.15 + 0.5 * Math.max(0, 1 - Math.abs(u * 7 - st) / 1.6);
      });
    }
    if (this.refusedLabel) { this.refusedLabel.visible = st > 0.9 && st < 2.1; this.passLabel.visible = st > 0.9 && st < 2.1; }
    if (this.astMissing && !(st > 2.6 && st < 4.6)) { this.astMissing.visible = false; this.astFound.visible = false; }

    // --- COURIER CONTINUOUS TRAJECTORY THROUGH 7 STAGES ---
    // Positions corresponding to each stage
    const p1 = new THREE.Vector3(-460, 200, 0); // Stage 1: In glass boundary cage
    const p2 = new THREE.Vector3(-260, 130, 0); // Stage 2: Passing boundary opening
    const p3 = new THREE.Vector3(-80, 50, 0);   // Stage 3: Stopped at vault collar
    const p4 = new THREE.Vector3(75, 25, 0);    // Stage 4: In AST scan zone
    const p5a = new THREE.Vector3(260, 50, -40);// Stage 5: Top of conduit
    const p5b = new THREE.Vector3(260, -110, 0);// Stage 5: Inside quarantine pod
    const p6a = new THREE.Vector3(430, -20, 0); // Stage 6: Gate 2 failure flinch point
    const p6b = new THREE.Vector3(540, -20, 0); // Stage 6: Cleared all gates
    const p7 = new THREE.Vector3(660, 70, 40);  // Stage 7: Docks into solution.py slot

    let courierPos = p1.clone();
    let courierScale = 1.0;
    let courierColor = 0xd8ff64;
    let flinchOffset = new THREE.Vector3(0, 0, 0);

    // Breathing pulse when idle
    const breathing = 1.0 + 0.05 * Math.sin(t * 2.5);

    if (p <= 1 / 7) {
      // Stage 1: Born inside closed glass outline, tiny, pulsing slowly
      const a = p / (1 / 7);
      courierPos = p1.clone();
      courierScale = 0.45 + a * 0.35; // grows from tiny to medium
      courierColor = 0xa4e8b0; // dim cool jade green when unsure
      if (inspectState && !isDrifting) inspectState.textContent = 'BORN_IN_BOUNDARY';
    } else if (p <= 2 / 7) {
      // Stage 2: Code lines wrap on faces, travels through boundary opening
      const a = (p - 1 / 7) / (1 / 7);
      courierPos = p1.clone().lerp(p2, a);
      courierScale = 0.8 + a * 0.2;
      courierColor = 0xb8f070;
      if (inspectState && !isDrifting) inspectState.textContent = 'CODE_WRAPPED_PORTAL';

      // Rogue shards deflect off boundary portal
      this.rogueShards.forEach((shard, i) => {
        const bounce = Math.sin(t * 4 + i) * 20;
        shard.position.x = shard.userData.basePos.x - bounce;
      });
    } else if (p <= 3 / 7) {
      // Stage 3: Stops at sealed vault collar; tight, tense camera; vault locks
      const a = (p - 2 / 7) / (1 / 7);
      courierPos = p2.clone().lerp(p3, a);
      courierScale = 1.0;
      courierColor = 0xd8ff64; // tensed
      if (inspectState && !isDrifting) inspectState.textContent = 'TENSED_AT_VAULT';

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
      if (inspectState && !isDrifting) inspectState.textContent = 'AST_SCANNING';

      // Sweep scan blade across courier
      this.scanBlade.position.x = -25 + a * 50;

      // Light up AST branch nodes sequentially
      this.astBranchNodes.forEach((node, i) => {
        const threshold = i / this.astBranchNodes.length;
        const lit = a >= threshold;
        node.material.opacity = lit ? 0.95 : 0.15;
        if (i === 1 && node.material.color) node.material.color.setHex(a < 0.55 ? 0xff4747 : 0xd8ff64);
      });
      if (this.astMissing) { this.astMissing.visible = a < 0.55; this.astFound.visible = a >= 0.55; }
    } else if (p <= 5 / 7) {
      // Stage 5: Clone travels down conduit into quarantine space, source stays sealed
      const a = (p - 4 / 7) / (1 / 7);
      // Courier follows conduit curve
      courierPos = this.conduitCurve.getPointAt(Math.min(1, Math.max(0, a)));
      courierScale = 1.0;
      courierColor = 0x8fffa8;
      if (inspectState && !isDrifting) inspectState.textContent = 'CONDUIT_DESCENT';

      // Source tree platform stays sealed and dimmed
      this.sourceTree.position.y = 60 + Math.sin(t * 0.8) * 1.5;
      this.podMesh.rotation.y = t * 0.3;
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
        if (inspectState && !isDrifting) inspectState.textContent = 'ATTEMPT_1_RUNNING';
      } else if (a < 0.62) {
        // Flinch, crack, red flash, recoil along retry arc
        const subA = (a - 0.42) / 0.2;
        courierColor = 0xff4747; // RED ON REJECT
        this.crackMat.opacity = 0.9;
        this.retryArcMat.opacity = 0.8;
        flinchOffset.set(
          -Math.sin(subA * Math.PI) * 28,
          Math.sin(subA * Math.PI) * 18,
          Math.sin(subA * Math.PI) * 12,
        );
        this.courier.rotation.z = Math.sin(subA * Math.PI) * 0.45;
        courierPos = p6a.clone().add(flinchOffset);
        if (inspectState && !isDrifting) inspectState.textContent = 'GATE_2_FLINCH_RETRY';
      } else {
        // Retry cleaner: gather composure, brighter, steady green, pass all four gates
        const subA = (a - 0.62) / 0.38;
        courierPos = p6a.clone().lerp(p6b, subA);
        courierColor = 0xd8ff64; // STEADY EMERALD PHOSPHOR
        this.crackMat.opacity = Math.max(0, 0.9 - subA * 2.5);
        this.retryArcMat.opacity = Math.max(0, 0.8 - subA * 2);
        this.courier.rotation.z = 0;
        if (inspectState && !isDrifting) inspectState.textContent = 'RETRY_ALL_GATES_PASS';
      }

      // Gate lights
      this.arenaGates.forEach((gate, i) => {
        const gateThresh = 0.62 + (i / 4) * 0.36;
        const pass = a >= gateThresh;
        gate.lamp.material.color.setHex(pass ? 0xd8ff64 : (a > 0.42 && a < 0.62 && i === 1 ? 0xff4747 : 0x243329));
        gate.curtain.material.opacity = pass ? 0.35 : 0.08;
      });
    } else {
      // Stage 7: Verified courier travels back up conduit, dissolves into solution.py in file tree
      const a = (p - 6 / 7) / (1 / 7);
      if (a < 0.5) {
        // Ascending back up the conduit
        const subA = 1.0 - a * 2.0;
        courierPos = this.conduitCurve.getPointAt(Math.min(1, Math.max(0, subA)));
        courierScale = 1.0;
      } else {
        // Docking and dissolving into solution.py
        const subA = (a - 0.5) / 0.5;
        courierPos = p5a.clone().lerp(p7, subA);
        // Dissolves into file slot
        courierScale = Math.max(0.01, 1.0 - subA * 0.55);
        if (subA > 0.9) {
          audio.playDock();
        }
      }
      courierColor = 0xd8ff64;
      if (inspectState && !isDrifting) inspectState.textContent = 'VERIFIED_DOCKED';

      // Quarantined space retracts and dims
      this.quarantinePod.position.y = -110 - a * 40;
      this.podMesh.material.opacity = Math.max(0.1, 0.7 - a * 0.6);
      const land = a < 0.5 ? 0 : Math.min(1, (a - 0.62) / 0.2);
      this.slotBar.material.opacity = Math.max(0, land);
      this.receiptMesh.material.opacity = Math.max(0, Math.min(1, (a - 0.72) / 0.12));
      this.reportMesh.material.opacity = Math.max(0, Math.min(1, (a - 0.84) / 0.12));
    }

    // Apply color and breathing to Courier
    this.courierCoreMat.color.setHex(isDrifting ? 0xff4747 : courierColor);
    this.courierWireMat.color.setHex(isDrifting ? 0xff4747 : courierColor);

    this.courier.position.copy(courierPos);
    const boost = 1 + 0.75 * Math.max(0, 1 - Math.abs(p * 7 - 1.5) / 1.0);
    this.courier.scale.setScalar(courierScale * breathing * 2.2 * boost);
    if (this.courierLight) {
      this.courierLight.position.set(courierPos.x, courierPos.y + 40, courierPos.z + 90);
      this.courierLight.color.setHex(isDrifting ? 0xff4747 : courierColor);
    }
    if (this.trail) {
      const last = this.trailPts[this.trailPts.length - 1];
      if (!last || last.distanceTo(courierPos) > 2.5) {
        this.trailPts.push(courierPos.clone());
        if (this.trailPts.length > this.trailN) this.trailPts.shift();
      }
      const arr = this.trailGeo.attributes.position.array;
      for (let i = 0; i < this.trailN; i++) {
        const pt = this.trailPts[Math.min(i, this.trailPts.length - 1)] || courierPos;
        arr[i*3] = pt.x; arr[i*3+1] = pt.y; arr[i*3+2] = pt.z;
      }
      this.trailGeo.attributes.position.needsUpdate = true;
      this.trail.material.color.setHex(isDrifting ? 0xff4747 : courierColor);
    }

    // Orbiting Glyphs motion around Courier
    this.glyphSprites.forEach((item) => {
      item.angle += deltaTime * 1.8;
      item.sprite.position.set(
        Math.cos(item.angle) * item.radius,
        Math.sin(item.angle * 1.5) * 8,
        Math.sin(item.angle) * item.radius,
      );
    });

    // Inactive object fading: smoothly adjust opacity of stages away from current progress
    const activeStage = p * 7;
    this.boundaryCage.traverse((obj) => {
      if (obj.material && obj !== this.courier) {
        obj.visible = activeStage < 2.3;
      }
    });
    this.vaultCollar.traverse((obj) => {
      if (obj.material) obj.visible = activeStage > 1.6 && activeStage < 3.6;
    });
    this.astZone.traverse((obj) => {
      if (obj.material) obj.visible = activeStage > 2.6 && activeStage < 4.6;
    });
    this.boundaryZone.traverse((obj) => { if (obj.material) obj.visible = activeStage > 0.9 && activeStage < 3.3; });
    this.dualSpace.traverse((obj) => { if (obj.material) obj.visible = activeStage > 3.75 && activeStage < 6.2; });
    this.masterDock.traverse((obj) => { if (obj.material) obj.visible = activeStage > 5.6; });
    this.gateArena.traverse((obj) => {
      if (obj.material) obj.visible = activeStage > 4.7;
    });
  }

  render(elapsed, deltaTime) {
    if (isReduced) return;

    // Auto-downgrade performance check
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
  scene.setProgress(storyTrigger?.scrollTrigger?.progress ?? 0);
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
      scrub: 0.5,
      invalidateOnRefresh: true,
      onUpdate: (self) => update(self.progress),
      onRefresh: (self) => update(self.progress),
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
}, { once: true });

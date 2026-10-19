import * as THREE from './vendor/three.module.min.js';

const { gsap, ScrollTrigger } = window;
const Lenis = window.Lenis;

document.body.classList.add('story-module-loaded');
gsap.registerPlugin(ScrollTrigger);

/* ------------------------------------------------------------------ *
 * Global Selectors & UI Elements
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
const inspectSymbol = document.querySelector('#inspect-symbol');
const inspectSector = document.querySelector('#inspect-sector');
const inspectIntegrity = document.querySelector('#inspect-integrity');

const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');

/* Low-quality tier: phones, coarse pointers and weak devices (or ?quality=low) */
const LOW_QUALITY = (() => {
  const q = new URLSearchParams(window.location.search).get('quality');
  if (q === 'low') return true;
  if (q === 'high') return false;
  const coarse = window.matchMedia('(pointer: coarse)').matches;
  const narrow = Math.min(window.innerWidth, window.innerHeight) < 700;
  const weak = (navigator.deviceMemory && navigator.deviceMemory <= 4) ||
    (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4);
  return coarse || narrow || !!weak;
})();
let isReduced = reduced.matches;

let scene = null;
let storyTrigger = null;
let lenis = null;
let lastStep = -1;
let scrollVelocity = 0;

const CHAMBERS = [
  'CHAMBER 01 / CONTRACT MONOLITH',
  'CHAMBER 02 / BOUNDARY DEFLECTOR SHIELD',
  'CHAMBER 03 / SHA-256 GIMBAL LASER COLLAR',
  'CHAMBER 04 / AST CONTRACT INSPECTION CORES',
  'CHAMBER 05 / ISOLATED GIT WORKTREE REACTOR',
  'CHAMBER 06 / QUAD-GATE SUITE & HEALING ARC',
  'CHAMBER 07 / MASTER REPO DOCK & AUDIT TRAIL',
];

/* ------------------------------------------------------------------ *
 * Procedural Web Audio Synthesizer (Zero External Audio Assets)
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
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start(now);
    osc.stop(now + 0.36);
  }

  playAlarm() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(220, now);
    osc.frequency.linearRampToValueAtTime(180, now + 0.3);
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
    osc.frequency.setValueAtTime(120, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.25);
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
 * UI & Step Synchronization
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
  if (chamberReadout) chamberReadout.textContent = CHAMBERS[safeStep];
  if (staticVisual) staticVisual.dataset.step = String(safeStep);

  panels.forEach((panel, index) => {
    const active = index === safeStep;
    panel.classList.toggle('is-current', active);
    panel.setAttribute('aria-hidden', String(!active));
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

// Interactive rail jumps
railItems.forEach((item, index) => {
  const btn = item.querySelector('button');
  btn?.addEventListener('click', () => {
    if (lenis && story) {
      const targetScroll = story.offsetTop + (index / 6) * (story.offsetHeight - window.innerHeight);
      lenis.scrollTo(targetScroll, { duration: 1.2 });
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

  if (inspectIntegrity) {
    inspectIntegrity.textContent = 'DRIFT COMPROMISED (MISMATCH)';
    inspectIntegrity.style.color = '#ff4747';
  }

  scene.triggerDriftAlert();

  setTimeout(() => {
    if (breachTitle) breachTitle.textContent = 'CD-AVC REJECTION PROTOCOL COMPLETE';
    if (breachDetail) breachDetail.textContent = 'Untrusted patch ejected. Original test and implementation restored. Zero repository residue.';
  }, 1600);

  setTimeout(() => {
    breachBanner?.classList.remove('is-active');
    btnDrift?.classList.remove('is-breached');
    isDrifting = false;
    scene.resetDriftAlert();
    if (inspectIntegrity) {
      inspectIntegrity.textContent = 'PRE-SEALED (0 BYTES DRIFT)';
      inspectIntegrity.style.color = '#d8ff64';
    }
    setTimeout(() => {
      if (breachTitle) breachTitle.textContent = 'SECURITY BREACH DETECTED: TEST DRIFT SIMULATED';
      if (breachDetail) breachDetail.textContent = 'Locked SHA-256 mismatch detected in test suite. CD-AVC isolation protocol active. Candidate write refused.';
    }, 500);
  }, 3800);
}

btnDrift?.addEventListener('click', triggerDriftSimulation);

/* ------------------------------------------------------------------ *
 * Procedural Dynamic Canvas Textures
 * ------------------------------------------------------------------ */
function createTexture(width, height, draw) {
  const canvasElement = document.createElement('canvas');
  canvasElement.width = width;
  canvasElement.height = height;
  const ctx = canvasElement.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  draw(ctx, width, height);
  const texture = new THREE.CanvasTexture(canvasElement);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function contractTexture() {
  return createTexture(1024, 480, (ctx, width, height) => {
    ctx.fillStyle = 'rgba(6, 10, 8, 0.95)';
    roundRect(ctx, 4, 4, width - 8, height - 8, 16);
    ctx.fill();
    ctx.strokeStyle = 'rgba(216, 255, 100, 0.35)';
    ctx.lineWidth = 2.5;
    roundRect(ctx, 4, 4, width - 8, height - 8, 16);
    ctx.stroke();

    // Laser bar
    ctx.fillStyle = '#d8ff64';
    ctx.fillRect(36, 32, 6, height - 64);

    ctx.font = '700 24px monospace';
    ctx.fillStyle = '#d8ff64';
    ctx.fillText('TASK SPECIFICATION CONTRACT', 64, 68);

    ctx.textAlign = 'right';
    ctx.fillStyle = '#7a8c80';
    ctx.font = '500 20px monospace';
    ctx.fillText('IMMUTABLE SCOPE', width - 44, 68);
    ctx.textAlign = 'left';

    ctx.fillStyle = '#f4f7f4';
    ctx.font = '700 52px system-ui, sans-serif';
    ctx.fillText('task_001 :: count_vowels', 64, 142);

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.18)';
    ctx.beginPath();
    ctx.moveTo(64, 175);
    ctx.lineTo(width - 44, 175);
    ctx.stroke();

    const items = [
      ['TARGET IMPLEMENTATION', 'solution.py'],
      ['REQUIRED EXPORTED SYMBOL', 'FunctionDef: count_vowels'],
      ['TEST INTEGRITY CONSTRAINT', 'SHA-256 pre-hash == post-hash'],
      ['ISOLATION ENVIRONMENT', 'Ephemeral git worktree'],
      ['MAX ATTEMPT BUDGET', '2 retries before hard rejection'],
    ];

    items.forEach(([lbl, val], idx) => {
      const y = 224 + idx * 46;
      ctx.fillStyle = '#839689';
      ctx.font = '600 20px monospace';
      ctx.fillText(lbl, 64, y);
      ctx.fillStyle = '#d8ff64';
      ctx.font = '600 22px monospace';
      ctx.fillText(val, 420, y);
    });
  });
}

function receiptLogTexture() {
  return createTexture(768, 960, (ctx, width, height) => {
    ctx.fillStyle = 'rgba(7, 12, 9, 0.96)';
    roundRect(ctx, 4, 4, width - 8, height - 8, 16);
    ctx.fill();
    ctx.strokeStyle = 'rgba(216, 255, 100, 0.35)';
    ctx.lineWidth = 2;
    roundRect(ctx, 4, 4, width - 8, height - 8, 16);
    ctx.stroke();

    ctx.fillStyle = '#d8ff64';
    ctx.fillRect(32, 28, 5, height - 56);

    ctx.font = '700 22px monospace';
    ctx.fillStyle = '#d8ff64';
    ctx.fillText('EXECUTION RECEIPT', 56, 62);

    ctx.fillStyle = '#f4f7f4';
    ctx.font = '700 36px monospace';
    ctx.fillText('execution_log.json', 56, 116);

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.16)';
    ctx.beginPath();
    ctx.moveTo(56, 142);
    ctx.lineTo(width - 44, 142);
    ctx.stroke();

    const lines = [
      '// Deterministic Run Evidence',
      '{',
      '  "task_id": "task_001_count_vowels",',
      '  "timestamp": "2026-10-20T01:28:10Z",',
      '  "pre_test_hash": "9c1f4e82b2e7d581...",',
      '  "post_test_hash": "9c1f4e82b2e7d581...",',
      '  "hash_drift_bits": 0,',
      '  "ast_contract": {',
      '    "parsed": true,',
      '    "symbols_found": ["count_vowels"]',
      '  },',
      '  "worktree_exit_code": 0,',
      '  "gates": {',
      '    "gate_1_sha256": "VERIFIED_PASS",',
      '    "gate_2_ast": "VERIFIED_PASS",',
      '    "gate_3_targeted": "PASS (4/4)",',
      '    "gate_4_regression": "PASS (12/12)"',
      '  },',
      '  "verified_copy_back": ["solution.py"]',
      '}',
    ];

    lines.forEach((line, i) => {
      const y = 180 + i * 36;
      ctx.fillStyle = line.includes('PASS') || line.includes('true') || line.includes('solution.py') ? '#d8ff64' : '#b2c0b6';
      ctx.font = '400 20px monospace';
      ctx.fillText(line, 56, y);
    });
  });
}

function statusPlateTexture({ title, code, detail, color = '#d8ff64' }) {
  return createTexture(512, 190, (ctx, width, height) => {
    ctx.fillStyle = 'rgba(6, 10, 8, 0.94)';
    roundRect(ctx, 3, 3, width - 6, height - 6, 10);
    ctx.fill();
    ctx.strokeStyle = color === '#ff4747' ? 'rgba(255, 71, 71, 0.5)' : 'rgba(216, 255, 100, 0.3)';
    ctx.lineWidth = 2;
    roundRect(ctx, 3, 3, width - 6, height - 6, 10);
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.fillRect(20, 20, 4, height - 40);

    ctx.font = '700 18px monospace';
    ctx.fillStyle = color;
    ctx.fillText(title.toUpperCase(), 38, 48);

    ctx.fillStyle = '#f4f7f4';
    ctx.font = '700 32px monospace';
    ctx.fillText(code, 38, 100);

    ctx.fillStyle = '#8f9f94';
    ctx.font = '500 18px system-ui, sans-serif';
    ctx.fillText(detail, 38, 144);
  });
}

function gridFloorTexture() {
  return createTexture(2048, 2048, (ctx, width, height) => {
    ctx.strokeStyle = 'rgba(150, 180, 160, 0.12)';
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

    ctx.strokeStyle = 'rgba(216, 255, 100, 0.22)';
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
    const fade = ctx.createRadialGradient(width / 2, height / 2, width * 0.05, width / 2, height / 2, width * 0.52);
    fade.addColorStop(0, 'rgba(0,0,0,1)');
    fade.addColorStop(0.65, 'rgba(0,0,0,0.6)');
    fade.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = fade;
    ctx.fillRect(0, 0, width, height);
  });
}

/* ------------------------------------------------------------------ *
 * Three.js 3D Spatial Pipeline & Post-Processing Engine
 * ------------------------------------------------------------------ */
class TaskScene {
  constructor(targetCanvas) {
    this.canvas = targetCanvas;
    this.width = targetCanvas.clientWidth || window.innerWidth;
    this.height = targetCanvas.clientHeight || window.innerHeight;

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(LOW_QUALITY ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(this.width, this.height, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x060908, 0.00065);

    this.camera = new THREE.PerspectiveCamera(34, this.width / Math.max(1, this.height), 1, 5000);
    this.clock = new THREE.Clock();
    this.time = 0;
    this.progress = 0;
    this.running = false;
    this.alertIntensity = 0;

    // Pointer Parallax & Raycasting
    this.pointer = new THREE.Vector2(0, 0);
    this.pointerTarget = new THREE.Vector2(0, 0);
    this.raycaster = new THREE.Raycaster();
    this.interactiveObjects = [];

    this.buildProceduralEnvironment();
    this.buildLighting();
    this.buildSplinePath();
    this.buildSceneWorld();
    this.setupPostProcessing();
    this.setupPointerEvents();
  }

  buildProceduralEnvironment() {
    try {
      const pmrem = new THREE.PMREMGenerator(this.renderer);
      pmrem.compileEquirectangularShader();

      const envScene = new THREE.Scene();
      // Emissive studio softboxes to create metallic sheens and crystal refractions
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
      console.warn('Procedural PMREM environment generation bypassed:', e);
    }
  }

  buildLighting() {
    this.scene.add(new THREE.HemisphereLight(0xd4e4da, 0x060908, 0.9));

    const mainKey = new THREE.DirectionalLight(0xffffff, 2.5);
    mainKey.position.set(-300, 500, 600);
    this.scene.add(mainKey);

    const rimLight = new THREE.DirectionalLight(0xd8ff64, 2.0);
    rimLight.position.set(600, 300, -400);
    this.scene.add(rimLight);

    const cyanRim = new THREE.DirectionalLight(0x5ef3d2, 1.2);
    cyanRim.position.set(-500, -100, 400);
    this.scene.add(cyanRim);
  }

  buildSplinePath() {
    // 7 Spatial Waypoints through the 3D pipeline
    const cameraWaypoints = [
      new THREE.Vector3(-460, 260, 640),  // 01: Contract Vault
      new THREE.Vector3(-260, 160, 520),  // 02: Boundary Deflector
      new THREE.Vector3(-80, 80, 440),    // 03: SHA-256 Laser Collar
      new THREE.Vector3(70, 35, 260),     // 04: AST Core Macro
      new THREE.Vector3(260, -90, 480),   // 05: Worktree Reactor Pod
      new THREE.Vector3(480, -30, 580),   // 06: Test Suite Pylons
      new THREE.Vector3(760, 120, 540),   // 07: Master Working Tree Dock
    ];

    const lookWaypoints = [
      new THREE.Vector3(-460, 200, 0),
      new THREE.Vector3(-250, 130, 0),
      new THREE.Vector3(-80, 50, 0),
      new THREE.Vector3(75, 25, 0),
      new THREE.Vector3(260, -110, 0),
      new THREE.Vector3(490, -20, 0),
      new THREE.Vector3(780, 70, 0),
    ];

    this.cameraSpline = new THREE.CatmullRomCurve3(cameraWaypoints, false, 'centripetal', 0.5);
    this.lookSpline = new THREE.CatmullRomCurve3(lookWaypoints, false, 'centripetal', 0.5);
  }

  buildSceneWorld() {
    this.world = new THREE.Group();
    this.scene.add(this.world);

    // Floor Plane
    const floorGeo = new THREE.PlaneGeometry(4800, 4800);
    const floorMat = new THREE.MeshBasicMaterial({
      map: gridFloorTexture(),
      transparent: true,
      depthWrite: false,
      opacity: 0.8,
    });
    this.floor = new THREE.Mesh(floorGeo, floorMat);
    this.floor.rotation.x = -Math.PI / 2;
    this.floor.position.y = -220;
    this.world.add(this.floor);

    // Pipeline Atmospheric Particles
    const dustCount = 350;
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

    // 1. The Obsidian-Titanium Containment Vault Monolith (Step 01)
    this.buildVaultMonolith();

    // 2. The Glowing Polyhedral AST Crystal (The Hero Object: solution.py)
    this.buildASTCrystal();

    // 3. Boundary Deflector Shield & Rogue Shards (Step 02)
    this.buildBoundaryShield();

    // 4. Triple Gimbal SHA-256 Laser Scanning Rings (Step 03)
    this.buildGimbalRings();

    // 5. AST Inspection Cores & Symbol Target (Step 04)
    this.buildASTInspectionZone();

    // 6. Subterranean Git Worktree Reactor Pod (Step 05)
    this.buildWorktreePod();

    // 7. Quad-Gate Test Suite & Healing Arc (Step 06)
    this.buildTestSuiteGates();

    // 8. Master Repository Docking Vault & Evidence Log (Step 07)
    this.buildMasterRepoDock();
  }

  buildVaultMonolith() {
    const monolithGroup = new THREE.Group();
    monolithGroup.position.set(-460, 220, 0);

    const titaniumMat = new THREE.MeshStandardMaterial({
      color: 0x0d1511,
      roughness: 0.25,
      metalness: 0.85,
    });

    // Outer Chassis Pylons
    [-1, 1].forEach((dir) => {
      const pylon = new THREE.Mesh(new THREE.BoxGeometry(24, 280, 48), titaniumMat);
      pylon.position.set(dir * 140, 0, 0);
      monolithGroup.add(pylon);

      const claw = new THREE.Mesh(
        new THREE.BoxGeometry(40, 16, 28),
        new THREE.MeshStandardMaterial({ color: 0x1a261f, roughness: 0.3, metalness: 0.7 }),
      );
      claw.position.set(dir * 115, 0, 16);
      monolithGroup.add(claw);
    });

    // Contract Holographic Screen
    const contractGeo = new THREE.PlaneGeometry(320, 150);
    const contractMat = new THREE.MeshBasicMaterial({
      map: contractTexture(),
      transparent: true,
      side: THREE.DoubleSide,
    });
    this.contractScreen = new THREE.Mesh(contractGeo, contractMat);
    this.contractScreen.position.set(0, 140, 20);
    monolithGroup.add(this.contractScreen);

    // Status beacon
    const beacon = new THREE.Mesh(
      new THREE.SphereGeometry(6, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xd8ff64 }),
    );
    beacon.position.set(0, 160, 28);
    monolithGroup.add(beacon);

    this.world.add(monolithGroup);
    this.vaultMonolith = monolithGroup;
  }

  buildASTCrystal() {
    this.crystalGroup = new THREE.Group();
    this.crystalGroup.position.set(-460, 200, 0);

    // Outer Glass Refractive Shell (MeshPhysicalMaterial with high transmission)
    const shellGeo = new THREE.IcosahedronGeometry(58, 1);
    this.crystalShellMat = LOW_QUALITY
      ? new THREE.MeshStandardMaterial({
        color: 0x122a1e,
        emissive: 0x0d3822,
        emissiveIntensity: 0.4,
        roughness: 0.2,
        metalness: 0.3,
        transparent: true,
        opacity: 0.55,
      })
      : new THREE.MeshPhysicalMaterial({
      color: 0x122a1e,
      emissive: 0x0d3822,
      emissiveIntensity: 0.28,
      roughness: 0.08,
      metalness: 0.12,
      transmission: 0.94,
      ior: 1.54,
      thickness: 2.6,
      specularIntensity: 1.0,
      specularColor: 0xd8ff64,
      transparent: true,
      opacity: 0.96,
    });

    this.crystalMesh = new THREE.Mesh(shellGeo, this.crystalShellMat);
    this.crystalMesh.userData = {
      type: 'crystal',
      name: 'AST_POLYHEDRON',
      file: 'solution.py',
      symbols: 'count_vowels(text)',
      sector: 'ZERO_TRUST_CONTAINMENT_VAULT',
      integrity: 'PRE-SEALED (0 BYTES DRIFT)',
    };
    this.interactiveObjects.push(this.crystalMesh);
    this.crystalGroup.add(this.crystalMesh);

    // Wireframe Cage Rim
    const wireMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.45 });
    const wireMesh = new THREE.LineSegments(new THREE.WireframeGeometry(shellGeo), wireMat);
    this.crystalGroup.add(wireMesh);

    // Internal 3D Abstract Syntax Tree (AST) Nodes & Vector Links
    this.astNodesGroup = new THREE.Group();
    const nodeCoords = [
      { name: 'Module (task_001)', pos: [0, 28, 0], color: 0x5ef3d2, size: 6.5 },
      { name: 'FunctionDef: count_vowels', pos: [0, 6, 0], color: 0xd8ff64, size: 9 }, // Target symbol!
      { name: 'arg: text', pos: [-20, -12, 10], color: 0x8fffa8, size: 5 },
      { name: 'For: ch in text', pos: [18, -14, -8], color: 0x8fffa8, size: 5 },
      { name: 'If: ch in "aeiou"', pos: [0, -28, 14], color: 0xffd864, size: 5.5 },
      { name: 'Return: total', pos: [0, -36, -10], color: 0x5ef3d2, size: 6 },
    ];

    this.astNodeMeshes = [];
    nodeCoords.forEach((node) => {
      const nMesh = new THREE.Mesh(
        new THREE.SphereGeometry(node.size, 16, 16),
        new THREE.MeshBasicMaterial({ color: node.color }),
      );
      nMesh.position.set(...node.pos);
      nMesh.userData = {
        type: 'ast_node',
        name: node.name,
        file: 'solution.py',
        symbols: node.name,
        sector: 'AST_SYNTAX_LATTICE',
        integrity: 'SYNTACTICALLY_VALID',
      };
      this.interactiveObjects.push(nMesh);
      this.astNodesGroup.add(nMesh);
      this.astNodeMeshes.push(nMesh);
    });

    // Links between AST nodes
    const linksGeo = new THREE.BufferGeometry();
    const linkPositions = [];
    // Module -> FunctionDef
    linkPositions.push(0, 28, 0, 0, 6, 0);
    // FunctionDef -> arg & For
    linkPositions.push(0, 6, 0, -20, -12, 10);
    linkPositions.push(0, 6, 0, 18, -14, -8);
    // For -> If
    linkPositions.push(18, -14, -8, 0, -28, 14);
    // If -> Return
    linkPositions.push(0, -28, 14, 0, -36, -10);

    linksGeo.setAttribute('position', new THREE.Float32BufferAttribute(linkPositions, 3));
    const linksMat = new THREE.LineBasicMaterial({ color: 0xd8ff64, transparent: true, opacity: 0.6 });
    this.astLinks = new THREE.LineSegments(linksGeo, linksMat);
    this.astNodesGroup.add(this.astLinks);

    this.crystalGroup.add(this.astNodesGroup);
    this.world.add(this.crystalGroup);
  }

  buildBoundaryShield() {
    this.shieldGroup = new THREE.Group();
    this.shieldGroup.position.set(-250, 130, 0);

    // Hexagonal Boundary Barrier Mesh
    const shieldGeo = new THREE.CircleGeometry(110, 6);
    this.shieldMat = new THREE.MeshBasicMaterial({
      color: 0x5ef3d2,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
      side: THREE.DoubleSide,
    });
    this.shieldMesh = new THREE.Mesh(shieldGeo, this.shieldMat);
    this.shieldGroup.add(this.shieldMesh);

    // Outer Barrier Ring
    const ringGeo = new THREE.RingGeometry(105, 115, 6);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64, side: THREE.DoubleSide });
    this.shieldRing = new THREE.Mesh(ringGeo, ringMat);
    this.shieldGroup.add(this.shieldRing);

    // Rogue File Shards (Unauthorized incoming attempts deflecting off the boundary)
    this.rogueShards = [];
    const shardNames = ['test_tamper.py', 'evil_exec.sh', 'override.config', 'leak.patch'];
    for (let i = 0; i < 4; i++) {
      const shardGeo = new THREE.TetrahedronGeometry(18, 0);
      const shardMat = new THREE.MeshStandardMaterial({
        color: 0x1f0b0b,
        emissive: 0xff3b30,
        emissiveIntensity: 0.4,
        roughness: 0.3,
      });
      const shard = new THREE.Mesh(shardGeo, shardMat);
      shard.position.set(-230 + (i % 2 === 0 ? -60 : 60), 110 + i * 28, 40 + i * 15);
      shard.userData = {
        name: shardNames[i],
        deflected: false,
      };
      this.shieldGroup.add(shard);
      this.rogueShards.push(shard);
    }

    this.world.add(this.shieldGroup);
  }

  buildGimbalRings() {
    this.gimbalGroup = new THREE.Group();
    this.gimbalGroup.position.set(-80, 50, 0);

    const metalMat = new THREE.MeshStandardMaterial({
      color: 0x15221b,
      roughness: 0.22,
      metalness: 0.9,
    });

    // 3 Concentric Gimbal Laser Rings
    this.ringOuter = new THREE.Mesh(new THREE.TorusGeometry(125, 4, 16, 64), metalMat);
    this.ringMid = new THREE.Mesh(new THREE.TorusGeometry(100, 3.5, 16, 64), metalMat);
    this.ringInner = new THREE.Mesh(
      new THREE.TorusGeometry(75, 3, 16, 64),
      new THREE.MeshStandardMaterial({ color: 0xd8ff64, emissive: 0xd8ff64, emissiveIntensity: 0.4 }),
    );

    this.ringOuter.userData = {
      type: 'sensor',
      name: 'GIMBAL_SHA256_RING_OUTER',
      sector: 'GATE_01_TEST_SEAL',
      integrity: 'SYNCHRONIZED',
    };
    this.interactiveObjects.push(this.ringOuter);

    this.gimbalGroup.add(this.ringOuter);
    this.gimbalGroup.add(this.ringMid);
    this.gimbalGroup.add(this.ringInner);

    // Crossfire Laser Scanner Beams
    const laserMat = new THREE.LineBasicMaterial({
      color: 0xd8ff64,
      transparent: true,
      opacity: 0.85,
    });
    this.laserMat = laserMat;

    const laserLines = new THREE.BufferGeometry();
    const lPos = [
      -120, 0, 0, 120, 0, 0,
      0, -120, 0, 0, 120, 0,
      0, 0, -120, 0, 0, 120,
    ];
    laserLines.setAttribute('position', new THREE.Float32BufferAttribute(lPos, 3));
    this.lasers = new THREE.LineSegments(laserLines, laserMat);
    this.gimbalGroup.add(this.lasers);

    // Holographic SHA-256 Plate
    this.shaPlate = new THREE.Mesh(
      new THREE.PlaneGeometry(240, 80),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'GATE 01 · LOCKED TESTS', code: '9c1f…b2e7', detail: 'sha-256 before == after' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    this.shaPlate.position.set(0, 140, 0);
    this.gimbalGroup.add(this.shaPlate);

    this.world.add(this.gimbalGroup);
  }

  buildASTInspectionZone() {
    this.astZone = new THREE.Group();
    this.astZone.position.set(75, 25, 0);

    // Optical Inspection Aperture
    const apertureRing = new THREE.Mesh(
      new THREE.RingGeometry(85, 95, 32),
      new THREE.MeshBasicMaterial({ color: 0x5ef3d2, side: THREE.DoubleSide }),
    );
    this.astZone.add(apertureRing);

    // AST Contract Status Plate
    this.astPlate = new THREE.Mesh(
      new THREE.PlaneGeometry(240, 80),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'GATE 02 · AST CONTRACT', code: 'count_vowels', detail: 'syntax valid · symbol present' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    this.astPlate.position.set(0, 125, 0);
    this.astZone.add(this.astPlate);

    this.world.add(this.astZone);
  }

  buildWorktreePod() {
    this.podGroup = new THREE.Group();
    this.podGroup.position.set(260, -110, 0);

    // Heavy Octagonal Subterranean Reactor Pod Shell
    const podShellGeo = new THREE.CylinderGeometry(150, 150, 240, 8, 1, true);
    const podShellMat = new THREE.MeshStandardMaterial({
      color: 0x090f0c,
      roughness: 0.35,
      metalness: 0.75,
      wireframe: true,
    });
    this.podShell = new THREE.Mesh(podShellGeo, podShellMat);
    this.podShell.userData = {
      type: 'pod',
      name: 'GIT_WORKTREE_REACTOR',
      sector: 'EPHEMERAL_ISOLATION_CELL',
      integrity: 'ISOLATED /tmp/cdavc-worktree-001',
    };
    this.interactiveObjects.push(this.podShell);
    this.podGroup.add(this.podShell);

    // Magnetic Confinement Rings
    [-90, 0, 90].forEach((y) => {
      const coil = new THREE.Mesh(
        new THREE.TorusGeometry(152, 3, 8, 32),
        new THREE.MeshBasicMaterial({ color: 0xd8ff64 }),
      );
      coil.rotation.x = Math.PI / 2;
      coil.position.y = y;
      this.podGroup.add(coil);
    });

    // Worktree Holographic Plate
    this.podPlate = new THREE.Mesh(
      new THREE.PlaneGeometry(260, 85),
      new THREE.MeshBasicMaterial({
        map: statusPlateTexture({ title: 'ISOLATION CELL', code: 'git worktree', detail: 'source tree untouched · disposable' }),
        transparent: true,
        side: THREE.DoubleSide,
      }),
    );
    this.podPlate.position.set(0, 160, 0);
    this.podGroup.add(this.podPlate);

    // Quarantined Ejection Tray for failed Attempt 1
    const trayGeo = new THREE.BoxGeometry(110, 12, 90);
    const trayMat = new THREE.MeshStandardMaterial({ color: 0x22120e, roughness: 0.6 });
    this.ejectTray = new THREE.Mesh(trayGeo, trayMat);
    this.ejectTray.position.set(0, -100, 120);
    this.podGroup.add(this.ejectTray);

    this.world.add(this.podGroup);
  }

  buildTestSuiteGates() {
    this.gatesGroup = new THREE.Group();
    this.gatesGroup.position.set(490, -20, 0);

    const gateTitles = [
      { t: 'GATE 03A', n: 'TARGETED', c: '4/4 pass' },
      { t: 'GATE 03B', n: 'HIDDEN', c: 'assertions ok' },
      { t: 'GATE 03C', n: 'NEGATIVE', c: 'invariants safe' },
      { t: 'GATE 04', n: 'REGRESSION', c: '12/12 pass' },
    ];

    this.gatePylons = [];
    gateTitles.forEach((g, idx) => {
      const pylonGroup = new THREE.Group();
      pylonGroup.position.set(-120 + idx * 80, 0, 0);

      // Vertical Gate Arch
      const arch = new THREE.Mesh(
        new THREE.BoxGeometry(10, 180, 14),
        new THREE.MeshStandardMaterial({ color: 0x111c16, roughness: 0.3, metalness: 0.8 }),
      );
      pylonGroup.add(arch);

      // Gate Laser Curtains
      const curtain = new THREE.Mesh(
        new THREE.PlaneGeometry(60, 160),
        new THREE.MeshBasicMaterial({
          color: 0xd8ff64,
          transparent: true,
          opacity: 0.15,
          side: THREE.DoubleSide,
        }),
      );
      curtain.position.set(30, 0, 0);
      pylonGroup.add(curtain);

      // Indicator Lamp
      const lamp = new THREE.Mesh(
        new THREE.SphereGeometry(6, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x243329 }),
      );
      lamp.position.set(0, 95, 0);
      pylonGroup.add(lamp);

      this.gatePylons.push({ pylonGroup, lamp, curtain });
      this.gatesGroup.add(pylonGroup);
    });

    this.world.add(this.gatesGroup);
  }

  buildMasterRepoDock() {
    this.dockGroup = new THREE.Group();
    this.dockGroup.position.set(780, 70, 0);

    // Master Working Tree Vault Frame
    const frameGeo = new THREE.BoxGeometry(220, 240, 180);
    const frameMat = new THREE.MeshStandardMaterial({
      color: 0x09110d,
      roughness: 0.2,
      metalness: 0.9,
    });
    this.dockFrame = new THREE.Mesh(frameGeo, frameMat);
    this.dockGroup.add(this.dockFrame);

    // Crystal Dock Receptacle Socket
    const socketGeo = new THREE.BoxGeometry(100, 100, 4);
    const socketMat = new THREE.MeshBasicMaterial({ color: 0xd8ff64, wireframe: true });
    this.dockSocket = new THREE.Mesh(socketGeo, socketMat);
    this.dockSocket.position.set(0, 0, 92);
    this.dockGroup.add(this.dockSocket);

    // Cryptographic Evidence Log Receipts (3D floating plate)
    const receiptGeo = new THREE.PlaneGeometry(240, 300);
    const receiptMat = new THREE.MeshBasicMaterial({
      map: receiptLogTexture(),
      transparent: true,
      side: THREE.DoubleSide,
    });
    this.receiptPlate = new THREE.Mesh(receiptGeo, receiptMat);
    this.receiptPlate.position.set(190, 40, 40);
    this.receiptPlate.rotation.y = -0.3;
    this.dockGroup.add(this.receiptPlate);

    this.world.add(this.dockGroup);
  }

  setupPostProcessing() {
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

            // Subtle barrel lens distortion modulated by scroll velocity
            float distortion = 1.0 + r2 * (0.03 + abs(uVelocity) * 0.0001);
            vec2 distortedUv = center + dist * distortion;

            // Velocity-driven chromatic aberration + alert flare
            float chroma = abs(uVelocity) * 0.00075 + uAlert * 0.0035;
            vec2 dir = normalize(dist + vec2(0.0001));

            float r = texture2D(tDiffuse, distortedUv + dir * chroma).r;
            float g = texture2D(tDiffuse, distortedUv).g;
            float b = texture2D(tDiffuse, distortedUv - dir * chroma).b;
            vec3 col = vec3(r, g, b);

            // Red alert emergency flash during drift simulation
            if (uAlert > 0.01) {
              col = mix(col, vec3(col.r * 1.5 + 0.18, col.g * 0.5, col.b * 0.45), uAlert * 0.55);
            }

            // Cinematic analog film grain
            float grain = (random(uv + sin(uTime * 8.0)) - 0.5) * 0.026;
            col += grain;

            // Edge vignette
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
      console.warn('Post-processing initialized directly to default canvas:', e);
      this.usePost = false;
    }
  }

  setupPointerEvents() {
    window.addEventListener('pointermove', (e) => {
      this.pointerTarget.x = (e.clientX / window.innerWidth) * 2 - 1;
      this.pointerTarget.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }, { passive: true });
  }

  triggerDriftAlert() {
    this.alertIntensity = 1.0;
    this.laserMat.color.setHex(0xff4747);
    this.ringInner.material.color.setHex(0xff4747);
    this.crystalShellMat.color.setHex(0x381212);
    this.crystalShellMat.emissive.setHex(0x550909);
  }

  resetDriftAlert() {
    this.alertIntensity = 0;
    this.laserMat.color.setHex(0xd8ff64);
    this.ringInner.material.color.setHex(0xd8ff64);
    this.crystalShellMat.color.setHex(0x122a1e);
    this.crystalShellMat.emissive.setHex(0x0d3822);
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

  updatePhysics(deltaTime) {
    this.time += deltaTime;
    const p = this.progress;
    const t = this.time;

    // Smooth pointer lerping
    this.pointer.x += (this.pointerTarget.x - this.pointer.x) * 0.08;
    this.pointer.y += (this.pointerTarget.y - this.pointer.y) * 0.08;

    // Camera CatmullRomCurve3 Spline Tracking
    const camPos = this.cameraSpline.getPointAt(p);
    const lookPos = this.lookSpline.getPointAt(p);

    // Apply smooth mouse parallax to camera
    this.camera.position.set(
      camPos.x + this.pointer.x * 35,
      camPos.y + this.pointer.y * 25,
      camPos.z,
    );
    this.camera.lookAt(lookPos.x, lookPos.y, lookPos.z);

    // Floating Dust Particle Motion
    if (this.dust) {
      this.dust.rotation.y = t * 0.02;
    }

    // 1. Crystal Motion along Pipeline
    const crystalTrack = [
      [0, new THREE.Vector3(-460, 200, 0)],
      [1 / 7, new THREE.Vector3(-460, 200, 0)],
      [2 / 7, new THREE.Vector3(-250, 130, 0)],
      [3 / 7, new THREE.Vector3(-80, 50, 0)],
      [4 / 7, new THREE.Vector3(75, 25, 0)],
      [5 / 7, new THREE.Vector3(260, -110, 0)],
      [6 / 7, new THREE.Vector3(490, -20, 0)],
      [1, new THREE.Vector3(780, 70, 92)],
    ];

    let currentPos = crystalTrack[0][1].clone();
    for (let i = 1; i < crystalTrack.length; i++) {
      if (p <= crystalTrack[i][0]) {
        const [p0, v0] = crystalTrack[i - 1];
        const [p1, v1] = crystalTrack[i];
        const alpha = (p - p0) / Math.max(0.0001, p1 - p0);
        currentPos = v0.clone().lerp(v1, alpha);
        break;
      }
    }

    const floatBob = Math.sin(t * 1.8) * 3;
    this.crystalGroup.position.copy(currentPos);
    this.crystalGroup.position.y += floatBob;

    this.crystalMesh.rotation.y = t * 0.45;
    this.crystalMesh.rotation.x = Math.sin(t * 0.6) * 0.2;

    // 2. Gimbal Rings Dynamic Rotation (Step 03)
    if (this.gimbalGroup) {
      this.ringOuter.rotation.z = t * 1.2;
      this.ringMid.rotation.y = t * 1.8;
      this.ringInner.rotation.x = t * 2.4;
      this.lasers.rotation.z = -t * 1.2;
    }

    // 3. Rogue Shards Deflection (Step 02)
    const step2Active = p >= 1 / 7 && p <= 2.8 / 7;
    this.rogueShards.forEach((shard, idx) => {
      if (step2Active) {
        shard.position.x = -240 + Math.sin(t * 3 + idx) * 35;
        shard.rotation.x += 0.05;
        shard.rotation.y += 0.08;
      }
    });

    // 4. Test Suite Pylon Activation (Step 06)
    this.gatePylons.forEach((gate, idx) => {
      const threshold = 5 / 7 + (idx * 0.22) / 7;
      const passed = p >= threshold;
      gate.lamp.material.color.setHex(passed ? 0xd8ff64 : 0x243329);
      gate.curtain.material.opacity = passed ? 0.35 : 0.08;
    });

    // 5. Worktree Pod Confinement Rotation (Step 05)
    if (this.podShell) {
      this.podShell.rotation.y = t * 0.25;
    }

    // 6. Dock Socket Lock Indicator (Step 07)
    if (p >= 0.96) {
      this.dockSocket.material.color.setHex(0xd8ff64);
    }

    // Raycast Interaction with 3D Objects
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const intersects = this.raycaster.intersectObjects(this.interactiveObjects, true);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      const data = obj.userData;
      if (data && data.name) {
        if (inspectTarget) inspectTarget.textContent = `${data.name} (${data.file || 'SYSTEM'})`;
        if (inspectSymbol) inspectSymbol.textContent = data.symbols || data.name;
        if (inspectSector) inspectSector.textContent = data.sector || CHAMBERS[lastStep] || 'PIPELINE';
        if (inspectIntegrity && !isDrifting) inspectIntegrity.textContent = data.integrity || 'VERIFIED';
        body.style.cursor = 'crosshair';
      }
    } else {
      body.style.cursor = 'default';
    }
  }

  renderFrame(time, deltaTime) {
    if (isReduced) return;
    this.updatePhysics(deltaTime);

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
}

/* ------------------------------------------------------------------ *
 * Initialization & Deterministic Single Tick Loop
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

  // Single Deterministic Ticker: eliminates double-requestAnimationFrame jitter
  gsap.ticker.add((time, deltaTime) => {
    lenis?.raf(time * 1000);
    scene?.renderFrame(time, (deltaTime || 16) / 1000);
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
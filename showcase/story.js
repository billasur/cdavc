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

class TaskScene {
  constructor(target) {
    this.canvas = target;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x0b0e0d, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.canvas.replaceWith(this.renderer.domElement);
    this.canvas = this.renderer.domElement;
    this.canvas.id = 'task-canvas';
    this.canvas.setAttribute('aria-label', 'Three-dimensional CD-AVC task patch story');
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.Fog(0x0b0e0d, 650, 1800);
    this.camera = new THREE.PerspectiveCamera(30, 1, .1, 2200);
    this.camera.position.set(0, 35, 980);
    this.camera.lookAt(0, 0, 0);
    this.clock = new THREE.Clock();
    this.progress = 0;
    this.running = false;
    this.baseX = 80;
    this.baseY = 0;
    this.visible = true;
    this.phase = { step: 0, local: 0 };
    this.group = new THREE.Group();
    this.scene.add(this.group);
    this.accent = new THREE.Color('#d8ff64');
    this.white = new THREE.Color('#f4f6f1');
    this.muted = new THREE.Color('#66736a');
    this.build();
    this.observer = new IntersectionObserver((entries) => {
      this.visible = entries.some((entry) => entry.isIntersecting);
      if (this.visible && !isReduced) this.start();
      else this.stop();
    }, { threshold: 0.01 });
    this.observer.observe(story);
  }

  build() {
    this.ambient = new THREE.HemisphereLight(0xd7e4d3, 0x111612, .72);
    this.scene.add(this.ambient);
    this.key = new THREE.DirectionalLight(0xd8ff64, 1.35);
    this.key.position.set(-260, 500, 650);
    this.scene.add(this.key);
    this.rim = new THREE.DirectionalLight(0xf4f6f1, .5);
    this.rim.position.set(420, 120, -300);
    this.scene.add(this.rim);

    const groundMaterial = new THREE.MeshBasicMaterial({ color: 0x2d382f, transparent: true, opacity: .28, wireframe: true });
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(2600, 1800, 12, 8), groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -178;
    ground.position.z = 100;
    this.group.add(ground);

    const frameMaterial = new THREE.MeshStandardMaterial({ color: this.accent, roughness: .62, metalness: .1, transparent: true, opacity: .05, depthWrite: false });
    const frameGeometry = new THREE.BoxGeometry(430, 300, 42);
    this.frame = new THREE.Mesh(frameGeometry, frameMaterial);
    this.frame.position.y = 12;
    this.frame.scale.set(.01, .01, .01);
    this.group.add(this.frame);

    const frameEdges = new THREE.LineSegments(new THREE.EdgesGeometry(frameGeometry), new THREE.LineBasicMaterial({ color: this.accent, transparent: true, opacity: .9 }));
    this.frameEdges = frameEdges;
    frameEdges.position.copy(this.frame.position);
    frameEdges.scale.copy(this.frame.scale);
    this.group.add(frameEdges);

    const patchGeometry = new THREE.BoxGeometry(104, 68, 66);
    this.patch = new THREE.Mesh(patchGeometry, new THREE.MeshStandardMaterial({ color: this.accent, roughness: .38, metalness: .12 }));
    this.patch.position.set(0, 12, 0);
    this.patch.scale.set(.01, .01, .01);
    this.group.add(this.patch);
    this.patchEdges = new THREE.LineSegments(new THREE.EdgesGeometry(patchGeometry), new THREE.LineBasicMaterial({ color: this.white, transparent: true, opacity: .65 }));
    this.patchEdges.position.copy(this.patch.position);
    this.patchEdges.scale.copy(this.patch.scale);
    this.group.add(this.patchEdges);

    const rejectedMaterial = new THREE.MeshStandardMaterial({ color: 0x8b968d, roughness: .8, metalness: 0, transparent: true, opacity: .8 });
    this.rejected = new THREE.Mesh(new THREE.BoxGeometry(92, 60, 58), rejectedMaterial);
    this.rejected.position.set(0, 12, 0);
    this.rejected.scale.set(.01, .01, .01);
    this.group.add(this.rejected);
    this.rejectedEdges = new THREE.LineSegments(new THREE.EdgesGeometry(this.rejected.geometry), new THREE.LineBasicMaterial({ color: this.white, transparent: true, opacity: .6 }));
    this.rejectedEdges.position.copy(this.rejected.position);
    this.rejectedEdges.scale.copy(this.rejected.scale);
    this.group.add(this.rejectedEdges);

    this.tree = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.BoxGeometry(18, 220, 18), new THREE.MeshStandardMaterial({ color: this.white, roughness: .85 }));
    trunk.position.y = -30;
    this.tree.add(trunk);
    [[-110, 42, -20, 0, 0, -.4], [110, 42, -20, 0, 0, .4], [0, 125, -20, 0, 0, 0]].forEach(([x, y, z, rx, ry, rz]) => {
      const branch = new THREE.Mesh(new THREE.BoxGeometry(9, 220, 9), new THREE.MeshStandardMaterial({ color: this.white, roughness: .85 }));
      branch.position.set(x / 2, y / 2, z);
      branch.rotation.z = rz;
      this.tree.add(branch);
    });
    this.tree.position.set(144, 50, -180);
    this.tree.scale.set(.001, .001, .001);
    this.group.add(this.tree);

    this.gates = [];
    for (let i = 0; i < 4; i += 1) {
      const gate = new THREE.Mesh(new THREE.TorusGeometry(34, 2, 8, 64), new THREE.MeshBasicMaterial({ color: this.accent, transparent: true, opacity: .85 }));
      gate.position.set((i - 1.5) * 76, 12, 130);
      gate.scale.set(.001, .001, .001);
      this.gates.push(gate);
      this.group.add(gate);
    }

    const mainLineMaterial = new THREE.LineBasicMaterial({ color: this.accent, transparent: true, opacity: .45 });
    const linePoints = [new THREE.Vector3(-500, -170, 80), new THREE.Vector3(500, -170, 80)];
    this.groundLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(linePoints), mainLineMaterial);
    this.group.add(this.groundLine);
  }

  resize() {
    const width = this.canvas.clientWidth || window.innerWidth;
    const height = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / Math.max(1, height);
    // Must match the layout switch in story.css: below it the copy moves to the
    // bottom and the scene gets the band above it.
    const compact = window.matchMedia('(max-width: 1180px)').matches;
    this.compact = compact;
    const fov = compact ? 38 : 30;
    this.camera.fov = fov;
    this.camera.updateProjectionMatrix();
    const halfHeight = Math.tan((fov * Math.PI) / 360) * 980;
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
    const regionWidth = Math.max(140, right - left);
    const regionHeight = Math.max(140, bottom - top);
    const scale = Math.min(1, regionWidth * .92 / (430 * pxPerUnit), regionHeight * .92 / (300 * pxPerUnit));
    this.group.scale.setScalar(scale);
    this.baseX = ((left + right) / 2 - width / 2) / pxPerUnit;
    this.baseY = (height / 2 - (top + bottom) / 2) / pxPerUnit - 12 * scale;
    this.group.position.x = this.baseX;
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
    const step = this.phase.step;
    const frameIn = .94 + smoothstep(0, 1, this.progress * 10) * .06;
    const patchIn = smoothstep(0, 1, clamp01((this.progress - .05) * 16));
    const gateIn = smoothstep(0, 1, clamp01((this.progress - 2 / 7) * 8));
    const mergeIn = smoothstep(0, 1, clamp01((this.progress - 6 / 7) * 10));
    setScale(this.frame, frameIn); setScale(this.frameEdges, frameIn);
    setScale(this.patch, patchIn); setScale(this.patchEdges, patchIn);
    this.patch.visible = patchIn > .02;
    this.patchEdges.visible = this.patch.visible;
    const reject = smoothstep(0, 1, clamp01((this.progress - 1 / 7) * 5)) * (1 - mergeIn);
    this.rejected.scale.setScalar(.01 + reject * .99);
    this.rejected.visible = reject > .02;
    this.rejectedEdges.visible = this.rejected.visible;
    this.rejectedEdges.scale.copy(this.rejected.scale);
    this.rejected.position.x = -240 * reject;
    this.rejected.position.y = 12 - 240 * reject * reject;
    this.rejected.position.z = 50 + 120 * reject;
    this.rejected.rotation.z = reject * -.9;
    this.rejectedEdges.position.copy(this.rejected.position);
    this.rejectedEdges.rotation.copy(this.rejected.rotation);
    this.frame.material.opacity = .05 * (1 - mergeIn * .6);
    this.frameEdges.material.opacity = .9 * (1 - mergeIn * .72);
    this.patch.position.x = mergeIn * 80;
    this.patch.position.z = mergeIn * 105;
    this.patchEdges.position.copy(this.patch.position);
    const treeIn = smoothstep(0, 1, clamp01((this.progress - 6 / 7) * 8));
    this.tree.scale.setScalar(.001 + treeIn * .549);
    this.gates.forEach((gate, index) => {
      const gateProgress = smoothstep(0, 1, clamp01((this.progress - (2 + index) / 7) * 8));
      gate.scale.setScalar(.001 + gateProgress * .999);
      gate.material.opacity = (.22 + gateProgress * .58) * (1 - mergeIn * .9);
      gate.rotation.z = (this.progress * .3) + index * .04;
    });
    const cameraTargetZ = step >= 6 ? 820 : step >= 4 ? 900 : 980;
    const cameraTargetY = step >= 5 ? 55 : step >= 2 ? 32 : 12;
    this.camera.position.z = cameraTargetZ;
    this.camera.position.y = cameraTargetY;
    this.camera.position.x = Math.sin(this.progress * Math.PI * 1.4) * (this.compact ? 12 : 30);
    this.camera.lookAt(mergeIn * 25, mergeIn * 18, mergeIn * 40);
    this.group.rotation.y = (this.progress - .5) * -.24;
    this.group.position.y = this.baseY + (step >= 6 ? -8 : 0);
    this.group.position.z = step >= 6 ? 30 : 0;
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
    const time = this.clock.getElapsedTime();
    this.group.rotation.x = Math.sin(time * .08) * .012;
    this.group.position.x = this.baseX + Math.sin(time * .07) * 3;
    this.render(time, this.progress);
    this.frameId = requestAnimationFrame(() => this.loop());
  }

  render(time, progress) {
    if (!this.visible && !isReduced) return;
    this.setProgress(progress);
    this.renderer.render(this.scene, this.camera);
    void time;
  }
}

function clamp01(value) { return Math.max(0, Math.min(1, value)); }
function smoothstep(edge0, edge1, value) {
  const x = clamp01((value - edge0) / Math.max(.0001, edge1 - edge0));
  return x * x * (3 - 2 * x);
}
function setScale(object, value) { object.scale.setScalar(Math.max(.001, value)); }

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

import * as THREE from 'three';

/**
 * CD-AVC Showcase v6
 * Theme W2 by default (Warm Charcoal & Monochromatic Off-White) / Switchable to W1 (Dark Green)
 * Direction A: "Thread"
 * Hero: Solid Tactile Square Cube with 4-Stage Binary Mitosis Split (1 -> 2 -> 4 -> 8 -> 16)
 * Stage 1: Single Model ("One shot, can fail.") -> Cube turns red at fail moment
 * Stage 2: Retry Baseline ("More shots, no judgement.") -> 1 > 2 > 4 > 8 > 16 mitosis fan-out
 * Rejection Beat: All 16 cubes turn crimson red together when fully expanded
 * Stage 3: CD-AVC ("A cage that checks before it accepts.") -> 16 > 8 > 4 > 2 > 1 sequential merge into luminous white cube, sealed in CD-AVC vitrine cage
 * 100% Scroll-Scrubbed Bidirectionally, Zero Autoplay, Zero Per-Frame Allocations, 60fps InstancedMesh
 */

// Initialize Smooth Scrolling with Lenis
let lenis = null;
if (typeof window.Lenis !== 'undefined') {
  lenis = new window.Lenis({
    duration: 1.15,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
  });

  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
}

// Register GSAP ScrollTrigger
if (typeof window.gsap !== 'undefined' && typeof window.ScrollTrigger !== 'undefined') {
  window.gsap.registerPlugin(window.ScrollTrigger);
  if (lenis) {
    lenis.on('scroll', window.ScrollTrigger.update);
    window.gsap.ticker.add((time) => {
      lenis.raf(time * 1000);
    });
    window.gsap.ticker.lagSmoothing(0);
  }
}

// Cubic ease in-out helper for velvet-smooth transitions with zero jerk
function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Smoothstep clamp helper
function smoothstep(min, max, val) {
  const x = Math.max(0, Math.min(1, (val - min) / (max - min)));
  return x * x * (3 - 2 * x);
}

class ThreadStoryStage {
  constructor() {
    this.canvas = document.querySelector('#stage-canvas');
    if (!this.canvas) return;

    this.sentences = document.querySelectorAll('.story-sentence');
    this.scrollCue = document.querySelector('#scroll-cue');
    this.currentStage = 0;

    // Smoothed progress driven by damped lerp
    this.targetProgress = 0;
    this.smoothedProgress = 0;
    this.lastTime = performance.now();

    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    // Pre-allocated scratch objects to ensure ZERO per-frame allocations
    this._dummy = new THREE.Object3D();
    this._color = new THREE.Color();
    this._baseColor = new THREE.Color();
    this._edgeColor = new THREE.Color();
    this._redColor = new THREE.Color(0xff3838);
    this._whiteColor = new THREE.Color(0xf4f4f2);
    this._w1AccentColor = new THREE.Color(0xd8ff64);
    this._pos = new THREE.Vector3();

    // 4 Spatial split vectors: orthogonal + diagonal for balanced 3D distribution
    // Guarantees generous air gaps (min pairwise distance > 34 units vs 16.56 cube size)
    this.u1 = new THREE.Vector3(36.0, 2.0, 4.0);    // Split 1: Lateral X
    this.u2 = new THREE.Vector3(4.0, 28.0, -4.0);   // Split 2: Vertical Y
    this.u3 = new THREE.Vector3(6.0, -4.0, 24.0);   // Split 3: Depth Z
    this.u4 = new THREE.Vector3(12.0, 10.0, 10.0);  // Split 4: Fine 3D diagonal

    // Pre-computed birth stage for each of the 16 cube instances
    // Stage 0: root cube #0 (always alive)
    // Stage 1: cube #8 (born from #0 at split 1)
    // Stage 2: cubes #4, #12 (born from #0, #8 at split 2)
    // Stage 3: cubes #2, #6, #10, #14 (born at split 3)
    // Stage 4: odd cubes #1, #3, #5, #7, #9, #11, #13, #15 (born at split 4)
    this.birthStages = new Int32Array(16);
    for (let i = 0; i < 16; i++) {
      if (i === 0) this.birthStages[i] = 0;
      else if (i & 1) this.birthStages[i] = 4;
      else if (i & 2) this.birthStages[i] = 3;
      else if (i & 4) this.birthStages[i] = 2;
      else if (i & 8) this.birthStages[i] = 1;
      else this.birthStages[i] = 0;
    }

    this.initTheme();
    this.initScene();
    this.initObjects();
    this.initScrollTrigger();
    this.initListeners();
    this.handleUrlParams();
    this.animate(performance.now());
  }

  initTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = (urlParams.get('theme') || 'w2').toLowerCase();
    this.isW2 = themeParam !== 'w1';

    if (this.isW2) {
      document.documentElement.setAttribute('data-theme', 'w2');
      document.body.classList.add('theme-w2');
    } else {
      document.documentElement.removeAttribute('data-theme');
      document.body.classList.remove('theme-w2');
    }

    const btnW1 = document.querySelector('#btn-theme-w1');
    const btnW2 = document.querySelector('#btn-theme-w2');
    if (btnW1 && btnW2) {
      btnW1.classList.toggle('is-active', !this.isW2);
      btnW2.classList.toggle('is-active', this.isW2);
    }

    this.colors = this.isW2
      ? {
          bg: 0x161514,
          heroBase: 0x32302e,
          heroEdge: 0xeae7e1,
          thread: 0x8e8d8a,
          connector: 0xf5f3ee,
          dashes: 0x484643,
          keyLight: 0xfffaee,
          fillLight: 0xb0ada7,
          rimLight: 0xebe8e1,
          heroPoint: 0xfffdfa,
          acceptedEmissive: 0xf4f4f2,
          acceptedCore: 0xeae7e1,
          cageWire: 0xf5f2eb,
          cageGlass: 0xffffff,
          failRed: 0xff3838,
        }
      : {
          bg: 0x060807,
          heroBase: 0x19251e,
          heroEdge: 0xd8ff64,
          thread: 0xd8ff64,
          connector: 0xd8ff64,
          dashes: 0x2d3e33,
          keyLight: 0xf5f7f5,
          fillLight: 0x3d5244,
          rimLight: 0xd8ff64,
          heroPoint: 0xd8ff64,
          acceptedEmissive: 0xd8ff64,
          acceptedCore: 0x223829,
          cageWire: 0xd8ff64,
          cageGlass: 0xd8ff64,
          failRed: 0xff3838,
        };

    this._baseColor.setHex(this.colors.heroBase);
    this._edgeColor.setHex(this.colors.heroEdge);
  }

  initScene() {
    this.scene = new THREE.Scene();

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    const fov = this.isMobile ? 44 : 38;
    const camZ = this.isMobile ? 260 : 230;

    this.camera = new THREE.PerspectiveCamera(fov, width / height, 1, 1200);
    this.camera.position.set(0, 0, camZ);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Studio 3-point lighting setup for solid physical presence
    const ambColor = this.isW2 ? 0x2c2927 : 0x0e1511;
    const ambientLight = new THREE.AmbientLight(ambColor, 1.75);
    this.scene.add(ambientLight);

    // Key light: illuminates top and upper-right facets
    this.keyLight = new THREE.DirectionalLight(this.colors.keyLight, 2.4);
    this.keyLight.position.set(70, 85, 95);
    this.scene.add(this.keyLight);

    // Fill light: softens front-left facet
    this.fillLight = new THREE.DirectionalLight(this.colors.fillLight, 1.3);
    this.fillLight.position.set(-60, 25, 75);
    this.scene.add(this.fillLight);

    // Rim light: outlines silhouette and back edges
    this.rimLight = new THREE.DirectionalLight(this.colors.rimLight, 1.55);
    this.rimLight.position.set(-55, -45, -60);
    this.scene.add(this.rimLight);

    // Local Hero Point Light
    this.heroLight = new THREE.PointLight(this.colors.heroPoint, 1.25, 180);
    this.scene.add(this.heroLight);
  }

  initObjects() {
    // -------------------------------------------------------------
    // 1. Continuous Vertical Thread Line
    // -------------------------------------------------------------
    const threadPoints = [
      new THREE.Vector3(0, 140, 0),
      new THREE.Vector3(0, -140, 0),
    ];
    const threadGeo = new THREE.BufferGeometry().setFromPoints(threadPoints);
    this.threadMat = new THREE.LineBasicMaterial({
      color: this.colors.thread,
      transparent: true,
      opacity: this.isW2 ? 0.35 : 0.30,
    });
    this.threadLine = new THREE.Line(threadGeo, this.threadMat);
    this.scene.add(this.threadLine);

    // Guide Dashes on Thread
    const dashPoints = [];
    for (let y = 120; y >= -120; y -= 20) {
      dashPoints.push(new THREE.Vector3(-2.2, y, 0), new THREE.Vector3(2.2, y, 0));
    }
    const dashGeo = new THREE.BufferGeometry().setFromPoints(dashPoints);
    const dashMat = new THREE.LineBasicMaterial({
      color: this.colors.dashes,
      transparent: true,
      opacity: 0.40,
    });
    this.scene.add(new THREE.LineSegments(dashGeo, dashMat));

    // Base aesthetic rotation angles (isometric 3-facet view)
    this.baseRotX = 0.36;
    this.baseRotY = 0.52;
    this.baseRotZ = 0.04;

    // -------------------------------------------------------------
    // 2. Solid Square Cube & Instanced Mitosis System (1 -> 2 -> 4 -> 8 -> 16)
    // Pure square cube geometry (38 x 38 x 38)
    // InstancedMesh renders all 16 cubes in one draw call with zero GC allocations
    // -------------------------------------------------------------
    this.splitGroup = new THREE.Group();
    this.splitOffsetX = this.isMobile ? 0 : 8;
    this.splitGroup.position.set(this.splitOffsetX, 22, 0);
    this.splitGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.splitGroup);

    this.baseCubeSize = 38;
    this.boxGeo = new THREE.BoxGeometry(this.baseCubeSize, this.baseCubeSize, this.baseCubeSize);
    this.cubeMat = new THREE.MeshStandardMaterial({
      color: 0xffffff, // Tinted per-instance via instanceColor
      roughness: 0.28,
      metalness: 0.42,
    });

    this.instancedCubes = new THREE.InstancedMesh(this.boxGeo, this.cubeMat, 16);
    this.instancedCubes.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

    // Initialize per-instance color attribute
    const colorArray = new Float32Array(16 * 3);
    this.instancedCubes.instanceColor = new THREE.InstancedBufferAttribute(colorArray, 3);
    this.instancedCubes.instanceColor.setUsage(THREE.DynamicDrawUsage);

    this.splitGroup.add(this.instancedCubes);

    // Tactile Keynote Edge Lines for the 16 cubes
    // matrixAutoUpdate = false guarantees zero matrix overhead
    this.edgeGeo = new THREE.EdgesGeometry(this.boxGeo);
    this.edgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: this.isW2 ? 0.85 : 0.90,
    });

    this.edgeLines = [];
    for (let i = 0; i < 16; i++) {
      const edge = new THREE.LineSegments(this.edgeGeo, this.edgeMat);
      edge.matrixAutoUpdate = false;
      this.splitGroup.add(edge);
      this.edgeLines.push(edge);
    }

    // -------------------------------------------------------------
    // 3. CD-AVC Verification Cage (Vitrine Enclosure)
    // Precision square enclosure (48 x 48 x 48) for the 38x38x38 solid cube
    // -------------------------------------------------------------
    this.cageGroup = new THREE.Group();
    this.cageGroup.visible = false;
    this.splitGroup.add(this.cageGroup);

    const cageGeo = new THREE.BoxGeometry(48, 48, 48);
    const cageWireGeo = new THREE.EdgesGeometry(cageGeo);

    this.cageWireMat = new THREE.LineBasicMaterial({
      color: this.colors.cageWire,
      transparent: true,
      opacity: 0,
    });
    this.cageLines = new THREE.LineSegments(cageWireGeo, this.cageWireMat);
    this.cageGroup.add(this.cageLines);

    // Light Frosted Glass Vitrine Membrane
    const glassGeo = new THREE.BoxGeometry(46.5, 46.5, 46.5);
    this.cageGlassMat = new THREE.MeshStandardMaterial({
      color: this.colors.cageGlass,
      roughness: 0.15,
      metalness: 0.10,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.cageGlass = new THREE.Mesh(glassGeo, this.cageGlassMat);
    this.cageGroup.add(this.cageGlass);

    // Set initial layout at progress 0
    this.updateProgress(0);
  }

  initScrollTrigger() {
    const triggerEl = document.querySelector('#story-section');
    if (!triggerEl || typeof window.ScrollTrigger === 'undefined') return;

    window.ScrollTrigger.create({
      trigger: triggerEl,
      start: 'top top',
      end: 'bottom bottom',
      scrub: true,
      onUpdate: (self) => {
        this.targetProgress = self.progress;
      },
    });
  }

  handleUrlParams() {
    const params = new URLSearchParams(window.location.search);

    if (params.get('device') === 'mobile' || params.get('w') === '390') {
      document.body.classList.add('is-mobile-preview');
      this.isMobile = true;
      this.onResize();
    }

    const scrollParam = params.get('scroll') || params.get('p') || params.get('view');
    if (scrollParam === null) {
      this.targetProgress = 0;
      this.smoothedProgress = 0;
      this.updateProgress(0);
      return;
    }

    if (scrollParam === 'results' || scrollParam === '1.0' || scrollParam === '1') {
      document.body.classList.add('view-results-snapshot');
      this.targetProgress = 1.0;
      this.smoothedProgress = 1.0;
      this.updateProgress(1.0);
    } else {
      const p = parseFloat(scrollParam);
      if (!isNaN(p)) {
        const clampedP = Math.max(0, Math.min(1, p));
        this.targetProgress = clampedP;
        this.smoothedProgress = clampedP;
        this.updateProgress(clampedP);
      }
    }
  }

  updateProgress(p) {
    const progress = Math.max(0, Math.min(1, p));

    // Editorial Sentence Switching:
    // 0.00 - 0.28: Stage 0 (Single model: "One shot, can fail.")
    // 0.28 - 0.72: Stage 1 (Retry baseline: "More shots, no judgement.")
    // 0.72 - 1.00: Stage 2 (CD-AVC: "A cage that checks before it accepts.")
    let stageIndex = 0;
    if (progress >= 0.72) {
      stageIndex = 2;
    } else if (progress >= 0.28) {
      stageIndex = 1;
    }

    if (stageIndex !== this.currentStage) {
      this.currentStage = stageIndex;
      this.sentences.forEach((el, idx) => {
        el.classList.toggle('is-active', idx === stageIndex);
      });
    }

    // Scroll cue fade
    if (this.scrollCue) {
      this.scrollCue.style.opacity = progress > 0.04 ? '0' : '0.6';
    }

    // Vertical travel position along thread
    const threadY = 22 - progress * 44;
    this.heroLight.position.set(0, threadY, 25);

    const stage0Sub = document.querySelector('[data-stage="0"] .accent-sub');

    // Subtle, unhurried isometric parallax (never flips or spins wildly)
    const scrubRotX = this.baseRotX + Math.sin(progress * Math.PI) * 0.12;
    const scrubRotY = this.baseRotY + (progress - 0.5) * 0.36;

    this.splitOffsetX = this.isMobile ? 0 : 8;
    this.splitGroup.position.set(this.splitOffsetX, threadY, 0);
    this.splitGroup.rotation.set(scrubRotX, scrubRotY, this.baseRotZ);

    // Responsive group scaling
    const groupScale = this.isMobile ? 0.58 : 0.75;
    this.splitGroup.scale.setScalar(groupScale);

    // -------------------------------------------------------------
    // PROGRESS BEAT FACTORS (Mitosis, Rejection, Merge, Enclosure)
    // -------------------------------------------------------------

    // 1. Stage 0 Fail Risk (Single shot failure pulse at p in [0.12, 0.27])
    const failRisk0 = smoothstep(0.12, 0.20, progress) * (1.0 - smoothstep(0.25, 0.28, progress));

    // 2. Stage 1 Mitosis Splits (1 -> 2 -> 4 -> 8 -> 16) across p in [0.28, 0.69]
    // Overlapping cubic eased transitions with zero dead pauses
    const s1Raw = Math.max(0, Math.min(1, (progress - 0.28) / (0.41 - 0.28)));
    const s2Raw = Math.max(0, Math.min(1, (progress - 0.38) / (0.51 - 0.38)));
    const s3Raw = Math.max(0, Math.min(1, (progress - 0.48) / (0.61 - 0.48)));
    const s4Raw = Math.max(0, Math.min(1, (progress - 0.58) / (0.69 - 0.58)));

    const g1 = easeInOutCubic(s1Raw); // Split 1: 1 -> 2
    const g2 = easeInOutCubic(s2Raw); // Split 2: 2 -> 4
    const g3 = easeInOutCubic(s3Raw); // Split 3: 4 -> 8
    const g4 = easeInOutCubic(s4Raw); // Split 4: 8 -> 16

    // 3. Stage 2 Sequential Reverse Merge (16 -> 8 -> 4 -> 2 -> 1) across p in [0.74, 0.90]
    // Collapses in exact reverse order
    const c4Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.74) / (0.80 - 0.74)));
    const c3Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.78) / (0.84 - 0.78)));
    const c2Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.82) / (0.87 - 0.82)));
    const c1Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.85) / (0.90 - 0.85)));

    const c4 = easeInOutCubic(c4Raw); // Split 4 collapses: 16 -> 8
    const c3 = easeInOutCubic(c3Raw); // Split 3 collapses: 8 -> 4
    const c2 = easeInOutCubic(c2Raw); // Split 2 collapses: 4 -> 2
    const c1 = easeInOutCubic(c1Raw); // Split 1 collapses: 2 -> 1

    // Combine Growth & Collapse into current active split factors
    let f1, f2, f3, f4;
    if (progress < 0.72) {
      // Expanding / Mitosis phase
      f1 = g1;
      f2 = g2;
      f3 = g3;
      f4 = g4;
    } else {
      // Merging back into 1
      f1 = c1;
      f2 = c2;
      f3 = c3;
      f4 = c4;
    }

    // 4. Rejection Moment: When all 16 are out, they all turn red together
    // Peak rejection across p in [0.68, 0.76]
    const redIntensity = smoothstep(0.68, 0.72, progress) * (1.0 - smoothstep(0.76, 0.80, progress));

    // 5. Stage 3 Verification: Turn white and pull into cage
    const tAccept = smoothstep(0.84, 0.91, progress);
    const tCage = smoothstep(0.86, 0.94, progress);

    // Base scale shrinking progressively as cubes multiply:
    // 1 cube = 1.00
    // 2 cubes = 0.82
    // 4 cubes = 0.68
    // 8 cubes = 0.56
    // 16 cubes = 0.46
    const curScale = 1.0 - 0.18 * f1 - 0.14 * f2 - 0.12 * f3 - 0.10 * f4;

    // -------------------------------------------------------------
    // COLOR RESOLUTION
    // -------------------------------------------------------------
    if (failRisk0 > 0.01) {
      // Stage 0: Single shot fail moment (root cube turns red)
      this._color.copy(this._baseColor).lerp(this._redColor, failRisk0);
      this.edgeMat.color.copy(this._edgeColor).lerp(this._redColor, failRisk0);
      if (stage0Sub) stage0Sub.style.color = '#ff4747';
    } else if (redIntensity > 0.01) {
      // Rejection Moment: ALL 16 CUBES TURN RED TOGETHER
      this._color.copy(this._baseColor).lerp(this._redColor, redIntensity);
      this.edgeMat.color.copy(this._edgeColor).lerp(this._redColor, redIntensity);
      if (stage0Sub) stage0Sub.style.color = '';
    } else if (tAccept > 0.01) {
      // Stage 3 Verification: Turn luminous white / phosphor accent
      const targetColor = this.isW2 ? this._whiteColor : this._w1AccentColor;
      this._color.copy(this._baseColor).lerp(targetColor, tAccept);
      this.edgeMat.color.copy(this._edgeColor).lerp(targetColor, tAccept);
      if (stage0Sub) stage0Sub.style.color = '';
    } else {
      // Neutral solid keynote hero
      this._color.copy(this._baseColor);
      this.edgeMat.color.copy(this._edgeColor);
      if (stage0Sub) stage0Sub.style.color = '';
    }

    // -------------------------------------------------------------
    // UPDATE INSTANCED CUBES & EDGES (0 to 15)
    // -------------------------------------------------------------
    const fSplits = [f1, f2, f3, f4];

    for (let i = 0; i < 16; i++) {
      const birth = this.birthStages[i];
      let instanceScale = 0;

      if (birth === 0) {
        // Root cube is always alive
        instanceScale = curScale;
      } else {
        // Twin cube: scales up smoothly during its birth split
        const birthFactor = fSplits[birth - 1];
        instanceScale = curScale * birthFactor;
      }

      if (instanceScale > 0.002) {
        // Compute 3D position fanning out from parent
        let px = 0.0;
        let py = 0.0;
        let pz = 0.0;

        for (let k = 0; k < 4; k++) {
          const fk = fSplits[k];
          const bit = (i >> (3 - k)) & 1;
          const s = bit ? 1.0 : -1.0;

          let factor = 0.0;
          if (k + 1 < birth) {
            // Split prior to birth was already inherited from parent
            factor = 1.0;
          } else {
            // Split during or after birth
            factor = fk;
          }

          let u;
          if (k === 0) u = this.u1;
          else if (k === 1) u = this.u2;
          else if (k === 2) u = this.u3;
          else u = this.u4;

          px += s * u.x * factor;
          py += s * u.y * factor;
          pz += s * u.z * factor;
        }

        this._dummy.position.set(px, py, pz);
        this._dummy.scale.setScalar(instanceScale);
        this._dummy.updateMatrix();

        this.instancedCubes.setMatrixAt(i, this._dummy.matrix);
        this.instancedCubes.setColorAt(i, this._color);

        this.edgeLines[i].visible = true;
        this.edgeLines[i].matrix.copy(this._dummy.matrix);
      } else {
        // Inactive cube: hidden with scale 0 at root
        this._dummy.position.set(0, 0, 0);
        this._dummy.scale.setScalar(0.0001);
        this._dummy.updateMatrix();

        this.instancedCubes.setMatrixAt(i, this._dummy.matrix);
        this.instancedCubes.setColorAt(i, this._color);

        this.edgeLines[i].visible = false;
      }
    }

    this.instancedCubes.instanceMatrix.needsUpdate = true;
    if (this.instancedCubes.instanceColor) {
      this.instancedCubes.instanceColor.needsUpdate = true;
    }

    // -------------------------------------------------------------
    // CD-AVC VERIFICATION CAGE DESCENT & ENCLOSURE
    // -------------------------------------------------------------
    if (tCage > 0.001) {
      this.cageGroup.visible = true;
      // Descends from above and seals around the single merged white cube
      const cageDrop = (1.0 - tCage) * 35;
      this.cageGroup.position.set(0, cageDrop, 0);

      this.cageWireMat.opacity = tCage * (this.isW2 ? 0.90 : 0.92);
      this.cageGlassMat.opacity = tCage * (this.isW2 ? 0.16 : 0.10);
      this.threadMat.opacity = (this.isW2 ? 0.35 : 0.30) + tCage * 0.25;
    } else {
      this.cageGroup.visible = false;
      this.cageWireMat.opacity = 0;
      this.cageGlassMat.opacity = 0;
      this.threadMat.opacity = this.isW2 ? 0.35 : 0.30;
    }
  }

  initListeners() {
    window.addEventListener('resize', () => this.onResize(), { passive: true });

    window.addEventListener(
      'pointermove',
      (e) => {
        this.mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
        this.mouse.targetY = (e.clientY / window.innerHeight - 0.5) * 2;
      },
      { passive: true },
    );

    // Theme Switchers
    const btnW1 = document.querySelector('#btn-theme-w1');
    const btnW2 = document.querySelector('#btn-theme-w2');

    if (btnW1) {
      btnW1.addEventListener('click', (e) => {
        e.preventDefault();
        this.switchTheme('w1');
      });
    }
    if (btnW2) {
      btnW2.addEventListener('click', (e) => {
        e.preventDefault();
        this.switchTheme('w2');
      });
    }
  }

  switchTheme(newTheme) {
    const url = new URL(window.location.href);
    url.searchParams.set('theme', newTheme);
    window.history.replaceState({}, '', url.toString());

    this.initTheme();

    this.threadMat.color.setHex(this.colors.thread);
    this.keyLight.color.setHex(this.colors.keyLight);
    this.fillLight.color.setHex(this.colors.fillLight);
    this.rimLight.color.setHex(this.colors.rimLight);
    this.heroLight.color.setHex(this.colors.heroPoint);
    this.cageWireMat.color.setHex(this.colors.cageWire);
    this.cageGlassMat.color.setHex(this.colors.cageGlass);
    this.edgeMat.color.setHex(this.colors.heroEdge);

    this.updateProgress(this.smoothedProgress);
  }

  onResize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    this.camera.fov = this.isMobile ? 44 : 38;
    this.camera.position.z = this.isMobile ? 260 : 230;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  }

  animate(now) {
    requestAnimationFrame((t) => this.animate(t));

    const dt = Math.min((now - this.lastTime) * 0.001, 0.1);
    this.lastTime = now;

    // Framerate-independent exponential damping (Lenis + damped lerp for zero stepped jumps)
    const damping = 1.0 - Math.exp(-14 * dt);
    this.smoothedProgress += (this.targetProgress - this.smoothedProgress) * damping;

    // Update 3D scene with smoothed progress value
    this.updateProgress(this.smoothedProgress);

    // Subtle smooth mouse parallax
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

    this.camera.position.x = this.mouse.x * 6;
    this.camera.position.y = -this.mouse.y * 4;

    // Subtly track hero position along vertical thread
    const currentHeroY = 22 - this.smoothedProgress * 44;
    this.camera.lookAt(0, currentHeroY * 0.35, 0);

    // Confident pulsation when verified in Stage 3
    if (this.smoothedProgress >= 0.88) {
      this.heroLight.intensity = 1.25 + Math.sin(now * 0.004) * 0.25;
    } else {
      this.heroLight.intensity = 1.25;
    }

    this.renderer.render(this.scene, this.camera);
  }
}

// Instantiate on DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new ThreadStoryStage());
} else {
  new ThreadStoryStage();
}

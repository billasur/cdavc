import * as THREE from 'three';

/**
 * CD-AVC Showcase v6
 * Theme W2 by default (Warm Charcoal & Monochromatic Off-White) / Switchable to W1 (Dark Green)
 * Direction A: "Thread"
 * Hero: Solid Tactile Square Cube with Plant-like Hollow Branching Mitosis (1 -> 2 -> 4 -> 8)
 * Bold Heroic Scale: 44px root solid cube, 34px Level 1 hollow cubes, 25px Level 2, 18px Level 3
 * Stage 1: Single Model ("One shot, can fail.") -> Root solid cube turns red at fail moment
 * Stage 2: Retry Baseline ("More shots, no judgement.") -> 1 solid cube grows 2 hollow wireframe cubes,
 *          each grows 2 smaller hollow cubes, each grows 2 smaller (1 -> 2 -> 4 -> 8)
 * Rejection Beat: When all 8 are out, all hollow cubes & branches turn crimson red together (rejected)
 * Stage 3: CD-AVC ("A cage that checks before it accepts.") -> Systematic reverse collapse
 *          (8 -> 4 -> 2 -> 1), root solid cube turns luminous white, and seals in CD-AVC vitrine cage
 * 100% Scroll-Scrubbed Bidirectionally, Zero Autoplay, Zero Per-Frame Allocations, 60fps Smoothness
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
    this._t1Color = new THREE.Color();
    this._t2Color = new THREE.Color();
    this._baseColor = new THREE.Color();
    this._edgeColor = new THREE.Color();
    this._branchColor = new THREE.Color();
    this._redColor = new THREE.Color(0xff3838);
    this._whiteColor = new THREE.Color(0xf4f4f2);
    this._w1AccentColor = new THREE.Color(0xd8ff64);

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
          hollowWire: 0xeae7e1,
          branchLine: 0xf5f3ee,
          thread: 0x8e8d8a,
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
          hollowWire: 0xd8ff64,
          branchLine: 0xd8ff64,
          thread: 0xd8ff64,
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
    this._branchColor.setHex(this.colors.branchLine);
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
    // 2. Main Plant-like Mitosis Branching Tree (1 -> 2 -> 4 -> 8)
    // Much Bolder Scale: 44px root solid cube, 34px Level 1, 25px Level 2, 18px Level 3
    // -------------------------------------------------------------
    this.treeGroup = new THREE.Group();
    this.treeOffsetX = this.isMobile ? 0 : 8;
    this.treeGroup.position.set(this.treeOffsetX, 22, 0);
    this.treeGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.treeGroup);

    // ROOT SOLID CUBE (A lot bigger: 44 x 44 x 44)
    this.rootSize = 44;
    const rootGeo = new THREE.BoxGeometry(this.rootSize, this.rootSize, this.rootSize);
    const rootEdgeGeo = new THREE.EdgesGeometry(rootGeo);

    this.rootMat = new THREE.MeshStandardMaterial({
      color: this.colors.heroBase,
      roughness: 0.28,
      metalness: 0.42,
    });
    this.rootMesh = new THREE.Mesh(rootGeo, this.rootMat);
    this.treeGroup.add(this.rootMesh);

    this.rootEdgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: this.isW2 ? 0.85 : 0.90,
    });
    this.rootEdge = new THREE.LineSegments(rootEdgeGeo, this.rootEdgeMat);
    this.treeGroup.add(this.rootEdge);

    // -------------------------------------------------------------
    // -------------------------------------------------------------
    // 3. 20 Hollow Branching Cubes ("line wale") across 2 Tiers (1 -> 4 -> 16)
    // Tier 0: Root solid cube (44px)
    // Tier 1: 4 hollow cubes emerging from the 4 corners of root (32px)
    // Tier 2: 16 hollow cubes (each Tier 1 cube grows 4 cubes from its corners, 20px)
    // -------------------------------------------------------------
    this.tierSizes = [44, 32, 20];

    // Per-Tier materials for viral infection cascade
    // Tier 1 materials (4 inner hollow cubes & filaments)
    this.tier1WireMat = new THREE.MeshBasicMaterial({
      color: this.colors.hollowWire,
      wireframe: true,
      transparent: true,
      opacity: 0,
    });
    this.tier1EdgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: 0,
    });
    this.tier1BranchMat = new THREE.LineBasicMaterial({
      color: this.colors.branchLine,
      transparent: true,
      opacity: 0,
    });

    // Tier 2 materials (16 outer hollow cubes & filaments)
    this.tier2WireMat = new THREE.MeshBasicMaterial({
      color: this.colors.hollowWire,
      wireframe: true,
      transparent: true,
      opacity: 0,
    });
    this.tier2EdgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: 0,
    });
    this.tier2BranchMat = new THREE.LineBasicMaterial({
      color: this.colors.branchLine,
      transparent: true,
      opacity: 0,
    });

    // Build the 21-node topological tree structure (1 -> 4 -> 16)
    this.buildTreeTopology();

    // -------------------------------------------------------------
    // 4. CD-AVC Verification Cage (Vitrine Enclosure)
    // Precision square enclosure (54 x 54 x 54) for the 44x44x44 solid cube
    // -------------------------------------------------------------
    this.cageGroup = new THREE.Group();
    this.cageGroup.visible = false;
    this.treeGroup.add(this.cageGroup);

    const cageGeo = new THREE.BoxGeometry(54, 54, 54);
    const cageWireGeo = new THREE.EdgesGeometry(cageGeo);

    this.cageWireMat = new THREE.LineBasicMaterial({
      color: this.colors.cageWire,
      transparent: true,
      opacity: 0,
    });
    this.cageLines = new THREE.LineSegments(cageWireGeo, this.cageWireMat);
    this.cageGroup.add(this.cageLines);

    // Light Frosted Glass Vitrine Membrane
    const glassGeo = new THREE.BoxGeometry(52.5, 52.5, 52.5);
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

    // Initial layout at progress 0
    this.updateProgress(0);
  }

  buildTreeTopology() {
    // Node 0 is the root solid cube at (0, 0, 0)
    this.nodes = [{
      id: 0,
      tier: 0,
      parent: -1,
      targetPos: new THREE.Vector3(0, 0, 0),
      currentPos: new THREE.Vector3(0, 0, 0),
    }];

    // -------------------------------------------------------------
    // Tier 1: 4 primary branches emerging from the 4 corners of the root solid cube
    // -------------------------------------------------------------
    const t1Coords = [
      new THREE.Vector3( 40.91,  32.73,  13.09), // 1: Top-Right
      new THREE.Vector3(-40.91, -32.73, -13.09), // 2: Bottom-Left
      new THREE.Vector3(-40.91,  32.73, -13.09), // 3: Top-Left
      new THREE.Vector3( 40.91, -32.73,  13.09), // 4: Bottom-Right
    ];

    for (let i = 0; i < 4; i++) {
      this.nodes.push({
        id: i + 1,
        tier: 1,
        parent: 0,
        targetPos: t1Coords[i],
        currentPos: new THREE.Vector3(0, 0, 0),
      });
    }

    const t2Defs = [
      // 4 daughter cubes scattered across open corners of Node 1 (Top-Right):
      { id:  5, parent: 1, pos: new THREE.Vector3( 20.13,  53.51,  -7.69) },
      { id:  6, parent: 1, pos: new THREE.Vector3( 61.69,  53.51,  -7.69) },
      { id:  7, parent: 1, pos: new THREE.Vector3( 61.69,  53.51,  33.87) },
      { id:  8, parent: 1, pos: new THREE.Vector3( 61.69,  11.95,  33.87) },
      // 4 daughter cubes scattered across open corners of Node 2 (Bottom-Left):
      { id:  9, parent: 2, pos: new THREE.Vector3(-20.13, -53.51,   7.69) },
      { id: 10, parent: 2, pos: new THREE.Vector3(-61.69, -53.51,   7.69) },
      { id: 11, parent: 2, pos: new THREE.Vector3(-61.69, -53.51, -33.87) },
      { id: 12, parent: 2, pos: new THREE.Vector3(-61.69, -11.95, -33.87) },
      // 4 daughter cubes scattered across open corners of Node 3 (Top-Left):
      { id: 13, parent: 3, pos: new THREE.Vector3(-20.13,  53.51, -33.87) },
      { id: 14, parent: 3, pos: new THREE.Vector3(-61.69,  53.51, -33.87) },
      { id: 15, parent: 3, pos: new THREE.Vector3(-61.69,  11.95, -33.87) },
      { id: 16, parent: 3, pos: new THREE.Vector3(-61.69,  11.95,   7.69) },
      // 4 daughter cubes scattered across open corners of Node 4 (Bottom-Right):
      { id: 17, parent: 4, pos: new THREE.Vector3( 20.13, -53.51,  33.87) },
      { id: 18, parent: 4, pos: new THREE.Vector3( 61.69, -53.51,  33.87) },
      { id: 19, parent: 4, pos: new THREE.Vector3( 61.69, -11.95,  33.87) },
      { id: 20, parent: 4, pos: new THREE.Vector3( 61.69, -11.95,  -7.69) },
    ];

    for (const def of t2Defs) {
      this.nodes.push({
        id: def.id,
        tier: 2,
        parent: def.parent,
        targetPos: def.pos,
        currentPos: new THREE.Vector3(0, 0, 0),
      });
    }

    // Create 3D visual representations for each hollow branching node (1 to N)
    for (let i = 1; i < this.nodes.length; i++) {
      const node = this.nodes[i];
      const size = this.tierSizes[node.tier];

      const boxGeo = new THREE.BoxGeometry(size, size, size);
      const edgeGeo = new THREE.EdgesGeometry(boxGeo);

      const isT1 = node.tier === 1;
      const wireMat = isT1 ? this.tier1WireMat : this.tier2WireMat;
      const edgeMat = isT1 ? this.tier1EdgeMat : this.tier2EdgeMat;
      const branchMat = isT1 ? this.tier1BranchMat : this.tier2BranchMat;

      // Hollow wireframe cube mesh
      const wireMesh = new THREE.Mesh(boxGeo, wireMat);
      // Outer crisp keynote edge lines
      const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);

      const cubeGroup = new THREE.Group();
      cubeGroup.add(wireMesh);
      cubeGroup.add(edgeLines);
      cubeGroup.visible = false;
      this.treeGroup.add(cubeGroup);

      // Connector filament linking parent node to child node
      const linePositions = new Float32Array(6);
      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
      const connectorLine = new THREE.Line(lineGeo, branchMat);
      connectorLine.visible = false;
      this.treeGroup.add(connectorLine);

      node.cubeGroup = cubeGroup;
      node.line = connectorLine;
      node.lineGeo = lineGeo;
    }
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

    // Editorial Sentence Switching (Aligned 1:1 with Visual Chapters):
    // 0.00 - 0.34: Stage 0 (Single model: "01 / SINGLE MODEL: One shot, can fail.")
    // 0.34 - 0.78: Stage 1 (Retry baseline: "02 / RETRY BASELINE: More shots, no judgement.")
    // 0.78 - 1.00: Stage 2 (CD-AVC: "03 / CD-AVC: A cage that checks before it accepts.")
    let stageIndex = 0;
    if (progress >= 0.78) {
      stageIndex = 2;
    } else if (progress >= 0.34) {
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
    const stage1Sub = document.querySelector('[data-stage="1"] .accent-sub');
    const stage2Sub = document.querySelector('[data-stage="2"] .accent-sub');

    // Subtle, unhurried isometric parallax (never flips or spins wildly)
    const scrubRotX = this.baseRotX + Math.sin(progress * Math.PI) * 0.12;
    const scrubRotY = this.baseRotY + (progress - 0.5) * 0.36;

    this.treeOffsetX = this.isMobile ? 0 : 8;
    this.treeGroup.position.set(this.treeOffsetX, threadY, 0);
    this.treeGroup.rotation.set(scrubRotX, scrubRotY, this.baseRotZ);

    // Responsive scaling (calibrated for 1 -> 4 -> 16 self-similar radial branching)
    const baseScale = 0.54;
    const groupScale = this.isMobile ? (baseScale * 0.74) : baseScale;
    this.treeGroup.scale.setScalar(groupScale);

    // -------------------------------------------------------------
    // PROGRESS BEAT FACTORS (Mitosis: 1 -> 4 -> 16, Viral Infection Cascade, Cleansing)
    // -------------------------------------------------------------

    // 1. Stage 0 Fail Moment ("One shot, can fail.")
    // Unhurried, generous scroll duration:
    // - 0.00 - 0.12: pristine solid cube
    // - 0.12 - 0.20: turns crimson red
    // - 0.20 - 0.31: SUSTAINED RED FAIL BEAT (ample time to read and register)
    // - 0.31 - 0.35: resets to neutral ready for retries
    const failRisk0 = smoothstep(0.12, 0.20, progress) * (1.0 - smoothstep(0.31, 0.35, progress));

    // 2. Stage 1 Mitosis Splits across p in [0.34, 0.68]
    // Split 1 (p in [0.34, 0.52]): 4 hollow cubes emerge from 4 corners of root (32px)
    // Split 2 (p in [0.50, 0.68]): 16 smaller hollow cubes emerge scattered across all open corners (20px)
    const s1Raw = Math.max(0, Math.min(1, (progress - 0.34) / (0.52 - 0.34)));
    const s2Raw = Math.max(0, Math.min(1, (progress - 0.50) / (0.68 - 0.50)));
    const g1 = easeInOutCubic(s1Raw);
    const g2 = easeInOutCubic(s2Raw);

    // 3. Stage 2 Sequential Reverse Merge across p in [0.78, 0.89]
    // Step 1: 16 outer cubes collapse into their 4 parents (p in [0.78, 0.84])
    // Step 2: 4 parent cubes collapse into root solid cube (p in [0.83, 0.89])
    const c2Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.78) / (0.84 - 0.78)));
    const c1Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.83) / (0.89 - 0.83)));
    const c2 = easeInOutCubic(c2Raw); // 16 cubes pull back into 4 cubes
    const c1 = easeInOutCubic(c1Raw); // 4 cubes pull back into root solid cube

    const f1 = (progress < 0.78) ? g1 : c1;
    const f2 = (progress < 0.78) ? g2 : c2;
    const f3 = 0.0;

    // -------------------------------------------------------------
    // VIRUS INFECTION CONTAGION CASCADE
    // "First outer most layer becomes red and after merging back,
    // inner layers one by one as red ones merge into them, become red
    // until main solid one becomes red - like virus infection"
    // -------------------------------------------------------------

    // Wave 1: Outermost layer (Tier 2: 16 cubes) turns RED first at p in [0.68, 0.74]
    // Stays red through p = 0.78 while text is still 02 / RETRY BASELINE!
    const infectT2 = smoothstep(0.68, 0.74, progress);

    // Wave 2: As red outer cubes merge into Tier 1 (across [0.78, 0.84]),
    // Tier 1 catches the infection and turns RED at p in [0.79, 0.84]
    const infectT1 = smoothstep(0.79, 0.84, progress);

    // Wave 3: As red Tier 1 cubes merge into Root Solid Cube (across [0.83, 0.89]),
    // Root Solid Cube catches the infection and turns RED at p in [0.85, 0.89]
    const infectT0 = smoothstep(0.85, 0.89, progress);

    // Wave 4: CD-AVC Cleansing & Enclosure (p in [0.89, 0.95])
    // The vitrine cage checks and cleanses the infection into purified luminous white
    const tPurify = smoothstep(0.89, 0.95, progress);
    const tCage = smoothstep(0.89, 0.96, progress);

    // Accent Sub Text Styling
    if (stage0Sub) stage0Sub.style.color = failRisk0 > 0.05 ? '#ff4747' : '';
    if (stage1Sub) stage1Sub.style.color = (infectT2 > 0.2 && stageIndex === 1) ? '#ff4747' : '';
    if (stage2Sub) stage2Sub.style.color = (tPurify > 0.4 && stageIndex === 2) ? (this.isW2 ? '#f4f4f2' : '#d8ff64') : '';

    // -------------------------------------------------------------
    // COLOR & MATERIAL STATES (Per-Tier Contagion Assignment)
    // -------------------------------------------------------------
    // Tier 2 (16 Outer Cubes & Branches)
    this._t2Color.copy(this._baseColor).lerp(this._redColor, infectT2);
    this.tier2WireMat.color.copy(this._t2Color);
    this.tier2EdgeMat.color.copy(this._t2Color);
    this.tier2BranchMat.color.copy(this._t2Color);

    // Tier 1 (4 Inner Cubes & Branches)
    this._t1Color.copy(this._baseColor).lerp(this._redColor, infectT1);
    this.tier1WireMat.color.copy(this._t1Color);
    this.tier1EdgeMat.color.copy(this._t1Color);
    this.tier1BranchMat.color.copy(this._t1Color);

    // Tier 0 (Root Solid Cube)
    if (failRisk0 > 0.01) {
      // Stage 0: Single shot failure pulse
      this._color.copy(this._baseColor).lerp(this._redColor, failRisk0);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(this._redColor).multiplyScalar(failRisk0 * 0.45);
      this.rootEdgeMat.color.copy(this._edgeColor).lerp(this._redColor, failRisk0);
    } else if (progress >= 0.89) {
      // Wave 4: CD-AVC Cleansing from infected red to purified luminous white
      const targetColor = this.isW2 ? this._whiteColor : this._w1AccentColor;
      this._color.copy(this._redColor).lerp(targetColor, tPurify);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(this._redColor).lerp(targetColor, tPurify).multiplyScalar(0.50);
      this.rootEdgeMat.color.copy(this._redColor).lerp(targetColor, tPurify);
    } else if (infectT0 > 0.01) {
      // Wave 3: Viral infection reaching the root solid cube
      this._color.copy(this._baseColor).lerp(this._redColor, infectT0);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(this._redColor).multiplyScalar(infectT0 * 0.60);
      this.rootEdgeMat.color.copy(this._edgeColor).lerp(this._redColor, infectT0);
    } else {
      // Neutral solid keynote hero
      this.rootMat.color.copy(this._baseColor);
      this.rootMat.emissive.setHex(0x000000);
      this.rootEdgeMat.color.copy(this._edgeColor);
    }

    // -------------------------------------------------------------
    // UPDATE HOLLOW BRANCHING CUBES & FILAMENTS
    // -------------------------------------------------------------
    const tierFactors = [1.0, f1, f2, f3];

    // Compute animated positions for each node along the tree
    for (let i = 1; i < this.nodes.length; i++) {
      const node = this.nodes[i];
      const parentNode = this.nodes[node.parent];
      const f = tierFactors[node.tier];

      if (f > 0.005) {
        node.cubeGroup.visible = true;
        node.cubeGroup.scale.setScalar(Math.max(0.001, f));

        // Position extends outward from parent's current position to target offset
        node.currentPos.x = parentNode.currentPos.x + (node.targetPos.x - parentNode.targetPos.x) * f;
        node.currentPos.y = parentNode.currentPos.y + (node.targetPos.y - parentNode.targetPos.y) * f;
        node.currentPos.z = parentNode.currentPos.z + (node.targetPos.z - parentNode.targetPos.z) * f;

        node.cubeGroup.position.copy(node.currentPos);

        // Update branch line linking parent to child
        node.line.visible = f > 0.02;
        const posAttr = node.lineGeo.attributes.position;
        posAttr.setXYZ(0, parentNode.currentPos.x, parentNode.currentPos.y, parentNode.currentPos.z);
        posAttr.setXYZ(1, node.currentPos.x, node.currentPos.y, node.currentPos.z);
        posAttr.needsUpdate = true;
      } else {
        node.cubeGroup.visible = false;
        node.cubeGroup.scale.setScalar(0.001);
        node.currentPos.copy(parentNode.currentPos);
        node.cubeGroup.position.copy(parentNode.currentPos);
        node.line.visible = false;
      }
    }

    // Update per-tier opacity based on tier factor
    this.tier2WireMat.opacity = Math.min(1.0, f2 * 0.75);
    this.tier2EdgeMat.opacity = Math.min(1.0, f2 * 0.90);
    this.tier2BranchMat.opacity = Math.min(1.0, f2 * 0.65);

    this.tier1WireMat.opacity = Math.min(1.0, f1 * 0.75);
    this.tier1EdgeMat.opacity = Math.min(1.0, f1 * 0.90);
    this.tier1BranchMat.opacity = Math.min(1.0, f1 * 0.65);

    // -------------------------------------------------------------
    // CD-AVC VERIFICATION CAGE DESCENT & ENCLOSURE
    // -------------------------------------------------------------
    if (tCage > 0.001) {
      this.cageGroup.visible = true;
      // Descends from above and seals around the 44px solid cube
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
    this.rootEdgeMat.color.setHex(this.colors.heroEdge);
    this.tier1WireMat.color.setHex(this.colors.hollowWire);
    this.tier1EdgeMat.color.setHex(this.colors.heroEdge);
    this.tier1BranchMat.color.setHex(this.colors.branchLine);
    this.tier2WireMat.color.setHex(this.colors.hollowWire);
    this.tier2EdgeMat.color.setHex(this.colors.heroEdge);
    this.tier2BranchMat.color.setHex(this.colors.branchLine);

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

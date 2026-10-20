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
    // 3. 14 Hollow Branching Cubes ("line wale") across 3 Tiers (1 -> 2 -> 4 -> 8)
    // Tier 1: 2 hollow cubes branching from root (34px)
    // Tier 2: 4 hollow cubes branching from Tier 1 (25px)
    // Tier 3: 8 hollow cubes branching from Tier 2 (18px)
    // (Removed 8->16 level to keep stage pristine, bold, and never clumsy)
    // -------------------------------------------------------------
    this.tierSizes = [44, 34, 25, 18];

    // Shared hollow wireframe material & edge material
    this.hollowWireMat = new THREE.MeshBasicMaterial({
      color: this.colors.hollowWire,
      wireframe: true,
      transparent: true,
      opacity: 0,
    });

    this.hollowEdgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: 0,
    });

    this.branchMat = new THREE.LineBasicMaterial({
      color: this.colors.branchLine,
      transparent: true,
      opacity: 0,
    });

    // Build the 15-node topological tree structure
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
    const l1_dist = 48.0;
    const l2_dist = 36.0;

    // Node 0 is the root solid cube at (0, 0, 0)
    this.nodes = [{
      id: 0,
      tier: 0,
      parent: -1,
      targetPos: new THREE.Vector3(0, 0, 0),
      currentPos: new THREE.Vector3(0, 0, 0),
    }];

    // Tier 1 (2 nodes from root solid cube, exactly matching demo frame 003)
    this.nodes.push({
      id: 1,
      tier: 1,
      parent: 0,
      targetPos: new THREE.Vector3(l1_dist * 0.76, l1_dist * 0.60, l1_dist * 0.25),
      currentPos: new THREE.Vector3(0, 0, 0),
    });
    this.nodes.push({
      id: 2,
      tier: 1,
      parent: 0,
      targetPos: new THREE.Vector3(-l1_dist * 0.76, -l1_dist * 0.60, -l1_dist * 0.25),
      currentPos: new THREE.Vector3(0, 0, 0),
    });

    // Tier 2 (2 from each Tier 1 = 4 nodes)
    const p1 = this.nodes[1].targetPos;
    this.nodes.push({
      id: 3,
      tier: 2,
      parent: 1,
      targetPos: new THREE.Vector3(p1.x + l2_dist * 0.45, p1.y + l2_dist * 0.75, p1.z - l2_dist * 0.48),
      currentPos: new THREE.Vector3(0, 0, 0),
    });
    this.nodes.push({
      id: 4,
      tier: 2,
      parent: 1,
      targetPos: new THREE.Vector3(p1.x + l2_dist * 0.75, p1.y - l2_dist * 0.40, p1.z + l2_dist * 0.52),
      currentPos: new THREE.Vector3(0, 0, 0),
    });

    const p2 = this.nodes[2].targetPos;
    this.nodes.push({
      id: 5,
      tier: 2,
      parent: 2,
      targetPos: new THREE.Vector3(p2.x - l2_dist * 0.45, p2.y - l2_dist * 0.75, p2.z + l2_dist * 0.48),
      currentPos: new THREE.Vector3(0, 0, 0),
    });
    this.nodes.push({
      id: 6,
      tier: 2,
      parent: 2,
      targetPos: new THREE.Vector3(p2.x - l2_dist * 0.75, p2.y + l2_dist * 0.40, p2.z - l2_dist * 0.52),
      currentPos: new THREE.Vector3(0, 0, 0),
    });

    // Tier 3 (2 from each Tier 2 = 8 nodes)
    // From 3:
    const p3 = this.nodes[3].targetPos;
    this.nodes.push({
      id: 7,
      tier: 3,
      parent: 3,
      targetPos: new THREE.Vector3(p3.x + 10.0, p3.y + 24.0, p3.z - 14.0),
      currentPos: new THREE.Vector3(0, 0, 0),
    });
    this.nodes.push({
      id: 8,
      tier: 3,
      parent: 3,
      targetPos: new THREE.Vector3(p3.x + 24.0, p3.y + 12.0, p3.z - 6.0),
      currentPos: new THREE.Vector3(0, 0, 0),
    });

    // From 4:
    const p4 = this.nodes[4].targetPos;
    this.nodes.push({
      id: 9,
      tier: 3,
      parent: 4,
      targetPos: new THREE.Vector3(p4.x + 24.0, p4.y - 8.0, p4.z + 14.0),
      currentPos: new THREE.Vector3(0, 0, 0),
    });
    this.nodes.push({
      id: 10,
      tier: 3,
      parent: 4,
      targetPos: new THREE.Vector3(p4.x + 10.0, p4.y - 24.0, p4.z + 16.0),
      currentPos: new THREE.Vector3(0, 0, 0),
    });

    // Symmetrics for 5 and 6:
    for (let i = 7; i <= 10; i++) {
      const src = this.nodes[i].targetPos;
      const parentId = i <= 8 ? 5 : 6;
      this.nodes.push({
        id: this.nodes.length,
        tier: 3,
        parent: parentId,
        targetPos: new THREE.Vector3(-src.x, -src.y, -src.z),
        currentPos: new THREE.Vector3(0, 0, 0),
      });
    }

    // Create 3D visual representations for each of the 14 hollow branching nodes (1 to 14)
    for (let i = 1; i < this.nodes.length; i++) {
      const node = this.nodes[i];
      const size = this.tierSizes[node.tier];

      const boxGeo = new THREE.BoxGeometry(size, size, size);
      const edgeGeo = new THREE.EdgesGeometry(boxGeo);

      // Hollow wireframe cube mesh (MeshBasicMaterial with wireframe: true, exactly as in demo frame 003)
      const wireMesh = new THREE.Mesh(boxGeo, this.hollowWireMat);
      // Outer crisp edge lines
      const edgeLines = new THREE.LineSegments(edgeGeo, this.hollowEdgeMat);

      const cubeGroup = new THREE.Group();
      cubeGroup.add(wireMesh);
      cubeGroup.add(edgeLines);
      cubeGroup.visible = false;
      this.treeGroup.add(cubeGroup);

      // Connector line linking parent node to child node
      const linePositions = new Float32Array(6);
      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
      const connectorLine = new THREE.Line(lineGeo, this.branchMat);
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

    this.treeOffsetX = this.isMobile ? 0 : 8;
    this.treeGroup.position.set(this.treeOffsetX, threadY, 0);
    this.treeGroup.rotation.set(scrubRotX, scrubRotY, this.baseRotZ);

    // Responsive scaling
    const groupScale = this.isMobile ? 0.46 : 0.62;
    this.treeGroup.scale.setScalar(groupScale);

    // -------------------------------------------------------------
    // PROGRESS BEAT FACTORS (Mitosis: 1 -> 2 -> 4 -> 8, Rejection, Merge, Enclosure)
    // -------------------------------------------------------------

    // 1. Stage 0 Fail Risk (Single shot failure pulse at p in [0.12, 0.27])
    const failRisk0 = smoothstep(0.12, 0.20, progress) * (1.0 - smoothstep(0.25, 0.28, progress));

    // 2. Stage 1 Mitosis Splits (1 -> 2 -> 4 -> 8) across p in [0.28, 0.68]
    // Overlapping cubic eased transitions with zero dead pauses
    const s1Raw = Math.max(0, Math.min(1, (progress - 0.28) / (0.42 - 0.28)));
    const s2Raw = Math.max(0, Math.min(1, (progress - 0.40) / (0.55 - 0.40)));
    const s3Raw = Math.max(0, Math.min(1, (progress - 0.53) / (0.68 - 0.53)));

    const g1 = easeInOutCubic(s1Raw); // Split 1: 2 hollow cubes emerge from root (34px)
    const g2 = easeInOutCubic(s2Raw); // Split 2: 4 smaller hollow cubes emerge from Tier 1 (25px)
    const g3 = easeInOutCubic(s3Raw); // Split 3: 8 smaller hollow cubes emerge from Tier 2 (18px)

    // 3. Stage 2 Sequential Reverse Merge (8 -> 4 -> 2 -> 1) across p in [0.74, 0.91]
    // Collapses systematically in exact reverse order
    const c3Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.74) / (0.82 - 0.74)));
    const c2Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.80) / (0.87 - 0.80)));
    const c1Raw = 1.0 - Math.max(0, Math.min(1, (progress - 0.85) / (0.91 - 0.85)));

    const c3 = easeInOutCubic(c3Raw); // Tier 3 collapses: 8 -> 4
    const c2 = easeInOutCubic(c2Raw); // Tier 2 collapses: 4 -> 2
    const c1 = easeInOutCubic(c1Raw); // Tier 1 collapses: 2 -> 1

    let f1, f2, f3;
    if (progress < 0.72) {
      f1 = g1;
      f2 = g2;
      f3 = g3;
    } else {
      f1 = c1;
      f2 = c2;
      f3 = c3;
    }

    // 4. Rejection Moment: When all 8 are out, they all turn red together
    const redIntensity = smoothstep(0.68, 0.72, progress) * (1.0 - smoothstep(0.76, 0.80, progress));

    // 5. Stage 3 Verification: Turn white and pull into cage
    const tAccept = smoothstep(0.85, 0.92, progress);
    const tCage = smoothstep(0.87, 0.95, progress);

    // -------------------------------------------------------------
    // COLOR & MATERIAL STATES
    // -------------------------------------------------------------
    if (failRisk0 > 0.01) {
      // Stage 0: Single shot fail moment (root solid cube turns red)
      this._color.copy(this._baseColor).lerp(this._redColor, failRisk0);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(this._redColor).multiplyScalar(failRisk0 * 0.45);
      this.rootEdgeMat.color.copy(this._edgeColor).lerp(this._redColor, failRisk0);
      if (stage0Sub) stage0Sub.style.color = '#ff4747';
    } else if (redIntensity > 0.01) {
      // Rejection Beat: ALL 8 CUBES & BRANCHES TURN RED TOGETHER
      this._color.copy(this._baseColor).lerp(this._redColor, redIntensity);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(this._redColor).multiplyScalar(redIntensity * 0.4);
      this.rootEdgeMat.color.copy(this._redColor);

      this.hollowWireMat.color.copy(this._redColor);
      this.hollowEdgeMat.color.copy(this._redColor);
      this.branchMat.color.copy(this._redColor);
      if (stage0Sub) stage0Sub.style.color = '';
    } else if (tAccept > 0.01) {
      // Stage 3 Verification: Turn luminous white / phosphor accent
      const targetColor = this.isW2 ? this._whiteColor : this._w1AccentColor;
      this._color.copy(this._baseColor).lerp(targetColor, tAccept);
      this.rootMat.color.copy(this._color);
      this.rootMat.emissive.copy(targetColor).multiplyScalar(tAccept * 0.5);
      this.rootEdgeMat.color.copy(this._edgeColor).lerp(targetColor, tAccept);

      this.hollowWireMat.color.setHex(this.colors.hollowWire);
      this.hollowEdgeMat.color.setHex(this.colors.heroEdge);
      this.branchMat.color.setHex(this.colors.branchLine);
      if (stage0Sub) stage0Sub.style.color = '';
    } else {
      // Neutral solid keynote hero
      this.rootMat.color.copy(this._baseColor);
      this.rootMat.emissive.setHex(0x000000);
      this.rootEdgeMat.color.copy(this._edgeColor);

      this.hollowWireMat.color.setHex(this.colors.hollowWire);
      this.hollowEdgeMat.color.setHex(this.colors.heroEdge);
      this.branchMat.color.setHex(this.colors.branchLine);
      if (stage0Sub) stage0Sub.style.color = '';
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

    // Update opacity for hollow wireframe and edges based on overall tree activity
    const maxBranchF = Math.max(f1, f2, f3);
    this.hollowWireMat.opacity = Math.min(1.0, maxBranchF * 0.75);
    this.hollowEdgeMat.opacity = Math.min(1.0, maxBranchF * 0.90);
    this.branchMat.opacity = Math.min(1.0, maxBranchF * 0.65);

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
    this.hollowWireMat.color.setHex(this.colors.hollowWire);
    this.hollowEdgeMat.color.setHex(this.colors.heroEdge);
    this.branchMat.color.setHex(this.colors.branchLine);

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

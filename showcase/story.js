import * as THREE from 'three';

/**
 * CD-AVC Showcase v6
 * Theme W2 by default (Warm Charcoal & Monochromatic Off-White) / Switchable to W1 (Dark Green)
 * Direction A: "Thread"
 * Hero: Solid Tactile Rectangle with 3-Tier Crystallisation Lattice (Recursive Branching)
 * Stage 1: One shot, can fail (Root rectangle turns red)
 * Stage 2: More shots, no judgement (Rectangles bloom out 1 -> 2 -> 4 -> 8 in radial crystal lattice)
 * Stage 3: A cage that checks before it accepts (Sequential collapse 8 -> 4 -> 2 -> 1, vitrine cage seals accepted core)
 * 100% Scroll-Scrubbed Bidirectionally, Zero Autoplay
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

class ThreadStoryStage {
  constructor() {
    this.canvas = document.querySelector('#stage-canvas');
    if (!this.canvas) return;

    this.sentences = document.querySelectorAll('.story-sentence');
    this.scrollCue = document.querySelector('#scroll-cue');
    this.currentStage = 0;
    this.progress = 0;

    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    this.initTheme();
    this.initScene();
    this.initObjects();
    this.initScrollTrigger();
    this.initListeners();
    this.handleUrlParams();
    this.animate();
  }

  initTheme() {
    const urlParams = new URLSearchParams(window.location.search);
    // User preference: Love W2! Default to W2 unless explicitly requested w1
    const themeParam = (urlParams.get('theme') || 'w2').toLowerCase();
    this.isW2 = themeParam !== 'w1';

    if (this.isW2) {
      document.documentElement.setAttribute('data-theme', 'w2');
      document.body.classList.add('theme-w2');
    } else {
      document.documentElement.removeAttribute('data-theme');
      document.body.classList.remove('theme-w2');
    }

    // Update active state on theme buttons
    const btnW1 = document.querySelector('#btn-theme-w1');
    const btnW2 = document.querySelector('#btn-theme-w2');
    if (btnW1 && btnW2) {
      btnW1.classList.toggle('is-active', !this.isW2);
      btnW2.classList.toggle('is-active', this.isW2);
    }

    // Studio color palette tailored per theme
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
  }

  initScene() {
    this.scene = new THREE.Scene();

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    const fov = this.isMobile ? 42 : 38;
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
    const ambientLight = new THREE.AmbientLight(ambColor, 1.65);
    this.scene.add(ambientLight);

    // Key light: illuminates top and upper-right facets
    this.keyLight = new THREE.DirectionalLight(this.colors.keyLight, 2.3);
    this.keyLight.position.set(70, 85, 95);
    this.scene.add(this.keyLight);

    // Fill light: softens front-left facet
    this.fillLight = new THREE.DirectionalLight(this.colors.fillLight, 1.25);
    this.fillLight.position.set(-60, 25, 75);
    this.scene.add(this.fillLight);

    // Rim light: outlines silhouette and back edges
    this.rimLight = new THREE.DirectionalLight(this.colors.rimLight, 1.5);
    this.rimLight.position.set(-55, -45, -60);
    this.scene.add(this.rimLight);

    // Local Hero Point Light
    this.heroLight = new THREE.PointLight(this.colors.heroPoint, 1.2, 170);
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
    // 2. Crystallisation Lattice of Rectangles
    // Radial Balanced Recursive Tree: Root (1) -> Tier 1 (2) -> Tier 2 (4) -> Tier 3 (8)
    // Exactly 15 connected crystalline rectangles in balanced 3D space
    // Calibrated with 6-unit right shift on desktop to clear text column with 40px margin
    // -------------------------------------------------------------
    this.latticeGroup = new THREE.Group();
    this.latticeOffsetX = this.isMobile ? 0 : 6;
    this.latticeGroup.position.set(this.latticeOffsetX, 22, 0);
    this.latticeGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.latticeGroup);

    // Node configurations: Root (0), Tier 1 (1,2), Tier 2 (3,4,5,6), Tier 3 (7..14)
    this.nodeConfigs = [
      // Level 0 (Original Root Rectangle R0)
      { id: 0, level: 0, parent: -1, offset: [0, 0, 0], rot: [0, 0, 0], dims: [42, 24, 24] },

      // Level 1: 2 rectangles branching laterally from Root (R1A Right, R1B Left)
      { id: 1, level: 1, parent: 0, offset: [32, 0, 4], rot: [0, 0.08, -0.05], dims: [34, 19, 19] },
      { id: 2, level: 1, parent: 0, offset: [-32, 0, -4], rot: [0, -0.08, 0.05], dims: [34, 19, 19] },

      // Level 2: 2 rectangles branching from EACH Level 1 rectangle (4 total)
      // From Node 1:
      { id: 3, level: 2, parent: 1, offset: [20, 20, -8], rot: [0.08, 0.12, -0.12], dims: [28, 15, 15] },
      { id: 4, level: 2, parent: 1, offset: [20, -20, 8], rot: [-0.08, 0.12, 0.12], dims: [28, 15, 15] },
      // From Node 2:
      { id: 5, level: 2, parent: 2, offset: [-20, 20, 8], rot: [0.08, -0.12, 0.12], dims: [28, 15, 15] },
      { id: 6, level: 2, parent: 2, offset: [-20, -20, -8], rot: [-0.08, -0.12, -0.12], dims: [28, 15, 15] },

      // Level 3: 2 rectangles branching from EACH Level 2 rectangle (8 total)
      // From Node 3 (Top-Right):
      { id: 7, level: 3, parent: 3, offset: [15, 10, -6], rot: [0.10, 0.14, -0.14], dims: [22, 12, 12] },
      { id: 8, level: 3, parent: 3, offset: [5, 16, 8], rot: [0.06, 0.16, -0.08], dims: [22, 12, 12] },
      // From Node 4 (Bottom-Right):
      { id: 9, level: 3, parent: 4, offset: [15, -10, 6], rot: [-0.10, 0.14, 0.14], dims: [22, 12, 12] },
      { id: 10, level: 3, parent: 4, offset: [5, -16, -8], rot: [-0.06, 0.16, 0.08], dims: [22, 12, 12] },
      // From Node 5 (Top-Left):
      { id: 11, level: 3, parent: 5, offset: [-15, 10, 6], rot: [0.10, -0.14, 0.14], dims: [22, 12, 12] },
      { id: 12, level: 3, parent: 5, offset: [-5, 16, -8], rot: [0.06, -0.16, 0.08], dims: [22, 12, 12] },
      // From Node 6 (Bottom-Left):
      { id: 13, level: 3, parent: 6, offset: [-15, -10, -6], rot: [-0.10, -0.14, -0.14], dims: [22, 12, 12] },
      { id: 14, level: 3, parent: 6, offset: [-5, -16, 8], rot: [-0.06, -0.16, -0.08], dims: [22, 12, 12] },
    ];

    this.nodes = [];
    this.nodeConfigs.forEach((cfg) => {
      const nGroup = new THREE.Group();

      // Rectangular box geometry
      const [w, h, d] = cfg.dims;
      const geo = new THREE.BoxGeometry(w, h, d);
      const edgeGeo = new THREE.EdgesGeometry(geo);

      const mat = new THREE.MeshStandardMaterial({
        color: this.colors.heroBase,
        roughness: 0.28,
        metalness: 0.45,
        transparent: true,
        opacity: 1.0,
      });
      const mesh = new THREE.Mesh(geo, mat);
      nGroup.add(mesh);

      const edgeMat = new THREE.LineBasicMaterial({
        color: this.colors.heroEdge,
        transparent: true,
        opacity: this.isW2 ? 0.75 : 0.85,
      });
      const edge = new THREE.LineSegments(edgeGeo, edgeMat);
      nGroup.add(edge);

      nGroup.rotation.set(cfg.rot[0], cfg.rot[1], cfg.rot[2]);
      this.latticeGroup.add(nGroup);

      // Connector line linking to parent rectangle
      let connector = null;
      let connectorMat = null;
      let lineGeo = null;
      if (cfg.parent >= 0) {
        const linePositions = new Float32Array(6);
        lineGeo = new THREE.BufferGeometry();
        lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));

        connectorMat = new THREE.LineBasicMaterial({
          color: this.colors.connector,
          transparent: true,
          opacity: 0,
        });
        connector = new THREE.Line(lineGeo, connectorMat);
        connector.visible = false;
        this.latticeGroup.add(connector);
      }

      this.nodes.push({
        id: cfg.id,
        level: cfg.level,
        parent: cfg.parent,
        relOffset: new THREE.Vector3(...cfg.offset),
        group: nGroup,
        mesh: mesh,
        mat: mat,
        edgeMat: edgeMat,
        connector: connector,
        connectorMat: connectorMat,
        lineGeo: lineGeo,
      });
    });

    // Root node references for Stage 1 & accepted Stage 3
    this.rootNode = this.nodes[0];

    // -------------------------------------------------------------
    // 3. Stage 3 CD-AVC Verification Cage (Vitrine Enclosure)
    // Tailored to enclose the 42x24x24 root rectangle with precision
    // -------------------------------------------------------------
    this.cageGroup = new THREE.Group();
    this.cageGroup.visible = false;
    this.latticeGroup.add(this.cageGroup);

    const cageGeo = new THREE.BoxGeometry(50, 32, 32);
    const cageWireGeo = new THREE.EdgesGeometry(cageGeo);

    this.cageWireMat = new THREE.LineBasicMaterial({
      color: this.colors.cageWire,
      transparent: true,
      opacity: 0,
    });
    this.cageLines = new THREE.LineSegments(cageWireGeo, this.cageWireMat);
    this.cageGroup.add(this.cageLines);

    // Light Frosted Glass Vitrine Membrane
    const glassGeo = new THREE.BoxGeometry(48.5, 30.5, 30.5);
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
  }

  initScrollTrigger() {
    const triggerEl = document.querySelector('#story-section');
    if (!triggerEl || typeof window.ScrollTrigger === 'undefined') return;

    window.ScrollTrigger.create({
      trigger: triggerEl,
      start: 'top top',
      end: 'bottom bottom',
      scrub: 0.4,
      onUpdate: (self) => {
        this.updateProgress(self.progress);
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
      this.updateProgress(0);
      return;
    }

    if (scrollParam === 'results' || scrollParam === '1.0' || scrollParam === '1') {
      document.body.classList.add('view-results-snapshot');
      this.updateProgress(1.0);
    } else {
      const p = parseFloat(scrollParam);
      if (!isNaN(p)) {
        this.updateProgress(Math.max(0, Math.min(1, p)));
      }
    }
  }

  updateProgress(p) {
    this.progress = Math.max(0, Math.min(1, p));

    // Editorial Sentence Switching:
    // 0.00 - 0.34: Stage 0 (Single model: "One shot, can fail.")
    // 0.34 - 0.64: Stage 1 (Retry baseline: "More shots, no judgement.")
    // 0.64 - 1.00: Stage 2 (CD-AVC: "A cage that checks before it accepts.")
    let stageIndex = 0;
    if (this.progress >= 0.64) {
      stageIndex = 2;
    } else if (this.progress >= 0.34) {
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
      this.scrollCue.style.opacity = this.progress > 0.04 ? '0' : '0.6';
    }

    // Vertical travel position along thread
    const threadY = 22 - this.progress * 44;
    this.heroLight.position.set(0, threadY, 25);

    const stage0Sub = document.querySelector('[data-stage="0"] .accent-sub');

    // Subtle, unhurried isometric parallax (never flips or spins wildly)
    const scrubRotX = this.baseRotX + Math.sin(this.progress * Math.PI) * 0.12;
    const scrubRotY = this.baseRotY + (this.progress - 0.5) * 0.36;

    this.latticeGroup.position.set(this.latticeOffsetX, threadY, 0);
    this.latticeGroup.rotation.set(scrubRotX, scrubRotY, this.baseRotZ);

    // Responsive scaling to ensure whole radial lattice fits with generous margins
    const latticeScale = this.isMobile ? 0.66 : 0.80;
    this.latticeGroup.scale.setScalar(latticeScale);

    // Smoothstep interpolation helper
    const smoothstep = (min, max, val) => {
      const x = Math.max(0, Math.min(1, (val - min) / (max - min)));
      return x * x * (3 - 2 * x);
    };

    // -------------------------------------------------------------
    // PROGRESS PHASE FACTORS
    // -------------------------------------------------------------

    // 1. Stage 0: Fail Risk on Single Shot (p in [0.16, 0.32])
    const failRisk = smoothstep(0.16, 0.30, this.progress) * (1.0 - smoothstep(0.32, 0.35, this.progress));

    // 2. Stage 1: Crystallisation Growth (p in [0.34, 0.64])
    const g1 = smoothstep(0.34, 0.44, this.progress); // Level 1 blooms out
    const g2 = smoothstep(0.44, 0.54, this.progress); // Level 2 blooms out
    const g3 = smoothstep(0.54, 0.63, this.progress); // Level 3 blooms out

    // 3. Stage 2: CD-AVC Sequential Collapse (p in [0.64, 0.86])
    // Collapses in the exact reverse / sequential order:
    // Level 3 collapses first (0.65 -> 0.72)
    const c3 = 1.0 - smoothstep(0.65, 0.72, this.progress);
    // Level 2 collapses second (0.72 -> 0.79)
    const c2 = 1.0 - smoothstep(0.72, 0.79, this.progress);
    // Level 1 collapses third (0.79 -> 0.85)
    const c1 = 1.0 - smoothstep(0.79, 0.85, this.progress);

    // 4. Stage 3: Verification Acceptance & Cage Enclosure (p in [0.84, 0.92])
    const tAccept = smoothstep(0.83, 0.89, this.progress);
    const tCage = smoothstep(0.84, 0.91, this.progress);

    // Determine level factors and failure states
    let f1, f2, f3;
    let isFailing3 = false;
    let isFailing2 = false;
    let isFailing1 = false;

    if (this.progress < 0.64) {
      // Growth phase (Stage 1)
      f1 = g1;
      f2 = g2;
      f3 = g3;
    } else {
      // Collapse phase (Stage 2)
      f1 = c1;
      f2 = c2;
      f3 = c3;
      // Mark candidate shoots as failing invariants as they prune
      isFailing3 = this.progress >= 0.64 && c3 > 0.001;
      isFailing2 = this.progress >= 0.71 && c2 > 0.001;
      isFailing1 = this.progress >= 0.78 && c1 > 0.001;
    }

    const levelFactors = [1.0, f1, f2, f3];
    const levelFailing = [false, isFailing1, isFailing2, isFailing3];

    // -------------------------------------------------------------
    // UPDATE ROOT NODE (R0)
    // -------------------------------------------------------------
    if (this.progress < 0.34) {
      // Stage 0: Solid single block with presence. Red at fail moment.
      if (failRisk > 0.01) {
        const activeColor = new THREE.Color(this.colors.heroBase).lerp(
          new THREE.Color(this.colors.failRed),
          failRisk
        );
        this.rootNode.mat.color.copy(activeColor);
        this.rootNode.mat.emissive.setHex(this.colors.failRed).multiplyScalar(failRisk * 0.45);
        this.rootNode.edgeMat.color.setHex(this.colors.failRed);
        if (stage0Sub) stage0Sub.style.color = '#ff4747';
      } else {
        this.rootNode.mat.color.setHex(this.colors.heroBase);
        this.rootNode.mat.emissive.setHex(0x000000);
        this.rootNode.edgeMat.color.setHex(this.colors.heroEdge);
        if (stage0Sub) stage0Sub.style.color = '';
      }
    } else if (this.progress < 0.83) {
      if (stage0Sub) stage0Sub.style.color = '';
      this.rootNode.mat.color.setHex(this.colors.heroBase);
      this.rootNode.mat.emissive.setHex(0x000000);
      this.rootNode.edgeMat.color.setHex(this.colors.heroEdge);
    } else {
      if (stage0Sub) stage0Sub.style.color = '';
      // Stage 3 Verification: Root core illuminates in pure accepted color
      if (this.isW2) {
        // Monochromatic Luminous Off-White
        const targetColor = new THREE.Color(0xf4f4f2);
        this.rootNode.mat.color.copy(new THREE.Color(this.colors.heroBase).lerp(targetColor, tAccept));
        this.rootNode.mat.emissive.setHex(0xffffff).multiplyScalar(tAccept * 0.45);
        this.rootNode.edgeMat.color.copy(new THREE.Color(this.colors.heroEdge).lerp(new THREE.Color(0xffffff), tAccept));
      } else {
        // Phosphor Green
        const targetColor = new THREE.Color(0xd8ff64);
        this.rootNode.mat.color.copy(new THREE.Color(this.colors.heroBase).lerp(targetColor, tAccept));
        this.rootNode.mat.emissive.setHex(0xd8ff64).multiplyScalar(tAccept * 0.55);
        this.rootNode.edgeMat.color.setHex(0xd8ff64);
      }
    }

    // -------------------------------------------------------------
    // UPDATE RECURSIVE CHILD NODES & CONNECTORS (1 to 14)
    // -------------------------------------------------------------
    for (let i = 1; i < this.nodes.length; i++) {
      const node = this.nodes[i];
      const parentNode = this.nodes[node.parent];
      const f = levelFactors[node.level];
      const isFailing = levelFailing[node.level];

      if (f > 0.005) {
        node.group.visible = true;
        node.group.scale.setScalar(Math.max(0.001, f));

        // Position branches outward from parent by relative offset scaled by factor f
        node.group.position.x = parentNode.group.position.x + node.relOffset.x * f;
        node.group.position.y = parentNode.group.position.y + node.relOffset.y * f;
        node.group.position.z = parentNode.group.position.z + node.relOffset.z * f;

        // Material styling: turn red when failing invariants during collapse
        if (isFailing) {
          node.mat.color.setHex(this.colors.failRed);
          node.mat.emissive.setHex(this.colors.failRed).multiplyScalar(0.42);
          node.edgeMat.color.setHex(this.colors.failRed);
          if (node.connectorMat) {
            node.connectorMat.color.setHex(this.colors.failRed);
            node.connectorMat.opacity = Math.min(1.0, f * 0.90);
          }
        } else {
          node.mat.color.setHex(this.colors.heroBase);
          node.mat.emissive.setHex(0x000000);
          node.edgeMat.color.setHex(this.colors.heroEdge);
          if (node.connectorMat) {
            node.connectorMat.color.setHex(this.colors.connector);
            node.connectorMat.opacity = Math.min(1.0, f * 0.80);
          }
        }

        // Connector filament linking parent and child
        if (node.connector && node.lineGeo) {
          node.connector.visible = f > 0.02;
          const posAttr = node.lineGeo.attributes.position;
          posAttr.setXYZ(0, parentNode.group.position.x, parentNode.group.position.y, parentNode.group.position.z);
          posAttr.setXYZ(1, node.group.position.x, node.group.position.y, node.group.position.z);
          posAttr.needsUpdate = true;
        }
      } else {
        node.group.visible = false;
        node.group.scale.setScalar(0.001);
        node.group.position.copy(parentNode.group.position);
        if (node.connector) node.connector.visible = false;
      }
    }

    // -------------------------------------------------------------
    // CD-AVC VERIFICATION CAGE DESCENT & ENCLOSURE
    // -------------------------------------------------------------
    if (tCage > 0.001) {
      this.cageGroup.visible = true;
      // Descends from above and seals around Root Node
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

    // Theme Switcher Click Handlers (instant live switch preserving scroll & preview params)
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

    // Reapply theme colors to dynamic materials
    this.threadMat.color.setHex(this.colors.thread);
    this.keyLight.color.setHex(this.colors.keyLight);
    this.fillLight.color.setHex(this.colors.fillLight);
    this.rimLight.color.setHex(this.colors.rimLight);
    this.heroLight.color.setHex(this.colors.heroPoint);
    this.cageWireMat.color.setHex(this.colors.cageWire);
    this.cageGlassMat.color.setHex(this.colors.cageGlass);

    this.nodes.forEach((n) => {
      n.mat.color.setHex(this.colors.heroBase);
      n.edgeMat.color.setHex(this.colors.heroEdge);
      if (n.connectorMat) n.connectorMat.color.setHex(this.colors.connector);
    });

    // Update progress state with new theme colors
    this.updateProgress(this.progress);
  }

  onResize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    this.camera.fov = this.isMobile ? 42 : 38;
    this.camera.position.z = this.isMobile ? 260 : 230;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // Subtle smooth mouse parallax
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

    this.camera.position.x = this.mouse.x * 6;
    this.camera.position.y = -this.mouse.y * 4;

    // Subtly track hero position
    const currentHeroY = 22 - this.progress * 44;
    this.camera.lookAt(0, currentHeroY * 0.35, 0);

    // Confident pulsation when verified in Stage 3
    if (this.progress >= 0.85) {
      this.heroLight.intensity = 1.2 + Math.sin(Date.now() * 0.004) * 0.25;
    } else {
      this.heroLight.intensity = 1.2;
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

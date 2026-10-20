import * as THREE from 'three';

/**
 * CD-AVC Showcase v6
 * Dual-Theme Architecture (W1: Dark Green / W2: Warm Charcoal & Monochromatic Off-White)
 * Direction A: "Thread" with Judgement Moment (Wall of Cubes, Drops & Cage Enclosure)
 * 100% Scroll-Scrubbed Bidirectionally, Zero Autoplay, Solid Physical Presence
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
    const themeParam = (urlParams.get('theme') || 'w1').toLowerCase();
    this.isW2 = themeParam === 'w2';

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
          heroBase: 0x2c2a28,
          heroEdge: 0xe0ddd7,
          thread: 0x8e8d8a,
          dashes: 0x484643,
          keyLight: 0xfffaee,
          fillLight: 0x8a8782,
          rimLight: 0xebe8e1,
          heroPoint: 0xfffdfa,
          acceptedEmissive: 0xf4f4f2,
          acceptedCore: 0xeae7e1,
          cageWire: 0xf0ede6,
          cageGlass: 0xffffff,
          failRed: 0xff3838,
        }
      : {
          bg: 0x060807,
          heroBase: 0x19251e,
          heroEdge: 0xd8ff64,
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
  }

  initScene() {
    this.scene = new THREE.Scene();

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    const fov = this.isMobile ? 42 : 38;
    const camZ = this.isMobile ? 240 : 205;

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
    const ambColor = this.isW2 ? 0x22201e : 0x0e1511;
    const ambientLight = new THREE.AmbientLight(ambColor, 1.3);
    this.scene.add(ambientLight);

    // Key light: illuminates top and upper-right facets
    this.keyLight = new THREE.DirectionalLight(this.colors.keyLight, 2.2);
    this.keyLight.position.set(65, 85, 90);
    this.scene.add(this.keyLight);

    // Fill light: softens front-left facet so mass is tactile
    this.fillLight = new THREE.DirectionalLight(this.colors.fillLight, 0.9);
    this.fillLight.position.set(-55, 30, 80);
    this.scene.add(this.fillLight);

    // Rim light: outlines silhouette and back edges
    this.rimLight = new THREE.DirectionalLight(this.colors.rimLight, 1.3);
    this.rimLight.position.set(-65, -50, -60);
    this.scene.add(this.rimLight);

    // Hero Local Point Light
    this.heroLight = new THREE.PointLight(this.colors.heroPoint, 1.1, 160);
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

    // Base aesthetic rotation angles (isometric 3-facet view from first frame)
    this.baseRotX = 0.42;
    this.baseRotY = 0.58;
    this.baseRotZ = 0.08;

    // -------------------------------------------------------------
    // 2. Solid Hero Block (36x36x36, 2x larger, solid material)
    // -------------------------------------------------------------
    this.heroSize = 36;
    this.heroGeo = new THREE.BoxGeometry(this.heroSize, this.heroSize, this.heroSize);
    this.heroEdgeGeo = new THREE.EdgesGeometry(this.heroGeo);

    this.heroGroup = new THREE.Group();
    this.heroGroup.position.set(0, 22, 0);
    this.heroGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.heroGroup);

    this.heroCoreMat = new THREE.MeshStandardMaterial({
      color: this.colors.heroBase,
      roughness: 0.30,
      metalness: 0.50,
    });
    this.heroMesh = new THREE.Mesh(this.heroGeo, this.heroCoreMat);
    this.heroGroup.add(this.heroMesh);

    this.heroEdgeMat = new THREE.LineBasicMaterial({
      color: this.colors.heroEdge,
      transparent: true,
      opacity: this.isW2 ? 0.50 : 0.75,
    });
    this.heroEdge = new THREE.LineSegments(this.heroEdgeGeo, this.heroEdgeMat);
    this.heroGroup.add(this.heroEdge);

    // -------------------------------------------------------------
    // 3. Stage 2 Stacked Blocks (Retry Baseline: 3 stacked solid blocks)
    // -------------------------------------------------------------
    this.stackGroup = new THREE.Group();
    this.stackGroup.visible = false;
    this.stackGroup.position.set(0, 22, 0);
    this.stackGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.stackGroup);

    this.stackCubes = [];
    const stackYOffsets = [44, 0, -44];
    for (let i = 0; i < 3; i++) {
      const sGroup = new THREE.Group();
      const sMat = new THREE.MeshStandardMaterial({
        color: this.colors.heroBase,
        roughness: 0.32,
        metalness: 0.48,
        transparent: true,
        opacity: 1,
      });
      const sMesh = new THREE.Mesh(this.heroGeo, sMat);
      const sEdge = new THREE.LineSegments(this.heroEdgeGeo, this.heroEdgeMat);
      sGroup.add(sMesh);
      sGroup.add(sEdge);
      sGroup.position.y = stackYOffsets[i];
      // Distinct stagger rotation so all 3 blocks are immediately clear
      sGroup.rotation.y = (i - 1) * 0.14;
      this.stackGroup.add(sGroup);
      this.stackCubes.push({ group: sGroup, mat: sMat, baseY: stackYOffsets[i] });
    }

    // -------------------------------------------------------------
    // 4. Stage 3 Wall of Candidate Cubes (Judgement Moment: 3x3 Grid)
    // -------------------------------------------------------------
    this.wallGroup = new THREE.Group();
    this.wallGroup.visible = false;
    this.wallGroup.position.set(0, 22, 0);
    this.wallGroup.rotation.set(this.baseRotX, this.baseRotY, this.baseRotZ);
    this.scene.add(this.wallGroup);

    this.candidateSize = 26;
    this.candidateGeo = new THREE.BoxGeometry(this.candidateSize, this.candidateSize, this.candidateSize);
    this.candidateEdgeGeo = new THREE.EdgesGeometry(this.candidateGeo);

    this.candidateCubes = [];
    // 3x3 Grid: Center is index 4. Spacing: 40 units. Shifted slightly right (+8) to clear text.
    const spacing = 40;
    this.gridOffsetX = 8;
    let index = 0;
    for (let row = 1; row >= -1; row--) {
      for (let col = -1; col <= 1; col++) {
        const isCenter = row === 0 && col === 0;
        const posX = this.gridOffsetX + col * spacing;
        const posY = row * spacing;

        const cGroup = new THREE.Group();
        cGroup.position.set(posX, posY, 0);

        const cMat = new THREE.MeshStandardMaterial({
          color: this.colors.heroBase,
          roughness: 0.30,
          metalness: 0.50,
          transparent: true,
          opacity: 1,
        });
        const cMesh = new THREE.Mesh(this.candidateGeo, cMat);
        const cEdgeMat = new THREE.LineBasicMaterial({
          color: this.colors.heroEdge,
          transparent: true,
          opacity: this.isW2 ? 0.45 : 0.65,
        });
        const cEdge = new THREE.LineSegments(this.candidateEdgeGeo, cEdgeMat);
        cGroup.add(cMesh);
        cGroup.add(cEdge);

        this.wallGroup.add(cGroup);
        this.candidateCubes.push({
          group: cGroup,
          mat: cMat,
          edgeMat: cEdgeMat,
          isCenter: isCenter,
          basePos: new THREE.Vector3(posX, posY, 0),
          dropVelocity: 0.85 + (index % 3) * 0.25,
          tiltAngle: ((index % 4) - 1.5) * 0.28,
        });
        index++;
      }
    }

    // -------------------------------------------------------------
    // 5. Stage 3 CD-AVC Verification Cage (Enclosing candidate hero)
    // -------------------------------------------------------------
    this.cageGroup = new THREE.Group();
    this.cageGroup.visible = false;

    const cageOuterSize = 42;
    const cageGeo = new THREE.BoxGeometry(cageOuterSize, cageOuterSize, cageOuterSize);
    const cageWireGeo = new THREE.EdgesGeometry(cageGeo);

    this.cageWireMat = new THREE.LineBasicMaterial({
      color: this.colors.cageWire,
      transparent: true,
      opacity: 0,
    });
    this.cageLines = new THREE.LineSegments(cageWireGeo, this.cageWireMat);
    this.cageGroup.add(this.cageLines);

    // Light Frosted Glass Membrane
    const glassSize = 40.5;
    const glassGeo = new THREE.BoxGeometry(glassSize, glassSize, glassSize);
    this.cageGlassMat = new THREE.MeshStandardMaterial({
      color: this.colors.cageGlass,
      roughness: 0.15,
      metalness: 0.1,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.cageGlass = new THREE.Mesh(glassGeo, this.cageGlassMat);
    this.cageGroup.add(this.cageGlass);

    this.scene.add(this.cageGroup);
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

    // Continuous scroll rotation adding to the base isometric pose
    const scrubRotX = this.baseRotX + this.progress * Math.PI * 0.8;
    const scrubRotY = this.baseRotY + this.progress * Math.PI * 1.5;

    // =========================================================================
    // STAGE 1: SINGLE MODEL (0.00 - 0.34)
    // Opens on solid block with presence. Transitions to solid red at fail moment.
    // =========================================================================
    if (this.progress < 0.34) {
      this.heroGroup.visible = true;
      this.stackGroup.visible = false;
      this.wallGroup.visible = false;
      this.cageGroup.visible = false;

      this.heroGroup.position.set(0, threadY, 0);
      this.heroGroup.scale.setScalar(1.0);
      this.heroGroup.rotation.set(scrubRotX, scrubRotY, this.baseRotZ);

      // Fail risk transition (0.16 to 0.34)
      const failRisk = Math.max(0, Math.min(1, (this.progress - 0.16) / 0.16));
      if (failRisk > 0) {
        // Smoothly lerp to solid red
        const activeColor = new THREE.Color(this.colors.heroBase).lerp(
          new THREE.Color(this.colors.failRed),
          failRisk
        );
        this.heroCoreMat.color.copy(activeColor);
        this.heroCoreMat.emissive.setHex(this.colors.failRed).multiplyScalar(failRisk * 0.38);
        this.heroEdgeMat.color.setHex(this.colors.failRed);

        if (stage0Sub) stage0Sub.style.color = '#ff4747';
      } else {
        this.heroCoreMat.color.setHex(this.colors.heroBase);
        this.heroCoreMat.emissive.setHex(0x000000);
        this.heroEdgeMat.color.setHex(this.colors.heroEdge);

        if (stage0Sub) stage0Sub.style.color = '';
      }

      this.threadMat.opacity = this.isW2 ? 0.35 : 0.30;
    }
    // =========================================================================
    // STAGE 2: RETRY BASELINE (0.34 - 0.62)
    // "Retry = a few stacked blocks." 3 stacked solid blocks blind to judgement.
    // =========================================================================
    else if (this.progress < 0.62) {
      if (stage0Sub) stage0Sub.style.color = '';

      this.heroGroup.visible = false;
      this.stackGroup.visible = true;
      this.wallGroup.visible = false;
      this.cageGroup.visible = false;

      this.stackGroup.position.set(0, threadY, 0);
      this.stackGroup.scale.setScalar(1.0);
      // Maintain pristine isometric angle with subtle scroll tilt so all 3 blocks remain cleanly visible
      const stackTilt = (this.progress - 0.34) * 0.45;
      this.stackGroup.rotation.set(
        this.baseRotX + stackTilt * 0.2,
        this.baseRotY + stackTilt * 0.5,
        this.baseRotZ
      );

      // Stack assembly / slide into place (0.34 - 0.40)
      const stackSpread = Math.min(1.0, (this.progress - 0.34) / 0.06);
      this.stackCubes.forEach((c) => {
        c.group.position.y = c.baseY * stackSpread;
        c.mat.color.setHex(this.colors.heroBase);
        c.mat.emissive.setHex(0x000000);
        c.mat.opacity = 1.0;
      });

      this.threadMat.opacity = this.isW2 ? 0.35 : 0.30;
    }
    // =========================================================================
    // STAGE 3: CD-AVC & JUDGEMENT MOMENT (0.62 - 1.00)
    // Scale up candidate cubes until they fill the screen (wall of cubes).
    // Rejected ones turn red and drop out. Accepted one stays green (W1) or
    // luminous off-white (W2) and settles into cage. Scales back down for results.
    // =========================================================================
    else {
      if (stage0Sub) stage0Sub.style.color = '';

      this.heroGroup.visible = false;
      this.stackGroup.visible = false;
      this.wallGroup.visible = true;

      // Sub-phases:
      // Sub-phase A: Wall Expansion & Scale Up (0.62 -> 0.72)
      const pWall = Math.min(1.0, (this.progress - 0.62) / 0.10);

      // Sub-phase B: Judgement & Rejection Drop (0.72 -> 0.82)
      const pDrop = Math.max(0, Math.min(1, (this.progress - 0.72) / 0.10));

      // Sub-phase C: Cage Enclosure & Scaling Back Down (0.82 -> 0.92)
      const pCage = Math.max(0, Math.min(1, (this.progress - 0.82) / 0.10));

      // Scale: grows from 1.0 up to 1.45 to fill stage, then scales back down to 1.0 with cage
      let currentScale = 1.0 + pWall * 0.45;
      if (pCage > 0) {
        currentScale = 1.45 - pCage * 0.45;
      }
      this.wallGroup.scale.setScalar(currentScale);
      this.wallGroup.position.set(0, threadY, 0);
      this.wallGroup.rotation.set(
        this.baseRotX + (this.progress - 0.62) * 0.3,
        this.baseRotY + (this.progress - 0.62) * 0.6,
        this.baseRotZ
      );

      // Animate each of the 9 candidate cubes
      this.candidateCubes.forEach((c) => {
        if (c.isCenter) {
          // Center accepted cube stays rock-solid
          c.group.position.copy(c.basePos);
          c.group.scale.setScalar(1.0);
          c.mat.opacity = 1.0;

          if (pDrop > 0.05) {
            if (this.isW2) {
              // W2: Pure Luminous Monochromatic Off-White
              c.mat.color.setHex(0xf4f4f2);
              c.mat.emissive.setHex(0xffffff).multiplyScalar(0.40);
              c.edgeMat.color.setHex(0xffffff);
            } else {
              // W1: Pure Vivid Phosphor Green
              c.mat.color.setHex(0xd8ff64);
              c.mat.emissive.setHex(0xd8ff64).multiplyScalar(0.55);
              c.edgeMat.color.setHex(0xd8ff64);
            }
          } else {
            c.mat.color.setHex(this.colors.heroBase);
            c.mat.emissive.setHex(0x000000);
            c.edgeMat.color.setHex(this.colors.heroEdge);
          }
        } else {
          // The 8 rejected cubes
          if (pDrop > 0) {
            // Turn solid red and drop out downwards
            c.mat.color.setHex(this.colors.failRed);
            c.mat.emissive.setHex(this.colors.failRed).multiplyScalar(0.40);
            c.edgeMat.color.setHex(this.colors.failRed);

            // Smooth drop acceleration downwards
            const dropDistance = Math.pow(pDrop, 2) * 220 * c.dropVelocity;
            c.group.position.x = c.basePos.x + c.tiltAngle * dropDistance * 0.25;
            c.group.position.y = c.basePos.y - dropDistance;
            c.group.rotation.z = c.tiltAngle * pDrop * 2.0;

            // Fade out
            const fadeAlpha = Math.max(0, 1.0 - pDrop * 1.25);
            c.mat.opacity = fadeAlpha;
            c.edgeMat.opacity = fadeAlpha * 0.5;
            c.group.visible = fadeAlpha > 0.01;
          } else {
            c.group.visible = true;
            c.group.position.copy(c.basePos);
            c.group.rotation.set(0, 0, 0);
            c.group.scale.setScalar(1.0);
            c.mat.color.setHex(this.colors.heroBase);
            c.mat.emissive.setHex(0x000000);
            c.mat.opacity = 1.0;
            c.edgeMat.color.setHex(this.colors.heroEdge);
            c.edgeMat.opacity = this.isW2 ? 0.45 : 0.65;
          }
        }
      });

      // Verification Cage Descent & Tight Enclosure
      if (pCage > 0) {
        this.cageGroup.visible = true;
        this.cageGroup.position.set(this.gridOffsetX, threadY, 0);
        this.cageGroup.rotation.copy(this.wallGroup.rotation);
        this.cageGroup.scale.setScalar(currentScale);

        // Descend from top and seal
        const cageDrop = (1.0 - pCage) * 45;
        this.cageGroup.position.y = threadY + cageDrop;

        const cageAlpha = Math.min(1.0, pCage * 1.5);
        this.cageWireMat.opacity = cageAlpha * (this.isW2 ? 0.85 : 0.90);
        this.cageGlassMat.opacity = cageAlpha * (this.isW2 ? 0.15 : 0.09);

        this.threadMat.opacity = (this.isW2 ? 0.35 : 0.30) + pCage * 0.25;
      } else {
        this.cageGroup.visible = false;
        this.cageWireMat.opacity = 0;
        this.cageGlassMat.opacity = 0;
      }
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
    this.heroCoreMat.color.setHex(this.colors.heroBase);
    this.heroEdgeMat.color.setHex(this.colors.heroEdge);
    this.keyLight.color.setHex(this.colors.keyLight);
    this.fillLight.color.setHex(this.colors.fillLight);
    this.rimLight.color.setHex(this.colors.rimLight);
    this.heroLight.color.setHex(this.colors.heroPoint);
    this.cageWireMat.color.setHex(this.colors.cageWire);
    this.cageGlassMat.color.setHex(this.colors.cageGlass);

    // Update progress state with new theme colors
    this.updateProgress(this.progress);
  }

  onResize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.isMobile = window.innerWidth <= 860 || document.body.classList.contains('is-mobile-preview');
    this.camera.fov = this.isMobile ? 42 : 38;
    this.camera.position.z = this.isMobile ? 240 : 205;
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
      this.heroLight.intensity = 1.1 + Math.sin(Date.now() * 0.004) * 0.25;
    } else {
      this.heroLight.intensity = 1.1;
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

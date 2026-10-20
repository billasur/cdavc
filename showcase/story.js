import * as THREE from 'three';

/**
 * CD-AVC Showcase v6
 * Direction A: "Thread"
 * Stripped-back editorial keynote architecture.
 * Continuous thread line with Three.js hero scrubbed bidirectionally.
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

    this.initScene();
    this.initHero();
    this.initScrollTrigger();
    this.initListeners();
    this.handleUrlScroll();
    this.animate();
  }

  initScene() {
    this.scene = new THREE.Scene();

    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

    this.camera = new THREE.PerspectiveCamera(38, width / height, 1, 1000);
    this.camera.position.set(0, 0, 200);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setSize(width, height, false);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Soft, realistic lighting (Apple keynote feel)
    const ambientLight = new THREE.AmbientLight(0x121714, 1.2);
    this.scene.add(ambientLight);

    this.keyLight = new THREE.DirectionalLight(0xf5f7f5, 1.6);
    this.keyLight.position.set(45, 55, 110);
    this.scene.add(this.keyLight);

    this.rimLight = new THREE.DirectionalLight(0xd8ff64, 0.85);
    this.rimLight.position.set(-50, -40, -50);
    this.scene.add(this.rimLight);

    // Hero Local Point Light
    this.heroLight = new THREE.PointLight(0xd8ff64, 1.1, 120);
    this.scene.add(this.heroLight);
  }

  initHero() {
    // 1. The Continuous Vertical Thread Line
    // Extended past visible frustum top and bottom
    const threadPoints = [
      new THREE.Vector3(0, 110, 0),
      new THREE.Vector3(0, -110, 0),
    ];
    const threadGeo = new THREE.BufferGeometry().setFromPoints(threadPoints);
    this.threadMat = new THREE.LineBasicMaterial({
      color: 0xd8ff64,
      transparent: true,
      opacity: 0.28,
    });
    this.threadLine = new THREE.Line(threadGeo, this.threadMat);
    this.scene.add(this.threadLine);

    // Subtle Guide Dashes on the Thread
    const dashPoints = [];
    for (let y = 90; y >= -90; y -= 15) {
      dashPoints.push(new THREE.Vector3(-1.8, y, 0), new THREE.Vector3(1.8, y, 0));
    }
    const dashGeo = new THREE.BufferGeometry().setFromPoints(dashPoints);
    const dashMat = new THREE.LineBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.12,
    });
    this.scene.add(new THREE.LineSegments(dashGeo, dashMat));

    // 2. The Hero Object (The Precision Code Token)
    // Small, subtle sizing: 18x18x18
    this.heroGroup = new THREE.Group();
    this.heroGroup.position.set(0, 24, 0); // Stage 1 aligned with headline

    const cubeGeo = new THREE.BoxGeometry(18, 18, 18);
    this.heroCoreMat = new THREE.MeshStandardMaterial({
      color: 0x0c110e,
      roughness: 0.28,
      metalness: 0.82,
    });
    this.heroMesh = new THREE.Mesh(cubeGeo, this.heroCoreMat);
    this.heroGroup.add(this.heroMesh);

    // Beveled Neon Wireframe
    const wireGeo = new THREE.EdgesGeometry(cubeGeo);
    this.heroWireMat = new THREE.LineBasicMaterial({
      color: 0xd8ff64,
      transparent: true,
      opacity: 0.85,
    });
    this.heroWire = new THREE.LineSegments(wireGeo, this.heroWireMat);
    this.heroGroup.add(this.heroWire);

    // Inner Glowing Quantum Kernel
    const kernelGeo = new THREE.OctahedronGeometry(6.5, 0);
    this.kernelMat = new THREE.MeshBasicMaterial({
      color: 0xd8ff64,
      wireframe: true,
    });
    this.kernelMesh = new THREE.Mesh(kernelGeo, this.kernelMat);
    this.heroGroup.add(this.kernelMesh);

    this.scene.add(this.heroGroup);

    // 3. Stage 2: Retry Echoes (Ghosted attempts fanning out along the thread)
    this.echoes = [];
    const echoOffsets = [
      { x: 8, y: 16, rotZ: 0.2 },
      { x: -8, y: -16, rotZ: -0.2 },
    ];
    for (let i = 0; i < 2; i++) {
      const echoGroup = new THREE.Group();
      const echoMat = new THREE.MeshBasicMaterial({
        color: 0xd8ff64,
        wireframe: true,
        transparent: true,
        opacity: 0,
      });
      const echoMesh = new THREE.Mesh(cubeGeo, echoMat);
      echoGroup.add(echoMesh);
      echoGroup.visible = false;
      this.scene.add(echoGroup);
      this.echoes.push({ group: echoGroup, mat: echoMat, offset: echoOffsets[i] });
    }

    // 4. Stage 3: The CD-AVC Verification Cage
    // Proportioned to enclose the 18x18 cube (30x30x30)
    this.cageGroup = new THREE.Group();
    const cageGeo = new THREE.BoxGeometry(30, 30, 30);
    const cageWireGeo = new THREE.EdgesGeometry(cageGeo);
    this.cageMat = new THREE.LineBasicMaterial({
      color: 0xd8ff64,
      transparent: true,
      opacity: 0,
    });
    this.cageLines = new THREE.LineSegments(cageWireGeo, this.cageMat);
    this.cageGroup.add(this.cageLines);

    // Subtle Glass Membrane around Cage
    const cageGlassGeo = new THREE.BoxGeometry(29, 29, 29);
    this.cageGlassMat = new THREE.MeshBasicMaterial({
      color: 0xd8ff64,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.cageGlass = new THREE.Mesh(cageGlassGeo, this.cageGlassMat);
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
      scrub: 0.5,
      onUpdate: (self) => {
        this.updateProgress(self.progress);
      },
    });
  }

  handleUrlScroll() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('device') === 'mobile' || params.get('w') === '390') {
      document.body.classList.add('is-mobile-preview');
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
        const clampedP = Math.max(0, Math.min(1, p));
        this.updateProgress(clampedP);
      }
    }
  }

  updateProgress(p) {
    this.progress = Math.max(0, Math.min(1, p));

    // Determine Active Stage:
    // 0.00 - 0.35: Stage 1 (Single model)
    // 0.35 - 0.70: Stage 2 (Retry baseline)
    // 0.70 - 1.00: Stage 3 (CD-AVC Cage)
    let stageIndex = 0;
    if (this.progress >= 0.7) {
      stageIndex = 2;
    } else if (this.progress >= 0.35) {
      stageIndex = 1;
    }

    if (stageIndex !== this.currentStage) {
      this.currentStage = stageIndex;
      this.sentences.forEach((el, idx) => {
        el.classList.toggle('is-active', idx === stageIndex);
      });
    }

    // Hide scroll cue once user begins scrolling
    if (this.scrollCue) {
      this.scrollCue.style.opacity = this.progress > 0.05 ? '0' : '0.6';
    }

    // --- Continuous 3D Motion Down the Thread ---
    // Smooth vertical descent along thread from +24 to -24
    const threadY = 24 - this.progress * 48;
    this.heroGroup.position.y = threadY;
    this.heroLight.position.set(0, threadY, 20);

    // Subtle hero rotation along the thread
    this.heroGroup.rotation.x = this.progress * Math.PI * 1.5;
    this.heroGroup.rotation.y = this.progress * Math.PI * 2.0;
    this.kernelMesh.rotation.z = -this.progress * Math.PI * 3.0;

    // Stage 1: Single model, can fail (subtle red warning lerp at 0.22 - 0.35)
    const stage0Sub = document.querySelector('[data-stage="0"] .accent-sub');
    if (this.progress < 0.35) {
      const failRisk = Math.max(0, (this.progress - 0.22) / 0.13);
      const wireCol = new THREE.Color(0xd8ff64).lerp(new THREE.Color(0xff4747), failRisk);
      this.heroWireMat.color.copy(wireCol);
      this.heroCoreMat.emissive.setHex(0xff4747).multiplyScalar(failRisk * 0.35);

      if (stage0Sub) {
        if (failRisk > 0.05) {
          stage0Sub.style.color = '#ff6b6b';
        } else {
          stage0Sub.style.color = '';
        }
      }

      // Hide echoes and cage
      this.echoes.forEach((e) => {
        e.group.visible = false;
        e.mat.opacity = 0;
      });
      this.cageGroup.visible = false;
      this.cageMat.opacity = 0;
      this.cageGlassMat.opacity = 0;
      this.threadMat.opacity = 0.28;
    }
    // Stage 2: Retry baseline - more shots, no judgement (fanned out duplicate attempts)
    else if (this.progress < 0.7) {
      if (stage0Sub) stage0Sub.style.color = '';
      const subP = (this.progress - 0.35) / 0.35;
      this.heroWireMat.color.setHex(0xd8ff64);
      this.heroCoreMat.emissive.setHex(0x000000);

      // Show retry echoes branching off the thread with distinct offsets
      const echoAlpha = Math.sin(subP * Math.PI);
      this.echoes.forEach((e) => {
        e.group.visible = true;
        e.mat.opacity = echoAlpha * 0.40;
        e.group.position.set(
          e.offset.x * echoAlpha,
          threadY + e.offset.y * echoAlpha,
          0
        );
        e.group.rotation.x = this.heroGroup.rotation.x + 0.3;
        e.group.rotation.y = this.heroGroup.rotation.y + 0.3;
        e.group.rotation.z = e.offset.rotZ;
      });

      this.cageGroup.visible = false;
      this.cageMat.opacity = 0;
      this.cageGlassMat.opacity = 0;
      this.threadMat.opacity = 0.28;
    }
    // Stage 3: CD-AVC - a cage that checks before it accepts
    else {
      const subP = (this.progress - 0.7) / 0.3;
      this.heroWireMat.color.setHex(0xd8ff64);

      // Hide retry echoes
      this.echoes.forEach((e) => {
        e.group.visible = false;
        e.mat.opacity = 0;
      });

      // Cage descends, scales down to frame the hero, and seals tight
      this.cageGroup.visible = true;
      this.cageGroup.position.set(0, threadY, 0);

      const cageScale = Math.max(1.0, 1.4 - subP * 0.4);
      this.cageGroup.scale.setScalar(cageScale);

      const cageOpacity = Math.min(1.0, subP * 1.5);
      this.cageMat.opacity = cageOpacity * 0.9;
      this.cageGlassMat.opacity = cageOpacity * 0.08;
      this.threadMat.opacity = 0.28 + subP * 0.25;

      // When fully verified and sealed, illuminate the core with confident phosphor glow
      if (subP > 0.6) {
        const glowStrength = (subP - 0.6) / 0.4;
        this.heroCoreMat.emissive.setHex(0xd8ff64).multiplyScalar(glowStrength * 0.25);
      } else {
        this.heroCoreMat.emissive.setHex(0x000000);
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
  }

  onResize() {
    const rect = this.canvas.getBoundingClientRect();
    const width = rect.width || window.innerWidth * 0.54;
    const height = rect.height || window.innerHeight;

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

    this.camera.position.x = this.mouse.x * 5;
    this.camera.position.y = -this.mouse.y * 4;
    this.camera.lookAt(0, this.heroGroup ? this.heroGroup.position.y * 0.35 : 0, 0);

    // Subtle idle rotation
    if (this.heroMesh) {
      this.heroMesh.rotation.z += 0.002;
    }

    // Stage 3 lock glow pulsation when in final stage
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

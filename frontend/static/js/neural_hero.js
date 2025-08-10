// 3D Generational Network background animation for the homepage hero
// Adapted from neural_network_3d.html to render into #heroCanvas and behave
// as a non-interactive background (auto-rotate only).

(function initNeuralHero() {
  const canvas = document.getElementById('heroCanvas');
  if (!canvas) return; // nothing to do if hero canvas is absent
  if (canvas.dataset && canvas.dataset.interactive === '1') return; // skip background mode if interactive is enabled

  const ctx = canvas.getContext('2d');

  // Size canvas to its container with devicePixelRatio
  const container = canvas.parentElement; // .home-video-container
  function resizeToContainer() {
    if (!container) return;
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const width = Math.max(1, container.clientWidth);
    const height = Math.max(1, container.clientHeight);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  // Observe container size changes for responsive behavior
  const ro = new ResizeObserver(resizeToContainer);
  if (container) ro.observe(container);
  window.addEventListener('resize', resizeToContainer);
  resizeToContainer();

  // World/visual parameters
  const GENERATION_LIMIT = 10;
  const SECTION_COUNT = 30;
  let direction = 1; // +1 right, -1 left across sections
  const MIN_CHILDREN = 1;
  const MAX_CHILDREN = 12;
  const MAX_POSITION_TRIES = 20;

  // World extents (arbitrary units projected to screen)
  const WORLD_WIDTH = 100000;  // X spans sections across this width
  const WORLD_HEIGHT = 100000; // clamp Y within this height
  const SCREEN_MARGIN = 120; // world-margin when placing nodes

  // Visuals
  const NODE_RADIUS = 3;
  const NODE_OUTER_COLOR = 'rgb(50, 200, 255)';
  const NODE_INNER_COLOR = 'rgb(0, 0, 0)';
  const INNER_FILL_PERCENT = 0.8;
  const LINE_COLOR = 'rgb(120, 120, 140)';
  const BIRTH_GLOW_DURATION_MS = 900; // glow duration for new nodes
  const GLOW_COLOR = 'rgba(50, 200, 255, 1)';

  // Animation speeds (per frame, tuned for ~60fps)
  const GROWTH_SPEED = 0.2; // 0->1 growth in ~5 frames
  const FADE_SPEED = 0.02;  // fade-out in ~50 frames
  const SPAWN_INTERVAL_FRAMES = 5;

  // Simple perspective camera; auto-rotating only for background
  const PERSPECTIVE = 1000; // focal length
  let yaw = -0.5;   // rotate around Y
  let pitch = -0.12; // rotate around X
  let zoom = 0.35;   // start zoomed all the way out (min)
  const autoRotate = true; // keep rotating to add life

  // Camera Y pan and spawn Y offset (static in background mode)
  let cameraY = 0;
  let spawnYOffset = 0;

  // Data structures
  class Node {
    constructor(position, section, generation, parents = []) {
      this.id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      this.position = { x: position.x, y: position.y, z: position.z };
      this.section = section;
      this.generation = generation;
      this.parents = parents; // array of Node
      this.growth = 0.0; // 0..1 edge growth toward this node from its parents
      this.fade = 1.0;   // 1..0 visibility
      this.createdAt = performance.now(); // for birth glow
    }
  }

  let nodes = [];

  // Rotation helpers
  function rotateX(p, a) {
    const c = Math.cos(a), s = Math.sin(a);
    const y = p.y * c - p.z * s;
    const z = p.y * s + p.z * c;
    return { x: p.x, y, z };
  }
  function rotateY(p, a) {
    const c = Math.cos(a), s = Math.sin(a);
    const x = p.x * c + p.z * s;
    const z = -p.x * s + p.z * c;
    return { x, y: p.y, z };
  }

  function project(p) {
    const zRel = p.z; // no Z camera translation; keep depth for perspective
    const yRel = p.y - cameraY; // translate camera along Y (pan up/down)
    const denom = PERSPECTIVE + zRel;
    const scale = (PERSPECTIVE * zoom) / Math.max(1, denom);
    const cx = canvas.width / (window.devicePixelRatio || 1) / 2;
    const cy = canvas.height / (window.devicePixelRatio || 1) / 2;
    return { x: cx + p.x * scale, y: cy + yRel * scale };
  }

  // Root node at world center
  const root = new Node({ x: 0, y: 0, z: 0 }, 0, 0, []);
  root.growth = 1.0; // already visible
  nodes.push(root);

  function worldSectionBounds(sectionIndex) {
    const sectionWidth = WORLD_WIDTH / SECTION_COUNT;
    const left = -WORLD_WIDTH / 2 + sectionIndex * sectionWidth;
    const right = left + sectionWidth;
    return { left, right };
  }

  function clamp(val, min, max) { return Math.max(min, Math.min(max, val)); }
  function rand(min, max) { return min + Math.random() * (max - min); }

  function addChildren() {
    if (nodes.length === 0) return;

    const parent = nodes[nodes.length - 1];
    const parentSection = parent.section;
    let nextSection = parentSection + direction;
    if (nextSection < 0 || nextSection >= SECTION_COUNT) {
      direction *= -1;
      nextSection = parentSection + direction;
    }

    const { left, right } = worldSectionBounds(nextSection);
    const numChildren = Math.floor(rand(MIN_CHILDREN, MAX_CHILDREN + 1));

    for (let i = 0; i < numChildren; i++) {
      let childPos = null;
      for (let t = 0; t < MAX_POSITION_TRIES; t++) {
        const x = rand(clamp(left + SCREEN_MARGIN, -WORLD_WIDTH/2, WORLD_WIDTH/2),
                       clamp(right - SCREEN_MARGIN, -WORLD_WIDTH/2, WORLD_WIDTH/2));
        const y = rand(-WORLD_HEIGHT/2 + SCREEN_MARGIN, WORLD_HEIGHT/2 - SCREEN_MARGIN) + spawnYOffset;
        const z = rand(-180, 180); // modest depth jitter
        childPos = { x, y, z };
        break; // accept first pick in background mode
      }
      const child = new Node(childPos, nextSection, parent.generation + 1, [parent]);
      nodes.push(child);
    }

    // Prune by generation limit
    let maxGen = -Infinity;
    for (const n of nodes) maxGen = Math.max(maxGen, n.generation);
    const minAliveGen = maxGen - (GENERATION_LIMIT - 1);
    nodes = nodes.filter(n => n.generation >= minAliveGen || n.fade > 0.0);
  }

  function updateAndDraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Auto-rotate for background motion
    if (autoRotate) yaw += 0.0022;

    // Update growth and fade
    let maxGen = -Infinity;
    for (const n of nodes) maxGen = Math.max(maxGen, n.generation);
    const minAliveGen = maxGen - (GENERATION_LIMIT - 1);

    for (const n of nodes) {
      if (n.growth < 1.0) n.growth = Math.min(1.0, n.growth + GROWTH_SPEED);
      if (n.generation < minAliveGen) {
        n.fade = Math.max(0.0, n.fade - FADE_SPEED);
      } else {
        n.fade = 1.0;
      }
    }

    // Remove fully faded nodes
    nodes = nodes.filter(n => n.fade > 0.0);

    // Draw connections first (animated growth)
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = LINE_COLOR;

    for (const n of nodes) {
      for (const p of n.parents) {
        if (!nodes.includes(p)) continue;

        const endWorld = {
          x: p.position.x + (n.position.x - p.position.x) * n.growth,
          y: p.position.y + (n.position.y - p.position.y) * n.growth,
          z: p.position.z + (n.position.z - p.position.z) * n.growth,
        };

        const parentRot = rotateX(rotateY(p.position, yaw), pitch);
        const endRot = rotateX(rotateY(endWorld, yaw), pitch);

        const a = project(parentRot);
        const b = project(endRot);

        const alpha = Math.min(n.fade, p.fade);
        if (alpha <= 0) continue;

        ctx.globalAlpha = alpha * 0.75; // soften
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
    ctx.restore();

    // Draw nodes on top
    ctx.save();
    for (const n of nodes) {
      if (n.growth < 1.0) continue; // only fully grown nodes
      const pr = project(rotateX(rotateY(n.position, yaw), pitch));

      const alpha = n.fade;
      if (alpha <= 0) continue;

      // Birth glow (brief, decaying)
      const ageMs = performance.now() - (n.createdAt || 0);
      if (ageMs >= 0 && ageMs < BIRTH_GLOW_DURATION_MS) {
        const t = 1 - ageMs / BIRTH_GLOW_DURATION_MS; // 1 -> 0
        const glowRadius = NODE_RADIUS * (1.2 + 0.6 * t);
        const blur = 18 + 24 * t;
        ctx.save();
        ctx.globalAlpha = Math.min(1, alpha * (0.35 + 0.45 * t));
        ctx.fillStyle = GLOW_COLOR;
        ctx.shadowColor = GLOW_COLOR;
        ctx.shadowBlur = blur;
        ctx.beginPath();
        ctx.arc(pr.x, pr.y, glowRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // Outer filled circle
      ctx.globalAlpha = alpha;
      ctx.fillStyle = NODE_OUTER_COLOR;
      ctx.beginPath();
      ctx.arc(pr.x, pr.y, NODE_RADIUS, 0, Math.PI * 2);
      ctx.fill();

      // Inner fill
      const innerR = Math.max(0, NODE_RADIUS * INNER_FILL_PERCENT);
      if (innerR > 0) {
        ctx.fillStyle = NODE_INNER_COLOR;
        ctx.beginPath();
        ctx.arc(pr.x, pr.y, innerR, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  // Spawn + render loop
  let frameCount = 0;
  function loop() {
    frameCount += 1;
    if (frameCount % SPAWN_INTERVAL_FRAMES === 0) addChildren();
    updateAndDraw();
    requestAnimationFrame(loop);
  }
  loop();

  // No mouse/scroll interactions are attached in background mode to avoid
  // interfering with page scrolling or CTA buttons.
})();

// Neural network 3D hero animation adapted for the homepage canvas container
// Encapsulated to avoid polluting the global scope
(function(){
    function initHeroNetwork3D(canvas){
        if(!canvas) return;

        const ctx = canvas.getContext('2d');

        // Responsive sizing based on the canvas' container
        function resize(){
            const dpr = Math.max(1, window.devicePixelRatio || 1);
            const rect = canvas.getBoundingClientRect();
            const width = Math.max(1, Math.floor(rect.width));
            const height = Math.max(1, Math.floor(rect.height));
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }
        const ro = new ResizeObserver(resize);
        ro.observe(canvas);
        resize();

        // World/visual parameters
        const GENERATION_LIMIT = 10;
        const SECTION_COUNT = 30;
        let direction = 1;
        const MIN_CHILDREN = 1;
        const MAX_CHILDREN = 12;
        const MAX_POSITION_TRIES = 20;

        // World extents
        const WORLD_WIDTH = 2400;
        const WORLD_HEIGHT = 1400;
        const SCREEN_MARGIN = 120;

        // Visuals
        const NODE_RADIUS = 3;
        const NODE_OUTER_COLOR = 'rgb(50, 200, 255)';
        const NODE_INNER_COLOR = 'rgb(0, 0, 0)';
        const INNER_FILL_PERCENT = 0.8;
        const LINE_COLOR = 'rgb(120, 120, 140)';
        const BIRTH_GLOW_DURATION_MS = 900;
        const GLOW_COLOR = 'rgba(50, 200, 255, 1)';

        // Animation speeds
        const GROWTH_SPEED = 0.2;
        const FADE_SPEED = 0.02;
        const SPAWN_INTERVAL_FRAMES = 5;

        // Camera + controls
        const PERSPECTIVE = 1000;
        let yaw = -0.5;
        let pitch = -0.12;
        let zoom = 0.35;
        let autoRotate = true;
        let cameraY = 0;
        let spawnYOffset = 0;
        const Y_PAN_SPEED = 0.5;
        const CAMERA_Y_MIN = -600;
        const CAMERA_Y_MAX = 600;

        // Interaction state
        let isDragging = false;
        let lastMouseX = 0;
        let lastMouseY = 0;

        class Node {
            constructor(position, section, generation, parents = []){
                this.id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
                this.position = { x: position.x, y: position.y, z: position.z };
                this.section = section;
                this.generation = generation;
                this.parents = parents;
                this.growth = 0.0;
                this.fade = 1.0;
                this.createdAt = performance.now();
            }
        }

        let nodes = [];

        function rotateX(p, a){
            const c = Math.cos(a), s = Math.sin(a);
            const y = p.y * c - p.z * s;
            const z = p.y * s + p.z * c;
            return { x: p.x, y, z };
        }
        function rotateY(p, a){
            const c = Math.cos(a), s = Math.sin(a);
            const x = p.x * c + p.z * s;
            const z = -p.x * s + p.z * c;
            return { x, y: p.y, z };
        }

        function project(p){
            const zRel = p.z;
            const yRel = p.y - cameraY;
            const denom = PERSPECTIVE + zRel;
            const scale = (PERSPECTIVE * zoom) / Math.max(1, denom);
            const cx = canvas.clientWidth / 2;
            const cy = canvas.clientHeight / 2;
            return { x: cx + p.x * scale, y: cy + yRel * scale };
        }

        // Root node
        const root = new Node({ x: 0, y: 0, z: 0 }, 0, 0, []);
        root.growth = 1.0;
        nodes.push(root);

        function worldSectionBounds(sectionIndex){
            const sectionWidth = WORLD_WIDTH / SECTION_COUNT;
            const left = -WORLD_WIDTH / 2 + sectionIndex * sectionWidth;
            const right = left + sectionWidth;
            return { left, right };
        }
        function clamp(val, min, max){ return Math.max(min, Math.min(max, val)); }
        function rand(min, max){ return min + Math.random() * (max - min); }

        function addChildren(){
            if (nodes.length === 0) return;
            const parent = nodes[nodes.length - 1];
            const parentSection = parent.section;
            let nextSection = parentSection + direction;
            if (nextSection < 0 || nextSection >= SECTION_COUNT){
                direction *= -1;
                nextSection = parentSection + direction;
            }
            const { left, right } = worldSectionBounds(nextSection);
            const numChildren = Math.floor(rand(MIN_CHILDREN, MAX_CHILDREN + 1));
            for (let i = 0; i < numChildren; i++){
                let childPos = null;
                for (let t = 0; t < MAX_POSITION_TRIES; t++){
                    const x = rand(clamp(left + SCREEN_MARGIN, -WORLD_WIDTH/2, WORLD_WIDTH/2),
                                   clamp(right - SCREEN_MARGIN, -WORLD_WIDTH/2, WORLD_WIDTH/2));
                    const y = rand(-WORLD_HEIGHT/2 + SCREEN_MARGIN, WORLD_HEIGHT/2 - SCREEN_MARGIN) + spawnYOffset;
                    const z = rand(-180, 180);
                    childPos = { x, y, z };
                    break;
                }
                const child = new Node(childPos, nextSection, parent.generation + 1, [parent]);
                nodes.push(child);
            }
            // Prune by generation
            let maxGen = -Infinity;
            for (const n of nodes) maxGen = Math.max(maxGen, n.generation);
            const minAliveGen = maxGen - (GENERATION_LIMIT - 1);
            nodes = nodes.filter(n => n.generation >= minAliveGen || n.fade > 0.0);
        }

        function updateAndDraw(){
            ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
            if (autoRotate) yaw += 0.0022;

            // Growth/fade
            let maxGen = -Infinity;
            for (const n of nodes) maxGen = Math.max(maxGen, n.generation);
            const minAliveGen = maxGen - (GENERATION_LIMIT - 1);
            for (const n of nodes){
                if (n.growth < 1.0) n.growth = Math.min(1.0, n.growth + GROWTH_SPEED);
                if (n.generation < minAliveGen) n.fade = Math.max(0.0, n.fade - FADE_SPEED);
                else n.fade = 1.0;
            }
            nodes = nodes.filter(n => n.fade > 0.0);

            // Precompute rotations
            const rotated = new Map();
            for (const n of nodes){
                const r1 = rotateY(n.position, yaw);
                const r2 = rotateX(r1, pitch);
                rotated.set(n.id, r2);
            }

            // Edges
            ctx.save();
            ctx.lineWidth = 1;
            ctx.strokeStyle = LINE_COLOR;
            for (const n of nodes){
                for (const p of n.parents){
                    if (!nodes.includes(p)) continue;
                    const endWorld = {
                        x: p.position.x + (n.position.x - p.position.x) * n.growth,
                        y: p.position.y + (n.position.y - p.position.y) * n.growth,
                        z: p.position.z + (n.position.z - p.position.z) * n.growth,
                    };
                    const parentRot = rotateX(rotateY(p.position, yaw), pitch);
                    const endRot = rotateX(rotateY(endWorld, yaw), pitch);
                    const a = project(parentRot);
                    const b = project(endRot);
                    const alpha = Math.min(n.fade, p.fade);
                    if (alpha <= 0) continue;
                    ctx.globalAlpha = alpha * 0.75;
                    ctx.beginPath();
                    ctx.moveTo(a.x, a.y);
                    ctx.lineTo(b.x, b.y);
                    ctx.stroke();
                }
            }
            ctx.restore();

            // Nodes
            ctx.save();
            for (const n of nodes){
                if (n.growth < 1.0) continue;
                const pr = project(rotateX(rotateY(n.position, yaw), pitch));
                const alpha = n.fade;
                if (alpha <= 0) continue;

                // Birth glow
                const ageMs = performance.now() - (n.createdAt || 0);
                if (ageMs >= 0 && ageMs < BIRTH_GLOW_DURATION_MS){
                    const t = 1 - ageMs / BIRTH_GLOW_DURATION_MS;
                    const glowRadius = NODE_RADIUS * (1.2 + 0.6 * t);
                    const blur = 18 + 24 * t;
                    ctx.save();
                    ctx.globalAlpha = Math.min(1, alpha * (0.35 + 0.45 * t));
                    ctx.fillStyle = GLOW_COLOR;
                    ctx.shadowColor = GLOW_COLOR;
                    ctx.shadowBlur = blur;
                    ctx.beginPath();
                    ctx.arc(pr.x, pr.y, glowRadius, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                }

                // Outer node
                ctx.globalAlpha = alpha;
                ctx.fillStyle = NODE_OUTER_COLOR;
                ctx.beginPath();
                ctx.arc(pr.x, pr.y, NODE_RADIUS, 0, Math.PI * 2);
                ctx.fill();

                // Inner fill
                const innerR = Math.max(0, NODE_RADIUS * INNER_FILL_PERCENT);
                if (innerR > 0){
                    ctx.fillStyle = NODE_INNER_COLOR;
                    ctx.beginPath();
                    ctx.arc(pr.x, pr.y, innerR, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            ctx.restore();
        }

        // Loop
        let frameCount = 0;
        function loop(){
            frameCount += 1;
            if (frameCount % SPAWN_INTERVAL_FRAMES === 0) addChildren();
            updateAndDraw();
            requestAnimationFrame(loop);
        }
        loop();

        // Interactions
        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
        });
        window.addEventListener('mouseup', () => { isDragging = false; });
        window.addEventListener('mouseleave', () => { isDragging = false; });
        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - lastMouseX;
            const dy = e.clientY - lastMouseY;
            lastMouseX = e.clientX;
            lastMouseY = e.clientY;
            yaw += dx * 0.005;
            pitch += dy * 0.005;
            const maxPitch = Math.PI / 2 - 0.05;
            if (pitch > maxPitch) pitch = maxPitch;
            if (pitch < -maxPitch) pitch = -maxPitch;
        });
        canvas.addEventListener('wheel', (e) => {
            const mainContainer = document.querySelector('.main-container');
            const snapActive = !!(mainContainer && mainContainer.classList.contains('snap-enabled'));
            if (!snapActive) {
                // While snap is off, tie internal pan to container scroll to keep
                // nodes moving with the page. Do not consume the event.
                const dy = e.deltaY * Y_PAN_SPEED;
                cameraY = clamp(cameraY + dy, CAMERA_Y_MIN, CAMERA_Y_MAX);
                spawnYOffset += dy;
                return;
            }
            // When snap is active, let the container handle the wheel to move
            // between snap sections. Users can still drag to pan the hero.
        }, { passive: false });
        canvas.addEventListener('dblclick', () => {
            yaw = -0.5; pitch = -0.12; zoom = 0.35; cameraY = 0; spawnYOffset = 0;
        });
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space') autoRotate = !autoRotate;
        });
    }

    // Auto-init when DOM is ready
    document.addEventListener('DOMContentLoaded', function(){
        const canvas = document.getElementById('heroCanvas');
        if (canvas) initHeroNetwork3D(canvas);
    });
})();



/* ==========================================================================
   Geetha Jewellers — collection stage
   --------------------------------------------------------------------------
   Vertical scroll → horizontal cinematic movement of five physical displays.

   The section is a tall track with a sticky 100vh stage. Scroll progress
   through the track becomes a continuous slot value t (0 … 4):
       t = 0     NECKLACES centred
       t = 0.5   necklaces leaving to the left, rings arriving from the right
       t = 1     RINGS centred … and so on.
   Every display is positioned from its signed distance to the centre (i - t),
   so the choreography is physically tied to the scroll position: scroll slowly
   and it moves slowly, stop and it stops. A short inertia lerp only smooths
   the steps of a mouse wheel. When a display settles in the centre, a golden
   light sweep crosses its jewellery once.
   ========================================================================== */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ data
     `image`  transparent WebP/PNG of the whole display unit (dome, frame,
              pedestal with the engraved name, jewellery) — swap freely.
     `size`   height relative to --gj-hero-h when centred.
     `glints` greyscale mask of the stones / speculars (white = catches the light).
     `jewel`  [x, y, w, h] fractions of the image box that hold the jewellery
              (where the light sweep plays). See images/manifest.json.        */
  const collections = [
    { name: 'Necklaces',             image: 'images/necklace.webp',     glints: 'images/necklace-glints.png',     size: 1,    jewel: [0.1970, 0.3107, 0.6006, 0.4366] },
    { name: 'Rings',                 image: 'images/ring.webp',         glints: 'images/ring-glints.png',         size: 0.86, jewel: [0.2807, 0.3597, 0.4373, 0.2888] },
    { name: 'Earrings',              image: 'images/earrings.webp',     glints: 'images/earrings-glints.png',     size: 0.86, jewel: [0.2742, 0.3191, 0.4439, 0.3495] },
    { name: 'Bangles',               image: 'images/bangles.webp',      glints: 'images/bangles-glints.png',      size: 0.86, jewel: [0.2285, 0.2880, 0.5091, 0.4057] },
    { name: 'Diamond Pendant Sets',  image: 'images/pendant-set.webp',  glints: 'images/pendant-set-glints.png',  size: 0.86, jewel: [0.2415, 0.2525, 0.5091, 0.4564] },
  ];

  const SETTINGS = {
    holdStart: 0.06,     // share of the travel where the first display stays centred
    holdEnd: 0.14,       // share of the travel where the last display stays centred
    settle: 0.55,        // 0 = linear scroll mapping, 1 = full ease-in-out per transition
    smoothing: 11,       // inertia response (per second) — higher is snappier
    sweepDelay: 150,     // ms after a display arrives in the centre before the light sweep starts
    parallax: { env: 0.004, sheen: 0.07 },   // × stage width per slot
  };

  /* choreography keyframes at |offset| = 0, 1, 2, 3 slots from the centre */
  const DESKTOP = {
    x: [0, 0.26, 0.42, 0.56],          // × stage width
    y: [0, -0.08, -0.11, -0.13],       // × stage height (up = further back on the floor)
    scale: [1, 0.72, 0.55, 0.45],
    opacity: [1, 0.86, 0.42, 0],
    bright: [1, 0.965, 0.93, 0.9],     // depth is read from scale/opacity only - never blur, the jewellery stays sharp
  };
  const COMPACT = {
    x: [0, 0.4, 0.66, 0.8],
    y: [0, -0.09, -0.12, -0.14],
    scale: [1, 0.56, 0.42, 0.35],
    opacity: [1, 0.55, 0, 0],
    bright: [1, 0.95, 0.92, 0.9],
  };

  /* ---------------------------------------------------------------- setup */
  const section = document.querySelector('[data-stage]');
  if (!section) return;

  const $ = (sel) => section.querySelector(sel);
  const track = $('.gj-track');
  const stage = $('.gj-stage');
  const env = $('.gj-env');
  const bloom = $('.gj-light--bloom');
  const sheen = $('.gj-light--sheen');
  const floorGlow = $('.gj-light--floor');
  const mount = $('.gj-displays');
  const counter = $('[data-current]');
  const total = $('[data-total]');
  const progress = $('.gj-progress');
  const hint = $('.gj-hint');
  const announce = $('[data-announce]');

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const N = collections.length;
  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  const smoothstep = (f) => f * f * (3 - 2 * f);
  const pad2 = (n) => String(n).padStart(2, '0');

  total.textContent = pad2(N);

  /* display units --------------------------------------------------------- */
  const displays = collections.map((item, i) => {
    const el = document.createElement('div');
    el.className = 'gj-display';
    el.style.setProperty('--size', item.size || 1);

    const unit = document.createElement('div');
    unit.className = 'gj-display__unit';

    const shadow = document.createElement('span');
    shadow.className = 'gj-display__shadow';

    const img = new Image();
    img.className = 'gj-display__image';
    img.src = item.image;
    img.alt = `${item.name} display`;
    img.decoding = 'async';
    img.draggable = false;

    const reflection = new Image();
    reflection.className = 'gj-display__reflection';
    reflection.src = item.image;
    reflection.alt = '';
    reflection.setAttribute('aria-hidden', 'true');
    reflection.draggable = false;

    const sweep = document.createElement('div');
    sweep.className = 'gj-display__sweep';
    sweep.setAttribute('aria-hidden', 'true');
    const [jx, jy, jw, jh] = item.jewel || [0, 0, 1, 1];
    sweep.style.setProperty('--jx', jx);
    sweep.style.setProperty('--jy', jy);
    sweep.style.setProperty('--jw', jw);
    sweep.style.setProperty('--jh', jh);
    // absolute URL: a relative url() inside a custom property resolves against the stylesheet, not the page
    sweep.style.setProperty('--mask', `url("${new URL(item.image, document.baseURI).href}")`);
    sweep.appendChild(document.createElement('i'));
    sweep.addEventListener('animationend', () => sweep.classList.remove('is-on'));

    // diamond glints: the same pass masked by the display's luminance (bright stones), blurred to bloom
    const glints = sweep.cloneNode(true);
    glints.className = 'gj-display__sweep gj-display__sweep--glints';
    if (item.glints) glints.style.setProperty('--mask', `url("${new URL(item.glints, document.baseURI).href}")`);
    glints.addEventListener('animationend', () => glints.classList.remove('is-on'));

    unit.append(shadow, img, reflection, sweep, glints);
    el.appendChild(unit);
    mount.appendChild(el);

    const d = { el, unit, img, sweep, glints, z: -1, hidden: false, filter: '', loaded: img.complete && img.naturalWidth > 0 };
    if (!d.loaded) img.addEventListener('load', () => { d.loaded = true; maybeSweep(); }, { once: true });
    return d;
  });

  /* passive progress indicator  ━ ○ ○ ○ ○ ------------------------------------ */
  const dots = collections.map(() => {
    const dot = document.createElement('i');
    progress.appendChild(dot);
    return dot;
  });

  /* --------------------------------------------------------------- geometry */
  let trackTop = 0;
  let travel = 1;
  let W = 1;
  let H = 1;
  let compact = false;

  function measure() {
    const rect = track.getBoundingClientRect();
    trackTop = rect.top + window.scrollY;
    // the track carries one extra stage-height at its end: the curtain hold, during
    // which the stage stays pinned while the next section rises over it
    travel = Math.max(1, track.offsetHeight - stage.offsetHeight * 2);
    W = stage.clientWidth;
    H = stage.clientHeight;
    compact = W < 768 || (W < 1024 && H > W);
  }

  /* ---------------------------------------------------------------- scroll */
  let target = 0;        // slot value the scroll position asks for
  let current = 0;       // slot value being rendered (inertia)
  let activeIndex = -1;
  let rafId = 0;
  let lastTime = 0;
  let pinned = false;
  let listening = false;

  function eased(t) {
    const i = Math.floor(t);
    const f = t - i;
    return i + f + (smoothstep(f) - f) * SETTINGS.settle;
  }

  function readScroll() {
    const y = window.scrollY;
    const p = clamp((y - trackTop) / travel, 0, 1);
    pinned = y >= trackTop - 1 && y <= trackTop + travel + 1;
    const u = clamp((p - SETTINGS.holdStart) / (1 - SETTINGS.holdStart - SETTINGS.holdEnd), 0, 1);
    target = eased(u * (N - 1));
  }

  function tick(now) {
    rafId = 0;
    // rAF timestamps can precede the performance.now() taken in kick(): never let dt go negative
    const dt = clamp((now - lastTime) / 1000, 0, 0.064);
    lastTime = now;
    if (reduceMotion.matches) {
      current = target;
    } else {
      current += (target - current) * (1 - Math.exp(-dt * SETTINGS.smoothing));
      if (Math.abs(target - current) < 0.0006) current = target;
    }
    render(current);
    if (current !== target) rafId = requestAnimationFrame(tick);
  }

  function kick() {
    if (rafId) return;
    lastTime = performance.now();
    rafId = requestAnimationFrame(tick);
  }

  function onScroll() { readScroll(); kick(); }
  function attach() { if (!listening) { listening = true; window.addEventListener('scroll', onScroll, { passive: true }); } }
  function detach() { if (listening) { listening = false; window.removeEventListener('scroll', onScroll); } }

  /* ------------------------------------------------------------ light sweep */
  let sweptIndex = -1;
  let sweepTimer = 0;
  let litTimer = 0;

  function cancelSweepTimer() {
    if (sweepTimer) { clearTimeout(sweepTimer); sweepTimer = 0; }
  }

  function runSweep(i) {
    const d = displays[i];
    d.sweep.classList.remove('is-on');
    d.glints.classList.remove('is-on');
    void d.sweep.offsetWidth;            // restart the animations if they are still running
    d.sweep.classList.add('is-on');
    d.glints.classList.add('is-on');
    // the whole display glows very slightly while the light passes
    displays.forEach((o) => o.img.classList.remove('is-lit'));
    d.img.classList.add('is-lit');
    if (litTimer) clearTimeout(litTimer);
    litTimer = setTimeout(() => { litTimer = 0; d.img.classList.remove('is-lit'); }, 950);
  }

  /* Fires once every time a display arrives in the centre (re-armed after it has
     clearly left), whether the scroll has fully stopped or not. */
  function maybeSweep() {
    if (reduceMotion.matches) return;
    const idx = clamp(Math.round(current), 0, N - 1);
    const dist = Math.abs(current - idx);
    if (dist > 0.4) { sweptIndex = -1; cancelSweepTimer(); return; }
    if (dist > 0.3) { cancelSweepTimer(); return; }         // moved on before the sweep started
    if (dist > 0.06 || sweptIndex === idx || sweepTimer || !displays[idx].loaded) return;
    sweepTimer = setTimeout(() => {
      sweepTimer = 0;
      if (Math.abs(current - idx) < 0.3 && sweptIndex !== idx) {
        sweptIndex = idx;
        runSweep(idx);
      }
    }, SETTINGS.sweepDelay);
  }

  /* ---------------------------------------------------------------- render */
  function key(arr, a) {
    const i = Math.min(Math.floor(a), 2);
    const f = a - i;
    return arr[i] + (arr[i + 1] - arr[i]) * f;
  }

  function render(t) {
    const k = compact ? COMPACT : DESKTOP;
    const reduced = reduceMotion.matches;

    for (let i = 0; i < N; i++) {
      const d = displays[i];
      const off = i - t;
      const a = Math.min(Math.abs(off), 3);
      let transform;
      let opacity;
      let filter = '';

      if (reduced) {
        opacity = clamp(1 - a * 1.6, 0, 1);
        transform = 'translate3d(0,0,0)';
      } else {
        const x = (off < 0 ? -1 : 1) * key(k.x, a) * W;
        const y = key(k.y, a) * H;
        const s = key(k.scale, a);
        opacity = key(k.opacity, a);
        transform = `translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0) scale(${s.toFixed(4)})`;
        filter = `brightness(${key(k.bright, a).toFixed(3)})`;
      }

      d.unit.style.transform = transform;
      d.unit.style.opacity = opacity.toFixed(3);
      if (filter !== d.filter) { d.unit.style.filter = filter; d.filter = filter; }

      const z = 100 - Math.round(a * 10);
      if (z !== d.z) { d.el.style.zIndex = z; d.z = z; }

      const hidden = opacity <= 0.002;
      if (hidden !== d.hidden) { d.el.classList.toggle('is-hidden', hidden); d.hidden = hidden; }
    }

    // counter / announcement
    const idx = clamp(Math.round(t), 0, N - 1);
    const dist = Math.abs(t - idx);
    if (idx !== activeIndex) {
      activeIndex = idx;
      counter.textContent = pad2(idx + 1);
      announce.textContent = collections[idx].name;
    }

    // progress bars grow / shrink continuously with the scroll
    for (let i = 0; i < N; i++) {
      dots[i].style.setProperty('--on', clamp(1 - Math.abs(i - t), 0, 1).toFixed(3));
    }

    // hint fades as soon as the choreography starts
    hint.style.opacity = clamp(1 - t * 5, 0, 1).toFixed(3);

    // lighting: the arch bloom and the floor pool brighten when a display is presented,
    // the sheen drifts across the gold architecture, the environment barely moves
    const presented = 1 - clamp((dist - 0.08) / 0.3, 0, 1);
    bloom.style.opacity = (0.62 + 0.38 * presented).toFixed(3);
    floorGlow.style.opacity = (0.3 + 0.7 * presented).toFixed(3);
    if (!reduced) {
      env.style.transform = `translate3d(${(-t * W * SETTINGS.parallax.env).toFixed(2)}px,0,0) scale(1.05)`;
      sheen.style.transform = `translate3d(${(-t * W * SETTINGS.parallax.sheen).toFixed(2)}px,0,0)`;
    }

    maybeSweep();
  }

  /* ---------------------------------------------- keyboard (secondary only) */
  function goTo(index) {
    const i = clamp(index, 0, N - 1);
    const p = SETTINGS.holdStart + (i / (N - 1)) * (1 - SETTINGS.holdStart - SETTINGS.holdEnd);
    window.scrollTo({ top: Math.round(trackTop + p * travel), behavior: reduceMotion.matches ? 'auto' : 'smooth' });
  }

  window.addEventListener('keydown', (e) => {
    if (!pinned || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.target instanceof Element && e.target.closest('input, textarea, select, [contenteditable]')) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); goTo(Math.round(target) + 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(Math.round(target) - 1); }
  });

  /* --------------------------------------------------------------- lifecycle */
  let measureRaf = 0;
  function scheduleMeasure() {
    if (measureRaf) return;
    measureRaf = requestAnimationFrame(() => { measureRaf = 0; measure(); readScroll(); kick(); });
  }

  const io = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) { attach(); measure(); readScroll(); kick(); } else { detach(); }
  }, { rootMargin: '30% 0px' });

  measure();
  readScroll();
  current = target;                 // no fly-in when the page is (re)loaded mid-section
  render(current);
  io.observe(track);

  window.addEventListener('resize', scheduleMeasure);
  window.addEventListener('orientationchange', scheduleMeasure);
  window.addEventListener('load', scheduleMeasure);
  if ('ResizeObserver' in window) {
    const ro = new ResizeObserver(scheduleMeasure);
    ro.observe(document.documentElement);
    ro.observe(track);
  }
  reduceMotion.addEventListener?.('change', () => { current = target; render(current); });

  /* menu ------------------------------------------------------------------ */
  const menuBtn = $('.gj-menu-btn');
  const menu = document.querySelector('.gj-menu');
  if (menuBtn && menu) {
    const closeBtn = menu.querySelector('.gj-menu__close');
    let open = false;
    const setOpen = (next) => {
      if (next === open) return;
      open = next;
      menu.classList.toggle('is-open', open);
      menu.setAttribute('aria-hidden', String(!open));
      menuBtn.setAttribute('aria-expanded', String(open));
      menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      document.documentElement.classList.toggle('gj-menu-open', open);   // page scroll pauses while the menu is open
      if (open) { closeBtn && closeBtn.focus({ preventScroll: true }); }
      else { menuBtn.focus({ preventScroll: true }); }
    };
    menuBtn.addEventListener('click', () => setOpen(!open));
    if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));
    menu.addEventListener('click', (e) => {
      if (e.target.closest('a') || e.target === menu) setOpen(false);   // a link, or the empty backdrop
    });
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });
  }

  window.GJStage = { goTo, get index() { return activeIndex; } };
})();

/* ==========================================================================
   Geetha Jewellers — Phase-02 section animation controller (reusable)
   --------------------------------------------------------------------------
   One controller for every post-hero section instead of per-element listeners
   (spec §16). A section opts in with `data-section`; its children describe
   their own entrance with `data-reveal="left|right|up|fade"` and an optional
   `--d` transition delay. The section gets `.is-in` when ~a quarter of it is
   visible; scrolling back up past it removes the class again, so the CSS
   transitions play smoothly in reverse — never a hard reset (spec §5).

   `data-parallax="<px>"` on a child adds a gentle scroll-linked drift while
   the section is on screen. Everything is transform/opacity only, one passive
   scroll listener, rAF-throttled, and inert under prefers-reduced-motion.
   ========================================================================== */
(function () {
  'use strict';

  document.documentElement.classList.add('js');

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

  const sections = Array.from(document.querySelectorAll('[data-section]'));
  const smooth01 = (t) => t * t * (3 - 2 * t);

  /* reveal / graceful reverse (About-style sections) ----------------------- */
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.intersectionRatio >= 0.22) {
        e.target.classList.add('is-in');
      } else if (!e.isIntersecting && e.boundingClientRect.top > window.innerHeight * 0.9) {
        // the section is entirely below the viewport again (user scrolled back up):
        // release the state so the entrance can replay — transitions run in reverse
        e.target.classList.remove('is-in');
      }
    }
  }, { threshold: [0, 0.22] });

  sections.forEach((s) => io.observe(s));

  /* gentle parallax -------------------------------------------------------- */
  const layers = sections
    .map((s) => ({ s, el: s.querySelector('[data-parallax]') }))
    .filter((o) => o.el);

  /* pinned progress sections ----------------------------------------------
     A section with `data-progress` gets a continuous scroll progress written
     to --p (and an eased necklace/hero progress to --pn). Children with
     `data-at="0.x"` gain .is-past once progress passes their threshold and
     lose it again on reverse scroll, so every reveal plays smoothly both
     ways. `data-sweep-host` fires its one-shot sweep as the hero completes
     (re-armed when the user scrolls well back). When the sticky stage is
     unpinned by CSS (mobile), progress falls back to viewport traversal.   */
  const pins = Array.from(document.querySelectorAll('[data-progress]')).map((sec) => ({
    sec,
    sticky: sec.querySelector('[data-sticky]'),
    items: Array.from(sec.querySelectorAll('[data-at], [data-until]')).map((el) => ({
      el,
      at: el.dataset.at !== undefined ? parseFloat(el.dataset.at) : null,
      until: el.dataset.until !== undefined ? parseFloat(el.dataset.until) : null,
    })),
    // hero progress window (explode/emerge) - overridable per section
    pnStart: parseFloat(sec.dataset.pnStart) || 0.12,
    pnSpan: parseFloat(sec.dataset.pnSpan) || 0.56,
    sweepHost: sec.querySelector('[data-sweep-host]'),
    swept: false,
  }));

  /* curtain sections: a section with `data-curtain="#target"` rises over the
     pinned target (the hero stage). The target receives --cover (0..1, eased)
     so it can recede, and the section gains .is-settled once it has fully
     risen into place - its own choreography waits for that moment.      */
  const curtains = Array.from(document.querySelectorAll('[data-curtain]'))
    .map((el) => ({ el, target: document.querySelector(el.dataset.curtain) }))
    .filter((c) => c.target);

  let raf = 0;

  function apply() {
    raf = 0;
    const vh = window.innerHeight;

    for (const c of curtains) {
      const r = c.el.getBoundingClientRect();
      const raw = clamp((vh - r.top) / vh, 0, 1);
      c.target.style.setProperty('--cover', (reduceMotion.matches ? raw : smooth01(raw)).toFixed(4));
      // "settled" = the section has all but finished rising; its content
      // sequence begins here and completes as the last of the rise lands
      if (r.top <= vh * 0.42) c.el.classList.add('is-settled');
      else if (r.top > vh * 0.72) c.el.classList.remove('is-settled');
    }

    if (!reduceMotion.matches) {
      for (const { s, el } of layers) {
        const r = s.getBoundingClientRect();
        if (r.bottom < -120 || r.top > vh + 120) continue;
        const p = clamp((vh - r.top) / (vh + r.height), 0, 1);   // 0 → entering, 1 → left above
        const strength = parseFloat(el.dataset.parallax) || 14;
        el.style.transform = `translate3d(0, ${((p - 0.5) * -2 * strength).toFixed(2)}px, 0)`;
      }
    }

    for (const o of pins) {
      const r = o.sec.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) continue;
      let p;
      const pinned = o.sticky && getComputedStyle(o.sticky).position === 'sticky';
      if (pinned) {
        // the approach (section sliding into view) is the first 12% of the
        // timeline, so the editorial establishes as the section enters and the
        // pinned travel drives the remaining 88% (spec: content first).
        const travel = o.sec.offsetHeight - o.sticky.offsetHeight;
        if (r.top > 0) p = clamp((vh - r.top) / vh, 0, 1) * 0.12;
        else p = 0.12 + (travel > 2 ? clamp(-r.top / travel, 0, 1) : 1) * 0.88;
        o.sec.style.setProperty('--pn', smooth01(clamp((p - o.pnStart) / o.pnSpan, 0, 1)).toFixed(4));
      } else {
        // unpinned (mobile flow): milestones ride the full traversal, but the
        // hero completes its emergence while its scene is still on screen
        p = clamp(((vh - r.top) / (r.height + vh * 0.5)) * 1.15, 0, 1);
        o.sec.style.setProperty('--pn', smooth01(clamp((vh - r.top) / (vh * 1.05), 0, 1)).toFixed(4));
      }
      o.sec.style.setProperty('--p', p.toFixed(4));
      for (const it of o.items) {
        if (it.at !== null) it.el.classList.toggle('is-past', p >= it.at);
        if (it.until !== null) it.el.classList.toggle('is-out', p >= it.until);
      }
      o.sec.classList.toggle('is-settled', p >= 0.94);
      if (o.sweepHost) {
        if (p < 0.45) {
          o.swept = false;
        } else if (!o.swept && p >= 0.78 && !reduceMotion.matches) {
          o.swept = true;
          o.sweepHost.classList.remove('do-sweep');
          void o.sweepHost.offsetWidth;
          o.sweepHost.classList.add('do-sweep');
        }
      }
    }
  }

  function schedule() {
    if (!raf) raf = requestAnimationFrame(apply);
  }

  if (layers.length || pins.length || curtains.length) {
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    apply();
  }

  reduceMotion.addEventListener?.('change', () => {
    layers.forEach(({ el }) => { el.style.transform = ''; });
    schedule();
  });

  /* autoplay collection rails ----------------------------------------------
     `data-rail` hosts `[data-rail-item]` children plus optional
     `[data-rail-dots]`, `[data-rail-prev]`, `[data-rail-next]` controls.
     `data-direction="ltr|rtl"` sets the autoplay direction, `data-interval`
     the pace (ms). Autoplay runs only while the rail is on screen, pauses on
     hover / touch / focus and resumes a few seconds after the interaction
     ends, and never runs under prefers-reduced-motion. Every change fires a
     `railchange` event so later sections can sync a featured product.       */
  document.querySelectorAll('[data-rail]').forEach((rail) => {
    const items = Array.from(rail.querySelectorAll('[data-rail-item]'));
    if (items.length < 2) return;
    const dotsHost = rail.querySelector('[data-rail-dots]');
    const dots = [];
    if (dotsHost) {
      items.forEach(() => dots.push(dotsHost.appendChild(document.createElement('i'))));
    }
    const interval = parseInt(rail.dataset.interval, 10) || 2800;
    const step = rail.dataset.direction === 'rtl' ? -1 : 1;
    let active = Math.max(0, items.findIndex((el) => el.classList.contains('is-active')));
    let timer = 0;
    let resumeTimer = 0;
    let visible = false;

    // a rail inside a phased section only acts during its own phase: not yet
    // arrived (data-at without .is-past) or already folded away (.is-out)
    const railOn = () => !rail.classList.contains('is-out') &&
      (!rail.hasAttribute('data-at') || rail.classList.contains('is-past'));

    function render() {
      items.forEach((el, i) => el.classList.toggle('is-active', i === active));
      dots.forEach((d, i) => d.classList.toggle('is-active', i === active));
      rail.dispatchEvent(new CustomEvent('railchange', { detail: { index: active }, bubbles: true }));
    }

    function goTo(i) {
      active = (i + items.length) % items.length;
      render();
    }

    function start() {
      if (timer || reduceMotion.matches || !visible) return;
      timer = window.setInterval(() => { if (railOn()) goTo(active + step); }, interval);
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = 0; }
      if (resumeTimer) { clearTimeout(resumeTimer); resumeTimer = 0; }
    }

    function pauseThenResume() {
      stop();
      resumeTimer = window.setTimeout(start, 4000);
    }

    items.forEach((el, i) => el.addEventListener('click', () => { goTo(i); pauseThenResume(); }));
    // controls usually live inside the rail; `data-rail-scope` on an ancestor
    // lets sibling arrows (outside the list) drive it too
    const scope = rail.closest('[data-rail-scope]') || rail;
    scope.querySelector('[data-rail-prev]')?.addEventListener('click', () => { goTo(active - 1); pauseThenResume(); });
    scope.querySelector('[data-rail-next]')?.addEventListener('click', () => { goTo(active + 1); pauseThenResume(); });
    rail.addEventListener('pointerenter', stop);
    rail.addEventListener('pointerleave', () => { resumeTimer = window.setTimeout(start, 1200); });
    rail.addEventListener('focusin', stop);
    rail.addEventListener('focusout', () => { resumeTimer = window.setTimeout(start, 1200); });

    new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
      if (visible) start(); else stop();
    }, { threshold: 0.25 }).observe(rail);

    /* featured-piece sync: `data-rail-feature` names a region whose
       [data-f="..."] slots crossfade to the active item's data-* values     */
    const featureSel = rail.dataset.railFeature;
    if (featureSel) {
      const region = document.querySelector(featureSel);
      if (region) {
        let firstSync = true;
        const fill = () => {
          const d = items[active].dataset;
          region.querySelectorAll('[data-f]').forEach((slot) => {
            const v = d['f' + slot.dataset.f];
            if (v !== undefined) slot.innerHTML = v;
          });
        };
        rail.addEventListener('railchange', () => {
          if (firstSync) { firstSync = false; fill(); return; }
          region.classList.add('is-swapping');
          window.setTimeout(() => { fill(); region.classList.remove('is-swapping'); }, 230);
        });
      }
    }

    render();
  });

  /* collection-focus sync: a rail whose items carry `data-focus` gently
     emphasises the matching staged piece (and its `data-bkey` annotation)
     when the active card changes - selection never rearranges the stage    */
  document.querySelectorAll('[data-rail]').forEach((rail) => {
    if (!rail.querySelector('[data-focus]')) return;
    const scope = rail.closest('section') || document;
    rail.addEventListener('railchange', (e) => {
      // phased rails (gold vs silver collection) only steer the stage while
      // their own phase is on stage
      if (rail.classList.contains('is-out') ||
          (rail.hasAttribute('data-at') && !rail.classList.contains('is-past'))) return;
      const items = Array.from(rail.querySelectorAll('[data-rail-item]'));
      const key = items[e.detail.index]?.dataset.focus;
      scope.querySelectorAll('.is-focus').forEach((el) => el.classList.remove('is-focus'));
      if (!key) return;
      scope.querySelectorAll(`.gjbn__bangle--${key}, [data-bkey="${key}"]`)
        .forEach((el) => el.classList.add('is-focus'));
    });
  });

  /* pointer parallax: hosts with `data-pointer-parallax` get --mx/--my in
     [-1, 1] from the pointer position; layers consume them in CSS. Depth
     only - transforms, no filters - so the jewellery stays sharp.          */
  document.querySelectorAll('[data-pointer-parallax]').forEach((host) => {
    let raf = 0;
    let nx = 0;
    let ny = 0;
    host.addEventListener('pointermove', (e) => {
      if (reduceMotion.matches || e.pointerType === 'touch') return;
      const r = host.getBoundingClientRect();
      nx = clamp(((e.clientX - r.left) / r.width) * 2 - 1, -1, 1);
      ny = clamp(((e.clientY - r.top) / r.height) * 2 - 1, -1, 1);
      if (!raf) raf = requestAnimationFrame(() => {
        raf = 0;
        host.style.setProperty('--mx', nx.toFixed(3));
        host.style.setProperty('--my', ny.toFixed(3));
      });
    });
    host.addEventListener('pointerleave', () => {
      host.style.setProperty('--mx', '0');
      host.style.setProperty('--my', '0');
    });
  });

  /* drag-to-rotate: the whole hanging group turns a few degrees under the
     pointer and springs back on release (mouse/pen only - touch scrolls)   */
  document.querySelectorAll('[data-drag-rotate]').forEach((el) => {
    let startX = 0;
    let dragging = false;
    el.addEventListener('pointerdown', (e) => {
      if (reduceMotion.matches || e.pointerType === 'touch') return;
      dragging = true;
      startX = e.clientX;
      el.classList.remove('is-springing');
      el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const deg = clamp((e.clientX - startX) / 38, -5.5, 5.5);
      el.style.transform = `rotate(${deg.toFixed(2)}deg)`;
    });
    const release = () => {
      if (!dragging) return;
      dragging = false;
      el.classList.add('is-springing');
      el.style.transform = '';
      window.setTimeout(() => el.classList.remove('is-springing'), 950);
    };
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
  });
})();

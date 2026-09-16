/* ==========================================================================
   Geetha Jewellers — PHASE 01 · intro conductor
   --------------------------------------------------------------------------
   The film itself is pure CSS (css/intro.css). This file only: waits for the
   first plate to decode (so nothing pops in half-loaded), starts the
   timeline, performs the FLIP travel of the lockup into the exact header
   logo rect, swaps to the real logo, and removes the overlay. Reduced
   motion gets a short fade. A click skips ahead. No layout shift — the page
   renders normally beneath the fixed overlay.
   ========================================================================== */
(function () {
  'use strict';

  var root = document.documentElement;
  var gi = document.getElementById('gjintro');
  if (!gi) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add('gji-run');
  window.scrollTo(0, 0);

  var headerImg = document.querySelector('.gj-logo img');
  var lock = gi.querySelector('.gji__lock');
  var fin = gi.querySelector('.gji__final');
  var done = false;
  var travelled = false;

  function finish() {
    if (done) return;
    done = true;
    root.classList.add('gji-land');
    gi.classList.add('gji--out');
    window.setTimeout(function () {
      gi.remove();
      root.classList.remove('gji-run', 'gji-land');
    }, 540);
  }

  function travel() {
    if (travelled) { return; }
    travelled = true;
    if (!headerImg || !fin || !lock) { finish(); return; }
    var t = headerImg.getBoundingClientRect();
    if (!t.width) { finish(); return; }
    var f = fin.getBoundingClientRect();
    var l = lock.getBoundingClientRect();
    var s = t.width / f.width;
    var dx = (t.left + t.width / 2) - (l.left + l.width / 2);
    var dy = (t.top + t.height / 2) - (l.top + l.height / 2);
    gi.classList.add('gji--swap');
    lock.style.transition = 'transform 0.55s cubic-bezier(0.4, 0, 0.2, 1)';
    lock.style.transform = 'translate(' + dx.toFixed(1) + 'px,' + dy.toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
    window.setTimeout(finish, 420);
  }

  if (reduce) {
    gi.classList.add('gji--rm');
    window.setTimeout(finish, 1100);
    gi.addEventListener('click', finish, { once: true });
    return;
  }

  var started = false;
  function start() {
    if (started) return;
    started = true;
    gi.classList.add('play');
    window.setTimeout(travel, 2150);
  }

  var img = gi.querySelector('.gji__gold img');
  if (img && img.complete) {
    window.requestAnimationFrame(function () { window.requestAnimationFrame(start); });
  } else if (img && img.decode) {
    Promise.race([
      img.decode(),
      new Promise(function (r) { window.setTimeout(r, 350); }),
    ]).then(start, start);
  } else {
    window.setTimeout(start, 120);
  }

  gi.addEventListener('click', function () { travel(); }, { once: true });
})();

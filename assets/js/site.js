/* site.js — theme control, one shared scroll handler, scroll-spy. */
(function () {
  'use strict';

  var root = document.documentElement;
  var STORE = 'theme';                       // "light" | "dark" | absent = auto
  var ORDER = ['auto', 'light', 'dark'];

  function stored() {
    try { return localStorage.getItem(STORE) || 'auto'; } catch (e) { return 'auto'; }
  }
  function apply(mode) {
    if (mode === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', mode);
    var dark = mode === 'dark' || (mode === 'auto' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#141311' : '#FBFAF8');
    document.dispatchEvent(new CustomEvent('themechange', { detail: { mode: mode, dark: dark } }));
  }

  var btn = document.querySelector('.theme-toggle');
  if (btn) {
    var mode = stored();
    var label = function () {
      btn.textContent = mode;
      btn.setAttribute('aria-label', 'Colour theme: ' + mode + '. Activate to change.');
    };
    label();
    btn.addEventListener('click', function () {
      mode = ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length];
      try {
        if (mode === 'auto') localStorage.removeItem(STORE);
        else localStorage.setItem(STORE, mode);
      } catch (e) { /* private mode — the choice just will not persist */ }
      apply(mode);
      label();
    });
  }

  // A visitor who flips their OS theme while the page is open, on auto.
  var mq = window.matchMedia('(prefers-color-scheme: dark)');
  var onMq = function () { if (stored() === 'auto') apply('auto'); };
  if (mq.addEventListener) mq.addEventListener('change', onMq);
  else if (mq.addListener) mq.addListener(onMq);

  requestAnimationFrame(function () { root.classList.add('theme-ready'); });

  /* ---- one rAF-throttled passive scroll handler for everything ---------- */

  var header = document.querySelector('.site-header');
  var links = [].slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  var targets = links.map(function (a) {
    return document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
  });
  var current = -1;
  var ticking = false;

  function readHeaderHeight() {
    return header ? header.getBoundingClientRect().height : 0;
  }

  function update() {
    ticking = false;
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 4);

    if (!links.length) return;
    // "last heading whose top crossed the header line" — stable on tall
    // monitors where naive isIntersecting flickers between two headings.
    var line = readHeaderHeight() + 24;
    var idx = 0;
    for (var i = 0; i < targets.length; i++) {
      if (targets[i] && targets[i].getBoundingClientRect().top - line <= 0) idx = i;
    }
    if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 2) {
      idx = targets.length - 1;                       // pin the last at the foot
    }
    if (idx !== current) {
      if (current >= 0 && links[current]) links[current].removeAttribute('aria-current');
      if (links[idx]) links[idx].setAttribute('aria-current', 'true');
      current = idx;
    }
  }

  function onScroll() {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();

  var y = document.querySelector('[data-year]');
  if (y) y.textContent = new Date().getFullYear();
})();

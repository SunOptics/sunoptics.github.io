/* site.js — theme control, header measurements, and complete print output. */
(function () {
  'use strict';

  var root = document.documentElement;
  var STORE = 'theme';                       // "light" | "dark" | absent = auto
  var ORDER = ['auto', 'light', 'dark'];
  var LABELS = { auto: 'System', light: 'Light', dark: 'Dark' };
  var mq = window.matchMedia('(prefers-color-scheme: dark)');

  function stored() {
    try {
      var value = localStorage.getItem(STORE);
      return ORDER.indexOf(value) !== -1 ? value : 'auto';
    } catch (e) { return 'auto'; }
  }
  function apply(mode) {
    if (mode === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', mode);
    var dark = mode === 'dark' || (mode === 'auto' && mq.matches);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#15181d' : '#ffffff');
    document.dispatchEvent(new CustomEvent('themechange', { detail: { mode: mode, dark: dark } }));
  }

  var mode = stored();
  apply(mode);
  var btn = document.querySelector('.theme-toggle');
  if (btn) {
    var label = function () {
      var next = ORDER[(ORDER.indexOf(mode) + 1) % ORDER.length];
      btn.textContent = LABELS[mode];
      btn.setAttribute('aria-label', 'Colour theme: ' + LABELS[mode] +
        '. Activate to use ' + LABELS[next] + ' theme.');
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
  var onMq = function () { if (mode === 'auto') apply('auto'); };
  if (mq.addEventListener) mq.addEventListener('change', onMq);
  else if (mq.addListener) mq.addListener(onMq);

  requestAnimationFrame(function () { root.classList.add('theme-ready'); });

  // The mobile navigation wraps, so anchor offsets follow its actual height.
  var header = document.querySelector('.site-header');
  var ticking = false;
  var headerHeight = -1;

  function updateHeaderHeight() {
    ticking = false;
    var height = header ? Math.ceil(header.getBoundingClientRect().height) : 0;
    if (height !== headerHeight) {
      headerHeight = height;
      root.style.setProperty('--header-h', height + 'px');
    }
  }

  function queueHeaderUpdate() {
    if (!ticking) { ticking = true; requestAnimationFrame(updateHeaderHeight); }
  }
  window.addEventListener('resize', queueHeaderUpdate, { passive: true });
  if (header && window.ResizeObserver) {
    var observer = new ResizeObserver(queueHeaderUpdate);
    observer.observe(header);
  }
  updateHeaderHeight();

  // Include collapsed research references and earlier news in print/PDF.
  // Record only what we open, preserving the reader's choices afterwards.
  var printDetails = null;
  window.addEventListener('beforeprint', function () {
    if (printDetails !== null) return;
    printDetails = [].slice.call(document.querySelectorAll('details:not([open])'));
    printDetails.forEach(function (details) { details.open = true; });
  });
  window.addEventListener('afterprint', function () {
    if (printDetails === null) return;
    printDetails.forEach(function (details) { details.open = false; });
    printDetails = null;
    queueHeaderUpdate();
  });

  var y = document.querySelector('[data-year]');
  if (y) y.textContent = new Date().getFullYear();
})();

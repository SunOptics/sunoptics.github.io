/*
 * waterfall.js — hidden-line waterfall of |E|² over successive cavity
 * roundtrips, drawn from a live integration of the Lugiato–Lefever equation
 * (see lle.js).  The plot writes itself top-down as the equation is solved,
 * once, and then the page runs zero animation frames for the rest of the visit.
 */
(function (global) {
  'use strict';

  var reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* True CW background of the LLE: I(1 + (Δ − I)²) = S², then E₀ = S/(1+i(Δ−I)). */
  function cwField(S, th) {
    var I = 0.05;
    for (var k = 0; k < 200; k++) {
      var f = I * (1 + (th - I) * (th - I)) - S * S;
      var df = 1 + (th - I) * (th - I) - 2 * I * (th - I);
      I -= f / df;
      if (I < 1e-9) I = 1e-9;
    }
    var di = th - I, den = 1 + di * di;
    return { re: S / den, im: -S * di / den, I: I };
  }

  /* Seed `count` equally spaced cavity solitons on that background.  A
     `vacancy` removes one — the defect that makes a soliton crystal visible
     in the comb, and that sets its neighbours slowly drifting. */
  function seed(s, count, vacancy) {
    var bg = cwField(s.S, s.detuning);
    var amp = Math.sqrt(2 * s.detuning);
    var w = 1 / Math.sqrt(s.detuning);
    var L = s.L, n = s.n, i, k;
    for (i = 0; i < n; i++) { s.re[i] = bg.re; s.im[i] = bg.im; }
    for (k = 0; k < count; k++) {
      if (k === vacancy) continue;
      var t0 = -L / 2 + L * (k + 0.5) / count;
      for (i = 0; i < n; i++) {
        var t = -L / 2 + L * i / n - t0;
        if (t > L / 2) t -= L;
        if (t < -L / 2) t += L;
        s.re[i] += amp / Math.cosh(t / w);
      }
    }
    // A whisper of asymmetry, so the crystal is never perfectly rigid.
    for (i = 0; i < n; i++) {
      s.re[i] += Math.sin(i * 1.7) * 6e-3;
      s.im[i] += Math.cos(i * 2.3) * 6e-3;
    }
    return bg;
  }

  function tokens() {
    var cs = getComputedStyle(document.documentElement);
    return {
      line:   cs.getPropertyValue('--fig-line').trim()   || '#b5afa3',
      peak:   cs.getPropertyValue('--fig-peak').trim()   || '#3040c4',
      ground: cs.getPropertyValue('--fig-ground').trim() || '#f2f0eb'
    };
  }

  function Waterfall(canvas, opts) {
    opts = opts || {};
    this.canvas = canvas;
    this.ctx = canvas.getContext && canvas.getContext('2d');
    if (!this.ctx) return;

    this.traces = opts.traces || 56;
    this.stepsPer = opts.stepsPer || 220;
    this.settle = opts.settle || 3000;
    this.crest = opts.crest != null ? opts.crest : 0.45;
    this.amp = opts.amp != null ? opts.amp : 0.165;

    this.solver = new global.LLE({
      n: opts.n || 512, L: opts.L || 40,
      S: opts.S != null ? opts.S : 2.0,
      detuning: opts.detuning != null ? opts.detuning : 4.0,
      dt: 2e-3, solitons: 0
    });
    seed(this.solver, opts.solitons != null ? opts.solitons : 5, opts.vacancy);
    this.solver.step(this.settle);

    this.data = [];        // Float32Array per captured roundtrip
    this.imax = 1e-9;
    this.visible = 0;
    this.raf = 0;
    this.w = 0; this.h = 0;

    this._resize();
    this._observe();
  }

  Waterfall.prototype.captureAll = function () {
    while (this.data.length < this.traces) this.captureOne();
  };

  Waterfall.prototype.captureOne = function () {
    var I = this.solver.step(this.stepsPer);
    var row = new Float32Array(I.length);
    for (var i = 0; i < I.length; i++) {
      row[i] = I[i];
      if (I[i] > this.imax) this.imax = I[i];
    }
    this.data.push(row);
  };

  Waterfall.prototype._resize = function () {
    var r = this.canvas.getBoundingClientRect();
    var cssW = Math.max(1, Math.round(r.width));
    var cssH = Math.max(1, Math.round(r.height));
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pxW = Math.round(cssW * dpr), pxH = Math.round(cssH * dpr);
    if (pxW === this._pxW && pxH === this._pxH) return false;
    this._pxW = pxW; this._pxH = pxH;
    this.canvas.width = pxW;
    this.canvas.height = pxH;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.dpr = dpr;
    this.w = cssW; this.h = cssH;
    return true;
  };

  /* Incremental by design: the hidden-line algorithm paints front-to-back, so
     a newly captured roundtrip can be laid straight over what is already on the
     canvas.  Redrawing all N traces every frame is O(N^2) work for no gain.
     Pass from = 0 to force a full repaint (theme change, resize). */
  Waterfall.prototype.draw = function (from) {
    var ctx = this.ctx;
    if (!ctx || !this.data.length) return;
    var t = tokens();
    var W = this.w, H = this.h, N = this.traces;
    var shown = Math.min(this.visible, this.data.length);
    if (from == null) from = 0;

    ctx.save();
    if (from === 0) {
      ctx.fillStyle = t.ground;
      ctx.fillRect(0, 0, W, H);
    }

    // padT must exceed AMP or the tallest crest is clipped by the frame.
    var AMP = (this.amp != null ? this.amp : 0.165) * H;
    var padT = AMP + 0.035 * H, padB = 0.08 * H;
    var span = Math.max(1, H - padT - padB);
    var inv = 1 / Math.max(this.imax, 1e-9);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    for (var n = from; n < shown; n++) {
      var row = this.data[n];
      var M = row.length;
      var base = padT + (N === 1 ? 0 : n * span / (N - 1));
      var i, x, y;

      // Fill under the trace with the ground colour: that occlusion is what
      // makes it a hidden-line plot rather than 56 overlapping squiggles.
      ctx.beginPath();
      for (i = 0; i < M; i++) {
        x = i * W / (M - 1);
        y = base - row[i] * inv * AMP;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
      ctx.globalAlpha = 1;
      ctx.fillStyle = t.ground;
      ctx.fill();

      ctx.beginPath();
      for (i = 0; i < M; i++) {
        x = i * W / (M - 1);
        y = base - row[i] * inv * AMP;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.globalAlpha = 0.28 + 0.72 * (N === 1 ? 1 : n / (N - 1));
      ctx.strokeStyle = t.line;
      ctx.lineWidth = this.dpr >= 2 ? 0.75 : 1;
      ctx.stroke();

      // Second pass: only the crests, in the accent. ~3% of the pixels.
      ctx.globalAlpha = 1;
      ctx.strokeStyle = t.peak;
      ctx.lineWidth = 1.4;
      var open = false;
      ctx.beginPath();
      for (i = 0; i < M; i++) {
        var v = row[i] * inv;
        x = i * W / (M - 1);
        y = base - v * AMP;
        if (v > this.crest) {
          if (!open) { ctx.moveTo(x, y); open = true; } else ctx.lineTo(x, y);
        } else if (open) { open = false; }
      }
      ctx.stroke();
    }
    ctx.restore();
    this.drawn = shown;
  };

  Waterfall.prototype.renderStatic = function () {
    this.captureAll();
    this.visible = this.traces;
    this.draw(0);
  };

  Waterfall.prototype.reveal = function () {
    if (this.raf) return;
    var self = this, t0 = null;
    var tick = function (now) {
      if (t0 === null) t0 = now;
      var p = 1 - Math.pow(2, -10 * Math.min(1, (now - t0) / 1400));
      var want = Math.ceil(p * self.traces);
      // Integrate just far enough ahead of the pen.
      var guard = 0;
      while (self.data.length < want && guard++ < 8) self.captureOne();
      var before = self.drawn || 0;
      self.visible = Math.min(want, self.data.length);
      self.draw(before);
      if (self.visible >= self.traces) { self.raf = 0; return; }
      self.raf = requestAnimationFrame(tick);
    };
    self.raf = requestAnimationFrame(tick);
  };

  Waterfall.prototype.start = function () {
    if (this.started) return;
    this.started = true;
    // The CSS reduced-motion override does not stop a rAF loop — check here.
    if (reduceMQ.matches) this.renderStatic();
    else this.reveal();
  };

  Waterfall.prototype._observe = function () {
    var self = this;

    var repaint = function () {
      if (!self.started) return;
      if (self.raf) { cancelAnimationFrame(self.raf); self.raf = 0; }
      self.captureAll();
      self.visible = self.traces;
      self.draw(0);
    };
    document.addEventListener('themechange', repaint);
    var cmq = window.matchMedia('(prefers-color-scheme: dark)');
    if (cmq.addEventListener) cmq.addEventListener('change', repaint);
    if (reduceMQ.addEventListener) reduceMQ.addEventListener('change', repaint);

    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () {
        // Guard against firing from our own canvas.width write.
        if (self._resize() && self.started) { self.visible = self.data.length; self.draw(0); }
      });
      ro.observe(this.canvas);
    } else {
      window.addEventListener('resize', function () {
        if (self._resize() && self.started) self.draw(0);
      }, { passive: true });
    }

    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) { io.disconnect(); self.start(); return; }
        }
      }, { rootMargin: '120px' });
      io.observe(this.canvas);
    } else {
      this.start();
    }
  };

  global.Waterfall = Waterfall;
  global.LLEHelpers = { cwField: cwField, seed: seed, tokens: tokens };

  document.addEventListener('DOMContentLoaded', function () {
    var nodes = document.querySelectorAll('[data-waterfall]');
    for (var i = 0; i < nodes.length; i++) {
      var cfg = {};
      try { cfg = JSON.parse(nodes[i].getAttribute('data-waterfall') || '{}'); } catch (e) {}
      if (window.matchMedia('(max-width: 62rem)').matches) {
        cfg.traces = Math.min(cfg.traces || 56, 34);
      }
      nodes[i].waterfall = new Waterfall(nodes[i], cfg);
    }
  });
})(window);

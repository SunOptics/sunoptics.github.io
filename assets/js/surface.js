/*
 * surface.js — the site's figures.
 *
 * A three-dimensional surface plot of |A|² over (delay, propagation), drawn in
 * the register of the MATLAB figures this work is published with: black ground,
 * height-mapped colour, no wireframe.  The colour ramp is sampled from the
 * author's own published figure.
 *
 * The surface grows away from you as the field is integrated — nothing here is
 * a recording, and once the last row is drawn the page runs no further frames.
 */
(function (global) {
  'use strict';

  var reduceMQ = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* Height ramp, sampled pixel by pixel from a cross-section of the author's
     multimode-soliton figure: black through olive, amber, red and magenta to
     azure at the crest. */
  var RAMP = [
    [0, 0, 0], [12, 12, 10], [44, 46, 27], [87, 88, 48], [139, 139, 71],
    [192, 192, 100], [187, 179, 80], [182, 165, 54], [187, 153, 37],
    [187, 138, 19], [187, 124, 3], [189, 110, 0], [196, 99, 0], [206, 85, 5],
    [219, 71, 22], [231, 60, 41], [235, 51, 58], [231, 46, 71], [223, 42, 87],
    [204, 37, 107], [177, 36, 134], [146, 36, 160], [124, 36, 177],
    [107, 37, 190], [88, 41, 199], [70, 42, 204], [49, 46, 202], [32, 51, 201],
    [22, 58, 201], [14, 66, 201], [5, 76, 202], [0, 90, 204], [0, 107, 213],
    [0, 124, 223]
  ];

  /* Pre-mix the ramp into 256 CSS colour strings once: this is the inner loop. */
  var LUT = (function () {
    var out = [], i, t, f, a, b, k;
    for (i = 0; i < 256; i++) {
      t = i / 255;
      f = t * (RAMP.length - 1);
      k = Math.min(RAMP.length - 2, Math.floor(f));
      a = RAMP[k]; b = RAMP[k + 1];
      f -= k;
      out.push('rgb(' + Math.round(a[0] + (b[0] - a[0]) * f) + ','
                      + Math.round(a[1] + (b[1] - a[1]) * f) + ','
                      + Math.round(a[2] + (b[2] - a[2]) * f) + ')');
    }
    return out;
  })();

  var GROUND = '#000000';

  /* ---- the two fields we plot ------------------------------------------- */

  function makeField(cfg) {
    if (cfg.kind === 'lle') {
      var s = new global.LLE({
        n: cfg.n || 256, L: cfg.L || 20,
        S: cfg.S != null ? cfg.S : 2.0,
        detuning: cfg.detuning != null ? cfg.detuning : 4.0,
        dt: 2e-3, solitons: 0
      });
      seedCavity(s, cfg.solitons != null ? cfg.solitons : 5, cfg.vacancy);
      s.step(cfg.settle != null ? cfg.settle : 3000);
      return s;
    }
    return new global.NLSE({
      n: cfg.n || 256, L: cfg.L || 40, dz: cfg.dz || 2e-3,
      solitons: cfg.pulses || []
    });
  }

  /* Cavity solitons sit on the lower branch of the bistable CW background, and
     the background's phase matters: seed it real and they dissolve. */
  function seedCavity(s, count, vacancy) {
    var S = s.S, th = s.detuning, I = 0.05, k, f, df;
    for (k = 0; k < 200; k++) {
      f = I * (1 + (th - I) * (th - I)) - S * S;
      df = 1 + (th - I) * (th - I) - 2 * I * (th - I);
      I = Math.max(I - f / df, 1e-9);
    }
    var di = th - I, den = 1 + di * di, bgR = S / den, bgI = -S * di / den;
    var amp = Math.sqrt(2 * th), w = 1 / Math.sqrt(th), L = s.L, n = s.n, i, m, t0, t;
    for (i = 0; i < n; i++) { s.re[i] = bgR; s.im[i] = bgI; }
    for (m = 0; m < count; m++) {
      if (m === vacancy) continue;
      t0 = -L / 2 + L * (m + 0.5) / count;
      for (i = 0; i < n; i++) {
        t = -L / 2 + L * i / n - t0;
        if (t > L / 2) t -= L;
        if (t < -L / 2) t += L;
        s.re[i] += amp / Math.cosh(t / w);
      }
    }
    for (i = 0; i < n; i++) {
      s.re[i] += Math.sin(i * 1.7) * 6e-3;
      s.im[i] += Math.cos(i * 2.3) * 6e-3;
    }
  }

  /* ---- the plot ---------------------------------------------------------- */

  function Surface(canvas, cfg) {
    this.canvas = canvas;
    this.ctx = canvas.getContext && canvas.getContext('2d');
    if (!this.ctx) return;

    this.cfg = cfg = cfg || {};
    this.rows = cfg.rows || 84;
    this.stepsPer = cfg.stepsPer || 90;
    this.gamma = cfg.gamma || 0.78;
    this.clip = cfg.clip || 1;    // normalise against max*clip, as caxis would
    this.field = makeField(cfg);
    this.n = this.field.n;

    this.data = [];
    this.max = 1e-9;
    this.drawn = 0;
    this.raf = 0;

    this._resize();
    this._observe();
  }

  Surface.prototype.capture = function () {
    var I = this.field.step(this.stepsPer);
    var row = new Float64Array(I.length), i;
    for (i = 0; i < I.length; i++) {
      row[i] = I[i];
      if (I[i] > this.max) this.max = I[i];
    }
    this.data.push(row);
  };

  Surface.prototype._resize = function () {
    var r = this.canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pw = Math.round(Math.max(1, r.width) * dpr);
    var ph = Math.round(Math.max(1, r.height) * dpr);
    if (pw === this._pw && ph === this._ph) return false;
    this._pw = pw; this._ph = ph;
    this.canvas.width = pw;
    this.canvas.height = ph;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = Math.max(1, r.width);
    this.h = Math.max(1, r.height);
    return true;
  };

  /* Oblique projection, roughly MATLAB's default view. The propagation axis
     must run from far (up and right) to near (down and left) as the row index
     grows, so that painting rows in order is also painting back to front — and
     so that the surface reveals itself growing towards the viewer. */
  Surface.prototype._basis = function () {
    var W = this.w, H = this.h;
    return {
      ox: 0.44 * W, oy: 0.40 * H,
      ax: 0.50 * W, ay: 0.18 * H,      // delay axis: right and down
      bx: -0.36 * W, by: 0.40 * H,     // propagation axis: towards the viewer
      hz: 0.34 * H                     // height
    };
  };

  Surface.prototype.draw = function (from) {
    var ctx = this.ctx;
    if (!ctx || this.data.length < 2) return;
    var B = this._basis(), N = this.n, M = this.rows;
    var shown = Math.min(this.drawn, this.data.length);
    var inv = 1 / (this.max * this.clip), g = this.gamma;
    var j, i, rowA, rowB, u0, u1, v0, v1, hA, hB, hC, hD, avg, c;
    var x0, y0, x1, y1, x2, y2, x3, y3;

    if (!from) {
      ctx.fillStyle = GROUND;
      ctx.fillRect(0, 0, this.w, this.h);
    }
    ctx.lineWidth = 1;
    ctx.lineJoin = 'round';

    for (j = Math.max(0, from - 1); j < shown - 1; j++) {
      rowA = this.data[j]; rowB = this.data[j + 1];
      v0 = j / (M - 1); v1 = (j + 1) / (M - 1);
      for (i = 0; i < N - 1; i++) {
        u0 = i / (N - 1); u1 = (i + 1) / (N - 1);
        hA = Math.min(1, rowA[i] * inv); hB = Math.min(1, rowA[i + 1] * inv);
        hC = Math.min(1, rowB[i + 1] * inv); hD = Math.min(1, rowB[i] * inv);
        avg = Math.min(1, (hA + hB + hC + hD) * 0.25);
        c = LUT[Math.max(0, Math.min(255, Math.round(Math.pow(avg, g) * 255)))];

        x0 = B.ox + u0 * B.ax + v0 * B.bx; y0 = B.oy + u0 * B.ay + v0 * B.by - hA * B.hz;
        x1 = B.ox + u1 * B.ax + v0 * B.bx; y1 = B.oy + u1 * B.ay + v0 * B.by - hB * B.hz;
        x2 = B.ox + u1 * B.ax + v1 * B.bx; y2 = B.oy + u1 * B.ay + v1 * B.by - hC * B.hz;
        x3 = B.ox + u0 * B.ax + v1 * B.bx; y3 = B.oy + u0 * B.ay + v1 * B.by - hD * B.hz;

        ctx.beginPath();
        ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.lineTo(x2, y2); ctx.lineTo(x3, y3);
        ctx.closePath();
        ctx.fillStyle = c;
        ctx.strokeStyle = c;   // closes the hairline seams between cells
        ctx.fill();
        ctx.stroke();
      }
    }
  };

  Surface.prototype.renderStatic = function () {
    while (this.data.length < this.rows) this.capture();
    this.drawn = this.rows;
    this.draw(0);
  };

  Surface.prototype.reveal = function () {
    if (this.raf) return;
    var self = this, t0 = null;
    var tick = function (now) {
      if (t0 === null) t0 = now;
      var p = Math.min(1, (now - t0) / 2600);
      p = 1 - Math.pow(1 - p, 2);
      var want = Math.max(2, Math.ceil(p * self.rows));
      var guard = 0;
      while (self.data.length < want && guard++ < 6) self.capture();
      var before = self.drawn;
      self.drawn = Math.min(want, self.data.length);
      self.draw(before);
      if (self.drawn >= self.rows) { self.raf = 0; return; }
      self.raf = requestAnimationFrame(tick);
    };
    self.raf = requestAnimationFrame(tick);
  };

  Surface.prototype.start = function () {
    if (this.started) return;
    this.started = true;
    // The CSS reduced-motion override cannot stop a rAF loop; check it here.
    if (reduceMQ.matches) this.renderStatic();
    else this.reveal();
  };

  Surface.prototype._observe = function () {
    var self = this;

    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        // Guard against firing from our own canvas.width write.
        if (self._resize() && self.started) {
          if (self.raf) { cancelAnimationFrame(self.raf); self.raf = 0; }
          self.renderStatic();
        }
      }).observe(this.canvas);
    }

    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) { io.disconnect(); self.start(); return; }
        }
      }, { rootMargin: '140px' });
      io.observe(this.canvas);
    } else {
      this.start();
    }
  };

  global.Surface = Surface;

  document.addEventListener('DOMContentLoaded', function () {
    var nodes = document.querySelectorAll('[data-surface]');
    for (var i = 0; i < nodes.length; i++) {
      var cfg = {};
      try { cfg = JSON.parse(nodes[i].getAttribute('data-surface') || '{}'); } catch (e) {}
      if (window.matchMedia('(max-width: 48rem)').matches) {
        cfg.rows = Math.min(cfg.rows || 84, 56);
        cfg.n = Math.min(cfg.n || 256, 128);
      }
      nodes[i].surface = new Surface(nodes[i], cfg);
    }
  });
})(window);

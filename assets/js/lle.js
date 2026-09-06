/*
 * lle.js — a real Lugiato–Lefever solver running in the browser.
 *
 *   ∂E/∂t = S − (1 + iΔ)E + i|E|²E + i ∂²E/∂τ²
 *
 * Split-step Fourier: the linear + driving part is integrated exactly in the
 * frequency domain, the Kerr term as a pure phase rotation in the time domain,
 * combined with Strang splitting.  What you see on the landing page is not a
 * looping video — it is this equation being integrated at ~60 fps.
 */
(function (global) {
  'use strict';

  /* ---------- radix-2 in-place complex FFT ---------- */

  function bitReverse(re, im, n) {
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        let t = re[i]; re[i] = re[j]; re[j] = t;
        t = im[i]; im[i] = im[j]; im[j] = t;
      }
    }
  }

  function fft(re, im, inverse) {
    const n = re.length;
    bitReverse(re, im, n);
    for (let len = 2; len <= n; len <<= 1) {
      const half = len >> 1;
      const ang = (inverse ? 2 : -2) * Math.PI / len;
      const wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let j = 0; j < half; j++) {
          const a = i + j, b = a + half;
          const ur = re[a], ui = im[a];
          const vr = re[b] * cr - im[b] * ci;
          const vi = re[b] * ci + im[b] * cr;
          re[a] = ur + vr; im[a] = ui + vi;
          re[b] = ur - vr; im[b] = ui - vi;
          const nr = cr * wr - ci * wi;
          ci = cr * wi + ci * wr;
          cr = nr;
        }
      }
    }
    if (inverse) {
      for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
    }
  }

  /* ---------- the solver ---------- */

  function LLE(opts) {
    opts = opts || {};
    this.n = opts.n || 512;                 // grid points around the cavity
    this.L = opts.L || 40;                  // normalised round-trip window
    this.S = opts.S != null ? opts.S : 2.0; // driving field amplitude
    this.detuning = opts.detuning != null ? opts.detuning : 4.0;
    this.dt = opts.dt || 2e-3;

    const n = this.n;
    this.re = new Float64Array(n);
    this.im = new Float64Array(n);
    this.wr = new Float64Array(n);          // scratch for the spectral step
    this.wi = new Float64Array(n);
    this.omega = new Float64Array(n);
    this.intensity = new Float64Array(n);

    const dw = 2 * Math.PI / this.L;
    for (let k = 0; k < n; k++) {
      this.omega[k] = dw * (k < n / 2 ? k : k - n);
    }

    this._expRe = new Float64Array(n);
    this._expIm = new Float64Array(n);
    this._driveRe = new Float64Array(n);
    this._driveIm = new Float64Array(n);
    this._cachedDetuning = NaN;

    this.reset(opts.solitons != null ? opts.solitons : 5, opts.vacancy);
  }

  /* Seed a soliton crystal: `count` equally spaced cavity solitons sitting on
     the lower branch of the bistable CW background.  `vacancy` removes one of
     them, the defect that makes real soliton crystals visible in the comb. */
  LLE.prototype.reset = function (count, vacancy) {
    const n = this.n, L = this.L, D = this.detuning, S = this.S;
    const cw = S / Math.sqrt(1 + D * D);            // lower-branch CW estimate
    const amp = Math.sqrt(2 * D);                    // peak of the sech ansatz
    const width = 1 / Math.sqrt(D);
    let phi = 0;
    const arg = Math.sqrt(8 * D) / (Math.PI * S);
    if (arg <= 1) phi = Math.acos(arg);              // Barashenkov phase

    for (let i = 0; i < n; i++) { this.re[i] = cw; this.im[i] = 0; }

    for (let s = 0; s < count; s++) {
      if (vacancy != null && s === vacancy) continue;
      const tau0 = -L / 2 + L * (s + 0.5) / count;
      for (let i = 0; i < n; i++) {
        let tau = -L / 2 + L * i / n - tau0;
        if (tau > L / 2) tau -= L;                   // the cavity is a ring
        if (tau < -L / 2) tau += L;
        const a = amp / Math.cosh(tau / width);
        this.re[i] += a * Math.cos(phi);
        this.im[i] += a * Math.sin(phi);
      }
    }
    // A whisper of noise, so the dynamics are never perfectly symmetric.
    for (let i = 0; i < n; i++) {
      this.re[i] += (Math.sin(i * 12.9898) * 43758.5453 % 1) * 1e-3;
      this.im[i] += (Math.sin(i * 78.233) * 43758.5453 % 1) * 1e-3;
    }
    return this;
  };

  LLE.prototype._refreshOperator = function () {
    if (this._cachedDetuning === this.detuning) return;
    const n = this.n, dt = this.dt, D = this.detuning;
    for (let k = 0; k < n; k++) {
      // L(ω) = −(1 + iΔ) − iω²
      const lr = -1;
      const li = -D - this.omega[k] * this.omega[k];
      const ex = Math.exp(lr * dt);
      const er = ex * Math.cos(li * dt);
      const ei = ex * Math.sin(li * dt);
      this._expRe[k] = er;
      this._expIm[k] = ei;
      // (e^{L dt} − 1) / L, the exact response to the constant drive
      const dr = er - 1, di = ei;
      const den = lr * lr + li * li;
      this._driveRe[k] = (dr * lr + di * li) / den;
      this._driveIm[k] = (di * lr - dr * li) / den;
    }
    this._cachedDetuning = this.detuning;
  };

  LLE.prototype.step = function (steps) {
    this._refreshOperator();
    const n = this.n, dt = this.dt, halfDt = dt / 2;
    const re = this.re, im = this.im, wr = this.wr, wi = this.wi;
    const driveHat = this.S * n;                     // FFT of a constant field

    for (let s = 0; s < (steps || 1); s++) {
      // ½ Kerr step
      for (let i = 0; i < n; i++) {
        const p = (re[i] * re[i] + im[i] * im[i]) * halfDt;
        const c = Math.cos(p), sn = Math.sin(p);
        const r = re[i] * c - im[i] * sn;
        im[i] = re[i] * sn + im[i] * c;
        re[i] = r;
      }
      // exact linear + drive step
      wr.set(re); wi.set(im);
      fft(wr, wi, false);
      for (let k = 0; k < n; k++) {
        const r = wr[k] * this._expRe[k] - wi[k] * this._expIm[k];
        const i2 = wr[k] * this._expIm[k] + wi[k] * this._expRe[k];
        wr[k] = r; wi[k] = i2;
      }
      wr[0] += driveHat * this._driveRe[0];
      wi[0] += driveHat * this._driveIm[0];
      fft(wr, wi, true);
      re.set(wr); im.set(wi);
      // ½ Kerr step
      for (let i = 0; i < n; i++) {
        const p = (re[i] * re[i] + im[i] * im[i]) * halfDt;
        const c = Math.cos(p), sn = Math.sin(p);
        const r = re[i] * c - im[i] * sn;
        im[i] = re[i] * sn + im[i] * c;
        re[i] = r;
      }
    }

    let peak = 0;
    for (let i = 0; i < n; i++) {
      const v = re[i] * re[i] + im[i] * im[i];
      this.intensity[i] = v;
      if (v > peak) peak = v;
    }
    this.peak = peak;
    return this.intensity;
  };

  global.LLE = LLE;
})(window);

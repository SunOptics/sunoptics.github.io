#!/usr/bin/env python3
"""
make_assets.py — generate the site's figurative assets from the physics itself.

    python3 tools/make_assets.py

Writes assets/img/soliton-rule.svg and favicon.svg.  Both are produced by
integrating the Lugiato-Lefever equation

    dE/dt = S - (1 + i*theta) E + i |E|^2 E + i d^2E/dtau^2

with a split-step Fourier scheme, in pure Python: no numpy, no Pillow, no
network.  Run it once and commit the output; nothing runs at deploy time.
"""

import cmath
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")

INK = (0x1A, 0x1B, 0x1E)
PAPER = (0xF2, 0xF0, 0xEB)
LINE = (0xB5, 0xAF, 0xA3)
PEAK = (0x30, 0x40, 0xC4)


# ------------------------------------------------------------------ the FFT

def fft(a, inverse=False):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        ang = (2 if inverse else -2) * math.pi / length
        w = cmath.exp(1j * ang)
        half = length >> 1
        for i in range(0, n, length):
            cur = 1 + 0j
            for k in range(i, i + half):
                u = a[k]
                v = a[k + half] * cur
                a[k] = u + v
                a[k + half] = u - v
                cur *= w
        length <<= 1
    if inverse:
        a[:] = [x / n for x in a]
    return a


# ---------------------------------------------------------------- the solver

class LLE(object):
    def __init__(self, n=256, L=20.0, S=2.0, theta=4.0, dt=5e-3):
        self.n, self.L, self.S, self.theta, self.dt = n, L, S, theta, dt
        dw = 2 * math.pi / L
        self.omega = [dw * (k if k < n // 2 else k - n) for k in range(n)]
        self.E = [0j] * n
        # exact linear + drive propagator
        self.exp = []
        self.drv = []
        for k in range(n):
            lam = complex(-1.0, -theta - self.omega[k] ** 2)
            ex = cmath.exp(lam * dt)
            self.exp.append(ex)
            self.drv.append((ex - 1) / lam)

    def cw(self):
        """Lower branch of the bistable CW solution: I(1+(theta-I)^2)=S^2."""
        I, S, th = 0.05, self.S, self.theta
        for _ in range(200):
            f = I * (1 + (th - I) ** 2) - S * S
            df = 1 + (th - I) ** 2 - 2 * I * (th - I)
            I = max(I - f / df, 1e-9)
        return S / complex(1, th - I), I

    def seed(self, count, vacancy=None):
        bg, _ = self.cw()
        amp = math.sqrt(2 * self.theta)
        w = 1 / math.sqrt(self.theta)
        n, L = self.n, self.L
        self.E = [bg] * n
        for s in range(count):
            if s == vacancy:
                continue
            t0 = -L / 2 + L * (s + 0.5) / count
            for i in range(n):
                t = -L / 2 + L * i / n - t0
                if t > L / 2:
                    t -= L
                if t < -L / 2:
                    t += L
                self.E[i] += amp / math.cosh(t / w)
        for i in range(n):
            self.E[i] += complex(math.sin(i * 1.7), math.cos(i * 2.3)) * 6e-3
        return self

    def step(self, steps=1):
        n, dt, S = self.n, self.dt, self.S
        half = dt / 2
        for _ in range(steps):
            E = self.E
            for i in range(n):
                E[i] *= cmath.exp(1j * abs(E[i]) ** 2 * half)
            F = fft(list(E))
            for k in range(n):
                F[k] *= self.exp[k]
            F[0] += S * n * self.drv[0]
            E = fft(F, True)
            for i in range(n):
                E[i] *= cmath.exp(1j * abs(E[i]) ** 2 * half)
            self.E = E
        return [abs(x) ** 2 for x in self.E]


# ------------------------------------------------------------- a PNG encoder

def trace_path(values, width, height, pad=1.0):
    top = max(values)
    pts = []
    for i, v in enumerate(values):
        x = i * width / (len(values) - 1)
        y = height - pad - (v / top) * (height - 2 * pad)
        pts.append((round(x, 2), round(y, 2)))
    return "M " + " L ".join("%s %s" % p for p in pts)


def make_soliton_rule(values):
    w, h = 1000.0, 14.0
    base = trace_path(values, w, h)
    top = max(values)
    crest, run = [], []
    for i, v in enumerate(values):
        x = i * w / (len(values) - 1)
        y = h - 1.0 - (v / top) * (h - 2.0)
        if v / top > 0.35:
            run.append("%s %s" % (round(x, 2), round(y, 2)))
        elif run:
            crest.append("M " + " L ".join(run))
            run = []
    if run:
        crest.append("M " + " L ".join(run))
    svg = (
        '<svg class="soliton-svg" viewBox="0 0 1000 14" preserveAspectRatio="none" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">'
        '<path d="%s" fill="none" stroke="currentColor" stroke-width="1" '
        'vector-effect="non-scaling-stroke"/>'
        '<path d="%s" fill="none" stroke="var(--fig-peak)" stroke-width="1.6" '
        'vector-effect="non-scaling-stroke"/>'
        '</svg>'
    ) % (base, " ".join(crest))
    path = os.path.join(IMG, "soliton-rule.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return path


def make_favicon(values):
    """A single cavity soliton on its background — the site's mark."""
    n = len(values)
    mid = max(range(n), key=lambda i: values[i])
    window = [values[(mid + i - 24) % n] for i in range(49)]
    top = max(window)
    pts = []
    for i, v in enumerate(window):
        x = 2 + i * 28.0 / (len(window) - 1)
        y = 29 - (v / top) * 25
        pts.append("%s %s" % (round(x, 2), round(y, 2)))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="4" fill="#1A1B1E"/>'
        '<path d="M %s" fill="none" stroke="#9BB2FF" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        '</svg>'
    ) % " L ".join(pts)
    path = os.path.join(IMG, "favicon.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return path


def main():
    os.makedirs(IMG, exist_ok=True)
    print("integrating the Lugiato-Lefever equation ...")

    rule = LLE(n=256, L=30.0, S=2.0, theta=4.0).seed(6, vacancy=4)
    rule.step(1200)
    values = rule.step(400)
    print("  rule      peak %.2f" % max(values))
    print("  wrote", make_soliton_rule(values))
    print("  wrote", make_favicon(values))



if __name__ == "__main__":
    main()

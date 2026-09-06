#!/usr/bin/env python3
"""
make_assets.py — generate the site's figurative assets from the physics itself.

    python3 tools/make_assets.py

Writes assets/img/soliton-rule.svg, favicon.svg and og.png.  Everything is
produced by integrating the Lugiato-Lefever equation

    dE/dt = S - (1 + i*theta) E + i |E|^2 E + i d^2E/dtau^2

with a split-step Fourier scheme, in pure Python: no numpy, no Pillow, no
network.  Run it once and commit the output; nothing runs at deploy time.
"""

import cmath
import math
import os
import struct
import zlib

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

def png(path, width, height, rows):
    """rows: list of height lists of (r,g,b). Pure stdlib, no Pillow."""
    raw = bytearray()
    for row in rows:
        raw.append(0)                       # filter type 0
        for r, g, b in row:
            raw += bytes((r, g, b))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(out)
    return os.path.getsize(path)


def blend(dst, src, alpha):
    return tuple(int(round(d + (s - d) * alpha)) for d, s in zip(dst, src))


def line(rows, w, h, x0, y0, x1, y1, colour, alpha=1.0):
    """Xiaolin-Wu-ish: plain Bresenham with a soft vertical neighbour."""
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        xi = int(round(x))
        if xi < 0 or xi >= w:
            continue
        yf = math.floor(y)
        frac = y - yf
        for yy, a in ((yf, (1 - frac) * alpha), (yf + 1, frac * alpha)):
            if 0 <= yy < h and a > 0.004:
                rows[yy][xi] = blend(rows[yy][xi], colour, a)


# -------------------------------------------------------------------- assets

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


RAMP = [
    (0, 0, 0), (12, 12, 10), (44, 46, 27), (87, 88, 48), (139, 139, 71),
    (192, 192, 100), (187, 179, 80), (182, 165, 54), (187, 153, 37),
    (187, 138, 19), (187, 124, 3), (189, 110, 0), (196, 99, 0), (206, 85, 5),
    (219, 71, 22), (231, 60, 41), (235, 51, 58), (231, 46, 71), (223, 42, 87),
    (204, 37, 107), (177, 36, 134), (146, 36, 160), (124, 36, 177),
    (107, 37, 190), (88, 41, 199), (70, 42, 204), (49, 46, 202), (32, 51, 201),
    (22, 58, 201), (14, 66, 201), (5, 76, 202), (0, 90, 204), (0, 107, 213),
    (0, 124, 223),
]


def ramp(t):
    """Height -> colour, sampled from the author's own published figure."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    f = t * (len(RAMP) - 1)
    k = min(len(RAMP) - 2, int(f))
    f -= k
    a, b = RAMP[k], RAMP[k + 1]
    return (int(a[0] + (b[0] - a[0]) * f),
            int(a[1] + (b[1] - a[1]) * f),
            int(a[2] + (b[2] - a[2]) * f))


def fill_quad(rows, W, H, pts, colour):
    """Scanline fill of a small convex quad. Enough for a surf plot; the cells
    are only a few pixels across."""
    ys = [p[1] for p in pts]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(H - 1, int(math.ceil(max(ys))))
    n = len(pts)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= yc < by) or (by <= yc < ay):
                xs.append(ax + (bx - ax) * (yc - ay) / (by - ay))
        if len(xs) < 2:
            continue
        lo, hi = min(xs), max(xs)
        x0 = max(0, int(math.floor(lo)))
        x1 = min(W - 1, int(math.ceil(hi)))
        row = rows[y]
        for x in range(x0, x1 + 1):
            row[x] = colour


def make_og(traces, gamma=0.78):
    """The share image: the same surface the front page draws, rendered here so
    the card people see in Slack is the same figure."""
    W, H = 1200, 630
    rows = [[(0, 0, 0)] * W for _ in range(H)]
    M = len(traces)
    N = len(traces[0])
    top = max(max(t) for t in traces)
    ox, oy = 0.44 * W, 0.40 * H
    ax, ay = 0.50 * W, 0.18 * H
    bx, by = -0.36 * W, 0.40 * H
    hz = 0.34 * H

    def project(u, v, h):
        return (ox + u * ax + v * bx, oy + u * ay + v * by - h * hz)

    for j in range(M - 1):
        ra, rb = traces[j], traces[j + 1]
        v0, v1 = j / (M - 1.0), (j + 1) / (M - 1.0)
        for i in range(N - 1):
            u0, u1 = i / (N - 1.0), (i + 1) / (N - 1.0)
            hA, hB = ra[i] / top, ra[i + 1] / top
            hC, hD = rb[i + 1] / top, rb[i] / top
            colour = ramp(((hA + hB + hC + hD) * 0.25) ** gamma)
            quad = [project(u0, v0, hA), project(u1, v0, hB),
                    project(u1, v1, hC), project(u0, v1, hD)]
            fill_quad(rows, W, H, quad, colour)
            # Stroke the edges too: where the surface turns nearly vertical the
            # scanline fill leaves hairline slivers of whatever was behind.
            for k in range(4):
                x0, y0 = quad[k]
                x1, y1 = quad[(k + 1) % 4]
                line(rows, W, H, x0, y0, x1, y1, colour, 1.0)

    return png(os.path.join(IMG, "og.png"), W, H, rows)


def main():
    os.makedirs(IMG, exist_ok=True)
    print("integrating the Lugiato-Lefever equation ...")

    rule = LLE(n=256, L=30.0, S=2.0, theta=4.0).seed(6, vacancy=4)
    rule.step(1200)
    values = rule.step(400)
    print("  rule      peak %.2f" % max(values))
    print("  wrote", make_soliton_rule(values))
    print("  wrote", make_favicon(values))

    sim = LLE(n=128, L=20.0, S=2.0, theta=4.0).seed(5, vacancy=3)
    sim.step(1200)
    traces = [sim.step(48) for _ in range(64)]
    print("  og        peak %.2f, %d rows" % (max(max(t) for t in traces), len(traces)))
    print("  wrote assets/img/og.png (%d bytes)" % make_og(traces))


if __name__ == "__main__":
    main()

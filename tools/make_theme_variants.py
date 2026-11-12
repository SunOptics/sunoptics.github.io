#!/usr/bin/env python3
"""
make_theme_variants.py — give every figure a version for the other colour theme.

    python3 tools/make_theme_variants.py      # needs Pillow

Figures in data/media.json carry "ground": "dark" (drawn on black) or
"ground": "light" (drawn on white).  For each one this writes the opposite
version next to the original — foo.png -> foo-light.png or foo-dark.png —
by inverting perceptual lightness (CIELAB L*) while keeping hue and chroma:
the black ground turns white, white labels turn black, and a red stays red.
build.py then shows whichever version matches the visitor's theme.

A figure may also set "neutralise_yellow": true.  The homepage render's colour
map runs through dark olive at low intensity, which after inversion reads as a
muddy yellow halo; this pulls yellow-olive hues to grey in the light version
only, leaving pink and blue untouched.  (Not for diagrams, where yellow means
something.)

Every version is also written as WebP next to its PNG; pages use the WebP and
the PNG stays as the source (and as the link-preview image, where WebP is not
reliably supported).

Run it after adding or replacing a figure, and commit the output.
"""

import json
import math
import os

from PIL import Image, ImageCms

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLACK = (3, 4, 3)  # the hero's backdrop, so a transparent render flattens the same way


def variant_path(src, ground):
    stem, ext = os.path.splitext(src)
    return "%s-%s%s" % (stem, "light" if ground == "dark" else "dark", ext)


def invert_lightness(im, ground):
    im = im.convert("RGBA")
    if ground == "dark":
        # A transparent render on a dark ground: flatten onto that ground first.
        flat = Image.new("RGBA", im.size, BLACK + (255,))
        flat.alpha_composite(im)
        alpha, rgb = None, flat.convert("RGB")
    else:
        alpha, rgb = im.getchannel("A"), im.convert("RGB")
    srgb, lab = ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB")
    to_lab = ImageCms.buildTransformFromOpenProfiles(srgb, lab, "RGB", "LAB")
    to_rgb = ImageCms.buildTransformFromOpenProfiles(lab, srgb, "LAB", "RGB")
    L, a, b = ImageCms.applyTransform(rgb, to_lab).split()
    out = ImageCms.applyTransform(Image.merge("LAB", (L.point(lambda v: 255 - v), a, b)), to_rgb)
    if alpha is not None and alpha.getextrema() != (255, 255):
        out.putalpha(alpha)
    return out


def neutralise_yellow(rgb, lo=55, hi=125, keep=0.15, ramp=20):
    """Shrink CIELAB chroma to `keep` for hues within [lo, hi] degrees,
    ramping over `ramp` degrees either side so there is no visible seam."""
    srgb, lab = ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB")
    to_lab = ImageCms.buildTransformFromOpenProfiles(srgb, lab, "RGB", "LAB")
    to_rgb = ImageCms.buildTransformFromOpenProfiles(lab, srgb, "LAB", "RGB")
    L, a, b = ImageCms.applyTransform(rgb, to_lab).split()
    A, B = list(a.getdata()), list(b.getdata())
    for i, (x, y) in enumerate(zip(A, B)):
        x, y = x - 128, y - 128
        if not (x or y):
            continue
        hue = math.degrees(math.atan2(y, x)) % 360
        edge = min(hue - (lo - ramp), (hi + ramp) - hue) / ramp
        if edge > 0:
            f = 1 - (1 - keep) * min(1.0, edge)
            A[i], B[i] = int(round(x * f)) + 128, int(round(y * f)) + 128
    a.putdata(A)
    b.putdata(B)
    return ImageCms.applyTransform(Image.merge("LAB", (L, a, b)), to_rgb)


def webp_path(path):
    return os.path.splitext(path)[0] + ".webp"


def save_webp(im, path):
    im.save(webp_path(path), "WEBP", quality=88, method=6)


def main():
    with open(os.path.join(ROOT, "data", "media.json"), encoding="utf-8") as fh:
        media = json.load(fh)
    for fig in [media["share"]] + media["figures"]:
        ground = fig.get("ground")
        if ground not in ("dark", "light"):
            continue
        src = os.path.join(ROOT, fig["src"])
        dst = os.path.join(ROOT, variant_path(fig["src"], ground))
        other = invert_lightness(Image.open(src), ground)
        if fig.get("neutralise_yellow") and ground == "dark":
            other = neutralise_yellow(other.convert("RGB"))
        other.save(dst, optimize=True)
        save_webp(other, dst)
        save_webp(Image.open(src), src)
        print("wrote", os.path.relpath(dst, ROOT), "+ WebP of both versions")


if __name__ == "__main__":
    main()

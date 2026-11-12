#!/usr/bin/env python3
"""
fetch_google_assets.py — pull the images and video thumbnails off the old
Google Sites page into assets/, so the new site serves its own copies.

    python3 tools/fetch_google_assets.py

Run once. The googleusercontent URLs are not permanent, which is exactly why
the files are downloaded and committed rather than hot-linked. The YouTube
thumbnails are fetched too, so that a visitor's browser never talks to Google
until they actually press play.
"""

import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

GUC = "https://lh3.googleusercontent.com/sitesv/"

# Page banners, one per page of the old site.
BANNERS = {
    "home": "AG8ngQUJKFWdSbmg2cFdQlQXsKVZ2wtMy814IoX0US5mHYQIhYZGVAey0eMqPd3rYUtxHP8RrXEhbj45l-tlrdrtSBc4OoxDCZErMSO22mRcR_H8dVlZcylkUBRfgxACeZ5sqbMcFYB1DWVDyV28uWr2DX0pxQcJizNjuKPtWQXNlpJQk-TaIvY6tCFk_POPi78",
    "research": "AG8ngQVCeO1dbAf8p4dysx6CcvSz6pTt838bkTfrKBO5esNCcPDWCg1f0RPzP7cu4G8FPBAhhYYOZpz0GjnQYDG7U7eluA5xNrMZ27wlLW-oZhAY332OghoEveuIKNBYceIAqK5tyzclds1TbtBMbGtZ0HBslOJu0f7VG3ubhlexcFq0Tk36-NM3ACodzA60Dg0",
    "publications": "AG8ngQV9PkG6W_p9eATDWz9e5-Z8yQR_ZZWVatF4AkguDblziAThJqAcYZqTDRDD_Y56s327f50KvKH_mnT7vZBF2MMBeXASlb1pasUJ-49v-qXSrZ3g4_31c5olBzVxIZ2dN9z8v3WuTzFKJrPbq1Y8CN7ki9FvZkPh4T7M6YLVNOWB5CIDrB78_ORyZsT--_M",
    "projects": "AG8ngQU6m4GcYiWXDdhbGeUt5Pp2r13Lz7QKi3xqtYTwfZU1aOmdA4wxvzn-IF9lzQ77c-bRN4ks7D7vzzZtKYdREhdE0reYWmWl8BSLM9pBT9--UwBWnMp0tStjUT5Lcr36ZCsSfnsVAkX0SD3GbpV4Kgu6lk24WlYb4g1seOYX5IJ-FPT811yC0-icDczZDjQ",
    "background": "AG8ngQXxshTRFNw6YKOyN7XxzPSbki1HlePQbfaHUCy5D3MWVWsKVG_hvmx3ElstdG5LWfbJ8gd_2MDug69eBFpXZVLOUxysq6YAa67xGJZfDKxvwRnwzWMBaXt0e9E7by49avKiemMtt79aTrn9dCYQ-K50mkdV6pj3MtomatnjCfkO2SKoqA2ouy6LGvdWuLI",
    "videos": "AG8ngQUHxPcxtl69fdJcsBANu8XXNC715XtJtHKVeGaJlX8a2c0VExVfOb_ZlmNOX884RLz9IC_efHQEOpAQ8ZxyNEWIwnhGvPTz9sDalnJUhPlQKC1jCDaqb_YumMmrBe2YOJ5MeKp6itwnp4DbvK7UlNTb8jydrMjsDs-GJL4SntrCM5k1SsGB8xR9y-wMImg",
    "travels": "AG8ngQWVzfiUfYdGhuqpj5miwdVrX6GsLYUH4e1Iaa7P4-CqAwuoe8zs5PoRHvdlBXiudkMU_YUZq34LiqDHgVWhOWg52d_KugkbHGovVAlNKxojwzwDSgaF9p9yA9bWdaxGB8dPAPAbvuhARyBLGDWyE9fr-Ag7FSCcgAPXXgEQtkdFaj8fQw8GpPHhUEvuzgg",
}

# Figures embedded in the body of the Research page, in document order.
FIGURES = [
    ("noise-pathways", "AG8ngQVy7VHvynyh0uxlVkbqpba7hhtv2WTfhOVuG7GDYq9OjeRm1tOCGU-a95eqhuzSoyIcoYdAKwWlzZ8H9v-Ets0LjvBIZlppU9rDzWyc0T35A9rs0GlkHcWucpiIXsufFTo_YuISDFoXLfQwG0NobG0jRcK2d34TKGj4HZe4HQb8fmUY-D5_j85LL8Qfhl5La73OL3ciIfaMRtM24CVQZKPXdju5Zp52IRvLN3HNnnk"),
    ("parametric-soliton-crystals", "AG8ngQV7b9cisCDd2MG73R0LEWQBgCn_p2Ze33sFytg43NfLMVVNEH7u3OaLjvhu0BsLTot-GcQpugyust626vh4t7VhRdlqs4x0g63L9X9eWc09VzDIWtxL8y1hUZKTWC5_7cTEFPOybJw6TYFEFadljsaPLXVOAsNcJKD59glQvXcFaCIjX7NSuyw7vv2KsCudiw1t920NglHDtsO3PJL3_WVjBaAtNr8dq_BomyAY"),
    ("cavity-dimensions", "AG8ngQUsEWC1szQALiFK3j17C_FUEiRlf4CqAJJIS9VYzV17G8HXm2vnUT4be26oEVyaFK4Zg462Gr1OYYJnoHt0-yANlkDypIvPL8nsLPY_XnkBJUC38olRsHo4J8B_e4fRmSEl7_pw1RUIcGjYpTOfx1oI4V-OUVVfxnjWzGlDCfCS52vvtLCidbEweL4EDYPFGVk_eDlblHMGhQGwJlBv2DhzTCXmclX3pfOrNkF9G20"),
    ("multimode-solitons", "AG8ngQX564kIybKiGsi6JEsDJuzU9Auc7OVXQMZWfXb9fTq5P6s_MqL28tGZ3XY4Y_K63CXOjAve8nNOp7n-6CNjxZaGv8xk_yQs74b6Nwn4tgjAcHI9H9lGaJZwQYl10H5tEWtBKqXMl-ov8AkW94so-Wo9EVZWVRslEeJqHkDUEJxpRBBB8wTgJ2tPuExo4aWh6Xjw0V6fnVqvppP14hGX5Fhp1WW7-FAS8QgiSNOUm0Q"),
    ("nanolaser-modes", "AG8ngQUr4CmrZQsNX6Ijg02QtQXEp2GciGX-Zg_vFpSZ_N8DTMOLGz1tllnGCU4QI0tA0leCkYfQIkoD4ZhJ7JQPf18Xl4HowtIOkNhWgIpCGnBd6gfmpUOxLyiBU9hHQIQMbGMliNCgJXQhVWJ5nxuDskCDg0-ZrPWw8lP83un0Y9KpmuD9sz5xFdH8srdVOC5zKxG4T4nO9It8OpH4I7Tf4ZX-HlqMrsMSahWxxFB54eg"),
]

VIDEO_IDS = [
    "atkTpMimGkU", "-vWOQzNRxHg", "p08_3cc0Og4", "QpL-oRu6uGM", "hV5qaBMS-v0",
    "txN03Qrn2tk", "Ja9K2Pd7rpE", "Vhz-yL41sB0", "8m6zLcjVdes", "HF54n4i0Qgc",
    "q9IdulS_6O8", "4jfRCjd47CY", "g7jRTYVUZK8", "_OSp7mxS1as", "pnjt5DG8-Qg",
    "7fObrzTnA7c",
    # Travels
    "8tvucthlpwg", "OYiAq1oJEzc", "FAAG4fu-wTY", "zhFmArFooEk", "lGcIVs32MHo",
    "BEYywTXuSAQ",
]


# The googleusercontent URLs are signed for the exact size the old page asked
# for; any other "=w..." suffix comes back 403. Try the ones it actually used.
SIZES = ("=w16383", "=w1280", "=w1600", "=w2000", "=w976")


def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 2000:
        return os.path.getsize(dest), True
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 2000:
        raise IOError("suspiciously small response for %s" % url)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        dest = os.path.splitext(dest)[0] + ".png"
    elif data[:2] == b"\xff\xd8":
        dest = os.path.splitext(dest)[0] + ".jpg"
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data), False


def get_sized(token, dest):
    last = None
    for size in SIZES:
        try:
            return get(GUC + token + size, dest)
        except Exception as exc:
            last = exc
    raise last


def main():
    ok = fail = 0
    for name, token in BANNERS.items():
        dest = os.path.join(IMG, "banners", name + ".png")
        try:
            n, cached = get_sized(token, dest)
            print("  banner  %-14s %8d bytes%s" % (name, n, "  (cached)" if cached else ""))
            ok += 1
        except Exception as exc:
            print("  banner  %-14s FAILED: %s" % (name, exc)); fail += 1

    for name, token in FIGURES:
        dest = os.path.join(IMG, "figures", name + ".png")
        try:
            n, cached = get_sized(token, dest)
            print("  figure  %-34s %8d bytes%s" % (name, n, "  (cached)" if cached else ""))
            ok += 1
        except Exception as exc:
            print("  figure  %-34s FAILED: %s" % (name, exc)); fail += 1

    for vid in VIDEO_IDS:
        dest = os.path.join(IMG, "thumbs", vid + ".jpg")
        got = False
        for quality in ("maxresdefault", "hqdefault"):
            try:
                n, cached = get("https://i.ytimg.com/vi/%s/%s.jpg" % (vid, quality), dest)
                print("  thumb   %-14s %8d bytes  (%s)%s" % (vid, n, quality, "  cached" if cached else ""))
                ok += 1
                got = True
                break
            except Exception:
                continue
        if not got:
            print("  thumb   %-14s FAILED" % vid); fail += 1

    print("\n%d downloaded, %d failed" % (ok, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())

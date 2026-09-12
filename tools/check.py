#!/usr/bin/env python3
"""
check.py — lint the data and the built site.

    python3 tools/check.py

Run it after tools/build.py. It exists because the old site shipped a Phys.
Rev. Lett. paper carrying an Optics-Express DOI copied from another entry, and
that class of mistake should be impossible to ship twice.
"""

import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

ERRORS = []
WARNINGS = []
CHECKS = [0]

TYPES = {"journal", "preprint", "chapter", "conference"}
ROLES = {"first", "corresponding", "co"}
STATUS = {"published", "accepted", "preprint", "upcoming"}
TOPICS = {"cavity-solitons", "multimode-fiber", "nanolasers", "noise", "other"}
REQUIRED = {"id", "type", "authors", "title", "venue", "year", "role", "status",
            "topic", "selected"}


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def check(msg):
    CHECKS[0] += 1


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


class IdCollector(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.ids = []
        self.hrefs = []
        self.assets = []
        self.imgs_without_alt = 0
        self.headings = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "link" and a.get("href", "").startswith("/"):
            self.assets.append(a["href"])
        if tag == "script" and a.get("src", "").startswith("/"):
            self.assets.append(a["src"])
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt += 1
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))


def check_publications(pubs):
    ids = [p["id"] for p in pubs]
    for slug, n in Counter(ids).items():
        if n > 1:
            err("publications.json: duplicate id %r (%d times)" % (slug, n))
    check("unique ids")

    dois = [(p["doi"].lower(), p["id"]) for p in pubs if p.get("doi")]
    seen = {}
    for doi, pid in dois:
        if doi in seen:
            err("publications.json: DOI %s is on two entries (%s and %s) — one of "
                "them is a copy-paste error" % (doi, seen[doi], pid))
        seen[doi] = pid
    check("unique DOIs")

    for p in pubs:
        missing = REQUIRED - set(p)
        if missing:
            err("publications.json: %s is missing %s" % (p.get("id"), sorted(missing)))
        if p.get("type") not in TYPES:
            err("publications.json: %s has type %r" % (p["id"], p.get("type")))
        if p.get("role") not in ROLES:
            err("publications.json: %s has role %r" % (p["id"], p.get("role")))
        if p.get("status") not in STATUS:
            err("publications.json: %s has status %r" % (p["id"], p.get("status")))
        if p.get("topic") not in TOPICS:
            err("publications.json: %s has topic %r" % (p["id"], p.get("topic")))
        if not p.get("authors"):
            err("publications.json: %s has no authors" % p["id"])
        if p.get("doi") and not re.match(r"^10\.\d{4,9}/", p["doi"]):
            err("publications.json: %s has a malformed DOI %r" % (p["id"], p["doi"]))
        if p.get("arxiv") and not re.match(r"^\d{4}\.\d{4,5}$", str(p["arxiv"])):
            err("publications.json: %s has a malformed arXiv id %r" % (p["id"], p["arxiv"]))
        if p.get("year") and not (1990 <= int(p["year"]) <= 2100):
            err("publications.json: %s has year %r" % (p["id"], p["year"]))
        if p["type"] == "chapter" and not p.get("book"):
            warn("publications.json: chapter %s has no host book title" % p["id"])
        if "Y. Sun" not in [a.rstrip("*") for a in p.get("authors", [])]:
            warn("publications.json: %s does not list Y. Sun as an author" % p["id"])
    check("field values")

    sel = [p for p in pubs if p.get("selected")]
    for p in sel:
        if not isinstance(p.get("blurb"), str) or not p["blurb"].strip():
            err("publications.json: selected entry %s has no blurb" % p["id"])
    check("selected set")


def check_research(research, pubs):
    known = {p["id"] for p in pubs}
    refs = []
    for s in research["strands"]:
        refs += [(s["id"], pid) for pid in s.get("pubs", [])]
        for note in s.get("notes", []):
            refs += [(s["id"], pid) for pid in note.get("pubs", [])]
    for where, pid in refs:
        if pid not in known:
            err("research.json: strand %s references unknown publication %r" % (where, pid))
    check("%d publication references resolve" % len(refs))

    blob = json.dumps(research, ensure_ascii=False)
    for bad, why in [(r"~\[", "LaTeX non-breaking space"),
                     (r"(?<!<)--(?!>)", "LaTeX double hyphen"),
                     (r"\[\d+[,\-–]?\d*\]", "bracketed numeric citation"),
                     (r"carreer", "typo"),
                     (r"accpetd", "typo")]:
        for m in set(re.findall(bad, blob)):
            err("research.json: contains %s (%s) — citations belong in the "
                "\"pubs\" arrays, not in the prose" % (repr(m), why))
    check("prose is clean")


def check_news(news):
    for item in news["news"]:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", item["date"]):
            err("news.json: %r is not an ISO date" % item["date"])
        link = item.get("link")
        if not link:
            continue
        href = link["href"]
        if not href.startswith(("https://", "mailto:", "/")):
            err("news.json: %r is not an absolute https link" % href)
        m = re.match(r"^https://doi\.org/(.+)$", href)
        if m and not re.match(r"^10\.\d{4,9}/", m.group(1)):
            err("news.json: malformed DOI link %s — an arXiv id needs "
                "https://arxiv.org/abs/<id>, not a bare 10.48550 prefix" % href)
    dates = [i["date"] for i in news["news"]]
    if dates != sorted(dates, reverse=True):
        warn("news.json: items are not in reverse-chronological order")
    check("news items")


def check_media(media, research):
    """Every picture on the site is a file in this repository. Nothing is
    hot-linked to googleusercontent, whose URLs expire."""
    figs = {f["id"]: f for f in media["figures"]}
    vids = {v["id"]: v for v in media["videos"]}

    for path in [media["share"]["src"]] + [f["src"] for f in media["figures"]] \
            + [v["thumb"] for v in media["videos"]]:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            err("media.json: %s is referenced but not in the repository" % path)
        elif os.path.getsize(full) < 2000:
            err("media.json: %s is suspiciously small (%d bytes)"
                % (path, os.path.getsize(full)))
    check("%d media files present" % (1 + len(media["figures"]) + len(media["videos"])))

    for f in media["figures"]:
        if not f.get("alt"):
            err("media.json: figure %s has no alt text" % f["id"])
        if not f.get("caption"):
            err("media.json: figure %s has no caption" % f["id"])
    if not media["share"].get("alt"):
        err("media.json: the share image has no alt text")

    for v in media["videos"]:
        if v.get("group") not in ("cavity", "fiber", "travel"):
            err("media.json: video %s has group %r" % (v["id"], v.get("group")))
        if not v.get("title"):
            err("media.json: video %s has no title" % v["id"])

    for s2 in research["strands"]:
        for fid in s2.get("figures", []):
            if fid not in figs:
                err("research.json: strand %s references unknown figure %r" % (s2["id"], fid))
        for vid in s2.get("videos", []):
            if vid not in vids:
                err("research.json: strand %s references unknown video %r" % (s2["id"], vid))
    check("figure and video references")


def check_site(site):
    for path, meta in site["meta"].items():
        t, d = len(meta["title"]), len(meta["desc"])
        if not 26 <= t <= 60:
            err("site.json: title for %s is %d chars (want 26-60)" % (path, t))
        if not 130 <= d <= 155:
            err("site.json: description for %s is %d chars (want 130-155)" % (path, d))
    check("meta lengths")

    blob = json.dumps(site, ensure_ascii=False)
    for ph in ("REPLACE_ME", "TODO", "FIXME", "example.com"):
        if ph in blob:
            err("site.json: still contains the placeholder %r" % ph)
    for p in site["pages"]:
        if p["href"] not in site["meta"]:
            err("site.json: page %s has no meta entry" % p["href"])
    check("no placeholders")


def check_built():
    pages = ["index.html", "research/index.html", "publications/index.html",
             "gallery/index.html", "cv/index.html", "404.html"]
    all_ids = {}
    all_hrefs = {}
    for page in pages:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            err("built site: %s is missing — run tools/build.py" % page)
            continue
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        c = IdCollector()
        c.feed(html)
        for i, n in Counter(c.ids).items():
            if n > 1:
                err("%s: duplicate id %r appears %d times" % (page, i, n))
        all_ids[page] = set(c.ids)
        all_hrefs[page] = c.hrefs
        if c.imgs_without_alt:
            err("%s: %d <img> without alt" % (page, c.imgs_without_alt))
        if c.headings and c.headings.count(1) != 1:
            warn("%s: %d <h1> elements (want exactly 1)" % (page, c.headings.count(1)))
        prev = 0
        for h in c.headings:
            if prev and h > prev + 1:
                warn("%s: heading level jumps from h%d to h%d" % (page, prev, h))
            prev = h
        if "REPLACE_ME" in html:
            err("%s: unreplaced REPLACE_ME in the output" % page)
        for ph in set(re.findall(r"\{\{[A-Z_]+\}\}", html)):
            err("%s: unreplaced template placeholder %s" % (page, ph))

        for ref in c.assets:
            # content-hashed URLs carry a ?v= query that is not part of the path
            target = ref.split("?")[0].lstrip("/")
            if not os.path.exists(os.path.join(ROOT, target)):
                err("%s: references %s, which does not exist" % (page, ref))

    # Resolve fragments after all pages have been parsed, including links to
    # pages later in the list. Publication filter hashes are application state.
    for page, hrefs in all_hrefs.items():
        for href in hrefs:
            parts = urlsplit(href)
            target = None
            if href.startswith("#"):
                target = page
            elif href.startswith("/") and not parts.netloc:
                base = unquote(parts.path)
                target = base.strip("/") + "/index.html" if base.endswith("/") else base.lstrip("/")
                if base == "/":
                    target = "index.html"
                if not os.path.exists(os.path.join(ROOT, target)):
                    err("%s: link %s points at a file that does not exist (%s)"
                        % (page, href, target))
            elif href.startswith("mailto:"):
                if "@" not in href:
                    err("%s: malformed mailto %s" % (page, href))
            fragment = unquote(parts.fragment)
            is_filter = target == "publications/index.html" and fragment.startswith("filter=")
            if target in all_ids and fragment and not is_filter and fragment not in all_ids[target]:
                err("%s: link %s has no matching id in %s" % (page, href, target))
    check("built pages")

    html_all = ""
    for page in pages:
        fp = os.path.join(ROOT, page)
        if os.path.exists(fp):
            with open(fp, encoding="utf-8") as fh:
                html_all += fh.read()
    if "googleusercontent.com" in html_all or "i.ytimg.com" in html_all:
        err("the built site still hot-links an image from Google; run "
            "tools/fetch_google_assets.py and point media.json at the local copy")
    check("no hot-linked images")

    for f in ["assets/css/site.css", "assets/css/fonts.css", "assets/js/site.js",
              "assets/js/video.js", "assets/js/pubs.js",
              "assets/img/favicon.svg",
              "assets/img/banners/home.png",
              "sitemap.xml", "robots.txt", "feed.xml", ".nojekyll"]:
        if not os.path.exists(os.path.join(ROOT, f)):
            err("missing file: %s" % f)
    font_css_path = os.path.join(ROOT, "assets", "css", "fonts.css")
    if os.path.exists(font_css_path):
        with open(font_css_path, encoding="utf-8") as fh:
            css = re.sub(r"/\*.*?\*/", "", fh.read(), flags=re.S)
        font_urls = re.findall(r"url\(\s*['\"]?([^\s)'\"]+)['\"]?\s*\)", css)
        if not font_urls:
            err("assets/css/fonts.css: no font files referenced")
        for ref in font_urls:
            parts = urlsplit(ref)
            if parts.scheme or parts.netloc:
                err("assets/css/fonts.css: font URL %s must refer to a local file" % ref)
                continue
            path = unquote(parts.path)
            target = os.path.join(ROOT, path.lstrip("/")) if path.startswith("/") \
                else os.path.join(os.path.dirname(font_css_path), path)
            if not os.path.isfile(target):
                err("assets/css/fonts.css: references missing font %s" % ref)
    check("assets")

    for name in ("feed.xml", "sitemap.xml"):
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            try:
                ElementTree.parse(path)
            except ElementTree.ParseError as exc:
                err("%s: invalid XML (%s)" % (name, exc))
    check("feed and sitemap XML")


def main():
    pubs = load("publications.json")["publications"]
    check_publications(pubs)
    check_research(load("research.json"), pubs)
    check_news(load("news.json"))
    research = load("research.json")
    check_media(load("media.json"), research)
    check_site(load("site.json"))
    check_built()

    for w in WARNINGS:
        print("  warning: %s" % w)
    for e in ERRORS:
        print("  ERROR:   %s" % e)
    print("\n%d checks, %d publications, %d warnings, %d errors"
          % (CHECKS[0], len(pubs), len(WARNINGS), len(ERRORS)))
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())

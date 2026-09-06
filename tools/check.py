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
    if len(sel) != 5:
        err("publications.json: %d entries are selected; the front page is laid out "
            "for exactly 5" % len(sel))
    for p in sel:
        if not p.get("blurb"):
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

        for href in c.hrefs:
            if href.startswith("#"):
                if href[1:] and href[1:] not in all_ids[page]:
                    err("%s: in-page link %s has no matching id" % (page, href))
            elif href.startswith("/"):
                base = href.split("#")[0]
                target = base.strip("/") + "/index.html" if base.endswith("/") else base.lstrip("/")
                if base == "/":
                    target = "index.html"
                if not os.path.exists(os.path.join(ROOT, target)):
                    err("%s: link %s points at a file that does not exist (%s)"
                        % (page, href, target))
            elif href.startswith("mailto:"):
                if "@" not in href:
                    err("%s: malformed mailto %s" % (page, href))
    check("built pages")

    for f in ["assets/css/site.css", "assets/css/fonts.css", "assets/js/site.js",
              "assets/js/lle.js", "assets/js/surface.js", "assets/js/pubs.js",
              "assets/img/favicon.svg", "assets/img/og.png", "assets/img/soliton-rule.svg",
              "sitemap.xml", "robots.txt", "feed.xml", ".nojekyll"]:
        if not os.path.exists(os.path.join(ROOT, f)):
            err("missing file: %s" % f)
    fonts = [f for f in os.listdir(os.path.join(ROOT, "assets", "fonts"))
             if f.endswith(".woff2")]
    if len(fonts) < 4:
        err("assets/fonts: expected 4 woff2 files, found %d" % len(fonts))
    css = open(os.path.join(ROOT, "assets", "css", "fonts.css"), encoding="utf-8").read()
    for host in ("fonts.googleapis.com", "fonts.gstatic.com"):
        if host in css:
            err("assets/css/fonts.css references %s — the fonts are meant to be "
                "self-hosted so no visitor IP reaches Google" % host)
    check("assets")


def main():
    pubs = load("publications.json")["publications"]
    check_publications(pubs)
    check_research(load("research.json"), pubs)
    check_news(load("news.json"))
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

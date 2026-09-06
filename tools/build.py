#!/usr/bin/env python3
"""
build.py — render the static site from data/*.json.

    python3 tools/build.py

No dependencies, no node, no network.  Everything a visitor sees is in the
served HTML: nothing that matters is assembled by JavaScript, because Bing,
Google Scholar's crawler and every link unfurler read the bytes, not the DOM.

To add a paper: edit data/publications.json and run this script.
"""

import hashlib
import html
import json
import os
import re
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TPL = os.path.join(ROOT, "tools", "templates")

ME = "Y. Sun"

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------- utilities

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def e(text):
    """Escape a plain-text value for HTML."""
    return html.escape("" if text is None else str(text), quote=True)


def write(relpath, content):
    path = os.path.join(ROOT, relpath)
    os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return relpath


_ASSET_CACHE = {}


def asset(path):
    """Append a short content hash to a stylesheet or script URL. Without it a
    returning visitor keeps last month's CSS against this month's markup."""
    if path not in _ASSET_CACHE:
        full = os.path.join(ROOT, path.lstrip("/"))
        with open(full, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:8]
        _ASSET_CACHE[path] = "%s?v=%s" % (path, digest)
    return _ASSET_CACHE[path]


def ym(value):
    """'2024-06' -> 'Jun 2024'; '2024' -> '2024'; None -> 'present'."""
    if not value:
        return "present"
    parts = str(value).split("-")
    if len(parts) == 1:
        return parts[0]
    return "%s %s" % (MONTHS[int(parts[1])][:3], parts[0])


def iso_long(value):
    d = datetime.strptime(value, "%Y-%m-%d").date()
    return "%s %s %s" % (d.day, MONTHS[d.month][:3], d.year)


# ------------------------------------------------------------- citation bits

def authors_html(names):
    """Author list with the site owner weight-marked — non-negotiable on an
    academic site — and a corresponding-author asterisk in the mark colour."""
    out = []
    for name in names:
        clean = name.rstrip("*")
        star = '<span class="corr" title="Corresponding author">*</span>' if name.endswith("*") else ""
        if clean == ME:
            out.append('<span class="me">%s</span>%s' % (e(clean), star))
        else:
            out.append(e(clean) + star)
    if len(out) > 1:
        return ", ".join(out[:-1]) + " and " + out[-1]
    return out[0] if out else ""


def venue_html(p):
    """Journal style: *Venue* vol, pages (year) — the year takes a space, not
    a comma, or the line reads "8, 03LT01, (2026)"."""
    bits = []
    if p["type"] == "chapter":
        if p.get("book"):
            bits.append("In <cite>%s</cite>" % e(p["book"]))
        if p.get("pages"):
            bits.append('<span class="m">pp.&nbsp;%s</span>' % e(p["pages"]))
        if p.get("venue"):
            bits.append(e(p["venue"]))
    elif p["type"] == "conference":
        if p.get("venue"):
            bits.append("<cite>%s</cite>" % e(p["venue"]))
        if p.get("location"):
            bits.append(e(p["location"]))
    else:
        head = ""
        if p.get("venue"):
            head = "<cite>%s</cite>" % e(p["venue"])
        vp = []
        if p.get("volume"):
            vp.append(e(p["volume"]))
        if p.get("pages"):
            vp.append(e(p["pages"]))
        if vp:
            head = (head + " " if head else "") + '<span class="m">%s</span>' % ", ".join(vp)
        if head:
            bits.append(head)
    line = ", ".join(bits)
    if p.get("year"):
        line += ('&nbsp;' if line else "") + '<span class="m">(%s)</span>' % e(p["year"])
    return line


def badges_html(p):
    out = ""
    if p.get("invited"):
        out += '<span class="badge">Invited</span>'
    if p.get("award"):
        out += '<span class="badge">%s</span>' % e(p["award"])
    if p.get("status") == "accepted":
        out += '<span class="badge">Accepted</span>'
    if p.get("status") == "upcoming":
        out += '<span class="badge">Upcoming</span>'
    if p.get("presentation") in ("oral", "poster"):
        out += '<span class="badge">%s</span>' % e(p["presentation"])
    return out


def links_html(p):
    items = []
    if p.get("doi"):
        items.append('<li><a href="https://doi.org/%s" rel="noopener">DOI</a></li>' % e(p["doi"]))
    if p.get("arxiv"):
        items.append('<li><a href="https://arxiv.org/abs/%s" rel="noopener">arXiv</a></li>' % e(p["arxiv"]))
    if not items:
        return ""
    return '<ul class="pub-links">%s</ul>' % "".join(items)


def pub_html(p, number=None, blurb=False, anchor=True, level=3):
    href = None
    if p.get("doi"):
        href = "https://doi.org/%s" % p["doi"]
    elif p.get("arxiv"):
        href = "https://arxiv.org/abs/%s" % p["arxiv"]
    title = e(p["title"])
    title_html = '<a href="%s" rel="noopener">%s</a>' % (e(href), title) if href else title
    num = '<div class="pub-n m">%s</div>' % (e(number) if number is not None else "")
    blurb_html = ('<p class="pub-blurb">%s</p>' % e(p["blurb"])) if (blurb and p.get("blurb")) else ""
    idattr = ' id="%s"' % e(p["id"]) if anchor else ""
    return (
        '<li class="pub"%s>%s<div>'
        '<h%d class="pub-title">%s%s</h%d>'
        '%s'
        '<p class="pub-authors">%s</p>'
        '<p class="pub-venue">%s</p>'
        '%s</div></li>'
    ) % (idattr, num, level, badges_html(p), title_html, level, blurb_html,
         authors_html(p["authors"]), venue_html(p), links_html(p))


# --------------------------------------------------------------- page shell

def header_html(site, active):
    items = []
    for page in site["pages"]:
        cur = ' aria-current="page"' if page["href"] == active else ""
        items.append('<li><a href="%s"%s>%s</a></li>' % (e(page["href"]), cur, e(page["label"])))
    return (
        '<header class="site-header"><div class="spine"><div class="header-inner">'
        '<a class="brand" href="/">%s</a>'
        '<nav class="nav" aria-label="Main"><ul>%s</ul></nav>'
        '<button class="theme-toggle" type="button">auto</button>'
        '</div></div></header>'
    ) % (e(site["name"]), "".join(items))


def footer_html(site):
    mails = "".join(
        '<li><a href="mailto:%s">%s</a></li>' % (e(m["addr"]), e(m["addr"]))
        for m in site["emails"])
    profiles = "".join(
        '<li><a href="%s" rel="noopener me">%s</a></li>' % (e(p["href"]), e(p["label"]))
        for p in site["profiles"])
    pages = "".join(
        '<li><a href="%s">%s</a></li>' % (e(p["href"]), e(p["label"]))
        for p in site["pages"])
    return (
        '<footer class="site-footer"><div class="spine">'
        '<div class="footer-inner">'
        '<div class="footer-block"><h2>Contact</h2><ul class="footer-list">%s</ul></div>'
        '<div class="footer-block"><h2>Profiles</h2><ul class="footer-list">%s</ul></div>'
        '<div class="footer-block"><h2>Pages</h2><ul class="footer-list">%s</ul></div>'
        '</div>'
        '<p class="colophon">%s · %s. '
        'Hand-written HTML and CSS, generated from JSON by a Python script; no framework '
        'and no build service. The surfaces on this site are the nonlinear '
        'Schr&ouml;dinger and Lugiato&ndash;Lefever equations being integrated in your '
        'browser as you read, not videos. '
        '&copy; <span data-year>%s</span> Yifan Sun.</p>'
        '</div></footer>'
    ) % (mails, profiles, pages, e(site["org"]), e(site["place"]), date.today().year)


def jsonld(site, extra=None):
    graph = [
        {
            "@type": "Person",
            "@id": site["origin"] + "/#person",
            "name": site["name"],
            "givenName": "Yifan",
            "familyName": "Sun",
            "jobTitle": site["role"],
            "description": site["lede"],
            "url": site["origin"] + "/",
            "email": "mailto:" + site["emails"][0]["addr"],
            "affiliation": {"@type": "Organization", "name": site["org"]},
            "knowsAbout": ["Nonlinear optics", "Cavity solitons", "Kerr frequency combs",
                           "Multimode optical fibers", "Dissipative solitons",
                           "Lugiato-Lefever equation", "Photonics"],
            "sameAs": [p["href"] for p in site["profiles"] if "REPLACE_ME" not in p["href"]],
        },
        {
            "@type": "WebSite",
            "@id": site["origin"] + "/#website",
            "url": site["origin"] + "/",
            "name": site["name"],
            "publisher": {"@id": site["origin"] + "/#person"},
        },
    ]
    if extra:
        graph.extend(extra)
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">%s</script>' % payload


def render(site, path, main, scripts="", extra_ld=None, og_type="website"):
    with open(os.path.join(TPL, "base.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    meta = site["meta"][path]
    canonical = site["origin"] + path
    out = (tpl
           .replace("{{TITLE}}", e(meta["title"]))
           .replace("{{DESC}}", e(meta["desc"]))
           .replace("{{CANONICAL}}", e(canonical))
           .replace("{{ORIGIN}}", e(site["origin"]))
           .replace("{{OG_TYPE}}", og_type)
           .replace("{{JSONLD}}", jsonld(site, extra_ld))
           .replace("{{HEADER}}", header_html(site, path))
           .replace("{{MAIN}}", main)
           .replace("{{FOOTER}}", footer_html(site))
           .replace("{{SCRIPTS}}", scripts)
           .replace("{{CSS_FONTS}}", asset("/assets/css/fonts.css"))
           .replace("{{CSS_SITE}}", asset("/assets/css/site.css"))
           .replace("{{JS_SITE}}", asset("/assets/js/site.js")))
    rel = "index.html" if path == "/" else path.strip("/") + "/index.html"
    return write(rel, out)


# ------------------------------------------------------------------- pages


def hero_html(site, rule_svg, hero):
    eyebrow = " · ".join([site["role"], site["org"], site["place"]]).upper()
    links = ['<li><a href="mailto:%s">Email</a></li>' % e(site["emails"][0]["addr"])]
    for p in site["profiles"]:
        links.append('<li><a href="%s" target="_blank" rel="noopener me">%s</a></li>'
                     % (e(p["href"]), e(p["label"])))
    return (
        '<section class="hero">'
        '<div class="hero-text">'
        '<p class="hero-eyebrow caps">%s</p>'
        '<h1 class="hero-name">%s</h1>'
        '%s'
        '<p class="hero-thesis">%s</p>'
        '<p class="hero-meta caps drule">%s</p>'
        '<ul class="linkrow">%s</ul>'
        '</div>'
        '<div class="hero-figure"><div class="figure-frame">'
        '<img src="/%s" alt="%s" width="%d" height="%d" fetchpriority="high" decoding="async">'
        '</div></div>'
        '</section>'
    ) % (e(eyebrow), e(site["name"]), rule_svg, e(site["thesis"]),
         e(site["tagline"]).replace(" · ", '<span class="sep">·</span>'),
         "".join(links),
         e(hero["src"]), e(hero["alt"]), hero["w"], hero["h"])


def figure_html(fig, wide=True):
    credit = ""
    if fig.get("credit"):
        credit = ' <a href="%s" rel="noopener">%s</a>' % (
            e(fig["credit"]["href"]), e(fig["credit"]["text"]))
    return (
        '<figure class="plate%s" id="fig-%s">'
        '<img src="/%s" alt="%s" width="%d" height="%d" loading="lazy" decoding="async">'
        '<figcaption><strong>%s.</strong> %s%s</figcaption></figure>'
    ) % (" wide" if wide else "", e(fig["id"]), e(fig["src"]), e(fig["alt"]),
         fig["w"], fig["h"], e(fig["title"]), e(fig["caption"]), credit)


def video_html(v):
    """A facade, not an embed: the thumbnail is ours and nothing reaches
    YouTube until the visitor presses play."""
    return (
        '<li class="video">'
        '<button class="video-play" type="button" data-video="%s" data-title="%s">'
        '<img src="/%s" alt="" width="480" height="360" loading="lazy" decoding="async">'
        '<span class="video-cue" aria-hidden="true">&#9654;</span>'
        '<span class="vh">Play: %s</span>'
        '</button>'
        '<p class="video-title">%s</p>'
        '</li>'
    ) % (e(v["id"]), e(v["title"]), e(v["thumb"]), e(v["title"]), e(v["title"]))


def video_grid(videos):
    return '<ul class="video-grid">%s</ul>' % "".join(video_html(v) for v in videos)


def section_head(num, label, title, anchor=None, level=2):
    """level=1 for the first section of a subpage: every page needs exactly one
    h1, and on a subpage that is the page's own title, not the site name."""
    idattr = ' id="%s"' % e(anchor) if anchor else ""
    return (
        '<div class="section-head">'
        '<div class="section-label caps"><span class="section-num">§&nbsp;%s</span>'
        '<span>%s</span></div>'
        '<h%d class="section-title"%s>%s</h%d>'
        '</div>'
    ) % (e(num), e(label), level, idattr, e(title), level)


def news_html(items, limit=None):
    rows = []
    for item in (items[:limit] if limit else items):
        link = ""
        if item.get("link"):
            link = ' <a href="%s" rel="noopener">%s</a>' % (
                e(item["link"]["href"]), e(item["link"]["label"]))
        rows.append(
            '<li class="news-item">'
            '<div class="news-date m"><time datetime="%s">%s</time></div>'
            '<div><h3 class="news-title">%s</h3>'
            '<p class="news-body">%s%s</p></div></li>'
            % (e(item["date"]), e(iso_long(item["date"])), e(item["title"]),
               item["body"], link))
    return '<ul class="news">%s</ul>' % "".join(rows)


def build_home(site, pubs, news, research, rule_svg, media):
    by_id = {p["id"]: p for p in pubs}
    selected = [p for p in pubs if p.get("selected")]

    strands = "".join(
        '<li class="thrust"><h3>%s</h3><p class="tl-note">%s</p>'
        '<p class="caps">%s</p></li>' % (e(s["title"]), e(s["summary"]), e(s["era"]))
        for s in research["strands"])

    main = (
        '<div class="spine">' + hero_html(site, rule_svg, media["hero"]) + '</div>'
        + '<div class="spine">'
        + '<section class="section">'
        + section_head("01", "Research", "What I work on")
        + '<div class="prose"><p class="lede">%s</p>%s</div>' % (
            e(research["programme"]["lede"]), "".join(research["programme"]["body"]))
        + '<ul class="thrusts">%s</ul>' % strands
        + '<p style="margin-top:var(--s5)"><a href="/research/">Read the full research programme</a></p>'
        + '</section>'
        + '<section class="section">'
        + section_head("02", "Selected work", "Five papers")
        + '<ul class="pub-list selected">%s</ul>' % "".join(
            pub_html(p, number=str(i + 1), blurb=True, anchor=False) for i, p in enumerate(selected))
        + '<p style="margin-top:var(--s5)"><a href="/publications/">All %d publications and talks</a></p>' % len(pubs)
        + '</section>'
        + '<section class="section">'
        + section_head("03", "News", "Recent news")
        + news_html(news["news"], limit=6)
        + '</section>'
        + '</div>'
    )
    return render(site, "/", main, og_type="profile")


def build_research(site, pubs, research, rule_svg, media):
    by_id = {p["id"]: p for p in pubs}
    by_fig = {f["id"]: f for f in media["figures"]}
    by_vid = {v["id"]: v for v in media["videos"]}
    prog = research["programme"]

    thrusts = "".join(
        '<li class="thrust"><h2>%s</h2><dl>'
        '<dt class="caps">Goal</dt><dd>%s</dd>'
        '<dt class="caps">Open question</dt><dd>%s</dd>'
        '<dt class="caps">Method</dt><dd>%s</dd>'
        '<dt class="caps">Partners</dt><dd>%s</dd>'
        '</dl></li>' % (e(t["title"]), e(t["goal"]), e(t["question"]),
                        e(t["method"]), e(t["partners"]))
        for t in prog["thrusts"])

    body = []
    note_n = 0
    for s in research["strands"]:
        notes = []
        for note in s.get("notes", []):
            note_n += 1
            refs = []
            for pid in note.get("pubs", []):
                p = by_id.get(pid)
                if not p:
                    continue
                href = ("https://doi.org/%s" % p["doi"]) if p.get("doi") else (
                    "https://arxiv.org/abs/%s" % p["arxiv"] if p.get("arxiv") else
                    "/publications/#%s" % p["id"])
                short = "%s %s" % (p.get("venue") or "", p.get("year") or "")
                refs.append('<a href="%s" rel="noopener">%s</a>' % (e(href), e(short.strip())))
            notes.append(
                '<aside class="sidenote"><span class="sidenote-n">%d</span> %s%s</aside>'
                % (note_n, e(note["text"]),
                   (" " + " · ".join(refs)) if refs else ""))

        # One <aside> per paragraph: more than one stacks via clear:right and
        # drifts away from its anchor.
        paras = list(s["body"])
        woven = []
        for i, para in enumerate(paras):
            if i < len(notes):
                woven.append(notes[i])
            woven.append(para)
        # More asides than paragraphs would stack via clear:right and drift away
        # from their anchors, so the surplus becomes plain inline notes.
        for extra in notes[len(paras):]:
            woven.append(extra.replace('class="sidenote"', 'class="sidenote is-inline"'))

        figs = "".join(figure_html(by_fig[f]) for f in s.get("figures", []) if f in by_fig)
        vids = [by_vid[v] for v in s.get("videos", []) if v in by_vid]
        media_block = figs + (video_grid(vids) if vids else "")

        strand_pubs = [by_id[pid] for pid in s["pubs"] if pid in by_id]
        strand_pubs.sort(key=lambda p: (-(p.get("year") or 0), p["title"]))
        listing = "".join(pub_html(p, number=str(i + 1), anchor=False)
                          for i, p in enumerate(strand_pubs))

        body.append(
            '<section class="section">'
            + section_head(s["num"], s["era"], s["title"], anchor=s["id"])
            + '<div class="prose"><p class="lede">%s</p>%s</div>' % (
                e(s["summary"]), "".join(woven))
            + media_block
            + '<h3 class="caps" style="margin-top:var(--s7)">Publications from this strand</h3>'
            + '<ul class="pub-list">%s</ul>' % listing
            + '</section>')

    main = (
        '<div class="spine">'
        '<section class="section">'
        + section_head("00", "Overview", "Research programme", anchor="programme", level=1)
        + '<div class="prose"><p class="lede">%s</p>%s</div>' % (
            e(prog["lede"]), "".join(prog["body"]))
        + '<ul class="thrusts">%s</ul>' % thrusts
        + '</section>'
        + rule_svg
        + "".join(body)
        + '</div>'
    )
    return render(site, "/research/", main,
                  '<script src="%s" defer></script>' % asset('/assets/js/video.js'))


TOPIC_LABEL = {
    "cavity-solitons": "Cavity solitons",
    "multimode-fiber": "Multimode fibre",
    "nanolasers": "Nanolasers",
    "noise": "Noise",
    "other": "Other",
}
TYPE_LABEL = {
    "journal": "Journal articles",
    "preprint": "Preprints",
    "chapter": "Book chapters",
    "conference": "Conference presentations",
}


def build_publications(site, pubs, rule_svg):
    selected = [p for p in pubs if p.get("selected")]
    topics = [t for t in TOPIC_LABEL if any(p.get("topic") == t for p in pubs)]

    type_pills = "".join(
        '<button class="pill" role="switch" aria-checked="false" data-filter="type" data-value="%s">%s</button>'
        % (e(t), e(TYPE_LABEL[t])) for t in TYPE_LABEL if any(p["type"] == t for p in pubs))
    topic_pills = "".join(
        '<button class="pill" role="switch" aria-checked="false" data-filter="topic" data-value="%s">%s</button>'
        % (e(t), e(TOPIC_LABEL[t])) for t in topics)

    blocks = []
    for kind in ("journal", "preprint", "chapter", "conference"):
        group = [p for p in pubs if p["type"] == kind]
        if not group:
            continue
        rows = []
        for i, p in enumerate(group):
            row = pub_html(p, number=str(len(group) - i))
            row = row.replace('<li class="pub"',
                              '<li class="pub" data-type="%s" data-topic="%s"'
                              % (e(p["type"]), e(p.get("topic") or "other")), 1)
            rows.append(row)
        blocks.append(
            '<h3 class="year-head caps" id="type-%s">%s <span class="m">(%d)</span></h3>'
            '<ul class="pub-list">%s</ul>' % (e(kind), e(TYPE_LABEL[kind]), len(group), "".join(rows)))

    ld = [{
        "@type": "ItemList",
        "name": "Publications of Yifan Sun",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": {
                "@type": "ScholarlyArticle",
                "name": p["title"],
                "author": [{"@type": "Person", "name": a.rstrip("*")} for a in p["authors"]],
                "datePublished": str(p.get("year") or ""),
                "isPartOf": p.get("venue") or "",
                **({"sameAs": "https://doi.org/" + p["doi"]} if p.get("doi") else {}),
            }} for i, p in enumerate(p2 for p2 in pubs if p2["type"] in ("journal", "chapter", "preprint"))
        ],
    }]

    main = (
        '<div class="spine">'
        '<section class="section">'
        + section_head("01", "Selected", "Five papers I would show first", level=1)
        + '<ul class="pub-list selected">%s</ul>' % "".join(
            pub_html(p, number=str(i + 1), blurb=True, anchor=False, level=2)
            for i, p in enumerate(selected))
        + '</section>'
        + rule_svg
        + '<section class="section">'
        + section_head("02", "Everything", "All publications and talks")
        + '<div class="filterbar" id="filters">'
        '<div class="filter-group"><span class="filter-legend caps">Type</span>%s</div>'
        '<div class="filter-group"><span class="filter-legend caps">Topic</span>%s</div>'
        '<button class="pill" type="button" data-filter="reset" style="margin-top:var(--s3)">Clear</button>'
        '<p class="filter-count caps" role="status" aria-live="polite" id="pub-count">Showing all %d</p>'
        '</div>' % (type_pills, topic_pills, len(pubs))
        + "".join(blocks)
        + '</section></div>'
    )
    scripts = '<script src="/assets/js/pubs.js" defer></script>'
    return render(site, "/publications/", main, scripts, extra_ld=ld)


def build_gallery(site, media, rule_svg):
    figs = media["figures"]
    cavity = [v for v in media["videos"] if v["group"] == "cavity"]
    fiber = [v for v in media["videos"] if v["group"] == "fiber"]
    travel = [v for v in media["videos"] if v["group"] == "travel"]

    main = (
        '<div class="spine"><section class="section">'
        + section_head("01", "Figures", "The pictures behind the papers", level=1)
        + '<p class="lede">Five schematics that carry most of the argument: what a '
          'multimode soliton is, what a cavity soliton is, where a soliton&rsquo;s noise '
          'comes from, and why a nanolaser mode-locks at all.</p>'
        + "".join(figure_html(f) for f in figs)
        + '</section>' + rule_svg
        + '<section class="section">'
        + section_head("02", "Simulations", "Solitons in motion")
        + '<p class="lede">Numerical experiments from the cavity work: soliton crystals '
          'forming and pursuing one another, breathers, chaoticons, and two-dimensional '
          'solitons losing stability. Nothing loads from YouTube until you press play.</p>'
        + video_grid(cavity)
        + '<h3 class="caps" style="margin-top:var(--s8)">In graded-index fibre</h3>'
        + video_grid(fiber)
        + '</section>'
        + '<section class="section">'
        + section_head("03", "Elsewhere", "Away from the desk")
        + '<p class="lede">Conferences take you places. A marathon in Rome, Mont Blanc '
          'from the air, and the long drive down Interstate 5.</p>'
        + video_grid(travel)
        + '</section></div>'
    )
    return render(site, "/gallery/", main,
                  '<script src="%s" defer></script>' % asset('/assets/js/video.js'))


def build_cv(site, cv, pubs, rule_svg):
    def timeline(rows, role_key, org_key):
        out = []
        for r in rows:
            note = ('<p class="tl-note">%s</p>' % e(r["note"])) if r.get("note") else ""
            out.append(
                '<li class="tl-item"><div class="tl-when m">%s &ndash; %s</div>'
                '<div><h3 class="tl-role">%s</h3>'
                '<p class="tl-org">%s, %s</p>%s</div></li>'
                % (e(ym(r["from"])), e(ym(r.get("to"))), e(r[role_key]),
                   e(r[org_key]), e(r["place"]), note))
        return '<ul class="timeline">%s</ul>' % "".join(out)

    grants = "".join(
        '<article class="grant"><div class="grant-head">'
        '<h3 class="grant-acronym">%s</h3><span class="grant-id m">%s</span></div>'
        '<p class="grant-scheme">%s</p>'
        '<p class="grant-meta caps">%s &ndash; %s · %s · %s</p></article>'
        % (e(g["acronym"]), e(g.get("id") or ""), e(g["scheme"]),
           e(ym(g["from"])), e(ym(g.get("to"))), e(g["host"]), e(g["role"]))
        for g in cv["funding"]["grants"])

    awards = "".join(
        '<li class="tl-item"><div class="tl-when m">%s</div>'
        '<div><h3 class="tl-role">%s</h3><p class="tl-org">%s</p></div></li>'
        % (e(a["year"]), e(a["title"]), e(a["org"])) for a in cv["awards"])

    talks = "".join(
        '<li class="tl-item"><div class="tl-when m">%s</div>'
        '<div><h3 class="tl-role">%s</h3><p class="tl-org">%s, %s</p></div></li>'
        % (e(t["year"]), e(t.get("title") or t["venue"]),
           e(t["venue"]), e(t["place"]))
        + ("" if not t.get("upcoming") else "")
        for t in cv["invitedTalks"])

    skills = "".join(
        '<div class="thrust"><h3>%s</h3><p class="tl-note">%s</p></div>'
        % (e(k), e("; ".join(v))) for k, v in cv["skills"].items())

    counts = {}
    for p in pubs:
        counts[p["type"]] = counts.get(p["type"], 0) + 1

    main = (
        '<div class="spine"><section class="section">'
        + section_head("01", "Curriculum vitae", site["name"], level=1)
        + '<p class="lede">%s</p>' % e(cv["lede"])
        + '<p class="caps" style="margin-top:var(--s5)">%s · %s</p>' % (e(site["org"]), e(site["place"]))
        + '</section>'
        + '<section class="section">' + section_head("02", "Appointments", "Positions")
        + timeline(cv["positions"], "role", "org") + '</section>'
        + '<section class="section">' + section_head("03", "Education", "Degrees")
        + timeline(cv["education"], "degree", "org") + '</section>'
        + '<section class="section">' + section_head("04", "Funding", "Grants and fellowships")
        + '<p class="lede">%s</p>' % e(cv["funding"]["lede"]) + grants + '</section>'
        + '<section class="section">' + section_head("05", "Recognition", "Awards")
        + '<ul class="timeline">%s</ul>' % awards + '</section>'
        + '<section class="section">' + section_head("06", "Talks", "Invited talks")
        + '<ul class="timeline">%s</ul>' % talks
        + '<p style="margin-top:var(--s5)"><a href="/publications/#type-conference">All %d conference presentations</a></p>'
          % counts.get("conference", 0)
        + '</section>'
        + '<section class="section">' + section_head("07", "Methods", "What I bring")
        + '<div class="thrusts">%s</div>' % skills + '</section>'
        + '</div>'
    )
    return render(site, "/cv/", main)


# ------------------------------------------------------- non-page artefacts

def build_feed(site, news):
    items = []
    for n in news["news"][:20]:
        pub = datetime.strptime(n["date"], "%Y-%m-%d")
        link = site["origin"] + "/#news"
        if n.get("link"):
            link = n["link"]["href"]
        items.append(
            "<item><title>%s</title><link>%s</link><guid isPermaLink=\"false\">%s</guid>"
            "<pubDate>%s</pubDate><description>%s</description></item>"
            % (e(n["title"]), e(link), e(n["date"] + "-" + n["title"][:40]),
               pub.strftime("%a, %d %b %Y 00:00:00 +0000"),
               e(re.sub(r"<[^>]+>", "", n["body"]))))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>'
           '<title>%s &mdash; news</title><link>%s/</link>'
           '<description>%s</description><language>en-GB</language>%s'
           '</channel></rss>') % (e(site["name"]), e(site["origin"]),
                                  e(site["meta"]["/"]["desc"]), "".join(items))
    return write("feed.xml", xml)


def build_sitemap(site):
    today = date.today().isoformat()
    urls = "".join(
        "<url><loc>%s%s</loc><lastmod>%s</lastmod></url>" % (site["origin"], p["href"], today)
        for p in site["pages"])
    return write("sitemap.xml",
                 '<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % urls)


def build_robots(site):
    return write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % site["origin"])


def build_404(site):
    main = ('<div class="spine"><section class="section">'
            '<h1>Page not found</h1>'
            '<p class="lede">That address does not exist on this site.</p>'
            '<p><a href="/">Back to the front page</a></p>'
            '</section></div>')
    with open(os.path.join(TPL, "base.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    out = (tpl.replace("{{TITLE}}", "Page not found — Yifan Sun")
              .replace("{{DESC}}", "That address does not exist on this site.")
              .replace("{{CANONICAL}}", site["origin"] + "/404.html")
              .replace("{{ORIGIN}}", site["origin"])
              .replace("{{OG_TYPE}}", "website")
              .replace("{{JSONLD}}", "")
              .replace("{{HEADER}}", header_html(site, "/404"))
              .replace("{{MAIN}}", main)
              .replace("{{FOOTER}}", footer_html(site))
              .replace("{{SCRIPTS}}", "")
              .replace("{{CSS_FONTS}}", asset("/assets/css/fonts.css"))
              .replace("{{CSS_SITE}}", asset("/assets/css/site.css"))
              .replace("{{JS_SITE}}", asset("/assets/js/site.js")))
    return write("404.html", out)


def load_rule():
    """The soliton rule: one round trip of |E|², authored offline by
    tools/make_assets.py and inlined so it inherits colour and costs no request."""
    path = os.path.join(ROOT, "assets", "img", "soliton-rule.svg")
    if not os.path.exists(path):
        return '<hr class="soliton">'
    with open(path, encoding="utf-8") as fh:
        return '<div class="soliton" role="separator">%s</div>' % fh.read().strip()


# -------------------------------------------------------------------- main

def main():
    site = load("site.json")
    pubs = load("publications.json")["publications"]
    news = load("news.json")
    research = load("research.json")
    cv = load("cv.json")
    media = load("media.json")
    rule = load_rule()

    made = [
        build_home(site, pubs, news, research, rule, media),
        build_research(site, pubs, research, rule, media),
        build_publications(site, pubs, rule),
        build_gallery(site, media, rule),
        build_cv(site, cv, pubs, rule),
        build_404(site),
        build_sitemap(site),
        build_robots(site),
        build_feed(site, news),
    ]
    for path in made:
        size = os.path.getsize(os.path.join(ROOT, path))
        print("  %-28s %7d bytes" % (path, size))
    print("\n%d files · %d publications · %d news items" % (len(made), len(pubs), len(news["news"])))


if __name__ == "__main__":
    main()

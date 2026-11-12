#!/usr/bin/env python3
"""
update_scholar.py — refresh the Google Scholar metrics shown on the CV page.

    python3 tools/update_scholar.py

Takes the "All" column of citations, h-index and i10-index for the Scholar
profile named by metrics.source_url in data/cv.json, and writes them back with
today's date in metrics.as_of.  Run daily by .github/workflows/scholar.yml;
standard library only.

Where it reads them from:
  * SERPAPI_KEY set (the GitHub workflow, via a repository secret): SerpAPI's
    Google Scholar Author API.  Scholar itself refuses GitHub's servers.
  * otherwise: the public profile page directly, which works from a home
    connection.

The file is rewritten only when a number has changed, or when the stored date
is more than a week old, so the site is not rebuilt and committed every day
just to move a date.  With SerpAPI it also lists recent papers on the profile
that are missing from data/publications.json into $SCHOLAR_NEW_FILE; the
workflow opens a GitHub issue for each.  On any failure nothing is changed and the site keeps the
last numbers it had; with SerpAPI the script also exits non-zero, so the
workflow fails and GitHub sends a notification.
"""

import difflib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CV = os.path.join(ROOT, "data", "cv.json")
PUBS = os.path.join(ROOT, "data", "publications.json")
NEW_WINDOW_YEARS = 1   # only flag Scholar entries from this year or last
STALE_DAYS = 7
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "hl=en", headers={
        "User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def author_id(url):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["user"][0]


def fetch_serpapi(url, key):
    """Returns (metrics, articles): one query gives both.  Articles come newest
    first, so the first page holds anything recently added to the profile."""
    query = urllib.parse.urlencode({
        "engine": "google_scholar_author", "author_id": author_id(url),
        "hl": "en", "sort": "pubdate", "api_key": key})
    with urllib.request.urlopen("https://serpapi.com/search.json?" + query, timeout=60) as resp:
        data = json.load(resp)
    if data.get("error"):
        raise RuntimeError("SerpAPI: " + data["error"])
    # cited_by.table is [{"citations": {"all": n, ...}}, {"h_index": {...}}, {"i10_index": {...}}]
    found = {}
    for row in data.get("cited_by", {}).get("table", []):
        for name, cols in row.items():
            if name in ("citations", "h_index", "i10_index") and isinstance(cols, dict):
                found[name] = int(cols["all"])
    return (found if len(found) == 3 else None), data.get("articles", [])


def norm_title(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def new_articles(articles):
    """Recent Scholar entries whose title matches nothing in publications.json."""
    with open(PUBS, encoding="utf-8") as fh:
        known = [norm_title(p["title"]) for p in json.load(fh)["publications"] if p.get("title")]
    first_year = date.today().year - NEW_WINDOW_YEARS
    out = []
    for art in articles:
        title = art.get("title") or ""
        year = int(art["year"]) if str(art.get("year", "")).isdigit() else None
        if not title or (year and year < first_year):
            continue
        t = norm_title(title)
        if any(difflib.SequenceMatcher(None, t, k).ratio() > 0.85 for k in known):
            continue
        out.append({
            "title": title,
            "body": "\n".join([
                "Google Scholar lists a paper that is not in `data/publications.json` yet:",
                "",
                "- **Title:** %s" % title,
                "- **Authors:** %s" % (art.get("authors") or "?"),
                "- **Venue:** %s" % (art.get("publication") or "?"),
                "- **Year:** %s" % (art.get("year") or "?"),
                "- **Scholar:** %s" % (art.get("link") or "?"),
                "",
                "Add it to `data/publications.json` (see the README), then close this issue. "
                "If it should not be on the site, just close the issue; it will not be raised again.",
            ]),
        })
    return out


def parse(page):
    """The stats table holds six cells: All / Since-YEAR for each metric."""
    cells = re.findall(r'<td class="gsc_rsb_std">(\d+)</td>', page)
    if len(cells) < 6:
        return None
    citations, h_index, i10_index = (int(cells[i]) for i in (0, 2, 4))
    return {"citations": citations, "h_index": h_index, "i10_index": i10_index}


def main():
    with open(CV, encoding="utf-8") as fh:
        text = fh.read()
    cv = json.loads(text)
    metrics = cv["metrics"]

    key = os.environ.get("SERPAPI_KEY", "").strip()
    try:
        if key:
            found, articles = fetch_serpapi(metrics["source_url"], key)
        else:
            found, articles = parse(fetch(metrics["source_url"])), []
    except Exception as exc:  # network error, HTTP 429, CAPTCHA redirect …
        print("Scholar fetch failed (%s); keeping the stored metrics." % str(exc).replace(key or "\0", "***"))
        return 1 if key else 0  # with SerpAPI a failure is actionable (key, quota): fail the job
    if not found:
        print("No metrics found in the response (CAPTCHA or changed format); keeping the stored metrics.")
        return 1 if key else 0

    # New papers are reported to the workflow, which opens one issue per title.
    out = os.environ.get("SCHOLAR_NEW_FILE")
    if out:
        new = new_articles(articles)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(new, fh, ensure_ascii=False)
        print("%d recent Scholar entr%s not on the site." % (len(new), "y" if len(new) == 1 else "ies"))

    # A sudden drop is far more likely a parsing mistake than lost citations.
    if found["citations"] < metrics["citations"] * 0.8:
        print("Refusing suspicious drop %d -> %d; keeping the stored metrics."
              % (metrics["citations"], found["citations"]))
        return 0

    changed = any(metrics[k] != v for k, v in found.items())
    age = (date.today() - date.fromisoformat(metrics["as_of"])).days
    if not changed and age < STALE_DAYS:
        print("Metrics unchanged: %(citations)d citations, h %(h_index)d, i10 %(i10_index)d." % found)
        return 0

    metrics.update(found)
    metrics["as_of"] = date.today().isoformat()
    with open(CV, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(cv, ensure_ascii=False, indent=2) + "\n")
    print("Updated: %(citations)d citations, h %(h_index)d, i10 %(i10_index)d." % found)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Negative tests for the Pages indexability gate.

A gate that only ever passes is indistinguishable from no gate at all, so each
way the Pages copy could become indexable gets a test that it is caught.
Run: python3 .github/scripts/test_assert_pages_noindex.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assert_pages_noindex as gate

NOINDEX = '<meta name="robots" content="noindex, nofollow">'
ROBOTS_OK = "User-agent: *\nAllow: /\n"


def build(tmp, pages=("index.html",), noindex=True, sitemap=False,
          robots=ROBOTS_OK):
    site = os.path.join(tmp, "site")
    os.makedirs(site, exist_ok=True)
    for p in pages:
        full = os.path.join(site, p)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        head = NOINDEX if noindex else ""
        with open(full, "w", encoding="utf-8") as fh:
            fh.write("<html><head>%s<title>x</title></head><body>hi</body></html>"
                     % head)
    if sitemap:
        with open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8") as fh:
            fh.write("<urlset></urlset>")
    if robots is not None:
        with open(os.path.join(site, "robots.txt"), "w", encoding="utf-8") as fh:
            fh.write(robots)
    return site


CASES = [
    ("clean tree passes", dict(), 0),
    ("a page without noindex is caught", dict(noindex=False), 1),
    ("one bad page among many is caught",
     dict(pages=("index.html", "plans/index.html"), noindex=False), 1),
    ("a shipped sitemap is caught", dict(sitemap=True), 1),
    ("a blanket Disallow is caught",
     dict(robots="User-agent: *\nDisallow: /\n"), 1),
    ("a Sitemap reference in robots is caught",
     dict(robots=ROBOTS_OK + "Sitemap: https://horsepowercoaching.co.uk/sitemap.xml\n"), 1),
    ("an empty tree is caught", dict(pages=()), 1),
]


def main():
    failures = 0
    for name, kwargs, expected in CASES:
        tmp = tempfile.mkdtemp()
        try:
            site = build(tmp, **kwargs)
            got = gate.main(site)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ok = got == expected
        failures += 0 if ok else 1
        print("%s  %s (expected %d, got %d)"
              % ("PASS" if ok else "FAIL", name, expected, got))
    print("\n%d/%d cases passed" % (len(CASES) - failures, len(CASES)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

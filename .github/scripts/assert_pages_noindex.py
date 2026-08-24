#!/usr/bin/env python3
"""Deploy-boundary guard for the GitHub Pages copy of horsepowercoaching.co.uk.

Pages serves the COMMITTED site/ tree, so generator/build.py's own gate can be
bypassed simply by committing a stale build. This runs against the exact bytes
about to be published and fails the deploy if that copy could be indexed.

Three things must hold on every published page and file:
  1. every .html carries <meta name="robots" content="noindex...">
  2. no sitemap.xml is shipped (a sitemap actively invites indexing)
  3. robots.txt does NOT Disallow the crawl. This looks backwards and is the
     subtlety worth spelling out: a blanket Disallow would stop Google fetching
     the pages, so it would never SEE the noindex, and already-indexed URLs
     would sit in the index indefinitely. Crawlable + noindex is what actually
     removes them.
"""
import os
import re
import sys

ROBOTS_META = re.compile(
    r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*noindex', re.I)
DISALLOW_ALL = re.compile(r'^\s*Disallow:\s*/\s*$', re.I | re.M)


def main(site_dir):
    errors = []

    pages = []
    for root, _dirs, names in os.walk(site_dir):
        for n in names:
            if n.endswith(".html"):
                pages.append(os.path.join(root, n))
    pages.sort()

    if not pages:
        errors.append("no HTML pages found in %s, refusing to deploy blind"
                      % site_dir)

    missing = []
    for path in pages:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            if not ROBOTS_META.search(fh.read()):
                missing.append(os.path.relpath(path, site_dir))
    if missing:
        errors.append("%d page(s) missing the noindex meta, first 5: %s"
                      % (len(missing), ", ".join(missing[:5])))

    if os.path.exists(os.path.join(site_dir, "sitemap.xml")):
        errors.append("sitemap.xml is present; the Pages copy must not ship one")

    robots_path = os.path.join(site_dir, "robots.txt")
    if os.path.exists(robots_path):
        with open(robots_path, encoding="utf-8") as fh:
            robots = fh.read()
        if DISALLOW_ALL.search(robots):
            errors.append(
                "robots.txt blanket-Disallows the crawl. That PREVENTS "
                "de-indexing: Google cannot fetch the page to see the noindex. "
                "Keep the Pages copy crawlable and rely on the meta tag.")
        if "Sitemap:" in robots:
            errors.append("robots.txt advertises a Sitemap; remove it")

    if errors:
        print("PAGES INDEXABILITY GATE FAILED:")
        for e in errors:
            print("  - %s" % e)
        return 1

    print("Pages indexability gate passed:")
    print("  - %d HTML pages, all carrying noindex" % len(pages))
    print("  - no sitemap.xml shipped")
    print("  - robots.txt keeps the copy crawlable, so the noindex is seen")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site"))

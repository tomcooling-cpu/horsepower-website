#!/usr/bin/env python3
"""WS-SITE20 FREEZE GATE.

The craft pass (self-hosted fonts, fluid type, scroll-reveal, motion) is allowed
to touch presentation ONLY. This gate is the hard proof that it changed nothing
an editor or a search engine would read:

  (a) the frozen <head> metadata SET per page - <title>, meta description,
      canonical, every og:*, every twitter:*, and every JSON-LD block, and
  (b) the visible body TEXT of every page (tags stripped, scripts/styles removed,
      HTML entities decoded, whitespace normalised), and
  (c) the exact set of shipped file paths (URLs) under site/.

Usage:
  python3 generator/freeze_gate.py snapshot [site_dir]   # write the baseline
  python3 generator/freeze_gate.py verify   [site_dir]   # assert unchanged

The snapshot is committed (generator/freeze_snapshot.json) so future passes reuse
it. If verify fails, the CHANGE is wrong - fix the change, never the snapshot.

Metadata frozen here is base-path independent (title/description/canonical/og/
twitter/JSON-LD all use the production origin), and body text is tag-stripped, so
one snapshot is valid for both build modes (default BASE_PATH and HP_BASE_PATH="").
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SITE = os.path.join(os.path.dirname(HERE), "site")
SNAPSHOT = os.path.join(HERE, "freeze_snapshot.json")

_WS = re.compile(r"\s+")


def _norm_text(s):
    """HTML-decode, treat NBSP as space, collapse all whitespace, strip."""
    s = html.unescape(s)
    s = s.replace(" ", " ")
    return _WS.sub(" ", s).strip()


def _strip_blocks(s, tag):
    return re.sub(r"<%s\b[^>]*>.*?</%s>" % (tag, tag), " ", s, flags=re.S | re.I)


def body_text(content):
    """Visible text of <body>: scripts + styles removed, tags stripped, decoded."""
    m = re.search(r"<body\b[^>]*>(.*)</body>", content, re.S | re.I)
    body = m.group(1) if m else content
    body = _strip_blocks(body, "script")
    body = _strip_blocks(body, "style")
    body = re.sub(r"<[^>]+>", " ", body)
    return _norm_text(body)


def head_meta(content):
    """The frozen metadata SET for one page (order-insensitive where it should be)."""
    meta = {}

    m = re.search(r"<title>(.*?)</title>", content, re.S)
    meta["title"] = _norm_text(m.group(1)) if m else None

    m = re.search(r'<meta name="description" content="(.*?)">', content, re.S)
    meta["description"] = m.group(1) if m else None

    m = re.search(r'<link rel="canonical" href="(.*?)">', content, re.S)
    meta["canonical"] = m.group(1) if m else None

    og = re.findall(r'<meta property="(og:[^"]+)" content="(.*?)">', content, re.S)
    meta["og"] = sorted((k, v) for k, v in og)

    tw = re.findall(r'<meta name="(twitter:[^"]+)" content="(.*?)">', content, re.S)
    meta["twitter"] = sorted((k, v) for k, v in tw)

    # Every JSON-LD block, normalised to canonical JSON (semantic identity).
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', content, re.S)
    norm = []
    for b in blocks:
        try:
            norm.append(json.dumps(json.loads(b), sort_keys=True, ensure_ascii=False))
        except Exception:
            norm.append("INVALID:" + b.strip())
    meta["jsonld"] = sorted(norm)
    return meta


def collect(site_dir):
    """Snapshot dict for a built site tree.

    The frozen URL set is every shipped page + SEO file (HTML, sitemap.xml,
    robots.txt, _redirects, .nojekyll). The assets/ tree is deliberately excluded:
    fonts and the reveal script are additive presentation, so new files there are
    expected and must not trip the gate. Adding or removing a PAGE still does.
    """
    files = []
    for root, _dirs, names in os.walk(site_dir):
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), site_dir)
            rel = rel.replace(os.sep, "/")
            if rel == "assets" or rel.startswith("assets/"):
                continue
            files.append(rel)
    files.sort()

    pages = {}
    for rel in files:
        if not rel.endswith(".html"):
            continue
        with open(os.path.join(site_dir, rel), encoding="utf-8") as fh:
            content = fh.read()
        pages[rel] = {"head": head_meta(content), "body": body_text(content)}
    return {"files": files, "pages": pages}


def _canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def verify(site_dir):
    if not os.path.exists(SNAPSHOT):
        print("FREEZE GATE: no snapshot at %s (run 'snapshot' first)" % SNAPSHOT)
        return 1
    with open(SNAPSHOT, encoding="utf-8") as fh:
        base = json.load(fh)
    cur = collect(site_dir)

    errors = []

    base_files = set(base["files"])
    cur_files = set(cur["files"])
    for missing in sorted(base_files - cur_files):
        errors.append("URL removed (page/path gone): %s" % missing)
    for added in sorted(cur_files - base_files):
        errors.append("URL added (new page/path): %s" % added)

    base_pages, cur_pages = base["pages"], cur["pages"]
    for path in sorted(set(base_pages) | set(cur_pages)):
        if path not in base_pages:
            errors.append("page appeared: %s" % path)
            continue
        if path not in cur_pages:
            errors.append("page disappeared: %s" % path)
            continue
        b, c = base_pages[path], cur_pages[path]
        if _canon(b["head"]) != _canon(c["head"]):
            # Pinpoint which metadata key drifted.
            for key in sorted(set(b["head"]) | set(c["head"])):
                if _canon(b["head"].get(key)) != _canon(c["head"].get(key)):
                    errors.append("HEAD metadata changed in %s [%s]:\n    was: %s\n    now: %s"
                                  % (path, key, _canon(b["head"].get(key))[:200],
                                     _canon(c["head"].get(key))[:200]))
        if b["body"] != c["body"]:
            # Show the first differing region.
            bt, ct = b["body"], c["body"]
            i = 0
            while i < min(len(bt), len(ct)) and bt[i] == ct[i]:
                i += 1
            lo = max(0, i - 40)
            errors.append("BODY text changed in %s (bytes %d/%d):\n    was: ...%s...\n    now: ...%s..."
                          % (path, len(bt), len(ct), bt[lo:i + 60], ct[lo:i + 60]))

    if errors:
        print("FREEZE GATE FAILED (%d diffs):" % len(errors))
        for e in errors[:60]:
            print("  -", e)
        if len(errors) > 60:
            print("  ... and %d more" % (len(errors) - 60))
        return 1

    n_pages = len(cur_pages)
    body_bytes = sum(len(p["body"]) for p in cur_pages.values())
    jsonld = sum(len(p["head"]["jsonld"]) for p in cur_pages.values())
    print("FREEZE GATE PASSED:")
    print("  - %d files (URLs) identical to snapshot" % len(cur["files"]))
    print("  - %d HTML pages: head metadata SET identical (title/description/"
          "canonical/og/twitter/%d JSON-LD blocks)" % (n_pages, jsonld))
    print("  - %d HTML pages: visible body text byte-identical "
          "(%d chars compared, whitespace-normalised)" % (n_pages, body_bytes))
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    site_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SITE
    if mode == "snapshot":
        snap = collect(site_dir)
        with open(SNAPSHOT, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print("Freeze snapshot written: %s" % SNAPSHOT)
        print("  - %d files, %d HTML pages" % (len(snap["files"]), len(snap["pages"])))
        return 0
    if mode == "verify":
        return verify(site_dir)
    print("usage: freeze_gate.py [snapshot|verify] [site_dir]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

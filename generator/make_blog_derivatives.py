# Copyright Tom Cooling 2026
"""Regenerate the original-blog-photography WebP derivatives (WS-SITE24).

The 13 posts migrated from the WordPress-era GoDaddy site (July 2017 to 31 Jan
2021) show their ORIGINAL photographs, recovered from the live pages' embedded
Draft.js content. `content/blog_media_sources.json` records, per shipped
derivative, the original image URL (the WordPress-hosted original where one
exists, else the GoDaddy CDN rendition) plus the encode settings used. This
script re-fetches each source and re-encodes it to `assets/img/blog/<name>.webp`,
reproducing the committed shipped set.

The intrinsic dimensions + factual alt for each derivative live in the committed
`content/blog_images.json` manifest (what build.py reads); the in-body photo
positions live as `{{fig:<name>}}` directives in the post markdown. Run this only
to reproduce or refresh the derivatives; nothing here runs at site-build time.

    python3 generator/make_blog_derivatives.py
"""
import io
import json
import os
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "content", "blog_media_sources.json")
OUT = os.path.join(HERE, "assets", "img", "blog")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def fetch(url):
    # GoDaddy CDN base images accept a size transform; ask for a large rendition
    # so the re-encode downscales from the biggest available master.
    if "wsimg.com/isteam/" in url and "/:/" not in url:
        url = url + "/:/rs=w:1600,m"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    src = json.load(open(SOURCES, encoding="utf-8"))
    total = 0
    for name, spec in sorted(src.items()):
        im = Image.open(io.BytesIO(fetch(spec["source_url"]))).convert("RGB")
        w, h = im.size
        longedge = spec["longedge"]
        scale = min(1.0, longedge / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        dst = os.path.join(OUT, name + ".webp")
        im.save(dst, "WEBP", quality=spec["webp_quality"], method=6)
        kb = os.path.getsize(dst) / 1024
        total += kb
        print(f"  {name:52s} {im.size[0]}x{im.size[1]:<5} {kb:6.0f}KB")
    print(f"  {'TOTAL':52s} {'':11s} {total:6.0f}KB  (blog budget 6144KB)")


if __name__ == "__main__":
    main()

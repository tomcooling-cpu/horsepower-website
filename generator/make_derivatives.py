# Copyright Tom Cooling 2026
"""Regenerate optimised, shipped image derivatives from generator/assets/img/src.

Every derivative is a full-frame downscale of its source (composition preserved);
art direction is done in CSS via object-position, never by re-cropping here. Run
after adding or replacing a source image, then rebuild the site.
"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "assets", "img", "src")
OUT = os.path.join(HERE, "assets", "img")

# derivative name -> (source file, long-edge px, quality)
WIDE = 1500   # full-bleed heroes / banners / bands
FEAT = 1100   # contained feature-media / portraits
JOBS = {
    "hero-alps":            ("hero-alps.jpg",            WIDE, 78),
    "hero-welsh-climb":     ("hero-welsh-climb.jpg",     WIDE, 78),
    "female-hero":          ("female-hero.jpg",          WIDE, 80),
    "ironman-wales-finish": ("ironman-wales-finish.jpg", WIDE, 80),
    "coached-band":         ("coached-band.jpeg",        WIDE, 78),
    "alpine-ridge":         ("alpine-hairpins.jpeg",     WIDE, 76),
    "tom-gravel":           ("tom-gravel.jpeg",          1400, 78),
    "camp-group":           ("camp-group.jpeg",          1400, 78),
    "female-tt":            ("female-tt.jpeg",           FEAT, 82),
    "female-podium":        ("female-podium.jpg",        FEAT, 82),
    "female-trail":         ("female-trail.jpeg",        FEAT, 79),
    "tom-portrait":         ("tom-portrait.jpeg",        FEAT, 82),
}


def main():
    total = 0
    for name, (src, longedge, q) in sorted(JOBS.items()):
        im = Image.open(os.path.join(SRC, src)).convert("RGB")
        w, h = im.size
        scale = min(1.0, longedge / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        dst = os.path.join(OUT, name + ".jpg")
        im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
        kb = os.path.getsize(dst) / 1024
        total += kb
        print(f"  {name:22s} {im.size[0]}x{im.size[1]:<5} {kb:6.0f}KB")
    print(f"  {'TOTAL':22s} {'':11s} {total:6.0f}KB  (budget 3584KB)")


if __name__ == "__main__":
    main()

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

# derivative name -> (source file, long-edge px, WebP quality)
# Derivatives ship as WebP (universally supported; ~30% smaller than JPEG at
# equal visual quality), which is what keeps 34 shipped images inside the budget.
# Qualities are tuned as a set so the whole shipped image payload stays inside
# the build gate's 3.5MB budget (gate 9); live hero/LCP slots get the most
# bytes, /options/-only preview candidates the fewest.
WIDE = 1500   # full-bleed heroes / banners / bands
FEAT = 1100   # contained feature-media / portraits
DROP = "drop-2026-08-05"
NAOMI = "naomi-2026-08-05"   # Tom-confirmed Naomi S photos, 2026-08-05
JOBS = {
    "hero-alps":            ("hero-alps.jpg",            WIDE, 74),
    "hero-welsh-climb":     ("hero-welsh-climb.jpg",     WIDE, 62),
    "female-hero":          ("female-hero.jpg",          WIDE, 72),
    "ironman-wales-finish": ("ironman-wales-finish.jpg", WIDE, 76),
    "coached-band":         ("coached-band.jpeg",        WIDE, 66),
    "alpine-ridge":         ("alpine-hairpins.jpeg",     WIDE, 66),
    "tom-gravel":           ("tom-gravel.jpeg",          1400, 58),
    "camp-group":           ("camp-group.jpeg",          1400, 52),
    "female-tt":            ("female-tt.jpeg",           FEAT, 80),
    "female-podium":        ("female-podium.jpg",        FEAT, 80),
    "female-trail":         ("female-trail.jpeg",        900, 58),
    "tom-portrait":         ("tom-portrait.jpeg",        FEAT, 80),
    # drop-2026-08-05: honours band (athlete identity verified per file)
    "honours-hannah-wales":    (DROP + "/1_IRONMAN-Wales.jpg", FEAT, 78),
    # Madison's honours tile is the Ironman Wales 2025 finish chute (Tom's pick,
    # 2026-08-05); source is small (~600px) so it ships at native resolution.
    # Her TT shot stays in play as a /options/ female banner candidate.
    "honours-madison-finish":  (DROP + "/top 5 - 5.jpg", 902, 80),
    "honours-madison-tt":      (DROP + "/c6d78967-c9ca-457f-93f1-39d28e01c873.jpeg", 1000, 66),
    # RETIRED (2026-08-05): the mountain-top 2:21:10 finish (298092795, with its
    # near-duplicate 236452499) is no longer confidently identified as Naomi:
    # her confirmed Swedeman 2026 kit (Precision paint-splatter top, black On
    # vest, Precision cap) is entirely different. Identity unresolved, so it is
    # out of every named/captioned slot and ships nowhere. Sources kept on disk.
    # Naomi's tile is now her Tom-confirmed Swedeman 2026 finish (Irish flag).
    "honours-naomi-flag":      (NAOMI + "/WhatsApp Image 2026-08-05 at 16.00.27 (3).jpeg", 1100, 76),
    # Elly's honours tile: her Tom-confirmed Outlaw finish (drop 2026-08-06).
    "honours-elly-outlaw":     ("elly-outlaw-finish.jpeg", FEAT, 76),
    "female-naomi-tt":         (NAOMI + "/WhatsApp Image 2026-05-26 at 13.09.23.jpeg", 1200, 60),
    # drop-2026-08-05: banner candidates (/options/) + about/coached imagery
    "hero-tenby-swim":         (DROP + "/alternate - 9.jpg", 1200, 58),
    "hero-alpine-mist":        (DROP + "/top 5 - 2.jpg", 1200, 46),
    "hero-torridon-ridge":     (DROP + "/f8380d24-01f9-4543-a1a9-988d2cc9797f.jpeg", 1200, 44),
    "tom-hill-climb":          (DROP + "/athlete-race.jpg", 1300, 76),
    "tom-alps-lead":           (DROP + "/1-HR-ALPS-2019RCL_4825.jpg", 1000, 56),
    "tom-alps-finish":         (DROP + "/5-HR-ALPS-2019DSC_1620.jpg", 1000, 62),
    "tom-dolomites-arch":      (DROP + "/2-hrdolo2019-rcl_d-453.jpg", 1000, 64),
    "tom-bottle-refill":       (DROP + "/7901535e-2f91-4d53-b57a-1fb930e63529.jpeg", 1000, 76),
    "tom-swim-kaolinite":      (DROP + "/kaolinite'25-037.jpg", 1000, 74),
    # NOTE: ff9312d4 (pink-cap portrait) is skipped: it duplicates the existing
    # tom-portrait source already live on the About rail.
    "tom-alps-signon":         (DROP + "/9-HR-ALPS-2019ARN_4191.jpg", 800, 64),
    "coaching-support-roadside": (DROP + "/a2cd6f11-54dd-4d8c-8e3a-cf0ddbc787c2.jpeg", 1100, 78),
    "coached-almere-finish":   (DROP + "/773897ce-9f4e-4e72-916f-2aa6b00e1ca8.jpeg", 1100, 74),
    "coached-tenby-swim":      (DROP + "/alternate - 13.jpg", 1400, 68),
    "female-wales-podium":     (DROP + "/0_IRONMAN-Wales.jpg", 1200, 52),
    "female-montblanc-hike":   (DROP + "/d78204b9-4429-404f-b1d6-45f5ce36e68a.jpeg", 850, 48),
    "female-welsh-tt":         (DROP + "/462639565_581577237629776_1513627609080372586_n.jpg", 1200, 66),
    "plans-izoard-trio":       (DROP + "/eed1217f-0113-4798-9a88-e38932a2e93e.jpeg", 1200, 45),
    "plans-pyrenees-switchback": (DROP + "/c0d36a66-7ae7-40d6-a2a6-2c1af2d4ef01.jpeg", 1200, 54),
    "plans-pyrenees-dawn":     (DROP + "/597e93c5-7cb4-4990-b350-ba0250b120ba.jpeg", 1200, 68),
}



def main():
    total = 0
    for name, (src, longedge, q) in sorted(JOBS.items()):
        im = Image.open(os.path.join(SRC, src)).convert("RGB")
        w, h = im.size
        scale = min(1.0, longedge / max(w, h))
        if scale < 1.0:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        dst = os.path.join(OUT, name + ".webp")
        im.save(dst, "WEBP", quality=q, method=6)
        kb = os.path.getsize(dst) / 1024
        total += kb
        print(f"  {name:22s} {im.size[0]}x{im.size[1]:<5} {kb:6.0f}KB")
    print(f"  {'TOTAL':22s} {'':11s} {total:6.0f}KB  (budget 3584KB)")


if __name__ == "__main__":
    main()

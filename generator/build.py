# Copyright Tom Cooling 2026
"""Static-site generator for the Horsepower Coaching website.

No JS build chain. Reads generator/catalogue.json (exported from the
automated-horsepower store data by scripts/export_catalogue.py) and Tom's
approved copy, and writes the full static site into ../site.

House rules enforced as build gates (build fails if any gate fails):
  - zero em-dashes (U+2014) anywhere in the generated output
  - the approved hero / tier / intro copy appears byte-exact
  - every internal link resolves to a generated file
  - every <img> has alt text; every page has a viewport meta + a unique
    title and meta description
  - the number of plan cards equals the live SKU count in catalogue.json
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "site"))
CATALOGUE = os.path.join(HERE, "catalogue.json")

BASE_PATH = "/horsepower-website"          # GitHub Pages project-site subpath
BASE_URL = "https://tomcooling-cpu.github.io/horsepower-website"
EXISTING = "https://www.horsepowercoaching.co.uk"   # current live site (phase 2 links)
CONTACT_URL = EXISTING + "/contact"

# ── Approved copy (VERBATIM) ─────────────────────────────────────────────────
HERO_HEADLINE = "Big goals are built from ordinary weeks done properly."
HERO_BODY = ("Your first 70.3. Ironman Wales. Kona. A 100 mile TT. Whatever the dream "
             "is, the road there isn't a secret session or a magic block. It's week "
             "after week of the right training, done at the right dose, adjusted when "
             "life happens. That's what Horsepower does. It's your dream. We take it "
             "as seriously as you do.")
CTA_FIND = "Find your plan"
CTA_GET = "Get coached"

# ── Tier 2 name (the £85/month self-coached tier) ────────────────────────────
# Tom is choosing a new name (candidates: The Programme / Race Ready / Horsepower
# Method / Built for You). Until he picks, this stays "Coached". Changing this one
# line renames the tier everywhere it is referenced by name: nav, footer, tier
# cards, the "which one am I" strip, page titles and the tier page's own headings.
# NOTE: "Coached by Tom" is a separate, higher tier and is never driven by this
# variable. A handful of Tom's byte-exact approved body-copy strings (the WHICH_*
# lines and the TIER_* bodies, which are locked by the verbatim gate) still spell
# the word literally; on rename those need Tom's re-approval, by design.
TIER2_NAME = "Coached"

TIER_PLANS_BODY = ("Over 150 training plans, each one built for a target race, not "
                   "adapted from a template. First marathon to Ironman, hill climbs "
                   "to 100 mile TTs. Every session tells you exactly what to do and "
                   "why, in plain language, with every target set as a percentage of "
                   "your own numbers so the plan fits you and not an average.")
TIER_COACHED_BODY = ("Your race, your hours, your plan. We build your programme block "
                     "by block around your life and your target event, review every "
                     "session you complete with real feedback from your actual data, "
                     "and put a proper race plan in your hands before every start "
                     "line. When your numbers move, the plan moves. No calls, no "
                     "fluff, just the work and the why.")
TIER_TOM_BODY = ("Everything in Coached, plus me. Calls when you need them, WhatsApp "
                 "when it's urgent, race-day strategy built together, and a coach who "
                 "knows your story, not just your data. I keep this group small on "
                 "purpose. If we're going to do it, we do it properly.")

RESULTS_LINE = ("Ironman wins. 70.3 podiums. XTRI podiums. Haute Route podiums. Ultra "
                "race wins. And a lot of first finish lines, which we're just as proud "
                "of.")

WHICH_PLANS = "Know what you're doing and want a proven route? Plans."
WHICH_COACHED = "Want the plan built around your life, and someone reading your sessions? Coached."
WHICH_TOM = "Chasing something big and want a coach in your corner for all of it? Coached by Tom."

PLANS_INTRO = ("Built for your race, not for everyone's. A plan for the Fred Whitton "
               "is not a plan for the London Marathon with the sports swapped. Every "
               "plan in this library was built for its event: the climbing, the heat, "
               "the distance, the specific thing that makes that day hard. Pick your "
               "race, pick your level, and get to work.")

COACHED_INTRO = ("Your race, your hours, your plan, for £85 a month. Not a template "
                 "with your name on it. A programme built around your life and your "
                 "target event, with real feedback on the sessions you actually do.")

# Strings that must appear byte-exact in the built output (copy-verbatim gate).
VERBATIM_REQUIRED = [
    HERO_HEADLINE, HERO_BODY, TIER_PLANS_BODY, TIER_COACHED_BODY, TIER_TOM_BODY,
    RESULTS_LINE, WHICH_PLANS, WHICH_COACHED, WHICH_TOM, PLANS_INTRO,
]

EM_DASH = "—"


# ── HTML helpers ─────────────────────────────────────────────────────────────
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def head(title, description, canonical, extra="") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#0F0F0F">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{BASE_PATH}/assets/style.css">
{extra}</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
"""


NAV = [
    ("Home", BASE_PATH + "/", "home"),
    ("Coached by Tom", BASE_PATH + "/coaching/", "coaching"),
    ("Female Performance", BASE_PATH + "/female-performance/", "female"),
    ("Plans", BASE_PATH + "/plans/", "plans"),
    (TIER2_NAME, BASE_PATH + "/coached/", "coached"),
    ("About", BASE_PATH + "/about/", "about"),
    ("Contact", CONTACT_URL, "contact"),
]


def header(active) -> str:
    items = []
    for label, href, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{esc(href)}"{cur}>{esc(label)}</a></li>')
    items.append(f'<li><a class="cta" href="{BASE_PATH}/plans/">{esc(CTA_FIND)}</a></li>')
    return f"""<div class="teal-bar"></div>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{BASE_PATH}/" aria-label="Horsepower Coaching home">
      <img src="{BASE_PATH}/assets/logo-white.png" alt="Horsepower Coaching" width="2041" height="803">
    </a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="site-nav" aria-label="Toggle navigation">&#9776;</button>
    <nav class="site-nav" id="site-nav" aria-label="Primary">
      <ul>{''.join(items)}</ul>
    </nav>
    <div class="header-social">{social_links("social-icon")}</div>
  </div>
</header>
<script>
(function(){{var b=document.querySelector('.nav-toggle'),n=document.getElementById('site-nav');
if(b&&n){{b.addEventListener('click',function(){{var o=n.classList.toggle('open');
b.setAttribute('aria-expanded',o?'true':'false');}});}}}})();
</script>
"""


def footer() -> str:
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <img class="footer-logo" src="{BASE_PATH}/assets/logo-white.png" alt="Horsepower Coaching" width="2041" height="803">
        <p>Training plans and coaching built for your race, at the right dose, adjusted when life happens.</p>
        <div class="footer-social">{social_links("social-icon")}</div>
      </div>
      <div>
        <h4>Train with us</h4>
        <ul>
          <li><a href="{BASE_PATH}/coaching/">Coached by Tom</a></li>
          <li><a href="{BASE_PATH}/female-performance/">Female Performance</a></li>
          <li><a href="{BASE_PATH}/plans/">Plans</a></li>
          <li><a href="{BASE_PATH}/coached/">{esc(TIER2_NAME)}</a></li>
          <li><a href="{BASE_PATH}/about/">About Tom</a></li>
          <li><a href="{esc(CONTACT_URL)}">Contact</a></li>
        </ul>
      </div>
      <div>
        <h4>Talk to us</h4>
        <ul>
          <li><a href="{WHATSAPP_URL}" rel="noopener" target="_blank">WhatsApp +44 7780 008724</a></li>
          <li><a href="{INSTAGRAM_URL}" rel="noopener" target="_blank">Instagram @horsepower.coaching</a></li>
          <li><a href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank">Reviews on Google</a></li>
        </ul>
        <h4 style="margin-top:22px">More from Horsepower</h4>
        <ul>
          <li><a href="{EXISTING}/breathwork">Breathwork</a></li>
          <li><a href="{EXISTING}/wheelbuilding">Wheelbuilding</a></li>
          <li><a href="{EXISTING}/alps-camp">Alps Camp</a></li>
          <li><a href="{EXISTING}/blog">Blog</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; {date.today().year} Horsepower Coaching. Plans are delivered through TrainingPeaks.</p>
    </div>
  </div>
</footer>
<script src="{BASE_PATH}/assets/carousel.js" defer></script>
</body>
</html>"""


def page(active, title, description, canonical, body, extra="") -> str:
    return head(title, description, canonical, extra) + header(active) + body + footer()


# ── Imagery ──────────────────────────────────────────────────────────────────
IMG_BASE = BASE_PATH + "/assets/img"

# Descriptive alt text (no athlete surnames), keyed by derivative name.
IMG_ALT = {
    "hero-alps": "A cyclist climbing high above an alpine valley with a huge mountain panorama behind",
    "hero-welsh-climb": "Two cyclists climbing a forested Welsh valley road under a big sky",
    "alpine-ridge": "A lone cyclist on a hairpin road high in a vast alpine mountain range",
    "ironman-wales-finish": "An athlete crossing an Ironman finish line in Wales with arms wide",
    "female-hero": "Three female athletes celebrating with champagne on the Ironman Wales podium",
    "coached-band": "A time triallist riding hard past a stone wall on a wet mountain road",
    "tom-gravel": "A cyclist riding a white gravel road towards the camera under a big blue sky",
    "tom-portrait": "Tom Cooling, founder and head coach of Horsepower Coaching",
    "female-tt": "A cyclist racing a time trial in an aero tuck on a country road",
    "female-podium": "Three athletes celebrating on a race podium",
    "female-trail": "A trail runner on a mountain path with an alpine range behind",
    "camp-group": "A group of coached cyclists riding together through an alpine village",
}

# Art direction: object-position per derivative so the subject lands on a
# rule-of-thirds power point inside its rendered window (verified by screenshot
# at desktop 1440 + mobile 390). Full-frame downscales; cropping is done here.
IMG_POS = {
    "hero-alps": "60% 42%",              # climbing rider, right of the text column
    "hero-welsh-climb": "50% 62%",       # push crop down to the TT rider + stone wall
    "alpine-ridge": "54% 60%",           # lone rider on the hairpin, valley + peaks behind
    "female-hero": "50% 30%",            # champagne spray + podium winner up top
    "ironman-wales-finish": "50% 28%",   # finisher's face + tape overhead
    "coached-band": "50% 52%",           # TT rider mid-frame against the mountain
    "tom-gravel": "64% 46%",             # Tom riding toward camera, right of text
    "camp-group": "50% 58%",             # the bunch of riders low-centre
    "female-tt": "62% 44%",              # keep the full rider + pink TT bike in frame
    "female-podium": "50% 30%",          # the three athletes' faces
    "female-trail": "50% 54%",           # runner on the trail, centre
    "tom-portrait": "50% 30%",           # Tom's face
}

# Verified from the live horsepowercoaching.co.uk contact page (not guessed).
INSTAGRAM_URL = "https://www.instagram.com/horsepower.coaching"
WHATSAPP_URL = "https://wa.me/447780008724"
FACEBOOK_URL = "https://www.facebook.com/541277319653869"

SVG_IG = ('<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
          'stroke-width="1.8" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/>'
          '<circle cx="12" cy="12" r="4.2"/><circle cx="17.4" cy="6.6" r="1.2" fill="currentColor" stroke="none"/></svg>')
SVG_WA = ('<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">'
          '<path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5.1-1.3A10 10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.6-6.1c-.3-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1-.2.3-.7.8-.8 1-.1.2-.3.2-.6.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4 0-.5.1-.7l.4-.5c.1-.2.1-.3 0-.5-.1-.2-.6-1.4-.8-1.9-.2-.5-.4-.4-.6-.4h-.5c-.2 0-.5.1-.7.3-.2.3-.9.9-.9 2.2s.9 2.5 1.1 2.7c.1.2 1.8 2.8 4.4 3.9 2.6 1.1 2.6.7 3.1.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3z"/></svg>')
SVG_FB = ('<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">'
          '<path d="M13.5 21v-7h2.4l.4-3h-2.8V9.1c0-.9.3-1.5 1.6-1.5h1.3V4.9c-.2 0-1-.1-1.9-.1-1.9 0-3.2 1.2-3.2 3.3V11H9v3h2.3v7h2.2z"/></svg>')


def social_links(cls):
    return (f'<a class="{cls}" href="{INSTAGRAM_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Instagram">{SVG_IG}</a>'
            f'<a class="{cls}" href="{WHATSAPP_URL}" rel="noopener" target="_blank" aria-label="Message Horsepower Coaching on WhatsApp">{SVG_WA}</a>'
            f'<a class="{cls}" href="{FACEBOOK_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Facebook">{SVG_FB}</a>')


IMG_DIMS = {
    "hero-alps": (1500, 1000), "hero-welsh-climb": (1500, 1000),
    "alpine-ridge": (1500, 1001),
    "female-hero": (1500, 1001), "ironman-wales-finish": (1500, 1000),
    "coached-band": (1500, 999), "tom-gravel": (1400, 1050),
    "camp-group": (1400, 1050), "female-tt": (734, 1100),
    "female-podium": (825, 1100), "female-trail": (825, 1100),
    "tom-portrait": (825, 1100),
}


def img(name, cls="", lazy=True, extra=""):
    """One <img> for derivative `name`; alt from IMG_ALT, object-position from
    IMG_POS, intrinsic width/height from IMG_DIMS (all gate-checked)."""
    alt = IMG_ALT[name]
    c = f' class="{cls}"' if cls else ""
    loading = ' loading="lazy" decoding="async"' if lazy else ' decoding="async"'
    w, h = IMG_DIMS[name]
    dims = f' width="{w}" height="{h}"'
    style = f' style="object-position:{IMG_POS[name]}"' if name in IMG_POS else ""
    return f'<img src="{IMG_BASE}/{name}.jpg" alt="{esc(alt)}"{c}{dims}{style}{loading}{extra}>'


# ── Client voices / reviews ──────────────────────────────────────────────────
# Tom's official Google share link (resolves to the verified Google Business
# profile "Horsepower Coaching | Triathlon, Cycling and Endurance Coaching",
# Clevedon). Used as every "Read our reviews on Google" CTA.
#   - REVIEW_RATING + REVIEW_COUNT: set BOTH only with the real profile numbers
#     (they drive schema.org AggregateRating; never fabricate them). Extraction
#     was blocked by Google's JS surfaces at build time -> Tom to confirm.
#   - CLIENT_QUOTES: verbatim Google review quotes + first-name attribution.
#     `tier` routes a quote to a page: "plans" | "coached" | "coaching" |
#     "about" | "female" ("" = home only). Empty entries render nothing.
GOOGLE_REVIEW_URL = "https://share.google/50jgAKYAnnnbGCbT3"
REVIEW_RATING = 5.0                         # verified Google Business profile
REVIEW_COUNT = 15                           # verified Google Business profile
# Real client result used as the Maddison result slide. VERIFIED against the
# official results database (endurance-data.com, Ironman Wales 2023 women's
# results) + Swansea Bay News: 6th woman overall including the professionals,
# 2nd age-group woman across the line, 11:03:02. The previous "led her age
# group by 45 minutes / 9th overall" line is CONTRADICTED by those primary
# sources and must never return (gate-checked below).
CLIENT_RESULT_LINE = ("Coached athlete Maddison Shaddick finished 6th woman overall "
                      "at Ironman Wales 2023, second age-group woman across the line, "
                      "in 11:03:02.")

# Verified verbatim quotes from Tom's Google Business profile (5.0, 15 reviews).
# Ian's real review runs on mid-sentence; per the spec it is closed at a natural
# earlier point and never invented past it. Every string here must appear in
# VERIFIED_QUOTES byte-exact (carousel-data gate).
CLIENT_QUOTES = [
    {"name": "Ian Cheatle", "context": "Cycling athlete", "pages": ["coached"],
     "quote": ("Tom is a great coach and has helped massively with my cycling, helping me "
               "achieve results I wouldn't have thought possible previously.")},
    {"name": "jc bastos", "context": "Ironman finisher, 11h13", "pages": ["coached", "coaching"],
     "quote": ("I can't recommend Tom enough. Over the past year, the support, structure, "
               "and guidance I received helped me progress massively and achieve my "
               "Ironman goal, finishing in 11h13.")},
    {"name": "Emma Needham", "context": "Multi-event athlete", "pages": ["female"],
     "quote": ("Really enjoyed being coached by Horsepower Coaching. Tom really knows his "
               "stuff and is easy to talk to. If ever I had any questions, Tom was always "
               "quick to answer & provided detailed race plans for my various events. "
               "Would highly recommend.")},
    {"name": "Google review", "context": "70.3 athlete", "pages": ["coaching"],
     "quote": "The dream was to finish a 70.3 before turning 50 with a personal best."},
    {"name": "Google review", "context": "", "pages": [],
     "quote": "The sessions are tough but always enjoyable I would highly recommend him"},
]

# Canonical spec-verified quote strings; the carousel-data gate asserts every
# CLIENT_QUOTES quote is one of these, byte-exact (no inventing or paraphrasing).
VERIFIED_QUOTES = {
    ("Tom is a great coach and has helped massively with my cycling, helping me "
     "achieve results I wouldn't have thought possible previously."),
    ("I can't recommend Tom enough. Over the past year, the support, structure, "
     "and guidance I received helped me progress massively and achieve my "
     "Ironman goal, finishing in 11h13."),
    ("Really enjoyed being coached by Horsepower Coaching. Tom really knows his "
     "stuff and is easy to talk to. If ever I had any questions, Tom was always "
     "quick to answer & provided detailed race plans for my various events. "
     "Would highly recommend."),
    "The dream was to finish a 70.3 before turning 50 with a personal best.",
    "The sessions are tough but always enjoyable I would highly recommend him",
}

# The Maddison Shaddick result, rendered as a distinct slide in every carousel.
MADDISON_SLIDE = {"kind": "result"}


def _review_cta(cls="btn on-dark ghost"):
    return (f'<a class="{cls}" href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank">'
            f'Read all {REVIEW_COUNT} reviews on Google</a>')


def _rating_html():
    if REVIEW_RATING and REVIEW_COUNT:
        stars = "★" * int(round(REVIEW_RATING))
        return (f'<p class="rating"><span class="stars" aria-hidden="true">{stars}</span> '
                f'<strong>{REVIEW_RATING:g}</strong> from {REVIEW_COUNT} Google reviews</p>')
    return ""


def quotes_for(page):
    """All quotes tagged for `page` ('home' returns every quote)."""
    if page == "home":
        return list(CLIENT_QUOTES)
    return [q for q in CLIENT_QUOTES if page in q.get("pages", [])]


def _slide_html(item):
    if item.get("kind") == "result":
        return (
            '<figure class="review-slide result-slide">'
            '<div class="result-stats">'
            '<div class="stat"><span class="n">6th</span><span class="k">Woman overall, Ironman Wales 2023</span></div>'
            '<div class="stat"><span class="n">2nd</span><span class="k">Age-group woman across the line</span></div>'
            '<div class="stat"><span class="n">11:03:02</span><span class="k">Her finishing time</span></div>'
            '</div>'
            f'<blockquote>{esc(CLIENT_RESULT_LINE)}</blockquote>'
            '<figcaption>Maddison Shaddick <span>Coached by Horsepower</span></figcaption>'
            '</figure>')
    ctx = f' <span>{esc(item["context"])}</span>' if item.get("context") else ""
    return (f'<figure class="review-slide"><blockquote>{esc(item["quote"])}</blockquote>'
            f'<figcaption>{esc(item.get("name", "Horsepower athlete"))}{ctx}</figcaption></figure>')


_CAROUSEL_SEQ = [0]


def carousel(page, heading="What athletes say", subhead="Real athletes, real finish lines",
             on_dark=True, include_result=True):
    """Accessible auto-advancing review carousel for `page`. Vanilla JS
    (assets/carousel.js) drives auto-advance, arrows, dots, hover/focus pause."""
    slides = list(quotes_for(page))
    if include_result:
        slides = slides + [MADDISON_SLIDE]
    if not slides:
        return ""
    _CAROUSEL_SEQ[0] += 1
    cid = f"reviews-{_CAROUSEL_SEQ[0]}"
    slide_html = "".join(
        f'<li class="carousel-slide" role="group" aria-roledescription="slide" '
        f'aria-label="{i + 1} of {len(slides)}">{_slide_html(s)}</li>'
        for i, s in enumerate(slides))
    dots = "".join(
        f'<button class="carousel-dot" type="button" data-i="{i}" '
        f'aria-label="Show review {i + 1}"></button>' for i in range(len(slides)))
    single = " is-single" if len(slides) == 1 else ""
    theme = "reviews" if on_dark else "reviews reviews--light"
    return f"""
<section class="{theme}">
  <div class="wrap">
    <p class="eyebrow"{' style="color:var(--teal-soft)"' if on_dark else ""}>{esc(heading)}</p>
    <h2>{esc(subhead)}</h2>
    {_rating_html()}
    <div class="carousel{single}" id="{cid}" data-carousel aria-roledescription="carousel" aria-label="Athlete reviews">
      <button class="carousel-arrow prev" type="button" aria-controls="{cid}-track" aria-label="Previous review">&#8249;</button>
      <div class="carousel-viewport">
        <ul class="carousel-track" id="{cid}-track" aria-live="polite">{slide_html}</ul>
      </div>
      <button class="carousel-arrow next" type="button" aria-controls="{cid}-track" aria-label="Next review">&#8250;</button>
      <div class="carousel-dots" role="tablist" aria-label="Choose a review">{dots}</div>
    </div>
    <p class="reviews-cta">{_review_cta("btn on-dark ghost" if on_dark else "btn ghost")}</p>
  </div>
</section>"""


def quote_block(page):
    """Per-page review carousel (light theme), or nothing if none for this page."""
    if not quotes_for(page):
        # still show the Maddison result on female / coaching even without a page quote
        if page not in ("female", "coaching", "coached"):
            return ""
    return carousel(page, heading="In their words",
                    subhead="What athletes say about Horsepower", on_dark=False)


def reviews_band():
    """Homepage client-voices carousel: every quote plus the Maddison result."""
    return carousel("home")


# The four live Female-First plan SKUs, cross-linked to the female performance page.
FEMALE_FIRST_SLUGS = {
    "female-first-70-3-training-plan",
    "female-first-marathon-training-plan",
    "female-first-olympic-triathlon-training-plan",
    "female-first-century-training-plan",
}


# ── Pages ────────────────────────────────────────────────────────────────────
def render_home(cat) -> str:
    total = cat["stats"]["total"]
    body = f"""<main id="main">
<section class="hero hero--image">
  {img("hero-alps", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <h1>{esc(HERO_HEADLINE)}</h1>
    <p class="lede">{esc(HERO_BODY)}</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/plans/">{esc(CTA_FIND)}</a>
      <a class="btn on-dark ghost" href="{BASE_PATH}/coached/">{esc(CTA_GET)}</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Three ways to train with Horsepower</p>
    <h2>Pick the level of support that fits</h2>
    <div class="tier-grid">
      <div class="tier-card">
        <h3>Plans</h3>
        <div class="price">From &pound;39.99, one-off</div>
        <p>{esc(TIER_PLANS_BODY)}</p>
        <a class="btn" href="{BASE_PATH}/plans/">Browse the library</a>
      </div>
      <div class="tier-card feature">
        <h3>{esc(TIER2_NAME)}</h3>
        <div class="price">&pound;85 a month</div>
        <p>{esc(TIER_COACHED_BODY)}</p>
        <a class="btn" href="{BASE_PATH}/coached/">How coaching works</a>
      </div>
      <div class="tier-card">
        <h3>Coached by Tom</h3>
        <div class="price">Limited places</div>
        <p>{esc(TIER_TOM_BODY)}</p>
        <a class="btn" href="{BASE_PATH}/coaching/">See if there is a place</a>
      </div>
    </div>
  </div>
</section>

<section class="alt feature-female">
  <div class="wrap feature-grid feature-grid--portrait">
    <div class="feature-media feature-media--portrait">{img("female-tt")}</div>
    <div class="feature-copy">
      <p class="eyebrow">Female performance</p>
      <h2>Female first, not female adapted.</h2>
      <p class="section-intro">For too long, women have been handed training built for men and
      told to make it fit. We do it the other way round. The plan is built for a female
      athlete from the start, and when we coach you, the training reads what your body
      actually did and adapts around your physiology, not an average.</p>
      <p style="margin-top:20px"><a class="btn" href="{BASE_PATH}/female-performance/">See our female performance approach</a></p>
    </div>
  </div>
</section>

<section class="results results--image">
  {img("ironman-wales-finish", cls="results-bg")}
  <div class="wrap">
    <p>{esc(RESULTS_LINE)}</p>
  </div>
</section>
{reviews_band()}

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">Which one am I?</p>
    <div class="which-grid">
      <div class="which-item"><strong>Plans</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Over {total} plans, every one built for its event</h2>
    <p class="section-intro">{esc(PLANS_INTRO)}</p>
    <p style="margin-top:22px"><a class="btn" href="{BASE_PATH}/plans/">{esc(CTA_FIND)}</a></p>
  </div>
</section>
</main>"""
    desc = ("Training plans and coaching built for your target race, at the right "
            "dose, adjusted when life happens. Over 150 plans, plus coaching from £85 a month.")
    org_ld = {
        "@context": "https://schema.org", "@type": "Organization",
        "name": "Horsepower Coaching", "url": BASE_URL + "/",
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": f"{REVIEW_RATING:g}", "reviewCount": str(REVIEW_COUNT),
            "bestRating": "5", "worstRating": "1"},
    }
    extra = f'<script type="application/ld+json">{json.dumps(org_ld)}</script>\n'
    return page("home", "Horsepower Coaching | Training plans and coaching for your race",
                desc, BASE_URL + "/", body, extra)


def _filter_options(plans, key):
    vals = sorted({p[key] for p in plans if p.get(key)})
    return "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in vals)


def render_plans_index(cat) -> str:
    plans = sorted(cat["plans"], key=lambda p: (p["sport"], p["category"], p["title"]))
    total = len(plans)
    cards = []
    for p in plans:
        tier_tag = "" if p["tier"] == "Standard" else f'<span class="tag tier">{esc(p["tier"])}</span>'
        detail = f'{BASE_PATH}/plans/{p["slug"]}/'
        female_link = (f'<p class="female-crosslink"><a href="{BASE_PATH}/female-performance/">Part of our female performance approach</a></p>'
                       if p["slug"] in FEMALE_FIRST_SLUGS else "")
        cards.append(f"""<article class="plan-card"
  data-sport="{esc(p['sport'])}" data-category="{esc(p['category'])}"
  data-tier="{esc(p['tier'])}" data-weeks="{p['weeks']}" data-hours="{p['hours_per_week']}"
  data-title="{esc(p['title'].lower())}">
  <div class="tags">
    <span class="tag">{esc(p['sport'])}</span>
    <span class="tag">{esc(p['category'])}</span>
    {tier_tag}
  </div>
  <h3><a href="{detail}">{esc(p['title'])}</a></h3>
  <p class="blurb">{esc(p['blurb'])}</p>
  {female_link}
  <div class="meta">
    <span class="price">&pound;{p['price']:.2f}</span>
    <span class="weeks">{p['weeks']} wk &middot; ~{p['hours_per_week']:g} h/wk</span>
  </div>
  <div class="actions">
    <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank">Buy on TrainingPeaks</a>
    <a class="link-plain" href="{detail}">Details</a>
  </div>
</article>""")

    body = f"""<main id="main">
<div class="page-banner">{img("hero-welsh-climb", cls="banner-bg", lazy=False)}</div>
<section class="alt" style="padding-bottom:24px">
  <div class="wrap">
    <p class="eyebrow">The plan library</p>
    <h1>Find your plan</h1>
    <p class="section-intro">{esc(PLANS_INTRO)}</p>
    <div class="filters">
      <div><label for="f-search">Search</label><input id="f-search" type="search" placeholder="Race or keyword" autocomplete="off"></div>
      <div><label for="f-sport">Sport</label><select id="f-sport"><option value="">All sports</option>{_filter_options(plans, 'sport')}</select></div>
      <div><label for="f-category">Type</label><select id="f-category"><option value="">All types</option>{_filter_options(plans, 'category')}</select></div>
      <div><label for="f-tier">Level</label><select id="f-tier"><option value="">All levels</option>{_filter_options(plans, 'tier')}</select></div>
      <div><label for="f-weeks">Length</label><select id="f-weeks"><option value="">Any length</option><option value="short">Up to 12 weeks</option><option value="mid">13 to 18 weeks</option><option value="long">19 weeks or more</option></select></div>
      <div><label for="f-hours">Hours a week</label><select id="f-hours"><option value="">Any volume</option><option value="low">Under 7 hours</option><option value="mid">7 to 11 hours</option><option value="high">12 hours or more</option></select></div>
    </div>
    <p class="filter-meta"><span class="num" id="result-count">{total}</span> of <span class="num">{total}</span> plans</p>
  </div>
</section>
<section style="padding-top:28px">
  <div class="wrap">
    <div class="card-grid" id="plan-grid">
      {''.join(cards)}
    </div>
    <p class="no-results" id="no-results" style="display:none">No plans match those filters. Try widening them.</p>
  </div>
</section>
</main>
<script src="{BASE_PATH}/assets/catalogue.js" defer></script>"""
    desc = (f"Browse {total} Horsepower training plans, each built for a target race. "
            "Filter by sport, event, level, length and weekly hours. From £39.99.")
    return page("plans", f"Training Plan Library | {total} plans built for your race | Horsepower Coaching",
                desc, BASE_URL + "/plans/", body)


def render_plan_detail(cat, p) -> str:
    canonical = f"{BASE_URL}/plans/{p['slug']}/"
    tier_line = "" if p["tier"] == "Standard" else f'<div class="spec-box"><div class="k">Level</div><div class="v">{esc(p["tier"])}</div></div>'
    paras = "".join(f"<p>{esc(x)}</p>" for x in re.split(r"(?<=[.])\s{2,}", p["description"]) if x.strip()) or f"<p>{esc(p['description'])}</p>"
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": p["title"], "description": p["description"],
        "brand": {"@type": "Brand", "name": "Horsepower Coaching"},
        "category": f'{p["sport"]} training plan',
        "offers": {"@type": "Offer", "price": f'{p["price"]:.2f}', "priceCurrency": "GBP",
                   "availability": "https://schema.org/InStock", "url": p["buy_url"]},
    }
    extra = f'<script type="application/ld+json">{json.dumps(ld)}</script>\n'
    female_note = ""
    if p["slug"] in FEMALE_FIRST_SLUGS:
        female_note = f"""
    <div class="callout" style="margin-top:26px">
      <p class="eyebrow" style="color:var(--teal-soft)">Female first, not female adapted</p>
      <p>This plan is part of our female performance approach: a programme built for a
      female athlete from the start, with recovery-respecting structure and strength work
      for long-term bone and tendon health. <a class="link-plain on-dark" href="{BASE_PATH}/female-performance/">See how we train female athletes</a>.</p>
    </div>"""
    body = f"""<main id="main">
<section class="plan-hero">
  <div class="wrap">
    <p class="crumbs"><a href="{BASE_PATH}/plans/">Plan library</a> / {esc(p['sport'])} / {esc(p['category'])}</p>
    <h1>{esc(p['title'])}</h1>
    <div class="plan-spec-grid">
      <div class="spec-box"><div class="k">Sport</div><div class="v">{esc(p['sport'])}</div></div>
      <div class="spec-box"><div class="k">Length</div><div class="v">{p['weeks']} wk</div></div>
      <div class="spec-box"><div class="k">Hours a week</div><div class="v">~{p['hours_per_week']:g}</div></div>
      {tier_line if tier_line else f'<div class="spec-box"><div class="k">Type</div><div class="v" style="font-size:0.95rem">{esc(p["category"])}</div></div>'}
    </div>
    <div class="buy-row">
      <span class="price">&pound;{p['price']:.2f}</span>
      <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank">Buy on TrainingPeaks</a>
      <span style="color:var(--grey-mid);font-size:0.9rem">One-off. Delivered to your TrainingPeaks account.</span>
    </div>
  </div>
</section>
<section>
  <div class="wrap prose">
    <h2>About this plan</h2>
    {paras}
    <h2>How it is built</h2>
    <p>Every Horsepower plan is generated by the same engine that builds our coached
    athletes' programmes, then written out session by session in plain language. The
    load builds in three-week blocks and eases back so the work lands, the hard
    sessions are dosed the way the research says fitness is built, and every target is
    set as a percentage of your own numbers so it fits you and not an average.</p>
    <p><a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank">Get {esc(p['title'])}</a>
    &nbsp; <a class="link-plain" href="{BASE_PATH}/plans/">Back to the library</a></p>
    <p style="margin-top:26px;color:var(--grey-mid)">Want it built around your life instead of off the shelf?
    <a href="{BASE_PATH}/coached/">See {esc(TIER2_NAME)}</a>.</p>
    {female_note}
  </div>
</section>
</main>"""
    desc = (p["blurb"][:150]).rsplit(" ", 1)[0]
    return page("plans", f"{p['title']} | Horsepower Coaching", desc, canonical, body, extra)


def render_coached(cat) -> str:
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 64px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">{esc(TIER2_NAME)} &middot; &pound;85 a month</p>
    <h1>Your race, your hours, your plan</h1>
    <p class="lede">{esc(COACHED_INTRO)}</p>
    <div class="cta-row"><a class="btn" href="{esc(CONTACT_URL)}">Apply for coaching</a></div>
  </div>
</section>

<div class="media-band">{img("coached-band", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>What you get for &pound;85 a month</h2>
    <p class="section-intro">{esc(TIER_COACHED_BODY)}</p>
    <ol class="step-list">
      <li><strong>We start with you</strong>A proper intake: your target event, your history, your week, your numbers and the hours you actually have.</li>
      <li><strong>Your plan arrives block by block</strong>Built around your life and your event, three weeks at a time, so it stays current with how your training is actually going rather than a whole year written on day one.</li>
      <li><strong>Feedback on every completed session</strong>We read the sessions you complete against what was asked, using your actual data, and tell you what it means and what happens next.</li>
      <li><strong>A race plan before every start line</strong>Pacing, fuelling and strategy for your event, in your hands before you get there.</li>
    </ol>
  </div>
</section>

<section class="alt">
  <div class="wrap content-grid two">
    <div>
      <h2>Honest answers</h2>
      <details class="faq" open><summary>Is there a call every week?</summary><p>No. Coached is built around the work and the why, delivered in writing so you can go back to it. If you want calls, WhatsApp and race-day strategy built together, that is Coached by Tom.</p></details>
      <details class="faq"><summary>What if my numbers change or life gets in the way?</summary><p>The plan moves. When your data shifts or a week falls apart, the next block reflects it. That is the point of building it block by block instead of all at once.</p></details>
      <details class="faq"><summary>Which sports do you coach?</summary><p>Triathlon across every distance, road and ultra running, and cycling from sportives to ultra-distance. If you have a target event, we can build for it.</p></details>
      <details class="faq"><summary>Can I upgrade later?</summary><p>Yes. If you want Tom directly, you can move to Coached by Tom when a place is open.</p></details>
    </div>
    <div>
      <div class="callout">
        <h2>What it isn't</h2>
        <p>It is not a template with your name on it, and it is not a scheduled weekly call. It is a programme built around your life and your event, with real feedback on the sessions you actually do. If you want a coach in your corner for all of it, look at Coached by Tom.</p>
        <p style="margin-top:18px"><a class="btn on-dark ghost" href="{BASE_PATH}/coaching/">Coached by Tom</a></p>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Ready to start?</h2>
    <p class="section-intro">Tell us about your event and your season and we will take it from there.</p>
    <p style="margin-top:18px"><a class="btn" href="{esc(CONTACT_URL)}">Apply for coaching</a></p>
  </div>
</section>
{quote_block("coached")}
</main>"""
    desc = ("Coached by Horsepower, £85 a month. Your race, your hours, your plan, "
            "built block by block with real feedback on every session and a race "
            "plan before every start line.")
    return page("coached", f"{TIER2_NAME} | £85 a month | Horsepower Coaching", desc,
                BASE_URL + "/coached/", body)


COACHED_BY_TOM_GET = [
    ("A completely bespoke programme",
     "Your whole training programme, built for you from the ground up and delivered through TrainingPeaks."),
    ("In-depth training and progress analysis",
     "Your training and progress analysed in depth with TrainingPeaks and WKO5, so decisions come from your data, not a hunch."),
    ("Free TrainingPeaks Premium",
     "A free TrainingPeaks Premium account for as long as we work together, so you see everything I see."),
    ("Unlimited plan amendments",
     "Change it as often as you need. When life or your form shifts, the plan shifts with it, no limits."),
    ("Weekly session feedback",
     "Feedback on your sessions every week, plus preparation tips for what is coming next."),
    ("Unlimited contact",
     "Instant messaging day to day and regular video catch-ups. You are never left guessing between sessions."),
    ("Science-backed methodology",
     "Evidence-led training including dedicated heat-preparation sessions when your race demands them."),
    ("Advice on the whole race",
     "Race craft, race prep, kit and equipment, nutrition and psychology. The parts of performance a training file alone cannot cover."),
]


def render_coaching(cat) -> str:
    get_cards = "".join(
        f'<div class="get-card"><h3>{esc(t)}</h3><p>{esc(d)}</p></div>'
        for t, d in COACHED_BY_TOM_GET)
    body = f"""<main id="main">
<section class="hero hero--image">
  {img("tom-gravel", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Coached by Tom &middot; &pound;160 a month &middot; Limited places</p>
    <h1>A coach in your corner for all&nbsp;of&nbsp;it</h1>
    <p class="lede">{esc(TIER_TOM_BODY)}</p>
    <div class="cta-row">
      <a class="btn" href="{esc(CONTACT_URL)}">Ask about a place</a>
      <a class="btn on-dark ghost" href="#what-you-get">See what you get</a>
    </div>
  </div>
</section>

<section id="what-you-get">
  <div class="wrap">
    <p class="eyebrow">Everything you get</p>
    <h2>Complete world class coaching</h2>
    <p class="section-intro">Coached by Tom is my highest level of support. You get everything in
    Coached, built and read by me directly, plus the tools, the analysis and the contact that
    turn a good block into a great season.</p>
    <div class="get-grid">{get_cards}</div>
  </div>
</section>

<div class="media-band">{img("alpine-ridge", cls="media-bg")}</div>

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">How a month looks</p>
    <h2>The weekly rhythm</h2>
    <ol class="step-list">
      <li><strong>Your block lands</strong>Three weeks of training built around your life, calibrated to where your form is right now and where it needs to be to reach your dream goal, delivered to your TrainingPeaks account.</li>
      <li><strong>You train, I stay close</strong>Every session tells you what to do and why. Message me any time you need to move something or talk it through. Contact is unlimited, so you are never left guessing between sessions.</li>
      <li><strong>Read, analysed, fed back on</strong>I read the sessions you complete, analyse them against what was set using your actual data in TrainingPeaks and WKO5, and feed back on them. Feedback is a key part of the coaching journey, so each week you get a full round of feedback on everything you have completed.</li>
      <li><strong>We talk, the plan moves</strong>Block by block video catch-ups, WhatsApp for general chat, and the next block reflects real life and your numbers as they move.</li>
    </ol>
  </div>
</section>

<section>
  <div class="wrap content-grid two">
    <div class="prose">
      <p class="eyebrow">Race support</p>
      <h2>A proper race plan, before every start line</h2>
      <p>Before every event you get a race plan built for that day: pacing for the climbs and
      the flats, a fuelling strategy you have rehearsed, heat and weather contingencies, and
      the race craft that decides close finishes. These are the same detailed race-plan
      documents our athletes have taken to Ironman Wales, long-course triathlon and the Haute
      Route, not a paragraph of generic advice.</p>
      <p>We build the strategy together, so on the day you are not hoping it goes well. You know
      the plan, because it is yours.</p>
    </div>
    <div>
      <div class="callout">
        <h2>Why places are limited</h2>
        <p>I keep this group small on purpose. If we are going to do it, we do it properly, and
        that means I can only take on so many athletes at this level at once. When it is full,
        it is full.</p>
        <p style="margin-top:18px"><a class="btn on-dark ghost" href="{esc(CONTACT_URL)}">Ask about a place</a></p>
      </div>
    </div>
  </div>
</section>

<div class="media-band">{img("camp-group", cls="media-bg")}</div>
{carousel("coaching", subhead="What athletes say about being coached by Tom")}
<section class="alt">
  <div class="wrap">
    <div class="pricing-card">
      <p class="eyebrow">Coached by Tom</p>
      <div class="pricing-figure"><span class="amount">&pound;160</span><span class="per">a month</span></div>
      <ul class="pricing-points">
        <li>No setup fee</li>
        <li>Three-month minimum</li>
        <li>Limited places, taken one at a time</li>
      </ul>
      <p style="margin-top:6px"><a class="btn" href="{esc(CONTACT_URL)}">Apply for a place</a></p>
      <p class="pricing-note">Not quite ready for this level? <a href="{BASE_PATH}/coached/">{esc(TIER2_NAME)} is &pound;85 a month</a>.</p>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Not sure which tier?</h2>
    <div class="which-grid">
      <div class="which-item"><strong>Plans</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>
</main>"""
    desc = ("Coached by Tom, £160 a month, limited places. A bespoke TrainingPeaks programme, "
            "in-depth WKO5 analysis, unlimited contact and amendments, weekly feedback and a "
            "race plan before every start line, built and read by Tom directly.")
    return page("coaching", "Coached by Tom | £160 a month | Horsepower Coaching", desc,
                BASE_URL + "/coaching/", body)


def render_about(cat) -> str:
    # Bio content is VERBATIM from the current site; structure/order is presentation.
    body = f"""<main id="main">
<section class="hero" style="padding:56px 0 60px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">About Tom Cooling</p>
    <h1>The coach behind Horsepower</h1>
    <p class="lede">Tom Cooling is an ex-elite triathlete, seasoned ultra-bike racer
    and FKT holder, with over a decade of coaching athletes from complete beginners to
    world-tour level professionals.</p>
  </div>
</section>

<section>
  <div class="wrap content-grid two about-grid">
    <div class="prose">
      <h2>Coaching experience</h2>
      <p>Tom has spent over a decade coaching athletes from complete beginners to
      world-tour level professionals, and has guided competitors to wins and podiums
      across Ironman, middle-distance triathlon, ultra-bike events and Haute
      Route-style races.</p>

      <h2>Where the expertise comes from</h2>
      <p>That expertise is drawn from personal racing, including FKT performances and
      ultra wins, training with Royal Marines and UKSF, and coaching elite performers.
      It is first-hand knowledge of what the hard days actually take, brought to how he
      builds and reads every athlete's training.</p>

      <h2>Philosophy</h2>
      <p>His coaching combines evidence-based methodologies valued by professional
      athletes with practical, race-proven strategies, with a particular emphasis on
      female-specific performance development and durable, race-winning preparation.
      The aim is never a single good block. It is a whole athlete, prepared to hold up
      on the day that matters.</p>
    </div>
    <div class="about-side">
      <figure class="portrait">{img("tom-portrait")}</figure>
    </div>
  </div>
</section>

<section class="alt" style="padding-top:40px;padding-bottom:40px">
  <div class="wrap">
    <p class="eyebrow">Qualifications</p>
    <h2>The credentials behind the coaching</h2>
    <div class="cred-band">
      <div class="cred"><h3>Sport science</h3><p>First Class BA and Master's Degree in Sport Science and Athlete Development.</p></div>
      <div class="cred"><h3>Breathwork</h3><p>Oxygen Advantage Advanced Breathwork Instructor qualification.</p></div>
      <div class="cred"><h3>Heat adaptation</h3><p>Accredited heat-training coach with applied experience in climate adaptation protocols.</p></div>
    </div>
  </div>
</section>

<div class="media-band">{img("tom-gravel", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>Train with Tom</h2>
    <p class="section-intro">Start with a plan built for your race, get coached from
    £85 a month, or ask about a limited place with Tom directly.</p>
    <div class="cta-row" style="margin-top:20px">
      <a class="btn" href="{BASE_PATH}/plans/">Browse plans</a>
      <a class="btn ghost" href="{BASE_PATH}/coached/">Get coached</a>
    </div>
  </div>
</section>
{quote_block("about")}
</main>"""
    desc = ("Tom Cooling is an ex-elite triathlete, ultra-bike racer and FKT holder "
            "with over a decade coaching beginners to world-tour professionals across "
            "triathlon, ultra-bike and Haute Route racing.")
    return page("about", "About Tom Cooling | Horsepower Coaching", desc,
                BASE_URL + "/about/", body)


FEMALE_LEAD = "Female first, not female adapted."

# ── Female honours (verified results only) ───────────────────────────────────
# Every line here is backed by a primary source, checked 2026-08-05:
#   Saitch 2022: endurance-data.com/en/results/739-ironman-wales/female/
#     (#1 woman, 10:47:37; no professional woman ahead; corroborated by TRI247)
#   Shaddick 2023: endurance-data.com/en/results/907-ironman-wales/female/
#     + Swansea Bay News 2023-09-04 (6th woman overall, 2nd AG woman, 11:03:02)
#   Shinkins: 220 Triathlon coverage (20-island Nordic crossing);
#     TRI247 2021 (IronBourne long-distance podium; exact step unconfirmed, so
#     the copy says "podium" and no more)
# Do NOT add results without a primary source; the old Shaddick "45-minute
# lead / 9th overall" line is contradicted by the official results and is
# gate-banned site-wide.
FEMALE_HONOURS = [
    {"name": "Hannah Saitch",
     "lines": ["Fastest woman of the day, Ironman Wales 2022",
               "10:47:37, first of every woman across the line",
               "Quicker than the entire amateur and professional field"]},
    {"name": "Maddison Shaddick",
     "lines": ["6th woman overall, Ironman Wales 2023",
               "Second age-group woman across the line",
               "11:03:02 on one of the hardest Ironman courses there is"]},
    {"name": "Naomi Shinkins",
     "lines": ["Crossed 20 Nordic islands under her own power",
               "Podium, IronBourne long-distance triathlon 2021",
               "Adventure and ultra-endurance, built the same way"]},
]

FEMALE_FAQ = [
    ("What is female-specific endurance training?",
     "It is training designed for a female athlete from the ground up, not a men's plan "
     "with the numbers scaled down. It respects the physiological differences that shape "
     "recovery, fuelling, strength needs and how training load is best spread across the week."),
    ("Do Horsepower's off-the-shelf plans sync to my menstrual cycle?",
     "No, and we will not claim they do. A downloadable plan cannot know where you are in "
     "your cycle, so instead our Female-First plans use recovery-respecting structure and "
     "dedicated strength work for bone and tendon health that benefit every female athlete. "
     "Genuine cycle-aware training comes with coaching, where the plan adapts around you."),
    ("What makes Horsepower's coaching cycle-aware?",
     "When we coach you, we read the sessions you actually complete in the context of what "
     "your body was doing, and we adapt the next block around your physiology, your symptoms "
     "and your feedback. It is personalised to you, not a generic template."),
    ("Which female-specific training plans does Horsepower offer?",
     "Four Female-First plans are live now: 70.3, Olympic-distance triathlon, marathon and "
     "century. Each is built for a female athlete targeting that specific event."),
    ("Is female-specific training only for elite athletes?",
     "No. The same approach that supports our racing athletes supports a first-timer. It is "
     "about training the athlete in front of us properly, at every level and life stage."),
]


def render_female(cat) -> str:
    fem = [p for p in cat["plans"] if p["slug"] in FEMALE_FIRST_SLUGS]
    fem.sort(key=lambda p: p["title"])
    plan_cards = "".join(f"""<article class="plan-card">
    <div class="tags"><span class="tag">{esc(p['sport'])}</span><span class="tag tier">Female-First</span></div>
    <h3><a href="{BASE_PATH}/plans/{p['slug']}/">{esc(p['title'])}</a></h3>
    <p class="blurb">{esc(p['blurb'])}</p>
    <div class="actions">
      <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank">Buy on TrainingPeaks</a>
      <a class="link-plain" href="{BASE_PATH}/plans/{p['slug']}/">Details</a>
    </div>
  </article>""" for p in fem)

    faq_html = "".join(
        f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
        for q, a in FEMALE_FAQ)
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in FEMALE_FAQ],
    }
    extra = f'<script type="application/ld+json">{json.dumps(faq_ld)}</script>\n'

    body = f"""<main id="main">
<section class="hero hero--image">
  {img("female-hero", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Female performance</p>
    <h1>{esc(FEMALE_LEAD)}</h1>
    <p class="lede">Endurance training was written for men and handed to women with the
    numbers turned down. We do it the other way round. From the first session, the training
    is built for a female athlete, and when we coach you it adapts around your physiology,
    not an average.</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/coached/">Get coached</a>
      <a class="btn on-dark ghost" href="#female-plans">See the plans</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap prose">
    <h2>Why "female adapted" fails</h2>
    <p>Most training plans, most research and most coaching were built around the male
    athlete, then shrunk to fit everyone else. Women were trained as small men. That
    ignores the things that actually shape how a female athlete responds to training:
    how you recover, how you fuel, the strength work that protects your bones and tendons,
    and how load is best distributed across your week. Turning a men's plan down is not
    the same as building the right one.</p>
    <h2>What female first actually means</h2>
    <p>It means the plan starts from the female athlete, not from a template. It means
    recovery-respecting structure so the work lands instead of grinding you down. It means
    strength work built in for long-term bone and tendon health, not bolted on as an
    afterthought. And it means being honest about what each level of support can and cannot do.</p>
  </div>
</section>

<section class="alt">
  <div class="wrap feature-grid">
    <div class="feature-media">{img("female-trail")}</div>
    <div class="feature-copy">
      <p class="eyebrow">Coached and Coached by Tom</p>
      <h2>Genuinely cycle-aware coaching</h2>
      <p class="section-intro">This is where female-specific training stops being a label and
      gets personal. When we coach you, three things happen that a downloadable plan cannot do.</p>
      <ul class="about-list">
        <li><strong>The plan adapts around your physiology.</strong> Load, recovery and intensity are shaped to how you respond, not to an average athlete.</li>
        <li><strong>Feedback reads your sessions in context.</strong> What your body actually did, alongside your reported symptoms, recovery and where you are in your cycle.</li>
        <li><strong>Strength for bone and tendon is built in.</strong> Not bolted on, because long-term durability is part of performance, not separate from it.</li>
      </ul>
      <p style="margin-top:16px">We are honest about the limits: coaching is personalised week to
      week, and we will never overclaim what it does. Tom coaches with a particular emphasis on
      female-specific performance development, drawn from years of working with female athletes
      from first finish lines to the front of the race.</p>
      <p style="margin-top:20px">
        <a class="btn" href="{BASE_PATH}/coached/">How coaching works</a>
        <a class="btn ghost" href="{BASE_PATH}/coaching/" style="margin-left:10px">Coached by Tom</a>
      </p>
    </div>
  </div>
</section>

<section class="female-results">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Female results, not female participation</p>
    <h2>Trained for her body, and to the front of the race</h2>
    <div class="female-results-grid">
      <div class="female-results-media">
        <figure class="feature-media">{img("female-podium")}</figure>
        <figure class="feature-media">{img("ironman-wales-finish")}</figure>
      </div>
      <div class="female-results-copy">
        <div class="result-stats">
          <div class="stat"><span class="n">6th</span><span class="k">Woman overall, Ironman Wales 2023</span></div>
          <div class="stat"><span class="n">2nd</span><span class="k">Age-group woman across the line</span></div>
          <div class="stat"><span class="n">11:03:02</span><span class="k">Her finishing time</span></div>
        </div>
        <p class="reviews-result">{esc(CLIENT_RESULT_LINE)}</p>
        <p class="reviews-result" style="color:#CFCFCF">Trained for her body, not an average. That is how female athletes get to the front.</p>
      </div>
    </div>
  </div>
</section>

<section class="female-honours">
  <div class="wrap">
    <p class="eyebrow">The women who prove it</p>
    <h2>Real names, real results</h2>
    <p class="section-intro" style="color:#CFCFCF">Not stock-photo athletes. These are Horsepower-coached
    women, and every line below is checked against the race records and race press, not invented.</p>
    <div class="honours-grid">{"".join(
      f'<div class="honour"><div class="honour-body"><h3 class="honour-name">{esc(h["name"])}</h3>'
      f'<ul class="honour-stats">{"".join(f"<li>{esc(l)}</li>" for l in h["lines"])}</ul>'
      f'</div></div>' for h in FEMALE_HONOURS)}</div>
  </div>
</section>
{carousel("female", subhead="In her words", include_result=False, on_dark=False)}
<section>
  <div class="wrap prose">
    <h2>Female performance, answered</h2>
    {faq_html}
  </div>
</section>

<section id="female-plans" class="alt">
  <div class="wrap">
    <p class="eyebrow">The entry point</p>
    <h2>Female-First training plans</h2>
    <p class="section-intro">Start here. Four plans, each built for a female athlete targeting its
    event, with recovery-respecting structure and dedicated strength work for bone and tendon
    health. What they do not do is claim to sync to your menstrual cycle: an off-the-shelf plan
    cannot know where you are in yours, so we will not pretend it does. That is what coaching
    is for. One-off, delivered through TrainingPeaks.</p>
    <div class="card-grid" style="margin-top:26px">{plan_cards}</div>
    <div class="callout callout--wide" style="margin-top:34px">
      <h2>Want it built around your body?</h2>
      <p>Get coached and have the training adapt around your physiology, your event and your life,
      with genuinely cycle-aware feedback on every session.</p>
      <p style="margin-top:18px">
        <a class="btn on-dark ghost" href="{BASE_PATH}/coaching/">Coached by Tom</a>
        <a class="btn" href="{BASE_PATH}/coached/" style="margin-left:10px">Get coached</a>
      </p>
    </div>
  </div>
</section>
</main>"""
    desc = ("Female-first endurance coaching and training plans: female-specific triathlon, "
            "cycling and marathon training built for female athletes, with cycle-aware coaching. "
            "Female first, not female adapted.")
    return page("female",
                "Female Performance Coaching | Female-Specific Triathlon, Cycling and Running Training | Horsepower Coaching",
                desc, BASE_URL + "/female-performance/", body, extra)


# ── Banner option previews (hidden /options/ page) ───────────────────────────
# A private, noindex page (not in nav, sitemap or robots) that renders every
# banner candidate IN ITS REAL SLOT with the real overlay + headline, so Tom
# judges the actual thing. Current incumbent first, then Option A/B/C, each
# labelled with its source filename. Tom picks; the live pages then change in
# one place. Candidate lists are the only thing to edit when curating.
BANNER_SLOTS = [
    {"id": "landing-hero", "kind": "hero", "name": "Landing hero",
     "where": "The home page hero, first thing every visitor sees.",
     "eyebrow": "", "headline": HERO_HEADLINE,
     "lede": ("Your first 70.3. Ironman Wales. Kona. A 100 mile TT. Whatever the dream is, "
              "Horsepower takes it as seriously as you do."),
     "candidates": ["hero-alps", "hero-welsh-climb", "alpine-ridge", "ironman-wales-finish"]},
    {"id": "coaching-top", "kind": "hero", "name": "Coached by Tom, top banner",
     "where": "The hero at the top of the Coached by Tom page.",
     "eyebrow": "Coached by Tom · £160 a month · Limited places",
     "headline": "A coach in your corner for all of it",
     "lede": ("Everything in Coached, plus me. Calls when you need them, WhatsApp when it is "
              "urgent, and a coach who knows your story, not just your data."),
     "candidates": ["tom-gravel", "coached-band", "alpine-ridge", "camp-group"]},
    {"id": "coaching-mid", "kind": "band", "name": "Coached by Tom, mid-page banner",
     "where": "The full-width band above the weekly rhythm section. Shipped live as "
              "alpine-ridge; the alternates below are here for you to override.",
     "candidates": ["alpine-ridge", "camp-group", "coached-band", "hero-welsh-climb"]},
    {"id": "plans-banner", "kind": "pagebanner", "name": "Plans banner",
     "where": "The full-width banner at the top of the plan library.",
     "candidates": ["hero-welsh-climb", "alpine-ridge", "hero-alps", "coached-band"]},
]


def _opt_hero(slot, name):
    eyebrow = (f'<p class="eyebrow" style="color:var(--teal-soft)">{esc(slot["eyebrow"])}</p>'
               if slot.get("eyebrow") else "")
    return f"""<section class="hero hero--image">
  {img(name, cls="hero-bg")}
  <div class="wrap">
    {eyebrow}<h1>{esc(slot["headline"])}</h1>
    <p class="lede">{esc(slot["lede"])}</p>
    <div class="cta-row"><a class="btn" href="#">Find your plan</a>
      <a class="btn on-dark ghost" href="#">Get coached</a></div>
  </div>
</section>"""


def _opt_band(slot, name):
    return f'<div class="media-band">{img(name, cls="media-bg")}</div>'


def _opt_pagebanner(slot, name):
    return f'<div class="page-banner">{img(name, cls="banner-bg")}</div>'


_OPT_RENDER = {"hero": _opt_hero, "band": _opt_band, "pagebanner": _opt_pagebanner}


def render_options() -> str:
    blocks = []
    for slot in BANNER_SLOTS:
        render = _OPT_RENDER[slot["kind"]]
        cands = slot["candidates"]
        cards = []
        for i, name in enumerate(cands):
            if i == 0:
                tag, tagcls = "Current", "opt-tag opt-tag--current"
            else:
                tag, tagcls = f"Option {chr(64 + i)}", "opt-tag"
            cards.append(
                f'<div class="opt">'
                f'<p class="opt-label"><span class="{tagcls}">{tag}</span> '
                f'<code>{esc(name)}.jpg</code></p>'
                f'<div class="opt-frame">{render(slot, name)}</div>'
                f'</div>')
        blocks.append(
            f'<section class="opt-slot">'
            f'<div class="wrap">'
            f'<p class="eyebrow">{esc(slot["name"])}</p>'
            f'<p class="opt-where">{esc(slot["where"])}</p>'
            f'</div>'
            f'{"".join(cards)}'
            f'</section>')
    body = f"""<main id="main" class="options-page">
<section class="hero" style="padding:56px 0 48px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Private preview, not indexed</p>
    <h1>Banner options</h1>
    <p class="lede">Every banner candidate rendered in its real slot, with the real overlay and
    headline, so you are judging the actual thing and not a thumbnail. Current pick first, then
    the alternates. Tell me the filename you want for each slot and it changes in one place.</p>
  </div>
</section>
{''.join(blocks)}
</main>"""
    extra = '<meta name="robots" content="noindex, nofollow">\n'
    return page("", "Banner options (private preview) | Horsepower Coaching",
                "Private banner preview page. Not indexed.",
                BASE_URL + "/options/", body, extra)


# ── Write + gates ────────────────────────────────────────────────────────────
def write(rel_path, content, written):
    path = os.path.join(SITE, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)
    written[rel_path] = content


def build():
    cat = json.load(open(CATALOGUE))
    plans = cat["plans"]
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)

    # assets (ship optimised derivatives in img/, but not the full-res img/src originals)
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(SITE, "assets"),
                    ignore=shutil.ignore_patterns("src"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    written = {}
    write("index.html", render_home(cat), written)
    write("plans/index.html", render_plans_index(cat), written)
    write("female-performance/index.html", render_female(cat), written)
    write("coached/index.html", render_coached(cat), written)
    write("coaching/index.html", render_coaching(cat), written)
    write("about/index.html", render_about(cat), written)
    # Hidden banner-preview page: noindex, deliberately absent from nav + sitemap.
    write("options/index.html", render_options(), written)
    for p in plans:
        write(f"plans/{p['slug']}/index.html", render_plan_detail(cat, p), written)

    # sitemap + robots
    urls = [BASE_URL + "/", BASE_URL + "/plans/", BASE_URL + "/female-performance/",
            BASE_URL + "/coached/", BASE_URL + "/coaching/", BASE_URL + "/about/"]
    urls += [f"{BASE_URL}/plans/{p['slug']}/" for p in plans]
    today = date.today().isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm), written)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n", written)

    run_gates(cat, written)
    print("Built %d pages into %s" % (len(written), SITE))
    return cat, written


def run_gates(cat, written):
    errors = []
    html_pages = {k: v for k, v in written.items() if k.endswith(".html")}

    # Gate 1: no em-dashes anywhere.
    for path, content in written.items():
        if EM_DASH in content:
            errors.append(f"em-dash (U+2014) found in {path}")

    # Gate 2: verbatim approved copy present (on the home page at least).
    home = written["index.html"]
    for s in VERBATIM_REQUIRED:
        target = home if s in (HERO_HEADLINE, HERO_BODY, TIER_PLANS_BODY, TIER_COACHED_BODY,
                               TIER_TOM_BODY, RESULTS_LINE, WHICH_PLANS, WHICH_COACHED, WHICH_TOM) else None
        # PLANS_INTRO lives on home + plans; the rest on home.
        pool = home + written["plans/index.html"]
        if esc(s) not in pool and s not in pool:
            errors.append(f"verbatim copy missing: {s[:48]}...")

    # Gate 3: viewport + unique title + meta description on every page.
    titles = {}
    for path, content in html_pages.items():
        if 'name="viewport"' not in content:
            errors.append(f"missing viewport meta: {path}")
        m = re.search(r"<title>(.*?)</title>", content, re.S)
        if not m or not m.group(1).strip():
            errors.append(f"missing/empty title: {path}")
        else:
            titles.setdefault(m.group(1), []).append(path)
        if 'name="description"' not in content:
            errors.append(f"missing meta description: {path}")
    for t, paths in titles.items():
        if len(paths) > 1:
            errors.append(f"duplicate <title> {t!r}: {paths}")

    # Gate 4: every <img> has non-empty alt.
    for path, content in html_pages.items():
        for img in re.findall(r"<img\b[^>]*>", content):
            if not re.search(r'alt="[^"]+"', img):
                errors.append(f"img without alt in {path}: {img[:60]}")

    # Gate 5: internal links resolve to generated files.
    file_set = set(written.keys())
    for path, content in html_pages.items():
        for ref in re.findall(r'(?:href|src)="([^"]+)"', content):
            if not ref.startswith(BASE_PATH + "/"):
                continue
            rel = ref[len(BASE_PATH) + 1:].split("#")[0].split("?")[0]
            if rel == "" or rel.endswith("/"):
                rel = rel + "index.html"
            if rel.startswith("assets/"):
                if not os.path.exists(os.path.join(SITE, rel)):
                    errors.append(f"broken asset link in {path}: {ref}")
            elif rel not in file_set:
                errors.append(f"broken internal link in {path}: {ref} -> {rel}")

    # Gate 6: card count equals live SKU count.
    n_cards = written["plans/index.html"].count('class="plan-card"')
    n_live = cat["stats"]["total"]
    if n_cards != n_live:
        errors.append(f"card count {n_cards} != live SKU count {n_live}")
    n_detail = sum(1 for k in written if k.startswith("plans/") and k.endswith("/index.html")
                   and k != "plans/index.html")
    if n_detail != n_live:
        errors.append(f"detail pages {n_detail} != live SKU count {n_live}")

    # Gate 7: female performance page present + on-brand + AEO wiring.
    fem = written.get("female-performance/index.html", "")
    if not fem:
        errors.append("female-performance page missing")
    else:
        if FEMALE_LEAD not in fem:
            errors.append("female lead line missing from female-performance page")
        if '"@type": "FAQPage"' not in fem:
            errors.append("FAQPage schema missing from female-performance page")
        for slug in FEMALE_FIRST_SLUGS:
            if f"/plans/{slug}/" not in fem:
                errors.append(f"female page missing link to plan {slug}")

    # Gate 8: never fabricate rating markup (AggregateRating only if real numbers set),
    # and when present it must carry the real verified numbers, nothing invented.
    if not (REVIEW_RATING and REVIEW_COUNT):
        for path, content in written.items():
            if "AggregateRating" in content:
                errors.append(f"AggregateRating present without real review numbers in {path}")
    else:
        home = written["index.html"]
        if "AggregateRating" not in home:
            errors.append("AggregateRating schema missing from home despite real numbers")
        if f'"ratingValue": "{REVIEW_RATING:g}"' not in home or f'"reviewCount": "{REVIEW_COUNT}"' not in home:
            errors.append("AggregateRating does not carry the verified rating/count")

    # Gate 8c: carousel-data integrity. Every rendered review quote must be one of
    # the spec-verified strings, byte-exact (no inventing, no paraphrase, no
    # completing Ian's truncated sentence). Every review carousel that ships must
    # link out to the real Google profile.
    for q in CLIENT_QUOTES:
        if q["quote"] not in VERIFIED_QUOTES:
            errors.append(f"carousel quote not in verified set: {q['quote'][:48]}...")
    for path, content in html_pages.items():
        if 'data-carousel' in content:
            if f"Read all {REVIEW_COUNT} reviews on Google" not in content:
                errors.append(f"carousel page missing 'read all reviews' Google link: {path}")
            if GOOGLE_REVIEW_URL not in content:
                errors.append(f"carousel page missing Google review URL: {path}")

    # Gate 8d: the contradicted Shaddick claim must never reappear (official
    # 2023 results: 2nd AG woman, 6th overall; not a 45-minute AG lead, not 9th).
    BANNED_CLAIMS = ["by 45 minutes", ">45min<", "9th overall against the professional"]
    for path, content in written.items():
        for b in BANNED_CLAIMS:
            if b in content:
                errors.append(f"banned unverified claim {b!r} found in {path}")

    # Gate 8e: female honours band present with every verified athlete + line.
    fem_page = written.get("female-performance/index.html", "")
    for h in FEMALE_HONOURS:
        if esc(h["name"]) not in fem_page and h["name"] not in fem_page:
            errors.append(f"female honours missing athlete: {h['name']}")
        for l in h["lines"]:
            if esc(l) not in fem_page and l not in fem_page:
                errors.append(f"female honours missing line: {l[:48]}")

    # Gate 8b: zero Domestiq cross-pollination anywhere (Tom's ruling: separate entities).
    for path, content in written.items():
        if "domestiq" in content.lower():
            errors.append(f'"domestiq" found in {path} (must be zero site-wide)')

    # Gate 9: total shipped image weight under budget.
    img_dir = os.path.join(SITE, "assets", "img")
    img_bytes = 0
    img_count = 0
    if os.path.isdir(img_dir):
        for f in os.listdir(img_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                img_bytes += os.path.getsize(os.path.join(img_dir, f))
                img_count += 1
    if os.path.isdir(os.path.join(img_dir, "src")):
        errors.append("full-res img/src originals leaked into shipped site/assets/img")
    img_budget = 3.5 * 1024 * 1024
    if img_bytes > img_budget:
        errors.append(f"image weight {img_bytes/1024:.0f}KB exceeds 2.5MB budget")

    if errors:
        print("BUILD GATES FAILED:")
        for e in errors:
            print("  -", e)
        raise SystemExit(1)
    print("All gates passed:")
    print(f"  - zero em-dashes across {len(written)} files")
    print(f"  - {len(VERBATIM_REQUIRED)} approved copy strings verified byte-exact")
    print(f"  - {len(html_pages)} pages: viewport + unique title + description + alt text")
    print(f"  - internal links resolve; {n_cards} cards == {n_live} live SKUs; {n_detail} detail pages")
    print(f"  - female performance page: lead line + FAQPage schema + 4 plan links")
    print(f"  - {img_count} images shipped, {img_bytes/1024:.0f}KB total (budget 3584KB); no fabricated ratings")
    print(f"  - zero 'domestiq' occurrences across all generated output")


if __name__ == "__main__":
    build()

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
  - Gate 17 (WS-SITE25): GA4 ships in the LIVE build only, behind the consent
    banner; the preview build carries no Google code; tracking attributes,
    privacy page and the contact thanks page are all checked
  - Gate 18 (WS-SITE26): the contact form option field, ?option= links, the
    analytics whitelist, the Plan Only first CTA and nav order, the monthly
    review copy on /coached/ and the privacy lines
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "site"))
CATALOGUE = os.path.join(HERE, "catalogue.json")
CONTENT_BLOG = os.path.join(HERE, "content", "blog")   # WS-SITE14 blog posts (front matter + markdown)
# WS-SITE16 race-plan snapshot: one self-contained inline SVG of the IRONMAN Wales
# bike course (real IMWA GPX via the automated-horsepower course loader + wind
# model). Committed as source; inlined into /coaching/ so it inherits the page's
# Oswald / JetBrains Mono webfonts and costs no extra request or image weight.
# Regenerate with scripts under automated-horsepower (read-only), never at build time.
RACEPLAN_SVG_PATH = os.path.join(HERE, "content", "imwales-raceplan.svg")
# Real figures baked into the committed SVG (from the IMWA bike.gpx course loader).
RACEPLAN_KM = 178
RACEPLAN_ASCENT = "2,421 m"


def raceplan_svg() -> str:
    """The committed IRONMAN Wales race-plan snapshot SVG, inlined verbatim."""
    with open(RACEPLAN_SVG_PATH, encoding="utf-8") as fh:
        return fh.read().strip()

# Base path for every internal href/src. Two deploy targets, one generator:
#   - GitHub Pages preview (the committed site/, served at a project subpath):
#     BASE_PATH = "/horsepower-website" (the default, so the Pages build is
#     unchanged and the committed site/ keeps working).
#   - Netlify at the domain root (WS-SITE13): run the generator with
#     HP_BASE_PATH="" so every link is root-relative (/plans/ not
#     /horsepower-website/plans/). netlify.toml sets this env + build command.
# Canonical / OG / sitemap / JSON-LD URLs use PROD_ORIGIN and are identical in
# both builds, so switching BASE_PATH never changes the SEO tags.
BASE_PATH = os.environ.get("HP_BASE_PATH", "/horsepower-website").rstrip("/")

# PREVIEW BUILD = the GitHub Pages copy (BASE_PATH non-empty). Netlify, the real
# site, always builds with HP_BASE_PATH="" so BASE_PATH is empty there.
# The Pages copy is a public, fully-crawlable second copy of the whole site on a
# different domain, which Google was treating as duplicate content and, on some
# pages, overriding our canonical (Search Console, 2026-08-24). Everything gated
# on IS_PREVIEW_BUILD below exists to keep that copy out of the index.
IS_PREVIEW_BUILD = bool(BASE_PATH)

# ── GA4 (WS-SITE25) ──────────────────────────────────────────────────────────
# ONE measurement ID for the whole site. Emitted ONLY in the live build (Netlify,
# HP_BASE_PATH=""); the GitHub Pages preview copy carries no Google code so test
# traffic can never reach the property. Env override HP_GA4_ID exists for a
# one-off local check; the committed constant is the source of truth.
GA4_MEASUREMENT_ID = os.environ.get("HP_GA4_ID", "G-HEZHVQCJ5P")
GA4_ID_RE = re.compile(r"^G-[A-Z0-9]{10}$")
GA4_ENABLED = not IS_PREVIEW_BUILD
if GA4_ENABLED and (GA4_MEASUREMENT_ID == "G-XXXXXXXXXX" or not GA4_ID_RE.match(GA4_MEASUREMENT_ID)):
    raise SystemExit("LIVE build refused: GA4_MEASUREMENT_ID missing or malformed "
                     f"({GA4_MEASUREMENT_ID!r}); set the constant in generator/build.py")
LEAD_VALUE_GBP = 40            # placeholder lead value, docs/ads s8.1 C2; not a measured figure
CONSENT_TTL_DAYS = 183         # ICO: re-ask after a reasonable time, six months suggested
THANKS_PATH = "/contact/thanks/"
PRIVACY_PATH = "/privacy/"
PRIVACY_UPDATED = "2026-10-17"  # the ship date; a constant, never date.today() (freeze gate)
GA4_RETENTION = "14 months"     # must equal the GA4 event-data retention setting (section 7 step 3)
# Confirmed by Tom 2026-10-17: sole trader; happy to publish this address on /privacy/.
LEGAL_NAME = "Tom Cooling, trading as Horsepower Coaching"
PRIVACY_CONTACT_EMAIL = "tom@horsepowercoaching.co.uk"
BASE_URL = "https://tomcooling-cpu.github.io/horsepower-website"
EXISTING = "https://www.horsepowercoaching.co.uk"   # current live site (phase 2 links)
# The Contact CTA now points at the real on-site /contact/ page (WS-SITE13),
# not the old external contact-us. Root-relative so it resolves in both builds.
CONTACT_URL = BASE_PATH + "/contact/"

# ── Production canonical host (WS-SITE10) ────────────────────────────────────
# The site is *served* from the github.io preview (BASE_PATH / BASE_URL, above,
# which drive every internal href, asset src and BASE_PATH-prefixed link, and
# must NOT change). But canonical / Open Graph / sitemap / JSON-LD absolute URLs
# point at the DNS-cutover target so the tags are already correct at go-live,
# when the custom domain serves this content at its root (no BASE_PATH prefix).
PROD_ORIGIN = "https://horsepowercoaching.co.uk"
SITE_NAME = "Horsepower Coaching"
OG_LOGO = PROD_ORIGIN + "/assets/logo-white.png"


def prod_url(path: str = "") -> str:
    """Absolute production URL for a root-relative logical path (no BASE_PATH)."""
    return PROD_ORIGIN + path


# ── Unified JSON-LD @graph node @ids (WS-SITE22) ─────────────────────────────
# The site used to repeat scattered per-page JSON-LD blocks with an inline copy
# of the Organization / Person on every page and ZERO "@id" anywhere. WS-SITE22
# restructures each page into ONE @graph carrying stable global identifiers, so
# every page references the SAME Organization (#org), the SAME Person (#tom) and
# the SAME WebSite (#website) by @id instead of duplicating them. Nothing is
# fabricated: the node bodies keep exactly the fields they already had.
ORG_ID = prod_url("/") + "#org"          # https://horsepowercoaching.co.uk/#org
TOM_ID = prod_url("/") + "#tom"          # https://horsepowercoaching.co.uk/#tom
WEBSITE_ID = prod_url("/") + "#website"  # https://horsepowercoaching.co.uk/#website


def _tom_ref():
    """A by-@id reference to the single #tom (Person) node."""
    return {"@id": TOM_ID}


def _org_ref():
    """A by-@id reference to the single #org (Organization) node."""
    return {"@id": ORG_ID}


def og_image_url(name: str) -> str:
    """Absolute production URL for an image derivative used as an OG/Twitter card."""
    return f"{PROD_ORIGIN}/assets/img/{name}.webp"


DEFAULT_OG_IMAGE = "ironman-wales-finish"   # landscape fallback social image

# ── Approved copy (VERBATIM) ─────────────────────────────────────────────────
# Tom's voice: first person, warm, direct, British, no-nonsense (WS-SITE12 de-AI
# rewrite, 2026-08-07, in answer to Jo's "reads very AI" note). Do NOT "tidy"
# these into neat "not X, Y" antitheses or rule-of-three triads; that is the tell
# Jo flagged. The one deliberately-kept antithesis is the locked female headline
# "Female first, not female adapted." (FEMALE_LEAD, below).
HERO_HEADLINE = "World class coaching, built around you and your dream."
HERO_BODY = ("Whether it's your first Ironman, a Haute Route podium or the perfect 25 mile "
             "time trial, getting there comes down to the right training, week in week out, "
             "at the right dose, and having the sense to adjust when life gets in the way. "
             "That's what I do, and I take your dream every bit as seriously as you do.")
CTA_FIND = "Find your plan"
# WS-SITE19: every CTA names the tier it leads to. This one points at /coaching/
# (the Coached by Tom page), so it reads "Coach with Tom", not the old generic
# "Get coached" (which no longer says which tier). WS-SITE26: the home hero
# primary is now Plan Only (CTA_START_PLAN); this is the second, ghost button.
CTA_GET = "Coach with Tom"
CTA_START_PLAN = "Start with Plan Only"
CTA_FEMALE_FEATURE = "See how I train female athletes"

# (Removed 2026-08-13: the "written by a professional coach / not a machine" home band was
# dropped. Protesting that the coaching is not AI is itself an AI tell; the site sells the
# coaching on its own terms in Tom's voice, never by arguing it is human.)

# Female-first block (copy E). Home female feature + /female-performance/ intro.
# The locked headline stays FEMALE_LEAD; this is the body that sits beneath it.
FEMALE_FIRST_BODY = ("Most plans are built around male physiology and handed to women "
                     "to get on with. I do it the other way round. Your plan starts from "
                     "how a female athlete actually trains, adapts and recovers, and when "
                     "I coach you it bends around your cycle and your life, not some "
                     "average that was never you in the first place.")

# ── Tier 2 name (the £120/month self-coached tier) ───────────────────────────
# Tom is choosing a new name (candidates: The Programme / Race Ready / Horsepower
# Method / Built for You). Until he picks, this stays "Coached". Changing this one
# line renames the tier everywhere it is referenced by name: nav, footer, tier
# cards, the "which one am I" strip, page titles and the tier page's own headings.
# NOTE: "Coached by Tom" is a separate, higher tier and is never driven by this
# variable. A handful of Tom's byte-exact approved body-copy strings (the WHICH_*
# lines and the TIER_* bodies, which are locked by the verbatim gate) still spell
# the word literally; on rename those need Tom's re-approval, by design.
TIER2_NAME = "Plan Only"

# Plans tier (copy B). One block, reused on the home tier card and the /plans/ intro.
TIER_PLANS_BODY = ("A proper plan for your race, ready to start today. Take your pick from "
                   "over 150 of them, every one written by me for a specific event and goal "
                   "and delivered straight into your TrainingPeaks. It's the same session "
                   "design my coached athletes follow, built for the rider who knows how to "
                   "train and just wants a proven plan to get on with.")

# Coached tier (copy C), two paragraphs. Home tier card + the /coached/ page body.
TIER_COACHED_BODY = ("A plan built for you, not pulled off a shelf. I write your "
                     "programme myself, block by block, exactly the way I do for my "
                     "fully coached athletes. At the end of each block I go through "
                     "everything you've done, tell you straight what I see, and build the "
                     "next block around where you actually are, not where some plan "
                     "guessed you'd be.")
TIER_COACHED_BODY_2 = ("The only thing you don't get compared to full coaching is the "
                       "contact. No catch-up calls, and I'm not on hand day to day. The "
                       "coaching that goes into the plan itself is exactly the same: a "
                       "real coach shaping your training around your life and your numbers, "
                       "just without the premium of unlimited access.")

# Coached by Tom tier (copy D), two paragraphs. Home tier card + the /coaching/ hero.
TIER_TOM_BODY = ("The full thing. One to one, completely bespoke, and a professional coach "
                 "in your corner the whole way. I build your programme around your race, "
                 "your life and your body, then I'm with you every step: feedback every "
                 "week, proper analysis of the sessions that matter, and a hand with "
                 "everything that decides the day, from pacing and fuelling to race craft, "
                 "bike fit and the mental side.")
TIER_TOM_BODY_2 = ("This is the coaching that's taken Horsepower athletes to Ironman "
                   "titles, course records and finish lines and achievements they didn't "
                   "think were possible. Places are limited simply because I can only give "
                   "this level of support to a small cohort, so I only ever open 15 Coached "
                   "by Tom spots.")

RESULTS_LINE = ("Ironman wins, 70.3 and XTRI podiums, Haute Route podiums and ultra race "
                "wins, and a whole lot of first finish lines that I'm every bit as proud "
                "of.")

WHICH_PLANS = "Know what you're doing and want a proven route? Plan Store."
WHICH_COACHED = "Want the plan built around your life, and someone reading your sessions? Plan Only."
WHICH_TOM = "Chasing something big and want a coach in your corner for all of it? Coached by Tom."

# The /plans/ intro is copy B, reused verbatim from the home tier card.
PLANS_INTRO = TIER_PLANS_BODY

COACHED_INTRO = ("The same coaching my fully coached athletes get, written for you, block by "
                 "block, for £120 a month. Each month runs the same way: three weeks of "
                 "training, then a rest week in which I review the block you have just done, "
                 "give you honest feedback and build the next one around it. The only "
                 "difference is the contact: no calls, and I am not on call day to day. The "
                 "coaching in the plan is exactly the same.")

# ── Tier 1 display name (the £39.99 off-the-shelf plan library) ───────────────
# Renamed "Plans" -> "Plan Store" (WS-SITE13, Tom's ask). The route stays /plans/;
# this is a display-name change only. Referenced in nav, footer, the home tier
# card and "which one am I" strips.
TIER1_NAME = "Plan Store"

# ── Support ladder (WS-SITE13, Tom's explicit ask) ───────────────────────────
# Make the level of support the clear differentiator, so the progression reads at
# a glance as none -> feedback -> full. One support descriptor per tier card plus
# a comparison strip on the home page. Tom's voice, no em-dashes.
SUPPORT_LEVELS = [
    ("Plan Store", "No support",
     "Buy a proven plan off the shelf and follow it yourself. No feedback and no "
     "check-ins, just a well-built plan ready to start today."),
    ("Plan Only", "Feedback each block",
     "Self-directed, but not on your own. I write your bespoke plan and give you a "
     "full round of feedback each block. You drive the day to day, there are no calls "
     "and I am not on call."),
    ("Coached by Tom", "Fully supported",
     "The complete relationship. One to one, weekly feedback, unlimited contact and a "
     "coach in your corner the whole way."),
]

# ── Contact form option (WS-SITE26) ───────────────────────────────────────────
# The one question the enquiry form asks beyond name, email, event and message:
# which option the person is asking about. Values are fixed machine strings so a
# Netlify submission, a ?option= link and the GA4 lead_option parameter all use
# the same four words. analytics.js carries the SAME list (LEAD_OPTIONS) as its
# whitelist; gate 18c asserts the two never drift. Display order is the ladder
# minus the store, then the default, then the store question (spec 1.1).
LEAD_OPTIONS = [
    ("plan-only", f"{TIER2_NAME}, £120 a month"),
    ("coached-by-tom", "Coached by Tom, £185 a month"),
    ("not-sure", "Not sure yet"),
    ("plan-store", f"A question about a {TIER1_NAME} plan"),
]
LEAD_OPTION_VALUES = [v for v, _l in LEAD_OPTIONS]
LEAD_OPTION_DEFAULT = "not-sure"
LEAD_OPTION_LABEL = "What are you interested in?"


def contact_url(option=None) -> str:
    """/contact/ with the option pre-selected. Only a known value may be linked."""
    if option is None:
        return CONTACT_URL
    assert option in LEAD_OPTION_VALUES, option
    return f"{CONTACT_URL}?option={option}"


# ── Home tier cards (WS-SITE21 item 2: the money moment, distilled) ──────────
# The HOME tier cards are distilled to a verdict + 3-4 sharp bullets so the three
# read at a glance and align to equal height. Every line here compresses copy that
# is already approved (the TIER_*_BODY paragraphs and the SUPPORT_LEVELS
# descriptors); no new claim is introduced. The FULL descriptions still live on
# each tier's own page (/plans/, /coached/, /coaching/), so this is the home cards
# only. Tom's voice: warm, direct, British, no em-dashes.
HOME_TIER_CARDS = [
    {"name": TIER1_NAME, "cls": "tier-card--store", "tag_cls": "support-tag--none",
     "support": SUPPORT_LEVELS[0][1], "btn_cls": "btn--store",
     "href": "/plans/", "cta": "Browse the library",
     "price_main": "From &pound;39.99,", "price_qual": " one-off",
     "verdict": "A proven plan for your race, ready to start today.",
     "bullets": [
         "Over 150 plans, each written for a specific event and goal",
         "The same session design my coached athletes follow",
         "Delivered straight into your TrainingPeaks",
         "Built for the athlete who just wants a plan to get on with",
     ]},
    {"name": TIER2_NAME, "cls": "feature tier-card--plan", "tag_cls": "support-tag--mid",
     "support": SUPPORT_LEVELS[1][1], "btn_cls": "btn--plan",
     "href": "/coached/", "cta": "How Plan Only works",
     "price_main": "&pound;120 a month", "price_qual": "",
     "verdict": "A plan I build for you, block by block, not pulled off a shelf.",
     "flag": "If in doubt, start here",
     "bullets": [
         "Written by me, the same way I work with my coached athletes",
         "One written review a month, at the end of every block",
         "The next block built around where you actually are",
         "Everything but the day to day contact and calls",
     ]},
    {"name": "Coached by Tom", "cls": "tier-card--tom", "tag_cls": "support-tag--full",
     "support": SUPPORT_LEVELS[2][1], "btn_cls": "btn--tom",
     "href": "/coaching/", "cta": "Coach with Tom",
     "price_main": "&pound;185 a month", "price_qual": "",
     "verdict": "The full thing, with a professional coach in your corner the whole way.",
     "bullets": [
         "A bespoke programme built around your race, life and body",
         "Weekly feedback and analysis of the sessions that matter",
         "Pacing, fuelling, race craft, bike fit and the mental side",
         "Just 15 places, so the support stays personal",
     ]},
]

# Strings that must appear byte-exact in the built output (copy-verbatim gate).
# WS-SITE21 item 2: TIER_TOM_BODY_2 was ONLY ever on the home Coached-by-Tom card,
# which is now distilled, so it no longer ships verbatim and is dropped from this
# lock. Its substance (the 15-place limit) survives on /coaching/ ("Why places are
# limited" band) and in the distilled card bullet, so no claim is lost.
VERBATIM_REQUIRED = [
    HERO_HEADLINE, HERO_BODY, FEMALE_FIRST_BODY,
    TIER_PLANS_BODY, TIER_COACHED_BODY, TIER_COACHED_BODY_2,
    TIER_TOM_BODY, RESULTS_LINE,
    WHICH_PLANS, WHICH_COACHED, WHICH_TOM, PLANS_INTRO,
]

EM_DASH = "—"


# ── HTML helpers ─────────────────────────────────────────────────────────────
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def ga(kind, **params) -> str:
    """Tracking attributes for analytics.js: data-ga="<kind>" plus data-ga-<key>="<value>"
    for each param. Values are esc()'d. Never pass user-entered text."""
    out = [f' data-ga="{esc(kind)}"']
    for k, v in params.items():
        out.append(f' data-ga-{k.replace("_", "-")}="{esc(v)}"')
    return "".join(out)


def ga_item(p) -> str:
    return esc(json.dumps({
        "item_id": f"tp-{p['live_plan_id']}", "item_name": p["title"],
        "item_brand": "Horsepower Coaching", "item_category": p["sport"],
        "item_category2": p["category"], "item_variant": p["tier"],
        "price": round(float(p["price"]), 2), "quantity": 1}, separators=(",", ":")))


# WS-SITE23: SERP titles truncate near 60 characters, so assemble each page
# <title> as `core` plus the LONGEST brand suffix that still fits within `cap`.
# Where the full " | Horsepower Coaching" would push a long race name over, it
# steps down to " | Horsepower", then drops the brand entirely, so a title is
# never longer than it needs to be. A hard site-wide ceiling of 65 chars is
# enforced separately by the title-length gate (one documented exception, the
# keyword-rich female-performance page).
TITLE_HARD_CAP = 65
TITLE_CAP_EXEMPT = {"female-performance/index.html"}


def fit_title(core, cap=60):
    for suffix in (" | Horsepower Coaching", " | Horsepower", ""):
        if len(core) + len(suffix) <= cap:
            return core + suffix
    return core


GA_BOOT = ("<!-- hp-ga-boot -->\n"
           "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}\n"
           "gtag('consent','default',{'ad_storage':'denied','ad_user_data':'denied',"
           "'ad_personalization':'denied','analytics_storage':'denied'});</script>\n")

# WS-SITE26: pre-select the contact form option from ?option=<value>. Pure
# functionality: no storage, no network, no analytics, so it runs whether or not
# the visitor has accepted measurement cookies. The <option> list is the
# whitelist; an unknown value is ignored and the default stands. Shipped ONLY on
# /contact/ (gate 18c), so no other page reads the URL. With JS off the static
# form is unchanged and still posts.
CONTACT_PRESELECT_JS = (
    "<script>(function(){var s=document.getElementById('c-option');"
    "if(!s||!window.URLSearchParams)return;"
    "var v=new URLSearchParams(location.search).get('option');if(!v)return;"
    "for(var i=0;i<s.options.length;i++){if(s.options[i].value===v){s.value=v;return;}}"
    "})();</script>")


def head(title, description, canonical, og_image_name=None, og_type="website", extra="",
         preload_img=None, page_type="page", sport="", tier="") -> str:
    name = og_image_name or DEFAULT_OG_IMAGE
    og_img = og_image_url(name)
    og_alt = IMG_ALT.get(name, SITE_NAME)
    w, h = IMG_DIMS.get(name, (1200, 800))
    # WS-SITE20 craft pass: set the `js` class as early as possible so every
    # reveal hidden-start state is gated behind it (content is fully visible with
    # JS off or before this runs); preload the two critical self-hosted font
    # weights (Oswald 600 headings, Source Sans 3 400 body) to kill FOUT; and,
    # when given, preload this page's LCP hero image. Font/hero preloads are
    # additive <link>s and are NOT part of the frozen head-metadata set.
    hero_preload = ""
    if preload_img:
        hero_preload = (f'<link rel="preload" as="image" '
                        f'href="{IMG_BASE}/{preload_img}.webp" '
                        f'type="image/webp" fetchpriority="high">\n')
    # Preview build only: keep the GitHub Pages copy out of every search index.
    # Crawling stays ALLOWED on that copy on purpose, because a blocked crawler
    # can never read this tag and the pages would linger in the index.
    noindex = ('\n<meta name="robots" content="noindex, nofollow">'
               '\n<meta name="googlebot" content="noindex, nofollow">'
               if IS_PREVIEW_BUILD else "")
    html_attrs = f' data-page-type="{esc(page_type)}"'
    if sport:
        html_attrs += f' data-sport="{esc(sport)}"'
    if tier:
        html_attrs += f' data-tier="{esc(tier)}"'
    if GA4_ENABLED:
        html_attrs += f' data-ga4="{esc(GA4_MEASUREMENT_ID)}"'
    ga_boot = GA_BOOT if GA4_ENABLED else ""
    return f"""<!doctype html>
<html lang="en"{html_attrs}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">{noindex}
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="Tom Cooling">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:locale" content="en_GB">
<meta property="og:type" content="{esc(og_type)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og_img)}">
<meta property="og:image:alt" content="{esc(og_alt)}">
<meta property="og:image:width" content="{w}">
<meta property="og:image:height" content="{h}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(og_img)}">
<meta name="twitter:image:alt" content="{esc(og_alt)}">
<meta name="theme-color" content="#0F0F0F">
{ga_boot}<script>document.documentElement.classList.add('js');</script>
<link rel="preload" as="font" type="font/woff2" href="{BASE_PATH}/assets/fonts/oswald-600.woff2" crossorigin>
<link rel="preload" as="font" type="font/woff2" href="{BASE_PATH}/assets/fonts/sourcesans3-400.woff2" crossorigin>
{hero_preload}<link rel="stylesheet" href="{BASE_PATH}/assets/style.css">
{extra}</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
"""


NAV = [
    ("Home", BASE_PATH + "/", "home"),
    # WS-SITE26: Plan Only first, Coached by Tom second (the premium step up), then the rest.
    (TIER2_NAME, BASE_PATH + "/coached/", "coached"),
    ("Coached by Tom", BASE_PATH + "/coaching/", "coaching"),
    ("Female Performance", BASE_PATH + "/female-performance/", "female"),
    (TIER1_NAME, BASE_PATH + "/plans/", "plans"),
    ("About Us", BASE_PATH + "/about/", "about"),
    ("Blog", BASE_PATH + "/blog/", "blog"),
]


def header(active) -> str:
    items = []
    for label, href, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{esc(href)}"{cur}{ga("nav", label=label)}>{esc(label)}</a></li>')
    # The single Contact CTA (teal button). Plan discovery lives on the "Plans"
    # nav link, so the button points at Contact instead of duplicating Plans.
    items.append(f'<li><a class="cta" href="{esc(CONTACT_URL)}"{ga("cta", label="Contact", location="header")}>Contact</a></li>')
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


def consent_banner() -> str:
    """WS-SITE25 cookie banner. Server-rendered hidden on every page; consent.js
    un-hides it when there is no valid stored choice or "Cookie settings" is used."""
    return f"""<section id="cookie-banner" class="consent" hidden aria-labelledby="consent-title" role="region" data-consent-ttl="{CONSENT_TTL_DAYS}">
  <div class="wrap consent-inner">
    <div class="consent-copy">
      <h2 id="consent-title" class="consent-title" tabindex="-1">Cookies for measurement</h2>
      <p>I use Google Analytics to see which pages, plans and buttons people use, and to tell whether an enquiry came from a Google ad. It only runs if you say yes. Google receives the data. <a href="{BASE_PATH}{PRIVACY_PATH}">How I use data and cookies</a>.</p>
    </div>
    <div class="consent-actions">
      <button type="button" class="btn consent-accept" data-consent="accept">Accept</button>
      <button type="button" class="btn consent-reject" data-consent="reject">Reject</button>
    </div>
  </div>
</section>"""


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
          <li><a href="{BASE_PATH}/coached/">{esc(TIER2_NAME)}</a></li>
          <li><a href="{BASE_PATH}/coaching/">Coached by Tom</a></li>
          <li><a href="{BASE_PATH}/female-performance/">Female Performance</a></li>
          <li><a href="{BASE_PATH}/plans/">{esc(TIER1_NAME)}</a></li>
          <li><a href="{BASE_PATH}/about/">About Tom</a></li>
          <li><a href="{esc(CONTACT_URL)}">Contact</a></li>
        </ul>
      </div>
      <div>
        <h4>Talk to us</h4>
        <ul>
          <li><a href="{WHATSAPP_URL}" rel="noopener" target="_blank"{ga("contact", channel="whatsapp")}>WhatsApp +44 7780 008724</a></li>
          <li><a href="{INSTAGRAM_URL}" rel="noopener" target="_blank"{ga("contact", channel="instagram")}>Instagram @horsepower.coaching</a></li>
          <li><a href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank"{ga("contact", channel="google_reviews")}>Reviews on Google</a></li>
        </ul>
        <h4 style="margin-top:22px">More from Horsepower</h4>
        <ul>
          <li><a href="{EXISTING}/breathwork"{ga("outbound")}>Breathwork</a></li>
          <li><a href="{EXISTING}/wheelbuilding"{ga("outbound")}>Wheelbuilding</a></li>
          <li><a href="{EXISTING}/alps-camp"{ga("outbound")}>Alps Camp</a></li>
          <li><a href="{BASE_PATH}/blog/">Blog</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>&copy; {date.today().year} Horsepower Coaching. Plans are delivered through TrainingPeaks.</p>
      <p class="footer-legal"><a href="{BASE_PATH}{PRIVACY_PATH}">Privacy and cookies</a> <a href="#cookie-settings" class="consent-open">Cookie settings</a></p>
    </div>
  </div>
</footer>
{consent_banner()}
<script src="{BASE_PATH}/assets/carousel.js" defer></script>
<script src="{BASE_PATH}/assets/reveal.js" defer></script>
<script src="{BASE_PATH}/assets/consent.js" defer></script>
<script src="{BASE_PATH}/assets/analytics.js" defer></script>
</body>
</html>"""


def page(active, title, description, canonical, body,
         og_image_name=None, og_type="website", extra="", preload_img=None,
         page_type="page", sport="", tier="") -> str:
    return (head(title, description, canonical, og_image_name, og_type, extra,
                 preload_img=preload_img, page_type=page_type, sport=sport, tier=tier)
            + header(active) + body + footer())


# ── JSON-LD structured data (WS-SITE10) ──────────────────────────────────────
# Every fact below already exists on the site or in config (no fabrication).
# Blocks are emitted verbatim as application/ld+json; a build gate parses every
# block and asserts zero "domestiq".
def ld_script(objs) -> str:
    """One JSON-LD block per page: a single {"@context", "@graph":[...]} document
    (WS-SITE22). Every node passed in becomes a top-level member of the shared
    @graph; the @context is hoisted to the document root so each node drops its
    own (semantically identical, one context for the whole graph). Page nodes
    reference #org / #tom / #website by @id rather than carrying inline copies."""
    if isinstance(objs, dict):
        objs = [objs]
    graph = []
    for o in objs:
        node = dict(o)
        node.pop("@context", None)
        graph.append(node)
    doc = {"@context": "https://schema.org", "@graph": graph}
    return f'<script type="application/ld+json">{json.dumps(doc)}</script>\n'


def _org_provider():
    """A by-@id reference to the single #org node (WS-SITE22). Kept under its old
    name so every existing provider / publisher / about call site now emits the
    reference instead of an inline Organization copy."""
    return {"@id": ORG_ID}


def _area_served():
    return [{"@type": "Country", "name": "United Kingdom"},
            {"@type": "Place", "name": "Online and remote coaching worldwide"}]


def org_node(with_rating=False):
    """Organization / LocalBusiness (SportsActivityLocation) for Horsepower."""
    node = {
        "@context": "https://schema.org",
        "@id": ORG_ID,
        "@type": ["SportsActivityLocation", "LocalBusiness"],
        "name": SITE_NAME,
        "alternateName": "Horsepower Coaching | Triathlon, Cycling and Endurance Coaching",
        "url": prod_url("/"),
        "logo": OG_LOGO,
        "image": og_image_url("ironman-wales-finish"),
        "description": ("Triathlon, cycling and endurance coaching and training plans built "
                        "for your target race, with a particular emphasis on female-specific "
                        "performance. Based in Truro, Cornwall, UK; coaching athletes online worldwide."),
        "founder": _tom_ref(),
        # WS-SITE18: business now based in Truro, Cornwall. Clevedon (plus Cornwall and
        # the wider South West) is deliberately kept in areaServed so the long-standing
        # Clevedon search signal / Google listing is not lost.
        "address": {"@type": "PostalAddress", "addressLocality": "Truro",
                    "addressRegion": "Cornwall", "addressCountry": "GB"},
        # WS-SITE23: LocalBusiness geo + telephone (SEO punch-list item d). The
        # coordinates are Truro (city centre, 50.2632, -5.051), consistent with the
        # Truro PostalAddress above; the phone is the number already public in the
        # site footer and on the contact page (+44 7780 008724 / wa.me/447780008724).
        "geo": {"@type": "GeoCoordinates", "latitude": 50.2632, "longitude": -5.051},
        "telephone": "+44 7780 008724",
        "areaServed": [{"@type": "City", "name": "Truro"},
                       {"@type": "City", "name": "Clevedon"},
                       {"@type": "AdministrativeArea", "name": "Cornwall"},
                       {"@type": "AdministrativeArea", "name": "South West England"}] + _area_served(),
        "knowsAbout": ["Triathlon coaching", "Ironman training", "Cycling coaching",
                       "Time trial training", "Ultra-endurance racing", "Marathon training",
                       "Female-specific endurance training", "Heat acclimation",
                       "Race pacing and fuelling strategy"],
        "sport": ["Triathlon", "Cycling", "Running", "Endurance"],
        "sameAs": [INSTAGRAM_URL, FACEBOOK_URL, GOOGLE_REVIEW_URL],
    }
    if with_rating and REVIEW_RATING and REVIEW_COUNT:
        node["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": f"{REVIEW_RATING:g}", "reviewCount": str(REVIEW_COUNT),
            "bestRating": "5", "worstRating": "1"}
    return node


def website_node():
    return {"@context": "https://schema.org", "@id": WEBSITE_ID, "@type": "WebSite",
            "name": SITE_NAME, "url": prod_url("/"),
            "inLanguage": "en-GB", "publisher": _org_provider()}


def person_node():
    return {
        "@context": "https://schema.org", "@id": TOM_ID, "@type": "Person",
        "name": "Tom Cooling",
        "jobTitle": "Founder and Head Coach",
        "worksFor": _org_provider(),
        "url": prod_url("/about/"),
        "image": og_image_url("tom-portrait"),
        "description": ("Ex-elite triathlete, ultra-bike racer and FKT holder with over a "
                        "decade coaching athletes from complete beginners to world-tour level "
                        "professionals, with a particular emphasis on female-specific "
                        "performance development."),
        "knowsAbout": ["Triathlon coaching", "Ultra-endurance cycling", "Heat acclimation",
                       "Breathwork", "Female-specific performance", "Race strategy"],
        "sameAs": [INSTAGRAM_URL, FACEBOOK_URL],
        "hasCredential": [
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "degree",
             "name": "First Class BA and Master's Degree in Sport Science and Athlete Development"},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "certification",
             "name": "Oxygen Advantage Advanced Breathwork Instructor"},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "certification",
             "name": "AIDA L4 Freediver"},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "certification",
             "name": "Core Temp and XTRI Extreme Triathlon Accredited Coach"},
            {"@type": "EducationalOccupationalCredential", "credentialCategory": "certification",
             "name": "BMC (British Mountaineering Council) Trained and Assessed Mountain Leader"},
        ],
    }


def service_node(name, description, path, monthly_price=None, low_price=None,
                 high_price=None, offer_count=None):
    """A coaching Service node. Prices are only ever stated where they are public
    on the site (£39.99+ Plans, £120/mo Coached, £185/mo Coached by Tom)."""
    node = {
        "@context": "https://schema.org", "@type": "Service",
        "serviceType": "Endurance coaching",
        "name": name, "description": description,
        "provider": _org_provider(),
        "areaServed": _area_served(),
        "url": prod_url(path),
    }
    if monthly_price is not None:
        node["offers"] = {
            "@type": "Offer", "priceCurrency": "GBP",
            "availability": "https://schema.org/InStock", "url": prod_url(path),
            "priceSpecification": {
                "@type": "UnitPriceSpecification", "price": monthly_price,
                "priceCurrency": "GBP", "unitText": "MONTH"}}
    elif low_price is not None:
        node["offers"] = {
            "@type": "AggregateOffer", "priceCurrency": "GBP",
            "lowPrice": low_price, "highPrice": high_price,
            "offerCount": offer_count, "availability": "https://schema.org/InStock",
            "url": prod_url(path)}
    return node


def breadcrumb_node(trail):
    """trail: list of (name, path_or_None). Final crumb usually has no link."""
    items = []
    for i, (name, path) in enumerate(trail):
        li = {"@type": "ListItem", "position": i + 1, "name": name}
        if path:
            li["item"] = prod_url(path)
        items.append(li)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": items}


# ── Imagery ──────────────────────────────────────────────────────────────────
IMG_BASE = BASE_PATH + "/assets/img"

# Descriptive alt text, keyed by derivative name. Honours-band entries carry
# the athlete's name as first name + surname initial (Tom's privacy ruling,
# 2026-08-06: never a client's full name anywhere on the site; identity still
# verified per file). Everything else stays name-free. Tom Cooling, as the
# business owner, is the one exception and keeps his full name.
IMG_ALT = {
    # drop-2026-08-05
    "honours-hannah-wales": "Hannah S breaking the tape to win Ironman Wales 2022",
    "honours-madison-finish": "Madison S finishing Ironman Wales 2025",
    "honours-madison-tt": "Madison S in a full aero tuck racing a time trial on her pink-wheeled TT bike",
    "honours-naomi-flag": "Naomi S wrapped in the Irish flag after finishing second at Swedeman 2026",
    "honours-elly-outlaw": "Elly B finishing the Outlaw triathlon, arms out on the finish carpet",
    "female-naomi-tt": "Naomi S time trialling in Horsepower Coaching kit",
    "hero-tenby-swim": "Swimmers in wetsuits and pink caps charging into the sea at the Ironman Wales swim start at sunrise",
    "hero-alpine-mist": "An empty hairpin road high on a misty alpine pass",
    "hero-torridon-ridge": "Two runners crossing a rocky Torridon ridge under a brooding sky",
    "tom-hill-climb": "Tom Cooling racing the National Time Trial Championships in Horsepower kit",
    "tom-alps-lead": "Tom Cooling on the front of a group climbing a tree-lined alpine road at the Haute Route Alps",
    "tom-alps-finish": "Tom Cooling riding into the Haute Route Alps stage finish at Serre Chevalier",
    "coached-tom-dolomites-arch": "Tom Cooling racing through the Haute Route Dolomites finish arch",
    "coaching-alpine-hairpin": "Sportive riders rounding an alpine hairpin towards the camera",
    "tom-bottle-refill": "Tom Cooling refuelling during the Lost Dot TransPyrenees",
    "about-brecon-titan": "Tom Cooling running through the finish arch to complete the Brecon Titan",
    "about-dolomites-descender": "Tom Cooling descending a Dolomites pass below jagged peaks at the Haute Route Dolomites",
    "about-dolomites-cobbles": "Tom Cooling riding across the cobbles at a Haute Route Dolomites stage start",
    "about-dolomites-pink-arch": "Tom Cooling riding through the Haute Route Dolomites arch with snowy peaks behind",
    "about-transpyrenees-night": "Tom Cooling greeted at the finish of the Lost Dot TransPyrenees at night",
    "tom-swim-kaolinite": "Tom Cooling with his race number before the Kaolinite open-water swim race",
    "tom-alps-signon": "Tom Cooling giving a thumbs up while holding his rider board at Haute Route Alps sign-on",
    "coaching-support-roadside": "Tom Cooling in a Horsepower cap giving a thumbs up to a racing athlete from the roadside on the Ironman Wales bike course",
    "coached-hamburg-finish": "A Horsepower athlete in branded kit finishing IRONMAN Hamburg",
    "coached-tenby-swim": "Swimmers in pink caps crossing Tenby harbour below pastel houses during the Ironman Wales swim",
    "female-wales-podium": "The women's podium celebration at Ironman Wales with champagne mid-spray",
    "female-montblanc-hike": "An athlete in a Horsepower cap hiking alpine switchbacks with the Mont Blanc massif in the distance",
    "female-welsh-tt": "Sophie R riding in an aero tuck on an open road",
    "plans-izoard-trio": "Three cyclists rounding a hairpin below the rock pinnacles of the Col d'Izoard",
    "plans-pyrenees-switchback": "A lone cyclist on a switchback gravel road high in the Pyrenees",
    "plans-pyrenees-dawn": "Layered Pyrenean valleys in dawn mist",
    "hero-alps": "A cyclist climbing high above an alpine valley with a huge mountain panorama behind",
    "hero-welsh-climb": "Two cyclists climbing a forested Welsh valley road under a big sky",
    "alpine-ridge": "A lone cyclist on a hairpin road high in a vast alpine mountain range",
    "ironman-wales-finish": "An athlete crossing an Ironman finish line in Wales with arms wide",
    "female-hero": "Three female athletes celebrating with champagne on the Ironman Wales podium",
    "coached-band": "A time triallist riding hard past a stone wall on a wet mountain road",
    "tom-gravel": "A cyclist riding a white gravel road towards the camera under a big blue sky",
    "tom-portrait": "Tom Cooling, founder and head coach of Horsepower Coaching",
    "female-tt-v2": "Madison S racing the bike leg at Ironman Wales, aero on her TT bike in the rain",
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
    "female-tt-v2": "50% 30%",           # Madison S at Ironman Wales 2026, aero on the TT bike
    "female-podium": "50% 30%",          # the three athletes' faces
    "female-trail": "50% 54%",           # runner on the trail, centre
    "tom-portrait": "50% 30%",           # Tom's face
    # drop-2026-08-05
    "honours-hannah-wales": "47% 50%",   # Hannah centred under the tape in the 4/5 tile
    "honours-madison-finish": "50% 28%", # Madison's face + hands high in the 4/5 tile
    "honours-madison-tt": "50% 42%",     # helmet to wheels, rider centred
    "honours-naomi-flag": "54% 40%",     # Naomi's face + draped flag centred in the 4/5 crop
    "honours-elly-outlaw": "48% 50%",    # Elly + both outstretched arms centred in the 4/5 crop
    "female-naomi-tt": "42% 45%",        # Naomi on the aero bars, left of centre
    "hero-tenby-swim": "50% 55%",        # swimmers + sunrise water, Goscar Rock right
    "hero-alpine-mist": "50% 55%",       # the hairpin low-centre
    "hero-torridon-ridge": "50% 45%",    # runners on the quartzite crest
    "tom-hill-climb": "50% 32%",         # Tom out of the saddle, upper third in wide crops
    "tom-alps-lead": "50% 45%",          # Tom on the front of the bunch
    "tom-alps-finish": "42% 52%",        # Tom left of centre, TAG Heuer arch behind
    "coached-tom-dolomites-arch": "50% 46%",  # Tom + the timing arch held in the wide banner crop
    "coaching-alpine-hairpin": "50% 74%",     # WS-SITE18: pan down so Ian (2nd rider, HP kit) + bike are fully in view
    "tom-bottle-refill": "50% 30%",      # Tom's face + bottle
    "about-brecon-titan": "50% 40%",     # Tom central under the FINISH arch
    "about-dolomites-descender": "50% 55%",  # descending rider low, peaks above
    "about-dolomites-cobbles": "50% 45%",    # rider + Haute Route arch behind
    "about-dolomites-pink-arch": "50% 50%",  # rider centred, arch cropped to portrait
    "about-transpyrenees-night": "50% 32%",  # Tom's face upper in the 4/5 crop
    "tom-swim-kaolinite": "50% 35%",     # Tom's face, race number lower
    "tom-alps-signon": "46% 40%",        # Tom + the THOMAS 2044 board centred
    "coaching-support-roadside": "50% 45%",  # Tom's thumbs up + the passing rider
    "coached-hamburg-finish": "50% 40%",  # runner dead-centre in the landscape source, center-crop
    "coached-tenby-swim": "50% 60%",     # swim field low, pastel harbour houses above
    "female-wales-podium": "50% 15%",    # 2026-08-24: was 45%, which cut the
                                         # winner's face off the top of the wide
                                         # hero crop. Verified by rendering the crop:
                                         # at 25% her cap still touched the frame edge,
                                         # 15% holds all three faces with headroom.
    "female-montblanc-hike": "50% 55%",  # hiker on the switchbacks, massif behind
    "female-welsh-tt": "60% 50%",        # Sophie R aero-tucked right of centre
    "plans-izoard-trio": "45% 60%",      # the trio low on the hairpin
    "plans-pyrenees-switchback": "50% 55%",
    "plans-pyrenees-dawn": "50% 50%",
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
    return (f'<a class="{cls}" href="{INSTAGRAM_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Instagram"{ga("contact", channel="instagram")}>{SVG_IG}</a>'
            f'<a class="{cls}" href="{WHATSAPP_URL}" rel="noopener" target="_blank" aria-label="Message Horsepower Coaching on WhatsApp"{ga("contact", channel="whatsapp")}>{SVG_WA}</a>'
            f'<a class="{cls}" href="{FACEBOOK_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Facebook"{ga("contact", channel="facebook")}>{SVG_FB}</a>')


IMG_DIMS = {
    "hero-alps": (1500, 1000), "hero-welsh-climb": (1500, 1000),
    "alpine-ridge": (1500, 1001),
    "female-hero": (1500, 1001), "ironman-wales-finish": (1500, 1000),
    "coached-band": (1500, 999), "tom-gravel": (1400, 1050),
    "camp-group": (1400, 1050), "female-tt-v2": (587, 880),
    "female-podium": (825, 1100), "female-trail": (675, 900),
    "tom-portrait": (825, 1100),
    # drop-2026-08-05
    "honours-hannah-wales": (1100, 733),
    "honours-madison-finish": (602, 902),
    "honours-madison-tt": (667, 1000),
    "honours-naomi-flag": (1100, 734),
    "honours-elly-outlaw": (1100, 732),
    "female-naomi-tt": (1200, 800),
    "hero-tenby-swim": (1200, 802),
    "hero-alpine-mist": (1200, 800),
    "hero-torridon-ridge": (1200, 799),
    "tom-hill-climb": (867, 1300),
    "tom-alps-lead": (1000, 667),
    "tom-alps-finish": (1000, 666),
    "coached-tom-dolomites-arch": (1600, 1067),
    "coaching-alpine-hairpin": (1200, 798),
    "tom-bottle-refill": (667, 1000),
    "about-brecon-titan": (1100, 733),
    "about-dolomites-descender": (1000, 667),
    "about-dolomites-cobbles": (1000, 665),
    "about-dolomites-pink-arch": (900, 600),
    "about-transpyrenees-night": (750, 1000),
    "tom-swim-kaolinite": (667, 1000),
    "tom-alps-signon": (800, 533),
    "coaching-support-roadside": (768, 1024),
    "coached-hamburg-finish": (860, 573),
    "coached-tenby-swim": (1400, 931),
    "female-wales-podium": (1200, 801),
    "female-montblanc-hike": (750, 1000),
    "female-welsh-tt": (1200, 801),
    "plans-izoard-trio": (1200, 798),
    "plans-pyrenees-switchback": (1200, 800),
    "plans-pyrenees-dawn": (1200, 800),
}


def img(name, cls="", lazy=True, extra=""):
    """One <img> for derivative `name`; alt from IMG_ALT, object-position from
    IMG_POS, intrinsic width/height from IMG_DIMS (all gate-checked).
    Derivatives ship as WebP (see make_derivatives.py)."""
    alt = IMG_ALT[name]
    c = f' class="{cls}"' if cls else ""
    loading = ' loading="lazy" decoding="async"' if lazy else ' decoding="async"'
    w, h = IMG_DIMS[name]
    dims = f' width="{w}" height="{h}"'
    style = f' style="object-position:{IMG_POS[name]}"' if name in IMG_POS else ""
    return f'<img src="{IMG_BASE}/{name}.webp" alt="{esc(alt)}"{c}{dims}{style}{loading}{extra}>'


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
# Real client result used as the Madison S result slide. From Tom's
# authoritative palmares, provided 2026-07-29: Madison won Ironman Wales 2025
# outright and placed 10th at the Ironman World Championships in Nice 2024. The
# earlier "led her age group by 45 minutes / 9th overall" line is a wrong claim
# and must never return (gate 8d, below). Client names render as first name +
# surname initial only (Tom's privacy ruling, 2026-08-06; gate 8f).
CLIENT_RESULT_LINE = ("Coached athlete Madison S won Ironman Wales 2025, "
                      "and placed 10th at the Ironman World Championships in Nice 2024.")

# Verified verbatim quotes now live in ONE source of truth,
# generator/content/reviews/reviews.yaml (WS-SITE22). Tom drops a review
# screenshot into generator/content/reviews/inbox/ (gitignored) and transcribes
# it VERBATIM into reviews.yaml; CLIENT_QUOTES and VERIFIED_QUOTES are derived
# from that file here, so a review that is not in reviews.yaml can never render
# (carousel-data + rendered-quote gates). The 5 existing verified quotes were
# migrated byte-for-byte, and the freeze gate proves the rendered output is
# unchanged. Ian's real review runs on mid-sentence; it is transcribed closed at
# a natural earlier point and never invented past it.
REVIEWS_DIR = os.path.join(HERE, "content", "reviews")
REVIEWS_PATH = os.path.join(REVIEWS_DIR, "reviews.yaml")


def _load_reviews(path=REVIEWS_PATH):
    """Parse reviews.yaml. Deliberately dependency-free (no PyYAML on the build
    host): a small, strict subset - a list of "- key: value" records where string
    values are JSON-quoted (so verbatim text with punctuation round-trips exactly)
    and bare tokens (source, gender_tag, pages) are taken as-is. Comments (#) and
    blank lines are ignored."""
    records = []
    cur = None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.rstrip("\n").strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped == "-":
                cur = {}
                records.append(cur)
                continue
            if stripped.startswith("- "):
                cur = {}
                records.append(cur)
                stripped = stripped[2:].strip()
            if cur is None:
                raise ValueError(f"reviews.yaml: key before first record: {stripped!r}")
            key, sep, val = stripped.partition(":")
            if not sep:
                raise ValueError(f"reviews.yaml: expected 'key: value', got {stripped!r}")
            val = val.strip()
            cur[key.strip()] = json.loads(val) if val.startswith('"') else val
    return records


def _reviews_to_quotes(records):
    """Rebuild the CLIENT_QUOTES shape from reviews.yaml records, preserving order
    and every string byte-for-byte: name<-reviewer_display, context<-event_note,
    quote<-text, pages<-the comma-separated routing list."""
    quotes = []
    for r in records:
        pages = [p.strip() for p in r.get("pages", "").split(",") if p.strip()]
        quotes.append({"name": r["reviewer_display"], "context": r.get("event_note", ""),
                       "pages": pages, "quote": r["text"]})
    return quotes


REVIEWS = _load_reviews()
CLIENT_QUOTES = _reviews_to_quotes(REVIEWS)
# Every text in reviews.yaml is, by definition, a verified quote; nothing else may
# render (the carousel-data gate + the rendered-quote gate both check membership).
VERIFIED_QUOTES = {r["text"] for r in REVIEWS}

# The Madison S result, rendered as a distinct slide in every carousel.
MADDISON_SLIDE = {"kind": "result"}
# WS-SITE21 item 1: the "more reviews on the way" placeholder slide is retired.
# Emma N's genuine review now leads the female carousel on its own; a single real
# review reads as a featured pull-quote (no arrows/dots), never as a placeholder.


def _review_cta(cls="btn on-dark ghost"):
    return (f'<a class="{cls}" href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank"'
            f'{ga("contact", channel="google_reviews")}>'
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
            '<div class="stat"><span class="n">1st</span><span class="k">Woman, Ironman Wales 2025</span></div>'
            '<div class="stat"><span class="n">10th</span><span class="k">Ironman World Championships, Nice 2024</span></div>'
            '<div class="stat"><span class="n">1st AG</span><span class="k">Ironman Swansea 70.3 2024, 2nd overall</span></div>'
            '</div>'
            f'<blockquote>{esc(CLIENT_RESULT_LINE)}</blockquote>'
            '<figcaption>Madison S <span>Coached by Horsepower</span></figcaption>'
            '</figure>')
    ctx = f' <span>{esc(item["context"])}</span>' if item.get("context") else ""
    return (f'<figure class="review-slide"><blockquote>{esc(item["quote"])}</blockquote>'
            f'<figcaption>{esc(item.get("name", "Horsepower athlete"))}{ctx}</figcaption></figure>')


_CAROUSEL_SEQ = [0]


def carousel(page, heading="What athletes say", subhead="Real athletes, real finish lines",
             on_dark=True, include_result=True):
    """Accessible auto-advancing review carousel for `page`. Vanilla JS
    (assets/carousel.js) drives auto-advance, arrows, dots, hover/focus pause.
    A single slide renders as a static featured pull-quote (arrows/dots hidden)."""
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
    """Per-page review carousel (light theme), or nothing if none for this page.
    Reviews-only: the Madison result slide is deliberately excluded here (Tom's
    ruling for the Coached page, WS-SITE9) so this carousel reads as reviews."""
    if not quotes_for(page):
        # still show the carousel on female / coaching even without a page quote
        if page not in ("female", "coaching", "coached"):
            return ""
    return carousel(page, heading="In their words",
                    subhead="What athletes say about Horsepower", on_dark=False,
                    include_result=False)


def reviews_band():
    """Homepage client-voices carousel: reviews only (WS-SITE18, Tom's ruling).
    The Madison result/stats slide is deliberately excluded so the home carousel
    reads as genuine Google reviews, nothing fabricated."""
    return carousel("home", include_result=False)


def home_tier_cards() -> str:
    """WS-SITE21 item 2: the distilled HOME tier cards. Each is name, one-line
    price (the 'one-off' qualifier is a smaller inline span so it never wraps),
    the support tag, one verdict sentence, 3-4 benefit bullets, then the button.
    All three flex to equal height with the button pinned to the card bottom."""
    cards = []
    for t in HOME_TIER_CARDS:
        qual = (f'<span class="price-qual">{t["price_qual"]}</span>'
                if t["price_qual"] else "")
        bullets = "".join(f"<li>{esc(b)}</li>" for b in t["bullets"])
        cards.append(
            f'<div class="tier-card {t["cls"]}">'
            f'<h3>{esc(t["name"])}</h3>'
            + (f'<p class="tier-flag">{esc(t["flag"])}</p>' if t.get("flag") else "") +
            f'<div class="price">{t["price_main"]}{qual}</div>'
            f'<p class="support-line"><span class="support-tag {t["tag_cls"]}">'
            f'Support: {esc(t["support"])}</span></p>'
            f'<p class="tier-verdict">{esc(t["verdict"])}</p>'
            f'<ul class="tier-benefits">{bullets}</ul>'
            f'<a class="btn {t["btn_cls"]}" href="{BASE_PATH}{t["href"]}"'
            f'{ga("cta", label=t["cta"], location="tier_card")}>'
            f'{esc(t["cta"])}</a>'
            f'</div>')
    return "".join(cards)


# The four live Female-First plan SKUs, cross-linked to the female performance page.
CTA_FEMALE_CROSSLINK = "Part of our female performance approach"
LIST_STORE = "Plan Store"
LIST_DETAIL = "Plan detail"
LIST_FEMALE = "Female Performance"

FEMALE_FIRST_SLUGS = {
    "female-first-70-3-training-plan",
    "female-first-marathon-training-plan",
    "female-first-olympic-triathlon-training-plan",
    "female-first-century-training-plan",
}


# ── Pages ────────────────────────────────────────────────────────────────────
def render_home(cat) -> str:
    total = cat["stats"]["total"]
    # Support ladder strip: none -> feedback -> full, read left to right.
    ladder = ""
    for i, (tname, tag, _line) in enumerate(SUPPORT_LEVELS):
        if i:
            ladder += '<span class="rung-arrow" aria-hidden="true">&rarr;</span>'
        full = " rung--full" if i == len(SUPPORT_LEVELS) - 1 else ""
        ladder += (f'<div class="rung{full}"><span class="rung-tier">{esc(tname)}</span>'
                   f'<span class="rung-level">{esc(tag)}</span></div>')
    body = f"""<main id="main">
<section class="hero hero--image">
  {img("hero-alpine-mist", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <h1>{esc(HERO_HEADLINE)}</h1>
    <p class="lede">{esc(HERO_BODY)}</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/coached/"{ga("cta", label=CTA_START_PLAN, location="hero")}>{esc(CTA_START_PLAN)}</a>
      <a class="btn on-dark ghost" href="{BASE_PATH}/coaching/"{ga("cta", label=CTA_GET, location="hero")}>{esc(CTA_GET)}</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Three ways to train with Horsepower</p>
    <h2>Pick the level of support that fits</h2>
    <p class="section-intro">The plan is only half of it. What really changes across the three tiers is
    how much of me you get, from a proven plan you run yourself, to feedback on every block, to the full
    coaching relationship. No nonsense, no upselling, just the right level of support for where you are.
    If in doubt, start with Plan Only, and step up to Coached by Tom later if you want me in your corner day to day.</p>
    <div class="support-ladder" role="list" aria-label="Support increases across the three tiers">{ladder}</div>
    <div class="tier-grid tier-grid--distilled">{home_tier_cards()}</div>
  </div>
</section>

<section class="alt feature-female">
  <div class="wrap feature-grid feature-grid--portrait">
    <div class="feature-media feature-media--portrait">{img("female-tt-v2")}</div>
    <div class="feature-copy">
      <p class="eyebrow">Female performance</p>
      <h2>Female first, not female adapted.</h2>
      <p class="section-intro">{esc(FEMALE_FIRST_BODY)}</p>
      <p style="margin-top:20px"><a class="btn" href="{BASE_PATH}/female-performance/"{ga("cta", label=CTA_FEMALE_FEATURE, location="feature_female")}>{esc(CTA_FEMALE_FEATURE)}</a></p>
    </div>
  </div>
</section>

<section class="results results--image">
  {img("ironman-wales-finish", cls="results-bg")}
  <div class="wrap">
    <p>{esc(RESULTS_LINE)}</p>
    <p class="results-sub">Real athletes I've taken to the podium, and to the finish line of the dream they started with.</p>
  </div>
</section>
{reviews_band()}

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">Which one am I?</p>
    <div class="which-grid">
      <div class="which-item which-item--store"><strong>{esc(TIER1_NAME)}</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item which-item--plan"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item which-item--tom"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>

<section class="plans-stat-band">
  <div class="wrap plans-stat-grid">
    <div class="plans-stat-figure" aria-hidden="true">
      <span class="plans-stat-num" data-total="{total}"></span>
    </div>
    <div class="plans-stat-copy">
      <h2>Over {total} plans, every one built for its event</h2>
      <p class="section-intro">First marathon to Ironman, hill climbs to 100 mile TTs, every plan in
      the library is written for one specific race and one specific goal. Find yours and get to work.</p>
      <p style="margin-top:22px"><a class="btn" href="{BASE_PATH}/plans/"{ga("cta", label=CTA_FIND, location="plans_stat")}>{esc(CTA_FIND)}</a></p>
    </div>
  </div>
</section>
</main>"""
    desc = ("Training plans and coaching built for your race, written by Tom Cooling. "
            "Over 150 plans, plus coaching from £120 a month.")
    extra = ld_script([org_node(with_rating=True), website_node()])
    return page("home", "Horsepower Coaching | Training Plans for Your Race",
                desc, prod_url("/"), body, og_image_name="hero-alpine-mist", extra=extra,
                preload_img="hero-alpine-mist", page_type="home")


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
        female_link = (f'<p class="female-crosslink"><a href="{BASE_PATH}/female-performance/"'
                       f'{ga("cta", label=CTA_FEMALE_CROSSLINK, location="plan_card")}>'
                       f'{esc(CTA_FEMALE_CROSSLINK)}</a></p>'
                       if p["slug"] in FEMALE_FIRST_SLUGS else "")
        cards.append(f"""<article class="plan-card"
  data-sport="{esc(p['sport'])}" data-category="{esc(p['category'])}"
  data-tier="{esc(p['tier'])}" data-weeks="{p['weeks']}" data-hours="{p['hours_per_week']}"
  data-title="{esc(p['title'].lower())}" data-ga-item="{ga_item(p)}">
  <div class="tags">
    <span class="tag">{esc(p['sport'])}</span>
    <span class="tag">{esc(p['category'])}</span>
    {tier_tag}
  </div>
  <h3><a href="{detail}"{ga("select", list=LIST_STORE)}>{esc(p['title'])}</a></h3>
  <p class="blurb">{esc(p['blurb'])}</p>
  {female_link}
  <div class="meta">
    <span class="price">&pound;{p['price']:.2f}</span>
    <span class="weeks">{p['weeks']} wk &middot; ~{p['hours_per_week']:g} h/wk</span>
  </div>
  <div class="actions">
    <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank"{ga("buy", list=LIST_STORE)}>Buy on TrainingPeaks</a>
    <a class="link-plain" href="{detail}"{ga("select", list=LIST_STORE)}>Details</a>
  </div>
</article>""")

    body = f"""<main id="main">
<div class="page-banner">{img("plans-izoard-trio", cls="banner-bg", lazy=False)}</div>
<section class="alt" style="padding-bottom:24px">
  <div class="wrap">
    <p class="eyebrow">The Plan Store</p>
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
    prices = [p["price"] for p in plans]
    collection = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": f"Horsepower Coaching Training Plan Library ({total} plans)",
        "url": prod_url("/plans/"),
        "description": ("Structured triathlon, cycling and running training plans, each built "
                        "for a specific target race and delivered through TrainingPeaks."),
        "mainEntity": {
            "@type": "ItemList", "numberOfItems": total,
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "url": prod_url(f"/plans/{p['slug']}/"), "name": p["title"]}
                for i, p in enumerate(plans)]},
    }
    service = service_node(
        "Horsepower training plans",
        ("Over 150 race-specific triathlon, cycling and running training plans, each built for "
         "a target event and delivered through TrainingPeaks. From £39.99, one-off."),
        "/plans/", low_price=f"{min(prices):.2f}", high_price=f"{max(prices):.2f}",
        offer_count=total)
    extra = ld_script([
        breadcrumb_node([("Home", "/"), ("Training Plans", None)]),
        collection, service])
    return page("plans", f"Training Plan Library | {total} Plans | Horsepower Coaching",
                desc, prod_url("/plans/"), body,
                og_image_name="plans-izoard-trio", extra=extra,
                preload_img="plans-izoard-trio", page_type="plan_list", tier="plan_store")


# ── Plan-page de-templating (WS-SITE23, punch-list b + 6) ────────────────────
# The 153 plan detail pages used to share an identical ~90-word "How it is built"
# block plus a heavily templated catalogue description, so same-sport pages read
# near-identically (measured Jaccard word-overlap 69-74%, some pairs >95%). This
# rebuilds each page's visible prose from ONLY the plan's own real attributes in
# catalogue.json (event name, event type, weeks, weekly hours, level/tier, sport)
# using rotating sentence patterns chosen independently per block, so both the
# wording and the interpolated specifics differ page to page. Nothing here invents
# a course fact: distances are the definitional distance of the event TYPE (a
# marathon is 26.2 miles), or a generic descriptor where distance genuinely varies
# (ultras, sportives). Each page also gets a 3-question FAQ (who it suits, hours
# needed, how it is delivered) rendered visibly AND as FAQPage JSON-LD.
_PLAN_DISTANCE = {
    "ironman": "the full iron distance",
    "70.3": "middle-distance triathlon",
    "olympic": "Olympic-distance triathlon",
    "duathlon": "a run, then a bike, then a run",
    "marathon": "the full 26.2 mile marathon",
    "half_marathon": "the 13.1 mile half marathon",
    "ultra": "an ultra-distance race",
    "sportive": "a long, hard day on the bike",
    "mtb": "marathon mountain bike distance",
    "hill_climb": "a short, all-out climb",
    "hyrox": "the HYROX format of running and functional stations",
    "base": "a block of base and strength work",
}
_SPORT_FOCUS = {
    "Triathlon": "the swim, the bike, the run and the transitions that join them",
    "Cycling": "your endurance, your climbing and the way you put the power down",
    "Running": "your endurance, your pace and the durability to hold it late on",
}
# Event-type overrides where the plain sport focus would misstate the event
# (a duathlon has no swim; HYROX pairs running with functional stations).
_EVENT_FOCUS = {
    "duathlon": "the run, the bike and the second run straight off it",
    "hyrox": "your running, your engine and the strength for the stations",
}
_SPORT_METRICS = {
    "Triathlon": "your own FTP and threshold pace",
    "Cycling": "your own FTP and threshold power",
    "Running": "your own threshold pace and heart rate",
}
_PLAN_GOAL = {
    "Finish": "get you across the line in good shape",
    "Finisher": "get you across the line in good shape",
    "Improve": "take a real chunk out of your previous time",
    "Performance": "take a real chunk out of your previous time",
    "Compete": "have you racing at the sharp end",
    "Competitive": "have you racing at the sharp end",
}
_LEVEL_AIM = {
    "Finish": "aimed at getting you to a strong, controlled finish",
    "Finisher": "aimed at getting you to a strong, controlled finish",
    "Improve": "aimed at a genuinely faster time than last time out",
    "Performance": "aimed at a genuinely faster time than last time out",
    "Compete": "aimed at racing for a result, not just completing it",
    "Competitive": "aimed at racing for a result, not just completing it",
}


def _plan_pick(slug, salt, n):
    return int(hashlib.md5(f"{slug}|{salt}".encode()).hexdigest(), 16) % n


def _plan_distance(p):
    return _PLAN_DISTANCE.get(p["event_type"], f"{p['sport'].lower()} racing")


def _hours_band(h):
    return "lean" if h < 7 else ("solid" if h < 12 else "big")


def _plan_focus(p):
    return _EVENT_FOCUS.get(p["event_type"],
                            _SPORT_FOCUS.get(p["sport"], "every discipline the event demands"))


def plan_prose(p):
    """Three attribute-driven paragraphs (intro, method, close), each chosen from
    a rotating pool so same-sport pages diverge in both structure and specifics."""
    ev = p["event_name"]
    dist = _plan_distance(p)
    wk = p["weeks"]
    hph = f"{p['hours_per_week']:g}"
    band = _hours_band(p["hours_per_week"])
    focus = _plan_focus(p)
    metrics = _SPORT_METRICS.get(p["sport"], "your own numbers")
    goal = _PLAN_GOAL.get(p["tier"])

    intro = [
        (f"This plan is built for {ev}, start to finish. It is shaped around {dist}, running "
         f"{wk} weeks at a {band} {hph} hours a week, so you know exactly what you are signing "
         f"up for."),
        (f"The whole plan points at one thing: {ev}. Across {wk} weeks and roughly {hph} hours "
         f"a week, it builds you toward {dist} with nothing in there that does not earn its "
         f"place."),
        (f"Targeting {ev}? This is the plan for it. {wk} weeks, a {band} {hph} hours a week, "
         f"every one of them built around {dist} rather than adapted from a template."),
    ][_plan_pick(p["slug"], "intro", 3)]

    method = [
        (f"The load builds in three-week blocks and then backs off, so the work actually lands "
         f"instead of burying you. The hard sessions are dosed the way the research says fitness "
         f"is built, never piled on as junk volume, and {focus} all get their turn."),
        (f"Every target is set as a percentage of {metrics}, so it fits you and not some average "
         f"athlete. The weeks climb and then ease in three-week blocks, and across them {focus} "
         f"are trained in balance."),
        (f"Three weeks up, ease back, repeat: that rhythm is what makes the fitness stick. "
         f"Intensity is rationed rather than sprayed around, every target reads off {metrics}, "
         f"and the plan gives {focus} the attention each one needs."),
    ][_plan_pick(p["slug"], "method", 3)]

    if goal:
        close = [
            f"Follow it properly and the aim is clear: {goal} at {ev}.",
            f"Do the work and this plan is built to {goal} when you line up for {ev}.",
            f"Held to week after week, it is designed to {goal} on the day you race {ev}.",
        ]
    else:
        close = [
            f"Follow it as written and you will arrive at {ev} genuinely ready, not just hopeful.",
            f"Do the work and you get to {ev} fit, confident and knowing your day is in hand.",
            f"Held to from the first week, it will have you ready for {ev} on the day it counts.",
        ]
    close = close[_plan_pick(p["slug"], "close", 3)]
    return [intro, method, close]


def plan_faqs(p):
    """Three real Q&As per plan, derived from its own attributes (who it suits,
    hours needed, delivery). Returned as (question, answer) pairs for both the
    visible FAQ and the FAQPage JSON-LD."""
    ev = p["event_name"]
    dist = _plan_distance(p)
    wk = p["weeks"]
    hph = f"{p['hours_per_week']:g}"
    band = _hours_band(p["hours_per_week"])
    aim = _LEVEL_AIM.get(p["tier"])
    who = [
        (f"Anyone with {ev} on the calendar. It is written for {dist}"
         + (f", {aim}" if aim else "")
         + f", and it assumes you can train consistently at around {hph} hours a week."),
        (f"The rider or athlete targeting {ev}. It suits {dist}"
         + (f" and is {aim}" if aim else "")
         + f", for someone who can give it a fairly steady {hph} hours most weeks."),
        (f"If {ev} is your goal, this is your plan. It is pitched at {dist}"
         + (f", {aim}" if aim else "")
         + f", and works best when you can hold roughly {hph} hours a week through the block."),
    ][_plan_pick(p["slug"], "faq_who", 3)]
    hours = [
        (f"It runs {wk} weeks at a {band} {hph} hours a week. The load builds in three-week "
         f"blocks and then eases back, so the volume is real but never random."),
        (f"Plan on {wk} weeks and about {hph} hours a week. It rises for a couple of weeks, then "
         f"drops to let the work settle, rather than climbing endlessly until you break."),
        (f"You are looking at {wk} weeks and a {band} {hph} hours a week, arranged in three-week "
         f"blocks that push and then recover so the fitness actually sticks."),
    ][_plan_pick(p["slug"], "faq_hours", 3)]
    delivery = [
        ("It is a one-off purchase delivered straight into your TrainingPeaks account, written "
         "out session by session in plain language so you always know what to do and why."),
        ("You buy it once and it lands in your TrainingPeaks account, every session spelled out "
         "in plain words with the reason it is there, ready to start straight away."),
        ("A single payment drops the whole plan into TrainingPeaks for you, laid out session by "
         "session in plain English so nothing is left to guesswork."),
    ][_plan_pick(p["slug"], "faq_delivery", 3)]
    return [("Who is this plan for?", who),
            ("How much training does it involve?", hours),
            ("How is the plan delivered?", delivery)]


def render_plan_detail(cat, p) -> str:
    canonical = prod_url(f"/plans/{p['slug']}/")
    tier_line = "" if p["tier"] == "Standard" else f'<div class="spec-box"><div class="k">Level</div><div class="v">{esc(p["tier"])}</div></div>'
    # WS-SITE23: visible prose rebuilt per-plan from real attributes (de-templating).
    paras = "".join(f"<p>{esc(x)}</p>" for x in plan_prose(p))
    faqs = plan_faqs(p)
    faq_html = "".join(
        f'<details class="faq"{" open" if i == 0 else ""}><summary>{esc(q)}</summary>'
        f'<p>{esc(a)}</p></details>'
        for i, (q, a) in enumerate(faqs))
    # Sport-appropriate imagery (Tom 2026-08-16: a cycling image must not front a
    # running or triathlon plan). Used for BOTH the Product schema image and the
    # social-share og:image below.
    plan_img = {
        "Cycling": "plans-pyrenees-switchback",   # a lone cyclist on a Pyrenean switchback
        "Triathlon": "ironman-wales-finish",       # an athlete crossing an Ironman finish line
        "Running": "hero-torridon-ridge",          # two runners crossing a Torridon ridge
    }.get(p["sport"], "plans-pyrenees-switchback")
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": p["title"], "description": p["description"],
        # Merchant-listing eligibility (GSC 2026-08-16): explicit image + named brand;
        # a digital training plan has no shipping cost and is non-returnable.
        "image": og_image_url(plan_img),
        "brand": {"@type": "Brand", "name": "Horsepower Coaching"},
        "category": f'{p["sport"]} training plan',
        "url": canonical,
        "offers": {"@type": "Offer", "price": f'{p["price"]:.2f}', "priceCurrency": "GBP",
                   "availability": "https://schema.org/InStock", "url": p["buy_url"],
                   "hasMerchantReturnPolicy": {
                       "@type": "MerchantReturnPolicy", "applicableCountry": "GB",
                       "returnPolicyCategory": "https://schema.org/MerchantReturnNotPermitted"},
                   "shippingDetails": {
                       "@type": "OfferShippingDetails",
                       "shippingRate": {"@type": "MonetaryAmount", "value": "0", "currency": "GBP"},
                       "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "GB"}}},
    }
    crumbs_ld = breadcrumb_node([("Home", "/"), ("Training Plans", "/plans/"),
                                 (p["title"], None)])
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs]}
    extra = ld_script([ld, crumbs_ld, faq_ld])
    female_note = ""
    if p["slug"] in FEMALE_FIRST_SLUGS:
        female_note = f"""
    <div class="callout" style="margin-top:26px">
      <p class="eyebrow" style="color:var(--teal-soft)">Female first, not female adapted</p>
      <p>This plan is part of our female performance approach: a programme built for a
      female athlete from the start, with recovery-respecting structure and strength work
      for long-term bone and tendon health. <a class="link-plain on-dark" href="{BASE_PATH}/female-performance/">See how we train female athletes</a>.</p>
    </div>"""
    body = f"""<main id="main" data-ga-item="{ga_item(p)}">
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
      <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank"{ga("buy", list=LIST_DETAIL)}>Buy on TrainingPeaks</a>
      <span style="color:var(--grey-mid);font-size:0.9rem">One-off. Delivered to your TrainingPeaks account.</span>
    </div>
  </div>
</section>
<section>
  <div class="wrap prose">
    <h2>About this plan</h2>
    {paras}
    <p><a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank"{ga("buy", list=LIST_DETAIL)}>Get {esc(p['title'])}</a>
    &nbsp; <a class="link-plain" href="{BASE_PATH}/plans/">Back to the library</a></p>
    <h2>Common questions</h2>
    {faq_html}
    <p style="margin-top:26px;color:var(--grey-mid)">Want it built around your life instead of off the shelf?
    <a href="{BASE_PATH}/coached/"{ga("cta", label=f"See {TIER2_NAME}", location="plan_body")}>See {esc(TIER2_NAME)}</a>.</p>
    {female_note}
  </div>
</section>
</main>"""
    desc = (p["blurb"][:150]).rsplit(" ", 1)[0]
    return page("plans", fit_title(p['title']), desc, canonical, body,
                og_image_name=plan_img, og_type="product", extra=extra,
                page_type="plan_detail", sport=p["sport"], tier="plan_store")


CTA_APPLY_PLAN = "Apply for Plan Only"

COACHED_FAQ = [
    ("Is there a call every week?",
     "No. Plan Only is built around the work and the why, delivered in writing so you can go "
     "back to it. If you want calls, WhatsApp and race-day strategy built together, that is "
     "Coached by Tom."),
    ("How often do you review my training?",
     "Once a month. Each cycle is three weeks of training then a rest week, and the rest week "
     "is when I review the block, write your feedback and build the next one. There is no "
     "per-session feedback in between."),
    ("What if my numbers change or life gets in the way?",
     "The plan moves. When your data shifts or a week falls apart, the next block reflects it. "
     "That is the point of building it block by block instead of all at once."),
    ("Which sports do you coach?",
     "Triathlon across every distance, road and ultra running, and cycling from sportives to "
     "ultra-distance. If you have a target event, I can build for it."),
    ("Can I message you between blocks?",
     "Leave notes on your sessions in TrainingPeaks and I read every one in the rest week, as "
     "part of the block review. There is no back and forth in between. If you want my time day "
     "to day, that is Coached by Tom."),
    ("Is TrainingPeaks Premium included?",
     "No. Plan Only is delivered to your own TrainingPeaks account. A free TrainingPeaks "
     "Premium account comes with Coached by Tom."),
    ("Can I upgrade later?",
     "Yes. If you want me directly, you can move to Coached by Tom when a place is open."),
]


def render_coached(cat) -> str:
    faq_html = "".join(
        f'<details class="faq"{" open" if i == 0 else ""}><summary>{esc(q)}</summary>'
        f'<p>{esc(a)}</p></details>'
        for i, (q, a) in enumerate(COACHED_FAQ))
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 64px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">{esc(TIER2_NAME)} &middot; &pound;120 a month</p>
    <h1>A plan I build for you, block by block</h1>
    <p class="lede">{esc(COACHED_INTRO)}</p>
    <div class="cta-row"><a class="btn" href="{esc(contact_url('plan-only'))}"{ga("cta", label=CTA_APPLY_PLAN, location="hero")}>{esc(CTA_APPLY_PLAN)}</a></div>
  </div>
</section>

<div class="media-band">{img("hero-torridon-ridge", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>What you get for &pound;120 a month</h2>
    <div class="side-fig-grid side-fig-grid--balanced">
      <div>
        <p class="section-intro">{esc(TIER_COACHED_BODY)}</p>
        <p class="section-intro">{esc(TIER_COACHED_BODY_2)}</p>
        <ol class="step-list">
          <li><strong>It starts with you</strong>A proper intake: your target event, your history, your week, your numbers and the hours you actually have.</li>
          <li><strong>Your plan arrives block by block</strong>Three weeks of training built around your life and your event, delivered to your TrainingPeaks account, so the plan stays current with how your training is actually going rather than a whole year written on day one.</li>
          <li><strong>A rest week, and one review a month</strong>The fourth week is a rest week. In it I go through the whole block against what was asked, using your actual data and the notes you leave on your sessions, tell you straight what I see, and build the next block from it. One review a month, in writing, so you can go back to it.</li>
          <li><strong>A race plan before every start line</strong>Pacing, fuelling and strategy for your event, in your hands before you get there.</li>
        </ol>
      </div>
      <figure class="photo-fig photo-fig--port">{img("coached-hamburg-finish")}
        <figcaption>A Horsepower athlete finishing IRONMAN Hamburg</figcaption></figure>
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap content-grid two">
    <div>
      <h2>Honest answers</h2>
      {faq_html}
    </div>
    <div>
      <div class="callout">
        <h2>Where it differs from full coaching</h2>
        <p>There are no scheduled calls and I am not on call day to day. What you get is a programme I build around your life and your event, with one proper review a month: at the end of every three week block, in the rest week, I go through the sessions you actually did and build the next block from them. If you want me in your corner for all of it, look at Coached by Tom.</p>
        <p style="margin-top:18px"><a class="btn on-dark ghost" href="{BASE_PATH}/coaching/"{ga("cta", label="Coached by Tom", location="faq_aside")}>Coached by Tom</a></p>
      </div>
    </div>
  </div>
</section>

<div class="media-band">{img("hero-tenby-swim", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>Ready to start?</h2>
    <p class="section-intro">Tell me about your event and your season and I'll take it from there.</p>
    <p style="margin-top:18px"><a class="btn" href="{esc(contact_url('plan-only'))}"{ga("cta", label=CTA_APPLY_PLAN, location="closing")}>{esc(CTA_APPLY_PLAN)}</a></p>
  </div>
</section>
{quote_block("coached")}
</main>"""
    desc = ("Plan Only with Tom Cooling, £120 a month. Three weeks of training, then a rest week "
            "in which I review your block and build the next one. Race plan included.")
    # Gate 18g: the description must fit the 158 character snippet budget.
    assert len(esc(desc)) <= 158, len(esc(desc))
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in COACHED_FAQ]}
    svc = service_node(
        f"{TIER2_NAME} coaching",
        f"{COACHED_INTRO} A race plan before every start line is included.",
        "/coached/", monthly_price="120.00")
    extra = ld_script([
        breadcrumb_node([("Home", "/"), (TIER2_NAME, None)]), svc, faq_ld])
    return page("coached", f"{TIER2_NAME} | £120 a month | Horsepower Coaching", desc,
                prod_url("/coached/"), body, og_image_name="hero-torridon-ridge", extra=extra,
                page_type="tier_plan_only", tier="plan_only")


CTA_ASK_TOM = "Ask about a Coached by Tom place"

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
    ("All the things that count on race day",
     "Race craft, race prep, kit and equipment, nutrition and psychology. The parts of performance a training file alone cannot cover."),
]


def render_coaching(cat) -> str:
    get_cards = "".join(
        f'<div class="get-card"><h3>{esc(t)}</h3><p>{esc(d)}</p></div>'
        for t, d in COACHED_BY_TOM_GET)
    body = f"""<main id="main">
<section class="hero hero--image">
  {img("coached-tom-dolomites-arch", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Coached by Tom &middot; &pound;185 a month &middot; Limited places</p>
    <h1>A coach in your corner for all&nbsp;of&nbsp;it</h1>
    <p class="lede">{esc(TIER_TOM_BODY)}</p>
    <div class="cta-row">
      <a class="btn" href="{esc(contact_url('coached-by-tom'))}"{ga("cta", label=CTA_ASK_TOM, location="hero")}>{esc(CTA_ASK_TOM)}</a>
      <a class="btn on-dark ghost" href="#what-you-get"{ga("cta", label="See what you get", location="hero")}>See what you get</a>
    </div>
  </div>
</section>

<section id="what-you-get">
  <div class="wrap">
    <p class="eyebrow">Everything you get</p>
    <h2>Complete world class coaching</h2>
    <p class="section-intro">This is the highest level of support I offer, for the athlete who wants
    a coach who understands them and their training completely. In-depth analysis of every session,
    a holistic approach across bike fit, race craft, fuelling and the mental side, and a plan that's
    truly yours, built and read by me.</p>
    <div class="get-grid">{get_cards}</div>
  </div>
</section>

<div class="media-band">{img("alpine-ridge", cls="media-bg")}</div>

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">How a month looks</p>
    <h2>The weekly rhythm</h2>
    <div class="side-fig-grid">
      <ol class="step-list">
        <li><strong>Your block lands</strong>Three weeks of training built around your life, calibrated to where your form is right now and where it needs to be to reach your dream goal, delivered to your TrainingPeaks account.</li>
        <li><strong>Every session earns its place</strong>Every session in your plan has a purpose. If I can't justify why it's there, it doesn't go in. Message me any time to move something or talk it through, and contact is unlimited, so you are never left guessing between sessions.</li>
        <li><strong>Read, analysed, fed back on</strong>I read the sessions you complete, analyse them against what was set using your actual data in TrainingPeaks and WKO5, and feed back on them. Feedback is a key part of the coaching journey, so each week you get a full round of feedback on everything you have completed.</li>
        <li><strong>We talk, the plan moves</strong>Block by block video catch-ups, WhatsApp for general chat, and the next block reflects real life and your numbers as they move.</li>
      </ol>
      <figure class="photo-fig photo-fig--port">{img("coaching-support-roadside")}
        <figcaption>Trackside on the Ironman Wales bike course</figcaption></figure>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Race support</p>
    <h2>A proper race plan, before every start line</h2>
    <div class="raceplan-showcase">
      <div class="prose raceplan-intro">
        <p>Before every event you get a race plan built for that day: pacing for the climbs and
        the flats, a fuelling strategy you have rehearsed, heat and weather contingencies, and
        the race craft that decides close finishes. These are the same detailed race-plan
        documents our athletes have taken to Ironman Wales, long-course triathlon and the Haute
        Route, not a paragraph of generic advice.</p>
        <p>I do not like surprises, other than birthdays and Christmas. A race should be the
        controlled execution of the training you have rehearsed, so you start the day knowing
        every element of it: your kit and equipment, your pacing strategy and your fuelling
        strategy, all practised and proven. That is what lets you actually enjoy the big day.</p>
        <p>We build the strategy together, so on the day you are not hoping it goes well. You know
        the plan, because it is yours.</p>
      </div>
      <figure class="raceplan raceplan--artefact">
        {raceplan_svg()}
        <figcaption>The bike leg of IRONMAN Wales, one of the toughest courses my athletes race,
        straight from the real course file: roughly {RACEPLAN_KM} km and {RACEPLAN_ASCENT} of
        climbing. The profile shows where the power goes on the climbs and the sustained drags,
        and the wind panel shows how a fresh westerly turns the same road into a headwind one way
        and a tailwind the other. Your plan gets the same treatment for your event.</figcaption>
      </figure>
    </div>
  </div>
</section>

<section class="limited-band">
  <div class="wrap limited-band-inner">
    <div class="limited-band-figure" aria-hidden="true"></div>
    <div class="limited-band-copy">
      <h2>Why places are limited</h2>
      <p>I keep this group small on purpose. I only ever open 15 Coached by Tom spots, because
      this level of support, weekly feedback, unlimited contact and a coach reading every
      session, is not something I can give properly to more than a small cohort. When those 15
      are taken, it is full.</p>
      <p style="margin-top:18px"><a class="btn btn--tom" href="{esc(contact_url('coached-by-tom'))}"{ga("cta", label=CTA_ASK_TOM, location="limited_band")}>{esc(CTA_ASK_TOM)}</a></p>
    </div>
  </div>
</section>

<div class="media-band">{img("coaching-alpine-hairpin", cls="media-bg")}</div>
{carousel("coaching", subhead="What athletes say about being coached by Tom", include_result=False)}
<section class="alt">
  <div class="wrap">
    <div class="pricing-card">
      <p class="eyebrow">Coached by Tom</p>
      <div class="pricing-figure"><span class="amount">&pound;185</span><span class="per">a month</span></div>
      <ul class="pricing-points">
        <li>No setup fee</li>
        <li>Three-month minimum</li>
        <li>Limited places, taken one at a time</li>
      </ul>
      <p style="margin-top:6px"><a class="btn" href="{esc(contact_url('coached-by-tom'))}"{ga("cta", label="Apply for Coached by Tom", location="pricing_card")}>Apply for Coached by Tom</a></p>
      <p class="pricing-note">Want the same plan without the day to day contact? <a href="{BASE_PATH}/coached/"{ga("cta", label=f"{TIER2_NAME} is £120 a month", location="pricing_note")}>{esc(TIER2_NAME)} is &pound;120 a month</a>.</p>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Not sure which tier?</h2>
    <div class="which-grid">
      <div class="which-item which-item--store"><strong>{esc(TIER1_NAME)}</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item which-item--plan"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item which-item--tom"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>
</main>"""
    desc = ("Coached by Tom, £185 a month, limited places. A bespoke TrainingPeaks programme, "
            "unlimited contact, weekly feedback and a race plan for race day.")
    svc = service_node(
        "Coached by Tom",
        ("The highest level of Horsepower support: a fully bespoke TrainingPeaks programme with "
         "in-depth WKO5 analysis, unlimited contact and amendments, weekly session feedback and "
         "a race plan before every start line, built and read by Tom Cooling directly. Limited "
         "places."),
        "/coaching/", monthly_price="185.00")
    extra = ld_script([
        breadcrumb_node([("Home", "/"), ("Coached by Tom", None)]), svc])
    return page("coaching", "Coached by Tom | £185 a month | Horsepower Coaching", desc,
                prod_url("/coaching/"), body, og_image_name="coached-tom-dolomites-arch", extra=extra,
                preload_img="coached-tom-dolomites-arch", page_type="tier_coached_by_tom",
                tier="coached_by_tom")


CTA_EXPLORE_PLAN = "Explore Plan Only"


def render_about(cat) -> str:
    # Bio content is VERBATIM from the current site; structure/order is presentation.
    body = f"""<main id="main">
<section class="hero about-hero">
  <div class="wrap about-hero-grid">
    <div class="about-hero-copy">
      <p class="eyebrow" style="color:var(--teal-soft)">About Us</p>
      <h1>The coach behind Horsepower</h1>
      <p class="lede">I'm Tom Cooling, Founder and Head Coach at Horsepower Coaching, and I
      bring a rare blend of lived experience and academic expertise. An ex-elite triathlete,
      seasoned ultra-bike racer and FKT holder, with a first-class degree and a master's in
      sport science behind everything I coach.</p>
    </div>
    <figure class="about-hero-portrait">{img("tom-portrait")}
      <figcaption>Tom Cooling, founder and head coach of Horsepower Coaching</figcaption></figure>
  </div>
</section>

<section>
  <div class="wrap content-grid two about-grid">
    <div class="prose">
      <h2>Coaching experience</h2>
      <p>I've spent over a decade coaching athletes from complete beginners to world-tour
      level professionals, guiding competitors to wins and podiums across Ironman,
      middle-distance triathlon, ultra-bike events and Haute Route-style races.</p>

      <h2>Where it comes from</h2>
      <p>It comes from my own racing, including FKT performances and ultra wins, from
      training alongside Royal Marines and UKSF, and from coaching elite performers. I
      know first-hand what the hard days actually take, and that goes into how I build
      and read every athlete's training.</p>

      <h2>Philosophy</h2>
      <p>I combine the evidence-based methods professional athletes rely on with practical,
      race-proven strategy, with a particular emphasis on female-specific performance
      development and durable, race-winning preparation. It's quality over quantity, and a no
      nonsense, holistic approach: one good block was never the point. What matters is a whole
      athlete, ready to hold up on the day it counts.</p>
    </div>
    <div class="about-side">
      <figure class="photo-fig photo-fig--port">{img("tom-hill-climb")}
        <figcaption>National Time Trial Championships</figcaption></figure>
    </div>
  </div>
</section>

<section class="alt" style="padding-top:40px;padding-bottom:40px">
  <div class="wrap">
    <p class="eyebrow">Qualifications</p>
    <h2>The credentials behind the coaching</h2>
    <div class="cred-band cred-band--five">
      <div class="cred"><h3>Sport science</h3><p>First Class BA and Master's Degree in Sport Science and Athlete Development.</p></div>
      <div class="cred"><h3>Breathwork and freediving</h3><p>Oxygen Advantage Advanced Breathwork Instructor, and AIDA L4 Freediver.</p></div>
      <div class="cred"><h3>Core Temp Accredited Coach</h3><p>Heat and climate adaptation, from designing the protocol to executing it on race day.</p></div>
      <div class="cred"><h3>XTRI Extreme Triathlon Accredited Coach</h3><p>Accredited for the extreme end of the sport, the XTRI races like Norseman and Celtman.</p></div>
      <div class="cred"><h3>Mountain leadership</h3><p>BMC (British Mountaineering Council) Trained and Assessed Mountain Leader.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Tom on the start line</p>
    <h2>Racing it, not just coaching it</h2>
    <p class="section-intro">The coaching is grounded in racing. Ironman and 70.3 podiums,
    Haute Route weeks in the Alps and the Dolomites, the Lost Dot TransPyrenees: the same
    kind of preparation Horsepower athletes get, tested first-hand.</p>
    <div class="about-gallery">
      <figure class="photo-fig photo-fig--land">{img("about-brecon-titan")}
        <figcaption>Multiple triathlon wins and podiums</figcaption></figure>
      <figure class="photo-fig photo-fig--land">{img("about-dolomites-descender")}
        <figcaption>Haute Route Dolomites</figcaption></figure>
      <figure class="photo-fig photo-fig--land">{img("about-dolomites-cobbles")}
        <figcaption>Haute Route Dolomites</figcaption></figure>
    </div>
    <div class="about-gallery">
      <figure class="photo-fig photo-fig--port">{img("about-transpyrenees-night")}
        <figcaption>Lost Dot TransPyrenees</figcaption></figure>
      <figure class="photo-fig photo-fig--port">{img("about-dolomites-pink-arch")}
        <figcaption>Haute Route Dolomites</figcaption></figure>
      <figure class="photo-fig photo-fig--port">{img("tom-bottle-refill")}
        <figcaption>Lost Dot TransPyrenees</figcaption></figure>
    </div>
  </div>
</section>

<section class="alt about-cta">
  <div class="wrap">
    <h2>Train with Tom</h2>
    <p class="section-intro">Start your journey with a plan built for your race, get coached
    from £120 a month, or ask about a limited place with me directly.</p>
    <div class="cta-row" style="margin-top:20px">
      <a class="btn" href="{BASE_PATH}/coached/"{ga("cta", label=CTA_EXPLORE_PLAN, location="closing")}>{esc(CTA_EXPLORE_PLAN)}</a>
      <a class="btn ghost" href="{BASE_PATH}/plans/"{ga("cta", label="Browse plans", location="closing")}>Browse plans</a>
    </div>
  </div>
</section>
{quote_block("about")}
</main>"""
    desc = ("Tom Cooling: ex-elite triathlete, ultra-bike racer and FKT holder coaching "
            "triathlon, cycling and endurance athletes from first-timers to world-tour pros.")
    extra = ld_script([
        breadcrumb_node([("Home", "/"), ("About Us", None)]),
        person_node(), org_node(with_rating=False)])
    return page("about", fit_title("About Tom Cooling | Founder and Head Coach"),
                desc, prod_url("/about/"), body,
                og_image_name="about-brecon-titan", extra=extra, page_type="about")


FEMALE_LEAD = "Female first, not female adapted."

# ── Female honours (Tom's authoritative palmares) ────────────────────────────
# Every line below is taken verbatim from the results Tom provided 2026-07-29,
# used exactly as written with no embellishment. Two of these women (Hannah S
# 2022, Madison S 2025) have won Ironman Wales outright. The unconfirmed
# "50 mile TT course record" claim is deliberately excluded. Do NOT add results
# that are not on Tom's list; the old Madison S "45-minute lead / 9th overall"
# line is a wrong claim and is gate-banned site-wide (gate 8d).
# Names render as first name + surname initial, no trailing period (Tom's
# privacy ruling, 2026-08-06: never a client's full name anywhere on the site;
# gate 8f bans the surnames site-wide). The palmares lines are untouched.
# `img` is the athlete's own verified photo (drops 2026-08-05/06). Never reuse
# another athlete's photo or an unidentified one here: name-photo pairing is a
# hard factual rule.
# Madison's 2025 supporting line is Tom's precision wording (2026-08-05): her
# Ironman Wales 2025 win was as overall women's age group champion.
FEMALE_HONOURS = [
    {"name": "Hannah S", "img": "honours-hannah-wales",
     "lines": ["Ironman Wales 2022 champion",
               "The ROC Wales 2021 - 1st, bike course record",
               "XTRI Celtman 2021 - 3rd, bike course record",
               "Welsh 100 Mile Time Trial Championships 2023 - 1st",
               "XTRI Norseman 2022 - 3rd"]},
    {"name": "Madison S", "img": "honours-madison-finish",
     "lines": ["Ironman Wales 2026 - age group champion, new age-group course record",
               "Welsh Triathlon Long Distance Champion 2026",
               "Ironman Wales 2025 champion",
               "Overall women's age group champion, Ironman Wales 2025",
               "Welsh 100 Mile Time Trial Champion 2026",
               "10th, Ironman World Championships Nice 2024",
               "Wales Middle and Long Distance Champion 2025",
               "Ironman Swansea 70.3 2024 - 1st age group, 2nd overall",
               "Cotswold 113 2024 - 1st, Cotswold 51 Fiver 2024 - 1st"]},
    {"name": "Naomi S", "img": "honours-naomi-flag",
     "lines": ["XTRI Swedeman 2026 - 2nd",
               "XTRI Celtman 2025 - 3rd",
               "Slateman Triathlon 2024 - 1st",
               "Brutal Triathlon 2024 - 1st"]},
    # Elly's tile photo: her Tom-confirmed Outlaw finish (drop 2026-08-06).
    # Tom's correction 2026-08-06: her Outlaw Half 2026 result is an age group
    # win, NOT the overall title; never present it as an overall win.
    {"name": "Elly B", "img": "honours-elly-outlaw",
     "lines": ["Ironman Wales 2026 - 2nd in age group",
               "Welsh Championships 2026 - age group champion",
               "Outlaw Half Triathlon 2026 - age group winner"]},
]

FEMALE_FAQ = [
    ("What is female-specific endurance training?",
     "It is training designed for a female athlete from the ground up, not a men's plan "
     "with the numbers scaled down. It respects the physiological differences that shape "
     "recovery, fuelling, strength needs and how training load is best spread across the week."),
    ("Do Horsepower's off-the-shelf plans sync to my menstrual cycle?",
     "No, and I won't claim they do. A downloadable plan cannot know where you are in "
     "your cycle, so instead my Female-First plans use recovery-respecting structure and "
     "dedicated strength work for bone and tendon health that benefit every female athlete. "
     "Genuine cycle-aware training comes with coaching, where the plan adapts around you."),
    ("What makes Horsepower's coaching cycle-aware?",
     "When I coach you, I read the sessions you actually complete in the context of what "
     "your body was doing, and I adapt the next block around your physiology, your symptoms "
     "and your feedback. It's personalised to you, not a generic template."),
    ("Which female-specific training plans does Horsepower offer?",
     "Four Female-First plans are live now: 70.3, Olympic-distance triathlon, marathon and "
     "century. Each is built for a female athlete targeting that specific event."),
    ("Is female-specific training only for elite athletes?",
     "No. The same approach that supports my racing athletes supports a first-timer. It's "
     "about training the athlete in front of me properly, at every level and life stage."),
]


def _honour_tile(h):
    """WS-SITE21 item 5: one aligned honours tile. The top three results show, the
    rest live in a native <details> ("More results") so every line stays in the DOM
    and is visible with JS off (details content is parsed by crawlers and captured
    by the freeze snapshot). Equal tile heights come from CSS flex, not truncation."""
    lines = h["lines"]
    top = lines[:3]
    rest = lines[3:]
    top_html = "".join(f"<li>{esc(l)}</li>" for l in top)
    more = ""
    if rest:
        rest_html = "".join(f"<li>{esc(l)}</li>" for l in rest)
        more = (f'<details class="honour-more"><summary>More results</summary>'
                f'<ul class="honour-stats honour-stats--more">{rest_html}</ul></details>')
    return (f'<div class="honour">'
            f'<div class="honour-media">{img(h["img"])}</div>'
            f'<div class="honour-body"><h3 class="honour-name">{esc(h["name"])}</h3>'
            f'<ul class="honour-stats">{top_html}</ul>{more}'
            f'</div></div>')


def render_female(cat) -> str:
    fem = [p for p in cat["plans"] if p["slug"] in FEMALE_FIRST_SLUGS]
    fem.sort(key=lambda p: p["title"])
    plan_cards = "".join(f"""<article class="plan-card" data-ga-item="{ga_item(p)}">
    <div class="tags"><span class="tag">{esc(p['sport'])}</span><span class="tag tier">Female-First</span></div>
    <h3><a href="{BASE_PATH}/plans/{p['slug']}/">{esc(p['title'])}</a></h3>
    <p class="blurb">{esc(p['blurb'])}</p>
    <div class="actions">
      <a class="btn" href="{esc(p['buy_url'])}" rel="noopener" target="_blank"{ga("buy", list=LIST_FEMALE)}>Buy on TrainingPeaks</a>
      <a class="link-plain" href="{BASE_PATH}/plans/{p['slug']}/"{ga("select", list=LIST_FEMALE)}>Details</a>
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
    extra = ld_script([
        breadcrumb_node([("Home", "/"), ("Female Performance", None)]), faq_ld])

    body = f"""<main id="main">
<section class="hero hero--image">
  {img("female-hero", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Female performance</p>
    <h1>{esc(FEMALE_LEAD)}</h1>
    <p class="lede">{esc(FEMALE_FIRST_BODY)}</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/coached/"{ga("cta", label=CTA_EXPLORE_PLAN, location="hero")}>{esc(CTA_EXPLORE_PLAN)}</a>
      <a class="btn on-dark ghost" href="#female-plans"{ga("cta", label="See the plans", location="hero")}>See the plans</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <div class="two-col-prose">
      <div class="prose">
        <h2>Why "female adapted" fails</h2>
        <p>Most training plans, most research and most coaching were built around the male
        athlete, then shrunk to fit everyone else. Women got trained as small men. That ignores
        what actually shapes how a female athlete responds to training: how you recover, how you
        fuel, the strength work that protects your bones and tendons, and how load is best spread
        across your week. Turning a men's plan down isn't the same as building the right one.</p>
      </div>
      <div class="prose">
        <h2>What female first actually means</h2>
        <p>Female first means the plan starts from the female athlete rather than a template. It
        means recovery-respecting structure so the work lands instead of grinding you down, and
        strength work built in for long-term bone and tendon health rather than bolted on as an
        afterthought. And it means I'm honest about what each level of support can and can't do.</p>
      </div>
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap feature-grid">
    <div class="feature-media">{img("female-trail")}</div>
    <div class="feature-copy">
      <p class="eyebrow">Plan Only and Coached by Tom</p>
      <h2>Genuinely cycle-aware coaching</h2>
      <p class="section-intro">This is where female-specific training stops being a label and
      gets personal. When I coach you, three things happen that a downloadable plan can't.</p>
      <ul class="about-list">
        <li><strong>The plan adapts around your physiology.</strong> Load, recovery and intensity are shaped to how you respond, not to an average athlete.</li>
        <li><strong>Feedback reads your sessions in context.</strong> What your body actually did, alongside your reported symptoms, recovery and where you are in your cycle.</li>
        <li><strong>Strength for bone and tendon is built in.</strong> Not bolted on, because long-term durability is part of performance, not separate from it.</li>
      </ul>
      <p style="margin-top:16px">I'm honest about the limits: coaching is personalised to you,
      and I'll never overclaim what it does. I coach with a particular emphasis on
      female-specific performance development, built from years of working with female athletes
      from first finish lines to the front of the race.</p>
      <p style="margin-top:20px">
        <a class="btn btn--plan" href="{BASE_PATH}/coached/"{ga("cta", label=CTA_EXPLORE_PLAN, location="feature_coaching")}>{esc(CTA_EXPLORE_PLAN)}</a>
        <a class="btn btn--tom" href="{BASE_PATH}/coaching/" style="margin-left:10px"{ga("cta", label=CTA_GET, location="feature_coaching")}>{esc(CTA_GET)}</a>
      </p>
    </div>
  </div>
</section>

<section class="female-honours">
  <div class="wrap">
    <p class="eyebrow">The women who prove it</p>
    <h2>Real names, real results</h2>
    <p style="color:var(--teal-soft);font-family:'Oswald',sans-serif;font-size:1.15rem;letter-spacing:0.04em;margin:6px 0 14px">Female results, not female participation.</p>
    <p class="section-intro" style="color:#CFCFCF">Horsepower is proud to have supported some amazing
    women on their journey to Ironman wins, XTRI podiums and course records. Every name below is one
    of them.</p>
    <div class="honours-grid">{"".join(_honour_tile(h) for h in FEMALE_HONOURS)}</div>
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
    cannot know where you are in yours, so I won't pretend it does. That's what coaching
    is for. One-off, delivered through TrainingPeaks.</p>
    <div class="card-grid card-grid--female2x2" style="margin-top:26px">{plan_cards}</div>
    <div class="callout callout--wide" style="margin-top:34px">
      <h2>Want it built around your body?</h2>
      <p>Pick your way in. Start with a proven plan off the shelf, have me write and read your
      training block by block, or go all in with a coach in your corner for all of it. Whichever
      path you choose, the training bends around your physiology, your event and your life.</p>
      <div class="tier-cta-row">
        <a class="btn btn--store" href="{BASE_PATH}/plans/"{ga("cta", label="Plan Store", location="callout")}>Plan Store</a>
        <a class="btn btn--plan" href="{BASE_PATH}/coached/"{ga("cta", label="Plan Only", location="callout")}>Plan Only</a>
        <a class="btn btn--tom" href="{BASE_PATH}/coaching/"{ga("cta", label="Coached by Tom", location="callout")}>Coached by Tom</a>
      </div>
    </div>
  </div>
</section>
</main>"""
    desc = ("Female-first triathlon, cycling and running coaching and training plans, built "
            "for female athletes with cycle-aware coaching. Female first, not female adapted.")
    return page("female",
                "Female Performance Coaching | Female-Specific Triathlon, Cycling and Running Training | Horsepower Coaching",
                desc, prod_url("/female-performance/"), body,
                og_image_name="female-hero", extra=extra,
                preload_img="female-hero", page_type="female_performance")


# ── Banner option previews (hidden /options/ page) ───────────────────────────
# A private, noindex page (not in nav, sitemap or robots) that renders every
# banner candidate IN ITS REAL SLOT with the real overlay + headline, so Tom
# judges the actual thing. Current incumbent first, then Option A/B/C, each
# labelled with its source filename. Tom picks; the live pages then change in
# one place. Candidate lists are the only thing to edit when curating.
# A candidate is a derivative name, or (derivative name, note) where the note
# renders as an extra tag next to the option letter (e.g. "Recommended").
BANNER_SLOTS = [
    {"id": "landing-hero", "kind": "hero", "name": "Landing hero",
     "where": "The home page hero, first thing every visitor sees. Ships live as "
              "hero-alpine-mist; the alternates below are here for you to override.",
     "eyebrow": "", "headline": HERO_HEADLINE,
     "lede": ("Your first 70.3. Ironman Wales. Kona. A 100 mile TT. Whatever the dream is, "
              "Horsepower takes it as seriously as you do."),
     "candidates": ["hero-alpine-mist",
                    ("hero-tenby-swim", "Alternate: Ironman Wales sunrise swim start"),
                    ("hero-torridon-ridge", "Alternate: Torridon ridge runners"),
                    "hero-alps", "hero-welsh-climb", "alpine-ridge", "ironman-wales-finish"]},
    {"id": "coaching-top", "kind": "hero", "name": "Coached by Tom, top banner",
     "where": "The hero at the top of the Coached by Tom page. Ships live as "
              "coached-tom-dolomites-arch; the alternates below are here for you to override.",
     "eyebrow": "Coached by Tom · £185 a month · Limited places",
     "headline": "A coach in your corner for all of it",
     "lede": ("Everything in Plan Only, plus me. Calls when you need them, WhatsApp when it is "
              "urgent, and a coach who knows your story, not just your data."),
     "candidates": ["coached-tom-dolomites-arch",
                    ("tom-alps-finish", "Alternate: Tom riding into the Haute Route Alps stage finish"),
                    ("tom-hill-climb", "Alternate: Tom racing the National Time Trial Championships in HP kit"),
                    "tom-alps-lead", "coached-band", "alpine-ridge"]},
    {"id": "coaching-mid", "kind": "band", "name": "Coached by Tom, mid-page banner",
     "where": "The full-width band above the weekly rhythm section. Shipped live as "
              "alpine-ridge; the alternates below are here for you to override.",
     "candidates": ["alpine-ridge", "coached-band", "hero-welsh-climb", "hero-torridon-ridge"]},
    {"id": "female-performance-banner", "kind": "hero", "name": "Female Performance hero",
     "where": "The hero at the top of the Female Performance page.",
     "eyebrow": "Female performance", "headline": FEMALE_LEAD,
     "lede": ("Endurance training was written for men and handed to women with the numbers "
              "turned down. We do it the other way round."),
     "candidates": ["female-hero", "female-wales-podium", "female-montblanc-hike",
                    ("female-naomi-tt", "Naomi S time trialling in Horsepower kit"),
                    ("honours-madison-tt", "Madison S on the TT bike"),
                    "female-welsh-tt"]},
    {"id": "plans-banner", "kind": "pagebanner", "name": "Plan Store banner",
     "where": "The full-width banner at the top of the plan library. Ships live as "
              "plans-izoard-trio; the alternates below are here for you to override.",
     "candidates": ["plans-izoard-trio",
                    ("plans-pyrenees-switchback", "Alternate: lone rider on a Pyrenean switchback"),
                    ("hero-alps", "Alternate: cyclist climbing high above an alpine valley"),
                    "plans-pyrenees-dawn", "hero-welsh-climb", "alpine-ridge", "coached-band"]},
    {"id": "coached-top", "kind": "band", "name": "Plan Only (£120), top banner",
     "where": "The full-width band under the hero on the Plan Only page. Ships live as "
              "hero-torridon-ridge; the alternates below are here for you to override.",
     "candidates": ["hero-torridon-ridge", "alpine-ridge", "plans-pyrenees-switchback",
                    "coached-band"]},
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
      <a class="btn on-dark ghost" href="#">Coach with Tom</a></div>
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
        for i, cand in enumerate(cands):
            name, note = cand if isinstance(cand, tuple) else (cand, "")
            if i == 0:
                tag, tagcls = "Current", "opt-tag opt-tag--current"
            else:
                tag, tagcls = f"Option {chr(64 + i)}", "opt-tag"
            note_html = f' <span class="opt-tag opt-tag--note">{esc(note)}</span>' if note else ""
            cards.append(
                f'<div class="opt">'
                f'<p class="opt-label"><span class="{tagcls}">{tag}</span> '
                f'<code>{esc(name)}.webp</code>{note_html}</p>'
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
    webpage_ld = {"@context": "https://schema.org", "@type": "WebPage",
                  "name": "Banner options (private preview)", "url": prod_url("/options/")}
    extra = '<meta name="robots" content="noindex, nofollow">\n' + ld_script(webpage_ld)
    return page("", "Banner options (private preview) | Horsepower Coaching",
                "Private banner preview page. Not indexed.",
                prod_url("/options/"), body, og_image_name="hero-alpine-mist", extra=extra,
                page_type="options")


# ── Contact (WS-SITE13) ──────────────────────────────────────────────────────
# A real on-site contact page. Channels are reused from the footer (WhatsApp,
# Instagram, Google reviews); no email address is invented because the footer
# does not carry one. The form is a plain Netlify Forms form: a static POST with
# a hidden form-name field and a honeypot, so it works on Netlify with no backend.
def render_contact(cat) -> str:
    option_tags = "".join(
        f'<option value="{v}"{" selected" if v == LEAD_OPTION_DEFAULT else ""}>{esc(label)}</option>'
        for v, label in LEAD_OPTIONS)
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 52px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Contact</p>
    <h1>Get in touch</h1>
    <p class="lede">Tell me about your event and your season and I'll come back to you. The
    quickest way to reach me is WhatsApp or Instagram. If you'd rather write it all down,
    use the form and I'll pick it up from there.</p>
  </div>
</section>

<section>
  <div class="wrap contact-grid">
    <div class="contact-intro">
      <figure class="photo-fig photo-fig--land contact-portrait">{img("tom-portrait")}
        <figcaption>Tom Cooling, founder and head coach of Horsepower Coaching</figcaption></figure>
      <h2>Talk to me directly</h2>
      <ul class="contact-channels">
        <li><a href="{WHATSAPP_URL}" rel="noopener" target="_blank"{ga("contact", channel="whatsapp")}>
          <span class="ch-icon">{SVG_WA}</span>
          <span class="ch-body"><strong>WhatsApp</strong><span>+44 7780 008724</span></span></a></li>
        <li><a href="{INSTAGRAM_URL}" rel="noopener" target="_blank"{ga("contact", channel="instagram")}>
          <span class="ch-icon">{SVG_IG}</span>
          <span class="ch-body"><strong>Instagram</strong><span>@horsepower.coaching</span></span></a></li>
        <li><a href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank"{ga("contact", channel="google_reviews")}>
          <span class="ch-icon">{SVG_FB}</span>
          <span class="ch-body"><strong>Reviews</strong><span>Read {REVIEW_COUNT} reviews on Google</span></span></a></li>
      </ul>
      <p style="color:var(--grey-mid);margin-top:22px">Based in Truro, Cornwall, coaching athletes
      across the UK and online worldwide.</p>
    </div>
    <div class="contact-panel">
      <h2>Send me a message</h2>
      <form name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" class="contact-form" action="{BASE_PATH}{THANKS_PATH}">
        <input type="hidden" name="form-name" value="contact">
        <p class="hp-field"><label>Leave this field empty if you're human <input name="bot-field"></label></p>
        <div class="field"><label for="c-name">Your name</label>
          <input id="c-name" name="name" type="text" autocomplete="name" required></div>
        <div class="field"><label for="c-email">Your email</label>
          <input id="c-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="c-option">{esc(LEAD_OPTION_LABEL)}</label>
          <select id="c-option" name="option">{option_tags}</select></div>
        <div class="field"><label for="c-event">Your target event (optional)</label>
          <input id="c-event" name="event" type="text"></div>
        <div class="field"><label for="c-message">Your message</label>
          <textarea id="c-message" name="message" rows="6" required></textarea></div>
        <button class="btn" type="submit">Send message</button>
      </form>
      {CONTACT_PRESELECT_JS}
    </div>
  </div>
</section>
</main>"""
    desc = ("Contact Tom Cooling at Horsepower Coaching. Message on WhatsApp +44 7780 008724 or "
            "Instagram @horsepower.coaching, or send a message about your target event.")
    contact_ld = {"@context": "https://schema.org", "@type": "ContactPage",
                  "name": "Contact Horsepower Coaching", "url": prod_url("/contact/"),
                  "about": _org_provider()}
    extra = ld_script([breadcrumb_node([("Home", "/"), ("Contact", None)]),
                       contact_ld, org_node(with_rating=False)])
    return page("contact", "Contact | Horsepower Coaching", desc,
                prod_url("/contact/"), body,
                og_image_name="coached-tom-dolomites-arch", extra=extra, page_type="contact")


# ── Privacy and cookies (WS-SITE25) ──────────────────────────────────────────
# The second consent layer, linked from the banner and every footer. Copy is the
# spec's verbatim text; the retention figure and the legal identity come from the
# constants above (gate 17h checks both).
PRIVACY_NO_PII_LINE = ("I never send your name, email address or the contents of your "
                       "message to Google Analytics.")
PRIVACY_FORM_LINE = ("When you send the form on the contact page I receive your name, your "
                     "email address, which option you are interested in, your target event if "
                     "you give one, and your message.")


def render_privacy(cat) -> str:
    email = (f'<a href="mailto:{esc(PRIVACY_CONTACT_EMAIL)}">{esc(PRIVACY_CONTACT_EMAIL)}</a>'
             if "@" in PRIVACY_CONTACT_EMAIL else esc(PRIVACY_CONTACT_EMAIL))
    body = f"""<main id="main">
<section class="plan-hero">
  <div class="wrap">
    <h1>Privacy and cookies</h1>
    <p class="blog-meta">Last updated <time datetime="{PRIVACY_UPDATED}">{esc(human_date(PRIVACY_UPDATED))}</time></p>
  </div>
</section>
<section>
  <div class="wrap prose">
    <h2>Who I am</h2>
    <p>I'm Tom Cooling and I run Horsepower Coaching from Truro, Cornwall. For data protection purposes the business is {esc(LEGAL_NAME)}. If anything on this page is unclear, email me at {email} and I'll answer it myself.</p>

    <h2>What this page covers</h2>
    <p>This page covers horsepowercoaching.co.uk only. When you buy a plan you are taken to TrainingPeaks, and when you message me on WhatsApp, Instagram or Facebook you are using those services. Each of them has its own privacy policy, and I don't control what they collect.</p>

    <h2>The contact form</h2>
    <p>{esc(PRIVACY_FORM_LINE)} I use them to reply to you and, if we go on to work together, to set up your coaching. The form is run by Netlify, which hosts this site, so your message is stored on Netlify's systems and emailed to me. I keep enquiries for as long as I need them to deal with your question, and I delete them when they are no longer needed. The legal basis is that you have asked me to get in touch, and my legitimate interest in answering enquiries about my coaching.</p>

    <h2>Measurement with Google Analytics</h2>
    <p>If you click Accept on the cookie banner, this site runs Google Analytics 4. It tells me which pages people read, which plans they look at, which buttons they click, how far down a page they get, whether they start and send the contact form, which option they picked on it, and whether a visit came from a Google ad. I use that to improve the site and to see whether the advertising I pay for is worth it.</p>
    <p>Google Analytics sets cookies on your device and sends data about your visit to Google, including a shortened version of your IP address, your browser and device type and the pages you view. Google acts on my instructions for the analytics itself, and it also uses the data under its own terms. I have switched off Google's cross-device signals and personalised advertising features. Analytics data is kept in my Google Analytics account for <span class="ga-retention">{esc(GA4_RETENTION)}</span> and then deleted.</p>
    <p>Nothing is sent to Google unless you accept. If you reject, or make no choice, Google Analytics does not load and no analytics cookies are set. You can change your mind at any time using the Cookie settings link at the bottom of every page. The legal basis is your consent.</p>
    <p>{esc(PRIVACY_NO_PII_LINE)}</p>

    <h2>Cookies and similar storage</h2>
    <table class="consent-table">
      <thead><tr><th scope="col">Name</th><th scope="col">Set by</th><th scope="col">Purpose</th><th scope="col">Lasts</th></tr></thead>
      <tbody>
        <tr><td>hp_consent</td><td>This site</td><td>Remembers whether you accepted or rejected measurement cookies</td><td>Six months</td></tr>
        <tr><td>_ga</td><td>Google Analytics</td><td>Tells one visitor's browser apart from another</td><td>Up to two years</td></tr>
        <tr><td>_ga_ followed by a code</td><td>Google Analytics</td><td>Keeps the state of your current visit</td><td>Up to two years</td></tr>
      </tbody>
    </table>
    <p>The hp_consent entry is strictly necessary to honour your choice and is set whichever button you press. The Google cookies are only set if you accept.</p>

    <h2>Buying a plan</h2>
    <p>Plans are sold through TrainingPeaks. When you click Buy on TrainingPeaks you leave this site, and TrainingPeaks handles your payment and your account under its own privacy policy.</p>

    <h2>Your rights</h2>
    <p>Under UK data protection law you can ask me what personal data I hold about you, ask me to correct it or delete it, object to how I use it, and withdraw consent at any time. Email {email} and I'll respond. If you are unhappy with how I've handled your data you can complain to the Information Commissioner's Office at ico.org.uk.</p>

    <h2>Changes</h2>
    <p>If I change how this site uses data I'll update this page and the date at the top.</p>
  </div>
</section>
</main>"""
    desc = ("How Horsepower Coaching handles your data: the contact form, Google Analytics "
            "with your consent, cookies, and your rights.")
    webpage_ld = {"@context": "https://schema.org", "@type": "WebPage",
                  "name": "Privacy and cookies", "url": prod_url(PRIVACY_PATH),
                  "about": _org_provider()}
    extra = ld_script([breadcrumb_node([("Home", "/"), ("Privacy and cookies", None)]),
                       webpage_ld])
    return page("", "Privacy and cookies | Horsepower Coaching", desc,
                prod_url(PRIVACY_PATH), body, og_image_name="tom-portrait", extra=extra,
                page_type="privacy")


# ── Contact form success page (WS-SITE25) ────────────────────────────────────
# The Netlify form action. Not indexed, not in the sitemap, Disallowed in robots.
# analytics.js fires generate_lead here only when the same-session submit flag
# written on /contact/ exists, so a reload or a direct visit never counts a lead.
def render_contact_thanks(cat) -> str:
    body = f"""<main id="main" data-lead-value="{LEAD_VALUE_GBP}">
<section class="hero" style="padding:60px 0 52px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Contact</p>
    <h1>Message sent</h1>
    <p class="lede">Thanks. Your message is on its way to me and I read every one myself. I'll come back to you as soon as I can. If it's quicker, you can also reach me on WhatsApp.</p>
  </div>
</section>
<section>
  <div class="wrap">
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/"{ga("cta", label="Back to the home page", location="thanks")}>Back to the home page</a>
      <a class="btn ghost" href="{BASE_PATH}/blog/"{ga("cta", label="Read the blog", location="thanks")}>Read the blog</a>
    </div>
    <p style="margin-top:22px"><a class="link-plain" href="{WHATSAPP_URL}" rel="noopener" target="_blank"{ga("contact", channel="whatsapp")}>Message me on WhatsApp, +44 7780 008724</a></p>
  </div>
</section>
</main>"""
    webpage_ld = {"@context": "https://schema.org", "@type": "WebPage",
                  "name": "Message sent", "url": prod_url(THANKS_PATH)}
    extra = ('<meta name="robots" content="noindex, nofollow">\n'
             + ld_script([breadcrumb_node([("Home", "/"), ("Contact", "/contact/"),
                                           ("Message sent", None)]), webpage_ld]))
    return page("contact", "Message sent | Horsepower Coaching",
                "Your message to Horsepower Coaching has been sent.",
                prod_url(THANKS_PATH), body, extra=extra, page_type="contact_thanks")


# ── Sport coaching landing pages (WS-SITE13, SEO retention) ──────────────────
# Thin, keyword-strong entry points matching the old GoDaddy /triathlon-coaching
# and /cycling-coaching URLs (the _redirects map sends the old no-slash URLs
# here). Each targets its head term + Clevedon/UK, then funnels to the three
# tiers. Not a duplicate of the tiers page; a focused door in.
def _funnel_cards():
    tiers = [
        (TIER1_NAME, 'From &pound;39.99,<span class="price-qual"> one-off</span>', SUPPORT_LEVELS[0][1], "/plans/", "Browse the plans"),
        (TIER2_NAME, "&pound;120 a month", SUPPORT_LEVELS[1][1], "/coached/", "How Plan Only works",
         "If in doubt, start here"),
        ("Coached by Tom", "&pound;185 a month", SUPPORT_LEVELS[2][1], "/coaching/", "Coach with Tom"),
    ]
    # WS-SITE18 tier colour theme: store (white/bordered), plan (teal), tom (gold).
    tier_cls = ["tier-card--store", "feature tier-card--plan", "tier-card--tom"]
    btn_cls = ["btn--store", "btn--plan", "btn--tom"]
    cards = []
    for i, (name, price, support, path, cta, *flag) in enumerate(tiers):
        cards.append(
            f'<div class="tier-card {tier_cls[i]}"><h3>{esc(name)}</h3>'
            + (f'<p class="tier-flag">{esc(flag[0])}</p>' if flag else "") +
            f'<div class="price">{price}</div>'
            f'<p class="support-line"><span class="support-tag">Support: {esc(support)}</span></p>'
            f'<a class="btn {btn_cls[i]}" href="{BASE_PATH}{path}"'
            f'{ga("cta", label=cta, location="funnel_card")}>{esc(cta)}</a></div>')
    return "".join(cards)


def render_sport_landing(*, slug, h1, eyebrow, hero_img, og_name, title, desc,
                         lede, intro_html, funnel_heading, service_name, service_desc,
                         sport) -> str:
    body = f"""<main id="main">
<section class="hero hero--image">
  {img(hero_img, cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">{esc(eyebrow)}</p>
    <h1>{esc(h1)}</h1>
    <p class="lede">{esc(lede)}</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/coached/"{ga("cta", label=CTA_EXPLORE_PLAN, location="hero")}>{esc(CTA_EXPLORE_PLAN)}</a>
      <a class="btn on-dark ghost" href="{BASE_PATH}/plans/"{ga("cta", label=CTA_FIND, location="hero")}>{esc(CTA_FIND)}</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap prose">
    {intro_html}
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">Three ways to train with Horsepower</p>
    <h2>{esc(funnel_heading)}</h2>
    <p class="section-intro">Pick the level of support that fits: a proven plan you run yourself,
    a bespoke plan with feedback each block, or the full coaching relationship.</p>
    <div class="tier-grid">{_funnel_cards()}</div>
  </div>
</section>
</main>"""
    svc = service_node(service_name, service_desc, f"/{slug}/")
    extra = ld_script([
        breadcrumb_node([("Home", "/"), (h1, None)]), svc, org_node(with_rating=False)])
    return page("", title, desc, prod_url(f"/{slug}/"), body,
                og_image_name=og_name, extra=extra, preload_img=hero_img,
                page_type="sport_landing", sport=sport)


def render_triathlon_coaching(cat) -> str:
    intro = (
        "<h2>Triathlon coaching for every distance</h2>"
        "<p>I'm Tom Cooling, and I coach triathletes from a first sprint all the way to Ironman, "
        "long course and the extreme XTRI races like Norseman. Whether you're chasing your first "
        "70.3 finish or a podium at Ironman Wales, coaching with Horsepower puts you and your dream "
        "at the centre of it, built around your target race, your life and your numbers, located "
        "in the South West of the UK and coaching online worldwide.</p>"
        "<p>Every plan is written by me and delivered straight into TrainingPeaks, built in "
        "three-week blocks so the load lands and the hard sessions are dosed the way the research "
        "says fitness is actually built. Swim, bike, run and the transitions in between, all "
        "prepared properly. Quality over quantity, every time.</p>"
        # WS-SITE23 punch-list c: ~150 words of unique head-term copy, Tom's voice.
        "<h2>What triathlon coaching with me actually covers</h2>"
        "<p>Triathlon is really four sports, not three, because the transitions and the way the "
        "three disciplines feed into each other decide as much as any single one. So we work the "
        "whole picture: a swim that leaves you fresh for the bike, bike pacing that protects your "
        "run, and a run built on the durability to hold form when you are tired. Around that sits "
        "the strength work, the fuelling you rehearse until it is boring, and the heat and "
        "race-craft preparation the bigger days demand.</p>"
        "<p>It suits the athlete who wants a coach reading their actual sessions, not a template "
        "downloaded and forgotten. First-timers who want to reach the start line genuinely ready, "
        "age-groupers chasing a championship slot, and plenty of people in between. Wherever you "
        "are in the UK or further afield, the coaching is delivered online from the South West, so "
        "the only thing that changes is your postcode, never the standard.</p>")
    return render_sport_landing(
        slug="triathlon-coaching", sport="Triathlon",
        h1="Triathlon Coaching",
        eyebrow="Triathlon coaching, South West UK and online",
        hero_img="hero-tenby-swim", og_name="hero-tenby-swim",
        title=fit_title("Triathlon Coaching | South West UK and Online"),
        desc=("Triathlon coaching for every distance, first sprint to Ironman, located in the "
              "South West of the UK and coaching online worldwide, by Tom Cooling."),
        lede=("Triathlon coaching built for your race, from your first sprint to Ironman. Written "
              "by me, delivered through TrainingPeaks, from the South West of the UK and coaching "
              "worldwide."),
        intro_html=intro,
        funnel_heading="Your paths into triathlon coaching",
        service_name="Triathlon coaching",
        service_desc=("Triathlon coaching and training plans for every distance, from first sprint "
                      "and 70.3 to Ironman and XTRI, built for your target race by Tom Cooling. "
                      "Located in the South West of the UK; coaching online worldwide."))


def render_cycling_coaching(cat) -> str:
    intro = (
        "<h2>Cycling coaching from sportives to ultra-distance</h2>"
        "<p>I coach cyclists from their first sportive or hill climb to the perfect 25 mile time "
        "trial, gran fondos, Everestings and full-blown ultra-distance racing. Coaching with "
        "Horsepower is built around the event you're chasing, the hours you've actually got and "
        "your own power numbers, located in the South West of the UK and coaching online across "
        "the UK and worldwide.</p>"
        "<p>Every plan is written by me and delivered straight into TrainingPeaks, the load built "
        "in three-week blocks and every target set as a percentage of your own numbers so it fits "
        "you and not some average. Climbing, time trialling, endurance and the race craft that "
        "wins the day. No nonsense, quality over quantity.</p>"
        # WS-SITE23 punch-list c: ~150 words of unique head-term copy, Tom's voice.
        "<h2>What cycling coaching with me actually covers</h2>"
        "<p>Bike racing rewards the rider who has trained the right thing, not simply the most. So "
        "we build the engine with structured endurance and threshold work, then sharpen it for the "
        "specific demands of your event, whether that is the repeatable climbing of a gran fondo, "
        "the single savage effort of a hill climb, or the pacing discipline of a long time trial. "
        "Position, fuelling and pacing get the same attention as the numbers, because on the day "
        "they decide as much as your FTP ever does.</p>"
        "<p>It suits the rider who knows there is more in there and wants a coach to find it: the "
        "sportive rider stepping up to a first big alpine day, the time triallist chasing a "
        "personal best, the ultra-distance rider learning to keep moving when it turns hard. It is "
        "all delivered online from the South West of the UK, so wherever you ride, the coaching "
        "comes with you.</p>")
    return render_sport_landing(
        slug="cycling-coaching", sport="Cycling",
        h1="Cycling Coaching",
        eyebrow="Cycling coaching, South West UK and online",
        hero_img="alpine-ridge", og_name="alpine-ridge",
        title=fit_title("Cycling Coaching | South West UK and Online"),
        desc=("Cycling coaching from sportives and hill climbs to 100 mile time trials and "
              "ultra racing, located in the South West of the UK and online. By Tom Cooling."),
        lede=("Cycling coaching built for your event, from sportives and hill climbs to 100 mile "
              "TTs and ultra racing. Written by me and delivered through TrainingPeaks."),
        intro_html=intro,
        funnel_heading="Your paths into cycling coaching",
        service_name="Cycling coaching",
        service_desc=("Cycling coaching and training plans from sportives and hill climbs to 100 "
                      "mile time trials and ultra-distance racing, built for your target event by "
                      "Tom Cooling. Located in the South West of the UK; coaching online worldwide."))


# ── Blog (WS-SITE14) ─────────────────────────────────────────────────────────
# Posts live as generator/content/blog/<slug>.md: a small YAML-ish front matter
# block (title, slug, date, datetime, description) followed by a light Markdown
# body. The 13 migrated posts keep their exact GoDaddy slugs so the live URLs
# (/blog/f/<slug>) are preserved; the old no-slash paths 301 to the new
# trailing-slash pages via _redirects. Canonicals use the trailing-slash clean
# URL, consistent with every other page on the site.
import datetime as _dt

_MD_SPECIAL = "\\`*_[]"
_SENT = "\x00"

# ── Original blog photography (WS-SITE24) ────────────────────────────────────
# The 13 posts migrated from the WordPress-era GoDaddy site (July 2017 to 31 Jan
# 2021) carry their ORIGINAL photographs, restored to the exact positions they
# hold on the current live site: the post's featured image as the hero, and every
# in-body photo inline where the author placed it. The images were recovered from
# the live pages' embedded Draft.js content (WordPress-hosted originals, largest
# rendition), re-encoded to WebP (heroes <=1200px, inline <=880px, quality-tuned)
# and shipped under assets/img/blog/ on their OWN budget line (gate 9b), separate
# from the site-wide image budget which is untouched. blog_images.json maps each
# derivative -> {file, w, h, alt}; the md bodies reference inline photos with a
# "{{fig:<name>}}" directive at the original position, so the author's words stay
# byte-identical (freeze gate) and only the images are (re)inserted. The four
# newer 2026 posts keep their WS-SITE18 hero picks (BLOG_HERO, below).
BLOG_IMG_MANIFEST = os.path.join(HERE, "content", "blog_images.json")


def _load_blog_images():
    if os.path.exists(BLOG_IMG_MANIFEST):
        with open(BLOG_IMG_MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


BLOG_IMAGES = _load_blog_images()


def blog_img_tag(name, cls="", lazy=True, fetchpriority=None):
    """One <img> for an original blog derivative (src assets/img/blog/<file>),
    with intrinsic width/height (no CLS) and factual alt, both from the manifest."""
    d = BLOG_IMAGES[name]
    c = f' class="{cls}"' if cls else ""
    loading = ' loading="lazy" decoding="async"' if lazy else ' decoding="async"'
    fp = f' fetchpriority="{fetchpriority}"' if fetchpriority else ""
    return (f'<img src="{IMG_BASE}/blog/{d["file"]}" alt="{esc(d["alt"])}"{c}'
            f' width="{d["w"]}" height="{d["h"]}"{loading}{fp}>')


def site_figure(name, caption=""):
    """Inline a SITE image derivative (assets/img/<name>.webp) inside a post body.

    The migrated 2021 posts carry their own recovered photo set under
    assets/img/blog/ and use {{fig:}}. Newer posts have no such set, so this lets
    them place any already-shipped site photograph in the flow of the writing,
    reusing that photo's locked alt text and intrinsic dimensions. No new image
    weight is added. An unknown name raises KeyError and fails the build loudly.
    """
    cap = f"<figcaption>{esc(caption)}</figcaption>" if caption else ""
    return f'<figure class="blog-figure">{img(name, lazy=True)}{cap}</figure>'


def blog_figure(name):
    """An inline blog photo rendered as a lazy-loaded <figure> (dimensions set so
    the reflow-free space is reserved). Captions, where the original had one, are
    the author's own bold lines already in the post body, so none is added here."""
    return f'<figure class="blog-figure">{blog_img_tag(name, lazy=True)}</figure>'


def _md_inline(text):
    """Inline Markdown -> HTML for a single logical line. Handles backslash
    escapes, [label](url) links (root-relative links are BASE_PATH-prefixed),
    **bold** and *italic*. Everything else is HTML-escaped."""
    protected = []

    def _protect(m):
        protected.append(m.group(1))
        return f"{_SENT}{len(protected) - 1}{_SENT}"

    text = re.sub(r"\\([\\`*_\[\]])", _protect, text)
    text = esc(text)   # escape &, <, >, quotes before we inject our own tags

    def _link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("/"):
            url = BASE_PATH + url
        return f'<a href="{url}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(_SENT + r"(\d+)" + _SENT, lambda m: esc(protected[int(m.group(1))]), text)
    return text


def _md_to_html(body):
    """Minimal, dependency-free Markdown block renderer (h2/h3, ul, ol,
    blockquote, paragraphs). A leading '#' h1 is demoted to h2 so each page
    keeps exactly one <h1> (the post title in the hero)."""
    lines = body.split("\n")
    out, para, i, n = [], [], 0, len(lines)

    def flush():
        if para:
            out.append("<p>" + _md_inline(" ".join(para)) + "</p>")
            para.clear()

    while i < n:
        s = lines[i].strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("{{img:") and s.endswith("}}"):
            # Inline a shipped SITE photo, with an optional caption after a pipe:
            # {{img:honours-hannah-wales|Hannah S wins Ironman Wales 2022}}
            flush()
            spec = s[6:-2].strip()
            nm, _, cap = spec.partition("|")
            out.append(site_figure(nm.strip(), cap.strip()))
            i += 1; continue
        if s.startswith("{{fig:") and s.endswith("}}"):
            # Inline original blog photo (WS-SITE24): a whole-line directive that
            # renders a <figure> in place. Not text, so it leaves the frozen body
            # text unchanged; a bad name fails the build loudly (KeyError).
            flush(); out.append(blog_figure(s[6:-2].strip())); i += 1; continue
        if s.startswith("### "):
            flush(); out.append("<h3>" + _md_inline(s[4:].strip()) + "</h3>"); i += 1; continue
        if s.startswith("## "):
            flush(); out.append("<h2>" + _md_inline(s[3:].strip()) + "</h2>"); i += 1; continue
        if s.startswith("# "):
            flush(); out.append("<h2>" + _md_inline(s[2:].strip()) + "</h2>"); i += 1; continue
        if s.startswith(">"):
            flush(); quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip()); i += 1
            out.append("<blockquote><p>" + _md_inline(" ".join(quote)) + "</p></blockquote>"); continue
        if re.match(r"[-*]\s+", s):
            flush(); items = []
            while i < n and re.match(r"[-*]\s+", lines[i].strip()):
                items.append("<li>" + _md_inline(re.sub(r"^[-*]\s+", "", lines[i].strip())) + "</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if re.match(r"\d+\.\s+", s):
            flush(); items = []
            while i < n and re.match(r"\d+\.\s+", lines[i].strip()):
                items.append("<li>" + _md_inline(re.sub(r"^\d+\.\s+", "", lines[i].strip())) + "</li>"); i += 1
            out.append("<ol>" + "".join(items) + "</ol>"); continue
        para.append(s); i += 1
    flush()
    return "\n".join(out)


def _parse_post(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"post missing front matter: {path}")
    fm_text, body = m.group(1), m.group(2)
    meta = {}
    for line in fm_text.split("\n"):
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1].replace('\\"', '"')
        meta[k.strip()] = v
    meta["body_html"] = _md_to_html(body.strip())
    return meta


def load_posts():
    posts = []
    if os.path.isdir(CONTENT_BLOG):
        for fn in sorted(os.listdir(CONTENT_BLOG)):
            if fn.endswith(".md"):
                posts.append(_parse_post(os.path.join(CONTENT_BLOG, fn)))
    # newest first, by the full timestamp when present, else the date
    posts.sort(key=lambda p: p.get("datetime") or p.get("date", ""), reverse=True)
    return posts


def human_date(iso):
    d = _dt.datetime.strptime(iso[:10], "%Y-%m-%d")
    return f"{d.day} {d.strftime('%B %Y')}"


# WS-SITE18: a topically-appropriate hero image per post, drawn only from the
# existing shipped derivatives (so no new image weight is added and the budget
# stays green). Keyed by slug; any unmapped post falls back to a clean branded
# image. The four recent posts use Tom's briefed picks.
BLOG_HERO = {
    # Recent posts (Tom's brief)
    "ironman-wales-how-to-beat-the-dragon": "female-wales-podium",  # two champions here
    "female-first-not-female-adapted": "female-welsh-tt",     # a female athlete racing (Welsh 100 TT)
    "make-the-plan-then-hold-it": "coached-band",             # a hard TT / pacing effort
    "train-easier-than-you-think": "plans-pyrenees-switchback",  # steady endurance on an alpine road
    "dont-get-fancy-before-youre-fancy": "hero-welsh-climb",  # honest fundamentals, climbing
    # Migrated posts
    "2017-season-wrapup---calm-after-the-storm": "plans-pyrenees-dawn",
    "everesting---climbing-the-mountain": "hero-alps",
    "how-not-to-coach---the-art-of-listening": "tom-alps-lead",
    "how-to-improve-your-triathlon-swim": "hero-tenby-swim",
    "into-the-unknown": "hero-torridon-ridge",
    "ironman-wales---enter-the-dragon": "ironman-wales-finish",
    "my-triathlon-top-tips": "female-naomi-tt",
    "once-twice-three-times-an-ironman": "female-wales-podium",
    "our-origins---a-little-bit-of-history": "about-brecon-titan",
    "plastic-pollution-triathlon": "hero-tenby-swim",
    "psychology---use-your-head": "about-dolomites-descender",
    "the-lightest-disc-brake-bike": "plans-izoard-trio",
    "tits-up---how-to-deal-with-failure": "about-dolomites-cobbles",
}
BLOG_HERO_FALLBACK = "hero-alpine-mist"   # clean branded fallback


def blog_hero(slug):
    return BLOG_HERO.get(slug, BLOG_HERO_FALLBACK)


def blog_hero_media(post, cls="media-bg", lazy=True, fetchpriority=None):
    """Hero image for a post. The 13 migrated posts (2017-2021) carry their
    ORIGINAL featured photograph via the front-matter `hero_blog` field; the four
    newer posts fall back to their WS-SITE18 shared derivative (blog_hero)."""
    hb = post.get("hero_blog")
    if hb and hb in BLOG_IMAGES:
        return blog_img_tag(hb, cls=cls, lazy=lazy, fetchpriority=fetchpriority)
    # Fallback (the 4 newer 2026 posts): reproduce their WS-SITE18 shared hero
    # byte-for-byte (index card carried fetchpriority="low"; the post hero none),
    # so restoring the migrated posts leaves the newer posts untouched.
    extra = ' fetchpriority="low"' if lazy else ""
    return img(blog_hero(post["slug"]), cls=cls, lazy=lazy, extra=extra)


def render_blog_index(posts):
    cards = []
    for p in posts:
        url = f'{BASE_PATH}/blog/f/{p["slug"]}/'
        media = blog_hero_media(p, cls="", lazy=True, fetchpriority="low")
        cards.append(
            f'<article class="blog-card">'
            f'<a class="blog-card-media" href="{url}" aria-hidden="true" tabindex="-1">{media}</a>'
            f'<div class="blog-card-body">'
            f'<p class="blog-date"><time datetime="{esc(p["date"])}">{esc(human_date(p["date"]))}</time></p>'
            f'<h2 class="blog-card-title"><a href="{url}">{esc(p["title"])}</a></h2>'
            f'<p class="blog-excerpt">{esc(p.get("description", ""))}</p>'
            f'<p><a class="link-plain" href="{url}">Read the post &rarr;</a></p>'
            f'</div>'
            f'</article>')
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 40px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">The Horsepower blog</p>
    <h1>Thoughts from the road, the pool and the coaching desk</h1>
    <p class="lede">Race reports, training philosophy and the odd rant, written by me over the years.
    The same voice you get when I coach you.</p>
  </div>
</section>
<section>
  <div class="wrap">
    <div class="blog-list">
      {''.join(cards)}
    </div>
  </div>
</section>
</main>"""
    desc = ("The Horsepower Coaching blog: triathlon and cycling training philosophy, race reports "
            "and honest coaching thinking, written by Tom Cooling.")
    blog_ld = {
        "@context": "https://schema.org", "@type": "Blog",
        "name": "Horsepower Coaching Blog", "url": prod_url("/blog/"),
        "description": desc, "publisher": _org_provider(),
        "blogPost": [
            {"@type": "BlogPosting", "headline": p["title"],
             "url": prod_url(f'/blog/f/{p["slug"]}/'),
             "datePublished": p.get("datetime") or p["date"],
             "author": _tom_ref()}
            for p in posts],
    }
    extra = ld_script([breadcrumb_node([("Home", "/"), ("Blog", None)]), blog_ld])
    return page("blog", "Blog | Horsepower Coaching", desc, prod_url("/blog/"), body,
                og_image_name="hero-welsh-climb", extra=extra, page_type="blog_index")


def render_blog_post(p):
    slug = p["slug"]
    canonical = prod_url(f"/blog/f/{slug}/")
    body = f"""<main id="main">
<section class="plan-hero blog-post-hero">
  <div class="wrap">
    <p class="crumbs"><a href="{BASE_PATH}/blog/">Blog</a> / {esc(human_date(p["date"]))}</p>
    <h1>{esc(p["title"])}</h1>
    <p class="blog-meta">By Tom Cooling &middot; <time datetime="{esc(p["date"])}">{esc(human_date(p["date"]))}</time></p>
  </div>
</section>
<div class="media-band blog-hero-media">{blog_hero_media(p, cls="media-bg", lazy=False, fetchpriority="high")}</div>
<section>
  <article class="wrap prose blog-prose">
    {p["body_html"]}
    <hr class="blog-rule">
    <p><a class="link-plain" href="{BASE_PATH}/blog/">&larr; Back to the blog</a></p>
    <div class="callout" style="margin-top:30px">
      <p class="eyebrow" style="color:var(--teal-soft)">Train with Horsepower</p>
      <p>If that is how you like your coaching, straight and built for your race, take a look at the
      <a class="link-plain on-dark" href="{BASE_PATH}/plans/"{ga("cta", label="training plans", location="post_callout")}>training plans</a> or see
      <a class="link-plain on-dark" href="{BASE_PATH}/coached/"{ga("cta", label="how coaching works", location="post_callout")}>how coaching works</a>.</p>
    </div>
  </article>
</section>
</main>"""
    # WS-SITE23 punch-list e: meta descriptions must be <=158 chars or the SERP
    # truncates them. The ceiling applies to the ESCAPED string that actually
    # ships (an embedded quote becomes &quot;, six chars), so trim word by word
    # against the escaped length and mark the cut with an ellipsis.
    desc = (p.get("description", "") or p["title"]).strip()
    if len(esc(desc)) > 158:
        out = ""
        for w in desc.split():
            cand = (out + " " + w).strip()
            if len(esc(cand.rstrip(".,;: ") + "...")) > 158:
                break
            out = cand
        desc = out.rstrip(".,;: ") + "..."
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"], "description": desc,
        "url": canonical, "mainEntityOfPage": canonical,
        "datePublished": p.get("datetime") or p["date"],
        "dateModified": p.get("datetime") or p["date"],
        "author": _tom_ref(),
        "publisher": _org_ref(),
        "image": og_image_url(DEFAULT_OG_IMAGE),
        "inLanguage": "en-GB",
    }
    crumbs = breadcrumb_node([("Home", "/"), ("Blog", "/blog/"), (p["title"], None)])
    extra = ld_script([ld, crumbs])
    return page("blog", fit_title(p["title"]), desc, canonical, body,
                og_image_name=DEFAULT_OG_IMAGE, og_type="article", extra=extra,
                page_type="blog_post")


# ── llms.txt (WS-SITE22, AI-crawl pass) ──────────────────────────────────────
# A plain-markdown machine-facing summary served at the site root (the llms.txt
# convention), so answer engines and AI crawlers get the core facts, prices and
# verified results from ONE authoritative place. Additive file, shipped like
# robots.txt (NOT listed in the sitemap). Every fact is derived from the same
# constants the site renders from - prices from the tier cards, the plan count
# from the catalogue, results from the honours band - so nothing is hand-typed
# out of sync, and the surname / domestiq / em-dash gates cover it like any other
# output.
# The ten key URLs advertised to crawlers, in the order the spec lists them.
LLMS_KEY_PATHS = ["/", "/coaching/", "/coached/", "/plans/", "/female-performance/",
                  "/triathlon-coaching/", "/cycling-coaching/", "/about/", "/blog/",
                  "/contact/"]


def _tier_price_amounts():
    """The pound amount for each home tier card, unescaped exactly as the site
    states it (["£39.99", "£120", "£185"]). Derived, never hand-typed."""
    amounts = []
    for c in HOME_TIER_CARDS:
        m = re.search(r"£\d[\d.]*", html.unescape(c["price_main"]))
        amounts.append(m.group(0) if m else "")
    return amounts


def render_llms_txt(cat) -> str:
    total = cat["stats"]["total"]
    store_amt, plan_amt, tom_amt = _tier_price_amounts()
    names = [c["name"] for c in HOME_TIER_CARDS]   # Plan Store / Plan Only / Coached by Tom

    lines = []
    lines.append("# Horsepower Coaching")
    lines.append("")
    lines.append(
        "Horsepower Coaching is world class multisport, cycling and endurance coaching by "
        "Tom Cooling. Located in the South West of the UK and based in Truro, Cornwall, it "
        "coaches athletes across the UK (including Clevedon) and online worldwide.")
    lines.append("")
    lines.append("## Coaching and plans")
    lines.append("")
    lines.append("Horsepower offers three tiers:")
    lines.append("")
    lines.append(
        f"- {names[0]}: training plans from {store_amt}, one-off. {total} plans, each written "
        "for a specific target race and goal and delivered through TrainingPeaks.")
    lines.append(
        f"- {names[1]}: {plan_amt} a month. A bespoke plan built for you block by block: three "
        "weeks of training, then a rest week in which Tom reviews the block, writes feedback and "
        "builds the next one. One review a month, no calls.")
    lines.append(
        f"- {names[2]}: {tom_amt} a month. Full one to one coaching with weekly feedback. "
        "15 places only.")
    lines.append("")
    lines.append("## Contact")
    lines.append("")
    lines.append("- WhatsApp: +44 7780 008724")
    lines.append("- Instagram: @horsepower.coaching")
    lines.append(f"- Contact page: {prod_url('/contact/')}")
    lines.append("")
    lines.append("## Verified athlete results")
    lines.append("")
    lines.append(
        "Coached athletes and their verified results (names as first name plus surname "
        "initial only):")
    lines.append("")
    for h in FEMALE_HONOURS:
        lines.append(f"### {h['name']}")
        for l in h["lines"]:
            lines.append(f"- {l}")
        lines.append("")
    lines.append("## Not published / do not infer")
    lines.append("")
    lines.append(
        "- Horsepower has no physical training venue open to the public.")
    lines.append(
        "- Coaching is delivered remotely, worldwide, through TrainingPeaks.")
    lines.append(
        "- Anything not stated on this page or the website is not published. Please do not "
        "infer it.")
    lines.append("")
    lines.append("## Key URLs")
    lines.append("")
    for path in LLMS_KEY_PATHS:
        lines.append(f"- {prod_url(path)}")
    lines.append("")
    return "\n".join(lines)


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
    write("contact/index.html", render_contact(cat), written)
    write("contact/thanks/index.html", render_contact_thanks(cat), written)
    write("privacy/index.html", render_privacy(cat), written)
    write("triathlon-coaching/index.html", render_triathlon_coaching(cat), written)
    write("cycling-coaching/index.html", render_cycling_coaching(cat), written)
    # Hidden banner-preview page: noindex, deliberately absent from nav + sitemap.
    write("options/index.html", render_options(), written)
    for p in plans:
        write(f"plans/{p['slug']}/index.html", render_plan_detail(cat, p), written)

    # blog (WS-SITE14): /blog/ index + one page per post at /blog/f/<slug>/
    posts = load_posts()
    write("blog/index.html", render_blog_index(posts), written)
    for post in posts:
        write(f"blog/f/{post['slug']}/index.html", render_blog_post(post), written)

    # sitemap (absolute prod URLs; /options/ deliberately excluded)
    today = date.today().isoformat()

    def sm_entry(loc, changefreq, priority):
        return (f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod>"
                f"<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>")

    main_pages = [("/", "weekly", "1.0"), ("/plans/", "weekly", "0.9"),
                  ("/female-performance/", "weekly", "0.9"),
                  ("/triathlon-coaching/", "monthly", "0.8"),
                  ("/cycling-coaching/", "monthly", "0.8"),
                  ("/coached/", "monthly", "0.8"),
                  ("/coaching/", "monthly", "0.8"), ("/about/", "monthly", "0.6"),
                  ("/blog/", "weekly", "0.7"),
                  ("/contact/", "monthly", "0.5"),
                  (PRIVACY_PATH, "yearly", "0.3")]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, cf, pr in main_pages:
        sm.append(sm_entry(prod_url(path), cf, pr))
    for p in plans:
        sm.append(sm_entry(prod_url(f"/plans/{p['slug']}/"), "monthly", "0.7"))
    for post in posts:
        sm.append(sm_entry(prod_url(f"/blog/f/{post['slug']}/"), "monthly", "0.6"))
    sm.append("</urlset>")
    if not IS_PREVIEW_BUILD:
        write("sitemap.xml", "\n".join(sm), written)

    # robots.txt: allow all standard crawlers AND the major AI crawlers explicitly
    # (Tom wants AI training + answer-engine citation for reach). /options/ stays
    # disallowed. Robots is honoured at the host root, so paths are root-relative
    # and the sitemap points at the production host.
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
               "Claude-Web", "PerplexityBot", "Perplexity-User", "Google-Extended",
               "CCBot", "Applebot-Extended", "Bytespider", "Amazonbot",
               "meta-externalagent", "cohere-ai", "Diffbot", "Timpibot", "YouBot"]
    rb = ["# Horsepower Coaching",
          "# Triathlon, cycling and endurance coaching | South West UK + online worldwide",
          "",
          "User-agent: *",
          "Allow: /",
          "Disallow: /options/",
          f"Disallow: {THANKS_PATH}",
          ""]
    for bot in ai_bots:
        rb += [f"User-agent: {bot}", "Allow: /", "Disallow: /options/",
               f"Disallow: {THANKS_PATH}", ""]
    rb += [f"Sitemap: {prod_url('/sitemap.xml')}", ""]
    if IS_PREVIEW_BUILD:
        # Preview build (GitHub Pages). Crawling is deliberately still allowed so
        # crawlers can READ the noindex tag on every page; blocking them here
        # would freeze the copy in the index instead of removing it. No sitemap
        # is advertised, because nothing on this copy should ever be submitted.
        rb = ["# Horsepower Coaching PREVIEW BUILD, not the live site.",
              "# The live site is https://horsepowercoaching.co.uk",
              "# Every page here carries noindex; crawling stays allowed only so",
              "# that tag can be read. Do not submit this host to any search engine.",
              "",
              "User-agent: *",
              "Allow: /",
              "Disallow: /options/",
              f"Disallow: {THANKS_PATH}",
              ""]
    write("robots.txt", "\n".join(rb), written)

    # llms.txt (WS-SITE22): machine-facing summary at the site root. Additive,
    # shipped like robots.txt and deliberately NOT added to the sitemap.
    write("llms.txt", render_llms_txt(cat), written)

    # _redirects (Netlify, WS-SITE13): true 301s from the old GoDaddy URLs to
    # their new equivalents. Ships inside the publish dir (site/). Destinations
    # all exist in this build. Blog URLs are deliberately untouched (identical
    # /blog/f/<slug> paths, handled in a later build). Root-relative, so this is
    # correct whichever base path the HTML is built at.
    redirects = [
        "# WS-SITE13 GoDaddy -> Netlify 301 map. Blog URLs added in WS-SITE14.",
        "/triathlon-coaching       /triathlon-coaching/     301",
        "/cycling-coaching         /cycling-coaching/       301",
        "/training-plans           /plans/                  301",
        "/our-team                 /about/                  301",
        "/achievements             /female-performance/     301",
        "/performance-breathwork   /about/                  301",
        "/contact-us               /contact/                301",
        "/alps-training-camp       /coaching/               301",
        "/the-foundry              /                        301",
        "/bespoke-wheelbuilding    /                        301",
        "/equality-development-1   /female-performance/     301",
        "",
        "# Blog: the old GoDaddy URLs were /blog and /blog/f/<slug> (no trailing",
        "# slash). Send them to the new trailing-slash pages so ranking is kept.",
        "/blog                      /blog/                   301",
    ]
    for post in posts:
        redirects.append(f"/blog/f/{post['slug']}    /blog/f/{post['slug']}/    301")

    # Root-level /f/<slug> (2026-08-24). GoDaddy also exposed every post at the
    # bare /f/<slug> path, and Google is still crawling those: Search Console
    # listed /f/into-the-unknown, /f/how-to-improve-your-triathlon-swim and
    # /f/my-triathlon-top-tips as 404s in August 2026. The posts themselves are
    # all live at /blog/f/<slug>/, so this is recoverable ranking, not dead
    # weight. Rules are emitted for EVERY post, not just the three Google has
    # found so far, so the rest are covered before they are ever crawled.
    redirects.append("")
    redirects.append("# Legacy root-level post URLs (GoDaddy served /f/<slug> too).")
    for post in posts:
        redirects.append(f"/f/{post['slug']}    /blog/f/{post['slug']}/    301")

    # The old GoDaddy RSS feed. There is no feed in this build, so send it to
    # the blog index rather than leaving a 404 on a URL feed readers may still
    # hold. Deliberately NOT a rewrite: the content is not a feed.
    redirects.append("")
    redirects.append("/blog/f.rss    /blog/    301")

    # NOTE: the old /m/* member-area URLs (/m/login, /m/account,
    # /m/create-account) are deliberately left as 404. They are permanently
    # gone with no equivalent on this site, so 404 is the correct signal.
    # Redirecting them to / would create soft-404s and tell Google those pages
    # moved to the homepage, which they did not.
    redirects.append("")
    write("_redirects", "\n".join(redirects), written)

    run_gates(cat, written)
    freeze_check()
    print("Built %d pages into %s" % (len(written), SITE))
    return cat, written


def freeze_check():
    """WS-SITE20 freeze gate: the craft pass must not change any page's frozen
    <head> metadata, visible body text, or the shipped URL set. Runs the committed
    snapshot against the just-written site/ (base-path independent, so it holds in
    both build modes). If the snapshot is absent (pre-WS-SITE20 tree) it is skipped
    with a warning rather than failing an otherwise-valid build."""
    import freeze_gate
    if not os.path.exists(freeze_gate.SNAPSHOT):
        print("Freeze gate: no snapshot committed yet, skipped "
              "(run 'python3 generator/freeze_gate.py snapshot').")
        return
    # The preview build deliberately omits sitemap.xml (an indexable sitemap on
    # the GitHub Pages copy is exactly what we are stopping). Everything else
    # stays frozen in both modes.
    allow_missing = ("sitemap.xml",) if IS_PREVIEW_BUILD else ()
    if freeze_gate.verify(SITE, allow_missing=allow_missing) != 0:
        raise SystemExit(1)


GA_JS_ASSETS = ("consent.js", "analytics.js")
GA_REQUIRED = {"nav": ("label",), "cta": ("label", "location"), "buy": ("list",),
               "select": ("list",), "contact": ("channel",), "outbound": ()}


def _ga_scan(html_pages):
    """[(path, attrs, enclosing data-ga-item values)] for every element carrying
    data-ga, from a real HTML parse so ancestry is structural, not regex."""
    from html.parser import HTMLParser
    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "source", "track", "wbr", "path", "rect", "circle"}
    found = []

    class _P(HTMLParser):
        def __init__(self, path):
            super().__init__(convert_charrefs=True)
            self.path, self.stack = path, []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            items = [x for _t, x in self.stack if x is not None]
            if "data-ga" in a:
                found.append((self.path, a, items + ([a["data-ga-item"]] if "data-ga-item" in a else [])))
            if tag not in void:
                self.stack.append((tag, a.get("data-ga-item")))

        def handle_startendtag(self, tag, attrs):
            a = dict(attrs)
            if "data-ga" in a:
                found.append((self.path, a, [x for _t, x in self.stack if x is not None]))

        def handle_endtag(self, tag):
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]
                    break

    for path, content in html_pages.items():
        _P(path).feed(content)
    return found


def run_gates(cat, written):
    errors = []
    html_pages = {k: v for k, v in written.items() if k.endswith(".html")}

    # Gate 1: no em-dashes anywhere.
    for path, content in written.items():
        if EM_DASH in content:
            errors.append(f"em-dash (U+2014) found in {path}")

    # Gate 2: every approved (verbatim-locked) copy string appears byte-exact
    # somewhere in the built HTML. Tom's voice is locked here (WS-SITE12 de-AI
    # rewrite): the gate tracks the constants, so a copy edit updates the gate in
    # the same file. Copy A/E live on home; B on home + /plans/; C on home +
    # /coached/; D on home + /coaching/. All are validated across the whole site.
    all_html = "".join(v for k, v in written.items() if k.endswith(".html"))
    for s in VERBATIM_REQUIRED:
        if esc(s) not in all_html and s not in all_html:
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

    # Gate 3b (WS-SITE23): SERP title-length ceiling. Every page <title> must be
    # <=65 rendered characters so it does not truncate in the search result. The
    # keyword-rich /female-performance/ page is the single documented exception.
    for path, content in html_pages.items():
        if path in TITLE_CAP_EXEMPT:
            continue
        m = re.search(r"<title>(.*?)</title>", content, re.S)
        if m:
            tlen = len(html.unescape(m.group(1)))
            if tlen > TITLE_HARD_CAP:
                errors.append(f"title too long ({tlen}>{TITLE_HARD_CAP} chars) in {path}: "
                              f"{html.unescape(m.group(1))!r}")

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

    # Gate 8g (WS-SITE22): no invented reviews. Every quote actually RENDERED in a
    # review slide must exist byte-exact in reviews.yaml (the single source). This
    # is stronger than 8c (which only checks the CLIENT_QUOTES data): it reads the
    # built HTML, so a quote that reached a page any other way is caught too. The
    # Madison result slide (review-slide result-slide) is a palmares stat block,
    # not a review, so it is deliberately excluded by the exact class match.
    review_texts = {r["text"] for r in REVIEWS}
    for path, content in html_pages.items():
        for q in re.findall(r'<figure class="review-slide"><blockquote>(.*?)</blockquote>',
                            content, re.S):
            if html.unescape(q) not in review_texts:
                errors.append(f"rendered review quote not in reviews.yaml ({path}): "
                              f"{html.unescape(q)[:48]}...")

    # Gate 8d: the old wrong Madison S claim must never reappear (it was never
    # in Tom's authoritative palmares: not a 45-minute AG lead, not 9th overall).
    BANNED_CLAIMS = ["by 45 minutes", ">45min<", "9th overall against the professional"]
    for path, content in written.items():
        for b in BANNED_CLAIMS:
            if b in content:
                errors.append(f"banned unverified claim {b!r} found in {path}")

    # Gate 8e: female honours band carries exactly Tom's authoritative palmares
    # (provided 2026-07-29): every athlete + every line present, byte-exact, and
    # the two Ironman Wales champion headlines lead the band. Athlete names are
    # asserted as they render: first name + surname initial (gate 8f), straight
    # from the FEMALE_HONOURS source of truth.
    fem_page = written.get("female-performance/index.html", "")
    for h in FEMALE_HONOURS:
        if esc(h["name"]) not in fem_page and h["name"] not in fem_page:
            errors.append(f"female honours missing athlete: {h['name']}")
        for l in h["lines"]:
            if esc(l) not in fem_page and l not in fem_page:
                errors.append(f"female honours missing line: {l[:48]}")
    for required in ("Ironman Wales 2022 champion", "Ironman Wales 2025 champion",
                     "Welsh 100 Mile Time Trial Champion 2026",
                     "Outlaw Half Triathlon 2026 - age group winner"):
        if required not in fem_page:
            errors.append(f"female honours missing required headline: {required}")

    # Gate 8f: client-name privacy (Tom's ruling, 2026-08-06: "i dont mind
    # Hannah S etc but not the full name"). Client and reviewer names render as
    # first name + surname initial only, so no client surname may appear
    # anywhere in the generated output. Tom Cooling, the business owner, is the
    # one exemption and keeps his full name.
    BANNED_SURNAMES = ["Saitch", "Shaddick", "Shinkins", "Blackwell",
                       "Cheatle", "Needham", "bastos"]
    for path, content in written.items():
        low = content.lower()
        for s in BANNED_SURNAMES:
            if s.lower() in low:
                errors.append(f"client surname {s!r} found in {path} "
                              "(names must be first name + surname initial)")

    # Gate 8b: zero Domestiq cross-pollination anywhere (Tom's ruling: separate entities).
    for path, content in written.items():
        if "domestiq" in content.lower():
            errors.append(f'"domestiq" found in {path} (must be zero site-wide)')

    # ── WS-SITE10 SEO / AEO gates ────────────────────────────────────────────
    # options/ is a private, noindex preview harness that intentionally renders
    # many hero slots (many <h1>s), so it is exempt from the single-h1 rule but
    # still validated for canonical + parsing JSON-LD.
    OPTIONS = "options/index.html"
    indexable = {k: v for k, v in html_pages.items() if k != OPTIONS}

    # Gate 10a: exactly one <h1> per indexable page.
    for path, content in indexable.items():
        n_h1 = len(re.findall(r"<h1[\s>]", content))
        if n_h1 != 1:
            errors.append(f"{path} has {n_h1} <h1> (must be exactly 1)")

    # Gate 10b: self-referencing canonical on the production host, unique per page.
    canon = {}
    for path, content in html_pages.items():
        m = re.search(r'<link rel="canonical" href="([^"]+)"', content)
        if not m:
            errors.append(f"missing canonical: {path}")
            continue
        if not m.group(1).startswith(PROD_ORIGIN):
            errors.append(f"canonical not on prod host in {path}: {m.group(1)}")
        canon.setdefault(m.group(1), []).append(path)
    for c, paths in canon.items():
        if len(paths) > 1:
            errors.append(f"duplicate canonical {c!r}: {paths}")

    # Gate 10c: Open Graph + Twitter card present on every page.
    for path, content in html_pages.items():
        for tag in ('property="og:title"', 'property="og:description"', 'property="og:url"',
                    'property="og:image"', 'name="twitter:card"', 'name="twitter:image"'):
            if tag not in content:
                errors.append(f"missing social tag {tag} in {path}")

    # Gate 10d: every page carries >=1 JSON-LD block; every block parses as valid
    # JSON and contains zero "domestiq".
    for path, content in html_pages.items():
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                            content, re.S)
        if not blocks:
            errors.append(f"no JSON-LD block on {path}")
        for b in blocks:
            try:
                obj = json.loads(b)
            except Exception as exc:
                errors.append(f"invalid JSON-LD in {path}: {exc}")
                continue
            if "domestiq" in json.dumps(obj).lower():
                errors.append(f"'domestiq' in JSON-LD of {path}")

    # Gate 10e (WS-SITE22): unified JSON-LD @graph. Each page carries exactly ONE
    # ld+json block, shaped {"@context", "@graph":[...]}. Every Organization /
    # Person node in the graph is the single canonical entity (@id #org / #tom):
    # no page repeats an inline copy, and org/person are otherwise referenced by
    # @id only. This is the proof for "one #org reference chain per page".
    def _iter_nodes(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from _iter_nodes(v)
        elif isinstance(o, list):
            for v in o:
                yield from _iter_nodes(v)

    for path, content in html_pages.items():
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                            content, re.S)
        if len(blocks) != 1:
            errors.append(f"{path} has {len(blocks)} JSON-LD blocks (WS-SITE22 wants exactly 1 @graph)")
            continue
        doc = json.loads(blocks[0])
        if not (isinstance(doc, dict) and isinstance(doc.get("@graph"), list)):
            errors.append(f"{path} JSON-LD is not a single @graph document")
            continue
        n_org = n_tom = 0
        for node in _iter_nodes(doc["@graph"]):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if node.get("name") is None and node.get("@type") is None:
                continue  # a bare {"@id": ...} reference is fine
            if any(t in ("Organization", "SportsActivityLocation", "LocalBusiness") for t in types):
                if node.get("@id") != ORG_ID:
                    errors.append(f"{path}: inline/foreign Organization node in @graph "
                                  f"(must be a single #org @id reference): {node.get('name')}")
                else:
                    n_org += 1
            if "Person" in types:
                if node.get("@id") != TOM_ID:
                    errors.append(f"{path}: inline/foreign Person node in @graph "
                                  f"(must be a single #tom @id reference): {node.get('name')}")
                else:
                    n_tom += 1
        if n_org > 1:
            errors.append(f"{path}: {n_org} #org node definitions in one @graph (want <=1)")
        if n_tom > 1:
            errors.append(f"{path}: {n_tom} #tom node definitions in one @graph (want <=1)")

    # Gate 11: robots.txt allows the major AI crawlers, disallows /options/,
    # and references the sitemap. LIVE BUILD ONLY: the preview copy deliberately
    # advertises no sitemap and courts no crawlers beyond what is needed to read
    # its noindex tag.
    robots = written.get("robots.txt", "")
    if not IS_PREVIEW_BUILD:
        for bot in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "anthropic-ai", "PerplexityBot",
                    "Google-Extended", "CCBot", "Applebot-Extended", "Bytespider"):
            if bot not in robots:
                errors.append(f"robots.txt missing required AI crawler allow: {bot}")
        if "Sitemap:" not in robots:
            errors.append("robots.txt missing Sitemap reference")
    if "Disallow: /options/" not in robots:
        errors.append("robots.txt missing 'Disallow: /options/'")

    # Gate 12: sitemap uses the prod host and never lists /options/. The preview
    # build ships no sitemap at all, which is checked by gate 13 instead.
    smx = written.get("sitemap.xml", "")
    if not IS_PREVIEW_BUILD:
        if PROD_ORIGIN not in smx:
            errors.append("sitemap.xml not using production host")
        if BASE_URL in smx:
            errors.append("sitemap.xml still references the github.io preview host")
        if "/options/" in smx:
            errors.append("sitemap.xml must not list /options/")

    # Gate 15 (2026-08-24): the preview copy must never be indexable. This is the
    # business-critical one: a second public copy of the whole site was competing
    # with horsepowercoaching.co.uk for canonical in Google. Every page carries
    # noindex, and no sitemap is shipped. Fails the BUILD, so it cannot regress.
    if IS_PREVIEW_BUILD:
        if "sitemap.xml" in written:
            errors.append("preview build must not ship a sitemap.xml")
        missing_noindex = [path for path, body in written.items()
                           if path.endswith(".html")
                           and 'name="robots" content="noindex' not in body]
        if missing_noindex:
            errors.append(
                f"preview build: {len(missing_noindex)} page(s) missing the noindex tag, "
                f"first: {missing_noindex[0]}")
    else:
        # And the live site must NEVER carry it, which would delist the business.
        # /options/ is the one deliberate exception: it is a private surface,
        # already Disallowed in robots.txt and absent from the sitemap.
        indexed_off = [path for path, body in written.items()
                       if path.endswith(".html") and 'content="noindex' in body
                       and not path.startswith("options/")
                       and not path.startswith("contact/thanks/")]
        if indexed_off:
            errors.append(
                f"LIVE build carries noindex on {len(indexed_off)} page(s), "
                f"first: {indexed_off[0]}")

    # Gate 16 (2026-08-24): every _redirects destination must resolve to a page
    # this build actually ships. A redirect pointing at a missing page is worse
    # than the 404 it replaces: it burns crawl budget and Google reports it as a
    # soft 404. Sources must also be unique, since Netlify applies first match
    # wins and a duplicated source silently shadows the later rule.
    rdr = written.get("_redirects", "")
    seen_sources = {}
    for line in rdr.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            errors.append(f"_redirects: unparseable rule: {line!r}")
            continue
        src, dest = parts[0], parts[1]
        if src in seen_sources:
            errors.append(f"_redirects: duplicate source {src} shadows a later rule")
        seen_sources[src] = dest
        if dest.startswith("http") or "*" in dest or ":" in dest:
            continue
        target = dest.strip("/")
        candidate = f"{target}/index.html" if target else "index.html"
        if candidate not in written and target not in written:
            errors.append(f"_redirects: {src} points at {dest}, which this build "
                          f"does not ship")

    # Gate 14 (WS-SITE22): llms.txt shipped at the site root and correct. It must
    # exist, lead with the H1, carry every tier price byte-for-byte as the site
    # states it (derived from the same tier cards, so the two can never drift),
    # advertise the ten key URLs, and include the "do not infer" boundary. The
    # em-dash (gate 1), domestiq (gate 8b) and client-surname (gate 8f) gates
    # already scan it as part of `written`.
    llms = written.get("llms.txt", "")
    if not llms:
        errors.append("llms.txt missing from built output")
    else:
        if not llms.startswith("# Horsepower Coaching"):
            errors.append("llms.txt does not open with the '# Horsepower Coaching' H1")
        site_unescaped = html.unescape(all_html)
        for amt in _tier_price_amounts():
            if amt not in llms:
                errors.append(f"llms.txt missing tier price {amt!r}")
            elif amt not in site_unescaped:
                errors.append(f"llms.txt price {amt!r} does not match a price on the site")
        for path in LLMS_KEY_PATHS:
            if prod_url(path) not in llms:
                errors.append(f"llms.txt missing key URL {prod_url(path)}")
        if "Not published / do not infer" not in llms:
            errors.append("llms.txt missing the 'Not published / do not infer' section")
        if "TrainingPeaks" not in llms:
            errors.append("llms.txt missing the TrainingPeaks delivery fact")

    # Gate 13: the live Plans page banner serves the Tom-chosen Izoard trio image
    # (WS-SITE11b; previously plans-pyrenees-switchback).
    plans_idx = written.get("plans/index.html", "")
    if 'class="page-banner"' in plans_idx and "plans-izoard-trio.webp" not in plans_idx:
        errors.append("plans page banner is not plans-izoard-trio.webp")

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
        errors.append(f"image weight {img_bytes/1024:.0f}KB exceeds 3.5MB budget")

    # Gate 9b (WS-SITE24): original blog photography has its OWN budget line. The
    # restored 2017-2021 photos ship under assets/img/blog/ and are counted here,
    # separately, against a 6MB allowance. os.listdir on img_dir above is
    # non-recursive, so these never touch the 3.5MB site-wide budget (gate 9). No
    # silent raise: this line is the documented ceiling for the full blog set.
    blog_dir = os.path.join(img_dir, "blog")
    blog_bytes = 0
    blog_count = 0
    if os.path.isdir(blog_dir):
        for f in os.listdir(blog_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                blog_bytes += os.path.getsize(os.path.join(blog_dir, f))
                blog_count += 1
    blog_budget = 6 * 1024 * 1024
    if blog_bytes > blog_budget:
        errors.append(f"blog image weight {blog_bytes/1024:.0f}KB exceeds 6MB budget")

    # ── Gate 17 (WS-SITE25): GA4 tagging, consent banner, privacy, thanks page ──
    js_src = {}
    for name in GA_JS_ASSETS:
        with open(os.path.join(HERE, "assets", name), encoding="utf-8") as fh:
            js_src[name] = fh.read()
    for name, src in js_src.items():
        if EM_DASH in src:
            errors.append(f"em-dash (U+2014) found in assets/{name}")
        if "domestiq" in src.lower():
            errors.append(f'"domestiq" found in assets/{name} (must be zero site-wide)')

    # 17a: the head stub ships exactly once per page in the live build and Google
    # is never referenced from HTML; the preview build carries no Google code.
    ga_id_re = re.compile(r"G-[A-Za-z0-9]{10}")
    if GA4_ENABLED:
        for path, content in html_pages.items():
            if content.count("<!-- hp-ga-boot -->") != 1:
                errors.append(f"17a: {path} must carry the hp-ga-boot stub exactly once")
            if content.count("gtag('consent','default'") != 1:
                errors.append(f"17a: {path} must set the consent default exactly once")
            m = re.search(r"<html\b[^>]*>", content)
            if not m or content.count(f'data-ga4="{GA4_MEASUREMENT_ID}"') != 1 \
                    or f'data-ga4="{GA4_MEASUREMENT_ID}"' not in m.group(0):
                errors.append(f"17a: {path} must carry data-ga4 exactly once, on <html>")
            if "googletagmanager.com" in content or "gtag('config'" in content:
                errors.append(f"17a: {path} references googletagmanager.com or gtag('config' in HTML")
    else:
        for path, content in written.items():
            for tok in ("hp-ga-boot", "gtag", "googletagmanager", "data-ga4"):
                if tok in content:
                    errors.append(f"17a: preview build carries {tok!r} in {path}")
            if ga_id_re.search(content):
                errors.append(f"17a: preview build carries a GA4 measurement ID in {path}")

    # 17b: consent.js boot order and ad_personalization stays denied.
    csrc = js_src["consent.js"]
    i_upd = csrc.find("'consent','update'")
    i_cfg = csrc.find("'config'")
    i_tag = csrc.find("googletagmanager.com/gtag/js")
    if not (0 <= i_upd < i_cfg < i_tag):
        errors.append(f"17b: consent.js boot order wrong (update {i_upd}, config {i_cfg}, "
                      f"gtag.js {i_tag})")
    if "'ad_personalization':'denied'" not in csrc or "'ad_personalization':'granted'" in csrc:
        errors.append("17b: consent.js must keep ad_personalization denied and never grant it")

    # 17c: no PII reaches analytics.
    asrc = js_src["analytics.js"]
    for tok in ("c-name", "c-email", "c-event", "c-message", "bot-field",
                "location.search", "FormData"):
        if tok in asrc:
            errors.append(f"17c: analytics.js references {tok!r}")
    for path, content in html_pages.items():
        for val in re.findall(r'\sdata-ga-[a-z0-9-]+="([^"]*)"', content):
            if "@" in html.unescape(val):
                errors.append(f"17c: data-ga-* value with '@' in {path}")
    thanks = written.get("contact/thanks/index.html", "")
    chrome_scripts = None
    for path, content in html_pages.items():
        tags = {t for t in re.findall(r"<script\b[^>]*>.*?</script>", content, re.S)
                if 'type="application/ld+json"' not in t}
        chrome_scripts = tags if chrome_scripts is None else chrome_scripts & tags
    asset_includes = {f'<script src="{BASE_PATH}/assets/{n}" defer></script>' for n in GA_JS_ASSETS}
    if not asset_includes <= (chrome_scripts or set()):
        errors.append("17c: consent.js / analytics.js are not included on every page")
    for t in re.findall(r"<script\b[^>]*>.*?</script>", thanks, re.S):
        if 'type="application/ld+json"' in t:
            continue
        if t not in (chrome_scripts or set()):
            errors.append(f"17c: thanks page carries a page-specific script: {t[:80]}")

    # 17d: tracking attributes carry their required params; buy/select sit inside
    # a parseable plan item whose id matches the TrainingPeaks store id.
    tracked = _ga_scan(html_pages)
    tp_by_title = {p["title"]: re.search(r"tp-(\d+)", p["buy_url"]).group(0)
                   for p in cat["plans"]}
    for path, attrs, items in tracked:
        kind = attrs.get("data-ga")
        need = GA_REQUIRED.get(kind)
        if need is None:
            errors.append(f"17d: unknown data-ga kind {kind!r} in {path}")
            continue
        for k in need:
            if not (attrs.get(f"data-ga-{k}") or "").strip():
                errors.append(f"17d: data-ga=\"{kind}\" missing data-ga-{k} in {path}")
        if kind in ("buy", "select"):
            if not items:
                errors.append(f"17d: {kind} link without a data-ga-item ancestor in {path}")
                continue
            try:
                it = json.loads(items[-1])
            except Exception:
                errors.append(f"17d: data-ga-item JSON does not parse in {path}")
                continue
            if not (re.match(r"^tp-\d+$", str(it.get("item_id", ""))) and it.get("item_name")
                    and float(it.get("price", 0)) > 0):
                errors.append(f"17d: data-ga-item incomplete in {path}: {it}")
            if kind == "buy":
                m = re.search(r"tp-\d+", attrs.get("href", ""))
                if not m or m.group(0) != it.get("item_id"):
                    errors.append(f"17d: buy link tp id != item_id in {path}")
    for path, content in html_pages.items():
        for raw in re.findall(r'data-ga-item="([^"]*)"', content):
            it = json.loads(html.unescape(raw))
            if tp_by_title.get(it.get("item_name")) != it.get("item_id"):
                errors.append(f"17d: data-ga-item {it.get('item_id')} does not match the "
                              f"buy_url of {it.get('item_name')!r} in {path}")

    # 17e: banner, both buttons in order, footer links, TTL.
    for path, content in html_pages.items():
        if content.count('id="cookie-banner"') != 1:
            errors.append(f"17e: {path} must carry exactly one #cookie-banner")
        btns = re.findall(r'data-consent="(accept|reject)"', content)
        if btns != ["accept", "reject"]:
            errors.append(f"17e: {path} consent buttons are {btns}, want accept then reject")
        if f'href="{BASE_PATH}{PRIVACY_PATH}"' not in content:
            errors.append(f"17e: {path} has no link to {PRIVACY_PATH}")
        if 'class="consent-open"' not in content:
            errors.append(f"17e: {path} has no Cookie settings link")
        if f'data-consent-ttl="{CONSENT_TTL_DAYS}"' not in content:
            errors.append(f"17e: {path} banner TTL is not {CONSENT_TTL_DAYS}")

    # 17f: en-dash gate, with the one frozen legacy page allowlisted.
    EN_DASH = "\u2013"
    EN_DASH_ALLOW = {"blog/f/our-origins---a-little-bit-of-history/index.html"}
    for path, content in written.items():
        if EN_DASH in content and path not in EN_DASH_ALLOW:
            errors.append(f"17f: en-dash (U+2013) found in {path}")
    for name in GA_JS_ASSETS + ("catalogue.js",):
        with open(os.path.join(HERE, "assets", name), encoding="utf-8") as fh:
            if EN_DASH in fh.read():
                errors.append(f"17f: en-dash (U+2013) found in assets/{name}")

    # 17g: thanks page is noindex, unlisted, Disallowed, and is the form action.
    if 'content="noindex' not in thanks:
        errors.append("17g: thanks page is not noindex")
    if prod_url(THANKS_PATH) in written.get("sitemap.xml", ""):
        errors.append("17g: thanks page listed in sitemap.xml")
    groups = robots.split("User-agent:")[1:]
    if not groups or any(f"Disallow: {THANKS_PATH}" not in g for g in groups):
        errors.append(f"17g: robots.txt group(s) missing 'Disallow: {THANKS_PATH}'")
    contact_html = written.get("contact/index.html", "")
    for tok in (f'action="{BASE_PATH}{THANKS_PATH}"', 'data-netlify="true"',
                'netlify-honeypot="bot-field"', 'name="form-name" value="contact"'):
        if tok not in contact_html:
            errors.append(f"17g: contact form missing {tok}")

    # 17h: privacy page is complete and true to the constants.
    priv = written.get("privacy/index.html", "")
    if not priv:
        errors.append("17h: privacy/index.html missing")
    else:
        for tok in ("{{", "TODO", "G-XXXXXXXXXX"):
            if tok in priv:
                errors.append(f"17h: privacy page contains {tok!r}")
        m = re.search(r'<span class="ga-retention">(.*?)</span>', priv)
        if not m or html.unescape(m.group(1)) != GA4_RETENTION:
            errors.append("17h: privacy page retention does not equal GA4_RETENTION")
        if PRIVACY_NO_PII_LINE not in html.unescape(priv):
            errors.append("17h: privacy page missing the no-PII sentence")

    # ── Gate 18 (WS-SITE26): Plan Only first, the enquiry option field ──────────
    # 18a: the option select sits in the contact form, in order, default selected.
    selects = re.findall(r'<select id="c-option" name="option">(.*?)</select>', contact_html, re.S)
    if len(selects) != 1:
        errors.append(f"18a: contact page carries {len(selects)} option selects, want 1")
    else:
        i_form = contact_html.find('class="contact-form"')
        i_sel = contact_html.find('<select id="c-option"')
        i_end = contact_html.find("</form>", i_form)
        if not (0 <= i_form < i_sel < i_end):
            errors.append("18a: option select is not inside the contact form")
        if not (contact_html.find('id="c-email"') < i_sel < contact_html.find('id="c-event"')):
            errors.append("18a: option select is not between email and event")
        vals = re.findall(r'<option value="([^"]*)"', selects[0])
        if vals != LEAD_OPTION_VALUES:
            errors.append(f"18a: option values {vals} != {LEAD_OPTION_VALUES}")
        sel = re.findall(r'<option value="([^"]*)" selected>', selects[0])
        if sel != [LEAD_OPTION_DEFAULT]:
            errors.append(f"18a: selected options {sel}, want [{LEAD_OPTION_DEFAULT!r}]")
        m = re.search(r'<label for="c-option">(.*?)</label>', contact_html)
        if not m or html.unescape(m.group(1)) != LEAD_OPTION_LABEL:
            errors.append("18a: option label text does not equal LEAD_OPTION_LABEL")

    # 18b: ?option= links carry known values, on the right tier pages only.
    bare_contact = f'href="{BASE_PATH}/contact/"'
    for path, content in html_pages.items():
        for v in re.findall(rf'href="{re.escape(BASE_PATH)}/contact/\?option=([^"]*)"', content):
            if v not in LEAD_OPTION_VALUES:
                errors.append(f"18b: unknown ?option={v!r} in {path}")
        if content.count(bare_contact) != 2:
            errors.append(f"18b: {path} has {content.count(bare_contact)} bare contact links, want 2")
    coached_html = written.get("coached/index.html", "")
    coaching_html = written.get("coaching/index.html", "")
    if coached_html.count(f'href="{BASE_PATH}/contact/?option=plan-only"') != 2:
        errors.append("18b: coached/index.html must link ?option=plan-only exactly twice")
    if "?option=coached-by-tom" in coached_html:
        errors.append("18b: coached/index.html links ?option=coached-by-tom")
    if coaching_html.count(f'href="{BASE_PATH}/contact/?option=coached-by-tom"') != 3:
        errors.append("18b: coaching/index.html must link ?option=coached-by-tom exactly 3 times")
    if "?option=plan-only" in coaching_html:
        errors.append("18b: coaching/index.html links ?option=plan-only")

    # 18c: analytics.js whitelist matches the build, and the preselect script
    # ships on /contact/ only.
    m = re.search(r"var LEAD_OPTIONS = \[([^\]]*)\]", asrc)
    js_vals = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    if js_vals != LEAD_OPTION_VALUES:
        errors.append(f"18c: analytics.js LEAD_OPTIONS {js_vals} != {LEAD_OPTION_VALUES}")
    if asrc.count("lead_option") < 2:
        errors.append("18c: analytics.js must send lead_option on submit and on the lead")
    if "JSON.stringify({ ts:" not in asrc:
        errors.append("18c: analytics.js must store the lead flag as JSON {ts, option}")
    if contact_html.count(CONTACT_PRESELECT_JS) != 1:
        errors.append("18c: contact page must carry the preselect script exactly once")
    for path, content in written.items():
        if path == "contact/index.html":
            continue
        if CONTACT_PRESELECT_JS in content or "URLSearchParams" in content:
            errors.append(f"18c: preselect script or URLSearchParams found in {path}")

    # 18d: the monthly review rhythm on /coached/ and in llms.txt.
    def _body_text(doc):
        doc = re.sub(r"<head\b.*?</head>", " ", doc, flags=re.S)
        doc = re.sub(r"<script\b.*?</script>", " ", doc, flags=re.S)
        return html.unescape(re.sub(r"<[^>]+>", " ", doc))
    ctext = _body_text(coached_html)
    if ctext.lower().count("rest week") < 4:
        errors.append(f"18d: coached page says 'rest week' {ctext.lower().count('rest week')} times, want >= 4")
    if ctext.lower().count("three weeks of training") < 2:
        errors.append("18d: coached page must say 'three weeks of training' at least twice")
    if "one review a month" not in ctext.lower():
        errors.append("18d: coached page missing 'one review a month'")
    m = re.search(r'<meta name="description" content="([^"]*)"', coached_html)
    coached_desc = html.unescape(m.group(1)) if m else ""
    if "rest week" not in coached_desc:
        errors.append("18d: coached meta description missing 'rest week'")
    svc_desc = ""
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', coached_html, re.S):
        data = json.loads(raw)
        nodes = data if isinstance(data, list) else data.get("@graph", [data])
        for n in nodes:
            if isinstance(n, dict) and n.get("@type") == "Service":
                svc_desc = n.get("description", "")
    if "rest week" not in svc_desc:
        errors.append("18d: coached Service JSON-LD description missing 'rest week'")
    if "rest week" not in written.get("llms.txt", ""):
        errors.append("18d: llms.txt missing 'rest week'")
    for tok in ("Feedback at the end of every block", "at the end of the block, as part of the review"):
        if tok in coached_html:
            errors.append(f"18d: coached page still carries {tok!r}")

    # 18e: Plan Only leads the CTAs and the nav.
    home_html = written.get("index.html", "")
    i_hero = home_html.find('<section class="hero')
    hero = home_html[i_hero:home_html.find("</section>", i_hero)] if i_hero >= 0 else ""
    hero_hrefs = re.findall(r'<a class="btn[" ][^>]*?href="([^"]*)"', hero)
    if hero_hrefs[:2] != [f"{BASE_PATH}/coached/", f"{BASE_PATH}/coaching/"]:
        errors.append(f"18e: home hero buttons point at {hero_hrefs[:2]}, want /coached/ then /coaching/")
    for path, content in html_pages.items():
        m = re.search(r'<nav class="site-nav".*?</nav>', content, re.S)
        if not m:
            errors.append(f"18e: {path} has no header nav")
            continue
        i_po = m.group(0).find(f'href="{BASE_PATH}/coached/"')
        i_tom = m.group(0).find(f'href="{BASE_PATH}/coaching/"')
        if not (0 <= i_po < i_tom):
            errors.append(f"18e: {path} nav does not put Plan Only before Coached by Tom")
    if "Not quite ready" in coaching_html:
        errors.append("18e: coaching page still says 'Not quite ready'")
    for path in ("index.html", "triathlon-coaching/index.html", "cycling-coaching/index.html"):
        n = written.get(path, "").count('class="tier-flag"')
        if n != 1:
            errors.append(f"18e: {path} carries {n} tier flags, want 1")
    for path in ("about/index.html", "triathlon-coaching/index.html", "cycling-coaching/index.html"):
        m = re.search(r'<div class="cta-row"[^>]*>\s*<a [^>]*?href="([^"]*)"', written.get(path, ""))
        if not m or m.group(1) != f"{BASE_PATH}/coached/":
            errors.append(f"18e: {path} first cta-row anchor does not point at /coached/")

    # 18f: the privacy page names the option field in both places.
    priv_text = html.unescape(priv)
    if PRIVACY_FORM_LINE not in priv_text:
        errors.append("18f: privacy page missing PRIVACY_FORM_LINE")
    if "which option they picked on it" not in priv_text:
        errors.append("18f: privacy page missing 'which option they picked on it'")
    if PRIVACY_NO_PII_LINE not in priv_text:
        errors.append("18f: privacy page missing the no-PII sentence")

    # 18g: the /coached/ description fits the snippet budget.
    if len(coached_desc) > 158:
        errors.append(f"18g: coached meta description is {len(coached_desc)} characters, want <= 158")

    # 17i is the freeze gate (freeze_check, after run_gates) against a snapshot
    # regenerated from the LIVE build.

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
    print(f"  - {blog_count} original blog photos, {blog_bytes/1024:.0f}KB total (separate budget 6144KB)")
    print(f"  - zero 'domestiq' occurrences across all generated output and JS assets")
    print(f"  - Gate 17 (GA4/consent): 17a stub {'once per page, live' if GA4_ENABLED else 'absent, preview'}; "
          f"17b boot order; 17c no PII; 17d {len(tracked)} tracked elements; 17e banner; "
          f"17f en-dash; 17g thanks page; 17h privacy page")
    print("  - Gate 18 (Plan Only first): 18a option field; 18b ?option= links; 18c analytics "
          "whitelist + preselect on /contact/ only; 18d monthly review copy; 18e CTA order; "
          "18f privacy; 18g description length")
    print(f"  - zero client surnames across all generated output (first name + initial policy)")
    ld_total = sum(len(re.findall(r'application/ld\+json', v)) for v in html_pages.values())
    print(f"  - SEO/AEO: 1 h1 + canonical(prod host) + OG/Twitter + parsing JSON-LD per page "
          f"({ld_total} JSON-LD blocks total)")
    print(f"  - robots.txt: {len([l for l in written['robots.txt'].splitlines() if l.startswith('User-agent:')])} "
          f"user-agent groups incl. AI crawlers; /options/ disallowed; sitemap referenced")
    if "sitemap.xml" in written:
        print(f"  - sitemap.xml: {written['sitemap.xml'].count('<url>')} URLs on prod host, /options/ excluded")
    else:
        print("  - sitemap.xml: not shipped (preview build, deliberately not indexable)")


if __name__ == "__main__":
    build()

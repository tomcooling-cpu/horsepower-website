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
CONTENT_BLOG = os.path.join(HERE, "content", "blog")   # WS-SITE14 blog posts (front matter + markdown)

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
HERO_HEADLINE = "Big goals are built from ordinary weeks, done properly."
HERO_BODY = ("Your first 70.3. Ironman Wales. Kona. A 100 mile TT. Whatever your dream "
             "is, getting there comes down to doing the right training week after week, "
             "at the right dose, and adjusting when life gets in the way. That's what I "
             "do, and I take your dream as seriously as you do.")
CTA_FIND = "Find your plan"
CTA_GET = "Get coached"

# (Removed 2026-08-13: the "written by a professional coach / not a machine" home band was
# dropped. Protesting that the coaching is not AI is itself an AI tell; the site sells the
# coaching on its own terms in Tom's voice, never by arguing it is human.)

# Female-first block (copy E). Home female feature + /female-performance/ intro.
# The locked headline stays FEMALE_LEAD; this is the body that sits beneath it.
FEMALE_FIRST_BODY = ("Most plans were built around male physiology and handed to women "
                     "to get on with. I build them the other way round. Your plan starts "
                     "from how a female athlete actually trains, adapts and recovers, and "
                     "when I coach you it works around your cycle and your life, not an "
                     "average that was never you.")

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
TIER_PLANS_BODY = ("Built for your race, ready to start today. Pick from over 150 plans, "
                   "every one written by me for a specific event and goal, delivered "
                   "straight into TrainingPeaks. The same session design my coached "
                   "athletes follow. For the rider who knows how to train and just wants "
                   "a proven plan to follow.")

# Coached tier (copy C), two paragraphs. Home tier card + the /coached/ page body.
TIER_COACHED_BODY = ("A plan built for you, not pulled off a shelf. I write your "
                     "programme myself, block by block, exactly the way I do for my "
                     "fully coached athletes. At the end of each block I look at "
                     "everything you have done, tell you what I see, and build the next "
                     "block around where you actually are, not where the plan assumed "
                     "you would be.")
TIER_COACHED_BODY_2 = ("The only difference from full coaching is the contact. There are "
                       "no catch-up calls and I am not on call day to day. The coaching "
                       "that goes into the plan is identical. A real coach shaping your "
                       "training around your life and your numbers, without the premium "
                       "of unlimited access.")

# Coached by Tom tier (copy D), two paragraphs. Home tier card + the /coaching/ hero.
TIER_TOM_BODY = ("The full thing. One to one, bespoke, and as close as it gets to having "
                 "a professional coach in your corner. I build your programme around your "
                 "race, your life and your body, then I am with you the whole way: "
                 "feedback every week, in depth analysis of the sessions that matter, and "
                 "support across everything that decides the day, from pacing and "
                 "fuelling to race craft, bike fit and the mental side.")
TIER_TOM_BODY_2 = ("This is the coaching that has taken Horsepower athletes to Ironman "
                   "titles, course records and finish lines they were told were beyond "
                   "them. Places are limited, because there are only so many athletes I "
                   "can coach this closely at once.")

RESULTS_LINE = ("Ironman wins. 70.3 podiums. XTRI podiums. Haute Route podiums. Ultra "
                "race wins. And a lot of first finish lines, which I'm just as proud "
                "of.")

WHICH_PLANS = "Know what you're doing and want a proven route? Plan Store."
WHICH_COACHED = "Want the plan built around your life, and someone reading your sessions? Plan Only."
WHICH_TOM = "Chasing something big and want a coach in your corner for all of it? Coached by Tom."

# The /plans/ intro is copy B, reused verbatim from the home tier card.
PLANS_INTRO = TIER_PLANS_BODY

COACHED_INTRO = ("The coaching that goes into my fully coached athletes' plans, written "
                 "for you, for £120 a month. I build your programme block by block and "
                 "give you real feedback on the sessions you actually do.")

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

# Strings that must appear byte-exact in the built output (copy-verbatim gate).
VERBATIM_REQUIRED = [
    HERO_HEADLINE, HERO_BODY, FEMALE_FIRST_BODY,
    TIER_PLANS_BODY, TIER_COACHED_BODY, TIER_COACHED_BODY_2,
    TIER_TOM_BODY, TIER_TOM_BODY_2, RESULTS_LINE,
    WHICH_PLANS, WHICH_COACHED, WHICH_TOM, PLANS_INTRO,
]

EM_DASH = "—"


# ── HTML helpers ─────────────────────────────────────────────────────────────
def esc(s) -> str:
    return html.escape(str(s), quote=True)


def head(title, description, canonical, og_image_name=None, og_type="website", extra="") -> str:
    name = og_image_name or DEFAULT_OG_IMAGE
    og_img = og_image_url(name)
    og_alt = IMG_ALT.get(name, SITE_NAME)
    w, h = IMG_DIMS.get(name, (1200, 800))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
    (TIER1_NAME, BASE_PATH + "/plans/", "plans"),
    (TIER2_NAME, BASE_PATH + "/coached/", "coached"),
    ("About Us", BASE_PATH + "/about/", "about"),
    ("Blog", BASE_PATH + "/blog/", "blog"),
]


def header(active) -> str:
    items = []
    for label, href, key in NAV:
        cur = ' aria-current="page"' if key == active else ""
        items.append(f'<li><a href="{esc(href)}"{cur}>{esc(label)}</a></li>')
    # The single Contact CTA (teal button). Plan discovery lives on the "Plans"
    # nav link, so the button points at Contact instead of duplicating Plans.
    items.append(f'<li><a class="cta" href="{esc(CONTACT_URL)}">Contact</a></li>')
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
          <li><a href="{BASE_PATH}/plans/">{esc(TIER1_NAME)}</a></li>
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
          <li><a href="{BASE_PATH}/blog/">Blog</a></li>
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


def page(active, title, description, canonical, body,
         og_image_name=None, og_type="website", extra="") -> str:
    return (head(title, description, canonical, og_image_name, og_type, extra)
            + header(active) + body + footer())


# ── JSON-LD structured data (WS-SITE10) ──────────────────────────────────────
# Every fact below already exists on the site or in config (no fabrication).
# Blocks are emitted verbatim as application/ld+json; a build gate parses every
# block and asserts zero "domestiq".
def ld_script(objs) -> str:
    if isinstance(objs, dict):
        objs = [objs]
    return "".join(
        f'<script type="application/ld+json">{json.dumps(o)}</script>\n'
        for o in objs)


def _org_provider():
    return {"@type": "Organization", "name": SITE_NAME, "url": prod_url("/")}


def _area_served():
    return [{"@type": "Country", "name": "United Kingdom"},
            {"@type": "Place", "name": "Online and remote coaching worldwide"}]


def org_node(with_rating=False):
    """Organization / LocalBusiness (SportsActivityLocation) for Horsepower."""
    node = {
        "@context": "https://schema.org",
        "@type": ["SportsActivityLocation", "LocalBusiness"],
        "name": SITE_NAME,
        "alternateName": "Horsepower Coaching | Triathlon, Cycling and Endurance Coaching",
        "url": prod_url("/"),
        "logo": OG_LOGO,
        "image": og_image_url("ironman-wales-finish"),
        "description": ("Triathlon, cycling and endurance coaching and training plans built "
                        "for your target race, with a particular emphasis on female-specific "
                        "performance. Based in Clevedon, UK; coaching athletes online worldwide."),
        "founder": {"@type": "Person", "name": "Tom Cooling"},
        "address": {"@type": "PostalAddress", "addressLocality": "Clevedon",
                    "addressRegion": "Somerset", "addressCountry": "GB"},
        "areaServed": [{"@type": "City", "name": "Clevedon"}] + _area_served(),
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
    return {"@context": "https://schema.org", "@type": "WebSite",
            "name": SITE_NAME, "url": prod_url("/"),
            "inLanguage": "en-GB", "publisher": _org_provider()}


def person_node():
    return {
        "@context": "https://schema.org", "@type": "Person",
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
    "coached-almere-finish": "A Horsepower athlete celebrating on the finish line at Challenge Almere-Amsterdam",
    "coached-tenby-swim": "Swimmers in pink caps crossing Tenby harbour below pastel houses during the Ironman Wales swim",
    "female-wales-podium": "The women's podium celebration at Ironman Wales with champagne mid-spray",
    "female-montblanc-hike": "An athlete in a Horsepower cap hiking alpine switchbacks with the Mont Blanc massif in the distance",
    "female-welsh-tt": "Hannah S in an aero tuck during the Welsh 100 mile time trial championships",
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
    "female-tt-v2": "A cyclist racing a time trial in an aero tuck on a country road",
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
    "female-tt-v2": "50% 50%",           # WS-SITE11a re-crop, Madison S centred in frame
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
    "coaching-alpine-hairpin": "50% 58%",     # riders + road low-centre in the band
    "tom-bottle-refill": "50% 30%",      # Tom's face + bottle
    "about-brecon-titan": "50% 40%",     # Tom central under the FINISH arch
    "about-dolomites-descender": "50% 55%",  # descending rider low, peaks above
    "about-dolomites-cobbles": "50% 45%",    # rider + Haute Route arch behind
    "about-dolomites-pink-arch": "50% 50%",  # rider centred, arch cropped to portrait
    "about-transpyrenees-night": "50% 32%",  # Tom's face upper in the 4/5 crop
    "tom-swim-kaolinite": "50% 35%",     # Tom's face, race number lower
    "tom-alps-signon": "46% 40%",        # Tom + the THOMAS 2044 board centred
    "coaching-support-roadside": "50% 45%",  # Tom's thumbs up + the passing rider
    "coached-almere-finish": "50% 35%",  # arms-up roar at the top of the frame
    "coached-tenby-swim": "50% 60%",     # swim field low, pastel harbour houses above
    "female-wales-podium": "50% 45%",    # the three podium steps
    "female-montblanc-hike": "50% 55%",  # hiker on the switchbacks, massif behind
    "female-welsh-tt": "60% 50%",        # Hannah aero-tucked right of centre
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
    return (f'<a class="{cls}" href="{INSTAGRAM_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Instagram">{SVG_IG}</a>'
            f'<a class="{cls}" href="{WHATSAPP_URL}" rel="noopener" target="_blank" aria-label="Message Horsepower Coaching on WhatsApp">{SVG_WA}</a>'
            f'<a class="{cls}" href="{FACEBOOK_URL}" rel="noopener" target="_blank" aria-label="Horsepower Coaching on Facebook">{SVG_FB}</a>')


IMG_DIMS = {
    "hero-alps": (1500, 1000), "hero-welsh-climb": (1500, 1000),
    "alpine-ridge": (1500, 1001),
    "female-hero": (1500, 1001), "ironman-wales-finish": (1500, 1000),
    "coached-band": (1500, 999), "tom-gravel": (1400, 1050),
    "camp-group": (1400, 1050), "female-tt-v2": (606, 758),
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
    "coached-almere-finish": (734, 1100),
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

# Verified verbatim quotes from Tom's Google Business profile (5.0, 15 reviews).
# Ian's real review runs on mid-sentence; per the spec it is closed at a natural
# earlier point and never invented past it. Every string here must appear in
# VERIFIED_QUOTES byte-exact (carousel-data gate).
CLIENT_QUOTES = [
    {"name": "Ian C", "context": "Cycling athlete", "pages": ["coached"],
     "quote": ("Tom is a great coach and has helped massively with my cycling, helping me "
               "achieve results I wouldn't have thought possible previously.")},
    {"name": "jc b", "context": "Ironman finisher, 11h13", "pages": ["coached", "coaching"],
     "quote": ("I can't recommend Tom enough. Over the past year, the support, structure, "
               "and guidance I received helped me progress massively and achieve my "
               "Ironman goal, finishing in 11h13.")},
    {"name": "Emma N", "context": "Multi-event athlete", "pages": ["female"],
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

# The Madison S result, rendered as a distinct slide in every carousel.
MADDISON_SLIDE = {"kind": "result"}
# A clearly-styled "more reviews" state (WS-SITE9, 3d). The female carousel holds
# every genuine female review in the repo (currently one, Emma N); rather than
# fabricate testimonials, we append this honest placeholder so the carousel reads
# as intentional and is ready to take the review screenshots Tom is sending.
MORE_SLIDE = {"kind": "more"}


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
    if item.get("kind") == "more":
        return (
            '<figure class="review-slide result-slide review-slide--more">'
            '<blockquote>More reviews from the women we coach are on the way. In the '
            'meantime, read what Horsepower athletes say on Google.</blockquote>'
            '<figcaption>Horsepower Coaching <span>Verified Google reviews</span></figcaption>'
            '</figure>')
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
             on_dark=True, include_result=True, more_state=False):
    """Accessible auto-advancing review carousel for `page`. Vanilla JS
    (assets/carousel.js) drives auto-advance, arrows, dots, hover/focus pause."""
    slides = list(quotes_for(page))
    if include_result:
        slides = slides + [MADDISON_SLIDE]
    if more_state:
        slides = slides + [MORE_SLIDE]
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
    """Homepage client-voices carousel: every quote plus the Madison result."""
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
      <a class="btn" href="{BASE_PATH}/plans/">{esc(CTA_FIND)}</a>
      <a class="btn on-dark ghost" href="{BASE_PATH}/coached/">{esc(CTA_GET)}</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Three ways to train with Horsepower</p>
    <h2>Pick the level of support that fits</h2>
    <p class="section-intro">The plan is only half of it. What changes across the three tiers is how
    much of me you get: from a proven plan you run yourself, to feedback every block, to the full
    coaching relationship.</p>
    <div class="support-ladder" role="list" aria-label="Support increases across the three tiers">{ladder}</div>
    <div class="tier-grid">
      <div class="tier-card">
        <h3>{esc(TIER1_NAME)}</h3>
        <div class="price">From &pound;39.99, one-off</div>
        <p class="support-line"><span class="support-tag support-tag--none">Support: {esc(SUPPORT_LEVELS[0][1])}</span>{esc(SUPPORT_LEVELS[0][2])}</p>
        <p>{esc(TIER_PLANS_BODY)}</p>
        <a class="btn" href="{BASE_PATH}/plans/">Browse the library</a>
      </div>
      <div class="tier-card feature">
        <h3>{esc(TIER2_NAME)}</h3>
        <div class="price">&pound;120 a month</div>
        <p class="support-line"><span class="support-tag support-tag--mid">Support: {esc(SUPPORT_LEVELS[1][1])}</span>{esc(SUPPORT_LEVELS[1][2])}</p>
        <p>{esc(TIER_COACHED_BODY)}</p>
        <p>{esc(TIER_COACHED_BODY_2)}</p>
        <a class="btn" href="{BASE_PATH}/coached/">How coaching works</a>
      </div>
      <div class="tier-card">
        <h3>Coached by Tom</h3>
        <div class="price">&pound;185 a month</div>
        <p class="support-line"><span class="support-tag support-tag--full">Support: {esc(SUPPORT_LEVELS[2][1])}</span>{esc(SUPPORT_LEVELS[2][2])}</p>
        <p>{esc(TIER_TOM_BODY)}</p>
        <p>{esc(TIER_TOM_BODY_2)}</p>
        <a class="btn" href="{BASE_PATH}/coaching/">See if there is a place</a>
      </div>
    </div>
  </div>
</section>

<section class="alt feature-female">
  <div class="wrap feature-grid feature-grid--portrait">
    <div class="feature-media feature-media--portrait">{img("female-tt-v2")}</div>
    <div class="feature-copy">
      <p class="eyebrow">Female performance</p>
      <h2>Female first, not female adapted.</h2>
      <p class="section-intro">{esc(FEMALE_FIRST_BODY)}</p>
      <p style="margin-top:20px"><a class="btn" href="{BASE_PATH}/female-performance/">See how I train female athletes</a></p>
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
      <div class="which-item"><strong>{esc(TIER1_NAME)}</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Over {total} plans, every one built for its event</h2>
    <p class="section-intro">First marathon to Ironman, hill climbs to 100 mile TTs, every plan in
    the library is written for one specific race and one specific goal. Find yours and get to work.</p>
    <p style="margin-top:22px"><a class="btn" href="{BASE_PATH}/plans/">{esc(CTA_FIND)}</a></p>
  </div>
</section>
</main>"""
    desc = ("Training plans and coaching built for your race, written by Tom Cooling. "
            "Over 150 plans, plus coaching from £120 a month.")
    extra = ld_script([org_node(with_rating=True), website_node()])
    return page("home", "Horsepower Coaching | Training plans and coaching for your race",
                desc, prod_url("/"), body, og_image_name="hero-alpine-mist", extra=extra)


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
    return page("plans", f"Training Plan Library | {total} plans built for your race | Horsepower Coaching",
                desc, prod_url("/plans/"), body,
                og_image_name="plans-izoard-trio", extra=extra)


def render_plan_detail(cat, p) -> str:
    canonical = prod_url(f"/plans/{p['slug']}/")
    tier_line = "" if p["tier"] == "Standard" else f'<div class="spec-box"><div class="k">Level</div><div class="v">{esc(p["tier"])}</div></div>'
    paras = "".join(f"<p>{esc(x)}</p>" for x in re.split(r"(?<=[.])\s{2,}", p["description"]) if x.strip()) or f"<p>{esc(p['description'])}</p>"
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": p["title"], "description": p["description"],
        "brand": {"@type": "Brand", "name": "Horsepower Coaching"},
        "category": f'{p["sport"]} training plan',
        "url": canonical,
        "offers": {"@type": "Offer", "price": f'{p["price"]:.2f}', "priceCurrency": "GBP",
                   "availability": "https://schema.org/InStock", "url": p["buy_url"]},
    }
    crumbs_ld = breadcrumb_node([("Home", "/"), ("Training Plans", "/plans/"),
                                 (p["title"], None)])
    extra = ld_script([ld, crumbs_ld])
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
    return page("plans", f"{p['title']} | Horsepower Coaching", desc, canonical, body,
                og_image_name="plans-pyrenees-switchback", og_type="product", extra=extra)


COACHED_FAQ = [
    ("Is there a call every week?",
     "No. Plan Only is built around the work and the why, delivered in writing so you can go "
     "back to it. If you want calls, WhatsApp and race-day strategy built together, that is "
     "Coached by Tom."),
    ("What if my numbers change or life gets in the way?",
     "The plan moves. When your data shifts or a week falls apart, the next block reflects it. "
     "That is the point of building it block by block instead of all at once."),
    ("Which sports do you coach?",
     "Triathlon across every distance, road and ultra running, and cycling from sportives to "
     "ultra-distance. If you have a target event, I can build for it."),
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
    <div class="cta-row"><a class="btn" href="{esc(CONTACT_URL)}">Apply for coaching</a></div>
  </div>
</section>

<div class="media-band">{img("hero-torridon-ridge", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>What you get for &pound;120 a month</h2>
    <p class="section-intro">{esc(TIER_COACHED_BODY)}</p>
    <p class="section-intro">{esc(TIER_COACHED_BODY_2)}</p>
    <div class="side-fig-grid">
      <ol class="step-list">
        <li><strong>It starts with you</strong>A proper intake: your target event, your history, your week, your numbers and the hours you actually have.</li>
        <li><strong>Your plan arrives block by block</strong>Built around your life and your event, three weeks at a time, so it stays current with how your training is actually going rather than a whole year written on day one.</li>
        <li><strong>Feedback on every completed session</strong>I read the sessions you complete against what was asked, using your actual data, and tell you what it means and what happens next.</li>
        <li><strong>A race plan before every start line</strong>Pacing, fuelling and strategy for your event, in your hands before you get there.</li>
      </ol>
      <figure class="photo-fig photo-fig--port">{img("coached-almere-finish")}
        <figcaption>A Horsepower athlete finishing Challenge Almere-Amsterdam</figcaption></figure>
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
        <p>There are no scheduled calls and I am not on call day to day. What you get is a programme I build around your life and your event, with real feedback on the sessions you actually do. If you want me in your corner for all of it, look at Coached by Tom.</p>
        <p style="margin-top:18px"><a class="btn on-dark ghost" href="{BASE_PATH}/coaching/">Coached by Tom</a></p>
      </div>
    </div>
  </div>
</section>

<div class="media-band">{img("hero-tenby-swim", cls="media-bg")}</div>

<section>
  <div class="wrap">
    <h2>Ready to start?</h2>
    <p class="section-intro">Tell me about your event and your season and I'll take it from there.</p>
    <p style="margin-top:18px"><a class="btn" href="{esc(CONTACT_URL)}">Apply for coaching</a></p>
  </div>
</section>
{quote_block("coached")}
</main>"""
    desc = ("Coached by Tom Cooling, £120 a month. A plan I build for you block by block, "
            "with real feedback on every session and a race plan for race day.")
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in COACHED_FAQ]}
    svc = service_node(
        f"{TIER2_NAME} coaching",
        (f"{COACHED_INTRO} Built block by block around your life and target event, with real "
         "feedback on every completed session and a race plan before every start line."),
        "/coached/", monthly_price="120.00")
    extra = ld_script([
        breadcrumb_node([("Home", "/"), (TIER2_NAME, None)]), svc, faq_ld])
    return page("coached", f"{TIER2_NAME} | £120 a month | Horsepower Coaching", desc,
                prod_url("/coached/"), body, og_image_name="hero-torridon-ridge", extra=extra)


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
  {img("coached-tom-dolomites-arch", cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Coached by Tom &middot; &pound;185 a month &middot; Limited places</p>
    <h1>A coach in your corner for all&nbsp;of&nbsp;it</h1>
    <p class="lede">{esc(TIER_TOM_BODY)}</p>
    <p class="lede">{esc(TIER_TOM_BODY_2)}</p>
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
        <li><strong>You train, I stay close</strong>Every session tells you what to do and why. Message me any time you need to move something or talk it through. Contact is unlimited, so you are never left guessing between sessions.</li>
        <li><strong>Read, analysed, fed back on</strong>I read the sessions you complete, analyse them against what was set using your actual data in TrainingPeaks and WKO5, and feed back on them. Feedback is a key part of the coaching journey, so each week you get a full round of feedback on everything you have completed.</li>
        <li><strong>We talk, the plan moves</strong>Block by block video catch-ups, WhatsApp for general chat, and the next block reflects real life and your numbers as they move.</li>
      </ol>
      <figure class="photo-fig photo-fig--port">{img("coaching-support-roadside")}
        <figcaption>Trackside on the Ironman Wales bike course</figcaption></figure>
    </div>
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

<div class="media-band">{img("coaching-alpine-hairpin", cls="media-bg")}</div>
{carousel("coaching", subhead="What athletes say about being coached by Tom")}
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
      <p style="margin-top:6px"><a class="btn" href="{esc(CONTACT_URL)}">Apply for a place</a></p>
      <p class="pricing-note">Not quite ready for this level? <a href="{BASE_PATH}/coached/">{esc(TIER2_NAME)} is &pound;120 a month</a>.</p>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Not sure which tier?</h2>
    <div class="which-grid">
      <div class="which-item"><strong>{esc(TIER1_NAME)}</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>{esc(TIER2_NAME)}</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
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
                prod_url("/coaching/"), body, og_image_name="coached-tom-dolomites-arch", extra=extra)


def render_about(cat) -> str:
    # Bio content is VERBATIM from the current site; structure/order is presentation.
    body = f"""<main id="main">
<section class="hero about-hero">
  <div class="wrap about-hero-grid">
    <div class="about-hero-copy">
      <p class="eyebrow" style="color:var(--teal-soft)">About Us</p>
      <h1>The coach behind Horsepower</h1>
      <p class="lede">I'm Tom Cooling: an ex-elite triathlete, seasoned ultra-bike racer
      and FKT holder, and I've spent over a decade coaching athletes from complete beginners
      to world-tour level professionals.</p>
    </div>
    <figure class="about-hero-portrait">{img("tom-portrait")}
      <figcaption>Tom Cooling, founder and head coach of Horsepower Coaching</figcaption></figure>
  </div>
</section>

<section>
  <div class="wrap content-grid two about-grid">
    <div class="prose">
      <h2>Coaching experience</h2>
      <p>I've spent over a decade coaching athletes from complete beginners to
      world-tour level professionals, and taken them to wins and podiums across Ironman,
      middle-distance triathlon, ultra-bike events and Haute Route-style races.</p>

      <h2>Where it comes from</h2>
      <p>It comes from my own racing, including FKT performances and ultra wins, from
      training alongside Royal Marines and UKSF, and from coaching elite performers. I
      know first-hand what the hard days actually take, and that goes into how I build
      and read every athlete's training.</p>

      <h2>Philosophy</h2>
      <p>I combine the evidence-based methods professional athletes rely on with practical,
      race-proven strategy, with a particular emphasis on female-specific performance
      development and durable, race-winning preparation. A single good block has never been
      the point. What matters is a whole athlete, prepared to hold up on the day it counts.</p>
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
      <div class="cred"><h3>Heat adaptation</h3><p>Accredited heat-training coach with applied experience in climate adaptation protocols.</p></div>
      <div class="cred"><h3>Extreme triathlon</h3><p>Core Temp and XTRI Extreme Triathlon Accredited Coach.</p></div>
      <div class="cred"><h3>Mountain leadership</h3><p>BMC (British Mountaineering Council) Trained and Assessed Mountain Leader.</p></div>
    </div>
  </div>
</section>

<section>
  <div class="wrap">
    <p class="eyebrow">Tom on the start line</p>
    <h2>Racing it, not just coaching it</h2>
    <p class="section-intro">The coaching is grounded in racing. Haute Route weeks in the Alps
    and the Dolomites, the Lost Dot TransPyrenees, the Brecon Titan: the same kind of
    preparation Horsepower athletes get, tested first-hand.</p>
    <div class="about-gallery">
      <figure class="photo-fig photo-fig--land">{img("about-brecon-titan")}
        <figcaption>Brecon Titan</figcaption></figure>
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
    <p class="section-intro">Start with a plan built for your race, get coached from
    £120 a month, or ask about a limited place with me directly.</p>
    <div class="cta-row" style="margin-top:20px">
      <a class="btn" href="{BASE_PATH}/plans/">Browse plans</a>
      <a class="btn ghost" href="{BASE_PATH}/coached/">Get coached</a>
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
    return page("about", "About Tom Cooling | Founder and Head Coach | Horsepower Coaching",
                desc, prod_url("/about/"), body,
                og_image_name="about-brecon-titan", extra=extra)


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
     "lines": ["Ironman Wales 2025 champion",
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
     "lines": ["Outlaw Half Triathlon 2026 - age group winner"]},
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
      <a class="btn" href="{BASE_PATH}/coached/">Get coached</a>
      <a class="btn on-dark ghost" href="#female-plans">See the plans</a>
    </div>
  </div>
</section>

<section>
  <div class="wrap prose">
    <h2>Why "female adapted" fails</h2>
    <p>Most training plans, most research and most coaching were built around the male
    athlete, then shrunk to fit everyone else. Women got trained as small men. That ignores
    what actually shapes how a female athlete responds to training: how you recover, how you
    fuel, the strength work that protects your bones and tendons, and how load is best spread
    across your week. Turning a men's plan down isn't the same as building the right one.</p>
    <h2>What female first actually means</h2>
    <p>Female first means the plan starts from the female athlete rather than a template. It
    means recovery-respecting structure so the work lands instead of grinding you down, and
    strength work built in for long-term bone and tendon health rather than bolted on as an
    afterthought. And it means I'm honest about what each level of support can and can't do.</p>
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
      <p style="margin-top:16px">I'm honest about the limits: coaching is personalised week to
      week, and I'll never overclaim what it does. I coach with a particular emphasis on
      female-specific performance development, built from years of working with female athletes
      from first finish lines to the front of the race.</p>
      <p style="margin-top:20px">
        <a class="btn" href="{BASE_PATH}/coached/">How coaching works</a>
        <a class="btn ghost" href="{BASE_PATH}/coaching/" style="margin-left:10px">Coached by Tom</a>
      </p>
    </div>
  </div>
</section>

<section class="female-honours">
  <div class="wrap">
    <p class="eyebrow">The women who prove it</p>
    <h2>Real names, real results</h2>
    <p style="color:var(--teal-soft);font-family:'Oswald',sans-serif;font-size:1.15rem;letter-spacing:0.04em;margin:6px 0 14px">Female results, not female participation.</p>
    <p class="section-intro" style="color:#CFCFCF">These are women I coach, not stock-photo athletes.
    Two of them, Hannah S and Madison S, have won Ironman Wales outright, and every line below comes
    straight from their race results.</p>
    <div class="honours-grid">{"".join(
      f'<div class="honour">'
      f'<div class="honour-media">{img(h["img"])}</div>'
      f'<div class="honour-body"><h3 class="honour-name">{esc(h["name"])}</h3>'
      f'<ul class="honour-stats">{"".join(f"<li>{esc(l)}</li>" for l in h["lines"])}</ul>'
      f'</div></div>' for h in FEMALE_HONOURS)}</div>
  </div>
</section>
{carousel("female", subhead="In her words", include_result=False, on_dark=False, more_state=True)}
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
    desc = ("Female-first triathlon, cycling and running coaching and training plans, built "
            "for female athletes with cycle-aware coaching. Female first, not female adapted.")
    return page("female",
                "Female Performance Coaching | Female-Specific Triathlon, Cycling and Running Training | Horsepower Coaching",
                desc, prod_url("/female-performance/"), body,
                og_image_name="female-hero", extra=extra)


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
                prod_url("/options/"), body, og_image_name="hero-alpine-mist", extra=extra)


# ── Contact (WS-SITE13) ──────────────────────────────────────────────────────
# A real on-site contact page. Channels are reused from the footer (WhatsApp,
# Instagram, Google reviews); no email address is invented because the footer
# does not carry one. The form is a plain Netlify Forms form: a static POST with
# a hidden form-name field and a honeypot, so it works on Netlify with no backend.
def render_contact(cat) -> str:
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
    <div>
      <h2>Talk to me directly</h2>
      <ul class="contact-channels">
        <li><a href="{WHATSAPP_URL}" rel="noopener" target="_blank">
          <span class="ch-icon">{SVG_WA}</span>
          <span class="ch-body"><strong>WhatsApp</strong><span>+44 7780 008724</span></span></a></li>
        <li><a href="{INSTAGRAM_URL}" rel="noopener" target="_blank">
          <span class="ch-icon">{SVG_IG}</span>
          <span class="ch-body"><strong>Instagram</strong><span>@horsepower.coaching</span></span></a></li>
        <li><a href="{esc(GOOGLE_REVIEW_URL)}" rel="noopener" target="_blank">
          <span class="ch-icon">{SVG_FB}</span>
          <span class="ch-body"><strong>Reviews</strong><span>Read {REVIEW_COUNT} reviews on Google</span></span></a></li>
      </ul>
      <p style="color:var(--grey-mid);margin-top:22px">Based in Clevedon, coaching athletes
      across the UK and online worldwide.</p>
    </div>
    <div>
      <h2>Send me a message</h2>
      <form name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field" class="contact-form" action="{BASE_PATH}/contact/">
        <input type="hidden" name="form-name" value="contact">
        <p class="hp-field"><label>Leave this field empty if you're human <input name="bot-field"></label></p>
        <div class="field"><label for="c-name">Your name</label>
          <input id="c-name" name="name" type="text" autocomplete="name" required></div>
        <div class="field"><label for="c-email">Your email</label>
          <input id="c-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="c-event">Your target event (optional)</label>
          <input id="c-event" name="event" type="text"></div>
        <div class="field"><label for="c-message">Your message</label>
          <textarea id="c-message" name="message" rows="6" required></textarea></div>
        <button class="btn" type="submit">Send message</button>
      </form>
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
                og_image_name="coached-tom-dolomites-arch", extra=extra)


# ── Sport coaching landing pages (WS-SITE13, SEO retention) ──────────────────
# Thin, keyword-strong entry points matching the old GoDaddy /triathlon-coaching
# and /cycling-coaching URLs (the _redirects map sends the old no-slash URLs
# here). Each targets its head term + Clevedon/UK, then funnels to the three
# tiers. Not a duplicate of the tiers page; a focused door in.
def _funnel_cards():
    tiers = [
        (TIER1_NAME, "From &pound;39.99, one-off", SUPPORT_LEVELS[0][1], "/plans/", "Browse the plans"),
        (TIER2_NAME, "&pound;120 a month", SUPPORT_LEVELS[1][1], "/coached/", "How it works"),
        ("Coached by Tom", "&pound;185 a month", SUPPORT_LEVELS[2][1], "/coaching/", "See if there's a place"),
    ]
    cards = []
    for i, (name, price, support, path, cta) in enumerate(tiers):
        feat = " feature" if i == 1 else ""
        cards.append(
            f'<div class="tier-card{feat}"><h3>{esc(name)}</h3>'
            f'<div class="price">{price}</div>'
            f'<p class="support-line"><span class="support-tag">Support: {esc(support)}</span></p>'
            f'<a class="btn" href="{BASE_PATH}{path}">{esc(cta)}</a></div>')
    return "".join(cards)


def render_sport_landing(*, slug, h1, eyebrow, hero_img, og_name, title, desc,
                         lede, intro_html, funnel_heading, service_name, service_desc) -> str:
    body = f"""<main id="main">
<section class="hero hero--image">
  {img(hero_img, cls="hero-bg", lazy=False)}
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">{esc(eyebrow)}</p>
    <h1>{esc(h1)}</h1>
    <p class="lede">{esc(lede)}</p>
    <div class="cta-row">
      <a class="btn" href="{BASE_PATH}/plans/">Find your plan</a>
      <a class="btn on-dark ghost" href="{BASE_PATH}/coached/">Get coached</a>
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
                og_image_name=og_name, extra=extra)


def render_triathlon_coaching(cat) -> str:
    intro = (
        "<h2>Triathlon coaching for every distance</h2>"
        "<p>I'm Tom Cooling, and I coach triathletes from a first sprint or super-sprint all the "
        "way to Ironman, long course and the extreme XTRI races. Whether you are chasing a first "
        "70.3 finish or a podium at Ironman Wales, triathlon coaching with Horsepower is built "
        "around your target race, your life and your numbers, from Clevedon and online worldwide.</p>"
        "<p>Every plan is written by me, delivered through TrainingPeaks, and built in three-week "
        "blocks so the load lands and the hard sessions are dosed the way the research says fitness "
        "is actually built. Swim, bike, run and the transitions between them, prepared properly.</p>")
    return render_sport_landing(
        slug="triathlon-coaching",
        h1="Triathlon Coaching",
        eyebrow="Triathlon coaching, Clevedon and online",
        hero_img="hero-tenby-swim", og_name="hero-tenby-swim",
        title="Triathlon Coaching | Clevedon and Online, UK | Horsepower Coaching",
        desc=("Triathlon coaching for every distance, from first sprint to Ironman, based in "
              "Clevedon, UK and online worldwide. Bespoke plans and coaching by Tom Cooling."),
        lede=("Triathlon coaching built for your race, from your first sprint to Ironman. Written "
              "by me, delivered through TrainingPeaks, based in Clevedon and coaching worldwide."),
        intro_html=intro,
        funnel_heading="Your paths into triathlon coaching",
        service_name="Triathlon coaching",
        service_desc=("Triathlon coaching and training plans for every distance, from first sprint "
                      "and 70.3 to Ironman and XTRI, built for your target race by Tom Cooling. "
                      "Based in Clevedon, UK; coaching online worldwide."))


def render_cycling_coaching(cat) -> str:
    intro = (
        "<h2>Cycling coaching from sportives to ultra-distance</h2>"
        "<p>I coach cyclists from first sportives and hill climbs to 100 mile time trials, "
        "gran fondos and ultra-distance racing. Cycling coaching with Horsepower is built around "
        "the event you are targeting, your available hours and your own power numbers, from "
        "Clevedon and online across the UK and worldwide.</p>"
        "<p>Every plan is written by me and delivered through TrainingPeaks, with the load built "
        "in three-week blocks and every target set as a percentage of your own numbers so it fits "
        "you, not an average. Climbing, time trialling, endurance and the race craft that goes "
        "with them.</p>")
    return render_sport_landing(
        slug="cycling-coaching",
        h1="Cycling Coaching",
        eyebrow="Cycling coaching, Clevedon and online",
        hero_img="alpine-ridge", og_name="alpine-ridge",
        title="Cycling Coaching | Clevedon and Online, UK | Horsepower Coaching",
        desc=("Cycling coaching from sportives and hill climbs to 100 mile time trials and "
              "ultra-distance racing, based in Clevedon, UK and online. Coaching by Tom Cooling."),
        lede=("Cycling coaching built for your event, from sportives and hill climbs to 100 mile "
              "TTs and ultra racing. Written by me and delivered through TrainingPeaks."),
        intro_html=intro,
        funnel_heading="Your paths into cycling coaching",
        service_name="Cycling coaching",
        service_desc=("Cycling coaching and training plans from sportives and hill climbs to 100 "
                      "mile time trials and ultra-distance racing, built for your target event by "
                      "Tom Cooling. Based in Clevedon, UK; coaching online worldwide."))


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


def render_blog_index(posts):
    cards = []
    for p in posts:
        url = f'{BASE_PATH}/blog/f/{p["slug"]}/'
        cards.append(
            f'<article class="blog-card">'
            f'<p class="blog-date"><time datetime="{esc(p["date"])}">{esc(human_date(p["date"]))}</time></p>'
            f'<h2 class="blog-card-title"><a href="{url}">{esc(p["title"])}</a></h2>'
            f'<p class="blog-excerpt">{esc(p.get("description", ""))}</p>'
            f'<p><a class="link-plain" href="{url}">Read the post &rarr;</a></p>'
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
             "author": {"@type": "Person", "name": "Tom Cooling"}}
            for p in posts],
    }
    extra = ld_script([breadcrumb_node([("Home", "/"), ("Blog", None)]), blog_ld])
    return page("blog", "Blog | Horsepower Coaching", desc, prod_url("/blog/"), body,
                og_image_name="hero-welsh-climb", extra=extra)


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
<section>
  <article class="wrap prose blog-prose">
    {p["body_html"]}
    <hr class="blog-rule">
    <p><a class="link-plain" href="{BASE_PATH}/blog/">&larr; Back to the blog</a></p>
    <div class="callout" style="margin-top:30px">
      <p class="eyebrow" style="color:var(--teal-soft)">Train with Horsepower</p>
      <p>If that is how you like your coaching, straight and built for your race, take a look at the
      <a class="link-plain on-dark" href="{BASE_PATH}/plans/">training plans</a> or see
      <a class="link-plain on-dark" href="{BASE_PATH}/coached/">how coaching works</a>.</p>
    </div>
  </article>
</section>
</main>"""
    desc = (p.get("description", "") or p["title"]).strip()
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "..."
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": p["title"], "description": desc,
        "url": canonical, "mainEntityOfPage": canonical,
        "datePublished": p.get("datetime") or p["date"],
        "dateModified": p.get("datetime") or p["date"],
        "author": {"@type": "Person", "name": "Tom Cooling", "url": prod_url("/about/")},
        "publisher": {"@type": "Organization", "name": SITE_NAME,
                      "logo": {"@type": "ImageObject", "url": OG_LOGO}},
        "image": og_image_url(DEFAULT_OG_IMAGE),
        "inLanguage": "en-GB",
    }
    crumbs = breadcrumb_node([("Home", "/"), ("Blog", "/blog/"), (p["title"], None)])
    extra = ld_script([ld, crumbs])
    return page("blog", f'{p["title"]} | Horsepower Coaching', desc, canonical, body,
                og_image_name=DEFAULT_OG_IMAGE, og_type="article", extra=extra)


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
                  ("/contact/", "monthly", "0.5")]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, cf, pr in main_pages:
        sm.append(sm_entry(prod_url(path), cf, pr))
    for p in plans:
        sm.append(sm_entry(prod_url(f"/plans/{p['slug']}/"), "monthly", "0.7"))
    for post in posts:
        sm.append(sm_entry(prod_url(f"/blog/f/{post['slug']}/"), "monthly", "0.6"))
    sm.append("</urlset>")
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
          "# Triathlon, cycling and endurance coaching | Clevedon, UK + online worldwide",
          "",
          "User-agent: *",
          "Allow: /",
          "Disallow: /options/",
          ""]
    for bot in ai_bots:
        rb += [f"User-agent: {bot}", "Allow: /", "Disallow: /options/", ""]
    rb += [f"Sitemap: {prod_url('/sitemap.xml')}", ""]
    write("robots.txt", "\n".join(rb), written)

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
    redirects.append("")
    write("_redirects", "\n".join(redirects), written)

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

    # Gate 11: robots.txt allows the major AI crawlers, disallows /options/,
    # and references the sitemap.
    robots = written.get("robots.txt", "")
    for bot in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "anthropic-ai", "PerplexityBot",
                "Google-Extended", "CCBot", "Applebot-Extended", "Bytespider"):
        if bot not in robots:
            errors.append(f"robots.txt missing required AI crawler allow: {bot}")
    if "Disallow: /options/" not in robots:
        errors.append("robots.txt missing 'Disallow: /options/'")
    if "Sitemap:" not in robots:
        errors.append("robots.txt missing Sitemap reference")

    # Gate 12: sitemap uses the prod host and never lists /options/.
    smx = written.get("sitemap.xml", "")
    if PROD_ORIGIN not in smx:
        errors.append("sitemap.xml not using production host")
    if BASE_URL in smx:
        errors.append("sitemap.xml still references the github.io preview host")
    if "/options/" in smx:
        errors.append("sitemap.xml must not list /options/")

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
    print(f"  - zero client surnames across all generated output (first name + initial policy)")
    ld_total = sum(len(re.findall(r'application/ld\+json', v)) for v in html_pages.values())
    print(f"  - SEO/AEO: 1 h1 + canonical(prod host) + OG/Twitter + parsing JSON-LD per page "
          f"({ld_total} JSON-LD blocks total)")
    print(f"  - robots.txt: {len([l for l in written['robots.txt'].splitlines() if l.startswith('User-agent:')])} "
          f"user-agent groups incl. AI crawlers; /options/ disallowed; sitemap referenced")
    print(f"  - sitemap.xml: {written['sitemap.xml'].count('<url>')} URLs on prod host, /options/ excluded")


if __name__ == "__main__":
    build()

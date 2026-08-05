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
    ("Plans", BASE_PATH + "/plans/", "plans"),
    ("Coached", BASE_PATH + "/coached/", "coached"),
    ("Coached by Tom", BASE_PATH + "/coaching/", "coaching"),
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
        <img src="{BASE_PATH}/assets/logo-white.png" alt="Horsepower Coaching" width="2041" height="803">
        <p>Training plans and coaching built for your race, at the right dose, adjusted when life happens.</p>
      </div>
      <div>
        <h4>Train with us</h4>
        <ul>
          <li><a href="{BASE_PATH}/plans/">Plans</a></li>
          <li><a href="{BASE_PATH}/coached/">Coached</a></li>
          <li><a href="{BASE_PATH}/coaching/">Coached by Tom</a></li>
          <li><a href="{BASE_PATH}/about/">About Tom</a></li>
          <li><a href="{esc(CONTACT_URL)}">Contact</a></li>
        </ul>
      </div>
      <div>
        <h4>More from Horsepower</h4>
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
</body>
</html>"""


def page(active, title, description, canonical, body, extra="") -> str:
    return head(title, description, canonical, extra) + header(active) + body + footer()


# ── Pages ────────────────────────────────────────────────────────────────────
def render_home(cat) -> str:
    total = cat["stats"]["total"]
    body = f"""<main id="main">
<section class="hero">
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
        <h3>Coached</h3>
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

<section class="results">
  <div class="wrap">
    <p>{esc(RESULTS_LINE)}</p>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <p class="eyebrow">Which one am I?</p>
    <div class="which-grid">
      <div class="which-item"><strong>Plans</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>Coached</strong>{esc(WHICH_COACHED)}</div>
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
    return page("home", "Horsepower Coaching | Training plans and coaching for your race",
                desc, BASE_URL + "/", body)


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
    <a href="{BASE_PATH}/coached/">See Coached</a>.</p>
  </div>
</section>
</main>"""
    desc = (p["blurb"][:150]).rsplit(" ", 1)[0]
    return page("plans", f"{p['title']} | Horsepower Coaching", desc, canonical, body, extra)


def render_coached(cat) -> str:
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 64px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Coached &middot; &pound;85 a month</p>
    <h1>Your race, your hours, your plan</h1>
    <p class="lede">{esc(COACHED_INTRO)}</p>
    <div class="cta-row"><a class="btn" href="{esc(CONTACT_URL)}">Apply for coaching</a></div>
  </div>
</section>

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
</main>"""
    desc = ("Coached by Horsepower, £85 a month. Your race, your hours, your plan, "
            "built block by block with real feedback on every session and a race "
            "plan before every start line.")
    return page("coached", "Coached | £85 a month | Horsepower Coaching", desc,
                BASE_URL + "/coached/", body)


def render_coaching(cat) -> str:
    body = f"""<main id="main">
<section class="hero" style="padding:60px 0 64px">
  <div class="wrap">
    <p class="eyebrow" style="color:var(--teal-soft)">Coached by Tom &middot; Limited places</p>
    <h1>A coach in your corner for all of it</h1>
    <p class="lede">{esc(TIER_TOM_BODY)}</p>
    <div class="cta-row"><a class="btn" href="{esc(CONTACT_URL)}">Ask about a place</a></div>
  </div>
</section>

<section>
  <div class="wrap content-grid two">
    <div>
      <h2>Everything in Coached, plus Tom</h2>
      <p>You get the full Coached service: your programme built block by block around
      your life and your event, feedback on every session you complete, and a race
      plan before every start line. On top of that you get Tom directly.</p>
      <ul class="about-list">
        <li>Calls when you need them, not on a fixed schedule you have to fill.</li>
        <li>WhatsApp when it is urgent, the day before a race or the morning of.</li>
        <li>Race-day strategy built together, not handed over.</li>
        <li>A coach who knows your story, not just your data.</li>
      </ul>
    </div>
    <div>
      <div class="callout">
        <h2>Why places are limited</h2>
        <p>I keep this group small on purpose. If we are going to do it, we do it
        properly, and that means I can only take on so many athletes at this level at
        once. When it is full, it is full.</p>
        <p style="margin-top:18px"><a class="btn on-dark ghost" href="{esc(CONTACT_URL)}">Ask about a place</a></p>
      </div>
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <h2>Not sure which tier?</h2>
    <div class="which-grid">
      <div class="which-item"><strong>Plans</strong>{esc(WHICH_PLANS)}</div>
      <div class="which-item"><strong>Coached</strong>{esc(WHICH_COACHED)}</div>
      <div class="which-item"><strong>Coached by Tom</strong>{esc(WHICH_TOM)}</div>
    </div>
  </div>
</section>
</main>"""
    desc = ("Coached by Tom, limited places. Everything in Coached plus Tom directly: "
            "calls when you need them, WhatsApp when it is urgent, and race-day "
            "strategy built together.")
    return page("coaching", "Coached by Tom | Limited places | Horsepower Coaching", desc,
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
  <div class="wrap content-grid two">
    <div class="prose">
      <h2>Coaching experience</h2>
      <p>Tom has spent over a decade coaching athletes from complete beginners to
      world-tour level professionals, and has guided competitors to wins and podiums
      across Ironman, middle-distance triathlon, ultra-bike events and Haute
      Route-style races.</p>

      <h2>Philosophy</h2>
      <p>His coaching combines evidence-based methodologies valued by professional
      athletes with practical, race-proven strategies, with a particular emphasis on
      female-specific performance development and durable, race-winning preparation.</p>

      <h2>Where the expertise comes from</h2>
      <p>That expertise is drawn from personal racing, including FKT performances and
      ultra wins, training with Royal Marines and UKSF, and coaching elite performers.</p>
    </div>
    <div>
      <div class="callout" style="background:var(--grey-bg);color:var(--black)">
        <h2 style="color:var(--black)">Qualifications</h2>
        <ul class="about-list">
          <li>First Class BA and Master's Degree in Sport Science &amp; Athlete Development.</li>
          <li>Oxygen Advantage Advanced Breathwork Instructor qualification.</li>
          <li>Accredited heat-training coach with applied experience in climate adaptation protocols.</li>
        </ul>
      </div>
    </div>
  </div>
</section>

<section class="alt">
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
</main>"""
    desc = ("Tom Cooling is an ex-elite triathlete, ultra-bike racer and FKT holder "
            "with over a decade coaching beginners to world-tour professionals across "
            "triathlon, ultra-bike and Haute Route racing.")
    return page("about", "About Tom Cooling | Horsepower Coaching", desc,
                BASE_URL + "/about/", body)


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

    # assets
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(SITE, "assets"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    written = {}
    write("index.html", render_home(cat), written)
    write("plans/index.html", render_plans_index(cat), written)
    write("coached/index.html", render_coached(cat), written)
    write("coaching/index.html", render_coaching(cat), written)
    write("about/index.html", render_about(cat), written)
    for p in plans:
        write(f"plans/{p['slug']}/index.html", render_plan_detail(cat, p), written)

    # sitemap + robots
    urls = [BASE_URL + "/", BASE_URL + "/plans/", BASE_URL + "/coached/",
            BASE_URL + "/coaching/", BASE_URL + "/about/"]
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


if __name__ == "__main__":
    build()

# SEO + AI-crawlability comparison: current GoDaddy site vs new Netlify build, ranked

Cold, evidence-cited audit. 2026-08-14. Read-only: no site changes were made. Method: raw HTML
with no JavaScript execution (what most AI crawlers and non-JS renderers see), per
`website-builder/METHOD.md` and `tools/audit_site.py`. Every number below was fetched live this
session via `curl` with UA `Mozilla/5.0 (compatible; site-audit/1.0)`.

- CURRENT: https://horsepowercoaching.co.uk (GoDaddy builder, live) - 26 real URLs crawled (13
 website pages + 13 blog posts; `sitemap.ols.xml` store map is itself a 404, `sitemap.ola.xml`
 lists only the homepage).
- NEW: https://horsepower-coaching.netlify.app (the rebuild) - 180 URLs from its sitemap, crawled
 on the Netlify host (canonical/og/sitemap emit the production origin `horsepowercoaching.co.uk`,
 which is correct-by-design for cutover, not an error).

---

## Executive summary (30-second read)

1. **NEW wins decisively and on every category: weighted 104 vs 46 (of 120), unweighted 8.5 vs
 3.3 out of 10.** It is not close on the two categories that carry the commercial risk (content
 depth, authority preservation).
2. **Authority will be preserved. You will not lose page authority at cutover** - same domain,
 every one of the 25 old URLs has a live-verified 301, blog slugs unchanged, head terms kept at
 `/triathlon-coaching/` and `/cycling-coaching/`. Zero uncovered URLs. Evidence chain below.
3. **The single biggest lift is content the crawler can actually read.** CURRENT's blog posts
 expose ~98 words each in raw HTML (the body is JavaScript-rendered); the NEW equivalents
 expose 800-2,140. CURRENT ships **zero** structured data sitewide; NEW ships parseable
 `Product` (153), `LocalBusiness`, `BlogPosting`, `FAQPage` and more.
4. **CURRENT beats NEW in exactly two narrow places, both fixable pre-cutover:** (a) CURRENT
 publishes an `llms.txt` (HTTP 200); NEW returns **404** - and the cutover runbook's own
 `verify_cutover.py` checks for it, so it will fail verification. (b) CURRENT's head-term
 coaching pages carry slightly more body prose (`/triathlon-coaching` 426 words vs NEW 318).
5. **No fabricated metrics here.** This is an on-page/technical read only. Live rank, traffic and
 Domain Authority are not measured or invented; **Google Search Console after cutover is the
 only ground truth for live positions** - resubmit the sitemap and watch Coverage/Performance.

---

## Ranked scorecard

Score 0-10 per category, each with one measured/quoted evidence citation. Categories 5 (content
depth) and 8 (authority preservation) carry the commercial risk and are weighted ×3; the rest ×1.

| # | Category | CURRENT | NEW | Winner | Evidence (measured/quoted live) |
|---|---|:--:|:--:|:--:|---|
| 1 | Technical metadata | 4 | 9 | **NEW** | Meta description present on **15/26** CURRENT pages, canonical on **13/26** (`/triathlon-coaching` has neither); NEW: title+description+canonical on **180/180**, exactly one H1 on every page of both. |
| 2 | Structured data | 1 | 9 | **NEW** | CURRENT: "pages with NO schema: **26**" - zero JSON-LD sitewide. NEW: `Product`×153, `BreadcrumbList`×179, `LocalBusiness`/`Service`/`SportsActivityLocation`×5, `BlogPosting`×17, `FAQPage`×2, `WebSite` - **0 unparseable blocks**. |
| 3 | Crawl/index surface (sitemap+robots+llms) | 4 | 8 | **NEW** | CURRENT robots.txt is bare `User-agent: *` with **no Sitemap line and no AI crawler named**; `sitemap.ols.xml` is a 404. NEW robots names **20** agents (GPTBot…YouBot) + `Sitemap:`. But **CURRENT has `/llms.txt` (200); NEW returns 404** - the one signal CURRENT wins here. |
| 4 | AI-answer-engine readiness | 2 | 8 | **NEW** | CURRENT blog body is JS-rendered: raw HTML of `once-twice-three-times-an-ironman` = **98 words**, no schema. NEW same post = **2,109 words** + `BlogPosting`; homepage schema carries a `knowsAbout` entity list (triathlon, Ironman, heat acclimation, female-specific training…). Docked for the missing `llms.txt`. |
| 5 | Content depth & keyword coverage (**×3**) | 3 | 9 | **NEW** | CURRENT = **26 URLs**, one generic `/training-plans` page, median **101** crawlable words. NEW = **180 URLs incl. 153 race-specific plan pages** (long-tail: `challenge-roth-training-plan`, `ironman-wales-training-plan`, `utmb-mont-blanc-…`), median **336**, blog 800-2,140. |
| 6 | Page experience (speed proxies, mobile) | 4 | 9 | **NEW** | CURRENT avg HTML **114 KB** (homepage 151 KB), **52** external non-first-party script `src`s (wsimg/GoDaddy), webp on only 4 pages, no font preload. NEW avg **14.8 KB**, **0** external scripts, webp + `rel=preload as=font` on **180/180**. Both: viewport set, no `maximum-scale`. |
| 7 | Local SEO | 1 | 7 | **NEW** | CURRENT: no `LocalBusiness`, no NAP in raw HTML (no "Clevedon", no postcode, no `ld+json` on `/contact-us`). NEW: `LocalBusiness`+`SportsActivityLocation` with `PostalAddress` + `areaServed` (Truro, Clevedon, Cornwall, SW England, UK, worldwide). Docked: locality inconsistency + no `geo`/`telephone` (see punch-list). |
| 8 | Authority preservation (**×3**) | 7 | 9 | **NEW** | CURRENT is the live indexed asset on an aged domain (scored on what exists), but much of its equity rides on domain+titles, not crawlable depth. NEW: **same domain**, all **25** old URLs 301 to a 200 target (verified live), blog slugs identical, head terms preserved, GSC sitemap step in the runbook. **Zero uncovered URLs.** |

**Unweighted mean: CURRENT 3.25 / NEW 8.5.**
**Weighted (cats 5 & 8 ×3, rest ×1; max 120): CURRENT 46 / NEW 104 (38% vs 87%).**

### Overall verdict
The NEW build is the higher performer by a wide margin on every axis a crawler or answer engine
measures. The commercial-risk categories are its strongest: it turns a 26-URL, schema-free,
JS-dependent brochure into a 180-URL, fully structured, race-targeted library that a non-JS
crawler reads in full. The only places CURRENT is ahead are the missing `llms.txt` and a little
more prose on two coaching pages - both closed before cutover with the punch-list below.

---

## Authority-preservation verdict: will Tom lose page authority at cutover?

**No - provided the cutover follows `docs/runbooks/dns-cutover.md`.** Evidence chain, each link
verified live this session against the Netlify host:

1. **Same registrable domain retained.** `horsepowercoaching.co.uk` stays; the change is
 DNS-only (runbook: apex A → `75.2.60.5`, www CNAME → Netlify; "TOUCH NOTHING ELSE… MX, TXT").
 Link equity attached to the domain does not move. NEW's `canonical`, `og:image` and sitemap
 already emit `https://horsepowercoaching.co.uk/…`, so nothing re-points at cutover.
2. **Every old URL has a live 301 to a live (200) target.** All 11 GoDaddy page URLs + `/blog` +
 13 blog posts = **25 redirects, every one returned HTTP 301** with the expected `Location`, and
 every destination returned **200** (tested on `horsepower-coaching.netlify.app` this session).
 Examples: `/training-plans → /plans/`, `/our-team → /about/`, `/blog/f/into-the-unknown →
 /blog/f/into-the-unknown/`.
3. **Blog path pattern is identical.** Old and new both use `/blog/f/<slug>`; slugs are unchanged,
 the 301 only appends the trailing slash. Ranking signals on those 13 posts transfer 1:1.
4. **Head-term pages preserved at their strongest slugs.** `/triathlon-coaching/` and
 `/cycling-coaching/` exist as 200 pages and receive the old no-slash URLs via 301, so the two
 commercial head terms keep their landing pages.
5. **GSC re-submission is in the runbook.** Post-cutover step 3: submit `…/sitemap.xml` and request
 indexing of `/`, `/triathlon-coaching/`, `/cycling-coaching/`, `/female-performance/`; step 2
 runs `verify_cutover.py` (checks apex/www 200s, the old-URL + blog redirects, robots/sitemap).

**Caveats (state plainly):**
- The 301s are proven on the `netlify.app` host today; they only protect the apex domain once DNS
 points at Netlify so the same `_redirects` apply on `horsepowercoaching.co.uk`. Runbook step 2
 re-verifies against the apex post-cutover - do not skip it.
- Expect a small position wobble in weeks 1-2, normal for a redirect migration; the runbook budgets
 4-8 weeks of GSC watch. **GSC is the only ground truth for live positions** - no position or
 traffic number in this document is measured or invented.

### Uncovered-URL residue
**None.** Every URL in every CURRENT sitemap is accounted for:

| CURRENT sitemap URL group | Count | Coverage | Verified |
|---|:--:|---|:--:|
| Website pages (`/triathlon-coaching`, `/our-team`, `/the-foundry`, …) | 11 | `_redirects` 301 → new equivalent | 301 live ✓ |
| `/blog` | 1 | 301 → `/blog/` | 301 live ✓ |
| Homepage `/` | 1 | same URL, 200 on new build | 200 live ✓ |
| Blog posts `/blog/f/<slug>` | 13 | `_redirects` 301 → `/blog/f/<slug>/` | 301 live ✓ |
| `sitemap.ols.xml` (store) | 0 | already a 404 on CURRENT; no live URLs to preserve | n/a |

All 26 live CURRENT URLs → covered. No orphaned old URL, no missing redirect.

---

## Punch-list: NEW-site gaps (ranked by impact; each with file + fix)

1. **[HIGH] `llms.txt` is missing (HTTP 404).** CURRENT serves one; the cutover runbook's
 `verify_cutover.py` checks `robots/sitemap/llms`, so cutover verification will fail on it.
 *Fix:* have `generator/build.py` emit `site/llms.txt` (core facts once, what's included/not,
 an explicit "price not published, do not infer" if applicable), per METHOD. This is the one
 category signal where CURRENT beats NEW.
2. **[HIGH] Location inconsistency (Truro vs Clevedon).** Homepage `LocalBusiness` description +
 `PostalAddress` say **"Based in Truro, Cornwall"**, but `robots.txt` header, the coaching-page
 titles ("Triathlon Coaching | **Clevedon** and Online, UK") and the retained Google Business
 Profile (runbook step 5, "Clevedon listing retained deliberately") say **Clevedon**.
 Contradictory NAP is the worst pattern for local SEO and LLM retrieval. *Fix:* pick one
 locality in the generator's location constant and make schema, titles, robots and GBP agree.
3. **[MEDIUM] 91 of 180 titles exceed ~60 characters** and will truncate in the SERP (avg title
 length 61, max 107). *Fix:* tighten plan-page title template in the generator toward ≤60 chars.
4. **[MEDIUM] 146 pages under 350 crawlable words; the 153 `Product` plan pages are templated at
 ~317-331 words with near-identical structure** (near-duplication risk). They still carry unique
 `Product` schema and race-specific naming, so they index - but depth is thin. *Fix:* inject
 per-race specifics (course profile, climbs, weather window, distances) into each plan body.
5. **[MEDIUM] Head-term coaching pages are lighter on prose than CURRENT.**
 `/triathlon-coaching/` = 318 words vs CURRENT's 426; `/cycling-coaching/` = 310. NEW wins
 overall via schema+metadata, but *add ~150 words* of unique copy to both to hold the head terms.
6. **[LOW-MED] `LocalBusiness` has no `geo` coordinates and no `telephone`/`email`.** *Fix:* add
 `geo` (lat/long from `api.postcodes.io`) and contact points once the locality is settled (#2).
7. **[LOW] 9 meta descriptions exceed 160 characters** (max 228) and will truncate. *Fix:* trim in
 the generator's description template.
8. **[LOW] `/plans/` index is a single 206 KB / 8,546-word page.** Heavy but static and first-party;
 acceptable, consider sectioned lazy reveal if it grows.
9. **[LOW] `FAQPage` schema appears on only 2 pages.** *Fix:* extend FAQ blocks to the coaching and
 top plan pages to win "how do I train for…" answer-engine queries.
10. **[VERIFY] canonical/og/sitemap emit the production origin.** Correct-by-design pre-cutover, but
 they only resolve once DNS is live - re-run `verify_cutover.py` against the apex after cutover.

---

## Appendix A - per-page tables

Columns: Words (raw HTML, scripts/styles stripped) · KB (HTML weight) · H1 (count) · Img/noalt
(images / missing alt) · Desc(len) (meta description present + length) · Canon (canonical present)
· Schema (JSON-LD @types) · Title. `**bold**` marks a flagged/absent value.

### CURRENT per-page (horsepowercoaching.co.uk) - 26 URLs

| URL | Words | KB | H1 | Img/noalt | Desc(len) | Canon | Schema | Title |
|---|--:|--:|--:|--:|:--:|:--:|---|---|
| `/` | 606 | 151 | 1 | 4/2 | Y(146) | **N** | **none** | Horsepower Coaching - Triathlon Coach, Cycling Coach |
| `/triathlon-coaching` | 426 | 108 | 1 | 3/1 | **N**(0) | **N** | **none** | Triathlon Coaching |
| `/cycling-coaching` | 423 | 108 | 1 | 3/1 | **N**(0) | **N** | **none** | Cycling Coaching |
| `/equality-development-1` | 220 | 82 | 1 | 3/1 | **N**(0) | **N** | **none** | Equality Development |
| `/training-plans` | 311 | 113 | 1 | 3/1 | **N**(0) | **N** | **none** | Training Plans |
| `/performance-breathwork` | 530 | 117 | 1 | 7/5 | **N**(0) | **N** | **none** | Performance Breathwork |
| `/our-team` | 313 | 103 | 1 | 3/1 | **N**(0) | **N** | **none** | Our Team |
| `/achievements` | 89 | 74 | 1 | 2/0 | **N**(0) | **N** | **none** | Achievements |
| `/alps-training-camp` | 667 | 122 | 1 | 8/6 | **N**(0) | **N** | **none** | Alps Training Camp / Horsepower Coaching |
| `/bespoke-wheelbuilding` | 452 | 146 | 1 | 23/20 | Y(59) | **N** | **none** | Bespoke Wheelbuilding |
| `/the-foundry` | 402 | 131 | 1 | 12/7 | **N**(0) | **N** | **none** | The Foundry |
| `/contact-us` | 145 | 111 | 1 | 3/1 | **N**(0) | **N** | **none** | Horsepower Coaching |
| `/blog` | 94 | 92 | 1 | 2/0 | **N**(0) | **N** | **none** | Horsepower Coaching |
| `/blog/f/how-to-improve-your-triathlon-swim` | 98 | 127 | 1 | 2/0 | Y(27) | Y | **none** | How to Improve Your Triathlon Swim |
| `/blog/f/my-triathlon-top-tips` | 96 | 121 | 1 | 2/0 | Y(220) | Y | **none** | My Triathlon Top Tips |
| `/blog/f/the-lightest-disc-brake-bike` | 97 | 121 | 1 | 2/0 | Y(9) | Y | **none** | The Lightest Disc Brake Bike??? |
| `/blog/f/how-not-to-coach---the-art-of-listening` | 101 | 110 | 1 | 2/0 | Y(139) | Y | **none** | How Not to Coach - The Art of Listening |
| `/blog/f/plastic-pollution-triathlon` | 103 | 116 | 1 | 2/0 | Y(24) | Y | **none** | Plastic Plastic Plastic - A Story About Sport &#x26; Plastic |
| `/blog/f/psychology---use-your-head` | 97 | 119 | 1 | 2/0 | Y(228) | Y | **none** | Psychology - Use Your Head |
| `/blog/f/2017-season-wrapup---calm-after-the-storm` | 100 | 112 | 1 | 2/0 | Y(66) | Y | **none** | 2017 Season Wrapup - Calm After The Storm |
| `/blog/f/once-twice-three-times-an-ironman` | 98 | 114 | 1 | 2/0 | Y(83) | Y | **none** | Once, Twice, Three Times an Ironman |
| `/blog/f/ironman-wales---enter-the-dragon` | 98 | 103 | 1 | 2/0 | Y(96) | Y | **none** | Ironman Wales - Enter The Dragon |
| `/blog/f/tits-up---how-to-deal-with-failure` | 100 | 113 | 1 | 2/0 | Y(67) | Y | **none** | Tits Up - How to Deal with Failure |
| `/blog/f/everesting---climbing-the-mountain` | 97 | 112 | 1 | 2/0 | Y(220) | Y | **none** | Everesting - Climbing The Mountain |
| `/blog/f/into-the-unknown` | 98 | 118 | 1 | 2/0 | Y(223) | Y | **none** | First Ironman - Into The Unknown |
| `/blog/f/our-origins---a-little-bit-of-history` | 99 | 108 | 1 | 2/0 | Y(230) | Y | **none** | Origins - A Little Bit of History |

### NEW per-page (horsepower-coaching.netlify.app) - 180 URLs

| URL | Words | KB | H1 | Img/noalt | Desc(len) | Canon | Schema | Title |
|---|--:|--:|--:|--:|:--:|:--:|---|---|
| `/` | 802 | 20 | 1 | 5/0 | Y(121) | Y | LocalBusiness, SportsActivityLocation, WebSite | Horsepower Coaching / Training plans and coaching for your r |
| `/plans/` | 8546 | 206 | 1 | 3/0 | Y(136) | Y | BreadcrumbList, CollectionPage, Service | Training Plan Library / 153 plans built for your race / Hors |
| `/female-performance/` | 1215 | 25 | 1 | 8/0 | Y(159) | Y | BreadcrumbList, FAQPage | Female Performance Coaching / Female-Specific Triathlon, Cyc |
| `/triathlon-coaching/` | 318 | 13 | 1 | 3/0 | Y(155) | Y | BreadcrumbList, LocalBusiness, Service, SportsActivityLocation | Triathlon Coaching / Clevedon and Online, UK / Horsepower Co |
| `/cycling-coaching/` | 310 | 13 | 1 | 3/0 | Y(157) | Y | BreadcrumbList, LocalBusiness, Service, SportsActivityLocation | Cycling Coaching / Clevedon and Online, UK / Horsepower Coac |
| `/coached/` | 709 | 17 | 1 | 5/0 | Y(142) | Y | BreadcrumbList, FAQPage, Service | Plan Only / £120 a month / Horsepower Coaching |
| `/coaching/` | 1263 | 69 | 1 | 6/0 | Y(145) | Y | BreadcrumbList, Service | Coached by Tom / £185 a month / Horsepower Coaching |
| `/about/` | 470 | 18 | 1 | 10/0 | Y(154) | Y | BreadcrumbList, LocalBusiness, Person, SportsActivityLocation | About Tom Cooling / Founder and Head Coach / Horsepower Coac |
| `/blog/` | 775 | 28 | 1 | 19/0 | Y(139) | Y | Blog, BreadcrumbList | Blog / Horsepower Coaching |
| `/contact/` | 187 | 14 | 1 | 3/0 | Y(157) | Y | BreadcrumbList, ContactPage, LocalBusiness, SportsActivityLocation | Contact / Horsepower Coaching |
| `/plans/challenge-roth-training-plan/` | 317 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Challenge Roth Training Plan / Horsepower Coaching |
| `/plans/ironman-lanzarote-training-plan/` | 317 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | IRONMAN Lanzarote Training Plan / Horsepower Coaching |
| `/plans/ironman-uk-bolton-training-plan/` | 321 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | IRONMAN UK Bolton Training Plan / Horsepower Coaching |
| `/plans/ironman-wales-training-plan/` | 317 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN Wales Training Plan / Horsepower Coaching |
| `/plans/norseman-xtreme-triathlon-training-plan/` | 321 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | Norseman Xtreme Triathlon Training Plan / Horsepower Coachin |
| `/plans/alpe-dhuez-long-distance-triathlon-training-plan/` | 331 | 12 | 1 | 2/0 | Y(154) | Y | BreadcrumbList, Product | Alpe d&#x27;Huez Long Distance Triathlon Training Plan / Hor |
| `/plans/ironman-70-3-edinburgh-training-plan/` | 323 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | IRONMAN 70.3 Edinburgh Training Plan / Horsepower Coaching |
| `/plans/ironman-70-3-staffordshire-training-plan/` | 323 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN 70.3 Staffordshire Training Plan / Horsepower Coachi |
| `/plans/ironman-70-3-weymouth-training-plan/` | 323 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | IRONMAN 70.3 Weymouth Training Plan / Horsepower Coaching |
| `/plans/17-week-middle-long-distance-triathlon-plan-intermediate/` | 329 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | 17 Week Middle/Long Distance Triathlon Plan (Intermediate) / |
| `/plans/etape-du-tour-training-plan/` | 324 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | Etape du Tour Training Plan / Horsepower Coaching |
| `/plans/la-marmotte-training-plan/` | 320 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | La Marmotte Training Plan / Horsepower Coaching |
| `/plans/maratona-dles-dolomites-training-plan/` | 324 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Maratona dles Dolomites Training Plan / Horsepower Coaching |
| `/plans/dirty-reiver-200-training-plan/` | 324 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Dirty Reiver 200 Training Plan / Horsepower Coaching |
| `/plans/mallorca-312-training-plan/` | 320 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | Mallorca 312 Training Plan / Horsepower Coaching |
| `/plans/haute-route-training-plan/` | 320 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | Haute Route Training Plan / Horsepower Coaching |
| `/plans/20-week-haute-route-gran-fondo-plan/` | 335 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | 20 Week Haute Route / Gran Fondo Plan / Horsepower Coaching |
| `/plans/ridelondon-surrey-100-training-plan/` | 320 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | RideLondon-Surrey 100 Training Plan / Horsepower Coaching |
| `/plans/the-gralloch-training-plan/` | 320 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | The Gralloch Training Plan / Horsepower Coaching |
| `/plans/horsepower-coaching-ultimate-winter-plan/` | 323 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Horsepower Coaching Ultimate Winter Plan / Horsepower Coachi |
| `/plans/edinburgh-marathon-training-plan/` | 315 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Edinburgh Marathon Training Plan / Horsepower Coaching |
| `/plans/london-marathon-training-plan/` | 315 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | London Marathon Training Plan / Horsepower Coaching |
| `/plans/manchester-marathon-training-plan/` | 315 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | Manchester Marathon Training Plan / Horsepower Coaching |
| `/plans/london-half-marathon-training-plan/` | 321 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | London Half Marathon Training Plan / Horsepower Coaching |
| `/plans/manchester-half-marathon-training-plan/` | 321 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Manchester Half Marathon Training Plan / Horsepower Coaching |
| `/plans/west-highland-way-race-training-plan/` | 323 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | West Highland Way Race Training Plan / Horsepower Coaching |
| `/plans/t100-pto-100km-triathlon-training-plan-finisher/` | 333 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | T100 PTO 100km Triathlon Training Plan - Finisher / Horsepow |
| `/plans/t100-pto-100km-triathlon-training-plan-performance/` | 332 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | T100 PTO 100km Triathlon Training Plan - Performance / Horse |
| `/plans/t100-pto-100km-triathlon-training-plan-competitive/` | 330 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | T100 PTO 100km Triathlon Training Plan - Competitive / Horse |
| `/plans/boston-marathon-training-plan-finisher/` | 322 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | Boston Marathon Training Plan - Finisher / Horsepower Coachi |
| `/plans/boston-marathon-training-plan-performance/` | 321 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Boston Marathon Training Plan - Performance / Horsepower Coa |
| `/plans/boston-marathon-training-plan-competitive/` | 319 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Boston Marathon Training Plan - Competitive / Horsepower Coa |
| `/plans/utmb-mont-blanc-training-plan-finisher/` | 322 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | UTMB Mont-Blanc Training Plan - Finisher / Horsepower Coachi |
| `/plans/utmb-mont-blanc-training-plan-performance/` | 321 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | UTMB Mont-Blanc Training Plan - Performance / Horsepower Coa |
| `/plans/utmb-mont-blanc-training-plan-competitive/` | 319 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | UTMB Mont-Blanc Training Plan - Competitive / Horsepower Coa |
| `/plans/200-mile-gravel-ultra-training-plan-finisher/` | 332 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | 200 Mile Gravel Ultra Training Plan - Finisher / Horsepower |
| `/plans/200-mile-gravel-ultra-training-plan-performance/` | 331 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | 200 Mile Gravel Ultra Training Plan - Performance / Horsepow |
| `/plans/200-mile-gravel-ultra-training-plan-competitive/` | 329 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | 200 Mile Gravel Ultra Training Plan - Competitive / Horsepow |
| `/plans/xcm-marathon-mountain-bike-training-plan-finisher/` | 330 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | XCM Marathon Mountain Bike Training Plan - Finisher / Horsep |
| `/plans/xcm-marathon-mountain-bike-training-plan-performance/` | 329 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | XCM Marathon Mountain Bike Training Plan - Performance / Hor |
| `/plans/xcm-marathon-mountain-bike-training-plan-competitive/` | 327 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | XCM Marathon Mountain Bike Training Plan - Competitive / Hor |
| `/plans/100-mile-trail-ultra-training-plan-finisher/` | 330 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | 100 Mile Trail Ultra Training Plan - Finisher / Horsepower C |
| `/plans/100-mile-trail-ultra-training-plan-performance/` | 329 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | 100 Mile Trail Ultra Training Plan - Performance / Horsepowe |
| `/plans/100-mile-trail-ultra-training-plan-competitive/` | 327 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | 100 Mile Trail Ultra Training Plan - Competitive / Horsepowe |
| `/plans/uk-hill-climb-training-plan/` | 321 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | UK Hill Climb Training Plan / Horsepower Coaching |
| `/plans/challenge-roth-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Challenge Roth Training Plan - Finish / Horsepower Coaching |
| `/plans/challenge-roth-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(138) | Y | BreadcrumbList, Product | Challenge Roth Training Plan - Improve / Horsepower Coaching |
| `/plans/challenge-roth-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Challenge Roth Training Plan - Compete / Horsepower Coaching |
| `/plans/ironman-lanzarote-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN Lanzarote Training Plan - Finish / Horsepower Coachi |
| `/plans/ironman-lanzarote-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(141) | Y | BreadcrumbList, Product | IRONMAN Lanzarote Training Plan - Improve / Horsepower Coach |
| `/plans/ironman-lanzarote-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN Lanzarote Training Plan - Compete / Horsepower Coach |
| `/plans/ironman-uk-bolton-training-plan-finish/` | 341 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN UK Bolton Training Plan - Finish / Horsepower Coachi |
| `/plans/ironman-uk-bolton-training-plan-improve/` | 333 | 12 | 1 | 2/0 | Y(141) | Y | BreadcrumbList, Product | IRONMAN UK Bolton Training Plan - Improve / Horsepower Coach |
| `/plans/ironman-uk-bolton-training-plan-compete/` | 337 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN UK Bolton Training Plan - Compete / Horsepower Coach |
| `/plans/ironman-wales-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN Wales Training Plan - Finish / Horsepower Coaching |
| `/plans/ironman-wales-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | IRONMAN Wales Training Plan - Improve / Horsepower Coaching |
| `/plans/ironman-wales-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN Wales Training Plan - Compete / Horsepower Coaching |
| `/plans/norseman-xtreme-triathlon-training-plan-finish/` | 341 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Norseman Xtreme Triathlon Training Plan - Finish / Horsepowe |
| `/plans/norseman-xtreme-triathlon-training-plan-improve/` | 333 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Norseman Xtreme Triathlon Training Plan - Improve / Horsepow |
| `/plans/norseman-xtreme-triathlon-training-plan-compete/` | 337 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Norseman Xtreme Triathlon Training Plan - Compete / Horsepow |
| `/plans/alpe-dhuez-long-distance-triathlon-training-plan-finish/` | 350 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Alpe d&#x27;Huez Long Distance Triathlon Training Plan - Fin |
| `/plans/alpe-dhuez-long-distance-triathlon-training-plan-improve/` | 342 | 12 | 1 | 2/0 | Y(152) | Y | BreadcrumbList, Product | Alpe d&#x27;Huez Long Distance Triathlon Training Plan - Imp |
| `/plans/alpe-dhuez-long-distance-triathlon-training-plan-compete/` | 346 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Alpe d&#x27;Huez Long Distance Triathlon Training Plan - Com |
| `/plans/ironman-70-3-edinburgh-training-plan-finish/` | 342 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | IRONMAN 70.3 Edinburgh Training Plan - Finish / Horsepower C |
| `/plans/ironman-70-3-edinburgh-training-plan-improve/` | 334 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN 70.3 Edinburgh Training Plan - Improve / Horsepower |
| `/plans/ironman-70-3-edinburgh-training-plan-compete/` | 338 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | IRONMAN 70.3 Edinburgh Training Plan - Compete / Horsepower |
| `/plans/ironman-70-3-staffordshire-training-plan-finish/` | 342 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | IRONMAN 70.3 Staffordshire Training Plan - Finish / Horsepow |
| `/plans/ironman-70-3-staffordshire-training-plan-improve/` | 334 | 12 | 1 | 2/0 | Y(141) | Y | BreadcrumbList, Product | IRONMAN 70.3 Staffordshire Training Plan - Improve / Horsepo |
| `/plans/ironman-70-3-staffordshire-training-plan-compete/` | 338 | 12 | 1 | 2/0 | Y(141) | Y | BreadcrumbList, Product | IRONMAN 70.3 Staffordshire Training Plan - Compete / Horsepo |
| `/plans/ironman-70-3-weymouth-training-plan-finish/` | 342 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | IRONMAN 70.3 Weymouth Training Plan - Finish / Horsepower Co |
| `/plans/ironman-70-3-weymouth-training-plan-improve/` | 334 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN 70.3 Weymouth Training Plan - Improve / Horsepower C |
| `/plans/ironman-70-3-weymouth-training-plan-compete/` | 338 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | IRONMAN 70.3 Weymouth Training Plan - Compete / Horsepower C |
| `/plans/etape-du-tour-training-plan-finish/` | 341 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Etape du Tour Training Plan - Finish / Horsepower Coaching |
| `/plans/etape-du-tour-training-plan-improve/` | 333 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Etape du Tour Training Plan - Improve / Horsepower Coaching |
| `/plans/etape-du-tour-training-plan-compete/` | 337 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Etape du Tour Training Plan - Compete / Horsepower Coaching |
| `/plans/la-marmotte-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | La Marmotte Training Plan - Finish / Horsepower Coaching |
| `/plans/la-marmotte-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | La Marmotte Training Plan - Improve / Horsepower Coaching |
| `/plans/la-marmotte-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | La Marmotte Training Plan - Compete / Horsepower Coaching |
| `/plans/maratona-dles-dolomites-training-plan-finish/` | 341 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Maratona dles Dolomites Training Plan - Finish / Horsepower |
| `/plans/maratona-dles-dolomites-training-plan-improve/` | 333 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Maratona dles Dolomites Training Plan - Improve / Horsepower |
| `/plans/maratona-dles-dolomites-training-plan-compete/` | 337 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Maratona dles Dolomites Training Plan - Compete / Horsepower |
| `/plans/dirty-reiver-200-training-plan-finish/` | 341 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Dirty Reiver 200 Training Plan - Finish / Horsepower Coachin |
| `/plans/dirty-reiver-200-training-plan-improve/` | 333 | 12 | 1 | 2/0 | Y(140) | Y | BreadcrumbList, Product | Dirty Reiver 200 Training Plan - Improve / Horsepower Coachi |
| `/plans/dirty-reiver-200-training-plan-compete/` | 337 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Dirty Reiver 200 Training Plan - Compete / Horsepower Coachi |
| `/plans/mallorca-312-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | Mallorca 312 Training Plan - Finish / Horsepower Coaching |
| `/plans/mallorca-312-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Mallorca 312 Training Plan - Improve / Horsepower Coaching |
| `/plans/mallorca-312-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Mallorca 312 Training Plan - Compete / Horsepower Coaching |
| `/plans/haute-route-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | Haute Route Training Plan - Finish / Horsepower Coaching |
| `/plans/haute-route-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Haute Route Training Plan - Improve / Horsepower Coaching |
| `/plans/haute-route-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Haute Route Training Plan - Compete / Horsepower Coaching |
| `/plans/ridelondon-surrey-100-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | RideLondon-Surrey 100 Training Plan - Finish / Horsepower Co |
| `/plans/ridelondon-surrey-100-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | RideLondon-Surrey 100 Training Plan - Improve / Horsepower C |
| `/plans/ridelondon-surrey-100-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | RideLondon-Surrey 100 Training Plan - Compete / Horsepower C |
| `/plans/the-gralloch-training-plan-finish/` | 337 | 12 | 1 | 2/0 | Y(144) | Y | BreadcrumbList, Product | The Gralloch Training Plan - Finish / Horsepower Coaching |
| `/plans/the-gralloch-training-plan-improve/` | 329 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | The Gralloch Training Plan - Improve / Horsepower Coaching |
| `/plans/the-gralloch-training-plan-compete/` | 333 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | The Gralloch Training Plan - Compete / Horsepower Coaching |
| `/plans/edinburgh-marathon-training-plan-finish/` | 335 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Edinburgh Marathon Training Plan - Finish / Horsepower Coach |
| `/plans/edinburgh-marathon-training-plan-improve/` | 327 | 12 | 1 | 2/0 | Y(141) | Y | BreadcrumbList, Product | Edinburgh Marathon Training Plan - Improve / Horsepower Coac |
| `/plans/edinburgh-marathon-training-plan-compete/` | 331 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Edinburgh Marathon Training Plan - Compete / Horsepower Coac |
| `/plans/london-marathon-training-plan-finish/` | 335 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | London Marathon Training Plan - Finish / Horsepower Coaching |
| `/plans/london-marathon-training-plan-improve/` | 327 | 12 | 1 | 2/0 | Y(138) | Y | BreadcrumbList, Product | London Marathon Training Plan - Improve / Horsepower Coachin |
| `/plans/london-marathon-training-plan-compete/` | 331 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | London Marathon Training Plan - Compete / Horsepower Coachin |
| `/plans/manchester-marathon-training-plan-finish/` | 335 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Manchester Marathon Training Plan - Finish / Horsepower Coac |
| `/plans/manchester-marathon-training-plan-improve/` | 327 | 12 | 1 | 2/0 | Y(142) | Y | BreadcrumbList, Product | Manchester Marathon Training Plan - Improve / Horsepower Coa |
| `/plans/manchester-marathon-training-plan-compete/` | 331 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Manchester Marathon Training Plan - Compete / Horsepower Coa |
| `/plans/london-half-marathon-training-plan-finish/` | 340 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | London Half Marathon Training Plan - Finish / Horsepower Coa |
| `/plans/london-half-marathon-training-plan-improve/` | 332 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | London Half Marathon Training Plan - Improve / Horsepower Co |
| `/plans/london-half-marathon-training-plan-compete/` | 336 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | London Half Marathon Training Plan - Compete / Horsepower Co |
| `/plans/manchester-half-marathon-training-plan-finish/` | 340 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Manchester Half Marathon Training Plan - Finish / Horsepower |
| `/plans/manchester-half-marathon-training-plan-improve/` | 332 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Manchester Half Marathon Training Plan - Improve / Horsepowe |
| `/plans/manchester-half-marathon-training-plan-compete/` | 336 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Manchester Half Marathon Training Plan - Compete / Horsepowe |
| `/plans/west-highland-way-race-training-plan-finish/` | 343 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | West Highland Way Race Training Plan - Finish / Horsepower C |
| `/plans/west-highland-way-race-training-plan-improve/` | 335 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | West Highland Way Race Training Plan - Improve / Horsepower |
| `/plans/west-highland-way-race-training-plan-compete/` | 339 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | West Highland Way Race Training Plan - Compete / Horsepower |
| `/plans/your-first-70-3-training-plan/` | 342 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Your First 70.3 Training Plan / Horsepower Coaching |
| `/plans/your-first-ironman-training-plan/` | 339 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Your First Ironman Training Plan / Horsepower Coaching |
| `/plans/your-first-marathon-training-plan/` | 337 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Your First Marathon Training Plan / Horsepower Coaching |
| `/plans/your-first-century-ride-training-plan/` | 347 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Your First Century Ride Training Plan / Horsepower Coaching |
| `/plans/your-first-olympic-triathlon-training-plan/` | 343 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Your First Olympic Triathlon Training Plan / Horsepower Coac |
| `/plans/your-first-duathlon-training-plan/` | 339 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Your First Duathlon Training Plan / Horsepower Coaching |
| `/plans/70-3-on-8-hours-a-week-training-plan/` | 342 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | 70.3 on 8 Hours a Week Training Plan / Horsepower Coaching |
| `/plans/ironman-on-10-hours-a-week-training-plan/` | 339 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Ironman on 10 Hours a Week Training Plan / Horsepower Coachi |
| `/plans/marathon-on-4-days-a-week-training-plan/` | 336 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Marathon on 4 Days a Week Training Plan / Horsepower Coachin |
| `/plans/century-on-6-hours-a-week-training-plan/` | 344 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Century on 6 Hours a Week Training Plan / Horsepower Coachin |
| `/plans/female-first-70-3-training-plan/` | 382 | 13 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Female-First 70.3 Training Plan / Horsepower Coaching |
| `/plans/female-first-marathon-training-plan/` | 377 | 13 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Female-First Marathon Training Plan / Horsepower Coaching |
| `/plans/female-first-olympic-triathlon-training-plan/` | 383 | 13 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Female-First Olympic Triathlon Training Plan / Horsepower Co |
| `/plans/female-first-century-training-plan/` | 384 | 13 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Female-First Century Training Plan / Horsepower Coaching |
| `/plans/hyrox-endurance-hybrid-training-plan/` | 327 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | HYROX Endurance Hybrid Training Plan / Horsepower Coaching |
| `/plans/hyrox-compete-training-plan/` | 324 | 12 | 1 | 2/0 | Y(143) | Y | BreadcrumbList, Product | HYROX Compete Training Plan / Horsepower Coaching |
| `/plans/standard-duathlon-race-plan/` | 320 | 12 | 1 | 2/0 | Y(145) | Y | BreadcrumbList, Product | Standard Duathlon Race Plan / Horsepower Coaching |
| `/plans/long-course-duathlon-race-plan/` | 324 | 12 | 1 | 2/0 | Y(148) | Y | BreadcrumbList, Product | Long Course Duathlon Race Plan / Horsepower Coaching |
| `/plans/hot-race-heat-preparation-block/` | 364 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Hot Race Heat Preparation Block / Horsepower Coaching |
| `/plans/strength-for-endurance-athletes-training-plan/` | 348 | 12 | 1 | 2/0 | Y(147) | Y | BreadcrumbList, Product | Strength for Endurance Athletes Training Plan / Horsepower C |
| `/plans/ironman-frankfurt-training-plan/` | 337 | 12 | 1 | 2/0 | Y(152) | Y | BreadcrumbList, Product | IRONMAN Frankfurt Training Plan / Horsepower Coaching |
| `/plans/ironman-copenhagen-training-plan/` | 343 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | IRONMAN Copenhagen Training Plan / Horsepower Coaching |
| `/plans/ironman-barcelona-training-plan/` | 343 | 12 | 1 | 2/0 | Y(152) | Y | BreadcrumbList, Product | IRONMAN Barcelona Training Plan / Horsepower Coaching |
| `/plans/ironman-cozumel-training-plan/` | 338 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | IRONMAN Cozumel Training Plan / Horsepower Coaching |
| `/plans/ironman-70-3-world-championship-training-plan/` | 348 | 12 | 1 | 2/0 | Y(142) | Y | BreadcrumbList, Product | IRONMAN 70.3 World Championship Training Plan / Horsepower C |
| `/plans/ironman-70-3-dubai-training-plan/` | 373 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | IRONMAN 70.3 Dubai Training Plan / Horsepower Coaching |
| `/plans/ironman-70-3-oceanside-training-plan/` | 343 | 12 | 1 | 2/0 | Y(151) | Y | BreadcrumbList, Product | IRONMAN 70.3 Oceanside Training Plan / Horsepower Coaching |
| `/plans/paris-marathon-training-plan/` | 335 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | Paris Marathon Training Plan / Horsepower Coaching |
| `/plans/valencia-marathon-training-plan/` | 341 | 12 | 1 | 2/0 | Y(151) | Y | BreadcrumbList, Product | Valencia Marathon Training Plan / Horsepower Coaching |
| `/plans/fred-whitton-challenge-training-plan/` | 348 | 12 | 1 | 2/0 | Y(146) | Y | BreadcrumbList, Product | Fred Whitton Challenge Training Plan / Horsepower Coaching |
| `/plans/tour-of-flanders-sportive-training-plan/` | 365 | 12 | 1 | 2/0 | Y(149) | Y | BreadcrumbList, Product | Tour of Flanders Sportive Training Plan / Horsepower Coachin |
| `/plans/quebrantahuesos-training-plan/` | 340 | 12 | 1 | 2/0 | Y(154) | Y | BreadcrumbList, Product | Quebrantahuesos Training Plan / Horsepower Coaching |
| `/plans/granfondo-stelvio-training-plan/` | 344 | 12 | 1 | 2/0 | Y(150) | Y | BreadcrumbList, Product | Granfondo Stelvio Training Plan / Horsepower Coaching |
| `/plans/cape-town-cycle-tour-training-plan/` | 349 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | Cape Town Cycle Tour Training Plan / Horsepower Coaching |
| `/plans/leroica-training-plan/` | 353 | 12 | 1 | 2/0 | Y(158) | Y | BreadcrumbList, Product | L&#x27;Eroica Training Plan / Horsepower Coaching |
| `/plans/ccc-training-plan/` | 334 | 12 | 1 | 2/0 | Y(152) | Y | BreadcrumbList, Product | CCC Training Plan / Horsepower Coaching |
| `/plans/lavaredo-ultra-trail-training-plan/` | 339 | 12 | 1 | 2/0 | Y(153) | Y | BreadcrumbList, Product | Lavaredo Ultra Trail Training Plan / Horsepower Coaching |
| `/plans/western-states-100-training-plan/` | 378 | 12 | 1 | 2/0 | Y(151) | Y | BreadcrumbList, Product | Western States 100 Training Plan / Horsepower Coaching |
| `/plans/miut-madeira-island-ultra-trail-training-plan/` | 347 | 12 | 1 | 2/0 | Y(142) | Y | BreadcrumbList, Product | MIUT Madeira Island Ultra Trail Training Plan / Horsepower C |
| `/blog/f/female-first-not-female-adapted/` | 1126 | 17 | 1 | 3/0 | Y(172) | Y | BlogPosting, BreadcrumbList | Female First, Not Female Adapted / Horsepower Coaching |
| `/blog/f/make-the-plan-then-hold-it/` | 1104 | 16 | 1 | 3/0 | Y(164) | Y | BlogPosting, BreadcrumbList | Make the Plan, Then Have the Discipline to Hold It / Horsepo |
| `/blog/f/dont-get-fancy-before-youre-fancy/` | 1158 | 17 | 1 | 3/0 | Y(180) | Y | BlogPosting, BreadcrumbList | Don&#x27;t Get Fancy Before You&#x27;re Fancy / Horsepower C |
| `/blog/f/train-easier-than-you-think/` | 1206 | 17 | 1 | 3/0 | Y(193) | Y | BlogPosting, BreadcrumbList | Why Most of Your Training Should Be Easier Than You Think / |
| `/blog/f/into-the-unknown/` | 2022 | 21 | 1 | 3/0 | Y(223) | Y | BlogPosting, BreadcrumbList | First Ironman - Into The Unknown / Horsepower Coaching |
| `/blog/f/how-to-improve-your-triathlon-swim/` | 3144 | 27 | 1 | 3/0 | Y(27) | Y | BlogPosting, BreadcrumbList | How to Improve Your Triathlon Swim / Horsepower Coaching |
| `/blog/f/my-triathlon-top-tips/` | 2665 | 25 | 1 | 3/0 | Y(220) | Y | BlogPosting, BreadcrumbList | My Triathlon Top Tips / Horsepower Coaching |
| `/blog/f/the-lightest-disc-brake-bike/` | 1524 | 18 | 1 | 3/0 | Y(9) | Y | BlogPosting, BreadcrumbList | The Lightest Disc Brake Bike??? / Horsepower Coaching |
| `/blog/f/how-not-to-coach---the-art-of-listening/` | 1766 | 19 | 1 | 3/0 | Y(139) | Y | BlogPosting, BreadcrumbList | How Not to Coach - The Art of Listening / Horsepower Coachin |
| `/blog/f/plastic-pollution-triathlon/` | 1518 | 19 | 1 | 3/0 | Y(24) | Y | BlogPosting, BreadcrumbList | Plastic Plastic Plastic - A Story About Sport &amp; Plastic |
| `/blog/f/once-twice-three-times-an-ironman/` | 2109 | 21 | 1 | 3/0 | Y(83) | Y | BlogPosting, BreadcrumbList | Once, Twice, Three Times an Ironman / Horsepower Coaching |
| `/blog/f/tits-up---how-to-deal-with-failure/` | 1731 | 19 | 1 | 3/0 | Y(67) | Y | BlogPosting, BreadcrumbList | Tits Up - How to Deal with Failure / Horsepower Coaching |
| `/blog/f/everesting---climbing-the-mountain/` | 1636 | 19 | 1 | 3/0 | Y(214) | Y | BlogPosting, BreadcrumbList | Everesting - Climbing The Mountain / Horsepower Coaching |
| `/blog/f/our-origins---a-little-bit-of-history/` | 1018 | 15 | 1 | 3/0 | Y(223) | Y | BlogPosting, BreadcrumbList | Origins - A Little Bit of History / Horsepower Coaching |
| `/blog/f/ironman-wales---enter-the-dragon/` | 801 | 14 | 1 | 3/0 | Y(96) | Y | BlogPosting, BreadcrumbList | Ironman Wales - Enter The Dragon / Horsepower Coaching |
| `/blog/f/2017-season-wrapup---calm-after-the-storm/` | 1472 | 18 | 1 | 3/0 | Y(66) | Y | BlogPosting, BreadcrumbList | 2017 Season Wrapup - Calm After The Storm / Horsepower Coach |
| `/blog/f/psychology---use-your-head/` | 2140 | 22 | 1 | 3/0 | Y(228) | Y | BlogPosting, BreadcrumbList | Psychology - Use Your Head / Horsepower Coaching |

---

## Appendix B - method & reproducibility

- Tooling: adapted read-only from `website-builder/tools/audit_site.py` (raw-HTML fetch, no JS),
 per `website-builder/METHOD.md`. `website-builder` was not modified.
- Fetch: `curl`, UA `Mozilla/5.0 (compatible; site-audit/1.0)`, on 2026-08-14. Word counts strip
 `<script>`/`<style>`/`<noscript>`/comments/tags - the non-JS crawler's view.
- CURRENT inventory from `sitemap.website.xml` (13) + `sitemap.blog.xml` (13); `sitemap.ols.xml`
 returned 404, `sitemap.ola.xml` listed only `/`.
- NEW inventory: 180 `<loc>`s from `https://horsepower-coaching.netlify.app/sitemap.xml`, crawled
 on the Netlify host (sitemap emits the production origin by design).
- Redirects verified by requesting each old path on the Netlify host and recording HTTP status +
 `Location`; all 25 returned 301 to a 200 target.
- No traffic, rank, or Domain Authority figure is measured or estimated anywhere in this document.
 Post-cutover Google Search Console is the sole ground truth for live positions.

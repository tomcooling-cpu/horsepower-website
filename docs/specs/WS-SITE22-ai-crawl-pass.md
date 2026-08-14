# SPEC WS-SITE22: AI-crawl pass (awards lift 3/3) + review-intake scaffolding + cutover verify script

Fable spec, 2026-08-14. Executor: Opus agent in a worktree. Deviations without justification fail review.

## Freeze rules
- Visible body text: ZERO deltas (freeze gate must pass without snapshot changes to body text).
- HEAD metadata: title/meta/canonical/og/twitter FROZEN. JSON-LD blocks WILL change by design
  (this pass restructures them); regenerate the freeze snapshot ONLY for the JSON-LD delta and
  enumerate per page what changed. Gate 10d (>=1 parsing JSON-LD, zero domestiq) must stay green.
- URLs frozen, plus THREE additive files allowed: /llms.txt, and nothing else new.

## Part A: llms.txt
Serve at site root (both base modes; add to the build like robots.txt, NOT to sitemap).
Content requirements (plain markdown per the llms.txt convention; write in factual, plain prose):
- H1: Horsepower Coaching. One-paragraph summary: world class multisport, cycling and endurance
  coaching by Tom Cooling; based in Truro, Cornwall, UK; coaches athletes across the UK (including
  Clevedon and the South West) and online worldwide.
- Core facts stated once: the three tiers with EXACT names and prices (Plan Store, plans from
  £39.99 one-off, 153 plans delivered via TrainingPeaks; Plan Only, £120/month, bespoke plan +
  block-by-block feedback, no calls; Coached by Tom, £185/month, full 1-2-1, weekly feedback,
  15 places only). Contact: WhatsApp +44 7780 008724, Instagram @horsepower.coaching, contact page.
- Verified athlete results ONLY (copy exactly from the site's honours band: Hannah S, Madison S,
  Naomi S, Elly B lines - first-name + initial ONLY, per the surname gate).
- An explicit "Not published / do not infer" section: no physical training venue open to the public;
  coaching is delivered remotely via TrainingPeaks; anything not stated here is not published.
- Key URLs list: /, /coaching/, /coached/, /plans/, /female-performance/, /triathlon-coaching/,
  /cycling-coaching/, /about/, /blog/, /contact/.
- Gate: llms.txt exists in built output, zero "domestiq", zero client surnames, zero em-dash,
  prices match the site byte-for-byte (derive from the same TIER constants, do not hand-type).

## Part B: unified JSON-LD @graph
Today: scattered per-page blocks, ZERO "@id" anywhere (verified). Restructure per page into ONE
`<script type="application/ld+json">` carrying `{"@context":..., "@graph":[...]}` with stable @ids:
- `https://horsepowercoaching.co.uk/#org` (the SportsActivityLocation/LocalBusiness node; keep
  ALL current fields incl. address Truro, areaServed with Clevedon, aggregateRating 5.0/15).
- `https://horsepowercoaching.co.uk/#tom` (Person; keep all credentials; add `worksFor` -> #org;
  #org gains `founder` -> {"@id": "#tom"} reference instead of an inline copy).
- `#website` (WebSite, publisher -> #org).
- Per page: the page's own nodes (Service, CollectionPage/ItemList, FAQPage, BreadcrumbList,
  BlogPosting, Product) join the same @graph and reference #org / #tom by @id (provider, author,
  publisher, brand). Product pages: Product.brand -> #org by @id.
- NO information lost: every field present today must survive (the freeze snapshot's parsed
  JSON-LD comparison is the proof surface - the enumerated delta must show restructuring and
  reference-linking only, plus the explicitly allowed additions: @id, worksFor, publisher, brand).
- JSON-LD contains no comments; every block json.loads-parses (existing gate). Test that each
  page's @graph has exactly one #org reference chain (no duplicate inline copies of org/person).

## Part C: review-intake scaffolding (so Tom's screenshots become slides in one step)
- Create generator/content/reviews/README.md documenting the intake: Tom drops screenshot files
  into generator/content/reviews/inbox/ (gitignored); each review is transcribed VERBATIM into
  reviews.yaml (fields: text, reviewer_display e.g. "Ian C", source: google, gender_tag:
  female|male|unknown, event_note optional). CLIENT_QUOTES/VERIFIED_QUOTES then read from
  reviews.yaml (single source). Migrate the 5 existing verified quotes into reviews.yaml now,
  byte-identical (freeze gate proves it).
- Hard rules in the loader: reviews render first-name + initial only; a review not in
  reviews.yaml never renders; count shown ("15 Google reviews") stays sourced from the existing
  REVIEW_COUNT constant. No invented reviews (gate: every rendered quote must exist in reviews.yaml).

## Part D: DNS cutover verify script
tools/verify_cutover.py: given a hostname argument (default horsepowercoaching.co.uk), checks and
reports PASS/FAIL for: apex resolves to Netlify (75.2.60.5) and www CNAME to
horsepower-coaching.netlify.app; https:// serves 200 with a valid cert; / serves the new site
(look for "Plan Store" + fonts/oswald woff2 reference); the 11 GoDaddy-era 301s redirect
correctly (reuse the _redirects map paths + expected targets); /blog/f/everesting---climbing-the-mountain
resolves; robots.txt, sitemap.xml, llms.txt all 200; sitemap URLs use the prod host. Read-only,
stdlib + curl only, exits non-zero on any FAIL. This script is run at cutover time (runbook:
docs/runbooks/dns-cutover.md).

## Acceptance
Both build modes green on ALL gates; freeze: body text zero-delta, metadata zero-delta except the
enumerated JSON-LD restructure; llms.txt + verify script shipped; reviews.yaml single-source with
byte-identical rendered output. Screenshot spot-check NOT required (no visual change expected);
instead prove no visual delta: rendered HTML diff limited to the JSON-LD script blocks.

# SPEC: Cold SEO + AI-crawlability comparison - new site vs current live site, ranked

Fable spec, 2026-08-14. Executor: Opus agent (read-only analysis; NO site changes). Tom's ask:
"a cold harsh comparison... ranked to see which is the highest performer. i want to know 100%
i wont lose my page authority."

## Subjects
- CURRENT: https://horsepowercoaching.co.uk (GoDaddy builder site, live)
- NEW: https://horsepower-coaching.netlify.app (the rebuilt site; treat canonicals-to-prod-host
  as correct-by-design for cutover, not an error)

## Method (evidence or it does not count)
Work from RAW HTML with no JS execution (what most AI crawlers see). For EVERY page in each
site's sitemap(s) plus robots.txt/llms.txt: fetch and tabulate per page - title (+length),
meta description (+length/presence), canonical, H1 count, word count (scripts/styles stripped),
image count + images missing alt, JSON-LD types (+do they parse), og:image presence/usability.
Also per site: sitemap URL count + correctness, robots.txt AI-crawler posture (named crawlers),
llms.txt presence, redirect handling (for NEW: verify the 11 GoDaddy-URL 301s + blog-URL parity
with CURRENT's sitemap - this is the authority-preservation evidence), page speed proxies
(HTML weight, render-blocking external requests, font strategy, image formats/lazy-loading),
mobile viewport + pinch-zoom, internal linking (orphan pages, anchor quality), local SEO signals
(NAP, areaServed, address schema), content depth (indexable pages by intent: head terms, long-tail
plan pages, blog).

## Scoring (the ranking Tom asked for)
Score each site 0-10 per category, with a one-line evidence citation per score (a quoted string
or measured number from the fetch - no vibes): 1 Technical metadata; 2 Structured data;
3 Crawl/index surface (sitemap+robots+llms); 4 AI-answer-engine readiness; 5 Content depth &
keyword coverage; 6 Page experience (speed proxies, mobile); 7 Local SEO; 8 Authority
preservation (CURRENT scores on what exists; NEW scores on redirect map + URL parity + same-domain
plan). Produce a ranked table (category, CURRENT score, NEW score, winner, evidence), an overall
weighted verdict (weight 8 and 5 highest - they carry the commercial risk), and a plain-English
"will Tom lose page authority at cutover?" answer with the exact evidence chain (same domain;
per-URL 301s verified live on Netlify; blog slugs identical; head-term pages preserved at
/triathlon-coaching/ /cycling-coaching/; GSC sitemap step in the runbook).

## Honesty requirements
- If CURRENT beats NEW anywhere, say so plainly and propose the fix; do not grade on a curve.
- Flag anything NEW does that carries cutover risk (e.g. any CURRENT sitemap URL not covered by
  a redirect or same-slug page = a named gap, listed explicitly; expected: the 13 blog posts map
  1:1, 11 pages map via _redirects, and any residue must be enumerated).
- No fabricated metrics: no invented traffic/DA numbers; this is an on-page/technical comparison.
  State that live rank tracking post-cutover (GSC) is the only ground truth for positions.

## Deliverable
docs/audits/seo-comparison-2026-08.md in the repo (committed on a branch, no push): the ranked
table, per-page appendix tables for both sites, the authority-preservation evidence chain, a
top-10 punch-list of any NEW-site gaps found (each with file/fix), and a 5-line executive summary
Tom can read in 30 seconds. Report the executive summary + ranked table verbatim in your final
message.

# RUNBOOK: DNS cutover - horsepowercoaching.co.uk -> Netlify

Fable, 2026-08-14. Execute ONLY on Tom's explicit go, after the SEO comparison is signed off.
Rollback tag pre-editorial-2026-08-14 exists; the GoDaddy site stays intact throughout (DNS-only
change), so full rollback = repoint DNS back.

## Pre-flight (before touching DNS)
1. Netlify: add the custom domains to the site (Site settings -> Domain management):
   horsepowercoaching.co.uk (primary) + www.horsepowercoaching.co.uk. Site id
   b595fd08-2194-42a3-ae31-5094a049e91c ("horsepower-coaching"). [Tom login or CLI]
2. Confirm latest deploy is the approved build: https://horsepower-coaching.netlify.app
3. Run: python3 tools/verify_cutover.py horsepower-coaching.netlify.app  (all PASS except
   apex-DNS checks, which only pass post-cutover).
4. Screenshot/记录 GoDaddy's CURRENT DNS records (rollback reference).

## The DNS change (GoDaddy DNS manager - keep GoDaddy as registrar+DNS; NO Cloudflare)
- Apex A record: @ -> 75.2.60.5 (Netlify load balancer). Remove/replace the GoDaddy-builder A records.
- www CNAME: www -> horsepower-coaching.netlify.app
- TOUCH NOTHING ELSE: leave MX, TXT (SPF/DKIM), and all mail records exactly as they are.
- TTL: lowest available (600s) for fast propagation and fast rollback.

## Post-cutover (same sitting)
1. Wait for propagation (minutes-hours). Netlify auto-provisions the Let's Encrypt cert once
   DNS resolves; confirm the padlock on https://horsepowercoaching.co.uk.
2. Run: python3 tools/verify_cutover.py horsepowercoaching.co.uk -> ALL PASS required
   (apex/www resolution, 200s, redirects incl. old GoDaddy URLs + blog slugs, robots/sitemap/llms).
3. Google Search Console: submit https://horsepowercoaching.co.uk/sitemap.xml; request indexing
   of /, /triathlon-coaching/, /cycling-coaching/, /female-performance/. [Tom login]
4. Google Ads: update landing URLs to the new paths (map: any ad -> nearest new page; the 301s
   cover misses but Quality Score prefers direct final URLs). [Tom login]
5. Google Business Profile: leave as-is (Clevedon listing retained deliberately for search).

## Watch period (4-8 weeks)
- GSC Coverage weekly: 404s spike = a missed redirect -> add to _redirects same day.
- GSC Performance: expect a small position wobble in week 1-2, recovery by week 4; escalate only
  if a head term (triathlon coaching / cycling coaching / female terms) drops >5 positions for
  >2 weeks.
- Netlify Forms: first contact-form submission appears in the Netlify dashboard; enable email
  notification to Tom. [Tom login]

## Rollback (if ever needed)
GoDaddy DNS: restore the recorded original A/CNAME records. The old GoDaddy site is untouched
and resumes serving on propagation. No data loss either direction.

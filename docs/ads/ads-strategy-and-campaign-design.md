# Horsepower Coaching: Google Ads Strategy and Campaign Design

Account: 223-337-7250 (UK timezone). Site: https://horsepowercoaching.co.uk
Owner: Tom Cooling. Status: design document, nothing in this file has been built in the account yet. Current-account audit completed 2026-08-16 from Tom's screenshots (section 11).

Style note for anyone editing this file: no em-dashes, British spelling, plain language. Every ad line in this document is written to be pasted straight into the Google Ads UI.

---

## 0. Audit headline: what the account runs today, and why it changes the plan

Full audit data is in section 11. The three findings that shape everything below:

1. **Both current campaigns are Google Smart campaigns, not standard Search.** The account header reads "All Smart campaigns"; targeting is by fuzzy "keyword themes" rather than keywords; all four ads point at the homepage; the reported "conversions" are Smart's loose auto-actions (calls, map views, website actions), not tracked leads or sales. Smart campaigns give no keyword-level control, no real negative keywords, no ad groups, no landing-page mapping. They also cannot be converted to Search campaigns: the migration is build-new-then-pause-old (Runbook RB4). The whole design below is, in effect, the answer to "what does this business get from standard Search that Smart cannot give it": exact-match control over which queries spend money, deep links to the tier pages instead of the homepage, real negatives against the observed waste, and conversion tracking that measures actual purchases and enquiries.
2. **The Plan Store is completely absent from the account, and the search-terms data proves the demand is already there.** People reached the Smart campaigns searching "cycling training plan", "triathlon training plan", "ironman training plan", "century ride training plan", "haute route training plan", "sportive training plan", "100 mile training plan", and every one of them landed on the homepage with no plan offer in the ad. Those queries map one-to-one onto the 153 Plan Store pages at low CPCs. Campaign 2 below is the single biggest new opportunity in this design: cheap £39.99 purchases at the top of the funnel that upsell to Plan Only and Coached.
3. **The spend history says head-term CPCs here are cheap.** Roughly £2,950 spent all-time bought ~8,860 clicks (blended CPC around £0.33); the head coaching terms cost £0.60 to £0.80 per click ("cycling coach" £0.76, "triathlon coaching" £0.79, "triathlon coach" £0.64) and brand clicks cost pennies (~£0.09). Smart-campaign CPCs are not a perfect predictor of exact-match Search CPCs, so treat these as strong planning inputs rather than guarantees, but they mean the budget tiers in section 6 buy meaningfully more clicks than a cold-start guess would assume.

One more audit observation worth naming: the current campaigns are on a combined budget of about £1.35/day (~£41/month capacity) and underspent even that (~£19 in the last month) with CTRs around 0.8 to 1.0 percent. The account is idling. The scaling room to Tom's £50 to £600/month range is real, but every extra pound should go into the new Search structure, never into the Smart campaigns.

---

## 1. Objective and strategy

### 1.1 What we are buying

New-user acquisition for the relaunched site, across three tiers that form a ladder:

| Tier | Price | Landing page | Conversion type |
|---|---|---|---|
| Plan Store | from £39.99 one-off | /plans/ plus 153 race pages | Purchase |
| Plan Only | £120/month | /coaching/ (Plan Only page) | Lead (apply / contact) |
| Coached by Tom | £185/month | /coached/ | Lead (apply / contact) |

The ladder matters for ads: a £39.99 plan buyer is worth more than £39.99 because some buyers step up to Plan Only or Coached later. We do not have measured step-up rates yet, so treat that as upside, not as something to bake into bids on day one.

### 1.2 Why Search is the spine

At £50 to £600 a month, every pound has to land on someone who is already looking. Search is the only Google format where intent is explicit in the query: "ironman wales training plan" or "online triathlon coach" tells us exactly which tier page to send them to. Display, YouTube and broad awareness formats need budget to build frequency and they need creative production; at this budget they would burn the month before they teach us anything.

So: Search only, Search Partners off, Display Expansion off. Everything else is an earn-in.

### 1.3 Performance Max and Demand Gen: when, if ever

- Performance Max needs two things we do not have yet: steady conversion volume (as a planning threshold, do not consider it below roughly 30 conversions a month flowing into the account) and a proper creative set (images, logos, video). Without conversions it optimises blind; without creative it builds ugly auto-ads. Revisit only at the £600/month tier, and only for the Plan Store (purchase conversions with a real value are the one thing PMax can optimise sensibly here).
- Demand Gen is a maybe for the Female Performance positioning at the top of the budget range, because that message is genuinely differentiated and visual. Park it until Search is proven and there is real creative (athlete photography, not stock).

Neither goes live in the initial build. They are documented here so the scale path is written down, not so they get built early.

### 1.4 How paid complements the organic position

The site already ranks well: structured data, llms.txt, blog, ranked head-term pages. That changes what we buy:

- Do not pay for clicks you already win. If /triathlon-coaching/ ranks number 1 for a term and no competitor ads sit above it, bidding on that term mostly cannibalises a free click. The audit gives this teeth: the Smart campaigns spent ~£17 buying 190 clicks on "horsepower coaching", a term the site ranks number 1 for organically. That is observed self-cannibalisation, not a hypothetical. Rule of thumb to apply per head term before enabling it: bid where organic position is 4 or worse, or where competitors run ads above your number 1 organic result; skip where you own position 1 uncontested. Cross-check each term in section 3 against Search Console before launch (Runbook RB4 Part A step 4).
- Long-tail race pages are the exception in our favour. 153 race pages cannot all rank quickly post-relaunch. Paid can cover the races where the page is new or not yet ranking, and be switched off race by race as organic catches up. That is a genuinely efficient use of a small budget. The audit's plan-intent search terms (haute route, century ride, sportive, 100 mile, ironman training plan) are the seed list.
- Brand defence ("horsepower coaching") is cheap insurance if anyone bids on the name, and near-pointless if nobody does. Given the observed self-cannibalisation above, the default flips to NO brand campaign at launch, with a monthly SERP check to reinstate it the moment a competitor bids on the name. Decision D2 in the runbooks.

---

## 2. Account structure

Three campaigns, single-theme ad groups, every ad group mapped to one landing page (never the homepage). Campaigns are the budget-control layer, which is why coaching and plans are separate: they have different economics and must not share a daily budget.

```
Campaign 1: HP | Coaching | Search        (leads, high value, low volume)
  AG 1.1 Triathlon Coaching      -> /triathlon-coaching/
  AG 1.2 Cycling Coaching        -> /cycling-coaching/
  AG 1.3 Female Performance      -> /female-performance/
  AG 1.4 Ironman Coaching        -> /triathlon-coaching/

Campaign 2: HP | Plans | Search           (purchases, £39.99+, higher volume)
  AG 2.1 Training Plans (generic)   -> /plans/
  AG 2.2 Ironman Race Plans         -> keyword-level URLs to race pages
  AG 2.3 Middle Distance 70.3 Plans -> keyword-level URLs to race pages
  AG 2.4 Ultra and Trail Run Plans  -> keyword-level URLs to race pages
  AG 2.5 Cycling Event Plans        -> keyword-level URLs to race pages
  (AG 2.6 DSA catch-all: scale tier only, see 2.2 below)

Campaign 3: HP | Brand | Search           (optional, tiny budget, decision D2)
  AG 3.1 Brand                   -> homepage or /coaching/
```

### 2.1 Match-type reality

Modern Google match types are looser than the names suggest. Exact match now includes close variants and same-meaning rewrites; phrase match includes anything Google deems to share the meaning. Practical policy:

- Exact match for the head terms where we want budget control.
- Phrase match to harvest the long tail around those heads.
- No broad match anywhere until the account has conversion history and a bidding strategy that can use it (broad match plus Maximise Conversions later is legitimate; broad match plus Manual CPC now is a leak).
- The real match-type control is the search-terms report plus negatives, worked weekly (Runbook RB6). Assume every keyword will match things you did not intend, and plan to prune.

### 2.2 Covering 153 race pages without 153 ad groups

Three mechanisms, in order of when to deploy:

1. **Keyword-level final URLs (from day one).** Google Ads allows a final URL on each keyword that overrides the ad's final URL. So AG 2.2 holds one RSA about Ironman plans, and each keyword ("ironman wales training plan", "challenge roth training plan", and so on) deep-links to its own race page. One ad group can cleanly cover 15 to 20 races per discipline. Start with the races Tom judges highest-demand (see decision D6): the audit screenshots plus Search Console impressions data should drive that pick.
2. **Themed ad groups by discipline (day one).** AG 2.2 to 2.5 split by discipline so the ad copy can name the sport. Do not split further until data says a race deserves its own ad group (planning trigger: a single race keyword earning a meaningful share of the ad group's clicks, say a third or more over a month, gets promoted to its own ad group with race-named headlines).
3. **Dynamic Search Ads catch-all (scale tier only).** A DSA ad group targeting the /plans/ directory lets Google match queries to all 153 pages and write the headline from the page. It is the only sane way to cover the full long tail. It needs the site's page titles to be clean (they are, post-relaunch) and it needs every manually-targeted keyword added as a DSA negative so it only catches what the manual groups miss. Deploy at £300/month or above, never in the lean start.

---

## 3. Ad groups in full: keywords, landing pages, RSAs

Conventions for everything below:
- [square brackets] = exact match, "quotes" = phrase match.
- All headlines are 30 characters or fewer; all descriptions are 90 characters or fewer. Counted, not guessed. Recount after any edit.
- Pinning guidance per ad group. Default is pin as little as possible (pinning restricts combinations and Google reports lower Ad Strength), with one exception: where a compliance-of-message issue exists (price clarity), pin lightly as noted.
- CPC figures anywhere in this document are planning assumptions to validate against the first two weeks of data, not benchmarks.

---

### AG 1.1 Triathlon Coaching
**Landing page:** https://horsepowercoaching.co.uk/triathlon-coaching/

**Keywords (10; the head terms are the audit's top spenders, see s11.3):**
- [triathlon coach]
- [triathlon coaching]
- [online triathlon coach]
- [triathlon coach uk]
- "online triathlon coaching"
- "triathlon coaching uk"
- "personal triathlon coach"
- "triathlon coach near me"
- "triathlon coach london"
- "best triathlon coach uk"

"triathlon coach london" is in because the audit shows real London-query volume (31 clicks, ~£21) and the geo is national online coaching; the copy's "UK Coach, Online Worldwide" line answers it honestly.

**Headlines (15):**
1. Triathlon Coaching by Tom
2. 1:1 Triathlon Coaching
3. Coached by a Real Racer
4. Full Coaching £185 a Month
5. Plan Only £120 a Month
6. 15 Coached Places Only
7. Weekly 1:1 Feedback
8. Two Ironman Wales Champions
9. UK Coach, Online Worldwide
10. Delivered via TrainingPeaks
11. A Real Coach, Not an App
12. 5.0 Rated on Google
13. Built Around Your Race
14. Apply for Coaching Today
15. Train With a Proven Coach

**Descriptions (4):**
1. 1:1 triathlon coaching from Tom Cooling. Weekly feedback, plans built around your race.
2. Coached athletes include two Ironman Wales champions. Real results, not marketing.
3. Coached by Tom is £185 a month, 15 places. Plan Only is £120 a month, self directed.
4. UK based, coaching triathletes worldwide online. 5.0 Google rating from 15 reviews.

**Pinning:** pin headline 1 or 2 to position 1 (the ad must always lead with what it is). Leave everything else unpinned.

---

### AG 1.2 Cycling Coaching
**Landing page:** https://horsepowercoaching.co.uk/cycling-coaching/

**Keywords (13; the first eight are the audit's proven spenders, see s11.3):**
- [cycling coach]
- [cycling coaching]
- [cycle coaching]
- [cycle coach]
- "cycling coach near me"
- "cycle coaching uk"
- [online cycling coach]
- "online cycling coaching"
- [cycling coach uk]
- "cycling coaching uk"
- "personal cycling coach"
- "road cycling coach"
- "time trial coach"

Note the "cycle coaching" spelling variants and the "near me" terms are in because the audit shows them earning real clicks at sane CPCs (s11.3), not because a keyword tool suggested them. On "near me" intent generally, see decision D1 note in section 7.1.

**Headlines (15):**
1. Cycling Coaching by Tom
2. 1:1 Cycling Coaching
3. Coach Led, Not App Led
4. Coached a Welsh TT Champion
5. Full Coaching £185 a Month
6. Plan Only £120 a Month
7. Weekly Feedback, Real Coach
8. Road, TT and Endurance
9. UK Coach, Online Worldwide
10. Delivered via TrainingPeaks
11. 15 Coached Places Only
12. 5.0 Rated on Google
13. Built Around Your Racing
14. Train With Purpose
15. Apply for Coaching Today

**Descriptions (4):**
1. 1:1 cycling coaching from Tom Cooling. Weekly feedback, training built around your races.
2. Coached by a racer, not an algorithm. Road, time trial and endurance cycling covered.
3. Coached athletes include a Welsh 100 TT champion. Real results on real roads.
4. Full coaching £185 a month or a bespoke plan at £120 a month. TrainingPeaks delivery.

**Pinning:** pin headline 1 or 2 to position 1. Nothing else.

---

### AG 1.3 Female Performance
**Landing page:** https://horsepowercoaching.co.uk/female-performance/

**Keywords (9):**
- "female triathlon coach"
- "triathlon coach for women"
- "womens triathlon coaching"
- "female cycling coach"
- "womens cycling coach"
- "female endurance coach"
- "cycle aware training plan"
- "menstrual cycle triathlon training"
- "coaching for female athletes"

Note: the last three are lower-intent, more informational queries. Keep them, but watch their search terms hardest; they are the first candidates for pruning if they draw browsers rather than buyers.

**Headlines (15):**
1. Female First Coaching
2. Not Female Adapted
3. Coaching Built for Women
4. Cycle-Aware Training
5. Women's Triathlon Coaching
6. Women's Cycling Coaching
7. Coached by Tom Cooling
8. Two Ironman Wales Champions
9. Weekly 1:1 Feedback
10. Full Coaching £185 a Month
11. Plan Only £120 a Month
12. Train With Your Physiology
13. 5.0 Rated on Google
14. UK Coach, Online Worldwide
15. Apply for Coaching Today

**Descriptions (4):**
1. Female first, not female adapted. Coaching built around your physiology from day one.
2. Most coaching defaults to male athletes. Ours does not. Weekly feedback, bespoke plans.
3. Coached athletes include two Ironman Wales champions. Real results for real women.
4. 1:1 coaching £185 a month or plan only £120 a month. UK based, online worldwide.

**Pinning:** pin "Female First Coaching" or "Coaching Built for Women" to position 1. This ad group exists to make the differentiator unmissable; it is the one place where a second pin is acceptable ("Not Female Adapted" pinned to position 2) if Ad Strength allows.

---

### AG 1.4 Ironman Coaching
**Landing page:** https://horsepowercoaching.co.uk/triathlon-coaching/

Split from AG 1.1 because "ironman coach" queries deserve Ironman-specific proof in the copy, and because the Ironman Wales results are the strongest single asset the business has.

**Keywords (8; [ironman coach] and "ironman coach uk" are proven spenders in the audit, s11.3):**
- [ironman coach]
- [ironman coaching]
- "ironman triathlon coach"
- "ironman coach uk"
- "ironman wales coach"
- "70.3 coach"
- "half ironman coach"
- "long course triathlon coach"

Optional extension (Tom's call): the old Smart campaign ran a Celtman/Norseman/XTRI ad, and coached athletes have real XTRI and Outlaw podiums, so "xtri coach", "celtman coaching" and "norseman coaching" are legitimate ultra-niche adds here. Tiny volume, near-zero competition expected; add them as phrase match and let the search-terms report say whether anyone is out there.

Important: the bare query "ironman" spent money in the old campaigns and is pure waste (brand browsing, merchandise, results). The exact negative [ironman] in section 4 blocks the bare term while leaving every "ironman coach/plan" query alive. Do not add a broad negative for it.

**Headlines (15):**
1. Ironman Coaching
2. Ironman Triathlon Coaching
3. Two Ironman Wales Champions
4. Coached by a Real Racer
5. Long Course Triathlon Coach
6. Weekly 1:1 Feedback
7. Full Coaching £185 a Month
8. Plan Only £120 a Month
9. 15 Coached Places Only
10. Delivered via TrainingPeaks
11. UK Coach, Online Worldwide
12. 5.0 Rated on Google
13. Built Around Your Ironman
14. Race Plans for Your A Race
15. Apply for Coaching Today

**Descriptions (4):**
1. Ironman coaching from Tom Cooling. Coached athletes won Ironman Wales in 2022 and 2025.
2. Weekly feedback, a plan built for your race, and a race-day plan when it matters.
3. Full 1:1 coaching £185 a month, 15 places only. Bespoke plan only from £120 a month.
4. Delivered via TrainingPeaks. UK based, coaching athletes worldwide. 5.0 on Google.

**Pinning:** pin headline 1 or 2 to position 1.

---

### AG 2.1 Training Plans (generic store)
**Landing page:** https://horsepowercoaching.co.uk/plans/

**Keywords (10):**
- [triathlon training plan]
- "triathlon training plans"
- [cycling training plan]
- "cycling training plans"
- "buy triathlon training plan"
- "trainingpeaks training plan"
- "structured training plan triathlon"
- "race specific training plan"
- "triathlon plan trainingpeaks"
- "training plan for triathlon"

**Headlines (15):**
1. Training Plans From £39.99
2. 153 Race-Specific Plans
3. Written for Named Races
4. One-Off Price, No Contract
5. Delivered on TrainingPeaks
6. Coach-Built Training Plans
7. Ironman to Ultra Covered
8. Buy Once, Train Anywhere
9. Plans for Your Exact Race
10. From a 5.0 Rated Coach
11. Triathlon, Cycling, Ultra
12. Find Your Race Plan
13. Start Training This Week
14. No Subscription Needed
15. Built by Horsepower Coaching

**Descriptions (4):**
1. 153 training plans, each written for a named race. From £39.99, one-off, no subscription.
2. Delivered straight into TrainingPeaks. Buy once, follow the plan, race your race.
3. From the coach behind two Ironman Wales champions. Plans priced from £39.99.
4. Ironman, 70.3, marathon, ultra and cycling events. Find the plan for your race.

**Pinning:** pin "Training Plans From £39.99" to position 1. Price-led is right for this ad group: it qualifies the click (this is a paid product, no support) and filters freebie hunters before they cost a click.

---

### AG 2.2 Ironman Race Plans
**Ad-level final URL:** https://horsepowercoaching.co.uk/plans/
**Keyword-level final URLs:** each race keyword points at its own race page.

**Keywords (starter set of 8; extend from the plan catalogue and Search Console, see decision D6):**
- [ironman training plan] -> /plans/
- "ironman training plan" -> /plans/
- [ironman wales training plan] -> /plans/ironman-wales-training-plan/
- "ironman wales training plan" -> /plans/ironman-wales-training-plan/
- "challenge roth training plan" -> /plans/challenge-roth-training-plan/ (confirm exact slug before entering)
- "full distance triathlon training plan" -> /plans/
- "ironman training plan trainingpeaks" -> /plans/
- "ironman training plan uk" -> /plans/

Rule: before entering any keyword-level URL, open the race page and copy the URL from the browser bar. Never type a slug from memory; a typo here sends paid traffic to a 404.

**Headlines (15):**
1. Ironman Wales Training Plan
2. Your Ironman Training Plan
3. Race-Specific Ironman Plans
4. Written for Your Ironman
5. Plans From £39.99
6. Delivered on TrainingPeaks
7. Coach-Built, Not Generic
8. Two Ironman Wales Champions
9. Built for the Actual Course
10. One-Off Price, No Contract
11. Full Distance Plans
12. Start Training This Week
13. From a 5.0 Rated Coach
14. Buy Once, Train Anywhere
15. Find Your Ironman Plan

Note on headline 1: it is race-specific while the ad group covers several races. That is acceptable because Wales is the flagship result; if it bothers you in reporting, swap it for "Ironman Plans, Named Races" (25 characters). If a single race is promoted to its own ad group later, all 15 headlines get that race's name treatment.

**Descriptions (4):**
1. Training plans written for named Ironman races, not generic templates. From £39.99.
2. From the coach behind two Ironman Wales champions, 2022 and 2025. TrainingPeaks delivery.
3. One-off price from £39.99. No subscription. Buy the plan, load it, start this week.
4. Named races, real courses. Sessions built around the demands of your chosen event.

**Pinning:** pin "Plans From £39.99" or headline 2 to position 1. Nothing else.

---

### AG 2.3 Middle Distance 70.3 Plans
**Ad-level final URL:** https://horsepowercoaching.co.uk/plans/
**Keyword-level final URLs** to specific 70.3 race pages where they exist in the catalogue.

**Keywords (7):**
- [70.3 training plan]
- "70.3 training plan"
- [half ironman training plan]
- "half ironman training plan"
- "middle distance triathlon training plan"
- "half distance triathlon plan"
- "70.3 training plan trainingpeaks"

**Headlines (15):**
1. 70.3 Training Plans
2. Half Ironman Training Plan
3. Middle Distance Tri Plans
4. Written for Named Races
5. Plans From £39.99
6. Delivered on TrainingPeaks
7. Coach-Built, Not Generic
8. One-Off Price, No Contract
9. Built for the Actual Course
10. Start Training This Week
11. From a 5.0 Rated Coach
12. Buy Once, Train Anywhere
13. Race-Specific Sessions
14. Your Race, Your Plan
15. Find Your 70.3 Plan

**Descriptions (4):**
1. Middle distance training plans written for named races. From £39.99, no subscription.
2. Buy once, load it into TrainingPeaks, start this week. Built by a real coach.
3. From the coach behind two Ironman Wales champions. Plans priced from £39.99.
4. Sessions built around the demands of your chosen race, not a generic template.

**Pinning:** pin headline 1 or 2 to position 1.

---

### AG 2.4 Ultra and Trail Run Plans
**Ad-level final URL:** https://horsepowercoaching.co.uk/plans/
**Keyword-level final URLs** to race pages (UTMB page confirmed to exist: /plans/utmb-mont-blanc.../ , copy the exact slug from the live site).

**Keywords (8):**
- "ultra marathon training plan"
- "ultra running training plan"
- [utmb training plan]
- "utmb training plan"
- "trail ultra training plan"
- "50 mile ultra training plan"
- "100k ultra training plan"
- "mountain ultra training plan"

**Headlines (15):**
1. Ultra Running Training Plans
2. UTMB Training Plan
3. Trail Ultra Race Plans
4. Written for Named Races
5. Plans From £39.99
6. Delivered on TrainingPeaks
7. Coach-Built, Not Generic
8. One-Off Price, No Contract
9. Built for the Actual Course
10. Start Training This Week
11. From a 5.0 Rated Coach
12. Vert, Terrain and Pacing
13. Your Race, Your Plan
14. Buy Once, Train Anywhere
15. Find Your Ultra Plan

**Descriptions (4):**
1. Ultra and trail training plans written for named races, UTMB included. From £39.99.
2. Built around the climbing, terrain and time on feet your race actually demands.
3. One-off price, no subscription. Delivered straight into TrainingPeaks.
4. Written by a real coach who plans for real courses, not a one-size template.

**Pinning:** pin headline 1 to position 1.

---

### AG 2.5 Cycling Event Plans
**Ad-level final URL:** https://horsepowercoaching.co.uk/plans/
**Keyword-level final URLs** to cycling event pages from the catalogue.

**Keywords (10; sportive, century, haute route and 100 mile are all real queries from the audit, s11.3):**
- [cycling training plan]
- "sportive training plan"
- "gran fondo training plan"
- "century ride training plan"
- "haute route training plan"
- "time trial training plan"
- "100 mile training plan"
- "cycling event training plan"
- [cycling training plan trainingpeaks]
- "hill climb training plan"

Watch note: "100 mile training plan" is ambiguous (100-mile running ultras exist). The old campaigns used it as a cycling theme and got cycling-context matches, but check its search terms weekly for run-intent leakage; if it leaks, replace with "100 mile sportive training plan" and "100 mile bike ride training plan".

**Headlines (15):**
1. Cycling Training Plans
2. Sportive Training Plans
3. Time Trial Training Plans
4. Written for Named Events
5. Plans From £39.99
6. Delivered on TrainingPeaks
7. Coach-Built, Not Generic
8. One-Off Price, No Contract
9. Built for the Actual Course
10. Start Training This Week
11. From a 5.0 Rated Coach
12. Coached a Welsh TT Champion
13. Your Event, Your Plan
14. Buy Once, Train Anywhere
15. Find Your Event Plan

**Descriptions (4):**
1. Cycling training plans written for named events. From £39.99, no subscription.
2. Built by the coach behind a Welsh 100 TT champion. Real plans for real events.
3. Buy once, load it into TrainingPeaks, start this week. Built by a real coach.
4. Sessions built around the demands of your chosen event, not a generic template.

**Pinning:** pin headline 1 to position 1.

---

### AG 3.1 Brand (Campaign 3, optional: decision D2)
**Landing page:** https://horsepowercoaching.co.uk/ (homepage is correct here and only here: brand searchers want the front door)

**Keywords (4):**
- [horsepower coaching]
- "horsepower coaching"
- [horsepower coaching uk]
- "horsepower coaching tom cooling"

Critical: this campaign needs aggressive automotive and equestrian negatives ("horsepower" attracts car and horse queries). See section 4.

**Headlines (15):**
1. Horsepower Coaching
2. Horsepower Coaching UK
3. Official Site
4. Coaching by Tom Cooling
5. Triathlon and Cycling Coach
6. Plans From £39.99
7. Coaching From £120 a Month
8. 5.0 Rated on Google
9. Two Ironman Wales Champions
10. Female First Coaching
11. Delivered via TrainingPeaks
12. UK Coach, Online Worldwide
13. 153 Race-Specific Plans
14. See Plans and Coaching
15. Get in Touch Today

**Descriptions (4):**
1. The official Horsepower Coaching site. Training plans, plan only and full 1:1 coaching.
2. Coaching by Tom Cooling. 5.0 Google rating, athletes winning at Ironman Wales.
3. Training plans from £39.99, bespoke plans £120 a month, full coaching £185 a month.
4. Female first coaching, TrainingPeaks delivery, UK based and online worldwide.

**Pinning:** pin "Horsepower Coaching" to position 1.

---

## 4. Negative keywords

### 4.1 Shared list: "HP Core Negatives" (apply to all campaigns)

Broad-match negatives unless bracketed. Grouped by why they are there.

Freebie and DIY intent:
- free
- freebie
- template
- pdf
- spreadsheet
- excel
- diy
- example
- sample

Job and career intent:
- jobs
- job
- vacancy
- vacancies
- salary
- career
- careers
- apprenticeship
- internship

Become-a-coach intent (people wanting to be coaches, not to hire one):
- course
- courses
- certification
- qualification
- qualifications
- "become a coach"
- "how to become"
- level 2
- level 3

Platform and app intent (people wanting software, not a coach):
- zwift
- trainerroad
- sufferfest
- systm
- "garmin coach"
- "apple watch"
- strava
- runna
- app

Research-only intent:
- youtube
- reddit
- podcast
- wiki
- forum
- review (watch this one: it also blocks "horsepower coaching reviews", which is a good brand query; keep "review" OFF the brand campaign, ON the other two)

Audit-derived (terms that actually spent money in the old Smart campaigns with no buying intent, s11.3):
- "how to" (phrase; kills the whole informational class in one line: "how to swim faster" and "how to train for a triathlon" together burned ~£14 in the old campaigns)
- "swim faster"
- [triathlon swim training] (exact; swim-session browsing, not coaching intent)
- [ironman] (EXACT ONLY, see the AG 1.4 note: the bare brand-browse query is waste, "ironman coach" is gold)
- "running coach" (off-target: Tom sells triathlon and cycling coaching; run-only seekers bounced)

Borderline, deliberately NOT negatived: "triathlon personal trainer" (11 clicks in the audit; plausibly real coaching intent, phrase-matched by "personal triathlon coach"). Judge it on its own search-terms line after a month.

### 4.2 Brand campaign extra list: "HP Automotive Negatives" (Campaign 3 only, plus keep watching campaigns 1 and 2)

"Horsepower" invites automotive and equestrian matches:
- car
- cars
- engine
- bhp
- dyno
- torque
- kw
- remap
- tuning
- motorbike
- motorcycle
- horse
- horses
- equestrian
- pony
- riding school

### 4.3 Account-level strategy

- Build both lists as shared negative lists under Tools, not as campaign-level one-offs, so an addition propagates everywhere at once (Runbook RB3).
- The lists above are the starting position. The real negative list is written by the search-terms report: every week, terms that spent money without relevance go into the shared list (Runbook RB6). Expect the first month to add more negatives than any other month; that is the account learning, not a problem.
- Keep the two lists separate on purpose: "review" and "app" class terms behave differently per campaign, and the automotive list must never accidentally block a legitimate coaching query in campaigns 1 and 2 (none of its terms should, but keeping it separate makes that auditable).

---

## 5. Assets (extensions)

All created at account level unless stated. Exact text below, ready to paste.

### 5.1 Sitelinks (create 6, Google shows up to 4)

| Sitelink text | Description line 1 | Description line 2 | Final URL |
|---|---|---|---|
| Training Plans | 153 race-specific plans | From £39.99, one-off | /plans/ |
| Coached by Tom | Full 1:1 coaching, £185/mo | 15 places, weekly feedback | /coached/ |
| Plan Only | Bespoke plan, £120 a month | Block-by-block feedback | /coaching/ |
| Female Performance | Female first coaching | Not female adapted | /female-performance/ |
| About Tom | Coach and racer | Based in the South West | /about/ |
| Training Blog | Real coaching articles | Written by the coach | /blog/ (confirm the live blog URL before entering) |

Sitelink text limit is 25 characters, description lines 35 characters; all of the above fit.

### 5.2 Callouts (25-character limit each)

- 5.0 Google Rating
- 15 Coached Places Only
- TrainingPeaks Delivery
- UK Based, Worldwide
- Female First Coaching
- Plans From £39.99
- Ironman Wales Winners
- Real Coach, Not an App

### 5.3 Structured snippets

Header "Services": Triathlon Coaching, Cycling Coaching, Training Plans, Female Performance, Race Planning

### 5.4 Price assets (one per campaign, matched to the campaign's tier emphasis)

Type: Services. Currency GBP.

| Item header | Description | Price | Final URL |
|---|---|---|---|
| Training Plans | Race-specific, one-off | From £39.99 | /plans/ |
| Plan Only | Bespoke plan, self directed | £120 per month | /coaching/ |
| Coached by Tom | Full 1:1 coaching | £185 per month | /coached/ |

Price asset headers are limited to 25 characters and descriptions to 25 characters; the above fit.

### 5.5 Call asset

Add Tom's business number, UK hours only (set an asset schedule, suggest 09:00 to 19:00). Only if Tom actually wants inbound calls; if the funnel is deliberately form-first, skip the call asset entirely and rely on the contact page. Decision D7.

### 5.6 Location asset

The Google Business Profile is listed at Clevedon (kept for search continuity). Linking it attaches the 5.0 rating and map presence to ads. Link it, but note the mismatch with Truro is visible to anyone who looks; that is an existing business decision, not an ads decision. If Tom updates the GBP location later, nothing in the ads account needs to change, the link follows the profile.

### 5.7 Image assets

Square (1200x1200) and landscape (1200x628) images: real athlete photography from the site, the Horsepower logo mark, nothing stock. Minimum 4 images. Note: image assets are optional at launch; do not hold up the build for them, add within the first fortnight.

### 5.8 Lead form asset

Considered and rejected for launch. Google-hosted lead forms lower friction but decouple the lead from the site's qualification flow (the application/contact form frames the 15-place scarcity and tiers). At £185/month with 15 places, we want fewer, better leads. Revisit only if form-fill volume is the binding constraint at scale.

---

## 6. Bidding and budget

### 6.1 Bidding progression

| Phase | Condition | Strategy |
|---|---|---|
| 1. Launch | 0 to ~15 conversions/month in account | Maximise Clicks WITH a max CPC bid limit. Caps informed by the audit's observed CPCs (head coaching terms £0.60 to £0.80, plan terms roughly £0.40 to £0.70, brand ~£0.09, all under Smart matching): set £1.50 on Coaching, £1.00 on Plans, £0.30 on Brand. Exact-match Search CPCs can run higher than Smart's blended CPCs, so validate in week 1; raise a cap if impression share is starved, lower it if clicks come in well under. |
| 2. Learning | roughly 15 to 30 conversions/month, consistently | Maximise Conversions, no target, per campaign. Let it run 2 to 3 weeks. |
| 3. Efficiency | 30+ conversions/month and a stable observed CPA | Add a tCPA at roughly the observed CPA, tighten by 10 to 15 percent per month while volume holds. |

Do not skip phase 1. Smart bidding without conversion data at this budget produces expensive noise. Note the conversion counts above are per-account planning thresholds; the Plans campaign will get there long before Coaching does, and it is fine for the two campaigns to sit in different phases.

### 6.2 Tiered budget plan

Monthly budget is set as daily budget x 30.4.

**Tier 1: Lean start, £120/month (~£4.00/day)**

| Campaign | Daily | Monthly | Rationale |
|---|---|---|---|
| HP Coaching | £2.00 | ~£61 | Highest value per conversion, worth the majority share |
| HP Plans | £1.50 | ~£46 | Volume engine, cheapest conversions, feeds the ladder |
| HP Brand | £0.50 | ~£15 | Only if D2 = yes; otherwise fold into Coaching |

At this tier run only AG 1.1, 1.2, 2.1, 2.2 (plus 3.1 if brand is on). Pause 1.3, 1.4, 2.3, 2.4, 2.5 as built-but-paused, ready to enable. Four live ad groups on £4 a day is already thin; more would starve them all.

**Tier 2: Middle, £300/month (~£10.00/day)**

| Campaign | Daily | Monthly | Change |
|---|---|---|---|
| HP Coaching | £5.00 | ~£152 | Enable AG 1.3 Female Performance and AG 1.4 Ironman |
| HP Plans | £4.00 | ~£122 | Enable AG 2.3, 2.4, 2.5; extend keyword-level race URLs |
| HP Brand | £1.00 | ~£30 | Unchanged |

**Tier 3: Scale, £600/month (~£20.00/day)**

| Campaign | Daily | Monthly | Change |
|---|---|---|---|
| HP Coaching | £9.00 | ~£274 | tCPA if conversion volume supports it |
| HP Plans | £8.00 | ~£243 | Add DSA catch-all ad group (AG 2.6); consider worldwide Plan Store campaign split (D5) |
| HP Brand | £1.00 | ~£30 | Unchanged |
| Reserve | £2.00 | ~£61 | Held for whichever campaign is budget-limited with the best CPA; or seed a PMax test for the Plan Store if 30+ purchase conversions/month exist |

### 6.3 Scale triggers (move up a tier only when ALL of the following hold)

1. The account has run at the current tier for at least 4 full weeks.
2. Search-terms hygiene is done: under 20 percent of the last fortnight's spend went to terms later added as negatives.
3. At least one campaign is flagged "Limited by budget" while its CPA (or, pre-conversion-volume, its CTR and search-term quality) is acceptable.
4. Conversion tracking is verified working (real conversions recorded that match real orders/enquiries; see section 8).

Move down a tier at any time if spend is producing clicks but zero conversions for 3+ weeks with tracking confirmed healthy; that is a landing-page or offer question, not a budget question, and more budget will not fix it.

---

## 7. Geo and audience

### 7.1 Geo

- **Campaigns 1 and 3 (Coaching, Brand): United Kingdom, national.** The coaching is online worldwide; there is no product reason to restrict to the South West, and SW-only would throttle an already small budget. Recommendation is national UK, with the SW connection carried in copy and the About page rather than in targeting. If Tom prefers an SW emphasis, do it as a location bid adjustment (for example +20 percent on Cornwall, Devon, Somerset, Bristol) rather than an exclusion. Decision D1.
- **Campaign 2 (Plans): United Kingdom at launch.** The Plan Store works worldwide, but pricing is in GBP and the copy is UK-voiced. At Tier 3, if Tom wants it, clone the Plans campaign for an English-speaking international group (Ireland, Australia, New Zealand, Canada, USA) with its own budget so international CPCs never cannibalise UK spend. Decision D5.
- **Location setting (all campaigns): "Presence: people in or regularly in your targeted locations"**, never "presence or interest". The default option leaks spend to people merely interested in the UK.

### 7.2 Audience

All audiences added as **Observation only** at launch (no bid adjustments until there is data; nothing is excluded):

- In-market: Triathlon, Cycling, Sports and Fitness Services, Fitness Products and Services
- Affinity: Health and Fitness Buffs, Cycling Enthusiasts, Running Enthusiasts
- Life events: none at launch (weak fit; endurance sport intent is not life-event shaped)
- Your data: all-site visitors (from the Google tag) as an observation segment; becomes a remarketing option later, and a useful lens on whether ads reach people who behave like existing visitors

After 4+ weeks, if an observed segment converts meaningfully better, apply a positive bid adjustment (start +10 to +20 percent). Do not exclude any segment on thin data.

---

## 8. Conversion tracking plan

Nothing launches until this section is built and verified (Runbook RB0). Spending before tracking works is the single most common small-account mistake.

### 8.1 Conversion actions

| # | Action | Type | Value | Count | Primary/Secondary |
|---|---|---|---|---|---|
| C1 | Plan Store purchase | Purchase | Actual order value (£39.99+) | Every | Primary |
| C2 | Coaching enquiry (contact/apply form submit for Plan Only or Coached) | Lead | Static £40 placeholder (see note) | One | Primary |
| C3 | Phone call from ads (call asset) and calls from site (if call tracking enabled) | Lead | Static £40 placeholder | One | Primary (only if D7 = calls wanted; otherwise Secondary) |
| C4 | TrainingPeaks outbound click from a plan page | Micro | No value | One | Secondary |
| C5 | Contact page view (fallback diagnostic) | Micro | No value | One | Secondary |

Note on C2/C3 value: £40 is a placeholder so value-based reporting is not empty, not a measured lead value. Once Tom knows the enquiry-to-signup rate, set value = £185 x expected months retained x enquiry-to-signup rate. That is a calculation to do with real numbers, not to invent now.

### 8.2 Plan Store purchase: implementation reality

The checkout path decides the implementation, and it must be confirmed on the live site before RB0 (it is step 1 of that runbook):

- **If checkout completes on horsepowercoaching.co.uk (Stripe embedded/Payment Element):** standard Google tag purchase event on the confirmation page, with transaction value and ID. Cleanest case.
- **If checkout redirects to Stripe Checkout (stripe.com) and returns to a success URL on the site:** fire the conversion on the success/return page. Ensure the success URL carries enough context (session id) to dedupe, and that the Google tag is on that page.
- **If fulfilment happens on TrainingPeaks' side (buyer pays or claims the plan on trainingpeaks.com):** the purchase is invisible to our tag. Then C4 (TrainingPeaks outbound click) is promoted to the best available proxy, marked Secondary still, and the honest position is that Plan Store ROAS cannot be measured directly. In that case prioritise fixing the checkout flow so money lands via the site's own Stripe before scaling Plans spend. Flag this loudly if found.

If GA4 already tracks purchases, prefer importing the GA4 purchase event into Google Ads over double-tagging (one source of truth). Either way: one purchase conversion action, not two.

### 8.3 Primary vs secondary discipline

Only C1 and C2 (plus C3 if calls are wanted) are Primary, meaning they drive smart bidding later. C4 and C5 stay Secondary forever; they are diagnostics. If a secondary action is ever accidentally set Primary, smart bidding will happily optimise for cheap outbound clicks instead of purchases. Check this in every monthly review.

### 8.4 Consent and GA4

- Link GA4 and Google Ads (RB0) for audience sharing and cross-checking.
- The site's cookie consent mechanism must grant ad_storage/analytics consent signals correctly (Consent Mode). If the site has no consent banner wired to Consent Mode, conversions will undercount in the UK. Verify during RB0; if it is missing, that is a site task to complete before trusting any conversion numbers.

---

## 9. Measurement and KPI framework

### 9.1 What each tier can afford per acquisition (planning assumptions to validate)

These are reasoned ceilings, not benchmarks, and every input marked "assumed" needs replacing with observed data as it arrives.

Do not reach for the old account's numbers here: the Smart campaigns report 347 all-time "conversions", but those are Smart's auto-counted actions (calls, map views, generic website actions), not tracked purchases or enquiries. They are not a CPA basis and must never be quoted as one. Real CPA starts from zero when RB0's tracking goes live.

- **Plan Store:** price £39.99, near-zero marginal cost. A first-pass ceiling is CPA at or below roughly £20 to break even inside the first purchase alone (assuming roughly half the price is an acceptable acquisition cost for a digital product; Tom to confirm his own margin logic). Any step-up to coaching is upside on top.
- **Plan Only:** £120/month. Assumed retention is the unknown; using an illustrative 4 months (assumption to validate against Tom's real churn), gross revenue per signup is £480. A CPA ceiling of £60 to £100 per signup would be comfortable IF enquiry-to-signup conversion is decent; per enquiry (which is what ads actually measures) divide by the enquiry-to-signup rate once known.
- **Coached by Tom:** £185/month, 15 places. Illustrative 6-month retention (assumption to validate) gives £1,110 per signup; even a £150 CPA per signup would be fine. But with only 15 places, the real constraint is availability, not CPA: when full, pause AG 1.4-style "apply now" pressure or let ads feed a waiting list (copy change, Tom's call at the time).

### 9.2 What "good" looks like at this budget

Honest framing: at £120/month with the audit's observed CPCs (£0.60 to £0.80 on coaching head terms, cheaper on plan terms), the account buys roughly 150 to 250 clicks a month if exact-match CPCs land near the Smart-era numbers, and 75 to 120 if they come in at double. Either way that is enough to judge search-term quality and CTR, and enough for the Plan Store to convert a handful of purchases if the pages do their job; it is NOT enough for statistically clean CPA numbers on coaching leads inside a month. Judge the first 6 to 8 weeks on leading indicators, not CPA.

The one hard benchmark we own: the Smart campaigns ran at 0.8 to 1.0 percent CTR over the last month, homepage-landing and loosely matched. Tightly themed ad groups with deep links should beat that by a multiple. If the new structure is not clearly above the old CTR by week 2, the copy-to-query match is wrong somewhere; find it in the search-terms report.

Leading indicators, weeks 1 to 4:
- Week 1: impressions flowing in every live ad group; CPCs within 2x of the audit-observed numbers; zero policy disapprovals; search terms mostly relevant.
- Week 2: CTR by ad group (planning assumption to validate: mid single digits for tightly themed search ads; anything under ~2 percent is barely better than the old Smart campaigns and needs a relevance investigation); negatives added from the first search-terms pass.
- Weeks 3 to 4: first conversions recorded and cross-checked against real orders and real enquiry emails (numbers must reconcile; if Ads shows conversions Tom cannot match to reality, stop and fix tracking); impression share and "Limited by budget" flags noted per campaign.

### 9.3 Review cadence

| Cadence | Scope | Runbook |
|---|---|---|
| First 72 hours | Delivery, disapprovals, search terms, CPC sanity | RB5 |
| Weekly (15 to 20 min) | Search-terms mining, negatives, budget pacing | RB6 |
| Monthly (45 to 60 min) | CPA by ad group, asset performance, bid strategy phase check, tier decision, organic-vs-paid cannibalisation check | RB6 |
| Quarterly | Structure review: promote race keywords to ad groups, retire ad groups organic now covers, revisit PMax/DSA decisions | RB6 |

---

## 10. SEO and AI-crawl alignment

The site's organic strength is an asset for the paid account, in three concrete ways:

1. **Vocabulary consistency lifts Quality Score.** Ad copy above deliberately mirrors the site's ranked vocabulary and structured-data claims: "race-specific training plans", "TrainingPeaks", "female first, not female adapted", tier names and exact prices. Landing-page experience and ad relevance both improve when the ad, the query and the page use the same words. When editing ads, pull phrasing from the landing page itself, not from a thesaurus.
2. **Final URLs are the SEO landing pages.** Every ad group above deep-links to the page built and ranked for that intent. Never point ads at the homepage (brand campaign excepted) and never build separate "PPC landing pages" that fork the content; the SEO pages are the best pages the business has.
3. **Truth parity.** The ads claim only what the site's structured data and review profile claim: 5.0 rating from 15 reviews, 153 plans, named champions, exact prices. If a price or the review count changes on the site, the ads and price assets change the same day. A mismatch between ad and page is both a Quality Score drag and a trust leak.

**The cannibalisation decision (partially settled by the audit):** the brand verdict is in: 190 paid clicks on "horsepower coaching" at ~£0.09 each, on a term the site owns organically, is observed self-cannibalisation, so the brand campaign defaults to off (D2). For the non-brand head terms the per-term work remains: before enabling each head-term ad group, check Search Console for that term's average position and check the live SERP for competitor ads. Own position 1 with no ads above you: leave that exact term paused, spend the money on terms you do not yet win. Competitors advertising above your organic number 1: bid, because the top of the page is being taken either way. Record the per-term verdicts in section 11.5.

---

## 11. CURRENT ACCOUNT AUDIT (completed 2026-08-16 from Tom's screenshots)

Account 223-337-7250 runs 2 campaigns. Headline finding, repeated from section 0 because it governs the migration: **both are Google Smart campaigns** (account header "All Smart campaigns", keyword-theme targeting, homepage-only landing, Smart auto-"conversions"). Smart campaigns cannot be converted to standard Search; RB4 is therefore build-new, run briefly in parallel, pause-old-never-delete.

### 11.1 Per-campaign summary

| | Bespoke Cycling Coaching | Bespoke Triathlon Coaching |
|---|---|---|
| Type / status | Smart campaign, Active | Smart campaign, Active |
| Daily budget | £0.64 (~£19/month) | £0.71 (~£22/month) |
| Last ~month (20 Jul to 16 Aug) | £8.65, 7K impressions, 56 clicks | £10.43, 4.37K impressions, 44 clicks |
| Last-month CTR / CPC | ~0.8% / ~£0.15 | ~1.0% / ~£0.24 |
| All-time (since ~2020) | £1,773.74, 1.1M impr, 5,630 clicks | £1,176.90, 472K impr, 3,230 clicks |
| All-time CTR / blended CPC | ~0.5% / ~£0.32 | ~0.7% / ~£0.36 |
| Smart "conversions" all-time | 240, plus 652 local actions | 107, plus 474 local actions |
| Landing page | Homepage only | Homepage only |
| Keyword themes | cycling coaching, cycle coach, cycle coaching, 100 mile training plan, cycle training plan, haute route, century ride training plan, haute route training plan, sportive training plan | triathlon coach, ironman coach, triathlon training, triathlon coaching, triathlon training plan, ironman coaching, online triathlon coaching, 121 triathlon coaching, ironman training plan, get faster at ironman |

Conversion-tracking reality: the 347 combined all-time "conversions" are Smart's loose auto-actions (calls, map interactions, website actions). There is no purchase or lead tracking in the account. Treat historical CPA as unknown. RB0 builds real tracking before the new structure spends a pound.

Both campaigns are also underspending their already tiny budgets (~£19 delivered against ~£41/month capacity last month). The account is idling, which is exactly why relaunch-scale budget must go into the new structure rather than feeding the Smart campaigns more money.

### 11.2 Current ads (4 Smart ads, all landing on the homepage)

1. "Ironman Coaching | Bespoke Triathlon Coaching | Long Distance..." / "Asking yourself how to train for an Ironman? Get in touch with our specialist long distance triathlon coach."
2. "Celtman Coaching | XTRI Coaching | Norseman Coaching" / "Get in touch to chat to our XTRI specialist coach. Asking yourself how you prepare for an Extreme Triathlon?"
3. "How to Train Like A Pro | Cutting Edge Training Methods | Triathlon..." / "Want a coach who understands the most current science in exercise physiology?..."
4. "Female Specific Training | Menstrual Cycle Optimised | World Class..." / "Get in touch with our award winning triathlon specialist coach. Completely bespoke, female specific training..."

Assessment: the copy instincts were sound (Ironman specialism, XTRI niche, female-specific angle: ad 4 is early validation of the Female Performance positioning, ad 2 justifies the optional XTRI keywords in AG 1.4). The structural faults are that everything lands on the homepage, nothing names a price or a tier, and the Plan Store does not exist anywhere in the account.

### 11.3 Search terms, all-time, by spend (the evidence base for sections 3 and 4)

Winners: proven coaching intent (mapped ad group in brackets):

| Term | Clicks | Spend | ~CPC | Maps to |
|---|---|---|---|---|
| cycling coach | 164 | £124 | £0.76 | AG 1.2 |
| triathlon coach | 96 | £61 | £0.64 | AG 1.1 |
| triathlon coaching | 89 | £70 | £0.79 | AG 1.1 |
| triathlon coach near me | 75 | £43 | £0.57 | AG 1.1 |
| cycle coaching | 73 | £46 | £0.63 | AG 1.2 |
| cycling coaching | 71 | £43 | £0.61 | AG 1.2 |
| cycling coach near me | 64 | £32 | £0.50 | AG 1.2 |
| ironman coach | 45 | £28 | £0.62 | AG 1.4 |
| cycling coaches near me | 36 | £20 | £0.56 | AG 1.2 (close variant) |
| triathlon coaches | 33 | £21 | £0.64 | AG 1.1 (close variant) |
| triathlon coaching uk | 26 | £20 | £0.77 | AG 1.1 |
| ironman coach uk | 24 | £13 | £0.54 | AG 1.4 |
| triathlon coach london | 24 | £16 | £0.67 | AG 1.1 |
| triathlon coaches near me | 24 | £13 | £0.54 | AG 1.1 (close variant) |
| cycle coaching uk | 21 | £10 | £0.48 | AG 1.2 |
| cycle coach | 20 | £12 | £0.60 | AG 1.2 |
| cycling coaches | 19 | £11 | £0.58 | AG 1.2 (close variant) |
| cycling coaching near me | 17 | £11 | £0.65 | AG 1.2 (close variant) |
| online cycling coach | 16 | £10 | £0.63 | AG 1.2 |
| online triathlon coaching | 15 | £11 | £0.73 | AG 1.1 |
| triathlon coach uk | 16 | £10 | £0.63 | AG 1.1 |
| online triathlon coaching uk | 16 | £9 | £0.56 | AG 1.1 (close variant) |
| personal cycling coach near me | 16 | £8 | £0.50 | AG 1.2 (close variant) |
| cycle coaching near me | 18 | £7 | £0.39 | AG 1.2 (close variant) |
| ironman coaching | 18 | £11 | £0.61 | AG 1.4 |
| triathlon coaches uk | 9 | £8 | £0.89 | AG 1.1 (close variant) |
| triathlon coaching near me | 12 | £6 | £0.50 | AG 1.1 (close variant) |
| triathlon coaching london | 7 | £5 | £0.71 | AG 1.1 (close variant) |

Plan-intent terms: real demand the account never monetised (all landed on the homepage with a coaching ad; every one maps to Campaign 2):

| Term | Clicks | Spend | Maps to |
|---|---|---|---|
| cycling training plan | 27 | £19 | AG 2.5 / AG 2.1 |
| triathlon training plan | 21 | £12 | AG 2.1 |
| triathlon training | 18 | £12 | AG 2.1 (watch: partly informational) |
| plus Smart themes with delivery history: ironman training plan, century ride training plan, haute route training plan, sportive training plan, 100 mile training plan, cycle training plan | | | AG 2.2 / 2.5 |

Brand (self-cannibalisation, feeds decision D2):

| Term | Clicks | Spend | ~CPC |
|---|---|---|---|
| horsepower coaching (via cycling campaign) | 123 | £10.53 | £0.09 |
| horsepower coaching (via triathlon campaign) | 67 | £6.88 | £0.10 |

Wasters: harvested into the shared negative list (section 4.1 audit-derived block, applied in RB3 before launch):

| Term | Clicks | Spend | Why waste |
|---|---|---|---|
| how to swim faster | 27 | £6.89 | Informational, no buying intent |
| triathlon swim training | 24 | £7 | Session browsing, not coaching intent |
| how to train for a triathlon | 11 | £6.71 | Informational DIY |
| ironman (bare) | 15 | £5.26 | Brand browsing, far too broad |
| running coach | 8 | £5.17 | Off-target discipline |
| triathlon coaching (matched inside the CYCLING campaign) | 18 | £14 | Cross-leak: right query, wrong campaign; the new single-theme structure fixes this by design |

### 11.4 What the audit settles

- **CPC caps (s6.1):** set from the observed £0.60 to £0.80 head-term CPCs, done.
- **Keyword lists (s3):** proven spenders and spelling variants folded into AG 1.1, 1.2, 1.4, 2.5, done.
- **Negative list (s4.1):** audit-derived wasters added, done.
- **Brand (D2):** default no, monthly SERP check, per s10.
- **D6 seed list (races for keyword-level URLs):** start from the proven plan-intent themes: Ironman Wales, Challenge Roth (confirm slugs), Haute Route, a century/100-mile sportive plan, plus Tom's picks from Plan Store sales and Search Console.
- **Priority (D4):** the Plan Store gap is the single biggest unexploited opportunity in the account. The recommended s6.2 split stays coaching-weighted at Tier 1 because coaching revenue per conversion dominates, but if Tom wants one thing to feel quickly, flipping to Plans-led at Tier 1 is defensible; the demand is proven and the CPCs are lower.

### 11.5 Still open after the audit

- Per-term cannibalisation verdicts for non-brand head terms (Search Console position + live SERP per s10). Owner: Tom + RB4 Part A step 4. Verdict table:

| Term | SC avg position | Competitor ads above organic? | Bid / no-bid |
|---|---|---|---|
| triathlon coaching | | | |
| triathlon coach | | | |
| cycling coaching | | | |
| cycling coach | | | |
| ironman coach | | | |
| triathlon training plan | | | |
| cycling training plan | | | |

- Checkout-flow confirmation for C1 (RB0 Part A step 2): still needs doing on the live site; screenshots cannot answer it.
- Whether any Smart "conversion" ever corresponded to a real enquiry: unknowable from the data; treat as no.

---

## 12. Change log

| Date | Change |
|---|---|
| 2026-08-16 | Initial design document written. |
| 2026-08-16 | Current-account audit completed from Tom's screenshots: Smart-campaign finding (s0), audit data filled (s11), CPC caps set from observed data (s6.1), audit-derived negatives (s4.1), proven keywords folded into AG 1.1/1.2/1.4/2.5, brand default flipped to off (s10, D2). |

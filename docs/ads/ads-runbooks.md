# Horsepower Coaching: Google Ads Execution Runbooks

Companion to `ads-strategy-and-campaign-design.md` (referred to below as "the design doc"). That file holds all copy, keywords, budgets and rationale; this file is the click-by-click execution path in the Google Ads web UI via Chrome.

Account: 223-337-7250. Sign in at https://ads.google.com with the account's Google login.

Audit status: the current-account audit is COMPLETE (design doc section 11, from Tom's screenshots, 2026-08-16). Key operational consequence for these runbooks: the two live campaigns ("Bespoke Cycling Coaching", "Bespoke Triathlon Coaching") are **Smart campaigns**. Smart campaigns cannot be converted to standard Search campaigns, so the migration is build-new (RB1), parallel-run briefly, then pause-old-never-delete (RB4). The account may also be in Smart Mode (simplified UI); RB1 step 0 handles the switch to Expert Mode before anything else is built.

General notes before starting:
- Google moves UI labels around a few times a year. The paths below match the current UI (left navigation: Campaigns, Goals, Tools, Billing, Admin). If a label differs slightly, the section names ("Conversions", "Shared library", "Negative keyword lists") are stable enough to find via the search box at the top of the Ads UI (magnifying glass, searches settings and pages).
- Every runbook ends with a verification step. Do not mark a runbook done until its verification passes.
- Nothing spends money until RB5 step 6. Campaigns are built PAUSED throughout.
- Order of execution: DECISIONS page first, then RB0, RB1, RB2, RB3, RB4 (audit part), RB5 (launch), RB4 (pause-old part), RB6 (forever).

---

## DECISIONS TOM MUST MAKE (one page, answer before building)

Write the answers in this file, then build to them.

| # | Decision | Options | Design doc ref | Answer |
|---|---|---|---|---|
| D1 | Geo for coaching campaigns | (a) UK national (recommended) (b) UK national with SW bid boost (c) SW only. Audit note: "near me" and local queries carried real volume in the old campaigns (the Clevedon GBP listing drives them) while Tom coaches online; recommendation is national with "online" and "UK" framing in copy, capturing "near me" via the proven near-me keywords rather than geo restriction | s7.1, s11.3 | ______ |
| D2 | Defend the brand term? | (a) Yes, run Campaign 3 at ~£0.50/day (b) No (NEW DEFAULT after the audit: the Smart campaigns bought 190 brand clicks for ~£17 against a number 1 organic ranking, observed self-cannibalisation). If no: check the brand SERP monthly and reinstate the moment a competitor bids | s0, s10, s11.3 | ______ |
| D3 | Start budget | £______ per month (£120 recommended lean start; tier table s6.2). Audit note: current Smart budgets total ~£41/month capacity and underspend it; whatever D3 is, it goes to the NEW campaigns only | s6.2, s11.1 | ______ |
| D4 | Which tier gets priority budget? | (a) Coaching-led (recommended split in s6.2) (b) Plans-led (flip the Coaching/Plans daily budgets). Audit note: the Plan Store gap is the biggest proven unexploited demand (s11.4), so (b) is defensible if Tom wants early wins | s6.2, s11.4 | ______ |
| D5 | Plan Store worldwide? | (a) UK only at launch (recommended) (b) Clone an international Plans campaign at Tier 3 | s7.1 | ______ |
| D6 | Which races get keyword-level URLs first? | List 10 to 20 race slugs. Audit seed list: Ironman Wales, Challenge Roth, Haute Route, century/100-mile sportive, plus picks from Plan Store sales and Search Console | s2.2, s11.4 | ______ |
| D7 | Inbound calls wanted? | (a) Yes: add call asset + call conversion (b) No: form-first funnel, skip call asset | s5.5, s8.1 | ______ |
| D8 | Coached tier full? | If the 15 places are currently full, AG 1.1/1.2/1.4 copy stays live but "Apply" framing feeds a waiting list; confirm current availability | s9.1 | ______ |

---

## RB0: Pre-flight: conversion tracking, tags, GA4

Goal: conversions C1 to C5 from design doc s8.1 exist, fire correctly, and are classified Primary/Secondary correctly. No campaign work happens until this passes.

### Part A: Establish the tagging baseline

1. Open https://horsepowercoaching.co.uk in Chrome. Open DevTools (Cmd+Option+I), Network tab, filter "collect". Reload the page.
   - Looking for requests to `google-analytics.com/g/collect` (GA4) and/or `googleads.g.doubleclick.net` (Google tag). Note what exists.
2. Confirm the checkout reality for the Plan Store (this decides how C1 is built, design doc s8.2):
   - Add a plan to checkout on the live site and proceed to (but not through) payment. Record: does payment happen on horsepowercoaching.co.uk, on a stripe.com Checkout page with a return URL, or on trainingpeaks.com?
   - If it is the TrainingPeaks case, stop and flag it: C1 cannot be tracked as a purchase, see design doc s8.2 for the fallback posture.
3. Confirm the site's cookie banner exists and is wired to Google Consent Mode: in DevTools Console on first visit (before accepting), run `dataLayer` and look for a consent event, or check the banner tool's documentation. If there is no Consent Mode wiring, record it as a site task; conversion counts will be understated until fixed.
4. Verification A: you can state, in writing, (i) which tags are on the site, (ii) where checkout completes, (iii) consent status.

### Part B: Link GA4 (if GA4 is on the site)

1. Google Ads left nav: **Tools -> Data manager** (or Tools -> Linked accounts).
2. Find **Google Analytics (GA4)**, click Link, choose the site's GA4 property, enable personalised advertising and auto-tagging when offered.
3. In GA4 (analytics.google.com): Admin -> Product links -> Google Ads links: confirm the link shows.
4. Verification B: the link status reads Linked in both UIs.

### Part C: Create the conversion actions

Path for each: **Goals -> Conversions -> Summary -> + New conversion action**.

1. **C1 Plan Store purchase.**
   - If GA4 already has a `purchase` event: choose **Import -> Google Analytics 4 properties -> Web**, select `purchase`, import. Category: Purchase. Value: use event value. Count: Every.
   - If not: choose **Website**, enter the site URL, let it scan, then create manually: Category Purchase, name `HP Plan Purchase`, value "Use different values for each conversion" (fallback 39.99), Count Every, click-through window 30 days. Install via the on-screen Google tag instructions on the order confirmation/success page (site build task: pass the real transaction value and transaction ID into the event snippet).
2. **C2 Coaching enquiry.** Website conversion, name `HP Coaching Enquiry`, Category "Submit lead form", value 40 (placeholder per design doc s8.1), Count One. Fire on the contact/apply form success state. If the form shows an inline success message rather than a thank-you URL, use a GA4 event or Google tag event snippet on the submit-success callback, not a page-load trigger.
3. **C3 Calls** (only if D7 = yes). + New conversion action -> Phone calls -> "Calls from ads using call assets". Name `HP Call From Ads`, Category "Phone call lead", value 40, Count One, minimum call length 60 seconds.
4. **C4 TrainingPeaks click.** Website conversion, name `HP TP Outbound Click`, Category "Other", no value, Count One, and after creating set **Primary/Secondary = Secondary** (Goals -> Conversions -> Summary -> click the action -> Edit settings).
5. **C5 Contact page view.** Website conversion on the contact page URL, name `HP Contact Pageview`, Category "Page view", no value, Count One, set Secondary.
6. Set C1 and C2 (and C3 if built) to **Primary**; confirm C4 and C5 are **Secondary**. This controls what smart bidding optimises later; getting it wrong is the classic failure (design doc s8.3).

### Part D: Fire-test every conversion

1. In Chrome, use Tag Assistant (tagassistant.google.com) connected to the live site, or DevTools Network filtered to `googleadservices.com/pagead/conversion`.
2. Complete a real test of each: submit the contact form (use an obvious test message so Tom can ignore the enquiry), click a TrainingPeaks outbound link, and if feasible make a real minimum purchase and refund it (the only honest end-to-end test of C1).
3. **Goals -> Conversions -> Summary**: within a few hours to a day, each tested action's status should move from "No recent conversions"/"Unverified" to recording. Tag statuses should read "Recording conversions" (a new tag can sit at "Needs attention" for 24 to 48 hours; recheck next day rather than rebuilding).
4. Verification D (gate for everything downstream): every Primary action has recorded at least one test conversion that Tom can match to his test activity, and statuses are healthy. Write down date/time of the tests so the test conversions can be mentally excluded from week-1 stats.

---

## RB1: Build the Search campaigns

Prerequisite: RB0 verified, DECISIONS answered. Copy source: design doc section 3 (paste exactly; headlines and descriptions are pre-counted against character limits).

### Step 0: Get out of Smart Mode (do this before any campaign work)

The audit shows the account running Smart campaigns under an "All Smart campaigns" header. If the whole UI looks simplified (no left nav with Campaigns/Goals/Tools, no keyword tabs), the account is in Smart Mode and standard Search campaigns cannot be built from it.

1. In the Smart-Mode UI, open the Settings/tools menu (gear or wrench icon, top right) and look for **Switch to Expert Mode**.
2. Read the confirmation: the switch is one-way (you cannot go back to the simplified UI) but it does NOT touch the existing Smart campaigns; they keep running unchanged and become manageable from the full UI.
3. Confirm the switch. Verify: the left navigation now shows Campaigns, Goals, Tools, Billing, and the two Smart campaigns appear in the Campaigns table with type "Smart".
4. If the account already shows the full Expert UI, skip this step; nothing to do.

### Part A: Campaign 1, HP | Coaching | Search

1. Left nav **Campaigns -> + (New campaign)**.
2. Objective: choose **Create a campaign without a goal's guidance** (avoids Google auto-attaching goals; we control conversion goals manually). Campaign type: **Search**.
3. If asked for results type, select Website visits, enter https://horsepowercoaching.co.uk, continue.
4. Campaign name: `HP | Coaching | Search`.
5. **Bidding:** click Bidding -> select **Clicks** -> tick **Set a maximum cost per click bid limit** -> enter £1.50 (audit-derived: observed head-term CPCs ran £0.60 to £0.80 under Smart matching, design doc s6.1 and s11.3). Do NOT select a conversion-based strategy yet (design doc s6.1 phase 1).
6. **Campaign settings:**
   - Networks: UNTICK "Include Google search partners". UNTICK "Include Google Display Network". Both off.
   - Locations: per D1. For UK national: Enter another location -> United Kingdom. Then expand **Location options** and set Target to **Presence: People in or regularly in your targeted locations**. This sub-step is mandatory; the default leaks spend (design doc s7.1).
   - Languages: English.
   - Audience segments: click Add -> Search the segments from design doc s7.2 (In-market: Triathlon, Cycling, Fitness Products and Services; Affinity: Health and Fitness Buffs, Cycling Enthusiasts, Running Enthusiasts) -> at the bottom select **Observation** (NOT Targeting). Wrong radio button here silently shrinks reach to almost nothing.
   - Expand More settings: Ad rotation "Optimise"; no start/end date; ad schedule: all day (calls-only schedule handled on the call asset, not here).
7. **Budget:** daily budget per D3/D4 (lean start: £2.00/day).
8. **Ad group 1 (AG 1.1 Triathlon Coaching):**
   - Ad group name: `Triathlon Coaching`.
   - Keywords: paste the AG 1.1 list from the design doc, one per line, WITH the brackets and quotes exactly as written (brackets/quotes in the paste set the match type).
9. **RSA for AG 1.1:**
   - Final URL: https://horsepowercoaching.co.uk/triathlon-coaching/
   - Display path (the two 15-character path fields after the domain): `triathlon` / `coaching`.
   - Paste the 15 headlines and 4 descriptions from the design doc AG 1.1.
   - Pinning: hover the designated headline (design doc pinning note), click the pin icon, choose position 1. Nothing else pinned.
   - Ad Strength: aim for Good or better. If it nags about more headlines, ignore; 15 is the maximum and variety is already built in. Do not weaken copy to chase Excellent.
10. Click **Done**, then **+ New ad group** and repeat steps 8 to 9 for AG 1.2 Cycling Coaching (and, if launching above Tier 1, AG 1.3 and AG 1.4). At Tier 1, still build 1.3 and 1.4 now if time allows, then pause those two ad groups after publish (build once, enable later).
11. Skip the assets screen for now if offered (RB2 does assets properly at account level), or add sitelinks here if the flow insists, matching RB2 text.
12. Review screen -> **Publish campaign**.
13. Immediately: Campaigns list -> select `HP | Coaching | Search` -> Edit -> **Pause**. Also pause ad groups 1.3/1.4 individually if built but not in this tier (open the campaign -> Ad groups -> tick -> Edit -> Pause).
14. **Campaign-level conversion goals check:** open the campaign -> Settings -> Goals (or "Conversion goals"): it should use the account-default goals, which after RB0 are C1+C2(+C3). Remove any auto-added goal that is not in that set.
15. Verification: campaign status Paused (not "Pending review" errors); 2 to 4 ad groups each showing the right keyword count; each RSA preview renders with correct URL; no disapprovals yet (recheck in RB5); networks show Search only; location shows United Kingdom with Presence setting.

### Part B: Campaign 2, HP | Plans | Search

1. Repeat Part A steps 1 to 7 with: name `HP | Plans | Search`; CPC cap £1.00 (plan-intent terms ran cheaper than coaching terms in the audit); budget per tier (lean: £1.50/day); geo per D5 (UK at launch); all other settings identical.
2. Build AG 2.1 Training Plans exactly as Part A steps 8 to 9, final URL https://horsepowercoaching.co.uk/plans/, display path `plans` / `race-specific`.
3. Build AG 2.2 Ironman Race Plans:
   - Keywords: paste the AG 2.2 list.
   - RSA final URL: /plans/ with the AG 2.2 copy.
   - **Keyword-level final URLs** (the deep-link mechanism, design doc s2.2): after the ad group exists, open it -> Keywords -> hover a race keyword -> pencil/edit -> expand **Final URL** (sometimes under "Edit -> Change final URLs" or the keyword's detail panel) -> paste the exact race-page URL copied from the live site's address bar (never typed from memory). Repeat for every race keyword on the D6 list.
4. Build AG 2.3, 2.4, 2.5 the same way (pause any not in the current tier after publish).
5. Publish, then pause the campaign as in Part A step 13.
6. Verification: same checks as Part A, PLUS: click 3 random keyword-level final URLs from the keywords table (the URL itself, or copy-paste to a tab) and confirm each loads the correct race page with a 200, not a redirect chain or 404.

### Part C: Campaign 3, HP | Brand | Search (only if D2 = yes; audit default is NO, see D2)

1. Repeat Part A with: name `HP | Brand | Search`; CPC cap £0.30 (brand clicks cost ~£0.09 in the audit); budget £0.50/day; single ad group `Brand` with AG 3.1 keywords/copy; final URL https://horsepowercoaching.co.uk/.
2. Publish, pause.
3. Verification: as Part A. Note the automotive negative list gets attached in RB3 before this campaign ever unpauses.

---

## RB2: Assets (extensions) at account level

Source text: design doc section 5. Assets built at account level apply to all campaigns automatically.

1. Left nav **Campaigns -> Assets** (or Ads & assets -> Assets in older layouts). Click **+**.
2. **Sitelinks:** + -> Sitelink -> "Add to: Account" -> create all 6 from the design doc s5.1 table (text, two description lines, final URL each). Before saving each, open its final URL in a tab and confirm it resolves (especially the blog URL, flagged in the design doc as confirm-before-entering).
3. **Callouts:** + -> Callout -> Add to: Account -> paste the 8 callouts from s5.2.
4. **Structured snippets:** + -> Structured snippet -> Add to: Account -> Header "Services" -> the 5 values from s5.3.
5. **Price asset:** + -> Price -> Add to: Account -> Type Services, currency GBP -> three rows from the s5.4 table.
6. **Call asset** (only if D7 = yes): + -> Call -> Add to: Account -> country UK, Tom's number -> Advanced: schedule 09:00 to 19:00 Mon to Sun (adjust to taste). Confirm call reporting is ON so C3 records.
7. **Location asset:** + -> Location -> link the Google Business Profile (sign-in prompt uses the GBP owner account). Accept the Clevedon listing per design doc s5.6.
8. **Images** (within the first fortnight, not blocking): + -> Image -> upload at least 4 real photos per s5.7 (1200x1200 and 1200x628 crops).
9. Verification: Campaigns -> Assets -> table view shows every asset with status Approved or Under review (recheck approvals in 24 to 48 hours); Association column reads Account. Then open each campaign -> Assets and confirm the account assets are inherited (no campaign-level overrides present).

---

## RB3: Negative keyword lists

Source: design doc section 4.

1. Left nav **Tools -> Shared library -> Exclusion lists** (may be labelled "Negative keyword lists").
2. **+ New list**, name `HP Core Negatives`. Paste every term from design doc s4.1, one per line, as broad negatives except any shown in brackets/quotes. IMPORTANT per s4.1: create the list WITHOUT the term `review`, then add `review` as a campaign-level negative directly on Campaigns 1 and 2 only (it must not block brand "reviews" queries). Campaign-level path: open the campaign -> Keywords -> Negative search keywords -> + .
3. **+ New list**, name `HP Automotive Negatives`. Paste every term from s4.2.
4. Apply the lists: from the list page, **Apply to campaigns**:
   - `HP Core Negatives` -> all campaigns.
   - `HP Automotive Negatives` -> `HP | Brand | Search` (and optionally all campaigns; s4.3 says keep separate but applying to all is safe since no coaching query contains those terms; if in doubt, Brand only, and watch the search-terms report).
5. Audit hook (RESOLVED): the old campaigns' waster search terms (design doc s11.3: "how to" informational queries, "swim faster", [triathlon swim training], bare [ironman], "running coach") are already folded into the s4.1 list you pasted in step 2. Double-check they made it in, especially that [ironman] is entered as EXACT (with brackets) and not broad; a broad "ironman" negative would kill every ironman coach and plan query in the account.
6. Verification: open each campaign -> Keywords -> Negative search keywords: the shared list names appear under "Negative keyword lists"; Campaigns 1 and 2 additionally show the campaign-level `review` negative; Brand campaign shows both lists.

---

## RB4: Migrate the two Smart campaigns (parallel run -> pause, never delete)

The two live campaigns ("Bespoke Cycling Coaching", "Bespoke Triathlon Coaching") are Smart campaigns. Two hard facts drive this runbook:

- **Smart campaigns cannot be converted into standard Search campaigns.** There is no upgrade button. The only migration is: build the new Search campaigns (RB1), run both side by side briefly, then pause the Smart ones.
- **Never delete them.** Paused campaigns keep their history and search-terms data queryable forever; that history (6 years, ~£2,950, 8,860 clicks) is the account's memory. Removed campaigns cannot be re-enabled.

Also note: shared negative lists and most Expert-Mode controls do not apply to Smart campaigns, so do not waste time trying to clean the Smart campaigns up during the parallel window. They run as-is until paused.

### Part A: Audit closure (mostly DONE, two items remain)

1. DONE 2026-08-16: per-campaign spend/CTR/budget, search-terms winners and wasters, ad copy, keyword themes, conversion-tracking reality. All recorded in design doc s11.
2. For the permanent record: open each Smart campaign -> its search terms view, set the date range to all time, and export/screenshot the full report. Save alongside this doc. (Smart campaigns expose less reporting than Search; capture whatever the UI gives.)
3. REMAINING: cannibalisation verdicts for the non-brand head terms. Fill the s11.5 table (Search Console average position + live-SERP competitor-ads check per term). Any term with verdict no-bid: pause that keyword in the new build (keyword-level pause, keep it in the ad group for later).
4. REMAINING: RB0 Part A step 2 (checkout-flow confirmation); screenshots could not answer it.

### Part B: Salvage (already folded into the design; verify, do not redo)

1. Keyword salvage: the audit's winning search terms are already in the design doc s3 keyword lists (AG 1.1, 1.2, 1.4, 2.1, 2.2, 2.5, mapping table in s11.3). During the RB1 build, tick each s11.3 winner off against the ad group you are building; anything missed gets added then (ad group -> Keywords -> +).
2. Copy salvage: the old ads' proven angles are already reflected: Ironman specialism (AG 1.4), female-specific (AG 1.3), XTRI niche (AG 1.4 optional keywords). One deliberate change: the old "How to Train Like A Pro" how-to framing is NOT carried over; it attracts exactly the informational clicks the negative list now blocks.
3. Waster salvage: done via RB3 step 5 (verify the negatives landed).

### Part C: Parallel run and cutover

1. Launch the new campaigns per RB5 while the two Smart campaigns keep running untouched at their existing tiny budgets (£0.64 and £0.71 per day). Do not change the Smart campaigns' budgets or settings during this window.
2. Parallel window: 7 to 14 days maximum. Purpose is continuity of presence while the new campaigns prove delivery, not a fair A/B test (the Smart budgets are too small for that; combined they spend under £1.50 a day). Do not let the window drag.
3. Self-competition check: the Smart campaigns will keep matching some of the same queries the new exact/phrase keywords target. Spend split on those queries is expected and is the reason the window is short. If the new campaigns are delivering cleanly by day 7, cut over then.
4. Cutover: Campaigns table -> tick both Smart campaigns -> Edit -> **Pause**. Apply a label `legacy-smart-2026` (Edit -> Apply label) so they stay visually distinct forever.
5. Budgets: the Smart budgets were never part of the D3 tier maths (the tier table in design doc s6.2 already allocates the full D3 amount to the new campaigns), so nothing to move; just confirm the new campaigns' combined daily budget equals the D3 tier total.
6. Verification: both Smart campaigns show Paused with the legacy label and zero spend the following day; account-level daily spend over the next 3 days equals the new campaigns' budgets only; the brand SERP still shows the site's organic number 1 for "horsepower coaching" (the Smart campaigns were buying brand clicks, s11.3, so post-pause is the moment to confirm organic holds the click, and the first data point for the monthly D2 check).

---

## RB5: Launch checklist, first 72 hours, first week

### Part A: Final pre-launch gate (all boxes must tick)

1. RB0 verification D passed (conversions fire and reconcile).
2. RB1 verifications passed for every campaign being launched; keyword-level URLs spot-checked.
3. RB2 assets Approved or Under review, correct text.
4. RB3 lists applied, including audit wasters (RB4 Part A done).
5. DECISIONS table fully answered.
6. Billing: left nav **Billing -> Settings**: valid payment method, correct GB address and VAT status. An account that stops serving over billing mid-week wastes the learning period.

### Part B: Go live

1. Campaigns list -> tick the new campaigns for this tier -> Edit -> **Enable**. Confirm the intended ad groups within each are Enabled and the deliberately-deferred ad groups stay Paused.
2. Note launch date/time here: ______________.

### Part C: First 72 hours (check twice a day, 5 minutes, HANDS OFF otherwise)

What to look at, in order:

1. **Ad disapprovals:** Campaigns -> Ads: any Disapproved or Limited status -> open the reason. Most likely tripwires: none expected for this copy, but healthcare/personalised-ads flags occasionally hit fitness copy in error; appeal via the ad's status link if the copy is compliant.
2. **Delivery:** each enabled ad group has impressions by hour 24 to 48. An ad group at zero impressions after 48 hours: check its keywords' Status column (below first page bid? low search volume?) and raise the campaign CPC cap one notch (for example £1.50 -> £2.00) if bid-limited.
3. **CPC sanity:** actual average CPC vs the planning assumption. Over 2x assumption: lower cap or note it for the week-1 review; do not chase.
4. **Search terms** (from hour 24): Campaigns -> Insights and reports -> Search terms. Add obvious junk to `HP Core Negatives` immediately (this is the one permitted "touch" in the first 72 hours).
5. What NOT to do in the first 72 hours: no bid strategy changes, no budget changes, no pausing keywords on tiny click counts, no copy edits. Everything is noise at this sample size.

### Part D: First week review (day 7, 20 minutes)

1. Full search-terms pass -> negatives + note any query worth adding as a keyword.
2. CTR by ad group vs the s9.2 leading indicators; investigate under ~2 percent (query-to-copy mismatch is the usual cause).
3. Reconcile any recorded conversions against reality (orders inbox, enquiry inbox). Mismatch = stop and fix tracking before anything else.
4. Impression share: Campaigns table -> Columns -> Modify columns -> Competitive metrics -> add "Search impr. share" and "Search lost IS (budget)". Record baseline.
5. Confirm spend pacing: daily spend can be up to 2x daily budget on a given day (Google's normal overdelivery) but the monthly total will respect budget x 30.4; only act if the month is tracking over.

### Part E: Learning period discipline

Any bid-strategy change (later, per design doc s6.1) restarts a roughly 1 to 2 week learning period during which results whipsaw. Rule: after any bid strategy or major budget change (over ~20 percent), change nothing else for 2 weeks. Calendar it.

---

## RB6: Ongoing optimisation cadence

### Weekly (15 to 20 minutes, same day each week)

1. **Search-terms mining:** Insights and reports -> Search terms, date range last 7 days.
   - Irrelevant terms with spend -> add to `HP Core Negatives` (Tools -> Shared library -> Exclusion lists -> open list -> +). Choose the negative's match type deliberately: a whole irrelevant theme (broad negative on the theme word) vs one bad phrasing (phrase/exact negative).
   - Relevant converting or high-CTR terms not yet keywords -> add as phrase or exact to the matching ad group. If a term does not fit any ad group's theme, note it as a future ad group, do not shoehorn it.
2. **Budget pacing:** Campaigns table, month-to-date spend vs tier plan. "Limited by budget" flag + healthy CPA/search-terms = log it as scale-trigger evidence (design doc s6.3).
3. **Keyword health:** any keyword flagged "Below first page bid" that we care about -> nudge campaign CPC cap or accept the lower position. On Manual/Max Clicks this is the only bid lever; do not micro-manage per-keyword bids at this spend.
4. Log the week in a running notes section at the bottom of this file (date, changes made, why). The log is what makes month reviews fast and prevents re-litigating old changes.

### Monthly (45 to 60 minutes, first week of the month)

1. **Conversion reconciliation first** (nothing else matters if this fails): Ads-recorded conversions vs actual orders and enquiries for the month. Investigate gaps over ~20 percent either way.
2. **CPA and value by ad group:** Campaigns -> Ad groups, columns Conversions, Cost/conv., Conv. value. Compare against the s9.1 ceilings (which by now should be updated with real retention/step-up numbers as they emerge). Pause only on meaningful sample (as a working rule, do not judge an ad group on fewer than ~30 clicks).
3. **Bid strategy phase check** (design doc s6.1): if the account crossed ~15 to 30 conversions/month, move the qualifying campaign to Maximise Conversions (campaign Settings -> Bidding -> Change bid strategy); calendar the 2-week no-touch learning period (RB5 Part E). At 30+ with stable CPA, add tCPA.
4. **RSA asset rotation:** each ad -> View asset details: assets rated Low after meaningful impressions get rewritten (stay within character limits, recount); Best/Good assets stay. Change at most a few assets per ad per month; wholesale rewrites reset ad learning.
5. **Asset (extension) check:** any sitelink/callout disapprovals; price asset still matches live site prices EXACTLY (if the site's pricing changed, fix the same day, design doc s10.3).
6. **Scale/de-scale decision** against the four triggers in s6.3; if moving tiers, apply the s6.2 allocation table (Edit -> Change budgets) and enable the next tranche of ad groups (1.3, 1.4, 2.3 to 2.5, then DSA at Tier 3).
7. **Brand SERP check** (if D2 = no): search "horsepower coaching" in an incognito window; if a competitor's ad appears above the organic listing, revisit D2 and enable Campaign 3.
8. **Primary/Secondary audit:** Goals -> Conversions -> Summary: confirm C4/C5 still Secondary (design doc s8.3).

### Quarterly (design doc s9.3)

1. Promote any race keyword earning roughly a third or more of its ad group's clicks to its own ad group with race-named copy (s2.2 rule).
2. Organic handover: for each paid term, recheck Search Console position; pause paid where organic now owns position 1 uncontested; record verdicts in the s11.2 table.
3. Revisit deferred machinery in order: DSA catch-all (Tier 3), international Plans campaign (D5), PMax for Plan Store (only if 30+ purchase conversions/month, s1.3), Demand Gen for Female Performance (only with real creative).
4. Refresh this file and the design doc: prices, review count, athlete results, plan count are all quoted in live ads and must match the site.

---

## CURRENT-ACCOUNT SCREENSHOT HOOKS: STATUS

Tom's screenshots arrived 2026-08-16 and the audit is folded into design doc s11 and these runbooks. Status of each hook:

1. RESOLVED: per-campaign audit (spend, CTR, budgets, bid setup, search-terms winners and wasters, ad copy, keyword themes, conversion-tracking reality) -> design doc s11.1 to s11.3. Headline: both campaigns are Smart campaigns; see RB4.
2. RESOLVED: CPC caps set from observed CPCs -> RB1 (£1.50 Coaching, £1.00 Plans, £0.30 Brand) and design doc s6.1.
3. RESOLVED: waster terms folded into `HP Core Negatives` -> design doc s4.1 audit block, RB3 step 5.
4. RESOLVED: salvage map -> design doc s11.3 mapping column, RB4 Part B.
5. PART-RESOLVED: D6 seed race list from the audit's plan-intent themes (Ironman Wales, Challenge Roth, Haute Route, century/100-mile sportive); Tom to extend from Plan Store sales and Search Console.

Still open (not screenshot-dependent, needs Tom or live-site time):
- Cannibalisation verdict table, design doc s11.5 (Search Console + live SERP per head term). Feeds keyword-level pauses in RB4 Part A step 3.
- Checkout-flow confirmation for conversion C1 (RB0 Part A step 2): where does Plan Store payment actually complete (site / Stripe Checkout / TrainingPeaks)? This decides the C1 build and is the single biggest remaining unknown.
- Parallel-run start date (set when RB5 Part B fires).

---

## Weekly log

| Date | Runbook step | Change made | Why |
|---|---|---|---|
| | | | |

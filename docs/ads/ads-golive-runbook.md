# Go-Live Runbook: HP | Search | UK

Import file: `docs/ads/horsepower-ads-import.csv`
Account: 223-337-7250. Everything imports PAUSED. Nothing spends a penny until step 7.

Budget when live: £2.10/day, roughly £64 a month, safely under the £70 cap. One campaign, one shared daily budget, Manual CPC.

## The steps

1. **Install Google Ads Editor** (free desktop app from Google), sign in with the account that owns 223-337-7250, and download the account when prompted.

2. **Import the file.** Account menu, Import, From file, select `horsepower-ads-import.csv`. Editor shows a preview of the proposed changes. You should see: 1 campaign (HP | Search | UK, Paused), 5 ad groups, 36 keywords, 20 campaign negatives, 5 responsive search ads. Accept the import into the editing pane (this does not post anything yet).

3. **Set what the CSV cannot carry.** Editor CSV import does not reliably set these, so do them by hand on the campaign before posting:
   - Locations: United Kingdom only. Use "Presence" (people in the UK), not "Presence or interest".
   - Languages: English.
   - Networks: Google Search only. Untick Search Partners and untick Display Network.
   - Optional but worth doing now: pin one headline per ad in Editor. Pin "Triathlon Coaching by Tom", "Cycling Coaching by Tom", "Training Plans From £39.99", "Female First Coaching" and "Coached by Tom, £185 a Month" each to headline position 1 in their ad group's ad, so every ad always leads with what it is.

4. **Review before posting.** Work through the review pane: every ad group, every keyword, every ad. Fix anything Editor flags red. Known caveats to watch for:
   - If Editor rejects the negative keyword rows, the criterion type token is the issue. Fallback: re-import just those rows with Criterion Type "Negative Phrase" / "Negative Exact", or simply add the 20 negatives by hand at campaign level (19 phrase, plus `ironman` as exact only). The exact-only `ironman` negative matters: it blocks the bare brand-browse query while leaving "ironman coach" and "ironman training plan" alive. Do not make it phrase or broad.
   - If Editor complains about the Budget column, set the campaign budget to £2.10/day manually. Check the account currency is GBP while you are there.
   - Ad Strength warnings ("Average") are fine. Do not add headlines to chase the rating.

5. **Post.** Everything uploads paused: campaign Paused, plus Female Performance and Coached 1 to 1 ad groups Paused within it. Confirm in the web UI that the campaign shows as Paused after posting.

6. **Conversion tracking BEFORE enabling anything.** In the Google Ads web UI:
   - Primary conversion: the message/enquiry form submit on https://horsepowercoaching.co.uk/contact/ (this is the lead action; there is no call asset and no call conversion, first contact is message only).
   - Secondary conversion: Plan Store purchase. Still open: the checkout flow needs confirming on the live site first (does payment complete on the site, or hand off to Stripe/TrainingPeaks?). Do not guess this; confirm the flow, then tag the confirmation page. Until it is confirmed, the enquiry conversion is the only one you trust.
   - Do not enable the campaign until at least the enquiry conversion is verified firing on a test submit.

7. **Enable.** When tracking is verified: enable the campaign and leave the 3 live ad groups running (Triathlon Coaching, Cycling Coaching, Training Plans). Keep Female Performance and Coached 1 to 1 paused until budget allows; they are built and ready, enabling them is one click later. This is the moment spend starts, at £2.10/day (~£64/month).

8. **Wind down the old Smart campaigns.** Run the two old Smart campaigns in parallel for 7 to 14 days, then PAUSE them. Never delete them; the history stays useful.

## After go-live

- Nothing in this build spends until step 7 is done deliberately. If spend appears before that, pause the campaign and find what got enabled.
- Weekly: 15 minutes in the search terms report, add negatives for anything irrelevant that spent money. Expect the first month to add the most.
- Monthly: check the live SERP for "horsepower coaching". No brand campaign exists by design (the site ranks 1 organically); if a competitor ever bids on the name, that decision gets revisited.
- Coached 1 to 1 copy says 3 places open. If the places fill or change, update that ad the same day.

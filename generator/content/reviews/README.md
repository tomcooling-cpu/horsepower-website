# Reviews intake (WS-SITE22)

This folder is the single source of truth for the review quotes that render on the
site (the review carousels and pull-quotes). The goal: Tom's screenshots become
slides in one step, with no invented or paraphrased text ever reaching the page.

## The intake, step by step

1. Tom drops the review screenshot files into `inbox/` (this subfolder is
   gitignored, so screenshots never get committed).
2. Each review is transcribed **verbatim** into `reviews.yaml` as one record.
   Transcribe exactly what the reviewer wrote. Do not tidy it, do not complete a
   trailing sentence, do not fix spelling. If a review runs on mid-sentence, close
   it at a natural earlier point and stop; never invent past it.
3. The build (`generator/build.py`) reads `reviews.yaml` and derives
   `CLIENT_QUOTES` and `VERIFIED_QUOTES` from it. Nothing else is a source of
   review text.

## Record format

`reviews.yaml` is a small, dependency-free YAML subset (no PyYAML on the build
host): a list of `- key: value` records. String values are JSON-quoted so verbatim
punctuation round-trips exactly; bare tokens are taken as-is.

```yaml
- text: "The exact review text, verbatim."
  reviewer_display: "Ian C"
  source: google
  gender_tag: male
  event_note: "Cycling athlete"
  pages: coached, coaching
```

| field | meaning |
| --- | --- |
| `text` | the review, transcribed verbatim (JSON-quoted string) |
| `reviewer_display` | first name + surname initial **only**, e.g. `"Ian C"` (never a full surname) |
| `source` | where the review came from, e.g. `google` |
| `gender_tag` | `female`, `male` or `unknown` |
| `event_note` | optional short context, e.g. `"Cycling athlete"`; use `""` if none |
| `pages` | which pages the quote is routed to, comma separated. Home is implicit (it shows every quote). Add any of: `coached`, `coaching`, `female`, `plans`, `about` |

## Hard rules (enforced by build gates)

- **First name + initial only.** Names render as `Ian C`, never a full surname
  (the site-wide client-surname gate fails the build otherwise). Tom Cooling, the
  business owner, is the one exemption elsewhere on the site.
- **No invented reviews.** Every quote that renders in the built HTML must exist
  byte-exact in `reviews.yaml` (rendered-quote gate). A review that is not in this
  file can never appear on the site.
- **The count stays sourced.** The "15 Google reviews" figure shown on the site is
  driven by the existing `REVIEW_COUNT` constant in `build.py`, not by how many
  records are in this file. Adding a transcribed quote here does not change the
  advertised review count.

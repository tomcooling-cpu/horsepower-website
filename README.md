# Horsepower Coaching website

Static marketing + plan-library site for Horsepower Coaching. No framework, no JS
build chain. A small Python generator turns Tom's approved copy plus the live
Plans-for-Sale catalogue into plain HTML served by GitHub Pages.

This is the PHASE 1 rebuild that replaces the GoDaddy-builder site. Nothing here
touches DNS or the live `horsepowercoaching.co.uk` domain; the Pages URL is a
preview only.

## Layout

```
generator/
  build.py            # renders /site from catalogue.json + approved copy
  catalogue.json      # exported from the automated-horsepower store data
  assets/             # style.css, catalogue.js, logo (copied into /site verbatim)
site/                 # generated output, served by GitHub Pages
.github/workflows/    # Pages deploy (uploads ./site as the Pages artifact)
```

## Build

```
python3 generator/build.py
```

The build fails if any quality gate fails: zero em-dashes, approved copy present
byte-exact, every internal link resolves, viewport + unique title + meta
description + image alt text on every page, and card count == live SKU count.

## Analytics and consent (WS-SITE25)

Google Analytics 4 ships in the LIVE build only (`HP_BASE_PATH=''`, Netlify); the
GitHub Pages preview build emits no Google code at all. The measurement ID is the
one constant `GA4_MEASUREMENT_ID` in `generator/build.py` (env `HP_GA4_ID` for a
one-off check), and the live build refuses to run without a valid ID. The privacy
page's `LEGAL_NAME` and `PRIVACY_CONTACT_EMAIL` are constants beside it (gate 17h
checks the page). `assets/consent.js` runs the cookie banner
and loads gtag.js only after the visitor clicks Accept (basic Consent Mode v2);
`assets/analytics.js` sends the events, driven by the `data-ga*` attributes the
generator emits. The privacy page is `/privacy/`; the contact form posts to the
noindex `/contact/thanks/` page, where `generate_lead` fires. The form's `option`
field, pre-selected from `?option=` on the link that led to `/contact/`, is carried
as `lead_option` on `contact_submit` and `generate_lead` (WS-SITE26, gate 18). Its
four values are `plan-only`, `coached-by-tom`, `not-sure` (the default) and
`plan-store`.

## Refreshing the catalogue

The catalogue is exported from the coaching engine repo so the storefront and the
site never drift. In the `automated-horsepower` repo:

```
python3 scripts/export_catalogue.py --out /path/to/horsepower-website/generator/catalogue.json
python3 generator/build.py   # then rebuild here
```

## Deferred to phase 2

Payments / signup flow, contact forms (Contact links to the current site's contact
route), blog migration, and the DNS cutover. See the delivery report.

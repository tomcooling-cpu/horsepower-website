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

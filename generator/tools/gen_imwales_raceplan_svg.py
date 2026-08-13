"""Generate ONE self-contained inline SVG for the Ironman Wales bike course.
Read-only against automated-horsepower course loader + wind model logic.

Panel A: elevation profile (real smoothed GPX), climbs shaded = where power matters.
Panel B: the real IMWA bike route drawn as a MAP in its true geographic shape,
         each segment coloured by head/tail/crosswind for a sample fresh WSW wind
         (from 247.5), with a compass rose showing the wind direction.

Wind model: headwind fraction = cos(travel_bearing - wind_from_bearing), the same
cos(course_bearing - wind_direction) component used in src/race_planner.py.

Map projection: equirectangular, aspect-correct (longitude scaled by cos(mean
latitude)) so the route keeps its true shape; fit into the panel preserving
aspect ratio (uniform scale, never stretched), north up.
"""
import math
import os
import sys

AH = "/Users/tomcooling/Documents/GITHUB/automated-horsepower"
sys.path.insert(0, os.path.join(AH, "src"))

from course_gpx import load_course, parse_gpx, _cumulative_distance, _haversine  # noqa
from climb_detector import smooth_elevation, compute_grade, detect_climbs  # noqa

EVENT = "im_wales"
WIND_FROM_DEG = 247.5   # WSW, a fresh sample day typical of Pembrokeshire
WIND_LABEL = "WSW"

# ── Load real course data ─────────────────────────────────────────────────────
cp = load_course(EVENT, courses_dir=os.path.join(AH, "config", "courses"))
bike = cp.legs["bike"]
pts = parse_gpx(os.path.join(AH, "config", "courses", EVENT, "bike.gpx"))
dist = _cumulative_distance(pts)                 # metres, cumulative
elev = [p[2] if p[2] is not None else 0.0 for p in pts]
selev = smooth_elevation(dist, elev)             # same 50m smoothing as the loader
total_m = dist[-1]
total_km = total_m / 1000.0

# Detected climbs (shared climb_detector). "Where power matters most": sustained
# drags + steep pitches. Shade climbs with a real net gain or a punchy pitch.
grade = compute_grade(dist, selev)
climbs = detect_climbs(dist, grade)
POWER_CLIMBS = [c for c in climbs
                if (c["net_gain_m"] >= 20.0) or bool(c["is_punchy"])]

# ── Wind: bearing per resampled step, then head/tail/cross ─────────────────────
def bearing(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlo = lo2 - lo1
    x = math.sin(dlo) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlo)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0

# Resample to even ~250m steps so bearings are stable (not GPS-jitter noise).
STEP = 250.0
samples = []  # (dist_m, lat, lon)
target = 0.0
i = 0
while target <= total_m and i < len(pts) - 1:
    while i < len(pts) - 1 and dist[i + 1] < target:
        i += 1
    # linear interp between pts[i], pts[i+1]
    d0, d1 = dist[i], dist[i + 1]
    t = 0.0 if d1 == d0 else (target - d0) / (d1 - d0)
    lat = pts[i][0] + t * (pts[i + 1][0] - pts[i][0])
    lon = pts[i][1] + t * (pts[i + 1][1] - pts[i][1])
    samples.append((target, lat, lon))
    target += STEP

wind_seg = []  # (dist_m, headwind_fraction) — one per segment between samples
for j in range(len(samples) - 1):
    b = bearing((samples[j][1], samples[j][2]), (samples[j + 1][1], samples[j + 1][2]))
    frac = math.cos(math.radians(b - WIND_FROM_DEG))  # + head, - tail, ~0 cross
    wind_seg.append((samples[j][0], frac))

def wind_class(f):
    if f > 0.35:
        return "head"
    if f < -0.35:
        return "tail"
    return "cross"

# Distance-weighted share in each class (STEP is constant so count-weighted == dist-weighted)
counts = {"head": 0, "tail": 0, "cross": 0}
for _, f in wind_seg:
    counts[wind_class(f)] += 1
n = len(wind_seg)
share = {k: round(100.0 * v / n) for k, v in counts.items()}

# ── SVG geometry ──────────────────────────────────────────────────────────────
W, H = 1000, 660
PADL, PADR = 64, 26
AX_TOP_A, AX_H_A = 92, 210          # elevation panel (unchanged)
plot_w = W - PADL - PADR
emin, emax = min(selev), max(selev)
espan = max(1.0, emax - emin)

TEAL = "#0D9488"
TEAL_DK = "#0B7A70"
TEAL_SOFT = "#CCFBF1"
INK = "#0F0F0F"
CREAM = "#F5F1E8"
CORAL = "#D2694A"     # headwind = where you spend
STONE = "#B9AE9C"     # crosswind = handling
GRID = "#E4E4E0"

def x_of(m):
    return PADL + plot_w * (m / total_m)

def y_of(e):
    return AX_TOP_A + AX_H_A - AX_H_A * (e - emin) / espan

# Elevation area path (downsample to ~size for a crisp, light path)
STEPX = max(1, len(selev) // 440)
pathpts = [(x_of(dist[k]), y_of(selev[k])) for k in range(0, len(selev), STEPX)]
pathpts.append((x_of(dist[-1]), y_of(selev[-1])))
line = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pathpts)
area = (f"M {pathpts[0][0]:.1f},{AX_TOP_A + AX_H_A:.1f} L "
        + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pathpts)
        + f" L {pathpts[-1][0]:.1f},{AX_TOP_A + AX_H_A:.1f} Z")

# Shade the power climbs on the elevation panel
climb_rects = []
for c in POWER_CLIMBS:
    x0 = x_of(c["start_dist_m"])
    x1 = x_of(c["start_dist_m"] + c["length_m"])
    climb_rects.append(
        f'<rect x="{x0:.1f}" y="{AX_TOP_A:.1f}" width="{max(1.5, x1 - x0):.1f}" '
        f'height="{AX_H_A:.1f}" fill="{TEAL}" fill-opacity="0.16"/>')

# Annotate the two marquee pitches: steepest (max grade) + longest sustained.
steep = max(climbs, key=lambda c: c["max_gradient_pct"])
biggest = max(climbs, key=lambda c: c["net_gain_m"])
def _summit_y(c):
    mid = c["start_dist_m"] + c["length_m"] / 2
    k = min(range(len(dist)), key=lambda j: abs(dist[j] - mid))
    return y_of(selev[k])

def climb_label(c, text, dy, anchor="middle"):
    xm = x_of(c["start_dist_m"] + c["length_m"] / 2)
    yt = _summit_y(c)
    laby = max(AX_TOP_A + 12, yt - dy)      # keep the label inside the plot
    return (f'<line x1="{xm:.1f}" y1="{yt - 5:.1f}" x2="{xm:.1f}" y2="{laby + 3:.1f}" '
            f'stroke="{INK}" stroke-width="1"/>'
            f'<text x="{xm:.1f}" y="{laby:.1f}" text-anchor="{anchor}" '
            f'font-family="Oswald,sans-serif" font-size="13" font-weight="600" '
            f'fill="{INK}">{text}</text>')

ann = climb_label(steep, f"Steepest pitch {steep['max_gradient_pct']:.0f}%", 42)
ann += climb_label(biggest, f"Longest drag {biggest['net_gain_m']:.0f} m", 40, anchor="end")

# x-axis ticks every 20km
xticks = ""
km = 0
while km <= total_km:
    xx = x_of(km * 1000.0)
    xticks += (f'<line x1="{xx:.1f}" y1="{AX_TOP_A + AX_H_A:.1f}" x2="{xx:.1f}" '
               f'y2="{AX_TOP_A + AX_H_A + 5:.1f}" stroke="{GRID}" stroke-width="1"/>'
               f'<text x="{xx:.1f}" y="{AX_TOP_A + AX_H_A + 19:.1f}" text-anchor="middle" '
               f'font-family="JetBrains Mono,monospace" font-size="11" fill="#6B6B6B">{km}</text>')
    km += 20

# y-axis labels (metres)
ylabs = ""
for e in (round(emin), round((emin + emax) / 2), round(emax)):
    yy = y_of(e)
    ylabs += (f'<text x="{PADL - 10:.1f}" y="{yy + 4:.1f}" text-anchor="end" '
              f'font-family="JetBrains Mono,monospace" font-size="11" fill="#6B6B6B">{e}</text>')

# ── Panel B: WIND MAP ─────────────────────────────────────────────────────────
# The route in its true geographic shape, equirectangular + aspect-correct
# (longitude scaled by cos(mean latitude)), fit into the map box preserving
# aspect (uniform scale), north up.
MAP_TITLE_Y = 372
MBX, MBY, MBW, MBH = PADL, 384, 452, 240    # map bounding box
MPAD = 14                                    # inner padding inside the box

# bounds from the resampled route (the same points we draw + colour)
route_lats = [s[1] for s in samples]
route_lons = [s[2] for s in samples]
lat_min, lat_max = min(route_lats), max(route_lats)
lon_min, lon_max = min(route_lons), max(route_lons)
mean_lat = sum(route_lats) / len(route_lats)
coslat = math.cos(math.radians(mean_lat))

pw = (lon_max - lon_min) * coslat            # projected width  (deg * cos lat)
ph = (lat_max - lat_min)                     # projected height (deg)
iw = MBW - 2 * MPAD
ih = MBH - 2 * MPAD
scale = min(iw / pw, ih / ph)                # uniform => true shape, no stretch
xoff = (iw - pw * scale) / 2.0               # centre the route in the box
yoff = (ih - ph * scale) / 2.0

def project(lat, lon):
    px = (lon - lon_min) * coslat
    py = (lat_max - lat)                      # flip: higher latitude -> higher up
    return (MBX + MPAD + xoff + px * scale,
            MBY + MPAD + yoff + py * scale)

# Colour the route per segment; merge consecutive same-class segments into one
# polyline so the inline SVG stays light.
colour = {"head": CORAL, "tail": TEAL, "cross": STONE}
runs = []              # (class, [(X,Y), ...])
prev_cls = None
cur = []
for j in range(len(samples) - 1):
    cls = wind_class(wind_seg[j][1])
    p0 = project(samples[j][1], samples[j][2])
    p1 = project(samples[j + 1][1], samples[j + 1][2])
    if cls != prev_cls:
        if cur:
            runs.append((prev_cls, cur))
        cur = [p0]
        prev_cls = cls
    cur.append(p1)
if cur:
    runs.append((prev_cls, cur))

route_paths = ""
for cls, ptsr in runs:
    pstr = " ".join(f"{x:.1f},{y:.1f}" for x, y in ptsr)
    route_paths += (f'<polyline points="{pstr}" fill="none" stroke="{colour[cls]}" '
                    f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')

# Faint wind-direction streaks across the map (blowing FROM WSW toward ENE).
def screen_vec(b):
    return math.sin(math.radians(b)), -math.cos(math.radians(b))
tox, toy = screen_vec(WIND_FROM_DEG + 180)   # unit vector the wind blows toward
streaks = ""
STREAK_LEN = 74
for k in range(3):
    # tails spread along the lower-left edge, heads point up-right
    sx = MBX + 40 + k * 96
    sy = MBY + MBH - 40 - k * 14
    ex = sx + tox * STREAK_LEN
    ey = sy + toy * STREAK_LEN
    # small arrow head
    perpx, perpy = -toy, tox
    h1x, h1y = ex - 9 * tox + 4 * perpx, ey - 9 * toy + 4 * perpy
    h2x, h2y = ex - 9 * tox - 4 * perpx, ey - 9 * toy - 4 * perpy
    streaks += (f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
                f'stroke="{STONE}" stroke-width="1.5" stroke-opacity="0.45"/>'
                f'<polyline points="{h1x:.1f},{h1y:.1f} {ex:.1f},{ey:.1f} {h2x:.1f},{h2y:.1f}" '
                f'fill="none" stroke="{STONE}" stroke-width="1.5" stroke-opacity="0.45"/>')

# Start / finish marker (Tenby — the route starts and finishes at the same point).
sfx, sfy = project(samples[0][1], samples[0][2])
start_marker = (f'<circle cx="{sfx:.1f}" cy="{sfy:.1f}" r="4.6" fill="{CREAM}" '
                f'stroke="{INK}" stroke-width="2"/>'
                f'<text x="{sfx + 9:.1f}" y="{sfy + 4:.1f}" font-family="Oswald,sans-serif" '
                f'font-size="12" font-weight="600" fill="{INK}">Start / finish</text>')

# ── Compass rose (right of the map): wind FROM the WSW, blowing toward ENE ─────
cx, cy, cr = 862, 486, 52
fx, fy = screen_vec(WIND_FROM_DEG)          # from-point on rim (WSW, lower-left)
ax_, ay_ = screen_vec(WIND_FROM_DEG + 180)  # arrow head on rim (ENE, upper-right)
# cardinal ticks
cardinals = ""
for lab, bdeg in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
    vx, vy = screen_vec(bdeg)
    cardinals += (f'<line x1="{vx*(cr-6):.1f}" y1="{vy*(cr-6):.1f}" '
                  f'x2="{vx*cr:.1f}" y2="{vy*cr:.1f}" stroke="{INK}" stroke-width="1"/>'
                  f'<text x="{vx*(cr+11):.1f}" y="{vy*(cr+11)+4:.1f}" text-anchor="middle" '
                  f'font-family="JetBrains Mono,monospace" font-size="10" fill="#6B6B6B">{lab}</text>')
# arrow head geometry (points to ENE rim)
perpx, perpy = -ay_, ax_
hx, hy = ax_ * cr, ay_ * cr
ha1x, ha1y = hx - 12 * ax_ + 6 * perpx, hy - 12 * ay_ + 6 * perpy
ha2x, ha2y = hx - 12 * ax_ - 6 * perpx, hy - 12 * ay_ - 6 * perpy

def stat(x, y, big, small, col):
    return (f'<text x="{x}" y="{y}" font-family="Oswald,sans-serif" font-size="26" '
            f'font-weight="700" fill="{col}">{big}</text>'
            f'<text x="{x}" y="{y + 17}" font-family="Source Sans 3,sans-serif" '
            f'font-size="12" fill="#3A3A3A">{small}</text>')

svg = f'''<svg class="raceplan-svg" viewBox="0 0 {W} {H}" role="img" width="100%"
  xmlns="http://www.w3.org/2000/svg"
  aria-label="Ironman Wales bike course race plan snapshot. An elevation profile of the {total_km:.0f} kilometre bike leg with {len(POWER_CLIMBS)} climbs shaded where power matters most, and a map of the real bike route drawn in its true geographic shape, each section coloured for a sample fresh {WIND_LABEL} wind to show the headwind, tailwind and crosswind portions of the course, with a compass showing the wind blowing from the {WIND_LABEL}.">
<title>Ironman Wales bike course: elevation and wind race-plan snapshot</title>
<rect x="0" y="0" width="{W}" height="{H}" fill="{CREAM}"/>
<rect x="0" y="0" width="{W}" height="6" fill="{TEAL}"/>

<text x="{PADL}" y="38" font-family="Oswald,sans-serif" font-size="22" font-weight="700"
  fill="{INK}">IRONMAN WALES &#183; THE BIKE COURSE</text>
<text x="{PADL}" y="58" font-family="Source Sans 3,sans-serif" font-size="13" fill="#3A3A3A">
  Real IMWA course data. {total_km:.0f} km, {bike.elevation_gain_m:,} m of climbing, {len(climbs)} climbs.</text>

{stat(W - 300, 34, f"{total_km:.0f} km", "Bike leg", INK)}
{stat(W - 190, 34, f"{bike.elevation_gain_m:,} m", "Total ascent", TEAL_DK)}
{stat(W - 78, 34, f"{steep['max_gradient_pct']:.0f}%", "Steepest", CORAL)}

<!-- Panel A: elevation -->
<text x="{PADL}" y="84" font-family="Oswald,sans-serif" font-size="13" font-weight="600"
  fill="{INK}" letter-spacing="0.5">ELEVATION &#183; SHADED WHERE POWER MATTERS MOST</text>
<line x1="{PADL}" y1="{AX_TOP_A + AX_H_A}" x2="{W - PADR}" y2="{AX_TOP_A + AX_H_A}" stroke="{INK}" stroke-width="1.2"/>
{''.join(climb_rects)}
<path d="{area}" fill="{INK}" fill-opacity="0.06"/>
<path d="{line}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-linejoin="round"/>
{xticks}{ylabs}{ann}
<text x="{PADL - 10}" y="{AX_TOP_A - 4}" text-anchor="end" font-family="Source Sans 3,sans-serif" font-size="10" fill="#6B6B6B">m</text>
<text x="{W/2:.0f}" y="{AX_TOP_A + AX_H_A + 40}" text-anchor="middle" font-family="Source Sans 3,sans-serif" font-size="12" fill="#3A3A3A">Distance along the bike course (km)</text>

<!-- Panel B: wind MAP -->
<text x="{PADL}" y="{MAP_TITLE_Y}" font-family="Oswald,sans-serif" font-size="13" font-weight="600"
  fill="{INK}" letter-spacing="0.5">WIND ON THE COURSE &#183; A SAMPLE FRESH {WIND_LABEL} DAY</text>
<rect x="{MBX}" y="{MBY}" width="{MBW}" height="{MBH}" fill="#FBFAF6" stroke="{GRID}" stroke-width="1"/>
{streaks}
{route_paths}
{start_marker}

<!-- Wind direction: compass rose -->
<g transform="translate({cx},{cy})">
<circle r="{cr}" fill="#FBFAF6" stroke="{INK}" stroke-width="1"/>
{cardinals}
<line x1="{fx*cr:.1f}" y1="{fy*cr:.1f}" x2="{ax_*cr:.1f}" y2="{ay_*cr:.1f}" stroke="{CORAL}" stroke-width="3"/>
<polygon points="{hx:.1f},{hy:.1f} {ha1x:.1f},{ha1y:.1f} {ha2x:.1f},{ha2y:.1f}" fill="{CORAL}"/>
<circle r="3" fill="{INK}"/>
</g>
<text x="{cx}" y="{cy + cr + 24}" text-anchor="middle" font-family="Oswald,sans-serif" font-size="14" font-weight="700" fill="{INK}">WIND FROM THE {WIND_LABEL}</text>
<text x="{cx}" y="{cy + cr + 42}" text-anchor="middle" font-family="Source Sans 3,sans-serif" font-size="12" fill="#3A3A3A">blowing toward the ENE</text>

<!-- Framing note (left of the compass, clear of it) -->
<g font-family="Source Sans 3,sans-serif" font-size="12.5" fill="#3A3A3A">
<text x="{MBX + MBW + 38}" y="{MBY + 20}">A sample fresh {WIND_LABEL} wind</text>
<text x="{MBX + MBW + 38}" y="{MBY + 38}">(from 247.5&#176;), typical of a</text>
<text x="{MBX + MBW + 38}" y="{MBY + 56}">Pembrokeshire race day.</text>
<text x="{MBX + MBW + 38}" y="{MBY + 74}">Every metre of the route is</text>
<text x="{MBX + MBW + 38}" y="{MBY + 92}">coloured by whether you</text>
<text x="{MBX + MBW + 38}" y="{MBY + 110}">push into it, ride with it,</text>
<text x="{MBX + MBW + 38}" y="{MBY + 128}">or handle it side-on.</text>
</g>

<!-- Wind legend -->
<g font-family="Source Sans 3,sans-serif" font-size="12" fill="{INK}">
<rect x="{PADL}" y="{H - 26}" width="13" height="13" fill="{CORAL}"/><text x="{PADL + 19}" y="{H - 15}">Headwind {share['head']}%</text>
<rect x="{PADL + 150}" y="{H - 26}" width="13" height="13" fill="{TEAL}"/><text x="{PADL + 169}" y="{H - 15}">Tailwind {share['tail']}%</text>
<rect x="{PADL + 300}" y="{H - 26}" width="13" height="13" fill="{STONE}"/><text x="{PADL + 319}" y="{H - 15}">Crosswind {share['cross']}%</text>
</g>
</svg>'''

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "imwales-raceplan.svg")
with open(out, "w") as f:
    f.write(svg)
print("wrote", out, len(svg), "bytes")
print("power climbs shaded:", len(POWER_CLIMBS))
print("wind shares:", share)
print("route runs (map polylines):", len(runs))
print("map box", (MBX, MBY, MBW, MBH), "scale px/deg", round(scale, 1))
print("steepest max grade:", steep["max_gradient_pct"], "at km", round(steep["start_dist_m"]/1000,1))
print("biggest net gain:", round(biggest["net_gain_m"]), "at km", round(biggest["start_dist_m"]/1000,1))
print("total_km", round(total_km,1), "gain", bike.elevation_gain_m)

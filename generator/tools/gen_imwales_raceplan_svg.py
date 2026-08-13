"""Generate ONE self-contained inline SVG for the Ironman Wales bike course.
Read-only against automated-horsepower course loader + wind model logic.

Panel A: elevation profile (real smoothed GPX), climbs shaded = where power matters.
Panel B: wind head/tail/cross along the route for a sample fresh WSW wind (from 247.5).

Wind model: headwind fraction = cos(travel_bearing - wind_from_bearing), the same
cos(course_bearing - wind_direction) component used in src/race_planner.py.
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

wind_seg = []  # (dist_m, headwind_fraction)
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
W, H = 1000, 560
PADL, PADR = 64, 26
AX_TOP_A, AX_H_A = 92, 210          # elevation panel
AX_TOP_B, AX_H_B = 386, 66          # wind strip panel
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

# Wind strip: bin the fine samples into ~1km bins (average fraction) so the
# inline SVG stays light, while the head/tail/cross shares above use fine data.
colour = {"head": CORAL, "tail": TEAL, "cross": STONE}
BIN_M = 1000.0
bins = []  # (start_m, end_m, avg_frac)
cur_start = 0.0
acc, cnt = 0.0, 0
for m, f in wind_seg:
    acc += f
    cnt += 1
    if m - cur_start >= BIN_M:
        bins.append((cur_start, m, acc / cnt))
        cur_start, acc, cnt = m, 0.0, 0
if cnt:
    bins.append((cur_start, total_m, acc / cnt))
wind_rects = ""
for (s, e, f) in bins:
    x0 = PADL + plot_w * (s / total_m)
    x1 = PADL + plot_w * (e / total_m)
    cls = wind_class(f)
    wind_rects += (f'<rect x="{x0:.2f}" y="{AX_TOP_B:.0f}" width="{x1 - x0 + 0.6:.2f}" '
                   f'height="{AX_H_B:.0f}" fill="{colour[cls]}"/>')

# x-axis for wind strip (same scale)
wxticks = ""
km = 0
while km <= total_km:
    xx = x_of(km * 1000.0)
    wxticks += (f'<line x1="{xx:.1f}" y1="{AX_TOP_B + AX_H_B:.1f}" x2="{xx:.1f}" '
                f'y2="{AX_TOP_B + AX_H_B + 5:.1f}" stroke="{GRID}" stroke-width="1"/>'
                f'<text x="{xx:.1f}" y="{AX_TOP_B + AX_H_B + 19:.1f}" text-anchor="middle" '
                f'font-family="JetBrains Mono,monospace" font-size="11" fill="#6B6B6B">{km}</text>')
    km += 20

# Compass rose showing the wind FROM direction
cx, cy, cr = W - 78, AX_TOP_B + AX_H_B / 2, 26
ang = math.radians(WIND_FROM_DEG - 90)  # 0deg=N at top; screen x=cos(a-90)
# arrow points in the direction the wind blows TO (from-dir + 180)
tox = math.cos(math.radians(WIND_FROM_DEG + 90))
toy = math.sin(math.radians(WIND_FROM_DEG + 90))
# convert compass bearing to screen vector: N=up. bearing b -> (sin b, -cos b)
def screen_vec(b):
    return math.sin(math.radians(b)), -math.cos(math.radians(b))
fx, fy = screen_vec(WIND_FROM_DEG)          # from-point on rim
ax_, ay_ = screen_vec(WIND_FROM_DEG + 180)  # arrow head (blows to)

def stat(x, y, big, small, col):
    return (f'<text x="{x}" y="{y}" font-family="Oswald,sans-serif" font-size="26" '
            f'font-weight="700" fill="{col}">{big}</text>'
            f'<text x="{x}" y="{y + 17}" font-family="Source Sans 3,sans-serif" '
            f'font-size="12" fill="#3A3A3A">{small}</text>')

svg = f'''<svg class="raceplan-svg" viewBox="0 0 {W} {H}" role="img" width="100%"
  xmlns="http://www.w3.org/2000/svg"
  aria-label="Ironman Wales bike course race plan snapshot. An elevation profile of the {total_km:.0f} kilometre bike leg with {len(POWER_CLIMBS)} climbs shaded where power matters most, and a wind analysis for a sample fresh {WIND_LABEL} wind showing headwind, tailwind and crosswind sections along the route.">
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

<!-- Panel B: wind -->
<text x="{PADL}" y="{AX_TOP_B - 12}" font-family="Oswald,sans-serif" font-size="13" font-weight="600"
  fill="{INK}" letter-spacing="0.5">WIND &#183; A SAMPLE FRESH {WIND_LABEL} DAY</text>
{wind_rects}
<rect x="{PADL}" y="{AX_TOP_B}" width="{plot_w:.1f}" height="{AX_H_B}" fill="none" stroke="{INK}" stroke-width="1"/>
{wxticks}
<text x="{W/2:.0f}" y="{AX_TOP_B + AX_H_B + 42}" text-anchor="middle" font-family="Source Sans 3,sans-serif" font-size="12" fill="#3A3A3A">Distance along the bike course (km)</text>

<!-- Wind legend -->
<g font-family="Source Sans 3,sans-serif" font-size="12" fill="{INK}">
<rect x="{PADL}" y="{H - 26}" width="13" height="13" fill="{CORAL}"/><text x="{PADL + 19}" y="{H - 15}">Headwind {share['head']}%</text>
<rect x="{PADL + 150}" y="{H - 26}" width="13" height="13" fill="{TEAL}"/><text x="{PADL + 169}" y="{H - 15}">Tailwind {share['tail']}%</text>
<rect x="{PADL + 300}" y="{H - 26}" width="13" height="13" fill="{STONE}"/><text x="{PADL + 319}" y="{H - 15}">Crosswind {share['cross']}%</text>
</g>

<!-- Compass -->
<g transform="translate({cx},{cy})">
<circle r="{cr}" fill="none" stroke="{INK}" stroke-width="1"/>
<text x="0" y="{-cr - 4}" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="9" fill="#6B6B6B">N</text>
<line x1="{fx*cr:.1f}" y1="{fy*cr:.1f}" x2="{ax_*cr:.1f}" y2="{ay_*cr:.1f}" stroke="{CORAL}" stroke-width="2.4"/>
<polygon points="{ax_*cr:.1f},{ay_*cr:.1f} {ax_*cr - 7*(ax_+0.5*fy):.1f},{ay_*cr - 7*(ay_-0.5*fx):.1f} {ax_*cr - 7*(ax_-0.5*fy):.1f},{ay_*cr - 7*(ay_+0.5*fx):.1f}" fill="{CORAL}"/>
<text x="0" y="{cr + 14}" text-anchor="middle" font-family="Oswald,sans-serif" font-size="11" font-weight="600" fill="{INK}">{WIND_LABEL} wind</text>
</g>
</svg>'''

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "imwales-raceplan.svg")
with open(out, "w") as f:
    f.write(svg)
print("wrote", out, len(svg), "bytes")
print("power climbs shaded:", len(POWER_CLIMBS))
print("wind shares:", share)
print("steepest max grade:", steep["max_gradient_pct"], "at km", round(steep["start_dist_m"]/1000,1))
print("biggest net gain:", round(biggest["net_gain_m"]), "at km", round(biggest["start_dist_m"]/1000,1))
print("total_km", round(total_km,1), "gain", bike.elevation_gain_m)

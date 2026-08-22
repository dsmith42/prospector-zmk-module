#!/usr/bin/env python3
"""Render the Dial layout as an SVG, from the widget's own constants.

Geometry and colours are parsed out of src/layouts/dial/ rather than duplicated
here, so the picture cannot drift from what the firmware draws. Rerun after
changing the widget:

    python3 docs/render_dial_mock.py --minutes 22 --mods GS

Font sizes are approximated by the bundled font names (the real faces are LVGL
binaries), so glyph metrics are indicative. Positions, colours, tick count,
dial geometry and the low-battery threshold are exact.
"""

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "boards/shields/prospector_adapter/src/layouts/dial"
PANEL_W, PANEL_H = 280, 240


def src(name):
    return (D / name).read_text()


def define(text, name, cast=int):
    m = re.search(rf"#define\s+{name}\s+\(?([^)\n]+)\)?", text)
    if not m:
        raise SystemExit(f"could not parse #define {name}")
    v = m.group(1).strip()
    if cast is int:
        return int(eval(v, {"DIAL_R": DIAL_R, "DIAL_TICK_IN": None})) if not v.isdigit() else int(v)
    return v


def colour(name):
    m = re.search(rf"#define\s+{name}\s+0x([0-9a-fA-F]+)", src("display_colors.h"))
    if not m:
        raise SystemExit(f"could not parse {name}")
    return "#" + m.group(1).zfill(6)


h = (D / "dial.h").read_text()
DIAL_R = int(re.search(r"#define DIAL_R (\d+)", h).group(1))
CX = int(re.search(r"#define DIAL_CX (\d+)", h).group(1))
CY = int(re.search(r"#define DIAL_CY (\d+)", h).group(1))
TICKS = int(re.search(r"#define DIAL_TICK_COUNT (\d+)", h).group(1))
FACE = int(re.search(r"#define DIAL_FACE_MINUTES (\d+)", h).group(1))
HUB_R = int(re.search(r"#define DIAL_HUB_R (\d+)", h).group(1))
TICK_IN = DIAL_R + int(re.search(r"#define DIAL_TICK_IN \(DIAL_R \+ (\d+)\)", h).group(1))
TICK_OUT = DIAL_R + int(re.search(r"#define DIAL_TICK_OUT \(DIAL_R \+ (\d+)\)", h).group(1))
LOW = int(re.search(r"#define BATTERY_LOW_PCT (\d+)", src("status_text.c")).group(1))

# Font sizes are inferred from the bundled font names used in status_text.c.
FONT_PX = {"FR_Medium_32": 32, "DINish_Medium_24": 24,
           "DINishCondensed_SemiBold_20": 20, "FG_Medium_20": 20}


def font_for(pattern):
    m = re.search(pattern, src("status_text.c"), re.S)
    return FONT_PX[m.group(1)]


def render(minutes_left, layer, batt, profile, mods):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    track = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    tick_col = colour("DISPLAY_COLOR_DIAL_TICK")
    hub_col = colour("DISPLAY_COLOR_DIAL_HUB")
    min_col = colour("DISPLAY_COLOR_DIAL_MINUTES")
    prof_col = colour("DISPLAY_COLOR_DIAL_PROFILE")
    batt_col = colour("DISPLAY_COLOR_BATTERY_FILL")
    low_col = colour("DISPLAY_COLOR_BATTERY_LOW_TEXT")
    mod_on = colour("DISPLAY_COLOR_MOD_ACTIVE")
    mod_off = colour("DISPLAY_COLOR_MOD_INACTIVE")

    frac = max(0.0, min(1.0, minutes_left / FACE))
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
         f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
         f'aria-label="Dial layout, {minutes_left} minutes remaining of a {FACE} minute face">',
         f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>']

    for i in range(TICKS):
        rad = math.radians(360 * i / TICKS - 90)
        mid = TICK_IN + (TICK_OUT - TICK_IN) / 2
        o.append(f'<circle cx="{CX + mid*math.cos(rad):.1f}" cy="{CY + mid*math.sin(rad):.1f}" '
                 f'r="1.5" fill="{tick_col}"/>')

    o.append(f'<circle cx="{CX}" cy="{CY}" r="{DIAL_R}" fill="{track}"/>')
    if frac >= 1:
        o.append(f'<circle cx="{CX}" cy="{CY}" r="{DIAL_R}" fill="{active}"/>')
    elif frac > 0:
        a = math.radians(-90 + 360 * frac)
        o.append(f'<path d="M {CX} {CY} L {CX} {CY-DIAL_R} A {DIAL_R} {DIAL_R} 0 '
                 f'{1 if frac > 0.5 else 0} 1 {CX + DIAL_R*math.cos(a):.1f} '
                 f'{CY + DIAL_R*math.sin(a):.1f} Z" fill="{active}"/>')

    a = math.radians(-90 + 360 * frac)
    o.append(f'<line x1="{CX}" y1="{CY}" x2="{CX + (DIAL_R+4)*math.cos(a):.1f}" '
             f'y2="{CY + (DIAL_R+4)*math.sin(a):.1f}" stroke="{active}" stroke-width="4" '
             f'stroke-linecap="round"/>')
    o.append(f'<circle cx="{CX}" cy="{CY}" r="{HUB_R}" fill="{hub_col}"/>')

    o.append(f'<text x="{PANEL_W-10}" y="{22+32}" text-anchor="end" font-family="{mono}" '
             f'font-size="32" fill="{min_col}">{minutes_left}</text>')
    o.append(f'<text x="{PANEL_W-10}" y="{154+20}" text-anchor="end" font-family="{mono}" '
             f'font-size="20" fill="{prof_col}">B{profile}</text>')
    for i, (dx, pct) in enumerate(zip((-46, -10), batt)):
        o.append(f'<text x="{PANEL_W+dx}" y="{184+24}" text-anchor="end" font-family="{mono}" '
                 f'font-size="24" fill="{low_col if pct < LOW else batt_col}">{pct}</text>')

    o.append(f'<text x="10" y="{PANEL_H-6}" font-family="{sans}" font-size="20" '
             f'fill="{mod_on}">{layer}</text>')
    for i, (flag, name) in enumerate((("G", "CMD"), ("A", "OPT"), ("C", "CTL"), ("S", "SFT"))):
        o.append(f'<text x="{PANEL_W-10-(3-i)*40}" y="{PANEL_H-6}" text-anchor="end" '
                 f'font-family="{sans}" font-size="20" font-weight="600" '
                 f'fill="{mod_on if flag in mods else mod_off}">{name}</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=22)
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--mods", default="")
    ap.add_argument("--out", default="docs/images/dial-layout.svg")
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.minutes, a.layer, a.battery, a.profile, a.mods))
    print(f"wrote {out.relative_to(ROOT)}")

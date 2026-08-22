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
RING_R = DIAL_R + int(re.search(r"#define DIAL_RING_R \(DIAL_R \+ (\d+)\)", h).group(1))
RING_W = int(re.search(r"#define DIAL_RING_W (\d+)", h).group(1))
LOW = int(re.search(r"#define BATTERY_LOW_PCT (\d+)", src("status_text.c")).group(1))

# Font sizes are inferred from the bundled font names used in status_text.c.
FONT_PX = {"FR_Medium_32": 32, "DINish_Medium_24": 24,
           "DINishCondensed_SemiBold_20": 20, "FG_Medium_20": 20}


def font_for(pattern):
    m = re.search(pattern, src("status_text.c"), re.S)
    return FONT_PX[m.group(1)]


def render(minutes_left, total, layer, batt, profile, mods, usb=False, armed=False):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    face_col = colour("DISPLAY_COLOR_DIAL_FACE")
    block_col = colour("DISPLAY_COLOR_DIAL_BLOCK")
    tick_col = colour("DISPLAY_COLOR_DIAL_TICK")
    hand_col = colour("DISPLAY_COLOR_DIAL_HAND")
    hub_col = colour("DISPLAY_COLOR_DIAL_HUB")
    min_col = colour("DISPLAY_COLOR_DIAL_MINUTES")
    prof_col = colour("DISPLAY_COLOR_DIAL_PROFILE")
    batt_col = colour("DISPLAY_COLOR_BATTERY_FILL")
    low_col = colour("DISPLAY_COLOR_BATTERY_LOW_TEXT")
    mod_on = colour("DISPLAY_COLOR_MOD_ACTIVE")
    mod_off = colour("DISPLAY_COLOR_MOD_INACTIVE")

    # Armed but not started: wedge, hand and numeral dim together, so the
    # selected length previews without reading as a running block.
    if armed:
        active = hand_col = min_col = colour("DISPLAY_COLOR_DIAL_ARMED")

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

    def pie(r, f, fill):
        if f <= 0:
            return ""
        if f >= 1:
            return f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="{fill}"/>'
        ang = math.radians(-90 + 360 * f)
        return (f'<path d="M {CX} {CY} L {CX} {CY-r} A {r} {r} 0 '
                f'{1 if f > 0.5 else 0} 1 {CX + r*math.cos(ang):.1f} '
                f'{CY + r*math.sin(ang):.1f} Z" fill="{fill}"/>')

    def ring(r, f, stroke, w):
        if f <= 0:
            return ""
        if f >= 1:
            return f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="{stroke}" stroke-width="{w}"/>'
        ang = math.radians(-90 + 360 * f)
        return (f'<path d="M {CX} {CY-r} A {r} {r} 0 {1 if f > 0.5 else 0} 1 '
                f'{CX + r*math.cos(ang):.1f} {CY + r*math.sin(ang):.1f}" fill="none" '
                f'stroke="{stroke}" stroke-width="{w}"/>')

    # Face (the whole hour) < block (the length chosen) < orange (what remains).
    disc_track = min(1.0, total / FACE)
    ring_track = max(0, total - FACE) / FACE
    ring_fill = max(0, minutes_left - FACE) / FACE

    o.append(f'<circle cx="{CX}" cy="{CY}" r="{DIAL_R}" fill="{face_col}"/>')
    if ring_track > 0:
        o.append(ring(RING_R, 1.0, face_col, RING_W))
        o.append(ring(RING_R, ring_track, block_col, RING_W))
    o.append(pie(DIAL_R, disc_track, block_col))
    o.append(pie(DIAL_R, frac, active))
    if ring_fill > 0:
        o.append(ring(RING_R, ring_fill, active, RING_W))

    a = math.radians(-90 + 360 * ((minutes_left % FACE) / FACE))
    o.append(f'<line x1="{CX}" y1="{CY}" x2="{CX + (DIAL_R+4)*math.cos(a):.1f}" '
             f'y2="{CY + (DIAL_R+4)*math.sin(a):.1f}" stroke="{hand_col}" stroke-width="4" '
             f'stroke-linecap="round"/>')
    o.append(f'<circle cx="{CX}" cy="{CY}" r="{HUB_R}" fill="{hub_col}"/>')

    o.append(f'<text x="{PANEL_W-10}" y="{22+32}" text-anchor="end" font-family="{mono}" '
             f'font-size="32" fill="{min_col}">{minutes_left}</text>')
    o.append(f'<text x="{PANEL_W-10}" y="{154+20}" text-anchor="end" font-family="{mono}" '
             f'font-size="20" fill="{prof_col}">{"USB" if usb else f"B {profile}"}</text>')
    for i, (dx, pct) in enumerate(zip((-46, -10), batt)):
        o.append(f'<text x="{PANEL_W+dx}" y="{184+24}" text-anchor="end" font-family="{mono}" '
                 f'font-size="24" fill="{low_col if pct < LOW else batt_col}">{pct}</text>')

    o.append(f'<text x="10" y="{PANEL_H-6}" font-family="{sans}" font-size="20" '
             f'fill="{mod_on}">{layer}</text>')
    # The firmware draws private-use glyphs from the bundled Symbols font, which
    # cannot be reproduced here — these Unicode equivalents are indicative of
    # position and state, not of the exact shapes on the panel.
    for i, (flag, glyph) in enumerate((("G", "\u2318"), ("A", "\u2325"),
                                       ("C", "\u2303"), ("S", "\u21e7"))):
        o.append(f'<text x="{PANEL_W-10-(3-i)*32}" y="{PANEL_H-4}" text-anchor="end" '
                 f'font-family="{sans}" font-size="24" '
                 f'fill="{mod_on if flag in mods else mod_off}">{glyph}</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=22)
    ap.add_argument("--total", type=int, default=0, help="block length; defaults to --minutes")
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--mods", default="")
    ap.add_argument("--usb", action="store_true", help="show USB instead of a BLE profile")
    ap.add_argument("--armed", action="store_true",
                    help="armed but not started: dimmed preview of the selected length")
    ap.add_argument("--out", default="docs/images/dial-layout.svg")
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.minutes, a.total or a.minutes, a.layer, a.battery, a.profile, a.mods, a.usb, a.armed))
    print(f"wrote {out.relative_to(ROOT)}")

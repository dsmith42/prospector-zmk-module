#!/usr/bin/env python3
"""Settled v2 concept: 60-minute absolute dial. NOT IMPLEMENTED YET.

Blocks are capped at 60 minutes, so the dial never wraps — which is what
retires the banked-track / spiral / outer-ring experiments in
render_wedge_concept.py. Those are kept only as a record of the options
considered.

Design, per vault/tech/zmk/zmk-dongle-build.md:
  - absolute 60-minute face, so a 30 fills half and you can see which block
    you are in, unlike the proportional v1 bar
  - tick ring for granularity without motion; a hand crossing one tick a
    minute is legible where a smooth sweep is an attention magnet
  - minutes-only numeral, muted, below the dial — a check, not the display
  - layer and profile top-right; battery bottom-right corner
  - one colour throughout, no depletion transition; zero is a non-event

    python3 docs/render_dial_concept.py --minutes 22 --total 30
"""

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OP = ROOT / "boards/shields/prospector_adapter/src/layouts/operator"
PANEL_W, PANEL_H = 280, 240
FACE = 60                      # minutes; blocks are capped at this
BATT_YELLOW, BATT_RED = 25, 10
WARN_YELLOW, WARN_RED = "#e8d21e", "#d63a2f"


def colour(name):
    text = (OP / "display_colors.h").read_text()
    m = re.search(rf"#define\s+{name}\s+0x([0-9a-fA-F]+)", text)
    if not m:
        raise SystemExit(f"could not parse {name}")
    return "#" + m.group(1).zfill(6)


def render(minutes_left, total, layer, batt_l, batt_r, profile, show_digits):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    track = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    # Layer takes Operator's modifier blue and battery takes its battery green,
    # so the diagnostics read as the same family as the stock screen rather than
    # as new vocabulary. Orange stays reserved for the timer.
    layer_col = colour("DISPLAY_COLOR_MOD_ACTIVE")
    batt_label = colour("DISPLAY_COLOR_BATTERY_FILL")
    dim = colour("DISPLAY_COLOR_OUTPUT_INACTIVE_TEXT")

    if total > FACE:
        raise SystemExit(f"blocks are capped at {FACE} minutes; got {total}")
    frac = max(0.0, min(1.0, minutes_left / FACE))

    # With the diagnostics pushed to a single bottom row and a short profile
    # marker top-right, the dial is now limited by the bottom row rather than by
    # a side column — so it grows into the width it just freed.
    cx, cy, r = 107, 106, 84
    tick_in, tick_out = r + 8, r + 16
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"
    right = PANEL_W - 10

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
        f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
        f'aria-label="60 minute dial, {minutes_left} minutes remaining">',
        f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>',
    ]

    for i in range(FACE):
        ang = math.radians(-90 + 360 * i / FACE)
        major = (i % 5 == 0)
        inner = tick_in if major else tick_in + 4
        o.append(f'<line x1="{cx + inner*math.cos(ang):.1f}" y1="{cy + inner*math.sin(ang):.1f}" '
                 f'x2="{cx + tick_out*math.cos(ang):.1f}" y2="{cy + tick_out*math.sin(ang):.1f}" '
                 f'stroke="{"#9a9a9a" if major else "#4a4a4a"}" '
                 f'stroke-width="{2 if major else 1.4}" stroke-linecap="round"/>')

    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{track}"/>')
    if frac >= 1:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{active}"/>')
    elif frac > 0:
        a = math.radians(-90 + 360 * frac)
        o.append(f'<path d="M {cx} {cy} L {cx} {cy-r} A {r} {r} 0 {1 if frac > 0.5 else 0} 1 '
                 f'{cx + r*math.cos(a):.1f} {cy + r*math.sin(a):.1f} Z" fill="{active}"/>')

    ang = math.radians(-90 + 360 * frac)
    o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + (r+4)*math.cos(ang):.1f}" '
             f'y2="{cy + (r+4)*math.sin(ang):.1f}" stroke="{active}" stroke-width="3.5" '
             f'stroke-linecap="round"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="#d8d4cc"/>')

    # Minutes top-right, alone in its corner. Muted and small: it is a check on
    # the dial, not the display.
    if show_digits:
        o.append(f'<text x="{right}" y="46" text-anchor="end" font-family="{mono}" '
                 f'font-size="30" fill="#8a8a8a">{minutes_left}</text>')

    # Bottom row: layer far left, both batteries far right, one baseline.
    base_y = PANEL_H - 12
    o.append(f'<text x="10" y="{base_y}" font-family="{sans}" font-size="18" '
             f'font-weight="400" letter-spacing="1.0" fill="{layer_col}">{layer}</text>')

    # Profile marker sits directly above the batteries — everything checked when
    # something is wrong ends up in one corner. "BLE" dropped; B and a digit do.
    o.append(f'<text x="{right}" y="{base_y - 26}" text-anchor="end" font-family="{mono}" '
             f'font-size="16" fill="{dim}">B{profile}</text>')

    # No L/R prefixes: the numbers are already left and right.
    cell = 46
    for i, pct in enumerate((batt_l, batt_r)):
        x = right - cell * (1 - i)
        if pct <= BATT_RED:
            bg, fg = WARN_RED, "#000000"
        elif pct <= BATT_YELLOW:
            bg, fg = WARN_YELLOW, "#000000"
        else:
            bg, fg = None, batt_label
        if bg:
            # Inverted badge, static. Fixed cells so the row cannot reflow at
            # exactly the moment a warning appears.
            o.append(f'<rect x="{x-38}" y="{base_y-16}" width="40" height="23" rx="5" fill="{bg}"/>')
        o.append(f'<text x="{x}" y="{base_y}" text-anchor="end" font-family="{mono}" '
                 f'font-size="17" fill="{fg}">{pct}</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=22)
    ap.add_argument("--total", type=int, default=30)
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--no-digits", action="store_true")
    ap.add_argument("--out", default="docs/images/dial60-concept.svg")
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.minutes, a.total, a.layer, a.battery[0], a.battery[1],
                          a.profile, not a.no_digits))
    print(f"wrote {out.relative_to(ROOT)}")

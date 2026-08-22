#!/usr/bin/env python3
"""Concept mock for the v2 'wedge' Operator layout — NOT IMPLEMENTED.

Unlike render_timer_mock.py, this cannot be derived from the widget source
because the layout doesn't exist yet. Colours are parsed from
display_colors.h so the palette is real; the geometry is the proposal from
vault/tech/zmk/zmk-dongle-build.md ("v2 layout candidate"):

  - disc budgeted at ~190px, not full height, so the side column stays legible
  - layer / profile / battery demoted to plain text in that column, because the
    timer is the only ambient element and the rest are diagnostic
  - battery warning as an inverted badge: yellow <=25%, red <=10%, black text

    python3 docs/render_wedge_concept.py --minutes 21 --total 30
    python3 docs/render_wedge_concept.py --minutes 3 --total 30 --battery 22 8 \
        --out docs/images/operator-wedge-concept-warning.svg
"""

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OP = ROOT / "boards/shields/prospector_adapter/src/layouts/operator"
PANEL_W, PANEL_H = 280, 240

# Warning thresholds from the design note. Yellow deliberately distinct from
# the orange timer, so a warning never reads as work-in-progress.
BATT_YELLOW, BATT_RED = 25, 10
SPIRAL_DARK = "#3d3128"   # dark orange-grey the spiral runs out of
WARN_YELLOW, WARN_RED = "#e8d21e", "#d63a2f"


def colour(name):
    text = (OP / "display_colors.h").read_text()
    m = re.search(rf"#define\s+{name}\s+0x([0-9a-fA-F]+)", text)
    if not m:
        raise SystemExit(f"could not parse {name}")
    return "#" + m.group(1).zfill(6)


def wedge_path(cx, cy, r, fraction):
    """Pie wedge from 12 o'clock, clockwise, covering `fraction` of the dial."""
    if fraction <= 0:
        return ""
    if fraction >= 1:
        return (f"M {cx} {cy-r} A {r} {r} 0 1 1 {cx-0.01:.2f} {cy-r} Z")
    end = math.radians(-90 + 360 * fraction)
    ex, ey = cx + r * math.cos(end), cy + r * math.sin(end)
    large = 1 if fraction > 0.5 else 0
    return f"M {cx} {cy} L {cx} {cy-r} A {r} {r} 0 {large} 1 {ex:.1f} {ey:.1f} Z"


def render(minutes_left, total, layer, batt_l, batt_r, profile, show_digits):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    spent = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    text_col = colour("DISPLAY_COLOR_TIMER_TEXT")
    layer_col = colour("DISPLAY_COLOR_LAYER_TEXT")
    batt_label = colour("DISPLAY_COLOR_BATTERY_LABEL")
    dim = colour("DISPLAY_COLOR_OUTPUT_INACTIVE_TEXT")

    frac = 0 if total <= 0 else max(0.0, min(1.0, minutes_left / total))

    # Disc left, diagnostic column right. r=88 leaves an 80px column.
    cx, cy, r = 96, 120, 88
    col_x = 196
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
        f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
        f'aria-label="Concept wedge layout, {minutes_left} of {total} minutes remaining">',
        f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{spent}"/>',
    ]

    path = wedge_path(cx, cy, r, frac)
    if path:
        # Single colour throughout — no depletion transition. Zero is a non-event.
        o.append(f'<path d="{path}" fill="{active}"/>')

    if show_digits:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="#000000"/>')
        o.append(f'<text x="{cx}" y="{cy+13}" text-anchor="middle" font-family="{mono}" '
                 f'font-size="38" font-weight="500" fill="{text_col}">{minutes_left}</text>')

    # Diagnostic column: three short strings, plain, no graphics.
    o.append(f'<text x="{col_x}" y="48" font-family="{sans}" font-size="26" font-weight="300" '
             f'letter-spacing="1.2" fill="{layer_col}">{layer}</text>')
    o.append(f'<text x="{col_x}" y="88" font-family="{mono}" font-size="17" fill="{dim}">'
             f'BLE {profile}</text>')

    for i, (side, pct) in enumerate((("L", batt_l), ("R", batt_r))):
        y = 138 + i * 32
        if pct <= BATT_RED:
            bg, fg = WARN_RED, "#000000"
        elif pct <= BATT_YELLOW:
            bg, fg = WARN_YELLOW, "#000000"
        else:
            bg, fg = None, batt_label
        if bg:
            # Inverted badge, static: visible in peripheral vision, never animated.
            o.append(f'<rect x="{col_x-5}" y="{y-17}" width="66" height="24" rx="5" fill="{bg}"/>')
        o.append(f'<text x="{col_x}" y="{y}" font-family="{mono}" font-size="18" '
                 f'fill="{fg}">{side} {pct}</text>')

    o.append("</svg>")
    return "\n".join(o)




def _mix(c1, c2, t):
    a = [int(c1[i:i+2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(a[i] + (b[i]-a[i])*t):02x}" for i in range(3))


def _conic_segments(cx, cy, r, start_frac, end_frac, c_from, c_to, steps=72):
    """Approximate a conic gradient with wedge segments.

    Neither SVG nor LVGL has a native conic gradient, so this is the same
    technique the widget would have to use: interpolate colour per segment and
    draw each as a small pie slice. Segments overlap by a hair to avoid seams.
    """
    out = []
    span = end_frac - start_frac
    if span <= 0:
        return out
    for i in range(steps):
        f0 = start_frac + span * i / steps
        f1 = start_frac + span * (i + 1) / steps
        a0 = math.radians(-90 + 360 * f0)
        a1 = math.radians(-90 + 360 * (f1 + 0.0015))
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        col = _mix(c_from, c_to, i / max(1, steps - 1))
        out.append(f'<path d="M {cx} {cy} L {x0:.2f} {y0:.2f} A {r} {r} 0 0 1 '
                   f'{x1:.2f} {y1:.2f} Z" fill="{col}"/>')
    return out


def render_session(minutes_left, total, layer, batt_l, batt_r, profile, show_digits, dial,
                   overflow="none", ring_width=4, banked=None):
    """Session-app inspired: tick ring, boundary hand, subordinate numeral.

    `dial` selects the model. 0 keeps proportional behaviour (the face always
    starts full). A non-zero value makes it an absolute dial of that many
    minutes, like Session's 60 — which tells you which block you are in, but
    wraps for anything longer than the face.

    `overflow` handles that wrap:
      shade  the disc's TRACK goes dark orange while a whole lap is banked
             underneath. The remaining wedge keeps its single colour.
      ring   a thin outer ring shows the whole block proportionally while the
             disc stays minute-precise. Ticks sit outside it.
      both   combine.
    """
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    spent = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    layer_col = colour("DISPLAY_COLOR_LAYER_TEXT")
    batt_label = colour("DISPLAY_COLOR_BATTERY_LABEL")
    dim = colour("DISPLAY_COLOR_OUTPUT_INACTIVE_TEXT")
    banked_track = banked or "#8a4a0c"   # dark orange: a whole lap still underneath

    face = dial if dial > 0 else total
    laps_left, shown = 0, minutes_left
    if dial > 0 and minutes_left > dial:
        laps_left = minutes_left // dial
        shown = minutes_left - laps_left * dial
        if shown == 0:
            laps_left -= 1
            shown = dial
    frac = 0.0 if face <= 0 else max(0.0, min(1.0, shown / face))
    overall = 0.0 if total <= 0 else max(0.0, min(1.0, minutes_left / total))

    want_ring = overflow in ("ring", "both")
    want_shade = overflow in ("shade", "both")
    want_spiral = overflow == "spiral"
    track = banked_track if (want_shade and laps_left > 0) else spent

    # Disc, then a thin ring just outside it, then the ticks further out again —
    # so the ring costs no disc radius and does not evict the tick marks.
    cx, cy, r = 104, 104, 74
    ring_r = r + 6
    tick_in, tick_out = (ring_r + 6), (ring_r + 16)
    col_x = 214
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
        f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
        f'aria-label="Concept, {minutes_left} minutes remaining">',
        f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>',
    ]

    ticks = face if face <= 60 else 60
    for i in range(ticks):
        ang = math.radians(-90 + 360 * i / ticks)
        major = (i % 5 == 0)
        inner = tick_in if major else tick_in + 4
        o.append(f'<line x1="{cx + inner*math.cos(ang):.1f}" y1="{cy + inner*math.sin(ang):.1f}" '
                 f'x2="{cx + tick_out*math.cos(ang):.1f}" y2="{cy + tick_out*math.sin(ang):.1f}" '
                 f'stroke="{"#9a9a9a" if major else "#4a4a4a"}" '
                 f'stroke-width="{2 if major else 1.4}" stroke-linecap="round"/>')

    if want_ring:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="{spent}" '
                 f'stroke-width="{ring_width}"/>')
        if overall >= 1:
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="{active}" '
                     f'stroke-width="{ring_width}"/>')
        elif overall > 0:
            a2 = math.radians(-90 + 360 * overall)
            o.append(f'<path d="M {cx} {cy-ring_r} A {ring_r} {ring_r} 0 '
                     f'{1 if overall > 0.5 else 0} 1 {cx + ring_r*math.cos(a2):.1f} '
                     f'{cy + ring_r*math.sin(a2):.1f}" fill="none" stroke="{active}" '
                     f'stroke-width="{ring_width}"/>')

    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{track}"/>')

    # Spiral: while a whole lap is still banked, the part of the dial the timer
    # has yet to come back around to is drawn as a gradient running from dark
    # into the main orange, so it reads as "this returns" rather than "this is
    # spent". Inside the final lap there is nothing banked, so the gradient is
    # gone and only the plain remaining wedge is shown.
    if want_spiral and laps_left > 0:
        for seg in _conic_segments(cx, cy, r, frac, 1.0, SPIRAL_DARK, active):
            o.append(seg)

    path = wedge_path(cx, cy, r, frac)
    if path:
        o.append(f'<path d="{path}" fill="{active}"/>')

    ang = math.radians(-90 + 360 * frac)
    o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + (r+4)*math.cos(ang):.1f}" '
             f'y2="{cy + (r+4)*math.sin(ang):.1f}" stroke="{active}" stroke-width="3.5" '
             f'stroke-linecap="round"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="#d8d4cc"/>')

    # Minutes only — no seconds. Subordinate: muted, below the dial, secondary
    # to the shape. The shape is the display; the number is a check.
    if show_digits:
        o.append(f'<text x="{cx}" y="{cy + 118}" text-anchor="middle" font-family="{mono}" '
                 f'font-size="24" fill="#8a8a8a">{minutes_left}</text>')

    o.append(f'<text x="{col_x}" y="52" font-family="{sans}" font-size="22" font-weight="300" '
             f'letter-spacing="1.2" fill="{layer_col}">{layer}</text>')
    o.append(f'<text x="{col_x}" y="86" font-family="{mono}" font-size="15" fill="{dim}">BLE {profile}</text>')
    for i, (side, pct) in enumerate((("L", batt_l), ("R", batt_r))):
        y = 130 + i * 28
        if pct <= BATT_RED:
            bg, fg = WARN_RED, "#000000"
        elif pct <= BATT_YELLOW:
            bg, fg = WARN_YELLOW, "#000000"
        else:
            bg, fg = None, batt_label
        if bg:
            o.append(f'<rect x="{col_x-5}" y="{y-15}" width="60" height="22" rx="5" fill="{bg}"/>')
        o.append(f'<text x="{col_x}" y="{y}" font-family="{mono}" font-size="16" fill="{fg}">{side} {pct}</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=21)
    ap.add_argument("--total", type=int, default=30)
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--no-digits", action="store_true", help="wedge only, no numeral")
    ap.add_argument("--style", choices=("plain", "session"), default="plain",
                    help="plain = flat wedge; session = tick ring, hand, subordinate numeral")
    ap.add_argument("--dial", type=int, default=0,
                    help="absolute dial size in minutes (e.g. 60). 0 = proportional to the block")
    ap.add_argument("--ring-width", type=int, default=4, help="outer ring stroke width")
    ap.add_argument("--banked", default=None,
                    help="track colour while a whole lap is banked, e.g. #8a4a0c")
    ap.add_argument("--overflow", choices=("none", "shade", "ring", "both", "spiral"), default="none",
                    help="how to show a block longer than the dial face: shade the disc, "
                         "or add an outer progress ring in the tick band")
    ap.add_argument("--out", default="docs/images/operator-wedge-concept.svg")
    a = ap.parse_args()

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    fn = render_session if a.style == "session" else render
    if a.style == "session":
        out.write_text(fn(a.minutes, a.total, a.layer, a.battery[0], a.battery[1],
                          a.profile, not a.no_digits, a.dial, a.overflow, a.ring_width, a.banked))
    else:
        out.write_text(fn(a.minutes, a.total, a.layer, a.battery[0], a.battery[1],
                          a.profile, not a.no_digits))
    print(f"wrote {out.relative_to(ROOT)}")

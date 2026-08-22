#!/usr/bin/env python3
"""Concepts for blocks longer than the 60 minute dial face. NOT IMPLEMENTED.

Colours are parsed from the dial layout so the palette is real; geometry is
proposed. Two schemes:

  ring    Disc stays FULL while an outer ring drains the overflow hour. Ring is
          the high digit, disc the low digit, like an odometer. The hand rides
          the ring above 60 and the disc below it, handing off at the hour.
          Nothing jumps at the boundary — which is what killed the earlier
          "disc shows remaining mod 60" version.

  spiral  One continuous track that winds inward, a turn per hour, like a
          spiral clock. Reads as "how much thread is left" rather than as a
          number of laps.

    python3 docs/render_overtime_concept.py --style ring --minutes 75
"""

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "boards/shields/prospector_adapter/src/layouts/dial"
PANEL_W, PANEL_H = 280, 240
FACE = 60


def colour(name):
    m = re.search(rf"#define\s+{name}\s+0x([0-9a-fA-F]+)", (D / "display_colors.h").read_text())
    if not m:
        raise SystemExit(f"could not parse {name}")
    return "#" + m.group(1).zfill(6)


def wedge(cx, cy, r, frac, fill):
    if frac <= 0:
        return ""
    if frac >= 1:
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'
    a = math.radians(-90 + 360 * frac)
    return (f'<path d="M {cx} {cy} L {cx} {cy-r} A {r} {r} 0 {1 if frac > 0.5 else 0} 1 '
            f'{cx + r*math.cos(a):.1f} {cy + r*math.sin(a):.1f} Z" fill="{fill}"/>')


def arc(cx, cy, r, frac, stroke, width):
    if frac <= 0:
        return ""
    if frac >= 1:
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{stroke}" stroke-width="{width}"/>'
    a = math.radians(-90 + 360 * frac)
    return (f'<path d="M {cx} {cy-r} A {r} {r} 0 {1 if frac > 0.5 else 0} 1 '
            f'{cx + r*math.cos(a):.1f} {cy + r*math.sin(a):.1f}" fill="none" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="butt"/>')


def chrome(o, minutes, layer, batt, profile, mods, mono, sans, cols):
    right = PANEL_W - 10
    o.append(f'<text x="{right}" y="46" text-anchor="end" font-family="{mono}" '
             f'font-size="32" fill="{cols["min"]}">{minutes}</text>')
    o.append(f'<text x="{right}" y="174" text-anchor="end" font-family="{mono}" '
             f'font-size="20" fill="{cols["prof"]}">B {profile}</text>')
    for dx, pct in zip((-46, -10), batt):
        o.append(f'<text x="{PANEL_W+dx}" y="208" text-anchor="end" font-family="{mono}" '
                 f'font-size="24" fill="{cols["batt"]}">{pct}</text>')
    o.append(f'<text x="10" y="{PANEL_H-6}" font-family="{sans}" font-size="20" '
             f'fill="{cols["layer"]}">{layer}</text>')
    for i, (flag, name) in enumerate((("G", "CMD"), ("A", "OPT"), ("C", "CTL"), ("S", "SFT"))):
        o.append(f'<text x="{PANEL_W-10-(3-i)*40}" y="{PANEL_H-6}" text-anchor="end" '
                 f'font-family="{sans}" font-size="20" font-weight="600" '
                 f'fill="{cols["mod_on"] if flag in mods else cols["mod_off"]}">{name}</text>')


def render(style, minutes_left, layer, batt, profile, mods, ticks='between', ring_width=5):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    track = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    hand_col = colour("DISPLAY_COLOR_DIAL_HAND")
    hub_col = colour("DISPLAY_COLOR_DIAL_HUB")
    cols = {"min": colour("DISPLAY_COLOR_DIAL_MINUTES"),
            "prof": colour("DISPLAY_COLOR_DIAL_PROFILE"),
            "batt": colour("DISPLAY_COLOR_BATTERY_FILL"),
            "layer": colour("DISPLAY_COLOR_MOD_ACTIVE"),
            "mod_on": colour("DISPLAY_COLOR_MOD_ACTIVE"),
            "mod_off": colour("DISPLAY_COLOR_MOD_INACTIVE")}
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"

    cx, cy = 107, 106
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
         f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
         f'aria-label="{style} concept, {minutes_left} minutes remaining">',
         f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>']

    if style == "ring":
        # Ring is deliberately thin: a secondary indicator that only appears for
        # the top slice of the longest block, not a peer of the disc.
        r_disc = 74
        r_ring = 92 if ticks == "between" else 86
        tick_mid = 83 if ticks == "between" else r_ring
        overflow = max(0, minutes_left - FACE)
        disc_frac = 1.0 if minutes_left > FACE else minutes_left / FACE
        ring_frac = overflow / FACE

        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r_ring}" fill="none" stroke="{track}" '
                 f'stroke-width="{ring_width}"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r_disc}" fill="{track}"/>')
        o.append(wedge(cx, cy, r_disc, disc_frac, active))
        o.append(arc(cx, cy, r_ring, ring_frac, active, ring_width))

        # Five minute markers. Either in the gap between disc and ring, or laid
        # over the ring's own track.
        for i in range(12):
            ang = math.radians(-90 + 360 * i / 12)
            o.append(f'<circle cx="{cx + tick_mid*math.cos(ang):.1f}" '
                     f'cy="{cy + tick_mid*math.sin(ang):.1f}" r="1.6" '
                     f'fill="{colour("DISPLAY_COLOR_DIAL_TICK")}"/>')

        # Hand rides whichever track is currently draining.
        on_ring = overflow > 0
        frac = ring_frac if on_ring else disc_frac
        tip = (r_ring + 6) if on_ring else (r_disc + 4)
        a = math.radians(-90 + 360 * frac)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + tip*math.cos(a):.1f}" '
                 f'y2="{cy + tip*math.sin(a):.1f}" stroke="{hand_col}" stroke-width="4" '
                 f'stroke-linecap="round"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{hub_col}"/>')

    else:  # spiral — one track winding inward, a turn per hour
        turns = 2.0
        r_out, r_in = 90, 26
        total = FACE * turns
        frac = min(1.0, minutes_left / total)
        steps = 260
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            spent = 1.0 - frac
            colr = active if t0 >= spent else track
            a0 = math.radians(-90 + 360 * turns * t0)
            a1 = math.radians(-90 + 360 * turns * t1)
            rr0 = r_out - (r_out - r_in) * t0
            rr1 = r_out - (r_out - r_in) * t1
            o.append(f'<line x1="{cx + rr0*math.cos(a0):.2f}" y1="{cy + rr0*math.sin(a0):.2f}" '
                     f'x2="{cx + rr1*math.cos(a1):.2f}" y2="{cy + rr1*math.sin(a1):.2f}" '
                     f'stroke="{colr}" stroke-width="9" stroke-linecap="round"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{hub_col}"/>')

    chrome(o, minutes_left, layer, batt, profile, mods, mono, sans, cols)
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=("ring", "spiral"), default="ring")
    ap.add_argument("--minutes", type=int, default=75)
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--mods", default="")
    ap.add_argument("--ticks", choices=("between", "on-track"), default="between")
    ap.add_argument("--ring-width", type=int, default=5)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.style, a.minutes, a.layer, a.battery, a.profile, a.mods, a.ticks, a.ring_width))
    print(f"wrote {out.relative_to(ROOT)}")

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

_H = (D / "dial.h").read_text()


def _def(name):
    return int(re.search(rf"#define {name} (\d+)", _H).group(1))


SHIPPED_R = _def("DIAL_R")
SHIPPED_CX = _def("DIAL_CX")
SHIPPED_CY = _def("DIAL_CY")
SHIPPED_TICKS = _def("DIAL_TICK_COUNT")
SHIPPED_TICK_IN = SHIPPED_R + int(re.search(r"#define DIAL_TICK_IN \(DIAL_R \+ (\d+)\)", _H).group(1))
SHIPPED_TICK_OUT = SHIPPED_R + int(re.search(r"#define DIAL_TICK_OUT \(DIAL_R \+ (\d+)\)", _H).group(1))


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


def render(style, minutes_left, total, layer, batt, profile, mods, ticks='between', ring_width=5, marker_len=1.0, marker_opacity=1.0, armed=False):
    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    track = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    hand_col = colour("DISPLAY_COLOR_DIAL_HAND")
    hub_col = colour("DISPLAY_COLOR_DIAL_HUB")
    # Armed but not started: the whole timer dims, ring included.
    if armed:
        active = hand_col = colour("DISPLAY_COLOR_DIAL_ARMED")
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

    if style == "shipped":
        # The shipped dial, untouched, with the overtime ring dropped into the
        # empty band between the disc edge and the existing tick dots.
        cx, cy = SHIPPED_CX, SHIPPED_CY
        r_disc = SHIPPED_R
        r_ring = (SHIPPED_R + SHIPPED_TICK_IN) / 2
        # Grey is the BLOCK, not the face: a 45 greys three quarters of the disc
        # and leaves the rest black, so the chosen length stays visible even at
        # zero. Orange is what remains of it.
        disc_track = min(1.0, total / FACE)
        ring_track = max(0, total - FACE) / FACE
        disc_frac = min(1.0, minutes_left / FACE)
        ring_frac = max(0, minutes_left - FACE) / FACE
        overflow = max(0, minutes_left - FACE)
        tick_col = colour("DISPLAY_COLOR_DIAL_TICK")
        tick_mid = (SHIPPED_TICK_IN + SHIPPED_TICK_OUT) / 2

        for i in range(SHIPPED_TICKS):
            ang = math.radians(-90 + 360 * i / SHIPPED_TICKS)
            o.append(f'<circle cx="{cx + tick_mid*math.cos(ang):.1f}" '
                     f'cy="{cy + tick_mid*math.sin(ang):.1f}" r="1.5" fill="{tick_col}"/>')

        # Ring only exists for blocks over an hour, so a 45 looks like today's
        # screen with a black notch where the unused quarter is.
        o.append(arc(cx, cy, r_ring, ring_track, track, ring_width))
        o.append(wedge(cx, cy, r_disc, disc_track, track))
        o.append(wedge(cx, cy, r_disc, disc_frac, active))
        o.append(arc(cx, cy, r_ring, ring_frac, active, ring_width))

        # One hand, one length, one formula. The ring fraction above the hour
        # and the disc fraction below it are both (remaining mod 60) / 60, so
        # the hand tracks whichever track is draining without a branch — and it
        # sweeps continuously past twelve at the hour instead of jumping.
        hand_frac = (minutes_left % FACE) / FACE
        tip = r_disc + 4
        a = math.radians(-90 + 360 * hand_frac)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + tip*math.cos(a):.1f}" '
                 f'y2="{cy + tip*math.sin(a):.1f}" stroke="{hand_col}" stroke-width="4" '
                 f'stroke-linecap="round"/>')
        o.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{hub_col}"/>')

    elif style == "ring":
        # Ring is deliberately thin: a secondary indicator that only appears for
        # the top slice of the longest block, not a peer of the disc.
        r_disc = 70
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

        # Five minute markers. In the gap they are radial ticks spanning it, so
        # they read as a scale belonging to the disc. Over the ring track there
        # is no room for length, so they stay as dots.
        tick_col = colour("DISPLAY_COLOR_DIAL_TICK")
        for i in range(12):
            ang = math.radians(-90 + 360 * i / 12)
            if ticks == "between":
                gap_in, gap_out = r_disc + 3, r_ring - ring_width / 2 - 3
                span = (gap_out - gap_in) * marker_len
                mid = (gap_in + gap_out) / 2
                t_in, t_out = mid - span / 2, mid + span / 2
                o.append(f'<line x1="{cx + t_in*math.cos(ang):.1f}" '
                         f'y1="{cy + t_in*math.sin(ang):.1f}" '
                         f'x2="{cx + t_out*math.cos(ang):.1f}" '
                         f'y2="{cy + t_out*math.sin(ang):.1f}" stroke="{tick_col}" '
                         f'stroke-width="2" stroke-linecap="round" stroke-opacity="{marker_opacity}"/>')
            else:
                o.append(f'<circle cx="{cx + tick_mid*math.cos(ang):.1f}" '
                         f'cy="{cy + tick_mid*math.sin(ang):.1f}" r="1.6" '
                         f'fill="{tick_col}"/>')

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
    ap.add_argument("--style", choices=("shipped", "ring", "spiral"), default="shipped")
    ap.add_argument("--minutes", type=int, default=75)
    ap.add_argument("--total", type=int, default=0, help="block length; defaults to --minutes")
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=2)
    ap.add_argument("--mods", default="")
    ap.add_argument("--ticks", choices=("between", "on-track"), default="between")
    ap.add_argument("--ring-width", type=int, default=5)
    ap.add_argument("--marker-len", type=float, default=1.0,
                    help="marker length as a fraction of the disc-to-ring gap")
    ap.add_argument("--marker-opacity", type=float, default=1.0)
    ap.add_argument("--armed", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.style, a.minutes, a.total or a.minutes, a.layer, a.battery, a.profile, a.mods, a.ticks, a.ring_width, a.marker_len, a.marker_opacity, a.armed))
    print(f"wrote {out.relative_to(ROOT)}")

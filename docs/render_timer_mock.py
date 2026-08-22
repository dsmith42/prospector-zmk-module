#!/usr/bin/env python3
"""Render a mock of the Operator screen's focus-block timer as an SVG.

Geometry and colours are parsed out of the C sources rather than duplicated
here, so the picture cannot drift from what the firmware actually draws. Rerun
after changing the widget:

    python3 docs/render_timer_mock.py --minutes 21 --total 30

Caveat: the modifier row, battery arcs and output pills are drawn from their
declared sizes and positions but with representative content and approximate
internals — this is an illustration of the timer, not a pixel-exact emulator.
The timer widget itself is exact.
"""

import argparse
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OP = ROOT / "boards/shields/prospector_adapter/src/layouts/operator"

# Panel is 240x280 rotated to landscape.
PANEL_W, PANEL_H = 280, 240


def read(name):
    return (OP / name).read_text()


def define(text, name):
    m = re.search(rf"#define\s+{name}\s+(\w+)", text)
    if not m:
        raise SystemExit(f"could not parse #define {name}")
    return m.group(1)


def colour(name):
    return "#" + define(read("display_colors.h"), name).removeprefix("0x").zfill(6)


def local_int(text, name):
    m = re.search(rf"int\s+{name}\s*=\s*(\d+)\s*;", text)
    if not m:
        raise SystemExit(f"could not parse int {name}")
    return int(m.group(1))


def widget_pos(widget):
    m = re.search(rf"zmk_widget_{widget}_obj\(&\w+\),\s*(\d+),\s*(\d+)\)", read("status_screen.c"))
    if not m:
        raise SystemExit(f"could not parse position for {widget}")
    return int(m.group(1)), int(m.group(2))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def render(minutes_left, total_minutes, layer, batt_l, batt_r, profile):
    tm_c, tm_h = read("timer_meter.c"), read("timer_meter.h")

    bar_count = int(define(tm_h, "TIMER_BAR_COUNT"))
    bar_w = local_int(tm_c, "bar_width")
    bar_gap = local_int(tm_c, "bar_gap")
    bar_h = local_int(tm_c, "bar_height")
    widget_w = 260

    active = colour("DISPLAY_COLOR_TIMER_BAR_ACTIVE")
    spent = colour("DISPLAY_COLOR_TIMER_BAR_SPENT")
    text_col = colour("DISPLAY_COLOR_TIMER_TEXT")
    layer_col = colour("DISPLAY_COLOR_LAYER_TEXT")
    mod_on = colour("DISPLAY_COLOR_MOD_ACTIVE")
    mod_off = colour("DISPLAY_COLOR_MOD_INACTIVE")
    batt_fill = colour("DISPLAY_COLOR_BATTERY_FILL")
    batt_ring = colour("DISPLAY_COLOR_BATTERY_RING")
    batt_label = colour("DISPLAY_COLOR_BATTERY_LABEL")
    ble_on = colour("DISPLAY_COLOR_BLE_ACTIVE_BG")
    usb_off = colour("DISPLAY_COLOR_USB_INACTIVE_BG")
    slot_on = colour("DISPLAY_COLOR_SLOT_ACTIVE_BG")
    slot_off = colour("DISPLAY_COLOR_SLOT_INACTIVE_BG")
    out_on = colour("DISPLAY_COLOR_OUTPUT_ACTIVE_TEXT")
    out_off = colour("DISPLAY_COLOR_OUTPUT_INACTIVE_TEXT")
    slot_text = colour("DISPLAY_COLOR_SLOT_TEXT")
    dot_on = colour("DISPLAY_COLOR_LAYER_DOT_ACTIVE")
    dot_off = colour("DISPLAY_COLOR_LAYER_DOT_INACTIVE")

    # Same arithmetic as active_bars_for(): proportional, rounded up.
    remaining_ms = minutes_left * 60 * 1000
    total_ms = total_minutes * 60 * 1000
    bars_on = 0 if total_ms <= 0 or remaining_ms <= 0 else min(
        bar_count, -(-remaining_ms * bar_count // total_ms))

    tx, ty = widget_pos("timer_meter")
    mx, my = widget_pos("modifier_indicator")
    lx, ly = widget_pos("layer_display")
    bx, by = widget_pos("battery_circles")
    ox, oy = widget_pos("output")

    start_x = (widget_w - (bar_count * bar_w + (bar_count - 1) * bar_gap)) // 2
    mono = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"
    sans = "Inter,'Helvetica Neue',Arial,sans-serif"

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PANEL_W*2}" height="{PANEL_H*2}" '
        f'viewBox="0 0 {PANEL_W} {PANEL_H}" role="img" '
        f'aria-label="Operator status screen showing a {minutes_left} minute focus block remaining">',
        f'<rect width="{PANEL_W}" height="{PANEL_H}" fill="#000000"/>',
    ]

    # modifier row
    for i, name in enumerate(["CMD", "OPT", "CTRL", "SHFT"]):
        o.append(f'<text x="{mx + i*58}" y="{my + 16}" font-family="{sans}" font-size="15" '
                 f'font-weight="600" fill="{mod_off if i else mod_on}">{name}</text>')

    # timer bars
    for i in range(bar_count):
        x = tx + start_x + i * (bar_w + bar_gap)
        o.append(f'<rect x="{x}" y="{ty}" width="{bar_w}" height="{bar_h}" rx="1" '
                 f'fill="{active if i < bars_on else spent}"/>')

    # minutes readout, top-left of the widget
    o.append(f'<rect x="{tx-7}" y="{ty-9}" width="46" height="42" fill="#000000"/>')
    o.append(f'<text x="{tx-1}" y="{ty+22}" font-family="{mono}" font-size="32" '
             f'font-weight="500" fill="{text_col}">{minutes_left}</text>')

    # layer name, bottom-right of the widget
    o.append(f'<text x="{tx+widget_w+2}" y="{ty+bar_h+2}" text-anchor="end" font-family="{sans}" '
             f'font-size="30" font-weight="300" letter-spacing="1.5" fill="{layer_col}">{esc(layer)}</text>')

    # layer position strip
    dots = 7
    dot_gap = 3
    dot_w = (260 - (dots - 1) * dot_gap) // dots
    for i in range(dots):
        o.append(f'<rect x="{lx + i*(dot_w+dot_gap)}" y="{ly}" width="{dot_w}" height="6" rx="2" '
                 f'fill="{dot_on if i == 0 else dot_off}"/>')

    # battery arcs
    for i, pct in enumerate((batt_l, batt_r)):
        cx, cy, r = bx + 22 + i * 62, by + 22, 18
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{batt_ring}" stroke-width="6"/>')
        end = -90 + 360 * pct / 100
        ex = cx + r * math.cos(math.radians(end))
        ey = cy + r * math.sin(math.radians(end))
        o.append(f'<path d="M {cx} {cy-r} A {r} {r} 0 {1 if pct > 50 else 0} 1 {ex:.1f} {ey:.1f}" '
                 f'fill="none" stroke="{batt_fill}" stroke-width="6" stroke-linecap="round"/>')
        o.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" font-family="{mono}" '
                 f'font-size="14" fill="{batt_label}">{pct}</text>')

    # output pills + profile slots
    for i, (name, on) in enumerate((("USB", False), ("BLE", True))):
        o.append(f'<rect x="{ox + i*58}" y="{oy}" width="56" height="29" rx="6" '
                 f'fill="{ble_on if on else usb_off}"/>')
        o.append(f'<text x="{ox + i*58 + 28}" y="{oy+20}" text-anchor="middle" font-family="{sans}" '
                 f'font-size="15" font-weight="600" fill="{out_on if on else out_off}">{name}</text>')

    slots, gap = 5, 2
    sw = (116 - (slots - 1) * gap) // slots
    for i in range(slots):
        x = ox + i * (sw + gap)
        o.append(f'<rect x="{x}" y="{oy+33}" width="{sw}" height="29" rx="6" '
                 f'fill="{slot_on if i == profile else slot_off}"/>')
        o.append(f'<text x="{x + sw//2}" y="{oy+53}" text-anchor="middle" font-family="{mono}" '
                 f'font-size="14" fill="{slot_text}">{i+1}</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=21, help="minutes remaining")
    ap.add_argument("--total", type=int, default=30, help="block length")
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--battery", type=int, nargs=2, default=(87, 89), metavar=("L", "R"))
    ap.add_argument("--profile", type=int, default=1, help="active profile, 0-indexed")
    ap.add_argument("--out", default="docs/images/operator-block-timer.svg")
    a = ap.parse_args()

    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(a.minutes, a.total, a.layer, a.battery[0], a.battery[1], a.profile))
    print(f"wrote {out.relative_to(ROOT)}")

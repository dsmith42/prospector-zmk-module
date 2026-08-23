#!/usr/bin/env python3
"""Compose the dial theme previews into one contact sheet.

Renders every dial_*_theme found in prospector_adapter.overlay, so adding a
theme adds a tile with no change here.

    python3 docs/render_theme_grid.py
    python3 docs/render_theme_grid.py --layer 基本 --out docs/images/theme-grid-jp.svg

The layer name is a parameter because the README shows the same six themes with
Latin and with Japanese names, and the two have to be generated from one source
or they drift apart.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "boards/shields/prospector_adapter/prospector_adapter.overlay"
TILE_W, TILE_H = 280, 240
PAD, LABEL_H, COLS = 16, 30, 3


def themes():
    names = re.findall(r"(dial_[a-z0-9]+_theme):", OVERLAY.read_text())
    return sorted(set(names), key=names.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", default="BASE")
    ap.add_argument("--out", default="docs/images/theme-grid.svg")
    a = ap.parse_args()

    found = themes()
    if not found:
        sys.exit("no dial_*_theme nodes found")

    # Per-theme tiles are intermediates, but they are keyed off the output name
    # so a Latin run and a Japanese run do not overwrite each other's files.
    stem = Path(a.out).stem.replace("theme-grid", "").lstrip("-")
    suffix = f"-{stem}" if stem else ""

    tiles = []
    for name in found:
        out = ROOT / f"docs/images/theme-{name.split('_')[1]}{suffix}.svg"
        subprocess.run(
            [sys.executable, str(ROOT / "docs/render_dial_mock.py"),
             "--minutes", "21", "--total", "30", "--theme", name,
             "--layer", a.layer, "--out", str(out.relative_to(ROOT))],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        body = out.read_text()
        body = body[body.index(">") + 1: body.rindex("</svg>")]
        tiles.append((name.split("_")[1], body))

    rows = (len(tiles) + COLS - 1) // COLS
    width = COLS * TILE_W + (COLS + 1) * PAD
    height = rows * (TILE_H + LABEL_H) + (rows + 1) * PAD

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
         f'viewBox="0 0 {width} {height}">',
         f'<rect width="{width}" height="{height}" fill="#101010"/>']

    for i, (label, body) in enumerate(tiles):
        col, row = i % COLS, i // COLS
        x = PAD + col * (TILE_W + PAD)
        y = PAD + row * (TILE_H + LABEL_H + PAD)
        o.append(f'<g transform="translate({x},{y})">')
        o.append(f'<rect width="{TILE_W}" height="{TILE_H}" fill="#000000" rx="10"/>')
        o.append(f'<svg width="{TILE_W}" height="{TILE_H}" viewBox="0 0 {TILE_W} {TILE_H}">{body}</svg>')
        o.append(f'<text x="{TILE_W/2}" y="{TILE_H + 21}" text-anchor="middle" '
                 f'font-family="Inter,Helvetica,Arial,sans-serif" font-size="16" '
                 f'fill="#c8c8c8">{label}</text>')
        o.append("</g>")

    o.append("</svg>")
    dest = ROOT / a.out
    dest.write_text("\n".join(o))
    print(f"wrote {dest.relative_to(ROOT)} — {len(tiles)} themes")


if __name__ == "__main__":
    main()

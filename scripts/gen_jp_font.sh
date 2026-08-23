#!/usr/bin/env bash
#
# Regenerate the Japanese glyph subset used for layer names.
#
# The point of this script is that we never ship a whole CJK face. M PLUS 1
# covers the full jouyou set, which at 20px/4bpp is roughly 680 KB of flash --
# far more than the dongle has spare. Instead we bake only the characters that
# actually appear on the display, which is currently 18 glyphs for about 2.9 KB.
#
# To add a layer name, append its characters to SYMBOLS and re-run. Duplicates
# are harmless; lv_font_conv de-duplicates.
#
# Requires node (for npx). The TTF is downloaded rather than vendored, both to
# keep the repo small and to make the OFL provenance obvious.

set -euo pipefail

SIZE=20
BPP=4
OUT_NAME="MPLUS1_JP_${SIZE}"

# Layer names rendered by the dial layout. Keep this list and the table in
# README.md in step -- the README is the human-readable index of what is here.
#
#   基本 kihon    Base      記号 kigou    Symbol
#   数字 suuji    Number    移動 idou     Nav
#   配置 haichi   Arrange   集中 shuuchuu Timer
#   マウス mausu  Mouse     タイマー taimaa (alternative for the timer layer)
SYMBOLS="基本記号数字移動配置集中マウスタイー"

# M PLUS 1 Medium: SIL Open Font License 1.1, geometric grotesque, which is the
# closest Japanese match to the Foundry Gridnik Latin it sits beside.
FONT_URL="https://github.com/coz-m/MPLUS_FONTS/raw/master/fonts/MPLUS1/ttf/MPLUS1-Medium.ttf"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out_dir="$repo_root/boards/shields/prospector_adapter/src/fonts"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "Fetching M PLUS 1 Medium..."
curl -sSL --fail -o "$work/MPLUS1-Medium.ttf" "$FONT_URL"

echo "Converting ${#SYMBOLS} characters at ${SIZE}px, ${BPP}bpp..."
npx -y lv_font_conv@1.5.2 \
    --font "$work/MPLUS1-Medium.ttf" \
    --bpp "$BPP" \
    --size "$SIZE" \
    --no-compress \
    --format lvgl \
    --symbols "$SYMBOLS" \
    -o "$out_dir/${OUT_NAME}.c"

# lv_font_conv emits a conditional include that resolves to "lvgl/lvgl.h" unless
# LV_LVGL_H_INCLUDE_SIMPLE is defined, which Zephyr does not define -- and that
# path is not on the include path here, so the file fails to compile. Every other
# font in this tree uses <lvgl.h>; match them. Caught by the ref-dial-jp build.
python3 - "$out_dir/${OUT_NAME}.c" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
old = '#ifdef LV_LVGL_H_INCLUDE_SIMPLE\n#include "lvgl.h"\n#else\n#include "lvgl/lvgl.h"\n#endif'
assert old in s, "lv_font_conv include block changed shape; update gen_jp_font.sh"
s = s.replace(old, '#include <lvgl.h>')

# lv_font_conv names the include guard after the font family and the variable
# after the output filename. For M PLUS those collide, so `#define MPLUS1_JP_18 1`
# turns the definition below into `const lv_font_t 1 = {`. The bundled fonts dodge
# this by accident -- FoundryGridnikMedium happens not to match FG_Medium_20 -- so
# give the guard its own name rather than relying on the same luck.
guard = p.rsplit('/', 1)[-1][:-2]
safe = 'MPLUS1MEDIUM_' + guard.rsplit('_', 1)[-1]
assert f'#define {guard} 1' in s, "guard macro changed shape; update gen_jp_font.sh"
s = s.replace(f'#ifndef {guard}', f'#ifndef {safe}')
s = s.replace(f'#define {guard} 1', f'#define {safe} 1')
s = s.replace(f'#if {guard}', f'#if {safe}')

open(p, 'w').write(s)
PYEOF

# lv_font_conv records the exact argv it was invoked with in a comment at the
# top of the output. Those are absolute paths into a temp dir and someone's home
# directory, so the file would differ on every machine and leak the path. Rewrite
# them to the stable form, which makes regeneration a byte-for-byte no-op and
# keeps the diff honest about whether the glyphs actually changed.
sed -i.bak \
    -e "s| --font [^ ]*/MPLUS1-Medium.ttf| --font ttf/MPLUS1-Medium.ttf|" \
    -e "s| -o [^ ]*/${OUT_NAME}.c| -o ${OUT_NAME}.c|" \
    "$out_dir/${OUT_NAME}.c"
rm -f "$out_dir/${OUT_NAME}.c.bak"

echo "Wrote $out_dir/${OUT_NAME}.c ($(wc -c < "$out_dir/${OUT_NAME}.c") bytes of C)"
echo
echo "Note: SIZE is tuned against the Latin face it sits beside, whose caps are"
echo "14px tall. 20px puts the kanji box at 18px -- a deliberate overshoot, judged"
echo "on hardware, because the denser glyphs need the body to read at a glance."
echo "16px matches the cap height exactly and looks undersized. Below 16px the"
echo "strokes start to fill in."

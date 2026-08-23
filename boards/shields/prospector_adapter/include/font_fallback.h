#pragma once

#include <lvgl.h>

/* Latin fonts on this shield are ASCII subsets, so a layer named in Japanese
 * renders as nothing at all. Rather than convert every face to cover CJK --
 * which we cannot do, the Latin faces are commercial and we only have the
 * baked C output -- we hang a small Japanese subset off LVGL's fallback chain.
 * The base font keeps drawing Latin; only codepoints it lacks fall through.
 *
 * `storage` must have static lifetime and is where the wrapped font lives,
 * because the generated fonts are const and cannot be modified in place. Each
 * call site owns its own storage, so layouts do not interfere with each other.
 *
 * With CONFIG_PROSPECTOR_LAYER_FONT_JP=n this returns `base` untouched and
 * costs nothing, so call sites need no conditional compilation of their own.
 */
const lv_font_t *prospector_font_jp(const lv_font_t *base, lv_font_t *storage);

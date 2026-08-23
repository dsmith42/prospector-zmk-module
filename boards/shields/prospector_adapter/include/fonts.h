#pragma once

#include <lvgl.h>

#if defined(CONFIG_PROSPECTOR_STATUS_SCREEN_CLASSIC)

LV_FONT_DECLARE(Symbols_Bold_26);
LV_FONT_DECLARE(Symbols_Regular_28);
LV_FONT_DECLARE(Symbols_Semibold_32);
LV_FONT_DECLARE(FG_Medium_20);
LV_FONT_DECLARE(FG_Medium_24);
LV_FONT_DECLARE(FR_Regular_48);
LV_FONT_DECLARE(FR_Thin_48);
LV_FONT_DECLARE(DINishCondensed_SemiBold_22);

#elif defined(CONFIG_PROSPECTOR_STATUS_SCREEN_RADII)

LV_FONT_DECLARE(Symbols_Semibold_32);
LV_FONT_DECLARE(Symbols_Semibold_28);
LV_FONT_DECLARE(Symbols_Medium_28);
LV_FONT_DECLARE(Symbols_Regular_28);
LV_FONT_DECLARE(Symbols_Bold_26);
LV_FONT_DECLARE(PPF_NarrowThin_64);
LV_FONT_DECLARE(DINishCondensed_SemiBold_22);

#elif defined(CONFIG_PROSPECTOR_STATUS_SCREEN_FIELD)

LV_FONT_DECLARE(Symbols_Semibold_32);
LV_FONT_DECLARE(Symbols_Regular_28);
LV_FONT_DECLARE(Symbols_Bold_26);
LV_FONT_DECLARE(FR_Regular_30);
LV_FONT_DECLARE(FR_Regular_36);
LV_FONT_DECLARE(FG_Medium_26);
LV_FONT_DECLARE(DINishCondensed_SemiBold_20);

#elif defined(CONFIG_PROSPECTOR_STATUS_SCREEN_OPERATOR)

LV_FONT_DECLARE(FG_Medium_20);
LV_FONT_DECLARE(FG_Medium_21);
LV_FONT_DECLARE(FG_Medium_26);
LV_FONT_DECLARE(DINishExpanded_Light_36);
LV_FONT_DECLARE(FR_Medium_32);
LV_FONT_DECLARE(DINish_Medium_24);

#elif defined(CONFIG_PROSPECTOR_STATUS_SCREEN_DIAL)

LV_FONT_DECLARE(Symbols_Bold_26);
LV_FONT_DECLARE(FR_Medium_32);
LV_FONT_DECLARE(DINish_Medium_24);
LV_FONT_DECLARE(DINishCondensed_SemiBold_20);
LV_FONT_DECLARE(FG_Medium_20);

#endif

/* Not part of the per-layout blocks above: the Japanese subset is a fallback
 * hung off whichever face a layout already uses, so it is declared once for
 * everyone rather than repeated per layout. */
#if defined(CONFIG_PROSPECTOR_LAYER_FONT_JP)
LV_FONT_DECLARE(MPLUS1_JP_18);
#endif

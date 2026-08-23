#include <font_fallback.h>

#include <zephyr/kernel.h>

#include <fonts.h>

const lv_font_t *prospector_font_jp(const lv_font_t *base, lv_font_t *storage) {
#if IS_ENABLED(CONFIG_PROSPECTOR_LAYER_FONT_JP)
    if (base == NULL || storage == NULL) {
        return base;
    }

    *storage = *base;
    storage->fallback = &MPLUS1_JP_18;
    return storage;
#else
    ARG_UNUSED(storage);
    return base;
#endif
}

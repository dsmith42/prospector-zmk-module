#define DT_DRV_COMPAT zmk_behavior_prospector_brightness

#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <drivers/behavior.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/behavior.h>
#include <zmk/prospector_brightness.h>
#include <dt-bindings/zmk/prospector_brightness.h>

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

/* Split peripherals compile the keymap but not the display, so they need the
 * symbol without the implementation. The shield's brightness.c provides the
 * real one and overrides this. */
__attribute__((weak)) void prospector_brightness_step(int delta) { ARG_UNUSED(delta); }

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    int step = CONFIG_PROSPECTOR_BRIGHTNESS_STEP;

    prospector_brightness_step(binding->param1 == BRI_UP ? step : -step);

    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_prospector_brightness_init(const struct device *dev) { return 0; }

static const struct behavior_driver_api behavior_prospector_brightness_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
};

BEHAVIOR_DT_INST_DEFINE(0, behavior_prospector_brightness_init, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT,
                        &behavior_prospector_brightness_driver_api);

#endif /* DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT) */

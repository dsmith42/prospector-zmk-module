#define DT_DRV_COMPAT zmk_behavior_block_timer

#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <drivers/behavior.h>

#include <zephyr/logging/log.h>
LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#include <zmk/behavior.h>
#include <zmk/block_timer.h>
#include <dt-bindings/zmk/block_timer.h>

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

/* See dt-bindings/zmk/block_timer.h: BLK_STOP stops, BLK_START begins the
 * armed length, anything else arms that many minutes. */
static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    switch (binding->param1) {
    case BLK_STOP:
        zmk_block_timer_stop();
        break;
    case BLK_START:
        zmk_block_timer_start_armed();
        break;
    default:
        zmk_block_timer_arm((uint16_t)binding->param1);
        break;
    }

    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_block_timer_init(const struct device *dev) { return 0; }

static const struct behavior_driver_api behavior_block_timer_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
};

BEHAVIOR_DT_INST_DEFINE(0, behavior_block_timer_init, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_block_timer_driver_api);

#endif /* DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT) */

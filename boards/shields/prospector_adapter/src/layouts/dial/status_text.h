#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

#define STATUS_MOD_COUNT 4
#define STATUS_PERIPHERAL_COUNT 2

/* Every diagnostic element in one widget: they are all plain text, all
 * consulted rather than watched, and grouping them keeps the object count down
 * on a 20KB LVGL pool. */
struct zmk_widget_status_text {
    sys_snode_t node;
    lv_obj_t *obj;
    lv_obj_t *layer_label;
    lv_obj_t *mods[STATUS_MOD_COUNT];
    lv_obj_t *profile_label;
    lv_obj_t *battery[STATUS_PERIPHERAL_COUNT];
};

int zmk_widget_status_text_init(struct zmk_widget_status_text *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_status_text_obj(struct zmk_widget_status_text *widget);

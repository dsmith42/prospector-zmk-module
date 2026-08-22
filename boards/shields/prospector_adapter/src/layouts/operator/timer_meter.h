#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

#define TIMER_BAR_COUNT 26

/* Replaces the stock WPM meter. Same geometry — 26 bars plus a numeric readout
 * top-left and the layer name bottom-right — so this is a data-source and
 * colour change, not a new layout. */
struct zmk_widget_timer_meter {
    sys_snode_t node;
    lv_obj_t *obj;
    lv_obj_t *bars[TIMER_BAR_COUNT];
    lv_obj_t *minutes_label;
    lv_obj_t *layer_label;
};

int zmk_widget_timer_meter_init(struct zmk_widget_timer_meter *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_timer_meter_obj(struct zmk_widget_timer_meter *widget);

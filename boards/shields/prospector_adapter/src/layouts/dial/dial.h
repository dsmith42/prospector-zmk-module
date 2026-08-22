#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

/* Absolute 60 minute face. Blocks are capped at this, so the dial never wraps
 * and there is no lap/overflow handling to get wrong. */
#define DIAL_FACE_MINUTES 60

/* Major ticks only, one per five minutes. 60 individual tick objects would cost
 * roughly 12KB of LVGL's 20KB pool; twelve costs a fifth of that. If the face
 * reads bare on hardware, the upgrade is a pre-rendered 1-bit tick ring image
 * in flash, not more objects. */
#define DIAL_TICK_COUNT 12

#define DIAL_CX 107
#define DIAL_CY 106
#define DIAL_R 84
#define DIAL_TICK_IN (DIAL_R + 8)
#define DIAL_TICK_OUT (DIAL_R + 16)
#define DIAL_HUB_R 8

struct zmk_widget_dial {
    sys_snode_t node;
    lv_obj_t *obj;
    lv_obj_t *arc;
    lv_obj_t *ticks[DIAL_TICK_COUNT];
    lv_obj_t *hand;
    lv_obj_t *hub;
    lv_obj_t *minutes_label;
    lv_point_precise_t hand_points[2];
};

int zmk_widget_dial_init(struct zmk_widget_dial *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_dial_obj(struct zmk_widget_dial *widget);

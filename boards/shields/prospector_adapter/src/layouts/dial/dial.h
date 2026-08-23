#pragma once

#include <lvgl.h>
#include <zephyr/kernel.h>

/* The disc is an absolute 60 minute face. Blocks longer than that spill onto a
 * thin overflow ring in the empty band between disc and ticks, so the ring is
 * the high digit and the disc the low digit — nothing wraps, nothing jumps. */
#define DIAL_FACE_MINUTES 60

/* One disc plus one ring, so two hours is the ceiling. */
#define DIAL_MAX_MINUTES 120

/* Major ticks only, one per five minutes. 60 individual tick objects would cost
 * roughly 12KB of LVGL's 20KB pool; twelve costs a fifth of that. If the face
 * reads bare on hardware, the upgrade is a pre-rendered 1-bit tick ring image
 * in flash, not more objects. */
#define DIAL_TICK_COUNT 12

#define DIAL_CX 107
#define DIAL_CY 106
#define DIAL_R 71
#define DIAL_TICK_IN (DIAL_R + 21)
#define DIAL_TICK_OUT (DIAL_R + 29)
#define DIAL_HUB_R 8

/* Overflow ring, placed to leave clear air either side: >=7px from the disc
   edge and >=5px from the tick dots. Offsets are explicit rather than derived,
   so changing the disc radius does not silently close the gaps. */
#define DIAL_RING_R (DIAL_R + 13)
#define DIAL_RING_W 5

/* The hand runs out to the centre line of the overflow ring band. LVGL strokes
   an arc inward from the radius it is given, so the band occupies
   DIAL_RING_R - DIAL_RING_W .. DIAL_RING_R and its middle is half a width in.
   Rounds outward by half a pixel; the alternative is half a pixel the other way.

   Constant, deliberately. The ring only appears past the hour, and a hand that
   grew when it did would read as two different hands rather than one that
   always points at the same track. */
#define DIAL_HAND_R (DIAL_RING_R - DIAL_RING_W / 2)

struct zmk_widget_dial {
    sys_snode_t node;
    lv_obj_t *obj;
    lv_obj_t *face;
    lv_obj_t *face_ring;
    lv_obj_t *arc;
    lv_obj_t *ring;
    lv_obj_t *ticks[DIAL_TICK_COUNT];
    lv_obj_t *hand;
    lv_obj_t *hub;
    lv_obj_t *minutes_label;
    lv_point_precise_t hand_points[2];
};

int zmk_widget_dial_init(struct zmk_widget_dial *widget, lv_obj_t *parent);
lv_obj_t *zmk_widget_dial_obj(struct zmk_widget_dial *widget);

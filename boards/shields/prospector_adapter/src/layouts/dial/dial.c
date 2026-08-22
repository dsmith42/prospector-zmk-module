#include "dial.h"

#include <zephyr/kernel.h>
#include <math.h>

/* Zephyr's math.h does not expose M_PI without _GNU_SOURCE. */
#define DIAL_PI 3.14159265358979323846
#include <zmk/display.h>
#include <zmk/events/block_timer_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/block_timer.h>

#include <fonts.h>
#include "display_colors.h"

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);
static struct k_work_delayable dial_tick_work;

static int prev_minutes = -1;
static int prev_disc_track = -1;
static int prev_disc_fill = -1;
static int prev_ring_track = -1;
static int prev_ring_fill = -1;
static int prev_hand = -1;
static int prev_armed = -1;    /* -1 unknown, 0 running, 1 armed preview */

/* Degrees of dial per minute. */
static int deg_of(int minutes) {
    if (minutes <= 0) {
        return 0;
    }
    if (minutes >= DIAL_FACE_MINUTES) {
        return 360;
    }
    return (minutes * 360) / DIAL_FACE_MINUTES;
}

struct dial_state {
    bool running;
};

static void dial_render(int disc_track, int disc_fill, int ring_track, int ring_fill,
                        int hand_deg, int minutes, bool armed_preview) {
    struct zmk_widget_dial *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        if ((int)armed_preview != prev_armed) {
            uint32_t wedge = armed_preview ? DISPLAY_COLOR_DIAL_ARMED
                                           : DISPLAY_COLOR_TIMER_BAR_ACTIVE;
            lv_obj_set_style_arc_color(widget->arc, lv_color_hex(wedge), LV_PART_INDICATOR);
            lv_obj_set_style_arc_color(widget->ring, lv_color_hex(wedge), LV_PART_INDICATOR);
            lv_obj_set_style_line_color(widget->hand,
                                        lv_color_hex(armed_preview ? DISPLAY_COLOR_DIAL_ARMED
                                                                   : DISPLAY_COLOR_DIAL_HAND),
                                        LV_PART_MAIN);
            lv_obj_set_style_text_color(widget->minutes_label,
                                        lv_color_hex(armed_preview ? DISPLAY_COLOR_DIAL_ARMED
                                                                   : DISPLAY_COLOR_DIAL_MINUTES),
                                        LV_PART_MAIN);
        }

        /* Grey track spans the BLOCK, not the face, so a 45 leaves a black
         * quarter and the finished screen still shows how long the block was. */
        if (disc_track != prev_disc_track) {
            lv_arc_set_bg_angles(widget->arc, 0, disc_track);
        }
        if (disc_fill != prev_disc_fill) {
            lv_arc_set_angles(widget->arc, 0, disc_fill);
        }

        if (ring_track != prev_ring_track) {
            if (ring_track > 0) {
                lv_arc_set_bg_angles(widget->ring, 0, ring_track);
                lv_obj_clear_flag(widget->ring, LV_OBJ_FLAG_HIDDEN);
                lv_obj_clear_flag(widget->face_ring, LV_OBJ_FLAG_HIDDEN);
            } else {
                lv_obj_add_flag(widget->ring, LV_OBJ_FLAG_HIDDEN);
                lv_obj_add_flag(widget->face_ring, LV_OBJ_FLAG_HIDDEN);
            }
        }
        if (ring_fill != prev_ring_fill) {
            lv_arc_set_angles(widget->ring, 0, ring_fill);
        }

        if (hand_deg != prev_hand) {
            double rad = (hand_deg - 90.0) * DIAL_PI / 180.0;
            widget->hand_points[1].x = DIAL_CX + (DIAL_R + 4) * cos(rad);
            widget->hand_points[1].y = DIAL_CY + (DIAL_R + 4) * sin(rad);
            lv_line_set_points(widget->hand, widget->hand_points, 2);
        }

        if (minutes != prev_minutes) {
            char text[5];
            snprintf(text, sizeof(text), "%d", minutes);
            lv_label_set_text(widget->minutes_label, text);
        }
    }

    prev_disc_track = disc_track;
    prev_disc_fill = disc_fill;
    prev_ring_track = ring_track;
    prev_ring_fill = ring_fill;
    prev_hand = hand_deg;
    prev_minutes = minutes;
    prev_armed = (int)armed_preview;
}

static void refresh(void) {
    struct zmk_block_timer_state state;
    zmk_block_timer_get(&state);

    bool live = state.running && state.remaining_ms > 0;

    /* Not running: preview the armed length, dimmed, at its full extent. */
    int total_min = live ? (int)(state.total_ms / 60000) : (int)state.armed_minutes;
    int left_min = live ? (int)((state.remaining_ms + 59999) / 60000) : total_min;

    if (total_min > DIAL_MAX_MINUTES) {
        total_min = DIAL_MAX_MINUTES;
    }
    if (left_min > total_min) {
        left_min = total_min;
    }

    int disc_track = deg_of(total_min);
    int disc_fill = deg_of(left_min);
    int ring_track = deg_of(total_min - DIAL_FACE_MINUTES);
    int ring_fill = deg_of(left_min - DIAL_FACE_MINUTES);

    /* One hand, one length. Above the hour the ring fraction and below it the
     * disc fraction are both (remaining mod 60) / 60, so the hand sweeps
     * continuously past twelve at the boundary rather than jumping. */
    int hand_deg = deg_of(left_min % DIAL_FACE_MINUTES);
    if (hand_deg >= 360) {
        hand_deg = 0;
    }

    if (disc_track != prev_disc_track || disc_fill != prev_disc_fill ||
        ring_track != prev_ring_track || ring_fill != prev_ring_fill ||
        hand_deg != prev_hand || left_min != prev_minutes || (int)!live != prev_armed) {
        dial_render(disc_track, disc_fill, ring_track, ring_fill, hand_deg, left_min, !live);
    }

    /* Stop ticking at zero. An empty block with the hand at twelve is both the
     * finished state and the pre-start state. */
    if (live) {
        k_work_schedule(&dial_tick_work, K_SECONDS(1));
    }
}

static void dial_tick_work_handler(struct k_work *work) { refresh(); }

static void dial_update_cb(struct dial_state state) {
    k_work_cancel_delayable(&dial_tick_work);
    refresh();
}

static struct dial_state dial_get_state(const zmk_event_t *eh) {
    struct zmk_block_timer_state state;
    zmk_block_timer_get(&state);

    return (struct dial_state){.running = state.running};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_dial, struct dial_state, dial_update_cb, dial_get_state)
ZMK_SUBSCRIPTION(widget_dial, zmk_block_timer_state_changed);

int zmk_widget_dial_init(struct zmk_widget_dial *widget, lv_obj_t *parent) {
    widget->obj = lv_obj_create(parent);
    lv_obj_set_size(widget->obj, 280, 240);
    lv_obj_set_style_bg_opa(widget->obj, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->obj, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(widget->obj, 0, LV_PART_MAIN);

    /* Ticks first so the disc paints over their inner ends. */
    for (int i = 0; i < DIAL_TICK_COUNT; i++) {
        double rad = (360.0 * i / DIAL_TICK_COUNT - 90.0) * DIAL_PI / 180.0;
        int len = DIAL_TICK_OUT - DIAL_TICK_IN;
        int mx = DIAL_CX + (DIAL_TICK_IN + len / 2) * cos(rad);
        int my = DIAL_CY + (DIAL_TICK_IN + len / 2) * sin(rad);

        widget->ticks[i] = lv_obj_create(widget->obj);
        lv_obj_set_size(widget->ticks[i], 3, 3);
        lv_obj_set_pos(widget->ticks[i], mx - 1, my - 1);
        lv_obj_set_style_bg_color(widget->ticks[i], lv_color_hex(DISPLAY_COLOR_DIAL_TICK), LV_PART_MAIN);
        lv_obj_set_style_bg_opa(widget->ticks[i], LV_OPA_COVER, LV_PART_MAIN);
        lv_obj_set_style_border_width(widget->ticks[i], 0, LV_PART_MAIN);
        lv_obj_set_style_radius(widget->ticks[i], 2, LV_PART_MAIN);
        lv_obj_set_style_pad_all(widget->ticks[i], 0, LV_PART_MAIN);
    }

    /* Face: the whole hour, always full, behind the block track. Without it
     * the unused part of a short block reads as a missing chunk rather than as
     * part of a dial. */
    widget->face = lv_obj_create(widget->obj);
    lv_obj_set_size(widget->face, DIAL_R * 2, DIAL_R * 2);
    lv_obj_set_pos(widget->face, DIAL_CX - DIAL_R, DIAL_CY - DIAL_R);
    lv_obj_set_style_radius(widget->face, LV_RADIUS_CIRCLE, LV_PART_MAIN);
    lv_obj_set_style_bg_color(widget->face, lv_color_hex(DISPLAY_COLOR_DIAL_FACE), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(widget->face, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->face, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(widget->face, 0, LV_PART_MAIN);

    widget->face_ring = lv_arc_create(widget->obj);
    lv_obj_remove_style(widget->face_ring, NULL, LV_PART_KNOB);
    lv_obj_clear_flag(widget->face_ring, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(widget->face_ring, DIAL_RING_R * 2, DIAL_RING_R * 2);
    lv_obj_set_pos(widget->face_ring, DIAL_CX - DIAL_RING_R, DIAL_CY - DIAL_RING_R);
    lv_arc_set_rotation(widget->face_ring, 270);
    lv_arc_set_bg_angles(widget->face_ring, 0, 360);
    lv_arc_set_angles(widget->face_ring, 0, 0);
    lv_obj_set_style_arc_width(widget->face_ring, DIAL_RING_W, LV_PART_MAIN);
    lv_obj_set_style_arc_color(widget->face_ring, lv_color_hex(DISPLAY_COLOR_DIAL_FACE), LV_PART_MAIN);
    lv_obj_set_style_arc_opa(widget->face_ring, LV_OPA_TRANSP, LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(widget->face_ring, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->face_ring, 0, LV_PART_MAIN);
    lv_obj_add_flag(widget->face_ring, LV_OBJ_FLAG_HIDDEN);

    /* An arc whose width equals its radius renders as a filled pie sector,
     * which is how you get a wedge out of LVGL without a canvas. */
    widget->arc = lv_arc_create(widget->obj);
    lv_obj_remove_style(widget->arc, NULL, LV_PART_KNOB);
    lv_obj_clear_flag(widget->arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(widget->arc, DIAL_R * 2, DIAL_R * 2);
    lv_obj_set_pos(widget->arc, DIAL_CX - DIAL_R, DIAL_CY - DIAL_R);
    lv_arc_set_rotation(widget->arc, 270);
    lv_arc_set_bg_angles(widget->arc, 0, 0);
    lv_arc_set_angles(widget->arc, 0, 0);
    lv_obj_set_style_arc_width(widget->arc, DIAL_R, LV_PART_MAIN);
    lv_obj_set_style_arc_width(widget->arc, DIAL_R, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(widget->arc, lv_color_hex(DISPLAY_COLOR_DIAL_BLOCK), LV_PART_MAIN);
    lv_obj_set_style_arc_color(widget->arc, lv_color_hex(DISPLAY_COLOR_TIMER_BAR_ACTIVE), LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(widget->arc, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->arc, 0, LV_PART_MAIN);

    widget->ring = lv_arc_create(widget->obj);
    lv_obj_remove_style(widget->ring, NULL, LV_PART_KNOB);
    lv_obj_clear_flag(widget->ring, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(widget->ring, DIAL_RING_R * 2, DIAL_RING_R * 2);
    lv_obj_set_pos(widget->ring, DIAL_CX - DIAL_RING_R, DIAL_CY - DIAL_RING_R);
    lv_arc_set_rotation(widget->ring, 270);
    lv_arc_set_bg_angles(widget->ring, 0, 0);
    lv_arc_set_angles(widget->ring, 0, 0);
    lv_obj_set_style_arc_width(widget->ring, DIAL_RING_W, LV_PART_MAIN);
    lv_obj_set_style_arc_width(widget->ring, DIAL_RING_W, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(widget->ring, lv_color_hex(DISPLAY_COLOR_DIAL_BLOCK), LV_PART_MAIN);
    lv_obj_set_style_arc_color(widget->ring, lv_color_hex(DISPLAY_COLOR_TIMER_BAR_ACTIVE), LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(widget->ring, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->ring, 0, LV_PART_MAIN);
    lv_obj_add_flag(widget->ring, LV_OBJ_FLAG_HIDDEN);

    widget->hand_points[0].x = DIAL_CX;
    widget->hand_points[0].y = DIAL_CY;
    widget->hand_points[1].x = DIAL_CX;
    widget->hand_points[1].y = DIAL_CY - (DIAL_R + 4);

    widget->hand = lv_line_create(widget->obj);
    lv_line_set_points(widget->hand, widget->hand_points, 2);
    lv_obj_set_style_line_width(widget->hand, 4, LV_PART_MAIN);
    lv_obj_set_style_line_rounded(widget->hand, true, LV_PART_MAIN);
    lv_obj_set_style_line_color(widget->hand, lv_color_hex(DISPLAY_COLOR_DIAL_HAND), LV_PART_MAIN);

    widget->hub = lv_obj_create(widget->obj);
    lv_obj_set_size(widget->hub, DIAL_HUB_R * 2, DIAL_HUB_R * 2);
    lv_obj_set_pos(widget->hub, DIAL_CX - DIAL_HUB_R, DIAL_CY - DIAL_HUB_R);
    lv_obj_set_style_radius(widget->hub, LV_RADIUS_CIRCLE, LV_PART_MAIN);
    lv_obj_set_style_bg_color(widget->hub, lv_color_hex(DISPLAY_COLOR_DIAL_HUB), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(widget->hub, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->hub, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(widget->hub, 0, LV_PART_MAIN);

    /* Minutes top-right. Muted: a check on the dial, not the display. */
    widget->minutes_label = lv_label_create(widget->obj);
    lv_label_set_text(widget->minutes_label, "0");
    lv_obj_set_style_text_font(widget->minutes_label, &FR_Medium_32, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->minutes_label, lv_color_hex(DISPLAY_COLOR_DIAL_MINUTES), LV_PART_MAIN);
    lv_obj_align(widget->minutes_label, LV_ALIGN_TOP_RIGHT, -10, 22);

    sys_slist_append(&widgets, &widget->node);
    widget_dial_init();

    k_work_init_delayable(&dial_tick_work, dial_tick_work_handler);

    return 0;
}

lv_obj_t *zmk_widget_dial_obj(struct zmk_widget_dial *widget) { return widget->obj; }

#include "dial.h"

#include <zephyr/kernel.h>
#include <math.h>
#include <zmk/display.h>
#include <zmk/events/block_timer_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/block_timer.h>

#include <fonts.h>
#include "display_colors.h"

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);
static struct k_work_delayable dial_tick_work;

static int prev_minutes = -1;
static int prev_tenths = -1;   /* wedge angle in tenths of a degree */

struct dial_state {
    bool running;
};

/* Minutes remaining, rounded UP: never read as finished with 59s left. */
static int minutes_remaining(int64_t remaining_ms) {
    return (int)((remaining_ms + 59999) / 60000);
}

static void dial_render(int angle_tenths, int minutes) {
    struct zmk_widget_dial *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        if (angle_tenths != prev_tenths) {
            /* LVGL arcs run clockwise from the rotation origin, which is set to
             * the top in init, so the indicator is simply 0 -> sweep. */
            lv_arc_set_angles(widget->arc, 0, angle_tenths / 10);

            double rad = (angle_tenths / 10.0 - 90.0) * M_PI / 180.0;
            widget->hand_points[1].x = DIAL_CX + (DIAL_R + 4) * cos(rad);
            widget->hand_points[1].y = DIAL_CY + (DIAL_R + 4) * sin(rad);
            lv_line_set_points(widget->hand, widget->hand_points, 2);
        }

        if (minutes != prev_minutes) {
            char text[4];
            snprintf(text, sizeof(text), "%d", minutes);
            lv_label_set_text(widget->minutes_label, text);
        }
    }

    prev_tenths = angle_tenths;
    prev_minutes = minutes;
}

static void refresh(void) {
    struct zmk_block_timer_state state;
    zmk_block_timer_get(&state);

    int minutes = minutes_remaining(state.remaining_ms);
    int64_t face_ms = (int64_t)DIAL_FACE_MINUTES * 60 * 1000;
    int64_t remaining = state.remaining_ms > face_ms ? face_ms : state.remaining_ms;
    int angle_tenths = (int)((remaining * 3600) / face_ms);

    if (angle_tenths != prev_tenths || minutes != prev_minutes) {
        dial_render(angle_tenths, minutes);
    }

    /* Stop ticking at zero. An empty dial with the hand at twelve is both the
     * finished state and the pre-start state — one quiet state, not two. */
    if (state.running && state.remaining_ms > 0) {
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
        double rad = (360.0 * i / DIAL_TICK_COUNT - 90.0) * M_PI / 180.0;
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

    /* An arc whose width equals its radius renders as a filled pie sector,
     * which is how you get a wedge out of LVGL without a canvas. */
    widget->arc = lv_arc_create(widget->obj);
    lv_obj_remove_style(widget->arc, NULL, LV_PART_KNOB);
    lv_obj_clear_flag(widget->arc, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(widget->arc, DIAL_R * 2, DIAL_R * 2);
    lv_obj_set_pos(widget->arc, DIAL_CX - DIAL_R, DIAL_CY - DIAL_R);
    lv_arc_set_rotation(widget->arc, 270);
    lv_arc_set_bg_angles(widget->arc, 0, 360);
    lv_arc_set_angles(widget->arc, 0, 0);
    lv_obj_set_style_arc_width(widget->arc, DIAL_R, LV_PART_MAIN);
    lv_obj_set_style_arc_width(widget->arc, DIAL_R, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(widget->arc, lv_color_hex(DISPLAY_COLOR_TIMER_BAR_SPENT), LV_PART_MAIN);
    lv_obj_set_style_arc_color(widget->arc, lv_color_hex(DISPLAY_COLOR_TIMER_BAR_ACTIVE), LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(widget->arc, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->arc, 0, LV_PART_MAIN);

    widget->hand_points[0].x = DIAL_CX;
    widget->hand_points[0].y = DIAL_CY;
    widget->hand_points[1].x = DIAL_CX;
    widget->hand_points[1].y = DIAL_CY - (DIAL_R + 4);

    widget->hand = lv_line_create(widget->obj);
    lv_line_set_points(widget->hand, widget->hand_points, 2);
    lv_obj_set_style_line_width(widget->hand, 4, LV_PART_MAIN);
    lv_obj_set_style_line_rounded(widget->hand, true, LV_PART_MAIN);
    lv_obj_set_style_line_color(widget->hand, lv_color_hex(DISPLAY_COLOR_TIMER_BAR_ACTIVE), LV_PART_MAIN);

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

#include "timer_meter.h"

#include <zephyr/kernel.h>
#include <ctype.h>
#include <zmk/display.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/block_timer_state_changed.h>
#include <zmk/event_manager.h>
#include <zmk/block_timer.h>
#include <zmk/keymap.h>

#include <fonts.h>
#include "display_colors.h"

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);
static struct k_work_delayable timer_tick_work;

/* Rendered state, kept so a tick that changes nothing visible costs nothing. */
static int prev_active_bars = -1;
static int prev_minutes = -1;

struct timer_meter_state {
    bool running;
};

struct layer_state {
    uint8_t index;
};

/* Minutes remaining, rounded UP: show "1" until the block is genuinely done,
 * so it never reads finished with 59 seconds left. */
static int minutes_remaining(int64_t remaining_ms) {
    return (int)((remaining_ms + 59999) / 60000);
}

/* Bars proportional to the chosen block length, so the bar always starts full
 * and a 30 reads identically to a 90 at a glance. Rounded up for the same
 * reason as the minutes. */
static int active_bars_for(int64_t remaining_ms, int64_t total_ms) {
    if (total_ms <= 0 || remaining_ms <= 0) {
        return 0;
    }

    int bars = (int)((remaining_ms * TIMER_BAR_COUNT + total_ms - 1) / total_ms);
    return (bars > TIMER_BAR_COUNT) ? TIMER_BAR_COUNT : bars;
}

static void timer_meter_render(int active_bars, int minutes) {
    struct zmk_widget_timer_meter *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        if (active_bars != prev_active_bars) {
            for (int i = 0; i < TIMER_BAR_COUNT; i++) {
                /* Single colour throughout — deliberately no green/amber/red
                 * transition. That would be a deadline signal, and a block is
                 * progress-defined: zero is a non-event. */
                lv_color_t color = (i < active_bars)
                    ? lv_color_hex(DISPLAY_COLOR_TIMER_BAR_ACTIVE)
                    : lv_color_hex(DISPLAY_COLOR_TIMER_BAR_SPENT);
                lv_obj_set_style_bg_color(widget->bars[i], color, LV_PART_MAIN);
            }
        }

        if (minutes != prev_minutes) {
            char text[6];
            snprintf(text, sizeof(text), "%d", minutes);
            lv_label_set_text(widget->minutes_label, text);
        }
    }

    prev_active_bars = active_bars;
    prev_minutes = minutes;
}

static void refresh(void) {
    struct zmk_block_timer_state state;
    zmk_block_timer_get(&state);

    int minutes = minutes_remaining(state.remaining_ms);
    int active_bars = active_bars_for(state.remaining_ms, state.total_ms);

    if (active_bars != prev_active_bars || minutes != prev_minutes) {
        timer_meter_render(active_bars, minutes);
    }

    /* Stop ticking once it reaches zero. Sitting at 0 with an empty bar is the
     * finished state and it is identical to the pre-start state — one quiet
     * state, not two. No flash, no inversion, no colour change. */
    if (state.running && state.remaining_ms > 0) {
        k_work_schedule(&timer_tick_work, K_SECONDS(1));
    }
}

static void timer_tick_work_handler(struct k_work *work) { refresh(); }

static void timer_meter_update_cb(struct timer_meter_state state) {
    k_work_cancel_delayable(&timer_tick_work);
    refresh();
}

static struct timer_meter_state timer_meter_get_state(const zmk_event_t *eh) {
    struct zmk_block_timer_state state;
    zmk_block_timer_get(&state);

    return (struct timer_meter_state){.running = state.running};
}

static void layer_update_cb(struct layer_state state) {
    struct zmk_widget_timer_meter *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        const char *layer_name = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(state.index));
        char display_name[32];

        if (layer_name && *layer_name) {
            snprintf(display_name, sizeof(display_name), "%s", layer_name);
        } else {
            snprintf(display_name, sizeof(display_name), "Layer %d", state.index);
        }

#if IS_ENABLED(CONFIG_PROSPECTOR_LAYER_NAME_UPPERCASE)
        for (int i = 0; display_name[i]; i++) {
            display_name[i] = toupper((unsigned char)display_name[i]);
        }
#endif

        lv_label_set_text(widget->layer_label, display_name);
    }
}

static struct layer_state layer_get_state(const zmk_event_t *eh) {
    return (struct layer_state){.index = zmk_keymap_highest_layer_active()};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_timer_meter, struct timer_meter_state,
                            timer_meter_update_cb, timer_meter_get_state)
ZMK_SUBSCRIPTION(widget_timer_meter, zmk_block_timer_state_changed);

ZMK_DISPLAY_WIDGET_LISTENER(widget_timer_meter_layer, struct layer_state,
                            layer_update_cb, layer_get_state)
ZMK_SUBSCRIPTION(widget_timer_meter_layer, zmk_layer_state_changed);

int zmk_widget_timer_meter_init(struct zmk_widget_timer_meter *widget, lv_obj_t *parent) {
    widget->obj = lv_obj_create(parent);
    lv_obj_set_size(widget->obj, 260, 90);
    lv_obj_set_style_bg_opa(widget->obj, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->obj, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(widget->obj, 0, LV_PART_MAIN);

    int bar_width = 8;
    int bar_gap = 2;
    int bar_height = 90;
    int total_width = TIMER_BAR_COUNT * bar_width + (TIMER_BAR_COUNT - 1) * bar_gap;
    int start_x = (260 - total_width) / 2;

    for (int i = 0; i < TIMER_BAR_COUNT; i++) {
        widget->bars[i] = lv_obj_create(widget->obj);
        lv_obj_set_size(widget->bars[i], bar_width, bar_height);
        lv_obj_set_pos(widget->bars[i], start_x + i * (bar_width + bar_gap), 0);
        lv_obj_set_style_bg_color(widget->bars[i], lv_color_hex(DISPLAY_COLOR_TIMER_BAR_SPENT), LV_PART_MAIN);
        lv_obj_set_style_bg_opa(widget->bars[i], LV_OPA_COVER, LV_PART_MAIN);
        lv_obj_set_style_border_width(widget->bars[i], 0, LV_PART_MAIN);
        lv_obj_set_style_radius(widget->bars[i], 1, LV_PART_MAIN);
        lv_obj_set_style_pad_all(widget->bars[i], 0, LV_PART_MAIN);
    }

    widget->minutes_label = lv_label_create(widget->obj);
    lv_label_set_text(widget->minutes_label, "0");
    lv_obj_set_style_text_font(widget->minutes_label, &FR_Medium_32, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->minutes_label, lv_color_hex(DISPLAY_COLOR_TIMER_TEXT), LV_PART_MAIN);
    lv_obj_set_style_bg_color(widget->minutes_label, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(widget->minutes_label, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_pad_hor(widget->minutes_label, 6, LV_PART_MAIN);
    lv_obj_set_style_pad_ver(widget->minutes_label, 4, LV_PART_MAIN);
    lv_obj_align(widget->minutes_label, LV_ALIGN_TOP_LEFT, -7, -9);

    widget->layer_label = lv_label_create(widget->obj);
    lv_label_set_text(widget->layer_label, "");
    lv_obj_set_style_text_font(widget->layer_label, &DINishExpanded_Light_36, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->layer_label, lv_color_hex(DISPLAY_COLOR_LAYER_TEXT), LV_PART_MAIN);
    lv_obj_set_style_bg_color(widget->layer_label, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(widget->layer_label, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_pad_hor(widget->layer_label, 8, LV_PART_MAIN);
    lv_obj_set_style_pad_top(widget->layer_label, 7, LV_PART_MAIN);
    lv_obj_set_style_pad_bottom(widget->layer_label, 3, LV_PART_MAIN);
    lv_obj_align(widget->layer_label, LV_ALIGN_BOTTOM_RIGHT, 9, 7);

    sys_slist_append(&widgets, &widget->node);
    widget_timer_meter_init();
    widget_timer_meter_layer_init();

    k_work_init_delayable(&timer_tick_work, timer_tick_work_handler);

    return 0;
}

lv_obj_t *zmk_widget_timer_meter_obj(struct zmk_widget_timer_meter *widget) {
    return widget->obj;
}

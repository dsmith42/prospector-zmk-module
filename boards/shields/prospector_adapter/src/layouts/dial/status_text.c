#include "status_text.h"

#include <zephyr/kernel.h>
#include <ctype.h>
#include <zmk/display.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/endpoints.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <zmk/ble.h>

#include <fonts.h>
#include <font_fallback.h>
#include <symbols.h>
#include "display_colors.h"

/* Below this the numeral turns red. Text colour only — no badge, no background,
 * no flash. Quiet by design; the trade is that it is easy to miss unless you
 * are already looking at that corner. */
#define BATTERY_LOW_PCT 15

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);

struct layer_state {
    uint8_t index;
};

struct mods_state {
    bool held[STATUS_MOD_COUNT];
};

struct profile_state {
    uint8_t index;
    bool usb;
};

struct battery_state {
    uint8_t source;
    uint8_t level;
};

static uint8_t battery_level[STATUS_PERIPHERAL_COUNT];

static void layer_update_cb(struct layer_state state) {
    struct zmk_widget_status_text *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        const char *name = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(state.index));
        /* Sized in bytes, not characters. A five character Japanese name is
         * fifteen bytes of UTF-8, and truncating one mid-sequence leaves a
         * partial codepoint that renders as a missing glyph rather than a
         * short name, so there is headroom here deliberately. */
        char display_name[32];

        if (name && *name) {
            snprintf(display_name, sizeof(display_name), "%s", name);
        } else {
            snprintf(display_name, sizeof(display_name), "L%d", state.index);
        }

#if IS_ENABLED(CONFIG_PROSPECTOR_LAYER_NAME_UPPERCASE)
        /* Bytewise, so skip anything with the high bit set: those are UTF-8
         * continuation and lead bytes, and passing them through toupper() is
         * locale dependent for values above 0x7F. Japanese has no case, so
         * there is nothing to convert anyway. */
        for (int i = 0; display_name[i]; i++) {
            unsigned char c = (unsigned char)display_name[i];

            if (c < 0x80) {
                display_name[i] = (char)toupper(c);
            }
        }
#endif

        lv_label_set_text(widget->layer_label, display_name);
    }
}

static struct layer_state layer_get_state(const zmk_event_t *eh) {
    return (struct layer_state){.index = zmk_keymap_highest_layer_active()};
}

static void mods_update_cb(struct mods_state state) {
    struct zmk_widget_status_text *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        for (int i = 0; i < STATUS_MOD_COUNT; i++) {
            lv_obj_set_style_text_color(
                widget->mods[i],
                lv_color_hex(state.held[i] ? DISPLAY_COLOR_MOD_ACTIVE : DISPLAY_COLOR_MOD_INACTIVE),
                LV_PART_MAIN);
        }
    }
}

static struct mods_state mods_get_state(const zmk_event_t *eh) {
    zmk_mod_flags_t mods = zmk_hid_get_explicit_mods();
    struct mods_state state = {0};

    /* GACS order, matching CONFIG_PROSPECTOR_MODIFIER_ORDER's default. */
    state.held[0] = (mods & (MOD_LGUI | MOD_RGUI)) != 0;
    state.held[1] = (mods & (MOD_LALT | MOD_RALT)) != 0;
    state.held[2] = (mods & (MOD_LCTL | MOD_RCTL)) != 0;
    state.held[3] = (mods & (MOD_LSFT | MOD_RSFT)) != 0;

    return state;
}

static void profile_update_cb(struct profile_state state) {
    struct zmk_widget_status_text *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        char text[6];
        if (state.usb) {
            snprintf(text, sizeof(text), "USB");
        } else {
            /* Spaced: "B 1" rather than "B1", which reads cramped at this size. */
            snprintf(text, sizeof(text), "B %d", state.index + 1);
        }
        lv_label_set_text(widget->profile_label, text);
    }
}

static struct profile_state profile_get_state(const zmk_event_t *eh) {
    struct zmk_endpoint_instance selected = zmk_endpoint_get_selected();

    return (struct profile_state){
        .index = zmk_ble_active_profile_index(),
        .usb = (selected.transport == ZMK_TRANSPORT_USB),
    };
}

static void battery_render(void) {
    struct zmk_widget_status_text *widget;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, widget, node) {
        for (int i = 0; i < STATUS_PERIPHERAL_COUNT; i++) {
            char text[5];
            snprintf(text, sizeof(text), "%d", battery_level[i]);
            lv_label_set_text(widget->battery[i], text);
            lv_obj_set_style_text_color(
                widget->battery[i],
                lv_color_hex(battery_level[i] < BATTERY_LOW_PCT ? DISPLAY_COLOR_BATTERY_LOW_TEXT
                                                                : DISPLAY_COLOR_BATTERY_FILL),
                LV_PART_MAIN);
        }
    }
}

static void battery_update_cb(struct battery_state state) {
    if (state.source < STATUS_PERIPHERAL_COUNT) {
        battery_level[state.source] = state.level;
    }
    battery_render();
}

static struct battery_state battery_get_state(const zmk_event_t *eh) {
    const struct zmk_peripheral_battery_state_changed *ev =
        as_zmk_peripheral_battery_state_changed(eh);
    if (ev == NULL) {
        return (struct battery_state){.source = 0xff, .level = 0};
    }

    return (struct battery_state){.source = ev->source, .level = ev->state_of_charge};
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_status_layer, struct layer_state, layer_update_cb, layer_get_state)
ZMK_SUBSCRIPTION(widget_status_layer, zmk_layer_state_changed);

ZMK_DISPLAY_WIDGET_LISTENER(widget_status_mods, struct mods_state, mods_update_cb, mods_get_state)
ZMK_SUBSCRIPTION(widget_status_mods, zmk_keycode_state_changed);

ZMK_DISPLAY_WIDGET_LISTENER(widget_status_profile, struct profile_state, profile_update_cb, profile_get_state)
ZMK_SUBSCRIPTION(widget_status_profile, zmk_ble_active_profile_changed);
ZMK_SUBSCRIPTION(widget_status_profile, zmk_endpoint_changed);

ZMK_DISPLAY_WIDGET_LISTENER(widget_status_battery, struct battery_state, battery_update_cb, battery_get_state)
ZMK_SUBSCRIPTION(widget_status_battery, zmk_peripheral_battery_state_changed);

static lv_obj_t *make_label(lv_obj_t *parent, const lv_font_t *font, uint32_t colour,
                            const char *text, lv_align_t align, int x, int y) {
    lv_obj_t *label = lv_label_create(parent);
    lv_label_set_text(label, text);
    lv_obj_set_style_text_font(label, font, LV_PART_MAIN);
    lv_obj_set_style_text_color(label, lv_color_hex(colour), LV_PART_MAIN);
    lv_obj_align(label, align, x, y);
    return label;
}

int zmk_widget_status_text_init(struct zmk_widget_status_text *widget, lv_obj_t *parent) {
    widget->obj = lv_obj_create(parent);
    lv_obj_set_size(widget->obj, 280, 240);
    lv_obj_set_style_bg_opa(widget->obj, LV_OPA_TRANSP, LV_PART_MAIN);
    lv_obj_set_style_border_width(widget->obj, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_all(widget->obj, 0, LV_PART_MAIN);

    /* Profile above the batteries; batteries side by side, position carrying
     * left/right so no L/R prefixes are needed. */
    widget->profile_label = make_label(widget->obj, &DINishCondensed_SemiBold_20,
                                       DISPLAY_COLOR_DIAL_PROFILE, "B 1",
                                       LV_ALIGN_TOP_RIGHT, -10, 154);

    static const int battery_x[STATUS_PERIPHERAL_COUNT] = {-46, -10};
    for (int i = 0; i < STATUS_PERIPHERAL_COUNT; i++) {
        widget->battery[i] = make_label(widget->obj, &DINish_Medium_24, DISPLAY_COLOR_BATTERY_FILL,
                                        "0", LV_ALIGN_TOP_RIGHT, battery_x[i], 184);
    }

    /* Bottom row: layer far left, modifiers far right on one baseline, so a
     * chord is scanned in a single movement. */
    /* Static because the label holds the pointer for the lifetime of the
     * screen; see font_fallback.h for why the wrapper is needed at all. */
    static lv_font_t layer_font;

    widget->layer_label = make_label(widget->obj, prospector_font_jp(&FG_Medium_20, &layer_font),
                                     DISPLAY_COLOR_MOD_ACTIVE, "", LV_ALIGN_BOTTOM_LEFT, 10, -6);

    /* Glyphs rather than CMD/OPT/CTL/SFT: a symbol is recognised without being
     * read, which is what the rest of this screen is built around. They are
     * also narrower, so the row tightens from a 40px pitch to 32px. */
    static const char *const mod_glyphs[STATUS_MOD_COUNT] = {
        SYMBOL_COMMAND, SYMBOL_OPTION, SYMBOL_CONTROL, SYMBOL_SHIFT};
    for (int i = 0; i < STATUS_MOD_COUNT; i++) {
        widget->mods[i] = make_label(widget->obj, &Symbols_Bold_26,
                                     DISPLAY_COLOR_MOD_INACTIVE, mod_glyphs[i],
                                     LV_ALIGN_BOTTOM_RIGHT,
                                     -10 - (STATUS_MOD_COUNT - 1 - i) * 32, -2);
    }

    sys_slist_append(&widgets, &widget->node);
    widget_status_layer_init();
    widget_status_mods_init();
    widget_status_profile_init();
    widget_status_battery_init();

    return 0;
}

lv_obj_t *zmk_widget_status_text_obj(struct zmk_widget_status_text *widget) { return widget->obj; }

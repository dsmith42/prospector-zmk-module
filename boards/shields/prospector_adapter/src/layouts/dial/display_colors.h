#pragma once

#include <zephyr/devicetree.h>

/*
 * Colours come from a theme node in devicetree, so a user picks one without
 * rebuilding or editing the module:
 *
 *   chosen { zmk,prospector-theme = &dial_teal_theme; };
 *
 * Six are defined in prospector_adapter.overlay. Every property has a default
 * in the binding, so a theme only needs to set what it changes — including
 * themes written for the RADII layout, which remain valid here.
 */

#if DT_HAS_CHOSEN(zmk_prospector_theme)
#define THEME_NODE DT_CHOSEN(zmk_prospector_theme)
#else
#define THEME_NODE DT_NODELABEL(dial_amber_theme)
#endif

/* Timer. One colour throughout as it depletes — no transition, because that
   would read as a deadline and a block is progress-defined. */
#define DISPLAY_COLOR_TIMER_BAR_ACTIVE DT_PROP(THEME_NODE, dial_wedge)

/* The hand and the armed preview are derived from the wedge in dial.c — see
   DIAL_HAND_LIFT and DIAL_ARMED_LEVEL. A theme sets its wedge and gets both. */

/* Three even steps: face (the whole hour) < block (the length chosen) <
   wedge (what remains). */
#define DISPLAY_COLOR_DIAL_FACE        DT_PROP(THEME_NODE, dial_face)
#define DISPLAY_COLOR_DIAL_BLOCK       DT_PROP(THEME_NODE, dial_block)

#define DISPLAY_COLOR_DIAL_TICK        DT_PROP(THEME_NODE, dial_tick)
#define DISPLAY_COLOR_DIAL_HUB         DT_PROP(THEME_NODE, dial_hub)
#define DISPLAY_COLOR_DIAL_MINUTES     DT_PROP(THEME_NODE, dial_minutes)
#define DISPLAY_COLOR_DIAL_PROFILE     DT_PROP(THEME_NODE, dial_profile)

/* Battery. Warning is text colour only — no badge, no flash. */
#define DISPLAY_COLOR_BATTERY_FILL     DT_PROP(THEME_NODE, dial_battery)
#define DISPLAY_COLOR_BATTERY_LOW_TEXT DT_PROP(THEME_NODE, dial_battery_low)

/* Layer and modifiers share the accent, so the diagnostics read as one family
   distinct from the timer. */
#define DISPLAY_COLOR_MOD_ACTIVE       DT_PROP(THEME_NODE, mod_active_color)
#define DISPLAY_COLOR_MOD_INACTIVE     DT_PROP(THEME_NODE, mod_inactive_color)

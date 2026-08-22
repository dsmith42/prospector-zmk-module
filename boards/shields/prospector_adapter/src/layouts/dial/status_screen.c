#include <lvgl.h>

#include "dial.h"
#include "status_text.h"

#include <fonts.h>

static struct zmk_widget_dial dial_widget;
static struct zmk_widget_status_text status_text_widget;

lv_obj_t *zmk_display_status_screen() {
    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x000000), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(screen, 255, LV_PART_MAIN);

    zmk_widget_dial_init(&dial_widget, screen);
    lv_obj_set_pos(zmk_widget_dial_obj(&dial_widget), 0, 0);

    zmk_widget_status_text_init(&status_text_widget, screen);
    lv_obj_set_pos(zmk_widget_status_text_obj(&status_text_widget), 0, 0);

    return screen;
}

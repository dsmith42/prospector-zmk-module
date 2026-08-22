#pragma once

#include <zephyr/kernel.h>
#include <zmk/event_manager.h>

struct zmk_block_timer_state_changed {
    bool running;
};

ZMK_EVENT_DECLARE(zmk_block_timer_state_changed);

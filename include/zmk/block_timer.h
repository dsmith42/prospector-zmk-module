/*
 * Focus-block timer state.
 *
 * Stores an absolute deadline rather than a decrementing counter, so remaining
 * time is a pure function of the monotonic uptime clock. Nothing that happens
 * to the display can affect it: hide the widget, stop ticking it, come back
 * twenty minutes later and it still reads correctly, with no drift and no
 * save/restore. Do not reintroduce a ticking countdown.
 */

#pragma once

#include <zephyr/kernel.h>

struct zmk_block_timer_state {
    bool running;
    int64_t remaining_ms;
    int64_t total_ms;
    uint16_t armed_minutes;   /* what BLK_START would begin */
};

/* Select the length a later start will use. Ignored while running. */
void zmk_block_timer_arm(uint16_t minutes);

/* Start the armed length. Ignored while running — stop it first. */
void zmk_block_timer_start_armed(void);

/* Start a block of the given length directly. Ignored while running. */
void zmk_block_timer_start(uint16_t minutes);

/* Stop and clear. */
void zmk_block_timer_stop(void);

/* Current state, recomputed from uptime at call time. */
void zmk_block_timer_get(struct zmk_block_timer_state *out);

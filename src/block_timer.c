#include <zephyr/kernel.h>

#include <zmk/block_timer.h>
#include <zmk/event_manager.h>
#include <zmk/events/block_timer_state_changed.h>

static int64_t deadline_ms;
static int64_t total_ms;
static bool running;

static void raise_changed(void) {
    raise_zmk_block_timer_state_changed(
        (struct zmk_block_timer_state_changed){.running = running});
}

void zmk_block_timer_start(uint16_t minutes) {
    if (minutes == 0) {
        zmk_block_timer_stop();
        return;
    }

    /* A running block is locked: starts are ignored until it is stopped
     * deliberately or reaches zero. Elapsed time is the one piece of state the
     * system cares about, and a stray keypress must not be able to discard it.
     * Switching length mid-block is therefore two deliberate acts — stop, then
     * start — which is the intent. */
    if (running && (deadline_ms - k_uptime_get()) > 0) {
        return;
    }

    total_ms = (int64_t)minutes * 60 * 1000;
    deadline_ms = k_uptime_get() + total_ms;
    running = true;

    raise_changed();
}

void zmk_block_timer_stop(void) {
    running = false;
    total_ms = 0;
    deadline_ms = 0;

    raise_changed();
}

void zmk_block_timer_get(struct zmk_block_timer_state *out) {
    out->running = running;
    out->total_ms = total_ms;

    if (!running) {
        out->remaining_ms = 0;
        return;
    }

    int64_t remaining = deadline_ms - k_uptime_get();
    out->remaining_ms = (remaining > 0) ? remaining : 0;
}

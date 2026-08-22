/*
 * Runtime display brightness.
 *
 * Only meaningful with the ambient light sensor disabled — with it enabled the
 * sensor owns the backlight and stepping is a no-op.
 */

#pragma once

/* Adjust by delta percent, clamped to 5..100. */
void prospector_brightness_step(int delta);

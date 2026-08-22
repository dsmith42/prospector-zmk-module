/*
 * Parameter values for the zmk,behavior-block-timer behaviour.
 *
 *   BLK_STOP        stop and clear a running block
 *   BLK_START       start the armed length
 *   1..999          arm that many minutes (does not start)
 *
 * Arming and starting are both ignored while a block is running: changing
 * length mid-block is stop, arm, start — three deliberate acts.
 */

#pragma once

#define BLK_STOP 0
#define BLK_START 1000

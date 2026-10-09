/*
 * TOUCAN_STATUS_SCREEN=3: the nice-view-gem v0.3.0 central screen
 * (github.com/M165437/nice-view-gem, MIT, (c) 2024 Michael Schmidt-Voigt)
 * redrawn on the Toucan's 144x168 portrait panel.
 *
 * Gem draws a 68x160 portrait strip in three rotated 68x68 tiles for the
 * landscape nice!view. This panel is natively portrait and big enough for the
 * whole strip, so every widget keeps gem's own coordinates and pixel art,
 * just shifted by (OX, OY) to centre the strip. Only change from gem: the
 * single BAT row became L/R rows, since this screen also shows the right half.
 */

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zmk/keymap.h>

#include "battery.h"
#include "battery_peripheral.h"
#include "chart.h"
#include "layer.h"
#include "output.h"
#include "profile.h"

LV_FONT_DECLARE(pixel_operator_mono);

LV_IMG_DECLARE(gem_bolt);
LV_IMG_DECLARE(gem_bt);
LV_IMG_DECLARE(gem_bt_no_signal);
LV_IMG_DECLARE(gem_bt_unbonded);
LV_IMG_DECLARE(gem_usb);
LV_IMG_DECLARE(gem_gauge);
LV_IMG_DECLARE(gem_grid);
LV_IMG_DECLARE(gem_profiles);

#define STRIP_W 68
#define OX ((SCREEN_WIDTH - STRIP_W) / 2)
#define OY 4

// toucan.dtsi turns layer 4 on while a finger is on the trackpad; showing it
// would flash "MOU" on every touch, so the label skips it.
#define TOUCH_LAYER 4

#define WPM_MAX 100

static void text(lv_obj_t *canvas, int x, int y, int w, lv_text_align_t align, const char *str) {
    lv_draw_label_dsc_t dsc;
    init_label_dsc(&dsc, LVGL_FOREGROUND, &pixel_operator_mono, align);
    lv_canvas_draw_text(canvas, OX + x, OY + y, w, &dsc, str);
}

static void img(lv_obj_t *canvas, int x, int y, const lv_img_dsc_t *src) {
    lv_draw_img_dsc_t dsc;
    lv_draw_img_dsc_init(&dsc);
    lv_canvas_draw_img(canvas, OX + x, OY + y, src, &dsc);
}

static void rect(lv_obj_t *canvas, int x, int y, int w, int h) {
    lv_draw_rect_dsc_t dsc;
    init_rect_dsc(&dsc, LVGL_FOREGROUND);
    lv_canvas_draw_rect(canvas, OX + x, OY + y, w, h, &dsc);
}

/* SIG row: connection symbol in a filled box */
void draw_output_status(lv_obj_t *canvas, const struct status_state *state) {
    text(canvas, 0, 1, 25, LV_TEXT_ALIGN_LEFT, "SIG");
    rect(canvas, 43, 0, 24, 15);

    switch (state->selected_endpoint.transport) {
    case ZMK_TRANSPORT_USB:
        img(canvas, 45, 2, &gem_usb);
        break;
    case ZMK_TRANSPORT_BLE:
        if (!state->active_profile_bonded) {
            img(canvas, 44, 0, &gem_bt_unbonded);
        } else if (state->active_profile_connected) {
            img(canvas, 49, 0, &gem_bt);
        } else {
            img(canvas, 49, 0, &gem_bt_no_signal);
        }
        break;
    }
}

static void battery_row(lv_obj_t *canvas, int y, const char *label, uint8_t level, bool charging) {
    char value[8];
    text(canvas, 0, y, 25, LV_TEXT_ALIGN_LEFT, label);
    if (level == 0) {
        snprintf(value, sizeof(value), "--");
    } else {
        snprintf(value, sizeof(value), "%u%%", level);
    }
    if (charging) {
        text(canvas, 26, y, 35, LV_TEXT_ALIGN_RIGHT, value);
        img(canvas, 62, y + 2, &gem_bolt);
    } else {
        text(canvas, 26, y, 42, LV_TEXT_ALIGN_RIGHT, value);
    }
}

void draw_battery_status(lv_obj_t *canvas, const struct status_state *state) {
    battery_row(canvas, 17, "L", state->battery, state->charging);
}

void draw_battery_peripheral_status(lv_obj_t *canvas, const struct status_state *state) {
    // charging_p only mirrors the left half's USB state, so no bolt here.
    battery_row(canvas, 30, "R", state->battery_p, false);
}

/* WPM: needle gauge, grid, 10-sample line graph, number */
static uint8_t wpm_hist[10];
static uint8_t wpm_last;

void draw_chart_status(lv_obj_t *canvas, const struct status_state *state) {
    if (state->wpm != wpm_last) {
        memmove(wpm_hist, wpm_hist + 1, sizeof(wpm_hist) - 1);
        wpm_hist[9] = state->wpm;
        wpm_last = state->wpm;
    }

    img(canvas, 16, 44, &gem_gauge);

    lv_draw_line_dsc_t line;
    init_line_dsc(&line, LVGL_FOREGROUND, 1);
    int value = wpm_hist[9] > WPM_MAX ? WPM_MAX : wpm_hist[9];
    float angle = (225 + (float)value / WPM_MAX * 90) * (3.14159f / 180.0f);
    lv_point_t needle[2] = {
        {OX + 33 + (int)(13 * cosf(angle)), OY + 67 + (int)(13 * sinf(angle))},
        {OX + 33 + (int)(25.45585f * cosf(angle)), OY + 67 + (int)(25.45585f * sinf(angle))},
    };
    lv_canvas_draw_line(canvas, needle, 2, &line);

    img(canvas, 0, 65, &gem_grid);

    init_line_dsc(&line, LVGL_FOREGROUND, 2);
    lv_point_t graph[10];
    for (int i = 0; i < 10; i++) {
        int v = wpm_hist[i] > WPM_MAX ? WPM_MAX : wpm_hist[i];
        graph[i].x = OX + (lv_coord_t)(i * 7.4f);
        graph[i].y = OY + 97 - v * 32 / WPM_MAX;
    }
    lv_canvas_draw_line(canvas, graph, 10, &line);

    char wpm_text[6];
    snprintf(wpm_text, sizeof(wpm_text), "%d", wpm_hist[9]);
    text(canvas, 0, 101, 25, LV_TEXT_ALIGN_LEFT, "WPM");
    text(canvas, 26, 101, 42, LV_TEXT_ALIGN_RIGHT, wpm_text);
}

/* Five profile slots, active one filled */
void draw_profile_status(lv_obj_t *canvas, const struct status_state *state) {
    img(canvas, 18, 129, &gem_profiles);
    rect(canvas, 18 + state->active_profile_index * 7, 129, 3, 3);
}

/* Layer name, upper-cased, max 9 chars */
void draw_layer_status(lv_obj_t *canvas, const struct status_state *state) {
    zmk_keymap_layer_index_t index = state->layer_index;
    if (index == TOUCH_LAYER) {
        while (index > 0) {
            index--;
            if (index != TOUCH_LAYER && zmk_keymap_layer_active(zmk_keymap_layer_index_to_id(index))) {
                break;
            }
        }
    }

    char name[10] = {};
    const char *label = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(index));
    if (label == NULL || label[0] == '\0') {
        snprintf(name, sizeof(name), "Layer %u", index);
    } else {
        strncpy(name, label, sizeof(name) - 1);
        to_uppercase(name);
    }
    text(canvas, 0, 146, STRIP_W, LV_TEXT_ALIGN_CENTER, name);
}

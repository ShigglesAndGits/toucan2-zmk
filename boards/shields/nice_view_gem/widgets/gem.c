/*
 * TOUCAN_STATUS_SCREEN=3: the nice-view-gem v0.3.0 central screen
 * (github.com/M165437/nice-view-gem, MIT, (c) 2024 Michael Schmidt-Voigt)
 * re-laid out to fill the Toucan's 144x168 portrait panel.
 *
 * Gem's 68x160 strip can't simply be doubled (it would be 320 tall), so the
 * same widgets are rearranged: full-width SIG and L/R battery rows, the needle
 * gauge at 2x beside a big WPM number, a full-width dotted grid for the WPM
 * graph, then the profile dots (2x) and the layer name. Gem's pixel art is
 * reused, scaled only by whole numbers so it stays crisp.
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
LV_FONT_DECLARE(quinquefive_18);
LV_FONT_DECLARE(quinquefive_24);

LV_IMG_DECLARE(gem_bolt);
LV_IMG_DECLARE(gem_bt);
LV_IMG_DECLARE(gem_bt_no_signal);
LV_IMG_DECLARE(gem_bt_unbonded);
LV_IMG_DECLARE(gem_usb);
LV_IMG_DECLARE(gem_gauge);
LV_IMG_DECLARE(gem_profiles);

// toucan.dtsi turns layer 4 on while a finger is on the trackpad; showing it
// would flash "MOU" on every touch, so the label skips it.
#define TOUCH_LAYER 4

#define WPM_MAX 100
#define MARGIN 4

// Vertical layout
#define ROW_SIG_Y 1
#define ROW_BAT_Y 20
#define GAUGE_Y 38
#define GRID_Y 88
#define GRID_H 37
#define PROFILES_Y 131
#define LAYER_Y 146

static void text(lv_obj_t *canvas, const lv_font_t *font, int x, int y, int w,
                 lv_text_align_t align, const char *str) {
    lv_draw_label_dsc_t dsc;
    init_label_dsc(&dsc, LVGL_FOREGROUND, font, align);
    lv_canvas_draw_text(canvas, x, y, w, &dsc, str);
}

static void img(lv_obj_t *canvas, int x, int y, const lv_img_dsc_t *src) {
    lv_draw_img_dsc_t dsc;
    lv_draw_img_dsc_init(&dsc);
    lv_canvas_draw_img(canvas, x, y, src, &dsc);
}

// Integer-scaled blit of gem's 1-bit art (LVGL's zoom smears 1-bit images).
// Index 1 is the "ink" colour in both gem palettes, so it maps to foreground.
static void img_scaled(lv_obj_t *canvas, int x, int y, const lv_img_dsc_t *src, int scale) {
    const uint8_t *bits = src->data + 8; // skip the 2-entry palette
    int w = src->header.w, h = src->header.h, stride = (w + 7) / 8;
    for (int row = 0; row < h; row++) {
        for (int col = 0; col < w; col++) {
            if (!(bits[row * stride + col / 8] & (0x80 >> (col % 8)))) {
                continue;
            }
            for (int dy = 0; dy < scale; dy++) {
                for (int dx = 0; dx < scale; dx++) {
                    lv_canvas_set_px_color(canvas, x + col * scale + dx, y + row * scale + dy,
                                           LVGL_FOREGROUND);
                }
            }
        }
    }
}

static void rect(lv_obj_t *canvas, int x, int y, int w, int h) {
    lv_draw_rect_dsc_t dsc;
    init_rect_dsc(&dsc, LVGL_FOREGROUND);
    lv_canvas_draw_rect(canvas, x, y, w, h, &dsc);
}

/* SIG row: connection symbol in a filled box at the right edge */
void draw_output_status(lv_obj_t *canvas, const struct status_state *state) {
    const int box_x = SCREEN_WIDTH - MARGIN - 24;
    text(canvas, &pixel_operator_mono, MARGIN, ROW_SIG_Y, 40, LV_TEXT_ALIGN_LEFT, "SIG");
    rect(canvas, box_x, ROW_SIG_Y - 1, 24, 15);

    switch (state->selected_endpoint.transport) {
    case ZMK_TRANSPORT_USB:
        img(canvas, box_x + 2, ROW_SIG_Y + 1, &gem_usb);
        break;
    case ZMK_TRANSPORT_BLE:
        if (!state->active_profile_bonded) {
            img(canvas, box_x + 1, ROW_SIG_Y - 1, &gem_bt_unbonded);
        } else if (state->active_profile_connected) {
            img(canvas, box_x + 6, ROW_SIG_Y - 1, &gem_bt);
        } else {
            img(canvas, box_x + 6, ROW_SIG_Y - 1, &gem_bt_no_signal);
        }
        break;
    }
}

/* L | R battery, each half: label left, value right */
static void battery_half(lv_obj_t *canvas, int x0, const char *label, uint8_t level,
                         bool charging) {
    const int half = SCREEN_WIDTH / 2 - MARGIN - 4;
    char value[8];
    if (level == 0) {
        snprintf(value, sizeof(value), "--");
    } else {
        snprintf(value, sizeof(value), "%u%%", level);
    }
    text(canvas, &pixel_operator_mono, x0, ROW_BAT_Y, 12, LV_TEXT_ALIGN_LEFT, label);
    if (charging) {
        text(canvas, &pixel_operator_mono, x0 + 10, ROW_BAT_Y, half - 17, LV_TEXT_ALIGN_RIGHT, value);
        img(canvas, x0 + half - 5, ROW_BAT_Y + 2, &gem_bolt);
    } else {
        text(canvas, &pixel_operator_mono, x0 + 10, ROW_BAT_Y, half - 10, LV_TEXT_ALIGN_RIGHT, value);
    }
}

void draw_battery_status(lv_obj_t *canvas, const struct status_state *state) {
    battery_half(canvas, MARGIN, "L", state->battery, state->charging);
}

void draw_battery_peripheral_status(lv_obj_t *canvas, const struct status_state *state) {
    // charging_p only mirrors the left half's USB state, so no bolt here.
    battery_half(canvas, SCREEN_WIDTH / 2 + 4, "R", state->battery_p, false);
    for (int y = ROW_BAT_Y; y < ROW_BAT_Y + 13; y += 2) { // dotted L | R divider
        lv_canvas_set_px_color(canvas, SCREEN_WIDTH / 2, y, LVGL_FOREGROUND);
    }
}

/* Gem's dotted grid, drawn to size: dotted rows, sparser dotted columns */
static void dotted_grid(lv_obj_t *canvas, int x0, int y0, int w, int h, int cols, int rows) {
    for (int r = 0; r <= rows; r++) {
        int y = y0 + r * (h - 1) / rows;
        for (int x = x0; x < x0 + w; x += 2) {
            lv_canvas_set_px_color(canvas, x, y, LVGL_FOREGROUND);
        }
    }
    for (int c = 0; c <= cols; c++) {
        int x = x0 + c * (w - 1) / cols;
        for (int y = y0; y < y0 + h; y += 3) {
            lv_canvas_set_px_color(canvas, x, y, LVGL_FOREGROUND);
        }
    }
}

/* WPM: 2x needle gauge + big number, full-width graph */
static uint8_t wpm_hist[10];
static uint8_t wpm_last;

void draw_chart_status(lv_obj_t *canvas, const struct status_state *state) {
    if (state->wpm != wpm_last) {
        memmove(wpm_hist, wpm_hist + 1, sizeof(wpm_hist) - 1);
        wpm_hist[9] = state->wpm;
        wpm_last = state->wpm;
    }
    int value = wpm_hist[9] > WPM_MAX ? WPM_MAX : wpm_hist[9];

    // Gem: gauge image at (16,44), needle pivot (33,67) -> pivot is 17px right
    // and 23px below the image corner; everything doubles here.
    const int gauge_x = MARGIN + 2;
    img_scaled(canvas, gauge_x, GAUGE_Y, &gem_gauge, 2);
    lv_draw_line_dsc_t line;
    init_line_dsc(&line, LVGL_FOREGROUND, 2);
    float angle = (225 + (float)value / WPM_MAX * 90) * (3.14159f / 180.0f);
    int px = gauge_x + 34, py = GAUGE_Y + 46;
    lv_point_t needle[2] = {
        {px + (int)(26 * cosf(angle)), py + (int)(26 * sinf(angle))},
        {px + (int)(51 * cosf(angle)), py + (int)(51 * sinf(angle))},
    };
    lv_canvas_draw_line(canvas, needle, 2, &line);

    char wpm_text[6];
    snprintf(wpm_text, sizeof(wpm_text), "%d", wpm_hist[9]);
    const int col_x = SCREEN_WIDTH / 2 + 4, col_w = SCREEN_WIDTH / 2 - MARGIN - 4;
    text(canvas, &pixel_operator_mono, col_x, GAUGE_Y + 4, col_w, LV_TEXT_ALIGN_RIGHT, "WPM");
    text(canvas, &quinquefive_24, col_x, GAUGE_Y + 22, col_w, LV_TEXT_ALIGN_RIGHT, wpm_text);

    const int grid_x = MARGIN, grid_w = SCREEN_WIDTH - 2 * MARGIN;
    dotted_grid(canvas, grid_x, GRID_Y, grid_w, GRID_H, 6, 3);

    init_line_dsc(&line, LVGL_FOREGROUND, 2);
    lv_point_t graph[10];
    for (int i = 0; i < 10; i++) {
        int v = wpm_hist[i] > WPM_MAX ? WPM_MAX : wpm_hist[i];
        graph[i].x = grid_x + i * (grid_w - 1) / 9;
        graph[i].y = GRID_Y + (GRID_H - 1) - v * (GRID_H - 1) / WPM_MAX;
    }
    lv_canvas_draw_line(canvas, graph, 10, &line);
}

/* Five profile slots (2x), active one filled */
void draw_profile_status(lv_obj_t *canvas, const struct status_state *state) {
    const int x = (SCREEN_WIDTH - 62) / 2;
    img_scaled(canvas, x, PROFILES_Y, &gem_profiles, 2);
    rect(canvas, x + state->active_profile_index * 14, PROFILES_Y, 6, 6);
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
    text(canvas, &quinquefive_18, 0, LAYER_Y, SCREEN_WIDTH, LV_TEXT_ALIGN_CENTER, name);
}

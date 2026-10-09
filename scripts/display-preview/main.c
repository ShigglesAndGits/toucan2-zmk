#include <stdio.h>
#include <string.h>
#include "lvgl.h"
#include "util.h"
#include "battery.h"
#include "battery_peripheral.h"
#include "chart.h"
#include "layer.h"
#include "output.h"
#include "profile.h"
#include <zmk/keymap.h>

static const char *names[] = {"BASE", "LOWER", "RAISE", "WORK", "MOU", "SYSTEM"};
static uint32_t active_mask = 1;
zmk_keymap_layer_id_t zmk_keymap_layer_index_to_id(zmk_keymap_layer_index_t i) { return i; }
bool zmk_keymap_layer_active(zmk_keymap_layer_id_t l) { return active_mask & (1u << l); }
const char *zmk_keymap_layer_name(zmk_keymap_layer_id_t l) { return l < 6 ? names[l] : NULL; }

static void flush(lv_disp_drv_t *d, const lv_area_t *a, lv_color_t *c) { lv_disp_flush_ready(d); }
static lv_color_t cbuf[SCREEN_WIDTH * SCREEN_HEIGHT];

static void dump(const char *path) {
    FILE *f = fopen(path, "wb");
    fprintf(f, "P5\n%d %d\n255\n", SCREEN_WIDTH, SCREEN_HEIGHT);
    for (int i = 0; i < SCREEN_WIDTH * SCREEN_HEIGHT; i++) fputc(cbuf[i].full ? 255 : 0, f);
    fclose(f);
}

int main(void) {
    lv_init();
    static lv_disp_draw_buf_t db; static lv_color_t b1[SCREEN_WIDTH * 20];
    lv_disp_draw_buf_init(&db, b1, NULL, SCREEN_WIDTH * 20);
    static lv_disp_drv_t dd; lv_disp_drv_init(&dd);
    dd.hor_res = SCREEN_WIDTH; dd.ver_res = SCREEN_HEIGHT; dd.flush_cb = flush; dd.draw_buf = &db;
    lv_disp_drv_register(&dd);
    lv_obj_t *canvas = lv_canvas_create(lv_scr_act());
    lv_canvas_set_buffer(canvas, cbuf, SCREEN_WIDTH, SCREEN_HEIGHT, LV_IMG_CF_TRUE_COLOR);

    struct status_state s = {0};
    int wpm_seq[] = {0, 20, 35, 48, 60, 55, 72, 80, 66, 74};
    struct { const char *file; int transport, bonded, connected, profile, layer; uint32_t mask; int bl, br, chg, wpm_n; } scenes[] = {
        {"s1.pgm", ZMK_TRANSPORT_BLE, 1, 1, 0, 0, 1, 85, 72, 0, 10},
        {"s2.pgm", ZMK_TRANSPORT_BLE, 1, 0, 2, 4, 1 | 4 | 16, 41, 0, 0, 4},   /* touching pad while RAISE held */
        {"s3.pgm", ZMK_TRANSPORT_USB, 1, 1, 1, 5, 1 | 2 | 4 | 32, 100, 99, 1, 10},
    };
    for (int k = 0; k < 3; k++) {
        memset(&s, 0, sizeof(s));
        s.selected_endpoint.transport = scenes[k].transport;
        s.active_profile_bonded = scenes[k].bonded; s.active_profile_connected = scenes[k].connected;
        s.active_profile_index = scenes[k].profile; s.layer_index = scenes[k].layer; active_mask = scenes[k].mask;
        s.battery = scenes[k].bl; s.battery_p = scenes[k].br; s.charging = scenes[k].chg;
        fill_background(canvas);
        for (int i = 0; i < scenes[k].wpm_n; i++) { s.wpm = wpm_seq[i]; if (i < scenes[k].wpm_n - 1) draw_chart_status(canvas, &s); }
        fill_background(canvas);
        draw_output_status(canvas, &s); draw_chart_status(canvas, &s); draw_layer_status(canvas, &s);
        draw_profile_status(canvas, &s); draw_battery_status(canvas, &s); draw_battery_peripheral_status(canvas, &s);
        dump(scenes[k].file);
    }
    return 0;
}

#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t zmk_keymap_layer_id_t;
typedef uint8_t zmk_keymap_layer_index_t;
zmk_keymap_layer_id_t zmk_keymap_layer_index_to_id(zmk_keymap_layer_index_t i);
bool zmk_keymap_layer_active(zmk_keymap_layer_id_t l);
const char *zmk_keymap_layer_name(zmk_keymap_layer_id_t l);

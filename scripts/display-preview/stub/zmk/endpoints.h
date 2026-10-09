#pragma once
#include <stdint.h>
enum zmk_transport { ZMK_TRANSPORT_USB, ZMK_TRANSPORT_BLE };
struct zmk_endpoint_instance { enum zmk_transport transport; union { struct { uint8_t profile_index; } ble; }; };

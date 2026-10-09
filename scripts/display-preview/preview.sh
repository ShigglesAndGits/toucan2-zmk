#!/usr/bin/env bash
# Render the style-3 (nice-view-gem) status screen on the desktop with the real
# LVGL 8.3 + widgets/gem.c, for checking layout changes without flashing.
#   scripts/display-preview/preview.sh   ->  display-preview.png in the repo root
# Needs the LVGL source from a local west workspace (default ~/.cache/toucan-west).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd)
lvgl=${LVGL:-$HOME/.cache/toucan-west/modules/lib/gui/lvgl}
mod=$root/boards/shields/nice_view_gem
out=$(mktemp -d); trap 'rm -rf "$out"' EXIT
mapfile -t srcs < <(find "$lvgl/src" -name '*.c' | grep -vE '/(sdl|gpu|nxp|arm2d|swm341|stm32)')
gcc -O1 -w -include "$here/stub/zephyr/kernel.h" -DLV_CONF_INCLUDE_SIMPLE \
  -DCONFIG_ZMK_SPLIT=1 -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=1 -DCONFIG_NICE_VIEW_WIDGET_INVERTED=0 \
  -DCONFIG_TOUCAN_STATUS_SCREEN=3 -DCONFIG_USB_DEVICE_STACK=1 \
  -I"$here" -I"$here/stub" -I"$lvgl" -I"$mod/widgets" -o "$out/harness" "$here/main.c" \
  "$mod/widgets/gem.c" "$mod/widgets/util.c" "$mod/assets/gem_images.c" \
  "$mod/assets/pixel_operator_mono.c" "${srcs[@]}" -lm 2> >(grep -v 'pragma message\|lv_conf_internal\|^ *[0-9]* |' >&2)
(cd "$out" && ./harness) && python3 -I "$here/compose.py" "$root/display-preview.png" "$out"/s1.pgm "$out"/s2.pgm "$out"/s3.pgm
echo "wrote $root/display-preview.png"

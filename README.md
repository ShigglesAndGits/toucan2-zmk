# ZMK config for beekeeb Toucan2 Keyboard

Alex's fork of [beekeeb/zmk-keyboard-toucan2](https://github.com/beekeeb/zmk-keyboard-toucan2)
(remote `upstream`), with the keymap ported from
[sofle-hybrid-ergomech](https://github.com/ShigglesAndGits/sofle-hybrid-ergomech).
Only `config/toucan.keymap` differs from upstream so far.

## Reference sheet

Live at **https://keymap.home.bironfamily.net** (LAN). `reference.html` is an
interactive page generated from the keymap: layer tabs on the real key geometry,
type a key to see where it lives, search, common actions, every symbol, and all
layers at a glance. Every "how do I reach it" answer is computed from
`config/toucan.keymap`, and the generator fails if a hand-written action points at
a binding that has moved.

After editing the keymap, run `scripts/deploy-site.sh`. It regenerates the page
(`scripts/reference.py` + `scripts/reference.template.html`), smoke-tests it in
headless Chromium (`scripts/check-site.mjs`, no npm needed) and publishes it.
Open copies reload themselves once the new version is up. `scripts/reference.py`
alone just rebuilds the local `reference.html`.

## Display

The left half's screen uses style 3 (`CONFIG_TOUCAN_STATUS_SCREEN` in
`boards/shields/toucan/toucan_left.conf`): nice-view-gem's central layout from
the Sofle, in `boards/shields/nice_view_gem/widgets/gem.c`. Preview layout
changes without flashing via `scripts/display-preview/preview.sh`.

## Flashing

0. Shortcut: `scripts/flash-when-ready.sh "firmware/<file>.uf2"` waits for the
   XIAO drive and copies the file for you (run once per half).
1. Push; GitHub Actions builds the firmware. Download the `firmware` artifact
   from the run and unzip it.
2. Plug the **left** half in with a data USB-C cable and put it in bootloader
   mode: hold RAISE + the left Space thumb (SYSTEM) and press the bottom-left
   key (BOOT). Without working firmware, double-tap the RST button on the XIAO
   instead (beside the USB-C port; support the acrylic plate while pressing).
   A drive named `XIAO...` mounts.
3. Copy `toucan_left rgbled_adapter nice_view_gem-seeeduino_xiao_ble-zmk.uf2`
   onto it. It reboots by itself after ~5-10 s, so ignore any "not ejected
   properly" warning.
4. Repeat with the **right** half and the `toucan_right ...` file; its BOOT
   key is SYSTEM + the bottom-right key.
5. The halves stay paired. Use `settings_reset` only if they stop finding
   each other: flash it to both halves, then the real firmware again.

Keymap edits saved through ZMK Studio override the flashed keymap until you
choose "Restore stock settings" in Studio.

## Upstream notes

[The beekeeb Toucan2 Keyboard](https://beekeeb.com/introducing-toucan2/) is a wireless split 42-key column‑stagger keyboard that a display and a trackpad, with an aggressive stagger on the pinky columns.

# Customizations

- **Keymap**: [config/toucan.keymap](config/toucan.keymap)
- **General configs**: [boards/shields/toucan/toucan_left.conf](boards/shields/toucan/toucan_left.conf) and [boards/shields/toucan/toucan_right.conf](boards/shields/toucan/toucan_right.conf)
- **Swipe shortcuts**: the `swipe_button_mapper` node in [boards/shields/toucan/toucan.dtsi](boards/shields/toucan/toucan.dtsi)
- **Invert scroll / trackpad settings**: the `tps43_trackpad` node in [boards/shields/toucan/toucan_right.overlay](boards/shields/toucan/toucan_right.overlay)

# License

The code in this repo is available under the MIT license.

The included shield nice_view_gem is modified from https://github.com/M165437/nice-view-gem licensed under the MIT License.

The linked trackpad module is based on https://github.com/geeksville/zmk_driver_azoteq

ZMK code snippets are taken from the ZMK documentation under the MIT license.

The embedded font QuinqueFive is designed by GGBotNet, licensed under under the SIL Open Font License, Version 1.1.

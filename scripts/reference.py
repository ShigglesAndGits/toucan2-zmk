#!/usr/bin/env python3
"""Render reference.html (all layers on the real Toucan 2 geometry) from the keymap.

    scripts/reference.py            # writes reference.html next to the repo root

Needs keymap-drawer (`pipx install keymap-drawer`) for parsing; the physical
key positions come straight from boards/shields/toucan/toucan.dtsi.
"""
import html
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DTSI = ROOT / "boards/shields/toucan/toucan.dtsi"
KEYMAP = ROOT / "config/toucan.keymap"
OUT = ROOT / "reference.html"

# How each layer is reached, shown under its title.
REACH = {
    "BASE": "default",
    "LOWER": "hold right outer thumb",
    "RAISE": "hold right inner thumb",
    "WORK": "double-tap + hold right inner thumb",
    "MOU": "automatic while a finger is on the trackpad",
    "SYSTEM": "hold RAISE + left centre (Space) thumb",
    "GAME": "LOWER + Esc corner (also jumps to Play) &middot; leave: hold corner + left outer thumb",
    "NUM": "in GAME: hold the Esc corner",
}

NOTES = [
    ("Thumbs", "left: GUI &middot; Space &middot; Ctrl &nbsp;|&nbsp; right: RAISE &middot; Enter &middot; LOWER"),
    ("Esc / Alt", "tap for Esc, hold (200ms) for Alt"),
    ("Alt+Tab", "RAISE + Tab"),
    ("Del", "RAISE + Backspace"),
    ("Super+arrows", "RAISE + M , . / (column focus)"),
    ("Ctrl+Alt+Del", "WORK &rarr; C-A-Del &middot; sticky Ctrl+Alt also on WORK"),
    ("Profiles", "BT 0&ndash;4 on LOWER bottom-left &middot; BT Clr on SYSTEM"),
    ("Output", "Out BLE / USB / Tog on SYSTEM (persists in flash)"),
    ("Gestures", "3-finger swipe = Super+arrow (column focus) &middot; pinch = Ctrl+−/= zoom"),
    ("Gaming", "LOWER + Esc corner = GAME + Play workspace &middot; corner + outer thumb = back to BASE + workspace 1"),
    ("Trackpad", "scrolls on RAISE &middot; while touching: S/D/F = R/M/L click, W/R = back/fwd"),
]

PRETTY = {
    "BACKSPACE": "⌫", "DEL": "Del", "ENTER": "⏎", "SPACE": "Space", "ESC": "Esc",
    "TAB": "Tab", "INS": "Ins", "HOME": "Home", "END": "End", "PG UP": "PgUp",
    "PG DN": "PgDn", "LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓",
    "LSHIFT": "⇧ Shift", "RSHIFT": "⇧ Shift", "LCTRL": "Ctrl", "LALT": "Alt",
    "LGUI": "◆ Super", "MUTE": "Mute", "VOL DN": "Vol−", "VOL UP": "Vol+",
    "PP": "⏯", "PAUSE BREAK": "Pause", "KP NUM": "NumLk", "BT CLR": "BT Clr",
    "OUT BLE": "Out BLE", "OUT USB": "Out USB", "OUT TOG": "Out Tog",
    "Ctl+C": "Copy", "Ctl+Sft+V": "Paste ⇧", "Ctl+LALT": "sC+A",
    "Ctl+Alt+DEL": "C-A-Del", "Ctl+Alt+END": "C-A-End",
    "Ctl+Alt+PAUSE BREAK": "C-A-Brk", "&mkp LCLK": "LMB", "&mkp RCLK": "RMB",
    "&mkp MCLK": "MMB", "Gui+LEFT": "◆←", "Gui+RIGHT": "◆→", "Gui+UP": "◆↑",
    "Gui+DOWN": "◆↓", "Alt+TAB": "Alt⇥",
    "&game_on": "GAME ▶", "&game_off": "◀ Desk",
}
LAYER_NAMES = set(REACH) | {"WORK"}
MODS = {"⇧ Shift", "Ctrl", "Alt", "◆ Super"}


def physical_keys():
    """(x, y, rot, rx, ry) per key, in ZMK centi-units / centi-degrees."""
    keys = []
    for line in DTSI.read_text().splitlines():
        m = re.search(r"&key_physical_attrs\s+(.*?)>?\s*$", line)
        if m:
            nums = [int(n) for n in re.findall(r"-?\d+", m.group(1).replace("(", "").replace(")", ""))]
            _w, _h, x, y, rot, rx, ry = nums
            keys.append((x, y, rot, rx, ry))
    return keys


def parse_layers():
    out = subprocess.run(["keymap", "-c", str(ROOT / "keymap_drawer.config.yaml"), "parse", "-z", str(KEYMAP)], check=True,
                         capture_output=True, text=True).stdout
    return yaml.safe_load(out)["layers"]


def pretty(label):
    return PRETTY.get(label, label)


def key_html(binding):
    """Return (classes, inner html) for one parsed binding."""
    if binding is None or binding == "":
        return "none", ""
    if isinstance(binding, dict):
        if binding.get("type") == "held":
            return "held", '<span class="tap">held</span>'
        if binding.get("type") == "trans":
            return "trans", ""
        tap = pretty(str(binding.get("t", "")))
        hold = binding.get("h")
        shifted = binding.get("s")
        cls = "layer" if tap in LAYER_NAMES else "dual" if hold else ""
        if tap == "BT" and hold is not None:  # &bt BT_SEL n
            return "sys", f'<span class="tap">BT {html.escape(str(hold))}</span>'
        inner = f'<span class="tap">{html.escape(tap)}</span>'
        if hold is not None:
            inner += f'<span class="hold">{html.escape(pretty(str(hold)))}</span>'
        if shifted:
            inner += f'<span class="hold">{html.escape(str(shifted))}</span>'
        return cls, inner
    label = pretty(str(binding))
    cls = ("layer" if label in LAYER_NAMES else "mod" if label in MODS
           else "sys" if label.startswith(("BT", "Out", "C-A")) else "")
    if len(label) == 1 and not label.isalnum():
        cls += " sym"
    return cls, f'<span class="tap">{html.escape(label)}</span>'


def board(name, bindings, phys):
    width, height = 1400, 440
    if name == "NUM":  # the Esc corner (0) is held
        bindings = [{"type": "held"} if i == 0 else b for i, b in enumerate(bindings)]
    if name == "SYSTEM":  # RAISE (39) + left centre thumb (37) are held
        bindings = [{"type": "held"} if i in (37, 39) else b for i, b in enumerate(bindings)]
    keys = []
    for (x, y, rot, rx, ry), binding in zip(phys, bindings):
        cls, inner = key_html(binding)
        style = (f"left:{x / width * 100:.3f}%;top:{y / height * 100:.3f}%;"
                 f"transform-origin:{(rx - x)}% {(ry - y)}%;"
                 f"transform:rotate({rot / 100}deg)") if rot else \
            f"left:{x / width * 100:.3f}%;top:{y / height * 100:.3f}%"
        keys.append(f'<div class="key {cls}" style="{style}">{inner}</div>')
    return (f'<section class="layer-card"><header><h2>{html.escape(name)}</h2>'
            f'<span>{REACH.get(name, "")}</span></header>'
            f'<div class="board">{"".join(keys)}</div></section>')


CSS = """
:root{--bg:#0f1115;--panel:#171a21;--key:#222733;--key-edge:#2d3442;--text:#e6e9ef;
--muted:#8a93a6;--accent:#8fb8ff;--mod:#c8a2ff;--layer:#7fe0c3;--sys:#ffb38a;--trans:#1a1e26}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#f4f5f8;--panel:#fff;
--key:#eef0f5;--key-edge:#d5d9e3;--text:#1b1f27;--muted:#5d6577;--accent:#2f6fde;--mod:#7d3fd6;
--layer:#0f8a6a;--sys:#c45a1a;--trans:#f7f8fb}}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.3 system-ui,-apple-system,"Segoe UI",sans-serif}
main{padding:16px;max-width:2400px;margin:auto}
.top{display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline;margin-bottom:12px}
h1{font-size:20px;margin:0;font-weight:650}.top small{color:var(--muted)}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,620px),1fr))}
.layer-card{background:var(--panel);border:1px solid var(--key-edge);border-radius:12px;
padding:10px 14px 14px;container-type:inline-size}
.layer-card header{display:flex;gap:12px;align-items:baseline;margin-bottom:6px}
h2{margin:0;font-size:16px;letter-spacing:.06em;color:var(--accent)}
.layer-card header span{color:var(--muted);font-size:13px}
.board{position:relative;width:100%;aspect-ratio:1400/440}
.key{position:absolute;width:calc(100%/14 - .5cqw);height:calc(100%/4.4 - .5cqw);
margin:.25cqw;background:var(--key);border:1px solid var(--key-edge);border-radius:.8cqw;
display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;
font-size:2cqw;line-height:1.1;overflow:hidden;padding:0 .2cqw}
.key .tap{font-weight:600}.key .hold{font-size:1.5cqw;color:var(--muted);margin-top:.2cqw}
.key.sym .tap{font-size:2.4cqw}
.key.trans,.key.none{background:var(--trans);border-style:dashed;opacity:.55}
.key.mod{color:var(--mod)}.key.layer{color:var(--layer);border-color:var(--layer)}
.key.sys{color:var(--sys)}.key.dual .hold{color:var(--mod)}
.key.held{background:var(--layer);border-color:var(--layer);opacity:.85}
.key.held .tap{color:var(--bg);font-size:1.4cqw;text-transform:uppercase;letter-spacing:.05em}
.notes{display:grid;gap:6px 18px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
margin-top:14px;background:var(--panel);border:1px solid var(--key-edge);border-radius:12px;padding:12px 14px}
.notes div b{color:var(--accent);font-weight:600;margin-right:6px}
"""


def main():
    phys = physical_keys()
    layers = parse_layers()
    cards = "".join(board(name, b, phys) for name, b in layers.items())
    notes = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in NOTES)
    OUT.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Toucan 2 Keymap</title><style>{CSS}</style></head>
<body><main>
<div class="top"><h1>Toucan 2 keymap</h1>
<small>generated from config/toucan.keymap &middot; regenerate with scripts/reference.py &middot; auto-reloads every minute</small></div>
<div class="grid">{cards}</div>
<div class="notes">{notes}</div>
</main></body></html>
""")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

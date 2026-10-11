#!/usr/bin/env python3
"""Render reference.html: an interactive Toucan 2 keymap reference.

    scripts/reference.py            # writes reference.html at the repo root

The page is generated straight from config/toucan.keymap (bindings) and
boards/shields/toucan/toucan.dtsi (physical key positions), so every "how do I
type X" answer on it is computed from the real keymap and cannot drift. It is
self-contained (inline CSS/JS, no fonts or CDNs) and is what
scripts/deploy-site.sh publishes to keymap.home.bironfamily.net.

Only the layer reach table, the curated common actions and a few Hyprland
shortcuts are hand-written below; the generator fails loudly if any of them
points at a binding the keymap no longer has.
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DTSI = ROOT / "boards/shields/toucan/toucan.dtsi"
KEYMAP = ROOT / "config/toucan.keymap"
OUT = ROOT / "reference.html"

# --------------------------------------------------------------------------
# Physical layout
# --------------------------------------------------------------------------
# Positions: rows of 12 (0-11, 12-23, 24-35), then thumbs 36-41 left to right
# (left outer, centre, inner, right inner, centre, outer).
POS_NAME = {0: "Esc", 11: "Backspace", 12: "Tab", 23: "'", 24: "Shift", 35: "-",
            36: "Ctrl thumb", 37: "Space thumb", 38: "Super thumb",
            39: "RAISE thumb", 40: "Enter thumb", 41: "LOWER thumb"}


def physical_keys():
    """[{x, y, r, rx, ry}] per key in key units (1u = one key pitch)."""
    keys = []
    for line in DTSI.read_text().splitlines():
        m = re.search(r"&key_physical_attrs\s+(.*?)>?\s*$", line)
        if m:
            nums = [int(n) for n in re.findall(r"-?\d+", m.group(1).replace("(", "").replace(")", ""))]
            _w, _h, x, y, rot, rx, ry = nums
            keys.append({"x": x / 100, "y": y / 100, "r": rot / 100, "rx": rx / 100, "ry": ry / 100})
    assert len(keys) == 42, f"expected 42 keys in {DTSI}, found {len(keys)}"
    return keys


# --------------------------------------------------------------------------
# Layers: how you get there, and the colour the page uses for each
# --------------------------------------------------------------------------
# chips: ("hold", pos) / ("tap", pos) / ("touch",) / ("mode", "GAME")
LAYER_INFO = {
    "BASE":   {"color": "base",   "reach": "Always on",                              "chips": []},
    "SYM":    {"color": "sym",    "reach": "Hold Esc",                               "chips": [("hold", 0)]},
    "LOWER":  {"color": "lower",  "reach": "Hold the right outer thumb",             "chips": [("hold", 41)]},
    "RAISE":  {"color": "raise",  "reach": "Hold the right inner thumb",             "chips": [("hold", 39)]},
    "SYSTEM": {"color": "system", "reach": "Hold RAISE and the Space thumb",         "chips": [("hold", 39), ("hold", 37)]},
    "WORK":   {"color": "work",   "reach": "Tap, then hold RAISE",                   "chips": [("taphold", 39)]},
    "MOU":    {"color": "mou",    "reach": "Automatic while a finger is on the trackpad", "chips": [("touch",)]},
    "GAME":   {"color": "game",   "reach": "Gaming mode: hold LOWER and press Esc",  "chips": [("mode", "GAME")]},
    "NUM":    {"color": "num",    "reach": "In gaming mode, hold Esc",               "chips": [("mode", "GAME"), ("hold", 0)]},
}
TAB_ORDER = ["BASE", "SYM", "LOWER", "RAISE", "SYSTEM", "GAME", "NUM", "MOU", "WORK"]

# --------------------------------------------------------------------------
# Keycodes -> (legend, description, character typed)
# --------------------------------------------------------------------------
KEYS = {}
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEYS[c] = (c, c, c.lower())
for d in "0123456789":
    KEYS[f"N{d}"] = (d, d, d)
for n in range(1, 13):
    KEYS[f"F{n}"] = (f"F{n}", f"F{n}", None)
SYMBOLS = [
    ("EXCL", "!", "Exclamation"), ("AT", "@", "At"), ("HASH", "#", "Hash"), ("DLLR", "$", "Dollar"),
    ("PRCNT", "%", "Percent"), ("CARET", "^", "Caret"), ("AMPS", "&", "Ampersand"),
    ("STAR", "*", "Asterisk"), ("LPAR", "(", "Left paren"), ("RPAR", ")", "Right paren"),
    ("MINUS", "-", "Minus"), ("UNDER", "_", "Underscore"), ("EQUAL", "=", "Equals"),
    ("PLUS", "+", "Plus"), ("LBKT", "[", "Left bracket"), ("RBKT", "]", "Right bracket"),
    ("LBRC", "{", "Left brace"), ("RBRC", "}", "Right brace"), ("BSLH", "\\", "Backslash"),
    ("PIPE", "|", "Pipe"), ("SEMI", ";", "Semicolon"), ("SQT", "'", "Apostrophe"),
    ("GRAVE", "`", "Backtick"), ("TILDE", "~", "Tilde"), ("COMMA", ",", "Comma"),
    ("DOT", ".", "Period"), ("FSLH", "/", "Slash"), ("LT", "<", "Less than"), ("GT", ">", "Greater than"),
]
for code, ch, name in SYMBOLS:
    KEYS[code] = (ch, name, ch)
KEYS.update({
    "SPACE": ("Space", "Space", " "), "ENTER": ("Enter", "Enter", None), "ESC": ("Esc", "Escape", None),
    "TAB": ("Tab", "Tab", None), "BACKSPACE": ("⌫", "Backspace", None), "DEL": ("Del", "Delete", None),
    "HOME": ("Home", "Home", None), "END": ("End", "End", None), "PG_UP": ("PgUp", "Page up", None),
    "PG_DN": ("PgDn", "Page down", None), "LEFT": ("←", "Left arrow", None), "RIGHT": ("→", "Right arrow", None),
    "UP": ("↑", "Up arrow", None), "DOWN": ("↓", "Down arrow", None),
    "LSHIFT": ("Shift", "Shift", None), "LCTRL": ("Ctrl", "Ctrl", None), "LALT": ("Alt", "Alt", None),
    "LGUI": ("Super", "Super", None), "C_MUTE": ("Mute", "Mute", None), "C_VOL_DN": ("Vol −", "Volume down", None),
    "C_VOL_UP": ("Vol +", "Volume up", None), "C_PP": ("⏯", "Play / pause", None),
    "PAUSE_BREAK": ("Pause", "Pause/Break", None), "KP_NUM": ("NumLk", "Num Lock", None),
})
MODS = {"LG": "Super", "LC": "Ctrl", "LA": "Alt", "LS": "Shift"}
MOD_KEYS = {"LSHIFT", "LCTRL", "LALT", "LGUI"}

# Named combos: legend + what it does on this desk (Hyprland).
COMBOS = {
    "LG(LEFT)": ("◆ ←", "Focus the window to the left"), "LG(RIGHT)": ("◆ →", "Focus the window to the right"),
    "LG(UP)": ("◆ ↑", "Focus up in the column"), "LG(DOWN)": ("◆ ↓", "Focus down in the column"),
    "LA(TAB)": ("Alt ⇥", "Alt+Tab"),
    "LC(LA(PAUSE_BREAK))": ("C-A-Brk", "Ctrl+Alt+Pause (KVM / remote)"),
    "LC(LA(END))": ("C-A-End", "Ctrl+Alt+End (remote desktop Ctrl+Alt+Del)"),
    "LC(LA(DEL))": ("C-A-Del", "Ctrl+Alt+Del"),
}
for n in "12345":
    COMBOS[f"LG(N{n})"] = (f"◆ {n}", f"Workspace {n} (add Shift to move the window there)")


def kp(code):
    """Describe an &kp parameter: plain keycode or LG(...)-style combo."""
    if code in COMBOS:
        t, desc = COMBOS[code]
        return {"t": t, "desc": desc, "kind": "combo", "code": code}
    m = re.fullmatch(r"(L[GCAS])\((.*)\)", code)
    if m:
        inner = kp(m.group(2))
        name = f"{MODS[m.group(1)]}+{inner['desc']}"
        return {"t": name, "desc": name, "kind": "combo", "code": code}
    if code not in KEYS:
        raise SystemExit(f"reference.py: unknown keycode {code!r} - add it to KEYS")
    t, desc, ch = KEYS[code]
    kind = "mod" if code in MOD_KEYS else "media" if code.startswith("C_") else "key"
    out = {"t": t, "desc": desc, "kind": kind, "code": code}
    if ch:
        out["ch"] = ch
    return out


MOUSE = {"LCLK": ("Left click", "Left click"), "RCLK": ("Right click", "Right click"),
         "MCLK": ("Middle", "Middle click"), "MB4": ("Back", "Mouse back"), "MB5": ("Fwd", "Mouse forward")}


def describe(tok):
    """One binding token (without the &) -> dict for the page."""
    parts = tok.split()
    b, args = parts[0], parts[1:]
    if b == "trans":
        return {"kind": "trans"}
    if b == "none":
        return {"kind": "none"}
    if b == "kp":
        return kp(args[0])
    if b == "mo":
        return {"t": args[0], "desc": f"Hold for {args[0]}", "kind": "layer", "layer": args[0]}
    if b == "td_layer_work":
        return {"t": "RAISE", "s": "×2 WORK", "desc": "Hold for RAISE · tap then hold for WORK",
                "kind": "layer", "layer": "RAISE"}
    if b == "ht_layer":
        tap = kp(args[1])
        return {"t": tap["t"], "s": args[0], "desc": f"Tap: {tap['desc']} · hold: {args[0]}",
                "kind": "layer", "layer": args[0], "tap": tap["code"]}
    if b == "ht_alt":
        tap = kp(args[1])
        return {"t": tap["t"], "s": "Alt", "desc": f"Tap: {tap['desc']} · hold: Alt",
                "kind": "dual", "tap": tap["code"], "hold": "LALT"}
    if b == "game_on":
        return {"t": "GAME", "s": "on", "desc": "Gaming mode on, and jump to the Play workspace", "kind": "macro", "code": "game_on"}
    if b == "game_off":
        return {"t": "Desk", "s": "exit", "desc": "Leave gaming mode, and jump to workspace 1", "kind": "macro", "code": "game_off"}
    if b == "bt":
        if args[0] == "BT_SEL":
            return {"t": f"BT {args[1]}", "desc": f"Bluetooth profile {args[1]}", "kind": "sys", "code": f"BT{args[1]}"}
        if args[0] == "BT_CLR":
            return {"t": "BT clr", "desc": "Forget the current Bluetooth profile's pairing", "kind": "sys", "code": "BT_CLR"}
    if b == "out":
        label = {"OUT_BLE": ("BLE", "Type over Bluetooth"), "OUT_USB": ("USB", "Type over USB"),
                 "OUT_TOG": ("USB/BT", "Toggle USB / Bluetooth")}[args[0]]
        return {"t": label[0], "desc": label[1], "kind": "sys", "code": args[0]}
    if b == "mkp":
        t, desc = MOUSE[args[0]]
        return {"t": t, "desc": desc, "kind": "mouse", "code": args[0]}
    if b == "sk":
        return {"t": "Ctrl+Alt", "s": "sticky", "desc": "Sticky Ctrl+Alt: applies to the next key you tap",
                "kind": "mod", "code": "sk"}
    if b == "bootloader":
        return {"t": "Boot", "desc": "Put this half into flashing mode", "kind": "sys", "code": "bootloader"}
    raise SystemExit(f"reference.py: unknown behavior &{tok} - teach describe() about it")


def parse_keymap():
    src = KEYMAP.read_text()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    body = src[src.index("compatible = \"zmk,keymap\""):]
    layers = []
    for m in re.finditer(r"display-name\s*=\s*\"([^\"]+)\";\s*bindings\s*=\s*<(.*?)>;", body, re.S):
        name, raw = m.group(1), m.group(2)
        toks = [t.strip() for t in raw.split("&") if t.strip()]
        assert len(toks) == 42, f"layer {name}: {len(toks)} bindings, expected 42"
        layers.append((name, [describe(t) for t in toks]))
    return layers


# --------------------------------------------------------------------------
# "How do I reach it" - computed from the keymap
# --------------------------------------------------------------------------
def build(layers):
    byname = dict(layers)
    base = byname["BASE"]

    def pos_name(p):
        if p in POS_NAME:
            return POS_NAME[p]
        return base[p]["t"]

    def reach_chips(layer):
        out = []
        for c in LAYER_INFO[layer]["chips"]:
            if c[0] == "hold":
                out.append({"t": f"hold {pos_name(c[1]).replace(' thumb', '')}", "layer": layer, "pos": c[1]})
            elif c[0] == "taphold":
                out.append({"t": "tap, hold RAISE", "layer": layer, "pos": c[1]})
            elif c[0] == "touch":
                out.append({"t": "touch the trackpad", "layer": layer})
            elif c[0] == "mode":
                out.append({"t": "gaming mode", "layer": "GAME"})
        return out

    held = {name: [c[1] for c in LAYER_INFO[name]["chips"] if c[0] in ("hold", "taphold")] for name in byname}

    # Every way to produce each code: [{layer, pos, chips}]
    ways = {}

    def add(code, layer, pos, chips):
        ways.setdefault(code, []).append({"layer": layer, "pos": pos, "chips": chips})

    for name, keys in layers:
        if name in ("GAME", "NUM"):
            continue  # gaming copies; don't offer them as everyday answers
        for p, k in enumerate(keys):
            if k["kind"] in ("trans", "none") or p in held[name]:
                continue
            target = reach_chips(name) + [{"t": pos_name(p), "layer": name, "pos": p}]
            if "tap" in k:
                add(k["tap"], name, p, target)
            if k.get("hold") == "LALT":
                add("LALT", name, p, reach_chips(name) + [{"t": f"hold {pos_name(p)}", "layer": name, "pos": p}])
            elif "code" in k:
                add(k["code"], name, p, target)
    for code in ways:
        ways[code].sort(key=lambda w: (len(w["chips"]), TAB_ORDER.index(w["layer"])))

    def how(code, layer=None):
        opts = [w for w in ways.get(code, []) if layer is None or w["layer"] == layer]
        if not opts:
            raise SystemExit(f"reference.py: nothing in the keymap produces {code}"
                             + (f" on {layer}" if layer else ""))
        return opts[0]["chips"]

    def multi(layer, codes, label=None):
        """Chips for a run of keys on one layer, e.g. RAISE + J K L ;"""
        ps = []
        for c in codes:
            w = [x for x in ways.get(c, []) if x["layer"] == layer]
            if not w:
                raise SystemExit(f"reference.py: {c} is not on {layer}")
            ps.append(w[0]["pos"])
        return reach_chips(layer) + [{"t": label or " ".join(pos_name(p) for p in ps),
                                      "layer": layer, "pos": ps}]

    def k(*names):
        """Plain chips for base keys/modifiers by name."""
        out = []
        for n in names:
            if n == "Alt":
                out += how("LALT")
            elif n in ("Ctrl", "Super", "Shift"):
                code = {"Ctrl": "LCTRL", "Super": "LGUI", "Shift": "LSHIFT"}[n]
                out += how(code, "BASE")
            else:
                out.append({"t": n, "kbd": 1})
        return out

    def g(text):
        """A trackpad gesture or other non-key step."""
        return [{"t": text, "gesture": 1}]

    def game(code_layer, codes, label=None):
        g = byname[code_layer]
        ps = [i for i, x in enumerate(g) if x.get("code") in codes]
        assert ps, f"{codes} not on {code_layer}"
        return reach_chips(code_layer) + [{"t": label or " ".join(pos_name(p) for p in ps),
                                           "layer": code_layer, "pos": ps}]

    # ---------------------------------------------------------------- actions
    A = []

    def group(title, items):
        A.append({"title": title, "items": items})

    def item(label, *alts, note=None):
        return {"label": label, "ways": list(alts), "note": note}

    group("Editing", [
        item("Delete the previous word", k("Ctrl", "Backspace")),
        item("Delete forward", how("DEL")),
        item("Arrow keys", multi("RAISE", ["LEFT", "DOWN", "UP", "RIGHT"])),
        item("Jump by word", k("Ctrl") + multi("RAISE", ["LEFT", "RIGHT"])),
        item("Select while moving", k("Shift") + multi("RAISE", ["LEFT", "DOWN", "UP", "RIGHT"])),
        item("Home / End", multi("RAISE", ["HOME", "END"])),
        item("Page up / down", multi("RAISE", ["PG_UP", "PG_DN"])),
        item("Undo, copy, cut, paste", k("Ctrl", "Z X C V")),
        item("Escape", k("Esc"), note="Tap it. Holding it opens SYM."),
    ])
    group("Windows and workspaces", [
        item("Focus left / down / up / right", multi("RAISE", ["LG(LEFT)", "LG(DOWN)", "LG(UP)", "LG(RIGHT)"]),
             k("Super") + multi("RAISE", ["LEFT", "DOWN", "UP", "RIGHT"]),
             note="A three-finger swipe on the trackpad does the same."),
        item("Move the window", k("Super", "Shift") + multi("RAISE", ["LEFT", "DOWN", "UP", "RIGHT"])),
        item("Workspace 1–5", multi("LOWER", [f"LG(N{n})" for n in "12345"])),
        item("Send the window to workspace 1–5", reach_chips("LOWER") + k("Shift") +
             [{"t": "Q W E R T", "layer": "LOWER", "pos": [1, 2, 3, 4, 5]}]),
        item("Named spaces", k("Super", "H J K L ; '"), note="imagegen, comms, dev, play, status, media"),
        item("Last-used workspace", k("Super") + how("GRAVE")),
        item("Alt+Tab", how("LA(TAB)")),
        item("Close the window", k("Super", "Q")),
        item("Launcher", k("Super", "R")),
        item("Terminal", k("Super", "T")),
        item("Cycle the window's width", k("Super", "A")),
        item("Minimize", k("Super", "M")),
    ])
    group("Numbers and zoom", [
        item("Numbers", multi("SYM", [f"N{n}" for n in range(1, 10)], "Y U I · H J K · N M ,"),
             note="It's a numpad: 7 8 9 on top. 0 is the Enter thumb, . the LOWER thumb."),
        item("Zero", how("N0", "SYM")),
        item("Zoom out", k("Ctrl", "Shift") + [{"t": "-", "pos": 35, "layer": "BASE"}]),
        item("Zoom in", k("Ctrl") + reach_chips("LOWER") + [{"t": "-", "pos": 35, "layer": "LOWER"}],
             note="LOWER turns the - key into +. Pinching the trackpad zooms browsers too."),
    ])
    group("Trackpad", [
        item("Click", g("Tap the pad")),
        item("Right click", g("Two-finger tap")),
        item("Drag", g("Press and hold, then move")),
        item("Scroll", g("Two-finger drag"), reach_chips("RAISE") + g("move a finger")),
        item("Click with keys", reach_chips("MOU") + [{"t": "F D S", "layer": "MOU", "pos": [16, 15, 14]}],
             note="Left, middle, right click while a finger rests on the pad."),
        item("Back / forward", reach_chips("MOU") + [{"t": "W R", "layer": "MOU", "pos": [2, 4]}]),
        item("Focus windows", g("Three-finger swipe")),
        item("Zoom", g("Pinch")),
    ])
    group("Media and connections", [
        item("Volume down / up / mute", multi("SYSTEM", ["C_VOL_DN", "C_VOL_UP", "C_MUTE"])),
        item("Play / pause", how("C_PP")),
        item("F1–F12", multi("SYSTEM", ["F1", "F12"], "top row")),
        item("Switch Bluetooth profile 0–4", multi("LOWER", [f"BT{n}" for n in range(5)])),
        item("Forget this profile's pairing", how("BT_CLR")),
        item("Type over USB / Bluetooth", multi("SYSTEM", ["OUT_USB", "OUT_BLE"])),
    ])
    group("Gaming mode", [
        item("Start gaming mode", how("game_on"), note="Also jumps to the Play workspace."),
        item("Numbers 1–5 / 6–0", game("NUM", ["N1", "N2", "N3", "N4", "N5"], "top row · home row")),
        item("F1–F5", game("NUM", ["F1", "F2", "F3", "F4", "F5"], "bottom row")),
        item("Back to the desktop", game("NUM", ["game_off"]), note="Also jumps to workspace 1."),
    ])
    group("Keyboard upkeep", [
        item("Flash the left half", reach_chips("SYSTEM") + [{"t": "Shift", "layer": "SYSTEM", "pos": 24}],
             note="Plug that half in by USB first; the XIAO drive appears."),
        item("Flash the right half", reach_chips("SYSTEM") + [{"t": "-", "layer": "SYSTEM", "pos": 35}]),
        item("Ctrl+Alt+Del", how("LC(LA(DEL))")),
        item("Sticky Ctrl+Alt", how("sk")),
        item("Num Lock", how("KP_NUM")),
    ])
    # Hand-placed chips above point at these positions; fail if the keymap moves them.
    assert byname["SYSTEM"][24].get("code") == "bootloader" and byname["SYSTEM"][35].get("code") == "bootloader"
    assert byname["LOWER"][35].get("code") == "PLUS" and byname["BASE"][35].get("code") == "MINUS"
    assert [byname["MOU"][p].get("code") for p in (16, 15, 14, 2, 4)] == ["LCLK", "MCLK", "RCLK", "MB4", "MB5"]
    assert [byname["LOWER"][p].get("code") for p in range(1, 6)] == [f"LG(N{n})" for n in "12345"]

    # ---------------------------------------------------------------- symbols
    shifted = {"!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9",
               ")": "0", "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\", ":": ";", "\"": "'", "~": "`",
               "<": ",", ">": ".", "?": "/"}
    ch2code = {v[2]: c for c, v in KEYS.items() if v[2]}
    shift_chip = how("LSHIFT", "BASE")
    sym_rows = []
    for ch in "!@#$%^&*()-_=+[]{}\\|;:'\"`~,.<>/?0123456789":
        opts = []
        code = ch2code.get(ch)
        if code and code in ways:
            opts += [w["chips"] for w in ways[code]]
        if ch in shifted and ch2code.get(shifted[ch]) in ways:
            opts += [shift_chip + w["chips"] for w in ways[ch2code[shifted[ch]]]]
        opts.sort(key=len)
        uniq = []
        for o in opts:
            if o not in uniq:
                uniq.append(o)
        if not uniq:
            raise SystemExit(f"reference.py: no way to type {ch!r}")
        sym_rows.append({"ch": ch, "ways": uniq[:2]})

    layer_list = []
    for name in TAB_ORDER:
        info = LAYER_INFO[name]
        layer_list.append({"name": name, "color": info["color"], "reach": info["reach"],
                           "held": held[name], "keys": byname[name]})
    missing = set(byname) - set(TAB_ORDER)
    assert not missing, f"layers without LAYER_INFO: {missing}"
    return {"layers": layer_list, "actions": A, "symbols": sym_rows,
            "ways": ways, "posNames": {p: pos_name(p) for p in range(42)}}


def git_rev():
    try:
        rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "config/"],
                               capture_output=True, text=True).stdout.strip()
        return rev + ("+" if dirty else "")
    except Exception:
        return "unknown"


TEMPLATE = (Path(__file__).resolve().parent / "reference.template.html")


def main():
    data = build(parse_keymap())
    data["phys"] = physical_keys()
    data["rev"] = git_rev()
    data["generated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    OUT.write_text(page)
    print(f"wrote {OUT} ({data['rev']})")


if __name__ == "__main__":
    main()

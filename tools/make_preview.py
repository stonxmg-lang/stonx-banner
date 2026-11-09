#!/usr/bin/env python3
"""Renders docs/preview.gif and docs/preview.png for the README.

It runs the real banner drawing code, then paints each terminal cell itself:
block and box-drawing characters are drawn as shapes, so the picture does not
depend on what fonts are installed.

    python3 tools/make_preview.py [path/to/mono.ttf]

Needs Pillow (pip install pillow).
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "stonx"))
sys.dont_write_bytecode = True
import banner  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

COLS = 50
CW, CH = 14, 28                  # cell size in pixels
PAD, BAR = 28, 44                # window padding, title bar height
BG, WINDOW = (13, 15, 20), (8, 9, 12)
RED_P, BLUE_P, TEXT = (255, 85, 85), (85, 85, 255), (225, 230, 240)
CFG = dict(banner.DEFAULTS)

FONT_PATHS = [p for p in sys.argv[1:2]] + [
    "/system/fonts/DroidSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]
WIDE_PATHS = ["/system/fonts/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]


def load(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT = load(FONT_PATHS, 22)
WIDE = load(WIDE_PATHS, 20)


def cell_box(d, ch, x0, y0, c):
    """Block and box-drawing characters as plain shapes."""
    x1, y1 = x0 + CW - 1, y0 + CH - 1
    cx, cy = x0 + CW // 2, y0 + CH // 2
    o, t = 3, 2                    # double-line offset and thickness

    def h(y, a, b):
        d.rectangle([a, y - t // 2, b, y - t // 2 + t - 1], fill=c)

    def v(x, a, b):
        d.rectangle([x - t // 2, a, x - t // 2 + t - 1, b], fill=c)

    if ch == "█":
        d.rectangle([x0, y0, x1, y1], fill=c)
    elif ch == "▀":
        d.rectangle([x0, y0, x1, cy - 1], fill=c)
    elif ch == "▄":
        d.rectangle([x0, cy, x1, y1], fill=c)
    elif ch == "░":
        for yy in range(y0, y1 + 1, 4):
            for xx in range(x0 + (yy // 4 % 2) * 2, x1 + 1, 4):
                d.rectangle([xx, yy, xx + 1, yy + 1], fill=c)
    elif ch == "═":
        h(cy - o, x0, x1); h(cy + o, x0, x1)
    elif ch == "║":
        v(cx - o, y0, y1); v(cx + o, y0, y1)
    elif ch == "╗":           # left + down
        h(cy - o, x0, cx + o); v(cx + o, cy - o, y1)
        h(cy + o, x0, cx - o); v(cx - o, cy + o, y1)
    elif ch == "╔":           # right + down
        h(cy - o, cx - o, x1); v(cx - o, cy - o, y1)
        h(cy + o, cx + o, x1); v(cx + o, cy + o, y1)
    elif ch == "╝":           # left + up
        h(cy + o, x0, cx + o); v(cx + o, y0, cy + o)
        h(cy - o, x0, cx - o); v(cx - o, y0, cy - o)
    elif ch == "╚":           # right + up
        h(cy + o, cx - o, x1); v(cx - o, y0, cy + o)
        h(cy - o, cx + o, x1); v(cx + o, y0, cy - o)
    elif ch == "─":
        h(cy, x0, x1)
    elif ch == "┌":
        h(cy, cx, x1); v(cx, cy, y1)
    elif ch == "└":
        h(cy, cx, x1); v(cx, y0, cy)
    else:
        return False
    return True


def paint(cells, cursor_on):
    w = COLS * CW + PAD * 2
    hgt = ROWS * CH + PAD * 2 + BAR
    img = Image.new("RGB", (w + 48, hgt + 48), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([24, 24, 24 + w, 24 + hgt], radius=18, fill=WINDOW, outline=(38, 42, 54), width=2)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([48 + i * 24, 40, 60 + i * 24, 52], fill=col)
    d.text((24 + w // 2, 46), "Termux", fill=(120, 126, 140), font=FONT, anchor="mm")
    ox, oy = 24 + PAD, 24 + BAR + PAD // 2
    for (r, c), ch, colour in cells:
        x0, y0 = ox + (c - 1) * CW, oy + (r - 1) * CH
        if ch == " ":
            continue
        if not cell_box(d, ch, x0, y0, colour):
            wide = ord(ch) > 0x3000      # double-width glyph: centre it across two cells
            d.text((x0 + (CW if wide else CW // 2), y0 + CH // 2), ch, fill=colour,
                   font=WIDE if wide else FONT, anchor="mm")
    if cursor_on:
        r, c = cursor
        d.rectangle([ox + (c - 1) * CW, oy + (r - 1) * CH + 3, ox + c * CW - 2, oy + r * CH - 3], fill=BLUE_P)
    return img


def banner_cells(lay, intro_t, shimmer_t):
    raw = {}
    banner.draw(lay, banner.THEMES[CFG["THEME"]], raw, intro_t, shimmer_t)
    out = []
    for key, s in raw.items():
        m = re.findall(r"38;2;(\d+);(\d+);(\d+)", s)
        out.append((key, s[-1], tuple(map(int, m[-1])) if m else TEXT))
    return out


def prompt_cells(top):
    parts = [(RED_P, "┌──("), (BLUE_P, "stonx㉿Termux"), (RED_P, ")-["), (BLUE_P, "~"), (RED_P, "]")]
    out, col = [], 1
    for colour, text in parts:
        for ch in text:
            out.append(((top, col), ch, colour))
            col += 2 if ch == "㉿" else 1
    out += [((top + 1, 1), "└", RED_P), ((top + 1, 2), "─", RED_P), ((top + 1, 3), "$", BLUE_P)]
    return out


lay = banner.Layout(40, COLS, CFG)
ROWS = lay.height + 2               # banner, then the two-line prompt
prompt = prompt_cells(lay.height + 1)
cursor = (lay.height + 2, 5)

frames, durations = [], []


def add(intro_t, shimmer_t, ms, cur=True):
    frames.append(paint(banner_cells(lay, intro_t, shimmer_t) + prompt, cur))
    durations.append(ms)


for i in range(12):                        # reveal
    add(i / 11, None, 50)
add(None, None, 500)
add(None, None, 500, False)
for i in range(22):                        # shimmer
    add(None, i / 21 * 1.0, 50)
for k in range(4):                         # rest, cursor blinking
    add(None, None, 500, k % 2 == 1)

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
still = paint(banner_cells(lay, None, None) + prompt, True)
still.save(os.path.join(ROOT, "docs", "preview.png"), optimize=True)
small = [f.resize((f.width * 2 // 3, f.height * 2 // 3), Image.LANCZOS) for f in frames]
pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in small]
pal[0].save(os.path.join(ROOT, "docs", "preview.gif"), save_all=True, append_images=pal[1:],
            duration=durations, loop=0, optimize=True, disposal=1)
print("wrote docs/preview.png and docs/preview.gif")

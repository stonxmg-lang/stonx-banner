#!/usr/bin/env python3
"""STONX live banner for Termux.

Draws your name in big block letters at the top of the terminal, with a grey
tagline underneath. It runs in the background above the prompt, never blocks
the shell, and re-fits itself on every resize or pinch-zoom.

    banner.py live <shell-pid> <prompt-first-line> <reserved-rows>
    banner.py print            draw it once, no animation
    banner.py height           rows the banner needs at this size
"""
import fcntl, os, re, signal, struct, sys, termios, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from font import GLYPHS, HEIGHT, MID_GLYPHS, MID_HEIGHT  # noqa: E402

CONFIG = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "stonx", "config")
LAYOUT_FILE = os.path.join(os.path.dirname(CONFIG), ".layout")

DEFAULTS = {"NAME": "STONX", "TAGLINE": "CODE  \xb7  BUILD  \xb7  BREAK  \xb7  REPEAT", "THEME": "red"}

# face light, face deep, shadow
THEMES = {
    "red":    ((255, 96, 108), (202, 24, 46), (120, 18, 32)),
    "blue":   ((110, 170, 255), (30, 90, 235), (22, 48, 125)),
    "green":  ((96, 240, 156), (14, 170, 90), (10, 84, 46)),
    "purple": ((196, 140, 255), (122, 52, 232), (62, 26, 118)),
    "orange": ((255, 186, 96), (236, 108, 20), (122, 56, 10)),
    "cyan":   ((110, 242, 255), (0, 168, 210), (0, 82, 104)),
    "pink":   ((255, 136, 204), (226, 40, 142), (112, 20, 72)),
    "gold":   ((255, 226, 120), (214, 158, 20), (110, 78, 8)),
}
GREY = (118, 124, 138)
INTRO, SWEEP, PERIOD = 0.7, 1.3, 6.0
CALM_AFTER = 300  # after this long the banner stops animating, to save battery


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.rstrip("\n").partition("=")
                if sep and key.strip() in cfg:
                    cfg[key.strip()] = value
    except OSError:
        pass
    if cfg["THEME"] not in THEMES:
        cfg["THEME"] = "red"
    return cfg


def term_size():
    return struct.unpack("HHHH", fcntl.ioctl(1, termios.TIOCGWINSZ, b"\0" * 8))


def clean_name(name):
    """Upper-case, only characters the font has, single spaces."""
    name = "".join(c for c in name.upper() if c in GLYPHS)
    return " ".join(name.split()) or "STONX"


def rows_of(text, glyphs, height):
    return ["".join(glyphs[c][i] for c in text).rstrip() for i in range(height)]


def wrap(name, room, glyphs, height):
    """Words packed onto as few lines as fit, or None if a word is too wide."""
    width = lambda t: max(map(len, rows_of(t, glyphs, height)))
    lines, cur = [], ""
    for word in name.split(" "):
        trial = (cur + " " + word).strip()
        if width(trial) <= room:
            cur = trial
        elif cur and width(word) <= room:
            lines.append(cur)
            cur = word
        else:
            return None
    lines.append(cur)
    return [rows_of(line, glyphs, height) for line in lines]


def wordmark(name, cols, max_rows):
    """Big letters if they fit, then mid-size blocks, then spaced small caps."""
    room = cols - 2
    for kind, glyphs, height in (("big", GLYPHS, HEIGHT), ("mid", MID_GLYPHS, MID_HEIGHT)):
        blocks = wrap(name, room, glyphs, height)
        if blocks and sum(len(b) + 1 for b in blocks) - 1 <= max_rows:
            return kind, blocks
    small = " ".join(name)
    return "small", [[small[:room]]]


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fg(c):
    return "\x1b[38;2;%d;%d;%dm" % c


class Layout:
    """Blank line, the name, the tagline, blank line, centred on the terminal."""

    def __init__(self, rows, cols, cfg):
        # Leave at least 4 free rows plus the blank lines and tagline.
        self.kind, self.blocks = wordmark(clean_name(cfg["NAME"]), cols, rows - 7)
        self.cols = cols
        tag = cfg["TAGLINE"].strip()
        self.tagline = tag if tag and len(tag) <= cols - 2 else ""
        title_rows = sum(len(b) for b in self.blocks) + (len(self.blocks) - 1)
        self.height = 1 + title_rows + (1 if self.tagline else 0) + 1
        self.fits = cols >= 10 and self.height <= rows - 4
        if not self.fits:
            self.height = 0


def draw(lay, theme, cells, intro_t, shimmer_t):
    hi, lo, shadow = theme
    row = 2
    for block in lay.blocks:
        width = max(len(r) for r in block)
        col = (lay.cols - width) // 2 + 1
        n = len(block)
        for y, line in enumerate(block):
            for i, ch in enumerate(line.ljust(width)):
                key = (row + y, col + i)
                x = i / max(width, 1)
                if ch == " " or (intro_t is not None and x > intro_t * 1.15):
                    cells[key] = "\x1b[0m "
                    continue
                if lay.kind == "small":
                    c = mix(hi, lo, x)
                else:
                    face = ch in "█▀▄"
                    c = mix(hi, lo, y / max(n - 1, 1)) if face else shadow
                    if ch == "░":  # the mid font's light-shade background
                        c = mix((0, 0, 0), shadow, 0.55)
                glow = 0.0
                if intro_t is not None:  # bright edge on the reveal
                    d = intro_t * 1.15 - x
                    glow = max(0.0, 1 - d / 0.08) * 0.9
                elif shimmer_t is not None:  # diagonal band of light
                    d = abs((x + y / n * 0.3) - shimmer_t * 1.3)
                    glow = max(0.0, 1 - d / 0.1) * (0.9 if ch == "█" else 0.4)
                if glow:
                    c = mix(c, (255, 255, 255), glow)
                cells[key] = fg(c) + "\x1b[49m" + ch
        row += n + 1
    if lay.tagline:
        row -= 1
        col = (lay.cols - len(lay.tagline)) // 2 + 1
        for i, ch in enumerate(lay.tagline):
            cells[(row, col + i)] = fg(GREY) + "\x1b[49m" + ch


class Banner:
    def __init__(self, shell, prompt_line):
        self.shell, self.prompt_line = shell, prompt_line
        self.cfg = load_config()
        self.theme = THEMES[self.cfg["THEME"]]
        self.start = self.anim_from = time.time()
        self.last = {}
        self.size = term_size()
        self.lay = Layout(self.size[0], self.size[1], self.cfg)

    def flush(self, cells, extra=""):
        out, pos = [], None
        for key in sorted(cells):
            if self.last.get(key) == cells[key]:
                continue
            if key != pos:
                out.append("\x1b[%d;%dH" % key)
            out.append(cells[key])
            pos = (key[0], key[1] + 1)
            self.last[key] = cells[key]
        if out or extra:
            # One write(): the kernel keeps it whole, so it cannot split your typing.
            # \e7 / \e8 save and restore the cursor and the input colour.
            os.write(1, ("\x1b7" + extra + "".join(out) + "\x1b[0m\x1b8").encode())

    def region(self):
        return "\x1b[%d;%dr" % (self.lay.height + 1, self.size[0]) if self.lay.fits else "\x1b[r"

    def relayout(self):
        """New size: redraw from clean, then let readline repaint the input line."""
        self.size = term_size()
        self.lay = Layout(self.size[0], self.size[1], self.cfg)
        self.last = {}
        h = self.lay.height
        plain = re.sub(r"\x1b\[[0-9;]*m", "", self.prompt_line)
        width = len(plain) + plain.count("\u327f")  # that glyph is two cells wide
        lines = max((width - 1) // self.size[1] + 1, 1)
        os.write(1, ("\x1b[r\x1b[3J\x1b[H\x1b[2J" + self.region() + "\x1b[%d;1H\x1b[0m%s\x1b[%d;1H"
                     % (h + 1, self.prompt_line, h + 1 + lines)).encode())
        remember(self.size, h)
        self.anim_from = time.time()
        self.repaint_input()

    def repaint_input(self):
        """Readline repaints the input line only when the size really changes, so
        nudge it by one row and put it back. Nothing you typed is lost."""
        r, c, x, y = self.size
        fcntl.ioctl(1, termios.TIOCSWINSZ, struct.pack("HHHH", max(r - 1, 1), c, x, y))
        time.sleep(0.05)
        fcntl.ioctl(1, termios.TIOCSWINSZ, struct.pack("HHHH", r, c, x, y))

    def finish(self, *_):
        if self.lay.fits:
            cells = {}
            draw(self.lay, self.theme, cells, None, None)
            self.flush(cells, "\x1b[r")
        else:
            os.write(1, b"\x1b7\x1b[r\x1b8")
        os._exit(0)

    def run(self, reserved):
        signal.signal(signal.SIGTERM, self.finish)
        signal.signal(signal.SIGHUP, lambda *_: os._exit(0))
        if self.lay.height != reserved:
            self.relayout()
        else:
            os.write(1, ("\x1b7" + self.region() + "\x1b8").encode())
            remember(self.size, self.lay.height)
        while True:
            now = time.time()
            if os.getppid() != self.shell:
                os._exit(0)
            size = term_size()
            if size != self.size:
                time.sleep(0.15)  # let a pinch-zoom settle
                if term_size() == size:
                    if size[:2] == self.size[:2]:
                        self.size = size
                    else:
                        self.relayout()
                continue
            if not self.lay.fits or now - self.start > CALM_AFTER:
                time.sleep(0.3)
                continue
            age = now - self.anim_from
            intro_t = age / INTRO if age < INTRO else None
            shimmer_t = None
            if intro_t is None and (age - INTRO) % PERIOD < SWEEP:
                shimmer_t = ((age - INTRO) % PERIOD) / SWEEP
            cells = {}
            draw(self.lay, self.theme, cells, intro_t, shimmer_t)
            self.flush(cells)
            time.sleep(0.05 if intro_t is not None or shimmer_t is not None else 0.25)


def remember(size, height):
    """Lets the next shell reserve the right space straight away."""
    try:
        os.makedirs(os.path.dirname(LAYOUT_FILE), exist_ok=True)
        with open(LAYOUT_FILE, "w") as f:
            f.write("%d %d %d\n" % (size[0], size[1], height))
    except OSError:
        pass


def static_lines(cols, rows=1000):
    """The banner as plain lines of text with colour codes, for printing once."""
    cfg = load_config()
    lay = Layout(rows, cols, cfg)
    if not lay.fits:
        return []
    cells = {}
    draw(lay, THEMES[cfg["THEME"]], cells, None, None)
    out = []
    for r in range(1, lay.height + 1):
        line = "".join(cells.get((r, c), " ") for c in range(1, cols + 1))
        out.append(re.sub(r"(\x1b\[0m )+$", "", line).rstrip() + "\x1b[0m")
    return out


def main(argv):
    mode = argv[1] if len(argv) > 1 else "print"
    if mode == "live":
        Banner(int(argv[2]), argv[3]).run(int(argv[4]))
    elif mode == "height":
        r, c = term_size()[:2]
        print(Layout(r, c, load_config()).height)
    else:
        try:
            cols = term_size()[1]
        except OSError:
            cols = 80
        print("\n".join(static_lines(cols)))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (OSError, KeyboardInterrupt):
        pass

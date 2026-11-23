"""Shared primitives: colour maths, masks, fonts and rich text.

Everything here is pure Pillow so the renderer runs on any OS with Python 3.9+.
"""

from __future__ import annotations

import functools
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RGB = tuple  # (r, g, b)

# ---------------------------------------------------------------- warnings

WARNINGS: list[str] = []


GROUPS: dict[str, list[str]] = {}


def warn(msg: str) -> None:
    if msg not in WARNINGS:
        WARNINGS.append(msg)


def warn_group(template: str, item: str) -> None:
    """One warning for many items: template holds {items}."""
    items = GROUPS.setdefault(template, [])
    if item not in items:
        items.append(item)


def report_warnings() -> None:
    lines = list(WARNINGS) + [t.format(items=", ".join(v)) for t, v in GROUPS.items()]
    if lines:
        print(f"\n{len(lines)} warning(s):")
        for w in lines:
            print("  -", w)


# ---------------------------------------------------------------- colour

def hex_rgb(value) -> RGB:
    """'#FF7A2E' / 'FF7A2E' / '#F72' / [255, 122, 46] -> (255, 122, 46)."""
    if isinstance(value, (list, tuple)):
        return tuple(int(v) for v in value[:3])
    s = str(value).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"colour {value!r}: use #RRGGBB")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(c: RGB) -> str:
    return "#{:02X}{:02X}{:02X}".format(*c[:3])


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(x + (y - x) * t) for x, y in zip(a[:3], b[:3]))


def luminance(c: RGB) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: RGB, b: RGB) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def ensure_contrast(fg: RGB, bg: RGB, target: float = 4.5) -> RGB:
    """Nudge fg toward white (dark bg) or black (light bg) until it reads."""
    goal = (255, 255, 255) if luminance(bg) < 0.4 else (0, 0, 0)
    c = fg
    for i in range(21):
        if contrast(c, bg) >= target:
            return c
        c = mix(fg, goal, i / 20)
    return c


def pixels(img: Image.Image) -> list:
    """Pixel values without the deprecated getdata(): ints for L, tuples for RGB."""
    if img.mode == "L":
        return list(img.tobytes())
    img = img.convert("RGB")
    b = img.tobytes()
    return [tuple(b[i:i + 3]) for i in range(0, len(b), 3)]


def is_dark(c: RGB) -> bool:
    return luminance(c) < 0.4


# ---------------------------------------------------------------- masks

def _ss(size) -> int:
    return 4 if max(size) <= 2400 else 2


@functools.lru_cache(maxsize=256)
def _corner(r: int) -> Image.Image:
    """Top-left quarter of an anti-aliased circle of radius r, as an r x r tile (4x supersampled)."""
    ss = 4
    m = Image.new("L", (r * ss, r * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 2 * r * ss - 1, 2 * r * ss - 1), fill=255)
    return m.resize((r, r), Image.LANCZOS)


@functools.lru_cache(maxsize=256)
def _rr_mask(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 255)
    if r <= 0:
        return m
    c = _corner(r)
    m.paste(c, (0, 0))
    m.paste(c.transpose(Image.FLIP_LEFT_RIGHT), (w - r, 0))
    m.paste(c.transpose(Image.FLIP_TOP_BOTTOM), (0, h - r))
    m.paste(c.transpose(Image.ROTATE_180), (w - r, h - r))
    return m


def rr_mask(size, radius) -> Image.Image:
    """Anti-aliased rounded-rectangle mask.

    Only the four corners are supersampled; the straight edges are exact. Cached, because the
    same device and card sizes repeat on every slide (returns a copy, so callers may mutate it).
    """
    w, h = int(size[0]), int(size[1])
    r = int(round(min(max(0, radius), w / 2, h / 2)))
    return _rr_mask(w, h, r).copy()


def ellipse_mask(size) -> Image.Image:
    w, h = int(size[0]), int(size[1])
    ss = _ss((w, h))
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).ellipse((0, 0, w * ss - 1, h * ss - 1), fill=255)
    return m.resize((w, h), Image.LANCZOS)


def superellipse_mask(size: int, n: float = 5.0) -> Image.Image:
    """Squircle mask, close to Apple's continuous-corner icon shape."""
    ss = 4
    s = size * ss
    m = Image.new("L", (s, s), 0)
    pts = []
    import math

    for i in range(720):
        t = 2 * math.pi * i / 720
        ct, st = math.cos(t), math.sin(t)
        x = abs(ct) ** (2 / n) * (1 if ct >= 0 else -1)
        y = abs(st) ** (2 / n) * (1 if st >= 0 else -1)
        pts.append((s / 2 + x * s / 2, s / 2 + y * s / 2))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    return m.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- fonts

_AXIS_TAGS = {"weight": "wght", "width": "wdth", "optical size": "opsz", "optical_size": "opsz",
              "italic": "ital", "slant": "slnt", "grade": "GRAD"}

_FALLBACKS = {
    False: [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/TTF/Inter-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ],
    True: [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/TTF/Inter-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ],
}


@functools.lru_cache(maxsize=None)
def system_font(bold: bool = False) -> str | None:
    """Best-effort sans-serif from the OS (fontconfig first)."""
    if shutil.which("fc-match"):
        pattern = "sans-serif:weight=bold" if bold else "sans-serif"
        try:
            out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True,
                                 timeout=5).stdout.strip()
            if out and Path(out).exists():
                return out
        except (OSError, subprocess.SubprocessError):
            pass
    for p in _FALLBACKS[bold]:
        if Path(p).exists():
            return p
    return None


@functools.lru_cache(maxsize=512)
def _truetype(path: str, size: int, index: int, axes: tuple, named: str | None):
    f = ImageFont.truetype(path, size, index=index)
    if named:
        try:
            f.set_variation_by_name(named)
        except (OSError, ValueError):
            warn(f"font {Path(path).name}: no named instance {named!r}")
    if axes:
        wanted = dict(axes)
        try:
            values = []
            for a in f.get_variation_axes():
                name = a["name"].decode() if isinstance(a["name"], bytes) else str(a["name"])
                tag = _AXIS_TAGS.get(name.lower(), name[:4].lower())
                values.append(wanted.get(tag, a.get("default", a["minimum"])))
            f.set_variation_by_axes(values)
        except OSError:
            warn(f"font {Path(path).name} is not a variable font; axes {wanted} ignored")
    return f


class Fonts:
    """Resolves the config's font roles: display (headlines), body, body_bold, label (eyebrows)."""

    def __init__(self, spec: dict | None, base: Path):
        self.spec = spec or {}
        self.base = base

    def _resolve(self, role: str):
        s = self.spec.get(role)
        if s is None and role == "label":
            s = self.spec.get("body_bold") or self.spec.get("body")
        if s is None and role == "body_bold":
            s = self.spec.get("body")
            if isinstance(s, dict) and s.get("axes"):
                s = {**s, "axes": {**s["axes"], "wght": 700}}
        if s is None and role == "display":
            s = self.spec.get("body_bold") or self.spec.get("body")
        if isinstance(s, str):
            s = {"path": s}
        if s:
            p = Path(os.path.expanduser(s["path"]))
            if not p.is_absolute():
                p = (self.base / p).resolve()
            if p.exists():
                return str(p), int(s.get("index", 0)), tuple(sorted((s.get("axes") or {}).items())), s.get("named")
            warn(f"font for {role!r} not found: {p}; using a system font")
        bold = role in ("display", "body_bold", "label", "status")
        sys_path = system_font(bold)
        if sys_path:
            axes = (("wght", 800 if role == "display" else 700),) if bold and sys_path.endswith("SFNS.ttf") else ()
            return sys_path, 0, axes, None
        return None

    def get(self, role: str, size: int) -> ImageFont.FreeTypeFont:
        size = max(6, int(round(size)))
        r = self._resolve(role)
        if r is None:
            warn("no TrueType font found; text uses Pillow's default font. Set brand.fonts in the config.")
            return ImageFont.load_default(size)
        path, index, axes, named = r
        return _truetype(path, size, index, axes, named)


# ---------------------------------------------------------------- text

def runs(line: str) -> list[tuple[str, bool]]:
    """'Log a fill-up in *seconds*' -> [('Log a fill-up in ', False), ('seconds', True)]."""
    return [(p, i % 2 == 1) for i, p in enumerate(line.split("*")) if p]


def run_width(font, text: str, track: float) -> float:
    if not text:
        return 0.0
    return font.getlength(text) + (track * (len(text) - 1) if track else 0)


def line_width(font, line: str, track: float) -> float:
    rs = runs(line)
    return sum(run_width(font, t, track) for t, _ in rs) + (track * (len(rs) - 1) if track else 0)


def _ascii(s: str) -> bool:
    return all(ord(c) < 0x2000 for c in s)


def draw_line(d: ImageDraw.ImageDraw, x: float, y: float, line: str, font, color, accent, track: float) -> None:
    for text, hot in runs(line):
        fill = accent if hot else color
        if track and _ascii(text):
            for ch in text:
                d.text((x, y), ch, font=font, fill=fill)
                x += font.getlength(ch) + track
        else:
            d.text((x, y), text, font=font, fill=fill)
            x += run_width(font, text, 0) + (track if track else 0)


def text_block(d, text: str, *, fonts: Fonts, role: str, size: float, x: float, y: float, max_w: float,
               color, accent=None, align: str = "center", lead: float = 1.05, track: float = 0.0,
               min_ratio: float = 0.72, label: str = "text") -> tuple[float, float]:
    """Draw multi-line text (explicit \\n breaks, *accent* runs). Shrinks to fit max_w.

    x is the left edge for align='left', the centre for 'center'. Returns (bottom_y, final_size).
    """
    lines = text.split("\n")
    s = size
    while True:
        f = fonts.get(role, s)
        t = s * track
        widest = max(line_width(f, ln, t) for ln in lines)
        if widest <= max_w or s <= size * min_ratio:
            break
        s *= 0.96
    if widest > max_w:
        warn(f"{label} {text!r} still overflows at {s / size:.0%} size; shorten it or add a line break")
    elif s < size * 0.9:
        warn(f"{label} {text!r} shrunk to {s / size:.0%} to fit; consider a shorter line")
    for ln in lines:
        w = line_width(f, ln, t)
        lx = x - w / 2 if align == "center" else x
        draw_line(d, lx, y, ln, f, color, accent or color, t)
        y += s * lead
    return y, s


def tracked(d, text: str, *, font, cx: float | None, x: float | None, y: float, fill, track: float) -> float:
    """Single-line tracked label (eyebrows). Centred on cx, or left at x. Returns width."""
    w = run_width(font, text, track)
    sx = cx - w / 2 if cx is not None else x
    draw_line(d, sx, y, text.replace("*", ""), font, fill, fill, track)
    return w


def platform_note() -> str:
    return f"Python {sys.version.split()[0]}, Pillow {Image.__version__}"

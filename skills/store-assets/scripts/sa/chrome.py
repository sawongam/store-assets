"""Capture cleaning: system bars out, a calm 9:41 status bar in.

A raw capture keeps whatever the device showed: carrier, notifications, a
no-data "!", a gesture handle. Stores want a clean, full status bar. Each
capture is turned into a Screen for one platform:

* android -> android  repaint the status band and the nav/gesture band
* ios     -> ios      keep (simctl status_bar override) or repaint
* android -> ios      "re-chrome": Android bars out, iOS status bar and home
                      indicator in, refit to the iPhone/iPad screen aspect

Every Screen carries map_y so callout boxes given in raw capture pixels still
land on the right content after the shift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PIL import Image, ImageDraw

from . import core


@dataclass
class Screen:
    img: Image.Image
    platform: str  # android | ios
    kind: str  # phone | tablet
    map_y: Callable[[float], float] = field(default=lambda y: y)
    source: str = ""


# ---------------------------------------------------------------- helpers

def _fill_from_row(img: Image.Image, row: int, y0: int, y1: int) -> None:
    """Stretch one clean row over [y0, y1)."""
    if y1 <= y0:
        return
    row = max(0, min(img.height - 1, row))
    img.paste(img.crop((0, row, img.width, row + 1)).resize((img.width, y1 - y0)), (0, y0))


def _centre_ink(img: Image.Image, y: int) -> bool:
    """True when row y has dark ink in its middle third: the tail of a punch-hole, notch or Dynamic Island."""
    g = img.convert("L").crop((img.width // 3, y, img.width * 2 // 3, y + 1))
    vals = core.pixels(g)
    base = sorted(vals)[len(vals) // 2]
    return sum(1 for v in vals if base - v > 40) > 2


def _clean_status_row(img: Image.Image, status_px: int, source: str = "") -> int:
    """The row to stretch over the status band: status_px, or the first row below it clear of a camera cut-out.

    Stretching a row that still holds the bottom of a punch-hole smears it into a
    vertical stem across the band, so a band set a few pixels short is extended
    instead, by at most 1.2% of the capture height so app content is never swallowed.
    """
    limit = min(img.height - 1, status_px + max(8, round(img.height * 0.012)))
    y = status_px
    while y < limit and _centre_ink(img, y):
        y += 1
    if y != status_px:
        core.warn_group("status_bar_px stops inside the camera cut-out ({items}); band extended to {px}px. "
                        "Set status_bar_px to {px} or more.".replace("{px}", str(y)), source)
    return y


def _band_fg(img: Image.Image, y0: int, y1: int, dark=(30, 30, 34), light=(255, 255, 255)):
    band = img.crop((0, max(0, y0), img.width, max(y0 + 1, y1))).resize((32, 4))
    px = core.pixels(band)
    avg = tuple(sum(p[i] for p in px) / len(px) for i in range(3))
    return dark if core.luminance(avg) > 0.45 else light


def _status_font(fonts, size):
    return fonts.get("status", size) if fonts else core.ImageFont.load_default(size)


# ---------------------------------------------------------------- android status bar

def draw_android_status(img: Image.Image, band_h: int, kind: str, fonts, density: float) -> None:
    d = ImageDraw.Draw(img)
    fg = _band_fg(img, 0, band_h, dark=(60, 60, 67))
    dp = density
    w = img.width
    if kind == "tablet":
        cy = min(band_h / 2, 12 * dp)
        tsize, margin, bat_w, bat_h = 13 * dp, 16 * dp, 6.5 * dp, 12 * dp
        sig, wifi = 11 * dp, 15 * dp
    else:
        cy = min(band_h / 2, 24.5 * dp)
        tsize, margin, bat_w, bat_h = 14.5 * dp, 28 * dp, 8.4 * dp, 16 * dp
        sig, wifi = 13.7 * dp, 18.3 * dp
    d.text((margin, cy), "9:41", font=_status_font(fonts, tsize), fill=fg, anchor="lm")
    bx = w - margin - bat_w - 2 * dp
    d.rounded_rectangle((bx, cy - bat_h / 2, bx + bat_w, cy + bat_h / 2), max(1, 1.5 * dp), fill=fg)
    d.rectangle((bx + bat_w * 0.27, cy - bat_h / 2 - 1.5 * dp, bx + bat_w * 0.73, cy - bat_h / 2), fill=fg)
    sx = bx - 8 * dp - sig
    d.polygon([(sx, cy + sig / 2), (sx + sig, cy + sig / 2), (sx + sig, cy - sig / 2)], fill=fg)
    wx = sx - 7 * dp - wifi
    d.pieslice((wx, cy - wifi * 0.46, wx + wifi, cy + wifi * 0.54 + wifi * 0.08), 225, 315, fill=fg)


# ---------------------------------------------------------------- iOS status bar

def ios_metrics(w: int, kind: str) -> dict:
    """Points -> pixels for an iPhone (Dynamic Island) or iPad screen of width w."""
    if kind == "tablet":
        pt = w / 1032
        return dict(pt=pt, top=round(24 * pt), cy=12 * pt, time=12.5 * pt, margin=22 * pt,
                    home_w=320 * pt, home_h=5 * pt, home_bottom=8 * pt, bottom=round(20 * pt))
    pt = w / 420
    return dict(pt=pt, top=round(62 * pt), cy=30 * pt, time=17 * pt, margin=0,
                home_w=139 * pt, home_h=5 * pt, home_bottom=8 * pt, bottom=round(34 * pt))


def draw_ios_status(img: Image.Image, kind: str, fonts) -> None:
    m = ios_metrics(img.width, kind)
    pt, cy = m["pt"], m["cy"]
    d = ImageDraw.Draw(img)
    fg = _band_fg(img, 0, m["top"], dark=(0, 0, 0))
    w = img.width
    f = _status_font(fonts, m["time"])
    if kind == "tablet":
        d.text((m["margin"], cy), "9:41", font=f, fill=fg, anchor="lm")
        right = w - m["margin"]
    else:
        d.text((w * 0.185, cy), "9:41", font=f, fill=fg, anchor="mm")
        right = w * 0.93  # right ear
    # battery: outline, fill, nub
    bw, bh = 25 * pt, 12 * pt
    bx = right - bw - 2.5 * pt
    d.rounded_rectangle((bx, cy - bh / 2, bx + bw, cy + bh / 2), 3.6 * pt, outline=fg, width=max(1, round(1 * pt)))
    d.rounded_rectangle((bx + 2 * pt, cy - bh / 2 + 2 * pt, bx + bw - 2 * pt, cy + bh / 2 - 2 * pt), 2 * pt, fill=fg)
    d.rounded_rectangle((bx + bw + 1 * pt, cy - 2 * pt, bx + bw + 2.5 * pt, cy + 2 * pt), 1 * pt, fill=fg)
    # wifi: three arcs
    wx = bx - 6 * pt - 17 * pt
    for i, r in enumerate((8.5, 5.6, 2.8)):
        rr = r * pt * 2
        x0 = wx + 8.5 * pt - rr / 2
        y0 = cy + 5 * pt - rr / 2
        if i < 2:
            d.arc((x0, y0, x0 + rr, y0 + rr), 225, 315, fill=fg, width=max(1, round(2 * pt)))
        else:
            d.pieslice((x0, y0, x0 + rr, y0 + rr), 225, 315, fill=fg)
    # signal: four bars
    sx = wx - 6 * pt - 18 * pt
    for i in range(4):
        bar_h = (4 + i * 2.6) * pt
        x = sx + i * 4.6 * pt
        d.rounded_rectangle((x, cy + 5.5 * pt - bar_h, x + 3 * pt, cy + 5.5 * pt), 1 * pt, fill=fg)


def draw_home_indicator(img: Image.Image, kind: str) -> None:
    m = ios_metrics(img.width, kind)
    h = img.height
    fg = _band_fg(img, h - m["bottom"], h, dark=(0, 0, 0), light=(255, 255, 255))
    w = img.width
    y1 = h - m["home_bottom"]
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(((w - m["home_w"]) / 2, y1 - m["home_h"], (w + m["home_w"]) / 2, y1), m["home_h"] / 2,
                        fill=fg)


# ---------------------------------------------------------------- public

def make_screen(raw: Image.Image, *, src_platform: str, kind: str, target_platform: str, target_aspect: float | None,
                status_px: int, nav_px: int, mode: str, fonts, density: float | None, source: str = "") -> Screen:
    """Clean one capture for one target platform.

    mode: 'repaint' (default for Android) or 'keep' (bars already clean, e.g. simctl override).
    target_aspect: width / height of the target device screen; only used when re-chroming to iOS.
    """
    img = raw.convert("RGB")
    w, h = img.size
    if density is None:
        density = w / (800 if kind == "tablet" else 411)

    if target_platform == src_platform:
        if mode == "keep":
            return Screen(img, target_platform, kind, source=source)
        img = img.copy()
        if src_platform == "android":
            status_px = _clean_status_row(img, status_px, source)
            _fill_from_row(img, status_px, 0, status_px)
            if nav_px:
                _fill_from_row(img, h - nav_px - 1, h - nav_px, h)
            draw_android_status(img, status_px, kind, fonts, density)
        else:
            m = ios_metrics(w, kind)
            _fill_from_row(img, max(status_px, m["top"]), 0, max(status_px, m["top"]))
            draw_ios_status(img, kind, fonts)
        return Screen(img, target_platform, kind, source=source)

    if src_platform == "android" and target_platform == "ios":
        return _rechrome_to_ios(img, kind, target_aspect or (w / h), status_px, nav_px, fonts, source)

    raise ValueError(f"cannot turn a {src_platform} capture into a {target_platform} screen; capture it on "
                     f"{target_platform} instead")


def _rechrome_to_ios(img, kind, aspect, status_px, nav_px, fonts, source) -> Screen:
    w, h = img.size
    m = ios_metrics(w, kind)
    target_h = round(w / aspect)
    content = img.crop((0, status_px, w, h - nav_px))
    top, bottom = m["top"], m["bottom"]
    need = top + content.height + bottom
    # Too tall: shrink the iOS top band toward the Android one, then the bottom band, then crop content.
    if need > target_h:
        give = min(need - target_h, max(0, top - max(status_px, round(top * 0.8))))
        top -= give
        need -= give
    if need > target_h:
        give = min(need - target_h, bottom)
        bottom -= give
        need -= give
    cut = max(0, need - target_h)
    if cut:
        pct = cut / content.height
        if pct > 0.02:
            core.warn_group("iOS screens cut at the bottom because the Android capture is taller than the iOS screen "
                            "({items}). Capture at the iOS aspect instead: capture.sh android-size iphone|ipad.",
                            f"{source} {pct:.0%}")
        content = content.crop((0, 0, w, content.height - cut))
    extra = target_h - (top + content.height + bottom)
    # Too short: grow the top band to the full iOS height, then extend the bottom.
    if extra > 0:
        grow = min(extra, ios_metrics(w, kind)["top"] - top)
        top += grow
        bottom += extra - grow
    out = Image.new("RGB", (w, target_h))
    _fill_band = content.crop((0, 0, w, 1)).resize((w, max(1, top)))
    out.paste(_fill_band, (0, 0))
    out.paste(content, (0, top))
    if bottom > 0:
        out.paste(content.crop((0, content.height - 1, w, content.height)).resize((w, bottom)),
                  (0, top + content.height))
    draw_ios_status(out, kind, fonts)
    draw_home_indicator(out, kind)
    shift = top - status_px
    core.warn_group("iOS screens made from Android captures ({items}): Android bars replaced by an iOS status bar "
                    "and home indicator. Look at each for Android-only UI (back arrows, Material switches/pickers, "
                    "snackbars, share sheets) before uploading to the App Store.", source)
    return Screen(out, "ios", kind, map_y=lambda y, s=shift: y + s, source=source)


# ---------------------------------------------------------------- bar detection (a hint, not a truth)

def suggest_bars(img: Image.Image) -> tuple[int, int]:
    """Guess (status_px, nav_px) from where the top/bottom glyph rows end.

    Looks for ink in the status-bar side zones (time at left, icons at right),
    for a camera cut-out in the top centre (it often reaches lower than the
    glyphs), and for a pill/buttons in the bottom centre. A hint for inspect_capture.py.
    """
    g = img.convert("L")
    w, h = g.size

    def ink(y, x0, x1):
        vals = core.pixels(g.crop((int(x0), y, int(x1), y + 1)))
        base = sorted(vals)[len(vals) // 2]
        return sum(1 for v in vals if abs(v - base) > 40) > 2

    def glyph(y, x0, x1, from_left):
        """Ink in a status-bar zone, ignoring ink joined to the screen edge (rounded corners, borders)."""
        vals = core.pixels(g.crop((int(x0), y, int(x1), y + 1)))
        base = sorted(vals)[len(vals) // 2]
        on = [abs(v - base) > 40 for v in vals]
        if not from_left:
            on.reverse()
        i = 0
        while i < len(on) and on[i]:  # skip the run touching the edge
            i += 1
        return sum(on[i:]) > 2

    last = 0
    limit = int(h * 0.09)
    gap = 0
    for y in range(0, limit):
        if glyph(y, 0, w * 0.3, from_left=True) or glyph(y, w * 0.6, w, from_left=False) \
                or (last and ink(y, w * 0.35, w * 0.65)):
            last, gap = y, 0
        else:
            gap += 1
            if last and gap > h * 0.006:
                break
    status = min(limit, last + max(4, round(h * 0.006))) if last else round(h * 0.04)

    first = h
    gap = 0
    for y in range(h - 1, int(h * 0.92), -1):
        if ink(y, w * 0.3, w * 0.7):
            first, gap = y, 0
        else:
            gap += 1
            if first < h and gap > h * 0.008:
                break
    nav = h - first + max(4, round(h * 0.004)) if first < h else 0
    # 3-button navigation: a row in the bottom ~48dp crossing exactly three glyphs, spread across the width
    band = round(48 * w / 411)
    for y in range(h - band, h):
        row = core.pixels(g.crop((0, y, w, y + 1)))
        base = sorted(row)[len(row) // 2]
        on = [abs(v - base) > 40 for v in row]
        runs, x = [], 0
        while x < w:
            if on[x]:
                x0 = x
                while x < w and on[x]:
                    x += 1
                if x - x0 >= 2 and x0 > w * 0.05 and x < w * 0.95:  # skip rounded-corner black at the edges
                    runs.append((x0 + x) / 2)
            x += 1
        clusters = []
        for cx in runs:  # merge runs belonging to one glyph
            if clusters and cx - clusters[-1][-1] < w * 0.06:
                clusters[-1].append(cx)
            else:
                clusters.append([cx])
        if len(clusters) == 3 and clusters[0][0] < w * 0.4 and clusters[-1][-1] > w * 0.6 \
                and clusters[1][0] > w * 0.4 and clusters[1][-1] < w * 0.6:
            return status, max(nav, band)
    return status, nav

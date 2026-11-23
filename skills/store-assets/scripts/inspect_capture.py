#!/usr/bin/env python3
"""Measure a capture's system bars so render.py can clean them.

    python3 inspect_capture.py raw/phone/*.png [--out store-assets/out/_review/bars.png]

Prints each capture's size and a guessed status_bar_px / nav_bar_px, and writes
one guide image: the top and bottom bands of every capture, enlarged, with a
ruler every 10px and the guesses drawn in red. Look at the guide and set the
numbers in config.captures.<set> yourself: the guess is a heuristic.

status_bar_px  rows from the top to repaint (status bar, notch/cut-out band)
nav_bar_px     rows from the bottom to repaint (gesture handle or 3-button bar)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sa  # noqa: E402,F401  (checks Python and Pillow first)
from PIL import Image, ImageDraw  # noqa: E402

from sa import chrome, core  # noqa: E402


def band(img: Image.Image, y0: int, y1: int, status: int | None, nav: int | None, width: int, font) -> Image.Image:
    crop = img.crop((0, y0, img.width, y1))
    k = width / img.width * 2.0
    crop = crop.resize((round(img.width * k), round((y1 - y0) * k)), Image.LANCZOS)
    out = Image.new("RGB", (crop.width + 70, crop.height), (40, 40, 44))
    out.paste(crop, (70, 0))
    d = ImageDraw.Draw(out)
    for y in range(y0 - y0 % 10, y1, 10):
        if y < y0:
            continue
        yy = (y - y0) * k
        major = y % 50 == 0
        d.line((70 if not major else 40, yy, out.width if major else 90, yy), fill=(0, 255, 200) if major else
               (120, 200, 190), width=1)
        if major:
            d.text((2, yy - 7), str(y), font=font, fill=(255, 255, 255))
    for mark, colour in ((status, (255, 40, 60)), (nav, (255, 40, 60))):
        if mark is not None and y0 <= mark <= y1:
            yy = (mark - y0) * k
            d.line((40, yy, out.width, yy), fill=colour, width=3)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captures", nargs="+")
    ap.add_argument("--out", default="store-assets/out/_review/bars.png")
    args = ap.parse_args(argv)
    font = core.Fonts({}, Path(".")).get("body", 14)
    columns = []
    sizes = set()
    guesses: dict = {}
    for p in args.captures:
        img = Image.open(p).convert("RGB")
        w, h = img.size
        sizes.add((w, h))
        s, n = chrome.suggest_bars(img)
        guesses.setdefault((w, h), []).append((s, n))
        print(f"{Path(p).name}: {w}x{h}  guess status_bar_px={s} nav_bar_px={n}")
        top = band(img, 0, min(h, max(s + 60, round(h * 0.09))), s, None, 360, font)
        bot_y0 = max(0, min(h - n - 60, round(h * 0.93)))
        bottom = band(img, bot_y0, h, None, h - n, 360, font)
        col = Image.new("RGB", (max(top.width, bottom.width), top.height + bottom.height + 50), (24, 24, 26))
        ImageDraw.Draw(col).text((6, 4), Path(p).name[:40], font=font, fill=(255, 255, 255))
        col.paste(top, (0, 24))
        col.paste(bottom, (0, 24 + top.height + 26))
        columns.append(col)
    for (w, h), gs in guesses.items():
        if len(gs) > 1:
            ms = sorted(g[0] for g in gs)[len(gs) // 2]
            mn = sorted(g[1] for g in gs)[len(gs) // 2]
            print(f"suggested for the {w}x{h} set (median of {len(gs)}): status_bar_px={ms} nav_bar_px={mn}")
    if len(sizes) > 1:
        print("note: captures in this set have different sizes:", sorted(sizes), "— keep one size per set")
    gap = 16
    sheet = Image.new("RGB", (sum(c.width for c in columns) + gap * (len(columns) + 1),
                              max(c.height for c in columns) + 2 * gap), (90, 90, 96))
    x = gap
    for c in columns:
        sheet.paste(c, (x, gap))
        x += c.width + gap
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("guide:", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())

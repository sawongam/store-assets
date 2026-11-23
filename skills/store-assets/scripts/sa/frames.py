"""Device frames drawn in code (no vendor artwork, so no licensing strings).

android-phone   graphite rim, black bezel, punch-hole camera, keys on the right
android-tablet  even bezel, camera centred in the top bezel
iphone          thin bezel, Dynamic Island, keys on both sides
ipad            even thin bezel, camera on the long (right) edge
none            no device: the screen as a rounded card with a hairline edge

Every frame scales from the screen width, so any capture size works.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

from . import core

FINISHES = {
    "graphite": ((84, 84, 92), (40, 40, 45)),
    "black": ((46, 46, 50), (14, 14, 16)),
    "silver": ((222, 222, 228), (164, 164, 172)),
    "titanium": ((150, 146, 140), (92, 89, 85)),
}

# fractions of the screen width
GEOMETRY = {
    "android-phone": dict(bezel=0.024, rim=0.0093, screen_r=0.111, outer_extra=0, keys="right"),
    "android-tablet": dict(bezel=0.040, rim=0.0075, screen_r=0.021, outer_r=0.074, keys=None),
    "iphone": dict(bezel=0.019, rim=0.010, screen_r=0.137, keys="both"),
    "ipad": dict(bezel=0.027, rim=0.006, screen_r=0.019, outer_r=0.05, keys=None),
    "none": dict(bezel=0, rim=0, screen_r=0.06, keys=None),
}


@dataclass
class Framed:
    img: Image.Image  # RGBA
    sx: int  # screen origin inside img
    sy: int
    k: float  # framed screen px per Screen px


def finish(style) -> tuple:
    if isinstance(style, str) and style in FINISHES:
        return FINISHES[style]
    c = core.hex_rgb(style)
    return core.mix(c, (255, 255, 255), 0.18), core.mix(c, (0, 0, 0), 0.35)


def height_ratio(screen_size, device: str) -> float:
    """framed height / screen width, to size a device before building it."""
    g = GEOMETRY[device]
    sw, sh = screen_size
    return sh / sw + 2 * (g["bezel"] + g["rim"])


def width_ratio(device: str) -> float:
    g = GEOMETRY[device]
    keys = 0.0074 * (2 if g["keys"] == "both" else 1 if g["keys"] else 0)
    return 1 + 2 * (g["bezel"] + g["rim"]) + keys


def _rim(size, radius, colors, k_hl):
    top, bottom = colors
    w, h = size
    rim = Image.new("RGBA", (w, h), top + (255,))
    rim.paste(bottom + (255,), (0, 0), Image.linear_gradient("L").resize((w, h)))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(rim, (0, 0), core.rr_mask((w, h), radius))
    hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle((1, 1, w - 2, h - 2), radius, outline=(255, 255, 255, 46),
                                         width=max(1, round(k_hl)))
    out.alpha_composite(hl)
    return out


def _sheen(img, sx, sy, sw, sh, r, strength=18):
    sheen = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sheen).polygon([(sx, sy), (sx + sw * 0.6, sy), (sx, sy + sh * 0.4)],
                                  fill=(255, 255, 255, strength))
    sheen = sheen.filter(ImageFilter.GaussianBlur(max(1, sw * 0.1)))
    mask = Image.new("L", img.size, 0)
    mask.paste(core.rr_mask((sw, sh), r), (sx, sy))
    sheen.putalpha(Image.composite(sheen.getchannel("A"), Image.new("L", img.size, 0), mask))
    return Image.alpha_composite(img, sheen)


def build(screen: Image.Image, device: str, screen_w: int, style="graphite", dark_canvas=True) -> Framed:
    g = GEOMETRY[device]
    k = screen_w / screen.width
    sw, sh = screen_w, round(screen.height * k)
    scr = screen.convert("RGB").resize((sw, sh), Image.LANCZOS)
    scr_r = round(g["screen_r"] * sw)

    if device == "none":
        pad = max(2, round(sw * 0.004))
        img = Image.new("RGBA", (sw + 2 * pad, sh + 2 * pad), (0, 0, 0, 0))
        edge = (255, 255, 255, 40) if dark_canvas else (0, 0, 0, 26)
        img.paste(edge, (0, 0), core.rr_mask(img.size, scr_r + pad))
        img.paste(scr, (pad, pad), core.rr_mask((sw, sh), scr_r))
        return Framed(img, pad, pad, k)

    colors = finish(style)
    bezel = max(2, round(g["bezel"] * sw))
    rim = max(2, round(g["rim"] * sw))
    body_w, body_h = sw + 2 * (bezel + rim), sh + 2 * (bezel + rim)
    outer_r = round(g["outer_r"] * sw) if "outer_r" in g else scr_r + bezel + rim
    key_w = max(2, round(0.0074 * sw)) if g["keys"] else 0
    left = key_w if g["keys"] == "both" else 0
    img = Image.new("RGBA", (body_w + key_w + left, body_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    key_fill = core.mix(colors[0], colors[1], 0.4) + (255,)
    kr = max(1, round(0.004 * sw))

    # side keys sit behind the rim
    if device == "android-phone":
        kx = left + body_w - rim
        for y, hh in ((0.20, 0.09), (0.32, 0.06)):
            d.rounded_rectangle((kx, body_h * y, kx + rim + key_w, body_h * (y + hh)), kr, fill=key_fill)
    elif device == "iphone":
        kx = left + body_w - rim
        d.rounded_rectangle((kx, body_h * 0.255, kx + rim + key_w, body_h * 0.355), kr, fill=key_fill)
        for y, hh in ((0.175, 0.035), (0.245, 0.06), (0.325, 0.06)):
            d.rounded_rectangle((0, body_h * y, left + rim, body_h * (y + hh)), kr, fill=key_fill)

    img.alpha_composite(_rim((body_w, body_h), outer_r, colors, 2 * sw / 1080), (left, 0))
    inner_r = max(scr_r + bezel, outer_r - rim)
    img.paste((10, 10, 12, 255), (left + rim, rim), core.rr_mask((body_w - 2 * rim, body_h - 2 * rim), inner_r))
    sx, sy = left + rim + bezel, rim + bezel
    img.paste(scr, (sx, sy), core.rr_mask((sw, sh), scr_r))

    d = ImageDraw.Draw(img)
    if device == "android-phone":
        cr = 0.0273 * sw
        cx, cy = sx + sw / 2, sy + 0.06 * sw
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=(6, 6, 8))
        d.ellipse((cx - cr / 2.6, cy - cr / 2.6, cx + cr / 2.6, cy + cr / 2.6), fill=(28, 30, 40))
    elif device == "iphone":
        iw, ih = 0.30 * sw, 0.088 * sw
        ix, iy = sx + (sw - iw) / 2, sy + 0.027 * sw
        d.rounded_rectangle((ix, iy, ix + iw, iy + ih), ih / 2, fill=(0, 0, 0))
        cr = ih * 0.22
        ccx, ccy = ix + iw - ih / 2, iy + ih / 2
        d.ellipse((ccx - cr, ccy - cr, ccx + cr, ccy + cr), fill=(18, 20, 30))
    elif device == "android-tablet":
        cr = 0.011 * sw
        cx, cy = left + body_w / 2, rim + bezel / 2
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=(24, 24, 28))
        d.ellipse((cx - cr / 2.4, cy - cr / 2.4, cx + cr / 2.4, cy + cr / 2.4), fill=(34, 38, 52))
    elif device == "ipad":
        cr = 0.0055 * sw
        cx, cy = left + body_w - rim - bezel / 2, rim + body_h / 2 - rim
        d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill=(26, 26, 30))

    img = _sheen(img, sx, sy, sw, sh, scr_r, 16 if device.endswith("tablet") or device == "ipad" else 18)
    return Framed(img, sx, sy, k)

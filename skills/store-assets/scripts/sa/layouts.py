"""Slide layouts: hero, feature, closing, and the landscape banner.

All sizes are written for a 1080-wide portrait canvas and scaled by
u = W / 1080, so one design serves Play phones, iPhones, tablets and iPads.
Each layout measures first, then centres its content vertically, so taller
canvases (iPhone 19.5:9) get balanced space instead of an empty bottom.
"""

from __future__ import annotations

import functools
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from . import core, frames

# ---------------------------------------------------------------- theme


def resolve_theme(brand: dict) -> dict:
    mode = brand.get("theme", "dark")
    accent = core.hex_rgb(brand.get("accent", "#3B82F6"))
    white, black = (255, 255, 255), (0, 0, 0)
    if mode == "light":
        t = dict(bg=(core.mix((250, 250, 251), accent, 0.04), core.mix((234, 234, 239), accent, 0.07)),
                 text=(17, 17, 20), muted=(91, 91, 102), glow=(255, 255, 255), glow_a=110,
                 card=(255, 255, 255), card_edge=(0, 0, 0, 22), shadow=0.30, grain=0.012, frame="graphite")
    elif mode == "brand":
        t = dict(bg=(core.mix(accent, white, 0.10), core.mix(accent, black, 0.30)),
                 text=white, muted=core.mix(white, accent, 0.28), glow=white, glow_a=45,
                 card=core.mix(accent, black, 0.55), card_edge=(255, 255, 255, 60), shadow=0.55, grain=0.02,
                 frame="graphite")
    else:
        mode = "dark"
        t = dict(bg=((0x1B, 0x1C, 0x20), (0x08, 0x08, 0x0A)), text=white, muted=(161, 161, 170),
                 glow=(244, 244, 248), glow_a=60, card=(24, 24, 27), card_edge=(255, 255, 255, 30), shadow=0.8,
                 grain=0.02, frame="graphite")
    t["mode"] = mode
    if brand.get("background"):
        bg = brand["background"]
        t["bg"] = (core.hex_rgb(bg[0]), core.hex_rgb(bg[1] if len(bg) > 1 else bg[0]))
    for key in ("text", "muted", "glow"):
        if brand.get(key):
            t[key] = core.hex_rgb(brand[key])
    mid = core.mix(*t["bg"], 0.4)
    t["dark"] = core.is_dark(mid)
    if mode == "brand":
        default_hi = (255, 228, 150) if t["dark"] else (17, 17, 20)
        t["accent"] = core.hex_rgb(brand["highlight"]) if brand.get("highlight") else default_hi
    else:
        t["accent"] = core.ensure_contrast(accent, mid, 3.0)
    t["check"] = core.hex_rgb(brand.get("check", core.to_hex(accent)))
    t["frame"] = brand.get("frame", t["frame"])
    return t


# ---------------------------------------------------------------- canvas pieces


def comp(canvas, img, x, y):
    """alpha_composite that tolerates negative offsets (Pillow refuses them)."""
    x, y = round(x), round(y)
    if x < 0 or y < 0:
        img = img.crop((max(0, -x), max(0, -y), img.width, img.height))
        x, y = max(0, x), max(0, y)
    if img.width > 0 and img.height > 0 and x < canvas.width and y < canvas.height:
        canvas.alpha_composite(img, (x, y))


@functools.lru_cache(maxsize=1)
def _noise_tile(n: int = 256) -> Image.Image:
    """Seeded Gaussian grain. Image.effect_noise draws from C rand(), so its output depends on what
    rendered before it in the process; a fixed seed keeps one slide identical in full and partial runs."""
    rnd = random.Random(941)
    return Image.frombytes("L", (n, n), bytes(max(0, min(255, round(rnd.gauss(128, 40)))) for _ in range(n * n)))


@functools.lru_cache(maxsize=16)
def _background(W: int, H: int, top: tuple, bottom: tuple, grain: float) -> Image.Image:
    g = Image.new("RGB", (1, 256))
    for y in range(256):
        t = (y / 255) ** 0.8
        g.putpixel((0, y), core.mix(top, bottom, t))
    img = g.resize((W, H), Image.BICUBIC)
    if grain:
        tile = _noise_tile()
        noise = Image.new("L", (W, H))
        for y in range(0, H, tile.height):
            for x in range(0, W, tile.width):
                noise.paste(tile, (x, y))
        img = Image.blend(img, noise.convert("RGB"), grain)
    return img.convert("RGBA")


def background(ctx) -> Image.Image:
    """Theme gradient plus grain. Cached per size: every slide of a target shares it."""
    top, bottom = ctx.theme["bg"]
    return _background(ctx.W, ctx.H, tuple(top), tuple(bottom), ctx.theme["grain"]).copy()


def glow(ctx, canvas, cx, cy, rx, ry, alpha=None, color=None):
    alpha = ctx.theme["glow_a"] if alpha is None else alpha
    if alpha <= 0:
        return
    color = color or ctx.theme["glow"]
    q = 4
    W, H = canvas.size
    layer = Image.new("RGBA", (max(1, W // q), max(1, H // q)), tuple(color) + (0,))
    m = Image.new("L", layer.size, 0)
    ImageDraw.Draw(m).ellipse(((cx - rx) / q, (cy - ry) / q, (cx + rx) / q, (cy + ry) / q), fill=int(alpha))
    layer.putalpha(m.filter(ImageFilter.GaussianBlur(max(1, min(rx, ry) / q * 0.6))))
    canvas.alpha_composite(layer.resize((W, H), Image.BICUBIC))


def place(ctx, canvas, img, cx, cy, angle=0.0, shadow=None):
    """Drop a framed device (RGBA) centred on (cx, cy) with a soft shadow. Returns its unrotated top-left."""
    shadow = ctx.theme["shadow"] if shadow is None else shadow * ctx.theme["shadow"] / 0.8
    x0, y0 = round(cx - img.width / 2), round(cy - img.height / 2)
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    u = ctx.u
    pad = round(140 * u)
    sh = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 255), (pad, pad), img.getchannel("A").point(lambda v: v * shadow))
    sh = soft_blur(sh, max(1, 46 * u))
    comp(canvas, sh, cx - sh.width / 2, cy - sh.height / 2 + 44 * u)
    comp(canvas, img, cx - img.width / 2, cy - img.height / 2)
    return x0, y0


def soft_blur(img, radius):
    """Gaussian blur for wide, soft shadows: blurred at reduced size and scaled back, ~10x cheaper
    and indistinguishable at these radii."""
    q = max(1, min(4, int(radius // 6)))
    if q == 1:
        return img.filter(ImageFilter.GaussianBlur(radius))
    small = img.resize((max(1, img.width // q), max(1, img.height // q)), Image.BILINEAR)
    return small.filter(ImageFilter.GaussianBlur(radius / q)).resize(img.size, Image.BICUBIC)


def drop_shadow(canvas, mask, x, y, alpha, blur):
    """Blurred black copy of mask at (x, y). Blurs only the area around it, not the whole canvas."""
    pad = round(blur * 3) + 2
    sh = Image.new("RGBA", (mask.width + 2 * pad, mask.height + 2 * pad), (0, 0, 0, 0))
    sh.paste((0, 0, 0, alpha), (pad, pad), mask)
    comp(canvas, soft_blur(sh, blur), x - pad, y - pad)


def paste_icon(ctx, canvas, size, x, y, radius_ratio=0.2275, shadow=False):
    icon = ctx.icon(size)
    if icon is None:
        return False
    mask = core.rr_mask(icon.size, size * radius_ratio)
    if shadow:
        drop_shadow(canvas, mask, round(x), round(y + 26 * ctx.u), round(230 * ctx.theme["shadow"] / 0.8),
                    max(1, 30 * ctx.u))
    canvas.paste(icon, (round(x), round(y)), mask)
    return True


def device_for(ctx, key, max_screen_w, max_h, scale=1.0, frame=None):
    """Build the target's device frame around capture `key`, as large as fits.

    frame: per-slide override: 'none' for a frameless screen card, or a finish (graphite, silver, #hex).
    """
    screen = ctx.screen(key)
    device = "none" if frame == "none" else ctx.device
    style = frame if frame and frame != "none" else ctx.theme["frame"]
    r = frames.height_ratio(screen.img.size, device)
    wr = frames.width_ratio(device)
    sw = min(max_screen_w, max_h / r, ctx.W * 0.98 / wr) * scale
    return frames.build(screen.img, device, max(40, round(sw)), style, ctx.theme["dark"]), screen


def callout(ctx, canvas, screen, box, width, cy):
    """Lift a region of the cleaned screen out of the device, enlarged, centred."""
    x0, y0, x1, y1 = box
    y0m, y1m = screen.map_y(y0), screen.map_y(y1)
    W = ctx.W
    sw, sh = screen.img.size
    crop = (max(0, int(x0)), max(0, int(y0m)), min(sw, int(x1)), min(sh, int(y1m)))
    if crop[2] - crop[0] < 4 or crop[3] - crop[1] < 4:
        core.warn(f"callout {box} falls outside {screen.source}; skipped")
        return
    part = screen.img.crop(crop)
    width = min(width, round(W * 0.92))
    h = round(width * part.height / part.width)
    part = part.resize((width, h), Image.LANCZOS)
    u = ctx.u
    r, pad = round(34 * u), round(10 * u)
    t = ctx.theme
    card = Image.new("RGBA", (width + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    edge = (255, 255, 255, 50) if t["dark"] else (0, 0, 0, 30)
    card.paste(edge, (0, 0), core.rr_mask(card.size, r + pad))
    card.paste(t["card"] + (255,), (pad - 2, pad - 2), core.rr_mask((width + 4, h + 4), r + 2))
    card.paste(part, (pad, pad), core.rr_mask(part.size, r))
    x = (W - card.width) // 2
    y = round(cy - card.height / 2)
    y = max(round(40 * u), min(ctx.H - card.height - round(40 * u), y))
    drop_shadow(canvas, core.rr_mask(card.size, r + pad), x, y + round(34 * u), round(210 * t["shadow"] / 0.8),
                max(1, 34 * u))
    canvas.alpha_composite(card, (x, y))


def _lines(text: str | None) -> int:
    return len(text.split("\n")) if text else 0


# ---------------------------------------------------------------- layouts


def feature(ctx, s: dict) -> Image.Image:
    u, W, H, t = ctx.u, ctx.W, ctx.H, ctx.theme
    eyebrow, title, body = ctx.text(s.get("eyebrow")), ctx.text(s.get("headline")), ctx.text(s.get("body"))
    hs = s.get("headline_size", 88) * u
    text_h = (58 * u if eyebrow else 0) + _lines(title) * hs * 1.04 + (_lines(body) * 38 * u * 1.3 + 22 * u if body else 0)
    gap, top_min, bottom = 70 * u, 120 * u, 64 * u
    tablet = ctx.kind == "tablet"
    max_sw = W * (0.736 if tablet else 0.556) * s.get("device_scale", 1.0)
    avail = H - top_min - text_h - gap - bottom
    dev, screen = device_for(ctx, s["capture"], max_sw, avail, frame=s.get("frame"))
    slack = max(0, avail - dev.img.height)
    top = top_min + slack * 0.42
    dev_top = top + text_h + gap

    c = background(ctx)
    cy = dev_top + dev.img.height / 2
    glow(ctx, c, W / 2, cy, W * 0.52, dev.img.height * 0.6)
    d = ImageDraw.Draw(c)
    y = top
    if eyebrow:
        core.tracked(d, eyebrow, font=ctx.fonts.get("label", 28 * u), cx=W / 2, x=None, y=y, fill=t["accent"],
                     track=6 * u)
        y += 58 * u
    if title:
        y, _ = core.text_block(d, title, fonts=ctx.fonts, role="display", size=hs, x=W / 2, y=y, max_w=W * 0.9,
                               color=t["text"], accent=t["accent"], lead=1.04, track=-0.025, label="headline")
    if body:
        core.text_block(d, body, fonts=ctx.fonts, role="body", size=38 * u, x=W / 2, y=y + 22 * u, max_w=W * 0.86,
                        color=t["muted"], lead=1.3, label="body")
    x0, y0 = place(ctx, c, dev.img, W / 2, cy)
    box = ctx.callout_box(s)
    if box:
        mid = (box[1] + box[3]) / 2
        ccy = y0 + dev.sy + screen.map_y(mid) * dev.k
        callout(ctx, c, screen, box, round(s.get("callout_width", 900) * u), ccy)
    return c.convert("RGB")


def hero(ctx, s: dict) -> Image.Image:
    u, W, H, t = ctx.u, ctx.W, ctx.H, ctx.theme
    caps = s.get("captures") or [s["capture"]]
    title, body = ctx.text(s.get("headline")), ctx.text(s.get("body"))
    hs = s.get("headline_size", 128) * u
    name = ctx.brand.get("name", "")
    row_h = 92 * u if (name or ctx.has_icon) else 0
    text_h = (row_h + 58 * u if row_h else 0) + _lines(title) * hs + (28 * u + _lines(body) * 38 * u * 1.3 if body else 0)
    top_min = 112 * u
    region_min = H - top_min - text_h - 50 * u
    tablet = ctx.kind == "tablet"
    tall = max(1.0, min(1.2, (H / W) / (16 / 9)))  # iPhone 19.5:9 gets bigger devices, not empty space
    cap_front = W * ((0.57 if tablet else 0.48) if len(caps) > 1 else (0.70 if tablet else 0.56)) * tall
    front, fscreen = device_for(ctx, caps[0], cap_front, region_min * 0.95, frame=s.get("frame"))
    slack = max(0, region_min * 0.95 - front.img.height)
    top = top_min + slack * 0.35
    region_top = top + text_h + 50 * u
    region_h = H - region_top

    c = background(ctx)
    gcy = region_top + region_h * 0.5
    glow(ctx, c, W * (0.574 if len(caps) > 1 else 0.5), gcy, W * 0.574, region_h * 0.6, alpha=t["glow_a"] * 1.25)
    d = ImageDraw.Draw(c)
    y = top
    if row_h:
        isz = round(92 * u)
        nf = ctx.fonts.get("display", 54 * u)
        has = ctx.has_icon
        roww = (isz + 22 * u if has else 0) + (nf.getlength(name) if name else 0)
        x = (W - roww) / 2
        if has:
            paste_icon(ctx, c, isz, x, y)
            x += isz + 22 * u
        if name:
            d.text((x, y + isz / 2), name, font=nf, fill=t["text"], anchor="lm")
        y += row_h + 58 * u
    if title:
        y, _ = core.text_block(d, title, fonts=ctx.fonts, role="display", size=hs, x=W / 2, y=y, max_w=W * 0.92,
                               color=t["text"], accent=t["accent"], lead=1.0, track=-0.025, label="hero headline")
    if body:
        core.text_block(d, body, fonts=ctx.fonts, role="body", size=38 * u, x=W / 2, y=y + 28 * u, max_w=W * 0.86,
                        color=t["muted"], lead=1.3, label="hero body")
    fy = region_top + region_h * 0.5
    if len(caps) > 1:
        back, _ = device_for(ctx, caps[1], cap_front * 0.83, region_h * 0.8, frame=s.get("frame"))
        place(ctx, c, back.img, W * 0.305, fy + region_h * 0.01, angle=7, shadow=0.6)
        place(ctx, c, front.img, W * 0.60, fy, angle=-3)
    else:
        place(ctx, c, front.img, W / 2, fy)
    return c.convert("RGB")


def closing(ctx, s: dict) -> Image.Image:
    u, W, H, t = ctx.u, ctx.W, ctx.H, ctx.theme
    title, body = ctx.text(s.get("headline")), ctx.text(s.get("body"))
    bullets = [ctx.text(b) for b in (s.get("bullets") or [])][:5]
    hs = s.get("headline_size", 92) * u
    isz = round(240 * u) if ctx.has_icon and s.get("icon", True) else 0
    cw, ch, gap = round(860 * u), round(124 * u), round(24 * u)
    total = (isz + 90 * u if isz else 0) + _lines(title) * hs * 1.05 + (36 * u + _lines(body) * 38 * u * 1.3 if body else 0) \
        + (90 * u + len(bullets) * (ch + gap) - gap if bullets else 0)
    top = max(120 * u, (H - total) / 2 - 20 * u)

    c = background(ctx)
    glow(ctx, c, W / 2, top + isz / 2 + 160 * u, 420 * u, 420 * u)
    d = ImageDraw.Draw(c)
    y = top
    if isz:
        paste_icon(ctx, c, isz, (W - isz) / 2, y, shadow=True)
        y += isz + 90 * u
    if title:
        y, _ = core.text_block(d, title, fonts=ctx.fonts, role="display", size=hs, x=W / 2, y=y, max_w=W * 0.9,
                               color=t["text"], accent=t["accent"], lead=1.05, track=-0.025, label="closing headline")
    if body:
        y, _ = core.text_block(d, body, fonts=ctx.fonts, role="body", size=38 * u, x=W / 2, y=y + 36 * u,
                               max_w=W * 0.86, color=t["muted"], lead=1.3, label="closing body")
    y += 90 * u - (hs * 0.05)
    f = ctx.fonts.get("body_bold", 40 * u)
    for label in bullets:
        x, yy = (W - cw) // 2, round(y)
        edge = t["card_edge"]
        c.paste(edge[:3] + (255,), (x, yy), core.rr_mask((cw, ch), round(34 * u)).point(lambda v: v * edge[3] // 255))
        c.paste(t["card"] + (255,), (x + 2, yy + 2), core.rr_mask((cw - 4, ch - 4), round(32 * u)))
        d = ImageDraw.Draw(c)
        bx, by, r = x + 42 * u, yy + ch / 2, 28 * u
        d.ellipse((bx, by - r, bx + 2 * r, by + r), fill=t["check"])
        tick = (255, 255, 255) if core.contrast((255, 255, 255), t["check"]) >= 2.2 else (17, 17, 20)
        d.line([(bx + 16 * u, by + 1), (bx + 25 * u, by + 10 * u), (bx + 41 * u, by - 9 * u)], fill=tick,
               width=max(2, round(6 * u)), joint="curve")
        tx = bx + 2 * r + 30 * u
        maxw = x + cw - tx - 30 * u
        ff = f
        if ff.getlength(label) > maxw:
            ff = ctx.fonts.get("body_bold", 40 * u * maxw / ff.getlength(label))
            core.warn(f"bullet {label!r} shrunk to fit its row")
        d.text((tx, by), label, font=ff, fill=t["text"] if t["dark"] else (17, 17, 20), anchor="lm")
        y += ch + gap
    return c.convert("RGB")


LAYOUTS = {"hero": hero, "feature": feature, "closing": closing}


# ---------------------------------------------------------------- banner (feature graphic, Apple header/search)


def _left_edge(img, cx, cy, angle, y0, y1) -> float:
    """Leftmost canvas x a device placed by place(img, cx, cy, angle) covers between rows y0 and y1."""
    a = img.getchannel("A")
    if angle:
        a = a.rotate(angle, resample=Image.BILINEAR, expand=True)
    top = cy - a.height / 2
    band = a.crop((0, max(0, round(y0 - top)), a.width, max(0, min(a.height, round(y1 - top)))))
    box = band.point(lambda p: 255 if p > 40 else 0).getbbox() if band.height else None
    return cx - a.width / 2 + box[0] if box else math.inf


def banner(ctx, b: dict, safe) -> Image.Image:
    """Landscape art. Composed on a virtual 1024x500 board fitted into the safe box."""
    W, H, t = ctx.W, ctx.H, ctx.theme
    sx0, sy0, sx1, sy1 = safe[0] * W, safe[1] * H, safe[2] * W, safe[3] * H
    v = min((sx1 - sx0) / 1024, (sy1 - sy0) / 500)
    ox = sx0 + ((sx1 - sx0) - 1024 * v) / 2
    oy = sy0 + ((sy1 - sy0) - 500 * v) / 2
    ctx.u = v * 1024 / 1080  # shadows/radii in place() scale with the board

    def X(x):
        return ox + x * v

    def Y(y):
        return oy + y * v

    style = b.get("style", "devices")
    caps = b.get("captures") or []
    if style == "devices" and not caps:
        style = "text"
    title, body = ctx.text(b.get("headline")), ctx.text(b.get("body"))
    name = ctx.brand.get("name", "")

    c = background(ctx)
    d = ImageDraw.Draw(c)
    if style == "devices":
        glow(ctx, c, X(780), Y(300), 380 * v, 330 * v, alpha=t["glow_a"] * 0.92)
        x = 76
        top = 92
        s = round(64 * v)
        tx = X(x)
        if ctx.has_icon:
            paste_icon(ctx, c, s, tx, Y(top), radius_ratio=0.234)
            tx += s + 16 * v
        if name:
            d.text((tx, Y(top) + s / 2), name, font=ctx.fonts.get("display", 38 * v), fill=t["text"], anchor="lm")
        spots = [(886, 378, 282, -6, 0.85), (712, 400, 238, 8, 0.6)]
        if len(caps) == 1:
            spots = [(800, 360, 290, -5, 0.85)]
        dx, dy = b.get("offset", [0, 0])  # board units (the board is 1024x500)
        k = b.get("device_scale", 1.0)
        devs = []
        for key, (cx, cy, sw, ang, shd) in zip(caps, spots):
            dev, _ = device_for(ctx, key, sw * v * k, 10 ** 6, frame=b.get("frame"))
            devs.append((dev.img, X(cx + dx), Y(cy + dy), ang, shd))
        # Text stops short of the devices: they are drawn on top and would hide it.
        y = Y(186)
        left = min(_left_edge(img, px, py, ang, y, Y(500)) for img, px, py, ang, _ in devs)
        room = left - X(x) - 20 * v
        if title:
            y, _ = core.text_block(d, title, fonts=ctx.fonts, role="display", size=86 * v, x=X(x - 4), y=y,
                                   max_w=min(560 * v, room), color=t["text"], accent=t["accent"], align="left",
                                   lead=1.0, track=-0.025, label="banner headline")
        if body:
            core.text_block(d, body, fonts=ctx.fonts, role="body", size=25 * v, x=X(x), y=y + 18 * v,
                            max_w=min(540 * v, room), color=t["muted"], align="left", lead=1.3, label="banner body")
        for img, px, py, ang, shd in reversed(devs):
            place(ctx, c, img, px, py, angle=ang, shadow=shd)
    else:
        glow(ctx, c, W / 2, Y(250), 420 * v, 260 * v)
        y = Y(110)
        s = round(84 * v)
        if ctx.has_icon:
            paste_icon(ctx, c, s, W / 2 - s / 2, y, shadow=True)
            y += s + 28 * v
        elif name:
            d.text((W / 2, y), name, font=ctx.fonts.get("display", 40 * v), fill=t["text"], anchor="ma")
            y += 64 * v
        if title:
            y, _ = core.text_block(d, title, fonts=ctx.fonts, role="display", size=80 * v, x=W / 2, y=y,
                                   max_w=900 * v, color=t["text"], accent=t["accent"], lead=1.0, track=-0.025,
                                   label="banner headline")
        if body:
            core.text_block(d, body, fonts=ctx.fonts, role="body", size=26 * v, x=W / 2, y=y + 16 * v, max_w=860 * v,
                            color=t["muted"], lead=1.3, label="banner body")
    return c.convert("RGB")

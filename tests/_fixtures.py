"""Synthetic app captures and a config, so the tests need no emulator and no real app."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "store-assets"
SCRIPTS = SKILL / "scripts"

SHOTS = {"home": (255, 120, 50), "stats": (60, 120, 255), "add": (40, 180, 120), "detail": (200, 60, 160)}


def fake_capture(w: int, h: int, status: int, nav: int, hue, seed: int) -> Image.Image:
    """An Android-looking screen: status bar glyphs, a header, list cards, a gesture handle."""
    rnd = random.Random(seed)
    im = Image.new("RGB", (w, h), (246, 246, 250))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, status + 120), fill=(255, 255, 255))
    d.rectangle((40, status // 2 - 10, 140, status // 2 + 10), fill=(0, 0, 0))  # "clock"
    d.rectangle((w - 120, status // 2 - 10, w - 60, status // 2 + 10), fill=(0, 0, 0))  # "battery"
    for i in range(8):
        y = status + 160 + i * 230
        d.rounded_rectangle((40, y, w - 40, y + 200), 30, fill=(255, 255, 255), outline=(220, 220, 228))
        d.rectangle((80, y + 40, 80 + rnd.randint(200, w - 200), y + 80), fill=hue)
    d.rounded_rectangle((w // 2 - 140, h - nav // 2 - 6, w // 2 + 140, h - nav // 2 + 6), 6, fill=(30, 30, 30))
    return im


def make_project(root: Path, targets: list[str], **overrides) -> Path:
    """Write captures, an icon and store-assets/config.json under root. Returns the config path."""
    sa = root / "store-assets"
    for i, (name, hue) in enumerate(SHOTS.items()):
        for kind, (w, h, s, n) in {"phone": (1080, 2400, 96, 48), "tablet": (1600, 2560, 52, 46)}.items():
            p = sa / "raw" / kind / f"{name}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            fake_capture(w, h, s, n, hue, i).save(p)
    icon = Image.new("RGB", (1024, 1024), (255, 122, 46))
    ImageDraw.Draw(icon).ellipse((262, 262, 762, 762), fill=(255, 255, 255))
    (root / "branding").mkdir(exist_ok=True)
    icon.save(root / "branding" / "icon.png")
    shots = {k: f"{k}.png" for k in SHOTS}
    cfg = {
        "brand": {"name": "testapp", "icon": "../branding/icon.png", "theme": "dark", "accent": "#FF8645"},
        "locales": ["en-US"],
        "captures": {
            "phone": {"platform": "android", "dir": "raw/phone", "status_bar_px": 96, "nav_bar_px": 48,
                      "shots": shots},
            "tablet": {"platform": "android", "dir": "raw/tablet", "status_bar_px": 52, "nav_bar_px": 46,
                       "shots": shots},
        },
        "targets": targets,
        "slides": [
            {"id": "01_hero", "layout": "hero", "captures": ["home", "stats"], "headline": "Every tank,\n*counted.*",
             "body": "Mileage and spend for every ride.", "alt": "Home and stats screens of the app"},
            {"id": "02_track", "capture": "home", "eyebrow": "REAL MILEAGE", "headline": "Know what your\nride *does*",
             "callout": {"phone": [0, 400, 1080, 900], "tablet": [0, 400, 1600, 900]},
             "alt": "Home screen with recent fill-ups"},
            {"id": "03_add", "capture": "add", "headline": "Log it\nin *seconds*", "alt": "Add fill-up form"},
        ],
        "banner": {"style": "devices", "headline": "Every tank,\n*counted.*",
                   "body": "Mileage and spend for every ride.", "captures": ["home", "stats"],
                   "alt": "App name and tagline beside two phone screens"},
    }
    cfg.update(overrides)
    path = sa / "config.json"
    path.write_text(json.dumps(cfg, indent=2))
    return path


def run(script: str, *args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a skill script the way an agent does: a fresh interpreter, from the app's repo root."""
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=600)

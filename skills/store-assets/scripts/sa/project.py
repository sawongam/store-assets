"""The project config (store-assets/config.json) and the per-image render context."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import chrome, core, layouts

HERE = Path(__file__).resolve().parent.parent
SPECS_PATH = HERE / "specs.json"


def load_specs() -> dict:
    return json.loads(SPECS_PATH.read_text(encoding="utf-8"))


def load_config(path: Path) -> tuple[dict, Path]:
    path = Path(path).resolve()
    if not path.exists():
        raise SystemExit(f"config not found: {path}\nStart from assets/config.example.json in the skill.")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: invalid JSON: {e}")
    for key in ("brand", "captures", "slides"):
        if key not in cfg:
            raise SystemExit(f"{path}: missing '{key}'")
    return cfg, path.parent


def rasterize_svg(path: Path, size: int) -> Image.Image:
    """SVG -> RGBA via rsvg-convert, cairosvg, inkscape or ImageMagick, whichever exists."""
    import io

    if shutil.which("rsvg-convert"):
        data = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(path)], check=True,
                              capture_output=True).stdout
        return Image.open(io.BytesIO(data)).convert("RGBA")
    try:
        import cairosvg  # type: ignore

        return Image.open(io.BytesIO(cairosvg.svg2png(url=str(path), output_width=size, output_height=size))).convert(
            "RGBA")
    except ImportError:
        pass
    for tool in (["inkscape", str(path), "--export-type=png", f"--export-width={size}", "--export-filename=-"],
                 ["magick", "-background", "none", "-density", "384", str(path), "-resize", f"{size}x{size}", "png:-"]):
        if shutil.which(tool[0]):
            data = subprocess.run(tool, check=True, capture_output=True).stdout
            return Image.open(io.BytesIO(data)).convert("RGBA")
    raise SystemExit("rendering SVG needs one of: rsvg-convert (librsvg), `pip install cairosvg`, inkscape, "
                     "ImageMagick. Or pass a 1024px PNG instead.")


def open_image(path: Path, size: int | None = None) -> Image.Image:
    if path.suffix.lower() == ".svg":
        return rasterize_svg(path, size or 1024)
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS) if size else img


class Project:
    """Everything shared across targets: config, fonts, theme, capture cache."""

    def __init__(self, cfg: dict, base: Path):
        self.cfg, self.base = cfg, base
        self.specs = load_specs()
        self.brand = cfg["brand"]
        self.fonts = core.Fonts(self.brand.get("fonts"), base)
        self.theme = layouts.resolve_theme(self.brand)
        self.locales = cfg.get("locales") or ["en-US"]
        self._raw: dict = {}
        self._screens: dict = {}
        self._icon_master = None
        icon = self.brand.get("icon")
        self.icon_path = (base / icon).resolve() if icon else None
        if self.icon_path and not self.icon_path.exists():
            core.warn(f"brand.icon not found: {self.icon_path}")
            self.icon_path = None

    def path(self, p) -> Path:
        p = Path(p).expanduser()
        return p if p.is_absolute() else (self.base / p).resolve()

    def icon(self, size: int):
        if not self.icon_path:
            return None
        if self._icon_master is None:
            self._icon_master = open_image(self.icon_path, 1024)
        return self._icon_master.resize((size, size), Image.LANCZOS)

    def capture_file(self, set_name: str, key: str, locale: str) -> Path | None:
        cs = self.cfg["captures"].get(set_name) or {}
        shots = cs.get("shots") or {}
        if key not in shots:
            return None
        name = shots[key]
        if isinstance(name, dict):
            name = name.get(locale) or name.get(self.locales[0]) or next(iter(name.values()))
        d = cs.get("dir", ".")
        p = self.path(Path(d.replace("{locale}", locale)) / name)
        if not p.exists() and "{locale}" in d:
            fallback = self.path(Path(d.replace("{locale}", self.locales[0])) / name)
            if fallback.exists():
                core.warn(f"{set_name}/{key}: no {locale} capture, using {self.locales[0]}")
                return fallback
        return p

    def screen(self, set_name, key, locale, platform, aspect) -> chrome.Screen:
        ck = (set_name, key, locale, platform, round(aspect or 0, 4))
        if ck in self._screens:
            return self._screens[ck]
        cs = self.cfg["captures"][set_name]
        p = self.capture_file(set_name, key, locale)
        if p is None or not p.exists():
            raise SystemExit(f"capture {set_name}/{key} not found: {p}")
        raw = self._raw.get(p) or Image.open(p)
        self._raw[p] = raw
        src_platform = cs.get("platform", "android")
        kind = "tablet" if set_name in ("tablet", "ipad") or cs.get("kind") == "tablet" else "phone"
        status = cs.get("status_bar_px")
        nav = cs.get("nav_bar_px")
        if status is None or nav is None:
            gs, gn = chrome.suggest_bars(raw.convert("RGB"))
            status = gs if status is None else status
            nav = gn if nav is None else nav
            core.warn(f"captures.{set_name}: status_bar_px/nav_bar_px not set, guessed {status}/{nav}px. "
                      f"Confirm with inspect_capture.py.")
        mode = cs.get("bars", "keep" if src_platform == "ios" else "repaint")
        scr = chrome.make_screen(raw, src_platform=src_platform, kind=kind, target_platform=platform,
                                 target_aspect=aspect, status_px=int(status), nav_px=int(nav), mode=mode,
                                 fonts=self.fonts, density=cs.get("density"), source=f"{set_name}/{key}")
        self._screens[ck] = scr
        return scr


class Ctx:
    """One image being rendered: a target at a size, in a locale."""

    def __init__(self, project: Project, target_id: str, spec: dict, locale: str, W: int, H: int):
        self.p, self.target_id, self.spec, self.locale = project, target_id, spec, locale
        self.W, self.H = W, H
        self.u = W / 1080
        self.brand, self.fonts, self.theme = project.brand, project.fonts, project.theme
        dev = spec.get("device", "android-phone")
        self.platform = "ios" if dev in ("iphone", "ipad") else "android"
        self.kind = "tablet" if dev in ("android-tablet", "ipad") else "phone"
        self.device = "none" if project.brand.get("frame") == "none" else dev
        self.has_icon = project.icon_path is not None
        self._set_for: dict = {}

    def text(self, v):
        if v is None or isinstance(v, str):
            return v
        if isinstance(v, dict):
            if self.locale in v:
                return v[self.locale]
            first = self.p.locales[0]
            core.warn(f"no {self.locale} text for {next(iter(v.values()))!r}; using {first}")
            return v.get(first) or next(iter(v.values()))
        return str(v)

    def icon(self, size):
        return self.p.icon(size)

    def screen(self, key) -> chrome.Screen:
        prefs = self.spec.get("captures", ["phone"])
        for set_name in prefs:
            if key in ((self.p.cfg["captures"].get(set_name) or {}).get("shots") or {}):
                self._set_for[key] = set_name
                sw, sh = self.spec.get("screen_size", self.spec["size"])
                aspect = sw / sh if self.platform == "ios" else None
                return self.p.screen(set_name, key, self.locale, self.platform, aspect)
        raise SystemExit(f"{self.target_id}: no capture named {key!r} in captures {prefs}")

    def callout_box(self, slide):
        box = slide.get("callout")
        if not box:
            return None
        if isinstance(box, dict):
            return box.get(self._set_for.get(slide.get("capture"), ""))
        return box if self._set_for.get(slide.get("capture")) in ("phone", "iphone") else None

#!/usr/bin/env python3
"""Render every store screenshot and banner from store-assets/config.json.

    python3 render.py                              # config at ./store-assets/config.json
    python3 render.py --config path/config.json
    python3 render.py --only play-phone ios-iphone-6.9 --slides 02_mileage
    python3 render.py --guides                     # also write safe-area overlays for banners
    python3 render.py --fastlane fastlane          # also copy into fastlane supply/deliver folders

Writes <output>/{play,appstore}/<locale>/<target>/NN_<id>.jpg, a manifest.json
for check.py, and <output>/_review/sheet-<locale>.jpg to look over.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sa  # noqa: E402,F401  (checks Python and Pillow first)
from PIL import Image, ImageDraw  # noqa: E402

from sa import core, layouts  # noqa: E402
from sa.project import Ctx, Project, load_config  # noqa: E402

DEFAULT_TARGETS = ["play-phone", "play-tablet-7", "play-tablet-10", "play-feature-graphic", "ios-iphone-6.9",
                   "ios-iphone-6.3", "ios-ipad-13"]


def slide_applies(slide: dict, target_id: str, spec: dict) -> bool:
    only = slide.get("only")
    if not only:
        return True
    only = [only] if isinstance(only, str) else only
    return target_id in only or spec["store"] in only or spec.get("device") in only


def save(img: Image.Image, path: Path, fmt: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = img.convert("RGB")  # stores reject alpha on screenshots and banners
    if fmt == "png":
        path = path.with_suffix(".png")
        img.save(path, optimize=True)
    else:
        path = path.with_suffix(".jpg")
        img.save(path, quality=92, subsampling=0, optimize=True)  # JPEG: the grain makes PNGs 4-5x bigger
    return path


def render_target(project: Project, target_id: str, spec: dict, locale: str, out: Path, fmt: str,
                  slide_filter, guides: bool, manifest: list, explicit: bool = False) -> list[Path]:
    written = []
    store_dir = out / spec["store"] / locale
    W, H = spec["size"]
    if spec["kind"] == "screenshots":
        n = 0
        for slide in project.cfg["slides"]:
            if not slide_applies(slide, target_id, spec):
                continue
            n += 1
            sid = slide.get("id") or f"{n:02d}"
            if slide_filter and sid not in slide_filter:
                continue
            lname = slide.get("layout", "feature")
            layout = layouts.LAYOUTS.get(lname)
            if lname == "closing":
                raise SystemExit(f"slide {sid}: the closing layout was removed in 1.1.0; delete this slide "
                                 f"(every screenshot now shows the app)")
            if layout is None:
                raise SystemExit(f"slide {sid}: unknown layout {lname!r} (hero, feature)")
            if lname == "feature" and not slide.get("capture"):
                raise SystemExit(f"slide {sid}: a feature slide needs \"capture\"")
            if lname == "hero" and not (slide.get("captures") or slide.get("capture")):
                raise SystemExit(f"slide {sid}: a hero slide needs \"captures\": [front, back]")
            ctx = Ctx(project, target_id, spec, locale, W, H)
            img = layout(ctx, slide)
            name = sid if sid[:2].isdigit() else f"{n:02d}_{sid}"
            p = save(img, store_dir / spec["folder"] / name, fmt)
            written.append(p)
            manifest.append(dict(path=str(p.relative_to(out)), target=target_id, store=spec["store"], locale=locale,
                                 kind="screenshot", slide=sid, size=[W, H]))
    else:
        b = project.cfg.get("banner") or {}
        if spec.get("experimental") and not explicit and target_id not in (project.cfg.get("targets") or []):
            return written  # experimental targets render only when listed in config.targets or --only
        ss = spec.get("supersample", 1)
        ctx = Ctx(project, target_id, {**spec, "device": b.get("device", "android-phone" if spec["store"] == "play"
                                                                 else "iphone"),
                                       "captures": ["phone", "iphone"] if spec["store"] == "play"
                                       else ["iphone", "phone"],
                                       "screen_size": [1320, 2868]},
                  locale, W * ss, H * ss)
        safe = b.get("safe", {}).get(target_id) if isinstance(b.get("safe"), dict) else None
        # Play's feature graphic uses the full board unless the config sets a safe box; Apple's use the spec's.
        safe = safe or ([0, 0, 1, 1] if spec["store"] == "play" else spec.get("safe", [0, 0, 1, 1]))
        img = layouts.banner(ctx, b, safe)
        if ss > 1:
            img = img.resize((W, H), Image.LANCZOS)
        bfmt = "png" if spec.get("png_only") else fmt
        p = save(img, store_dir / spec["file"], bfmt)
        written.append(p)
        manifest.append(dict(path=str(p.relative_to(out)), target=target_id, store=spec["store"], locale=locale,
                             kind="banner", size=[W, H]))
        if guides:
            g = img.convert("RGBA")
            d = ImageDraw.Draw(g)
            s = spec.get("safe", [0, 0, 1, 1])
            d.rectangle((s[0] * W, s[1] * H, s[2] * W, s[3] * H), outline=(255, 64, 64, 255),
                        width=max(2, W // 400))
            save(g, out / "_review" / f"{target_id}-{locale}-guides", "jpeg")
    return written


def contact_sheet(out: Path, locale: str, rows: list[tuple[str, list[Path]]]) -> Path | None:
    rows = [(label, paths) for label, paths in rows if paths]
    if not rows:
        return None
    th, bh, gap, label_h = 560, 280, 16, 44
    tiles = []
    for label, paths in rows:
        ims = []
        for p in paths:
            im = Image.open(p).convert("RGB")
            h = bh if im.width > im.height else th
            ims.append(im.resize((round(im.width * h / im.height), h), Image.LANCZOS))
        tiles.append((label, ims))
    width = max(sum(i.width for i in ims) + gap * (len(ims) + 1) for _, ims in tiles)
    height = sum(label_h + ims[0].height + gap for _, ims in tiles) + gap
    sheet = Image.new("RGB", (width, height), (128, 128, 134))
    d = ImageDraw.Draw(sheet)
    f = core.Fonts({}, out).get("body_bold", 26)
    y = gap
    for label, ims in tiles:
        d.text((gap, y + 8), label, font=f, fill=(255, 255, 255))
        y += label_h
        x = gap
        for im in ims:
            sheet.paste(im, (x, y))
            x += im.width + gap
        y += ims[0].height + gap
    p = out / "_review" / f"sheet-{locale}.jpg"
    p.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(p, quality=85)
    return p


def fastlane_export(out: Path, dest: Path, manifest: list, specs: dict) -> None:
    for m in manifest:
        src = out / m["path"]
        spec = specs["targets"][m["target"]]
        loc = m["locale"]
        if m["store"] == "play":
            images = dest / "metadata" / "android" / loc / "images"
            if m["kind"] == "banner":
                tgt = images / f"{spec['fastlane']}{src.suffix}"
            else:
                tgt = images / spec["fastlane"] / src.name
        else:
            if m["kind"] == "banner":
                continue  # deliver has no slot for header/search assets
            tgt = dest / "screenshots" / loc / f"{src.stem}_{m['target']}{src.suffix}"
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
    icon = out / "icons" / "play" / "icon-512.png"
    if icon.exists():
        for loc in {m["locale"] for m in manifest if m["store"] == "play"}:
            shutil.copy2(icon, dest / "metadata" / "android" / loc / "images" / "icon.png")
    print(f"fastlane layout written under {dest}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="store-assets/config.json")
    ap.add_argument("--only", nargs="*", help="target ids to render (default: config.targets)")
    ap.add_argument("--slides", nargs="*", help="slide ids to render")
    ap.add_argument("--locale", nargs="*", help="locales to render (default: config.locales)")
    ap.add_argument("--out", help="output dir (default: config.output or <config dir>/out)")
    ap.add_argument("--guides", action="store_true", help="write safe-area overlays for banners")
    ap.add_argument("--fastlane", help="also copy outputs into a fastlane folder (supply + deliver layout)")
    ap.add_argument("--no-sheet", action="store_true")
    args = ap.parse_args(argv)

    cfg, base = load_config(Path(args.config))
    project = Project(cfg, base)
    specs = project.specs
    targets = args.only or cfg.get("targets") or DEFAULT_TARGETS
    unknown = [t for t in targets if t not in specs["targets"]]
    if unknown:
        raise SystemExit(f"unknown targets {unknown}; known: {', '.join(specs['targets'])}")
    out = project.path(args.out or cfg.get("output", "out"))
    fmt = cfg.get("format", "jpeg")
    locales = args.locale or project.locales
    partial = bool(args.only or args.slides or args.locale)

    t0 = time.time()
    manifest: list = []
    prev = out / "manifest.json"
    if partial and prev.exists():
        keep = json.loads(prev.read_text(encoding="utf-8")).get("files", [])
        manifest = [m for m in keep if not (m["target"] in targets and m["locale"] in locales and
                                            (not args.slides or m.get("slide") in args.slides))]
    for locale in locales:
        for tid in targets:
            spec = specs["targets"][tid]
            for p in render_target(project, tid, spec, locale, out, fmt, args.slides, args.guides, manifest,
                                   explicit=bool(args.only)):
                print("wrote", p.relative_to(out))
        # A partial run keeps old entries and re-renders banners (they have no slide id): newest entry wins.
        manifest = list({m["path"]: m for m in manifest}.values())
        if not args.no_sheet:
            rows = []
            for tid, spec in specs["targets"].items():  # whole manifest, so partial runs refresh the full sheet
                paths = sorted(out / m["path"] for m in manifest if m["target"] == tid and m["locale"] == locale)
                rows.append((spec["label"], [p for p in paths if p.exists()]))
            sheet = contact_sheet(out, locale, rows)
            if sheet:
                print("review sheet:", sheet)
    (out / "manifest.json").write_text(json.dumps({"config": str(Path(args.config).resolve()),
                                                   "files": manifest}, indent=2) + "\n", encoding="utf-8")
    if args.fastlane:
        fastlane_export(out, project.path(args.fastlane), manifest, specs)
    for locale in locales:
        alt = alt_text(project, locale, manifest, out)
        if alt:
            print("alt text drafts:", alt)
    print(f"done in {time.time() - t0:.1f}s · {len(manifest)} files · {core.platform_note()}")
    core.report_warnings()
    return 0


def alt_text(project: Project, locale: str, manifest: list, out: Path) -> Path | None:
    """Play asks for alt text (<=140 chars) per image. Writes slide.alt, or a TODO draft to finish by hand."""
    import re

    slides = {s.get("id"): s for s in project.cfg["slides"]}
    lines = [f"# Alt text · {locale}", "",
             "Play Console asks for one per image (140 characters max, describe what is shown, no 'image of').",
             "Set `alt` on a slide in config.json to fill these in; TODO lines are drafts.", ""]
    ctx_text = Ctx(project, "play-phone", project.specs["targets"]["play-phone"], locale, 1080, 1920).text
    seen = False
    for m in sorted(manifest, key=lambda m: m["path"]):  # partial runs append out of order
        if m["store"] != "play" or m["locale"] != locale:
            continue
        seen = True
        if m["kind"] == "banner":
            b = project.cfg.get("banner") or {}
            head = re.sub(r"[*\n]+", " ", ctx_text(b.get("headline")) or "")
            text = ctx_text(b.get("alt")) or f"TODO: feature graphic — {head}"
        else:
            s = slides.get(m.get("slide")) or {}
            head = re.sub(r"\s+", " ", (ctx_text(s.get("headline")) or "").replace("*", "").replace("\n", " "))
            shown = s.get("capture") or ", ".join(s.get("captures") or []) or "app icon and feature list"
            text = ctx_text(s.get("alt")) or f"TODO: {shown} screen — {head}"
        flag = "  ⚠ over 140" if len(text) > 140 else ""
        lines.append(f"- `{m['path']}`: {text}{flag}")
    if not seen:
        return None
    p = out / f"alt-text-{locale}.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


if __name__ == "__main__":
    sys.exit(main())

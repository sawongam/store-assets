#!/usr/bin/env python3
"""Validate rendered store assets against specs.json before anything is uploaded.

    python3 check.py                                   # store-assets/out + store-assets/config.json
    python3 check.py --out path/out --config path/config.json
    python3 check.py --file shot.png --target ios-iphone-6.9   # one ad-hoc file

Checks pixel size, format, alpha, file size, Play's side/ratio limits, counts
per store and locale, colour profile, and the copy (banned ranking/price/CTA
words, other platforms' names). Exit code 1 when anything would be rejected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sa  # noqa: E402,F401  (checks Python and Pillow first)
from PIL import Image  # noqa: E402

from sa import core  # noqa: E402
from sa.project import load_specs  # noqa: E402

ERR, WARN = [], []


def err(m):
    ERR.append(m)


def wrn(m):
    WARN.append(m)


def has_alpha(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA", "PA"):
        return True
    return img.mode == "P" and "transparency" in img.info


def check_image(path: Path, label: str, spec: dict) -> None:
    if not path.exists():
        err(f"{label}: missing file {path}")
        return
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:  # noqa: BLE001
        err(f"{label}: unreadable ({e})")
        return
    fmt = (img.format or "").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    if fmt not in spec.get("formats", ["png", "jpeg"]):
        err(f"{label}: format {fmt or '?'} not accepted ({'/'.join(spec['formats'])})")
    w, h = img.size
    accepted = [tuple(s) for s in spec.get("accepted", [])] or ([tuple(spec["size"])] if "size" in spec else [])
    if "accepted_range" in spec:
        (lw, lh), (hw, hh) = spec["accepted_range"]
        if not (lw <= w <= hw and lh <= h <= hh and abs(w / h - lw / lh) < 0.01):
            err(f"{label}: {w}x{h} outside {lw}x{lh}..{hw}x{hh} at {lw}:{lh}")
    elif "side_range" in spec:
        lo, hi = spec["side_range"]
        if not (lo <= min(w, h) and max(w, h) <= hi):
            err(f"{label}: {w}x{h} sides must be {lo}-{hi}px")
        if spec.get("max_ratio") and max(w, h) / min(w, h) > spec["max_ratio"]:
            err(f"{label}: {w}x{h} long side is more than {spec['max_ratio']}x the short side")
        if spec.get("promo_min_short_side") and min(w, h) < spec["promo_min_short_side"]:
            wrn(f"{label}: under {spec['promo_min_short_side']}px short side; not eligible for Play promotion")
    elif accepted and (w, h) not in accepted and (h, w) not in accepted:
        err(f"{label}: {w}x{h} is not an accepted size ({', '.join(f'{a}x{b}' for a, b in accepted)})")
    if spec.get("alpha") is False and has_alpha(img):
        err(f"{label}: has an alpha channel; flatten to RGB")
    size = path.stat().st_size
    if spec.get("max_bytes") and size > spec["max_bytes"]:
        err(f"{label}: {size / 1e6:.1f} MB is over {spec['max_bytes'] / 1e6:.1f} MB")
    icc = img.info.get("icc_profile")
    if icc and b"sRGB" not in icc:
        wrn(f"{label}: embedded colour profile is not sRGB; stores may shift colours")
    if img.mode not in ("RGB", "RGBA", "P", "L"):
        err(f"{label}: colour mode {img.mode}; save as RGB")


ALT_MAX = 140  # Play Console's alt-text limit per image


def lint_alt(where: str, alt, texts) -> None:
    """Play asks for alt text on every screenshot and the feature graphic."""
    if not alt:
        wrn(f"{where}: no alt text; Play asks for one per image (set \"alt\", {ALT_MAX} characters or fewer)")
        return
    for loc, t in texts(alt):
        if len(t) > ALT_MAX:
            err(f"{where}.alt[{loc}]: {len(t)} characters; Play allows {ALT_MAX}")
        if "TODO" in t:
            wrn(f"{where}.alt[{loc}]: still a TODO draft")
        if re.match(r"\s*(an? )?(image|picture|screenshot|photo) of\b", t, re.I):
            wrn(f"{where}.alt[{loc}]: drop the leading \"{t.split(' of')[0]} of\"; describe what is shown")


def lint_copy(cfg: dict, specs: dict) -> None:
    lint = specs["copy_lint"]
    stores = {specs["targets"][t]["store"] for t in (cfg.get("targets") or []) if t in specs["targets"]} or {"play",
                                                                                                         "appstore"}

    def texts(v):
        if v is None:
            return []
        if isinstance(v, dict):
            return [(loc, s) for loc, s in v.items() if isinstance(s, str)]
        if isinstance(v, list):
            return [x for item in v for x in texts(item)]
        return [("*", str(v))]

    items = []
    for s in cfg.get("slides", []):
        only = s.get("only")
        only = [only] if isinstance(only, str) else (only or [])
        slide_stores = {o for o in only if o in ("play", "appstore")} | {
            specs["targets"][o]["store"] for o in only if o in specs["targets"]} or stores
        for field in ("eyebrow", "headline", "body", "bullets"):
            for loc, t in texts(s.get(field)):
                items.append((f"slide {s.get('id', '?')}.{field}[{loc}]", t, slide_stores & stores))
        if "play" in slide_stores & stores:
            lint_alt(f"slide {s.get('id', '?')}", s.get("alt"), texts)
    b = cfg.get("banner") or {}
    for field in ("headline", "body"):
        for loc, t in texts(b.get(field)):
            items.append((f"banner.{field}[{loc}]", t, stores))
    if b and "play" in stores:
        lint_alt("banner", b.get("alt"), texts)

    def hits(words, text):
        out = []
        for w in words:
            pat = re.escape(w.lower())
            pat = (r"(?<![\w])" + pat if w[0].isalnum() else pat) + (r"(?![\w])" if w[-1].isalnum() else "")
            if re.search(pat, text.lower().replace("*", "")):
                out.append(w)
        return out

    for where, text, st in items:
        for w in hits(lint["error"], text):
            err(f"copy {where}: {w!r} is banned in store art ({text!r})")
        if "play" in st:
            for w in hits(lint["error_play"], text):
                err(f"copy {where}: {w!r} names another platform on Google Play ({text!r})")
        if "appstore" in st:
            for w in hits(lint["error_appstore"], text):
                err(f"copy {where}: {w!r} names another platform on the App Store ({text!r})")
        for w in hits(lint["warn"], text):
            wrn(f"copy {where}: {w!r} — check it is not a price/promo/unprovable claim ({text!r})")
        longest = max((len(x) for x in text.split("\n")), default=0)
        if "headline" in where and longest > 28:
            wrn(f"copy {where}: a {longest}-character line reads small in store thumbnails; aim for 3-5 words a line")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="rendered output dir (default: the config's output, as render.py uses)")
    ap.add_argument("--config", default="store-assets/config.json")
    ap.add_argument("--file")
    ap.add_argument("--target", help="with --file: a target or icon id from specs.json")
    args = ap.parse_args(argv)
    specs = load_specs()
    print(f"specs last verified {specs['last_verified']} — re-check the live pages if that is months old")

    if args.file:
        spec = specs["targets"].get(args.target) or specs["icons"].get(args.target)
        if not spec:
            raise SystemExit(f"--target must be one of {', '.join(list(specs['targets']) + list(specs['icons']))}")
        check_image(Path(args.file), args.file, spec)
    else:
        cfg_path = Path(args.config)
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else None
        if args.out:
            out = Path(args.out)
        elif cfg is not None:
            o = Path(cfg.get("output", "out")).expanduser()
            out = o if o.is_absolute() else cfg_path.resolve().parent / o
        else:
            out = Path("store-assets/out")
        man = out / "manifest.json"
        files = json.loads(man.read_text())["files"] if man.exists() else []
        if not files:
            wrn(f"no {man}; run render.py first")
        counts = defaultdict(int)
        for m in files:
            spec = specs["targets"].get(m["target"])
            if spec is None:
                err(f"{m['path']}: unknown target {m['target']!r} in the manifest; re-run render.py")
                continue
            check_image(out / m["path"], m["path"], spec)
            counts[(m["target"], m["locale"])] += 1
            if m["target"] == "play-feature-graphic" and (out / m["path"]).exists():
                im = Image.open(out / m["path"]).convert("RGB").resize((64, 32))
                px = core.pixels(im)
                lum = sum(core.luminance(p) for p in px) / len(px)
                if lum < 0.06 or lum > 0.9:
                    wrn(f"{m['path']}: mostly {'black/dark grey' if lum < 0.06 else 'white'}; Play recommends vibrant "
                        f"colours here (it blends into the store background)")
        by_target = defaultdict(dict)
        for (t, loc), n in counts.items():
            by_target[t][loc] = n
            spec = specs["targets"][t]
            if spec["kind"] == "screenshots":
                lo, hi = spec["count"]
                if n < lo or n > hi:
                    err(f"{t} [{loc}]: {n} screenshots; the store takes {lo}-{hi}")
                if spec.get("promo_min_count") and n < spec["promo_min_count"]:
                    wrn(f"{t} [{loc}]: {n} screenshots; Play needs {spec['promo_min_count']}+ for promotion slots")
        for t, locs in by_target.items():
            if len(set(locs.values())) > 1:
                wrn(f"{t}: different screenshot counts per locale {locs}")
        present = set(by_target)
        if any(specs["targets"][t]["store"] == "play" for t in present):
            if "play-feature-graphic" not in present:
                err("Play listing needs a feature graphic (play-feature-graphic)")
            if "play-phone" not in present:
                wrn("no play-phone screenshots")
        if any(specs["targets"][t]["store"] == "appstore" for t in present):
            if not present & {"ios-iphone-6.9", "ios-iphone-6.3"}:
                err("App Store needs iPhone screenshots (ios-iphone-6.9 and/or ios-iphone-6.3)")
        icon_man = out / "icons" / "manifest.json"
        if icon_man.exists():
            for m in json.loads(icon_man.read_text())["files"]:
                check_image(out / "icons" / m["path"], "icons/" + m["path"], specs["icons"][m["target"]])
        else:
            wrn("no icons checked (run icons.py, or check existing ones with --file X --target play-icon|ios-icon)")
        if cfg is not None:
            lint_copy(cfg, specs)
        else:
            wrn(f"no config at {cfg_path}; copy and alt text were not checked (pass --config)")
        print(f"checked {len(files)} images")

    for m in ERR:
        print("FAIL", m)
    for m in WARN:
        print("WARN", m)
    print(f"\n{len(ERR)} errors, {len(WARN)} warnings")
    return 1 if ERR else 0


if __name__ == "__main__":
    sys.exit(main())

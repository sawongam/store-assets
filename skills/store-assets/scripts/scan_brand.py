#!/usr/bin/env python3
"""Inventory a codebase for store-asset inputs: name, colours, fonts, icons, strings, captures.

    python3 scan_brand.py [repo_dir] [--json]

Prints candidates with the file each came from. It does not decide anything:
read the top files it names (theme, tokens, design docs) and choose. Works for
Flutter, React Native / Expo, native Android, native iOS, and web projects.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SKIP = {".git", "node_modules", "build", ".dart_tool", "Pods", "DerivedData", ".gradle", "dist", ".next", "vendor",
        ".idea", ".vscode", "out", ".expo", "coverage", "__pycache__", ".venv", "venv", "Carthage", ".fvm",
        ".symlinks", "ephemeral", "store-assets", ".turbo", ".cache", "generated"}
TEXT_EXT = {".dart", ".kt", ".java", ".xml", ".swift", ".m", ".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".json",
            ".yaml", ".yml", ".md", ".plist", ".gradle", ".kts", ".arb", ".html", ".vue", ".svelte"}
THEME_HINT = re.compile(r"(theme|color|colour|palette|token|brand|style|design|tailwind|app_ui)", re.I)
HEX = re.compile(r"(?<![\w&])#([0-9a-fA-F]{6})(?![0-9a-fA-F])")
FLUTTER = re.compile(r"Color\(\s*0x([0-9a-fA-F]{2})([0-9a-fA-F]{6})\s*\)")
ANDROID_HEX = re.compile(r">#(?:[0-9a-fA-F]{2})?([0-9a-fA-F]{6})<")


def walk(root: Path, max_files=40000):
    n = 0
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name not in SKIP and not p.name.startswith("."):
                    stack.append(p)
            else:
                n += 1
                if n > max_files:
                    return
                yield p


def read(p: Path, limit=400_000) -> str:
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def grey(h: str) -> bool:
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return max(r, g, b) - min(r, g, b) < 18


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    stack, names, ids = set(), [], []
    colors: Counter = Counter()
    color_src: dict = defaultdict(set)
    fonts, icons, l10n, captures, docs = [], [], defaultdict(list), defaultdict(list), []
    res_dirs, appiconsets = set(), set()

    for p in walk(root):
        rel = p.relative_to(root)
        s = str(rel)
        name, ext = p.name, p.suffix.lower()
        if name == "pubspec.yaml" and len(rel.parts) <= 2:
            stack.add("flutter")
            t = read(p)
            m = re.search(r"^name:\s*(\S+)", t, re.M)
            if m:
                names.append((m.group(1), s))
            for fm in re.finditer(r"asset:\s*(\S+\.(?:ttf|otf))", t):
                fonts.append((fm.group(1), s + " (declared)"))
        elif name == "package.json" and len(rel.parts) <= 2:
            t = read(p)
            try:
                pj = json.loads(t)
            except json.JSONDecodeError:
                pj = {}
            deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}
            if "react-native" in deps:
                stack.add("react-native")
            if "expo" in deps:
                stack.add("expo")
            if any(k in deps for k in ("next", "vite", "react-dom", "vue", "svelte")):
                stack.add("web")
            for k in ("productName", "displayName", "name"):
                if pj.get(k):
                    names.append((pj[k], f"{s} ({k})"))
        elif name in ("app.json", "app.config.json") and len(rel.parts) <= 2:
            t = read(p)
            for m in re.finditer(r'"(name|slug|bundleIdentifier|package|backgroundColor|primaryColor)"\s*:\s*"([^"]+)"', t):
                (ids if m.group(1) in ("bundleIdentifier", "package") else names).append((m.group(2), f"{s} ({m.group(1)})"))
        elif name == "AndroidManifest.xml" and "main" in rel.parts:
            stack.add("android")
            m = re.search(r'android:label="([^"]+)"', read(p))
            if m:
                names.append((m.group(1), s))
        elif name in ("build.gradle", "build.gradle.kts") and "app" in rel.parts:
            m = re.search(r'applicationId\s*=?\s*"([^"]+)"', read(p))
            if m:
                ids.append((m.group(1), s))
        elif name == "strings.xml" and "values" in rel.parts:
            m = re.search(r'name="app_name"[^>]*>([^<]+)<', read(p))
            if m:
                names.append((m.group(1), s))
        elif name == "Info.plist" and "Pods" not in rel.parts:
            stack.add("ios")
            t = read(p)
            for key in ("CFBundleDisplayName", "CFBundleName"):
                m = re.search(rf"<key>{key}</key>\s*<string>([^<$]+)</string>", t)
                if m:
                    names.append((m.group(1), f"{s} ({key})"))
        if ext in (".ttf", ".otf", ".woff2", ".ttc") and "icon" not in name.lower():
            fonts.append((s, f"{p.stat().st_size // 1024} KB"))
        if ext in (".svg", ".png") and re.search(r"(logo|mark|icon|brand)", name, re.I) and \
                "mipmap" not in s and "appiconset" not in s and ("brand" in s.lower() or "logo" in name.lower()
                                                                  or "mark" in name.lower() or ext == ".svg"):
            icons.append(s)
        if "mipmap-xxxhdpi" in s and name.startswith("ic_launcher"):
            icons.append(s)
            res_dirs.add(str(rel.parent.parent))
        if p.parent.name.endswith(".appiconset") and ext == ".png":
            appiconsets.add(str(rel.parent))
        if ext == ".arb":
            l10n["arb"].append(s)
        elif name == "strings.xml":
            l10n["android"].append(s)
        elif ext == ".xcstrings" or name == "Localizable.strings":
            l10n["ios"].append(s)
        elif ext == ".json" and re.search(r"(locales?|i18n|lang)/", s):
            l10n["json"].append(s)
        if ext in (".png", ".jpg", ".jpeg") and (re.match(r"(screenshot|screen_?shot|simulator screen shot)", name, re.I)
                                                 or re.search(r"screenshots?/", s, re.I)):
            captures[str(rel.parent)].append(name)
        if ext == ".md" and re.search(r"(design|brand|style|theme)", name, re.I):
            docs.append(s)
        if ext in TEXT_EXT and (THEME_HINT.search(s) or name in ("colors.xml", "themes.xml", "tailwind.config.js",
                                                                  "tailwind.config.ts")):
            t = read(p)
            for m in FLUTTER.finditer(t):
                h = m.group(2).upper()
                colors[h] += 1
                color_src[h].add(s)
            for m in HEX.finditer(t):
                h = m.group(1).upper()
                colors[h] += 1
                color_src[h].add(s)
            for m in ANDROID_HEX.finditer(t):
                h = m.group(1).upper()
                colors[h] += 1
                color_src[h].add(s)
        if p.suffix == ".json" and p.parent.name.endswith(".colorset"):
            t = read(p)
            comps = dict(re.findall(r'"(red|green|blue)"\s*:\s*"([^"]+)"', t))
            if len(comps) == 3:
                try:
                    vals = [float(comps[k]) if "." in comps[k] else int(comps[k], 0) for k in ("red", "green", "blue")]
                    vals = [round(v * 255) if isinstance(v, float) and v <= 1 else int(v) for v in vals]
                    h = "{:02X}{:02X}{:02X}".format(*vals)
                    colors[h] += 3
                    color_src[h].add(s)
                except ValueError:
                    pass

    chroma = [(h, n) for h, n in colors.most_common() if not grey(h)][:16]
    neutrals = [(h, n) for h, n in colors.most_common() if grey(h)][:8]
    report = {
        "root": str(root),
        "stack": sorted(stack) or ["unknown"],
        "app_names": list(dict.fromkeys(names))[:10],
        "app_ids": list(dict.fromkeys(ids))[:6],
        "brand_docs": docs[:10],
        "colors": [{"hex": "#" + h, "count": n, "from": sorted(color_src[h])[:3]} for h, n in chroma],
        "neutrals": [{"hex": "#" + h, "count": n} for h, n in neutrals],
        "fonts": fonts[:40],
        "icon_candidates": icons[:20],
        "android_res_dirs": sorted(res_dirs),
        "ios_appiconsets": sorted(appiconsets),
        "localization": {k: v[:12] for k, v in l10n.items()},
        "capture_dirs": {k: f"{len(v)} images, e.g. {v[0]}" for k, v in sorted(captures.items())},
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"repo: {root}\nstack: {', '.join(report['stack'])}")
    print("\napp name candidates:")
    for v, src in report["app_names"]:
        print(f"  {v!r:32} {src}")
    for v, src in report["app_ids"]:
        print(f"  id {v:29} {src}")
    if docs:
        print("\nbrand/design docs (read these first):")
        for d in docs[:10]:
            print("  ", d)
    print("\ncolours (most used, non-grey) — the brand is usually one of the first few:")
    for c in report["colors"]:
        print(f"  {c['hex']}  x{c['count']:<4} {', '.join(c['from'])}")
    print("neutrals:", ", ".join(f"{c['hex']}(x{c['count']})" for c in report["neutrals"]))
    print("\nfonts:")
    for f, note in report["fonts"]:
        print(f"  {f}  ({note})")
    print("\nicon / mark candidates:")
    for i in report["icon_candidates"]:
        print("  ", i)
    print("android res:", ", ".join(report["android_res_dirs"]) or "-")
    print("ios appiconset:", ", ".join(report["ios_appiconsets"]) or "-")
    print("\nlocalization:")
    for k, v in report["localization"].items():
        print(f"  {k}: {len(v)} files, e.g. {v[0]}")
    print("\nexisting captures:")
    for k, v in report["capture_dirs"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Changelog

## 1.1.0

- **Removed:** the `closing` layout (icon plus bullet list). Every screenshot now shows the app; put trust points in the hero body or a feature eyebrow. A config that still has a closing slide stops with a message saying to delete it. `brand.check` is gone with it.
- **Fixed:** a punch-hole camera could be smeared into a vertical line across the status bar. The bar guess ignored the centre of the band, so it stopped above a cut-out that reaches lower than the clock, and the repaint then stretched the cut-out's last row upward. `inspect_capture.py` now measures the cut-out too, and the renderer moves past any cut-out left in the band (by up to 1.2% of the height) and warns with the value to set.

## 1.0.1

- **Fixed:** text files are now read and written as UTF-8, so alt text and non-ASCII config copy no longer crash on Windows.
- **Fixed:** the feature graphic's body text could run under the devices and be cut off. Banner text now stops where the devices begin, and shrinks with a warning to fit.
- **Fixed:** a slide rendered alone (`--slides`) could differ from the same slide in a full render, because the grain came from unseeded noise. It is now seeded, so renders are identical either way.
- **Fixed:** `render.py --only ios-header|ios-search` rendered nothing unless the target was also in `config.targets`.
- **Faster:** a full render takes about half the time (136 s → 57 s for 66 images). Rounded masks, shadows and backgrounds are cached or computed at lower cost.
- `check.py` lints Play alt text (missing, TODO, over 140 characters, "screenshot of …") and warns when no config is found.
- The scripts print a one-line fix when Python or Pillow is too old. The floor is Pillow 10.1, which `ImageFont.load_default(size)` needs.
- `alt-text-<locale>.md` lists images in path order after partial runs.
- Packaging for more harnesses: `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json` and `gemini-extension.json`, alongside the Claude Code plugin. All of them load the same `skills/` folder.
- SKILL.md: harness-neutral wording, a note on runtime and timeouts, a fallback for runs that can't stop to ask, and Windows `python`.
- Tests (`tests/`, stdlib unittest with synthetic captures), CI on Linux, macOS and Windows, and `AGENTS.md` for contributors.

## 1.0.0

First release.

- Screenshots for Play phone, 7" and 10" tablet, iPhone 6.9" and 6.3", and iPad 13"
- `hero`, `feature` (with a zoomed callout) and `closing` layouts
- `dark`, `light` and `brand` themes
- Drawn device frames (Android phone and tablet, iPhone, iPad) or frameless
- Capture cleaning to a 9:41 status bar; Android captures re-chromed for iOS
- Play feature graphic, plus experimental iOS 27 product-page header and search assets from one banner design
- Icons: Play 512, App Store 1024, appiconset with dark and tinted, a starter Icon Composer bundle, Android adaptive and themed, legacy and round, and a mask preview
- `scan_brand.py`, `inspect_capture.py`, `capture.sh` (Android demo mode, iOS-size capture, simctl)
- `check.py` validator: sizes, alpha, counts, file size, colour profile, copy lint per store
- Locales, fastlane supply/deliver export, review contact sheet
- Per-slide `frame`, `banner.offset`/`device_scale`, closing `icon: false`, Play alt-text drafts (`out/alt-text-<locale>.md`)
- Bar detection handles rounded-corner captures, edge borders and 3-button navigation, with a per-set median suggestion

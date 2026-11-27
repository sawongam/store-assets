---
name: store-assets
description: Create upload-ready Google Play and App Store assets from an app's own codebase. Covers framed screenshots with benefit headlines for phone, tablet, iPhone and iPad, the Play feature graphic, the iOS 27 product-page header and search assets, and every store and launcher icon (Play 512, App Store 1024 with dark/tinted, Icon Composer, Android adaptive and themed). Reads brand colours, fonts, name and icon from the repo, cleans real captures to a 9:41 status bar, renders deterministically with Pillow (no AI redraws of the UI), and checks sizes, alpha, counts and banned copy before upload. Use it whenever someone wants store screenshots, a store listing, Play Store or App Store graphics, a feature graphic, ASO visuals, app or launcher icons, or to localize or refresh store images, even if they only say "make the app look good on the store".
license: MIT
compatibility: Python 3.9+ with Pillow 10.1+. Optional tools are rsvg-convert or cairosvg for SVG icons, adb for Android captures, and xcrun simctl for iOS captures (macOS). Works on Linux, macOS and Windows.
metadata:
  author: sawongam
  version: "1.1.0"
---

# Store assets

Turn a codebase and a handful of real captures into a complete, validated store kit for Google Play and the App Store. The look is set by one config file, so a UI change means re-capturing and re-rendering, not redrawing.

**How it works:** you make the decisions (story, copy, crops) and the scripts make the pixels. Everything renders from `store-assets/config.json` in the user's repo. You look at every output image before calling it done, because layout bugs only show up visually.

Scripts live in `scripts/` next to this file. Below, `$S` means that folder, as an absolute path (it depends on where this skill is installed). Run them from the app's repo root. By default every script reads and writes under `./store-assets/` (config, `raw/`, `out/`); pass `--config` and `--out` to work elsewhere. On Windows, `python3` may be `python` or `py`. If a script says Pillow is missing, install it with `python3 -m pip install pillow` (ask first if the project manages its own Python environment).

| Script | Does |
|---|---|
| `scan_brand.py [repo]` | Lists name, colour, font, icon, l10n and capture candidates, with the file each came from |
| `inspect_capture.py files…` | Measures status and nav bars and writes a ruler image to check by eye |
| `render.py` | Renders all screenshots and banners, the manifest and the review sheet |
| `icons.py --mark … --bg …` | Builds store icons, the appiconset (light, dark, tinted), Icon Composer, Android adaptive and themed, plus a preview |
| `check.py` | Runs the validator: sizes, alpha, counts, file size, colour profile, copy lint. Exits 1 on failure |
| `capture.sh` | Android demo mode, Android display resized to iOS sizes, simctl status bar, screenshot helpers |

## Workflow

### 0. Resume or start

If `store-assets/config.json` exists, this is a refresh. Read it, ask what changed (new screens, copy, locale, theme), then go to step 4 or 5. Otherwise start at step 1.

Also ask which stores and devices are in scope, unless it's obvious from the repo. For example, there's no iPad set when the app doesn't support iPad, and no iOS assets for an Android-only app. Trim `targets` to match.

If the repo already has store art or generator scripts (scan_brand lists capture dirs and brand folders), ask whether the new set replaces them or lives beside them. Never overwrite existing assets silently.

### 1. Read the brand from the code

Run `python3 $S/scan_brand.py .`. Then open what it points at: design docs (`DESIGN.md`, brand guides), theme and token files, and the font files. Pick:

- **accent**: the brand colour. Make sure it's the brand and not a link blue or an error red.
- **fonts**: a display face for headlines and a text face for the rest. Point at the app's own TTF/OTF files.
- **icon**: the finished app icon, 512px or larger.
- **theme**: `dark` (graphite plus glow, the default, and it makes UI pop), `light`, or `brand` (accent-coloured canvas).

Say what you picked and why in 3–4 lines. Don't stop for approval unless something is genuinely ambiguous, such as two plausible brand colours.

### 2. Plan the story

Read `references/copy.md` first. Then read the app's actual features from its routes, screens and strings, so that every claim maps to a screen that exists.

Draft 4–8 slides, every one showing the app:

1. **hero**: app name, a promise headline, and 2 devices.
2. **features** (3–7): one benefit per slide, each with a capture and usually a callout.

There is no text-only slide. Trust points (offline, privacy, open source) go in the hero body or a feature's eyebrow.

Show the plan as a table: slide, layout, capture, eyebrow, headline. This is the one checkpoint worth asking the user about. Copy is the part they care most about, and it's cheap to change now. If you can't ask (a headless or CI run), go ahead with your best plan and list every copy decision under "what is unverified" at hand-off.

Match the story to the captures you have, and ask for the missing ones:

- **Fewer captures than slides:** each feature slide should show a different screen. Reusing a capture with a different callout is acceptable once. Otherwise cut the slide, or list the screens to capture next, which is better.
- **Sparse screens:** a list with 2 rows or an empty state leaves a mostly blank device. Ask for richer demo data, or give that slide `"frame": "none"` with a callout, or drop it.
- **Content to flag before rendering:** a trademark (a game title, another brand), a real person's name or a real place.

### 3. Get captures

Real UI only. Never mock, redraw or AI-generate the app's screens, because stores reject UI that doesn't match the app. If the repo already has captures, use them. Otherwise read `references/capture.md` and give the user the exact steps:

- Turn on demo mode (`capture.sh android-demo on`), seed realistic data, and capture each planned screen. Use the same device for the whole set.
- For iOS without a Mac, run `capture.sh android-size iphone` (or `ipad`) first. That captures the same app at the exact iOS aspect, which render.py re-chromes with an iOS status bar and home indicator.

If the project's instructions say not to run the app or emulator, hand the user these commands instead of running them yourself.

### 4. Measure the bars, write the config

Run `python3 $S/inspect_capture.py <one or two captures per set>` and look at the guide image it writes. Set `status_bar_px` and `nav_bar_px` for each capture set from the rulers, not from the guess alone. The cleaned band must cover the clock, the icons and any camera cut-out.

Write `store-assets/config.json`. Start from `assets/config.example.json`, and use `references/config.md` for every field. Paths may be relative to the config or absolute.

Callout boxes are `[x0, y0, x1, y1]` in the capture's **original pixels**. inspect_capture prints each capture's size. Image viewers, including the one you use to look at files, often show captures scaled down, so convert from what you see. Pick a card or section a user would care about (a stat, a chart, a form row) and keep whole rows inside the box.

### 5. Render and look

```bash
python3 $S/render.py                       # all targets in config.targets
python3 $S/render.py --only play-phone --slides 02_mileage   # fast iteration on one image
```

A full render takes about a second per image, so 40–70 images can run a minute or more. Give the command a long timeout, or run it in the background, and iterate with `--only` and `--slides`.

Open `store-assets/out/_review/sheet-<locale>.jpg` and look at it. Then open at least the hero and one feature slide per device class at full size. Check:

- Headlines are two short lines. Nothing has shrunk: the script prints a warning when it shrinks text.
- Each callout shows the right region and is readable at thumbnail size.
- Devices aren't cropped awkwardly, and the two hero devices don't hide each other's key content.
- iOS images made from Android captures show no Android-only UI (back arrow style, Material switches, toasts). The script warns for every such screen. Look at each one.
- The first 3 screenshots tell the whole story on their own, because that's all search results show.
- No device sits mostly empty (see "Sparse screens" in step 2), and no capture shows personal data or someone else's trademark.
- The feature graphic's devices aren't cut off at an important place. Nudge them with `banner.offset` or `banner.device_scale`.

Iterate by editing the config and re-rendering. The renderer is deterministic, so a fix stays fixed.

### 6. Icons (when asked, or when no store icon exists yet)

Read `references/icons.md`. With a transparent mark (SVG preferred) and the background colour or colours:

```bash
python3 $S/icons.py --mark branding/mark.svg --bg "#FF7A2E,#EE4D12" [--mono mark_mono.svg]
```

Look at `out/icons/preview.png`. Check the masks, that the safe-zone circle contains the mark, that the themed and tinted versions read, and that the 29px size is still recognisable.

Writing into the project with `--android-res` or `--ios-appiconset` overwrites the launcher icons. Confirm with the user before you do it.

### 7. Validate

`python3 $S/check.py` must end with 0 errors before you say the assets are ready. It also lints the copy and the Play alt text. Copy warnings are judgement calls: read each one and either fix it or tell the user why it's fine.

### 8. Hand off

Report:

- where the files are (`out/play/<locale>/…`, `out/appstore/<locale>/…`, `out/icons/…`)
- the upload order: Play Console → Main store listing; App Store Connect → the version's Previews and Screenshots
- the alt text for each Play image (140 characters or fewer, describing what is shown). render.py writes drafts to `out/alt-text-<locale>.md`; set `alt` on each slide and `banner` so none of them say TODO (check.py warns about missing or TODO alt text and fails any over 140 characters).
- what is unverified

Things that are usually unverified: iOS images built from Android captures, the iOS 27 header and search safe areas (check them in App Store Connect's preview), and anything the user still has to capture.

`render.py --fastlane fastlane` also lays files out for `fastlane supply` and `fastlane deliver`.

## Rules that save rejections

- **Specs:** they live in `scripts/specs.json`, dated. If `last_verified` is more than about 3 months old, re-check the source URLs listed there and update the file. The live store pages win over this skill.
- **No alpha:** screenshots and banners never have alpha. render.py flattens and check.py verifies. The App Store icon must be opaque too.
- **No banned copy:** no ranking, price, promo or call-to-action words, and no other store's name or platform. `references/copy.md` has the list and check.py enforces it.
- **Status bar:** full battery and signal, 9:41, no notifications. Personal data never appears in a capture: use a demo account.
- **Same capture size:** keep one capture size per set. Mixing sizes breaks the bar numbers.

## References

- `references/copy.md`: headline formulas, story order, banned words, localization. Read before step 2.
- `references/capture.md`: demo mode, iOS-aspect capture on Android, simctl, Flutter/RN tips, demo data. Read before step 3.
- `references/config.md`: every config field, layouts, themes and frames. Read when writing the config.
- `references/play-store.md`: all Play listing asset rules, including tablet, feature graphic and promotion eligibility.
- `references/app-store.md`: all App Store sizes, the iOS 27 header and search assets, and review guidelines that touch screenshots.
- `references/icons.md`: icon specs for both stores, adaptive and themed icons, iOS dark and tinted, and Icon Composer.

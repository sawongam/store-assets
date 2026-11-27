# store-assets/config.json

Relative paths resolve from the config's folder. Keep the config, captures and copy in the repo, so the next UI change is just "re-capture, re-render". Add `store-assets/out/` to `.gitignore` unless the user wants outputs committed.

```jsonc
{
  "brand": {
    "name": "pumpwise",                       // wordmark on hero + banners ("" to hide)
    "icon": "../branding/icon_1024.png",      // finished app icon, png/svg, 512+ px
    "theme": "dark",                          // dark | light | brand
    "accent": "#FF8645",                      // brand colour: accent words, eyebrows
    "highlight": "#FFE496",                   // brand theme only: accent-word colour on the brand canvas
    "background": ["#1B1C20", "#08080A"],     // optional: override the theme's top → bottom gradient
    "text": "#FFFFFF", "muted": "#A1A1AA", "glow": "#F4F4F8",   // optional overrides
    "frame": "graphite",                      // graphite | black | silver | titanium | "#hex" | none
    "fonts": {
      "display": "../assets/fonts/Brand-ExtraBold.ttf",          // headlines
      "body": "../assets/fonts/Text-Regular.ttf",                // sub-lines
      "body_bold": "../assets/fonts/Text-Medium.ttf",            // bullets, sheet labels
      "label": "../assets/fonts/Text-Bold.ttf",                  // eyebrows
      "status": "/path/Roboto-Medium.ttf"                        // optional: status-bar clock
      // variable font: {"path": "Inter.ttf", "axes": {"wght": 800}}; collection: {"path": "x.ttc", "index": 1}
    }
  },
  "locales": ["en-US", "de-DE"],             // first one is the fallback
  "captures": {                               // sets; names matter (see below)
    "phone":  {"platform": "android", "dir": "raw/phone", "status_bar_px": 98, "nav_bar_px": 46,
               "shots": {"home": "home.png", "stats": "stats.png"}},
    "tablet": {"platform": "android", "dir": "raw/tablet", "status_bar_px": 52, "nav_bar_px": 46, "shots": {...}},
    "iphone": {"platform": "android", "dir": "raw/iphone", ...},          // android-size iphone captures
    "ipad":   {"platform": "ios", "dir": "raw/{locale}/ipad", "bars": "keep", ...}   // simulator captures
  },
  "targets": ["play-phone", "play-tablet-7", "play-tablet-10", "play-feature-graphic",
              "ios-iphone-6.9", "ios-iphone-6.3", "ios-ipad-13"],
  "slides": [ ... ],
  "banner": { ... },
  "output": "out",                            // default <config dir>/out
  "format": "jpeg"                            // jpeg (default, small) | png
}
```

## Capture sets

| Set | Used by | Fallback |
|---|---|---|
| `phone` | play-phone, Play banner devices | none |
| `tablet` | play-tablet-7/10 | none |
| `iphone` | ios-iphone-*, App Store banner devices | `phone` (re-chromed to iOS) |
| `ipad` | ios-ipad-13 | `tablet` (re-chromed, warns about crop) |

Set fields:

- `platform`: `android` or `ios`. This is where the capture came from.
- `dir`: the capture folder. It may contain `{locale}`.
- `shots`: `{key: file}` or `{key: {"en-US": file, "de-DE": file}}`.
- `status_bar_px` / `nav_bar_px`: the bands to clean. Measure them with inspect_capture.py. If unset, the renderer guesses and warns.
- `bars`: `repaint` (Android default) or `keep` (iOS default; use it for demo-mode captures that already look right).
- `density`: optional px per dp for the Android status-bar drawing. The default is width / 411 (phone) or width / 800 (tablet).
- `kind`: `phone` or `tablet`, only needed for a custom set name.

## Slides

Each slide renders once per screenshot target, in order. Filenames are `NN_<id>.jpg`; give ids a `NN_` prefix to control the order.

```jsonc
{"id": "01_hero", "layout": "hero", "captures": ["home", "stats"],      // front, back (1 or 2)
 "headline": "Every tank,\n*counted.*", "body": "Mileage, fuel and spend for every ride."},

{"id": "02_mileage", "layout": "feature", "capture": "home",
 "eyebrow": "REAL MILEAGE · EVERY TANK",
 "headline": "Know what your\nride *really* does",
 "body": "optional sub-line",
 "callout": {"phone": [0, 960, 1080, 1645], "tablet": [0, 700, 1600, 1250]},
 "callout_width": 900,          // px at 1080 wide (default 900)
 "device_scale": 1.0,           // shrink/grow the device
 "frame": "none",               // per-slide frame override: none | graphite | silver | black | titanium | "#hex"
 "alt": "Home screen showing last tank mileage, distance and fill-up count",   // Play alt text, <=140 chars
 "headline_size": 88,           // px at 1080 wide
 "only": ["play"]}              // limit to stores / target ids / devices
```

Notes:

- **Text:** `\n` breaks a line and `*word*` gets the accent colour. Any text field can be a `{locale: text}` map.
- **callout:** `[x0, y0, x1, y1]` in **raw capture pixels** of the set being rendered. The region is lifted out of the device, enlarged and centred at the same height. A plain list applies to phone-class sets only; use the dict form for tablets and other sets. Choose a self-contained card (a stat block, a chart, a form row) that is legible when enlarged and doesn't cut a line of text in half.
- **only:** e.g. `["appstore"]`, `["play-phone"]` or `["iphone"]`. Use it for slides that only make sense on one store, such as a widget or Wear OS screen.

## Banner

This is the Play feature graphic plus the App Store header and search assets: one composition fitted into each target's safe box.

```jsonc
"banner": {
  "style": "devices",                   // devices (text left, 1-2 tilted phones right) | text (centred)
  "headline": "Every tank,\n*counted.*",
  "body": "Mileage, fuel and spend for every ride.",
  "captures": ["home", "stats"],                   // front, back
  "device_scale": 1.0,                             // grow/shrink the banner devices
  "offset": [0, 0],                                // move them, in board units (the board is 1024x500)
  "frame": "graphite",                             // or none
  "alt": "Pumpwise logo and tagline beside the home and stats screens",
  "safe": {"ios-header": [0.2, 0.12, 0.8, 0.88]}   // optional override, fractions of the canvas
}
```

Play's guidance for the feature graphic favours vibrant colour, a centred focal point and no device imagery for promotion slots. `style: "text"` with `theme: "brand"` meets all of that. Devices on a dark canvas look premium but may not be eligible for every promo format. Tell the user the trade-off.

## Targets

`render.py --only` takes any of these ids (sizes in `scripts/specs.json`):

| id | Output |
|---|---|
| `play-phone` | 1080×1920 |
| `play-tablet-7` | 1440×2560 |
| `play-tablet-10` | 1800×3200 |
| `play-feature-graphic` | 1024×500 |
| `ios-iphone-6.9` | 1320×2868 |
| `ios-iphone-6.3` | 1206×2622 |
| `ios-ipad-13` | 2064×2752 |
| `ios-header` | 3840×1646, experimental, iOS 27+ |
| `ios-search` | 3840×2560, experimental, iOS 27+ |

Experimental targets render only when listed in `config.targets` or named with `--only`.

## Output layout

```
out/
├── play/<locale>/phone/NN_<id>.jpg   tablet-7/…   tablet-10/…   feature-graphic.jpg
├── appstore/<locale>/iphone-6.9/…   iphone-6.3/…   ipad-13/…   product-page-header.jpg   search-result.jpg
├── icons/…                           (icons.py)
├── alt-text-<locale>.md              Play alt text, drafts marked TODO
├── manifest.json                     what check.py validates
└── _review/sheet-<locale>.jpg        contact sheet; *-guides.jpg with --guides
```

## Colours by role

| Role | dark / light | brand |
|---|---|---|
| Accent words and eyebrows | `accent` (nudged to 3:1 contrast) | `highlight` (default cream) |
| Headline text | `text` | `text` |
| Sub-lines | `muted` | `muted` |
| Check circles | `check` | `check` |

## Themes

| Theme | Look | Best for |
|---|---|---|
| `dark` | Graphite gradient, soft white glow from the screen, accent on words | Light-UI apps; premium, calm |
| `light` | Off-white tinted toward the accent, soft shadows | Dark-UI apps; friendly, clean |
| `brand` | Accent-coloured gradient, cream accent words (or `highlight`) | Bold brands, kids, games, promo-friendly feature graphic |

The accent is nudged until it reaches 3:1 contrast on the canvas, which is the minimum for large text. On `light`, a bright accent may come out darker. Set a deeper `accent` if the brand hue drifts.

`frame: "none"` drops the device and shows the screen as a rounded card. It's cleaner, ages better, and matches Play's "avoid device imagery" advice.

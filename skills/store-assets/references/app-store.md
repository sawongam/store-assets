# App Store product page assets

Source: App Store Connect Help, "Screenshot specifications" and "App preview specifications". Last verified: see `scripts/specs.json`. Apple adds sizes with new hardware, so re-check the live table before a big release.

## Screenshots

- 1–10 per device size and localization. JPEG or PNG, **no alpha or transparency**.
- If the UI is the same across sizes, provide the largest required size and App Store Connect scales it down for smaller devices.

### iPhone (portrait sizes; landscape is the same swapped)

| Display class | Accepted | Notes |
|---|---|---|
| 6.9" (Dynamic Island, large) | **1320×2868**, 1290×2796, 1260×2736 | the size to design for |
| 6.5" (Face ID, large) | 1284×2778, 1242×2688 | needed only if there are no 6.9" shots |
| 6.3" (Dynamic Island, medium) | **1206×2622**, 1179×2556 | listed as required; falls back to scaled larger shots. Render it to be safe |
| 6.1" and smaller | 1170×2532, 1125×2436, 1080×2340, 1242×2208, 750×1334 … | scaled from the classes above |

The fetched table also lists an "iPhone Duo" (outer 1398×2034, inner 2007×2853), with a note that screenshots become required for apps built with the iOS 27.1 SDK or later from April 2027. Check the live page before relying on this. It's not rendered by default.

### iPad (required only when the app runs on iPad)

| Display | Accepted |
|---|---|
| 13" | **2064×2752**, 2048×2732 |
| 12.9", 11", 10.5", 9.7" | scaled from 13" |

## iOS 27 product page header and search results assets (optional, experimental here)

Apple introduced these with the App Store Asset Library in Oct 2026. They show only to viewers on iOS and iPadOS 27 or later, and they sit **alongside** screenshots rather than replacing them. Once one app version is approved, they can be published without a new version, with their own review.

| Asset | Ratio | Size | Format |
|---|---|---|---|
| Product page header | 21:9 | 3840×1646 | PNG or JPEG |
| Search results asset | 3:2 | 1920×1280 – 3840×2560 | PNG or JPEG |
| Universal (fills both) | 16:9 | 5244×2950 | PNG only |

Video versions exist too: 5–30 s loops, which this skill doesn't make.

Apple publishes no pixel safe areas, only Photoshop templates and the preview tool in App Store Connect. The safe boxes in `specs.json` are conservative estimates (`safe_verified: false`). Render with `--guides`, then confirm placement in App Store Connect's preview before publishing. Enable them with `"targets": [..., "ios-header", "ios-search"]`.

## App previews (video, not made by this skill)

- Up to 3 per size and language, 15–30 s, ≤ 500 MB, 30 fps max.
- H.264 or ProRes 422 HQ, in `.mov`, `.m4v` or `.mp4`.
- iPhone 6.9"/6.5": 886×1920. iPad 13": 1200×1600.

## Review guidelines that touch screenshots

- **2.3.3:** screenshots must show the app in use, not just title art, logos or splash screens. Text and image overlays are fine.
- **2.3.7 / 2.3.10:** no other platforms' names, icons or devices (no Android, no Google Play), and no fake price, ranking or awards. Keep metadata appropriate for a 4+ audience.
- **Accuracy:** UI in screenshots must match the app. Re-chromed Android captures are acceptable only when the iOS build really looks like that. Verify on a real iOS build.
- **No personal data:** use demo accounts.

## Upload

App Store Connect → your app → the version → Previews and Screenshots:

- **iPhone 6.9":** `out/appstore/<locale>/iphone-6.9/*`
- **iPhone 6.3":** `iphone-6.3/*`
- **iPad 13":** `ipad-13/*`

Drag to reorder. The first three appear in search.

The header and search assets go in App Store Connect's Asset Library.

`render.py --fastlane fastlane` writes `fastlane/screenshots/<locale>/NN_id_<target>.jpg`. `deliver` detects the device class from the pixel size.

The App Store icon comes from the app binary (the asset catalog or Icon Composer file), not from an upload.

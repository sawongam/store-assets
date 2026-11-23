# Google Play listing graphics

Source: Play Console Help, "Add preview assets" (support.google.com/googleplay/android-developer/answer/9866151), and the Play icon design specs. Last verified: see `scripts/specs.json`.

## Required to publish

| Asset | Spec |
|---|---|
| App icon | 512×512, 32-bit PNG (alpha allowed but opaque is safer), ≤ 1024 KB, full square. Play applies the mask (30% radius) and the shadow, so don't round it or add a shadow. |
| Feature graphic | 1024×500, JPEG or 24-bit PNG, **no alpha** |
| Screenshots | At least 2 across device types. JPEG or 24-bit PNG, no alpha, ≤ 8 MB each |

## Screenshots per device type

| Type | Count | Sides | Notes |
|---|---|---|---|
| Phone | 2–8 | 320–3840 px | 9:16 or 16:9. Long side ≤ 2.3× short side |
| 7-inch tablet | 4–8 for large-screen eligibility | 1080–7680 px | 9:16 or 16:9 |
| 10-inch tablet | 4–8 for large-screen eligibility | 1080–7680 px | 9:16 or 16:9 |
| Chromebook | 4–8 | 1080–7680 px | 16:9 landscape |
| Foldables | 3–8 | 960–3840 px | needs a 1:1 inner, a 4:3 inner landscape and a 10:16 outer |
| Wear OS | 1+ | ≥ 384×384, 1:1 | UI only: no frames, no text, no backgrounds |
| Android TV | 1+ plus a 1280×720 banner | | TV screenshots show on TV only |
| Android XR | 4–8 | 8:5, ≥ 1920×1200 | |

This skill renders phone (1080×1920) and both tablet sizes (1440×2560, 1800×3200) as 9:16 portrait. Add other form factors by hand if the app supports them.

## Promotion eligibility ("highly recommended", but required for the screenshot-based promo formats)

- **Apps:** 4 or more screenshots at 1080px or more on the short side (9:16 at ≥ 1080×1920, or 16:9 at ≥ 1920×1080).
- **Games:** 3 or more landscape (or portrait) shots of actual gameplay.
- **Large screens:** tablet and Chromebook screenshots are needed to rank well on large-screen devices.

## Content rules for screenshots

**Required**

- Show the actual in-app experience. You may stylise by spreading UI across images, but keep UI prominent in the first 3.
- Clean the status bar: no carrier, no notifications, full battery, wifi and cell.
- No blurry, stretched or wrongly rotated images.
- No Play badges or other store badges, and no third-party trademarks without permission.

**Promotion guidance (highly recommended)**

- Taglines only where needed, taking at most ~20% of the image.
- No ranking or award words ("Best", "#1", "Top", "Award"), no price or promo ("Free", "Sale", "Discount", "Million downloads"), and no calls to action ("Download now", "Install now").
- Avoid small text and busy backgrounds behind text.
- Avoid time-sensitive copy.
- Localize taglines.
- "Avoid device imagery", because frames date quickly. Frameless (`frame: "none"`) follows this best, and device frames are a deliberate style choice.
- Provide alt text, 140 characters or fewer.

## Feature graphic

The feature graphic appears at the top of the listing, in promos, and as the video cover when there's a promo video (with a play button over the centre).

- Keep the focal point (logo, name, slogan) centred. Edges may be cropped in some placements.
- Use vibrant colour. Pure white, black or dark grey blend into Play's backgrounds, and check.py warns about mostly-dark graphics.
- Avoid fine detail, which isn't legible on phones.
- Don't repeat the icon in a big way. A small icon and wordmark is fine.
- Same copy bans as screenshots. No store badges, and avoid device imagery for promo eligibility.
- Provide alt text, 140 characters or fewer.

## Upload

Play Console → Grow users → Store presence → Main store listing → Graphics:

- **Icon:** `out/icons/play/icon-512.png`
- **Feature graphic:** `out/play/<locale>/feature-graphic.jpg`
- **Phone screenshots:** `out/play/<locale>/phone/*`
- **7-inch tablet:** `out/play/<locale>/tablet-7/*`
- **10-inch tablet:** `out/play/<locale>/tablet-10/*`

Translations go under Custom store listings or Translations, one per locale.

`render.py --fastlane fastlane` writes the `fastlane supply` layout: `metadata/android/<locale>/images/{icon.png, featureGraphic.jpg, phoneScreenshots/, sevenInchScreenshots/, tenInchScreenshots/}`.

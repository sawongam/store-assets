# Capturing real screens

The renderer only frames what you capture, so the captures decide the quality ceiling. The ideal is a seeded demo account, the same device for the whole set, a clean status bar, and real UI.

## Before capturing

- **Demo data:** fill the app with realistic, attractive data: varied numbers, non-empty charts, plausible names. Never use real personal data, emails or phone numbers. If the app has a seed or demo mode, use it. Otherwise ask the user to create a demo account.
- **Theme:** capture light or dark mode to match the store theme. Light UI on the dark canvas pops, and dark UI on a light canvas works too.
- **One device per set:** every capture in a set must be the same size, because bar heights are measured once per set.
- **Gesture navigation:** prefer gesture navigation over the 3-button bar. It leaves a thin handle that's easy to clean.

## Android (emulator or device)

```bash
S=<skill>/scripts
$S/capture.sh android-demo on               # 9:41, full wifi/cell/battery, notifications hidden
# open each screen in the app, then:
$S/capture.sh android-shot home store-assets/raw/phone
$S/capture.sh android-shot stats store-assets/raw/phone
$S/capture.sh android-demo off
```

Good emulator profiles:

| Use | Profile |
|---|---|
| Phone | Pixel 8 / 9 (1080×2400) |
| Tablet | Pixel Tablet (1600×2560) |
| 10-inch-class tablet | Nexus 10 / Generic 10.1" at 2560×1600 |

Rotate as needed.

The demo-mode broadcast needs `sysui_demo_allowed`, which the script sets. Some OEM ROMs ignore it. render.py repaints the bar anyway, so captures stay usable.

## iOS without a Mac: capture at the iOS aspect on Android

For Flutter, React Native, Compose Multiplatform and web views, the UI renders the same on both platforms. Resize the Android display to the iPhone's pixel size and point width, then capture:

```bash
$S/capture.sh android-size iphone           # 1320x2868 @ 480dpi → 440pt wide, like iPhone 6.9"
$S/capture.sh android-shot home store-assets/raw/iphone
$S/capture.sh android-size ipad             # 2064x2752 @ 320dpi → 1032pt, like iPad 13"
$S/capture.sh android-shot home store-assets/raw/ipad
$S/capture.sh android-size reset
```

In the config, declare these sets as `"iphone": {"platform": "android", ...}` and `"ipad": {...}`. render.py removes the Android bars and adds an iOS status bar (time in the left ear, signal, wifi and battery on the right), a home indicator, and the Dynamic Island frame.

Limits:

- **Android-looking UI:** platform-adaptive widgets still look like Android: back arrows, switches, date pickers, snackbars and share sheets. In Flutter you can render iOS-style widgets by building a capture flavor with `debugDefaultTargetPlatformOverride = TargetPlatform.iOS` (debug only) or a `--dart-define` that sets `ThemeData(platform: TargetPlatform.iOS)`. Otherwise pick screens without those widgets.
- **Falling back to phone captures:** without an `iphone` set, render.py falls back to the `phone` set and re-chromes it. A 20:9 Android capture is close to the iPhone's 19.5:9, so it works, but expect a slight bottom crop. Tablet captures at 10:16 are far from the iPad's 3:4, so render.py warns about large crops. Use `android-size ipad` instead.
- **Apple's rule:** screenshots must show the app as it runs on iOS. Ask the user to compare against a real iOS build (TestFlight or a friend's Mac) before the first submission.

## iOS Simulator (macOS)

```bash
xcrun simctl boot "iPhone 17 Pro Max"     # 6.9" class, 1320x2868
$S/capture.sh ios-demo                      # 9:41, full bars, charged
$S/capture.sh ios-shot home store-assets/raw/iphone
```

Use the iPad Pro 13-inch (M4/M5) simulator for 2064×2752 captures. Set `"platform": "ios", "bars": "keep"` for simulator sets, because the override already cleaned the bar.

## Automating captures (optional)

- **Flutter:** use an `integration_test` with `binding.takeScreenshot('home')` plus a driver that writes the PNGs (`flutter drive --driver=test_driver/integration_test.dart --target=integration_test/screenshots_test.dart`). Seed data in the test.
- **Native Android:** Fastlane `screengrab` with Espresso, or a Maestro flow.
- **iOS:** an XCUITest plus `fastlane snapshot`, or a Maestro flow.
- **React Native and Expo:** Maestro or Detox.

Automated captures pay off once there are several locales or frequent UI changes.

## Measuring bars

```bash
python3 $S/inspect_capture.py store-assets/raw/phone/home.png store-assets/raw/phone/stats.png
```

Look at the guide image. Red lines are the guesses. Set:

- `status_bar_px`: the first row below the clock, icons and camera cut-out. Too small leaves glyphs behind; too large eats the app's header.
- `nav_bar_px`: the height of the gesture handle or button bar from the bottom.

The repaint stretches the first clean row over the band. That's ideal when the app's top bar is a flat colour. If the app draws a gradient or image under the status bar, use demo mode and set `"bars": "keep"`. The demo bar is already clean.

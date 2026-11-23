# Icons for both stores

The best input is a **mark** (the symbol alone, on a transparent canvas, ideally SVG) plus a **background** (one colour or a 2-stop gradient). With those, `icons.py` can build every variant, including the layered and monochrome ones. A flattened icon PNG (`--icon`) only yields the store icons.

Good mark sources, from `scan_brand.py`: `*_mark.svg`, `logo.svg`, Android `ic_launcher_foreground` vectors, the layers in an Icon Composer `.icon/Assets/`, or the designer's export. If the only source is a flat icon, ask for the mark rather than tracing it.

```bash
python3 $S/icons.py --mark branding/mark.svg --bg "#FF7A2E,#EE4D12" \
    [--mono branding/mark_mono.svg] [--dark-mark branding/mark_light.svg] \
    [--mark-size 0.60] [--adaptive-size 0.46] [--out store-assets/out/icons]
```

## What it writes, and the rules behind each file

| File | Rule |
|---|---|
| `play/icon-512.png` | Play listing icon: 512×512 PNG, ≤ 1024 KB, full square. Play rounds it (30% radius) and adds the shadow. Not the launcher icon. |
| `appstore/icon-1024.png` | App Store icon: 1024×1024, **opaque**, square, no pre-rounded corners. The system applies the mask. |
| `appstore/AppIcon.appiconset/` | Xcode asset catalog with light, **dark** and **tinted** appearances (iOS 18+). Dark is the mark on transparent, and iOS supplies the dark backdrop. Tinted is a white mark on black, which iOS tints. |
| `icon-composer/AppIcon.icon/` | Starter **Icon Composer** bundle (Xcode 26+, Liquid Glass): a glass group holding the mark over the brand fill. Open it in Icon Composer to tune glass, specular and shadow, and check every appearance, before replacing the project's icon. `background.png` and `foreground.png` sit next to it for building one by hand. |
| `android/res/mipmap-anydpi-v26/ic_launcher*.xml` | Adaptive icon: background, foreground and monochrome layers. |
| `android/res/mipmap-*/ic_launcher_{foreground,background,monochrome}.png` | 108dp layers at every density. Launchers mask them to circles, squircles and so on, and animate (parallax), so only the centre 72dp is ever visible and the **66dp safe circle** is never clipped. The mark is auto-shrunk to sit inside it. |
| `…/ic_launcher_monochrome.png` | **Themed icons** (Android 13+): the system takes the alpha and tints it with the wallpaper colour. From Android 16 QPR2 the system auto-themes apps that don't provide one, usually badly, so provide one. |
| `…/ic_launcher.png`, `ic_launcher_round.png` | Legacy launchers (API < 26). |
| `preview.png` | Every mask plus 60/40/29 px sizes. **Look at it.** |

## Judging the preview

- **Safe-zone tile:** the mark sits inside the red circle with margin. A wide wordmark-style mark will look tiny, so ask for a compact symbol.
- **29px:** still recognisable. Fine strokes disappear first. Thicken them or simplify the mark for small sizes.
- **Themed and tinted:** the shape alone must still read, because colour is gone. A mark whose meaning depends on two colours (a coloured dot, for example) needs a `--mono` variant that keeps the shape distinct.
- **Dark:** the mark must be light enough for a dark backdrop. Pass `--dark-mark` with a light version if the mark is dark.

## Writing into the project (confirm with the user first)

- **Android:** `--android-res android/app/src/main/res` copies the mipmaps and XML. Then:
  - Check `AndroidManifest.xml` for `android:icon="@mipmap/ic_launcher"` and `android:roundIcon="@mipmap/ic_launcher_round"`.
  - Delete stale `drawable/ic_launcher_*.xml` that would shadow the mipmaps.
  - For product flavors, write the dev icon into `src/dev/res` with a second run using different colours.
- **iOS asset catalog:** `--ios-appiconset ios/Runner/Assets.xcassets/AppIcon.appiconset` (Flutter), or `<App>/Assets.xcassets/AppIcon.appiconset`.
- **Icon Composer:** if the project already uses a `.icon` file, which Xcode references as `folder.iconcomposer.icon`, update that instead. Copy `Assets/Mark.png` and adjust `icon.json`, or rebuild it in Icon Composer.
- **Tooling:** Flutter's `flutter_launcher_icons` and Expo's `app.json` icon fields regenerate icons on build. If the project uses them, point their config at the new files instead of writing res folders that will be overwritten.

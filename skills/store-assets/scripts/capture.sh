#!/usr/bin/env bash
# Clean, repeatable store captures from an Android emulator/device or the iOS Simulator.
#
#   capture.sh android-demo on|off        clean status bar: 9:41, full battery/wifi, no notifications
#   capture.sh android-size iphone|iphone-6.3|ipad|android-tablet|reset
#                                         resize the Android display to an iOS screen (same aspect and
#                                         logical points), so iOS shots need no cropping
#   capture.sh android-shot NAME [DIR]    save DIR/NAME.png (default DIR: store-assets/raw/phone)
#   capture.sh ios-demo [DEVICE]          simctl status bar override (DEVICE default: booted)
#   capture.sh ios-shot NAME [DIR]        save DIR/NAME.png from the booted simulator
#
# ANDROID_SERIAL picks a device when several are connected. Nothing here installs or launches the
# app: open the screen you want, then shoot.
set -euo pipefail

cmd="${1:-help}"
shift || true

adb_() { adb ${ANDROID_SERIAL:+-s "$ANDROID_SERIAL"} "$@"; }
demo() { adb_ shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }

case "$cmd" in
  android-demo)
    case "${1:-on}" in
      on)
        adb_ shell settings put global sysui_demo_allowed 1
        demo enter
        demo clock -e hhmm 0941
        demo battery -e level 100 -e plugged false -e powersave false
        demo network -e wifi show -e level 4 -e fully true
        demo network -e mobile show -e datatype none -e level 4 -e fully true
        demo network -e airplane hide
        demo notifications -e visible false
        demo status -e volume hide -e bluetooth hide -e location hide -e alarm hide -e zen hide -e mute hide
        echo "demo mode on: 9:41, full bars, no notifications" ;;
      off)
        demo exit
        echo "demo mode off" ;;
      *) echo "android-demo on|off" >&2; exit 2 ;;
    esac ;;

  android-size)
    # density = physical px / logical width * 160, so the app lays out at the iOS point width
    case "${1:-}" in
      iphone)          adb_ shell wm size 1320x2868; adb_ shell wm density 480 ;;   # 6.9" (440 pt wide)
      iphone-6.3)      adb_ shell wm size 1206x2622; adb_ shell wm density 480 ;;   # 6.3" (402 pt wide)
      ipad)            adb_ shell wm size 2064x2752; adb_ shell wm density 320 ;;   # 13"  (1032 pt wide)
      android-tablet)  adb_ shell wm size 1600x2560; adb_ shell wm density 320 ;;
      reset)           adb_ shell wm size reset; adb_ shell wm density reset ;;
      *) echo "android-size iphone|iphone-6.3|ipad|android-tablet|reset" >&2; exit 2 ;;
    esac
    adb_ shell wm size; adb_ shell wm density ;;

  android-shot)
    name="${1:?android-shot NAME [DIR]}"; dir="${2:-store-assets/raw/phone}"
    mkdir -p "$dir"
    adb_ exec-out screencap -p > "$dir/$name.png"
    python3 - "$dir/$name.png" <<'PY' 2>/dev/null || echo "wrote $dir/$name.png"
import sys
from PIL import Image
p = sys.argv[1]
print(f"wrote {p} {Image.open(p).size[0]}x{Image.open(p).size[1]}")
PY
    ;;

  ios-demo)
    dev="${1:-booted}"
    xcrun simctl status_bar "$dev" override --time "9:41" --dataNetwork wifi --wifiMode active --wifiBars 3 \
      --cellularMode active --cellularBars 4 --operatorName "" --batteryState charged --batteryLevel 100
    echo "simulator status bar: 9:41, full bars" ;;

  ios-shot)
    name="${1:?ios-shot NAME [DIR]}"; dir="${2:-store-assets/raw/iphone}"
    mkdir -p "$dir"
    xcrun simctl io booted screenshot --type=png "$dir/$name.png" >/dev/null
    echo "wrote $dir/$name.png" ;;

  *)
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
esac

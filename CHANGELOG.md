# Changelog

## 1.1.0

- Removed the `closing` layout and `brand.check`. A config with a closing slide now stops and tells you to delete it.
- Fixed punch-hole cameras getting smeared across the status bar. The renderer now skips past the cut-out and warns with the value to set.

## 1.0.1

- Fixed crashes on Windows with non-ASCII text (files are now read and written as UTF-8).
- Fixed feature graphic text running under the devices.
- Fixed `--slides` renders differing from full renders (grain is now seeded).
- Fixed `--only ios-header|ios-search` rendering nothing.
- Full render is about 2x faster.
- `check.py` now lints Play alt text.
- Added Codex, Cursor and Gemini CLI packaging.
- Added tests, CI and `AGENTS.md`.

## 1.0.0

First release: store screenshots, feature graphic and icons for Play and the App Store, with device frames, capture cleaning, locales, fastlane export and a `check.py` validator.

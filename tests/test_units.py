"""Fast unit tests: colour maths, masks, the copy/alt lint and the image validator."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from _fixtures import SCRIPTS

sys.path.insert(0, str(SCRIPTS))

import check  # noqa: E402
from sa import chrome, core  # noqa: E402
from sa.project import load_specs  # noqa: E402


def punch_hole_capture() -> Image.Image:
    """A white status band whose centred camera cut-out (rows 30-101) reaches below the clock (rows 45-85)."""
    im = Image.new("RGB", (1080, 2400), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((75, 45, 190, 85), fill=(60, 60, 60))  # clock
    d.rectangle((890, 45, 1005, 85), fill=(60, 60, 60))  # icons
    d.ellipse((504, 30, 576, 101), fill=(0, 0, 0))  # punch-hole
    d.rectangle((64, 160, 400, 240), fill=(20, 20, 20))  # page title
    return im


class Bars(unittest.TestCase):
    def setUp(self):
        core.WARNINGS.clear()
        core.GROUPS.clear()

    def test_guess_covers_camera_cutout(self):
        status, _ = chrome.suggest_bars(punch_hole_capture())
        self.assertGreater(status, 101)
        self.assertLess(status, 160)

    def test_short_band_does_not_smear_cutout(self):
        scr = chrome.make_screen(punch_hole_capture(), src_platform="android", kind="phone", target_platform="android",
                                 target_aspect=None, status_px=97, nav_px=0, mode="repaint", fonts=None, density=None)
        column = [scr.img.getpixel((540, y)) for y in range(0, 110)]
        self.assertTrue(all(min(px) > 200 for px in column), "cut-out stretched into a line")
        self.assertTrue(any("camera cut-out" in t for t in core.GROUPS))

    def test_clean_band_is_left_alone(self):
        chrome.make_screen(punch_hole_capture(), src_platform="android", kind="phone", target_platform="android",
                           target_aspect=None, status_px=115, nav_px=0, mode="repaint", fonts=None, density=None)
        self.assertFalse(core.GROUPS)


class Core(unittest.TestCase):
    def test_hex_rgb(self):
        self.assertEqual(core.hex_rgb("#FF7A2E"), (255, 122, 46))
        self.assertEqual(core.hex_rgb("f72"), (255, 119, 34))
        self.assertEqual(core.hex_rgb([1, 2, 3, 4]), (1, 2, 3))
        with self.assertRaises(ValueError):
            core.hex_rgb("#12345")

    def test_ensure_contrast_reaches_target(self):
        bg = (20, 20, 24)
        self.assertGreaterEqual(core.contrast(core.ensure_contrast((40, 40, 200), bg, 3.0), bg), 3.0)

    def test_rr_mask_shape(self):
        m = core.rr_mask((300, 200), 40)
        self.assertEqual(m.size, (300, 200))
        self.assertEqual(m.getpixel((0, 0)), 0)  # corner cut
        self.assertEqual(m.getpixel((150, 0)), 255)  # straight edge kept
        self.assertEqual(m.getpixel((150, 100)), 255)
        # all four corners are mirror images
        self.assertEqual(m.getpixel((5, 5)), m.getpixel((294, 194)))
        self.assertEqual(m.getpixel((5, 194)), m.getpixel((294, 5)))

    def test_rr_mask_is_a_copy(self):
        a = core.rr_mask((50, 50), 10)
        a.putpixel((25, 25), 0)
        self.assertEqual(core.rr_mask((50, 50), 10).getpixel((25, 25)), 255)

    def test_rr_mask_radius_clamped(self):
        self.assertEqual(core.rr_mask((40, 20), 999).size, (40, 20))

    def test_runs(self):
        self.assertEqual(core.runs("Log it in *seconds*"), [("Log it in ", False), ("seconds", True)])


class Lint(unittest.TestCase):
    def setUp(self):
        check.ERR.clear()
        check.WARN.clear()
        self.specs = load_specs()

    def lint(self, targets, **slide):
        s = {"id": "01", "layout": "feature", "capture": "home", "alt": "Home screen", **slide}
        check.lint_copy({"targets": targets, "slides": [s]}, self.specs)

    def test_banned_word_fails_everywhere(self):
        self.lint(["play-phone"], headline="The *best* tracker")
        self.assertTrue(any("'best'" in e for e in check.ERR))

    def test_whole_word_only(self):
        self.lint(["play-phone"], headline="Bestow your *data*")
        self.assertEqual(check.ERR, [])

    def test_other_platform_depends_on_store(self):
        self.lint(["play-phone"], headline="Also on Android")
        self.assertEqual(check.ERR, [])
        self.lint(["ios-iphone-6.9"], headline="Also on Android")
        self.assertTrue(any("App Store" in e for e in check.ERR))

    def test_only_limits_store(self):
        self.lint(["play-phone", "ios-iphone-6.9"], headline="Works with iPhone", only=["appstore"])
        self.assertEqual(check.ERR, [])

    def test_alt_text_rules(self):
        self.lint(["play-phone"], alt="x" * 141)
        self.assertTrue(any("141 characters" in e for e in check.ERR))
        check.ERR.clear()
        self.lint(["play-phone"], alt="TODO: home")
        self.assertTrue(any("TODO" in w for w in check.WARN))
        check.WARN.clear()
        self.lint(["play-phone"], alt="Screenshot of the home screen")
        self.assertTrue(any("describe what is shown" in w for w in check.WARN))

    def test_missing_alt_warns_for_play_only(self):
        self.lint(["ios-iphone-6.9"], alt=None)
        self.assertFalse(any("alt" in w for w in check.WARN))
        self.lint(["play-phone"], alt=None)
        self.assertTrue(any("no alt text" in w for w in check.WARN))


class Validator(unittest.TestCase):
    def setUp(self):
        check.ERR.clear()
        self.specs = load_specs()
        self.tmp = Path(tempfile.mkdtemp(prefix="sa-unit-"))

    def test_alpha_rejected(self):
        p = self.tmp / "a.png"
        Image.new("RGBA", (1080, 1920)).save(p)
        check.check_image(p, "a", self.specs["targets"]["play-phone"])
        self.assertTrue(any("alpha" in e for e in check.ERR))

    def test_wrong_iphone_size_rejected(self):
        p = self.tmp / "b.png"
        Image.new("RGB", (1080, 1920)).save(p)
        check.check_image(p, "b", self.specs["targets"]["ios-iphone-6.9"])
        self.assertTrue(any("not an accepted size" in e for e in check.ERR))

    def test_play_ratio_limit(self):
        p = self.tmp / "c.png"
        Image.new("RGB", (400, 1000)).save(p)
        check.check_image(p, "c", self.specs["targets"]["play-phone"])
        self.assertTrue(any("2.3x" in e for e in check.ERR))


if __name__ == "__main__":
    unittest.main()

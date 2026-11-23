"""End to end: render -> check, icons -> check, determinism, and the bugs fixed before 1.0."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from _fixtures import make_project, run

TARGETS = ["play-phone", "play-feature-graphic", "ios-iphone-6.9", "ios-ipad-13"]


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


class RenderPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="sa-test-"))
        make_project(cls.tmp, TARGETS)
        cls.render = run("render.py", cwd=cls.tmp)
        cls.out = cls.tmp / "store-assets" / "out"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_render_succeeds(self):
        self.assertEqual(self.render.returncode, 0, self.render.stdout + self.render.stderr)

    def test_outputs_match_specs(self):
        specs = json.loads((Path(__file__).parent.parent / "skills/store-assets/scripts/specs.json").read_text())
        manifest = json.loads((self.out / "manifest.json").read_text())["files"]
        self.assertEqual(len(manifest), 4 + 1 + 4 + 4)
        for m in manifest:
            with Image.open(self.out / m["path"]) as im:
                self.assertEqual(list(im.size), specs["targets"][m["target"]]["size"], m["path"])
                self.assertEqual(im.mode, "RGB", f"{m['path']} must not carry alpha")

    def test_check_passes(self):
        r = run("check.py", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("0 errors", r.stdout)

    def test_review_sheet_and_alt_text(self):
        self.assertTrue((self.out / "_review" / "sheet-en-US.jpg").exists())
        lines = [ln for ln in (self.out / "alt-text-en-US.md").read_text(encoding="utf-8").splitlines()
                 if ln.startswith("- ")]
        self.assertEqual(len(lines), 5)  # 4 phone screenshots + the feature graphic
        self.assertEqual(lines, sorted(lines))
        self.assertFalse([ln for ln in lines if "TODO" in ln])

    def test_partial_render_is_identical(self):
        """A slide rendered alone must match the full render byte for byte (grain is seeded)."""
        p = self.out / "play" / "en-US" / "phone" / "03_add.jpg"
        before = md5(p)
        r = run("render.py", "--only", "play-phone", "--slides", "03_add", "--no-sheet", cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(md5(p), before)
        # the partial run keeps the rest of the manifest
        self.assertEqual(len(json.loads((self.out / "manifest.json").read_text())["files"]), 13)

    def test_banner_text_stays_clear_of_devices(self):
        """The banner body used to run under the phones and get cut off. Every text box must now sit
        where no device covers it (the renderer shrinks the text, with a warning, to make it fit)."""
        import sys

        from _fixtures import SCRIPTS
        sys.path.insert(0, str(SCRIPTS))
        import render
        from sa import layouts
        from sa.project import Project, load_config

        tmp = Path(tempfile.mkdtemp(prefix="sa-banner-"))
        boxes, devices = [], []
        real_text, real_place = layouts.core.text_block, layouts.place

        def text_block(d, text, **kw):
            bottom, size = real_text(d, text, **kw)
            boxes.append((kw["x"], kw["y"], kw["x"] + kw["max_w"], bottom, kw["label"]))
            return bottom, size

        def place(ctx, canvas, img, cx, cy, angle=0.0, shadow=None):
            a = img.getchannel("A")
            a = a.rotate(angle, expand=True) if angle else a
            cover = Image.new("L", canvas.size, 0)
            cover.paste(a, (round(cx - a.width / 2), round(cy - a.height / 2)))
            devices.append(cover)
            return real_place(ctx, canvas, img, cx, cy, angle, shadow)

        try:
            for body in ("One short sentence that says what the app is.",
                         "A much longer line of body copy that keeps on going past where the phones begin."):
                boxes.clear()
                devices.clear()
                cfg_path = make_project(tmp, ["play-feature-graphic"])
                cfg = json.loads(cfg_path.read_text())
                cfg["banner"]["body"] = body
                cfg_path.write_text(json.dumps(cfg))
                project = Project(*load_config(cfg_path))
                layouts.core.text_block, layouts.place = text_block, place
                try:
                    render.render_target(project, "play-feature-graphic",
                                         project.specs["targets"]["play-feature-graphic"], "en-US",
                                         tmp / "out", "jpeg", None, False, [])
                finally:
                    layouts.core.text_block, layouts.place = real_text, real_place
                self.assertEqual(len(boxes), 2)
                self.assertEqual(len(devices), 2)
                for x0, y0, x1, y1, label in boxes:
                    for cover in devices:
                        hit = cover.crop((round(x0), round(y0), round(x1), round(y1))).point(
                            lambda p: 255 if p > 40 else 0).getbbox()
                        self.assertIsNone(hit, f"{label} box overlaps a device ({body!r})")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_only_renders_experimental_target(self):
        """Experimental targets skip a plain run but render when asked for by --only."""
        tmp = Path(tempfile.mkdtemp(prefix="sa-exp-"))
        try:
            make_project(tmp, ["play-phone"])
            header = tmp / "store-assets" / "out" / "appstore" / "en-US" / "product-page-header.jpg"
            r = run("render.py", "--only", "ios-header", "--no-sheet", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(header.exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Icons(unittest.TestCase):
    def test_icons_from_png_mark(self):
        tmp = Path(tempfile.mkdtemp(prefix="sa-icons-"))
        try:
            mark = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
            mark.paste((255, 255, 255, 255), (200, 100, 600, 700))
            mark.save(tmp / "mark.png")
            r = run("icons.py", "--mark", "mark.png", "--bg", "#FF7A2E,#EE4D12", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = tmp / "store-assets" / "out" / "icons"
            with Image.open(out / "appstore" / "icon-1024.png") as im:
                self.assertEqual((im.size, im.mode), ((1024, 1024), "RGB"))
            with Image.open(out / "play" / "icon-512.png") as im:
                self.assertEqual(im.size, (512, 512))
            for f in ("android/res/mipmap-anydpi-v26/ic_launcher.xml",
                      "android/res/mipmap-xxxhdpi/ic_launcher_monochrome.png",
                      "appstore/AppIcon.appiconset/Contents.json", "icon-composer/AppIcon.icon/icon.json",
                      "preview.png"):
                self.assertTrue((out / f).exists(), f)
            c = run("check.py", "--file", str(out / "appstore" / "icon-1024.png"), "--target", "ios-icon", cwd=tmp)
            self.assertEqual(c.returncode, 0, c.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Inspect(unittest.TestCase):
    def test_bar_guess_is_close(self):
        tmp = Path(tempfile.mkdtemp(prefix="sa-inspect-"))
        try:
            make_project(tmp, ["play-phone"])
            r = run("inspect_capture.py", "store-assets/raw/phone/home.png", cwd=tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("1080x2400", r.stdout)
            self.assertTrue((tmp / "store-assets" / "out" / "_review" / "bars.png").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

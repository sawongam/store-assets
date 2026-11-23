"""The skill and every harness manifest stay valid and in sync.

Rules from the Agent Skills spec (agentskills.io/specification), plus a version check across the
Claude Code, Codex, Cursor and Gemini CLI manifests so a release never ships with mismatched numbers.
"""

from __future__ import annotations

import json
import re
import unittest

from _fixtures import ROOT, SKILL

MANIFESTS = [".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
             "gemini-extension.json"]


def frontmatter(text: str) -> dict:
    """Minimal YAML subset the spec uses: top-level `key: value` and one nested `metadata:` map."""
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with a --- frontmatter block"
    out: dict = {}
    parent = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        key, _, val = line.strip().partition(":")
        val = val.strip()
        if line.startswith((" ", "\t")):
            out[parent][key] = val
        elif val == "":
            parent = key
            out[key] = {}
        else:
            out[key] = val
    return out


def unquote(v: str) -> str:
    return v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v


class SkillSpec(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.fm = frontmatter(self.text)

    def test_name(self):
        name = self.fm["name"]
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, SKILL.name, "name must match the skill's folder")

    def test_lengths(self):
        self.assertTrue(1 <= len(self.fm["description"]) <= 1024)
        self.assertTrue(1 <= len(self.fm.get("compatibility", "x")) <= 500)

    def test_only_spec_fields(self):
        allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
        self.assertEqual(set(self.fm) - allowed, set())

    def test_metadata_is_string_map(self):
        for k, v in self.fm.get("metadata", {}).items():
            self.assertTrue(v.startswith(('"', "'")) or not re.fullmatch(r"[\d.]+|true|false", v),
                            f"metadata.{k} must be a string; quote it")

    def test_body_size(self):
        self.assertLess(len(self.text.splitlines()), 500, "spec: keep SKILL.md under 500 lines")

    def test_referenced_files_exist(self):
        refs = set(re.findall(r"`((?:references|scripts|assets)/[\w./-]+)`", self.text))
        self.assertTrue(refs)
        for r in refs:
            self.assertTrue((SKILL / r).exists(), f"SKILL.md points at missing {r}")
        for r in set(re.findall(r"`references/([\w-]+\.md)`", self.text)):
            self.assertTrue((SKILL / "references" / r).is_file())

    def test_every_reference_is_linked(self):
        for p in (SKILL / "references").glob("*.md"):
            self.assertIn(f"references/{p.name}", self.text, f"{p.name} is never mentioned in SKILL.md")


class Manifests(unittest.TestCase):
    def setUp(self):
        self.fm = frontmatter((SKILL / "SKILL.md").read_text(encoding="utf-8"))
        self.data = {m: json.loads((ROOT / m).read_text(encoding="utf-8")) for m in MANIFESTS}

    def test_versions_match(self):
        want = unquote(self.fm["metadata"]["version"])
        for m, d in self.data.items():
            self.assertEqual(d["version"], want, m)
        top = re.search(r"^## (\d+\.\d+\.\d+)", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual(top.group(1), want, "CHANGELOG's latest release")

    def test_names_match(self):
        for m, d in self.data.items():
            self.assertEqual(d["name"], self.fm["name"], m)
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertIn(self.fm["name"], [p["name"] for p in market["plugins"]])

    def test_paths_exist(self):
        codex = self.data[".codex-plugin/plugin.json"]
        for p in (codex["skills"], codex["interface"]["logo"], codex["interface"]["composerIcon"],
                  self.data[".cursor-plugin/plugin.json"]["logo"]):
            self.assertTrue((ROOT / p).exists(), p)

    def test_codex_listing_limits(self):
        ui = self.data[".codex-plugin/plugin.json"]["interface"]
        self.assertLessEqual(len(ui["displayName"]), 30)
        self.assertLessEqual(len(ui["shortDescription"]), 30)
        self.assertLessEqual(len(ui["defaultPrompt"]), 3)

    def test_no_gemini_context_file(self):
        """A GEMINI.md would be loaded into every Gemini session of everyone who installs the extension."""
        self.assertFalse((ROOT / "GEMINI.md").exists())


if __name__ == "__main__":
    unittest.main()

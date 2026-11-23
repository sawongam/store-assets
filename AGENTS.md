# Working on store-assets

This repo ships one Agent Skill, `skills/store-assets/`, packaged for several harnesses. These notes are for agents and people changing the skill, not for using it: the instructions the skill runs on live in `skills/store-assets/SKILL.md`.

## Layout

| Path | What it is |
|---|---|
| `skills/store-assets/SKILL.md` | The skill. Keep it under 500 lines; detail goes in `references/` |
| `skills/store-assets/scripts/` | Python 3.9+ and Pillow 10.1+ only. `sa/` is the shared renderer |
| `skills/store-assets/scripts/specs.json` | Store sizes and copy rules, dated. The one place to update when a store changes |
| `.claude-plugin/` | Claude Code plugin and marketplace (also read by `npx skills` and Codex) |
| `.codex-plugin/plugin.json` | Codex plugin manifest |
| `.cursor-plugin/plugin.json` | Cursor plugin manifest |
| `gemini-extension.json` | Gemini CLI extension manifest |
| `tests/` | stdlib `unittest`, synthetic captures, no emulator needed |

Every harness discovers the skill from `skills/`, so nothing is duplicated. Don't add a `GEMINI.md`: Gemini CLI would load it into every session of everyone who installs the extension.

## Checks

```bash
python3 -m pip install pillow
python3 -m unittest discover -s tests -v   # ~25 s
```

CI runs the same on Linux, macOS and Windows, plus Python 3.9 with Pillow 10.1.0 as the floor.

## Rules

- **Rendering stays deterministic.** No unseeded randomness, no wall-clock values in images. `test_partial_render_is_identical` guards this.
- **Never draw or generate app UI.** The renderer frames real captures only.
- **A release bumps every version together:** `SKILL.md` (`metadata.version`), the three `plugin.json` files, `gemini-extension.json` and a new `CHANGELOG.md` heading. `tests/test_packaging.py` fails when they disagree. Merging that to `main` publishes the GitHub Release by itself (the `release` job in `ci.yml`), using the matching `CHANGELOG.md` section as the notes. If the version already has a release, the job does nothing, so a change without a bump never re-releases.
- **Spec changes cite a source.** Update `specs.json` → `last_verified` and the matching `references/*.md` together, with the store page URL in the PR.
- **Keep SKILL.md harness-neutral.** Refer to "your file viewer" or "the shell", not one harness's tool names, and keep paths relative to the skill folder.

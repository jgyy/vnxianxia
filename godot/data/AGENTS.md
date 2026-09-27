# AGENTS.md: godot/data/

The two JSON files the runtime reads at startup are both **generated** and checked in CI. Never edit them by hand:
change the Python source and rerun its tool. A hand edit is either overwritten or fails `--check`.

| File | Source | Command | CI check |
|---|---|---|---|
| `world.json` (about 12 KB) | `tools/world_spec.py` `as_dict()` | `python tools/world_spec.py` | `python tools/world_spec.py --check` |
| `story.json` (about 7.6 MB) | `tools/story/` package | `python tools/build_story.py` | `python tools/build_story.py --check` |

## Contents

- **world.json** holds `maps` (18: 5 exterior + 13 interiors, each with `name`, `music` and the sorted `markers`),
  `models`, `humanoid_anims`, `creature_anims`, `enemies` (enemy -> model), `bosses`, `items`, `props` (prop -> GLB
  or null), `item_model_dir`, `realms`, `stages`, `stage_groups`, `alignments`, `align_range` and `align_threshold`.
  It is written with `sort_keys`, indent 1 and a trailing newline.
- **story.json** has `version` 2, `title`, `premise`, `volumes`, `chapters`, `npcs` (66, with model, tint, home and
  timeline), `quests` (2000, `q0001..q2000`), `cinematics` (20) and `threads`. Objectives carry `type`, `map`,
  `npc` / `at` / `marker`, `text`, `with` (the NPCs present for a group conversation), `dialogue` (lines with
  `speaker`, `text`, `voice` = `res://audio/voice/<key>.ogg` or null, and an optional `cond`), and `choices`. The
  field-by-field reference is docs/STORY.md, "How it is stored".

## Who reads them

`godot/scripts/autoload/story.gd` (`Story`) loads both (`PATH`, `WORLD_PATH`). It exposes `Story.world`, resolves the
`{player}` tokens and picks the `_m` / `_f` voice takes. The tests use `Story.world` to enumerate maps, markers,
models and props. `tools/gen_voices.py` reads story.json to know which voice files must exist.

## Rules

- Order of regeneration: `world_spec.py` first (ids), then `build_story.py`, which validates every map, marker,
  model, enemy, item and prop id against `world_spec`. Then `gen_voices.py --check` if voiced text changed.
- Both files must be byte-identical to a fresh build. Commit them in the same change as their sources.
- story.json is large. Read it with `python -c "import json; ..."` or `jq` instead of opening the whole file.

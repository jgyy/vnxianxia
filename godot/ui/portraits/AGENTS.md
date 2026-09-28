# AGENTS.md: godot/ui/portraits/

This directory holds the dialogue portraits: one 256x256 RGBA PNG per humanoid **model** (not per NPC), each with a
committed `.png.import`. They are **generated** by `blender/render_portraits.py`, which builds each
`characters.HUMANOIDS` config and renders a Cycles head-and-shoulders shot with key, fill and warm rim lights.

The files are `cultivator_male`, `cultivator_female`, `elder_male`, `sect_master`, `disciple_male`, `disciple_female`,
`villager_male`, `villager_female`, `bandit`, `demon_cultivator` and `blood_patriarch` (`.png`). The creature models
(`stone_golem`, `spirit_wolf`, `jiao_serpent`) have no portrait.

```bash
. /home/user/.venv/bin/activate
python blender/render_portraits.py --only elder_male,bandit     # --samples 48, --size 256, --out godot/ui/portraits
~/godot/godot --headless --path godot --import                  # then commit .png + .png.import
```

## How it is used

`godot/scripts/ui/dialogue_ui.gd` (`PORTRAIT_DIR = "res://ui/portraits/"`) shows the speaker's model portrait inside
the `portrait_frame` from the HUD kit. Many NPCs share a model and are told apart by the tint applied in game, not by
the portrait. The smoke test requires a portrait for every model used by a story NPC, plus both heroes.

## Rules

- Never edit the PNGs. Change the character in `blender/xianxia/characters.py` (or the lighting and framing in
  `render_portraits.py`) and re-render. After a character's face, hair or outfit changes, re-render its portrait too,
  so the portrait matches the in-game model.
- A new humanoid model that any NPC uses needs a portrait here, named exactly like the model id in
  `tools/world_spec.py` `MODELS`.
- Hair cards need 64 transparent bounces in Cycles (`preview.setup`), or the hair renders as black clumps
  (docs/bugfixes/hair_skin.md #11).
- Rendering is a heavy Cycles job. Use `--only` and run one Blender process at a time.

# AGENTS.md: blender/

These are the entry-point scripts for headless Blender 5.2.2. Each one builds or renders something from the
procedural library in [xianxia/](xianxia/AGENTS.md) and writes the result into the Godot project or `docs/`. The
scripts are hand-written. Their outputs are generated, so never edit those by hand.

Run them with the `bpy` module (`python blender/<script>.py [args]`) or with a Blender binary:
`blender --background --factory-startup --python blender/<script>.py -- [args]`. Every script accepts its arguments
after `--`. Every script inserts this directory into `sys.path` and imports `xianxia`.

| Script | Writes | Notes |
|---|---|---|
| `build_assets.py` | `godot/assets/characters/*.glb` (`characters.HUMANOIDS` + `creatures.CREATURES`), `environment/*.glb` (`catalog.ENVIRONMENT`), `items/*.glb` (`catalog.ITEMS`) | `--only a,b`, `--out DIR`, `--skip-characters`, `--skip-environment`. The heroes are then keyframe-reduced by `moves.optimize_glb`. |
| `render_portraits.py` | `godot/ui/portraits/<model>.png` (256 px Cycles head-and-shoulders) | `--only`, `--samples 48`, `--size 256` |
| `render_hud.py` | `godot/ui/hud/*.png` + `hud_kit.json` (2x logical size, transparent) | `--only panel,gauges` (builder groups, see `BUILDERS`). With `--only`, it merges into the existing `hud_kit.json`. It reads fonts from `godot/ui/fonts/`. |
| `render_previews.py` | `docs/screenshots/` hero turnaround | documentation only |
| `render_animation_sheet.py` | `docs/screenshots/animations_sheet.jpg`, gait strips | `--blend/--save-blend` caches a built scene. `--strips walk,run --travel` checks foot planting. |
| `render_props_sheet.py` | `docs/screenshots/quest_props.jpg`, `items.jpg` | `--kind props/items/dressing/quest`, or `--dir --names`. It prints visual and collider bounds (visual QA). |

## Building selectively

- `--only` matches the names of humanoid configs, creatures, `catalog.ENVIRONMENT` keys and items. Items also answer
  to `item_<id>`. A bare `spirit_herb`, `spirit_stone` or `jade_slip` only rebuilds the *environment* asset, because
  the same name exists in both catalogs (docs/bugfixes/props.md #4).
- A full build takes a long time (the CI budget is 120 min). The heroes take the longest, because of 136 actions.
  Build only what you changed, and run one Blender process at a time on this shared 4-core machine.
- The environment terrains (`terrain`, `forest_terrain`, `town_terrain`) import `tools/maps/*` for their height fields,
  and `abyss_terrain` shares its carve layout with `tools/maps/blood_abyss.py`. After you change a map's ground,
  rebuild its terrain GLB.

## Validate after building

```bash
. /home/user/.venv/bin/activate            # bpy 5.2.2 on Python 3.13
python blender/build_assets.py --only pine_tree,bandit
python tools/validate_glb.py godot/assets  # containers, materials, rigs, animations, props/items budgets
python tools/zfight_glb.py --names pine_tree godot/assets   # coplanar overlapping triangles (want 0)
python -m py_compile blender/*.py blender/xianxia/*.py
godot --headless --path godot --import && godot --headless --path godot -s res://tests/smoke_test.gd
```

For animation changes, also run `godot --headless --path godot -s res://tests/animations_test.gd`.

## Pitfalls

- When you regenerate a GLB, keep its committed `.glb.import`, because it holds the UID and `generate_lods`. LODs are
  off for all environment GLBs except vegetation and rubble (docs/bugfixes/runtime.md #61).
- `render_animation_sheet.py --blend` uses the cached scene as-is. Rebuilding actions on top of it made `*.001`
  duplicates (docs/bugfixes/animation.md #17).
- Cycles previews need 64 transparent bounces for the hair cards (`preview.setup`), or the hair renders as black
  clumps (docs/bugfixes/hair_skin.md #11).

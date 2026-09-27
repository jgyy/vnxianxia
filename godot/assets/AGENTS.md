# AGENTS.md: godot/assets/

These are the 3D models, all **generated** as GLB by `blender/build_assets.py` (library in `blender/xianxia/`).
Never edit, re-export or hand-replace a `.glb`. Change the builder and rebuild:

```bash
. /home/user/.venv/bin/activate
python blender/build_assets.py --only <name>[,<name>]        # writes into godot/assets/<kind>/
python tools/validate_glb.py godot/assets                    # CI check (stdlib)
~/godot/godot --headless --path godot --import               # then commit the .glb and its .glb.import
```

| Subdirectory | Contents | Built from | Guide |
|---|---|---|---|
| `characters/` | 14 rigged, animated models (11 humanoids + golem, wolf, Jiao) | `characters.HUMANOIDS`, `creatures.CREATURES` | [characters/AGENTS.md](characters/AGENTS.md) |
| `environment/` | about 270 buildings, terrains, vegetation, props, interiors, quest props | `catalog.ENVIRONMENT` | [environment/AGENTS.md](environment/AGENTS.md) |
| `items/` | 18 collectible pickups, one per `world_spec.ITEMS` id | `catalog.ITEMS` (`items.py`) | [items/AGENTS.md](items/AGENTS.md) |

## Conventions

- File name = asset id = the builder key. Scripts load `res://assets/<kind>/<id>.glb` by that id: the model ids in
  `world.json` `models`, the prop GLB names in `props`, and the item ids under `item_model_dir`. Map scenes reference
  environment GLBs by path.
- glTF is Y-up. Model fronts face **+Z** (Blender -Y), and units are metres. Collision is imported from node-name
  suffixes (`-colonly`, `-convcolonly`, `-col`).
- Textures are embedded as JPEG (quality 88). The PNG/JPG files Godot extracts next to the GLBs on import are
  gitignored.
- Budgets: 12 MB per GLB (the terrains and heroes are the largest, 4-9 MB), 1.5 MB per quest prop, 512 KB per item.
- Only the files ending in `.glb` / `.glb.import` matter here. The smoke test's `DirAccess` scan and
  `validate_glb.py`'s `rglob("*.glb")` skip everything else, so these AGENTS.md files are harmless.

## Validate

`python tools/validate_glb.py godot/assets` (containers, materials, rigs + animations, prop / item rules, models
missing from `world_spec`), `python tools/zfight_glb.py --names <id> godot/assets` (z-fighting, want 0 pairs), then
`~/godot/godot --headless --path godot -s res://tests/smoke_test.gd`, which loads every character and environment GLB
and checks rigs, animations and props.

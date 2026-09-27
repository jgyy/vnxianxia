# AGENTS.md: godot/scenes/maps/

This directory holds 18 **generated** map scenes: 5 exterior maps (`sect`, `bamboo_forest`, `qingshi_town`,
`blood_abyss`, `sky_isles`) and 13 interiors (`sect_main_hall`, `elder_quarters`, `scripture_pavilion`,
`alchemy_pavilion`, `weapons_hall`, `disciple_dormitory`, `qingshi_inn`, `qingshi_teahouse`, `qingshi_blacksmith`,
`qingshi_herb_shop`, `hidden_vault`, `celestial_pavilion`, `blood_abyss_shrine`). `tools/maps/common.py` writes them
from the layout modules in `tools/maps/`.

**Never edit a `.tscn` here, in a text editor or in the Godot editor.** CI regenerates them and fails on any diff:

```bash
python tools/build_maps.py                       # all maps; or: python tools/build_maps.py sect qingshi_inn
git diff --exit-code -- godot/scenes/maps        # what CI runs; must be clean after committing
```

## Structure (the runtime depends on it)

```
Map (Node3D, script res://scripts/map.gd: map_id, display_name, music, ambient, kill_y)
  WorldEnvironment   (sky, fog, tonemap, SSAO, glow from maps.common.Env)
  Sun                (DirectionalLight3D; shadow bias / normal bias / blended splits)
  Level              (Node3D) one instance per placed environment GLB, res://assets/environment/<asset>.glb
  Markers            (Node3D) one Marker3D per marker named in tools/world_spec.py MAPS[map_id]["markers"]
```

- `game.gd` loads `res://scenes/maps/<map_id>.tscn` on a thread. `map.gd` resolves markers (`marker_position`,
  `ground_at`, `marker_grounded`, `open_spot`) with downward ray casts, so markers only need an approximate height.
- **Level child names are unique.** Godot keeps only one of two same-named siblings and orphans the other; a
  cloud-harbour pier went missing that way. The writer exits on duplicates (docs/bugfixes/world.md #65).
- The marker set must equal `world_spec.MAPS[map_id]["markers"]` exactly. Quests, cinematics and door links refer to
  markers by name only.
- Coordinates are Godot's (-Z north), and instance yaw 0 means the asset's front faces south (+Z).
- The exterior maps are large (the bamboo forest has about 1400 instances), so the writer emits one
  `ext_resource` per unique GLB.

## Validate

```bash
python tools/build_maps.py && git diff --exit-code -- godot/scenes/maps
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd           # every marker present and on the ground
~/godot/godot --headless --path godot -s res://tests/capture_world_check.gd  # stricter: capsule fits, level ring, fight spot
xvfb-run -a ~/godot/godot --path godot --rendering-driver vulkan -s res://tests/capture_map.gd -- sect /tmp/shots
```

When a map changes shape, rebuild its terrain GLB too (`python blender/build_assets.py --only forest_terrain`).
Then play the affected quests with `walkthrough_test.gd -- <first> <last>`.

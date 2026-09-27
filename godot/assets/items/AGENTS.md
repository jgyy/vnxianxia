# AGENTS.md: godot/assets/items/

This directory holds 18 **generated** collectible-item models, one `<item_id>.glb` (+ committed `.glb.import`) per id
in `tools/world_spec.py` `ITEMS`. They are built by `blender/xianxia/items.py` (`ITEMS`, exposed as `catalog.ITEMS`).
Never edit them; rebuild with:

```bash
python blender/build_assets.py --only item_spirit_stone,wolf_fang   # item_<id> always selects the item
python tools/validate_glb.py godot/assets
```

Plain ids also work (`--only wolf_fang`), except `spirit_herb`, `spirit_stone` and `jade_slip`. Those names also exist
as environment assets, and a bare name builds the environment one (docs/bugfixes/props.md #4).

## How the runtime uses them

`godot/scripts/world/pickup.gd` (`model_path()`) loads `world.json` `item_model_dir` + `/<item>.glb`
(`res://assets/items/`). It enlarges small models toward `DISPLAY_SIZE` 0.32 m (at most `MAX_ENLARGE` 2x, never
shrinking them), centres them on a turning, bobbing pivot about 0.5 m up and lights them with a glow in the item's
`COLORS` entry. If the GLB is missing, it falls back to a glowing primitive. The pickup has its own trigger area.

## Rules (enforced by `tools/validate_glb.py` `_check_item`)

- **No collision nodes.** A pickup must never block the player (props.md #3).
- The item is at most **0.6 m** on any axis (hand-held scale is 0.15-0.4 m) and at most **512 KB**.
- The origin is at the **bottom centre**: the lowest point is within -0.03..0.05 m of y 0, and the centre is within
  0.1 m horizontally.
- Every id in `world_spec.ITEMS` must have a GLB here, or validation fails with "missing".
- Style (`items.py`): 256 px textures, an emissive accent so the item reads at a distance, and the readable face
  toward +Z (Blender -Y). Do not share faces between parts: z-fighting was found on items too (props.md #24). Check
  with `python tools/zfight_glb.py --names <id> godot/assets`.

To add an item: add it to `world_spec.ITEMS`, run `python tools/world_spec.py`, add a builder to `items.ITEMS`, build
it, validate it, run `--import` in Godot and commit the `.glb` + `.glb.import`. Add a glow colour to `pickup.gd`
`COLORS`, or the item uses the default cyan.

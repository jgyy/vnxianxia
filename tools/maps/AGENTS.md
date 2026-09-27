# AGENTS.md: tools/maps/

These are the map layouts, in hand-written, stdlib-only Python. Each exterior map module exposes `build() -> MapDef`
(a list of placed GLBs, the markers and the environment). `../build_maps.py` passes it to `common.write`, which
renders `godot/scenes/maps/<map_id>.tscn`. That output is **generated**: never edit a `.tscn` in
`godot/scenes/maps/`; change the module here and rerun the builder.

| Module | Role |
|---|---|
| `common.py` | `MapDef`, `Env`, `Sky` dataclasses; `render()` writes the scene (`Map` with map.gd -> `WorldEnvironment`, `Sun`, `Level` of GLB instances, `Markers` of Marker3D); `check_markers()` compares against `world_spec.MAPS`; `write()` |
| `terrain.py` | `Ground`: base height + *pads* (terraces, plots, roads, lakes) + surface *regions* + *waters*; shapes `Rect`, `Disc`, `Path`, `Poly`, `Union`, `Ring`; seeded `noise2` / `fbm2` |
| `layout.py` | `FOOT` (every building's footprint), `Sites` (levels a pad under each building), `check_markers()` (no marker inside or right next to a building; level ground 5 m around and 9 m south of it) |
| `sect.py`, `bamboo_forest.py`, `qingshi_town.py` | the enlarged (about 10x) exterior maps on one `terrain.Ground` each; the original first-map layout sits untouched in the middle |
| `blood_abyss.py` | ground carved from rock by capsule `CARVES`; `ground_height` is shared with `blender/xianxia/realms.py` |
| `sky_isles.py` | floating isles chained by jade bridges and stairs; the overlap and bridge-end rules are in the module docstring |
| `interiors.py` | `BUILDERS` for the 13 interiors (one GLB of the same name + `PlayerSpawn` / `ExitDoor` / `TeleportArray` + a feature marker) |
| `zfight_visible.py` | **not a map**: sorts `tools/zfight_glb.py` pairs into hidden / same-texel / visible (`python tools/maps/zfight_visible.py godot/assets/environment/<asset>.glb`) |

## Conventions

- Coordinates are **Godot's**: x east, y up, z south (-Z is north). Environment GLBs face +Z, so yaw 0 means the front
  faces south. A Blender point (x, y, z) lands at Godot (x, z, -y) (see `interiors.py`).
- Marker names come from `tools/world_spec.py` `MAPS[map]["markers"]`. Add the name there first. `common.write` exits
  if the markers differ in either direction. Quests only ever refer to markers.
- Every placed node name in `Level` must be unique. `render()` refuses duplicates, because Godot silently orphans
  one of two same-named siblings (docs/bugfixes/world.md #65). Name nodes explicitly (`CloudPier1`, `CloudPier2`), or
  pass `None` for an automatic `PascalAsset<n>`.
- Determinism: randomness comes from `random.Random(seed)` with fixed seeds and the hashed terrain noise. Never use
  unseeded `random`, `set` iteration order or the time. CI diffs the regenerated scenes.
- The ground lives here: `lands.py` / `realms.py` in Blender import these modules to mesh `terrain.glb` (sect),
  `forest_terrain.glb`, `town_terrain.glb` and `abyss_terrain.glb`. **After changing heights, pads or regions, rebuild
  that GLB** (`python blender/build_assets.py --only forest_terrain`), or markers and props will float or sink.
- A new building asset needs a `layout.FOOT` entry so its site is levelled and markers keep clear of it.
- Door links (exterior marker <-> interior) live in `godot/scripts/world/doors.gd`. Keep map ids and marker names in
  step with `interiors.py`.

## Validate

```bash
python tools/build_maps.py                 # or: python tools/build_maps.py sect qingshi_inn
git diff --stat -- godot/scenes/maps       # review; CI requires the committed scenes to match
python tools/world_spec.py --check && python tools/build_story.py --check
godot --headless --path godot -s res://tests/smoke_test.gd           # markers on walkable ground
godot --headless --path godot -s res://tests/capture_world_check.gd  # marker ground/ring check vs real collision
```

A layout-time failure such as `<map> marker problems:` comes from `layout.check_markers`. Move the marker, or add it
to that map's `exempt` tuple only when it really stands on a bridge or jetty. Walkthrough failures such as
unreachable enemies usually mean a marker is too close to an edge (world.md #46).

# AGENTS.md: godot/assets/environment/

This directory holds about 270 **generated** static environment GLBs, each with a committed `.glb.import`. There is
one file per key of `blender/xianxia/catalog.py` `ENVIRONMENT`, named `<key>.glb`. Never edit them; rebuild with
`python blender/build_assets.py --only <key>[,<key>]`, then re-import in Godot and commit both files.

## Where each family comes from (the builder module's `ASSETS`)

| Family | Examples | Module |
|---|---|---|
| Terrains | `terrain` (the sect mountain), `forest_terrain`, `town_terrain`, `abyss_terrain` | `lands.py`, `realms.py`; the height fields come from `tools/maps/*` |
| Original sect kit | `main_hall`, `sect_gate`, `pavilion`, `pagoda`, `courtyard_wall`, `moon_gate_wall`, lanterns, trees, `cloud_sea` | `arch.py`, `props.py`, `nature.py` (listed in `catalog.py`) |
| Enlarged sect | `outer_sect_hall`, `mission_hall`, `treasure_tower`, `stone_stairs_14`, `martial_stage`, `sword_tomb` ... | `buildings.py` |
| Town | `shophouse_a/b/c`, `city_gate`, `city_wall`, `granary`, `opera_stage`, `watermill`, `town_house*` ... | `buildings_town.py`, `lands.py` |
| Forest | `stilt_house*`, `lake_pavilion`, `buddha_cliff`, `banyan_giant`, `rope_bridge_long`, `bamboo_grove` ... | `buildings_wild.py`, `lands.py` |
| Abyss | `demon_palace`, `skull_tower`, `obsidian_spire*`, `blood_altar`, `demon_gate`, `fortress_wall` ... | `buildings_abyss.py`, `realms.py` |
| Sky Isles | `sky_platform_*`, `jade_bridge*`, `ascension_stair`, `sky_steps`, `jade_palace_hall`, `tree_of_ages` ... | `buildings_sky.py`, `realms.py` |
| Interiors (13) | `sect_main_hall`, `qingshi_inn`, `hidden_vault`, `blood_abyss_shrine` ... (same ids as their interior maps) | `interiors.py` |
| Quest props (30) | `notice_board`, `pill_furnace`, `armillary_sphere`, `fishing_boat` ... (= `world_spec.PROPS` values) | `quest_props.py` (`QUEST`) |
| Dressing | `goods_baskets`, `cloth_bolts`, `tea_set`, `hand_cart` ... | `quest_props.py` (`DRESSING`) |
| Legacy props | `teleport_array`, `stone_stele`, `treasure_chest`, `spirit_herb`, `spirit_stone`, `jade_slip`, `bronze_bell` | `lands.py` |

`spirit_herb`, `spirit_stone` and `jade_slip` exist here (ground-scale dressing with colliders) **and** in `../items/`
(hand-held pickups). `--only spirit_stone` rebuilds only this one.

## Conventions

- Y-up, metres, **front faces +Z (south)**, origin at the footprint's ground centre. Map layouts place them by yaw
  (0 = front south) and rely on `tools/maps/layout.py` `FOOT` for footprints.
- Collision nodes carry `-colonly` / `-convcolonly` / `-col` suffixes. Stairs and podiums use smooth ramp colliders
  (risers <= 0.17 m), and walkable shapes need gentle collider slopes (docs/bugfixes/world.md #6-13).
- Quest props (validated): collision if taller than 0.5 m, lowest point at the origin, at most 1.5 MB. Everything
  else: at most 12 MB (the terrains are the largest, about 4-9 MB).
- `.glb.import`: `meshes/generate_lods=false` except for the 24 vegetation / rubble assets (trees, bamboo, rocks,
  ferns, `crates`, `bone_pile` ...). Keep that when you regenerate. A new vegetation GLB that should get LODs needs
  `generate_lods=true` set in its `.import`.

## Validate

```bash
python tools/validate_glb.py godot/assets
python tools/zfight_glb.py --names <key> godot/assets          # want 0 overlapping coplanar pairs
python tools/maps/zfight_visible.py godot/assets/environment/<key>.glb   # which pairs are actually visible
python blender/render_props_sheet.py --dir godot/assets/environment --names <key> --out /tmp/x.jpg
python tools/build_maps.py && git diff --exit-code -- godot/scenes/maps   # footprint / placement still valid
```

Z-fighting is the most common defect here, followed by colliders the player cannot climb. Read
docs/bugfixes/world.md and props.md before editing a builder.

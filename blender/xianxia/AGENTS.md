# AGENTS.md: blender/xianxia/

This is the procedural asset library (hand-written Python for `bpy` 5.2.2 + numpy). The scripts in
[../](../AGENTS.md) (`build_assets.py`, `render_*.py`) import it. Nothing in the game reads it directly. Its product
is the GLBs in `godot/assets/` and the rendered PNGs, so a change here only reaches the game after the affected
assets are rebuilt and committed.

## Modules

| Group | Modules | Role |
|---|---|---|
| Shared | `util.py`, `tex.py`, `preview.py`, `catalog.py` | mesh / material / collider / `export_glb` helpers; numpy PBR textures (row 0 = bottom); Cycles preview setup; `catalog.ENVIRONMENT` + `catalog.ITEMS` (GLB name -> builder) |
| Characters | `characters.py`, `anatomy.py`, `creatures.py` | `HUMANOIDS` (2 heroes in `PLAYERS` + NPC `VARIANTS`), 58-bone rig (54 + `sleeve.L/R` + `eye.L/R`), weights, outfits, the 10 base actions; ears/hands; golem, wolf, Jiao serpent (`CREATURES`) |
| Face | `face_landmarks.py`, `face_surface.py`, `face_chart.py`, `face_uv.py`, `face_mesh.py`, `face_eyes.py`, `face_cards.py`, `face_mouth.py`, `face_materials.py`, `face_head.py`, `face_shapes.py`, `face_anim.py`, `face_rig.py`, `face_check.py` | the "Head" mesh: per-character anthropometric params and ~150 landmarks -> implicit head surface -> ray-cast quad grid with eye / mouth / nostril O-grids; eyeballs (sclera, iris, cornea), lids, caruncle, tear lines, lash + brow cards, teeth/tongue, ears, neck; UV islands; 22 shape keys baked per action as glTF morph tracks; `eye.L/R` bones; `face_check` self-checks (lid seal, blink, teeth, symmetry, winding, folds, eyeball orientation) print `WARNING face check` lines on every build |
| Animation | `gait.py`, `moves.py` | IK locomotion with the speed contract and `verify_clip` (build fails above `MAX_SLIP` 2 cm); 126 hero clips as key poses (`Clip`, `Rig`), `optimize_glb` keyframe reduction |
| Hair / skin | `hair_groom.py`, `hair_styles.py`, `hair_cards.py`, `hair_tex.py`, `hair_props.py`, `skin.py`, `skin_maps.py`, `skin_eyes.py`, `skin_shading.py` | strand solver -> alpha-tested cards + atlas; painted face / body skin; eyes, mouth, lashes; node trees that both Cycles and the glTF exporter understand |
| Environment | `arch.py`, `buildings.py` (+ `_town`, `_wild`, `_abyss`, `_sky`), `lands.py`, `realms.py`, `nature.py`, `props.py`, `interiors.py` | the building kit (podium, hall, roofs, stairs), per-map buildings and landmarks, terrains, vegetation, the 13 interiors |
| Quest objects | `quest_props.py`, `items.py` | the 30 interactable quest props (+ market / shrine dressing) and the 18 collectible items |
| HUD | `hud_art.py` | primitives for `render_hud.py` (logical px, y down, ortho camera) |

Each environment module exposes `ASSETS = {glb_name: builder}`, which `catalog.py` merges. A new asset needs an
entry there. If it is a quest prop or an item, its id goes into `tools/world_spec.py` `PROPS` / `ITEMS` first, because
`validate_glb.py` fails when a GLB named there is missing.

## Conventions

- **Blender Z-up, metres, fronts face -Y (= Godot +Z).** The origin is the ground centre of the footprint. Items put
  it at the bottom centre, at hand-held scale (0.15-0.4 m), with 256 px textures and **no** colliders.
- Collision comes from invisible meshes named with Godot suffixes: `util.collider(..., convex=True)` produces
  `-convcolonly`, `convex=False` produces `-colonly`, and walkable terrain uses `-col`. Stairs get a smooth ramp
  collider through the tread nosings with risers <= 0.17 m (`buildings.podium`, `stair_ramp`). Quest props taller
  than 0.5 m must have collision.
- Budgets (checked by `tools/validate_glb.py`): 12 MB per GLB, 1.5 MB per quest prop, 512 KB and 0.6 m per item.
  Terrains are chunked and only refined where visible (docs/bugfixes/world.md #3).
- Determinism: textures use seeded `np.random.default_rng(seed)`. Keep seeds fixed so rebuilt GLBs don't churn.
- Call `util.reset_scene()` before each asset. It also clears the texture and material caches.
- Materials must stay on the Principled BSDF / "glTF Material Output" patterns in `skin_shading.py`, or the exporter
  drops them. Alpha is exported as MASK, not BLEND.
- Animation: never change the authored speeds in `gait.py` without also changing `AUTHORED_SPEED` in
  `godot/scripts/player.gd`. Loops must be seamless: whole cycles per loop, baked on every frame.

## Pitfalls seen in the bug logs

- **Z-fighting** is the most common defect. Never leave two faces coplanar: offset joined members by 3-12 mm, lift
  overlays 2-4 cm, and sink trunks and stilts into what they rest on. Closed loops need `quest_props.hoop()` /
  `loop_tube()`, not `util.tube`. Check with `python tools/zfight_glb.py --names <asset> godot/assets` and classify
  with `tools/maps/zfight_visible.py` (docs/bugfixes/world.md, props.md #12-24).
- `tex.fbm` produced NaNs when `cells > size/2` at small sizes. Use >= 256 px for stone (hair_skin.md #1, props.md #11).
- Convex hulls: remove duplicate vertices before `convex_hull` (`lands.convex_mesh`, `quest_props.hull`).
- Gable roofs and copings must be one continuous sheet over the ridge (world.md #47-49).
- Hero clips: `run_start` / `run_stop` are keyed from the run cycle's real first pose (animation.md #15).

Rebuild and validation commands are in [../AGENTS.md](../AGENTS.md).

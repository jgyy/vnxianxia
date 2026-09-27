# AGENTS.md: godot/assets/characters/

These are **generated** rigged, animated character GLBs (`<model>.glb` + committed `.glb.import`). Never edit them;
rebuild with `python blender/build_assets.py --only <model>` (use the Blender venv).

| Files | Builder | Rig / animations |
|---|---|---|
| `cultivator_male`, `cultivator_female` | `characters.PLAYERS` + `moves.build_player_actions`, then `moves.optimize_glb` | 58-bone humanoid rig (54 + `sleeve.L/R` + `eye.L/R`); the 10 base actions + 126 extended moves (136); about 10.5-11.3 MB each (the head's morph targets are ~3 MB) |
| `elder_male`, `sect_master`, `disciple_male`, `disciple_female`, `villager_male`, `villager_female`, `bandit`, `demon_cultivator`, `blood_patriarch` | `characters.VARIANTS` | humanoid rig, `idle walk run salute cast attack hit death meditate talk` |
| `stone_golem` | `creatures.build_golem` | humanoid rig of rock chunks; checked against the humanoid list |
| `spirit_wolf`, `jiao_serpent` | `creatures.build_wolf` / `build_serpent` | quadruped / spine-chain rig; `idle walk run attack hit death` |

The model ids come from `tools/world_spec.py` `MODELS`. The required animations are `HUMANOID_ANIMS` /
`CREATURE_ANIMS`, and each protagonist needs at least `PROTAGONIST_MIN_ANIMS` (100). The 40 story NPCs reuse these
models with a tint and scale (`godot/scripts/world/actor_look.gd`, `npc.gd`). Each humanoid also has a portrait in
`godot/ui/portraits/<model>.png`.

## Contracts

- `walk` / `run` / `sprint` plant their feet at exactly **1.6 / 4.6 / 6.2 m/s** (sneak 1.0, crouch_walk 0.8,
  walk_back and strafes 1.0) at speed_scale 1. `player.gd` and `enemy.gd` divide the ground speed by these numbers
  (times the model scale). `gait.verify_clip` fails the build if a stance foot slips more than 2 cm.
- The front faces +Z. Each model has exactly one `Skeleton3D` and one `AnimationPlayer` (the smoke test checks this),
  and every required clip is longer than 0.3 s.
- Materials: skin gets SSS, and the hair cards use alpha scissor with anisotropy. Both are applied at runtime by
  `actor_look.gd` on the imported GLB, so the names of material slots matter to it.
- The committed `.glb.import` files keep `generate_lods=true` for characters.
- Faces: the `Head` mesh carries 22 blend shapes (`blink_L/R`, `squint_L/R`, `lid_look_up/down`, `eyes_wide`,
  `brow_up/down/inner_up`, `smile`, `frown`, `sneer_L/R`, `cheek_puff`, `mouth_stretch`, `jaw_open`, `viseme_AA/EE/OO/MM/FF`).
  Every clip carries all 22 as blend_shape tracks (blinks, saccades, visemes, expressions), and the eyes are the
  `eye.L` / `eye.R` bones. Runtime scripts must not drive these blend shapes, or they fight the baked tracks.
  Material slots of the head: `<model>_face` (skin), `Mouth_Inner`, `<model>_eye_sclera`, `_eye_iris`, `_eye_cornea`,
  `_eye_tearline`, `_teeth`, `_tongue`, `_lashes`, `_brows`.

## Validate

```bash
python tools/validate_glb.py godot/assets          # skin, required animations, protagonist >= 100 clips, size
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd
~/godot/godot --headless --path godot -s res://tests/animations_test.gd   # heroes: every move plays, loops flagged
python blender/render_animation_sheet.py --name cultivator_female --strips walk,run --frames 8 --view side \
    --engine workbench --travel --out /tmp/strip.jpg                     # visual foot-planting check
```

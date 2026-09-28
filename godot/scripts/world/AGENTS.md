# AGENTS.md: godot/scripts/world/

This directory holds the hand-written in-world actors and systems that `game.gd`, `quest_runner.gd` and `player.gd`
spawn at runtime. Most are code-only nodes with a `class_name` and a static `create(...)`, with no `.tscn`.

| Script | Class | Role |
|---|---|---|
| `npc.gd` | `Npc` | story character at a marker: model from `res://assets/characters/<model>.glb` (falls back to `disciple_male`), name plate, quest mark, `face()` |
| `enemy.gd` | `Enemy` | data-driven enemy (`kind` -> stats, model, `sfx`): chase, attack, flinch, die; stair stepping; gait speed_scale; returns to spawn below `kill_y`; 2.5 m vertical reach; falls back to the bandit model |
| `pickup.gd` | `Pickup` | collectible: `res://assets/items/<item>.glb` (via world.json `item_model_dir`) or a glowing primitive; `COLORS` per item |
| `prop.gd` | `QuestProp` | interactable object: the GLB named in world.json `props` (or a glowing seal), stood on the ground, cylinder body; `footprint()` scales reach, beacon and NPC circles |
| `beacon.gd` | `Beacon` | objective pillar of light + rune ring (lifted 14 cm against z-fighting) |
| `tribulation.gd` | `Tribulation` | heavenly tribulation objective: storm clouds, telegraphed lightning volleys, beast / heart-shade waves |
| `conversation.gd` | | stages talk scenes: who faces whom, over-the-shoulder camera cut per line (180-degree rule, pulled in front of walls), gestures |
| `monologue.gd` | | the hero thinks out loud while roaming (`game.hud.say_thought()`); silent during dialogue, cinematics, combat, meditation, menus |
| `player_moves.gd` | | the heroes' 130+ move runtime: combos, dodges, block / parry, jumps / glide / ledges, crouch / sneak / sprint / slide, techniques, emotes; `reset_state()` on every teleport |
| `actor_look.gd` | `ActorLook` | material fixes on imported character GLBs, matched by material name: skin SSS, alpha-scissor hair cards with anisotropy, additive cornea / tear line, NPC tints, the shadow heart-demon look |
| `stepper.gd` | | `step_up()` / `step_down()` for CharacterBody3D walkers (lift <= 0.45 m), used by the player and enemies |
| `doors.gd` | `Doors` | static registry: exterior map + door marker -> interior map / spawn, plus `ExitDoor` links back |
| `qi_blast.gd` | | travelling qi projectile (`Area3D`) that damages the first enemy it touches |

## Contracts

- Ids (models, enemies, items, props, markers) come from `Story.world` / story.json, which are generated from
  `tools/world_spec.py`. `doors.gd` must agree with `tools/maps/interiors.py` on interior map ids and marker names.
- Gait: `speed_scale = ground speed / (AUTHORED_SPEED x model scale)`. The speeds are walk 1.6 / run 4.6 /
  sprint 6.2 m/s, as authored in `blender/xianxia/gait.py`. Reset `speed_scale` to 1 for attacks and hits
  (runtime.md #13-14).
- Every animation name `player_moves.gd` plays must exist in the hero GLBs (built by `blender/xianxia/moves.py`).
  `res://tests/animations_test.gd` checks this.

## Pitfalls (docs/bugfixes/runtime.md)

- Use `is_grounded()` rather than `is_on_floor()` for "standing?" checks, because a capsule on a stair nose is not on
  the floor (#8). Move with `player.move_body()`, not a bare `move_and_slide()`, so stairs work (#10).
- Ground everything that is placed next to a marker (`map.ground_at`), and skip actors whose marker is missing
  instead of placing them at the origin (#51, #58-59, #66).
- Timers for gameplay effects must not run while paused (`create_timer(t, false)`, #73).
- Heights: surface decals must sit at least 14 cm above uneven ground (#63-64).

Test with `smoke_test.gd`, `animations_test.gd` and a `walkthrough_test.gd` shard (see [../AGENTS.md](../AGENTS.md)).

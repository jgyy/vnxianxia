# AGENTS.md: godot/scenes/

This directory holds the Godot scenes. The three top-level scenes are **hand-written** and tiny: they only attach a
script, and all behaviour lives in `godot/scripts/`. The map scenes in [maps/](maps/AGENTS.md) are **generated**.

| Scene | Root | Script | Notes |
|---|---|---|---|
| `title.tscn` | `Title` (Node3D) | `scripts/title.gd` | main scene (`project.godot` `run/main_scene`); menu over the sect at dusk |
| `game.tscn` | `Game` (Node3D) | `scripts/game.gd` | the play session; instances `player.tscn` as `Player` and loads maps as children from `res://scenes/maps/<id>.tscn` |
| `player.tscn` | `Player` (CharacterBody3D) | `scripts/player.gd` | capsule r 0.3 / h 1.7 at y 0.85, `ModelRoot`, `CameraPivot/SpringArm3D/Camera3D` |

## player.tscn values that are tuned on purpose (docs/bugfixes/runtime.md)

- `floor_snap_length = 0.5`, `floor_constant_speed = true`, `floor_max_angle` 50 degrees (#11). Stair stepping is
  handled in `scripts/world/stepper.gd`.
- The SpringArm3D uses a 0.2 m `SphereShape3D`, not a ray, so the camera does not clip through wall edges (#62).
- Camera `near = 0.15`, `far = 1500` for depth precision. A smaller near or larger far brings back floor z-fighting
  (#60).
- `collision_mask = 3`. The node paths `ModelRoot`, `CameraPivot`, `CameraPivot/SpringArm3D` and
  `.../Camera3D` are `@onready` in `player.gd`, so renaming a node breaks the script.

## Conventions

- Keep these scenes minimal. Build UI and dynamic nodes in code (the HUD, dialogue, journal and cinematic are
  CanvasLayers created by `game.gd` from preloaded scripts), in the same style as the existing code.
- Scene files use the text `format=3` without UIDs on `ext_resource`. Paths are `res://`, so moving a script means
  updating the scene.
- Test after any change: `~/godot/godot --headless --path godot -s res://tests/smoke_test.gd` (it plays a session:
  walk, run, strike, qi blast, meditate, talk, journal, switch hero) and a walkthrough shard.

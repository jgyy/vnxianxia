# AGENTS.md: godot/scripts/

This is all the runtime GDScript (hand-written, Godot 4.7). Subdirectories: [autoload/](autoload/AGENTS.md)
(singletons), [ui/](ui/AGENTS.md) (CanvasLayers and the theme) and [world/](world/AGENTS.md) (in-world actors and
systems). The content this code drives (story, world ids, maps, models, audio) is generated elsewhere and read at
runtime.

| Script | Role |
|---|---|
| `game.gd` | the session (`game.tscn`): threaded map loading behind the loading screen, travel and doors, NPC population by story progress (`ensure_npc`, `refresh_npcs`), conversation scenes (`converse`, `choose`, `scene_begin/end`, `release_controls`), respawn |
| `quest_runner.gd` | runs the active objective: spawns NPCs / group `party_ids` / enemies / pickups / props / beacons, detects completion, offers moral choices, rewards, breakthroughs, victory music; an `_epoch` counter stops stale coroutines after a map change |
| `player.gd` | third-person controller (walk / run / sprint gaits, `AUTHORED_SPEED`, `stride_scale`, `gait_for` hysteresis, `move_body` with stair stepping, `is_grounded`, `hold_pose`, jump buffer); owns `world/player_moves.gd` |
| `map.gd` | root script of every generated map: `@export map_id, display_name, music, ambient, kill_y`; marker lookup and ground ray casts (`marker_position`, `ground_at`, `marker_grounded`, `is_open`, `open_spot`); ambient particles |
| `title.gd` | title menu: new game, continue, volume / chapter select, quit |
| `fx.gd` | `class_name Fx`: procedural particle effects shared by maps, combat and cinematics |

## GDScript style used here

- Tabs, static typing (`var x := 0.0`, `-> void`, typed `Array`/`Dictionary` casts), `##` doc comments on the class
  and on non-obvious members, `_private` names. Helpers without a scene use `class_name` + `extends RefCounted` /
  `Node3D` and a static `create()` (see `world/npc.gd`).
- Scenes are minimal. UI and actors are built in code, and cross-script references use `preload` constants
  (`game.gd` preloads the UI scripts, the runner, the monologue and the conversation).
- Content ids come from `Story.world` (world.json) and `Story` (story.json). Never hard-code a marker or model that
  is not in `tools/world_spec.py`. Missing models fall back with `push_warning` instead of crashing (`npc.gd`,
  `enemy.gd`).
- `Game.fast` is the test hook: it skips waits and fades, and choices come from `Game.auto_choice()`. Keep every new
  wait or tween skippable under it, or the walkthrough slows down or times out.
- Use game-time timers (`create_timer(t, false)`) for gameplay, so the pause menu really pauses. Kill tweens before
  you free their target.

## Contracts with generated content

- Locomotion speed contract: `AUTHORED_SPEED` walk 1.6 / run 4.6 / sprint 6.2 m/s (sneak 1.0, crouch_walk 0.8,
  walk_back and strafes 1.0) must match `blender/xianxia/gait.py`. `speed_scale = ground speed / (authored x model
  scale)`, unclamped (docs/bugfixes/runtime.md #1-2).
- Map scenes follow the `Map / WorldEnvironment / Sun / Level / Markers` layout written by `tools/maps/common.py`.
- Group conversations: an objective's `with` NPCs stand in a circle with the talk target or around the marker, and
  are dismissed afterwards unless the map is their home (`quest_runner.gd` `party_ids`, `_place_party`,
  `_dismiss_party`).

## Test

```bash
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd
~/godot/godot --headless --path godot -s res://tests/walkthrough_test.gd -- 1 100      # any range in 1..2000
~/godot/godot --headless --path godot -s res://tests/animations_test.gd                # after player / moves changes
```

docs/bugfixes/runtime.md lists 76 fixed defects with file:line. Read it before you touch input handling, dialogue
timing, stairs, enemies or cinematics.

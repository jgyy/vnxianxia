# AGENTS.md: godot/tests/

These are hand-written headless tests and capture tools. Each one `extends SceneTree` and runs with
`-s res://tests/<file>.gd`. Arguments after `--` are read by the script, and each script exits with `quit(0)` or
`quit(1)`. Run `~/godot/godot --headless --path godot --import` once first. Run one Godot process at a time on this
shared machine.

| Script | In CI | What it does |
|---|---|---|
| `smoke_test.gd` | yes (`godot-smoke-test`) | every character / environment GLB loads (rig: 1 Skeleton3D + AnimationPlayer with the required clips); models and props from world.json exist; every map loads with all markers present and grounded, more than 10 collision bodies, its music; voice files and portraits exist; conditions and a save round trip; plays a session (walk, run, strike, qi blast, meditate, damage, talk, journal, hero switch) |
| `walkthrough_test.gd` | yes, 20 shards | plays quests `first..last` (1-based, 1..2000) through the real systems: travel, talk, fight, collect, meditate, interact, cinematics, tribulations. `Game.start_at` applies the earlier rewards, `Game.auto_choice` varies the alignment, and `OBJECTIVE_TIMEOUT` is 1800 physics frames per objective |
| `capture_screenshots.gd` | yes (`screenshots`, lavapipe) | showcase PNGs into the out_dir; CI requires at least 12 |
| `animations_test.gd` | no | both heroes have at least 100 unique non-empty clips, every clip `player_moves.gd` names exists, loops are flagged, and every move, combo, dodge and emote plays |
| `capture_world_check.gd` | no (headless) | for every exterior marker: ground, a standing capsule fits, 6 of 8 ring spots at 3.5 m open and level, ground 9 m south; exits non-zero on failure |
| `capture_hud.gd` | no (GPU / lavapipe) | HUD screenshots at several window sizes (`-- out_dir [WxH,...] [quick]`) |
| `capture_map.gd`, `capture_world_shots.gd` | no (GPU / lavapipe) | map screenshots from above and from markers / explicit cameras. `--flicker` counts pixels that change under a 2 cm camera nudge (z-fighting) |
| `capture_loading_art.gd` | no (GPU) | **writes committed files**: `res://ui/loading/<map>.jpg` key art |

```bash
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd
~/godot/godot --headless --path godot -s res://tests/walkthrough_test.gd -- 101 200
~/godot/godot --headless --path godot -s res://tests/animations_test.gd
~/godot/godot --headless --path godot -s res://tests/capture_world_check.gd -- sect
xvfb-run -a -s "-screen 0 1280x720x24" ~/godot/godot --path godot --rendering-driver vulkan \
    --resolution 1280x720 -s res://tests/capture_screenshots.gd -- /tmp/shots
```

## Conventions

- Tests drive the real game (`game.tscn`, autoloads) with `Game.fast = true` to skip waits. Prefer waiting on a
  condition with a frame limit (`walkthrough_test.gd` `_wait(cond, limit)`) over fixed sleeps, because CI machines
  are slow and shared.
- Enumerate content from `Story.world` / story.json, never from hard-coded lists, so new maps, models and props are
  covered automatically. Directory scans (`DirAccess.get_files_at`) must filter by extension, as `_assets()` does
  with `.glb`. Other files in `res://assets/*`, such as AGENTS.md, are skipped.
- Report failures through `check(cond, msg)` / `fail(msg)` and exit with `quit(1)`, because CI relies on the exit code
  through `tee` with `pipefail`.
- When a walkthrough shard fails, rerun just that range. The cause is usually a marker that is too close to an edge
  or inside a building (tools/maps), or a runtime regression. See docs/bugfixes/world.md #46 and runtime.md.
- If you add a test that CI should run, add a step to `.github/workflows/ci.yml` and mention it in README.md.

# AGENTS.md: godot/ui/loading/

This directory holds the loading-screen key art, one 1280x720 JPEG per exterior map (`sect`, `bamboo_forest`,
`qingshi_town`, `blood_abyss`, `sky_isles`), each with a committed `.jpg.import`. The images are **generated
in-engine** by `godot/tests/capture_loading_art.gd`. It loads each map scene, poses characters (with the given
animations) near a focus marker, frames a camera shot and saves `res://ui/loading/<map_id>.jpg` at JPEG quality 0.86.

```bash
~/godot/godot --path godot --rendering-driver vulkan -s res://tests/capture_loading_art.gd   # needs a GPU or lavapipe
# headless CI-like machine: xvfb-run -a ~/godot/godot --path godot --rendering-driver vulkan -s res://tests/capture_loading_art.gd
~/godot/godot --headless --path godot --import                                             # then commit .jpg + .jpg.import
```

## How it is used

`godot/scripts/ui/loading_screen.gd` (`ART_DIR = "res://ui/loading/"`) shows `<map_id>.jpg` behind the map name,
the chapter or volume synopsis, a tip and the progress bar while `game.gd` loads the map on a thread. A map with no
image (every interior, for example) simply shows no art. That is intended, not an error.

## Rules

- Never retouch the JPEGs. To change a shot, edit the `SHOTS` table in `capture_loading_art.gd` (map -> focus
  marker, camera offset, look offset, actors as `[model, marker offset, anim]`) and re-render.
- Re-render after a map's layout or look around its focus marker changes a lot (`tools/maps/*`, environment GLBs),
  or after character models change, so the art matches the game.
- The focus markers must exist in `tools/world_spec.py`, and the actor models must be valid `MODELS` ids with the
  named animations.
- A new exterior map should get a `SHOTS` entry and a committed JPEG. The file name must equal the map id.

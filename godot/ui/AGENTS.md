# AGENTS.md: godot/ui/

These are the 2D resources for the interface. The code that uses them lives in `godot/scripts/ui/`, mainly
`ui_theme.gd`, `hud.gd`, `dialogue_ui.gd` and `loading_screen.gd`. Apart from the fonts, everything here is
**generated** and committed with its `.import` sidecar.

| Subdirectory | Contents | Source | Guide |
|---|---|---|---|
| `fonts/` | Marcellus, Alegreya Sans, a Ma Shan Zheng HUD subset (+ OFL licences) | third-party (SIL OFL), hand-added | [fonts/AGENTS.md](fonts/AGENTS.md) |
| `hud/` | the HUD kit: 37 PNGs + `hud_kit.json` | `python blender/render_hud.py` | [hud/AGENTS.md](hud/AGENTS.md) |
| `loading/` | key art per exterior map, `<map_id>.jpg` 1280x720 | `res://tests/capture_loading_art.gd` (GPU) | [loading/AGENTS.md](loading/AGENTS.md) |
| `portraits/` | dialogue portraits, `<model>.png` 256x256 | `python blender/render_portraits.py` | [portraits/AGENTS.md](portraits/AGENTS.md) |

## Rules

- Scripts find these files by naming convention (`res://ui/portraits/<model>.png`, `res://ui/loading/<map_id>.jpg`,
  `res://ui/hud/<piece>.png`, `res://ui/fonts/<file>.ttf`). Keep the names in step with the model ids and map ids of
  `tools/world_spec.py`.
- Never retouch generated images by hand. Change the generator and re-render, then run
  `~/godot/godot --headless --path godot --import` and commit the image with its `.import` file.
- UI art is authored for the 1280x720 logical canvas (`canvas_items` stretch). The HUD PNGs are rendered at 2x so
  they stay sharp up to 1440p.

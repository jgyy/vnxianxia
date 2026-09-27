# AGENTS.md: godot/

This is the Godot **4.7.2** project (`project.godot`, Forward Plus). Open or run it with `--path godot`. Most of the
content is **generated** elsewhere in the repo and committed here together with its `.import` sidecars. The
hand-written parts are `scripts/`, `tests/`, the three top-level scenes in `scenes/`, `project.godot`, `icon.svg` and
the fonts.

| Directory | Contents | Source | Guide |
|---|---|---|---|
| `assets/` | characters / environment / items GLBs | `blender/build_assets.py` | [assets/AGENTS.md](assets/AGENTS.md) |
| `audio/` | music, sfx, voice (Ogg Vorbis) | `tools/gen_audio.py`, `tools/gen_voices.py` | [audio/AGENTS.md](audio/AGENTS.md) |
| `data/` | `story.json`, `world.json` | `tools/build_story.py`, `tools/world_spec.py` | [data/AGENTS.md](data/AGENTS.md) |
| `scenes/` | `title.tscn`, `game.tscn`, `player.tscn` (hand-written), `maps/*.tscn` (generated) | `tools/build_maps.py` | [scenes/AGENTS.md](scenes/AGENTS.md) |
| `scripts/` | all GDScript runtime code | hand-written | [scripts/AGENTS.md](scripts/AGENTS.md) |
| `tests/` | headless tests and capture scripts (`extends SceneTree`) | hand-written | [tests/AGENTS.md](tests/AGENTS.md) |
| `ui/` | fonts, HUD kit, loading art, portraits | Blender renders + capture script | [ui/AGENTS.md](ui/AGENTS.md) |

## project.godot essentials

- Main scene: `res://scenes/title.tscn`. Autoloads: `Story` (`scripts/autoload/story.gd`), `Game`
  (`scripts/autoload/game_state.gd`) and `Audio` (`scripts/autoload/audio.gd`).
- The base canvas is 1280x720 with `window/stretch/mode="canvas_items"` and `aspect="expand"`. All UI sizes are
  logical 720p pixels.
- `[importer_defaults] scene` sets `meshes/generate_lods=false` for new imports, because LOD swaps made terrain and
  floors pop. The committed `.glb.import` files decide the rest: `true` for characters, items and the 24 vegetation /
  rubble environment GLBs, `false` for every other environment GLB.
- Physics runs at 60 ticks. There is a 4096 directional shadow atlas and MSAA 2x.

## Commands

```bash
~/godot/godot --headless --path godot --import       # build .godot/ (gitignored); several minutes the first time
~/godot/godot --path godot                           # play
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd
~/godot/godot --headless --path godot -s res://tests/walkthrough_test.gd -- 1 100
~/godot/godot --headless --path godot -s res://tests/animations_test.gd
```

## Rules

- **Commit the `.import` files** (and the `.gd.uid` files for new scripts). They carry the UIDs and import
  options: `generate_lods`, and `loop=false` on the audio, whose looping is set in code. After adding assets, run
  `--import` and commit the new sidecars. Do not commit `.godot/` or the textures Godot extracts next to the GLBs
  (`assets/**/*.png|jpg`, gitignored).
- Godot ignores `.md` files (no `.import` is created), so the AGENTS.md files here are inert.
- Every content id (map, marker, model, enemy, item, prop, realm) comes from `data/world.json` / `data/story.json`.
  Do not hard-code new ids in scripts without adding them to `tools/world_spec.py`.
- Run one Godot process at a time on the shared 4-core machine. An import or a walkthrough shard is heavy.

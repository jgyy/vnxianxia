# AGENTS.md: tools/

This directory holds the data compilers, generators and validators, all hand-written Python. Subpackages:
[maps/](maps/AGENTS.md) (map layouts) and [story/](story/AGENTS.md) (the saga as data). Run the scripts from the repo
root. They find their paths from `__file__`.

| Script | Deps | What it does |
|---|---|---|
| `world_spec.py` | stdlib | **Single source of truth**: `MAPS` (+ markers with descriptions), `MODELS`, `NPC_MODELS`, `ENEMIES`, `BOSSES`, `ITEMS`, `PROPS`, `REALMS`, `STAGES`, alignments, `OBJECTIVE_TYPES`. `python tools/world_spec.py` writes `godot/data/world.json`; `--check` fails if that file is stale. |
| `build_maps.py` | stdlib | `python tools/build_maps.py [map_id ...]` writes `godot/scenes/maps/<id>.tscn` for the five exterior maps and the 13 interiors (see `maps/`). |
| `build_story.py` | stdlib | Compiles `story/` into `godot/data/story.json` and validates it against `world_spec.py`. `--check` (CI), `--quiet`, `--out`, `--quests docs/QUESTS.md`. |
| `gen_voices.py` | piper-tts, numpy, soundfile (`--check` is stdlib) | Piper TTS for every line with a `voice` path: `godot/audio/voice/<key>[_m/_f].ogg` + `manifest.json`. Hash-based and resumable. `--check`, `--prune`, `--only PREFIX`, `--workers`, `--limit`. |
| `gen_audio.py` | numpy, scipy, soundfile | Synthesises 11 music loops and 42 SFX into `godot/audio/{music,sfx}/` (`--only`, `--out`, `--jobs`, `--verbose`). The cues are described in docs/AUDIO.md. |
| `validate_glb.py` | stdlib | `python tools/validate_glb.py godot/assets`: GLB container, textured materials, rigs + required animations, quest-prop collision / grounding / 1.5 MB budget, items collision-free / <= 0.6 m / 512 KB / bottom-centre origin, missing `PROPS` / `ITEMS` models. |
| `zfight_glb.py` | stdlib | Finds coplanar overlapping triangles: `python tools/zfight_glb.py --names a,b godot/assets` (`--eps`, `--area`, `--detail N`, `-q`). Not in CI. The four terrains together take about 5 min. |

## Conventions

- Everything CI runs in the `lint` job (`world_spec.py`, `build_maps.py`, `build_story.py`, `validate_glb.py`,
  `gen_voices.py --check`) must stay **stdlib-only**. Heavy imports belong in the synthesis paths only.
- Outputs must be **deterministic**. CI runs `build_maps.py` and then `git diff --exit-code -- godot/scenes/maps`, and
  compares story.json and world.json byte for byte. world.json uses `sort_keys`, and story.json uses
  `build_story.dumps` (compact, 110-column). Both end with a trailing newline. Never reformat them by hand.
- The order of changes: edit `world_spec.py` -> `python tools/world_spec.py` -> build what it names (GLBs, map
  markers) -> `build_maps.py` / `build_story.py`. `maps/common.check_markers` fails a map whose markers differ from
  `MAPS[map]["markers"]`.
- gen_voices finds Piper models in `$PIPER_VOICES`, `~/voices` or `/home/user/voices` (the rhasspy/piper v0.0.2 release
  models, e.g. `en-us-lessac-medium.onnx`). When piper is not importable it re-executes itself with `$PIPER_PYTHON`.
  Only the ten original chapters are voiced. The other lines have `"voice": null`.

## Checks

```bash
python -m py_compile tools/*.py tools/maps/*.py tools/story/*.py
python tools/world_spec.py --check
python tools/build_maps.py && git diff --exit-code -- godot/scenes/maps
python tools/build_story.py --check
python tools/gen_voices.py --check      # exits 1 on missing / stale files; orphans are only reported
python tools/validate_glb.py godot/assets
```

## Pitfalls

- `gen_voices.py --check` ignores orphaned `.ogg` files. Run `--prune` after you remove voiced lines, or dead files
  get committed. It only looks at `*.ogg` in the voice directory, so other files there are harmless.
- `build_story.py --check` does not regenerate `docs/QUESTS.md`. Pass `--quests docs/QUESTS.md` when the quest list
  changes.
- `validate_glb.py` treats nodes or meshes whose name contains `colonly` as collision (docs/bugfixes/props.md #8). A
  collider without that suffix is counted as visible geometry and needs a material.

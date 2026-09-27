# AGENTS.md: .github/workflows/

`ci.yml` is the only workflow. It has five jobs, all on `ubuntu-24.04`:

| Job | What it does | Timeout |
|---|---|---|
| `lint` | Python 3.13: `py_compile` of every script, `tools/validate_glb.py godot/assets`, `tools/world_spec.py --check`, `tools/build_maps.py` then `git diff --exit-code -- godot/scenes/maps`, `tools/build_story.py --check`, `tools/gen_voices.py --check` | default |
| `blender-build` | `pip install bpy==5.2.2` (plus X11/GL libs for the wheel), `python blender/build_assets.py --out build/assets`, `validate_glb.py build/assets`, uploads the `xianxia-glb-assets` artifact | 120 min |
| `godot-smoke-test` | downloads Godot 4.7.2 to `~/godot/godot` (cached), `--import`, `res://tests/smoke_test.gd` | 75 min |
| `godot-walkthrough` | a 20-shard matrix (two per volume, 100 quests each): `walkthrough_test.gd -- first last` | 90 min |
| `screenshots` | needs the smoke test; lavapipe + xvfb, `capture_screenshots.gd -- $PWD/build/screenshots`, needs at least 12 PNGs | 150 min |

## Conventions and pitfalls

- The `lint` job needs no third-party packages. The scripts it runs (`validate_glb.py`, `world_spec.py`,
  `build_maps.py`, `build_story.py`, `gen_voices.py --check`) must stay stdlib-only. The `blender/` scripts are only
  byte-compiled there, never imported.
- `blender-build` writes to `build/assets`, not the committed `godot/assets`. It proves that the generators still
  run, but it does not diff the output against the committed GLBs.
- The Godot download step appears three times (smoke, walkthrough, screenshots) with the same cache key
  `godot-${GODOT_VERSION}-linux`. Keep the three copies identical.
- The walkthrough shard bounds must cover 1..2000 without gaps. The numbers also appear in `README.md` and in
  `godot/tests/walkthrough_test.gd`'s header.
- Timeouts were sized for the 10x world (about 270 environment GLBs). If you add many assets or quests, re-measure
  locally before you tighten a timeout.
- Every Godot step pipes through `tee` with `set -o pipefail`, so a failing test still fails the job. Keep that
  pattern when you add a step.

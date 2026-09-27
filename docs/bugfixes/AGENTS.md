# AGENTS.md: docs/bugfixes/

These are hand-written logs of genuine defects found and fixed, one file per workstream. Read the log for your area
**before** changing code there: most entries are traps that are easy to fall into again (coplanar faces, speed
contracts, input races, duplicate node names).

| Log | Area | Typical lessons |
|---|---|---|
| `animation.md` | `blender/xianxia/gait.py`, `moves.py`, `characters.py` | foot slip is measured by `gait.verify_clip`; the authored speeds (walk 1.6 / run 4.6 / sprint 6.2 m/s) must match the runtime; loops need whole cycles and must be baked on every frame |
| `hair_skin.md` | `hair_*.py`, `skin*.py`, `tex.py`, `preview.py` | `tex.fbm` NaN at small sizes; MikkTSpace needs real UVs; Cycles needs 64 transparent bounces for hair cards |
| `hud.md` | `godot/scripts/ui/hud.gd`, `project.godot` | `canvas_items` stretch; one centre-stage queue; container-fitted panels; kill tweens before freeing |
| `props.md` | `quest_props.py`, `items.py`, `tools/validate_glb.py`, `tools/zfight_glb.py` | missing GLBs fail validation; items carry no collision; the `--only` name clash; z-fighting causes and fixes |
| `runtime.md` | `godot/scripts/**`, `godot/scenes/player.tscn`, `project.godot` | 76 fixes: locomotion speed_scale, stairs (`stepper.gd`), dialogue input and timing, quest coroutine epochs, audio cross-fades, camera near/far, LODs |
| `story.md` | `tools/story/*`, `tools/build_story.py`, `tools/gen_voices.py` | the `with` contract; voice keys that never move (`added(...)`); time-aware NPC categories; filler pools |
| `world.md` | `blender/xianxia/{lands,realms,arch,buildings*,interiors}.py`, `tools/maps/*` | split terrain instead of overlays; walkable colliders; z-fighting offsets; markers clear of buildings; unique Level node names |

## Format (keep it)

Each file has a `# Title` and a line explaining the format, followed by a numbered list with **one line per
defect**:

```
N. <symptom> -> <cause> -> <fix> (path/to/file.py:line)
```

Some files group entries in sections (e.g. "Reported to the runtime workstream", "Requested changes (not counted
above)"). When you fix a real defect, append the next number to the log for that area, with the file:line of the fix.
Record only genuine bugs, not feature work, and add requested features under their own heading. Line numbers are
"at commit time", so they are allowed to drift later.

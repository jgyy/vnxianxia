# AGENTS.md: godot/audio/sfx/

These are 42 **generated** mono sound effects, `<id>.ogg` (44.1 kHz Vorbis, under 1 MB in total), each with a
committed `.ogg.import`. They are synthesised from scratch (no samples) by `tools/gen_audio.py`: the `SFX` dict maps
`id -> (sfx_<id> function, gain dB, loops)`. Never edit or replace a file by hand. Every cue is described in
docs/AUDIO.md ("Sound effects").

The name families are `ui_*` (click, hover, open, close), `footstep_*`, combat (`sword_swing`, `sword_hit`, `hit_flesh`,
`hit_stone`, `block`, `qi_charge`, `qi_blast`, `player_hurt`, `enemy_death`), creatures (`wolf_*`, `golem_*`,
`serpent_roar`, `demon_laugh_ish`), quest and progress cues (`quest_accept`, `quest_complete`, `objective_update`,
`pickup`, `chest_open`, `breakthrough`, `chapter_title`, `teleport`, `gameover`), ambience (`thunder`, `bell_toll`,
`drum_hit`, `heartbeat`) and the three loops `meditate_loop`, `wind_loop`, `fire_loop`.

## How the runtime uses them

`Audio.sfx(id, volume_db, pitch)` in `godot/scripts/autoload/audio.gd` loads `res://audio/sfx/<id>.ogg` into a pooled
player. The ids are plain strings in the scripts (e.g. `Audio.sfx("qi_blast", -3.0)` in `player.gd`), and enemies
take theirs from their stats (`enemy.gd`, `stats.sfx`). Renaming a cue therefore means grepping `godot/scripts` for
the old id. Looping is decided in code: `audio.gd` `LOOPING` lists the three loop ids, and the `.import` stays at
`loop=false`.

## Rebuild

```bash
python tools/gen_audio.py --only qi_blast,thunder   # numpy, scipy, soundfile
```

The output is deterministic (seeded from string keys), apart from the Ogg serial number in the header, so rebuilt
files always differ as binaries. Commit only the cues you meant to change. One-shots have their silent tail trimmed
(`trim_silence`), and loops are built on a cyclic timeline so they join without a click. The script's verification
table (peak, loudness, loop-seam clicks) must pass.

To add a cue: write `sfx_<id>()`, register it in `SFX`, document it in docs/AUDIO.md, generate it, run
`~/godot/godot --headless --path godot --import` and commit the `.ogg` + `.ogg.import`. If it loops, add it to
`audio.gd` `LOOPING`.

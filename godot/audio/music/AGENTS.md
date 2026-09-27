# AGENTS.md: godot/audio/music/

These are 11 **generated** stereo music tracks, `<id>.ogg` (44.1 kHz Vorbis, about 11 MB in total), each with a
committed `.ogg.import`. They are synthesised note by note (guzheng, guqin, pipa, dizi, xiao, erhu, choir, taiko,
gongs, bells) by `tools/gen_audio.py` (`MUSIC` dict, `m_<id>` functions). Never edit, trim or replace a file by hand.

| id | Used for |
|---|---|
| `title` | title screen |
| `sect`, `forest`, `town`, `abyss`, `sky` | map music, chosen per map in `tools/world_spec.py` `MAPS[...]["music"]`; interiors reuse their region's track |
| `battle`, `boss` | fights and boss fights (`quest_runner.gd` `_set_fight`) |
| `victory` | 12.8 s jingle after a chapter's last quest (`quest_runner.gd`), **not** a loop |
| `sorrow`, `tribulation` | chosen by cinematics through `music=` in `tools/story/cinematics.py` (`ch04_lotus`, `ch09_sacrifice`, `ch10_tribulation`) |

The descriptions of each cue (mode, tempo, instruments) are in docs/AUDIO.md.

## Rebuild

```bash
python tools/gen_audio.py --only sect,battle     # numpy, scipy, soundfile (libsndfile with Vorbis)
python tools/gen_audio.py --verbose              # everything, about 3 min on 4 cores; prints a loudness profile
```

The output is deterministic: every random source is seeded from string keys, so the decoded audio is identical on
every run and only the Ogg stream serial in the header changes. A regenerated file therefore always shows up as a
binary diff. Commit it only when the cue really changed.

## Conventions and pitfalls

- Every track except `victory` is built on a **cyclic timeline** exactly one loop long (reverb and echo tails wrap
  around), so it loops seamlessly. The runtime enables looping in `audio.gd` `_stream(path, loop)`. The `.import`
  keeps `loop=false`, so leave it alone.
- Loudness is normalised per mood (about -13.5 to -18 LUFS) with a -1.2 dBFS limiter. The script's final
  verification table (peak, RMS, LUFS, seam click test) makes it exit non-zero if a cue fails, so fix the cue, not
  the check.
- A new track needs an `m_<id>` function in `MUSIC`, a mention in docs/AUDIO.md and, for map music, the id in
  `world_spec.MAPS`. Then run `python tools/world_spec.py`. The smoke test checks that each map's track and
  `title` / `battle` / `boss` / `victory` exist.

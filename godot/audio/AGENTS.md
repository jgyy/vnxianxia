# AGENTS.md: godot/audio/

All game audio is Ogg Vorbis and fully **generated**. Nothing here is recorded or hand-edited. The `.ogg.import`
sidecars are committed.

| Subdirectory | Contents | Generator | Guide |
|---|---|---|---|
| `music/` | 11 stereo tracks, `<id>.ogg` | `python tools/gen_audio.py` (numpy/scipy synthesis) | [music/AGENTS.md](music/AGENTS.md) |
| `sfx/` | 42 mono effects, `<id>.ogg` | `python tools/gen_audio.py` | [sfx/AGENTS.md](sfx/AGENTS.md) |
| `voice/` | about 1170 voiced dialogue lines + `manifest.json` | `python tools/gen_voices.py` (Piper TTS) | [voice/AGENTS.md](voice/AGENTS.md) |

The runtime player is `godot/scripts/autoload/audio.gd` (the `Audio` autoload). It builds paths from `MUSIC_DIR`
(`res://audio/music/`) and `SFX_DIR` (`res://audio/sfx/`) plus the cue id, cross-fades the music, keeps a pooled SFX
bus and a separate voice player. **Looping is set in code**: `_stream(path, loop)` sets
`AudioStreamOggVorbis.loop`, and the `.import` files keep `loop=false`. Do not flip the import option. Music loops
(except `victory`), as do the SFX listed in `audio.gd` `LOOPING` (`meditate_loop`, `wind_loop`, `fire_loop`).

Synthesis and cue descriptions: docs/AUDIO.md. Setup: `pip install numpy scipy soundfile piper-tts` in the Python
3.13 venv, and Piper voice models from the rhasspy/piper v0.0.2 release in `~/voices`.

Checks: `python tools/gen_voices.py --check` (CI). `gen_audio.py` ends with its own verification table (loudness,
peak, loop-seam click test) and exits non-zero on failure. The smoke test checks that each map's music and the
title, battle, boss and victory tracks exist.

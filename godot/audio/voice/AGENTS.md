# AGENTS.md: godot/audio/voice/

This directory holds about 1170 **generated** neural-TTS voice lines (mono Ogg Vorbis, 22050 Hz, about 33 MB), each
with a committed `.ogg.import`, plus `manifest.json`. They are all written by `tools/gen_voices.py` with Piper from
`godot/data/story.json`, using the casting in `tools/story/voices.py`. Never edit, rename or hand-record a file here,
and never hand-edit `manifest.json`.

## Naming (the key comes from build_story and is stored in each line's `voice` path)

- `q<NNN>_o<obj>_l<line>.ogg` is a line of the **original** voiced chapters. `NNN` is the three-digit *original* quest
  number, not the saga number (e.g. `q017_o2_l1`). Lines marked `added(...)` in the chapter files are keyed after the
  objective's original lines, so existing keys never move.
- `cin_<cinematic>_s<shot>.ogg` is a cinematic subtitle (e.g. `cin_ch09_sacrifice_s2`).
- The suffixes `_m` / `_f` mark gendered takes for lines spoken by the protagonist or containing `{player}`-style
  tokens. `godot/scripts/autoload/story.gd` `voice_path()` picks `_m` for Lin Feng and `_f` for Su Yue.
- Only the ten original chapters are voiced. The lines of the 90 newer chapters have `"voice": null` and are shown as
  text.

`manifest.json` records, per file, a hash of (spoken text, voice settings, sample rate, `PROCESS_VERSION`, quality),
the speaker, the subtitle and the duration. A file is re-synthesised only when its hash changes, so runs are
resumable.

## Commands

```bash
python tools/gen_voices.py --check      # CI (stdlib only): exit 1 if any file is missing or stale
python tools/gen_voices.py              # synthesise missing / stale files (piper-tts, numpy, soundfile)
python tools/gen_voices.py --prune      # also delete .ogg files no line references any more
python tools/gen_voices.py --only q017  # restrict to a key prefix; --workers 4, --limit N
~/godot/godot --headless --path godot --import   # then commit the .ogg + .ogg.import + manifest.json
```

The Piper models (`*.onnx` + `.onnx.json`, e.g. `en-us-lessac-medium`, `en-us-libritts-high`) come from the
rhasspy/piper v0.0.2 GitHub release and live in `$PIPER_VOICES`, `~/voices` or `/home/user/voices`. If piper is not
importable, the script re-executes itself with `$PIPER_PYTHON`.

## Pitfalls

- Editing the text of a voiced line in `tools/story/chapterNN.py` or `cinematics.py` makes `--check` fail until you
  regenerate. Changing `voices.py` casting or `PROCESS_VERSION` in `gen_voices.py` re-synthesises many files.
- `--check` reports orphans but does not fail on them. Run `--prune` so that dead files do not stay committed.
- Only `*.ogg` files are scanned, so `manifest.json`, `.import` files and this AGENTS.md are ignored by `--check` and
  `--prune`.
- The smoke test checks that every voiced line's file exists and that the text-only lines resolve to no file.

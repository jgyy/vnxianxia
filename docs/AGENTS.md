# AGENTS.md: docs/

This is the project documentation, for humans and agents. Nothing in the game or the tools reads it. Subdirectories:
[bugfixes/](bugfixes/AGENTS.md) (defect logs per workstream) and [screenshots/](screenshots/AGENTS.md) (images used by
README.md).

| File | Kind | Content |
|---|---|---|
| `STORY.md` | hand-written | the plot, cast, ten volumes, original chapters, cultivation / tribulation / alignment rules, **how the story is stored in story.json** (field table, condition keys), how to edit the original and the new chapters, the full list of validation rules |
| `AUDIO.md` | hand-written | how `tools/gen_audio.py` synthesises the music and SFX, looping rules, and a description of every music cue and sound effect |
| `QUESTS.md` | **generated** | a table of all 2000 quests (number, title, map, objectives, rewards), written by `python tools/build_story.py --quests docs/QUESTS.md`. Never edit it by hand. |

## Keeping the docs true

- `docs/STORY.md` is the reference for the story data contract (the `with` rules, voice keys, condition keys, save
  version). When `tools/build_story.py` validation or the story.json format changes, update its "How it is stored"
  and "Validation" sections in the same change.
- `docs/AUDIO.md` lists every cue in `tools/gen_audio.py` `MUSIC` / `SFX`. Add a row when you add a cue.
- `QUESTS.md` is not checked by CI (`build_story.py --check` only compares story.json). Regenerate it whenever quest
  titles, maps, objectives or rewards change:
  `python tools/build_story.py --quests docs/QUESTS.md`.
- README.md (repo root) embeds images from `screenshots/` and quotes the counts (quests, animations, voice lines,
  assets). Keep those numbers in step when they change.
- The markdown is plain GitHub-flavoured, with Mermaid diagrams in README.md only. Godot ignores `.md` files, so
  nothing here needs an `.import`.

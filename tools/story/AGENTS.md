# AGENTS.md: tools/story/

This package is the 2000-quest saga (10 volumes x 10 chapters x 20 quests, ids `q0001..q2000`) written as
hand-written, stdlib-only Python data. `tools/build_story.py` compiles and validates it into **`godot/data/story.json`**
(generated: never edit it; rebuild). docs/STORY.md ("How it is stored", "Editing the story", "Validation") is the
authoritative reference.

## Files

| Group | Files | Role |
|---|---|---|
| Structure | `__init__.py`, `volumes.py`, `numbering.py`, `saga.py` | package entry (`NPCS`, volumes...); volume/chapter layout; id arithmetic shared with build_story and the runtime; title + premise |
| Original voiced chapters | `chapter01.py` .. `chapter10.py` | the ten hand-written chapters, slotted in as saga chapters 1, 2, 3, 11, 12, 21, 22, 31, 41, 100; the only voiced text |
| New chapters | `vol01.py` .. `vol10.py` | the 90 new chapters as outlines `C(title, map, summary, cast=, foes=, items=, props=, boss=, beats=[B(...)])` |
| Generator | `saga_gen.py`, `fillers.py`, `places.py`, `ensemble.py` | deterministic expansion of outlines into quests; template lines; marker phrases / kinds / tags / `HAUNTS` / `PROPS_AT` / `ITEMS_AT`; group-conversation companions |
| Systems | `morality.py`, `choices.py`, `tribulations.py`, `threads.py`, `cinematics.py` | alignment, reactions, greetings, time-aware NPC categories; hand-written choices; tribulation objectives; "Story So Far" beats; the 20 cinematics (shots are `(yaw, distance, height)` around a marker) |
| Cast | `npcs.py`, `voices.py` | NPC ids as constants (a typo is a `NameError`), models, homes, `appear_from` / `hidden_after` / `gone_after`, locals in `MINOR`; Piper casting for gen_voices |
| DSL | `dsl.py` | `quest`, `talk`, `reach`, `defeat`, `collect`, `meditate`, `interact`, `cinematic`, `added`, `fill_with`... |

## The contracts that matter

- **`with` (group conversations):** every objective's `with` lists the NPCs present besides its `npc`. Every NPC who
  speaks (lines or choice replies) must be the `npc` or be in `with`. `dsl.fill_with` adds the speakers
  automatically, so `with_=(...)` is only needed for silent bystanders. The limits are four NPCs, never the `npc`
  itself, and all present in the story at that quest. Every quest needs a conversation with two or more NPC speakers
  plus the player. `godot/scripts/quest_runner.gd` (`party_ids`, `_place_party`) stands them in a circle.
- **Voice keys never move:** original lines are keyed `q017_o2_l1` (original quest, objective, line), and cinematic
  lines `cin_<id>_s<n>`. A line added later to a voiced objective must be written `added(SPEAKER, "text")`, which keys
  it after the originals. New-chapter lines are text-only (`"voice": null`). Voiced lines cannot be conditional.
- Ids for maps, markers, enemies, items, props and models are validated against `tools/world_spec.py`. Add them there
  first. The original cast's `appear_from` uses three-digit original ids (`q085`), and new ids use four digits.
- Text tokens `{player} {junior} {senior} {sibling} {they} {them} {their}` are resolved at runtime. A voiced line with
  a token gets `_m` / `_f` takes.
- Limits: lines at most 32 words, tracker text at most 64 characters, collect objectives carry no dialogue, boss
  fights have a count of 1. No line may be conditioned on a realm the player cannot hold at that quest.
- Determinism: the generator is a pure function of the outlines, and `build_story.py --check` compares bytes.

## Workflow

```bash
python tools/build_story.py                      # validate + write story.json + stats
python tools/build_story.py --quests docs/QUESTS.md   # when quest titles / objectives change
python tools/build_story.py --check              # CI
python tools/gen_voices.py --check               # after touching voiced chapters or voices.py
python tools/gen_voices.py && python tools/gen_voices.py --prune   # re-synthesise changed voiced lines
godot --headless --path godot -s res://tests/walkthrough_test.gd -- 1 100   # play the quests you changed
```

## Pitfalls (docs/bugfixes/story.md)

- NPC temperament is time-aware (`morality.category(nid, q)`), so Elder Gu is an elder until he is unmasked. Pass the
  quest number whenever you choose greetings, reactions or choice families.
- Filler pools depend on context: MEET vs REGROUP openers, AFTER_REPLY after an action, and `{place}` must be a real
  phrase, never the word "here".
- Choose prop words carefully (`saga_gen.PROP_WORDS`): a "ledger" is not a jade slip.
- Changing the text of a voiced line changes its hash, and `gen_voices.py --check` then fails until it is
  re-synthesised.

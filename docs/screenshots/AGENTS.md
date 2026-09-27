# AGENTS.md: docs/screenshots/

These are documentation images: about 45 JPEGs, plus one PNG, embedded in README.md and used as visual records of
workstreams. They sit outside `godot/`, so Godot never imports them, and no tool or test reads them. They are
**rendered, not drawn**. Each one comes from a capture or render script and is then converted to JPEG for size.

| Files | Produced by |
|---|---|
| `title_screen`, `loading_screen`, `cinematic_intro`, `cinematic_title_card`, `quest_hud`, `dialogue_voiced`, `meditation`, `journal`, `combat_forest`, `boss_jiao_serpent`, `map_<map_id>`, `characters_lineup`, `characters_portrait`, `creatures` | `godot/tests/capture_screenshots.gd` (writes PNGs to its out_dir; CI uploads them as the `godot-screenshots` artifact) |
| `hud_after_<W>x<H>`, `hud_banner_toasts`, `hud_dialogue_choice`, `hud_journal` | renamed captures from `godot/tests/capture_hud.gd`, which writes `hud_all_<W>x<H>`, `hud_banner_*`, `dialogue_choice_*`, `journal_*` PNGs |
| `hud_before` | the HUD before the Blender-rendered kit (a historical record that cannot be regenerated) |
| `world_<map>_<view>` | `godot/tests/capture_world_shots.gd` (explicit camera positions) |
| `characters_turnaround` | `blender/render_previews.py` (Cycles turnaround of both heroes) |
| `realism_face`, `realism_profile`, `realism_hand`, `hair_skin` | one-off Cycles close-ups made with the `blender/xianxia/preview.py` helpers. No committed script writes them, so re-create them with `preview.setup` / `camera` / `render` |
| `face_realism` | before/after face sheet: top row the committed `godot/ui/portraits` of cultivator_female, cultivator_male, disciple_female, elder_male before the landmark head; bottom row `python blender/render_portraits.py --only ... --samples 112 --size 512` after it, tiled 2x4 |
| `animations_sheet`, `gait_walk_run` | `blender/render_animation_sheet.py` (default out is `docs/screenshots/animations_sheet.jpg`; gait strips with `--strips walk,run --travel`) |
| `quest_props`, `items` | `blender/render_props_sheet.py --kind props` / `--kind items` |
| `dialogue_voiced_2000q.png` | an in-game capture kept as PNG |

```bash
xvfb-run -a -s "-screen 0 1280x720x24" ~/godot/godot --path godot --rendering-driver vulkan \
    --resolution 1280x720 -s res://tests/capture_screenshots.gd -- /tmp/shots   # GPU or lavapipe
python blender/render_props_sheet.py --kind items --out docs/screenshots/items.jpg
```

## Rules

- Commit JPEGs (roughly 100 KB to 3 MB). Convert large PNG captures before committing, and keep the file names
  stable, because README.md links to them by path (`docs/screenshots/<name>.jpg`).
- Replace a screenshot only with a fresh capture from the current build. Never edit an image to show something the
  game does not do.
- Some images (`hud_before`, `world_*`, `gait_walk_run`, ...) are not referenced in README.md but are kept as
  before/after records of a workstream. Check `git log` before you delete one.
- Heavy renders (lavapipe, Cycles) take many minutes. Run them one at a time on this shared machine.

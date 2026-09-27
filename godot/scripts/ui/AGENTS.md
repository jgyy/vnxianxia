# AGENTS.md: godot/scripts/ui/

This is the hand-written UI code. Every screen is a `CanvasLayer` built entirely in code (no `.tscn`). `game.gd`
creates them from preloaded scripts. All sizes are **logical pixels on the 1280x720 base canvas**. The project's
`canvas_items` stretch (`aspect="expand"`) scales them, so anchor to screen edges through containers instead of
absolute positions.

| Script | Role |
|---|---|
| `ui_theme.gd` | `class_name UiTheme`: the look (black-jade lacquer panels in gilt frames, parchment / gold colours); loads `res://ui/hud/hud_kit.json` + PNGs (`HUD_DIR`) as 9-slice / gauge textures and the fonts from `res://ui/fonts/` (`FONT_DIR`: Marcellus display, Alegreya Sans body, Ma Shan Zheng subset for hanzi) |
| `hud.gd` | gauges (HP / qi / XP, `TextureProgressBar`, `step = 0`, eased), quest scroll, horizon compass + objective marker, interact prompt, toasts (max 4, deferred during conversations), boss bar under the compass, meditation ring, key-hint chips, the centre-stage queue (`banner`, `title_card`, `quest_card`), `say_thought` |
| `dialogue_ui.gd` | conversation box with portrait (`res://ui/portraits/<model>.png`), whole line at once; `play()` (one press = one line, 90 ms per-line debounce, voiced lines advance 1.2 s after the voice, text lines after `Story.reading_time()`); `choose()` for moral choices (1-4, click, arrows / W / S + E / Enter / Space); `_fit()` to the window |
| `cinematic.gd` | letterbox, title card, camera moves around markers, voiced subtitles, posed actors; `_input()` consumes everything while active; Esc / Enter skips |
| `journal.gd` | pause menu / journal: current quest, Story So Far, chronicle, cultivation, settings, save, quit |
| `loading_screen.gd` | region key art from `res://ui/loading/<map>.jpg` (`ART_DIR`), name, tip, progress |
| `travel_menu.gd` | teleport-array destination picker (interiors excluded) |

## Conventions and pitfalls (docs/bugfixes/hud.md, runtime.md)

- The HUD art is generated. To change a frame, gauge or glyph, edit `blender/render_hud.py` / `blender/xianxia/hud_art.py`
  and re-render into `godot/ui/hud/`. Do not paint over the PNGs. The texture sizes, 9-slice margins and gauge
  windows come from `hud_kit.json`, so do not hard-code them.
- Centre-stage items (banners, volume title cards, quest cards) share **one queue**. Never show them with
  independent tweens, or they overlap (hud.md #3-4).
- A free-floating `PanelContainer` never shrinks. Put resizable panels in containers (`SHRINK_*`) so they are
  re-fitted (hud.md #7).
- Kill a node's tween before freeing it (hud.md #6, runtime.md #56, #67). Restore the previous mouse mode when a
  menu closes (runtime.md #53).
- Read advance and skip input in `_input()`, not `_unhandled_input()`, because the panel swallows clicks. Mark the
  input handled so the Space that closes a line does not make the hero jump (runtime.md #21-24).
- During a conversation, toasts wait, and the parts of the HUD that overlap the dialogue box fade out
  (`_conversation_up()`, `_fade_for_dialogue()`).
- Every wait must honour `Game.fast`, which the tests use.

## Test

```bash
~/godot/godot --headless --path godot -s res://tests/smoke_test.gd        # opens the journal, talks, plays a session
xvfb-run -a -s "-screen 0 2560x1440x24" ~/godot/godot --path godot --rendering-driver vulkan \
    -s res://tests/capture_hud.gd -- /tmp/hud 1280x720,1024x768,2560x1080   # HUD screenshots at several sizes
```

# AGENTS.md: godot/ui/fonts/

These are the only hand-added (not generated) binary assets in the project: three OFL-licensed fonts, each with its
licence text and a committed `.ttf.import`.

| File | Use | Licence |
|---|---|---|
| `Marcellus-Regular.ttf` | display type: names, titles, banners (`UiTheme.display_font()`); also the Latin glyphs in the HUD art (`blender/render_hud.py` `LATIN`) | `Marcellus-OFL.txt` |
| `AlegreyaSans-Medium.ttf` | reading text: dialogue, journal, tracker (`UiTheme.body_font()`), with emboldened / skewed variants built in code (`_variant`) | `AlegreyaSans-OFL.txt` |
| `MaShanZheng-HudSubset.ttf` | brush-script hanzi (`UiTheme.hanzi_font()`), and the 3D glyphs of the HUD kit (`render_hud.py` `HANZI`, e.g. the gauge medallions) | `MaShanZheng-OFL.txt` |

## Rules

- `godot/scripts/ui/ui_theme.gd` loads them by file name from `FONT_DIR` (`res://ui/fonts/`), and
  `blender/render_hud.py` reads Marcellus and the Ma Shan Zheng subset from this directory. Renaming a font breaks
  both, so update `ui_theme.gd` and `render_hud.py` together.
- `MaShanZheng-HudSubset.ttf` is a **glyph subset** of Ma Shan Zheng, not the full font. A new hanzi in the UI or the
  HUD art renders as a missing glyph until the subset is regenerated from the upstream Ma Shan Zheng font (Google
  Fonts, OFL) with that character added. After changing it, re-render the HUD kit (`python blender/render_hud.py`).
- Keep each `*-OFL.txt` next to its font, because the SIL Open Font License requires the licence to ship with the
  font. Add a licence file with any new font.
- Commit the `.ttf.import` with any new font, after `~/godot/godot --headless --path godot --import`.

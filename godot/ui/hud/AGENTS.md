# AGENTS.md: godot/ui/hud/

This is the **generated** HUD kit: 37 transparent PNGs (each with a committed `.png.import`) plus `hud_kit.json`.
`blender/render_hud.py` renders them, using the primitives in `blender/xianxia/hud_art.py`. Each piece is modelled as
small 3D geometry (bevelled lacquer slabs, gold-leaf wires, jade cabochons, brush-font glyphs) and rendered with
Cycles through a top-down orthographic camera. Troughs, glows and ink textures are numpy. **Never paint over or
resize these files. Re-render them.**

```bash
. /home/user/.venv/bin/activate
python blender/render_hud.py                          # everything (deterministic: fixed seeds + Cycles seed)
python blender/render_hud.py --only panel,gauges      # builder groups: panel scroll buttons toast prompt chip
                                                      #   portrait gauges spark compass ring icons banner
~/godot/godot --headless --path godot --import        # then commit PNGs, .png.import and hud_kit.json
```

With `--only`, the entries of the other pieces are kept: they are merged from the existing `hud_kit.json`.

## Pieces (names = files)

These are the logical sizes, in 1280x720 pixels. The PNGs are 2x.

- Panels and frames: `panel_fill` / `panel_frame` (96x96 9-slice, two layers that are tinted separately), `scroll`
  (quest tracker), `portrait_frame`, `toast`, `prompt`, `chip` (keycap), `button_{normal,hover,pressed,disabled}`,
  `divider`, `banner`.
- Gauges: `gauge_{hp,qi,xp}_frame`, `boss_frame`, `fill_{hp,qi,xp,boss}`, `trough_{gauge,xp,boss,compass}`,
  `glow_gauge`, `spark`.
- Navigation and other pieces: `compass_frame`, `compass_strip` (768 px = 360 degrees, north at x = 0, tileable),
  `marker`, `marker_edge`, `ring_{frame,fill,under}` (meditation), `glow_ring`, `lotus` / `lotus_done`.

## hud_kit.json: the contract with the runtime

`{"scale": 2, "items": {entry: {...}}}` is keyed by logical entries (`panel`, `button`, `gauge_hp`, `boss`,
`compass`, `ring`, `scroll`, ...), not by file names. Each entry names its PNG files (`layers`, `states`, `frame`,
`fill`, `trough`, `glow`, `strip`, `under`) and gives, in **logical** pixels, the canvas `size`, the 9-slice
`margins` `[l, t, r, b]`, the drop-shadow `pad`, suggested `content` margins and, for gauges and the compass, the
`window` rect `[x, y, w, h]` where the trough and fill go. `godot/scripts/ui/ui_theme.gd`
(`HUD_DIR`, `kit_scale()`) and `hud.gd` read it. Never hard-code these numbers in GDScript. If a piece's geometry
changes, re-render so the JSON and the PNG stay in step.

The glyphs use `godot/ui/fonts/MaShanZheng-HudSubset.ttf` (hanzi) and `Marcellus-Regular.ttf` (Latin). A new hanzi
needs the font subset regenerated first.

Visual check: `xvfb-run -a ~/godot/godot --path godot --rendering-driver vulkan -s res://tests/capture_hud.gd -- /tmp/hud`
(add `quick` for the HUD over a plain backdrop). The layout rules and bugs are in docs/bugfixes/hud.md.

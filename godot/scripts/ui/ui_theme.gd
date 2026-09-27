class_name UiTheme
extends RefCounted
## The game's UI look: black-jade lacquer panels in carved gilt frames with
## cloud-scroll corners (rendered in Blender by blender/render_hud.py into
## res://ui/hud/, described by hud_kit.json), Marcellus display type for names
## and titles, Alegreya Sans for reading text, and parchment/gold colours.
##
## Every piece of the kit is a 2x texture drawn at its logical size (the size
## it occupies on a 1280x720 canvas), so with the project's canvas_items stretch
## mode it stays crisp from 720p up to 4K.

const GOLD := Color(0.86, 0.72, 0.42)
const INK := Color(0.06, 0.07, 0.1, 0.82)
const TEXT := Color(0.96, 0.93, 0.85)
const MUTED := Color(0.78, 0.74, 0.66)
const JADE := Color(0.45, 0.9, 0.78)
const CRIMSON := Color(0.86, 0.22, 0.2)
const AZURE := Color(0.42, 0.76, 1.0)
const OUTLINE := Color(0.02, 0.025, 0.03)

const HUD_DIR := "res://ui/hud/"
const FONT_DIR := "res://ui/fonts/"
## Labels at or above this size use the display face (names, titles, banners).
const DISPLAY_FROM := 19

static var _theme: Theme
static var _kit: Dictionary
static var _tex := {}
static var _fonts := {}


# ------------------------------------------------------------------ kit data

## Metadata of one kit piece (sizes, 9-slice margins, windows) in logical px.
static func kit_item(item_name: String) -> Dictionary:
	if _kit.is_empty():
		var f := FileAccess.open(HUD_DIR + "hud_kit.json", FileAccess.READ)
		var parsed: Variant = JSON.parse_string(f.get_as_text()) if f else null
		_kit = parsed if parsed is Dictionary else {"scale": 2, "items": {}}
	return _kit.get("items", {}).get(item_name, {})


## Texel density of the kit textures (texels per logical pixel).
static func kit_scale() -> float:
	kit_item("")
	return float(_kit.get("scale", 2))


## A kit texture by file name (cached); null when missing.
static func hud_tex(file: String) -> Texture2D:
	if not _tex.has(file):
		var path := HUD_DIR + file
		_tex[file] = load(path) if ResourceLoader.exists(path) else null
	return _tex[file]


static func v2(a: Variant) -> Vector2:
	return Vector2(float(a[0]), float(a[1])) if a is Array and a.size() >= 2 else Vector2.ZERO


static func rect(a: Variant) -> Rect2:
	return Rect2(float(a[0]), float(a[1]), float(a[2]), float(a[3])) if a is Array and a.size() >= 4 else Rect2()


## A 9-slice StyleBox of the kit drawn at logical size (the texture is 2x).
## Each layer has its own modulate so fill and gilt frame tint independently.
class KitBox:
	extends StyleBox

	var layers: Array[Texture2D] = []
	var tints: Array[Color] = []
	var margins := Vector4(8, 8, 8, 8)  # left, top, right, bottom (logical px)
	var pad := Vector4.ZERO  # drawn beyond the control rect (drop shadow)
	var texel := 2.0

	func _draw(to_canvas_item: RID, r: Rect2) -> void:
		var rs := RenderingServer
		var dr := r.grow_individual(pad.x, pad.y, pad.z, pad.w)
		var s := texel
		# nine-patch borders are drawn 1:1 in texels, so draw in texel space
		# under a 1/s transform: the corners come out at their logical size.
		rs.canvas_item_add_set_transform(to_canvas_item, Transform2D(0.0, Vector2(1.0 / s, 1.0 / s), 0.0, Vector2.ZERO))
		var dst := Rect2(dr.position * s, dr.size * s)
		var tl := Vector2(margins.x, margins.y) * s
		var br := Vector2(margins.z, margins.w) * s
		# never let the borders overlap on a box smaller than its corners
		var k := minf(1.0, minf(dst.size.x / maxf(tl.x + br.x, 0.001), dst.size.y / maxf(tl.y + br.y, 0.001)))
		for i in layers.size():
			var t := layers[i]
			if t == null:
				continue
			var src := Rect2(Vector2.ZERO, t.get_size())
			rs.canvas_item_add_nine_patch(to_canvas_item, dst, src, t.get_rid(), tl * k, br * k,
				RenderingServer.NINE_PATCH_STRETCH, RenderingServer.NINE_PATCH_STRETCH, true, tints[i] if i < tints.size() else Color.WHITE)
		rs.canvas_item_add_set_transform(to_canvas_item, Transform2D.IDENTITY)


## A StyleBox of kit piece ``item_name`` (panel, scroll, toast, prompt, chip,
## button, portrait_frame). ``files`` overrides the layer files, ``tints`` the
## per-layer modulate. Returns a flat fallback when the kit is missing.
static func kit_box(item_name: String, tints: Array = [], files: Array = []) -> StyleBox:
	var it := kit_item(item_name)
	var names: Array = files if not files.is_empty() else it.get("layers", [])
	if it.is_empty() or names.is_empty() or hud_tex(names[0]) == null:
		return flat_panel()
	var b := KitBox.new()
	b.texel = kit_scale()
	var m: Array = it.get("margins", [8, 8, 8, 8])
	b.margins = Vector4(m[0], m[1], m[2], m[3])
	var p: Array = it.get("pad", [0, 0, 0, 0])
	b.pad = Vector4(p[0], p[1], p[2], p[3])
	for i in names.size():
		b.layers.append(_filtered(hud_tex(names[i])))
		b.tints.append(tints[i] if i < tints.size() else Color.WHITE)
	var c: Array = it.get("content", [12, 8, 12, 8])
	b.content_margin_left = c[0]
	b.content_margin_top = c[1]
	b.content_margin_right = c[2]
	b.content_margin_bottom = c[3]
	return b


## Wrap a texture so it samples with mipmaps whatever node draws it (a theme
## StyleBox is drawn by other scripts' controls with their own filter).
static func _filtered(t: Texture2D) -> Texture2D:
	if t == null:
		return null
	var ct := CanvasTexture.new()
	ct.diffuse_texture = t
	ct.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	return ct


static func _ratio(c: Color, ref: Color) -> Color:
	var f := func(a: float, b: float) -> float: return clampf(a / maxf(b, 0.001), 0.0, 6.0)
	return Color(f.call(c.r, ref.r), f.call(c.g, ref.g), f.call(c.b, ref.b), 1.0)


## The standard panel: lacquer tinted by ``bg`` (relative to INK) inside a
## gilt cloud-scroll frame tinted by ``border`` (relative to GOLD). ``radius``
## is kept for compatibility; ``border_w`` >= 2 brightens the gilt a little.
static func panel(bg := INK, border := GOLD, radius := 6, border_w := 1) -> StyleBox:
	var fill := _ratio(bg, INK)
	fill.a = clampf(bg.a / INK.a, 0.0, 1.0) * 0.93
	var frame := _ratio(border, GOLD)
	frame.a = border.a
	if border_w >= 2:
		frame = frame * Color(1.12, 1.12, 1.12, 1.0)
	var b := kit_box("panel", [fill, frame])
	if b is StyleBoxFlat:
		return flat_panel(bg, border, radius, border_w)
	return b


## The old flat look (rounded rect with a thin border), still handy for
## tooltips and fallbacks.
static func flat_panel(bg := INK, border := GOLD, radius := 6, border_w := 1) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(border_w)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 12
	s.content_margin_right = 12
	s.content_margin_top = 8
	s.content_margin_bottom = 8
	s.shadow_color = Color(0, 0, 0, 0.35)
	s.shadow_size = 5
	return s


## The hanging-scroll panel of the quest tracker.
static func scroll_panel() -> StyleBox:
	return kit_box("scroll")


## Ornamental portrait frame (144x144 logical, 128x128 opening at 8,8): use as
## a PanelContainer "panel" style around a 128x128 portrait TextureRect.
static func portrait_frame() -> StyleBox:
	return kit_box("portrait_frame")


static func button_style(state: String) -> StyleBox:
	var it := kit_item("button")
	var f: String = it.get("states", {}).get(state, "")
	return kit_box("button", [], [f]) if f != "" else flat_panel()


## A thin gilt rule with a jade lozenge, ``width`` logical px wide.
static func divider(width := 240.0) -> TextureRect:
	var t := TextureRect.new()
	t.texture = hud_tex("divider.png")
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_SCALE
	var sz := v2(kit_item("divider").get("size", [300, 14]))
	t.custom_minimum_size = Vector2(width, sz.y * width / maxf(sz.x, 1.0))
	t.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


## A kit icon (lotus, marker ...) at logical size * ``k``.
static func icon(file: String, k := 1.0) -> TextureRect:
	var t := TextureRect.new()
	t.texture = hud_tex(file + ".png")
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.custom_minimum_size = v2(kit_item(file).get("size", [20, 20])) * k
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return t


# ------------------------------------------------------------------ fonts

static func _font(file: String) -> Font:
	if not _fonts.has(file):
		var path := FONT_DIR + file
		_fonts[file] = load(path) if ResourceLoader.exists(path) else null
	return _fonts[file]


## Reading text (Alegreya Sans Medium); null falls back to the engine font.
static func body_font() -> Font:
	return _font("AlegreyaSans-Medium.ttf")


## Titles, names and banners (Marcellus).
static func display_font() -> Font:
	return _font("Marcellus-Regular.ttf")


## Brush-script CJK glyphs used on the HUD (a small subset of Ma Shan Zheng).
static func hanzi_font() -> Font:
	return _font("MaShanZheng-HudSubset.ttf")


static func _variant(key: String, embolden: float, skew: float) -> Font:
	if not _fonts.has(key):
		var base := body_font()
		if base == null:
			_fonts[key] = null
		else:
			var v := FontVariation.new()
			v.base_font = base
			v.variation_embolden = embolden
			if skew != 0.0:
				v.variation_transform = Transform2D(Vector2(1, 0), Vector2(skew, 1), Vector2.ZERO)
			_fonts[key] = v
	return _fonts[key]


# ------------------------------------------------------------------ theme

static func get_theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	var body := body_font()
	if body:
		t.default_font = body
	t.default_font_size = 17
	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_outline_color", "Label", OUTLINE)
	t.set_constant("outline_size", "Label", 4)
	t.set_color("font_shadow_color", "Label", Color(0, 0, 0, 0.35))
	t.set_constant("shadow_offset_x", "Label", 0)
	t.set_constant("shadow_offset_y", "Label", 1)
	t.set_stylebox("panel", "PanelContainer", panel())
	t.set_stylebox("panel", "Panel", panel())
	# buttons: lacquer plates; hover lights the gilt and a jade inlay
	t.set_stylebox("normal", "Button", button_style("normal"))
	t.set_stylebox("hover", "Button", button_style("hover"))
	t.set_stylebox("pressed", "Button", button_style("pressed"))
	t.set_stylebox("hover_pressed", "Button", button_style("pressed"))
	t.set_stylebox("disabled", "Button", button_style("disabled"))
	var focus := StyleBoxFlat.new()
	focus.draw_center = false
	focus.border_color = Color(JADE, 0.85)
	focus.set_border_width_all(1)
	focus.set_corner_radius_all(5)
	focus.set_expand_margin_all(1)
	t.set_stylebox("focus", "Button", focus)
	t.set_color("font_color", "Button", TEXT)
	t.set_color("font_hover_color", "Button", Color(1, 0.92, 0.7))
	t.set_color("font_focus_color", "Button", Color(1, 0.92, 0.7))
	t.set_color("font_pressed_color", "Button", GOLD)
	t.set_color("font_hover_pressed_color", "Button", GOLD)
	t.set_color("font_disabled_color", "Button", Color(0.5, 0.5, 0.48))
	t.set_color("font_outline_color", "Button", OUTLINE)
	t.set_constant("outline_size", "Button", 3)
	t.set_font_size("font_size", "Button", 18)
	var disp := display_font()
	if disp:
		t.set_font("font", "Button", disp)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.01, 0.015, 0.02, 0.7)
	bg.border_color = Color(GOLD, 0.55)
	bg.set_border_width_all(1)
	bg.set_corner_radius_all(4)
	var fill := StyleBoxFlat.new()
	fill.bg_color = GOLD
	fill.set_corner_radius_all(4)
	t.set_stylebox("background", "ProgressBar", bg)
	t.set_stylebox("fill", "ProgressBar", fill)
	t.set_color("font_color", "RichTextLabel", TEXT)
	t.set_color("default_color", "RichTextLabel", TEXT)
	t.set_color("font_outline_color", "RichTextLabel", OUTLINE)
	if body:
		t.set_font("normal_font", "RichTextLabel", body)
		t.set_font("italics_font", "RichTextLabel", _variant("italic", 0.0, 0.2))
		t.set_font("bold_font", "RichTextLabel", _variant("bold", 0.7, 0.0))
		t.set_font("bold_italics_font", "RichTextLabel", _variant("bold_italic", 0.7, 0.2))
	# tooltips and scroll bars in the same palette
	t.set_stylebox("panel", "TooltipPanel", flat_panel(Color(0.03, 0.04, 0.05, 0.94), Color(GOLD, 0.7), 4))
	t.set_color("font_color", "TooltipLabel", TEXT)
	t.set_font_size("font_size", "TooltipLabel", 14)
	var track := StyleBoxFlat.new()
	track.bg_color = Color(0, 0, 0, 0.35)
	track.set_corner_radius_all(3)
	track.content_margin_left = 3
	track.content_margin_right = 3
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(GOLD, 0.7)
	grab.set_corner_radius_all(3)
	var grab_hi := grab.duplicate()
	grab_hi.bg_color = GOLD
	t.set_stylebox("scroll", "VScrollBar", track)
	t.set_stylebox("grabber", "VScrollBar", grab)
	t.set_stylebox("grabber_highlight", "VScrollBar", grab_hi)
	t.set_stylebox("grabber_pressed", "VScrollBar", grab_hi)
	_theme = t
	return t


## A label in the house style. Sizes >= DISPLAY_FROM use the display face.
static func label(text: String, size := 18, color := TEXT, outline := 4) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_constant_override("outline_size", outline)
	if size >= DISPLAY_FROM and display_font():
		l.add_theme_font_override("font", display_font())
	return l


## A label that always uses the display face (for small-caps style headings).
static func title_label(text: String, size := 18, color := GOLD, outline := 4) -> Label:
	var l := label(text, size, color, outline)
	if display_font():
		l.add_theme_font_override("font", display_font())
	return l


## A plain ProgressBar in the palette (loading screen, simple meters).
static func bar(color: Color, w := 240.0, h := 12.0) -> ProgressBar:
	var p := ProgressBar.new()
	p.custom_minimum_size = Vector2(w, h)
	p.show_percentage = false
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	fill.set_corner_radius_all(int(minf(h * 0.5, 4.0)))
	fill.border_color = color.lightened(0.35)
	fill.border_width_top = 1 if h >= 6.0 else 0
	p.add_theme_stylebox_override("fill", fill)
	p.max_value = 1.0
	p.value = 1.0
	return p

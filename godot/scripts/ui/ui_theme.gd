class_name UiTheme
extends RefCounted
## The game's UI look: dark lacquer panels with thin gold borders and parchment text.

const GOLD := Color(0.86, 0.72, 0.42)
const INK := Color(0.06, 0.07, 0.1, 0.82)
const TEXT := Color(0.96, 0.93, 0.85)
const MUTED := Color(0.78, 0.74, 0.66)
const JADE := Color(0.45, 0.9, 0.78)
const CRIMSON := Color(0.86, 0.22, 0.2)

static var _theme: Theme


static func panel(bg := INK, border := GOLD, radius := 6, border_w := 1) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(border_w)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 14
	s.content_margin_right = 14
	s.content_margin_top = 10
	s.content_margin_bottom = 10
	s.shadow_color = Color(0, 0, 0, 0.35)
	s.shadow_size = 6
	return s


static func get_theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font_size = 18
	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_outline_color", "Label", Color(0.03, 0.03, 0.06))
	t.set_constant("outline_size", "Label", 4)
	t.set_stylebox("panel", "PanelContainer", panel())
	t.set_stylebox("panel", "Panel", panel())
	var b := panel(Color(0.1, 0.1, 0.14, 0.9), Color(GOLD, 0.6), 4)
	var bh := panel(Color(0.2, 0.17, 0.12, 0.95), GOLD, 4)
	var bp := panel(Color(0.3, 0.24, 0.12, 0.95), GOLD, 4)
	t.set_stylebox("normal", "Button", b)
	t.set_stylebox("hover", "Button", bh)
	t.set_stylebox("pressed", "Button", bp)
	t.set_stylebox("focus", "Button", bh)
	t.set_stylebox("disabled", "Button", panel(Color(0.08, 0.08, 0.1, 0.6), Color(0.4, 0.4, 0.4, 0.4), 4))
	t.set_color("font_color", "Button", TEXT)
	t.set_color("font_hover_color", "Button", Color(1, 0.92, 0.7))
	t.set_color("font_disabled_color", "Button", Color(0.5, 0.5, 0.5))
	t.set_font_size("font_size", "Button", 20)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0, 0, 0, 0.55)
	bg.set_corner_radius_all(3)
	var fill := StyleBoxFlat.new()
	fill.bg_color = GOLD
	fill.set_corner_radius_all(3)
	t.set_stylebox("background", "ProgressBar", bg)
	t.set_stylebox("fill", "ProgressBar", fill)
	t.set_color("font_color", "RichTextLabel", TEXT)
	t.set_color("default_color", "RichTextLabel", TEXT)
	_theme = t
	return t


static func label(text: String, size := 18, color := TEXT, outline := 4) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_constant_override("outline_size", outline)
	return l


static func bar(color: Color, w := 240.0, h := 12.0) -> ProgressBar:
	var p := ProgressBar.new()
	p.custom_minimum_size = Vector2(w, h)
	p.show_percentage = false
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	fill.set_corner_radius_all(3)
	p.add_theme_stylebox_override("fill", fill)
	p.max_value = 1.0
	p.value = 1.0
	return p

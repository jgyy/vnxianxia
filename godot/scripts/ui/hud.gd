extends CanvasLayer
## In-game HUD: vitality / qi / cultivation gauges, the quest scroll, the
## horizon compass with the objective marker, interact prompt, toasts, boss
## bar, meditation ring, key hints, and the centre stage (map banner, volume
## title card, new-quest card).
##
## Art: res://ui/hud/ (blender/render_hud.py, described by hud_kit.json). All
## sizes here are logical px on the 1280x720 base canvas; the project's
## canvas_items stretch scales them to the window, and every element hangs off
## a screen edge through containers, so nothing is placed absolutely.

const M := 14.0  ## screen-edge margin
const TRACKER_W := 300.0
const TOAST_W := 300.0
const MAX_TOASTS := 4
const RING_SIZE := 96.0
const KEY_RE := "^(\\S{1,6})\\s{2,}(.+)$"

const STRIP_SHADER := """
shader_type canvas_item;
uniform float offset = 0.0;   // heading at the left edge, in turns
uniform float span = 0.3333;  // fraction of the dial visible
void fragment() {
	vec2 raw = vec2(offset + UV.x * span, UV.y);
	vec4 c = textureGrad(TEXTURE, vec2(fract(raw.x), raw.y), dFdx(raw), dFdy(raw));
	float edge = smoothstep(0.0, 0.14, UV.x) * smoothstep(1.0, 0.86, UV.x);
	COLOR = vec4(c.rgb, c.a * edge);
}
"""

var player: Node3D
var target_point := Vector3.INF

var _root: Control
var _damage: TextureRect
var _realm: Label
var _align: Label
var _hp: Gauge
var _qi: Gauge
var _xp: Gauge
var _tracker: PanelContainer
var _quest_chapter: Label
var _quest_title: Label
var _objective: Label
var _objective_icon: TextureRect
var _compass: Compass
var _prompt: PanelContainer
var _prompt_key: Label
var _prompt_chip: PanelContainer
var _prompt_text: Label
var _key_re := RegEx.new()
var _meditate: Control
var _ring: TextureProgressBar
var _ring_glow: TextureRect
var _thought: Label
var _thought_tween: Tween
var _toasts: VBoxContainer
var _boss: VBoxContainer
var _boss_bar: Gauge
var _boss_name: Label
var _stage: VBoxContainer
var _banner_box: Control
var _banner: Label
var _banner_sub: Label
var _title_box: VBoxContainer
var _title_card: Label
var _title_card_sub: Label
var _card: PanelContainer
var _card_head: Label
var _card_title: Label
var _card_text: Label
var _hints: HBoxContainer
var _stage_queue: Array = []
var _stage_busy := false
var _clock := 0.0
var _top_col: VBoxContainer
## a conversation (dialogue box or choice) holds the screen: toasts wait,
## overlapping HUD pieces fade out of its way
var _quiet := false
var _pending_toasts: Array = []


func _ready() -> void:
	layer = 5
	_key_re.compile(KEY_RE)
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UiTheme.get_theme()
	_root.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	add_child(_root)
	_build_damage()
	var frame := MarginContainer.new()
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["left", "right", "top", "bottom"]:
		frame.add_theme_constant_override("margin_" + side, int(M))
	_root.add_child(frame)
	_build_left(frame)
	_build_right(frame)
	_build_top(frame)
	_build_bottom()
	_build_stage()
	Game.changed.connect(refresh)
	refresh()


# ------------------------------------------------------------------ building

func _build_damage() -> void:
	# a red vignette rather than a flat full-screen tint
	var g := Gradient.new()
	g.set_color(0, Color(0.7, 0.0, 0.0, 0.0))
	g.set_color(1, Color(0.7, 0.02, 0.0, 0.85))
	g.add_point(0.55, Color(0.7, 0.0, 0.0, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.05, 1.05)
	gt.width = 256
	gt.height = 256
	_damage = TextureRect.new()
	_damage.texture = gt
	_damage.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_damage.stretch_mode = TextureRect.STRETCH_SCALE
	_damage.set_anchors_preset(Control.PRESET_FULL_RECT)
	_damage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_damage.modulate.a = 0.0
	_root.add_child(_damage)


func _col(parent: Control, align := BoxContainer.ALIGNMENT_BEGIN, sep := 8) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.alignment = align
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_theme_constant_override("separation", sep)
	parent.add_child(v)
	return v


func _build_left(frame: Control) -> void:
	var col := _col(frame)
	# vitals: realm, dao heart, then the three gauges
	var vit := PanelContainer.new()
	vit.add_theme_stylebox_override("panel", UiTheme.panel())
	vit.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	vit.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(vit)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 0)
	vit.add_child(vb)
	_realm = UiTheme.title_label("Mortal", 17, UiTheme.GOLD)
	_realm.mouse_filter = Control.MOUSE_FILTER_PASS
	vb.add_child(_realm)
	_align = UiTheme.label("Walker of the Middle Way", 13, UiTheme.MUTED, 3)
	_align.mouse_filter = Control.MOUSE_FILTER_PASS
	vb.add_child(_align)
	var gap := Control.new()
	gap.custom_minimum_size.y = 3
	vb.add_child(gap)
	_hp = Gauge.new("gauge_hp")
	_hp.ghost_tint = Color(1.0, 0.86, 0.6, 0.9)
	vb.add_child(_hp)
	_qi = Gauge.new("gauge_qi")
	_qi.glow_when_full = true
	_qi.glow_tint = Color(0.45, 0.75, 1.0)
	_qi.ghost_tint = Color(0.8, 0.92, 1.0, 0.8)
	vb.add_child(_qi)
	_xp = Gauge.new("gauge_xp")
	_xp.ghost_tint = Color(1, 1, 1, 0.0)
	vb.add_child(_xp)
	# toasts flow under the vitals (never a fixed y that the panel can outgrow)
	_toasts = VBoxContainer.new()
	_toasts.add_theme_constant_override("separation", 4)
	_toasts.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_toasts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(_toasts)
	var spacer := Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(spacer)
	# key hints, bottom left
	_hints = HBoxContainer.new()
	_hints.add_theme_constant_override("separation", 5)
	_hints.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_hints.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hints.modulate.a = 0.8
	col.add_child(_hints)
	for pair in [["WASD", "move"], ["Shift", "run"], ["Space", "leap"], ["E", "interact"], ["F", "strike"],
			["Q", "qi blast"], ["C", "meditate"], ["Tab", "switch"], ["J", "journal"], ["Esc", "menu"]]:
		_hints.add_child(_chip(pair[0], 12))
		var l := UiTheme.label(pair[1], 13, UiTheme.MUTED, 3)
		l.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		_hints.add_child(l)
		var sp := Control.new()
		sp.custom_minimum_size.x = 4
		_hints.add_child(sp)


func _build_right(frame: Control) -> void:
	var col := _col(frame)
	_tracker = PanelContainer.new()
	_tracker.add_theme_stylebox_override("panel", UiTheme.scroll_panel())
	_tracker.size_flags_horizontal = Control.SIZE_SHRINK_END
	_tracker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(_tracker)
	var inner_w := TRACKER_W - 50.0
	var qv := VBoxContainer.new()
	qv.add_theme_constant_override("separation", 2)
	_tracker.add_child(qv)
	_quest_chapter = UiTheme.label("", 13, UiTheme.MUTED, 3)
	_quest_chapter.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_quest_chapter.custom_minimum_size.x = inner_w
	qv.add_child(_quest_chapter)
	_quest_title = UiTheme.title_label("", 19, UiTheme.GOLD, 4)
	_quest_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_quest_title.custom_minimum_size.x = inner_w
	qv.add_child(_quest_title)
	qv.add_child(UiTheme.divider(inner_w * 0.8))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	qv.add_child(row)
	_objective_icon = UiTheme.icon("lotus", 0.9)
	_objective_icon.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	row.add_child(_objective_icon)
	_objective = UiTheme.label("", 15, UiTheme.TEXT, 3)
	_objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective.custom_minimum_size.x = inner_w - 24.0
	row.add_child(_objective)


func _build_top(frame: Control) -> void:
	var col := _col(frame, BoxContainer.ALIGNMENT_BEGIN, 4)
	_top_col = col
	_compass = Compass.new()
	_compass.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(_compass)
	_boss = VBoxContainer.new()
	_boss.add_theme_constant_override("separation", -4)
	_boss.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_boss.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_boss.visible = false
	col.add_child(_boss)
	_boss_name = UiTheme.title_label("", 18, Color(1, 0.84, 0.72), 5)
	_boss_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_boss.add_child(_boss_name)
	_boss_bar = Gauge.new("boss", 0.9)
	_boss_bar.ghost_tint = Color(1.0, 0.8, 0.55, 0.9)
	_boss.add_child(_boss_bar)
	# new-quest story card: flows under the compass (and the boss bar)
	_card = PanelContainer.new()
	_card.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.04, 0.05, 0.08, 0.86), UiTheme.GOLD, 8, 1))
	_card.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_card.modulate.a = 0.0
	_card.visible = false
	col.add_child(_card)
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 3)
	_card.add_child(cv)
	_card_head = UiTheme.label("", 13, UiTheme.MUTED, 3)
	_card_title = UiTheme.title_label("", 24, UiTheme.GOLD, 5)
	_card_text = UiTheme.label("", 15, UiTheme.TEXT, 3)
	_card_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_card_text.custom_minimum_size.x = 500
	for l in [_card_head, _card_title]:
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cv.add_child(l)
	cv.add_child(UiTheme.divider(300))
	_card_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	cv.add_child(_card_text)


func _build_bottom() -> void:
	# thought, meditation ring and interact prompt stack up from above the
	# dialogue region at the bottom centre
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_END
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_theme_constant_override("separation", 10)
	col.anchor_left = 0.5
	col.anchor_right = 0.5
	col.anchor_top = 1.0
	col.anchor_bottom = 1.0
	col.offset_left = -380
	col.offset_right = 380
	col.offset_top = -420
	col.offset_bottom = -128
	_root.add_child(col)
	_thought = UiTheme.label("", 17, Color(0.88, 0.85, 0.76), 4)
	_thought.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_thought.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_thought.custom_minimum_size.x = 640
	_thought.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_thought.add_theme_font_override("font", UiTheme.get_theme().get_font("italics_font", "RichTextLabel"))
	_thought.modulate.a = 0.0
	col.add_child(_thought)
	_meditate = Control.new()
	_meditate.custom_minimum_size = Vector2(RING_SIZE, RING_SIZE)
	_meditate.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_meditate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_meditate.visible = false
	col.add_child(_meditate)
	var ring := UiTheme.kit_item("ring")
	var k := RING_SIZE / maxf(UiTheme.v2(ring.get("size", [112, 112])).x, 1.0) / UiTheme.kit_scale()
	_ring = TextureProgressBar.new()
	_ring.texture_under = UiTheme.hud_tex(ring.get("under", ""))
	_ring.texture_progress = UiTheme.hud_tex(ring.get("fill", ""))
	_ring.texture_over = UiTheme.hud_tex(ring.get("frame", ""))
	_ring.fill_mode = TextureProgressBar.FILL_CLOCKWISE
	_ring.max_value = 1.0
	_ring.step = 0.0
	_ring.scale = Vector2(k, k)
	_ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_meditate.add_child(_ring)
	_ring_glow = _additive(UiTheme.hud_tex(ring.get("glow", "")), Color(0.5, 1.0, 0.8))
	_ring_glow.position = Vector2.ZERO
	_ring_glow.size = Vector2(RING_SIZE, RING_SIZE)
	_meditate.add_child(_ring_glow)
	_prompt = PanelContainer.new()
	_prompt.add_theme_stylebox_override("panel", UiTheme.kit_box("prompt"))
	_prompt.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_prompt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt.visible = false
	col.add_child(_prompt)
	var pr := HBoxContainer.new()
	pr.add_theme_constant_override("separation", 8)
	_prompt.add_child(pr)
	_prompt_chip = _chip("E", 15)
	_prompt_key = _prompt_chip.get_child(0)
	pr.add_child(_prompt_chip)
	_prompt_text = UiTheme.label("", 17, Color(1, 0.95, 0.82), 4)
	_prompt_text.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	pr.add_child(_prompt_text)


func _build_stage() -> void:
	# centre stage, a quarter of the way down: map banner or volume title card
	_stage = VBoxContainer.new()
	_stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stage.anchor_left = 0.5
	_stage.anchor_right = 0.5
	_stage.anchor_top = 0.27
	_stage.anchor_bottom = 0.27
	_stage.offset_left = -400
	_stage.offset_right = 400
	_stage.grow_vertical = Control.GROW_DIRECTION_BOTH
	_stage.alignment = BoxContainer.ALIGNMENT_CENTER
	_root.add_child(_stage)
	_banner_box = Control.new()
	_banner_box.custom_minimum_size = Vector2(640, 98)  # clear of the toast column (x <= 314)
	_banner_box.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_banner_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_banner_box.modulate.a = 0.0
	_banner_box.visible = false
	_stage.add_child(_banner_box)
	var brush := TextureRect.new()
	brush.texture = UiTheme.hud_tex("banner.png")
	brush.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	brush.stretch_mode = TextureRect.STRETCH_SCALE
	brush.set_anchors_preset(Control.PRESET_FULL_RECT)
	brush.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_banner_box.add_child(brush)
	var bv := VBoxContainer.new()
	bv.set_anchors_preset(Control.PRESET_FULL_RECT)
	bv.alignment = BoxContainer.ALIGNMENT_CENTER
	bv.add_theme_constant_override("separation", -2)
	bv.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_banner_box.add_child(bv)
	_banner = UiTheme.title_label("", 34, UiTheme.GOLD, 6)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bv.add_child(_banner)
	_banner_sub = UiTheme.label("", 16, UiTheme.TEXT, 4)
	_banner_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	bv.add_child(_banner_sub)
	_title_box = VBoxContainer.new()
	_title_box.add_theme_constant_override("separation", 2)
	_title_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_title_box.modulate.a = 0.0
	_title_box.visible = false
	_stage.add_child(_title_box)
	_title_card = UiTheme.title_label("", 50, UiTheme.GOLD, 8)
	_title_card.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title_card.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title_card.custom_minimum_size.x = 800
	_title_box.add_child(_title_card)
	_title_box.add_child(UiTheme.divider(360))
	_title_card_sub = UiTheme.label("", 21, UiTheme.TEXT, 5)
	_title_card_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title_box.add_child(_title_card_sub)


## A keycap chip with ``key`` on it.
func _chip(key: String, font_size := 13) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UiTheme.kit_box("chip"))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var l := UiTheme.title_label(key, font_size, Color(0.95, 0.9, 0.75), 3)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.custom_minimum_size.x = 8
	p.add_child(l)
	return p


static func _additive(tex: Texture2D, tint: Color) -> TextureRect:
	var t := TextureRect.new()
	t.texture = tex
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_SCALE
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	t.material = m
	t.self_modulate = tint
	t.modulate.a = 0.0
	return t


# ------------------------------------------------------------------ API

func refresh() -> void:
	_realm.text = Game.realm_label()
	_align.text = Game.alignment_name()
	var tip := "%s\nDao Heart: %s\nBearing %+d  ·  Dao %+d" % [Game.realm_label(), Game.alignment_name(), Game.law, Game.good]
	_realm.tooltip_text = tip
	_align.tooltip_text = tip
	_xp.set_value(float(Game.xp % Game.XP_PER_REALM) / Game.XP_PER_REALM)
	var q := Game.quest()
	if q.is_empty():
		_quest_chapter.text = "The saga is complete"
		_quest_title.text = "Immortal Ascension"
		_objective.text = "Wander the realms freely."
		return
	_quest_chapter.text = "%s\n%s   ·   Quest %d / %d" % [
		Story.volume_label(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter)), int(q.number), Story.quests.size()]
	_quest_title.text = q.title


func set_objective(text: String) -> void:
	if _objective.text == text:
		return
	_objective.text = text
	# a brief flare so the change is noticed
	_objective.modulate = Color(1.6, 1.4, 0.9)
	var tw := create_tween()
	tw.tween_property(_objective, "modulate", Color.WHITE, 0.8)


func set_vitals(hp: float, max_hp: float, qi: float, max_qi: float) -> void:
	_hp.set_value(hp / maxf(max_hp, 0.001), true)
	_qi.set_value(qi / maxf(max_qi, 0.001), true)


func set_hp(hp: float, max_hp: float) -> void:
	var before := _hp.target
	_hp.set_value(hp / maxf(max_hp, 0.001))
	if _hp.target < before - 0.001:
		_damage.modulate.a = 0.55
		create_tween().tween_property(_damage, "modulate:a", 0.0, 0.5)


func set_qi(qi: float, max_qi: float) -> void:
	_qi.set_value(qi / maxf(max_qi, 0.001))


func set_prompt(text: String) -> void:
	_prompt.visible = text != ""
	if text == "":
		return
	var m := _key_re.search(text)
	_prompt_chip.visible = m != null
	if m:
		_prompt_key.text = m.get_string(1)
		_prompt_text.text = m.get_string(2)
	else:
		_prompt_text.text = text


func set_meditation(value: float) -> void:
	_meditate.visible = value >= 0.0
	_ring.value = clampf(value, 0.0, 1.0)


func toast(text: String, color := UiTheme.TEXT, seconds := 4.0) -> void:
	if _quiet or _conversation_up():
		# raised during a conversation: shown once it is over, not under the box
		_pending_toasts.append([text, color, seconds])
		return
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UiTheme.kit_box("toast"))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	var l := UiTheme.label(text, 15, color, 3)
	var font := l.get_theme_font("font")
	var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x if font else 200.0
	l.custom_minimum_size.x = minf(w + 2.0, TOAST_W - 47.0)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	p.add_child(l)
	_toasts.add_child(p)
	p.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(p, "modulate:a", 1.0, 0.25)
	tw.tween_interval(seconds)
	tw.tween_property(p, "modulate:a", 0.0, 0.6)
	tw.tween_callback(p.queue_free)
	p.set_meta("tween", tw)
	# drop the oldest (killing its tween first, so it never calls into a freed node)
	while _toasts.get_child_count() > MAX_TOASTS:
		var old := _toasts.get_child(0)
		var otw: Tween = old.get_meta("tween", null)
		if otw:
			otw.kill()
		_toasts.remove_child(old)
		old.queue_free()


## Present a newly begun quest: its place in the saga, title and story setup.
## Queued behind any banner / title card so the centre never shows two at once.
func quest_card(q: Dictionary, seconds := 6.0) -> void:
	if q.is_empty():
		return
	_enqueue({"kind": "card", "q": q, "seconds": seconds})


## Show a centred banner. Banners queue, so a breakthrough, a chapter's end
## and a new volume's title each get their moment instead of overwriting.
func banner(title: String, sub := "", seconds := 3.0) -> void:
	_enqueue({"kind": "banner", "title": title, "sub": sub, "seconds": seconds})


## A large title card (a new volume begins): fades in over the game after
## ``delay`` seconds (or after whatever is on the centre stage, if later).
func title_card(title: String, sub := "", seconds := 5.0, delay := 0.0) -> void:
	_enqueue({"kind": "title", "title": title, "sub": sub, "seconds": seconds, "at": _clock + delay})


## A fleeting first-person thought (the roaming monologue). Never interrupts
## anything; simply fades in over the world, then out again.
func say_thought(text: String) -> void:
	if _thought_tween:
		_thought_tween.kill()
	_thought.text = "“" + text + "”"
	_thought_tween = create_tween()
	_thought_tween.tween_property(_thought, "modulate:a", 1.0, 0.5)
	_thought_tween.tween_interval(4.2)
	_thought_tween.tween_property(_thought, "modulate:a", 0.0, 1.2)


func show_boss(enemy_name: String, frac: float) -> void:
	var was := _boss.visible
	_boss.visible = frac >= 0.0
	_boss_name.text = enemy_name
	_boss_bar.set_value(maxf(frac, 0.0), not was)


func show_gameplay(on: bool) -> void:
	_root.visible = on


# ------------------------------------------------------------------ centre stage

func _enqueue(item: Dictionary) -> void:
	if not item.has("at"):
		item["at"] = _clock
	_stage_queue.append(item)
	if not _stage_busy:
		_next_stage()


func _next_stage() -> void:
	if _stage_queue.is_empty():
		_stage_busy = false
		return
	_stage_busy = true
	var it: Dictionary = _stage_queue.pop_front()
	var wait := maxf(0.0, float(it.at) - _clock)
	if wait > 0.0 and not Game.fast:
		get_tree().create_timer(wait, false).timeout.connect(_show_stage.bind(it))
	else:
		_show_stage(it)


func _show_stage(it: Dictionary) -> void:
	var seconds: float = it.seconds
	var node: Control
	var fade_in := 0.6
	var fade_out := 1.0
	match it.kind:
		"banner":
			_banner.text = it.title
			_banner_sub.text = it.sub
			_banner_sub.visible = it.sub != ""
			node = _banner_box
		"title":
			_title_card.text = it.title
			_title_card_sub.text = it.sub
			node = _title_box
			fade_in = 1.2
			fade_out = 1.4
		_:
			var q: Dictionary = it.q
			_card_head.text = "Volume %s  ·  %s   ·   Quest %d" % [
				Story.roman(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter)), int(q.number)]
			_card_title.text = q.title
			_card_text.text = Story.fill(q.summary)
			node = _card
			fade_in = 0.5
			fade_out = 0.8
	node.visible = true
	node.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(node, "modulate:a", 1.0, fade_in)
	tw.tween_interval(seconds)
	tw.tween_property(node, "modulate:a", 0.0, fade_out)
	tw.tween_callback(func(): node.visible = false)
	var done := create_tween()
	done.tween_interval(seconds + fade_in + fade_out + 0.2 if not Game.fast else 0.0)
	done.tween_callback(_next_stage)


# ------------------------------------------------------------------ per frame

func _process(delta: float) -> void:
	_clock += delta
	var dlg: Variant = get_parent().get("dialogue") if get_parent() else null
	var talking: bool = dlg is Node and dlg.get("active")
	_set_quiet(_conversation_up())
	_hints.visible = not talking
	_fade_for_dialogue(dlg if talking else null, delta)
	if _meditate.visible:
		_ring_glow.modulate.a = 0.35 + 0.25 * sin(_clock * 2.4)
	var cam := get_viewport().get_camera_3d()
	if player == null or cam == null:
		_compass.visible = false
		return
	_compass.visible = true
	var f := -cam.global_basis.z
	var heading := atan2(f.x, -f.z)
	_compass.set_heading(heading)
	if target_point == Vector3.INF:
		_compass.set_target(NAN, 0.0)
		return
	var to := target_point - player.global_position
	var flat := Vector2(to.x, to.z)
	if flat.length() <= 2.5:
		_compass.set_target(NAN, 0.0)
		return
	_compass.set_target(wrapf(atan2(to.x, -to.z) - heading, -PI, PI), flat.length())


# ------------------------------------------------------------------ conversations

## Is a conversation (the dialogue box, a choice, or the scene around them) up?
func _conversation_up() -> bool:
	var g := get_parent()
	if g == null:
		return false
	var dlg: Variant = g.get("dialogue")
	var depth: Variant = g.get("_scene_depth")
	return (dlg is Node and dlg.get("active")) or (depth is int and depth > 0)


func _set_quiet(on: bool) -> void:
	if on == _quiet:
		return
	_quiet = on
	if not on and not _pending_toasts.is_empty():
		var waiting := _pending_toasts.duplicate()
		_pending_toasts.clear()
		for t in waiting:
			toast(t[0], t[1], t[2])


## While the dialogue box is up, the toast column fades away and the centre
## stage (banner / title card) and the top column (boss bar, quest card) fade
## wherever they would overlap the box; all fade back afterwards.
func _fade_for_dialogue(dlg: Variant, delta: float) -> void:
	var box := Rect2()
	if dlg is Node and dlg.has_method("panel_rect"):
		box = dlg.panel_rect().grow(6.0)
	var rate := delta / 0.25
	_toasts.modulate.a = move_toward(_toasts.modulate.a, 0.0 if _quiet else 1.0, rate)
	var top_hit := false
	for n in [_boss, _card]:
		if n.visible and box.has_area() and n.get_global_rect().intersects(box):
			top_hit = true
	_top_col.modulate.a = move_toward(_top_col.modulate.a, 0.0 if top_hit else 1.0, rate)
	var stage_hit := false
	for n in _stage.get_children():
		if n is Control and n.visible and box.has_area() and n.get_global_rect().intersects(box):
			stage_hit = true
	_stage.modulate.a = move_toward(_stage.modulate.a, 0.0 if stage_hit else 1.0, rate)


# ------------------------------------------------------------------ widgets

## A carved gauge: trough, a trailing "ghost" bar, the liquid fill (eased),
## a spark on the moving edge, the frame on top, and an optional glow when full.
class Gauge:
	extends Control

	var item: Dictionary
	var target := 1.0
	var shown := 1.0
	var ghost := 1.0
	var glow_when_full := false
	var glow_tint := Color.WHITE
	var ghost_tint := Color(1, 0.9, 0.7, 0.85):
		set(v):
			ghost_tint = v
			if _ghost:
				_ghost.tint_progress = v
	var _hold := 0.0
	var _t := 0.0
	var _fill: TextureProgressBar
	var _ghost: TextureProgressBar
	var _spark: TextureRect
	var _glow: TextureRect
	var _win: Rect2

	func _init(kit_name: String, k := 1.0) -> void:
		item = UiTheme.kit_item(kit_name)
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		var sz := UiTheme.v2(item.get("size", [240, 20])) * k
		custom_minimum_size = sz
		var w := UiTheme.rect(item.get("window", [0, 0, 240, 20]))
		_win = Rect2(w.position * k, w.size * k)
		_add_rect(UiTheme.hud_tex(item.get("trough", "")), _win)
		_ghost = _bar(UiTheme.hud_tex(item.get("fill", "")))
		_ghost.tint_progress = ghost_tint
		_fill = _bar(UiTheme.hud_tex(item.get("fill", "")))
		_spark = hud_additive(UiTheme.hud_tex("spark.png"), Color(1, 0.95, 0.85))
		_spark.size = Vector2(_win.size.y * 0.8, _win.size.y * 1.6)
		add_child(_spark)
		_add_rect(UiTheme.hud_tex(item.get("frame", "")), Rect2(Vector2.ZERO, sz))
		if item.has("glow"):
			var g := UiTheme.rect(item.get("glow_rect", [0, 0, sz.x, sz.y]))
			_glow = hud_additive(UiTheme.hud_tex(item.glow), Color.WHITE)
			_glow.position = g.position * k
			_glow.size = g.size * k
			add_child(_glow)

	static func hud_additive(tex: Texture2D, tint: Color) -> TextureRect:
		var t := TextureRect.new()
		t.texture = tex
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_SCALE
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		t.material = m
		t.self_modulate = tint
		t.modulate.a = 0.0
		return t

	func _add_rect(tex: Texture2D, r: Rect2) -> void:
		var t := TextureRect.new()
		t.texture = tex
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_SCALE
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		t.position = r.position
		t.size = r.size
		add_child(t)

	func _bar(tex: Texture2D) -> TextureProgressBar:
		var b := TextureProgressBar.new()
		b.texture_progress = tex
		b.nine_patch_stretch = true  # margins 0: the whole texture scales to the window
		b.max_value = 1.0
		b.step = 0.0
		b.value = 1.0
		b.position = _win.position
		b.size = _win.size
		b.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(b)
		return b

	func set_value(v: float, instant := false) -> void:
		v = clampf(v, 0.0, 1.0) if not is_nan(v) else 0.0
		if v < target - 0.0005:
			_hold = 0.45  # the ghost lingers, then drains
		target = v
		if instant:
			shown = v
			ghost = v
			_apply()

	func _process(delta: float) -> void:
		_t += delta
		var moving := absf(shown - target) > 0.002
		shown = lerpf(shown, target, 1.0 - exp(-delta * 9.0)) if moving else target
		if ghost < shown:
			ghost = shown
		elif _hold > 0.0:
			_hold -= delta
		else:
			ghost = maxf(shown, ghost - delta * 0.55)
		_apply()
		_spark.modulate.a = move_toward(_spark.modulate.a, 0.9 if moving and shown > 0.01 else 0.0, delta * 6.0)
		if _glow:
			var on := glow_when_full and target >= 0.999
			var a := (0.45 + 0.3 * sin(_t * 3.0)) if on else 0.0
			_glow.modulate.a = move_toward(_glow.modulate.a, a, delta * 2.0)
			_glow.self_modulate = glow_tint

	func _apply() -> void:
		_fill.value = shown
		_ghost.value = ghost
		_spark.position = Vector2(_win.position.x + _win.size.x * shown - _spark.size.x * 0.5,
			_win.position.y + (_win.size.y - _spark.size.y) * 0.5)


## The horizon compass: a bronze strip whose dial scrolls with the camera's
## heading (north = -Z), with the objective marker (or an edge chevron when
## the objective is behind) and its distance.
class Compass:
	extends Control

	var item: Dictionary
	var _strip: TextureRect
	var _mat: ShaderMaterial
	var _marker: TextureRect
	var _left: TextureRect
	var _right: TextureRect
	var _dist: Label
	var _win: Rect2
	var _span := 120.0

	func _init() -> void:
		item = UiTheme.kit_item("compass")
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		var sz := UiTheme.v2(item.get("size", [320, 44]))
		custom_minimum_size = Vector2(sz.x, sz.y + 16)
		_win = UiTheme.rect(item.get("window", [32, 9, 256, 26]))
		_span = float(item.get("span_deg", 120))
		_rect(UiTheme.hud_tex(item.get("trough", "")), _win)
		_strip = _rect(UiTheme.hud_tex(item.get("strip", "")), _win)
		_strip.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		var sh := Shader.new()
		sh.code = STRIP_SHADER
		_mat = ShaderMaterial.new()
		_mat.shader = sh
		_mat.set_shader_parameter("span", _span / 360.0)
		_strip.material = _mat
		_rect(UiTheme.hud_tex(item.get("frame", "")), Rect2(Vector2.ZERO, sz))
		var ms := UiTheme.v2(UiTheme.kit_item("marker").get("size", [20, 26])) * 0.8
		_marker = _rect(UiTheme.hud_tex("marker.png"), Rect2(Vector2.ZERO, ms))
		var es := UiTheme.v2(UiTheme.kit_item("marker_edge").get("size", [12, 16]))
		_right = _rect(UiTheme.hud_tex("marker_edge.png"), Rect2(Vector2(_win.end.x + 2, _win.position.y + (_win.size.y - es.y) / 2), es))
		_left = _rect(UiTheme.hud_tex("marker_edge.png"), Rect2(Vector2(_win.position.x - 2 - es.x, _win.position.y + (_win.size.y - es.y) / 2), es))
		_left.flip_h = true
		_dist = UiTheme.label("", 13, UiTheme.TEXT, 3)
		_dist.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_dist.size = Vector2(80, 16)
		_dist.position = Vector2(sz.x / 2 - 40, sz.y - 3)
		add_child(_dist)
		set_target(NAN, 0.0)

	func _rect(tex: Texture2D, r: Rect2) -> TextureRect:
		var t := TextureRect.new()
		t.texture = tex
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_SCALE
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		t.position = r.position
		t.size = r.size
		add_child(t)
		return t

	## ``yaw``: camera heading in radians, 0 = north (-Z), clockwise (east = +X).
	func set_heading(yaw: float) -> void:
		var deg := fposmod(rad_to_deg(yaw), 360.0)
		_mat.set_shader_parameter("offset", fposmod(deg - _span * 0.5, 360.0) / 360.0)

	## ``rel``: bearing of the objective relative to the heading (radians,
	## -PI..PI, NAN = none); ``dist`` in metres.
	func set_target(rel: float, dist: float) -> void:
		var has := not is_nan(rel)
		_dist.visible = has
		if not has:
			_marker.visible = false
			_left.visible = false
			_right.visible = false
			return
		var d := rad_to_deg(rel)
		var half := _span * 0.5
		var inside := absf(d) <= half - 4.0
		_marker.visible = inside
		_left.visible = not inside and d < 0.0
		_right.visible = not inside and d > 0.0
		var cx := _win.position.x + _win.size.x * 0.5
		var x := cx + clampf(d / _span, -0.5, 0.5) * _win.size.x
		if inside:
			_marker.position = Vector2(x - _marker.size.x * 0.5, _win.position.y - 4.0)
		else:
			x = (_left.position.x + _left.size.x * 0.5) if d < 0.0 else (_right.position.x + _right.size.x * 0.5)
		_dist.text = "%d m" % int(dist)
		_dist.position.x = clampf(x - _dist.size.x * 0.5, 0.0, size.x - _dist.size.x)

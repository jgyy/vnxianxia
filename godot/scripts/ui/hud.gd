extends CanvasLayer
## In-game HUD: vitals, cultivation, quest tracker, compass, prompts, toasts,
## boss bar and the map banner.

var player: Node3D
var target_point := Vector3.INF
var _hp: ProgressBar
var _qi: ProgressBar
var _xp: ProgressBar
var _realm: Label
var _align: Label
var _quest_chapter: Label
var _quest_title: Label
var _objective: Label
var _prompt: Label
var _toasts: VBoxContainer
var _boss: VBoxContainer
var _boss_bar: ProgressBar
var _boss_name: Label
var _banner: Label
var _banner_sub: Label
var _compass: Control
var _arrow: Control
var _dist: Label
var _meditate: ProgressBar
var _damage: ColorRect
var _root: Control
var _card: PanelContainer
var _card_head: Label
var _card_title: Label
var _card_text: Label
var _banner_queue: Array = []
var _banner_busy := false
var _title_card: Label
var _title_card_sub: Label
var _thought: Label
var _thought_tween: Tween


func _ready() -> void:
	layer = 5
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.theme = UiTheme.get_theme()
	add_child(_root)
	_damage = ColorRect.new()
	_damage.set_anchors_preset(Control.PRESET_FULL_RECT)
	_damage.color = Color(0.7, 0.0, 0.0, 0.0)
	_damage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_damage)
	# vitals (top left)
	var vit := PanelContainer.new()
	vit.position = Vector2(16, 14)
	vit.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(vit)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 5)
	vit.add_child(vb)
	_realm = UiTheme.label("Mortal", 17, UiTheme.GOLD)
	_realm.mouse_filter = Control.MOUSE_FILTER_PASS
	vb.add_child(_realm)
	_align = UiTheme.label("Walker of the Middle Way", 13, UiTheme.MUTED, 3)
	_align.mouse_filter = Control.MOUSE_FILTER_PASS
	vb.add_child(_align)
	_hp = _labelled_bar(vb, "Vitality", UiTheme.CRIMSON)
	_qi = _labelled_bar(vb, "Qi", Color(0.35, 0.75, 1.0))
	_xp = _labelled_bar(vb, "Cultivation", UiTheme.JADE, 7.0)
	# quest tracker (top right)
	var qp := PanelContainer.new()
	qp.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	qp.position = Vector2(-376, 14)
	qp.custom_minimum_size = Vector2(360, 0)
	qp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(qp)
	var qv := VBoxContainer.new()
	qp.add_child(qv)
	_quest_chapter = UiTheme.label("", 14, UiTheme.MUTED)
	_quest_chapter.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_quest_title = UiTheme.label("", 21, UiTheme.GOLD)
	_quest_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective = UiTheme.label("", 17)
	_objective.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	for l in [_quest_chapter, _quest_title, _objective]:
		l.custom_minimum_size.x = 330
		qv.add_child(l)
	# compass (top centre)
	_compass = VBoxContainer.new()
	_compass.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_compass.position = Vector2(-40, 10)
	_compass.custom_minimum_size = Vector2(80, 0)
	_compass.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_compass)
	_arrow = Arrow.new()
	_arrow.pivot_offset = Vector2(40, 22)
	_arrow.custom_minimum_size = Vector2(80, 44)
	_dist = UiTheme.label("", 15, UiTheme.TEXT)
	_dist.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_compass.add_child(_arrow)
	_compass.add_child(_dist)
	# interaction prompt (lower centre)
	_prompt = UiTheme.label("", 21, Color(1, 0.95, 0.8), 6)
	_prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.position = Vector2(-300, -210)
	_prompt.custom_minimum_size = Vector2(600, 30)
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_root.add_child(_prompt)
	_meditate = UiTheme.bar(UiTheme.JADE, 300, 10)
	_meditate.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_meditate.position = Vector2(-150, -170)
	_meditate.visible = false
	_root.add_child(_meditate)
	# roaming monologue: a quiet, italic thought near the bottom of the screen
	_thought = UiTheme.label("", 18, Color(0.85, 0.82, 0.72), 4)
	_thought.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_thought.position = Vector2(-360, -260)
	_thought.custom_minimum_size = Vector2(720, 40)
	_thought.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_thought.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_thought.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_thought.modulate.a = 0.0
	_root.add_child(_thought)
	# toasts (left, under vitals)
	_toasts = VBoxContainer.new()
	_toasts.position = Vector2(16, 170)
	_toasts.add_theme_constant_override("separation", 6)
	_toasts.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_toasts)
	# boss bar (bottom centre)
	_boss = VBoxContainer.new()
	_boss.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_boss.position = Vector2(-320, -90)
	_boss.custom_minimum_size = Vector2(640, 0)
	_boss.visible = false
	_root.add_child(_boss)
	_boss_name = UiTheme.label("", 22, Color(1, 0.85, 0.75), 6)
	_boss_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_boss.add_child(_boss_name)
	_boss_bar = UiTheme.bar(Color(0.75, 0.1, 0.12), 640, 16)
	_boss.add_child(_boss_bar)
	# map banner
	_banner = UiTheme.label("", 44, UiTheme.GOLD, 8)
	_banner.set_anchors_preset(Control.PRESET_CENTER)
	_banner.position = Vector2(-500, -170)
	_banner.custom_minimum_size = Vector2(1000, 50)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.modulate.a = 0.0
	_root.add_child(_banner)
	_banner_sub = UiTheme.label("", 20, UiTheme.MUTED, 5)
	_banner_sub.set_anchors_preset(Control.PRESET_CENTER)
	_banner_sub.position = Vector2(-500, -112)
	_banner_sub.custom_minimum_size = Vector2(1000, 30)
	_banner_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner_sub.modulate.a = 0.0
	_root.add_child(_banner_sub)
	# volume title card (centre, above the banner)
	_title_card = UiTheme.label("", 60, UiTheme.GOLD, 10)
	_title_card.set_anchors_preset(Control.PRESET_CENTER)
	_title_card.position = Vector2(-600, -300)
	_title_card.custom_minimum_size = Vector2(1200, 70)
	_title_card.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title_card.modulate.a = 0.0
	_root.add_child(_title_card)
	_title_card_sub = UiTheme.label("", 26, UiTheme.TEXT, 6)
	_title_card_sub.set_anchors_preset(Control.PRESET_CENTER)
	_title_card_sub.position = Vector2(-600, -224)
	_title_card_sub.custom_minimum_size = Vector2(1200, 34)
	_title_card_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title_card_sub.modulate.a = 0.0
	_root.add_child(_title_card_sub)
	# new-quest story card (top centre)
	_card = PanelContainer.new()
	_card.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_card.position = Vector2(-330, 86)
	_card.custom_minimum_size = Vector2(660, 0)
	_card.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.04, 0.05, 0.08, 0.86), UiTheme.GOLD, 8, 1))
	_card.modulate.a = 0.0
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_card)
	var cv := VBoxContainer.new()
	_card.add_child(cv)
	_card_head = UiTheme.label("", 14, UiTheme.MUTED)
	_card_title = UiTheme.label("", 26, UiTheme.GOLD, 5)
	_card_text = UiTheme.label("", 17, UiTheme.TEXT)
	_card_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_card_text.custom_minimum_size.x = 630
	for l in [_card_head, _card_title, _card_text]:
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cv.add_child(l)
	var help := UiTheme.label("WASD move · Shift run · Space leap · E interact · F/LMB strike · Q qi blast · C meditate · Tab switch · J journal · Esc menu", 13, UiTheme.MUTED, 3)
	help.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	help.position = Vector2(16, -28)
	_root.add_child(help)
	Game.changed.connect(refresh)
	refresh()


func _labelled_bar(parent: Control, text: String, color: Color, h := 11.0) -> ProgressBar:
	var row := HBoxContainer.new()
	var l := UiTheme.label(text, 13, UiTheme.MUTED, 3)
	l.custom_minimum_size.x = 82
	row.add_child(l)
	var b := UiTheme.bar(color, 220, h)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(b)
	parent.add_child(row)
	return b


func refresh() -> void:
	_realm.text = Game.realm_label()
	_align.text = Game.alignment_name()
	var tip := "%s\nDao Heart: %s\nBearing %+d  ·  Dao %+d" % [Game.realm_label(), Game.alignment_name(), Game.law, Game.good]
	_realm.tooltip_text = tip
	_align.tooltip_text = tip
	_xp.value = float(Game.xp % Game.XP_PER_REALM) / Game.XP_PER_REALM
	var q := Game.quest()
	if q.is_empty():
		_quest_chapter.text = "The saga is complete"
		_quest_title.text = "Immortal Ascension"
		_objective.text = "Wander the realms freely."
		return
	_quest_chapter.text = "%s\n%s   —   Quest %d / %d" % [
		Story.volume_label(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter)), int(q.number), Story.quests.size()]
	_quest_title.text = q.title


func set_objective(text: String) -> void:
	_objective.text = "» " + text


func set_vitals(hp: float, max_hp: float, qi: float, max_qi: float) -> void:
	_hp.value = hp / max_hp
	_qi.value = qi / max_qi


func set_hp(hp: float, max_hp: float) -> void:
	var before := _hp.value
	_hp.value = hp / max_hp
	if _hp.value < before - 0.001:
		_damage.color.a = 0.25
		create_tween().tween_property(_damage, "color:a", 0.0, 0.4)


func set_qi(qi: float, max_qi: float) -> void:
	_qi.value = qi / max_qi


func set_prompt(text: String) -> void:
	_prompt.text = text


func set_meditation(value: float) -> void:
	_meditate.visible = value >= 0.0
	_meditate.value = maxf(value, 0.0)


func toast(text: String, color := UiTheme.TEXT, seconds := 4.0) -> void:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.05, 0.06, 0.09, 0.8), Color(color, 0.7)))
	var l := UiTheme.label(text, 17, color)
	p.add_child(l)
	_toasts.add_child(p)
	p.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(p, "modulate:a", 1.0, 0.25)
	tw.tween_interval(seconds)
	tw.tween_property(p, "modulate:a", 0.0, 0.6)
	tw.tween_callback(p.queue_free)
	while _toasts.get_child_count() > 5:
		_toasts.get_child(0).free()


## Present a newly begun quest: its place in the saga, title and story setup.
func quest_card(q: Dictionary, seconds := 6.0) -> void:
	if q.is_empty():
		return
	_card_head.text = "Volume %s  ·  %s   —   Quest %d" % [
		Story.roman(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter)), int(q.number)]
	_card_title.text = q.title
	_card_text.text = Story.fill(q.summary)
	var tw := create_tween()
	tw.tween_property(_card, "modulate:a", 1.0, 0.5)
	tw.tween_interval(seconds)
	tw.tween_property(_card, "modulate:a", 0.0, 0.8)


## Show a centred banner. Banners queue, so a breakthrough, a chapter's end
## and a new volume's title each get their moment instead of overwriting.
func banner(title: String, sub := "", seconds := 3.0) -> void:
	_banner_queue.append([title, sub, seconds])
	if not _banner_busy:
		_next_banner()


func _next_banner() -> void:
	if _banner_queue.is_empty():
		_banner_busy = false
		return
	_banner_busy = true
	var b: Array = _banner_queue.pop_front()
	_banner.text = b[0]
	_banner_sub.text = b[1]
	var seconds: float = b[2]
	for l in [_banner, _banner_sub]:
		var tw := create_tween()
		tw.tween_property(l, "modulate:a", 1.0, 0.6)
		tw.tween_interval(seconds)
		tw.tween_property(l, "modulate:a", 0.0, 1.0)
	var done := create_tween()
	done.tween_interval(seconds + 1.7 if not Game.fast else 0.0)
	done.tween_callback(_next_banner)


## A large title card (a new volume begins): letterbox-free, fades in over the game.
func title_card(title: String, sub := "", seconds := 5.0, delay := 0.0) -> void:
	_title_card.text = title
	_title_card_sub.text = sub
	for l in [_title_card, _title_card_sub]:
		l.modulate.a = 0.0
		var tw := create_tween()
		tw.tween_interval(delay)
		tw.tween_property(l, "modulate:a", 1.0, 1.2)
		tw.tween_interval(seconds)
		tw.tween_property(l, "modulate:a", 0.0, 1.4)


## A fleeting first-person thought (the roaming monologue). Never interrupts
## anything; simply fades in over the world, then out again.
func say_thought(text: String) -> void:
	if _thought_tween:
		_thought_tween.kill()
	_thought.text = "\"" + text + "\""
	_thought_tween = create_tween()
	_thought_tween.tween_property(_thought, "modulate:a", 1.0, 0.5)
	_thought_tween.tween_interval(4.2)
	_thought_tween.tween_property(_thought, "modulate:a", 0.0, 1.2)


func show_boss(enemy_name: String, frac: float) -> void:
	_boss.visible = frac >= 0.0
	_boss_name.text = enemy_name
	_boss_bar.value = maxf(frac, 0.0)


func show_gameplay(on: bool) -> void:
	_root.visible = on


func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if player == null or cam == null or target_point == Vector3.INF:
		_compass.visible = false
		return
	var to := target_point - player.global_position
	var flat := Vector2(to.x, to.z)
	_compass.visible = flat.length() > 2.5
	var f := -cam.global_basis.z
	var cam_yaw := atan2(f.x, -f.z)
	var tgt_yaw := atan2(to.x, -to.z)
	_arrow.rotation = wrapf(tgt_yaw - cam_yaw, -PI, PI)
	_dist.text = "%d m" % int(flat.length())


class Arrow:
	extends Control

	func _draw() -> void:
		var c := Vector2(40, 22)
		var pts := PackedVector2Array([c + Vector2(0, -18), c + Vector2(13, 14), c + Vector2(0, 7), c + Vector2(-13, 14)])
		draw_colored_polygon(pts, Color(0.05, 0.05, 0.08, 0.7))
		var inner := PackedVector2Array()
		for p in pts:
			inner.append(c + (p - c) * 0.78)
		draw_colored_polygon(inner, UiTheme.GOLD)

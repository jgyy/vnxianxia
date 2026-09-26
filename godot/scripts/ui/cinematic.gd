extends CanvasLayer
## Plays story cinematics: letterbox, title card, camera moves orbiting map
## markers, voiced subtitles and posed actors. Esc / Enter skips.

signal finished

var game: Node
var active := false
var _top: ColorRect
var _bottom: ColorRect
var _fade: ColorRect
var _title: Label
var _subtitle: Label
var _line: Label
var _speaker: Label
var _skip := false
var _cam: Camera3D


func _ready() -> void:
	layer = 15
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiTheme.get_theme()
	add_child(root)
	_top = _bar(root, Control.PRESET_TOP_WIDE)
	_bottom = _bar(root, Control.PRESET_BOTTOM_WIDE)
	_fade = ColorRect.new()
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.color = Color(0, 0, 0, 0)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_fade)
	_title = _centered(root, 56, UiTheme.GOLD, -60)
	_subtitle = _centered(root, 28, UiTheme.TEXT, 10)
	_speaker = UiTheme.label("", 20, UiTheme.GOLD, 5)
	_speaker.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_speaker.position = Vector2(-500, -84)
	_speaker.custom_minimum_size = Vector2(1000, 24)
	_speaker.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_speaker)
	_line = UiTheme.label("", 22, UiTheme.TEXT, 5)
	_line.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_line.position = Vector2(-520, -58)
	_line.custom_minimum_size = Vector2(1040, 50)
	_line.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root.add_child(_line)
	var skip := UiTheme.label("Esc  skip", 13, UiTheme.MUTED, 3)
	skip.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	skip.position = Vector2(-110, 16)
	root.add_child(skip)
	visible = false


func _bar(root: Control, preset: int) -> ColorRect:
	var r := ColorRect.new()
	r.set_anchors_preset(preset)
	r.color = Color.BLACK
	r.offset_top = 0.0
	r.offset_bottom = 0.0
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(r)
	return r


func _centered(root: Control, size: int, color: Color, y: float) -> Label:
	var l := UiTheme.label("", size, color, 8)
	l.set_anchors_preset(Control.PRESET_CENTER)
	l.position = Vector2(-600, y)
	l.custom_minimum_size = Vector2(1200, size + 10)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.modulate.a = 0.0
	root.add_child(l)
	return l


func _unhandled_input(event: InputEvent) -> void:
	if active and (event.is_action_pressed("pause") or (event is InputEventKey and event.pressed and event.keycode == KEY_ENTER)):
		_skip = true
		get_viewport().set_input_as_handled()


func _letterbox(on: bool, t := 0.6) -> void:
	var h := 90.0 if on else 0.0
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_top, "offset_bottom", h, t)
	tw.tween_property(_bottom, "offset_top", -h, t)


func play(cin_id: String) -> void:
	var cin: Dictionary = Story.cinematics.get(cin_id, {})
	if cin.is_empty():
		return
	active = true
	_skip = false
	visible = true
	var map: Node = game.map
	var player: Node3D = game.player
	player.controls_enabled = false
	player.stop_meditation()
	game.hud.show_gameplay(false)
	if cin.get("music"):
		Audio.play_music(cin.music)
	var temp: Array[Node] = []
	var hidden: Array[Node] = []
	for a in cin.get("actors", []):
		var pos: Vector3 = map.marker_position(a.marker)
		var face = map.marker_position(a.face) if a.get("face") else null
		if a.npc == "player":
			player.global_position = pos + Vector3.UP * 0.1
			player.velocity = Vector3.ZERO
			if face != null:
				var to: Vector3 = face - pos
				player.model_root.rotation.y = atan2(to.x, to.z)
			if player.anim and player.anim.has_animation(a.anim):
				player.anim.play(a.anim)
			continue
		var existing: Node = game.find_npc(a.npc)
		if existing:
			existing.visible = false
			hidden.append(existing)
		var n := Npc.create(a.npc)
		map.add_child(n)
		n.global_position = pos
		if face != null:
			var to2: Vector3 = face - pos
			n.rotation.y = atan2(to2.x, to2.z)
		n.play(a.anim)
		temp.append(n)
	for e in cin.get("enemies", []):
		for i in int(e.get("count", 1)):
			var en := Enemy.create(e.enemy, Story.world.bosses.has(e.enemy))
			en.process_mode = Node.PROCESS_MODE_DISABLED
			map.add_child(en)
			var base: Vector3 = map.marker_position(e.marker)
			en.global_position = base + Vector3(cos(i * 2.4) * 2.5 * mini(i, 1), 0, sin(i * 2.4) * 2.5 * mini(i, 1))
			en.remove_from_group("enemies")
			temp.append(en)
	_cam = Camera3D.new()
	_cam.fov = 50.0
	_cam.far = 3000.0
	map.add_child(_cam)
	_cam.make_current()
	if not Game.fast:
		_letterbox(true)
		if cin.get("title"):
			Audio.sfx("chapter_title", -2.0)
			await _card(cin.title, cin.get("subtitle", ""))
		for shot in cin.shots:
			if _skip:
				break
			await _shot(map, shot)
	Audio.stop_voice()
	_line.text = ""
	_speaker.text = ""
	for n in temp:
		n.queue_free()
	for n in hidden:
		n.visible = true
	_cam.queue_free()
	player.camera.make_current()
	if player.anim:
		player.anim.play("idle")
	_letterbox(false, 0.4)
	game.hud.show_gameplay(true)
	player.controls_enabled = true
	active = false
	visible = false
	finished.emit()


func _card(title: String, sub: String) -> void:
	_title.text = title
	_subtitle.text = sub
	var tw := create_tween().set_parallel(true)
	tw.tween_property(_title, "modulate:a", 1.0, 1.0)
	tw.tween_property(_subtitle, "modulate:a", 1.0, 1.4)
	var t := 0.0
	while t < 3.2 and not _skip:
		await get_tree().process_frame
		t += get_process_delta_time()
	var tw2 := create_tween().set_parallel(true)
	tw2.tween_property(_title, "modulate:a", 0.0, 0.8)
	tw2.tween_property(_subtitle, "modulate:a", 0.0, 0.8)


func _orbit(p: Vector3, o: Dictionary) -> Vector3:
	var yaw := deg_to_rad(float(o.get("yaw", 0.0)))
	var d := float(o.get("distance", 8.0))
	return p + Vector3(sin(yaw) * d, float(o.get("height", 3.0)), cos(yaw) * d)


func _shot(map: Node, shot: Dictionary) -> void:
	var p: Vector3 = map.marker_position(shot.marker)
	var look := p + Vector3.UP * float(shot.get("look_height", 1.6))
	var a := _orbit(p, shot.from)
	var b := _orbit(p, shot.to)
	var text: String = shot.get("text", "") if shot.get("text") else ""
	var speaker: String = shot.get("speaker", "") if shot.get("speaker") else ""
	_line.text = Story.fill(text)
	_speaker.text = Story.speaker_name(speaker) if speaker != "" else ""
	var vlen := Audio.play_voice(Story.voice_path(shot)) if shot.get("voice") else 0.0
	var dur := maxf(float(shot.get("duration", 4.0)), vlen + 0.6)
	var t := 0.0
	while t < dur and not _skip:
		var k := smoothstep(0.0, 1.0, t / dur)
		_cam.global_position = a.lerp(b, k)
		if _cam.global_position.distance_to(look) > 0.1:
			_cam.look_at(look)
		await get_tree().process_frame
		t += get_process_delta_time()

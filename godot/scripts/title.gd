extends Node3D
## Title screen: the sect at dusk behind the menu (new game, continue,
## chapter select, quit).

var _cam: Camera3D
var _t := 0.0
var _centre := Vector3.ZERO
var _menu: VBoxContainer
var _chars: VBoxContainer
var _chapters: PanelContainer


func _ready() -> void:
	var map: Node3D = (load("res://scenes/maps/sect.tscn") as PackedScene).instantiate()
	add_child(map)
	await get_tree().physics_frame
	_centre = map.marker_position("FormationArray")
	_cam = Camera3D.new()
	_cam.fov = 55.0
	_cam.far = 3000.0
	add_child(_cam)
	_cam.make_current()
	# the two heroes on the cliff edge
	var edge: Vector3 = map.marker_position("HallSteps")
	for i in 2:
		var m: Node3D = (load("res://assets/characters/%s.glb" % ["cultivator_male", "cultivator_female"][i]) as PackedScene).instantiate()
		add_child(m)
		ActorLook.apply(m)
		m.global_position = edge + Vector3(-0.6 + i * 1.2, 0, 6.0)
		m.rotation.y = PI
		var ap := m.find_child("AnimationPlayer", true, false) as AnimationPlayer
		ActorLook.loop_anims(ap)
		ap.play("idle")
		ap.seek(i * 1.3)
	_build_ui()
	Audio.play_music("title")


func _process(delta: float) -> void:
	_t += delta
	if _cam:
		var a := 0.6 + _t * 0.03
		_cam.global_position = _centre + Vector3(sin(a) * 34.0, 11.0 + sin(_t * 0.2) * 1.5, cos(a) * 34.0)
		_cam.look_at(_centre + Vector3(0, 4, -20))


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UiTheme.get_theme()
	layer.add_child(root)
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_LEFT_WIDE)
	shade.custom_minimum_size = Vector2(520, 0)
	shade.color = Color(0.02, 0.03, 0.05, 0.55)
	root.add_child(shade)
	var box := VBoxContainer.new()
	box.position = Vector2(70, 110)
	box.add_theme_constant_override("separation", 10)
	root.add_child(box)
	box.add_child(UiTheme.label("AZURE CLOUD SECT", 54, UiTheme.GOLD, 10))
	box.add_child(UiTheme.label(Story.title + "  ·  a xianxia saga in one hundred quests", 21, UiTheme.MUTED, 4))
	var premise := UiTheme.label(Story.premise.split("\n\n")[-1], 16, UiTheme.TEXT, 3)
	premise.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	premise.custom_minimum_size.x = 440
	box.add_child(premise)
	var gap := Control.new()
	gap.custom_minimum_size.y = 40
	box.add_child(gap)
	_menu = VBoxContainer.new()
	_menu.add_theme_constant_override("separation", 10)
	box.add_child(_menu)
	if Game.has_save():
		_button(_menu, "Continue", _continue)
	_button(_menu, "New Game", func(): _menu.visible = false; _chars.visible = true)
	_button(_menu, "Chapter Select", func(): _chapters.visible = true)
	_button(_menu, "Quit", func(): get_tree().quit())
	_chars = VBoxContainer.new()
	_chars.add_theme_constant_override("separation", 10)
	_chars.visible = false
	box.add_child(_chars)
	_chars.add_child(UiTheme.label("Who climbs the nine thousand steps?", 20, UiTheme.TEXT))
	_button(_chars, "Lin Feng  —  a wandering orphan with a stubborn heart", func(): _new_game(0))
	_button(_chars, "Su Yue  —  a physician's daughter seeking the dao", func(): _new_game(1))
	_button(_chars, "Back", func(): _chars.visible = false; _menu.visible = true)
	_chapters = PanelContainer.new()
	_chapters.set_anchors_preset(Control.PRESET_CENTER_RIGHT)
	_chapters.position = Vector2(-520, -300)
	_chapters.custom_minimum_size = Vector2(460, 600)
	_chapters.visible = false
	root.add_child(_chapters)
	var cv := VBoxContainer.new()
	cv.add_theme_constant_override("separation", 6)
	_chapters.add_child(cv)
	cv.add_child(UiTheme.label("Chapters", 28, UiTheme.GOLD, 5))
	for c in Story.chapters:
		var n := int(c.number)
		_button(cv, "%d · %s" % [n, c.title], func(): _start_chapter(n))
	_button(cv, "Close", func(): _chapters.visible = false)
	var credit := UiTheme.label("Built with headless Blender and Godot · every model, texture, track and voice is procedural", 13, UiTheme.MUTED, 3)
	credit.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	credit.position = Vector2(20, -30)
	root.add_child(credit)


func _button(parent: Control, text: String, cb: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(420, 44)
	b.pressed.connect(cb)
	b.pressed.connect(func(): Audio.sfx("ui_click", -6.0))
	b.mouse_entered.connect(func(): Audio.sfx("ui_hover", -14.0))
	parent.add_child(b)
	return b


func _continue() -> void:
	if Game.load_save():
		get_tree().change_scene_to_file("res://scenes/game.tscn")


func _new_game(character: int) -> void:
	Game.reset()
	Game.character = character
	get_tree().change_scene_to_file("res://scenes/game.tscn")


func _start_chapter(n: int) -> void:
	var c := Game.character
	Game.start_at((n - 1) * 10)
	Game.character = c
	get_tree().change_scene_to_file("res://scenes/game.tscn")

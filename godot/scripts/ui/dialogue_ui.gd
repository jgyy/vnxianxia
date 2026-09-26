extends CanvasLayer
## Voiced conversation box with speaker portrait, name and typewriter text.

signal finished
signal line_started(speaker: String)

const CHARS_PER_SEC := 48.0
const PORTRAIT_DIR := "res://ui/portraits/"

var active := false
var _panel: PanelContainer
var _portrait: TextureRect
var _name: Label
var _title: Label
var _text: RichTextLabel
var _hint: Label
var _visible_chars := 0.0
var _advance := false
var _ignore_until := 0


func _ready() -> void:
	layer = 8
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiTheme.get_theme()
	add_child(root)
	_panel = PanelContainer.new()
	_panel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_panel.position = Vector2(-520, -214)
	_panel.custom_minimum_size = Vector2(1040, 186)
	_panel.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.04, 0.05, 0.08, 0.86), UiTheme.GOLD, 8))
	root.add_child(_panel)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 18)
	_panel.add_child(hb)
	_portrait = TextureRect.new()
	_portrait.custom_minimum_size = Vector2(150, 150)
	_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	hb.add_child(_portrait)
	var vb := VBoxContainer.new()
	vb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(vb)
	var nb := HBoxContainer.new()
	nb.add_theme_constant_override("separation", 12)
	vb.add_child(nb)
	_name = UiTheme.label("", 24, UiTheme.GOLD, 5)
	_title = UiTheme.label("", 15, UiTheme.MUTED, 3)
	_title.size_flags_vertical = Control.SIZE_SHRINK_END
	nb.add_child(_name)
	nb.add_child(_title)
	_text = RichTextLabel.new()
	_text.bbcode_enabled = true
	_text.fit_content = true
	_text.scroll_active = false
	_text.custom_minimum_size = Vector2(820, 96)
	_text.add_theme_font_size_override("normal_font_size", 21)
	_text.add_theme_font_size_override("italics_font_size", 21)
	_text.add_theme_constant_override("outline_size", 3)
	_text.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	vb.add_child(_text)
	_hint = UiTheme.label("E / Space  continue", 13, UiTheme.MUTED, 3)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vb.add_child(_hint)
	_panel.visible = false


func _unhandled_input(event: InputEvent) -> void:
	if not active or Time.get_ticks_msec() < _ignore_until:
		return
	var click: bool = event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT
	if click or event.is_action_pressed("advance"):
		_advance = true
		get_viewport().set_input_as_handled()


## Speak the lines in order. Await `finished` (or this coroutine) for the end.
func play(lines: Array) -> void:
	active = true
	_ignore_until = Time.get_ticks_msec() + 200
	_panel.visible = true
	for line in lines:
		await _line(line)
	Audio.stop_voice()
	_panel.visible = false
	active = false
	finished.emit()


func _line(line: Dictionary) -> void:
	var speaker: String = line.get("speaker", "narrator")
	line_started.emit(speaker)
	var narr := speaker == "narrator"
	_name.text = Story.speaker_name(speaker)
	_title.text = "" if narr or speaker == "player" else Story.npc(speaker).get("title", "")
	var model := ""
	if speaker == "player":
		model = "cultivator_male" if Game.character == 0 else "cultivator_female"
	elif not narr:
		model = Story.npc(speaker).get("model", "")
	var path := PORTRAIT_DIR + model + ".png"
	_portrait.texture = load(path) if model != "" and ResourceLoader.exists(path) else null
	_portrait.visible = _portrait.texture != null
	var body := Story.fill(line.get("text", ""))
	_text.text = ("[i]%s[/i]" % body) if narr else body
	_advance = false
	if Game.fast:
		return
	Audio.sfx("dialogue_next", -10.0)
	var vpath := Story.voice_path(line)
	var voice_len := Audio.play_voice(vpath)
	_visible_chars = 0.0
	_text.visible_characters = 0
	var total := _text.get_total_character_count()
	var elapsed := 0.0
	# text-only lines (the saga's new chapters) advance by themselves after a reading time
	if voice_len <= 0.0:
		voice_len = total / CHARS_PER_SEC + Story.reading_time(body) * 0.6
	_hint.text = "E / Space  continue" if vpath != "" else "E / Space  continue   ·   auto"
	while true:
		await get_tree().process_frame
		var dt := get_process_delta_time()
		elapsed += dt
		if _text.visible_characters < total:
			_visible_chars += dt * CHARS_PER_SEC
			_text.visible_characters = int(_visible_chars)
			if _advance:
				_text.visible_characters = total
				_advance = false
			continue
		_text.visible_characters = -1
		# auto-advance a moment after the voice finishes, or on input
		if _advance or (voice_len > 0.0 and elapsed > voice_len + 1.4):
			break
	_advance = false

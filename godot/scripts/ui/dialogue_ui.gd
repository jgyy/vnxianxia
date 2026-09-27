extends CanvasLayer
## Conversation box: the speaker's portrait, name and title, and the whole
## line at once (no typewriter). One press of E / Space / Enter or one left
## click advances exactly one line; a voiced line also moves on a moment after
## its voice ends, a text-only line after a reading time. The moral choices of
## the story use the same box (choose(): keys 1-4, click, or arrows + E / Enter).
##
## The box hugs the bottom of the screen and grows upward with its content;
## it is re-fitted whenever the content or the window changes so its bottom
## edge is never cut off (and its top never leaves the screen).

signal finished
signal line_started(speaker: String)
signal chosen(index: int)

const PORTRAIT_DIR := "res://ui/portraits/"
const PLAYER_PROMPT := "Your choice"
## gap between the box and the bottom / sides of the window (px)
const BOTTOM_MARGIN := 14.0
const SIDE_MARGIN := 16.0
const MAX_WIDTH := 1040.0
const PORTRAIT_SIZE := 150.0
## a press that lands this soon after a line appeared counts for that line
## only once (bounced or doubled key events never skip two lines)
const DEBOUNCE_MSEC := 90
## choices ignore keys this long after they appear, so a press meant to skip
## the last line can never pick an option by accident
const CHOICE_ARM_MSEC := 350
## seconds a voiced line stays up after its voice has finished
const VOICE_TAIL := 1.2

var active := false
var _panel: PanelContainer
var _row: HBoxContainer
var _portrait: TextureRect
var _name: Label
var _title: Label
var _text: RichTextLabel
var _hint: Label
var _advance := false
var _line_at := 0
var _choices: VBoxContainer
var _choosing := false
var _choice_armed_at := 0
var _speaker := ""


func _ready() -> void:
	layer = 8
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiTheme.get_theme()
	add_child(root)
	_panel = PanelContainer.new()
	# placed by _fit() in viewport pixels: anchored top-left, sized to content
	_panel.set_anchors_preset(Control.PRESET_TOP_LEFT)
	_panel.mouse_filter = Control.MOUSE_FILTER_PASS
	_panel.add_theme_stylebox_override("panel", UiTheme.panel(Color(0.04, 0.05, 0.08, 0.86), UiTheme.GOLD, 8))
	root.add_child(_panel)
	_row = HBoxContainer.new()
	_row.add_theme_constant_override("separation", 18)
	_panel.add_child(_row)
	_portrait = TextureRect.new()
	_portrait.custom_minimum_size = Vector2(PORTRAIT_SIZE, PORTRAIT_SIZE)
	_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_portrait.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	_row.add_child(_portrait)
	var vb := VBoxContainer.new()
	vb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_row.add_child(vb)
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
	_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_text.custom_minimum_size = Vector2(0, 96)
	_text.mouse_filter = Control.MOUSE_FILTER_PASS
	_text.add_theme_font_size_override("normal_font_size", 21)
	_text.add_theme_font_size_override("italics_font_size", 21)
	_text.add_theme_constant_override("outline_size", 3)
	_text.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	vb.add_child(_text)
	_choices = VBoxContainer.new()
	_choices.add_theme_constant_override("separation", 6)
	_choices.visible = false
	vb.add_child(_choices)
	_hint = UiTheme.label("E / Space  continue", 13, UiTheme.MUTED, 3)
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vb.add_child(_hint)
	_panel.visible = false
	get_viewport().size_changed.connect(_fit)
	_panel.minimum_size_changed.connect(_fit, CONNECT_DEFERRED)
	_fit()


## Size the box to the window and pin it to the bottom: the width follows the
## visible rect (so it also fits narrow windows and every stretch mode), the
## height follows the content, and the bottom edge stays BOTTOM_MARGIN above
## the bottom of the screen (the top is clamped at 0 if content ever exceeds it).
func _fit() -> void:
	if _panel == null:
		return
	var vr := get_viewport().get_visible_rect()
	var w := minf(MAX_WIDTH, vr.size.x - 2.0 * SIDE_MARGIN)
	# a narrow window gets a smaller portrait so the text keeps a readable width
	var ps := clampf(w * 0.15, 72.0, PORTRAIT_SIZE)
	_portrait.custom_minimum_size = Vector2(ps, ps)
	_panel.custom_minimum_size = Vector2(w, 0.0)
	_panel.size = Vector2(w, 0.0)          # shrink to the content's minimum height
	var h := maxf(_panel.get_combined_minimum_size().y, _panel.size.y)
	var y := vr.position.y + vr.size.y - BOTTOM_MARGIN - h
	_panel.position = Vector2(vr.position.x + (vr.size.x - w) * 0.5, maxf(vr.position.y, y))


## The box's rectangle on screen (tests).
func panel_rect() -> Rect2:
	return _panel.get_global_rect()


func _process(_delta: float) -> void:
	# containers settle a frame after a content change; keep the box clamped
	if _panel.visible:
		var vr := get_viewport().get_visible_rect()
		var r := _panel.get_global_rect()
		if r.end.y > vr.end.y - BOTTOM_MARGIN + 0.5 or r.position.y < vr.position.y - 0.5 \
				or absf(r.end.y - (vr.end.y - BOTTOM_MARGIN)) > 0.5:
			_fit()


func _input(event: InputEvent) -> void:
	if not active:
		return
	if _choosing:
		_choice_input(event)
		return
	var press := false
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		press = mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT
	elif event is InputEventKey or event is InputEventJoypadButton:
		press = event.is_action_pressed("advance")      # never an echo of a held key
	if not press:
		return
	# the box owns this press: it must not also jump, interact or capture the mouse
	get_viewport().set_input_as_handled()
	if Time.get_ticks_msec() - _line_at >= DEBOUNCE_MSEC:
		_advance = true


func _choice_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var key := event as InputEventKey
	var n := _choices.get_child_count()
	var armed := Time.get_ticks_msec() >= _choice_armed_at
	var k := -1
	if key.keycode >= KEY_1 and key.keycode <= KEY_9:
		k = key.keycode - KEY_1
	elif key.keycode >= KEY_KP_1 and key.keycode <= KEY_KP_9:
		k = key.keycode - KEY_KP_1
	if k >= 0:
		get_viewport().set_input_as_handled()
		if armed and k < n:
			chosen.emit(k)
		return
	var focus := _focused_choice()
	if key.keycode in [KEY_UP, KEY_DOWN, KEY_W, KEY_S]:
		get_viewport().set_input_as_handled()
		var step := -1 if key.keycode in [KEY_UP, KEY_W] else 1
		var nxt := 0 if focus < 0 else wrapi(focus + step, 0, n)
		(_choices.get_child(nxt) as Control).grab_focus()
		return
	if event.is_action_pressed("advance") or event.is_action_pressed("ui_accept"):
		get_viewport().set_input_as_handled()
		if armed and focus >= 0:
			chosen.emit(focus)


func _focused_choice() -> int:
	for i in _choices.get_child_count():
		if (_choices.get_child(i) as Control).has_focus():
			return i
	return -1


## Speak the lines in order. Await this coroutine (or `finished`) for the end.
## A second conversation started while one is running waits its turn instead
## of fighting over the box.
func play(lines: Array) -> void:
	while active:
		await finished
	if lines.is_empty():
		return
	active = true
	_advance = false
	_panel.visible = true
	for line in lines:
		await _line(line)
		if not is_inside_tree():
			return
	Audio.stop_voice()
	_panel.visible = false
	active = false
	_speaker = ""
	finished.emit()


func _show_speaker(speaker: String) -> void:
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
	# the protagonist's portrait sits on the right, everyone else's on the left
	_row.move_child(_portrait, _row.get_child_count() - 1 if speaker == "player" else 0)
	_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_speaker = speaker


func _line(line: Dictionary) -> void:
	var speaker: String = line.get("speaker", "narrator")
	_show_speaker(speaker)
	var body := Story.fill(line.get("text", ""))
	_text.text = ("[i]%s[/i]" % body) if speaker == "narrator" else body
	_text.visible_characters = -1
	_fit()
	# a press made before this line appeared never counts for it
	_advance = false
	_line_at = Time.get_ticks_msec()
	line_started.emit(speaker)
	if Game.fast:
		return
	Audio.sfx("dialogue_next", -10.0)
	var vpath := Story.voice_path(line)
	var voice_len := Audio.play_voice(vpath)
	# voiced: a moment after the voice ends; text-only: a reading time
	var wait := voice_len + VOICE_TAIL if voice_len > 0.0 else Story.reading_time(body)
	_hint.text = "E / Space  continue" if voice_len > 0.0 else "E / Space  continue   ·   auto"
	var elapsed := 0.0
	while not _advance and elapsed < wait:
		await get_tree().process_frame
		if not is_inside_tree():
			return
		elapsed += get_process_delta_time()
	_advance = false


## Offer 2-4 options after ``prompt``; returns the chosen index. In fast mode
## (tests) the choice is made at once by Game.auto_choice().
func choose(prompt: String, options: Array) -> int:
	if Game.fast or options.size() <= 1:
		return Game.auto_choice(options.size()) if options.size() > 1 else 0
	while active:
		await finished
	active = true
	_choosing = true
	_panel.visible = true
	_show_speaker("player")
	_name.text = PLAYER_PROMPT
	_text.visible_characters = -1
	_text.text = "[i]%s[/i]" % prompt
	for c in _choices.get_children():
		_choices.remove_child(c)
		c.queue_free()
	for i in options.size():
		var b := Button.new()
		b.text = "%d.  %s" % [i + 1, options[i]]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		b.add_theme_font_size_override("font_size", 18)
		b.focus_mode = Control.FOCUS_ALL
		b.pressed.connect(func():
			if _choosing and Time.get_ticks_msec() >= _choice_armed_at:
				chosen.emit(i))
		_choices.add_child(b)
	_choices.visible = true
	_hint.text = "1-%d, click, or arrows + E  choose" % options.size()
	_fit()
	_choice_armed_at = Time.get_ticks_msec() + CHOICE_ARM_MSEC
	var prev_mouse := Input.mouse_mode
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	Audio.sfx("ui_open", -8.0)
	var i: int = await chosen
	Audio.sfx("ui_click", -6.0)
	_choosing = false
	_choices.visible = false
	for c in _choices.get_children():
		_choices.remove_child(c)
		c.queue_free()
	Input.mouse_mode = prev_mouse
	_panel.visible = false
	active = false
	finished.emit()
	return i

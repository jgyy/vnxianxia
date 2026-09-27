extends CanvasLayer
## Teleport array destination picker.

signal chosen(map_id: String)

var open := false
var _list: VBoxContainer
var _mouse_before := Input.MOUSE_MODE_VISIBLE


func _ready() -> void:
	layer = 12
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UiTheme.get_theme()
	add_child(root)
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-220, -200)
	panel.custom_minimum_size = Vector2(440, 0)
	root.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 8)
	panel.add_child(vb)
	vb.add_child(UiTheme.label("Teleport Array", 28, UiTheme.GOLD, 5))
	vb.add_child(UiTheme.label("Choose a destination", 15, UiTheme.MUTED))
	_list = VBoxContainer.new()
	_list.add_theme_constant_override("separation", 6)
	vb.add_child(_list)
	var cancel := Button.new()
	cancel.text = "Stay"
	cancel.pressed.connect(close)
	vb.add_child(cancel)
	visible = false


func show_for(current: String, quest_map: String) -> void:
	if open:
		return
	for c in _list.get_children():
		_list.remove_child(c)
		c.queue_free()
	var maps: Array = []
	for m in Game.visited:
		# interiors are reached through their doors, never by teleport
		if not Doors.INTERIORS.has(m) and not maps.has(m):
			maps.append(m)
	if quest_map != "" and not maps.has(quest_map) and not Doors.INTERIORS.has(quest_map):
		maps.append(quest_map)
	for m in maps:
		var b := Button.new()
		b.text = Story.map_name(m) + ("   — quest" if m == quest_map and m != current else "")
		b.disabled = m == current
		b.pressed.connect(func(): close(); chosen.emit(m))
		_list.add_child(b)
	open = true
	visible = true
	get_tree().paused = true
	_mouse_before = Input.mouse_mode
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	Audio.sfx("ui_open", -6.0)


func close() -> void:
	if not open:
		return
	open = false
	visible = false
	get_tree().paused = false
	Input.mouse_mode = _mouse_before


func _unhandled_input(event: InputEvent) -> void:
	if open and event.is_action_pressed("pause"):
		close()
		get_viewport().set_input_as_handled()

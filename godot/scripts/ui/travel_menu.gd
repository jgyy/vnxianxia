extends CanvasLayer
## Teleport array destination picker.

signal chosen(map_id: String)

var open := false
var _list: VBoxContainer


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
	for c in _list.get_children():
		c.queue_free()
	var maps: Array = Game.visited.duplicate()
	if quest_map != "" and not maps.has(quest_map):
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
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	Audio.sfx("ui_open", -6.0)


func close() -> void:
	open = false
	visible = false
	get_tree().paused = false


func _unhandled_input(event: InputEvent) -> void:
	if open and event.is_action_pressed("pause"):
		close()
		get_viewport().set_input_as_handled()

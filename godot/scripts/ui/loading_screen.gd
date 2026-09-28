extends CanvasLayer
## Full-screen loading card: region key art, name, a tip and progress.

const ART_DIR := "res://ui/loading/"
const TIPS := [
	"Meditate (C) anywhere to restore vitality and qi faster.",
	"A qi blast (Q) strikes from afar, but costs qi. Palm strikes (F) are free.",
	"Teleport arrays link every region you have visited. Press E on one to travel.",
	"Tab switches between Lin Feng and Su Yue; the story remembers who you are.",
	"Your journal (J) lists every quest and your cultivation.",
	"Bosses shrug off most flinches. Keep moving and strike after they attack.",
	"Breakthroughs raise vitality, qi and the power of your techniques.",
	"The golden pillar of light marks your current objective.",
]

var _art: TextureRect
var _title: Label
var _sub: Label
var _tip: Label
var _synopsis: Label
var _bar: ProgressBar
var _fade: ColorRect
var _close_tween: Tween


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.theme = UiTheme.get_theme()
	add_child(root)
	var bg := ColorRect.new()
	bg.color = Color(0.03, 0.035, 0.05)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)
	_art = TextureRect.new()
	_art.set_anchors_preset(Control.PRESET_FULL_RECT)
	_art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	root.add_child(_art)
	var shade := ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	shade.custom_minimum_size = Vector2(0, 260)
	shade.position.y = -260
	shade.color = Color(0, 0, 0, 0.55)
	root.add_child(shade)
	var box := VBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	box.position = Vector2(60, -236)
	box.add_theme_constant_override("separation", 8)
	root.add_child(box)
	_title = UiTheme.label("", 48, UiTheme.GOLD, 8)
	_sub = UiTheme.label("", 20, UiTheme.MUTED, 4)
	_synopsis = UiTheme.label("", 17, UiTheme.TEXT, 3)
	_synopsis.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_synopsis.custom_minimum_size.x = 1100
	_tip = UiTheme.label("", 15, UiTheme.MUTED, 3)
	_bar = UiTheme.bar(UiTheme.GOLD, 520, 6)
	for c in [_title, _sub, _synopsis, _tip, _bar]:
		box.add_child(c)
	_fade = ColorRect.new()
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	_fade.color = Color(0, 0, 0, 0)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_fade)
	visible = false


func open(map_id: String, subtitle := "") -> void:
	# a fade-out still running from the previous load would hide this one
	if _close_tween and _close_tween.is_valid():
		_close_tween.kill()
	_fade.color.a = 0.0
	var path := ART_DIR + map_id + ".jpg"
	_art.texture = load(path) if ResourceLoader.exists(path) else null
	_title.text = Story.map_name(map_id)
	_sub.text = subtitle
	var q := Game.quest()
	_synopsis.text = Story.fill(Story.chapter(int(q.chapter)).get("summary", "")) if not q.is_empty() else Story.premise
	if not q.is_empty() and Game.objective_index == 0:
		# the very start of a volume: show the volume's synopsis instead
		var v := Story.volume(int(q.get("volume", 1)))
		if int(q.number) - 1 == int(v.get("first", -1)):
			_synopsis.text = Story.fill(v.get("summary", ""))
	_tip.text = "Tip: " + TIPS[randi() % TIPS.size()]
	_bar.value = 0.0
	visible = true


func set_progress(v: float) -> void:
	_bar.value = v


func close() -> void:
	if Game.fast:
		visible = false
		return
	_fade.color.a = 0.0
	var tw := create_tween()
	_close_tween = tw
	tw.tween_property(_fade, "color:a", 1.0, 0.25)
	tw.tween_callback(func(): visible = false; _fade.color.a = 0.0)

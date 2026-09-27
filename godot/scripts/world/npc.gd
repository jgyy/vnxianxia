class_name Npc
extends Node3D
## A story character standing at a marker: model, name plate, quest indicator.

var npc_id := ""
var data: Dictionary = {}
var model: Node3D
var anim: AnimationPlayer
var quest_target := false
var talking := false
## name plate hidden (a conversation close-up doesn't need a label over every head)
var hide_plate := false
var _plate: Label3D
var _mark: Label3D
var _look_at := Vector3.INF
var _t := 0.0


static func create(id: String) -> Npc:
	var n := Npc.new()
	n.npc_id = id
	n.data = Story.npc(id)
	n.name = "Npc_" + id
	return n


func _ready() -> void:
	add_to_group("npcs")
	var path := "res://assets/characters/%s.glb" % data.get("model", "disciple_male")
	if not ResourceLoader.exists(path):
		# a story NPC whose model is not built (yet): stand in a disciple rather than crash
		push_warning("npc %s: no model %s" % [npc_id, path])
		path = "res://assets/characters/disciple_male.glb"
	model = (load(path) as PackedScene).instantiate()
	model.scale = Vector3.ONE * float(data.get("scale", 1.0))
	add_child(model)
	ActorLook.apply(model, data.get("tint"))
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim:
		ActorLook.loop_anims(anim)
		anim.play("idle")
		anim.seek(randf() * 3.0)
	# solid body on layer 2 (the player collides, ground probes ignore it)
	var body := StaticBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.7
	shape.shape = cap
	shape.position.y = 0.85
	body.add_child(shape)
	add_child(body)
	var h := 1.95 * float(data.get("scale", 1.0))
	_plate = _label(data.get("name", npc_id), 42, Color(1.0, 0.95, 0.82), h + 0.12)
	var title: String = data.get("title", "")
	if title:
		_plate.text += "\n" + title
		_plate.font_size = 40
	_mark = _label("!", 150, Color(1.0, 0.82, 0.25), h + 0.55)
	_mark.outline_size = 22
	_mark.visible = false


func _label(text: String, size: int, color: Color, y: float) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.font_size = size
	l.pixel_size = 0.0035
	l.modulate = color
	l.outline_modulate = Color(0.05, 0.05, 0.1, 0.85)
	l.outline_size = 10
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = false
	l.position.y = y
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(l)
	return l


func set_quest_target(on: bool) -> void:
	quest_target = on
	_mark.visible = on


func face(point: Vector3) -> void:
	_look_at = point


func play(anim_name: String) -> void:
	if anim and anim.has_animation(anim_name) and anim.current_animation != anim_name:
		anim.play(anim_name, 0.3)


func set_talking(on: bool) -> void:
	talking = on
	play("talk" if on else "idle")


func _process(delta: float) -> void:
	_t += delta
	if _mark.visible:
		_mark.position.y = 1.95 * float(data.get("scale", 1.0)) + 0.55 + sin(_t * 3.0) * 0.06
	var cam := get_viewport().get_camera_3d()
	if cam:
		var d := cam.global_position.distance_to(global_position)
		_plate.visible = d < 14.0 and not hide_plate
	if _look_at != Vector3.INF:
		var to := _look_at - global_position
		to.y = 0
		if to.length() > 0.05:
			rotation.y = lerp_angle(rotation.y, atan2(to.x, to.z), clampf(5.0 * delta, 0, 1))

class_name Pickup
extends Node3D
## A collectible quest item bobbing above the ground.

signal collected(pickup: Pickup)

const MODELS := {"spirit_herb": "spirit_herb", "spirit_stone": "spirit_stone", "jade_slip": "jade_slip"}
const COLORS := {
	"wolf_fang": Color(0.95, 0.92, 0.8), "blood_lotus": Color(1.0, 0.2, 0.3), "demon_core": Color(0.8, 0.1, 0.2),
	"star_iron": Color(0.7, 0.75, 1.0), "thunder_crystal": Color(0.6, 0.7, 1.0), "cloud_silk": Color(0.95, 0.95, 1.0),
	"phoenix_feather": Color(1.0, 0.55, 0.15), "medicine": Color(0.5, 0.9, 0.4), "letter": Color(1.0, 0.9, 0.6),
	"lantern_oil": Color(1.0, 0.7, 0.2), "rune_fragment": Color(0.4, 1.0, 0.9),
}

var item := ""
var taken := false
var _t := randf() * 6.0
var _body: Node3D


static func create(item_id: String) -> Pickup:
	var p := Pickup.new()
	p.item = item_id
	return p


func _ready() -> void:
	add_to_group("pickups")
	var col: Color = COLORS.get(item, Color(0.6, 1.0, 0.9))
	if MODELS.has(item) and ResourceLoader.exists("res://assets/environment/%s.glb" % MODELS[item]):
		_body = (load("res://assets/environment/%s.glb" % MODELS[item]) as PackedScene).instantiate()
		col = Color(0.55, 1.0, 0.85) if item != "jade_slip" else Color(0.6, 1.0, 0.7)
	else:
		_body = MeshInstance3D.new()
		var m: PrimitiveMesh = PrismMesh.new() if item in ["star_iron", "thunder_crystal", "demon_core", "rune_fragment"] else SphereMesh.new()
		if m is SphereMesh:
			m.radius = 0.16
			m.height = 0.32
		else:
			m.size = Vector3(0.25, 0.4, 0.25)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = col
		mat.emission_enabled = true
		mat.emission = col
		mat.emission_energy_multiplier = 2.5
		mat.roughness = 0.2
		m.material = mat
		(_body as MeshInstance3D).mesh = m
		_body.position.y = 0.6
	add_child(_body)
	var glow := Fx.motes(col, 14, Vector3(0.3, 0.2, 0.3), 2.0, 0.025)
	glow.position.y = 0.4
	add_child(glow)
	var light := OmniLight3D.new()
	light.light_color = col
	light.light_energy = 0.8
	light.omni_range = 2.5
	light.position.y = 0.7
	add_child(light)


func _process(delta: float) -> void:
	_t += delta
	_body.rotation.y += delta * 0.8
	if _body is MeshInstance3D:
		_body.position.y = 0.6 + sin(_t * 2.0) * 0.08


func take() -> void:
	if taken:
		return
	taken = true
	Audio.sfx("pickup", -4.0)
	Fx.burst(get_parent(), global_position + Vector3.UP * 0.5, COLORS.get(item, Color(0.6, 1, 0.9)), 30, 3.0)
	collected.emit(self)
	queue_free()

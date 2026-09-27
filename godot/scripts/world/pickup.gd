class_name Pickup
extends Node3D
## A collectible quest item hovering and turning above the ground: the item's
## own model (world.json item_model_dir: res://assets/items/<item>.glb) when it
## exists, else an older environment model, else a glowing primitive. Models
## are scaled to a common hand-held size so a tiny slip and a large feather
## read alike, and lit by a soft light in the item's colour.

signal collected(pickup: Pickup)

const LEGACY_MODELS := {"spirit_herb": "spirit_herb", "spirit_stone": "spirit_stone", "jade_slip": "jade_slip"}
const COLORS := {
	"wolf_fang": Color(0.95, 0.92, 0.8), "blood_lotus": Color(1.0, 0.2, 0.3), "demon_core": Color(0.8, 0.1, 0.2),
	"star_iron": Color(0.7, 0.75, 1.0), "thunder_crystal": Color(0.6, 0.7, 1.0), "cloud_silk": Color(0.95, 0.95, 1.0),
	"phoenix_feather": Color(1.0, 0.55, 0.15), "medicine": Color(0.5, 0.9, 0.4), "letter": Color(1.0, 0.9, 0.6),
	"lantern_oil": Color(1.0, 0.7, 0.2), "rune_fragment": Color(0.4, 1.0, 0.9),
}
## the largest dimension of a model is scaled toward this (m)
const DISPLAY_SIZE := 0.42
const HOVER := 0.55
const BOB := 0.07

var item := ""
var taken := false
var _t := randf() * 6.0
var _body: Node3D
var _col := Color(0.6, 1.0, 0.9)
var _base_y := HOVER


static func create(item_id: String) -> Pickup:
	var p := Pickup.new()
	p.item = item_id
	return p


## res:// path of the item's model, or "" when it has none.
static func model_path(item_id: String) -> String:
	var dir: String = Story.world.get("item_model_dir", "res://assets/items")
	var own := "%s/%s.glb" % [dir.trim_suffix("/"), item_id]
	if ResourceLoader.exists(own):
		return own
	if LEGACY_MODELS.has(item_id):
		var old := "res://assets/environment/%s.glb" % LEGACY_MODELS[item_id]
		if ResourceLoader.exists(old):
			return old
	return ""


func _ready() -> void:
	add_to_group("pickups")
	_col = COLORS.get(item, Color(0.6, 1.0, 0.9))
	var path := model_path(item)
	if path != "":
		var pivot := Node3D.new()        # turns and bobs; the model is centred inside it
		var inst := (load(path) as PackedScene).instantiate() as Node3D
		pivot.add_child(inst)
		add_child(pivot)
		_body = pivot
		var box := _bounds(inst)
		var big := maxf(box.size.x, maxf(box.size.y, box.size.z))
		var s := clampf(DISPLAY_SIZE / big, 0.35, 4.0) if big > 0.001 else 1.0
		inst.scale = Vector3.ONE * s
		# centre the model on the pivot so it turns about its own middle
		inst.position = -box.get_center() * s
		_base_y = maxf(HOVER, box.size.y * s * 0.5 + 0.15)
		for gi in inst.find_children("*", "GeometryInstance3D", true, false):
			(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if not COLORS.has(item):
			_col = Color(0.6, 1.0, 0.85)
	else:
		var mi := MeshInstance3D.new()
		var m: PrimitiveMesh = PrismMesh.new() if item in ["star_iron", "thunder_crystal", "demon_core", "rune_fragment"] else SphereMesh.new()
		if m is SphereMesh:
			m.radius = 0.16
			m.height = 0.32
		else:
			m.size = Vector3(0.25, 0.4, 0.25)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = _col
		mat.emission_enabled = true
		mat.emission = _col
		mat.emission_energy_multiplier = 2.5
		mat.roughness = 0.2
		m.material = mat
		mi.mesh = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_body = mi
		add_child(_body)
	_body.position.y = _base_y
	var glow := Fx.motes(_col, 14, Vector3(0.3, 0.2, 0.3), 2.0, 0.025)
	glow.position.y = 0.4
	add_child(glow)
	var light := OmniLight3D.new()
	light.light_color = _col
	light.light_energy = 0.6
	light.omni_range = 2.2
	light.shadow_enabled = false
	light.position.y = _base_y + 0.15
	add_child(light)


func _process(delta: float) -> void:
	_t += delta
	_body.rotation.y += delta * 0.8
	_body.position.y = _base_y + sin(_t * 2.0) * BOB


func take() -> void:
	if taken:
		return
	taken = true
	Audio.sfx("pickup", -4.0)
	Fx.burst(get_parent(), global_position + Vector3.UP * 0.5, _col, 30, 3.0)
	collected.emit(self)
	queue_free()


static func _bounds(root: Node3D) -> AABB:
	var out := AABB()
	var first := true
	var inv := root.global_transform.affine_inverse() if root.is_inside_tree() else Transform3D.IDENTITY
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.mesh == null:
			continue
		var t: Transform3D = inv * m.global_transform if root.is_inside_tree() else _rel(root, m)
		var b: AABB = t * m.get_aabb()
		out = b if first else out.merge(b)
		first = false
	return out


static func _rel(root: Node3D, n: Node3D) -> Transform3D:
	var t := Transform3D.IDENTITY
	var cur: Node = n
	while cur and cur != root:
		if cur is Node3D:
			t = (cur as Node3D).transform * t
		cur = cur.get_parent()
	return t

class_name QuestProp
extends Node3D
## An interactable object (stele, chest, altar, boat...) placed for an
## objective: the GLB named in world.json `props` (res://assets/environment),
## stood on the ground, or a glowing seal when there is no model.
##
## footprint() is the prop's horizontal half-size, so the interaction reach,
## the objective beacon and the NPCs gathered around it scale with big props.

## how close (m) to the prop's outline the player must be to use it
const REACH := 2.0

var prop_id := ""
var used := false
var _extent := 0.6
var _height := 0.2
## the model's bounds in this node's space (a 1.2 m seal when there is no model)
var _box := AABB(Vector3(-0.6, 0.0, -0.6), Vector3(1.2, 0.12, 1.2))


static func create(id: String) -> QuestProp:
	var p := QuestProp.new()
	p.prop_id = id
	return p


func _ready() -> void:
	add_to_group("props")
	var glb = Story.world.get("props", {}).get(prop_id)
	var path := "res://assets/environment/%s.glb" % glb if glb else ""
	if glb and ResourceLoader.exists(path):
		var inst := (load(path) as PackedScene).instantiate() as Node3D
		add_child(inst)
		var box := _local_aabb(inst)
		if box.size != Vector3.ZERO:
			# stand it on the ground: a model modelled floating (or centred on
			# its origin) is lowered / raised so its base meets the marker
			if box.position.y > 0.02 or box.position.y < -0.5:
				inst.position.y -= box.position.y
				box.position.y = 0.0
			_box = box
			_extent = clampf(maxf(box.size.x, box.size.z) * 0.5, 0.3, 8.0)
			_height = box.size.y
		if inst.find_children("*", "CollisionObject3D", true, false).is_empty():
			_add_body()
	else:
		var seal := MeshInstance3D.new()
		var m := CylinderMesh.new()
		m.top_radius = 0.5
		m.bottom_radius = 0.6
		m.height = 0.12
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.9, 0.8, 0.5)
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.8, 0.3)
		mat.emission_energy_multiplier = 2.0
		m.material = mat
		seal.mesh = m
		seal.position.y = 0.07
		add_child(seal)


## Horizontal half-size of the prop in metres.
func footprint() -> float:
	return _extent


## Horizontal distance from `p` to the prop's outline (0 inside it); INF when
## `p` is on another level (a terrace above or below).
func edge_distance(p: Vector3) -> float:
	var l := global_transform.affine_inverse() * p
	if l.y < _box.position.y - 3.0 or l.y > _box.end.y + 3.0:
		return INF
	var dx := maxf(maxf(_box.position.x - l.x, 0.0), l.x - _box.end.x)
	var dz := maxf(maxf(_box.position.z - l.z, 0.0), l.z - _box.end.z)
	return Vector2(dx, dz).length()


## A walkable, open spot just outside the prop from which it can be used,
## preferring its front (+Z) side. Used by tests to walk up to big props.
func approach_point(map: Node) -> Vector3:
	var dirs := [Vector3.BACK, Vector3.RIGHT, Vector3.LEFT, Vector3.FORWARD]
	for d in dirs:
		for extra in [0.9, 1.4]:
			var local: Vector3 = _box.get_center() * Vector3(1, 0, 1) + d * (absf((_box.size * 0.5).dot(d)) + extra)
			var g: Vector3 = map.ground_at(global_transform * local)
			if absf(g.y - global_position.y) < 1.5 and map.is_open(g, 0.32) and edge_distance(g) < REACH:
				return g
	return map.ground_at(global_transform * (Vector3.BACK * (_box.end.z + 1.0)))


func height() -> float:
	return _height


## A solid body the player bumps into (on the NPC layer, so ground probes and
## the placement of pickups and people ignore it).
func _add_body() -> void:
	if _height < 0.3:
		return
	var body := StaticBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = _extent * 0.8
	cyl.height = _height
	shape.shape = cyl
	shape.position.y = _height * 0.5
	body.add_child(shape)
	add_child(body)


## Bounds of every mesh under `root`, in this prop's space.
func _local_aabb(root: Node3D) -> AABB:
	var out := AABB()
	var first := true
	var inv := global_transform.affine_inverse()
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.mesh == null:
			continue
		var b: AABB = (inv * m.global_transform) * m.get_aabb()
		out = b if first else out.merge(b)
		first = false
	return out

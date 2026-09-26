class_name ActorLook
extends RefCounted
## Material touch-ups for imported character GLBs: subsurface-scattered skin,
## cloth tints for reused NPC models, and special looks (shadow heart demon).

const SKIN_KEYS := ["_face", "_skin", "_nail", "_eyelid"]
const CLOTH_KEYS := ["_robe", "_trim", "_belt", "_undercollar", "_scarf", "_band"]


static func _materials(model: Node) -> Array:
	var out := []
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		for i in m.mesh.get_surface_count():
			out.append([m, i])
	return out


static func _has(name: String, keys: Array) -> bool:
	for k in keys:
		if name.contains(k):
			return true
	return false


## Called for every spawned humanoid: skin gets subsurface scattering and a
## soft rim, eyes get a wet specular.
static func apply(model: Node, tint = null) -> void:
	for pair in _materials(model):
		var m: MeshInstance3D = pair[0]
		var i: int = pair[1]
		var src := m.get_active_material(i) as StandardMaterial3D
		if src == null:
			continue
		var n := src.resource_name
		var mat: StandardMaterial3D = null
		if _has(n, SKIN_KEYS):
			mat = src.duplicate()
			mat.subsurf_scatter_enabled = true
			mat.subsurf_scatter_strength = 0.35 if n.contains("_face") else 0.25
			mat.subsurf_scatter_skin_mode = true
			mat.rim_enabled = true
			mat.rim = 0.12
			mat.rim_tint = 0.6
		elif n.ends_with("_eye"):
			mat = src.duplicate()
			mat.clearcoat_enabled = true
			mat.clearcoat = 1.0
			mat.clearcoat_roughness = 0.05
		elif n.ends_with("_hair") or n.ends_with("_beard"):
			mat = src.duplicate()
			mat.anisotropy_enabled = true
			mat.anisotropy = 0.6
		elif tint != null and _has(n, CLOTH_KEYS):
			mat = src.duplicate()
			mat.albedo_color = Color(tint[0], tint[1], tint[2])
		if mat:
			m.set_surface_override_material(i, mat)


## A translucent violet-black silhouette with glowing edges (the heart demon).
static func shadow(model: Node) -> void:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.05, 0.02, 0.08, 0.82)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.emission_enabled = true
	mat.emission = Color(0.45, 0.08, 0.6)
	mat.emission_energy_multiplier = 0.6
	mat.rim_enabled = true
	mat.rim = 1.0
	mat.rim_tint = 0.0
	mat.roughness = 0.3
	for pair in _materials(model):
		(pair[0] as MeshInstance3D).set_surface_override_material(pair[1], mat)


## Multiply every material by a colour (corrupted wolves, wooden puppets...).
static func recolor(model: Node, color: Color, glow := Color.BLACK) -> void:
	for pair in _materials(model):
		var m: MeshInstance3D = pair[0]
		var src := m.get_active_material(pair[1]) as StandardMaterial3D
		if src == null:
			continue
		var mat: StandardMaterial3D = src.duplicate()
		mat.albedo_color = src.albedo_color * color
		if glow != Color.BLACK and mat.emission_enabled:
			mat.emission = glow
		m.set_surface_override_material(pair[1], mat)


static func loop_anims(anim: AnimationPlayer) -> void:
	for a in ["idle", "walk", "run", "meditate", "talk"]:
		if anim.has_animation(a):
			anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR

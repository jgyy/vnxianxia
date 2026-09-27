class_name ActorLook
extends RefCounted
## Material touch-ups for imported character GLBs: subsurface-scattered skin,
## cloth tints for reused NPC models, and special looks (shadow heart demon).

const SKIN_KEYS := ["_face", "_skin", "_nail", "_eyelid"]
const CLOTH_KEYS := ["_robe", "_trim", "_belt", "_undercollar", "_scarf", "_band"]
## strand-card hair and hair-like cards (alpha-masked in the GLB)
const CARD_SUFFIXES := ["_hair", "_beard", "_brows", "_lashes"]
## light subsurface scattering for the mouth and the white of the eye
const SOFT_SSS := {"_eye_sclera": 0.2, "_teeth": 0.15, "_tongue": 0.4}
## thin wet films over the eye: exported as alpha blend, rendered additive
const FILMS := ["_eye_cornea", "_eye_tearline"]


static func _materials(model: Node) -> Array:
	var out := []
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.mesh == null:
			continue
		for i in m.mesh.get_surface_count():
			out.append([m, i])
	return out


static func _has(name: String, keys: Array) -> bool:
	for k in keys:
		if name.contains(k):
			return true
	return false


static func _ends(name: String, keys: Array) -> bool:
	for k in keys:
		if name.ends_with(k):
			return true
	return false


## Called for every spawned humanoid (material names from
## blender/xianxia/skin_shading.py, skin_eyes.py and hair_tex.py). Only
## materials are touched: meshes, skeletons and blend shapes (the facial
## animation baked into the actions) are left as imported.
static func apply(model: Node, tint = null) -> void:
	for pair in _materials(model):
		var m: MeshInstance3D = pair[0]
		var i: int = pair[1]
		var src := m.get_active_material(i) as StandardMaterial3D
		if src == null:
			continue
		var n := src.resource_name
		var mat: StandardMaterial3D = null
		if _ends(n, FILMS):
			# cornea / tear line: only their glint should show, added over the eye
			mat = src.duplicate()
			mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			mat.albedo_color = Color(0.0, 0.0, 0.0, src.albedo_color.a)
			mat.albedo_texture = null
		elif _ends(n, CARD_SUFFIXES):
			# strand cards: alpha-to-coverage keeps the masked edges soft (MSAA) and stable
			mat = src.duplicate()
			if mat.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED or mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR \
					or mat.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA:
				mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
			mat.alpha_scissor_threshold = 0.3
			mat.alpha_antialiasing_mode = BaseMaterial3D.ALPHA_ANTIALIASING_ALPHA_TO_COVERAGE_AND_TO_ONE
			if n.ends_with("_hair") or n.ends_with("_beard"):
				mat.anisotropy_enabled = true
				mat.anisotropy = 0.6           # the tangent runs across the strands
				mat.backlight_enabled = true
				var c := src.albedo_color
				mat.backlight = Color(c.r * 0.35, c.g * 0.3, c.b * 0.25)
		elif _has(n, SKIN_KEYS):
			mat = src.duplicate()
			mat.subsurf_scatter_enabled = true
			mat.subsurf_scatter_strength = 0.35 if n.contains("_face") else 0.25
			mat.subsurf_scatter_skin_mode = true
			mat.subsurf_scatter_transmittance_enabled = true
			mat.subsurf_scatter_transmittance_color = Color(0.95, 0.45, 0.35)
			mat.subsurf_scatter_transmittance_depth = 0.1
			mat.clearcoat_enabled = true
			mat.clearcoat = 0.1
			mat.clearcoat_roughness = 0.3
			mat.rim_enabled = true
			mat.rim = 0.12
			mat.rim_tint = 0.6
		elif _ends(n, SOFT_SSS.keys()):
			mat = src.duplicate()
			mat.subsurf_scatter_enabled = true
			for k in SOFT_SSS:
				if n.ends_with(k):
					mat.subsurf_scatter_strength = SOFT_SSS[k]
		elif n.ends_with("_eye"):
			# the older single-material eyeball: a wet specular
			mat = src.duplicate()
			mat.clearcoat_enabled = true
			mat.clearcoat = 1.0
			mat.clearcoat_roughness = 0.05
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
		var m: MeshInstance3D = pair[0]
		var src := m.get_active_material(pair[1]) as StandardMaterial3D
		var use := mat
		if src and src.transparency == BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR and src.albedo_texture:
			# hair cards keep their strand mask (a solid ribbon otherwise)
			use = mat.duplicate()
			use.albedo_texture = src.albedo_texture
			use.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
			use.alpha_scissor_threshold = 0.3
		m.set_surface_override_material(pair[1], use)


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

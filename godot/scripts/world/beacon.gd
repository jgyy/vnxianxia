class_name Beacon
extends Node3D
## Objective marker: a soft pillar of light and a turning rune ring on the ground.

var color := Color(1.0, 0.85, 0.35)
var radius := 1.6
var _ring: MeshInstance3D


static func create(c: Color, r := 1.6) -> Beacon:
	var b := Beacon.new()
	b.color = c
	b.radius = r
	return b


func _ready() -> void:
	var pillar := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.35
	cyl.bottom_radius = 0.6
	cyl.height = 14.0
	cyl.cap_top = false
	cyl.cap_bottom = false
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(color, 0.16)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	cyl.material = mat
	pillar.mesh = cyl
	pillar.position.y = 7.0
	pillar.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(pillar)
	_ring = MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = radius - 0.08
	torus.outer_radius = radius
	torus.rings = 48
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_color = color
	rm.emission_enabled = true
	rm.emission = color
	rm.emission_energy_multiplier = 3.0
	torus.material = rm
	_ring.mesh = torus
	# lifted clear of the ground: a ring lying at a few centimetres z-fights
	# with (and dips under) uneven or sloping ground and flickers as the camera moves
	_ring.scale = Vector3(1, 0.3, 1)
	_ring.position.y = 0.14
	_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_ring)
	var motes := Fx.motes(color, 30, Vector3(radius * 0.6, 0.3, radius * 0.6), 3.0, 0.03)
	motes.position.y = 0.3
	add_child(motes)


func _process(delta: float) -> void:
	_ring.rotation.y += delta * 0.6

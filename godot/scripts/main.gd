extends Node3D
## Level bootstrap: HUD, animated spirit crystal and drifting spirit motes.

const HELP := "WASD move · Shift run · Space leap · Tab switch cultivator · E salute · Q cast · RMB/click orbit · Esc release mouse"

@onready var player: CharacterBody3D = $Player

var _crystal: Node3D
var _crystal_base := Vector3.ZERO
var _time := 0.0
var _name_label: Label


func _ready() -> void:
	_build_hud()
	player.character_changed.connect(_on_character_changed)
	_on_character_changed(player.CHARACTERS[player.character_index].name)
	_crystal = find_child("SpiritCrystal", true, false) as Node3D
	if _crystal:
		_crystal_base = _crystal.position
	var formation := find_child("FormationArray", true, false) as Node3D
	if formation:
		formation.add_child(_make_motes(Color(0.5, 0.95, 1.0), 90, Vector3(4, 2.5, 4)))
	var burner := find_child("IncenseBurner", true, false) as Node3D
	if burner:
		var smoke := _make_motes(Color(0.85, 0.85, 0.82, 0.5), 40, Vector3(0.25, 0.1, 0.25))
		smoke.position = Vector3(0, 2.1, 0)
		(smoke.process_material as ParticleProcessMaterial).gravity = Vector3(0, 0.6, 0)
		burner.add_child(smoke)


func _process(delta: float) -> void:
	_time += delta
	if _crystal:
		_crystal.position = _crystal_base + Vector3(0, sin(_time * 1.3) * 0.25, 0)
		_crystal.rotation.y = _time * 0.6


func _make_motes(color: Color, amount: int, extents: Vector3) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = 5.0
	p.preprocess = 5.0
	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	mat.emission_box_extents = extents
	mat.direction = Vector3.UP
	mat.spread = 25.0
	mat.initial_velocity_min = 0.1
	mat.initial_velocity_max = 0.4
	mat.gravity = Vector3(0, 0.15, 0)
	mat.scale_min = 0.5
	mat.scale_max = 1.2
	p.process_material = mat
	var mesh := SphereMesh.new()
	mesh.radius = 0.035
	mesh.height = 0.07
	mesh.radial_segments = 6
	mesh.rings = 3
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.albedo_color = color
	sm.emission_enabled = true
	sm.emission = color
	sm.emission_energy_multiplier = 3.0
	if color.a < 1.0:
		sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mesh.material = sm
	p.draw_pass_1 = mesh
	p.position = Vector3(0, 1.0, 0)
	return p


func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := VBoxContainer.new()
	panel.position = Vector2(16, 12)
	layer.add_child(panel)
	var title := Label.new()
	title.text = "Azure Cloud Sect"
	title.add_theme_font_size_override("font_size", 22)
	title.add_theme_color_override("font_color", Color(0.95, 0.9, 0.75))
	title.add_theme_color_override("font_outline_color", Color(0.1, 0.12, 0.2))
	title.add_theme_constant_override("outline_size", 6)
	panel.add_child(title)
	_name_label = Label.new()
	_name_label.add_theme_color_override("font_outline_color", Color(0.1, 0.12, 0.2))
	_name_label.add_theme_constant_override("outline_size", 5)
	panel.add_child(_name_label)
	var help := Label.new()
	help.text = HELP
	help.add_theme_font_size_override("font_size", 13)
	help.add_theme_color_override("font_outline_color", Color(0.1, 0.12, 0.2))
	help.add_theme_constant_override("outline_size", 4)
	panel.add_child(help)


func _on_character_changed(display_name: String) -> void:
	if _name_label:
		_name_label.text = "Playing as: " + display_name

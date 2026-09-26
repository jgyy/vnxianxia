class_name QuestProp
extends Node3D
## An interactable object (stele, chest, altar...) placed for an objective.

var prop_id := ""
var used := false


static func create(id: String) -> QuestProp:
	var p := QuestProp.new()
	p.prop_id = id
	return p


func _ready() -> void:
	add_to_group("props")
	var glb = Story.world.props.get(prop_id)
	var path := "res://assets/environment/%s.glb" % glb if glb else ""
	if glb and ResourceLoader.exists(path):
		add_child((load(path) as PackedScene).instantiate())
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
		seal.position.y = 0.06
		add_child(seal)

extends Node3D
## A generated map (see tools/maps): environment, level geometry and named
## markers. Adds ambient particles and resolves markers to ground positions.

@export var map_id := ""
@export var display_name := ""
@export var music := ""
## Particle preset: motes, fireflies, petals, embers, snow, none.
@export var ambient := "motes"
## The player is returned to the spawn point when falling below this height.
@export var kill_y := -30.0

var _time := 0.0
var _crystal: Node3D
var _crystal_base := Vector3.ZERO


func _ready() -> void:
	_crystal = find_child("SpiritCrystal", true, false) as Node3D
	if _crystal:
		_crystal_base = _crystal.position
	var formation := find_child("FormationArray", true, false) as Node3D
	if formation and formation.get_parent().name == "Level":
		formation.add_child(Fx.motes(Color(0.5, 0.95, 1.0), 90, Vector3(4, 2.5, 4)))
	for burner in find_children("IncenseBurner*", "Node3D", true, false):
		if burner.get_parent().name != "Level":
			continue
		var smoke := Fx.motes(Color(0.85, 0.85, 0.82, 0.5), 40, Vector3(0.25, 0.1, 0.25))
		smoke.position = Vector3(0, 2.1, 0)
		(smoke.process_material as ParticleProcessMaterial).gravity = Vector3(0, 0.6, 0)
		burner.add_child(smoke)
	var amb := Fx.ambient(ambient)
	if amb:
		amb.name = "Ambient"
		add_child(amb)


func _process(delta: float) -> void:
	_time += delta
	if _crystal:
		_crystal.position = _crystal_base + Vector3(0, sin(_time * 1.3) * 0.25, 0)
		_crystal.rotation.y = _time * 0.6
	var amb := get_node_or_null("Ambient") as Node3D
	var cam := get_viewport().get_camera_3d()
	if amb and cam:
		amb.global_position = cam.global_position


func has_marker(marker: String) -> bool:
	return get_node_or_null("Markers/" + marker) != null


func marker_names() -> PackedStringArray:
	var out := PackedStringArray()
	for m in $Markers.get_children():
		out.append(m.name)
	return out


## World position of a marker, dropped onto the ground below it.
func marker_position(marker: String) -> Vector3:
	var m := get_node_or_null("Markers/" + marker) as Node3D
	if m == null:
		push_warning("map %s has no marker %s" % [map_id, marker])
		return Vector3.ZERO
	return ground_at(m.global_position)


## Snap a point to the first collider below it (searching from 6 m above).
func ground_at(p: Vector3, up := 6.0, down := 60.0) -> Vector3:
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * up, p + Vector3.DOWN * down)
	q.collision_mask = 1
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return p
	return hit.position

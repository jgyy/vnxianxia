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


## True when the marker has walkable ground within reach below it.
func marker_grounded(marker: String) -> bool:
	var m := get_node_or_null("Markers/" + marker) as Node3D
	if m == null:
		return false
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(m.global_position + Vector3.UP * 1.5, m.global_position + Vector3.DOWN * 60.0)
	q.collision_mask = 1
	q.hit_back_faces = false
	return not space.intersect_ray(q).is_empty()


## Snap a point to the ground below it. Probes from just above the point first
## (so tree canopies and roofs overhead are ignored), then from higher up in
## case the point is buried in a slope.
func ground_at(p: Vector3, up := 1.5, down := 60.0) -> Vector3:
	var space := get_world_3d().direct_space_state
	for start in [up, 8.0]:
		var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * start, p + Vector3.DOWN * down)
		q.collision_mask = 1
		q.hit_back_faces = false
		var hit := space.intersect_ray(q)
		if not hit.is_empty():
			return hit.position
	return p


## True when a standing capsule fits at a ground point without touching level geometry.
func is_open(p: Vector3, radius := 0.4) -> bool:
	var shape := CapsuleShape3D.new()
	shape.radius = radius
	shape.height = 1.7
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = shape
	q.transform = Transform3D(Basis(), p + Vector3.UP * 0.95)
	q.collision_mask = 1
	return get_world_3d().direct_space_state.intersect_shape(q, 1).is_empty()


## A walkable, uncluttered spot near `center`, trying the preferred polar
## position first and then spiralling outward/inward until one fits.
func open_spot(center: Vector3, angle: float, dist: float) -> Vector3:
	for k in 24:
		var a := angle + k * 2.39996
		var d := dist if k < 8 else lerpf(1.0, dist + 3.0, fmod(k * 0.37, 1.0))
		var cand := center + Vector3(cos(a) * d, 0, sin(a) * d)
		var g := ground_at(cand)
		if g == cand or absf(g.y - center.y) > 2.0:
			continue
		if is_open(g) and reachable(center, g):
			return g
	return center


## True when a spot can be walked to from `from`: nothing solid between them at
## chest height and no roof overhead (a hollow building's inside passes
## is_open() but is walled off from the objective).
func reachable(from: Vector3, to: Vector3) -> bool:
	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(from + Vector3.UP * 1.1, to + Vector3.UP * 1.1)
	q.collision_mask = 1
	if not space.intersect_ray(q).is_empty():
		return false
	var up := PhysicsRayQueryParameters3D.create(to + Vector3.UP * 0.5, to + Vector3.UP * 12.0)
	up.collision_mask = 1
	return space.intersect_ray(up).is_empty()

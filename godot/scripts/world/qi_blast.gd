extends Area3D
## A travelling ball of qi fired by the player's cast. Damages the first enemy it touches.

var direction := Vector3.FORWARD
var damage := 30.0
var speed := 16.0
var life := 1.8


func _ready() -> void:
	var shape := CollisionShape3D.new()
	var sph := SphereShape3D.new()
	sph.radius = 0.45
	shape.shape = sph
	add_child(shape)
	collision_layer = 0
	collision_mask = 1 | 4
	var core := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.22
	mesh.height = 0.44
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(0.7, 0.95, 1.0)
	mat.emission_enabled = true
	mat.emission = Color(0.4, 0.9, 1.0)
	mat.emission_energy_multiplier = 6.0
	mesh.material = mat
	core.mesh = mesh
	add_child(core)
	var trail := Fx.motes(Color(0.5, 0.95, 1.0), 60, Vector3(0.1, 0.1, 0.1), 0.5, 0.05)
	trail.position = Vector3.ZERO
	trail.local_coords = false
	add_child(trail)
	var light := OmniLight3D.new()
	light.light_color = Color(0.5, 0.9, 1.0)
	light.light_energy = 2.0
	light.omni_range = 4.0
	add_child(light)
	body_entered.connect(_on_body, CONNECT_DEFERRED)


func _physics_process(delta: float) -> void:
	global_position += direction * speed * delta
	life -= delta
	if life <= 0.0:
		queue_free()
		return
	for e in get_tree().get_nodes_in_group("enemies"):
		if not e.dead and global_position.distance_to(e.global_position + Vector3.UP * e.height * 0.5) < 0.6 + e.radius:
			_hit(e)
			return


func _on_body(body: Node) -> void:
	if is_queued_for_deletion() or not is_instance_valid(body):
		return
	if body.is_in_group("enemies"):
		_hit(body)
	elif not body.is_in_group("player"):
		Fx.burst(get_parent(), global_position, Color(0.5, 0.95, 1.0), 24, 3.0)
		queue_free()


func _hit(e: Node) -> void:
	if e.dead:
		return
	e.take_damage(damage, self)
	Fx.burst(get_parent(), global_position, Color(0.5, 0.95, 1.0), 40, 5.0)
	queue_free()

class_name Fx
extends RefCounted
## Small library of procedural particle effects shared by maps, combat and cinematics.


static func _mesh(radius: float, color: Color, energy := 3.0) -> SphereMesh:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	mesh.radial_segments = 6
	mesh.rings = 3
	var sm := StandardMaterial3D.new()
	sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	sm.albedo_color = color
	sm.emission_enabled = true
	sm.emission = color
	sm.emission_energy_multiplier = energy
	sm.vertex_color_use_as_albedo = true
	if color.a < 1.0:
		sm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mesh.material = sm
	return mesh


static func motes(color: Color, amount: int, extents: Vector3, lifetime := 5.0, radius := 0.035) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.amount = amount
	p.lifetime = lifetime
	p.preprocess = lifetime
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
	p.draw_pass_1 = _mesh(radius, color)
	p.position = Vector3(0, 1.0, 0)
	p.visibility_aabb = AABB(-extents - Vector3.ONE * 4, extents * 2 + Vector3.ONE * 8)
	return p


## Camera-following ambient particles for a map.
static func ambient(kind: String) -> GPUParticles3D:
	var p: GPUParticles3D
	match kind:
		"motes":
			p = motes(Color(0.75, 0.95, 1.0, 0.8), 120, Vector3(18, 6, 18), 7.0, 0.025)
		"fireflies":
			p = motes(Color(0.85, 1.0, 0.45), 160, Vector3(20, 3, 20), 6.0, 0.03)
			var m := p.process_material as ParticleProcessMaterial
			m.gravity = Vector3.ZERO
			m.spread = 180.0
			m.turbulence_enabled = true
			m.turbulence_noise_strength = 1.5
		"petals":
			p = motes(Color(1.0, 0.72, 0.82), 140, Vector3(20, 8, 20), 8.0, 0.04)
			var m := p.process_material as ParticleProcessMaterial
			m.gravity = Vector3(0.3, -0.35, 0.1)
			m.direction = Vector3(1, -0.2, 0)
			m.angular_velocity_min = -90
			m.angular_velocity_max = 90
			(p.draw_pass_1 as SphereMesh).height = 0.015
		"embers":
			p = motes(Color(1.0, 0.35, 0.12), 200, Vector3(22, 4, 22), 5.0, 0.03)
			var m := p.process_material as ParticleProcessMaterial
			m.gravity = Vector3(0, 0.5, 0)
			m.turbulence_enabled = true
		"snow":
			p = motes(Color(0.95, 0.97, 1.0), 260, Vector3(22, 8, 22), 8.0, 0.03)
			var m := p.process_material as ParticleProcessMaterial
			m.gravity = Vector3(0, -0.6, 0)
			m.direction = Vector3.DOWN
		_:
			return null
	p.local_coords = false
	p.visibility_aabb = AABB(Vector3(-40, -20, -40), Vector3(80, 40, 80))
	return p


## One-shot burst (hits, pickups, breakthroughs). Frees itself.
static func burst(parent: Node, at: Vector3, color: Color, amount := 40, speed := 4.0, size := 0.05) -> GPUParticles3D:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.explosiveness = 0.95
	p.amount = amount
	p.lifetime = 0.9
	var mat := ParticleProcessMaterial.new()
	mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	mat.emission_sphere_radius = 0.2
	mat.direction = Vector3.UP
	mat.spread = 180.0
	mat.initial_velocity_min = speed * 0.4
	mat.initial_velocity_max = speed
	mat.gravity = Vector3(0, -2.0, 0)
	mat.damping_min = 2.0
	mat.damping_max = 4.0
	mat.scale_min = 0.5
	mat.scale_max = 1.3
	p.process_material = mat
	p.draw_pass_1 = _mesh(size, color, 4.0)
	parent.add_child(p)
	p.global_position = at
	p.emitting = true
	p.finished.connect(p.queue_free)
	return p

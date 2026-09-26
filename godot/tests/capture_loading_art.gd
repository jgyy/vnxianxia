extends SceneTree
## Renders the loading-screen key art for every map into res://ui/loading/<map>.jpg
## (run with a GPU or lavapipe; the results are committed).
##
##   godot --path godot --rendering-driver vulkan -s res://tests/capture_loading_art.gd

## map -> [focus marker, camera offset, look offset, actors (model, marker offset, anim)]
const SHOTS := {
	"sect": ["HallSteps", Vector3(-3.5, 2.2, 13.5), Vector3(0, 2.6, 0),
		[["cultivator_male", Vector3(-0.8, 0, 8), "salute"], ["cultivator_female", Vector3(0.8, 0, 8), "salute"], ["elder_male", Vector3(0, 0, 0.5), "talk"]]],
	"bamboo_forest": ["RuinsGate", Vector3(4.5, 1.8, 9.5), Vector3(0, 1.6, 0),
		[["cultivator_female", Vector3(1.2, 0, 4.5), "cast"], ["spirit_wolf", Vector3(-1.2, 0, 0.5), "attack"]]],
	"qingshi_town": ["MarketSquare", Vector3(-4, 2.0, 6.5), Vector3(0, 1.5, 0),
		[["villager_male", Vector3(1, 0, 0), "talk"], ["villager_female", Vector3(-1, 0, 0.6), "idle"], ["cultivator_male", Vector3(0.2, 0, 2.8), "idle"]]],
	"blood_abyss": ["AltarOfBlood", Vector3(4, 2.2, 8), Vector3(0, 1.8, 0),
		[["blood_patriarch", Vector3(0, 0, 0), "cast"], ["demon_cultivator", Vector3(-2.2, 0, 1.2), "idle"], ["demon_cultivator", Vector3(2.2, 0, 1.2), "idle"]]],
	"sky_isles": ["TribulationPeak", Vector3(-4.5, 2.5, 7.5), Vector3(0, 1.5, 0),
		[["cultivator_male", Vector3(0, 0, 0), "meditate"]]],
}


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	root.size = Vector2i(1280, 720)
	for map_id in SHOTS:
		var s: Array = SHOTS[map_id]
		var map: Node3D = (load("res://scenes/maps/%s.tscn" % map_id) as PackedScene).instantiate()
		root.add_child(map)
		for i in 3:
			await physics_frame
		var focus: Vector3 = map.marker_position(s[0])
		for a in s[3]:
			var m := (load("res://assets/characters/%s.glb" % a[0]) as PackedScene).instantiate() as Node3D
			map.add_child(m)
			load("res://scripts/world/actor_look.gd").apply(m)
			m.global_position = map.ground_at(focus + a[1])
			var to: Vector3 = (focus + s[1]) - m.global_position
			m.rotation.y = atan2(to.x, to.z) - 0.3
			var ap := m.find_child("AnimationPlayer", true, false) as AnimationPlayer
			ap.play(a[2])
			ap.seek(ap.current_animation_length * 0.45, true)
			ap.pause()
		var fill := OmniLight3D.new()
		fill.light_energy = 1.6
		fill.omni_range = 14.0
		fill.light_color = Color(1.0, 0.92, 0.82)
		map.add_child(fill)
		fill.global_position = focus + s[1] * 0.5 + Vector3.UP * 3.0
		var cam := Camera3D.new()
		cam.fov = 55.0
		cam.far = 3000.0
		map.add_child(cam)
		cam.make_current()
		cam.global_position = focus + s[1]
		cam.look_at(focus + s[2])
		for i in 40:
			await process_frame
		await RenderingServer.frame_post_draw
		var img := root.get_viewport().get_texture().get_image()
		var path := ProjectSettings.globalize_path("res://ui/loading/%s.jpg" % map_id)
		img.save_jpg(path, 0.86)
		print("saved ", path)
		map.free()
	quit(0)

extends SceneTree
## Headless smoke test: every GLB imports, characters are rigged and animated,
## and the level is playable (the player stands on the ground, walks, runs,
## switches character and performs actions).
##
##   godot --headless --path godot --import
##   godot --headless --path godot -s res://tests/smoke_test.gd

const REQUIRED_ANIMS := ["idle", "walk", "run", "salute", "cast"]

var failures: PackedStringArray = []


func check(cond: bool, msg: String) -> void:
	if cond:
		print("  ok   ", msg)
	else:
		print("  FAIL ", msg)
		failures.append(msg)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	print("Godot ", Engine.get_version_info().string)
	print("[assets]")
	for dir in ["res://assets/characters", "res://assets/environment"]:
		for file in DirAccess.get_files_at(dir):
			if not file.ends_with(".glb"):
				continue
			var scene := load(dir + "/" + file) as PackedScene
			check(scene != null, "load " + file)
			if scene == null:
				continue
			var inst := scene.instantiate()
			var meshes := inst.find_children("*", "MeshInstance3D", true, false)
			check(meshes.size() > 0, "%s has %d meshes" % [file, meshes.size()])
			if dir.ends_with("characters"):
				_check_character(file, inst)
			inst.free()

	print("[level]")
	var main := (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	var bodies := main.find_children("*", "StaticBody3D", true, false)
	check(bodies.size() > 50, "level has %d static collision bodies" % bodies.size())
	var player := main.get_node("Player") as CharacterBody3D
	for i in 90:
		await physics_frame
	check(player.is_on_floor(), "player lands on the ground (y=%.2f)" % player.global_position.y)
	check(player.current_animation() == "idle", "idle plays at rest (%s)" % player.current_animation())

	var start := player.global_position
	player.scripted_input = Vector2(0, -1)
	for i in 60:
		await physics_frame
	check(player.current_animation() == "walk", "walk plays when moving (%s)" % player.current_animation())
	player.scripted_run = true
	for i in 90:
		await physics_frame
	check(player.current_animation() == "run", "run plays when sprinting (%s)" % player.current_animation())
	var moved := start.distance_to(player.global_position)
	check(moved > 4.0, "player travelled %.1f m toward the gate" % moved)
	check(player.global_position.y > -1.0, "player stays on the plateau (y=%.2f)" % player.global_position.y)
	player.scripted_input = Vector2.ZERO
	player.scripted_run = false
	for i in 60:
		await physics_frame
	player.set_character(1)
	await physics_frame
	check(player.anim != null and player.anim.has_animation("salute"), "female cultivator swapped in")
	player.play_action("salute")
	await physics_frame
	check(player.current_animation() == "salute", "salute action plays (%s)" % player.current_animation())

	print("")
	if failures.is_empty():
		print("SMOKE TEST PASSED")
		quit(0)
	else:
		print("SMOKE TEST FAILED: %d check(s)" % failures.size())
		quit(1)


func _check_character(file: String, inst: Node) -> void:
	var skeletons := inst.find_children("*", "Skeleton3D", true, false)
	check(skeletons.size() == 1, file + " has one Skeleton3D")
	if skeletons.size() == 1:
		var s := skeletons[0] as Skeleton3D
		check(s.get_bone_count() >= 20, "%s skeleton has %d bones" % [file, s.get_bone_count()])
	var ap := inst.find_child("AnimationPlayer", true, false) as AnimationPlayer
	check(ap != null, file + " has an AnimationPlayer")
	if ap:
		for a in REQUIRED_ANIMS:
			check(ap.has_animation(a) and ap.get_animation(a).length > 0.3,
				"%s animation '%s'" % [file, a])

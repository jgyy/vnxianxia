extends SceneTree
## Renders showcase screenshots of the level (needs a GPU or a software
## Vulkan driver such as lavapipe; under CI run inside xvfb-run).
##
##   godot --path godot --rendering-driver vulkan -s res://tests/capture_screenshots.gd -- out_dir

const SHOTS := [
	# name, camera position, look-at target
	["sect_overview", Vector3(46, 34, 78), Vector3(0, 2, -12)],
	["gate_approach", Vector3(3.5, 2.6, 70), Vector3(0, 4, 20)],
	["courtyard", Vector3(-9, 5.5, 22), Vector3(2, 3, -30)],
	["pond_pagoda", Vector3(8, 3.2, 16), Vector3(20, 6, -26)],
	["cliff_edge", Vector3(-40, 3.0, 4), Vector3(-160, 20, 30)],
]

var out_dir := "user://screenshots"


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0]
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _save(name: String) -> void:
	for i in 12:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := out_dir.path_join(name + ".png")
	img.save_png(path)
	print("saved ", path, " ", img.get_size())


func _run() -> void:
	root.size = Vector2i(1280, 720)
	var main := (load("res://scenes/main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	var player := main.get_node("Player") as CharacterBody3D
	for i in 30:
		await physics_frame

	# 1) the game camera behind the player on the processional way
	await _save("gameplay_third_person")

	# 2) free camera establishing shots
	var cam := Camera3D.new()
	cam.far = 3000.0
	cam.fov = 60.0
	main.add_child(cam)
	cam.make_current()
	player.visible = false
	for shot in SHOTS:
		cam.global_position = shot[1]
		cam.look_at(shot[2])
		await _save(shot[0])
	player.visible = true

	# 3) character line-up in the courtyard: both cultivators in each pose
	var stage := Node3D.new()
	main.add_child(stage)
	var poses := [["idle", 0.5], ["walk", 0.3], ["run", 0.2], ["salute", 1.1], ["cast", 1.0]]
	var scenes := [load("res://assets/characters/cultivator_male.glb"), load("res://assets/characters/cultivator_female.glb")]
	var x := -4.4
	for p in poses:
		for s in scenes:
			var c := (s as PackedScene).instantiate() as Node3D
			stage.add_child(c)
			c.global_position = Vector3(x, 0.04, -6.0)
			var ap := c.find_child("AnimationPlayer", true, false) as AnimationPlayer
			ap.play(p[0])
			ap.seek(p[1], true)
			ap.pause()
			x += 0.95
	cam.fov = 38.0
	cam.global_position = Vector3(0, 1.5, 3.4)
	cam.look_at(Vector3(0, 1.0, -6.0))
	await _save("characters_lineup")

	# 4) close portraits
	for c in stage.get_children():
		c.queue_free()
	await process_frame
	var i := 0
	for s in scenes:
		var c := (s as PackedScene).instantiate() as Node3D
		stage.add_child(c)
		c.global_position = Vector3(-0.45 + i * 0.9, 0.04, -6.0)
		var ap := c.find_child("AnimationPlayer", true, false) as AnimationPlayer
		ap.play("idle")
		ap.seek(0.8, true)
		ap.pause()
		i += 1
	cam.fov = 30.0
	cam.global_position = Vector3(0.0, 1.6, -2.8)
	cam.look_at(Vector3(0, 1.25, -6.0))
	await _save("characters_portrait")
	quit(0)

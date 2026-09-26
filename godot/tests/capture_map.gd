extends SceneTree
## Screenshot a generated map from above and from a few of its markers.
##
##   xvfb-run -a godot --path godot --rendering-driver vulkan \
##       -s res://tests/capture_map.gd -- <map_id> <out_dir> [Marker,Marker,...]

var out_dir := "user://map_shots"


func _initialize() -> void:
	_run.call_deferred()


func _save(name: String) -> void:
	for i in 10:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	img.save_png(out_dir.path_join(name + ".png"))
	print("saved ", out_dir.path_join(name + ".png"))


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var map_id: String = args[0] if args.size() > 0 else "sect"
	if args.size() > 1:
		out_dir = args[1]
	DirAccess.make_dir_recursive_absolute(out_dir)
	root.size = Vector2i(1280, 720)
	var map := (load("res://scenes/maps/%s.tscn" % map_id) as PackedScene).instantiate()
	root.add_child(map)
	for i in 5:
		await physics_frame
	var cam := Camera3D.new()
	cam.far = 3000.0
	cam.fov = 60.0
	map.add_child(cam)
	cam.make_current()
	# overview
	var centre := Vector3.ZERO
	var names: PackedStringArray = map.marker_names()
	for n in names:
		centre += map.marker_position(n)
	centre /= maxf(1.0, names.size())
	cam.global_position = centre + Vector3(60, 70, 90)
	cam.look_at(centre)
	await _save(map_id + "_overview")
	cam.global_position = centre + Vector3(0, 140, 1)
	cam.look_at(centre)
	await _save(map_id + "_top")
	var wanted := names
	if args.size() > 2:
		wanted = args[2].split(",")
	for n in wanted:
		var p: Vector3 = map.marker_position(n)
		cam.global_position = p + Vector3(6, 4, 9)
		cam.look_at(p + Vector3(0, 1.2, 0))
		await _save(map_id + "_" + n)
	quit(0)

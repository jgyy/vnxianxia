extends SceneTree
## World workstream: screenshots of a generated map from explicit camera positions.
##
##   xvfb-run -a godot --path godot --rendering-driver vulkan --resolution 1280x720 \
##       -s res://tests/capture_world_shots.gd -- <map_id> <out_dir> name@x,y,z@tx,ty,tz [...]
##
## A position may instead be "Marker+dx,dy,dz" (relative to a marker on the ground).
## With "--flicker" each shot is rendered twice with the camera nudged 2 cm sideways and the
## number of pixels that changed by more than a threshold is printed (z-fighting shows up as
## scattered pixels flipping between two surfaces; a clean frame differs only by the tiny shift).

var out_dir := "user://world_shots"
var map: Node


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame
	await RenderingServer.frame_post_draw


func _vec(s: String) -> Vector3:
	var rel := ""
	if "+" in s:
		rel = s.get_slice("+", 0)
		s = s.get_slice("+", 1)
	var p := s.split(",")
	var v := Vector3(float(p[0]), float(p[1]), float(p[2]))
	if rel != "":
		v += map.marker_position(rel)
	return v


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var map_id: String = args[0]
	out_dir = args[1]
	var flicker := args.has("--flicker")
	DirAccess.make_dir_recursive_absolute(out_dir)
	root.size = Vector2i(1280, 720)
	map = (load("res://scenes/maps/%s.tscn" % map_id) as PackedScene).instantiate()
	root.add_child(map)
	for i in 5:
		await physics_frame
	var cam := Camera3D.new()
	cam.far = 3000.0
	cam.near = 0.08
	cam.fov = 60.0
	map.add_child(cam)
	cam.make_current()
	for spec in args.slice(2):
		if not "@" in spec:
			continue
		var parts: PackedStringArray = spec.split("@")
		var pos := _vec(parts[1])
		var tgt := _vec(parts[2])
		cam.global_position = pos
		cam.look_at(tgt)
		await _frames(12)
		var img := root.get_viewport().get_texture().get_image()
		img.save_jpg(out_dir.path_join("%s_%s.jpg" % [map_id, parts[0]]), 0.9)
		print("saved ", parts[0])
		if flicker:
			var side := cam.global_transform.basis.x * 0.02
			cam.global_position = pos + side
			await _frames(6)
			var img2 := root.get_viewport().get_texture().get_image()
			cam.global_position = pos
			await _frames(6)
			var img3 := root.get_viewport().get_texture().get_image()
			var changed := 0
			var back := 0
			for y in range(0, img.get_height(), 2):
				for x in range(0, img.get_width(), 2):
					var a := img.get_pixel(x, y)
					var b := img2.get_pixel(x, y)
					var c := img3.get_pixel(x, y)
					if absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b) > 0.25:
						changed += 1
					if absf(a.r - c.r) + absf(a.g - c.g) + absf(a.b - c.b) > 0.25:
						back += 1
			print("FLICKER %s: %d px changed after a 2 cm nudge, %d px differ on return (of %d)" % [
				parts[0], changed, back, img.get_width() * img.get_height() / 4])
	quit(0)

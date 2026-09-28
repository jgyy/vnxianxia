extends SceneTree
## World workstream: in-engine check of every exterior map's markers against the real collision.
##
##   godot --headless --path godot -s res://tests/capture_world_check.gd [-- map_id ...]
##
## For each marker: ground under it, a standing capsule fits on that ground, at least 6 of 8 spots
## on a 3.5 m ring are open and level (NPC groups gather there), and ground exists 9 m to the south
## within 3 m of the marker's height (the walkthrough fights from there). Prints one line per problem
## and exits non-zero when any marker fails.

const MAPS := ["sect", "bamboo_forest", "qingshi_town", "blood_abyss", "sky_isles"]
const RING := 3.5


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var maps: Array = args if args.size() > 0 else MAPS
	var bad := 0
	var total := 0
	for map_id in maps:
		var t0 := Time.get_ticks_msec()
		var map: Node = (load("res://scenes/maps/%s.tscn" % map_id) as PackedScene).instantiate()
		root.add_child(map)
		for i in 4:
			await physics_frame
		var load_ms := Time.get_ticks_msec() - t0
		var n := 0
		for m in map.marker_names():
			n += 1
			var node := map.get_node("Markers/" + m) as Node3D
			var probs := PackedStringArray()
			if not map.marker_grounded(m):
				probs.append("no ground")
			else:
				var g: Vector3 = map.ground_at(node.global_position)
				if not map.is_open(g, 0.35):
					probs.append("capsule blocked at %s" % g)
				var ok := 0
				for k in 8:
					var a := TAU * k / 8.0
					var p: Vector3 = map.ground_at(g + Vector3(cos(a), 0, sin(a)) * RING)
					if absf(p.y - g.y) < 1.2 and map.is_open(p, 0.35):
						ok += 1
				if ok < 6:
					probs.append("only %d/8 open spots around" % ok)
				var s: Vector3 = g + Vector3(0, 0.4, 9)
				var gs: Vector3 = map.ground_at(s, 1.5)
				if gs == s or absf(gs.y - g.y) > 3.0:
					probs.append("no level ground 9 m south (%.1f)" % (gs.y - g.y))
			if not probs.is_empty():
				bad += 1
				print("  MARKER %s/%s: %s" % [map_id, m, ", ".join(probs)])
		total += n
		print("%s: %d markers checked, loaded in %d ms" % [map_id, n, load_ms])
		map.queue_free()
		await process_frame
	print("WORLD CHECK: %d of %d markers with problems" % [bad, total])
	quit(1 if bad > 0 else 0)

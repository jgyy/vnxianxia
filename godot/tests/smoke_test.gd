extends SceneTree
## Headless smoke test: every GLB imports with its rig and animations, every
## map has all of its markers on walkable ground, the story's voice lines and
## portraits exist, and a game session plays (walk, run, strike, qi blast,
## meditate, take damage, talk, journal, switch hero).
##
##   godot --headless --path godot --import
##   godot --headless --path godot -s res://tests/smoke_test.gd

var failures: PackedStringArray = []
var EnemyScript: GDScript
var ActorLookScript: GDScript
var story: Node
var gs: Node


func check(cond: bool, msg: String) -> void:
	if cond:
		print("  ok   ", msg)
	else:
		print("  FAIL ", msg)
		failures.append(msg)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	story = root.get_node("/root/Story")
	EnemyScript = load("res://scripts/world/enemy.gd")
	ActorLookScript = load("res://scripts/world/actor_look.gd")
	gs = root.get_node("/root/Game")
	print("Godot ", Engine.get_version_info().string)
	_assets()
	await _maps()
	_story()
	await _session()
	print("")
	if failures.is_empty():
		print("SMOKE TEST PASSED")
		quit(0)
	else:
		print("SMOKE TEST FAILED: %d check(s)" % failures.size())
		quit(1)


func _assets() -> void:
	print("[assets]")
	var world: Dictionary = story.world
	for dir in ["res://assets/characters", "res://assets/environment"]:
		for file in DirAccess.get_files_at(dir):
			if not file.ends_with(".glb"):
				continue
			var scene := load(dir + "/" + file) as PackedScene
			if scene == null:
				check(false, "load " + file)
				continue
			var inst := scene.instantiate()
			var meshes := inst.find_children("*", "MeshInstance3D", true, false)
			if meshes.is_empty():
				check(false, file + " has meshes")
			if dir.ends_with("characters"):
				var model := file.get_basename()
				var anims: Array = world.creature_anims.get(model, world.humanoid_anims)
				var skeletons := inst.find_children("*", "Skeleton3D", true, false)
				var ap := inst.find_child("AnimationPlayer", true, false) as AnimationPlayer
				var ok := skeletons.size() == 1 and ap != null
				for a in anims:
					ok = ok and ap != null and ap.has_animation(a) and ap.get_animation(a).length > 0.3
				var bones: int = (skeletons[0] as Skeleton3D).get_bone_count() if skeletons.size() == 1 else 0
				check(ok, "%s: rig with %d bones, %d animations" % [file, bones, anims.size()])
			inst.free()
	for m in world.models:
		check(ResourceLoader.exists("res://assets/characters/%s.glb" % m), "model %s exists" % m)
	for p in world.props:
		var glb = world.props[p]
		if glb:
			check(ResourceLoader.exists("res://assets/environment/%s.glb" % glb), "prop %s exists" % p)


func _maps() -> void:
	print("[maps]")
	var world: Dictionary = story.world
	for map_id in world.maps:
		var scene := load("res://scenes/maps/%s.tscn" % map_id) as PackedScene
		check(scene != null, "map %s loads" % map_id)
		if scene == null:
			continue
		var map := scene.instantiate()
		root.add_child(map)
		for i in 3:
			await physics_frame
		var bodies := map.find_children("*", "StaticBody3D", true, false)
		var missing := []
		var floating := []
		for marker in world.maps[map_id].markers:
			if not map.has_marker(marker):
				missing.append(marker)
			elif not map.marker_grounded(marker):
				floating.append(marker)
		check(missing.is_empty(), "%s: all %d markers present %s" % [map_id, world.maps[map_id].markers.size(), missing])
		check(floating.is_empty(), "%s: markers stand on ground %s" % [map_id, floating])
		check(bodies.size() > 10, "%s: %d collision bodies" % [map_id, bodies.size()])
		check(map.music != "" and ResourceLoader.exists("res://audio/music/%s.ogg" % map.music), "%s: music '%s'" % [map_id, map.music])
		map.free()


func _story() -> void:
	print("[story]")
	check(story.quests.size() == 100, "%d main quests" % story.quests.size())
	check(story.chapters.size() == 10, "%d chapters" % story.chapters.size())
	var lines := 0
	var missing := []
	var all_lines := []
	for q in story.quests:
		for o in q.objectives:
			all_lines.append_array(o.get("dialogue", []) if o.get("dialogue") else [])
	for c in story.cinematics.values():
		for s in c.shots:
			if s.get("voice"):
				all_lines.append(s)
	for l in all_lines:
		var v: String = l.get("voice", "") if l.get("voice") else ""
		if v == "":
			continue
		var paths := [v]
		if l.get("gendered", false):
			paths = [v.replace(".ogg", "_m.ogg"), v.replace(".ogg", "_f.ogg")]
		for p in paths:
			lines += 1
			if not ResourceLoader.exists(p):
				missing.append(p)
	check(missing.is_empty(), "%d voice files present %s" % [lines, missing.slice(0, 5)])
	var models := {}
	for id in story.npcs:
		models[story.npcs[id].model] = true
	models["cultivator_male"] = true
	models["cultivator_female"] = true
	for m in models:
		check(ResourceLoader.exists("res://ui/portraits/%s.png" % m), "portrait for %s" % m)
	for track in ["title", "battle", "boss", "victory"]:
		check(ResourceLoader.exists("res://audio/music/%s.ogg" % track), "music %s" % track)


func _session() -> void:
	print("[game]")
	gs.fast = true
	gs.reset()
	var game := (load("res://scenes/game.tscn") as PackedScene).instantiate()
	root.add_child(game)
	for i in 3000:
		if not game.busy and game.map != null:
			break
		await physics_frame
	check(game.map != null and gs.map_id == "sect", "game starts in the sect")
	var player: CharacterBody3D = game.player
	for i in 90:
		await physics_frame
	check(player.is_on_floor(), "player lands on the ground (y=%.2f)" % player.global_position.y)
	check(game.runner.state in ["active", "busy"], "quest runner active on %s" % gs.quest().get("id", "?"))
	var start := player.global_position
	player.scripted_input = Vector2(0, -1)
	for i in 50:
		await physics_frame
	check(player.current_animation() == "walk", "walk plays when moving (%s)" % player.current_animation())
	player.scripted_run = true
	for i in 70:
		await physics_frame
	check(player.current_animation() == "run", "run plays when sprinting (%s)" % player.current_animation())
	check(start.distance_to(player.global_position) > 4.0, "player travelled %.1f m" % start.distance_to(player.global_position))
	player.scripted_input = Vector2.ZERO
	player.scripted_run = false
	for i in 40:
		await physics_frame
	# combat against a training puppet
	var e = EnemyScript.create("training_puppet")
	game.map.add_child(e)
	e.global_position = player.global_position + player.facing() * 1.5
	for i in 5:
		await physics_frame
	var hp0: float = e.hp
	player.strike()
	await physics_frame
	check(player.current_animation() == "attack", "strike plays attack (%s)" % player.current_animation())
	for i in 40:
		await physics_frame
	check(e.hp < hp0, "palm strike damages the puppet (%.0f -> %.0f)" % [hp0, e.hp])
	var qi0: float = player.qi
	player._action_lock = 0.0
	player.blast()
	check(player.qi < qi0, "qi blast spends qi")
	for i in 60:
		await physics_frame
	if is_instance_valid(e):
		e.take_damage(1e6)
	check(not is_instance_valid(e) or e.dead, "puppet can be defeated")
	var hp_before: float = player.hp
	player.take_damage(10.0)
	check(player.hp < hp_before, "player takes damage")
	for i in 30:
		await physics_frame
	player.start_meditation()
	check(player.meditating and player.current_animation() == "meditate", "meditation pose (%s)" % player.current_animation())
	for i in 60:
		await physics_frame
	check(player.hp > hp_before - 10.0, "meditation restores vitality")
	player.stop_meditation()
	# a voiced line through the dialogue box
	var line: Dictionary = story.quests[0].objectives[1].dialogue[0]
	check(ResourceLoader.load(story.voice_path(line)) is AudioStream, "voice line loads as audio")
	await game.converse([line])
	check(not game.dialogue.active and player.controls_enabled, "dialogue finishes and returns control")
	game.journal.show_page("quest")
	check(game.journal.open and paused, "journal pauses the game")
	game.journal.close()
	check(not paused, "journal closes")
	player.set_character(1)
	await physics_frame
	check(gs.character == 1 and player.anim.has_animation("salute"), "Su Yue swapped in")
	check(player.play_action("salute"), "salute action plays")
	game.queue_free()

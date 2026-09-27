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
	await _stairs()
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
	check(story.quests.size() == 2000, "%d main quests" % story.quests.size())
	check(story.chapters.size() == 100, "%d chapters" % story.chapters.size())
	check(story.volumes.size() == 10, "%d volumes" % story.volumes.size())
	check(story.load_msec < 3000, "story.json parsed in %d ms" % story.load_msec)
	var realms: Array = story.world.realms
	check(realms.size() == 12 and realms[6] == "Spirit Severing" and realms[-1] == "Immortal Ascension",
		"%d realms (Mortal, ten major stages, Immortal Ascension)" % realms.size())
	var tribs := 0
	var choices := 0
	var cond_lines := 0
	for q in story.quests:
		for o in q.objectives:
			if o.type == "tribulation":
				tribs += 1
			if o.get("choices"):
				choices += 1
			for l in (o.get("dialogue", []) if o.get("dialogue") else []):
				if l.get("cond"):
					cond_lines += 1
		if q.rewards.get("realm") and q.rewards.realm != "Immortal Ascension":
			var has := false
			for o in q.objectives:
				has = has or o.type == "tribulation"
			check(has, "%s breaks through with a tribulation" % q.id)
	check(tribs == 11, "%d tribulations" % tribs)
	check(choices > 200 and cond_lines > 100, "%d moral choices, %d conditional lines" % [choices, cond_lines])
	for v in story.volumes:
		check(v.title == realms[int(v.number)] and (v.chapters as Array).size() == 10,
			"volume %d: %s, %d chapters" % [int(v.number), v.title, (v.chapters as Array).size()])
	check(story.quests[-1].rewards.realm == "Immortal Ascension", "the last quest grants Immortal Ascension")
	check(story.legacy_index(40) == 219 and story.quest(219).title == "Foundation Establishment",
		"original quest 40 is quest %d of the saga" % (story.legacy_index(40) + 1))
	var unvoiced := 0
	for q in story.quests:
		for o in q.objectives:
			for l in (o.get("dialogue", []) if o.get("dialogue") else []):
				if story.voice_path(l) == "":
					unvoiced += 1
	check(unvoiced > 1000, "%d text-only lines resolve to no voice file" % unvoiced)
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
	var steps0: int = player.footsteps
	for i in 50:
		await physics_frame
	check(player.current_animation() == "walk", "walk plays when moving (%s)" % player.current_animation())
	var walk_len: float = player.anim.get_animation("walk").length
	for i in 120:
		await physics_frame
	var want_steps := 2.0 * (170.0 / 60.0) / walk_len
	check(absf((player.footsteps - steps0) - want_steps) <= 2.0,
		"footfalls follow the walk cycle (%d in %.1f s, cycle %.2f s)" % [player.footsteps - steps0, 170.0 / 60.0, walk_len])
	check(absf(player.anim.speed_scale - 1.0) < 0.08,
		"walk at %.2f m/s plays at speed_scale %.2f (feet planted)" % [Vector2(player.velocity.x, player.velocity.z).length(), player.anim.speed_scale])
	player.scripted_run = true
	for i in 70:
		await physics_frame
	check(player.current_animation() == "run", "run plays when sprinting (%s)" % player.current_animation())
	check(absf(player.anim.speed_scale - 1.0) < 0.08,
		"run at %.2f m/s plays at speed_scale %.2f (feet planted)" % [Vector2(player.velocity.x, player.velocity.z).length(), player.anim.speed_scale])
	check(player.gait_for(2.8, "walk") == "walk" and player.gait_for(2.8, "run") == "run"
		and player.gait_for(3.3, "walk") == "run" and player.gait_for(2.3, "run") == "walk",
		"walk / run switch with hysteresis (no thrash at the threshold)")
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
	check(player.current_animation() in ["attack", "palm_1"], "strike plays a palm strike (%s)" % player.current_animation())
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
	check(player.meditating and player.current_animation().begins_with("meditate"), "meditation pose (%s)" % player.current_animation())
	for i in 60:
		await physics_frame
	check(player.hp > hp_before - 10.0, "meditation restores vitality")
	player.stop_meditation()
	# a voiced line through the dialogue box
	var line: Dictionary = story.quests[0].objectives[1].dialogue[0]
	check(ResourceLoader.load(story.voice_path(line)) is AudioStream, "voice line loads as audio")
	await game.converse([line])
	check(not game.dialogue.active and player.controls_enabled, "dialogue finishes and returns control")
	await _hall_steps(game, player)
	await _dialogue_input(game, player)
	await _dialogue_fits(game)
	await _group_talk(game, player)
	_pickups_and_props(game)
	# a text-only line of a new chapter, played at normal speed: it must advance by itself
	var plain := {"speaker": "senior_wei", "text": "Have you eaten? You should eat.", "voice": null}
	gs.fast = false
	var t0 := Time.get_ticks_msec()
	await game.converse([plain])
	gs.fast = true
	var waited := (Time.get_ticks_msec() - t0) / 1000.0
	check(not game.dialogue.active and waited > 1.0 and waited < 12.0, "text-only line auto-advances (%.1fs)" % waited)
	# cultivation: ten minor stages per realm and their labels
	var r0: int = gs.realm
	var seen := []
	gs.stage_changed.connect(func(r, st): seen.append([r, st]))
	gs.realm = 3
	gs.stage = 1
	gs.set_stage(7)
	check(gs.realm_label() == "Core Formation · 7th Layer (Late)", "minor stage label: %s" % gs.realm_label())
	gs.set_stage(10)
	check(gs.realm_label() == "Core Formation · Great Perfection", "great perfection label: %s" % gs.realm_label())
	var p10: float = gs.power()
	gs.set_realm("Nascent Soul")
	check(gs.stage == 1 and gs.realm_label() == "Nascent Soul · 1st Layer (Early)", "a breakthrough starts at the 1st layer")
	check(gs.power() > p10 and p10 > 3.0, "power grows with minor and major stages (%.1f -> %.1f)" % [p10, gs.power()])
	check(seen == [[3, 7], [3, 10], [4, 1]], "stage_changed(realm, stage) signals %s" % [seen])
	check(story.stage_name(3, 4) == "4th Layer" and story.stage_name(0, 3) == "", "Story.stage_name")
	gs.realm = r0
	gs.stage = 0
	# shards start mid-story with realm, stage and rewards applied
	gs.start_at(story.chapter_first(47))
	check(gs.realm == 5 and gs.stage == 6, "chapter 47 starts at %s" % gs.realm_label())
	gs.start_at(story.chapter_first(52))
	check(gs.realm == 6 and gs.stage == 1, "chapter 52 starts at %s" % gs.realm_label())
	# alignment, conditions, choices and a save/load round trip
	gs.start_at(story.chapter_first(12))
	check(gs.alignment() == "neutral_neutral" and gs.alignment_name() == "Walker of the Middle Way", "alignment starts true neutral")
	gs.shift_alignment(30, -40)
	check(gs.alignment() == "lawful_evil" and gs.alignment_name() == "Iron-Handed Tyrant", "alignment moves: %s" % gs.alignment_name())
	check(gs.cond_ok({"align": "*_evil"}) and not gs.cond_ok({"align": "*_good"}) and gs.cond_ok({"align_law": ">=30"})
		and gs.cond_ok({"min_realm": "Qi Condensation"}) and not gs.cond_ok({"min_realm": "Core Formation"}),
		"conditions follow alignment and realm")
	var lines := [{"speaker": "narrator", "text": "a"}, {"speaker": "narrator", "text": "b", "cond": {"align": "*_good"}},
		{"speaker": "narrator", "text": "c", "cond": {"align": "lawful_*"}}]
	check(story.visible_lines(lines).map(func(l): return l.text) == ["a", "c"], "conditional lines are filtered")
	gs.apply_choice({"align": {"law": -10, "good": 20}, "reward": {"xp": 5, "items": {"medicine": 1}},
		"flag": "smoke_flag", "attitude": {"senior_han": 1}}, 1)
	check(gs.flags.has("smoke_flag") and gs.cond_ok({"flag": "smoke_flag"}) and gs.cond_ok({"likes": "senior_han"}),
		"a choice sets flags and attitudes")
	var saved: Dictionary = JSON.parse_string(JSON.stringify(gs.save_dict()))
	var want := [gs.law, gs.good, gs.alignment(), gs.realm, gs.stage, gs.quest_index]
	gs.start_at(0)
	gs.load_dict(saved)
	check([gs.law, gs.good, gs.alignment(), gs.realm, gs.stage, gs.quest_index] == want and gs.flags.has("smoke_flag")
		and gs.choices.size() == 1, "save/load keeps alignment, flags, choices and cultivation %s" % [want])
	var pick: int = await game.choose("Smoke?", ["a", "b", "c"])
	check(pick >= 0 and pick < 3, "a choice is made in fast mode (%d)" % pick)
	gs.start_at(0)
	await _tribulation(game, player)
	game.journal.show_page("quest")
	check(game.journal.open and paused, "journal pauses the game")
	# every journal page renders, late in the saga too (volumes, chronicle, cultivation)
	var saved_q: int = gs.quest_index
	gs.quest_index = story.chapter_first(57) + 3
	var t_start := Time.get_ticks_msec()
	for page in ["_show_story", "_show_chronicle", "_show_cultivation", "_show_quest"]:
		game.journal.call(page)
		check(game.journal._content.get_parsed_text().length() > 40, "journal %s renders at quest %d" % [page, gs.quest_index + 1])
	check(Time.get_ticks_msec() - t_start < 2000, "journal pages render in %d ms" % (Time.get_ticks_msec() - t_start))
	gs.quest_index = saved_q
	game.journal.close()
	check(not paused, "journal closes")
	player.set_character(1)
	await physics_frame
	check(gs.character == 1 and player.anim.has_animation("salute"), "Su Yue swapped in")
	check(player.play_action("salute"), "salute action plays")
	game.queue_free()
	await _title()


## A heavenly tribulation with a wave: meditate through the bolts, strike down the beasts.
func _tribulation(game: Node, player: CharacterBody3D) -> void:
	var t = load("res://scripts/world/tribulation.gd").create({"bolts": 4, "waves": [{"enemy": "tribulation_beast", "count": 1, "after": 2}]}, 4)
	game.map.add_child(t)
	t.global_position = player.global_position
	var ok := [false]
	t.survived.connect(func(): ok[0] = true)
	var struck := [0]
	t.volley_struck.connect(func(_d, _n): struck[0] += 1)
	await physics_frame
	t.begin(player)
	for i in 1500:
		if ok[0]:
			break
		for e in t.enemies:
			if is_instance_valid(e) and not e.dead:
				e.take_damage(1e9)
		if not player.meditating and player.is_on_floor():
			player.start_meditation()
		await physics_frame
	check(ok[0] and struck[0] == 4 and player.hp > 0.0, "tribulation survived by meditating (%d volleys, hp %.0f)" % [struck[0], player.hp])
	player.stop_meditation()
	t.queue_free()


## The title screen builds its volume -> chapter picker.
func _title() -> void:
	print("[title]")
	var title := (load("res://scenes/title.tscn") as PackedScene).instantiate()
	root.add_child(title)
	for i in 5:
		await physics_frame
	title._show_volume(5)
	await process_frame
	var n := 0
	for c in title._chapter_list.get_children():
		if not c.is_queued_for_deletion():
			n += 1
	check(n == 10, "chapter select lists %d chapters of volume V" % n)
	check(title._vol_title.text == "Volume V · Soul Transformation", "volume title: %s" % title._vol_title.text)
	title.queue_free()
	await process_frame


func _box(parent: Node3D, center: Vector3, size: Vector3) -> void:
	var b := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = size
	shape.shape = bs
	b.add_child(shape)
	parent.add_child(b)
	b.global_position = center


## Stairs, a curb and a wall on flat ground: the player walks up and runs back
## down the stairs without jumping (or falling), steps onto the curb, is
## stopped by the wall; an enemy chases up the stairs.
func _stairs() -> void:
	print("[stairs]")
	gs.fast = true
	var w := Node3D.new()
	root.add_child(w)
	_box(w, Vector3(0, -0.5, 0), Vector3(60, 1, 80))
	# six 0.22 m risers with 0.32 m treads toward -Z, then a landing
	for i in 6:
		_box(w, Vector3(0, 0.11 * (i + 1), -8.0 - 0.32 * i), Vector3(4, 0.22 * (i + 1), 10))
	# a 0.4 m curb and a 0.7 m wall to either side
	_box(w, Vector3(12, 0.2, -8), Vector3(4, 0.4, 10))
	_box(w, Vector3(-12, 0.35, -8), Vector3(4, 0.7, 10))
	var player = (load("res://scenes/player.tscn") as PackedScene).instantiate()
	w.add_child(player)
	for lane in [[0.0, 1.32, "six 0.22 m stairs"], [12.0, 0.4, "a 0.4 m curb"], [-12.0, 0.0, "a 0.7 m wall (not climbed)"]]:
		player.place_at(Vector3(lane[0], 0.05, 0.0))
		player._yaw = 0.0
		player.scripted_input = Vector2.ZERO
		player.scripted_run = false
		for i in 10:
			await physics_frame
		player.scripted_input = Vector2(0, -1)
		var max_vy := 0.0
		var air := 0
		for i in 300:
			await physics_frame
			max_vy = maxf(max_vy, player.velocity.y)
			if not player.is_on_floor():
				air += 1
		var top: float = player.global_position.y
		check(absf(top - lane[1]) < 0.08 and max_vy < 1.0,
			"walking up %s: reached y=%.2f (want %.2f), no jump (max vy %.2f, %d frames off the floor)" % [lane[2], top, lane[1], max_vy, air])
	# back down the stairs at a run: no fall, no fall animation
	player.place_at(Vector3(0, 1.4, -13.0))
	player.scripted_input = Vector2.ZERO
	for i in 20:
		await physics_frame
	player.scripted_input = Vector2(0, 1)
	player.scripted_run = true
	var longest_air := 0
	var air_run := 0
	var fell := false
	for i in 150:
		await physics_frame
		air_run = 0 if player.is_grounded() else air_run + 1
		longest_air = maxi(longest_air, air_run)
		fell = fell or player.current_animation() in ["fall", "jump_air", "jump_land", "landing_hard"]
	check(player.global_position.y < 0.05 and longest_air <= 6 and not fell,
		"running down the stairs keeps the feet on the steps (at most %d frames airborne, fall anim %s)" % [longest_air, fell])
	# an enemy chases the player up the stairs
	player.place_at(Vector3(0, 1.4, -14.0))
	player.scripted_input = Vector2.ZERO
	player.scripted_run = false
	var e = EnemyScript.create("bandit")
	w.add_child(e)
	e.global_position = Vector3(0.0, 0.1, 1.0)
	var gait_ok := true
	for i in 400:
		await physics_frame
		if e.anim.current_animation in ["walk", "run"]:
			var authored: float = 4.6 if e.anim.current_animation == "run" else 1.6
			var want := maxf(Vector2(e.velocity.x, e.velocity.z).length() / authored, 0.05)
			gait_ok = gait_ok and absf(e.anim.speed_scale - want) < 0.05
		if e.global_position.y > 1.2:
			break
	check(e.global_position.y > 1.2, "an enemy climbs the stairs after the player (y=%.2f)" % e.global_position.y)
	check(gait_ok, "a humanoid enemy's walk / run is speed-scaled to its ground speed")
	w.queue_free()
	await physics_frame


## On the real sect map: from the foot of the main hall's steps up to its door, walking.
func _hall_steps(game: Node, player: CharacterBody3D) -> void:
	var map: Node = game.map
	if not (map.has_marker("HallSteps") and map.has_marker("MainHall")):
		check(false, "sect has HallSteps and MainHall markers")
		return
	var from: Vector3 = map.marker_position("HallSteps")
	var to: Vector3 = map.marker_position("MainHall")
	# people standing on the steps would block the walk: step them aside for the test
	var moved := {}
	for n in game.npcs.values():
		moved[n] = n.global_position
		n.global_position += Vector3(0, -200, 0)
	player.place_at(from + Vector3.UP * 0.1)
	var d := to - from
	player._yaw = atan2(-d.x, -d.z)
	player.scripted_input = Vector2.ZERO
	for i in 10:
		await physics_frame
	player.scripted_input = Vector2(0, -1)
	var max_vy := 0.0
	var best := INF
	for i in int(Vector2(d.x, d.z).length() / 1.6 * 60.0) + 240:
		await physics_frame
		max_vy = maxf(max_vy, player.velocity.y)
		var p: Vector3 = player.global_position
		best = minf(best, Vector2(p.x - to.x, p.z - to.z).length())
		# keep heading for the door
		var r := to - p
		player._yaw = atan2(-r.x, -r.z)
		if best < 0.9:
			break
	player.scripted_input = Vector2.ZERO
	var pp: Vector3 = player.global_position
	check(best < 1.5 and absf(pp.y - to.y) < 0.5 and max_vy < 1.0,
		"walked up the main hall steps on sect.tscn (%.1f m climbed, %.1f m short of the door, max vy %.2f)" % [pp.y - from.y, best, max_vy])
	for n in moved:
		if is_instance_valid(n):
			n.global_position = moved[n]
	for i in 20:
		await physics_frame


func _wait_ms(ms: int) -> void:
	await create_timer(ms / 1000.0).timeout


func _key(ev_key: int, pressed: bool) -> InputEventKey:
	var ev := InputEventKey.new()
	ev.keycode = ev_key
	ev.physical_keycode = ev_key
	ev.pressed = pressed
	return ev


func _press(ev_key: int, twice := false) -> void:
	root.push_input(_key(ev_key, true))
	if twice:
		root.push_input(_key(ev_key, true))     # a doubled / bounced key event
	root.push_input(_key(ev_key, false))


## Text shows at once; each press advances exactly one line; the press that
## ends a conversation never jumps, interacts or starts it again.
func _dialogue_input(game: Node, player: CharacterBody3D) -> void:
	print("[dialogue]")
	gs.fast = false
	var dlg = game.dialogue
	var seen := []
	var cb := func(sp): seen.append(sp)
	dlg.line_started.connect(cb)
	var lines := [{"speaker": "senior_wei", "text": "One. A line long enough to have wrapped over two rows of the box, had it been typed."},
		{"speaker": "player", "text": "Two."}, {"speaker": "senior_wei", "text": "Three."}]
	var state := {"done": false}
	var talk := func():
		await game.converse(lines)
		state.done = true
	talk.call()
	await process_frame
	check(dlg.active and seen.size() == 1 and dlg._text.visible_characters == -1 and dlg._text.visible_ratio >= 1.0,
		"the whole line shows at once (no typewriter)")
	await _wait_ms(400)
	check(seen.size() == 1, "a line waits for the player (%d lines shown)" % seen.size())
	_press(KEY_E, true)
	await _wait_ms(150)
	check(seen.size() == 2, "one press (even a doubled key event) advances exactly one line (%d)" % seen.size())
	_press(KEY_SPACE)
	await _wait_ms(150)
	check(seen.size() == 3 and not state.done, "Space advances one line too (%d)" % seen.size())
	var y0: float = player.global_position.y
	_press(KEY_SPACE)
	for i in 20:
		await physics_frame
	check(state.done and not dlg.active, "the last press ends the conversation")
	check(player.global_position.y - y0 < 0.05 and player.velocity.y < 0.5 and player.is_on_floor(),
		"the press that closed the dialogue did not become a jump")
	# a hurried E right after the end must not start another conversation
	var npc: Node3D = null
	for n in game.npcs.values():
		npc = n
		break
	if npc:
		player.place_at(game.map.ground_at(npc.global_position + npc.global_basis.z * 1.3) + Vector3.UP * 0.05)
		await physics_frame
		talk = func():
			await game.converse([{"speaker": npc.npc_id, "text": "Again?"}], npc)
			state.done = true
		state.done = false
		talk.call()
		await _wait_ms(150)
		_press(KEY_E)
		for i in 4:
			await process_frame
		check(state.done and not dlg.active, "E closes the bark")
		_press(KEY_E)
		for i in 6:
			await process_frame
		check(not dlg.active, "the same E press (or a hurried second one) does not reopen the conversation")
	# two conversations started together take turns instead of mixing lines
	var order := []
	var a := func():
		await game.converse([{"speaker": "narrator", "text": "A1"}, {"speaker": "narrator", "text": "A2"}])
		order.append("A")
	var b := func():
		await game.converse([{"speaker": "narrator", "text": "B1"}])
		order.append("B")
	a.call()
	b.call()
	var texts := []
	for k in 3:
		await _wait_ms(150)
		texts.append(dlg._text.get_parsed_text())
		_press(KEY_ENTER)
	for i in 8:
		await process_frame
	check(order == ["A", "B"] and texts == ["A1", "A2", "B1"], "overlapping conversations queue (%s %s)" % [order, texts])
	dlg.line_started.disconnect(cb)
	gs.fast = true
	for i in 30:
		await physics_frame


## The dialogue box sits just above the bottom edge and never leaves the
## screen: a long wrapped prompt with four long choices, at several window sizes.
func _dialogue_fits(game: Node) -> void:
	gs.fast = false
	var dlg = game.dialogue
	var long_text := "Elder Hua lowers her voice. " + "The herbs remember every hand that pulled them, and so do the people who planted them. ".repeat(3)
	var opts := []
	for k in 4:
		opts.append("Option %d: a long answer that runs on and on, the way people talk when they are not sure of themselves at all." % (k + 1))
	var res := {"i": -1}
	var pick := func():
		res.i = await dlg.choose(long_text, opts)
	pick.call()
	var sizes := [Vector2i(1280, 720), Vector2i(1024, 768), Vector2i(1920, 1080), Vector2i(1280, 720)]
	for sz in sizes:
		root.size = sz
		for i in 4:
			await process_frame
		var vr: Rect2 = root.get_visible_rect()
		var r: Rect2 = dlg.panel_rect()
		var inside := r.position.y >= vr.position.y - 0.5 and r.end.y <= vr.end.y + 0.5 and r.position.x >= vr.position.x - 0.5 \
			and r.end.x <= vr.end.x + 0.5
		var gap := vr.end.y - r.end.y
		check(inside and gap <= dlg.BOTTOM_MARGIN + 1.0, "dialogue box inside the %s view (box %s, %.0f px above the bottom)" % [vr.size, r, gap])
	await _wait_ms(400)
	_press(KEY_4)
	for i in 4:
		await process_frame
	check(res.i == 3, "key 4 picks the fourth choice (%d)" % res.i)
	gs.fast = true


## A three-participant conversation (the talk target, two NPCs listed in the
## objective's `with`, the player): the group gathers around the target, the
## speaker gestures under an over-the-shoulder camera, and the extras leave again.
func _group_talk(game: Node, player: CharacterBody3D) -> void:
	print("[group conversation]")
	var map: Node = game.map
	var home_here := []
	var elsewhere := []
	for id in story.npcs:
		var h = story.npcs[id].get("home")
		if h and h.map == "sect" and map.has_marker(h.marker) and game._present(story.npcs[id]):
			home_here.append(id)
		elif h == null or h.map != "sect":
			elsewhere.append(id)
	if home_here.size() < 2 or elsewhere.is_empty():
		check(false, "enough NPCs for a group conversation")
		return
	var target: String = home_here[0]
	var ambient_guest: String = home_here[1]
	var guest: String = elsewhere[0]
	var o := {"type": "talk", "map": "sect", "npc": target, "at": null, "text": "Speak with the group",
		"with": [ambient_guest, guest],
		"dialogue": [{"speaker": target, "text": "Everyone is here."}, {"speaker": ambient_guest, "text": "Not quite."},
			{"speaker": guest, "text": "I came a long way for this."}, {"speaker": "player", "text": "Then let us begin."},
			{"speaker": target, "text": "Good."}]}
	var runner: Node = game.runner
	runner.clear()
	runner.state = "active"
	runner.stage(o)
	var t: Node3D = runner.target_npc
	var party: Array = runner.party
	check(party.size() == 2, "both NPCs listed in `with` stand in (%d)" % party.size())
	var ppl: Array = [t]
	ppl.append_array(party)
	for i in 60:
		await process_frame
	var centre := Vector3.ZERO
	for n in ppl:
		centre += n.global_position / ppl.size()
	var spaced := true
	var near := true
	var grounded := true
	var facing := true
	for n in party:
		near = near and n.global_position.distance_to(t.global_position) < 4.0
		grounded = grounded and absf(map.ground_at(n.global_position).y - n.global_position.y) < 0.1
		for m in ppl:
			if m != n and Vector2(m.global_position.x - n.global_position.x, m.global_position.z - n.global_position.z).length() < 0.75:
				spaced = false
		var to: Vector3 = centre - n.global_position
		to.y = 0.0
		facing = facing and (to.length() < 0.3 or n.global_basis.z.dot(to.normalized()) > 0.5)
	check(near and spaced and grounded and facing, "the group stands around the target, apart, on the ground, facing in (near %s spaced %s ground %s facing %s)" % [near, spaced, grounded, facing])
	# talk: record who gestures and where the camera looks on every line
	var log := []
	var cb := func(sp):
		var cam: Camera3D = player.get_viewport().get_camera_3d()
		var node: Node3D = player if sp == "player" else game.find_npc(sp)
		var talking := []
		for n in ppl:
			if is_instance_valid(n) and n.anim and n.anim.current_animation == "talk":
				talking.append(n.npc_id)
		var head: Vector3 = node.global_position + Vector3.UP * 1.5
		var looks: float = (-cam.global_basis.z).dot((head - cam.global_position).normalized())
		log.append({"sp": sp, "cam": cam == game.conversation.cam, "talking": talking, "looks": looks,
			"dist": cam.global_position.distance_to(head)})
	# recorded after the scene has reacted to the line (connected after it)
	game.dialogue.line_started.connect(cb)
	player.place_at(map.ground_at(t.global_position + t.global_basis.z * 1.4) + Vector3.UP * 0.05)
	for i in 3:
		await physics_frame
	game._on_interact()
	for i in 20:
		await process_frame
	game.dialogue.line_started.disconnect(cb)
	var cams_ok := log.size() == 5
	var talk_ok := true
	for e in log:
		cams_ok = cams_ok and e.cam and e.looks > 0.85 and e.dist < 5.5
		if e.sp != "player":
			talk_ok = talk_ok and e.talking == [e.sp]
		else:
			talk_ok = talk_ok and e.talking.is_empty()
	check(cams_ok, "the conversation camera frames each speaker %s" % [log.map(func(e): return "%s %s %.2f %.1fm" % [e.sp, e.cam, e.looks, e.dist])])
	check(talk_ok, "only the speaker gestures %s" % [log.map(func(e): return e.talking)])
	check(player.get_viewport().get_camera_3d() == player.camera and player.controls_enabled, "the gameplay camera and controls come back")
	check(game.find_npc(guest) == null, "the NPC brought in for the conversation leaves afterwards")
	var amb: Node3D = game.find_npc(ambient_guest)
	var home_pos: Vector3 = map.marker_position(story.npcs[ambient_guest].home.marker)
	check(amb != null and amb.global_position.distance_to(home_pos) < 0.6, "an NPC who lives here goes back home")
	for i in 20:
		await physics_frame


## Pickups use their item model when it exists (a glowing primitive otherwise);
## props stand on the ground and their reach grows with their size.
func _pickups_and_props(game: Node) -> void:
	var PickupScript: GDScript = load("res://scripts/world/pickup.gd")
	var PropScript: GDScript = load("res://scripts/world/prop.gd")
	var n_models := 0
	var n_items := 0
	for item in story.world.items:
		n_items += 1
		var path: String = PickupScript.model_path(item)
		if path != "":
			n_models += 1
		if not (path == "" or path.begins_with(story.world.item_model_dir)):
			check(false, "pickup model path for %s: %s" % [item, path])
	print("  (%d of %d items have a model)" % [n_models, n_items])
	var at: Vector3 = game.map.marker_position("FormationArray") + Vector3(3, 0, 3)
	for item in ["spirit_herb", "wolf_fang"]:
		var p = PickupScript.create(item)
		game.map.add_child(p)
		p.global_position = game.map.ground_at(at)
		check(p._body != null and p._body.position.y > 0.3, "pickup %s hovers above the ground (%s)" % [item, PickupScript.model_path(item)])
		p.queue_free()
	var n_props := 0
	var bad := []
	for id in story.world.props:
		var glb = story.world.props[id]
		if glb == null or not ResourceLoader.exists("res://assets/environment/%s.glb" % glb):
			continue
		var pr = PropScript.create(id)
		game.map.add_child(pr)
		pr.global_position = game.map.ground_at(at + Vector3(0, 0, 10))
		var box: AABB = pr._local_aabb(pr)
		n_props += 1
		if not (pr.footprint() > 0.1 and box.position.y > -0.55 and box.position.y < 0.05):
			bad.append("%s base %.2f" % [id, box.position.y])
		var ap: Vector3 = pr.approach_point(game.map)
		if not (pr.edge_distance(ap) < pr.REACH and pr.edge_distance(ap) > 0.2):
			bad.append("%s approach %.2f m from its outline" % [id, pr.edge_distance(ap)])
		pr.queue_free()
	check(bad.is_empty(), "%d quest props stand on the ground and can be walked up to %s" % [n_props, bad])

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
	check(story.quests.size() == 1000, "%d main quests" % story.quests.size())
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
	check(story.legacy_index(40) == 109 and story.quest(109).title == "Foundation Establishment",
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
	check(gs.alignment() == "neutral_neutral" and gs.alignment_name() == "True Neutral", "alignment starts true neutral")
	gs.shift_alignment(30, -40)
	check(gs.alignment() == "lawful_evil" and gs.alignment_name() == "Lawful Evil", "alignment moves: %s" % gs.alignment_name())
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

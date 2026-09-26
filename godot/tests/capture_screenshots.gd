extends SceneTree
## Renders showcase screenshots of the game (needs a GPU or a software Vulkan
## driver such as lavapipe; under CI run inside xvfb-run).
##
##   godot --path godot --rendering-driver vulkan -s res://tests/capture_screenshots.gd -- out_dir

var out_dir := "user://screenshots"
var EnemyScript: GDScript
var ActorLookScript: GDScript
var story: Node
var gs: Node
var game: Node


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0]
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _save(name: String, settle := 12) -> void:
	for i in settle:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := out_dir.path_join(name + ".png")
	img.save_png(path)
	print("saved ", path, " ", img.get_size())


func _frames(n: int) -> void:
	for i in n:
		await process_frame


## Wait for a condition with game time sped up (software rendering is slow).
func _until(cond: Callable, limit := 2000) -> void:
	Engine.time_scale = 8.0
	for i in limit:
		if cond.call():
			break
		await process_frame
	Engine.time_scale = 1.0


func _run() -> void:
	story = root.get_node("/root/Story")
	EnemyScript = load("res://scripts/world/enemy.gd")
	ActorLookScript = load("res://scripts/world/actor_look.gd")
	gs = root.get_node("/root/Game")
	root.size = Vector2i(1280, 720)
	var audio := root.get_node("/root/Audio")
	audio.music_volume = 0.0

	# 1) title screen
	var title := (load("res://scenes/title.tscn") as PackedScene).instantiate()
	root.add_child(title)
	await _frames(40)
	await _save("title_screen")
	title.free()

	# 2) new game: loading screen, chapter one cinematic, quest HUD, dialogue
	gs.reset()
	gs.character = 0
	game = (load("res://scenes/game.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await _frames(3)
	await _save("loading_screen", 2)
	await _until(func(): return game.cinematic.active)
	await _until(func(): return game.cinematic._title.modulate.a > 0.95, 400)
	await _save("cinematic_title_card", 2)
	await _until(func(): return game.cinematic._line.text != "", 1200)
	await _until(func(): return false, 30)
	await _save("cinematic_intro", 2)
	game.cinematic._skip = true
	await _until(func(): return game.runner.state == "active" and gs.objective().get("type") == "talk")
	var player: CharacterBody3D = game.player
	var npc: Node3D = game.runner.target_npc
	player.global_position = game.map.ground_at(npc.global_position + Vector3(1.0, 0, 5.5)) + Vector3.UP * 0.2
	player._yaw = 0.25
	player._pitch = -0.2
	await _frames(40)
	await _save("quest_hud")
	player.global_position = game.map.ground_at(npc.global_position + Vector3(0.6, 0, 1.6)) + Vector3.UP * 0.2
	# over-the-shoulder from the side so both speakers are in frame
	var side := npc.global_position - player.global_position
	player._yaw = atan2(-side.x, -side.z) + 1.15
	player._pitch = -0.12
	player.spring.spring_length = 3.2
	await _frames(20)
	game._on_interact()
	await _until(func(): return game.dialogue._text.visible_characters < 0, 600)
	await _save("dialogue_voiced", 2)
	game.dialogue._advance = true
	gs.fast = true
	await _until(func(): return not game.dialogue.active)
	gs.fast = false

	# 3) meditation on the formation array
	var fa: Vector3 = game.map.marker_position("FormationArray")
	player.global_position = fa + Vector3.UP * 0.3
	await _frames(30)
	player.start_meditation()
	player._yaw = 2.6
	player._pitch = -0.35
	game.hud.set_meditation(0.6)
	await _frames(60)
	await _save("meditation")
	player.stop_meditation()
	game.hud.set_meditation(-1.0)

	# 4) journal
	game.journal.show_page("quest")
	await _save("journal", 6)
	game.journal.close()

	# 5) combat with spirit wolves in the bamboo forest
	gs.fast = true
	await game.load_map("bamboo_forest", "WolfDen")
	gs.fast = false
	game.runner.clear()
	player = game.player
	var den: Vector3 = game.map.marker_position("WolfDen")
	player.global_position = den + Vector3(0, 0.3, 0)
	for i in 3:
		var w = EnemyScript.create("spirit_wolf" if i < 2 else "corrupted_wolf")
		game.map.add_child(w)
		w.global_position = game.map.open_spot(den, i * 2.1, 3.0)
	await _frames(60)
	player.refill()
	game.hud.set_objective("Drive off the corrupted wolves  (1/3)")
	player._yaw = 0.8
	player._pitch = -0.25
	player.strike()
	await _frames(12)
	await _save("combat_forest", 2)
	for e in root.get_tree().get_nodes_in_group("enemies"):
		e.take_damage(1e6)
	await _frames(30)

	# 6) the flood dragon boss on the sky isles
	gs.fast = true
	await game.load_map("sky_isles", "SerpentLair")
	gs.fast = false
	game.runner.clear()
	var lair: Vector3 = game.map.marker_position("SerpentLair")
	var boss = EnemyScript.create("jiao_serpent", true)
	game.map.add_child(boss)
	boss.global_position = lair + Vector3(0, 0.2, -10)
	player.global_position = lair + Vector3(3.0, 0.4, 5)
	player.refill()
	game.hud.set_objective("Defeat Jiao, the Flood Dragon")
	player._yaw = 0.3
	player._pitch = 0.05
	player.spring.spring_length = 10.0
	boss.take_damage(260.0)
	game.hud.show_boss(boss.display_name(), boss.hp / boss.max_hp)
	await _frames(100)
	player._action_lock = 0.0
	player.blast()
	await _frames(40)
	await _save("boss_jiao_serpent", 2)
	game.hud.show_boss("", -1.0)
	boss.queue_free()

	# 7) map overviews
	var shots := {
		"sect": ["FormationArray", Vector3(46, 34, 70), Vector3(0, 2, -18)],
		"bamboo_forest": ["Clearing", Vector3(-20, 42, 58), Vector3(-10, 0, -10)],
		"qingshi_town": ["MarketSquare", Vector3(-30, 22, 34), Vector3(0, 2, 0)],
		"blood_abyss": ["BoneField", Vector3(-10, 38, 55), Vector3(0, -4, -25)],
		"sky_isles": ["TribulationPeak", Vector3(-40, 24, 55), Vector3(0, 4, 0)],
	}
	for map_id in shots:
		gs.fast = true
		await game.load_map(map_id)
		gs.fast = false
		game.runner.clear()
		game.hud.show_gameplay(false)
		var cam := Camera3D.new()
		cam.far = 3000.0
		cam.fov = 60.0
		game.map.add_child(cam)
		cam.make_current()
		var s: Array = shots[map_id]
		var target: Vector3 = game.map.marker_position(s[0])
		cam.global_position = target + s[1]
		cam.look_at(target + s[2])
		await _save("map_" + map_id, 30)
		cam.queue_free()
		player.camera.make_current()
		game.hud.show_gameplay(true)

	# 8) the cast: every humanoid model lined up in the sect courtyard
	gs.fast = true
	await game.load_map("sect")
	gs.fast = false
	game.runner.clear()
	game.hud.show_gameplay(false)
	for n in game.npcs.values():
		n.visible = false
	player.visible = false
	var models := ["cultivator_male", "cultivator_female", "elder_male", "sect_master", "disciple_male",
		"disciple_female", "villager_male", "villager_female", "bandit", "demon_cultivator", "blood_patriarch"]
	var base: Vector3 = game.map.marker_position("IncenseBurner") + Vector3(0, 0, 7)
	var x := -(models.size() - 1) * 0.5 * 0.95
	var stage := Node3D.new()
	game.map.add_child(stage)
	for m in models:
		var c := (load("res://assets/characters/%s.glb" % m) as PackedScene).instantiate() as Node3D
		stage.add_child(c)
		ActorLookScript.apply(c)
		c.global_position = game.map.ground_at(base + Vector3(x, 0, 0))
		var ap := c.find_child("AnimationPlayer", true, false) as AnimationPlayer
		ap.play("idle")
		ap.seek(0.6, true)
		ap.pause()
		x += 0.95
	var cam2 := Camera3D.new()
	cam2.fov = 42.0
	game.map.add_child(cam2)
	cam2.make_current()
	cam2.global_position = base + Vector3(0, 1.45, 7.8)
	cam2.look_at(base + Vector3(0, 1.0, 0))
	await _save("characters_lineup", 30)
	# close-up of the two heroes
	for c in stage.get_children():
		c.visible = c.get_index() < 2
		if c.get_index() < 2:
			c.global_position = game.map.ground_at(base + Vector3(-0.42 + c.get_index() * 0.84, 0, 0))
	cam2.fov = 26.0
	cam2.global_position = base + Vector3(0, 1.62, 3.1)
	cam2.look_at(base + Vector3(0, 1.45, 0))
	await _save("characters_portrait", 20)
	# creatures
	stage.queue_free()
	var zoo := Node3D.new()
	game.map.add_child(zoo)
	var spots := [Vector3(-2.6, 0, 0.5), Vector3(0.4, 0, -1.0), Vector3(4.5, 0, -9.0)]
	var yaws := [0.9, 0.3, -0.6]
	for i in 3:
		var e = EnemyScript.create(["spirit_wolf", "stone_golem", "jiao_serpent"][i])
		zoo.add_child(e)
		e.global_position = game.map.ground_at(base + spots[i])
		e.rotation.y = yaws[i]
		e.set_physics_process(false)
	cam2.fov = 55.0
	cam2.global_position = base + Vector3(-1.0, 2.6, 7.5)
	cam2.look_at(base + Vector3(0.8, 1.6, -3.0))
	await _save("creatures", 30)
	quit(0)

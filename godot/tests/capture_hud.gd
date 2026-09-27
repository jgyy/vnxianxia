extends SceneTree
## Screenshots of the HUD (gauges, quest scroll, compass + marker, prompt,
## toasts, boss bar, meditation ring, centre stage, dialogue) at several window
## sizes, to check the canvas_items scaling and edge anchoring. Needs a GPU or
## software Vulkan (lavapipe); under CI run inside xvfb-run:
##
##   xvfb-run -a -s "-screen 0 2560x1440x24" godot --path godot --rendering-driver vulkan \
##       -s res://tests/capture_hud.gd -- out_dir [WxH,WxH,...] [quick]
##
## ``quick`` skips the game world: the HUD alone over a plain backdrop (fast,
## light on memory), for iterating on the art and layout.

var out_dir := "user://hud_shots"
var sizes := [Vector2i(1280, 720), Vector2i(1920, 1080), Vector2i(2560, 1440), Vector2i(1024, 768), Vector2i(2560, 1080)]
var gs: Node
var game: Node
var quick := false


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out_dir = args[0]
	if args.size() > 1:
		sizes.clear()
		for s in args[1].split(","):
			var p := s.split("x")
			sizes.append(Vector2i(int(p[0]), int(p[1])))
	quick = args.size() > 2 and args[2] == "quick"
	DirAccess.make_dir_recursive_absolute(out_dir)
	(_run_quick if quick else _run).call_deferred()


func _save(file: String, settle := 8) -> void:
	for i in settle:
		await process_frame
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := out_dir.path_join(file + ".png")
	img.save_png(path)
	print("saved ", path, " ", img.get_size())


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _until(cond: Callable, limit := 2000) -> void:
	Engine.time_scale = 8.0
	for i in limit:
		if cond.call():
			break
		await process_frame
	Engine.time_scale = 1.0


func _resize(s: Vector2i) -> void:
	root.size = s
	await _frames(6)


func _run_quick() -> void:
	gs = root.get_node("/root/Game")
	gs.reset()
	await _resize(sizes[0])
	var bg := ColorRect.new()
	bg.color = Color(0.42, 0.5, 0.46)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)
	var hud: CanvasLayer = (load("res://scripts/ui/hud.gd") as GDScript).new()
	root.add_child(hud)
	await _frames(2)
	hud.set_objective("Speak with the gate disciple")
	hud.set_vitals(100, 100, 100, 100)
	hud.set_hp(55, 100)
	hud.toast("+3 Spirit Stones", UiTheme.JADE, 600.0)
	hud.toast("Your path turns: Walker of the Middle Way", UiTheme.GOLD, 600.0)
	hud.toast("Previously... the gate disciple warned you about the fainting candidates, and the elder is watching.", UiTheme.MUTED, 600.0)
	hud.show_boss("Jiao, the Flood Dragon", 0.62)
	hud.set_prompt("E  Talk to Lu Ping")
	hud.set_meditation(0.6)
	hud.banner("Azure Cloud Sect", "Outer Court", 600.0)
	await _frames(30)
	for s in sizes:
		await _resize(s)
		await _save("quick_%dx%d" % [s.x, s.y], 4)
	quit()


func _run() -> void:
	gs = root.get_node("/root/Game")
	root.get_node("/root/Audio").music_volume = 0.0
	await _resize(sizes[0])
	gs.reset()
	gs.character = 0
	game = (load("res://scenes/game.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await _until(func(): return game.cinematic.active)
	game.cinematic._skip = true
	await _until(func(): return game.runner.state == "active" and gs.objective().get("type") == "talk")
	var hud: CanvasLayer = game.hud
	var player: CharacterBody3D = game.player
	var npc: Node3D = game.runner.target_npc
	player.global_position = game.map.ground_at(npc.global_position + Vector3(4.0, 0, 9.0)) + Vector3.UP * 0.2
	player._yaw = 0.55
	player._pitch = -0.2
	await _frames(30)
	# let the map banner / first quest card finish so the stage is ours
	hud._stage_queue.clear()
	await _until(func(): return not hud._stage_busy, 600)

	game.set_process(false)  # keep our prompt (game.gd refreshes it every frame)
	# 1) everything at once: damaged vitals, toasts, boss, prompt, meditation, quest card
	hud.set_vitals(100, 100, 100, 100)
	await _frames(4)
	hud.set_hp(58, 100)
	hud.set_qi(100, 100)
	hud.toast("+3 Spirit Stones", UiTheme.JADE, 600.0)
	hud.toast("Your path turns: Walker of the Middle Way", UiTheme.GOLD, 600.0)
	hud.toast("Previously... the gate disciple warned you about the fainting candidates, and the elder is watching.", UiTheme.MUTED, 600.0)
	hud.show_boss("Jiao, the Flood Dragon", 0.62)
	hud.set_prompt("E  Talk to Lu Ping")
	hud.set_meditation(0.6)
	hud.quest_card(gs.quest(), 30.0)
	await _frames(40)
	hud.set_hp(41, 100)
	for s in sizes:
		await _resize(s)
		await _save("hud_all_%dx%d" % [s.x, s.y], 4)
	# 2) the everyday HUD (no boss, no meditation) + the map banner
	await _resize(sizes[0])
	hud._stage_queue.clear()
	hud.show_boss("", -1.0)
	hud.set_meditation(-1.0)
	hud.set_prompt("")
	hud._card.visible = false
	hud._stage_busy = false
	hud.banner("Azure Cloud Sect", "Outer Court", 600.0)
	await _frames(40)
	for s in [sizes[0], sizes[sizes.size() - 1]]:
		await _resize(s)
		await _save("hud_banner_%dx%d" % [s.x, s.y], 4)
	# 3) volume title card
	await _resize(sizes[0])
	hud._banner_box.visible = false
	hud._stage_queue.clear()
	hud._stage_busy = false
	hud.title_card("Volume II · Foundation Establishment", "The Sword That Sleeps in the Lake", 20.0)
	await _frames(60)
	await _save("hud_title_1280x720", 4)
	await _resize(Vector2i(1024, 768))
	await _save("hud_title_1024x768", 4)
	await _resize(sizes[0])
	hud._title_box.visible = false
	# 4) dialogue box with the new theme, at the base size and 4:3 / 21:9
	player.global_position = game.map.ground_at(npc.global_position + Vector3(0.6, 0, 1.6)) + Vector3.UP * 0.2
	var side: Vector3 = npc.global_position - player.global_position
	player._yaw = atan2(-side.x, -side.z) + 1.15
	player._pitch = -0.12
	await _frames(20)
	game.set_process(true)
	game._on_interact()
	await _until(func(): return game.dialogue._text.visible_characters < 0, 600)
	for s in [Vector2i(1280, 720), Vector2i(1024, 768), Vector2i(2560, 1080)]:
		await _resize(s)
		await _save("dialogue_%dx%d" % [s.x, s.y], 4)
	await _resize(sizes[0])
	game.dialogue._advance = true
	gs.fast = true
	await _until(func(): return not game.dialogue.active)
	gs.fast = false
	# 5) a choice (theme buttons) and the journal
	game.dialogue.choose("What do you say?", ["I seek the dao.", "I seek revenge.", "I am merely lost."])
	await _frames(20)
	await _save("dialogue_choice_1280x720", 4)
	game.dialogue.chosen.emit(0)
	await _frames(4)
	game.journal.show_page("quest")
	await _save("journal_1280x720", 6)
	game.journal.close()
	game.free()
	var title := (load("res://scenes/title.tscn") as PackedScene).instantiate()
	root.add_child(title)
	await _frames(40)
	await _save("title_1280x720", 4)
	title.free()
	print("capture_hud: done")
	quit()

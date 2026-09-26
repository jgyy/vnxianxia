extends SceneTree
## Headless test of the protagonists' extended move set: both player models
## carry at least 100 unique, non-empty animations, every animation the
## runtime (player_moves.gd) refers to exists, loops are flagged as loops, and
## the player can play every single animation, the combo chains, dodges,
## blocks, techniques, jumps and emotes without errors.
##
##   godot --headless --path godot -s res://tests/animations_test.gd

const MIN_ANIMS := 100
const MODELS := ["res://assets/characters/cultivator_male.glb", "res://assets/characters/cultivator_female.glb"]

var failures: PackedStringArray = []


func check(cond: bool, msg: String) -> void:
	print("  ok   " if cond else "  FAIL ", msg)
	if not cond:
		failures.append(msg)


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	print("Godot ", Engine.get_version_info().string)
	var Moves: GDScript = load("res://scripts/world/player_moves.gd")
	var referenced: Array = Moves.referenced()
	print("[models]")
	for path in MODELS:
		var inst: Node = (load(path) as PackedScene).instantiate()
		var ap := inst.find_child("AnimationPlayer", true, false) as AnimationPlayer
		var names: Array = []
		var empty: Array = []
		for n in ap.get_animation_list():
			if n == "RESET":
				continue
			names.append(n)
			var a := ap.get_animation(n)
			if a.length <= 0.0 or a.get_track_count() == 0:
				empty.append(n)
		check(names.size() >= MIN_ANIMS, "%s: %d unique animations (>= %d)" % [path.get_file(), names.size(), MIN_ANIMS])
		check(empty.is_empty(), "%s: every animation has length and tracks %s" % [path.get_file(), empty])
		var missing := referenced.filter(func(n): return not ap.has_animation(n))
		check(missing.is_empty(), "%s: all %d animations used by the runtime exist %s" % [path.get_file(), referenced.size(), missing])
		inst.free()
	await _session()
	print("")
	if failures.is_empty():
		print("ANIMATIONS TEST PASSED")
		quit(0)
	else:
		print("ANIMATIONS TEST FAILED: %d check(s)" % failures.size())
		quit(1)


func _frames(n: int) -> void:
	for i in n:
		await physics_frame


func _session() -> void:
	print("[player]")
	var gs := root.get_node("/root/Game")
	gs.fast = true
	gs.reset()
	var game: Node = (load("res://scenes/game.tscn") as PackedScene).instantiate()
	root.add_child(game)
	for i in 3000:
		if not game.busy and game.map != null:
			break
		await physics_frame
	var player: CharacterBody3D = game.player
	await _frames(60)
	for ci in 2:
		player.set_character(ci)
		await physics_frame
		var moves: Node = player.moves
		var ap: AnimationPlayer = player.anim
		var names := Array(ap.get_animation_list()).filter(func(n): return n != "RESET")
		var played := 0
		var bad := []
		for n in names:
			if not moves.play_anim(n, 0.0):
				bad.append(n)
				continue
			ap.advance(0.05)
			if ap.current_animation != n:
				bad.append(n)
			else:
				played += 1
		check(bad.is_empty() and played == names.size(), "character %d: played all %d animations %s" % [ci, played, bad])
		var loops_ok := true
		for n in moves.LOOPS:
			loops_ok = loops_ok and ap.get_animation(n).loop_mode == Animation.LOOP_LINEAR
		check(loops_ok, "character %d: %d looping animations flagged" % [ci, moves.LOOPS.size()])
		ap.play("idle", 0.0)
		player._action_lock = 0.0
		moves._clear_busy()
		await _frames(10)
		# combo chains
		for kind in ["palm", "kick", "sword"]:
			var seen := []
			for k in moves.CHAINS[kind].size():
				player._action_lock = 0.0
				if kind == "palm":
					player.strike()
				else:
					moves.strike(kind)
				await physics_frame
				seen.append(player.current_animation())
				await _frames(12)
			var want: Array = moves.CHAINS[kind].map(func(e): return e[0])
			check(seen == want, "character %d: %s combo chain %s" % [ci, kind, seen])
			player._action_lock = 0.0
			moves._clear_busy()
			await _frames(50)
		# block, parry and hit reactions
		player._action_lock = 0.0
		moves.block(true)
		await _frames(12)
		var hp0: float = player.hp
		moves._block_pressed = -100.0
		player._invulnerable = 0.0
		player.take_damage(10.0)
		check(player.hp > hp0 - 10.0 and player.current_animation().begins_with("block"),
				"character %d: block reduces damage (%s)" % [ci, player.current_animation()])
		moves.block(false)
		player._invulnerable = 0.0
		player._action_lock = 0.0
		moves._clear_busy()
		player.take_damage(9.0)
		await physics_frame
		check(player.current_animation().begins_with("stagger"), "character %d: stagger reaction (%s)" % [ci, player.current_animation()])
		player.refill()
		await _frames(30)
		# dodge
		player._action_lock = 0.0
		moves._clear_busy()
		moves.dodge()
		await physics_frame
		check(player.current_animation() == "backflip", "character %d: dodge without direction backflips (%s)" % [ci, player.current_animation()])
		await _frames(60)
		# technique
		player.qi = 100.0
		player._action_lock = 0.0
		moves.technique(2)
		await physics_frame
		check(player.current_animation() == "blast_wave", "character %d: qi technique (%s)" % [ci, player.current_animation()])
		await _frames(50)
		# emotes (sequence and held loop)
		player._action_lock = 0.0
		moves.play_emote(["sit_ground", "sit_ground_idle"])
		await physics_frame
		check(player.current_animation() == "sit_ground", "character %d: emote starts (%s)" % [ci, player.current_animation()])
		await _frames(100)
		check(player.current_animation() == "sit_ground_idle", "character %d: emote holds its loop (%s)" % [ci, player.current_animation()])
		moves.open_menu()
		check(moves.menu_open and moves._menu.visible, "character %d: emote menu opens" % ci)
		moves.close_menu()
		# jump and qinggong flip
		player._action_lock = 0.0
		moves._clear_busy()
		player.velocity.y = player.JUMP_VELOCITY
		await _frames(6)
		check(not player.is_on_floor(), "character %d: jumped" % ci)
		check(moves._air_jump() and player.current_animation() == "double_jump_flip",
				"character %d: second jump somersaults (%s)" % [ci, player.current_animation()])
		await _frames(120)
		check(player.is_on_floor(), "character %d: landed" % ci)
	game.queue_free()
	await _frames(3)

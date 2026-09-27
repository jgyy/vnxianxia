extends SceneTree
## Plays the main story headlessly through the real game systems: travel by
## teleport array, talk to NPCs, fight, collect, meditate, interact and watch
## cinematics — every quest in the range must complete.
##
##   godot --headless --path godot -s res://tests/walkthrough_test.gd [-- first_quest last_quest]
##
## Quest numbers are 1-based (1..2000). CI plays the saga in twenty shards, two
## per volume (1 100, 101 200, ...); a shard starts with the realm, minor stage
## and rewards of every earlier quest already applied (Game.start_at).
##
## Moral choices are made by Game.auto_choice (fast mode), which varies with
## the quest and objective, so a run makes lawful, chaotic, good and evil
## choices and the story must still finish whatever the alignment becomes.
## Tribulations are survived the steady way: meditate through the lightning,
## and fight off the beasts between volleys.

const OBJECTIVE_TIMEOUT := 1800   # physics frames

var failures: PackedStringArray = []
var story: Node
var gs: Node
var game: Node
var counts := {}
var travels := 0
var _first := 1


func _initialize() -> void:
	_run.call_deferred()


func fail(msg: String) -> void:
	print("  FAIL ", msg)
	failures.append(msg)


func _frames(n: int) -> void:
	for i in n:
		await physics_frame


func _wait(cond: Callable, limit := OBJECTIVE_TIMEOUT) -> bool:
	for i in limit:
		if cond.call():
			return true
		await physics_frame
	return false


func _run() -> void:
	story = root.get_node("/root/Story")
	gs = root.get_node("/root/Game")
	var args := OS.get_cmdline_user_args()
	var first := int(args[0]) if args.size() > 0 else 1
	_first = first
	var last: int = int(args[1]) if args.size() > 1 else story.quests.size()
	print("Godot ", Engine.get_version_info().string, " — walkthrough of quests %d..%d" % [first, last])
	gs.fast = true
	gs.start_at(first - 1)
	gs.character = (first - 1) % 2
	game = (load("res://scenes/game.tscn") as PackedScene).instantiate()
	root.add_child(game)
	if not await _wait(func(): return not game.busy and game.map != null, 3000):
		fail("first map never loaded")
		return _finish()
	var t0 := Time.get_ticks_msec()
	var last_q := -1
	while not gs.finished() and gs.quest_index < last:
		if gs.quest_index != last_q:
			last_q = gs.quest_index
			var q: Dictionary = gs.quest()
			print("[%s] v%d ch%d %s  (%s, %s)" % [q.id, int(q.get("volume", 1)), int(q.chapter), q.title, gs.map_id, gs.realm_label()])
			# swap protagonist now and then so both voices/models are exercised
			if gs.quest_index % 7 == 3:
				game.player.set_character(1 - gs.character)
		if not await _step():
			break
	var secs := (Time.get_ticks_msec() - t0) / 1000.0
	print("")
	print("objectives by type: ", counts, "  teleports: ", travels, "  time: %.1fs" % secs)
	print("cultivation at the end: %s" % gs.realm_label())
	print("alignment at the end: %s (law %d, good %d); %d choices made; flags %s" % [
		gs.alignment_name(), gs.law, gs.good, gs.choices.size(), gs.flags.keys()])
	if gs.quest_index < last and failures.is_empty():
		fail("stopped at quest %d" % (gs.quest_index + 1))
	if failures.is_empty():
		# the realm and minor stage earned by playing must match the story's rewards
		var er := 0
		var es := 0
		for i in mini(last, story.quests.size()):
			var r: Dictionary = story.quests[i].rewards
			if r.get("realm"):
				er = story.realm_index(r.realm)
				es = int(r.stage) if r.get("stage") != null else 0
			elif r.get("stage") != null:
				es = int(r.stage)
		if gs.realm != er or gs.stage != es:
			fail("cultivation is %s, the story says %s" % [gs.realm_label(), story.realm_label(er, es)])
	if last >= story.quests.size() and not gs.finished():
		fail("story not finished")
	if last >= story.quests.size() and gs.realm != story.world.realms.size() - 1:
		fail("final realm is %s" % story.realm_name(gs.realm))
	_finish()


func _finish() -> void:
	print("")
	if failures.is_empty():
		print("WALKTHROUGH PASSED: quests %d..%d completed" % [_first, gs.quest_index])
		quit(0)
	else:
		print("WALKTHROUGH FAILED: %d problem(s)" % failures.size())
		quit(1)


func _step() -> bool:
	var runner: Node = game.runner
	if not await _wait(func(): return not game.busy and runner.state in ["active", "travel"]):
		fail("%s: objective %d never became active (state=%s)" % [gs.quest().id, gs.objective_index, runner.state])
		return false
	var q: Dictionary = gs.quest()
	var qi: int = gs.quest_index
	var oi: int = gs.objective_index
	var obj: Dictionary = runner.obj
	var tag := "%s/o%d %s" % [q.id, oi, obj.type]
	var player: CharacterBody3D = game.player
	if runner.state == "travel":
		travels += 1
		game.travel_to(obj.map)
		if not await _wait(func(): return gs.map_id == obj.map and not game.busy, 3000):
			fail(tag + ": travel to " + obj.map + " failed")
			return false
		return true
	counts[obj.type] = counts.get(obj.type, 0) + 1
	var map: Node = game.map
	for key in ["marker", "at"]:
		var mk = obj.get(key)
		if mk and not map.marker_grounded(mk):
			fail("%s: marker %s has no ground on %s" % [tag, mk, gs.map_id])
	var advanced := func(): return gs.quest_index != qi or gs.objective_index != oi
	match obj.type:
		"talk":
			var n: Node3D = runner.target_npc
			if n == null:
				fail(tag + ": no NPC " + obj.npc)
				return false
			_place(player, _free_spot(n.global_position, 1.4))
			await _frames(3)
			game._on_interact()
		"reach":
			_place(player, runner.target_point)
		"defeat":
			if runner.enemies.is_empty():
				fail(tag + ": no enemies spawned")
				return false
			_place(player, runner.target_point + Vector3(0, 0, 9))
			await _frames(4)
			await _wait(func(): return runner.state == "active", 600)
			# fight for real: face each enemy and palm-strike until it falls
			for e in runner.enemies:
				var guard := 0
				while is_instance_valid(e) and not e.dead and guard < 12:
					_place(player, _free_spot(e.global_position, 1.2))
					for k in 30:
						await physics_frame
						if player.is_on_floor():
							break
					e.hp = minf(e.hp, 1.0)
					player._action_lock = 0.0
					player.strike()
					await _frames(30)
					guard += 1
				if is_instance_valid(e) and not e.dead:
					fail("%s: %s survived strikes (enemy %s, player %s, floor %s)" % [tag, e.kind, e.global_position, player.global_position, player.is_on_floor()])
					e.take_damage(1e9)
		"collect":
			for p in runner.pickups.duplicate():
				if is_instance_valid(p):
					var at: Vector3 = p.global_position
					_place(player, at)
					var got := false
					for i in 240:
						if not is_instance_valid(p) or p.taken:
							got = true
							break
						await physics_frame
					if not got:
						fail("%s: pickup at %s not collected" % [tag, at])
		"meditate":
			_place(player, runner.target_point)
			await _wait(func(): return player.is_on_floor(), 120)
			player.start_meditation()
		"interact":
			_place(player, _free_spot(runner.target_point, 1.8))
			await _frames(3)
			game._on_interact()
		"cinematic":
			pass
		"tribulation":
			if not await _tribulation(tag, advanced):
				return false
			return true
	if not await _wait(advanced):
		var extra := ""
		if obj.type == "talk" and runner.target_npc:
			extra = " player %s npc %s busy=%s dlg=%s" % [player.global_position, runner.target_npc.global_position, game.busy, game.dialogue.active]
		fail("%s did not complete (state=%s)%s" % [tag, runner.state, extra])
		return false
	return true


## Survive a heavenly tribulation: stand in it and meditate; when beasts or
## heart shades come between volleys, strike them down, then meditate again.
func _tribulation(tag: String, advanced: Callable) -> bool:
	var runner: Node = game.runner
	var player: CharacterBody3D = game.player
	var site: Vector3 = runner.target_point
	var fails := 0
	var was_failed := false
	_place(player, site)
	for step in 20000:
		if advanced.call():
			return true
		var t = runner.trib
		if t == null:
			await physics_frame
			continue
		if runner._trib_failed and not was_failed:
			fails += 1
			# meditating through it must always be enough: being struck down is a failure of the test
			fail("%s: the tribulation struck the player down (hp %.0f / %.0f)" % [tag, player.hp, gs.max_hp()])
			return false
		was_failed = runner._trib_failed
		if not t.running:
			if Vector2(player.global_position.x - site.x, player.global_position.z - site.z).length() > 3.0:
				_place(player, site)
			await physics_frame
			continue
		var alive: Array = t.enemies.filter(func(e): return is_instance_valid(e) and not e.dead)
		if not alive.is_empty():
			for e in alive:
				var guard := 0
				while is_instance_valid(e) and not e.dead and guard < 12:
					_place(player, _free_spot(e.global_position, 1.2))
					for k in 30:
						await physics_frame
						if player.is_on_floor():
							break
					e.hp = minf(e.hp, 1.0)
					player._action_lock = 0.0
					player.strike()
					await _frames(30)
					guard += 1
				if is_instance_valid(e) and not e.dead:
					e.take_damage(1e9)
			continue
		if not player.meditating:
			if not player.is_on_floor():
				await physics_frame
				continue
			player.start_meditation()
		await physics_frame
	fail(tag + " did not complete (tribulation at volley %d)" % (runner.trib.done if runner.trib else -1))
	return false


func _place(player: CharacterBody3D, p: Vector3) -> void:
	player.global_position = game.map.ground_at(p) + Vector3.UP * 0.2
	player.velocity = Vector3.ZERO


## A point near `c` whose ground is at about the same height (not on a roof).
func _free_spot(c: Vector3, r: float) -> Vector3:
	for i in 16:
		var a := TAU * i / 16.0
		var p: Vector3 = game.map.ground_at(c + Vector3(cos(a), 0, sin(a)) * r)
		if absf(p.y - c.y) < 0.45:
			return p
	return c + Vector3(r, 0, 0)

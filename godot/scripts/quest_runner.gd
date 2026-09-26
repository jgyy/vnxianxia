extends Node
## Drives the active objective of the main story: spawns what it needs
## (NPC, enemies, pickups, props, beacons), detects completion, grants rewards.

signal objective_completed(quest_id: String, index: int)
signal quest_completed(quest_id: String)

const BEACON_GOLD := Color(1.0, 0.82, 0.35)
const BEACON_JADE := Color(0.45, 1.0, 0.8)

var game: Node
var obj: Dictionary = {}
var state := ""                 ## "", "travel", "active", "busy"
var target_npc: Npc
var target_point := Vector3.INF
var spawned: Array[Node] = []
var enemies: Array[Enemy] = []
var pickups: Array[Pickup] = []
var prop: QuestProp
var _med_time := 0.0
var _fight_talked := false
var _completing := false
var _fighting := ""


func clear() -> void:
	for n in spawned:
		if is_instance_valid(n):
			n.queue_free()
	spawned.clear()
	enemies.clear()
	pickups.clear()
	prop = null
	if target_npc and is_instance_valid(target_npc):
		target_npc.set_quest_target(false)
	target_npc = null
	target_point = Vector3.INF
	state = ""
	_med_time = 0.0
	_fight_talked = false
	_completing = false
	game.hud.target_point = Vector3.INF
	game.hud.show_boss("", -1.0)
	game.hud.set_meditation(-1.0)
	_set_fight("")


func activate() -> void:
	clear()
	game.hud.refresh()
	if Game.finished():
		game.hud.set_objective("Your legend is written. Wander freely.")
		return
	obj = Game.objective()
	var map: Node = game.map
	if obj.map != Game.map_id:
		state = "travel"
		game.hud.set_objective("Travel to %s by teleport array" % Story.map_name(obj.map))
		_point(map.marker_position("TeleportArray"))
		return
	state = "active"
	_update_text()
	match obj.type:
		"talk":
			var at: String = obj.at if obj.get("at") else Story.npc(obj.npc).home.marker
			target_npc = game.ensure_npc(obj.npc, at)
			target_npc.set_quest_target(true)
			_point(target_npc.global_position)
		"reach":
			var p: Vector3 = map.marker_position(obj.marker)
			_beacon(p, BEACON_GOLD, float(obj.get("radius", 4.0)) * 0.5)
			_point(p)
		"defeat":
			_spawn_enemies(map.marker_position(obj.marker))
		"collect":
			_spawn_pickups(map.marker_position(obj.marker))
		"meditate":
			var p: Vector3 = map.marker_position(obj.marker)
			_beacon(p, BEACON_JADE, 1.6)
			_point(p)
		"interact":
			var p: Vector3 = map.marker_position(obj.marker)
			prop = QuestProp.create(obj.object)
			map.add_child(prop)
			prop.global_position = p
			var to: Vector3 = map.marker_position("PlayerSpawn") - p
			prop.rotation.y = atan2(to.x, to.z)
			spawned.append(prop)
			_beacon(p, BEACON_GOLD, 1.8)
			_point(p)
		"cinematic":
			state = "busy"
			_play_cinematic.call_deferred()


func _point(p: Vector3) -> void:
	target_point = p
	game.hud.target_point = p


func _beacon(p: Vector3, c: Color, r: float) -> void:
	var b := Beacon.create(c, r)
	game.map.add_child(b)
	b.global_position = p
	spawned.append(b)


func _update_text() -> void:
	var t := Story.fill(obj.text)
	match obj.type:
		"defeat", "collect":
			t += "  (%d/%d)" % [Game.progress, int(obj.count)]
	game.hud.set_objective(t)


func _spawn_enemies(center: Vector3) -> void:
	var boss: bool = Story.world.bosses.has(obj.enemy)
	var count := int(obj.count)
	var remaining := count - Game.progress
	for i in remaining:
		var e := Enemy.create(obj.enemy, boss)
		var a := TAU * i / maxf(remaining, 1) + 0.4
		var r := 0.0 if (boss or remaining == 1) else 3.0 + 1.6 * (i % 2)
		var p: Vector3 = center if r == 0.0 else game.map.open_spot(center, a, r)
		game.map.add_child(e)
		e.global_position = p + Vector3.UP * 0.1
		var to: Vector3 = game.player.global_position - p
		e.rotation.y = atan2(to.x, to.z)
		e.died.connect(_on_enemy_died)
		e.aggroed.connect(_on_aggro)
		enemies.append(e)
		spawned.append(e)
	_point(center)


func _spawn_pickups(center: Vector3) -> void:
	var count := int(obj.count)
	for i in range(Game.progress, count):
		var a := i * 2.39996
		var r := 1.5 + 6.0 * sqrt((i + 0.5) / count)
		var p := Pickup.create(obj.item)
		game.map.add_child(p)
		p.global_position = game.map.open_spot(center, a, r)
		pickups.append(p)
		spawned.append(p)
	_point(center)


func _play_cinematic() -> void:
	await game.cinematic.play(obj.id)
	complete()


func _on_aggro(e: Enemy) -> void:
	_set_fight("boss" if e.boss else "battle")


func _set_fight(kind: String) -> void:
	if kind == _fighting:
		return
	if _fighting == "boss" and kind == "battle":
		return
	_fighting = kind
	if kind == "":
		if game.map:
			Audio.play_music(game.map.music)
	else:
		Audio.play_music(kind, 0.8)


func _on_enemy_died(e: Enemy) -> void:
	if state != "active":
		return
	Game.progress += 1
	Game.add_xp(12 if not e.boss else 120)
	_update_text()
	if Game.progress >= int(obj.count):
		_set_fight("")
		complete()


## Called by the game when the player presses E near something of ours.
func try_interact() -> bool:
	if state != "active":
		return false
	var pp: Vector3 = game.player.global_position
	if obj.type == "talk" and target_npc and pp.distance_to(target_npc.global_position) < 2.8:
		_talk()
		return true
	if obj.type == "interact" and prop and pp.distance_to(prop.global_position) < 3.0:
		_interact()
		return true
	return false


func prompt() -> String:
	if state != "active":
		return ""
	var pp: Vector3 = game.player.global_position
	match obj.type:
		"talk":
			if target_npc and pp.distance_to(target_npc.global_position) < 2.8:
				return "E  Talk to " + Story.npc(obj.npc).get("name", "")
		"interact":
			if prop and pp.distance_to(prop.global_position) < 3.0:
				return "E  " + Story.fill(obj.text)
		"meditate":
			if pp.distance_to(target_point) < 3.5 and not game.player.meditating:
				return "C  Meditate here"
	return ""


func _talk() -> void:
	state = "busy"
	var npc := target_npc
	npc.set_quest_target(false)
	await game.converse(obj.dialogue, npc)
	complete()


func _interact() -> void:
	state = "busy"
	Audio.sfx("chest_open" if obj.object == "treasure_chest" else "bell_toll" if obj.object == "bronze_bell" else "objective_update", -4.0)
	Fx.burst(game.map, prop.global_position + Vector3.UP, BEACON_GOLD, 40, 3.0)
	if obj.get("dialogue"):
		await game.converse(obj.dialogue)
	complete()


func _process(delta: float) -> void:
	if state != "active" or game.busy:
		return
	var player: Node3D = game.player
	var pp := player.global_position
	match obj.type:
		"talk":
			if target_npc:
				_point(target_npc.global_position)
		"reach":
			if Vector2(pp.x - target_point.x, pp.z - target_point.z).length() < float(obj.get("radius", 4.0)) \
					and absf(pp.y - target_point.y) < 6.0:
				state = "busy"
				if obj.get("dialogue"):
					await game.converse(obj.dialogue)
				complete()
		"defeat":
			if obj.get("dialogue") and not _fight_talked and pp.distance_to(target_point) < 24.0:
				_fight_talked = true
				state = "busy"
				await game.converse(obj.dialogue)
				state = "active"
			var boss_e: Enemy = null
			for e in enemies:
				if is_instance_valid(e) and e.boss:
					boss_e = e
			if boss_e and not boss_e.dead and pp.distance_to(boss_e.global_position) < 40.0:
				game.hud.show_boss(boss_e.display_name(), boss_e.hp / boss_e.max_hp)
			else:
				game.hud.show_boss("", -1.0)
			var alive := enemies.filter(func(e): return is_instance_valid(e) and not e.dead)
			if not alive.is_empty():
				var near: Enemy = alive[0]
				for e in alive:
					if pp.distance_to(e.global_position) < pp.distance_to(near.global_position):
						near = e
				_point(near.global_position)
		"collect":
			var nearest: Pickup = null
			for p in pickups:
				if not is_instance_valid(p) or p.taken:
					continue
				if pp.distance_to(p.global_position + Vector3.UP * 0.4) < 1.5:
					p.take()
					Game.progress += 1
					Game.add_item(obj.item)
					_update_text()
					if Game.progress >= int(obj.count):
						complete()
						return
				elif nearest == null or pp.distance_to(p.global_position) < pp.distance_to(nearest.global_position):
					nearest = p
			if nearest:
				_point(nearest.global_position)
		"meditate":
			var secs := float(obj.get("seconds", 6.0)) * (0.02 if Game.fast else 1.0)
			if player.meditating and pp.distance_to(target_point) < 3.5:
				_med_time += delta
				game.hud.set_meditation(_med_time / secs)
				if _med_time >= secs:
					state = "busy"
					game.hud.set_meditation(-1.0)
					Audio.sfx("breakthrough" if obj.get("dialogue") == null else "objective_update", -6.0)
					Fx.burst(game.map, pp + Vector3.UP, BEACON_JADE, 60, 2.5)
					if obj.get("dialogue"):
						await game.converse(obj.dialogue)
					player.stop_meditation()
					complete()
			else:
				game.hud.set_meditation(_med_time / secs if _med_time > 0.0 else -1.0)


## Objective finished: advance the story.
func complete() -> void:
	if _completing:
		return
	_completing = true
	var q := Game.quest()
	objective_completed.emit(q.id, Game.objective_index)
	Game.objective_index += 1
	Game.progress = 0
	if Game.objective_index >= (q.objectives as Array).size():
		_finish_quest(q)
	else:
		Audio.sfx("objective_update", -6.0)
	Game.save()
	game.refresh_npcs()
	activate()


func _finish_quest(q: Dictionary) -> void:
	var r: Dictionary = q.rewards
	Game.add_xp(int(r.get("xp", 0)))
	for item in r.get("items", {}):
		Game.add_item(item, int(r.items[item]))
	Game.completed.append(q.id)
	Game.quest_index += 1
	Game.objective_index = 0
	Audio.sfx("quest_complete", -3.0)
	game.hud.toast("Quest complete: " + q.title, UiTheme.GOLD)
	if r.get("realm"):
		Game.set_realm(r.realm)
	quest_completed.emit(q.id)
	if int(q.number) % 10 == 0:
		var ch := Story.chapter(int(q.chapter))
		game.hud.banner("Chapter %d Complete" % int(q.chapter), ch.get("title", ""), 4.0)
		if not Game.fast:
			Audio.play_music("victory", 0.5)
			get_tree().create_timer(12.0).timeout.connect(func(): if game.map: Audio.play_music(game.map.music))
	if not Game.finished():
		var nq := Game.quest()
		game.hud.toast("New quest: " + nq.title, UiTheme.JADE)
		Audio.sfx("quest_accept", -6.0)
	else:
		game.hud.banner("Immortal Ascension", "The saga of the Azure Cloud Sect is complete", 6.0)

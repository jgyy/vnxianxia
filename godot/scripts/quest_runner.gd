extends Node
## Drives the active objective of the main story: spawns what it needs
## (NPC, the NPCs present for its conversation, enemies, pickups, props,
## beacons), detects completion, grants rewards.
##
## Conversations with several NPCs: an objective's `with` lists NPCs who are
## present for it (see docs/STORY.md). They are placed standing in a loose
## circle with the talk target (talk) or around the objective's marker (the
## other types), facing the middle, and removed again when the objective ends
## unless the map is their home. Without `with`, the NPCs who speak in the
## objective's lines are gathered the same way, so nobody talks from nowhere.

signal objective_completed(quest_id: String, index: int)
signal quest_completed(quest_id: String)

const BEACON_GOLD := Color(1.0, 0.82, 0.35)
const BEACON_JADE := Color(0.45, 1.0, 0.8)
## circle of a group conversation around its centre (m)
const PARTY_RADIUS := 1.45
## minimum distance between two people standing in a group (m)
const PARTY_SPACING := 0.85

var game: Node
var obj: Dictionary = {}
var state := ""                 ## "", "travel", "active", "busy"
var target_npc: Npc
var target_point := Vector3.INF
var spawned: Array[Node] = []
var enemies: Array[Enemy] = []
var pickups: Array[Pickup] = []
var prop: QuestProp
## NPCs standing in for this objective's conversation (the target excluded)
var party: Array[Npc] = []
var _med_time := 0.0
var _fight_talked := false
var _completing := false
var _fighting := ""
var trib: Tribulation
var _trib_failed := false
## bumped by clear(): a coroutine that awaited across it must not act on the new objective
var _epoch := 0
var _music_timer: SceneTreeTimer


func clear() -> void:
	_epoch += 1
	for n in spawned:
		if is_instance_valid(n):
			# an enemy already mid-death (its own tween fades it out, then
			# frees it) must not be queue_free()'d again here: racing that
			# tween's own queue_free() against this one risks the tween's
			# later steps running on a node freed out from under it
			if n is Enemy and n.dead:
				continue
			n.queue_free()
	spawned.clear()
	enemies.clear()
	pickups.clear()
	prop = null
	_dismiss_party()
	if target_npc and is_instance_valid(target_npc):
		target_npc.set_quest_target(false)
	target_npc = null
	target_point = Vector3.INF
	state = ""
	_med_time = 0.0
	_fight_talked = false
	_completing = false
	trib = null
	_trib_failed = false
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
	if obj.is_empty():
		return
	stage(obj)


## Set up objective ``o`` on the current map (activate() passes the story's
## current objective; tests stage made-up ones).
func stage(o: Dictionary) -> void:
	obj = o
	var map: Node = game.map
	if obj.map != Game.map_id:
		state = "travel"
		if Doors.INTERIORS.has(Game.map_id) and map.has_marker("ExitDoor"):
			# teleport arrays do not work indoors: out through the door first
			game.hud.set_objective("Leave the building, then travel to %s" % Story.map_name(obj.map))
			_point(map.marker_position("ExitDoor"))
		else:
			game.hud.set_objective("Travel to %s by teleport array" % Story.map_name(obj.map))
			if map.has_marker("TeleportArray"):
				_point(map.marker_position("TeleportArray"))
		return
	state = "active"
	_update_text()
	match obj.type:
		"talk":
			var at: String = _talk_marker()
			target_npc = game.ensure_npc(obj.npc, at)
			target_npc.set_quest_target(true)
			_point(target_npc.global_position)
			_gather_talk_party()
		"reach":
			var p: Vector3 = map.marker_position(obj.marker)
			_beacon(p, BEACON_GOLD, float(obj.get("radius", 4.0)) * 0.5)
			_point(p)
			_gather_party(p, 2.1, 0.0)
		"defeat":
			var c: Vector3 = map.marker_position(obj.marker)
			_spawn_enemies(c)
			_gather_party(c, PARTY_RADIUS, 9.0)
		"collect":
			var c: Vector3 = map.marker_position(obj.marker)
			_spawn_pickups(c)
			_gather_party(c, PARTY_RADIUS, 9.0)
		"meditate":
			var p: Vector3 = map.marker_position(obj.marker)
			_beacon(p, BEACON_JADE, 1.6)
			_point(p)
			_gather_party(p, 2.4, 0.0)
		"interact":
			var p: Vector3 = map.marker_position(obj.marker)
			prop = QuestProp.create(obj.object)
			map.add_child(prop)
			prop.global_position = p
			var to: Vector3 = map.marker_position("PlayerSpawn") - p
			prop.rotation.y = atan2(to.x, to.z)
			spawned.append(prop)
			_beacon(p, BEACON_GOLD, maxf(1.8, prop.footprint() + 0.6))
			_point(p)
			_gather_party(p, PARTY_RADIUS, prop.footprint() + 2.0)
		"cinematic":
			state = "busy"
			_play_cinematic.call_deferred(_epoch)
		"tribulation":
			var p: Vector3 = map.marker_position(obj.marker)
			_beacon(p, Color(0.6, 0.72, 1.0), 2.2)
			_point(p)
			trib = Tribulation.create(obj, int(Game.quest().get("tier", Game.realm)))
			map.add_child(trib)
			trib.global_position = p
			spawned.append(trib)
			trib.volley_struck.connect(_on_volley)
			trib.wave_spawned.connect(_on_wave)
			trib.survived.connect(_on_tribulation_survived)
			trib.failed.connect(_on_tribulation_failed)
			_gather_party(p, PARTY_RADIUS, 11.0)


## Where the talk target stands: the objective's `at`, else the NPC's home
## marker, else (an NPC with no home here) beside the arrival point.
func _talk_marker() -> String:
	var map: Node = game.map
	var at = obj.get("at")
	if at and map.has_marker(at):
		return at
	var home = Story.npc(obj.npc).get("home")
	if home and home.map == Game.map_id and map.has_marker(home.marker):
		return home.marker
	return "PlayerSpawn"


# ------------------------------------------------------------ group conversations

## NPC ids present for this objective's conversation: `with` when the story
## gives it, otherwise everyone (but the player, the narrator and the talk
## target) who speaks in its lines or its choices' replies.
func party_ids() -> Array:
	var ids: Array = []
	var w = obj.get("with")
	if w is Array:
		ids = w.duplicate()
	else:
		var lines: Array = (obj.get("dialogue", []) if obj.get("dialogue") else []).duplicate()
		for c in (obj.get("choices", []) if obj.get("choices") else []):
			lines.append_array(c.get("reply", []) if c.get("reply") else [])
		for l in lines:
			var sp: String = l.get("speaker", "")
			if not ids.has(sp):
				ids.append(sp)
	var out: Array = []
	for id in ids:
		if id is String and id not in ["", "player", "narrator", obj.get("npc", "")] and not out.has(id) \
				and not Story.npc(id).is_empty():
			out.append(id)
	return out


## Talk: the target stands at its marker facing the approach; the others
## join it in a circle whose open side is where the player will stand.
func _gather_talk_party() -> void:
	var ids := party_ids()
	if ids.is_empty() or target_npc == null:
		return
	var f := target_npc.global_basis.z
	f.y = 0.0
	f = f.normalized() if f.length() > 0.01 else Vector3.FORWARD
	var centre := target_npc.global_position + f * (PARTY_RADIUS * 0.75)
	_place_party(ids, centre, f, PARTY_RADIUS, [target_npc.global_position])


## Other objectives: the group waits around the marker (or, for a fight or a
## tribulation, a little way back toward where the player comes from).
func _gather_party(anchor: Vector3, radius: float, stand_back: float) -> void:
	var ids := party_ids()
	if ids.is_empty():
		return
	var map: Node = game.map
	var toward: Vector3 = game.player.global_position - anchor
	toward.y = 0.0
	if toward.length() < 1.0:
		toward = map.marker_position("PlayerSpawn") - anchor
		toward.y = 0.0
	toward = toward.normalized() if toward.length() > 0.01 else Vector3.FORWARD
	var centre := anchor
	if stand_back > 0.0:
		centre = map.ground_at(anchor + toward * stand_back)
	_place_party(ids, centre, toward, radius, [])


## Stand `ids` on a circle around `centre`, leaving the arc toward `open_dir`
## free for the player, each on open walkable ground and facing the middle.
func _place_party(ids: Array, centre: Vector3, open_dir: Vector3, radius: float, taken: Array) -> void:
	var map: Node = game.map
	var right := open_dir.cross(Vector3.UP).normalized()
	var used: Array = taken.duplicate()
	var n := ids.size()
	for i in n:
		var id: String = ids[i]
		# spread over the far arc: 0 = the open side, PI = straight across
		var slot := (float(i) + 0.5) / float(n)
		var ang := lerpf(deg_to_rad(80.0), deg_to_rad(280.0), slot) if n > 1 else deg_to_rad(110.0)
		var r := radius + (0.35 if n > 4 else 0.0)
		var at := _free_spot(centre, open_dir, right, ang, r, used)
		used.append(at)
		var npc: Npc = game.place_npc(id, at, centre)
		npc.set_quest_target(false)
		if not party.has(npc):
			party.append(npc)


func _free_spot(centre: Vector3, fwd: Vector3, right: Vector3, ang: float, r: float, used: Array) -> Vector3:
	var map: Node = game.map
	for tries in 14:
		var da := (0.22 * ceilf(tries * 0.5)) * (1.0 if tries % 2 == 0 else -1.0)
		var rr := r + 0.3 * floorf(tries / 4.0)
		var a := ang + da
		var cand: Vector3 = centre + (fwd * cos(a) + right * sin(a)) * rr
		var g: Vector3 = map.ground_at(cand)
		if absf(g.y - centre.y) > 0.8 or not map.is_open(g, 0.3):
			continue
		var crowded := false
		for u in used:
			if Vector2(g.x - u.x, g.z - u.z).length() < PARTY_SPACING:
				crowded = true
				break
		if not crowded:
			return g
	var fb: Vector3 = map.open_spot(centre, atan2((fwd * cos(ang) + right * sin(ang)).z, (fwd * cos(ang) + right * sin(ang)).x), r)
	return fb


## Send the group home: NPCs who live on this map go back to their marker,
## the ones brought in for the conversation leave.
func _dismiss_party() -> void:
	for npc in party:
		if not is_instance_valid(npc) or npc == target_npc:
			continue
		if game.is_ambient(npc.npc_id):
			var home = Story.npc(npc.npc_id).home
			if game.map and game.map.has_marker(home.marker):
				game.ensure_npc(npc.npc_id, home.marker)
		else:
			game.npcs.erase(npc.npc_id)
			npc.queue_free()
	party.clear()


# ------------------------------------------------------------ objectives

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
		"tribulation":
			if _trib_failed:
				t = "Return and face the tribulation again"
			elif trib and trib.running:
				t += "  (%d/%d)" % [trib.done, trib.volleys]
	game.hud.set_objective(t)


func _spawn_enemies(center: Vector3) -> void:
	var boss: bool = Story.world.bosses.has(obj.enemy)
	var count := int(obj.count)
	var remaining := count - Game.progress
	var tier := int(Game.quest().get("tier", Game.realm))
	var display: String = obj.get("name", "") if obj.get("name") else ""
	for i in remaining:
		var e := Enemy.create(obj.enemy, boss, tier, display)
		var a := TAU * i / maxf(remaining, 1) + 0.4
		var r := 0.0 if (boss or remaining == 1) else 3.0 + 1.6 * (i % 2)
		var p: Vector3 = center if r == 0.0 else game.map.open_spot(center, a, r)
		game.map.add_child(e)
		e.global_position = p + Vector3.UP * 0.1
		e.home = e.global_position
		var to: Vector3 = game.player.global_position - p
		e.rotation.y = atan2(to.x, to.z)
		e.died.connect(_on_enemy_died)
		e.aggroed.connect(_on_aggro)
		enemies.append(e)
		spawned.append(e)
	_point(center)


func _spawn_pickups(center: Vector3) -> void:
	var count := int(obj.count)
	var used: Array = []
	for i in range(Game.progress, count):
		var a := i * 2.39996
		var r := 1.5 + 6.0 * sqrt((i + 0.5) / count)
		var p := Pickup.create(obj.item)
		game.map.add_child(p)
		var at: Vector3 = game.map.open_spot(center, a, r)
		for u in used:
			if at.distance_to(u) < 0.6:
				# open_spot fell back to the centre: fan the rest out instead of stacking them
				at = game.map.ground_at(center + Vector3(cos(a), 0, sin(a)) * r)
				break
		used.append(at)
		p.global_position = at
		pickups.append(p)
		spawned.append(p)
	_point(center)


func _play_cinematic(epoch: int) -> void:
	if epoch != _epoch:
		return
	await game.cinematic.play(obj.id)
	if epoch != _epoch:
		return
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
	if state != "active" or not enemies.has(e):
		return
	Game.progress += 1
	Game.add_xp(12 if not e.boss else 120)
	_update_text()
	if Game.progress >= int(obj.count):
		_set_fight("")
		complete()


## How close the player must be to use the objective's prop.
func _prop_reach() -> float:
	return (prop.footprint() + 1.8) if prop else 3.0


## Called by the game when the player presses E near something of ours.
func try_interact() -> bool:
	if state != "active":
		return false
	var pp: Vector3 = game.player.global_position
	if obj.type == "talk" and target_npc and pp.distance_to(target_npc.global_position) < 2.8:
		_talk()
		return true
	if obj.type == "interact" and prop and _flat_dist(pp, prop.global_position) < _prop_reach():
		_interact()
		return true
	return false


func _flat_dist(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length() if absf(a.y - b.y) < 3.0 else INF


func prompt() -> String:
	if state != "active":
		return ""
	var pp: Vector3 = game.player.global_position
	match obj.type:
		"talk":
			if target_npc and pp.distance_to(target_npc.global_position) < 2.8:
				return "E  Talk to " + Story.npc(obj.npc).get("name", "")
		"interact":
			if prop and _flat_dist(pp, prop.global_position) < _prop_reach():
				return "E  " + Story.fill(obj.text)
		"meditate":
			if pp.distance_to(target_point) < 3.5 and not game.player.meditating:
				return "C  Meditate here"
	return ""


## Play an objective's conversation (its lines, then its choice and reply) as
## one scene; returns false when the objective changed underneath (map load).
func _scene(npc: Npc = null) -> bool:
	var ep := _epoch
	if not obj.get("dialogue") and not obj.get("choices"):
		return true
	game.scene_begin(npc)
	if obj.get("dialogue"):
		await game.converse(obj.dialogue, npc)
	if ep == _epoch:
		await _choose(npc)
	game.scene_end()
	return ep == _epoch


func _talk() -> void:
	state = "busy"
	var npc := target_npc
	npc.set_quest_target(false)
	if await _scene(npc):
		complete()


func _interact() -> void:
	state = "busy"
	Audio.sfx("chest_open" if obj.object == "treasure_chest" else "bell_toll" if obj.object == "bronze_bell" else "objective_update", -4.0)
	Fx.burst(game.map, prop.global_position + Vector3.UP, BEACON_GOLD, 40, 3.0)
	if await _scene():
		complete()


## A moral choice after the objective's dialogue: the options whose conditions
## hold are offered, the chosen one shifts the alignment, grants its reward,
## sets its flag and is answered by its reply lines.
func _choose(npc: Npc = null) -> void:
	var opts: Array = obj.get("choices", []) if obj.get("choices") else []
	if opts.is_empty():
		return
	var valid: Array = Game.valid_options(opts)
	if valid.is_empty():
		return
	var ep := _epoch
	var texts: Array = valid.map(func(o): return Story.fill(o.text))
	var i: int = await game.choose(Story.fill(obj.get("choice_prompt", "")), texts, npc)
	if ep != _epoch:
		return
	var op: Dictionary = valid[clampi(i, 0, valid.size() - 1)]
	var before := Game.alignment()
	Game.apply_choice(op, opts.find(op))
	var rw: Dictionary = op.get("reward", {})
	for item in rw.get("items", {}):
		game.hud.toast("+%d %s" % [int(rw.items[item]), Story.item_name(item)], UiTheme.JADE)
	if Game.alignment() != before:
		game.hud.toast("Your path turns: " + Game.alignment_name(), UiTheme.GOLD)
	var reply: Array = op.get("reply", []) if op.get("reply") else []
	if not reply.is_empty():
		await game.converse(reply, npc)


func _process(delta: float) -> void:
	if state != "active" or game.busy or game.dialogue.active or game.cinematic.active:
		return
	var player: Node3D = game.player
	var pp := player.global_position
	match obj.type:
		"talk":
			if target_npc and is_instance_valid(target_npc):
				_point(target_npc.global_position)
		"reach":
			if Vector2(pp.x - target_point.x, pp.z - target_point.z).length() < float(obj.get("radius", 4.0)) \
					and absf(pp.y - target_point.y) < 6.0 and not player.dead:
				state = "busy"
				if await _scene():
					complete()
		"tribulation":
			if trib == null:
				return
			if trib.running:
				var near := trib.enemies.filter(func(e): return is_instance_valid(e) and not e.dead)
				_point(near[0].global_position if not near.is_empty() else trib.global_position)
				game.hud.show_boss("Heavenly Tribulation", 1.0 - float(trib.done) / trib.volleys)
			elif not trib.finished:
				_point(trib.global_position)
				var d := Vector2(pp.x - trib.global_position.x, pp.z - trib.global_position.z).length()
				if d < 5.0 and absf(pp.y - trib.global_position.y) < 6.0 and not player.dead:
					state = "busy"
					var ep := _epoch
					if obj.get("dialogue") and not _fight_talked:
						_fight_talked = true
						game.scene_begin()
						await game.converse(obj.dialogue)
						game.scene_end()
					if ep != _epoch:
						return
					state = "active"
					_trib_failed = false
					_set_fight("boss")
					trib.begin(player)
					_update_text()
		"defeat":
			if obj.get("dialogue") and not _fight_talked and pp.distance_to(target_point) < 24.0:
				_fight_talked = true
				state = "busy"
				var ep := _epoch
				game.scene_begin()
				await game.converse(obj.dialogue)
				game.scene_end()
				if ep != _epoch:
					return
				state = "active"
				# the fight may have ended while they talked (a blast already in flight)
				if Game.progress >= int(obj.count):
					complete()
					return
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
				if pp.distance_to(p.global_position + Vector3.UP * 0.4) < 1.5 and not player.dead:
					p.take()
					Game.progress += 1
					Game.add_item(obj.item)
					_update_text()
					if Game.progress >= int(obj.count):
						state = "busy"
						if await _scene():
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
					player.stop_meditation()
					if await _scene():
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
	_dismiss_party()
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
		Game.set_realm(r.realm, int(r.stage) if r.get("stage") != null else 1)
	elif r.get("stage") != null:
		Game.set_stage(int(r.stage))
	# who the player has become shows in what the world gives back
	for b in r.get("bonus", []):
		if Game.cond_ok(b.get("cond")):
			Game.add_xp(int(b.get("xp", 0)))
			for item in b.get("items", {}):
				Game.add_item(item, int(b.items[item]))
			game.hud.toast(b.get("note", ""), UiTheme.JADE)
	quest_completed.emit(q.id)
	var vol := int(q.get("volume", 1))
	if Story.ends_volume(q) and not Game.finished():
		# a volume ends: its banner now, the next volume's title card a moment later
		game.hud.banner("Volume %s Complete" % Story.roman(vol), Story.volume(vol).get("subtitle", ""), 4.0)
		var nv := Story.volume(vol + 1)
		if not nv.is_empty():
			game.hud.title_card(Story.volume_label(vol + 1), nv.get("subtitle", ""), 5.0, 0.0 if Game.fast else 5.5)
		_victory_music()
	elif Story.ends_chapter(q):
		var ch := Story.chapter(int(q.chapter))
		game.hud.banner("Chapter %d Complete" % int(q.chapter), ch.get("title", ""), 4.0)
		_victory_music()
	if not Game.finished():
		if Story.ends_chapter(q):
			var recap := Story.latest_beat(Game.quest_index)
			if recap != "":
				game.hud.toast("Previously... " + recap, UiTheme.MUTED, 6.0)
		var nq := Game.quest()
		game.hud.toast("New quest: " + nq.title, UiTheme.JADE)
		game.hud.quest_card(nq)
		Audio.sfx("quest_accept", -6.0)
	else:
		game.hud.banner("Immortal Ascension", "The saga of the Azure Cloud Sect is complete", 6.0)


## The victory fanfare, then back to the map's music, unless a fight (or a
## newer fanfare, or a new map) has taken the music over in the meantime.
func _victory_music() -> void:
	if Game.fast:
		return
	Audio.play_music("victory", 0.5)
	var t := get_tree().create_timer(12.0)
	_music_timer = t
	t.timeout.connect(func():
		if _music_timer == t and is_instance_valid(game) and game.map and _fighting == "" \
				and Audio.current_music == "victory":
			Audio.play_music(game.map.music))


func _on_volley(_done: int, _total: int) -> void:
	Game.progress = _done
	_update_text()


func _on_wave(list: Array) -> void:
	for e in list:
		e.aggroed.connect(_on_aggro)


func _on_tribulation_survived() -> void:
	if state != "active" or obj.type != "tribulation":
		return
	state = "busy"
	game.hud.show_boss("", -1.0)
	_set_fight("")
	Audio.sfx("breakthrough", -4.0)
	Fx.burst(game.map, game.player.global_position + Vector3.UP, Color(0.75, 0.85, 1.0), 120, 6.0, 0.06)
	game.hud.banner("Tribulation Survived", Story.fill(obj.text).replace("Survive the ", "You endured the "), 3.5)
	if game.player.meditating:
		game.player.stop_meditation()
	complete()


func _on_tribulation_failed() -> void:
	_trib_failed = true
	Game.progress = 0
	game.hud.show_boss("", -1.0)
	_set_fight("")
	game.hud.toast("The lightning strikes you down. Steady yourself and face heaven again.", UiTheme.CRIMSON)
	_update_text()

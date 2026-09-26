extends Node3D
## The playing session: loads maps behind a loading screen, keeps the player,
## HUD, dialogue, cinematics and the quest runner alive across maps.

signal map_loaded(map_id: String)

const MAP_DIR := "res://scenes/maps/"
const HudScript := preload("res://scripts/ui/hud.gd")
const DialogueScript := preload("res://scripts/ui/dialogue_ui.gd")
const CinematicScript := preload("res://scripts/ui/cinematic.gd")
const LoadingScript := preload("res://scripts/ui/loading_screen.gd")
const JournalScript := preload("res://scripts/ui/journal.gd")
const TravelScript := preload("res://scripts/ui/travel_menu.gd")
const RunnerScript := preload("res://scripts/quest_runner.gd")

var map: Node3D
var hud: CanvasLayer
var dialogue: CanvasLayer
var cinematic: CanvasLayer
var loading: CanvasLayer
var journal: CanvasLayer
var travel: CanvasLayer
var runner: Node
var busy := true
var npcs := {}                 ## npc id -> Npc on the current map
var first_load := true

@onready var player: CharacterBody3D = $Player


func _ready() -> void:
	hud = HudScript.new()
	dialogue = DialogueScript.new()
	cinematic = CinematicScript.new()
	cinematic.game = self
	loading = LoadingScript.new()
	journal = JournalScript.new()
	travel = TravelScript.new()
	runner = RunnerScript.new()
	runner.game = self
	for n in [hud, dialogue, cinematic, loading, journal, travel, runner]:
		add_child(n)
	hud.player = player
	player.controls_enabled = false
	player.interact_pressed.connect(_on_interact)
	player.died.connect(_on_player_died)
	player.hp_changed.connect(hud.set_hp)
	player.qi_changed.connect(hud.set_qi)
	player.character_changed.connect(func(_n): hud.refresh())
	Game.realm_changed.connect(_on_breakthrough)
	Game.stage_changed.connect(_on_stage)
	journal.quit_to_title.connect(func(): get_tree().change_scene_to_file("res://scenes/title.tscn"))
	travel.chosen.connect(func(m): travel_to(m))
	player.refill()
	load_map(Game.map_id)


func _unhandled_input(event: InputEvent) -> void:
	if busy or dialogue.active or cinematic.active:
		return
	if event.is_action_pressed("journal"):
		journal.show_page("quest")
	elif event.is_action_pressed("pause"):
		if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			journal.show_page("quest")


## Load a map behind the loading screen and place the player at a marker.
func load_map(map_id: String, spawn := "PlayerSpawn") -> void:
	busy = true
	player.controls_enabled = false
	player.stop_meditation()
	if map:
		runner.clear()
	var q := Game.quest()
	var sub := ""
	if not q.is_empty():
		sub = "%s  —  %s" % [Story.volume_label(int(q.get("volume", 1))), Story.chapter_label(int(q.chapter))]
	loading.open(map_id, sub)
	Audio.play_music("", 0.6)
	var path := MAP_DIR + map_id + ".tscn"
	ResourceLoader.load_threaded_request(path)
	var progress := []
	while ResourceLoader.load_threaded_get_status(path, progress) == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
		loading.set_progress(progress[0] if progress.size() > 0 else 0.0)
		await get_tree().process_frame
	var scene := ResourceLoader.load_threaded_get(path) as PackedScene
	if map:
		for n in npcs.values():
			n.queue_free()
		npcs.clear()
		map.queue_free()
		map = null
		await get_tree().process_frame
	map = scene.instantiate()
	add_child(map)
	move_child(map, 0)
	loading.set_progress(1.0)
	for i in 3:
		await get_tree().physics_frame
	Game.map_id = map_id
	if not Game.visited.has(map_id):
		Game.visited.append(map_id)
	var p: Vector3 = map.marker_position(spawn)
	player.global_position = p + Vector3.UP * 0.3
	player.spawn_point = player.global_position
	player.velocity = Vector3.ZERO
	var tp: Vector3 = map.marker_position("TeleportArray")
	var away := p - tp
	player.model_root.rotation.y = atan2(away.x, away.z)
	refresh_npcs()
	Audio.play_music(map.music)
	if not Game.fast:
		await get_tree().create_timer(0.6).timeout
	loading.close()
	hud.banner(Story.map_name(map_id), sub)
	busy = false
	player.controls_enabled = true
	map_loaded.emit(map_id)
	runner.activate()
	if first_load and Game.objective_index == 0 and Game.objective().get("type") != "cinematic":
		hud.quest_card(Game.quest())
	first_load = false


func travel_to(map_id: String) -> void:
	if busy or map_id == Game.map_id:
		return
	Audio.sfx("teleport", -3.0)
	Fx.burst(map, player.global_position + Vector3.UP, Color(0.5, 1.0, 0.9), 80, 4.0)
	if not Game.fast:
		await get_tree().create_timer(0.5).timeout
	await load_map(map_id, "TeleportArray")
	Game.save()


## Place ambient NPCs whose home is this map (respecting story progress).
func refresh_npcs() -> void:
	if map == null:
		return
	var keep := {}
	for id in Story.npcs:
		var d: Dictionary = Story.npcs[id]
		var home = d.get("home")
		if home == null or home.map != Game.map_id or not _present(d):
			continue
		keep[id] = home.marker
	# the active talk target stays wherever the objective wants it
	var obj := Game.objective()
	var pinned := ""
	if obj.get("type") == "talk" and obj.map == Game.map_id:
		pinned = obj.npc
	for id in npcs.keys():
		if id != pinned and not keep.has(id):
			npcs[id].queue_free()
			npcs.erase(id)
	for id in keep:
		if id == pinned and npcs.has(id):
			continue
		ensure_npc(id, keep[id])


func _present(d: Dictionary) -> bool:
	var from = d.get("appear_from")
	if from and _quest_pos(from) > Game.quest_index:
		return false
	var until = d.get("hidden_after")
	if until and _quest_pos(until) < Game.quest_index:
		return false
	return true


func _quest_pos(id: String) -> int:
	return int(id.substr(1)) - 1


## Get (or spawn) an NPC and stand it on a marker facing the arrival point.
func ensure_npc(id: String, marker: String) -> Npc:
	var n: Npc = npcs.get(id)
	if n == null or not is_instance_valid(n):
		n = Npc.create(id)
		map.add_child(n)
		npcs[id] = n
	var p: Vector3 = map.marker_position(marker)
	if n.global_position.distance_to(p) > 0.5:
		n.global_position = p
		var look: Vector3 = map.marker_position("PlayerSpawn")
		if look.distance_to(p) < 3.0:
			look = map.marker_position("TeleportArray")
		var to := look - p
		n.rotation.y = atan2(to.x, to.z)
	return n


func find_npc(id: String) -> Npc:
	var n = npcs.get(id)
	return n if n and is_instance_valid(n) else null


## Run a conversation; the speaking NPC (if any) faces the player and gestures.
func converse(lines: Array, npc: Npc = null) -> void:
	player.controls_enabled = false
	player.velocity = Vector3.ZERO
	player.stop_meditation()
	hud.set_prompt("")
	if npc:
		npc.face(player.global_position)
		var to := npc.global_position - player.global_position
		player.model_root.rotation.y = atan2(to.x, to.z)
	var speaking := func(speaker: String):
		for n in npcs.values():
			if is_instance_valid(n):
				n.set_talking(n.npc_id == speaker)
		if player.anim and not player.dead:
			player.anim.play("talk" if speaker == "player" else "idle", 0.3)
	dialogue.line_started.connect(speaking)
	await dialogue.play(lines)
	dialogue.line_started.disconnect(speaking)
	for n in npcs.values():
		if is_instance_valid(n):
			n.set_talking(false)
	if player.anim and not player.dead:
		player.anim.play("idle", 0.3)
	player.controls_enabled = true


func _process(_delta: float) -> void:
	if busy or map == null:
		return
	if player.global_position.y < map.kill_y:
		player.respawn(player.spawn_point)
	if dialogue.active or cinematic.active:
		hud.set_prompt("")
		return
	var text: String = runner.prompt()
	if text == "":
		if _near_teleport():
			text = "E  Use the teleport array"
		else:
			var n := _near_npc()
			if n:
				text = "E  Talk to " + n.data.get("name", "")
	hud.set_prompt(text)


func _near_teleport() -> bool:
	return player.global_position.distance_to(map.marker_position("TeleportArray")) < 4.5


func _near_npc() -> Npc:
	for n in npcs.values():
		if is_instance_valid(n) and n.visible and player.global_position.distance_to(n.global_position) < 2.4:
			return n
	return null


func _on_interact() -> void:
	if busy or dialogue.active or cinematic.active:
		return
	if runner.try_interact():
		return
	if _near_teleport():
		var o := Game.objective()
		travel.show_for(Game.map_id, o.get("map", "") if not o.is_empty() else "")
		return
	var n := _near_npc()
	if n:
		var barks: Array = n.data.get("barks", [])
		if not barks.is_empty():
			converse([{"speaker": n.npc_id, "text": barks[randi() % barks.size()], "voice": ""}], n)


func _on_player_died() -> void:
	hud.toast("You have fallen. Your dao heart endures...", UiTheme.CRIMSON)
	Audio.sfx("gameover", -2.0)
	await get_tree().create_timer(3.0 if not Game.fast else 0.05).timeout
	var at: Vector3 = map.marker_position("PlayerSpawn") + Vector3.UP * 0.3
	player.respawn(at)
	for e in get_tree().get_nodes_in_group("enemies"):
		e.hp = e.max_hp


func _on_breakthrough(realm: String) -> void:
	hud.banner("Breakthrough!", "You have reached " + realm, 4.0)
	Audio.sfx("breakthrough", 0.0)
	if map:
		Fx.burst(map, player.global_position + Vector3.UP, Color(1.0, 0.85, 0.4), 160, 6.0, 0.06)
	player.refill()


## A minor stage within the realm (Middle, Late, Peak).
func _on_stage(label: String) -> void:
	hud.banner("Cultivation Deepens", label, 3.5)
	Audio.sfx("breakthrough", -6.0)
	if map:
		Fx.burst(map, player.global_position + Vector3.UP, Color(0.55, 1.0, 0.85), 90, 4.0, 0.05)
	player.refill()

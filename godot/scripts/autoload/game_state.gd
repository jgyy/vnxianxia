extends Node
## Persistent game progress: the active quest/objective, cultivation realm and
## minor stage, inventory and the protagonist. Saved to user://save.json after
## every objective.

signal changed
signal realm_changed(realm: String)
signal stage_changed(label: String)

const SAVE_PATH := "user://save.json"
## save format 2: quest indices of the 1000-quest saga (format 1 = the original 100 quests)
const SAVE_VERSION := 2
const XP_PER_REALM := 1000

var character := 0              ## 0 = Lin Feng, 1 = Su Yue
var quest_index := 0
var objective_index := 0
var progress := 0               ## counter for defeat/collect objectives
var xp := 0
var realm := 0
var stage := 0                  ## minor stage within the realm: 0 Early, 1 Middle, 2 Late, 3 Peak
var inventory: Dictionary = {}
var map_id := "sect"
var visited: Array = ["sect"]
var completed: Array = []
## Test hook: skip waits (typewriter, voice, fades) so a walkthrough runs fast.
var fast := false


func reset() -> void:
	quest_index = 0
	objective_index = 0
	progress = 0
	xp = 0
	realm = 0
	stage = 0
	inventory = {}
	map_id = "sect"
	visited = ["sect"]
	completed = []
	changed.emit()


func quest() -> Dictionary:
	return Story.quest(quest_index)


func objective() -> Dictionary:
	var q := quest()
	if q.is_empty():
		return {}
	var objs: Array = q.objectives
	return objs[objective_index] if objective_index < objs.size() else {}


func finished() -> bool:
	return quest_index >= Story.quests.size()


func add_item(item: String, count := 1) -> void:
	inventory[item] = int(inventory.get(item, 0)) + count
	changed.emit()


func add_xp(amount: int) -> void:
	xp += amount
	changed.emit()


## Break through to a major realm; the minor stage starts again at Early.
func set_realm(name: String) -> void:
	var i := Story.realm_index(name)
	if i > realm:
		realm = i
		stage = 0
		realm_changed.emit(name)
		changed.emit()


func set_stage(s: int) -> void:
	if s > stage:
		stage = s
		stage_changed.emit(realm_label())
		changed.emit()


func realm_label() -> String:
	return Story.realm_label(realm, stage)


## Cultivation stats scale with the realm, and a little with the minor stage.
func power() -> float:
	return realm + 0.2 * stage


func max_hp() -> float:
	return 100.0 + 45.0 * power()


func max_qi() -> float:
	return 60.0 + 20.0 * power()


func strike_damage() -> float:
	return 14.0 + 9.0 * power()


func blast_damage() -> float:
	return 34.0 + 18.0 * power()


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save() -> void:
	if fast:
		return
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({
		"version": SAVE_VERSION, "character": character, "quest": quest_index, "objective": objective_index,
		"progress": progress, "xp": xp, "realm": realm, "stage": stage, "inventory": inventory,
		"map": map_id, "visited": visited,
	}, "  "))


func load_save() -> bool:
	if not has_save():
		return false
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return false
	var version := int(d.get("version", 1))
	var q := int(d.get("quest", 0))
	var obj := int(d.get("objective", 0))
	var prog := int(d.get("progress", 0))
	if version < 2:
		# a save of the original 100-quest story: continue at the same quest of the saga
		var mapped := Story.legacy_index(q + 1) if q < 100 else Story.quests.size()
		if mapped < 0:
			mapped = 0
			obj = 0
			prog = 0
		q = mapped
	var keep_xp := int(d.get("xp", 0))
	var keep_inv: Dictionary = d.get("inventory", {})
	var keep_visited: Array = d.get("visited", ["sect"])
	var keep_map: String = d.get("map", "sect")
	start_at(q)                 # recompute realm, stage and the chronicle from the story itself
	character = int(d.get("character", 0))
	quest_index = clampi(q, 0, Story.quests.size())
	objective_index = obj
	progress = prog
	xp = maxi(keep_xp, xp)
	inventory = keep_inv
	visited = keep_visited
	map_id = keep_map if Story.world.maps.has(keep_map) else "sect"
	if not quest().is_empty() and objective_index >= (quest().objectives as Array).size():
		objective_index = 0
		progress = 0
	changed.emit()
	return true


## Jump to a quest (chapter select, loading a save, test shards) with the realm,
## minor stage, rewards and chronicle of every earlier quest applied.
func start_at(index: int) -> void:
	reset()
	quest_index = clampi(index, 0, Story.quests.size())
	for i in mini(quest_index, Story.quests.size()):
		var q := Story.quest(i)
		completed.append(q.id)
		var r: Dictionary = q.rewards
		var rn = r.get("realm")
		if rn:
			var ri := Story.realm_index(rn)
			if ri > realm:
				realm = ri
				stage = 0
		var st = r.get("stage")
		if st != null and int(st) > stage:
			stage = int(st)
		xp += int(r.get("xp", 0))
		var items: Dictionary = r.get("items", {})
		for item in items:
			inventory[item] = int(inventory.get(item, 0)) + int(items[item])
	if quest_index < Story.quests.size():
		map_id = Story.quest(quest_index).map
	if not visited.has(map_id):
		visited.append(map_id)
	changed.emit()

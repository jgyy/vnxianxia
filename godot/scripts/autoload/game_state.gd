extends Node
## Persistent game progress: the active quest/objective, cultivation, inventory
## and the protagonist. Saved to user://save.json after every objective.

signal changed
signal realm_changed(realm: String)

const SAVE_PATH := "user://save.json"
const XP_PER_REALM := 1000

var character := 0              ## 0 = Lin Feng, 1 = Su Yue
var quest_index := 0
var objective_index := 0
var progress := 0               ## counter for defeat/collect objectives
var xp := 0
var realm := 0
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


func set_realm(name: String) -> void:
	var i := Story.realm_index(name)
	if i > realm:
		realm = i
		realm_changed.emit(name)
		changed.emit()


## Cultivation stats scale with the realm.
func max_hp() -> float:
	return 100.0 + 45.0 * realm


func max_qi() -> float:
	return 60.0 + 20.0 * realm


func strike_damage() -> float:
	return 14.0 + 9.0 * realm


func blast_damage() -> float:
	return 34.0 + 18.0 * realm


func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save() -> void:
	if fast:
		return
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify({
		"character": character, "quest": quest_index, "objective": objective_index,
		"progress": progress, "xp": xp, "realm": realm, "inventory": inventory,
		"map": map_id, "visited": visited, "completed": completed,
	}, "  "))


func load_save() -> bool:
	if not has_save():
		return false
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return false
	character = int(d.get("character", 0))
	quest_index = int(d.get("quest", 0))
	objective_index = int(d.get("objective", 0))
	progress = int(d.get("progress", 0))
	xp = int(d.get("xp", 0))
	realm = int(d.get("realm", 0))
	inventory = d.get("inventory", {})
	map_id = d.get("map", "sect")
	visited = d.get("visited", ["sect"])
	completed = d.get("completed", [])
	changed.emit()
	return true


## Jump to a quest (chapter select / debugging) keeping realm progression sane.
func start_at(index: int) -> void:
	reset()
	quest_index = clampi(index, 0, Story.quests.size() - 1)
	for i in quest_index:
		var q := Story.quest(i)
		completed.append(q.id)
		var r = q.rewards.get("realm")
		if r:
			realm = maxi(realm, Story.realm_index(r))
		xp += int(q.rewards.get("xp", 0))
	map_id = Story.quest(quest_index).map
	if not visited.has(map_id):
		visited.append(map_id)
	changed.emit()

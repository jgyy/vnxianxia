extends Node
## The main story (res://data/story.json, compiled by tools/build_story.py):
## chapters, quests, NPC roster and cinematics, plus text-token substitution
## for the active protagonist.

const PATH := "res://data/story.json"
const WORLD_PATH := "res://data/world.json"
const PLAYER_NAMES := ["Lin Feng", "Su Yue"]

var chapters: Array = []
var quests: Array = []
var npcs: Dictionary = {}
var cinematics: Dictionary = {}
## tools/world_spec.py mirrored as JSON: maps, markers, enemies, items, realms.
var world: Dictionary = {}


func _ready() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	chapters = data.chapters
	quests = data.quests
	npcs = data.npcs
	cinematics = data.cinematics
	world = JSON.parse_string(FileAccess.get_file_as_string(WORLD_PATH))


func quest(index: int) -> Dictionary:
	return quests[index] if index >= 0 and index < quests.size() else {}


func chapter(number: int) -> Dictionary:
	for c in chapters:
		if int(c.number) == number:
			return c
	return {}


func npc(id: String) -> Dictionary:
	return npcs.get(id, {})


func map_name(map_id: String) -> String:
	return world.maps.get(map_id, {}).get("name", map_id.capitalize())


func realm_name(index: int) -> String:
	var realms: Array = world.realms
	return realms[clampi(index, 0, realms.size() - 1)]


func realm_index(realm: String) -> int:
	return (world.realms as Array).find(realm)


func item_name(item: String) -> String:
	return world.items.get(item, item.capitalize())


func speaker_name(speaker: String) -> String:
	match speaker:
		"player":
			return PLAYER_NAMES[Game.character]
		"narrator":
			return ""
	return npc(speaker).get("name", speaker.capitalize())


## Replace {player}, {junior}, {senior}, {sibling}, {they}, {them}, {their}.
func fill(text: String, character := -1) -> String:
	var c := Game.character if character < 0 else character
	var male := c == 0
	var tokens := {
		"{player}": PLAYER_NAMES[c],
		"{junior}": "Junior Brother" if male else "Junior Sister",
		"{senior}": "Senior Brother" if male else "Senior Sister",
		"{sibling}": "brother" if male else "sister",
		"{they}": "he" if male else "she",
		"{them}": "him" if male else "her",
		"{their}": "his" if male else "her",
	}
	for k in tokens:
		text = text.replace(k, tokens[k])
	return text


## Voice file for a dialogue line, honouring the gendered _m/_f variants.
func voice_path(line: Dictionary) -> String:
	var path: String = line.get("voice", "")
	if path.is_empty():
		return ""
	if line.get("gendered", false):
		path = path.replace(".ogg", "_m.ogg" if Game.character == 0 else "_f.ogg")
	return path

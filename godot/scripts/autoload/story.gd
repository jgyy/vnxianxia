extends Node
## The main story (res://data/story.json, compiled by tools/build_story.py):
## 10 volumes x 10 chapters x 10 quests, the NPC roster and cinematics, plus
## text-token substitution for the active protagonist.

const PATH := "res://data/story.json"
const WORLD_PATH := "res://data/world.json"
const PLAYER_NAMES := ["Lin Feng", "Su Yue"]
const STAGE_NAMES := ["Early", "Middle", "Late", "Peak"]

var title := ""
var premise := ""
var volumes: Array = []
var chapters: Array = []
var quests: Array = []
var npcs: Dictionary = {}
var cinematics: Dictionary = {}
## tools/world_spec.py mirrored as JSON: maps, markers, enemies, items, realms.
var world: Dictionary = {}
## milliseconds spent parsing story.json at startup
var load_msec := 0
var _chapter_index := {}
var _legacy := {}


func _ready() -> void:
	var t0 := Time.get_ticks_msec()
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	title = data.get("title", "")
	premise = data.get("premise", "")
	volumes = data.get("volumes", [])
	chapters = data.chapters
	quests = data.quests
	npcs = data.npcs
	cinematics = data.cinematics
	world = JSON.parse_string(FileAccess.get_file_as_string(WORLD_PATH))
	for i in chapters.size():
		_chapter_index[int(chapters[i].number)] = i
	for i in quests.size():
		var l = quests[i].get("legacy")
		if l != null:
			_legacy[int(l)] = i
	load_msec = Time.get_ticks_msec() - t0


func quest(index: int) -> Dictionary:
	return quests[index] if index >= 0 and index < quests.size() else {}


func chapter(number: int) -> Dictionary:
	var i: int = _chapter_index.get(number, -1)
	return chapters[i] if i >= 0 else {}


func volume(number: int) -> Dictionary:
	return volumes[number - 1] if number >= 1 and number <= volumes.size() else {}


## Index of the first quest of a chapter.
func chapter_first(number: int) -> int:
	return int(chapter(number).get("first", (number - 1) * 10))


## Is this quest the last one of its chapter / volume?
func ends_chapter(q: Dictionary) -> bool:
	var nq := quest(int(q.number))
	return nq.is_empty() or int(nq.chapter) != int(q.chapter)


func ends_volume(q: Dictionary) -> bool:
	var nq := quest(int(q.number))
	return nq.is_empty() or int(nq.get("volume", 1)) != int(q.get("volume", 1))


## "Volume III · Core Formation"
func volume_label(number: int) -> String:
	return "Volume %s · %s" % [roman(number), volume(number).get("title", "")]


## "Chapter 23 · Envoys of the Iron Scale"
func chapter_label(number: int) -> String:
	return "Chapter %d · %s" % [number, chapter(number).get("title", "")]


## Index in the 1000-quest story of quest ``n`` (1..100) of the original 100-quest story.
func legacy_index(n: int) -> int:
	return int(_legacy.get(n, -1))


func npc(id: String) -> Dictionary:
	return npcs.get(id, {})


func map_name(map_id: String) -> String:
	return world.maps.get(map_id, {}).get("name", map_id.capitalize())


func realm_name(index: int) -> String:
	var realms: Array = world.realms
	return realms[clampi(index, 0, realms.size() - 1)]


func realm_index(realm: String) -> int:
	return (world.realms as Array).find(realm)


func stage_name(stage: int) -> String:
	return STAGE_NAMES[clampi(stage, 0, STAGE_NAMES.size() - 1)]


## "Core Formation · Late" (Mortal and Immortal Ascension have no minor stages).
func realm_label(realm: int, stage: int) -> String:
	var r := realm_name(realm)
	if realm <= 0 or realm >= (world.realms as Array).size() - 1:
		return r
	return "%s · %s" % [r, stage_name(stage)]


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
## Lines of the chapters added for the 1000-quest saga are text-only: "".
func voice_path(line: Dictionary) -> String:
	var v = line.get("voice")
	if v == null or not (v is String) or (v as String).is_empty():
		return ""
	var path: String = v
	if line.get("gendered", false):
		path = path.replace(".ogg", "_m.ogg" if Game.character == 0 else "_f.ogg")
	return path


## Seconds an unvoiced line stays on screen before it advances by itself.
func reading_time(text: String) -> float:
	return clampf(1.6 + 0.3 * text.split(" ", false).size(), 2.5, 11.0)


static func roman(n: int) -> String:
	var vals := [10, 9, 5, 4, 1]
	var syms := ["X", "IX", "V", "IV", "I"]
	var out := ""
	for i in vals.size():
		while n >= vals[i]:
			out += syms[i]
			n -= vals[i]
	return out

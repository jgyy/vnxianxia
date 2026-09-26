extends Node
## Persistent game progress: the active quest/objective, cultivation (major
## realm and minor stage), alignment, choices and flags, inventory and the
## protagonist. Saved to user://save.json after every objective.
##
## Cultivation: ``realm`` indexes Story.world.realms (0 Mortal, 1..10 the ten
## major stages, 11 Immortal Ascension); ``stage`` is the minor stage 1..10
## within a major realm (10 = Great Perfection), 0 for Mortal and Immortal.
## Alignment: ``law`` (Law +100 .. Chaos -100) and ``good`` (Good +100 ..
## Evil -100) give the nine alignments, see alignment().

signal changed
## a major breakthrough; ``realm`` is the realm's name
signal realm_changed(realm: String)
## the minor stage changed (also on a breakthrough, where it restarts at 1)
signal stage_changed(realm: int, stage: int)
## the alignment id changed ("lawful_good" .. "chaotic_evil")
signal alignment_changed(alignment: String)

const SAVE_PATH := "user://save.json"
## save format 3: cultivation stages 1..10, alignment, choices, flags
## (2 = the saga with four minor stages, 1 = the original 100 quests)
const SAVE_VERSION := 3
const XP_PER_REALM := 1000
const ALIGN_LAW := ["lawful", "neutral", "chaotic"]
const ALIGN_MORAL := ["good", "neutral", "evil"]

var character := 0              ## 0 = Lin Feng, 1 = Su Yue
var quest_index := 0
var objective_index := 0
var progress := 0               ## counter for defeat/collect objectives, volleys of a tribulation
var xp := 0
var realm := 0
var stage := 0                  ## minor stage 1..10 within the realm (10 = Great Perfection); 0 = none
var law := 0                    ## -100 chaotic .. +100 lawful
var good := 0                   ## -100 evil .. +100 good
var flags: Dictionary = {}      ## flag -> true, set by choices
var attitude: Dictionary = {}   ## npc id -> int, how an NPC feels about the player
var choices: Dictionary = {}    ## "q0123/2" -> index of the option chosen there
var inventory: Dictionary = {}
var map_id := "sect"
var visited: Array = ["sect"]
var completed: Array = []
## Test hook: skip waits (typewriter, voice, fades) so a walkthrough runs fast.
## In fast mode choices are made by auto_choice().
var fast := false
## Offset for auto_choice(), so test runs can steer toward different alignments.
var choice_seed := 0


func reset() -> void:
	quest_index = 0
	objective_index = 0
	progress = 0
	xp = 0
	realm = 0
	stage = 0
	law = 0
	good = 0
	flags = {}
	attitude = {}
	choices = {}
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


# ------------------------------------------------------------------ cultivation

func _last_realm() -> int:
	return (Story.world.realms as Array).size() - 1


## Break through to a major realm, which starts at minor stage ``s`` (1).
func set_realm(name: String, s := 1) -> void:
	var i := Story.realm_index(name)
	if i > realm:
		realm = i
		stage = 0 if i == 0 or i == _last_realm() else clampi(s, 1, 10)
		realm_changed.emit(name)
		stage_changed.emit(realm, stage)
		changed.emit()


## Reach minor stage ``s`` (1..10) of the current realm.
func set_stage(s: int) -> void:
	if s > stage and realm > 0 and realm < _last_realm():
		stage = clampi(s, 1, 10)
		stage_changed.emit(realm, stage)
		changed.emit()


## "Core Formation · 7th Layer (Late)"
func realm_label() -> String:
	return Story.realm_label(realm, stage)


## Cultivation power: one per major realm, a tenth of one per minor stage.
## Qi Condensation 1st Layer = 1.0, its Great Perfection = 1.9, Foundation 1st Layer = 2.0.
func power() -> float:
	return realm + 0.1 * maxi(stage - 1, 0)


func max_hp() -> float:
	return 100.0 + 45.0 * power()


func max_qi() -> float:
	return 60.0 + 20.0 * power()


func strike_damage() -> float:
	return 14.0 + 9.0 * power()


func blast_damage() -> float:
	return 34.0 + 18.0 * power()


# ------------------------------------------------------------------ alignment

## "lawful_good", "neutral_evil", "neutral_neutral" (true neutral), ...
func alignment() -> String:
	var t := int(Story.world.get("align_threshold", 25))
	var a := "lawful" if law >= t else ("chaotic" if law <= -t else "neutral")
	var b := "good" if good >= t else ("evil" if good <= -t else "neutral")
	return a + "_" + b


func alignment_name() -> String:
	return Story.alignment_name(alignment())


## Move along the two axes (clamped to -100..100).
func shift_alignment(d_law: int, d_good: int) -> void:
	var before := alignment()
	var r := int(Story.world.get("align_range", 100))
	law = clampi(law + d_law, -r, r)
	good = clampi(good + d_good, -r, r)
	if alignment() != before:
		alignment_changed.emit(alignment())
	changed.emit()


## Does a story condition hold? (see tools/build_story.py check_cond)
func cond_ok(cond) -> bool:
	if cond == null or not (cond is Dictionary):
		return true
	for k in cond:
		var v = cond[k]
		match k:
			"align":
				var any := false
				for pat in (v if v is Array else [v]):
					if _align_match(pat):
						any = true
				if not any:
					return false
			"align_law":
				if not _compare(law, v):
					return false
			"align_good":
				if not _compare(good, v):
					return false
			"min_realm":
				if realm < Story.realm_index(v):
					return false
			"max_realm":
				if realm > Story.realm_index(v):
					return false
			"min_stage":
				if stage < int(v):
					return false
			"max_stage":
				if stage > int(v):
					return false
			"flag":
				if not flags.has(v):
					return false
			"not_flag":
				if flags.has(v):
					return false
			"likes":
				if int(attitude.get(v, 0)) <= 0:
					return false
			"dislikes":
				if int(attitude.get(v, 0)) >= 0:
					return false
			_:
				return false
	return true


func _align_match(pat: String) -> bool:
	var want := pat.split("_")
	var have := alignment().split("_")
	return want.size() == 2 and (want[0] == "*" or want[0] == have[0]) and (want[1] == "*" or want[1] == have[1])


func _compare(value: int, expr: String) -> bool:
	var ops := [">=", "<=", "==", ">", "<"]
	for op in ops:
		if expr.begins_with(op):
			var n := int(expr.substr(op.length()))
			match op:
				">=":
					return value >= n
				"<=":
					return value <= n
				"==":
					return value == n
				">":
					return value > n
				"<":
					return value < n
	return false


## The options of a choice whose conditions hold (always at least one).
func valid_options(options: Array) -> Array:
	var out := []
	for op in options:
		if cond_ok(op.get("cond")):
			out.append(op)
	return out


## The option picked in fast mode (tests): varies with the quest and objective,
## so a walkthrough makes lawful, chaotic, good and evil choices in turn.
func auto_choice(count: int) -> int:
	return (quest_index * 7 + objective_index * 3 + choice_seed) % maxi(count, 1)


## Record a choice made at the current objective and apply what it does.
func apply_choice(option: Dictionary, index: int) -> void:
	var q := quest()
	choices["%s/%d" % [q.get("id", "?"), objective_index]] = index
	var a: Dictionary = option.get("align", {})
	var rw: Dictionary = option.get("reward", {})
	xp += int(rw.get("xp", 0))
	var items: Dictionary = rw.get("items", {})
	for item in items:
		inventory[item] = int(inventory.get(item, 0)) + int(items[item])
	var f = option.get("flag")
	if f:
		flags[f] = true
	var att: Dictionary = option.get("attitude", {})
	for npc in att:
		attitude[npc] = int(attitude.get(npc, 0)) + int(att[npc])
	shift_alignment(int(a.get("law", 0)), int(a.get("good", 0)))


# ------------------------------------------------------------------ saving

func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save_dict() -> Dictionary:
	return {
		"version": SAVE_VERSION, "character": character, "quest": quest_index, "objective": objective_index,
		"progress": progress, "xp": xp, "realm": realm, "stage": stage, "inventory": inventory,
		"map": map_id, "visited": visited, "law": law, "good": good, "flags": flags,
		"attitude": attitude, "choices": choices,
	}


func save() -> void:
	if fast:
		return
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		return
	f.store_string(JSON.stringify(save_dict(), "  "))


func load_save() -> bool:
	if not has_save():
		return false
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if typeof(d) != TYPE_DICTIONARY:
		return false
	return load_dict(d)


## Restore from a save dictionary. Cultivation is recomputed from the story
## (a save from before minor stages or of the original 100 quests still loads).
func load_dict(d: Dictionary) -> bool:
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
	law = int(d.get("law", 0))
	good = int(d.get("good", 0))
	flags = d.get("flags", {})
	attitude = d.get("attitude", {})
	choices = d.get("choices", {})
	# the objective may have been added since (a tribulation in a voiced quest): start that quest over
	if version < SAVE_VERSION and not quest().is_empty() and objective_index > 0:
		for o in quest().objectives:
			if o.type == "tribulation":
				objective_index = 0
				progress = 0
	if not quest().is_empty() and objective_index >= (quest().objectives as Array).size():
		objective_index = 0
		progress = 0
	changed.emit()
	return true


## Jump to a quest (chapter select, loading a save, test shards) with the realm,
## minor stage, rewards and chronicle of every earlier quest applied. Alignment
## starts neutral; choices are only made by playing.
func start_at(index: int) -> void:
	reset()
	quest_index = clampi(index, 0, Story.quests.size())
	for i in mini(quest_index, Story.quests.size()):
		var q := Story.quest(i)
		completed.append(q.id)
		var r: Dictionary = q.rewards
		var rn = r.get("realm")
		var st = r.get("stage")
		if rn:
			var ri := Story.realm_index(rn)
			if ri > realm:
				realm = ri
				stage = 0 if ri == _last_realm() else (int(st) if st != null else 1)
		elif st != null and int(st) > stage:
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

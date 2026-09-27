extends Node
## The protagonist thinks out loud while roaming. Lin Feng and Su Yue are
## chatty: idle thoughts about wherever they are, what they're meant to be
## doing, who they are becoming (alignment) and the saga so far (plot
## callbacks that unlock as the story advances). Silent during dialogue,
## cinematics, combat, meditation and menus so it never talks over anything
## that matters.
##
## Purely cosmetic flavour text shown through HUD.say_thought(); nothing here
## is saved, voiced or validated by the story pipeline.

var game: Node

var _cooldown := 0.0
var _recent: Array[String] = []
const RECENT_MAX := 10
const MIN_GAP := 13.0
const MAX_GAP := 27.0

# ---------------------------------------------------------------- idle chatter

const IDLE := [
	"Nine thousand steps up, and I still catch myself counting them out of habit.",
	"Quiet out here. I could get used to quiet. I probably won't get the chance.",
	"If I stop moving, someone always finds a chore for me. Best keep walking.",
	"I wonder what I was before all this. Probably shorter.",
	"Talking to myself again. Well, the wind's not much of a conversationalist either.",
	"Every road on this mountain eventually leads back to a chore.",
	"I used to think cultivators were supposed to look serene. I mostly look tired.",
	"Someday I'll take a whole afternoon and do absolutely nothing with it.",
	"The pendant's warm today. It does that sometimes. I've stopped asking why.",
	"Funny — a year ago I'd never held a sword. Now I argue with them about form.",
	"I keep a mental list of things to ask Elder Bai. It's mostly questions he'll dodge.",
	"Whoever said cultivation was peaceful clearly never met a training puppet.",
	"I should write some of this down. 'Dear journal: today I talked to a rock.'",
	"Breathe in, breathe out. Elder Hua would be proud. Mostly I'm just stalling.",
	"I wonder if the wolves remember me, or if I just look like lunch to everyone.",
	"There's a version of me that stayed a farmer. I hope she's having a nicer week.",
	"Half of cultivation is discipline. The other half is pretending you're not lost.",
	"I keep expecting someone to tell me I'm not allowed to be here. Nobody has yet.",
	"The steward would say I'm burning daylight. The steward says that about everything.",
	"Some days the mountain feels like home. Today's one of the good days.",
]

# ---------------------------------------------------------------- per-map flavour

const BY_MAP := {
	"sect": [
		"Nine thousand steps below, Qingshi's probably still arguing about the price of rice.",
		"The Azure Eye hums differently when it's about to be tested. I've learned to listen for it.",
		"Every peak here has its own weather. I've stopped trusting the one over the Law Hall.",
		"Somewhere in this sect, forty new disciples are dreading the puppet hall exactly as much as I once did.",
		"The carp in Elder Mo's pond outlived him. That still doesn't feel fair.",
	],
	"bamboo_forest": [
		"The bamboo groans like it's complaining about something. Could be the wind. Could be everything else.",
		"Hard to believe a hermit hid in here for three hundred years and only I noticed the tea smoke.",
		"Every path through here used to mean wolves. Now it mostly means memories.",
		"The spirit spring runs cleaner than it used to. Small mercies count.",
		"I still check the old den out of habit, even though nothing waits there anymore.",
	],
	"qingshi_town": [
		"Madam Fang's noodles taste like a good day, even on a bad one.",
		"Half this town has a story about the new moon they still won't tell straight.",
		"The magistrate finally stands up straight. Small miracles happen slowly.",
		"I know these streets better than the mountain, if I'm honest.",
		"Someone always waves. It still catches me off guard, every single time.",
	],
	"blood_abyss": [
		"The air down here tastes like old iron. I don't think that's just the blood pools.",
		"Every obelisk we broke, and the ground still remembers what stood on it.",
		"I don't like how quiet the fold gets. Quiet, down here, is never good news.",
		"Somewhere past that gate, three hundred years of grudges are still waiting.",
		"I try not to look at the cages too long. Some things don't need a second look.",
	],
	"sky_isles": [
		"The clouds up here don't behave like clouds should. I've made my peace with that.",
		"Qing Luan says the stars disagree with our formation. I still don't like how she says it.",
		"Thin air, thinner ground, and somehow the view is worth every step of the bridge.",
		"You can see the whole sect from up here, small as a coin. Puts the chores in perspective.",
		"Something about this place makes me want to tell the truth. Maybe that's the point of it.",
	],
}

# ---------------------------------------------------------------- per-objective flavour

const BY_OBJECTIVE := {
	"talk": [
		"I should go find them. Whatever this is about, it's easier said face to face.",
		"Best not to keep them waiting. People remember who kept them waiting.",
	],
	"reach": [
		"Not far now. My legs disagree, but my legs are rarely consulted.",
		"Just have to get there in one piece. That part's usually the hard part.",
	],
	"defeat": [
		"I can feel them before I see them. That's either cultivation or nerves. Possibly both.",
		"Let's get this over with cleanly. Heroics are exhausting.",
	],
	"collect": [
		"Somewhere around here, probably under something inconvenient.",
		"I've gotten disturbingly good at finding things nobody wants to lose in public.",
	],
	"interact": [
		"Let's see what this actually is before I decide how I feel about it.",
		"Some things want to be looked at up close. This is apparently one of them.",
	],
	"meditate": [
		"Time to sit down and actually listen to my own qi for once.",
		"Breathe in for four. I can already hear Elder Hua counting with me.",
	],
	"tribulation": [
		"Heaven's watching again. It always picks the worst possible moment to look.",
		"Whatever's coming, I've survived worse. I hope that's still true after this one.",
	],
	"cinematic": [
		"Something's about to happen. I can feel it in the way everyone's gone quiet.",
	],
}

# ---------------------------------------------------------------- alignment flavour

const BY_ALIGN := {
	"lawful": ["The precepts exist for a reason. I've started believing that instead of just reciting it."],
	"chaotic": ["Rules are a starting point, not a leash. I'll apologise for the results, not the method."],
	"good": ["If I can make someone's day a little lighter on the way, I will. Costs me nothing."],
	"evil": ["People mistake kindness for weakness far too often. I try not to correct them twice."],
}

# ---------------------------------------------------------------- plot callbacks
# Unlock at a quest index (0-based, Game.quest_index reached) and stay
# available afterward — a running memory of the saga so far.

const CALLBACKS := [
	{"at": 2, "text": "That temple keeper still doesn't sit right with me. Kindly men don't usually make my skin crawl."},
	{"at": 20, "text": "Lan Jue kept that pendant's secret from everyone but me. I still don't know what to do with that."},
	{"at": 21, "text": "Elder Gu asked for the sutra like it was owed to him. I've thought about that look on his face more than once."},
	{"at": 40, "text": "The traitor's still out there somewhere below. I keep rehearsing what I'll say when I find him."},
	{"at": 41, "text": "Han Xue doesn't talk about the obelisks. I don't push. Some things need to heal on their own time."},
	{"at": 81, "text": "Elder Mo checked nine thousand runes himself. I hope he knows I noticed."},
	{"at": 83, "text": "I still see my own shadow sometimes, out of the corner of my eye. It hasn't tried anything. Yet."},
	{"at": 99, "text": "Seven Rungs to a ladder, Qing Luan said. We've only broken the first, and it already cost too much."},
	{"at": 121, "text": "Standing in the void gets easier. I'm not sure that's something to be proud of."},
	{"at": 141, "text": "Nobody's tried to wear my face in months. I'd like to keep it that way."},
	{"at": 161, "text": "Forty sects swore one oath on our plaza. I hope they meant it when winter comes."},
	{"at": 181, "text": "The Ascension Stair is still just standing there, waiting. It's patient. I'm trying to be."},
	{"at": 197, "text": "My cousin's face, on that shadow. I didn't expect the Ladder's last rung to hurt the most."},
]


func _process(delta: float) -> void:
	if game == null:
		return
	_cooldown -= delta
	if _cooldown > 0.0:
		return
	if not _may_speak():
		_cooldown = 2.0
		return
	_cooldown = randf_range(MIN_GAP, MAX_GAP)
	var line := _pick_line()
	if line != "":
		game.hud.say_thought(line)


func _may_speak() -> bool:
	if game.busy or game.dialogue.active or game.cinematic.active or game.journal.open or game.travel.open \
			or game.conversation.active:
		return false
	var p: CharacterBody3D = game.player
	if p == null or p.dead or p.meditating or not p.controls_enabled:
		return false
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return false
	for e in get_tree().get_nodes_in_group("enemies"):
		if is_instance_valid(e) and not e.dead and p.global_position.distance_to(e.global_position) < 14.0:
			return false
	return true


## Weighted pick: plot callbacks and location flavour come up more often than
## generic idling, alignment colour rarest of all. Never repeats a line until
## the last ten have been used.
func _pick_line() -> String:
	var pool: Array[String] = []
	for cb in CALLBACKS:
		if Game.quest_index >= int(cb.at):
			pool.append(cb.text)
			pool.append(cb.text)
	# CALLBACKS above only hand-covers the saga's first tenth (volume I); every
	# later volume's major beats come from Story.threads instead, so the
	# roaming monologue keeps referencing the plot all the way to quest 2000.
	for beat in Story.threads_so_far(Game.quest_index):
		pool.append(beat.beats[-1])
		pool.append(beat.beats[-1])
	pool.append_array(BY_MAP.get(Game.map_id, []))
	pool.append_array(BY_MAP.get(Game.map_id, []))
	var ot: String = Game.objective().get("type", "") if not Game.quest().is_empty() else ""
	pool.append_array(BY_OBJECTIVE.get(ot, []))
	var align: String = Game.alignment()
	for axis in BY_ALIGN:
		if align.begins_with(axis) or align.ends_with(axis):
			pool.append_array(BY_ALIGN[axis])
	pool.append_array(IDLE)
	var choices: Array[String] = []
	for line in pool:
		if not _recent.has(line):
			choices.append(line)
	if choices.is_empty():
		choices = pool
	if choices.is_empty():
		return ""
	var pick: String = choices[randi() % choices.size()]
	_recent.append(pick)
	while _recent.size() > RECENT_MAX:
		_recent.pop_front()
	return pick

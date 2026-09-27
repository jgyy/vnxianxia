extends Node
## The protagonists' extended move set at runtime (130+ animations built by
## blender/xianxia/moves.py): combo chains, dodges, blocking and parries, jumps
## with a qinggong somersault and glide, ledge grabs, crouch / sneak / sprint /
## slide, run start / stop and turn-in-place, directional hit reactions,
## knockdowns, deaths and revival, meditation variants, breakthroughs, qi
## techniques, idle fidgets, victory poses, talk gestures and an emote menu.
##
## Created by player.gd as a child node; every hook there is guarded by
## `if moves`.  Controls (added to the InputMap at runtime if missing):
##   F / LMB palm combo (crouched: uppercut) · Z kick combo (airborne: flying kick)
##   X sword combo · hold H / MMB charged strike · hold R block (tap just before
##   a hit to parry) · Alt dodge (direction relative to facing; none = backflip,
##   forward = roll) · Space again in the air: somersault, hold to glide ·
##   hold Ctrl crouch (while sprinting: slide) · B sneak toggle · 1-4 qi
##   techniques · V emote menu · Shift held 1.5 s sprints.

const FPS := 30.0
const QiBlast := preload("res://scripts/world/qi_blast.gd")

## Looping animations of the move set (the base five are set by ActorLook).
const LOOPS := [
	"walk_back", "strafe_l", "strafe_r", "sprint", "crouch_idle", "crouch_walk", "sneak", "jump_air", "fall",
	"glide", "ledge_hang", "combat_idle", "sword_idle", "charge_hold", "block_idle", "meditate_levitate",
	"meditate_breath", "sword_ride_idle", "qi_circulate", "thinking", "arms_crossed", "sit_ground_idle",
	"sit_chair", "sleep", "read_scroll", "write_calligraphy", "play_flute", "play_guqin", "sweep_floor",
	"talk_explain", "talk_emphatic", "talk_listen",
]
## Combo chains: [animation, hit frame, damage multiplier, extra reach].
const CHAINS := {
	"palm": [["palm_1", 8, 1.0, 0.0], ["palm_2", 7, 1.0, 0.0], ["palm_3", 11, 1.2, 0.1],
			["palm_4", 10, 1.2, 0.0], ["palm_5", 13, 1.8, 0.3]],
	"kick": [["kick_1", 11, 1.1, 0.3], ["kick_2", 12, 1.2, 0.3], ["kick_3", 13, 1.4, 0.4],
			["spin_kick", 18, 1.8, 0.5]],
	"sword": [["sword_1", 9, 1.3, 0.6], ["sword_2", 10, 1.3, 0.6], ["sword_3", 10, 1.3, 0.6],
			["sword_4", 12, 1.6, 0.6], ["sword_5", 24, 2.2, 0.8]],
}
## Qi techniques on keys 1-4: [animation, qi cost, release frame].
const TECHNIQUES := [["blast_forward", 20.0, 14], ["blast_two_hand", 35.0, 20], ["blast_wave", 30.0, 18],
		["blast_rain", 45.0, 28]]
const FIDGETS := ["idle_look", "idle_shift_weight", "idle_adjust_sleeve", "idle_stretch", "look_around",
		"idle_look", "idle_shift_weight", "yawn"]
const VICTORIES := ["victory_1", "victory_2", "victory_3"]
const TALKS := ["talk", "talk_explain", "talk_emphatic"]
## Emote menu: category -> [[label, [animations...]], ...]; a looping last
## animation holds until the player moves (then its exit animation plays).
const EMOTES := [
	["Etiquette", [["Deep bow", ["bow_deep"]], ["Fist-palm salute", ["bow_fist_palm"]], ["Salute", ["salute"]],
			["Wave", ["wave"]], ["Beckon", ["beckon"]], ["Point", ["point"]], ["Nod", ["nod"]],
			["Shake head", ["shake_head"]], ["Give item", ["give_item"]], ["Offer incense", ["pray_incense"]]]],
	["Feelings", [["Laugh", ["laugh"]], ["Cry", ["cry"]], ["Shrug", ["shrug"]], ["Clap", ["clap"]],
			["Cheer", ["cheer"]], ["Facepalm", ["facepalm"]], ["Thinking", ["thinking"]],
			["Arms crossed", ["arms_crossed"]], ["Bashful", ["bashful"]], ["Angry stomp", ["angry_stomp"]],
			["Surprised", ["surprised"]], ["Sigh", ["sigh"]], ["Yawn", ["yawn"]], ["Stretch", ["stretch"]],
			["Look around", ["look_around"]]]],
	["Daily life", [["Sit on the ground", ["sit_ground", "sit_ground_idle"]], ["Sit on a chair", ["sit_chair"]],
			["Lie down & sleep", ["lie_down", "sleep"]], ["Drink tea", ["drink_tea"]], ["Eat", ["eat"]],
			["Read a scroll", ["read_scroll"]], ["Calligraphy", ["write_calligraphy"]], ["Play the dizi", ["play_flute"]],
			["Play the guqin", ["meditate_enter", "play_guqin"]], ["Sweep", ["sweep_floor"]], ["Pick up", ["pick_up"]],
			["Push a door", ["push_door"]]]],
	["Cultivation", [["Hand seals", ["mudra_sequence"]], ["Qi circulation", ["qi_circulate"]],
			["Breathing meditation", ["meditate_enter", "meditate_breath"]],
			["Levitating meditation", ["meditate_enter", "meditate_levitate"]], ["Breakthrough", ["breakthrough"]],
			["Ride the flying sword", ["sword_mount", "sword_ride_idle"]], ["Cast a seal", ["cast"]]]],
	["Performance", [["Dance of the drifting sleeves", ["dance_1", "dance_2", "dance_3", "dance_4"]],
			["Dance: opening", ["dance_1"]], ["Dance: turn", ["dance_2"]], ["Dance: low sweep", ["dance_3"]],
			["Dance: finale", ["dance_4"]], ["Victory: fist", ["victory_1"]], ["Victory: composed", ["victory_2"]],
			["Victory: flourish", ["victory_3"]], ["Mudra kata", ["mudra_sequence", "qi_circulate"]]]],
]
## How a held emote pose is left when the player moves off.
const EXITS := {"sit_ground_idle": "stand_up", "sleep": "getup", "play_guqin": "meditate_exit",
		"meditate_breath": "meditate_exit", "meditate_levitate": "meditate_exit", "sit_chair": "stand_up"}

var player  ## the owning player.gd CharacterBody3D (untyped: script members are used)
var anim: AnimationPlayer
## Multiplier / extra reach applied by player._apply_strike to the current blow.
var damage_mult := 1.0
var extra_reach := 0.0
var menu_open := false

var _now := 0.0
var _busy_until := 0.0          ## a one-shot owns the body until then
var _interruptible := true      ## ...unless the player moves
var _queue: Array = []          ## animations to chain after the one-shot
var _hold_loop := ""            ## looping emote held until the player moves
var _loco := ""
var _idle_time := 0.0
var _next_fidget := 9.0
var _combo_kind := ""
var _combo_idx := 0
var _combo_until := 0.0
var _last_attack := -100.0
var _last_sword := -100.0
var _blocking := false
var _block_key := false
var _absorbed := false         ## block started from the key (released with it)
var _block_pressed := -100.0
var _crouch := false
var _sneak := false
var _run_time := 0.0
var _sprinting := false
var _charging := false
var _charge_t0 := 0.0
var _state := ""                ## "", dodge, slide, ledge, climb
var _state_until := 0.0
var _motion := Vector3.ZERO
var _motion_decay := 0.0
var _was_floor := true
var _air_time := 0.0
var _min_vy := 0.0
var _jumps_left := 0
var _gliding := false
var _ledge_face := Vector3.FORWARD
var _enemies_seen := 0
var _victory_at := -1.0
var _med_next := 0.0
var _med_idx := 0
var _menu: CanvasLayer
var _mouse_before := Input.MOUSE_MODE_VISIBLE


func _ready() -> void:
	setup_input_map()
	Game.realm_changed.connect(_on_realm_changed)


static func setup_input_map() -> void:
	var keys := {
		"kick": [KEY_Z], "sword": [KEY_X], "heavy": [KEY_H], "block": [KEY_R], "dodge": [KEY_ALT],
		"crouch": [KEY_CTRL], "sneak": [KEY_B], "emote_menu": [KEY_V],
		"technique_1": [KEY_1], "technique_2": [KEY_2], "technique_3": [KEY_3], "technique_4": [KEY_4],
	}
	for action in keys:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in keys[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	if not InputMap.has_action("heavy_mouse"):
		InputMap.add_action("heavy_mouse")
		var mb := InputEventMouseButton.new()
		mb.button_index = MOUSE_BUTTON_MIDDLE
		InputMap.action_add_event("heavy_mouse", mb)


## Called by player.set_character with the new model's AnimationPlayer.
func on_model(ap: AnimationPlayer) -> void:
	anim = ap
	_state = ""
	_queue.clear()
	_hold_loop = ""
	_busy_until = 0.0
	if anim == null:
		return
	for a in LOOPS:
		if anim.has_animation(a):
			anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR


## Forget any move in progress (ledge hang, climb, dodge, slide, charge,
## block, queued one-shots): called when the player is teleported.
func reset_state() -> void:
	_state = ""
	_charging = false
	_blocking = false
	_block_key = false
	_gliding = false
	_motion = Vector3.ZERO
	_clear_busy()
	if player and player._action_lock > 1.0 and not player.dead:
		player._action_lock = 0.0


func has(anim_name: String) -> bool:
	return anim != null and anim.has_animation(anim_name)


## Plays an animation (any from the library); returns false if missing.
func play_anim(anim_name: String, blend := 0.15, speed := 1.0) -> bool:
	if not has(anim_name):
		return false
	anim.play(anim_name, blend)
	anim.speed_scale = speed
	return true


func _length(anim_name: String) -> float:
	return anim.get_animation(anim_name).length if has(anim_name) else 0.0


## One-shot that owns the body for its length (or until the player moves).
func play_once(anim_name: String, blend := 0.12, interruptible := true, then: Array = []) -> float:
	if not play_anim(anim_name, blend):
		return 0.0
	var l := _length(anim_name)
	_busy_until = _now + l * 0.94
	_interruptible = interruptible
	_queue = then.duplicate()
	_hold_loop = ""
	_idle_time = 0.0
	_loco = ""
	return l


func _tick_queue() -> void:
	if _queue.is_empty() or _now < _busy_until or anim == null:
		return
	var nxt: String = _queue.pop_front()
	if _queue.is_empty() and nxt in LOOPS:
		play_anim(nxt, 0.3)
		_hold_loop = nxt
		_busy_until = _now
	else:
		var keep := _queue.duplicate()
		play_once(nxt, 0.2, false, keep)


func _clear_busy() -> void:
	_busy_until = 0.0
	_queue.clear()
	_hold_loop = ""


# ----------------------------------------------------------------- queries
func _enemies_near(radius: float) -> Array:
	var out := []
	for e in get_tree().get_nodes_in_group("enemies"):
		if not e.dead and player.global_position.distance_to(e.global_position) < radius:
			out.append(e)
	return out


## Side a hit came from relative to the facing: front, back, left or right.
func _side_of(from: Node) -> String:
	if from == null or not (from is Node3D):
		return "front"
	var to: Vector3 = (from as Node3D).global_position - player.global_position
	to.y = 0.0
	if to.length() < 0.01:
		return "front"
	to = to.normalized()
	var fwd: Vector3 = player.model_root.global_basis.z
	var left: Vector3 = player.model_root.global_basis.x
	var f := to.dot(fwd)
	var l := to.dot(left)
	if absf(f) >= absf(l):
		return "front" if f > 0.0 else "back"
	return "left" if l > 0.0 else "right"


func facing_locked() -> bool:
	return _blocking or _charging


func speed_mult(running: bool) -> float:
	if _blocking:
		return 0.55
	if _crouch:
		return 0.45
	if _sneak and not running:
		return 0.7
	if _sprinting:
		return 1.35
	return 1.0


func _scale() -> float:
	return 0.93 if player.character_index == 1 else 1.0


# ----------------------------------------------------------------- input
func handle_input(event: InputEvent) -> bool:
	if menu_open:
		if event.is_action_pressed("emote_menu") or event.is_action_pressed("pause"):
			close_menu()
			get_viewport().set_input_as_handled()
			return true
		return false
	if event.is_action_pressed("emote_menu"):
		open_menu()
		return true
	if player.dead:
		return false
	if event.is_action_pressed("jump") and not player.is_grounded():
		return _air_jump()
	if event.is_action_pressed("jump") and _state == "ledge":
		_climb()
		return true
	if event.is_action_pressed("kick"):
		strike("kick")
		return true
	if event.is_action_pressed("sword"):
		strike("sword")
		return true
	if event.is_action_pressed("heavy") or event.is_action_pressed("heavy_mouse"):
		charge_begin()
		return true
	if event.is_action_released("heavy") or event.is_action_released("heavy_mouse"):
		charge_release()
		return true
	if event.is_action_pressed("block"):
		_block_pressed = _now
		block(true)
		_block_key = _blocking
		return true
	if event.is_action_released("block"):
		block(false)
		return true
	if event.is_action_pressed("dodge"):
		dodge()
		return true
	if event.is_action_pressed("sneak"):
		_sneak = not _sneak
		return true
	for i in 4:
		if event.is_action_pressed("technique_%d" % (i + 1)):
			technique(i)
			return true
	return false


# ----------------------------------------------------------------- combat
## Next blow of a combo chain; returns true when handled (played or refused).
func strike(kind: String) -> bool:
	if player.dead or anim == null or _state != "":
		return true
	if not player.is_grounded():
		if kind == "kick" and has("flying_kick") and _now >= _busy_until:
			_blow("flying_kick", 13, 1.5, 0.5)
		return true
	if player._action_lock > 0.0 or _charging:
		return true
	if kind == "palm" and _crouch and has("uppercut"):
		_blow("uppercut", 11, 1.5, 0.0)
		_combo_kind = ""
		return true
	var chain: Array = CHAINS[kind]
	var idx := _combo_idx if kind == _combo_kind and _now <= _combo_until else 0
	var e: Array = chain[idx]
	if not has(e[0]):
		return false
	var l := _blow(e[0], e[1], e[2], e[3])
	_combo_kind = kind
	_combo_idx = (idx + 1) % chain.size()
	_combo_until = _now + l + 0.3
	if kind == "sword":
		_last_sword = _now
	return true


func _blow(anim_name: String, hit_frame: int, mult: float, reach: float) -> float:
	player._face_nearest_enemy(4.0 + reach)
	player.stop_meditation()
	var l := play_once(anim_name, 0.08)
	var hit: float = hit_frame / FPS
	player._action_lock = hit + 0.12
	player._strike_at = hit
	damage_mult = mult
	extra_reach = reach
	_last_attack = _now
	Audio.sfx("sword_swing", -4.0, randf_range(0.9, 1.1))
	return l


func charge_begin() -> void:
	if _charging or not player.is_grounded() or player._action_lock > 0.0 or not has("charge_start"):
		return
	player.stop_meditation()
	_face_enemy()
	_charging = true
	_charge_t0 = _now
	play_once("charge_start", 0.1, false, ["charge_hold"])
	player._action_lock = 99.0
	Audio.sfx("qi_charge", -6.0)


func charge_release() -> void:
	if not _charging:
		return
	_charging = false
	var power := clampf((_now - _charge_t0) / 1.2, 0.0, 1.0)
	player._action_lock = 0.0
	_blow("charge_release", 6, 1.4 + 2.2 * power, 0.9)
	_combo_kind = ""


func _face_enemy() -> void:
	player._face_nearest_enemy(10.0)


func block(on: bool) -> void:
	if on:
		if _blocking or not player.is_grounded() or player._action_lock > 0.0 or not has("block_start"):
			return
		player.stop_meditation()
		_blocking = true
		_face_enemy()
		play_once("block_start", 0.08, true, ["block_idle"])
	else:
		_blocking = false
		_block_key = false
		if _hold_loop == "block_idle" or (anim and anim.current_animation.begins_with("block")):
			_clear_busy()


## Damage after blocking / parrying (called first thing in player.take_damage).
func filter_damage(amount: float, from: Node) -> float:
	_absorbed = false
	var side := _side_of(from)
	if side == "front" and _now - _block_pressed < 0.3 and has("parry"):
		play_once("parry", 0.05)
		player._action_lock = 0.25
		_block_pressed = -100.0
		Audio.sfx("sword_hit", -2.0, 1.2)
		if from and from.has_method("take_damage") and from.is_in_group("enemies"):
			from.take_damage(Game.strike_damage() * 0.5, player)
		return 0.0
	if _blocking and side == "front":
		play_once("block_hit", 0.05, true, ["block_idle"])
		Audio.sfx("block", -3.0, randf_range(0.9, 1.1))
		_absorbed = true
		return amount * 0.2
	return amount


## Hit reaction for a survivable blow (light flinch, stagger or knockdown).
func hit_reaction(amount: float, from: Node) -> void:
	if anim == null:
		return
	if _absorbed:            # taken on the guard: block_hit already plays
		_absorbed = false
		return
	_charging = false
	_blocking = false
	var mx: float = Game.max_hp()
	var boss: bool = from != null and "boss" in from and from.boss
	if (amount >= mx * 0.25 or (boss and amount >= mx * 0.12)) and player.is_grounded() and has("knockdown"):
		_state = ""
		play_once("knockdown", 0.06, false, ["getup"])
		_busy_until = _now + _length("knockdown") * 0.8
		player._action_lock = _length("knockdown") * 0.8 + _length("getup") * 0.85
		player._invulnerable = 1.6
		return
	if player._action_lock > 0.0 and amount < mx * 0.07:
		return
	if amount >= mx * 0.07 and has("stagger_front"):
		var a := "stagger_" + _side_of(from)
		play_once(a, 0.05, false)
		player._action_lock = 0.42
	else:
		play_once("hit", 0.05, false)
		player._action_lock = 0.3


func death_anim(from: Node) -> String:
	_state = ""
	_clear_busy()
	var side := _side_of(from)
	if side == "back" and has("death_forward"):
		return "death_forward"
	return "death_back" if has("death_back") else "death"


func on_respawn() -> void:
	_state = ""
	_charging = false
	_blocking = false
	if has("revive"):
		play_once("revive", 0.0, false)
		player._action_lock = _length("revive") * 0.8
		player._invulnerable = 2.0
	elif anim:
		anim.play("idle")


func technique(i: int) -> void:
	var t: Array = TECHNIQUES[i]
	if player.qi < t[1] or not player.is_grounded() or player._action_lock > 0.0 or not has(t[0]):
		return
	player.stop_meditation()
	player._face_nearest_enemy(22.0)
	player.qi -= t[1]
	player.qi_changed.emit(player.qi, Game.max_qi())
	var l := play_once(t[0], 0.1)
	player._action_lock = l * 0.7
	Audio.sfx("qi_charge", -6.0)
	var delay: float = t[2] / FPS if not Game.fast else 0.0
	get_tree().create_timer(delay, false).timeout.connect(_release_technique.bind(i))


func _release_technique(i: int) -> void:
	if player == null or player.dead or not is_inside_tree():
		return
	var fwd: Vector3 = player.model_root.global_basis.z
	var pos: Vector3 = player.global_position
	match i:
		0, 1:
			var b: Node3D = QiBlast.new()
			b.damage = Game.blast_damage() * (1.0 if i == 0 else 2.2)
			if i == 1:
				b.speed = 20.0
				b.scale = Vector3.ONE * 1.6
			player.get_parent().add_child(b)
			b.global_position = pos + Vector3.UP * 1.3 + fwd * 0.7
			b.direction = fwd
			Audio.sfx("qi_blast", -3.0)
		2:
			Fx.burst(player.get_parent(), pos + Vector3.UP * 0.4, Color(0.5, 0.9, 1.0), 120, 7.0, 0.06)
			Audio.sfx("qi_blast", -1.0, 0.8)
			for e in _enemies_near(5.5):
				e.take_damage(Game.blast_damage() * 1.3, player)
		3:
			var targets := _enemies_near(22.0)
			var centre: Vector3 = pos + fwd * 6.0
			if not targets.is_empty():
				targets.sort_custom(func(a, b): return pos.distance_to(a.global_position) < pos.distance_to(b.global_position))
				centre = targets[0].global_position
			for k in 3:
				Fx.burst(player.get_parent(), centre + Vector3(randf_range(-1.5, 1.5), 3.5, randf_range(-1.5, 1.5)),
						Color(0.7, 0.9, 1.0), 40, 6.0, 0.05)
				for e in get_tree().get_nodes_in_group("enemies"):
					if not e.dead and e.global_position.distance_to(centre) < 4.0:
						e.take_damage(Game.blast_damage() * 0.8, player)
			Audio.sfx("qi_blast", 0.0, 1.2)


func dodge() -> void:
	if not player.is_grounded() or _state != "" or player.dead or _charging:
		return
	if player._action_lock > 0.2:
		return
	player.stop_meditation()
	_blocking = false
	var input: Vector2 = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if player.scripted_input != Vector2.ZERO:
		input = player.scripted_input
	var dir: Vector3 = Basis(Vector3.UP, player._yaw) * Vector3(input.x, 0, input.y)
	var fwd: Vector3 = player.model_root.global_basis.z
	var left: Vector3 = player.model_root.global_basis.x
	var a := "backflip"
	var speed := -4.2
	var move_dir := fwd
	var dur := 0.9
	if dir.length() > 0.1:
		dir = dir.normalized()
		var f := dir.dot(fwd)
		var l := dir.dot(left)
		if absf(l) > absf(f):
			a = "dodge_l" if l > 0.0 else "dodge_r"
			move_dir = left if l > 0.0 else -left
			speed = 6.5
			dur = 0.42
		elif f > 0.0:
			a = "roll_forward"
			speed = 5.5
			dur = 0.75
		else:
			a = "dodge_back"
			speed = -5.5
			dur = 0.45
	if not has(a):
		return
	play_once(a, 0.06, false)
	_state = "dodge"
	_state_until = _now + dur
	_motion = move_dir * speed
	_motion_decay = 0.35
	player._invulnerable = maxf(player._invulnerable, dur * 0.7)
	player._action_lock = 0.0
	_combo_kind = ""
	Audio.sfx("jump", -12.0, 1.3)


func _air_jump() -> bool:
	if _jumps_left <= 0 or _state != "" or not has("double_jump_flip"):
		return false
	_jumps_left -= 1
	player.velocity.y = player.JUMP_VELOCITY * 0.95
	play_once("double_jump_flip", 0.05, false, ["jump_air"])
	Audio.sfx("jump", -6.0, 1.2)
	Fx.burst(player.get_parent(), player.global_position, Color(0.8, 0.95, 1.0), 24, 2.5, 0.04)
	return true


# ----------------------------------------------------------------- physics
## Runs before the player's own movement. Returns the (possibly altered) move
## direction, or null when this frame's motion was fully handled here.
func pre_physics(delta: float, dir: Vector3, running: bool) -> Variant:
	_now += delta
	_tick_queue()
	if anim == null:
		return dir
	if menu_open:
		dir = Vector3.ZERO
	var on_floor: bool = player.is_grounded()
	_crouch = on_floor and player.controls_enabled and Input.is_action_pressed("crouch") and _state == ""
	# sprinting after a sustained run
	if running and dir != Vector3.ZERO and on_floor:
		_run_time += delta
	else:
		_run_time = 0.0
	_sprinting = _run_time > 1.5 and not _crouch and not _blocking
	if _blocking and _block_key and not Input.is_action_pressed("block"):
		block(false)
	if _charging and not (Input.is_action_pressed("heavy") or Input.is_action_pressed("heavy_mouse")):
		charge_release()
	if facing_locked() and dir != Vector3.ZERO:
		_face_enemy()
	if player.meditating:
		_meditation_cycle()
	# slide out of a sprint
	if _crouch and _sprinting and _state == "" and has("slide"):
		play_once("slide", 0.1, false)
		_state = "slide"
		_state_until = _now + 0.85
		_motion = player.model_root.global_basis.z * 7.0
		_motion_decay = 0.8
		_sprinting = false
		_run_time = 0.0
	match _state:
		"dodge", "slide":
			return _motion_state(delta)
		"ledge":
			return _ledge_state(dir)
		"climb":
			return _climb_state()
	_air(delta, dir, on_floor)
	if _state == "ledge":
		return null
	return dir


func _motion_state(delta: float) -> Variant:
	if _now >= _state_until or player.dead:
		_state = ""
		return Vector3.ZERO
	var v: Vector3 = _motion * (1.0 - _motion_decay * clampf(1.0 - (_state_until - _now) / 0.9, 0.0, 1.0))
	player.velocity.x = v.x
	player.velocity.z = v.z
	if not player.is_on_floor():
		player.velocity.y -= player.GRAVITY * delta
	player.move_body(delta)
	return null


func _air(delta: float, dir: Vector3, on_floor: bool) -> void:
	if on_floor:
		if not _was_floor:
			_land()
		_was_floor = true
		_air_time = 0.0
		_min_vy = 0.0
		_gliding = false
		_jumps_left = 1
		return
	if _was_floor:
		_was_floor = false
		if player.velocity.y > 1.0 and has("jump_start"):
			play_once("jump_start", 0.05, false, ["jump_air"])
	_air_time += delta
	_min_vy = minf(_min_vy, player.velocity.y)
	if player.dead:
		return
	var holding: bool = player.controls_enabled and Input.is_action_pressed("jump")
	if holding and player.velocity.y < -1.0 and _air_time > 0.35 and has("glide"):
		player.velocity.y = maxf(player.velocity.y, -1.6)
		_min_vy = maxf(_min_vy, -2.0)
		if not _gliding:
			_gliding = true
			play_anim("glide", 0.25)
			_clear_busy()
	elif _gliding:
		_gliding = false
	if not _gliding and _now >= _busy_until and player.velocity.y < -3.0 and has("fall") \
			and anim.current_animation != "fall":
		play_anim("fall", 0.3)
		_queue.clear()
	# ledge grab: moving into a wall with a ledge top within reach
	if dir != Vector3.ZERO and player.velocity.y < 2.0 and player.is_on_wall() and _state == "":
		_try_ledge()


func _land() -> void:
	if player.dead:
		return
	if _min_vy < -11.0 and _air_time > 0.6 and has("landing_hard"):
		play_once("landing_hard", 0.05, false)
		player._action_lock = 0.8
		Audio.sfx("land", 0.0, 0.8)
	elif _air_time > 0.35 and has("jump_land"):
		play_once("jump_land", 0.06, true)
		Audio.sfx("land", -6.0)
	elif anim and anim.current_animation in ["jump_air", "fall", "glide", "jump_start", "double_jump_flip"]:
		_clear_busy()


func _try_ledge() -> void:
	var s: float = _scale()
	var fwd: Vector3 = player.model_root.global_basis.z
	var from: Vector3 = player.global_position + Vector3.UP * 2.5 * s + fwd * 0.55
	var q := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 1.6 * s, player.collision_mask,
			[player.get_rid()])
	var hit: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty() or (hit.normal as Vector3).y < 0.7:
		return
	var h: float = (hit.position as Vector3).y - player.global_position.y
	if h < 1.1 * s or h > 2.3 * s:
		return
	_state = "ledge"
	_ledge_face = fwd
	player.velocity = Vector3.ZERO
	player.global_position.y = (hit.position as Vector3).y - 2.0 * s
	_clear_busy()
	play_anim("ledge_hang", 0.15)


func _ledge_state(dir: Vector3) -> Variant:
	player.velocity = Vector3.ZERO
	if dir != Vector3.ZERO:
		if dir.dot(_ledge_face) > 0.5:
			_climb()
		elif dir.dot(_ledge_face) < -0.5 or _crouch:
			_state = ""
			player.global_position -= _ledge_face * 0.25
			play_anim("fall", 0.2)
	return null


func _climb() -> void:
	if _state != "ledge" or not has("climb_up"):
		return
	_state = "climb"
	var l := play_once("climb_up", 0.1, false)
	_state_until = _now + l
	Audio.sfx("jump", -10.0, 0.8)


func _climb_state() -> Variant:
	player.velocity = Vector3.ZERO
	if _now >= _state_until:
		var s: float = _scale()
		player.global_position += Vector3.UP * 2.0 * s + _ledge_face * 0.35 * s
		_state = ""
		_clear_busy()
		anim.play("idle", 0.0)
		_loco = "idle"
	return null


# ----------------------------------------------------------------- meditation
func meditate_enter() -> void:
	if has("meditate_enter"):
		play_once("meditate_enter", 0.3, false, ["meditate"])
		_med_next = _now + 14.0
		_med_idx = 0
	elif anim:
		anim.play("meditate", 0.4)


func meditate_exit() -> void:
	_clear_busy()
	if has("meditate_exit") and player.is_grounded() and not player.dead:
		play_once("meditate_exit", 0.3, false)
		player._action_lock = maxf(player._action_lock, _length("meditate_exit") * 0.75)
	elif anim:
		anim.play("idle", 0.4)


func _meditation_cycle() -> void:
	if _now < _med_next or _now < _busy_until:
		return
	_med_next = _now + 14.0
	var cycle := ["meditate", "meditate_breath", "meditate_levitate" if Game.realm >= 1 else "meditate_breath"]
	_med_idx = (_med_idx + 1) % cycle.size()
	if has(cycle[_med_idx]):
		play_anim(cycle[_med_idx], 1.2)


func _on_realm_changed(_realm: String) -> void:
	if player == null or player.dead or not player.is_grounded() or not player.controls_enabled or anim == null:
		return
	player.stop_meditation()
	if has("breakthrough"):
		play_once("breakthrough", 0.2, false)
		player._action_lock = _length("breakthrough") * 0.85


## Talk gesture for a dialogue line (listening pose while others speak).
func talk_anim(speaking: bool) -> String:
	if not speaking:
		return "talk_listen" if has("talk_listen") else "idle"
	var options := TALKS.filter(func(a): return has(a))
	return options[randi() % options.size()] if not options.is_empty() else "talk"


# ----------------------------------------------------------------- locomotion
## Chooses the ground animation; returns true when it handled this frame.
func update_animation(delta: float) -> bool:
	if anim == null:
		return false
	if not player.is_grounded() or _state != "":
		return true
	var planar := Vector2(player.velocity.x, player.velocity.z).length()
	var moving := planar > 0.15
	if _hold_loop != "":
		if not moving:
			return true
		var exit_a: String = EXITS.get(_hold_loop, "")
		_hold_loop = ""
		if exit_a != "" and has(exit_a):
			play_once(exit_a, 0.2, false)
			player._action_lock = _length(exit_a) * 0.8
			return true
	if _now < _busy_until and (not _interruptible or not moving):
		return true
	if not _queue.is_empty():
		return true
	var wanted := "idle"
	var speed := 1.0
	var fwd: Vector3 = player.model_root.global_basis.z
	if _crouch:
		wanted = "crouch_walk" if moving else "crouch_idle"
		speed = player.stride_scale("crouch_walk", planar) if moving else 1.0
	elif _blocking:
		wanted = "block_idle"
		if moving:
			var v: Vector3 = Vector3(player.velocity.x, 0, player.velocity.z).normalized()
			var f := v.dot(fwd)
			var l := v.dot(player.model_root.global_basis.x)
			if absf(l) > absf(f):
				wanted = "strafe_l" if l > 0.0 else "strafe_r"
			else:
				wanted = "walk" if f > 0.0 else "walk_back"
			speed = player.stride_scale(wanted, planar)
	elif moving:
		# walk / run / sprint with hysteresis, speed_scale = ground speed / authored speed (no foot sliding)
		wanted = player.gait_for(planar, _loco, _sprinting and has("sprint"))
		if wanted == "walk" and _sneak and has("sneak"):
			wanted = "sneak"
		speed = player.stride_scale(wanted, planar)
	else:
		if _now - _last_attack < 6.0 or not _enemies_near(12.0).is_empty():
			wanted = "sword_idle" if _now - _last_sword < 8.0 else "combat_idle"
	# transitions
	if moving and _loco in ["idle", "combat_idle", "sword_idle"]:
		var vel: Vector3 = Vector3(player.velocity.x, 0, player.velocity.z)
		var ang: float = fwd.signed_angle_to(vel.normalized(), Vector3.UP) if vel.length() > 0.01 else 0.0
		if absf(ang) > deg_to_rad(100.0) and has("turn_l"):
			play_once("turn_l" if ang > 0.0 else "turn_r", 0.1, false)
			_busy_until = _now + 0.3
			return true
		if wanted == "run" and has("run_start"):
			play_once("run_start", 0.1, false)
			_busy_until = _now + 0.32
			_loco = "run"
			return true
	if not moving and _loco in ["run", "sprint"] and has("run_stop"):
		play_once("run_stop", 0.08, true)
		return true
	if wanted == "idle":
		_idle_time += delta
		if _idle_time > _next_fidget:
			_idle_time = 0.0
			_next_fidget = randf_range(8.0, 15.0)
			var fid: String = FIDGETS[randi() % FIDGETS.size()]
			if has(fid):
				play_once(fid, 0.3)
				return true
	else:
		_idle_time = 0.0
	_check_victory(wanted)
	if not has(wanted):
		wanted = "idle"
	if anim.current_animation != wanted:
		var blend := 0.12 if wanted == "block_idle" else (0.25 if wanted.ends_with("idle") else 0.2)
		if anim.current_animation == "run_start" and wanted in ["run", "sprint"]:
			blend = 0.0          # run_start ends exactly on run's first frame
		anim.play(wanted, blend)
	anim.speed_scale = speed
	_loco = wanted
	if moving:
		player.footstep_tick(wanted, -14.0 if not (_crouch or _sneak) else -22.0)
	return true


func _check_victory(wanted: String) -> void:
	var n := _enemies_near(25.0).size()
	if n == 0 and _enemies_seen > 0 and _now - _last_attack < 10.0:
		_victory_at = _now + 0.9
	_enemies_seen = n
	if _victory_at > 0.0 and _now >= _victory_at:
		_victory_at = -1.0
		if wanted in ["idle", "combat_idle", "sword_idle"]:
			play_once(VICTORIES[randi() % VICTORIES.size()], 0.3)


# ----------------------------------------------------------------- emotes
## Plays an emote sequence (the last looping animation holds until moving).
func play_emote(anims: Array) -> void:
	close_menu()
	if player.dead or not player.is_grounded() or anim == null or _state != "":
		return
	player.stop_meditation()
	player.velocity = Vector3.ZERO
	var seq := anims.filter(func(a): return has(a))
	if seq.is_empty():
		return
	var first: String = seq.pop_front()
	if seq.is_empty() and first in LOOPS:
		_clear_busy()
		play_anim(first, 0.3)
		_hold_loop = first
		return
	play_once(first, 0.25, true, seq)


func open_menu() -> void:
	if _menu == null:
		_build_menu()
	menu_open = true
	_menu.visible = true
	_mouse_before = Input.mouse_mode
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func close_menu() -> void:
	if not menu_open:
		return
	menu_open = false
	_menu.visible = false
	Input.mouse_mode = _mouse_before


func _build_menu() -> void:
	_menu = CanvasLayer.new()
	_menu.layer = 15
	add_child(_menu)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiTheme.get_theme()
	_menu.add_child(root)
	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-470, -300)
	panel.custom_minimum_size = Vector2(940, 0)
	root.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 6)
	panel.add_child(vb)
	vb.add_child(UiTheme.label("Gestures & Arts", 26, UiTheme.GOLD, 5))
	vb.add_child(UiTheme.label("Choose a gesture · V or Esc closes · move to stand up", 14, UiTheme.MUTED))
	for cat in EMOTES:
		vb.add_child(UiTheme.label(cat[0], 17, UiTheme.GOLD, 3))
		var grid := GridContainer.new()
		grid.columns = 5
		grid.add_theme_constant_override("h_separation", 6)
		grid.add_theme_constant_override("v_separation", 4)
		vb.add_child(grid)
		for entry in cat[1]:
			var b := Button.new()
			b.text = entry[0]
			b.custom_minimum_size = Vector2(178, 0)
			b.focus_mode = Control.FOCUS_NONE
			b.pressed.connect(play_emote.bind(entry[1]))
			grid.add_child(b)
	_menu.visible = false


## Every animation name the runtime refers to (used by the tests).
static func referenced() -> Array:
	var out := LOOPS.duplicate()
	for k in CHAINS:
		for e in CHAINS[k]:
			out.append(e[0])
	for t in TECHNIQUES:
		out.append(t[0])
	for cat in EMOTES:
		for entry in cat[1]:
			out.append_array(entry[1])
	out.append_array(FIDGETS + VICTORIES + TALKS + EXITS.values())
	out.append_array(["uppercut", "flying_kick", "charge_start", "charge_release", "block_start", "block_hit",
			"parry", "dodge_l", "dodge_r", "dodge_back", "roll_forward", "backflip", "slide", "climb_up",
			"jump_start", "jump_land", "landing_hard", "double_jump_flip", "turn_l", "turn_r", "run_start",
			"run_stop", "stagger_front", "stagger_back", "stagger_left", "stagger_right", "knockdown", "getup",
			"death_forward", "death_back", "revive", "meditate_enter", "meditate_exit", "breakthrough"])
	return out

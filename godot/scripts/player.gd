extends CharacterBody3D
## Third-person cultivator controller with light combat.
##
## WASD / arrows move relative to the camera, Shift runs, Space leaps
## (qinggong), Tab swaps between Lin Feng and Su Yue, E interacts,
## F / left click strikes, Q fires a qi blast, C meditates, G salutes.
## Hold the right mouse button (or click to capture the mouse) to orbit,
## scroll to zoom.
##
## Stairs, terraces and curbs up to Stepper.MAX_STEP are walked up (and down)
## without jumping; the model and camera ease over each step so the body's
## instant lift never shows as a pop.

signal character_changed(display_name: String)
signal hp_changed(hp: float, max_hp: float)
signal qi_changed(qi: float, max_qi: float)
signal died
signal interact_pressed
signal meditation_changed(active: bool)

const CHARACTERS := [
	{"name": "Disciple Lin Feng", "scene": preload("res://assets/characters/cultivator_male.glb")},
	{"name": "Fairy Su Yue", "scene": preload("res://assets/characters/cultivator_female.glb")},
]
const WALK_SPEED := 1.6
const RUN_SPEED := 4.6
## Ground speed (m/s) at which each locomotion clip plants its feet at
## speed_scale 1.0 (the animation contract, see blender/xianxia/gait.py).
const AUTHORED_SPEED := {"walk": 1.6, "run": 4.6, "sprint": 6.2, "sneak": 1.0, "crouch_walk": 0.8,
		"walk_back": 1.0, "strafe_l": 1.0, "strafe_r": 1.0}
## walk -> run above RUN_UP m/s, run -> walk below RUN_DOWN (no thrash at the threshold)
const RUN_UP := 3.1
const RUN_DOWN := 2.5
const JUMP_VELOCITY := 6.5
const GRAVITY := 13.0
const TURN_SPEED := 10.0
## ground acceleration / braking (m/s^2) and in the air
const ACCEL := 16.0
const BRAKE := 22.0
const AIR_ACCEL := 5.0
## a jump pressed this long before landing still happens; a jump pressed this
## long after walking off an edge still counts as from the ground
const JUMP_BUFFER := 0.15
const COYOTE := 0.12
const MOUSE_SENSITIVITY := 0.004
const STRIKE_RANGE := 2.6
const BLAST_COST := 20.0
const PIVOT_HEIGHT := 1.55
const MAX_LEAN := 0.07
const QiBlast := preload("res://scripts/world/qi_blast.gd")
const PlayerMoves := preload("res://scripts/world/player_moves.gd")
const Stepper := preload("res://scripts/world/stepper.gd")

## Initial camera yaw in radians (0 = looking toward -Z).
@export var start_yaw := 0.0

## Scripted input used by tests and demo captures: x = strafe, y = forward (-1).
var scripted_input := Vector2.ZERO
var scripted_run := false
## False while dialogue, cinematics or menus own the player.
var controls_enabled := true:
	set(v):
		if v != controls_enabled:
			_jump_buffer = 0.0
		controls_enabled = v

var spawn_point := Vector3.ZERO
var character_index := 0
var model: Node3D
var anim: AnimationPlayer
var hp := 100.0
var qi := 60.0
var meditating := false
var dead := false
## Height climbed by the last step-up / dropped by the last step-down snap (tests).
var last_step := 0.0
var _action_lock := 0.0
var _strike_at := -1.0
var _yaw := 0.0
var _pitch := -0.18
var _orbiting := false
## footfalls played so far (tests)
var footsteps := 0
var _step_phase := -1.0
var _step_clip := ""
var _invulnerable := 0.0
var _med_sound: AudioStreamPlayer
var _jump_buffer := 0.0
var _air_time := 0.0
var _supported := false
var _vis_offset := 0.0
var _lean := 0.0
var _gait := "idle"
## a pose (talk, listen, a cinematic stance) that locomotion must not override
var _held_pose := ""
## while a conversation holds the player: the point to turn toward
var _face_point := Vector3.INF
## Extended move set (combos, dodges, emotes...), see world/player_moves.gd.
var moves: Node

@onready var model_root: Node3D = $ModelRoot
@onready var pivot: Node3D = $CameraPivot
@onready var spring: SpringArm3D = $CameraPivot/SpringArm3D
@onready var camera: Camera3D = $CameraPivot/SpringArm3D/Camera3D


func _ready() -> void:
	add_to_group("player")
	setup_input_map()
	spawn_point = global_position
	_yaw = start_yaw
	model_root.rotation.y = start_yaw + PI
	spring.add_excluded_object(get_rid())
	moves = PlayerMoves.new()
	moves.player = self
	add_child(moves)
	set_character(Game.character)
	refill()


func _exit_tree() -> void:
	# the meditation hum is a looping pool player of the Audio autoload: it would
	# keep playing on the title screen after quitting mid-meditation
	if _med_sound:
		_med_sound.stop()
		_med_sound = null


static func setup_input_map() -> void:
	var keys := {
		"move_forward": [KEY_W, KEY_UP],
		"move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT],
		"run": [KEY_SHIFT],
		"jump": [KEY_SPACE],
		"switch_character": [KEY_TAB],
		"interact": [KEY_E],
		"attack": [KEY_F],
		"cast": [KEY_Q],
		"meditate": [KEY_C],
		"salute": [KEY_G],
		"journal": [KEY_J],
		"pause": [KEY_ESCAPE],
		"advance": [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER, KEY_E],
	}
	for action in keys:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in keys[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	if not InputMap.has_action("attack_mouse"):
		InputMap.add_action("attack_mouse")
		var mb := InputEventMouseButton.new()
		mb.button_index = MOUSE_BUTTON_LEFT
		InputMap.action_add_event("attack_mouse", mb)


func set_character(index: int) -> void:
	character_index = wrapi(index, 0, CHARACTERS.size())
	Game.character = character_index
	if model:
		model.queue_free()
	model = CHARACTERS[character_index].scene.instantiate()
	model_root.add_child(model)
	ActorLook.apply(model)
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim:
		ActorLook.loop_anims(anim)
	if moves:
		moves.on_model(anim)
	_gait = "idle"
	if anim:
		if dead:
			anim.play(moves.death_anim(null) if moves else "death")
			anim.seek(anim.current_animation_length, true)
		elif _held_pose != "" and anim.has_animation(_held_pose):
			anim.play(_held_pose)
		else:
			anim.play("meditate" if meditating else "idle")
	if not dead:
		_action_lock = 0.0
	character_changed.emit(CHARACTERS[character_index].name)


func refill() -> void:
	hp = Game.max_hp()
	qi = Game.max_qi()
	dead = false
	hp_changed.emit(hp, Game.max_hp())
	qi_changed.emit(qi, Game.max_qi())


func play_action(anim_name: String) -> bool:
	if anim and anim.has_animation(anim_name) and is_grounded() and _action_lock <= 0.0 and not dead:
		stop_meditation()
		anim.play(anim_name, 0.12)
		anim.speed_scale = 1.0
		_action_lock = anim.get_animation(anim_name).length * 0.85
		return true
	return false


## Hold a pose (talk / listen gestures, a cinematic stance) that locomotion
## leaves alone until release_pose(); "" releases.
func hold_pose(anim_name: String, blend := 0.3) -> void:
	_held_pose = anim_name
	if anim_name == "" or anim == null or dead or not anim.has_animation(anim_name):
		return
	if anim.current_animation != anim_name:
		anim.play(anim_name, blend)
	anim.speed_scale = 1.0


func release_pose() -> void:
	_held_pose = ""
	_face_point = Vector3.INF
	_gait = ""


## Turn (smoothly) toward a point while the controls are held by a conversation.
func face_toward(point: Vector3) -> void:
	_face_point = point


## Forget any buffered jump (a dialogue key press must never turn into a leap).
func clear_input_buffer() -> void:
	_jump_buffer = 0.0


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			_orbiting = mb.pressed and controls_enabled
		elif mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed:
			if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
				if controls_enabled and not dead:
					strike()
			elif controls_enabled:
				# a click on the world (not on a menu, a choice or the dialogue box) captures the mouse
				Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			spring.spring_length = maxf(1.5, spring.spring_length - 0.4)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			spring.spring_length = minf(12.0, spring.spring_length + 0.4)
	elif event is InputEventMouseMotion:
		if _orbiting or Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			var mm := event as InputEventMouseMotion
			_yaw -= mm.relative.x * MOUSE_SENSITIVITY
			_pitch = clampf(_pitch - mm.relative.y * MOUSE_SENSITIVITY, -1.2, 0.5)
	if not controls_enabled or dead:
		return
	if moves and moves.handle_input(event):
		return
	if event.is_action_pressed("jump"):
		_jump_buffer = JUMP_BUFFER
	elif event.is_action_pressed("switch_character"):
		set_character(character_index + 1)
	elif event.is_action_pressed("interact"):
		interact_pressed.emit()
	elif event.is_action_pressed("attack"):
		strike()
	elif event.is_action_pressed("cast"):
		blast()
	elif event.is_action_pressed("meditate"):
		if meditating:
			stop_meditation()
		else:
			start_meditation()
	elif event.is_action_pressed("salute"):
		play_action("salute")


## Melee palm strike: damages enemies in a cone in front of the player.
func strike() -> void:
	if moves and moves.strike("palm"):
		return
	_face_nearest_enemy(4.0)
	if play_action("attack"):
		_strike_at = 0.32
		Audio.sfx("sword_swing", -4.0, randf_range(0.95, 1.08))


## Ranged qi blast (costs qi).
func blast() -> void:
	if qi < BLAST_COST or dead:
		return
	_face_nearest_enemy(22.0)
	if play_action("cast"):
		qi -= BLAST_COST
		qi_changed.emit(qi, Game.max_qi())
		Audio.sfx("qi_charge", -6.0)
		# a game-time timer: pausing (journal) right after casting must not release it behind the menu
		get_tree().create_timer(0.62 if not Game.fast else 0.0, false).timeout.connect(_fire_blast)


func _fire_blast() -> void:
	if dead or not is_inside_tree():
		return
	var b: Node3D = QiBlast.new()
	b.damage = Game.blast_damage()
	get_parent().add_child(b)
	var fwd := model_root.global_basis.z
	b.global_position = global_position + Vector3.UP * 1.35 + fwd * 0.6
	b.direction = fwd
	Audio.sfx("qi_blast", -3.0)


func _face_nearest_enemy(radius: float) -> void:
	var best: Node3D = null
	var bd := radius
	for e in get_tree().get_nodes_in_group("enemies"):
		if e.dead:
			continue
		var d := global_position.distance_to(e.global_position)
		if d < bd:
			bd = d
			best = e
	if best:
		var to := best.global_position - global_position
		model_root.rotation.y = atan2(to.x, to.z)


func _apply_strike() -> void:
	var fwd := model_root.global_basis.z
	var hit := false
	for e in get_tree().get_nodes_in_group("enemies"):
		if e.dead:
			continue
		var to: Vector3 = e.global_position - global_position
		if absf(to.y) > 2.5:
			continue        # an enemy on the terrace above / below is out of reach
		to.y = 0
		var reach: float = STRIKE_RANGE + e.radius + (moves.extra_reach if moves else 0.0)
		if to.length() < reach and (to.length() < 0.8 or fwd.dot(to.normalized()) > 0.25):
			e.take_damage(Game.strike_damage() * (moves.damage_mult if moves else 1.0), self)
			hit = true
	if hit:
		Audio.sfx("hit_flesh", -2.0, randf_range(0.9, 1.1))


func start_meditation() -> void:
	if meditating or not is_grounded() or dead:
		return
	meditating = true
	velocity = Vector3.ZERO
	if moves:
		moves.meditate_enter()
	elif anim:
		anim.play("meditate", 0.4)
		anim.speed_scale = 1.0
	if _med_sound:
		_med_sound.stop()
	_med_sound = Audio.sfx("meditate_loop", -10.0)
	meditation_changed.emit(true)


func stop_meditation() -> void:
	if not meditating:
		return
	meditating = false
	if _med_sound:
		_med_sound.stop()
		_med_sound = null
	if moves:
		moves.meditate_exit()
	elif anim:
		anim.play("idle", 0.4)
	meditation_changed.emit(false)


func take_damage(amount: float, _from: Node = null) -> void:
	if dead or _invulnerable > 0.0:
		return
	if moves:
		amount = moves.filter_damage(amount, _from)
		if amount <= 0.0:
			return
	stop_meditation()
	hp = maxf(0.0, hp - amount)
	hp_changed.emit(hp, Game.max_hp())
	_invulnerable = 0.35
	Audio.sfx("player_hurt", -4.0, randf_range(0.9, 1.1))
	if hp <= 0.0:
		dead = true
		_strike_at = -1.0
		_jump_buffer = 0.0
		if anim:
			anim.play(moves.death_anim(_from) if moves else "death", 0.1)
			anim.speed_scale = 1.0
		_action_lock = 99.0
		died.emit()
	elif moves:
		moves.hit_reaction(amount, _from)
	elif _action_lock <= 0.0 and anim:
		anim.play("hit", 0.05)
		_action_lock = 0.3


func respawn(at: Vector3) -> void:
	stop_meditation()
	global_position = at
	velocity = Vector3.ZERO
	_action_lock = 0.0
	_strike_at = -1.0
	_jump_buffer = 0.0
	_vis_offset = 0.0
	_air_time = 0.0
	_gait = ""
	refill()
	if moves:
		moves.on_respawn()
	elif anim:
		anim.play("idle")


## Standing: on the floor, or crossing the nose of a step with ground just below.
func is_grounded() -> bool:
	return is_on_floor() or _supported


## Teleport (map load, cinematics, tests): no step smoothing carried over.
func place_at(at: Vector3) -> void:
	global_position = at
	velocity = Vector3.ZERO
	_vis_offset = 0.0
	_air_time = 0.0
	_apply_visual_offset()
	if moves:
		moves.reset_state()


func _physics_process(delta: float) -> void:
	var input := Vector2.ZERO
	if controls_enabled and not dead:
		input = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
		if scripted_input != Vector2.ZERO:
			input = scripted_input
	var running := (Input.is_action_pressed("run") or scripted_run) and controls_enabled

	pivot.rotation = Vector3(_pitch, _yaw, 0)
	var basis_yaw := Basis(Vector3.UP, _yaw)
	var dir := (basis_yaw * Vector3(input.x, 0, input.y))
	dir.y = 0
	dir = dir.normalized() if dir.length() > 0.01 else Vector3.ZERO
	_jump_buffer = maxf(0.0, _jump_buffer - delta)
	if moves:
		var d = moves.pre_physics(delta, dir, running)
		if d == null:
			_air_time = 0.0 if is_on_floor() else _air_time + delta
			_ease_visuals(delta, 0.0)
			return
		dir = d
	if meditating and dir != Vector3.ZERO:
		stop_meditation()
	if meditating:
		dir = Vector3.ZERO
		hp = minf(Game.max_hp(), hp + delta * 8.0)
		qi = minf(Game.max_qi(), qi + delta * 10.0)
		hp_changed.emit(hp, Game.max_hp())
		qi_changed.emit(qi, Game.max_qi())
	elif qi < Game.max_qi():
		qi = minf(Game.max_qi(), qi + delta * 1.5)
		qi_changed.emit(qi, Game.max_qi())
	_invulnerable = maxf(0.0, _invulnerable - delta)

	if _action_lock > 0.0:
		_action_lock -= delta
		dir = Vector3.ZERO
	if _strike_at >= 0.0:
		_strike_at -= delta
		if _strike_at < 0.0:
			_apply_strike()

	var speed: float = (RUN_SPEED if running else WALK_SPEED) * (moves.speed_mult(running) if moves else 1.0)
	var target := dir * speed
	var on_floor := is_grounded()
	var planar := Vector2(velocity.x, velocity.z)
	var want := Vector2(target.x, target.z)
	var rate := (ACCEL if want.length() >= planar.length() - 0.01 else BRAKE) if on_floor else AIR_ACCEL
	planar = planar.move_toward(want, rate * delta)
	velocity.x = planar.x
	velocity.z = planar.y
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	if _jump_buffer > 0.0 and controls_enabled and not dead and _action_lock <= 0.0 and not meditating \
			and (on_floor or _air_time < COYOTE) and velocity.y <= 0.5:
		velocity.y = JUMP_VELOCITY
		_jump_buffer = 0.0
		_air_time = COYOTE
		Audio.sfx("jump", -8.0)
	move_body(delta)

	var yaw_before := model_root.rotation.y
	if dir != Vector3.ZERO and not (moves and moves.facing_locked()):
		var target_yaw := atan2(dir.x, dir.z)
		model_root.rotation.y = lerp_angle(model_root.rotation.y, target_yaw, clampf(TURN_SPEED * delta, 0, 1))
	elif not controls_enabled and _face_point != Vector3.INF and not dead:
		var to := _face_point - global_position
		if Vector2(to.x, to.z).length() > 0.2:
			model_root.rotation.y = lerp_angle(model_root.rotation.y, atan2(to.x, to.z), clampf(6.0 * delta, 0, 1))
	# a slight lean into turns while running (never while walking or standing)
	var turn_rate := wrapf(model_root.rotation.y - yaw_before, -PI, PI) / maxf(delta, 0.001)
	var lean_target := 0.0
	var ground_speed := Vector2(velocity.x, velocity.z).length()
	if is_grounded() and ground_speed > RUN_UP:
		lean_target = clampf(-turn_rate * ground_speed * 0.012, -MAX_LEAN, MAX_LEAN)
	_ease_visuals(delta, lean_target)

	_update_animation(delta)


## move_and_slide() with stair handling: steps up onto risers up to
## Stepper.MAX_STEP and smooths the visible body over steps up and down.
func move_body(delta: float) -> void:
	var was_floor := is_on_floor()
	var y0 := global_position.y
	var rise := Stepper.step_up(self, delta, was_floor or _supported or _air_time < COYOTE)
	move_and_slide()
	var drop := Stepper.step_down(self, was_floor) if rise <= 0.0 else 0.0
	_supported = is_on_floor()
	if not _supported and velocity.y <= 0.0 and (drop < 0.0 or _air_time < 0.1) \
			and Stepper.ground_within(self, Stepper.MAX_STEP + 0.05):
		# riding over the nose of a step: not falling, just going down the stairs
		_supported = true
		velocity.y = clampf(velocity.y, -4.0, -1.0)
	if _supported:
		_air_time = 0.0
	else:
		_air_time += delta
	if rise > 0.0:
		last_step = rise
		_vis_offset = clampf(_vis_offset - rise, -0.6, 0.6)
	elif was_floor:
		var dy := global_position.y - y0
		if dy < -0.12:
			last_step = dy
			_vis_offset = clampf(_vis_offset - dy, -0.6, 0.6)


func _ease_visuals(delta: float, lean_target: float) -> void:
	_vis_offset = move_toward(_vis_offset, 0.0, delta * (1.2 + absf(_vis_offset) * 14.0))
	_lean = lerpf(_lean, lean_target, clampf(6.0 * delta, 0.0, 1.0))
	_apply_visual_offset()


func _apply_visual_offset() -> void:
	model_root.position.y = _vis_offset
	model_root.rotation.z = _lean
	pivot.position.y = PIVOT_HEIGHT + _vis_offset * 0.85


## Locomotion clip for a planar ground speed, with hysteresis between walk and run.
func gait_for(planar: float, current: String, can_sprint := false) -> String:
	if planar <= 0.15:
		return "idle"
	var fast := current in ["run", "sprint"]
	if planar > RUN_UP or (fast and planar > RUN_DOWN):
		if can_sprint and (planar > 5.3 or (current == "sprint" and planar > 4.9)):
			return "sprint"
		return "run"
	return "walk"


## speed_scale that plants the feet of `clip` at `planar` m/s.
static func stride_scale(clip: String, planar: float, model_scale := 1.0) -> float:
	var authored: float = AUTHORED_SPEED.get(clip, 0.0) * model_scale
	if authored <= 0.0:
		return 1.0
	# no clamp: any other rate slides the feet (a tiny floor only keeps a pose from freezing)
	return maxf(planar / authored, 0.05)


func _update_animation(delta: float) -> void:
	if anim == null or _action_lock > 0.0 or meditating or dead:
		return
	var planar := Vector2(velocity.x, velocity.z).length()
	if _held_pose != "" and planar < 0.15:
		return
	if moves and moves.update_animation(delta):
		return
	var wanted := gait_for(planar, _gait)
	var scale := stride_scale(wanted, planar)
	if anim.current_animation != wanted:
		anim.play(wanted, 0.2 if wanted != "idle" else 0.25)
	anim.speed_scale = scale
	_gait = wanted
	if wanted != "idle" and is_grounded():
		footstep_tick(wanted)
	else:
		_step_phase = -1.0


## Footfall sounds in time with the feet: two per cycle of the gait clip that is
## playing (at the start and the middle of the cycle, where the feet plant),
## whatever its length (it differs per character) and speed_scale.
func footstep_tick(clip: String, volume_db := -14.0) -> void:
	if anim == null or anim.current_animation != clip or anim.current_animation_length <= 0.0:
		_step_phase = -1.0
		return
	var ph := fposmod(anim.current_animation_position / anim.current_animation_length, 1.0)
	if _step_phase >= 0.0 and _step_clip == clip:
		for mark in [0.0, 0.5]:
			var crossed: bool = (_step_phase < mark and ph >= mark) if ph >= _step_phase \
					else (mark > _step_phase or mark <= ph)
			if crossed:
				footsteps += 1
				Audio.sfx("footstep_stone", volume_db, randf_range(0.9, 1.1))
				break
	_step_phase = ph
	_step_clip = clip


func current_animation() -> String:
	return anim.current_animation if anim else ""


func facing() -> Vector3:
	return model_root.global_basis.z

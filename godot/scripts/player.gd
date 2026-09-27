extends CharacterBody3D
## Third-person cultivator controller with light combat.
##
## WASD / arrows move relative to the camera, Shift runs, Space leaps
## (qinggong), Tab swaps between Lin Feng and Su Yue, E interacts,
## F / left click strikes, Q fires a qi blast, C meditates, G salutes.
## Hold the right mouse button (or click to capture the mouse) to orbit,
## scroll to zoom.

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
const JUMP_VELOCITY := 6.5
const GRAVITY := 13.0
const TURN_SPEED := 10.0
const MOUSE_SENSITIVITY := 0.004
const STRIKE_RANGE := 2.6
const BLAST_COST := 20.0
const QiBlast := preload("res://scripts/world/qi_blast.gd")
const PlayerMoves := preload("res://scripts/world/player_moves.gd")

## Initial camera yaw in radians (0 = looking toward -Z).
@export var start_yaw := 0.0

## Scripted input used by tests and demo captures: x = strafe, y = forward (-1).
var scripted_input := Vector2.ZERO
var scripted_run := false
## False while dialogue, cinematics or menus own the player.
var controls_enabled := true

var spawn_point := Vector3.ZERO
var character_index := 0
var model: Node3D
var anim: AnimationPlayer
var hp := 100.0
var qi := 60.0
var meditating := false
var dead := false
var _action_lock := 0.0
var _strike_at := -1.0
var _yaw := 0.0
var _pitch := -0.18
var _orbiting := false
var _step_timer := 0.0
var _invulnerable := 0.0
var _med_sound: AudioStreamPlayer
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
		"advance": [KEY_SPACE, KEY_ENTER, KEY_E],
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
	if anim:
		anim.play("meditate" if meditating else "idle")
	_action_lock = 0.0
	character_changed.emit(CHARACTERS[character_index].name)


func refill() -> void:
	hp = Game.max_hp()
	qi = Game.max_qi()
	dead = false
	hp_changed.emit(hp, Game.max_hp())
	qi_changed.emit(qi, Game.max_qi())


func play_action(anim_name: String) -> bool:
	if anim and anim.has_animation(anim_name) and is_on_floor() and _action_lock <= 0.0 and not dead:
		stop_meditation()
		anim.play(anim_name, 0.12)
		anim.speed_scale = 1.0
		_action_lock = anim.get_animation(anim_name).length * 0.85
		return true
	return false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			_orbiting = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed:
			if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
				if controls_enabled:
					strike()
			else:
				Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			spring.spring_length = maxf(1.5, spring.spring_length - 0.4)
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			spring.spring_length = minf(12.0, spring.spring_length + 0.4)
	elif event is InputEventMouseMotion:
		if _orbiting or Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
			var mm := event as InputEventMouseMotion
			_yaw -= mm.relative.x * MOUSE_SENSITIVITY
			_pitch = clampf(_pitch - mm.relative.y * MOUSE_SENSITIVITY, -1.2, 0.5)
	if not controls_enabled:
		return
	if moves and moves.handle_input(event):
		return
	if event.is_action_pressed("switch_character"):
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
		get_tree().create_timer(0.62 if not Game.fast else 0.0).timeout.connect(_fire_blast)


func _fire_blast() -> void:
	if dead:
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
		to.y = 0
		var reach: float = STRIKE_RANGE + e.radius + (moves.extra_reach if moves else 0.0)
		if to.length() < reach and (to.length() < 0.8 or fwd.dot(to.normalized()) > 0.25):
			e.take_damage(Game.strike_damage() * (moves.damage_mult if moves else 1.0), self)
			hit = true
	if hit:
		Audio.sfx("hit_flesh", -2.0, randf_range(0.9, 1.1))


func start_meditation() -> void:
	if meditating or not is_on_floor() or dead:
		return
	meditating = true
	velocity = Vector3.ZERO
	if moves:
		moves.meditate_enter()
	elif anim:
		anim.play("meditate", 0.4)
		anim.speed_scale = 1.0
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
		if anim:
			anim.play(moves.death_anim(_from) if moves else "death", 0.1)
		_action_lock = 99.0
		died.emit()
	elif moves:
		moves.hit_reaction(amount, _from)
	elif _action_lock <= 0.0 and anim:
		anim.play("hit", 0.05)
		_action_lock = 0.3


func respawn(at: Vector3) -> void:
	global_position = at
	velocity = Vector3.ZERO
	_action_lock = 0.0
	refill()
	if moves:
		moves.on_respawn()
	elif anim:
		anim.play("idle")


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
	if moves:
		var d = moves.pre_physics(delta, dir, running)
		if d == null:
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
	var accel := 12.0 if is_on_floor() else 3.0
	velocity.x = move_toward(velocity.x, target.x, accel * speed * delta)
	velocity.z = move_toward(velocity.z, target.z, accel * speed * delta)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif controls_enabled and Input.is_action_just_pressed("jump") and _action_lock <= 0.0 and not meditating:
		velocity.y = JUMP_VELOCITY
		Audio.sfx("jump", -8.0)
	move_and_slide()

	if dir != Vector3.ZERO and not (moves and moves.facing_locked()):
		var target_yaw := atan2(dir.x, dir.z)
		model_root.rotation.y = lerp_angle(model_root.rotation.y, target_yaw, clampf(TURN_SPEED * delta, 0, 1))

	_update_animation(delta)


func _update_animation(delta: float) -> void:
	if anim == null or _action_lock > 0.0 or meditating or dead:
		return
	if moves and moves.update_animation(delta):
		return
	var planar := Vector2(velocity.x, velocity.z).length()
	var wanted := "idle"
	var scale := 1.0
	if planar > 2.8:
		wanted = "run"
		scale = planar / 4.2
	elif planar > 0.15:
		wanted = "walk"
		scale = clampf(planar / 1.45, 0.5, 1.5)
	if anim.current_animation != wanted:
		anim.play(wanted, 0.25)
	anim.speed_scale = scale
	if wanted != "idle" and is_on_floor():
		_step_timer -= delta
		if _step_timer <= 0.0:
			_step_timer = 0.31 if wanted == "run" else 0.5
			Audio.sfx("footstep_stone", -14.0, randf_range(0.9, 1.1))


func current_animation() -> String:
	return anim.current_animation if anim else ""


func facing() -> Vector3:
	return model_root.global_basis.z

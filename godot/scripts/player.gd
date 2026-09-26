extends CharacterBody3D
## Third-person cultivator controller.
##
## WASD / arrows move relative to the camera, Shift runs, Space jumps
## (a light "qinggong" leap), Tab swaps between the male and female
## cultivator, E performs a salute, Q casts a sword-seal technique.
## Hold the right mouse button (or click to capture the mouse) to orbit,
## scroll to zoom.

signal character_changed(display_name: String)

const CHARACTERS := [
	{"name": "Disciple Lin Feng", "scene": preload("res://assets/characters/cultivator_male.glb")},
	{"name": "Fairy Su Yue", "scene": preload("res://assets/characters/cultivator_female.glb")},
]
const LOOPING := ["idle", "walk", "run"]
const WALK_SPEED := 1.6
const RUN_SPEED := 4.6
const JUMP_VELOCITY := 6.5
const GRAVITY := 13.0
const TURN_SPEED := 10.0
const MOUSE_SENSITIVITY := 0.004

## Initial camera yaw in radians (0 = looking toward -Z).
@export var start_yaw := 0.0

## Scripted input used by tests and demo captures: x = strafe, y = forward (-1).
var scripted_input := Vector2.ZERO
var scripted_run := false

var spawn_point := Vector3.ZERO
var character_index := 0
var model: Node3D
var anim: AnimationPlayer
var _action_lock := 0.0
var _yaw := 0.0
var _pitch := -0.18
var _orbiting := false

@onready var model_root: Node3D = $ModelRoot
@onready var pivot: Node3D = $CameraPivot
@onready var spring: SpringArm3D = $CameraPivot/SpringArm3D
@onready var camera: Camera3D = $CameraPivot/SpringArm3D/Camera3D


func _ready() -> void:
	_setup_input_map()
	spawn_point = global_position
	_yaw = start_yaw
	model_root.rotation.y = start_yaw + PI
	spring.add_excluded_object(get_rid())
	set_character(0)


static func _setup_input_map() -> void:
	var map := {
		"move_forward": [KEY_W, KEY_UP],
		"move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT],
		"run": [KEY_SHIFT],
		"jump": [KEY_SPACE],
		"switch_character": [KEY_TAB],
		"salute": [KEY_E],
		"cast": [KEY_Q],
		"release_mouse": [KEY_ESCAPE],
	}
	for action in map:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action)
		for key in map[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)


func set_character(index: int) -> void:
	character_index = wrapi(index, 0, CHARACTERS.size())
	if model:
		model.queue_free()
	model = CHARACTERS[character_index].scene.instantiate()
	model_root.add_child(model)
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim:
		for anim_name in LOOPING:
			if anim.has_animation(anim_name):
				anim.get_animation(anim_name).loop_mode = Animation.LOOP_LINEAR
		anim.play("idle")
	_action_lock = 0.0
	character_changed.emit(CHARACTERS[character_index].name)


func play_action(anim_name: String) -> void:
	if anim and anim.has_animation(anim_name) and is_on_floor():
		anim.play(anim_name, 0.2)
		_action_lock = anim.get_animation(anim_name).length


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			_orbiting = mb.pressed
		elif mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed:
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
	elif event.is_action_pressed("release_mouse"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif event.is_action_pressed("switch_character"):
		set_character(character_index + 1)
	elif event.is_action_pressed("salute"):
		play_action("salute")
	elif event.is_action_pressed("cast"):
		play_action("cast")


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if scripted_input != Vector2.ZERO:
		input = scripted_input
	var running := Input.is_action_pressed("run") or scripted_run

	pivot.rotation = Vector3(_pitch, _yaw, 0)
	var basis_yaw := Basis(Vector3.UP, _yaw)
	var dir := (basis_yaw * Vector3(input.x, 0, input.y))
	dir.y = 0
	dir = dir.normalized() if dir.length() > 0.01 else Vector3.ZERO

	if _action_lock > 0.0:
		_action_lock -= delta
		dir = Vector3.ZERO

	var speed := RUN_SPEED if running else WALK_SPEED
	var target := dir * speed
	var accel := 12.0 if is_on_floor() else 3.0
	velocity.x = move_toward(velocity.x, target.x, accel * speed * delta)
	velocity.z = move_toward(velocity.z, target.z, accel * speed * delta)
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	elif Input.is_action_just_pressed("jump") and _action_lock <= 0.0:
		velocity.y = JUMP_VELOCITY
	move_and_slide()

	if dir != Vector3.ZERO:
		var target_yaw := atan2(dir.x, dir.z)
		model_root.rotation.y = lerp_angle(model_root.rotation.y, target_yaw, clampf(TURN_SPEED * delta, 0, 1))

	_update_animation()
	if global_position.y < -30.0:
		global_position = spawn_point
		velocity = Vector3.ZERO


func _update_animation() -> void:
	if anim == null or _action_lock > 0.0:
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


func current_animation() -> String:
	return anim.current_animation if anim else ""

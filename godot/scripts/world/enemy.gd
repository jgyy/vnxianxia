class_name Enemy
extends CharacterBody3D
## Data-driven enemy: chases the player, attacks in range, flinches, dies.

signal died(enemy: Enemy)
signal aggroed(enemy: Enemy)

## kind -> stats. model: GLB under res://assets/characters ("player" = shadow clone).
const STATS := {
	"spirit_wolf": {"name": "Spirit Wolf", "model": "spirit_wolf", "hp": 45, "dmg": 6, "speed": 4.6, "range": 1.9, "cd": 1.6, "hit_t": 0.35, "sfx": "wolf_growl"},
	"corrupted_wolf": {"name": "Corrupted Wolf", "model": "spirit_wolf", "hp": 75, "dmg": 10, "speed": 4.8, "range": 1.9, "cd": 1.5, "hit_t": 0.35, "tint": Color(0.75, 0.3, 0.33), "glow": Color(1, 0.2, 0.1), "sfx": "wolf_growl"},
	"wolf_king": {"name": "Silvermoon Wolf King", "model": "spirit_wolf", "hp": 420, "dmg": 15, "speed": 5.2, "range": 2.8, "cd": 1.4, "hit_t": 0.35, "scale": 1.7, "tint": Color(1.1, 1.1, 1.2), "sfx": "wolf_howl"},
	"bandit": {"name": "Bandit", "model": "bandit", "hp": 60, "dmg": 8, "speed": 3.4, "range": 1.6, "cd": 1.5, "hit_t": 0.4},
	"bandit_chief": {"name": "Bandit Chief Iron Fang", "model": "bandit", "hp": 520, "dmg": 16, "speed": 3.8, "range": 1.8, "cd": 1.3, "hit_t": 0.4, "scale": 1.15, "tint": Color(0.7, 0.55, 0.5)},
	"training_puppet": {"name": "Training Puppet", "model": "stone_golem", "hp": 30, "dmg": 3, "speed": 2.2, "range": 1.8, "cd": 2.0, "hit_t": 0.4, "scale": 0.72, "tint": Color(0.95, 0.72, 0.5), "sfx": "golem_step"},
	"sparring_disciple": {"name": "Sparring Disciple", "model": "disciple_male", "hp": 60, "dmg": 6, "speed": 3.4, "range": 1.6, "cd": 1.5, "hit_t": 0.4},
	"tournament_champion": {"name": "Tournament Champion", "model": "disciple_male", "hp": 480, "dmg": 14, "speed": 4.0, "range": 1.7, "cd": 1.2, "hit_t": 0.4, "tint": Color(0.75, 0.8, 1.0)},
	"demon_cultivator": {"name": "Blood Moon Cultivator", "model": "demon_cultivator", "hp": 95, "dmg": 12, "speed": 3.6, "range": 1.7, "cd": 1.4, "hit_t": 0.4, "sfx": "demon_laugh_ish"},
	"blood_guard": {"name": "Blood Guard", "model": "demon_cultivator", "hp": 150, "dmg": 16, "speed": 3.4, "range": 1.8, "cd": 1.4, "hit_t": 0.4, "scale": 1.08, "tint": Color(0.7, 0.5, 0.5)},
	"demon_elder": {"name": "Demon Elder", "model": "demon_cultivator", "hp": 850, "dmg": 20, "speed": 3.8, "range": 1.9, "cd": 1.2, "hit_t": 0.4, "scale": 1.12, "tint": Color(0.6, 0.45, 0.65)},
	"blood_patriarch": {"name": "The Blood Moon Patriarch", "model": "blood_patriarch", "hp": 1700, "dmg": 26, "speed": 3.9, "range": 2.1, "cd": 1.1, "hit_t": 0.4},
	"stone_golem": {"name": "Stone Golem", "model": "stone_golem", "hp": 160, "dmg": 18, "speed": 2.3, "range": 2.2, "cd": 2.0, "hit_t": 0.45, "sfx": "golem_rumble"},
	"ancient_guardian": {"name": "Ancient Guardian", "model": "stone_golem", "hp": 950, "dmg": 24, "speed": 2.6, "range": 3.4, "cd": 1.8, "hit_t": 0.45, "scale": 2.0, "sfx": "golem_rumble"},
	"jiao_serpent": {"name": "Jiao, the Flood Dragon", "model": "jiao_serpent", "hp": 1500, "dmg": 24, "speed": 3.4, "range": 7.0, "cd": 1.8, "hit_t": 0.6, "radius": 1.0, "scale": 1.5, "sfx": "serpent_roar"},
	"heart_demon": {"name": "Heart Demon", "model": "player", "hp": 1100, "dmg": 22, "speed": 4.4, "range": 1.7, "cd": 1.0, "hit_t": 0.4},
	# added for the 1000-quest saga
	"rogue_cultivator": {"name": "Rogue Cultivator", "model": "bandit", "hp": 80, "dmg": 10, "speed": 3.6, "range": 1.7, "cd": 1.4, "hit_t": 0.4, "tint": Color(0.55, 0.6, 0.75)},
	"iron_scale_disciple": {"name": "Iron Scale Disciple", "model": "disciple_male", "hp": 110, "dmg": 12, "speed": 3.5, "range": 1.7, "cd": 1.4, "hit_t": 0.4, "tint": Color(0.55, 0.72, 0.6)},
	"void_wraith": {"name": "Void Wraith", "model": "demon_cultivator", "hp": 140, "dmg": 16, "speed": 4.0, "range": 1.8, "cd": 1.3, "hit_t": 0.4, "tint": Color(0.42, 0.36, 0.7), "glow": Color(0.55, 0.3, 1.0), "sfx": "demon_laugh_ish"},
	"thunder_wolf": {"name": "Thunder Wolf", "model": "spirit_wolf", "hp": 120, "dmg": 15, "speed": 5.2, "range": 1.9, "cd": 1.3, "hit_t": 0.35, "tint": Color(0.7, 0.8, 1.2), "glow": Color(0.4, 0.7, 1.0), "sfx": "wolf_growl"},
	"celestial_sentinel": {"name": "Celestial Sentinel", "model": "stone_golem", "hp": 220, "dmg": 20, "speed": 2.6, "range": 2.3, "cd": 1.8, "hit_t": 0.45, "scale": 1.15, "tint": Color(0.75, 0.95, 0.9), "sfx": "golem_rumble"},
	"rung_deacon": {"name": "Rung of the Ladder", "model": "demon_cultivator", "hp": 1300, "dmg": 24, "speed": 4.0, "range": 2.0, "cd": 1.1, "hit_t": 0.4, "scale": 1.12, "tint": Color(0.5, 0.25, 0.35), "glow": Color(1.0, 0.2, 0.3)},
	"void_colossus": {"name": "Void Colossus", "model": "stone_golem", "hp": 1800, "dmg": 28, "speed": 2.4, "range": 3.6, "cd": 1.9, "hit_t": 0.5, "scale": 2.2, "tint": Color(0.38, 0.32, 0.55), "glow": Color(0.6, 0.35, 1.0), "sfx": "golem_rumble"},
	# waves of a heavenly tribulation (world/tribulation.gd)
	"tribulation_beast": {"name": "Tribulation Beast", "model": "spirit_wolf", "hp": 110, "dmg": 12, "speed": 5.0, "range": 1.9, "cd": 1.4, "hit_t": 0.35, "scale": 1.2, "tint": Color(0.85, 0.9, 1.3), "glow": Color(0.55, 0.8, 1.0), "sfx": "wolf_howl"},
	"heart_shade": {"name": "Heart Shade", "model": "player", "hp": 130, "dmg": 12, "speed": 4.0, "range": 1.7, "cd": 1.3, "hit_t": 0.4},
}
## The realm tier each enemy's base stats were tuned for. Fought in a later
## tier (story.json gives every quest the realm index at its start), an enemy
## gains 30% hit points and 20% damage per tier, so late fights keep pace with
## the protagonist's growing strength.
const NATIVE_TIER := {
	"training_puppet": 0, "spirit_wolf": 1, "corrupted_wolf": 1, "wolf_king": 1, "bandit": 1, "sparring_disciple": 1,
	"demon_cultivator": 1, "stone_golem": 1, "ancient_guardian": 1, "bandit_chief": 3, "tournament_champion": 2,
	"blood_guard": 2, "demon_elder": 2, "jiao_serpent": 3, "heart_demon": 4, "blood_patriarch": 6,
	"rogue_cultivator": 1, "iron_scale_disciple": 3, "void_wraith": 5, "thunder_wolf": 5, "celestial_sentinel": 4,
	"rung_deacon": 4, "void_colossus": 6, "tribulation_beast": 4, "heart_shade": 4,
}
const GRAVITY := 13.0
const AGGRO := 16.0
const Stepper := preload("res://scripts/world/stepper.gd")
## Humanoid gait clips plant their feet at these ground speeds (m/s) at
## speed_scale 1 (the animation contract); creatures keep their own gaits.
const WALK_AUTHORED := 1.6
const RUN_AUTHORED := 4.6

var kind := ""
## realm tier of the fight (-1 = the protagonist's current realm)
var tier := -1
## display name override (named bosses)
var title := ""
var stats: Dictionary = {}
var hp := 1.0
var max_hp := 1.0
var dead := false
var boss := false
var radius := 0.45
var height := 1.8
var home := Vector3.ZERO
var model: Node3D
var anim: AnimationPlayer
var target: Node3D
var _cooldown := 0.5
var _lock := 0.0
var _strike := -1.0
var _aggro := false
var _hits := 0
var _bar_bg: MeshInstance3D
var _bar: MeshInstance3D
var _bar_mesh: QuadMesh
var _home_set := false
var _humanoid := true
var _model_scale := 1.0
var _vis := 0.0
var _gait := "idle"


static func create(enemy_kind: String, is_boss := false, fight_tier := -1, display := "") -> Enemy:
	var e := Enemy.new()
	e.kind = enemy_kind
	e.boss = is_boss
	e.tier = fight_tier
	e.title = display
	return e


## Stat multiplier for fighting ``k`` at realm tier ``t``.
static func tier_scale(k: String, t: int, per_tier: float) -> float:
	return 1.0 + per_tier * maxf(0.0, float(t - int(NATIVE_TIER.get(k, 1))))


func _ready() -> void:
	stats = STATS.get(kind, STATS["bandit"])
	add_to_group("enemies")
	collision_layer = 4
	collision_mask = 1
	floor_snap_length = Stepper.MAX_STEP + 0.05
	floor_constant_speed = true
	floor_max_angle = deg_to_rad(50.0)
	var sc: float = stats.get("scale", 1.0)
	_model_scale = sc
	var t := tier if tier >= 0 else Game.realm
	stats = stats.duplicate()
	stats.dmg = float(stats.dmg) * tier_scale(kind, t, 0.2)
	max_hp = float(stats.hp) * tier_scale(kind, t, 0.3)
	hp = max_hp
	radius = stats.get("radius", 0.4) * sc
	height = 1.8 * sc
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = minf(radius, 0.8)
	cap.height = maxf(height, cap.radius * 2.0 + 0.1)
	shape.shape = cap
	shape.position.y = cap.height * 0.5
	add_child(shape)
	var path: String = stats.model
	if path == "player":
		path = "cultivator_male" if Game.character == 0 else "cultivator_female"
	if not ResourceLoader.exists("res://assets/characters/%s.glb" % path):
		push_warning("enemy %s: no model %s" % [kind, path])
		path = "bandit"
	model = (load("res://assets/characters/%s.glb" % path) as PackedScene).instantiate()
	model.scale = Vector3.ONE * sc
	add_child(model)
	if stats.model == "player":
		ActorLook.shadow(model)
	elif stats.has("tint"):
		ActorLook.recolor(model, stats.tint, stats.get("glow", Color.BLACK))
	else:
		ActorLook.apply(model)
	anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim:
		ActorLook.loop_anims(anim)
		anim.play("idle")
		anim.seek(randf() * 2.0)
	_humanoid = not (Story.world.get("creature_anims", {}) as Dictionary).has(stats.model)
	if not boss:
		_make_bar()


func display_name() -> String:
	if title != "":
		return title
	return stats.get("name", kind.capitalize())


func _make_bar() -> void:
	var bg := QuadMesh.new()
	bg.size = Vector2(0.9, 0.09)
	_bar_bg = MeshInstance3D.new()
	_bar_bg.mesh = bg
	_bar_bg.material_override = _bar_mat(Color(0, 0, 0, 0.6))
	_bar_mesh = QuadMesh.new()
	_bar_mesh.size = Vector2(0.86, 0.06)
	_bar = MeshInstance3D.new()
	_bar.mesh = _bar_mesh
	_bar.material_override = _bar_mat(Color(0.85, 0.15, 0.12))
	_bar.material_override.render_priority = 1
	for m in [_bar_bg, _bar]:
		m.position.y = height + 0.35
		m.visible = false
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(m)


func _bar_mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = c
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.no_depth_test = true
	return m


func _update_bar() -> void:
	if _bar == null:
		return
	var f := clampf(hp / max_hp, 0.0, 1.0)
	_bar_mesh.size.x = 0.86 * f
	_bar_mesh.center_offset.x = -0.43 * (1.0 - f)
	_bar.visible = _aggro and not dead
	_bar_bg.visible = _bar.visible


func take_damage(amount: float, _from: Node = null) -> void:
	if dead:
		return
	hp -= amount
	_hits += 1
	_set_aggro()
	Fx.burst(get_parent(), global_position + Vector3.UP * height * 0.6, Color(1.0, 0.85, 0.5), 16, 3.0, 0.035)
	if hp <= 0.0:
		_die()
		return
	if anim and (not boss or _hits % 4 == 0) and _strike < 0.0:
		anim.play("hit", 0.05)
		anim.speed_scale = 1.0
		_gait = ""
		_lock = 0.35
	_update_bar()


func _set_aggro() -> void:
	if not _aggro:
		_aggro = true
		aggroed.emit(self)
		if stats.has("sfx"):
			Audio.sfx(stats.sfx, -4.0)


func _die() -> void:
	dead = true
	hp = 0.0
	remove_from_group("enemies")
	_update_bar()
	set_deferred("collision_layer", 0)
	if anim:
		anim.play("death", 0.1)
		anim.speed_scale = 1.0
	Audio.sfx("enemy_death", -4.0 if not boss else 0.0)
	Fx.burst(get_parent(), global_position + Vector3.UP * height * 0.5, Color(0.6, 0.9, 1.0), 60 if boss else 30, 4.0)
	died.emit(self)
	var tw := create_tween()
	tw.tween_interval(3.0 if not Game.fast else 0.0)
	tw.tween_property(self, "scale", Vector3.ONE * 0.01, 0.6)
	tw.tween_callback(queue_free)


func _physics_process(delta: float) -> void:
	if not _home_set:
		# spawners add the enemy to the tree first and place it afterwards
		home = global_position
		_home_set = true
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = -0.5
	if dead:
		velocity.x = 0
		velocity.z = 0
		move_and_slide()
		return
	var map := get_parent()
	if map and "kill_y" in map and global_position.y < float(map.kill_y):
		# fell off the world (chasing over a cliff): come back, or the fight could never be won
		global_position = home + Vector3.UP * 0.3
		velocity = Vector3.ZERO
	if target == null or not is_instance_valid(target):
		target = get_tree().get_first_node_in_group("player") as Node3D
	var to := Vector3.ZERO
	var dist := 999.0
	var player_ok: bool = target != null and not target.dead and target.controls_enabled
	if player_ok:
		to = target.global_position - global_position
		to.y = 0
		dist = to.length()
		if dist < AGGRO or (_aggro and dist < AGGRO * 2.5):
			_set_aggro()
	_cooldown -= delta
	_lock -= delta
	if _strike >= 0.0:
		_strike -= delta
		if _strike < 0.0 and player_ok and dist < float(stats.range) + 0.9 + radius \
				and absf(target.global_position.y - global_position.y) < 2.5:
			target.take_damage(float(stats.dmg), self)
	var want := Vector3.ZERO
	var reach: float = float(stats.range) + radius * 0.5
	if _aggro and player_ok and _lock <= 0.0:
		_face(to, delta)
		if dist > reach:
			want = to.normalized() * float(stats.speed)
		elif _cooldown <= 0.0:
			_attack()
	elif _aggro and not player_ok:
		_aggro = false if target == null or target.dead else _aggro
	# keep a little space from other enemies
	for e in get_tree().get_nodes_in_group("enemies"):
		if e != self:
			var d: Vector3 = global_position - e.global_position
			d.y = 0
			var min_d: float = radius + e.radius + 0.4
			if d.length() < min_d and d.length() > 0.01:
				want += d.normalized() * 1.5
	velocity.x = move_toward(velocity.x, want.x, 20.0 * delta)
	velocity.z = move_toward(velocity.z, want.z, 20.0 * delta)
	var was_floor := is_on_floor()
	var rise := Stepper.step_up(self, delta, was_floor, Stepper.MAX_STEP * maxf(_model_scale, 1.0))
	move_and_slide()
	var drop := Stepper.step_down(self, was_floor) if rise <= 0.0 else 0.0
	_vis = clampf(_vis - rise - drop, -0.6, 0.6)
	_vis = move_toward(_vis, 0.0, delta * (1.2 + absf(_vis) * 14.0))
	if model:
		model.position.y = _vis
	if anim and _lock <= 0.0 and _strike < 0.0:
		_animate_gait(Vector2(velocity.x, velocity.z).length())
	_update_bar()


## Walk / run with hysteresis; humanoids play them at speed_scale = ground
## speed / authored speed (feet planted), creatures at their chase speed.
func _animate_gait(planar: float) -> void:
	var a := "idle"
	var fast := _gait == "run"
	if planar > 3.1 or (fast and planar > 2.5) or (not _humanoid and planar > 2.5):
		a = "run"
	elif planar > 0.2:
		a = "walk"
	var sc := 1.0
	if _humanoid:
		if a == "run":
			sc = maxf(planar / (RUN_AUTHORED * _model_scale), 0.05)
		elif a == "walk":
			sc = maxf(planar / (WALK_AUTHORED * _model_scale), 0.05)
	elif a == "run":
		sc = clampf(planar / maxf(float(stats.speed), 0.1), 0.5, 1.5)
	elif a == "walk":
		sc = clampf(planar / maxf(float(stats.speed) * 0.35, 0.1), 0.4, 1.5)
	if anim.current_animation != a:
		anim.play(a, 0.2)
	anim.speed_scale = sc
	_gait = a


## The player fell and was revived: calm down, heal and go back to the post.
func reset_after_player_death() -> void:
	if dead:
		return
	hp = max_hp
	_aggro = false
	_strike = -1.0
	_lock = 0.0
	_hits = 0
	global_position = home + Vector3.UP * 0.1
	velocity = Vector3.ZERO
	_update_bar()


func _face(to: Vector3, delta: float) -> void:
	if to.length() > 0.01:
		rotation.y = lerp_angle(rotation.y, atan2(to.x, to.z), clampf(8.0 * delta, 0, 1))


func _attack() -> void:
	_cooldown = float(stats.cd) * randf_range(0.85, 1.2)
	if anim and anim.has_animation("attack"):
		anim.play("attack", 0.1)
		anim.speed_scale = 1.0
		_gait = ""
		_lock = anim.get_animation("attack").length * 0.8
	_strike = float(stats.hit_t)
	if kind.contains("wolf"):
		Audio.sfx("wolf_attack", -6.0)
	elif stats.model == "stone_golem":
		Audio.sfx("golem_step", -4.0)
	else:
		Audio.sfx("sword_swing", -8.0, 0.85)

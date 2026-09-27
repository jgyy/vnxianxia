class_name Tribulation
extends Node3D
## A heavenly tribulation (story objective type "tribulation"): dark clouds
## swirl over the marker and lightning falls on the player in volleys.
##
## Each volley is marked on the ground a moment before it lands. The player
## survives by enduring (meditating halves the damage, and does not break the
## meditation), by stepping out of the marked circle, or by letting qi blunt a
## bolt. From Nascent Soul on, waves of tribulation beasts and heart shades
## attack between volleys; the storm waits until they fall. If the lightning
## (or a wave) would strike the player down, the tribulation fails and starts
## again from the first volley once the player returns.
##
## Damage is budgeted: a player who takes every volley standing loses
## DAMAGE_BUDGET of their vitality over the whole tribulation (so they must
## dodge, shield or meditate), one who meditates through it loses half that.

signal volley_struck(done: int, total: int)
signal wave_spawned(enemies: Array)
signal survived
signal failed

const CLOUD_HEIGHT := 22.0
const STRIKE_RADIUS := 2.0
const DAMAGE_BUDGET := 1.3
const MEDITATE_FACTOR := 0.5
const QI_SHIELD := 0.35
const QI_COST := 12.0
const MAX_VOLLEYS := 9
## seconds (scaled down in fast mode)
const T_GATHER := 2.6
const T_TELEGRAPH := 1.15
const T_COOLDOWN := 1.25
const T_FADE := 1.6

var bolts := 3
var volleys := 3
## bolts landing in each volley (sums to ``bolts`` exactly, not just to a
## per-volley ceiling times ``volleys``, so a count that doesn't divide evenly
## never strikes more bolts than the objective actually asked for).
var per_volley: Array[int] = [1]
var waves: Array = []
var tier := -1
var done := 0
var running := false
var finished := false
var enemies: Array[Enemy] = []
var player: Node3D
var _phase := ""
var _t := 0.0
var _targets: Array[Vector3] = []
var _rings: Array[MeshInstance3D] = []
var _clouds: Array[MeshInstance3D] = []
var _cloud_mat: ShaderMaterial
var _light: OmniLight3D
var _wave_i := 0
var _fade := 0.0

const CLOUD_SHADER := """
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, blend_mix;
uniform float fade = 0.0;
uniform float flash = 0.0;
uniform float spin = 1.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 5; i++) { v += a * noise(p); p *= 2.03; a *= 0.5; }
	return v;
}
void fragment() {
	vec2 p = UV - 0.5;
	float r = length(p) * 2.0;
	float ang = atan(p.y, p.x) + r * 3.2 - TIME * 0.45 * spin;
	vec2 q = vec2(cos(ang), sin(ang)) * r * 3.0;
	float n = fbm(q * 1.4 + vec2(TIME * 0.07, -TIME * 0.05));
	float eye = smoothstep(0.08, 0.22, r);
	vec3 col = mix(vec3(0.03, 0.03, 0.06), vec3(0.22, 0.2, 0.34), n);
	col += vec3(0.55, 0.65, 1.0) * flash * (1.0 - r) * (0.5 + n);
	col += vec3(0.35, 0.45, 0.9) * (1.0 - eye) * 0.6;
	ALBEDO = col;
	ALPHA = smoothstep(1.0, 0.45, r) * (0.45 + 0.5 * n) * fade;
}
"""


static func create(obj: Dictionary, fight_tier := -1) -> Tribulation:
	var t := Tribulation.new()
	t.bolts = int(obj.get("bolts", 3))
	t.volleys = mini(t.bolts, MAX_VOLLEYS)
	t.per_volley = _split_bolts(t.bolts, t.volleys)
	t.waves = obj.get("waves", []) if obj.get("waves") else []
	t.tier = fight_tier
	return t


## Split ``bolts`` lightning strikes as evenly as possible across ``volleys``
## volleys (each gets the base count, the first ``bolts % volleys`` get one
## more), so the total struck is always exactly ``bolts``.
static func _split_bolts(bolts: int, volleys: int) -> Array[int]:
	var out: Array[int] = []
	var base := bolts / volleys
	var extra := bolts % volleys
	for i in volleys:
		out.append(base + (1 if i < extra else 0))
	return out


func _ready() -> void:
	var shader := Shader.new()
	shader.code = CLOUD_SHADER
	_cloud_mat = ShaderMaterial.new()
	_cloud_mat.shader = shader
	for i in 2:
		var mi := MeshInstance3D.new()
		var plane := PlaneMesh.new()
		plane.size = Vector2(44, 44) if i == 0 else Vector2(28, 28)
		mi.mesh = plane
		var m: ShaderMaterial = _cloud_mat if i == 0 else _cloud_mat.duplicate()
		if i == 1:
			m.set_shader_parameter("spin", -1.6)
		mi.material_override = m
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.position = Vector3(0, CLOUD_HEIGHT - 2.5 * i, 0)
		add_child(mi)
		_clouds.append(mi)
	_light = OmniLight3D.new()
	_light.light_color = Color(0.7, 0.8, 1.0)
	_light.omni_range = 30.0
	_light.light_energy = 0.0
	_light.position = Vector3(0, 9, 0)
	add_child(_light)


func _speed() -> float:
	return 0.04 if Game.fast else 1.0


## Start (or restart) the tribulation with ``p`` standing in it.
func begin(p: Node3D) -> void:
	player = p
	if player.has_signal("died") and not player.died.is_connected(_on_player_died):
		player.died.connect(_on_player_died)
	_clear_wave()
	_clear_rings()
	done = 0
	_wave_i = 0
	running = true
	finished = false
	if player.has_method("refill"):
		player.refill()     # heaven tests a cultivator at full strength
	_phase = "gather"
	_t = T_GATHER * _speed()
	Audio.sfx("thunder", -6.0, 0.7)


func _process(delta: float) -> void:
	# clouds gather while the tribulation runs and thin out afterwards
	var want := 1.0 if running else 0.0
	_fade = move_toward(_fade, want, delta / (T_FADE * _speed()))
	for c in _clouds:
		(c.material_override as ShaderMaterial).set_shader_parameter("fade", _fade)
	_light.light_energy = move_toward(_light.light_energy, 0.0, delta * 30.0)
	for c in _clouds:
		(c.material_override as ShaderMaterial).set_shader_parameter("flash", _light.light_energy / 10.0)
	for r in _rings:
		if is_instance_valid(r):
			var a := 0.35 + 0.35 * sin(Time.get_ticks_msec() / 60.0)
			(r.material_override as StandardMaterial3D).albedo_color.a = a
	if not running:
		return
	_t -= delta
	match _phase:
		"gather":
			if _t <= 0.0:
				_telegraph()
		"telegraph":
			if _t <= 0.0:
				_strike()
		"cooldown":
			if _t <= 0.0:
				if _wave_i < waves.size() and done >= int(waves[_wave_i].after):
					_spawn_wave(waves[_wave_i])
					_wave_i += 1
				elif done >= volleys:
					_finish()
				else:
					_telegraph()
		"wave":
			enemies = enemies.filter(func(e): return is_instance_valid(e) and not e.dead)
			if enemies.is_empty():
				_phase = "cooldown"
				_t = T_COOLDOWN * _speed()


func _telegraph() -> void:
	_clear_rings()
	_targets.clear()
	var c := player.global_position if is_instance_valid(player) else global_position
	_targets.append(c)
	var count: int = per_volley[clampi(done, 0, per_volley.size() - 1)]
	for k in count - 1:
		var a := TAU * k / maxf(count - 1, 1) + done * 0.7
		_targets.append(c + Vector3(cos(a), 0, sin(a)) * (3.5 + 1.5 * (k % 2)))
	var map := get_parent()
	for tp in _targets:
		var ring := MeshInstance3D.new()
		var torus := TorusMesh.new()
		torus.inner_radius = STRIKE_RADIUS - 0.25
		torus.outer_radius = STRIKE_RADIUS
		ring.mesh = torus
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		m.albedo_color = Color(0.75, 0.85, 1.0, 0.5)
		ring.material_override = m
		ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(ring)
		var g: Vector3 = map.ground_at(tp) if map and map.has_method("ground_at") else tp
		ring.global_position = g + Vector3.UP * 0.06
		_rings.append(ring)
	_phase = "telegraph"
	_t = T_TELEGRAPH * _speed()


func _strike() -> void:
	var hit := false
	for tp in _targets:
		_bolt(tp)
		if is_instance_valid(player):
			var d := Vector2(player.global_position.x - tp.x, player.global_position.z - tp.z).length()
			if d <= STRIKE_RADIUS and absf(player.global_position.y - tp.y) < 4.0:
				hit = true
	_clear_rings()
	_light.light_energy = 10.0
	Audio.sfx("thunder", 0.0, randf_range(0.85, 1.1))
	done += 1
	volley_struck.emit(done, volleys)
	if hit and not _damage():
		return
	_phase = "cooldown"
	_t = T_COOLDOWN * _speed()


## Apply one volley's damage; false if it would strike the player down (the tribulation fails).
func _damage() -> bool:
	if not is_instance_valid(player):
		return true
	var dmg := Game.max_hp() * DAMAGE_BUDGET / float(volleys)
	var meditating: bool = player.get("meditating") == true
	if meditating:
		dmg *= MEDITATE_FACTOR
	elif float(player.get("qi")) >= QI_COST:
		player.qi -= QI_COST
		player.qi_changed.emit(player.qi, Game.max_qi())
		dmg *= 1.0 - QI_SHIELD
	if float(player.hp) - dmg <= 1.0:
		_fail()
		return false
	if meditating:
		# the storm does not break a meditation: endure it
		player.hp -= dmg
		player.hp_changed.emit(player.hp, Game.max_hp())
		Audio.sfx("player_hurt", -8.0)
	else:
		player.take_damage(dmg)
	return true


func _bolt(at: Vector3) -> void:
	var map := get_parent()
	var ground: Vector3 = map.ground_at(at) if map and map.has_method("ground_at") else at
	var top := Vector3(ground.x + randf_range(-2, 2), global_position.y + CLOUD_HEIGHT, ground.z + randf_range(-2, 2))
	var root := Node3D.new()
	add_child(root)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.85, 0.92, 1.0)
	m.emission_enabled = true
	m.emission = Color(0.6, 0.75, 1.0)
	m.emission_energy_multiplier = 4.0
	var glow := m.duplicate() as StandardMaterial3D
	glow.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glow.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	glow.albedo_color = Color(0.4, 0.55, 1.0, 0.35)
	var pts: Array[Vector3] = [top]
	var segs := 8
	for i in range(1, segs):
		var f := float(i) / segs
		var p := top.lerp(ground, f)
		p += Vector3(randf_range(-1.2, 1.2), 0, randf_range(-1.2, 1.2)) * (1.0 - f * 0.6)
		pts.append(p)
	pts.append(ground)
	for i in pts.size() - 1:
		for layer in 2:
			var seg := MeshInstance3D.new()
			var cyl := CylinderMesh.new()
			var r := 0.07 if layer == 0 else 0.28
			cyl.top_radius = r
			cyl.bottom_radius = r
			cyl.height = pts[i].distance_to(pts[i + 1])
			cyl.radial_segments = 6
			cyl.rings = 1
			seg.mesh = cyl
			seg.material_override = m if layer == 0 else glow
			seg.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			root.add_child(seg)
			var mid := (pts[i] + pts[i + 1]) * 0.5
			seg.global_position = mid
			var dir := (pts[i + 1] - pts[i]).normalized()
			if absf(dir.dot(Vector3.UP)) < 0.999:
				seg.look_at(mid + dir, Vector3.UP)
				seg.rotate_object_local(Vector3.RIGHT, PI / 2)
	if map:
		Fx.burst(map, ground + Vector3.UP * 0.3, Color(0.7, 0.8, 1.0), 50, 6.0, 0.05)
	get_tree().create_timer(0.28 if not Game.fast else 0.02).timeout.connect(root.queue_free)


func _spawn_wave(w: Dictionary) -> void:
	var map := get_parent()
	var count := int(w.count)
	var spawned: Array = []
	for i in count:
		var e := Enemy.create(w.enemy, false, tier)
		var a := TAU * i / count + done
		var p: Vector3 = global_position + Vector3(cos(a), 0, sin(a)) * 6.0
		if map and map.has_method("open_spot"):
			p = map.open_spot(global_position, a, 6.0)
		map.add_child(e)
		e.global_position = p + Vector3.UP * 0.1
		Fx.burst(map, p + Vector3.UP, Color(0.6, 0.7, 1.0), 40, 4.0)
		enemies.append(e)
		spawned.append(e)
	_light.light_energy = 6.0
	Audio.sfx("thunder", -3.0, 0.6)
	_phase = "wave"
	wave_spawned.emit(spawned)


func _finish() -> void:
	running = false
	finished = true
	_phase = ""
	_clear_rings()
	survived.emit()


func _fail(refill := true) -> void:
	running = false
	_phase = ""
	_clear_rings()
	_clear_wave()
	done = 0
	_wave_i = 0
	if refill and is_instance_valid(player) and player.has_method("refill"):
		player.refill()
	failed.emit()


func _on_player_died() -> void:
	if running:
		_fail(false)     # the game revives the player at the arrival point


func _clear_rings() -> void:
	for r in _rings:
		if is_instance_valid(r):
			r.queue_free()
	_rings.clear()


func _clear_wave() -> void:
	for e in enemies:
		if is_instance_valid(e):
			e.queue_free()
	enemies.clear()


func _exit_tree() -> void:
	_clear_wave()

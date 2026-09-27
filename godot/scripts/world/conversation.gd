extends Node
## Stages a conversation on the map: who takes part, who faces whom, who
## gestures, and the camera. Every line cuts to an over-the-shoulder shot of
## the listener looking at the speaker (keeping to one side of the pair's axis,
## so reverse shots read naturally); the speaker plays a talk gesture and turns
## to whoever they address (the player, or the NPC whose line they answer),
## everyone else turns to the speaker. end() hands the gameplay camera back.

const HEAD := 1.58
const OTS_BACK := 1.15
const OTS_SIDE := 0.62
const OTS_UP := 0.16
## NPC speakers farther than this from the player are not pulled into the scene
const JOIN_RADIUS := 16.0

var game: Node
var active := false
var cam: Camera3D
var members: Dictionary = {}       ## id -> Node3D ("player" or an npc id)
var main_id := ""
var speaker := ""
var _last_npc := ""
var _prev := ""
var _from := Vector3.ZERO
var _look := Vector3.ZERO
var _t := 0.0
var _cam_on := false


func _ready() -> void:
	cam = Camera3D.new()
	cam.name = "ConversationCamera"
	cam.fov = 48.0
	cam.near = 0.1
	cam.far = 1500.0
	add_child(cam)


## Gather the participants: the player, the NPC spoken to and the NPCs present
## for this objective (the story's `with`).
func begin(main: Node3D, party: Array) -> void:
	active = true
	members.clear()
	members["player"] = game.player
	main_id = ""
	if main and is_instance_valid(main):
		members[main.npc_id] = main
		main_id = main.npc_id
	for n in party:
		# the objective's group, when it is here (not a bark on the other side of the map)
		if n and is_instance_valid(n) and n.global_position.distance_to(game.player.global_position) < JOIN_RADIUS:
			members[n.npc_id] = n
	_last_npc = main_id
	speaker = ""
	_prev = ""
	_cam_on = false
	var c := centre()
	for id in members:
		_turn(id, c)
		if id != "player":
			members[id].hide_plate = true


func set_main(main: Node3D) -> void:
	if main and is_instance_valid(main):
		members[main.npc_id] = main
		main_id = main.npc_id
		main.hide_plate = true
		if _last_npc == "":
			_last_npc = main_id


func end() -> void:
	if not active:
		return
	active = false
	for id in members:
		var n = members[id]
		if id != "player" and is_instance_valid(n):
			n.set_talking(false)
			n.hide_plate = false
	var p = game.player
	if is_instance_valid(p):
		p.release_pose()
		if _cam_on and p.camera:
			p.camera.make_current()
	_cam_on = false
	members.clear()


## Centre of the group on the ground.
func centre() -> Vector3:
	var sum := Vector3.ZERO
	var k := 0
	for id in members:
		var n = members[id]
		if is_instance_valid(n):
			sum += n.global_position
			k += 1
	return sum / maxf(k, 1)


func _node(id: String) -> Node3D:
	var n = members.get(id)
	return n if n and is_instance_valid(n) else null


func _npc_ids() -> Array:
	return members.keys().filter(func(id): return id != "player" and _node(id) != null)


func _head(n: Node3D) -> Vector3:
	var s := 1.0
	if "data" in n:
		s = float(n.data.get("scale", 1.0))
	return n.global_position + Vector3.UP * HEAD * s


func _turn(id: String, point: Vector3) -> void:
	var n := _node(id)
	if n == null:
		return
	if id == "player":
		n.face_toward(point)
	else:
		n.face(point)


## A line begins: gestures, facing and the shot.
func on_line(who: String) -> void:
	if not active:
		return
	if who != "narrator" and who != "player" and not members.has(who):
		var n: Node3D = game.find_npc(who)
		if n and n.global_position.distance_to(game.player.global_position) < JOIN_RADIUS:
			members[who] = n
			n.hide_plate = true
	_prev = speaker
	speaker = who
	var s := _node(who)
	var listener := _listener_for(who)
	var l := _node(listener)
	for id in members:
		var n := _node(id)
		if n == null:
			continue
		var talking: bool = id == who
		if id == "player":
			var moves = n.moves
			n.hold_pose(moves.talk_anim(talking) if moves else ("talk" if talking else "idle"))
		else:
			n.set_talking(talking)
		if talking and l:
			_turn(id, l.global_position)
		elif s and not talking:
			_turn(id, s.global_position)
	if s and who != "player":
		_last_npc = who
	if s == null:
		# the narrator (or someone not on the map): hold the shot, or open on the group
		if not _cam_on and _npc_ids().size() > 0:
			_wide_shot()
		return
	_shot(s, l, who, listener)


## Whom a line is addressed to: an NPC answers the NPC who spoke just before
## (when that was someone else), otherwise speaks to the player; the player
## answers the last NPC who spoke (or the one they came to talk to).
func _listener_for(who: String) -> String:
	if who == "player":
		if _node(_last_npc):
			return _last_npc
		if _node(main_id):
			return main_id
		var ids := _npc_ids()
		return ids[0] if not ids.is_empty() else ""
	if _prev != "" and _prev != who and _prev != "narrator" and _prev != "player" and _node(_prev):
		return _prev
	return "player" if _node("player") else ""


func _shot(s: Node3D, l: Node3D, sid: String, lid: String) -> void:
	var sh := _head(s)
	var from: Vector3
	var look: Vector3
	if l == null or l == s:
		# talking to themselves: a frontal medium shot
		var f: Vector3 = s.facing() if s.has_method("facing") else s.global_basis.z
		f.y = 0.0
		f = f.normalized() if f.length() > 0.01 else Vector3.FORWARD
		var r := f.cross(Vector3.UP).normalized()
		from = sh + f * 2.1 + r * 0.35 + Vector3.UP * 0.05
		look = sh - Vector3.UP * 0.12
	else:
		var lh := _head(l)
		var d := sh - lh
		d.y = 0.0
		if d.length() < 0.2:
			d = -l.global_basis.z
			d.y = 0.0
		d = d.normalized()
		var right := d.cross(Vector3.UP).normalized()
		# the same side of the pair's axis for both reverse shots (the 180 degree rule)
		var side := 1.0 if sid < lid else -1.0
		look = sh.lerp(lh, 0.1) - Vector3.UP * 0.1
		# candidates: over the listener's shoulder, the other shoulder, a higher and
		# wider angle, and a frontal single of the speaker; the first one that sees
		# the speaker past walls and the other people wins
		var cands: Array[Vector3] = [
			lh - d * OTS_BACK + right * side * OTS_SIDE + Vector3.UP * OTS_UP,
			lh - d * OTS_BACK - right * side * OTS_SIDE + Vector3.UP * OTS_UP,
			lh - d * (OTS_BACK + 0.7) + right * side * (OTS_SIDE + 0.5) + Vector3.UP * 0.75,
			sh - d * 1.3 + right * side * 1.2 + Vector3.UP * 0.05,
		]
		from = cands[0]
		var best := -1.0
		for c in cands:
			var clear := _unblock(look, c)
			var score := clear.distance_to(look) / c.distance_to(look)
			if _occluded(clear, sh, [s, l]):
				score -= 1.0
			if score > best + 0.001:
				best = score
				from = clear
			if score > 0.95:
				break
	from = _unblock(look, from)
	_set_cam(from, look)


## Is anyone (but `skip`) standing between the camera and the speaker's head?
func _occluded(cam_pos: Vector3, target: Vector3, skip: Array) -> bool:
	for id in members:
		var n := _node(id)
		if n == null or skip.has(n):
			continue
		var seg := target - cam_pos
		var len2 := seg.length_squared()
		if len2 < 0.01:
			continue
		for h in [1.0, 1.5]:
			var q: Vector3 = n.global_position + Vector3.UP * h
			var t := clampf((q - cam_pos).dot(seg) / len2, 0.0, 1.0)
			if t > 0.05 and t < 0.95 and q.distance_to(cam_pos + seg * t) < 0.3:
				return true
	return false


## An establishing shot of the whole group from behind the player.
func _wide_shot() -> void:
	var p: Node3D = game.player
	var c := centre()
	var to := c - p.global_position
	to.y = 0.0
	if to.length() < 0.3:
		to = p.facing()
	to = to.normalized()
	var right := to.cross(Vector3.UP).normalized()
	var look := c + Vector3.UP * 1.3
	var from := p.global_position + Vector3.UP * 2.2 - to * 2.6 + right * 0.8
	_set_cam(_unblock(look, from), look)


## Pull a camera position in front of any wall between it and what it frames.
func _unblock(look: Vector3, from: Vector3) -> Vector3:
	var space: PhysicsDirectSpaceState3D = game.player.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(look, from, 1, [game.player.get_rid()])
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return from
	var dir := (from - look).normalized()
	return (hit.position as Vector3) - dir * 0.2


func _set_cam(from: Vector3, look: Vector3) -> void:
	_from = from
	_look = look
	_t = 0.0
	cam.global_position = from
	if from.distance_to(look) > 0.05:
		cam.look_at(look, Vector3.UP)
	if not _cam_on:
		_cam_on = true
		cam.make_current()


func _process(delta: float) -> void:
	if not active or not _cam_on:
		return
	# a slow push-in keeps a held shot alive
	_t += delta
	var k := minf(_t * 0.015, 0.08)
	cam.global_position = _from.lerp(_look, k)

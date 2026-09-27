extends RefCounted
## Stair and curb handling for the CharacterBody3D walkers (player, enemies).
##
## A capsule sliding with move_and_slide() stops dead against any vertical
## riser taller than a few centimetres (the bottom hemisphere's contact normal
## is too steep to count as floor), so stairs, hall terraces, curbs and
## platform lips needed a jump. step_up() runs before move_and_slide(): when
## this frame's planar motion is blocked by a steep face, it tests whether the
## capsule, lifted by at most `max_step`, can move on and then set down on
## walkable ground; if so the body is raised by exactly the height of that
## ground and move_and_slide() carries it forward over the edge. Walking back
## down is handled by the bodies' floor_snap_length (>= MAX_STEP), which keeps
## a grounded body glued to the next step instead of letting it fall.

const MAX_STEP := 0.45
const MIN_STEP := 0.015
## Look this far ahead at least, so a riser is found before the capsule is
## pressed flat against it at low speed.
const MIN_PROBE := 0.1


## Lift `body` onto a step in front of it. Returns the height climbed (0 when
## nothing was done). `grounded` is whether the body counts as standing (the
## caller's is_on_floor(), usually with a little coyote time).
static func step_up(body: CharacterBody3D, delta: float, grounded: bool, max_step := MAX_STEP) -> float:
	if not grounded or body.velocity.y > 0.5:
		return 0.0
	var planar := Vector3(body.velocity.x, 0.0, body.velocity.z)
	var speed := planar.length()
	if speed < 0.05:
		return 0.0
	var ahead := planar / speed * maxf(speed * delta, MIN_PROBE)
	var from := body.global_transform
	var col := KinematicCollision3D.new()
	if not body.test_move(from, ahead, col):
		return 0.0                                 # free path
	var min_floor_y := cos(body.floor_max_angle)
	if col.get_normal().y >= min_floor_y:
		return 0.0                                 # a walkable ramp: move_and_slide climbs it
	# room overhead?
	var up := Vector3.UP * max_step
	if body.test_move(from, up, col):
		up = col.get_travel()
	if up.y < MIN_STEP:
		return 0.0
	var raised := from
	raised.origin += up
	if body.test_move(raised, ahead, col):
		return 0.0                                 # a wall, not a step
	var over := raised
	over.origin += ahead
	if not body.test_move(over, Vector3.DOWN * (up.y + 0.05), col):
		return 0.0                                 # nothing under us there: a drop, not a step
	if col.get_normal().y < min_floor_y:
		return 0.0                                 # would land on something steep
	var rise: float = up.y + col.get_travel().y
	if rise < MIN_STEP or rise > max_step + 0.001:
		return 0.0
	body.global_position.y += rise + 0.002
	return rise


## After move_and_slide: a body that was standing and has just walked off a
## step (or a curb) is set straight down onto whatever is below within
## `max_step`, instead of falling (and playing a fall) down every stair. When
## the capsule comes to rest on the nose of the step it just left, it is given
## a little downward speed so it slides off onto the next tread. Returns the
## (negative) height dropped, 0 when nothing was done.
static func step_down(body: CharacterBody3D, was_floor: bool, max_step := MAX_STEP) -> float:
	if not was_floor or body.is_on_floor() or body.velocity.y > 0.0:
		return 0.0
	var col := KinematicCollision3D.new()
	if not body.test_move(body.global_transform, Vector3.DOWN * (max_step + 0.05), col):
		return 0.0                                 # a real drop: let it fall
	var travel := col.get_travel()
	var walkable := col.get_normal().y >= cos(body.floor_max_angle)
	if travel.y > -0.02:
		# already resting on something (the nose of a step being climbed): leave it be
		if walkable:
			body.apply_floor_snap()
		return 0.0
	body.global_position += travel
	if walkable:
		body.apply_floor_snap()
	else:
		body.velocity.y = minf(body.velocity.y, -2.5)
	return travel.y

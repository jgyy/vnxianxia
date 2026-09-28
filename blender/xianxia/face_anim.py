"""Bakes facial performance into every humanoid action.

For each armature action this adds, in the *same* (slotted) action:

* a shape-key slot animating the face_shapes morphs (blinks, expressions,
  visemes).  An NLA track per action on the shape-key datablock makes the
  glTF exporter merge those weights into the animation of the same name, so
  Godot sees a ``blend_shapes/<key>`` track inside e.g. ``talk``;
* eye-bone rotations (saccades, gaze shifts) on ``eye.L`` / ``eye.R`` with the
  lids following through lid_look_up / lid_look_down;
* for talking clips, small head nods layered onto the existing head keys.

Natural timing: blinks every 2-6 s lasting ~130 ms (4 frames at 30 fps,
closing faster than opening, right eye a hair behind), micro-saccades every
0.4-2.5 s of 1-5 deg with a one-frame jump, a blink riding along larger gaze
shifts; talking at ~6 syllables per second in phrases with pauses, visemes
blended with coarticulation, stressed syllables lifting the brows.
Looping clips start and end on the same face so they loop cleanly.
"""
import math
import random

import numpy as np
from mathutils import Quaternion, Vector

from . import face_rig, face_shapes

FPS = 30.0
BLINK = (0.0, 0.62, 1.0, 0.48, 0.12, 0.0)       # per-frame closure, ~130 ms
BLINK_R = (0.0, 0.5, 0.98, 0.58, 0.18, 0.02)


class Track:
    """Per-frame values of every face channel for one action."""

    def __init__(self, n_frames):
        self.n = n_frames
        self.k = {name: np.zeros(n_frames) for name in face_shapes.ORDER}
        self.yaw = np.zeros(n_frames)
        self.pitch = np.zeros(n_frames)
        self.nod = np.zeros(n_frames)          # extra head pitch (deg), talk clips

    def env(self, a, b, attack=6, release=8):
        """0..1 envelope that rises from frame a over `attack` frames and falls to 0 at b."""
        f = np.arange(self.n, dtype=np.float64)
        up = np.clip((f - a) / max(attack, 1), 0, 1)
        down = np.clip((b - f) / max(release, 1), 0, 1)
        e = np.minimum(up, down)
        return e * e * (3 - 2 * e)

    def add(self, key, values):
        self.k[key] = np.maximum(self.k[key], values) if key.startswith(("blink", "squint")) else self.k[key] + values

    def hold(self, key, value, a=None, b=None, attack=6, release=8):
        """Hold a key at value between frames a and b (the whole clip, flat, when both are omitted)."""
        if a is None and b is None:
            self.add(key, np.full(self.n, value))
            return
        self.add(key, value * self.env(a or 0, self.n - 1 if b is None else b, attack, release))


# --------------------------------------------------------------------------
# generators
# --------------------------------------------------------------------------
def blinks(tr, rng, every=(2.0, 6.0), loop=True, start=None, closed=None):
    """Spontaneous blinks; `closed` = array of 0..1 already-closed amounts (no blinks while closed)."""
    f = start if start is not None else rng.uniform(0.6, 2.0) * FPS
    end = tr.n - len(BLINK) - (2 if loop else 0)
    while f < end:
        i = int(f)
        if closed is None or closed[min(i, tr.n - 1)] < 0.5:
            amp = rng.uniform(0.96, 1.0)
            lag = rng.random() < 0.5
            for j, (a, b) in enumerate(zip(BLINK, BLINK_R if lag else BLINK)):
                if i + j < tr.n:
                    tr.k["blink_L"][i + j] = max(tr.k["blink_L"][i + j], a * amp)
                    tr.k["blink_R"][i + j] = max(tr.k["blink_R"][i + j], b * amp)
            if rng.random() < 0.12:        # the occasional double blink
                f += len(BLINK) + 3
                continue
        f += rng.uniform(*every) * FPS


def saccades(tr, rng, yaw_amp=4.0, pitch_amp=2.5, every=(0.4, 2.5), bias=(0.0, 0.0), loop=True):
    """Gaze: fixations joined by one-frame jumps, with a blink on the larger shifts."""
    f = 0
    cur = (bias[0], bias[1])
    first = cur
    marks = []
    while f < tr.n:
        dur = int(rng.uniform(*every) * FPS)
        g = f + dur
        tr.yaw[f:g] = cur[0]
        tr.pitch[f:g] = cur[1]
        marks.append(g)
        nxt = (bias[0] + rng.gauss(0, yaw_amp), bias[1] + rng.gauss(0, pitch_amp))
        if loop and g + dur * 0.5 > tr.n:
            nxt = first
        if abs(nxt[0] - cur[0]) > 7.0 and g + 6 < tr.n:
            for j, a in enumerate(BLINK):
                tr.k["blink_L"][g + j] = max(tr.k["blink_L"][g + j], a * 0.85)
                tr.k["blink_R"][g + j] = max(tr.k["blink_R"][g + j], a * 0.85)
        cur = nxt
        f = g
    if loop:
        tr.yaw[-3:] = first[0]
        tr.pitch[-3:] = first[1]
    # a tiny drift during fixations keeps the eyes alive
    t = np.arange(tr.n) / FPS
    tr.yaw += 0.25 * np.sin(t * 2.1 + rng.random() * 6)
    tr.pitch += 0.2 * np.sin(t * 1.7 + rng.random() * 6)


def lids_follow(tr):
    tr.k["lid_look_up"] = np.maximum(tr.k["lid_look_up"], np.clip(tr.pitch / 25.0, 0, 1))
    tr.k["lid_look_down"] = np.maximum(tr.k["lid_look_down"], np.clip(-tr.pitch / 25.0, 0, 1))


VOWELS = (("viseme_AA", 0.55, 0.9), ("viseme_EE", 0.45, 0.75), ("viseme_OO", 0.45, 0.8), ("viseme_AA", 0.4, 0.7))
CONSONANTS = (("viseme_MM", 0.7, 1.0), ("viseme_FF", 0.55, 0.85), (None, 0, 0), (None, 0, 0))


def speech(tr, rng, a, b, energy=1.0, nods=True):
    """Syllables at ~6/s in phrases; visemes with coarticulation, stress brows and nods."""
    f = a + rng.uniform(4, 10)
    while f < b - 12:
        n_syl = rng.randint(5, 13)
        stress = rng.randrange(n_syl)
        for k in range(n_syl):
            if f >= b - 8:
                break
            length = rng.uniform(4.0, 6.5)
            c = CONSONANTS[rng.randrange(len(CONSONANTS))]
            v = VOWELS[rng.randrange(len(VOWELS))]
            if c[0]:
                _pulse(tr, c[0], f, length * 0.45, rng.uniform(c[1], c[2]))
            amp = rng.uniform(v[1], v[2]) * energy * (1.25 if k == stress else 1.0)
            _pulse(tr, v[0], f + length * 0.45, length * 0.8, min(amp, 1.0))
            if k == stress:
                _pulse(tr, "brow_up", f, 14, 0.35 * energy)
                if nods:
                    _pulse_arr(tr.nod, f + 2, 14, -3.5 * energy)
            f += length
        f += rng.uniform(0.25, 0.8) * FPS           # breath between phrases


def _pulse(tr, key, centre, width, amp):
    _pulse_arr(tr.k[key], centre, width, amp)


def _pulse_arr(arr, centre, width, amp):
    f = np.arange(len(arr), dtype=np.float64)
    x = (f - centre) / max(width, 1.0)
    w = np.where(np.abs(x) < 1, 0.5 + 0.5 * np.cos(np.pi * x), 0.0)
    arr += amp * w


# --------------------------------------------------------------------------
# per-clip performances
# --------------------------------------------------------------------------
def _moment(act_name, n):
    """Frame of the clip's main beat (impact, strike, release) - roughly 40 % in."""
    return int(n * 0.4)


def perform(name, tr, rng, loop):
    n = tr.n
    beat = _moment(name, n)
    closed = None
    has = lambda *ws: any(w in name for w in ws)        # noqa: E731
    if has("meditate", "qi_circulate", "pray", "sleep", "lie_down", "mudra"):
        if has("enter"):
            e = tr.env(n * 0.35, n + 20, attack=int(n * 0.4))
        elif has("exit"):
            e = tr.env(-20, n * 0.6, release=int(n * 0.35))
        else:
            e = np.ones(n)
        for k in ("blink_L", "blink_R"):
            tr.k[k] = np.maximum(tr.k[k], 0.97 * e)
        tr.add("smile", 0.12 * e)
        tr.add("brow_inner_up", 0.06 * e)
        closed = e
        if has("mudra"):
            tr.k["blink_L"] *= 0.0
            tr.k["blink_R"] *= 0.0
            tr.hold("brow_down", 0.35)
            closed = None
    elif has("death", "knockdown"):
        e = tr.env(beat, n + 30, attack=int(n * 0.45))
        tr.hold("squint_L", 0.9, 0, beat + 6, 2, 8)
        tr.hold("squint_R", 0.9, 0, beat + 6, 2, 8)
        tr.hold("brow_down", 0.8, 0, beat + 8, 2, 10)
        tr.hold("mouth_stretch", 0.6, 0, beat + 4, 2, 10)
        for k in ("blink_L", "blink_R"):
            tr.k[k] = np.maximum(tr.k[k], (0.93 if k == "blink_L" else 0.9) * e)
        tr.add("jaw_open", 0.22 * e)
        closed = e
        if has("knockdown"):
            closed = e * 0.4
    elif has("revive", "getup", "stand_up"):
        e = 1.0 - tr.env(n * 0.25, n + 30, attack=int(n * 0.35))
        for k in ("blink_L", "blink_R"):
            tr.k[k] = np.maximum(tr.k[k], 0.95 * e)
        tr.hold("brow_down", 0.3, n * 0.3, n * 0.8)
        closed = e
    elif has("hit", "stagger", "landing_hard", "block_hit"):
        a = max(1, beat - int(n * 0.25))
        tr.hold("squint_L", 0.85, a, a + 10, 2, 10)
        tr.hold("squint_R", 0.8, a, a + 10, 2, 10)
        tr.hold("brow_down", 0.75, a, a + 12, 2, 10)
        tr.hold("mouth_stretch", 0.65, a, a + 8, 2, 10)
        tr.hold("sneer_L", 0.3, a, a + 8, 2, 8)
        tr.hold("sneer_R", 0.25, a, a + 8, 2, 8)
        for j, v in enumerate(BLINK):
            if a + j < n:
                tr.k["blink_L"][a + j] = max(tr.k["blink_L"][a + j], v)
                tr.k["blink_R"][a + j] = max(tr.k["blink_R"][a + j], v)
    elif has("attack", "palm", "kick", "sword_", "uppercut", "blast", "charge", "cast", "parry", "dodge",
             "block", "combat", "flying", "roll", "backflip", "slide", "spin", "breakthrough"):
        focus = 0.55 if not has("idle") else 0.35
        tr.hold("brow_down", focus)
        tr.hold("squint_L", 0.3)
        tr.hold("squint_R", 0.3)
        if has("kick", "palm", "uppercut", "attack", "blast", "charge_release", "breakthrough", "spin"):
            tr.hold("viseme_AA", 0.45, beat - 3, beat + 9, 2, 8)                  # kiai
            tr.hold("sneer_L", 0.25, beat - 3, beat + 9, 2, 8)
            tr.hold("sneer_R", 0.25, beat - 3, beat + 9, 2, 8)
        elif has("cast", "charge_hold", "charge_start"):
            tr.hold("viseme_MM", 0.4, 0, beat, 6, 4)
            tr.hold("viseme_AA", 0.25, beat, beat + 12, 3, 8)
    elif has("talk") or has("explain"):
        listen = has("listen")
        if not listen:
            speech(tr, rng, 0, n, energy=1.25 if has("emphatic") else 1.0)
            if has("emphatic"):
                tr.hold("brow_down", 0.25, n * 0.5, n)
        else:
            tr.hold("smile", 0.2)
            for k in range(3):
                _pulse_arr(tr.nod, rng.uniform(0.15, 0.85) * n, 10, -4.0)
    elif has("laugh"):
        tr.hold("smile", 0.95, 0, n - 1, 5, 8)
        tr.hold("squint_L", 0.55, 0, n - 1, 5, 8)
        tr.hold("squint_R", 0.55, 0, n - 1, 5, 8)
        f = 6.0
        while f < n - 8:
            _pulse(tr, "viseme_AA", f, 4.5, 0.55)
            f += rng.uniform(6.5, 8.5)
        tr.pitch += 6.0 * tr.env(0, n)
    elif has("cry", "sigh"):
        tr.hold("brow_inner_up", 0.85 if has("cry") else 0.45)
        tr.hold("frown", 0.7 if has("cry") else 0.3)
        tr.hold("squint_L", 0.45 if has("cry") else 0.15)
        tr.hold("squint_R", 0.45 if has("cry") else 0.15)
        tr.pitch -= 10.0 * tr.env(0, n)
        if has("sigh"):
            tr.hold("viseme_OO", 0.35, n * 0.4, n * 0.8)
    elif has("surprised"):
        tr.hold("brow_up", 1.0, 2, n, 3, 12)
        tr.hold("eyes_wide", 0.8, 2, n, 3, 12)
        tr.hold("jaw_open", 0.4, 3, n, 3, 12)
    elif has("angry"):
        tr.hold("brow_down", 1.0, 0, n - 1, 4, 8)
        tr.hold("sneer_L", 0.55, 0, n - 1, 4, 8)
        tr.hold("sneer_R", 0.45, 0, n - 1, 4, 8)
        tr.hold("frown", 0.35, 0, n - 1, 4, 8)
        tr.hold("viseme_EE", 0.3, beat - 4, beat + 10, 3, 6)                     # bared teeth
    elif has("yawn"):
        tr.hold("jaw_open", 1.0, n * 0.15, n * 0.75, int(n * 0.25), int(n * 0.2))
        tr.hold("squint_L", 0.8, n * 0.15, n * 0.75, int(n * 0.25), int(n * 0.2))
        tr.hold("squint_R", 0.8, n * 0.15, n * 0.75, int(n * 0.25), int(n * 0.2))
        tr.hold("brow_up", 0.4, n * 0.15, n * 0.75, int(n * 0.25), int(n * 0.2))
    elif has("facepalm", "shake_head"):
        tr.hold("frown", 0.45)
        tr.hold("brow_inner_up", 0.4)
        if has("facepalm"):
            closed = tr.env(n * 0.3, n * 0.8, 5, 8)
            tr.k["blink_L"] = np.maximum(tr.k["blink_L"], 0.9 * closed)
            tr.k["blink_R"] = np.maximum(tr.k["blink_R"], 0.9 * closed)
    elif has("bashful"):
        tr.hold("smile", 0.5)
        tr.pitch -= 12.0 * tr.env(0, n, 8, 8)
        tr.yaw += 8.0 * tr.env(0, n, 8, 8)
    elif has("thinking"):
        tr.hold("brow_inner_up", 0.3)
        tr.hold("brow_down", 0.2)
        tr.hold("viseme_MM", 0.35)
        tr.pitch += 9.0 * tr.env(8, n - 4, 6, 6)
        tr.yaw += 12.0 * tr.env(8, n - 4, 6, 6)
    elif has("victory", "cheer"):
        tr.hold("smile", 0.9)
        tr.hold("brow_up", 0.35)
        tr.hold("viseme_AA", 0.5, beat - 6, beat + 16, 4, 8)
    elif has("salute", "bow", "wave", "beckon", "clap", "give_item", "nod", "point", "dance", "shrug"):
        smile = 0.55 if has("salute", "bow", "wave", "clap", "dance") else 0.35
        tr.hold("smile", smile, n * 0.1, n * 0.95, int(n * 0.2), int(n * 0.15))
        if has("bow", "salute"):
            tr.pitch -= 8.0 * tr.env(n * 0.3, n * 0.7, 6, 6)
            for j, v in enumerate(BLINK):
                i = int(n * 0.45) + j
                if i < n:
                    tr.k["blink_L"][i] = max(tr.k["blink_L"][i], v)
                    tr.k["blink_R"][i] = max(tr.k["blink_R"][i], v)
        if has("shrug"):
            tr.hold("brow_up", 0.5)
            tr.hold("frown", 0.3)
    elif has("play_flute"):
        tr.hold("viseme_OO", 0.6)
        tr.hold("viseme_MM", 0.3)
        tr.pitch -= 8.0 * tr.env(0, n)
    elif has("drink", "eat"):
        f = n * 0.45
        while f < n - 6:
            _pulse(tr, "viseme_MM", f, 4, 0.6)
            _pulse(tr, "jaw_open", f + 3, 4, 0.2)
            f += 8
    elif has("read", "write", "guqin", "sweep_floor"):
        tr.pitch -= 14.0 * tr.env(0, n)
        tr.hold("brow_down", 0.18)
    elif has("look_around", "idle_look", "turn"):
        pass
    elif has("run", "sprint", "climb", "jump", "fall", "glide", "ledge"):
        tr.hold("squint_L", 0.18)
        tr.hold("squint_R", 0.18)
        if has("run", "sprint", "climb"):
            t = np.arange(n)
            tr.k["jaw_open"] += 0.1 + 0.06 * np.sin(2 * np.pi * t / max(n, 1) * 2)
    return closed


def face_track(name, n, loop, seed):
    rng = random.Random(seed)
    tr = Track(n)
    closed = perform(name, tr, rng, loop)
    look = any(w in name for w in ("look_around", "idle_look"))
    saccades(tr, rng, yaw_amp=14.0 if look else 4.0, pitch_amp=4.0 if look else 2.5,
             every=(0.5, 1.4) if look else (0.4, 2.5), loop=loop)
    if closed is None or closed.max() < 0.95:
        blinks(tr, rng, every=(2.0, 4.5) if "talk" in name else (2.0, 6.0), loop=loop, closed=closed)
    lids_follow(tr)
    for key in tr.k:
        tr.k[key] = np.clip(tr.k[key], 0.0, 1.0)
    if loop:
        for arr in list(tr.k.values()) + [tr.yaw, tr.pitch, tr.nod]:
            arr[-1] = arr[0]
    return tr


# --------------------------------------------------------------------------
# writing into the actions
# --------------------------------------------------------------------------
def _frame_range(act):
    lo, hi = act.frame_range
    return int(round(lo)), int(round(hi))


def _is_loop(act, arm):
    """A clip loops when every armature channel ends where it started."""
    lo, hi = _frame_range(act)
    for fc in _fcurves(act, arm):
        if abs(fc.evaluate(lo) - fc.evaluate(hi)) > 1e-3:
            return False
    return True


def _fcurves(act, owner):
    slot = owner.animation_data.action_slot if owner.animation_data else None
    for layer in act.layers:
        for strip in layer.strips:
            bag = strip.channelbag(slot) if slot else None
            if bag:
                yield from bag.fcurves


def _write_curve(act, owner, path, index, frames, values, group):
    fc = act.fcurve_ensure_for_datablock(owner, path, index=index, group_name=group)
    kp = fc.keyframe_points
    kp.clear()              # a clip baker may already have keyed the eye bones at rest
    # keep only the keys needed to reproduce the curve linearly (within 0.004)
    keep = [0]
    for i in range(1, len(values) - 1):
        a, b = keep[-1], i + 1
        t = (i - a) / (b - a)
        if abs(values[a] + (values[b] - values[a]) * t - values[i]) > 0.004 or values[i] in (0.0, 1.0) and \
                values[i] != values[i - 1]:
            keep.append(i)
    keep.append(len(values) - 1)
    kp.add(len(keep))
    co = []
    for i in keep:
        co += [float(frames[i]), float(values[i])]
    kp.foreach_set("co", co)
    for k in kp:
        k.interpolation = "LINEAR"
    fc.update()


def bake(arm, fh, actions, seed=0):
    """Add face keys, eye gaze and talk nods to every action; set up the shape-key NLA tracks."""
    key = fh.obj.data.shape_keys
    key.animation_data_create()
    keep = arm.animation_data.action
    head_bone = arm.data.bones["head"]
    r_head = head_bone.matrix_local.to_quaternion()
    nod_axis = r_head.inverted() @ Vector((1.0, 0.0, 0.0))
    for n_act, act in enumerate(actions):
        arm.animation_data.action = act
        lo, hi = _frame_range(act)
        n = hi - lo + 1
        loop = _is_loop(act, arm)
        tr = face_track(act.name, n, loop, seed * 1000 + n_act)
        frames = np.arange(lo, hi + 1)
        # eyes
        for bone, sgn in (("eye.L", 1.0), ("eye.R", 1.0)):
            pb = arm.pose.bones[bone]
            pb.rotation_mode = "QUATERNION"
            qs = [face_rig.eye_rotation(arm, bone, tr.yaw[i] * sgn, tr.pitch[i]) for i in range(n)]
            for c in range(4):
                _write_curve(act, arm, f'pose.bones["{bone}"].rotation_quaternion', c, frames,
                             np.array([q[c] for q in qs]), bone)
        # head nods on top of the existing head keys
        if np.abs(tr.nod).max() > 0.01:
            _nod(act, arm, nod_axis, lo, tr.nod)
        # shape keys in a KEY slot of the same action
        slot = act.slots.new(id_type="KEY", name="Face")
        key.animation_data.action = act
        key.animation_data.action_slot = slot
        for name in face_shapes.ORDER:
            vals = tr.k[name]
            if vals.max() <= 1e-4:
                continue
            _write_curve(act, key, f'key_blocks["{name}"].value', 0, frames, vals, "Face")
    key.animation_data.action = None
    for act in actions:
        slot = next(s for s in act.slots if s.target_id_type == "KEY")
        track = key.animation_data.nla_tracks.new()
        track.name = act.name
        lo, _ = _frame_range(act)
        strip = track.strips.new(act.name, lo, act)
        strip.action_slot = slot
        track.mute = False
    arm.animation_data.action = keep


def _nod(act, arm, axis, lo, nod):
    """Compose a pitch nod (deg per frame) onto the head bone's quaternion keys."""
    curves = {}
    for fc in _fcurves(act, arm):
        if fc.data_path == 'pose.bones["head"].rotation_quaternion':
            curves[fc.array_index] = fc
    if len(curves) != 4:
        return
    frames = sorted({int(round(k.co[0])) for k in curves[0].keyframe_points})
    new = {}
    for f in frames:
        q = Quaternion([curves[c].evaluate(f) for c in range(4)])
        i = min(max(f - lo, 0), len(nod) - 1)
        new[f] = q @ Quaternion(axis, math.radians(nod[i]))
    # denser keys where the nod moves
    for f in range(lo, lo + len(nod), 2):
        if f not in new:
            q = Quaternion([curves[c].evaluate(f) for c in range(4)])
            new[f] = q @ Quaternion(axis, math.radians(nod[f - lo]))
    for c in range(4):
        kp = curves[c].keyframe_points
        kp.clear()
        items = sorted(new.items())
        kp.add(len(items))
        co = []
        for f, q in items:
            co += [float(f), q[c]]
        kp.foreach_set("co", co)
        for k in kp:
            k.interpolation = "BEZIER"
            k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
        curves[c].update()

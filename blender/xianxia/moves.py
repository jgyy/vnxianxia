"""The protagonists' extended move set: 100+ keyframed actions on the shared rig.

Called from ``characters.build_character`` for the player configs
(``cultivator_*``) through ``build_player_actions(arm, J, cfg, s)``.

How the animation is authored
-----------------------------
Every action is a :class:`Clip`: a handful of *key poses* at chosen frames.
A pose is a flat dict of readable controls (all numeric, so they interpolate):

* ``root``  (x, f, z)   hips offset in metres (x = character's left, f = forward)
* ``hips spine chest neck head`` (pitch, yaw, roll) degrees, relative to the
  parent: pitch + bends forward, yaw + turns to the character's left, roll +
  tilts the top toward the character's left.
* ``sh_L``  (raise, forward) clavicle shrug / protraction.
* ``hand_L`` (x, f, z)  wrist target, x measured *outward* from the midline, in
  rest-pose coordinates carried by the chest (``hs_L`` = 1 pins it to the
  ground frame instead).  Arms are solved with analytic two-bone IK and an
  elbow pole ``elb_L`` (x outward, f, z) in chest space.
* ``wr_L`` (flex, deviation, twist) wrist relative to the forearm, or an
  absolute hand frame ``hdir_L`` / ``palm_L`` (chest space) blended in by ``hw_L``.
* ``foot_L`` (x outward, f, z) offset of the ball of the foot from rest in the
  ground frame, ``fp_L`` foot pitch (+ heel up: pivots on the ball; - toes up:
  pivots on the heel), ``fyaw_L`` toe-out, ``toe_L`` extra toe bend, ``tc_L``
  toe contact (1 keeps the toes flat on the floor), ``knee_L`` knee pole
  (x outward, f, z) in hips space.  Legs are two-bone IK so planted feet stay
  planted however the body moves.
* ``fg_L`` finger pose: a preset name (see ``HAND``) or 15 flexion values.

A key given without the ``_L``/``_R`` suffix sets both sides (mirrored).
Each key only lists what changes; controls hold their previous value.

Between keys every control follows a monotone cardinal spline (no overshoot
on holds, so contacts stay exact; ``ease`` per key flattens the tangents),
loops wrap their tangents so they cycle seamlessly, and bone groups are
sampled with small time offsets (hips lead, chest/arms/fingers trail, the
head anticipates) for overlapping action.  Poses are baked every other frame
as Bezier keys on the core body and finger bones only (hair / cloth chains
are left to physics).
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from . import anatomy

V = Vector
R = math.radians
AX, AY, AZ = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))

TORSO = ("hips", "spine", "chest", "neck", "head")
LIMB = ("shoulder", "upper_arm", "forearm", "hand", "thigh", "shin", "foot", "toe")
FINGER_NAMES = tuple(anatomy.FINGERS) + ("thumb",)


def qa(axis, deg):
    return Quaternion(V(axis).normalized(), R(deg))


def eul(p, y, r):
    """(pitch, yaw, roll) in degrees -> delta rotation (world axes)."""
    return qa(AZ, y) @ qa(AX, p) @ qa(AY, r)


def frame(a, n):
    x = a.normalized()
    y = n - x * n.dot(x)
    if y.length < 1e-6:
        y = x.orthogonal()
    y.normalize()
    return Matrix((x, y, x.cross(y))).transposed()


def frame_rot(a1, n1, a0, n0):
    return (frame(a1, n1) @ frame(a0, n0).transposed()).to_quaternion()


def perp(v, axis):
    a = axis.normalized()
    return v - a * v.dot(a)


def two_bone(root, target, l1, l2, pole):
    d = target - root
    dist = max(min(d.length, (l1 + l2) * 0.9995), abs(l1 - l2) + 1e-4)
    d = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    pd = perp(pole - root, d)
    if pd.length < 1e-6:
        pd = d.orthogonal()
    return root + d * a + pd.normalized() * h


def twist_angle(q, axis):
    """Signed twist (radians) of q about axis (swing-twist decomposition)."""
    a = axis.normalized()
    p = V((q.x, q.y, q.z)).dot(a)
    return 2.0 * math.atan2(p, q.w)


# --------------------------------------------------------------------------
# finger presets: per finger (knuckle, middle, tip) flexion in degrees, on
# top of the modelled rest curl.  Order: index middle ring pinky thumb.
# --------------------------------------------------------------------------
def _h(i, m, r, p, t):
    return tuple(v for f in (i, m, r, p, t) for v in f)


HAND = {
    "relaxed": _h((6, 10, 6), (8, 12, 7), (10, 13, 8), (12, 14, 9), (0, 6, 6)),
    "soft": _h((14, 18, 10), (18, 22, 12), (22, 24, 13), (26, 26, 14), (6, 10, 8)),
    "open": _h((-8, -10, -6), (-8, -10, -6), (-8, -10, -6), (-6, -10, -6), (-6, -8, -6)),
    "flat": _h((-4, -6, -4), (-4, -6, -4), (-4, -6, -4), (-4, -6, -4), (-14, -4, -2)),
    "palm": _h((-6, -8, -4), (-8, -8, -4), (-6, -8, -4), (-4, -6, -4), (-18, -6, -4)),
    "fist": _h((78, 95, 55), (80, 95, 55), (82, 95, 55), (84, 95, 55), (20, 35, 30)),
    "loose_fist": _h((50, 60, 35), (54, 62, 36), (58, 64, 38), (62, 66, 40), (12, 22, 20)),
    "grip": _h((60, 60, 30), (64, 62, 32), (68, 64, 34), (72, 66, 36), (26, 24, 16)),
    "seal": _h((-6, -8, -4), (-6, -8, -4), (78, 95, 55), (78, 95, 55), (30, 40, 30)),
    "point": _h((-4, -6, -4), (76, 92, 55), (80, 94, 55), (82, 95, 55), (22, 30, 24)),
    "cup": _h((30, 25, 12), (30, 25, 12), (30, 25, 12), (30, 25, 12), (8, 10, 8)),
    "mudra": _h((40, 50, 30), (12, 12, 6), (14, 14, 8), (16, 16, 10), (18, 22, 18)),
    "claw": _h((30, 60, 50), (30, 60, 50), (30, 60, 50), (30, 60, 50), (10, 30, 30)),
    "pinch": _h((30, 40, 22), (22, 28, 14), (30, 36, 20), (36, 40, 22), (18, 26, 24)),
    "orchid": _h((6, 4, 0), (38, 48, 20), (4, 2, 0), (-6, -10, -6), (24, 32, 26)),
    "thumb_up": _h((82, 95, 55), (84, 95, 55), (84, 95, 55), (84, 95, 55), (-12, -10, -8)),
    "hold": _h((40, 38, 20), (44, 40, 22), (48, 42, 24), (52, 44, 26), (20, 18, 12)),
    "spread": _h((-10, -12, -8), (-8, -12, -8), (-10, -12, -8), (-12, -12, -8), (-20, -10, -6)),
}


def fingers(v):
    if isinstance(v, str):
        return HAND[v]
    return tuple(v)


def blend_hand(a, b, t):
    a, b = fingers(a), fingers(b)
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# --------------------------------------------------------------------------
# default standing pose (outward x, forward f, up z; metres unscaled)
# --------------------------------------------------------------------------
BASE = {
    "root": (0.0, 0.0, -0.014),
    "hips": (0.0, 0.0, 0.0), "spine": (0.0, 0.0, 0.0), "chest": (0.0, 0.0, 0.0),
    "neck": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0),
}
for _s in ("L", "R"):
    BASE.update({
        f"sh_{_s}": (0.0, 0.0),
        f"hand_{_s}": (0.235, 0.03, 0.925), f"hs_{_s}": 0.0, f"elb_{_s}": (0.5, -0.8, -0.25),
        f"wr_{_s}": (6.0, 0.0, 0.0), f"hw_{_s}": 0.0,
        f"hdir_{_s}": (0.0, 0.0, -1.0), f"palm_{_s}": (-1.0, 0.0, 0.0),
        f"foot_{_s}": (0.0, 0.0, 0.0), f"fp_{_s}": 0.0, f"fyaw_{_s}": 6.0, f"toe_{_s}": 0.0,
        f"tc_{_s}": 1.0, f"knee_{_s}": (0.12, 1.0, 0.0), f"fs_{_s}": 0.0,
        f"fg_{_s}": HAND["relaxed"],
    })
SIDED = {k[:-2] for k in BASE if k.endswith(("_L", "_R"))}
TRIPLE_SIGNED = set(TORSO) | {"root"}

# time offsets (frames) per control, scaled by the clip's `lag`
LAG = {"spine": -0.7, "chest": -1.4, "neck": 0.6, "head": 1.6, "sh": -1.6, "hand": -1.0, "elb": -1.0,
       "wr": -2.0, "hdir": -1.6, "palm": -1.6, "fg": -2.4, "hs": -1.0, "hw": -1.6}


def expand(changes):
    """Keyword controls -> sided controls (keys without a side set both)."""
    out = {}
    for k, v in changes.items():
        if k in SIDED:
            out[k + "_L"] = v
            out[k + "_R"] = v
        else:
            out[k] = v
    for k in list(out):
        if k.startswith("fg_"):
            out[k] = fingers(out[k])
    return out


def mirror_changes(ch):
    out = {}
    for k, v in ch.items():
        if k.endswith("_L"):
            out[k[:-2] + "_R"] = v
        elif k.endswith("_R"):
            out[k[:-2] + "_L"] = v
        elif k == "root":
            out[k] = (-v[0], v[1], v[2])
        elif k in TORSO:
            out[k] = (v[0], -v[1], -v[2])
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------------
# clips
# --------------------------------------------------------------------------
class Clip:
    """Per-control key lists; see the module docstring."""

    def __init__(self, name, length, loop=False, lag=1.0, base=None, extra=None):
        self.name = name
        self.length = length
        self.loop = loop
        self.lag = lag
        self.base = dict(BASE)
        if base:
            self.base.update(expand(base))
        self.pk = {}            # control -> [(frame, value, ease)]
        self.extra = extra      # fn(frame, pose) -> None, procedural layer
        self.events = []

    def _last(self, name, f):
        best = None
        for kf, v, _ in self.pk.get(name, []):
            if kf <= f and (best is None or kf >= best[0]):
                best = (kf, v)
        return best[1] if best else self.base[name]

    def k(self, f, ease=0.0, **changes):
        return self.kd(f, changes, ease)

    def kd(self, f, changes, ease=0.0):
        for n, v in expand(changes).items():
            if n not in self.base:
                raise KeyError(f"{self.name}: unknown control {n}")
            lst = self.pk.setdefault(n, [])
            lst[:] = [x for x in lst if x[0] != f]
            lst.append((f, v, ease))
        return self

    def hold(self, f, ease=0.0, only=None):
        """Key every control at frame f with the value of its latest key."""
        for n in list(self.pk):
            if only and not any(n.startswith(o) for o in only):
                continue
            if any(kf == f for kf, _, _ in self.pk[n]):
                continue
            self.pk[n].append((f, self._last(n, f), ease))
        return self

    def mirrored(self, name):
        c = Clip(name, self.length, self.loop, self.lag)
        c.base = dict(self.base)
        c.base.update(mirror_changes(dict(self.base)))
        for n, lst in self.pk.items():
            for f, v, e in lst:
                for mn, mv in mirror_changes({n: v}).items():
                    c.pk.setdefault(mn, []).append((f, mv, e))
        if self.extra:
            src = self.extra

            def ex(f, P):
                tmp = mirror_changes(P)
                src(f, tmp)
                P.update(mirror_changes(tmp))
            c.extra = ex
        return c

    # ----------------------------------------------------------- evaluation
    def resolve(self):
        self._k = {}
        for n, base in self.base.items():
            lst = sorted(self.pk.get(n, []), key=lambda x: x[0])
            if self.loop:
                lst = [x for x in lst if x[0] < self.length] or [(0, base, 0.0)]
            else:
                if not lst or lst[0][0] > 0:
                    lst.insert(0, (0, base, 0.0))
            self._k[n] = lst

    def _tangent(self, lst, i, comp):
        n = len(lst)
        f, v, ease = lst[i]
        if ease >= 1.0:
            return 0.0
        if self.loop:
            fp, vp = (lst[i - 1][0], lst[i - 1][1]) if i > 0 else (lst[-1][0] - self.length, lst[-1][1])
            fn, vn = (lst[i + 1][0], lst[i + 1][1]) if i < n - 1 else (lst[0][0] + self.length, lst[0][1])
        else:
            if i == 0 or i == n - 1:
                return 0.0
            fp, vp = lst[i - 1][0], lst[i - 1][1]
            fn, vn = lst[i + 1][0], lst[i + 1][1]
        v, vp, vn = _c(v, comp), _c(vp, comp), _c(vn, comp)
        d0 = (v - vp) / max(f - fp, 1e-6)
        d1 = (vn - v) / max(fn - f, 1e-6)
        if d0 * d1 <= 0.0:
            return 0.0                      # extremum / hold: flat, no overshoot
        m = (vn - vp) / max(fn - fp, 1e-6)
        m = math.copysign(min(abs(m), 3 * abs(d0), 3 * abs(d1)), m)
        return m * (1.0 - ease)

    def value(self, name, t):
        lst = self._k[name]
        n = len(lst)
        if n == 1:
            return lst[0][1]
        if self.loop:
            t = t % self.length
            if t < lst[0][0]:
                t += self.length
            i = n - 1
            for j in range(n - 1):
                if lst[j][0] <= t < lst[j + 1][0]:
                    i = j
                    break
            j = (i + 1) % n
            f0, f1 = lst[i][0], lst[j][0] + (self.length if j == 0 else 0)
        else:
            t = max(0.0, min(float(self.length), t))
            if t >= lst[-1][0]:
                return lst[-1][1]
            i = 0
            while t >= lst[i + 1][0]:
                i += 1
            j = i + 1
            f0, f1 = lst[i][0], lst[j][0]
        h = max(f1 - f0, 1e-6)
        u = max(0.0, min(1.0, (t - f0) / h))
        a, b = lst[i][1], lst[j][1]
        if isinstance(a, (int, float)):
            return _hermite(a, b, self._tangent(lst, i, None) * h, self._tangent(lst, j, None) * h, u)
        return tuple(_hermite(a[c], b[c], self._tangent(lst, i, c) * h, self._tangent(lst, j, c) * h, u)
                     for c in range(len(a)))

    def pose(self, t):
        P = {}
        for name in self.base:
            grp = name[:-2] if name.endswith(("_L", "_R")) else name
            off = LAG.get(grp, 0.0) * self.lag
            P[name] = self.value(name, t + off)
        if self.extra:
            self.extra(t, P)
        return P


def _c(v, comp):
    return v if comp is None else v[comp]


def _hermite(p0, p1, m0, m1, u):
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1


# --------------------------------------------------------------------------
# rig: pose controls -> bone rotations
# --------------------------------------------------------------------------
class Rig:
    def __init__(self, arm, J, cfg, s):
        self.arm = arm
        self.s = s
        self.fem = cfg["female"]
        names = [n for n in J if n in _core_names()]
        self.names = names
        self.J = J
        self.parent = {n: J[n][2] for n in names}
        self.head = {n: J[n][0].copy() for n in names}
        self.tail = {n: J[n][1].copy() for n in names}
        self.rest = {n: arm.data.bones[n].matrix_local.to_quaternion() for n in names}
        L = {}
        for sd in ("L", "R"):
            L[f"ua{sd}"] = (self.head[f"forearm.{sd}"] - self.head[f"upper_arm.{sd}"]).length
            L[f"fa{sd}"] = (self.head[f"hand.{sd}"] - self.head[f"forearm.{sd}"]).length
            L[f"th{sd}"] = (self.head[f"shin.{sd}"] - self.head[f"thigh.{sd}"]).length
            L[f"sh{sd}"] = (self.head[f"foot.{sd}"] - self.head[f"shin.{sd}"]).length
        self.len = L
        # finger flexion axes and rest hand frames
        self.flex = {}
        self.palm0 = {}
        for sd in ("L", "R"):
            wr, ht = self.head[f"hand.{sd}"], self.tail[f"hand.{sd}"]
            hx, hy, hz = anatomy.hand_frame(wr, ht, sd)
            self.palm0[sd] = -hz
            for fname in FINGER_NAMES:
                for i in (1, 2, 3):
                    bn = f"{fname}.{i}.{sd}"
                    if bn not in self.head:
                        continue
                    d = (self.tail[bn] - self.head[bn]).normalized()
                    toward = -hz if fname != "thumb" else (-hz * 0.7 - hx * 0.7).normalized()
                    self.flex[bn] = d.cross(toward).normalized()

    def P(self, v, sd):
        """Outward-x, forward-f, up-z (unscaled) -> armature space."""
        sg = 1 if sd == "L" else -1
        return V((sg * v[0], -v[1], v[2]))

    def solve(self, P):
        s = self.s
        W, pos = {}, {}

        def place(n, q):
            p = self.parent[n]
            W[n] = q
            if p is None:
                rt = P["root"]
                pos[n] = self.head[n] + V((rt[0], -rt[1], rt[2])) * s
            else:
                pos[n] = pos[p] + W[p] @ (self.head[n] - self.head[p])

        place("hips", eul(*P["hips"]))
        for n, p in (("spine", "hips"), ("chest", "spine"), ("neck", "chest"), ("head", "neck")):
            place(n, W[p] @ eul(*P[n]))
        chest_q, chest_h = W["chest"], pos["chest"]

        def chest_pt(v, sd):
            return chest_h + chest_q @ (self.P(v, sd) * s - self.head["chest"])

        for sd in ("L", "R"):
            sg = 1 if sd == "L" else -1
            raise_, fwd = P[f"sh_{sd}"]
            place(f"shoulder.{sd}", chest_q @ (qa(AZ, -sg * fwd) @ qa(AY, -sg * raise_)))
            ua, fa, hd = f"upper_arm.{sd}", f"forearm.{sd}", f"hand.{sd}"
            S = pos[f"shoulder.{sd}"] + W[f"shoulder.{sd}"] @ (self.head[ua] - self.head[f"shoulder.{sd}"])
            hs = P[f"hs_{sd}"]
            T = chest_pt(P[f"hand_{sd}"], sd).lerp(self.P(P[f"hand_{sd}"], sd) * s, hs)
            pole = S + chest_q @ self.P(P[f"elb_{sd}"], sd)
            l1, l2 = self.len[f"ua{sd}"], self.len[f"fa{sd}"]
            el = two_bone(S, T, l1, l2, pole)
            wr = el + (T - el).normalized() * l2
            ua0 = self.head[fa] - self.head[ua]
            fa0 = self.head[hd] - self.head[fa]
            n0 = ua0.cross(V((0, -1, 0))).normalized()
            ua1, fa1 = el - S, wr - el
            b1 = perp(fa1, ua1)
            if b1.length < 0.02 * l2:
                b1 = -perp(pole - S, ua1)
            n1 = ua1.cross(b1).normalized()
            q_ua = frame_rot(ua1, n1, ua0, n0)
            q_fa = frame_rot(fa1, n1, fa0, n0)
            # hand: wrist-relative and/or absolute frame
            flex, dev, tw = P[f"wr_{sd}"]
            palm0 = self.palm0[sd]
            h0 = self.tail[hd] - self.head[hd]
            fax = fa0.normalized()
            q_rel = q_fa @ qa(fax, sg * tw) @ qa(h0.cross(palm0), flex) @ qa(palm0, sg * dev)
            hw = P[f"hw_{sd}"]
            if hw > 1e-4:
                dv, pv = self.P(P[f"hdir_{sd}"], sd), self.P(P[f"palm_{sd}"], sd)
                dirv = (chest_q @ dv).lerp(dv, hs)
                palmv = (chest_q @ pv).lerp(pv, hs)
                q_abs = frame_rot(dirv, palmv, h0, palm0)
                if q_abs.dot(q_rel) < 0:
                    q_abs.negate()
                q_hand = q_rel.slerp(q_abs, min(1.0, hw))
            else:
                q_hand = q_rel
            # spread half of the wrist twist into the forearm (less candy-wrapping)
            rel = q_fa.inverted() @ q_hand
            ang = twist_angle(rel, fax)
            q_fa = q_fa @ Quaternion(fax, 0.5 * ang)
            place(ua, q_ua)
            place(fa, q_fa)
            place(hd, q_hand)
            fg = P[f"fg_{sd}"]
            for fi, fname in enumerate(FINGER_NAMES):
                par = hd
                for i in (1, 2, 3):
                    bn = f"{fname}.{i}.{sd}"
                    if bn not in self.head:
                        continue
                    place(bn, W[par] @ Quaternion(self.flex[bn], R(fg[fi * 3 + i - 1])))
                    par = bn
            # ---- leg
            th, sh, ft, to = f"thigh.{sd}", f"shin.{sd}", f"foot.{sd}", f"toe.{sd}"
            place(th, Quaternion())         # temp to get the hip joint
            H = pos[th]
            A0, B0 = self.head[ft], self.head[to]
            Hl0 = V((A0.x, A0.y + 0.034 * s, 0.004 * s))
            fp = P[f"fp_{sd}"]
            yaw = sg * P[f"fyaw_{sd}"]
            qy = qa(AZ, yaw)
            rf = qy @ qa(AX, fp)
            P0 = B0 if fp >= 0 else Hl0
            off = self.P(P[f"foot_{sd}"], sd) * s
            piv = A0 + off + qy @ (P0 - A0)
            ank = piv + rf @ (A0 - P0)
            fs = P[f"fs_{sd}"]
            if fs > 1e-4:           # foot carried by the hips (airborne / tumbling)
                ank_h = pos["hips"] + W["hips"] @ (ank - self.head["hips"])
                ank = ank.lerp(ank_h, min(1.0, fs))
                rf_h = W["hips"] @ rf
                if rf_h.dot(rf) < 0:
                    rf_h.negate()
                rf = rf.slerp(rf_h, min(1.0, fs))
            kdir = W["hips"] @ self.P(P[f"knee_{sd}"], sd)
            lt, ls = self.len[f"th{sd}"], self.len[f"sh{sd}"]
            kn = two_bone(H, ank, lt, ls, H + kdir)
            an = kn + (ank - kn).normalized() * ls
            t0 = self.head[sh] - self.head[th]
            s0 = self.head[ft] - self.head[sh]
            m0 = t0.cross(V((0, 1, 0))).normalized()
            t1, s1 = kn - H, an - kn
            b1 = perp(s1, t1)
            if b1.length < 0.02 * ls:
                b1 = -perp(kdir, t1)
            m1 = t1.cross(b1).normalized()
            place(th, frame_rot(t1, m1, t0, m0))
            place(sh, frame_rot(s1, m1, s0, m0))
            place(ft, rf)
            tc = P[f"tc_{sd}"]
            place(to, rf @ qa(AX, -fp * tc - P[f"toe_{sd}"]))
        return W, pos

    def local(self, W):
        out = {}
        for n in self.names:
            p = self.parent[n]
            pq = W[p] if p else Quaternion()
            r = self.rest[n]
            out[n] = r.inverted() @ (pq.inverted() @ W[n]) @ r
        return out

    def hips_loc(self, P):
        r = self.rest["hips"]
        return r.inverted() @ (V((P["root"][0], -P["root"][1], P["root"][2])) * self.s)


def _core_names():
    names = set(TORSO)
    for sd in ("L", "R"):
        for b in LIMB:
            names.add(f"{b}.{sd}")
        for fname in FINGER_NAMES:
            for i in (1, 2, 3):
                names.add(f"{fname}.{i}.{sd}")
    return names


# --------------------------------------------------------------------------
# baking
# --------------------------------------------------------------------------
def bake(rig, clip, step=2):
    clip.resolve()
    arm = rig.arm
    act = bpy.data.actions.new(clip.name)
    act.use_fake_user = True
    arm.animation_data.action = act
    frames = list(range(0, clip.length + 1, step))
    if frames[-1] != clip.length:
        frames.append(clip.length)
    rot = {n: [] for n in rig.names}
    loc = []
    prev = {}
    for f in frames:
        P = clip.pose(float(f))
        W, _ = rig.solve(P)
        lq = rig.local(W)
        for n in rig.names:
            q = lq[n]
            if n in prev and prev[n].dot(q) < 0:
                q.negate()
            prev[n] = q
            rot[n].append(q)
        loc.append(rig.hips_loc(P))
    if clip.loop:
        # exact wrap (identical first/last sample)
        for n in rig.names:
            q = rot[n][0].copy()
            if q.dot(rot[n][-2 if len(rot[n]) > 1 else -1]) < 0:
                q.negate()
            rot[n][-1] = q
        loc[-1] = loc[0].copy()
    for n in rig.names:
        pb = arm.pose.bones[n]
        pb.rotation_mode = "QUATERNION"
        path = f'pose.bones["{n}"].rotation_quaternion'
        for i in range(4):
            _write(act, arm, path, i, n, frames, [q[i] for q in rot[n]])
        if n == "hips":
            path = f'pose.bones["{n}"].location'
            for i in range(3):
                _write(act, arm, path, i, n, frames, [v[i] for v in loc])
    return act


def _write(act, arm, path, index, group, frames, values):
    fc = act.fcurve_ensure_for_datablock(arm, path, index=index, group_name=group)
    kp = fc.keyframe_points
    kp.add(len(frames))
    co = []
    for f, v in zip(frames, values):
        co += [f + 1.0, v]
    kp.foreach_set("co", co)
    for k in kp:
        k.interpolation = "BEZIER"
        k.handle_left_type = "AUTO_CLAMPED"
        k.handle_right_type = "AUTO_CLAMPED"
    fc.update()


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def build_player_actions(arm, J, cfg, s):
    """Create the extended protagonist move set on `arm`; returns the actions."""
    rig = Rig(arm, J, cfg, s)
    if arm.animation_data is None:
        arm.animation_data_create()
    keep = arm.animation_data.action
    acts = []
    from . import gait
    for clip in clips(cfg["female"]):
        spec = getattr(clip, "gait", None)
        if spec:
            kind, arms = spec[0], spec[1]
            g = gait.attach(rig, clip, cfg, kind, arms=arms, direction=spec[2] if len(spec) > 2 else None)
            act = gait.bake(rig, clip, g.p["speed"])
            gait.check(arm, act, g)
            acts.append(act)
        else:
            acts.append(bake(rig, clip))
    arm.animation_data.action = keep
    return acts



# ==========================================================================
# the move library
# ==========================================================================
def sm(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def add(P, name, delta):
    v = P[name]
    if isinstance(v, (int, float)):
        P[name] = v + delta
    else:
        P[name] = tuple(a + b for a, b in zip(v, delta))


def gait(T, travel=(0.0, 1.0), stride=0.5, lift=0.07, duty=0.6, strike=-14.0, push=22.0, bob=0.02,
         sway=0.012, toe_first=False, arms=0.0, arm_up=0.0, twist=0.0, width=0.0, knee_lift=0.0):
    """Procedural in-place stepping: feet slide at constant speed during stance
    (so they stay planted relative to the travelling ground), arc through the
    swing, heel-strike / toe-off rolls, pelvis bob, sway and counter-rotation."""
    tx, tf = travel

    def fn(t, P):
        for sd, off in (("L", 0.0), ("R", 0.5)):
            sg = 1 if sd == "L" else -1
            ph = (t / T + off) % 1.0
            if ph < duty:
                u = ph / duty
                k = 0.5 - u
                z = 0.0
                if toe_first:
                    fp = -strike * (1 - sm(u / 0.22)) + push * sm((u - 0.75) / 0.25)
                else:
                    fp = strike * (1 - sm(u / 0.18)) + push * sm((u - 0.72) / 0.28)
            else:
                v = (ph - duty) / (1 - duty)
                k = -0.5 + sm(v)
                z = lift * math.sin(math.pi * min(1.0, v * 1.08)) ** 1.3
                end = -strike if toe_first else strike
                fp = push * (1 - sm(v / 0.45)) + end * sm((v - 0.55) / 0.45)
            xw, f = tx * stride * k, tf * stride * k
            add(P, f"foot_{sd}", (sg * xw + width, f + knee_lift * z, z))
            add(P, f"fp_{sd}", fp)
        c = math.cos(2 * math.pi * t / T)
        add(P, "root", (sway * math.cos(2 * math.pi * (t / T - duty / 2 + 0.1)), 0.0,
                        -bob * (0.5 + 0.5 * math.cos(4 * math.pi * (t / T - 0.08)))))
        if twist:
            add(P, "hips", (0.0, -twist * c, 0.0))
            add(P, "chest", (0.0, twist * 1.3 * c, 0.0))
        if arms:
            for sd, sg in (("L", -1), ("R", 1)):
                a = sg * c
                add(P, f"hand_{sd}", (0.0, arms * a, arm_up * max(0.0, a)))
    return fn


def breath(T, amp=1.0, sway=0.004):
    """Idle breathing layer (chest rise, shoulders, tiny weight sway)."""
    def fn(t, P):
        b = math.sin(2 * math.pi * t / T)
        add(P, "chest", (-1.2 * amp * b, 0.0, 0.0))
        add(P, "spine", (0.6 * amp * b, 0.0, 0.0))
        add(P, "neck", (0.5 * amp * b, 0.0, 0.0))
        add(P, "sh_L", (0.8 * amp * b, 0.0))
        add(P, "sh_R", (0.8 * amp * b, 0.0))
        add(P, "root", (sway * math.sin(2 * math.pi * t / T), 0.0, 0.0))
    return fn


def chain(*fns):
    fns = [f for f in fns if f]

    def fn(t, P):
        for f in fns:
            f(t, P)
    return fn


def tumble(pitch, cz, d=0.22, cf=0.0, x=0.0):
    """Root offset that spins the body about a point `d` up the spine held at
    height cz (somersaults and rolls turn about the tucked body's centre)."""
    a = R(pitch)
    return (x, cf - d * math.sin(a), cz - d * math.cos(a) - 0.98)


def foot_at(x, f):
    """Absolute ball-of-foot position (outward x, forward f) -> foot offset."""
    return (x - 0.095, f - 0.085, 0.0)


def guard(fem):
    g = dict(
        root=(0.0, -0.02, -0.085), hips=(3, -24, 0), spine=(3, 9, 0), chest=(1, 9, 0), neck=(0, 2, 0),
        head=(-3, 4, 0),
        foot_L=(0.03, 0.15, 0.0), fyaw_L=12, foot_R=(0.07, -0.17, 0.0), fyaw_R=40,
        knee_L=(0.3, 1, 0), knee_R=(0.5, 1, 0),
        hand_L=(0.0, 0.36, 1.3), hw_L=1.0, hdir_L=(0.1, 0.3, 1), palm_L=(-0.35, 1, 0), fg_L="palm",
        elb_L=(0.8, -0.2, -1),
        hand_R=(0.05, 0.22, 1.14), hw_R=1.0, hdir_R=(-0.25, 0.45, 1), palm_R=(-0.8, 0.5, 0), fg_R="palm",
        elb_R=(0.6, -0.5, -1), hs_L=0.0, hs_R=0.0, fs_L=0.0, fs_R=0.0, tc_L=1.0, tc_R=1.0)
    if fem:
        g.update(foot_L=(0.01, 0.13, 0.0), foot_R=(0.04, -0.14, 0.0), fg_L="flat", fg_R="flat",
                 hand_L=(0.02, 0.34, 1.32))
    return g


def sword_guard(fem):
    """Jian guard: right hand holds the (imagined) sword forward, left in sword seal."""
    return dict(
        root=(0.0, -0.03, -0.1), hips=(2, -30, 0), spine=(2, 10, 0), chest=(0, 12, 0), neck=(0, 3, 0),
        head=(-2, 5, 0),
        foot_L=(0.02, 0.2, 0.0), fyaw_L=8, foot_R=(0.08, -0.18, 0.0), fyaw_R=55,
        knee_L=(0.2, 1, 0), knee_R=(0.5, 1, 0),
        hand_R=(0.08, 0.36, 1.2), hw_R=1.0, hdir_R=(-0.1, 0.25, 1), palm_R=(-1, 0, 0), fg_R="grip",
        elb_R=(0.6, -0.4, -1),
        hand_L=(0.26, -0.02, 1.52), hw_L=1.0, hdir_L=(0.2, 0.3, 1), palm_L=(0.2, 1, 0), fg_L="seal",
        elb_L=(1, -0.4, 0.2), hs_L=0.0, hs_R=0.0, fs_L=0.0, fs_R=0.0, tc_L=1.0, tc_R=1.0)


def stand(fem):
    d = {}
    if fem:
        d.update(foot_L=(-0.012, 0.0, 0.0), foot_R=(-0.012, 0.0, 0.0), fyaw_L=4, fyaw_R=4,
                 hand_L=(0.215, 0.05, 0.93), hand_R=(0.215, 0.05, 0.93))
    return d


def rest_of(fem, **over):
    """Neutral standing controls (used to end a clip back in the idle pose)."""
    d = {k: v for k, v in BASE.items() if not k.startswith(("hdir", "palm"))}
    d = {k: (v if not k.startswith("fg") else "relaxed") for k, v in d.items()}
    d.update(stand(fem))
    d.update(over)
    return d


def loco(fem):
    out = []
    S = stand(fem)
    REST = rest_of(fem)

    # ---- walk backward: toe-first contact, shorter stride, slightly upright
    # (legs, pelvis and arm swing from gait.py; planted at 1.0 m/s)
    c = Clip("walk_back", 30, loop=True, base=S)
    c.gait = ("back", True)
    c.k(0, root=(0, 0.02, -0.03), spine=(-2, 0, 0), chest=(-1, 0, 0), head=(3, 0, 0), wr=(10, 0, 0), fg="soft")
    out.append(c)

    # ---- strafes: side-shuffle (lead foot opens, trailing foot closes, the
    # feet never cross), planted at 1.0 m/s
    for name, tx in (("strafe_l", 1.0), ("strafe_r", -1.0)):
        c = Clip(name, 16, loop=True, base=S)
        c.gait = ("strafe", False, (tx, 0.0))
        c.k(0, root=(0, 0, -0.04), hips=(0, 4 * tx, 0), spine=(2, -2 * tx, -2 * tx), chest=(0, 0, 0),
            head=(0, -6 * tx, 0), elb=(0.6, -0.6, -0.4), fg="soft", hand=(0.25, 0.08, 0.95))
        out.append(c)

    # ---- run start: lean in, drive off the back foot
    c = Clip("run_start", 14, base=S)
    c.k(0)
    c.k(4, root=(0, -0.02, -0.08), hips=(8, -6, 0), spine=(8, 0, 0), chest=(4, 4, 0), head=(-6, 0, 0),
        foot_R=(0, -0.12, 0), fp_R=25, hand_L=(0.2, 0.2, 1.05), hand_R=(0.25, -0.15, 1.0), fg="loose_fist",
        elb=(0.6, -0.8, -0.3))
    c.k(9, root=(0, 0.06, -0.04), hips=(12, 8, 0), spine=(8, 0, 0), chest=(4, -8, 0), foot_R=(0, 0.16, 0.12),
        fp_R=-10, foot_L=(0, -0.2, 0), fp_L=35, hand_L=(0.24, -0.18, 1.0), hand_R=(0.18, 0.26, 1.12))
    c.k(14, root=(0, 0.04, -0.05), hips=(12, 0, 0), foot_R=(0, 0.26, 0), fp_R=-8, foot_L=(0, -0.28, 0.06),
        fp_L=40, hand_L=(0.24, -0.1, 1.04), hand_R=(0.22, 0.2, 1.1))
    out.append(c)

    # ---- run stop: plant the lead foot, skid, arms fling forward, settle
    c = Clip("run_stop", 26, base=S)
    c.k(0, root=(0, 0.04, -0.06), hips=(12, 0, 0), spine=(8, 0, 0), chest=(4, 0, 0), foot_L=(0, 0.25, 0.05),
        fp_L=-10, foot_R=(0, -0.3, 0.08), fp_R=40, hand_L=(0.24, -0.12, 1.05), hand_R=(0.22, 0.22, 1.12),
        fg="loose_fist", elb=(0.6, -0.8, -0.3))
    c.k(4, root=(0, -0.06, -0.14), hips=(-6, -8, 0), spine=(-6, 0, 0), chest=(-4, 6, 0), head=(6, 0, 0),
        foot_L=(0, 0.34, 0), fp_L=-18, foot_R=(0, -0.12, 0), fp_R=20, hand_L=(0.26, 0.24, 1.2),
        hand_R=(0.28, 0.16, 1.24), fg="open")
    c.k(9, root=(0, -0.02, -0.1), hips=(-2, -6, 0), spine=(-2, 0, 0), chest=(2, 3, 0), head=(-2, 0, 0),
        foot_L=(0, 0.3, 0), fp_L=0, foot_R=(0, -0.08, 0), fp_R=0, hand_L=(0.25, 0.14, 1.1), hand_R=(0.25, 0.1, 1.1))
    c.k(15, root=(0, 0.01, -0.04), hips=(0, 0, 0), spine=(1, 0, 0), chest=(0, 0, 0), head=(0, 0, 0),
        foot_L=(0, 0.1, 0.04), foot_R=(0, -0.02, 0), fg="soft")
    c.k(20, foot_L=(0, 0.0, 0), hand_L=(0.235, 0.04, 0.95), hand_R=(0.235, 0.04, 0.95))
    c.kd(26, REST)
    out.append(c)

    # ---- turn in place (the game rotates the body; head leads, feet re-step)
    c = Clip("turn_l", 20, base=S)
    c.k(0)
    c.k(3, head=(0, 30, 0), neck=(0, 10, 0), chest=(0, 8, 0))
    c.k(7, root=(0.03, 0, -0.03), hips=(0, 10, 0), chest=(0, 12, 2), foot_L=(0.02, 0.02, 0.05), fyaw_L=30,
        fp_L=6, hand_L=(0.25, -0.02, 0.95), hand_R=(0.22, 0.12, 0.95))
    c.k(11, root=(0.02, 0, -0.03), foot_L=(0.03, 0.0, 0.0), fyaw_L=12, fp_L=0, foot_R=(0.0, 0.04, 0.05),
        fyaw_R=-18, fp_R=8, head=(0, 12, 0), neck=(0, 4, 0))
    c.k(15, root=(0, 0, -0.02), hips=(0, 3, 0), chest=(0, 2, 0), foot_R=(0, 0, 0), fyaw_R=6, fp_R=0,
        head=(0, 2, 0), neck=(0, 0, 0))
    c.kd(20, REST)
    out.append(c)
    out.append(c.mirrored("turn_r"))

    # ---- qinggong sprint: long leaning strides, arms swept back like wings
    # (legs and pelvis from gait.py; planted at 6.2 m/s)
    c = Clip("sprint", 18, loop=True, base=S)
    c.gait = ("sprint", False)
    c.k(0, root=(0, 0.06, 0.0), hips=(16, 0, 0), spine=(8, 0, 0), chest=(4, 0, 0), neck=(-6, 0, 0),
        head=(-10, 0, 0), hand=(0.3, -0.42, 1.08), elb=(0.4, 0.3, 1.0), hw=0.7, hdir=(0.2, -1, -0.2),
        palm=(0, 0, 1), fg="flat", sh=(4, -6))
    c.sway = dict(hand_L=(0.0, 0.035, 0.02), hand_R=(0.0, -0.035, 0.02))
    out.append(c)

    # ---- crouch idle / crouch walk / sneak
    crouch = dict(root=(0, -0.06, -0.36), hips=(26, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), neck=(-12, 0, 0),
                  head=(-16, 0, 0), foot_L=(0.05, 0.1, 0.0), foot_R=(0.07, -0.08, 0.0), fp_R=18,
                  fyaw_L=14, fyaw_R=18, knee_L=(0.5, 1, 0), knee_R=(0.5, 1, 0),
                  hand_L=(0.2, 0.3, 1.03), hand_R=(0.16, 0.28, 0.98), fg="soft", elb=(0.8, -0.3, -0.6),
                  wr=(10, 0, 0))
    c = Clip("crouch_idle", 90, loop=True, base=S, extra=breath(90, 1.2))
    c.kd(0, crouch)
    c.k(30, head=(-14, 18, 0), neck=(-12, 6, 0))
    c.k(55, head=(-14, -14, 0), neck=(-12, -4, 0))
    c.k(75, head=(-16, 0, 0), neck=(-12, 0, 0))
    out.append(c)

    c = Clip("crouch_walk", 40, loop=True, base=S)
    c.gait = ("crouch", False)
    c.kd(0, {k: v for k, v in crouch.items() if not k.startswith(("foot", "fp", "fyaw", "knee"))})
    c.k(0, root=(0, 0.0, -0.3))
    c.sway = dict(hand_L=(0.0, 0.03, 0.0), hand_R=(0.0, -0.03, 0.0))
    out.append(c)

    c = Clip("sneak", 44, loop=True, base=S)
    c.gait = ("sneak", False)
    c.k(0, root=(0, -0.02, -0.12), hips=(14, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), neck=(-8, 0, 0),
        head=(-10, 0, 0), hand_L=(0.16, 0.26, 1.18), hand_R=(0.18, 0.2, 1.1), fg="claw",
        elb=(0.9, -0.2, -0.6), wr=(24, 0, 0), sh=(4, 4))
    c.sway = dict(hand_L=(0.0, 0.02, 0.01), hand_R=(0.0, -0.02, 0.01))
    out.append(c)

    # ---- jumping
    c = Clip("jump_start", 10, base=S, lag=0.6)
    c.k(0)
    c.k(4, root=(0, -0.02, -0.16), hips=(18, 0, 0), spine=(8, 0, 0), chest=(2, 0, 0), head=(-10, 0, 0),
        hand=(0.3, -0.2, 1.0), elb=(0.3, -1, 0), fg="soft", knee=(0.25, 1, 0))
    c.k(10, root=(0, 0.02, 0.1), hips=(-2, 0, 0), spine=(-4, 0, 0), chest=(-4, 0, 0), head=(4, 0, 0),
        hand=(0.3, 0.2, 1.62), fg="open", fp=45, foot=(0, -0.02, 0.1), tc=0.3)
    out.append(c)

    air = dict(root=(0, 0, 0.0), hips=(4, 0, 0), spine=(2, 0, 0), chest=(-2, 0, 0), head=(2, 0, 0),
               fs=1.0, tc=0.0, foot_L=(0.0, 0.14, 0.26), fp_L=10, foot_R=(0.0, -0.06, 0.12), fp_R=30,
               knee_L=(0.2, 1, 0.2), knee_R=(0.2, 1, 0), hand_L=(0.36, 0.1, 1.34), hand_R=(0.38, 0.0, 1.3),
               elb=(0.6, -0.6, -0.3), fg="open", hw=0.0, wr=(-10, 0, 0))
    c = Clip("jump_air", 24, loop=True, base=S)
    c.kd(0, air)
    c.k(12, hand_L=(0.38, 0.06, 1.38), hand_R=(0.4, -0.04, 1.36), foot_L=(0.0, 0.12, 0.23),
        foot_R=(0, -0.08, 0.14), head=(3, 0, 0))
    out.append(c)

    c = Clip("fall", 20, loop=True, base=S)
    c.kd(0, {**air, "foot_L": (0.02, 0.04, 0.08), "foot_R": (0.03, -0.04, 0.04), "fp_L": 20, "fp_R": 25,
             "hand_L": (0.42, 0.06, 1.5), "hand_R": (0.44, 0.0, 1.46), "hips": (-2, 0, 0), "spine": (-4, 0, 0),
             "head": (8, 0, 0)})
    c.k(10, hand_L=(0.44, 0.02, 1.56), hand_R=(0.42, 0.06, 1.52), foot_L=(0.02, 0.0, 0.06),
        foot_R=(0.03, 0.02, 0.08))
    out.append(c)

    c = Clip("jump_land", 16, base=S, lag=0.7)
    c.kd(0, {**air, "foot_L": (0.0, 0.04, 0.05), "foot_R": (0.0, -0.02, 0.05), "fs": 0.0, "fp_L": 20,
             "fp_R": 20, "root": (0, 0, 0.02)})
    c.k(3, root=(0, 0.0, -0.17), hips=(20, 0, 0), spine=(8, 0, 0), chest=(2, 0, 0), head=(-8, 0, 0),
        foot_L=(0.02, 0.06, 0), foot_R=(0.02, -0.03, 0), fp=0, tc=1.0, hand=(0.3, 0.16, 1.02),
        knee=(0.3, 1, 0), fg="soft")
    c.k(8, root=(0, 0, -0.06), hips=(6, 0, 0), spine=(2, 0, 0), head=(0, 0, 0), hand=(0.25, 0.06, 0.96))
    c.kd(16, REST)
    out.append(c)

    # superhero landing: one knee down, a palm on the ground, then rise
    c = Clip("landing_hard", 40, base=S, lag=0.6)
    c.kd(0, {**air, "fs": 0.0, "foot_L": (0.0, 0.1, 0.1), "foot_R": (0, -0.05, 0.1), "root": (0, 0, 0.06)})
    c.k(4, root=(0, -0.02, -0.5), hips=(30, 0, 0), spine=(18, 0, 0), chest=(8, 0, 0), neck=(-14, 0, 0),
        head=(-18, 0, 0), foot_L=(0.04, 0.2, 0), fp_L=0, foot_R=(0.05, -0.34, 0.0), fp_R=55, tc=1.0,
        knee_L=(0.3, 1, 0), knee_R=(0.2, 0.3, -1), hand_R=(0.24, 0.26, 0.04), hs_R=1.0, fg_R="spread",
        hw_R=0.8, hdir_R=(0.2, 1, 0), palm_R=(0, 0, -1), hand_L=(0.42, -0.12, 0.9), fg_L="open",
        elb_R=(0.8, -0.2, 0))
    c.hold(18)
    c.k(26, root=(0, -0.02, -0.26), hips=(18, 0, 0), spine=(8, 0, 0), chest=(2, 0, 0), neck=(-4, 0, 0),
        head=(-4, 0, 0), foot_R=(0.04, -0.2, 0), fp_R=20, hand_R=(0.25, 0.1, 0.98), hs_R=0.0, hw_R=0.0,
        hand_L=(0.25, 0.08, 0.98), fg="soft", knee_R=(0.3, 1, 0))
    c.kd(40, REST)
    out.append(c)

    # qinggong second jump: a tucked forward somersault
    c = Clip("double_jump_flip", 26, base=S, lag=0.5)
    c.kd(0, air)
    c.k(4, hips=(40, 0, 0), spine=(18, 0, 0), chest=(10, 0, 0), head=(-10, 0, 0), foot_L=(0, 0.3, 0.42),
        foot_R=(0, 0.26, 0.4), fp=35, hand_L=(0.2, 0.36, 1.05), hand_R=(0.2, 0.36, 1.05), fg="fist",
        knee=(0.2, 1, 0.3), root=tumble(40, 1.28))
    c.k(10, hips=(190, 0, 0), spine=(24, 0, 0), chest=(14, 0, 0), foot_L=(0, 0.38, 0.52), foot_R=(0, 0.35, 0.5),
        hand_L=(0.18, 0.4, 0.98), hand_R=(0.18, 0.4, 0.98), root=tumble(190, 1.42))
    c.k(16, hips=(330, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), foot_L=(0, 0.2, 0.34), foot_R=(0, 0.1, 0.3),
        hand_L=(0.34, 0.2, 1.2), hand_R=(0.34, 0.2, 1.2), fg="open", root=tumble(330, 1.36))
    c.k(20, hips=(362, 0, 0), spine=(2, 0, 0), chest=(-2, 0, 0), head=(4, 0, 0), foot_L=(0, 0.1, 0.2),
        foot_R=(0, -0.06, 0.12), fp_L=12, fp_R=25, hand_L=(0.38, 0.08, 1.36), hand_R=(0.4, 0.0, 1.32),
        root=(0, 0, 0.05))
    c.k(26, hips=(364, 0, 0), foot_L=(0.0, 0.14, 0.26), foot_R=(0.0, -0.06, 0.12), fp_L=10, fp_R=30,
        root=(0, 0, 0.0))
    out.append(c)

    # glide: floating descent, arms spread like wings, legs trailing
    c = Clip("glide", 60, loop=True, base=S)
    c.k(0, root=(0, 0, 0.02), hips=(10, 0, 0), spine=(4, 0, 0), chest=(-4, 0, 0), neck=(0, 0, 0),
        head=(-4, 0, 0), fs=1.0, tc=0.0, foot_L=(0.0, 0.04, 0.2), foot_R=(0.01, -0.12, 0.06), fp_L=40, fp_R=45,
        knee_L=(0.1, 1, 0.2), hand=(0.62, -0.08, 1.4), elb=(0.3, -1, 0.2), hw=1.0, hdir=(1, -0.2, 0.05),
        palm=(0, 0, -1), fg="open", sh=(4, 0))
    c.k(30, root=(0, 0, 0.05), hand=(0.62, -0.1, 1.45), hips=(8, 0, 0), foot_L=(0, 0.02, 0.22), chest=(-5, 0, 0))
    c.k(15, hips=(10, 0, 3), chest=(-4, 0, -3))
    c.k(45, hips=(10, 0, -3), chest=(-4, 0, 3))
    out.append(c)

    # ground slide (from a sprint)
    c = Clip("slide", 30, base=S, lag=0.6)
    c.k(0, root=(0, 0.06, -0.06), hips=(14, 0, 0), spine=(6, 0, 0), foot_L=(0, 0.2, 0.08), fp_L=-10,
        foot_R=(0, -0.3, 0.1), fp_R=40, hand_L=(0.26, -0.2, 1.05), hand_R=(0.22, 0.22, 1.1), fg="loose_fist")
    c.k(6, root=(0, -0.3, -0.66), hips=(-38, 0, 0), spine=(10, 0, 0), chest=(8, 0, 0), neck=(10, 0, 0),
        head=(14, 0, 0), foot_L=(0.0, 0.55, 0.02), fp_L=-40, foot_R=(0.1, 0.02, 0.0), fp_R=60, tc=0.2,
        knee_R=(1, 0.3, 0.2), hand_R=(0.34, -0.38, 0.06), hs_R=1.0, fg_R="spread", hand_L=(0.36, 0.24, 1.22),
        fg_L="open", elb_R=(0.3, 0.2, 1))
    c.hold(20)
    c.k(30, root=(0, -0.2, -0.5), hips=(-20, 0, 0), spine=(14, 0, 0), chest=(8, 0, 0), neck=(0, 0, 0),
        head=(0, 0, 0), foot_L=(0.0, 0.4, 0.0), fp_L=-10, hand_L=(0.3, 0.2, 1.1))
    out.append(c)

    # ledge hang / climb up (hands on a ledge ~2 m above the feet)
    hang_p = dict(root=(0, -0.08, 0.02), hips=(-6, 0, 0), spine=(-4, 0, 0), chest=(-6, 0, 0), neck=(4, 0, 0),
                  head=(-12, 0, 0), sh=(14, 4), hand=(0.2, 0.2, 2.0), hs=1.0, elb=(0.8, -0.2, -0.2),
                  hw=1.0, hdir=(0, 1, 0.1), palm=(0, 0, -1), fg="hold", fs=1.0, tc=0.0,
                  foot_L=(0.0, 0.04, 0.02), foot_R=(0.0, -0.04, 0.04), fp=35, knee=(0.2, 1, 0))
    c = Clip("ledge_hang", 60, loop=True, base=S)
    c.kd(0, hang_p)
    c.k(30, root=(0, -0.06, 0.02), hips=(-3, 0, 0), foot_L=(0, 0.06, 0.03), foot_R=(0, -0.06, 0.05),
        head=(-14, 0, 0))
    c.k(15, hips=(-5, 0, 2), chest=(-6, 0, -2))
    c.k(45, hips=(-5, 0, -2), chest=(-6, 0, 2))
    out.append(c)

    c = Clip("climb_up", 44, base=S, lag=0.5)
    c.kd(0, hang_p)
    c.k(6, root=(0, -0.1, -0.06), hips=(-2, 0, 0), foot_L=(0, 0.14, 0.2), foot_R=(0, 0.12, 0.18),
        head=(-6, 0, 0))
    c.k(16, root=(0, 0.02, 0.62), hips=(22, 0, 0), spine=(14, 0, 0), chest=(8, 0, 0), neck=(-8, 0, 0),
        head=(-10, 0, 0), sh=(0, 4), hand=(0.24, 0.14, 1.98), elb=(0.7, -1, 0.2), hdir=(0, 1, 0),
        palm=(0, 0, -1), fg="spread", foot_L=(0, 0.2, 0.3), foot_R=(0, 0.16, 0.24))
    c.k(26, root=(0, 0.16, 1.28), hips=(40, 0, 0), spine=(18, 0, 0), chest=(8, 0, 0), fs=0.0, tc=1.0,
        foot_L=(0.02, 0.42, 2.0), fp_L=0, foot_R=(0.02, 0.0, 1.5), fp_R=40, knee=(0.3, 1, 0.2),
        hand=(0.24, 0.3, 1.98))
    c.k(34, root=(0, 0.34, 1.72), hips=(24, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), neck=(0, 0, 0),
        head=(-4, 0, 0), foot_L=(0.02, 0.42, 2.0), fp_L=0, foot_R=(0.0, 0.2, 2.06), fp_R=10,
        hand=(0.27, 0.34, 1.9), hs=0.6, fg="soft", sh=(0, 0))
    c.k(44, root=(0, 0.35, 1.986), hips=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), head=(0, 0, 0),
        foot_L=(0.0, 0.35, 2.0), foot_R=(0.0, 0.35, 2.0), fp=0, hs=0.0, hw=0.0,
        hand=(0.235, 0.03, 0.93), elb=(0.5, -0.8, -0.25), wr=(6, 0, 0), fg="relaxed", knee=(0.12, 1, 0))
    out.append(c)
    return out



def tremble(amp=0.6, speed=5.0, start=0.0, end=1e9):
    """High-frequency tremor (straining qi, crying)."""
    def fn(t, P):
        if not (start <= t <= end):
            return
        a = amp * math.sin(t * speed * 1.7) * math.sin(t * speed * 0.53 + 1.0)
        add(P, "chest", (a, 0.4 * a, 0.0))
        add(P, "head", (-0.6 * a, 0.0, 0.3 * a))
        add(P, "hand_L", (0.0, 0.0, 0.002 * a))
        add(P, "hand_R", (0.0, 0.0, -0.002 * a))
    return fn


def lie_back(fem):
    """Lying on the back, legs forward (end of knockdown / death_back)."""
    return dict(root=(0.0, -0.42, -0.86), hips=(-88, 0, 0), spine=(-4, 0, 0), chest=(-2, 0, 0), neck=(8, 0, 0),
                head=(6, 18, 0), foot_L=(0.02, 0.4, 0.04), foot_R=(0.07, 0.3, 0.05), fp_L=-70, fp_R=-60,
                fyaw_L=24, fyaw_R=30, tc=0.0, knee_L=(0.2, 0, 1), knee_R=(0.4, 0.1, 1),
                hand_L=(0.36, -0.5, 0.05), hand_R=(0.4, -0.3, 0.04), hs=1.0, hw=0.0, elb=(0.8, 0, 1),
                fg="soft", sh=(0, 0), wr=(10, 0, 0))


def lie_front(fem):
    """Lying face down, head turned (end of death_forward)."""
    return dict(root=(0.0, 0.42, -0.86), hips=(88, 0, 0), spine=(2, 0, 0), chest=(0, 0, 0), neck=(-18, 0, 0),
                head=(-10, 60, 0), foot_L=(0.03, -0.46, 0.08), foot_R=(0.07, -0.36, 0.07), fp=70,
                fyaw_L=10, fyaw_R=24, tc=0.0, knee_L=(0.2, 0, -1), knee_R=(0.3, 0, -1),
                hand_L=(0.36, 0.72, 0.04), hand_R=(0.34, 0.2, 0.05), hs=1.0, hw=0.0, elb=(1, 0, 1),
                fg="soft", wr=(0, 0, 0))


def combat(fem):
    out = []
    G = guard(fem)
    SG = sword_guard(fem)
    REST = rest_of(fem)

    def strike(name, T, base=G, lag=0.8):
        c = Clip(name, T, base=base, lag=lag)
        c.k(0)
        return c

    # ---- stances (loops)
    c = Clip("combat_idle", 60, loop=True, base=G, extra=breath(60, 1.4))
    c.k(0)
    c.k(30, root=(0.0, -0.025, -0.095), hand_L=(0.0, 0.37, 1.29), hand_R=(0.05, 0.22, 1.13), head=(-3, 6, 0))
    out.append(c)
    c = Clip("sword_idle", 60, loop=True, base=SG, extra=breath(60, 1.3))
    c.k(0)
    c.k(30, root=(0.0, -0.035, -0.11), hand_R=(0.08, 0.37, 1.21), hand_L=(0.26, -0.03, 1.5), head=(-2, 7, 0))
    out.append(c)

    # ---- palm combo
    c = strike("palm_1", 22)          # right straight palm
    c.k(3, hips=(4, -34, 0), chest=(2, 4, 0), root=(0, -0.04, -0.1), hand_R=(0.17, 0.02, 1.13),
        hdir_R=(0, 1, 0.3), palm_R=(-1, 0, 0), hand_L=(0.0, 0.4, 1.3))
    c.k(5, foot_L=(0.03, 0.2, 0.04))
    c.k(8, hips=(2, 8, 0), spine=(4, 8, 0), chest=(4, 14, 0), head=(-3, -8, 0), root=(0, 0.07, -0.1),
        foot_L=(0.03, 0.27, 0), hand_R=(0.03, 0.64, 1.32), hs_R=1.0, hdir_R=(0, 0.2, 1), palm_R=(0, 1, -0.1),
        hand_L=(0.1, 0.16, 1.22), fg_L="fist", hdir_L=(-0.3, 0.5, 1), palm_L=(-1, 0.2, 0))
    c.k(12, hand_R=(0.03, 0.66, 1.31), chest=(4, 15, 0))
    c.k(17, foot_L=(0.03, 0.2, 0.03))
    c.kd(22, G)
    out.append(c)

    c = strike("palm_2", 22)          # lead palm, hips drive right
    c.k(3, hand_L=(0.06, 0.24, 1.3), hips=(3, -18, 0), root=(0, -0.03, -0.1), hand_R=(0.18, 0.0, 1.1),
        fg_R="fist", hdir_R=(0, 1, 0), palm_R=(0, 0, 1))
    c.k(7, hips=(3, -46, 0), spine=(3, 2, 0), chest=(4, -6, 0), head=(-3, 16, 0), root=(0, 0.06, -0.1),
        hand_L=(0.04, 0.64, 1.34), hs_L=1.0, hdir_L=(0, 0.2, 1), palm_L=(0, 1, -0.1), foot_L=(0.03, 0.22, 0))
    c.k(11, hand_L=(0.04, 0.66, 1.33))
    c.kd(22, G)
    out.append(c)

    c = strike("palm_3", 26)          # twin palms: push the mountain
    c.k(4, root=(0, -0.05, -0.16), hips=(2, -10, 0), chest=(-4, 4, 0), hand=(0.14, 0.12, 1.3),
        hdir=(0.1, 0.2, 1), palm=(0, 1, 0), fg="palm", elb=(0.9, -0.3, -0.8), foot_R=(0.1, -0.2, 0))
    c.k(7, foot_L=(0.04, 0.26, 0.04))
    c.k(11, root=(0, 0.12, -0.14), hips=(4, 0, 0), spine=(4, -4, 0), chest=(6, -4, 0), head=(-4, 0, 0),
        hand=(0.1, 0.56, 1.3), hdir=(0.05, 0.3, 1), foot_L=(0.04, 0.34, 0), foot_R=(0.1, -0.2, 0), fp_R=12)
    c.k(15, hand=(0.1, 0.58, 1.29))
    c.k(21, foot_L=(0.03, 0.2, 0.03), fp_R=0)
    c.kd(26, G)
    out.append(c)

    c = strike("palm_4", 24)          # rising palm
    c.k(4, root=(0, -0.02, -0.22), hips=(12, -20, 0), spine=(8, 6, 0), chest=(4, 10, 0), head=(-8, 0, 0),
        hand_R=(0.12, 0.28, 0.98), hdir_R=(0, 1, 0), palm_R=(0, 0, 1), fg_R="palm", hand_L=(0.0, 0.3, 1.38))
    c.k(10, root=(0, 0.06, 0.0), hips=(-4, 10, 0), spine=(-6, 6, 0), chest=(-6, 8, 0), neck=(-4, 0, 0),
        head=(12, -6, 0), hand_R=(0.05, 0.46, 1.72), hs_R=1.0, hdir_R=(0, 0.3, 1), palm_R=(0, 1, 0.4),
        hand_L=(0.12, 0.18, 1.2), fg_L="fist", fp_R=18, foot_L=(0.03, 0.22, 0))
    c.k(14, hand_R=(0.05, 0.44, 1.76), head=(14, -6, 0))
    c.kd(24, G)
    out.append(c)

    c = strike("palm_5", 40)          # finisher: thunder palm in a bow stance
    c.k(6, root=(0, -0.06, -0.12), hips=(0, -60, 0), spine=(0, -8, 0), chest=(-4, -10, 0), head=(-4, 40, 0),
        hand_R=(0.34, -0.12, 1.24), hand_L=(0.06, 0.02, 1.26), hdir=(0, 0.3, 1), palm=(0.2, 1, 0),
        fg="palm", elb=(0.9, -0.4, -0.6))
    c.k(10, foot_L=(0.04, 0.38, 0.07))
    c.k(15, root=(0, 0.22, -0.24), hips=(6, 0, 0), spine=(4, 0, 0), chest=(6, 4, 0), head=(-6, 0, 0),
        foot_L=(0.05, 0.52, 0), foot_R=(0.08, -0.26, 0), fp_R=16, fyaw_R=45, knee_L=(0.2, 1, 0),
        hand_R=(0.02, 0.6, 1.26), hand_L=(-0.02, 0.56, 1.3), hdir_R=(0, 0.1, 1), hdir_L=(-0.2, 0.2, 1),
        palm_R=(0, 1, 0), palm_L=(0.3, 1, 0))
    c.k(26, root=(0, 0.2, -0.23), hand_R=(0.02, 0.62, 1.26), hand_L=(-0.02, 0.57, 1.3))
    c.k(31, foot_L=(0.04, 0.3, 0.04), fp_R=0, root=(0, 0.06, -0.12))
    c.kd(40, G)
    out.append(c)

    # ---- kick combo
    c = strike("kick_1", 26)          # front snap kick, right leg
    c.k(5, root=(0, -0.02, -0.07), hips=(-4, -12, 0), foot_R=(0.02, 0.1, 0.36), fp_R=30, knee_R=(0.1, 1, 0.3),
        tc_R=0.0, hand_L=(0.02, 0.32, 1.36), hand_R=(0.1, 0.2, 1.26), fg_R="fist")
    c.k(11, hips=(-14, 0, 0), spine=(-6, 0, 0), chest=(4, 0, 0), head=(-6, 0, 0),
        foot_R=(0.05, 0.78, 0.92), fp_R=20, fyaw_R=10, hand_L=(0.1, 0.26, 1.3), hand_R=(0.2, 0.08, 1.2))
    c.k(14, foot_R=(0.05, 0.8, 0.94))
    c.k(18, foot_R=(0.04, 0.2, 0.4), fp_R=30, hips=(-4, -16, 0))
    c.k(22, foot_R=(0.07, -0.12, 0.05), tc_R=1.0)
    c.kd(26, G)
    out.append(c)

    c = strike("kick_2", 28)          # lead-leg roundhouse
    c.k(4, root=(0, -0.05, -0.08), hips=(0, -40, 0), foot_R=(0.07, -0.17, 0), fp_R=20, fyaw_R=70,
        foot_L=(0.06, 0.1, 0.3), fp_L=40, tc_L=0.0, knee_L=(0.6, 0.6, 0.6), hand_R=(0.06, 0.3, 1.34))
    c.k(12, hips=(0, -80, -18), spine=(0, -6, -8), chest=(6, 10, -6), head=(-6, 50, 12),
        foot_L=(0.1, 0.6, 1.02), fp_L=55, knee_L=(0.1, 0.3, 1.0), fyaw_R=105, hand_L=(0.36, -0.1, 1.2),
        hand_R=(0.0, 0.3, 1.4))
    c.k(15, foot_L=(0.02, 0.62, 1.0))
    c.k(20, hips=(0, -40, 0), foot_L=(0.08, 0.22, 0.34), fp_L=30, knee_L=(0.5, 1, 0.3), fyaw_R=60)
    c.k(24, foot_L=(0.03, 0.15, 0.04), tc_L=1.0, fp_L=0)
    c.kd(28, G)
    out.append(c)

    c = strike("kick_3", 30)          # chambered side kick
    c.k(5, hips=(0, 30, 10), root=(0, -0.03, -0.1), foot_R=(-0.06, 0.12, 0.42), fp_R=10, tc_R=0.0,
        knee_R=(-0.3, 1, 0.6), fyaw_L=40, hand_L=(0.1, 0.3, 1.34), hand_R=(0.2, 0.15, 1.3), fg_R="fist")
    c.k(13, hips=(0, 72, 26), spine=(0, 6, 6), chest=(0, -20, 4), neck=(0, -12, 0), head=(0, -30, -20),
        foot_R=(-0.02, 0.86, 0.9), fp_R=-10, fyaw_R=-80, fyaw_L=80, knee_R=(-0.2, 0.4, 1),
        hand_R=(0.34, -0.2, 1.2), hand_L=(0.02, 0.36, 1.46))
    c.k(17, foot_R=(-0.02, 0.88, 0.9))
    c.k(22, hips=(0, 24, 6), foot_R=(-0.04, 0.14, 0.4), fp_R=10, fyaw_R=10)
    c.k(26, foot_R=(0.07, -0.14, 0.04), tc_R=1.0, fyaw_R=40, fyaw_L=12)
    c.kd(30, G)
    out.append(c)

    c = strike("spin_kick", 36, lag=0.5)   # 360 degree spinning back kick
    c.k(4, root=(0, -0.02, -0.12), hips=(4, -10, 0), fp_L=10, hand_L=(0.2, 0.3, 1.3), hand_R=(0.3, 0.1, 1.2))
    c.k(8, fs_R=0.0)
    c.k(12, hips=(0, -120, -6), spine=(0, -10, 0), chest=(0, -16, 0), head=(0, -30, 0), fyaw_L=-110, fp_L=18,
        foot_R=(0.2, -0.1, 0.4), tc_R=0.0, fs_R=0.9, knee_R=(0.4, 1, 0.3), hand_L=(0.3, -0.1, 1.3),
        hand_R=(0.3, 0.2, 1.36), root=(0, 0, -0.04))
    c.k(18, hips=(-10, -220, -26), spine=(0, -10, -8), chest=(0, -10, -6), head=(0, -34, 10), fyaw_L=-210,
        foot_R=(0.55, 0.3, 0.86), fp_R=40, knee_R=(0.2, 0.3, 1), hand_L=(0.32, 0.16, 1.28),
        hand_R=(0.4, -0.2, 1.2))
    c.k(22, hips=(-6, -300, -14), fyaw_L=-300, foot_R=(0.4, 0.2, 0.6), head=(0, -20, 0))
    c.k(28, hips=(2, -370, 0), spine=(3, 9, 0), chest=(1, 9, 0), head=(-3, 4, 0), fyaw_L=-348, fp_L=0,
        foot_R=(0.07, -0.17, 0.08), fs_R=0.0, knee_R=(0.5, 1, 0), root=(0, -0.02, -0.09))
    c.k(31, foot_R=(0.07, -0.17, 0.0), tc_R=1.0)
    c.kd(36, {**G, "hips": (3, -384, 0), "fyaw_L": -348})
    out.append(c)

    c = strike("uppercut", 26)
    c.k(5, root=(0, -0.02, -0.26), hips=(14, -30, 0), spine=(8, 0, 0), chest=(4, 0, 0), head=(-10, 10, 0),
        hand_R=(0.14, 0.22, 0.96), fg_R="fist", hdir_R=(0, 1, 0.3), palm_R=(-0.3, 0, 1),
        hand_L=(0.06, 0.24, 1.4), fg_L="fist", fp_R=10)
    c.k(11, root=(0, 0.05, 0.02), hips=(-6, 16, 0), spine=(-8, 10, 0), chest=(-6, 10, 0), neck=(-6, 0, 0),
        head=(16, -6, 0), hand_R=(0.04, 0.36, 1.74), hs_R=1.0, hdir_R=(0, -0.2, 1), palm_R=(-0.6, -1, 0), fp_R=35,
        foot_R=(0.07, -0.12, 0.0), hand_L=(0.12, 0.14, 1.28))
    c.k(14, hand_R=(0.04, 0.34, 1.78))
    c.kd(26, G)
    out.append(c)

    c = Clip("flying_kick", 30, base=G, lag=0.5)     # airborne jump kick
    c.k(0, fs=0.0)
    c.k(4, fs=1.0, tc=0.0, foot_L=(0.0, 0.2, 0.42), fp_L=30, foot_R=(0.02, 0.1, 0.3), fp_R=30,
        knee=(0.2, 1, 0.3), hips=(10, -10, 0), root=(0, 0, 0.08), hand_L=(0.2, 0.3, 1.36), hand_R=(0.3, 0.0, 1.3))
    c.k(13, hips=(-18, 10, 0), spine=(-6, 0, 0), chest=(8, 0, 0), head=(-10, 0, 0), foot_R=(0.02, 0.84, 0.72),
        fp_R=40, foot_L=(0.02, 0.1, 0.46), knee_L=(0.2, 1, 0.6), hand_L=(0.36, -0.2, 1.26),
        hand_R=(0.06, 0.3, 1.4), fg="fist", root=(0, 0.02, 0.14))
    c.k(17, foot_R=(0.02, 0.86, 0.74))
    c.k(24, hips=(4, 0, 0), spine=(2, 0, 0), chest=(-2, 0, 0), head=(2, 0, 0), foot_L=(0.0, 0.14, 0.26),
        foot_R=(0.0, -0.06, 0.12), fp_L=10, fp_R=30, knee=(0.2, 1, 0.1), hand_L=(0.36, 0.1, 1.34),
        hand_R=(0.38, 0.0, 1.3), fg="open", root=(0, 0, 0.02))
    c.hold(30)
    out.append(c)

    # ---- jian sword combo (sword stays sheathed in the model; the grip is mimed)
    GRIP = dict(hdir_R=(0, 1, -0.3), palm_R=(-1, 0, 0), fg_R="grip")
    c = strike("sword_1", 24, base=SG)   # thrust
    c.k(4, root=(0, -0.05, -0.12), hips=(2, -40, 0), hand_R=(0.16, 0.12, 1.22), hand_L=(0.24, 0.0, 1.56), **GRIP)
    c.k(6, foot_L=(0.02, 0.28, 0.04))
    c.k(9, root=(0, 0.14, -0.16), hips=(4, -14, 0), spine=(4, 4, 0), chest=(2, 10, 0), head=(-4, -6, 0),
        foot_L=(0.02, 0.4, 0), hand_R=(0.02, 0.66, 1.3), hdir_R=(0, 1, 0.05), hand_L=(0.36, -0.2, 1.5),
        fp_R=12)
    c.k(13, hand_R=(0.02, 0.68, 1.3))
    c.k(18, foot_L=(0.02, 0.26, 0.03), root=(0, 0.02, -0.1), fp_R=0)
    c.kd(24, SG)
    out.append(c)

    c = strike("sword_2", 26, base=SG)   # flat slash right to left
    c.k(4, hips=(2, -56, 0), chest=(0, -12, 0), head=(-2, 20, 0), hand_R=(0.46, 0.14, 1.34), hdir_R=(0.4, 0.3, -0.2),
        palm_R=(0, 0, -1), fg_R="grip", hand_L=(0.2, 0.1, 1.45))
    c.k(10, hips=(4, 16, 0), spine=(4, 8, 0), chest=(4, 20, 0), head=(-4, -10, 0), root=(0, 0.08, -0.12),
        hand_R=(-0.22, 0.5, 1.26), hdir_R=(-0.6, 0.5, 0), palm_R=(0, 0, -1), hand_L=(0.36, -0.1, 1.4),
        foot_L=(0.02, 0.28, 0))
    c.k(13, hand_R=(-0.3, 0.42, 1.24), chest=(4, 24, 0))
    c.kd(26, SG)
    out.append(c)

    c = strike("sword_3", 26, base=SG)   # rising backhand slash
    c.k(4, root=(0, -0.02, -0.18), hips=(8, 10, 0), chest=(6, 16, 0), hand_R=(-0.2, 0.32, 0.98),
        hdir_R=(-0.5, 0.4, -0.4), palm_R=(0, 0, 1), fg_R="grip", hand_L=(0.1, 0.2, 1.3))
    c.k(10, root=(0, 0.04, -0.04), hips=(-2, -44, 0), spine=(-4, -6, 0), chest=(-4, -14, 0), head=(4, 14, 0),
        hand_R=(0.42, 0.34, 1.66), hdir_R=(0.6, 0.4, 0.5), palm_R=(0, 0, 1), hand_L=(0.3, -0.1, 1.46),
        fp_R=20)
    c.k(13, hand_R=(0.46, 0.28, 1.7))
    c.kd(26, SG)
    out.append(c)

    c = strike("sword_4", 28, base=SG)   # overhead chop with a lunge
    c.k(6, root=(0, -0.05, -0.06), hips=(-4, -20, 0), spine=(-6, 0, 0), chest=(-6, 6, 0), head=(4, 0, 0),
        hand_R=(0.14, 0.02, 1.9), hdir_R=(0, -0.3, 1), palm_R=(-1, 0, 0), hand_L=(0.1, 0.06, 1.86),
        fg_L="seal", fg_R="grip")
    c.k(8, foot_L=(0.02, 0.34, 0.05))
    c.k(12, root=(0, 0.18, -0.24), hips=(10, -10, 0), spine=(8, 4, 0), chest=(8, 6, 0), head=(-8, 0, 0),
        foot_L=(0.02, 0.46, 0), fp_R=14, hand_R=(0.06, 0.6, 1.08), hdir_R=(0, 1, -0.5), hand_L=(0.36, -0.2, 1.3))
    c.k(15, hand_R=(0.06, 0.6, 1.02))
    c.k(22, foot_L=(0.02, 0.28, 0.04), fp_R=0, root=(0, 0.04, -0.12))
    c.kd(28, SG)
    out.append(c)

    c = strike("sword_5", 44, base=SG, lag=0.6)   # finisher: whirling slash into a lunge
    c.k(5, root=(0, -0.02, -0.14), hips=(2, -60, 0), hand_R=(0.5, 0.0, 1.32), hdir_R=(1, -0.2, 0),
        palm_R=(0, 0, -1), fg_R="grip")
    c.k(12, hips=(2, -150, 0), chest=(0, -10, 0), head=(0, -20, 0), fyaw_L=-130, fp_L=14, foot_R=(0.1, -0.1, 0.1),
        tc_R=0.0, fs_R=0.8, hand_R=(0.56, 0.1, 1.34), hand_L=(0.4, 0.0, 1.4))
    c.k(18, hips=(0, -260, 0), fyaw_L=-250, head=(0, -10, 0), foot_R=(0.1, -0.08, 0.12))
    c.k(24, hips=(4, -345, 0), fyaw_L=-340, fp_L=0, foot_R=(0.1, -0.3, 0.0), fs_R=0.0, tc_R=1.0,
        root=(0, 0.2, -0.26), foot_L=(0.02, 0.48, 0), hand_R=(0.02, 0.7, 1.28), hdir_R=(0, 1, 0.05),
        palm_R=(-1, 0, 0), hand_L=(0.4, -0.3, 1.52), spine=(4, 4, 0), chest=(4, 10, 0), head=(-4, -4, 0))
    c.k(30, hand_R=(0.02, 0.72, 1.27))
    c.k(36, foot_L=(0.02, 0.3, 0.04), root=(0, 0.04, -0.12))
    c.kd(44, {**SG, "hips": (2, -390, 0), "fyaw_L": -352})
    out.append(c)

    # ---- charged heavy strike
    c = Clip("charge_start", 16, base=G, lag=0.7)
    c.k(0)
    c.k(10, root=(0, -0.06, -0.2), hips=(4, -40, 0), spine=(2, -4, 0), chest=(0, -6, 0), head=(-4, 30, 0),
        foot_L=(0.08, 0.2, 0), foot_R=(0.12, -0.2, 0), hand_R=(0.3, -0.16, 1.18), hdir_R=(0, 0.2, 1),
        palm_R=(0, 1, 0), fg_R="claw", hand_L=(0.04, 0.46, 1.3), fg_L="seal", elb_R=(0.8, -0.6, -0.4))
    c.hold(16)
    out.append(c)
    charge_p = dict(root=(0, -0.06, -0.21), hips=(4, -40, 0), spine=(2, -4, 0), chest=(0, -6, 0), head=(-4, 30, 0),
                    foot_L=(0.08, 0.2, 0), foot_R=(0.12, -0.2, 0), hand_R=(0.3, -0.16, 1.18), hdir_R=(0, 0.2, 1),
                    palm_R=(0, 1, 0), fg_R="claw", hand_L=(0.04, 0.46, 1.3), fg_L="seal")
    c = Clip("charge_hold", 30, loop=True, base={**G, **charge_p}, extra=tremble(0.9, 6.0))
    c.k(0)
    c.k(15, root=(0, -0.06, -0.225), hand_R=(0.31, -0.17, 1.19))
    out.append(c)
    c = Clip("charge_release", 34, base={**G, **charge_p}, lag=0.6)
    c.k(0)
    c.k(3, foot_L=(0.08, 0.4, 0.06))
    c.k(6, root=(0, 0.24, -0.24), hips=(6, 6, 0), spine=(6, 8, 0), chest=(6, 12, 0), head=(-6, -8, 0),
        foot_L=(0.08, 0.5, 0), fp_R=16, hand_R=(0.02, 0.84, 1.24), hs_R=1.0, hdir_R=(0, 0.1, 1), palm_R=(0, 1, 0),
        fg_R="palm", hand_L=(0.2, 0.1, 1.2), fg_L="fist")
    c.k(16, root=(0, 0.23, -0.23), hand_R=(0.02, 0.86, 1.24))
    c.k(24, foot_L=(0.04, 0.3, 0.04), fp_R=0, root=(0, 0.08, -0.12))
    c.kd(34, G)
    out.append(c)

    # ---- qi blasts
    c = Clip("blast_forward", 34, base=REST, lag=0.8)
    c.k(0)
    c.k(8, root=(0, -0.02, -0.06), hips=(0, -20, 0), chest=(0, 10, 0), head=(0, 8, 0), foot_L=(0.02, 0.1, 0),
        foot_R=(0.05, -0.1, 0), fyaw_R=30, hand_R=(0.1, 0.24, 1.58), hw_R=1.0, hdir_R=(0, 0.2, 1),
        palm_R=(-1, 0, 0), fg_R="seal", hand_L=(0.12, 0.26, 1.2), hw_L=1.0, hdir_L=(-1, 0.3, 0),
        palm_L=(0, 0, 1), fg_L="flat")
    c.k(14, root=(0, 0.08, -0.08), hips=(2, 0, 0), spine=(4, 0, 0), chest=(4, 6, 0), head=(-4, -4, 0),
        hand_R=(0.06, 0.62, 1.38), hdir_R=(0, 0.2, 1), palm_R=(0, 1, 0), fg_R="palm", foot_L=(0.02, 0.2, 0))
    c.k(20, hand_R=(0.06, 0.6, 1.4))
    c.kd(34, REST)
    out.append(c)

    c = Clip("blast_two_hand", 44, base=REST, lag=0.7)
    c.k(0)
    c.k(10, root=(0, -0.04, -0.16), hips=(0, -40, 0), chest=(-4, -8, 0), head=(0, 40, 0),
        foot_L=(0.08, 0.14, 0), foot_R=(0.1, -0.16, 0), fyaw_R=40,
        hand_R=(0.26, -0.1, 1.08), hand_L=(0.02, -0.08, 1.24), hw=1.0, hdir_R=(0, 1, 0.2), palm_R=(-0.3, 0, 1),
        hdir_L=(0, 1, -0.2), palm_L=(0.3, 0, -1), fg="claw", elb=(0.8, -0.5, -0.4))
    c.k(16, tc=1.0)
    c.k(20, root=(0, 0.16, -0.2), hips=(4, 0, 0), spine=(4, 0, 0), chest=(4, 0, 0), head=(-4, 0, 0),
        hand_R=(0.04, 0.62, 1.3), hand_L=(0.04, 0.62, 1.3), hdir=(0.2, 0.2, 1), palm=(-0.1, 1, 0), fg="spread",
        fp_R=12)
    c.k(30, hand_R=(0.04, 0.64, 1.3), hand_L=(0.04, 0.64, 1.3))
    c.kd(44, REST)
    out.append(c)

    c = Clip("blast_wave", 46, base=REST, lag=0.7)
    c.k(0)
    c.k(12, root=(0, 0, -0.08), hips=(-2, 0, 0), chest=(-6, 0, 0), head=(6, 0, 0), foot_L=(0.02, 0, 0.12),
        fp_L=10, hand=(0.1, 0.22, 1.36), hw=1.0, hdir=(-0.4, 0.3, 1), palm=(-1, 0, 0), fg="seal",
        elb=(1, -0.2, -0.3))
    c.k(18, foot_L=(0.12, 0.02, 0.0), fp_L=0, root=(0, 0, -0.28), hips=(20, 0, 0), spine=(12, 0, 0),
        chest=(6, 0, 0), head=(-12, 0, 0), hand=(0.62, 0.2, 0.8), hdir=(1, 0.2, -0.6), palm=(0, 0, -1),
        fg="spread", foot_R=(0.12, 0.0, 0), knee=(0.5, 1, 0))
    c.k(30, hand=(0.64, 0.2, 0.78), root=(0, 0, -0.27))
    c.kd(46, REST)
    out.append(c)

    c = Clip("blast_rain", 54, base=REST, lag=0.7)
    c.k(0)
    c.k(14, root=(0, 0, 0.0), chest=(-10, 0, 0), neck=(-4, 0, 0), head=(-14, 0, 0), hand_R=(0.14, 0.12, 2.0),
        hw_R=1.0, hdir_R=(0, 0, 1), palm_R=(-1, 0, 0), fg_R="seal", hand_L=(0.14, 0.2, 1.3), hw_L=1.0,
        hdir_L=(-0.6, 0.3, 1), palm_L=(-0.2, 1, 0), fg_L="seal", fp=16, foot_R=(0.0, -0.06, 0))
    c.k(22, head=(-18, 0, 0))
    c.k(28, root=(0, 0.08, -0.12), chest=(6, 0, 0), head=(-2, 0, 0), neck=(0, 0, 0), hand_R=(0.08, 0.64, 1.5),
        hdir_R=(0, 1, 0.3), palm_R=(-1, 0, 0), fp=0, foot_L=(0.02, 0.2, 0))
    c.k(38, hand_R=(0.08, 0.66, 1.48))
    c.kd(54, REST)
    out.append(c)

    # ---- block / parry
    BLOCK = dict(root=(0, -0.04, -0.12), hips=(4, -14, 0), spine=(4, 4, 0), chest=(6, 6, 0), neck=(4, 0, 0),
                 head=(-4, 4, 0), hand_L=(-0.02, 0.28, 1.52), hand_R=(-0.02, 0.24, 1.42), hw=1.0,
                 hdir_L=(-1, 0.1, 0.5), palm_L=(0, 1, 0), hdir_R=(-1, 0.1, 0.6), palm_R=(0, 1, 0), fg="palm",
                 elb=(0.8, 0.3, -1), sh=(4, 6))
    c = Clip("block_start", 8, base=G, lag=0.4)
    c.k(0)
    c.kd(6, BLOCK)
    c.hold(8)
    out.append(c)
    c = Clip("block_idle", 40, loop=True, base={**G, **BLOCK}, extra=breath(40, 1.2))
    c.k(0)
    c.k(20, root=(0, -0.045, -0.13))
    out.append(c)
    c = Clip("block_hit", 16, base={**G, **BLOCK}, lag=0.5)
    c.k(0)
    c.k(3, root=(0, -0.12, -0.15), chest=(-6, 6, 0), head=(4, 4, 0), hand_L=(-0.02, 0.2, 1.54),
        hand_R=(-0.02, 0.16, 1.44), foot_L=(0.03, 0.08, 0), fp_L=-6)
    c.k(16, **BLOCK, foot_L=(0.03, 0.15, 0), fp_L=0)
    out.append(c)
    c = strike("parry", 22, lag=0.5)
    c.k(3, hips=(2, -10, 0), chest=(0, 14, 0), hand_L=(-0.12, 0.34, 1.46), hdir_L=(-0.6, 0.2, 1),
        palm_L=(-0.2, 1, 0))
    c.k(7, hips=(2, -44, 0), chest=(2, -10, 0), head=(-2, 18, 0), hand_L=(0.42, 0.3, 1.4),
        hdir_L=(0.4, 0.4, 1), palm_L=(1, 0.4, 0), root=(0, -0.05, -0.1))
    c.k(11, hand_L=(0.44, 0.24, 1.36), hand_R=(0.02, 0.4, 1.24), hdir_R=(0, 0.2, 1), palm_R=(0, 1, 0))
    c.kd(22, G)
    out.append(c)

    # ---- evasion
    c = Clip("dodge_l", 20, base=G, lag=0.6)
    c.k(0)
    c.k(3, root=(-0.05, 0, -0.16), hips=(6, -20, 6), foot_R=(0.07, -0.17, 0), fp_R=20)
    c.k(7, root=(0.16, 0, -0.1), hips=(4, -24, 16), spine=(0, 0, 8), chest=(0, 10, 6), head=(0, 0, -16),
        foot_L=(0.18, 0.14, 0.08), foot_R=(-0.02, -0.14, 0.12), tc=0.0, fp=20, hand_R=(0.3, 0.2, 1.3),
        hand_L=(0.18, 0.28, 1.4))
    c.k(11, root=(0.06, 0, -0.18), hips=(4, -24, 4), spine=(3, 9, 2), head=(0, 0, -4), foot_L=(0.03, 0.15, 0),
        foot_R=(0.07, -0.17, 0), tc=1.0, fp=0)
    c.kd(20, G)
    out.append(c)
    out.append(c.mirrored("dodge_r"))

    c = Clip("dodge_back", 22, base=G, lag=0.6)
    c.k(0)
    c.k(3, root=(0, 0.02, -0.16), hips=(10, -24, 0), fp_L=20)
    c.k(8, root=(0, -0.18, -0.02), hips=(14, -20, 0), spine=(8, 9, 0), head=(-10, 4, 0), tc=0.0, fp=30,
        foot_L=(0.03, 0.2, 0.12), foot_R=(0.07, -0.28, 0.1), hand_L=(0.08, 0.42, 1.3), hand_R=(0.1, 0.32, 1.2))
    c.k(12, root=(0, -0.06, -0.18), hips=(8, -24, 0), tc=1.0, fp=0, foot_L=(0.03, 0.15, 0),
        foot_R=(0.07, -0.17, 0), fp_R=12)
    c.kd(22, G)
    out.append(c)

    c = Clip("roll_forward", 28, base=G, lag=0.4)
    c.k(0)
    c.k(4, root=tumble(50, 0.76, cf=0.12), hips=(50, 0, 0), spine=(20, 0, 0), chest=(14, 0, 0), neck=(20, 0, 0),
        head=(20, 0, 0), hand=(0.2, 0.5, 0.05), hs=1.0, fg="spread", elb=(0.6, -0.2, 0.2), foot_L=(0.03, 0.1, 0),
        foot_R=(0.05, -0.2, 0.06), fp=30, knee=(0.2, 1, 0))
    c.k(9, root=tumble(150, 0.37), hips=(150, 0, 0), spine=(26, 0, 0), chest=(18, 0, 0), neck=(24, 0, 0),
        head=(22, 0, 0), fs=1.0, tc=0.0,
        foot_L=(0, 0.3, 0.46), foot_R=(0, 0.28, 0.44), hand=(0.18, 0.3, 1.1), hs=0.0)
    c.k(15, root=tumble(260, 0.37), hips=(260, 0, 0), foot_L=(0, 0.34, 0.5), foot_R=(0, 0.32, 0.48),
        hand=(0.2, 0.36, 1.1), fg="fist")
    c.k(21, root=tumble(345, 0.68), hips=(345, 0, 0), spine=(18, 0, 0), chest=(8, 0, 0), neck=(0, 0, 0),
        head=(-10, 0, 0), fs=0.0, tc=1.0, foot_L=(0.06, 0.16, 0), foot_R=(0.08, -0.1, 0), fp_R=30, fp_L=0,
        hand=(0.24, 0.3, 1.1), fg="soft")
    c.kd(28, {**G, "hips": (363, -24, 0)})
    out.append(c)

    c = Clip("backflip", 32, base=G, lag=0.4)
    c.k(0)
    c.k(5, root=(0, 0.02, -0.2), hips=(16, 0, 0), spine=(6, 0, 0), chest=(2, 0, 0), head=(-8, 0, 0),
        hand=(0.3, -0.2, 1.0), hw=0.0, fg="soft", foot_L=(0.02, 0.0, 0), foot_R=(0.02, -0.02, 0), fyaw=8,
        fyaw_R=8, knee=(0.2, 1, 0))
    c.k(10, root=tumble(-60, 1.35, d=0.2), hips=(-60, 0, 0), spine=(-10, 0, 0), chest=(-8, 0, 0), head=(-10, 0, 0),
        hand=(0.34, 0.1, 1.9), fg="open", fs=1.0, tc=0.0, foot_L=(0, 0.05, 0.2), foot_R=(0, 0.05, 0.2), fp=30)
    c.k(16, root=tumble(-190, 1.32, d=0.2), hips=(-190, 0, 0), spine=(8, 0, 0), chest=(8, 0, 0), head=(6, 0, 0),
        foot_L=(0, 0.34, 0.5), foot_R=(0, 0.32, 0.48), hand=(0.2, 0.34, 1.1), fg="fist", knee=(0.2, 1, 0.3))
    c.k(22, root=tumble(-320, 1.08, d=0.2), hips=(-320, 0, 0), spine=(4, 0, 0), chest=(0, 0, 0), head=(-4, 0, 0),
        foot_L=(0, 0.1, 0.25), foot_R=(0, 0.1, 0.25), hand=(0.4, 0.1, 1.4), fg="open")
    c.k(25, root=(0, 0.0, -0.16), hips=(-352, 0, 0), fs=0.0, tc=1.0, foot_L=(0.03, 0.08, 0), foot_R=(0.05, -0.08, 0),
        fp=0, hand=(0.34, 0.2, 1.2))
    c.kd(32, {**G, "hips": (-357, -24, 0)})
    out.append(c)

    # ---- hit reactions
    c = Clip("stagger_front", 26, base=G, lag=1.2)   # struck from the front
    c.k(0)
    c.k(3, root=(0, -0.1, -0.1), hips=(-8, -20, 0), spine=(-10, 0, 0), chest=(-10, 0, 0), neck=(-6, 0, 0),
        head=(-14, 0, 6), hand_L=(0.3, 0.3, 1.42), hand_R=(0.32, 0.26, 1.36), fg="claw", hw=0.0,
        wr=(-20, 0, 0), elb=(0.8, -0.4, -0.3))
    c.k(7, foot_L=(0.03, 0.02, 0.06))
    c.k(10, root=(0, -0.08, -0.12), hips=(0, -22, 0), spine=(2, 6, 0), chest=(4, 6, 0), head=(0, 4, 0),
        foot_L=(0.03, -0.02, 0), hand_L=(0.1, 0.3, 1.3), hand_R=(0.1, 0.2, 1.16), fg="soft")
    c.k(16, foot_L=(0.03, 0.08, 0.03))
    c.kd(26, G)
    out.append(c)

    c = Clip("stagger_back", 26, base=G, lag=1.2)    # struck from behind
    c.k(0)
    c.k(3, root=(0, 0.1, -0.12), hips=(14, -20, 0), spine=(12, 0, 0), chest=(8, 0, 0), neck=(-6, 0, 0),
        head=(10, 0, 0), hand_L=(0.34, -0.1, 1.2), hand_R=(0.36, -0.12, 1.16), fg="claw", hw=0.0,
        elb=(0.6, -0.8, 0.2))
    c.k(6, foot_R=(0.07, -0.04, 0.08))
    c.k(10, root=(0, 0.06, -0.13), foot_R=(0.07, -0.02, 0), hips=(6, -22, 0), head=(-4, 20, 0),
        hand_L=(0.1, 0.34, 1.26), hand_R=(0.12, 0.2, 1.14), fg="soft")
    c.k(18, foot_R=(0.07, -0.12, 0.03))
    c.kd(26, G)
    out.append(c)

    c = Clip("stagger_left", 26, base=G, lag=1.2)    # struck on the left side
    c.k(0)
    c.k(3, root=(-0.1, 0, -0.1), hips=(0, -18, -8), spine=(0, 0, -12), chest=(0, 0, -8), head=(0, 10, 16),
        hand_L=(0.36, 0.1, 1.3), hand_R=(0.4, 0.04, 1.2), fg="claw", hw=0.0, elb=(0.8, -0.4, -0.3))
    c.k(6, foot_R=(0.2, -0.16, 0.07))
    c.k(10, root=(-0.08, 0, -0.12), hips=(2, -22, 0), spine=(2, 6, 0), head=(0, 10, 0), foot_R=(0.22, -0.16, 0),
        hand_L=(0.1, 0.32, 1.3), hand_R=(0.1, 0.2, 1.16), fg="soft")
    c.k(18, foot_R=(0.12, -0.17, 0.03))
    c.kd(26, G)
    out.append(c)
    out.append(c.mirrored("stagger_right"))

    # knockdown: blown off the feet, crash onto the back; getup rolls up from it
    LB = lie_back(fem)
    c = Clip("knockdown", 50, base=G, lag=1.0)
    c.k(0)
    c.k(4, root=(0, -0.16, 0.04), hips=(-24, -10, 0), spine=(-12, 0, 0), chest=(-10, 0, 0), neck=(-6, 0, 0),
        head=(-18, 0, 0), hand=(0.4, 0.3, 1.5), hw=0.0, fg="open", fs=0.6, tc=0.0, foot_L=(0.03, 0.3, 0.2),
        foot_R=(0.07, 0.1, 0.12), fp=20, elb=(0.8, -0.4, 0))
    c.k(12, root=(0, -0.34, -0.42), hips=(-64, 0, 0), spine=(-6, 0, 0), chest=(-4, 0, 0), neck=(10, 0, 0),
        head=(10, 0, 0), foot_L=(0.03, 0.46, 0.3), foot_R=(0.07, 0.36, 0.2), fs=0.0, hand=(0.46, 0.0, 1.2))
    c.k(18, **{**LB, "root": (0, -0.42, -0.84)})
    c.k(22, root=(0, -0.42, -0.8), neck=(14, 0, 0), foot_L=(0.02, 0.4, 0.1))
    c.k(28, **LB)
    c.hold(50)
    out.append(c)

    c = Clip("getup", 50, base=LB, lag=1.0)
    c.k(0)
    c.k(10, root=(0, -0.36, -0.74), hips=(-60, 0, 0), spine=(14, 0, 0), chest=(10, 0, 0), neck=(10, 0, 0),
        head=(4, 0, 0), foot_L=(0.08, 0.26, 0.0), fp_L=0, tc_L=1.0, knee_L=(0.3, 1, 0.2),
        hand_R=(0.34, -0.5, 0.04), hand_L=(0.3, 0.1, 1.1), hs_L=0.0)
    c.k(20, root=(0, -0.2, -0.56), hips=(-10, -30, 0), spine=(20, 0, 0), chest=(10, 0, 0), neck=(0, 0, 0),
        head=(-6, 0, 0), foot_R=(0.1, -0.1, 0.0), fp_R=40, tc_R=1.0, knee_R=(0.3, 0.4, -1),
        hand_R=(0.34, -0.2, 0.04))
    c.k(30, root=(0, -0.04, -0.36), hips=(24, -10, 0), spine=(14, 0, 0), chest=(4, 0, 0), head=(-10, 0, 0),
        foot_L=(0.05, 0.14, 0), foot_R=(0.07, -0.14, 0), fp_R=10, fyaw_L=12, fyaw_R=30, knee_R=(0.4, 1, 0),
        hand_R=(0.3, 0.1, 1.0), hs_R=0.0, hand_L=(0.25, 0.2, 1.05), fg="soft")
    c.k(40, root=(0, -0.02, -0.12), hips=(6, -20, 0), spine=(4, 6, 0), head=(-2, 4, 0), fp_R=0)
    c.kd(50, G)
    out.append(c)

    c = Clip("death_back", 64, base=G, lag=1.2)
    c.k(0)
    c.k(4, root=(0, -0.08, -0.06), hips=(-10, -10, 0), spine=(-10, 0, 0), chest=(-8, 0, 0), head=(-16, 0, 0),
        hand=(0.36, 0.2, 1.36), hw=0.0, fg="claw")
    c.k(10, foot_L=(0.03, -0.12, 0.05), root=(0, -0.16, -0.1))
    c.k(14, foot_L=(0.03, -0.14, 0.0), hips=(-4, -6, 0), spine=(8, 0, 0), chest=(10, 0, 0), head=(12, 0, 0),
        hand_L=(0.2, 0.3, 1.1), hand_R=(0.3, 0.1, 1.0))
    c.k(20, root=(0, -0.14, -0.3), hips=(0, 0, 0), foot_R=(0.07, -0.06, 0), knee=(0.3, 1, 0), fg="soft")
    c.k(30, root=(0, -0.36, -0.6), hips=(-50, 0, 0), spine=(-8, 0, 0), head=(-4, 0, 0),
        foot_L=(0.03, 0.2, 0.02), foot_R=(0.07, 0.1, 0.05), fp=-20, hand=(0.4, -0.1, 1.1))
    c.k(38, **{**LB, "head": (0, 10, 0), "neck": (4, 0, 0), "hand_R": (0.6, -0.1, 0.04)})
    c.k(42, root=(0, -0.42, -0.83), head=(4, 12, 0))
    c.k(48, root=(0, -0.42, -0.86), head=(2, 30, 0), fg="relaxed")
    c.hold(64)
    out.append(c)

    LF = lie_front(fem)
    c = Clip("death_forward", 64, base=G, lag=1.2)
    c.k(0)
    c.k(5, root=(0, 0.06, -0.08), hips=(16, -20, 0), spine=(16, 0, 0), chest=(10, 0, 0), head=(14, 0, 0),
        hand_L=(0.1, 0.2, 1.1), hand_R=(0.16, 0.2, 1.05), fg="claw", hw=0.0)
    c.k(18, root=(0, 0.08, -0.5), hips=(30, -10, 0), spine=(10, 0, 0), head=(0, 0, 0), foot_L=(0.03, 0.1, 0),
        foot_R=(0.07, -0.2, 0), fp_R=60, tc_R=0.0, knee=(0.3, 1, -0.4), hand=(0.3, 0.3, 0.9), fg="soft")
    c.k(26, root=(0, 0.28, -0.7), hips=(70, 0, 0), spine=(4, 0, 0), foot_L=(0.03, -0.2, 0.05), fp_L=40,
        foot_R=(0.07, -0.34, 0.05), hand=(0.34, 0.66, 0.12), hs=1.0, fg="spread", neck=(-10, 0, 0))
    c.k(34, **LF)
    c.k(38, root=(0, 0.42, -0.83))
    c.k(44, root=(0, 0.42, -0.86), fg="relaxed")
    c.hold(64)
    out.append(c)

    c = Clip("revive", 70, base={**REST, **lie_back(fem), "head": (2, 30, 0), "neck": (4, 0, 0),
                                 "hand_R": (0.6, -0.1, 0.04)}, lag=1.0)
    c.k(0)
    c.k(16, root=(0, -0.42, -0.8), head=(0, 0, 0), neck=(0, 0, 0), fg="open")
    c.k(34, root=(0, -0.1, -0.2), hips=(-14, 0, 0), spine=(-4, 0, 0), chest=(-8, 0, 0), neck=(-4, 0, 0),
        head=(-12, 0, 0), fs=1.0, foot_L=(0.02, 0.1, 0.1), foot_R=(0.04, 0.0, 0.1), fp=40, knee=(0.2, 1, 0),
        hand=(0.5, 0.1, 1.1), hs=0.0, hw=1.0, hdir=(1, 0, -0.3), palm=(0, 0, 1), elb=(0.6, -0.6, -0.3))
    c.k(46, root=(0, 0, 0.1), hips=(0, 0, 0), chest=(-10, 0, 0), head=(-16, 0, 0), hand=(0.5, 0.1, 1.5),
        foot_L=(0.0, 0.02, 0.1), foot_R=(0.0, 0.0, 0.1))
    c.k(58, root=(0, 0, -0.03), fs=0.0, tc=1.0, foot_L=(0, 0, 0), foot_R=(0, 0, 0), fp=0, chest=(0, 0, 0),
        head=(0, 0, 0), neck=(0, 0, 0), hand=(0.3, 0.1, 1.0), hw=0.0, fg="soft", fyaw=6)
    c.kd(70, REST)
    out.append(c)
    return out



def lotus(fem):
    """Cross-legged seat on the ground (matches the base `meditate` loop)."""
    return dict(root=(0.0, 0.02, -0.765), hips=(-4, 0, 0), spine=(5, 0, 0), chest=(0, 0, 0), neck=(2, 0, 0),
                head=(-3, 0, 0),
                foot_L=(-0.15, 0.13, 0.03), fyaw_L=-62, fp_L=10, foot_R=(-0.15, 0.2, 0.08), fyaw_R=-58, fp_R=10,
                tc=0.0, knee_L=(1, 0.8, 0.05), knee_R=(1, 0.7, 0.1),
                hand=(0.24, 0.3, 0.26), hs=1.0, hw=1.0, hdir=(-0.25, 1, -0.2), palm=(0, 0, 1), fg="mudra",
                elb=(0.8, -0.4, -0.4))


def sit_casual(fem):
    """Sitting on the ground leaning back on the hands, one knee up."""
    return dict(root=(0.0, -0.12, -0.8), hips=(-22, 0, 0), spine=(12, 0, 0), chest=(8, 0, 0), neck=(4, 0, 0),
                head=(-4, 0, 0),
                foot_L=(0.02, 0.62, 0.03), fp_L=-65, tc_L=0.0, knee_L=(0.2, 0.2, 1), fyaw_L=14,
                foot_R=(0.05, 0.3, 0.0), fp_R=0, knee_R=(0.2, 0.4, 1), fyaw_R=8,
                hand=(0.28, -0.4, 0.03), hs=1.0, hw=1.0, hdir=(0.3, -1, 0), palm=(0, 0, -1), fg="palm",
                elb=(0.6, -1, 0.2))


def seated_chair(fem):
    return dict(root=(0.0, 0.0, -0.5), hips=(-2, 0, 0), spine=(3, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0),
                head=(-2, 0, 0),
                foot_L=(0.01, 0.41, 0.0), foot_R=(0.01, 0.38, 0.0), knee=(0.12, 1, 0.2), fyaw=6,
                hand=(0.14, 0.28, 0.54), hs=1.0, hw=1.0, hdir=(-0.2, 1, -0.3), palm=(0, 0, -1), fg="soft",
                elb=(0.6, -0.8, -0.2))


def seq(c, frames, poses, hold_for=0):
    for f, p in zip(frames, poses):
        c.kd(f, p)
        if hold_for:
            c.hold(f + hold_for)


def cultivation(fem):
    out = []
    S = stand(fem)
    REST = rest_of(fem)
    SIT = lotus(fem)
    SQ = dict(root=(0, -0.06, -0.52), hips=(34, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), head=(-12, 0, 0),
              foot_L=(0.04, 0.06, 0), foot_R=(0.04, -0.04, 0), knee=(0.6, 1, 0), fyaw=18, fp=0, tc=1.0,
              hand=(0.24, 0.34, 1.08), hs=0.0, hw=0.0, fg="soft", elb=(0.7, -0.5, -0.4))

    # ---- meditation in / out
    c = Clip("meditate_enter", 56, base=S, lag=0.9)
    c.kd(0, REST)
    c.k(6, root=(0, 0, -0.04), head=(6, 0, 0), hand=(0.235, 0.1, 0.95), fg="soft")
    c.kd(20, SQ)
    c.k(28, foot_L=(-0.08, 0.1, 0.12), fyaw_L=-30, fp_L=10, tc_L=0.0, knee_L=(1, 0.8, 0.2),
        root=(0, -0.02, -0.62), hand=(0.26, 0.1, 0.12), hs=1.0, fg="spread", hw=0.6, hdir=(0.2, 0.2, -1),
        palm=(0, 0, -1))
    c.k(36, foot_L=SIT["foot_L"], fyaw_L=-62, root=(0, 0.0, -0.72), hips=(6, 0, 0), foot_R=(-0.06, 0.14, 0.12),
        fyaw_R=-30, fp_R=10, tc_R=0.0, knee_R=(1, 0.7, 0.2))
    c.k(44, **{k: v for k, v in SIT.items() if k not in ("hand", "hdir", "palm", "fg", "hw", "hs")},
        hand=(0.24, 0.26, 0.28))
    c.kd(56, SIT)
    out.append(c)

    c = Clip("meditate_exit", 50, base=SIT, lag=0.9)
    c.k(0)
    c.k(8, fg="soft", hand=(0.28, 0.3, 0.12), palm=(0, 0, -1), hdir=(0, 1, -0.4), hips=(10, 0, 0),
        spine=(10, 0, 0), head=(-6, 0, 0))
    c.k(18, foot_R=(0.02, 0.1, 0.1), fyaw_R=10, fp_R=0, tc_R=1.0, knee_R=(0.6, 1, 0.1), root=(0, 0.0, -0.7))
    c.k(26, foot_L=(0.03, 0.02, 0.08), fyaw_L=14, fp_L=0, tc_L=1.0, knee_L=(0.6, 1, 0.1), root=(0, -0.02, -0.6),
        hips=(28, 0, 0), foot_R=(0.04, -0.02, 0))
    c.k(30, foot_L=(0.04, 0.04, 0))
    c.kd(36, {**SQ, "hand": (0.24, 0.32, 1.1)})
    c.kd(50, REST)
    out.append(c)

    c = Clip("meditate_levitate", 96, loop=True, base={**SIT, "fs_L": 1.0, "fs_R": 1.0}, extra=breath(96, 1.6))
    c.k(0, root=(0, 0.02, -0.46), hand=(0.1, 0.24, 1.02), hs=0.0, hdir=(-0.6, 0.8, 0.2), palm=(-0.9, 0, 0.4),
        fg="cup", elb=(0.9, -0.3, -0.5), head=(-4, 0, 0))
    c.k(48, root=(0, 0.02, -0.42), hand=(0.11, 0.25, 1.05), head=(-2, 0, 0))
    c.k(24, hips=(-4, 0, 1.5))
    c.k(72, hips=(-4, 0, -1.5))
    out.append(c)

    c = Clip("meditate_breath", 120, loop=True, base=SIT, extra=breath(120, 2.6))
    c.k(0, hand=(0.12, 0.26, 0.98), hs=0.0, hdir=(-0.7, 0.7, 0), palm=(0, 0, 1), fg="soft")
    c.k(45, hand=(0.1, 0.24, 1.3), hdir=(-0.8, 0.6, 0), palm=(0, 0, 1), head=(-6, 0, 0))
    c.k(60, hand=(0.1, 0.25, 1.3), palm=(0, 0, -1), hdir=(-0.8, 0.6, 0))
    c.k(105, hand=(0.12, 0.27, 0.98), palm=(0, 0, -1), head=(-2, 0, 0))
    out.append(c)

    # ---- breakthrough: gather, strain, burst upward, settle
    c = Clip("breakthrough", 110, base=S, lag=1.0, extra=tremble(1.4, 7.0, 22, 44))
    c.kd(0, REST)
    c.k(14, root=(0, -0.02, -0.2), hips=(10, 0, 0), spine=(10, 0, 0), chest=(8, 0, 0), neck=(10, 0, 0),
        head=(12, 0, 0), foot_L=(0.08, 0.02, 0), foot_R=(0.08, 0.02, 0), fyaw=14, knee=(0.4, 1, 0),
        hand=(0.19, -0.02, 1.08), hw=1.0, hdir=(0, 1, 0), palm=(0, 0, 1), fg="fist", elb=(0.4, -1, 0))
    c.hold(42)
    c.k(50, root=(0, 0, 0.02), hips=(-4, 0, 0), spine=(-8, 0, 0), chest=(-14, 0, 0), neck=(-10, 0, 0),
        head=(-24, 0, 0), hand=(0.56, 0.12, 1.92), hdir=(0.6, 0.1, 1), palm=(0, 1, 0.3), fg="spread", fp=18,
        elb=(0.8, -0.5, -0.3), sh=(10, 0))
    c.k(74, root=(0, 0, 0.03), hand=(0.58, 0.1, 1.95), head=(-26, 0, 0))
    c.k(90, root=(0, 0, -0.06), hips=(0, 0, 0), spine=(2, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0), head=(4, 0, 0),
        hand=(0.12, 0.26, 1.12), hdir=(-1, 0.4, 0), palm=(0, 0, -1), fg="flat", fp=0, sh=(0, 0))
    c.kd(110, REST)
    out.append(c)

    # ---- hand-seal sequence before the chest
    seals = [
        dict(hand=(0.02, 0.24, 1.32), hw=1.0, hdir=(0, 0.2, 1), palm=(-1, 0, 0), fg="flat", elb=(0.9, -0.2, -0.6)),
        dict(hand_L=(0.04, 0.26, 1.36), hand_R=(0.02, 0.24, 1.3), hdir_L=(-0.3, 0.3, 1), hdir_R=(-1, 0.3, 0.1),
             palm_L=(-1, 0, 0.2), palm_R=(0, 0, 1), fg_L="seal", fg_R="fist"),
        dict(hand_L=(0.06, 0.28, 1.52), hand_R=(-0.02, 0.26, 1.48), hdir_L=(-0.6, 0.2, 0.8), hdir_R=(-0.7, 0.3, 0.7),
             palm_L=(0, 1, 0), palm_R=(0, -1, 0), fg="seal", elb=(1, -0.1, -0.4)),
        dict(hand=(0.08, 0.3, 1.38), hdir=(-0.7, 0.2, 0.7), palm=(0, 1, 0), fg="open", elb=(0.9, -0.2, -0.6)),
        dict(hand=(0.06, 0.26, 1.08), hdir=(-0.8, 0.6, 0), palm=(0, 0, 1), fg="mudra", elb=(0.7, -0.5, -0.5)),
    ]
    c = Clip("mudra_sequence", 120, base=S, lag=0.6)
    c.kd(0, REST)
    c.k(6, root=(0, 0, -0.03), head=(4, 0, 0))
    for i, sp in enumerate(seals):
        f = 12 + i * 19
        c.kd(f, sp)
        c.hold(f + 12)
    c.kd(120, REST)
    out.append(c)

    # ---- flying sword: stand on the blade, and hop onto it
    RIDE = dict(root=(0.0, 0.0, -0.07), hips=(0, -18, 0), spine=(1, 8, 0), chest=(0, 6, 0), neck=(0, 2, 0),
                head=(-3, 4, 0),
                foot_L=(-0.08, 0.2, 0), fyaw_L=-4, foot_R=(-0.08, -0.16, 0), fyaw_R=30, knee_L=(0.2, 1, 0),
                knee_R=(0.4, 1, 0),
                hand_L=(0.1, 0.3, 1.4), hw_L=1.0, hdir_L=(-0.2, 0.3, 1), palm_L=(-1, 0.3, 0), fg_L="seal",
                elb_L=(0.8, -0.2, -0.8),
                hand_R=(0.04, -0.17, 1.06), hw_R=1.0, hdir_R=(-1, 0, -0.2), palm_R=(0, -1, 0), fg_R="loose_fist",
                elb_R=(0.8, -0.3, -0.2))
    c = Clip("sword_ride_idle", 72, loop=True, base={**S, **RIDE}, extra=breath(72, 1.1))
    c.k(0)
    c.k(36, root=(0.0, 0.0, -0.05), hips=(1, -18, 1), head=(-2, 6, 0))
    out.append(c)

    c = Clip("sword_mount", 40, base=S, lag=0.6)
    c.kd(0, REST)
    c.k(7, root=(0, 0, -0.18), hips=(14, 0, 0), spine=(6, 0, 0), head=(-8, 0, 0), hand=(0.3, -0.12, 1.0),
        fg="soft", knee=(0.3, 1, 0))
    c.k(14, root=(0, 0, 0.22), hips=(0, -10, 0), fs=1.0, tc=0.0, foot_L=(-0.05, 0.14, 0.18), foot_R=(-0.05, -0.1, 0.1),
        fp=30, hand_L=(0.3, 0.2, 1.5), hand_R=(0.3, 0.0, 1.3), fg="open")
    c.k(21, **{k: v for k, v in RIDE.items() if not k.startswith(("hand", "hdir", "palm", "fg", "elb", "hw"))},
        fs=0.0, tc=1.0, fp=0)
    c.k(22, root=(0.0, 0.0, -0.16))
    c.kd(30, {**RIDE, "root": (0, 0, -0.06)})
    c.kd(40, RIDE)
    out.append(c)

    # ---- standing qi circulation (taiji-like, loops)
    HS = dict(root=(0, 0, -0.14), foot_L=(0.1, 0.02, 0), foot_R=(0.1, 0.02, 0), fyaw=10, knee=(0.3, 1, 0),
              hw=1.0, elb=(0.8, -0.4, -0.6), fg="soft")
    c = Clip("qi_circulate", 128, loop=True, base={**S, **HS}, extra=breath(128, 1.5))
    c.k(0, hand=(0.18, 0.28, 1.02), hdir=(-0.3, 1, 0), palm=(0, 0, -1), root=(0.0, 0, -0.16))
    c.k(32, hand=(0.2, 0.36, 1.38), hdir=(-0.2, 1, 0.1), palm=(0, 0, -1), root=(0.04, 0, -0.1), hips=(0, 8, 0),
        head=(0, 6, 0))
    c.k(64, hand=(0.42, 0.22, 1.3), hdir=(0.8, 0.5, 0.2), palm=(0.2, 0, -1), root=(0.0, 0, -0.12), hips=(0, 0, 0),
        head=(0, 0, 0))
    c.k(96, hand=(0.26, 0.2, 1.0), hdir=(0.3, 1, -0.2), palm=(0, 0, -1), root=(-0.04, 0, -0.18),
        hips=(0, -8, 0), head=(0, -6, 0))
    out.append(c)
    return out


def social(fem):
    out = []
    S = stand(fem)
    REST = rest_of(fem)
    FEM_HANDS = dict(hand_L=(0.03, 0.2, 1.08), hand_R=(0.01, 0.22, 1.1), hw=1.0, hdir_L=(-1, 0.2, -0.2),
                     hdir_R=(-1, 0.3, -0.1), palm_L=(0, 0.3, 1), palm_R=(0, -0.3, -1), fg="soft",
                     elb=(0.7, -0.6, -0.5))

    def emote(name, T, lag=1.0, extra=None, loop=False, base=None):
        c = Clip(name, T, loop=loop, base={**S, **(base or {})}, lag=lag, extra=extra)
        if not loop:
            c.kd(0, REST)
        out.append(c)
        return c

    # ---- bows
    c = emote("bow_deep", 66)
    if fem:
        c.kd(10, FEM_HANDS)
    else:
        c.k(10, hand=(0.2, 0.12, 0.9), hw=0.0, fg="flat", wr=(0, 0, 0))
    c.k(26, root=(0, -0.07, -0.04), hips=(38, 0, 0), spine=(6, 0, 0), chest=(2, 0, 0), neck=(-2, 0, 0),
        head=(4, 0, 0), **({} if fem else dict(hand=(0.16, 0.32, 0.7), hs=0.6)))
    c.hold(42)
    c.k(56, root=(0, 0, -0.014), hips=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), neck=(0, 0, 0), head=(0, 0, 0),
        hs=0.0)
    c.kd(66, REST)

    c = emote("bow_fist_palm", 52)
    c.k(10, hand_R=(0.03, 0.26, 1.3), hand_L=(0.0, 0.29, 1.31), hw=1.0, hdir_R=(-1, 0.2, 0.2), palm_R=(0, 0, -1),
        hdir_L=(-0.1, 0.25, 1), palm_L=(-1, 0.1, 0), fg_R="fist", fg_L="flat", elb=(0.9, -0.2, -0.7),
        head=(-2, 0, 0))
    c.k(17, hand_R=(0.03, 0.3, 1.28), hand_L=(0.0, 0.33, 1.29), hips=(8, 0, 0), spine=(8, 0, 0), chest=(4, 0, 0),
        head=(2, 0, 0), root=(0, -0.02, -0.02))
    c.hold(34)
    c.k(42, hips=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), head=(0, 0, 0))
    c.kd(52, REST)

    # ---- greetings and pointing
    c = emote("wave", 52)
    up = dict(hand_R=(0.34, 0.12, 1.74), hw_R=1.0, hdir_R=(0.2, 0.1, 1), palm_R=(0, 1, 0),
              fg_R="orchid" if fem else "open", elb_R=(1, -0.2, -0.6), head=(-4, -6, 3 if fem else 0),
              chest=(-2, -4, 0), sh_R=(8, 0))
    c.kd(10, up)
    for i, f in enumerate((16, 22, 28, 34, 40)):
        c.k(f, hand_R=(0.4 if i % 2 == 0 else 0.26, 0.12, 1.72), hdir_R=((0.6, 0.1, 1) if i % 2 == 0 else
                                                                         (-0.3, 0.1, 1)))
    c.kd(52, REST)

    c = emote("beckon", 48)
    c.k(10, hand_R=(0.14, 0.36, 1.22), hw_R=1.0, hdir_R=(-0.2, 1, 0.1), palm_R=(0, 0, 1), fg_R="open",
        elb_R=(0.8, -0.5, -0.6), head=(4, -4, 0), chest=(2, -3, 0))
    for f, g in ((16, "soft"), (21, "open"), (26, "cup"), (31, "open"), (36, "cup")):
        c.k(f, fg_R=g, hand_R=(0.14, 0.33 if g != "open" else 0.37, 1.22))
    c.kd(48, REST)

    c = emote("point", 44)
    c.k(4, head=(-4, -12, 0), neck=(0, -4, 0))
    c.k(12, hand_R=(0.26, 0.6, 1.5), hs_R=1.0, hw_R=1.0, hdir_R=(0.3, 1, 0.2), palm_R=(-1, 0, -0.3), fg_R="point",
        elb_R=(0.8, -0.3, -0.6), chest=(0, -8, 0), head=(-6, -8, 0), foot_R=(0.02, 0.06, 0))
    c.k(16, hand_R=(0.26, 0.62, 1.52))
    c.hold(32)
    c.kd(44, REST)

    c = emote("nod", 28)
    for f, p in ((6, 12), (11, -3), (16, 9), (21, -1)):
        c.k(f, head=(p, 0, 0), neck=(p * 0.3, 0, 0))
    c.kd(28, REST)

    c = emote("shake_head", 34)
    for f, y in ((6, 18), (12, -18), (18, 14), (24, -10)):
        c.k(f, head=(2, y, 0), neck=(0, y * 0.3, 0))
    c.kd(34, REST)

    # ---- emotions
    bounce = 4.0 if not fem else 2.5

    def laugh_fn(t, P):
        if 10 <= t <= 54:
            k = math.sin((t - 10) * 0.9) * (1 - (t - 10) / 50)
            add(P, "chest", (bounce * k, 0, 0))
            add(P, "sh_L", (3 * k, 0))
            add(P, "sh_R", (3 * k, 0))
            add(P, "head", (-bounce * 0.8 * k, 0, 0))
    c = emote("laugh", 66, extra=laugh_fn)
    c.k(10, chest=(-10, 0, 0), head=(-12, 0, 4), spine=(-4, 0, 0),
        hand_L=(0.1, 0.2, 1.08), hw_L=1.0, hdir_L=(-1, 0.2, 0), palm_L=(0, -1, 0), fg_L="soft")
    if fem:
        c.k(10, hand_R=(0.02, 0.15, 1.62), hw_R=1.0, hdir_R=(-0.8, 0.2, 0.5), palm_R=(0, -1, 0), fg_R="soft",
            head=(-4, 8, 6), chest=(-2, 0, 0))
    c.k(36, chest=(4, 0, 0), spine=(6, 0, 0), head=(4, 0, 0))
    c.kd(66, REST)

    c = emote("cry", 96, extra=tremble(1.8, 2.2, 14, 80))
    c.k(14, hand=(0.05, 0.13, 1.66), hw=1.0, hdir=(-0.4, 0.1, 1), palm=(0, -1, 0), fg="soft",
        head=(14, 0, 0), neck=(8, 0, 0), spine=(6, 0, 0), chest=(6, 0, 0), root=(0, 0, -0.04), sh=(6, 6),
        elb=(0.6, -0.3, -1))
    c.k(50, head=(18, 6, 0), hand=(0.06, 0.12, 1.64))
    c.hold(80)
    c.kd(96, REST)

    c = emote("shrug", 36)
    c.k(10, sh=(14, 0), hand=(0.34, 0.2, 1.04), hw=1.0, hdir=(0.4, 1, 0), palm=(0, 0, 1), fg="open",
        head=(0, 0, 10), elb=(0.6, -0.8, -0.3))
    c.hold(20)
    c.kd(36, REST)

    c = emote("clap", 46)
    c.k(8, hand=(0.1, 0.28, 1.3), hw=1.0, hdir=(-0.2, 0.3, 1), palm=(-1, 0, 0), fg="flat", elb=(0.8, -0.3, -0.7))
    for i, f in enumerate(range(12, 38, 4)):
        c.k(f, hand=(0.035 if i % 2 == 0 else 0.13, 0.28, 1.3))
    c.kd(46, REST)

    c = emote("cheer", 50)
    for f, z in ((10, 1.96), (18, 1.84), (26, 1.98), (34, 1.86)):
        c.k(f, hand=(0.22, 0.06, z), fg="fist", hw=1.0, hdir=(0, 0, 1), palm=(-1, 0, 0), elb=(1, -0.2, -0.4),
            head=(-10, 0, 0), chest=(-6, 0, 0), fp=10 if z > 1.9 else 0, root=(0, 0, 0.0 if z > 1.9 else -0.04))
    c.kd(50, REST)

    c = emote("facepalm", 60)
    c.k(12, hand_R=(0.02, 0.13, 1.72), hw_R=1.0, hdir_R=(-0.6, 0, 1), palm_R=(0, -1, 0), fg_R="soft",
        elb_R=(0.8, 0.2, -1), head=(14, 0, 0), neck=(6, 0, 0))
    c.k(24, head=(14, 8, 0))
    c.k(32, head=(14, -8, 0))
    c.k(40, head=(16, 0, 0))
    c.hold(46)
    c.kd(60, REST)

    c = emote("thinking", 96, loop=True, base=dict(
        hand_R=(0.0, 0.16, 1.57), hw_R=1.0, hdir_R=(-0.4, 0, 1), palm_R=(-0.2, -1, 0), fg_R="point",
        elb_R=(0.3, -0.2, -1), hand_L=(-0.12, 0.16, 1.2), hw_L=1.0, hdir_L=(-1, 0, 0), palm_L=(0, 0, 1),
        fg_L="soft", elb_L=(0.8, -0.4, -0.4), head=(-6, -10, 6), root=(0.02, 0, -0.02), hips=(0, 0, 3)),
        extra=breath(96, 1.0))
    c.k(0)
    c.k(48, head=(-10, 8, 4), hand_R=(0.0, 0.17, 1.58))

    c = emote("arms_crossed", 96, loop=True, base=dict(
        hand_L=(-0.12, 0.13, 1.3), hw_L=1.0, hdir_L=(-1, 0.2, 0.1), palm_L=(0, -0.3, -1), fg_L="soft",
        elb_L=(0.6, 0.3, -1), hand_R=(-0.13, 0.17, 1.24), hw_R=1.0, hdir_R=(-1, 0.1, 0.1), palm_R=(0, -0.2, -1),
        fg_R="soft", elb_R=(0.6, 0.4, -1), root=(-0.03, 0, -0.02), hips=(0, 4, -3), head=(-2, 6, 0),
        foot_L=(0.02, 0.04, 0), fyaw_L=14), extra=breath(96, 1.0))
    c.k(0)
    c.k(48, head=(0, -6, 0))

    c = emote("bashful", 72)
    c.k(10, hand=(0.08, -0.15, 1.02), hw=1.0, hdir=(-1, -0.2, -0.3), palm=(0, -1, 0), fg="soft",
        elb=(0.6, -1, 0.2), head=(14, 0, 8), neck=(6, 0, 0))
    c.k(24, hips=(0, 8, 0), chest=(0, 6, 0), foot_R=(-0.02, -0.08, 0.02), fp_R=40, tc_R=0.0, fyaw_R=-20)
    c.k(36, hips=(0, -6, 0), chest=(0, -6, 0), head=(12, -6, 8))
    c.k(48, hips=(0, 6, 0), chest=(0, 4, 0), foot_R=(-0.02, -0.1, 0.03), head=(14, 4, 10))
    c.k(58, foot_R=(0, 0, 0), fp_R=0, tc_R=1.0, fyaw_R=6)
    c.kd(72, REST)

    c = emote("angry_stomp", 46)
    c.k(6, hand=(0.26, 0.02, 0.96), fg="fist", sh=(8, 4), head=(10, 0, 0), neck=(-6, 0, 0), spine=(6, 0, 0))
    c.k(11, foot_R=(0.02, 0.06, 0.2), fp_R=-10, tc_R=0.0, root=(0.03, 0, 0.0), hips=(0, 0, 4))
    c.k(15, foot_R=(0.02, 0.06, 0.0), fp_R=0, tc_R=1.0, root=(0.0, 0, -0.08), hips=(0, 0, 0),
        hand=(0.26, 0.0, 0.9), head=(14, 0, 0))
    c.hold(28)
    c.kd(46, REST)

    c = emote("surprised", 40)
    c.k(5, root=(0, -0.06, 0.01), hips=(-4, 0, 0), chest=(-8, 0, 0), head=(-10, 0, 0),
        hand=(0.2, 0.22, 1.46), hw=1.0, hdir=(0, 0.2, 1), palm=(0, 1, 0), fg="spread", elb=(0.8, -0.4, -0.7),
        foot_L=(0.0, -0.08, 0.0), sh=(8, 0))
    c.k(9, root=(0, -0.06, -0.06))
    c.hold(20)
    c.kd(40, REST)

    c = emote("sigh", 62)
    c.k(16, sh=(9, -2), chest=(-5, 0, 0), head=(-6, 0, 0))
    c.k(34, sh=(-3, 2), chest=(4, 0, 0), spine=(6, 0, 0), head=(16, 0, 0), neck=(6, 0, 0), root=(0, 0, -0.03),
        hand=(0.24, 0.06, 0.9))
    c.hold(46)
    c.kd(62, REST)

    c = emote("yawn", 84)
    c.k(16, hand_R=(0.03, 0.15, 1.62), hw_R=1.0, hdir_R=(-0.8, 0, 0.6), palm_R=(0, -1, 0), fg_R="soft",
        elb_R=(0.8, 0.1, -1), head=(-12, 0, 0), chest=(-6, 0, 0),
        hand_L=(0.38, 0.06, 1.78), hw_L=1.0, hdir_L=(0.4, 0, 1), palm_L=(-0.2, 1, 0), fg_L="spread",
        elb_L=(1, -0.3, -0.3), fp=8)
    c.hold(40)
    c.k(56, head=(4, 0, 0), chest=(0, 0, 0), fp=0, hand_L=(0.24, 0.05, 0.94), hw_L=0.0, fg_L="relaxed")
    c.kd(84, REST)

    c = emote("stretch", 96)
    c.k(16, hand=(0.04, 0.04, 2.02), hw=1.0, hdir=(-0.6, 0, 0.8), palm=(0, 0, 1), fg="spread",
        elb=(1, -0.2, 0), fp=16, head=(-10, 0, 0), chest=(-8, 0, 0), sh=(10, 0))
    c.hold(34)
    c.k(48, hips=(0, 0, 6), spine=(0, 0, 10), chest=(-6, 0, 8), fp=0)
    c.k(62, hips=(0, 0, -6), spine=(0, 0, -10), chest=(-6, 0, -8))
    c.k(74, hips=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), hand=(0.3, 0.1, 1.3), hw=0.3)
    c.kd(96, REST)

    c = emote("look_around", 96)
    c.k(20, head=(-2, 48, 0), neck=(0, 14, 0), chest=(0, 10, 0), hips=(0, 4, 0))
    c.hold(34)
    c.k(52, head=(-2, -48, 0), neck=(0, -14, 0), chest=(0, -10, 0), hips=(0, -4, 0))
    c.hold(66)
    c.kd(84, REST)
    c.hold(96)

    # ---- sitting, lying, sleeping
    SC = sit_casual(fem)
    SQ = dict(root=(0, -0.08, -0.5), hips=(30, 0, 0), spine=(10, 0, 0), chest=(4, 0, 0), head=(-10, 0, 0),
              foot_L=(0.04, 0.12, 0), foot_R=(0.04, 0.02, 0), knee=(0.5, 1, 0), fyaw=14, fp=0, tc=1.0,
              hand=(0.26, 0.3, 1.1), hs=0.0, hw=0.0, fg="soft", elb=(0.7, -0.5, -0.4))
    c = emote("sit_ground", 48, lag=0.9)
    c.kd(16, SQ)
    c.k(24, hand_R=(0.3, -0.28, 0.06), hs_R=1.0, hw_R=1.0, hdir_R=(0.3, -1, 0), palm_R=(0, 0, -1), fg_R="palm",
        root=(0, -0.1, -0.62))
    c.kd(36, SC)
    c.hold(48)

    c = emote("sit_ground_idle", 100, loop=True, base=SC, extra=breath(100, 1.4))
    c.k(0)
    c.k(30, head=(-8, 20, 0))
    c.k(60, head=(-2, -10, 0), foot_L=(0.02, 0.6, 0.03))

    c = Clip("stand_up", 48, base={**S, **SC}, lag=0.9)
    c.k(0)
    c.k(12, root=(0, -0.04, -0.72), hips=(10, 0, 0), spine=(14, 0, 0), foot_L=(0.03, 0.2, 0.05), fp_L=0,
        tc_L=1.0, knee_L=(0.3, 1, 0.3), hand_L=(0.3, 0.2, 1.05), hs_L=0.0, hw_L=0.0)
    c.kd(24, SQ)
    c.kd(48, REST)
    out.append(c)

    c = emote("sit_chair", 100, loop=True, base=seated_chair(fem), extra=breath(100, 1.3))
    c.k(0)
    c.k(40, head=(-4, 12, 0))
    c.k(70, head=(0, -6, 0), hand_R=(0.14, 0.3, 0.55))

    LB = lie_back(fem)
    SLEEP = {**LB, "hand_L": (0.12, 0.18, 1.12), "hand_R": (0.1, 0.22, 1.08), "hs": 0.0, "hw": 1.0,
             "hdir_L": (-1, 0.2, 0), "hdir_R": (-1, 0.1, 0), "palm_L": (0, -1, 0), "palm_R": (0, -1, 0.2),
             "elb": (0.9, -0.2, -0.2), "head": (2, 30, 0), "neck": (6, 0, 0), "fg": "soft",
             "foot_R": (0.05, 0.32, 0.05), "knee_R": (0.6, 0.3, 1)}
    c = emote("lie_down", 64, lag=0.9)
    c.kd(16, SQ)
    c.k(24, hand=(0.3, -0.25, 0.05), hs=1.0, hw=1.0, hdir=(0.3, -1, 0), palm=(0, 0, -1), fg="palm",
        root=(0, -0.12, -0.66))
    c.kd(36, SC)
    c.k(48, root=(0, -0.3, -0.84), hips=(-60, 0, 0), spine=(4, 0, 0), chest=(2, 0, 0), hand=(0.3, -0.5, 0.04))
    c.kd(60, SLEEP)
    c.hold(64)

    c = emote("sleep", 120, loop=True, base=SLEEP, extra=breath(120, 2.2))
    c.k(0)
    c.k(60, head=(2, 34, 0), hand_L=(0.12, 0.19, 1.13))

    # ---- daily life
    c = emote("drink_tea", 74)
    c.k(10, hand_L=(0.07, 0.27, 1.18), hw_L=1.0, hdir_L=(-1, 0.4, 0), palm_L=(0, 0, 1), fg_L="cup",
        hand_R=(0.03, 0.29, 1.21), hw_R=1.0, hdir_R=(-0.7, 0.6, 0.2), palm_R=(-0.2, 0, -1), fg_R="pinch",
        elb=(0.8, -0.5, -0.5), head=(8, 0, 0))
    c.k(24, hand_R=(0.03, 0.15, 1.6), hdir_R=(-0.8, 0.4, 0.4), palm_R=(0, -0.5, -1), head=(-2, 0, 0))
    c.k(30, head=(-10, 0, 0), neck=(-4, 0, 0), hand_R=(0.03, 0.14, 1.62), hdir_R=(-0.6, 0.3, 0.8))
    c.hold(40)
    c.k(50, hand_R=(0.03, 0.29, 1.21), hdir_R=(-0.7, 0.6, 0.2), head=(6, 0, 0), neck=(0, 0, 0))
    c.hold(58)
    c.kd(74, REST)

    c = emote("eat", 74)
    c.k(10, hand_L=(0.08, 0.26, 1.28), hw_L=1.0, hdir_L=(-1, 0.4, 0), palm_L=(0, 0, 1), fg_L="cup",
        hand_R=(0.02, 0.3, 1.34), hw_R=1.0, hdir_R=(-0.4, 1, 0.3), palm_R=(-1, 0, 0), fg_R="pinch",
        elb=(0.8, -0.5, -0.5), head=(12, 0, 0), spine=(4, 0, 0))
    for f0 in (18, 42):
        c.k(f0, hand_R=(0.02, 0.29, 1.3))
        c.k(f0 + 8, hand_R=(0.02, 0.14, 1.58), head=(6, 0, 0))
        c.k(f0 + 16, hand_R=(0.02, 0.3, 1.34), head=(12, 0, 0))
    c.kd(74, REST)

    c = emote("read_scroll", 96, loop=True, base=dict(
        hand=(0.17, 0.32, 1.3), hw=1.0, hdir=(-0.3, 0.3, 1), palm=(-1, 0, 0), fg="hold", elb=(0.8, -0.4, -0.6),
        head=(20, 8, 0), neck=(6, 0, 0), spine=(3, 0, 0)), extra=breath(96, 1.0))
    c.k(0)
    c.k(22, head=(21, -8, 0))
    c.k(26, head=(23, 8, 0))
    c.k(48, head=(23, -8, 0))
    c.k(52, head=(25, 8, 0))
    c.k(74, head=(25, -8, 0))
    c.k(80, head=(20, 8, 0))

    c = emote("write_calligraphy", 84, loop=True, base=dict(
        spine=(12, 0, 0), chest=(6, 0, 0), head=(22, 0, 0), neck=(6, 0, 0), root=(0, -0.03, -0.03),
        hand_R=(0.02, 0.42, 1.08), hw_R=1.0, hdir_R=(-0.3, 0.6, -0.8), palm_R=(-1, 0.2, 0), fg_R="pinch",
        elb_R=(0.8, -0.5, -0.3),
        hand_L=(-0.06, 0.32, 1.12), hw_L=1.0, hdir_L=(-1, 0.3, 0), palm_L=(0, 0, -1), fg_L="pinch",
        elb_L=(0.8, -0.5, -0.4)), extra=breath(84, 1.0))
    strokes = [(0.02, 0.42, 1.08), (0.0, 0.46, 1.06), (0.04, 0.47, 1.06), (0.05, 0.4, 1.07), (-0.02, 0.38, 1.06),
               (0.03, 0.36, 1.1), (0.06, 0.44, 1.06)]
    for i, p in enumerate(strokes):
        c.k(i * 12, hand_R=p, hand_L=(-0.06 + (p[0] - 0.02) * 0.6, 0.32 + (p[1] - 0.42) * 0.6, 1.12))

    def flute_fingers(t, P):
        for sd, ph in (("L", 0.0), ("R", 1.7)):
            v = list(P[f"fg_{sd}"])
            for fi in range(3):
                tap = max(0.0, math.sin(t * 0.45 + ph + fi * 1.3)) ** 3 * 22
                v[fi * 3] -= tap
                v[fi * 3 + 1] -= tap * 0.6
            P[f"fg_{sd}"] = tuple(v)
    c = emote("play_flute", 64, loop=True, base=dict(
        hand_L=(-0.02, 0.2, 1.58), hw=1.0, hdir_L=(-0.5, 0.3, 0.9), palm_L=(0.2, 1, 0.2),
        hand_R=(0.24, 0.2, 1.53), hdir_R=(0.3, 0.3, 1), palm_R=(0.2, 1, -0.2), fg="hold", elb=(0.9, -0.3, -0.6),
        head=(4, -12, -8), chest=(0, -4, 0), sh=(4, 4)),
        extra=chain(breath(64, 1.6), flute_fingers))
    c.k(0)
    c.k(32, hips=(0, 4, 2), chest=(0, -6, -2), head=(2, -14, -10))

    SIT = lotus(fem)
    c = emote("play_guqin", 80, loop=True, base={**SIT, "hand_L": (0.18, 0.4, 1.02), "hand_R": (0.08, 0.4, 1.02),
                                                 "hs": 0.0, "hdir": (-0.1, 1, -0.3), "palm": (0, 0, -1),
                                                 "fg_L": "soft", "fg_R": "pinch", "elb": (0.9, -0.4, -0.4),
                                                 "head": (16, 0, 0), "spine": (8, 0, 0)},
              extra=breath(80, 1.2))
    c.k(0)
    for i, x in enumerate((0.06, 0.12, 0.02, 0.1, 0.04)):
        c.k(8 + i * 14, hand_R=(x, 0.42, 1.0), fg_R="pinch" if i % 2 else "point")
        c.k(14 + i * 14, hand_R=(x, 0.38, 1.04), hand_L=(0.18 + 0.02 * (i % 2), 0.4, 1.0))

    c = emote("sweep_floor", 48, loop=True, base=dict(
        spine=(12, 0, 0), chest=(4, 0, 0), head=(14, 0, 0), root=(0, -0.02, -0.08),
        hand_R=(-0.04, 0.3, 0.98), hand_L=(0.12, 0.24, 1.26), hw=1.0, hdir_R=(-1, 0.1, 0), palm_R=(0, -0.3, 1),
        hdir_L=(-1, 0.2, 0), palm_L=(0, -0.3, 1), fg="hold", elb=(0.8, -0.6, -0.4), knee=(0.3, 1, 0)),
        extra=breath(48, 1.0))
    c.k(0, hips=(0, -10, 0), hand_R=(-0.2, 0.34, 0.98), hand_L=(0.02, 0.26, 1.26), head=(14, -10, 0))
    c.k(24, hips=(0, 10, 0), hand_R=(0.14, 0.32, 0.94), hand_L=(0.18, 0.2, 1.24), head=(14, 10, 0))

    c = emote("pick_up", 50, lag=0.8)
    c.k(18, root=(0, -0.06, -0.42), hips=(36, 0, 0), spine=(14, 0, 0), chest=(4, 0, 0), head=(0, 0, 0),
        foot_L=(0.04, 0.1, 0), foot_R=(0.04, -0.12, 0), fp_R=30, knee=(0.4, 1, 0),
        hand_R=(0.1, 0.46, 0.06), hs_R=1.0, hw_R=1.0, hdir_R=(-0.2, 1, -0.6), palm_R=(-1, 0, 0), fg_R="open",
        hand_L=(0.26, 0.22, 1.08), elb_R=(0.6, -0.4, 0))
    c.k(22, fg_R="hold")
    c.k(34, root=(0, -0.01, -0.03), hips=(0, 0, 0), spine=(2, 0, 0), chest=(0, 0, 0), head=(16, 0, 0),
        foot_R=(0, 0, 0), fp_R=0, hand_R=(0.06, 0.26, 1.28), hs_R=0.0, hdir_R=(-0.8, 0.6, 0), palm_R=(0, 0, 1))
    c.hold(42)
    c.kd(50, REST)

    c = emote("give_item", 54)
    c.k(12, hand=(0.08, 0.4, 1.24), hw=1.0, hdir=(-0.3, 1, 0), palm=(0, 0, 1), fg="cup", elb=(0.7, -0.6, -0.5),
        hips=(8, 0, 0), spine=(6, 0, 0), head=(4, 0, 0), root=(0, -0.02, -0.02))
    c.hold(30)
    c.k(38, fg="soft", hand=(0.12, 0.3, 1.18))
    c.kd(54, REST)

    c = emote("push_door", 48)
    c.k(8, hand=(0.16, 0.3, 1.36), hw=1.0, hdir=(0, 0.2, 1), palm=(0, 1, 0), fg="palm", elb=(0.8, -0.5, -0.6))
    c.k(12, foot_L=(0.0, 0.2, 0.04))
    c.k(18, foot_L=(0.0, 0.3, 0), root=(0, 0.14, -0.06), hips=(10, 0, 0), spine=(6, 0, 0),
        hand=(0.16, 0.66, 1.32), hs=1.0, fp_R=14)
    c.k(30, hand=(0.16, 0.7, 1.32), root=(0, 0.16, -0.06))
    c.k(38, foot_L=(0.0, 0.14, 0.03), root=(0, 0.04, -0.03), hs=0.0, fp_R=0)
    c.kd(48, REST)

    c = emote("pray_incense", 96)
    c.k(12, hand=(0.02, 0.22, 1.36), hw=1.0, hdir=(0, 0.2, 1), palm=(-1, 0, 0), fg="hold", elb=(0.9, -0.3, -0.7))
    c.k(20, hand=(0.02, 0.2, 1.6), head=(-4, 0, 0))
    for f in (32, 52, 72):
        c.k(f, hips=(18, 0, 0), spine=(8, 0, 0), head=(8, 0, 0), root=(0, -0.04, -0.02))
        c.k(f + 10, hips=(0, 0, 0), spine=(0, 0, 0), head=(-2, 0, 0), root=(0, 0, -0.014))
    c.kd(96, REST)

    # ---- dance (four parts, a flowing sleeve / fan dance)
    hf = "orchid" if fem else "open"
    c = emote("dance_1", 90, lag=1.4)       # opening: arms sweep up in arcs
    c.k(14, hand_R=(0.3, 0.3, 1.3), hand_L=(0.36, -0.1, 1.1), hw=1.0, hdir_R=(0.2, 1, 0.3), palm_R=(0, 0, 1),
        hdir_L=(1, -0.3, 0), palm_L=(0, 0, -1), fg=hf, foot_L=(-0.04, 0.12, 0.0), fp_L=24, fyaw_L=-6,
        root=(0, -0.02, -0.06), hips=(0, -12, 0), head=(-4, -14, 0))
    c.k(30, hand_R=(0.24, 0.12, 1.98), hdir_R=(-0.3, 0.2, 1), palm_R=(0, 1, 0), hand_L=(0.5, 0.1, 1.2),
        chest=(-6, -8, 4), head=(-12, -10, 0))
    c.k(46, hand_R=(0.52, 0.12, 1.22), hdir_R=(1, 0.2, 0), palm_R=(0, 0, -1), hand_L=(0.26, 0.16, 1.9),
        hdir_L=(-0.4, 0.2, 1), palm_L=(0, 1, 0), hips=(0, 12, 0), chest=(-6, 8, -4), head=(-12, 12, 0),
        foot_L=(0, 0, 0), fp_L=0, foot_R=(-0.04, 0.12, 0), fp_R=24)
    c.k(62, hand_R=(0.34, 0.3, 1.5), hand_L=(0.34, 0.3, 1.5), hdir=(0.3, 1, 0.3), palm=(0, 0, -1),
        hips=(0, 0, 0), chest=(0, 0, 0), head=(-4, 0, 0), foot_R=(0, 0, 0), fp_R=0)
    c.hold(74)
    c.kd(90, REST)

    c = emote("dance_2", 84, lag=1.4)       # the turn: a full spin with open arms
    arms = dict(hand=(0.56, 0.06, 1.42), hw=1.0, hdir=(1, 0, 0.1), palm=(0, 0.4, -1), fg=hf, elb=(0.3, -1, 0))
    c.k(12, root=(0, 0, -0.06), fp=16, **arms)
    for i, f in enumerate((24, 36, 48, 60)):
        yaw = 90 * (i + 1)
        c.k(f, hips=(0, yaw, 0), fyaw=6 + yaw, root=(0, 0, -0.03 + 0.02 * (i % 2)),
            hand_L=(0.56, 0.06, 1.42 + (0.12 if i % 2 else -0.08)),
            hand_R=(0.56, 0.06, 1.42 - (0.12 if i % 2 else -0.08)))
    c.k(68, hips=(0, 360, 0), fyaw=366, fp=0, hand=(0.4, 0.2, 1.2), root=(0, 0, -0.04))
    c.kd(84, {**REST, "hips": (0, 360, 0), "fyaw_L": 364, "fyaw_R": 364})

    c = emote("dance_3", 96, lag=1.4)       # the low bend with a sweeping sleeve
    c.k(16, root=(0, -0.02, -0.34), foot_L=(0.06, 0.24, 0), foot_R=(0.1, -0.24, 0), fp_R=40, fyaw_R=30,
        knee=(0.4, 1, 0), hips=(16, -10, 0), spine=(14, 0, -12), chest=(8, 0, -8), head=(4, -10, -10),
        hand_R=(0.3, 0.46, 0.5), hs_R=1.0, hw=1.0, hdir_R=(-0.6, 1, -0.4), palm_R=(0, 0, -1),
        hand_L=(0.46, -0.3, 1.8), hdir_L=(0.3, -0.5, 1), palm_L=(0, -1, 0), fg=hf)
    c.k(36, hand_R=(-0.2, 0.5, 0.52), hdir_R=(-1, 0.4, -0.3), spine=(14, 0, -4), head=(4, 10, -4))
    c.k(56, root=(0, 0, -0.06), foot_L=(0.02, 0.12, 0), foot_R=(0.04, -0.08, 0), fp_R=10, hips=(-4, 10, 0),
        spine=(-6, 0, 6), chest=(-8, 0, 4), head=(-12, 10, 0), hand_R=(0.4, 0.2, 1.9), hs_R=0.0,
        hdir_R=(0, 0.2, 1), palm_R=(0, 1, 0), hand_L=(0.5, 0.1, 1.2), hdir_L=(1, 0, 0), palm_L=(0, 0, -1))
    c.hold(72)
    c.kd(96, REST)

    c = emote("dance_4", 90, lag=1.4)       # finale: fold in, open wide, curtsey pose
    c.k(14, hand=(-0.05, 0.22, 1.36), hw=1.0, hdir=(-1, 0.2, 0.3), palm=(0, -1, 0), fg=hf,
        elb=(0.9, -0.2, -0.6), head=(10, 0, 0), sh=(6, 6), root=(0, 0, -0.05))
    c.k(30, hand_L=(0.62, 0.2, 1.5), hand_R=(0.58, 0.1, 1.2), hdir_L=(1, 0.3, 0.4), hdir_R=(1, 0.1, -0.3),
        palm=(0, 0.5, -1), head=(-10, 16, 0), chest=(-8, 6, 0), sh=(0, 0), foot_R=(-0.12, -0.14, 0), fp_R=40,
        fyaw_R=10, root=(0, -0.03, -0.14), knee=(0.3, 1, 0))
    c.hold(58)
    c.k(66, hand=(0.235, 0.1, 0.95), hw=0.0, head=(8, 0, 0), chest=(4, 0, 0), foot_R=(-0.02, -0.04, 0), fp_R=0,
        root=(0, 0, -0.1), hips=(10, 0, 0), spine=(4, 0, 0))
    c.kd(90, REST)

    # ---- victory poses
    c = emote("victory_1", 64)
    c.k(10, foot_L=(0.08, 0.04, 0), foot_R=(0.08, -0.02, 0), root=(0, 0, -0.06), hand_R=(0.14, 0.08, 1.96),
        hw_R=1.0, hdir_R=(0, 0, 1), palm_R=(-1, 0, 0), fg_R="fist", elb_R=(1, -0.2, -0.2), head=(-12, -6, 0),
        chest=(-6, 0, 0), hand_L=(0.2, -0.02, 1.08), hw_L=1.0, hdir_L=(0, 1, 0), palm_L=(0, 0, 1), fg_L="fist")
    c.k(18, hand_R=(0.14, 0.08, 1.9))
    c.k(24, hand_R=(0.14, 0.08, 1.98))
    c.hold(46)
    c.kd(64, REST)

    c = emote("victory_2", 72)            # composed immortal: hands behind the back, chin up
    c.k(14, hand=(0.06, -0.16, 1.06), hw=1.0, hdir=(-1, -0.2, -0.2), palm=(0, -1, 0), fg="loose_fist",
        elb=(0.7, -1, 0.2), head=(-8, 14, 0), chest=(-3, 4, 0), foot_L=(0.0, 0.1, 0), fyaw_L=20)
    c.hold(56)
    c.kd(72, REST)

    c = emote("victory_3", 72, lag=1.2)   # qi flourish ending in a crossed sword-seal
    c.k(10, hand_R=(0.3, 0.3, 1.1), hand_L=(0.3, 0.3, 1.5), hw=1.0, hdir=(0.2, 1, 0), palm=(0, 0, -1), fg="seal")
    c.k(20, hand_R=(0.4, 0.2, 1.5), hand_L=(0.36, 0.3, 1.08), hips=(0, 10, 0))
    c.k(30, hand_R=(0.08, 0.3, 1.46), hand_L=(0.06, 0.28, 1.4), hdir_R=(-0.7, 0.2, 0.7), hdir_L=(-0.7, 0.2, 0.7),
        palm_R=(0, 1, 0), palm_L=(0, 1, 0), hips=(0, 0, 0), root=(0, 0, -0.08), foot_L=(0.06, 0.1, 0),
        head=(-4, 0, 0))
    c.hold(56)
    c.kd(72, REST)

    # ---- idle fidgets
    c = emote("idle_look", 72)
    c.k(12, head=(-4, 38, 0), neck=(0, 10, 0), chest=(0, 4, 0))
    c.hold(34)
    c.k(50, head=(0, 0, 0), neck=(0, 0, 0), chest=(0, 0, 0))
    c.kd(72, REST)

    c = emote("idle_shift_weight", 84)
    c.k(20, root=(-0.045, 0, -0.02), hips=(0, -3, 5), spine=(0, 0, -3), chest=(0, 0, -2), head=(0, 0, 2),
        foot_L=(0.0, 0.05, 0.0), fp_L=12, tc_L=1.0)
    c.hold(52)
    c.k(70, root=(0.0, 0, -0.014), hips=(0, 0, 0), spine=(0, 0, 0), chest=(0, 0, 0), head=(0, 0, 0), fp_L=0,
        foot_L=(0, 0, 0))
    c.kd(84, REST)

    c = emote("idle_adjust_sleeve", 84)
    c.k(12, hand_L=(0.12, 0.3, 1.2), hw_L=1.0, hdir_L=(-0.3, 1, 0), palm_L=(0, 0, -1), fg_L="relaxed",
        hand_R=(-0.06, 0.28, 1.24), hw_R=1.0, hdir_R=(-1, 0.4, 0), palm_R=(0, 0, -1), fg_R="pinch",
        elb=(0.8, -0.4, -0.6), head=(18, 10, 0))
    c.k(22, hand_R=(-0.02, 0.2, 1.24))
    c.k(30, hand_R=(-0.06, 0.28, 1.24))
    c.k(40, hand_R=(-0.02, 0.2, 1.23))
    c.k(50, hand_L=(0.2, 0.22, 1.12), hand_R=(0.12, 0.2, 1.14), head=(4, 0, 0), fg_R="soft")
    c.kd(84, REST)

    c = emote("idle_stretch", 84)
    c.k(14, head=(0, 0, 16), neck=(0, 0, 6), sh_R=(6, 0))
    c.k(28, head=(-12, 0, 0), neck=(-4, 0, 0), sh=(8, -4))
    c.k(42, head=(0, 0, -16), neck=(0, 0, -6), sh=(2, 6), sh_R=(0, 6))
    c.k(56, head=(4, 0, 0), neck=(0, 0, 0), sh=(0, 0))
    c.kd(84, REST)

    # ---- talking variants (loops, played during dialogue)
    c = emote("talk_explain", 96, loop=True, extra=breath(96, 1.0))
    c.k(0, hand=(0.18, 0.26, 1.14), hw=1.0, hdir=(0.2, 1, 0.2), palm=(-0.3, 0, 1), fg="open",
        elb=(0.7, -0.6, -0.5), head=(0, 0, 0))
    c.k(20, hand=(0.3, 0.3, 1.2), head=(4, 6, 0), chest=(2, 0, 0))
    c.k(40, hand_L=(0.16, 0.24, 1.12), hand_R=(0.26, 0.34, 1.22), head=(-2, -6, 0), chest=(0, -4, 0))
    c.k(64, hand=(0.12, 0.3, 1.16), palm=(-0.6, 0, 1), head=(3, 0, 2), chest=(1, 2, 0))
    c.k(80, hand=(0.24, 0.24, 1.12), head=(0, 4, 0))

    c = emote("talk_emphatic", 60, loop=True, extra=breath(60, 1.2))
    c.k(0, hand_L=(0.08, 0.3, 1.2), hw=1.0, hdir_L=(-0.4, 0.5, 1), palm_L=(-1, 0, 0), fg_L="flat",
        hand_R=(0.06, 0.32, 1.34), hdir_R=(-0.6, 0.6, 0.3), palm_R=(0, 0, -1), fg_R="fist",
        elb=(0.8, -0.4, -0.6), chest=(-3, 0, 0), head=(-4, 0, 0))
    c.k(10, hand_R=(0.06, 0.3, 1.24), chest=(4, 4, 0), head=(8, 4, 0), spine=(3, 0, 0))
    c.k(18, hand_R=(0.14, 0.34, 1.38), chest=(-2, -3, 0), head=(-4, -4, 0), spine=(0, 0, 0))
    c.k(40, hand_R=(0.06, 0.3, 1.24), chest=(5, -4, 0), head=(9, -4, 0), spine=(3, 0, 0))
    c.k(50, hand_R=(0.08, 0.33, 1.34), chest=(-3, 0, 0), head=(-4, 0, 0), spine=(0, 0, 0))

    c = emote("talk_listen", 120, loop=True, extra=breath(120, 1.0))
    c.k(0, hand_L=(0.04, 0.2, 1.06), hand_R=(0.02, 0.22, 1.08), hw=1.0, hdir_L=(-1, 0.2, -0.2),
        hdir_R=(-1, 0.3, -0.1), palm_L=(0, 0.3, 1), palm_R=(0, -0.3, -1), fg="soft", elb=(0.7, -0.6, -0.5),
        root=(0.02, 0, -0.02), hips=(0, 0, 3), head=(2, 4, 6))
    c.k(36, head=(8, 4, 5))
    c.k(42, head=(0, 4, 5))
    c.k(48, head=(6, 4, 4))
    c.k(60, head=(2, -4, 4))
    c.k(96, head=(9, -2, 3))
    c.k(104, head=(1, 0, 5))
    return out


def clips(fem):
    out = []
    out += loco(fem)
    out += combat(fem)
    out += cultivation(fem)
    out += social(fem)
    return out


# --------------------------------------------------------------------------
# GLB keyframe reduction (run on the exported protagonist files)
# --------------------------------------------------------------------------
def _reduce(t, v, tol):
    """Indices of samples to keep so linear interpolation stays within tol."""
    import numpy as np
    n = len(t)
    if n <= 2:
        return list(range(n))
    keep = [0]
    a = 0
    while a < n - 1:
        best = a + 1
        j = a + 2
        while j < n:
            u = ((t[a + 1:j] - t[a]) / (t[j] - t[a]))[:, None]
            if np.abs(v[a] + (v[j] - v[a]) * u - v[a + 1:j]).max() > tol:
                break
            best = j
            j += 1
        keep.append(best)
        a = best
    return keep


def optimize_glb(path, rot_tol=0.0012, pos_tol=0.0006, other_tol=0.002):
    """Rewrite a GLB so every LINEAR animation channel keeps only the keys
    needed to reproduce it within tolerance (each channel gets its own time
    input), instead of the exporter's dense per-frame sampling."""
    import json
    import struct

    import numpy as np
    data = open(path, "rb").read()
    jlen = struct.unpack_from("<I", data, 12)[0]
    g = json.loads(data[20:20 + jlen])
    boff = 20 + jlen
    blen = struct.unpack_from("<I", data, boff)[0]
    binary = data[boff + 8:boff + 8 + blen]
    acc, views = g["accessors"], g["bufferViews"]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

    def read(ai):
        a = acc[ai]
        bv = views[a["bufferView"]]
        k = ncomp[a["type"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(binary, dtype="<f4", count=a["count"] * k, offset=off).reshape(a["count"], k)

    anim_acc = set()
    for an in g.get("animations", []):
        for smp in an["samplers"]:
            anim_acc.update((smp["input"], smp["output"]))
    out = bytearray()
    new_views, vmap = [], {}
    used = {a["bufferView"] for i, a in enumerate(acc) if i not in anim_acc and "bufferView" in a}
    used.update(img["bufferView"] for img in g.get("images", []) if "bufferView" in img)
    for vi, bv in enumerate(views):
        if vi not in used:
            continue
        while len(out) % 4:
            out.append(0)
        o = bv.get("byteOffset", 0)
        vmap[vi] = len(new_views)
        new_views.append(dict(bv, byteOffset=len(out)))
        out += binary[o:o + bv["byteLength"]]
    new_acc, amap = [], {}
    for ai, a in enumerate(acc):
        if ai in anim_acc:
            continue
        na = dict(a)
        if "bufferView" in na:
            na["bufferView"] = vmap[na["bufferView"]]
        amap[ai] = len(new_acc)
        new_acc.append(na)

    while len(out) % 4:
        out.append(0)
    anim_start = len(out)
    anim_view = len(new_views)
    new_views.append({"buffer": 0, "byteOffset": anim_start, "byteLength": 0})
    shared = {}

    def put(arr, minmax=False):
        raw = np.ascontiguousarray(arr, dtype="<f4").tobytes()
        if minmax and raw in shared:            # identical key times: share the input
            return shared[raw]
        a = {"bufferView": anim_view, "byteOffset": len(out) - anim_start, "componentType": 5126,
             "count": len(arr), "type": {1: "SCALAR", 3: "VEC3", 4: "VEC4"}[arr.shape[1]]}
        out.extend(raw)
        if minmax:
            a["min"] = [float(arr.min())]
            a["max"] = [float(arr.max())]
        new_acc.append(a)
        if minmax:
            shared[raw] = len(new_acc) - 1
        return len(new_acc) - 1

    nodes = g.get("nodes", [])
    defaults = {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}

    for an in g.get("animations", []):
        paths = {ch["sampler"]: ch["target"]["path"] for ch in an["channels"]}
        # drop channels that only hold the node's rest value (scale, bone offsets)
        drop = set()
        for ch in an["channels"]:
            tg = ch["target"]
            v = read(an["samplers"][ch["sampler"]]["output"]).astype(np.float64)
            rest = np.array(nodes[tg["node"]].get(tg["path"], defaults.get(tg["path"], [0])), dtype=np.float64)
            if tg["path"] in defaults and v.shape[1] == len(rest):
                d = np.abs(v - rest).max()
                if tg["path"] == "rotation":
                    d = min(d, np.abs(v + rest).max())
                if d < 1e-5:
                    drop.add(ch["sampler"])
        if drop and len(drop) < len(an["samplers"]):
            keep = [i for i in range(len(an["samplers"])) if i not in drop]
            remap = {o: n for n, o in enumerate(keep)}
            an["samplers"] = [an["samplers"][i] for i in keep]
            an["channels"] = [dict(ch, sampler=remap[ch["sampler"]]) for ch in an["channels"]
                              if ch["sampler"] in remap]
            paths = {remap[k]: v for k, v in paths.items() if k in remap}
        for si, smp in enumerate(an["samplers"]):
            t = read(smp["input"])[:, 0].astype(np.float64)
            v = read(smp["output"]).astype(np.float64)
            if smp.get("interpolation", "LINEAR") == "LINEAR" and len(t) == len(v):
                pth = paths.get(si, "")
                if pth == "rotation":
                    for i in range(1, len(v)):
                        if np.dot(v[i], v[i - 1]) < 0:
                            v[i] = -v[i]
                tol = rot_tol if pth == "rotation" else pos_tol if pth == "translation" else other_tol
                idx = _reduce(t, v, tol)
                t, v = t[idx], v[idx]
            smp["input"] = put(t.reshape(-1, 1), True)
            smp["output"] = put(v)
    for m in g.get("meshes", []):
        for p in m["primitives"]:
            p["attributes"] = {k: amap[i] for k, i in p["attributes"].items()}
            if "indices" in p:
                p["indices"] = amap[p["indices"]]
            if "targets" in p:
                p["targets"] = [{k: amap[i] for k, i in tg.items()} for tg in p["targets"]]
    for sk in g.get("skins", []):
        if "inverseBindMatrices" in sk:
            sk["inverseBindMatrices"] = amap[sk["inverseBindMatrices"]]
    for img in g.get("images", []):
        if "bufferView" in img:
            img["bufferView"] = vmap[img["bufferView"]]
    new_views[anim_view]["byteLength"] = len(out) - anim_start
    g["accessors"], g["bufferViews"] = new_acc, new_views
    while len(out) % 4:
        out.append(0)
    g["buffers"][0]["byteLength"] = len(out)
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(out)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(js), b"JSON"))
        f.write(js)
        f.write(struct.pack("<I4s", len(out), b"BIN\0"))
        f.write(out)
    return total

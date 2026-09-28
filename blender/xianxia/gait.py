"""Procedural, biomechanically driven locomotion (walk / run / sprint ...).

Every humanoid's `walk` / `run` (characters.build_actions) and the heroes'
`sprint`, `sneak`, `crouch_walk`, `walk_back`, `strafe_l/r` (moves.loco) come
from here.  Authored ground speeds (m/s) at speed_scale 1 - the runtime sets
speed_scale = planar_speed / authored_speed:

    walk 1.6   run 4.6   sprint 6.2   sneak 1.0   crouch_walk 0.8
    walk_back 1.0   strafe_l / strafe_r 1.0

Biomechanics (adult gait-lab data; Perry & Burnfield, Novacheck 1998, Winter):
* cadence from leg length (Froude-scaled step length): a 1.8 m adult walks
  1.6 m/s at ~130 steps/min (step 0.74 m) and runs 4.6 m/s at ~180
  steps/min; shorter legs step faster, the golem lumbers.
* duty factor: walk 0.59 (10% double support), run 0.27, sprint 0.22 (flight
  phases); the short, anime-proportioned feet of the rig cap stance length,
  so runs use trained-runner duty factors rather than 0.35.
* foot: heel rocker (heel strike 20 deg toes-up in walk, 8 deg in run,
  forefoot strike in sprint) -> foot flat by 12% of the cycle -> heel rise from
  ~30% about the ball -> toe rocker (tip planted, toes extending ~26 deg) ->
  toe-off at 45-50 deg heel rise; toes lift into heel strike.
* knee: walk ~20-25 deg loading response, ~10 deg mid-stance, 62 deg peak at
  75% of the cycle; run 40-45 deg mid-stance, 106 deg swing (sprint 121).
* pelvis: height solved from the stance legs (walk: highest mid-stance,
  lowest at double support, ~5 cm; run: low through stance, ballistic
  flight); rotation +-4.5 deg (female 6.5), obliquity +-3.2 (female 4.5),
  anterior tilt twice a stride, lateral weight shift over the stance foot.
* thorax counter-rotates against the pelvis, head stabilised in yaw / roll and
  held level; arms swing counter to the same-side leg with the elbow flexing
  late on the forward swing and wrist / fingers trailing (walk 15 deg swing,
  run 40 deg with ~90 deg elbows); relaxed hands walking, loose fists running.
* female: narrower base (feet near the line of progression), more pelvic
  rotation, less arm swing, upright chest; elders stoop; the golem walks wide.
* hair chains (any bone hanging off the solved body) get damped-pendulum
  follow-through driven by the head's acceleration and the travel speed.

verify_clip() measures the baked result (stance slip, loop seam, knees, floor
penetration) and the build fails when a planted foot slips more than 2 cm.
"""
import math

from mathutils import Quaternion, Vector

V = Vector
FPS = 30


# --------------------------------------------------------------------------
# verification: sample the baked action and measure what the player sees
# --------------------------------------------------------------------------
_CHAIN = ("hips", "thigh", "shin", "foot", "toe")


def _fcurves(act):
    """{(data_path, index): fcurve} for an action (layered or legacy)."""
    out = {}
    fcs = getattr(act, "fcurves", None)
    if fcs is None or len(fcs) == 0:
        fcs = []
        for layer in getattr(act, "layers", []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    fcs.extend(bag.fcurves)
    for fc in fcs:
        out[(fc.data_path, fc.array_index)] = fc
    return out


class _Sampler:
    """Evaluates the leg chains of an action straight from its f-curves
    (no depsgraph, so it is fast and independent of the scene frame)."""

    def __init__(self, arm, act):
        self.arm = arm
        self.fc = _fcurves(act)
        self.rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}
        f0, f1 = act.frame_range
        self.f0, self.f1 = float(f0), float(f1)

    def basis(self, name, f):
        """Local pose matrix at frame f as the game plays it: the exporter
        samples whole frames and Godot interpolates linearly between them."""
        fl = math.floor(f)
        u = f - fl
        if u < 1e-6:
            return self._basis(name, fl)
        a, b = self._basis(name, fl), self._basis(name, fl + 1)
        qa_, qb = a.to_quaternion(), b.to_quaternion()
        m = qa_.slerp(qb, u).to_matrix().to_4x4()
        m.translation = a.translation.lerp(b.translation, u)
        return m

    def _basis(self, name, f):
        q = [1.0, 0.0, 0.0, 0.0]
        loc = [0.0, 0.0, 0.0]
        pq = f'pose.bones["{name}"].rotation_quaternion'
        pl = f'pose.bones["{name}"].location'
        for i in range(4):
            c = self.fc.get((pq, i))
            if c is not None:
                q[i] = c.evaluate(f)
        for i in range(3):
            c = self.fc.get((pl, i))
            if c is not None:
                loc[i] = c.evaluate(f)
        m = Quaternion(q).normalized().to_matrix().to_4x4()
        m.translation = V(loc)
        return m

    def pose(self, names, f):
        M = {}

        def get(n):
            if n in M:
                return M[n]
            p = self.parent[n]
            b = self.basis(n, f)
            if p is None:
                M[n] = self.rest[n] @ b
            else:
                M[n] = get(p) @ (self.rest[p].inverted() @ self.rest[n]) @ b
            return M[n]
        for n in names:
            get(n)
        return M


def verify_clip(arm, act, speed, direction=(0.0, 1.0), scale=1.0, loop=True, samples_per_frame=4,
                label=None, verbose=True):
    """Measure foot planting / loop / knee quality of a baked locomotion clip.

    speed: authored ground speed in m/s; direction: (left, forward) unit
    vector of travel in the character's frame.  Every foot contact point
    (heel, ball, toe tip) within 1.5 mm of its lowest height is "in contact";
    while in contact, a planted point must not move relative to the ground,
    which itself slides backwards under the in-place character at `speed`.

    Returns a dict: slip (max metres a contact point moves while in contact
    at the authored speed), implied_speed (the stance-phase ground speed the
    feet actually show), slip_implied (slip at that speed), loop_rot (deg),
    loop_loc (m), loop_vel (deg/frame velocity jump at the seam), knee_min /
    knee_max (deg flexion, negative = hyper-extended), penetration (m below
    the floor, positive = through it).
    """
    smp = _Sampler(arm, act)
    f0, f1 = smp.f0, smp.f1
    length = f1 - f0
    sides = [sd for sd in ("L", "R") if f"foot.{sd}" in smp.rest]
    names = []
    for sd in sides:
        names += [f"thigh.{sd}", f"shin.{sd}", f"foot.{sd}", f"toe.{sd}"]
    # travel direction in armature space (character faces -Y, left is +X)
    dirv = V((direction[0], -direction[1], 0.0))
    if dirv.length > 0:
        dirv.normalize()
    # contact points in each bone's rest space
    pts = {}
    for sd in sides:
        ft = smp.rest[f"foot.{sd}"]
        to = smp.rest[f"toe.{sd}"]
        a0 = ft.translation.copy()
        heel = V((a0.x, a0.y + 0.034 * scale, 0.004 * scale))
        ball = to.translation.copy()
        tip = to @ V((0.0, arm.data.bones[f"toe.{sd}"].length, 0.0))
        pts[sd] = {
            "heel": (f"foot.{sd}", ft.inverted() @ heel, heel.z),
            "ball": (f"toe.{sd}", V((0, 0, 0)), ball.z),
            "tip": (f"toe.{sd}", V((0.0, arm.data.bones[f"toe.{sd}"].length, 0.0)), tip.z),
        }
    n = max(2, int(round(length * samples_per_frame)))
    cycles = 2 if loop else 1
    ts = [f0 + length * i / n for i in range(n * cycles + (0 if loop else 1))]
    track = {(sd, k): [] for sd in sides for k in ("heel", "ball", "tip")}
    knees = []
    for t in ts:
        ft = f0 + ((t - f0) % length if loop else (t - f0))
        if not loop:
            ft = min(ft, f1)
        M = smp.pose(names, ft)
        for sd in sides:
            for k, (bn, lp, rz) in pts[sd].items():
                p = M[bn] @ lp
                track[(sd, k)].append((t, p, rz))
            hip = M[f"thigh.{sd}"].translation
            kn = M[f"shin.{sd}"].translation
            an = M[f"foot.{sd}"].translation
            a, b = (kn - hip), (an - kn)
            ang = math.degrees(a.angle(b)) if a.length > 1e-6 and b.length > 1e-6 else 0.0
            if a.cross(b).dot(V((1, 0, 0))) < 0 and a.cross(b).length > 1e-6:
                ang = -ang
            knees.append(ang)
    dt = length / n / FPS

    def planted_runs(tr, v, trim):
        """Worst drift of a point across its contact runs (contact = within
        1.5 mm of the lowest height it reaches), measured against the ground
        sliding back at speed v.  `trim` samples are dropped at both ends of
        each run: touchdown / lift-off transients (a heel skims the floor for
        a moment before it plants), so what is left is the stance itself."""
        zmin = min(p.z for _, p, _ in tr)
        thr = zmin + 0.0015 * scale
        runs, cur = [], []
        for t, p, _ in tr:
            if p.z <= thr:
                w = p + dirv * (v * (t - f0) / FPS)
                w.z = 0.0
                cur.append(w)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        worst = 0.0
        for r in runs:
            if loop and (r is runs[0] or r is runs[-1]) and len(runs) > 1:
                continue     # clipped by the sampling window, measured in the other cycle
            if trim and len(r) > 2 * trim + 1:
                r = r[trim:-trim]
            if len(r) < 2:
                continue
            c0 = r[0]
            worst = max(worst, max((w - c0).length for w in r))
        return worst

    # implied ground speed: median backward velocity of the lowest foot point
    vel = []
    for sd in sides:
        tr = track[(sd, "ball")]
        zmin = min(p.z for _, p, _ in tr)
        for i in range(1, len(tr)):
            if tr[i][1].z <= zmin + 0.01 * scale and tr[i - 1][1].z <= zmin + 0.01 * scale:
                d = (tr[i][1] - tr[i - 1][1])
                vel.append(-d.dot(dirv) / dt)
    vel.sort()
    implied = vel[len(vel) // 2] if vel else 0.0
    half = max(1, samples_per_frame // 2)          # half a frame
    per = {k: planted_runs(tr, speed, half) for k, tr in track.items()}
    slip = max(per.values())
    if verbose and slip > 0.005:
        print("      slip per point (cm):", {f"{a}.{b}": round(x * 100, 2) for (a, b), x in per.items()})
    scuff = max(planted_runs(tr, speed, 0) for tr in track.values())
    slip_imp = max(planted_runs(tr, implied, half) for tr in track.values())
    pen = 0.0
    for (sd, k), tr in track.items():
        pen = max(pen, max(rz - p.z for _, p, rz in tr))
    # loop continuity on every animated channel: the pose gap at the seam,
    # and a velocity kink = the seam's second difference minus the larger of
    # its two neighbours' (a seam defect is a one-sample spike; a hard but
    # smooth event such as a landing spans several samples)
    lrot = lloc = lvel = 0.0
    kink_at = ""
    if loop:
        groups = {}
        for (path, idx), c in smp.fc.items():
            groups.setdefault(path, {})[idx] = c
        nf = int(round(length))
        for path, cs in groups.items():
            idx = sorted(cs)
            vals = [[cs[i].evaluate(f0 + k) for i in idx] for k in range(nf + 1)]
            a, b = vals[0], vals[-1]
            if path.endswith("rotation_quaternion") and len(idx) == 4:
                qs = [Quaternion(v) for v in vals[:-1]]
                lrot = max(lrot, math.degrees(Quaternion(a).rotation_difference(Quaternion(b)).angle))
                inc = [qs[k].rotation_difference(qs[(k + 1) % nf]) for k in range(nf)]
                d2 = [math.degrees(inc[k - 1].rotation_difference(inc[k]).angle) for k in range(nf)]
            elif path.endswith("location"):
                lloc = max(lloc, max(abs(x - y) for x, y in zip(a, b)))
                d2 = [0.0] * nf
                for c in range(len(idx)):
                    ser = [v[c] for v in vals[:-1]]
                    for k in range(nf):
                        d2[k] = max(d2[k], 100.0 * abs(ser[(k + 1) % nf] - 2 * ser[k] + ser[k - 1]))
            else:
                continue
            kink = d2[0] - max(d2[1], d2[-1])
            if kink > lvel:
                lvel, kink_at = kink, path
    res = dict(slip=slip, scuff=scuff, implied_speed=implied, slip_implied=slip_imp, loop_rot=lrot, loop_loc=lloc,
               loop_vel=lvel, knee_min=min(knees), knee_max=max(knees), penetration=pen)
    res["kink_at"] = kink_at
    if verbose:
        where = ""
        if lvel > 0.5 and '"' in kink_at:
            where = " (" + kink_at.split('"')[1] + ")"
        print(f"    verify {label or act.name:<14} v={speed:4.2f} slip={slip * 100:5.2f}cm scuff={scuff * 100:4.2f}cm "
              f"(feet imply {implied:4.2f} m/s, slip there {slip_imp * 100:5.2f}cm) "
              f"loop={lrot:4.2f}deg/{lloc * 1000:3.1f}mm kink={lvel:4.2f}{where} "
              f"knee={res['knee_min']:5.1f}..{res['knee_max']:5.1f}deg pen={pen * 100:4.2f}cm")
    return res


# ==========================================================================
# the generator
# ==========================================================================
G = 9.81
AXV, AYV, AZV = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def sm(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _hermite(p0, p1, m0, m1, u):
    u2, u3 = u * u, u * u * u
    return p0 * (2 * u3 - 3 * u2 + 1) + m0 * (u3 - 2 * u2 + u) + p1 * (-2 * u3 + 3 * u2) + m1 * (u3 - u2)


class Path:
    """C1 cubic Hermite spline through keys [(w, value)] (floats or Vectors),
    with prescribed end slopes (d value / d w) and non-uniform Catmull-Rom
    tangents at the interior keys."""

    def __init__(self, keys, s0, s1):
        self.w = [k[0] for k in keys]
        self.p = [k[1] for k in keys]
        n = len(keys)
        self.m = []
        for i in range(n):
            if i == 0:
                self.m.append(s0)
            elif i == n - 1:
                self.m.append(s1)
            else:
                self.m.append((self.p[i + 1] - self.p[i - 1]) * (1.0 / (self.w[i + 1] - self.w[i - 1])))

    def __call__(self, w):
        i = 0
        while i < len(self.w) - 2 and w > self.w[i + 1]:
            i += 1
        h = self.w[i + 1] - self.w[i]
        u = max(0.0, min(1.0, (w - self.w[i]) / h))
        return _hermite(self.p[i], self.p[i + 1], self.m[i] * h, self.m[i + 1] * h, u)


class Loop:
    """Periodic C1 (Catmull-Rom) interpolation of N samples over phase [0, 1)."""

    def __init__(self, vals):
        self.v = list(vals)

    def __call__(self, ph):
        n = len(self.v)
        x = (ph % 1.0) * n
        i = int(x) % n
        u = x - int(x)
        p0, p1, p2, p3 = self.v[(i - 1) % n], self.v[i], self.v[(i + 1) % n], self.v[(i + 2) % n]
        return _hermite(p1, p2, (p2 - p0) * 0.5, (p3 - p1) * 0.5, u)


def _lowpass(vals, harmonics):
    """Keep the first `harmonics` Fourier terms of a periodic sample list."""
    n = len(vals)
    out = [sum(vals) / n] * n
    for k in range(1, harmonics + 1):
        c = sum(v * math.cos(2 * math.pi * k * i / n) for i, v in enumerate(vals)) * 2 / n
        d = sum(v * math.sin(2 * math.pi * k * i / n) for i, v in enumerate(vals)) * 2 / n
        for i in range(n):
            out[i] += c * math.cos(2 * math.pi * k * i / n) + d * math.sin(2 * math.pi * k * i / n)
    return out


def _blur(vals, sigma):
    """Circular Gaussian blur of a periodic sample list."""
    n = len(vals)
    if sigma <= 0:
        return list(vals)
    r = int(3 * sigma) + 1
    w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    tw = sum(w)
    return [sum(vals[(i + k) % n] * w[k + r] for k in range(-r, r + 1)) / tw for i in range(n)]


def _pw(keys, x):
    """Piecewise-smoothstep interpolation of [(x, y)] keys (clamped)."""
    if x <= keys[0][0]:
        return keys[0][1]
    for (x0, y0), (x1, y1) in zip(keys, keys[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * sm((x - x0) / (x1 - x0))
    return keys[-1][1]


def qa(axis, deg):
    return Quaternion(V(axis).normalized(), math.radians(deg))


def eul(p, y, r):
    """Same convention as moves.eul: (pitch, yaw, roll) degrees."""
    return qa(AZV, y) @ qa(AXV, p) @ qa(AYV, r)


# --------------------------------------------------------------------------
# character style: how this particular person walks
# --------------------------------------------------------------------------
def style(cfg):
    """Per-character modifiers on top of the biomechanical defaults."""
    name = cfg.get("name", "")
    fem = bool(cfg.get("female"))
    age = cfg.get("age", 0.0)
    st = dict(
        fem=fem,
        width=-0.062 if fem else -0.042,     # stance line offset from the hip line (inward -)
        toe_out=4.0 if fem else 7.0,         # foot progression angle
        yaw=6.5 if fem else 4.5,             # pelvic rotation amplitude (deg)
        list=4.5 if fem else 3.2,            # pelvic obliquity amplitude
        sway=0.016 if fem else 0.022,        # lateral weight shift (m, unscaled)
        chest_yaw=3.5 if fem else 5.0,       # thoracic counter-rotation (world)
        arm=0.72 if fem else 1.0,            # arm swing scale
        abduct=11.0 if fem else 8.0,         # arms carried clear of the robe
        elbow=4.0 if fem else 0.0,           # extra elbow flexion (soft, carried arms)
        chest_up=-2.5 if fem else -1.5,      # upright chest (negative pitch)
        stoop=0.0, heavy=0.0, swagger=0.0, step=1.0, gaze=-1.5,
        fingers="soft" if fem else "relaxed",
    )
    if age > 0.6:                            # elder: slight stoop, smaller steps, restrained arms
        st.update(stoop=1.0, step=0.96, arm=0.6, yaw=3.5, sway=0.024, chest_yaw=3.0, gaze=-4.0)
    if name == "stone_golem":                # heavy lumbering stone body
        st.update(heavy=1.0, width=0.02, toe_out=12.0, yaw=2.0, list=2.0, sway=0.045, chest_yaw=4.0,
                  arm=0.7, abduct=24.0, elbow=10.0, chest_up=4.0, step=0.95)
    if name == "bandit":                     # swagger: shoulders roll, arms out
        st.update(swagger=1.0, chest_yaw=7.5, arm=1.15, abduct=11.0, toe_out=10.0, width=-0.03)
    if name in ("demon_cultivator", "blood_patriarch"):   # stately, arms restrained
        st.update(arm=0.65, chest_up=-3.0, yaw=3.5, chest_yaw=3.5)
    if name == "sect_master":
        st.update(arm=0.6, chest_up=-3.0)
    return st


def leg_len(s):
    return 0.94 * s                          # hip joint height (m)


def cycle_frames(speed, s, kind, st=None):
    """Stride period in frames from the leg length (Froude-scaled step length
    step = k L (Fr / Fr0)^b, calibrated on adult data for a 1.8 m person:
    1.6 m/s walk ~128 steps/min, 4.6 m/s run ~180 steps/min)."""
    k, fr0, b = {"walk": (0.77, 0.527, 0.45), "run": (1.66, 1.515, 0.55), "sprint": (1.95, 2.04, 0.5),
                 "sneak": (0.56, 0.33, 0.45), "crouch": (0.50, 0.26, 0.45), "back": (0.52, 0.33, 0.45),
                 "strafe": (0.27, 0.33, 0.3)}[kind]
    L = leg_len(s)
    fr = speed / math.sqrt(G * L)
    step = k * L * (fr / fr0) ** b * ((st or {}).get("step", 1.0) if kind == "walk" else 1.0)
    return max(8, int(round(FPS * 2.0 * step / speed)))


def preset(kind, st, speed=None):
    """Biomechanical parameters for one gait (angles deg, lengths unscaled m)."""
    fem = st["fem"]
    if kind == "walk":
        p = dict(
            speed=1.6, duty=0.59, mode="fk", fore=0.43, pelvis="auto", harmonics=4,
            strike=20.0, push=48.0, u_ff=0.2, u_ho=0.5, toe_ext=10.0, toe_rocker=(0.86, 26.0),
            kappa=[(0.0, 4.0), (0.2, 16.0), (0.55, 6.0), (1.0, 5.0)],
            swing=[(0.33, 10.0, 60.0, 10.0), (0.67, 25.0, 27.0, 0.0), (0.88, 26.0, 8.0, 0.0)],
            bulge=0.012,
            hips_pitch=2.0, tilt=1.2, spine_pitch=1.0, chest_pitch=st["chest_up"], bounce=0.6,
            arms=dict(c=-4.0, amp=15.0, e0=16.0, ea=22.0, abduct=st["abduct"], psi=0.12, lag=0.05,
                      lag_e=0.05, wr=5.0, sh=2.5, fg=st["fingers"], fg_k=0.0),
        )
    elif kind == "run":
        p = dict(
            speed=4.6, duty=0.27, mode="fk", fore=0.37, pelvis="auto", harmonics=4,
            strike=8.0, push=52.0, u_ff=0.22, u_ho=0.42, toe_ext=6.0, toe_rocker=(0.82, 26.0),
            kappa=[(0.0, 20.0), (0.38, 48.0), (0.8, 22.0), (1.0, 8.0)],
            swing=[(0.1, -15.0, 50.0, 24.0), (0.27, -3.0, 84.0, 12.0), (0.5, 18.0, 106.0, 2.0),
                   (0.78, 44.0, 62.0, -4.0)],
            bulge=0.01,
            hips_pitch=9.0, tilt=2.0, spine_pitch=4.0, chest_pitch=2.0 + st["chest_up"] * 0.5, bounce=2.0,
            arms=dict(c=-4.0, amp=40.0, e0=80.0, ea=18.0, abduct=st["abduct"] + 4.0, psi=0.28, lag=0.03,
                      lag_e=0.04, wr=6.0, sh=4.0, fg="loose_fist", fg_k=0.45 if fem else 0.7),
        )
    elif kind == "sprint":
        p = dict(
            speed=6.2, duty=0.22, mode="fk", fore=0.36, pelvis="auto", harmonics=4,
            strike=-8.0, push=58.0, u_ff=0.25, u_ho=0.3, toe_ext=0.0, toe_rocker=(0.8, 30.0),
            kappa=[(0.0, 22.0), (0.4, 46.0), (0.8, 20.0), (1.0, 8.0)],
            swing=[(0.1, -12.0, 55.0, 24.0), (0.27, 2.0, 94.0, 12.0), (0.48, 28.0, 120.0, 2.0),
                   (0.76, 58.0, 70.0, -4.0)],
            bulge=0.01,
            hips_pitch=0.0, tilt=2.0, spine_pitch=0.0, chest_pitch=0.0, bounce=2.0, arms=None,
        )
    elif kind in ("sneak", "crouch"):
        sneak = kind == "sneak"
        p = dict(
            speed=1.0 if sneak else 0.8, duty=0.7 if sneak else 0.66, mode="cart",
            fore=0.5, pelvis="fixed", bob=0.012 if sneak else 0.016,
            strike=-10.0 if sneak else 6.0, push=24.0 if sneak else 18.0,
            u_ff=0.25, u_ho=0.62, toe_ext=0.0 if sneak else 6.0,
            lift=0.085 if sneak else 0.075, lift_at=0.42, bulge=0.018,
            hips_pitch=0.0, tilt=1.0, spine_pitch=0.0, chest_pitch=0.0, bounce=0.5, arms=None,
        )
    elif kind == "back":
        p = dict(
            speed=1.0, duty=0.62, mode="cart", fore=0.5, pelvis="auto", dir=(0.0, -1.0),
            strike=-14.0, push=-12.0, u_ff=0.25, u_ho=0.6, toe_ext=0.0,
            kappa=[(0.0, 8.0), (0.3, 14.0), (0.7, 8.0), (1.0, 12.0)],
            lift=0.065, lift_at=0.5, bulge=0.012,
            hips_pitch=0.0, tilt=0.8, spine_pitch=0.0, chest_pitch=0.0, bounce=0.4,
            arms=dict(c=-2.0, amp=8.0, e0=22.0, ea=12.0, abduct=st["abduct"] + 2.0, psi=0.12, lag=0.05,
                      lag_e=0.05, wr=4.0, sh=1.5, fg="soft", fg_k=0.0),
        )
    elif kind == "strafe":
        p = dict(
            speed=1.0, duty=0.56, mode="cart", fore=0.5, pelvis="auto",
            strike=0.0, push=6.0, u_ff=0.2, u_ho=0.7, toe_ext=0.0,
            kappa=[(0.0, 12.0), (0.5, 16.0), (1.0, 12.0)],
            lift=0.045, lift_at=0.42, bulge=0.0, min_gap=0.15,
            hips_pitch=0.0, tilt=0.6, spine_pitch=0.0, chest_pitch=0.0, bounce=0.4, arms=None,
        )
    else:
        raise KeyError(kind)
    p["kind"] = kind
    if speed is not None:
        p["speed"] = speed
    p.setdefault("dir", (0.0, 1.0))
    p.setdefault("lift", 0.0)
    return p


# --------------------------------------------------------------------------
# the gait layer: fn(frame, P) on top of a moves.Clip's keyed pose
# --------------------------------------------------------------------------
class Gait:
    """Procedural locomotion layer for one looping clip.

    Works in the rig's unscaled armature space (x = character's left,
    -y = forward, z = up).  Each foot's contact pivot (the heel while the
    toes are up, the ball of the foot while the heel is up, both while flat)
    is locked to the ground: during stance it moves backwards at exactly the
    authored ground speed, so with playback scaled by planar_speed /
    authored_speed the foot never moves against the floor.  Swing is a C1
    spline that leaves and re-joins stance with matching position and
    velocity, shaped through hip/knee angle keys taken from gait-lab data
    (walk, run, sprint) or a Cartesian lift (sneak, crouch, back, strafe).
    The pelvis height is solved from the stance legs (a knee-flexion target
    per stance phase; ballistic during flight), smoothed and clamped to the
    legs' reach.
    """

    def __init__(self, rig, p, st, frames, base=None, arms=True):
        self.rig = rig
        self.p = p
        self.st = st
        self.T = frames
        s = self.s = rig.s
        base = base or {}
        self.base_root = V(base.get("root", (0.0, 0.0, 0.0)))
        self.base_hips = base.get("hips", (0.0, 0.0, 0.0))
        self.use_arms = arms and p.get("arms") is not None
        H = {n: rig.head[n] / s for n in rig.head}
        Tl = {n: rig.tail[n] / s for n in rig.tail}
        self.l1 = (rig.len["thL"] + rig.len["thR"]) / (2 * s)
        self.l2 = (rig.len["shL"] + rig.len["shR"]) / (2 * s)
        self.Tc = frames / FPS                       # stride period (s)
        self.v = p["speed"] / s                      # unscaled ground speed
        dx, df = p["dir"]
        self.dir = V((dx, -df, 0.0)).normalized()   # travel direction (armature)
        self.D = self.v * self.Tc * p["duty"]       # stance travel distance
        self.geo = {}
        for sd in ("L", "R"):
            A0 = H[f"foot.{sd}"].copy()
            self.geo[sd] = dict(A0=A0, B0=H[f"toe.{sd}"].copy(), heel=V((A0.x, A0.y + 0.034, 0.004)),
                                tip=Tl[f"toe.{sd}"].copy(), H0=H[f"thigh.{sd}"].copy(),
                                sg=1 if sd == "L" else -1)
        self.HH = H["hips"].copy()
        self.phase_off = {"L": 0.0, "R": 0.5}
        width = st["width"]
        if p["kind"] == "strafe":
            # side-shuffle: the feet never cross, the gap closes to min_gap
            x0 = (p["min_gap"] + 0.5 * self.v * self.Tc) / 2.0
            width = x0 - abs(self.geo["L"]["A0"].x)
        elif p["kind"] in ("run", "sprint"):
            width = st["width"] - 0.03              # runners land close to the midline
        elif p["kind"] in ("sneak", "crouch"):
            width = st["width"] + 0.035             # crouched: wider base
        self.width = width
        self.yaw = st["toe_out"] * (0.5 if p["kind"] in ("run", "sprint", "strafe") else 1.0)
        self.N = 240
        extra = [None] * self.N
        self._pelvis(extra)
        self._swings()
        for _ in range(3):
            # the swing leg must reach its targets too (terminal swing into
            # heel strike): lower the pelvis where it cannot and re-plan
            lim = self._swing_limits()
            if all(a is None or a >= self.rz(i / self.N) - 1e-4 for i, a in enumerate(lim)):
                break
            extra = [a if b is None else (b if a is None else min(a, b)) for a, b in zip(extra, lim)]
            self._pelvis(extra)
            self._swings()

    # ----------------------------------------------------------------- torso
    def torso(self, ph):
        """Pelvis / spine / head angles (deg) and the root's horizontal motion."""
        p, st = self.p, self.st
        tw = 2 * math.pi
        run = p["kind"] in ("run", "sprint")
        k = 1.0 if p["kind"] in ("walk", "run", "sprint") else 0.5
        yaw_a = st["yaw"] * (1.35 if run else 1.0) * k
        list_a = st["list"] * (1.3 if run else 1.0) * k
        # pelvis: transverse rotation (the swing-side hip leads into its heel
        # strike), obliquity (the swing side drops in loading response) and
        # anterior tilt twice per stride
        hy = -yaw_a * math.cos(tw * (ph - 0.02))
        hr = -list_a * math.sin(tw * (ph + (0.1 if run else 0.13)))
        hp = p["hips_pitch"] + p["tilt"] * math.cos(2 * tw * (ph - 0.1))
        if p["kind"] == "strafe":
            hy, hr = 0.0, 0.5 * list_a * math.sin(tw * ph)
        # thorax counter-rotates against the pelvis (world yaw), slight lag
        cw = st["chest_yaw"] * (1.6 if run else 1.0) * k * math.cos(tw * (ph - 0.04))
        cw *= 1.0 + 0.4 * st["swagger"]
        sp_y = (cw - hy) * 0.45
        ch_y = (cw - hy) * 0.55
        sp_r = -hr * 0.55
        ch_r = -hr * 0.3 - st["swagger"] * 1.5 * math.cos(tw * (ph - 0.1))
        bounce = p["bounce"] * math.cos(2 * tw * (ph - (0.16 if run else 0.1)))
        sp_p = p["spine_pitch"] + 0.5 * bounce + 4.0 * st["stoop"] + 1.5 * st["heavy"]
        ch_p = p["chest_pitch"] + 0.5 * bounce + 3.0 * st["stoop"]
        # head: stabilised in world yaw / roll, gaze held level
        world_p = self.base_hips[0] + hp + sp_p + ch_p
        world_y = hy + sp_y + ch_y
        world_r = hr + sp_r + ch_r
        nk_p = -(world_p - st["gaze"]) * 0.45
        hd_p = -(world_p - st["gaze"]) * 0.35 - 0.6 * bounce
        nk_y, hd_y = -world_y * 0.5, -world_y * 0.4
        nk_r, hd_r = -world_r * 0.5, -world_r * 0.45
        # lateral weight shift over the stance foot, forward surge
        sway = st["sway"] * (0.45 if run else 1.0) * math.cos(tw * (ph - 0.3))
        if p["kind"] == "strafe":
            sway = 0.0
        surge = 0.006 * math.sin(2 * tw * ph) * (0.5 if run else 1.0)
        return dict(hips=(hp, hy, hr), spine=(sp_p, sp_y, sp_r), chest=(ch_p, ch_y, ch_r),
                    neck=(nk_p, nk_y, nk_r), head=(hd_p, hd_y, hd_r), x=sway, f=surge)

    def hip_joint(self, sd, tor, rz):
        br = self.base_root
        root = V((br.x + tor["x"], -(br.y + tor["f"]), br.z + rz))
        hb = self.base_hips
        Wh = eul(hb[0] + tor["hips"][0], hb[1] + tor["hips"][1], hb[2] + tor["hips"][2])
        return self.HH + root + Wh @ (self.geo[sd]["H0"] - self.HH)

    # --------------------------------------------------------------- stance
    def fp_stance(self, u):
        """Foot pitch: heel rocker (toes up -> flat), then heel rise to toe-off."""
        p = self.p
        heel = -p["strike"] * (1.0 - sm(u / p["u_ff"]))
        x = max(0.0, (u - p["u_ho"]) / (1.0 - p["u_ho"]))
        return heel + p["push"] * x * x

    def toe_stance(self, u, fp):
        """Toe extension relative to the foot: flat on the floor while the heel
        is up, lifted a little into heel strike."""
        p = self.p
        ext = p["toe_ext"] * (1.0 - sm(u / p["u_ff"])) if p["strike"] > 0 else 0.0
        return max(fp, 0.0) + ext

    def pivot_off(self, sd, u):
        """Contact pivot offset from rest (unscaled armature) during stance."""
        lat = V((self.geo[sd]["sg"] * self.width, 0.0, 0.0))
        return lat + self.dir * (self.D * (self.p["fore"] - u))

    def _qy(self, sd):
        return qa(AZV, self.geo[sd]["sg"] * self.yaw)

    def ankle(self, sd, off, fp):
        """Rig foot model (moves.Rig.solve): pivot on the ball for fp >= 0,
        on the heel for fp < 0."""
        g = self.geo[sd]
        qy = self._qy(sd)
        rf = qy @ qa(AXV, fp)
        P0 = g["B0"] if fp >= 0 else g["heel"]
        return g["A0"] + off + qy @ (P0 - g["A0"]) + rf @ (g["A0"] - P0)

    def off_from_ankle(self, sd, ank, fp):
        g = self.geo[sd]
        qy = self._qy(sd)
        rf = qy @ qa(AXV, fp)
        P0 = g["B0"] if fp >= 0 else g["heel"]
        return ank - g["A0"] - qy @ (P0 - g["A0"]) - rf @ (g["A0"] - P0)

    def toe_beta(self, u):
        """Toe rocker: pitch of the toe itself (tip planted) late in stance."""
        tr = self.p.get("toe_rocker")
        if not tr or u <= tr[0]:
            return 0.0
        x = (u - tr[0]) / (1.0 - tr[0])
        return tr[1] * x * x

    def stance_state(self, sd, u):
        """(ankle, foot pitch, toe bend) during stance.  Heel rocker, then
        ankle rocker (foot flat), forefoot rocker (heel rises about the
        ball), and finally the toe rocker: the ball lifts too while the toe
        tip stays on the floor and the toes keep extending."""
        fp = self.fp_stance(u)
        off = self.pivot_off(sd, u)
        beta = self.toe_beta(u)
        if beta <= 0.0:
            return self.ankle(sd, off, fp), fp, self.toe_stance(u, fp)
        g = self.geo[sd]
        qy = self._qy(sd)
        ball_flat = g["A0"] + off + qy @ (g["B0"] - g["A0"])
        tip = ball_flat + qy @ (g["tip"] - g["B0"])
        ball = tip - qy @ qa(AXV, beta) @ (g["tip"] - g["B0"])
        ank = ball + qy @ qa(AXV, fp) @ (g["A0"] - g["B0"])
        return ank, fp, fp - beta

    def stance_ankle(self, sd, u):
        return self.stance_state(sd, u)[0]

    # --------------------------------------------------------------- pelvis
    def _reach_z(self, ank, hip, kappa):
        """Highest root z offset (relative to `hip` computed at z 0) at which
        the leg still reaches `ank` with at least `kappa` degrees of knee flexion."""
        L1, L2 = self.l1, self.l2
        d = ank - hip
        lk2 = L1 * L1 + L2 * L2 + 2 * L1 * L2 * math.cos(math.radians(kappa))
        return ank.z - hip.z + math.sqrt(max(lk2 - d.x * d.x - d.y * d.y, 1e-6))

    def _swing_limits(self):
        n = self.N
        out = [None] * n
        duty = self.p["duty"]
        for i in range(n):
            ph = i / n
            tor = self.torso(ph)
            for sd in ("L", "R"):
                lp = (ph - self.phase_off[sd]) % 1.0
                if lp < duty:
                    continue
                ank = self.sw[sd]["ank"]((lp - duty) / (1 - duty))
                z = self._reach_z(ank, self.hip_joint(sd, tor, 0.0), 6.0)
                out[i] = z if out[i] is None else min(out[i], z)
        return out

    def _pelvis(self, extra):
        p = self.p
        n = self.N
        duty = p["duty"]
        hard = list(extra)
        want = [None] * n
        for i in range(n):
            ph = i / n
            tor = self.torso(ph)
            for sd in ("L", "R"):
                lp = (ph - self.phase_off[sd]) % 1.0
                if lp >= duty:
                    continue
                u = lp / duty
                ank = self.stance_ankle(sd, u)
                hip = self.hip_joint(sd, tor, 0.0)
                for kap, arr in ((_pw(p["kappa"], u) if "kappa" in p else None, want), (5.0, hard)):
                    if kap is None:
                        continue
                    z = self._reach_z(ank, hip, kap)
                    arr[i] = z if arr[i] is None else min(arr[i], z)
        if p["pelvis"] == "fixed":
            want = [-p["bob"] * (0.5 + 0.5 * math.cos(4 * math.pi * (i / n - 0.1))) for i in range(n)]
        else:
            want = self._fill_flight(want)
        top = max(h for h in hard if h is not None)
        hard = [top if h is None else h for h in hard]
        if p["pelvis"] != "fixed":
            # a smooth bob: the constraint envelope, low-passed (a few
            # harmonics of the stride), then pushed down where a leg would
            # still over-reach
            want = _lowpass([min(a, b) for a, b in zip(want, hard)], p.get("harmonics", 6))
        h = list(want)
        for _ in range(40):
            viol = [max(0.0, a - b + 0.002) for a, b in zip(h, hard)]
            if max(viol) <= 0.0:
                break
            viol = _blur([x * 1.5 for x in viol], 1.6 * n / self.T)
            h = [a - b for a, b in zip(h, viol)]
        h = [min(a, b) for a, b in zip(h, hard)]
        self.rz = Loop(h)
        self.rz_range = (min(h), max(h))

    def _fill_flight(self, h):
        """Ballistic pelvis during flight phases (gravity in rig units)."""
        n = len(h)
        if all(x is not None for x in h):
            return h
        g = G / self.s
        dt = self.Tc / n
        out = list(h)
        known = [i for i in range(n) if h[i] is not None]
        for idx, i in enumerate(known):
            k = known[(idx + 1) % len(known)]
            gap = (k - i - 1) % n
            if gap == 0:
                continue
            a, b = h[i], h[k]
            tf = (gap + 1) * dt
            v0 = (b - a) / tf + 0.5 * g * tf
            for m in range(1, gap + 1):
                t = m * dt
                out[(i + m) % n] = a + v0 * t - 0.5 * g * t * t
        return out

    # ---------------------------------------------------------------- swing
    def _swings(self):
        p = self.p
        duty = p["duty"]
        r = (1 - duty) / duty            # d(stance u) / d(swing w)
        self.sw = {}
        eps = 1e-3
        for sd in ("L", "R"):
            g = self.geo[sd]
            p0 = self.stance_ankle(sd, 1.0)
            v0 = (p0 - self.stance_ankle(sd, 1.0 - eps)) * (r / eps)
            p1 = self.stance_ankle(sd, 0.0)
            v1 = (self.stance_ankle(sd, eps) - p1) * (r / eps)
            fp0, fp1 = self.fp_stance(1.0), self.fp_stance(0.0)
            dfp0 = (fp0 - self.fp_stance(1.0 - eps)) * (r / eps)
            dfp1 = (self.fp_stance(eps) - fp1) * (r / eps)
            tau0, tau1 = self.stance_state(sd, 1.0)[2], self.stance_state(sd, 0.0)[2]
            dtau0 = (tau0 - self.stance_state(sd, 1.0 - eps)[2]) * (r / eps)
            keys, fkeys = [(0.0, p0)], [(0.0, fp0)]
            if p["mode"] == "fk":
                for w, th, kn, pf in p["swing"]:
                    ph = (duty + w * (1 - duty) + self.phase_off[sd]) % 1.0
                    hip = self.hip_joint(sd, self.torso(ph), self.rz(ph))
                    a1, a2 = math.radians(th), math.radians(th - kn)
                    fwd = self.l1 * math.sin(a1) + self.l2 * math.sin(a2)
                    up = -self.l1 * math.cos(a1) - self.l2 * math.cos(a2)
                    x = p0.x + (p1.x - p0.x) * sm(w) + g["sg"] * p["bulge"] * math.sin(math.pi * w)
                    keys.append((w, V((x, hip.y - fwd, hip.z + up))))
                    fkeys.append((w, -(th - kn) + pf))
            else:
                lift, at = p["lift"], p["lift_at"]
                for w, lz, fr in ((at, 1.0, 0.4), (min(0.88, at + 0.28), 0.3, 0.8)):
                    q = p0.lerp(p1, fr) + V((g["sg"] * p["bulge"] * math.sin(math.pi * w), 0.0, lift * lz))
                    keys.append((w, q))
                fkeys.append((at, 0.15 * (fp0 + fp1)))
            keys.append((1.0, p1))
            fkeys.append((1.0, fp1))
            self.sw[sd] = dict(ank=Path(keys, v0, v1), fp=Path(fkeys, dfp0, dfp1),
                               toe=Path([(0.0, tau0), (0.28, 0.0), (1.0, tau1)], dtau0, 0.0))
            self.sw[sd]["lift"] = self._clearance(sd)

    def foot_points(self, sd, ank, fp, toe):
        """World (unscaled) heel, ball and toe-tip for an ankle / pitch / toe bend."""
        g = self.geo[sd]
        qy = self._qy(sd)
        rf = qy @ qa(AXV, fp)
        heel = ank + rf @ (g["heel"] - g["A0"])
        ball = ank + rf @ (g["B0"] - g["A0"])
        tip = ball + rf @ qa(AXV, -toe) @ (g["tip"] - g["B0"])
        return heel, ball, tip

    def _clearance(self, sd, n=48):
        """Swing-foot lift correction: the lowest foot point keeps clear of the
        floor (0 at lift-off / touchdown, up to ~1.5 cm mid-swing)."""
        sw = self.sw[sd]
        g = self.geo[sd]
        need = []
        for i in range(n + 1):
            w = i / n
            ank = sw["ank"](w)
            pts = self.foot_points(sd, ank, sw["fp"](w), sw["toe"](w))
            rest = (g["heel"].z, g["B0"].z, g["tip"].z)
            low = min(p.z - r for p, r in zip(pts, rest))
            want = 0.015 * math.sin(math.pi * w) ** 1.2
            need.append(max(0.0, want - low))
        for _ in range(2):
            need = [need[0]] + [max(need[i], 0.25 * need[i - 1] + 0.5 * need[i] + 0.25 * need[i + 1])
                                for i in range(1, n)] + [need[-1]]
        need[0] = need[-1] = 0.0
        if max(need) <= 0.0:
            return None
        return Path([(i / n, need[i]) for i in range(n + 1)], 0.0, 0.0)

    # ------------------------------------------------------------- per frame
    def feet(self, ph, P):
        duty = self.p["duty"]
        for sd in ("L", "R"):
            g = self.geo[sd]
            lp = (ph - self.phase_off[sd]) % 1.0
            if lp < duty:
                u = lp / duty
                ank, fp, toe = self.stance_state(sd, u)
                off = self.off_from_ankle(sd, ank, fp) if self.toe_beta(u) > 0 else self.pivot_off(sd, u)
            else:
                w = (lp - duty) / (1 - duty)
                sw = self.sw[sd]
                fp = sw["fp"](w)
                ank = sw["ank"](w)
                if sw["lift"] is not None:
                    ank = ank + V((0.0, 0.0, sw["lift"](w)))
                off = self.off_from_ankle(sd, ank, fp)
                toe = sw["toe"](w)
            P[f"foot_{sd}"] = (g["sg"] * off.x, -off.y, off.z)
            P[f"fp_{sd}"] = fp
            P[f"fyaw_{sd}"] = self.yaw
            P[f"toe_{sd}"] = toe
            P[f"tc_{sd}"] = 0.0
            P[f"fs_{sd}"] = 0.0
            P[f"knee_{sd}"] = (0.1 + 0.2 * self.st["heavy"], 1.0, 0.0)

    def arms(self, ph, P):
        """Pendular arm swing, counter-phase to the same-side leg: the shoulder
        leads, the elbow flexes on the forward swing a little later, wrist and
        fingers trail (overlapping action).  FK angles -> IK targets."""
        from . import moves
        a = self.p["arms"]
        st = self.st
        rig, s = self.rig, self.s
        tw = 2 * math.pi
        for sd, off in (("L", 0.0), ("R", 0.5)):
            q = ph + off
            S = rig.head[f"upper_arm.{sd}"] / s
            S = V((abs(S.x), -S.y, S.z))                 # (outward, forward, up)
            l1 = rig.len[f"ua{sd}"] / s
            l2 = rig.len[f"fa{sd}"] / s
            fwd = -math.cos(tw * (q - a["lag"]))
            th = a["c"] + a["amp"] * st["arm"] * fwd
            el = (a["e0"] + st["elbow"] + a["ea"] * st["arm"] * 0.5 *
                  (1 - math.cos(tw * (q - a["lag"] - a["lag_e"]))))
            ab = math.radians(a["abduct"] + 1.5 * st["swagger"])
            t = math.radians(th)
            u = V((math.sin(ab), math.cos(ab) * math.sin(t), -math.cos(ab) * math.cos(t)))
            E = S + u * l1
            fv = (V((0, 1, 0)) - u * u.y).normalized() - V((a["psi"], 0, 0))
            fv = (fv - u * fv.dot(u)).normalized()
            e = math.radians(el)
            W = E + (u * math.cos(e) + fv * math.sin(e)) * l2
            P[f"hand_{sd}"] = (W.x, W.y, W.z)
            elb = (E - S) - fv * 0.3
            P[f"elb_{sd}"] = (elb.x, elb.y, elb.z)
            P[f"hs_{sd}"] = 0.0
            P[f"hw_{sd}"] = 0.0
            P[f"wr_{sd}"] = (6.0 + a["wr"] * math.sin(tw * (q - a["lag"] - 0.12)), 0.0, 0.0)
            P[f"sh_{sd}"] = (0.6 * a["sh"] * max(0.0, fwd), a["sh"] * fwd)
            base = moves.fingers(st["fingers"])
            if a["fg_k"] > 0:
                base = moves.blend_hand(base, a["fg"], a["fg_k"])
            elif a["fg"] in moves.HAND:
                base = moves.fingers(a["fg"])
            curl = 2.5 * math.sin(tw * (q - a["lag"] - 0.2))
            P[f"fg_{sd}"] = tuple(v + curl for v in base)

    def __call__(self, t, P):
        ph = (t / self.T) % 1.0
        tor = self.torso(ph)
        for n in ("hips", "spine", "chest", "neck", "head"):
            P[n] = tuple(a + b for a, b in zip(P[n], tor[n]))
        rt = P["root"]
        P["root"] = (rt[0] + tor["x"], rt[1] + tor["f"], rt[2] + self.rz(ph))
        self.feet(ph, P)
        if self.use_arms:
            self.arms(ph, P)
        for name, amp in (getattr(self, "sway", None) or {}).items():
            off = 0.0 if name.endswith("_L") else 0.5
            k = -math.cos(2 * math.pi * (ph + off - 0.05))
            P[name] = tuple(a + b * k for a, b in zip(P[name], amp))

    def travel(self):
        """Armature-space velocity (m/s) of the character this clip depicts."""
        return self.dir * self.p["speed"]


# --------------------------------------------------------------------------
# follow-through for secondary chains (hair, ribbons ...)
# --------------------------------------------------------------------------
def _secondary(arm, core):
    """Bones hanging off the solved body, as parent -> child chains."""
    out = []
    for b in arm.data.bones:
        if b.name in core or b.parent is None or b.parent.name not in core or b.name.startswith("sleeve"):
            continue
        chain = [b.name]
        c = b
        while len(c.children) == 1 and c.children[0].name not in core:
            c = c.children[0]
            chain.append(c.name)
        out.append(chain)
    return out


def follow_through(arm, chains, heads, speed, loop=True):
    """Damped-pendulum secondary motion for chains hanging off the body.

    heads: per frame {parent bone: world position} (scaled armature space);
    speed: travel speed (m/s) - the air streams the hair back.  Each link is
    a damped oscillator driven by its root's acceleration, lower links softer
    (so they lag: overlapping action).  Simulated for several cycles from
    rest so the kept cycle is the periodic steady state.
    Returns {bone: [delta quaternion per frame]}.
    """
    n = len(heads) - 1 if loop else len(heads)
    dt = 1.0 / FPS
    out = {}
    for chain in chains:
        par = arm.data.bones[chain[0]].parent.name
        pos = [heads[i][par] for i in range(n)]
        acc = []
        for i in range(n):
            if loop:
                acc.append((pos[(i + 1) % n] - pos[i] * 2 + pos[(i - 1) % n]) * (1.0 / (dt * dt)))
            else:
                acc.append(V((0, 0, 0)) if i in (0, n - 1) else (pos[i + 1] - pos[i] * 2 + pos[i - 1]) * (1.0 / (dt * dt)))
        k = len(chain)
        stream = min(1.8, (speed / 4.6) ** 2)
        ang = [[None] * n for _ in range(k)]
        state = [[0.0, 0.0, 0.0, 0.0] for _ in range(k)]
        sub = 6
        h = dt / sub
        for rep in range(5 if loop else 1):
            for i in range(n):
                if rep == (4 if loop else 0):
                    for j in range(k):
                        ang[j][i] = (state[j][0], state[j][1])
                a0, a1 = acc[i], acc[(i + 1) % n] if loop else acc[min(i + 1, n - 1)]
                for m in range(sub):
                    a = a0.lerp(a1, m / sub)
                    for j in range(k):
                        om = 2 * math.pi * (1.8 - 0.35 * j)
                        ze = 0.3
                        ln = max(arm.data.bones[chain[j]].length, 0.05)
                        tgt = (0.35 + 0.3 * j) * stream * 16.0 + 1.5 * j
                        sp = state[j]
                        gain = 57.3 * 0.6 * (1 + 0.4 * j) / ln
                        drive_p = -a.y * gain - a.z * gain * 0.25 * math.sin(math.radians(sp[0] + 8.0))
                        drive_r = a.x * gain * 0.8
                        ap = drive_p - om * om * (sp[0] - tgt) - 2 * ze * om * sp[2]
                        ar = drive_r - om * om * sp[1] - 2 * ze * om * sp[3]
                        sp[2] += ap * h
                        sp[3] += ar * h
                        sp[0] = max(-30.0, min(45.0, sp[0] + sp[2] * h))
                        sp[1] = max(-25.0, min(25.0, sp[1] + sp[3] * h))
        for j, bn in enumerate(chain):
            seq = ang[j] + ([ang[j][0]] if loop else [])
            out[bn] = [qa(AXV, pt) @ qa(AYV, rl) for pt, rl in seq]
    return out


# --------------------------------------------------------------------------
# baking and entry points
# --------------------------------------------------------------------------
def bake(rig, clip, speed=0.0):
    """Bake a clip on every frame (planted feet stay exact between samples),
    plus follow-through on the secondary chains."""
    import bpy
    from . import moves
    clip.resolve()
    arm = rig.arm
    act = bpy.data.actions.new(clip.name)
    act.use_fake_user = True
    arm.animation_data.action = act
    frames = list(range(0, clip.length + 1))
    rot = {n: [] for n in rig.names}
    loc = []
    prev = {}
    heads = []
    chains = _secondary(arm, set(rig.names))
    parents = {arm.data.bones[c[0]].parent.name for c in chains}
    for f in frames:
        P = clip.pose(float(f % clip.length) if clip.loop else float(f))
        W, pos = rig.solve(P)
        lq = rig.local(W)
        for n in rig.names:
            q = lq[n]
            if n in prev and prev[n].dot(q) < 0:
                q.negate()
            prev[n] = q
            rot[n].append(q)
        loc.append(rig.hips_loc(P))
        heads.append({pn: pos[pn].copy() for pn in parents})
    if clip.loop:
        for n in rig.names:
            q = rot[n][0].copy()
            if q.dot(rot[n][-2]) < 0:
                q.negate()
            rot[n][-1] = q
        loc[-1] = loc[0].copy()
    for n in rig.names:
        pb = arm.pose.bones[n]
        pb.rotation_mode = "QUATERNION"
        path = f'pose.bones["{n}"].rotation_quaternion'
        for i in range(4):
            moves._write(act, arm, path, i, n, frames, [q[i] for q in rot[n]])
        if n == "hips":
            path = f'pose.bones["{n}"].location'
            for i in range(3):
                moves._write(act, arm, path, i, n, frames, [v[i] for v in loc])
    for bn, qs in follow_through(arm, chains, heads, speed, clip.loop).items():
        rest = arm.data.bones[bn].matrix_local.to_quaternion()
        arm.pose.bones[bn].rotation_mode = "QUATERNION"
        path = f'pose.bones["{bn}"].rotation_quaternion'
        out, pq = [], None
        for d in qs:
            q = rest.inverted() @ d @ rest
            if pq is not None and pq.dot(q) < 0:
                q.negate()
            pq = q
            out.append(q)
        for i in range(4):
            moves._write(act, arm, path, i, bn, frames, [q[i] for q in out])
    return act


def attach(rig, clip, cfg, kind, arms=True, speed=None, direction=None):
    """Put a gait layer on a looping moves.Clip whose keys hold the upper body
    (and the base root / hips); returns the Gait.  The clip's length becomes
    the gait's stride period (keys past it are dropped, so clips keyed with
    this in mind only key frame 0).  `clip.sway` (optional) maps hand
    controls to an (x, f, z) amplitude swung in counter-phase with the legs,
    for clips whose arms are keyed (sprint, sneak ...)."""
    st = style(cfg)
    p = preset(kind, st, speed)
    if direction is not None:
        p["dir"] = direction
    frames = cycle_frames(p["speed"], rig.s, kind, st)
    clip.length = frames

    def first(name):
        for f, v, _ in sorted(clip.pk.get(name, []), key=lambda x: x[0]):
            return v
        return clip.base[name]
    g = Gait(rig, p, st, frames, base={"root": first("root"), "hips": first("hips")}, arms=arms)
    g.sway = getattr(clip, "sway", None)
    clip.extra = g
    return g


MAX_SLIP = 0.02          # metres; the build fails above this


def check(arm, act, g, label=None):
    """verify_clip for a baked gait clip; raises if the feet slide."""
    dx, df = g.p["dir"]
    print(f"    gait   {act.name:<14} {g.T} frames ({60 * 2 / g.Tc:.0f} steps/min) duty {g.p['duty']:.2f} "
          f"stance {g.D * g.s:.2f} m pelvis {g.rz_range[0] * g.s * 100:+.1f}..{g.rz_range[1] * g.s * 100:+.1f} cm")
    res = verify_clip(arm, act, g.p["speed"], (dx, df), scale=g.s, label=label)
    if res["slip"] > MAX_SLIP:
        raise RuntimeError(f"{act.name}: planted foot slips {res['slip'] * 100:.1f} cm (> {MAX_SLIP * 100:.0f} cm)")
    if res["loop_rot"] > 0.05 or res["loop_loc"] > 1e-4:
        raise RuntimeError(f"{act.name}: loop does not close ({res['loop_rot']:.3f} deg)")
    return res


def pose_at(rig, cfg, kind, phase):
    """The full control pose of a gait at a stride phase (to key transition
    clips such as run_start / run_stop onto the cycle)."""
    from . import moves
    clip = moves.Clip(kind, 30, loop=True, base=moves.stand(cfg["female"]))
    g = attach(rig, clip, cfg, kind)
    clip.resolve()
    P = clip.pose(phase * g.T)
    return {k: v for k, v in P.items() if not k.startswith(("hdir", "palm", "hw", "hs"))}


def build_locomotion(arm, J, cfg, s, kinds=("walk", "run")):
    """The `walk` / `run` actions for any humanoid on the shared rig."""
    from . import moves
    if arm.animation_data is None:
        arm.animation_data_create()
    keep = arm.animation_data.action
    rig = moves.Rig(arm, J, cfg, s)
    acts = []
    for kind in kinds:
        clip = moves.Clip(kind, 30, loop=True, base=moves.stand(cfg["female"]))
        g = attach(rig, clip, cfg, kind)
        act = bake(rig, clip, g.p["speed"])
        check(arm, act, g)
        acts.append(act)
    arm.animation_data.action = keep
    return acts


# --------------------------------------------------------------------------
# wide sleeves: a hanging drape bone per arm, baked onto every action
# --------------------------------------------------------------------------
def _key_rotation(act, arm, bone, frames, quats):
    """(Re)write a bone's rotation channels with one key per frame."""
    path = f'pose.bones["{bone}"].rotation_quaternion'
    arm.pose.bones[bone].rotation_mode = "QUATERNION"
    for i in range(4):
        fc = act.fcurve_ensure_for_datablock(arm, path, index=i, group_name=bone)
        kp = fc.keyframe_points
        kp.clear()
        kp.add(len(frames))
        co = []
        for f, q in zip(frames, quats):
            co += [float(f), q[i]]
        kp.foreach_set("co", co)
        for k in kp:
            k.interpolation = "LINEAR"
        fc.update()


def sleeve_follow(arm, actions, scale=1.0, length=0.2, bones=("sleeve.L", "sleeve.R")):
    """Bake the sleeve drape bones on every action.

    Each drape is a damped spherical pendulum hung from the forearm: gravity
    pulls it down, a little cloth stiffness pulls it toward the pose it has
    when carried rigidly by the forearm, the pivot's own acceleration swings
    it (follow-through when the arm pumps), and it never rises above ~15 deg
    below the horizontal.  The bone keeps the forearm's twist (swing-only
    correction).  Looping actions (first and last frame agree) are simulated
    for three cycles and the steady-state cycle is kept, so they still loop.
    """
    names = [b for b in bones if b in arm.data.bones]
    if not names:
        return
    rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    if arm.animation_data is None:
        arm.animation_data_create()
    keep = arm.animation_data.action
    L = length * scale
    down = V((0.0, 0.0, -1.0))
    gvec = V((0.0, 0.0, -G))
    for act in actions:
        smp = _Sampler(arm, act)
        f0, f1 = int(round(smp.f0)), int(round(smp.f1))
        frames = list(range(f0, f1 + 1))
        for bn in names:
            par = arm.data.bones[bn].parent.name
            rel = rest[par].inverted() @ rest[bn]
            carried = []
            for f in frames:
                M = smp.pose([par], float(f))[par] @ rel
                carried.append(M)
            P = [M.translation.copy() for M in carried]
            C = [(M.to_3x3() @ V((0, 1, 0))).normalized() for M in carried]
            loop = (P[0] - P[-1]).length < 1e-4 * scale and C[0].dot(C[-1]) > 0.99999
            n = len(frames)
            dt = 1.0 / FPS
            sub = 8
            h = dt / sub

            D0 = (rest[bn].to_3x3() @ V((0, 1, 0))).normalized()

            def target(i):
                # arm hanging as in the rest pose: the drape hangs as modelled;
                # as the forearm rises toward level, the drape is pulled down
                hang = (down * 0.85 + C[i] * 0.15).normalized()
                f = sm((C[i].z - D0.z) / max(1e-3, -D0.z))
                return C[i].slerp(hang, f) if C[i].dot(hang) > -0.99 else hang
            q = P[0] + target(0) * L
            v = V((0, 0, 0))
            out = [None] * n
            reps = 3 if loop and n > 2 else 1
            for rep in range(reps):
                for i in range(n):
                    if rep == reps - 1:
                        out[i] = (q - P[i]).normalized()
                    if i == n - 1:
                        break
                    for m in range(sub):
                        a_ = (m + 1) / sub
                        piv = P[i].lerp(P[i + 1], a_)
                        tgt = piv + (target(i).lerp(target(i + 1), a_)).normalized() * L
                        acc = gvec * 0.35 + (tgt - q) * 60.0 - v * 7.0
                        v = v + acc * h
                        q = q + v * h
                        d = q - piv
                        if d.length < 1e-6:
                            d = down.copy()
                        d.normalize()
                        if d.z > -0.26:                 # never flare above ~15 deg below level
                            d.z = -0.26
                            d.normalize()
                        qn = piv + d * L
                        v = v - d * v.dot(d)            # no stretching
                        q = qn
            if loop:
                out[-1] = out[0]
            quats = []
            prev = None
            for i in range(n):
                rot_c = carried[i].to_quaternion()
                sw = C[i].rotation_difference(out[i])
                basis = rot_c.inverted() @ sw @ rot_c
                if prev is not None and prev.dot(basis) < 0:
                    basis.negate()
                prev = basis
                quats.append(basis)
            arm.animation_data.action = act
            _key_rotation(act, arm, bn, frames, quats)
    arm.animation_data.action = keep

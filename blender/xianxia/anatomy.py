"""Anatomical body parts for the cultivators: skull/face, ears, neck and hands.

The head is a sphere whose directions are mapped onto a sculpted surface
(``head_shape``): stacked cross-sections give a real skull, cheekbones, a
mandible with a jaw angle and a squared chin, then Gaussian "clay" layers add
the brow ridge, orbits, nose, lips and chin. Because the mapping is defined
per unit-sphere direction, UVs, eye placement and the painted face texture
all stay in the same latitude/longitude space.

Hands are box-modelled cages (palm, three phalanges per finger, thumb) that
are Catmull-Clark subdivided into one smooth surface with knuckles, finger
pads and nails, and are driven by 15 finger bones per hand.
"""
import math

import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import util

V = Vector
R = math.radians


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def g2(x, z, cx, cz, sx, sz):
    return math.exp(-(((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))


# --------------------------------------------------------------------------
# skull and face
# --------------------------------------------------------------------------
# Cross-sections from crown (z = 1) to the chin (z = -1) in unit head space:
# (z, y_front, y_back, half width at the back, half width at the front,
#  superellipse power front, power back). -y is the face.
SECTIONS_MALE = [
    (1.00, -0.02, 0.08, 0.02, 0.02, 2.0, 2.0),
    (0.93, -0.36, 0.48, 0.40, 0.36, 2.1, 2.0),
    (0.75, -0.70, 0.84, 0.74, 0.66, 2.2, 2.1),
    (0.45, -0.90, 0.99, 0.93, 0.84, 2.5, 2.2),
    (0.18, -0.95, 1.00, 0.97, 0.90, 2.9, 2.2),
    (-0.05, -0.96, 0.97, 0.98, 0.93, 3.0, 2.2),
    (-0.25, -0.97, 0.86, 0.96, 0.86, 2.9, 2.3),
    (-0.45, -0.98, 0.60, 0.90, 0.72, 2.8, 2.6),
    (-0.62, -0.99, 0.30, 0.83, 0.54, 2.8, 3.2),
    (-0.76, -0.99, -0.08, 0.66, 0.50, 3.2, 3.0),
    (-0.88, -0.97, -0.46, 0.42, 0.40, 3.4, 2.8),
    (-0.96, -0.90, -0.66, 0.26, 0.26, 3.0, 2.4),
    (-1.00, -0.80, -0.76, 0.02, 0.02, 2.0, 2.0),
]
SECTIONS_FEMALE = [
    (1.00, -0.02, 0.08, 0.02, 0.02, 2.0, 2.0),
    (0.93, -0.36, 0.48, 0.40, 0.36, 2.1, 2.0),
    (0.75, -0.70, 0.85, 0.74, 0.66, 2.2, 2.1),
    (0.45, -0.90, 1.00, 0.93, 0.84, 2.4, 2.2),
    (0.18, -0.95, 1.00, 0.97, 0.90, 2.7, 2.2),
    (-0.05, -0.96, 0.96, 0.97, 0.91, 2.8, 2.2),
    (-0.25, -0.97, 0.84, 0.95, 0.85, 2.7, 2.3),
    (-0.45, -0.98, 0.58, 0.88, 0.70, 2.5, 2.5),
    (-0.62, -0.99, 0.28, 0.78, 0.52, 2.5, 2.8),
    (-0.76, -0.98, -0.10, 0.56, 0.42, 2.6, 2.6),
    (-0.88, -0.95, -0.46, 0.34, 0.31, 2.6, 2.4),
    (-0.96, -0.88, -0.66, 0.18, 0.18, 2.4, 2.2),
    (-1.00, -0.80, -0.76, 0.02, 0.02, 2.0, 2.0),
]

_SECTION_CACHE = {}


def _sections(fem, jaw):
    key = (fem, round(jaw, 3))
    if key in _SECTION_CACHE:
        return _SECTION_CACHE[key]
    rows = SECTIONS_FEMALE if fem else SECTIONS_MALE
    # jaw: 0 = narrow, 1 = broad mandible; scales the lower face half widths
    out = []
    for z, yf, yb, wb, wf, pf, pb in rows:
        k = smooth((-0.3 - z) / 0.4) * smooth((z + 1.0) / 0.12)
        f = 1.0 + (jaw - 0.45) * 0.5 * k
        out.append(V((z, yf, yb, wb * f, wf * f, pf, pb)))
    pts = [V(r) for r in reversed(out)]           # ascending z
    dense = util.catmull(pts, 12)
    dense.sort(key=lambda v: v[0])
    _SECTION_CACHE[key] = dense
    return dense


def _section_at(z, fem, jaw):
    tab = _sections(fem, jaw)
    if z <= tab[0][0]:
        return tab[0]
    lo, hi = 0, len(tab) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if tab[mid][0] <= z:
            lo = mid
        else:
            hi = mid
    a, b = tab[lo], tab[hi]
    t = (z - a[0]) / max(b[0] - a[0], 1e-9)
    return a.lerp(b, t)


def _superellipse(c, s, pf, pb):
    p = pf if c > 0 else pb
    e = 2.0 / p
    return math.copysign(abs(c) ** e, c), math.copysign(abs(s) ** e, s)


def head_shape(d, fem, jaw, features=None):
    """Map a unit-sphere direction to the sculpted head surface (unit space).

    features: optional dict of shape tweaks (nose, cheek, chin, brow, lips, age).
    """
    f = features or {}
    x, y, z = d
    z = max(-1.0, min(1.0, z))
    theta = math.atan2(x, -y)            # 0 = straight ahead (face), +x = character's left
    c, s = math.cos(theta), math.sin(theta)
    sec = _section_at(z, fem, jaw)
    _, yf, yb, wb, wf, pf, pb = sec
    cc, ss = _superellipse(c, s, pf, pb)
    front = max(0.0, c)
    w = wb + (wf - wb) * front ** 1.5
    yc = (yf + yb) * 0.5
    hd = (yb - yf) * 0.5
    p = V((w * ss, yc - hd * cc, z))
    ax = abs(x)
    fr = front ** 3                       # strictly facial region

    # --- facial "clay" layers (in unit head space, -y = toward the viewer)
    nose_k = f.get("nose", 1.0)
    brow_k = f.get("brow", 1.0 if not fem else 0.45)
    cheek_k = f.get("cheek", 1.0)
    chin_k = f.get("chin", 1.0 if not fem else 0.75)
    lip_k = f.get("lips", 0.8 if not fem else 1.0)
    # forehead slopes back a touch; temples are hollow
    p.y += 0.05 * smooth((z - 0.35) / 0.5) * fr
    p.x -= math.copysign(0.035 * g2(ax, z, 0.93, 0.25, 0.12, 0.22), x)
    # brow ridge (glabella + superciliary arches)
    p.y -= brow_k * 0.045 * g2(ax, z, 0.26, 0.24, 0.30, 0.07) * fr
    p.y -= brow_k * 0.02 * g2(ax, z, 0.0, 0.27, 0.12, 0.08) * fr
    # nasion: the bridge dips between the eyes
    p.y += 0.035 * g2(ax, z, 0.0, 0.14, 0.1, 0.07) * fr
    # orbits: eye sockets sink in, deepest at the inner-upper corner
    p.y += 0.085 * g2(ax, z, 0.35, 0.07, 0.19, 0.11) * fr
    p.y += 0.03 * g2(ax, z, 0.2, 0.12, 0.08, 0.06) * fr
    # cheekbones (zygomatic): forward and outward below the outer eye
    ck = g2(ax, z, 0.62, -0.12, 0.2, 0.13) * cheek_k
    p.y -= 0.045 * ck * front ** 1.2
    p.x += math.copysign(0.03 * ck, x)
    # cheek hollow under the cheekbone
    p.y += 0.035 * g2(ax, z, 0.6, -0.45, 0.16, 0.14) * front * (1.0 if not fem else 0.4)
    # nose: a narrow bony bridge that projects more toward a defined tip, small alae
    zb = smooth((0.14 - z) / 0.46)                       # 0 at the nasion .. 1 at the tip
    ridge_w = 0.045 + 0.05 * zb
    ridge = math.exp(-((ax / ridge_w) ** 2)) * smooth((0.14 - z) / 0.1) * smooth((z + 0.4) / 0.08)
    p.y -= nose_k * (0.05 + (0.15 if not fem else 0.12) * zb) * ridge * fr
    tip = g2(ax, z, 0.0, -0.33, 0.075, 0.06)
    p.y -= nose_k * (0.07 if not fem else 0.06) * tip * fr
    ala = g2(ax, z, 0.1, -0.365, 0.045, 0.04)
    p.y -= nose_k * 0.055 * ala * fr
    p.x += math.copysign(0.008 * ala, x)
    # nostril underside tucks in, columella
    p.y += 0.05 * g2(ax, z, 0.055, -0.415, 0.05, 0.028) * fr
    # philtrum groove and a gentle muzzle (dental arch) under the nose
    p.y -= 0.028 * g2(ax, z, 0.0, -0.6, 0.3, 0.16) * fr
    p.y += 0.01 * g2(ax, z, 0.0, -0.5, 0.022, 0.06) * fr
    # nasolabial folds
    nl = math.exp(-(((ax - (0.17 + 0.18 * smooth((-0.4 - z) / 0.3))) / 0.035) ** 2)) \
        * g2(0, z, 0, -0.52, 1, 0.14)
    p.y += 0.015 * nl * fr
    # lips: upper lip, lower lip, mouth line and corners
    up_lip = g2(ax, z, 0.0, -0.575, 0.24, 0.035)
    lo_lip = g2(ax, z, 0.0, -0.665, 0.21, 0.045)
    p.y -= lip_k * (0.04 * up_lip + 0.048 * lo_lip) * fr
    p.y += 0.022 * g2(ax, z, 0.0, -0.622, 0.25, 0.012) * fr
    p.y += 0.02 * g2(ax, z, 0.26, -0.62, 0.04, 0.05) * fr
    # labiomental fold and the chin (mentalis) — squarer for men
    p.y += 0.022 * g2(ax, z, 0.0, -0.75, 0.22, 0.035) * fr
    chin = math.exp(-((ax / (0.30 if not fem else 0.22)) ** 4)) * g2(0, z, 0, -0.86, 1, 0.08)
    p.y -= chin_k * 0.085 * chin * fr
    # mandible: a crisp jaw line (edge of the jaw bone)
    jl = g2(ax, z, 0.72, -0.66, 0.2, 0.08) * (1.0 - front ** 4)
    p.x += math.copysign((0.03 if not fem else 0.015) * jl, x)
    age = f.get("age", 0.0)
    if age:
        # sagging jowls, sunken cheeks and temples
        p.y += 0.03 * age * g2(ax, z, 0.55, -0.35, 0.2, 0.2) * front
        p.x += math.copysign(0.02 * age * g2(ax, z, 0.6, -0.72, 0.2, 0.08), x)
    return p


# --------------------------------------------------------------------------
# ears
# --------------------------------------------------------------------------
EAR_OUTLINE = [  # (back, up) in mm around the pinna, starting at the top front, clockwise seen from the side
    (-4, 26), (4, 30), (12, 27), (17, 18), (18, 6), (15, -6), (10, -16), (4, -24), (-3, -28),
    (-9, -24), (-10, -14), (-9, -2), (-10, 10), (-9, 20)]
# rings from the attachment to the concha: (scale toward the concha centre, outward mm)
EAR_RINGS = [(0.78, -3.0), (0.98, 3.5), (1.0, 7.5), (0.9, 9.5), (0.8, 7.5), (0.7, 9.0), (0.52, 5.5),
             (0.32, 2.5), (0.12, -0.5)]


def ear(bm, loc, side, s, size=1.0):
    """Pinna: helix rim, scapha, antihelix and concha lofted from an ear outline."""
    k = 0.001 * s * size
    centre = V((-3.0, 2.0))
    outline = util.catmull([V((a, b, 0)) for a, b in EAR_OUTLINE + EAR_OUTLINE[:1]], 3)[:-1]
    rows = []
    for sc, out in EAR_RINGS:
        ring_ = []
        for q in outline:
            u = centre.x + (q.x - centre.x) * sc
            v = centre.y + (q.y - centre.y) * sc
            # the pinna flares away from the head toward the back
            w = out + max(0.0, u) * 0.18 * (1.0 if sc > 0.6 else 0.3)
            ring_.append(loc + V((side * w * k, u * k, v * k)))
        rows.append(ring_)
    util.loft(bm, rows, closed=True, cap_end=True, uv_scale=(1.0, 1.0))
    # tragus: a small flap in front of the canal
    util.sphere(bm, 3.0 * k, loc=loc + V((side * 3.0 * k, -8.5 * k, 0.0)), segs=10, rings=6,
                scale=(0.7, 0.8, 1.2))


# --------------------------------------------------------------------------
# neck
# --------------------------------------------------------------------------
def neck(bm, s, nr, fem):
    """Neck with sternocleidomastoid wedge, throat and nape, rising into the skull."""
    rows = []
    zs = [1.44, 1.49, 1.54, 1.585, 1.63, 1.665]
    n = 24
    for j, z in enumerate(zs):
        t = j / (len(zs) - 1)
        ring_ = []
        for i in range(n):
            a = 2 * math.pi * i / n            # 0 = front
            c, sn = math.cos(a), math.sin(a)
            r = nr * (1.18 - 0.2 * smooth(t / 0.5))
            # SCM muscles make the front-sides fuller; the throat is flatter
            scm = math.exp(-((abs(sn) - 0.62) / 0.25) ** 2) * max(0.0, c) * (0.10 if not fem else 0.04)
            adam = (0.12 if not fem else 0.0) * math.exp(-((sn / 0.2) ** 2)) * max(0.0, c) ** 4 \
                * math.exp(-(((t - 0.45) / 0.18) ** 2))
            rr = r * (1.0 + scm + adam - 0.08 * max(0.0, c) ** 2)
            yoff = 0.012 * s * (1 - t) + 0.006 * s
            ring_.append(V((rr * sn * 1.08, -rr * c * 0.94 + yoff, z * s)))
        rows.append(ring_)
    util.loft(bm, rows, closed=True, uv_scale=(1.0, 4.0))


# --------------------------------------------------------------------------
# hands
# --------------------------------------------------------------------------
FINGERS = ("index", "middle", "ring", "pinky")
# x offset across the knuckles (+ = thumb side), knuckle y (from wrist),
# phalanx lengths, half width and splay (deg)
FINGER_DATA = {
    "index": (0.0275, 0.086, (0.041, 0.025, 0.020), 0.0094, 5.0),
    "middle": (0.009, 0.089, (0.045, 0.028, 0.021), 0.0096, 0.0),
    "ring": (-0.009, 0.086, (0.042, 0.026, 0.020), 0.0091, -4.0),
    "pinky": (-0.0265, 0.079, (0.033, 0.020, 0.018), 0.0082, -10.0),
}
REST_CURL = {"index": (8, 12, 8), "middle": (10, 16, 10), "ring": (12, 18, 11), "pinky": (14, 20, 12)}


def hand_frame(wrist, hand_tail, side):
    """(x: thumb side, y: along the fingers, z: back of the hand) in world space."""
    sg = 1 if side == "L" else -1
    hd = (hand_tail - wrist).normalized()
    front = V((0, -1, 0))
    front = (front - hd * front.dot(hd)).normalized()
    dorsal = V((sg, 0, 0))
    dorsal = (dorsal - hd * dorsal.dot(hd) - front * dorsal.dot(front)).normalized()
    return front, hd, dorsal


def _rot(axis, deg):
    return Matrix.Rotation(R(deg), 3, axis)


def finger_chains(scale):
    """Local-space joint chains: name -> [p0, p1, p2, p3] (base knuckle .. tip).

    Local frame: +x thumb side, +y along the hand, +z back of the hand.
    """
    chains = {}
    for name in FINGERS:
        ox, ky, lens, _, splay = FINGER_DATA[name]
        curl = REST_CURL[name]
        p = V((ox, ky, -0.001)) * scale
        d = _rot("Z", -splay) @ V((0, 1, 0))      # splay toward the thumb for +deg
        side_ax = d.cross(V((0, 0, 1))).normalized()
        pts = [p.copy()]
        for ln, cu in zip(lens, curl):
            d = (Matrix.Rotation(R(cu), 3, side_ax) @ d).normalized()
            p = p + d * ln * scale
            pts.append(p.copy())
        chains[name] = pts
    # thumb: carpometacarpal base on the palm side of the wrist
    base = V((0.021, 0.022, -0.011)) * scale
    d = V((0.62, 0.62, -0.48)).normalized()
    pts = [base]
    p = base
    for ln, bend in ((0.040, 0.0), (0.031, 14.0), (0.026, 16.0)):
        ax = d.cross(V((0.2, 0.3, -1.0)).normalized()).normalized()
        d = (Matrix.Rotation(R(bend), 3, ax) @ d).normalized()
        p = p + d * ln * scale
        pts.append(p.copy())
    chains["thumb"] = pts
    return chains


def finger_bones(wrist, hand_tail, side, scale):
    """Bone dict entries for the 15 finger bones of one hand (world space)."""
    x, y, z = hand_frame(wrist, hand_tail, side)
    M = Matrix((x, y, z)).transposed()
    out = {}
    for name, pts in finger_chains(scale).items():
        world = [wrist + M @ p for p in pts]
        parent = f"hand.{side}"
        for i in range(3):
            bn = f"{name}.{i + 1}.{side}"
            out[bn] = (world[i], world[i + 1], parent)
            parent = bn
    return out


def _square(c, xa, za, hw, ht, bulge=0.0, crease=0.0):
    """Four cage corners around c: (-x,+z), (+x,+z), (+x,-z), (-x,-z)."""
    return [c - xa * hw + za * (ht + bulge), c + xa * hw + za * (ht + bulge),
            c + xa * hw - za * (ht - crease), c - xa * hw - za * (ht - crease)]


def hand_mesh(wrist, hand_tail, side, scale, skin_mat, nail_mat, fem=False):
    """Subdivided single-surface hand with nails. Returns the object."""
    xw, yw, zw = hand_frame(wrist, hand_tail, side)
    M = Matrix((xw, yw, zw)).transposed()
    S = scale
    bm = bmesh.new()
    # palm rows: (y, half width, dorsal thickness, palmar thickness)
    rows = [(-0.045, 0.024, 0.016, 0.016), (-0.012, 0.026, 0.015, 0.016), (0.02, 0.034, 0.0145, 0.019),
            (0.052, 0.041, 0.0135, 0.019), (0.080, 0.045, 0.0125, 0.0135)]
    bounds = [-1.0, -0.36, 0.0, 0.36, 1.0]       # finger column borders (fraction of half width)
    knuckle_x = [-0.0355, -0.0175, 0.0, 0.018, 0.037]
    loops = []
    for j, (yy, hw, td, tp) in enumerate(rows):
        last = j == len(rows) - 1
        dors, pal = [], []
        for k, b in enumerate(bounds):
            xx = knuckle_x[k] if last else b * hw
            arch = 1.0 + 0.25 * (1 - abs(b)) if not last else 1.0
            thenar = 1.0 + (0.35 if (b > 0.3 and 0 < j < 4) else 0.0)
            dors.append(V((xx, yy, td * arch)) * S)
            pal.append(V((xx, yy, -tp * thenar)) * S)
        loops.append([bm.verts.new(p) for p in dors] + [bm.verts.new(p) for p in reversed(pal)])
    nl = 10

    def dv(loop, k):     # dorsal vertex k (0 pinky .. 4 thumb side)
        return loop[k]

    def pv(loop, k):     # palmar vertex k
        return loop[9 - k]

    thumb_face = (1, 2)   # the thumb grows from the side between palm rows 1 and 2
    for j in range(len(loops) - 1):
        a, b = loops[j], loops[j + 1]
        for i in range(nl):
            i2 = (i + 1) % nl
            if i == 4 and j == thumb_face[0]:
                continue   # leave the thumb port open (edge d4 -> p4 is index 4 -> 5)
            bm.faces.new((a[i], a[i2], b[i2], b[i]))
    # cap under the sleeve
    lo = loops[0]
    for k in range(4):
        bm.faces.new((dv(lo, k + 1), dv(lo, k), pv(lo, k), pv(lo, k + 1)))
    top = loops[-1]
    chains = finger_chains(S)
    names_by_col = ["pinky", "ring", "middle", "index"]
    for col, name in enumerate(names_by_col):
        pts = chains[name]
        hw0 = FINGER_DATA[name][3] * S
        prev = [dv(top, col), dv(top, col + 1), pv(top, col + 1), pv(top, col)]
        # sample rings along the chain
        stations = []
        for i in range(3):
            a, b = pts[i], pts[i + 1]
            for t in ((0.45,) if i == 0 else (0.0, 0.5)):
                stations.append((a.lerp(b, t), (b - a).normalized(), i, t))
        a, b = pts[2], pts[3]
        stations.append((a.lerp(b, 0.85), (b - a).normalized(), 2, 0.85))
        for c, d, seg, t in stations:
            xa = V((1, 0, 0)) - d * d.x
            xa.normalize()
            za = xa.cross(d).normalized()
            if za.z < 0:
                za = -za
            taper = 1.0 - 0.08 * seg - 0.04 * t
            joint = t == 0.0 and seg > 0
            hw = hw0 * taper * (1.06 if joint else 1.0)
            ht = hw0 * 0.92 * taper
            ring_ = [bm.verts.new(p) for p in _square(c, xa, za, hw, ht,
                                                     bulge=(0.0016 * S if joint else 0.0),
                                                     crease=(0.001 * S if joint else 0.0))]
            for i in range(4):
                i2 = (i + 1) % 4
                bm.faces.new((prev[i], prev[i2], ring_[i2], ring_[i]))
            prev = ring_
        # fingertip: a slightly smaller ring then a cap (subdivision rounds it)
        tipc = pts[3] - (pts[3] - pts[2]).normalized() * 0.002 * S
        d = (pts[3] - pts[2]).normalized()
        xa = (V((1, 0, 0)) - d * d.x).normalized()
        za = xa.cross(d).normalized()
        if za.z < 0:
            za = -za
        ring_ = [bm.verts.new(p) for p in _square(tipc, xa, za, hw0 * 0.62, hw0 * 0.55)]
        for i in range(4):
            i2 = (i + 1) % 4
            bm.faces.new((prev[i], prev[i2], ring_[i2], ring_[i]))
        bm.faces.new(ring_)
    # thumb from the side port
    a, b = loops[thumb_face[0]], loops[thumb_face[1]]
    prev = [a[4], b[4], b[5], a[5]]   # (low-dorsal, high-dorsal, high-palmar, low-palmar)
    pts = chains["thumb"]
    stations = [(pts[0].lerp(pts[1], 0.55), 0), (pts[1], 1), (pts[1].lerp(pts[2], 0.5), 1), (pts[2], 2),
                (pts[2].lerp(pts[3], 0.5), 2), (pts[2].lerp(pts[3], 0.85), 2)]
    for n_, (c, seg) in enumerate(stations):
        d = (pts[min(seg + 1, 3)] - pts[seg]).normalized()
        u = V((0, 1, 0)) - d * d.y
        u.normalize()
        v = d.cross(u).normalized()
        if v.z < 0:
            v = -v
        w = (0.0115 - 0.0012 * n_) * S
        ring_ = [bm.verts.new(p) for p in (c - u * w + v * w * 0.85, c + u * w + v * w * 0.85,
                                            c + u * w - v * w * 0.95, c - u * w - v * w * 0.95)]
        for i in range(4):
            i2 = (i + 1) % 4
            bm.faces.new((prev[i], prev[i2], ring_[i2], ring_[i]))
        prev = ring_
    c = pts[3]
    d = (pts[3] - pts[2]).normalized()
    u = (V((0, 1, 0)) - d * d.y).normalized()
    v = d.cross(u).normalized()
    if v.z < 0:
        v = -v
    w = 0.0062 * S
    ring_ = [bm.verts.new(p) for p in (c - u * w + v * w, c + u * w + v * w, c + u * w - v * w, c - u * w - v * w)]
    for i in range(4):
        i2 = (i + 1) % 4
        bm.faces.new((prev[i], prev[i2], ring_[i2], ring_[i]))
    bm.faces.new(ring_)
    # to world (the right hand's frame is mirrored, so fix the winding afterwards)
    for vtx in bm.verts:
        vtx.co = wrist + M @ vtx.co
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = util.mesh_object(f"Hand.{side}", bm, skin_mat)
    util.subdivide(obj, 2)
    util.box_uv(obj, 9.0)
    # nails: small curved plates projected onto the dorsal side of each distal phalanx
    nbm = bmesh.new()
    nbm.from_mesh(obj.data)
    bvh = BVHTree.FromBMesh(nbm)
    nbm.free()
    nails = bmesh.new()
    uvl = nails.loops.layers.uv.verify()
    wchains = {k: [wrist + M @ p for p in v] for k, v in chains.items()}
    for name, pts in wchains.items():
        a, b = pts[2], pts[3]
        d = (b - a).normalized()
        up = zw - d * zw.dot(d)
        up.normalize()
        xa = d.cross(up).normalized()
        wide = FINGER_DATA[name][3] * S * 0.78 if name != "thumb" else 0.0098 * S
        grid = []
        for j in range(5):
            row = []
            for i in range(5):
                u = (i / 4 - 0.5) * 2
                t = 0.42 + 0.5 * j / 4
                probe = a.lerp(b, t) + xa * u * wide * 0.8 + up * 0.03 * S
                hit = bvh.ray_cast(probe, -up, 0.05 * S)
                if hit[0] is None:
                    loc, nrm = bvh.find_nearest(probe)[:2]
                else:
                    loc, nrm = hit[0], hit[1]
                lift = 0.00035 * S * (1 - abs(u) ** 2) + 0.0001 * S
                row.append(nails.verts.new(loc + nrm * lift))
            grid.append(row)
        faces = []
        for j in range(4):
            for i in range(4):
                f = nails.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uvl].uv = (uu / 4, vv / 4)
                faces.append(f)
        faces[5].normal_update()
        if faces[5].normal.dot(up) < 0:
            bmesh.ops.reverse_faces(nails, faces=faces)
    nail_obj = util.mesh_object(f"Nails.{side}", nails, nail_mat)
    return obj, nail_obj

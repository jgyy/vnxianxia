"""Anatomical body parts for the cultivators: ears and hands.

The head, face and neck live in the face_* modules (a landmark-driven implicit
head, ray-cast onto an O-grid quad topology); this module keeps the pinna,
which ``face_head`` attaches in head millimetres.

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


# --------------------------------------------------------------------------
# ears
# --------------------------------------------------------------------------
# Pinna outline (back, up) in mm seen from the side, clockwise from the top of
# the helix root: the helix rim sweeps up and back, down the posterior edge to
# a soft free lobule, then forward and up along the tragus notch.
EAR_OUTLINE = [(-3, 24), (3, 29), (11, 27), (16, 19), (17.5, 8), (15, -4), (11, -14), (6, -22), (1, -29),
               (-4, -31), (-8, -27), (-9, -19), (-7.5, -12), (-9, -3), (-10, 8), (-8.5, 18)]
# Rings from the attachment to the concha floor: (scale toward the concha centre,
# lateral offset mm, curl of the rim).  The rim rolls over (helix), dips into
# the scapha, rises on the antihelix and falls into the concha.
EAR_RINGS = [(0.80, -3.0, 0.0), (0.97, 2.5, 0.0), (1.03, 6.8, 0.0), (1.0, 9.3, -1.2), (0.93, 9.0, -2.2),
             (0.86, 7.0, -1.0), (0.76, 7.9, 0.0), (0.66, 8.4, 0.0), (0.52, 5.2, 0.0), (0.36, 1.8, 0.0),
             (0.18, -1.2, 0.0), (0.04, -2.4, 0.0)]


def ear(bm, loc, side, size=1.0, flare=21.0, uv_fn=None, mat_index=0):
    """Pinna in head millimetres: helix rim, scapha, antihelix, concha, lobule and tragus.

    loc: attachment point (tragus root); side +1 = left; flare: protrusion
    angle (deg) of the pinna away from the head.  uv_fn(up, back) -> (u, v).
    Returns the created vertices."""
    k = size
    centre = V((-2.0, 1.0))
    outline = util.catmull([V((a, b_, 0)) for a, b_ in EAR_OUTLINE + EAR_OUTLINE[:1]], 3)[:-1]
    rot = Matrix.Rotation(R(-flare * side), 3, "Z")
    made = []
    uvl = bm.loops.layers.uv.verify()
    rows = []
    for sc, out, curl in EAR_RINGS:
        ring_ = []
        for q in outline:
            u = centre.x + (q.x - centre.x) * sc
            v = centre.y + (q.y - centre.y) * sc
            lobe = max(0.0, -v - 16.0) / 14.0                  # the lobule is thick and soft
            # the pinna flares away from the head toward its back edge, the rim curls forward
            w = out + max(0.0, u) * 0.22 * (1.0 if sc > 0.6 else 0.3) + lobe * 1.5 * (sc > 0.5)
            back = u + curl * (1.0 if sc > 0.9 else 0.5)
            p = rot @ V((side * w, back, 0.0))
            ring_.append(loc + V((p.x * k, p.y * k, v * k)))
        rows.append(ring_)
    n = len(outline)
    vrows = [[bm.verts.new(p) for p in r] for r in rows]
    for j in range(len(vrows) - 1):
        for i in range(n):
            i2 = (i + 1) % n
            quad = (vrows[j][i], vrows[j][i2], vrows[j + 1][i2], vrows[j + 1][i])
            f = bm.faces.new(quad if side > 0 else quad[::-1])
            f.material_index = mat_index
    f = bm.faces.new(vrows[-1] if side > 0 else vrows[-1][::-1])
    f.material_index = mat_index
    made += [v for r in vrows for v in r]
    # tragus: a small flap in front of the canal
    before = set(bm.verts)
    util.sphere(bm, 3.2 * k, loc=loc + V((side * 2.5 * k, -7.5 * k, -3.0 * k)), segs=10, rings=6,
                scale=(0.65, 0.8, 1.25))
    made += [v for v in bm.verts if v not in before]
    for f in {f for v in made for f in v.link_faces}:
        f.material_index = mat_index
        if uv_fn is not None:
            for lp in f.loops:
                d = lp.vert.co - loc
                lp[uvl].uv = uv_fn(d.z / k, d.y / k)
    return made


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

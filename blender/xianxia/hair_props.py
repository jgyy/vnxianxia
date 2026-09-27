"""Hair accessories: guan crowns, hairpins, buyao ornaments, headband, douli hat,
headscarf, horns.  All rigid with the head (weight kind "head")."""
import math

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import util

V = Vector
R = math.radians


def _v(a):
    return V(tuple(float(x) for x in a))


def solid(parts, name, bm, mat, uvs=8.0, weight="head"):
    o = util.mesh_object(name, bm, mat)
    if uvs:
        util.box_uv(o, uvs)
    parts.append((weight, o))
    return o


def guan(parts, mats, centre, up, s, size=1.0, pin=True, name="Guan"):
    """Xiaoguan: a small lacquered-metal crown cupping the topknot, pierced by a pin.

    A shallow oval cup with a raised front plate, a cloud-scroll rim and a jade-tipped
    hairpin through both sides.
    """
    c = _v(centre)
    bm = bmesh.new()
    k = s * size
    prof = [(0.020, -0.018), (0.027, -0.012), (0.030, 0.0), (0.030, 0.016), (0.026, 0.030),
            (0.016, 0.040), (0.004, 0.044)]
    util.lathe(bm, [(r * k, z * k) for r, z in prof], segs=28, loc=c, cap_top=True)
    bmesh.ops.scale(bm, vec=(0.72, 1.12, 1.0), verts=bm.verts, space=Matrix.Translation(-c))
    # raised front plate (the "crown" silhouette seen from the front)
    plate = [c + V((x * k, -0.028 * k, z * k)) for x, z in ((-0.018, -0.01), (-0.02, 0.028), (-0.008, 0.05),
                                                            (0.0, 0.056), (0.008, 0.05), (0.02, 0.028),
                                                            (0.018, -0.01))]
    util.tube(bm, util.catmull(plate, 4), 0.0028 * k, n=6)
    # rim ring
    rim = [c + V((math.cos(a) * 0.0305 * k * 0.72, math.sin(a) * 0.0305 * k * 1.12, -0.004 * k))
           for a in np.linspace(0, 2 * math.pi, 33)]
    util.tube(bm, rim, 0.0022 * k, n=6, closed_ends=False)
    solid(parts, name, bm, mats["metal"], 0)
    if pin:
        bm = bmesh.new()
        util.cylinder(bm, 0.0032 * s, 0.0024 * s, 0.13 * s, loc=c + V((0, 0, 0.018 * k)),
                      rot=Matrix.Rotation(R(90), 4, "Y"), segs=8)
        util.sphere(bm, 0.0075 * s, loc=c + V((0.066 * s, 0, 0.018 * k)), segs=10, rings=6)
        solid(parts, "Hairpin", bm, mats["jade"], 0)
    return c


def knot_wrap(parts, mats, centre, up, s):
    """Cloth band wound round a topknot and tied with a short ribbon."""
    c = _v(centre)
    u = _v(up).normalized()
    ref = V((1, 0, 0)) if abs(u.x) < 0.9 else V((0, 1, 0))
    a = u.cross(ref).normalized()
    b = u.cross(a)
    bm = bmesh.new()
    for k, (r, h) in enumerate(((0.024, -0.008), (0.022, 0.004))):
        ring_ = [c + (a * math.cos(t) + b * math.sin(t)) * r * s + u * h * s
                 for t in np.linspace(0, 2 * math.pi, 25)]
        util.tube(bm, ring_, (0.0035 * s, 0.006 * s), n=6, up=tuple(u), closed_ends=False)
    tail = c - b * 0.024 * s
    util.tube(bm, util.catmull([tail, tail - b * 0.01 * s - u * 0.03 * s, tail - b * 0.012 * s - u * 0.07 * s], 4),
              (0.002 * s, 0.008 * s), n=6)
    solid(parts, "KnotWrap", bm, mats["band"], 30)


def phoenix_crown(parts, mats, centre, s):
    """Sect master's tall crown with sweeping phoenix wings."""
    c = _v(centre)
    bm = bmesh.new()
    prof = [(0.042, -0.02), (0.05, 0.0), (0.052, 0.03), (0.046, 0.06), (0.03, 0.08), (0.006, 0.09)]
    util.lathe(bm, [(r * s, z * s) for r, z in prof], segs=24, loc=c, cap_top=True)
    bmesh.ops.scale(bm, vec=(0.8, 1.2, 1.0), verts=bm.verts, space=Matrix.Translation(-c))
    for side in (1, -1):
        wing = [c + V((side * 0.04 * s, 0, 0.04 * s)), c + V((side * 0.09 * s, 0.03 * s, 0.07 * s)),
                c + V((side * 0.12 * s, 0.07 * s, 0.05 * s))]
        util.tube(bm, util.catmull(wing, 4), lambda t: (0.006 - 0.004 * t) * s, n=6)
    solid(parts, "Crown", bm, mats["metal"], 0)


def buyao(parts, mats, anchor, side, s, blossom=True):
    """Step-shaking hairpin: a gold stem ending in a flower with dangling beads."""
    base = _v(anchor)
    bm = bmesh.new()
    tip = base + V((side * 0.05 * s, -0.012 * s, 0.028 * s))
    util.tube(bm, [base - V((side * 0.03 * s, -0.01 * s, 0.015 * s)), tip], 0.0022 * s, n=6)
    for k in range(5):
        a = 2 * math.pi * k / 5
        util.sphere(bm, 0.0085 * s, loc=tip + V((math.cos(a) * 0.009 * s, 0, math.sin(a) * 0.009 * s)),
                    segs=8, rings=5, scale=(1, 0.4, 1))
    for k in range(3):
        bead = tip + V((side * 0.004 * k * s, -0.004 * s, -0.02 * s * (k + 1)))
        util.sphere(bm, 0.004 * s, loc=bead, segs=8, rings=5)
        util.tube(bm, [tip, bead], 0.0007 * s, n=4)
    solid(parts, "Ornament", bm, mats["metal"], 0)
    if blossom:
        bm = bmesh.new()
        fl = base + V((-side * 0.01 * s, -0.012 * s, 0.004 * s))
        for k in range(5):
            a = 2 * math.pi * k / 5 + 0.3
            util.sphere(bm, 0.0095 * s, loc=fl + V((math.cos(a) * 0.01 * s, -0.003 * s, math.sin(a) * 0.01 * s)),
                        segs=8, rings=5, scale=(1, 0.35, 1))
        util.sphere(bm, 0.004 * s, loc=fl + V((0, -0.006 * s, 0)), segs=8, rings=5)
        solid(parts, "Blossom", bm, mats["accent"], 0)


def hairstick(parts, mats, centre, s, angle=25):
    """Plain jade hairstick (zan) through a bun."""
    c = _v(centre)
    bm = bmesh.new()
    rot = Matrix.Rotation(R(90), 4, "Y") @ Matrix.Rotation(R(angle), 4, "X")
    util.cylinder(bm, 0.003 * s, 0.002 * s, 0.12 * s, loc=c, rot=rot, segs=8)
    solid(parts, "Hairstick", bm, mats["jade"], 0)


def headband(parts, mats, head, s, z=0.36):
    """Cloth band round the brow, knotted at the back with trailing tails."""
    bm = bmesh.new()
    lon = np.linspace(-math.pi, math.pi, 37).astype(np.float32)
    ring_ = [_v(p) for p in head.point(lon, np.full_like(lon, math.asin(z)), 0.009 * s)]
    util.tube(bm, ring_, (0.004 * s, 0.012 * s), n=8, up=(0, 0, 1), closed_ends=False)
    knot = _v(head.point(np.float32(math.pi), np.float32(math.asin(z)), 0.012 * s))
    for side in (1, -1):
        util.tube(bm, util.catmull([knot, knot + V((side * 0.02 * s, 0.03 * s, -0.06 * s)),
                                    knot + V((side * 0.03 * s, 0.04 * s, -0.16 * s))], 4),
                  (0.0025 * s, 0.01 * s), n=6, up=(0, 1, 0))
    solid(parts, "Headband", bm, mats["band"], 30)


def douli(parts, mats, head, s):
    """Conical bamboo hat with a chin strap."""
    top = _v(head.point(np.float32(0), np.float32(math.pi / 2), 0.0))
    bm = bmesh.new()
    hc = top + V((0, 0.01 * s, 0.012 * s))
    prof = [(0.25, -0.03), (0.23, -0.02), (0.16, 0.03), (0.08, 0.07), (0.01, 0.1)]
    util.lathe(bm, [(r * s, z * s) for r, z in prof], segs=32, loc=hc, cap_top=True)
    solid(parts, "Hat", bm, mats["straw"], 6)
    bm = bmesh.new()
    lon = np.array([1.45, 1.1, 0.0, -1.1, -1.45], np.float32)
    lat = np.array([-0.1, -0.75, -1.2, -0.75, -0.1], np.float32)
    strap = [_v(p) for p in head.point(lon, lat, 0.004 * s)]
    util.tube(bm, util.catmull(strap, 4), 0.0018 * s, n=5)
    solid(parts, "HatStrap", bm, mats["band"], 30)


def scarf_knot(parts, mats, head, s):
    knot = _v(head.point(np.float32(math.pi), np.float32(0.1), 0.02 * s))
    bm = bmesh.new()
    util.sphere(bm, 0.024 * s, loc=knot, segs=12, rings=8, scale=(1.3, 0.8, 1.0))
    for side in (1, -1):
        util.tube(bm, util.catmull([knot, knot + V((side * 0.03 * s, 0.03 * s, -0.08 * s)),
                                    knot + V((side * 0.035 * s, 0.035 * s, -0.17 * s))], 4),
                  (0.004 * s, 0.018 * s), n=6, up=(0, 1, 0))
    solid(parts, "ScarfKnot", bm, mats["scarf"], 20)


def horns(parts, mats, head, s):
    bm = bmesh.new()
    for side in (1, -1):
        root = _v(head.point(np.float32(side * 0.5), np.float32(0.72), -0.004 * s))
        path = [root, root + V((side * 0.03 * s, 0.03 * s, 0.07 * s)), root + V((side * 0.07 * s, 0.1 * s, 0.12 * s)),
                root + V((side * 0.1 * s, 0.2 * s, 0.13 * s)), root + V((side * 0.1 * s, 0.27 * s, 0.1 * s))]
        util.tube(bm, util.catmull(path, 5), lambda t: (0.022 - 0.02 * t) * s, n=10)
    solid(parts, "Horns", bm, mats["horn"], 10)

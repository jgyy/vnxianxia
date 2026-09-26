"""Procedural xianxia cultivators: modelling, texturing, rigging and animation.

Characters face -Y in Blender (=> +Z in glTF / Godot "model front").
Units are metres. Left side of the character is +X.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from . import anatomy, tex, util

V = Vector
R = math.radians

# --------------------------------------------------------------------------
# character definitions
# --------------------------------------------------------------------------
MALE = dict(
    name="cultivator_male",
    female=False,
    scale=1.0,                      # 1.80 m
    shoulder=0.195, hip=0.095,
    head_r=(0.075, 0.097, 0.114),
    jaw=0.55, neck_r=0.053,
    # robe rings: (z, half width, half depth, y centre, squareness)
    robe=[(0.035, 0.27, 0.235, 0.01, 2.0), (0.22, 0.25, 0.21, 0.01, 2.0),
          (0.48, 0.225, 0.18, 0.005, 2.0), (0.74, 0.205, 0.155, 0.0, 2.1),
          (0.92, 0.19, 0.138, 0.0, 2.2), (1.03, 0.172, 0.125, 0.0, 2.2),
          (1.09, 0.160, 0.117, 0.0, 2.2), (1.19, 0.170, 0.122, -0.005, 2.3),
          (1.31, 0.186, 0.128, -0.012, 2.5), (1.40, 0.196, 0.118, -0.006, 2.8),
          (1.45, 0.175, 0.098, 0.0, 2.4), (1.485, 0.105, 0.080, 0.005, 2.0),
          (1.525, 0.072, 0.068, 0.008, 2.0), (1.55, 0.073, 0.069, 0.008, 2.0)],
    sleeve_cuff=(0.145, 0.10),
    colors=dict(
        skin="#e8c3a4", hair="#120e10", hair_hl="#40363c", iris="#3a2414",
        lip="#a9585a", brow="#17100f", liner="#150e0e", blush="#d4908a",
        robe_top="#f3f6f8", robe_hem="#a7bccd", robe_motif="#4f6780", robe_accent="#dfe8ef",
        trim="#1f3150", thread="#c9d2dc", belt="#1c2b45", boots="#1b1c22", sole="#e9e4da",
        metal="#c8ccd2", jade="#4f9a7c",
    ),
    robe_style="mountains",
)

FEMALE = dict(
    name="cultivator_female",
    female=True,
    scale=0.93,                     # ~1.67 m
    shoulder=0.170, hip=0.092,
    head_r=(0.072, 0.093, 0.108),
    jaw=0.40, neck_r=0.047,
    robe=[(0.035, 0.34, 0.30, 0.015, 2.0), (0.20, 0.30, 0.26, 0.015, 2.0),
          (0.46, 0.245, 0.20, 0.01, 2.0), (0.72, 0.205, 0.158, 0.005, 2.0),
          (0.91, 0.188, 0.14, 0.0, 2.1), (1.02, 0.160, 0.118, 0.0, 2.1),
          (1.09, 0.140, 0.104, 0.0, 2.1), (1.18, 0.150, 0.112, -0.008, 2.1),
          (1.28, 0.165, 0.128, -0.022, 2.2), (1.37, 0.172, 0.115, -0.01, 2.6),
          (1.435, 0.155, 0.092, 0.0, 2.4), (1.48, 0.095, 0.074, 0.005, 2.0),
          (1.52, 0.064, 0.060, 0.008, 2.0), (1.545, 0.066, 0.062, 0.008, 2.0)],
    sleeve_cuff=(0.17, 0.11),
    colors=dict(
        skin="#f1d2bd", hair="#140f10", hair_hl="#4a3a3c", iris="#2e1a12",
        lip="#c0404e", brow="#2a1c1a", liner="#1a0f10", blush="#e89aa0",
        robe_top="#fbf7fa", robe_hem="#e9b3c6", robe_motif="#5a3b35", robe_accent="#d0467a",
        trim="#7a1f3d", thread="#dcb863", belt="#c43d62", boots="#f2ece6", sole="#b8a58a",
        metal="#d9b25a", jade="#6fbf9f", ribbon="#f4c3d4",
    ),
    robe_style="blossom",
)


def variant(base, name, colors=None, **over):
    """A new character config derived from MALE/FEMALE with overrides."""
    cfg = dict(base)
    cfg["colors"] = dict(base["colors"], **(colors or {}))
    cfg.update(over)
    cfg["name"] = name
    return cfg


# NPCs and enemies (NPC faces use 1024 px textures to keep the GLBs small)
VARIANTS = {
    "elder_male": variant(
        MALE, "elder_male", hair_style="elder", beard="long", age=0.85, stubble=0.0, accessory="none",
        face_tex=1024, jaw=0.5, face=dict(nose=1.12, brow=1.25, cheek=0.85, age=0.8),
        colors=dict(skin="#d9b596", hair="#bdb9b3", hair_hl="#eceae6", brow="#9d9994", iris="#2a1c14",
                    lip="#a0645e", robe_top="#3e5f5b", robe_hem="#1b2e2d", robe_motif="#c8ad6c",
                    robe_accent="#e7d6a4", trim="#161a1c", thread="#c9a55a", belt="#5b3f27",
                    metal="#b9975a", jade="#3f8a6c"),
        robe_style="clouds", sleeve_cuff=(0.16, 0.11)),
    "sect_master": variant(
        FEMALE, "sect_master", hair_style="crown", age=0.2, face_tex=1024, scale=0.96, accessory="ribbon",
        face=dict(nose=1.0, cheek=1.1, chin=0.8),
        colors=dict(skin="#f0d6c2", robe_top="#f8f5ec", robe_hem="#dccb9c", robe_motif="#9c7a34",
                    robe_accent="#e8cf86", trim="#5e4a1c", thread="#f2d57e", belt="#a8843a",
                    metal="#e0c068", ribbon="#f3e3b3", lip="#b34a50"),
        robe_style="clouds"),
    "disciple_male": variant(
        MALE, "disciple_male", face_tex=1024, jaw=0.48, face=dict(nose=0.95, brow=0.9),
        colors=dict(skin="#e6c0a0", robe_top="#d3dbe2", robe_hem="#8397ab", robe_motif="#3d5268",
                    robe_accent="#b4c3d1", trim="#34475e", belt="#2a3a50", metal="#aeb4bb"),
        robe_style="plain"),
    "disciple_female": variant(
        FEMALE, "disciple_female", face_tex=1024, accessory="none", forehead_mark=False, ornaments=False,
        colors=dict(skin="#efd0ba", robe_top="#eef5ec", robe_hem="#a3c7aa", robe_motif="#3f6b4d",
                    robe_accent="#6fa37e", trim="#2f5a40", thread="#d7e6d2", belt="#3f7a57", lip="#b24c55"),
        robe_style="bamboo"),
    "villager_male": variant(
        MALE, "villager_male", hair_style="hat", accessory="none", face_tex=1024, age=0.35, stubble=0.55,
        jaw=0.62, face=dict(nose=1.1, cheek=1.1, age=0.3), sleeve_cuff=(0.10, 0.075),
        colors=dict(skin="#d6a17c", robe_top="#8b7358", robe_hem="#5f4c3b", robe_motif="#3a2e24",
                    robe_accent="#a58b69", trim="#4a3a2a", thread="#8f7b5f", belt="#3a3028", band="#3a3028"),
        robe_style="hemp"),
    "villager_female": variant(
        FEMALE, "villager_female", hair_style="scarf", accessory="none", face_tex=1024, age=0.3,
        forehead_mark=False, sleeve_cuff=(0.11, 0.08), face=dict(cheek=1.15, age=0.2),
        colors=dict(skin="#e3b995", robe_top="#c29a5c", robe_hem="#8a6a3c", robe_motif="#5a4020",
                    robe_accent="#b58550", trim="#6a4a2a", thread="#b8a078", belt="#5a3e22",
                    scarf="#3f5a7a", lip="#a4585a"),
        robe_style="hemp"),
    "bandit": variant(
        MALE, "bandit", hair_style="ponytail", beard="short", face_tex=1024, stubble=0.8, jaw=0.72,
        face=dict(brow=1.35, nose=1.15, cheek=1.2), sleeve_cuff=(0.09, 0.07), age=0.25,
        colors=dict(skin="#cc946f", hair="#1a1412", robe_top="#4b4139", robe_hem="#2a2420",
                    robe_motif="#15110f", robe_accent="#5a4c40", trim="#3b1b15", thread="#6e5a44",
                    belt="#6b2b1b", band="#a01c1c", metal="#8c8a86", boots="#241c18"),
        robe_style="hemp"),
    "demon_cultivator": variant(
        MALE, "demon_cultivator", hair_style="loose", face_tex=1024, stubble=0.0, eye_glow="#ff2a1a",
        face=dict(cheek=1.25, brow=1.2, nose=1.0), jaw=0.5,
        colors=dict(skin="#e8d9d3", hair="#0f0a0c", hair_hl="#5a1a22", iris="#9a1010", lip="#5b2331",
                    brow="#140c0e", liner="#2a0a10", robe_top="#1d1318", robe_hem="#3c0a12",
                    robe_motif="#8e1020", robe_accent="#ff4a2a", trim="#5a0a14", thread="#d4a24a",
                    belt="#2a0a0e", metal="#6b5a4a", jade="#8a1020", boots="#120c0e"),
        robe_style="flames"),
    "blood_patriarch": variant(
        MALE, "blood_patriarch", hair_style="loose", horns=True, face_tex=1024, stubble=0.0,
        eye_glow="#ff3020", scale=1.12, shoulder=0.212, age=0.45, accessory="none",
        sleeve_cuff=(0.2, 0.13), face=dict(cheek=1.35, brow=1.5, nose=1.15, chin=1.2, age=0.4), jaw=0.62,
        colors=dict(skin="#d6c6c4", hair="#e9e5e2", hair_hl="#ffffff", brow="#cfc9c6", iris="#a01010",
                    lip="#4a1c26", liner="#1a0608", robe_top="#120b0e", robe_hem="#4a0810",
                    robe_motif="#b0182a", robe_accent="#ffb040", trim="#2a0408", thread="#e0b050",
                    belt="#5a0a12", metal="#c8a050", horn="#1c1416"),
        robe_style="flames"),
}
PLAYERS = [MALE, FEMALE]
HUMANOIDS = PLAYERS + list(VARIANTS.values())


# --------------------------------------------------------------------------
# skeleton layout
# --------------------------------------------------------------------------
def joints(cfg):
    sw = cfg["shoulder"]
    hw = cfg["hip"]
    a = R(62)  # A-pose: upper arm angle below horizontal
    d = V((math.cos(a), 0.0, -math.sin(a)))
    sh = V((sw, 0.0, 1.445))
    elbow = sh + d * 0.29 + V((0, 0.018, 0))
    wrist = elbow + d * 0.255 + V((0, -0.03, 0))
    hand = wrist + (wrist - elbow).normalized() * 0.095
    b = {
        "hips": (V((0, 0, 0.98)), V((0, 0, 1.10)), None),
        "spine": (V((0, 0, 1.10)), V((0, 0, 1.27)), "hips"),
        "chest": (V((0, 0, 1.27)), V((0, 0, 1.45)), "spine"),
        "neck": (V((0, 0.005, 1.47)), V((0, -0.005, 1.585)), "chest"),
        "head": (V((0, -0.005, 1.585)), V((0, -0.005, 1.80)), "neck"),
        "hair.1": (V((0, 0.095, 1.64)), V((0, 0.125, 1.42)), "head"),
        "hair.2": (V((0, 0.125, 1.42)), V((0, 0.14, 1.20)), "hair.1"),
        "hair.3": (V((0, 0.14, 1.20)), V((0, 0.15, 0.98)), "hair.2"),
    }
    for side, s in (("L", 1), ("R", -1)):
        m = V((s, 1, 1))

        def mir(v):
            return V((v.x * m.x, v.y, v.z))

        b[f"shoulder.{side}"] = (mir(V((0.025, 0.0, 1.425))), mir(sh), "chest")
        b[f"upper_arm.{side}"] = (mir(sh), mir(elbow), f"shoulder.{side}")
        b[f"forearm.{side}"] = (mir(elbow), mir(wrist), f"upper_arm.{side}")
        b[f"hand.{side}"] = (mir(wrist), mir(hand), f"forearm.{side}")
        b.update(anatomy.finger_bones(mir(wrist), mir(hand), side, hand_scale(cfg)))
        b[f"thigh.{side}"] = (mir(V((hw, 0.0, 0.94))), mir(V((hw, -0.012, 0.515))), "hips")
        b[f"shin.{side}"] = (mir(V((hw, -0.012, 0.515))), mir(V((hw, 0.018, 0.09))), f"thigh.{side}")
        b[f"foot.{side}"] = (mir(V((hw, 0.018, 0.09))), mir(V((hw, -0.085, 0.028))), f"shin.{side}")
        b[f"toe.{side}"] = (mir(V((hw, -0.085, 0.028))), mir(V((hw, -0.15, 0.022))), f"foot.{side}")
    return b


def hand_scale(cfg):
    return cfg.get("hand", 0.92 if cfg["female"] else 1.0)


def build_armature(cfg, bones):
    arm_data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", arm_data)
    util.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, (h, t, parent) in bones.items():
        e = eb.new(name)
        e.head = h
        e.tail = t
        # consistent roll: bone Z axis points to the character's back (+Y) where possible
        e.align_roll(V((0, 1, 0)) if abs((t - h).normalized().y) < 0.9 else V((0, 0, 1)))
    for name, (h, t, parent) in bones.items():
        if parent:
            eb[name].parent = eb[parent]
            eb[name].use_connect = (eb[parent].tail - eb[name].head).length < 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_data.display_type = "STICK"
    return arm


# --------------------------------------------------------------------------
# skin weights
# --------------------------------------------------------------------------
def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length, t


def seg_weights(p, bones, names, power=6.0, top=3):
    ws = {}
    for n in names:
        h, t, _ = bones[n]
        d, _ = _seg_dist(p, h, t)
        ws[n] = 1.0 / (d + 0.01) ** power
    best = sorted(ws.items(), key=lambda kv: -kv[1])[:top]
    s = sum(w for _, w in best)
    return {n: w / s for n, w in best}


def _chain_z(z, chain):
    """Piecewise linear blend along a vertical chain [(z, bone), ...]."""
    if z <= chain[0][0]:
        return {chain[0][1]: 1.0}
    for (z0, b0), (z1, b1) in zip(chain[:-1], chain[1:]):
        if z <= z1:
            t = util_smooth((z - z0) / (z1 - z0))
            return {b0: 1 - t, b1: t}
    return {chain[-1][1]: 1.0}


def util_smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _add(d, other, k=1.0):
    for n, w in other.items():
        d[n] = d.get(n, 0.0) + w * k
    return d


def w_torso(p, bones, s):
    """Robe body: vertical chain for the torso, blended legs for the skirt."""
    z = p.z / s
    chain = [(1.0, "hips"), (1.19, "spine"), (1.36, "chest"), (1.50, "chest"), (1.56, "neck")]
    w = _chain_z(z, chain)
    # skirt follows the legs progressively toward the hem
    legf = 0.8 * util_smooth((0.98 - z) / (0.98 - 0.40))
    if legf > 0:
        w = {n: v * (1 - legf) for n, v in w.items()}
        side_l = util_smooth((p.x / s + 0.07) / 0.14)
        shinf = util_smooth((0.62 - z) / 0.3)
        for side, f in (("L", side_l), ("R", 1 - side_l)):
            _add(w, {f"thigh.{side}": legf * f * (1 - shinf), f"shin.{side}": legf * f * shinf})
    # shoulders
    ax = abs(p.x / s)
    shf = util_smooth((ax - 0.10) / 0.10) * util_smooth((z - 1.30) / 0.1)
    if shf > 0:
        side = "L" if p.x > 0 else "R"
        w = {n: v * (1 - shf) for n, v in w.items()}
        _add(w, {f"shoulder.{side}": shf * 0.6, f"upper_arm.{side}": shf * 0.4})
    return w


def w_arm(p, bones, s, side):
    names = [f"shoulder.{side}", f"upper_arm.{side}", f"forearm.{side}", f"hand.{side}"]
    w = seg_weights(p, bones, names, power=5.0, top=2)
    joint = bones[f"upper_arm.{side}"][0]
    f = 1 - util_smooth(((p - joint).length / s - 0.03) / 0.09)
    if f > 0:
        w = {n: v * (1 - 0.55 * f) for n, v in w.items()}
        _add(w, {"chest": 0.35 * f, f"shoulder.{side}": 0.2 * f})
    # sleeves should not twist with the hand
    if f"hand.{side}" in w:
        _add(w, {f"forearm.{side}": w.pop(f"hand.{side}") * 0.8})
    return w


def w_hand(p, bones, s, side):
    h, t, _ = bones[f"hand.{side}"]
    along = (p - h).dot((t - h).normalized())
    names = [f"hand.{side}"] + [f"{f}.{i}.{side}" for f in anatomy.FINGERS + ("thumb",) for i in (1, 2, 3)]
    w = seg_weights(p, bones, names, power=9.0, top=2)
    f = util_smooth((along + 0.02 * s) / (0.05 * s))
    w = {n: v * f for n, v in w.items()}
    _add(w, {f"forearm.{side}": 1 - f})
    return w


def w_leg(p, bones, s, side):
    return seg_weights(p, bones, [f"shin.{side}", f"foot.{side}", f"toe.{side}"], power=6.0, top=2)


def w_hair(p, bones, s):
    z = p.z / s
    if z > 1.62:
        return {"head": 1.0}
    w = seg_weights(p, bones, ["head", "hair.1", "hair.2", "hair.3"], power=4.0, top=2)
    f = util_smooth((1.62 - z) / 0.12)
    w = {n: v * f for n, v in w.items()}
    _add(w, {"head": 1 - f})
    return w


def w_sidelock(p, bones, s):
    z = p.z / s
    f = util_smooth((1.56 - z) / 0.2) * 0.6
    return {"head": 1 - f, "chest": f}


def w_neck(p, bones, s):
    z = p.z / s
    return _chain_z(z, [(1.48, "chest"), (1.53, "neck"), (1.60, "neck"), (1.64, "head")])


def w_ribbon(p, bones, s):
    names = ["chest", "upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R", "spine"]
    return seg_weights(p, bones, names, power=6.0, top=2)


def assign(obj, fn, bones, s, *args):
    me = obj.data
    for v in me.vertices:
        p = obj.matrix_world @ v.co
        w = fn(p, bones, s, *args)
        tot = sum(w.values())
        for n, val in w.items():
            if val / tot < 1e-3:
                continue
            vg = obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)
            vg.add([v.index], val / tot, "REPLACE")


# --------------------------------------------------------------------------
# modelling helpers
# --------------------------------------------------------------------------
def _interp_rings(ctrl, samples=4):
    pts = [V(c) for c in ctrl]
    return util.catmull(pts, samples)


def surface_strip(name, bvh, path, width, mat, offset=0.004, thickness=0.004, samples=6,
                  u_scale=None, twist=None):
    """Ribbon lying on a surface (collar/lapel trims), UV u along its length."""
    pts = util.catmull([V(p) for p in path], samples)
    proj = []
    for p in pts:
        loc, nrm, _, _ = bvh.find_nearest(p)
        proj.append((loc, nrm))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rows = []
    length = 0.0
    lens = [0.0]
    for i in range(1, len(proj)):
        length += (proj[i][0] - proj[i - 1][0]).length
        lens.append(length)
    for i, (loc, nrm) in enumerate(proj):
        t = (proj[min(i + 1, len(proj) - 1)][0] - proj[max(i - 1, 0)][0]).normalized()
        side = nrm.cross(t).normalized()
        base = loc + nrm * offset
        rows.append((bm.verts.new(base - side * width * 0.5), bm.verts.new(base + side * width * 0.5)))
    us = u_scale or (1.0 / (width * 4))
    for i in range(len(rows) - 1):
        a, b = rows[i]
        c, d = rows[i + 1]
        f = bm.faces.new((a, b, d, c))
        for loop, (uu, vv) in zip(f.loops, ((lens[i], 0), (lens[i], 1), (lens[i + 1], 1),
                                             (lens[i + 1], 0))):
            loop[uv].uv = (uu * us, vv)
    obj = util.mesh_object(name, bm, mat)
    if thickness:
        util.solidify(obj, thickness, offset=1.0)
    return obj


def flat_ribbon(name, path, width, mat, outward_fn, samples=6, u_scale=1.0):
    """Free-hanging flat ribbon. outward_fn(p) returns the ribbon face normal."""
    pts = util.catmull([V(p) for p in path], samples)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rows = []
    lens = [0.0]
    for i in range(1, len(pts)):
        lens.append(lens[-1] + (pts[i] - pts[i - 1]).length)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = outward_fn(p)
        side = n.cross(t).normalized()
        w = width(lens[i] / lens[-1]) if callable(width) else width
        rows.append((bm.verts.new(p - side * w * 0.5), bm.verts.new(p + side * w * 0.5)))
    for i in range(len(rows) - 1):
        a, b = rows[i]
        c, d = rows[i + 1]
        f = bm.faces.new((a, b, d, c))
        for loop, (uu, vv) in zip(f.loops, ((lens[i], 0), (lens[i], 1), (lens[i + 1], 1),
                                             (lens[i + 1], 0))):
            loop[uv].uv = (uu * u_scale, vv)
    return util.mesh_object(name, bm, mat)


# --------------------------------------------------------------------------
# head
# --------------------------------------------------------------------------
def head_shape(d, fem, jaw, features=None):
    """Unit-sphere direction -> sculpted head surface (see anatomy.head_shape)."""
    return anatomy.head_shape(d, fem, jaw, features)


def build_head(cfg, J, mats, s):
    fem = cfg["female"]
    rx, ry, rz = (r * s for r in cfg["head_r"])
    centre = V((0, -0.012, 1.664)) * s
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    res = bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=64, radius=1.0)
    dirs = {}
    for v in bm.verts:
        d = v.co.normalized()
        dirs[v] = d
        v.co = centre + head_shape(d, fem, cfg["jaw"], cfg.get("face"))
    for v in bm.verts:
        q = v.co - centre
        v.co = centre + V((q.x * rx, q.y * ry, q.z * rz))
    for f in bm.faces:
        us = []
        for loop in f.loops:
            d = dirs[loop.vert]
            lon = math.atan2(d.x, -d.y)
            u = tex.lon_to_u(lon)
            vv = math.asin(max(-1, min(1, d.z))) / math.pi + 0.5
            us.append([u, vv])
        umin, umax = min(u[0] for u in us), max(u[0] for u in us)
        if umax - umin > 0.5:
            for u in us:
                if u[0] < 0.5:
                    u[0] += 1.0
        for loop, u in zip(f.loops, us):
            loop[uv].uv = u
    head = util.mesh_object("Head", bm, mats["face"])

    def surf(dx, dz):
        d = V((dx, -math.sqrt(max(0.0, 1 - dx * dx - dz * dz)), dz))
        q = head_shape(d, fem, cfg["jaw"], cfg.get("face"))
        return centre + V((q.x * rx, q.y * ry, q.z * rz))

    parts = [head]
    # eyes + lids
    er = (0.0126 if fem else 0.0119) * s
    for side in (1, -1):
        sp = surf(0.37 * side, 0.075)
        c = sp + V((0, 0.30 * er, 0))
        bm = bmesh.new()
        util.sphere(bm, er, segs=24, rings=16)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(R(90), 3, "X"))
        bmesh.ops.translate(bm, verts=bm.verts, vec=c)
        parts.append(util.mesh_object("Eye", bm, mats["eye"]))
        # eyelid shell around an almond opening (outer corner lifted = phoenix eye)
        parts.append(eyelid_shell(c, er * 1.1, side, fem, mats["lid"]))
    # ears: helix, antihelix, concha and lobe, set behind the jaw at eye-to-nose height
    for side in (1, -1):
        bm = bmesh.new()
        loc = surf(0.985 * side, -0.16) + V((side * 0.002 * s, 0.02 * s, 0))
        anatomy.ear(bm, loc, side, s, 1.0 if not fem else 0.92)
        o = util.mesh_object("Ear", bm, mats["skin"])
        util.box_uv(o, 6.0)
        parts.append(o)
    return parts, centre, (rx, ry, rz)


def eyelid_shell(c, lr, side, fem, mat, cols=40, rows=8):
    tilt = 0.20 if fem else 0.12
    w = 0.97
    up_h, lo_h = (0.30, 0.22) if fem else (0.22, 0.2)

    def inside(lx, lz):
        if abs(lx) >= w:
            return False
        k = 1 - (lx / w) ** 2
        base = tilt * lx
        return base - lo_h * k ** 0.9 < lz < base + up_h * k ** 0.8

    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    grid = []
    for i in range(cols):
        phi = 2 * math.pi * i / cols
        cx, cz = math.cos(phi), math.sin(phi)
        lo, hi = 0.0, 1.0
        for _ in range(24):
            mid = (lo + hi) * 0.5
            if inside(mid * cx, mid * cz):
                lo = mid
            else:
                hi = mid
        tb = math.asin(min(lo, 0.999))
        tmax = R(105)
        col = []
        for j in range(rows + 1):
            th = tb + (tmax - tb) * (j / rows) ** 1.4
            p = V((math.sin(th) * cx * side, -math.cos(th), math.sin(th) * cz)) * lr
            col.append(bm.verts.new(c + p))
        grid.append(col)
    for i in range(cols):
        i2 = (i + 1) % cols
        for j in range(rows):
            vs = (grid[i][j], grid[i][j + 1], grid[i2][j + 1], grid[i2][j])
            f = bm.faces.new(vs if side > 0 else tuple(reversed(vs)))
            for loop in f.loops:
                ii = next(k for k in (i, i2) if loop.vert in grid[k])
                jj = grid[ii].index(loop.vert)
                loop[uv].uv = (ii / cols, jj / rows)
    return util.mesh_object("Eyelid", bm, mat)


def hairline_table(fem):
    """(|longitude|, unit-sphere z) points of the scalp hairline."""
    if fem:
        return [(0.0, 0.42), (0.35, 0.34), (0.9, 0.12), (1.25, -0.05), (1.5, -0.25),
                (1.9, -0.45), (2.4, -0.62), (math.pi, -0.7)]
    return [(0.0, 0.50), (0.45, 0.45), (0.9, 0.28), (1.25, 0.08), (1.5, -0.12),
            (1.65, -0.10), (1.85, -0.35), (2.4, -0.55), (math.pi, -0.62)]


def hairline(lon, fem):
    """Minimum unit-sphere z where the scalp hair starts, by |longitude|."""
    table = hairline_table(fem)
    a = abs(lon)
    for (a0, z0), (a1, z1) in zip(table[:-1], table[1:]):
        if a <= a1:
            t = (a - a0) / (a1 - a0)
            return z0 + (z1 - z0) * t
    return table[-1][1]


def build_hair(cfg, mats, centre, radii, s):
    """Scalp cap plus a hair style, optional beard and horns (see cfg hair_style/beard/horns)."""
    fem = cfg["female"]
    style = cfg.get("hair_style", "buns" if fem else "topknot")
    rx, ry, rz = radii
    parts = []
    fshape = cfg.get("face")

    def scalp(name, mat, lift=1.0, lo=None):
        """Shell from the hairline (or unit-sphere z `lo`) up to the crown."""
        bm = bmesh.new()
        uv = bm.loops.layers.uv.verify()
        cols, rows = 72, 16
        grid = []
        for j in range(rows + 1):
            row = []
            for i in range(cols):
                lon = -math.pi + 2 * math.pi * i / cols
                z0 = hairline(lon, fem) if lo is None else lo(lon)
                t = j / rows
                z = min(z0 + (1 - z0) * t ** 0.85, 0.995)
                r = math.sqrt(1 - z * z)
                d = V((math.sin(lon) * r, -math.cos(lon) * r, z))
                q = head_shape(d, fem, cfg["jaw"], fshape)
                infl = (1.035 + 0.045 * max(0.0, z) ** 2 + 0.02 * max(0.0, d.y)
                        - 0.02 * (1 - t) ** 3) * lift
                row.append(bm.verts.new(centre + V((q.x * rx * infl, q.y * ry * infl, q.z * rz * infl))))
            grid.append(row)
        for j in range(rows):
            for i in range(cols):
                i2 = (i + 1) % cols
                f = bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
                for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uv].uv = (uu / cols * 4.0, vv / rows * 1.2)
        f = bm.faces.new(grid[rows])
        for loop in f.loops:
            loop[uv].uv = (0.5, 1.2)
        o = util.mesh_object(name, bm, mat)
        util.solidify(o, 0.004 * s, offset=1.0)
        return o

    def surf(dx, dz, infl=1.0):
        d = V((dx, -math.sqrt(max(0.0, 1 - dx * dx - dz * dz)), dz))
        q = head_shape(d, fem, cfg["jaw"], fshape)
        return centre + V((q.x * rx * infl, q.y * ry * infl, q.z * rz * infl))

    def around(lon, z, infl=1.0):
        """Point on the head at longitude lon (0 = face) and unit height z, pushed out by infl."""
        r = math.sqrt(1 - z * z)
        q = head_shape(V((math.sin(lon) * r, -math.cos(lon) * r, z)), fem, cfg["jaw"], fshape)
        return centre + V((q.x * rx * infl, q.y * ry * infl, q.z * rz * infl))

    if style != "scarf":
        parts.append(("head", scalp("HairCap", mats["hair"])))

    top = centre + V((0, 0.0, rz * 1.02))
    back = centre + V((0, ry * 0.9, -rz * 0.2))

    def lock(name, path, r0, r1, flat=0.35, weight="hair", n=10, mat="hair"):
        bm = bmesh.new()
        pts = util.catmull([V(p) for p in path], 6)

        def rad(t):
            r = r0 + (r1 - r0) * t ** 0.8
            return (r, r * flat)
        util.tube(bm, pts, rad, n=n, up=(0, 1, 0), uv_scale=(1.0, 6.0))
        o = util.mesh_object(name, bm, mats[mat])
        parts.append((weight, o))
        return o

    def solid(name, bm, mat, uvs=8.0, weight="head"):
        o = util.mesh_object(name, bm, mats[mat])
        if uvs:
            util.box_uv(o, uvs)
        parts.append((weight, o))
        return o

    def back_hair(xs_list, length, spread=1.3, depth=0.162):
        mid = (len(xs_list) - 1) / 2
        for i, x in enumerate(xs_list):
            xs = x * s
            ln = length + 0.05 * abs(i - mid) / max(mid, 1) - 0.03 * (i % 2)
            path = [back + V((xs * 0.6, -0.03 * s, 0.09 * s)), back + V((xs, 0.012 * s, -0.05 * s)),
                    V((xs * 1.2, (depth - 0.04) * s, 1.47 * s)), V((xs * spread, depth * s, 1.34 * s))]
            if ln < 1.2:
                path.append(V((xs * spread, (depth + 0.016) * s, 1.15 * s)))
            path.append(V((xs * (spread - 0.1) + 0.006 * s * (i - mid), (depth + 0.028) * s, ln * s)))
            lock(f"HairBack{i}", path, 0.034 * s, 0.012 * s, flat=0.38)

    def side_locks(r0, reach, thick=0.0065):
        for side in (1, -1):
            path = [centre + V((side * rx * 0.72, -ry * 0.62, rz * 0.55)),
                    centre + V((side * rx * 0.98, -ry * 0.62, rz * 0.12)),
                    centre + V((side * rx * 1.06, -ry * 0.50, -rz * 0.35)),
                    centre + V((side * rx * 1.02, -ry * 0.42, -rz * reach))]
            for k, off in enumerate((-0.006, 0.0, 0.006)):
                p2 = [q + V((side * abs(off) * 0.4 * s, off * s, -0.004 * s * k)) for q in path]
                lock("SideLock", p2, thick * s, 0.0012 * s, flat=0.3, weight="side", n=8)

    def topknot(size=1.0, crown=True, pin=True, bun_mat="hair"):
        bun_c = top + V((0, 0.012 * s, 0.018 * s * size))
        bm = bmesh.new()
        util.sphere(bm, 0.036 * s * size, loc=bun_c, segs=20, rings=12, scale=(0.95, 1.0, 0.85))
        solid("Topknot", bm, bun_mat)
        if crown:
            bm = bmesh.new()
            prof = [(0.030, -0.012), (0.036, 0.0), (0.038, 0.02), (0.030, 0.040), (0.018, 0.052),
                    (0.004, 0.056)]
            util.lathe(bm, [(r * s * size, z * s * size) for r, z in prof], segs=20, loc=bun_c, cap_top=True)
            bmesh.ops.scale(bm, vec=(0.75, 1.15, 1.0), verts=bm.verts, space=Matrix.Translation(-bun_c))
            solid("Crown", bm, "metal", 0)
        if pin:
            bm = bmesh.new()
            util.cylinder(bm, 0.004 * s, 0.003 * s, 0.14 * s, loc=bun_c + V((0, 0, 0.026 * s * size)),
                          rot=Matrix.Rotation(R(90), 4, "Y"), segs=8)
            util.sphere(bm, 0.008 * s, loc=bun_c + V((0.07 * s, 0, 0.026 * s * size)), segs=10, rings=6)
            solid("Hairpin", bm, "jade", 0)
        return bun_c

    if style in ("topknot", "elder"):
        topknot(1.15 if style == "elder" else 1.0)
        back_hair((-0.05, -0.025, 0.0, 0.025, 0.05), 1.20, spread=1.25, depth=0.152)
        side_locks(0.0065, 0.85)
    elif style == "buns":
        for side in (1, -1):
            loop_c = top + V((side * 0.04 * s, 0.03 * s, 0.025 * s))
            pts = [V((math.cos(a) * 0.028 * s, 0, math.sin(a) * 0.036 * s))
                   for a in [2 * math.pi * k / 24 for k in range(25)]]
            bm = bmesh.new()
            rot = Matrix.Rotation(R(-25 * side), 3, "Y") @ Matrix.Rotation(R(20), 3, "X")
            util.tube(bm, [loop_c + rot @ p for p in pts], 0.013 * s, n=10, uv_scale=(1.0, 4.0),
                      closed_ends=False)
            solid("HairLoop", bm, "hair", 0)
        bm = bmesh.new()
        util.sphere(bm, 0.042 * s, loc=top + V((0, 0.045 * s, 0.0)), segs=20, rings=12, scale=(1.3, 1.0, 0.8))
        solid("HairBun", bm, "hair")
        if cfg.get("ornaments", True):
            bm = bmesh.new()
            for side in (1, -1):
                base = top + V((side * 0.06 * s, 0.02 * s, 0.01 * s))
                tip = base + V((side * 0.07 * s, -0.02 * s, 0.03 * s))
                util.tube(bm, [base, tip], 0.0025 * s, n=6)
                for k in range(5):
                    a = 2 * math.pi * k / 5
                    util.sphere(bm, 0.009 * s, loc=tip + V((math.cos(a) * 0.01 * s, 0, math.sin(a) * 0.01 * s)),
                                segs=8, rings=5, scale=(1, 0.4, 1))
                for k in range(3):
                    bead = tip + V((side * 0.004 * k * s, -0.004 * s, -0.02 * s * (k + 1)))
                    util.sphere(bm, 0.0045 * s, loc=bead, segs=8, rings=5)
                    util.tube(bm, [tip, bead], 0.0008 * s, n=4)
            solid("Ornament", bm, "metal", 0)
            bm = bmesh.new()
            fl = top + V((0.07 * s, -0.01 * s, -0.01 * s))
            for k in range(5):
                a = 2 * math.pi * k / 5
                util.sphere(bm, 0.011 * s, loc=fl + V((math.cos(a) * 0.012 * s, -0.004 * s, math.sin(a) * 0.012 * s)),
                            segs=8, rings=5, scale=(1, 0.35, 1))
            solid("Blossom", bm, "accent", 0)
        back_hair((-0.075, -0.05, -0.025, 0.0, 0.025, 0.05, 0.075), 0.97)
        side_locks(0.0085, 0.9, 0.0085)
    elif style == "crown":
        # a tall single bun held by an ornate phoenix crown
        bun_c = topknot(1.35, crown=False, pin=True)
        bm = bmesh.new()
        prof = [(0.042, -0.02), (0.05, 0.0), (0.052, 0.03), (0.046, 0.06), (0.03, 0.08), (0.006, 0.09)]
        util.lathe(bm, [(r * s, z * s) for r, z in prof], segs=24, loc=bun_c, cap_top=True)
        bmesh.ops.scale(bm, vec=(0.8, 1.2, 1.0), verts=bm.verts, space=Matrix.Translation(-bun_c))
        for side in (1, -1):   # phoenix wings sweeping back from the crown
            wing = [bun_c + V((side * 0.04 * s, 0, 0.04 * s)), bun_c + V((side * 0.09 * s, 0.03 * s, 0.07 * s)),
                    bun_c + V((side * 0.12 * s, 0.07 * s, 0.05 * s))]
            util.tube(bm, util.catmull(wing, 4), lambda t: (0.006 - 0.004 * t) * s, n=6)
        solid("Crown", bm, "metal", 0)
        back_hair((-0.075, -0.05, -0.025, 0.0, 0.025, 0.05, 0.075), 0.92)
        side_locks(0.0075, 0.9, 0.0075)
    elif style == "ponytail":
        tie = top + V((0, 0.07 * s, -0.01 * s))
        bm = bmesh.new()
        util.sphere(bm, 0.02 * s, loc=tie, segs=14, rings=8)
        solid("Tie", bm, "hair")
        for k, x in enumerate((-0.012, 0.0, 0.012)):
            path = [tie + V((x * s, 0, 0)), tie + V((x * 1.5 * s, 0.05 * s, -0.04 * s)),
                    V((x * 2 * s, 0.14 * s, 1.52 * s)), V((x * 2.5 * s, 0.16 * s, 1.36 * s)),
                    V((x * 2.8 * s, 0.155 * s, 1.24 * s))]
            lock(f"Ponytail{k}", path, 0.02 * s, 0.006 * s, flat=0.5)
        # headband round the brow, knotted at the back with trailing tails
        bm = bmesh.new()
        ring_ = [around(a, 0.36, 1.06) for a in [2 * math.pi * k / 36 - math.pi for k in range(37)]]
        util.tube(bm, ring_, (0.004 * s, 0.012 * s), n=8, up=(0, 0, 1), closed_ends=False)
        knot = centre + V((0, ry * 1.05, 0.36 * rz))
        for side in (1, -1):
            util.tube(bm, util.catmull([knot, knot + V((side * 0.02 * s, 0.03 * s, -0.06 * s)),
                                        knot + V((side * 0.03 * s, 0.04 * s, -0.16 * s))], 4),
                      (0.0025 * s, 0.01 * s), n=6, up=(0, 1, 0))
        solid("Headband", bm, "band", 30)
        side_locks(0.006, 0.6)
    elif style == "loose":
        back_hair((-0.09, -0.065, -0.04, -0.015, 0.015, 0.04, 0.065, 0.09), 0.9, spread=1.35, depth=0.17)
        side_locks(0.009, 1.6, 0.009)
        for side in (1, -1):   # bangs swept to the sides
            path = [centre + V((0, -ry * 0.8, rz * 0.9)), centre + V((side * rx * 0.5, -ry * 1.02, rz * 0.62)),
                    centre + V((side * rx * 0.95, -ry * 0.82, rz * 0.3))]
            lock("Bangs", path, 0.012 * s, 0.003 * s, flat=0.3, weight="head", n=8)
    elif style == "scarf":
        parts.append(("head", scalp("Scarf", mats["scarf"], 1.08, lo=lambda lon: 0.25 if abs(lon) < 1.3 else -0.35)))
        knot = centre + V((0, ry * 1.02, 0.1 * rz))
        bm = bmesh.new()
        util.sphere(bm, 0.024 * s, loc=knot, segs=12, rings=8, scale=(1.3, 0.8, 1.0))
        for side in (1, -1):
            util.tube(bm, util.catmull([knot, knot + V((side * 0.03 * s, 0.03 * s, -0.08 * s)),
                                        knot + V((side * 0.035 * s, 0.035 * s, -0.17 * s))], 4),
                      (0.004 * s, 0.018 * s), n=6, up=(0, 1, 0))
        solid("ScarfKnot", bm, "scarf", 20)
        side_locks(0.006, 0.4)
    elif style == "hat":
        topknot(0.8, crown=False, pin=False)
        bm = bmesh.new()   # douli: a conical bamboo hat
        hc = top + V((0, 0.01 * s, 0.01 * s))
        prof = [(0.25, -0.03), (0.23, -0.02), (0.16, 0.03), (0.08, 0.07), (0.01, 0.1)]
        util.lathe(bm, [(r * s, z * s) for r, z in prof], segs=32, loc=hc, cap_top=True)
        solid("Hat", bm, "straw", 6)
        bm = bmesh.new()
        chin = surf(0.0, -0.95, 1.02)
        strap = [surf(0.97, -0.1, 1.04), surf(0.8, -0.7, 1.05), chin + V((0, 0.004 * s, -0.005 * s)),
                 surf(-0.8, -0.7, 1.05), surf(-0.97, -0.1, 1.04)]
        util.tube(bm, util.catmull(strap, 4), 0.0018 * s, n=5)
        solid("HatStrap", bm, "band", 30)
        back_hair((-0.02, 0.0, 0.02), 1.3, spread=1.1, depth=0.15)
    # beards: moustache and chin locks
    beard = cfg.get("beard")
    if beard:
        mcol = "beard"
        for side in (1, -1):
            path = [surf(side * 0.05, -0.5, 1.01), surf(side * 0.2, -0.56, 1.03), surf(side * 0.3, -0.68, 1.03)]
            if beard == "long":
                path.append(surf(side * 0.32, -0.86, 1.08) + V((0, -0.01 * s, -0.03 * s)))
            lock("Moustache", path, 0.0065 * s, 0.0015 * s, flat=0.45, weight="head", n=8, mat=mcol)
        n_locks = 11 if beard == "long" else 5
        length = 0.19 if beard == "long" else 0.035
        rnd = __import__("random").Random(5)
        for k in range(n_locks):
            x = (k - (n_locks - 1) / 2) * (0.05 if beard == "long" else 0.06)
            root = surf(x, -0.86, 1.0)
            ln = length * (1 - 0.45 * (abs(x) / 0.25) ** 2) * rnd.uniform(0.85, 1.1)
            tipv = root + V((x * 0.01 * s, -0.02 * s, -ln * s))
            path = [surf(x * 1.3, -0.72, 1.02), root + V((0, -0.008 * s, 0)),
                    root.lerp(tipv, 0.5) + V((0, -0.016 * s, 0)), tipv]
            thick = 0.014 if beard == "long" else 0.008
            lock("Beard", path, thick * s, 0.002 * s, flat=0.4, weight="head", n=8, mat=mcol)
    if cfg.get("horns"):
        bm = bmesh.new()
        for side in (1, -1):
            root = surf(side * 0.45, 0.62, 1.0)
            path = [root, root + V((side * 0.03 * s, 0.03 * s, 0.07 * s)), root + V((side * 0.07 * s, 0.1 * s, 0.12 * s)),
                    root + V((side * 0.1 * s, 0.2 * s, 0.13 * s)), root + V((side * 0.1 * s, 0.27 * s, 0.1 * s))]
            util.tube(bm, util.catmull(path, 5), lambda t: (0.022 - 0.02 * t) * s, n=10)
        solid("Horns", bm, "horn", 10)
    return parts


# --------------------------------------------------------------------------
# body & outfit
# --------------------------------------------------------------------------
def fold(p, yc, s, n=17, amp=0.045):
    """Vertical pleats: push ring points in/out with a smooth wave below the waist."""
    z = p.z / s
    k = amp * util_smooth((1.02 - z) / 0.55)
    if k <= 0:
        return p
    ang = math.atan2(p.y - yc, p.x)
    wave = math.sin(n * ang + 0.7 * math.sin(3 * ang)) * (0.6 + 0.4 * math.sin(2 * ang + 1.0))
    c = V((0, yc, p.z))
    return c + (p - c) * (1 + k * wave)


def build_outfit(cfg, J, mats, s):
    fem = cfg["female"]
    parts = []   # (weight kind, object, extra)
    # --- robe body: loft of superellipse rings from hem to collar
    ctrl = [V((z * s, w * s, d * s, y * s, p)) for (z, w, d, y, p) in cfg["robe"]]
    samples = util.catmull(ctrl, 5)
    rings = []
    n = 48
    n = 64
    for c in samples:
        z, w, d, y, pw = c
        r = util.ring((0, y, z), (1, 0, 0), (0, 1, 0), w, d, n, start=-math.pi / 2, power=pw)
        rings.append([fold(p, y, s) for p in r])
    # tuck the hem inward so the robe reads as having thickness
    hem = samples[0]
    inner = [fold(p, hem[3], s) for p in
             util.ring((0, hem[3], hem[0] + 0.03 * s), (1, 0, 0), (0, 1, 0), hem[1] * 0.93,
                       hem[2] * 0.93, n, start=-math.pi / 2, power=hem[4])]
    bm = bmesh.new()
    height = samples[-1][0] - samples[0][0]
    vvals = [(c[0] - samples[0][0]) / height for c in samples]
    util.loft(bm, [inner] + rings, closed=True, cap_start=True,
              v_values=[-0.01] + vvals)
    robe = util.mesh_object("Robe", bm, mats["robe"])
    parts.append(("torso", robe))
    bvh_bm = bmesh.new()
    bvh_bm.from_mesh(robe.data)
    bvh = BVHTree.FromBMesh(bvh_bm)

    def robe_ring_at(zq):
        for a, b in zip(samples[:-1], samples[1:]):
            if a[0] <= zq <= b[0]:
                t = (zq - a[0]) / (b[0] - a[0])
                return a.lerp(b, t)
        return samples[-1]

    # --- sleeves
    cw, cd = cfg["sleeve_cuff"]
    for side, sg in (("L", 1), ("R", -1)):
        sh, el, _ = J[f"upper_arm.{side}"]
        _, wr, _ = J[f"forearm.{side}"]
        d = (wr - el).normalized()
        cuff = wr + d * 0.035 * s
        start = sh - (el - sh).normalized() * 0.015 * s
        path = util.catmull([start, sh, el, wr, cuff], 5)
        tot = len(path) - 1

        def rad(t):
            r_sh, r_el = 0.062 * s, 0.072 * s
            if t < 0.5:
                r = r_sh + (r_el - r_sh) * t * 2
                return (r, r)
            k = util_smooth((t - 0.5) / 0.5) ** 1.3
            return (r_el + (cw * s - r_el) * k, r_el + (cd * s - r_el) * k)

        bm = bmesh.new()
        def sink(t):
            return (-0.05 * s * (1 - util_smooth(t / 0.45)), 0.0)
        util.tube(bm, path, rad, n=24, up=(0, 0, 1), closed_ends=False, uv_scale=(1.0, 0.25),
                  profile=sink)
        # move sleeve UVs into the upper (plain) part of the robe texture
        uvl = bm.loops.layers.uv.active
        for f in bm.faces:
            for loop in f.loops:
                u_, v_ = loop[uvl].uv
                loop[uvl].uv = (u_, 0.62 + v_ * 0.5)
        sl = util.mesh_object(f"Sleeve.{side}", bm, mats["robe"])
        parts.append(("arm", sl, side))
        # cuff trim band
        bm = bmesh.new()
        c0 = cuff - d * 0.05 * s
        rings_c = []
        for pt, grow in ((c0, 1.0), (cuff, 1.0)):
            t_ = 1.0 if pt is cuff else 0.93
            rx_, ry_ = rad(t_)
            fr = util.frames_along([wr, cuff])[-1]
            b = d.cross(V((0, 0, 1))).normalized()
            nn = b.cross(d).normalized()
            rings_c.append(util.ring(pt, b, nn, rx_ * 1.02, ry_ * 1.02, 32))
        util.loft(bm, rings_c, closed=True, uv_scale=(6.0, 1.0 / (0.05 * s)))
        o = util.mesh_object(f"Cuff.{side}", bm, mats["trim"])
        parts.append(("arm", o, side))
        # hand: one subdivided surface with knuckles, finger pads and nails
        _, hand_t, _ = J[f"hand.{side}"]
        o, nails = anatomy.hand_mesh(wr, hand_t, side, s * hand_scale(cfg), mats["skin"], mats["nail"],
                                     fem)
        parts.append(("hand", nails, side))
        parts.append(("hand", o, side))
    # --- neck
    bm = bmesh.new()
    anatomy.neck(bm, s, cfg["neck_r"] * s, fem)
    neck = util.mesh_object("Neck", bm, mats["skin"])
    parts.append(("neck", neck))
    # --- collar trims (left lapel over right: wearer's left crosses to the right hip)
    back_neck = V((0, 0.07, 1.53))
    outer = [back_neck, V((0.055, 0.045, 1.53)), V((0.075, -0.01, 1.51)), V((0.045, -0.075, 1.47)),
             V((-0.01, -0.12, 1.38)), V((-0.07, -0.13, 1.27)), V((-0.12, -0.11, 1.16)),
             V((-0.15, -0.07, 1.10))]
    inner_l = [back_neck, V((-0.055, 0.045, 1.53)), V((-0.075, -0.01, 1.51)), V((-0.045, -0.07, 1.47)),
               V((0.0, -0.105, 1.41))]
    outer = [p * s for p in outer]
    inner_l = [p * s for p in inner_l]
    tw = (0.05 if not fem else 0.045) * s
    parts.append(("torso", surface_strip("CollarOuter", bvh, outer, tw, mats["trim"], 0.005 * s,
                                         0.004 * s, u_scale=1.0 / (tw * 5))))
    parts.append(("torso", surface_strip("CollarInner", bvh, inner_l, tw, mats["trim"], 0.004 * s,
                                         0.004 * s, u_scale=1.0 / (tw * 5))))
    # white under-robe collar peeking above the trim
    under = [back_neck + V((0, 0.0, 0.012)) * 1, V((0.06, 0.035, 1.545)), V((0.06, -0.035, 1.525)),
             V((0.0, -0.08, 1.475)), V((-0.06, -0.035, 1.525)), V((-0.06, 0.035, 1.545)),
             back_neck + V((0, 0.0, 0.012))]
    under = [p * s for p in under]
    parts.append(("torso", surface_strip("UnderCollar", bvh, under, 0.022 * s, mats["under"],
                                         0.003 * s, 0.003 * s)))
    # --- hem trim
    bm = bmesh.new()
    hr = []
    for zq in (samples[0][0] + 0.002, samples[0][0] + 0.07 * s):
        c = robe_ring_at(zq)
        hr.append([fold(p, c[3], s) for p in
                   util.ring((0, c[3], zq), (1, 0, 0), (0, 1, 0), c[1] * 1.012, c[2] * 1.012, n,
                             start=-math.pi / 2, power=c[4])])
    util.loft(bm, hr, closed=True, uv_scale=(14.0, 1.0 / (0.07 * s)))
    parts.append(("torso", util.mesh_object("HemTrim", bm, mats["trim"])))
    # --- belt / sash
    bm = bmesh.new()
    br = []
    bz = (1.035, 1.06, 1.12, 1.145) if not fem else (1.05, 1.07, 1.16, 1.18)
    grow = (1.03, 1.07, 1.07, 1.03)
    for zq, g in zip(bz, grow):
        c = robe_ring_at(zq * s)
        br.append(util.ring((0, c[3], zq * s), (1, 0, 0), (0, 1, 0), c[1] * g, c[2] * g, n,
                            start=-math.pi / 2, power=c[4]))
    util.loft(bm, br, closed=True, uv_scale=(10.0, 1.0 / ((bz[-1] - bz[0]) * s)))
    parts.append(("torso", util.mesh_object("Belt", bm, mats["belt"])))
    # belt knot + hanging sash tails
    front_z = (bz[1] + bz[2]) * 0.5 * s
    c = robe_ring_at(front_z)
    knot = V((0.03 * s, c[3] - c[2] * 1.08, front_z))
    bm = bmesh.new()
    util.sphere(bm, 0.022 * s, loc=knot, segs=12, rings=8, scale=(1.3, 0.6, 1.0))
    o = util.mesh_object("BeltKnot", bm, mats["belt"])
    util.box_uv(o, 10)
    parts.append(("torso", o))
    for k, (dx, ln) in enumerate(((0.012, 0.42), (0.05, 0.36))):
        path = []
        for i in range(6):
            zq = front_z - ln * s * i / 5
            cc = robe_ring_at(max(zq, samples[0][0]))
            path.append(V(((0.03 + dx) * s + 0.01 * s * i * (k - 0.5), cc[3] - cc[2] * 1.12 - 0.004 * s * i, zq)))
        parts.append(("torso", flat_ribbon("SashTail", path, lambda t: (0.05 - 0.01 * t) * s,
                                           mats["belt"], lambda p: V((0, -1, 0)), u_scale=3.0)))
    # jade pendant with tassel on the left hip
    pj = V((0.12 * s, c[3] - c[2] * 0.95, front_z - 0.18 * s))
    bm = bmesh.new()
    util.cylinder(bm, 0.028 * s, 0.028 * s, 0.008 * s, loc=pj, rot=Matrix.Rotation(R(90), 4, "X"), segs=20)
    o = util.mesh_object("JadePendant", bm, mats["jade"])
    util.box_uv(o, 20)
    parts.append(("torso", o))
    bm = bmesh.new()
    util.tube(bm, [V((0.12 * s, c[3] - c[2] * 1.04, front_z)), pj + V((0, 0, 0.028 * s))], 0.002 * s, n=6)
    util.cylinder(bm, 0.004 * s, 0.014 * s, 0.10 * s, loc=pj - V((0, 0, 0.08 * s)), segs=10)
    o = util.mesh_object("Tassel", bm, mats["tassel"])
    util.box_uv(o, 20)
    parts.append(("torso", o))
    # --- boots (only the toes show under the hem)
    for side, sg in (("L", 1), ("R", -1)):
        sh_h, ank, _ = J[f"shin.{side}"]
        _, toe_t, _ = J[f"toe.{side}"]
        x = ank.x
        bm = bmesh.new()
        path = [V((x, 0.05 * s, 0.05 * s)), V((x, 0.0, 0.055 * s)), V((x, -0.07 * s, 0.045 * s)),
                V((x, -0.14 * s, 0.035 * s)), V((x, -0.175 * s, 0.05 * s))]
        prof = [(0.036, 0.040), (0.042, 0.050), (0.045, 0.040), (0.036, 0.028), (0.008, 0.01)]

        def brad(t, prof=prof):
            i = t * (len(prof) - 1)
            i0 = min(int(i), len(prof) - 2)
            f = i - i0
            a, b = prof[i0], prof[i0 + 1]
            return ((a[0] + (b[0] - a[0]) * f) * s, (a[1] + (b[1] - a[1]) * f) * s)
        util.tube(bm, util.catmull(path, 4), brad, n=14, up=(0, 0, 1))
        util.tube(bm, [V((x, 0.012 * s, 0.05 * s)), V((x, 0.015 * s, 0.34 * s))],
                  lambda t: 0.045 * s * (1 + 0.1 * t), n=14)
        o = util.mesh_object(f"Boot.{side}", bm, mats["boots"])
        util.box_uv(o, 6)
        parts.append(("leg", o, side))
        bm = bmesh.new()
        util.box(bm, (0.09 * s, 0.25 * s, 0.018 * s), loc=(x, -0.05 * s, 0.009 * s))
        bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.006 * s, segments=2, affect="EDGES")
        o = util.mesh_object(f"Sole.{side}", bm, mats["sole"])
        util.box_uv(o, 10)
        parts.append(("leg", o, side))
    return parts, bvh, robe_ring_at


def build_sword(mats, s, J):
    """Jian in its scabbard hanging from the left hip."""
    bm_s = bmesh.new()
    bm_m = bmesh.new()
    bm_g = bmesh.new()
    hip = V((0.2 * s, -0.02 * s, 1.03 * s))
    direction = V((0.10, 0.80, -0.59)).normalized()
    guard = hip - direction * 0.12 * s
    tip = guard + direction * 0.78 * s
    # scabbard (flattened, slightly tapered)
    up = V((1, 0, 0))
    util.tube(bm_s, [guard, tip], lambda t: (0.026 * s * (1 - 0.25 * t), 0.012 * s), n=12, up=up,
              power=2.6)
    # chape and locket fittings
    util.tube(bm_m, [tip - direction * 0.06 * s, tip + direction * 0.01 * s],
              lambda t: (0.021 * s * (1 - 0.4 * t), 0.0135 * s), n=12, up=up)
    util.tube(bm_m, [guard + direction * 0.01 * s, guard + direction * 0.06 * s],
              (0.029 * s, 0.015 * s), n=12, up=up)
    # guard (cross), grip and pommel
    gc = guard - direction * 0.01 * s
    side = direction.cross(up).normalized()
    util.tube(bm_m, [gc - up * 0.05 * s, gc, gc + up * 0.05 * s],
              lambda t: (0.012 * s * (1 - 0.5 * abs(t - 0.5)), 0.02 * s), n=8, up=side)
    g0 = gc - direction * 0.012 * s
    g1 = g0 - direction * 0.16 * s
    util.tube(bm_g, [g0, g1], (0.014 * s, 0.011 * s), n=10, up=up)
    util.sphere(bm_m, 0.018 * s, loc=g1 - direction * 0.01 * s, segs=12, rings=8, scale=(1, 1, 0.7))
    parts = []
    for bm, name, mat, sc in ((bm_s, "Scabbard", mats["lacquer"], 8), (bm_m, "SwordFittings", mats["metal"], 10),
                              (bm_g, "SwordGrip", mats["belt"], 20)):
        o = util.mesh_object(name, bm, mat)
        util.box_uv(o, sc)
        parts.append(o)
    # sword tassel
    bm = bmesh.new()
    pom = g1 - direction * 0.02 * s
    util.tube(bm, [pom, pom + V((0, 0.01, -0.06)) * s], 0.002 * s, n=6)
    util.cylinder(bm, 0.003 * s, 0.012 * s, 0.09 * s, loc=pom + V((0, 0.012, -0.11)) * s, segs=10)
    o = util.mesh_object("SwordTassel", bm, mats["tassel"])
    util.box_uv(o, 20)
    parts.append(o)
    return parts


def build_ribbon(mats, s):
    """Pibo: a long sheer ribbon draped behind the back and over both arms."""
    path = [V((0.43, -0.04, 0.50)), V((0.42, -0.02, 0.74)), V((0.39, 0.0, 0.98)),
            V((0.33, 0.07, 1.20)), V((0.22, 0.14, 1.33)), V((0.08, 0.175, 1.36)),
            V((-0.08, 0.175, 1.36)), V((-0.22, 0.14, 1.33)), V((-0.33, 0.07, 1.20)),
            V((-0.39, 0.0, 0.98)), V((-0.42, -0.02, 0.74)), V((-0.44, -0.05, 0.46))]
    path = [p * s for p in path]

    def outward(p):
        o = V((p.x, p.y, 0))
        if p.z > 1.25 * s and abs(p.x) < 0.25 * s:
            o = V((p.x * 0.6, 1.0, 0.25))
        return o.normalized()
    o = flat_ribbon("Ribbon", path, lambda t: (0.13 - 0.03 * abs(t - 0.5)) * s, mats["ribbon"], outward,
                    samples=8, u_scale=1.2)
    return o


# --------------------------------------------------------------------------
# materials per character
# --------------------------------------------------------------------------
def make_materials(cfg):
    c = cfg["colors"]
    fem = cfg["female"]
    p = cfg["name"] + "_"
    m = {}
    face = dict(brow=c["brow"], lip=c["lip"], liner=c["liner"], blush=c["blush"], female=fem,
                beard=cfg.get("stubble", 0.0 if fem else 0.35), age=cfg.get("age", 0.0),
                mark=cfg.get("forehead_mark", fem), hairline=hairline_table(fem), hair=c["hair"])
    m["face"] = util.material(p + "face", tex.skin(c["skin"], cfg.get("face_tex", 2048), 11, face),
                              normal_strength=0.6, normal_bump=1.2, detail_div=cfg.get("face_tex", 2048) // 1024)
    m["skin"] = util.material(p + "skin", tex.skin(c["skin"], 512, 12), normal_strength=0.5)
    m["nail"] = util.material(p + "nail", tex.nail(c["skin"]), normal_strength=0.2)
    eye = tex.eye(c["iris"], glow=cfg.get("eye_glow"))
    m["eye"] = util.material(p + "eye", eye, normal_strength=0.0, emission_map=eye.get("emission"),
                             emission_strength=3.0)
    m["lid"] = util.material(p + "eyelid", tex.eyelid(c["skin"], c["liner"]), normal_strength=0.0)
    m["hair"] = util.material(p + "hair", tex.hair(c["hair"], c["hair_hl"], 512), normal_strength=0.6,
                              double_sided=True)
    m["robe"] = util.material(p + "robe", tex.robe(c["robe_top"], c["robe_hem"], c["robe_motif"],
                                                   c["robe_accent"], cfg["robe_style"], 1024),
                              normal_strength=0.5, double_sided=True)
    m["under"] = util.material(p + "undercollar", tex.silk("#f7f5f0", "#ebe6dc", 256, 3), normal_strength=0.4)
    m["trim"] = util.material(p + "trim", tex.embroidery_trim(c["trim"], c["thread"], 512), normal_strength=0.6)
    m["belt"] = util.material(p + "belt", tex.silk(c["belt"], c["thread"], 512, 5, 9, 0.05, 0.3),
                              normal_strength=0.5, double_sided=True)
    m["metal"] = util.material(p + "metal", tex.metal(c["metal"], rough=0.25))
    m["jade"] = util.material(p + "jade", tex.jade(c["jade"]))
    m["tassel"] = util.material(p + "tassel", tex.silk("#b3213a" if not fem else "#e0567e", "#d24a5e", 128, 9))
    m["boots"] = util.material(p + "boots", tex.leather(c["boots"]))
    m["sole"] = util.material(p + "sole", tex.leather(c["sole"], seed=8))
    m["lacquer"] = util.material(p + "scabbard", tex.lacquer("#1e1a22", wear=0.1))
    m["accent"] = util.material(p + "blossom", color=c["robe_accent"], rough=0.5)
    m["band"] = util.material(p + "band", tex.silk(c.get("band", c["trim"]), c["thread"], 128, 6), normal_strength=0.4)
    m["scarf"] = util.material(p + "scarf", tex.silk(c.get("scarf", c["trim"]), c["thread"], 256, 7, 5, 0.08),
                               normal_strength=0.5, double_sided=True)
    m["straw"] = util.material(p + "straw", tex.wood("#b8995e", 256, 63, rings=40), normal_strength=0.8,
                               double_sided=True)
    m["beard"] = util.material(p + "beard", tex.hair(c["hair"], c["hair_hl"], 256, 23), normal_strength=0.4,
                               double_sided=True)
    m["horn"] = util.material(p + "horn", tex.lacquer(c.get("horn", "#2a2224"), 256, 52, wear=0.4), normal_strength=0.6)
    if "ribbon" in c:
        m["ribbon"] = util.material(p + "ribbon", tex.sheer(c["ribbon"]), alpha=0.82, double_sided=True,
                                    normal_strength=0.2)
    return m


# --------------------------------------------------------------------------
# animation
# --------------------------------------------------------------------------
class Poser:
    """Keys bone poses given as rotations in *world* axes.

    Each bone gets a delta rotation D (world axes, about its head) relative to
    its parent's posed frame; world deltas compose down the chain like FK.
    """

    def __init__(self, arm, bones):
        self.arm = arm
        self.bones = bones
        self.rest = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
        self.parent = {n: p for n, (_, _, p) in bones.items()}
        self.order = list(bones.keys())

    def key(self, frame, deltas, hips_offset=V(), absolute=None):
        absolute = dict(absolute or {})
        world = {}
        for n in self.order:
            p = self.parent[n]
            pq = world.get(p, Quaternion()) if p else Quaternion()
            if n in absolute:
                world[n] = absolute[n]
            else:
                world[n] = pq @ deltas.get(n, Quaternion())
        for n in self.order:
            pb = self.arm.pose.bones[n]
            p = self.parent[n]
            pq = world.get(p, Quaternion()) if p else Quaternion()
            r = self.rest[n]
            local = r.inverted() @ (pq.inverted() @ world[n]) @ r
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = local
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=n)
            if n == "hips":
                pb.location = r.inverted() @ hips_offset
                pb.keyframe_insert("location", frame=frame, group=n)
            else:
                pb.location = V()
        return world

    def fk_pos(self, deltas, hips_offset=V()):
        """Posed world head/tail positions (used for simple arm IK)."""
        world, pos = {}, {}
        for n in self.order:
            h, t, p = self.bones[n]
            if p is None:
                q = deltas.get(n, Quaternion())
                head = h + hips_offset
            else:
                ph, pt, _ = self.bones[p]
                q = world[p] @ deltas.get(n, Quaternion())
                head = pos[p][0] + world[p] @ (h - ph)
            world[n] = q
            pos[n] = (head, head + q @ (t - h))
        return world, pos


def qa(axis, deg):
    return Quaternion(V(axis).normalized(), R(deg))


def aim(rest_dir, new_dir):
    return rest_dir.normalized().rotation_difference(new_dir.normalized())


def two_bone(root, target, l1, l2, pole):
    """Analytic two-bone IK: returns elbow position."""
    d = target - root
    dist = min(d.length, (l1 + l2) * 0.999)
    d = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    pole_dir = (pole - root)
    pole_dir = (pole_dir - d * pole_dir.dot(d)).normalized()
    return root + d * a + pole_dir * h


def build_actions(arm, bones, cfg, s):
    poser = Poser(arm, bones)
    fem = cfg["female"]
    X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
    arm.animation_data_create()

    def arm_down(side, deg):
        return qa(Y, deg if side == "L" else -deg)

    def swing(deg):  # + = forward for limbs hanging down
        return qa(X, -deg)

    def elbow(side, deg):
        """Bend the forearm forward/inward around the elbow hinge."""
        h, t, _ = bones[f"upper_arm.{side}"]
        d = (t - h).normalized()
        axis = d.cross(V((0, -1, 0))).normalized()
        return Quaternion(axis, R(deg))

    def arms_hang(dl, extra=None):
        extra = extra or {}
        for side in ("L", "R"):
            sgn = 1 if side == "L" else -1
            dl[f"upper_arm.{side}"] = extra.get(f"swing.{side}", Quaternion()) @ arm_down(side, 24) @ \
                qa(Z, -8 * sgn)
            dl[f"forearm.{side}"] = elbow(side, extra.get(f"elbow.{side}", 12))
            dl[f"hand.{side}"] = qa(X, extra.get(f"wrist.{side}", -5))
        return dl

    # finger flexion axes (rest pose, world space): bending a phalanx toward the palm
    flex = {}
    for side in ("L", "R"):
        wr, ht, _ = bones[f"hand.{side}"]
        hx, hy, hz = anatomy.hand_frame(wr, ht, side)
        for fname in anatomy.FINGERS + ("thumb",):
            for i in (1, 2, 3):
                bn = f"{fname}.{i}.{side}"
                h, t, _ = bones[bn]
                d = (t - h).normalized()
                toward = -hz if fname != "thumb" else (-hz * 0.7 - hx * 0.7).normalized()
                flex[bn] = d.cross(toward).normalized()
    # per-finger (knuckle, middle, tip) flexion in degrees on top of the rest curl
    HAND_POSES = {
        "relaxed": {f: (6, 10, 6) for f in anatomy.FINGERS} | {"thumb": (0, 6, 6)},
        "open": {f: (-8, -10, -6) for f in anatomy.FINGERS} | {"thumb": (-6, -8, -6)},
        "fist": {f: (78, 95, 55) for f in anatomy.FINGERS} | {"thumb": (20, 35, 30)},
        "seal": {"index": (-6, -8, -4), "middle": (-6, -8, -4), "ring": (78, 95, 55),
                 "pinky": (78, 95, 55), "thumb": (30, 40, 30)},
        "cup": {f: (30, 25, 12) for f in anatomy.FINGERS} | {"thumb": (8, 10, 8)},
        "mudra": {"index": (40, 50, 30), "middle": (12, 12, 6), "ring": (14, 14, 8),
                  "pinky": (16, 16, 10), "thumb": (18, 22, 18)},
        "claw": {f: (30, 60, 50) for f in anatomy.FINGERS} | {"thumb": (10, 30, 30)},
    }

    def pose_hand(dl, side, preset, k=1.0, blend_to=None, t=0.0):
        a = HAND_POSES[preset]
        b = HAND_POSES[blend_to] if blend_to else a
        for fname in anatomy.FINGERS + ("thumb",):
            for i in (1, 2, 3):
                deg = (a[fname][i - 1] * (1 - t) + b[fname][i - 1] * t) * k
                dl[f"{fname}.{i}.{side}"] = Quaternion(flex[f"{fname}.{i}.{side}"], R(deg))
        return dl

    def start(name):
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        return act

    actions = []
    # ---------------------------------------------------------------- idle
    act = start("idle")
    T = 120
    for f in range(0, T + 1, 2):
        ph = 2 * math.pi * f / T
        br = math.sin(ph)
        dl = {}
        dl["hips"] = qa(Z, 2.0 * math.sin(ph * 0.5 + 0.3)) @ qa(Y, 1.0 * math.sin(ph * 0.5))
        dl["spine"] = qa(X, 1.2 * br) @ qa(Y, -0.6 * math.sin(ph * 0.5))
        dl["chest"] = qa(X, -1.6 * br)
        dl["neck"] = qa(X, 1.0 * br)
        dl["head"] = qa(Z, 4.0 * math.sin(ph * 0.5 + 1.0)) @ qa(X, -1.5 + 1.0 * math.sin(ph + 0.5))
        for side, sg in (("L", 1), ("R", -1)):
            dl[f"shoulder.{side}"] = qa(Y, sg * 1.0 * br)
            dl[f"thigh.{side}"] = qa(Y, sg * 2.0)
            dl[f"foot.{side}"] = qa(Y, -sg * 2.0)
        arms_hang(dl, {"elbow.L": 14 + 2 * br, "elbow.R": 14 + 2 * br,
                       "swing.L": swing(3 + br), "swing.R": swing(3 + br)})
        pose_hand(dl, "L", "relaxed", 1.0 + 0.3 * br)
        pose_hand(dl, "R", "relaxed", 1.0 + 0.3 * math.sin(ph + 0.7))
        dl["hair.1"] = qa(X, 1.5 * math.sin(ph + 1.2))
        dl["hair.2"] = qa(X, 2.0 * math.sin(ph + 0.4))
        dl["hair.3"] = qa(X, 2.5 * math.sin(ph - 0.4))
        poser.key(f + 1, dl, V((0.006 * s * math.sin(ph * 0.5), 0, -0.004 * s * (1 - br) * 0.5)))
    actions.append(act)

    # ---------------------------------------------------------------- walk / run
    def locomotion(name, T, stride, knee, lean, arm_sw, bob, elbow_base, twist):
        act = start(name)
        for f in range(0, T + 1):
            ph = 2 * math.pi * f / T
            dl = {}
            dl["hips"] = qa(X, -lean * 0.4) @ qa(Z, twist * math.sin(ph)) @ qa(Y, 2.5 * math.cos(ph))
            dl["spine"] = qa(X, -lean * 0.4) @ qa(Z, -twist * 0.6 * math.sin(ph))
            dl["chest"] = qa(X, -lean * 0.2) @ qa(Z, -twist * 0.8 * math.sin(ph))
            dl["neck"] = qa(X, lean * 0.3)
            dl["head"] = qa(X, lean * 0.4) @ qa(Z, twist * 0.5 * math.sin(ph))
            for side, off in (("L", 0.0), ("R", math.pi)):
                p = ph + off
                th = stride * math.sin(p)
                # knee: flexes most mid-swing (leg travelling forward) + contact flex
                swing_phase = max(0.0, math.cos(p))
                bend = 6 + knee * swing_phase ** 1.4 + 10 * max(0.0, math.sin(p - 0.6)) ** 4
                dl[f"thigh.{side}"] = swing(th)
                dl[f"shin.{side}"] = qa(X, bend)
                # keep the sole roughly level, toe-off at the back of the stride
                foot = -(th - bend) * 0.8 - 18 * max(0.0, -math.sin(p)) ** 3 * (1 if name == "walk" else 1.6)
                dl[f"foot.{side}"] = qa(X, -foot)
                dl[f"toe.{side}"] = qa(X, 20 * max(0.0, -math.sin(p)) ** 4)
                sgn = 1 if side == "L" else -1
                dl[f"shoulder.{side}"] = qa(Y, sgn * 2 * math.sin(p))
            for side, off in (("L", math.pi), ("R", 0.0)):
                p = ph + off
                a = arm_sw * math.sin(p)
                dl.setdefault("_x", {})
                dl["_x"][f"swing.{side}"] = swing(a)
                dl["_x"][f"elbow.{side}"] = elbow_base + max(0.0, a) * 0.6
            ex = dl.pop("_x")
            arms_hang(dl, ex)
            for side in ("L", "R"):
                pose_hand(dl, side, "relaxed", 1.5, "fist", 0.0 if name == "walk" else 0.55)
            dl["hair.1"] = qa(X, 5 + 3 * math.sin(2 * ph - 0.8) + lean * 0.8)
            dl["hair.2"] = qa(X, 4 + 4 * math.sin(2 * ph - 1.6) + lean * 0.5)
            dl["hair.3"] = qa(X, 3 + 5 * math.sin(2 * ph - 2.4))
            z = -bob * s * (0.5 + 0.5 * math.cos(2 * ph)) + 0.0
            poser.key(f + 1, dl, V((0.012 * s * math.sin(ph), 0, z)))
        return act

    actions.append(locomotion("walk", 32, 26, 55, 3.0, 16, 0.028, 14, 5))
    actions.append(locomotion("run", 20, 44, 100, 13.0, 38, 0.05, 70, 8))

    # ---------------------------------------------------------------- IK based gestures
    lens = {side: ((bones[f"upper_arm.{side}"][1] - bones[f"upper_arm.{side}"][0]).length,
                   (bones[f"forearm.{side}"][1] - bones[f"forearm.{side}"][0]).length)
            for side in ("L", "R")}

    def arm_ik(dl, side, hand_target, pole, hand_dir=None, hips_offset=V()):
        world, pos = poser.fk_pos(dl, hips_offset)
        sh_head = pos[f"upper_arm.{side}"][0]
        l1, l2 = lens[side]
        el = two_bone(sh_head, hand_target, l1, l2, pole)
        rh, rt, _ = bones[f"upper_arm.{side}"]
        fh, ft, _ = bones[f"forearm.{side}"]
        hh, ht, _ = bones[f"hand.{side}"]
        absq = {
            f"upper_arm.{side}": aim(rt - rh, el - sh_head),
            f"forearm.{side}": aim(ft - fh, hand_target - el),
        }
        if hand_dir is not None:
            absq[f"hand.{side}"] = aim(ht - hh, hand_dir)
        return absq

    # salute (zuoyi): cupped hands raised before the chest, a respectful bow
    act = start("salute")
    T = 60
    for f in range(0, T + 1, 2):
        t = f / T
        up = util_smooth(t / 0.25) * (1 - util_smooth((t - 0.8) / 0.2))
        bow = util_smooth((t - 0.3) / 0.2) * (1 - util_smooth((t - 0.65) / 0.2))
        dl = {"hips": qa(X, 0), "spine": qa(X, -10 * bow), "chest": qa(X, -12 * bow),
              "neck": qa(X, -6 * bow), "head": qa(X, -8 * bow)}
        arms_hang(dl)
        pose_hand(dl, "L", "relaxed", 1.0, "fist", up)
        pose_hand(dl, "R", "relaxed", 1.0, "cup", up)
        absq = {}
        world, pos = poser.fk_pos(dl)
        chest_h, chest_t = pos["chest"]
        fwd = world["chest"] @ V((0, -1, 0))
        upv = world["chest"] @ V((0, 0, 1))
        centre = chest_t - upv * 0.10 * s + fwd * 0.30 * s
        for side, sg in (("L", 1), ("R", -1)):
            rest_hand = pos[f"hand.{side}"][0]
            tgt = centre + world["chest"] @ V((sg * 0.03 * s, 0, 0))
            tgt = rest_hand.lerp(tgt, up)
            pole = pos[f"upper_arm.{side}"][0] + world["chest"] @ V((sg * 0.5, 0.2, -0.6))
            hand_dir = (world["chest"] @ V((-sg * 0.9, -0.3, 0.3))).lerp(
                pos[f"hand.{side}"][1] - pos[f"hand.{side}"][0], 1 - up)
            if up > 0.01:
                absq.update(arm_ik(dl, side, tgt, pole, hand_dir))
        poser.key(f + 1, dl, V(), absolute=absq)
    actions.append(act)

    # cast: sword-seal gesture then a thrust of spiritual energy
    act = start("cast")
    T = 50
    for f in range(0, T + 1, 2):
        t = f / T
        raise_ = util_smooth(t / 0.3) * (1 - util_smooth((t - 0.85) / 0.15))
        thrust = util_smooth((t - 0.45) / 0.12) * (1 - util_smooth((t - 0.8) / 0.15))
        dl = {"hips": qa(Z, -15 * raise_), "spine": qa(Z, -5 * raise_) @ qa(X, -4 * thrust),
              "chest": qa(Z, 8 * raise_), "head": qa(Z, 10 * raise_)}
        for side, sg in (("L", 1), ("R", -1)):
            dl[f"thigh.{side}"] = qa(Y, sg * 6 * raise_) @ swing(10 * raise_ * sg)
            dl[f"shin.{side}"] = qa(X, 10 * raise_)
        arms_hang(dl)
        pose_hand(dl, "R", "relaxed", 1.0, "seal", raise_)
        pose_hand(dl, "L", "relaxed", 1.0, "open", raise_)
        world, pos = poser.fk_pos(dl, V((0, 0, -0.04 * s * raise_)))
        chest_h, chest_t = pos["chest"]
        fwd = world["chest"] @ V((0, -1, 0))
        upv = world["chest"] @ V((0, 0, 1))
        absq = {}
        # right hand: seal before the face, then thrust forward
        seal = chest_t + upv * 0.12 * s + fwd * 0.22 * s + world["chest"] @ V((-0.02 * s, 0, 0))
        push = chest_t + upv * 0.05 * s + fwd * 0.55 * s + world["chest"] @ V((-0.08 * s, 0, 0))
        tgt_r = pos["hand.R"][0].lerp(seal.lerp(push, thrust), raise_)
        pole_r = pos["upper_arm.R"][0] + world["chest"] @ V((-0.6, 0.3, -0.5))
        if raise_ > 0.01:
            absq.update(arm_ik(dl, "R", tgt_r, pole_r, world["chest"] @ V((0.1, -0.2, 1.0)).lerp(fwd, thrust),
                               V((0, 0, -0.04 * s * raise_))))
            # left hand: flat seal at the chest
            tgt_l = pos["hand.L"][0].lerp(chest_h + upv * 0.08 * s + fwd * 0.25 * s +
                                          world["chest"] @ V((0.04 * s, 0, 0)), raise_)
            pole_l = pos["upper_arm.L"][0] + world["chest"] @ V((0.6, 0.3, -0.5))
            absq.update(arm_ik(dl, "L", tgt_l, pole_l, world["chest"] @ V((-1.0, -0.2, 0.1)),
                               V((0, 0, -0.04 * s * raise_))))
        dl["hair.1"] = qa(X, 8 * thrust)
        dl["hair.2"] = qa(X, 10 * thrust)
        dl["hair.3"] = qa(X, 12 * thrust)
        poser.key(f + 1, dl, V((0, 0, -0.04 * s * raise_)), absolute=absq)
    actions.append(act)

    # attack: a stepping palm strike (wind up, strike, recover)
    act = start("attack")
    T = 28
    for f in range(0, T + 1, 2):
        t = f / T
        wind = util_smooth(t / 0.3) * (1 - util_smooth((t - 0.3) / 0.12))
        hit = util_smooth((t - 0.3) / 0.14) * (1 - util_smooth((t - 0.62) / 0.38))
        lunge = hit * 0.09 * s
        hips_off = V((0, -lunge, -0.03 * s * (wind + hit)))
        dl = {"hips": qa(Z, 18 * wind - 22 * hit),
              "spine": qa(Z, 6 * wind - 8 * hit) @ qa(X, -6 * hit),
              "chest": qa(Z, 8 * wind - 10 * hit), "neck": qa(Z, -8 * wind + 12 * hit),
              "head": qa(Z, -10 * wind + 14 * hit)}
        for side, sg in (("L", 1), ("R", -1)):
            fwd = hit if side == "R" else wind
            dl[f"thigh.{side}"] = swing(-14 * hit * sg) @ qa(Y, sg * 4)
            dl[f"shin.{side}"] = qa(X, 12 * (wind + hit))
        arms_hang(dl)
        world, pos = poser.fk_pos(dl, hips_off)
        ch_h, ch_t = pos["chest"]
        fwdv = world["chest"] @ V((0, -1, 0))
        upv = world["chest"] @ V((0, 0, 1))
        absq = {}
        back = ch_h + upv * 0.02 * s + fwdv * 0.05 * s + world["chest"] @ V((-0.2 * s, 0, 0))
        strike = ch_t - upv * 0.05 * s + fwdv * 0.58 * s + world["chest"] @ V((-0.04 * s, 0, 0))
        tgt_r = back.lerp(strike, util_smooth(hit * 1.4))
        tgt_r = pos["hand.R"][0].lerp(tgt_r, min(1.0, wind + hit))
        pole_r = pos["upper_arm.R"][0] + world["chest"] @ V((-0.6, 0.4, -0.5))
        absq.update(arm_ik(dl, "R", tgt_r, pole_r, (fwdv + upv * 0.8).normalized(), hips_off))
        guard = ch_t - upv * 0.02 * s + fwdv * 0.28 * s + world["chest"] @ V((0.05 * s, 0, 0))
        tgt_l = pos["hand.L"][0].lerp(guard, util_smooth((wind + hit) * 1.5))
        pole_l = pos["upper_arm.L"][0] + world["chest"] @ V((0.6, 0.3, -0.5))
        absq.update(arm_ik(dl, "L", tgt_l, pole_l, world["chest"] @ V((-0.5, -0.3, 0.8)), hips_off))
        pose_hand(dl, "R", "relaxed", 1.0, "open", hit)
        pose_hand(dl, "L", "relaxed", 1.0, "fist", min(1.0, wind + hit))
        dl["hair.1"] = qa(X, 6 * hit) @ qa(Z, -8 * hit)
        dl["hair.2"] = qa(X, 8 * hit) @ qa(Z, -10 * hit)
        dl["hair.3"] = qa(X, 10 * hit)
        poser.key(f + 1, dl, hips_off, absolute=absq)
    actions.append(act)

    # hit: a flinch backward
    act = start("hit")
    T = 16
    for f in range(0, T + 1, 2):
        t = f / T
        k = util_smooth(t / 0.25) * (1 - util_smooth((t - 0.3) / 0.7))
        dl = {"hips": qa(X, 4 * k), "spine": qa(X, 10 * k) @ qa(Z, 5 * k), "chest": qa(X, 8 * k),
              "neck": qa(X, 8 * k), "head": qa(X, 12 * k) @ qa(Z, -8 * k)}
        for side in ("L", "R"):
            dl[f"shin.{side}"] = qa(X, 14 * k)
            dl[f"thigh.{side}"] = swing(6 * k)
        arms_hang(dl, {"swing.L": swing(25 * k), "swing.R": swing(30 * k), "elbow.L": 12 + 45 * k,
                       "elbow.R": 12 + 50 * k})
        pose_hand(dl, "L", "relaxed", 1.0, "claw", k)
        pose_hand(dl, "R", "relaxed", 1.0, "claw", k)
        dl["hair.1"] = qa(X, -8 * k)
        dl["hair.2"] = qa(X, -10 * k)
        dl["hair.3"] = qa(X, -12 * k)
        poser.key(f + 1, dl, V((0, 0.04 * s * k, -0.03 * s * k)))
    actions.append(act)

    # death: recoil, knees buckle, fall onto the back, settle
    act = start("death")
    T = 60
    for f in range(0, T + 1, 2):
        t = f / T
        rec = util_smooth(t / 0.15) * (1 - util_smooth((t - 0.15) / 0.2))
        fall = util_smooth((t - 0.18) / 0.5)
        bounce = math.sin(math.pi * util_smooth((t - 0.66) / 0.14)) * (1 - util_smooth((t - 0.8) / 0.1))
        kb = math.sin(math.pi * min(1.0, fall * 1.2))
        dl = {"hips": qa(X, -86 * fall + 3 * bounce),
              "spine": qa(X, 10 * rec + 6 * kb - 4 * fall), "chest": qa(X, 8 * rec - 2 * fall),
              "neck": qa(X, 10 * rec - 12 * kb), "head": qa(X, 12 * rec - 10 * kb + 8 * fall) @ qa(Z, 22 * fall)}
        for side, sg in (("L", 1), ("R", -1)):
            dl[f"thigh.{side}"] = swing(40 * kb) @ qa(Y, sg * 8 * fall)
            dl[f"shin.{side}"] = qa(X, 70 * kb + 8 * fall)
            dl[f"foot.{side}"] = qa(X, -20 * fall)
        arms_hang(dl, {"swing.L": qa(Y, 50 * fall) @ swing(30 * rec + 40 * kb),
                       "swing.R": qa(Y, -45 * fall) @ swing(30 * rec + 30 * kb),
                       "elbow.L": 12 + 40 * kb + 15 * fall, "elbow.R": 12 + 35 * kb + 25 * fall})
        pose_hand(dl, "L", "relaxed", 1.0, "claw", 0.5 * kb + 0.4 * fall)
        pose_hand(dl, "R", "relaxed", 1.0, "claw", 0.4 * kb + 0.5 * fall)
        dl["hair.1"] = qa(X, -20 * kb + 30 * fall)
        dl["hair.2"] = qa(X, -25 * kb + 20 * fall)
        dl["hair.3"] = qa(X, -20 * kb + 10 * fall)
        z = -0.83 * s * util_smooth((t - 0.18) / 0.48) + 0.03 * s * bounce
        poser.key(f + 1, dl, V((0, 0.34 * s * fall + 0.03 * s * rec, z)))
    actions.append(act)

    # meditate: seated cross-legged, hands resting on the knees in a mudra, slow breath (loop)
    act = start("meditate")
    T = 120
    th_len = (bones["thigh.L"][1] - bones["thigh.L"][0]).length
    sh_len = (bones["shin.L"][1] - bones["shin.L"][0]).length
    for f in range(0, T + 1, 4):
        ph = 2 * math.pi * f / T
        br = math.sin(ph)
        hips_off = V((0, 0.02 * s, -0.78 * s - 0.004 * s * br))
        dl = {"hips": qa(X, -4), "spine": qa(X, 4 + 1.5 * br), "chest": qa(X, -1.5 * br),
              "neck": qa(X, 2), "head": qa(X, -3 + br)}
        absq = {}
        knees = {}
        for side, sg in (("L", 1), ("R", -1)):
            hh, ht, _ = bones[f"thigh.{side}"]
            hip = hh + hips_off
            tdir = V((sg * 0.72, -0.66, -0.12)).normalized()
            knee = hip + tdir * th_len
            knees[side] = knee
            sdir = V((-sg * 0.86, 0.3 if side == "L" else 0.18, -0.08 if side == "L" else 0.05)).normalized()
            absq[f"thigh.{side}"] = aim(ht - hh, tdir)
            sh, st, _ = bones[f"shin.{side}"]
            absq[f"shin.{side}"] = aim(st - sh, sdir)
            fh, ft, _ = bones[f"foot.{side}"]
            absq[f"foot.{side}"] = aim(ft - fh, V((-sg * 0.35, -0.5, 0.3)))
        arms_hang(dl)
        world, pos = poser.fk_pos(dl, hips_off)
        for side, sg in (("L", 1), ("R", -1)):
            tgt = knees[side] + V((-sg * 0.06 * s, 0.03 * s, 0.07 * s))
            pole = pos[f"upper_arm.{side}"][0] + V((sg * 0.5, 0.3, -0.3))
            absq.update(arm_ik(dl, side, tgt, pole, V((sg * 0.25, -0.9, -0.2)), hips_off))
            pose_hand(dl, side, "mudra")
        dl["hair.1"] = qa(X, 1.0 * br)
        dl["hair.2"] = qa(X, 1.5 * br)
        poser.key(f + 1, dl, hips_off, absolute=absq)
    actions.append(act)

    # talk: conversational idle with an explaining right hand and nods (loop)
    act = start("talk")
    T = 120
    for f in range(0, T + 1, 2):
        ph = 2 * math.pi * f / T
        br = math.sin(ph)
        g = 0.5 + 0.5 * math.sin(2 * ph - 0.5)
        dl = {"hips": qa(Z, 3 * math.sin(ph)), "spine": qa(X, 1.0 * br) @ qa(Z, -2 * math.sin(ph)),
              "chest": qa(X, -1.2 * br) @ qa(Z, 2 * math.sin(2 * ph)),
              "neck": qa(X, 2 * math.sin(3 * ph)), "head": qa(X, -2 + 3 * math.sin(3 * ph + 0.4)) @ qa(Z, 5 * math.sin(ph))}
        for side, sg in (("L", 1), ("R", -1)):
            dl[f"thigh.{side}"] = qa(Y, sg * 2.0)
        arms_hang(dl, {"swing.R": swing(12 + 20 * g) @ qa(Y, -8 * g), "elbow.R": 35 + 45 * g,
                       "wrist.R": -5 - 20 * g, "swing.L": swing(4), "elbow.L": 16 + 6 * g})
        pose_hand(dl, "R", "relaxed", 1.0, "open", g)
        pose_hand(dl, "L", "relaxed", 1.2)
        dl["hair.1"] = qa(X, 1.5 * math.sin(ph + 1.2))
        dl["hair.2"] = qa(X, 2.0 * math.sin(ph + 0.4))
        poser.key(f + 1, dl, V((0.006 * s * math.sin(ph), 0, 0)))
    actions.append(act)

    # rest pose for the file: idle first frame
    arm.animation_data.action = actions[0]
    return actions


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------
def build_character(cfg):
    util.reset_scene()
    s = cfg["scale"]
    J = {n: (h * s, t * s, p) for n, (h, t, p) in joints(cfg).items()}
    mats = make_materials(cfg)
    arm = build_armature(cfg, J)

    head_parts, centre, radii = build_head(cfg, J, mats, s)
    hair_parts = build_hair(cfg, mats, centre, radii, s)
    outfit, bvh, ring_at = build_outfit(cfg, J, mats, s)

    body, hair, clothes, acc = [], [], [], []
    for o in head_parts:
        assign(o, lambda p, b, s_: {"head": 1.0}, J, s)
        body.append(o)
    for kind, o in hair_parts:
        fn = {"head": lambda p, b, s_: {"head": 1.0}, "hair": w_hair, "side": w_sidelock}[kind]
        assign(o, fn, J, s)
        hair.append(o)
    for item in outfit:
        kind, o = item[0], item[1]
        side = item[2] if len(item) > 2 else None
        if kind == "torso":
            assign(o, w_torso, J, s)
            clothes.append(o)
        elif kind == "arm":
            assign(o, w_arm, J, s, side)
            clothes.append(o)
        elif kind == "hand":
            assign(o, w_hand, J, s, side)
            body.append(o)
        elif kind == "leg":
            assign(o, w_leg, J, s, side)
            clothes.append(o)
        elif kind == "neck":
            assign(o, w_neck, J, s)
            body.append(o)
    accessory = cfg.get("accessory", "ribbon" if cfg["female"] else "sword")
    if accessory == "sword":
        for o in build_sword(mats, s, J):
            assign(o, lambda p, b, s_: {"hips": 1.0}, J, s)
            acc.append(o)
    elif accessory == "ribbon":
        o = build_ribbon(mats, s)
        assign(o, w_ribbon, J, s)
        acc.append(o)

    meshes = []
    for name, group in (("Body", body), ("Hair", hair), ("Outfit", clothes), ("Accessories", acc)):
        if not group:
            continue
        o = util.join(group, name)
        o.parent = arm
        mod = o.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        meshes.append(o)
    arm.name = "Armature"
    actions = build_actions(arm, J, cfg, s)
    if cfg["name"].startswith("cultivator_"):
        from . import moves
        actions += moves.build_player_actions(arm, J, cfg, s)
    return arm, meshes, actions

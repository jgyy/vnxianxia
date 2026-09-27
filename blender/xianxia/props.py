"""Small set-dressing props for the sect courtyard."""
import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import arch, nature, tex, util

V = Vector
R = math.radians


def _m():
    m = arch.kit()
    m["bronze"] = util.material("bronze", tex.metal("#7a6238", rough=0.35, patina="#41695c", patina_amt=0.22),
                                normal_strength=0.6)
    m["glow"] = util.material("lamp_glow", color="#ffd9a0", rough=0.6, emission="#ffc46b",
                              emission_strength=6.0)
    m["lantern"] = util.material("red_lantern", tex.paper_lantern("#c7261c"), emission="#ff4a1c",
                                 emission_strength=1.5, normal_strength=0.3)
    m["cloth"] = util.material("tassel_red", tex.silk("#b3213a", "#d24a5e", 128, 9))
    return m


def stone_lantern():
    m = _m()
    bm_s, bm_g = bmesh.new(), bmesh.new()
    util.cylinder(bm_s, 0.55, 0.6, 0.25, loc=(0, 0, 0.125), segs=6)
    util.lathe(bm_s, [(0.4, 0.25), (0.3, 0.35), (0.16, 0.45), (0.14, 1.1), (0.2, 1.2), (0.001, 1.2)],
               segs=12, cap_bottom=False)
    util.cylinder(bm_s, 0.45, 0.4, 0.14, loc=(0, 0, 1.27), segs=6)
    for k in range(6):
        a = R(60 * k + 30)
        util.box(bm_s, (0.08, 0.08, 0.42), loc=(math.cos(a) * 0.3, math.sin(a) * 0.3, 1.55),
                 rot=Matrix.Rotation(a, 4, "Z"))
    util.cylinder(bm_g, 0.24, 0.24, 0.38, loc=(0, 0, 1.55), segs=6)
    o_s = util.mesh_object("LanternStone", bm_s, m["stone"], smooth=False)
    util.box_uv(o_s, 1.2)
    o_g = util.mesh_object("LanternLight", bm_g, m["glow"], smooth=False)
    objs = [o_s, o_g]
    roof_m = {"tiles": m["stone"], "wood": m["stone"], "ridge": m["stone"], "gold": m["stone"]}
    objs += arch.poly_roof("LanternCap", 0, 0, 0.62, 6, 0.45, roof_m, base_z=1.76, rot=R(30), lift=0.12,
                           lift_len=0.2, curve=1.5, per_edge=6, rows=6, thick=0.08, ridges=True,
                           detail=0.3)
    for o in objs[2:]:
        util.box_uv(o, 1.2)
    objs.append(util.collider("LanternCol", (1.0, 1.0, 2.2), (0, 0, 1.1)))
    return objs


def red_lantern():
    """Hanging paper lantern (origin at the hook)."""
    m = _m()
    bm = bmesh.new()
    prof = [(0.12, -0.1)]
    for k in range(11):
        t = k / 10
        prof.append((0.14 + 0.2 * math.sin(math.pi * t), -0.12 - 0.5 * t))
    util.lathe(bm, prof, segs=24, uv_v=1.6)
    o = util.mesh_object("LanternPaper", bm, m["lantern"])
    bm = bmesh.new()
    util.cylinder(bm, 0.15, 0.15, 0.06, loc=(0, 0, -0.1), segs=16)
    util.cylinder(bm, 0.15, 0.15, 0.06, loc=(0, 0, -0.63), segs=16)
    util.cylinder(bm, 0.008, 0.008, 0.12, loc=(0, 0, -0.03), segs=6)
    caps = util.mesh_object("LanternCaps", bm, m["gold"])
    util.box_uv(caps, 3)
    bm = bmesh.new()
    util.cylinder(bm, 0.02, 0.06, 0.35, loc=(0, 0, -0.85), segs=10)
    tas = util.mesh_object("LanternTassel", bm, m["cloth"])
    util.box_uv(tas, 3)
    return [o, caps, tas]


def incense_burner():
    """Bronze ding cauldron on a stone plinth with smouldering incense."""
    m = _m()
    bm = bmesh.new()
    util.cylinder(bm, 1.0, 1.1, 0.4, loc=(0, 0, 0.2), segs=8)
    pl = util.mesh_object("BurnerPlinth", bm, m["stone"], smooth=False)
    util.box_uv(pl, 1.0)
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.75), (0.45, 0.78), (0.62, 0.95), (0.66, 1.25), (0.62, 1.45), (0.7, 1.52),
                    (0.66, 1.56), (0.55, 1.5)], segs=32, cap_bottom=True)
    for k in range(3):
        a = R(120 * k + 90)
        top = V((math.cos(a) * 0.4, math.sin(a) * 0.4, 0.9))
        foot = V((math.cos(a) * 0.55, math.sin(a) * 0.55, 0.4))
        util.tube(bm, util.catmull([top, top.lerp(foot, 0.5) + V((0, 0, 0.05)), foot], 3),
                  lambda t: 0.09 * (1 - 0.3 * t), n=10)
        util.sphere(bm, 0.11, loc=foot + V((0, 0, 0.02)), segs=10, rings=6, scale=(1, 1, 0.6))
    for sx in (-1, 1):
        path = [V((sx * 0.45, 0, 1.5)), V((sx * 0.5, 0, 1.85)), V((sx * 0.3, 0, 1.95)), V((sx * 0.2, 0, 1.6))]
        util.tube(bm, util.catmull(path, 4), 0.045, n=8, power=3)
    # lid (domed) with lion-ish finial
    util.lathe(bm, [(0.58, 1.56), (0.5, 1.66), (0.3, 1.78), (0.12, 1.84), (0.1, 1.92), (0.16, 2.0),
                    (0.1, 2.12), (0.001, 2.16)], segs=24)
    o = util.mesh_object("Cauldron", bm, m["bronze"])
    util.box_uv(o, 1.5)
    bm_i, bm_g = bmesh.new(), bmesh.new()
    rnd = random.Random(2)
    for k in range(7):
        x, y = rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25)
        tip = V((x * 1.3, y * 1.3, 1.95 + rnd.uniform(-0.05, 0.1)))
        util.tube(bm_i, [V((x, y, 1.4)), tip], 0.008, n=5)
        util.sphere(bm_g, 0.014, loc=tip, segs=6, rings=4)
    inc = util.mesh_object("IncenseSticks", bm_i, util.material("incense", color="#8a3b2a", rough=0.8))
    embers = util.mesh_object("IncenseEmbers", bm_g, util.material("ember", color="#ff6a2a", emission="#ff5a1a",
                                                                  emission_strength=8.0))
    return [pl, o, inc, embers, util.collider("BurnerCol", (2.0, 2.0, 2.0), (0, 0, 1.0))]


def banner():
    """Sect banner: tall pole with a hanging silk pennant."""
    m = _m()
    s = 512
    u, v = tex.grid(s)
    col = tex.lerp(tex.srgb("#1f3150"), tex.srgb("#2c4670"), tex.fbm(s, 4, 4, 0.5, 5) * 0.5)
    # emblem: a white cloud swirl in a ring + a sword stroke
    x, y = u - 0.5, (v - 0.65) * 0.4
    r = np.sqrt(x * x + y * y)
    ring = (np.abs(r - 0.28) < 0.02)
    mask = np.zeros((s, s), np.float32)
    tex.stamp_curve(mask, [((0.5 + 0.18 * math.cos(t) * (1 - t / 12)) % 1, 0.65 + 0.45 * math.sin(t) * (1 - t / 12))
                           for t in np.linspace(0, 10, 200)], 0.012, s)
    tex.stamp_curve(mask, [(0.5, vv) for vv in np.linspace(0.12, 0.45, 60)], 0.015, s)
    border = (u < 0.05) | (u > 0.95)
    emb = np.clip(mask + ring + border * 1.0, 0, 1)
    col = tex.lerp(col, tex.srgb("#e9e4d6"), emb)
    maps = tex.result(col, 0.6, 0.0, tex.weave(s) * 0.3)
    flag = util.material("banner_silk", maps, double_sided=True, normal_strength=0.3)
    bm = bmesh.new()
    util.cylinder(bm, 0.07, 0.05, 7.0, loc=(0, 0, 3.5), segs=10)
    util.sphere(bm, 0.12, loc=(0, 0, 7.05), segs=10, rings=6)
    util.cylinder(bm, 0.03, 0.03, 1.4, loc=(0.6, 0, 6.7), segs=6, rot=Matrix.Rotation(R(90), 4, "Y"))
    pole = util.mesh_object("BannerPole", bm, m["pillar"])
    util.box_uv(pole, 1.0)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    cols, rows = 8, 16
    vs = []
    for j in range(rows + 1):
        row = []
        for i in range(cols + 1):
            t = j / rows
            xx = 0.05 + 1.2 * i / cols
            zz = 6.65 - 4.2 * t
            yy = 0.12 * math.sin(t * 5.0 + i * 0.3) * t
            row.append(bm.verts.new(V((xx, yy, zz))))
        vs.append(row)
    for j in range(rows):
        for i in range(cols):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / cols, 1 - b / rows)
    cloth = util.mesh_object("BannerCloth", bm, flag)
    bm = bmesh.new()
    util.cylinder(bm, 0.4, 0.5, 0.5, loc=(0, 0, 0.25), segs=8)
    base = util.mesh_object("BannerBase", bm, m["stone"], smooth=False)
    util.box_uv(base, 1.0)
    return [pole, cloth, base, util.collider("BannerCol", (0.9, 0.9, 3.0), (0, 0, 1.5))]


def weapon_rack():
    m = _m()
    steel = util.material("steel", tex.metal("#c9ced6", rough=0.2))
    bm_w, bm_s = bmesh.new(), bmesh.new()
    for x in (-1.2, 1.2):
        util.box(bm_w, (0.12, 0.5, 0.1), loc=(x, 0, 0.05))
        util.box(bm_w, (0.1, 0.1, 1.9), loc=(x, 0, 0.95))
    util.box(bm_w, (2.6, 0.12, 0.1), loc=(0, 0, 1.75))
    util.box(bm_w, (2.6, 0.3, 0.08), loc=(0, 0, 0.35))
    for k in range(5):
        x = -0.9 + k * 0.45
        util.cylinder(bm_w, 0.022, 0.022, 2.3, loc=(x, -0.06, 1.35), segs=6)
        tip = V((x, -0.06, 2.5))
        util.cylinder(bm_s, 0.035, 0.001, 0.3, loc=tip + V((0, 0, 0.15)), segs=4)
        util.cylinder(bm_s, 0.03, 0.03, 0.04, loc=tip, segs=6)
        util.cylinder(bm_s, 0.06, 0.001, 0.12, loc=tip + V((0, 0, -0.08)), segs=6)
    wood = util.mesh_object("RackWood", bm_w, m["wood"], smooth=False)
    util.box_uv(wood, 1.0)
    steel_o = util.mesh_object("RackBlades", bm_s, steel, smooth=False)
    util.box_uv(steel_o, 2.0)
    tas = bmesh.new()
    for k in range(5):
        x = -0.9 + k * 0.45
        util.cylinder(tas, 0.012, 0.05, 0.14, loc=(x, -0.06, 2.28), segs=8)
    tassels = util.mesh_object("RackTassels", tas, m["cloth"])
    util.box_uv(tassels, 3)
    return [wood, steel_o, tassels, util.collider("RackCol", (2.7, 0.6, 2.0), (0, 0, 1.0))]


def formation_array():
    """Glowing formation disc with a floating spirit crystal (node 'SpiritCrystal')."""
    maps = tex.rune_circle(1024)
    emit = np.clip(maps["emit_mask"][..., None] * tex.srgb("#6fe7ff")[None, None, :], 0, 1)
    disc_m = util.material("formation_disc", maps, emission_map=emit, emission_strength=3.0, normal_strength=0.8)
    stone_m = util.material("granite", tex.stone("#b3aea5", 512))
    crystal_m = util.material("spirit_crystal", color="#78f0e0", rough=0.05, emission="#3fe0ff",
                              emission_strength=2.5, alpha=0.8)
    objs = []
    bm = bmesh.new()
    util.cylinder(bm, 4.6, 4.8, 0.3, loc=(0, 0, 0.15), segs=48)
    util.cylinder(bm, 4.25, 4.35, 0.18, loc=(0, 0, 0.37), segs=48)
    o = util.mesh_object("FormationSteps", bm, stone_m, smooth=False)
    util.box_uv(o, 0.6)
    objs.append(o)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    n = 64
    c = bm.verts.new(V((0, 0, 0.49)))
    ring = [bm.verts.new(V((4.1 * math.cos(2 * math.pi * k / n), 4.1 * math.sin(2 * math.pi * k / n), 0.49)))
            for k in range(n)]
    for k in range(n):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 8.6 + 0.5, loop.vert.co.y / 8.6 + 0.5)
    objs.append(util.mesh_object("FormationDisc", bm, disc_m, smooth=False))
    # four guardian pillars with glowing orbs
    bm_p, bm_o = bmesh.new(), bmesh.new()
    for k in range(4):
        a = R(45 + 90 * k)
        p = V((math.cos(a) * 3.9, math.sin(a) * 3.9, 0.46))
        util.cylinder(bm_p, 0.22, 0.26, 1.6, loc=p + V((0, 0, 0.8)), segs=8)
        util.cylinder(bm_p, 0.34, 0.34, 0.14, loc=p + V((0, 0, 1.62)), segs=8)
        util.sphere(bm_o, 0.2, loc=p + V((0, 0, 1.9)), segs=12, rings=8)
    o = util.mesh_object("FormationPillars", bm_p, stone_m, smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(util.mesh_object("FormationOrbs", bm_o, crystal_m))
    bm = bmesh.new()
    top, bot = V((0, 0, 1.3)), V((0, 0, -1.3))
    mid = [V((0.55 * math.cos(2 * math.pi * k / 6), 0.55 * math.sin(2 * math.pi * k / 6), 0.25)) for k in range(6)]
    tv = bm.verts.new(top)
    bv = bm.verts.new(bot)
    mv = [bm.verts.new(p) for p in mid]
    for k in range(6):
        bm.faces.new((tv, mv[k], mv[(k + 1) % 6]))
        bm.faces.new((bv, mv[(k + 1) % 6], mv[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cr = util.mesh_object("SpiritCrystal", bm, crystal_m, smooth=False)
    cr.location = (0, 0, 3.2)
    objs.append(cr)
    from . import arch
    objs.append(arch.frustum_col("FormationCol", 24, 4.35, 0.49, 5.6, -0.05))
    return objs


def stone_bridge(length=17.0, width=2.6, rise=1.4):
    """Arched stone bridge spanning the pond (along Y)."""
    m = _m()
    seg = 24
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()

    def deck_z(t):
        return rise * math.sin(math.pi * t)

    top, bot = [], []
    for i in range(seg + 1):
        t = i / seg
        y = -length / 2 + length * t
        z = deck_z(t)
        top.append((V((-width / 2, y, z)), V((width / 2, y, z))))
        bot.append((V((-width / 2, y, z - 0.35 - 0.6 * (1 - abs(2 * t - 1)))),
                    V((width / 2, y, z - 0.35 - 0.6 * (1 - abs(2 * t - 1))))))
    rows_t = [[bm.verts.new(a), bm.verts.new(b)] for a, b in top]
    rows_b = [[bm.verts.new(a), bm.verts.new(b)] for a, b in bot]
    for i in range(seg):
        faces = [
            (rows_t[i][0], rows_t[i][1], rows_t[i + 1][1], rows_t[i + 1][0]),
            (rows_b[i][1], rows_b[i][0], rows_b[i + 1][0], rows_b[i + 1][1]),
            (rows_t[i][1], rows_b[i][1], rows_b[i + 1][1], rows_t[i + 1][1]),
            (rows_b[i][0], rows_t[i][0], rows_t[i + 1][0], rows_b[i + 1][0]),
        ]
        for fv in faces:
            f = bm.faces.new(fv)
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co.y * 0.5, (co.x + co.z) * 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    deck = util.mesh_object("BridgeDeck", bm, m["marble"], smooth=False)
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * (width / 2 - 0.09)
        posts = 9
        for k in range(posts):
            t = k / (posts - 1)
            y = -length / 2 + length * t
            z = deck_z(t)
            util.box(bm, (0.16, 0.16, 0.9), loc=(x, y, z + 0.45))
            util.sphere(bm, 0.1, loc=(x, y, z + 0.95), segs=8, rings=5)
        rail = [V((x, -length / 2 + length * i / seg, deck_z(i / seg) + 0.8)) for i in range(seg + 1)]
        util.tube(bm, rail, (0.07, 0.06), n=6, power=3.0)
        rail2 = [V((x, -length / 2 + length * i / seg, deck_z(i / seg) + 0.3)) for i in range(seg + 1)]
        util.tube(bm, rail2, (0.05, 0.2), n=6, power=3.0)
    rails = util.mesh_object("BridgeRails", bm, m["marble"], smooth=False)
    util.box_uv(rails, 1.0)
    # walkable collision: the deck surface as a thin trimesh
    bm = bmesh.new()
    rows = [[bm.verts.new(a), bm.verts.new(b)] for a, b in top]
    for i in range(seg):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    col = util.mesh_object("BridgeWalk-colonly", bm, None, smooth=False)
    objs = [deck, rails, col]
    for sx in (-1, 1):
        c = util.collider("BridgeRail", (0.2, length, 1.0), (sx * (width / 2 - 0.08), 0, 1.4))
        objs.append(c)
    return objs


def lotus_cluster(seed=9):
    rnd = random.Random(seed)
    pad_m = util.material("lotus_pad", tex.foliage("#3f7a3a", 256, 143), normal_strength=0.5, double_sided=True)
    pet_m = util.material("lotus_petal", color="#f4b6cc", rough=0.5)
    bm_p, bm_f = bmesh.new(), bmesh.new()
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 2.2)
        c = V((math.cos(a) * r, math.sin(a) * r, 0.0))
        rad = rnd.uniform(0.35, 0.6)
        util.cylinder(bm_p, rad, rad, 0.02, loc=c, segs=16)
        if k % 3 == 0:
            fc = c + V((0.1, 0.1, 0.25))
            for j in range(8):
                ang = 2 * math.pi * j / 8
                d = V((math.cos(ang), math.sin(ang), 0.9)).normalized()
                util.sphere(bm_f, 0.12, loc=fc + d * 0.1, segs=8, rings=6, scale=(0.5, 0.5, 1.2))
            util.sphere(bm_f, 0.06, loc=fc + V((0, 0, 0.1)), segs=8, rings=5)
    pads = util.mesh_object("LotusPads", bm_p, pad_m, smooth=False)
    util.box_uv(pads, 1.0)
    fl = util.mesh_object("LotusFlowers", bm_f, pet_m)
    util.box_uv(fl, 3.0)
    return [pads, fl]


def training_dummy():
    m = _m()
    bm = bmesh.new()
    util.cylinder(bm, 0.16, 0.16, 1.7, loc=(0, 0, 0.85), segs=12)
    for (z, ang) in ((1.35, 15), (1.25, -15), (0.95, 0)):
        rot = Matrix.Rotation(R(90), 4, "X") @ Matrix.Rotation(R(ang), 4, "Y")
        util.cylinder(bm, 0.035, 0.03, 0.5, loc=(0, -0.3, z), rot=rot, segs=8)
    util.cylinder(bm, 0.03, 0.03, 0.5, loc=(0, -0.2, 0.45), rot=Matrix.Rotation(R(60), 4, "X"), segs=8)
    o = util.mesh_object("Dummy", bm, m["wood"])
    util.box_uv(o, 1.5)
    bm = bmesh.new()
    util.box(bm, (0.9, 0.9, 0.12), loc=(0, 0, 0.06))
    base = util.mesh_object("DummyBase", bm, m["stone"], smooth=False)
    util.box_uv(base, 1)
    return [o, base, util.collider("DummyCol", (0.5, 0.5, 1.8), (0, 0, 0.9))]

"""Buildings and landmarks of the enlarged bamboo forest (stilt houses, mills, a buried temple,
a cliff of stone buddhas, a banyan giant, rope bridges ...) plus shared wilderness pieces.

Fronts face -Y in Blender (+Z in Godot); origin at the footprint centre on the ground.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

from . import buildings as B
from . import buildings_town as T
from . import lands, nature, realms, tex, util

V = Vector
R = math.radians


def rustic():
    m = lands.kit()
    m["bamboo"] = util.material("culm", lands.culm(256), normal_strength=0.4)
    m["thatch"] = util.material("thatch", lands.thatch(256), normal_strength=1.2)
    m["mat"] = util.material("bamboo_mat", lands.woven("#a8834a", 256, 553), normal_strength=0.6)
    return m


def poles(bm, pts, r=0.08, segs=6):
    for a, b in pts:
        util.cylinder(bm, r, r, (V(b) - V(a)).length, loc=(V(a) + V(b)) / 2,
                      rot=(V(b) - V(a)).to_track_quat("Z", "Y").to_matrix().to_4x4(), segs=segs)


def thatched_roof(name, m, hw, hd, h, z, overhang=0.8):
    parts, _ = lands.gable_roof(name, hw + overhang, hd + overhang, h, {"tiles": m["thatch"], "wood": m["log"],
                                                                        "ridge": m["log"]},
                                base_z=z, curve=1.1, lift=0.05, thick=0.25, curl=False)
    return parts


def stilt_house(w=7.0, d=5.5, deck=2.2, seed=1, veranda=True):
    """Bamboo house on stilts: a slatted floor 2.2 m up, woven walls, a thatched roof, a ladder-stair
    down the front (ramp collision) and a railed veranda."""
    m = rustic()
    rnd = random.Random(seed)
    objs = []
    vd = 1.6 if veranda else 0.0
    bm = bmesh.new()
    for x in [-w / 2 + w * i / 4 for i in range(5)]:
        for y in (-d / 2 - vd, 0.0, d / 2):
            util.cylinder(bm, 0.12, 0.13, deck + 0.6, loc=(x, y, (deck - 0.6) / 2), segs=7)
    for x in (-w / 2, w / 2):
        util.tube(bm, [V((x, -d / 2 - vd, 0.2)), V((x, d / 2, deck - 0.2))], 0.06, n=5)
    objs.append(B.obj("Stilts", bm, m["bamboo"], uv=1.0, smooth=True))
    bm = bmesh.new()
    util.box(bm, (w + 0.3, d + vd + 0.3, 0.2), loc=(0, -vd / 2, deck - 0.1))
    objs.append(B.obj("Floor", bm, m["mat"], uv=0.8))
    # walls of woven bamboo, a doorway at the front
    bm = bmesh.new()
    wh = 2.4
    util.box(bm, (w, 0.12, wh), loc=(0, d / 2, deck + wh / 2))
    for sx in (-1, 1):
        util.box(bm, (0.12, d, wh), loc=(sx * w / 2, 0, deck + wh / 2))
        util.box(bm, (w / 2 - 0.6, 0.12, wh), loc=(sx * (w / 4 + 0.3), -d / 2, deck + wh / 2))
    util.box(bm, (1.2, 0.12, 0.5), loc=(0, -d / 2, deck + wh - 0.25))
    objs.append(B.obj("Walls", bm, m["mat"], uv=0.6))
    bm = bmesh.new()
    for x in (-w / 2, -0.6, 0.6, w / 2):
        util.box(bm, (0.14, 0.14, wh + 0.2), loc=(x, -d / 2, deck + wh / 2))
    if veranda:
        for x in [-w / 2 + w * i / 6 for i in range(7)]:
            util.box(bm, (0.07, 0.07, 0.9), loc=(x, -d / 2 - vd, deck + 0.45))
        util.box(bm, (w, 0.08, 0.08), loc=(0, -d / 2 - vd, deck + 0.9))
    objs.append(B.obj("Frame", bm, m["bamboo"], uv=1.0))
    objs += thatched_roof("Thatch", m, w / 2, (d + vd) / 2, 2.2, deck + wh - 0.1, 0.9)
    for o in objs[-2:]:
        o.location.y -= vd / 2
        util.apply_transform(o)
    # the stair (a steep plank flight with slats) down the front-left, arriving on the veranda
    bm = bmesh.new()
    sw = 1.2
    n = max(1, math.ceil(deck / 0.2))
    run = n * 0.3
    for k in range(n):
        util.box(bm, (sw, 0.3, 0.06), loc=(-w / 2 + 1.0, -d / 2 - vd - run + (k + 0.5) * 0.3, deck * (k + 1) / n - 0.03))
    for sx in (-1, 1):
        util.tube(bm, [V((-w / 2 + 1.0 + sx * sw / 2, -d / 2 - vd - run - 0.1, 0.0)),
                       V((-w / 2 + 1.0 + sx * sw / 2, -d / 2 - vd, deck))], 0.05, n=5)
    objs.append(B.obj("Stair", bm, m["planks"], uv=1.0))
    col = B.ramp("StairRamp", sw + 0.2, -d / 2 - vd - run - 0.15, 0.0, -d / 2 - vd - 0.15, deck, x=-w / 2 + 1.0)
    objs.append(col)
    # jars, a drying rack of bamboo on the veranda
    bm = bmesh.new()
    T.jars(bm, w / 2 - 0.8, -d / 2 - vd / 2, n=2, seed=seed, r=0.22, h=0.6, spread=0.3)
    o = B.obj("Jars", bm, util.material("clay_glaze", lands.glaze("#6b4a32"), normal_strength=0.2), uv=1.0, smooth=True)
    o.location.z += deck
    util.apply_transform(o)
    objs.append(o)
    # collision: floor deck (walkable), walls, stilts
    objs.append(util.collider("Deck", (w + 0.3, d + vd + 0.3, 0.3), (0, -vd / 2, deck - 0.15)))
    objs.append(util.collider("Back", (w, 0.3, wh), (0, d / 2, deck + wh / 2)))
    for sx in (-1, 1):
        objs.append(util.collider("Side", (0.3, d, wh), (sx * w / 2, 0, deck + wh / 2)))
        objs.append(util.collider("Front", (w / 2 - 0.6, 0.3, wh), (sx * (w / 4 + 0.3), -d / 2, deck + wh / 2)))
    if veranda:
        objs.append(util.collider("Rail", (w - 2.2, 0.2, 1.0), (1.1, -d / 2 - vd, deck + 0.5)))
    for x in [-w / 2 + w * i / 4 for i in range(5)]:
        objs.append(util.collider("Stilt", (0.3, 0.3, deck), (x, d / 2, deck / 2)))
    del rnd
    return objs


def earth_shrine(scale=1.0, style="temple"):
    """A small earth-god shrine: stone base, a tiny roofed niche with a statue, an incense pot."""
    m = B.kit(style)
    objs = []
    bm = bmesh.new()
    util.box(bm, (2.4, 1.8, 0.6), loc=(0, 0, 0.1))
    util.box(bm, (1.8, 1.3, 1.5), loc=(0, 0.1, 1.15))
    objs.append(B.obj("ShrineBase", bm, m["brick"], uv=0.5))
    bm = bmesh.new()
    util.box(bm, (1.0, 0.1, 0.9), loc=(0, -0.55, 1.2))
    objs.append(B.obj("Niche", bm, m["dark"], uv=None))
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.0), (0.22, 0.0), (0.2, 0.3), (0.12, 0.45), (0.14, 0.62), (0.001, 0.72)], segs=10,
               loc=(0, -0.45, 0.8), cap_bottom=True)
    util.lathe(bm, [(0.001, 0.0), (0.22, 0.0), (0.26, 0.2), (0.2, 0.28), (0.001, 0.28)], segs=10, loc=(0, -1.3, 0.4))
    objs.append(B.obj("Statue", bm, m["gold"], uv=1.0, smooth=True))
    objs += B.hip_roof("Shrine", m, 0, 0.1, 1.5, 1.1, 0.9, 1.9, lift=0.3, lift_len=0.6, beasts=0, detail=0.5, rows=6)
    objs.append(util.collider("Shrine", (2.4, 1.8, 2.2), (0, 0, 1.1)))
    return lands.transform_objs(objs, scale=scale) if scale != 1.0 else objs


def lake_pavilion():
    """Hexagonal pavilion on piles over the water (deck 0.8 m above the origin = the water line),
    reached by a zig-zag plank walkway that runs 14 m toward +Y (Godot -Z) to the shore."""
    from . import arch
    m = rustic()
    km = B.kit("sect")
    objs = []
    deck = 0.8
    r = 4.0
    bm = bmesh.new()
    realms.prism(bm, [(r + 0.6, deck - 0.3), (r + 0.6, deck)], sides=6, rot=R(30), cap_top=True, cap_bottom=True,
                 v_scale=1.0)
    objs.append(B.obj("PavilionDeck", bm, m["planks"], uv=0.8))
    bm = bmesh.new()
    for k in range(6):
        a = R(30 + 60 * k)
        util.cylinder(bm, 0.18, 0.18, 4.0, loc=((r + 0.3) * math.cos(a), (r + 0.3) * math.sin(a), deck - 2.0), segs=6)
    # walkway: three legs zig-zagging to the shore
    legs = [((0, r + 0.3), (3.0, r + 5.0)), ((3.0, r + 5.0), (-1.5, r + 9.5)), ((-1.5, r + 9.5), (0.0, r + 14.0))]
    bm_w = bmesh.new()
    for (ax, ay), (bx, by) in legs:
        a_, b_ = V((ax, ay, deck)), V((bx, by, deck))
        dvec = b_ - a_
        ang = math.atan2(dvec.y, dvec.x)
        ln = dvec.length
        util.box(bm_w, (ln + 1.6, 1.6, 0.16), loc=((a_ + b_) / 2 - V((0, 0, 0.08))), rot=Matrix.Rotation(ang, 4, "Z"))
        for t in (0.0, 0.5, 1.0):
            p = a_.lerp(b_, t)
            for s in (-0.7, 0.7):
                q = p + V((-math.sin(ang) * s, math.cos(ang) * s, 0))
                util.cylinder(bm, 0.1, 0.1, 3.4, loc=(q.x, q.y, deck - 1.7), segs=6)
        objs.append(util.collider("Walk", (ln + 1.6, 1.6, 0.3), ((a_ + b_) / 2 - V((0, 0, 0.15))), rot_z=ang))
    objs.append(B.obj("Piles", bm, m["log"], uv=1.0, smooth=True))
    objs.append(B.obj("Walkway", bm_w, m["planks"], uv=0.8))
    bm_p, bm_s = bmesh.new(), bmesh.new()
    pts = [(r * math.cos(R(30 + 60 * i)), r * math.sin(R(30 + 60 * i))) for i in range(6)]
    for (x, y) in pts:
        B.column(bm_p, bm_s, x, y, deck, 3.2, r=0.17)
    objs.append(B.obj("Pillars", bm_p, km["pillar"], smooth=True))
    objs.append(B.obj("PillarBases", bm_s, km["stone"]))
    bm = bmesh.new()
    for i in range(6):
        a, b = V((*pts[i], 0)), V((*pts[(i + 1) % 6], 0))
        mid = (a + b) / 2
        dvec = b - a
        rot = Matrix.Rotation(math.atan2(dvec.y, dvec.x), 4, "Z")
        util.box(bm, (dvec.length, 0.22, 0.35), loc=(mid.x, mid.y, deck + 3.3), rot=rot)
        if i != 1:
            util.box(bm, (dvec.length - 0.3, 0.4, 0.08), loc=(mid.x * 0.97, mid.y * 0.97, deck + 0.5), rot=rot)
            util.box(bm, (dvec.length - 0.3, 0.3, 0.45), loc=(mid.x * 0.97, mid.y * 0.97, deck + 0.25), rot=rot)
    objs.append(B.obj("Beams", bm, km["beam"], uv=1.0))
    objs += arch.poly_roof("PavRoof", 0, 0, r + 1.2, 6, 2.6, km, base_z=deck + 3.5, rot=R(30), lift=0.55,
                           lift_len=1.3, curve=1.8, per_edge=10, rows=10)
    objs.append(realms._frustum_collider("PavDeck", (r + 0.6) * 0.866, deck, (r + 0.6) * 0.866, deck - 0.3)
                if False else util.collider("PavDeck", (2 * (r + 0.6), 2 * (r + 0.6) * 0.87, 0.3), (0, 0, deck - 0.15)))
    for (x, y) in pts:
        objs.append(util.collider("Pillar", (0.34, 0.34, 3.2), (x, y, deck + 1.6)))
    return objs


def fishing_jetty(length=14.0, width=2.0):
    """Plank jetty on log piles running toward -Y (Godot +Z) from the shore at the origin, deck 0.6 m up."""
    m = rustic()
    objs = []
    deck = 0.6
    rnd = random.Random(3)
    bm = bmesh.new()
    n = int(length / 0.3)
    for k in range(n):
        y = -(k + 0.5) * length / n
        util.box(bm, (width + rnd.uniform(-0.1, 0.1), 0.26, 0.07), loc=(rnd.uniform(-0.04, 0.04), y, deck - 0.035),
                 rot=Matrix.Rotation(R(rnd.uniform(-1.5, 1.5)), 4, "Z"))
    objs.append(B.obj("JettyDeck", bm, m["old_planks"], uv=1.0))
    bm = bmesh.new()
    for k in range(5):
        y = -1.0 - k * (length - 1.5) / 4
        for x in (-width / 2, width / 2):
            util.cylinder(bm, 0.11, 0.12, 3.6 + (0.6 if k == 4 else 0), loc=(x, y, deck - 1.8 + (0.3 if k == 4 else 0)),
                          segs=7)
        util.box(bm, (width + 0.2, 0.18, 0.18), loc=(0, y, deck - 0.2))
    objs.append(B.obj("JettyPiles", bm, m["log"], uv=1.0, smooth=True))
    bm = bmesh.new()
    for k in range(3):
        util.tube(bm, [V((0.5 + 0.1 * k, -length + 0.6, deck + 0.02)), V((1.6 + 0.4 * k, -length - 1.8, -0.5))], 0.012,
                  n=4)
    util.box(bm, (0.5, 0.35, 0.3), loc=(-0.4, -length + 1.2, deck + 0.15))
    objs.append(B.obj("FishingGear", bm, m["rope"], uv=1.0))
    objs.append(util.collider("Jetty", (width, length, 0.4), (0, -length / 2, deck - 0.2)))
    return objs


def waterwheel(r=3.4):
    """A creaking mill wheel on a stream, its axle carried by a stone pier and a little wheelhouse."""
    km = B.kit("rustic")
    m = rustic()
    objs = T.waterwheel_parts(km, r, (0.0, 0.0, r - 1.2), width=1.4)
    bm = bmesh.new()
    util.box(bm, (1.2, 1.4, r + 0.2), loc=(-1.6, 0.0, (r - 1.4) / 2))
    objs.append(B.obj("Pier", bm, km["stone"], uv=0.6))
    objs.append(util.collider("Pier", (1.2, 1.4, r), (-1.6, 0.0, (r - 1.4) / 2)))
    hut = rustic_hut(4.0, 3.4, seed=17)
    lands.transform_objs(hut, loc=(-4.6, 0.0, 0.0))
    objs += hut
    del m
    return objs


def rustic_hut(w=4.5, d=3.8, seed=7, loft=False):
    """Log-and-daub hut with a thatched gable roof, a doorway on the front."""
    m = rustic()
    objs = []
    wh = 2.4
    bm = bmesh.new()
    util.box(bm, (w, 0.3, wh), loc=(0, d / 2, wh / 2))
    for sx in (-1, 1):
        util.box(bm, (0.3, d, wh), loc=(sx * w / 2, 0, wh / 2))
        util.box(bm, (w / 2 - 0.55, 0.3, wh), loc=(sx * (w / 4 + 0.275), -d / 2, wh / 2))
    util.box(bm, (1.1, 0.3, 0.5), loc=(0, -d / 2, wh - 0.25))
    objs.append(B.obj("HutWalls", bm, m["daub"], uv=0.4))
    bm = bmesh.new()
    for (x, y) in ((-w / 2, -d / 2), (w / 2, -d / 2), (-w / 2, d / 2), (w / 2, d / 2), (-0.55, -d / 2), (0.55, -d / 2)):
        util.box(bm, (0.2, 0.2, wh + 0.1), loc=(x, y, wh / 2))
    util.box(bm, (w + 0.3, 0.22, 0.22), loc=(0, -d / 2, wh))
    util.box(bm, (w + 0.3, 0.22, 0.22), loc=(0, d / 2, wh))
    util.box(bm, (1.2, 0.1, 0.1), loc=(0, -d / 2 - 0.1, 0.15))
    objs.append(B.obj("HutFrame", bm, m["log"], uv=1.0))
    objs += thatched_roof("HutRoof", m, w / 2, d / 2, 1.8, wh - 0.1, 0.7)
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * w / 2
        vs = [bm.verts.new(V((x, -d / 2, wh))), bm.verts.new(V((x, d / 2, wh))), bm.verts.new(V((x, 0, wh + 1.7)))]
        bm.faces.new(vs if sx > 0 else list(reversed(vs)))
    objs.append(B.obj("HutGables", bm, m["daub"], uv=0.4))
    objs.append(util.collider("Back", (w, 0.4, wh), (0, d / 2, wh / 2)))
    for sx in (-1, 1):
        objs.append(util.collider("Side", (0.4, d, wh), (sx * w / 2, 0, wh / 2)))
        objs.append(util.collider("Front", (w / 2 - 0.55, 0.4, wh), (sx * (w / 4 + 0.275), -d / 2, wh / 2)))
    return objs


def hunter_lodge():
    """Log lodge with a porch, pelts drying on frames and antlers over the door."""
    m = rustic()
    objs = rustic_hut(7.0, 5.0, seed=21)
    hide = util.material("pelt", tex.leather("#6a4a32", 256, 11), double_sided=True, normal_strength=0.6)
    bm, bm_h = bmesh.new(), bmesh.new()
    for k in range(3):
        x = -4.5 + k * 1.6
        util.box(bm, (0.08, 0.08, 2.0), loc=(x - 0.6, -4.0, 1.0))
        util.box(bm, (0.08, 0.08, 2.0), loc=(x + 0.6, -4.0, 1.0))
        util.box(bm, (1.3, 0.08, 0.08), loc=(x, -4.0, 1.9))
        util.box(bm_h, (1.0, 0.03, 1.3), loc=(x, -4.0, 1.2), rot=Matrix.Rotation(R(4 * k - 4), 4, "Y"))
    util.tube(bm, [V((-0.5, -2.7, 2.1)), V((-0.2, -2.8, 2.5)), V((-0.6, -2.85, 2.9))], 0.04, n=5)
    util.tube(bm, [V((0.5, -2.7, 2.1)), V((0.2, -2.8, 2.5)), V((0.6, -2.85, 2.9))], 0.04, n=5)
    objs.append(B.obj("PeltFrames", bm, m["log"], uv=1.0, smooth=True))
    objs.append(B.obj("Pelts", bm_h, hide, uv=0.6))
    objs.append(util.collider("Pelts", (4.4, 0.4, 2.0), (-3.0, -4.0, 1.0)))
    return objs


def charcoal_kiln(r=2.6):
    """Domed earthen charcoal kiln with smoke vents and a bricked-up stoke door."""
    earthm = util.material("kiln_earth", lands.earth("#5d4a36", 256, 426, 0.3), normal_strength=0.8)
    objs = []
    bm = bmesh.new()
    res = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    for v in res["verts"]:
        if v.co.z < 0:
            v.co.z *= 0.1
        n_ = noise.noise(v.co * 3.0)
        v.co = V((v.co.x * r * (1 + 0.05 * n_), v.co.y * r * (1 + 0.05 * n_), v.co.z * r * 0.75))
    objs.append(B.obj("Dome", bm, earthm, uv=0.6, smooth=True))
    bm = bmesh.new()
    for k in range(5):
        a = 2 * math.pi * k / 5
        util.cylinder(bm, 0.12, 0.1, 0.3, loc=(math.cos(a) * r * 0.6, math.sin(a) * r * 0.6, r * 0.62), segs=6)
    util.box(bm, (1.0, 0.2, 1.0), loc=(0, -r + 0.05, 0.5))
    objs.append(B.obj("Vents", bm, B.glow("ember_glow", "#ff5a1a", 2.5), uv=None))
    objs.append(realms.convex("Kiln", _dome_hull(r)))
    return objs


def _dome_hull(r):
    bm = bmesh.new()
    for k in range(12):
        a = 2 * math.pi * k / 12
        for z, f in ((0.0, 1.0), (r * 0.45, 0.8), (r * 0.7, 0.4)):
            bm.verts.new(V((math.cos(a) * r * f, math.sin(a) * r * f, z)))
    return bm


def woodcutter_camp():
    """Stacked bamboo, a log pile, a saw pit with a trestle and a two-man saw, chopping block."""
    m = rustic()
    objs = []
    bm = bmesh.new()
    for k in range(18):
        util.cylinder(bm, 0.06, 0.06, 6.0, loc=(-3.0 + (k % 6) * 0.14, (k // 6) * 0.14 - 2.0, 0.08 + (k // 6) * 0.12),
                      rot=Matrix.Rotation(R(90), 4, "X"), segs=6)
    objs.append(B.obj("Bamboo", bm, m["bamboo"], uv=1.0, smooth=True))
    bm = bmesh.new()
    for k in range(9):
        row = k // 4 if k < 8 else 2
        util.cylinder(bm, 0.25, 0.25, 3.0, loc=(2.0 + (k % 4) * 0.52 + row * 0.26, 1.5, 0.25 + row * 0.44),
                      rot=Matrix.Rotation(R(90), 4, "X"), segs=10)
    util.cylinder(bm, 0.4, 0.42, 0.7, loc=(0.0, -3.0, 0.35), segs=12)
    util.box(bm, (0.2, 2.6, 0.2), loc=(-0.4, 3.2, 1.2))
    for y in (2.2, 4.2):
        for x in (-1.0, 0.2):
            util.box(bm, (0.14, 0.14, 1.3), loc=(x, y, 0.65))
    util.box(bm, (1.4, 0.2, 0.2), loc=(-0.4, 2.2, 1.3))
    util.box(bm, (1.4, 0.2, 0.2), loc=(-0.4, 4.2, 1.3))
    objs.append(B.obj("Logs", bm, m["log"], uv=1.0, smooth=True))
    bm = bmesh.new()
    util.box(bm, (0.04, 2.0, 0.25), loc=(-0.4, 3.2, 0.8))
    util.box(bm, (0.08, 0.5, 0.08), loc=(0.05, -3.0, 0.9), rot=Matrix.Rotation(R(30), 4, "X"))
    objs.append(B.obj("Tools", bm, B.kit("town")["gold"], uv=1.0))
    objs.append(util.collider("Bamboo", (1.0, 6.0, 0.5), (-2.65, -1.86, 0.25)))
    objs.append(util.collider("Logs", (2.6, 3.0, 1.2), (2.9, 1.5, 0.6)))
    objs.append(util.collider("Trestle", (1.6, 2.6, 1.4), (-0.4, 3.2, 0.7)))
    return objs


def giant_bamboo(seed=31, count=10, radius=3.0):
    """Giant bamboo: culms a hand thick and 18-22 m tall."""
    rnd = random.Random(seed)
    m = rustic()
    lc = lands.leaf_cards(256, 513, "#5b8a3a", kind="bamboo")
    leaf = lands.clip_alpha(util.material("bamboo_leaf_cards", lc, alpha=lc["alpha"], double_sided=True,
                                          normal_strength=0.3))
    bm_s, bm_l = bmesh.new(), bmesh.new()
    uvl = bm_l.loops.layers.uv.verify()
    objs = []
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0, radius)
        base = V((math.cos(a) * rr, math.sin(a) * rr, -0.2))
        h = rnd.uniform(17, 22)
        lean = V((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0))
        path = util.catmull([base, base + V((0, 0, h * 0.5)) + lean * 0.3, base + V((0, 0, h)) + lean], 6)
        rad = rnd.uniform(0.12, 0.17)
        util.tube(bm_s, path, lambda t: rad * (1 - 0.4 * t), n=8, uv_scale=(1, 0.15))
        for k in range(len(path) // 2, len(path)):
            p = path[k]
            for j in range(2):
                ang = rnd.uniform(0, 2 * math.pi)
                d = V((math.cos(ang), math.sin(ang), 0))
                s = rnd.uniform(1.6, 2.4)
                q0 = p - V((0, 0, 0.2))
                vs = [bm_l.verts.new(q0 + d * 0.1 - V((-d.y, d.x, 0)) * s * 0.4),
                      bm_l.verts.new(q0 + d * 0.1 + V((-d.y, d.x, 0)) * s * 0.4),
                      bm_l.verts.new(q0 + d * s + V((-d.y, d.x, 0)) * s * 0.4 - V((0, 0, s * 0.6))),
                      bm_l.verts.new(q0 + d * s - V((-d.y, d.x, 0)) * s * 0.4 - V((0, 0, s * 0.6)))]
                f = bm_l.faces.new(vs)
                for loop, uv in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                    loop[uvl].uv = uv
        objs.append(util.collider("Culm", (0.4, 0.4, 6.0), (base.x, base.y, 3.0)))
    objs.insert(0, util.mesh_object("GiantCulms", bm_s, m["bamboo"], smooth=True))
    objs.insert(1, util.mesh_object("GiantLeaves", bm_l, leaf, smooth=False))
    return objs


def banyan_giant(seed=41):
    """A giant banyan (~34 m across): a buttressed trunk, a ring of aerial-root pillars that form a
    walkable hall under the crown, and a great dome of foliage."""
    rnd = random.Random(seed)
    m = nature.mats()
    bark = util.material("banyan_bark", tex.bark("#5a4f42", 512, 139), normal_strength=1.0)
    objs = []
    bm_t, bm_f = bmesh.new(), bmesh.new()
    H = 16.0
    # the fused trunk: several twisting stems
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.2, 0.2)
        base = V((math.cos(a) * 2.4, math.sin(a) * 2.4, -0.4))
        pts = [base, base * 0.6 + V((0, 0, H * 0.35)), base * 0.3 + V((0, 0, H * 0.7)), base * 0.5 + V((0, 0, H))]
        util.tube(bm_t, util.catmull(pts, 4), lambda t: 1.1 * (1 - 0.5 * t) + 0.2, n=10)
    # boughs and aerial roots coming down to the ground as pillars (the "hall")
    for k in range(10):
        a = 2 * math.pi * k / 10 + rnd.uniform(-0.15, 0.15)
        d = V((math.cos(a), math.sin(a), 0))
        start = d * 1.5 + V((0, 0, H * 0.75))
        tip = d * rnd.uniform(13, 16) + V((0, 0, H * 0.85 + rnd.uniform(-1, 2)))
        util.tube(bm_t, util.catmull([start, start.lerp(tip, 0.5) + V((0, 0, 2.0)), tip], 4),
                  lambda t: 0.6 * (1 - 0.6 * t) + 0.1, n=8)
        for j in (0.55, 0.85):
            top = start.lerp(tip, j) + V((0, 0, 1.2))
            foot = V((top.x, top.y, -0.3)) + d * 0.6
            util.tube(bm_t, [top, top.lerp(foot, 0.5) + V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0)), foot],
                      lambda t: 0.28 + 0.2 * t, n=7)
            if j > 0.8:
                objs.append(util.collider("Root", (0.8, 0.8, H * 0.8), (foot.x, foot.y, H * 0.4)))
        for c in range(4):
            cpos = start.lerp(tip, 0.4 + 0.2 * c) + V((rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(1.5, 3.5)))
            s = rnd.uniform(3.2, 4.6)
            nature.blob(bm_f, cpos, (s * 1.3, s * 1.3, s * 0.65), 0.35, 1.8, seed + k * 5 + c, 2)
    nature.blob(bm_f, (0, 0, H + 2.5), (7, 7, 3.5), 0.35, 1.5, seed, 2)
    trunk = util.mesh_object("BanyanTrunk", bm_t, bark, smooth=True)
    util.box_uv(trunk, 0.5)
    fol = util.mesh_object("BanyanCrown", bm_f, m["pine"] if False else util.material(
        "banyan_leaves", tex.foliage("#3f6a2c", 256, 146), normal_strength=0.8), smooth=True)
    util.box_uv(fol, 0.3)
    objs = [trunk, fol] + objs
    objs.append(util.collider("Trunk", (5.4, 5.4, H), (0, 0, H / 2)))
    return objs


def spider_webs(seed=51):
    """Sheets of web strung between dead stems, and silk-wrapped cocoons hanging from them."""
    rnd = random.Random(seed)
    s = 256
    u, v = tex.grid(s)
    cu, cv = u - 0.5, v - 0.5
    r = (cu * cu + cv * cv) ** 0.5
    ang = tex.np.arctan2(cv, cu)
    spokes = tex.sstep(0.035, 0.0, abs(((ang / (2 * math.pi) * 16) % 1.0) - 0.5) * r * 2)
    rings = tex.sstep(0.04, 0.0, abs(((r * 14) % 1.0) - 0.5) * 0.12)
    alpha = tex.np.clip((spokes + rings) * (r < 0.5), 0, 1) * 0.9
    col = tex.np.ones((s, s, 3), tex.np.float32) * 0.92
    maps = tex.result(col, 0.4, 0.0, None)
    web = lands.clip_alpha(util.material("web", maps, alpha=alpha, double_sided=True, normal_strength=0.0,
                                         emission="#cfe0e8", emission_strength=0.3))
    silk = util.material("cocoon_silk", tex.plaster("#d8d4c8", 128, 107), normal_strength=0.6)
    objs = []
    bm_w, bm_c, bm_s = bmesh.new(), bmesh.new(), bmesh.new()
    uvl = bm_w.loops.layers.uv.verify()
    stems = []
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.3, 0.3)
        p = V((math.cos(a) * rnd.uniform(4, 7), math.sin(a) * rnd.uniform(4, 7), 0))
        h = rnd.uniform(5, 8)
        util.tube(bm_s, [p, p + V((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), h))], lambda t: 0.18 * (1 - 0.6 * t),
                  n=6)
        stems.append((p, h))
        objs.append(util.collider("Stem", (0.4, 0.4, h), (p.x, p.y, h / 2)))
    for k in range(6):
        (p, h), (q, g) = stems[k], stems[(k + 1) % 6]
        a0 = p + V((0, 0, h * 0.35))
        b0 = q + V((0, 0, g * 0.35))
        a1 = p + V((0, 0, h * 0.95))
        b1 = q + V((0, 0, g * 0.95))
        vs = [bm_w.verts.new(x) for x in (a0, b0, b1, a1)]
        f = bm_w.faces.new(vs)
        for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uvl].uv = uv
        mid = (a1 + b1) / 2
        util.tube(bm_s, [mid, mid - V((0, 0, 0.8))], 0.01, n=4)
        util.sphere(bm_c, 0.35, loc=mid - V((0, 0, 1.4)), segs=10, rings=6, scale=(0.7, 0.7, 1.4))
    objs.insert(0, util.mesh_object("Webs", bm_w, web, smooth=False))
    objs.insert(1, B.obj("Cocoons", bm_c, silk, uv=1.0, smooth=True))
    objs.insert(2, B.obj("DeadStems", bm_s, util.material("dead_wood", tex.bark("#3a332c", 256, 138)), uv=1.0,
                         smooth=True))
    return objs


def lingzhi_ring(seed=61, n=16, radius=3.2):
    """A fairy ring of glowing lingzhi (reishi) brackets on little stumps."""
    rnd = random.Random(seed)
    cap = util.material("lingzhi", tex.lacquer("#8a2a14", 128, 57, 0.4), emission="#ff8a3a", emission_strength=0.8,
                        normal_strength=0.4)
    stem = util.material("stump", tex.bark("#4a3a2a", 128, 136))
    bm_c, bm_s = bmesh.new(), bmesh.new()
    for k in range(n):
        a = 2 * math.pi * k / n + rnd.uniform(-0.1, 0.1)
        p = V((math.cos(a) * radius, math.sin(a) * radius, 0))
        h = rnd.uniform(0.2, 0.5)
        util.cylinder(bm_s, 0.12, 0.16, h, loc=p + V((0, 0, h / 2)), segs=7)
        for j in range(rnd.randint(1, 3)):
            s = rnd.uniform(0.25, 0.45)
            q = p + V((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), h + j * 0.12))
            util.sphere(bm_c, s, loc=q, segs=10, rings=5, scale=(1, 0.8, 0.22))
    return [B.obj("Caps", bm_c, cap, uv=1.0, smooth=True), B.obj("Stumps", bm_s, stem, uv=1.0, smooth=True)]


def buried_temple():
    """A temple hall half-swallowed by the earth: sunk 2.2 m and tilted, roots over its roof, the doors
    still open onto the sunken courtyard in front (origin = courtyard floor level at the doors)."""
    objs = B.hall("Buried", "temple", w=14.0, d=10.0, col_h=4.6, bays=5, podium_h=0.0, roof="xieshan", veranda=1.8,
                  beasts=3, plaque=True)
    objs = [o for o in objs if not o.name.startswith("BuriedBody")]
    # tilt and sink (the front stays at courtyard level)
    for o in objs:
        o.matrix_basis = Matrix.Translation(V((0, 0, -0.3))) @ Matrix.Rotation(R(3.5), 4, "Y") @ \
            Matrix.Rotation(R(-2.0), 4, "X") @ o.matrix_basis
        util.apply_transform(o)
    # break the roof: strip faces in a ragged patch
    lands._strip_faces(objs, lambda x, y, z: z > 6.0 and (x - 2.0) ** 2 + (y - 1.0) ** 2 < 9.0)
    rnd = random.Random(71)
    bark = util.material("root_bark", tex.bark("#4a4034", 256, 140), normal_strength=1.0)
    bm = bmesh.new()
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        start = V((rnd.uniform(-6, 6), rnd.uniform(-2, 5), 8.5))
        end = start + V((math.cos(a) * rnd.uniform(5, 9), math.sin(a) * rnd.uniform(5, 9), -8.5))
        mid = start.lerp(end, 0.5) + V((0, 0, rnd.uniform(1.0, 2.5)))
        util.tube(bm, util.catmull([start + V((0, 0, 2)), start, mid, end], 4), lambda t: 0.45 * (1 - 0.5 * t) + 0.08,
                  n=7)
    objs.append(B.obj("Roots", bm, bark, uv=0.6, smooth=True))
    km = B.kit("temple")
    objs.append(util.collider("BuriedBody", (14.3, 10.3, 5.0), (0, 0, 2.2)))
    del km
    return objs


def buddha_cliff(width=36.0, height=22.0, niches=5, seed=81):
    """A cliff face carved with weathered seated buddhas in arched niches (faces -Y), with a narrow
    ledge path along its foot (the cliff itself is solid)."""
    rnd = random.Random(seed)
    rock = util.material("buddha_rock", lands.crag("#8a8478", 512, 603, "#56643a"), normal_strength=1.0)
    carved = util.material("buddha_stone", tex.stone("#a39d90", 256, 77, 0.2), normal_strength=0.8)
    objs = []
    # the cliff: a thick slab with a noisy front face
    bm = bmesh.new()
    nx, nz = 36, 22
    front = []
    for j in range(nz + 1):
        row = []
        for i in range(nx + 1):
            x = -width / 2 + width * i / nx
            z = -1.0 + (height + 1.0) * j / nz
            d = noise.fractal(V((x * 0.15, z * 0.15, seed)), 0.7, 2.0, 4) * 1.2
            edge = min(1.0, (width / 2 - abs(x)) / 4.0)
            row.append(bm.verts.new(V((x, -1.5 * edge + d * edge + (0 if j < nz else 2.0), z))))
        front.append(row)
    uvl = bm.loops.layers.uv.verify()
    for j in range(nz):
        for i in range(nx):
            f = bm.faces.new((front[j][i], front[j][i + 1], front[j + 1][i + 1], front[j + 1][i]))
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.x * 0.08, loop.vert.co.z * 0.08)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    back = []
    for (x, z) in ((-width / 2, -1.0), (width / 2, -1.0), (width / 2, height), (-width / 2, height)):
        back.append(bm.verts.new(V((x, 6.0, z))))
    objs.append(util.mesh_object("CliffFace", bm, rock, smooth=True))
    # niches and buddhas
    bm_n, bm_b = bmesh.new(), bmesh.new()
    for k in range(niches):
        x = -width / 2 + width * (k + 0.5) / niches
        big = k == niches // 2
        s = 1.8 if big else 1.0
        z0 = 0.8 if big else rnd.choice((0.8, 7.5))
        nw, nh = 3.2 * s, 5.0 * s
        outline = lands.arc_outline(nw, nh * 0.6, 10, 0.0)
        tmp = bmesh.new()
        lands.extrude_outline(tmp, outline, -1.2, -0.9)
        bmesh.ops.translate(tmp, verts=tmp.verts, vec=V((x, 0, z0)))
        lands.merge(bm_n, tmp)
        # seated buddha: crossed legs, body, head with ushnisha, halo
        cx, cy, cz = x, -1.4, z0
        util.sphere(bm_b, 1.0 * s, loc=(cx, cy - 0.2 * s, cz + 0.5 * s), segs=12, rings=6, scale=(1.3, 0.8, 0.45))
        util.sphere(bm_b, 0.8 * s, loc=(cx, cy, cz + 1.5 * s), segs=12, rings=8, scale=(0.9, 0.65, 1.15))
        util.sphere(bm_b, 0.42 * s, loc=(cx, cy - 0.1 * s, cz + 2.65 * s), segs=12, rings=8, scale=(0.9, 0.9, 1.05))
        util.sphere(bm_b, 0.18 * s, loc=(cx, cy - 0.05 * s, cz + 3.1 * s), segs=8, rings=5)
        for sx in (-1, 1):
            util.sphere(bm_b, 0.1 * s, loc=(cx + sx * 0.42 * s, cy - 0.05 * s, cz + 2.55 * s), segs=6, rings=4,
                        scale=(0.6, 0.5, 1.6))
        halo = [V((cx + 0.9 * s * math.cos(a), cy + 0.25, cz + 2.65 * s + 0.9 * s * math.sin(a)))
                for a in [2 * math.pi * i / 24 for i in range(25)]]
        util.tube(bm_b, halo, 0.08 * s, n=5, closed_ends=False)
    objs.append(B.obj("Niches", bm_n, util.material("niche_shadow", color="#2e2a26", rough=1.0), uv=None))
    objs.append(B.obj("Buddhas", bm_b, carved, uv=0.8, smooth=True))
    objs.append(util.collider("Cliff", (width, 8.0, height + 1.0), (0, 2.5, height / 2 - 0.5)))
    return objs


def rope_bridge(length=30.0, width=1.8, sag=1.6):
    """Plank bridge on ropes spanning `length` along Y, ends at z = 0; posts at each end.
    Collision: the sagging plank walk as a trimesh strip and rope rails."""
    m = rustic()
    objs = []
    n = int(length / 0.35)
    bm = bmesh.new()
    rnd = random.Random(5)

    def z_at(y):
        t = (y + length / 2) / length
        return -sag * 4 * t * (1 - t)
    for k in range(n):
        y = -length / 2 + (k + 0.5) * length / n
        if rnd.random() < 0.05 and 2 < k < n - 3:
            continue
        util.box(bm, (width + rnd.uniform(-0.1, 0.1), 0.28, 0.06), loc=(0, y, z_at(y) - 0.03),
                 rot=Matrix.Rotation(R(rnd.uniform(-3, 3)), 4, "Z"))
    objs.append(B.obj("Planks", bm, m["old_planks"], uv=1.0))
    bm = bmesh.new()
    for sx in (-1, 1):
        for zoff in (0.0, 1.0):
            pts = [V((sx * width / 2, -length / 2 + length * i / 20, z_at(-length / 2 + length * i / 20) + zoff
                      + (0.15 if zoff else 0))) for i in range(21)]
            util.tube(bm, pts, 0.03, n=5)
        for i in range(0, 21, 2):
            y = -length / 2 + length * i / 20
            util.tube(bm, [V((sx * width / 2, y, z_at(y))), V((sx * width / 2, y, z_at(y) + 1.15))], 0.015, n=4)
    objs.append(B.obj("Ropes", bm, m["rope"], uv=2.0, smooth=True))
    bm = bmesh.new()
    for y in (-length / 2 - 0.3, length / 2 + 0.3):
        for sx in (-1, 1):
            util.cylinder(bm, 0.15, 0.17, 2.6, loc=(sx * (width / 2 + 0.2), y, 0.6), segs=8)
    objs.append(B.obj("Posts", bm, m["log"], uv=1.0, smooth=True))
    bm = bmesh.new()
    rows = []
    for i in range(21):
        y = -length / 2 - 0.6 + (length + 1.2) * i / 20
        rows.append((bm.verts.new(V((-width / 2, y, z_at(max(-length / 2, min(length / 2, y))) + 0.01))),
                     bm.verts.new(V((width / 2, y, z_at(max(-length / 2, min(length / 2, y))) + 0.01)))))
    for i in range(20):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    objs.append(util.mesh_object("Walk-colonly", bm, None, smooth=False))
    for sx in (-1, 1):
        for i in range(10):
            ya = -length / 2 + length * i / 10
            yb = ya + length / 10
            za, zb = z_at(ya), z_at(yb)
            c = util.collider("Rail", (0.2, length / 10 + 0.05, 1.3), (0, 0, 0))
            c.rotation_euler = (math.atan2(zb - za, yb - ya), 0, 0)
            c.location = (sx * (width / 2 + 0.1), (ya + yb) / 2, (za + zb) / 2 + 0.65)
            util.apply_transform(c)
            objs.append(c)
    return objs


def battlefield(seed=91):
    """Rusted spears and halberds stuck in the ground, broken shields, helmets and a shattered cart wheel."""
    rnd = random.Random(seed)
    iron = util.material("rust_iron", tex.metal("#5a3a28", 128, rough=0.8, patina="#8a4a22", patina_amt=0.5))
    wood = util.material("grey_wood", tex.wood("#6a6050", 128, 64))
    bm_i, bm_w = bmesh.new(), bmesh.new()
    for k in range(22):
        p = V((rnd.uniform(-7, 7), rnd.uniform(-7, 7), 0))
        tilt = V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 1)).normalized()
        ln = rnd.uniform(1.6, 2.6)
        util.tube(bm_w, [p - tilt * 0.3, p + tilt * ln], 0.03, n=4)
        tip = p + tilt * ln
        util.cylinder(bm_i, 0.06, 0.001, 0.35, loc=tip + tilt * 0.17, rot=tilt.to_track_quat("Z", "Y").to_matrix().to_4x4(),
                      segs=4)
        if k % 4 == 0:
            util.box(bm_i, (0.35, 0.03, 0.25), loc=tip - tilt * 0.1, rot=tilt.to_track_quat("Z", "Y").to_matrix().to_4x4())
    for k in range(7):
        p = V((rnd.uniform(-6, 6), rnd.uniform(-6, 6), 0.1))
        util.sphere(bm_i, 0.18, loc=p, segs=8, rings=4, scale=(1, 1, 0.8))
        util.cylinder(bm_w, 0.45, 0.45, 0.06, loc=p + V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0.0)),
                      rot=Matrix.Rotation(R(rnd.uniform(0, 30)), 4, "X"), segs=10)
    ring = [V((1.0 * math.cos(a), 3.0, 0.2 + 1.0 * math.sin(a) * 0.2)) for a in [2 * math.pi * i / 16 for i in range(17)]]
    util.tube(bm_w, ring, 0.06, n=5, closed_ends=False)
    return [B.obj("Iron", bm_i, iron, uv=1.0), B.obj("Hafts", bm_w, wood, uv=1.0, smooth=True)]


def burial_mounds(seed=93):
    """A row of grassed burial mounds with worn marker stones."""
    rnd = random.Random(seed)
    g = util.material("mound_grass", tex.grass(256, 124), normal_strength=0.6)
    st = util.material("marker_stone", tex.stone("#8a857a", 128, 78), normal_strength=0.8)
    bm, bm_s = bmesh.new(), bmesh.new()
    objs = []
    for k in range(5):
        x = -8 + k * 4.0 + rnd.uniform(-0.5, 0.5)
        y = rnd.uniform(-1, 1)
        lands.rock(bm, (x, y, -0.4), (1.8, 2.4, 1.2), 90 + k, 0.1, 2)
        util.box(bm_s, (0.5, 0.2, 0.9), loc=(x, y - 2.3, 0.4), rot=Matrix.Rotation(R(rnd.uniform(-8, 8)), 4, "Y"))
        objs.append(util.collider("Mound", (3.2, 4.2, 0.9), (x, y, 0.2)))
    return [B.obj("Mounds", bm, g, uv=0.5, smooth=True), B.obj("Markers", bm_s, st, uv=1.0)] + objs


def drying_racks():
    """An alchemist's bamboo racks of herbs and roots drying in the sun, a mortar and a small stove."""
    m = rustic()
    herb = util.material("dried_herbs", tex.foliage("#7a7a3a", 128, 147), normal_strength=0.6)
    bm, bm_h = bmesh.new(), bmesh.new()
    for row in range(2):
        y = row * 2.2 - 1.1
        for x in (-2.5, 0.0, 2.5):
            util.cylinder(bm, 0.05, 0.05, 1.8, loc=(x, y, 0.9), segs=6)
        for z in (0.8, 1.4):
            util.cylinder(bm, 0.04, 0.04, 5.2, loc=(0, y, z), rot=Matrix.Rotation(R(90), 4, "Y"), segs=6)
            util.box(bm, (5.0, 0.9, 0.03), loc=(0, y, z + 0.05))
            for k in range(10):
                nature.blob(bm_h, (-2.2 + k * 0.5, y + (k % 2) * 0.2 - 0.1, z + 0.12), (0.2, 0.2, 0.08), 0.4, 3.0, k + row,
                            1)
    objs = [B.obj("Racks", bm, m["bamboo"], uv=1.0, smooth=True), B.obj("Herbs", bm_h, herb, uv=1.0, smooth=True)]
    for row in range(2):
        objs.append(util.collider("Rack", (5.2, 1.0, 1.6), (0, row * 2.2 - 1.1, 0.8)))
    return objs


def stone_wall_low(length=6.0, h=1.3):
    """A low dry-stone wall segment (sacred spring, fields)."""
    st = util.material("drystone", lands.stone_blocks("#8e8a80", 256, 493, rows=4, cols=3, moss=0.35),
                       normal_strength=1.0)
    bm = bmesh.new()
    realms.tapered_box(bm, -length / 2, length / 2, -0.4, 0.4, -0.3, h, sides=(0, 0, 0.1, 0.1))
    o = B.obj("Wall", bm, st, uv=0.6)
    bm = bmesh.new()
    util.box(bm, (length + 0.1, 0.75, 0.15), loc=(0, 0, h + 0.05))
    return [o, B.obj("Cap", bm, st, uv=0.8), util.collider("Wall", (length, 0.8, h + 0.4), (0, 0, (h - 0.2) / 2 + 0.1))]


def forest_gate():
    """Rustic timber gate where the southern road leaves the forest."""
    return B.paifang("ForestGate", "rustic", bays=1, span=6.0, height=5.5, material="wood", plaque=True)


def watch_platform():
    """The sect's forest watchpost: a stilted lookout hut 6 m up with a ladder-stair (ramp)."""
    objs = stilt_house(5.0, 4.0, deck=6.0, seed=33, veranda=True)
    return objs


ASSETS = {
    "stilt_house": lambda: stilt_house(7.0, 5.5, 2.2, 1, True),
    "stilt_house_small": lambda: stilt_house(5.0, 4.5, 1.8, 2, False),
    "earth_shrine": earth_shrine,
    "lake_pavilion": lake_pavilion,
    "fishing_jetty": fishing_jetty,
    "waterwheel": waterwheel,
    "rustic_hut": rustic_hut,
    "hunter_lodge": hunter_lodge,
    "charcoal_kiln": charcoal_kiln,
    "woodcutter_camp": woodcutter_camp,
    "giant_bamboo": giant_bamboo,
    "banyan_giant": banyan_giant,
    "spider_webs": spider_webs,
    "lingzhi_ring": lingzhi_ring,
    "buried_temple": buried_temple,
    "buddha_cliff": buddha_cliff,
    "rope_bridge": rope_bridge,
    "battlefield_debris": battlefield,
    "burial_mounds": burial_mounds,
    "drying_racks": drying_racks,
    "stone_wall_low": stone_wall_low,
    "forest_gate": forest_gate,
    "forest_watchpost": watch_platform,
}

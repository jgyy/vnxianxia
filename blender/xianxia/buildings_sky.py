"""Celestial architecture of the enlarged Sky Isles (white jade and gold), bridges between isles,
landmarks (dragon bones, a sky-ship wreck, the tree of ages ...) and the chain bridge kit.

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


def chain_bridge(length=48.0, width=2.6, sag=2.0, style="sect"):
    """Suspension bridge of iron chains and planks along Y (ends at z = 0) between two stone anchor
    posts at each end. Collision: the sagging deck (trimesh) and chain-rail walls."""
    m = B.kit(style)
    iron = util.material(f"{style}_chain_iron", tex.metal("#3a3836", 128, rough=0.5, patina="#6a4a2e", patina_amt=0.3))
    objs = []

    def z_at(y):
        t = (y + length / 2) / length
        return 0.04 - sag * 4 * t * (1 - t)
    n = int(length / 0.4)
    rnd = random.Random(7)
    bm = bmesh.new()
    for k in range(n):
        y = -length / 2 + (k + 0.5) * length / n
        util.box(bm, (width, 0.34, 0.07), loc=(rnd.uniform(-0.03, 0.03), y, z_at(y) - 0.035))
    objs.append(B.obj("Planks", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    for sx in (-1, 1):
        for zoff in (0.0, 1.1):
            util.tube(bm, [V((sx * width / 2, -length / 2 + length * i / 24,
                              z_at(-length / 2 + length * i / 24) + zoff)) for i in range(25)], 0.045, n=6)
        for i in range(0, 25):
            y = -length / 2 + length * i / 24
            util.cylinder(bm, 0.015, 0.015, 1.1, loc=(sx * width / 2, y, z_at(y) + 0.55), segs=4)
    objs.append(B.obj("Chains", bm, iron, uv=1.0, smooth=True))
    bm = bmesh.new()
    for y in (-length / 2 - 0.4, length / 2 + 0.4):
        for sx in (-1, 1):
            util.box(bm, (0.7, 0.7, 2.4), loc=(sx * (width / 2 + 0.45), y, 0.6))
            util.box(bm, (0.9, 0.9, 0.3), loc=(sx * (width / 2 + 0.45), y, 1.95))
    objs.append(B.obj("Anchors", bm, m["stone"], uv=0.8))
    bm = bmesh.new()
    rows = []
    for i in range(25):
        y = -length / 2 - 0.8 + (length + 1.6) * i / 24
        z = z_at(max(-length / 2, min(length / 2, y))) + 0.01
        rows.append((bm.verts.new(V((-width / 2, y, z))), bm.verts.new(V((width / 2, y, z)))))
    for i in range(24):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    objs.append(util.mesh_object("Deck-colonly", bm, None, smooth=False))
    for sx in (-1, 1):
        for i in range(12):
            ya = -length / 2 + length * i / 12
            yb = ya + length / 12
            c = util.collider("Rail", (0.2, length / 12 + 0.05, 1.4), (0, 0, 0))
            c.rotation_euler = (math.atan2(z_at(yb) - z_at(ya), yb - ya), 0, 0)
            c.location = (sx * (width / 2 + 0.1), (ya + yb) / 2, (z_at(ya) + z_at(yb)) / 2 + 0.7)
            util.apply_transform(c)
            objs.append(c)
        for y in (-length / 2 - 0.4, length / 2 + 0.4):
            objs.append(util.collider("Anchor", (0.7, 0.7, 2.4), (sx * (width / 2 + 0.45), y, 0.6)))
    return objs


def sky_bridge(length=40.0, width=4.0, colours=None, name="Rainbow"):
    """A level bridge of light: translucent glowing bands (seven colours for the rainbow bridge) over a
    thin marble keel, with gold posts. Along Y, top at z = 0."""
    colours = colours or ["#ff5a5a", "#ffa64a", "#ffe45a", "#6aff7a", "#5ad8ff", "#5a7aff", "#c05aff"]
    sm = realms.sky_mats()
    objs = []
    bw = width / len(colours)
    for k, c in enumerate(colours):
        bm = bmesh.new()
        util.box(bm, (bw, length, 0.12), loc=(-width / 2 + bw * (k + 0.5), 0, -0.02))
        mat = util.material(f"{name}_band{k}", color=c, rough=0.2, emission=c, emission_strength=1.4, alpha=0.75)
        objs.append(util.mesh_object(f"Band{k}", bm, mat, smooth=False))
    bm = bmesh.new()
    util.box(bm, (width * 0.4, length, 0.5), loc=(0, 0, -0.45))
    objs.append(B.obj("Keel", bm, sm["marble"], uv=0.4))
    bm = bmesh.new()
    for y in [-length / 2 + length * i / 8 for i in range(9)]:
        for sx in (-1, 1):
            util.cylinder(bm, 0.07, 0.07, 1.0, loc=(sx * (width / 2 - 0.1), y, 0.5), segs=6)
            util.sphere(bm, 0.13, loc=(sx * (width / 2 - 0.1), y, 1.05), segs=8, rings=5)
    for sx in (-1, 1):
        util.box(bm, (0.06, length, 0.06), loc=(sx * (width / 2 - 0.1), 0, 0.95))
    objs.append(B.obj("Posts", bm, sm["gold"], uv=1.0, smooth=True))
    objs.append(util.collider("Deck", (width, length + 1.0, 0.4), (0, 0, -0.16)))
    for sx in (-1, 1):
        objs.append(util.collider("Rail", (0.3, length, 1.2), (sx * (width / 2 - 0.1), 0, 0.6)))
    return objs


def stepping_stone(seed=1, r=2.4):
    """A floating stepping stone: flat mossy top (walkable, z = 0) over a rough rock pendant."""
    sm = realms.sky_mats()
    rnd = random.Random(seed)
    bm = bmesh.new()
    realms.disc(bm, (0, 0), r, 16, z=0.04, uv_size=3.0, wobble=0.06, seed=seed)
    top = B.obj("Top", bm, sm["grass"], uv=None)
    bm = bmesh.new()
    prof = [(r * 1.0, 0.04), (r * 1.02, -0.3), (r * 0.8, -1.2), (r * 0.45, -2.4), (0.05, -3.4)]
    rings = realms.prism(bm, prof, sides=12, rot=0, cap_top=False, jitter=0.1, seed=seed)
    del rings
    rock = B.obj("Rock", bm, sm["cliff"], uv=0.5, smooth=True)
    del rnd
    return [top, rock, realms._frustum_collider("Stone", r * 0.92, 0.04, r * 0.7, -1.2)]


def armillary(bm, c, r):
    for k, (ax, ang) in enumerate((("X", 0), ("Y", 60), ("Z", 0), ("X", 120))):
        ring = [V((r * math.cos(a), r * math.sin(a), 0)) for a in [2 * math.pi * i / 32 for i in range(33)]]
        rot = Matrix.Rotation(R(90), 3, "X") if ax == "X" else (Matrix.Rotation(R(90), 3, "Y") if ax == "Y"
                                                                  else Matrix.Identity(3))
        rot = Matrix.Rotation(R(ang), 3, "Z") @ rot
        util.tube(bm, [rot @ p + V(c) for p in ring], 0.06 if k < 3 else 0.04, n=5, closed_ends=False)
    util.sphere(bm, r * 0.18, loc=c, segs=12, rings=8)


def observatory():
    """The armillary observatory: a slender octagonal spire of white jade with an open top terrace
    carrying a great gilded armillary sphere."""
    objs, top = B.tower(p="Obs", style="sky", sides=8, storeys=5, r0=3.6, shrink=0.86, storey_h=3.6, base_h=1.2,
                        base_r=6.0, spire=False, eave=1.2, roof_h=1.2)
    sm = realms.sky_mats()
    bm = bmesh.new()
    armillary(bm, (0, 0, top + 3.2), 2.6)
    util.cylinder(bm, 0.25, 0.35, 1.2, loc=(0, 0, top + 0.4), segs=8)
    objs.append(B.obj("Armillary", bm, sm["gold"], uv=1.0, smooth=True))
    return objs


def wind_temple():
    """Temple of the four winds: a round twelve-columned hall under a conical roof, open on all sides."""
    objs, top = B.tower(p="WindTemple", style="sky", sides=12, storeys=1, r0=7.0, storey_h=5.0, base_h=1.2,
                        base_r=9.0, spire=True, eave=1.8)
    # open the walls: drop the wall ring and window panels so the wind blows through
    objs = [o for o in objs if not (o.name.startswith("WindTempleWalls") or o.name.startswith("WindTempleWindows")
                                    or o.name.startswith("WindTempleBody"))]
    for k in range(12):
        a = 2 * math.pi * k / 12
        c = 1 / math.cos(math.pi / 12)
        objs.append(util.collider("Col", (0.5, 0.5, 5.0), (7.0 * c * math.cos(a), 7.0 * c * math.sin(a), 1.2 + 2.5)))
    sm = realms.sky_mats()
    bm = bmesh.new()
    realms.prism(bm, [(1.2, 1.2), (1.0, 2.2), (1.4, 2.4)], sides=8, rot=0, cap_top=True)
    objs.append(B.obj("Altar", bm, sm["jade"], uv=1.0))
    objs.append(util.collider("Altar", (2.4, 2.4, 1.2), (0, 0, 1.8)))
    return objs


def sky_ship_wreck():
    """A wrecked sky ship: a great junk hull broken-backed on its side, a snapped mast, torn sails."""
    sm = realms.sky_mats()
    hull_m = util.material("skyship_hull", lands.planks("#6a4a2e", 256, 409, boards=12), normal_strength=0.7,
                           double_sided=True)
    sail = util.material("skyship_sail", lands.canvas("#d8c8a0", 256, 471), double_sided=True, normal_strength=0.4)
    objs = []
    for part, (dy, roll, pitch) in enumerate(((-7.0, 18, 4), (7.5, 24, -9))):
        bm = bmesh.new()
        T.boat_hull(bm, 15.0, 7.0, 3.2, 1.8)
        vs = list(bm.verts)
        cut = [f for f in bm.faces if (f.calc_center_median().y > 5.5 if part == 0 else f.calc_center_median().y < -5.5)]
        bmesh.ops.delete(bm, geom=cut, context="FACES")
        realms.xform_verts(bm, [v for v in bm.verts], (0, dy, 2.2), yaw=0, pitch=R(pitch), roll=R(roll))
        del vs
        objs.append(util.mesh_object(f"Hull{part}", bm, hull_m, smooth=False))
    bm = bmesh.new()
    util.tube(bm, [V((0.5, -2.0, 2.0)), V((4.0, -3.0, 11.0))], 0.35, n=8)
    util.tube(bm, [V((5.0, 3.0, 0.3)), V((12.0, 6.0, 0.6))], 0.3, n=8)
    util.box(bm, (0.3, 7.0, 0.3), loc=(3.4, -2.8, 9.0), rot=Matrix.Rotation(R(15), 4, "X"))
    objs.append(B.obj("Masts", bm, B.kit("town")["wood"], uv=1.0, smooth=True))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    for (a, b, c, d) in ((V((3.3, -6.0, 9.5)), V((3.3, 0.5, 9.0)), V((2.4, 0.0, 4.5)), V((2.6, -5.0, 3.5))),
                         (V((7.0, 4.0, 0.5)), V((11.0, 5.5, 0.6)), V((10.0, 8.0, 0.4)), V((6.5, 7.0, 0.3)))):
        vs = [bm.verts.new(p) for p in (a, b, c, d)]
        f = bm.faces.new(vs)
        for loop, uv in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
            loop[uvl].uv = uv
    objs.append(util.mesh_object("Sails", bm, sail, smooth=False))
    objs.append(util.collider("Hull0", (7.0, 12.0, 5.0), (0.5, -7.0, 2.2)))
    objs.append(util.collider("Hull1", (7.0, 12.0, 5.0), (0.5, 7.5, 2.2)))
    del sm
    return objs


def dragon_bones():
    """The bleached skeleton of a true dragon (~40 m): a serpentine spine of vertebrae, arching ribs, a
    horned skull and clawed forelimbs, half sunk in the ground."""
    bone_m = util.material("dragon_bone", realms.bone(256, 443), normal_strength=0.8)
    bm = bmesh.new()
    objs = []
    spine = [V((math.sin(t * 2.2) * 5.0, -20 + 40 * t, 1.2 + 1.6 * math.sin(t * math.pi))) for t in
             [i / 40 for i in range(41)]]
    for i, p in enumerate(spine[:-1]):
        q = spine[i + 1]
        d = (q - p).normalized()
        rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        s = 1.0 - 0.7 * abs(i / 40 - 0.35)
        util.cylinder(bm, 0.45 * s, 0.45 * s, 0.7, loc=p, rot=rot, segs=8)
        util.cylinder(bm, 0.12 * s, 0.05, 1.2 * s, loc=p + V((0, 0, 0.8 * s)), segs=5)
        if 6 < i < 24 and i % 2 == 0:
            side = V((d.y, -d.x, 0)).normalized()
            for sgn in (-1, 1):
                pts = [p + side * sgn * 0.4, p + side * sgn * 3.2 * s + V((0, 0, 1.5 * s)),
                       p + side * sgn * 4.2 * s + V((0, 0, -1.4))]
                util.tube(bm, util.catmull(pts, 4), lambda t: 0.22 * s * (1 - 0.6 * t), n=6)
                if i % 4 == 0:
                    objs.append(util.collider("Rib", (0.6, 0.6, 3.0), tuple(p + side * sgn * 3.6 * s)))
    head = spine[-1] + V((0, 2.5, 0.8))
    util.sphere(bm, 1.6, loc=head, segs=12, rings=8, scale=(1.0, 1.8, 0.8))
    util.sphere(bm, 0.9, loc=head + V((0, 2.4, -0.4)), segs=10, rings=6, scale=(0.8, 1.6, 0.5))
    for sgn in (-1, 1):
        util.tube(bm, util.catmull([head + V((sgn * 0.8, -0.5, 1.0)), head + V((sgn * 1.8, -2.5, 2.2)),
                                    head + V((sgn * 1.6, -4.5, 2.0))], 4), lambda t: 0.3 * (1 - 0.8 * t), n=6)
    for (i, sgn) in ((10, 1), (10, -1)):
        p = spine[i]
        util.tube(bm, util.catmull([p, p + V((sgn * 3.0, -1.0, -0.5)), p + V((sgn * 4.0, -2.5, -1.4))], 4),
                  0.35, n=6)
    objs.insert(0, B.obj("Skeleton", bm, bone_m, uv=0.8, smooth=True))
    objs.append(util.collider("Skull", (3.4, 6.0, 2.6), tuple(head + V((0, 1.0, 0)))))
    return objs


def great_tree(seed=51, height=34.0, trunk_r=3.2, crown=16.0, blossom=False, name="TreeOfAges"):
    """A colossal tree: a flaring buttressed trunk, great limbs and a layered crown."""
    rnd = random.Random(seed)
    bark = util.material(f"{name}_bark", tex.bark("#5d4c3c", 512, 142), normal_strength=1.0)
    leafm = util.material(f"{name}_leaves", tex.blossom(256, 153) if blossom else tex.foliage("#3f7a3a", 256, 149),
                          normal_strength=0.7, emission="#fff0a0" if not blossom else None, emission_strength=0.08)
    bm_t, bm_f = bmesh.new(), bmesh.new()
    util.tube(bm_t, util.catmull([V((0, 0, -1.0)), V((0.5, 0.2, height * 0.35)), V((0, 0, height * 0.7))], 6),
              lambda t: trunk_r * (1 - 0.55 * t) + 0.4, n=14)
    for k in range(7):
        a = 2 * math.pi * k / 7
        d = V((math.cos(a), math.sin(a), 0))
        util.tube(bm_t, [d * trunk_r * 0.6 + V((0, 0, 3.5)), d * trunk_r * 1.6 + V((0, 0, 0.6)), d * trunk_r * 2.4
                         + V((0, 0, -0.6))], lambda t: 1.0 * (1 - 0.7 * t), n=7)
    for k in range(8):
        a = 2 * math.pi * k / 8 + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), 0))
        start = V((0, 0, height * (0.45 + 0.05 * (k % 3))))
        tip = d * crown * rnd.uniform(0.7, 1.0) + V((0, 0, height * rnd.uniform(0.7, 0.85)))
        util.tube(bm_t, util.catmull([start, start.lerp(tip, 0.5) + V((0, 0, 3)), tip], 4),
                  lambda t: 1.1 * (1 - 0.8 * t) + 0.1, n=8)
        for c in range(3):
            cp = start.lerp(tip, 0.55 + 0.22 * c) + V((0, 0, rnd.uniform(1, 3)))
            s = rnd.uniform(4.0, 6.0)
            nature.blob(bm_f, cp, (s * 1.3, s * 1.3, s * 0.6), 0.35, 1.6, seed + k * 3 + c, 2)
    nature.blob(bm_f, (0, 0, height + 2.0), (crown * 0.55, crown * 0.55, crown * 0.3), 0.3, 1.4, seed, 2)
    t = util.mesh_object(name + "Trunk", bm_t, bark, smooth=True)
    util.box_uv(t, 0.4)
    f = util.mesh_object(name + "Crown", bm_f, leafm, smooth=True)
    util.box_uv(f, 0.3)
    return [t, f, util.collider("Trunk", (trunk_r * 2, trunk_r * 2, height * 0.7), (0, 0, height * 0.35))]


def peach_tree(seed=57):
    """A peach tree of immortality: gnarled trunk, pink blossom and golden glowing peaches."""
    objs = nature.blossom_tree(seed, 5.5)
    rnd = random.Random(seed)
    peach = util.material("immortal_peach", color="#ffb070", rough=0.4, emission="#ffb040", emission_strength=0.9)
    bm = bmesh.new()
    for k in range(18):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(1.0, 2.6)
        util.sphere(bm, 0.14, loc=(math.cos(a) * r, math.sin(a) * r, rnd.uniform(3.0, 4.6)), segs=8, rings=5)
    objs.append(util.mesh_object("Peaches", bm, peach, smooth=True))
    return objs


def phoenix_nest():
    """A great phoenix nest of charred branches on a scorched crag, a glowing egg in its hollow."""
    wood = util.material("nest_twigs", tex.bark("#2e221a", 256, 143), normal_strength=1.0)
    egg = util.material("phoenix_egg", color="#ffc050", rough=0.2, emission="#ff8a2a", emission_strength=3.0)
    rnd = random.Random(61)
    bm = bmesh.new()
    for k in range(70):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(3.0, 5.0)
        z = rnd.uniform(0.3, 2.2)
        p = V((math.cos(a) * r, math.sin(a) * r, z))
        d = V((-math.sin(a), math.cos(a), rnd.uniform(-0.3, 0.3))) * rnd.uniform(2.0, 4.0)
        util.tube(bm, [p - d, p + V((0, 0, 0.2)), p + d], 0.09, n=4)
    bm_e = bmesh.new()
    util.sphere(bm_e, 0.9, loc=(0, 0, 1.3), segs=12, rings=8, scale=(1, 1, 1.35))
    objs = [B.obj("Nest", bm, wood, uv=1.0, smooth=True), B.obj("Egg", bm_e, egg, uv=None, smooth=True)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        objs.append(util.collider("Nest", (2.4, 1.4, 2.4), (math.cos(a) * 4.2, math.sin(a) * 4.2, 1.2), rot_z=a + 1.57))
    return objs


def sky_lanterns(seed=67, n=14, spread=10.0):
    """A drift of floating sky lanterns (no collision)."""
    rnd = random.Random(seed)
    paper = util.material("sky_lantern_paper", tex.paper_lantern("#ffd070", 128), emission="#ffb040",
                          emission_strength=2.2)
    bm = bmesh.new()
    for k in range(n):
        p = V((rnd.uniform(-spread, spread), rnd.uniform(-spread, spread), rnd.uniform(3, 14)))
        s = rnd.uniform(0.7, 1.1)
        util.cylinder(bm, 0.45 * s, 0.35 * s, 0.9 * s, loc=p, segs=8)
    return [util.mesh_object("SkyLanterns", bm, paper, smooth=True)]


def sword_spire():
    """A stone spire ringed by a halo of flying swords frozen mid-orbit."""
    sm = realms.sky_mats()
    steel = util.material("sword_steel", tex.metal("#c8d4dc", 128, rough=0.15))
    objs = []
    bm = bmesh.new()
    realms.prism(bm, [(2.4, -0.5), (1.8, 6.0), (1.0, 14.0), (0.02, 18.0)], sides=6, rot=0, jitter=0.12, seed=3)
    objs.append(B.obj("Spire", bm, sm["cliff"], uv=0.4))
    bm = bmesh.new()
    for ring, (rr, z, n) in enumerate(((6.0, 6.0, 12), (4.5, 10.5, 9), (3.2, 14.0, 7))):
        for k in range(n):
            a = 2 * math.pi * k / n + ring * 0.3
            c = V((rr * math.cos(a), rr * math.sin(a), z + 0.6 * math.sin(a * 2)))
            d = V((-math.sin(a), math.cos(a), 0.15)).normalized()
            rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            util.box(bm, (0.12, 0.03, 1.6), loc=c, rot=rot)
            util.box(bm, (0.45, 0.08, 0.08), loc=c - d * 0.8, rot=rot)
    objs.append(B.obj("Swords", bm, steel, uv=1.0))
    objs.append(util.collider("Spire", (3.6, 3.6, 12.0), (0, 0, 6.0)))
    return objs


def seal_of_heaven(r=9.0):
    """The seal of heaven: a great carved stone disc (walkable top, 1.2 m high with ramped rim)."""
    tb = realms.taiji_bagua(512, 552)
    face = realms._mat("seal_face", tb, 1.5, normal_strength=0.8)
    sm = realms.sky_mats()
    bm = bmesh.new()
    realms.disc(bm, (0, 0), r, 48, z=1.2)
    top = B.obj("SealFace", bm, face, uv=None)
    bm = bmesh.new()
    realms.prism(bm, [(r + 2.0, -0.5), (r, 1.18), (r - 0.02, 1.18)], sides=48, rot=0, cap_top=False, v_scale=0.5)
    return [top, B.obj("SealRim", bm, sm["carved"], uv=0.5, smooth=True),
            realms._frustum_collider("Seal", r, 1.2, r + 2.0, -0.5) if False else _cone_col("Seal", r, 1.2, r + 2.0, -0.5)]


def _cone_col(name, r_top, z_top, r_bot, z_bot, n=16):
    bm = bmesh.new()
    for r, z in ((r_top, z_top), (r_bot, z_bot)):
        for k in range(n):
            a = 2 * math.pi * k / n
            bm.verts.new(V((r * math.cos(a), r * math.sin(a), z)))
    return realms.convex(name, bm)


def sun_altar():
    """The golden sun altar: an octagonal stepped dais (walkable ramps) with a radiant gold disc."""
    sm = realms.sky_mats()
    bm = bmesh.new()
    realms._octagon_base(bm, 4, 5.0, step_w=0.6, step_h=0.22, z_top=0.88, bottom=-0.4)
    objs = [B.obj("Dais", bm, sm["marble"], uv=0.5)]
    objs.append(realms._frustum_collider("Dais", 5.0, 0.88, 7.4, -0.4))
    bm = bmesh.new()
    for k in range(16):
        a = 2 * math.pi * k / 16
        util.box(bm, (0.2, 2.8 if k % 2 else 1.8, 0.08), loc=(math.cos(a) * 3.0, math.sin(a) * 3.0, 0.92),
                 rot=Matrix.Rotation(a - math.pi / 2, 4, "Z"))
    util.cylinder(bm, 1.6, 1.6, 0.12, loc=(0, 0, 0.94), segs=24)
    objs.append(B.obj("Sun", bm, util.material("sun_gold", color="#ffd060", rough=0.2, metal=1.0, emission="#ffb030",
                                                emission_strength=1.2), uv=None))
    return objs


def cloud_pier(length=24.0, width=5.0):
    """The cloud harbour pier: a marble jetty jutting into the void toward -Y (Godot +Z), mooring posts
    with gold rings, jade lamps. Top at z = 0."""
    sm = realms.sky_mats()
    objs = []
    bm = bmesh.new()
    util.box(bm, (width, length, 0.8), loc=(0, -length / 2, -0.36))
    realms.prism(bm, [(0.3, -0.8), (width * 0.3, -3.0), (0.05, -5.0)], sides=6, rot=0, loc=(0, -length * 0.6, 0))
    objs.append(B.obj("Pier", bm, sm["marble"], uv=0.4))
    bm, bm_l = bmesh.new(), bmesh.new()
    for k in range(5):
        y = -2.0 - k * (length - 3) / 4
        for sx in (-1, 1):
            util.cylinder(bm, 0.2, 0.25, 1.1, loc=(sx * (width / 2 - 0.3), y, 0.55), segs=8)
            ring = [V((sx * (width / 2 - 0.3) + 0.3 * math.cos(a), y, 0.8 + 0.3 * math.sin(a)))
                    for a in [2 * math.pi * i / 12 for i in range(13)]]
            util.tube(bm, ring, 0.04, n=4, closed_ends=False)
            if k % 2 == 0:
                util.cylinder(bm, 0.07, 0.07, 2.4, loc=(sx * (width / 2 - 0.3), y - 1.5, 1.2), segs=6)
                util.sphere(bm_l, 0.25, loc=(sx * (width / 2 - 0.3), y - 1.5, 2.6), segs=10, rings=6)
    objs += [B.obj("Posts", bm, sm["gold"], uv=1.0, smooth=True), B.obj("Lamps", bm_l, sm["lamp"], uv=None, smooth=True)]
    objs.append(util.collider("PierDeck", (width, length, 0.8), (0, -length / 2, -0.36)))
    for sx in (-1, 1):
        objs.append(util.collider("Edge", (0.4, length, 1.1), (sx * (width / 2 - 0.3), -length / 2, 0.55)))
    return objs


def elixir_spring():
    """The spring of the elixir of life: a lotus-carved jade basin brimming with glowing water."""
    sm = realms.sky_mats()
    bm = bmesh.new()
    realms.prism(bm, [(4.6, -0.4), (4.6, 0.5), (4.2, 0.6), (4.0, 0.6), (4.0, 0.1)], sides=16, rot=0, cap_top=False,
                 v_scale=0.5)
    objs = [B.obj("Basin", bm, sm["jade"], uv=0.6, smooth=True)]
    bm = bmesh.new()
    realms.disc(bm, (0, 0), 4.05, 32, z=0.4)
    objs.append(B.obj("Elixir", bm, util.material("elixir", color="#9ff8e0", rough=0.05, emission="#5fffd0",
                                                  emission_strength=1.8, alpha=0.85), uv=None))
    for k in range(8):
        a = 2 * math.pi * k / 8
        objs.append(util.collider("Rim", (1.8, 0.5, 1.0), (math.cos(a) * 4.3, math.sin(a) * 4.3, 0.1), rot_z=a + 1.57))
    return objs


def thunder_rods(seed=71):
    """Bronze lightning rods on stone bases, crackling with captured lightning."""
    rnd = random.Random(seed)
    br = util.material("thunder_bronze", tex.metal("#6a5a3a", 128, rough=0.3, patina="#3a7a6a", patina_amt=0.4))
    bolt = B.glow("lightning", "#bfe0ff", 6.0)
    bm, bm_b = bmesh.new(), bmesh.new()
    objs = []
    for k in range(5):
        a = 2 * math.pi * k / 5
        p = V((math.cos(a) * 6, math.sin(a) * 6, 0))
        util.box(bm, (1.2, 1.2, 0.8), loc=p + V((0, 0, 0.4)))
        h = rnd.uniform(7, 10)
        util.cylinder(bm, 0.12, 0.05, h, loc=p + V((0, 0, 0.8 + h / 2)), segs=6)
        pts = [p + V((0, 0, 0.8 + h))]
        for j in range(5):
            pts.append(pts[-1] + V((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0.6, 1.2))))
        util.tube(bm_b, pts, 0.04, n=4)
        objs.append(util.collider("Rod", (1.2, 1.2, 3.0), tuple(p + V((0, 0, 1.5)))))
    return [B.obj("Rods", bm, br, uv=1.0), B.obj("Bolts", bm_b, bolt, uv=None)] + objs


ASSETS = {
    "chain_bridge": lambda: chain_bridge(48.0, 2.6, 2.0, "sect"),
    "rainbow_bridge": lambda: sky_bridge(44.0, 4.2),
    "stepping_stone": stepping_stone,
    "immortal_palace_gate": lambda: B.gate_house("PalaceGate", "sky", w=24.0, d=12.0, h=9.0, tower_storeys=2),
    "jade_palace_hall": lambda: B.hall("JadePalace", "sky", w=26.0, d=16.0, col_h=6.0, bays=9, podium_h=2.0,
                                       roof="double", veranda=2.6, beasts=7,
                                       stairs=(("front", 7.0), ("left", 4.0), ("right", 4.0))),
    "hall_of_records": lambda: B.hall("Records", "sky", w=18.0, d=11.0, col_h=4.6, bays=7, podium_h=1.4,
                                      roof="xieshan", veranda=2.0, storeys=2, beasts=5),
    "observatory": observatory,
    "wind_temple": wind_temple,
    "sky_ship_wreck": sky_ship_wreck,
    "dragon_bones": dragon_bones,
    "tree_of_ages": great_tree,
    "peach_tree": peach_tree,
    "phoenix_nest": phoenix_nest,
    "sky_lanterns": sky_lanterns,
    "sword_spire": sword_spire,
    "seal_of_heaven": seal_of_heaven,
    "gate_of_heaven": lambda: B.paifang("HeavenGate", "sky", bays=5, span=22.0, height=14.0, material="stone"),
    "sun_altar": sun_altar,
    "cloud_pier": cloud_pier,
    "elixir_spring": elixir_spring,
    "thunder_rods": thunder_rods,
    "sky_platform_huge": lambda: realms.sky_platform(38.0, 71),
    "sky_platform_mid": lambda: realms.sky_platform(28.0, 73, plaza=9.0),
    "sky_platform_palace": lambda: realms.sky_platform(46.0, 75, plaza=26.0),
    "sky_platform_moon": lambda: realms.sky_platform(38.0, 77, top="sand"),
    "sky_platform_burnt": lambda: realms.sky_platform(28.0, 79, top="burnt"),
    "sky_platform_terraces": lambda: realms.sky_platform(38.0, 81, top="terraces"),
    "sky_platform_crystal": lambda: realms.sky_platform(28.0, 83, top="crystal"),
    "mirror_pool": lambda: _mirror_pool(),
    "cypress_tree": lambda: _cypress(),
    "crane_figure": lambda: _crane(),
}


def _mirror_pool(r=7.0):
    """A lake that mirrors the sky: a still, glassy surface in a low white-jade rim (0.5 m proud of the
    ground, so the water is never coplanar with the isle's grass)."""
    sm = realms.sky_mats()
    mirror = util.material("sky_mirror", realms.mirror_surface(256, 492), normal_strength=0.1)
    bm = bmesh.new()
    realms.prism(bm, [(r + 0.9, -0.3), (r + 0.9, 0.45), (r + 0.5, 0.55), (r, 0.55), (r, 0.2)], sides=32, rot=0,
                 cap_top=False, v_scale=0.5)
    objs = [B.obj("MirrorRim", bm, sm["jade"], uv=0.6, smooth=True)]
    bm = bmesh.new()
    realms.disc(bm, (0, 0), r + 0.02, 48, z=0.4)
    objs.append(B.obj("MirrorWater", bm, mirror, uv=None))
    objs.append(_cone_col("MirrorRim", r + 0.5, 0.55, r + 2.4, -0.3))
    return objs


def _cypress(seed=81, h=11.0):
    """A columnar cypress (graveyards, ancestral tombs)."""
    rnd = random.Random(seed)
    m = nature.mats()
    bm_t, bm_f = bmesh.new(), bmesh.new()
    util.tube(bm_t, [V((0, 0, -0.2)), V((0.1, 0, h * 0.5)), V((0, 0.1, h * 0.9))], lambda t: 0.3 * (1 - 0.7 * t), n=8)
    for k in range(7):
        z = h * (0.2 + 0.11 * k)
        s = (1.6 - 0.18 * k) * rnd.uniform(0.9, 1.1)
        nature.blob(bm_f, (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), z), (s, s, h * 0.12), 0.3, 2.2, seed + k, 2)
    t = util.mesh_object("CypressTrunk", bm_t, m["bark"], smooth=True)
    f = util.mesh_object("CypressFoliage", bm_f, util.material("cypress", tex.foliage("#2a4a2e", 256, 150),
                                                               normal_strength=0.8), smooth=True)
    util.box_uv(f, 0.7)
    return [t, f, util.collider("Trunk", (0.6, 0.6, h * 0.5), (0, 0, h * 0.25))]


def _crane():
    """A red-crowned crane standing on one leg (bronze or living, as the scene needs)."""
    white = util.material("crane_white", tex.plaster("#f2f0ea", 128, 108), normal_strength=0.3)
    black = util.material("crane_black", color="#1a1a1c", rough=0.6)
    red = util.material("crane_red", color="#c21a1a", rough=0.5)
    bm, bm_b, bm_r = bmesh.new(), bmesh.new(), bmesh.new()
    util.sphere(bm, 0.35, loc=(0, 0, 1.25), segs=10, rings=6, scale=(0.7, 1.4, 0.8))
    util.tube(bm, util.catmull([V((0, -0.35, 1.35)), V((0, -0.55, 1.9)), V((0, -0.45, 2.3))], 4), 0.06, n=6)
    util.sphere(bm, 0.09, loc=(0, -0.48, 2.36), segs=8, rings=5)
    util.sphere(bm_r, 0.05, loc=(0, -0.47, 2.44), segs=6, rings=4)
    util.cylinder(bm_b, 0.025, 0.005, 0.3, loc=(0, -0.65, 2.34), rot=Matrix.Rotation(R(90), 4, "X"), segs=5)
    util.sphere(bm_b, 0.25, loc=(0, 0.45, 1.25), segs=8, rings=5, scale=(0.6, 1.0, 0.5))
    util.tube(bm_b, [V((0, 0, 1.0)), V((0, 0.05, 0.5)), V((0, 0, 0.0))], 0.02, n=4)
    util.tube(bm_b, [V((0.05, 0, 1.0)), V((0.2, 0.1, 0.8)), V((0.05, 0.05, 0.6))], 0.02, n=4)
    return [util.mesh_object("Crane", bm, white, smooth=True), util.mesh_object("CraneBlack", bm_b, black, smooth=True),
            util.mesh_object("CraneRed", bm_r, red, smooth=True)]

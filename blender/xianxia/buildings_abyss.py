"""Demonic architecture of the enlarged Blood Moon Abyss: obsidian, bone, chains and spikes.

Fronts face -Y in Blender (+Z in Godot); origin at the footprint centre on the ground.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

from . import buildings as B
from . import buildings_town as T
from . import buildings_wild as W
from . import lands, realms, tex, util

V = Vector
R = math.radians


def am():
    m = realms.abyss_mats()
    m.update({k: v for k, v in B.kit("abyss").items() if k not in m})
    m["obsidian"] = util.material("obsidian", realms.basalt(256, 415, "#141116"), normal_strength=1.2)
    m["bone"] = util.material("bone", realms.bone(256), normal_strength=0.8)
    m["iron"] = util.material("dark_iron", tex.metal("#2a2426", 128, rough=0.55, patina="#5a2a1a", patina_amt=0.3))
    m["ember"] = B.glow("blood_glow", "#ff2a10", 4.0)
    m["lava"] = util.material("lava", realms.liquid(256, 452, "#5a0a02", "#ff5a0a", "#ffb030"), emission="#ff4a0a",
                              emission_strength=3.5, normal_strength=0.3)
    return m


def spikes(bm, pts, h=1.2, r=0.18):
    for p in pts:
        util.cylinder(bm, r, 0.001, h, loc=V(p) + V((0, 0, h / 2)), segs=5)


def _skull_lo(bm, bm_e, p, a, s=1.0):
    """A low-poly skull (for walls and towers made of hundreds of them) facing outward along angle a."""
    d = V((math.cos(a), math.sin(a), 0))
    rot = Matrix.Rotation(a - math.pi / 2, 4, "Z")
    util.sphere(bm, 0.13 * s, loc=p + V((0, 0, 0.14 * s)), segs=6, rings=4, scale=(0.9, 1.0, 0.95))
    util.box(bm, (0.12 * s, 0.07 * s, 0.07 * s), loc=p + d * 0.09 * s + V((0, 0, 0.03 * s)), rot=rot)
    for sgn in (-1, 1):
        side = V((-d.y, d.x, 0)) * sgn * 0.045 * s
        util.box(bm_e, (0.045 * s, 0.03 * s, 0.045 * s), loc=p + d * 0.12 * s + side + V((0, 0, 0.13 * s)), rot=rot)


def obsidian_spire(seed=3, height=18.0):
    """A forest-tree of jagged obsidian: a tall faceted spire with lesser shards around its foot."""
    rnd = random.Random(seed)
    m = am()
    bm, bm_v = bmesh.new(), bmesh.new()
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        d = 0.0 if k == 0 else rnd.uniform(1.5, 3.5)
        h = height if k == 0 else rnd.uniform(3, 8)
        r = 2.0 if k == 0 else rnd.uniform(0.5, 1.2)
        base = V((math.cos(a) * d, math.sin(a) * d, -0.5))
        tilt = V((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 1)).normalized() if k else V((0, 0, 1))
        rings = realms.prism(bm, [(r, 0), (r * 0.8, h * 0.4), (r * 0.35, h * 0.85), (0.02, h)], sides=5,
                             rot=rnd.uniform(0, 6), jitter=0.2, seed=seed + k)
        vs = [v for ring in rings for v in ring]
        rot = tilt.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=Matrix.Translation(base) @ rot, verts=vs)
        if k == 0:
            util.tube(bm_v, [V((0.9, -1.2, 1.0)), V((0.5, -0.9, h * 0.4)), V((0.1, -0.3, h * 0.8))], 0.07, n=4)
    objs = [B.obj("Spire", bm, m["obsidian"], uv=0.4), B.obj("Veins", bm_v, m["ember"], uv=None)]
    objs.append(util.collider("Spire", (3.4, 3.4, height * 0.6), (0, 0, height * 0.3)))
    return objs


def bone_bridge(length=34.0, width=4.0):
    """A bridge of giant bones: a vertebral deck carried on a pair of curving rib arches, with rib
    balustrades. Along Y, ends at z = 0, walkable deck (trimesh)."""
    m = am()
    objs = []
    n = 28
    ys = [-length / 2 + length * i / n for i in range(n + 1)]

    def dz(y):
        t = y / (length / 2)
        return 1.2 * (1 - t * t)
    bm = bmesh.new()
    for i in range(n):
        y = (ys[i] + ys[i + 1]) / 2
        util.sphere(bm, 1.0, loc=(0, y, dz(y) - 0.25), segs=10, rings=5, scale=(width / 2, 0.62, 0.3))
        util.cylinder(bm, 0.15, 0.1, 1.1, loc=(0, y, dz(y) - 0.9), segs=6)
    for sx in (-1, 1):
        arc = [V((sx * (width / 2 - 0.4), y, dz(y) - 1.0 - 4.5 * (1 - (y / (length / 2)) ** 2) ** 0.5 * 0.0))
               for y in ys]
        under = [V((sx * (width / 2 - 0.4), y, dz(y) - 0.6 - 5.0 * max(0.0, 1 - (y / (length / 2)) ** 2)))
                 for y in ys]
        util.tube(bm, under, 0.45, n=8)
        del arc
        for i in range(0, n + 1, 2):
            y = ys[i]
            top = V((sx * (width / 2 - 0.1), y, dz(y) + 1.1))
            util.tube(bm, [V((sx * (width / 2 - 0.3), y, dz(y) - 0.2)), V((sx * (width / 2 + 0.2), y, dz(y) + 0.5)), top],
                      lambda t: 0.12 * (1 - 0.6 * t), n=6)
    objs.append(B.obj("Bones", bm, m["bone"], uv=1.0, smooth=True))
    bm, bm_e = bmesh.new(), bmesh.new()
    for y in (-length / 2, length / 2):
        realms.skull(bm, bm_e, (0, y - (0.4 if y < 0 else -0.4) * 0, 2.6), s=4.0, yaw=0 if y < 0 else math.pi)
    objs.append(B.obj("GateSkulls", bm, m["bone"], uv=1.0, smooth=True))
    objs.append(util.mesh_object("SkullEyes", bm_e, m["ember"], smooth=True))
    bm = bmesh.new()
    rows = [(bm.verts.new(V((-width / 2 + 0.3, y, dz(y) + 0.02))), bm.verts.new(V((width / 2 - 0.3, y, dz(y) + 0.02))))
            for y in ys]
    for i in range(n):
        bm.faces.new((rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]))
    objs.append(util.mesh_object("Deck-colonly", bm, None, smooth=False))
    for sx in (-1, 1):
        for i in range(0, n, 4):
            ya, yb = ys[i], ys[min(n, i + 4)]
            c = util.collider("Rail", (0.3, yb - ya, 1.3), (0, 0, 0))
            c.rotation_euler = (math.atan2(dz(yb) - dz(ya), yb - ya), 0, 0)
            c.location = (sx * (width / 2 - 0.05), (ya + yb) / 2, (dz(ya) + dz(yb)) / 2 + 0.6)
            util.apply_transform(c)
            objs.append(c)
    return objs


def mine_entrance():
    """Slave mine adit: a timber-framed portal in a rock face, a headframe with a wheel, rails, ore carts
    and chains. The portal faces -Y; the rock mass behind is solid."""
    m = am()
    km = B.kit("rustic")
    objs = []
    bm = bmesh.new()
    lands.rock(bm, (0, 6.0, 2.0), (9.0, 6.5, 6.0), 7, 0.25, 3)
    rock = B.obj("RockFace", bm, m["rock"], uv=0.3, smooth=True)
    objs.append(rock)
    bm = bmesh.new()
    util.box(bm, (3.8, 0.1, 4.2), loc=(0, 0.2, 2.1))
    objs.append(B.obj("Dark", bm, m["dark"] if "dark" in m else B.kit("abyss")["dark"], uv=None))
    bm = bmesh.new()
    for x in (-2.0, 2.0):
        util.box(bm, (0.4, 0.4, 4.6), loc=(x, -0.3, 2.3))
    util.box(bm, (4.8, 0.5, 0.5), loc=(0, -0.3, 4.6))
    for k in range(4):
        y = -0.3 - k * 1.8
    # headframe
    for (x, y) in ((-3.5, -5), (-3.5, -9), (-7.5, -5), (-7.5, -9)):
        util.box(bm, (0.3, 0.3, 8.0), loc=(x, y, 4.0))
    for z in (3.0, 7.8):
        util.box(bm, (4.3, 0.3, 0.3), loc=(-5.5, -5, z))
        util.box(bm, (4.3, 0.3, 0.3), loc=(-5.5, -9, z))
    objs.append(B.obj("Timbers", bm, km["wood"], uv=1.0))
    objs += T.waterwheel_parts(km, 1.8, (-5.5, -7.0, 8.4), width=0.4, paddles=0)
    bm = bmesh.new()
    for x in (-0.6, 0.6):
        util.box(bm, (0.1, 16.0, 0.12), loc=(x, -8.0, 0.06))
    for k in range(20):
        util.box(bm, (1.8, 0.2, 0.08), loc=(0, -0.5 - k * 0.8, 0.02))
    objs.append(B.obj("Rails", bm, m["iron"], uv=1.0))
    bm = bmesh.new()
    for y in (-5.0, -11.0):
        util.box(bm, (1.4, 2.0, 0.9), loc=(0, y, 0.7))
    objs.append(B.obj("Carts", bm, m["iron"], uv=1.0))
    bm = bmesh.new()
    for y in (-5.0, -11.0):
        lands.rock(bm, (0, y, 1.2), (0.6, 0.8, 0.35), int(-y), 0.3, 1)
    objs.append(B.obj("Ore", bm, m["ember"], uv=None, smooth=True))
    for y in (-5.0, -11.0):
        objs.append(util.collider("Cart", (1.4, 2.0, 1.2), (0, y, 0.6)))
    for x in (-2.0, 2.0):
        objs.append(util.collider("Post", (0.5, 0.5, 4.6), (x, -0.3, 2.3)))
    objs.append(util.collider("Rock", (18.0, 10.0, 10.0), (0, 5.3, 4.0)))
    for (x, y) in ((-3.5, -5), (-3.5, -9), (-7.5, -5), (-7.5, -9)):
        objs.append(util.collider("Leg", (0.4, 0.4, 8.0), (x, y, 4.0)))
    return objs


def soul_forge():
    """The soul forge: a black stepped furnace mouth roaring with red fire, a huge anvil, bellows
    and chains hung with cages whose occupants feed the flames."""
    m = am()
    objs = []
    bm = bmesh.new()
    realms.prism(bm, [(5.0, -0.5), (5.0, 1.0), (4.0, 1.0), (3.2, 7.0), (1.6, 11.0), (1.2, 16.0)], sides=6,
                 rot=R(30), cap_top=True, v_scale=0.3)
    objs.append(B.obj("Furnace", bm, m["blocks"], uv=0.4))
    bm = bmesh.new()
    util.box(bm, (3.2, 0.3, 3.4), loc=(0, -3.55, 2.8))
    for k in range(6):
        a = R(30 + 60 * k)
        util.box(bm, (0.5, 0.1, 1.5), loc=(3.5 * math.cos(a), 3.5 * math.sin(a), 5.0),
                 rot=Matrix.Rotation(a + math.pi / 2, 4, "Z"))
    util.cylinder(bm, 1.25, 1.25, 0.2, loc=(0, 0, 16.05), segs=8)
    objs.append(B.obj("Fire", bm, m["lava"], uv=0.5))
    bm = bmesh.new()
    util.box(bm, (1.2, 2.4, 1.0), loc=(0, -8.0, 0.5))
    util.box(bm, (2.2, 3.2, 0.6), loc=(0, -8.0, 1.3))
    util.cylinder(bm, 0.6, 0.001, 1.2, loc=(0, -10.2, 1.3), rot=Matrix.Rotation(R(90), 4, "X"), segs=8)
    for sx in (-1, 1):
        util.box(bm, (1.4, 3.0, 1.0), loc=(sx * 4.8, -3.0, 0.9), rot=Matrix.Rotation(R(sx * 20), 4, "Z"))
    objs.append(B.obj("Anvil", bm, m["iron"], uv=1.0))
    bm = bmesh.new()
    for sx in (-1, 1):
        realms.chain(bm, [(sx * 2.5, -3.0, 9.0), (sx * 5.0, -6.5, 6.0), (sx * 7.0, -9.0, 8.5)], 0.25, 0.04)
    objs.append(B.obj("Chains", bm, m["iron"], uv=1.0, smooth=True))
    objs.append(util.collider("Furnace", (8.0, 8.0, 12.0), (0, 0, 5.5)))
    objs.append(util.collider("Anvil", (2.2, 3.4, 1.6), (0, -8.2, 0.8)))
    for sx in (-1, 1):
        objs.append(util.collider("Bellows", (1.6, 3.2, 1.4), (sx * 4.8, -3.0, 0.7)))
    return objs


def skull_tower(height=12.0, r=2.4):
    """A tapering tower mortared from skulls, topped by a brazier of blood-fire."""
    m = am()
    rnd = random.Random(5)
    bm, bm_e = bmesh.new(), bmesh.new()
    rings = int(height / 1.1)
    core = bmesh.new()
    realms.prism(core, [(r, -0.3), (r * 0.6, height)], sides=10, rot=0, cap_top=True, v_scale=0.3)
    objs = [B.obj("Core", core, m["blocks"], uv=0.4)]
    for j in range(rings):
        z = j * 1.1
        rr = r - (r * 0.4) * z / height + 0.08
        cnt = max(5, int(2 * math.pi * rr / 0.8))
        for k in range(cnt):
            a = 2 * math.pi * (k + 0.5 * (j % 2)) / cnt
            _skull_lo(bm, bm_e, V((rr * math.cos(a), rr * math.sin(a), z)), a, 1.5 + rnd.uniform(-0.1, 0.1))
    bm_f = bmesh.new()
    bm_m = bmesh.new()
    realms.brazier(bm_m, bm_f, (0, 0, height), 1.4)
    objs += [B.obj("Skulls", bm, m["bone"], uv=1.0, smooth=True), util.mesh_object("Eyes", bm_e, m["ember"], smooth=True),
             B.obj("Brazier", bm_m, m["iron"], uv=1.0, smooth=True), util.mesh_object("Flames", bm_f, m["ember"],
                                                                                  smooth=True)]
    objs.append(util.collider("Tower", (r * 2, r * 2, height), (0, 0, height / 2)))
    return objs


def iron_pens(seed=9):
    """Pens of black iron bars for corrupted beasts, chained gates, bones in the straw."""
    m = am()
    bm = bmesh.new()
    objs = []
    for k in range(3):
        cx = -7.0 + k * 7.0
        for (ax, ay, bx, by) in ((-3, -3, 3, -3), (3, -3, 3, 3), (3, 3, -3, 3), (-3, 3, -3, -3)):
            n = 12
            for i in range(n + 1):
                x = cx + ax + (bx - ax) * i / n
                y = ay + (by - ay) * i / n
                util.cylinder(bm, 0.05, 0.05, 3.0, loc=(x, y, 1.5), segs=5)
            util.box(bm, (abs(bx - ax) + 0.12, abs(by - ay) + 0.12, 0.12), loc=(cx + (ax + bx) / 2, (ay + by) / 2, 2.9))
        spikes(bm, [(cx + dx, dy, 3.0) for dx in (-3, 3) for dy in (-3, 3)], 0.8, 0.12)
        for (sx, sy, lx, ly) in ((0, -3, 6, 0.3), (3, 0, 0.3, 6), (0, 3, 6, 0.3), (-3, 0, 0.3, 6)):
            objs.append(util.collider("Bars", (lx, ly, 3.0), (cx + sx, sy, 1.5)))
    objs.insert(0, B.obj("Bars", bm, m["iron"], uv=1.0))
    bm = bmesh.new()
    for k in range(3):
        realms.long_bone(bm, (-7 + k * 7 - 1, 0.5, 0.1), (-7 + k * 7 + 1, -0.4, 0.1))
    objs.insert(1, B.obj("Bones", bm, m["bone"], uv=1.0, smooth=True))
    return objs


def sacrifice_ring(r=9.0):
    """The ring around the sacrificial pit: black stones with chains dragged down into the pit."""
    m = am()
    bm, bm_c = bmesh.new(), bmesh.new()
    objs = []
    for k in range(12):
        a = 2 * math.pi * k / 12
        p = V((math.cos(a) * r, math.sin(a) * r, 0))
        realms.prism(bm, [(0.7, -0.5), (0.6, 2.4), (0.001, 3.1)], sides=4, rot=a, loc=p, cap_top=False)
        util.tube(bm_c, util.catmull([V((p.x, p.y, 2.2)), V((p.x * 0.75, p.y * 0.75, 0.2)),
                                      V((p.x * 0.45, p.y * 0.45, -2.5))], 4), 0.06, n=5)
        objs.append(util.collider("Stone", (1.2, 1.2, 3.0), (p.x, p.y, 1.2)))
    return [B.obj("Stones", bm, m["obsidian"], uv=0.5), B.obj("Chains", bm_c, m["iron"], uv=1.0, smooth=True)] + objs


def lava_fall(width=14.0, height=28.0):
    """A curtain of molten rock pouring over a ledge (faces -Y) into a glowing pool."""
    m = am()
    bm = bmesh.new()
    rows = []
    for j in range(13):
        t = j / 12
        z = height * (1 - t)
        y = -1.5 * t * t - 0.3
        rows.append([V((x * (1 + 0.15 * t), y + 0.3 * noise.noise(V((x * 0.3, t * 3, 1))), z))
                     for x in [-width / 2 + width * i / 10 for i in range(11)]])
    util.loft(bm, [list(r) for r in rows], closed=False, uv_scale=(2.0, 0.15))
    objs = [B.obj("LavaCurtain", bm, m["lava"], uv=None, smooth=True)]
    objs[0].data.materials[0].use_backface_culling = False
    bm = bmesh.new()
    realms.disc(bm, (0, -3.0), width * 0.55, 32, z=0.15, uv_size=4.0, wobble=0.1, seed=3)
    objs.append(B.obj("LavaPool", bm, m["lava"], uv=None))
    bm = bmesh.new()
    for k in range(8):
        a = 2 * math.pi * k / 8
        lands.rock(bm, (math.cos(a) * width * 0.6, -3.0 + math.sin(a) * width * 0.5, 0.2), (1.5, 1.2, 0.8), k, 0.3, 1)
    objs.append(B.obj("Rim", bm, m["obsidian"], uv=0.6, smooth=True))
    objs.append(util.collider("Pool", (width * 1.1, width * 0.9, 1.4), (0, -3.0, 0.2)))
    return objs


def seal_stone(seed=13):
    """A Verdant Lotus seal stone: a weathered standing stone bound with glowing green seal script."""
    rs = realms.rune_stone(256, 432, "#5a5a52", "#5aff8a", cols=1, rows=7, frame=True)
    mat = util.material("seal_stone", rs, emission_map=rs.get("emit"), emission_strength=2.0, normal_strength=0.8) \
        if rs.get("emit") is not None else util.material("seal_stone", rs)
    bm = bmesh.new()
    realms.prism(bm, [(0.9, -0.4), (0.85, 3.4), (0.6, 4.0), (0.001, 4.3)], sides=4, rot=R(45), cap_top=False)
    rope = util.material("seal_rope", tex.bark("#c8b070", 128, 135), normal_strength=0.4)
    bm_r = bmesh.new()
    ring = [V((0.95 * math.cos(a), 0.95 * math.sin(a), 2.6)) for a in [2 * math.pi * k / 16 for k in range(17)]]
    util.tube(bm_r, ring, 0.07, n=5, closed_ends=False)
    return [util.mesh_object("SealStone", bm, mat, smooth=False), B.obj("Rope", bm_r, rope, uv=1.0, smooth=True),
            util.collider("Stone", (1.5, 1.5, 4.0), (0, 0, 1.8))]


def ghost_house(seed=17):
    """An abandoned village house: broken walls, a half-fallen roof, ghost-lanterns burning blue."""
    objs = T.shophouse(8.0, 6.0, 1, seed=seed, roof="gable", style="rustic")
    lands._strip_faces(objs, lambda x, y, z: (z > 3.0 and x > 1.0) or (z > 1.2 and z < 3.0 and x > 2.5 and y > 0))
    paper = util.material("ghost_paper", tex.paper_lantern("#8ab0ff", 128), emission="#6a9aff", emission_strength=2.0)
    frame = util.material("lantern_frame", color="#2a1a12", rough=0.6)
    bm_p, bm_f = bmesh.new(), bmesh.new()
    realms.lantern(bm_p, bm_f, (-2.0, -4.5, 3.0), 0.8)
    objs += [util.mesh_object("GhostLantern", bm_p, paper, smooth=True), util.mesh_object("GhostFrame", bm_f, frame)]
    return objs


def ruined_gate():
    """A shattered sect gate: stone paifang with a fallen side span and a cracked lintel."""
    objs = B.paifang("RuinedGate", "abyss", bays=3, span=12.0, height=8.0, material="stone")
    lands._strip_faces(objs, lambda x, y, z: x > 3.0 and z > 3.5)
    m = am()
    bm = bmesh.new()
    util.box(bm, (4.5, 0.6, 0.6), loc=(5.5, -2.2, 0.3), rot=Matrix.Rotation(R(20), 4, "Z"))
    util.box(bm, (0.7, 3.5, 0.7), loc=(7.0, -1.5, 0.35), rot=Matrix.Rotation(R(80), 4, "Z"))
    objs.append(B.obj("Rubble", bm, m["blocks"], uv=0.5))
    objs.append(util.collider("Rubble", (4.5, 1.2, 0.8), (5.5, -2.2, 0.4)))
    return objs


def ruined_hall():
    """The burned hall of the destroyed sect: charred columns, a collapsed roof, scorched podium."""
    objs = B.hall("Burned", "abyss", w=18.0, d=11.0, col_h=5.0, bays=5, podium_h=1.2, roof="hip", veranda=2.0,
                  beasts=0, plaque=False)
    objs = [o for o in objs if not o.name.startswith("BurnedBody")]
    lands._strip_faces(objs, lambda x, y, z: (z > 6.5 and x < 2.5) or (z > 1.4 and z < 6.3 and y > 3.0 and x < 0))
    m = am()
    bm = bmesh.new()
    rnd = random.Random(21)
    for k in range(10):
        util.box(bm, (rnd.uniform(2, 5), 0.35, 0.35), loc=(rnd.uniform(-7, 1), rnd.uniform(-4, 4), 1.4 + 0.2),
                 rot=Matrix.Rotation(R(rnd.uniform(0, 180)), 4, "Z"))
    objs.append(B.obj("Beams", bm, util.material("charred", tex.bark("#1c1716", 128, 141)), uv=1.0))
    # back and right walls remain solid
    objs.append(util.collider("BackWall", (18.3, 0.5, 5.0), (0, 5.5, 1.2 + 2.5)))
    objs.append(util.collider("SideWall", (0.5, 11.3, 5.0), (9.0, 0, 1.2 + 2.5)))
    del m
    return objs


def watch_spire():
    """A tall black watch spire with a crenellated platform and a blood lantern."""
    objs, top = B.tower(p="WatchSpire", style="abyss", sides=6, storeys=4, r0=2.6, shrink=0.88, storey_h=4.0,
                        base_h=0.9, base_r=4.0, spire=True, eave=1.0)
    m = am()
    bm = bmesh.new()
    spikes(bm, [(3.6 * math.cos(R(60 * k)), 3.6 * math.sin(R(60 * k)), 0.9) for k in range(6)], 2.0, 0.25)
    objs.append(B.obj("Spikes", bm, m["iron"], uv=1.0))
    return objs


def bone_throne():
    """The first patriarch's throne: a high seat of fused bones on a four-step dais."""
    m = am()
    objs = B.podium("Dais", B.kit("abyss"), 4.0, 3.5, 1.0, stairs=(("front", 3.0),), rail=False, base="brick",
                    cap="stone")
    bm, bm_e = bmesh.new(), bmesh.new()
    util.box(bm, (2.6, 2.0, 0.9), loc=(0, 1.2, 1.45))
    util.box(bm, (2.6, 0.5, 4.0), loc=(0, 2.1, 3.0))
    for sx in (-1, 1):
        util.box(bm, (0.5, 2.0, 1.4), loc=(sx * 1.3, 1.2, 1.7))
        for k in range(5):
            realms.long_bone(bm, (sx * 1.3, 2.1, 1.0 + k * 0.8), (sx * (1.8 + 0.3 * k), 2.3, 3.0 + k * 0.7), r=0.09)
    for k in range(5):
        realms.skull(bm, bm_e, (-1.0 + k * 0.5, 2.0, 5.1 + 0.3 * math.sin(k)), s=1.5)
    objs += [B.obj("Throne", bm, m["bone"], uv=1.0, smooth=True), util.mesh_object("ThroneEyes", bm_e, m["ember"])]
    objs.append(util.collider("Throne", (2.6, 1.6, 4.0), (0, 2.0, 3.0)))
    return objs


def hanged_tree(seed=23):
    """A black corpse tree hung with iron gibbet cages on chains."""
    m = am()
    objs = realms.dead_tree(seed, 9.0)
    bm_c, bm_i = bmesh.new(), bmesh.new()
    rnd = random.Random(seed)
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        top = V((math.cos(a) * 2.6, math.sin(a) * 2.6, 6.2))
        realms.chain(bm_c, [top, top - V((0, 0, 1.5))], 0.2, 0.025)
        c = top - V((0, 0, 2.8))
        for j in range(8):
            b = 2 * math.pi * j / 8
            util.cylinder(bm_i, 0.025, 0.025, 1.3, loc=(c.x + 0.4 * math.cos(b), c.y + 0.4 * math.sin(b), c.z), segs=4)
        for dz in (-0.65, 0.65):
            util.cylinder(bm_i, 0.45, 0.45, 0.05, loc=(c.x, c.y, c.z + dz), segs=8)
        del rnd
        rnd = random.Random(k)
    objs += [B.obj("Chains", bm_c, m["iron"], uv=1.0, smooth=True), B.obj("Gibbets", bm_i, m["iron"], uv=1.0)]
    return objs


def sulphur_vent(seed=27):
    """A crusted yellow cone hissing sulphur fumes (glowing throat)."""
    sul = util.material("sulphur", tex.stone("#c8b43a", 128, 79, 0.5), normal_strength=1.0)
    bm, bm_g = bmesh.new(), bmesh.new()
    for k in range(3):
        a = 2 * math.pi * k / 3
        p = V((math.cos(a) * 2.2 * (k > 0), math.sin(a) * 2.2 * (k > 0), 0))
        h = 1.6 if k == 0 else 0.9
        util.lathe(bm, [(1.6 * h, -0.3), (1.2 * h, 0.4 * h), (0.45 * h, h), (0.3 * h, h * 0.9), (0.001, h * 0.6)],
                   segs=12, loc=p)
        realms.disc(bm_g, (p.x, p.y), 0.3 * h, 10, z=h * 0.92)
    return [B.obj("Vents", bm, sul, uv=1.0, smooth=True), B.obj("Throats", bm_g, B.glow("sulphur_glow", "#ffd83a", 3.0),
                                                                uv=None),
            util.collider("Cone", (3.0, 3.0, 1.4), (0, 0, 0.6))]


def poison_flowers(seed=29, n=26, radius=4.0):
    """A bed of glowing violet poison flowers with dark stems."""
    rnd = random.Random(seed)
    petal = util.material("poison_petal", color="#b03aff", rough=0.4, emission="#a02aff", emission_strength=1.6)
    stem = util.material("poison_stem", tex.foliage("#1f2a1a", 128, 148))
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for k in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        d = radius * math.sqrt(rnd.random())
        p = V((math.cos(a) * d, math.sin(a) * d, 0))
        h = rnd.uniform(0.5, 1.2)
        util.tube(bm_s, [p, p + V((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), h))], 0.025, n=4)
        for j in range(5):
            b = 2 * math.pi * j / 5
            util.sphere(bm_p, 0.12, loc=p + V((0.1 * math.cos(b), 0.1 * math.sin(b), h)), segs=6, rings=3,
                        scale=(1.6, 0.8, 0.3))
    return [B.obj("Petals", bm_p, petal, uv=None, smooth=True), B.obj("Stems", bm_s, stem, uv=1.0, smooth=True)]


def blood_moon_shrine():
    """An open-air shrine to the Blood Moon: a round dais, six fanged pillars and a hanging red disc."""
    m = am()
    bm = bmesh.new()
    realms.prism(bm, [(7.5, -0.6), (7.5, 0.5), (6.6, 0.5), (6.6, 0.9)], sides=24, rot=0, cap_top=True, v_scale=0.5)
    objs = [B.obj("Dais", bm, m["blocks"], uv=0.4)]
    objs.append(realms._frustum_collider("DaisCol", 7.2, 0.9, 10.2, -0.6))
    bm, bm_s = bmesh.new(), bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6
        p = V((math.cos(a) * 6.0, math.sin(a) * 6.0, 0.9))
        realms.prism(bm, [(0.5, 0), (0.45, 6.0), (0.001, 7.4)], sides=4, rot=a, loc=p, cap_top=False)
        spikes(bm_s, [(p.x, p.y, p.z + 3.0)], 0.9, 0.15)
        objs.append(util.collider("Pillar", (1.0, 1.0, 6.0), (p.x, p.y, p.z + 3.0)))
    objs += [B.obj("Pillars", bm, m["obsidian"], uv=0.5), B.obj("Fangs", bm_s, m["bone"], uv=1.0)]
    bm = bmesh.new()
    realms.disc(bm, (0, 0), 2.6, 32, z=0.0)
    for f in bm.faces:
        pass
    disc = B.obj("MoonDisc", bm, B.glow("moon_red", "#ff2a1a", 3.0), uv=None)
    disc.rotation_euler = (R(90), 0, 0)
    disc.location = (0, 2.0, 9.0)
    util.apply_transform(disc)
    disc.data.materials[0].use_backface_culling = False
    objs.append(disc)
    return objs


def shadow_stall(seed=31):
    """A shadow-market stall: black canopy, violet lanterns, a counter of jars, bones and scrolls."""
    objs = T.shophouse(6.0, 4.0, 1, seed=seed, roof="gable", style="abyss")
    return objs


def demon_palace():
    objs = B.hall("DemonPalace", "abyss", w=24.0, d=14.0, col_h=6.0, bays=7, podium_h=2.2, roof="double", veranda=2.4,
                  beasts=5, stairs=(("front", 7.0),))
    m = am()
    bm = bmesh.new()
    spikes(bm, [(x, y, 2.2) for x in (-13.5, 13.5) for y in (-9.0, 8.0)], 3.0, 0.4)
    spikes(bm, [(x, -10.5, 2.2) for x in (-9.0, -5.0, 5.0, 9.0)], 2.0, 0.25)
    objs.append(B.obj("Spikes", bm, m["iron"], uv=1.0))
    return objs


ASSETS = {
    "obsidian_spire": obsidian_spire,
    "obsidian_spire_small": lambda: obsidian_spire(7, 9.0),
    "bone_bridge": bone_bridge,
    "mine_entrance": mine_entrance,
    "soul_forge": soul_forge,
    "skull_tower": skull_tower,
    "iron_pens": iron_pens,
    "sacrifice_ring": sacrifice_ring,
    "lava_fall": lava_fall,
    "seal_stone": seal_stone,
    "ghost_house": ghost_house,
    "ruined_gate": ruined_gate,
    "ruined_hall": ruined_hall,
    "watch_spire": watch_spire,
    "bone_throne": bone_throne,
    "hanged_tree": hanged_tree,
    "sulphur_vent": sulphur_vent,
    "poison_flowers": poison_flowers,
    "blood_moon_shrine": blood_moon_shrine,
    "shadow_stall": shadow_stall,
    "demon_palace": demon_palace,
    "demon_library": lambda: B.tower(p="Library", style="abyss", sides=6, storeys=4, r0=5.0, shrink=0.85,
                                     storey_h=4.0, base_h=1.2, base_r=7.0, spire=True, eave=1.4)[0],
    "chain_bridge_dark": lambda: __import__("xianxia.buildings_sky", fromlist=["chain_bridge"]).chain_bridge(
        40.0, 3.0, 2.2, style="abyss"),
}

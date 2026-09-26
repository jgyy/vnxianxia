"""Vegetation, rocks, the mountain-top plateau and the sky backdrop."""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

from . import tex, util

V = Vector
R = math.radians


def mats():
    m = {}
    m["bark"] = util.material("pine_bark", tex.bark("#5a4535", 512), normal_strength=1.0)
    m["pine"] = util.material("pine_needles", tex.foliage("#2f5a35", 512), normal_strength=0.8)
    m["plum_bark"] = util.material("plum_bark", tex.bark("#3d2b26", 512, 132), normal_strength=1.0)
    m["blossom"] = util.material("plum_blossom", tex.blossom(512), normal_strength=0.8)
    m["rock"] = util.material("rock", tex.stone("#8e8a82", 512, 75), normal_strength=1.2)
    m["taihu"] = util.material("taihu_stone", tex.stone("#b7b4ab", 512, 76, 0.5), normal_strength=1.4)
    m["grass"] = util.material("grass", tex.grass(512), normal_strength=0.6)
    m["cliff"] = util.material("cliff", tex.cliff("#7d776c", 1024), normal_strength=1.2)
    m["paving"] = util.material("paving", tex.paving("#cdbfa6", 1024, gap=0.007, moss=0.12), normal_strength=1.0)
    m["bamboo"] = util.material("bamboo", tex.wood("#6f8f3a", 256, 62, rings=3), normal_strength=0.3)
    m["bamboo_leaf"] = util.material("bamboo_leaf", tex.foliage("#4f7f35", 256, 142), normal_strength=0.5)
    m["water"] = util.material("water", tex.water(256), alpha=0.82, normal_strength=0.6)
    return m


def displace(bm, amount, scale, seed=0.0, up_bias=0.0):
    off = V((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        n = v.co.normalized() if v.co.length > 1e-6 else V((0, 0, 1))
        d = noise.fractal(v.co * scale + off, 0.9, 2.0, 4)
        v.co += n * d * amount + V((0, 0, up_bias * d))


def blob(bm, loc, size, amount=0.25, scale=1.5, seed=0.0, subdiv=2):
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    verts = res["verts"]
    off = V((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in verts:
        n = v.co.normalized()
        d = noise.fractal(v.co * scale + off, 0.9, 2.0, 4)
        v.co = n * (1 + d * amount)
        v.co = V((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + V(loc)
    return verts


# --------------------------------------------------------------------------
# trees
# --------------------------------------------------------------------------
def pine_tree(seed=1, height=7.0):
    """Huangshan-style pine: twisting trunk, horizontal cloud-like needle pads."""
    rnd = random.Random(seed)
    m = mats()
    bm_t, bm_f = bmesh.new(), bmesh.new()
    lean = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * height * 0.18
    pts = [V((0, 0, 0)), V((0.1, 0, height * 0.3)) + lean * 0.3, V((0, 0.1, height * 0.6)) + lean * 0.8,
           V((0, 0, height)) + lean * 0.6]
    trunk = util.catmull(pts, 6)
    util.tube(bm_t, trunk, lambda t: 0.32 * height / 7 * (1 - 0.75 * t) + 0.02, n=12, uv_scale=(1, 0.5))
    # flared roots
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        d = V((math.cos(a), math.sin(a), 0))
        util.tube(bm_t, [d * 0.05 + V((0, 0, 0.5)), d * 0.5 + V((0, 0, 0.05)), d * 0.8 + V((0, 0, -0.1))],
                  lambda t: 0.16 * (1 - 0.8 * t), n=8)
    pads = []
    levels = 6
    for i in range(levels):
        t = 0.35 + 0.65 * i / (levels - 1)
        base = trunk[min(int(t * (len(trunk) - 1)), len(trunk) - 1)]
        a = rnd.uniform(0, 2 * math.pi) + i * 2.1
        ln = height * (0.42 - 0.3 * (i / levels)) * rnd.uniform(0.8, 1.2)
        d = V((math.cos(a), math.sin(a), rnd.uniform(-0.05, 0.15))).normalized()
        tip = base + d * ln + V((0, 0, rnd.uniform(0.0, 0.4)))
        mid = base.lerp(tip, 0.5) + V((0, 0, rnd.uniform(0.1, 0.4)))
        util.tube(bm_t, util.catmull([base, mid, tip], 4), lambda t: 0.1 * (1 - 0.8 * t) + 0.02, n=8)
        pads.append((tip, ln))
    pads.append((trunk[-1] + V((0, 0, 0.2)), height * 0.25))
    for j, (c, ln) in enumerate(pads):
        w = max(0.9, ln * 0.55)
        # each pad is a lumpy cluster of needle clumps, domed in the middle
        for k in range(9):
            a = rnd.uniform(0, 2 * math.pi)
            r = math.sqrt(rnd.random()) * w * 0.85
            off = V((math.cos(a) * r * 1.2, math.sin(a) * r, 0.0))
            dome = (1 - r / (w * 0.95)) * w * 0.28
            size = w * rnd.uniform(0.38, 0.6)
            blob(bm_f, c + off + V((0, 0, 0.1 + dome)), (size * 1.15, size, size * 0.42), 0.4,
                 2.4, seed * 10 + j + k * 0.37, 2)
    trunk_o = util.mesh_object("PineTrunk", bm_t, m["bark"])
    fol = util.mesh_object("PineNeedles", bm_f, m["pine"])
    util.box_uv(fol, 0.7)
    col = util.collider("TrunkCol", (0.6, 0.6, height * 0.6), (0, 0, height * 0.3))
    return [trunk_o, fol, col]


def blossom_tree(seed=3, height=5.0):
    """Plum blossom tree: gnarled trunk with pink blossom clusters."""
    rnd = random.Random(seed)
    m = mats()
    bm_t, bm_f = bmesh.new(), bmesh.new()

    def branch(p, d, ln, r, depth):
        pts = [p]
        cur = V(p)
        dd = V(d)
        for k in range(4):
            dd = (dd + V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.2, 0.4)))).normalized()
            cur = cur + dd * ln / 4
            pts.append(cur)
        util.tube(bm_t, util.catmull(pts, 3), lambda t: r * (1 - 0.7 * t) + 0.01, n=8)
        if depth > 0:
            for _ in range(rnd.randint(2, 3)):
                nd = (dd + V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 0.8)))).normalized()
                branch(pts[rnd.randint(2, 4)], nd, ln * 0.65, r * 0.55, depth - 1)
        else:
            for k in range(3):
                c = pts[-1] + V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.1, 0.3)))
                s = rnd.uniform(0.35, 0.6)
                blob(bm_f, c, (s * 1.2, s, s * 0.8), 0.45, 2.2, rnd.random() * 100, 2)

    trunk_top = V((0.3, 0.1, height * 0.45))
    util.tube(bm_t, util.catmull([V((0, 0, -0.1)), V((0.15, 0, height * 0.2)), trunk_top], 4),
              lambda t: 0.28 * (1 - 0.4 * t), n=10)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rnd.uniform(-0.4, 0.4)
        branch(trunk_top, V((math.cos(a), math.sin(a), 1.1)), height * 0.45, 0.16, 2)
    trunk_o = util.mesh_object("PlumTrunk", bm_t, m["plum_bark"])
    fol = util.mesh_object("PlumBlossoms", bm_f, m["blossom"])
    util.box_uv(fol, 1.0)
    col = util.collider("TrunkCol", (0.6, 0.6, height * 0.5), (0.1, 0, height * 0.25))
    return [trunk_o, fol, col]


def bamboo_cluster(seed=5, count=9):
    rnd = random.Random(seed)
    m = mats()
    bm_s, bm_l = bmesh.new(), bmesh.new()
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 1.2)
        base = V((math.cos(a) * r, math.sin(a) * r, 0))
        h = rnd.uniform(5.5, 8.0)
        lean = V((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0))
        pts = [base, base + V((0, 0, h * 0.5)) + lean * 0.3, base + V((0, 0, h)) + lean]
        path = util.catmull(pts, 8)
        rad = rnd.uniform(0.045, 0.07)
        util.tube(bm_s, path, rad, n=8, uv_scale=(1, 0.3))
        for k in range(3, len(path) - 1, 2):
            util.cylinder(bm_s, rad * 1.18, rad * 1.18, 0.04, loc=path[k], segs=8)
        for k in range(len(path) // 2, len(path), 2):
            p = path[k]
            for j in range(2):
                ang = rnd.uniform(0, 2 * math.pi)
                d = V((math.cos(ang), math.sin(ang), -0.4))
                blob(bm_l, p + d * 0.45, (0.55, 0.35, 0.12), 0.3, 2.0, rnd.random() * 50, 1)
    s = util.mesh_object("BambooStalks", bm_s, m["bamboo"])
    lv = util.mesh_object("BambooLeaves", bm_l, m["bamboo_leaf"])
    util.box_uv(lv, 1.0)
    col = util.collider("BambooCol", (2.2, 2.2, 3.0), (0, 0, 1.5))
    return [s, lv, col]


# --------------------------------------------------------------------------
# rocks
# --------------------------------------------------------------------------
def boulders(seed=7):
    rnd = random.Random(seed)
    m = mats()
    bm = bmesh.new()
    specs = [((0, 0, 0.5), (1.4, 1.1, 0.9)), ((1.4, 0.5, 0.3), (0.8, 0.7, 0.55)),
             ((-1.1, 0.6, 0.25), (0.7, 0.6, 0.45)), ((0.4, -1.0, 0.15), (0.45, 0.4, 0.3))]
    for i, (loc, size) in enumerate(specs):
        blob(bm, loc, size, 0.35, 1.3, seed * 3 + i, 3)
    o = util.mesh_object("Boulders", bm, m["rock"])
    util.box_uv(o, 0.6)
    return [o, util.collider("RockCol", (2.8, 2.2, 1.4), (0, 0, 0.7))]


def scholar_rock(seed=11):
    """Tall eroded Taihu rock on a low plinth."""
    m = mats()
    bm = bmesh.new()
    res = bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    for v in bm.verts:
        c = v.co
        d = noise.fractal(c * 1.8 + V((seed, 0, 0)), 0.8, 2.2, 5)
        holes = noise.noise(c * 3.2 + V((0, seed, 0)))
        r = 1 + 0.45 * d - 0.35 * max(0.0, holes)
        twist = math.sin(c.z * 2.5) * 0.25
        v.co = V((c.x * r * 0.55 + twist, c.y * r * 0.4, (c.z * r + 1.0) * 1.35))
    o = util.mesh_object("ScholarRock", bm, m["taihu"])
    util.box_uv(o, 0.8)
    bm = bmesh.new()
    util.cylinder(bm, 0.9, 1.0, 0.3, loc=(0, 0, 0.15), segs=8)
    p = util.mesh_object("RockPlinth", bm, util.material("granite", tex.stone("#b3aea5", 512)), smooth=False)
    util.box_uv(p, 0.8)
    return [o, p, util.collider("RockCol", (1.6, 1.4, 2.8), (0, 0, 1.4))]


# --------------------------------------------------------------------------
# landscape
# --------------------------------------------------------------------------
PLATEAU = dict(hx=60.0, hy=76.0)
POND = dict(x=18.0, y=-2.0, rx=7.0, ry=6.0, depth=1.3)


def ground_height(x, y):
    hx, hy = PLATEAU["hx"], PLATEAU["hy"]
    # rounded-rectangle distance outside the plateau
    edge = 9.0 * noise.fractal(V((x * 0.018, y * 0.018, 7.0)), 0.7, 2.0, 3)
    dx = max(abs(x) - hx - edge, 0.0)
    dy = max(abs(y) - hy - edge, 0.0)
    out = math.hypot(dx, dy) + max(0.0, -edge) * 0.0
    n = noise.fractal(V((x * 0.03, y * 0.03, 0.0)), 0.8, 2.0, 5)
    z = 0.0
    inner = math.hypot(max(abs(x) - 44.0, 0), max(abs(y) - 70.0, 0))
    z += 0.6 * n * min(1.0, inner / 10.0)
    if out > 0:
        z -= 70.0 * (1 - math.exp(-out / 18.0)) + out * 0.5
        z += n * 6.0 * min(1.0, out / 6.0)
    # pond depression
    px = (x - POND["x"]) / POND["rx"]
    py = (y - POND["y"]) / POND["ry"]
    pr = math.hypot(px, py)
    if pr < 1.25:
        k = max(0.0, min(1.0, (1.25 - pr) / 0.45))
        z -= POND["depth"] * (k * k * (3 - 2 * k))
    return z


def terrain():
    """Mountain-top plateau: grassy top, cliffs falling into the sea of clouds."""
    m = mats()
    span_x, span_y = 112.0, 128.0
    step = 2.0
    nx, ny = int(span_x * 2 / step), int(span_y * 2 / step)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -span_x + i * step
            y = -span_y + j * step
            row.append(bm.verts.new(V((x, y, ground_height(x, y)))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.normal_update()
            steep = f.normal.z < 0.8
            f.material_index = 1 if steep else 0
            for loop in f.loops:
                co = loop.vert.co
                if steep:
                    loop[uv].uv = ((co.x + co.y) * 0.05, co.z * 0.05)
                else:
                    loop[uv].uv = (co.x * 0.15, co.y * 0.15)
    ground = util.mesh_object("Ground-col", bm, [m["grass"], m["cliff"]])
    # paved plaza, processional way and hall forecourt
    bm = bmesh.new()
    # (Blender XY; Godot z = -y): processional way, central plaza, hall forecourt,
    # path to the west moon gate and paths to both ends of the pond bridge
    rects = [(-3.5, -68, 3.5, -30), (-10, -30, 10, 12), (-12, 12, 12, 30), (-42, 3, -10, 9),
             (10, -13.5, 19.5, -10.5), (10, 6.5, 19.5, 9.5)]
    uv = bm.loops.layers.uv.verify()
    for (x0, y0, x1, y1) in rects:
        cols = max(1, int((x1 - x0) / 2))
        rows = max(1, int((y1 - y0) / 2))
        vs = [[bm.verts.new(V((x0 + (x1 - x0) * i / cols, y0 + (y1 - y0) * j / rows, 0.0)))
               for i in range(cols + 1)] for j in range(rows + 1)]
        for j in range(rows):
            for i in range(cols):
                f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
                for loop in f.loops:
                    loop[uv].uv = (loop.vert.co.x * 0.25, loop.vert.co.y * 0.25)
        # lift to terrain + a little
        for row in vs:
            for v in row:
                v.co.z = max(ground_height(v.co.x, v.co.y), 0.0) + 0.04
    # curbs
    plaza = util.mesh_object("Plaza", bm, m["paving"], smooth=False)
    # pond water
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    n = 48
    c = bm.verts.new(V((POND["x"], POND["y"], -0.45)))
    ring = [bm.verts.new(V((POND["x"] + POND["rx"] * 1.2 * math.cos(2 * math.pi * k / n),
                            POND["y"] + POND["ry"] * 1.2 * math.sin(2 * math.pi * k / n), -0.45)))
            for k in range(n)]
    for k in range(n):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x * 0.1, loop.vert.co.y * 0.1)
    water = util.mesh_object("PondWater", bm, m["water"], smooth=False)
    # pond rim stones
    bm = bmesh.new()
    rnd = random.Random(4)
    for k in range(40):
        a = 2 * math.pi * k / 40 + rnd.uniform(-0.05, 0.05)
        x = POND["x"] + POND["rx"] * 1.08 * math.cos(a)
        y = POND["y"] + POND["ry"] * 1.08 * math.sin(a)
        s = rnd.uniform(0.35, 0.7)
        blob(bm, (x, y, ground_height(x, y) + 0.05), (s * 1.3, s, s * 0.6), 0.3, 1.5, k, 1)
    rim = util.mesh_object("PondRim", bm, m["rock"])
    util.box_uv(rim, 0.8)
    return [ground, plaza, water, rim]


def floating_island(seed=21, radius=14.0):
    """Floating mountain islet: inverted rocky cone with a grassy top."""
    rnd = random.Random(seed)
    m = mats()
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rings = []
    prof = [(1.0, 0.0), (1.02, -0.6), (0.9, -2.5), (0.75, -5.5), (0.55, -9.0), (0.35, -13.0),
            (0.18, -17.0), (0.06, -21.0), (0.01, -23.0)]
    seg = 40
    for (rr, z) in prof:
        row = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            d = noise.fractal(V((math.cos(a) * 2, math.sin(a) * 2, z * 0.15 + seed)), 0.8, 2.0, 4)
            r = radius * rr * (1 + 0.28 * d)
            row.append(V((math.cos(a) * r, math.sin(a) * r, z * radius / 14.0 * 1.3 + d * 1.5 * (z < -0.5))))
        rings.append(row)
    rows = util.loft(bm, rings, closed=True, cap_start=False, cap_end=False, uv_scale=(6.0, 0.08))
    # top cap
    top = rows[0]
    cen = bm.verts.new(V((0, 0, 0.6)))
    uvl = bm.loops.layers.uv.active
    for k in range(seg):
        f = bm.faces.new((cen, top[(k + 1) % seg], top[k]))
        f.material_index = 1
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.x * 0.15, loop.vert.co.y * 0.15)
    o = util.mesh_object("IslandRock", bm, [m["cliff"], m["grass"]])
    objs = [o]
    for k in range(3):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.2, 0.55) * radius
        for p in pine_tree(seed * 7 + k, rnd.uniform(5, 8)):
            if "colonly" in p.name:
                util.delete_objects([p])
                continue
            p.location = (math.cos(a) * r, math.sin(a) * r, 0.3)
            util.apply_transform(p)
            objs.append(p)
    return objs


def karst_peak(seed=31, height=90.0, radius=12.0):
    """Towering stone pillar (Zhangjiajie style) for the distant backdrop."""
    rnd = random.Random(seed)
    m = mats()
    bm = bmesh.new()
    rings = []
    seg = 28
    steps = 18
    for j in range(steps + 1):
        t = j / steps
        z = -60 + (height + 60) * t
        row = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            d = noise.fractal(V((math.cos(a) * 1.5, math.sin(a) * 1.5, t * 4 + seed)), 0.8, 2.0, 4)
            r = radius * (1.15 - 0.35 * t + 0.1 * math.sin(t * 9)) * (1 + 0.3 * d)
            if t > 0.95:
                r *= 0.8
            row.append(V((math.cos(a) * r, math.sin(a) * r, z)))
        rings.append(row)
    util.loft(bm, rings, closed=True, cap_end=True, uv_scale=(5.0, 0.012))
    o = util.mesh_object("KarstPeak", bm, m["cliff"])
    objs = [o]
    for k in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.0, 0.5) * radius * 0.7
        for p in pine_tree(seed * 5 + k, rnd.uniform(6, 10)):
            if "colonly" in p.name:
                util.delete_objects([p])
                continue
            p.location = (math.cos(a) * r, math.sin(a) * r, height - 0.5)
            util.apply_transform(p)
            objs.append(p)
    return objs


def cloud_sea(size=1400.0):
    """Huge soft cloud layer far below the plateau."""
    import numpy as np
    s = 512
    n = tex.fbm(s, 4, 6, 0.55, 99)
    n2 = tex.fbm(s, 16, 4, 0.5, 98)
    val = np.clip((n * 0.8 + n2 * 0.2 - 0.25) * 1.8, 0, 1)
    col = tex.lerp(tex.srgb("#a9b8cc"), tex.srgb("#fbfbfd"), val)
    maps = tex.result(col, 0.95, 0.0, None)
    mat = util.material("cloud_sea", maps, emission="#dde6f2", emission_strength=0.25,
                        alpha=np.clip(val * 1.4 + 0.15, 0, 1), normal_strength=0.0)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    k = 8
    vs = [[bm.verts.new(V((-size / 2 + size * i / k, -size / 2 + size * j / k, 0))) for i in range(k + 1)]
          for j in range(k + 1)]
    for j in range(k):
        for i in range(k):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for loop in f.loops:
                loop[uv].uv = (loop.vert.co.x / 180.0, loop.vert.co.y / 180.0)
    return [util.mesh_object("CloudSea", bm, mat, smooth=False)]

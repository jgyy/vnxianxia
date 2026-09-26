"""Traditional Chinese sect architecture kit and buildings.

Buildings face -Y in Blender (their front faces +Z in Godot).
"""
import math

import bmesh
from mathutils import Matrix, Vector

from . import tex, util

V = Vector
R = math.radians


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def kit():
    m = {}
    m["pillar"] = util.material("red_lacquer", tex.lacquer("#8c1d17", 512, 51, 0.2), normal_strength=0.3)
    m["wood"] = util.material("dark_wood", tex.wood("#4b2f1f", 512), normal_strength=0.5)
    m["beam"] = util.material("painted_beam", tex.beam_paint(512), normal_strength=0.4)
    m["plaster"] = util.material("plaster", tex.plaster("#ebe6da", 512), normal_strength=0.3)
    m["brick"] = util.material("grey_brick", tex.bricks("#77746e", 512), normal_strength=0.8)
    m["stone"] = util.material("granite", tex.stone("#b3aea5", 512), normal_strength=0.6)
    m["marble"] = util.material("white_marble", tex.stone("#e4e1da", 512, 72, 0.15), normal_strength=0.3)
    m["tiles"] = util.material("roof_tiles", tex.roof_tiles("#2e3d47", 512), normal_strength=1.0)
    m["ridge"] = util.material("ridge_tiles", tex.stone("#2a3238", 256, 73, 0.1), normal_strength=0.4)
    m["gold"] = util.material("gold", tex.metal("#d4a93c", rough=0.3))
    m["lattice"] = util.material("lattice", tex.lattice("#6b2016", "#efe2c4", 512), normal_strength=0.6,
                                 emission="#ffcf8a", emission_strength=0.15)
    m["plaque"] = util.material("plaque", tex.plaque(512), normal_strength=0.5)
    return m


# --------------------------------------------------------------------------
# roofs
# --------------------------------------------------------------------------
def roof(name, corners, target, h, mats, base_z=0.0, t_max=0.97, curve=1.9, lift=0.55,
         lift_len=2.2, flare=0.35, per_edge=24, rows=14, thick=0.16, ridges=True,
         ornaments=True, detail=1.0):
    """Curved Chinese roof with upturned 'flying' corners.

    corners: eave footprint polygon (counter-clockwise, 2D).
    target : callable 2D point -> 2D point the slope climbs toward (ridge/apex).
    """
    corners = [V((c[0], c[1])) for c in corners]
    n = len(corners)
    perim = []  # (point, outward normal, corner weight, perimeter length)
    L = 0.0
    for i in range(n):
        a, b = corners[i], corners[(i + 1) % n]
        e = b - a
        el = e.length
        for k in range(per_edge):
            f = k / per_edge
            p = a + e * f
            dist = min(f, 1 - f) * el
            cw = max(0.0, 1 - dist / lift_len) ** 2
            # corner outward direction = bisector, else edge normal
            en = V((e.y, -e.x)).normalized()
            if f < 0.5:
                prev = corners[i] - corners[i - 1]
                bis = (en + V((prev.y, -prev.x)).normalized()).normalized()
            else:
                nxt = corners[(i + 2) % n] - corners[(i + 1) % n]
                bis = (en + V((nxt.y, -nxt.x)).normalized()).normalized()
            out = en.lerp(bis, cw).normalized()
            perim.append((p, out, cw, L + f * el))
        L += el

    def point(i, t):
        p, out, cw, _ = perim[i % len(perim)]
        tp = V(target(p))
        q = p.lerp(tp, t)
        k = (1 - t / t_max) ** 2 if t < t_max else 0.0
        q += out * cw * k * flare * lift
        z = base_z + h * (t / t_max) ** curve + lift * cw * k
        return V((q.x, q.y, z))

    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    grid = [[bm.verts.new(point(i, t_max * j / rows)) for i in range(len(perim))] for j in range(rows + 1)]
    slope = (V(target(perim[0][0])) - perim[0][0]).length
    for j in range(rows):
        for i in range(len(perim)):
            i2 = (i + 1) % len(perim)
            f = bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
            l1 = perim[i][3]
            l2 = perim[i][3] + (perim[i2][0] - perim[i][0]).length
            for loop, (uu, vv) in zip(f.loops, ((l1, j), (l2, j), (l2, j + 1), (l1, j + 1))):
                loop[uv].uv = (uu * 0.6, vv / rows * (slope + h) * 0.5)
    obj = util.mesh_object(name, bm, [mats["tiles"], mats["wood"]])
    mod = obj.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thick
    mod.offset = -1
    mod.material_offset = 1
    mod.material_offset_rim = 1
    util.apply_modifiers(obj)
    parts = [obj]
    if ridges:
        bm = bmesh.new()
        idx = [i * per_edge for i in range(n)]
        for i in idx:
            path = [point(i, t_max * j / rows) + V((0, 0, 0.09 * detail)) for j in range(0, rows + 1)]
            util.tube(bm, path, (0.09 * detail, 0.07 * detail), n=8, power=3.0, closed_ends=True)
        top = [point(i, t_max) for i in range(len(perim))]
        # ridge along the top edge (degenerates to a point for pyramids)
        xs = [p for p in top]
        a = min(xs, key=lambda p: (p.x, p.y))
        b = max(xs, key=lambda p: (p.x, p.y))
        if (b - a).length > 0.3:
            ra = a + V((0, 0, 0.12 * detail))
            rb = b + V((0, 0, 0.12 * detail))
            util.tube(bm, [ra, rb], (0.16 * detail, 0.13 * detail), n=8, power=4.0)
            if ornaments:
                for end, sgn in ((ra, -1), (rb, 1)):
                    curl = []
                    for k in range(24):
                        tt = k / 23
                        ang = tt * R(260)
                        rr = 0.45 * detail * (1 - 0.6 * tt)
                        curl.append(end + V((sgn * (0.1 * detail - rr * math.sin(ang)), 0, 0.1 * detail + rr * (1 - math.cos(ang)))))
                    util.tube(bm, curl, lambda t: 0.13 * detail * (1 - 0.6 * t), n=8)
        o = util.mesh_object(name + "Ridges", bm, mats["ridge"])
        util.box_uv(o, 1.0)
        parts.append(o)
        if ornaments:
            bm = bmesh.new()
            for i in idx:
                p0 = point(i, 0.0) + V((0, 0, 0.12 * detail))
                _, out, _, _ = perim[i]
                tip = p0 + V((out.x, out.y, 1.0)) * 0.25 * detail
                util.tube(bm, [p0, p0 + V((out.x * 0.12, out.y * 0.12, 0.05)) * detail, tip],
                          lambda t: 0.07 * detail * (1 - 0.7 * t), n=8)
                util.sphere(bm, 0.07 * detail, loc=tip, segs=10, rings=6)
            if (b - a).length <= 0.3:
                apex = top[0] + V((0, 0, 0.05 * detail))
                util.lathe(bm, [(r * detail, z * detail) for r, z in ((0.2, 0), (0.24, 0.15), (0.1, 0.3), (0.16, 0.5), (0.05, 0.75), (0.001, 0.9))],
                           segs=12, loc=apex, cap_bottom=True)
            o = util.mesh_object(name + "Ornaments", bm, mats["gold"])
            util.box_uv(o, 2.0)
            parts.append(o)
    return parts


def rect_roof(name, cx, cy, hw, hd, h, mats, base_z, **kw):
    """Hip roof over a rectangle: ridge along X."""
    ridge = max(hw - hd, 0.0)

    def target(p):
        return (max(-ridge, min(ridge, p.x - cx)) + cx, cy)
    corners = [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)]
    return roof(name, corners, target, h, mats, base_z=base_z, **kw)


def poly_roof(name, cx, cy, radius, sides, h, mats, base_z, rot=0.0, **kw):
    corners = [(cx + radius * math.cos(rot + 2 * math.pi * i / sides),
                cy + radius * math.sin(rot + 2 * math.pi * i / sides)) for i in range(sides)]
    return roof(name, corners, lambda p: (cx, cy), h, mats, base_z=base_z, **kw)


# --------------------------------------------------------------------------
# structural pieces
# --------------------------------------------------------------------------
def column(bm_p, bm_s, x, y, z0, height, r=0.26):
    util.cylinder(bm_p, r, r * 0.92, height, loc=(x, y, z0 + height / 2), segs=16)
    util.lathe(bm_s, [(r * 1.55, 0.0), (r * 1.55, 0.08), (r * 1.35, 0.22), (r * 1.05, 0.3)],
               segs=16, loc=(x, y, z0 - 0.02), cap_top=True, cap_bottom=True)


def dougong(bm, x, y, z, s=1.0, out=V((0, -1, 0))):
    """Simplified bracket set: stacked blocks and crossing arms."""
    util.box(bm, (0.42 * s, 0.42 * s, 0.16 * s), loc=(x, y, z + 0.08 * s))
    util.box(bm, (1.2 * s, 0.18 * s, 0.14 * s), loc=(x, y, z + 0.23 * s))
    util.box(bm, (0.18 * s, 1.0 * s, 0.14 * s), loc=(x, y, z + 0.23 * s))
    for dx in (-0.5, 0, 0.5):
        util.box(bm, (0.2 * s, 0.2 * s, 0.12 * s), loc=(x + dx * s, y, z + 0.36 * s))
    util.box(bm, (1.6 * s, 0.2 * s, 0.14 * s), loc=(x, y, z + 0.49 * s))
    util.box(bm, (0.2 * s, 1.4 * s, 0.14 * s), loc=(x, y, z + 0.49 * s))


def platform(name, hw, hd, h, mats, stairs_w=4.0, stairs_side=True, rails=True):
    """Stone terrace with front stairs and marble balustrade. Top at z = h."""
    objs = []
    bm = bmesh.new()
    util.box(bm, (hw * 2, hd * 2, h), loc=(0, 0, h / 2))
    util.box(bm, (hw * 2 + 0.3, hd * 2 + 0.3, 0.2), loc=(0, 0, 0.1))
    o = util.mesh_object(name + "Base", bm, mats["brick"], smooth=False)
    util.box_uv(o, 0.5)
    objs.append(o)
    bm = bmesh.new()
    util.box(bm, (hw * 2 + 0.2, hd * 2 + 0.2, 0.15), loc=(0, 0, h + 0.075 - 0.15))
    steps = max(3, int(round(h / 0.18)))
    run = 0.34
    for k in range(steps):
        sh = h * (k + 1) / steps
        depth = run * (steps - k)
        util.box(bm, (stairs_w, depth, sh), loc=(0, -hd - depth / 2, sh / 2))
    o = util.mesh_object(name + "Stairs", bm, mats["stone"], smooth=False)
    util.box_uv(o, 0.6)
    objs.append(o)
    # stair cheek walls
    bm = bmesh.new()
    total = run * steps
    for sx in (-1, 1):
        x = sx * (stairs_w / 2 + 0.2)
        verts = [V((x - 0.2, -hd, 0)), V((x + 0.2, -hd, 0)), V((x + 0.2, -hd - total, 0)),
                 V((x - 0.2, -hd - total, 0)), V((x - 0.2, -hd, h + 0.1)), V((x + 0.2, -hd, h + 0.1)),
                 V((x + 0.2, -hd - total, 0.25)), V((x - 0.2, -hd - total, 0.25))]
        vs = [bm.verts.new(v) for v in verts]
        for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[i] for i in f])
    # central carved dragon ramp (imperial way)
    if stairs_w >= 3.5:
        ramp = [V((-0.7, -hd, h)), V((0.7, -hd, h)), V((0.7, -hd - total, 0.02)), V((-0.7, -hd - total, 0.02))]
        vs = [bm.verts.new(v + V((0, 0, 0.03))) for v in ramp]
        bm.faces.new(vs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = util.mesh_object(name + "Cheeks", bm, mats["marble"], smooth=False)
    util.box_uv(o, 0.8)
    objs.append(o)
    if rails:
        bm = bmesh.new()
        z = h
        path_pts = []
        gap = stairs_w / 2 + 0.4
        segs = [((-hw, -hd), (-gap, -hd)), ((gap, -hd), (hw, -hd)), ((hw, -hd), (hw, hd)),
                ((hw, hd), (-hw, hd)), ((-hw, hd), (-hw, -hd))]
        for (a, b) in segs:
            a, b = V((a[0], a[1], z)), V((b[0], b[1], z))
            ln = (b - a).length
            cnt = max(1, int(ln / 1.6))
            for k in range(cnt + 1):
                p = a.lerp(b, k / cnt)
                util.box(bm, (0.18, 0.18, 0.95), loc=(p.x, p.y, z + 0.475))
                util.sphere(bm, 0.11, loc=(p.x, p.y, z + 1.02), segs=8, rings=6)
            mid = (a + b) / 2
            d = b - a
            if abs(d.x) > abs(d.y):
                util.box(bm, (ln, 0.12, 0.1), loc=(mid.x, mid.y, z + 0.85))
                util.box(bm, (ln, 0.08, 0.45), loc=(mid.x, mid.y, z + 0.4))
            else:
                util.box(bm, (0.12, ln, 0.1), loc=(mid.x, mid.y, z + 0.85))
                util.box(bm, (0.08, ln, 0.45), loc=(mid.x, mid.y, z + 0.4))
        o = util.mesh_object(name + "Balustrade", bm, mats["marble"], smooth=False)
        util.box_uv(o, 1.0)
        objs.append(o)
    # collision: terrace block + walkable stair ramp
    objs.append(util.collider(name + "TerraceCol", (hw * 2, hd * 2, h), (0, 0, h / 2)))
    ang = math.atan2(h, total)
    ln = math.hypot(h, total)
    c = util.collider(name + "StairCol", (stairs_w + 0.8, ln, 0.2), (0, 0, 0))
    c.rotation_euler = (ang, 0, 0)
    c.location = (0, -hd - total / 2, h / 2 - 0.1)
    util.apply_transform(c)
    objs.append(c)
    return objs


def plaque_board(mats, loc, w=2.4, h=0.9, tilt=12):
    bm = bmesh.new()
    util.box(bm, (w + 0.2, 0.12, h + 0.2), loc=(0, 0.02, 0))
    o_frame = util.mesh_object("PlaqueFrame", bm, mats["gold"], smooth=False)
    util.box_uv(o_frame, 1.0)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(V((x * w / 2, -0.05, z * h / 2))) for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for loop, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = (uu, vv)
    o_face = util.mesh_object("Plaque", bm, mats["plaque"], smooth=False)
    objs = [o_frame, o_face]
    for o in objs:
        o.rotation_euler = (R(-tilt), 0, 0)
        o.location = loc
        util.apply_transform(o)
    return objs


# --------------------------------------------------------------------------
# buildings
# --------------------------------------------------------------------------
def main_hall():
    """Grand hall on a terrace with a double-eave hip roof."""
    mats = kit()
    objs = []
    th = 1.3  # terrace height
    hw, hd = 9.0, 6.5
    objs += platform("Hall", hw, hd, th, mats, stairs_w=5.0)
    xs = [-6.0, -3.6, -1.2, 1.2, 3.6, 6.0]
    ys = [-3.6, 0.0, 3.6]
    ch = 4.6
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for x in xs:
        for y in ys:
            column(bm_p, bm_s, x, y, th, ch)
    # veranda columns in front
    for x in xs:
        column(bm_p, bm_s, x, -5.0, th, ch, r=0.24)
    o = util.mesh_object("Columns", bm_p, mats["pillar"])
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("ColumnBases", bm_s, mats["stone"])
    util.box_uv(o, 1.0)
    objs.append(o)
    # walls: back and sides plaster, front lattice doors, brick dado
    bm_w, bm_d, bm_l = bmesh.new(), bmesh.new(), bmesh.new()
    wz = th + ch / 2
    util.box(bm_w, (12.0, 0.3, ch), loc=(0, 3.6, wz))
    util.box(bm_w, (0.3, 7.2, ch), loc=(-6.0, 0, wz))
    util.box(bm_w, (0.3, 7.2, ch), loc=(6.0, 0, wz))
    util.box(bm_d, (12.1, 0.34, 0.9), loc=(0, 3.6, th + 0.45))
    util.box(bm_d, (0.34, 7.3, 0.9), loc=(-6.0, 0, th + 0.45))
    util.box(bm_d, (0.34, 7.3, 0.9), loc=(6.0, 0, th + 0.45))
    o = util.mesh_object("Walls", bm_w, mats["plaster"], smooth=False)
    util.box_uv(o, 0.35)
    objs.append(o)
    # front lattice panels (five bays), UV mapped per panel
    uv = bm_l.loops.layers.uv.verify()
    for i in range(5):
        x0, x1 = xs[i] + 0.3, xs[i + 1] - 0.3
        z0, z1 = th + (0.1 if 1 <= i <= 3 else 1.0), th + ch - 0.6
        vs = [bm_l.verts.new(V((x, -3.6, z))) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
        f = bm_l.faces.new(vs)
        cols = 4 if 1 <= i <= 3 else 2
        for loop, (uu, vv) in zip(f.loops, ((0, 0), (cols, 0), (cols, 1), (0, 1))):
            loop[uv].uv = (uu, vv)
        if not (1 <= i <= 3):
            util.box(bm_d, (x1 - x0, 0.3, 0.9), loc=((x0 + x1) / 2, -3.6, th + 0.45))
    o = util.mesh_object("LatticeDoors", bm_l, mats["lattice"], smooth=False)
    objs.append(o)
    o = util.mesh_object("Dado", bm_d, mats["brick"], smooth=False)
    util.box_uv(o, 0.5)
    objs.append(o)
    bm = bmesh.new()
    for i in range(5):
        x0, x1 = xs[i] + 0.3, xs[i + 1] - 0.3
        for x in [x0 + (x1 - x0) * k / 4 for k in range(5)] if 1 <= i <= 3 else [x0, x1]:
            util.box(bm, (0.1, 0.12, ch - 0.6), loc=(x, -3.62, th + (ch - 0.6) / 2))
        util.box(bm, (x1 - x0, 0.12, 0.14), loc=((x0 + x1) / 2, -3.62, th + ch - 0.6))
    o = util.mesh_object("DoorFrames", bm, mats["pillar"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    # painted beams + brackets
    bm = bmesh.new()
    top = th + ch
    for y in (-5.0, -3.6, 3.6):
        util.box(bm, (12.8, 0.34, 0.5), loc=(0, y, top + 0.1))
    for x in (-6.0, 6.0):
        util.box(bm, (0.34, 8.8, 0.5), loc=(x, -0.7, top + 0.1))
    o = util.mesh_object("Beams", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    bm = bmesh.new()
    for x in xs:
        dougong(bm, x, -5.0, top + 0.35, 0.8)
        dougong(bm, x, 3.6, top + 0.35, 0.8)
    for y in ys:
        dougong(bm, -6.0, y, top + 0.35, 0.8)
        dougong(bm, 6.0, y, top + 0.35, 0.8)
    o = util.mesh_object("Brackets", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.5)
    objs.append(o)
    # lower eave and upper roof
    z1 = top + 0.85
    objs += roof("LowerEave", [(-8.4, -7.0), (8.4, -7.0), (8.4, 5.6), (-8.4, 5.6)],
                 lambda p: (max(-5.0, min(5.0, p.x)), -0.7), 5.0, mats, base_z=z1, t_max=0.34,
                 curve=1.4, lift=0.7, lift_len=2.5, ornaments=True, ridges=False)
    bm = bmesh.new()
    util.box(bm, (11.0, 7.6, 1.6), loc=(0, -0.7, z1 + 1.7 + 0.8))
    o = util.mesh_object("UpperStorey", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    bm = bmesh.new()
    for x in [-5.5 + k * 1.1 for k in range(11)]:
        dougong(bm, x, -4.5, z1 + 3.2, 0.6)
    o = util.mesh_object("UpperBrackets", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.5)
    objs.append(o)
    objs += rect_roof("UpperRoof", 0, -0.7, 7.6, 5.4, 4.2, mats, base_z=z1 + 3.4, curve=1.9, lift=0.8,
                      lift_len=3.0, flare=0.4)
    objs += plaque_board(mats, (0, -4.55, z1 + 2.5), w=2.6, h=1.0)
    # collision for the hall body
    objs.append(util.collider("HallBody", (12.4, 7.6, ch), (0, 0, th + ch / 2)))
    for x in xs:
        objs.append(util.collider("Pillar", (0.5, 0.5, ch), (x, -5.0, th + ch / 2)))
    return objs


def sect_gate():
    """Three-bay paifang archway with tiled roofs and a name plaque."""
    mats = kit()
    objs = []
    xs = [-4.2, -1.6, 1.6, 4.2]
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for i, x in enumerate(xs):
        h = 7.0 if i in (1, 2) else 5.4
        column(bm_p, bm_s, x, 0, 0.0, h, r=0.3)
        # stone drum braces
        util.box(bm_s, (0.9, 1.6, 1.1), loc=(x, 0, 0.55))
    o = util.mesh_object("GatePillars", bm_p, mats["pillar"])
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("GateBases", bm_s, mats["stone"], smooth=False)
    util.box_uv(o, 0.8)
    objs.append(o)
    bm = bmesh.new()
    util.box(bm, (3.6, 0.45, 0.6), loc=(0, 0, 6.3))
    util.box(bm, (3.6, 0.4, 0.4), loc=(0, 0, 5.0))
    for sx in (-1, 1):
        util.box(bm, (2.9, 0.4, 0.5), loc=(sx * 2.9, 0, 4.9))
        util.box(bm, (2.9, 0.35, 0.35), loc=(sx * 2.9, 0, 3.9))
    o = util.mesh_object("GateBeams", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    bm = bmesh.new()
    for x in [-1.2 + k * 0.6 for k in range(5)]:
        dougong(bm, x, 0, 6.6, 0.5)
    for sx in (-1, 1):
        for x in [sx * (2.9 + d) for d in (-0.9, 0, 0.9)]:
            dougong(bm, x, 0, 5.15, 0.45)
    o = util.mesh_object("GateBrackets", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.5)
    objs.append(o)
    objs += rect_roof("GateRoofMain", 0, 0, 2.6, 1.2, 1.4, mats, base_z=7.05, lift=0.45, lift_len=1.1,
                      curve=1.7, flare=0.4)
    for sx in (-1, 1):
        objs += rect_roof(f"GateRoofSide{'L' if sx > 0 else 'R'}", sx * 2.95, 0, 1.9, 1.0, 1.1, mats,
                          base_z=5.55, lift=0.4, lift_len=0.9, curve=1.7, flare=0.4)
    objs += plaque_board(mats, (0, -0.3, 5.65), w=2.2, h=0.9, tilt=0)
    for x in xs:
        objs.append(util.collider("GatePillar", (0.9, 1.6, 7.0), (x, 0, 3.5)))
    return objs


def pavilion():
    """Hexagonal pavilion (ting) with benches and a pointed roof."""
    mats = kit()
    objs = []
    r = 2.6
    bm = bmesh.new()
    util.cylinder(bm, r + 0.5, r + 0.5, 0.5, loc=(0, 0, 0.25), segs=6)
    for k in range(3):
        util.box(bm, (1.6, 0.35, 0.17 * (k + 1)), loc=(0, -(r + 0.5) - 0.35 * (3 - k) + 0.17, 0.085 * (k + 1)))
    o = util.mesh_object("PavilionBase", bm, mats["stone"], smooth=False)
    util.box_uv(o, 0.8)
    objs.append(o)
    bm_p, bm_s = bmesh.new(), bmesh.new()
    pts = [(r * math.cos(R(60 * i + 30)), r * math.sin(R(60 * i + 30))) for i in range(6)]
    for (x, y) in pts:
        column(bm_p, bm_s, x, y, 0.5, 3.2, r=0.17)
    o = util.mesh_object("PavilionPillars", bm_p, mats["pillar"])
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("PavilionPillarBases", bm_s, mats["stone"])
    util.box_uv(o, 1.0)
    objs.append(o)
    bm = bmesh.new()
    bm_b = bmesh.new()
    for i in range(6):
        a, b = V((*pts[i], 0)), V((*pts[(i + 1) % 6], 0))
        mid = (a + b) / 2
        d = b - a
        ang = math.atan2(d.y, d.x)
        rot = Matrix.Rotation(ang, 4, "Z")
        util.box(bm, (d.length, 0.22, 0.35), loc=(mid.x, mid.y, 3.6), rot=rot)
        if i != 4:  # leave the entrance (front, facing -Y) open
            util.box(bm_b, (d.length - 0.3, 0.45, 0.08), loc=(mid.x * 0.97, mid.y * 0.97, 0.95), rot=rot)
            util.box(bm_b, (d.length - 0.3, 0.06, 0.06), loc=(mid.x * 1.03, mid.y * 1.03, 1.45), rot=rot)
            for k in (-0.35, 0.0, 0.35):
                p = mid + d * k * 0.9
                util.box(bm_b, (0.06, 0.06, 0.5), loc=(p.x * 1.03, p.y * 1.03, 1.2), rot=rot)
            util.box(bm_b, (d.length - 0.3, 0.3, 0.45), loc=(mid.x * 0.97, mid.y * 0.97, 0.72), rot=rot)
    o = util.mesh_object("PavilionBeams", bm, mats["beam"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("PavilionBenches", bm_b, mats["wood"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    # stone table + stools
    bm = bmesh.new()
    util.lathe(bm, [(0.25, 0), (0.18, 0.3), (0.2, 0.6), (0.55, 0.68), (0.55, 0.78), (0.001, 0.78)],
               segs=20, loc=(0, 0, 0.5), cap_bottom=True)
    for k in range(4):
        a = R(45 + 90 * k)
        util.lathe(bm, [(0.2, 0), (0.14, 0.2), (0.2, 0.42), (0.001, 0.44)], segs=12,
                   loc=(math.cos(a) * 0.95, math.sin(a) * 0.95, 0.5), cap_bottom=True)
    o = util.mesh_object("StoneTable", bm, mats["marble"])
    util.box_uv(o, 1.0)
    objs.append(o)
    objs += poly_roof("PavilionRoof", 0, 0, r + 1.1, 6, 2.8, mats, base_z=3.8, rot=R(30), lift=0.55,
                      lift_len=1.3, curve=1.8, per_edge=12, rows=12)
    objs.append(util.collider("PavilionBase", (2 * (r + 0.5), 2 * (r + 0.5) * 0.87, 0.5), (0, 0, 0.25)))
    for (x, y) in pts:
        objs.append(util.collider("PavilionPillar", (0.34, 0.34, 3.2), (x, y, 2.1)))
    return objs


def pagoda(tiers=7):
    """Tall square pagoda with stacked eaves and a golden spire."""
    mats = kit()
    objs = []
    bm = bmesh.new()
    util.box(bm, (7.0, 7.0, 0.8), loc=(0, 0, 0.4))
    util.box(bm, (2.4, 1.2, 0.4), loc=(0, -4.0, 0.2))
    o = util.mesh_object("PagodaBase", bm, mats["stone"], smooth=False)
    util.box_uv(o, 0.6)
    objs.append(o)
    z = 0.8
    w = 2.6
    bm_w, bm_p, bm_s, bm_b, bm_l = (bmesh.new() for _ in range(5))
    uv = bm_l.loops.layers.uv.verify()
    for t in range(tiers):
        h = 3.2 if t == 0 else 2.2 - 0.08 * t
        util.box(bm_w, (w * 2 - 0.3, w * 2 - 0.3, h), loc=(0, 0, z + h / 2))
        for sx in (-1, 1):
            for sy in (-1, 1):
                column(bm_p, bm_s, sx * (w - 0.1), sy * (w - 0.1), z, h, r=0.16)
        util.box(bm_b, (w * 2 + 0.2, w * 2 + 0.2, 0.3), loc=(0, 0, z + h + 0.1))
        # door/window panel on each face
        for k in range(4):
            ang = R(90 * k)
            rot = Matrix.Rotation(ang, 3, "Z")
            pw, ph = w * 0.7, h * 0.65
            corners = [V((-pw / 2, -w + 0.14, z + 0.2)), V((pw / 2, -w + 0.14, z + 0.2)),
                       V((pw / 2, -w + 0.14, z + 0.2 + ph)), V((-pw / 2, -w + 0.14, z + 0.2 + ph))]
            vs = [bm_l.verts.new(rot @ c) for c in corners]
            f = bm_l.faces.new(vs)
            for loop, (uu, vv) in zip(f.loops, ((0, 0), (2, 0), (2, 1), (0, 1))):
                loop[uv].uv = (uu, vv)
        rz = z + h + 0.25
        objs += poly_roof(f"PagodaEave{t}", 0, 0, (w + 1.2) * math.sqrt(2), 4, 2.4, mats, base_z=rz,
                          rot=R(45), t_max=0.33, lift=0.5, lift_len=1.2, curve=1.3, per_edge=12, rows=5,
                          ridges=False, ornaments=True)
        z = rz + 0.55
        w *= 0.88
    for bm, name, mat, sc in ((bm_w, "PagodaWalls", mats["plaster"], 0.4), (bm_p, "PagodaPillars", mats["pillar"], 1),
                              (bm_s, "PagodaPillarBases", mats["stone"], 1), (bm_b, "PagodaBeams", mats["beam"], 1)):
        o = util.mesh_object(name, bm, mat, smooth=name == "PagodaPillars")
        util.box_uv(o, sc)
        objs.append(o)
    objs.append(util.mesh_object("PagodaWindows", bm_l, mats["lattice"], smooth=False))
    objs += poly_roof("PagodaCap", 0, 0, (w + 1.4) * math.sqrt(2), 4, 2.2, mats, base_z=z - 0.3, rot=R(45),
                      lift=0.5, lift_len=1.2, curve=1.6, per_edge=12, rows=10, ornaments=False)
    bm = bmesh.new()
    top = z + 1.8
    prof = [(0.35, 0), (0.3, 0.3)]
    for k in range(7):
        prof += [(0.32 - k * 0.03, 0.5 + k * 0.45), (0.22 - k * 0.02, 0.7 + k * 0.45)]
    prof += [(0.18, 3.8), (0.35, 4.1), (0.2, 4.4), (0.001, 4.9)]
    util.lathe(bm, prof, segs=16, loc=(0, 0, top), cap_bottom=True)
    o = util.mesh_object("PagodaSpire", bm, mats["gold"])
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(util.collider("PagodaBase", (7.0, 7.0, 0.8), (0, 0, 0.4)))
    objs.append(util.collider("PagodaBody", (5.0, 5.0, 12.0), (0, 0, 6.8)))
    return objs


def wall_segment(length=8.0, height=3.2, moon_gate=False):
    """Courtyard wall: brick plinth, white plaster, tiled coping.
    With moon_gate=True a circular opening is cut in the middle.
    """
    mats = kit()
    objs = []
    t = 0.5
    bm = bmesh.new()
    if moon_gate:
        seg = length / 2 - 1.45
        for sx in (-1, 1):
            util.box(bm, (seg, t + 0.1, 0.8), loc=(sx * (1.45 + seg / 2), 0, 0.4))
    else:
        util.box(bm, (length, t + 0.1, 0.8), loc=(0, 0, 0.4))
    o = util.mesh_object("WallPlinth", bm, mats["brick"], smooth=False)
    util.box_uv(o, 0.5)
    objs.append(o)
    bm = bmesh.new()
    if not moon_gate:
        util.box(bm, (length, t, height - 0.8), loc=(0, 0, 0.8 + (height - 0.8) / 2))
    else:
        # wall panel with a circular hole: bridge a rectangle loop to a circle loop
        rad = 1.35
        cz = 1.38
        n = 48
        for y in (-t / 2, t / 2):
            outer, inner = [], []
            for i in range(n):
                a = 2 * math.pi * i / n - math.pi / 2
                inner.append(V((rad * math.cos(a), y, cz + rad * math.sin(a))))
                # matching point on the rectangle boundary
                dx, dz = math.cos(a), math.sin(a)
                hx, hz0, hz1 = length / 2, 0.0, height - 0.0
                k = min(hx / max(abs(dx), 1e-6), ((hz1 - cz) if dz > 0 else (cz - hz0)) / max(abs(dz), 1e-6))
                outer.append(V((dx * k, y, cz + dz * k)))
            vo = [bm.verts.new(p) for p in outer]
            vi = [bm.verts.new(p) for p in inner]
            for i in range(n):
                i2 = (i + 1) % n
                f = (vo[i], vo[i2], vi[i2], vi[i])
                bm.faces.new(f if y < 0 else tuple(reversed(f)))
        # inner cylinder of the opening
        verts = list(bm.verts)
        front = [v for v in verts if v.co.y < 0]
        back = [v for v in verts if v.co.y > 0]
        fi = [v for v in front if abs((V((v.co.x, v.co.z)) - V((0, cz))).length - rad) < 1e-3]
        bi = [v for v in back if abs((V((v.co.x, v.co.z)) - V((0, cz))).length - rad) < 1e-3]
        key = lambda v: math.atan2(v.co.z - cz, v.co.x)
        fi.sort(key=key)
        bi.sort(key=key)
        for i in range(len(fi)):
            i2 = (i + 1) % len(fi)
            bm.faces.new((fi[i], fi[i2], bi[i2], bi[i]))
        # ends and top of the wall
        util.box(bm, (0.02, t, height), loc=(-length / 2, 0, height / 2))
        util.box(bm, (0.02, t, height), loc=(length / 2, 0, height / 2))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # stone ring around the gate
        bm_r = bmesh.new()
        path = [V((rad * math.cos(a), 0, cz + rad * math.sin(a))) for a in
                [2 * math.pi * k / 48 for k in range(49)]]
        util.tube(bm_r, path, (0.12, t / 2 + 0.06), n=8, power=4.0, up=(0, 1, 0), closed_ends=False)
        o = util.mesh_object("MoonGateRing", bm_r, mats["marble"])
        util.box_uv(o, 1.0)
        objs.append(o)
    o = util.mesh_object("WallBody", bm, mats["plaster"], smooth=False)
    util.box_uv(o, 0.35)
    objs.append(o)
    # coping: small gabled tile roof along the wall
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    hw = length / 2 + 0.2
    for sy in (-1, 1):
        vs = [bm.verts.new(V(p)) for p in ((-hw, 0, height + 0.45), (hw, 0, height + 0.45),
                                           (hw, sy * 0.65, height + 0.05), (-hw, sy * 0.65, height + 0.05))]
        f = bm.faces.new(vs if sy > 0 else list(reversed(vs)))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x * 0.6, abs(loop.vert.co.y) * 0.8)
    o = util.mesh_object("WallCoping", bm, [mats["tiles"], mats["wood"]], smooth=False)
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = 0.08
    mod.material_offset = 1
    mod.material_offset_rim = 1
    util.apply_modifiers(o)
    objs.append(o)
    bm = bmesh.new()
    util.tube(bm, [V((-hw, 0, height + 0.5)), V((hw, 0, height + 0.5))], (0.1, 0.1), n=8, power=3)
    o = util.mesh_object("WallRidge", bm, mats["ridge"])
    util.box_uv(o, 1.0)
    objs.append(o)
    if moon_gate:
        side = (length / 2 - 1.35) / 2
        for sx in (-1, 1):
            objs.append(util.collider("WallCol", (length / 2 - 1.35, t + 0.1, height),
                                      (sx * (1.35 + side), 0, height / 2)))
        objs.append(util.collider("WallTop", (2.7, t + 0.1, height - 2.8), (0, 0, 2.8 + (height - 2.8) / 2)))
    else:
        objs.append(util.collider("WallCol", (length, t + 0.1, height + 0.5), (0, 0, (height + 0.5) / 2)))
    return objs

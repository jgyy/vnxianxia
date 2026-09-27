"""Buildings, bridges and workshops of the enlarged Qingshi Town (see buildings.py for the kit).

Fronts face -Y in Blender (+Z in Godot); origin at the footprint centre on the ground.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector

from . import buildings as B
from . import lands, nature, realms, tex, util

V = Vector
R = math.radians


def _mat(name, maps, **kw):
    return util.material(name, maps, **kw)


def cloth_mat(color, seed):
    return util.material(f"cloth_{seed}", lands.canvas(color, 128, 700 + seed), double_sided=True,
                         normal_strength=0.4)


def jars(bm, cx, cy, n=6, seed=1, r=0.32, h=0.9, spread=1.6):
    rnd = random.Random(seed)
    for k in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0, spread)
        s = rnd.uniform(0.8, 1.2)
        util.lathe(bm, [(0.001, 0.0), (r * 0.6 * s, 0.0), (r * s, h * 0.35 * s), (r * 0.9 * s, h * 0.7 * s),
                        (r * 0.45 * s, h * 0.92 * s), (r * 0.5 * s, h * s)], segs=10,
                   loc=(cx + math.cos(a) * d, cy + math.sin(a) * d, 0.0), cap_bottom=True)


# --------------------------------------------------------------------------
# bridge
# --------------------------------------------------------------------------
def arch_bridge(span=16.0, width=4.2, rise=3.2, style="town"):
    """Humpbacked stone bridge along Y (a canal runs along X under it): steps up both sides
    (walkable ramps), a semicircular-ish arch, carved balustrades with lion posts."""
    m = B.kit(style)
    objs = []
    hw = width / 2
    n = 24
    ys = [-span / 2 + span * i / n for i in range(n + 1)]

    def deck(y):
        t = abs(y) / (span / 2)
        return rise * (1 - t * t)
    # body: side walls following the deck with the arch opening, as a lofted solid
    bm = bmesh.new()
    arch_r = span * 0.3
    arch_h = rise - 0.9
    for sx in (-1, 1):
        x = sx * hw
        tmp = bmesh.new()
        outline = [(-span / 2 - 0.5, -1.5)]
        k = 12
        outline += [(-arch_r, -1.5)]
        for i in range(k + 1):
            a = math.pi - math.pi * i / k
            outline.append((arch_r * math.cos(a), -1.5 + (arch_h + 1.5) * math.sin(a)))
        outline += [(arch_r, -1.5), (span / 2 + 0.5, -1.5)]
        outline += [(y, deck(y) - 0.02) for y in reversed(ys)]
        # outline in (y, z); build a thin slab (0.5 thick) at x
        vs_f = [tmp.verts.new(V((x - 0.25, y, z))) for (y, z) in outline]
        vs_b = [tmp.verts.new(V((x + 0.25, y, z))) for (y, z) in outline]
        nn = len(outline)
        for i in range(nn):
            i2 = (i + 1) % nn
            tmp.faces.new((vs_f[i], vs_f[i2], vs_b[i2], vs_b[i]))
        tmp.faces.new(vs_f)
        tmp.faces.new(list(reversed(vs_b)))
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        lands.merge(bm, tmp)
    # arch vault underside
    k = 12
    rows = []
    for i in range(k + 1):
        a = math.pi - math.pi * i / k
        yy, zz = arch_r * math.cos(a), -1.5 + (arch_h + 1.5) * math.sin(a)
        rows.append([V((x, yy, zz)) for x in (hw - 0.25, -hw + 0.25)])
    util.loft(bm, rows, closed=False)
    objs.append(B.obj("BridgeBody", bm, m["stone"], uv=0.5))
    # steps on the deck (visual)
    bm = bmesh.new()
    for i in range(n):
        y0, y1 = ys[i], ys[i + 1]
        z = max(deck(y0), deck(y1))
        util.box(bm, (width - 0.5, y1 - y0 + 0.02, 0.4), loc=(0, (y0 + y1) / 2, z - 0.2 + 0.02))
    objs.append(B.obj("BridgeSteps", bm, m["stone"], uv=0.6))
    # balustrade
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * (hw - 0.12)
        for i in range(0, n + 1, 2):
            y = ys[i]
            util.box(bm, (0.22, 0.22, 1.1), loc=(x, y, deck(y) + 0.5))
            util.sphere(bm, 0.14, loc=(x, y, deck(y) + 1.12), segs=6, rings=4)
        for i in range(0, n, 2):
            ya, yb = ys[i], ys[i + 2]
            za, zb = deck(ya), deck(yb)
            ang = math.atan2(zb - za, yb - ya)
            ln = math.hypot(yb - ya, zb - za)
            util.box(bm, (0.12, ln, 0.5), loc=(x, (ya + yb) / 2, (za + zb) / 2 + 0.45), rot=Matrix.Rotation(ang, 4, "X"))
            util.box(bm, (0.16, ln, 0.1), loc=(x, (ya + yb) / 2, (za + zb) / 2 + 0.85), rot=Matrix.Rotation(ang, 4, "X"))
    objs.append(B.obj("BridgeRails", bm, m["marble"], uv=1.0))
    # collision: the walking surface as a trimesh strip (through the step centres) + rails
    bm = bmesh.new()
    rowsv = []
    for i in range(n + 1):
        y = ys[i]
        z = deck(y) + 0.02
        rowsv.append((bm.verts.new(V((-hw, y, z))), bm.verts.new(V((hw, y, z)))))
    for i in range(n):
        bm.faces.new((rowsv[i][0], rowsv[i][1], rowsv[i + 1][1], rowsv[i + 1][0]))
    # extend ramps a little past both ends to meet the banks
    objs.append(util.mesh_object("BridgeWalk-colonly", bm, None, smooth=False))
    for sx in (-1, 1):
        for i in range(0, n, 4):
            ya, yb = ys[i], ys[min(i + 4, n)]
            za, zb = deck(ya), deck(yb)
            ang = math.atan2(zb - za, yb - ya)
            ln = math.hypot(yb - ya, zb - za)
            c = util.collider("BridgeRail", (0.3, ln, 1.4), (0, 0, 0))
            c.rotation_euler = (ang, 0, 0)
            c.location = (sx * (hw - 0.1), (ya + yb) / 2, (za + zb) / 2 + 0.7)
            util.apply_transform(c)
            objs.append(c)
    return objs


# --------------------------------------------------------------------------
# shops and houses
# --------------------------------------------------------------------------
def shophouse(w=8.0, d=6.5, storeys=1, seed=1, roof="gable", style="town"):
    """Street shop: an open front with a counter, shutters and a hanging signboard."""
    objs = B.hall(f"Shop{seed}", style, w=w, d=d, col_h=3.3, bays=3, podium_h=0.34, roof=roof, veranda=1.3,
                  storeys=storeys, beasts=0, plaque=False, rail=False, brackets=False, sign=seed, eave=1.2,
                  podium_margin=0.6)
    m = B.kit(style)
    bm = bmesh.new()
    # counter across the middle bay front and stacked goods
    util.box(bm, (w / 3 - 0.6, 0.6, 1.0), loc=(0, -d / 2 - 0.7, 0.34 + 0.5))
    util.box(bm, (w / 3 - 0.4, 0.75, 0.08), loc=(0, -d / 2 - 0.7, 0.34 + 1.04))
    objs.append(B.obj("Counter", bm, m["planks"], uv=1.0))
    rnd = random.Random(seed)
    bm = bmesh.new()
    jars(bm, w / 3, -d / 2 - 0.8, n=3, seed=seed, r=0.25, h=0.7, spread=0.4)
    for o in [B.obj("Jars", bm, _mat("glaze_" + str(seed % 3), lands.glaze(("#6b4a32", "#2f4a3a", "#5a3a2a")[seed % 3])),
                    uv=1.0, smooth=True)]:
        o.location.z += 0.34
        util.apply_transform(o)
        objs.append(o)
    # cloth awning over the front
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    y0, y1 = -d / 2 - 1.3 - 0.1, -d / 2 - 3.0
    z0, z1 = 0.34 + 3.1, 0.34 + 2.5
    vs = [bm.verts.new(V(p)) for p in ((-w / 2 + 0.3, y0, z0), (w / 2 - 0.3, y0, z0), (w / 2 - 0.3, y1, z1),
                                        (-w / 2 + 0.3, y1, z1))]
    f = bm.faces.new(vs)
    for loop, uv in zip(f.loops, ((0, 0), (3, 0), (3, 1), (0, 1))):
        loop[uvl].uv = uv
    objs.append(util.mesh_object("Awning", bm, util.material(f"awning_{seed % 4}",
                                                             lands.canvas(("#b5a482", "#8a3a2a", "#3a5a6a", "#a08a3a")[seed % 4],
                                                                          256, 461 + seed, stripes="#e8dcc0"),
                                                             double_sided=True, normal_strength=0.4), smooth=False))
    bm = bmesh.new()
    for x in (-w / 2 + 0.3, w / 2 - 0.3):
        util.cylinder(bm, 0.05, 0.05, z1, loc=(x, y1, z1 / 2), segs=6)
    objs.append(B.obj("AwningPoles", bm, m["wood"], uv=1.0))
    del rnd
    return objs


def city_gate():
    return B.gate_house("CityGate", "town", w=22.0, d=12.0, h=8.5, tower_storeys=2)


def granary():
    objs = B.hall("Granary", "town", w=16.0, d=10.0, col_h=4.0, bays=5, podium_h=1.6, roof="gable", veranda=0.0,
                  beasts=0, plaque=True, windows="none", stairs=(("front", 3.0),), rail=False)
    m = B.kit("town")
    bm = bmesh.new()
    # raised vents along the ridge and stone vent grilles on the plinth
    for x in (-5, 0, 5):
        util.box(bm, (1.2, 1.2, 0.8), loc=(x, 0, 1.6 + 4.0 + 3.4))
    objs.append(B.obj("Vents", bm, m["tiles"], uv=1.0))
    bm = bmesh.new()
    for x in (-6, -3, 3, 6):
        util.box(bm, (0.9, 0.1, 0.5), loc=(x, -5.0 - 1.4 - 0.05, 0.9))
    objs.append(B.obj("PlinthGrilles", bm, m["dark"], uv=None))
    return objs


def workshop(p, w=14.0, d=9.0, looms=4, seed=3):
    """Open-sided workshop shed with looms (silk) inside."""
    objs = B.hall(p, "town", w=w, d=d, col_h=3.6, bays=4, podium_h=0.3, roof="gable", veranda=0.0, beasts=0,
                  plaque=False, open_sides=True, windows="none", rail=False, brackets=False)
    # the hall's lattice front stays; remove the body collider so the shed can be entered
    objs = [o for o in objs if not o.name.startswith(p + "Body")]
    m = B.kit("town")
    bm = bmesh.new()
    silk = cloth_mat("#e8dcc0", seed)
    bm_c = bmesh.new()
    for k in range(looms):
        x = -w / 2 + 2.0 + (w - 4.0) * k / max(1, looms - 1)
        for dx in (-0.7, 0.7):
            for y in (-1.0, 1.0):
                util.box(bm, (0.1, 0.1, 1.6), loc=(x + dx, y, 0.3 + 0.8))
        util.box(bm, (1.5, 0.1, 0.1), loc=(x, -1.0, 0.3 + 1.6))
        util.box(bm, (1.5, 0.1, 0.1), loc=(x, 1.0, 0.3 + 1.6))
        util.box(bm, (1.5, 0.5, 0.06), loc=(x, 0.4, 0.3 + 0.75))
        util.box(bm_c, (1.3, 1.9, 0.02), loc=(x, 0.0, 0.3 + 0.9), rot=Matrix.Rotation(R(8), 4, "X"))
        util.box(bm, (0.5, 0.4, 0.45), loc=(x, -1.6, 0.3 + 0.22))
    objs.append(B.obj("Looms", bm, m["wood"], uv=1.0))
    objs.append(B.obj("LoomSilk", bm_c, silk, uv=1.0))
    for k in range(looms):
        x = -w / 2 + 2.0 + (w - 4.0) * k / max(1, looms - 1)
        objs.append(util.collider("Loom", (1.6, 2.2, 1.6), (x, 0, 0.3 + 0.8)))
    objs.append(util.collider("BackWall", (w, 0.4, 3.6), (0, d / 2, 0.3 + 1.8)))
    return objs


def dye_racks(seed=5):
    """Tall timber frames hung with long lengths of freshly dyed cloth (indigo, madder, saffron)."""
    m = B.kit("town")
    objs = []
    bm = bmesh.new()
    colours = ["#2a3f7a", "#8a1f22", "#d8a02a", "#3a6a4a", "#5a2a6a", "#1f2a4a"]
    bm_c = [bmesh.new() for _ in colours]
    for row in range(3):
        y = -3.0 + row * 3.0
        for x in (-5.0, 0.0, 5.0):
            util.box(bm, (0.16, 0.16, 5.2), loc=(x, y, 2.6))
        util.box(bm, (10.4, 0.14, 0.14), loc=(0, y, 5.1))
        util.box(bm, (10.4, 0.1, 0.1), loc=(0, y, 3.4))
        for k in range(8):
            x = -4.4 + k * 1.25
            ci = (k + row * 3 + seed) % len(colours)
            util.box(bm_c[ci], (0.9, 0.03, 4.4), loc=(x, y + 0.05, 5.05 - 2.2))
    objs.append(B.obj("DyeFrames", bm, m["wood"], uv=1.0))
    for i, b in enumerate(bm_c):
        objs.append(B.obj(f"DyedCloth{i}", b, cloth_mat(colours[i], 20 + i), uv=0.5))
    for row in range(3):
        objs.append(util.collider("Frame", (10.4, 0.3, 5.2), (0, -3.0 + row * 3.0, 2.6)))
    return objs


def dye_vats(seed=6):
    objs = []
    bm, bm_l = bmesh.new(), bmesh.new()
    rnd = random.Random(seed)
    colours = ["#1c2a5a", "#6a1418", "#b8801a", "#2a4a2a"]
    lq = [bmesh.new() for _ in colours]
    for k in range(6):
        x, y = (k % 3) * 2.4 - 2.4, (k // 3) * 2.4 - 1.2
        util.lathe(bm, [(0.001, 0), (0.9, 0), (1.0, 0.9), (1.05, 1.0), (0.95, 1.0), (0.9, 0.2), (0.001, 0.2)], segs=16,
                   loc=(x, y, 0))
        realms.disc(lq[k % 4], (x, y), 0.92, 16, z=0.85)
        del rnd
        rnd = random.Random(seed + k)
    objs.append(B.obj("Vats", bm, _mat("vat_wood", lands.planks("#5a4632", 256, 407, boards=12)), uv=1.0, smooth=True))
    for i, b in enumerate(lq):
        objs.append(util.mesh_object(f"Dye{i}", b, util.material(f"dye_{i}", color=colours[i], rough=0.15),
                                     smooth=False))
    for k in range(6):
        x, y = (k % 3) * 2.4 - 2.4, (k // 3) * 2.4 - 1.2
        objs.append(util.collider("Vat", (2.0, 2.0, 1.0), (x, y, 0.5)))
    del bm_l
    return objs


def exam_cells(n=12):
    """A long row of tiny examination cells (each 1.3 m wide) under a continuous tiled roof."""
    m = B.kit("town")
    objs = []
    cw, cd, ch = 1.3, 1.6, 2.6
    w = n * cw
    bm_w, bm_b = bmesh.new(), bmesh.new()
    util.box(bm_w, (w + 0.2, 0.2, ch), loc=(0, cd / 2, ch / 2))
    for k in range(n + 1):
        util.box(bm_w, (0.14, cd, ch), loc=(-w / 2 + k * cw, 0, ch / 2))
    for k in range(n):
        x = -w / 2 + (k + 0.5) * cw
        util.box(bm_b, (cw - 0.2, 0.5, 0.06), loc=(x, -0.1, 0.85))     # writing board
        util.box(bm_b, (cw - 0.2, 0.4, 0.06), loc=(x, 0.4, 0.45))      # seat board
    objs.append(B.obj("CellWalls", bm_w, m["brick"], uv=0.5))
    objs.append(B.obj("CellBoards", bm_b, m["planks"], uv=1.0))
    objs += B.gable_roof("Cells", m, w / 2 + 0.6, cd / 2 + 0.9, 1.0, ch)
    objs.append(util.collider("Cells", (w + 0.2, cd, ch), (0, 0.2, ch / 2)))
    # numbered placards
    bm = bmesh.new()
    for k in range(n):
        util.box(bm, (0.3, 0.05, 0.4), loc=(-w / 2 + (k + 0.5) * cw, -cd / 2 - 0.05, ch - 0.35))
    objs.append(B.obj("Placards", bm, m["plaque"], uv=1.0))
    return objs


def manor_gate():
    """Menlou: a gate building with a heavy lacquered door, lions and wing walls."""
    objs = B.hall("ManorGate", "town", w=8.0, d=5.0, col_h=3.8, bays=3, podium_h=0.7, roof="xieshan", veranda=1.2,
                  beasts=2, plaque=True, rail=False, stairs=(("front", 3.0), ("back", 3.0)))
    objs = [o for o in objs if not o.name.startswith("ManorGateBody")]
    m = B.kit("town")
    # side rooms (solid) leaving the middle bay as a passage
    for sx in (-1, 1):
        objs.append(util.collider("GateRoom", (8.0 / 3, 5.2, 3.8), (sx * 8.0 / 3, 0, 0.7 + 1.9)))
    bm = bmesh.new()
    for sx in (-1, 1):
        util.box(bm, (6.0, 0.6, 3.2), loc=(sx * 7.0, 0.0, 1.6))
    objs.append(B.obj("WingWalls", bm, m["plaster"], uv=0.35))
    bm = bmesh.new()
    for sx in (-1, 1):
        util.box(bm, (6.2, 1.0, 0.25), loc=(sx * 7.0, 0.0, 3.3))
    objs.append(B.obj("WingCoping", bm, m["tiles"], uv=0.8))
    for sx in (-1, 1):
        objs.append(util.collider("Wing", (6.0, 0.8, 3.4), (sx * 7.0, 0, 1.7)))
    # stone lions
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * 2.0
        util.box(bm, (0.9, 1.3, 0.9), loc=(x, -4.6, 0.45))
        util.sphere(bm, 0.45, loc=(x, -4.6, 1.3), segs=10, rings=6, scale=(0.9, 1.1, 1.0))
        util.sphere(bm, 0.36, loc=(x, -4.95, 1.85), segs=10, rings=6)
    objs.append(B.obj("Lions", bm, m["stone"], uv=1.0, smooth=True))
    for sx in (-1, 1):
        objs.append(util.collider("Lion", (1.0, 1.4, 2.2), (sx * 2.0, -4.6, 1.1)))
    return objs


def opera_stage():
    """Raised opera stage (open on the front) with a painted back screen and a hip-and-gable roof."""
    m = B.kit("temple")
    objs = []
    h = 1.6
    w, d = 12.0, 9.0
    bm = bmesh.new()
    util.box(bm, (w, d, h + 0.6), loc=(0, 0, (h - 0.6) / 2))
    objs.append(B.obj("StageBase", bm, m["brick"], uv=0.5))
    bm = bmesh.new()
    util.box(bm, (w + 0.2, d + 0.2, 0.12), loc=(0, 0, h + 0.06))
    objs.append(B.obj("StageFloor", bm, m["planks"], uv=0.5))
    # rear flights (performers' entrance) left and right of the back
    for sx in (-1, 1):
        bm_s = bmesh.new()
        run = B.steps(bm_s, 2.0, h, y_top=0.0)
        o = B.obj("StageSteps", bm_s, m["stone"], uv=0.6)
        c = B.stair_ramp("StageRamp", 2.3, h)
        for oo in (o, c):
            oo.matrix_basis = Matrix.Translation(V((sx * (w / 2 - 1.5), d / 2 + 0.1, 0))) @ Matrix.Rotation(math.pi, 4, "Z")
            util.apply_transform(oo)
        objs += [o, c]
        del run
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for x in (-w / 2 + 0.4, -w / 6, w / 6, w / 2 - 0.4):
        for y in (-d / 2 + 0.4, d / 2 - 0.4):
            B.column(bm_p, bm_s, x, y, h + 0.12, 4.2, r=0.24)
    objs.append(B.obj("StageColumns", bm_p, m["pillar"], smooth=True))
    objs.append(B.obj("StageBases", bm_s, m["stone"]))
    bm = bmesh.new()
    util.box(bm, (w - 0.8, 0.25, 4.0), loc=(0, d / 2 - 1.8, h + 2.1))
    objs.append(B.obj("BackScreen", bm, m["plaster"], uv=0.3))
    screen = util.material("opera_screen", tex.silk("#7a1a14", "#d8b04a", 256, 31), normal_strength=0.3)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(V((x, d / 2 - 1.95, z))) for x, z in ((-w / 2 + 1.0, h + 0.4), (w / 2 - 1.0, h + 0.4),
                                                             (w / 2 - 1.0, h + 3.8), (-w / 2 + 1.0, h + 3.8))]
    f = bm.faces.new(vs)
    for loop, uvv in zip(f.loops, ((0, 0), (3, 0), (3, 1), (0, 1))):
        loop[uv].uv = uvv
    objs.append(util.mesh_object("ScreenSilk", bm, screen, smooth=False))
    bm = bmesh.new()
    util.box(bm, (w + 0.6, 0.4, 0.6), loc=(0, -d / 2 + 0.4, h + 4.4))
    util.box(bm, (w + 0.6, 0.4, 0.6), loc=(0, d / 2 - 0.4, h + 4.4))
    util.box(bm, (0.4, d, 0.6), loc=(-w / 2 + 0.4, 0, h + 4.4))
    util.box(bm, (0.4, d, 0.6), loc=(w / 2 - 0.4, 0, h + 4.4))
    objs.append(B.obj("StageBeams", bm, m["beam"], uv=1.0))
    objs += B.xieshan_roof("Stage", m, 0, 0, w / 2 + 1.5, d / 2 + 1.4, 4.2, h + 4.9, beasts=3)
    objs += __import__("xianxia.arch", fromlist=["plaque_board"]).plaque_board(m, (0, -d / 2 + 0.1, h + 4.2), w=3.0,
                                                                                 h=0.8, tilt=0)
    objs.append(util.collider("Stage", (w, d, h + 0.6), (0, 0, (h - 0.6) / 2)))
    objs.append(util.collider("Screen", (w, 0.4, 4.0), (0, d / 2 - 1.8, h + 2.1)))
    # front: a low rail except a gap
    return objs


def watermill(wheel_r=3.2):
    """Mill house on a stone base beside its race, with an undershot wheel on the +X side."""
    m = B.kit("town")
    objs = B.hall("Mill", "town", w=9.0, d=7.0, col_h=3.4, bays=3, podium_h=0.6, roof="gable", veranda=0.0,
                  beasts=0, plaque=False, rail=False, brackets=False)
    objs += waterwheel_parts(m, wheel_r, (4.5 + 0.9 + 0.6, 0.0, wheel_r - 0.8))
    return objs


def waterwheel_parts(m, r, loc, width=1.2, paddles=16):
    x0, y0, z0 = loc
    bm = bmesh.new()
    for dx in (-width / 2, width / 2):
        ring = [V((x0 + dx, y0 + r * math.cos(a), z0 + r * math.sin(a))) for a in
                [2 * math.pi * k / 32 for k in range(33)]]
        util.tube(bm, ring, 0.09, n=6, closed_ends=False)
        for k in range(8):
            a = 2 * math.pi * k / 8
            util.tube(bm, [V((x0 + dx, y0, z0)), V((x0 + dx, y0 + r * math.cos(a), z0 + r * math.sin(a)))], 0.07, n=5)
    for k in range(paddles):
        a = 2 * math.pi * k / paddles
        util.box(bm, (width + 0.1, 0.06, 0.7), loc=(x0, y0 + (r - 0.25) * math.cos(a), z0 + (r - 0.25) * math.sin(a)),
                 rot=Matrix.Rotation(a + math.pi / 2, 4, "X"))
    util.cylinder(bm, 0.18, 0.18, width + 1.6, loc=(x0 - 0.8, y0, z0), rot=Matrix.Rotation(R(90), 4, "Y"), segs=10)
    return [B.obj("Waterwheel", bm, m["planks"], uv=1.0, smooth=False),
            util.collider("Wheel", (width + 0.2, r * 2, r * 2), (x0, y0, z0))]


def boat_hull(bm, L=9.0, B_=2.6, depth=1.2, rise=0.6):
    rings = []
    for k in range(13):
        t = k / 12
        y = -L / 2 + L * t
        wdt = B_ / 2 * math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.6
        zb = -depth + depth * 0.4 * (abs(2 * t - 1) ** 3)
        top = rise * (abs(2 * t - 1) ** 2)
        rings.append([V((-wdt, y, top)), V((-wdt * 0.85, y, zb + 0.25)), V((0, y, zb)), V((wdt * 0.85, y, zb + 0.25)),
                      V((wdt, y, top))])
    util.loft(bm, rings, closed=False, uv_scale=(1.0, 0.4))
    deck = [[V((-B_ / 2 * 0.9 * math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.6, -L / 2 + L * t,
                rise * (abs(2 * t - 1) ** 2) - 0.15)),
             V((B_ / 2 * 0.9 * math.sin(math.pi * (0.06 + 0.88 * t)) ** 0.6, -L / 2 + L * t,
                rise * (abs(2 * t - 1) ** 2) - 0.15))] for t in [k / 12 for k in range(13)]]
    util.loft(bm, deck, closed=False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def sampan(L=7.0):
    """A river sampan with a woven canopy (floats; origin at the waterline)."""
    hull_m = util.material("boat_hull", lands.planks("#4a3a2a", 256, 403, boards=8), normal_strength=0.7,
                           double_sided=True)
    mat_m = util.material("boat_matting", lands.woven("#8a6a3c", 256, 552), double_sided=True, normal_strength=0.6)
    bm = bmesh.new()
    boat_hull(bm, L, 1.8, 0.7, 0.4)
    objs = [util.mesh_object("SampanHull", bm, hull_m, smooth=False)]
    bm = bmesh.new()
    arc = [V((0.8 * math.cos(a), 0, 0.1 + 0.9 * math.sin(a))) for a in [math.pi * k / 9 for k in range(10)]]
    util.loft(bm, [[p + V((0, y, 0)) for p in arc] for y in (-1.2, 1.2)], closed=False, uv_scale=(3.0, 1.0))
    objs.append(util.mesh_object("SampanCanopy", bm, mat_m, smooth=True))
    bm = bmesh.new()
    util.tube(bm, [V((0.3, L / 2 - 0.6, 0.4)), V((0.5, L / 2 + 2.2, -0.6))], 0.04, n=5)
    objs.append(B.obj("Oar", bm, B.kit("town")["wood"], uv=1.0))
    objs.append(util.collider("Sampan", (1.8, L, 1.2), (0, 0, -0.1)))
    return objs


def boat_on_stocks():
    """A junk under construction on timber stocks, with scaffold and a ribbed half-planked hull."""
    m = B.kit("town")
    objs = []
    bm = bmesh.new()
    boat_hull(bm, 14.0, 4.2, 2.0, 1.2)
    bmesh.ops.translate(bm, verts=bm.verts, vec=V((0, 0, 2.6)))
    # strip part of the planking (ribs showing)
    kill = [f for f in bm.faces if f.calc_center_median().y > 2.0 and f.calc_center_median().x > 0]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    objs.append(util.mesh_object("JunkHull", bm, util.material("junk_hull", lands.planks("#7a5a3c", 256, 408, boards=10),
                                                                 double_sided=True, normal_strength=0.7), smooth=False))
    bm = bmesh.new()
    for k in range(7):
        y = -6 + k * 2.0
        util.box(bm, (3.4, 0.4, 0.8), loc=(0, y, 0.4))
        if y > 2.0:
            arc = [V((2.1 * math.sin(a) * 0.95, y, 2.6 - 1.9 * math.cos(a) + 0.2)) for a in
                   [(-math.pi / 2) + math.pi * i / 10 for i in range(11)]]
            util.tube(bm, arc, 0.08, n=5)
    for sx in (-1, 1):
        for y in (-6, -2, 2, 6):
            util.box(bm, (0.14, 0.14, 5.2), loc=(sx * 3.2, y, 2.6))
        util.box(bm, (0.12, 13.0, 0.12), loc=(sx * 3.2, 0, 2.2))
        util.box(bm, (0.8, 13.0, 0.08), loc=(sx * 2.85, 0, 3.8))
    objs.append(B.obj("Stocks", bm, m["wood"], uv=1.0))
    objs.append(util.collider("Hull", (4.4, 14.0, 4.4), (0, 0, 2.4)))
    for sx in (-1, 1):
        objs.append(util.collider("Scaffold", (1.0, 13.0, 5.2), (sx * 3.0, 0, 2.6)))
    return objs


def post_station():
    """Stables: an open-fronted shed with stalls, a hay loft, trough and hitching rail."""
    m = B.kit("town")
    objs = B.hall("Stable", "town", w=14.0, d=6.0, col_h=3.2, bays=5, podium_h=0.0, roof="gable", veranda=0.0,
                  beasts=0, plaque=False, open_sides=True, rail=False, brackets=False, windows="none")
    objs = [o for o in objs if not o.name.startswith("StableBody") and not o.name.startswith("StableLattice")
            and not o.name.startswith("StableFrames")]
    bm = bmesh.new()
    util.box(bm, (14.0, 0.25, 3.2), loc=(0, 3.0, 1.6))
    for k in range(6):
        util.box(bm, (0.15, 5.0, 1.5), loc=(-7.0 + k * 2.8, 0.5, 0.75))
    util.box(bm, (14.0, 0.15, 0.15), loc=(0, -4.4, 1.0))
    for x in (-6.5, -2.0, 2.0, 6.5):
        util.box(bm, (0.14, 0.14, 1.1), loc=(x, -4.4, 0.55))
    objs.append(B.obj("Stalls", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    util.box(bm, (3.0, 0.8, 0.6), loc=(-4.0, -3.2, 0.3))
    objs.append(B.obj("Trough", bm, m["stone"], uv=1.0))
    thatch = util.material("thatch", lands.thatch(256), normal_strength=1.0)
    bm = bmesh.new()
    for k in range(5):
        lands.rock(bm, (-5.6 + k * 2.8, 1.5, 0.45), (0.9, 1.2, 0.5), 80 + k, 0.2, 1)
    objs.append(B.obj("Hay", bm, thatch, uv=1.0, smooth=True))
    objs.append(util.collider("Back", (14.0, 0.4, 3.2), (0, 3.0, 1.6)))
    objs.append(util.collider("Rail", (14.0, 0.3, 1.2), (0, -4.4, 0.6)))
    objs.append(util.collider("Trough", (3.0, 0.8, 0.6), (-4.0, -3.2, 0.3)))
    return objs


def execution_platform():
    m = B.kit("town")
    objs = B.podium("Exec", m, 5.0, 4.0, 1.2, stairs=(("front", 2.5),), rail=False, base="stone", cap="planks")
    bm = bmesh.new()
    for x in (-2.0, 2.0):
        util.box(bm, (0.3, 0.3, 3.2), loc=(x, 1.5, 1.2 + 1.6))
    util.box(bm, (4.6, 0.3, 0.3), loc=(0, 1.5, 1.2 + 3.1))
    util.box(bm, (1.2, 0.6, 0.5), loc=(0, 0.2, 1.2 + 0.25))
    objs.append(B.obj("Frame", bm, m["wood"], uv=1.0))
    for x in (-2.0, 2.0):
        objs.append(util.collider("Post", (0.4, 0.4, 3.2), (x, 1.5, 1.2 + 1.6)))
    return objs


def tannery_racks():
    m = B.kit("town")
    objs = []
    hide = util.material("hide", tex.leather("#8a6a4a", 256, 9), double_sided=True, normal_strength=0.5)
    bm, bm_h = bmesh.new(), bmesh.new()
    rnd = random.Random(9)
    for row in range(2):
        y = -2.0 + row * 4.0
        for k in range(4):
            x = -4.5 + k * 3.0
            for dx in (-1.1, 1.1):
                util.box(bm, (0.12, 0.12, 2.6), loc=(x + dx, y, 1.3))
            util.box(bm, (2.4, 0.1, 0.1), loc=(x, y, 2.5))
            util.box(bm, (2.4, 0.1, 0.1), loc=(x, y, 0.4))
            s = rnd.uniform(0.8, 1.0)
            util.box(bm_h, (1.8 * s, 0.03, 1.8 * s), loc=(x, y, 1.45), rot=Matrix.Rotation(R(rnd.uniform(-8, 8)), 4, "Y"))
    objs.append(B.obj("Racks", bm, m["wood"], uv=1.0))
    objs.append(B.obj("Hides", bm_h, hide, uv=0.6))
    for row in range(2):
        objs.append(util.collider("Rack", (12.0, 0.3, 2.6), (0, -2.0 + row * 4.0, 1.3)))
    return objs


def pottery_kiln():
    """Dragon kiln: a long brick vault climbing the clay bank (along +Y), stoke holes and a chimney."""
    m = B.kit("town")
    objs = []
    L, W = 16.0, 3.0
    bm = bmesh.new()
    rings = []
    for k in range(17):
        y = -L / 2 + L * k / 16
        z = 0.12 * (y + L / 2)
        ring = [V((W / 2 * math.cos(a), y, z + 1.9 * math.sin(a))) for a in [math.pi * i / 10 for i in range(11)]]
        rings.append(ring)
    util.loft(bm, rings, closed=False, uv_scale=(4.0, 1.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < -0.1 and abs(f.normal.x) < 0.3:
            pass
    objs.append(B.obj("KilnVault", bm, m["brick"], uv=0.5, smooth=True))
    bm = bmesh.new()
    util.box(bm, (1.6, 1.6, 4.5), loc=(0, L / 2 + 0.6, 0.12 * L + 2.0))
    objs.append(B.obj("KilnChimney", bm, m["brick"], uv=0.5))
    bm = bmesh.new()
    for k in range(6):
        y = -L / 2 + 1.5 + k * 2.6
        z = 0.12 * (y + L / 2)
        for sx in (-1, 1):
            util.box(bm, (0.1, 0.4, 0.4), loc=(sx * (W / 2 + 0.02), y, z + 0.6))
    util.box(bm, (1.2, 0.1, 1.2), loc=(0, -L / 2 - 0.02, 0.7))
    objs.append(B.obj("StokeHoles", bm, B.glow("kiln_fire", "#ff7a2a", 3.0), uv=None))
    bm = bmesh.new()
    jars(bm, -3.5, -L / 2 - 1.5, n=10, seed=4, r=0.3, h=0.7, spread=1.5)
    jars(bm, 3.5, -L / 2 - 2.0, n=8, seed=5, r=0.22, h=0.5, spread=1.2)
    objs.append(B.obj("Pots", bm, util.material("unglazed_clay", lands.glaze("#a8643a", 256, 545), normal_strength=0.2),
                      uv=1.0, smooth=True))
    for k in range(4):
        y = -L / 2 + L * (k + 0.5) / 4
        objs.append(util.collider("Kiln", (W, L / 4, 2.0), (0, y, 0.12 * (y + L / 2) + 1.0)))
    objs.append(util.collider("Chimney", (1.6, 1.6, 4.5), (0, L / 2 + 0.6, 0.12 * L + 2.0)))
    return objs


def wine_jars():
    """A brewery yard's rows of big glazed wine jars under cloth covers."""
    objs = []
    bm = bmesh.new()
    for row in range(3):
        for k in range(6):
            util.lathe(bm, [(0.001, 0.0), (0.35, 0.0), (0.6, 0.45), (0.55, 0.95), (0.25, 1.15), (0.28, 1.25)], segs=12,
                       loc=(-3.5 + k * 1.4, -1.5 + row * 1.5, 0.0), cap_bottom=True)
    objs.append(B.obj("WineJars", bm, util.material("wine_glaze", lands.glaze("#3a2a1e", 256, 546),
                                                    normal_strength=0.2), uv=1.0, smooth=True))
    bm = bmesh.new()
    for row in range(3):
        for k in range(6):
            util.sphere(bm, 0.3, loc=(-3.5 + k * 1.4, -1.5 + row * 1.5, 1.27), segs=8, rings=4, scale=(1, 1, 0.35))
    objs.append(B.obj("JarCovers", bm, cloth_mat("#8a2a1a", 40), uv=1.0, smooth=True))
    objs.append(util.collider("Jars", (8.4, 4.4, 1.3), (0, 0, 0.65)))
    return objs


def lantern_line(length=12.0, n=8, seed=3):
    """Two poles strung with red paper lanterns (night market)."""
    m = B.kit("town")
    paper = util.material("lantern_paper", tex.paper_lantern("#c8281c", 128), emission="#ff6a3a",
                          emission_strength=1.6)
    frame = util.material("lantern_frame", color="#2a1a12", rough=0.6)
    bm_p, bm_f, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
    for x in (-length / 2, length / 2):
        util.box(bm_w, (0.18, 0.18, 5.0), loc=(x, 0, 2.5))
    pts = [V((-length / 2 + length * k / 16, 0, 4.7 - 0.7 * math.sin(math.pi * k / 16))) for k in range(17)]
    util.tube(bm_w, pts, 0.015, n=4)
    for k in range(n):
        t = (k + 0.5) / n
        x = -length / 2 + length * t
        z = 4.7 - 0.7 * math.sin(math.pi * t)
        realms.lantern(bm_p, bm_f, (x, 0, z), 0.9)
    objs = [B.obj("Poles", bm_w, m["wood"], uv=1.0), util.mesh_object("Lanterns", bm_p, paper, smooth=True),
            util.mesh_object("LanternFrames", bm_f, frame, smooth=False)]
    for x in (-length / 2, length / 2):
        objs.append(util.collider("Pole", (0.3, 0.3, 5.0), (x, 0, 2.5)))
    return objs


def willow_tree(seed=11, height=8.0):
    """Weeping willow: leaning trunk, a rounded crown and long hanging curtains of leaves."""
    rnd = random.Random(seed)
    bark = util.material("willow_bark", tex.bark("#4d4234", 256, 137), normal_strength=1.0)
    lc = lands.leaf_cards(256, 512, "#7a9a3a", kind="bamboo")
    leaf = lands.clip_alpha(util.material("willow_leaves", lc, alpha=lc["alpha"], double_sided=True,
                                          normal_strength=0.3))
    bm_t, bm_l = bmesh.new(), bmesh.new()
    top = V((0.6, 0.3, height * 0.6))
    util.tube(bm_t, util.catmull([V((0, 0, -0.2)), V((0.3, 0.1, height * 0.3)), top], 4),
              lambda t: 0.35 * (1 - 0.5 * t), n=10)
    uvl = bm_l.loops.layers.uv.verify()
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.3, 0.3)
        tip = top + V((math.cos(a) * 3.0, math.sin(a) * 3.0, rnd.uniform(0.5, 1.8)))
        util.tube(bm_t, util.catmull([top, top.lerp(tip, 0.5) + V((0, 0, 0.6)), tip], 3), lambda t: 0.15 * (1 - 0.7 * t),
                  n=6)
        for j in range(9):
            b = a + rnd.uniform(-0.7, 0.7)
            r = rnd.uniform(1.5, 4.0)
            base = top + V((math.cos(b) * r, math.sin(b) * r, rnd.uniform(0.8, 2.2)))
            ln = rnd.uniform(3.0, 5.5)
            wd = 0.9
            d = V((-math.sin(b), math.cos(b), 0)) * wd / 2
            vs = [bm_l.verts.new(base - d), bm_l.verts.new(base + d), bm_l.verts.new(base + d - V((0, 0, ln))),
                  bm_l.verts.new(base - d - V((0, 0, ln)))]
            f = bm_l.faces.new(vs)
            for loop, uv in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                loop[uvl].uv = uv
    return [util.mesh_object("WillowTrunk", bm_t, bark, smooth=True), util.mesh_object("WillowLeaves", bm_l, leaf,
                                                                                        smooth=False),
            util.collider("Trunk", (0.8, 0.8, height * 0.5), (0.2, 0.1, height * 0.25))]


def town_temple():
    """The City God temple's main hall: green-glazed double eaves on a high terrace."""
    return B.hall("CityGod", "temple", w=18.0, d=12.0, col_h=5.0, bays=5, podium_h=1.4, roof="double", veranda=2.2,
                  beasts=5, stairs=(("front", 5.0),))


ASSETS = {
    "city_gate": city_gate,
    "city_wall": lambda: B.wall_segment("town", 8.0, 5.5, 1.8, crenel=True),
    "shophouse_a": lambda: shophouse(8.0, 6.5, 1, seed=1),
    "shophouse_b": lambda: shophouse(9.0, 7.0, 2, seed=2, roof="hip"),
    "shophouse_c": lambda: shophouse(10.0, 7.0, 1, seed=3, roof="xieshan"),
    "tavern": lambda: B.hall("Tavern", "town", w=14.0, d=9.0, col_h=3.6, bays=5, podium_h=0.45, roof="xieshan",
                             veranda=1.6, storeys=2, beasts=2, plaque=True, rail=False, sign=7),
    "pharmacy": lambda: B.hall("Pharmacy", "town", w=13.0, d=9.0, col_h=3.6, bays=5, podium_h=0.6, roof="gable",
                               veranda=1.6, storeys=2, beasts=0, plaque=True, rail=False, sign=8),
    "pawnshop": lambda: B.hall("Pawnshop", "town", w=8.0, d=8.0, col_h=4.4, bays=3, podium_h=0.9, roof="gable",
                               veranda=0.0, storeys=2, beasts=0, plaque=True, rail=False, sign=9,
                               stairs=(("front", 2.4),)),
    "granary": granary,
    "silk_workshop": lambda: workshop("Silk", 14.0, 9.0, looms=4),
    "dye_racks": dye_racks,
    "dye_vats": dye_vats,
    "academy_hall": lambda: B.hall("Academy", "sect", w=16.0, d=10.0, col_h=4.4, bays=5, podium_h=1.0,
                                   roof="xieshan", veranda=2.0, beasts=3),
    "exam_cells": exam_cells,
    "manor_gate": manor_gate,
    "manor_hall": lambda: B.hall("Manor", "town", w=15.0, d=10.0, col_h=4.0, bays=5, podium_h=0.8, roof="xieshan",
                                 veranda=1.8, beasts=2, plaque=True),
    "opera_stage": opera_stage,
    "city_god_temple": town_temple,
    "bell_pavilion": lambda: B.tower(p="BellPavilion", style="town", sides=4, storeys=1, r0=3.6, storey_h=3.6,
                                     base="arch", base_h=6.0, base_r=5.5, spire=False, eave=1.6)[0],
    "bathhouse": lambda: B.hall("Bathhouse", "town", w=14.0, d=10.0, col_h=3.6, bays=5, podium_h=0.45, roof="gable",
                                veranda=1.4, beasts=0, plaque=True, rail=False),
    "watermill": watermill,
    "boat_on_stocks": boat_on_stocks,
    "sampan": sampan,
    "arch_bridge": arch_bridge,
    "post_station": post_station,
    "barracks": lambda: B.hall("Barracks", "town", w=24.0, d=8.0, col_h=3.4, bays=8, podium_h=0.45, roof="gable",
                               veranda=1.4, beasts=0, plaque=True, rail=False),
    "execution_platform": execution_platform,
    "tannery_racks": tannery_racks,
    "pottery_kiln": pottery_kiln,
    "wine_jars": wine_jars,
    "lantern_line": lantern_line,
    "willow_tree": willow_tree,
    "town_hall_small": lambda: B.hall("Orphanage", "town", w=12.0, d=8.0, col_h=3.4, bays=5, podium_h=0.45,
                                      roof="gable", veranda=1.4, beasts=0, plaque=True, rail=False),
}

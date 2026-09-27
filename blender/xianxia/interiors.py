"""Explorable building interiors, entered through a door on one of the five
exterior maps (see godot/scripts/world/doors.gd and tools/maps/interiors.py).

Every interior is a single enclosed room built with the same conventions as
blender/xianxia/arch.py: Blender Z-up, origin at floor centre, a doorway
centred on the -Y wall (the room's front, +Z once exported to Godot), and
'-colonly' collision boxes for the floor/walls so the player cannot walk
through them. Materials are the same kits used by the exterior of the
building each interior belongs to (arch.kit() for the sect, lands.kit() for
the town, realms.abyss_mats()/sky_mats() for the Abyss and the Isles), so
walking through a door never breaks the map's look.
"""
import math
import random

import bmesh
from mathutils import Vector

from . import arch, lands, props, realms, tex, util

V = Vector
R = math.radians


# --------------------------------------------------------------------------
# room shell
# --------------------------------------------------------------------------
def _shell(mats, w, d, h, door_w=2.6, door_h=2.35, floor_mat=None, wall_mat=None, ceil_mat=None,
           beams=True):
    """Closed rectangular room: floor, four walls with a doorway in the
    middle of the -Y wall, and a flat beamed ceiling. Returns a list of
    objects (visual meshes + '-colonly' colliders)."""
    fm = floor_mat or mats.get("stone") or mats.get("marble")
    wm = wall_mat or mats["plaster"]
    cm = ceil_mat or mats.get("beam") or mats["wood"]
    t = 0.3
    objs = []
    bm = bmesh.new()
    util.box(bm, (w, d, 0.2), loc=(0, 0, -0.1))
    o = util.mesh_object("Floor", bm, fm, smooth=False)
    util.box_uv(o, 0.5)
    objs.append(o)
    side = (w - door_w) / 2
    bm = bmesh.new()
    util.box(bm, (w + t, t, h), loc=(0, d / 2, h / 2))
    util.box(bm, (t, d + t, h), loc=(-w / 2, 0, h / 2))
    util.box(bm, (t, d + t, h), loc=(w / 2, 0, h / 2))
    if side > 0.05:
        for sx in (-1, 1):
            util.box(bm, (side, t, h), loc=(sx * (w / 2 - side / 2), -d / 2, h / 2))
    util.box(bm, (door_w, t, h - door_h), loc=(0, -d / 2, h - (h - door_h) / 2))
    o = util.mesh_object("Walls", bm, wm, smooth=False)
    util.box_uv(o, 0.4)
    objs.append(o)
    bm = bmesh.new()
    util.box(bm, (w + t, d + t, 0.25), loc=(0, 0, h + 0.125))
    if beams:
        for x in [-w / 2 + 0.6 + k * (w - 1.2) / 3 for k in range(4)]:
            util.box(bm, (0.18, d + t - 0.06, 0.22), loc=(x, 0, h - 0.11))
    o = util.mesh_object("Ceiling", bm, cm, smooth=False)
    util.box_uv(o, 0.4)
    objs.append(o)
    objs.append(util.collider("ShellFloor", (w, d, 0.4), (0, 0, -0.2)))
    objs.append(util.collider("ShellBack", (w + t, t, h), (0, d / 2, h / 2)))
    objs.append(util.collider("ShellLeft", (t, d + t, h), (-w / 2, 0, h / 2)))
    objs.append(util.collider("ShellRight", (t, d + t, h), (w / 2, 0, h / 2)))
    if side > 0.05:
        for sx in (-1, 1):
            objs.append(util.collider("ShellFront", (side, t, h), (sx * (w / 2 - side / 2), -d / 2, h / 2)))
    objs.append(util.collider("ShellLintel", (door_w, t, h - door_h), (0, -d / 2, h - (h - door_h) / 2)))
    return objs


def _place(objs, loc, yaw=0.0, scale=1.0):
    """Move/rotate/scale a group of freshly built objects as one rigid piece."""
    for o in objs:
        o.rotation_euler = (0, 0, R(yaw))
        o.scale = (scale, scale, scale)
        o.location = Vector(loc)
        util.apply_transform(o)
    return objs


# --------------------------------------------------------------------------
# reusable furniture (built at the origin; place with _place)
# --------------------------------------------------------------------------
def _table(mats, w=1.4, d=0.8, h=0.78, mat=None):
    m = mat or mats["wood"]
    bm = bmesh.new()
    util.box(bm, (w, d, 0.07), loc=(0, 0, h - 0.035))
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (0.09, 0.09, h - 0.07), loc=(sx * (w / 2 - 0.12), sy * (d / 2 - 0.12), (h - 0.07) / 2))
    o = util.mesh_object("Table", bm, m, smooth=False)
    util.box_uv(o, 1.5)
    return [o, util.collider("TableCol", (w, d, h), (0, 0, h / 2))]


def _stool(mats, mat=None, r=0.22, h=0.46):
    m = mat or mats["wood"]
    bm = bmesh.new()
    util.cylinder(bm, r, r, 0.05, loc=(0, 0, h), segs=10)
    for k in range(4):
        a = R(45 + 90 * k)
        util.cylinder(bm, 0.024, 0.024, h - 0.03, loc=(math.cos(a) * r * 0.72, math.sin(a) * r * 0.72, (h - 0.03) / 2),
                      segs=6)
    o = util.mesh_object("Stool", bm, m, smooth=False)
    util.box_uv(o, 2.0)
    return [o, util.collider("StoolCol", (r * 2, r * 2, h + 0.05), (0, 0, (h + 0.05) / 2))]


def _bed(mats, w=1.0, ln=1.95, h=0.42, mat=None, blanket=None):
    wood = mat or mats["wood"]
    bm = bmesh.new()
    util.box(bm, (w, ln, h), loc=(0, 0, h / 2))
    o = util.mesh_object("BedFrame", bm, wood, smooth=False)
    util.box_uv(o, 1.2)
    bm = bmesh.new()
    util.box(bm, (w - 0.08, ln * 0.5, 0.12), loc=(0, -ln * 0.22, h + 0.06))
    util.box(bm, (w - 0.1, 0.24, 0.1), loc=(0, ln / 2 - 0.16, h + 0.1))
    bl = util.mesh_object("BedBlanket", bm, blanket or mat or mats["wood"], smooth=False)
    util.box_uv(bl, 2.0)
    return [o, bl, util.collider("BedCol", (w, ln, h + 0.15), (0, 0, (h + 0.15) / 2))]


def _shelf(mats, w=1.6, h=1.7, levels=3, depth=0.32, mat=None, item_mat=None, items=0, seed=0):
    wood = mat or mats["wood"]
    bm = bmesh.new()
    for sx in (-1, 1):
        util.box(bm, (0.07, depth, h), loc=(sx * (w / 2 - 0.035), depth / 2, h / 2))
    for k in range(levels + 1):
        util.box(bm, (w, depth, 0.045), loc=(0, depth / 2, h * k / levels))
    o = util.mesh_object("Shelf", bm, wood, smooth=False)
    util.box_uv(o, 1.2)
    objs = [o, util.collider("ShelfCol", (w, depth, h), (0, depth / 2, h / 2))]
    if items > 0 and item_mat is not None:
        rnd = random.Random(seed)
        bm2 = bmesh.new()
        for k in range(levels):
            z = h * k / levels + 0.22
            for i in range(items):
                x = -w / 2 + 0.16 + i * (w - 0.32) / max(1, items - 1)
                util.cylinder(bm2, 0.055, 0.05, rnd.uniform(0.16, 0.26), segs=8,
                              loc=(x, depth / 2 + rnd.uniform(-0.03, 0.03), z))
        objs.append(util.mesh_object("ShelfItems", bm2, item_mat))
    return objs


def _cushion(color="#b3213a", r=0.32, h=0.14, mat=None):
    m = mat or util.material("cushion_" + color.strip("#"), color=color, rough=0.7)
    bm = bmesh.new()
    util.cylinder(bm, r, r * 0.9, h, loc=(0, 0, h / 2), segs=12)
    o = util.mesh_object("Cushion", bm, m, smooth=True)
    return [o]


def _brazier_fire(r=0.4, glow="#ff5a1a"):
    """A glowing bed of embers (no smoke): used for furnaces and forges."""
    fire = util.material("brazier_fire_" + glow.strip("#"), color=glow, rough=0.6, emission=glow,
                         emission_strength=6.0)
    bm = bmesh.new()
    util.cylinder(bm, r, r * 0.85, 0.12, loc=(0, 0, 0.06), segs=16)
    return [util.mesh_object("Embers", bm, fire, smooth=False)]


def _hanging_lantern(loc, glow="#ff4a1c"):
    return _place(props.red_lantern(), loc)


def _rug(mats, w, d, color="#8e1a14", h=0.03):
    m = util.material("rug_" + color.strip("#"), color=color, rough=0.85)
    bm = bmesh.new()
    util.box(bm, (w, d, h), loc=(0, 0, h / 2 + 0.002))
    o = util.mesh_object("Rug", bm, m, smooth=False)
    util.box_uv(o, 0.8)
    return [o]


# --------------------------------------------------------------------------
# Azure Cloud Sect
# --------------------------------------------------------------------------
def sect_main_hall():
    """Audience hall: throne dais, twin lacquer columns and hanging banners."""
    m = arch.kit()
    objs = _shell(m, 9.0, 8.0, 5.5, door_w=3.2, door_h=3.0)
    objs += _rug(m, 2.4, 6.5, "#8c1d17")
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for x in (-3.2, 3.2):
        for y in (-1.5, 1.5):
            arch.column(bm_p, bm_s, x, y, 0.0, 4.6, r=0.28)
    o = util.mesh_object("Columns", bm_p, m["pillar"])
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("ColumnBases", bm_s, m["stone"])
    util.box_uv(o, 1.0)
    objs.append(o)
    # throne dais against the back wall
    bm = bmesh.new()
    util.box(bm, (3.4, 2.0, 0.5), loc=(0, 3.0, 0.25))
    d0 = util.mesh_object("Dais", bm, m["marble"], smooth=False)
    util.box_uv(d0, 0.8)
    objs.append(d0)
    bm = bmesh.new()
    util.box(bm, (1.1, 0.55, 1.0), loc=(0, 3.3, 1.0))
    util.box(bm, (1.1, 0.12, 1.5), loc=(0, 3.55, 1.25))
    for sx in (-1, 1):
        util.box(bm, (0.12, 0.55, 1.35), loc=(sx * 0.53, 3.3, 1.18))
    throne = util.mesh_object("Throne", bm, m["pillar"], smooth=False)
    util.box_uv(throne, 1.5)
    objs.append(throne)
    objs.append(util.collider("ThroneCol", (1.3, 0.8, 2.0), (0, 3.3, 1.0)))
    # the 0.5 m dais had no collider at all (the player walked through it): a block and a front ramp
    objs.append(util.collider("DaisCol", (3.4, 2.0, 0.5), (0, 3.0, 0.25)))
    objs.append(realms.ramp_collider("DaisRamp", 3.4, 0.0, 0.5, 0.6, 2.0))
    objs += _place(props.incense_burner(), (0, -2.4, 0.0), scale=0.85)
    for sx in (-1, 1):
        objs += _place(props.banner(), (sx * 3.5, 3.5, 0.0), yaw=180, scale=0.55)
    for x in (-2.5, 2.5):
        objs += _hanging_lantern((x, 1.5, 4.6))
    return objs


def elder_quarters():
    """A modest meditation chamber: a raised sleeping mat, a tea table and a scroll rack."""
    m = arch.kit()
    objs = _shell(m, 5.5, 5.0, 3.3, door_w=2.2, door_h=2.2)
    bm = bmesh.new()
    util.box(bm, (2.2, 1.8, 0.16), loc=(0, 1.55, 0.08))
    o = util.mesh_object("MeditationDais", bm, m["wood"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(realms.ramp_collider("MatRamp", 2.2, 0.0, 0.16, 0.25, 0.65))
    objs.append(util.collider("MatCol", (2.2, 1.8, 0.16), (0, 1.55, 0.08)))
    objs += _place(_cushion("#2f4d3a", 0.55, 0.1), (0, 1.55, 0.16))
    objs += _place(_table(m, 0.9, 0.55, 0.4), (0, -0.6, 0.0))
    for a in (-0.55, 0.55):
        objs += _place(_stool(m, r=0.18, h=0.28), (a, -1.3, 0.0))
    objs += _place(_shelf(m, 1.6, 1.4, 3, item_mat=util.material("scroll", color="#c7261c", rough=0.6),
                          items=4, seed=2), (-2.55, 1.2, 0.0), yaw=90)
    objs += _place(props.incense_burner(), (1.8, -1.8, 0.0), scale=0.5)
    return objs


def scripture_pavilion():
    """Ground floor of the seven-tier pagoda: tall bookshelves and a reading table."""
    m = arch.kit()
    objs = _shell(m, 7.0, 7.0, 6.0, door_w=2.6, door_h=2.6)
    scroll = util.material("shelf_scroll", color="#e7dcb8", rough=0.7)
    for x in (-2.6, -0.9, 0.9, 2.6):
        objs += _place(_shelf(m, 1.5, 3.6, 5, item_mat=scroll, items=4, seed=x), (x, 3.15, 0.0))
    for y in (2.2, -0.5):
        objs += _place(_shelf(m, 1.5, 3.6, 5, item_mat=scroll, items=4, seed=y + 40), (-3.15, y, 0.0), yaw=90)
        objs += _place(_shelf(m, 1.5, 3.6, 5, item_mat=scroll, items=4, seed=y + 80), (3.15, y, 0.0), yaw=-90)
    objs += _place(_table(m, 1.6, 1.0, 0.75), (0, -0.4, 0.0))
    for a in range(4):
        ang = R(90 * a + 45)
        objs += _place(_stool(m), (math.cos(ang) * 1.1, -0.4 + math.sin(ang) * 1.1, 0.0))
    objs += _place(lands.jade_slip(), (0.5, -0.15, 0.76))
    return objs


def alchemy_pavilion():
    """Pill furnace room: a fire-lit cauldron, herb racks and jars of reagents."""
    m = arch.kit()
    objs = _shell(m, 6.0, 6.0, 4.2, door_w=2.4, door_h=2.4, floor_mat=m["brick"])
    glass = util.material("alchemy_glass", color="#8fe0c0", rough=0.05, alpha=0.55)
    bm = bmesh.new()
    util.cylinder(bm, 0.85, 0.95, 0.35, loc=(0, 1.6, 0.18), segs=10)
    util.lathe(bm, [(0.001, 0.35), (0.4, 0.4), (0.55, 0.55), (0.6, 0.9), (0.55, 1.2), (0.6, 1.3), (0.001, 1.4)],
               segs=24, loc=(0, 1.6, 0.0))
    o = util.mesh_object("Furnace", bm, m["stone"], smooth=True)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs += _place(_brazier_fire(0.42), (0, 1.6, 1.35))
    objs.append(util.collider("FurnaceCol", (1.3, 1.3, 1.5), (0, 1.6, 0.75)))
    herb = util.material("herb_bundle", tex.foliage("#4a8a3a", 128, 91), normal_strength=0.3)
    for x, yaw in ((-2.6, 90), (2.6, -90)):
        objs += _place(_shelf(m, 3.2, 1.6, 3, item_mat=herb, items=5, seed=int(x * 10)), (x, 0.5, 0.0), yaw=yaw)
    objs += _place(_table(m, 1.6, 0.7, 0.85), (0, -1.9, 0.0))
    bm_j = bmesh.new()
    rnd = random.Random(7)
    for k in range(6):
        x = -0.6 + k * 0.24
        util.cylinder(bm_j, 0.07, 0.06, rnd.uniform(0.16, 0.28), loc=(x, -1.9, 0.85 + rnd.uniform(0.08, 0.14)), segs=8)
    objs.append(util.mesh_object("ReagentJars", bm_j, glass))
    return objs


def weapons_hall():
    """The training ground's armoury: racks of blades around a sparring ring."""
    m = arch.kit()
    objs = _shell(m, 8.5, 6.5, 4.4, door_w=3.0, door_h=2.8, floor_mat=m["stone"])
    for x, yaw in ((-3.6, 90), (3.6, -90)):
        objs += _place(props.weapon_rack(), (x, 1.2, 0.0), yaw=yaw)
    objs += _place(props.weapon_rack(), (0, 2.7, 0.0), yaw=180)
    bm = bmesh.new()
    n = 48
    ring = [V((1.9 * math.cos(2 * math.pi * k / n), 1.9 * math.sin(2 * math.pi * k / n), 0.03)) for k in range(n)]
    uv = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((0, 0, 0.03)))
    vs = [bm.verts.new(p) for p in ring]
    for k in range(n):
        f = bm.faces.new((c, vs[k], vs[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 3.9 + 0.5, loop.vert.co.y / 3.9 + 0.5)
    o = util.mesh_object("SparringRing", bm, m["marble"], smooth=False)
    objs.append(o)
    objs.append(util.collider("SparringRing", (3.9, 3.9, 0.03), (0, 0, 0.0)))
    objs += _place(props.training_dummy(), (0, -1.1, 0.0))
    return objs


def disciple_dormitory():
    """Shared sleeping quarters: four bunks, desks and a common table."""
    m = arch.kit()
    objs = _shell(m, 8.0, 6.0, 3.5, door_w=2.4, door_h=2.4)
    blanket = util.material("dorm_blanket", color="#5c6f8a", rough=0.8)
    for i, x in enumerate((-3.1, -1.05, 1.05, 3.1)):
        objs += _place(_bed(m, blanket=blanket), (x, 2.2, 0.0))
        objs += _place(_table(m, 0.7, 0.5, 0.7), (x, -0.3, 0.0))
        objs += _place(_stool(m), (x, -1.0, 0.0))
    objs += _place(_table(m, 2.2, 1.0, 0.78), (0, -2.4, 0.0))
    for sx in (-1, 1):
        objs += _place(_stool(m), (sx * 0.9, -2.9, 0.0))
    return objs


# --------------------------------------------------------------------------
# Qingshi Town
# --------------------------------------------------------------------------
def qingshi_inn():
    """The Drunken Crane Inn: a bar counter, wine jars and guest tables."""
    m = lands.kit()
    objs = _shell(m, 8.0, 7.0, 3.7, wall_mat=m["planks"], door_w=2.6, door_h=2.4)
    bm = bmesh.new()
    util.box(bm, (4.0, 0.7, 0.95), loc=(0, 2.9, 0.475))
    o = util.mesh_object("BarCounter", bm, m["old_planks"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(util.collider("BarCounterCol", (4.0, 0.7, 0.95), (0, 2.9, 0.475)))
    bm_w, bm_h = bmesh.new(), bmesh.new()
    rnd = random.Random(4)
    for k in range(5):
        lands._barrel(bm_w, bm_h, (-1.8 + k * 0.9, 3.35, 0.0), h=rnd.uniform(0.5, 0.62), r=0.2)
    objs.append(util.mesh_object("WineJars", bm_w, m["planks"], smooth=True))
    objs.append(util.mesh_object("WineJarHoops", bm_h, m["iron"], smooth=True))
    for (x, y) in ((-2.4, -0.5), (2.4, -0.5), (-2.4, -2.2), (2.4, -2.2)):
        objs += _place(_table(m, 1.1, 1.1, 0.75), (x, y, 0.0))
        for a in range(4):
            ang = R(90 * a + 45)
            objs += _place(_stool(m), (x + math.cos(ang) * 0.85, y + math.sin(ang) * 0.85, 0.0))
    for x in (-2.6, 2.6):
        objs += _hanging_lantern((x, 1.2, 3.2))
    sign_mat = util.material("inn_sign", lands.signboard(chars=4), normal_strength=0.5, double_sided=True)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(V((x, 3.24, z))) for x, z in ((-0.9, 2.2), (0.9, 2.2), (0.9, 3.0), (-0.9, 3.0))]
    f = bm.faces.new(vs)
    for loop, (uu, vv) in zip(f.loops, ((1, 0), (0, 0), (0, 1), (1, 1))):
        loop[uv].uv = (uu, vv)
    objs.append(util.mesh_object("InnSign", bm, sign_mat, smooth=False))
    return objs


def qingshi_teahouse():
    """A quiet teahouse: low tables, cushions and a serving counter."""
    m = lands.kit()
    objs = _shell(m, 6.0, 6.0, 3.3, wall_mat=m["whitewash"], door_w=2.2, door_h=2.2)
    bm = bmesh.new()
    util.box(bm, (2.2, 0.6, 0.85), loc=(0, 2.55, 0.425))
    o = util.mesh_object("TeaCounter", bm, m["wood"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(util.collider("TeaCounterCol", (2.2, 0.6, 0.85), (0, 2.55, 0.425)))
    for (x, y) in ((-1.7, -0.3), (1.7, -0.3), (0.0, -2.1)):
        objs += _place(_table(m, 0.75, 0.75, 0.4), (x, y, 0.0))
        for a, col in zip(range(4), ("#b3213a", "#2f6b4a", "#c78a2c", "#3a4f8a")):
            ang = R(90 * a + 45)
            objs += _place(_cushion(col, 0.28, 0.12), (x + math.cos(ang) * 0.55, y + math.sin(ang) * 0.55, 0.0))
    objs += _rug(m, 4.4, 4.4, "#7a5a3c")
    for x in (-1.8, 1.8):
        objs += _hanging_lantern((x, 0.5, 2.9))
    return objs


def qingshi_blacksmith():
    """A working smithy: forge, anvil and racks of half-finished blades."""
    m = lands.kit()
    steel = util.material("smithy_steel", tex.metal("#c9ced6", rough=0.25))
    objs = _shell(m, 6.0, 5.5, 3.6, wall_mat=m["blocks"], floor_mat=m["blocks"], door_w=2.6, door_h=2.6)
    bm = bmesh.new()
    util.box(bm, (1.8, 1.1, 0.7), loc=(0, 2.2, 0.35))
    util.box(bm, (1.0, 0.7, 0.3), loc=(0, 2.2, 0.85))
    o = util.mesh_object("Forge", bm, m["blocks"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs += _place(_brazier_fire(0.32), (0, 2.2, 0.86))
    objs.append(util.collider("ForgeCol", (1.8, 1.1, 1.2), (0, 2.2, 0.6)))
    bm = bmesh.new()
    util.box(bm, (0.55, 1.0, 0.45), loc=(-1.7, 0.4, 0.225))
    util.box(bm, (0.28, 0.55, 0.4), loc=(-1.7, 0.75, 0.62))
    o = util.mesh_object("Anvil", bm, steel, smooth=False)
    util.box_uv(o, 1.5)
    objs.append(o)
    objs.append(util.collider("AnvilCol", (0.6, 1.0, 1.1), (-1.7, 0.4, 0.45)))
    bm_w, bm_h = bmesh.new(), bmesh.new()
    lands._barrel(bm_w, bm_h, (-2.0, -1.8, 0.0), h=0.7, r=0.42)
    objs.append(util.mesh_object("QuenchBarrel", bm_w, m["planks"], smooth=True))
    objs.append(util.mesh_object("QuenchHoops", bm_h, m["iron"], smooth=True))
    water = util.material("quench_water", color="#3a5a6a", rough=0.1)
    bm = bmesh.new()
    util.cylinder(bm, 0.36, 0.36, 0.02, loc=(-2.0, -1.8, 0.62), segs=16)
    objs.append(util.mesh_object("QuenchWater", bm, water))
    objs.append(util.collider("QuenchBarrelCol", (0.9, 0.9, 0.7), (-2.0, -1.8, 0.35)))
    objs += _place(props.weapon_rack(), (1.8, -1.9, 0.0), yaw=180)
    return objs


def qingshi_herb_shop():
    """An apothecary: shelves of jars, drying herbs and a counter scale."""
    m = lands.kit()
    objs = _shell(m, 5.5, 5.0, 3.3, wall_mat=m["daub"], door_w=2.2, door_h=2.2)
    jar = util.material("herb_jar", color="#8a6a3a", rough=0.5)
    herb = util.material("dried_herb", tex.foliage("#8a7a3a", 128, 92), normal_strength=0.3)
    for x, yaw in ((-2.2, 90), (2.2, -90)):
        objs += _place(_shelf(m, 3.0, 1.7, 3, item_mat=jar, items=5, seed=int(x * 5)), (x, 0.6, 0.0), yaw=yaw)
    bm = bmesh.new()
    util.box(bm, (2.0, 0.6, 0.85), loc=(0, 1.9, 0.425))
    o = util.mesh_object("HerbCounter", bm, m["wood"], smooth=False)
    util.box_uv(o, 1.0)
    objs.append(o)
    objs.append(util.collider("HerbCounterCol", (2.0, 0.6, 0.85), (0, 1.9, 0.425)))
    bm_s = bmesh.new()
    util.cylinder(bm_s, 0.02, 0.02, 0.4, loc=(0.6, 1.9, 1.05), segs=6)
    util.box(bm_s, (0.5, 0.02, 0.02), loc=(0.6, 1.9, 1.25))
    for sx in (-1, 1):
        util.cylinder(bm_s, 0.14, 0.16, 0.05, loc=(0.6 + sx * 0.25, 1.9, 1.05), segs=10)
    objs.append(util.mesh_object("HerbScale", bm_s, m["bronze"]))
    objs.append(util.collider("HerbScaleCol", (0.6, 0.1, 0.85), (0.6, 1.9, 1.0)))
    bm_h = bmesh.new()
    rnd = random.Random(3)
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        tip = V((math.cos(a) * 0.12, math.sin(a) * 0.12 - 1.3, 2.6 + rnd.uniform(-0.1, 0.05)))
        util.tube(bm_h, [V((math.cos(a) * 0.12, math.sin(a) * 0.12 - 1.3, 2.9)), tip], 0.02, n=5)
    objs.append(util.mesh_object("DryingHerbs", bm_h, herb))
    return objs


# --------------------------------------------------------------------------
# hidden treasure vault (beneath the bamboo forest's ruined shrine)
# --------------------------------------------------------------------------
def hidden_vault():
    """A quest-gated treasure vault sealed beneath the forest ruins: piled
    chests, loose gold and a glowing spirit crystal vein."""
    m = lands.kit()
    objs = _shell(m, 7.0, 6.0, 4.0, wall_mat=m["ruin"], floor_mat=m["blocks"], door_w=2.2, door_h=2.4, beams=False)
    for x, y, yaw, sc in ((-0.8, 1.2, 20, 1.0), (0.8, 1.6, -35, 0.9), (0.1, 0.5, 190, 0.85)):
        objs += _place(lands.treasure_chest(), (x, y, 0.0), yaw=yaw, scale=sc)
    gold = util.material("loose_gold", tex.metal("#d4a93c", rough=0.3))
    bm = bmesh.new()
    rnd = random.Random(11)
    for k in range(40):
        x = rnd.uniform(-2.6, 2.6)
        y = rnd.uniform(-1.5, 2.4)
        util.cylinder(bm, rnd.uniform(0.05, 0.09), rnd.uniform(0.05, 0.09), 0.02, loc=(x, y, 0.011), segs=8)
    objs.append(util.mesh_object("LooseGold", bm, gold))
    objs += _place(lands.spirit_stone(seed=17), (-2.4, -1.8, 0.0), scale=1.2)
    objs += _place(lands.spirit_stone(seed=23), (2.5, -1.6, 0.0), yaw=140, scale=0.9)
    for x in (-2.9, 2.9):
        objs += _place(lands.broken_pillar(seed=int(x)), (x, 2.3, 0.0), scale=0.8)
    return objs


# --------------------------------------------------------------------------
# Celestial Sky Isles
# --------------------------------------------------------------------------
def celestial_pavilion():
    """A sanctum atop the star-gazing pavilion: a star-chart floor and a
    floating jade dais ringed by crystal light."""
    m = realms.sky_mats()
    m.setdefault("stone", m["marble"])
    m.setdefault("beam", m["beam"])
    m.setdefault("plaster", m["marble"])
    objs = _shell(m, 6.5, 6.5, 4.5, floor_mat=m["marble"], wall_mat=m["marble"], ceil_mat=m["beam"],
                 door_w=2.6, door_h=2.6, beams=False)
    star = realms._mat("star_chart_floor", realms.star_map(1024), 2.0, normal_strength=0.3)
    bm = bmesh.new()
    n = 48
    uv = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((0, 0, 0.012)))
    ring = [V((2.6 * math.cos(2 * math.pi * k / n), 2.6 * math.sin(2 * math.pi * k / n), 0.012)) for k in range(n)]
    vs = [bm.verts.new(p) for p in ring]
    for k in range(n):
        f = bm.faces.new((c, vs[k], vs[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 5.4 + 0.5, loop.vert.co.y / 5.4 + 0.5)
    objs.append(util.mesh_object("StarFloor", bm, star, smooth=False))
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for k in range(4):
        a = R(45 + 90 * k)
        arch.column(bm_p, bm_s, math.cos(a) * 2.4, math.sin(a) * 2.4, 0.0, 3.6, r=0.16)
    o = util.mesh_object("Columns", bm_p, m["jade"])
    util.box_uv(o, 1.0)
    objs.append(o)
    o = util.mesh_object("ColumnBases", bm_s, m["marble"])
    util.box_uv(o, 1.0)
    objs.append(o)
    bm = bmesh.new()
    util.lathe(bm, [(0.7, 0.0), (0.55, 0.25), (0.3, 0.32), (0.001, 0.36)], segs=16, loc=(0, 0, 0.9), cap_bottom=True)
    dais = util.mesh_object("FloatingDais", bm, m["jade"])
    util.box_uv(dais, 1.0)
    objs.append(dais)
    bm = bmesh.new()
    util.sphere(bm, 0.28, loc=(0, 0, 1.55), segs=16, rings=10)
    orb = util.mesh_object("SpiritOrb", bm, m["crystal_core"])
    objs.append(orb)
    for x, y in ((-2.6, -2.6), (2.6, -2.6), (-2.6, 2.6), (2.6, 2.6)):
        objs += _place(realms.crystal_cluster(seed=int(abs(x) * 10 + abs(y))), (x, y, 0.0), scale=0.35)
    return objs


# --------------------------------------------------------------------------
# Blood Moon Abyss
# --------------------------------------------------------------------------
def blood_abyss_shrine():
    """The ruin beneath the great blood altar: a smaller relic altar, broken
    pillars and a bone-strewn floor lit by glowing runes."""
    m = realms.abyss_mats()
    m.setdefault("plaster", m["blocks"])
    m.setdefault("stone", m["blocks"])
    m.setdefault("beam", m["blocks"])
    objs = _shell(m, 8.0, 7.0, 5.0, floor_mat=m["blocks"], wall_mat=m["blocks"], ceil_mat=m["blocks"],
                 door_w=3.0, door_h=2.8, beams=False)
    rune_mat = realms._mat("shrine_runes", realms.rune_stone(512), 3.0, normal_strength=0.5)
    bm = bmesh.new()
    n = 40
    uv = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((0, 2.2, 0.03)))
    ring = [V((2.2 * math.cos(2 * math.pi * k / n), 2.2 + 2.2 * math.sin(2 * math.pi * k / n), 0.03))
            for k in range(n)]
    vs = [bm.verts.new(p) for p in ring]
    for k in range(n):
        f = bm.faces.new((c, vs[k], vs[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 4.4 + 0.5, loop.vert.co.y / 4.4 + 0.5)
    objs.append(util.mesh_object("RuneFloor", bm, rune_mat, smooth=False))
    objs += _place(realms.blood_altar(), (0, 2.4, 0.0), scale=0.55)
    for x, y, yaw in ((-3.0, -1.5, 20), (3.0, -1.0, -30), (-2.6, 1.8, 200)):
        objs += _place(lands.broken_pillar(seed=int(x * 3 + y)), (x, y, 0.0), yaw=yaw, scale=1.1)
    objs += _place(realms.bone_pile(seed=9), (-2.2, -2.6, 0.0), scale=0.9)
    objs += _place(realms.bone_pile(seed=13), (2.4, -2.4, 0.0), yaw=110, scale=0.8)
    return objs


ASSETS = {
    "sect_main_hall": sect_main_hall,
    "elder_quarters": elder_quarters,
    "scripture_pavilion": scripture_pavilion,
    "alchemy_pavilion": alchemy_pavilion,
    "weapons_hall": weapons_hall,
    "disciple_dormitory": disciple_dormitory,
    "qingshi_inn": qingshi_inn,
    "qingshi_teahouse": qingshi_teahouse,
    "qingshi_blacksmith": qingshi_blacksmith,
    "qingshi_herb_shop": qingshi_herb_shop,
    "hidden_vault": hidden_vault,
    "celestial_pavilion": celestial_pavilion,
    "blood_abyss_shrine": blood_abyss_shrine,
}

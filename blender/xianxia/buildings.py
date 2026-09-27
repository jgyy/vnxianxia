"""Parametric Chinese / xianxia architecture: the kit behind the enlarged maps.

One set of generators builds every hall, tower, gate, stair and wall in several
styles (sect, town, temple, imperial, abyss, sky, rustic):

* ``podium``     raised stone platform with stairs on any side (real steps of
                 <= 0.17 m risers; the collision is a smooth ramp through the
                 tread centres so the player walks up without step logic)
* ``stair_run``  a free-standing stone stairway between two terrace levels
* ``hall``       columned hall: podium, bays of lattice doors and windows,
                 painted architrave, dougong bracket sets, hip, gable,
                 hip-and-gable (xieshan) or double-eave roofs with ridge beasts,
                 optional upper storey with a balcony and a name plaque
* ``tower``      stacked square/hexagonal/octagonal storeys with eaves and
                 balconies (bell/drum/treasure towers, pagodas)
* ``paifang``    memorial archways of 1-5 bays, stone or timber
* ``gate_house`` brick gate block with an arched passage and a gate tower
* ``wall_run``   straight wall segments (sect, town, fortress styles)

Conventions (as everywhere in blender/xianxia): Blender Z up, fronts face -Y
(+Z in Godot), origin at the centre of the footprint on the ground; hidden
'-convcolonly' / '-colonly' colliders. Textures are small (256 px) and tile, so
the many new building GLBs stay small; walls are solid so no floor or wall is
ever coplanar with another surface.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector

from . import arch, lands, realms, tex, util

V = Vector
R = math.radians

TEX = 256

STYLES = {
    "sect": dict(pillar="#8c1d17", tiles="#2e3d47", ridge="#2a3238", plaster="#ebe6da", wood="#4b2f1f",
                 stone="#b3aea5", brick="#77746e", paper="#efe2c4", trim="#d4a93c", beam=True),
    "town": dict(pillar="#5a3522", tiles="#3d4043", ridge="#2c2e30", plaster="#e6e1d4", wood="#4a3526",
                 stone="#a8a39a", brick="#6f6d69", paper="#e9dcbc", trim="#b88a3a", beam=False),
    "temple": dict(pillar="#9a2418", tiles="#2f6b4a", ridge="#27513a", plaster="#c9955f", wood="#4b2f1f",
                   stone="#b5afa4", brick="#7a6f66", paper="#efe2c4", trim="#d4a93c", beam=True),
    "imperial": dict(pillar="#a3241a", tiles="#c8962a", ridge="#a6771f", plaster="#a8392e", wood="#4b2f1f",
                     stone="#d8d3c8", brick="#8a4a3c", paper="#f2e6c8", trim="#e0b84e", beam=True),
    "abyss": dict(pillar="#1d1416", tiles="#221d22", ridge="#4a0f0f", plaster="#3b3034", wood="#241a1a",
                  stone="#4a4044", brick="#3a3336", paper="#7a1a12", trim="#8a1a12", beam=False, glow="#ff3018"),
    "sky": dict(pillar="#e9efe9", tiles="#3f86b8", ridge="#d8b04a", plaster="#f4f1ea", wood="#d8cbb4",
                stone="#ebe8e0", brick="#d6d2c8", paper="#f7f0da", trim="#e0b84e", beam=True),
    "rustic": dict(pillar="#6b5238", tiles="#4a4a45", ridge="#3a3a36", plaster="#b9a27c", wood="#5b4430",
                   stone="#8e8a82", brick="#6f6a60", paper="#e2d2a8", trim="#8a6a3a", beam=False),
}


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def kit(style="sect"):
    """Materials of one architectural style (names are unique per style)."""
    c = STYLES[style]
    s = style
    m = {}
    m["pillar"] = util.material(f"{s}_pillar", tex.lacquer(c["pillar"], TEX, 51, 0.2), normal_strength=0.3)
    m["wood"] = util.material(f"{s}_wood", tex.wood(c["wood"], TEX), normal_strength=0.5)
    if c["beam"]:
        m["beam"] = util.material(f"{s}_beam", _tint_beam(TEX, style), normal_strength=0.4)
    else:
        m["beam"] = util.material(f"{s}_beam", tex.wood(c["wood"], TEX, 63, rings=12), normal_strength=0.5)
    m["plaster"] = util.material(f"{s}_plaster", tex.plaster(c["plaster"], TEX), normal_strength=0.3)
    m["brick"] = util.material(f"{s}_brick", tex.bricks(c["brick"], TEX), normal_strength=0.8)
    m["stone"] = util.material(f"{s}_stone", tex.stone(c["stone"], TEX), normal_strength=0.6)
    m["marble"] = util.material(f"{s}_marble", tex.stone("#e4e1da" if s != "abyss" else "#2a2326", TEX, 72, 0.15),
                                normal_strength=0.3)
    m["tiles"] = util.material(f"{s}_tiles", tex.roof_tiles(c["tiles"], TEX), normal_strength=1.0)
    m["ridge"] = util.material(f"{s}_ridge", tex.stone(c["ridge"], 128, 73, 0.1), normal_strength=0.4)
    m["gold"] = util.material(f"{s}_trim", tex.metal(c["trim"], 128, rough=0.3))
    glow = c.get("glow")
    m["lattice"] = util.material(f"{s}_lattice", tex.lattice(c["pillar"] if s != "sky" else "#b8a070", c["paper"], TEX),
                                 normal_strength=0.6, emission=glow or "#ffcf8a",
                                 emission_strength=1.2 if glow else 0.15)
    m["plaque"] = util.material(f"{s}_plaque", tex.plaque(TEX), normal_strength=0.5)
    m["planks"] = util.material(f"{s}_planks", lands.planks(c["wood"], TEX, 405), normal_strength=0.7)
    m["dark"] = util.material("shadow", color="#0d0b0a", rough=1.0)
    return m


def _tint_beam(size, style):
    maps = tex.beam_paint(size)
    if style == "sky":
        maps["albedo"] = tex.lerp(maps["albedo"], tex.srgb("#f0ead8"), 0.55)
    elif style == "imperial":
        maps["albedo"] = tex.lerp(maps["albedo"], tex.srgb("#2a5a8a"), 0.15)
    return maps


def glow(name, color, strength=4.0):
    return util.material(name, color=color, rough=0.4, emission=color, emission_strength=strength)


def obj(name, bm, mat, uv=1.0, smooth=False):
    o = util.mesh_object(name, bm, mat, smooth=smooth)
    if uv:
        util.box_uv(o, uv)
    return o


def rotated(objs, yaw=0.0, loc=(0, 0, 0)):
    """Rotate objects about Z by yaw (radians) and move them; returns the list."""
    for o in objs:
        o.matrix_basis = Matrix.Translation(V(loc)) @ Matrix.Rotation(yaw, 4, "Z") @ o.matrix_basis
        util.apply_transform(o)
    return objs


def column(bm_p, bm_s, x, y, z0, h, r=0.25, segs=10):
    """Lacquered column (open ended: its ends are hidden in the drum base and under the beams) on a
    stone drum base."""
    util.cylinder(bm_p, r, r * 0.92, h, loc=(x, y, z0 + h / 2), segs=segs, cap=False)
    util.cylinder(bm_s, r * 1.5, r * 1.28, 0.3, loc=(x, y, z0 + 0.1), segs=8)


def bracket(bm, x, y, z, s=1.0):
    """Light dougong: bearing block, two crossing arms with small blocks, a top tie beam."""
    util.box(bm, (0.42 * s, 0.42 * s, 0.18 * s), loc=(x, y, z + 0.09 * s))
    util.box(bm, (1.2 * s, 0.2 * s, 0.16 * s), loc=(x, y, z + 0.26 * s))
    util.box(bm, (0.2 * s, 1.0 * s, 0.16 * s), loc=(x, y, z + 0.26 * s))
    util.box(bm, (1.5 * s, 0.24 * s, 0.14 * s), loc=(x, y, z + 0.44 * s))


def ramp(name, width, y0, z0, y1, z1, x=0.0, thick=0.4):
    """Walkable ramp collider whose top surface runs from (y0, z0) to (y1, z1)."""
    return realms.ramp_collider(name, width, z0, z1, y0, y1, x=x, thick=thick)


# --------------------------------------------------------------------------
# stairs and podiums
# --------------------------------------------------------------------------
RISER = 0.17
TREAD = 0.32


def steps(bm, width, rise, z0=0.0, y_top=0.0, depth_below=0.6, x=0.0, riser=RISER, tread=TREAD):
    """Visual flight climbing toward +Y and ending at y_top, from z0 up to z0 + rise.
    Returns the horizontal run. Every step is a solid block down to depth_below under its tread."""
    n = max(1, math.ceil(rise / riser - 1e-6))
    r = rise / n
    run = n * tread
    for k in range(n):
        top = z0 + r * (k + 1)
        bottom = z0 + r * k - depth_below
        y_front = y_top - run + k * tread
        util.box(bm, (width, tread + 0.02, top - bottom), loc=(x, y_front + tread / 2 + 0.01, (top + bottom) / 2))
    return run


def stair_ramp(name, width, rise, z0=0.0, y_top=0.0, x=0.0, tread=TREAD, riser=RISER):
    """Collision for steps(): a ramp through the tread centres, extended to meet the ground in front."""
    n = max(1, math.ceil(rise / riser - 1e-6))
    run = n * tread
    e = tread / 2
    return ramp(name, width, y_top - run - e, z0, y_top - e, z0 + rise, x=x)


def cheeks(bm, width, rise, run, z0=0.0, y_top=0.0, t=0.35, cap=0.25, x=0.0):
    """Sloped stone side walls of a flight (outer faces at +-(width/2 + t))."""
    for sx in (-1, 1):
        xc = x + sx * (width / 2 + t / 2)
        pts = [(y_top - run - 0.1, z0 - 0.6), (y_top + 0.05, z0 - 0.6), (y_top + 0.05, z0 + rise + cap),
               (y_top - run - 0.1, z0 + cap)]
        vs = [bm.verts.new(V((xc + dx, y, z))) for dx in (-t / 2, t / 2) for (y, z) in pts]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


SIDES = {"front": 0.0, "back": math.pi, "left": -math.pi / 2, "right": math.pi / 2}


def podium(p, m, hw, hd, h, stairs=(("front", 4.0),), rail=True, base="brick", cap="stone", sink=0.8):
    """Raised terrace (top at z = h) with flights on the given sides ((side, width), ...).

    The stairs of the "front" side descend toward -Y. Returns (objects, list of collision boxes)."""
    objs = []
    bm = bmesh.new()
    util.box(bm, (hw * 2, hd * 2, h - 0.14 + sink), loc=(0, 0, (h - 0.14 - sink) / 2))
    objs.append(obj(p + "PodiumBase", bm, m[base], uv=0.5))
    bm = bmesh.new()
    util.box(bm, (hw * 2 + 0.18, hd * 2 + 0.18, 0.14), loc=(0, 0, h - 0.07))
    objs.append(obj(p + "PodiumCap", bm, m[cap], uv=0.6))
    for side, sw in stairs:
        yaw = SIDES[side]
        edge = hd if side in ("front", "back") else hw
        bm_s, bm_c = bmesh.new(), bmesh.new()
        run = steps(bm_s, sw, h, y_top=0.0)
        cheeks(bm_c, sw, h, run)
        o1 = obj(p + "Stairs" + side, bm_s, m[cap], uv=0.6)
        o2 = obj(p + "Cheeks" + side, bm_c, m["marble" if rail else cap], uv=0.8)
        col = stair_ramp(p + "StairCol" + side, sw + 0.3, h)
        # built climbing +Y to y = 0; turn so it climbs toward the podium edge on that side
        for o in (o1, o2, col):
            # the top step ends exactly at the cap slab's edge (overlapping it, both z-fought at height h)
            o.matrix_basis = Matrix.Rotation(yaw, 4, "Z") @ Matrix.Translation(V((0, -edge - 0.11, 0)))
            util.apply_transform(o)
        objs += [o1, o2, col]
    if rail:
        objs += balustrade(p, m, hw, hd, h, [(s, w) for s, w in stairs])
    objs.append(util.collider(p + "Podium", (hw * 2, hd * 2, h + sink), (0, 0, (h - sink) / 2)))
    return objs


def balustrade(p, m, hw, hd, z, openings=(), inset=0.12, mat="marble", h=0.9):
    """Marble railing around a hw x hd rectangle at height z, open where stairs arrive."""
    bm = bmesh.new()
    cols = []
    corners = [(-hw + inset, -hd + inset), (hw - inset, -hd + inset), (hw - inset, hd - inset), (-hw + inset, hd - inset)]
    names = ["front", "right", "back", "left"]
    gaps = dict((s, w) for s, w in openings)
    for k in range(4):
        a, b = V((*corners[k], z)), V((*corners[(k + 1) % 4], z))
        runs = [(a, b)]
        if names[k] in gaps:
            mid = (a + b) / 2
            d = (b - a).normalized()
            g = gaps[names[k]] / 2 + 0.35
            runs = [(a, mid - d * g), (mid + d * g, b)]
        for (s0, s1) in runs:
            ln = (s1 - s0).length
            if ln < 0.4:
                continue
            cnt = max(1, int(ln / 1.8))
            for i in range(cnt + 1):
                q = s0.lerp(s1, i / cnt)
                util.box(bm, (0.2, 0.2, h + 0.1), loc=(q.x, q.y, z + (h + 0.1) / 2))
                util.box(bm, (0.26, 0.26, 0.1), loc=(q.x, q.y, z + h + 0.12))
            mid = (s0 + s1) / 2
            d = s1 - s0
            ang = math.atan2(d.y, d.x)
            rot = Matrix.Rotation(ang, 4, "Z")
            util.box(bm, (ln, 0.13, 0.1), loc=(mid.x, mid.y, z + h - 0.08), rot=rot)
            util.box(bm, (ln, 0.08, 0.42), loc=(mid.x, mid.y, z + 0.4), rot=rot)
            util.box(bm, (ln, 0.16, 0.1), loc=(mid.x, mid.y, z + 0.05), rot=rot)
            cols.append(util.collider(p + "Rail", (ln, 0.3, 1.2), (mid.x, mid.y, z + 0.6), rot_z=ang))
    return [obj(p + "Balustrade", bm, m[mat], uv=1.0)] + cols


def stair_run(rise=6.0, width=5.0, style="sect", landing=3.0, lanterns=False):
    """Free-standing stone stairway climbing toward -Z in Godot (+Y in Blender) from (0, 0, 0) up to
    (0, run, rise), with a landing of `landing` metres at the top; solid down to 1.2 m below the
    slope so the graded terrain underneath never shows. Collision: one ramp + the landing."""
    m = kit(style)
    objs = []
    bm_s, bm_c = bmesh.new(), bmesh.new()
    n = max(1, math.ceil(rise / RISER - 1e-6))
    run = n * TREAD
    steps(bm_s, width, rise, y_top=run, depth_below=1.2)
    util.box(bm_s, (width, landing, 1.2 + 0.001), loc=(0, run + landing / 2, rise - 0.6))
    cheeks(bm_c, width, rise, run, y_top=run)
    bm_c2 = bmesh.new()
    for sx in (-1, 1):
        util.box(bm_c2, (0.35, landing, 1.2 + 0.25), loc=(sx * (width / 2 + 0.175), run + landing / 2, rise - 0.475))
    lands.merge(bm_c, bm_c2)
    objs.append(obj("StairSteps", bm_s, m["stone"], uv=0.6))
    objs.append(obj("StairCheeks", bm_c, m["marble"] if style in ("sect", "sky", "imperial") else m["brick"], uv=0.7))
    objs.append(stair_ramp("StairRamp", width, rise, y_top=run))
    objs.append(util.collider("StairLanding", (width, landing, 0.6), (0, run + landing / 2, rise - 0.3)))
    for sx in (-1, 1):
        objs.append(util.collider("StairWall", (0.35, run + landing, rise + 1.2),
                                  (sx * (width / 2 + 0.175), (run + landing) / 2, rise / 2 - 0.3)))
    if lanterns:
        from . import props
        for y, z in ((0.4, 0.25), (run + landing * 0.5, rise + 0.25)):
            for sx in (-1, 1):
                objs += lands.transform_objs(props.stone_lantern(), loc=(sx * (width / 2 + 0.2), y, z), scale=0.55)
    return objs


# --------------------------------------------------------------------------
# roofs
# --------------------------------------------------------------------------
def ridge_beasts(bm, corners, target, h, base_z, t_max, curve, lift, lift_len, flare, count=3, s=1.0):
    """Little seated guardian beasts marching up the hip ridges from each eave corner."""
    for c in corners:
        c = V((c[0], c[1]))
        tp = V(target(c))
        for k in range(count):
            t = t_max * (0.06 + 0.075 * k)
            q = c.lerp(tp, t)
            kk = (1 - t / t_max) ** 2
            z = base_z + h * (t / t_max) ** curve + lift * kk + 0.16 * s
            d = (tp - c).normalized()
            rot = Matrix.Rotation(math.atan2(d.y, d.x), 4, "Z")
            util.box(bm, (0.2 * s, 0.13 * s, 0.2 * s), loc=(q.x, q.y, z + 0.06 * s), rot=rot)
            util.box(bm, (0.11 * s, 0.11 * s, 0.13 * s), loc=(q.x - d.x * 0.08 * s, q.y - d.y * 0.08 * s,
                                                          z + 0.2 * s), rot=rot)
        # the immortal riding a hen leads the procession at the very corner
        q = c.lerp(tp, t_max * 0.015)
        z = base_z + lift + 0.2 * s
        util.cylinder(bm, 0.05 * s, 0.07 * s, 0.3 * s, loc=(q.x, q.y, z + 0.1 * s), segs=5)


def hip_roof(p, m, cx, cy, hw, hd, h, base_z, lift=0.7, lift_len=None, beasts=3, curve=1.9, flare=0.4,
             t_max=0.97, ridges=True, ornaments=True, detail=1.0, rows=12):
    lift_len = lift_len or min(hw, hd) * 0.45
    objs = arch.rect_roof(p + "Roof", cx, cy, hw, hd, h, m, base_z, lift=lift, lift_len=lift_len, curve=curve,
                          flare=flare, t_max=t_max, ridges=ridges, ornaments=ornaments, detail=detail,
                          per_edge=16, rows=rows)
    if beasts:
        ridge = max(hw - hd, 0.0)
        corners = [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)]
        bm = bmesh.new()
        ridge_beasts(bm, corners, lambda q: (max(-ridge, min(ridge, q.x - cx)) + cx, cy), h, base_z, t_max, curve,
                     lift, lift_len, flare, beasts, detail)
        objs.append(obj(p + "RidgeBeasts", bm, m["ridge"], uv=2.0, smooth=True))
    return objs


def skirt_roof(p, m, cx, cy, hw, hd, drop, base_z, lift=0.6):
    """A single ring of eave (the lower roof of a double-eave building)."""
    return arch.roof(p + "Skirt", [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)],
                     lambda q: (max(cx - hw * 0.6, min(cx + hw * 0.6, q.x)), cy), drop * max(0.9, 0.24 * min(hw, hd)), m, base_z=base_z,
                     t_max=0.34, curve=1.3, lift=lift, lift_len=min(hw, hd) * 0.45, flare=0.4, per_edge=14, rows=5,
                     ridges=False, ornaments=True)


def xieshan_roof(p, m, cx, cy, hw, hd, h, base_z, beasts=3, lift=0.7):
    """Hip-and-gable roof: a hipped lower slope under a gabled upper roof with ornate gable faces."""
    hl = h * 0.55
    objs = arch.roof(p + "LowerRoof", [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)],
                     lambda q: (max(cx - hw + hd, min(cx + hw - hd, q.x)) if hw > hd else cx, cy), hl, m,
                     base_z=base_z, t_max=0.6, curve=1.7, lift=lift, lift_len=min(hw, hd) * 0.45, flare=0.4,
                     per_edge=16, rows=8, ridges=True, ornaments=True, top_ridge=False)
    if beasts:
        bm = bmesh.new()
        ridge = max(hw - hd, 0.0)
        ridge_beasts(bm, [(cx - hw, cy - hd), (cx + hw, cy - hd), (cx + hw, cy + hd), (cx - hw, cy + hd)],
                     lambda q: (max(-ridge, min(ridge, q.x - cx)) + cx, cy), hl, base_z, 0.6, 1.7, lift,
                     min(hw, hd) * 0.45, 0.4, beasts)
        objs.append(obj(p + "RidgeBeasts", bm, m["ridge"], uv=2.0, smooth=True))
    zt = base_z + hl - 0.12
    ghw = hw - 0.6 * min(hw, hd)
    ghd = 0.4 * hd
    gh = h - hl + 0.25
    parts, _ = lands.gable_roof(p + "Gable", ghw + 0.45, ghd + 0.55, gh, {"tiles": m["tiles"], "wood": m["wood"],
                                                                        "ridge": m["ridge"]},
                                base_z=zt, curve=1.35, lift=0.1, curl=True)
    for o in parts:
        o.location = (cx, cy, 0)
        util.apply_transform(o)
    objs += parts
    # gable faces (triangles, double-walled) under the upper roof
    bm = bmesh.new()
    for sx in (-1, 1):
        for inset in (0.0, 0.14):
            x = cx + sx * (ghw - inset)
            vs = [bm.verts.new(V((x, cy - ghd, zt))), bm.verts.new(V((x, cy + ghd, zt))),
                  bm.verts.new(V((x, cy, zt + gh * 0.96)))]
            face_out = (sx > 0) == (inset == 0.0)
            bm.faces.new(vs if face_out else list(reversed(vs)))
    objs.append(obj(p + "GableFace", bm, m["beam"], uv=0.8))
    return objs


def gable_roof(p, m, hw, hd, h, base_z, lift=0.18, curl=True, cy=0.0):
    parts, _ = lands.gable_roof(p + "Roof", hw, hd, h, {"tiles": m["tiles"], "wood": m["wood"], "ridge": m["ridge"]},
                                base_z=base_z, lift=lift, curl=curl)
    for o in parts:
        o.location = (0, cy, 0)
        util.apply_transform(o)
    return parts


# --------------------------------------------------------------------------
# halls
# --------------------------------------------------------------------------
def dougong_row(bm, pts, z, s=0.7):
    for (x, y) in pts:
        bracket(bm, x, y, z, s)


def hall(p="Hall", style="sect", w=14.0, d=9.0, col_h=4.2, bays=5, podium_h=0.9, roof="hip", veranda=1.8,
         stairs=None, rail=True, storeys=1, beasts=3, plaque=True, back_door=False, windows="lattice",
         eave=1.8, roof_h=None, brackets=True, walls="plaster", open_sides=False, podium_margin=1.4,
         sign=None):
    """A columned hall of `bays` bays (front on -Y). Returns objects (with collision)."""
    m = kit(style)
    objs = []
    hw, hd = w / 2, d / 2
    ph = podium_h
    pw, pdd = hw + podium_margin, hd + podium_margin + (veranda if veranda else 0) / 2
    pcy = -(veranda or 0) / 2
    if ph > 0:
        sw = min(w * 0.45, 6.0)
        st = stairs if stairs is not None else (("front", sw),)
        pod = podium(p, m, pw, pdd, ph, stairs=st, rail=rail and ph >= 0.6)
        objs += rotated(pod, 0.0, (0, pcy, 0))
    z0 = max(ph, 0.0)
    xs = [-hw + w * i / bays for i in range(bays + 1)]
    ys = [-hd, hd]
    nd = max(1, int(round(d / 4.0)))
    side_ys = [-hd + d * j / nd for j in range(nd + 1)]
    bm_p, bm_s = bmesh.new(), bmesh.new()
    col_r = 0.22 + 0.01 * col_h
    for x in xs:
        for y in ys:
            column(bm_p, bm_s, x, y, z0, col_h, r=col_r)
    for y in side_ys[1:-1]:
        for x in (-hw, hw):
            column(bm_p, bm_s, x, y, z0, col_h, r=col_r)
    vy = -hd - veranda if veranda else None
    if veranda:
        for x in xs:
            column(bm_p, bm_s, x, vy, z0, col_h, r=col_r * 0.9)
    objs.append(obj(p + "Columns", bm_p, m["pillar"], smooth=True))
    objs.append(obj(p + "ColumnBases", bm_s, m["stone"]))
    # walls: sides and back solid (plaster over a brick dado), front bays of lattice doors/windows
    bm_w, bm_d, bm_l, bm_f = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    t = 0.3
    if not open_sides:
        util.box(bm_w, (w, t, col_h - 0.9), loc=(0, hd, z0 + 0.9 + (col_h - 0.9) / 2))
        for sx in (-1, 1):
            util.box(bm_w, (t, d, col_h - 0.9), loc=(sx * hw, 0, z0 + 0.9 + (col_h - 0.9) / 2))
        util.box(bm_d, (w + 0.04, t + 0.04, 0.9), loc=(0, hd, z0 + 0.45))
        for sx in (-1, 1):
            util.box(bm_d, (t + 0.04, d + 0.04, 0.9), loc=(sx * hw, 0, z0 + 0.45))
    uv = bm_l.loops.layers.uv.verify()
    for yy, sgn in ((-hd, -1), (hd, 1)) if back_door else ((-hd, -1),):
        for i in range(bays):
            x0, x1 = xs[i] + col_r + 0.05, xs[i + 1] - col_r - 0.05
            door = (bays // 2 - (1 if bays >= 5 else 0)) <= i <= (bays // 2 + (1 if bays >= 5 else 0)) or bays < 3
            if sgn > 0 and not door:
                continue
            zb = z0 + (0.05 if door else 0.9)
            ztop = z0 + col_h - 0.55
            if not door:
                util.box(bm_d, (x1 - x0 + 0.1, t, 0.9), loc=((x0 + x1) / 2, yy, z0 + 0.45))
            util.box(bm_d if False else bm_f, (x1 - x0, 0.14, 0.12), loc=((x0 + x1) / 2, yy + sgn * 0.02, ztop))
            util.box(bm_w, (x1 - x0, t * 0.9, col_h - (ztop - z0) - 0.06), loc=((x0 + x1) / 2, yy,
                                                                            (ztop + 0.06 + z0 + col_h) / 2))
            # lattice panel: a thin slab so its back face never meets anything
            yy2 = yy + sgn * 0.04
            vs = [bm_l.verts.new(V((x, yy2, z))) for x, z in ((x0, zb), (x1, zb), (x1, ztop - 0.06), (x0, ztop - 0.06))]
            f = bm_l.faces.new(vs if sgn < 0 else list(reversed(vs)))
            cols = 4 if door else 3
            for loop, (uu, vv) in zip(f.loops, ((0, 0), (cols, 0), (cols, 1), (0, 1))):
                loop[uv].uv = (uu if sgn < 0 else cols - uu, vv)
            # door leaves' frames
            for k in range(cols + 1) if door else (0, cols):
                xx = x0 + (x1 - x0) * k / cols
                util.box(bm_f, (0.09, 0.12, ztop - zb), loc=(xx, yy + sgn * 0.02, (zb + ztop) / 2))
            # back of the lattice (inside): a dark panel 0.12 m behind it
            vs = [bm_f.verts.new(V((x, yy - sgn * 0.1, z))) for x, z in ((x0, zb), (x1, zb), (x1, ztop), (x0, ztop))]
            bm_f.faces.new(list(reversed(vs)) if sgn < 0 else vs)
    if windows == "lattice" and not open_sides:
        # side windows
        for sx in (-1, 1):
            for j in range(nd):
                y0_, y1_ = side_ys[j] + col_r + 0.3, side_ys[j + 1] - col_r - 0.3
                if y1_ - y0_ < 0.8:
                    continue
                zb, zt = z0 + 1.2, z0 + col_h - 0.9
                xx = sx * (hw + t / 2 + 0.02)
                vs = [bm_l.verts.new(V((xx, y, z))) for y, z in ((y0_, zb), (y1_, zb), (y1_, zt), (y0_, zt))]
                f = bm_l.faces.new(vs if sx > 0 else list(reversed(vs)))
                for loop, (uu, vv) in zip(f.loops, ((0, 0), (2, 0), (2, 1), (0, 1))):
                    loop[uv].uv = (uu, vv)
                util.box(bm_f, (0.1, y1_ - y0_ + 0.2, 0.12), loc=(xx, (y0_ + y1_) / 2, zb - 0.06))
                util.box(bm_f, (0.1, y1_ - y0_ + 0.2, 0.12), loc=(xx, (y0_ + y1_) / 2, zt + 0.06))
    wall_mat = m["plaster"] if walls == "plaster" else m[walls]
    objs.append(obj(p + "Walls", bm_w, wall_mat, uv=0.35))
    objs.append(obj(p + "Dado", bm_d, m["brick"], uv=0.5))
    objs.append(util.mesh_object(p + "Lattice", bm_l, m["lattice"], smooth=False))
    objs.append(obj(p + "Frames", bm_f, m["pillar"] if style != "town" else m["wood"], uv=1.0))
    # architrave and brackets
    top = z0 + col_h
    bm_b = bmesh.new()
    fy = vy if veranda else -hd
    for y in (fy, hd) + ((-hd,) if veranda else ()):
        util.box(bm_b, (w + 0.6, 0.36, 0.5), loc=(0, y, top + 0.1))
    for x in (-hw, hw):
        util.box(bm_b, (0.36, hd - fy + 0.6, 0.5), loc=(x, (hd + fy) / 2, top + 0.1))
    if veranda:
        for x in xs[1:-1]:
            util.box(bm_b, (0.26, veranda, 0.34), loc=(x, -hd - veranda / 2, top - 0.1))
    objs.append(obj(p + "Beams", bm_b, m["beam"], uv=1.0))
    if brackets:
        bm = bmesh.new()
        pts = [(x, fy) for x in xs] + [(x, hd) for x in xs]
        pts += [((xs[i] + xs[i + 1]) / 2, fy) for i in range(bays)] + [(x, y) for y in side_ys[1:-1] for x in (-hw, hw)]
        dougong_row(bm, pts, top + 0.35, 0.62 + 0.03 * col_h)
        objs.append(obj(p + "Brackets", bm, m["beam"], uv=1.5))
    # roof(s)
    rz = top + 0.8
    rhw, rhd = hw + eave, (hd - fy) / 2 + eave
    rcy = (hd + fy) / 2
    rh = roof_h if roof_h else max(2.4, min(rhw, rhd) * 0.5)
    if storeys > 1:
        objs += skirt_roof(p + "Low", m, 0, rcy, rhw, rhd, 1.0, rz, lift=0.55)
        # upper storey: smaller body, balcony, its own roof
        uw, ud = w * 0.8, (hd - fy) * 0.72
        uh = col_h * 0.72
        uz = rz + 1.1
        bm = bmesh.new()
        util.box(bm, (uw, ud, 0.3), loc=(0, rcy, uz - 0.15))
        objs.append(obj(p + "UpperFloor", bm, m["planks"], uv=1.0))
        bm_p2, bm_s2, bm_w2, bm_l2 = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
        uxs = [-uw / 2 + 0.4 + (uw - 0.8) * i / bays for i in range(bays + 1)]
        for x in uxs:
            for y in (rcy - ud / 2 + 0.4, rcy + ud / 2 - 0.4):
                column(bm_p2, bm_s2, x, y, uz, uh, r=col_r * 0.8)
        util.box(bm_w2, (uw - 0.8, ud - 0.8, uh - 0.2), loc=(0, rcy, uz + uh / 2))
        uvl = bm_l2.loops.layers.uv.verify()
        yf = rcy - ud / 2 + 0.4 - 0.2 - 0.03
        for i in range(bays):
            x0, x1 = uxs[i] + 0.25, uxs[i + 1] - 0.25
            vs = [bm_l2.verts.new(V((x, yf, z))) for x, z in ((x0, uz + 0.5), (x1, uz + 0.5), (x1, uz + uh - 0.6),
                                                                (x0, uz + uh - 0.6))]
            f = bm_l2.faces.new(vs)
            for loop, (uu, vv) in zip(f.loops, ((0, 0), (3, 0), (3, 1), (0, 1))):
                loop[uvl].uv = (uu, vv)
        objs.append(obj(p + "UpperColumns", bm_p2, m["pillar"], smooth=True))
        objs.append(obj(p + "UpperBases", bm_s2, m["stone"]))
        objs.append(obj(p + "UpperWalls", bm_w2, m["plaster"], uv=0.35))
        objs.append(util.mesh_object(p + "UpperLattice", bm_l2, m["lattice"], smooth=False))
        objs += balustrade(p + "Balcony", m, uw / 2, ud / 2, uz, mat="wood" if style in ("town", "rustic") else "marble",
                           h=0.8)[:1]
        for o in objs[-1:]:
            o.location.y += rcy
            util.apply_transform(o)
        bm = bmesh.new()
        dougong_row(bm, [(x, rcy - ud / 2 + 0.4) for x in uxs] + [(x, rcy + ud / 2 - 0.4) for x in uxs], uz + uh + 0.2,
                    0.55)
        objs.append(obj(p + "UpperBrackets", bm, m["beam"], uv=1.5))
        rz = uz + uh + 0.6
        rhw, rhd = uw / 2 + eave, ud / 2 + eave
        rh = roof_h if roof_h else max(2.2, min(rhw, rhd) * 0.5)
    if roof == "double":
        objs += skirt_roof(p + "D", m, 0, rcy, rhw, rhd, 1.0, rz, lift=0.6)
        bm = bmesh.new()
        util.box(bm, (rhw * 2 - eave * 2 - 0.6, rhd * 2 - eave * 2 - 0.6, 1.6), loc=(0, rcy, rz + 1.9))
        objs.append(obj(p + "Clerestory", bm, m["beam"], uv=1.0))
        bm = bmesh.new()
        dougong_row(bm, [(-rhw + eave + 0.6 + k * 1.2, rcy - rhd + eave + 0.3)
                         for k in range(int((rhw - eave) * 2 / 1.2))], rz + 2.7, 0.5)
        objs.append(obj(p + "UpperBrackets2", bm, m["beam"], uv=1.5))
        objs += hip_roof(p + "Top", m, 0, rcy, rhw * 0.88, rhd * 0.86, rh, rz + 3.0, beasts=beasts)
    elif roof == "xieshan":
        objs += xieshan_roof(p, m, 0, rcy, rhw, rhd, rh, rz, beasts=beasts)
    elif roof == "gable":
        objs += gable_roof(p, m, rhw, rhd, rh * 0.8, rz - 0.2, cy=rcy)
        bm = bmesh.new()
        for sx in (-1, 1):
            x = sx * hw
            vs = [bm.verts.new(V((x, fy - 0.2, rz - 0.3))), bm.verts.new(V((x, hd + 0.2, rz - 0.3))),
                  bm.verts.new(V((x, rcy, rz - 0.3 + rh * 0.78)))]
            bm.faces.new(vs if sx > 0 else list(reversed(vs)))
            vs = [bm.verts.new(V((x - sx * 0.25, fy - 0.2, rz - 0.3))), bm.verts.new(V((x - sx * 0.25, hd + 0.2, rz - 0.3))),
                  bm.verts.new(V((x - sx * 0.25, rcy, rz - 0.3 + rh * 0.78)))]
            bm.faces.new(list(reversed(vs)) if sx > 0 else vs)
        objs.append(obj(p + "Gables", bm, m["plaster"], uv=0.35))
    elif roof == "pyramid":
        objs += arch.poly_roof(p + "Roof", 0, rcy, max(rhw, rhd) * 1.41, 4, rh, m, base_z=rz, rot=R(45), lift=0.6,
                               lift_len=max(rhw, rhd) * 0.5, curve=1.8, per_edge=12, rows=12)
    else:
        objs += hip_roof(p, m, 0, rcy, rhw, rhd, rh, rz, beasts=beasts)
    if plaque:
        objs += arch.plaque_board(m, (0, fy - 0.3, top - 0.25), w=min(3.0, w * 0.22), h=0.8, tilt=10)
    if sign:
        objs += signboard(m, sign, (xs[1] + 0.2 if bays > 1 else -hw * 0.6, fy - 0.35, z0 + col_h * 0.55))
    # collision: the hall body and the veranda columns
    objs.append(util.collider(p + "Body", (w + 0.3, d + 0.3, col_h), (0, 0, z0 + col_h / 2)))
    if veranda:
        for x in xs:
            objs.append(util.collider(p + "VCol", (col_r * 2 + 0.1, col_r * 2 + 0.1, col_h), (x, vy, z0 + col_h / 2)))
    return objs


def signboard(m, seed, loc, vertical=True, w=0.55, h=2.0):
    """A lacquered shop sign with gilded characters hanging off the front."""
    sm = util.material(f"sign_{seed}", lands.signboard(256, 560 + seed, chars=3 + seed % 3, vertical=vertical),
                       normal_strength=0.5)
    if not vertical:
        w, h = h, w
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    x, y, z = loc
    util.box(bm, (w + 0.12, 0.08, h + 0.12), loc=(x, y + 0.06, z))
    fr = obj("SignFrame", bm, m["wood"], uv=1.0)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(V((x + dx * w / 2, y - 0.01, z + dz * h / 2))) for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for loop, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = (uu, vv)
    return [fr, util.mesh_object("Sign", bm, sm, smooth=False)]


# --------------------------------------------------------------------------
# towers
# --------------------------------------------------------------------------
def tower(p="Tower", style="sect", sides=4, storeys=3, r0=4.2, shrink=0.86, storey_h=3.6, base_h=0.9,
          base="podium", base_r=None, roof_h=None, balcony=True, spire=True, eave=1.6, door=True, open_first=False,
          contents=None):
    """Stacked storeys (square, hexagonal or octagonal plan, apothem r0 at the bottom) each with an eave;
    base 'podium' (low stepped plinth) or 'arch' (tall brick block with an arched passage, as the bell and
    drum towers). Returns (objects, top z)."""
    m = kit(style)
    objs = []
    # orientation with a face (not a corner) toward -Y, where the stairs and the door are
    rot = (-math.pi / 2 - math.pi / sides) % (2 * math.pi / sides)
    c = 1.0 / math.cos(math.pi / sides)
    z = 0.0
    if base == "arch":
        br = base_r or r0 + 2.0
        objs += arch_block(p, m, br * 2, br * 2, base_h, passage_w=3.6, passage_h=min(4.6, base_h - 1.4))
        z = base_h
        objs += battlements(p, m, br, br, z)
    elif base_h > 0:
        bm = bmesh.new()
        br = base_r or r0 + 1.4
        realms.prism(bm, [(br * c, -0.8), (br * c, base_h), ], sides=sides, rot=rot, cap_top=True, v_scale=0.5)
        objs.append(obj(p + "Plinth", bm, m["stone"], uv=0.6))
        bm = bmesh.new()
        sw = 3.2
        run = steps(bm, sw, base_h, y_top=0.0)
        o = obj(p + "PlinthSteps", bm, m["stone"], uv=0.6)
        col = stair_ramp(p + "PlinthRamp", sw + 0.3, base_h)
        for oo in (o, col):
            # steps() climbs toward +Y and ends at y = 0: put the flight in front of the plinth
            oo.matrix_basis = Matrix.Translation(V((0, -br * (1 if sides == 4 else 1.0) - 0.02, 0)))
            util.apply_transform(oo)
        objs += [o, col]
        objs.append(realms._frustum_collider(p + "PlinthCol", br, base_h, br, -0.8) if sides == 8 else
                    util.collider(p + "PlinthCol", (br * 2, br * 2, base_h + 0.8), (0, 0, (base_h - 0.8) / 2)))
        z = base_h
    r = r0
    bm_w, bm_p, bm_s, bm_l, bm_b, bm_r = (bmesh.new() for _ in range(6))
    uvl = bm_l.loops.layers.uv.verify()
    for t in range(storeys):
        h = storey_h * (1.15 if t == 0 else 1.0 - 0.03 * t)
        opened = t == 0 and open_first
        if not opened:
            realms.prism(bm_w, [(r * c * 0.94, z), (r * c * 0.94, z + h)], sides=sides, rot=rot, cap_top=False,
                         v_scale=0.3)
        else:
            realms.prism(bm_w, [(r * c * 0.9, z - 0.3), (r * c * 0.9, z + 0.25)], sides=sides, rot=rot, cap_top=True,
                         v_scale=0.3)
            if contents:
                objs += contents(z + 0.25, h, m)
        for k in range(sides):
            a = rot + 2 * math.pi * k / sides
            column(bm_p, bm_s, r * c * math.cos(a), r * c * math.sin(a), z, h, r=0.2)
        # lattice panels on each face (a door on the front face of the ground storey)
        for k in range(sides if not opened else 0):
            a0 = rot + 2 * math.pi * k / sides
            a1 = rot + 2 * math.pi * (k + 1) / sides
            pa = V((r * c * 0.94 * math.cos(a0), r * c * 0.94 * math.sin(a0), 0))
            pb = V((r * c * 0.94 * math.cos(a1), r * c * 0.94 * math.sin(a1), 0))
            mid = (pa + pb) / 2
            out = mid.normalized() * 0.03
            dvec = (pb - pa)
            ln = dvec.length
            dvec.normalize()
            front_face = abs(mid.x) < 0.3 * r and mid.y < 0
            zb = z + (0.1 if (t == 0 and front_face and door) else h * 0.28)
            zt = z + h * 0.82
            q0 = mid - dvec * ln * 0.34 + out
            q1 = mid + dvec * ln * 0.34 + out
            vs = [bm_l.verts.new(V((q.x, q.y, zz))) for q, zz in ((q0, zb), (q1, zb), (q1, zt), (q0, zt))]
            f = bm_l.faces.new(vs)
            f.normal_update()
            if f.normal.dot(mid) < 0:
                f.normal_flip()
            for loop, (uu, vv) in zip(f.loops, ((0, 0), (3, 0), (3, 1), (0, 1))):
                loop[uvl].uv = (uu, vv)
        realms.prism(bm_b, [(r * c + 0.18, z + h - 0.05), (r * c + 0.18, z + h + 0.45)], sides=sides, rot=rot,
                     cap_top=True, cap_bottom=True, v_scale=1.0)
        er = (r + eave) * c
        last = t == storeys - 1
        if not last:
            rise = 1.0 + 0.12 * r
            objs += arch.poly_roof(f"{p}Eave{t}", 0, 0, er, sides, rise, m, base_z=z + h + 0.45,
                                   rot=rot, t_max=0.4, lift=0.45, lift_len=er * 0.35, curve=1.2,
                                   per_edge=8, rows=4, ridges=False, ornaments=True)
            z_next = z + h + 0.45 + rise * 0.85
            r_next = r * shrink
            if balcony:
                bz = z + h + 0.45 + rise * 0.95
                realms.prism(bm_r, [(r_next * c + 0.9, bz - 0.2), (r_next * c + 0.9, bz)], sides=sides, rot=rot,
                             cap_top=True, cap_bottom=True, v_scale=1.0)
                for k in range(sides):
                    a0 = rot + 2 * math.pi * k / sides
                    a1 = rot + 2 * math.pi * (k + 1) / sides
                    rr = r_next * c + 0.8
                    pa = V((rr * math.cos(a0), rr * math.sin(a0), bz))
                    pb = V((rr * math.cos(a1), rr * math.sin(a1), bz))
                    d_ = pb - pa
                    mid_ = (pa + pb) / 2
                    util.box(bm_r, (d_.length + 0.08, 0.08, 0.08), loc=(mid_.x, mid_.y, bz + 0.75),
                             rot=Matrix.Rotation(math.atan2(d_.y, d_.x), 4, "Z"))
                    for i in range(3):
                        q = pa.lerp(pb, i / 3)
                        util.box(bm_r, (0.08, 0.08, 0.75), loc=(q.x, q.y, bz + 0.37))
                z_next = max(z_next, bz)
            z = z_next
            r = r_next
        else:
            z_roof = z + h + 0.45
            rh = roof_h or (r + eave) * 0.7
            objs += arch.poly_roof(f"{p}Cap", 0, 0, er, sides, rh, m, base_z=z_roof, rot=rot, lift=0.6,
                                   lift_len=er * 0.4, curve=1.7, per_edge=10, rows=10, ornaments=not spire)
            z = z_roof + rh
    objs.append(obj(p + "Walls", bm_w, m["plaster"], uv=0.35))
    objs.append(obj(p + "Pillars", bm_p, m["pillar"], smooth=True))
    objs.append(obj(p + "PillarBases", bm_s, m["stone"]))
    objs.append(util.mesh_object(p + "Windows", bm_l, m["lattice"], smooth=False))
    objs.append(obj(p + "Beams", bm_b, m["beam"], uv=1.0))
    if balcony and storeys > 1:
        objs.append(obj(p + "Balconies", bm_r, m["wood"] if style in ("town", "rustic", "abyss") else m["pillar"], uv=1.0))
    if spire:
        bm = bmesh.new()
        prof = [(0.35, 0), (0.3, 0.3)]
        for k in range(7):
            prof += [(0.32 - k * 0.03, 0.5 + k * 0.42), (0.22 - k * 0.02, 0.7 + k * 0.42)]
        prof += [(0.18, 3.6), (0.35, 3.9), (0.2, 4.2), (0.001, 4.7)]
        util.lathe(bm, prof, segs=12, loc=(0, 0, z - 0.4), cap_bottom=True)
        objs.append(obj(p + "Spire", bm, m["gold"], smooth=True))
    objs.append(util.collider(p + "Body", (r0 * 2 * 0.94, r0 * 2 * 0.94, max(z - (base_h if base == "arch" else 0), 1)),
                              (0, 0, (z + (base_h if base == "arch" else 0)) / 2)))
    return objs, z


def arch_block(p, m, w, d, h, passage_w=4.0, passage_h=4.5, mat="brick"):
    """Brick block with an arched passage through it along Y (walkable); collision leaves the passage open."""
    objs = []
    hw, hd = w / 2, d / 2
    pw = passage_w / 2
    spring = passage_h - pw
    outline = [(-hw, -0.6), (-pw, -0.6), (-pw, spring)]
    for k in range(1, 12):
        a = math.pi - math.pi * k / 12
        outline.append((pw * math.cos(a), spring + pw * math.sin(a)))
    outline += [(pw, spring), (pw, -0.6), (hw, -0.6), (hw, h), (-hw, h)]
    # the outline has a notch: split it into three convex prisms (left pier, right pier, the arch top)
    bm = bmesh.new()
    lands.extrude_outline(bm, [(-hw, -0.6), (-pw, -0.6), (-pw, h), (-hw, h)], -hd, hd)
    lands.extrude_outline(bm, [(pw, -0.6), (hw, -0.6), (hw, h), (pw, h)], -hd, hd)
    top = [(-pw, spring)] + [(pw * math.cos(math.pi - math.pi * k / 12), spring + pw * math.sin(math.pi - math.pi * k / 12))
                             for k in range(1, 12)] + [(pw, spring), (pw, h), (-pw, h)]
    tmp = bmesh.new()
    lands.extrude_outline(tmp, top, -hd, hd)
    lands.merge(bm, tmp)
    objs.append(obj(p + "ArchBlock", bm, m[mat], uv=0.5))
    # stone voussoir ring on both faces
    bm = bmesh.new()
    for y in (-hd - 0.06, hd + 0.06):
        path = [V((pw * math.cos(math.pi - math.pi * k / 16), y, spring + pw * math.sin(math.pi - math.pi * k / 16)))
                for k in range(17)]
        path = [V((-pw, y, 0.0))] + path + [V((pw, y, 0.0))]
        util.tube(bm, path, (0.32, 0.1), n=4, power=4.0, up=(0, 1, 0))
    objs.append(obj(p + "ArchRing", bm, m["stone"], uv=0.8))
    objs.append(util.collider(p + "PierL", (hw - pw, d, h + 0.6), (-(hw + pw) / 2, 0, (h - 0.6) / 2)))
    objs.append(util.collider(p + "PierR", (hw - pw, d, h + 0.6), ((hw + pw) / 2, 0, (h - 0.6) / 2)))
    objs.append(util.collider(p + "Lintel", (passage_w, d, h - passage_h), (0, 0, (h + passage_h) / 2)))
    return objs


def battlements(p, m, hw, hd, z, t=0.5, h=1.1, mat="brick"):
    bm = bmesh.new()
    for (ax, ay, bx, by) in ((-hw, -hd, hw, -hd), (hw, -hd, hw, hd), (hw, hd, -hw, hd), (-hw, hd, -hw, -hd)):
        a, b = V((ax, ay, 0)), V((bx, by, 0))
        ln = (b - a).length
        d = (b - a).normalized()
        n = int(ln / 1.4)
        inward = V((-d.y, d.x, 0))
        util.box(bm, (ln if abs(d.x) > 0.5 else t, t if abs(d.x) > 0.5 else ln, 0.5),
                 loc=((a + b).x / 2 + inward.x * t / 2, (a + b).y / 2 + inward.y * t / 2, z + 0.25))
        for k in range(n):
            if k % 2:
                continue
            q = a + d * (ln * (k + 0.5) / n) + inward * t / 2
            util.box(bm, (ln / n if abs(d.x) > 0.5 else t, t if abs(d.x) > 0.5 else ln / n, h - 0.5),
                     loc=(q.x, q.y, z + 0.5 + (h - 0.5) / 2))
    return [obj(p + "Battlements", bm, m[mat], uv=0.5)]


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------
def paifang(p="Paifang", style="sect", bays=3, span=10.0, height=7.5, material="wood", roofs=True, plaque=True):
    """Memorial archway: bays openings over `span` metres, roofs over every bay (the middle one higher)."""
    m = kit(style)
    objs = []
    n = bays + 1
    xs = [-span / 2 + span * i / bays for i in range(n)]
    mid = bays // 2
    bm_p, bm_s = bmesh.new(), bmesh.new()
    pm = m["pillar"] if material == "wood" else m["stone"]
    for i, x in enumerate(xs):
        central = i in (mid, mid + 1)
        h = height if central else height * 0.78
        if material == "wood":
            column(bm_p, bm_s, x, 0, 0.0, h, r=0.3)
        else:
            util.box(bm_p, (0.7, 0.7, h), loc=(x, 0, h / 2))
        util.box(bm_s, (1.0, 1.9, 1.2), loc=(x, 0, 0.6))
        util.box(bm_s, (0.8, 1.6, 0.25), loc=(x, 0, 1.32))
    objs.append(obj(p + "Pillars", bm_p, pm, smooth=material == "wood"))
    objs.append(obj(p + "Plinths", bm_s, m["stone"], uv=0.8))
    bm_b = bmesh.new()
    bm_d = bmesh.new()
    for i in range(bays):
        x0, x1 = xs[i], xs[i + 1]
        central = i == mid
        top = height if central else height * 0.78
        cx = (x0 + x1) / 2
        util.box(bm_b, (x1 - x0 + 0.3, 0.5, 0.55), loc=(cx, 0, top - 1.2))
        util.box(bm_b, (x1 - x0 + 0.3, 0.45, 0.4), loc=(cx, 0, top - 2.4))
        if plaque and central:
            pass
        k = max(2, int((x1 - x0) / 0.9))
        for j in range(k):
            bracket(bm_d, x0 + (x1 - x0) * (j + 0.5) / k, 0, top - 0.95, 0.45)
    objs.append(obj(p + "Beams", bm_b, m["beam"] if material == "wood" else m["stone"], uv=1.0))
    objs.append(obj(p + "Brackets", bm_d, m["beam"] if material == "wood" else m["stone"], uv=1.5))
    if roofs:
        for i in range(bays):
            x0, x1 = xs[i], xs[i + 1]
            central = i == mid
            top = height if central else height * 0.78
            objs += hip_roof(f"{p}R{i}", m, (x0 + x1) / 2, 0, (x1 - x0) / 2 + 0.7, 1.15, 1.2, top - 0.5, lift=0.4,
                             lift_len=0.9, beasts=2 if central else 0, detail=0.6, rows=6)
    if plaque:
        cx = (xs[mid] + xs[mid + 1]) / 2
        objs += arch.plaque_board(m, (cx, -0.32, height - 1.8), w=min(2.6, (xs[1] - xs[0]) * 0.7), h=0.8, tilt=0)
    for x in xs:
        objs.append(util.collider(p + "Pier", (1.0, 1.9, height), (x, 0, height / 2)))
    return objs


def gate_house(p="CityGate", style="town", w=22.0, d=12.0, h=8.5, tower_storeys=2):
    """City gate: brick block with an arched passage (walkable, 5 m wide), battlements and a gate tower."""
    m = kit(style)
    objs = arch_block(p, m, w, d, h, passage_w=5.0, passage_h=6.0)
    objs += battlements(p, m, w / 2, d / 2, h)
    objs += hall(p + "Tower", style, w=w * 0.62, d=d * 0.5, col_h=3.4, bays=5, podium_h=0.0, roof="xieshan",
                 veranda=1.2, storeys=tower_storeys, beasts=3, plaque=True, eave=1.4)
    for o in objs[-80:]:
        pass
    # lift the tower onto the block
    tower_objs = [o for o in objs if o.name.startswith(p + "Tower")]
    for o in tower_objs:
        o.location.z += h
        util.apply_transform(o)
    return objs


def wall_segment(style="town", length=8.0, h=5.0, t=1.6, crenel=True):
    """Straight wall (along X) on a stone plinth, with a walk, merlons or a tiled coping."""
    m = kit(style)
    objs = []
    bm = bmesh.new()
    util.box(bm, (length, t + 0.3, 1.0), loc=(0, 0, -0.1))
    objs.append(obj("WallPlinth", bm, m["stone"], uv=0.5))
    bm = bmesh.new()
    realms.tapered_box(bm, -length / 2, length / 2, -t / 2, t / 2, 0.4, h, sides=(0, 0, 0.2, 0.2))
    objs.append(obj("WallBody", bm, m["brick"] if style != "sect" else m["plaster"], uv=0.4))
    if crenel:
        bm = bmesh.new()
        util.box(bm, (length, 0.5, 0.5), loc=(0, -t / 2 + 0.45, h + 0.25))
        n = int(length / 1.6)
        for k in range(n):
            if k % 2 == 0:
                util.box(bm, (length / n, 0.5, 0.6), loc=(-length / 2 + length * (k + 0.5) / n, -t / 2 + 0.45, h + 0.8))
        util.box(bm, (length, 0.35, 0.35), loc=(0, t / 2 - 0.37, h + 0.17))
        objs.append(obj("WallMerlons", bm, m["brick"], uv=0.5))
    else:
        bm = bmesh.new()
        util.box(bm, (length + 0.2, t + 0.5, 0.25), loc=(0, 0, h + 0.12))
        objs.append(obj("WallCoping", bm, m["tiles"], uv=0.8))
    objs.append(util.collider("WallCol", (length, t + 0.3, h + 1.2), (0, 0, (h + 1.2) / 2)))
    return objs


# --------------------------------------------------------------------------
# the sect's landmarks
# --------------------------------------------------------------------------
def martial_stage(hw=10.0, h=1.2):
    """Raised square sparring stage with flights on all four sides, a rune-inlaid floor ring and
    banner poles at the corners."""
    m = kit("sect")
    objs = podium("Stage", m, hw, hw, h, stairs=[(s, 5.0) for s in ("front", "back", "left", "right")], rail=False,
                  base="stone", cap="stone")
    rc = realms.rune_stone(256, 434, "#8f8b85", "#6ff2ff", cols=6, rows=1, frame=False)
    ring = util.material("stage_runes", rc, emission_map=rc["emit"], emission_strength=1.5, normal_strength=0.5)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    # a square ring of rune slabs 2 cm proud of the floor (its own raised strip, not a coplanar decal)
    for k in range(4):
        rot = Matrix.Rotation(R(90 * k), 4, "Z")
        vs = util.box(bm, (hw * 2 - 3.0, 0.8, 0.04), loc=(0, 0, 0))
        bmesh.ops.transform(bm, matrix=rot @ Matrix.Translation(V((0, -hw + 1.9, h + 0.02))), verts=vs)
    objs.append(obj("RuneRing", bm, ring, uv=0.5))
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.cylinder(bm, 0.12, 0.12, 7.0, loc=(sx * (hw - 0.5), sy * (hw - 0.5), h + 3.5), segs=8)
            util.sphere(bm, 0.2, loc=(sx * (hw - 0.5), sy * (hw - 0.5), h + 7.1), segs=8, rings=5)
    objs.append(obj("Poles", bm, m["gold"], uv=1.0, smooth=True))
    flag = util.material("stage_flag", tex.silk("#1f3a6a", "#d8c890", 256, 33), double_sided=True, normal_strength=0.3)
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (0.02, 1.2, 3.0), loc=(sx * (hw - 0.5), sy * (hw - 0.5) + 0.62, h + 5.2))
    objs.append(obj("Flags", bm, flag, uv=0.5))
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs.append(util.collider("Pole", (0.3, 0.3, 7.0), (sx * (hw - 0.5), sy * (hw - 0.5), h + 3.5)))
    return objs


def arena_stands(length=24.0, tiers=5, rise=0.5, tread=0.9, style="sect"):
    """Straight block of stone seating tiers (front on -Y), with a central aisle stair (ramp) and a
    parapet along the top."""
    m = kit(style)
    objs = []
    depth = tiers * tread
    bm = bmesh.new()
    aisle = 2.0
    for k in range(tiers):
        z = rise * (k + 1)
        y0 = -depth / 2 + k * tread
        for sx in (-1, 1):
            seg = (length - aisle) / 2
            util.box(bm, (seg, depth - k * tread, z + 0.4), loc=(sx * (aisle / 2 + seg / 2), y0 + (depth - k * tread) / 2,
                                                                (z - 0.4) / 2))
    objs.append(obj("Tiers", bm, m["stone"], uv=0.6))
    bm = bmesh.new()
    run = steps(bm, aisle, rise * tiers, y_top=0.0)
    o = obj("AisleSteps", bm, m["stone"], uv=0.6)
    col = stair_ramp("AisleRamp", aisle, rise * tiers)
    for oo in (o, col):
        oo.location.y += depth / 2
        util.apply_transform(oo)
    objs += [o, col]
    del run
    bm = bmesh.new()
    util.box(bm, (length, 0.4, 1.0), loc=(0, depth / 2 + 0.2, rise * tiers + 0.5))
    objs.append(obj("Parapet", bm, m["marble"], uv=0.8))
    for sx in (-1, 1):
        seg = (length - aisle) / 2
        for k in range(tiers):
            z = rise * (k + 1)
            y0 = -depth / 2 + k * tread
            objs.append(util.collider("Tier", (seg, depth - k * tread, z + 0.4),
                                      (sx * (aisle / 2 + seg / 2), y0 + (depth - k * tread) / 2, (z - 0.4) / 2)))
    objs.append(util.collider("Parapet", (length, 0.4, 1.0), (0, depth / 2 + 0.2, rise * tiers + 0.5)))
    return objs


def rune_pillar():
    """A carved stone pillar with a column of glowing cyan runes (the formation hall's ring)."""
    rs = realms.rune_stone(256, 435, "#9a968c", "#6ff2ff", cols=1, rows=8, frame=True)
    mat = util.material("rune_pillar", rs, emission_map=rs["emit"], emission_strength=2.5, normal_strength=0.6)
    m = kit("sect")
    bm = bmesh.new()
    realms.prism(bm, [(0.55, 0.3), (0.5, 4.6)], sides=8, rot=R(22.5), cap_top=False)
    objs = [util.mesh_object("Pillar", bm, mat, smooth=False)]
    bm = bmesh.new()
    realms.prism(bm, [(0.85, -0.3), (0.85, 0.3), (0.6, 0.35)], sides=8, rot=R(22.5), cap_top=True)
    realms.prism(bm, [(0.7, 4.55), (0.75, 4.9), (0.3, 5.3), (0.001, 5.4)], sides=8, rot=R(22.5), cap_top=False,
                 cap_bottom=True)
    objs.append(obj("PillarCaps", bm, m["stone"], uv=0.8))
    objs.append(util.collider("Pillar", (1.2, 1.2, 5.0), (0, 0, 2.4)))
    return objs


def pill_kiln():
    """A great bronze pill furnace: a three-legged gourd cauldron on an octagonal stone hearth,
    fire glowing through its vents, a lid crowned with a flame finial."""
    m = kit("sect")
    bronze = util.material("kiln_bronze", tex.metal("#7a5a2e", 256, rough=0.35, patina="#3f6a5a", patina_amt=0.35),
                           normal_strength=0.6)
    fire = glow("kiln_flame", "#ff7a2a", 4.0)
    objs = []
    bm = bmesh.new()
    realms.prism(bm, [(3.0, -0.4), (3.0, 0.5), (2.6, 0.5), (2.6, 0.7)], sides=8, rot=R(22.5), cap_top=True)
    objs.append(obj("Hearth", bm, m["stone"], uv=0.6))
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 1.2), (1.2, 1.25), (1.8, 1.9), (1.9, 2.6), (1.5, 3.3), (0.9, 3.6), (1.1, 3.8), (1.4, 4.3),
                    (1.2, 4.9), (0.6, 5.2), (0.3, 5.6), (0.15, 6.2), (0.001, 6.4)], segs=20, cap_bottom=True)
    for k in range(3):
        a = 2 * math.pi * k / 3
        util.tube(bm, [V((math.cos(a) * 1.3, math.sin(a) * 1.3, 1.5)), V((math.cos(a) * 1.7, math.sin(a) * 1.7, 0.7))],
                  0.22, n=8)
    for sx in (-1, 1):
        ring = [V((sx * (1.9 + 0.35 * math.cos(t)), 0, 3.0 + 0.35 * math.sin(t))) for t in
                [2 * math.pi * i / 12 for i in range(13)]]
        util.tube(bm, ring, 0.07, n=5, closed_ends=False)
    objs.append(obj("Cauldron", bm, bronze, uv=0.8, smooth=True))
    bm = bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6
        util.box(bm, (0.5, 0.1, 0.35), loc=(math.cos(a) * 1.87, math.sin(a) * 1.87, 2.3),
                 rot=Matrix.Rotation(a + math.pi / 2, 4, "Z"))
    util.sphere(bm, 0.9, loc=(0, 0, 0.95), segs=10, rings=5, scale=(1, 1, 0.4))
    objs.append(obj("Fire", bm, fire, uv=None, smooth=True))
    objs.append(realms._frustum_collider("Hearth", 2.6, 0.7, 3.0, -0.4))
    objs.append(util.collider("Cauldron", (3.6, 3.6, 5.5), (0, 0, 3.4)))
    return objs


def beast_pen(w=12.0, d=8.0):
    """A wooden paddock with a gate gap, a thatched shelter and a water trough."""
    from . import buildings_wild as W
    m = kit("rustic")
    objs = []
    bm = bmesh.new()
    posts = []
    for (ax, ay, bx, by) in ((-w / 2, -d / 2, w / 2, -d / 2), (w / 2, -d / 2, w / 2, d / 2), (w / 2, d / 2, -w / 2, d / 2),
                             (-w / 2, d / 2, -w / 2, -d / 2)):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 2.0))
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            if ay == -d / 2 and by == -d / 2 and abs((t0 + t1) / 2 - 0.5) < 0.12:
                continue       # the gate gap on the front
            p0 = V((ax + (bx - ax) * t0, ay + (by - ay) * t0, 0))
            p1 = V((ax + (bx - ax) * t1, ay + (by - ay) * t1, 0))
            mid = (p0 + p1) / 2
            dvec = p1 - p0
            rot = Matrix.Rotation(math.atan2(dvec.y, dvec.x), 4, "Z")
            for z in (0.5, 1.0):
                util.box(bm, (dvec.length + 0.1, 0.08, 0.12), loc=(mid.x, mid.y, z), rot=rot)
            posts.append(p0)
            objs.append(util.collider("Fence", (dvec.length, 0.3, 1.3), (mid.x, mid.y, 0.65),
                                      rot_z=math.atan2(dvec.y, dvec.x)))
    for p in posts:
        util.box(bm, (0.16, 0.16, 1.3), loc=(p.x, p.y, 0.55))
    objs.insert(0, obj("Fence", bm, m["wood"], uv=1.0))
    hut = W.thatched_roof("Shelter", W.rustic(), 2.0, 1.4, 1.2, 2.2, 0.4)
    bm = bmesh.new()
    for (x, y) in ((-2, -1.4), (2, -1.4), (-2, 1.4), (2, 1.4)):
        util.box(bm, (0.14, 0.14, 2.3), loc=(x, y, 1.1))
    objs.append(obj("ShelterPosts", bm, m["wood"], uv=1.0))
    for o in hut + objs[-1:]:
        o.location += V((w / 2 - 3.0, d / 2 - 2.2, 0))
        util.apply_transform(o)
    objs += hut
    bm = bmesh.new()
    util.box(bm, (2.0, 0.6, 0.5), loc=(-w / 2 + 2.0, d / 2 - 1.0, 0.25))
    objs.append(obj("Trough", bm, m["stone"], uv=1.0))
    return objs


def waterfall(height=24.0, width=9.0):
    """A waterfall sheet pouring over a lip (faces -Y) into a foaming plunge: curved translucent water,
    white foam at the foot, mist blobs and wet rocks. No collision."""
    s = 256
    n = tex.fbm(s, 8, 5, 0.55, 171, stretch=8)
    streak = tex.sstep(0.35, 0.8, n)
    col = tex.lerp(tex.srgb("#6fa8b8"), tex.srgb("#f2f8fa"), streak)
    maps = tex.result(col, 0.1, 0.0, n)
    water = util.material("fall_water", maps, alpha=0.82, normal_strength=0.4, emission="#cfe8f0",
                          emission_strength=0.25, double_sided=True)
    foam = util.material("fall_foam", tex.plaster("#f4f8fa", 128, 109), emission="#e8f4f8", emission_strength=0.3,
                         normal_strength=0.3)
    rockm = util.material("wet_rock", tex.stone("#4a4a46", 256, 79, 0.2), normal_strength=1.2)
    objs = []
    bm = bmesh.new()
    rows = []
    for j in range(15):
        t = j / 14
        z = height * (1 - t)
        y = -0.6 - 2.2 * t * t
        rows.append([V((x * (1 + 0.25 * t), y, z)) for x in [-width / 2 + width * i / 8 for i in range(9)]])
    util.loft(bm, rows, closed=False, uv_scale=(1.5, 0.12))
    objs.append(util.mesh_object("FallSheet", bm, water, smooth=True))
    bm = bmesh.new()
    rnd = random.Random(9)
    for k in range(9):
        lands.rock(bm, (rnd.uniform(-width * 0.6, width * 0.6), -3.2 + rnd.uniform(-1, 1), 0.1), (1.6, 1.2, 0.7), k, 0.3, 1)
    objs.append(obj("Foam", bm, foam, uv=0.8, smooth=True))
    bm = bmesh.new()
    for k in range(10):
        a = rnd.uniform(0, math.pi)
        lands.rock(bm, (math.cos(a) * (width * 0.7 + 2), -3.0 - math.sin(a) * 4.0, 0.0), (1.4, 1.2, 1.0), 20 + k, 0.3, 2)
        objs.append(util.collider("Rock", (2.4, 2.0, 1.4), (math.cos(a) * (width * 0.7 + 2), -3.0 - math.sin(a) * 4.0, 0.3)))
    objs.insert(2, obj("Rocks", bm, rockm, uv=0.7, smooth=True))
    return objs


def ancestral_tomb():
    """An ancestor's tomb: a round earthen mound in a stone retaining ring, a stone offering table and
    an inscribed tablet in front (front on -Y)."""
    m = kit("sect")
    grass = util.material("tomb_grass", tex.grass(256, 125), normal_strength=0.6)
    objs = []
    bm = bmesh.new()
    res = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=8, radius=1.0)
    for v in res["verts"]:
        v.co = V((v.co.x * 4.2, v.co.y * 4.2, max(v.co.z, -0.1) * 2.4 + 0.6))
    objs.append(obj("Mound", bm, grass, uv=0.4, smooth=True))
    bm = bmesh.new()
    realms.prism(bm, [(4.6, -0.4), (4.6, 1.0), (4.3, 1.1), (4.2, 0.7)], sides=24, rot=0, cap_top=False, v_scale=0.5)
    objs.append(obj("Ring", bm, m["stone"], uv=0.6, smooth=True))
    ins = lands.inscription(256, 473, "#8a877e", cols=3, rows=6)
    bm = bmesh.new()
    util.box(bm, (1.6, 0.35, 2.2), loc=(0, -4.75, 1.1))
    objs.append(util.mesh_object("Tablet", bm, util.material("tomb_tablet", ins, normal_strength=0.8), smooth=False))
    util.box_uv(objs[-1], 0.45)
    bm = bmesh.new()
    util.box(bm, (2.0, 0.9, 0.7), loc=(0, -6.0, 0.35))
    util.box(bm, (1.8, 0.8, 0.2), loc=(0, -6.0, 0.8))
    objs.append(obj("Offering", bm, m["marble"], uv=0.8))
    objs.append(util.collider("Mound", (8.6, 8.6, 2.6), (0, 0, 1.2)))
    objs.append(util.collider("Tablet", (1.8, 0.5, 2.2), (0, -4.75, 1.1)))
    objs.append(util.collider("Offering", (2.0, 0.9, 0.9), (0, -6.0, 0.45)))
    return objs


def sword_tomb(seed=5, count=46, radius=9.0):
    """The sword tomb: old blades thrust into the rock at every angle around a stone of names."""
    rnd = random.Random(seed)
    steel = util.material("old_steel", tex.metal("#8a8a88", 128, rough=0.45, patina="#6a4a2e", patina_amt=0.35))
    hilt = util.material("sword_hilt", tex.wood("#3a2418", 128, 65))
    bm_b, bm_h = bmesh.new(), bmesh.new()
    for k in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        d = radius * math.sqrt(rnd.uniform(0.08, 1.0))
        p = V((math.cos(a) * d, math.sin(a) * d, 0))
        tilt = V((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), 1)).normalized()
        rot = tilt.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Rotation(rnd.uniform(0, 3.1), 4, "Z")
        ln = rnd.uniform(0.9, 1.4)
        util.box(bm_b, (0.08, 0.012, ln), loc=p + tilt * (ln / 2 - 0.25), rot=rot)
        util.box(bm_h, (0.34, 0.06, 0.06), loc=p + tilt * (ln - 0.25), rot=rot)
        util.box(bm_h, (0.04, 0.04, 0.3), loc=p + tilt * (ln - 0.1), rot=rot)
    objs = [obj("Blades", bm_b, steel, uv=1.0), obj("Hilts", bm_h, hilt, uv=1.0)]
    from . import lands as L
    objs += L.transform_objs(L.stone_stele(), loc=(0, 0, 0))
    return objs


def _bell(z, h, m):
    return lands.transform_objs(lands.bronze_bell(), loc=(0, 0, z), scale=1.25)


def _drum(z, h, m):
    """A great red war drum on a lacquered stand, its hide facing -Y."""
    skin = util.material("drum_skin", tex.leather("#d8c8a0", 128, 12), normal_strength=0.3)
    bm, bm_s = bmesh.new(), bmesh.new()
    util.lathe(bm, [(1.0, -0.8), (1.25, -0.4), (1.3, 0.0), (1.25, 0.4), (1.0, 0.8)], segs=20)
    for v in bm.verts:
        v.co = V((v.co.x, v.co.z, v.co.y))
    realms.disc(bm_s, (0, 0), 1.0, 20, z=0.0)
    for v in bm_s.verts:
        v.co = V((v.co.x, -0.8, v.co.y))
    for f in bm_s.faces:
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    stand = bmesh.new()
    for sx in (-1, 1):
        util.box(stand, (0.15, 0.15, 2.2), loc=(sx * 1.2, 0, 1.1))
    util.box(stand, (2.6, 0.2, 0.2), loc=(0, 0, 0.2))
    drum = obj("Drum", bm, m["pillar"], uv=1.0, smooth=True)
    head = obj("DrumHead", bm_s, skin, uv=None)
    for o in (drum, head):
        o.location = (0, 0, 1.9)
        util.apply_transform(o)
    objs = [drum, head, obj("DrumStand", stand, m["wood"], uv=1.0)]
    return lands.transform_objs(objs, loc=(0, 0, z))


def cottage():
    return hall("Cottage", "sect", w=8.0, d=6.0, col_h=3.2, bays=3, podium_h=0.45, roof="xieshan", veranda=1.2,
                beasts=0, plaque=False, rail=False, brackets=False, eave=1.2)


# --------------------------------------------------------------------------
# catalogue (the sect's new buildings; town/wild/abyss/sky live in the sibling modules)
# --------------------------------------------------------------------------
def _tower(**kw):
    return tower(**kw)[0]


ASSETS = {
    "outer_sect_hall": lambda: hall("OuterHall", "sect", w=22.0, d=13.0, col_h=5.2, bays=7, podium_h=1.5,
                                    roof="double", veranda=2.2, beasts=5),
    "mission_hall": lambda: hall("MissionHall", "sect", w=16.0, d=10.0, col_h=4.4, bays=5, podium_h=1.0,
                                 roof="xieshan", veranda=2.0, beasts=3),
    "sect_refectory": lambda: hall("Refectory", "sect", w=26.0, d=9.0, col_h=3.8, bays=8, podium_h=0.6,
                                   roof="gable", veranda=1.6, beasts=0, plaque=True, stairs=(("front", 4.0),)),
    "bell_tower": lambda: _tower(p="BellTower", style="sect", sides=4, storeys=2, r0=3.4, storey_h=3.4,
                                 base="arch", base_h=6.5, base_r=5.2, spire=False, eave=1.5, open_first=True,
                                 contents=_bell),
    "treasure_tower": lambda: _tower(p="TreasureTower", style="sect", sides=8, storeys=9, r0=4.6, shrink=0.9,
                                     storey_h=3.3, base_h=1.2, base_r=7.0, eave=1.5),
    "inner_sect_gate": lambda: paifang("InnerGate", "sect", bays=3, span=12.0, height=8.5),
    "stone_stairs_14": lambda: stair_run(14.0, 7.0, "sect"),
    "drum_tower": lambda: _tower(p="DrumTower", style="sect", sides=4, storeys=2, r0=3.4, storey_h=3.4,
                                 base="arch", base_h=6.5, base_r=5.2, spire=False, eave=1.5, open_first=True,
                                 contents=_drum),
    "contribution_pavilion": lambda: hall("Contribution", "sect", w=12.0, d=9.0, col_h=3.8, bays=5, podium_h=1.0,
                                          roof="hip", veranda=1.6, storeys=2, beasts=3),
    "dormitory_row": lambda: hall("Dorm", "sect", w=18.0, d=7.0, col_h=3.2, bays=6, podium_h=0.5, roof="gable",
                                  veranda=1.4, beasts=0, plaque=False, rail=False, brackets=False),
    "formation_hall": lambda: _tower(p="FormationHall", style="sect", sides=8, storeys=1, r0=7.0, storey_h=5.0,
                                     base_h=1.2, base_r=9.5, spire=True, eave=2.0),
    "martial_stage": martial_stage,
    "arena_stands": arena_stands,
    "formation_pillar": rune_pillar,
    "pill_kiln": pill_kiln,
    "beast_pen": beast_pen,
    "waterfall": waterfall,
    "ancestral_tomb": ancestral_tomb,
    "sword_tomb": sword_tomb,
    "sect_cottage": cottage,
}

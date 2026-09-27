"""Collectible item models: one GLB per tools/world_spec.ITEMS id, written to
godot/assets/items/<item id>.glb and bobbing above the ground as pickups.

ITEMS: item id -> builder.

Conventions: hand-held scale (0.15 - 0.4 m), Blender Z-up with the origin at the
bottom centre of the object (it rests on / hovers above its origin), the
readable face toward -Y (= +Z in Godot), 256 px textures, an emissive accent on
every item so it reads at a distance while it bobs and glows, and no collision
(the runtime pickup has its own trigger area).
"""
import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import lands, realms, tex, util
from .quest_props import (card, hoop, ink_paper, lathe_n, lightning, new_verts, paper, talisman, ubox, xf)

V = Vector
R = math.radians
S = 256  # item texture size


def _o(name, bm, mat, uv=None, smooth=True):
    return lands.obj(name, bm, mat, uv=uv, smooth=smooth)


def _glow(name, color, s=4.0, alpha=None):
    return util.material(name, color=color, rough=0.3, emission=color, emission_strength=s, alpha=alpha)


def _emat(name, maps, emit, s=3.0, **kw):
    """Textured material with an emission colour map (H, W, 3)."""
    return util.material(name, maps, emission_map=np.clip(emit, 0, 1), emission_strength=s, **kw)


def _tint(mask, color, k=1.0):
    return np.clip(mask[..., None] * tex.srgb(color)[None, None, :] * k, 0, 1)


def _gold():
    return util.material("it_gold", tex.metal("#d8ae4a", S, 901, rough=0.25))


def _silk(name, base, hl, seed):
    return util.material(name, tex.silk(base, hl, S, seed), double_sided=True, normal_strength=0.3)


# --------------------------------------------------------------------------
# items
# --------------------------------------------------------------------------
def spirit_herb(seed=3):
    """Uprooted spirit herb: fern fronds around a cluster of glowing buds on a clump of soil (~0.32 m)."""
    rnd = random.Random(seed)
    lc = lands.leaf_cards(S, 512, "#3f8a4a", "fern")
    leaf = lands.clip_alpha(util.material("it_herb_leaf", lc, alpha=lc["alpha"], double_sided=True,
                                          normal_strength=0.4, emission="#1f7a50", emission_strength=0.4))
    soil = util.material("it_herb_soil", lands.earth("#4d3d2a", S, 902, 0.3), normal_strength=0.6)
    bud = _glow("it_herb_glow", "#b8fff0", 5.0)
    bm_l, bm_s, bm_b, bm_r = (bmesh.new() for _ in range(4))
    uvl = bm_l.loops.layers.uv.verify()
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), 0))
        side = V((-d.y, d.x, 0))
        ln = rnd.uniform(0.2, 0.26)
        rows = 6
        verts = []
        for j in range(rows + 1):
            t = j / rows
            p = d * (0.015 + ln * 0.6 * t) + V((0, 0, 0.06 + ln * 0.9 * math.sin(t * 1.9) * (1 - 0.25 * t)))
            verts.append((bm_l.verts.new(p - side * 0.05), bm_l.verts.new(p + side * 0.05)))
        for j in range(rows):
            f = bm_l.faces.new((verts[j][0], verts[j][1], verts[j + 1][1], verts[j + 1][0]))
            for loop, (uu, vv) in zip(f.loops, ((0.3, j / rows), (0.7, j / rows), (0.7, (j + 1) / rows),
                                                (0.3, (j + 1) / rows))):
                loop[uvl].uv = (uu, vv)
    util.tube(bm_s, util.catmull([V((0, 0, 0.04)), V((0.01, 0.0, 0.18)), V((-0.005, 0, 0.29))], 4),
              lambda t: 0.008 * (1 - 0.4 * t), n=6)
    util.lathe(bm_b, [(0.001, 0.27), (0.028, 0.285), (0.038, 0.32), (0.028, 0.35), (0.001, 0.37)], segs=10)
    for k in range(4):
        a = 2 * math.pi * k / 4 + 0.4
        p = V((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.19 + 0.02 * (k % 2)))
        util.tube(bm_s, [V((0, 0, 0.1)), p * 0.6 + V((0, 0, 0.06)), p], 0.004, n=4)
        util.sphere(bm_b, 0.016, loc=p + V((0, 0, 0.01)), segs=8, rings=5)
    util.sphere(bm_r, 0.07, loc=(0, 0, 0.04), segs=12, rings=8, scale=(1.0, 1.0, 0.6))
    for k in range(5):  # dangling roots
        a = 2 * math.pi * k / 5
        util.tube(bm_s, [V((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.03)),
                         V((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.0))], 0.004, n=4)
    for v in bm_r.verts:
        v.co.z = max(v.co.z, 0.0)
    return [_o("HerbLeaves", bm_l, leaf), _o("HerbStems", bm_s, soil, uv=6.0), _o("HerbBuds", bm_b, bud),
            _o("HerbSoil", bm_r, soil, uv=6.0)]


def spirit_stone():
    """Faceted spirit crystal cluster on a pebble (~0.26 m), glowing sky-blue."""
    rnd = random.Random(5)
    cr = tex.jade("#4fd8ff", S, 903)
    crystal = _emat("it_spirit_crystal", cr, _tint(cr["albedo"].mean(axis=2), "#39c8ff", 1.0), 2.5,
                    normal_strength=0.3)
    rock = util.material("it_pebble", tex.stone("#8e8a82", S, 904), normal_strength=1.0)
    bm_c, bm_r = bmesh.new(), bmesh.new()
    specs = [(0, 0, 0.24, 0.045, 0, 0)] + [(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), rnd.uniform(0.1, 0.17),
                                           rnd.uniform(0.022, 0.032), rnd.uniform(0.35, 0.7), a)
                                          for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    for (x, y, h, r, tilt, az) in specs:
        vs = new_verts(bm_c, lambda: util.lathe(bm_c, [(r, 0), (r, h * 0.72), (r * 0.55, h * 0.9), (0.001, h)],
                                                 segs=6, cap_bottom=True))
        xf(bm_c, vs, (x, y, 0.025), yaw=az, pitch=tilt)
    lands.rock(bm_r, (0, 0, 0.02), (0.1, 0.09, 0.045), 9, 0.3, 2)
    for v in bm_r.verts:
        v.co.z = max(v.co.z, 0.0)
    return [_o("SpiritCrystals", bm_c, crystal, uv=8.0, smooth=False), _o("CrystalPebble", bm_r, rock, uv=6.0)]


def jade_slip():
    """A jade slip: a round-topped jade plaque with glowing inscribed columns, red cord and tassel (~0.26 m)."""
    base = tex.jade("#8fcfa8", S, 905)
    m = lands.glyph_mask(S, 3, 8, 906, (0.15, 0.08, 0.85, 0.8), 0.012)
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#1f4a34"), m * 0.85)
    base["height"] = base["height"] - m * 0.4
    jade = _emat("it_jade_slip", base, _tint(m, "#5fffc0", 0.9), 2.0, normal_strength=0.6)
    cord = _silk("it_cord_red", "#b3213a", "#d24a5e", 907)
    gold = _gold()
    bm_j, bm_c, bm_g = bmesh.new(), bmesh.new(), bmesh.new()
    w, h = 0.1, 0.2
    lands.extrude_outline(bm_j, lands.arc_outline(w, h, 10, 0.0), -0.011, 0.011, uv_front=(-w / 2, 0.0, w, h + w * 0.28))
    util.cylinder(bm_g, 0.012, 0.012, 0.026, loc=(0, 0, h + 0.012), segs=10, rot=Matrix.Rotation(R(90), 4, "X"))
    ubox(bm_g, (w + 0.01, 0.026, 0.012), loc=(0, 0, 0.006))
    hoop(bm_c, (0, 0, h + 0.045), 0.02, 0.004, normal=(0, 1, 0), segs=14, n=4)
    util.tube(bm_c, util.catmull([V((0.012, 0, h + 0.03)), V((0.06, -0.01, h - 0.02)), V((0.07, -0.012, h - 0.1))], 4),
              0.004, n=4)
    util.cylinder(bm_c, 0.006, 0.02, 0.07, loc=(0.07, -0.012, h - 0.14), segs=8)
    return [_o("JadeSlip", bm_j, jade, smooth=False), _o("SlipCord", bm_c, cord, uv=10.0), _o("SlipGilt", bm_g, gold,
                                                                                                 uv=10.0)]


def wolf_fang():
    """A great spirit-wolf fang, root bound in leather with a blue spirit bead (~0.24 m)."""
    bone = realms.bone(S, 908)
    frost = tex.sstep(0.55, 0.95, tex.grid(S)[1])  # tip glows (v along the fang)
    fang = _emat("it_fang", bone, _tint(frost, "#8fd8ff", 0.8), 2.0, normal_strength=0.6)
    leather = util.material("it_leather", tex.leather("#5a3a22", S, 909), normal_strength=0.6)
    bead = _glow("it_fang_bead", "#6fd8ff", 5.0)
    bm_f, bm_l, bm_b = bmesh.new(), bmesh.new(), bmesh.new()
    path = util.catmull([V((0, 0, 0.0)), V((0.0, -0.01, 0.1)), V((0.02, -0.04, 0.18)), V((0.05, -0.08, 0.24))], 6)
    util.tube(bm_f, path, lambda t: 0.034 * (1 - t) ** 0.9 + 0.0015, n=12, uv_scale=(1.0, 4.0))
    for z in (0.02, 0.035, 0.05):
        hoop(bm_l, (0, 0, z), 0.034, 0.006, segs=16, n=4)
    util.tube(bm_l, [V((0.03, 0, 0.04)), V((0.05, 0.01, 0.0)), V((0.05, 0.015, -0.0))], 0.004, n=4)
    util.sphere(bm_b, 0.013, loc=(-0.036, -0.01, 0.035), segs=10, rings=6)
    for v in bm_f.verts:
        v.co.z = max(v.co.z, 0.0)
    return [_o("Fang", bm_f, fang), _o("FangBinding", bm_l, leather, uv=12.0), _o("SpiritBead", bm_b, bead)]


def blood_lotus():
    """Blood lotus: three whorls of crimson petals around a glowing golden seedpod on a pad (~0.26 m wide)."""
    u, v = tex.grid(S)
    n = tex.fbm(S, 6, 4, 0.5, 910)
    col = tex.lerp(tex.srgb("#5a0610"), tex.srgb("#e0283a"), tex.sstep(0.0, 0.9, v) * (0.8 + 0.3 * n))
    veins = np.abs(np.sin(u * math.pi * 14)) < 0.12
    col = tex.lerp(col, col * 0.7, veins.astype(np.float32))
    maps = tex.result(col, 0.45, 0.0, n * 0.2 + veins * 0.2)
    petal = _emat("it_blood_petal", maps, _tint(tex.sstep(0.3, 1.0, v), "#ff1a2a", 0.7), 1.6, double_sided=True,
                  normal_strength=0.4)
    pod = _glow("it_lotus_pod", "#ffc24a", 4.0)
    pad = util.material("it_lotus_pad", tex.foliage("#2f5a2a", S, 911), double_sided=True, normal_strength=0.5)
    bm_p, bm_c, bm_d = bmesh.new(), bmesh.new(), bmesh.new()
    realms.disc(bm_d, (0, 0), 0.13, segs=24, z=0.006)
    for (cnt, rad, tilt, ln, z) in ((10, 0.045, 62, 0.12, 0.02), (8, 0.03, 38, 0.11, 0.03), (6, 0.018, 14, 0.09, 0.04)):
        for k in range(cnt):
            a = 2 * math.pi * k / cnt + (0.3 if cnt == 8 else 0)
            vs = card(bm_p, 0.075, ln, loc=(0, 0, ln / 2), rows=4, cols=4,
                      bend=lambda x, zz: 0.02 * (1 - (2 * x / 0.075) ** 2) - 0.012 * ((zz + ln / 2) / ln) ** 2)
            for vv in vs:  # pointed tip
                t = (vv.co.z) / ln
                vv.co.x *= math.sin(math.pi * min(1.0, 0.15 + t)) ** 0.7
            xf(bm_p, vs, (math.cos(a) * rad, math.sin(a) * rad, z), yaw=a - R(90), pitch=R(-tilt))
    util.lathe(bm_c, [(0.001, 0.05), (0.02, 0.055), (0.032, 0.085), (0.03, 0.09), (0.001, 0.092)], segs=14)
    for k in range(8):
        a = 2 * math.pi * k / 8
        util.cylinder(bm_c, 0.002, 0.002, 0.03, loc=(math.cos(a) * 0.036, math.sin(a) * 0.036, 0.085), segs=4)
    return [_o("LotusPetals", bm_p, petal), _o("LotusPod", bm_c, pod), _o("LotusPad", bm_d, pad, smooth=False)]


def demon_core():
    """Demon core: a faceted obsidian heart split by glowing red veins, ringed with spikes (~0.22 m)."""
    s = tex.stone("#15101a", S, 912, 0.1)
    veins = lightning(S, 913, 6)
    s["albedo"] = tex.lerp(s["albedo"], tex.srgb("#ff2a14"), veins)
    s["rough"] = s["rough"] * 0 + 0.2
    core = _emat("it_demon_core", s, _tint(veins, "#ff2a14", 1.0), 5.0, normal_strength=0.8)
    spike = util.material("it_obsidian", tex.stone("#0f0b10", S, 914, 0.05), normal_strength=0.3)
    heart = _glow("it_demon_heart", "#ff3a1a", 6.0)
    bm_c, bm_s, bm_h = bmesh.new(), bmesh.new(), bmesh.new()
    c = V((0, 0, 0.11))
    res = bmesh.ops.create_icosphere(bm_c, subdivisions=2, radius=0.08)
    rnd = random.Random(15)
    for vv in res["verts"]:
        vv.co = vv.co * rnd.uniform(0.9, 1.1) + c
    bm_c.verts.ensure_lookup_table()
    util.sphere(bm_h, 0.05, loc=c, segs=10, rings=6)
    for k in range(10):
        d = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.4, 1))).normalized()
        q = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        vs = new_verts(bm_s, lambda: util.cylinder(bm_s, 0.016, 0.001, 0.07, loc=(0, 0, 0.035), segs=5))
        bmesh.ops.transform(bm_s, matrix=Matrix.Translation(c + d * 0.065) @ q, verts=vs)
    for f in bm_c.faces:
        f.smooth = False
    return [_o("DemonCore", bm_c, core, uv=8.0, smooth=False), _o("CoreSpikes", bm_s, spike, uv=10.0, smooth=False),
            _o("CoreHeart", bm_h, heart)]


def star_iron():
    """Star iron: a lump of meteoric iron flecked with glittering starlight (~0.2 m)."""
    base = tex.metal("#3a3f52", S, 915, rough=0.45)
    fl = tex.sstep(0.82, 0.9, tex.fbm(S, 96, 2, 0.5, 916))
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#e8f0ff"), fl)
    mat = _emat("it_star_iron", base, _tint(fl, "#9fc4ff", 1.0), 5.0, normal_strength=1.0)
    ring = _glow("it_star_glint", "#bcd6ff", 3.0)
    bm, bm_g = bmesh.new(), bmesh.new()
    lands.rock(bm, (0, 0, 0.08), (0.11, 0.09, 0.08), 17, 0.35, 3)
    for v in bm.verts:
        v.co.z = max(v.co.z, 0.0)
    for k in range(5):  # a few crystalline star points poking out
        a = 2 * math.pi * k / 5
        d = V((math.cos(a), math.sin(a), 0.6)).normalized()
        vs = new_verts(bm_g, lambda: realms.prism(bm_g, [(0.001, 0.0), (0.012, 0.015), (0.001, 0.04)], sides=4))
        q = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm_g, matrix=Matrix.Translation(V((0, 0, 0.08)) + V((d.x * 0.09, d.y * 0.08, d.z * 0.06)))
                            @ q, verts=vs)
    return [_o("StarIron", bm, mat, uv=6.0), _o("StarPoints", bm_g, ring, smooth=False)]


def thunder_crystal():
    """Thunder crystal: jagged violet crystals crackling with bright lightning veins (~0.32 m)."""
    base = tex.jade("#6a4fd8", S, 917)
    bolt = lightning(S, 918, 5)
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#e8f0ff"), bolt)
    mat = _emat("it_thunder_crystal", base, _tint(bolt, "#a8c8ff", 1.0) + _tint(np.ones((S, S)), "#3a2a8a", 0.4),
                4.0, normal_strength=0.3)
    rock = util.material("it_dark_rock", tex.stone("#3a3840", S, 919), normal_strength=1.0)
    bm, bm_r = bmesh.new(), bmesh.new()
    for (x, y, h, r, tilt, yaw, sd) in ((0, 0, 0.3, 0.045, 0, 0, 1), (0.05, 0.02, 0.19, 0.03, 30, 40, 2),
                                         (-0.04, 0.03, 0.16, 0.028, 28, 200, 3), (0.0, -0.05, 0.13, 0.025, 32, 290, 4)):
        vs = new_verts(bm, lambda: realms.prism(bm, [(r, 0.0), (r * 1.1, h * 0.55), (r * 0.8, h * 0.8), (0.002, h)],
                                                sides=5, jitter=0.2, seed=sd))
        xf(bm, vs, (x, y, 0.02), yaw=R(yaw), pitch=R(tilt))
    lands.rock(bm_r, (0, 0, 0.015), (0.08, 0.07, 0.035), 23, 0.35, 2)
    for v in bm_r.verts:
        v.co.z = max(v.co.z, 0.0)
    return [_o("ThunderCrystals", bm, mat, smooth=False), _o("CrystalBase", bm_r, rock, uv=6.0)]


def cloud_silk():
    """Cloud silk: a folded bolt of shimmering white silk woven with glowing clouds, tied with a blue ribbon (~0.26 m)."""
    maps = tex.silk("#eef0f6", "#ffffff", S, 920, motif_count=9, motif_scale=0.09)
    clouds = tex.xiangyun_mask(S, 4, 921, 0.1, 0.01)
    maps["albedo"] = tex.lerp(maps["albedo"], tex.srgb("#cfe2ff"), clouds * 0.6)
    silk = _emat("it_cloud_silk", maps, _tint(clouds, "#bfe0ff", 0.8) + 0.05, 2.0, normal_strength=0.4)
    ribbon = _silk("it_ribbon_blue", "#2f5f9a", "#4f86c6", 922)
    bm, bm_r = bmesh.new(), bmesh.new()
    for k, (w, d, z) in enumerate(((0.26, 0.16, 0.0), (0.25, 0.155, 0.032), (0.24, 0.15, 0.064))):
        ubox(bm, (w, d, 0.03), loc=(0.004 * k, 0.003 * k, z + 0.015), bevel=0.012, rect=(0, 0, 1, 1))
    for x in (-0.06, 0.06):
        ubox(bm_r, (0.03, 0.17, 0.1), loc=(x, 0.0, 0.047))
    util.tube(bm_r, util.catmull([V((0.06, -0.09, 0.08)), V((0.09, -0.1, 0.1)), V((0.12, -0.09, 0.085))], 3),
              (0.012, 0.003), n=4)
    return [_o("CloudSilk", bm, silk, smooth=False), _o("SilkRibbon", bm_r, ribbon, uv=8.0)]


def phoenix_feather():
    """Phoenix feather standing on its quill: flame-gradient vane with an eye, glowing like embers (~0.42 m)."""
    u, v = tex.grid(S)
    x = (u - 0.5) * 2
    width = np.sin(np.clip(v, 0, 1) * math.pi * 0.95 + 0.1) ** 0.6 * (0.95 - 0.3 * v)
    alpha = (np.abs(x) < width).astype(np.float32) * (v > 0.12)
    barbs = (np.abs(np.sin((np.abs(x) * 0.9 + v * 1.6) * 90)) < 0.35).astype(np.float32)
    notch = tex.fbm(S, 12, 3, 0.5, 923)
    alpha = alpha * (1 - ((np.abs(x) > width * 0.75) & (notch > 0.62)).astype(np.float32))
    col = tex.lerp(tex.srgb("#b3200c"), tex.srgb("#ff8a1a"), tex.sstep(0.1, 0.6, v))
    col = tex.lerp(col, tex.srgb("#ffd84a"), tex.sstep(0.6, 0.95, v))
    eye_r = np.hypot(x * 1.3, (v - 0.8) * 2.2)
    col = tex.lerp(col, tex.srgb("#1f7aa8"), (eye_r < 0.22).astype(np.float32))
    col = tex.lerp(col, tex.srgb("#0a1a3a"), (eye_r < 0.1).astype(np.float32))
    col = col * (0.85 + 0.15 * barbs)[..., None]
    maps = tex.result(col, 0.5, 0.0, barbs * 0.3)
    maps["alpha"] = alpha
    vane = lands.clip_alpha(_emat("it_phoenix_vane", maps, col * 0.8, 2.2, alpha=alpha, double_sided=True,
                                  normal_strength=0.3))
    quill = _gold()
    bm_v, bm_q = bmesh.new(), bmesh.new()
    card(bm_v, 0.16, 0.38, loc=(0, 0, 0.21), rows=8, cols=2,
         bend=lambda xx, zz: 0.03 * ((zz + 0.19) / 0.38) ** 2 - 0.02 * (xx / 0.08) ** 2)
    util.tube(bm_q, [V((0, 0.0, 0.0)), V((0, 0.005, 0.2)), V((0, 0.03, 0.4))], lambda t: 0.006 * (1 - 0.7 * t), n=6)
    return [_o("PhoenixVane", bm_v, vane), _o("PhoenixQuill", bm_q, quill, uv=10.0)]


def medicine():
    """Medicine bundle: a paper-wrapped herbal packet tied with twine under a red label, beside a
    glazed pill gourd (~0.22 m)."""
    wrap = util.material("it_wrap_paper", paper("#d8c49a", S, 924, 0.5), normal_strength=0.4)
    lab = ink_paper("#c42a22", S, 925, 1, 3, ink="#f4d27a", box=(0.3, 0.1, 0.7, 0.9), stroke=0.04, seal=False)
    label = _emat("it_med_label", lab, _tint(lab["ink"], "#ffcf6a", 0.8), 1.5, double_sided=True)
    twine = util.material("it_twine", tex.bark("#b39a6a", 128, 926), normal_strength=0.3)
    gourd = util.material("it_gourd", lands.glaze("#3f7a4a", S, 927))
    herb = _glow("it_med_herb", "#7fff9a", 2.5)
    bm_p, bm_t, bm_l, bm_g, bm_h = (bmesh.new() for _ in range(5))
    vs = ubox(bm_p, (0.16, 0.12, 0.08), loc=(-0.02, 0, 0.04), bevel=0.015, rect=(0, 0, 1, 1))
    for v in vs:
        if v.co.z > 0.07:
            v.co.x *= 0.85
    for x in (-0.06, 0.02):
        ubox(bm_t, (0.006, 0.125, 0.085), loc=(x, 0, 0.042))
    ubox(bm_t, (0.165, 0.006, 0.085), loc=(-0.02, 0, 0.042))
    hoop(bm_t, (-0.02, 0, 0.09), 0.015, 0.004, normal=(1, 0, 0), segs=10, n=4)
    card(bm_l, 0.05, 0.1, loc=(-0.02, -0.02, 0.083), pitch=R(-90), rect=(0, 0, 1, 1))
    for k in range(3):  # sprigs peeking from the fold
        util.sphere(bm_h, 0.012, loc=(-0.08 + k * 0.015, 0.05, 0.085), segs=6, rings=4, scale=(1, 1, 1.6))
    util.lathe(bm_g, [(0.001, 0.0), (0.03, 0.0), (0.045, 0.04), (0.035, 0.08), (0.02, 0.095), (0.028, 0.12),
                      (0.02, 0.15), (0.008, 0.16), (0.01, 0.175), (0.001, 0.178)], segs=16, loc=(0.1, 0.03, 0))
    hoop(bm_t, (0.1, 0.03, 0.095), 0.021, 0.004, segs=12, n=4)
    return [_o("Packet", bm_p, wrap, smooth=False), _o("Twine", bm_t, twine, uv=12.0, smooth=False),
            _o("MedLabel", bm_l, label, smooth=False), _o("PillGourd", bm_g, gourd, uv=8.0),
            _o("HerbSprigs", bm_h, herb)]


def letter():
    """Sealed letter: a paper envelope with a red address strip and a glowing wax seal, standing on edge (~0.23 m)."""
    s = S
    p = ink_paper("#efe4c8", s, 928, 1, 6, ink="#1a120c", box=(0.42, 0.12, 0.58, 0.85), stroke=0.01, seal=False)
    u, v = tex.grid(s)
    strip = ((np.abs(u - 0.5) < 0.1) & (v > 0.08) & (v < 0.9)).astype(np.float32)
    p["albedo"] = tex.lerp(p["albedo"], tex.srgb("#b3261e"), strip * (1 - p["ink"]) * 0.9)
    env = util.material("it_envelope", p, normal_strength=0.3)
    seal = _glow("it_wax_seal", "#e0302a", 2.5)
    cord = _silk("it_letter_cord", "#c8a040", "#e8c870", 929)
    bm_e, bm_s, bm_c = bmesh.new(), bmesh.new(), bmesh.new()
    ubox(bm_e, (0.12, 0.014, 0.22), loc=(0, 0, 0.11), bevel=0.003, rect=(0, 0, 1, 1))
    util.cylinder(bm_s, 0.022, 0.024, 0.008, loc=(0, 0.012, 0.18), segs=16, rot=Matrix.Rotation(R(90), 4, "X"))
    util.cylinder(bm_s, 0.022, 0.024, 0.008, loc=(0, -0.012, 0.03), segs=16, rot=Matrix.Rotation(R(90), 4, "X"))
    ubox(bm_c, (0.124, 0.018, 0.01), loc=(0, 0, 0.13))
    return [_o("Envelope", bm_e, env, smooth=False), _o("WaxSeals", bm_s, seal), _o("LetterCord", bm_c, cord,
                                                                                   uv=10.0)]


def lantern_oil():
    """Lantern oil: a glass flask of glowing amber oil with a clay neck, cork and rope sling (~0.24 m)."""
    glass = util.material("it_flask_glass", color="#e8d8a8", rough=0.05, alpha=0.35)
    oil = _glow("it_lamp_oil", "#ffb030", 3.5)
    clay = util.material("it_flask_clay", tex.stone("#8a5a3a", S, 930, 0.2), normal_strength=0.4)
    cork = util.material("it_cork", tex.stone("#b08a5a", 256, 931, 0.6), normal_strength=0.5)
    rope = util.material("it_rope", tex.bark("#9b855c", 128, 932), normal_strength=0.4)
    lab = util.material("it_oil_label", ink_paper("#e8dcb8", S, 933, 1, 2, box=(0.3, 0.2, 0.7, 0.8), stroke=0.04,
                                                  seal=False), double_sided=True)
    bm_g, bm_o, bm_c, bm_k, bm_r, bm_l = (bmesh.new() for _ in range(6))
    util.lathe(bm_g, [(0.001, 0.0), (0.06, 0.0), (0.075, 0.03), (0.08, 0.08), (0.07, 0.12), (0.035, 0.15),
                      (0.001, 0.15)], segs=20)
    util.lathe(bm_o, [(0.001, 0.005), (0.055, 0.005), (0.068, 0.03), (0.072, 0.075), (0.064, 0.1), (0.001, 0.1)],
               segs=16)
    util.lathe(bm_c, [(0.036, 0.14), (0.03, 0.16), (0.025, 0.19), (0.032, 0.2), (0.025, 0.205), (0.001, 0.205)],
               segs=16)
    util.lathe(bm_c, [(0.062, 0.0), (0.066, 0.0), (0.066, 0.012), (0.062, 0.012)], segs=20)
    util.lathe(bm_k, [(0.02, 0.2), (0.022, 0.23), (0.001, 0.232)], segs=10)
    hoop(bm_r, (0, 0, 0.175), 0.028, 0.005, segs=14, n=4)
    util.tube(bm_r, [V((-0.028, 0, 0.175)) + V((0, 0, 0)), V((-0.05, 0, 0.24)), V((0, 0, 0.27)), V((0.05, 0, 0.24)),
                     V((0.028, 0, 0.175))], 0.004, n=4)
    card(bm_l, 0.05, 0.05, loc=(0, -0.081, 0.07), roll=R(45))
    return [_o("FlaskGlass", bm_g, glass), _o("FlaskOil", bm_o, oil), _o("FlaskClay", bm_c, clay, uv=10.0),
            _o("FlaskCork", bm_k, cork, uv=10.0), _o("FlaskRope", bm_r, rope, uv=10.0),
            _o("FlaskLabel", bm_l, lab, smooth=False)]


def rune_fragment():
    """Rune fragment: a broken shard of a formation stele with a glowing cyan rune (~0.25 m)."""
    runes = realms.rune_stone(S, 934, "#5a5a58", "#56e8ff", cols=1, rows=2)
    mat = util.material("it_rune_fragment", runes, emission_map=runes["emit"], emission_strength=4.0,
                        normal_strength=1.0)
    bm = bmesh.new()
    outline = [(-0.08, 0.0), (0.09, 0.0), (0.1, 0.07), (0.06, 0.12), (0.085, 0.19), (0.02, 0.25), (-0.02, 0.21),
               (-0.07, 0.24), (-0.1, 0.14), (-0.075, 0.07)]
    lands.extrude_outline(bm, outline, -0.025, 0.025, uv_front=(-0.1, 0.0, 0.2, 0.25))
    return [_o("RuneFragment", bm, mat, smooth=False)]


def void_shard():
    """Void shard: a jagged black splinter of space rimmed in violet light, with orbiting slivers (~0.34 m)."""
    u, v = tex.grid(S)
    fu = np.minimum(u, 1 - u)
    edge = 1 - tex.sstep(0.02, 0.12, fu)
    n = tex.fbm(S, 6, 4, 0.5, 935)
    col = tex.lerp(tex.srgb("#050308"), tex.srgb("#2a1040"), n * 0.6)
    col = tex.lerp(col, tex.srgb("#c07aff"), edge)
    maps = tex.result(col, 0.1, 0.4, n * 0.2)
    mat = _emat("it_void_shard", maps, _tint(edge, "#b060ff", 1.0) + _tint(n * 0.2, "#3a1a8a"), 4.0,
                normal_strength=0.3)
    bm = bmesh.new()
    vs = new_verts(bm, lambda: realms.prism(bm, [(0.03, 0.0), (0.05, 0.08), (0.035, 0.2), (0.001, 0.34)], sides=4,
                                            jitter=0.3, seed=7))
    xf(bm, vs, (0, 0, 0), pitch=R(6))
    for k, (r, z, ln) in enumerate(((0.09, 0.2, 0.08), (0.08, 0.12, 0.06), (0.1, 0.28, 0.05))):
        a = 2 * math.pi * k / 3 + 0.4
        vs = new_verts(bm, lambda: realms.prism(bm, [(0.012, 0.0), (0.001, ln)], sides=3, seed=k))
        xf(bm, vs, (math.cos(a) * r, math.sin(a) * r, z), pitch=R(40), yaw=a)
    return [_o("VoidShard", bm, mat, smooth=False)]


def spirit_pill():
    """Spirit pill: a glowing golden pill with cloud swirls resting on a jade lotus dish (~0.15 m)."""
    u, v = tex.grid(S)
    sw = np.zeros((S, S), np.float32)
    for k in range(4):
        tex.stamp_curve(sw, tex.cloud_curl((k + 0.5) / 4, 0.5, 0.08, turns=1.4, flip=1 if k % 2 else -1), 0.012, S)
    col = tex.lerp(tex.srgb("#d88a10"), tex.srgb("#ffe070"), sw)
    maps = tex.result(col, 0.25, 0.6, sw * 0.4)
    pill = _emat("it_spirit_pill", maps, _tint(sw, "#ffd040", 1.0) + _tint(np.ones((S, S)), "#b06000", 0.35), 2.5,
                 normal_strength=0.5)
    jade = util.material("it_white_jade", tex.jade("#cfe8d6", S, 936), normal_strength=0.3)
    bm_p, bm_d = bmesh.new(), bmesh.new()
    util.lathe(bm_d, [(0.001, 0.0), (0.035, 0.0), (0.04, 0.015), (0.03, 0.025), (0.001, 0.025)], segs=16)
    for k in range(8):
        a = 2 * math.pi * k / 8
        vs = util.sphere(bm_d, 1.0, segs=10, rings=6, scale=(0.04, 0.014, 0.03))
        xf(bm_d, vs, (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.035), yaw=a + R(90), pitch=R(-55))
    util.sphere(bm_p, 0.042, loc=(0, 0, 0.07), segs=18, rings=12)
    return [_o("SpiritPill", bm_p, pill, uv=12.0), _o("LotusDish", bm_d, jade, uv=10.0)]


def incense():
    """Incense bundle: a fan of sandalwood sticks bound with a red paper band, tips smouldering (~0.32 m)."""
    rnd = random.Random(19)
    stick = util.material("it_incense", tex.wood("#7a4a2a", 128, 937, 6), normal_strength=0.3)
    dyed = util.material("it_incense_foot", color="#b3231c", rough=0.6)
    tal = talisman(S, 938)
    band = _emat("it_incense_band", tal, tal["emit"], 1.5, double_sided=True)
    ember = _glow("it_incense_ember", "#ff6a1a", 7.0)
    bm_s, bm_f, bm_b, bm_e = (bmesh.new() for _ in range(4))
    for k in range(16):
        a, r = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()) * 0.018
        base = V((math.cos(a) * r, math.sin(a) * r, 0.0))
        top = V((math.cos(a) * r * 2.8, math.sin(a) * r * 2.8, 0.3 + rnd.uniform(-0.02, 0.02)))
        util.tube(bm_s, [base.lerp(top, 0.25), top], 0.0028, n=4)
        util.tube(bm_f, [base, base.lerp(top, 0.25)], 0.0032, n=4)
        if k % 3 == 0:
            util.sphere(bm_e, 0.005, loc=top, segs=6, rings=4)
    vs = new_verts(bm_b, lambda: util.lathe(bm_b, [(0.024, 0.0), (0.024, 0.05)], segs=16))
    xf(bm_b, vs, (0, 0, 0.1))
    return [_o("IncenseSticks", bm_s, stick, uv=12.0), _o("IncenseFeet", bm_f, dyed), _o("IncenseBand", bm_b, band),
            _o("IncenseEmbers", bm_e, ember)]


def tribulation_jade():
    """Tribulation jade: a lavender jade bi disc etched with living lightning, on a small rosewood stand
    with a red cord knot and tassel (~0.28 m)."""
    base = tex.jade("#b8a8e8", S, 939)
    bolt = lightning(S, 940, 4)
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#f4f0ff"), bolt)
    jade = _emat("it_tribulation_jade", base, _tint(bolt, "#c8b0ff", 1.0) + _tint(np.ones((S, S)), "#40307a", 0.25),
                 3.5, normal_strength=0.4)
    wood = util.material("it_rosewood", tex.wood("#4a2418", S, 941, 20), normal_strength=0.4)
    cord = _silk("it_cord_red", "#b3213a", "#d24a5e", 907)
    bm_j, bm_w, bm_c = bmesh.new(), bmesh.new(), bmesh.new()
    c = V((0, 0, 0.14))
    Ro, Ri, t = 0.1, 0.035, 0.018
    uvl = bm_j.loops.layers.uv.verify()
    segs = 40
    rings = []
    for (r, y) in ((Ri, -t / 2), (Ro, -t / 2), (Ro, t / 2), (Ri, t / 2)):
        rings.append([c + V((math.cos(a) * r, y, math.sin(a) * r)) for a in np.linspace(0, 2 * math.pi, segs,
                                                                                       endpoint=False)])
    util.loft(bm_j, rings + [rings[0]], closed=True)
    for f in bm_j.faces:
        for loop in f.loops:
            co = loop.vert.co - c
            loop[uvl].uv = (co.x / (2 * Ro) + 0.5, co.z / (2 * Ro) + 0.5)
    bmesh.ops.remove_doubles(bm_j, verts=bm_j.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm_j, faces=bm_j.faces)
    ubox(bm_w, (0.16, 0.06, 0.02), loc=(0, 0, 0.01), bevel=0.005)
    for sx in (-1, 1):
        ubox(bm_w, (0.02, 0.035, 0.07), loc=(sx * 0.07, 0, 0.055), bevel=0.004)
        util.sphere(bm_w, 0.013, loc=(sx * 0.07, 0, 0.095), segs=8, rings=5)
    ubox(bm_w, (0.12, 0.04, 0.02), loc=(0, 0, 0.035))
    hoop(bm_c, c + V((0, 0, Ro + 0.012)), 0.014, 0.004, normal=(0, 1, 0), segs=12, n=4)
    util.tube(bm_c, util.catmull([c + V((0.01, -0.01, Ro + 0.01)), c + V((0.06, -0.015, Ro - 0.02)),
                                  c + V((0.11, -0.02, Ro - 0.1))], 4), 0.003, n=4)
    util.cylinder(bm_c, 0.005, 0.016, 0.05, loc=c + V((0.11, -0.02, Ro - 0.13)), segs=8)
    return [_o("TribulationBi", bm_j, jade, smooth=False), _o("JadeStand", bm_w, wood, uv=10.0, smooth=False),
            _o("JadeCord", bm_c, cord, uv=10.0)]


ITEMS = {
    "spirit_herb": spirit_herb,
    "spirit_stone": spirit_stone,
    "jade_slip": jade_slip,
    "wolf_fang": wolf_fang,
    "blood_lotus": blood_lotus,
    "demon_core": demon_core,
    "star_iron": star_iron,
    "thunder_crystal": thunder_crystal,
    "cloud_silk": cloud_silk,
    "phoenix_feather": phoenix_feather,
    "medicine": medicine,
    "letter": letter,
    "lantern_oil": lantern_oil,
    "rune_fragment": rune_fragment,
    "void_shard": void_shard,
    "spirit_pill": spirit_pill,
    "incense": incense,
    "tribulation_jade": tribulation_jade,
}

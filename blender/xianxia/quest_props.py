"""Interactable quest props added with the expanded world, plus market / shrine dressing.

Every id in tools/world_spec.PROPS that maps to a GLB name listed here is built
into godot/assets/environment/<name>.glb. ASSETS: GLB name -> builder.

House conventions (same as lands.py / realms.py): Blender Z-up, metres, the
front of every prop faces -Y in Blender (= +Z / south in Godot), origin at the
ground centre, invisible '-convcolonly' boxes/hulls for collision that hug the
solid part of the prop so the player can walk right up to it. Magical props
carry emissive materials (KHR_materials_emissive_strength).

QUEST (the 30 interactable quest props):
    notice_board ancestral_tablet pill_furnace sword_in_stone tortoise_stele
    guardian_lion bronze_ding bronze_mirror spirit_lamp scroll_rack war_drum
    sealed_coffin offering_table rune_pillar armillary_sphere medicine_cabinet
    wine_jars loom map_table crane_statue spirit_fountain puppet_frame
    herb_drying_rack chain_anchor soul_lantern abacus_desk fishing_boat
    wishing_tree jade_screen stone_tablet_array

DRESSING (decorative set dressing for districts and quest scenes):
    goods_baskets cloth_bolts grain_sacks barrel_stack tea_set calligraphy_table
    hanging_scrolls halberd_rack sword_stand lantern_string paper_umbrellas
    spirit_bird_cage hand_cart fishing_nets altar_candles incense_coils
    pottery_stack firewood_pile

The texture / material / geometry helpers at the top are shared with items.py.
"""
import math
import random

import bmesh
import numpy as np
from mathutils import Matrix, Vector

from . import lands, realms, tex, util

V = Vector
R = math.radians


# --------------------------------------------------------------------------
# textures (numpy; row 0 = v 0)
# --------------------------------------------------------------------------
def paper(color="#e8dcc0", size=256, seed=701, age=0.35):
    """Rice paper: long fibres, soft blotches and foxing."""
    c = tex.srgb(color)
    fib = tex.fbm(size, 48, 3, 0.5, seed, stretch=6)
    n = tex.fbm(size, 4, 5, 0.55, seed + 1)
    fox = tex.sstep(0.72, 0.9, tex.fbm(size, 12, 3, 0.5, seed + 2)) * age
    col = c * (0.9 + 0.08 * fib + 0.06 * (n - 0.5))[..., None]
    col = tex.lerp(col, col * np.array([0.8, 0.68, 0.5], np.float32), fox)
    return tex.result(col, 0.85, 0.0, fib * 0.2)


def ink_paper(color="#e8dcc0", size=256, seed=711, cols=4, rows=8, ink="#1c1612", box=(0.1, 0.08, 0.9, 0.92),
              stroke=0.01, seal=True):
    """Paper covered in columns of calligraphy with an optional red seal."""
    p = paper(color, size, seed)
    m = lands.glyph_mask(size, cols, rows, seed, box, stroke)
    col = tex.lerp(p["albedo"], tex.srgb(ink), m * 0.92)
    if seal:
        u, v = tex.grid(size)
        sq = ((np.abs(u - 0.2) < 0.06) & (np.abs(v - 0.14) < 0.06)).astype(np.float32)
        inner = lands.glyph_mask(size, 2, 2, seed + 5, (0.15, 0.09, 0.25, 0.19), stroke * 0.6)
        col = tex.lerp(col, tex.srgb("#b3261e"), np.clip(sq - inner, 0, 1) * 0.9)
    p["albedo"] = col
    p["height"] = p["height"] - m * 0.1
    p["ink"] = m
    return p


def notice_atlas(size=512, seed=721):
    """2x2 atlas of posted notices: edict, wanted poster, bounty list, torn old notice."""
    out = np.zeros((size, size, 3), np.float32)
    h = size // 2
    tones = ["#efe3c4", "#e6d09a", "#f2ead6", "#d9c49a"]
    for k in range(4):
        cell = ink_paper(tones[k], h, seed + k * 7, cols=[5, 3, 4, 6][k], rows=[9, 4, 7, 10][k],
                         box=[(0.1, 0.08, 0.9, 0.9), (0.12, 0.06, 0.88, 0.3), (0.1, 0.1, 0.9, 0.92),
                              (0.08, 0.06, 0.92, 0.86)][k], stroke=0.012, seal=k != 3)
        col = cell["albedo"]
        u, v = tex.grid(h)
        if k == 1:  # wanted poster: framed ink portrait
            frame = ((np.abs(u - 0.5) < 0.3) & (np.abs(v - 0.62) < 0.27)).astype(np.float32)
            inner = ((np.abs(u - 0.5) < 0.285) & (np.abs(v - 0.62) < 0.255)).astype(np.float32)
            face = np.zeros((h, h), np.float32)
            pts = [(0.5 + 0.13 * math.cos(a), 0.64 + 0.17 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 60)]
            tex.stamp_curve(face, pts, 0.008, h)
            for sx in (-1, 1):
                tex.stamp_curve(face, [(0.5 + sx * (0.04 + t * 0.06), 0.68 + t * 0.01) for t in np.linspace(0, 1, 10)],
                                0.007, h)
                tex.stamp_curve(face, [(0.5 + sx * (0.05 + t * 0.03), 0.65) for t in np.linspace(0, 1, 6)], 0.01, h)
            tex.stamp_curve(face, [(0.5 - 0.05 + t * 0.1, 0.55) for t in np.linspace(0, 1, 10)], 0.006, h)
            tex.stamp_curve(face, [(0.5 + 0.13 * math.cos(a), 0.64 + 0.17 * math.sin(a) + 0.05)
                                   for a in np.linspace(0.2, math.pi - 0.2, 30)], 0.02, h)  # hair
            col = tex.lerp(col, tex.srgb("#231a14"), np.clip(frame - inner + face, 0, 1) * 0.9)
        if k == 3:  # torn, weathered
            stain = tex.sstep(0.45, 0.85, tex.fbm(h, 5, 4, 0.5, seed + 40))
            col = tex.lerp(col, col * np.array([0.7, 0.6, 0.45], np.float32), stain * 0.6)
        ys, xs = (k // 2) * h, (k % 2) * h
        out[ys:ys + h, xs:xs + h] = col
    n = tex.fbm(size, 32, 3, 0.5, seed + 99)
    return tex.result(out, 0.85, 0.0, n * 0.2)


def talisman(size=256, seed=731, base="#e3c048", ink="#b3170f"):
    """Yellow Taoist talisman strip (u across, v along): red seal script + border. 'emit' = glowing ink."""
    p = paper(base, size, seed, 0.2)
    u, v = tex.grid(size)
    g = realms.glyph_column(size, 1, 6, seed, stroke=0.018, margin=0.22)
    border = (((u > 0.06) & (u < 0.1)) | ((u > 0.9) & (u < 0.94)) | ((v > 0.02) & (v < 0.035))
              | ((v > 0.965) & (v < 0.98))).astype(np.float32)
    m = np.clip(g + border, 0, 1)
    p["albedo"] = tex.lerp(p["albedo"], tex.srgb(ink), m * 0.95)
    p["emit"] = np.clip(g[..., None] * tex.srgb("#ff3a1a")[None, None, :] * 0.9, 0, 1)
    return p


def leiwen_bronze(size=512, seed=741, color="#8a6a3a", patina="#3f8a72", bands=((0.62, 0.9),), amt=0.25):
    """Cast bronze with raised thunder-pattern (leiwen) registers and taotie eyes.

    Band registers span v ranges; recesses fill with verdigris, raised lines are polished.
    """
    u, v = tex.grid(size)
    base = tex.metal(color, size, seed, rough=0.35)
    reps = 24
    fu = (u * reps) % 1.0
    band = np.zeros_like(u)
    pattern = np.zeros_like(u)
    for (v0, v1) in bands:
        inb = (v > v0) & (v < v1)
        fv = (v - v0) / (v1 - v0)
        cell_v = (fv * 3) % 1.0
        d = np.maximum(np.abs(fu - 0.5), np.abs(cell_v - 0.5))
        spiral = (((d * 6.0) % 1.0) < 0.45).astype(np.float32)
        # taotie eyes: every 6th cell a large boss ring
        eu = (u * reps / 6) % 1.0
        er = np.hypot((eu - 0.5) * 2.2, (fv - 0.5) * 1.4)
        eye = ((er < 0.32) & (er > 0.22)).astype(np.float32) + (er < 0.1)
        edge = ((np.abs(fv - 0.02) < 0.02) | (np.abs(fv - 0.98) < 0.02)).astype(np.float32)
        pat = np.where(er < 0.36, np.clip(eye, 0, 1), spiral)
        pattern = np.where(inb, np.clip(pat + edge, 0, 1), pattern)
        band = np.maximum(band, inb.astype(np.float32))
    n = tex.fbm(size, 6, 5, 0.6, seed + 3)
    recess = band * (1 - pattern)
    verd = np.clip(recess * 0.9 + tex.sstep(1 - amt, 1.2 - amt, n) * 0.8, 0, 1)
    col = tex.lerp(base["albedo"], base["albedo"] * 1.25, band * pattern * 0.5)
    col = tex.lerp(col, tex.srgb(patina) * (0.75 + 0.4 * n)[..., None], verd)
    metal = np.clip(1 - verd, 0, 1)
    rough = tex.lerp(base["rough"], 0.85, verd)
    return tex.result(col, rough, metal, n * 0.2 + pattern * 0.7)


def drawer_atlas(size=512, seed=751, grid=4):
    """Apothecary drawer fronts: dark wood, inset border, paper label with a glyph (grid x grid variants)."""
    u, v = tex.grid(size)
    w = tex.wood("#5b3a22", size, seed)
    fu, fv = (u * grid) % 1.0, (v * grid) % 1.0
    inset = ((np.minimum(fu, 1 - fu) < 0.06) | (np.minimum(fv, 1 - fv) < 0.08)).astype(np.float32)
    label = ((np.abs(fu - 0.5) < 0.2) & (np.abs(fv - 0.66) < 0.22)).astype(np.float32)
    glyph = np.zeros_like(u)
    for gy in range(grid):
        for gx in range(grid):
            box = ((gx + 0.36) / grid, (gy + 0.48) / grid, (gx + 0.64) / grid, (gy + 0.84) / grid)
            glyph = np.maximum(glyph, lands.glyph_mask(size, 1, 2, seed + gx * 7 + gy, box, 0.006))
    col = tex.lerp(w["albedo"], w["albedo"] * 0.55, inset)
    col = tex.lerp(col, tex.srgb("#eadcb8"), label)
    col = tex.lerp(col, tex.srgb("#1d1612"), glyph * label)
    return tex.result(col, 0.55 - label * 0.1, 0.0, w["height"] * 0.3 - inset * 0.6 + label * 0.1)


def map_parchment(size=1024, seed=761):
    """Hand-drawn strategic map: rivers, mountain ranges, cities, roads, border and compass."""
    rng = np.random.default_rng(seed)
    u, v = tex.grid(size)
    p = paper("#dcc79a", size, seed, 0.6)
    col = p["albedo"]
    ink = np.zeros((size, size), np.float32)
    water = np.zeros_like(ink)
    red = np.zeros_like(ink)
    # coastline + sea wash on the right
    coast = 0.78 + 0.06 * np.sin(v * 9) + 0.04 * (tex.fbm(size, 4, 4, 0.5, seed + 1) - 0.5)
    sea = tex.sstep(coast - 0.005, coast + 0.005, u)
    col = tex.lerp(col, tex.srgb("#8fa7a0"), sea * 0.55)
    tex.stamp_curve(ink, [(0.78 + 0.06 * math.sin(t * 9), t) for t in np.linspace(0.05, 0.95, 300)], 0.0025, size)
    # rivers: meandering random walks toward the sea
    for r in range(3):
        x, y = rng.uniform(0.1, 0.3), rng.uniform(0.2, 0.8)
        pts = []
        ang = rng.uniform(-0.3, 0.3)
        for _ in range(160):
            pts.append((x, y))
            ang += rng.uniform(-0.25, 0.25)
            ang = max(-0.9, min(0.9, ang))
            x += 0.004 * math.cos(ang)
            y += 0.004 * math.sin(ang)
            if x > 0.8:
                break
        tex.stamp_curve(water, pts, 0.004, size)
    # mountain ranges: clusters of inverted-V strokes
    for _ in range(9):
        cx, cy = rng.uniform(0.1, 0.68), rng.uniform(0.12, 0.88)
        for _ in range(rng.integers(4, 9)):
            x, y = cx + rng.uniform(-0.07, 0.07), cy + rng.uniform(-0.04, 0.04)
            s = rng.uniform(0.012, 0.022)
            tex.stamp_curve(ink, [(x - s + t * s, y + t * s * 1.3) for t in np.linspace(0, 1, 8)]
                            + [(x + t * s, y + s * 1.3 - t * s * 1.3) for t in np.linspace(0, 1, 8)], 0.002, size)
    # roads (dashed) and cities (red squares with a ring)
    cities = [(rng.uniform(0.12, 0.7), rng.uniform(0.12, 0.88)) for _ in range(7)]
    for a, b in zip(cities[:-1], cities[1:]):
        pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, 60)]
        tex.stamp_curve(ink, [q for i, q in enumerate(pts) if (i // 4) % 2 == 0], 0.0018, size)
    for (x, y) in cities:
        sq = ((np.abs(u - x) < 0.012) & (np.abs(v - y) < 0.012)).astype(np.float32)
        red = np.maximum(red, sq)
        tex.stamp_curve(ink, [(x + 0.022 * math.cos(a), y + 0.022 * math.sin(a))
                              for a in np.linspace(0, 2 * math.pi, 40)], 0.0018, size)
    # labels, border, compass rose
    ink = np.maximum(ink, lands.glyph_mask(size, 6, 1, seed + 3, (0.1, 0.9, 0.6, 0.97), 0.003, vertical=False))
    border = ((np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < 0.03)
              & (np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) > 0.022)).astype(np.float32)
    rr = np.hypot(u - 0.88, v - 0.14)
    ang = np.arctan2(v - 0.14, u - 0.88)
    rose = ((np.abs(rr - 0.06) < 0.002) | ((rr < 0.07) & (np.abs(np.sin(ang * 4)) < 0.08 + 0.4 * (0.07 - rr) / 0.07)))
    ink = np.clip(ink + border + rose.astype(np.float32), 0, 1)
    col = tex.lerp(col, tex.srgb("#3f6f86"), water * 0.9)
    col = tex.lerp(col, tex.srgb("#2a1d14"), ink * 0.9)
    col = tex.lerp(col, tex.srgb("#b3261e"), red * 0.9)
    return tex.result(col, 0.8, 0.0, p["height"] - ink * 0.1)


def drum_skin(size=256, seed=771):
    """Drum head (planar disc uv): cream hide, red lacquer ring, gold taiji-like swirl."""
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.hypot(x, y) * 2
    n = tex.fbm(size, 8, 5, 0.55, seed)
    col = tex.lerp(tex.srgb("#d8c7a0"), tex.srgb("#ecdfc2"), n)
    col = tex.lerp(col, col * 0.75, tex.sstep(0.35, 0.95, r) * 0.5)
    ring = ((r > 0.72) & (r < 0.8)).astype(np.float32)
    swirl = np.zeros_like(r)
    for k in range(2):
        rot = k * math.pi
        tex.stamp_curve(swirl, tex.cloud_curl(0.5 + 0.12 * math.cos(rot), 0.5 + 0.12 * math.sin(rot), 0.12,
                                               turns=1.2, rot=rot), 0.012, size)
    col = tex.lerp(col, tex.srgb("#9a1c14"), ring)
    col = tex.lerp(col, tex.srgb("#b8892f"), swirl)
    return tex.result(col, 0.6, swirl * 0.7, n * 0.3 + ring * 0.2)


def jade_relief(size=512, seed=781, color="#5ca882"):
    """Carved jade landscape panel (u across, v up): mountain tiers, pines, clouds, moon."""
    base = tex.jade(color, size, seed)
    u, v = tex.grid(size)
    h = np.zeros_like(u)
    for k, (y0, amp, cells) in enumerate(((0.18, 0.2, 5), (0.34, 0.22, 4), (0.5, 0.18, 3))):
        ridge = tex.fbm(size, cells, 4, 0.5, seed + k)[0]  # 1-D profile along u from row 0
        top = y0 + amp * ridge[None, :]
        h = np.maximum(h, tex.sstep(0.004, -0.004, v - top) * (0.5 + 0.2 * k))
    clouds = tex.xiangyun_mask(size, 4, seed + 7, 0.06, 0.008) * (v > 0.55)
    moon = (np.hypot(u - 0.75, v - 0.82) < 0.07).astype(np.float32)
    frame = (np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v)) < 0.035).astype(np.float32)
    relief = np.clip(h + clouds * 0.7 + moon * 0.6 + frame, 0, 1)
    col = tex.lerp(base["albedo"] * 0.8, np.minimum(base["albedo"] * 1.35, 1), relief)
    base["albedo"] = col
    base["height"] = relief * 0.8 + base["height"]
    base["emit"] = np.clip((relief * 0.25 + moon * 0.6)[..., None] * tex.srgb("#7fffc8")[None, None, :], 0, 1)
    return base


def shell_hex(size=512, seed=791, color="#7c7b72"):
    """Tortoise shell carving: hexagonal scutes with grooves (box-projected stone)."""
    base = tex.stone(color, size, seed, 0.2)
    u, v = tex.grid(size)
    s = 5.0
    x, y = u * s, v * s * 1.1547
    row = np.floor(y)
    xo = x + (row % 2) * 0.5
    fx, fy = xo - np.floor(xo) - 0.5, y - row - 0.5
    d = np.maximum(np.abs(fx), np.abs(fx) * 0.5 + np.abs(fy) * 0.866)
    groove = tex.sstep(0.42, 0.48, d)
    base["albedo"] = tex.lerp(base["albedo"], base["albedo"] * 0.5, groove)
    base["height"] = base["height"] * 0.4 - groove * 0.8 + (0.5 - d) * 0.4
    return base


def ink_landscape(size=512, seed=801):
    """Hanging-scroll ink painting (u across, v up): misty peaks, pine, poem column, seal."""
    p = paper("#e9dfc8", size, seed, 0.3)
    u, v = tex.grid(size)
    col = p["albedo"]
    for k, (y0, amp, tone) in enumerate(((0.2, 0.35, 0.45), (0.35, 0.3, 0.3), (0.5, 0.28, 0.18))):
        ridge = tex.fbm(size, 3 + k, 4, 0.55, seed + k)[0]
        top = y0 + amp * ridge[None, :]
        mt = tex.sstep(0.01, -0.02, v - top) * tex.sstep(top - 0.25, top, v)
        col = tex.lerp(col, tex.srgb("#26221e"), mt * tone)
    poem = lands.glyph_mask(size, 2, 7, seed + 9, (0.08, 0.55, 0.26, 0.95), 0.006)
    col = tex.lerp(col, tex.srgb("#1a1511"), poem)
    seal = ((np.abs(u - 0.2) < 0.035) & (np.abs(v - 0.5) < 0.03)).astype(np.float32)
    col = tex.lerp(col, tex.srgb("#b3261e"), seal)
    mount = ((u < 0.05) | (u > 0.95) | (v < 0.05) | (v > 0.95)).astype(np.float32)
    col = tex.lerp(col, tex.srgb("#6b5a3a"), mount)
    return tex.result(col, 0.85, 0.0, p["height"])


def lightning(size=256, seed=811, bolts=4):
    """Branching lightning mask."""
    rng = np.random.default_rng(seed)
    m = np.zeros((size, size), np.float32)
    for b in range(bolts):
        stack = [(rng.uniform(0.2, 0.8), 0.98, 0.9)]
        while stack:
            x, y, w = stack.pop()
            pts = [(x, y)]
            for _ in range(int(40 * w)):
                x += rng.uniform(-0.03, 0.03)
                y -= rng.uniform(0.01, 0.025)
                pts.append((x % 1.0, max(y, 0.0)))
                if w > 0.3 and rng.random() < 0.05:
                    stack.append((x, y, w * 0.5))
            tex.stamp_curve(m, pts, 0.004 + 0.004 * w, size)
    return np.clip(m, 0, 1)


def net(size=256, cells=12, line=0.08):
    """Knotted fishing net (alpha)."""
    u, v = tex.grid(size)
    fu, fv = ((u + v) * cells) % 1.0, ((u - v) * cells) % 1.0
    a = ((np.minimum(fu, 1 - fu) < line) | (np.minimum(fv, 1 - fv) < line)).astype(np.float32)
    col = np.ones((size, size, 3), np.float32) * tex.srgb("#8a7a5a") * (0.8 + 0.3 * tex.fbm(size, 8, 3, 0.5, 3))[..., None]
    out = tex.result(col, 0.9, 0.0, a * 0.5)
    out["alpha"] = a
    return out


def umbrella_paper(size=256, seed=821, color="#c8352a"):
    """Oil-paper umbrella canopy (lathe u around, v out): ribs, a rim band and plum blossoms."""
    u, v = tex.grid(size)
    c = tex.srgb(color)
    n = tex.fbm(size, 8, 4, 0.5, seed)
    col = c * (0.85 + 0.2 * n)[..., None]
    ribs = np.clip(1 - np.abs(((u * 24) % 1.0) - 0.5) * 16, 0, 1)
    rim = ((v > 0.86) & (v < 0.92)).astype(np.float32)
    rng = np.random.default_rng(seed)
    fl = np.zeros_like(u)
    for _ in range(18):
        cx, cy = rng.random(), rng.uniform(0.35, 0.8)
        for k in range(5):
            a = 2 * math.pi * k / 5
            fl = np.maximum(fl, (np.hypot((u - cx - 0.012 * math.cos(a)) * 3, v - cy - 0.02 * math.sin(a)) < 0.018)
                            .astype(np.float32))
    col = tex.lerp(col, tex.srgb("#f6e9d8"), fl)
    col = tex.lerp(col, tex.srgb("#2a1a12"), rim * 0.8)
    col = col * (1 - 0.3 * ribs)[..., None]
    return tex.result(col, 0.55, 0.0, ribs * 0.5)


def emissive(maps, key, color):
    """Emission colour map from a mask stored in maps[key]."""
    return np.clip(maps[key][..., None] * tex.srgb(color)[None, None, :], 0, 1)


# --------------------------------------------------------------------------
# material library (lazy: only what a prop uses is generated and exported)
# --------------------------------------------------------------------------
def _glow(name, color, s=5.0, alpha=None):
    return util.material(name, color=color, rough=0.4, emission=color, emission_strength=s, alpha=alpha)


def _emit_mat(name, maps, s=3.0, **kw):
    """Material whose emission colour map is maps['emit']."""
    return util.material(name, maps, emission_map=maps["emit"], emission_strength=s, **kw)


def _em(name, maps, key, color, s=3.0, **kw):
    return util.material(name, maps, emission_map=emissive(maps, key, color), emission_strength=s, **kw)


LIB = {
    "stone": lambda: util.material("qp_granite", tex.stone("#a19d93", 512, 701, 0.3), normal_strength=0.9),
    "dark_stone": lambda: util.material("qp_dark_stone", tex.stone("#6b6c66", 512, 702, 0.25), normal_strength=1.0),
    "weathered": lambda: util.material("qp_weathered", lands.crag("#8f8a7e", 512, 703), normal_strength=1.1),
    "marble": lambda: util.material("qp_marble", realms.marble(512, 704), normal_strength=0.4),
    "carved": lambda: util.material("qp_carved_marble", realms.carved_marble(512, 705), normal_strength=1.2),
    "shell": lambda: util.material("qp_shell_stone", shell_hex(512), normal_strength=1.3),
    "inscribed": lambda: util.material("qp_inscription", lands.inscription(512, 706, "#77786f"), normal_strength=1.2),
    "bronze": lambda: util.material("qp_bronze", tex.metal("#8a6a3a", 512, 707, rough=0.35, patina="#3f8a72",
                                                          patina_amt=0.2), normal_strength=0.6),
    "bronze_band": lambda: util.material("qp_bronze_leiwen", leiwen_bronze(512), normal_strength=1.0),
    "gold": lambda: util.material("qp_gold", tex.metal("#d4a93c", 256, 708, rough=0.28)),
    "brass": lambda: util.material("qp_brass", tex.metal("#b88a3a", 256, 709, rough=0.3, patina="#556b4a",
                                                        patina_amt=0.12)),
    "iron": lambda: util.material("qp_iron", tex.metal("#3c3a39", 256, 710, rough=0.55, patina="#6b3f22",
                                                      patina_amt=0.35), normal_strength=0.8),
    "steel": lambda: util.material("qp_steel", tex.metal("#c9ced6", 256, 711, rough=0.18)),
    "lacquer_red": lambda: util.material("qp_red_lacquer", tex.lacquer("#8c1d17", 512, 712, 0.18), normal_strength=0.3),
    "lacquer_black": lambda: util.material("qp_black_lacquer", tex.lacquer("#1d1614", 512, 713, 0.12),
                                           normal_strength=0.3),
    "rosewood": lambda: util.material("qp_rosewood", tex.wood("#4a2418", 512, 714, 30), normal_strength=0.5),
    "wood": lambda: util.material("qp_dark_wood", tex.wood("#5a3a24", 512, 715), normal_strength=0.5),
    "wood_light": lambda: util.material("qp_light_wood", tex.wood("#9a7650", 512, 716), normal_strength=0.5),
    "planks": lambda: util.material("qp_planks", lands.planks("#7a5a3c", 512, 717), normal_strength=0.7),
    "old_planks": lambda: util.material("qp_old_planks", lands.planks("#6a6150", 512, 718), normal_strength=0.8),
    "bamboo": lambda: util.material("qp_bamboo", lands.culm(256, 719), normal_strength=0.4),
    # solid objects use single-sided materials: a double-sided back face resting on a table or a
    # neighbour is coplanar with it and z-fights. Only thin cards use the *_ds variants.
    "woven": lambda: util.material("qp_woven", lands.woven("#a8834a", 256, 720), normal_strength=0.8),
    "woven_ds": lambda: util.material("qp_woven_ds", lands.woven("#a8834a", 256, 720), normal_strength=0.8,
                                      double_sided=True),
    "canvas": lambda: util.material("qp_canvas", lands.canvas("#a08d68", 256, 721), normal_strength=0.6),
    "rope": lambda: util.material("qp_rope", tex.bark("#9b855c", 128, 722), normal_strength=0.4),
    "bark": lambda: util.material("qp_bark", tex.bark("#4f3f30", 512, 723), normal_strength=1.0),
    "foliage": lambda: util.material("qp_foliage", tex.foliage("#3f6a2c", 256, 724), normal_strength=0.6),
    "earth": lambda: util.material("qp_earth", lands.earth("#5d4a32", 256, 725, 0.4), normal_strength=0.8),
    "paper": lambda: util.material("qp_paper", paper("#ece2c8", 256, 726), normal_strength=0.3),
    "ink_paper": lambda: util.material("qp_ink_paper", ink_paper("#ece2c8", 512, 727, 6, 9), normal_strength=0.3),
    "notices": lambda: util.material("qp_notices", notice_atlas(512), double_sided=True, normal_strength=0.3),
    "talisman": lambda: _emit_mat("qp_talisman", talisman(256), 1.6, double_sided=True, normal_strength=0.2),
    "silk_red": lambda: util.material("qp_silk_red", tex.silk("#a61c2a", "#c8404e", 256, 731), normal_strength=0.3),
    "silk_red_ds": lambda: util.material("qp_silk_red_ds", tex.silk("#a61c2a", "#c8404e", 256, 731),
                                         normal_strength=0.3, double_sided=True),
    "silk_gold": lambda: util.material("qp_silk_gold", tex.silk("#c4912e", "#e2b95a", 256, 732), normal_strength=0.3),
    "silk_gold_ds": lambda: util.material("qp_silk_gold_ds", tex.silk("#c4912e", "#e2b95a", 256, 732),
                                          normal_strength=0.3, double_sided=True),
    "silk_blue": lambda: util.material("qp_silk_blue", tex.silk("#27456e", "#3f6aa0", 256, 733), normal_strength=0.3),
    "silk_green": lambda: util.material("qp_silk_green", tex.silk("#2f6a4a", "#4f9a70", 256, 734),
                                        normal_strength=0.3),
    "silk_white": lambda: util.material("qp_silk_white", tex.silk("#e8e4da", "#ffffff", 256, 735),
                                        normal_strength=0.3),
    "jade": lambda: util.material("qp_jade", tex.jade("#5fae84", 256, 736), normal_strength=0.3),
    "white_jade": lambda: util.material("qp_white_jade", tex.jade("#d8e4d0", 256, 737), normal_strength=0.3),
    "porcelain": lambda: util.material("qp_porcelain", lands.glaze("#e9ecef", 256, 738)),
    "celadon": lambda: util.material("qp_celadon", lands.glaze("#8fb8a0", 256, 739)),
    "stoneware": lambda: util.material("qp_stoneware", lands.glaze("#4a2c1a", 256, 740)),
    "terracotta": lambda: util.material("qp_terracotta", tex.stone("#a0603a", 256, 741, 0.2), normal_strength=0.5),
    "leather": lambda: util.material("qp_leather", tex.leather("#6b4a2e", 256, 742), normal_strength=0.6),
    "roof": lambda: util.material("qp_roof_tiles", tex.roof_tiles("#3d4247", 256, 743), normal_strength=1.0),
    "ridge": lambda: util.material("qp_ridge", tex.stone("#2a3238", 256, 744, 0.1), normal_strength=0.4),
    "flame": lambda: _glow("qp_flame", "#ffb040", 8.0),
    "fire": lambda: _glow("qp_fire", "#ff6a1c", 7.0),
    "ember": lambda: _glow("qp_ember", "#ff5a1a", 8.0),
    "spirit": lambda: _glow("qp_spirit_glow", "#8ff4ff", 6.0),
    "soul": lambda: _glow("qp_soul_fire", "#b8ffe0", 7.0),
    "candle": lambda: util.material("qp_candle_wax", color="#b3231c", rough=0.45),
    "dark": lambda: util.material("qp_shadow", color="#0d0b0a", rough=1.0),
    "string": lambda: util.material("qp_string", color="#d8d2c0", rough=0.9),
    "skin": lambda: util.material("qp_puppet_face", color="#f0d8c0", rough=0.5),
    "red_paint": lambda: util.material("qp_red_paint", color="#a81e1a", rough=0.5),
    "fruit": lambda: util.material("qp_peach", color="#f2a07a", rough=0.6),
    "orange": lambda: util.material("qp_orange", color="#e07a1a", rough=0.5),
    "bun": lambda: util.material("qp_bun", color="#f2ead8", rough=0.8),
    "cabbage": lambda: util.material("qp_cabbage", color="#8fbf5a", rough=0.6),
}


class Mats(dict):
    """Lazy material dict: m['bronze'] builds the material on first use."""

    def __missing__(self, key):
        mat = LIB[key]()
        self[key] = mat
        return mat


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
obj = lands.obj
bevel_box = lands.bevel_box


def xf(bm, verts, loc=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    """Transform verts: scale, roll (Y), pitch (X), yaw (Z), then translate."""
    s = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    m = (Matrix.Translation(V(loc)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X")
         @ Matrix.Rotation(roll, 4, "Y") @ Matrix.Diagonal((*s, 1.0)))
    bmesh.ops.transform(bm, matrix=m, verts=list(verts))
    return verts


def unit_uv(bm, verts, rect=(0, 0, 1, 1)):
    """Map each face of an axis-aligned block to rect (u0, v0, u1, v1) by its dominant normal."""
    uvl = bm.loops.layers.uv.verify()
    lo = V((min(v.co.x for v in verts), min(v.co.y for v in verts), min(v.co.z for v in verts)))
    hi = V((max(v.co.x for v in verts), max(v.co.y for v in verts), max(v.co.z for v in verts)))
    ext = hi - lo
    faces = {f for v in verts for f in v.link_faces}
    u0, v0, u1, v1 = rect
    for f in faces:
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        for loop in f.loops:
            c = loop.vert.co - lo
            if ax == 2:
                a, b = c.x / max(ext.x, 1e-6), c.y / max(ext.y, 1e-6)
            elif ax == 0:
                a, b = c.y / max(ext.y, 1e-6), c.z / max(ext.z, 1e-6)
                a = a if n.x > 0 else 1 - a
            else:
                a, b = c.x / max(ext.x, 1e-6), c.z / max(ext.z, 1e-6)
                a = a if n.y < 0 else 1 - a
            loop[uvl].uv = (u0 + (u1 - u0) * a, v0 + (v1 - v0) * b)


def ubox(bm, size, loc=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, bevel=0.0, rect=None):
    """Box built at the origin (optionally bevelled, optionally unit-UV'd to rect), then placed."""
    before = set(bm.verts)
    if bevel > 0:
        bevel_box(bm, size, bevel=bevel)
    else:
        util.box(bm, size)
    verts = [v for v in bm.verts if v not in before]
    bm.normal_update()
    if rect is not None:
        unit_uv(bm, verts, rect)
    xf(bm, verts, loc, yaw, pitch, roll)
    return verts


def new_verts(bm, fn):
    """Run fn() and return the verts it added to bm."""
    before = set(bm.verts)
    fn()
    return [v for v in bm.verts if v not in before]


def card(bm, w, h, loc=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, rect=(0, 0, 1, 1), cols=1, rows=1, bend=None):
    """Rectangle in the XZ plane facing -Y, centred at loc. bend(x, z) -> y offset (for drapes)."""
    uvl = bm.loops.layers.uv.verify()
    u0, v0, u1, v1 = rect
    grid = []
    for j in range(rows + 1):
        row = []
        for i in range(cols + 1):
            x, z = -w / 2 + w * i / cols, -h / 2 + h * j / rows
            y = bend(x, z) if bend else 0.0
            row.append(bm.verts.new(V((x, y, z))))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uvl].uv = (u0 + (u1 - u0) * a / cols, v0 + (v1 - v0) * b / rows)
    verts = [v for row in grid for v in row]
    xf(bm, verts, loc, yaw, pitch, roll)
    return verts


def lathe_n(bm, profile, segs=24, loc=(0, 0, 0), u_rep=1.0, cap_top=False, cap_bottom=False):
    """Revolve [(r, z)] about Z with v normalised to 0..1 over the profile length."""
    rings = [util.ring((loc[0], loc[1], loc[2] + z), (1, 0, 0), (0, 1, 0), max(r, 1e-4), max(r, 1e-4), segs)
             for (r, z) in profile]
    vals = [0.0]
    for (r0, z0), (r1, z1) in zip(profile[:-1], profile[1:]):
        vals.append(vals[-1] + math.hypot(r1 - r0, z1 - z0))
    total = max(vals[-1], 1e-6)
    return util.loft(bm, rings, closed=True, cap_start=cap_bottom, cap_end=cap_top, uv_scale=(u_rep, 1.0),
                     v_values=[x / total for x in vals])


def hoop(bm, center, radius, r, normal=(0, 0, 1), segs=32, n=8, rx=None):
    """Closed torus of section radius r around `normal`.

    rx: radial half-width for a flattened section (r is then the half-thickness along `normal`).
    Built as an exact torus: sweeping util.tube round a closed path left a twisted seam whose
    first and last segments overlapped coplanar.
    """
    nrm = V(normal).normalized()
    a = nrm.orthogonal().normalized()
    b = nrm.cross(a).normalized()
    c = V(center)
    uvl = bm.loops.layers.uv.verify()
    rr = r if rx is None else rx
    rows = []
    for i in range(segs):
        th = 2 * math.pi * i / segs
        rad = a * math.cos(th) + b * math.sin(th)
        p = c + rad * radius
        rows.append([bm.verts.new(p + rad * (rr * math.cos(2 * math.pi * j / n)) + nrm * (r * math.sin(2 * math.pi * j / n)))
                     for j in range(n)])
    for i in range(segs):
        i2 = (i + 1) % segs
        for j in range(n):
            j2 = (j + 1) % n
            f = bm.faces.new((rows[i][j], rows[i2][j], rows[i2][j2], rows[i][j2]))
            for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uvl].uv = (uu / segs * radius * 6.0, vv / n)
    verts = [v for row in rows for v in row]
    bmesh.ops.recalc_face_normals(bm, faces=list({f for v in verts for f in v.link_faces}))
    return verts


def flame(bm, loc, h=0.12, r=0.03):
    return new_verts(bm, lambda: realms.flame(bm, loc, h, r))


def candle(bm_wax, bm_flame, loc, h=0.25, r=0.03):
    x, y, z = loc
    util.cylinder(bm_wax, r, r, h, loc=(x, y, z + h / 2), segs=10)
    util.sphere(bm_wax, r * 0.5, loc=(x + r * 0.7, y - r * 0.3, z + h * 0.8), segs=6, rings=4, scale=(0.6, 0.6, 1.8))
    flame(bm_flame, (x, y, z + h + 0.005), h=r * 2.6, r=r * 0.55)


def peach(bm, loc, r=0.045):
    util.sphere(bm, r, loc=loc, segs=10, rings=7, scale=(1, 1, 1.05))
    util.cylinder(bm, r * 0.18, 0.001, r * 0.6, loc=V(loc) + V((0, 0, r * 1.2)), segs=5)


def plate(bm, loc, r=0.12):
    x, y, z = loc
    util.lathe(bm, [(0.001, 0.0), (r * 0.5, 0.0), (r * 0.55, 0.015), (r, 0.03), (r * 0.95, 0.035),
                    (r * 0.5, 0.02), (0.001, 0.02)], segs=20, loc=(x, y, z))


def cup(bm, loc, r=0.03, h=0.04):
    x, y, z = loc
    util.lathe(bm, [(0.001, 0.0), (r * 0.6, 0.0), (r * 0.65, h * 0.15), (r, h), (r * 0.9, h), (r * 0.55, h * 0.3),
                    (0.001, h * 0.3)], segs=14, loc=(x, y, z))


def incense_pot(bm_b, bm_s, bm_g, loc, s=1.0, sticks=3, seed=1):
    """Small tripod censer with smouldering sticks (bronze, sticks, embers)."""
    rnd = random.Random(seed)
    x, y, z = loc
    util.lathe(bm_b, [(0.001, 0.03 * s), (0.07 * s, 0.035 * s), (0.1 * s, 0.07 * s), (0.1 * s, 0.11 * s),
                      (0.11 * s, 0.12 * s), (0.085 * s, 0.12 * s), (0.001, 0.1 * s)], segs=16, loc=(x, y, z))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        util.cylinder(bm_b, 0.012 * s, 0.008 * s, 0.04 * s, loc=(x + math.cos(a) * 0.06 * s,
                                                                 y + math.sin(a) * 0.06 * s, z + 0.02 * s), segs=6)
    for k in range(sticks):
        dx, dy = rnd.uniform(-0.03, 0.03) * s, rnd.uniform(-0.03, 0.03) * s
        top = V((x + dx * 1.6, y + dy * 1.6, z + (0.28 + rnd.uniform(-0.03, 0.03)) * s))
        util.tube(bm_s, [V((x + dx, y + dy, z + 0.1 * s)), top], 0.0035 * s, n=4)
        util.sphere(bm_g, 0.006 * s, loc=top, segs=6, rings=4)


def chain(bm, pts, link=0.13, r=0.018):
    """Iron chain along a poly-line. Like realms.chain, but alternate links are turned 83 degrees
    rather than exactly 90: with square-on links the facets of interlocking neighbours coincided
    (z-fighting where the links pass through each other)."""
    path = util.catmull([V(p) for p in pts], 10)
    out, acc = [path[0]], 0.0
    step = link * 0.8
    for p, q in zip(path[:-1], path[1:]):
        seg = (q - p).length
        while acc + seg >= step:
            p = p.lerp(q, (step - acc) / seg)
            seg = (q - p).length
            out.append(p)
            acc = 0.0
        acc += seg
    for i, (p, q) in enumerate(zip(out[:-1], out[1:])):
        t = (q - p).normalized()
        up = V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))
        s = t.cross(up).normalized()
        if i % 2:
            s = (Matrix.Rotation(R(83), 3, t) @ s).normalized()
        c = (p + q) / 2
        ring = [c + t * math.cos(a) * link * 0.55 + s * math.sin(a) * link * 0.3
                for a in [2 * math.pi * k / 12 for k in range(12)]]
        loop_tube(bm, ring, t.cross(s).normalized(), r, n=6)


def loop_tube(bm, pts, plane_normal, r, n=6):
    """Seamless tube round a closed planar loop (no duplicate end point)."""
    N = V(plane_normal).normalized()
    m = len(pts)
    rows = []
    for i in range(m):
        tan = (pts[(i + 1) % m] - pts[i - 1]).normalized()
        rad = tan.cross(N).normalized()
        rows.append([bm.verts.new(pts[i] + rad * (r * math.cos(2 * math.pi * j / n)) + N * (r * math.sin(2 * math.pi * j / n)))
                     for j in range(n)])
    uvl = bm.loops.layers.uv.verify()
    faces = []
    for i in range(m):
        for j in range(n):
            f = bm.faces.new((rows[i][j], rows[(i + 1) % m][j], rows[(i + 1) % m][(j + 1) % n], rows[i][(j + 1) % n]))
            for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uvl].uv = (uu / m, vv / n)
            faces.append(f)
    bmesh.ops.recalc_face_normals(bm, faces=faces)


def hull(name, bm):
    """Convex '-convcolonly' hull of every vert in bm.

    (lands.convex_mesh passes geom_interior + geom_unused straight to
    bmesh.ops.delete, which raises when a vert appears in both lists.)
    """
    res = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    extra = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
    if extra:
        bmesh.ops.delete(bm, geom=list(extra), context="VERTS")
    return util.mesh_object(name + "-convcolonly", bm, None, smooth=False)


def altar_table(bm, w, d, h, top=0.06, leg=0.07, everted=True):
    """Chinese altar table (qiaotou an): overhanging top, splayed legs, apron, upturned ends."""
    bevel_box(bm, (w, d, top), loc=(0, 0, h - top / 2), bevel=0.012)
    if everted:
        for sx in (-1, 1):
            # upturned end: inset 3 mm from the top's end and edges so no face is coplanar with it
            vs = ubox(bm, (0.12, d - 0.006, 0.05), loc=(sx * (w / 2 - 0.063), 0, h + 0.02))
            for v in vs:
                if v.co.z > h + 0.03 and sx * v.co.x > w / 2 - 0.02:
                    v.co.z += 0.05
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (leg, leg, h - top), loc=(sx * (w / 2 - 0.16), sy * (d / 2 - 0.08), (h - top) / 2))
        util.box(bm, (0.04, d - 0.12, 0.05), loc=(sx * (w / 2 - 0.16), 0, 0.12))
        util.box(bm, (0.04, d - 0.16, 0.2), loc=(sx * (w / 2 - 0.16), 0, h - top - 0.12))
    for sy in (-1, 1):  # aprons stop 5 mm under the top so their tops don't share the legs' top plane
        util.box(bm, (w - 0.3, 0.03, 0.12), loc=(0, sy * (d / 2 - 0.08), h - top - 0.065))


def chair(bm, loc, yaw=0.0, seat=0.48):
    """Official's hat armchair (guanmaoyi), ~1.1 m, facing -Y before yaw."""
    vs = new_verts(bm, lambda: _chair(bm, seat))
    xf(bm, vs, loc, yaw)


def _chair(bm, seat):
    w, d = 0.56, 0.46
    util.box(bm, (w, d, 0.04), loc=(0, 0, seat))
    for sx in (-1, 1):
        for sy in (-1, 1):
            hgt = seat if sy < 0 else 1.1
            util.box(bm, (0.04, 0.04, hgt + (0.22 if sy < 0 else 0)), loc=(sx * (w / 2 - 0.03), sy * (d / 2 - 0.03),
                                                                           (hgt + (0.22 if sy < 0 else 0)) / 2))
        util.box(bm, (0.035, d, 0.035), loc=(sx * (w / 2 - 0.03), 0, seat + 0.22))
        util.box(bm, (0.03, d - 0.06, 0.03), loc=(sx * (w / 2 - 0.03), 0, 0.1))
    util.box(bm, (w + 0.1, 0.05, 0.05), loc=(0, d / 2 - 0.03, 1.12))
    util.box(bm, (0.2, 0.02, 0.55), loc=(0, d / 2 - 0.04, seat + 0.32))
    util.box(bm, (w - 0.06, 0.03, 0.03), loc=(0, -d / 2 + 0.03, 0.14))  # above the side stretchers


def stool(bm, loc, r=0.2, h=0.45):
    x, y, z = loc
    util.cylinder(bm, r, r, 0.05, loc=(x, y, z + h - 0.025), segs=16)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        util.tube(bm, [V((x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75, z + h - 0.05)),
                       V((x + math.cos(a) * r * 0.95, y + math.sin(a) * r * 0.95, z))], 0.02, n=6)
    util.tube(bm, [V((x + r * 0.85 * math.cos(t), y + r * 0.85 * math.sin(t), z + 0.15))
                   for t in np.linspace(0, 2 * math.pi, 17)], 0.012, n=5, closed_ends=False)


def pennant(bm, loc, w=0.05, h=0.035, yaw=0.0):
    """Small triangular map flag on a pin."""
    x, y, z = loc
    uvl = bm.loops.layers.uv.verify()
    a = bm.verts.new(V((x, y, z)))
    b = bm.verts.new(V((x + w * math.cos(yaw), y + w * math.sin(yaw), z - h / 2)))
    c = bm.verts.new(V((x, y, z - h)))
    f = bm.faces.new((a, b, c))
    for loop, uv in zip(f.loops, ((0, 1), (1, 0.5), (0, 0))):
        loop[uvl].uv = uv


def scroll_roll(bm_p, bm_e, loc, length, r, axis="Y", knob=0.012):
    """Rolled scroll: paper cylinder plus wooden knob ends (into bm_e)."""
    rot = {"Y": Matrix.Rotation(R(90), 4, "X"), "X": Matrix.Rotation(R(90), 4, "Y"), "Z": None}[axis]
    util.cylinder(bm_p, r, r, length, loc=loc, segs=7, rot=rot)
    d = V((0, 1, 0)) if axis == "Y" else V((1, 0, 0)) if axis == "X" else V((0, 0, 1))
    for s in ((-1,) if axis == "Y" else (-1, 1)):  # the back knob of a shelved scroll is never seen
        util.cylinder(bm_e, r * 0.45, r * 0.45, knob * 2 + 0.01, loc=V(loc) + d * s * (length / 2 + knob), segs=6,
                      rot=rot)


# --------------------------------------------------------------------------
# the 30 quest props
# --------------------------------------------------------------------------
def notice_board():
    """Town notice board: two posts on stone footings, plank board under a little tiled roof,
    covered in pinned edicts, a wanted poster and bounty lists (~2.6 x 3.0 m)."""
    m = Mats()
    bm_w, bm_s, bm_b, bm_p, bm_n = (bmesh.new() for _ in range(5))
    for sx in (-1, 1):
        bevel_box(bm_s, (0.34, 0.34, 0.28), loc=(sx * 1.2, 0, 0.14), bevel=0.03)
        bevel_box(bm_w, (0.14, 0.14, 2.6), loc=(sx * 1.2, 0, 1.4), bevel=0.012)
        util.box(bm_w, (0.08, 0.32, 0.08), loc=(sx * 1.2, 0, 2.52))
    for z in (0.66, 2.06):
        bevel_box(bm_w, (2.62, 0.12, 0.1), loc=(0, 0, z), bevel=0.01)  # ends clear of the posts' bevels
    bevel_box(bm_w, (2.9, 0.1, 0.1), loc=(0, 0, 2.52), bevel=0.01)
    ubox(bm_b, (2.3, 0.05, 1.32), loc=(0, 0.02, 1.36), rect=(0, 0, 1, 1))
    rnd = random.Random(4)
    slots = [(-0.8, 1.7, 0.42, 0.5), (-0.3, 1.62, 0.4, 0.62), (0.22, 1.72, 0.44, 0.52), (0.75, 1.6, 0.42, 0.58),
             (-0.72, 1.05, 0.46, 0.56), (-0.12, 1.0, 0.38, 0.5), (0.4, 1.08, 0.36, 0.54), (0.86, 1.1, 0.34, 0.46)]
    for k, (x, z, w, h) in enumerate(slots):
        q = [0, 1, 2, 3, 2, 0, 3, 1][k]
        rect = ((q % 2) * 0.5, (q // 2) * 0.5, (q % 2) * 0.5 + 0.5, (q // 2) * 0.5 + 0.5)
        y = -0.01 - 0.002 * k
        card(bm_n, w, h, loc=(x, y, z), roll=R(rnd.uniform(-5, 5)), rect=rect, cols=2, rows=3,
             bend=lambda xx, zz: -0.01 * (1 - (2 * zz / h) ** 2) if k % 3 == 0 else 0.0)
        util.sphere(bm_p, 0.012, loc=(x, y - 0.006, z + h / 2 - 0.03), segs=6, rings=4)
    objs = [obj("BoardPosts", bm_w, m["wood"], uv=1.2), obj("BoardFootings", bm_s, m["stone"], uv=1.2),
            obj("BoardPlanks", bm_b, m["old_planks"]), obj("Notices", bm_n, m["notices"]),
            obj("NoticePins", bm_p, m["red_paint"])]
    roof, _ = lands.gable_roof("BoardRoof", 1.45, 0.5, 0.36, {"tiles": m["roof"], "wood": m["wood"],
                                                              "ridge": m["ridge"]}, 2.58, lift=0.12, nx=12, ny=5,
                              curl=False)
    # lands.gable_roof's front and back verge tubes meet at the apex with coplanar end faces: push the
    # back-slope verge tubes 4 mm outward
    for v in roof[1].data.vertices:
        if v.co.y > 0.001 and abs(v.co.x) > 1.45 - 0.12:
            v.co.x += math.copysign(0.004, v.co.x)
    objs += roof
    objs.append(util.collider("BoardCol", (2.6, 0.42, 2.9), (0, 0, 1.45)))
    return objs


def ancestral_tablet():
    """Ancestral altar: red lacquer altar table with a three-tier stand of gilded spirit tablets,
    candles, a censer and offerings (~2.0 x 0.7 x 2.0 m)."""
    m = Mats()
    bm_t, bm_k, bm_g, bm_c, bm_f, bm_b, bm_s, bm_e, bm_p, bm_fr = (bmesh.new() for _ in range(10))
    altar_table(bm_t, 2.0, 0.7, 0.92)
    for k, (w, d, h, y) in enumerate(((1.6, 0.26, 0.14, 0.14), (1.2, 0.2, 0.28, 0.2), (0.7, 0.14, 0.42, 0.25))):
        z0 = 0.92 + 0.003 * k  # stacked tiers: bottoms 3 mm apart so they don't share the table-top plane
        bevel_box(bm_t, (w, d, h - 0.003 * k), loc=(0, y, z0 + (h - 0.003 * k) / 2), bevel=0.01)
    # spirit tablets: (x, y, base z, width, height)
    specs = [(-0.55, 0.06, 1.06, 0.13, 0.4), (-0.3, 0.06, 1.06, 0.13, 0.42), (0.3, 0.06, 1.06, 0.13, 0.42),
             (0.55, 0.06, 1.06, 0.13, 0.4), (-0.3, 0.14, 1.2, 0.15, 0.48), (0.3, 0.14, 1.2, 0.15, 0.48),
             (0.0, 0.22, 1.34, 0.22, 0.62)]
    for i, (x, y, z, w, h) in enumerate(specs):
        bevel_box(bm_g, (w * 1.5, 0.1, 0.06), loc=(x, y, z + 0.03), bevel=0.01)
        uvl = bm_k.loops.layers.uv.verify()
        vs = new_verts(bm_k, lambda: lands.extrude_outline(bm_k, lands.arc_outline(w, h - w * 0.28, 8, 0.0),
                                                           -0.02, 0.02, uv_front=(-w / 2, 0.0, w, h)))
        # each tablet uses a different column of the glyph atlas
        for f in {f for v in vs for f in v.link_faces}:
            if abs(f.normal.y) > 0.9:
                for loop in f.loops:
                    uu, vv = loop[uvl].uv
                    loop[uvl].uv = ((i + uu) / 7.0, vv)
        xf(bm_k, vs, (x, y, z + 0.06))
        util.sphere(bm_g, w * 0.32, loc=(x, y, z + 0.06 + h + 0.02), segs=10, rings=6, scale=(1.2, 0.5, 0.7))
    # tablet faces: black lacquer, gold border + one gilded glyph column each
    s = 512
    u, v = tex.grid(s)
    lac = tex.lacquer("#17100e", s, 761, 0.1)
    fu = (u * 7) % 1.0
    border = ((np.abs(fu - 0.1) < 0.03) | (np.abs(fu - 0.9) < 0.03) | (np.abs(v - 0.04) < 0.012)).astype(np.float32)
    glyph = realms.glyph_column(s, 7, 7, 762, stroke=0.004, margin=0.3) * (v < 0.82) * (v > 0.1)
    gm = np.clip(border + glyph, 0, 1)
    lac["albedo"] = tex.lerp(lac["albedo"], tex.srgb("#e2b85a"), gm)
    lac["metal"] = gm * 0.9
    lac["rough"] = lac["rough"] - gm * 0.1
    tablet = util.material("qp_spirit_tablet", lac, normal_strength=0.3)
    # candles, censer, fruit
    for sx in (-1, 1):
        util.lathe(bm_b, [(0.07, 0.0), (0.07, 0.015), (0.025, 0.04), (0.02, 0.12), (0.06, 0.13), (0.06, 0.15),
                          (0.001, 0.15)], segs=14, loc=(sx * 0.82, -0.2, 0.92))
        candle(bm_c, bm_f, (sx * 0.82, -0.2, 1.07), h=0.28, r=0.03)
    incense_pot(bm_b, bm_s, bm_e, (0, -0.2, 0.92), 1.2, sticks=3, seed=3)
    for sx in (-0.45, 0.45):
        plate(bm_p, (sx, -0.18, 0.92), 0.12)
        for k in range(3):
            a = 2 * math.pi * k / 3
            peach(bm_fr, (sx + math.cos(a) * 0.045, -0.18 + math.sin(a) * 0.045, 0.99))
        peach(bm_fr, (sx, -0.18, 1.06))
    objs = [obj("AltarTable", bm_t, m["lacquer_red"], uv=1.5), obj("SpiritTablets", bm_k, tablet),
            obj("TabletGilt", bm_g, m["gold"], uv=3.0, smooth=True),
            obj("AltarCandles", bm_c, m["candle"], smooth=True), obj("CandleFlames", bm_f, m["flame"], smooth=True),
            obj("AltarBrass", bm_b, m["brass"], uv=3.0, smooth=True),
            obj("IncenseSticks", bm_s, m["candle"]), obj("IncenseEmbers", bm_e, m["ember"]),
            obj("OfferingPlates", bm_p, m["porcelain"], uv=4.0, smooth=True),
            obj("Peaches", bm_fr, m["fruit"], smooth=True)]
    objs.append(util.collider("AltarCol", (2.05, 0.75, 1.95), (0, 0, 0.97)))
    return objs


def pill_furnace():
    """Alchemist's bronze pill furnace: tripod cauldron with leiwen bands, a glowing fire
    window, vents and a pagoda lid on an octagonal plinth (~1.9 x 1.9 x 2.5 m)."""
    m = Mats()
    bm_p, bm_body, bm_b, bm_f, bm_g = (bmesh.new() for _ in range(5))
    realms.prism(bm_p, [(0.95, 0.0), (0.95, 0.18), (0.88, 0.24), (0.8, 0.24)], sides=8, rot=R(22.5), v_scale=0.5)
    lathe_n(bm_body, [(0.001, 0.62), (0.4, 0.64), (0.62, 0.78), (0.74, 1.0), (0.76, 1.2), (0.7, 1.42), (0.58, 1.55),
                      (0.6, 1.6), (0.62, 1.62)], segs=40, u_rep=1.0, cap_bottom=True)
    for k in range(3):
        a = R(90 + 120 * k)
        top = V((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.8))
        foot = V((math.cos(a) * 0.72, math.sin(a) * 0.72, 0.28))
        util.tube(bm_b, util.catmull([top, top.lerp(foot, 0.5) + V((math.cos(a) * 0.08, math.sin(a) * 0.08, 0)),
                                      foot], 4), lambda t: 0.1 * (1 - 0.35 * t), n=10)
        util.sphere(bm_b, 0.13, loc=foot + V((0, 0, -0.02)), segs=12, rings=8, scale=(1.1, 1.1, 0.55))
        util.sphere(bm_b, 0.12, loc=top + V((0, 0, 0.05)), segs=10, rings=7, scale=(1.0, 1.0, 0.8))
    # rim, handles and lid
    hoop(bm_b, (0, 0, 1.62), 0.63, 0.035, segs=40)
    for sx in (-1, 1):
        pts = [V((sx * 0.55, 0, 1.6)), V((sx * 0.62, 0, 1.9)), V((sx * 0.5, 0, 2.02)), V((sx * 0.4, 0, 1.9)),
               V((sx * 0.42, 0, 1.64))]
        util.tube(bm_b, util.catmull(pts, 4), (0.05, 0.03), n=8, power=3)
    util.lathe(bm_b, [(0.6, 1.63), (0.56, 1.72), (0.4, 1.85), (0.22, 1.92), (0.2, 1.98), (0.3, 2.0), (0.26, 2.04),
                      (0.12, 2.1), (0.2, 2.16), (0.16, 2.2), (0.07, 2.26), (0.1, 2.32), (0.001, 2.45)], segs=24)
    for k in range(8):
        a = 2 * math.pi * k / 8
        util.sphere(bm_b, 0.04, loc=(math.cos(a) * 0.29, math.sin(a) * 0.29, 2.03), segs=8, rings=5)
    util.sphere(bm_g, 0.06, loc=(0, 0, 2.47), segs=12, rings=8)
    # fire window at the front: glowing panel behind a bronze grille, plus four side vents
    card(bm_f, 0.42, 0.3, loc=(0, -0.735, 1.12), pitch=R(-4), cols=1, rows=1)
    hoop(bm_b, (0, -0.74, 1.12), 0.24, 0.035, normal=(0, 1, 0), segs=24, rx=0.02)
    for dx in (-0.12, 0.0, 0.12):
        util.box(bm_b, (0.025, 0.04, 0.34), loc=(dx, -0.75, 1.12))
    for k in (1, 2, 3):
        a = R(-90 + 90 * k)
        c = V((math.cos(a) * 0.745, math.sin(a) * 0.745, 1.12))
        vs = util.cylinder(bm_f, 0.07, 0.07, 0.03, loc=(0, 0, 0), segs=12, rot=Matrix.Rotation(R(90), 4, "X"))
        xf(bm_f, vs, c, yaw=a + R(90))
        vs = hoop(bm_b, (0, 0, 0), 0.08, 0.018, normal=(0, 1, 0), segs=16)
        xf(bm_b, vs, c, yaw=a + R(90))
    # coals glowing in the plinth mouth
    for k in range(6):
        util.sphere(bm_f, 0.07, loc=(math.cos(k) * 0.2, math.sin(k) * 0.2, 0.3), segs=8, rings=5,
                    scale=(1, 1, 0.6))
    objs = [obj("FurnacePlinth", bm_p, m["stone"], uv=0.8), obj("FurnaceBody", bm_body, m["bronze_band"],
                                                                smooth=True),
            obj("FurnaceCast", bm_b, m["bronze"], uv=1.5, smooth=True), obj("FurnaceFire", bm_f, m["fire"]),
            obj("FurnacePearl", bm_g, m["gold"], uv=4, smooth=True)]
    bm = bmesh.new()
    realms.prism(bm, [(0.95, 0.0), (0.95, 1.6), (0.3, 2.3)], sides=8, rot=R(22.5))
    objs.append(hull("FurnaceCol", bm))
    return objs


def sword_in_stone():
    """An ancient jian driven into a mossy boulder, runes glowing along its fuller (~1.8 m)."""
    m = Mats()
    bm_r, bm_bl, bm_gd, bm_gr, bm_rn, bm_t, bm_c = (bmesh.new() for _ in range(7))
    lands.rock(bm_r, (0, 0.05, 0.28), (0.85, 0.7, 0.58), 7, 0.3, 3)
    for k, (x, y, s) in enumerate(((0.8, -0.35, 0.22), (-0.75, -0.3, 0.16), (0.55, 0.62, 0.2), (-0.6, 0.55, 0.26))):
        lands.rock(bm_r, (x, y, s * 0.3), (s, s * 0.9, s * 0.7), 20 + k, 0.35, 2)
    # blade: lozenge cross-section, tapering to the (buried) tip
    L, z0 = 1.0, 0.5
    rings = []
    for t in np.linspace(0, 1, 6):
        w = 0.022 + 0.022 * t if t < 0.95 else 0.044
        th = 0.007 + 0.005 * t
        z = z0 + L * t
        rings.append([V((-w, 0, z)), V((0, -th, z)), V((w, 0, z)), V((0, th, z))])
    util.loft(bm_bl, rings, closed=True, cap_start=True, cap_end=True)
    for sy in (-1, 1):
        util.box(bm_rn, (0.008, 0.002, 0.62), loc=(0, sy * 0.0105, z0 + 0.62))
    top = z0 + L
    util.lathe(bm_gd, [(0.02, top), (0.05, top + 0.005), (0.055, top + 0.03), (0.02, top + 0.045)], segs=8)
    bevel_box(bm_gd, (0.2, 0.05, 0.035), loc=(0, 0, top + 0.02), bevel=0.012)
    for sx in (-1, 1):
        util.sphere(bm_gd, 0.022, loc=(sx * 0.11, 0, top + 0.03), segs=8, rings=6, scale=(1.2, 1, 1))
    util.cylinder(bm_gr, 0.018, 0.016, 0.22, loc=(0, 0, top + 0.155), segs=10)
    util.lathe(bm_gd, [(0.02, top + 0.265), (0.03, top + 0.275), (0.032, top + 0.3), (0.012, top + 0.32),
                       (0.001, top + 0.325)], segs=10)
    # red silk tassel swinging from the pommel
    knot = V((0.0, -0.01, top + 0.31))
    util.tube(bm_t, util.catmull([knot, knot + V((0.04, -0.03, -0.1)), knot + V((0.07, -0.05, -0.24))], 4),
              0.004, n=5)
    util.cylinder(bm_t, 0.008, 0.028, 0.12, loc=knot + V((0.075, -0.05, -0.3)), segs=8)
    objs = [obj("Boulder", bm_r, m["weathered"], uv=0.9, smooth=True), obj("SwordBlade", bm_bl, m["steel"], uv=4.0),
            obj("SwordGuard", bm_gd, m["gold"], uv=6.0, smooth=True),
            obj("SwordGrip", bm_gr, m["silk_blue"], uv=8.0, smooth=True),
            obj("SwordRunes", bm_rn, _glow("qp_sword_rune", "#7fdcff", 5.0)),
            obj("SwordTassel", bm_t, m["silk_red"], uv=6.0, smooth=True)]
    sword = objs[1:]
    for o in sword:  # drive the sword in at an angle
        o.rotation_euler = (R(9), R(-6), R(20))
        o.location = (0.05, 0.02, 0.0)
        util.apply_transform(o)
    objs.append(util.collider("BoulderCol", (1.55, 1.3, 0.85), (0, 0.05, 0.42)))
    objs.append(util.collider("HiltCol", (0.25, 0.25, 0.9), (0.05, 0.0, 1.2)))
    return objs


def tortoise_stele():
    """Imperial stele on a great bixi (dragon-headed tortoise) with a carved hexagon shell,
    twin-dragon crest and inscription (~2.8 x 4.4 x 4.6 m)."""
    m = Mats()
    bm_pl, bm_t, bm_sh, bm_cr, bm_d = (bmesh.new() for _ in range(5))
    bevel_box(bm_pl, (2.8, 4.4, 0.3), loc=(0, 0.2, 0.15), bevel=0.05)
    # shell: long dome with a skirt
    vs = new_verts(bm_sh, lambda: util.lathe(bm_sh, [(0.95, 0.3), (1.05, 0.42), (1.02, 0.6), (0.9, 0.85),
                                                      (0.6, 1.08), (0.3, 1.18), (0.001, 1.2)], segs=32,
                                             cap_bottom=True))
    xf(bm_sh, vs, (0, 0.35, 0), scale=(1.0, 1.45, 1.0))
    # head and neck (dragon): thrust forward (-Y), raised
    util.tube(bm_t, util.catmull([V((0, -0.9, 0.62)), V((0, -1.35, 0.85)), V((0, -1.7, 0.92))], 5),
              lambda t: 0.33 - 0.06 * t, n=14)
    util.sphere(bm_t, 0.34, loc=(0, -1.85, 0.98), segs=16, rings=10, scale=(0.95, 1.15, 0.85))
    util.sphere(bm_t, 0.22, loc=(0, -2.12, 0.9), segs=14, rings=8, scale=(1.1, 1.0, 0.7))  # snout
    util.sphere(bm_d, 0.1, loc=(0, -2.22, 0.78), segs=10, rings=6)  # pearl in the jaws
    for sx in (-1, 1):
        util.sphere(bm_t, 0.08, loc=(sx * 0.18, -2.02, 1.12), segs=10, rings=6)  # eyes
        util.sphere(bm_t, 0.1, loc=(sx * 0.2, -1.95, 1.18), segs=10, rings=6, scale=(1.3, 1.0, 0.5))  # brows
        util.tube(bm_t, util.catmull([V((sx * 0.16, -1.75, 1.2)), V((sx * 0.3, -1.55, 1.42)),
                                      V((sx * 0.28, -1.35, 1.55))], 4), lambda t: 0.06 * (1 - 0.7 * t), n=8)
        util.tube(bm_t, util.catmull([V((sx * 0.14, -2.25, 0.85)), V((sx * 0.35, -2.25, 0.8)),
                                      V((sx * 0.5, -2.1, 0.7))], 4), lambda t: 0.025 * (1 - 0.6 * t), n=6)
    # four legs with claws, tail
    for sx in (-1, 1):
        for sy in (-0.55, 1.2):
            c = V((sx * 0.95, 0.35 + sy * 0.9 - 0.35, 0.32))
            util.sphere(bm_t, 0.3, loc=c, segs=14, rings=8, scale=(1.1, 1.1, 0.95))
            for k in range(4):
                a = R(-90 + (k - 1.5) * 22) if sy < 0 else R(90 + (k - 1.5) * 22)
                a = a + (R(-25) * sx if sy < 0 else R(25) * sx)
                util.sphere(bm_t, 0.07, loc=c + V((math.cos(a) * 0.3 + sx * 0.12, math.sin(a) * 0.3, -0.24)),
                            segs=8, rings=5, scale=(1, 1, 0.7))
    util.tube(bm_t, util.catmull([V((0, 2.0, 0.5)), V((0.2, 2.35, 0.4)), V((0.1, 2.6, 0.35))], 4),
              lambda t: 0.18 * (1 - 0.8 * t), n=10)
    # socket and tablet
    bevel_box(bm_t, (1.6, 0.66, 0.2), loc=(0, 0.35, 1.26), bevel=0.04)
    w, side_h, z0 = 1.3, 2.3, 1.36
    tab = bmesh.new()
    # the tablet's round top stops 8 cm lower, fully inside the crest (their arcs nearly coincided)
    lands.extrude_outline(tab, lands.arc_outline(w, side_h - 0.08, 12, z0), 0.35 - 0.18, 0.35 + 0.18,
                          uv_front=(-w / 2, z0, w, side_h + w / 2 * 0.55))
    slab = util.mesh_object("SteleTablet", tab, m["inscribed"], smooth=False)
    crest = lands.arc_outline(w + 0.14, 0.0, 12, z0 + side_h - 0.05)
    lands.extrude_outline(bm_cr, crest, 0.35 - 0.21, 0.35 + 0.21)
    for sx in (-1, 1):
        for face_y in (0.35 - 0.215, 0.35 + 0.215):
            scroll = [V((sx * (0.34 - 0.14 * (1 - t) * math.cos(t * 9)), face_y,
                         z0 + side_h + 0.2 + 0.14 * (1 - t) * math.sin(t * 9))) for t in np.linspace(0, 0.85, 18)]
            util.tube(bm_cr, scroll, lambda t: 0.04 * (1 - 0.5 * t), n=7)
    util.sphere(bm_cr, 0.1, loc=(0, 0.35, z0 + side_h + 0.44), segs=12, rings=8)
    objs = [obj("StelePlinth", bm_pl, m["stone"], uv=0.8), obj("Bixi", bm_t, m["dark_stone"], uv=1.0, smooth=True),
            obj("BixiShell", bm_sh, m["shell"], uv=0.9, smooth=True), slab,
            obj("SteleCrest", bm_cr, m["dark_stone"], uv=1.2), obj("BixiPearl", bm_d, m["gold"], uv=4, smooth=True)]
    objs.append(util.collider("StelePlinthCol", (2.8, 4.4, 0.3), (0, 0.2, 0.15)))
    objs.append(util.collider("BixiCol", (2.3, 3.6, 1.1), (0, 0.15, 0.85)))
    objs.append(util.collider("SteleTabletCol", (1.5, 0.5, 2.8), (0, 0.35, 2.75)))
    return objs


def guardian_lion():
    """Seated stone guardian lion (shishi), paw on an embroidered ball, on a carved
    pedestal (~1.2 x 1.6 x 2.5 m)."""
    m = Mats()
    bm_p, bm_c, bm_l, bm_b = (bmesh.new() for _ in range(4))
    bevel_box(bm_p, (1.15, 1.6, 0.22), loc=(0, 0, 0.11), bevel=0.03)
    ubox(bm_c, (0.98, 1.42, 0.5), loc=(0, 0, 0.47), rect=(0, 0, 1, 0.5))
    bevel_box(bm_p, (1.15, 1.6, 0.16), loc=(0, 0, 0.8), bevel=0.03)
    z = 0.88
    # haunches, torso, chest
    for sx in (-1, 1):
        util.sphere(bm_l, 0.3, loc=(sx * 0.24, 0.35, z + 0.3), segs=16, rings=10, scale=(0.9, 1.25, 1.0))
        util.sphere(bm_l, 0.13, loc=(sx * 0.3, 0.05, z + 0.08), segs=10, rings=6, scale=(1.0, 1.6, 0.6))  # hind paw
    util.tube(bm_l, util.catmull([V((0, 0.4, z + 0.35)), V((0, 0.12, z + 0.62)), V((0, -0.1, z + 0.85))], 4),
              lambda t: 0.33 - 0.03 * t, n=16)
    util.sphere(bm_l, 0.3, loc=(0, -0.2, z + 0.72), segs=16, rings=10, scale=(1.0, 0.9, 1.1))
    # front legs (right paw raised on the ball)
    for sx in (-1, 1):
        foot = V((sx * 0.2, -0.45, z + 0.06)) if sx < 0 else V((0.24, -0.58, z + 0.36))
        util.tube(bm_l, util.catmull([V((sx * 0.2, -0.25, z + 0.78)), V((sx * 0.21, -0.36, z + 0.45)), foot], 4),
                  lambda t: 0.11 - 0.02 * t, n=12)
        util.sphere(bm_l, 0.11, loc=foot + V((0, -0.04, -0.02)), segs=12, rings=7, scale=(1.0, 1.25, 0.65))
        for k in range(3):
            util.sphere(bm_l, 0.035, loc=foot + V(((k - 1) * 0.05, -0.15, -0.03)), segs=8, rings=5)
    util.sphere(bm_b, 0.19, loc=(0.25, -0.6, z + 0.19), segs=16, rings=10)
    for k in range(6):
        hoop(bm_b, (0.25, -0.6, z + 0.19), 0.19, 0.012, normal=(math.cos(k), math.sin(k), 0.6), segs=20, n=5)
    # head: skull, muzzle, nose, eyes, brows, jaws, ears
    hz = z + 1.22
    util.sphere(bm_l, 0.32, loc=(0, -0.3, hz), segs=18, rings=12, scale=(1.0, 0.85, 0.92))
    util.sphere(bm_l, 0.17, loc=(0, -0.55, hz - 0.1), segs=14, rings=8, scale=(1.25, 0.8, 0.75))
    util.sphere(bm_l, 0.07, loc=(0, -0.68, hz - 0.03), segs=10, rings=6, scale=(1.3, 0.9, 0.8))
    util.sphere(bm_c, 0.1, loc=(0, -0.52, hz - 0.24), segs=10, rings=6, scale=(1.4, 1.0, 0.5))  # open mouth (dark)
    util.sphere(bm_l, 0.12, loc=(0, -0.5, hz - 0.32), segs=10, rings=6, scale=(1.4, 1.1, 0.45))  # lower jaw
    for sx in (-1, 1):
        util.sphere(bm_l, 0.075, loc=(sx * 0.13, -0.57, hz + 0.08), segs=10, rings=7)
        util.sphere(bm_l, 0.08, loc=(sx * 0.14, -0.53, hz + 0.16), segs=10, rings=6, scale=(1.4, 1.0, 0.5))
        util.sphere(bm_l, 0.07, loc=(sx * 0.3, -0.3, hz + 0.18), segs=8, rings=6, scale=(0.6, 1.0, 1.2))
        util.cylinder(bm_l, 0.018, 0.004, 0.06, loc=(sx * 0.08, -0.6, hz - 0.2), segs=6)  # fangs
    # mane: rows of spiral curls over the skull and down the neck
    for row, (zz, yy, rr, cnt) in enumerate(((hz + 0.26, -0.35, 0.22, 7), (hz + 0.16, -0.18, 0.3, 9),
                                             (hz - 0.02, -0.08, 0.34, 11), (hz - 0.22, -0.05, 0.33, 11),
                                             (hz - 0.42, -0.02, 0.3, 9))):
        for k in range(cnt):
            a = math.pi * (0.1 + 0.8 * k / (cnt - 1))
            util.sphere(bm_l, 0.075, loc=(math.cos(a) * rr * (1 if row else 0.9), yy + math.sin(a) * rr * 0.9, zz),
                        segs=8, rings=6, scale=(1, 1, 0.8))
    # collar with bell and tassel
    hoop(bm_b, (0, -0.2, z + 0.9), 0.28, 0.025, normal=(0, -0.5, 1), segs=28, n=6)
    util.sphere(bm_b, 0.07, loc=(0, -0.48, z + 0.8), segs=12, rings=8)
    # curly tail on the back
    util.tube(bm_l, util.catmull([V((0, 0.62, z + 0.2)), V((0, 0.72, z + 0.55)), V((0.1, 0.62, z + 0.8)),
                                  V((0, 0.5, z + 0.72))], 4), lambda t: 0.08 * (1 - 0.3 * t), n=10)
    for k in range(5):
        util.sphere(bm_l, 0.07, loc=(0.1 * math.cos(k * 1.3), 0.66 + 0.06 * math.sin(k * 1.3), z + 0.62 + k * 0.05),
                    segs=8, rings=5)
    objs = [obj("LionPedestal", bm_p, m["stone"], uv=1.0), obj("PedestalRelief", bm_c, m["carved"]),
            obj("Lion", bm_l, m["stone"], uv=1.4, smooth=True), obj("LionBall", bm_b, m["weathered"], uv=3.0,
                                                                    smooth=True)]
    objs.append(util.collider("LionCol", (1.15, 1.6, 2.1), (0, 0, 1.05)))
    return objs


def bronze_ding():
    """Rectangular fangding: cast bronze cauldron on four column legs with upright loop
    handles, flanges and leiwen / taotie registers (~1.15 x 0.85 x 1.45 m)."""
    m = Mats()
    bm_body, bm_b, bm_in = bmesh.new(), bmesh.new(), bmesh.new()
    w, d, h, z0 = 1.05, 0.78, 0.62, 0.48
    vs = ubox(bm_body, (w, d, h), loc=(0, 0, z0 + h / 2), bevel=0.02, rect=(0, 0.02, 3.0, 0.98))
    for v in vs:  # slight flare toward the rim
        if v.co.z > z0 + h * 0.5:
            v.co.x *= 1.04
            v.co.y *= 1.04
    ubox(bm_in, (w - 0.08, d - 0.08, 0.02), loc=(0, 0, z0 + h - 0.08))
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.cylinder(bm_b, 0.085, 0.075, z0 + 0.02, loc=(sx * (w / 2 - 0.13), sy * (d / 2 - 0.12), z0 / 2),
                          segs=14)
            util.sphere(bm_b, 0.11, loc=(sx * (w / 2 - 0.13), sy * (d / 2 - 0.12), z0 - 0.08), segs=12, rings=7,
                        scale=(1, 1, 0.8))
            util.cylinder(bm_b, 0.1, 0.08, 0.04, loc=(sx * (w / 2 - 0.13), sy * (d / 2 - 0.12), 0.02), segs=14)
            # corner flanges
            bevel_box(bm_b, (0.035, 0.035, h + 0.04), loc=(sx * (w / 2 + 0.01), sy * (d / 2 + 0.01), z0 + h / 2),
                      bevel=0.008)
        # mid flanges on the long faces and short faces
        bevel_box(bm_b, (0.03, 0.05, h * 0.7), loc=(0, sx * (d / 2 + 0.025), z0 + h * 0.45), bevel=0.008)
        bevel_box(bm_b, (0.05, 0.03, h * 0.7), loc=(sx * (w / 2 + 0.025), 0, z0 + h * 0.45), bevel=0.008)
        # upright handles on the short rims
        for dy in (-0.14, 0.14):
            bevel_box(bm_b, (0.06, 0.06, 0.3), loc=(sx * (w / 2 - 0.08), dy, z0 + h + 0.13), bevel=0.01)
        bevel_box(bm_b, (0.068, 0.352, 0.06), loc=(sx * (w / 2 - 0.08), 0, z0 + h + 0.27), bevel=0.01)
    bevel_box(bm_b, (w + 0.08, d + 0.08, 0.05), loc=(0, 0, z0 + h - 0.01), bevel=0.01)
    objs = [obj("DingBody", bm_body, m["bronze_band"]), obj("DingCast", bm_b, m["bronze"], uv=1.5),
            obj("DingInside", bm_in, m["dark"])]
    objs.append(util.collider("DingCol", (1.15, 0.9, 1.15), (0, 0, 0.58)))
    return objs


def bronze_mirror():
    """Great bronze mirror of seeing in a rosewood stand with cloud-scroll crest (~1.5 x 0.7 x 2.2 m)."""
    m = Mats()
    bm_w, bm_g, bm_back, bm_face, bm_t = (bmesh.new() for _ in range(5))
    for sx in (-1, 1):
        vs = ubox(bm_w, (0.14, 0.7, 0.12), loc=(sx * 0.62, 0, 0.06), bevel=0.02)
        for v in vs:
            if abs(v.co.y) > 0.3 and v.co.z > 0.1:
                v.co.z -= 0.04
        bevel_box(bm_w, (0.09, 0.09, 1.95), loc=(sx * 0.62, 0, 1.05), bevel=0.012)
        for sy in (-1, 1):  # braces
            util.tube(bm_w, [V((sx * 0.62, sy * 0.3, 0.12)), V((sx * 0.62, sy * 0.04, 0.5))], 0.025, n=6)
        util.sphere(bm_g, 0.06, loc=(sx * 0.62, 0, 2.06), segs=10, rings=6)
    bevel_box(bm_w, (1.4, 0.1, 0.1), loc=(0, 0, 1.96), bevel=0.012)
    bevel_box(bm_w, (1.24, 0.08, 0.08), loc=(0, 0, 0.3), bevel=0.01)
    # cloud crest
    for sx in (-1, 1):
        pts = [V((sx * (0.05 + 0.2 * (1 - t) * math.cos(t * 8) + 0.3 * t), 0, 2.1 + 0.12 * (1 - t) * math.sin(t * 8)))
               for t in np.linspace(0, 1, 20)]
        util.tube(bm_g, pts, lambda t: 0.03 * (1 - 0.5 * t), n=7)
    util.sphere(bm_g, 0.07, loc=(0, 0, 2.2), segs=12, rings=8)
    # mirror: disc facing -Y, hung from the crossbeam by cords, side pegs
    c = V((0, 0, 1.16))
    rot = Matrix.Rotation(R(90), 4, "X")
    util.cylinder(bm_back, 0.56, 0.56, 0.05, loc=c + V((0, 0.012, 0)), segs=48, rot=rot)
    hoop(bm_back, c + V((0, -0.012, 0)), 0.555, 0.02, normal=(0, 1, 0), segs=48, n=6)
    util.sphere(bm_back, 0.07, loc=c + V((0, 0.05, 0)), segs=10, rings=6, scale=(1, 0.6, 1))  # knob on the back
    uvl = bm_face.loops.layers.uv.verify()
    ring = [bm_face.verts.new(c + V((math.cos(a) * 0.54, -0.015, math.sin(a) * 0.54)))
            for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
    f = bm_face.faces.new(list(reversed(ring)))
    for loop in f.loops:
        co = loop.vert.co - c
        loop[uvl].uv = (co.x / 1.08 + 0.5, co.z / 1.08 + 0.5)
    for sx in (-1, 1):
        util.tube(bm_t, [V((sx * 0.2, 0.0, 1.92)), V((sx * 0.3, 0.03, 1.6))], 0.008, n=5)
        util.box(bm_w, (0.14, 0.05, 0.05), loc=(sx * 0.53, 0.0, 1.16))
    util.tube(bm_t, [c + V((0, 0.0, -0.58)), c + V((0, -0.01, -0.72))], 0.01, n=5)
    util.cylinder(bm_t, 0.01, 0.045, 0.16, loc=c + V((0, -0.01, -0.8)), segs=10)
    # mirror face: polished speculum with a faint rune ring
    s = 256
    u, v = tex.grid(s)
    rr = np.hypot(u - 0.5, v - 0.5) * 2
    n = tex.fbm(s, 6, 4, 0.5, 771)
    col = tex.lerp(tex.srgb("#d9d2b8"), tex.srgb("#b8ad88"), n * 0.5 + tex.sstep(0.8, 1.0, rr) * 0.5)
    ringm = ((np.abs(rr - 0.86) < 0.01) | (np.abs(rr - 0.78) < 0.006)).astype(np.float32)
    runes = ((np.sin(np.arctan2(v - 0.5, u - 0.5) * 24) > 0.5) & (rr > 0.79) & (rr < 0.85)).astype(np.float32)
    mm = np.clip(ringm + runes, 0, 1)
    maps = tex.result(col, 0.08 + 0.1 * n, 1.0, n * 0.02)
    maps["emit"] = mm
    face = _em("qp_mirror_face", maps, "emit", "#9ff0ff", 2.0)
    objs = [obj("MirrorStand", bm_w, m["rosewood"], uv=1.5), obj("MirrorGilt", bm_g, m["gold"], uv=3, smooth=True),
            obj("MirrorBack", bm_back, m["bronze_band"], smooth=True), obj("MirrorFace", bm_face, face),
            obj("MirrorCords", bm_t, m["silk_red"], uv=6, smooth=True)]
    objs.append(util.collider("MirrorCol", (1.45, 0.7, 2.2), (0, 0, 1.1)))
    return objs


def spirit_lamp():
    """Bronze lotus lamp-tree burning spirit fire in three lotus cups (~0.9 x 0.7 x 2.0 m)."""
    m = Mats()
    bm_s, bm_b, bm_g, bm_f = (bmesh.new() for _ in range(4))
    realms.prism(bm_s, [(0.36, 0.0), (0.36, 0.1), (0.3, 0.16), (0.24, 0.16), (0.24, 0.24), (0.18, 0.24)], sides=6,
                 rot=R(30))
    util.lathe(bm_b, [(0.16, 0.24), (0.1, 0.3), (0.05, 0.4), (0.045, 0.9), (0.07, 0.95), (0.045, 1.0),
                      (0.04, 1.5), (0.06, 1.55), (0.04, 1.6), (0.001, 1.62)], segs=14)

    def lotus(c, r, petals=8):
        util.lathe(bm_b, [(0.001, c.z - 0.04), (r * 0.5, c.z - 0.03), (r * 0.55, c.z)], segs=12, loc=(c.x, c.y, 0))
        for k in range(petals):
            a = 2 * math.pi * k / petals
            d = V((math.cos(a), math.sin(a), 0))
            util.sphere(bm_g, r * 0.5, loc=c + d * r * 0.55 + V((0, 0, r * 0.3)), segs=8, rings=6,
                        scale=(1, 1, 1))
            vs = util.sphere(bm_g, 1.0, loc=(0, 0, 0), segs=8, rings=6, scale=(r * 0.45, r * 0.15, r * 0.8))
            xf(bm_g, vs, c + d * r * 0.75 + V((0, 0, r * 0.35)), yaw=a + R(90), pitch=0.0, roll=0.0)
        util.cylinder(bm_g, r * 0.45, r * 0.4, r * 0.3, loc=c + V((0, 0, r * 0.2)), segs=12)
        flame(bm_f, c + V((0, 0, r * 0.35)), h=r * 2.6, r=r * 0.45)
        util.sphere(bm_f, r * 0.2, loc=c + V((0, 0, r * 0.9)), segs=8, rings=5)

    lotus(V((0, 0, 1.62)), 0.14)
    for sx in (-1, 1):
        pts = [V((0, 0, 1.05)), V((sx * 0.15, 0, 1.1)), V((sx * 0.3, 0, 1.2)), V((sx * 0.35, 0, 1.3))]
        util.tube(bm_b, util.catmull(pts, 4), lambda t: 0.03 * (1 - 0.3 * t), n=8)
        lotus(V((sx * 0.35, 0, 1.33)), 0.1)
    # jade beads dangling under the arms
    for sx in (-1, 1):
        for k in range(4):
            util.sphere(bm_g, 0.018, loc=(sx * 0.3, 0, 1.18 - k * 0.04), segs=8, rings=5)
    objs = [obj("LampBase", bm_s, m["stone"], uv=1.2), obj("LampBronze", bm_b, m["bronze"], uv=2.0, smooth=True),
            obj("LampLotus", bm_g, m["gold"], uv=3.0, smooth=True), obj("SpiritFlames", bm_f, m["spirit"],
                                                                        smooth=True)]
    objs.append(util.collider("LampCol", (0.6, 0.6, 1.7), (0, 0, 0.85)))
    return objs


def scroll_rack():
    """Scripture rack: rosewood cubbies stuffed with scrolls, tagged cases and bound books
    (~2.1 x 0.5 x 2.2 m)."""
    m = Mats()
    rnd = random.Random(11)
    bm_w, bm_p, bm_e, bm_tag, bm_bk, bm_pg = (bmesh.new() for _ in range(6))
    W, D, H, t = 2.1, 0.48, 2.2, 0.05
    cols, rows = 5, 5
    for sx in (-1, 1):
        bevel_box(bm_w, (t, D, H), loc=(sx * (W / 2 - t / 2), 0, H / 2), bevel=0.01)
    bevel_box(bm_w, (W + 0.08, D + 0.04, 0.06), loc=(0, 0, H + 0.03), bevel=0.015)
    ubox(bm_w, (W - 2 * t + 0.006, 0.02, H - 0.1), loc=(0, D / 2 - 0.007, H / 2 + 0.03))  # back proud by 3 mm
    z_shelves = [0.1 + k * (H - 0.14) / rows for k in range(rows + 1)]
    cw = (W - 2 * t) / cols
    for z in z_shelves:
        util.box(bm_w, (W - 2 * t, D, 0.03), loc=(0, 0, z))
    for c in range(1, cols):
        util.box(bm_w, (0.025, D - 0.006, H - 0.126), loc=(-W / 2 + t + c * cw, 0, H / 2 + 0.037))
    util.box(bm_w, (W - 2 * t - 0.006, 0.04, 0.1), loc=(0, -D / 2 + 0.023, 0.05))  # kick board inset between the sides
    for r in range(rows):
        z0, z1 = z_shelves[r] + 0.015, z_shelves[r + 1] - 0.015
        for c in range(cols):
            x0 = -W / 2 + t + c * cw + 0.02
            kind = rnd.random()
            if kind < 0.72:  # pile of scrolls, ends facing the viewer
                rr = rnd.uniform(0.03, 0.038)
                per = int((cw - 0.03) // (2 * rr))
                layers = int((z1 - z0) // (1.8 * rr))
                for ly in range(layers):
                    n = per - (ly % 2)
                    for i in range(n):
                        if rnd.random() < 0.12:
                            continue
                        x = x0 + rr + (ly % 2) * rr + i * 2 * rr
                        z = z0 + rr + ly * rr * 1.72
                        ln = rnd.uniform(0.34, 0.42)
                        scroll_roll(bm_p, bm_e, (x, -0.02 - (0.42 - ln) / 2, z), ln, rr * 0.95)
                        if rnd.random() < 0.3:
                            card(bm_tag, 0.03, 0.06, loc=(x, -0.02 - ln / 2 - 0.02, z - 0.035), rect=(0.1, 0.1, 0.3, 0.5))
            elif kind < 0.9:  # bound thread books lying flat
                z = z0
                for i in range(rnd.randint(3, 6)):
                    th = rnd.uniform(0.025, 0.04)
                    ubox(bm_bk, (0.2, 0.28, th), loc=(x0 + cw / 2 - 0.01 + rnd.uniform(-0.02, 0.02), -0.04,
                                                       z + th / 2), yaw=R(rnd.uniform(-8, 8)))
                    ubox(bm_pg, (0.19, 0.26, th * 0.7), loc=(x0 + cw / 2 - 0.01, -0.045, z + th / 2))
                    z += th
            else:  # a lacquered scroll case standing upright
                util.cylinder(bm_bk, 0.06, 0.06, z1 - z0 - 0.04, loc=(x0 + cw / 2, 0.0, (z0 + z1) / 2 - 0.02),
                              segs=12)
    objs = [obj("RackFrame", bm_w, m["rosewood"], uv=1.2), obj("Scrolls", bm_p, m["paper"], uv=3.0, smooth=True),
            obj("ScrollKnobs", bm_e, m["lacquer_red"], uv=4.0, smooth=True), obj("ScrollTags", bm_tag, m["talisman"]),
            obj("BookCovers", bm_bk, m["silk_blue"], uv=3.0), obj("BookPages", bm_pg, m["paper"], uv=6.0)]
    objs.append(util.collider("RackCol", (W + 0.08, D + 0.04, H + 0.06), (0, 0, (H + 0.06) / 2)))
    return objs


def war_drum():
    """Great war drum on a red lacquer cradle, hide heads studded with brass nails,
    drumsticks racked on the frame (~1.7 x 1.3 x 2.4 m)."""
    m = Mats()
    bm_f, bm_d, bm_h, bm_n, bm_st, bm_k, bm_r = (bmesh.new() for _ in range(7))
    c = V((0, 0, 1.5))
    L, Re, Rm = 1.0, 0.62, 0.74
    rot = Matrix.Rotation(R(-90), 4, "X")
    prof = [(Re, -L / 2), (Re + 0.03, -L / 2 + 0.02)] + [(Re + (Rm - Re) * math.sin(math.pi * t), -L / 2 + L * t)
                                                          for t in np.linspace(0.05, 0.95, 9)] + [(Re + 0.03, L / 2 - 0.02),
                                                                                                    (Re, L / 2)]
    vs = new_verts(bm_d, lambda: lathe_n(bm_d, prof, segs=40, u_rep=2.0))
    bmesh.ops.transform(bm_d, matrix=Matrix.Translation(c) @ rot, verts=vs)
    for sy in (-1, 1):  # hide heads (planar disc uv)
        uvl = bm_h.loops.layers.uv.verify()
        ring = [bm_h.verts.new(c + V((math.cos(a) * Re, sy * L / 2, math.sin(a) * Re)))
                for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
        f = bm_h.faces.new(ring if sy > 0 else list(reversed(ring)))
        for loop in f.loops:
            co = loop.vert.co - c
            loop[uvl].uv = ((co.x * (-sy)) / (2 * Re) + 0.5, co.z / (2 * Re) + 0.5)
        for k in range(36):  # brass nails
            a = 2 * math.pi * k / 36
            util.sphere(bm_n, 0.018, loc=c + V((math.cos(a) * (Re + 0.02), sy * (L / 2 - 0.035),
                                                  math.sin(a) * (Re + 0.02))), segs=6, rings=4)
        hoop(bm_n, c + V((0, sy * (L / 2 - 0.012), 0)), Re + 0.012, 0.012, normal=(0, 1, 0), segs=40, n=5)
    for sx in (-1, 1):  # side rings
        hoop(bm_n, c + V((sx * (Rm + 0.03), 0, -0.1)), 0.09, 0.012, normal=(0, 1, 0), segs=16, n=5)
    # cradle frame
    for sx in (-1, 1):
        for sy in (-1, 1):
            bevel_box(bm_f, (0.1, 0.1, 1.0), loc=(sx * 0.68, sy * 0.45, 0.5), bevel=0.012)
        bevel_box(bm_f, (0.12, 1.25, 0.12), loc=(sx * 0.68, 0, 0.08), bevel=0.015)
        # rails 12 mm slimmer than the 0.1 m posts they join, so their sides don't share the posts' planes
        bevel_box(bm_f, (0.088, 1.05, 0.088), loc=(sx * 0.68, 0, 0.95), bevel=0.012)
    for sy in (-1, 1):
        bevel_box(bm_f, (1.44, 0.088, 0.088), loc=(0, sy * 0.45, 0.4), bevel=0.012)
        # crescent saddle under the drum
        arc = [c + V((math.sin(a) * (Rm - 0.02), sy * 0.32, -math.cos(a) * (Rm - 0.02))) for a in np.linspace(-0.9, 0.9, 12)]
        util.tube(bm_f, arc, (0.06, 0.05), n=6, power=4)
        util.box(bm_f, (0.08, 0.08, 0.26), loc=(0, sy * 0.32, 0.9))
    # drumsticks racked across the front legs
    for k, dz in enumerate((0.62, 0.7)):
        a, b = V((-0.55, -0.56, dz)), V((0.2 + 0.08 * k, -0.56, dz + 0.05))
        util.tube(bm_st, [a, b], lambda t: 0.018 + 0.006 * t, n=8)
        util.sphere(bm_k, 0.045, loc=b + V((0.03, 0, 0.004)), segs=10, rings=6)
    for sx in (-0.6, 0.35):
        util.box(bm_f, (0.04, 0.08, 0.12), loc=(sx, -0.52, 0.64))
    objs = [obj("DrumFrame", bm_f, m["lacquer_red"], uv=1.2), obj("DrumBody", bm_d, m["lacquer_red"], smooth=True),
            obj("DrumHeads", bm_h, util.material("qp_drum_skin", drum_skin(256), normal_strength=0.4)),
            obj("DrumNails", bm_n, m["brass"], uv=4.0, smooth=True),
            obj("Drumsticks", bm_st, m["wood_light"], uv=3.0, smooth=True),
            obj("DrumstickKnobs", bm_k, m["silk_red"], uv=4.0, smooth=True)]
    objs.append(util.collider("DrumCol", (1.6, 1.3, 2.3), (0, 0, 1.15)))
    return objs


def sealed_coffin():
    """Black lacquer coffin bound in iron chains and glowing talismans, raised on stone
    trestles (~1.0 x 2.5 x 1.25 m)."""
    m = Mats()
    bm_c, bm_l, bm_s, bm_ch, bm_t, bm_g = (bmesh.new() for _ in range(6))
    base = 0.36

    def section(t, grow=0.0):
        w = 0.3 + 0.12 * t + grow
        h = 0.28 + 0.14 * t + grow
        return w, h

    stations = np.linspace(-1.1, 1.1, 9)
    rings = []
    for y in stations:
        t = (y + 1.1) / 2.2
        w, h = section(t)
        rings.append(util.ring((0, y, base + h), (1, 0, 0), (0, 0, 1), w, h, 16, power=5))
    util.loft(bm_c, rings, closed=True, cap_start=True, cap_end=True, uv_scale=(2.0, 0.6))
    bmesh.ops.recalc_face_normals(bm_c, faces=bm_c.faces)  # the end caps were wound inward (culled)
    rings = []
    for y in np.linspace(-1.16, 1.16, 9):
        t = (y + 1.16) / 2.32
        w, h = section(t, 0.04)
        pts = util.ring((0, y, base + 2 * h - 0.06), (1, 0, 0), (0, 0, 1), w, 0.12, 16, power=3)
        rings.append(pts)
    util.loft(bm_l, rings, closed=True, cap_start=True, cap_end=True, uv_scale=(2.0, 0.6))
    bmesh.ops.recalc_face_normals(bm_l, faces=bm_l.faces)
    for y in (-0.7, 0.7):
        bevel_box(bm_s, (0.95, 0.36, base), loc=(0, y, base / 2), bevel=0.03)
    # gold longevity medallion on the head end
    w, h = section(1.0)
    util.cylinder(bm_g, 0.16, 0.16, 0.02, loc=(0, 1.114, base + h + 0.02), segs=24, rot=Matrix.Rotation(R(90), 4, "X"))
    hoop(bm_g, (0, 1.124, base + h + 0.02), 0.16, 0.012, normal=(0, 1, 0), segs=24, n=5)
    # chains wrapped around at three stations
    for y in (-0.65, 0.05, 0.72):
        t = (y + 1.1) / 2.2
        w, h = section(t, 0.05)
        loop = util.ring((0, y, base + h + 0.02), (1, 0, 0), (0, 0, 1), w + 0.035, h + 0.05, 20, power=4)
        loop = [p for p in loop if p.z > base - 0.02]
        chain(bm_ch, loop, link=0.12, r=0.013)  # over the top only; the chord back underneath overlapped
    # talismans pasted on the lid and hanging on the sides
    rnd = random.Random(5)
    for k, y in enumerate(np.linspace(-0.85, 0.85, 6)):
        t = (y + 1.1) / 2.2
        w, h = section(t, 0.04)
        top = base + 2 * h - 0.06 + 0.12 + 0.004
        card(bm_t, 0.1, 0.34, loc=(rnd.uniform(-0.1, 0.1), y, top), pitch=R(-90), yaw=R(rnd.uniform(-20, 20)),
             rect=(0, 0, 1, 1))
    for k, y in enumerate((-0.4, 0.4)):
        for sx in (-1, 1):
            t = (y + 1.1) / 2.2
            w, h = section(t, 0.04)
            card(bm_t, 0.09, 0.3, loc=(sx * (w + 0.012), y, base + h * 1.1), yaw=R(90 * sx), roll=R(rnd.uniform(-8, 8)))
    objs = [obj("Coffin", bm_c, m["lacquer_black"], smooth=True), obj("CoffinLid", bm_l, m["lacquer_black"],
                                                                     smooth=True),
            obj("CoffinTrestles", bm_s, m["dark_stone"], uv=1.2), obj("CoffinChains", bm_ch, m["iron"], uv=3.0,
                                                                        smooth=True),
            obj("Talismans", bm_t, m["talisman"]), obj("CoffinMedallion", bm_g, m["gold"], uv=4.0, smooth=True)]
    objs.append(util.collider("CoffinCol", (1.0, 2.45, 1.3), (0, 0, 0.65)))
    return objs


def offering_table():
    """Temple offering table: red lacquer altar table with an embroidered runner, fruit,
    buns, wine cups, a censer and tall candles (~1.9 x 0.75 x 1.3 m)."""
    m = Mats()
    bm_t, bm_cl, bm_p, bm_fr, bm_o, bm_bu, bm_c, bm_f, bm_b, bm_s, bm_e, bm_cup = (bmesh.new() for _ in range(12))
    W, D, H = 1.8, 0.7, 0.88
    altar_table(bm_t, W, D, H)
    # runner: over the top and hanging down the front
    card(bm_cl, 0.62, D + 0.02, loc=(0, 0, H + 0.003), pitch=R(-90), rect=(0, 0.5, 1, 1))
    card(bm_cl, 0.62, 0.5, loc=(0, -D / 2 - 0.012, H - 0.24), rect=(0, 0, 1, 0.5), cols=4, rows=3,
         bend=lambda x, z: -0.01 * math.sin(x * 20))
    s = 256
    trim = tex.embroidery_trim("#8e1a14", "#d9ab45", s, 741)
    runner = util.material("qp_runner", trim, double_sided=True, normal_strength=0.4)
    for k, x in enumerate((-0.6, 0.6)):
        plate(bm_p, (x, 0.05, H), 0.14)
        if k == 0:
            for i in range(4):
                a = 2 * math.pi * i / 4
                peach(bm_fr, (x + math.cos(a) * 0.055, 0.05 + math.sin(a) * 0.055, H + 0.07))
            peach(bm_fr, (x, 0.05, H + 0.14))
        else:
            for i in range(4):
                a = 2 * math.pi * i / 4 + 0.4
                util.sphere(bm_o, 0.045, loc=(x + math.cos(a) * 0.055, 0.05 + math.sin(a) * 0.055, H + 0.065),
                            segs=10, rings=7)
            util.sphere(bm_o, 0.045, loc=(x, 0.05, H + 0.13), segs=10, rings=7)
    plate(bm_p, (-0.22, 0.12, H), 0.13)
    for i, (dx, dy, dz) in enumerate(((-0.05, -0.03, 0.04), (0.05, -0.03, 0.04), (0, 0.05, 0.04), (0, 0.0, 0.1))):
        util.sphere(bm_bu, 0.055, loc=(-0.22 + dx, 0.12 + dy, H + dz), segs=10, rings=7, scale=(1, 1, 0.75))
    for i in range(3):
        cup(bm_cup, (0.12 + i * 0.1, -0.18, H), 0.03, 0.035)
    incense_pot(bm_b, bm_s, bm_e, (0.2, 0.12, H), 1.3, sticks=5, seed=7)
    for sx in (-1, 1):
        util.lathe(bm_b, [(0.07, 0.0), (0.07, 0.015), (0.025, 0.04), (0.02, 0.14), (0.06, 0.15), (0.06, 0.17),
                          (0.001, 0.17)], segs=14, loc=(sx * 0.8, 0.18, H))
        candle(bm_c, bm_f, (sx * 0.8, 0.18, H + 0.17), h=0.36, r=0.035)
    objs = [obj("OfferingTable", bm_t, m["lacquer_red"], uv=1.5), obj("Runner", bm_cl, runner),
            obj("Plates", bm_p, m["porcelain"], uv=4.0, smooth=True), obj("Peaches", bm_fr, m["fruit"], smooth=True),
            obj("Oranges", bm_o, m["orange"], smooth=True), obj("Buns", bm_bu, m["bun"], smooth=True),
            obj("WineCups", bm_cup, m["celadon"], uv=6.0, smooth=True),
            obj("Candles", bm_c, m["candle"], smooth=True), obj("Flames", bm_f, m["flame"], smooth=True),
            obj("Censer", bm_b, m["brass"], uv=3.0, smooth=True), obj("Incense", bm_s, m["candle"]),
            obj("Embers", bm_e, m["ember"])]
    objs.append(util.collider("OfferingCol", (1.9, 0.75, 1.0), (0, 0, 0.5)))
    return objs


def rune_pillar():
    """Octagonal formation pillar of dark stone carved with glowing runes, a floating rune
    ring and a spirit crystal (~1.6 x 1.6 x 4.4 m)."""
    m = Mats()
    bm_b, bm_sh, bm_cap, bm_ring, bm_cr = (bmesh.new() for _ in range(5))
    realms.prism(bm_b, [(0.8, 0.0), (0.8, 0.22), (0.7, 0.28), (0.62, 0.28), (0.62, 0.45), (0.5, 0.5)], sides=8,
                 rot=R(22.5), v_scale=0.6)
    realms.prism(bm_sh, [(0.44, 0.45), (0.4, 3.35)], sides=8, rot=R(22.5), cap_top=False)
    realms.prism(bm_cap, [(0.46, 3.35), (0.58, 3.45), (0.58, 3.55), (0.4, 3.62), (0.25, 3.7)], sides=8,
                 rot=R(22.5), v_scale=0.6)
    for k in range(8):
        a = R(22.5 + 45 * k)
        util.sphere(bm_cap, 0.07, loc=(math.cos(a) * 0.58, math.sin(a) * 0.58, 3.5), segs=8, rings=5)
    # floating rings and crystal
    hoop(bm_ring, (0, 0, 2.3), 0.72, 0.02, segs=48, n=6, rx=0.05)
    hoop(bm_ring, (0, 0, 1.2), 0.66, 0.015, segs=48, n=6, rx=0.04)
    for k in range(12):
        a = 2 * math.pi * k / 12
        vs = util.box(bm_ring, (0.08, 0.02, 0.12), loc=(0, 0, 0))
        xf(bm_ring, vs, (math.cos(a) * 0.72, math.sin(a) * 0.72, 2.3), yaw=a + R(90))
    cr = new_verts(bm_cr, lambda: realms.prism(bm_cr, [(0.001, 0.0), (0.2, 0.35), (0.001, 0.9)], sides=6))
    xf(bm_cr, cr, (0, 0, 3.8))
    runes = realms.rune_stone(512, 791, "#2a2d33", "#56e8ff", cols=1, rows=10)
    rmat = util.material("qp_rune_stone", runes, emission_map=runes["emit"], emission_strength=3.0,
                         normal_strength=0.8)
    crystal = util.material("qp_rune_crystal", color="#8ff4ff", rough=0.05, emission="#35c8ff",
                            emission_strength=3.5, alpha=0.9)
    objs = [obj("PillarBase", bm_b, m["dark_stone"], uv=0.8), obj("PillarShaft", bm_sh, rmat),
            obj("PillarCap", bm_cap, m["dark_stone"], uv=0.8, smooth=False),
            obj("RuneRings", bm_ring, m["spirit"], smooth=True), obj("PillarCrystal", bm_cr, crystal)]
    bm = bmesh.new()
    realms.prism(bm, [(0.8, 0.0), (0.8, 0.5), (0.5, 3.7)], sides=8, rot=R(22.5))
    objs.append(hull("PillarCol", bm))
    return objs


def armillary_sphere():
    """Bronze armillary sphere: horizon, meridian, equatorial and ecliptic rings with a
    sighting tube, held by four dragon columns on a stone cross base (~2.0 x 2.0 x 2.4 m)."""
    m = Mats()
    bm_s, bm_b, bm_g = bmesh.new(), bmesh.new(), bmesh.new()
    for k, yaw in enumerate((0, R(90))):  # crossing beams differ by 6 mm in height (no shared top/bottom)
        vs = ubox(bm_s, (2.0, 0.34 - 0.006 * k, 0.24 + 0.006 * k), bevel=0.03)
        xf(bm_s, vs, (0, 0, 0.12 + 0.006 * k), yaw=yaw)
    bevel_box(bm_s, (0.5, 0.5, 0.396), loc=(0, 0, 0.202), bevel=0.04)
    c = V((0, 0, 1.4))
    lat = R(35)
    polar = V((0, math.cos(lat), math.sin(lat)))
    hoop(bm_b, c, 0.95, 0.03, normal=(0, 0, 1), segs=64, n=6, rx=0.07)           # horizon (flat, wide)
    hoop(bm_b, c, 0.88, 0.035, normal=(1, 0, 0), segs=64, n=6)                  # meridian
    hoop(bm_g, c, 0.8, 0.028, normal=polar, segs=64, n=6)                       # equator
    ecl = (Matrix.Rotation(R(23.5), 3, "X") @ polar).normalized()
    hoop(bm_g, c, 0.76, 0.02, normal=ecl, segs=64, n=6)                         # ecliptic
    hoop(bm_b, c, 0.66, 0.025, normal=polar.cross(V((1, 0, 0))), segs=48, n=6)  # declination ring
    util.tube(bm_b, [c - polar * 0.98, c + polar * 0.98], 0.02, n=8)            # polar axis
    util.tube(bm_g, [c - polar.cross(V((1, 0, 0))).normalized() * 0.6 + V((0, 0, 0)),
                     c + polar.cross(V((1, 0, 0))).normalized() * 0.6], 0.03, n=10)  # sighting tube (thinner than the meridian ring)
    util.sphere(bm_g, 0.07, loc=c, segs=12, rings=8)
    # meridian cradle post
    util.lathe(bm_b, [(0.14, 0.4), (0.1, 0.46), (0.07, 0.52), (0.07, 0.5 + 0.02)], segs=12)
    util.tube(bm_b, [V((0, 0, 0.404)), V((0, 0, 0.52))], 0.08, n=10)
    # dragon columns: posts wrapped in a scaled spiral body with a head under the horizon ring
    for k in range(4):
        a = R(90 * k)  # on the arms of the cross base (at 45 degrees they hovered 0.24 m over the ground)
        p = V((math.cos(a) * 0.72, math.sin(a) * 0.72, 0.24 + 0.003 * (k % 2)))
        top = p + V((0, 0, c.z - 0.24))
        util.cylinder(bm_b, 0.06, 0.05, top.z - p.z - 0.01, loc=(p.x, p.y, (p.z + 0.01 + top.z) / 2), segs=10)
        spiral = [p + V((math.cos(t * 7) * 0.08, math.sin(t * 7) * 0.08, t * (top.z - p.z - 0.15)))
                  for t in np.linspace(0, 1, 40)]
        util.tube(bm_g, spiral, lambda t: 0.045 * (1 - 0.3 * t), n=7)
        util.sphere(bm_g, 0.07, loc=top + V((0, 0, -0.1)) - V((p.x, p.y, 0)).normalized() * 0.06, segs=10, rings=6,
                    scale=(1, 1, 0.8))
        util.cylinder(bm_b, 0.09, 0.09, 0.06, loc=(p.x, p.y, p.z + 0.03), segs=10)
    objs = [obj("ArmillaryBase", bm_s, m["stone"], uv=1.0), obj("ArmillaryBronze", bm_b, m["bronze"], uv=2.0,
                                                                smooth=True),
            obj("ArmillaryGilt", bm_g, m["gold"], uv=3.0, smooth=True)]
    objs.append(util.collider("ArmillaryCol", (2.0, 2.0, 2.4), (0, 0, 1.2)))
    return objs


def medicine_cabinet():
    """Apothecary's hundred-drawer cabinet with labelled drawers, brass pulls and jars on
    top (~1.95 x 0.55 x 2.2 m)."""
    m = Mats()
    rnd = random.Random(21)
    bm_c, bm_d, bm_p, bm_j, bm_l = (bmesh.new() for _ in range(5))
    W, D, H = 1.9, 0.5, 1.95
    for sx in (-1, 1):
        bevel_box(bm_c, (0.05, D, H), loc=(sx * (W / 2 - 0.025), 0, H / 2), bevel=0.01)
    bevel_box(bm_c, (W + 0.06, D + 0.04, 0.06), loc=(0, 0, H + 0.03), bevel=0.015)
    bevel_box(bm_c, (W - 0.006, D - 0.006, 0.12), loc=(0, 0, 0.062), bevel=0.01)  # plinth inset 3 mm
    util.box(bm_c, (W - 0.106, 0.02, H - 0.12), loc=(0, D / 2 - 0.01, H / 2 + 0.06))
    cols, rows = 8, 8
    z0, z1 = 0.14, H - 0.04
    cw, ch = (W - 0.1) / cols, (z1 - z0) / rows
    for r in range(rows + 1):
        util.box(bm_c, (W - 0.1, D - 0.02, 0.018), loc=(0, 0, z0 + r * ch))
    for c in range(1, cols):
        # dividers 4 mm shallower than the shelves: their fronts were coplanar with the shelf fronts
        util.box(bm_c, (0.018, D - 0.028, z1 - z0), loc=(-W / 2 + 0.05 + c * cw, 0, (z0 + z1) / 2))
    for r in range(rows):
        for c in range(cols):
            x = -W / 2 + 0.05 + (c + 0.5) * cw
            z = z0 + (r + 0.5) * ch
            q = rnd.randrange(16)
            rect = ((q % 4) / 4, (q // 4) / 4, (q % 4 + 1) / 4, (q // 4 + 1) / 4)
            out = 0.0 if rnd.random() > 0.06 else rnd.uniform(0.05, 0.12)  # a few drawers left ajar
            ubox(bm_d, (cw - 0.022, 0.03, ch - 0.02), loc=(x, -D / 2 + 0.02 - out, z), rect=rect)
            util.cylinder(bm_p, 0.012, 0.012, 0.03, loc=(x, -D / 2 - out - 0.01, z - ch * 0.12), segs=8,
                          rot=Matrix.Rotation(R(90), 4, "X"))
            hoop(bm_p, (x, -D / 2 - out - 0.025, z - ch * 0.12 - 0.018), 0.018, 0.004, normal=(0, 1, 0), segs=12,
                 n=4)
    for k, x in enumerate((-0.65, -0.2, 0.3, 0.7)):
        s = [0.8, 1.0, 0.7, 0.9][k]
        util.lathe(bm_j, [(0.001, 0), (0.08 * s, 0), (0.12 * s, 0.1 * s), (0.13 * s, 0.18 * s), (0.08 * s, 0.26 * s),
                          (0.06 * s, 0.3 * s), (0.07 * s, 0.32 * s), (0.001, 0.32 * s)], segs=16,
                   loc=(x, 0.02, H + 0.06))
        util.sphere(bm_l, 0.075 * s, loc=(x, 0.02, H + 0.06 + 0.33 * s), segs=12, rings=6, scale=(1, 1, 0.5))
    drawers = util.material("qp_drawers", drawer_atlas(512), normal_strength=0.6)
    objs = [obj("CabinetCarcass", bm_c, m["rosewood"], uv=1.2), obj("Drawers", bm_d, drawers),
            obj("DrawerPulls", bm_p, m["brass"], uv=4.0, smooth=True),
            obj("HerbJars", bm_j, m["celadon"], uv=3.0, smooth=True),
            obj("JarCloths", bm_l, m["silk_red"], uv=4.0, smooth=True)]
    objs.append(util.collider("CabinetCol", (W + 0.06, D + 0.1, H + 0.06), (0, -0.03, (H + 0.06) / 2)))
    return objs


def wine_jars():
    """Five glazed wine jars sealed with red cloth, rope and paper labels (~1.7 x 1.1 x 0.95 m)."""
    m = Mats()
    bm_j, bm_c, bm_r, bm_l = (bmesh.new() for _ in range(4))
    s = 256
    u, v = tex.grid(s)
    n = tex.fbm(s, 6, 4, 0.5, 801)
    drip = 0.3 + 0.08 * tex.fbm(s, 8, 3, 0.5, 802)[0][None, :]
    glazed = tex.sstep(drip - 0.02, drip + 0.02, v)
    col = tex.lerp(tex.srgb("#a0643c") * (0.85 + 0.2 * n)[..., None], tex.srgb("#3a2012") * (0.8 + 0.4 * n)[..., None],
                   glazed)
    col = tex.lerp(col, tex.srgb("#1a0f08"), tex.sstep(0.93, 0.97, v))
    jar = util.material("qp_jar_glaze", tex.result(col, tex.lerp(0.85, 0.18, glazed), 0.0, n * 0.2),
                        normal_strength=0.3)
    lab = ink_paper("#c42a22", 256, 803, 1, 1, ink="#140c08", box=(0.25, 0.25, 0.75, 0.75), stroke=0.05, seal=False)
    label = util.material("qp_wine_label", lab, double_sided=True, normal_strength=0.2)
    specs = [(-0.52, 0.25, 1.0), (0.05, 0.3, 0.95), (0.58, 0.22, 0.9), (-0.25, -0.3, 0.75), (0.35, -0.28, 0.7)]
    for k, (x, y, sc) in enumerate(specs):
        H = 0.9 * sc
        prof = [(0.001, 0.0), (0.2 * sc, 0.0), (0.26 * sc, 0.1 * H), (0.33 * sc, 0.42 * H), (0.3 * sc, 0.7 * H),
                (0.17 * sc, 0.86 * H), (0.12 * sc, 0.9 * H), (0.14 * sc, 0.94 * H), (0.13 * sc, 0.96 * H)]
        lathe_n(bm_j, prof, segs=28, loc=(x, y, 0), cap_bottom=True)
        # cloth cap over the mouth, tied with rope
        util.lathe(bm_c, [(0.001, 1.04 * H), (0.1 * sc, 1.02 * H), (0.17 * sc, 0.96 * H), (0.2 * sc, 0.88 * H),
                          (0.21 * sc, 0.82 * H)], segs=16, loc=(x, y, 0))
        hoop(bm_r, (x, y, 0.92 * H), 0.165 * sc, 0.012, segs=20, n=5)
        a = R(-90 + (k * 23) % 40 - 20)
        rr = 0.33 * sc
        card(bm_l, 0.16 * sc, 0.16 * sc, loc=(x + math.cos(a) * (rr + 0.005), y + math.sin(a) * (rr + 0.005), 0.45 * H),
             yaw=a + R(90), roll=R(45))
    objs = [obj("WineJars", bm_j, jar, smooth=True), obj("JarCloths", bm_c, m["silk_red"], uv=4.0, smooth=True),
            obj("JarRopes", bm_r, m["rope"], uv=6.0, smooth=True), obj("JarLabels", bm_l, label)]
    objs.append(util.collider("JarsCol", (1.75, 1.15, 0.9), (0.03, 0.0, 0.45)))
    return objs


def loom():
    """Wooden treadle loom mid-weave: warp threads, heddles, beater, a bolt of patterned silk
    on the cloth beam, treadles and the weaver's bench (~1.4 x 2.4 x 1.8 m)."""
    m = Mats()
    bm_w, bm_warp, bm_cloth, bm_roll, bm_str = (bmesh.new() for _ in range(5))
    hw = 0.62
    for sx in (-1, 1):
        x = sx * hw
        # joined members differ by >= 6 mm in section so no two faces share a plane
        bevel_box(bm_w, (0.092, 1.9, 0.08), loc=(x, 0, 0.04), bevel=0.01)
        bevel_box(bm_w, (0.08, 0.08, 0.95), loc=(x, -0.85, 0.478), bevel=0.01)
        bevel_box(bm_w, (0.08, 0.08, 1.75), loc=(x, 0.8, 0.878), bevel=0.01)
        bevel_box(bm_w, (0.07, 0.08, 1.6), loc=(x, 0.05, 0.803), bevel=0.01)
        bevel_box(bm_w, (0.062, 1.72, 0.062), loc=(x, 0.0, 1.62), bevel=0.01)
        util.tube(bm_w, [V((x, -0.85, 0.5)), V((x, 0.8, 0.35))], 0.03, n=6)
    bevel_box(bm_w, (2 * hw + 0.1, 0.06, 0.08), loc=(0, -0.85, 0.88), bevel=0.01)  # breast beam
    bevel_box(bm_w, (2 * hw + 0.1, 0.07, 0.08), loc=(0, 0.05, 1.62), bevel=0.01)
    bevel_box(bm_w, (2 * hw + 0.1, 0.06, 0.06), loc=(0, 0.8, 1.72), bevel=0.01)
    util.cylinder(bm_w, 0.07, 0.07, 2 * hw, loc=(0, 0.72, 0.55), segs=14, rot=Matrix.Rotation(R(90), 4, "Y"))
    # heddle frames and the beater hanging from the top rail
    for y in (0.05, 0.16):
        for z in (0.72, 1.12):
            util.box(bm_w, (2 * hw - 0.1, 0.03, 0.03), loc=(0, y, z))
        card(bm_str, 2 * hw - 0.14, 0.38, loc=(0, y, 0.92), rect=(0, 0, 8, 1))
        for sx in (-1, 1):
            util.tube(bm_w, [V((sx * 0.4, y, 1.12)), V((sx * 0.4, 0.05, 1.6))], 0.006, n=4)
    for sx in (-1, 1):
        util.box(bm_w, (0.04, 0.04, 0.8), loc=(sx * (hw - 0.08), -0.3, 1.2))
    util.box(bm_w, (2 * hw - 0.14, 0.06, 0.05), loc=(0, -0.3, 0.8))  # ends inside the beater uprights
    util.box(bm_w, (2 * hw - 0.14, 0.03, 0.04), loc=(0, -0.3, 1.1))
    card(bm_str, 2 * hw - 0.2, 0.28, loc=(0, -0.3, 0.95), rect=(0, 0, 10, 1))
    # warp from the warp beam up over the heddles to the fell; woven cloth from the fell to the breast beam
    card(bm_warp, 2 * hw - 0.2, 1.08, loc=(0, 0.24, 0.72), pitch=R(-90) + math.atan2(0.17, 1.0), rect=(0, 0, 12, 1))
    card(bm_cloth, 2 * hw - 0.2, 0.58, loc=(0, -0.57, 0.885), pitch=R(-90), rect=(0, 0, 1, 1))
    util.cylinder(bm_roll, 0.1, 0.1, 2 * hw - 0.2, loc=(0, -0.85, 0.72), segs=18, rot=Matrix.Rotation(R(90), 4, "Y"))
    # treadles and bench
    for sx in (-0.18, 0.0, 0.18):
        util.box(bm_w, (0.08, 0.9, 0.03), loc=(sx, -0.3, 0.08))
    util.cylinder(bm_w, 0.03, 0.03, 0.5, loc=(0, 0.1, 0.06), segs=6, rot=Matrix.Rotation(R(90), 4, "Y"))
    bevel_box(bm_w, (1.0, 0.3, 0.05), loc=(0, -1.25, 0.5), bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm_w, (0.05, 0.05, 0.48), loc=(sx * 0.42, -1.25 + sy * 0.1, 0.24))
    # shuttle resting on the cloth
    util.sphere(bm_roll, 0.03, loc=(0.2, -0.45, 0.905), segs=10, rings=6, scale=(4, 1, 0.7))
    s = 256
    u, v = tex.grid(s)
    threads = (np.sin(u * s * math.pi / 2) * 0.5 + 0.5)
    wc = tex.lerp(tex.srgb("#cfc4ae"), tex.srgb("#f0e8d8"), threads)
    warp_maps = tex.result(wc, 0.7, 0.0, threads * 0.5)
    warp_maps["alpha"] = tex.sstep(0.35, 0.55, threads)
    warp = lands.clip_alpha(util.material("qp_warp_threads", warp_maps, alpha=warp_maps["alpha"], double_sided=True,
                                          normal_strength=0.3))
    brocade = util.material("qp_brocade", tex.silk("#2f5a8a", "#d8b060", 256, 804, motif_count=9, motif_scale=0.09),
                            double_sided=True, normal_strength=0.3)
    objs = [obj("LoomFrame", bm_w, m["wood_light"], uv=1.2), obj("Warp", bm_warp, warp),
            obj("WovenCloth", bm_cloth, brocade), obj("ClothRoll", bm_roll, brocade, uv=2.0, smooth=True),
            obj("Heddles", bm_str, warp)]
    objs.append(util.collider("LoomCol", (1.4, 1.85, 1.8), (0, -0.02, 0.9)))
    objs.append(util.collider("BenchCol", (1.0, 0.32, 0.52), (0, -1.25, 0.26)))
    return objs


def map_table():
    """War-room map table: a painted campaign map under brass weights, army tokens, flags,
    a geomancer's compass, brush and candle (~2.3 x 1.5 x 1.0 m)."""
    m = Mats()
    bm_t, bm_map, bm_rl, bm_tk, bm_fl, bm_pin, bm_c, bm_f, bm_cp = (bmesh.new() for _ in range(9))
    W, D, H = 2.2, 1.4, 0.86
    bevel_box(bm_t, (W, D, 0.08), loc=(0, 0, H - 0.04), bevel=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            vs = ubox(bm_t, (0.1, 0.1, H - 0.08), loc=(sx * (W / 2 - 0.12), sy * (D / 2 - 0.12), (H - 0.08) / 2))
            for v in vs:
                if v.co.z < 0.05:
                    v.co.x += sx * 0.03
                    v.co.y += sy * 0.03
        util.box(bm_t, (0.05, D - 0.3, 0.12), loc=(sx * (W / 2 - 0.12), 0, H - 0.16))
    for sy in (-1, 1):
        util.box(bm_t, (W - 0.3, 0.05, 0.12), loc=(0, sy * (D / 2 - 0.12), H - 0.16))
    mw, md = W - 0.3, D - 0.2
    card(bm_map, mw, md, loc=(0, 0, H + 0.004), pitch=R(-90), cols=4, rows=2)
    for sx in (-1, 1):
        util.cylinder(bm_rl, 0.035, 0.035, md, loc=(sx * (mw / 2 + 0.03), 0, H + 0.035), segs=12,
                      rot=Matrix.Rotation(R(90), 4, "X"))
        for sy in (-1, 1):
            util.cylinder(bm_cp, 0.016, 0.016, 0.03, loc=(sx * (mw / 2 + 0.03), sy * (md / 2 + 0.02), H + 0.035),
                          segs=8, rot=Matrix.Rotation(R(90), 4, "X"))
    rnd = random.Random(31)
    for k in range(9):
        x, y = rnd.uniform(-0.8, 0.6), rnd.uniform(-0.5, 0.5)
        if k < 5:
            util.cylinder(bm_pin, 0.003, 0.003, 0.14, loc=(x, y, H + 0.07), segs=4)
            pennant(bm_fl, (x, y, H + 0.14), 0.06, 0.04, yaw=R(rnd.uniform(0, 360)))
        else:
            bevel_box(bm_tk, (0.05, 0.035, 0.04), loc=(x, y, H + 0.02), bevel=0.006)
            util.sphere(bm_tk, 0.015, loc=(x, y, H + 0.05), segs=6, rings=4)
    # geomancer's compass (luopan) and a brass paperweight
    util.cylinder(bm_cp, 0.13, 0.13, 0.03, loc=(0.82, -0.45, H + 0.015), segs=32)
    hoop(bm_cp, (0.82, -0.45, H + 0.03), 0.1, 0.006, segs=24, n=4)
    ubox(bm_cp, (0.12, 0.012, 0.004), loc=(0.82, -0.45, H + 0.034), yaw=R(30))
    bevel_box(bm_cp, (0.3, 0.05, 0.04), loc=(-0.2, 0.52, H + 0.02), bevel=0.01)
    util.lathe(bm_cp, [(0.06, 0.0), (0.06, 0.012), (0.02, 0.03), (0.018, 0.08), (0.04, 0.09), (0.001, 0.09)],
               segs=12, loc=(0.9, 0.5, H))
    candle(bm_c, bm_f, (0.9, 0.5, H + 0.09), h=0.18, r=0.028)
    parch = util.material("qp_war_map", map_parchment(1024), normal_strength=0.3)
    flags = util.material("qp_flag_silk", tex.silk("#b3261e", "#d24a3e", 128, 805), double_sided=True)
    objs = [obj("MapTable", bm_t, m["rosewood"], uv=1.2), obj("WarMap", bm_map, parch),
            obj("MapRollers", bm_rl, m["lacquer_black"], uv=2.0, smooth=True), obj("ArmyTokens", bm_tk, m["jade"],
                                                                                   uv=6.0),
            obj("MapFlags", bm_fl, flags), obj("FlagPins", bm_pin, m["iron"]),
            obj("TableBrass", bm_cp, m["brass"], uv=4.0, smooth=True),
            obj("Candle", bm_c, m["candle"], smooth=True), obj("CandleFlame", bm_f, m["flame"], smooth=True)]
    objs.append(util.collider("MapTableCol", (2.25, 1.45, 0.95), (0, 0, 0.475)))
    return objs


def crane_statue():
    """Bronze red-crowned crane on a rock pedestal, neck raised (~0.9 x 0.9 x 2.2 m)."""
    m = Mats()
    bm_p, bm_c, bm_k, bm_r = (bmesh.new() for _ in range(4))
    realms.prism(bm_p, [(0.46, 0.0), (0.46, 0.14), (0.4, 0.2), (0.36, 0.2), (0.36, 0.44), (0.42, 0.5),
                        (0.42, 0.58), (0.001, 0.6)], sides=8, rot=R(22.5), v_scale=0.8)
    lands.rock(bm_r, (0.05, 0.05, 0.62), (0.3, 0.26, 0.12), 41, 0.3, 2)
    z0 = 0.7
    # legs: thighs hidden in the body, thin shanks, backward knees, toes
    for sx in (-1, 1):
        hip = V((sx * 0.06, 0.05, z0 + 0.55))
        knee = V((sx * 0.07, 0.08, z0 + 0.3))
        foot = V((sx * 0.08, 0.02, z0 + 0.02))
        util.tube(bm_c, [hip, knee, foot], lambda t: 0.018 - 0.006 * t, n=6)
        util.sphere(bm_c, 0.022, loc=knee, segs=8, rings=5)
        for a in (-100, -70, -130, 90):
            d = V((math.cos(R(a)), math.sin(R(a)), 0))
            util.tube(bm_c, [foot, foot + d * 0.1 + V((0, 0, -0.012))], lambda t: 0.009 * (1 - 0.6 * t), n=5)
    # body, wings folded, tail plumes (black in life: darker patina)
    util.sphere(bm_c, 0.2, loc=(0, 0.05, z0 + 0.72), segs=18, rings=12, scale=(0.95, 1.6, 0.95))
    for sx in (-1, 1):
        vs = util.sphere(bm_c, 0.18, loc=(0, 0, 0), segs=14, rings=8, scale=(0.35, 1.8, 0.85))
        xf(bm_c, vs, (sx * 0.15, 0.12, z0 + 0.76), pitch=R(-12), yaw=R(-5 * sx))
    for k in range(7):
        a = R(-30 + 10 * k)
        tip = V((math.sin(a) * 0.12, 0.58 + math.cos(a) * 0.02, z0 + 0.48 - abs(k - 3) * 0.015))
        util.tube(bm_c, util.catmull([V((0, 0.35, z0 + 0.66)), V((math.sin(a) * 0.06, 0.48, z0 + 0.6)), tip], 3),
                  lambda t: 0.035 * (1 - 0.8 * t), n=6)
    # S-curved neck, head, long beak, red crown
    neck = util.catmull([V((0, -0.22, z0 + 0.8)), V((0, -0.32, z0 + 1.0)), V((0, -0.26, z0 + 1.2)),
                         V((0, -0.3, z0 + 1.38)), V((0, -0.36, z0 + 1.46))], 5)
    util.tube(bm_c, neck, lambda t: 0.06 - 0.03 * t, n=10)
    head = V((0, -0.38, z0 + 1.48))
    util.sphere(bm_c, 0.05, loc=head, segs=12, rings=8, scale=(0.9, 1.3, 0.95))
    util.tube(bm_c, [head + V((0, -0.04, -0.005)), head + V((0, -0.24, -0.06))], lambda t: 0.018 * (1 - 0.9 * t), n=6)
    util.sphere(bm_k, 0.03, loc=head + V((0, 0.0, 0.035)), segs=10, rings=6, scale=(1, 1.3, 0.5))
    objs = [obj("CranePedestal", bm_p, m["stone"], uv=1.2), obj("CraneRock", bm_r, m["weathered"], uv=1.5,
                                                                smooth=True),
            obj("Crane", bm_c, m["bronze"], uv=2.0, smooth=True), obj("CraneCrown", bm_k, m["red_paint"], smooth=True)]
    objs.append(util.collider("CraneCol", (0.92, 0.92, 1.9), (0, 0, 0.95)))
    return objs


def spirit_fountain():
    """Octagonal marble basin brimming with glowing spirit water, a lotus column pouring
    luminous streams from an upper bowl, crowned by a spirit bud (~3.1 x 3.1 x 2.1 m)."""
    m = Mats()
    bm_b, bm_c, bm_w, bm_s, bm_g, bm_bud = (bmesh.new() for _ in range(6))
    realms.prism(bm_b, [(1.55, 0.0), (1.55, 0.5), (1.6, 0.55), (1.6, 0.62), (1.42, 0.62), (1.42, 0.3)], sides=8,
                 rot=R(22.5), v_scale=0.6, cap_top=False)
    realms.prism(bm_b, [(1.42, 0.3), (0.001, 0.3)], sides=8, rot=R(22.5), v_scale=0.6, cap_top=False)
    realms.disc(bm_w, (0, 0), 1.42, segs=8, z=0.5)
    # column with lotus petals, upper bowl
    util.lathe(bm_c, [(0.3, 0.3), (0.26, 0.4), (0.18, 0.5), (0.16, 1.1), (0.22, 1.18), (0.3, 1.2)], segs=24)
    util.lathe(bm_c, [(0.3, 1.2), (0.55, 1.3), (0.68, 1.42), (0.7, 1.48), (0.64, 1.48), (0.5, 1.38), (0.001, 1.36)],
               segs=32)
    realms.disc(bm_w, (0, 0), 0.64, segs=32, z=1.45)
    for k in range(10):
        a = 2 * math.pi * k / 10
        vs = util.sphere(bm_c, 1.0, segs=10, rings=6, scale=(0.12, 0.04, 0.2))
        xf(bm_c, vs, (math.cos(a) * 0.24, math.sin(a) * 0.24, 0.62), yaw=a + R(90), pitch=R(-25))
    # spirit bud on top
    util.lathe(bm_g, [(0.001, 1.46), (0.06, 1.5), (0.08, 1.56), (0.001, 1.58)], segs=12)
    for k in range(6):
        a = 2 * math.pi * k / 6
        vs = util.sphere(bm_g, 1.0, segs=10, rings=6, scale=(0.07, 0.03, 0.16))
        xf(bm_g, vs, (math.cos(a) * 0.08, math.sin(a) * 0.08, 1.68), yaw=a + R(90), pitch=R(20))
    util.sphere(bm_bud, 0.09, loc=(0, 0, 1.72), segs=14, rings=10, scale=(1, 1, 1.3))
    util.sphere(bm_bud, 0.04, loc=(0, 0, 2.02), segs=8, rings=5)
    # luminous streams arcing from the bowl lip into the basin
    for k in range(8):
        a = 2 * math.pi * k / 8 + R(22.5)
        d = V((math.cos(a), math.sin(a), 0))
        pts = [d * (0.7 + 0.35 * t) + V((0, 0, 1.46 + 0.05 * math.sin(t * math.pi) - 0.97 * t ** 2))
               for t in np.linspace(0, 1, 10)]
        util.tube(bm_s, pts, lambda t: 0.025 + 0.01 * t, n=6)
    water = realms.liquid(256, 806, "#0f4a52", "#3fd0d8", "#6ff8ff")
    wmat = util.material("qp_spirit_water", water, emission_map=water["emit"], emission_strength=2.5,
                         normal_strength=0.4)
    stream = util.material("qp_spirit_stream", color="#a8faff", rough=0.1, emission="#6ff0ff", emission_strength=4.0,
                           alpha=0.75)
    objs = [obj("FountainBasin", bm_b, m["carved"]), obj("FountainColumn", bm_c, m["marble"], uv=1.5, smooth=True),
            obj("SpiritWater", bm_w, wmat), obj("SpiritStreams", bm_s, stream, smooth=True),
            obj("SpiritBudPetals", bm_g, m["jade"], uv=4.0, smooth=True), obj("SpiritBud", bm_bud, m["spirit"],
                                                                              smooth=True)]
    bm = bmesh.new()
    realms.prism(bm, [(1.6, 0.0), (1.6, 0.62)], sides=8, rot=R(22.5))
    objs.append(hull("FountainCol", bm))
    objs.append(util.collider("FountainColumnCol", (0.9, 0.9, 1.6), (0, 0, 1.2)))
    return objs


def puppet_frame():
    """Marionette theatre: red lacquer stage with brocade skirt and curtains, a carved
    proscenium, and three string puppets hanging from the control bar (~2.2 x 0.9 x 2.5 m)."""
    m = Mats()
    bm_st, bm_w, bm_cur, bm_sk, bm_str, bm_face, bm_rb = (bmesh.new() for _ in range(7))
    robes = [bmesh.new() for _ in range(3)]
    W, D, H = 2.1, 0.85, 0.8
    bevel_box(bm_st, (W, D, 0.06), loc=(0, 0, H - 0.03), bevel=0.012)
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm_st, (0.07, 0.07, H - 0.06), loc=(sx * (W / 2 - 0.05), sy * (D / 2 - 0.05), (H - 0.06) / 2))
        bevel_box(bm_st, (0.1, 0.1, 1.75), loc=(sx * (W / 2 - 0.06), D / 2 - 0.08, H + 0.87), bevel=0.012)
        bevel_box(bm_st, (0.09, 0.09, 1.5), loc=(sx * (W / 2 - 0.06), -D / 2 + 0.06, H + 0.75), bevel=0.012)
        util.box(bm_st, (0.07, D - 0.1, 0.07), loc=(sx * (W / 2 - 0.06), 0, H + 1.5))
    bevel_box(bm_st, (W + 0.2, 0.12, 0.22), loc=(0, -D / 2 + 0.06, H + 1.55), bevel=0.02)  # proscenium beam
    bevel_box(bm_st, (W, 0.07, 0.08), loc=(0, D / 2 - 0.08, H + 1.72), bevel=0.01)
    ubox(bm_st, (W - 0.1, 0.03, 1.6), loc=(0, D / 2 - 0.02, H + 0.8), rect=(0, 0, 1, 1))
    # gilded cloud corners on the proscenium
    for sx in (-1, 1):
        pts = [V((sx * (W / 2 - 0.1 - 0.25 * t), -D / 2, H + 1.45 - 0.2 * math.sin(t * math.pi * 0.5)))
               for t in np.linspace(0, 1, 10)]
        util.tube(bm_w, pts, lambda t: 0.03 * (1 - 0.5 * t), n=6)
    # curtains gathered at the sides
    for sx in (-1, 1):
        card(bm_cur, 0.34, 1.35, loc=(sx * (W / 2 - 0.26), -D / 2 + 0.1, H + 0.8), cols=8, rows=4,
             bend=lambda x, z: 0.04 * math.sin(x * 40) * (0.5 + (z + 0.675) / 1.35))
        util.tube(bm_w, [V((sx * (W / 2 - 0.4), -D / 2 + 0.06, H + 0.6)), V((sx * (W / 2 - 0.1), -D / 2 + 0.06, H + 0.62))],
                  0.012, n=5)
    # skirt around the stage front
    card(bm_sk, W, H - 0.06, loc=(0, -D / 2 - 0.005, (H - 0.06) / 2), cols=12, rows=2,
         bend=lambda x, z: -0.012 * math.sin(x * 30))
    # three marionettes
    cols_ = ["silk_red", "silk_blue", "silk_green"]
    for k, x in enumerate((-0.55, 0.0, 0.55)):
        base = V((x, -0.05, H))
        rb = robes[k]
        util.lathe(rb, [(0.001, 0.02), (0.1, 0.02), (0.08, 0.15), (0.06, 0.26), (0.05, 0.3), (0.001, 0.31)], segs=14,
                   loc=base)
        for sx in (-1, 1):
            util.tube(rb, [base + V((sx * 0.05, 0, 0.28)), base + V((sx * 0.12, -0.03, 0.18)),
                           base + V((sx * 0.14, -0.06, 0.1))], lambda t: 0.018 + 0.01 * t, n=6)
            util.sphere(bm_face, 0.015, loc=base + V((sx * 0.14, -0.07, 0.08)), segs=6, rings=4)
            util.box(bm_rb, (0.03, 0.05, 0.02), loc=base + V((sx * 0.035, -0.01, 0.01)))
        util.sphere(bm_face, 0.05, loc=base + V((0, 0, 0.36)), segs=12, rings=8, scale=(0.9, 0.9, 1.1))
        util.sphere(bm_rb, 0.052, loc=base + V((0, 0.01, 0.39)), segs=10, rings=6, scale=(1, 1, 0.7))  # hair
        util.cylinder(bm_rb, 0.012, 0.008, 0.06, loc=base + V((0, 0.01, 0.45)), segs=6)
        bar = V((x, -0.05, H + 1.3))
        util.box(bm_w, (0.22, 0.02, 0.02), loc=bar)
        util.box(bm_w, (0.026, 0.18, 0.014), loc=bar)
        util.tube(bm_w, [bar, bar + V((0, 0.02, 0.15))], 0.005, n=4)
        for p in (V((0, 0, 0.42)), V((-0.14, -0.06, 0.1)), V((0.14, -0.06, 0.1))):
            end = base + p
            util.tube(bm_str, [V((bar.x + p.x * 0.7, bar.y, bar.z)), end], 0.0018, n=3)
    util.box(bm_w, (1.6, 0.04, 0.04), loc=(0, -0.05, H + 1.45))
    util.tube(bm_w, [V((0, -0.05, H + 1.45)), V((0, D / 2 - 0.08, H + 1.72))], 0.012, n=5)
    skirt = util.material("qp_stage_skirt", tex.embroidery_trim("#7a1410", "#d9ab45", 256, 807), double_sided=True,
                          normal_strength=0.4)
    objs = [obj("Stage", bm_st, m["lacquer_red"], uv=1.2), obj("StageGilt", bm_w, m["gold"], uv=3.0, smooth=True),
            obj("Curtains", bm_cur, m["silk_red_ds"], uv=1.0), obj("StageSkirt", bm_sk, skirt),
            obj("PuppetStrings", bm_str, m["string"]), obj("PuppetFaces", bm_face, m["skin"], smooth=True),
            obj("PuppetHair", bm_rb, m["lacquer_black"], uv=6.0, smooth=True)]
    for k in range(3):
        objs.append(obj("PuppetRobe%d" % k, robes[k], m[cols_[k]], uv=5.0, smooth=True))
    objs.append(util.collider("StageCol", (W + 0.2, D, 2.55), (0, 0, 1.27)))
    return objs


def herb_drying_rack():
    """Bamboo drying rack: four tiers of woven trays of herbs, roots and mushrooms, with herb
    bundles hanging from the top rail (~1.8 x 0.8 x 1.95 m)."""
    m = Mats()
    rnd = random.Random(41)
    bm_b, bm_t, bm_h, bm_r, bm_mush, bm_st = (bmesh.new() for _ in range(6))
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.cylinder(bm_b, 0.03, 0.03, 1.95, loc=(sx * 0.85, sy * 0.32, 0.975), segs=8)
            for z in np.arange(0.3, 1.95, 0.4):
                util.sphere(bm_b, 0.034, loc=(sx * 0.85, sy * 0.32, z), segs=8, rings=4, scale=(1, 1, 0.3))
    for z in (0.28, 0.68, 1.08, 1.48, 1.9):
        for sy in (-1, 1):
            util.cylinder(bm_b, 0.022, 0.022, 1.76, loc=(0, sy * 0.32, z), segs=6, rot=Matrix.Rotation(R(90), 4, "Y"))
        for sx in (-1, 1):
            util.cylinder(bm_b, 0.02, 0.02, 0.7, loc=(sx * 0.85, 0, z), segs=6, rot=Matrix.Rotation(R(90), 4, "X"))
    for z in (0.3, 0.7, 1.1, 1.5):
        for x in (-0.42, 0.42):
            util.lathe(bm_t, [(0.001, z + 0.02), (0.36, z + 0.02), (0.38, z + 0.07), (0.34, z + 0.07),
                              (0.33, z + 0.035), (0.001, z + 0.035)], segs=24, loc=(x, 0, 0))
            kind = rnd.randrange(3)
            for i in range(14):
                a, rr = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()) * 0.27
                p = V((x + math.cos(a) * rr, math.sin(a) * rr, z + 0.05))
                if kind == 0:
                    lands.rock(bm_h, p, (0.06, 0.05, 0.02), rnd.random() * 50, 0.5, 1)
                elif kind == 1:
                    vs = util.cylinder(bm_r, 0.03, 0.03, 0.012, loc=(0, 0, 0), segs=10)
                    xf(bm_r, vs, p, pitch=R(rnd.uniform(-15, 15)))
                else:
                    xf(bm_mush, util.sphere(bm_mush, 0.035, segs=8, rings=5, scale=(1, 1, 0.4)), p + V((0, 0, 0.01)),
                       yaw=rnd.uniform(0, 6.3))  # random turn: identical caps side by side shared facets
    for k in range(5):
        x = -0.7 + k * 0.35
        top = V((x, 0.0, 1.88))
        util.tube(bm_st, [top, top + V((0, 0, -0.12))], 0.006, n=4)
        for i in range(7):
            a = 2 * math.pi * i / 7
            util.tube(bm_st, [top + V((0, 0, -0.12)), top + V((math.cos(a) * 0.05, math.sin(a) * 0.05, -0.35))],
                      0.005, n=4)
            lands.rock(bm_h, top + V((math.cos(a) * 0.06, math.sin(a) * 0.06, -0.42)), (0.035, 0.035, 0.08),
                       k * 10 + i, 0.4, 1)
    objs = [obj("RackBamboo", bm_b, m["bamboo"], uv=2.0, smooth=True), obj("Trays", bm_t, m["woven"], uv=3.0),
            obj("DriedLeaves", bm_h, m["foliage"], uv=6.0, smooth=True),
            obj("RootSlices", bm_r, util.material("qp_root_slices", tex.wood("#c49a5a", 128, 808, 10)), uv=12.0),
            obj("Mushrooms", bm_mush, util.material("qp_lingzhi", tex.lacquer("#7a2e18", 128, 809, 0.4)), uv=8.0,
                smooth=True), obj("HerbStems", bm_st, m["rope"], uv=6.0)]
    objs.append(util.collider("HerbRackCol", (1.8, 0.75, 1.95), (0, 0, 0.975)))
    return objs


def chain_anchor():
    """Demon-sealing anchor: a rune-carved stone block with a great iron ring, one chain
    snaking across the ground and one straining up into the sky (~1.7 x 4 x 4.4 m)."""
    m = Mats()
    bm_s, bm_i, bm_ch, bm_t = (bmesh.new() for _ in range(4))
    vs = ubox(bm_s, (1.6, 1.6, 1.0), loc=(0, 0, 0.42), bevel=0.06, rect=(0, 0, 4, 1))
    for v in vs:
        if v.co.z > 0.8:
            v.co.x *= 0.9
            v.co.y *= 0.9
    # staple + ring
    util.tube(bm_i, util.catmull([V((-0.2, 0, 0.88)), V((-0.2, 0, 1.12)), V((0, 0, 1.22)), V((0.2, 0, 1.12)),
                                  V((0.2, 0, 0.88))], 4), 0.06, n=10)
    for sx in (-1, 1):
        util.cylinder(bm_i, 0.12, 0.12, 0.04, loc=(sx * 0.2, 0, 0.925), segs=12)  # proud of the block top
    hoop(bm_i, (0, 0.0, 0.92), 0.34, 0.055, normal=(0, 1, 0.25), segs=32, n=10)
    # chains
    ground = [V((0.1, 0.3, 0.62)), V((0.2, 0.7, 0.2)), V((0.3, 1.2, 0.06)), V((0.1, 1.8, 0.06)),
              V((0.25, 2.4, 0.06)), V((0.15, 3.0, 0.06))]  # gentle bends: links on sharp kinks overlapped
    chain(bm_ch, ground, link=0.28, r=0.035)
    sky = [V((0.0, -0.3, 1.2)), V((0.05, -0.8, 2.2)), V((0.1, -1.3, 3.2)), V((0.15, -1.8, 4.2))]
    chain(bm_ch, sky, link=0.28, r=0.035)
    # on the block faces (at +-0.8 m; they used to sit 7 cm inside the block, invisible)
    for k, (x, y, yaw) in enumerate(((0, -0.805, 0), (0.805, 0.1, R(90)), (-0.805, -0.2, R(-90)))):
        card(bm_t, 0.16, 0.5, loc=(x, y, 0.45), yaw=yaw, roll=R(4 - k * 4))
    runes = realms.rune_stone(512, 810, "#4a4744", "#ff5a2a", cols=4, rows=5)
    rmat = util.material("qp_anchor_runes", runes, emission_map=runes["emit"], emission_strength=1.8,
                         normal_strength=1.0)
    objs = [obj("AnchorBlock", bm_s, rmat), obj("AnchorIron", bm_i, m["iron"], uv=2.0, smooth=True),
            obj("AnchorChains", bm_ch, m["iron"], uv=3.0, smooth=True), obj("AnchorTalismans", bm_t, m["talisman"])]
    objs.append(util.collider("AnchorCol", (1.6, 1.6, 1.25), (0, 0, 0.55)))
    return objs


def soul_lantern():
    """Crooked pole bearing an iron-caged soul lantern burning with pale ghost fire, hung
    with talismans and a spirit bell (~0.8 x 1.0 x 2.8 m)."""
    m = Mats()
    bm_p, bm_i, bm_g, bm_f, bm_t, bm_r = (bmesh.new() for _ in range(6))
    pole = util.catmull([V((0, 0.1, 0)), V((0.04, 0.08, 0.8)), V((-0.03, 0.12, 1.6)), V((0.02, 0.1, 2.4)),
                         V((0, 0.02, 2.7))], 5)
    util.tube(bm_p, pole, lambda t: 0.07 * (1 - 0.45 * t), n=10)
    arm = util.catmull([V((0, 0.04, 2.6)), V((0, -0.2, 2.72)), V((0, -0.45, 2.68)), V((0, -0.58, 2.55))], 5)
    util.tube(bm_p, arm, lambda t: 0.035 * (1 - 0.4 * t), n=8)
    for k in range(5):
        lands.rock(bm_r, (math.cos(k * 1.3) * 0.22, 0.1 + math.sin(k * 1.3) * 0.22, 0.05), (0.14, 0.12, 0.1),
                   k + 60, 0.35, 1)
    # lantern: hook, cap, hexagonal cage, glass, base
    top = V((0, -0.58, 2.5))
    util.tube(bm_i, [V((0, -0.58, 2.56)), top], 0.008, n=5)
    hoop(bm_i, top + V((0, 0, 0.0)), 0.03, 0.007, normal=(1, 0, 0), segs=12, n=4)
    lz = top.z - 0.06
    realms.prism(bm_i, [(0.05, lz), (0.2, lz - 0.1), (0.2, lz - 0.12)], sides=6, loc=(top.x, top.y, 0))
    realms.prism(bm_i, [(0.2, lz - 0.5), (0.2, lz - 0.52), (0.12, lz - 0.58), (0.001, lz - 0.6)], sides=6,
                 loc=(top.x, top.y, 0))
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        util.box(bm_i, (0.018, 0.018, 0.4), loc=(top.x + math.cos(a) * 0.185, top.y + math.sin(a) * 0.185, lz - 0.31))
    util.cylinder(bm_g, 0.17, 0.17, 0.37, loc=(top.x, top.y, lz - 0.31), segs=6)
    flame(bm_f, (top.x, top.y, lz - 0.5), h=0.28, r=0.07)
    # talismans hanging below the lantern and from the arm, a small bell
    for k, (dx, dz) in enumerate(((-0.08, 0.0), (0.08, -0.03))):
        card(bm_t, 0.06, 0.24, loc=(top.x + dx, top.y, lz - 0.74 + dz), roll=R(6 - 12 * k))
    card(bm_t, 0.06, 0.24, loc=(0, -0.28, 2.55), yaw=R(90))
    util.lathe(bm_i, [(0.001, 2.5), (0.02, 2.49), (0.035, 2.44), (0.04, 2.41), (0.001, 2.41)], segs=10,
               loc=(0, -0.28, 0))
    ghost = util.material("qp_soul_glass", color="#9cf5d8", rough=0.2, emission="#6fffd0", emission_strength=2.5,
                          alpha=0.6)
    objs = [obj("LanternPole", bm_p, m["bark"], uv=1.5, smooth=True), obj("PoleStones", bm_r, m["weathered"], uv=2.0,
                                                                         smooth=True),
            obj("LanternIron", bm_i, m["iron"], uv=4.0), obj("SoulGlass", bm_g, ghost),
            obj("SoulFire", bm_f, m["soul"], smooth=True), obj("LanternTalismans", bm_t, m["talisman"])]
    objs.append(util.collider("SoulPoleCol", (0.45, 0.45, 2.7), (0, 0.1, 1.35)))
    return objs


def abacus_desk():
    """Counting-house desk: drawers, a big abacus, ledgers, brush and ink stone, strings of
    coins, silver ingots and the merchant's armchair behind (~1.5 x 1.3 x 1.1 m)."""
    m = Mats()
    bm_d, bm_a, bm_bd, bm_bk, bm_pg, bm_c, bm_s, bm_ink, bm_ch = (bmesh.new() for _ in range(9))
    W, D, H = 1.45, 0.72, 0.8
    bevel_box(bm_d, (W, D, 0.05), loc=(0, 0, H - 0.025), bevel=0.012)
    for sx in (-1, 1):
        ubox(bm_d, (0.42, D - 0.04, H - 0.05), loc=(sx * (W / 2 - 0.23), 0, (H - 0.05) / 2))
        for k in range(3):
            z = 0.14 + k * 0.23
            bevel_box(bm_d, (0.36, 0.02, 0.19), loc=(sx * (W / 2 - 0.23), -D / 2 + 0.01, z), bevel=0.006)
            util.cylinder(bm_c, 0.012, 0.012, 0.03, loc=(sx * (W / 2 - 0.23), -D / 2 - 0.01, z), segs=8,
                          rot=Matrix.Rotation(R(90), 4, "X"))
    util.box(bm_d, (W - 0.9, 0.02, 0.5), loc=(0, D / 2 - 0.06, H - 0.3))
    # abacus: frame, beam, rods and beads (2 heaven + 5 earth per rod)
    ax, ay, az = -0.1, -0.08, H
    aw, ad, rods = 0.55, 0.24, 13
    # frame: end bars 0.04 tall, long bars and beam a few mm shorter so no faces share a plane
    for sy in (-1, 1):
        util.box(bm_a, (aw, 0.025, 0.033), loc=(ax, ay + sy * ad / 2, az + 0.0185))
    for sx in (-1, 1):
        util.box(bm_a, (0.025, ad + 0.006, 0.04), loc=(ax + sx * aw / 2, ay, az + 0.02))
    util.box(bm_a, (aw, 0.015, 0.026), loc=(ax, ay + ad / 2 - 0.07, az + 0.02))
    rnd = random.Random(51)
    for i in range(rods):
        x = ax - aw / 2 + 0.03 + i * (aw - 0.06) / (rods - 1)
        util.cylinder(bm_a, 0.003, 0.003, ad, loc=(x, ay, az + 0.02), segs=4, rot=Matrix.Rotation(R(90), 4, "X"))
        up = rnd.randint(0, 2)
        for b in range(2):
            y = ay + ad / 2 - 0.02 - b * 0.022 - (0.012 if b >= 2 - up else 0)  # counted beads slide to the beam
            util.sphere(bm_bd, 0.013, loc=(x, y - 0.0, az + 0.02), segs=8, rings=5, scale=(1.1, 0.7, 1.1))
        dn = rnd.randint(0, 5)
        for b in range(5):
            y = ay - ad / 2 + 0.02 + b * 0.022 + (0.03 if b >= 5 - dn else 0)
            util.sphere(bm_bd, 0.013, loc=(x, y, az + 0.02), segs=8, rings=5, scale=(1.1, 0.7, 1.1))
    # ledgers: a stack and an open one
    zz = H
    for k in range(4):
        th = 0.025
        ubox(bm_bk, (0.2, 0.28, th), loc=(0.48, 0.1, zz + th / 2), yaw=R(4 * k - 6))
        ubox(bm_pg, (0.19, 0.27, th * 0.7), loc=(0.48, 0.1, zz + th / 2), yaw=R(4 * k - 6))
        zz += th
    for sx in (-1, 1):
        card(bm_pg, 0.17, 0.26, loc=(0.35 + sx * 0.087, -0.18, H + 0.012), pitch=R(-90),
             rect=(0.5 if sx > 0 else 0.0, 0, 1.0 if sx > 0 else 0.5, 1))
    # ink stone, brush, coins, ingots
    bevel_box(bm_ink, (0.12, 0.18, 0.03), loc=(-0.52, 0.05, H + 0.015), bevel=0.008)
    util.tube(bm_ink, [V((-0.45, -0.18, H + 0.012)), V((-0.3, -0.24, H + 0.012))], 0.006, n=6)
    for k in range(3):
        for i in range(8):
            util.cylinder(bm_c, 0.016, 0.016, 0.004, loc=(0.1 + k * 0.05, 0.2, H + 0.002 + i * 0.0045), segs=10)
    coin_str = [V((-0.4 + 0.3 * t, 0.26 + 0.03 * math.sin(t * 6), H + 0.012)) for t in np.linspace(0, 1, 16)]
    util.tube(bm_c, coin_str, 0.011, n=6, closed_ends=True)
    for k, (x, y) in enumerate(((0.62, -0.25), (0.54, -0.28), (0.58, -0.18))):
        vs = util.sphere(bm_s, 0.04, loc=(0, 0, 0), segs=12, rings=8, scale=(1.4, 0.8, 0.6))
        for v in vs:
            if abs(v.co.x) > 0.03:
                v.co.z += 0.02 * (abs(v.co.x) - 0.03) / 0.03
        xf(bm_s, vs, (x, y, H + 0.025), yaw=R(20 * k))
    chair(bm_ch, (0.0, 0.62, 0), yaw=R(180))
    objs = [obj("Desk", bm_d, m["rosewood"], uv=1.3), obj("AbacusFrame", bm_a, m["lacquer_black"], uv=4.0),
            obj("AbacusBeads", bm_bd, m["wood_light"], uv=8.0, smooth=True), obj("Ledgers", bm_bk, m["silk_blue"],
                                                                                  uv=3.0),
            obj("LedgerPages", bm_pg, m["ink_paper"]), obj("Coins", bm_c, m["brass"], uv=6.0, smooth=True),
            obj("SilverIngots", bm_s, util.material("qp_silver", tex.metal("#d8dade", 128, 811, rough=0.25)),
                uv=6.0, smooth=True), obj("InkStone", bm_ink, m["dark_stone"], uv=4.0),
            obj("Armchair", bm_ch, m["rosewood"], uv=1.5)]
    objs.append(util.collider("DeskCol", (W, D, H), (0, 0, H / 2)))
    objs.append(util.collider("ChairCol", (0.6, 0.5, 1.1), (0, 0.62, 0.55)))
    return objs


def fishing_boat():
    """River sampan: planked hull with raised bow and stern, an arched woven bamboo canopy,
    sculling oar, nets, a fish basket and a bow lantern (~1.5 x 5.2 x 2.3 m). Origin at the
    keel; sink it ~0.25 m into water or leave it beached."""
    m = Mats()
    bm_h, bm_d, bm_c, bm_w, bm_n, bm_bk, bm_lp, bm_lf = (bmesh.new() for _ in range(8))
    L = 5.0
    rings = []
    for t in np.linspace(0, 1, 15):
        y = -L / 2 + L * t
        s = math.sin(math.pi * min(1.0, 0.1 + t * 0.95)) if t < 0.8 else math.sin(math.pi * (0.1 + 0.8 * 0.95)) * 0.95
        hw = 0.72 * max(s, 0.06) ** 0.6
        sheer = 0.62 + 0.45 * (1 - t) ** 4 * 1.0 + 0.25 * t ** 6
        keel = 0.0 + 0.35 * (1 - t) ** 5 + 0.15 * t ** 8
        pts = [V((-hw, y, sheer)), V((-hw * 0.95, y, keel + (sheer - keel) * 0.5)), V((-hw * 0.7, y, keel + 0.08)),
               V((-hw * 0.3, y, keel)), V((hw * 0.3, y, keel)), V((hw * 0.7, y, keel + 0.08)),
               V((hw * 0.95, y, keel + (sheer - keel) * 0.5)), V((hw, y, sheer))]
        rings.append(pts)
    util.loft(bm_h, rings, closed=False, uv_scale=(1.0, 0.5))
    # transom caps (bow and stern)
    for ring in (rings[0], rings[-1]):
        util.tube(bm_d, ring, 0.02, n=4)
    hull_o = util.mesh_object("Hull", bm_h, m["planks"], smooth=False)
    util.box_uv(hull_o, 0.9)
    util.solidify(hull_o, 0.05, offset=1.0)
    # gunwale rails and ribs, floor boards
    for sx in (-1, 1):
        rail = [V((p[-1 if sx > 0 else 0].x, p[0].y, p[0].z + 0.02)) for p in rings]  # port and starboard
        util.tube(bm_d, rail, 0.035, n=6)
    for t in np.linspace(0.12, 0.88, 7):
        i = int(round(t * 14))
        util.tube(bm_d, [p + V((0, 0, 0.02)) for p in rings[i]], 0.022, n=4)
    ubox(bm_d, (0.8, 3.6, 0.03), loc=(0, 0.05, 0.14))
    for y in (-1.35, 1.5):
        ubox(bm_d, (1.2, 0.2, 0.04), loc=(0, y, 0.5))
    # arched woven canopy
    rings_c = []
    for y in np.linspace(-0.7, 0.9, 6):
        rings_c.append([V((math.cos(a) * 0.68, y, 0.6 + math.sin(a) * 0.72)) for a in np.linspace(0, math.pi, 12)])
    util.loft(bm_c, rings_c, closed=False, uv_scale=(2.0, 1.0))
    for y in np.linspace(-0.7, 0.9, 4):
        util.tube(bm_d, [V((math.cos(a) * 0.7, y, 0.6 + math.sin(a) * 0.74)) for a in np.linspace(0, math.pi, 12)],
                  0.018, n=4, closed_ends=True)
    # sculling oar at the stern, a pole, net heap, basket, bow lantern
    util.tube(bm_w, [V((0.3, 2.3, 0.9)), V((0.4, 3.3, 0.25))], 0.03, n=6)
    ubox(bm_w, (0.16, 0.5, 0.02), loc=(0.42, 3.45, 0.15), pitch=R(-35))
    util.tube(bm_w, [V((-0.55, -1.6, 0.55)), V((-0.5, 1.9, 0.75))], 0.025, n=6)
    lands.rock(bm_n, (0.15, -1.25, 0.3), (0.3, 0.35, 0.16), 71, 0.35, 2)
    util.lathe(bm_bk, [(0.001, 0.15), (0.12, 0.15), (0.18, 0.25), (0.16, 0.42), (0.12, 0.45)], segs=16,
               loc=(-0.3, 1.2, 0))
    util.tube(bm_w, [V((0, -2.3, 0.9)), V((0, -2.35, 1.6)), V((0, -2.55, 1.7))], 0.02, n=6)
    realms.lantern(bm_lp, bm_w, (0, -2.55, 1.68), 0.4)
    util.sphere(bm_lf, 0.05, loc=(0, -2.55, 1.52), segs=8, rings=5)
    lantern = util.material("qp_boat_lantern", tex.paper_lantern("#c7261c", 128), emission="#ff4a1c",
                            emission_strength=1.5, normal_strength=0.3)
    nets = util.material("qp_net_heap", lands.woven("#6f6a55", 128, 812),
                         normal_strength=1.0)
    objs = [hull_o, obj("BoatTrim", bm_d, m["wood"], uv=1.5), obj("Canopy", bm_c, m["woven_ds"]),
            obj("OarAndPole", bm_w, m["bamboo"], uv=2.0, smooth=True), obj("NetHeap", bm_n, nets, uv=3.0, smooth=True),
            obj("FishBasket", bm_bk, m["woven"], uv=3.0, smooth=True), obj("BowLantern", bm_lp, lantern, smooth=True),
            obj("BowLanternGlow", bm_lf, m["flame"], smooth=True)]
    bm = bmesh.new()
    for ring in rings:
        for p in ring:
            bm.verts.new(p)
    objs.append(hull("HullCol", bm))
    return objs


def wishing_tree():
    """Ancient wishing tree hung with red ribbons, wooden wish plaques and bells, inside a low
    stone ring (~6 x 6 x 6 m)."""
    m = Mats()
    rnd = random.Random(61)
    bm_t, bm_f, bm_rib, bm_tag, bm_str, bm_bell, bm_ring, bm_soil = (bmesh.new() for _ in range(8))
    trunk = util.catmull([V((0, 0, -0.1)), V((0.1, 0.05, 1.0)), V((-0.1, 0.1, 2.0)), V((0.05, 0, 2.9))], 6)
    util.tube(bm_t, trunk, lambda t: 0.5 * (1 - 0.45 * t), n=16, uv_scale=(2, 0.5))
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), 0))
        util.tube(bm_t, [d * 0.15 + V((0, 0, 0.35)), d * 0.62 + V((0, 0, 0.06)), d * 0.9 + V((0, 0, -0.1))],
                  lambda t: 0.22 * (1 - 0.8 * t), n=7)
    tips = []
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.3, 0.3)
        d = V((math.cos(a), math.sin(a), 0))
        start = V((0, 0, 2.3 + 0.1 * k))
        mid = start + d * 1.2 + V((0, 0, 0.7 + rnd.uniform(-0.2, 0.3)))
        end = start + d * rnd.uniform(2.1, 2.6) + V((0, 0, rnd.uniform(0.8, 1.5)))
        util.tube(bm_t, util.catmull([start, mid, end], 4), lambda t: 0.2 * (1 - 0.8 * t), n=10)
        tips.append((start, mid, end))
        side = d.cross(V((0, 0, 1)))
        for sgn in (-1, 1):
            b2 = mid.lerp(end, 0.4) + side * sgn * 0.8 + V((0, 0, 0.5))
            util.tube(bm_t, [mid.lerp(end, 0.3), b2], lambda t: 0.08 * (1 - 0.7 * t), n=6)
            tips.append((mid, mid.lerp(end, 0.3), b2))
    # canopy clumps at the branch ends
    for (_, mid, end) in tips:
        lands.rock(bm_f, end + V((0, 0, 0.3)), (0.9, 0.9, 0.55), rnd.random() * 100, 0.35, 2)
    # ribbons, plaques and bells hanging from the branches
    hung = []
    for (s, mid, end) in tips:
        for i in range(5):
            p = mid.lerp(end, rnd.uniform(0.1, 0.8)) + V((0, 0, -0.05))
            if rnd.random() < 0.6:
                ln = rnd.uniform(0.5, 1.1)
                card(bm_rib, 0.05, ln, loc=p + V((0, 0, -ln / 2)), yaw=rnd.uniform(0, math.pi), rows=4,
                     bend=lambda x, z: 0.05 * math.sin(z * 4))
            else:
                ln = rnd.uniform(0.2, 0.4)
                if any((p - q).length < 0.04 for q in hung):
                    continue  # two strings on the same spot overlapped
                hung.append(p)
                util.tube(bm_str, [p, p + V((0, 0, -ln - 0.01))], 0.004, n=3)  # ends inside the plaque
                if rnd.random() < 0.75:
                    ubox(bm_tag, (0.08, 0.012, 0.12), loc=p + V((0, 0, -ln - 0.06)), yaw=rnd.uniform(0, math.pi),
                         rect=(rnd.randrange(4) / 4, 0, rnd.randrange(4) / 4 + 0.25, 0.5))
                    card(bm_rib, 0.03, 0.22, loc=p + V((0, 0, -ln - 0.22)), yaw=rnd.uniform(0, math.pi))
                else:
                    util.lathe(bm_bell, [(0.001, 0.0), (0.03, -0.01), (0.04, -0.06), (0.045, -0.08), (0.001, -0.08)],
                               segs=10, loc=p + V((0, 0, -ln)))
    realms.prism(bm_ring, [(1.35, 0.0), (1.35, 0.42), (1.2, 0.42), (1.2, 0.2)], sides=10, v_scale=0.6, cap_top=False)
    realms.disc(bm_soil, (0, 0), 1.22, segs=10, z=0.2)
    tag = util.material("qp_wish_plaque", ink_paper("#b08a5a", 256, 813, 4, 2, box=(0.05, 0.05, 0.95, 0.5),
                                                          seal=False),
                        normal_strength=0.4)
    leaf = util.material("qp_tree_leaves", tex.foliage("#4a7a34", 256, 814), normal_strength=0.7)
    objs = [obj("WishTree", bm_t, m["bark"], smooth=True), obj("WishTreeLeaves", bm_f, leaf, uv=1.0, smooth=True),
            obj("Ribbons", bm_rib, m["silk_red_ds"]), obj("WishPlaques", bm_tag, tag),
            obj("RibbonStrings", bm_str, m["silk_red"]), obj("WishBells", bm_bell, m["brass"], uv=6.0, smooth=True),
            obj("TreeRing", bm_ring, m["stone"], uv=1.0), obj("TreeSoil", bm_soil, m["earth"], uv=1.0)]
    bm = bmesh.new()
    realms.prism(bm, [(1.35, 0.0), (1.35, 0.42)], sides=10)
    objs.append(hull("TreeRingCol", bm))
    objs.append(util.collider("TrunkCol", (1.0, 1.0, 3.0), (0, 0.05, 1.5)))
    return objs


def jade_screen():
    """Standing screen: a carved jade landscape panel glowing faintly, framed in rosewood on
    carved feet, with a gilt cloud crest (~2.1 x 0.6 x 2.3 m)."""
    m = Mats()
    bm_w, bm_j, bm_g, bm_ap = (bmesh.new() for _ in range(4))
    for sx in (-1, 1):
        vs = ubox(bm_w, (0.16, 0.6, 0.16), loc=(sx * 0.92, 0, 0.08), bevel=0.03)
        for v in vs:
            if abs(v.co.y) > 0.25 and v.co.z > 0.1:
                v.co.z -= 0.05
        bevel_box(bm_w, (0.1, 0.1, 2.05), loc=(sx * 0.92, 0, 1.1), bevel=0.015)
        util.sphere(bm_g, 0.06, loc=(sx * 0.92, 0, 2.16), segs=10, rings=6)
        for sy in (-1, 1):
            util.tube(bm_w, [V((sx * 0.92, sy * 0.26, 0.16)), V((sx * 0.92, sy * 0.05, 0.55))], 0.03, n=6)
    for z in (0.5, 0.62, 1.98):  # rails 7 mm slimmer than the posts
        bevel_box(bm_w, (1.84, 0.086, 0.08), loc=(0, 0, z), bevel=0.012)
    # openwork apron between the lower rails
    for k in range(9):
        x = -0.8 + k * 0.2
        util.box(bm_ap, (0.03, 0.04, 0.12), loc=(x, 0, 0.3 + 0.2 * 0))
        hoop(bm_ap, (x + 0.1, 0, 0.35), 0.06, 0.012, normal=(0, 1, 0), segs=12, n=4)
    util.box(bm_ap, (1.74, 0.05, 0.04), loc=(0, 0, 0.24))
    # jade panel with the relief texture on both faces
    ubox(bm_j, (1.72, 0.05, 1.3), loc=(0, 0, 1.3), rect=(0, 0, 1, 1))
    # crest
    for sx in (-1, 1):
        pts = [V((sx * (0.08 + 0.25 * (1 - t) * math.cos(t * 7) + 0.45 * t), 0, 2.08 + 0.14 * (1 - t) * math.sin(t * 7)))
               for t in np.linspace(0, 1, 22)]
        util.tube(bm_g, pts, lambda t: 0.035 * (1 - 0.5 * t), n=7)
    util.sphere(bm_g, 0.08, loc=(0, 0, 2.22), segs=12, rings=8)
    jr = jade_relief(512)
    jade = util.material("qp_jade_relief", jr, emission_map=jr["emit"], emission_strength=1.5, normal_strength=1.2)
    objs = [obj("ScreenFrame", bm_w, m["rosewood"], uv=1.5), obj("JadePanel", bm_j, jade),
            obj("ScreenGilt", bm_g, m["gold"], uv=3.0, smooth=True), obj("ScreenApron", bm_ap, m["rosewood"], uv=3.0)]
    objs.append(util.collider("ScreenCol", (2.0, 0.6, 2.25), (0, 0, 1.12)))
    return objs


def stone_tablet_array():
    """Seven-star tablet formation: seven inscribed steles in an arc on a round rune platform
    around a glowing array-eye pedestal (~6.6 x 6.6 x 2.3 m)."""
    m = Mats()
    bm_p, bm_d, bm_t, bm_b, bm_c, bm_o = (bmesh.new() for _ in range(6))
    realms.prism(bm_p, [(3.3, 0.0), (3.3, 0.22), (3.2, 0.28), (3.05, 0.28)], sides=32, v_scale=0.8, cap_top=False)
    realms.disc(bm_d, (0, 0), 3.05, segs=32, z=0.28)
    ins = lands.inscription(512, 815, "#6f716b")
    ins["emit"] = ins["cut"]
    tab_m = util.material("qp_array_tablet", ins, emission_map=emissive(ins, "cut", "#56e8ff") * 0.5,
                          emission_strength=1.5, normal_strength=1.2)
    cols = []
    for k in range(7):
        a = R(-90 + 40 + k * (280 / 6))  # leave the front (-Y) open
        p = V((math.cos(a) * 2.45, math.sin(a) * 2.45, 0.28))
        yaw = a + R(90)
        vs = new_verts(bm_b, lambda: bevel_box(bm_b, (0.9, 0.36, 0.2), loc=(0, 0, 0.1), bevel=0.03))
        xf(bm_b, vs, p, yaw=yaw)
        w, sh = 0.72, 1.35
        vs = new_verts(bm_t, lambda: lands.extrude_outline(bm_t, lands.arc_outline(w, sh, 10, 0.2), -0.09, 0.09,
                                                           uv_front=(-w / 2, 0.2, w, sh + w / 2 * 0.55)))
        xf(bm_t, vs, p, yaw=yaw + math.pi)
        cols.append(util.collider("TabletCol%d" % k, (0.95, 0.4, 1.95), (0, 0, 0)))
        cols[-1].rotation_euler = (0, 0, yaw)
        cols[-1].location = p + V((0, 0, 0.97))
        util.apply_transform(cols[-1])
    # array eye: pedestal and orb
    realms.prism(bm_c, [(0.4, 0.28), (0.4, 0.4), (0.24, 0.5), (0.2, 0.9), (0.32, 1.0), (0.32, 1.06)], sides=8,
                 rot=R(22.5), v_scale=0.8)
    util.sphere(bm_o, 0.22, loc=(0, 0, 1.32), segs=16, rings=10)
    disc = tex.rune_circle(1024, 816, "#6ff2ff", "#8f8b85")
    disc_m = util.material("qp_array_disc", disc, emission_map=emissive(disc, "emit_mask", "#6ff2ff"),
                           emission_strength=2.0, normal_strength=0.8)
    objs = [obj("ArrayPlatform", bm_p, m["stone"], uv=0.6), obj("ArrayDisc", bm_d, disc_m),
            obj("TabletBases", bm_b, m["dark_stone"], uv=1.2), obj("ArrayTablets", bm_t, tab_m),
            obj("ArrayEye", bm_c, m["stone"], uv=1.2), obj("ArrayOrb", bm_o, m["spirit"], smooth=True)]
    bm = bmesh.new()
    realms.prism(bm, [(3.3, 0.0), (3.3, 0.28)], sides=16)
    objs.append(hull("ArrayPlatformCol", bm))
    objs.append(util.collider("ArrayEyeCol", (0.8, 0.8, 1.5), (0, 0, 0.75)))
    return objs + cols


# --------------------------------------------------------------------------
# dressing props (market, household, shrine and dock set dressing)
# --------------------------------------------------------------------------
def blue_white(size=256, seed=831):
    """Blue-and-white porcelain (lathe uv: u around, v up): bands, lotus scroll, lappets."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 8, 3, 0.5, seed)
    col = np.ones((size, size, 3), np.float32) * tex.srgb("#eef1f2") * (0.95 + 0.05 * n)[..., None]
    blue = np.zeros_like(u)
    for (a, b) in ((0.08, 0.1), (0.14, 0.15), (0.78, 0.8), (0.9, 0.93)):
        blue = np.maximum(blue, ((v > a) & (v < b)).astype(np.float32))
    scroll = np.zeros_like(u)
    for k in range(6):
        cx = (k + 0.5) / 6
        tex.stamp_curve(scroll, tex.cloud_curl(cx, 0.45, 0.06, turns=1.3, flip=1 if k % 2 else -1), 0.008, size)
        tex.stamp_curve(scroll, [((cx + t / 6) % 1.0, 0.45 + 0.12 * math.sin(t * math.pi * 2)) for t in
                                 np.linspace(0, 1, 30)], 0.005, size)
    lap = ((v > 0.8) & (v < 0.9) & (np.abs(((u * 12) % 1.0) - 0.5) < (0.9 - v) * 4)).astype(np.float32)
    blue = np.clip(blue + scroll + lap, 0, 1)
    col = tex.lerp(col, tex.srgb("#1f3f8a") * (0.8 + 0.3 * n)[..., None], blue * 0.9)
    return tex.result(col, 0.15, 0.0, n * 0.05)


def _alpha_mat(name, maps):
    return lands.clip_alpha(util.material(name, maps, alpha=maps["alpha"], double_sided=True))


LIB.update({
    "incense": lambda: util.material("qp_incense", color="#6b4a30", rough=0.8),
    "blue_white": lambda: util.material("qp_blue_white", blue_white(256)),
    "yixing": lambda: util.material("qp_yixing_clay", tex.stone("#7a3a22", 256, 832, 0.1), normal_strength=0.3),
    "grain": lambda: util.material("qp_grain", tex.stone("#d9b862", 256, 833, 0.8), normal_strength=1.2),
    "fish": lambda: util.material("qp_fish", tex.metal("#aab4b8", 128, 834, rough=0.3), normal_strength=0.3),
    "paper_lantern": lambda: util.material("qp_paper_lantern", tex.paper_lantern("#c7261c", 128),
                                           emission="#ff4a1c", emission_strength=2.0, normal_strength=0.3),
    "cushion": lambda: util.material("qp_cushion", tex.silk("#7a1f2a", "#b8892f", 256, 835), normal_strength=0.3),
    "end_grain": lambda: util.material("qp_end_grain", lands.end_grain(256, 836), normal_strength=0.5),
    "net": lambda: _alpha_mat("qp_net", net(256)),
})


def sack(bm, loc, s=1.0, yaw=0.0, pitch=0.0, squash=1.0):
    """Tied grain sack ~0.7 m tall at s = 1."""
    vs = new_verts(bm, lambda: lathe_n(bm, [(0.001, 0.0), (0.22, 0.01), (0.28, 0.12), (0.27, 0.34), (0.2, 0.5),
                                             (0.08, 0.58), (0.06, 0.6), (0.1, 0.66), (0.07, 0.7), (0.001, 0.7)],
                                        segs=16, u_rep=2.0))
    xf(bm, vs, loc, yaw=yaw, pitch=pitch, scale=(s * 1.05, s * 0.85, s * squash))


def basket(bm, loc, r=0.3, h=0.3, handle=False):
    x, y, z = loc
    lathe_n(bm, [(0.001, 0.0), (r * 0.8, 0.0), (r * 0.95, h * 0.3), (r * 1.05, h), (r * 1.08, h + 0.02),
                 (r * 0.98, h + 0.02), (r * 0.92, h * 0.4), (0.001, h * 0.25)], segs=24, loc=(x, y, z), u_rep=4.0)
    if handle:
        util.tube(bm, [V((x + r * math.cos(a), y, z + h + math.sin(a) * r * 0.9)) for a in np.linspace(0, math.pi, 12)],
                  0.012, n=5)


def barrel(bm_w, bm_h, loc, h=0.9, r=0.32, yaw=0.0, pitch=0.0):
    before_w, before_h = set(bm_w.verts), set(bm_h.verts)
    lands._barrel(bm_w, bm_h, (0, 0, -h / 2 if pitch else 0.0), h=h, r=r)
    vw = [v for v in bm_w.verts if v not in before_w]
    vh = [v for v in bm_h.verts if v not in before_h]
    xf(bm_w, vw, loc, yaw=yaw, pitch=pitch)
    xf(bm_h, vh, loc, yaw=yaw, pitch=pitch)


def goods_baskets():
    """Market produce: woven baskets of oranges, cabbages, grain and eggs, one raised on a
    crate (~1.5 x 1.1 x 0.8 m)."""
    m = Mats()
    rnd = random.Random(71)
    bm_b, bm_o, bm_c, bm_g, bm_e, bm_cr = (bmesh.new() for _ in range(6))
    ubox(bm_cr, (0.55, 0.45, 0.35), loc=(0.45, 0.25, 0.175), bevel=0.015, rect=(0, 0, 1, 1))
    specs = [(-0.45, -0.15, 0.0, 0.3, "orange"), (0.1, -0.3, 0.0, 0.26, "cabbage"), (0.45, 0.25, 0.352, 0.24, "egg"),
             (-0.35, 0.35, 0.0, 0.28, "grain"), (0.55, -0.3, 0.0, 0.2, "orange")]
    for (x, y, z, r, kind) in specs:
        h = r * 0.9
        basket(bm_b, (x, y, z), r, h, handle=kind == "egg")
        top = z + h
        if kind == "grain":
            util.lathe(bm_g, [(r * 0.98, top - 0.02), (r * 0.8, top + 0.04), (r * 0.4, top + 0.09), (0.001, top + 0.1)],
                       segs=20, loc=(x, y, 0))
            continue
        cnt = {"orange": 11, "cabbage": 4, "egg": 12}[kind]
        rad = {"orange": 0.045, "cabbage": 0.1, "egg": 0.03}[kind]
        placed = []
        for _ in range(cnt * 20):  # non-overlapping heap (interpenetrating copies z-fight)
            if len(placed) == cnt:
                break
            a, rr = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()) * r * 0.65
            p = V((x + math.cos(a) * rr, y + math.sin(a) * rr, top - 0.01 + rnd.uniform(0, 0.04)))
            if any((p - q).length < 2 * rad + 0.003 for q in placed):
                continue
            placed.append(p)
            if kind == "orange":
                xf(bm_o, util.sphere(bm_o, 0.045, segs=10, rings=7), p, yaw=rnd.uniform(0, 6.3))
            elif kind == "cabbage":
                lands.rock(bm_c, p + V((0, 0, 0.04)), (0.1, 0.1, 0.09), rnd.random() * 90, 0.12, 2)
            else:
                xf(bm_e, util.sphere(bm_e, 0.028, segs=8, rings=6, scale=(1, 1, 1.3)), p, yaw=rnd.uniform(0, 6.3))
    objs = [obj("Baskets", bm_b, m["woven"], smooth=True), obj("Oranges", bm_o, m["orange"], smooth=True),
            obj("Cabbages", bm_c, m["cabbage"], smooth=True), obj("Grain", bm_g, m["grain"], uv=3.0, smooth=True),
            obj("Eggs", bm_e, m["bun"], smooth=True), obj("Crate", bm_cr, m["planks"])]
    objs.append(util.collider("BasketsCol", (1.55, 1.15, 0.6), (0.05, 0.02, 0.3)))
    return objs


def cloth_bolts():
    """Silk merchant's display: bolts of coloured silk stacked on a trestle table, more
    standing in a tall basket, one length unrolled over the edge (~2.0 x 0.8 x 1.2 m)."""
    m = Mats()
    silks = ["silk_red", "silk_blue", "silk_green", "silk_gold", "silk_white"]
    bms = {k: bmesh.new() for k in silks}
    bm_t, bm_b = bmesh.new(), bmesh.new()
    altar_table(bm_t, 1.5, 0.62, 0.74, everted=False)
    rnd = random.Random(73)
    rot = Matrix.Rotation(R(90), 4, "X")  # bolts lie front-to-back, rolled ends facing the customer
    k = 0
    for layer, n in enumerate((5, 4, 3)):
        for i in range(n):
            r = 0.075
            x = -0.3 + (i - (n - 1) / 2) * (2 * r + 0.01)
            z = 0.742 + r + layer * r * 1.75
            for y in (-0.14, 0.14):  # two 0.26 m bolts per slot, 2 cm apart (0.5 m bolts overlapped by 0.22 m)
                util.cylinder(bms[silks[k % 5]], r, r, 0.26, loc=(x + rnd.uniform(-0.003, 0.003), y, z), segs=14,
                              rot=rot)
                k += 1
    # an unrolled length spilling over the front edge
    bolt = V((0.5, -0.05, 0.74 + 0.07))
    util.cylinder(bms["silk_gold"], 0.07, 0.07, 0.45, loc=bolt, segs=14, rot=Matrix.Rotation(R(90), 4, "X"))
    bm_drape = bmesh.new()  # the unrolled length is a thin card: double-sided material
    card(bm_drape, 0.42, 0.9, loc=(0.5, -0.33, 0.55), cols=3, rows=6,
         bend=lambda x, z: -0.03 * math.sin(z * 6) - 0.02 * (1 - (z + 0.45) / 0.9) ** 2)
    card(bm_drape, 0.42, 0.24, loc=(0.5, -0.2, 0.745), pitch=R(-90))
    basket(bm_b, (0.95, 0.15, 0.0), 0.22, 0.5)
    for i in range(6):
        a = 2 * math.pi * i / 6
        util.cylinder(bms[silks[i % 5]], 0.06, 0.06, 1.0, loc=(0.95 + math.cos(a) * 0.1, 0.15 + math.sin(a) * 0.1,
                                                               0.5 + rnd.uniform(0.0, 0.12)), segs=12,
                      rot=Matrix.Rotation(R(rnd.uniform(-6, 6)), 4, "X"))
    objs = [obj("SilkTable", bm_t, m["wood"], uv=1.3), obj("SilkBasket", bm_b, m["woven"], smooth=True),
            obj("SilkDrape", bm_drape, m["silk_gold_ds"])]
    for k in silks:
        objs.append(obj("Bolts_" + k, bms[k], m[k], uv=3.0, smooth=True))
    objs.append(util.collider("SilkCol", (1.55, 0.7, 1.1), (0, 0, 0.55)))
    objs.append(util.collider("SilkBasketCol", (0.5, 0.5, 1.2), (0.95, 0.15, 0.6)))
    return objs


def grain_sacks():
    """A heap of tied grain sacks with a wooden scoop and spilled grain (~1.8 x 1.3 x 1.1 m)."""
    m = Mats()
    rnd = random.Random(75)
    bm_s, bm_g, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
    for (x, y) in ((-0.5, 0.2), (0.05, 0.25), (0.6, 0.2), (-0.2, -0.3)):
        sack(bm_s, (x, y, 0), 1.0 + rnd.uniform(-0.08, 0.08), yaw=rnd.uniform(-0.5, 0.5), squash=0.9)
    sack(bm_s, (-0.2, 0.25, 0.62), 0.95, yaw=R(20), squash=0.85)
    sack(bm_s, (0.35, 0.25, 0.6), 0.9, yaw=R(-30), squash=0.85)
    sack(bm_s, (0.55, -0.35, 0.22), 0.9, yaw=R(70), pitch=R(-80))
    util.lathe(bm_g, [(0.35, 0.0), (0.25, 0.03), (0.1, 0.06), (0.001, 0.065)], segs=16, loc=(0.2, -0.65, 0))
    util.lathe(bm_w, [(0.001, 0.03), (0.08, 0.03), (0.09, 0.1), (0.085, 0.1), (0.075, 0.035), (0.001, 0.035)],
               segs=14, loc=(0.0, -0.7, 0.0))
    util.tube(bm_w, [V((0.08, -0.7, 0.06)), V((0.25, -0.78, 0.1))], 0.015, n=6)
    stamp = ink_paper("#b8a47e", 256, 837, 1, 2, ink="#8e1a14", box=(0.35, 0.3, 0.65, 0.7), stroke=0.03, seal=False)
    cv = lands.canvas("#a89570", 256, 838)
    cv["albedo"] = tex.lerp(cv["albedo"], tex.srgb("#8e1a14"), stamp["ink"] * 0.8)
    objs = [obj("Sacks", bm_s, util.material("qp_sack", cv, normal_strength=0.6), smooth=True),
            obj("SpilledGrain", bm_g, m["grain"], uv=3.0, smooth=True),
            obj("Scoop", bm_w, m["wood_light"], uv=3.0, smooth=True)]
    objs.append(util.collider("SacksCol", (1.75, 1.2, 1.1), (0.05, 0.0, 0.55)))
    return objs


def barrel_stack():
    """Wine / oil barrels: three standing, three lying in a timber cradle (~2.2 x 1.4 x 1.3 m)."""
    m = Mats()
    bm_w, bm_h, bm_c, bm_l = (bmesh.new() for _ in range(4))
    for x, y, h in ((-0.75, 0.3, 0.95), (-0.07, 0.35, 0.9), (-0.45, -0.3, 0.85)):  # hoops no longer touch
        barrel(bm_w, bm_h, (x, y, 0.0), h=h, r=0.32)
    for y in (-0.35, 0.35):
        bevel_box(bm_c, (0.12, 0.12, 0.12), loc=(0.35, y, 0.06), bevel=0.01)
        bevel_box(bm_c, (0.12, 0.12, 0.12), loc=(1.05, y, 0.06), bevel=0.01)
    for x in (0.35, 1.05):
        bevel_box(bm_c, (0.1, 1.0, 0.08), loc=(x, 0, 0.14), bevel=0.01)
    for k, y in enumerate((-0.33, 0.33)):
        barrel(bm_w, bm_h, (0.7, y, 0.46), h=0.85, r=0.3, pitch=R(90), yaw=R(90))
    barrel(bm_w, bm_h, (0.7, 0.0, 0.98), h=0.85, r=0.3, pitch=R(90), yaw=R(90))
    for x, y, h in ((-0.75, 0.3, 0.95), (-0.07, 0.35, 0.9)):
        card(bm_l, 0.22, 0.22, loc=(x, y - 0.33, h * 0.55), roll=R(45))
    lab = ink_paper("#c42a22", 128, 839, 1, 1, ink="#140c08", box=(0.25, 0.25, 0.75, 0.75), stroke=0.06, seal=False)
    objs = [obj("Barrels", bm_w, m["planks"], uv=1.0, smooth=True), obj("BarrelHoops", bm_h, m["iron"], uv=2.0,
                                                                        smooth=True),
            obj("Cradle", bm_c, m["old_planks"], uv=1.2), obj("BarrelLabels", bm_l, util.material(
                "qp_barrel_label", lab, double_sided=True))]
    objs.append(util.collider("BarrelsCol", (2.2, 1.4, 1.3), (0.15, 0.02, 0.65)))
    return objs


def tea_set():
    """Low tea table on a mat: yixing teapot, cups on a bamboo tray, tea caddy, a kettle
    on a charcoal brazier and two cushions (~1.8 x 1.3 x 0.6 m)."""
    m = Mats()
    bm_t, bm_tr, bm_p, bm_c, bm_k, bm_br, bm_f, bm_cu, bm_mat, bm_cad = (bmesh.new() for _ in range(10))
    card(bm_mat, 1.8, 1.3, loc=(0, 0, 0.004), pitch=R(-90))
    bevel_box(bm_t, (0.9, 0.6, 0.05), loc=(0, 0, 0.33), bevel=0.012)
    for sx in (-1, 1):
        for sy in (-1, 1):
            vs = ubox(bm_t, (0.06, 0.06, 0.31), loc=(sx * 0.38, sy * 0.24, 0.155))
            for v in vs:
                if v.co.z < 0.03:
                    v.co.x += sx * 0.03
    bevel_box(bm_tr, (0.42, 0.3, 0.03), loc=(-0.1, 0, 0.37), bevel=0.008)
    z = 0.385
    util.lathe(bm_p, [(0.001, z), (0.05, z), (0.07, z + 0.03), (0.075, z + 0.06), (0.06, z + 0.09), (0.035, z + 0.1),
                      (0.035, z + 0.11), (0.001, z + 0.115)], segs=20, loc=(-0.15, 0.0, 0))
    util.sphere(bm_p, 0.012, loc=(-0.15, 0, z + 0.125), segs=8, rings=5)
    util.tube(bm_p, util.catmull([V((-0.08, 0, z + 0.04)), V((-0.04, 0, z + 0.07)), V((-0.02, 0, z + 0.1))], 3),
              lambda t: 0.012 * (1 - 0.4 * t), n=6)
    hoop(bm_p, (-0.23, 0, z + 0.06), 0.035, 0.008, normal=(0, 1, 0), segs=14, n=5)
    for i in range(4):
        cup(bm_c, (0.0 + (i % 2) * 0.07, -0.07 + (i // 2) * 0.14, 0.385), 0.025, 0.03)
    util.cylinder(bm_cad, 0.045, 0.045, 0.12, loc=(0.3, 0.15, 0.415), segs=14)
    util.cylinder(bm_cad, 0.048, 0.048, 0.03, loc=(0.3, 0.15, 0.48), segs=14)
    # brazier stove with a kettle
    util.lathe(bm_br, [(0.001, 0.0), (0.14, 0.0), (0.16, 0.1), (0.15, 0.26), (0.17, 0.28), (0.12, 0.28),
                       (0.001, 0.2)], segs=16, loc=(0.75, 0.35, 0))
    for k in range(5):
        util.sphere(bm_f, 0.04, loc=(0.75 + math.cos(k) * 0.06, 0.35 + math.sin(k) * 0.06, 0.24), segs=6, rings=4)
    util.lathe(bm_k, [(0.001, 0.28), (0.09, 0.29), (0.11, 0.34), (0.1, 0.4), (0.05, 0.43), (0.05, 0.45),
                      (0.001, 0.46)], segs=16, loc=(0.75, 0.35, 0))
    util.tube(bm_k, [V((0.75 - 0.09, 0.35, 0.44)), V((0.75, 0.35, 0.52)), V((0.75 + 0.09, 0.35, 0.44))], 0.008, n=5)
    util.tube(bm_k, [V((0.85, 0.35, 0.34)), V((0.92, 0.35, 0.4))], 0.012, n=5)
    for y in (-0.55, 0.55):
        util.sphere(bm_cu, 0.28, loc=(0, y, 0.06), segs=18, rings=8, scale=(1, 1, 0.24))
    objs = [obj("TeaMat", bm_mat, m["woven_ds"]), obj("TeaTable", bm_t, m["rosewood"], uv=1.5),
            obj("TeaTray", bm_tr, m["bamboo"], uv=3.0), obj("Teapot", bm_p, m["yixing"], uv=6.0, smooth=True),
            obj("TeaCups", bm_c, m["celadon"], uv=8.0, smooth=True), obj("TeaCaddy", bm_cad, m["lacquer_red"], uv=6.0),
            obj("Brazier", bm_br, m["iron"], uv=3.0, smooth=True), obj("Coals", bm_f, m["ember"]),
            obj("Kettle", bm_k, m["bronze"], uv=4.0, smooth=True), obj("Cushions", bm_cu, m["cushion"], uv=2.0,
                                                                       smooth=True)]
    objs.append(util.collider("TeaTableCol", (0.9, 0.6, 0.36), (0, 0, 0.18)))
    objs.append(util.collider("BrazierCol", (0.36, 0.36, 0.5), (0.75, 0.35, 0.25)))
    return objs


def calligraphy_table():
    """Scholar's desk: a sheet of fresh calligraphy under paperweights, ink stone, brush rack
    and pot, seal box, and a chair (~1.6 x 1.2 x 1.1 m)."""
    m = Mats()
    bm_t, bm_pp, bm_w, bm_ink, bm_br, bm_tip, bm_pot, bm_ch, bm_seal = (bmesh.new() for _ in range(9))
    W, D, H = 1.6, 0.62, 0.78
    altar_table(bm_t, W, D, H, everted=True)
    card(bm_pp, 0.5, 0.36, loc=(-0.05, -0.05, H + 0.003), pitch=R(-90), yaw=R(90))
    for dx in (-0.25, 0.2):
        bevel_box(bm_w, (0.04, 0.36, 0.025), loc=(dx, -0.05, H + 0.015), bevel=0.006)
    bevel_box(bm_ink, (0.16, 0.22, 0.035), loc=(0.45, 0.05, H + 0.0175), bevel=0.01)
    util.cylinder(bm_w, 0.03, 0.03, 0.01, loc=(0.45, 0.12, H + 0.036), segs=12)
    bevel_box(bm_ink, (0.02, 0.07, 0.015), loc=(0.53, -0.12, H + 0.008), bevel=0.004)
    # mountain-shaped brush rack with hanging brushes
    for dx in (-0.12, 0.12):
        util.box(bm_br, (0.02, 0.05, 0.2), loc=(-0.55 + dx, 0.15, H + 0.1))
    util.tube(bm_br, util.catmull([V((-0.7, 0.15, H + 0.18)), V((-0.62, 0.15, H + 0.24)), V((-0.55, 0.15, H + 0.2)),
                                   V((-0.48, 0.15, H + 0.26)), V((-0.4, 0.15, H + 0.18))], 4), (0.012, 0.02), n=6)
    for k in range(4):
        x = -0.66 + k * 0.07
        util.tube(bm_br, [V((x, 0.15, H + 0.2)), V((x, 0.15, H + 0.03))], 0.005, n=5)
        util.cylinder(bm_tip, 0.007, 0.001, 0.035, loc=(x, 0.15, H + 0.02), segs=6, rot=Matrix.Rotation(R(180), 4, "X"))
    util.cylinder(bm_pot, 0.06, 0.06, 0.16, loc=(0.62, 0.2, H + 0.08), segs=14)
    for k in range(5):
        a = k * 1.3
        util.tube(bm_br, [V((0.62 + math.cos(a) * 0.02, 0.2 + math.sin(a) * 0.02, H + 0.05)),
                          V((0.62 + math.cos(a) * 0.05, 0.2 + math.sin(a) * 0.05, H + 0.32))], 0.005, n=5)
    bevel_box(bm_seal, (0.08, 0.08, 0.05), loc=(0.3, 0.22, H + 0.025), bevel=0.008)
    chair(bm_ch, (0, 0.62, 0), yaw=R(180))
    objs = [obj("Desk", bm_t, m["rosewood"], uv=1.3), obj("Calligraphy", bm_pp, m["ink_paper"]),
            obj("Paperweights", bm_w, m["jade"], uv=6.0), obj("InkStone", bm_ink, m["dark_stone"], uv=4.0),
            obj("Brushes", bm_br, m["bamboo"], uv=6.0, smooth=True), obj("BrushTips", bm_tip, m["dark"], smooth=True),
            obj("BrushPot", bm_pot, m["blue_white"], smooth=True), obj("Chair", bm_ch, m["rosewood"], uv=1.5),
            obj("SealBox", bm_seal, m["lacquer_red"], uv=6.0)]
    objs.append(util.collider("DeskCol", (W, D, H + 0.1), (0, 0, (H + 0.1) / 2)))
    objs.append(util.collider("ChairCol", (0.6, 0.5, 1.1), (0, 0.62, 0.55)))
    return objs


def hanging_scrolls():
    """Free-standing display frame with two ink-landscape scrolls and a calligraphy scroll
    (~2.3 x 0.6 x 2.4 m)."""
    m = Mats()
    bm_f, bm_l, bm_c, bm_r, bm_k, bm_s = (bmesh.new() for _ in range(6))
    for sx in (-1, 1):
        vs = ubox(bm_f, (0.12, 0.6, 0.12), loc=(sx * 1.1, 0, 0.06), bevel=0.02)
        bevel_box(bm_f, (0.08, 0.08, 2.35), loc=(sx * 1.1, 0, 1.2), bevel=0.01)
        util.sphere(bm_k, 0.05, loc=(sx * 1.1, 0, 2.4), segs=10, rings=6)
        for sy in (-1, 1):
            util.tube(bm_f, [V((sx * 1.1, sy * 0.25, 0.12)), V((sx * 1.1, sy * 0.04, 0.5))], 0.025, n=6)
    bevel_box(bm_f, (2.3, 0.07, 0.08), loc=(0, 0, 2.3), bevel=0.01)
    for k, x in enumerate((-0.68, 0.0, 0.68)):
        w, h = 0.52, 1.55
        zc = 2.18 - 0.12 - h / 2
        card(bm_l if k != 1 else bm_c, w, h, loc=(x, 0.0, zc), rect=(0, 0, 1, 1) if k == 0 else (1, 0, 0, 1))
        util.cylinder(bm_r, 0.015, 0.015, w + 0.04, loc=(x, 0, zc + h / 2 + 0.01), segs=8,
                      rot=Matrix.Rotation(R(90), 4, "Y"))
        util.cylinder(bm_r, 0.022, 0.022, w + 0.06, loc=(x, 0, zc - h / 2 - 0.015), segs=10,
                      rot=Matrix.Rotation(R(90), 4, "Y"))
        for sx in (-1, 1):
            util.cylinder(bm_k, 0.028, 0.028, 0.03, loc=(x + sx * (w / 2 + 0.045), 0, zc - h / 2 - 0.015), segs=10,
                          rot=Matrix.Rotation(R(90), 4, "Y"))
        util.tube(bm_s, [V((x - 0.15, 0, zc + h / 2 + 0.01)), V((x, 0, 2.26)), V((x + 0.15, 0, zc + h / 2 + 0.01))],
                  0.004, n=4)
    land = util.material("qp_ink_landscape", ink_landscape(512), double_sided=True, normal_strength=0.2)
    call = ink_paper("#efe6cf", 512, 840, 2, 9, box=(0.22, 0.08, 0.78, 0.92), stroke=0.016)
    u, v = tex.grid(512)
    mount = ((u < 0.08) | (u > 0.92) | (v < 0.05) | (v > 0.95)).astype(np.float32)
    call["albedo"] = tex.lerp(call["albedo"], tex.srgb("#3f5a4a"), mount)
    objs = [obj("ScrollFrame", bm_f, m["rosewood"], uv=1.5), obj("LandscapeScrolls", bm_l, land),
            obj("CalligraphyScroll", bm_c, util.material("qp_calligraphy_scroll", call, double_sided=True,
                                                         normal_strength=0.2)),
            obj("ScrollRods", bm_r, m["lacquer_black"], uv=4.0, smooth=True), obj("ScrollKnobs", bm_k, m["jade"],
                                                                                  uv=6.0, smooth=True),
            obj("ScrollCords", bm_s, m["string"])]
    objs.append(util.collider("ScrollFrameCol", (2.3, 0.6, 2.4), (0, 0, 1.2)))
    return objs


def _blade(bm, outline, z0, th=0.012, loc=(0, 0, 0), yaw=0.0):
    """Flat blade from an XZ outline (counter-clockwise), thickness th."""
    vs = new_verts(bm, lambda: lands.extrude_outline(bm, [(x, z + z0) for x, z in outline], -th / 2, th / 2))
    xf(bm, vs, loc, yaw=yaw)


def halberd_rack():
    """Polearm rack: guandao, ji halberd, tasselled spears and a trident standing in a
    timber rack (~2.4 x 0.7 x 2.9 m)."""
    m = Mats()
    bm_w, bm_s, bm_sh, bm_t = (bmesh.new() for _ in range(4))
    for sx in (-1, 1):
        bevel_box(bm_w, (0.12, 0.7, 0.12), loc=(sx * 1.15, 0, 0.06), bevel=0.02)
        bevel_box(bm_w, (0.1, 0.1, 1.6), loc=(sx * 1.15, 0.1, 0.805), bevel=0.01)
    for z in (0.3, 1.45):  # rails stop 10 mm short of the posts' outer faces
        bevel_box(bm_w, (2.38, 0.12, 0.08), loc=(0, 0.1, z), bevel=0.01)
    bevel_box(bm_w, (2.3, 0.29, 0.06), loc=(0, 0.0, 0.1), bevel=0.01)  # back edge 5 mm off the posts' backs
    xs = [-0.85, -0.42, 0.0, 0.42, 0.85]
    for k, x in enumerate(xs):
        top = 2.35
        util.cylinder(bm_sh, 0.022, 0.022, top - 0.125, loc=(x, 0.0, 0.125 + (top - 0.125) / 2), segs=8)
        util.cylinder(bm_s, 0.03, 0.028, 0.08, loc=(x, 0, 0.16), segs=8)
        kind = ["guandao", "spear", "ji", "spear", "trident"][k]
        if kind == "guandao":
            _blade(bm_s, [(-0.03, 0.0), (0.06, 0.0), (0.1, 0.2), (0.08, 0.42), (0.0, 0.6), (-0.02, 0.45),
                          (-0.04, 0.2)], top - 0.02, loc=(x, 0, 0))
            util.cylinder(bm_s, 0.04, 0.03, 0.06, loc=(x, 0, top), segs=8)
            util.sphere(bm_t, 0.03, loc=(x - 0.05, 0, top + 0.25), segs=8, rings=5)
        elif kind == "spear":
            _blade(bm_s, [(0.0, 0.0), (0.035, 0.08), (0.0, 0.32), (-0.035, 0.08)], top, loc=(x, 0, 0))
            util.cylinder(bm_t, 0.012, 0.06, 0.16, loc=(x, 0, top - 0.06), segs=10)
        elif kind == "ji":
            _blade(bm_s, [(0.0, 0.0), (0.03, 0.08), (0.0, 0.3), (-0.03, 0.08)], top, loc=(x, 0, 0))
            _blade(bm_s, [(0.0, -0.06), (0.1, -0.1), (0.2, -0.02), (0.22, 0.1), (0.14, 0.02), (0.0, 0.04)], top,
                   th=0.008, loc=(x, 0, 0))  # thinner than the spear point it crosses
        else:
            for dx in (-0.08, 0.0, 0.08):
                _blade(bm_s, [(dx - 0.012, 0.0), (dx + 0.012, 0.0), (dx + 0.012, 0.2), (dx, 0.26),
                              (dx - 0.012, 0.2)], top + 0.06, loc=(x, 0, 0))
            util.tube(bm_s, [V((x - 0.08, 0, top + 0.07)), V((x, 0, top)), V((x + 0.08, 0, top + 0.07))], 0.014, n=6)
    objs = [obj("RackTimber", bm_w, m["wood"], uv=1.2), obj("Blades", bm_s, m["steel"], uv=3.0),
            obj("Shafts", bm_sh, m["lacquer_red"], uv=2.0, smooth=True), obj("Tassels", bm_t, m["silk_red"], uv=4.0,
                                                                             smooth=True)]
    objs.append(util.collider("HalberdCol", (2.4, 0.7, 2.7), (0, 0.0, 1.35)))
    return objs


def sword_stand():
    """Lacquered cabinet with a three-tier sword stand of sheathed jian (~1.1 x 0.45 x 1.5 m)."""
    m = Mats()
    bm_c, bm_st, bm_sc, bm_g, bm_h, bm_t = (bmesh.new() for _ in range(6))
    bevel_box(bm_c, (1.1, 0.45, 0.72), loc=(0, 0, 0.4), bevel=0.015)
    bevel_box(bm_c, (1.16, 0.5, 0.04), loc=(0, 0, 0.78), bevel=0.01)
    for sx in (-1, 1):
        util.box(bm_c, (0.08, 0.4, 0.06), loc=(sx * 0.48, 0, 0.03))
        bevel_box(bm_st, (0.04, 0.2, 0.6), loc=(sx * 0.32, 0.02, 1.103), bevel=0.008)
        bevel_box(bm_st, (0.16, 0.26, 0.04), loc=(sx * 0.32, 0.02, 0.82), bevel=0.008)
        for k in range(3):
            bevel_box(bm_st, (0.05, 0.1, 0.03), loc=(sx * 0.32, -0.05 - 0.0, 0.96 + k * 0.17), bevel=0.006)
    for k in range(3):
        z = 1.0 + k * 0.17
        x0, x1 = -0.46, 0.4
        util.cylinder(bm_sc, 0.022, 0.018, x1 - x0, loc=((x0 + x1) / 2, -0.07, z), segs=8,
                      rot=Matrix.Rotation(R(90), 4, "Y"))
        for x in (x0 + 0.08, x0 + 0.4, x1 - 0.03):
            util.cylinder(bm_g, 0.026, 0.026, 0.03, loc=(x, -0.07, z), segs=8, rot=Matrix.Rotation(R(90), 4, "Y"))
        bevel_box(bm_g, (0.03, 0.1, 0.035), loc=(x1 + 0.02, -0.07, z), bevel=0.006)
        util.cylinder(bm_h, 0.016, 0.016, 0.2, loc=(x1 + 0.13, -0.07, z), segs=8, rot=Matrix.Rotation(R(90), 4, "Y"))
        util.sphere(bm_g, 0.022, loc=(x1 + 0.24, -0.07, z), segs=8, rings=5)
        util.tube(bm_t, [V((x1 + 0.25, -0.07, z)), V((x1 + 0.28, -0.08, z - 0.12))], 0.004, n=4)
        util.cylinder(bm_t, 0.008, 0.02, 0.08, loc=(x1 + 0.28, -0.08, z - 0.16), segs=6)
    objs = [obj("SwordCabinet", bm_c, m["lacquer_black"], uv=1.2), obj("SwordStand", bm_st, m["rosewood"], uv=2.0),
            obj("Scabbards", bm_sc, m["leather"], uv=4.0, smooth=True), obj("SwordFittings", bm_g, m["gold"], uv=6.0,
                                                                            smooth=True),
            obj("SwordGrips", bm_h, m["silk_blue"], uv=6.0, smooth=True), obj("SwordTassels", bm_t, m["silk_red"],
                                                                              uv=6.0)]
    objs.append(util.collider("SwordStandCol", (1.2, 0.5, 1.45), (0, 0, 0.72)))
    return objs


def lantern_string():
    """Festival lanterns: a sagging rope strung between two poles hung with six red paper
    lanterns (~6.4 x 0.6 x 3.4 m). Tile several along a street."""
    m = Mats()
    bm_p, bm_s, bm_r, bm_l, bm_f, bm_g = (bmesh.new() for _ in range(6))
    span = 3.0
    for sx in (-1, 1):
        bevel_box(bm_s, (0.4, 0.4, 0.3), loc=(sx * span, 0, 0.15), bevel=0.03)
        util.cylinder(bm_p, 0.07, 0.06, 3.3, loc=(sx * span, 0, 1.8), segs=10)
        util.sphere(bm_p, 0.09, loc=(sx * span, 0, 3.47), segs=10, rings=6)
    sag = lambda t: 3.2 - 0.55 * math.sin(math.pi * t)  # noqa: E731
    rope = [V((-span + 2 * span * t, 0, sag(t))) for t in np.linspace(0, 1, 25)]
    util.tube(bm_r, rope, 0.012, n=5)
    for k in range(6):
        t = (k + 0.5) / 6
        p = V((-span + 2 * span * t, 0, sag(t)))
        util.tube(bm_r, [p, p + V((0, 0, -0.1))], 0.006, n=4)
        realms.lantern(bm_l, bm_f, (p.x, p.y, p.z - 0.1), 0.8)
        util.sphere(bm_g, 0.09, loc=(p.x, p.y, p.z - 0.42), segs=8, rings=5)
    objs = [obj("LanternPoles", bm_p, m["lacquer_red"], uv=1.5, smooth=True), obj("PoleBases", bm_s, m["stone"], uv=1.2),
            obj("LanternRope", bm_r, m["rope"], uv=4.0, smooth=True),
            obj("Lanterns", bm_l, m["paper_lantern"], smooth=True), obj("LanternFrames", bm_f, m["gold"], uv=4.0),
            obj("LanternGlow", bm_g, m["flame"], smooth=True)]
    for sx in (-1, 1):
        objs.append(util.collider("LanternPoleCol", (0.42, 0.42, 3.5), (sx * span, 0, 1.75)))
    return objs


def paper_umbrellas():
    """Umbrella maker's display: oil-paper parasols open in a stand and on the ground, one
    furled and leaning (~2.2 x 1.6 x 1.9 m)."""
    m = Mats()
    red = util.material("qp_umbrella_red", umbrella_paper(256, 841, "#c8352a"), double_sided=True,
                        normal_strength=0.4)
    teal = util.material("qp_umbrella_teal", umbrella_paper(256, 842, "#2f7a78"), double_sided=True,
                         normal_strength=0.4)
    bm_red, bm_teal, bm_b, bm_bk = (bmesh.new() for _ in range(4))

    def umbrella(bm_c, loc, yaw, pitch, R_=0.55, furled=False):
        vs = []
        if furled:
            vs += new_verts(bm_c, lambda: lathe_n(bm_c, [(0.001, 0.25), (0.06, 0.4), (0.07, 0.8), (0.03, 1.0),
                                                         (0.001, 1.05)], segs=12, u_rep=1.0))
            vs2 = new_verts(bm_b, lambda: util.cylinder(bm_b, 0.012, 0.012, 1.1, loc=(0, 0, 0.55), segs=6))
        else:
            vs += new_verts(bm_c, lambda: lathe_n(bm_c, [(0.001, 0.9), (R_ * 0.35, 0.87), (R_ * 0.7, 0.78),
                                                         (R_, 0.64)], segs=24, u_rep=1.0))
            vs2 = new_verts(bm_b, lambda: util.cylinder(bm_b, 0.012, 0.012, 0.95, loc=(0, 0, 0.47), segs=6))
            for k in range(12):
                a = 2 * math.pi * k / 12
                d = V((math.cos(a), math.sin(a), 0))
                vs2 += new_verts(bm_b, lambda: util.tube(bm_b, [V((0, 0, 0.55)), d * R_ * 0.55 + V((0, 0, 0.77))],
                                                         0.004, n=3))
            vs2 += new_verts(bm_b, lambda: util.sphere(bm_b, 0.025, loc=(0, 0, 0.92), segs=8, rings=5))
        xf(bm_c, vs, loc, yaw=yaw, pitch=pitch)
        xf(bm_b, vs2, loc, yaw=yaw, pitch=pitch)

    basket(bm_bk, (0.0, 0.3, 0.0), 0.2, 0.45)
    umbrella(bm_red, (0.0, 0.3, 0.35), 0.0, R(-8))
    umbrella(bm_teal, (-0.12, 0.38, 0.35), R(40), R(14), 0.5)
    umbrella(bm_teal, (-0.7, -0.35, 0.35), R(20), R(75), 0.55)
    umbrella(bm_red, (0.75, -0.2, 0.3), R(-100), R(70), 0.5)
    umbrella(bm_red, (0.55, 0.55, 0.0), R(0), R(-12), furled=True)
    objs = [obj("UmbrellaRed", bm_red, red, smooth=True), obj("UmbrellaTeal", bm_teal, teal, smooth=True),
            obj("UmbrellaShafts", bm_b, m["bamboo"], uv=4.0, smooth=True), obj("UmbrellaBasket", bm_bk, m["woven"],
                                                                               smooth=True)]
    objs.append(util.collider("UmbrellaStandCol", (0.5, 0.5, 1.2), (0.0, 0.3, 0.6)))
    return objs


def spirit_bird_cage():
    """A domed bamboo birdcage hanging from a stand, holding a luminous spirit bird with a
    trailing tail (~0.9 x 0.9 x 2.3 m)."""
    m = Mats()
    bm_w, bm_c, bm_b, bm_t, bm_bk = (bmesh.new() for _ in range(5))
    for k, yaw in enumerate((0, R(90))):  # crossed feet differ by 6 mm so their faces don't coincide
        vs = ubox(bm_w, (0.8, 0.1 - 0.006 * k, 0.08 + 0.006 * k), bevel=0.015)
        xf(bm_w, vs, (0, 0, 0.04 + 0.006 * k), yaw=yaw)
    util.cylinder(bm_w, 0.04, 0.035, 2.2, loc=(0, 0, 1.14), segs=10)
    util.tube(bm_w, util.catmull([V((0, 0, 2.2)), V((0, -0.2, 2.3)), V((0, -0.42, 2.25))], 4), 0.025, n=6)
    top = V((0, -0.42, 2.2))
    util.tube(bm_c, [V((0, -0.42, 2.25)), top], 0.005, n=4)
    hoop(bm_c, top + V((0, 0, -0.03)), 0.03, 0.006, normal=(1, 0, 0), segs=12, n=4)
    base = top + V((0, 0, -0.72))
    R_ = 0.24
    util.cylinder(bm_c, R_ + 0.02, R_ + 0.02, 0.04, loc=base, segs=24)
    for z in (0.06, 0.2):
        hoop(bm_c, base + V((0, 0, z)), R_, 0.006, segs=32, n=4)
    for k in range(20):
        a = 2 * math.pi * k / 20
        d = V((math.cos(a), math.sin(a), 0))
        pts = [base + d * R_ * (math.cos(t * math.pi / 2) if t > 0.55 else 1.0) +
               V((0, 0, 0.012 + (0.5 * t if t <= 0.55 else 0.275 + 0.35 * math.sin((t - 0.55) / 0.45 * math.pi / 2))))
               for t in np.linspace(0, 0.9, 10)]  # bars stop at the crown ring instead of meeting in one point
        util.tube(bm_c, pts, 0.004, n=3)
    hoop(bm_c, base + V((0, 0, 0.02 + 0.275 + 0.35 * math.sin(0.35 / 0.45 * math.pi / 2))), R_ * math.cos(0.45 * math.pi),
         0.006, segs=16, n=4)
    util.sphere(bm_c, 0.045, loc=base + V((0, 0, 0.64)), segs=12, rings=6, scale=(1, 1, 0.5))
    util.cylinder(bm_c, 0.006, 0.006, 0.36, loc=base + V((0, 0, 0.18)), segs=4, rot=Matrix.Rotation(R(90), 4, "Y"))
    # spirit bird on its perch
    p = base + V((0, 0, 0.26))
    util.sphere(bm_b, 0.05, loc=p, segs=12, rings=8, scale=(0.8, 1.2, 0.9))
    util.sphere(bm_b, 0.032, loc=p + V((0, -0.06, 0.05)), segs=10, rings=6)
    util.cylinder(bm_bk, 0.008, 0.001, 0.03, loc=p + V((0, -0.1, 0.05)), segs=6, rot=Matrix.Rotation(R(90), 4, "X"))
    for k in range(3):
        util.tube(bm_t, util.catmull([p + V((0, 0.05, 0)), p + V(((k - 1) * 0.03, 0.14, -0.08)),
                                      p + V(((k - 1) * 0.06, 0.2, -0.2))], 4), lambda t: 0.012 * (1 - 0.6 * t), n=5)
    glow = _glow("qp_spirit_bird", "#9fe8ff", 4.0)
    tail = _glow("qp_spirit_tail", "#c69cff", 5.0)
    objs = [obj("CageStand", bm_w, m["wood"], uv=1.5, smooth=True), obj("Cage", bm_c, m["bamboo"], uv=4.0, smooth=True),
            obj("SpiritBird", bm_b, glow, smooth=True), obj("SpiritBirdTail", bm_t, tail, smooth=True),
            obj("SpiritBirdBeak", bm_bk, m["gold"], uv=8.0)]
    objs.append(util.collider("CageStandCol", (0.35, 0.35, 2.3), (0, 0, 1.15)))
    return objs


def hand_cart():
    """Two-wheeled handcart loaded with sacks and a crate, handles resting on a prop leg
    (~1.3 x 2.6 x 1.3 m)."""
    m = Mats()
    bm_w, bm_wh, bm_i, bm_s, bm_cr = (bmesh.new() for _ in range(5))
    bed_z = 0.62
    bevel_box(bm_w, (1.0, 1.3, 0.06), loc=(0, 0.2, bed_z), bevel=0.01)
    for sx in (-1, 1):
        util.box(bm_w, (0.04, 1.306, 0.25), loc=(sx * 0.5, 0.2, bed_z + 0.15))
        util.tube(bm_w, [V((sx * 0.42, 0.85, bed_z - 0.03)), V((sx * 0.42, -1.2, bed_z + 0.02))], 0.03, n=6)
        util.tube(bm_w, [V((sx * 0.42, -0.5, bed_z - 0.03)), V((sx * 0.38, -0.55, 0.0))], 0.025, n=6)
        # spoked wheel
        c = V((sx * 0.6, 0.3, 0.45))
        hoop(bm_wh, c, 0.43, 0.035, normal=(1, 0, 0), segs=30, n=7)
        hoop(bm_i, c, 0.45, 0.04, normal=(1, 0, 0), segs=28, n=4, rx=0.012)  # tyre: 8 cm wide, thin
        util.cylinder(bm_wh, 0.07, 0.07, 0.14, loc=c, segs=12, rot=Matrix.Rotation(R(90), 4, "Y"))
        for k in range(10):
            a = 2 * math.pi * k / 10
            d = V((0, math.cos(a), math.sin(a)))
            util.tube(bm_wh, [c + d * 0.06, c + d * 0.42], 0.016, n=5)  # from the hub, not its centre
    for sy in (-0.4, 0.85):
        util.box(bm_w, (1.0, 0.04, 0.244), loc=(0, sy, bed_z + 0.15))
    util.cylinder(bm_i, 0.025, 0.025, 1.3, loc=(0, 0.3, 0.45), segs=8, rot=Matrix.Rotation(R(90), 4, "Y"))
    sack(bm_s, (-0.22, 0.4, bed_z + 0.03), 0.75, yaw=R(10), pitch=R(-85))
    sack(bm_s, (0.2, 0.45, bed_z + 0.03), 0.75, yaw=R(-5), pitch=R(-85))
    sack(bm_s, (0.0, 0.5, bed_z + 0.35), 0.7, yaw=R(0), pitch=R(-80))
    ubox(bm_cr, (0.45, 0.4, 0.35), loc=(0.1, -0.15, bed_z + 0.2), yaw=R(8), bevel=0.012, rect=(0, 0, 1, 1))
    objs = [obj("CartBed", bm_w, m["old_planks"], uv=1.2), obj("Wheels", bm_wh, m["wood"], uv=2.0, smooth=True),
            obj("CartIron", bm_i, m["iron"], uv=3.0, smooth=True), obj("CartSacks", bm_s, m["canvas"], smooth=True),
            obj("CartCrate", bm_cr, m["planks"])]
    objs.append(util.collider("CartCol", (1.4, 1.5, 1.25), (0, 0.25, 0.62)))
    objs.append(util.collider("HandleCol", (0.9, 0.9, 0.7), (0, -0.75, 0.35)))
    return objs


def fishing_nets():
    """Bamboo net-drying frame with nets draped over the bar, cork floats, a fish basket
    and oars (~3.2 x 1.6 x 2.0 m)."""
    m = Mats()
    bm_b, bm_n, bm_f, bm_bk, bm_fish = (bmesh.new() for _ in range(5))
    L = 3.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            x = sx * L / 2 + sy * 0.012  # the two legs of each A-frame lashed side by side, not merged
            util.tube(bm_b, [V((x, sy * 0.55, 0.0)), V((x, -sy * 0.05, 2.0))], 0.03, n=6)
    util.cylinder(bm_b, 0.03, 0.03, L + 0.3, loc=(0, 0, 1.92), segs=8, rot=Matrix.Rotation(R(90), 4, "Y"))
    for sy in (-1, 1):
        card(bm_n, L - 0.2, 1.6, loc=(0, sy * 0.3, 1.15), pitch=sy * R(18), cols=10, rows=6,
             bend=lambda x, z: 0.08 * math.sin(x * 2.5) * (1 - (z + 0.8) / 1.6) + 0.05 * (1 - ((z + 0.8) / 1.6)) ** 2)
        for k in range(12):
            x = -L / 2 + 0.2 + k * (L - 0.4) / 11
            util.cylinder(bm_f, 0.035, 0.035, 0.07, loc=(x, sy * 0.55, 0.4 + 0.05 * math.sin(x * 2.5)), segs=8,
                          rot=Matrix.Rotation(R(90), 4, "Y"))
    basket(bm_bk, (1.0, -0.95, 0.0), 0.25, 0.3)
    rnd = random.Random(77)
    for i in range(5):
        vs = util.sphere(bm_fish, 0.03, segs=10, rings=6, scale=(3.2, 1.0, 0.8))
        xf(bm_fish, vs, (1.0 + rnd.uniform(-0.12, 0.12), -0.95 + rnd.uniform(-0.12, 0.12), 0.3), yaw=rnd.uniform(0, 3))
    for dy in (0.0, -0.22):  # two oars side by side (they used to overlap blade on blade)
        util.tube(bm_b, [V((-1.2, -0.9 + dy, 0.02)), V((-0.2, -1.1 + dy, 0.02))], 0.025, n=6)
        ubox(bm_b, (0.4, 0.14, 0.02), loc=(-1.35, -0.88 + dy, 0.02), yaw=R(-11))
    objs = [obj("NetFrame", bm_b, m["bamboo"], uv=2.0, smooth=True), obj("Nets", bm_n, m["net"]),
            obj("NetFloats", bm_f, m["wood_light"], uv=6.0, smooth=True),
            obj("FishBasket", bm_bk, m["woven"], smooth=True), obj("Fish", bm_fish, m["fish"], uv=8.0, smooth=True)]
    objs.append(util.collider("NetFrameCol", (L + 0.1, 1.2, 2.0), (0, 0, 1.0)))
    return objs


def altar_candles():
    """Tiered candle altar crowded with red candles of many heights (~1.2 x 0.6 x 1.3 m)."""
    m = Mats()
    rnd = random.Random(79)
    bm_s, bm_c, bm_f, bm_d = (bmesh.new() for _ in range(4))
    for k, (w, d, z) in enumerate(((1.2, 0.6, 0.55), (0.95, 0.4, 0.7), (0.7, 0.22, 0.85))):
        bevel_box(bm_s, (w, d, z if k == 0 else 0.15), loc=(0, 0.18 * k - 0.0 + (0.1 if k else 0),
                                                           z / 2 if k == 0 else z - 0.075), bevel=0.012)
    for k, (z, y0, w, n) in enumerate(((0.55, -0.2, 1.1, 7), (0.7, 0.08, 0.85, 5), (0.85, 0.3, 0.6, 4))):
        for i in range(n):
            x = -w / 2 + 0.06 + i * (w - 0.12) / (n - 1)
            y = y0 + rnd.uniform(-0.04, 0.04)
            util.cylinder(bm_d, 0.05, 0.05, 0.012, loc=(x, y, z + 0.006), segs=12)
            candle(bm_c, bm_f, (x, y, z + 0.012), h=rnd.uniform(0.1, 0.32), r=rnd.uniform(0.022, 0.035))
    objs = [obj("CandleAltar", bm_s, m["lacquer_red"], uv=1.5), obj("Candles", bm_c, m["candle"], smooth=True),
            obj("CandleFlames", bm_f, m["flame"], smooth=True), obj("CandleDishes", bm_d, m["brass"], uv=6.0)]
    objs.append(util.collider("CandleAltarCol", (1.2, 0.6, 0.9), (0, 0.05, 0.45)))
    return objs


def incense_coils():
    """Temple incense coils: three great hanging spiral coils with red prayer tags and
    glowing tips on a lacquered frame (~1.9 x 0.6 x 2.3 m)."""
    m = Mats()
    bm_w, bm_i, bm_g, bm_t, bm_h = (bmesh.new() for _ in range(5))
    for sx in (-1, 1):
        vs = ubox(bm_w, (0.12, 0.6, 0.1), loc=(sx * 0.9, 0, 0.05), bevel=0.015)
        bevel_box(bm_w, (0.09, 0.09, 2.25), loc=(sx * 0.9, 0, 1.12), bevel=0.01)
    bevel_box(bm_w, (1.95, 0.1, 0.1), loc=(0, 0, 2.2), bevel=0.012)
    for k, x in enumerate((-0.55, 0.0, 0.55)):
        top = V((x, 0, 2.15))
        rr = [0.3, 0.36, 0.3][k]
        z0 = 1.45 - 0.08 * (k % 2)
        util.tube(bm_h, [top + V((0, 0, 0.02)), V((x, 0, z0 + 0.28))], 0.005, n=4)
        for a in (0, 2 * math.pi / 3, 4 * math.pi / 3):
            util.tube(bm_h, [V((x, 0, z0 + 0.28)), V((x + math.cos(a) * rr, math.sin(a) * rr, z0))], 0.003, n=3)
        pts = []
        turns = 7
        for t in np.linspace(0, 1, 220):
            ang = t * turns * 2 * math.pi
            r = 0.03 + (rr - 0.03) * t
            pts.append(V((x + math.cos(ang) * r, math.sin(ang) * r, z0 + 0.25 - 0.25 * t)))
        util.tube(bm_i, pts, 0.009, n=4)
        util.sphere(bm_g, 0.014, loc=pts[-1], segs=6, rings=4)
        card(bm_t, 0.08, 0.32, loc=(x, -0.005, z0 - 0.2), rect=(0, 0, 1, 1))
    objs = [obj("CoilFrame", bm_w, m["lacquer_red"], uv=1.5), obj("IncenseCoils", bm_i, m["incense"], smooth=True),
            obj("CoilEmbers", bm_g, m["ember"], smooth=True), obj("PrayerTags", bm_t, m["talisman"]),
            obj("CoilHangers", bm_h, m["iron"])]
    objs.append(util.collider("CoilFrameCol", (1.95, 0.6, 2.25), (0, 0, 1.12)))
    return objs


def pottery_stack():
    """Potter's stall: a two-tier plank shelf of blue-and-white bowls, celadon plates and
    brown stoneware jars, with more jars on the ground (~1.6 x 0.8 x 1.3 m)."""
    m = Mats()
    rnd = random.Random(81)
    bm_s, bm_bw, bm_cel, bm_st = (bmesh.new() for _ in range(4))
    for z in (0.45, 0.95):
        bevel_box(bm_s, (1.5, 0.45, 0.04), loc=(0, 0.1, z), bevel=0.008)
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm_s, (0.05, 0.05, 1.0), loc=(sx * 0.7, 0.1 + sy * 0.18, 0.5))
    for i in range(4):  # bowl stacks
        x = -0.55 + i * 0.36
        for k in range(rnd.randint(3, 6)):
            lathe_n(bm_bw, [(0.001, 0.0), (0.04, 0.0), (0.05, 0.01), (0.1, 0.06), (0.105, 0.065), (0.095, 0.065),
                            (0.045, 0.015), (0.001, 0.015)], segs=20, loc=(x, 0.1, 0.97 + k * 0.03))
    for i in range(5):  # plates standing on edge
        vs = new_verts(bm_cel, lambda: plate(bm_cel, (0, 0, 0), 0.12))
        xf(bm_cel, vs, (-0.5 + i * 0.25, 0.2, 0.595), pitch=R(78))
    for i, (x, y, z, s) in enumerate(((-0.4, 0.05, 0.0, 1.0), (0.1, 0.1, 0.0, 1.3), (0.5, 0.05, 0.0, 0.9),
                                      (0.9, -0.3, 0.0, 1.4), (1.05, 0.1, 0.0, 1.1), (-0.95, -0.2, 0.0, 1.2))):
        prof = [(0.001, 0.0), (0.08 * s, 0.0), (0.14 * s, 0.12 * s), (0.15 * s, 0.22 * s), (0.08 * s, 0.33 * s),
                (0.07 * s, 0.36 * s), (0.08 * s, 0.37 * s), (0.001, 0.36 * s)]
        lathe_n(bm_st if i != 2 else bm_bw, prof, segs=20, loc=(x, y, z + (0.47 if i < 3 else 0.0)))
    objs = [obj("PotteryShelf", bm_s, m["old_planks"], uv=1.2), obj("BlueWhite", bm_bw, m["blue_white"], smooth=True),
            obj("CeladonPlates", bm_cel, m["celadon"], uv=4.0, smooth=True),
            obj("Stoneware", bm_st, m["stoneware"], uv=3.0, smooth=True)]
    objs.append(util.collider("PotteryCol", (1.5, 0.5, 1.15), (0, 0.1, 0.57)))
    objs.append(util.collider("GroundJarsCol", (0.7, 0.7, 0.5), (1.0, -0.1, 0.25)))
    return objs


def firewood_pile():
    """Cord of split firewood under a plank lean-to, a chopping stump with an axe in it
    (~2.2 x 1.4 x 1.7 m)."""
    m = Mats()
    rnd = random.Random(83)
    bm_l, bm_e, bm_r, bm_st, bm_top, bm_ax, bm_h = (bmesh.new() for _ in range(7))
    rot = Matrix.Rotation(R(90), 4, "X")
    for layer in range(6):
        for i in range(9):
            if layer >= 4 and (i < 1 or i > 7):
                continue
            x = -0.8 + i * 0.2 + (layer % 2) * 0.1
            z = 0.09 + layer * 0.16
            r = rnd.uniform(0.07, 0.09)
            ln = 0.55
            yaw = R(rnd.uniform(-4, 4))
            vs = util.cylinder(bm_l, r, r, ln, loc=(0, 0, 0), segs=6, rot=rot)
            xf(bm_l, vs, (x, 0.35, z), yaw=yaw, roll=R(rnd.uniform(0, 60)))
            vs = util.cylinder(bm_e, r * 0.98, r * 0.98, 0.01, loc=(0, 0, 0), segs=6, rot=rot)
            xf(bm_e, vs, (x, 0.35 - ln / 2 - 0.003, z), yaw=yaw)
    # lean-to roof of planks on two posts
    for sx in (-1, 1):
        util.box(bm_r, (0.08, 0.08, 1.5), loc=(sx * 1.0, -0.05, 0.75))
        util.box(bm_r, (0.08, 0.08, 1.2), loc=(sx * 1.0, 0.7, 0.6))
    ubox(bm_r, (2.3, 1.1, 0.04), loc=(0, 0.33, 1.4), pitch=R(15), rect=(0, 0, 3, 1))
    # chopping stump with an axe
    util.cylinder(bm_st, 0.25, 0.28, 0.45, loc=(0.6, -0.55, 0.225), segs=14)
    util.cylinder(bm_top, 0.25, 0.25, 0.005, loc=(0.6, -0.55, 0.452), segs=14)
    util.tube(bm_h, [V((0.55, -0.55, 0.45)), V((0.35, -0.6, 0.85))], lambda t: 0.018, n=6)
    ubox(bm_ax, (0.03, 0.14, 0.12), loc=(0.57, -0.55, 0.44), roll=R(-25))
    for k in range(4):  # kindling
        vs = util.cylinder(bm_l, 0.03, 0.03, 0.4, loc=(0, 0, 0), segs=5, rot=Matrix.Rotation(R(90), 4, "Y"))
        xf(bm_l, vs, (0.1 + k * 0.06, -0.6, 0.03), yaw=R(rnd.uniform(-30, 30)))
    objs = [obj("Firewood", bm_l, m["bark"], uv=2.0), obj("LogEnds", bm_e, m["end_grain"]),
            obj("LeanTo", bm_r, m["old_planks"], uv=1.0), obj("Stump", bm_st, m["bark"], uv=2.0, smooth=True),
            obj("StumpTop", bm_top, m["end_grain"]), obj("AxeHead", bm_ax, m["iron"], uv=6.0),
            obj("AxeHandle", bm_h, m["wood_light"], uv=6.0, smooth=True)]
    tp = objs[4]  # planar end-grain uv on the stump top
    bm = bmesh.new()
    bm.from_mesh(tp.data)
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for loop in f.loops:
            loop[uvl].uv = ((loop.vert.co.x - 0.6) / 0.5 + 0.5, (loop.vert.co.y + 0.55) / 0.5 + 0.5)
    bm.to_mesh(tp.data)
    bm.free()
    objs.append(util.collider("WoodpileCol", (2.1, 1.0, 1.45), (0, 0.3, 0.72)))
    objs.append(util.collider("StumpCol", (0.55, 0.55, 0.45), (0.6, -0.55, 0.225)))
    return objs


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------
QUEST = {
    "notice_board": notice_board,
    "ancestral_tablet": ancestral_tablet,
    "pill_furnace": pill_furnace,
    "sword_in_stone": sword_in_stone,
    "tortoise_stele": tortoise_stele,
    "guardian_lion": guardian_lion,
    "bronze_ding": bronze_ding,
    "bronze_mirror": bronze_mirror,
    "spirit_lamp": spirit_lamp,
    "scroll_rack": scroll_rack,
    "war_drum": war_drum,
    "sealed_coffin": sealed_coffin,
    "offering_table": offering_table,
    "rune_pillar": rune_pillar,
    "armillary_sphere": armillary_sphere,
    "medicine_cabinet": medicine_cabinet,
    "wine_jars": wine_jars,
    "loom": loom,
    "map_table": map_table,
    "crane_statue": crane_statue,
    "spirit_fountain": spirit_fountain,
    "puppet_frame": puppet_frame,
    "herb_drying_rack": herb_drying_rack,
    "chain_anchor": chain_anchor,
    "soul_lantern": soul_lantern,
    "abacus_desk": abacus_desk,
    "fishing_boat": fishing_boat,
    "wishing_tree": wishing_tree,
    "jade_screen": jade_screen,
    "stone_tablet_array": stone_tablet_array,
}

DRESSING = {
    "goods_baskets": goods_baskets,
    "cloth_bolts": cloth_bolts,
    "grain_sacks": grain_sacks,
    "barrel_stack": barrel_stack,
    "tea_set": tea_set,
    "calligraphy_table": calligraphy_table,
    "hanging_scrolls": hanging_scrolls,
    "halberd_rack": halberd_rack,
    "sword_stand": sword_stand,
    "lantern_string": lantern_string,
    "paper_umbrellas": paper_umbrellas,
    "spirit_bird_cage": spirit_bird_cage,
    "hand_cart": hand_cart,
    "fishing_nets": fishing_nets,
    "altar_candles": altar_candles,
    "incense_coils": incense_coils,
    "pottery_stack": pottery_stack,
    "firewood_pile": firewood_pile,
}

ASSETS = dict(QUEST)
ASSETS.update(DRESSING)

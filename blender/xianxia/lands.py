"""Bamboo forest, mortal town and shared quest props.

Every builder follows the house conventions: Blender Z-up, fronts face -Y
(+Z in Godot), origin at ground centre, invisible '-convcolonly'/'-colonly'
colliders and '-col' terrain. The forest and town terrains read their height
fields from the map layouts in tools/maps so layout and ground always agree.
"""
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import arch, nature, props, tex, util

V = Vector
R = math.radians
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def clip_alpha(mat):
    """Turn a texture-alpha material into alpha scissor (glTF MASK)."""
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if not bsdf.inputs["Alpha"].links:
        return mat
    link = bsdf.inputs["Alpha"].links[0]
    src = link.from_socket
    if link.from_node.type == "MATH":
        return mat
    nt.links.remove(link)
    rnd = nt.nodes.new("ShaderNodeMath")
    rnd.operation = "ROUND"
    nt.links.new(src, rnd.inputs[0])
    nt.links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    return mat


def obj(name, bm, mat, uv=None, smooth=False):
    """mesh_object + optional box UV projection (metres * uv)."""
    o = util.mesh_object(name, bm, mat, smooth=smooth)
    if uv is not None:
        util.box_uv(o, uv)
    return o


def bevel_box(bm, size, loc=(0, 0, 0), rot=None, bevel=0.03, segs=1):
    """util.box with bevelled edges."""
    verts = util.box(bm, size, loc=loc, rot=rot)
    edges = list({e for v in verts for e in v.link_edges})
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=edges, offset=min(bevel, min(size) * 0.45), segments=segs,
                        affect="EDGES", profile=0.5)


def merge(bm, tmp):
    """Append the geometry of bmesh `tmp` to `bm` (frees tmp)."""
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def extrude_outline(bm, outline, y0, y1, uv_front=None):
    """Prism from a 2D outline in XZ (counter-clockwise seen from -Y), spanning y0..y1.

    uv_front: (x0, z0, w, h) maps the front/back faces to 0..1 UVs.
    """
    uv = bm.loops.layers.uv.verify()
    f_verts = [bm.verts.new(V((x, y0, z))) for (x, z) in outline]
    b_verts = [bm.verts.new(V((x, y1, z))) for (x, z) in outline]
    front = bm.faces.new(f_verts)
    back = bm.faces.new(list(reversed(b_verts)))
    n = len(outline)
    sides = [bm.faces.new((f_verts[i2], f_verts[i], b_verts[i], b_verts[i2]))
             for i, i2 in ((i, (i + 1) % n) for i in range(n))]
    bmesh.ops.recalc_face_normals(bm, faces=[front, back] + sides)
    if uv_front:
        x0, z0, w, h = uv_front
        for f in (front, back):
            for loop in f.loops:
                co = loop.vert.co
                u = (co.x - x0) / w
                loop[uv].uv = (u if f is front else 1 - u, (co.z - z0) / h)
    return front, back


def arc_outline(w, h_side, segs=10, z0=0.0):
    """Tablet outline: rectangle with a round top (XZ, counter-clockwise)."""
    pts = [(-w / 2, z0), (w / 2, z0), (w / 2, z0 + h_side)]
    for k in range(1, segs):
        a = math.pi * k / segs
        pts.append((w / 2 * math.cos(a), z0 + h_side + w / 2 * 0.55 * math.sin(a)))
    pts.append((-w / 2, z0 + h_side))
    return pts


def rock(bm, loc, size, seed, amount=0.3, subdiv=2):
    return nature.blob(bm, loc, size, amount, 1.4, seed, subdiv)


def transform_objs(objs, loc=(0, 0, 0), rot_z=0.0, scale=1.0):
    for o in objs:
        o.location = V(o.location) * scale
        o.scale = (scale, scale, scale)
        o.location.rotate(Matrix.Rotation(rot_z, 3, "Z"))
        o.rotation_euler.z += rot_z
        o.location += V(loc)
        util.apply_transform(o)
    return objs


def convex_mesh(name, bm):
    """Convex collision hull from arbitrary bmesh geometry."""
    # coincident input vertices make convex_hull report them both as used and unused; merge them first
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-4)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    extra = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if extra:
        bmesh.ops.delete(bm, geom=extra, context="VERTS")
    return util.mesh_object(name + "-convcolonly", bm, None, smooth=False)


# --------------------------------------------------------------------------
# textures (numpy, tileable unless noted)
# --------------------------------------------------------------------------
def planks(color, size=512, seed=401, boards=5, gap=0.02):
    """Weathered boards running along v; u crosses `boards` planks."""
    c = tex.srgb(color)
    u, v = tex.grid(size)
    rng = np.random.default_rng(seed)
    idx = np.floor(u * boards).astype(int)
    fu = u * boards - idx
    tone = rng.uniform(0.75, 1.15, boards + 1).astype(np.float32)[idx % boards]
    grain = tex.fbm(size, 8, 4, 0.5, seed, stretch=16)
    fine = tex.fbm(size, 64, 2, 0.5, seed + 1, stretch=16)
    seam_v = rng.uniform(0, 1, boards)[idx % boards]
    butt = np.abs(((v + seam_v) % 1.0) - 0.5) > 0.495
    edge = (fu < gap * boards) | (fu > 1 - gap * boards) | butt
    col = c * (tone * (0.72 + 0.35 * grain + 0.1 * fine))[..., None]
    knots = tex.sstep(0.82, 0.9, tex.fbm(size, 12, 3, 0.5, seed + 2))
    col = tex.lerp(col, col * 0.55, knots * 0.6)
    col = np.where(edge[..., None], col * 0.35, col)
    height = np.where(edge, 0.0, 0.6 + 0.3 * grain)
    return tex.result(col, 0.72 + 0.15 * grain, 0.0, height)


def thatch(size=512, seed=411, rows=6):
    """Straw thatch: overlapping courses along v, straws along v."""
    u, v = tex.grid(size)
    straw = tex.fbm(size, 96, 3, 0.55, seed, stretch=24)
    clump = tex.fbm(size, 8, 3, 0.5, seed + 1)
    fv = (v * rows + clump * 0.35) % 1.0
    course = tex.sstep(0.0, 0.85, fv)
    col = tex.lerp(tex.srgb("#5c4526"), tex.srgb("#b99d5f"), straw * 0.7 + clump * 0.3)
    col = col * (0.5 + 0.5 * course)[..., None]
    moss = tex.sstep(0.62, 0.8, tex.fbm(size, 5, 4, 0.5, seed + 2))
    col = tex.lerp(col, tex.srgb("#4d5a2a"), moss * 0.45)
    return tex.result(col, 0.95, 0.0, straw * 0.6 + course * 0.6)


def earth(color="#77603f", size=512, seed=421, pebbles=0.5):
    """Packed dirt with pebbles and faint wheel ruts."""
    c = tex.srgb(color)
    n = tex.fbm(size, 6, 6, 0.55, seed)
    grit = tex.fbm(size, 128, 2, 0.5, seed + 1)
    peb = tex.sstep(0.78, 0.86, tex.fbm(size, 48, 2, 0.5, seed + 2)) * pebbles
    col = c * (0.78 + 0.35 * n + 0.12 * (grit - 0.5))[..., None]
    col = tex.lerp(col, tex.srgb("#a69c8a") * (0.8 + 0.3 * grit)[..., None], peb)
    return tex.result(col, 0.92 - peb * 0.2, 0.0, n * 0.4 + grit * 0.25 + peb * 0.6)


def forest_floor(size=1024, seed=431):
    """Bamboo-forest floor: a carpet of dry leaves over soil with patches of moss and grass."""
    g = tex.grass(size, seed)
    n = tex.fbm(size, 6, 5, 0.55, seed + 3)
    moss = tex.fbm(size, 5, 4, 0.5, seed + 4)
    soil = tex.lerp(tex.srgb("#5a4a32"), tex.srgb("#7a6a45"), n)
    green = g["albedo"] * np.array([0.82, 0.95, 0.78], np.float32)
    cover = tex.sstep(0.4, 0.62, moss)
    col = tex.lerp(soil, green, cover)
    rng = np.random.default_rng(seed)
    leaves = np.zeros((size, size), np.float32)
    tone = np.zeros((size, size), np.float32)
    for _ in range(1400):
        x, y = rng.uniform(0, 1, 2)
        a = rng.uniform(0, math.pi)
        ln = rng.uniform(0.008, 0.02)
        pts = [((x + math.cos(a) * ln * t) % 1.0, (y + math.sin(a) * ln * t) % 1.0) for t in np.linspace(-1, 1, 7)]
        val = rng.uniform(0.4, 1.0)
        r = max(1, int(ln * size) + 3)
        cx, cy = int(x * size), int(y * size)
        ys, xs = np.arange(cy - r, cy + r + 1) % size, np.arange(cx - r, cx + r + 1) % size
        sub = np.zeros((len(ys), len(xs)), np.float32)
        for (px, py) in pts:
            dx = (np.arange(cx - r, cx + r + 1) - px * size)[None, :]
            dy = (np.arange(cy - r, cy + r + 1) - py * size)[:, None]
            dx = (dx + size / 2) % size - size / 2
            dy = (dy + size / 2) % size - size / 2
            sub = np.maximum(sub, np.clip(1.6 - np.sqrt(dx * dx + dy * dy) / (0.0024 * size), 0, 1))
        blk = leaves[np.ix_(ys, xs)]
        upd = sub > blk
        leaves[np.ix_(ys, xs)] = np.where(upd, sub, blk)
        tone[np.ix_(ys, xs)] = np.where(upd, val, tone[np.ix_(ys, xs)])
    leaf_col = tex.lerp(tex.srgb("#7d6437"), tex.srgb("#c9ad6a"), tone)
    col = tex.lerp(col, leaf_col, np.clip(leaves, 0, 1) * (1 - cover * 0.75))
    return tex.result(col, 0.88, 0.0, g["height"] * 0.5 * cover + leaves * 0.5 + n * 0.2)


def pebbles(size=512, seed=441, cells=14, tint="#8c877c"):
    """Rounded river stones (worley cells)."""
    rng = np.random.default_rng(seed)
    u, v = tex.grid(size)
    pts = rng.random((cells, cells, 2)).astype(np.float32)
    tone = rng.uniform(0.6, 1.25, (cells, cells)).astype(np.float32)
    gx, gy = u * cells, v * cells
    ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
    f1 = np.full(u.shape, 9.0, np.float32)
    f2 = np.full(u.shape, 9.0, np.float32)
    t1 = np.ones(u.shape, np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = (ix + dx) % cells, (iy + dy) % cells
            p = pts[cy, cx]
            d = np.hypot(gx - (ix + dx + p[..., 0]), gy - (iy + dy + p[..., 1]))
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            t1 = np.where(closer, tone[cy, cx], t1)
            f1 = np.where(closer, d, f1)
    edge = f2 - f1
    dome = tex.sstep(0.0, 0.35, edge)
    n = tex.fbm(size, 16, 4, 0.5, seed + 1)
    col = tex.srgb(tint) * (t1 * (0.75 + 0.25 * n))[..., None]
    col = tex.lerp(tex.srgb("#3b3a2f") * 0.7, col, tex.sstep(0.0, 0.08, edge))
    return tex.result(col, 0.55 + (1 - dome) * 0.4, 0.0, dome * 0.8 + n * 0.1)


def rammed_earth(size=512, seed=451, color="#a08c6c"):
    """Horizontal courses of rammed earth with streaks."""
    c = tex.srgb(color)
    u, v = tex.grid(size)
    warp = tex.fbm(size, 4, 3, 0.5, seed)
    layer = np.sin((v * 10 + warp * 0.6) * math.pi * 2) * 0.5 + 0.5
    streak = tex.fbm(size, 32, 3, 0.5, seed + 1, stretch=1) * 0.6 + tex.fbm(size, 4, 4, 0.5, seed + 2) * 0.4
    col = c * (0.84 + 0.1 * layer + 0.14 * (streak - 0.5))[..., None]
    rain = tex.fbm(size, 24, 3, 0.5, seed + 3, stretch=12)
    col = tex.lerp(col, col * 0.72, tex.sstep(0.55, 0.8, rain) * (1 - v)[..., ] * 0.6)
    return tex.result(col, 0.93, 0.0, layer * 0.5 + streak * 0.4)


def canvas(color="#b5a482", size=512, seed=461, stripes=None):
    """Coarse canvas with stains, patches and optional awning stripes (along v)."""
    c = tex.srgb(color)
    u, v = tex.grid(size)
    w = tex.weave(size, 3.0)
    n = tex.fbm(size, 6, 5, 0.5, seed)
    col = c * (0.85 + 0.12 * w + 0.15 * (n - 0.5))[..., None]
    if stripes is not None:
        band = ((u * 8) % 1.0) < 0.5
        col = np.where(band[..., None], tex.srgb(stripes) * (0.85 + 0.15 * n)[..., None], col)
    stain = tex.sstep(0.6, 0.9, tex.fbm(size, 4, 4, 0.5, seed + 1))
    col = tex.lerp(col, col * np.array([0.7, 0.62, 0.5], np.float32), stain * 0.5)
    return tex.result(col, 0.9, 0.0, w * 0.4 + n * 0.2)


def glyph_mask(size, cols, rows, seed, box=(0.08, 0.08, 0.92, 0.92), stroke=0.012, vertical=True):
    """Pseudo-calligraphy characters laid out in columns (right to left)."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((size, size), np.float32)
    x0, y0, x1, y1 = box
    cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
    for ci in range(cols):
        for ri in range(rows):
            cx = x1 - (ci + 0.5) * cw if vertical else x0 + (ri + 0.5) * cw
            cy = y1 - (ri + 0.5) * ch if vertical else y1 - (ci + 0.5) * ch
            s = min(cw, ch) * 0.36
            for _ in range(rng.integers(3, 7)):
                kind = rng.integers(0, 5)
                ax, ay = cx + rng.uniform(-s, s * 0.4), cy + rng.uniform(-s, s)
                ln = rng.uniform(0.5, 1.2) * s
                if kind == 0:
                    pts = [(ax + t * ln, ay) for t in np.linspace(0, 1, 12)]
                elif kind == 1:
                    pts = [(cx + rng.uniform(-s, s) * 0.6, cy + s - t * 2 * s * rng.uniform(0.5, 1))
                           for t in np.linspace(0, 1, 12)]
                elif kind == 2:
                    pts = [(ax + t * ln * 0.7, ay - t * ln) for t in np.linspace(0, 1, 12)]
                elif kind == 3:
                    pts = [(ax + t * ln * 0.7, ay + t * ln * 0.5) for t in np.linspace(0, 1, 12)]
                else:
                    pts = [(ax + 0.3 * s * math.cos(a), ay + 0.3 * s * math.sin(a)) for a in np.linspace(0, 5.5, 14)]
                tex.stamp_curve(mask, [(p[0] % 1.0, p[1] % 1.0) for p in pts], stroke, size)
    return np.clip(mask, 0, 1)


def inscription(size=512, seed=471, color="#6f716b", cols=5, rows=9):
    """Stele face (u across, v up): carved title band, framed columns of characters."""
    base = tex.stone(color, size, seed, 0.2)
    u, v = tex.grid(size)
    frame = ((np.abs(u - 0.06) < 0.012) | (np.abs(u - 0.94) < 0.012) | (np.abs(v - 0.04) < 0.01)
             | (np.abs(v - 0.8) < 0.01)).astype(np.float32) * (v < 0.82)
    body = glyph_mask(size, cols, rows, seed, (0.1, 0.06, 0.9, 0.78), 0.009)
    title = glyph_mask(size, 1, 4, seed + 1, (0.4, 0.83, 0.6, 0.99), 0.011, vertical=True)
    cut = np.clip(body + title + frame, 0, 1)
    moss = tex.sstep(0.6, 0.85, tex.fbm(size, 6, 4, 0.5, seed + 3)) * (1 - v) ** 2
    col = tex.lerp(base["albedo"], base["albedo"] * 0.35, cut * 0.9)
    col = tex.lerp(col, tex.srgb("#4f6231"), moss * 0.7)
    base["albedo"] = col
    base["height"] = base["height"] * 0.4 - cut * 0.7
    base["cut"] = cut
    return base


def ruin_stone(size=512, seed=481, color="#9a968a", moss=0.45):
    """Old stone blocks with lichen and moss creeping in from above."""
    base = tex.stone(color, size, seed, 0.35)
    u, v = tex.grid(size)
    m = tex.fbm(size, 5, 5, 0.55, seed + 1)
    lichen = tex.sstep(0.7, 0.78, tex.fbm(size, 24, 3, 0.5, seed + 2))
    mm = tex.sstep(1 - moss, 1.0, m * 0.8 + v * 0.3)
    col = tex.lerp(base["albedo"], tex.srgb("#48602e") * (0.8 + 0.4 * m)[..., None], mm * 0.85)
    col = tex.lerp(col, tex.srgb("#c9c29a"), lichen * 0.35)
    base["albedo"] = col
    base["height"] = base["height"] + mm * 0.3
    base["rough"] = np.clip(base["rough"] + mm * 0.1, 0, 1)
    return base


def stone_blocks(color="#9a968a", size=512, seed=491, rows=4, cols=2, moss=0.3):
    """Ashlar blocks in a running bond with moss in the joints."""
    br = tex.bricks(color, size, seed, rows=rows, cols=cols)
    rs = ruin_stone(size, seed + 1, color, moss)
    col = br["albedo"] * 0.5 + rs["albedo"] * 0.6
    return tex.result(col, np.clip(rs["rough"], 0, 1), 0.0, br["height"] * 0.8 + rs["height"] * 0.3)


def jade_rune_disc(size=1024, seed=501, glow="#6ff2ff"):
    """Teleport array top: pale jade stone, octagonal borders, rune band, trigrams.

    Returns maps plus 'emit' (H, W, 3) for the glowing carvings.
    """
    base = tex.stone("#86a89a", size, seed, 0.15)
    j = tex.jade("#5fae8e", size, seed + 1)
    col = tex.lerp(base["albedo"], j["albedo"], 0.45)
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    oct_r = np.zeros_like(r)
    for k in range(4):
        ang = k * math.pi / 4 + math.pi / 8
        oct_r = np.maximum(oct_r, np.abs(x * math.cos(ang) + y * math.sin(ang)))

    def line(d, w):
        return 1 - tex.sstep(0.0, w, np.abs(d))
    carve = line(oct_r - 0.445, 0.006) + line(oct_r - 0.425, 0.004)
    carve += line(r - 0.395, 0.005) + line(r - 0.335, 0.005) + line(r - 0.2, 0.004) + line(r - 0.09, 0.004)
    # rune band: one pseudo-glyph per angular cell
    rng = np.random.default_rng(seed)
    cells = 40
    ci = np.floor((a + math.pi) / (2 * math.pi) * cells).astype(int) % cells
    s = ((a + math.pi) / (2 * math.pi) * cells) % 1.0
    t = (r - 0.345) / 0.04
    band = (t > 0) & (t < 1)
    hb = rng.random((cells, 3)) < 0.55
    vb = rng.random((cells, 3)) < 0.5
    runes = np.zeros_like(r)
    for k, tk in enumerate((0.2, 0.5, 0.8)):
        runes = np.maximum(runes, hb[ci, k] * (np.abs(t - tk) < 0.09) * (s > 0.18) * (s < 0.82))
    for k, sk in enumerate((0.22, 0.5, 0.78)):
        runes = np.maximum(runes, vb[ci, k] * (np.abs(s - sk) < 0.06) * (t > 0.12) * (t < 0.88))
    runes *= band
    # eight trigrams between r = 0.21 and 0.32
    tri = np.zeros_like(r)
    for k in range(8):
        ang = k * math.pi / 4
        ca, sa = math.cos(ang), math.sin(ang)
        rad = x * ca + y * sa
        tan = -x * sa + y * ca
        for bar in range(3):
            rr = 0.235 + bar * 0.03
            solid = (k >> bar) & 1
            on = (np.abs(rad - rr) < 0.008) & (np.abs(tan) < 0.045)
            if not solid:
                on &= np.abs(tan) > 0.01
            tri = np.maximum(tri, on.astype(np.float32))
    # taiji-ish centre
    inner = (r < 0.075).astype(np.float32)
    swirl = ((np.sin(a * 1 + r * 60) > 0) & (r < 0.075)).astype(np.float32)
    m = np.clip(carve + runes + tri + swirl * 0.8, 0, 1)
    col = tex.lerp(col, col * 0.75, inner * 0.3)
    col = tex.lerp(col, tex.srgb(glow), m * 0.85)
    out = tex.result(col, np.clip(0.4 - m * 0.2 + base["rough"] * 0.2, 0, 1), 0.0, base["height"] * 0.3 - m * 0.6)
    out["emit"] = np.clip(m[..., None] * tex.srgb(glow)[None, None, :], 0, 1)
    return out


def leaf_cards(size=512, seed=511, color="#5b8a3a", kind="bamboo"):
    """Transparent card of leaves (alpha in 'alpha'). Leaves hang toward v = 0.

    kind 'bamboo': lance-shaped leaves fanning from twigs; 'fern': a pinnate frond
    along the card's centre line (base at v = 0).
    """
    rng = np.random.default_rng(seed)
    u, v = tex.grid(size)
    alpha = np.zeros((size, size), np.float32)
    shade = np.zeros((size, size), np.float32)
    c = tex.srgb(color)

    def leaf(cx, cy, ang, ln, wd, tone):
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = u - cx, v - cy
        along = px * ca + py * sa
        across = -px * sa + py * ca
        t = along / ln
        prof = wd * np.clip(np.sin(np.clip(t, 0, 1) * math.pi), 0, 1) ** 0.8 * (1 - 0.4 * np.clip(t, 0, 1))
        m = (t > 0) & (t < 1) & (np.abs(across) < prof)
        vein = np.abs(across) < prof * 0.12
        nonlocal alpha, shade
        alpha = np.where(m, 1.0, alpha)
        shade = np.where(m, tone * (0.85 + 0.15 * (1 - np.abs(across) / np.maximum(prof, 1e-4))) - vein * 0.12, shade)

    if kind == "bamboo":
        for _ in range(34):
            cx, cy = rng.uniform(0.12, 0.88), rng.uniform(0.3, 0.97)
            for _ in range(rng.integers(4, 7)):
                ang = -math.pi / 2 + rng.uniform(-1.1, 1.1)
                leaf(cx, cy, ang, rng.uniform(0.18, 0.3), rng.uniform(0.02, 0.032), rng.uniform(0.7, 1.15))
    else:
        tex.stamp_curve(alpha, [(0.5 + 0.02 * math.sin(t * 3), t) for t in np.linspace(0.0, 0.97, 80)], 0.006, size)
        shade = np.maximum(shade, alpha * 0.6)
        for k in range(22):
            t = 0.08 + k * 0.04
            wl = 0.36 * math.sin(math.pi * min(1.0, t / 0.95)) + 0.05
            for side in (-1, 1):
                ang = math.pi / 2 - side * (1.2 - 0.4 * t)
                leaf(0.5 + 0.02 * math.sin(t * 3), t, ang, wl, 0.028, rng.uniform(0.8, 1.1))
    n = tex.fbm(size, 16, 3, 0.5, seed + 1)
    col = c * (shade * (0.8 + 0.3 * n))[..., None]
    col = tex.lerp(col, col * np.array([1.25, 1.15, 0.6], np.float32), tex.sstep(0.6, 0.9, n) * 0.35)
    out = tex.result(col, 0.7, 0.0, shade * 0.4)
    out["alpha"] = alpha
    return out


def path_strip(size=512, seed=521, color="#a08a66", edge_col="#6b6440"):
    """Dirt path ribbon (u across 0..1, v along). Ragged alpha edges."""
    base = earth(color, size, seed, 0.6)
    u, v = tex.grid(size)
    n = tex.fbm(size, 8, 4, 0.5, seed + 5)
    d = np.minimum(u, 1 - u) + (n - 0.5) * 0.18
    alpha = tex.sstep(0.03, 0.06, d)
    grassy = 1 - tex.sstep(0.06, 0.2, d)
    rut = np.exp(-((np.abs(u - 0.5) - 0.2) / 0.06) ** 2) * 0.1
    col = tex.lerp(base["albedo"] * (1 - rut)[..., None], tex.srgb(edge_col) * (0.8 + 0.4 * n)[..., None], grassy * 0.8)
    out = tex.result(col, base["rough"], 0.0, base["height"] - rut)
    out["alpha"] = alpha
    return out


def crops(size=512, seed=531):
    """Rows of young rice / millet over wet soil (rows along v)."""
    u, v = tex.grid(size)
    soil = earth("#5d4a32", size, seed, 0.1)
    rows = 10
    fu = (u * rows) % 1.0
    tuft = tex.fbm(size, 96, 2, 0.5, seed + 1, stretch=4)
    plant = tex.sstep(0.34, 0.14, np.abs(fu - 0.5)) * (0.6 + 0.4 * tuft)
    n = tex.fbm(size, 6, 4, 0.5, seed + 2)
    green = tex.lerp(tex.srgb("#5f9a32"), tex.srgb("#b5c85a"), n)
    col = tex.lerp(soil["albedo"], green * (0.7 + 0.5 * tuft)[..., None], np.clip(plant * 1.4, 0, 1))
    return tex.result(col, 0.85, 0.0, plant * 0.8 + soil["height"] * 0.3)


def crag(color="#7f7a6e", size=1024, seed=601, moss="#4f6233"):
    """Weathered rock face: blocky fractures, streaks and moss in the cracks (tri-planar use)."""
    base = tex.stone(color, size, seed, 0.25)
    u, v = tex.grid(size)
    big = tex.fbm(size, 3, 5, 0.55, seed + 1)
    ridges = 1 - np.abs(tex.fbm(size, 5, 4, 0.5, seed + 2) * 2 - 1)
    cracks = tex.sstep(0.86, 0.96, ridges)
    streak = tex.fbm(size, 24, 3, 0.5, seed + 3, stretch=8)
    col = base["albedo"] * (0.7 + 0.45 * big + 0.12 * (streak - 0.5))[..., None]
    col = tex.lerp(col, col * 0.35, cracks)
    mm = tex.sstep(0.55, 0.8, tex.fbm(size, 6, 4, 0.5, seed + 4) + cracks * 0.3)
    col = tex.lerp(col, tex.srgb(moss) * (0.7 + 0.5 * big)[..., None], mm * 0.75)
    height = big * 0.5 + base["height"] * 0.4 - cracks * 0.6 + mm * 0.1
    return tex.result(col, 0.85 + 0.1 * mm, 0.0, height)


def glaze(color, size=256, seed=541):
    c = tex.srgb(color)
    n = tex.fbm(size, 8, 4, 0.5, seed)
    col = c * (0.85 + 0.25 * n)[..., None]
    return tex.result(col, 0.25 + 0.1 * n, 0.0, n * 0.1)


def woven(color="#a8834a", size=256, seed=551):
    """Basketry / bamboo matting."""
    c = tex.srgb(color)
    w = tex.weave(size, 8.0)
    n = tex.fbm(size, 8, 3, 0.5, seed)
    col = c * (0.65 + 0.4 * w + 0.1 * n)[..., None]
    return tex.result(col, 0.8, 0.0, w)


def signboard(size=512, seed=561, chars=4, field="#2b1d14", ink="#e3b85a", vertical=True):
    """Shop sign: dark lacquer board with gilded characters and a border."""
    u, v = tex.grid(size)
    wood = tex.lacquer(field, size, seed, 0.3)
    if vertical:
        m = glyph_mask(size, 1, chars, seed, (0.2, 0.08, 0.8, 0.92), 0.02)
    else:
        m = glyph_mask(size, chars, 1, seed, (0.08, 0.2, 0.92, 0.8), 0.02, vertical=False)
    border = ((u < 0.06) | (u > 0.94) | (v < 0.04) | (v > 0.96)).astype(np.float32)
    mm = np.clip(m + border, 0, 1)
    col = tex.lerp(wood["albedo"], tex.srgb(ink), mm)
    return tex.result(col, 0.4 - mm * 0.15, mm * 0.8, wood["height"] * 0.2 + mm * 0.5)


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def kit():
    """arch.kit() plus the materials of the lands."""
    m = arch.kit()
    m["bronze"] = util.material("bronze", tex.metal("#7a6238", rough=0.35, patina="#41695c", patina_amt=0.22),
                                normal_strength=0.6)
    m["iron"] = util.material("iron", tex.metal("#3b3a38", rough=0.6, patina="#6b4a2e", patina_amt=0.3))
    m["planks"] = util.material("planks", planks("#7a5a3c", 512), normal_strength=0.7)
    m["old_planks"] = util.material("old_planks", planks("#6a6150", 512, 402), normal_strength=0.8)
    m["log"] = util.material("log_bark", tex.bark("#5b4a38", 512, 133), normal_strength=1.0)
    m["thatch"] = util.material("thatch", thatch(512), normal_strength=1.2)
    m["daub"] = util.material("daub", tex.plaster("#b9a27c", 512, 103, "#6d5a3e"), normal_strength=0.5)
    m["whitewash"] = util.material("whitewash", tex.plaster("#e8e4d8", 512, 104, "#8f877a"), normal_strength=0.3)
    m["earth_wall"] = util.material("rammed_earth", rammed_earth(512), normal_strength=0.8)
    m["ruin"] = util.material("ruin_stone", ruin_stone(512), normal_strength=1.0)
    m["blocks"] = util.material("stone_blocks", stone_blocks(), normal_strength=1.0)
    m["canvas"] = util.material("canvas", canvas(), double_sided=True, normal_strength=0.5)
    m["rope"] = util.material("rope", tex.bark("#9b855c", 128, 135), normal_strength=0.4)
    m["rock"] = util.material("rock", tex.stone("#8e8a82", 512, 75), normal_strength=1.2)
    m["moss"] = util.material("moss", tex.foliage("#4a6b2c", 256, 144), normal_strength=0.6)
    m["dark"] = util.material("shadow", color="#0d0b0a", rough=1.0)
    return m


def glow_mat(name, color, strength=4.0):
    return util.material(name, color=color, rough=0.4, emission=color, emission_strength=strength)


# --------------------------------------------------------------------------
# shared quest props
# --------------------------------------------------------------------------
def teleport_array():
    """Octagonal jade platform (~6 m) with a glowing rune ring and eight jade posts."""
    maps = jade_rune_disc(1024)
    disc = util.material("teleport_disc", maps, emission_map=maps["emit"], emission_strength=3.5,
                         normal_strength=0.6)
    stone = util.material("jade_stone", tex.stone("#7f9c90", 512, 77, 0.2), normal_strength=0.7)
    jade = util.material("jade", tex.jade("#3f9a78", 256, 42), normal_strength=0.2)
    orb = glow_mat("spirit_glow", "#8ff6ff", 5.0)
    rot = Matrix.Rotation(R(22.5), 4, "Z")
    bm = bmesh.new()
    util.lathe(bm, [(3.72, -0.1), (3.72, 0.1), (3.66, 0.16), (3.42, 0.16), (3.38, 0.2), (3.34, 0.34),
                    (3.28, 0.4), (3.0, 0.4)], segs=8, cap_bottom=True)
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    # four low stair blocks on the cardinal sides
    for k in range(4):
        a = R(90 * k)
        bevel_box(bm, (1.9, 0.55, 0.2), loc=(math.cos(a) * 3.64, math.sin(a) * 3.64, 0.1),
                  rot=Matrix.Rotation(a + R(90), 4, "Z"), bevel=0.03)
    base = obj("ArrayBase", bm, stone, uv=0.7)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((0, 0, 0.402)))
    ring = [bm.verts.new(V((3.0 * math.cos(R(45 * k + 22.5)), 3.0 * math.sin(R(45 * k + 22.5)), 0.402)))
            for k in range(8)]
    for k in range(8):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % 8]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 6.1 + 0.5, loop.vert.co.y / 6.1 + 0.5)
    top = obj("ArrayRunes", bm, disc)
    bm_p, bm_o = bmesh.new(), bmesh.new()
    for k in range(8):
        a = R(45 * k + 22.5)
        p = V((math.cos(a) * 3.08, math.sin(a) * 3.08, 0.4))
        pr = Matrix.Rotation(a, 4, "Z")
        bevel_box(bm_p, (0.26, 0.26, 0.12), loc=p + V((0, 0, 0.06)), rot=pr, bevel=0.03)
        bevel_box(bm_p, (0.18, 0.18, 0.62), loc=p + V((0, 0, 0.43)), rot=pr, bevel=0.02)
        util.cylinder(bm_p, 0.16, 0.02, 0.14, loc=p + V((0, 0, 0.81)), segs=4, rot=pr @ Matrix.Rotation(R(45), 4, "Z"))
        util.sphere(bm_o, 0.075, loc=p + V((0, 0, 0.95)), segs=10, rings=6)
    posts = obj("ArrayPosts", bm_p, jade, uv=2.0)
    orbs = obj("ArrayOrbs", bm_o, orb, smooth=True)
    bm = bmesh.new()
    util.lathe(bm, [(3.95, 0.0), (3.1, 0.42), (0.001, 0.42)], segs=8, cap_bottom=True)
    bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
    col = util.mesh_object("ArrayWalk-convcolonly", bm, None, smooth=False)
    return [base, top, posts, orbs, col]


def stone_stele():
    """Inscribed stele on a bixi tortoise, ~2.2 m tall."""
    ins = inscription(512)
    face = util.material("stele_face", ins, normal_strength=1.2)
    stone = util.material("stele_stone", tex.stone("#77786f", 512, 78, 0.25), normal_strength=1.0)
    objs = []
    bm = bmesh.new()
    bevel_box(bm, (1.25, 2.0, 0.22), loc=(0, 0.1, 0.11), bevel=0.05)
    # tortoise: domed shell, head, legs
    util.lathe(bm, [(0.58, 0.2), (0.66, 0.26), (0.64, 0.4), (0.54, 0.56), (0.32, 0.66), (0.001, 0.69)],
               segs=20, loc=(0, 0.15, 0), cap_bottom=True)
    for v in bm.verts:
        if v.co.z > 0.19 and abs(v.co.x) < 0.7 and v.co.y > -0.6:
            v.co.y = 0.15 + (v.co.y - 0.15) * 1.35
    util.tube(bm, util.catmull([V((0, -0.45, 0.32)), V((0, -0.72, 0.42)), V((0, -0.92, 0.4))], 4),
              lambda t: 0.13 + 0.04 * math.sin(t * math.pi), n=10)
    util.sphere(bm, 0.15, loc=(0, -0.98, 0.42), segs=12, rings=8, scale=(0.95, 1.2, 0.85))
    for sx in (-1, 1):
        for sy in (-0.35, 0.65):
            util.sphere(bm, 0.14, loc=(sx * 0.52, sy, 0.3), segs=10, rings=6, scale=(1.2, 1.0, 0.9))
    base = obj("SteleTortoise", bm, stone, uv=1.1, smooth=True)
    objs.append(base)
    # socket on the shell
    bm = bmesh.new()
    bevel_box(bm, (1.1, 0.46, 0.14), loc=(0, 0.15, 0.62), bevel=0.03)
    objs.append(obj("SteleSocket", bm, stone, uv=1.0))
    # the tablet with a rounded, crested top
    bm = bmesh.new()
    w, side_h, z0 = 0.92, 1.25, 0.66
    extrude_outline(bm, arc_outline(w, side_h, 12, z0), 0.15 - 0.13, 0.15 + 0.13,
                    uv_front=(-w / 2, z0, w, side_h + w / 2 * 0.55))
    slab = util.mesh_object("SteleTablet", bm, face, smooth=False)
    objs.append(slab)
    bm = bmesh.new()
    crest = arc_outline(w + 0.1, 0.0, 12, z0 + side_h - 0.04)
    extrude_outline(bm, crest, 0.15 - 0.16, 0.15 + 0.16)
    # twin dragon scrolls carved on the crest and a pearl on top
    for sx in (-1, 1):
        for face_y in (0.15 - 0.165, 0.15 + 0.165):
            scroll = [V((sx * (0.24 - 0.1 * (1 - t) * math.cos(t * 9)), face_y,
                         z0 + side_h + 0.14 + 0.1 * (1 - t) * math.sin(t * 9))) for t in np.linspace(0, 0.85, 16)]
            util.tube(bm, scroll, lambda t: 0.025 * (1 - 0.5 * t), n=6)
    util.sphere(bm, 0.07, loc=(0, 0.15, z0 + side_h + 0.3), segs=10, rings=7)
    objs.append(obj("SteleCrest", bm, stone, uv=1.2))
    objs.append(util.collider("SteleBase", (1.3, 2.1, 0.7), (0, 0.05, 0.35)))
    objs.append(util.collider("SteleTablet", (1.0, 0.36, 1.6), (0, 0.15, 1.45)))
    return objs


def treasure_chest():
    """Red lacquered chest with a vaulted lid and bronze fittings (~0.9 m)."""
    lac = util.material("chest_lacquer", tex.lacquer("#8e1a14", 512, 52, 0.15), normal_strength=0.4)
    brass = util.material("brass", tex.metal("#b88a3a", rough=0.3, patina="#556b4a", patina_amt=0.12))
    w, d, h = 0.9, 0.56, 0.4
    bm = bmesh.new()
    bevel_box(bm, (w, d, h), loc=(0, 0, h / 2 + 0.05), bevel=0.02)
    # vaulted lid: half cylinder along X
    arc = [V((0, math.cos(a) * d / 2, h + 0.05 + math.sin(a) * d * 0.32)) for a in np.linspace(0, math.pi, 12)]
    rings = [[p + V((x, 0, 0)) for p in arc] for x in (-w / 2, w / 2)]
    util.loft(bm, rings, closed=True, cap_start=True, cap_end=True)
    body = obj("ChestBody", bm, lac, uv=1.5)
    bm = bmesh.new()
    for sx in (-1, 1):
        for x in (sx * 0.3,):
            util.box(bm, (0.07, d + 0.02, h + 0.01), loc=(x, 0, h / 2 + 0.05))
            band = [V((x, math.cos(a) * (d / 2 + 0.012), h + 0.05 + math.sin(a) * (d * 0.32 + 0.012)))
                    for a in np.linspace(0, math.pi, 12)]
            util.tube(bm, band, (0.035, 0.008), n=4, power=6, up=(1, 0, 0), closed_ends=True)
        # corner caps and side handles
        for sy in (-1, 1):
            util.box(bm, (0.08, 0.08, 0.1), loc=(sx * (w / 2 - 0.03), sy * (d / 2 - 0.03), 0.1))
        ring = [V((sx * (w / 2 + 0.03), 0.09 * math.cos(a), 0.3 + 0.07 * math.sin(a)))
                for a in np.linspace(0, 2 * math.pi, 13)]
        util.tube(bm, ring, 0.012, n=6, closed_ends=False)
        util.box(bm, (0.02, 0.16, 0.08), loc=(sx * (w / 2 + 0.01), 0, 0.37))
    # lock plate and feet
    util.cylinder(bm, 0.075, 0.075, 0.02, loc=(0, -d / 2 - 0.01, h + 0.02), segs=16, rot=Matrix.Rotation(R(90), 4, "X"))
    util.box(bm, (0.05, 0.03, 0.12), loc=(0, -d / 2 - 0.02, h + 0.1))
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.cylinder(bm, 0.05, 0.04, 0.05, loc=(sx * 0.38, sy * 0.22, 0.025), segs=8)
    fit = obj("ChestFittings", bm, brass, uv=3.0)
    return [body, fit, util.collider("ChestCol", (w + 0.05, d + 0.05, 0.62), (0, 0, 0.31))]


def spirit_herb(seed=3):
    """Small luminous herb: serrated leaves around a glowing bud, ~0.5 m."""
    rnd = random.Random(seed)
    lc = leaf_cards(256, 512, "#3f8a4a", "fern")
    leaf = clip_alpha(util.material("herb_leaf", lc, alpha=lc["alpha"], double_sided=True, normal_strength=0.4,
                                    emission="#1f6a4a", emission_strength=0.25))
    bud = glow_mat("herb_glow", "#b8fff0", 4.0)
    soil = util.material("herb_soil", earth("#4d3d2a", 256, 422, 0.3), normal_strength=0.6)
    bm_l = bmesh.new()
    uv = bm_l.loops.layers.uv.verify()
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), 0))
        side = V((-d.y, d.x, 0))
        ln = rnd.uniform(0.28, 0.38)
        rows = 6
        verts = []
        for j in range(rows + 1):
            t = j / rows
            p = d * (0.02 + ln * t) + V((0, 0, 0.04 + 0.22 * math.sin(t * 2.2) * (1 - 0.3 * t)))
            wd = 0.07
            verts.append((bm_l.verts.new(p - side * wd), bm_l.verts.new(p + side * wd)))
        for j in range(rows):
            f = bm_l.faces.new((verts[j][0], verts[j][1], verts[j + 1][1], verts[j + 1][0]))
            quad = ((0.3, j / rows), (0.7, j / rows), (0.7, (j + 1) / rows), (0.3, (j + 1) / rows))
            for loop, (uu, vv) in zip(f.loops, quad):
                loop[uv].uv = (uu, vv)
    leaves = util.mesh_object("HerbLeaves", bm_l, leaf, smooth=True)
    bm_s, bm_b = bmesh.new(), bmesh.new()
    stem = [V((0, 0, 0)), V((0.02, 0.01, 0.2)), V((-0.01, 0.0, 0.38))]
    util.tube(bm_s, util.catmull(stem, 4), lambda t: 0.012 * (1 - 0.5 * t), n=6)
    util.lathe(bm_b, [(0.001, 0.36), (0.04, 0.38), (0.055, 0.43), (0.04, 0.48), (0.001, 0.52)], segs=10)
    for k in range(5):
        a = 2 * math.pi * k / 5
        p = V((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.2 + 0.03 * (k % 2)))
        util.tube(bm_s, [V((0, 0, 0.1)), p * 0.6 + V((0, 0, 0.08)), p], 0.005, n=4)
        util.sphere(bm_b, 0.022, loc=p + V((0, 0, 0.015)), segs=8, rings=5)
    rock(bm_s, (0, 0, -0.02), (0.16, 0.16, 0.06), 3.0, 0.3, 2)
    stems = obj("HerbStems", bm_s, soil, uv=4.0, smooth=True)
    buds = obj("HerbBud", bm_b, bud, smooth=True)
    return [leaves, stems, buds]


def spirit_stone(seed=5):
    """Faceted glowing crystal cluster on a rock (~0.6 m)."""
    rnd = random.Random(seed)
    crystal = util.material("spirit_crystal", tex.jade("#4fd8ff", 256, 43), normal_strength=0.3,
                            emission="#39c8ff", emission_strength=2.2)
    stone = util.material("rock", tex.stone("#8e8a82", 512, 75), normal_strength=1.2)
    bm = bmesh.new()
    specs = [(0, 0, 0.55, 0.09, 0, 0)] + [(rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12),
                                           rnd.uniform(0.2, 0.4), rnd.uniform(0.04, 0.07),
                                           rnd.uniform(0.3, 0.7), rnd.uniform(0, 2 * math.pi)) for _ in range(7)]
    for (x, y, h, r, tilt, az) in specs:
        tmp = util.lathe(bm, [(r, 0), (r, h * 0.75), (r * 0.6, h * 0.9), (0.001, h)], segs=6, cap_bottom=True)
        m = (Matrix.Translation(V((x, y, 0.06))) @ Matrix.Rotation(az, 4, "Z") @ Matrix.Rotation(tilt, 4, "X"))
        bmesh.ops.transform(bm, matrix=m, verts=[v for row in tmp for v in row])
    cr = obj("SpiritCrystals", bm, crystal, uv=3.0)
    bm = bmesh.new()
    rock(bm, (0, 0, 0.04), (0.26, 0.22, 0.12), 5.0, 0.35, 2)
    base = obj("CrystalRock", bm, stone, uv=1.5, smooth=True)
    return [cr, base, util.collider("CrystalCol", (0.5, 0.5, 0.45), (0, 0, 0.22))]


def jade_slip():
    """A bundle of jade slips bound with red cord, half unrolled (~0.4 m)."""
    s = 512
    base = tex.jade("#8fcfa8", s, 44)
    m = glyph_mask(s, 10, 12, 91, (0.02, 0.05, 0.98, 0.95), 0.006)
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#1f4a34"), m * 0.85)
    base["height"] = base["height"] - m * 0.4
    jade = util.material("jade_slip", base, normal_strength=0.6, emission_map=np.clip(
        m[..., None] * tex.srgb("#5fffc0")[None, None, :] * 0.6, 0, 1), emission_strength=1.2)
    cord = util.material("tassel_red", tex.silk("#b3213a", "#d24a5e", 128, 9))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    n_flat, sw, sl, th = 10, 0.028, 0.3, 0.008
    for k in range(n_flat):
        x = -0.05 + k * (sw + 0.003)
        vs = util.box(bm, (sw, sl, th), loc=(x, 0, th / 2 + 0.002))
        faces = {f for v in vs for f in v.link_faces}
        for f in faces:
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = ((k + 0.5 + (co.x - x) / sw * 0.9) / n_flat, (co.y + sl / 2) / sl)
    # the rolled part: slips wound around a spiral
    for k in range(16):
        a = k * 0.62
        rr = 0.07 - k * 0.003
        c = V((-0.09 - rr * math.sin(a) * 0.9, 0, 0.07 + rr * math.cos(a)))
        rot = Matrix.Rotation(-a, 4, "Y")
        vs = util.box(bm, (sw, sl, th), loc=c, rot=rot)
        faces = {f for v in vs for f in v.link_faces}
        for f in faces:
            for loop in f.loops:
                loop[uv].uv = (0.97, (loop.vert.co.y + sl / 2) / sl * 0.2)
    slips = util.mesh_object("JadeSlips", bm, jade, smooth=False)
    bm = bmesh.new()
    for y in (-0.08, 0.08):
        path = [V((0.25, y, 0.004)), V((-0.02, y, 0.012))]
        path += [V((-0.09 - 0.08 * math.sin(a), y, 0.07 + 0.08 * math.cos(a))) for a in np.linspace(0.3, 2 * math.pi,
                                                                                                    16)]
        util.tube(bm, path, 0.004, n=5)
    util.tube(bm, util.catmull([V((-0.09, 0.08, 0.15)), V((-0.12, 0.2, 0.1)), V((-0.08, 0.26, 0.01))], 4), 0.004, n=5)
    util.cylinder(bm, 0.012, 0.004, 0.06, loc=(-0.07, 0.28, 0.01), segs=8, rot=Matrix.Rotation(R(90), 4, "X"))
    cords = obj("SlipCord", bm, cord, uv=4.0, smooth=True)
    return [slips, cords]


def bronze_bell():
    """A bianzhong bronze bell hung in a small lacquered frame (~2.4 m)."""
    m = kit()
    bronze = util.material("bell_bronze", tex.metal("#7c6035", rough=0.32, patina="#3f7a66", patina_amt=0.3),
                           normal_strength=0.7)
    objs = []
    black = util.material("black_lacquer", tex.lacquer("#1e1714", 512, 53, 0.15), normal_strength=0.3)
    bm_w, bm_s, bm_g = bmesh.new(), bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        x = sx * 0.95
        bevel_box(bm_s, (0.56, 0.8, 0.22), loc=(x, 0, 0.11), bevel=0.05)
        bevel_box(bm_s, (0.4, 0.6, 0.2), loc=(x, 0, 0.31), bevel=0.04)
        bevel_box(bm_w, (0.17, 0.17, 2.05), loc=(x, 0, 1.4), bevel=0.02)
        for sy in (-1, 1):
            util.tube(bm_w, [V((x, sy * 0.36, 0.38)), V((x, sy * 0.06, 1.05))], (0.05, 0.05), n=4, power=6)
        util.tube(bm_w, [V((x - sx * 0.06, 0, 1.85)), V((x - sx * 0.45, 0, 2.3))], (0.045, 0.045), n=4, power=6)
        # gilt dragon-head cap on the post and a crouching beast base
        curl = [V((x + sx * 0.12 * math.sin(a), 0, 2.55 + 0.14 * (1 - math.cos(a)))) for a in np.linspace(0, R(300),
                                                                                                          14)]
        util.tube(bm_g, curl, lambda t: 0.07 * (1 - 0.6 * t), n=8)
        util.cylinder(bm_g, 0.13, 0.12, 0.06, loc=(x, 0, 2.53), segs=8)
        util.sphere(bm_s, 0.22, loc=(x, -0.3, 0.52), segs=10, rings=7, scale=(1.0, 1.1, 0.9))
    bevel_box(bm_w, (2.12, 0.22, 0.24), loc=(0, 0, 2.41), bevel=0.03)
    for x in np.linspace(-0.8, 0.8, 5):
        util.sphere(bm_g, 0.04, loc=(x, -0.12, 2.41), segs=8, rings=5)
    frame = obj("BellFrame", bm_w, black, uv=1.2)
    stones = obj("BellFrameStones", bm_s, m["stone"], uv=1.0)
    objs += [frame, stones, obj("BellFrameGilt", bm_g, m["gold"], uv=2.0)]
    # the bell: lens-shaped section, arched mouth, bosses, hanging shank
    bm = bmesh.new()
    rings = []
    top, bot = 1.78, 1.0
    for j in range(9):
        t = j / 8
        z = top - (top - bot) * t
        rx = 0.2 + 0.1 * t ** 0.9
        ry = 0.14 + 0.06 * t
        ring = util.ring((0, 0, z), (1, 0, 0), (0, 1, 0), rx, ry, 24, power=1.6)
        if j == 8:
            ring = [p + V((0, 0, 0.09 * math.sin(math.atan2(p.y / ry, p.x / rx)) ** 2)) for p in ring]
        rings.append(ring)
    util.loft(bm, rings, closed=True, cap_start=True)
    inner = [[p * 0.94 + V((0, 0, (1 - 0.94) * p.z + 0.06)) for p in rings[-1]],
             [p * 0.85 + V((0, 0, 0.35 * (1 - 0.85) + 0.3)) for p in rings[-1]]]
    util.loft(bm, [rings[-1], inner[0]], closed=True)
    util.loft(bm, inner, closed=True, cap_end=True)
    for side in (-1, 1):
        for gx in (-1, 1):
            for r in range(3):
                for c in range(3):
                    t = 0.2 + 0.2 * r
                    z = top - (top - bot) * t
                    x = gx * (0.1 + 0.05 * c) * (1 + 0.5 * t)
                    ry = (0.14 + 0.06 * t) * math.sqrt(max(0.0, 1 - (abs(x) / (0.2 + 0.1 * t)) ** 1.6)) ** 1.0
                    util.cylinder(bm, 0.018, 0.004, 0.05, loc=(x, side * (ry + 0.015), z), segs=6,
                                  rot=Matrix.Rotation(R(-90 * side), 4, "X"))
    util.cylinder(bm, 0.05, 0.06, 0.28, loc=(0, 0, top + 0.14), segs=10)
    util.tube(bm, [V((0, 0, top + 0.26)), V((0, 0, 2.3))], 0.018, n=6)
    ring = [V((0.06 * math.cos(a), 0, 2.22 + 0.06 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 13)]
    util.tube(bm, ring, 0.014, n=6, closed_ends=False)
    bell = obj("BronzeBell", bm, bronze, uv=2.5, smooth=True)
    objs.append(bell)
    # striking beam hanging on ropes
    bm = bmesh.new()
    util.cylinder(bm, 0.05, 0.05, 0.9, loc=(0.0, -0.55, 1.35), segs=10, rot=Matrix.Rotation(R(90), 4, "Y"))
    objs.append(obj("BellStriker", bm, m["wood"], uv=1.5, smooth=True))
    bm = bmesh.new()
    for x in (-0.35, 0.35):
        util.tube(bm, [V((x, -0.55, 1.38)), V((x, -0.1, 2.3))], 0.008, n=4)
    objs.append(obj("BellRopes", bm, util.material("rope", tex.bark("#9b855c", 128, 135), normal_strength=0.4), uv=4.0))
    for sx in (-1, 1):
        objs.append(util.collider("BellPost", (0.5, 0.7, 2.4), (sx * 0.95, 0, 1.2)))
    objs.append(util.collider("BellBody", (0.65, 0.45, 0.9), (0, 0, 1.4)))
    return objs


# --------------------------------------------------------------------------
# terrain helpers
# --------------------------------------------------------------------------
def dirt_patch(size=512, seed=571, color="#a08866"):
    """Round dirt patch with a ragged grassy rim (planar UV 0..1, alpha)."""
    base = earth(color, size, seed, 0.5)
    u, v = tex.grid(size)
    r = np.hypot(u - 0.5, v - 0.5) * 2
    n = tex.fbm(size, 6, 4, 0.5, seed + 1)
    d = 1 - r + (n - 0.5) * 0.55
    out = tex.result(tex.lerp(base["albedo"], tex.srgb("#6b6440"), 1 - tex.sstep(0.05, 0.3, d)),
                     base["rough"], 0.0, base["height"])
    out["alpha"] = tex.sstep(0.02, 0.06, d)
    return out


def culm(size=256, seed=581):
    """Bamboo culm: green with fine vertical fibres (v along the stalk)."""
    fib = tex.fbm(size, 64, 3, 0.5, seed, stretch=16)
    n = tex.fbm(size, 4, 4, 0.5, seed + 1, stretch=4)
    col = tex.lerp(tex.srgb("#4f6b2a"), tex.srgb("#8ba54c"), n * 0.7 + fib * 0.3)
    col = tex.lerp(col, tex.srgb("#b7aa62"), tex.sstep(0.75, 0.95, n) * 0.4)
    return tex.result(col, 0.45 + 0.2 * fib, 0.0, fib * 0.3)


def end_grain(size=256, seed=591, color="#9a7a52"):
    u, v = tex.grid(size)
    r = np.hypot(u - 0.5, v - 0.5)
    n = tex.fbm(size, 6, 3, 0.5, seed)
    rings = np.sin((r * 28 + n * 1.5) * 2 * math.pi) * 0.5 + 0.5
    col = tex.srgb(color) * (0.7 + 0.3 * rings)[..., None]
    col = tex.lerp(col, tex.srgb("#3a2a1c"), tex.sstep(0.44, 0.5, r))
    return tex.result(col, 0.8, 0.0, rings * 0.4)


def triplanar(co, nrm, scale):
    """Planar UV along the dominant axis of the face normal."""
    ax = max(range(3), key=lambda k: abs(nrm[k]))
    if ax == 2:
        return (co.x * scale, co.y * scale)
    if ax == 0:
        return (co.y * scale, co.z * scale)
    return (co.x * scale, co.z * scale)


def terrain_grid(name, height_fn, span, step, mats, classify, uv_fn):
    """Square height-field mesh in Blender space (Godot z = -Y)."""
    n = int(round(span * 2 / step))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    rows = []
    for j in range(n + 1):
        y = -span + j * step
        rows.append([bm.verts.new(V((-span + i * step, y, height_fn(-span + i * step, -y)))) for i in range(n + 1)])
    for j in range(n):
        for i in range(n):
            a, b, c, d = rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]
            # split along the flatter diagonal
            if abs(a.co.z - c.co.z) > abs(b.co.z - d.co.z):
                tris = ((a, b, d), (b, c, d))
            else:
                tris = ((a, b, c), (a, c, d))
            for tri in tris:
                f = bm.faces.new(tri)
                f.normal_update()
                cen = (tri[0].co + tri[1].co + tri[2].co) / 3
                f.material_index = classify(cen.x, -cen.y, cen.z, f.normal)
                for loop in f.loops:
                    loop[uv].uv = uv_fn(loop.vert.co, f.material_index, f.normal)
    return util.mesh_object(name, bm, mats, smooth=True)


def ribbon(name, pts, width, height_fn, mat, lift=0.06, keep=None, taper=3.0, cols=4, tile=None):
    """Strip following a Godot-space poly-line over the ground (u across, v along)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    # resample at ~1 m
    dense = [pts[0]]
    for (x0, z0), (x1, z1) in zip(pts[:-1], pts[1:]):
        k = max(1, int(math.hypot(x1 - x0, z1 - z0) / 1.0))
        dense += [(x0 + (x1 - x0) * t / k, z0 + (z1 - z0) * t / k) for t in range(1, k + 1)]
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(dense[:-1], dense[1:]))
    prev, prev_d, dist = None, 0.0, 0.0
    for idx, (x, z) in enumerate(dense):
        if idx:
            dist += math.hypot(x - dense[idx - 1][0], z - dense[idx - 1][1])
        ok = keep is None or keep(x, z)
        if not ok:
            prev = None
            continue
        a = dense[max(idx - 1, 0)]
        b = dense[min(idx + 1, len(dense) - 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / ln, tx / ln
        w = width if not taper else width * min(1.0, 0.35 + 0.65 * min(dist, total - dist) / taper)
        row = []
        for c in range(cols + 1):
            s = c / cols - 0.5
            px, pz = x + nx * w * s, z + nz * w * s
            row.append(bm.verts.new(V((px, -pz, height_fn(px, pz) + lift))))
        if prev is not None:
            for c in range(cols):
                f = bm.faces.new((prev[c], prev[c + 1], row[c + 1], row[c]))
                for loop, (uu, vv) in zip(f.loops, ((c, prev_d), (c + 1, prev_d), (c + 1, dist), (c, dist))):
                    loop[uv].uv = ((uu / cols, vv / width) if tile is None else (uu / cols * width / tile, vv / tile))
        prev, prev_d = row, dist
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    return util.mesh_object(name, bm, mat, smooth=True)


def disc_patch(name, cx, cz, radius, height_fn, mat, lift=0.05, rings=8, drop=None, uv_scale=None):
    """Ground-hugging disc (planar UVs 0..1 over its diameter). drop(i, j) removes faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    grid = []
    n = rings * 2
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            x = cx - radius + 2 * radius * i / n
            z = cz - radius + 2 * radius * j / n
            row.append(bm.verts.new(V((x, -z, height_fn(x, z) + lift))))
        grid.append(row)
    for j in range(n):
        for i in range(n):
            fx = (i + 0.5) / n * 2 - 1
            fz = (j + 0.5) / n * 2 - 1
            if fx * fx + fz * fz > 1.05 or (drop and drop(i, j)):
                continue
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.normal_update()
            if f.normal.z < 0:
                f.normal_flip()
            for loop in f.loops:
                co = loop.vert.co
                if uv_scale:
                    loop[uv].uv = (co.x * uv_scale, co.y * uv_scale)
                else:
                    loop[uv].uv = ((co.x - cx + radius) / (2 * radius), (-co.y - cz + radius) / (2 * radius))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    return util.mesh_object(name, bm, mat, smooth=True)


def bounds_colliders(hx, hz, height=90.0, base=-30.0, thick=4.0):
    objs = []
    for sx in (-1, 1):
        objs.append(util.collider("BoundX", (thick, hz * 2 + thick * 2, height), (sx * (hx + thick / 2), 0,
                                                                                  base + height / 2),
                                  convex=False))
    for sz in (-1, 1):
        objs.append(util.collider("BoundZ", (hx * 2 + thick * 2, thick, height), (0, sz * (hz + thick / 2),
                                                                                  base + height / 2),
                                  convex=False))
    return objs


# --------------------------------------------------------------------------
# forest
# --------------------------------------------------------------------------
def forest_terrain():
    """Bamboo valley: rolling floor, winding paths, a stream bed and steep valley walls."""
    from maps import bamboo_forest as F
    m = {}
    m["floor"] = util.material("forest_floor", forest_floor(1024), normal_strength=0.8)
    m["cliff"] = util.material("crag", crag("#77746a", 512), normal_strength=1.0)
    m["bed"] = util.material("pebbles", pebbles(512), normal_strength=1.2)
    m["moss"] = util.material("moss_floor", tex.foliage("#3d5a2a", 512, 145), normal_strength=0.6)
    ps = path_strip(512)
    m["path"] = clip_alpha(util.material("forest_path", ps, alpha=ps["alpha"], normal_strength=0.3))
    dp = dirt_patch(512)
    m["dirt"] = clip_alpha(util.material("dirt_patch", dp, alpha=dp["alpha"], normal_strength=0.3))
    m["paving"] = util.material("old_paving", tex.paving("#a09a8a", 512, 82, tiles=4, gap=0.01, moss=0.45),
                                normal_strength=1.0)
    m["water"] = util.material("stream_water", tex.water(256), alpha=0.78, normal_strength=0.6)

    def classify(x, z, h, nrm):
        if nrm.z < 0.74:
            return 1
        if F.boundary(x, z) > 3:
            return 3
        if F.STREAM.distance(x, z, 4.0)[0] < 3.4 and h < F.stream_level(x) + 0.3:
            return 2
        return 0

    def uv_fn(co, mi, nrm):
        if mi == 1:
            return triplanar(co, nrm, 0.06)
        if mi == 2:
            return (co.x * 0.25, co.y * 0.25)
        return (co.x * 0.1, co.y * 0.1)
    ground = terrain_grid("Ground-col", F.height, F.SPAN, 1.6, [m["floor"], m["cliff"], m["bed"], m["moss"]],
                          classify, uv_fn)
    objs = [ground]

    def keep(x, z):
        return F.boundary(x, z) < 1.0 and F.STREAM.distance(x, z, 8.0)[0] > 5.8
    for name, p in F.PATHS.items():
        objs.append(ribbon("Path_" + name, p.pts, p.width, F.height, m["path"], keep=keep))
    for (x, z, r) in (F.ZONES["camp"], F.ZONES["clearing"], F.ZONES["hermit"], F.ZONES["teleport"]):
        objs.append(disc_patch("Dirt", x, z, r * 0.75, F.height, m["dirt"], lift=0.04))
    rnd = random.Random(5)
    cx, cz, r = F.ZONES["ruins_inner"]
    objs.append(disc_patch("RuinsPaving", cx, cz, r + 1, F.height, m["paving"], lift=0.07, rings=18,
                           drop=lambda i, j: rnd.random() < 0.1, uv_scale=0.22))
    objs.append(ribbon("StreamWater", F.STREAM.pts, 9.5, lambda x, z: F.stream_level(x) - 0.1, m["water"], lift=0.0,
                       taper=None, cols=2))
    objs += bounds_colliders(F.PLAY_X + 14, F.PLAY_Z + 14)
    return objs


def spring_pool():
    """Glowing spirit-spring water disc (sits in the forest terrain's pool hollow)."""
    s = 512
    base = tex.water(s, 162)
    u, v = tex.grid(s)
    swirl = tex.fbm(s, 6, 4, 0.5, 163)
    caust = tex.sstep(0.55, 0.62, np.abs(np.sin(swirl * 18)))
    base["albedo"] = tex.lerp(base["albedo"], tex.srgb("#4fe0c8"), 0.35 + caust * 0.3)
    emit = np.clip((0.25 + caust * 0.75)[..., None] * tex.srgb("#3fe8d0")[None, None, :], 0, 1)
    mat = util.material("spirit_water", base, alpha=0.8, emission_map=emit, emission_strength=0.55,
                        normal_strength=0.5)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((0, 0, 0)))
    n = 40
    ring = [bm.verts.new(V((7.6 * math.cos(2 * math.pi * k / n), 7.6 * math.sin(2 * math.pi * k / n),
                            0))) for k in range(n)]
    for k in range(n):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % n]))
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x / 7.0, loop.vert.co.y / 7.0)
    return [util.mesh_object("SpringWater", bm, mat, smooth=False)]


def bamboo_grove(seed=13, count=18, radius=3.4):
    """A stand of tall bamboo (10-14 m) with drooping leaf sprays; each culm collides."""
    rnd = random.Random(seed)
    stalk = util.material("bamboo_culm", culm(256), normal_strength=0.3)
    lc = leaf_cards(512, 512, "#6f9f45", "bamboo")
    leaf = clip_alpha(util.material("bamboo_sprays", lc, alpha=lc["alpha"], double_sided=True, normal_strength=0.3))
    bm_s, bm_l = bmesh.new(), bmesh.new()
    uvl = bm_l.loops.layers.uv.verify()
    objs = []
    for i in range(count):
        a = rnd.uniform(0, 2 * math.pi)
        r = radius * math.sqrt(rnd.random())
        base = V((math.cos(a) * r, math.sin(a) * r, -0.2))
        h = rnd.uniform(9.5, 14.0)
        out = (V((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.6, 1.8)
               + V((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0)))
        path = [base + out * (t ** 1.8) + V((0, 0, h * t)) for t in np.linspace(0, 1, 9)]
        rad = rnd.uniform(0.045, 0.085)
        util.tube(bm_s, path, lambda t, rad=rad: rad * (1 - 0.55 * t), n=6, uv_scale=(1, 0.35))
        for k in range(1, 8):
            p = path[k]
            util.cylinder(bm_s, rad * (1.12 - 0.55 * k / 8), rad * (1.12 - 0.55 * k / 8), 0.05, loc=p, segs=6)
        objs.append(util.collider("Culm", (0.2, 0.2, 3.0), (base.x, base.y, 1.3)))
        for k in range(3, 9):
            p = path[k]
            for _ in range(3 if k > 4 else 2):
                ang = rnd.uniform(0, 2 * math.pi)
                d = V((math.cos(ang), math.sin(ang), 0))
                side = V((-d.y, d.x, 0))
                wd, ln = rnd.uniform(1.3, 1.9), rnd.uniform(1.8, 2.6)
                droop = rnd.uniform(0.3, 0.8)
                rows = []
                for j in range(4):
                    t = j / 3
                    c = p + d * (0.05 + ln * t) + V((0, 0, 0.35 - droop * t * t * 2.0))
                    rows.append((bm_l.verts.new(c - side * wd * (0.3 + 0.7 * t) / 2),
                                 bm_l.verts.new(c + side * wd * (0.3 + 0.7 * t) / 2)))
                for j in range(3):
                    f = bm_l.faces.new((rows[j][0], rows[j][1], rows[j + 1][1], rows[j + 1][0]))
                    quad = ((0, 1 - j / 3), (1, 1 - j / 3), (1, 1 - (j + 1) / 3), (0, 1 - (j + 1) / 3))
                    for loop, (uu, vv) in zip(f.loops, quad):
                        loop[uvl].uv = (uu, vv)
    objs.insert(0, util.mesh_object("BambooCulms", bm_s, stalk, smooth=True))
    objs.insert(1, util.mesh_object("BambooSprays", bm_l, leaf, smooth=True))
    return objs


def fern_cluster(seed=17, fronds=9):
    """Arching fern fronds (alpha-clipped cards), ~1.4 m across."""
    rnd = random.Random(seed)
    lc = leaf_cards(512, 513, "#4f8a36", "fern")
    mat = clip_alpha(util.material("fern_frond", lc, alpha=lc["alpha"], double_sided=True, normal_strength=0.4))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + rnd.uniform(-0.3, 0.3)
        d = V((math.cos(a), math.sin(a), 0))
        side = V((-d.y, d.x, 0))
        ln = rnd.uniform(0.7, 1.1)
        lift = rnd.uniform(0.35, 0.6)
        rows = []
        for j in range(6):
            t = j / 5
            c = d * ln * t + V((0, 0, lift * math.sin(t * math.pi * 0.75) + 0.02))
            w = 0.26 + 0.1 * math.sin(t * math.pi)
            tilt = V((0, 0, 0.08 * t))
            rows.append((bm.verts.new(c - side * w + tilt), bm.verts.new(c + side * w + tilt)))
        for j in range(5):
            f = bm.faces.new((rows[j][0], rows[j][1], rows[j + 1][1], rows[j + 1][0]))
            for loop, (uu, vv) in zip(f.loops, ((0, j / 5), (1, j / 5), (1, (j + 1) / 5), (0, (j + 1) / 5))):
                loop[uv].uv = (uu, vv)
    return [util.mesh_object("FernFronds", bm, mat, smooth=True)]


def fallen_log(seed=19):
    """Mossy fallen trunk (~6 m) with a root plate, stubs and bracket fungi."""
    rnd = random.Random(seed)
    m = kit()
    ends = util.material("log_end", end_grain(256), normal_strength=0.5)
    fungus = util.material("fungus", tex.stone("#c8b48a", 256, 79, 0.1), normal_strength=0.3)
    bm = bmesh.new()
    path = [V((-3.0 + 6.0 * t, 0.1 * math.sin(t * 5), 0.42 + 0.06 * math.sin(t * 3))) for t in np.linspace(0, 1, 10)]
    util.tube(bm, path, lambda t: 0.44 - 0.1 * t, n=14, closed_ends=False, uv_scale=(2, 0.5))
    for k in range(2):
        x = rnd.uniform(-1.5, 1.8)
        util.tube(bm, [V((x, 0, 0.7)), V((x + 0.2, 0.25, 1.05)), V((x + 0.3, 0.35, 1.2))],
                  lambda t: 0.12 * (1 - 0.5 * t), n=8)
    for k in range(10):
        a = 2 * math.pi * k / 10 + rnd.uniform(-0.2, 0.2)
        d = V((0, math.cos(a), math.sin(a)))
        ln = rnd.uniform(0.7, 1.2)
        pts = [V((-2.85, 0, 0.42)) + d * 0.3, V((-3.05, 0, 0.42)) + d * (0.35 + ln * 0.5),
               V((-3.1 + rnd.uniform(-0.2, 0.2), 0, 0.42)) + d * (0.4 + ln) + V((0, 0, -0.25))]
        util.tube(bm, util.catmull(pts, 3), lambda t: 0.09 * (1 - 0.7 * t), n=6)
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.4
        rock(bm, (-3.05, math.cos(a) * 0.5, 0.42 + math.sin(a) * 0.5), (0.25, 0.3, 0.3), k + 70, 0.4, 1)
    log = obj("LogBark", bm, m["log"], smooth=True)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    end = path[-1]
    rr = 0.34
    c = bm.verts.new(end + V((0.01, 0, 0)))
    ring = [bm.verts.new(end + V((0.01, rr * math.cos(2 * math.pi * k / 14), rr * math.sin(2 * math.pi * k / 14))))
            for k in range(14)]
    for k in range(14):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % 14]))
        for loop in f.loops:
            co = loop.vert.co - end
            loop[uv].uv = (co.y / (2 * rr) + 0.5, co.z / (2 * rr) + 0.5)
    cap = util.mesh_object("LogEnd", bm, ends, smooth=False)
    bm = bmesh.new()
    for k in range(6):
        x = -2.4 + k * 0.95
        rock(bm, (x, rnd.uniform(-0.1, 0.1), 0.78 - 0.02 * k), (0.55, 0.3, 0.1), k + seed, 0.35, 1)
    moss = obj("LogMoss", bm, m["moss"], uv=1.0, smooth=True)
    bm = bmesh.new()
    for k in range(5):
        x = rnd.uniform(-2, 2.5)
        sgn = rnd.choice((-1, 1))
        util.cylinder(bm, 0.12, 0.1, 0.035, loc=(x, sgn * 0.42, 0.3 + rnd.uniform(0, 0.2)), segs=10)
    fung = obj("LogFungus", bm, fungus, uv=2.0)
    col = util.collider("LogCol", (6.4, 0.85, 0.85), (0, 0, 0.42))
    return [log, cap, moss, fung, col]


def broken_pillar(seed=29):
    """Toppled ruin column: plinth, jagged broken shaft and a fallen drum."""
    rnd = random.Random(seed)
    m = kit()
    bm = bmesh.new()
    bevel_box(bm, (1.2, 1.2, 0.3), loc=(0, 0, 0.15), bevel=0.05)
    util.lathe(bm, [(0.52, 0.3), (0.5, 0.38), (0.44, 0.42), (0.4, 0.48)], segs=16, cap_top=True)
    top = 1.6 + rnd.uniform(0, 0.6)
    prof = [(0.38, 0.48 + (top - 0.48) * t) for t in np.linspace(0, 1, 7)]
    rows = util.lathe(bm, prof, segs=16)
    for v in rows[-1]:
        v.co.z -= rnd.uniform(0, 0.45)
    for v in rows[-2]:
        v.co.z -= rnd.uniform(0, 0.15)
    f = bm.faces.new(rows[-1])
    f.normal_update()
    if f.normal.z < 0:
        f.normal_flip()
    for k in range(16):
        rows[3][k].co.x *= 1 + rnd.uniform(-0.03, 0.03)
    shaft = obj("PillarShaft", bm, m["ruin"], uv=0.8)
    bm = bmesh.new()
    util.cylinder(bm, 0.37, 0.37, 0.9, loc=(1.25, 0.6, 0.37), segs=16,
                  rot=Matrix.Rotation(R(90), 4, "Y") @ Matrix.Rotation(R(15), 4, "X"))
    for k in range(4):
        rock(bm, (rnd.uniform(-1, 1), rnd.uniform(-1.1, -0.6), 0.05), (0.18, 0.15, 0.12), k + seed, 0.4, 1)
    drum = obj("PillarDrum", bm, m["ruin"], uv=0.8)
    bm = bmesh.new()
    rock(bm, (-0.2, 0.3, 0.3), (0.5, 0.4, 0.08), seed, 0.4, 1)
    moss = obj("PillarMoss", bm, m["moss"], uv=1.0, smooth=True)
    return [shaft, drum, moss, util.collider("PillarCol", (0.8, 0.8, top), (0, 0, top / 2)),
            util.collider("DrumCol", (0.9, 0.75, 0.75), (1.25, 0.6, 0.37), rot_z=R(15))]


def ruin_wall(seed=37, length=6.0):
    """Crumbling ashlar wall segment (along X) with a breach and fallen blocks."""
    rnd = random.Random(seed)
    m = kit()
    bm = bmesh.new()
    course = 0.46

    def top(x):
        t = (x + length / 2) / length
        return 2.5 + 0.3 * math.sin(t * 7 + seed) - 1.9 * math.exp(-((t - 0.62) / 0.12) ** 2)
    for c in range(6):
        z = c * course
        x = -length / 2 + (0.45 if c % 2 else 0.0)
        while x < length / 2 - 0.1:
            ln = min(rnd.uniform(0.8, 1.35), length / 2 - x)
            mid = x + ln / 2
            if z + course <= top(mid) + 0.2 and not (c > 0 and rnd.random() < 0.08):
                jit = V((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.05, 0.05), 0))
                bevel_box(bm, (ln - 0.04, 0.78, course - 0.03), loc=V((mid, 0, z + course / 2)) + jit,
                          rot=Matrix.Rotation(rnd.uniform(-0.03, 0.03), 4, "Z"), bevel=0.04)
            x += ln
    for k in range(5):
        x = rnd.uniform(-0.5, 2.5)
        bevel_box(bm, (rnd.uniform(0.6, 1.0), 0.7, 0.42), loc=(x, rnd.choice((-1, 1)) * rnd.uniform(0.9, 1.6), 0.18),
                  rot=Matrix.Rotation(rnd.uniform(0, 3), 4, "Z") @ Matrix.Rotation(rnd.uniform(-0.3, 0.3), 4, "X"),
                  bevel=0.05)
    wall = obj("RuinWall", bm, m["blocks"], uv=0.55)
    bm = bmesh.new()
    for k in range(4):
        x = -length / 2 + 0.8 + k * 1.3
        if top(x) > 1.4:
            rock(bm, (x, 0, top(x) - 0.1), (0.5, 0.42, 0.1), seed + k, 0.4, 1)
    moss = obj("RuinWallMoss", bm, m["moss"], uv=1.0, smooth=True)
    objs = [wall, moss]
    for k in range(6):
        x0 = -length / 2 + k * length / 6
        h = min(top(x0 + 0.1), top(x0 + length / 12), top(x0 + length / 6 - 0.1))
        h = max(0.4, (math.floor(h / course)) * course)
        objs.append(util.collider("RuinWallCol", (length / 6, 0.8, h), (x0 + length / 12, 0, h / 2)))
    return objs


def stone_archway():
    """Ancient ruins gate: two carved pillars, a lintel broken at one end, eave stones."""
    m = kit()
    rnd = random.Random(41)
    plaque = util.material("ruin_plaque", signboard(512, 562, 3, "#4b4f45", "#8e8a6a", vertical=False),
                           normal_strength=0.6)
    objs = []
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * 2.65
        bevel_box(bm, (1.4, 1.4, 0.5), loc=(x, 0, 0.25), bevel=0.06)
        bevel_box(bm, (1.15, 1.15, 0.25), loc=(x, 0, 0.62), bevel=0.04)
        bevel_box(bm, (0.9, 0.9, 3.7), loc=(x, 0, 2.6), bevel=0.05)
        bevel_box(bm, (1.12, 1.12, 0.3), loc=(x, 0, 4.6), bevel=0.05)
        for sy in (-1, 1):
            bevel_box(bm, (0.5, 0.06, 2.6), loc=(x, sy * 0.46, 2.5), bevel=0.02)
    # lintel, broken on the east end
    bevel_box(bm, (5.8, 0.85, 0.75), loc=(-0.5, 0, 5.12), bevel=0.06)
    bevel_box(bm, (6.8, 0.6, 0.3), loc=(0, 0, 4.72), bevel=0.04)
    bevel_box(bm, (1.9, 0.8, 0.7), loc=(3.75, 1.3, 0.34), rot=Matrix.Rotation(R(18), 4, "Z") @ Matrix.Rotation(R(-8),
                                                                                                               4, "Y"),
              bevel=0.06)
    for k in range(9):
        rock(bm, (rnd.uniform(2.6, 5.0), rnd.uniform(-0.8, 2.4), 0.08), (0.28, 0.24, 0.18), k, 0.4, 1)
    stone = obj("ArchStone", bm, m["ruin"], uv=0.6)
    objs.append(stone)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(V(p)) for p in ((-1.4, -0.44, 4.85), (0.6, -0.44, 4.85), (0.6, -0.44, 5.4), (-1.4, -0.44, 5.4))]
    f = bm.faces.new(vs)
    for loop, (uu, vv) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = (uu, vv)
    objs.append(util.mesh_object("ArchPlaque", bm, plaque, smooth=False))
    rm = {"tiles": m["ruin"], "wood": m["ruin"], "ridge": m["ruin"], "gold": m["ruin"]}
    roof = arch.rect_roof("ArchEave", -0.5, 0, 3.3, 0.8, 0.55, rm, base_z=5.49, lift=0.25, lift_len=0.8,
                          curve=1.5, flare=0.3, per_edge=10, rows=6, thick=0.12, ornaments=False)
    for o in roof:
        util.box_uv(o, 0.8)
    objs += roof
    bm = bmesh.new()
    for k in range(7):
        x = rnd.uniform(-3.0, 2.0)
        ln = rnd.uniform(0.8, 2.2)
        util.tube(bm, [V((x, -0.45, 5.0)), V((x + 0.1, -0.52, 5.0 - ln * 0.5)), V((x - 0.05, -0.5, 5.0 - ln))],
                  0.025, n=4)
        rock(bm, (x, 0, 5.5), (0.35, 0.3, 0.08), k + 50, 0.4, 1)
    objs.append(obj("ArchVines", bm, m["moss"], uv=1.5, smooth=True))
    for sx in (-1, 1):
        objs.append(util.collider("ArchPillar", (1.4, 1.4, 4.8), (sx * 2.65, 0, 2.4)))
    objs.append(util.collider("ArchLintel", (5.8, 0.9, 1.0), (-0.5, 0, 5.1)))
    objs.append(util.collider("ArchFallen", (1.9, 0.9, 0.7), (3.75, 1.3, 0.35), rot_z=R(18)))
    return objs


def _strip_faces(objs, test):
    """Delete faces whose centre satisfies test(x, y, z) (breaks roofs)."""
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        dead = [f for f in bm.faces if test(*f.calc_center_median())]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        bm.to_mesh(o.data)
        bm.free()


def ruined_shrine():
    """Broken roofed shrine on a walkable stone platform, with a weathered statue."""
    m = kit()
    rnd = random.Random(43)
    faded = util.material("faded_lacquer", tex.lacquer("#6a2a20", 512, 54, 0.6), normal_strength=0.5)
    mossy_tiles = util.material("mossy_tiles", tex.roof_tiles("#3b463d", 512, 112), normal_strength=1.0)
    objs = []
    pm = {"brick": m["blocks"], "stone": m["ruin"], "marble": m["ruin"]}
    th = 0.9
    objs += arch.platform("Shrine", 5.2, 3.8, th, pm, stairs_w=3.2, rails=False)
    bm_p, bm_s = bmesh.new(), bmesh.new()
    cols = [(-4.2, 2.8, 3.6), (-1.4, 2.8, 3.6), (1.4, 2.8, 3.6), (4.2, 2.8, 3.6),
            (-4.2, -2.8, 3.6), (-1.4, -2.8, 1.3), (1.4, -2.8, 3.6), (4.2, -2.8, 0.6)]
    for (x, y, h) in cols:
        arch.column(bm_p, bm_s, x, y, th, h, r=0.22)
    pil = obj("ShrinePillars", bm_p, faded, uv=1.0, smooth=True)
    objs += [pil, obj("ShrinePillarBases", bm_s, m["ruin"], uv=1.0)]
    # beams on the standing pillars, one fallen across the steps
    bm = bmesh.new()
    top = th + 3.6
    util.box(bm, (9.0, 0.3, 0.4), loc=(0, 2.8, top + 0.1))
    util.box(bm, (0.3, 6.2, 0.4), loc=(-4.2, 0, top + 0.1))
    util.box(bm, (3.4, 0.3, 0.4), loc=(-2.8, -2.8, top + 0.1))
    bevel_box(bm, (4.2, 0.28, 0.35), loc=(3.2, -3.9, 0.8), rot=Matrix.Rotation(R(-24), 4,
                                                                               "Z") @ Matrix.Rotation(R(14), 4, "Y"),
              bevel=0.03)
    objs.append(obj("ShrineBeams", bm, m["old_planks"], uv=1.0))
    rm = {"tiles": mossy_tiles, "wood": m["old_planks"], "ridge": m["ruin"], "gold": m["ruin"]}
    roof = arch.rect_roof("ShrineRoof", 0, 0.2, 5.8, 4.2, 2.4, rm, base_z=top + 0.3, lift=0.5, lift_len=1.6,
                          curve=1.7, flare=0.3, per_edge=16, rows=10)
    _strip_faces(roof, lambda x, y, z: (x > 0.2 and y < 0.8 + 0.8 * math.sin(x * 2.3)) or (x > 3.5 and y < 2.5))
    objs += roof
    bm = bmesh.new()
    for k in range(5):
        x = 0.6 + k * 1.0
        util.box(bm, (0.12, 5.2, 0.14), loc=(x, 0.3, top + 1.1 + 0.25 * (4 - k)),
                 rot=Matrix.Rotation(R(rnd.uniform(-6, 6)), 4, "Z"))
    objs.append(obj("ShrineRafters", bm, m["old_planks"], uv=1.0))
    # back wall (broken), altar and statue
    bm = bmesh.new()
    for k in range(6):
        x0 = -4.2 + k * 1.4
        hh = 3.4 if k < 3 else 3.4 - (k - 2) * 0.8
        util.box(bm, (1.4, 0.25, hh), loc=(x0 + 0.7, 3.0, th + hh / 2))
    objs.append(obj("ShrineWall", bm, m["daub"], uv=0.4))
    bm = bmesh.new()
    bevel_box(bm, (2.2, 1.0, 0.9), loc=(0, 2.1, th + 0.45), bevel=0.06)
    bevel_box(bm, (1.2, 0.8, 0.3), loc=(0, 2.3, th + 1.05), bevel=0.05)
    rock(bm, (0, 2.3, th + 1.55), (0.55, 0.42, 0.45), 1.0, 0.15, 2)
    util.sphere(bm, 0.36, loc=(0, 2.3, th + 2.05), segs=14, rings=10, scale=(1.0, 0.9, 0.85))
    util.sphere(bm, 0.25, loc=(0, 2.2, th + 2.5), segs=12, rings=8, scale=(0.9, 0.9, 1.1))
    util.cylinder(bm, 0.1, 0.06, 0.2, loc=(0, 2.25, th + 2.75), segs=8)
    for sx in (-1, 1):
        util.tube(bm, [V((sx * 0.35, 2.3, th + 2.1)), V((sx * 0.4, 2.0, th + 1.75)), V((sx * 0.12, 1.95, th + 1.6))],
                  0.09, n=8)
    for k in range(10):
        rock(bm, (rnd.uniform(1.0, 4.5), rnd.uniform(-3.0, 1.0), th + 0.05), (0.3, 0.25, 0.12), k + 7, 0.4, 1)
    objs.append(obj("ShrineAltar", bm, m["ruin"], uv=0.9, smooth=False))
    bm = bmesh.new()
    for k in range(12):
        rock(bm, (rnd.uniform(0.5, 4.8), rnd.uniform(-3.6, 1.5), th + 0.08), (0.35, 0.28, 0.1), k + 20, 0.5, 1)
    objs.append(obj("ShrineTileRubble", bm, mossy_tiles, uv=1.0))
    for (x, y, h) in cols:
        objs.append(util.collider("ShrinePillar", (0.44, 0.44, h), (x, y, th + h / 2)))
    objs.append(util.collider("ShrineWallCol", (8.4, 0.3, 3.4), (0, 3.0, th + 1.7)))
    objs.append(util.collider("ShrineAltarCol", (2.2, 1.2, 2.2), (0, 2.2, th + 1.1)))
    return objs


def hermit_hut():
    """Thatched wattle-and-daub hut with a porch bench, woodpile and water jar."""
    m = kit()
    jar_m = util.material("clay_glaze", glaze("#6b4a32"), normal_strength=0.2)
    objs = []
    hw, hd, base, wh = 2.7, 2.2, 0.3, 2.3
    bm = bmesh.new()
    bevel_box(bm, (hw * 2 + 0.3, hd * 2 + 0.3, base), loc=(0, 0, base / 2), bevel=0.06)
    bevel_box(bm, (1.4, 0.5, 0.18), loc=(0, -hd - 0.35, 0.09), bevel=0.04)
    objs.append(obj("HutBase", bm, m["rock"], uv=0.6))
    # walls: front with door, window on the east side
    bm = bmesh.new()
    z0, z1 = base, base + wh
    zc = (z0 + z1) / 2
    util.box(bm, (hw * 2, 0.16, wh), loc=(0, hd, zc))
    util.box(bm, (0.16, hd * 2, wh), loc=(-hw, 0, zc))
    util.box(bm, (0.16, hd * 2, 0.9), loc=(hw, 0, z0 + 0.45))
    util.box(bm, (0.16, hd * 2, 0.5), loc=(hw, 0, z1 - 0.25))
    for sy in (-1, 1):
        util.box(bm, (0.16, hd - 0.6, 0.9), loc=(hw, sy * (0.6 + (hd - 0.6) / 2), z0 + 1.35))
    dw = 0.55
    for sx in (-1, 1):
        util.box(bm, (hw - dw, 0.16, wh), loc=(sx * (dw + (hw - dw) / 2), -hd, zc))
    util.box(bm, (dw * 2, 0.16, wh - 1.95), loc=(0, -hd, z0 + 1.95 + (wh - 1.95) / 2))
    objs.append(obj("HutWalls", bm, m["daub"], uv=0.5))
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.cylinder(bm, 0.11, 0.1, wh + 0.2, loc=(sx * hw, sy * hd, z0 + wh / 2), segs=8)
        util.box(bm, (0.14, 0.14, 1.95), loc=(sx * dw, -hd - 0.02, z0 + 0.97))
    util.box(bm, (dw * 2 + 0.3, 0.14, 0.14), loc=(0, -hd - 0.02, z0 + 1.97))
    for sy in (-1, 1):
        util.tube(bm, [V((-hw - 0.1, sy * hd, z1)), V((hw + 0.1, sy * hd, z1))], 0.09, n=8)
    for sx in (-1, 1):
        util.tube(bm, [V((sx * hw, -hd - 0.1, z1 - 0.05)), V((sx * hw, hd + 0.1, z1 - 0.05))], 0.09, n=8)
    for k in range(5):
        util.cylinder(bm, 0.025, 0.025, 0.9, loc=(hw + 0.02, -0.45 + k * 0.22, z0 + 1.35), segs=6)
    objs.append(obj("HutTimber", bm, m["log"], uv=1.0, smooth=True))
    # door ajar and the dark interior floor
    bm = bmesh.new()
    door = Matrix.Translation(V((-dw, -hd, z0))) @ Matrix.Rotation(R(-70), 4, "Z")
    bevel_box(bm, (dw * 2 - 0.1, 0.06, 1.9), loc=(dw - 0.05, 0, 0.95), bevel=0.01)
    bmesh.ops.transform(bm, matrix=door, verts=bm.verts)
    util.box(bm, (hw * 2 - 0.2, hd * 2 - 0.2, 0.04), loc=(0, 0, z0 + 0.02))
    util.box(bm, (1.6, 0.4, 0.08), loc=(0, -hd - 0.75, 0.45))
    for sx in (-1, 1):
        util.box(bm, (0.08, 0.3, 0.42), loc=(sx * 0.65, -hd - 0.75, 0.21))
    objs.append(obj("HutPlanks", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    util.box(bm, (hw * 2 - 0.3, 0.05, wh - 0.2), loc=(0, hd - 0.12, zc))
    objs.append(obj("HutInterior", bm, m["dark"]))
    # thatch roof
    rm = {"tiles": m["thatch"], "wood": m["log"], "ridge": m["thatch"], "gold": m["thatch"]}
    roof = arch.rect_roof("HutRoof", 0, 0, hw + 0.8, hd + 0.8, 1.9, rm, base_z=z1 - 0.1, lift=0.1, lift_len=1.0,
                          curve=1.15, flare=0.05, per_edge=12, rows=8, thick=0.28, ornaments=False, detail=1.8)
    objs += roof
    # woodpile, jar, chopping stump
    bm = bmesh.new()
    for r_ in range(3):
        for k in range(5 - r_):
            util.cylinder(bm, 0.09, 0.09, 1.1, loc=(-hw - 0.35, -1.2 + k * 0.19 + r_ * 0.095, 0.1 + r_ * 0.16),
                          segs=7, rot=Matrix.Rotation(R(90), 4, "X"))
    util.cylinder(bm, 0.25, 0.28, 0.45, loc=(1.9, -hd - 1.4, 0.22), segs=12)
    objs.append(obj("HutWoodpile", bm, m["log"], uv=1.5, smooth=True))
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.0), (0.2, 0.0), (0.3, 0.2), (0.32, 0.4), (0.22, 0.62), (0.2, 0.68), (0.23, 0.72)],
               segs=16, loc=(hw + 0.45, -1.4, 0.0), cap_bottom=True)
    objs.append(obj("HutJar", bm, jar_m, uv=2.0, smooth=True))
    objs.append(util.collider("HutBody", (hw * 2 + 0.3, hd * 2 + 0.3, 2.9), (0, 0, 1.45)))
    objs.append(util.collider("HutWood", (0.6, 1.2, 0.6), (-hw - 0.35, -0.9, 0.3)))
    return objs


def campfire():
    """Stone ring, crossed logs, glowing embers and flames, a tripod with a pot."""
    m = kit()
    rnd = random.Random(47)
    charred = util.material("charred", tex.bark("#2a211b", 256, 136), normal_strength=0.8)
    ember = util.material("embers", tex.stone("#3a1a0c", 256, 80, 0.4), emission="#ff5a1a", emission_strength=3.0)
    flame = glow_mat("flame", "#ff9a30", 4.0)
    core = glow_mat("flame_core", "#ffd27a", 6.0)
    bm = bmesh.new()
    for k in range(10):
        a = 2 * math.pi * k / 10 + rnd.uniform(-0.1, 0.1)
        rock(bm, (math.cos(a) * 0.72, math.sin(a) * 0.72, 0.08), (0.2, 0.17, 0.14), k + 3, 0.35, 1)
    stones = obj("FireStones", bm, m["rock"], uv=1.5, smooth=True)
    bm = bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        d = V((math.cos(a), math.sin(a), 0))
        util.tube(bm, [d * 0.55 + V((0, 0, 0.05)), d * 0.08 + V((0, 0, 0.55))], lambda t: 0.06 * (1 - 0.4 * t), n=7)
    logs = obj("FireLogs", bm, charred, uv=2.0, smooth=True)
    bm = bmesh.new()
    rock(bm, (0, 0, 0.02), (0.45, 0.45, 0.08), 9.0, 0.4, 2)
    embers = obj("FireEmbers", bm, ember, uv=2.0, smooth=True)
    bm_f, bm_c = bmesh.new(), bmesh.new()
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.3, 0.3)
        off = V((math.cos(a) * 0.14, math.sin(a) * 0.14, 0.05))
        h = rnd.uniform(0.35, 0.75)
        prof = [(0.08, 0.0), (0.09, h * 0.25), (0.05, h * 0.6), (0.001, h)]
        rows = util.lathe(bm_f, prof, segs=6, loc=off)
        for row in rows[1:]:
            for v in row:
                v.co.x += 0.05 * math.sin(v.co.z * 10 + k * 1.7)
                v.co.y += 0.04 * math.cos(v.co.z * 8 + k)
        util.lathe(bm_c, [(0.04, 0.02), (0.045, h * 0.2), (0.001, h * 0.5)], segs=5, loc=off)
    fl = obj("Flames", bm_f, flame, smooth=True)
    fc = obj("FlameCore", bm_c, core, smooth=True)
    bm = bmesh.new()
    apex = V((0, 0, 1.35))
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        util.tube(bm, [V((math.cos(a) * 0.9, math.sin(a) * 0.9, 0)), apex + V((math.cos(a) * 0.05, math.sin(a) * 0.05,
                                                                               0.1))],
                  0.03, n=6)
    tri = obj("FireTripod", bm, m["log"], uv=2.0, smooth=True)
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.62), (0.14, 0.63), (0.2, 0.7), (0.21, 0.85), (0.18, 0.92), (0.19, 0.94)], segs=14,
               cap_bottom=False)
    util.tube(bm, [V((0, 0, 0.95)), V((0, 0, 1.4))], 0.008, n=4)
    pot = obj("FirePot", bm, m["iron"], uv=2.0, smooth=True)
    return [stones, logs, embers, fl, fc, tri, pot, util.collider("FireCol", (1.6, 1.6, 0.4), (0, 0, 0.2))]


def bandit_tent():
    """A-frame canvas tent with poles, guy ropes and an open front."""
    m = kit()
    cv = util.material("tent_canvas", canvas("#8f8266", 512, 462), double_sided=True, normal_strength=0.6)
    objs = []
    ridge, half, depth = 2.3, 1.9, 1.7
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    ni, nj = 8, 6
    for sx in (-1, 1):
        grid = []
        for j in range(nj + 1):
            t = j / nj
            row = []
            for i in range(ni + 1):
                s = i / ni
                y = -depth - 0.15 + (2 * depth + 0.3) * s
                sag = 0.13 * math.sin(math.pi * s) * math.sin(math.pi * t)
                x = sx * half * t * 1.02
                z = ridge * (1 - t) - sag + 0.05
                row.append(bm.verts.new(V((x + sx * sag * 0.3, y, z))))
            grid.append(row)
        for j in range(nj):
            for i in range(ni):
                q = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                f = bm.faces.new(q if sx > 0 else tuple(reversed(q)))
                for loop in f.loops:
                    co = loop.vert.co
                    loop[uv].uv = (co.y * 0.4, abs(co.x) * 0.5)
    # back panel and folded-back front flaps
    back = [bm.verts.new(V(p)) for p in ((-half, depth + 0.1, 0.05), (half, depth + 0.1, 0.05), (0, depth + 0.1,
                                                                                                 ridge))]
    f = bm.faces.new(back)
    for loop in f.loops:
        loop[uv].uv = (loop.vert.co.x * 0.4, loop.vert.co.z * 0.4)
    for sx in (-1, 1):
        flap = ((sx * 0.25, -depth - 0.14, ridge * 0.86), (sx * half * 0.9, -depth - 0.5, 0.15),
                (sx * half * 1.05, -depth + 0.1, 0.1))
        fl = [bm.verts.new(V(p)) for p in flap]
        f = bm.faces.new(fl)
        for loop in f.loops:
            loop[uv].uv = (loop.vert.co.x * 0.4, loop.vert.co.z * 0.4)
    objs.append(util.mesh_object("TentCanvas", bm, cv, smooth=True))
    bm = bmesh.new()
    for y in (-depth - 0.1, depth + 0.05):
        util.cylinder(bm, 0.045, 0.04, ridge + 0.25, loc=(0, y, (ridge + 0.25) / 2), segs=8)
    util.tube(bm, [V((0, -depth - 0.35, ridge + 0.06)), V((0, depth + 0.3, ridge + 0.06))], 0.04, n=8)
    for y in (-depth - 2.0, depth + 1.8):
        util.box(bm, (0.06, 0.06, 0.35), loc=(0, y, 0.1), rot=Matrix.Rotation(R(20 if y > 0 else -20), 4, "X"))
    for sx in (-1, 1):
        for y in (-depth + 0.3, 0, depth - 0.3):
            util.box(bm, (0.05, 0.05, 0.3), loc=(sx * (half + 0.6), y, 0.08))
    objs.append(obj("TentPoles", bm, m["log"], uv=2.0, smooth=True))
    bm = bmesh.new()
    for y in (-1, 1):
        util.tube(bm, [V((0, y * (depth + 0.3), ridge + 0.1)), V((0, y * (depth + 2.0), 0.2))], 0.012, n=4)
    for sx in (-1, 1):
        for y in (-depth + 0.3, 0, depth - 0.3):
            util.tube(bm, [V((sx * half * 0.55, y, ridge * 0.45)), V((sx * (half + 0.6), y, 0.2))], 0.01, n=4)
    util.cylinder(bm, 0.2, 0.2, 1.2, loc=(0.6, 0.2, 0.2), segs=10, rot=Matrix.Rotation(R(90), 4, "X"))
    objs.append(obj("TentRopes", bm, m["rope"], uv=3.0, smooth=True))
    bm = bmesh.new()
    util.box(bm, (2.6, 2.8, 0.03), loc=(0, 0.1, 0.02))
    objs.append(obj("TentFloor", bm, m["dark"]))
    bm = bmesh.new()
    util.box(bm, (half * 2 + 0.2, 2 * depth + 0.3, 0.1), loc=(0, 0, 0.05))
    for v in [v for v in bm.verts if v.co.z > 0.07]:
        v.co.x *= 0.06
        v.co.z = ridge
    objs.append(convex_mesh("TentCol", bm))
    return objs


def _crate(bm_b, bm_f, size, loc, yaw=0.0):
    rot = Matrix.Rotation(yaw, 4, "Z")
    bevel_box(bm_b, size, loc=loc, rot=rot, bevel=0.02)
    sx, sy, sz = size
    t = 0.06
    for dx in (-1, 1):
        for dy in (-1, 1):
            p = rot @ V((dx * (sx / 2 - t / 2 + 0.01), dy * (sy / 2 - t / 2 + 0.01), 0))
            util.box(bm_f, (t, t, sz + 0.02), loc=V(loc) + p, rot=rot)
    for dz in (-1, 1):
        for dy in (-1, 1):
            p = rot @ V((0, dy * (sy / 2 - t / 2 + 0.01), dz * (sz / 2 - t / 2 + 0.01)))
            util.box(bm_f, (sx + 0.02, t, t), loc=V(loc) + p, rot=rot)
        for dx in (-1, 1):
            p = rot @ V((dx * (sx / 2 - t / 2 + 0.01), 0, dz * (sz / 2 - t / 2 + 0.01)))
            util.box(bm_f, (t, sy + 0.02, t), loc=V(loc) + p, rot=rot)


def _barrel(bm_w, bm_h, loc, h=0.95, r=0.34):
    x, y, z = loc
    prof = [(r * (0.86 + 0.14 * math.sin(math.pi * t)), h * t) for t in np.linspace(0, 1, 9)]
    util.lathe(bm_w, [(0.001, 0.0)] + prof + [(0.001, h - 0.02)], segs=16, loc=loc)
    for t in (0.12, 0.35, 0.65, 0.88):
        rr = r * (0.86 + 0.14 * math.sin(math.pi * t)) + 0.008
        ring = [V((x + rr * math.cos(a), y + rr * math.sin(a), z + h * t)) for a in np.linspace(0, 2 * math.pi, 17)]
        util.tube(bm_h, ring, (0.012, 0.035), n=4, power=4, up=(0, 0, 1), closed_ends=False)


def crates():
    """Stacked crates, barrels and sacks."""
    m = kit()
    sack = util.material("sack", canvas("#a08d68", 256, 463), normal_strength=0.6)
    bm_b, bm_f, bm_w, bm_h, bm_s = (bmesh.new() for _ in range(5))
    _crate(bm_b, bm_f, (0.9, 0.9, 0.9), (0, 0, 0.45), 0.1)
    _crate(bm_b, bm_f, (0.8, 0.8, 0.8), (0.05, 0.02, 1.3), 0.45)
    _crate(bm_b, bm_f, (0.7, 0.7, 0.7), (1.0, 0.25, 0.35), -0.3)
    _crate(bm_b, bm_f, (1.6, 0.6, 0.5), (-0.3, 1.05, 0.25), 0.05)
    _barrel(bm_w, bm_h, (-1.2, -0.3, 0.0))
    _barrel(bm_w, bm_h, (-1.35, 0.45, 0.0), h=0.85, r=0.3)
    for k, (x, y) in enumerate(((0.8, -0.8), (0.3, -0.95))):
        rock(bm_s, (x, y, 0.2), (0.24, 0.36, 0.22), k + 11, 0.18, 2)
    objs = [obj("Crates", bm_b, m["planks"], uv=1.2), obj("CrateFrames", bm_f, m["old_planks"], uv=1.2),
            obj("Barrels", bm_w, m["planks"], uv=1.0, smooth=True), obj("BarrelHoops", bm_h, m["iron"], uv=2.0,
                                                                        smooth=True),
            obj("Sacks", bm_s, sack, uv=1.2, smooth=True)]
    objs += [util.collider("CrateCol", (1.05, 1.05, 1.7), (0.02, 0, 0.85)),
             util.collider("CrateCol", (0.85, 0.85, 0.7), (1.0, 0.25, 0.35)),
             util.collider("CrateCol", (1.65, 0.65, 0.5), (-0.3, 1.05, 0.25)),
             util.collider("BarrelCol", (0.8, 1.6, 0.95), (-1.28, 0.08, 0.47))]
    return objs


def wooden_bridge(length=15.0, width=2.6, rise=0.75):
    """Plank footbridge on log piers (along Y), with rails and a walkable deck."""
    m = kit()
    rnd = random.Random(59)
    objs = []

    def deck_z(y):
        t = (y + length / 2) / length
        return rise * math.sin(math.pi * t) - 0.04

    bm = bmesh.new()
    n = int(length / 0.3)
    for k in range(n):
        y = -length / 2 + (k + 0.5) * length / n
        slope = math.atan2(deck_z(y + 0.1) - deck_z(y - 0.1), 0.2)
        util.box(bm, (width + rnd.uniform(-0.1, 0.15), length / n - 0.03, 0.08),
                 loc=(rnd.uniform(-0.05, 0.05), y, deck_z(y) + 0.04),
                 rot=Matrix.Rotation(slope, 4, "X") @ Matrix.Rotation(R(rnd.uniform(-1.5, 1.5)), 4, "Z"))
    objs.append(obj("BridgeDeck", bm, m["old_planks"], uv=1.0))
    bm = bmesh.new()
    for x in (-0.85, 0.85):
        util.tube(bm, [V((x, y, deck_z(y) - 0.1)) for y in np.linspace(-length / 2 - 0.2, length / 2 + 0.2, 13)],
                  0.12, n=8)
    for y in (-length * 0.27, 0.0, length * 0.27):
        for x in (-1.0, 1.0):
            util.tube(bm, [V((x, y, -2.2)), V((x * 0.95, y, deck_z(y) - 0.05))], 0.13, n=8)
        util.tube(bm, [V((-1.05, y, deck_z(y) - 0.25)), V((1.05, y, deck_z(y) - 0.25))], 0.1, n=8)
        util.tube(bm, [V((-1.0, y, -1.6)), V((1.0, y, deck_z(y) - 0.4))], 0.07, n=6)
    for sx in (-1, 1):
        x = sx * (width / 2 + 0.02)
        posts = 7
        for k in range(posts):
            y = -length / 2 + 0.4 + (length - 0.8) * k / (posts - 1)
            util.tube(bm, [V((x, y, deck_z(y) - 0.15)), V((x, y, deck_z(y) + 1.0))], 0.06, n=7)
        util.tube(bm, [V((x, y, deck_z(y) + 0.95)) for y in np.linspace(-length / 2 + 0.4, length / 2 - 0.4, 14)],
                  0.045, n=7)
        util.tube(bm, [V((x, y, deck_z(y) + 0.5)) for y in np.linspace(-length / 2 + 0.4, length / 2 - 0.4, 14)],
                  0.03, n=6)
    objs.append(obj("BridgeFrame", bm, m["log"], uv=1.5, smooth=True))
    bm = bmesh.new()
    rows = []
    for k in range(25):
        y = -length / 2 - 0.3 + (length + 0.6) * k / 24
        z = deck_z(max(-length / 2, min(length / 2, y))) + 0.08
        rows.append((bm.verts.new(V((-width / 2, y, z))), bm.verts.new(V((width / 2, y, z)))))
    for k in range(24):
        bm.faces.new((rows[k][0], rows[k][1], rows[k + 1][1], rows[k + 1][0]))
    objs.append(util.mesh_object("BridgeWalk-colonly", bm, None, smooth=False))
    for sx in (-1, 1):
        for k in range(5):
            y0 = -length / 2 + 0.4 + (length - 0.8) * k / 5
            y1 = y0 + (length - 0.8) / 5
            yc = (y0 + y1) / 2
            objs.append(util.collider("BridgeRail", (0.2, y1 - y0, 1.2), (sx * (width / 2 + 0.05), yc,
                                                                          deck_z(yc) + 0.55)))
    return objs


def cave_mouth():
    """Mossy rock outcrop with a dark cave mouth and scattered bones (~13 m wide)."""
    m = kit()
    bone = util.material("bone", tex.stone("#d8d0bb", 256, 81, 0.1), normal_strength=0.3)
    objs = []
    specs = [((-5.6, 1.2, 2.0), (3.2, 4.2, 4.8), 1), ((5.8, 1.4, 2.2), (3.4, 4.4, 5.2), 2),
             ((0.2, 2.4, 6.4), (5.8, 4.2, 2.3), 3), ((0.0, 6.2, 3.0), (7.5, 3.0, 6.0), 4),
             ((-7.2, 3.5, 1.2), (2.5, 3.2, 3.0), 5), ((7.6, 3.2, 1.0), (2.4, 3.0, 2.6), 6)]
    bm = bmesh.new()
    for (loc, size, sd) in specs:
        rock(bm, loc, size, sd * 3.3, 0.28, 3)
    for f in bm.faces:
        f.material_index = 1 if f.normal.z > 0.8 and f.calc_center_median().z > 3.0 else 0
    rocks = util.mesh_object("CaveRocks", bm, [m["rock"], m["moss"]], smooth=True)
    util.box_uv(rocks, 0.25)
    objs.append(rocks)
    bm = bmesh.new()
    util.sphere(bm, 1.0, loc=(0.1, 3.4, 2.0), segs=16, rings=10, scale=(2.6, 1.4, 2.4))
    objs.append(obj("CaveDark", bm, m["dark"], smooth=True))
    bm = bmesh.new()
    rnd = random.Random(61)
    for k in range(9):
        c = V((rnd.uniform(-2.5, 2.5), rnd.uniform(-3.5, -0.5), 0.05))
        a = rnd.uniform(0, math.pi)
        d = V((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.2, 0.35)
        util.tube(bm, [c - d, c + d], 0.025, n=5)
        util.sphere(bm, 0.045, loc=c - d, segs=6, rings=4)
        util.sphere(bm, 0.045, loc=c + d, segs=6, rings=4)
    util.sphere(bm, 0.12, loc=(1.2, -1.8, 0.1), segs=10, rings=7, scale=(1.0, 1.3, 0.9))
    objs.append(obj("CaveBones", bm, bone, uv=3.0, smooth=True))
    for (loc, size, sd) in specs:
        cb = bmesh.new()
        util.box(cb, tuple(s * 1.55 for s in size), loc=loc)
        objs.append(convex_mesh("CaveRock", cb))
    objs.append(util.collider("CaveBlock", (5.0, 1.0, 4.5), (0.1, 2.4, 2.2)))
    return objs


# --------------------------------------------------------------------------
# town
# --------------------------------------------------------------------------
def town_kit():
    m = kit()
    m["door"] = util.material("door_lacquer", tex.lacquer("#5a2418", 512, 55, 0.35), normal_strength=0.4)
    m["tiles"] = util.material("roof_tiles", tex.roof_tiles("#43464a", 512, 113), normal_strength=1.0)
    m["lattice"] = util.material("lattice_window", tex.lattice("#3b2a1e", "#e9dcc0", 256, 5), normal_strength=0.5)
    return m


def gable_roof(name, hw, hd, h, mats, base_z, curve=1.35, lift=0.18, thick=0.12, nx=16, ny=8, curl=True):
    """Concave gable roof, ridge along X at y = 0 (hw/hd include the overhangs)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()

    def z_at(x, s):
        return base_z + h * (1 - s) ** curve + lift * s ** 3 * (abs(x) / hw) ** 6

    slope_len = math.hypot(hd, h)
    for sy in (-1, 1):
        grid = []
        for j in range(ny + 1):
            s = 1 - j / ny
            grid.append([bm.verts.new(V((-hw + 2 * hw * i / nx, sy * hd * s, z_at(-hw + 2 * hw * i / nx, s))))
                         for i in range(nx + 1)])
        for j in range(ny):
            for i in range(nx):
                q = (grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
                f = bm.faces.new(q if sy < 0 else tuple(reversed(q)))
                for loop in f.loops:
                    co = loop.vert.co
                    loop[uv].uv = (co.x * 0.6, (1 - abs(co.y) / hd) * slope_len * 0.5)
    o = util.mesh_object(name, bm, [mats["tiles"], mats["wood"]], smooth=True)
    mod = o.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thick
    mod.offset = -1
    mod.material_offset = 1
    mod.material_offset_rim = 1
    util.apply_modifiers(o)
    bm = bmesh.new()
    top = base_z + h + 0.06
    ridge = [V((-hw - 0.05, 0, top)), V((hw + 0.05, 0, top))]
    util.tube(bm, ridge, (0.14, 0.12), n=8, power=4.0)
    if curl:
        for sgn in (-1, 1):
            end = V((sgn * (hw + 0.05), 0, top))
            rc = min(0.3, hw * 0.07)
            pts = [end + V((sgn * (0.05 - rc * math.sin(a)), 0, rc * 0.9 * (1 - math.cos(a))))
                   for a in np.linspace(0, R(230), 12)]
            util.tube(bm, pts, lambda t: rc * 0.32 * (1 - 0.55 * t), n=8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            edge = [V((sx * hw, sy * hd * (1 - t), z_at(hw, 1 - t) + 0.07)) for t in np.linspace(0, 1, ny + 1)]
            util.tube(bm, edge, (0.08, 0.07), n=6, power=3.0)
    r = util.mesh_object(name + "Ridge", bm, mats["ridge"], smooth=True)
    util.box_uv(r, 1.0)
    return [o, r], z_at


def wall_openings(bm, x0, x1, y, z0, z1, t, openings=()):
    """Wall slab along X at depth y with rectangular openings (xa, xb, za, zb)."""
    xs = sorted({x0, x1, *[o[0] for o in openings], *[o[1] for o in openings]})
    for xa, xb in zip(xs[:-1], xs[1:]):
        if xb - xa < 1e-4:
            continue
        xm = (xa + xb) / 2
        holes = sorted((o[2], o[3]) for o in openings if o[0] <= xm <= o[1])
        z = z0
        for (za, zb) in holes + [(z1, z1)]:
            if za - z > 1e-4:
                util.box(bm, (xb - xa, t, za - z), loc=(xm, y, (z + za) / 2))
            z = max(z, zb)


def panel(bm, x0, x1, y, z0, z1, u_reps=1.0, flip=False):
    """Single UV-mapped quad in an XZ plane facing -Y (+Y when flip) for windows, doors and signs."""
    uv = bm.loops.layers.uv.verify()
    if flip:
        corners = (((x1, z0), (0, 0)), ((x0, z0), (u_reps, 0)), ((x0, z1), (u_reps, 1)), ((x1, z1), (0, 1)))
    else:
        corners = (((x0, z0), (0, 0)), ((x1, z0), (u_reps, 0)), ((x1, z1), (u_reps, 1)), ((x0, z1), (0, 1)))
    f = bm.faces.new([bm.verts.new(V((x, y, z))) for (x, z), _ in corners])
    for loop, (_, st) in zip(f.loops, corners):
        loop[uv].uv = st
    return f


def gable_wall(bm, x, hd, z_base, z_at, roof_hd, t=0.2, steps=8):
    """Gable-end wall at x (spanning y = -hd..hd) following the roof underside."""
    outline = [(-hd, z_base), (hd, z_base)]
    outline += [(hd * (1 - k / steps), z_at(x, hd * (1 - k / steps) / roof_hd) - 0.12) for k in range(steps + 1)]
    outline += [(-hd * k / steps, z_at(x, hd * k / steps / roof_hd) - 0.12) for k in range(1, steps + 1)]
    tmp = bmesh.new()
    extrude_outline(tmp, outline, -t / 2, t / 2)
    bmesh.ops.transform(tmp, matrix=Matrix.Translation(V((x, 0, 0))) @ Matrix.Rotation(R(90), 4, "Z"), verts=tmp.verts)
    merge(bm, tmp)


def town_house(w=8.0, d=5.5, seed=1):
    """Single-storey house: stone plinth, white walls, timber frame, grey-tile gable roof."""
    m = town_kit()
    objs = []
    base, wz = 0.35, 3.25
    hw, hd = w / 2, d / 2
    bm = bmesh.new()
    bevel_box(bm, (w + 0.4, d + 0.4, base), loc=(0, 0, base / 2), bevel=0.04)
    bevel_box(bm, (2.0, 0.6, 0.18), loc=(0, -hd - 0.45, 0.09), bevel=0.03)
    objs.append(obj("HousePlinth", bm, m["stone"], uv=0.7))
    door = (-0.8, 0.8, base, base + 2.25)
    wins = [(-3.2, -1.9, base + 1.2, base + 2.3), (1.9, 3.2, base + 1.2, base + 2.3)]
    bm, bm_d = bmesh.new(), bmesh.new()
    wall_openings(bm, -hw, hw, -hd, base + 0.8, wz, 0.22, [door] + wins)
    wall_openings(bm, -hw, hw, hd, base + 0.8, wz, 0.22, [(-0.6, 0.6, base + 1.4, base + 2.2)])
    for sx in (-1, 1):
        util.box(bm, (0.22, d, wz - base - 0.8), loc=(sx * hw, 0, (base + 0.8 + wz) / 2))
    wall_openings(bm_d, -hw - 0.02, hw + 0.02, -hd, base, base + 0.8, 0.26, [door])
    util.box(bm_d, (w + 0.04, 0.26, 0.8), loc=(0, hd, base + 0.4))
    for sx in (-1, 1):
        util.box(bm_d, (0.26, d + 0.04, 0.8), loc=(sx * hw, 0, base + 0.4))
    roof, z_at = gable_roof("HouseRoof", hw + 0.45, hd + 0.7, 2.0, m, wz + 0.05)
    for sx in (-1, 1):
        gable_wall(bm, sx * hw, hd, wz - 0.01, z_at, hd + 0.7, t=0.22)
    objs.append(obj("HouseWalls", bm, m["whitewash"], uv=0.4))
    objs.append(obj("HouseDado", bm_d, m["brick"], uv=0.5))
    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (0.24, 0.24, wz - base), loc=(sx * hw, sy * hd, (base + wz) / 2))
        util.box(bm, (0.2, 0.26, 2.35), loc=(sx * 0.9, -hd - 0.01, base + 1.17))
        util.box(bm, (0.14, 0.26, 1.3), loc=(sx * 3.3, -hd - 0.01, base + 1.75))
        util.box(bm, (0.14, 0.26, 1.3), loc=(sx * 1.8, -hd - 0.01, base + 1.75))
        util.box(bm, (1.6, 0.3, 0.12), loc=(sx * 2.55, -hd - 0.02, base + 1.15))
        util.box(bm, (1.6, 0.3, 0.12), loc=(sx * 2.55, -hd - 0.02, base + 2.35))
    util.box(bm, (2.0, 0.28, 0.2), loc=(0, -hd - 0.02, base + 2.35))
    for sy in (-1, 1):
        util.box(bm, (w + 0.3, 0.3, 0.26), loc=(0, sy * hd, wz - 0.05))
    objs.append(obj("HouseTimber", bm, m["wood"], uv=1.0))
    bm = bmesh.new()
    for (x0, x1, z0, z1) in wins:
        panel(bm, x0 + 0.05, x1 - 0.05, -hd - 0.02, z0, z1, 2)
    panel(bm, -0.55, 0.55, hd + 0.12, base + 1.4, base + 2.2, 1, flip=True)
    objs.append(util.mesh_object("HouseWindows", bm, m["lattice"], smooth=False))
    bm = bmesh.new()
    for sx in (-1, 1):
        bevel_box(bm, (0.78, 0.07, 2.2), loc=(sx * 0.4, -hd + 0.03, base + 1.1), bevel=0.02)
        util.sphere(bm, 0.035, loc=(sx * 0.1, -hd - 0.02, base + 1.1), segs=8, rings=5)
    objs.append(obj("HouseDoor", bm, m["door"], uv=1.0))
    bm = bmesh.new()
    util.box(bm, (w - 0.3, d - 0.3, 0.05), loc=(0, 0, base + 0.02))
    util.box(bm, (1.5, 0.05, 2.2), loc=(0, -hd + 0.4, base + 1.1))
    objs.append(obj("HouseInside", bm, m["dark"]))
    objs += roof
    rnd = random.Random(seed)
    bm = bmesh.new()
    util.box(bm, (1.5, 0.4, 0.07), loc=(2.4, -hd - 0.55, 0.47))
    for sx in (-0.6, 0.6):
        util.box(bm, (0.08, 0.3, 0.44), loc=(2.4 + sx, -hd - 0.55, 0.22))
    objs.append(obj("HouseBench", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.0), (0.28, 0.0), (0.36, 0.3), (0.34, 0.6), (0.3, 0.66), (0.33, 0.7)], segs=14,
               loc=(-hw + 0.5, -hd - 0.6, 0.0), cap_bottom=True)
    if rnd.random() < 0.7:
        util.lathe(bm, [(0.001, 0.0), (0.12, 0.0), (0.16, 0.18), (0.1, 0.34), (0.12, 0.38)], segs=10,
                   loc=(-hw + 1.2, -hd - 0.5, 0.0), cap_bottom=True)
    objs.append(obj("HouseJars", bm, util.material("clay_glaze", glaze("#6b4a32"), normal_strength=0.2), uv=2.0,
                    smooth=True))
    objs.append(util.collider("HouseBody", (w + 0.4, d + 0.4, wz + 0.3), (0, 0, (wz + 0.3) / 2)))
    return objs


def town_house_large(w=11.0, d=7.0):
    """Two-storey inn: open lattice front, balcony, gable roof, hanging signs and lanterns."""
    m = town_kit()
    sign_v = util.material("inn_sign", signboard(512, 563, 4, "#2b1d14", "#e3b85a", vertical=True), normal_strength=0.4)
    sign_h = util.material("inn_plaque", signboard(512, 564, 4, "#1b2a4a", "#e2bd57", vertical=False),
                           normal_strength=0.4)
    flag_maps = canvas("#e8ddc4", 256, 464)
    flag_maps["albedo"] = tex.lerp(flag_maps["albedo"], tex.srgb("#1a1a1a"),
                                   glyph_mask(256, 1, 1, 77, (0.25, 0.3, 0.75, 0.8), 0.04))
    flag = util.material("wine_flag", flag_maps, double_sided=True, normal_strength=0.3)
    objs = []
    base, f1, f2 = 0.4, 3.6, 6.6
    hw, hd = w / 2, d / 2
    bm = bmesh.new()
    bevel_box(bm, (w + 0.5, d + 0.5, base), loc=(0, 0, base / 2), bevel=0.05)
    bevel_box(bm, (3.0, 0.7, 0.2), loc=(0, -hd - 0.55, 0.1), bevel=0.03)
    objs.append(obj("InnPlinth", bm, m["stone"], uv=0.7))
    xs = [-hw, -3.3, -1.1, 1.1, 3.3, hw]
    bm, bm_d = bmesh.new(), bmesh.new()
    wall_openings(bm, -hw, hw, hd, base + 0.8, f2, 0.24, [(-2, 2, f1 + 1.0, f1 + 2.1)])
    for sx in (-1, 1):  # side walls, built along X then turned into place
        tmp = bmesh.new()
        wall_openings(tmp, -hd, hd, 0, base + 0.8, f2, 0.24, [(-1.2, 1.2, f1 + 1.0, f1 + 2.1)])
        bmesh.ops.transform(tmp, matrix=Matrix.Translation(V((sx * hw, 0, 0))) @ Matrix.Rotation(R(90), 4, "Z"),
                            verts=tmp.verts)
        merge(bm, tmp)
    # upper front wall with lattice windows, ground floor front mostly lattice doors
    windows = [(xs[i] + 0.35, xs[i + 1] - 0.35, f1 + 0.9, f2 - 0.45) for i in range(5)]
    wall_openings(bm, -hw, hw, -hd, f1 + 0.1, f2, 0.2, windows)
    util.box(bm_d, (w + 0.04, 0.28, 0.8), loc=(0, hd, base + 0.4))
    for sx in (-1, 1):
        util.box(bm_d, (0.28, d + 0.04, 0.8), loc=(sx * hw, 0, base + 0.4))
    roof, z_at = gable_roof("InnRoof", hw + 0.6, hd + 1.9, 2.8, m, f2 + 0.05, nx=18, ny=10)
    for sx in (-1, 1):
        gable_wall(bm, sx * hw, hd, f2 - 0.01, z_at, hd + 1.9, t=0.24)
    objs.append(obj("InnWalls", bm, m["whitewash"], uv=0.4))
    objs.append(obj("InnDado", bm_d, m["brick"], uv=0.5))
    bm = bmesh.new()
    for i in range(5):
        x0, x1 = xs[i] + 0.2, xs[i + 1] - 0.2
        panel(bm, x0, x1, -hd, base + (0.05 if i in (1, 2, 3) else 0.9), f1 - 0.35, 3 if i in (1, 2, 3) else 2)
        panel(bm, xs[i] + 0.4, xs[i + 1] - 0.4, -hd - 0.08, f1 + 0.9, f2 - 0.45, 2)
    objs.append(util.mesh_object("InnLattice", bm, m["lattice"], smooth=False))
    bm = bmesh.new()
    for i in (0, 4):
        util.box(bm, (xs[i + 1] - xs[i] - 0.3, 0.26, 0.85), loc=((xs[i] + xs[i + 1]) / 2, -hd, base + 0.42))
    objs.append(obj("InnFrontDado", bm, m["brick"], uv=0.5))
    # columns, balcony, beams
    bm_p, bm_s = bmesh.new(), bmesh.new()
    for x in xs:
        arch.column(bm_p, bm_s, x, -hd, base, f2 - base, r=0.18)
        arch.column(bm_p, bm_s, x, -hd - 1.3, base, f1 + 1.05 - base, r=0.14)
    objs.append(obj("InnColumns", bm_p, m["pillar"], uv=1.0, smooth=True))
    objs.append(obj("InnColumnBases", bm_s, m["stone"], uv=1.0))
    bm = bmesh.new()
    util.box(bm, (w + 0.4, 1.5, 0.16), loc=(0, -hd - 0.7, f1))
    for x in np.linspace(-hw, hw, 23):
        util.box(bm, (0.06, 0.06, 0.8), loc=(x, -hd - 1.35, f1 + 0.45))
    util.box(bm, (w + 0.3, 0.1, 0.08), loc=(0, -hd - 1.35, f1 + 0.9))
    util.box(bm, (w + 0.3, 0.08, 0.06), loc=(0, -hd - 1.35, f1 + 0.2))
    for sx in (-1, 1):
        util.box(bm, (0.08, 1.4, 0.08), loc=(sx * (hw + 0.1), -hd - 0.7, f1 + 0.9))
    objs.append(obj("InnBalcony", bm, m["wood"], uv=1.0))
    bm = bmesh.new()
    for y in (-hd - 1.3, -hd, hd):
        util.box(bm, (w + 0.6, 0.28, 0.34), loc=(0, y, f1 + 1.1 if y < -hd - 1 else f2 - 0.05))
    util.box(bm, (w + 0.4, 0.3, 0.3), loc=(0, -hd, f1 - 0.1))
    objs.append(obj("InnBeams", bm, m["beam"], uv=1.0))
    bm = bmesh.new()
    util.box(bm, (w - 0.4, d - 0.4, 0.05), loc=(0, 0, base + 0.02))
    util.box(bm, (w - 0.5, 0.05, f1 - base - 0.2), loc=(0, -hd + 0.6, (base + f1) / 2))
    objs.append(obj("InnInside", bm, m["dark"]))
    objs += roof
    # signs: horizontal plaque over the entrance, vertical board at the corner, a wine flag
    bm = bmesh.new()
    panel(bm, -1.6, 1.6, -hd - 1.45, f1 - 0.95, f1 - 0.25)
    objs.append(util.mesh_object("InnPlaque", bm, sign_h, smooth=False))
    bm = bmesh.new()
    panel(bm, -hw - 0.35, -hw + 0.35, -hd - 1.5, 0.9, f1 - 0.6)
    panel(bm, -hw - 0.35, -hw + 0.35, -hd - 1.54, 0.9, f1 - 0.6, flip=True)
    objs.append(util.mesh_object("InnSign", bm, sign_v, smooth=False))
    bm = bmesh.new()
    util.box(bm, (3.4, 0.12, 0.8), loc=(0, -hd - 1.4, f1 - 0.6))
    util.box(bm, (0.8, 0.08, f1 - 0.6 - 0.8 + 0.1), loc=(-hw, -hd - 1.52, (0.9 + f1 - 0.6) / 2))
    util.tube(bm, [V((hw + 0.2, -hd - 1.3, f2 - 0.5)), V((hw + 1.6, -hd - 1.8, f2 + 0.3))], 0.04, n=6)
    objs.append(obj("InnSignFrames", bm, m["wood"], uv=1.0))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    rows = []
    for j in range(7):
        t = j / 6
        top = V((hw + 0.3, -hd - 1.34, f2 - 0.4)).lerp(V((hw + 1.5, -hd - 1.76, f2 + 0.24)), t)
        rows.append((bm.verts.new(top), bm.verts.new(top + V((0.05 * math.sin(t * 4), 0.1, -1.4)))))
    for j in range(6):
        f = bm.faces.new((rows[j][0], rows[j + 1][0], rows[j + 1][1], rows[j][1]))
        for loop, (uu, vv) in zip(f.loops, ((j / 6, 1), ((j + 1) / 6, 1), ((j + 1) / 6, 0), (j / 6, 0))):
            loop[uvl].uv = (uu, vv)
    objs.append(util.mesh_object("InnWineFlag", bm, flag, smooth=True))
    for x in (-2.2, 2.2):
        objs += transform_objs(props.red_lantern(), loc=(x, -hd - 1.3, f1 - 0.1))
    objs.append(util.collider("InnBody", (w + 0.5, d + 0.5, f2 + 0.3), (0, 0, (f2 + 0.3) / 2)))
    for x in xs:
        objs.append(util.collider("InnPost", (0.34, 0.34, f1), (x, -hd - 1.3, f1 / 2)))
    return objs


def market_stall(seed=7):
    """Awninged stall with a table of produce, baskets, cloth bolts and jars."""
    rnd = random.Random(seed)
    m = town_kit()
    awn = util.material("awning", canvas("#e4dccb", 512, 465, stripes="#3f5f8a"), double_sided=True,
                        normal_strength=0.4)
    basket = util.material("basket", woven("#a8834a"), normal_strength=0.8)
    produce = [util.material(n, glaze(c, 128, 542 + k), normal_strength=0.1)
               for k, (n, c) in enumerate((("cabbage", "#6f9a3c"), ("oranges", "#e0842a"), ("peppers", "#b8261c"),
                                           ("radish", "#e8e2d0")))]
    silk = [util.material(n, tex.silk(a, b, 256, 30 + k), normal_strength=0.3)
            for k, (n, a, b) in enumerate((("bolt_red", "#9e2a2a", "#c65a4a"), ("bolt_blue", "#2c4f7a", "#5a7fa8"),
                                           ("bolt_jade", "#3d7a5f", "#77b08e")))]
    jar = util.material("celadon", glaze("#8fb3a0", 256, 545), normal_strength=0.2)
    objs = []
    bm = bmesh.new()
    bevel_box(bm, (2.6, 1.1, 0.08), loc=(0, 0, 0.86), bevel=0.02)
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (0.08, 0.08, 0.82), loc=(sx * 1.2, sy * 0.45, 0.41))
    util.box(bm, (2.5, 0.9, 0.04), loc=(0, 0, 0.25))
    for sx in (-1, 1):
        util.cylinder(bm, 0.045, 0.045, 2.6, loc=(sx * 1.35, 0.75, 1.3), segs=8)
        util.cylinder(bm, 0.045, 0.045, 2.1, loc=(sx * 1.35, -0.85, 1.05), segs=8)
    util.box(bm, (0.4, 0.4, 0.45), loc=(0.6, 1.2, 0.22))
    objs.append(obj("StallWood", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    nx, ny = 8, 5
    grid = []
    for j in range(ny + 1):
        t = j / ny
        row = []
        for i in range(nx + 1):
            x = -1.5 + 3.0 * i / nx
            y = 0.85 - 1.95 * t
            z = 2.62 - 0.55 * t - 0.12 * math.sin(math.pi * i / nx) * math.sin(math.pi * t)
            row.append(bm.verts.new(V((x, y, z))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop in f.loops:
                co = loop.vert.co
                loop[uv].uv = (co.x / 3.0, co.y / 2.0)
    for i in range(nx):
        a, b = grid[ny][i].co, grid[ny][i + 1].co
        mid = (a + b) / 2 + V((0, -0.02, -0.28))
        vs = [bm.verts.new(a.copy()), bm.verts.new(b.copy()), bm.verts.new(mid)]
        f = bm.faces.new(vs)
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = (co.x / 3.0, co.z / 2.0)
    objs.append(util.mesh_object("StallAwning", bm, awn, smooth=True))
    bm_b, bm_p = bmesh.new(), [bmesh.new() for _ in produce]
    for k, x in enumerate((-0.85, 0.0, 0.85)):
        util.lathe(bm_b, [(0.001, 0.9), (0.28, 0.9), (0.36, 1.08), (0.34, 1.1), (0.26, 0.96)], segs=16,
                   loc=(x, -0.1, 0.0), cap_bottom=True)
        kind = (k + seed) % len(produce)
        for q in range(9):
            a = rnd.uniform(0, 2 * math.pi)
            r = rnd.uniform(0, 0.2)
            rr = 0.11 if kind == 0 else 0.07
            util.sphere(bm_p[kind], rr, loc=(x + math.cos(a) * r, -0.1 + math.sin(a) * r, 1.02 + rnd.uniform(0, 0.08)),
                        segs=8, rings=6)
    objs.append(obj("StallBaskets", bm_b, basket, uv=3.0, smooth=True))
    for k, b in enumerate(bm_p):
        if len(b.verts):
            objs.append(obj(f"StallProduce{k}", b, produce[k], uv=2.0, smooth=True))
        else:
            b.free()
    for k, sm in enumerate(silk):
        bm = bmesh.new()
        util.cylinder(bm, 0.1, 0.1, 0.9, loc=(-0.6 + k * 0.28, 0.32, 1.0), segs=12,
                      rot=Matrix.Rotation(R(90), 4, "X") @ Matrix.Rotation(R(rnd.uniform(-8, 8)), 4, "Y"))
        objs.append(obj(f"StallBolt{k}", bm, sm, uv=2.0, smooth=True))
    bm = bmesh.new()
    for k in range(2):
        util.lathe(bm, [(0.001, 0.0), (0.1, 0.0), (0.16, 0.12), (0.14, 0.26), (0.06, 0.32), (0.07, 0.36)], segs=12,
                   loc=(0.95 - k * 0.3, 0.3, 0.9), cap_bottom=True)
    objs.append(obj("StallJars", bm, jar, uv=2.0, smooth=True))
    objs.append(util.collider("StallCol", (2.8, 1.3, 1.0), (0, 0, 0.5)))
    for sx in (-1, 1):
        objs.append(util.collider("StallPost", (0.2, 0.2, 2.2), (sx * 1.35, -0.85, 1.1)))
    return objs


def village_well():
    """Octagonal stone well with a windlass, bucket and a little tiled roof."""
    m = town_kit()
    dark_water = util.material("well_water", tex.water(256, 164), normal_strength=0.3)
    objs = []
    bm = bmesh.new()
    util.lathe(bm, [(1.0, 0.0), (1.0, 0.7), (0.96, 0.8), (0.64, 0.8), (0.6, 0.72), (0.6, -0.9)], segs=8)
    bmesh.ops.transform(bm, matrix=Matrix.Rotation(R(22.5), 4, "Z"), verts=bm.verts)
    bevel_box(bm, (2.6, 2.6, 0.12), loc=(0, 0, 0.0), bevel=0.04)
    objs.append(obj("WellCurb", bm, m["stone"], uv=0.8))
    bm = bmesh.new()
    util.cylinder(bm, 0.62, 0.62, 0.02, loc=(0, 0, -0.5), segs=16)
    objs.append(obj("WellWater", bm, dark_water, uv=0.5))
    bm = bmesh.new()
    for sx in (-1, 1):
        bevel_box(bm, (0.16, 0.16, 2.3), loc=(sx * 1.12, 0, 1.15), bevel=0.02)
    util.cylinder(bm, 0.12, 0.12, 1.9, loc=(0, 0, 1.45), segs=12, rot=Matrix.Rotation(R(90), 4, "Y"))
    util.box(bm, (0.06, 0.06, 0.4), loc=(1.3, 0, 1.3))
    util.box(bm, (0.2, 0.05, 0.05), loc=(1.4, 0, 1.12))
    util.lathe(bm, [(0.001, 0.8), (0.14, 0.8), (0.17, 1.08), (0.18, 1.1)], segs=12, loc=(0.75, 0.62, 0.0),
               cap_bottom=True)
    objs.append(obj("WellWood", bm, m["planks"], uv=1.0, smooth=True))
    bm = bmesh.new()
    util.tube(bm, [V((0.1, 0.0, 1.35)), V((0.1, 0.0, 0.2))], 0.012, n=5)
    util.tube(bm, [V((0.75, 0.62, 1.12)), V((0.62, 0.62, 1.3)), V((0.88, 0.62, 1.3)), V((0.75, 0.62, 1.12))], 0.01, n=4)
    objs.append(obj("WellRope", bm, m["rope"], uv=3.0, smooth=True))
    roof, _ = gable_roof("WellRoof", 1.5, 0.95, 0.6, m, 2.3, nx=8, ny=4, lift=0.1, thick=0.08)
    objs += roof
    tmp = bmesh.new()
    util.lathe(tmp, [(1.05, 0.0), (1.05, 0.8)], segs=8)
    objs.append(convex_mesh("WellCol", tmp))
    for sx in (-1, 1):
        objs.append(util.collider("WellPost", (0.2, 0.2, 2.3), (sx * 1.12, 0, 1.15)))
    return objs


def town_gate():
    """Brick gate piers with a timber gatehouse and a tiled hip roof over a 5 m opening."""
    m = town_kit()
    plaque = util.material("gate_plaque", signboard(512, 565, 2, "#2a1c14", "#e3c06a", vertical=False),
                           normal_strength=0.4)
    objs = []
    ow, pw, pd, ph = 5.0, 3.0, 3.2, 5.2
    bm_b, bm_s = bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        x = sx * (ow / 2 + pw / 2)
        bevel_box(bm_s, (pw + 0.2, pd + 0.2, 0.5), loc=(x, 0, 0.25), bevel=0.04)
        util.box(bm_b, (pw, pd, ph - 0.5), loc=(x, 0, 0.5 + (ph - 0.5) / 2))
        bevel_box(bm_s, (pw + 0.15, pd + 0.15, 0.2), loc=(x, 0, ph - 0.1), bevel=0.03)
    objs.append(obj("GatePiers", bm_b, m["brick"], uv=0.5))
    objs.append(obj("GateStone", bm_s, m["stone"], uv=0.7))
    bm = bmesh.new()
    util.box(bm, (ow + 2 * pw + 0.4, pd + 0.2, 0.4), loc=(0, 0, ph + 0.2))
    util.box(bm, (ow + 0.2, 0.4, 0.5), loc=(0, -pd / 2 + 0.2, ph - 0.25))
    util.box(bm, (ow + 0.2, 0.4, 0.5), loc=(0, pd / 2 - 0.2, ph - 0.25))
    for x in np.linspace(-(ow / 2 + pw) + 0.2, ow / 2 + pw - 0.2, 5):
        for y in (-1.2, 1.2):
            util.box(bm, (0.22, 0.22, 2.6), loc=(x, y, ph + 1.7))
    objs.append(obj("GateTimber", bm, m["pillar"], uv=1.0))
    bm = bmesh.new()
    top = ph + 3.0
    for y in (-1.2, 1.2):
        util.box(bm, (ow + 2 * pw + 0.2, 0.3, 0.35), loc=(0, y, top))
        util.box(bm, (ow + 2 * pw, 0.1, 0.08), loc=(0, y * 1.1, ph + 1.3))
        for x in np.linspace(-(ow / 2 + pw) + 0.2, ow / 2 + pw - 0.2, 29):
            util.box(bm, (0.05, 0.05, 0.9), loc=(x, y * 1.1, ph + 0.85))
    for sx in (-1, 1):
        util.box(bm, (0.3, 2.7, 0.35), loc=(sx * (ow / 2 + pw - 0.2), 0, top))
    objs.append(obj("GateBeams", bm, m["beam"], uv=1.0))
    bm = bmesh.new()
    for y in (-1.21, 1.21):
        for i in range(4):
            x0 = -(ow / 2 + pw) + 0.35 + i * (ow + 2 * pw - 0.4) / 4
            x1 = x0 + (ow + 2 * pw - 0.4) / 4 - 0.25
            panel(bm, x0, x1, y * 1.0, ph + 1.5, top - 0.25, 2, flip=y > 0)
    objs.append(util.mesh_object("GateLattice", bm, m["lattice"], smooth=False))
    objs += arch.rect_roof("GateRoof", 0, 0, ow / 2 + pw + 0.9, 2.3, 2.0, m, base_z=top + 0.15, lift=0.45,
                           lift_len=1.4, curve=1.6, flare=0.35, per_edge=14, rows=10)
    bm = bmesh.new()
    for sx in (-1, 1):
        hinge = V((sx * ow / 2, pd / 2 - 0.3, 0))
        rot = Matrix.Translation(hinge) @ Matrix.Rotation(R(-sx * 95), 4, "Z")
        tmp_bm = bmesh.new()
        bevel_box(tmp_bm, (ow / 2 - 0.1, 0.14, ph - 0.7), loc=(-sx * (ow / 4), 0, (ph - 0.7) / 2 + 0.05), bevel=0.02)
        for r_ in range(5):
            for c in range(4):
                util.sphere(tmp_bm, 0.04, loc=(-sx * (0.35 + c * 0.55), -0.08, 0.6 + r_ * 0.8), segs=6, rings=4)
        bmesh.ops.transform(tmp_bm, matrix=rot, verts=tmp_bm.verts)
        merge(bm, tmp_bm)
    objs.append(obj("GateDoors", bm, m["door"], uv=1.0))
    bm = bmesh.new()
    panel(bm, -1.1, 1.1, -pd / 2 - 0.02, ph - 0.45, ph + 0.35)
    objs.append(util.mesh_object("GatePlaque", bm, plaque, smooth=False))
    for sx in (-1, 1):
        objs.append(util.collider("GatePier", (pw, pd, ph + 5), (sx * (ow / 2 + pw / 2), 0, (ph + 5) / 2)))
        objs.append(util.collider("GateDoor", (0.2, ow / 2, ph - 0.7), (sx * (ow / 2 - 0.15), pd / 2 - 0.3 + ow / 4,
                                                                        (ph - 0.7) / 2)))
    objs.append(util.collider("GateHouse", (ow + 2 * pw, pd, 5.0), (0, 0, ph + 2.5)))
    return objs


def town_wall(length=8.0):
    """Rammed-earth town wall segment (along X): brick plinth, battered body, crenellated parapet."""
    m = town_kit()
    objs = []
    t0, t1, h = 1.9, 1.5, 4.5
    bm = bmesh.new()
    util.box(bm, (length, t0 + 0.1, 0.9), loc=(0, 0, 0.45))
    util.box(bm, (length, 0.42, 0.55), loc=(0, -t1 / 2 + 0.21, h + 0.27))
    for k in range(4):
        util.box(bm, (length / 4 - 0.8, 0.42, 0.55), loc=(-length / 2 + length / 8 + k * length / 4, -t1 / 2 + 0.21,
                                                          h + 0.82))
    util.box(bm, (length, 0.3, 0.45), loc=(0, t1 / 2 - 0.15, h + 0.22))
    objs.append(obj("WallBrick", bm, m["brick"], uv=0.5))
    bm = bmesh.new()
    outline = [(-t0 / 2, 0.9), (t0 / 2, 0.9), (t1 / 2, h), (-t1 / 2, h)]
    tmp = bmesh.new()
    extrude_outline(tmp, outline, -length / 2, length / 2)
    bmesh.ops.transform(tmp, matrix=Matrix.Rotation(R(90), 4, "Z"), verts=tmp.verts)
    merge(bm, tmp)
    body = obj("WallEarth", bm, m["earth_wall"], uv=0.35)
    objs.append(body)
    bm = bmesh.new()
    util.box(bm, (length, 0.55, 0.08), loc=(0, t1 / 2 - 0.15, h + 0.48))
    for k in range(4):
        util.box(bm, (length / 4 - 0.7, 0.55, 0.08), loc=(-length / 2 + length / 8 + k * length / 4, -t1 / 2 + 0.21,
                                                          h + 1.13))
    objs.append(obj("WallCoping", bm, m["tiles"], uv=0.8))
    objs.append(util.collider("WallCol", (length, t0 + 0.1, h + 1.2), (0, 0, (h + 1.2) / 2)))
    return objs


def watchtower():
    """Timber watchtower (~9.5 m): splayed log legs, braces, railed platform, tiled roof, ladder."""
    m = town_kit()
    objs = []
    base_h, top_h = 1.7, 1.3
    pz = 7.0
    bm = bmesh.new()
    corners = [(sx, sy) for sx in (-1, 1) for sy in (-1, 1)]
    for sx, sy in corners:
        util.tube(bm, [V((sx * base_h, sy * base_h, -0.2)), V((sx * top_h, sy * top_h, pz + 2.6))], 0.14, n=8)
    for z0, z1 in ((0.6, 3.6), (3.6, 6.6)):
        f0 = base_h + (top_h - base_h) * z0 / pz
        f1 = base_h + (top_h - base_h) * z1 / pz
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            util.tube(bm, [V((ax * f0, ay * f0, z0)), V((bx * f1, by * f1, z1))], 0.06, n=6)
            util.tube(bm, [V((bx * f0, by * f0, z0)), V((ax * f1, ay * f1, z1))], 0.06, n=6)
            util.tube(bm, [V((ax * f1, ay * f1, z1)), V((bx * f1, by * f1, z1))], 0.07, n=6)
    # ladder on the inner (+Y) side
    for sx in (-0.3, 0.3):
        util.tube(bm, [V((sx, 2.8, 0.0)), V((sx, 1.45, pz + 0.9))], 0.04, n=6)
    for k in range(17):
        t = (k + 0.5) / 17
        p = V((0, 2.8, 0.0)).lerp(V((0, 1.45, pz + 0.9)), t)
        util.tube(bm, [p + V((-0.3, 0, 0)), p + V((0.3, 0, 0))], 0.025, n=5)
    objs.append(obj("TowerLogs", bm, m["log"], uv=1.2, smooth=True))
    bm = bmesh.new()
    util.box(bm, (3.4, 3.4, 0.14), loc=(0, 0, pz))
    util.box(bm, (3.0, 0.3, 0.3), loc=(0, -1.35, pz - 0.2))
    util.box(bm, (3.0, 0.3, 0.3), loc=(0, 1.35, pz - 0.2))
    for (ax, ay, bx, by) in ((-1.65, -1.65, 1.65, -1.65), (1.65, -1.65, 1.65, 1.65), (-1.65, 1.65, -1.65, -1.65)):
        util.tube(bm, [V((ax, ay, pz + 1.0)), V((bx, by, pz + 1.0))], 0.05, n=6)
        util.tube(bm, [V((ax, ay, pz + 0.5)), V((bx, by, pz + 0.5))], 0.035, n=6)
    util.tube(bm, [V((1.65, 1.65, pz + 1.0)), V((0.5, 1.65, pz + 1.0))], 0.05, n=6)
    util.tube(bm, [V((-1.65, 1.65, pz + 1.0)), V((-0.5, 1.65, pz + 1.0))], 0.05, n=6)
    objs.append(obj("TowerDeck", bm, m["planks"], uv=1.0))
    rm = {"tiles": m["tiles"], "wood": m["wood"], "ridge": m["ridge"], "gold": m["ridge"]}
    objs += arch.poly_roof("TowerRoof", 0, 0, 2.6 * math.sqrt(2), 4, 1.6, rm, base_z=pz + 2.55, rot=R(45), lift=0.3,
                           lift_len=0.9, curve=1.5, flare=0.3, per_edge=10, rows=8, ornaments=False)
    objs += transform_objs(props.red_lantern(), loc=(1.2, -1.2, pz + 2.45))
    for sx, sy in corners:
        objs.append(util.collider("TowerLeg", (0.4, 0.4, pz), (sx * (base_h + top_h) / 2, sy * (base_h + top_h) / 2,
                                                               pz / 2)))
    objs.append(util.collider("TowerDeck", (3.4, 3.4, 0.3), (0, 0, pz)))
    return objs


def tombstones(seed=67):
    """A family plot: grave mounds with inscribed headstones and an incense stone."""
    rnd = random.Random(seed)
    m = town_kit()
    ins = inscription(256, 472, "#7c7b72", cols=2, rows=5)
    face = util.material("headstone", ins, normal_strength=1.0)
    mm = tex.grass(256, 122)
    mm["albedo"] = tex.lerp(mm["albedo"], earth("#6d5a40", 256, 424)["albedo"], 0.55)
    mound_m = util.material("grave_mound", mm, normal_strength=0.6)
    ember = glow_mat("ember", "#ff6a2a", 6.0)
    objs = []
    bm_t, bm_b, bm_m = bmesh.new(), bmesh.new(), bmesh.new()
    spots = [(-2.2, 0.0), (0.0, 0.3), (2.2, 0.0), (-1.1, 3.0), (1.3, 3.2)]
    for k, (x, y) in enumerate(spots):
        tilt = rnd.uniform(-6, 6)
        rock(bm_m, (x, y + 1.3, 0.0), (0.85, 1.1, 0.55), seed + k, 0.12, 2)
        bevel_box(bm_b, (0.8, 0.4, 0.22), loc=(x, y, 0.11), bevel=0.03)
        tmp = bmesh.new()
        h = rnd.uniform(0.75, 1.0)
        extrude_outline(tmp, arc_outline(0.55, h - 0.15, 8, 0.0), -0.07, 0.07, uv_front=(-0.275, 0.0, 0.55, h))
        bmesh.ops.transform(tmp, matrix=Matrix.Translation(V((x, y, 0.2))) @ Matrix.Rotation(R(tilt), 4, "Y")
                            @ Matrix.Rotation(R(rnd.uniform(-4, 4)), 4, "X"), verts=tmp.verts)
        merge(bm_t, tmp)
    objs.append(util.mesh_object("Headstones", bm_t, face, smooth=False))
    objs.append(obj("GraveBases", bm_b, m["stone"], uv=1.0))
    objs.append(obj("GraveMounds", bm_m, mound_m, uv=0.8, smooth=True))
    bm, bm_e = bmesh.new(), bmesh.new()
    bevel_box(bm, (0.6, 0.45, 0.35), loc=(0.2, -1.5, 0.17), bevel=0.04)
    for k in range(3):
        x = 0.08 + k * 0.12
        util.tube(bm, [V((x, -1.5, 0.34)), V((x + 0.02, -1.5, 0.62))], 0.006, n=4)
        util.sphere(bm_e, 0.012, loc=(x + 0.02, -1.5, 0.63), segs=6, rings=4)
    for x in (-0.6, 1.0):
        util.lathe(bm, [(0.001, 0.0), (0.08, 0.0), (0.12, 0.06), (0.13, 0.08)], segs=10, loc=(x, -1.2, 0.0),
                   cap_bottom=True)
    objs.append(obj("IncenseStone", bm, m["stone"], uv=1.2))
    objs.append(obj("IncenseEmbers", bm_e, ember, smooth=True))
    for k, (x, y) in enumerate(spots):
        objs.append(util.collider("Grave", (1.6, 2.4, 0.9), (x, y + 1.1, 0.45)))
    return objs


def river_dock(length=12.0, width=3.2):
    """Wooden pier (extends along -Y over the water) with a moored sampan and a lantern post."""
    m = town_kit()
    mat_m = util.material("boat_matting", woven("#8a6a3c", 256, 552), double_sided=True, normal_strength=0.6)
    hull_m = util.material("boat_hull", planks("#4a3a2a", 512, 403, boards=8), normal_strength=0.7)
    rnd = random.Random(71)
    objs = []
    bm = bmesh.new()
    n = int((length + 0.8) / 0.32)
    for k in range(n):
        y = 0.8 - (k + 0.5) * (length + 0.8) / n
        util.box(bm, (width + rnd.uniform(-0.1, 0.1), 0.28, 0.08), loc=(rnd.uniform(-0.04, 0.04), y, 0.01),
                 rot=Matrix.Rotation(R(rnd.uniform(-1, 1)), 4, "Z"))
    objs.append(obj("DockDeck", bm, m["old_planks"], uv=1.0))
    bm = bmesh.new()
    for x in (-width / 2 + 0.2, width / 2 - 0.2):
        util.box(bm, (0.2, length + 0.6, 0.25), loc=(x, -length / 2 + 0.5, -0.16))
    for k in range(5):
        y = -1.0 - k * (length - 1.2) / 4
        for x in (-width / 2 + 0.05, width / 2 - 0.05):
            util.tube(bm, [V((x, y, -4.0)), V((x, y, 0.35 if k == 4 else -0.02))], 0.14, n=8)
        util.box(bm, (width, 0.2, 0.2), loc=(0, y, -0.35))
    objs.append(obj("DockPiles", bm, m["log"], uv=1.0, smooth=True))
    bm = bmesh.new()
    for x in (-width / 2 + 0.05, width / 2 - 0.05):
        pts = [V((x, -1.0 - k * (length - 1.2) / 4, 0.35)) for k in range(5)]
        for a, b in zip(pts[:-1], pts[1:]):
            mid = (a + b) / 2 + V((0, 0, -0.18))
            util.tube(bm, util.catmull([a, mid, b], 4), 0.022, n=5)
    for k in range(3):
        a = k * 2.2
        ring = [V((0.9 + 0.22 * math.cos(t), -length + 1.0 + 0.22 * math.sin(t),
                   0.08 + 0.05 * k)) for t in np.linspace(0, 2 * math.pi, 13)]
        util.tube(bm, ring, 0.035, n=5, closed_ends=False)
    util.tube(bm, [V((width / 2 - 0.05, -length + 1.4, 0.3)), V((width / 2 + 0.6, -length + 1.6, -0.6)),
                   V((width / 2 + 1.0, -length + 2.2, -1.0))], 0.02, n=5)
    objs.append(obj("DockRopes", bm, m["rope"], uv=3.0, smooth=True))
    # lantern post
    bm = bmesh.new()
    util.box(bm, (0.16, 0.16, 2.6), loc=(-width / 2 + 0.1, -length + 0.4, 1.3))
    util.box(bm, (0.9, 0.1, 0.1), loc=(-width / 2 + 0.5, -length + 0.4, 2.5))
    objs.append(obj("DockPost", bm, m["wood"], uv=1.0))
    objs += transform_objs(props.red_lantern(), loc=(-width / 2 + 0.85, -length + 0.4, 2.45))
    # moored sampan beside the pier
    bm = bmesh.new()
    rings = []
    L, B = 6.4, 1.7
    for k in range(11):
        t = k / 10
        y = -L / 2 + L * t
        wdt = B / 2 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.7
        zb = -0.55 + 0.35 * (abs(2 * t - 1) ** 3)
        top = 0.0 + 0.35 * (abs(2 * t - 1) ** 2)
        rings.append([V((-wdt, y, top)), V((-wdt * 0.8, y, zb + 0.1)), V((0, y, zb)), V((wdt * 0.8, y, zb + 0.1)),
                      V((wdt, y, top))])
    util.loft(bm, rings, closed=False, uv_scale=(1.0, 0.5))
    deck = [[V((-B / 2 * 0.85 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.7, -L / 2 + L * t,
                0.0 + 0.35 * (abs(2 * t - 1) ** 2) - 0.1)),
             V((B / 2 * 0.85 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.7, -L / 2 + L * t,
                0.0 + 0.35 * (abs(2 * t - 1) ** 2) - 0.1))]
            for t in np.linspace(0, 1, 11)]
    util.loft(bm, deck, closed=False)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    hull = util.mesh_object("SampanHull", bm, hull_m, smooth=False)
    hull.data.materials[0].use_backface_culling = False
    bm = bmesh.new()
    arc = [V((0.75 * math.cos(a), 0, 0.05 + 0.85 * math.sin(a))) for a in np.linspace(0, math.pi, 10)]
    util.loft(bm, [[p + V((0, y, 0)) for p in arc] for y in (-1.1, 1.1)], closed=False, uv_scale=(3.0, 1.0))
    canopy = util.mesh_object("SampanCanopy", bm, mat_m, smooth=True)
    boat = [hull, canopy]
    for o in boat:
        o.location = (width / 2 + 1.25, -length + 4.2, -1.25)
        o.rotation_euler = (0, R(-3), R(4))
        util.apply_transform(o)
    objs += boat
    objs.append(util.collider("DockWalk", (width, length + 0.8, 0.4), (0, -length / 2 + 0.4, -0.15)))
    for x in (-width / 2 - 0.1, width / 2 + 0.1):
        objs.append(util.collider("DockRail", (0.2, length - 0.6, 1.6), (x, -length / 2 - 0.3, 0.8)))
    objs.append(util.collider("DockEnd", (width + 0.4, 0.2, 1.6), (0, -length + 0.05, 0.8)))
    return objs


def cart():
    """Two-wheeled hand cart loaded with sacks and a jar."""
    m = town_kit()
    sack = util.material("sack", canvas("#a08d68", 256, 463), normal_strength=0.6)
    objs = []
    bm = bmesh.new()
    util.box(bm, (1.25, 2.0, 0.08), loc=(0, 0, 0.78))
    for sx in (-1, 1):
        util.box(bm, (0.06, 2.0, 0.3), loc=(sx * 0.62, 0, 0.95))
        util.tube(bm, [V((sx * 0.5, 1.0, 0.76)), V((sx * 0.5, 2.7, 0.62))], 0.04, n=6)
    util.box(bm, (1.25, 0.06, 0.3), loc=(0, -1.0, 0.95))
    util.box(bm, (0.06, 0.06, 0.62), loc=(0, 1.7, 0.36), rot=Matrix.Rotation(R(-12), 4, "X"))
    util.box(bm, (1.4, 0.1, 0.1), loc=(0, 0.1, 0.62))
    objs.append(obj("CartBed", bm, m["planks"], uv=1.0))
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * 0.78
        ring = [V((x, 0.1 + 0.55 * math.cos(a), 0.55 + 0.55 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 25)]
        util.tube(bm, ring, (0.05, 0.035), n=6, closed_ends=False)
        util.cylinder(bm, 0.1, 0.1, 0.2, loc=(x, 0.1, 0.55), segs=10, rot=Matrix.Rotation(R(90), 4, "Y"))
        for k in range(10):
            a = 2 * math.pi * k / 10
            util.tube(bm, [V((x, 0.1, 0.55)), V((x, 0.1 + 0.52 * math.cos(a), 0.55 + 0.52 * math.sin(a)))], 0.022, n=4)
    objs.append(obj("CartWheels", bm, m["wood"], uv=1.5, smooth=True))
    bm = bmesh.new()
    for k, (x, y) in enumerate(((-0.28, -0.5), (0.28, -0.45), (0.0, 0.2), (-0.25, 0.65))):
        rock(bm, (x, y, 1.0), (0.26, 0.38, 0.2), k + 31, 0.15, 2)
    objs.append(obj("CartSacks", bm, sack, uv=1.2, smooth=True))
    bm = bmesh.new()
    util.lathe(bm, [(0.001, 0.0), (0.14, 0.0), (0.22, 0.18), (0.2, 0.36), (0.1, 0.46), (0.11, 0.5)], segs=12,
               loc=(0.3, 0.72, 0.82), cap_bottom=True)
    objs.append(obj("CartJar", bm, util.material("clay_glaze", glaze("#6b4a32"), normal_strength=0.2), uv=2.0,
                    smooth=True))
    objs.append(util.collider("CartCol", (1.8, 2.2, 1.2), (0, 0.1, 0.6)))
    return objs


def town_terrain():
    """The Qingshi river valley (tools/maps/qingshi_town.py): one ground mesh with the streets, squares,
    fields and river bed as regions, the river, canal and ponds, the river's stone embankment."""
    from maps import qingshi_town as T
    objs = ground_terrain(T.G, "TownGround", _water_mats())
    m = {"blocks": util.material("stone_blocks", stone_blocks("#8f8a80", 512, 492, rows=6, cols=3, moss=0.2),
                                 normal_strength=1.0)}

    def open_bank(z):
        """Where the embankment is broken: the canal mouth, the mill race, the docks."""
        return abs(z - T.CANAL_Z) < 6.5 or abs(z + 184) < 4.0 or abs(z + 144) < 4.0
    bank = []
    for k in range(len(T.RIVER.pts)):
        x, z = T.RIVER.pts[k]
        tx, tz = T.RIVER.tangent(min(k / (len(T.RIVER.pts) - 1), 0.999))
        bank.append((x + tz * T.BANK, z - tx * T.BANK, tx, tz))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    prev = None
    dist = 0.0
    for idx, (x, z, tx, tz) in enumerate(bank):
        if idx:
            dist += math.hypot(x - bank[idx - 1][0], z - bank[idx - 1][1])
        ex, ez = tz, -tx
        if open_bank(z):
            prev = None
            continue
        # the coping stands 12 cm proud of the ground (a curb, never coplanar with it)
        row = [bm.verts.new(V((x - ex * 0.45, -(z - ez * 0.45), -3.6))), bm.verts.new(V((x - ex * 0.45,
                                                                                         -(z - ez * 0.45), 0.12))),
               bm.verts.new(V((x + ex * 0.45, -(z + ez * 0.45), 0.12)))]
        if prev:
            for c in range(2):
                f = bm.faces.new((prev[1][c], prev[1][c + 1], row[c + 1], row[c]))
                for loop in f.loops:
                    co = loop.vert.co
                    loop[uv].uv = ((dist if loop.vert in row else prev[0]) * 0.3, co.z * 0.3 if c == 0 else co.x * 0.3)
        prev = (dist, row)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    objs.append(util.mesh_object("Embankment", bm, m["blocks"], smooth=False))
    # invisible railing along the bank (gap for the dock)
    for (a, b) in zip(bank[:-1], bank[1:]):
        steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 4.0))
        for k in range(steps):
            p0 = (a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps)
            p1 = (a[0] + (b[0] - a[0]) * (k + 1) / steps, a[1] + (b[1] - a[1]) * (k + 1) / steps)
            cz = (p0[1] + p1[1]) / 2
            if abs(cz - T.DOCK_Z) < 2.4 or abs(cz - 108) < 2.4 or open_bank(cz) or abs(cz) > T.SPAN:
                continue
            ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            ang = math.atan2(-(p1[1] - p0[1]), p1[0] - p0[0])
            objs.append(util.collider("BankRail", (ln + 0.05, 0.5, 3.0), ((p0[0] + p1[0]) / 2 - 0.2, -cz, 1.0),
                                      rot_z=ang))
    objs += bounds_colliders(T.PLAY + 14, T.PLAY + 14)
    return objs


# --------------------------------------------------------------------------
# ground terrain of the enlarged maps (tools/maps/terrain.py Ground)
# --------------------------------------------------------------------------
def tea_rows(size=512, seed=611):
    """Contour rows of clipped tea bushes over dark soil (rows along u)."""
    u, v = tex.grid(size)
    soil = earth("#4e3d2a", size, seed, 0.15)
    rows = 4
    fv = (v * rows) % 1.0
    bush = tex.sstep(0.46, 0.2, np.abs(fv - 0.5))
    leaf = tex.fbm(size, 64, 3, 0.55, seed + 1)
    n = tex.fbm(size, 6, 4, 0.5, seed + 2)
    green = tex.lerp(tex.srgb("#2f5a24"), tex.srgb("#7fa43c"), leaf * 0.6 + n * 0.4)
    col = tex.lerp(soil["albedo"], green, np.clip(bush * 1.3, 0, 1)[..., None])
    return tex.result(col, 0.8, 0.0, bush * 0.8 + leaf * 0.3)


def gravel(color="#9c968a", size=512, seed=621):
    base = pebbles(size, seed, 40, color)
    n = tex.fbm(size, 6, 4, 0.5, seed + 3)
    base["albedo"] = base["albedo"] * (0.85 + 0.25 * n)[..., None]
    return base


def mud(size=512, seed=631, color="#3d3a22", scum="#6f8a2a"):
    """Wet marsh mud with algae scum and puddle sheen."""
    n = tex.fbm(size, 6, 5, 0.55, seed)
    s = tex.fbm(size, 12, 4, 0.5, seed + 1)
    col = tex.srgb(color) * (0.7 + 0.5 * n)[..., None]
    sc = tex.sstep(0.55, 0.7, s)
    col = tex.lerp(col, tex.srgb(scum), (sc * 0.6)[..., None])
    wet = tex.sstep(0.35, 0.2, n)
    return tex.result(col * (1 - 0.3 * wet)[..., None], 0.9 - 0.7 * wet, 0.0, n * 0.4 + sc * 0.2)


def ash(size=512, seed=641):
    """Grey volcanic ash with drifted ridges and cinders."""
    n = tex.fbm(size, 6, 6, 0.55, seed)
    ripple = np.abs(np.sin((tex.fbm(size, 3, 3, 0.5, seed + 1) * 9 + tex.grid(size)[1] * 24) * math.pi))
    cind = tex.sstep(0.8, 0.9, tex.fbm(size, 64, 2, 0.5, seed + 2))
    col = tex.lerp(tex.srgb("#6a6461"), tex.srgb("#a29a93"), (n * 0.7 + ripple * 0.3)[..., None])
    col = tex.lerp(col, tex.srgb("#1c1818"), (cind * 0.8)[..., None])
    return tex.result(col, 0.95, 0.0, n * 0.4 + ripple * 0.2 + cind * 0.3)


def sand(color="#d9d2c0", size=512, seed=651):
    n = tex.fbm(size, 8, 5, 0.55, seed)
    grit = tex.fbm(size, 128, 2, 0.5, seed + 1)
    col = tex.srgb(color) * (0.85 + 0.2 * n + 0.1 * (grit - 0.5))[..., None]
    return tex.result(col, 0.85, 0.0, n * 0.3 + grit * 0.3)


def _bone_ground(size=512, seed=661):
    """Dark earth littered with bleached bone shards."""
    from . import realms
    soil = realms.crimson_soil(size, seed)
    shards = tex.sstep(0.82, 0.88, tex.fbm(size, 40, 2, 0.5, seed + 1))
    col = tex.lerp(soil["albedo"], tex.srgb("#d8cfb8"), (shards * 0.85)[..., None])
    return tex.result(col, 0.85, 0.0, soil["height"] * 0.6 + shards * 0.5)


def _ground_palette():
    """Material key -> (material factory, metres per texture repeat, tri-planar)."""
    from . import realms
    return {
        "grass": (lambda: util.material("meadow", tex.grass(1024, 123), normal_strength=0.6), 10.0, False),
        "grass_sect": (lambda: util.material("grass", tex.grass(1024), normal_strength=0.6), 9.0, False),
        "forest": (lambda: util.material("forest_floor", forest_floor(1024), normal_strength=0.8), 10.0, False),
        "moss": (lambda: util.material("moss_floor", tex.foliage("#3d5a2a", 512, 145), normal_strength=0.6), 8.0,
                 False),
        "cliff": (lambda: util.material("crag", crag("#8a8374", 1024, 602, "#5f6b3a"), normal_strength=1.0), 22.0,
                  True),
        "cliff_sect": (lambda: util.material("cliff", tex.cliff("#7d776c", 1024), normal_strength=1.2), 20.0, True),
        "paving": (lambda: util.material("paving", tex.paving("#cdbfa6", 1024, gap=0.007, moss=0.12),
                                         normal_strength=1.0), 4.0, False),
        "paving_old": (lambda: util.material("old_paving", tex.paving("#a09a8a", 512, 82, tiles=4, gap=0.01,
                                                                      moss=0.45), normal_strength=1.0), 4.5, False),
        "street": (lambda: util.material("street_paving", tex.paving("#b0a797", 512, 83, tiles=6, gap=0.008,
                                                                     moss=0.05), normal_strength=1.0), 6.0, False),
        "earth": (lambda: util.material("packed_earth", earth("#a08966", 512, 423, 0.35), normal_strength=0.3), 5.0,
                  False),
        "road": (lambda: util.material("dirt_road", earth("#8f7a58", 512, 424, 0.6), normal_strength=0.4), 5.0,
                 False),
        "dirt": (lambda: util.material("dirt", earth("#6f5a3c", 512, 425, 0.3), normal_strength=0.4), 5.0, False),
        "gravel": (lambda: util.material("gravel", gravel(), normal_strength=1.0), 3.0, False),
        "crops": (lambda: util.material("crops", crops(512), normal_strength=0.8), 4.0, False),
        "tea": (lambda: util.material("tea_rows", tea_rows(512), normal_strength=0.9), 4.0, False),
        "pebbles": (lambda: util.material("pebbles", pebbles(512), normal_strength=1.2), 4.0, False),
        "mud": (lambda: util.material("marsh_mud", mud(512), normal_strength=0.6), 6.0, False),
        "sand": (lambda: util.material("sand", sand(), normal_strength=0.5), 5.0, False),
        "ash": (lambda: util.material("ash", ash(512), normal_strength=0.8), 8.0, False),
        "abyss_soil": (lambda: realms._mat("abyss_soil", realms.crimson_soil(512), 1.4, normal_strength=1.0), 10.0,
                       False),
        "abyss_rock": (lambda: util.material("abyss_rock", realms.basalt(512, 413, "#352c2e"), normal_strength=1.3),
                       11.0, True),
        "abyss_blocks": (lambda: util.material("dark_blocks", realms.dark_blocks(512), normal_strength=1.0), 4.0,
                         False),
        "bone_ground": (lambda: util.material("bone_ground", _bone_ground(512), normal_strength=0.8), 6.0, False),
    }


class _Mesher:
    """Collects polygons (vertex ids + material key) and builds one Blender mesh from them."""

    def __init__(self):
        self.pos = []
        self.ids = {}
        self.polys = []

    def vid(self, x, z, y):
        k = (round(x, 3), round(z, 3))
        i = self.ids.get(k)
        if i is None:
            i = len(self.pos)
            self.ids[k] = i
            self.pos.append((x, z, y))
        return i

    def build(self, name, palette, mats):
        used = sorted({k for _, k, _ in self.polys})
        if not used:
            return None
        remap = {}
        verts, faces, mis, uvs = [], [], [], []
        for poly, key, nrm in self.polys:
            f = []
            for i in poly:
                j = remap.get(i)
                if j is None:
                    j = len(verts)
                    remap[i] = j
                    x, z, y = self.pos[i]
                    verts.append((x, -z, y))
                f.append(j)
            faces.append(f)
            mis.append(used.index(key))
            _, rep, tri = palette[key]
            ax = max(range(3), key=lambda k: abs(nrm[k])) if tri else 2
            for i in poly:
                x, z, y = self.pos[i]
                if ax == 2:
                    uvs += [x / rep, -z / rep]
                elif ax == 0:
                    uvs += [-z / rep, y / rep]
                else:
                    uvs += [x / rep, y / rep]
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.polygons.foreach_set("material_index", mis)
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", uvs)
        for k in used:
            me.materials.append(mats[k])
        me.validate()
        me.update()
        ob = bpy.data.objects.new(name, me)
        util.link(ob)
        me.shade_smooth()
        return ob


def _split_poly(poly, vals, lerp_vert):
    """Split a convex polygon at the zero level of per-vertex values (linear along the edges)."""
    inside, outside = [], []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        va, vb = vals[k], vals[(k + 1) % n]
        (inside if va <= 0 else outside).append(a)
        if (va <= 0) != (vb <= 0):
            m = lerp_vert(a, b, va / (va - vb))
            inside.append(m)
            outside.append(m)
    return inside, outside


def _ccw(poly, table):
    """Order a polygon counter-clockwise seen from above in Blender space (normal +Z). Repeated vertices
    (a cut that lands on a corner snaps onto it) are dropped; None if fewer than three remain."""
    clean = []
    for v in poly:
        if not clean or clean[-1] != v:
            clean.append(v)
    while len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    if len(set(clean)) < 3 or len(set(clean)) != len(clean):
        return None
    poly = clean
    area = 0.0
    n = len(poly)
    for k in range(n):
        ax, az = table[poly[k]][0], -table[poly[k]][1]
        bx, bz = table[poly[(k + 1) % n]][0], -table[poly[(k + 1) % n]][1]
        area += ax * bz - bx * az
    return poly if area > 0 else poly[::-1]


def _mesh_ground_cells(G, i0, j0, i1, j1, heights, mesher, flat=None, only=None, min_len=1.1):
    """Triangulate grid cells [i0, i1) x [j0, j1), refine triangles along the region outlines and
    split every triangle exactly at them (first region wins). With ``flat``/``only`` it meshes a flat
    water surface instead: the parts inside the shape ``only`` at height ``flat``.

    Refinement only ever inserts edge midpoints on the flat triangles of the height field, and the
    decision to split an edge depends on that edge alone, so neighbouring triangles agree (no cracks,
    no T-junctions) and the surface is exactly the collision surface of the plain grid."""
    x0, z0 = G.bounds[0], G.bounds[1]
    s = G.step
    bb = (x0 + i0 * s - 4, z0 + j0 * s - 4, x0 + i1 * s + 4, z0 + j1 * s + 4)
    if only is not None:
        regs = [("water", only)]
    else:
        regs = [(mat, shape) for _, mat, shape in G.regions_near(bb)
                if shape.bbox[0] <= bb[2] and shape.bbox[2] >= bb[0] and shape.bbox[1] <= bb[3]
                and shape.bbox[3] >= bb[1]]
    nreg = len(regs)
    table = {}

    def vert(x, z, y):
        i = mesher.vid(x, z, y)
        if i not in table:
            table[i] = (x, z, y, tuple(shape.sdf(x, z) for _, shape in regs))
        return i

    def node(i, j):
        return vert(x0 + i * s, z0 + j * s, flat if flat is not None else heights[j][i])

    mid_cache = {}

    def midpoint(a, b):
        key = (a, b) if a < b else (b, a)
        if key in mid_cache:
            return mid_cache[key]
        ax, az, ay, sa = table[a]
        bx, bz, by, sb = table[b]
        ln = math.hypot(bx - ax, bz - az)
        m = None
        if ln > min_len:
            for k in range(nreg):
                # split where an outline crosses the edge, or where a narrow band (a path) may pass
                # between its ends
                if (sa[k] > 0) != (sb[k] > 0) or (sa[k] > 0 and sb[k] > 0 and sa[k] + sb[k] < ln * 1.1):
                    m = vert((ax + bx) / 2, (az + bz) / 2, (ay + by) / 2)
                    break
        mid_cache[key] = m
        return m

    leaves = []

    def refine(a, b, c, depth=0):
        mab, mbc, mca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        cnt = (mab is not None) + (mbc is not None) + (mca is not None)
        if cnt == 0 or depth > 8:
            leaves.append((a, b, c))
        elif cnt == 3:
            refine(a, mab, mca, depth + 1)
            refine(mab, b, mbc, depth + 1)
            refine(mca, mbc, c, depth + 1)
            refine(mab, mbc, mca, depth + 1)
        elif cnt == 1:
            if mab is not None:
                refine(a, mab, c, depth + 1)
                refine(mab, b, c, depth + 1)
            elif mbc is not None:
                refine(b, mbc, a, depth + 1)
                refine(mbc, c, a, depth + 1)
            else:
                refine(c, mca, b, depth + 1)
                refine(mca, a, b, depth + 1)
        elif mab is None:
            refine(c, mca, mbc, depth + 1)
            refine(mca, a, mbc, depth + 1)
            refine(a, b, mbc, depth + 1)
        elif mbc is None:
            refine(a, mab, mca, depth + 1)
            refine(mab, b, mca, depth + 1)
            refine(b, c, mca, depth + 1)
        else:
            refine(b, mbc, mab, depth + 1)
            refine(mbc, c, mab, depth + 1)
            refine(c, a, mab, depth + 1)

    for j in range(j0, j1):
        for i in range(i0, i1):
            a, b, c, d = node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1)
            # split along the flatter diagonal
            if abs(table[a][2] - table[c][2]) > abs(table[b][2] - table[d][2]):
                tris = ((a, d, b), (b, d, c))
            else:
                tris = ((a, d, c), (a, c, b))
            for t in tris:
                if only is not None and all(table[v][3][0] > s * 1.5 for v in t):
                    continue
                if flat is None and G.floor is not None and all(table[v][2] < G.floor for v in t):
                    continue        # hidden far below the clouds: nobody can see or reach it
                refine(*t)

    def lerp_vert(a, b, t):
        if t < 1e-3:
            return a
        if t > 1 - 1e-3:
            return b
        ax, az, ay, _ = table[a]
        bx, bz, by, _ = table[b]
        return vert(ax + (bx - ax) * t, az + (bz - az) * t, ay + (by - ay) * t)

    for tri in leaves:
        pa, pb, pc = (table[v] for v in tri)
        ux, uy, uz = pb[0] - pa[0], pb[2] - pa[2], pb[1] - pa[1]
        vx, vy, vz = pc[0] - pa[0], pc[2] - pa[2], pc[1] - pa[1]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / ln, ny / ln, nz / ln
        if ny < 0:
            nx, ny, nz = -nx, -ny, -nz
        nrm_b = (nx, -nz, ny)            # Blender axes, for tri-planar UVs
        poly = list(tri)
        for k in range(nreg):
            vals = [table[v][3][k] for v in poly]
            if all(v_ > 0 for v_ in vals):
                continue
            if all(v_ <= 0 for v_ in vals):
                inside, poly = poly, []
            else:
                inside, poly = _split_poly(poly, vals, lerp_vert)
            if len(inside) >= 3:
                cp = _ccw(inside, table)
                if cp:
                    mesher.polys.append((cp, regs[k][0], nrm_b))
            if len(poly) < 3:
                poly = []
                break
        if poly and only is None:
            cx = sum(table[v][0] for v in poly) / len(poly)
            cz = sum(table[v][1] for v in poly) / len(poly)
            cy = sum(table[v][2] for v in poly) / len(poly)
            cp = _ccw(poly, table)
            if cp:
                mesher.polys.append((cp, G.classify(cx, cz, cy, ny), nrm_b))


def ground_terrain(G, name="Ground", water_mats=None):
    """Chunked height-field terrain of a tools/maps/terrain.Ground. Every chunk is one visible mesh
    with its own trimesh collision ('-col'), whose triangles are split exactly along the paving, road
    and field outlines (so no overlay can z-fight with the ground), plus flat water surfaces without
    collision (water_mats: material key -> factory)."""
    palette = _ground_palette()
    mats = {}

    def mat(k):
        if k not in mats:
            mats[k] = palette[k][0]()
        return mats[k]
    x0, z0, x1, z1 = G.bounds
    s = G.step
    nx, nz = int(round((x1 - x0) / s)), int(round((z1 - z0) / s))
    heights = [[G.height(x0 + i * s, z0 + j * s) for i in range(nx + 1)] for j in range(nz + 1)]
    objs = []
    C = G.chunk
    for cj in range(0, nz, C):
        for ci in range(0, nx, C):
            mesher = _Mesher()
            _mesh_ground_cells(G, ci, cj, min(ci + C, nx), min(cj + C, nz), heights, mesher)
            for key in {k for _, k, _ in mesher.polys}:
                mat(key)
            ob = mesher.build(f"{name}_{ci // C}_{cj // C}-col", palette, mats)
            if ob is not None:
                objs.append(ob)
    for k, (wmat, shape, level) in enumerate(G.waters):
        pal = {"water": (None, 8.0, False)}
        wm = {"water": (water_mats or {})[wmat]()}
        bx0, bz0, bx1, bz1 = shape.inflate(1.0)
        i0, j0 = max(0, int((bx0 - x0) / s)), max(0, int((bz0 - z0) / s))
        i1, j1 = min(nx, int((bx1 - x0) / s) + 1), min(nz, int((bz1 - z0) / s) + 1)
        mesher = _Mesher()
        _mesh_ground_cells(G, i0, j0, i1, j1, heights, mesher, flat=level, only=shape, min_len=1.2)
        ob = mesher.build(f"Water{k}", pal, wm)
        if ob is not None:
            objs.append(ob)
    return objs


def _water_mats():
    return {
        "pond": lambda: util.material("water", tex.water(256), alpha=0.82, normal_strength=0.6),
        "stream": lambda: util.material("stream_water", tex.water(256), alpha=0.78, normal_strength=0.6),
        "river": lambda: util.material("river_water", tex.water(256, 165), alpha=0.85, normal_strength=0.6),
        "lake": lambda: util.material("lake_water", _lake_water(), alpha=0.8, normal_strength=0.5),
        "marsh": lambda: util.material("marsh_water", _marsh_water(), alpha=0.9, normal_strength=0.4,
                                       emission="#4a8a1a", emission_strength=0.25),
    }


def _lake_water():
    w = tex.water(256, 166)
    w["albedo"] = tex.lerp(w["albedo"], tex.srgb("#8ab0b0"), 0.35)
    return w


def _marsh_water():
    w = tex.water(256, 167)
    w["albedo"] = tex.lerp(w["albedo"], tex.srgb("#5a7a1a"), 0.6)
    return w


def sect_terrain():
    """The whole Azure Cloud mountain (tools/maps/sect.py): the old plateau and its terraces."""
    from maps import sect
    return ground_terrain(sect.G, "SectGround", _water_mats())


ASSETS = {
    "terrain": sect_terrain,
    "teleport_array": teleport_array,
    "stone_stele": stone_stele,
    "treasure_chest": treasure_chest,
    "spirit_herb": spirit_herb,
    "spirit_stone": spirit_stone,
    "jade_slip": jade_slip,
    "bronze_bell": bronze_bell,
    # forest
    "forest_terrain": forest_terrain,
    "spring_pool": spring_pool,
    "bamboo_grove": bamboo_grove,
    "fern_cluster": fern_cluster,
    "fallen_log": fallen_log,
    "broken_pillar": broken_pillar,
    "ruin_wall": ruin_wall,
    "stone_archway": stone_archway,
    "ruined_shrine": ruined_shrine,
    "hermit_hut": hermit_hut,
    "campfire": campfire,
    "bandit_tent": bandit_tent,
    "crates": crates,
    "wooden_bridge": wooden_bridge,
    "cave_mouth": cave_mouth,
    # town
    "town_terrain": town_terrain,
    "town_house": town_house,
    "town_house_large": town_house_large,
    "market_stall": market_stall,
    "village_well": village_well,
    "town_gate": town_gate,
    "town_wall": town_wall,
    "watchtower": watchtower,
    "tombstones": tombstones,
    "river_dock": river_dock,
    "cart": cart,
}

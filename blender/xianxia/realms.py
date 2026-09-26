"""Blood Moon Abyss and Celestial Sky Isles assets.

Blood Moon Abyss: canyon terrain carved from black basalt, blood pools, altars,
obelisks, cages, a demon fortress gate and wall, war camp tents and banners,
the patriarch's throne arena and the heart-demon mirror pool.

Celestial Sky Isles: walkable floating islands, jade bridges, a floating
ascension stair, marble ruins, a star-gazing pavilion, a cloud gate, spirit
crystals and the tribulation altar.

Everything faces -Y in Blender (+Z in Godot). Walkable surfaces use trimesh
collision (``*-col`` / ``*-colonly``) or ramps so the player capsule can climb
them without step logic.
"""
import math
import os
import random
import sys

import bmesh
import numpy as np
from mathutils import Matrix, Vector, noise

from . import arch, nature, tex, util

V = Vector
R = math.radians
TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")


def abyss_layout():
    """tools/maps/blood_abyss.py: the shared, pure-Python definition of the canyon ground."""
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    from maps import blood_abyss
    return blood_abyss


# --------------------------------------------------------------------------
# textures
# --------------------------------------------------------------------------
def glyph_column(size, cols=1, rows=10, seed=601, stroke=0.006, margin=0.3):
    """Columns of angular pseudo-runes (mask), one column per 1/cols of u."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((size, size), np.float32)
    for c in range(cols):
        for r in range(rows):
            u0 = (c + margin) / cols
            u1 = (c + 1 - margin) / cols
            v0 = (r + 0.18) / rows
            v1 = (r + 0.82) / rows
            gx = [u0 + (u1 - u0) * k / 2 for k in range(3)]
            gy = [v0 + (v1 - v0) * k / 2 for k in range(3)]
            for _ in range(rng.integers(3, 6)):
                a = (gx[rng.integers(0, 3)], gy[rng.integers(0, 3)])
                b = (gx[rng.integers(0, 3)], gy[rng.integers(0, 3)])
                if a == b:
                    continue
                n = 24
                pts = [(a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n) for t in range(n + 1)]
                tex.stamp_curve(mask, pts, stroke, size)
            if rng.random() < 0.5:
                cx, cy = (u0 + u1) / 2, (v0 + v1) / 2
                rr = (u1 - u0) * 0.22
                pts = [(cx + rr * math.cos(t), cy + rr * math.sin(t) * (u1 - u0) / (v1 - v0) * 1.6)
                       for t in np.linspace(0, 2 * math.pi, 40)]
                tex.stamp_curve(mask, pts, stroke * 0.8, size)
    return mask


def crimson_soil(size=512, seed=401):
    """Dark red volcanic soil with ash patches, pebbles and faintly glowing cracks."""
    n = tex.fbm(size, 6, 6, 0.55, seed)
    n2 = tex.fbm(size, 24, 4, 0.5, seed + 1)
    patches = tex.fbm(size, 6, 4, 0.5, seed + 2)
    col = tex.lerp(tex.srgb("#2e1c18"), tex.srgb("#5a3a2e"), n * 0.6 + n2 * 0.4)
    col = tex.lerp(col, tex.srgb("#2a2424"), tex.sstep(0.5, 0.8, patches) * 0.35)
    crack = 1 - tex.sstep(0.0, 0.03, np.abs(tex.fbm(size, 5, 5, 0.55, seed + 3) - 0.5))
    fine = 1 - tex.sstep(0.0, 0.018, np.abs(tex.fbm(size, 12, 4, 0.5, seed + 4) - 0.5))
    cr = np.maximum(crack, fine * 0.6)
    col = tex.lerp(col, tex.srgb("#140606"), cr * 0.85)
    peb = tex.sstep(0.76, 0.84, tex.fbm(size, 64, 2, 0.5, seed + 5))
    col = tex.lerp(col, tex.srgb("#3e3432"), peb * 0.55)
    maps = tex.result(col, 0.9 - peb * 0.12, 0.0, n * 0.4 + n2 * 0.3 - cr * 0.5 + peb * 0.3)
    glow = crack * tex.sstep(0.62, 0.8, tex.fbm(size, 4, 3, 0.5, seed + 6))
    maps["emit"] = np.clip(glow[..., None] * tex.srgb("#ff2a10")[None, None, :], 0, 1)
    return maps


def basalt(size=512, seed=411, color="#2c2527", veins=0.0):
    """Black volcanic rock: strata, vesicles, rust stains; optional glowing lava veins."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 4, 7, 0.55, seed)
    warp = tex.fbm(size, 2, 4, 0.5, seed + 1)
    strata = np.sin((v * 10 + warp * 3) * math.pi) * 0.5 + 0.5
    col = tex.srgb(color) * (0.65 + 0.45 * n + 0.2 * strata)[..., None]
    rust = tex.sstep(0.6, 0.85, tex.fbm(size, 3, 4, 0.5, seed + 2))
    col = tex.lerp(col, tex.srgb("#4a1a14"), rust * 0.55)
    cracks = tex.sstep(0.9, 0.97, tex.fbm(size, 16, 3, 0.5, seed + 3, stretch=4))
    col = tex.lerp(col, col * 0.3, cracks)
    ves = tex.sstep(0.8, 0.9, tex.fbm(size, 96, 2, 0.5, seed + 4))
    col = col * (1 - 0.35 * ves)[..., None]
    maps = tex.result(col, 0.8 - 0.25 * tex.sstep(0.7, 0.9, n), 0.0,
                      strata * 0.4 + n * 0.5 - cracks * 0.5 - ves * 0.2)
    if veins > 0:
        vein = 1 - tex.sstep(0.0, 0.025, np.abs(tex.fbm(size, 4, 5, 0.55, seed + 5) - 0.5))
        vein = vein * tex.sstep(0.35, 0.6, tex.fbm(size, 3, 3, 0.5, seed + 6)) * veins
        maps["albedo"] = np.clip(tex.lerp(maps["albedo"], tex.srgb("#ff3a12"), vein * 0.7), 0, 1)
        maps["emit"] = np.clip(vein[..., None] * tex.srgb("#ff3010")[None, None, :], 0, 1)
    return maps


def dark_blocks(size=512, seed=421, color="#4a4044", rows=5):
    """Irregular dressed basalt ashlar with dark mortar joints, rust and blood stains (tileable)."""
    rng = np.random.default_rng(seed)
    u, v = tex.grid(size)
    hs = rng.uniform(0.75, 1.25, rows)
    ev = np.concatenate([[0.0], np.cumsum(hs) / hs.sum()])
    row = np.clip(np.searchsorted(ev, v, side="right") - 1, 0, rows - 1)
    hr = (ev[1:] - ev[:-1])[row]
    fv = (v - ev[row]) / hr
    dist = np.zeros_like(u)
    tone = np.zeros_like(u)
    for r in range(rows):
        widths = rng.uniform(0.6, 1.4, rng.integers(2, 4))
        eu = np.concatenate([[0.0], np.cumsum(widths) / widths.sum()])
        off = rng.random()
        tones = rng.random(len(widths))
        mask = row == r
        uu = (u[mask] - off) % 1.0
        idx = np.clip(np.searchsorted(eu, uu, side="right") - 1, 0, len(widths) - 1)
        w = (eu[1:] - eu[:-1])[idx]
        fu = (uu - eu[idx]) / w
        du = np.minimum(fu, 1 - fu) * w
        dvv = np.minimum(fv[mask], 1 - fv[mask]) * hr[mask]
        dist[mask] = np.minimum(du, dvv)
        tone[mask] = tones[idx]
    n = tex.fbm(size, 8, 5, 0.55, seed + 7)
    chip = tex.fbm(size, 32, 3, 0.5, seed + 9)
    d = dist + (chip - 0.5) * 0.008
    mortar = 1 - tex.sstep(0.003, 0.009, d)
    stain = tex.sstep(0.55, 0.9, tex.fbm(size, 2, 4, 0.5, seed + 8, stretch=3))
    col = tex.srgb(color) * (0.6 + 0.3 * tone + 0.25 * n)[..., None]
    col = tex.lerp(col, tex.srgb("#4a1712"), stain * 0.4)
    col = tex.lerp(col, tex.srgb("#0d0a0b"), mortar * 0.9)
    bevel = tex.sstep(0.0, 0.02, d)
    return tex.result(col, 0.75 + mortar * 0.15, 0.0, bevel * 0.6 + n * 0.25 + chip * 0.1)


def rune_stone(size=512, seed=431, color="#18141a", glow="#ff2410", cols=1, rows=9, frame=True):
    """Polished dark stone with carved rune columns; 'emit' holds the glowing glyphs."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 4, 6, 0.55, seed)
    col = tex.srgb(color) * (0.8 + 0.4 * n)[..., None]
    glyph = glyph_column(size, cols, rows, seed + 1, stroke=0.007 / max(1, cols) * 1.5 + 0.002)
    border = np.zeros_like(u)
    if frame:
        fu = (u * cols) % 1.0
        border = (((fu > 0.2) & (fu < 0.225)) | ((fu > 0.775) & (fu < 0.8))).astype(np.float32)
    col = tex.lerp(col, tex.srgb(glow) * 0.8, glyph * 0.85)
    col = tex.lerp(col, col * 0.4, border)
    maps = tex.result(col, 0.35 + 0.2 * n, 0.0, n * 0.3 - glyph * 0.5 - border * 0.4)
    maps["emit"] = np.clip(glyph[..., None] * tex.srgb(glow)[None, None, :], 0, 1)
    return maps


def bone(size=256, seed=441):
    n = tex.fbm(size, 8, 5, 0.55, seed)
    stains = tex.fbm(size, 3, 4, 0.5, seed + 1)
    col = tex.lerp(tex.srgb("#cfc3a6"), tex.srgb("#ece4cf"), n)
    col = tex.lerp(col, tex.srgb("#6e4a30"), tex.sstep(0.6, 0.9, stains) * 0.55)
    pores = tex.sstep(0.8, 0.9, tex.fbm(size, 64, 2, 0.5, seed + 2))
    col = col * (1 - 0.15 * pores)[..., None]
    return tex.result(col, 0.55 + 0.25 * stains, 0.0, n * 0.4 + pores * 0.2)


def liquid(size=256, seed=451, base="#4a0405", light="#b0150c", glow="#ff200a"):
    """Swirling, viscous liquid surface (blood by default)."""
    n = tex.fbm(size, 4, 5, 0.6, seed)
    sw = np.abs(np.sin((tex.fbm(size, 3, 4, 0.5, seed + 1) * 5 + n * 2) * math.pi))
    t = tex.sstep(0.6, 1.0, sw) * 0.6 + n * 0.4
    maps = tex.result(tex.lerp(tex.srgb(base), tex.srgb(light), t), 0.12, 0.0, n * 0.3 + sw * 0.1)
    maps["emit"] = np.clip((t ** 2)[..., None] * tex.srgb(glow)[None, None, :], 0, 1)
    return maps


def war_cloth(size=512, seed=461, base="#6b0f12", trim="#101014", gold="#b8892f"):
    """Coarse crimson canvas with black and gold hem bands at v = 0 (u runs along the hem)."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 6, 5, 0.55, seed)
    dirt = tex.sstep(0.35, 0.0, v) * 0.5 + tex.sstep(0.6, 0.95, tex.fbm(size, 3, 4, 0.5, seed + 1)) * 0.3
    col = tex.srgb(base) * (0.75 + 0.35 * n)[..., None]
    band = (v < 0.12).astype(np.float32)
    line = ((v > 0.135) & (v < 0.15)).astype(np.float32) + ((v > 0.07) & (v < 0.08)).astype(np.float32)
    col = tex.lerp(col, tex.srgb(trim), band)
    col = tex.lerp(col, tex.srgb(gold), np.clip(line, 0, 1))
    col = tex.lerp(col, tex.srgb("#2a1a14"), np.clip(dirt, 0, 1) * 0.5)
    w = tex.weave(size, 3.0)
    return tex.result(col, 0.85 - line * 0.4, line * 0.6, w * 0.4 + n * 0.2)


def blood_moon_banner(size=512, seed=471):
    """Crimson banner (u across, v down from the top) with a blood moon and sect glyph."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 5, 5, 0.55, seed)
    col = tex.lerp(tex.srgb("#520a0d"), tex.srgb("#8e1a17"), n)
    x, y = u - 0.5, (v - 0.68) * 2.6
    r = np.sqrt(x * x + y * y)
    moon = 1 - tex.sstep(0.26, 0.27, r)
    halo = np.clip(1 - (r - 0.27) / 0.12, 0, 1) * (r > 0.27)
    shade = 1 - tex.sstep(0.2, 0.21, np.sqrt((x + 0.1) ** 2 + (y - 0.06) ** 2))
    moon_c = tex.lerp(tex.srgb("#ff4a1c"), tex.srgb("#b3120c"), tex.fbm(size, 8, 4, 0.5, seed + 1))
    col = tex.lerp(col, tex.srgb("#ff7a3a"), halo * 0.35)
    col = tex.lerp(col, moon_c, moon)
    col = tex.lerp(col, tex.srgb("#2a0405"), moon * shade * 0.8)
    glyph = glyph_column(size, 1, 3, seed + 2, stroke=0.012, margin=0.28)
    glyph = glyph * (v < 0.42) * (v > 0.08)
    col = tex.lerp(col, tex.srgb("#0c0a0c"), glyph)
    border = ((u < 0.06) | (u > 0.94) | (v > 0.95)).astype(np.float32)
    gold = (((u > 0.075) & (u < 0.085)) | ((u > 0.915) & (u < 0.925))).astype(np.float32)
    col = tex.lerp(col, tex.srgb("#0e0b0d"), border)
    col = tex.lerp(col, tex.srgb("#c0922f"), gold)
    maps = tex.result(col, 0.8 - gold * 0.4, gold * 0.7, tex.weave(size, 3.0) * 0.3)
    maps["emit"] = np.clip((moon * (1 - shade * 0.8))[..., None] * tex.srgb("#ff2a0c")[None, None, :], 0, 1)
    return maps


def sigil_floor(size=1024, seed=481):
    """Polished basalt flagstones with an inlaid blood-moon summoning circle (planar disc uv)."""
    base = tex.paving("#2e2629", size, seed, tiles=8, gap=0.004, moss=0.0)
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    m = np.zeros_like(r)
    for rr in (0.44, 0.41, 0.3, 0.16):
        m = np.maximum(m, 1 - tex.sstep(0.0, 0.0035, np.abs(r - rr)))
    m = np.maximum(m, ((np.sin(a * 40) > 0.55) & (r > 0.415) & (r < 0.435)).astype(np.float32))
    for k in range(5):
        a0 = k * 4 * math.pi / 5 + math.pi / 2
        a1 = (k + 1) * 4 * math.pi / 5 + math.pi / 2
        p0 = np.array([math.cos(a0), math.sin(a0)]) * 0.3
        p1 = np.array([math.cos(a1), math.sin(a1)]) * 0.3
        d = p1 - p0
        t = np.clip(((x - p0[0]) * d[0] + (y - p0[1]) * d[1]) / (d @ d), 0, 1)
        dist = np.sqrt((x - p0[0] - d[0] * t) ** 2 + (y - p0[1] - d[1] * t) ** 2)
        m = np.maximum(m, 1 - tex.sstep(0.0, 0.003, dist))
    m = np.maximum(m, (1 - tex.sstep(0.07, 0.075, r)) * 0.8)
    col = tex.lerp(base["albedo"] * 0.8, tex.srgb("#c0180c"), m)
    maps = tex.result(col, np.clip(base["rough"] * 0.5, 0, 1), 0.0, base["height"] - m * 0.4)
    maps["emit"] = np.clip(m[..., None] * tex.srgb("#ff1a08")[None, None, :], 0, 1)
    return maps


def mirror_surface(size=256, seed=491):
    n = tex.fbm(size, 3, 5, 0.6, seed)
    sw = np.abs(np.sin((tex.fbm(size, 2, 4, 0.5, seed + 1) * 4 + n) * math.pi))
    col = tex.lerp(tex.srgb("#040308"), tex.srgb("#150b22"), n * 0.6)
    maps = tex.result(col, 0.03, 0.3, n * 0.05)
    maps["emit"] = np.clip((tex.sstep(0.88, 1.0, sw) * 0.45 + n * 0.12)[..., None]
                           * tex.srgb("#7a3cff")[None, None, :], 0, 1)
    return maps


# sky isles -----------------------------------------------------------------
def sky_grass(size=512, seed=501):
    g = tex.grass(size, seed)
    patches = tex.fbm(size, 2, 4, 0.5, seed + 11)
    col = g["albedo"] * np.array([1.05, 1.18, 0.95], np.float32)
    col = tex.lerp(col, col * np.array([1.2, 1.15, 0.8], np.float32), tex.sstep(0.45, 0.75, patches) * 0.6)
    dots = tex.sstep(0.86, 0.9, tex.fbm(size, 128, 2, 0.5, seed + 9))
    hue = tex.fbm(size, 6, 3, 0.5, seed + 10)
    flower = tex.lerp(tex.srgb("#fff6f8"), tex.srgb("#f2a8c4"), tex.sstep(0.4, 0.7, hue))
    col = tex.lerp(col, flower, dots * 0.9)
    return tex.result(col, 0.85, 0.0, g["height"] + dots * 0.3)


def marble(size=512, seed=511, color="#eceae3", veins=0.35):
    s = tex.stone(color, size, seed, 0.12)
    vn = np.abs(np.sin((tex.fbm(size, 3, 5, 0.55, seed + 1) * 7) * math.pi))
    vein = (1 - tex.sstep(0.0, 0.06, vn)) * veins
    col = tex.lerp(s["albedo"], tex.srgb("#9da3a6"), vein)
    return tex.result(col, 0.32 + 0.2 * tex.fbm(size, 8, 3, 0.5, seed + 2), 0.0, s["height"] * 0.3)


def cracked_marble(size=512, seed=521):
    m = marble(size, seed, "#e2dfd6", 0.25)
    crack = 1 - tex.sstep(0.0, 0.012, np.abs(tex.fbm(size, 4, 5, 0.55, seed + 3) - 0.5))
    crack = crack * tex.sstep(0.3, 0.55, tex.fbm(size, 3, 3, 0.5, seed + 4))
    moss = tex.sstep(0.6, 0.85, tex.fbm(size, 5, 5, 0.55, seed + 5))
    col = tex.lerp(m["albedo"], tex.srgb("#4a4a44"), crack * 0.8)
    col = tex.lerp(col, tex.srgb("#7d9a5a"), moss * 0.35)
    return tex.result(col, np.clip(m["rough"] + moss * 0.3, 0, 1), 0.0, m["height"] - crack * 0.6)


def carved_marble(size=512, seed=531):
    """White marble with raised auspicious-cloud reliefs (for beams and gate pillars)."""
    m = marble(size, seed, "#efece4", 0.15)
    clouds = tex.xiangyun_mask(size, 4, seed + 1, 0.09, 0.012)
    col = tex.lerp(m["albedo"], m["albedo"] * np.array([0.92, 0.93, 0.95], np.float32), clouds)
    return tex.result(col, 0.4, 0.0, m["height"] + clouds * 0.9)


def star_map(size=1024, seed=541):
    """Deep-blue lapis floor with gold rings, constellations and glowing stars (disc uv)."""
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    n = tex.fbm(size, 6, 6, 0.55, seed)
    col = tex.lerp(tex.srgb("#0d1638"), tex.srgb("#233a78"), n * 0.7)
    fleck = tex.sstep(0.9, 0.95, tex.fbm(size, 128, 2, 0.5, seed + 1))
    col = tex.lerp(col, tex.srgb("#d8b85a"), fleck * 0.6)
    gold = np.zeros_like(r)
    for rr in (0.47, 0.455, 0.36, 0.2):
        gold = np.maximum(gold, 1 - tex.sstep(0.0, 0.0025, np.abs(r - rr)))
    ticks = ((np.abs(np.sin(a * 14)) < 0.08) & (r > 0.36) & (r < 0.455)).astype(np.float32)
    ticks += ((np.abs(np.sin(a * 56)) < 0.05) & (r > 0.44) & (r < 0.455)).astype(np.float32)
    gold = np.clip(gold + ticks, 0, 1)
    rng = np.random.default_rng(seed + 2)
    lines = np.zeros_like(r)
    stars = np.zeros_like(r)
    for _ in range(9):
        ca = rng.uniform(0, 2 * math.pi)
        cr = rng.uniform(0.06, 0.33)
        c = np.array([0.5 + cr * math.cos(ca), 0.5 + cr * math.sin(ca)])
        pts = [c + rng.uniform(-0.06, 0.06, 2) for _ in range(rng.integers(3, 7))]
        for p, q in zip(pts[:-1], pts[1:]):
            seg = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t) for t in np.linspace(0, 1, 40)]
            tex.stamp_curve(lines, seg, 0.0012, size, 0.7)
        for p in pts:
            tex.stamp_curve(stars, [(p[0], p[1])], 0.006, size)
    for _ in range(260):
        p = rng.uniform(0.05, 0.95, 2)
        if np.hypot(p[0] - 0.5, p[1] - 0.5) < 0.35:
            tex.stamp_curve(stars, [(p[0], p[1])], rng.uniform(0.0015, 0.003), size, rng.uniform(0.5, 1))
    inside = (r < 0.475).astype(np.float32)
    col = tex.lerp(col, tex.srgb("#e0c060"), np.clip(gold + lines * 0.8, 0, 1))
    col = tex.lerp(col, tex.srgb("#f4f8ff"), stars)
    col = tex.lerp(tex.srgb("#e8e6df") * (0.85 + 0.2 * n)[..., None], col, inside)
    maps = tex.result(col, 0.25 + 0.2 * (1 - inside), gold * 0.8 * inside, n * 0.2 - gold * 0.3)
    glow = np.clip(stars + lines * 0.5 + gold * 0.25, 0, 1) * inside
    maps["emit"] = np.clip(glow[..., None] * tex.srgb("#9fc8ff")[None, None, :], 0, 1)
    return maps


def taiji_bagua(size=1024, seed=551):
    """Tribulation altar disc: taiji in the centre, eight trigrams, thunder-rune rings (disc uv)."""
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    base = tex.stone("#bdbab2", size, seed, 0.2)
    col = base["albedo"]
    rt = 0.11
    yang = np.where(x > 0, 1.0, 0.0)
    top = np.sqrt(x * x + (y - rt / 2) ** 2) < rt / 2
    bot = np.sqrt(x * x + (y + rt / 2) ** 2) < rt / 2
    yang = np.where(top, 0.0, np.where(bot, 1.0, yang))
    yang = np.where(np.sqrt(x * x + (y - rt / 2) ** 2) < rt / 8, 1.0, yang)
    yang = np.where(np.sqrt(x * x + (y + rt / 2) ** 2) < rt / 8, 0.0, yang)
    disc = (r < rt).astype(np.float32)
    col = tex.lerp(col, tex.lerp(tex.srgb("#15161a"), tex.srgb("#f2f0ea"), yang), disc)
    gold = 1 - tex.sstep(0.0, 0.003, np.abs(r - rt))
    for rr in (0.2, 0.32, 0.46, 0.475):
        gold = np.maximum(gold, 1 - tex.sstep(0.0, 0.003, np.abs(r - rr)))
    trig = np.zeros_like(r)
    for k in range(8):
        ang = k * math.pi / 4
        ca, sa = math.cos(ang), math.sin(ang)
        lx = x * ca + y * sa
        ly = -x * sa + y * ca
        for j in range(3):
            rad = 0.225 + j * 0.03
            line = (np.abs(lx - rad) < 0.009) & (np.abs(ly) < 0.05)
            if (k >> j) & 1:
                line &= np.abs(ly) > 0.009
            trig = np.maximum(trig, line.astype(np.float32))
    runes = ((np.sin(a * 64) > 0.2) & (np.cos(a * 16) > -0.3) & (r > 0.345) & (r < 0.44)).astype(np.float32)
    runes *= (np.abs(((r - 0.345) / 0.095 * 3) % 1.0 - 0.5) < 0.3)
    m = np.clip(gold + trig + runes * 0.8, 0, 1)
    col = tex.lerp(col, tex.srgb("#d9ae45"), m)
    maps = tex.result(col, 0.6 - m * 0.35, m * 0.85, base["height"] * 0.4 - m * 0.4)
    maps["emit"] = np.clip((trig * 0.6 + runes * 0.8 + gold * 0.3)[..., None]
                           * tex.srgb("#9fdcff")[None, None, :], 0, 1)
    return maps


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def _mat(name, maps, strength=2.0, **kw):
    emit = maps.get("emit")
    return util.material(name, maps, emission_map=emit, emission_strength=strength if emit is not None else 1.0,
                         **kw)


def glow(name, color, strength=4.0, base=None):
    return util.material(name, color=base or color, rough=0.5, emission=color, emission_strength=strength)


def abyss_mats():
    m = {}
    m["rock"] = util.material("abyss_basalt", basalt(512), normal_strength=1.2)
    m["lava_rock"] = _mat("abyss_lava_rock", basalt(512, 412, "#241e20", veins=1.0), 3.0, normal_strength=1.2)
    m["blocks"] = util.material("fortress_blocks", dark_blocks(512), normal_strength=1.0)
    m["runes"] = _mat("blood_runes", rune_stone(512), 3.5, normal_strength=0.6)
    m["obsidian"] = util.material("obsidian", tex.stone("#141116", 256, 433, 0.1), rough=0.2, normal_strength=0.3)
    m["bone"] = util.material("bone", bone(256), normal_strength=0.6)
    m["iron"] = util.material("rusty_iron", tex.metal("#3c3a3d", 256, 435, rough=0.55, patina="#5c2c1a",
                                                      patina_amt=0.35), normal_strength=0.8)
    m["bronze"] = util.material("dark_bronze", tex.metal("#6b4a26", 256, 436, rough=0.4, patina="#2f2a22",
                                                         patina_amt=0.3), normal_strength=0.6)
    m["blood"] = _mat("blood", liquid(256), 1.6, normal_strength=0.4)
    m["fire"] = glow("demon_fire", "#ff4a14", 8.0)
    m["eye"] = glow("demon_eye", "#ff1a0a", 6.0)
    m["dark"] = util.material("socket_dark", color="#070506", rough=0.9)
    m["cloth"] = util.material("war_cloth", war_cloth(512), double_sided=True, normal_strength=0.4)
    m["lacquer"] = util.material("black_lacquer", tex.lacquer("#5a0d0c", 256, 437, 0.2), normal_strength=0.3)
    m["wood"] = util.material("charred_wood", tex.wood("#2a1c16", 256, 438), normal_strength=0.5)
    return m


def sky_mats():
    m = {}
    m["marble"] = util.material("sky_marble", marble(512), normal_strength=0.4)
    m["carved"] = util.material("carved_marble", carved_marble(512), normal_strength=1.2)
    m["cracked"] = util.material("cracked_marble", cracked_marble(512), normal_strength=0.8)
    m["jade"] = util.material("sky_jade", tex.jade("#4fae8a", 256, 561), normal_strength=0.3)
    m["gold"] = util.material("sky_gold", tex.metal("#d8ae4a", 256, 562, rough=0.25))
    m["jade_tiles"] = util.material("jade_tiles", tex.roof_tiles("#3a8f78", 512, 563), normal_strength=1.0)
    m["blue_tiles"] = util.material("lapis_tiles", tex.roof_tiles("#2c4585", 512, 564), normal_strength=1.0)
    m["ridge"] = util.material("sky_ridge", tex.stone("#f2efe8", 256, 565, 0.1), normal_strength=0.4)
    m["beam"] = util.material("sky_beam", tex.beam_paint(512), normal_strength=0.4)
    m["grass"] = util.material("sky_grass", sky_grass(512), normal_strength=0.6)
    m["cliff"] = util.material("sky_cliff", tex.cliff("#9a948a", 512, 566), normal_strength=1.2)
    m["roots"] = util.material("sky_roots", tex.bark("#5b4636", 256, 567), normal_strength=0.8)
    m["crystal"] = util.material("spirit_crystal_blue", color="#8ff4ff", rough=0.05, emission="#35c8ff",
                                 emission_strength=3.0, alpha=0.88)
    m["crystal_core"] = glow("crystal_core", "#bff8ff", 6.0)
    m["lamp"] = glow("jade_lamp", "#9ff7e0", 5.0)
    return m


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------
def prism(bm, profile, sides=4, rot=math.pi / 4, loc=(0, 0, 0), cap_top=True, cap_bottom=False,
          v_scale=None, jitter=0.0, seed=0):
    """Faceted solid of revolution from [(radius, z)]; every side face gets u 0..1.

    v runs 0..1 over the whole height, or z * v_scale when given.
    """
    uvl = bm.loops.layers.uv.verify()
    rnd = random.Random(seed)
    rings = []
    for r, z in profile:
        ring = []
        for k in range(sides):
            a = rot + 2 * math.pi * k / sides
            rr = r * (1 + rnd.uniform(-jitter, jitter)) if jitter else r
            ring.append(bm.verts.new(V((loc[0] + rr * math.cos(a), loc[1] + rr * math.sin(a), loc[2] + z))))
        rings.append(ring)
    z0, z1 = profile[0][1], profile[-1][1]
    for j in range(len(rings) - 1):
        va = (profile[j][1] - z0) / (z1 - z0) if v_scale is None else profile[j][1] * v_scale
        vb = (profile[j + 1][1] - z0) / (z1 - z0) if v_scale is None else profile[j + 1][1] * v_scale
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((rings[j][k], rings[j][k2], rings[j + 1][k2], rings[j + 1][k]))
            for loop, uv in zip(f.loops, ((0, va), (1, va), (1, vb), (0, vb))):
                loop[uvl].uv = uv
    for ring, top in ((rings[-1], True), (rings[0], False)):
        if (top and cap_top) or (not top and cap_bottom):
            f = bm.faces.new(ring if top else list(reversed(ring)))
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.x * 0.5, loop.vert.co.y * 0.5)
    return rings


def tapered_box(bm, x0, x1, y0, y1, z0, z1, inset=0.0, sides=None):
    """Box whose top face is inset (a battered wall/tower).

    sides: optional (x0, x1, y0, y1) insets overriding the uniform one.
    """
    uvl = bm.loops.layers.uv.verify()
    i0, i1, j0, j1 = sides if sides is not None else (inset, inset, inset, inset)
    b = [V((x0, y0, z0)), V((x1, y0, z0)), V((x1, y1, z0)), V((x0, y1, z0))]
    t = [V((x0 + i0, y0 + j0, z1)), V((x1 - i1, y0 + j0, z1)), V((x1 - i1, y1 - j1, z1)),
         V((x0 + i0, y1 - j1, z1))]
    vb = [bm.verts.new(p) for p in b]
    vt = [bm.verts.new(p) for p in t]
    faces = [vt, list(reversed(vb))]
    for k in range(4):
        k2 = (k + 1) % 4
        faces.append([vb[k], vb[k2], vt[k2], vt[k]])
    for fv in faces:
        f = bm.faces.new(fv)
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.x, loop.vert.co.z)
    return vb + vt


def disc(bm, center, radius, segs=48, z=0.0, uv_size=None, wobble=0.0, seed=0.0):
    """Flat fan disc; uv maps the disc into 0..1 (or world metres / uv_size)."""
    uvl = bm.loops.layers.uv.verify()
    c = bm.verts.new(V((center[0], center[1], z)))
    ring = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        rr = radius * (1 + wobble * noise.noise(V((math.cos(a) * 1.7, math.sin(a) * 1.7, seed))))
        ring.append(bm.verts.new(V((center[0] + rr * math.cos(a), center[1] + rr * math.sin(a), z))))
    for k in range(segs):
        f = bm.faces.new((c, ring[k], ring[(k + 1) % segs]))
        for loop in f.loops:
            co = loop.vert.co
            if uv_size:
                loop[uvl].uv = (co.x / uv_size, co.y / uv_size)
            else:
                loop[uvl].uv = ((co.x - center[0]) / (2 * radius) + 0.5, (co.y - center[1]) / (2 * radius) + 0.5)
    return ring


def xform_verts(bm, verts, loc=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
    m = (Matrix.Translation(V(loc)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "X")
         @ Matrix.Rotation(roll, 4, "Y") @ Matrix.Scale(scale, 4))
    bmesh.ops.transform(bm, matrix=m, verts=verts)


def skull(bm, bm_eyes, loc, s=1.0, yaw=0.0, pitch=0.0, roll=0.0):
    """A skull ~0.3 m * s facing -Y; the eye sockets go into bm_eyes (dark or glowing)."""
    vs = []
    vs += util.sphere(bm, 0.12, loc=(0, 0.015, 0.13), segs=12, rings=8, scale=(0.88, 1.08, 0.95))
    vs += util.sphere(bm, 0.075, loc=(0, -0.075, 0.065), segs=10, rings=6, scale=(1.05, 0.9, 0.95))
    vs += util.box(bm, (0.11, 0.08, 0.045), loc=(0, -0.085, 0.0))
    for sx in (-1, 1):
        vs += util.box(bm, (0.03, 0.09, 0.04), loc=(sx * 0.07, -0.02, 0.03))
    xform_verts(bm, vs, loc, yaw, pitch, roll, s)
    ev = []
    for sx in (-1, 1):
        ev += util.sphere(bm_eyes, 0.03, loc=(sx * 0.043, -0.112, 0.105), segs=8, rings=5)
    ev += util.sphere(bm_eyes, 0.017, loc=(0, -0.142, 0.058), segs=6, rings=4)
    xform_verts(bm_eyes, ev, loc, yaw, pitch, roll, s)


def long_bone(bm, a, b, r=0.035):
    a, b = V(a), V(b)
    d = (b - a).normalized()
    side = d.cross(V((0, 0, 1)))
    if side.length < 1e-3:
        side = V((1, 0, 0))
    side.normalize()
    util.tube(bm, [a, a.lerp(b, 0.5), b], lambda t: r * (1.0 - 0.25 * math.sin(math.pi * t)), n=7)
    for end in (a, b):
        for sgn in (-1, 1):
            util.sphere(bm, r * 1.25, loc=end + side * sgn * r * 0.7, segs=7, rings=5)


def chain(bm, pts, link=0.13, r=0.018):
    """Iron chain of alternating oval links along a (sagging) poly-line."""
    path = util.catmull([V(p) for p in pts], 10)
    # resample by arc length
    out, acc = [path[0]], 0.0
    for p, q in zip(path[:-1], path[1:]):
        seg = (q - p).length
        while acc + seg >= link * 0.8:
            t = (link * 0.8 - acc) / seg
            p = p.lerp(q, t)
            seg = (q - p).length
            out.append(p)
            acc = 0.0
        acc += seg
    for i, (p, q) in enumerate(zip(out[:-1], out[1:])):
        t = (q - p).normalized()
        up = V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))
        s = t.cross(up).normalized()
        if i % 2:
            s = t.cross(s).normalized()
        c = (p + q) / 2
        loop = [c + t * math.cos(a) * link * 0.55 + s * math.sin(a) * link * 0.3
                for a in [2 * math.pi * k / 10 for k in range(11)]]
        util.tube(bm, loop, r, n=5, closed_ends=False)


def lantern(bm_paper, bm_frame, loc, s=1.0):
    """Hanging paper lantern: origin at the hook."""
    x, y, z = loc
    prof = [(0.1 * s, -0.12 * s)]
    for k in range(9):
        t = k / 8
        prof.append(((0.13 + 0.2 * math.sin(math.pi * t)) * s, (-0.14 - 0.5 * t) * s))
    util.lathe(bm_paper, prof, segs=14, loc=(x, y, z), uv_v=1.6)
    util.cylinder(bm_frame, 0.13 * s, 0.13 * s, 0.05 * s, loc=(x, y, z - 0.12 * s), segs=12)
    util.cylinder(bm_frame, 0.13 * s, 0.13 * s, 0.05 * s, loc=(x, y, z - 0.64 * s), segs=12)
    util.cylinder(bm_frame, 0.01 * s, 0.01 * s, 0.12 * s, loc=(x, y, z - 0.04 * s), segs=5)
    util.cylinder(bm_frame, 0.02 * s, 0.05 * s, 0.3 * s, loc=(x, y, z - 0.82 * s), segs=6)


def flame(bm, loc, h=0.35, r=0.12):
    x, y, z = loc
    util.lathe(bm, [(r * 0.6, 0), (r, h * 0.2), (r * 0.7, h * 0.55), (r * 0.25, h * 0.85), (0.001, h)],
               segs=8, loc=(x, y, z))


def brazier(bm_metal, bm_fire, loc, s=1.0, legs=True):
    x, y, z = loc
    util.lathe(bm_metal, [(0.001, 0.0), (0.25 * s, 0.02 * s), (0.45 * s, 0.22 * s), (0.55 * s, 0.4 * s),
                          (0.5 * s, 0.42 * s), (0.4 * s, 0.3 * s), (0.001, 0.28 * s)],
               segs=16, loc=(x, y, z + 0.75 * s))
    if legs:
        for k in range(3):
            a = 2 * math.pi * k / 3
            util.tube(bm_metal, [V((x + math.cos(a) * 0.3 * s, y + math.sin(a) * 0.3 * s, z + 0.85 * s)),
                                 V((x + math.cos(a) * 0.5 * s, y + math.sin(a) * 0.5 * s, z + 0.3 * s)),
                                 V((x + math.cos(a) * 0.42 * s, y + math.sin(a) * 0.42 * s, z))],
                      0.04 * s, n=6)
    for k in range(5):
        a = 2 * math.pi * k / 5
        rr = 0.18 * s if k else 0.0
        flame(bm_fire, (x + math.cos(a) * rr, y + math.sin(a) * rr, z + 1.02 * s),
              h=(0.6 if k == 0 else 0.4) * s, r=0.14 * s)


def finish(name, bm, mat, uv=None, smooth=False):
    o = util.mesh_object(name, bm, mat, smooth=smooth)
    if uv:
        util.box_uv(o, uv)
    return o


def convex(name, bm):
    """Custom convex collision hull (Godot '-convcolonly')."""
    bmesh.ops.convex_hull(bm, input=bm.verts)
    return util.mesh_object(name + "-convcolonly", bm, None, smooth=False)


def ramp_collider(name, width, z0, z1, y0, y1, x=0.0, thick=0.3):
    """Walkable ramp box from (y0, z0) to (y1, z1), top surface on that line."""
    ln = math.hypot(y1 - y0, z1 - z0)
    ang = math.atan2(z1 - z0, y1 - y0)
    c = util.collider(name, (width, ln, thick), (0, 0, 0))
    c.rotation_euler = (ang, 0, 0)
    n = V((0, -math.sin(ang), math.cos(ang)))
    c.location = V((x, (y0 + y1) / 2, (z0 + z1) / 2)) - n * thick / 2
    util.apply_transform(c)
    return c


# --------------------------------------------------------------------------
# Blood Moon Abyss props
# --------------------------------------------------------------------------
def blood_altar():
    """Stepped octagonal altar with a basin of glowing blood, bone horns and chains (~5 m)."""
    m = abyss_mats()
    objs = []
    bm = bmesh.new()
    prism(bm, [(2.75, 0.0), (2.75, 0.42), (2.62, 0.48), (2.2, 0.48), (2.2, 0.9), (2.08, 0.96), (1.72, 0.96)],
          sides=8, rot=R(22.5), v_scale=0.5)
    objs.append(finish("AltarSteps", bm, m["blocks"], uv=0.35))
    bm = bmesh.new()
    prism(bm, [(1.72, 0.96), (1.72, 1.46), (1.6, 1.5)], sides=8, rot=R(22.5), cap_top=True)
    objs.append(finish("AltarRunes", bm, m["runes"]))
    bm = bmesh.new()
    util.lathe(bm, [(1.5, 1.48), (1.56, 1.62), (1.44, 1.92), (1.56, 2.06), (1.48, 2.12), (1.3, 2.04),
                    (1.0, 1.84), (0.001, 1.78)], segs=24)
    objs.append(finish("AltarBasin", bm, m["obsidian"], uv=1.0, smooth=True))
    bm = bmesh.new()
    disc(bm, (0, 0), 1.36, 32, z=1.98)
    objs.append(finish("AltarBlood", bm, m["blood"]))
    bm_b, bm_i, bm_e, bm_c, bm_f = (bmesh.new() for _ in range(5))
    for k in range(4):
        a = R(45 + 90 * k)
        d = V((math.cos(a), math.sin(a), 0))
        base = d * 2.3 + V((0, 0, 0.45))
        pts = [base, base + d * 0.15 + V((0, 0, 1.2)), base + d * 0.45 + V((0, 0, 2.4)),
               base + d * 0.3 + V((0, 0, 3.3)), base - d * 0.15 + V((0, 0, 3.8))]
        util.tube(bm_b, util.catmull(pts, 5), lambda t: 0.2 * (1 - 0.85 * t) + 0.015, n=10)
        for zz in (0.35, 1.1):
            util.cylinder(bm_i, 0.23, 0.23, 0.1, loc=base + d * 0.06 + V((0, 0, zz)), segs=10)
        hook = base + d * 0.38 + V((0, 0, 2.7))
        rim = d * 1.45 + V((0, 0, 2.1))
        mid = hook.lerp(rim, 0.5) - V((0, 0, 0.55))
        chain(bm_c, [hook, mid, rim])
        # candles on the middle tier
        for j in (-1, 1):
            ca = a + j * R(20)
            p = V((math.cos(ca) * 1.95, math.sin(ca) * 1.95, 0.96))
            util.cylinder(bm_i, 0.05, 0.05, 0.3, loc=p + V((0, 0, 0.15)), segs=8)
            flame(bm_f, p + V((0, 0, 0.3)), h=0.12, r=0.035)
    for k in range(4):
        a = R(90 * k - 90)
        d = V((math.cos(a), math.sin(a), 0))
        skull(bm_b, bm_e, d * 2.42 + V((0, 0, 0.48)), s=1.3, yaw=a + R(90))
    objs.append(finish("AltarHorns", bm_b, m["bone"], uv=2.0, smooth=True))
    objs.append(finish("AltarIron", bm_i, m["iron"], uv=2.0))
    objs.append(finish("AltarChains", bm_c, m["iron"], uv=3.0, smooth=True))
    objs.append(finish("AltarEyes", bm_e, m["eye"]))
    objs.append(finish("AltarFlames", bm_f, m["fire"]))
    objs.append(util.collider("AltarTier1", (5.2, 5.2, 0.48), (0, 0, 0.24)))
    objs.append(util.collider("AltarTier2", (4.1, 4.1, 0.96), (0, 0, 0.48)))
    objs.append(util.collider("AltarBasin", (3.1, 3.1, 2.1), (0, 0, 1.05)))
    return objs


def demon_obelisk():
    """Tall black obelisk with a column of glowing blood runes on every face (~6.3 m)."""
    m = abyss_mats()
    objs = []
    bm = bmesh.new()
    prism(bm, [(1.3, 0.0), (1.3, 0.34), (1.18, 0.4), (1.02, 0.4), (1.02, 0.72), (0.86, 0.8)], sides=4,
          v_scale=0.5)
    objs.append(finish("ObeliskPlinth", bm, m["blocks"], uv=0.4))
    bm = bmesh.new()
    prism(bm, [(0.8, 0.8), (0.52, 5.3)], sides=4, cap_top=False)
    objs.append(finish("ObeliskShaft", bm, m["runes"]))
    bm = bmesh.new()
    prism(bm, [(0.53, 5.28), (0.6, 5.42), (0.001, 6.3)], sides=4, cap_top=False)
    objs.append(finish("ObeliskCap", bm, m["obsidian"], uv=1.0))
    bm_b, bm_e = bmesh.new(), bmesh.new()
    for k in range(4):
        a = R(45 + 90 * k)
        d = V((math.cos(a), math.sin(a), 0))
        p = d * 0.55 + V((0, 0, 5.25))
        util.tube(bm_b, util.catmull([p, p + d * 0.45 + V((0, 0, 0.1)), p + d * 0.7 + V((0, 0, 0.55))], 4),
                  lambda t: 0.1 * (1 - 0.85 * t) + 0.01, n=8)
    skull(bm_b, bm_e, V((0, -0.66, 0.78)), s=1.5)
    util.sphere(bm_e, 0.13, loc=(0, -0.37, 4.85), segs=12, rings=8, scale=(1, 0.5, 1.3))
    objs.append(finish("ObeliskHorns", bm_b, m["bone"], uv=2.0, smooth=True))
    objs.append(finish("ObeliskEye", bm_e, m["eye"], smooth=True))
    objs.append(util.collider("ObeliskCol", (1.85, 1.85, 6.0), (0, 0, 3.0)))
    return objs


def prison_cage():
    """Rusty iron cage (2.4 m square, 3 m to the hook) with a locked door; bars collide."""
    m = abyss_mats()
    objs = []
    w, h = 2.4, 2.45
    bm = bmesh.new()
    util.box(bm, (w, w, 0.16), loc=(0, 0, 0.08))
    for sx in (-1, 1):
        for sy in (-1, 1):
            util.box(bm, (0.14, 0.14, h), loc=(sx * (w / 2 - 0.07), sy * (w / 2 - 0.07), h / 2))
            util.box(bm, (0.3, 0.3, 0.12), loc=(sx * (w / 2 - 0.1), sy * (w / 2 - 0.1), 0.06))
    for zz in (0.24, 1.25, h - 0.05):
        for sy in (-1, 1):
            util.box(bm, (w, 0.08, 0.08), loc=(0, sy * (w / 2 - 0.04), zz))
            util.box(bm, (0.08, w, 0.08), loc=(sy * (w / 2 - 0.04), 0, zz))
    prism(bm, [(w / 2 * 1.414 + 0.05, h), (0.2, h + 0.55)], sides=4, cap_top=True)
    for k in range(-5, 6):
        x = k * 0.2
        for side in range(4):
            rot = Matrix.Rotation(R(90 * side), 4, "Z")
            if side == 0 and -3 <= k <= 1:
                continue  # door
            util.cylinder(bm, 0.022, 0.022, h - 0.2, loc=rot @ V((x, -(w / 2 - 0.04), h / 2)), segs=6)
    # door: hinged on the left, slightly ajar
    door = []
    for k in range(5):
        door += util.cylinder(bm, 0.022, 0.022, h - 0.3, loc=(0.04 + k * 0.2, 0, h / 2 - 0.02), segs=6)
    for zz in (0.3, 1.25, h - 0.18):
        door += util.box(bm, (0.9, 0.06, 0.06), loc=(0.44, 0, zz))
    xform_verts(bm, door, loc=(-0.62, -(w / 2 - 0.04), 0), yaw=R(-12))
    util.tube(bm, [V((0.06 * math.cos(a), 0, h + 0.62 + 0.12 * math.sin(a) + 0.1)) for a in
                   [2 * math.pi * k / 12 for k in range(13)]], 0.025, n=6, closed_ends=False)
    objs.append(finish("CageIron", bm, m["iron"], uv=1.5))
    bm = bmesh.new()
    util.box(bm, (0.16, 0.08, 0.2), loc=(0.3, -(w / 2) - 0.02, 1.2))
    util.tube(bm, [V((0.3 + 0.05 * math.cos(a), -(w / 2) - 0.02, 1.32 + 0.05 * math.sin(a))) for a in
                   [math.pi * k / 8 for k in range(9)]], 0.012, n=5)
    objs.append(finish("CageLock", bm, m["bronze"], uv=3.0))
    bm_b, bm_e, bm_c = bmesh.new(), bmesh.new(), bmesh.new()
    skull(bm_b, bm_e, V((0.6, 0.5, 0.16)), s=1.0, yaw=R(150), roll=R(8))
    long_bone(bm_b, (-0.5, 0.6, 0.2), (0.2, 0.8, 0.2))
    long_bone(bm_b, (0.7, -0.2, 0.2), (0.4, 0.5, 0.21), 0.03)
    chain(bm_c, [V((-w / 2 + 0.1, w / 2 - 0.1, h - 0.1)), V((-0.6, 0.6, 1.0)), V((-0.2, 0.9, 0.18))])
    objs.append(finish("CageBones", bm_b, m["bone"], uv=2.0, smooth=True))
    objs.append(finish("CageSockets", bm_e, m["dark"]))
    objs.append(finish("CageChain", bm_c, m["iron"], uv=3.0, smooth=True))
    for side in range(4):
        rot = R(90 * side)
        d = V((math.sin(rot), -math.cos(rot), 0)) * (w / 2 - 0.05)
        objs.append(util.collider("CageBars", (w, 0.12, h), (d.x, d.y, h / 2), rot_z=rot))
    objs.append(util.collider("CageRoof", (w, w, 0.5), (0, 0, h + 0.2)))
    objs.append(util.collider("CageFloor", (w, w, 0.16), (0, 0, 0.08)))
    return objs


def bone_pile(seed=5):
    """Mound of dark earth heaped with skulls, long bones and ribs (~3.4 m across)."""
    rnd = random.Random(seed)
    m = abyss_mats()
    soil = util.material("abyss_soil", crimson_soil(256), normal_strength=1.0)
    bm = bmesh.new()
    nature.blob(bm, (0, 0, -0.1), (1.7, 1.4, 0.45), 0.25, 1.5, seed, 3)
    mound = finish("BoneMound", bm, soil, uv=0.6, smooth=True)

    def top(x, y):
        return max(0.0, 0.33 * (1 - (x / 1.7) ** 2 - (y / 1.4) ** 2)) + 0.02

    bm_b, bm_e = bmesh.new(), bmesh.new()
    for k in range(18):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 1.3)
        x, y = math.cos(a) * r, math.sin(a) * r * 0.8
        yaw = rnd.uniform(0, math.pi)
        ln = rnd.uniform(0.35, 0.75)
        d = V((math.cos(yaw), math.sin(yaw), rnd.uniform(-0.25, 0.3))) * ln / 2
        c = V((x, y, top(x, y) + 0.03))
        long_bone(bm_b, c - d, c + d, rnd.uniform(0.025, 0.04))
    for k in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        x, y = rnd.uniform(-0.9, 0.9), rnd.uniform(-0.7, 0.7)
        c = V((x, y, top(x, y) + 0.05))
        arc = [c + V((math.cos(a) * 0.3 * math.cos(t), math.sin(a) * 0.3 * math.cos(t), 0.22 * math.sin(t)))
               for t in np.linspace(0, math.pi * 0.9, 7)]
        util.tube(bm_b, arc, lambda t: 0.018 * (1 - 0.5 * t) + 0.006, n=5)
    for (x, y, yaw) in ((0.15, -0.3, 0.2), (-0.7, 0.2, 1.3), (0.8, 0.4, -0.8), (-0.2, 0.55, 2.8)):
        skull(bm_b, bm_e, V((x, y, top(x, y) - 0.03)), s=rnd.uniform(0.9, 1.15), yaw=yaw,
              pitch=rnd.uniform(-0.2, 0.3), roll=rnd.uniform(-0.3, 0.3))
    bones = finish("Bones", bm_b, m["bone"], uv=2.0, smooth=True)
    sockets = finish("BoneSockets", bm_e, m["dark"])
    return [mound, bones, sockets]


def dead_tree(seed=17, height=7.0):
    """Twisted, leafless charred tree with ember-lit cracks and tattered red ribbons."""
    rnd = random.Random(seed)
    bark_maps = tex.bark("#221a19", 512, 139)
    crack = tex.sstep(0.82, 0.95, 1 - bark_maps["height"]) * tex.sstep(0.55, 0.8, tex.fbm(512, 4, 3, 0.5, 7))
    bark_maps["emit"] = np.clip(crack[..., None] * tex.srgb("#ff3510")[None, None, :], 0, 1)
    bark_m = _mat("charred_bark", bark_maps, 2.0, normal_strength=1.2)
    cloth = util.material("ribbon_red", war_cloth(256, 463, "#7a1014"), double_sided=True)
    bm, bm_r = bmesh.new(), bmesh.new()
    tips = []

    def branch(p, d, ln, r, depth):
        pts = [V(p)]
        cur, dd = V(p), V(d)
        for _ in range(4):
            dd = (dd + V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.2, 0.4)))).normalized()
            cur = cur + dd * ln / 4
            pts.append(cur)
        util.tube(bm, util.catmull(pts, 3), lambda t: r * (1 - 0.75 * t) + 0.012, n=max(5, 4 + depth))
        if depth > 0:
            for _ in range(rnd.randint(2, 3)):
                nd = (dd + V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 0.7)))).normalized()
                branch(pts[rnd.randint(2, 4)], nd, ln * 0.62, r * 0.5, depth - 1)
        else:
            tips.append(pts[-1])

    s = height / 7.0
    trunk = [V((0, 0, -0.3)), V((0.25 * s, 0.1, 1.2 * s)), V((-0.2 * s, 0.25, 2.4 * s)), V((0.15 * s, -0.1, 3.3 * s))]
    util.tube(bm, util.catmull(trunk, 5), lambda t: 0.38 * s * (1 - 0.45 * t), n=10)
    for k in range(5):
        a = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
        d = V((math.cos(a), math.sin(a), 0))
        util.tube(bm, util.catmull([d * 0.1 + V((0, 0, 0.7 * s)), d * 0.55 * s + V((0, 0, 0.12)),
                                    d * 1.1 * s + V((0, 0, -0.15))], 3), lambda t: 0.2 * s * (1 - 0.8 * t), n=7)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rnd.uniform(-0.4, 0.4)
        branch(trunk[-1] - V((0, 0, rnd.uniform(0, 0.8 * s))), V((math.cos(a), math.sin(a), 0.9)),
               height * 0.42, 0.2 * s, 2)
    for k, tip in enumerate(tips[::7][:3]):
        top = tip - V((0, 0, 0.05))
        uvl = bm_r.loops.layers.uv.verify()
        vs = []
        for j in range(7):
            t = j / 6
            sway = 0.1 * math.sin(t * 4 + k)
            vs.append((bm_r.verts.new(top + V((-0.06 + sway, 0, -1.3 * t))), bm_r.verts.new(top + V((0.06 + sway, 0.02, -1.3 * t)))))
        for j in range(6):
            f = bm_r.faces.new((vs[j][0], vs[j][1], vs[j + 1][1], vs[j + 1][0]))
            for loop, uv in zip(f.loops, ((0, 1 - j / 6), (1, 1 - j / 6), (1, 1 - (j + 1) / 6), (0, 1 - (j + 1) / 6))):
                loop[uvl].uv = uv
    tree = finish("DeadTree", bm, bark_m, smooth=True)
    objs = [tree, finish("DeadTreeRibbons", bm_r, cloth)]
    objs.append(util.collider("DeadTreeCol", (0.8, 0.8, 3.0 * s), (0, 0, 1.5 * s)))
    return objs


def spiky_rocks(seed=23):
    """Cluster of jagged obsidian-basalt spikes with glowing lava veins (~5 m, up to 6 m tall)."""
    rnd = random.Random(seed)
    m = abyss_mats()
    bm = bmesh.new()
    specs = [(0, 0, 6.0, 1.1, 0.0)] + [
        (math.cos(a) * rnd.uniform(1.0, 1.9), math.sin(a) * rnd.uniform(1.0, 1.9), rnd.uniform(1.8, 4.2),
         rnd.uniform(0.45, 0.8), a) for a in [2 * math.pi * k / 7 + rnd.uniform(-0.3, 0.3) for k in range(7)]]
    for i, (x, y, h, r, a) in enumerate(specs):
        lean = 0.0 if i == 0 else rnd.uniform(0.15, 0.45)
        prof = [(r, -0.4), (r * 1.05, h * 0.15), (r * 0.7, h * 0.5), (r * 0.35, h * 0.8), (0.03, h)]
        rings = prism(bm, prof, sides=rnd.choice((5, 6)), rot=rnd.uniform(0, 1), loc=(0, 0, 0),
                      jitter=0.25, seed=seed * 10 + i)
        vs = [v for ring in rings for v in ring]
        for v in vs:
            v.co.x += v.co.z * lean * math.cos(a)
            v.co.y += v.co.z * lean * math.sin(a)
            v.co.x += x
            v.co.y += y
    for k in range(6):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(1.6, 2.6)
        nature.blob(bm, (math.cos(a) * rr, math.sin(a) * rr, 0.05), (0.5, 0.4, 0.3), 0.35, 1.8, seed + k, 1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = finish("SpikyRocks", bm, m["lava_rock"], uv=0.45)
    return [o, util.collider("SpikesCol", (2.6, 2.6, 4.0), (0, 0, 2.0), rot_z=0.3)]


def _dark_roof_mats(m):
    return {"tiles": util.material("black_tiles", tex.roof_tiles("#1c1a1f", 512, 441), normal_strength=1.0),
            "wood": m["lacquer"], "ridge": util.material("black_ridge", tex.stone("#141215", 256, 442, 0.1)),
            "gold": m["bronze"]}


def demon_gate():
    """Black fortress gatehouse: twin towers, an arched 7.6 m passage, a gate tower with a dark
    roof, red lanterns and a horned skull over the arch. Front faces -Y."""
    m = abyss_mats()
    rm = _dark_roof_mats(m)
    lantern_m = util.material("demon_lantern", tex.paper_lantern("#9e1512"), emission="#ff2a10",
                              emission_strength=3.0, normal_strength=0.3)
    objs = []
    hw, dep, top = 3.8, 3.4, 13.0
    spring, arch_r = 5.0, hw
    bm = bmesh.new()
    for sx in (-1, 1):
        x0, x1 = sorted((sx * hw, sx * 11.0))
        tapered_box(bm, x0, x1, -dep - 0.3, dep + 0.3, 0.0, top + 1.2,
                    sides=(0.35, 0.0, 0.35, 0.35) if sx < 0 else (0.0, 0.35, 0.35, 0.35))
    # passage: front/back spandrels above the arch and the vaulted ceiling
    uvl = bm.loops.layers.uv.verify()
    n = 16
    arcs = []
    for y in (-dep, dep):
        arcs.append([V((arch_r * math.cos(math.pi - math.pi * k / n), y, spring + arch_r * math.sin(math.pi * k / n)))
                     for k in range(n + 1)])
    for side, y in enumerate((-dep, dep)):
        a = [bm.verts.new(p) for p in arcs[side]]
        t = [bm.verts.new(V((p.x, y, top))) for p in arcs[side]]
        for k in range(n):
            f = bm.faces.new((a[k + 1], a[k], t[k], t[k + 1]) if side else (a[k], a[k + 1], t[k + 1], t[k]))
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.x * 0.25, loop.vert.co.z * 0.25)
    fa = [bm.verts.new(p) for p in arcs[0]]
    ba = [bm.verts.new(p) for p in arcs[1]]
    for k in range(n):
        f = bm.faces.new((fa[k], ba[k], ba[k + 1], fa[k + 1]))
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.y * 0.25, (k + (loop.vert in (fa[k + 1], ba[k + 1]))) / n * 3)
    # lintel top slab
    util.box(bm, (2 * hw, 2 * dep, 1.2), loc=(0, 0, top + 0.6))
    # merlons around the towers and the centre
    for sx in (-1, 1):
        cx = sx * 7.4
        for k in range(5):
            x = cx - 3.0 + k * 1.5
            for y in (-dep + 0.3, dep - 0.3):
                util.box(bm, (0.9, 0.55, 1.1), loc=(x, y, top + 1.75))
        for k in range(4):
            y = -2.4 + k * 1.6
            util.box(bm, (0.55, 0.9, 1.1), loc=(sx * 10.3, y, top + 1.75))
    objs.append(finish("GateStone", bm, m["blocks"], uv=0.25))
    # plinth course
    bm = bmesh.new()
    for sx in (-1, 1):
        x0, x1 = sorted((sx * hw, sx * 11.3))
        util.box(bm, (x1 - x0, 2 * dep + 1.0, 1.2), loc=((x0 + x1) / 2, 0, 0.6))
    objs.append(finish("GatePlinth", bm, m["rock"], uv=0.4))
    # glowing arrow slits and a rune cornice on the tower faces
    bm_s, bm_r = bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        cx = sx * 7.4
        for zz in (6.2, 10.4):
            yf = -(dep + 0.3 - 0.35 * zz / (top + 1.2))
            for dx in (-1.9, 1.9):
                util.box(bm_s, (0.28, 0.08, 1.3), loc=(cx + dx, yf - 0.02, zz))
        for y in (-1, 1):
            yf = y * (dep + 0.3 - 0.35 * 12.6 / (top + 1.2))
            util.box(bm_r, (7.2, 0.1, 0.35), loc=(cx - sx * 0.2, yf + y * 0.03, 12.6))
        xf = sx * (11.0 - 0.35 * 12.6 / (top + 1.2))
        util.box(bm_r, (0.1, 2 * dep, 0.35), loc=(xf + sx * 0.03, 0, 12.6))
    objs.append(finish("GateSlits", bm_s, glow("slit_glow", "#ff2a12", 2.5)))
    objs.append(finish("GateCornice", bm_r, m["runes"], uv=0.5))
    # glowing rune trim around the arch (front and back) and a band under the merlons
    bm = bmesh.new()
    for y in (-dep - 0.08, dep + 0.08):
        path = [V((0, y, 0)) + V((p.x * 1.06, 0, spring + (p.z - spring) * 1.06)) for p in arcs[0]]
        path = [V((path[0].x, y, 0.3))] + path + [V((path[-1].x, y, 0.3))]
        util.tube(bm, path, (0.16, 0.08), n=6, power=4.0, closed_ends=True)
    objs.append(finish("GateRuneTrim", bm, m["eye"]))
    # skull and horns over the arch
    bm_b, bm_e = bmesh.new(), bmesh.new()
    skull(bm_b, bm_e, V((0, -dep - 0.25, 9.4)), s=5.0, pitch=R(8))
    for sx in (-1, 1):
        pts = [V((sx * 0.7, -dep - 0.2, 10.6)), V((sx * 1.8, -dep - 0.5, 11.3)), V((sx * 2.6, -dep - 0.6, 12.8)),
               V((sx * 2.3, -dep - 0.5, 14.2))]
        util.tube(bm_b, util.catmull(pts, 5), lambda t: 0.35 * (1 - 0.9 * t) + 0.02, n=10)
    for sx in (-1, 1):
        for zz in (4.0, 8.0):
            skull(bm_b, bm_e, V((sx * 7.4, -(dep + 0.3 - 0.35 * zz / (top + 1.2)) - 0.2, zz)), s=1.6)
    objs.append(finish("GateSkulls", bm_b, m["bone"], uv=1.0, smooth=True))
    objs.append(finish("GateEyes", bm_e, m["eye"], smooth=True))
    # the gate tower on the lintel: red columns, back wall, dark hip roof
    bm_p, bm_s, bm_w = bmesh.new(), bmesh.new(), bmesh.new()
    for x in (-5.4, -1.8, 1.8, 5.4):
        for y in (-2.6, 2.6):
            arch.column(bm_p, bm_s, x, y, top + 1.2, 3.2, r=0.26)
    util.box(bm_w, (11.2, 0.4, 3.2), loc=(0, 2.6, top + 2.8))
    util.box(bm_w, (11.6, 5.8, 0.5), loc=(0, 0, top + 4.6))
    for sx in (-1, 1):
        util.box(bm_w, (0.4, 5.2, 3.2), loc=(sx * 5.4, 0, top + 2.8))
    objs.append(finish("GateTowerColumns", bm_p, m["lacquer"], uv=1.0, smooth=True))
    objs.append(finish("GateTowerBases", bm_s, m["obsidian"], uv=1.0))
    objs.append(finish("GateTowerWalls", bm_w, m["blocks"], uv=0.35))
    objs += arch.rect_roof("GateRoof", 0, 0, 7.6, 4.2, 3.0, rm, base_z=top + 4.8, lift=0.7, lift_len=2.0,
                           curve=1.8, flare=0.4, per_edge=16, rows=10)
    objs += arch.plaque_board({"gold": m["bronze"], "plaque": util.material(
        "demon_plaque", tex.plaque(512, 312, 3, field="#140808", ink="#d0281a"), normal_strength=0.5)},
        (0, -2.75, top + 3.9), w=3.0, h=1.0, tilt=0)
    # lanterns under the eaves and on iron brackets flanking the arch
    bm_l, bm_f = bmesh.new(), bmesh.new()
    for x in (-5.4, -1.8, 1.8, 5.4):
        lantern(bm_l, bm_f, (x, -3.6, top + 4.4), s=1.3)
    for sx in (-1, 1):
        x = sx * 4.8
        util.tube(bm_f, [V((x, -dep - 0.3, 7.2)), V((x, -dep - 1.2, 7.4)), V((x, -dep - 1.3, 7.1))], 0.05, n=6)
        lantern(bm_l, bm_f, (x, -dep - 1.3, 7.1), s=1.5)
    objs.append(finish("GateLanterns", bm_l, lantern_m, smooth=True))
    objs.append(finish("GateIronwork", bm_f, m["iron"], uv=2.0))
    # studded doors swung open against the passage walls
    bm_d, bm_n = bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        x = sx * (hw - 0.12)
        util.box(bm_d, (0.22, 3.6, 6.6), loc=(x, -dep + 2.0, 3.3))
        for zz in np.linspace(0.6, 5.8, 5):
            util.box(bm_n, (0.06, 3.6, 0.14), loc=(x - sx * 0.13, -dep + 2.0, zz))
            for yy in np.linspace(-dep + 0.5, -dep + 3.5, 5):
                util.sphere(bm_n, 0.07, loc=(x - sx * 0.15, yy, zz + 0.35), segs=6, rings=4)
    objs.append(finish("GateDoors", bm_d, m["lacquer"], uv=0.8))
    objs.append(finish("GateStuds", bm_n, m["iron"], uv=2.0))
    for sx in (-1, 1):
        objs.append(util.collider("GateTower", (7.6, 2 * dep + 1.0, top + 3.0), (sx * 7.4, 0, (top + 3.0) / 2)))
    objs.append(util.collider("GateLintel", (2 * hw, 2 * dep, top + 3 - spring - arch_r),
                              (0, 0, spring + arch_r + (top + 3 - spring - arch_r) / 2)))
    return objs


def fortress_wall(length=8.0, height=7.5):
    """8 m segment of battered black fortress wall with merlons, a crimson band and iron spikes."""
    m = abyss_mats()
    objs = []
    t = 1.4
    bm = bmesh.new()
    tapered_box(bm, -length / 2, length / 2, -t - 0.3, t + 0.3, 0.0, height, sides=(0, 0, 0.3, 0.3))
    util.box(bm, (length, 2 * t, 0.4), loc=(0, 0, height + 0.2))
    for k in range(5):
        x = -length / 2 + 0.8 + k * 1.6
        for y in (-t + 0.25, t - 0.25):
            util.box(bm, (1.0, 0.5, 1.2), loc=(x, y, height + 1.0))
    tapered_box(bm, -1.1, 1.1, -t - 1.4, -t, 0.0, height - 0.8, sides=(0.2, 0.2, 0.5, 0.0))
    objs.append(finish("WallStone", bm, m["blocks"], uv=0.25))
    bm = bmesh.new()
    util.box(bm, (length + 0.02, 2 * t + 0.62, 1.0), loc=(0, 0, 0.5))
    objs.append(finish("WallPlinth", bm, m["rock"], uv=0.4))
    bm = bmesh.new()
    util.box(bm, (length + 0.04, 0.12, 0.35), loc=(0, -t - 0.02, height - 0.6))
    util.box(bm, (length + 0.04, 0.12, 0.35), loc=(0, t + 0.02, height - 0.6))
    objs.append(finish("WallBand", bm, m["runes"], uv=0.5))
    bm_i = bmesh.new()
    for x in (-3.0, -2.0, 2.0, 3.0):
        for zz in (3.2, 4.4):
            util.cylinder(bm_i, 0.07, 0.001, 0.9, loc=(x, -t - 0.55, zz), segs=6,
                          rot=Matrix.Rotation(R(90), 4, "X"))
    objs.append(finish("WallSpikes", bm_i, m["iron"], uv=2.0))
    bm_b, bm_e = bmesh.new(), bmesh.new()
    skull(bm_b, bm_e, V((0, -t - 1.4 + 0.5 * 5.2 / (height - 0.8) - 0.3, 5.2)), s=2.2)
    objs.append(finish("WallSkull", bm_b, m["bone"], uv=1.0, smooth=True))
    objs.append(finish("WallSkullEyes", bm_e, m["eye"]))
    objs.append(util.collider("WallCol", (length, 2 * t + 0.6, height + 1.6), (0, 0, (height + 1.6) / 2)))
    return objs


def demon_tent():
    """Octagonal crimson war tent with an open front, sagging roof panels and guy ropes (~5.8 m)."""
    m = abyss_mats()
    rope = util.material("rope", tex.wood("#6b5a44", 128, 464, rings=30), normal_strength=0.3)
    sides, r_wall, r_roof, h_wall, apex = 8, 2.5, 2.95, 1.9, 4.3
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()

    def corner(k, r, z):
        a = R(90) + 2 * math.pi * (k + 0.5) / sides
        return V((r * math.cos(a), r * math.sin(a), z))

    front = 0
    for k in range(sides):
        a_mid = R(90) + 2 * math.pi * (k + 1) / sides
        if abs(math.sin(a_mid) + 1) < 0.2:
            front = k
    for k in range(sides):
        # roof panel (quad grid with sag)
        c0, c1 = corner(k, r_roof, h_wall + 0.1), corner(k + 1, r_roof, h_wall + 0.1)
        ap = V((0, 0, apex))
        rows = []
        for j in range(6):
            v = j / 5
            row = []
            for i in range(5):
                u = i / 4
                p = c0.lerp(c1, u).lerp(ap, v)
                sag = 0.18 * math.sin(math.pi * u) * math.sin(math.pi * min(1, v * 1.2)) * (1 - v)
                inward = V((p.x, p.y, 0)).normalized() if p.xy.length > 1e-3 else V((0, 0, 0))
                p = p - inward * sag - V((0, 0, sag * 0.5))
                row.append(bm.verts.new(p))
            rows.append(row)
        for j in range(5):
            for i in range(4):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uvl].uv = (uu / 4, vv / 5 * 0.9 + 0.02)
        # scalloped valance
        vr = []
        for i in range(9):
            u = i / 8
            p = c0.lerp(c1, u)
            drop = 0.35 + 0.12 * abs(math.sin(math.pi * u * 2))
            vr.append((bm.verts.new(p + V((0, 0, 0.02))), bm.verts.new(p - V((0, 0, drop)))))
        for i in range(8):
            f = bm.faces.new((vr[i][1], vr[i + 1][1], vr[i + 1][0], vr[i][0]))
            for loop, (uu, vv) in zip(f.loops, ((i, 0), (i + 1, 0), (i + 1, 1), (i, 1))):
                loop[uvl].uv = (uu / 8, vv * 0.1)
        if k == front:
            continue
        w0, w1 = corner(k, r_wall, 0.0), corner(k + 1, r_wall, 0.0)
        wv = [[bm.verts.new(w0.lerp(w1, i / 4) + V((0, 0, h_wall * j / 3)) + (
            V((w0.lerp(w1, i / 4).x, w0.lerp(w1, i / 4).y, 0)).normalized() * 0.08 * math.sin(math.pi * i / 4)
            * (1 - j / 3))) for i in range(5)] for j in range(4)]
        for j in range(3):
            for i in range(4):
                f = bm.faces.new((wv[j][i], wv[j][i + 1], wv[j + 1][i + 1], wv[j + 1][i]))
                for loop, (uu, vv) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uvl].uv = (uu / 4, vv / 3 * 0.8)
    # tied-back door flaps
    w0, w1 = corner(front, r_wall, 0.0), corner(front + 1, r_wall, 0.0)
    for c, other in ((w0, w1), (w1, w0)):
        tip = c.lerp(other, 0.22) + V((0, 0, 1.0))
        vs = [bm.verts.new(c), bm.verts.new(c + V((0, 0, h_wall))), bm.verts.new(tip)]
        f = bm.faces.new(vs)
        for loop, uv in zip(f.loops, ((0, 0), (0, 0.8), (0.3, 0.4))):
            loop[uvl].uv = uv
    tent = finish("TentCloth", bm, m["cloth"])
    bm_p, bm_r = bmesh.new(), bmesh.new()
    util.cylinder(bm_p, 0.07, 0.06, apex + 0.6, loc=(0, 0, (apex + 0.6) / 2), segs=8)
    util.cylinder(bm_p, 0.08, 0.001, 0.5, loc=(0, 0, apex + 0.85), segs=6)
    for k in range(sides):
        c = corner(k, r_wall, 0.0)
        util.cylinder(bm_p, 0.045, 0.045, h_wall + 0.1, loc=c + V((0, 0, (h_wall + 0.1) / 2)), segs=6)
        e = corner(k, r_roof, h_wall + 0.05)
        stake = corner(k, r_roof + 1.4, 0.0)
        util.tube(bm_r, [e, e.lerp(stake, 0.5) - V((0, 0, 0.05)), stake], 0.012, n=4)
        util.cylinder(bm_p, 0.03, 0.02, 0.35, loc=stake + V((0, 0, 0.1)), segs=5)
    poles = finish("TentPoles", bm_p, m["wood"], uv=1.0)
    ropes = finish("TentRopes", bm_r, rope, uv=2.0)
    # pennant on the centre pole
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    vs = [bm.verts.new(p) for p in (V((0.05, 0, apex + 0.55)), V((0.95, 0.05, apex + 0.4)),
                                      V((0.05, 0, apex + 0.2)))]
    f = bm.faces.new(vs)
    for loop, uv in zip(f.loops, ((0.1, 0.9), (0.9, 0.7), (0.1, 0.5))):
        loop[uvl].uv = uv
    pennant = finish("TentPennant", bm, m["cloth"])
    return [tent, poles, ropes, pennant, util.collider("TentCol", (4.9, 4.9, 2.4), (0, 0, 1.2), rot_z=R(22.5))]


def demon_banner(seed=31):
    """Black war pole with a tattered crimson blood-moon banner (~6.8 m)."""
    rnd = random.Random(seed)
    m = abyss_mats()
    flag = _mat("blood_moon_banner", blood_moon_banner(512), 1.5, double_sided=True, normal_strength=0.3)
    bm = bmesh.new()
    util.cylinder(bm, 0.08, 0.06, 6.6, loc=(0, 0, 3.3), segs=8)
    util.cylinder(bm, 0.04, 0.04, 1.8, loc=(0, 0, 6.2), segs=6, rot=Matrix.Rotation(R(90), 4, "Y"))
    pole = finish("BannerPole", bm, m["wood"], uv=1.0)
    bm_i = bmesh.new()
    util.cylinder(bm_i, 0.07, 0.001, 0.6, loc=(0, 0, 6.9), segs=4)
    util.cylinder(bm_i, 0.1, 0.1, 0.08, loc=(0, 0, 6.6), segs=8)
    for sx in (-1, 1):
        util.cylinder(bm_i, 0.06, 0.06, 0.1, loc=(sx * 0.9, 0, 6.2), segs=6, rot=Matrix.Rotation(R(90), 4, "Y"))
    tip = finish("BannerIron", bm_i, m["iron"], uv=2.0)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    cols, rows = 8, 14
    width, top, length = 1.6, 6.15, 3.9
    grid = []
    bottom = [length * (0.82 + 0.18 * rnd.random()) for _ in range(cols + 1)]
    for j in range(rows + 1):
        row = []
        for i in range(cols + 1):
            t = j / rows
            ln = bottom[i] if j == rows else length * t
            if j < rows:
                ln = min(ln, bottom[i])
            x = -width / 2 + width * i / cols
            y = -0.1 + 0.1 * math.sin(t * 4.0 + i * 0.5) * t
            row.append(bm.verts.new(V((x, y, top - ln))))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop in f.loops:
                co = loop.vert.co
                loop[uvl].uv = ((co.x + width / 2) / width, (co.z - (top - length)) / length)
    cloth = finish("BannerCloth", bm, flag)
    bm_b, bm_e = bmesh.new(), bmesh.new()
    util.box(bm_b, (0.8, 0.8, 0.5), loc=(0, 0, 0.25))
    base = finish("BannerBase", bm_b, m["blocks"], uv=0.6)
    bm_s = bmesh.new()
    for sx in (-1, 1):
        skull(bm_s, bm_e, V((sx * 0.9, -0.02, 5.75)), s=0.7, pitch=R(10))
    skulls = finish("BannerSkulls", bm_s, m["bone"], uv=2.0, smooth=True)
    sockets = finish("BannerSockets", bm_e, m["dark"])
    return [pole, tip, cloth, base, skulls, sockets, util.collider("BannerCol", (0.8, 0.8, 3.0), (0, 0, 1.5))]


def patriarch_throne():
    """Boss arena: a 26 x 27 m basalt platform (top 1.6 m) with a summoning-circle floor,
    front stairs, braziers, and a bone-and-obsidian throne at the back. Origin = arena centre."""
    m = abyss_mats()
    objs = []
    hw, y0, y1, h = 13.0, -12.0, 15.0, 1.6
    bm = bmesh.new()
    tapered_box(bm, -hw - 0.3, hw + 0.3, y0 - 0.3, y1 + 0.3, -0.6, h - 0.35, inset=0.3)
    objs.append(finish("ThroneBase", bm, m["blocks"], uv=0.3))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    # rune fascia under the lip, u along the perimeter
    corners = [V((-hw, y0, 0)), V((hw, y0, 0)), V((hw, y1, 0)), V((-hw, y1, 0))]
    acc = 0.0
    for a, b in zip(corners, corners[1:] + corners[:1]):
        ln = (b - a).length
        n = int(ln)
        out = V((b.y - a.y, a.x - b.x, 0)).normalized() * 0.02
        for k in range(n):
            p, q = a.lerp(b, k / n) + out, a.lerp(b, (k + 1) / n) + out
            vs = [bm.verts.new(p + V((0, 0, h - 0.35))), bm.verts.new(q + V((0, 0, h - 0.35))),
                  bm.verts.new(q + V((0, 0, h - 0.05))), bm.verts.new(p + V((0, 0, h - 0.05)))]
            f = bm.faces.new(vs)
            for loop, uv in zip(f.loops, ((0.3, 0), (0.7, 0), (0.7, 0.1), (0.3, 0.1))):
                loop[uvl].uv = (uv[0], uv[1] + 0.1 * (k % 9))
        acc += ln
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    objs.append(finish("ThroneRuneBand", bm, m["runes"]))
    # arena floor with the summoning circle (square uv: disc fills the platform width)
    floor_m = _mat("sigil_floor", sigil_floor(1024), 2.5, normal_strength=0.6)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    size = 2 * hw
    cy = 0.0
    k = 8
    vs = [[bm.verts.new(V((-hw + 2 * hw * i / k, y0 + (y1 - y0) * j / k, h))) for i in range(k + 1)]
          for j in range(k + 1)]
    for j in range(k):
        for i in range(k):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for loop in f.loops:
                co = loop.vert.co
                loop[uvl].uv = (co.x / size + 0.5, (co.y - cy) / size + 0.5)
    objs.append(finish("ThroneFloor", bm, floor_m))
    # lip
    bm = bmesh.new()
    for (sx, sy, lx, ly) in ((0, y0, 2 * hw + 0.4, 0.4), (0, y1, 2 * hw + 0.4, 0.4), (-hw, (y0 + y1) / 2, 0.4, y1 - y0),
                             (hw, (y0 + y1) / 2, 0.4, y1 - y0)):
        util.box(bm, (lx, ly, 0.12), loc=(sx, sy, h - 0.04))
    objs.append(finish("ThroneLip", bm, m["obsidian"], uv=0.8))
    # front stairs with cheek walls
    bm = bmesh.new()
    steps, sw, run = 5, 14.0, 0.5
    for s_ in range(steps):
        sh = h * (s_ + 1) / steps
        d = run * (steps - s_)
        util.box(bm, (sw, d, sh + 0.6), loc=(0, y0 - d / 2, (sh - 0.6) / 2))
    for sx in (-1, 1):
        tapered_box(bm, sx * sw / 2 - 0.5, sx * sw / 2 + 0.5, y0 - run * steps - 0.3, y0, -0.6, h + 0.5, inset=0.05)
    objs.append(finish("ThroneStairs", bm, m["blocks"], uv=0.4))
    # throne dais, seat and bone crown
    bm = bmesh.new()
    tapered_box(bm, -4.5, 4.5, 10.0, 14.6, h - 0.1, h + 0.7, inset=0.2)
    tapered_box(bm, -3.2, 3.2, 9.2, 10.2, h - 0.1, h + 0.35, inset=0.05)
    objs.append(finish("ThroneDais", bm, m["obsidian"], uv=0.6))
    bm_o, bm_c = bmesh.new(), bmesh.new()
    z = h + 0.7
    util.box(bm_o, (2.2, 1.6, 0.7), loc=(0, 12.2, z + 0.35))
    tapered_box(bm_o, -1.4, 1.4, 12.6, 13.3, z, z + 4.6, inset=0.25)
    for sx in (-1, 1):
        util.box(bm_o, (0.45, 1.5, 0.35), loc=(sx * 1.25, 12.2, z + 1.05))
        util.box(bm_o, (0.4, 0.4, 0.7), loc=(sx * 1.25, 11.6, z + 0.55))
    util.box(bm_c, (1.8, 1.3, 0.18), loc=(0, 12.1, z + 0.78))
    util.box(bm_c, (1.8, 0.16, 1.6), loc=(0, 12.55, z + 1.7))
    objs.append(finish("ThroneSeat", bm_o, m["obsidian"], uv=0.8))
    objs.append(finish("ThroneCushion", bm_c, util.material("throne_silk", tex.silk("#5e0b10", "#8a1a1c", 256, 465)),
                       uv=1.0))
    bm_b, bm_e = bmesh.new(), bmesh.new()
    for k in range(9):
        a = R(-70 + 140 * k / 8)
        base = V((0, 13.0, z + 4.0))
        d = V((math.sin(a), 0.1, math.cos(a)))
        ln = 2.6 - 0.9 * abs(k - 4) / 4
        util.tube(bm_b, util.catmull([base, base + d * ln * 0.5 + V((0, 0.1, 0)), base + d * ln + V((0, 0.3, 0.2))], 4),
                  lambda t: 0.16 * (1 - 0.85 * t) + 0.012, n=8)
    skull(bm_b, bm_e, V((0, 12.45, z + 4.2)), s=3.0)
    for sx in (-1, 1):
        skull(bm_b, bm_e, V((sx * 1.25, 11.25, z + 1.2)), s=1.0)
        util.tube(bm_b, util.catmull([V((sx * 2.2, 13.0, z)), V((sx * 3.0, 13.2, z + 2.0)),
                                      V((sx * 2.6, 13.1, z + 3.6)), V((sx * 1.9, 12.8, z + 4.4))], 5),
                  lambda t: 0.3 * (1 - 0.85 * t) + 0.02, n=10)
    objs.append(finish("ThroneBones", bm_b, m["bone"], uv=1.5, smooth=True))
    objs.append(finish("ThroneEyes", bm_e, m["eye"]))
    # obsidian pillars with fire bowls at the back corners, low braziers at the front corners
    bm_p, bm_m, bm_f, bm_ch = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        x, y = sx * 10.8, 12.6
        prism(bm_p, [(1.1, h - 0.05), (1.1, h + 0.5), (0.75, h + 0.6), (0.62, h + 5.2), (0.85, h + 5.5)],
              sides=6, loc=(x, y, 0))
        brazier(bm_m, bm_f, (x, y, h + 5.5 - 0.75 * 1.3), s=1.3, legs=False)
        chain(bm_ch, [V((x - sx * 0.6, y, h + 4.8)), V((sx * 6.0, 13.0, h + 3.0)), V((sx * 1.6, 13.0, z + 3.8))])
        for yy in (-10.5,):
            brazier(bm_m, bm_f, (sx * 11.3, yy, h), s=1.2)
    objs.append(finish("ThronePillars", bm_p, m["runes"], uv=None))
    objs.append(finish("ThroneBraziers", bm_m, m["bronze"], uv=1.5, smooth=True))
    objs.append(finish("ThroneFire", bm_f, m["fire"], smooth=True))
    objs.append(finish("ThroneChains", bm_ch, m["iron"], uv=3.0, smooth=True))
    # bone spikes along the back edge
    bm = bmesh.new()
    for k in range(12):
        x = -12.0 + k * (24.0 / 11)
        if abs(x) < 5.0:
            continue
        p = V((x, 14.6, h))
        util.tube(bm, [p, p + V((0.1, 0.2, 1.2)), p + V((0.05, -0.1, 2.3))], lambda t: 0.16 * (1 - t) + 0.01, n=7)
    objs.append(finish("ThroneSpikes", bm, m["bone"], uv=1.5, smooth=True))
    # collision: platform, stair ramp, dais + throne, pillars, braziers
    # platform collider 2 cm under the floor so the stair ramp never leaves a lip at the edge
    objs.append(util.collider("ThronePlatform", (2 * hw + 0.6, y1 - y0, h + 0.58), (0, (y0 + y1) / 2, (h - 0.62) / 2)))
    slope = h / (run * steps + 0.25)
    objs.append(ramp_collider("ThroneStairRamp", sw, -0.6, h, y0 - run * steps - 0.2 - 0.6 / slope, y0))
    objs.append(util.collider("ThroneDaisCol", (9.0, 5.0, 0.8), (0, 12.3, h + 0.3)))
    objs.append(util.collider("ThroneSeatCol", (3.0, 2.2, 5.3), (0, 12.6, z + 2.65)))
    for sx in (-1, 1):
        objs.append(util.collider("ThronePillarCol", (1.9, 1.9, 6.0), (sx * 10.8, 12.6, h + 3.0)))
        objs.append(util.collider("ThroneBrazierCol", (1.2, 1.2, 1.6), (sx * 11.3, -10.5, h + 0.8)))
    return objs


def heart_pool():
    """Still black mirror pool (r 3.9 m) with a stone rim and a horseshoe of rune stones
    that leaves the front (-Y) open. The surface faintly glows violet."""
    m = abyss_mats()
    rune_p = _mat("heart_runes", rune_stone(512, 434, "#1c1a20", "#a04dff", 1, 6), 1.8, normal_strength=0.6)
    candle_fire = glow("violet_fire", "#b36bff", 6.0)
    objs = []
    bm = bmesh.new()
    util.lathe(bm, [(5.0, -0.5), (5.0, 0.08), (4.8, 0.2), (4.1, 0.2), (3.95, 0.1), (3.9, -0.2), (3.0, -0.5)], segs=40)
    objs.append(finish("PoolRim", bm, m["blocks"], uv=0.6))
    bm = bmesh.new()
    disc(bm, (0, 0), 3.95, 40, z=0.04)
    objs.append(finish("PoolMirror", bm, _mat("heart_mirror", mirror_surface(256), 0.6, normal_strength=0.2)))
    bm = bmesh.new()
    bm_f, bm_c = bmesh.new(), bmesh.new()
    rnd = random.Random(8)
    for k in range(7):
        a = R(-90 + 55 + (360 - 110) * k / 6)
        p = V((math.cos(a) * 6.2, math.sin(a) * 6.2, 0))
        hgt = rnd.uniform(1.8, 2.8)
        rings = prism(bm, [(0.62, -0.4), (0.58, hgt * 0.7), (0.45, hgt), (0.12, hgt + 0.3)], sides=4,
                      rot=a + R(45), loc=p, jitter=0.12, seed=k)
        radial = V((math.cos(a), math.sin(a), 0))
        for ring in rings:
            for v in ring:
                d = V((v.co.x - p.x, v.co.y - p.y, 0))
                v.co -= radial * d.dot(radial) * 0.55
        cp = V((math.cos(a + 0.18) * 5.2, math.sin(a + 0.18) * 5.2, 0.0))
        util.cylinder(bm_c, 0.06, 0.06, 0.35, loc=cp + V((0, 0, 0.17)), segs=8)
        flame(bm_f, cp + V((0, 0, 0.35)), h=0.14, r=0.04)
        objs.append(util.collider(f"HeartStone{k}", (1.0, 1.0, hgt), (p.x, p.y, hgt / 2), rot_z=a))
    objs.append(finish("HeartStones", bm, rune_p))
    objs.append(finish("HeartCandles", bm_c, m["obsidian"], uv=2.0))
    objs.append(finish("HeartFlames", bm_f, candle_fire))
    return objs
def _rock_arch(bm, a, b, height, r=1.6, seed=0.0):
    """Natural rock arch between two ground points (Blender coordinates)."""
    a, b = V(a), V(b)
    pts = []
    for k in range(13):
        t = k / 12
        p = a.lerp(b, t) + V((0, 0, height * math.sin(math.pi * t)))
        pts.append(p)
    util.tube(bm, pts, lambda t: r * (1.35 - 0.55 * math.sin(math.pi * t)), n=10)
    for v in bm.verts:
        v.co += V((noise.noise(v.co * 0.45 + V((seed, 0, 0))), noise.noise(v.co * 0.45 + V((0, seed, 0))),
                   noise.noise(v.co * 0.45 + V((0, 0, seed))))) * 0.9


def abyss_terrain():
    """Blood Moon Abyss canyon (see tools/maps/blood_abyss.py): crimson soil floors and ledges,
    jagged basalt walls, glowing blood pools and two rock arches. Visible trimesh collision."""
    L = abyss_layout()
    soil = _mat("abyss_soil", crimson_soil(512), 1.4, normal_strength=1.0)
    rock = util.material("abyss_rock", basalt(512, 413, "#352c2e"), normal_strength=1.3)
    blood = _mat("blood", liquid(256), 1.6, normal_strength=0.4)
    x0, z0, x1, z1 = L.BOUNDS
    step = L.STEP
    nx, nz = int(round((x1 - x0) / step)), int(round((z1 - z0) / step))
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    grid, dist = [], []
    for j in range(nz + 1):
        gz = z0 + j * step
        row, drow = [], []
        for i in range(nx + 1):
            gx = x0 + i * step
            h = L.ground_height(gx, gz)
            d = L.carve(gx, gz)[1]
            w = L._sstep(1.0, 4.5, d)
            jx = w * 1.1 * noise.noise(V((gx * 0.23, gz * 0.23, 1.7)))
            jz = w * 1.1 * noise.noise(V((gx * 0.23, gz * 0.23, 5.3)))
            row.append(bm.verts.new(V((gx + jx, -(gz + jz), h))))
            drow.append(d)
        grid.append(row)
        dist.append(drow)
    for j in range(nz):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
            f.normal_update()
            n = f.normal
            dc = (dist[j][i] + dist[j + 1][i] + dist[j][i + 1] + dist[j + 1][i + 1]) / 4
            steep = n.z < 0.74 or dc > 2.5
            f.material_index = 1 if steep else 0
            for loop in f.loops:
                co = loop.vert.co
                if not steep:
                    loop[uvl].uv = (co.x * 0.1, co.y * 0.1)
                elif abs(n.x) > abs(n.y):
                    loop[uvl].uv = (co.y * 0.09, co.z * 0.09)
                else:
                    loop[uvl].uv = (co.x * 0.09, co.z * 0.09)
    ground = util.mesh_object("AbyssGround-col", bm, [soil, rock], smooth=True)
    objs = [ground]
    # blood pools: liquid sitting in the depressions (no collision)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    for pool in L.POOLS:
        px, pz, rx, rz, depth, seed = pool
        level = L.pool_level(pool)
        c = bm.verts.new(V((px, -pz, level)))
        ring = []
        for k in range(40):
            a = 2 * math.pi * k / 40
            ring.append(bm.verts.new(V((px + rx * 1.02 * math.cos(a), -(pz + rz * 1.02 * math.sin(a)), level))))
        for k in range(40):
            f = bm.faces.new((c, ring[(k + 1) % 40], ring[k]))
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.x * 0.12, loop.vert.co.y * 0.12)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    objs.append(util.mesh_object("BloodPools", bm, blood, smooth=False))
    # rock arches over the canyon mouth and the grotto passage
    for k, (a, b, hgt) in enumerate((((22.0, 56.0), (45.0, 54.0), 13.0), ((-51.0, -15.0), (-56.0, -27.0), 9.0))):
        bm = bmesh.new()
        pa = V((a[0], -a[1], L.ground_height(*a) - 2.0))
        pb = V((b[0], -b[1], L.ground_height(*b) - 2.0))
        _rock_arch(bm, pa, pb, hgt, r=1.8, seed=k * 3.1)
        o = util.mesh_object(f"RockArch{k}", bm, rock, smooth=True)
        util.box_uv(o, 0.12)
        objs.append(o)
    return objs


# --------------------------------------------------------------------------
# Celestial Sky Isles
# --------------------------------------------------------------------------
def sky_platform(radius=20.0, seed=41, plaza=0.0):
    """Walkable floating island: a flat grassy top (trimesh collision, z = 0 out to ~0.95 r)
    over an inverted rocky cone with hanging roots, vines and small spirit crystals.
    plaza > 0 paves a central marble circle of that radius, edged with jade."""
    rnd = random.Random(seed)
    m = sky_mats()
    seg = 64 if radius > 12 else 44
    depth = radius * 1.35

    def rim(a, f=1.0):
        c, s_ = math.cos(a), math.sin(a)
        return radius * f * (1 + 0.03 * noise.noise(V((c * 1.4, s_ * 1.4, seed))) +
                             0.012 * noise.noise(V((c * 4.1, s_ * 4.1, seed + 3.3))))

    angles = [2 * math.pi * k / seg for k in range(seg)]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    top = [(0.25, 0.0), (0.5, 0.0), (0.7, 0.0), (0.85, 0.0), (0.95, 0.0), (0.99, -0.12), (1.01, -0.45),
           (1.02, -0.9)]
    edge = len(top) - 3  # faces outward of the 0.99 ring are the rounded rim (cliff material)
    circles = []
    if plaza > 0:
        # paved circle: plain circles (no outline noise) of the plaza and its jade border
        pf = plaza / radius
        circles = [(pf * 0.5, 2), (pf, 2), (pf + 0.6 / radius, 3)]
        top = [(f, 0.0) for f in (pf * 0.5, pf, pf + 0.6 / radius)] + [t for t in top if t[0] > pf + 1.5 / radius]
        edge = len(top) - 3
    centre = bm.verts.new(V((0, 0, 0)))
    rings = []
    for f, z in top:
        exact = any(abs(f - c) < 1e-6 for c, _ in circles)
        rings.append([bm.verts.new(V(((radius * f if exact else rim(a, f)) * math.cos(a),
                                      (radius * f if exact else rim(a, f)) * math.sin(a), z))) for a in angles])
    mat_of = {c: mi for c, mi in circles}
    for k in range(seg):
        k2 = (k + 1) % seg
        f = bm.faces.new((centre, rings[0][k], rings[0][k2]))
        f.material_index = 2 if circles else 0
        for loop in f.loops:
            loop[uvl].uv = (loop.vert.co.x * (0.25 if circles else 0.12), loop.vert.co.y * (0.25 if circles else 0.12))
    for j in range(len(rings) - 1):
        mi = mat_of.get(top[j + 1][0], 1 if j >= edge else 0)
        for k in range(seg):
            k2 = (k + 1) % seg
            f = bm.faces.new((rings[j][k], rings[j + 1][k], rings[j + 1][k2], rings[j][k2]))
            f.material_index = mi
            for loop in f.loops:
                co = loop.vert.co
                if mi == 1:
                    loop[uvl].uv = (math.atan2(co.y, co.x) * radius * 0.1, co.z * 0.1)
                elif mi == 2:
                    loop[uvl].uv = (co.x * 0.25, co.y * 0.25)
                else:
                    loop[uvl].uv = (co.x * 0.12, co.y * 0.12)
    paving = util.material("sky_paving", tex.paving("#efe2c8", 512, 582, tiles=4, gap=0.006, moss=0.1),
                           normal_strength=0.8)
    top_o = util.mesh_object("IslandTop-col", bm, [m["grass"], m["cliff"], paving, m["jade"]], smooth=True)
    # rocky underside
    bm = bmesh.new()
    prof = [(1.02, -0.9), (1.0, -1.6), (0.94, -0.1), (0.82, -0.22), (0.66, -0.4), (0.47, -0.58), (0.3, -0.74),
            (0.15, -0.88), (0.05, -0.97), (0.01, -1.0)]
    under = []
    for j, (f, z) in enumerate(prof):
        zz = z if j < 2 else z * depth
        row = []
        for a in angles:
            d = noise.fractal(V((math.cos(a) * 1.8, math.sin(a) * 1.8, zz * 0.12 + seed)), 0.8, 2.0, 4) if j > 1 else 0
            r = rim(a, f) * (1 + 0.22 * d)
            row.append(V((r * math.cos(a), r * math.sin(a), zz + d * 1.6)))
        under.append(row)
    util.loft(bm, under, closed=True, uv_scale=(radius * 0.35, 0.1))
    rock = util.mesh_object("IslandRock", bm, m["cliff"], smooth=True)
    objs = [top_o, rock]
    # hanging roots and vines
    bm_r = bmesh.new()
    for k in range(int(radius * 0.8)):
        a = rnd.uniform(0, 2 * math.pi)
        j = rnd.choice((2, 3, 4))
        f, z = prof[j]
        r = rim(a, f) * 0.92
        p = V((r * math.cos(a), r * math.sin(a), z * depth))
        ln = rnd.uniform(3, 9) * radius / 20
        pts = [p]
        for s_ in range(5):
            pts.append(pts[-1] + V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), -ln / 5)))
        util.tube(bm_r, util.catmull(pts, 3), lambda t: 0.16 * (1 - 0.85 * t) + 0.015, n=6)
    for k in range(int(radius * 0.7)):
        a = rnd.uniform(0, 2 * math.pi)
        r = rim(a, 1.015)
        p = V((r * math.cos(a), r * math.sin(a), -0.6))
        out = V((math.cos(a), math.sin(a), 0))
        ln = rnd.uniform(2, 5)
        pts = [p, p + out * 0.3 - V((0, 0, ln * 0.3)), p + out * 0.2 - V((0, 0, ln * 0.7)), p + out * 0.4 - V((0, 0, ln))]
        util.tube(bm_r, util.catmull(pts, 3), 0.035, n=4)
    objs.append(finish("IslandRoots", bm_r, m["roots"], uv=1.0, smooth=True))
    # spirit crystals embedded in the underside
    bm_c = bmesh.new()
    for k in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        f, z = prof[3 + k % 3]
        r = rim(a, f) * (1.0 + 0.1)
        base = V((r * math.cos(a), r * math.sin(a), z * depth))
        for j in range(3):
            d = (V((math.cos(a), math.sin(a), -0.6)) + V((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0))).normalized()
            ln = rnd.uniform(0.8, 1.8) * radius / 20
            vs = [v for ring in prism(bm_c, [(0.18 * ln, 0), (0.18 * ln, ln * 0.75), (0.01, ln)], sides=6)
                  for v in ring]
            rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.transform(bm_c, matrix=Matrix.Translation(base) @ rot, verts=vs)
    objs.append(finish("IslandCrystals", bm_c, m["crystal"]))
    return objs


def _deck_z(y, length, rise, flat):
    """Deck height along a bridge: arched, or ramped up to a flat central section of half-width flat."""
    t = abs(y) / (length / 2)
    if flat <= 0:
        return rise * math.cos(math.pi / 2 * t)
    ramp = (length / 2 - abs(y)) / (length / 2 - flat)
    ramp = min(1.0, max(0.0, ramp))
    return rise * ramp * ramp * (3 - 2 * ramp)


def jade_bridge(length=30.0, width=4.4, rise=1.0, belvedere=0.0):
    """Floating white-marble bridge with jade balustrade panels and gold finials, running along Y
    (ends at z = 0). With belvedere > 0 a railed octagonal viewing platform of that apothem sits
    at mid-span with jade lamps and a pendant keel beneath."""
    m = sky_mats()
    objs = []
    n = int(length / 1.0)
    ys = [-length / 2 + length * i / n for i in range(n + 1)]
    zs = [_deck_z(y, length, rise, belvedere) for y in ys]
    hw = width / 2
    cross = [(-hw, 0.0), (hw, 0.0), (hw, -0.45), (hw - 0.5, -0.8), (-hw + 0.5, -0.8), (-hw, -0.45)]
    bm = bmesh.new()
    rings = [[V((x, y, z + dz)) for x, dz in cross] for y, z in zip(ys, zs)]
    util.loft(bm, rings, closed=True, cap_start=True, cap_end=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    objs.append(finish("BridgeDeck", bm, m["marble"], uv=0.3))
    # jade fascia strip and gold edge along both sides
    bm_j, bm_g = bmesh.new(), bmesh.new()
    for sx in (-1, 1):
        util.tube(bm_j, [V((sx * (hw + 0.02), y, z - 0.22)) for y, z in zip(ys, zs)], (0.04, 0.16), n=4,
                  power=4.0)
        util.tube(bm_g, [V((sx * (hw + 0.03), y, z - 0.02)) for y, z in zip(ys, zs)], (0.035, 0.035), n=6)
    # balustrade
    bm_p = bmesh.new()
    rail_len = length / 2 - 2.6
    spacing = 2.0
    cols = []
    y = -rail_len
    while y <= rail_len + 1e-6:
        if belvedere <= 0 or abs(y) >= belvedere - 0.2:
            cols.append(y)
        y += spacing
    runs = []
    for y in cols:
        z = _deck_z(y, length, rise, belvedere)
        end = abs(abs(y) - rail_len) < 1e-3 or (belvedere > 0 and abs(abs(y) - belvedere) < spacing * 0.6)
        for sx in (-1, 1):
            x = sx * (hw - 0.18)
            sz = 0.34 if end else 0.22
            hh = 1.35 if end else 1.0
            util.box(bm_p, (sz, sz, hh), loc=(x, y, z + hh / 2))
            util.lathe(bm_g, [(sz * 0.55, 0), (sz * 0.7, 0.06), (sz * 0.35, 0.16), (sz * 0.5, 0.26),
                              (0.001, 0.4 if end else 0.3)], segs=10, loc=(x, y, z + hh))
    for a, b in zip(cols[:-1], cols[1:]):
        if b - a > spacing * 1.5:
            continue
        runs.append((a, b))
        for sx in (-1, 1):
            x = sx * (hw - 0.18)
            za, zb = _deck_z(a, length, rise, belvedere), _deck_z(b, length, rise, belvedere)
            mid = (a + b) / 2
            zm = (za + zb) / 2
            ang = math.atan2(zb - za, b - a)
            util.box(bm_j, (0.07, b - a - 0.24, 0.55), loc=(x, mid, zm + 0.45), rot=Matrix.Rotation(ang, 4, "X"))
            util.box(bm_p, (0.16, b - a, 0.12), loc=(x, mid, zm + 0.94), rot=Matrix.Rotation(ang, 4, "X"))
            util.box(bm_p, (0.2, b - a, 0.12), loc=(x, mid, zm + 0.1), rot=Matrix.Rotation(ang, 4, "X"))
    walk = []
    if belvedere > 0:
        ap = belvedere
        cr = ap / math.cos(R(22.5))
        zb = rise
        oct_pts = [V((cr * math.cos(R(22.5 + 45 * k)), cr * math.sin(R(22.5 + 45 * k)), 0)) for k in range(8)]
        bm = bmesh.new()
        prism(bm, [(cr + 0.25, zb - 0.9), (cr + 0.25, zb - 0.15), (cr, zb)], sides=8, rot=R(22.5), cap_top=True)
        prism(bm, [(cr + 0.25, zb - 0.9), (cr * 0.6, zb - 2.6), (0.6, zb - 4.4), (0.05, zb - 5.2)], sides=8,
              rot=R(22.5), cap_top=False)
        objs.append(finish("BelvedereBase", bm, m["marble"], uv=0.3))
        bm = bmesh.new()
        disc(bm, (0, 0), ap - 0.6, 48, z=zb + 0.012)
        objs.append(finish("BelvedereInlay", bm, _mat("belvedere_star", star_map(512, 542), 1.5)))
        for k in range(8):
            a, b = oct_pts[k] * ((ap - 0.18) / ap), oct_pts[(k + 1) % 8] * ((ap - 0.18) / ap)
            mid = (a + b) / 2
            d = b - a
            ang = math.atan2(d.y, d.x)
            facing_y = abs(mid.x) < 0.5
            segs = [(a, b)]
            if facing_y:
                gap = hw + 0.1
                segs = [(a, V((-gap if a.x < 0 else gap, a.y, 0))), (V((-gap if b.x < 0 else gap, b.y, 0)), b)]
            for p, q in segs:
                ln = (q - p).length
                if ln < 0.3:
                    continue
                c = (p + q) / 2
                util.box(bm_j, (ln - 0.2, 0.07, 0.55), loc=(c.x, c.y, zb + 0.45), rot=Matrix.Rotation(ang, 4, "Z"))
                util.box(bm_p, (ln, 0.16, 0.12), loc=(c.x, c.y, zb + 0.94), rot=Matrix.Rotation(ang, 4, "Z"))
                util.box(bm_p, (ln, 0.2, 0.12), loc=(c.x, c.y, zb + 0.1), rot=Matrix.Rotation(ang, 4, "Z"))
                for e in (p, q):
                    util.box(bm_p, (0.26, 0.26, 1.1), loc=(e.x, e.y, zb + 0.55))
                    util.lathe(bm_g, [(0.15, 0), (0.18, 0.06), (0.09, 0.16), (0.13, 0.26), (0.001, 0.36)], segs=10,
                               loc=(e.x, e.y, zb + 1.1))
                walk.append(util.collider("BelvedereRail", (ln, 0.3, 1.2), (c.x, c.y, zb + 0.6), rot_z=ang))
        # jade lamps at four corners, pendant under the keel
        bm_l = bmesh.new()
        for k in (0, 2, 4, 6):
            p = oct_pts[k] * ((ap - 0.18) / ap)
            util.cylinder(bm_p, 0.12, 0.16, 2.2, loc=(p.x, p.y, zb + 1.1), segs=8)
            util.lathe(bm_g, [(0.3, 0), (0.34, 0.08), (0.001, 0.1)], segs=12, loc=(p.x, p.y, zb + 2.2))
            util.sphere(bm_l, 0.24, loc=(p.x, p.y, zb + 2.52), segs=12, rings=8)
            util.lathe(bm_g, [(0.2, 0), (0.001, 0.25)], segs=8, loc=(p.x, p.y, zb + 2.72))
        util.lathe(bm_g, [(0.001, zb - 5.2), (0.3, zb - 5.4), (0.001, zb - 6.6)], segs=12)
        util.sphere(bm_l, 0.3, loc=(0, 0, zb - 6.9), segs=12, rings=8)
        objs.append(finish("BelvedereLamps", bm_l, m["lamp"], smooth=True))
    objs.append(finish("BridgeJade", bm_j, m["jade"], uv=1.0))
    objs.append(finish("BridgeGold", bm_g, m["gold"], uv=2.0, smooth=True))
    objs.append(finish("BridgeBalustrade", bm_p, m["marble"], uv=1.0))
    # collision: the walkable deck surface as a thin trimesh, rails as boxes
    bm = bmesh.new()
    vr = [(bm.verts.new(V((-hw, y, z))), bm.verts.new(V((hw, y, z)))) for y, z in zip(ys, zs)]
    for i in range(n):
        bm.faces.new((vr[i][0], vr[i][1], vr[i + 1][1], vr[i + 1][0]))
    if belvedere > 0:
        c = bm.verts.new(V((0, 0, rise)))
        ring = [bm.verts.new(p + V((0, 0, rise))) for p in oct_pts]
        for k in range(8):
            bm.faces.new((c, ring[k], ring[(k + 1) % 8]))
    objs.append(util.mesh_object("BridgeWalk-colonly", bm, None, smooth=False))
    for a, b in runs:
        za, zb2 = _deck_z(a, length, rise, belvedere), _deck_z(b, length, rise, belvedere)
        for sx in (-1, 1):
            objs.append(util.collider("BridgeRail", (0.3, b - a, 1.4), (sx * (hw - 0.18), (a + b) / 2,
                                                                        (za + zb2) / 2 + 0.55)))
    return objs + walk


def ascension_stair(rise=26.0, run=56.0, width=5.0, seed=51):
    """Stair of floating marble slabs from (0, 0, 0) up to (0, run, rise), with 4 m landings at both
    ends (the upper one rests on the destination isle), gold nosings and floating jade lamps.
    Collision is one smooth ramp."""
    rnd = random.Random(seed)
    m = sky_mats()
    n = max(4, int(run / 1.2))
    bm_s, bm_g, bm_l, bm_c = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    cloud = util.material("stair_cloud", color="#f4f7ff", rough=0.9, emission="#dfe8ff", emission_strength=0.4)
    for i in range(n):
        y = (i + 0.5) * run / n
        z = rise * y / run + 0.1
        x = rnd.uniform(-0.12, 0.12)
        depth = run / n - 0.14
        vs = util.box(bm_s, (width, depth, 0.42), loc=(0, 0, -0.21))
        vs += util.box(bm_s, (width * 0.8, depth * 0.7, 0.3), loc=(0, 0, -0.55))
        g = util.box(bm_g, (width + 0.02, 0.08, 0.1), loc=(0, -depth / 2 + 0.03, -0.04))
        yaw = R(rnd.uniform(-1.5, 1.5))
        xform_verts(bm_s, vs, (x, y, z), yaw=yaw)
        xform_verts(bm_g, g, (x, y, z), yaw=yaw)
        if i % 3 == 1:
            nature.blob(bm_c, (x + rnd.uniform(-1.5, 1.5), y, z - 1.1), (1.6, 0.9, 0.45), 0.35, 1.2, seed + i, 2)
        if i % 6 == 3:
            for sx in (-1, 1):
                p = V((x + sx * (width / 2 + 0.35), y, z))
                util.cylinder(bm_g, 0.05, 0.05, 1.5, loc=p + V((0, 0, 0.35)), segs=6)
                util.lathe(bm_g, [(0.2, 0), (0.24, 0.06), (0.001, 0.08)], segs=10, loc=p + V((0, 0, 1.1)))
                util.sphere(bm_l, 0.2, loc=p + V((0, 0, 1.36)), segs=10, rings=6)
                util.lathe(bm_g, [(0.001, 0), (0.14, -0.2), (0.001, -0.5)], segs=8, loc=p - V((0, 0, 0.4)))
    for y0, z in ((-4.0, 0.0), (run, rise)):
        util.box(bm_s, (width + 0.6, 4.0, 0.5), loc=(0, y0 + 2.0, z - 0.25))
        util.box(bm_s, (width, 3.4, 0.5), loc=(0, y0 + 2.0, z - 0.7))
        util.box(bm_g, (width + 0.64, 4.04, 0.08), loc=(0, y0 + 2.0, z - 0.3))
    objs = [finish("StairSlabs", bm_s, m["marble"], uv=0.4), finish("StairGold", bm_g, m["gold"], uv=2.0),
            finish("StairLamps", bm_l, m["lamp"], smooth=True), finish("StairClouds", bm_c, cloud, uv=0.5, smooth=True)]
    objs.append(ramp_collider("StairRamp", width, 0.0, rise, 0.0, run))
    objs.append(util.collider("LandingLow", (width + 0.6, 4.0, 0.5), (0, -2.0, -0.25)))
    objs.append(util.collider("LandingHigh", (width + 0.6, 4.0, 0.5), (0, run + 2.0, rise - 0.25)))
    return objs


def _octagon_base(bm, steps, ap_top, step_w=0.6, step_h=0.25, z_top=0.5, bottom=-0.4):
    """Stepped octagonal plinth: a top of apothem ap_top at z_top above `steps` treads of
    step_w x step_h; the outer riser runs down to `bottom` (pair with _frustum_collider)."""
    c = 1.0 / math.cos(R(22.5))
    prof = [((ap_top + step_w * steps) * c, bottom)]
    for k in range(steps, 0, -1):
        z = z_top - step_h * (k - 1)
        prof += [((ap_top + step_w * k) * c, z), ((ap_top + step_w * (k - 1)) * c, z)]
    prism(bm, prof, sides=8, rot=R(22.5), cap_top=True, v_scale=0.5)


def _frustum_collider(name, ap_top, z_top, ap_bottom, z_bottom):
    bm = bmesh.new()
    c = 1.0 / math.cos(R(22.5))
    for ap, z in ((ap_top, z_top), (ap_bottom, z_bottom)):
        for k in range(8):
            a = R(22.5 + 45 * k)
            bm.verts.new(V((ap * c * math.cos(a), ap * c * math.sin(a), z)))
    return convex(name, bm)


def celestial_ruins(seed=61):
    """Ruined celestial palace: a cracked octagonal marble dais (apothem 6.6, top 0.5 m, ramped
    edges) ringed by broken columns, a fallen jade roof and an architrave fragment (~26 m)."""
    rnd = random.Random(seed)
    m = sky_mats()
    rm = {"tiles": m["jade_tiles"], "wood": m["beam"], "ridge": m["ridge"], "gold": m["gold"]}
    objs = []
    bm = bmesh.new()
    _octagon_base(bm, 2, 6.6, step_w=0.8, step_h=0.25, z_top=0.5, bottom=-0.5)
    objs.append(finish("RuinsDais", bm, m["cracked"], uv=0.3))
    bm = bmesh.new()
    disc(bm, (0, 0), 6.3, 48, z=0.508)
    maps = cracked_marble(512, 523)
    u, v = tex.grid(512)
    r = np.sqrt((u - 0.5) ** 2 + (v - 0.5) ** 2)
    ring = np.clip((1 - tex.sstep(0.0, 0.006, np.abs(r - 0.44))) + (1 - tex.sstep(0.0, 0.004, np.abs(r - 0.4))), 0, 1)
    ring *= tex.sstep(0.25, 0.5, tex.fbm(512, 6, 3, 0.5, 9))
    maps["albedo"] = tex.lerp(maps["albedo"], tex.srgb("#c9a24a"), ring)
    objs.append(finish("RuinsFloor", bm, util.material("ruins_floor", maps, normal_strength=0.8)))
    bm_c, bm_g, bm_b = bmesh.new(), bmesh.new(), bmesh.new()
    standing = []
    # column angles leave clear lanes to the east, north and south-west (bridge and stair heads)
    for k, deg in enumerate((30, 60, 120, 150, 175, 200, 262, 290, 318, 345)):
        a = R(deg)
        p = V((math.cos(a) * 10.4, math.sin(a) * 10.4, 0))
        kind = rnd.random()
        if k in (2, 3):
            hgt = 8.0
        elif abs(math.sin(a) + 1) < 0.35:
            hgt = rnd.uniform(0.6, 1.6)  # front: low stumps keep the view open
        else:
            hgt = rnd.uniform(1.8, 3.2) if kind > 0.5 else rnd.uniform(4.0, 6.0)
        util.lathe(bm_b, [(0.8, -0.2), (0.8, 0.25), (0.62, 0.35), (0.55, 0.55), (0.001, 0.55)], segs=16, loc=p)
        util.cylinder(bm_g, 0.5, 0.5, 0.14, loc=p + V((0, 0, 0.72)), segs=16)
        if hgt >= 8.0:
            util.cylinder(bm_c, 0.46, 0.42, hgt - 0.55, loc=p + V((0, 0, 0.55 + (hgt - 0.55) / 2)), segs=16)
            util.cylinder(bm_g, 0.47, 0.47, 0.14, loc=p + V((0, 0, hgt - 0.6)), segs=16)
            util.box(bm_b, (1.2, 1.2, 0.35), loc=p + V((0, 0, hgt + 0.17)))
            arch.dougong(bm_b, p.x, p.y, hgt + 0.35, 0.8)
            standing.append((p, hgt))
        else:
            rings = prism(bm_c, [(0.46, 0.55), (0.45, hgt * 0.8), (0.44, hgt)], sides=16, rot=0.0, cap_top=True,
                          v_scale=0.25)
            for v in rings[-1]:
                v.co.z += rnd.uniform(-0.35, 0.35)
        objs.append(util.collider(f"Column{k}", (1.1, 1.1, max(hgt, 1.0)), (p.x, p.y, max(hgt, 1.0) / 2)))
    if len(standing) >= 2:
        (pa, ha), (pb, _) = standing[0], standing[-1]
        mid = (pa + pb) / 2
        d = pb - pa
        ang = math.atan2(d.y, d.x)
        util.box(bm_b, (d.length + 1.0, 0.8, 0.9), loc=(mid.x, mid.y, ha + 1.5), rot=Matrix.Rotation(ang, 4, "Z"))
    # toppled column drums outside the dais
    for k, (x, y, yaw) in enumerate(((-11.5, -4.0, 0.3), (9.5, -8.5, -0.9), (-7.0, 11.5, 1.8))):
        for j in range(3):
            c = V((x, y, 0.42)) + V((math.cos(yaw), math.sin(yaw), 0)) * j * 1.35
            vs = util.cylinder(bm_c, 0.44, 0.44, 1.2, loc=(0, 0, 0), segs=16)
            xform_verts(bm_c, vs, c + V((0, 0, rnd.uniform(-0.05, 0.05))), yaw=yaw + rnd.uniform(-0.15, 0.15),
                        roll=R(90))
        objs.append(util.collider(f"Drums{k}", (4.2, 1.0, 0.9), (x + math.cos(yaw) * 1.35, y + math.sin(yaw) * 1.35, 0.42),
                                  rot_z=yaw))
    objs.append(finish("RuinsColumns", bm_c, m["carved"], uv=0.5))
    objs.append(finish("RuinsGoldBands", bm_g, m["gold"], uv=1.0))
    objs.append(finish("RuinsStone", bm_b, m["marble"], uv=0.6))
    # fallen roof fragment, tilted into the ground
    roof = arch.rect_roof("FallenRoof", 0, 0, 3.4, 1.9, 1.5, rm, base_z=0.0, lift=0.45, lift_len=1.1,
                          per_edge=12, rows=8)
    for o in roof:
        o.rotation_euler = (R(18), R(-24), R(35))
        o.location = (-9.5, 6.0, -0.4)
        util.apply_transform(o)
    objs += roof
    objs.append(util.collider("FallenRoofCol", (6.0, 3.6, 1.6), (-9.5, 6.0, 0.6), rot_z=R(35)))
    objs.append(_frustum_collider("RuinsDaisCol", 6.6, 0.5, 8.4, -0.5))
    return objs


def star_pavilion():
    """Open octagonal star-gazing pavilion: a star-map floor, lapis columns and roof crowned
    by an armillary sphere, a bronze celestial globe in the middle. Entrance at -Y."""
    m = sky_mats()
    lapis = util.material("lapis_lacquer", tex.lacquer("#1f3a7a", 256, 569, 0.15), normal_strength=0.3)
    rm = {"tiles": m["blue_tiles"], "wood": lapis, "ridge": m["ridge"], "gold": m["gold"]}
    objs = []
    bm = bmesh.new()
    _octagon_base(bm, 3, 5.6, step_w=0.5, step_h=0.15, z_top=0.45, bottom=-0.3)
    objs.append(finish("PavilionBase", bm, m["marble"], uv=0.4))
    bm = bmesh.new()
    disc(bm, (0, 0), 5.2, 64, z=0.458)
    objs.append(finish("StarFloor", bm, _mat("star_map", star_map(1024), 2.0, normal_strength=0.5)))
    cr = 4.9
    pts = [V((cr * math.cos(R(22.5 + 45 * k)), cr * math.sin(R(22.5 + 45 * k)), 0)) for k in range(8)]
    bm_p, bm_s, bm_b, bm_r, bm_g = (bmesh.new() for _ in range(5))
    for p in pts:
        arch.column(bm_p, bm_s, p.x, p.y, 0.45, 3.9, r=0.2)
        util.cylinder(bm_g, 0.23, 0.23, 0.1, loc=p + V((0, 0, 4.1)), segs=12)
        objs.append(util.collider("PavilionColumn", (0.45, 0.45, 3.9), (p.x, p.y, 2.4)))
    for k in range(8):
        a, b = pts[k], pts[(k + 1) % 8]
        mid = (a + b) / 2
        d = b - a
        ang = math.atan2(d.y, d.x)
        rot = Matrix.Rotation(ang, 4, "Z")
        util.box(bm_b, (d.length, 0.24, 0.4), loc=(mid.x, mid.y, 4.55), rot=rot)
        util.box(bm_b, (d.length, 0.14, 0.18), loc=(mid.x, mid.y, 4.05), rot=rot)
        if mid.y < -3.0:
            continue  # entrance
        util.box(bm_r, (d.length - 0.4, 0.14, 0.1), loc=(mid.x, mid.y, 1.35), rot=rot)
        util.box(bm_r, (d.length - 0.4, 0.2, 0.14), loc=(mid.x, mid.y, 0.52), rot=rot)
        for t in (-0.25, 0.0, 0.25):
            q = mid + d * t
            util.box(bm_r, (0.1, 0.1, 0.8), loc=(q.x, q.y, 0.95))
        objs.append(util.collider("PavilionRail", (d.length, 0.3, 1.0), (mid.x, mid.y, 0.95), rot_z=ang))
    # bronze celestial globe on a pedestal at the centre
    util.lathe(bm_s, [(0.35, 0.45), (0.25, 0.6), (0.14, 0.7), (0.14, 1.1), (0.3, 1.18), (0.001, 1.2)], segs=16,
               cap_bottom=True)
    objs.append(finish("PavilionColumns", bm_p, lapis, uv=1.0, smooth=True))
    objs.append(finish("PavilionColumnBases", bm_s, m["marble"], uv=1.0))
    objs.append(finish("PavilionBeams", bm_b, m["beam"], uv=1.0))
    objs.append(finish("PavilionRails", bm_r, m["marble"], uv=1.0))
    objs += arch.poly_roof("StarRoof", 0, 0, 6.4, 8, 3.2, rm, base_z=4.75, rot=R(22.5), lift=0.55, lift_len=1.4,
                           curve=1.7, per_edge=10, rows=12)
    # armillary sphere above the finial
    top = 4.75 + 3.2 * (0.97 / 0.97) + 1.0
    util.cylinder(bm_g, 0.05, 0.05, 1.2, loc=(0, 0, top), segs=8)
    for k, (ax, ang) in enumerate((("X", 0), ("Y", 0), ("X", 60))):
        ring = [V((0.55 * math.cos(t), 0, 0.55 * math.sin(t))) for t in np.linspace(0, 2 * math.pi, 25)]
        rot = Matrix.Rotation(R(90 * k), 3, "Z") @ Matrix.Rotation(R(ang), 3, "X")
        util.tube(bm_g, [rot @ p + V((0, 0, top + 0.9)) for p in ring], 0.03, n=6, closed_ends=False)
    util.sphere(bm_g, 0.14, loc=(0, 0, top + 0.9), segs=10, rings=6)
    globe = bmesh.new()
    util.sphere(globe, 0.36, loc=(0, 0, 1.58), segs=20, rings=12)
    objs.append(finish("CelestialGlobe", globe, _mat("globe", star_map(256, 543), 1.0), uv=None, smooth=True))
    for t in np.linspace(0, math.pi, 2):
        ring = [V((0.46 * math.cos(u), 0.46 * math.sin(u) * math.cos(t), 0.46 * math.sin(u) * math.sin(t)))
                for u in np.linspace(0, 2 * math.pi, 25)]
        util.tube(bm_g, [p + V((0, 0, 1.58)) for p in ring], 0.025, n=5, closed_ends=False)
    objs.append(finish("PavilionGold", bm_g, m["gold"], uv=2.0, smooth=True))
    objs.append(util.collider("GlobeCol", (0.8, 0.8, 1.6), (0, 0, 1.2)))
    objs.append(_frustum_collider("PavilionBaseCol", 5.6, 0.45, 7.1, -0.3))
    return objs


def cloud_gate():
    """Tall three-bay white-marble paifang with jade roofs, cloud-carved beams and gold
    ornaments (13.6 m wide, 12.8 m tall; 4.5 m clear central opening). Front faces -Y."""
    m = sky_mats()
    rm = {"tiles": m["jade_tiles"], "wood": m["carved"], "ridge": m["ridge"], "gold": m["gold"]}
    objs = []
    xs = [(-6.4, 8.2), (-2.6, 10.6), (2.6, 10.6), (6.4, 8.2)]
    bm_p, bm_d, bm_g = bmesh.new(), bmesh.new(), bmesh.new()
    for x, h in xs:
        prism(bm_p, [(0.52, 0.0), (0.5, h)], sides=4, loc=(x, 0, 0), v_scale=0.25)
        util.box(bm_d, (1.1, 2.4, 1.6), loc=(x, 0, 0.8))
        util.box(bm_d, (0.9, 0.6, 2.2), loc=(x, -1.05, 1.1))
        util.box(bm_d, (0.9, 0.6, 2.2), loc=(x, 1.05, 1.1))
        util.lathe(bm_g, [(0.38, 0), (0.44, 0.12), (0.001, 0.2)], segs=8, loc=(x, 0, h))
        objs.append(util.collider("GatePillar", (1.1, 2.4, h), (x, 0, h / 2)))
    objs.append(finish("CloudGatePillars", bm_p, m["carved"]))
    objs.append(finish("CloudGateDrums", bm_d, m["marble"], uv=0.6))
    bm_b = bmesh.new()
    util.box(bm_b, (5.9, 0.55, 0.8), loc=(0, 0, 9.2))
    util.box(bm_b, (5.9, 0.45, 0.55), loc=(0, 0, 6.5))
    for sx in (-1, 1):
        util.box(bm_b, (4.4, 0.5, 0.7), loc=(sx * 4.5, 0, 7.0))
        util.box(bm_b, (4.4, 0.4, 0.45), loc=(sx * 4.5, 0, 5.3))
    objs.append(finish("CloudGateBeams", bm_b, m["carved"], uv=0.4))
    bm_k = bmesh.new()
    for x in (-1.8, -0.6, 0.6, 1.8):
        arch.dougong(bm_k, x, 0, 9.6, 0.5)
    for sx in (-1, 1):
        for x in (sx * 3.6, sx * 4.5, sx * 5.4):
            arch.dougong(bm_k, x, 0, 7.35, 0.42)
    objs.append(finish("CloudGateBrackets", bm_k, m["beam"], uv=1.5))
    objs += arch.rect_roof("CloudRoofMain", 0, 0, 3.7, 1.4, 1.6, rm, base_z=10.1, lift=0.55, lift_len=1.2, curve=1.7,
                           flare=0.45, per_edge=16, rows=10)
    for sx in (-1, 1):
        objs += arch.rect_roof(f"CloudRoofSide{'L' if sx > 0 else 'R'}", sx * 4.5, 0, 2.5, 1.15, 1.2, rm,
                               base_z=7.85, lift=0.45, lift_len=0.9, curve=1.7, flare=0.4, per_edge=12, rows=8)
    plaque_m = util.material("cloud_plaque", tex.plaque(512, 313, 4, field="#1d3f78", ink="#f0d070"),
                             normal_strength=0.5)
    objs += arch.plaque_board({"gold": m["gold"], "plaque": plaque_m}, (0, -0.32, 7.85), w=2.6, h=0.9, tilt=0)
    # gold cloud scrolls on the main beam ends
    for sx in (-1, 1):
        curl = [V((sx * (2.95 + 0.28 * math.cos(t) * (1 - t / 9)), -0.3, 9.2 + 0.28 * math.sin(t) * (1 - t / 9)))
                for t in np.linspace(0, 7, 30)]
        util.tube(bm_g, curl, 0.05, n=6)
    objs.append(finish("CloudGateGold", bm_g, m["gold"], uv=2.0, smooth=True))
    return objs


def crystal_cluster(seed=71):
    """Spirit-vein outcrop: glowing cyan hexagonal crystals (up to 3.2 m) bursting from a rock."""
    rnd = random.Random(seed)
    m = sky_mats()
    bm = bmesh.new()
    nature.blob(bm, (0, 0, 0.1), (1.5, 1.2, 0.8), 0.35, 1.4, seed, 3)
    rock = finish("CrystalRock", bm, util.material("vein_rock", tex.stone("#5d6470", 256, 572, 0.4)), uv=0.6,
                  smooth=True)
    bm, bm_i = bmesh.new(), bmesh.new()
    specs = [(0, 0, 0.0, 3.2, 0.42)] + [(rnd.uniform(-1, 1), rnd.uniform(-0.8, 0.8), rnd.uniform(0.2, 0.75),
                                         rnd.uniform(0.9, 2.4), rnd.uniform(0.16, 0.34)) for _ in range(9)]
    for i, (x, y, tilt, ln, r) in enumerate(specs):
        a = math.atan2(y, x) if (x or y) else 0.0
        rings = prism(bm, [(r, -0.3), (r * 1.05, ln * 0.72), (0.02, ln)], sides=6, rot=rnd.uniform(0, 1))
        vs = [v for ring in rings for v in ring]
        xform_verts(bm, vs, (x, y, 0.5), yaw=a - math.pi / 2, pitch=-tilt)
        if i < 4:
            core = [v for ring in prism(bm_i, [(r * 0.45, 0.0), (r * 0.45, ln * 0.6), (0.02, ln * 0.8)], sides=6)
                    for v in ring]
            xform_verts(bm_i, core, (x, y, 0.5), yaw=a - math.pi / 2, pitch=-tilt)
    for k in range(10):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(1.4, 2.4)
        ln = rnd.uniform(0.25, 0.6)
        vs = [v for ring in prism(bm, [(0.08, -0.1), (0.08, ln * 0.7), (0.01, ln)], sides=6) for v in ring]
        xform_verts(bm, vs, (math.cos(a) * rr, math.sin(a) * rr, 0), yaw=a - math.pi / 2, pitch=-rnd.uniform(0.2, 0.8))
    crystals = finish("SpiritCrystals", bm, util.material("vein_crystal", color="#7fe9ff", rough=0.08,
                                                         emission="#2fb6ff", emission_strength=2.6))
    cores = finish("SpiritCrystalCores", bm_i, m["crystal_core"])
    return [rock, crystals, cores, util.collider("CrystalCol", (2.6, 2.2, 2.6), (0, 0, 1.3))]


def tribulation_altar():
    """Octagonal summit altar (top apothem 9 m, 0.75 m high, ramped steps) with a taiji-bagua
    disc and eight lightning-rod pillars hung with thunder talismans."""
    bronze = util.material("rod_bronze", tex.metal("#8a6a3a", 256, 573, rough=0.3, patina="#3f7f6c",
                                                   patina_amt=0.3), normal_strength=0.6)
    talisman = util.material("talisman", _talisman_tex(256), double_sided=True, normal_strength=0.2)
    spark = glow("thunder_orb", "#bfe4ff", 7.0)
    objs = []
    bm = bmesh.new()
    _octagon_base(bm, 3, 9.0, step_w=0.6, step_h=0.25, z_top=0.75, bottom=-0.4)
    objs.append(finish("AltarBase", bm, util.material("altar_granite", tex.stone("#b9b5ab", 512, 574, 0.25),
                                                      normal_strength=0.6), uv=0.3))
    bm = bmesh.new()
    disc(bm, (0, 0), 8.8, 64, z=0.758)
    objs.append(finish("TaijiDisc", bm, _mat("taiji_bagua", taiji_bagua(1024), 2.0, normal_strength=0.4)))
    bm_p, bm_r, bm_o, bm_t = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    uvl = bm_t.loops.layers.uv.verify()
    cr = 8.35
    for k in range(8):
        a = R(22.5 + 45 * k)
        p = V((cr * math.cos(a), cr * math.sin(a), 0.75))
        prism(bm_p, [(0.62, -0.05), (0.62, 0.35), (0.48, 0.45), (0.44, 4.6), (0.6, 4.8), (0.6, 5.0), (0.2, 5.3)],
              sides=4, rot=a + R(45), loc=p, v_scale=0.25)
        for zz in (1.2, 3.8):
            util.cylinder(bm_r, 0.36, 0.36, 0.14, loc=p + V((0, 0, zz)), segs=8)
        util.cylinder(bm_r, 0.09, 0.012, 3.2, loc=p + V((0, 0, 5.3 + 1.6)), segs=8)
        for j in range(3):
            util.tube(bm_r, [p + V((0.18 * math.cos(t), 0.18 * math.sin(t), 5.6 + j * 0.45)) for t in
                             np.linspace(0, 2 * math.pi, 13)], 0.025, n=5, closed_ends=False)
        util.sphere(bm_o, 0.2, loc=p + V((0, 0, 5.35)), segs=12, rings=8)
        util.sphere(bm_o, 0.07, loc=p + V((0, 0, 8.5)), segs=8, rings=5)
        # two talismans hanging from the upper band, facing the centre and outward
        for side in (-1, 1):
            d = V((math.cos(a), math.sin(a), 0)) * side * 0.46
            t = V((-math.sin(a), math.cos(a), 0))
            top = p + d + V((0, 0, 3.7))
            sway = V((0, 0, 0)) + d.normalized() * 0.08
            vs = [bm_t.verts.new(top - t * 0.16), bm_t.verts.new(top + t * 0.16),
                  bm_t.verts.new(top + t * 0.16 - V((0, 0, 1.0)) + sway), bm_t.verts.new(top - t * 0.16 - V((0, 0, 1.0)) + sway)]
            f = bm_t.faces.new(vs)
            for loop, uv in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                loop[uvl].uv = uv
        objs.append(util.collider(f"RodPillar{k}", (1.0, 1.0, 5.3), (p.x, p.y, 0.75 + 2.65), rot_z=a))
    objs.append(finish("RodPillars", bm_p, util.material("pillar_granite", tex.stone("#9c988f", 256, 575, 0.3)),
                       uv=None))
    objs.append(finish("LightningRods", bm_r, bronze, uv=2.0, smooth=True))
    objs.append(finish("ThunderOrbs", bm_o, spark, smooth=True))
    objs.append(finish("Talismans", bm_t, talisman))
    objs.append(_frustum_collider("AltarBaseCol", 9.0, 0.75, 10.8, -0.4))
    return objs


def _talisman_tex(size=256, seed=581):
    """Yellow paper talisman with red brush script (u across, v up)."""
    u, v = tex.grid(size)
    n = tex.fbm(size, 8, 4, 0.5, seed)
    col = tex.lerp(tex.srgb("#e8c85a"), tex.srgb("#f4dc86"), n)
    script = glyph_column(size, 1, 5, seed + 1, stroke=0.018, margin=0.25)
    border = ((u < 0.08) | (u > 0.92) | (v < 0.05) | (v > 0.95)).astype(np.float32) * 0.8
    col = tex.lerp(col, tex.srgb("#b3161a"), np.clip(script + border, 0, 1))
    return tex.result(col, 0.8, 0.0, n * 0.2)


ASSETS = {
    "abyss_terrain": abyss_terrain,
    "blood_altar": blood_altar,
    "demon_obelisk": demon_obelisk,
    "prison_cage": prison_cage,
    "bone_pile": bone_pile,
    "dead_tree": dead_tree,
    "spiky_rocks": spiky_rocks,
    "demon_gate": demon_gate,
    "fortress_wall": fortress_wall,
    "demon_tent": demon_tent,
    "demon_banner": demon_banner,
    "patriarch_throne": patriarch_throne,
    "heart_pool": heart_pool,
    "sky_platform_large": lambda: sky_platform(20.0, 41, plaza=7.0),
    "sky_platform_small": lambda: sky_platform(9.0, 43),
    "jade_bridge": lambda: jade_bridge(30.0, rise=1.0),
    "jade_bridge_long": lambda: jade_bridge(60.0, rise=1.5, belvedere=9.0),
    "celestial_ruins": celestial_ruins,
    "star_pavilion": star_pavilion,
    "cloud_gate": cloud_gate,
    "crystal_cluster": crystal_cluster,
    "tribulation_altar": tribulation_altar,
    "ascension_stair": lambda: ascension_stair(26.0, 56.0),
    "sky_steps": lambda: ascension_stair(10.0, 22.0, seed=53),
}

"""Procedural, tileable PBR texture generation with numpy.

Every generator returns a dict with float32 arrays in [0, 1]:
    albedo : (H, W, 3) sRGB colour
    rough  : (H, W)    roughness
    metal  : (H, W)    metallic
    height : (H, W)    height used to derive a tangent-space normal map
Row 0 is the bottom of the image (Blender / OpenGL convention, v = 0).
"""
import math

import numpy as np


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise(size, cells, rng, sx=None):
    """Tileable value noise. `cells` lattice cells across the image."""
    cy = cells
    cx = sx if sx is not None else cells
    g = rng.random((cy, cx)).astype(np.float32)
    ys = np.arange(size, dtype=np.float32) / size * cy
    xs = np.arange(size, dtype=np.float32) / size * cx
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = _smooth(ys - y0)[:, None]
    fx = _smooth(xs - x0)[None, :]
    y1 = (y0 + 1) % cy
    x1 = (x0 + 1) % cx
    y0 %= cy
    x0 %= cx
    v00 = g[y0[:, None], x0[None, :]]
    v01 = g[y0[:, None], x1[None, :]]
    v10 = g[y1[:, None], x0[None, :]]
    v11 = g[y1[:, None], x1[None, :]]
    a = v00 + (v01 - v00) * fx
    b = v10 + (v11 - v10) * fx
    return a + (b - a) * fy


def fbm(size, cells=4, octaves=5, persistence=0.5, seed=0, stretch=1):
    """Tileable fractal noise in [0, 1]. `stretch` elongates along v."""
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, total = 1.0, 0.0
    c = cells
    for _ in range(octaves):
        if c > size // 2:
            break
        out += amp * value_noise(size, max(1, c // stretch), rng, sx=c)
        total += amp
        amp *= persistence
        c *= 2
    out /= total
    lo, hi = out.min(), out.max()
    return (out - lo) / max(hi - lo, 1e-6)


def grid(size):
    v, u = np.mgrid[0:size, 0:size].astype(np.float32)
    return (u + 0.5) / size, (v + 0.5) / size


def lerp(a, b, t):
    a = np.asarray(a, np.float32)
    b = np.asarray(b, np.float32)
    t = np.asarray(t, np.float32)
    if t.ndim == 2 and (a.ndim in (1, 3) or b.ndim in (1, 3)):
        t = t[..., None]
    return a + (b - a) * t


def srgb(hexstr):
    hexstr = hexstr.lstrip("#")
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def stamp_curve(mask, pts, radius, size, value=1.0):
    """Rasterise a thick poly-line (uv points, wraps) into mask (max blend)."""
    r = max(1, int(math.ceil(radius * size)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(xx * xx + yy * yy) / (radius * size)
    disc = np.clip(1.0 - d, 0.0, 1.0)
    disc = np.clip(disc * 2.5, 0.0, 1.0) * value
    for (u, v) in pts:
        cx = int(u * size)
        cy = int(v * size)
        ys = (np.arange(cy - r, cy + r + 1)) % size
        xs = (np.arange(cx - r, cx + r + 1)) % size
        sub = mask[np.ix_(ys, xs)]
        mask[np.ix_(ys, xs)] = np.maximum(sub, disc)
    return mask


def cloud_curl(cx, cy, scale, turns=1.6, flip=1.0, rot=0.0, steps=90):
    """Points of an auspicious-cloud (xiangyun) spiral curl."""
    pts = []
    for i in range(steps):
        t = i / (steps - 1)
        ang = flip * t * turns * 2 * math.pi + rot
        rad = scale * (1.0 - 0.8 * t)
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def xiangyun_mask(size, count=6, seed=3, scale=0.07, thick=0.006):
    """Scattered auspicious cloud motifs: a tail stroke ending in twin curls."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((size, size), np.float32)
    cells = int(math.sqrt(count)) or 1
    for gy in range(cells):
        for gx in range(cells):
            cx = (gx + 0.5 + rng.uniform(-0.15, 0.15)) / cells
            cy = (gy + 0.5 + rng.uniform(-0.15, 0.15)) / cells
            s = scale * rng.uniform(0.8, 1.2)
            flip = 1.0 if (gx + gy) % 2 == 0 else -1.0
            pts = cloud_curl(cx - s * 0.9 * flip, cy, s, turns=1.3, flip=flip, rot=0)
            pts += cloud_curl(cx + s * 0.9 * flip, cy + s * 0.2, s * 0.8, turns=1.3,
                              flip=-flip, rot=math.pi)
            pts += cloud_curl(cx, cy + s * 0.9, s * 0.6, turns=1.1, flip=flip, rot=math.pi / 2)
            # trailing wisp
            for i in range(40):
                t = i / 39
                pts.append((cx + flip * (-s * 1.5 - t * s * 2.2),
                            cy - s * 0.9 + math.sin(t * math.pi) * s * 0.4))
            stamp_curve(mask, pts, thick, size)
    return mask


def huiwen_band(size, reps=8, line=0.12):
    """Greek-key / huiwen meander band pattern (tileable along u)."""
    cell = size // reps
    unit = np.zeros((cell, cell), np.float32)
    k = max(1, int(cell * line))
    # draw a square spiral in the cell
    x0, y0, x1, y1 = k, k, cell - k, cell - k
    step = 2 * k
    path = []
    while x1 - x0 > step and y1 - y0 > step:
        path.append((x0, y0, x1, y0 + k))
        path.append((x1 - k, y0, x1, y1))
        path.append((x0 + step, y1 - k, x1, y1))
        path.append((x0 + step, y0 + step, x0 + step + k, y1))
        x0 += step
        y0 += step
        x1 -= step
        y1 -= step
    for (a, b, c, d) in path:
        unit[b:d, a:c] = 1.0
    unit[:k, :] = 1.0
    band = np.tile(unit, (1, reps))
    band = band[:, :size]
    if band.shape[1] < size:
        band = np.pad(band, ((0, 0), (0, size - band.shape[1])))
    return band


def weave(size, period=4.0):
    u, v = grid(size)
    a = np.sin(u * size * 2 * math.pi / period)
    b = np.sin(v * size * 2 * math.pi / period)
    w = np.where(((np.floor(u * size / period) + np.floor(v * size / period)) % 2) == 0, a, b)
    return (w * 0.5 + 0.5).astype(np.float32)


def normal_from_height(h, strength=2.0):
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    n = np.stack([-dx * strength * h.shape[1] / 256.0,
                  -dy * strength * h.shape[0] / 256.0,
                  np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5).astype(np.float32)


def result(albedo, rough, metal=None, height=None):
    s = albedo.shape[0]
    return {
        "albedo": np.clip(albedo, 0, 1).astype(np.float32),
        "rough": np.clip(rough if np.ndim(rough) else np.full((s, s), rough), 0, 1).astype(np.float32),
        "metal": np.clip(metal if metal is not None and np.ndim(metal) else
                         np.full((s, s), metal or 0.0), 0, 1).astype(np.float32),
        "height": None if height is None else height.astype(np.float32),
    }


# --------------------------------------------------------------------------
# cloth
# --------------------------------------------------------------------------
def silk(base, motif, size=512, seed=1, motif_count=9, motif_scale=0.06, sheen=0.25):
    """Silk damask: fine weave + tonal auspicious-cloud damask pattern."""
    base = srgb(base)
    motif = srgb(motif)
    w = weave(size, 3.0)
    n = fbm(size, 4, 5, 0.55, seed)
    m = xiangyun_mask(size, motif_count, seed + 7, motif_scale, 0.0045)
    col = lerp(base, motif, m * 0.85)
    col = col * (0.92 + 0.08 * n)[..., None] * (0.97 + 0.03 * w)[..., None]
    rough = 0.62 - m * sheen + (n - 0.5) * 0.08
    height = w * 0.35 + m * 0.5 + n * 0.15
    return result(col, rough, 0.0, height)


def embroidery_trim(base, thread, size=512, seed=2, metallic_thread=True):
    """Band trim: u runs along the band. Huiwen border lines + cloud curls."""
    base = srgb(base)
    thread = srgb(thread)
    u, v = grid(size)
    w = weave(size, 3.0)
    border = ((np.abs(v - 0.08) < 0.03) | (np.abs(v - 0.92) < 0.03)).astype(np.float32)
    key = np.zeros((size, size), np.float32)
    hb = huiwen_band(size, reps=6)
    bh = hb.shape[0]
    y0 = int(size * 0.18)
    key[y0:y0 + bh, :] = hb[: min(bh, size - y0)]
    key = key[:, :size]
    curls = np.zeros((size, size), np.float32)
    reps = 4
    for i in range(reps):
        cx = (i + 0.5) / reps
        pts = cloud_curl(cx - 0.035, 0.72, 0.05, 1.2, 1.0)
        pts += cloud_curl(cx + 0.035, 0.72, 0.05, 1.2, -1.0, math.pi)
        stamp_curve(curls, pts, 0.006, size)
    pat = np.clip(border + key * 0.0 + curls, 0, 1)
    # the key pattern sits between the border lines, drawn thinner
    pat = np.clip(pat + np.where((v > 0.14) & (v < 0.5), key, 0) * 0.9, 0, 1)
    n = fbm(size, 8, 4, 0.5, seed)
    col = lerp(base * (0.9 + 0.1 * n)[..., None], thread * (0.85 + 0.15 * w)[..., None], pat)
    rough = lerp(0.7, 0.35 if metallic_thread else 0.55, pat)
    metal = pat * (0.85 if metallic_thread else 0.0)
    height = w * 0.3 + pat * 0.8
    return result(col, rough, metal, height)


def leather(color, size=256, seed=4):
    c = srgb(color)
    n = fbm(size, 16, 4, 0.6, seed)
    col = c * (0.8 + 0.3 * n)[..., None]
    return result(col, 0.55 + n * 0.2, 0.0, n)


def sheer(color, size=256, seed=5):
    c = srgb(color)
    w = weave(size, 2.0)
    n = fbm(size, 4, 3, 0.5, seed)
    col = c * (0.9 + 0.1 * n)[..., None]
    return result(col, 0.45, 0.0, w * 0.2)


# --------------------------------------------------------------------------
# character
# --------------------------------------------------------------------------
FACE_WARP = 0.6   # longitude warp: the face gets (1 + k) times the texel density of the back


def lon_to_u(lon):
    """Head UV u for a longitude (0 = the face). Denser texels toward the front."""
    return 0.5 + (lon + FACE_WARP * math.sin(lon)) / (2 * math.pi)


def u_to_lon(u):
    """Inverse of lon_to_u (vectorised Newton iterations)."""
    target = (np.asarray(u, np.float64) - 0.5) * 2 * math.pi
    lon = target / (1 + FACE_WARP)
    for _ in range(8):
        f = lon + FACE_WARP * np.sin(lon) - target
        lon = lon - f / (1 + FACE_WARP * np.cos(lon))
    return lon.astype(np.float32)


def skin_detail(size, seed, scale=1.0):
    """Micro relief shared by all skin: pores, fine skin lines and soft mottling.

    Returns (height, pore mask, mottling noise).
    """
    c = max(8, int(size * 0.35 * scale))
    pores_n = fbm(size, c, 2, 0.45, seed + 1)
    pores = sstep(0.62, 0.82, pores_n)
    lines_a = fbm(size, max(4, c // 3), 3, 0.5, seed + 3, stretch=6)
    lines_b = np.rot90(fbm(size, max(4, c // 3), 3, 0.5, seed + 4, stretch=6))
    lines = np.abs(lines_a - 0.5) + np.abs(lines_b - 0.5)
    fine = fbm(size, max(8, c * 2), 2, 0.5, seed + 5) if c * 2 <= size // 2 else pores_n
    mottle = fbm(size, 8, 5, 0.55, seed)
    height = 0.55 - pores * 0.22 - (lines < 0.12) * 0.1 + fine * 0.12 + mottle * 0.06
    return height.astype(np.float32), pores, mottle


def skin(tone, size=1024, seed=11, face=None):
    """Realistic skin: pores, skin lines, sub-dermal colour variation.

    face: dict(brow, lip, liner, blush, female, beard, age) paints facial
    features in head UV space (u warped by lon_to_u, v = asin(z)/pi + 0.5).
    """
    tone = srgb(tone)
    u, v = grid(size)
    height, pores, mottle = skin_detail(size, seed, 1.0 if face else 0.5)
    red = fbm(size, 6, 4, 0.5, seed + 2)
    blue = fbm(size, 5, 4, 0.5, seed + 6)
    col = tone * (0.94 + 0.09 * mottle)[..., None]
    # haemoglobin (warm) and venous (cool) variation under the surface
    col = lerp(col, col * np.array([1.06, 0.88, 0.86], np.float32), red * 0.35)
    col = lerp(col, col * np.array([0.93, 0.97, 1.04], np.float32), blue * 0.2)
    col = col * (1.0 - pores * 0.025)[..., None]
    rough = 0.52 + pores * 0.1 - mottle * 0.04
    rng = np.random.default_rng(seed + 9)
    # a few faint freckles / moles
    spots = np.zeros((size, size), np.float32)
    for _ in range(40 if face else 12):
        cx, cy = rng.random(2)
        r = rng.uniform(0.0012, 0.003)
        spots = np.maximum(spots, np.exp(-(((u - cx) ** 2 + (v - cy) ** 2) / r ** 2)) * rng.uniform(0.2, 0.6))
    col = lerp(col, col * np.array([0.72, 0.58, 0.5], np.float32), spots * 0.5)
    if face:
        du = u_to_lon(u)                     # longitude, 0 at front
        lat = np.arcsin(np.clip(np.sin((v - 0.5) * math.pi), -1, 1))

        def blob(cu, cv, su, sv):
            return np.exp(-(((du - cu) / su) ** 2 + ((lat - cv) / sv) ** 2))

        fem = face.get("female", False)
        age = face.get("age", 0.0)
        beard = face.get("beard", 0.0 if fem else 0.35)
        # warm centre of the face: nose, cheeks, ears are redder; forehead a little sallow
        flush = blob(0.0, -0.32, 0.18, 0.14) + 0.7 * (blob(0.55, -0.28, 0.3, 0.2) + blob(-0.55, -0.28, 0.3, 0.2))
        col = lerp(col, col * np.array([1.08, 0.86, 0.84], np.float32), np.clip(flush, 0, 1) * 0.5)
        col = lerp(col, col * np.array([1.03, 1.0, 0.9], np.float32), blob(0.0, 0.4, 0.5, 0.2) * 0.4)
        # blush
        blush = blob(0.62, -0.3, 0.3, 0.2) + blob(-0.62, -0.3, 0.3, 0.2)
        col = lerp(col, srgb(face["blush"]), np.clip(blush, 0, 1) * (0.32 if fem else 0.1))
        # beard shadow: jaw, chin and upper lip (bluish-grey stubble)
        if beard > 0:
            jaw = np.clip(sstep(-0.45, -0.75, lat) * np.exp(-((du / 1.25) ** 6)) +
                          blob(0.0, -0.52, 0.2, 0.05) * 0.8, 0, 1)
            jaw *= 1 - np.exp(-((du / 0.24) ** 2) - (((lat + 0.64) / 0.07) ** 2))   # not on the lips
            stub = fbm(size, max(8, size // 6), 2, 0.5, seed + 11)
            col = lerp(col, col * np.array([0.72, 0.74, 0.8], np.float32), jaw * beard * (0.55 + 0.45 * stub))
            height = height + jaw * beard * stub * 0.2
        # T-zone is shinier, cheeks more matte
        tz = np.clip(blob(0.0, 0.35, 0.4, 0.2) + blob(0.0, -0.2, 0.12, 0.25), 0, 1)
        rough = rough - tz * 0.12
        # lips: shape, vertical lip lines, a moist sheen
        lip_shape = np.exp(-((du / 0.27) ** 2) - (((lat + 0.67) / 0.05) ** 2))
        upper = np.exp(-((du / 0.24) ** 2) - (((lat + 0.6) / 0.035) ** 2))
        cupid = np.exp(-((du / 0.06) ** 2) - (((lat + 0.575) / 0.015) ** 2)) * 0.6
        lips = np.clip((lip_shape + upper * 0.95 - cupid) * 1.5, 0, 1)
        lip_c = srgb(face["lip"])
        col = lerp(col, lip_c * (0.92 + 0.12 * mottle)[..., None], lips * (0.8 if fem else 0.45))
        lip_lines = 0.5 + 0.5 * np.sin(du * 180.0 + fbm(size, 16, 2, 0.5, seed + 12) * 6)
        height = height + lips * (lip_lines * 0.15 - 0.05)
        rough = rough - lips * (0.25 if fem else 0.12)
        mouth = np.exp(-((du / 0.23) ** 2) - (((lat + 0.635) / 0.007) ** 2))
        col = lerp(col, lip_c * 0.35, np.clip(mouth, 0, 1) * 0.85)
        for side in (-1, 1):
            c = side * 0.42
            rel = (du - c) * side
            peak = 0.07 if fem else 0.10
            k = np.where(rel < peak, 0.55 if fem else 0.25, 2.6 if fem else 1.2)
            arch = (0.235 if fem else 0.215) - k * (rel - peak) ** 2
            tilt = rel * (0.0 if fem else 0.05)
            width = (0.022 if fem else 0.032) * (1 - 0.5 * sstep(0.0, 0.3, rel))
            span = np.exp(-(((du - c) / (0.23 if fem else 0.24)) ** 6))
            brow = np.exp(-(((lat - arch - tilt) / width) ** 2)) * span
            # individual brow hairs: streaks running outward and slightly up
            hairs = fbm(size, 96, 2, 0.5, seed + 5 + side, stretch=1)
            strands = sstep(0.45, 0.7, 0.5 + 0.5 * np.sin((lat - rel * 0.3) * 900 + hairs * 8))
            col = lerp(col, srgb(face["brow"]), np.clip(brow * (0.55 + 0.5 * strands), 0, 1) * 0.95)
            height = height + brow * strands * 0.15
            ec = side * 0.38
            lid = np.exp(-(((lat - 0.075 - 0.5 * np.cos(np.clip((du - ec) / 0.2, -1.6, 1.6)) * 0.06)
                           / (0.018 if fem else 0.013)) ** 2))
            lid *= np.exp(-(((du - ec) / 0.19) ** 6))
            col = lerp(col, srgb(face["liner"]), np.clip(lid, 0, 1) * 0.9)
            if fem:
                wing = np.exp(-(((du - side * 0.6) / 0.07) ** 2) - (((lat - 0.1) / 0.02) ** 2))
                col = lerp(col, srgb(face["liner"]), np.clip(wing, 0, 1) * 0.7)
                shadow = blob(ec, 0.14, 0.2, 0.06)
                col = lerp(col, srgb(face["blush"]) * 0.9, np.clip(shadow, 0, 1) * 0.3)
                if face.get("mark", True):
                    mark = np.exp(-((du / 0.03) ** 2) - (((lat - 0.42) / 0.06) ** 2))
                    col = lerp(col, srgb("#c2182b"), np.clip(mark * 1.3, 0, 1))
            # under-eye: thin skin looks darker/cooler; age adds bags and crow's feet
            low = np.exp(-(((lat + 0.02) / 0.035) ** 2)) * np.exp(-(((du - ec) / 0.16) ** 6))
            col = lerp(col, col * np.array([0.8, 0.76, 0.8], np.float32), np.clip(low, 0, 1) * (0.35 + 0.3 * age))
            if age > 0:
                crow = np.exp(-(((du - side * 0.68) / 0.08) ** 2) - (((lat - 0.05) / 0.08) ** 2))
                wr = 0.5 + 0.5 * np.sin((lat + (du - side * 0.68) * side * 0.6) * 260)
                height = height - crow * wr * 0.35 * age
        # soft hairline: fine strands fading into the skin just below the scalp cap
        if face.get("hairline"):
            tab = face["hairline"]
            hz = np.interp(np.abs(du), [a for a, _ in tab], [z for _, z in tab])
            zz = np.sin(lat)
            strands = sstep(0.35, 0.75, fbm(size, 128, 2, 0.5, seed + 21, stretch=1)
                            * (0.6 + 0.4 * np.sin(du * 700)))
            edge = sstep(hz - 0.07, hz + 0.01, zz)
            hair_c = srgb(face.get("hair", "#161113"))
            col = lerp(col, hair_c, np.clip(edge * (0.12 + 0.8 * strands) * sstep(hz - 0.07, hz - 0.02, zz), 0, 1))
            rough = rough + edge * 0.1
        # nostrils and nose shading
        nose = blob(0.07, -0.385, 0.045, 0.025) + blob(-0.07, -0.385, 0.045, 0.025)
        col = lerp(col, col * np.array([0.45, 0.32, 0.3], np.float32), np.clip(nose, 0, 1) * 0.75)
        if age > 0:
            # forehead lines and nasolabial creases
            fh = 0.5 + 0.5 * np.sin(lat * 140 + fbm(size, 6, 2, 0.5, seed + 13) * 3)
            height = height - blob(0.0, 0.45, 0.6, 0.12) * sstep(0.7, 1.0, fh) * 0.4 * age
            for side in (-1, 1):
                nlf = np.exp(-(((du - side * (0.16 + 0.35 * np.clip(-0.38 - lat, 0, 0.4))) / 0.02) ** 2))
                nlf *= np.exp(-(((lat + 0.52) / 0.14) ** 2))
                height = height - nlf * 0.4 * age
                col = lerp(col, col * 0.88, nlf * 0.4 * age)
    return result(col, rough, 0.0, height)


def nail(tone, size=64):
    """Fingernail: pale pink plate with a lighter free edge (v = 1)."""
    u, v = grid(size)
    base = srgb(tone) * np.array([1.02, 0.9, 0.9], np.float32)
    col = lerp(base, np.array([0.95, 0.9, 0.86], np.float32), sstep(0.8, 0.95, v))
    col = lerp(col * 1.08, col, sstep(0.0, 0.25, v))       # lunula
    ridges = 0.5 + 0.5 * np.sin(u * math.pi * 14)
    return result(col, 0.25, 0.0, ridges * 0.1)


def eye(iris, size=512, glow=None):
    """Eye sphere texture: pupil at v=1 pole (sphere pole faces forward).

    glow: optional hex colour for a luminous (demonic) iris.
    """
    u, v = grid(size)
    r = 1.0 - v  # 0 at the forward pole
    iris_c = srgb(iris)
    col = np.ones((size, size, 3), np.float32) * np.array([0.92, 0.9, 0.87], np.float32)
    n = fbm(size, 16, 3, 0.5, 9)
    # sclera: slightly pink toward the corners, fine veins
    veins = sstep(0.62, 0.7, fbm(size, 24, 4, 0.6, 12, stretch=1)) * sstep(0.3, 0.7, r)
    col = lerp(col, np.array([0.86, 0.62, 0.6], np.float32), sstep(0.35, 0.7, r) * 0.25 + veins * 0.35)
    # iris: radial fibres, a darker outer ring, a lighter collarette around the pupil
    fibres = 0.6 + 0.4 * np.sin(u * 2 * math.pi * 60 + n * 4) * fbm(size, 32, 2, 0.5, 14)
    ir = r / 0.13
    shade = (0.55 + 0.6 * ir) * fibres
    irc = iris_c[None, None, :] * shade[..., None]
    collar = np.exp(-(((r - 0.075) / 0.012) ** 2))
    irc = lerp(irc, np.minimum(iris_c * 1.8 + 0.08, 1.0), collar * 0.35)
    iris_m = 1.0 - sstep(0.12, 0.14, r)
    col = lerp(col, irc, iris_m)
    limbal = np.exp(-(((r - 0.132) / 0.014) ** 2))
    col = lerp(col, np.zeros(3, np.float32), limbal * 0.75)
    pupil = 1.0 - sstep(0.045, 0.055, r)
    col = lerp(col, np.array([0.01, 0.01, 0.012], np.float32), pupil)
    out = result(col, lerp(0.2, 0.05, iris_m), 0.0, iris_m * 0.25 - pupil * 0.1)
    if glow:
        out["emission"] = (srgb(glow)[None, None, :] * (iris_m * (1 - pupil) * shade)[..., None]).astype(np.float32)
    return out


def hair(color, highlight, size=512, seed=21):
    """Hair strands: long streaks along v."""
    c = srgb(color)
    hl = srgb(highlight)
    rng = np.random.default_rng(seed)
    streak = np.zeros((size, size), np.float32)
    for oct_, amp in ((256, 0.5), (128, 0.3), (48, 0.2)):
        line = rng.random(oct_).astype(np.float32)
        xs = np.arange(size) / size * oct_
        x0 = np.floor(xs).astype(int)
        f = _smooth(xs - x0)
        row = line[x0 % oct_] * (1 - f) + line[(x0 + 1) % oct_] * f
        streak += amp * row[None, :]
    wav = fbm(size, 4, 3, 0.5, seed + 1, stretch=4)
    u, v = grid(size)
    col = lerp(c, hl, (streak ** 3) * 0.6 + wav * 0.1)
    rough = 0.42 + streak * 0.12
    return result(col, rough, 0.0, streak)


# --------------------------------------------------------------------------
# metals & gems
# --------------------------------------------------------------------------
def metal(color, size=256, seed=31, rough=0.3, patina=None, patina_amt=0.0):
    c = srgb(color)
    n = fbm(size, 8, 5, 0.55, seed)
    col = c * (0.85 + 0.2 * n)[..., None]
    m = np.full((size, size), 1.0, np.float32)
    r = rough + (n - 0.5) * 0.15
    if patina:
        p = sstep(1.0 - patina_amt, 1.0 - patina_amt + 0.2, fbm(size, 4, 5, 0.6, seed + 3))
        col = lerp(col, srgb(patina), p)
        m = m * (1 - p)
        r = lerp(r, 0.85, p)
    return result(col, r, m, n * 0.3)


def jade(color, size=256, seed=41):
    c = srgb(color)
    n = fbm(size, 4, 6, 0.6, seed)
    veins = np.abs(np.sin((fbm(size, 3, 4, 0.5, seed + 1) * 6.0) * math.pi))
    col = lerp(c * 0.75, np.minimum(c * 1.5, 1.0), n)
    col = lerp(col, np.array([0.95, 0.97, 0.9], np.float32), (1 - sstep(0.0, 0.08, veins)) * 0.5)
    return result(col, 0.12, 0.0, n * 0.1)


# --------------------------------------------------------------------------
# architecture
# --------------------------------------------------------------------------
def lacquer(color, size=512, seed=51, wear=0.25):
    c = srgb(color)
    grain = fbm(size, 4, 5, 0.5, seed, stretch=8)
    n = fbm(size, 8, 5, 0.55, seed + 1)
    col = c * (0.85 + 0.2 * n)[..., None]
    worn = sstep(1 - wear, 1.0, n) * 0.6
    col = lerp(col, srgb("#5b3a24") * (0.8 + 0.4 * grain)[..., None], worn)
    rough = 0.35 + worn * 0.4 + grain * 0.05
    return result(col, rough, 0.0, grain * 0.3 + worn * 0.2)


def wood(color, size=512, seed=61, rings=24):
    c = srgb(color)
    u, v = grid(size)
    warp = fbm(size, 4, 4, 0.5, seed, stretch=6)
    fine = fbm(size, 64, 3, 0.5, seed + 1, stretch=16)
    ring = np.sin((u * rings + warp * 3.0) * 2 * math.pi) * 0.5 + 0.5
    col = c * (0.75 + 0.25 * ring + 0.12 * fine)[..., None]
    return result(col, 0.6 + ring * 0.15, 0.0, ring * 0.4 + fine * 0.3)


def stone(color, size=512, seed=71, speckle=0.3):
    c = srgb(color)
    n = fbm(size, 4, 7, 0.55, seed)
    sp = fbm(size, 128, 2, 0.5, seed + 1)
    col = c * (0.8 + 0.35 * n)[..., None]
    col = lerp(col, col * 0.55, sstep(0.72, 0.8, sp) * speckle)
    col = lerp(col, col * 1.25, sstep(0.75, 0.85, 1 - sp) * speckle)
    return result(col, 0.8 + n * 0.1, 0.0, n * 0.6 + sp * 0.3)


def paving(color, size=1024, seed=81, tiles=4, gap=0.012, moss=0.25):
    """Large flagstones in a staggered bond with mortar gaps and moss."""
    c = srgb(color)
    u, v = grid(size)
    rng = np.random.default_rng(seed)
    row = np.floor(v * tiles)
    uu = u * tiles + (row % 2) * 0.5
    col_i = np.floor(uu)
    fu = uu - col_i
    fv = v * tiles - row
    tone = rng.random((tiles, tiles + 1)).astype(np.float32)
    t = tone[row.astype(int) % tiles, col_i.astype(int) % (tiles + 1)]
    edge = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv))
    g = gap * tiles
    mortar = 1.0 - sstep(g * 0.5, g * 1.5, edge)
    n = fbm(size, 8, 6, 0.55, seed + 1)
    col = c * (0.78 + 0.25 * t + 0.2 * (n - 0.5))[..., None]
    mn = fbm(size, 8, 5, 0.6, seed + 2)
    mo = np.clip(mortar * 0.6 + sstep(1 - moss, 1.0, mn) * 0.8, 0, 1) * (moss > 0)
    col = lerp(col, srgb("#3c4a28") * (0.7 + 0.5 * n)[..., None], mo * 0.7)
    col = lerp(col, col * 0.62, mortar * 0.6)
    height = (1 - mortar) * 0.6 + n * 0.3
    bevel = sstep(0, g * 3.0, edge)
    height = height * (0.6 + 0.4 * bevel)
    return result(col, 0.96 - (1 - mortar) * 0.04, 0.0, height)


def bricks(color, size=512, seed=91, rows=8, cols=4):
    c = srgb(color)
    u, v = grid(size)
    rng = np.random.default_rng(seed)
    row = np.floor(v * rows)
    uu = u * cols + (row % 2) * 0.5
    ci = np.floor(uu)
    fu = uu - ci
    fv = v * rows - row
    tone = rng.random((rows, cols + 1)).astype(np.float32)
    t = tone[row.astype(int) % rows, ci.astype(int) % (cols + 1)]
    edge = np.minimum(np.minimum(fu / cols * rows * 0.5, (1 - fu) / cols * rows * 0.5),
                      np.minimum(fv, 1 - fv))
    mortar = 1.0 - sstep(0.04, 0.09, edge)
    n = fbm(size, 8, 5, 0.55, seed + 1)
    col = c * (0.8 + 0.25 * t + 0.15 * (n - 0.5))[..., None]
    col = lerp(col, np.array([0.7, 0.68, 0.62], np.float32), mortar * 0.8)
    return result(col, 0.85, 0.0, (1 - mortar) * 0.7 + n * 0.2)


def plaster(color, size=512, seed=101, grime="#8a7d6a"):
    c = srgb(color)
    u, v = grid(size)
    n = fbm(size, 4, 6, 0.55, seed)
    d = fbm(size, 2, 5, 0.5, seed + 1, stretch=3)
    dirt = sstep(0.4, 1.0, (1 - v) * 0.7 + d * 0.5) * 0.5
    col = c * (0.93 + 0.08 * n)[..., None]
    col = lerp(col, srgb(grime), dirt)
    return result(col, 0.9, 0.0, n * 0.4)


def roof_tiles(color, size=512, seed=111, channels=8, rows=10):
    """Barrel-tile roof. u across the slope (channels), v up the slope."""
    c = srgb(color)
    u, v = grid(size)
    fu = (u * channels) % 1.0
    barrel = np.sqrt(np.clip(1 - ((fu - 0.5) / 0.5) ** 2, 0, 1))
    fv = (v * rows) % 1.0
    lap = sstep(0.0, 0.85, fv) * (1 - sstep(0.95, 1.0, fv))
    height = barrel * 0.7 + lap * 0.3
    n = fbm(size, 8, 5, 0.5, seed)
    rng = np.random.default_rng(seed)
    tone = rng.random((rows, channels)).astype(np.float32)
    t = tone[np.floor(v * rows).astype(int) % rows, np.floor(u * channels).astype(int) % channels]
    col = c * (0.7 + 0.3 * barrel + 0.15 * t + 0.1 * n)[..., None]
    col = lerp(col, col * 0.4, (1 - barrel) ** 4 * 0.8)
    rough = 0.35 + (1 - barrel) * 0.4 + n * 0.1
    return result(col, rough, 0.0, height)


def lattice(frame, paper, size=512, cells=6):
    """Window/door lattice: wood grid over rice paper (u, v in panel space)."""
    fr = srgb(frame)
    pa = srgb(paper)
    u, v = grid(size)
    fu = (u * cells) % 1.0
    fv = (v * cells * 1.5) % 1.0
    bar = 0.1
    grid_m = ((fu < bar) | (fu > 1 - bar) | (fv < bar) | (fv > 1 - bar)).astype(np.float32)
    # diagonal accent bars
    d1 = np.abs(((u * cells + v * cells * 1.5) % 1.0) - 0.5) < 0.05
    grid_m = np.maximum(grid_m, d1.astype(np.float32) * 0.0)
    border = ((u < 0.04) | (u > 0.96) | (v < 0.03) | (v > 0.97)).astype(np.float32)
    m = np.maximum(grid_m, border)
    n = fbm(size, 8, 4, 0.5, 7)
    col = lerp(pa * (0.95 + 0.05 * n)[..., None], fr * (0.85 + 0.2 * n)[..., None], m)
    return result(col, lerp(0.8, 0.4, m), 0.0, m)


def grass(size=512, seed=121):
    u, v = grid(size)
    n = fbm(size, 8, 6, 0.55, seed)
    blades = fbm(size, 128, 2, 0.5, seed + 1)
    patches = fbm(size, 3, 4, 0.5, seed + 2)
    col = lerp(srgb("#4a6b2c"), srgb("#8fa04e"), n * 0.7 + blades * 0.3)
    col = lerp(col, srgb("#6b5a3a"), sstep(0.7, 0.9, patches) * 0.35)
    col = lerp(col, srgb("#b9b060"), sstep(0.25, 0.05, patches) * 0.3)
    return result(col, 0.9, 0.0, blades * 0.6 + n * 0.3)


def bark(color, size=512, seed=131):
    c = srgb(color)
    ridges = fbm(size, 6, 5, 0.5, seed, stretch=6)
    n = fbm(size, 16, 4, 0.5, seed + 1)
    r = np.abs(np.sin(ridges * 12.0))
    col = c * (0.55 + 0.5 * r + 0.1 * n)[..., None]
    return result(col, 0.9, 0.0, r * 0.8 + n * 0.2)


def foliage(color, size=512, seed=141):
    c = srgb(color)
    n = fbm(size, 16, 5, 0.6, seed)
    clumps = fbm(size, 6, 3, 0.5, seed + 1)
    needles = fbm(size, 128, 2, 0.5, seed + 2, stretch=1)
    col = c * (0.45 + 0.7 * n * (0.6 + 0.4 * clumps) + 0.2 * (needles - 0.5))[..., None]
    col = lerp(col, col * np.array([1.15, 1.1, 0.7], np.float32), sstep(0.6, 0.9, clumps) * 0.4)
    return result(col, 0.8, 0.0, n * 0.6 + needles * 0.6)


def blossom(size=512, seed=151):
    n = fbm(size, 24, 5, 0.6, seed)
    c = lerp(srgb("#f3c1cf"), srgb("#fff0f4"), n)
    c = lerp(c, srgb("#c7507a"), sstep(0.8, 0.95, fbm(size, 64, 2, 0.5, seed + 1)) * 0.6)
    return result(c, 0.7, 0.0, n)


def paper_lantern(color, size=256, ribs=12):
    c = srgb(color)
    u, v = grid(size)
    rib = np.exp(-(((u * ribs) % 1.0 - 0.5) / 0.05) ** 2 * 1.0)
    rib = np.clip(1 - np.abs(((u * ribs) % 1.0) - 0.5) * 20, 0, 1)
    hoop = np.clip(1 - np.abs(((v * 6) % 1.0) - 0.5) * 30, 0, 1)
    col = c * (1 - 0.35 * np.maximum(rib, hoop))[..., None]
    return result(col, 0.7, 0.0, np.maximum(rib, hoop))


def water(size=256, seed=161):
    n = fbm(size, 8, 5, 0.6, seed)
    col = lerp(srgb("#1d4d57"), srgb("#3f7f80"), n)
    return result(col, 0.05, 0.0, n)


def cliff(color, size=1024, seed=171):
    """Layered karst cliff (for floating mountains): strata along v."""
    c = srgb(color)
    u, v = grid(size)
    n = fbm(size, 4, 7, 0.55, seed)
    warp = fbm(size, 2, 4, 0.5, seed + 1)
    strata = np.sin((v * 18 + warp * 4) * math.pi) * 0.5 + 0.5
    cracks = sstep(0.9, 0.98, fbm(size, 16, 3, 0.5, seed + 2, stretch=4))
    col = c * (0.65 + 0.25 * strata + 0.25 * n)[..., None]
    col = lerp(col, col * 0.4, cracks)
    return result(col, 0.88, 0.0, strata * 0.4 + n * 0.5 - cracks * 0.4)


# --------------------------------------------------------------------------
# garments laid out in loft space (u around the body, v from hem 0 to neck 1)
# --------------------------------------------------------------------------
def periodic_ridge(size, seed, cells=6, octaves=5):
    """1-D tileable fbm profile (for mountain silhouettes)."""
    rng = np.random.default_rng(seed)
    x = np.arange(size) / size
    out = np.zeros(size, np.float32)
    amp, tot = 1.0, 0.0
    c = cells
    for _ in range(octaves):
        g = rng.random(c).astype(np.float32)
        xs = x * c
        i0 = np.floor(xs).astype(int)
        f = _smooth(xs - i0)
        out += amp * (g[i0 % c] * (1 - f) + g[(i0 + 1) % c] * f)
        tot += amp
        amp *= 0.5
        c *= 2
    return out / tot


def robe(top, hem, motif, accent, style="mountains", size=1024, seed=201):
    """Gradient silk robe with an ink-wash hem design.

    style 'mountains': layered ink-wash peaks and mist (male disciple robe)
    style 'blossom'  : plum-blossom branches rising from the hem (female robe)
    style 'plain'    : tonal damask only
    style 'clouds'   : large auspicious clouds embroidered above the hem
    style 'flames'   : demonic flame tongues licking up from the hem
    style 'bamboo'   : ink bamboo stalks and leaves
    style 'hemp'     : coarse undyed hemp with patches and darning (commoners)
    """
    top_c, hem_c, mot_c, acc_c = srgb(top), srgb(hem), srgb(motif), srgb(accent)
    u, v = grid(size)
    w = weave(size, 3.0)
    n = fbm(size, 4, 5, 0.55, seed)
    grad = sstep(0.05, 0.75, v + (n - 0.5) * 0.08)
    col = lerp(hem_c, top_c, grad)
    damask = xiangyun_mask(size, 16, seed + 3, 0.035, 0.003)
    col = lerp(col, col * 0.93, damask * 0.8)
    rough = 0.6 - damask * 0.2
    height = damask * 0.4 + n * 0.1
    if style == "hemp":
        coarse = weave(size, 5.0)
        slub = fbm(size, 64, 3, 0.6, seed + 40, stretch=4)
        col = lerp(hem_c, top_c, grad) * (0.85 + 0.12 * coarse + 0.1 * slub)[..., None]
        rng = np.random.default_rng(seed + 41)
        for _ in range(7):
            cx, cy = rng.random(), rng.uniform(0.05, 0.7)
            w_, h_ = rng.uniform(0.03, 0.07), rng.uniform(0.03, 0.06)
            patch = (np.abs(u - cx) < w_) & (np.abs(v - cy) < h_)
            col = np.where(patch[..., None], col * np.array([0.85, 0.8, 0.72], np.float32), col)
            edge = patch & ((np.abs(np.abs(u - cx) - w_) < 0.004) | (np.abs(np.abs(v - cy) - h_) < 0.004))
            col = np.where(edge[..., None], mot_c, col)
            height = height + patch * 0.2
        dirt = sstep(0.25, 0.0, v) * fbm(size, 8, 4, 0.5, seed + 42)
        col = lerp(col, col * np.array([0.6, 0.52, 0.42], np.float32), dirt * 0.8)
        return result(col, 0.85 - slub * 0.1, 0.0, coarse * 0.5 + slub * 0.3 + height * 0.2)
    if style == "plain":
        return result(col, rough, 0.0, height)
    if style == "clouds":
        big = xiangyun_mask(size, 7, seed + 50, 0.09, 0.006) * sstep(0.55, 0.3, v)
        col = lerp(col, mot_c, np.clip(big, 0, 1) * 0.9)
        rim = xiangyun_mask(size, 7, seed + 50, 0.09, 0.012) * sstep(0.55, 0.3, v)
        col = lerp(col, acc_c, np.clip(rim - big, 0, 1) * 0.8)
        return result(col, rough - big * 0.2, big * 0.3, height + big * 0.4)
    if style == "flames":
        fl = np.zeros((size, size), np.float32)
        rng = np.random.default_rng(seed + 60)
        for k in range(22):
            cx = k / 22 + rng.uniform(-0.01, 0.01)
            h_ = rng.uniform(0.18, 0.42)
            wob = 0.012 * np.sin(v * 40 + k) + 0.02 * (fbm(size, 8, 3, 0.5, seed + 61 + k % 3) - 0.5)
            width = 0.022 * (1 - np.clip(v / h_, 0, 1)) ** 0.8
            d = np.abs(((u - cx - wob + 0.5) % 1.0) - 0.5)
            fl = np.maximum(fl, (d < width).astype(np.float32) * (v < h_))
        core = fl * sstep(0.25, 0.0, v)
        col = lerp(col, mot_c, fl * 0.95)
        col = lerp(col, acc_c, core * 0.8)
        return result(col, rough - fl * 0.15, 0.0, height + fl * 0.3)
    if style == "bamboo":
        stalk = np.zeros((size, size), np.float32)
        rng = np.random.default_rng(seed + 70)
        for k in range(9):
            cx = k / 9 + rng.uniform(0, 0.08)
            hgt = rng.uniform(0.3, 0.55)
            lean = rng.uniform(-0.05, 0.05)
            d = np.abs(((u - cx - lean * v + 0.5) % 1.0) - 0.5)
            node = np.abs(((v * 12 + k * 0.3) % 1.0) - 0.5) > 0.46
            stalk = np.maximum(stalk, ((d < 0.006) & (v < hgt) & ~node).astype(np.float32))
            for j in range(4):
                ly = rng.uniform(0.1, hgt)
                pts = [((cx + lean * ly + t * 0.04 * rng.choice([-1, 1])) % 1.0, ly + t * 0.012)
                       for t in np.linspace(0, 1, 10)]
                stamp_curve(stalk, pts, 0.004, size)
        col = lerp(col, mot_c, np.clip(stalk, 0, 1) * 0.85)
        return result(col, rough, 0.0, height + stalk * 0.3)
    if style == "mountains":
        layers = [(0.30, 0.10, 0.45, 5), (0.22, 0.09, 0.7, 7), (0.13, 0.07, 1.0, 9)]
        for i, (base, amp, dark, cells) in enumerate(layers):
            ridge = base + amp * periodic_ridge(size, seed + 10 + i, cells)
            m = sstep(0.004, -0.004, v - ridge[None, :])
            # ink-wash: darker near the ridge, fading downward into mist
            fade = sstep(ridge[None, :] - 0.12, ridge[None, :], v)
            ink = m * (0.35 + 0.65 * fade) * dark
            col = lerp(col, mot_c, np.clip(ink, 0, 1) * 0.85)
            height = height + m * 0.15
        mist = sstep(0.0, 0.1, v) * (1 - sstep(0.1, 0.2, v)) * fbm(size, 6, 4, 0.5, seed + 20)
        col = lerp(col, hem_c * 1.1, np.clip(mist, 0, 1) * 0.5)
        # a few flying cranes as small accent checks
        for k in range(3):
            cu, cv = (0.15 + k * 0.33) % 1.0, 0.36 + 0.03 * k
            wing = np.exp(-(((u - cu) / 0.012) ** 2 + ((v - cv - 0.3 * np.abs(u - cu)) / 0.0025) ** 2))
            col = lerp(col, mot_c * 0.6, np.clip(wing * 2, 0, 1))
    else:
        branch = np.zeros((size, size), np.float32)
        flowers = np.zeros((size, size), np.float32)
        rng = np.random.default_rng(seed + 30)
        for b in range(5):
            x = b / 5 + rng.uniform(0, 0.1)
            y = 0.0
            ang = rng.uniform(1.2, 1.9)
            pts = []
            for s in range(120):
                ang += rng.uniform(-0.12, 0.12)
                x += math.cos(ang) * 0.003
                y += math.sin(ang) * 0.003
                pts.append((x % 1.0, y))
                if s % 18 == 17:
                    # side twig
                    a2 = ang + rng.choice([-0.9, 0.9])
                    tx, ty = x, y
                    twig = []
                    for _ in range(25):
                        tx += math.cos(a2) * 0.003
                        ty += math.sin(a2) * 0.003
                        twig.append((tx % 1.0, ty))
                    stamp_curve(branch, twig, 0.0025, size)
                    fx, fy = twig[-1]
                    for _ in range(3):
                        ox, oy = rng.normal(0, 0.012, 2)
                        stamp_curve(flowers, [((fx + ox) % 1.0, fy + oy)], 0.009, size)
            stamp_curve(branch, pts, 0.0045, size)
            for _ in range(8):
                px, py = pts[rng.integers(20, len(pts))]
                ox, oy = rng.normal(0, 0.015, 2)
                stamp_curve(flowers, [((px + ox) % 1.0, py + oy)], 0.010, size)
        petals = flowers * (0.7 + 0.3 * fbm(size, 64, 2, 0.5, seed + 31))
        centre = sstep(0.75, 0.95, flowers)
        col = lerp(col, mot_c, np.clip(branch, 0, 1) * 0.9)
        col = lerp(col, acc_c, np.clip(petals, 0, 1))
        col = lerp(col, srgb("#f6d67a"), centre * 0.8)
        height = height + branch * 0.3 + flowers * 0.4
        rough = rough - flowers * 0.15
    return result(col, rough, 0.0, height)


def eyelid(skin_c, liner_c, size=64):
    """Eyelid shell: v=0 at the lid rim (lash line), 1 far from the opening."""
    u, v = grid(size)
    col = lerp(srgb(liner_c), srgb(skin_c) * 0.92, sstep(0.05, 0.16, v))
    return result(col, 0.55, 0.0, None)


# --------------------------------------------------------------------------
# architecture decoration
# --------------------------------------------------------------------------
def beam_paint(size=512, seed=301):
    """Suzhou/xuanzi-style painted beam: bands along u, constant along v."""
    u, v = grid(size)
    blue, green, gold, red = srgb("#1f4f7a"), srgb("#2f7a63"), srgb("#d8b04a"), srgb("#8e2a20")
    period = 0.5
    fu = (u % period) / period
    col = np.where((fu < 0.35)[..., None], blue, green)
    col = np.where(((fu > 0.7) & (fu < 0.85))[..., None], red, col)
    edges = (np.abs(fu - 0.35) < 0.012) | (np.abs(fu - 0.7) < 0.012) | (np.abs(fu - 0.85) < 0.012) | (fu < 0.012)
    col = np.where(edges[..., None], gold, col)
    # xuanzi rosettes (circles) inside the blue band
    cx = 0.175
    ring_d = np.abs(np.abs(fu - cx) - 0.08)
    ros = (ring_d < 0.012) | (np.abs(fu - cx) < 0.02)
    col = np.where(ros[..., None], lerp(gold, srgb("#f2e6c2"), 0.3) * np.ones_like(col), col)
    n = fbm(size, 8, 4, 0.5, seed)
    col = col * (0.85 + 0.2 * n)[..., None]
    metal = np.where(edges | ros, 0.7, 0.0).astype(np.float32)
    rough = np.where(edges | ros, 0.35, 0.6).astype(np.float32)
    return result(col, rough, metal, (edges | ros).astype(np.float32) * 0.5 + n * 0.2)


def plaque(size=512, seed=311, chars=3, field="#1b2a4a", ink="#e2bd57"):
    """Horizontal name board with pseudo-calligraphy (u across, v up)."""
    rng = np.random.default_rng(seed)
    u, v = grid(size)
    col = np.ones((size, size, 3), np.float32) * srgb(field)
    border = (u < 0.05) | (u > 0.95) | (v < 0.1) | (v > 0.9)
    inner = (np.abs(u - 0.5) > 0.43) | (np.abs(v - 0.5) > 0.36)
    mask = np.zeros((size, size), np.float32)
    for c in range(chars):
        cx = 0.5 + (c - (chars - 1) / 2) * 0.28
        for _ in range(rng.integers(5, 9)):
            kind = rng.integers(0, 4)
            x0 = cx + rng.uniform(-0.09, 0.07)
            y0 = 0.5 + rng.uniform(-0.25, 0.25)
            ln = rng.uniform(0.05, 0.14)
            if kind == 0:
                pts = [(x0 + t * ln, y0) for t in np.linspace(0, 1, 30)]
            elif kind == 1:
                pts = [(x0, y0 + 0.12 - t * ln * 2.2) for t in np.linspace(0, 1, 30)]
            elif kind == 2:
                pts = [(x0 + t * ln, y0 - t * ln * 1.6) for t in np.linspace(0, 1, 30)]
            else:
                pts = [(x0 + t * ln * 0.8, y0 + t * ln * 1.2) for t in np.linspace(0, 1, 30)]
            stamp_curve(mask, [(p[0] % 1.0, min(max(p[1], 0.15), 0.85)) for p in pts], 0.013, size)
    g = srgb(ink)
    col = lerp(col, g, mask)
    col = np.where((border & ~inner)[..., None] | border[..., None], g * 0.9, col)
    col = np.where((inner & ~border)[..., None], srgb(field) * 0.8 + g * 0.2, col)
    metal = np.clip(mask + border, 0, 1) * 0.8
    return result(col, 0.4, metal, mask * 0.6 + border * 0.5)


def rune_circle(size=1024, seed=321, glow="#7ff0ff", stone_c="#8f8b85"):
    """Formation array disc: concentric rune rings (u, v = planar disc coordinates)."""
    base = stone(stone_c, size, seed)
    u, v = grid(size)
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    rings = np.zeros_like(r)
    for rr in (0.46, 0.40, 0.30, 0.22, 0.12):
        rings = np.maximum(rings, 1 - sstep(0.0, 0.004, np.abs(r - rr)))
    runes = ((np.sin(a * 36) > 0.6) & (r > 0.41) & (r < 0.455)).astype(np.float32)
    runes += ((np.sin(a * 24 + 1) > 0.3) & (np.cos(a * 72) > 0) & (r > 0.31) & (r < 0.39)).astype(np.float32)
    trig = np.zeros_like(r)
    for k in range(8):
        ang = k * math.pi / 4
        d = np.abs(x * math.sin(ang) - y * math.cos(ang))
        trig = np.maximum(trig, (1 - sstep(0.0, 0.003, d)) * ((r > 0.12) & (r < 0.3)))
    m = np.clip(rings + runes + trig, 0, 1)
    col = lerp(base["albedo"], srgb(glow), m * 0.9)
    base["albedo"] = col
    base["height"] = base["height"] - m * 0.5
    base["emit_mask"] = m
    return base

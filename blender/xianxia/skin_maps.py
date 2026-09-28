"""Surface-space maps for the head skin texture.

The face texture is painted per texel from where that texel lies on the real head
mesh, so it works with any UV layout (the old warped UV sphere, or the new face
island + cylindrical sides) and never shows a seam:

* rasterize() - every triangle of the faces using the skin material is scan-converted
  in UV space, writing interpolated world position and normal (a "position map").
  Gutter texels are then filled by dilation so bilinear filtering and mip-maps at
  island borders sample sensible values.
* FaceFrame   - converts positions to face coordinates (lon, lat) around the head
  centre, the same convention as the hairline table and the hair groom, plus
  landmark-relative helpers (gaussian blobs, tangent frames for skin tension lines).
* 3-D noise   - value noise, fBm and Worley (cellular) noise evaluated at the world
  positions: pores, skin lines and mottling are uniform in millimetres whatever the
  local UV stretch, and continuous across UV seams.
"""
import math

import numpy as np


# --------------------------------------------------------------------------
# rasteriser
# --------------------------------------------------------------------------
def mesh_triangles(objs, mats):
    """World-space triangles (T,3,3), normals (T,3,3) and UVs (T,3,2) of faces using any of mats."""
    P, N, UV = [], [], []
    for o in objs:
        me = o.data
        if not me.uv_layers:
            continue
        slots = {i for i, m in enumerate(me.materials) if m is not None and m in mats}
        if not slots:
            continue
        me.calc_loop_triangles()
        mw = o.matrix_world
        rot = mw.to_3x3()
        co = np.array([tuple(mw @ v.co) for v in me.vertices], np.float32)
        vn = np.array([tuple((rot @ v.normal).normalized()) for v in me.vertices], np.float32)
        uv = np.zeros(len(me.loops) * 2, np.float32)
        me.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        for t in me.loop_triangles:
            if t.material_index not in slots:
                continue
            P.append(co[list(t.vertices)])
            N.append(vn[list(t.vertices)])
            UV.append(uv[list(t.loops)])
    if not P:
        return None
    return np.array(P), np.array(N), np.array(UV)


def rasterize(tris, size):
    """Scan-convert triangles in UV space. Returns (pos, nrm, cover) at size x size.

    UVs outside [0, 1] wrap (the texture repeats), matching the sampler.
    """
    P, N, UV = tris
    pos = np.zeros((size, size, 3), np.float32)
    nrm = np.zeros((size, size, 3), np.float32)
    cover = np.zeros((size, size), bool)
    px = UV * size - 0.5
    for k in range(len(P)):
        a, b, c = px[k]
        x0, x1 = int(math.floor(min(a[0], b[0], c[0]))), int(math.ceil(max(a[0], b[0], c[0])))
        y0, y1 = int(math.floor(min(a[1], b[1], c[1]))), int(math.ceil(max(a[1], b[1], c[1])))
        if x1 - x0 > size or y1 - y0 > size:
            continue
        xs = np.arange(x0, x1 + 1, dtype=np.float32)
        ys = np.arange(y0, y1 + 1, dtype=np.float32)
        gx, gy = np.meshgrid(xs, ys)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / d
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / d
        w2 = 1 - w0 - w1
        eps = -1e-4
        inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        if not inside.any():
            continue
        iy = gy[inside].astype(int) % size
        ix = gx[inside].astype(int) % size
        W = np.stack([w0[inside], w1[inside], w2[inside]], -1)
        pos[iy, ix] = W @ P[k]
        nrm[iy, ix] = W @ N[k]
        cover[iy, ix] = True
    nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-6)
    return pos, nrm, cover


def dilate(arrs, cover):
    """Fill uncovered (gutter) texels from the nearest islands: push-pull pyramid.

    Push: coverage-weighted 2x2 averages down to 1 px.  Pull: every empty texel takes the
    upsampled coarser value, so gutters get the colour of the adjacent island edge and
    mip-mapping / bilinear filtering never blend in black or unrelated texels.
    """
    w = cover.astype(np.float32)
    out = []
    for a in arrs:
        a3 = a if a.ndim == 3 else a[..., None]
        levels = [(a3 * w[..., None], w)]
        while levels[-1][1].shape[0] > 1:
            v, ww = levels[-1]
            h = ww.shape[0] // 2
            v = v[:2 * h, :2 * h].reshape(h, 2, h, 2, -1).sum((1, 3))
            ww = ww[:2 * h, :2 * h].reshape(h, 2, h, 2).sum((1, 3))
            levels.append((v, ww))
        v, ww = levels[-1]
        fill = v / np.maximum(ww, 1e-6)[..., None]
        for v, ww in reversed(levels[:-1]):
            up = np.repeat(np.repeat(fill, 2, 0), 2, 1)[:ww.shape[0], :ww.shape[1]]
            fill = np.where((ww > 0)[..., None], v / np.maximum(ww, 1e-6)[..., None], up)
        res = np.where(cover[..., None], a3, fill).astype(np.float32)
        out.append(res if a.ndim == 3 else res[..., 0])
    return out


# --------------------------------------------------------------------------
# face coordinates
# --------------------------------------------------------------------------
class FaceFrame:
    """Face coordinates of texel positions: lon (0 = front, + = character's left), lat."""

    def __init__(self, pos, centre, radii):
        self.c = np.asarray(centre, np.float32)
        self.radii = np.asarray(radii, np.float32)
        e = (pos - self.c) / self.radii
        e /= np.maximum(np.linalg.norm(e, axis=-1, keepdims=True), 1e-6)
        self.lon = np.arctan2(e[..., 0], -e[..., 1])
        self.lat = np.arcsin(np.clip(e[..., 2], -1, 1))
        # tangent frame on the unit sphere (east = +lon, north = +lat), in world space
        east = np.stack([np.cos(self.lon), np.sin(self.lon), np.zeros_like(self.lon)], -1)
        north = np.stack([-np.sin(self.lon) * np.sin(self.lat), np.cos(self.lon) * np.sin(self.lat),
                          np.cos(self.lat)], -1)
        self.east, self.north = east, north

    def blob(self, lon, lat, slon, slat, power=2.0):
        """Soft elliptical mask centred at (lon, lat)."""
        return np.exp(-(np.abs((self.lon - lon) / slon) ** power + np.abs((self.lat - lat) / slat) ** power))

    def pair(self, lon, lat, slon, slat, power=2.0):
        """Symmetric left + right blobs."""
        return np.clip(self.blob(lon, lat, slon, slat, power) + self.blob(-lon, lat, slon, slat, power), 0, 1)


# --------------------------------------------------------------------------
# 3-D noise (positions in metres)
# --------------------------------------------------------------------------
_TABLES = {}
PERIOD = 64                       # lattice period of the noise tables (cells; small = cache friendly)


def _table(channels=1):
    """Random lattice values, periodic every PERIOD cells (one table per channel count)."""
    if channels not in _TABLES:
        rng = np.random.default_rng(7919 + channels)
        _TABLES[channels] = rng.random((PERIOD, PERIOD, PERIOD, channels), dtype=np.float32)
    return _TABLES[channels]


def _seeded(p, cell, seed):
    """Lattice coordinates, shifted per seed so each seed reads a different part of the table."""
    return p / cell + np.array([seed * 37.13, seed * 17.31, seed * 11.77], np.float32)


def _axes(i):
    """Per-axis wrapped lattice indices (and their +1 neighbours) pre-scaled for a flat lookup."""
    m = PERIOD - 1
    ix, iy, iz = (i[..., k].astype(np.int32) for k in range(3))
    return ((ix & m) * PERIOD * PERIOD, ((ix + 1) & m) * PERIOD * PERIOD), \
        ((iy & m) * PERIOD, ((iy + 1) & m) * PERIOD), (iz & m, (iz + 1) & m)


def value3(p, cell, seed=0):
    """Smooth value noise in [0, 1] with lattice spacing `cell` metres."""
    q = _seeded(p, cell, seed)
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)
    ax, ay, az = _axes(i)
    tab = _table(1).ravel()
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    lerp = lambda a, b, t: a + (b - a) * t
    yz = []
    for y in (0, 1):
        for z in (0, 1):
            yz.append(lerp(tab[ax[0] + ay[y] + az[z]], tab[ax[1] + ay[y] + az[z]], fx))
    return lerp(lerp(yz[0], yz[2], fy), lerp(yz[1], yz[3], fy), fz).astype(np.float32)


def fbm3(p, cell, octaves=4, gain=0.5, seed=0):
    out = np.zeros(p.shape[:-1], np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * value3(p, cell / 2 ** o, seed + 17 * o)
        tot += amp
        amp *= gain
    return out / tot


def worley3(p, cell, seed=0, jitter=0.7):
    """Distance to the nearest feature point (in cell units) and that point's random id.

    Searches the 2x2x2 cells around the nearest lattice corner (enough for jitter <= 0.7).
    """
    q = _seeded(p, cell, seed).astype(np.float32)
    base = np.floor(q - 0.5)
    fq = (q - base).astype(np.float32)
    ax, ay, az = _axes(base)
    tab = _table(4).reshape(-1, 4)
    best = np.full(p.shape[:-1], 9.0, np.float32)
    ident = np.zeros(p.shape[:-1], np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                r = tab[ax[dx] + ay[dy] + az[dz]]
                d = ((fq[..., 0] - dx - 0.5 - (r[..., 0] - 0.5) * jitter) ** 2
                     + (fq[..., 1] - dy - 0.5 - (r[..., 1] - 0.5) * jitter) ** 2
                     + (fq[..., 2] - dz - 0.5 - (r[..., 2] - 0.5) * jitter) ** 2)
                closer = d < best
                best = np.where(closer, d, best)
                ident = np.where(closer, r[..., 3], ident)
    return np.sqrt(best), ident


def stretch(p, direction, k):
    """Squash positions along a per-texel unit direction by 1/k (features elongate by k)."""
    along = np.sum(p * direction, -1, keepdims=True)
    return p - direction * along * (1 - 1 / k)


def blur(a, passes=2):
    """Cheap separable box blur (wrapping)."""
    for _ in range(passes):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)) / 3
        a = (a + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 3
    return a

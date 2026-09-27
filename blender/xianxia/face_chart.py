"""The head chart: a family of rays that sweeps the whole head and neck.

A mesh vertex is identified by its chart coordinate (lon, b):

* ``lon`` - angle around the vertical axis, 0 = straight ahead, + = the
  character's left, +-pi at the back;
* ``b``   - a latitude-like row coordinate.  For b >= B_HEAD the ray starts at
  ORIGIN (on the head's vertical axis, 30 mm below the head centre, level with
  the nose) and points at latitude b (radians).  From there the head is
  star-shaped even around the lower face: seen from the true centre the chin
  pad hides the mentolabial sulcus.  Below B_HEAD the ray is horizontal,
  starts on the (slightly forward-leaning) neck axis and sits at height z:
  below B_NECK z = neck_z(b); in the band between, z is interpolated from the
  height where the last head ray hit the surface (per lon) down to the neck
  top, so rows flow from under the jaw into the neck without folding.

``cast(F, lon, b, band_top)`` finds where each ray first leaves the implicit
surface (vectorised march + bisection).  The same chart drives
the UVs (``face_uv``).
"""
import math

import numpy as np

ORIGIN = np.array([0.0, 0.0, -30.0])     # head rays start here: 30 mm below the head centre
B_HEAD = math.radians(-62.0)      # head rays down to this latitude
B_NECK = math.radians(-84.0)      # plain horizontal neck rays below this
NECK_TOP_Z = -150.0               # z (mm) of the first plain neck row
NECK_DZ_PER_RAD = 150.0           # mm of neck per radian of b below B_NECK


def neck_z(b):
    return NECK_TOP_Z + (np.asarray(b) - B_NECK) * NECK_DZ_PER_RAD


def b_of_neck_z(z):
    return B_NECK + (np.asarray(z) - NECK_TOP_Z) / NECK_DZ_PER_RAD


def neck_axis_y(z):
    return 7.0 + 0.012 * (np.asarray(z) + 128.0)


def rays(lon, b, band_top=None, centre_only=False):
    """Origins and unit directions (N, 3) for chart coordinates.

    centre_only: every ray starts at the head centre (radial lookups).
    band_top(lon) -> z where the lowest head ray hit the surface; required for
    rows between B_NECK and B_HEAD."""
    lon = np.asarray(lon, np.float64)
    b = np.asarray(b, np.float64)
    cb, sb = np.cos(b), np.sin(b)
    d_head = np.stack([np.sin(lon) * cb, -np.cos(lon) * cb, sb], axis=-1)
    head = (b >= B_HEAD) | centre_only
    z = neck_z(np.minimum(b, B_NECK))
    band = (~head) & (b > B_NECK)
    if np.any(band):
        if band_top is None:
            raise ValueError("band rows need band_top")
        f = (B_HEAD - b[band]) / (B_HEAD - B_NECK)
        zt = band_top(lon[band])
        z[band] = zt + (NECK_TOP_Z - zt) * f
    o_neck = np.stack([np.zeros_like(z), neck_axis_y(z), z], axis=-1)
    d_neck = np.stack([np.sin(lon), -np.cos(lon), np.zeros_like(lon)], axis=-1)
    o = np.where(head[..., None], 0.0 if centre_only else ORIGIN, o_neck)
    d = np.where(head[..., None], d_head, d_neck)
    return o, d


def cast(F, lon, b, band_top=None, t_max=175.0, step=0.7, iters=22, centre_only=False):
    """First exit of each chart ray from the head (F < 0 inside). Returns (points (N,3), distances).

    Marching outward from the ray origin (inside the head) and taking the first
    exit, rather than the outermost crossing, keeps concavities that a bump
    further along the same ray would hide - the mentolabial sulcus behind the
    chin pad is the classic case."""
    o, d = rays(lon, b, band_top, centre_only)
    n = len(o)
    t_lo = np.zeros(n)
    t_hi = np.full(n, t_max)
    found = np.zeros(n, bool)
    t = step
    while t < t_max and not found.all():
        idx = np.nonzero(~found)[0]
        pts = o[idx] + d[idx] * t
        f = F(pts[:, 0], pts[:, 1], pts[:, 2])
        out = idx[f > 0]
        t_hi[out] = t
        t_lo[out] = t - step
        found[out] = True
        t += step
    for _ in range(iters):
        tm = 0.5 * (t_hi + t_lo)
        pts = o + d * tm[:, None]
        f = F(pts[:, 0], pts[:, 1], pts[:, 2])
        inside = f < 0
        t_lo = np.where(inside, tm, t_lo)
        t_hi = np.where(inside, t_hi, tm)
    tm = 0.5 * (t_hi + t_lo)
    return o + d * tm[:, None], tm


def chart_of_points(P):
    """Chart coordinates of head points as seen from the ray origin (exact for b >= B_HEAD)."""
    P = np.asarray(P, np.float64) - ORIGIN
    lon = np.arctan2(P[..., 0], -P[..., 1])
    b = np.arctan2(P[..., 2], np.hypot(P[..., 0], P[..., 1]))
    return lon, b


def band_top_from(lons, zs):
    """Periodic interpolator lon -> z built from the lowest head row's hit points."""
    order = np.argsort(lons)
    L = np.asarray(lons)[order]
    Z = np.asarray(zs)[order]
    L = np.concatenate([L[-1:] - 2 * math.pi, L, L[:1] + 2 * math.pi])
    Z = np.concatenate([Z[-1:], Z, Z[:1]])
    return lambda lon: np.interp((np.asarray(lon) + math.pi) % (2 * math.pi) - math.pi, L, Z)

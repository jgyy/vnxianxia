"""UV layout of the head mesh (pure numpy - importable from texture code).

The head, neck and ears share one texture (the ``face`` material).  Every head
vertex has a chart coordinate (lon, b) (see ``face_chart``): lon = angle
around the vertical axis (0 = front, + = character's left), b = latitude of
the ray from the head centre (below the jaw it continues down the neck).

Islands (u right, v up, all characters share the layout):

====================  =========================  =================================
island                chart region               projection
====================  =========================  =================================
FACE  u 0.00-0.62     |lon| <= 80 deg,           Lambert azimuthal equal-area
      v 0.00-1.00     b <= 50 deg                centred on (lon 0, b -14 deg): a
                      (face, front of neck)      front projection without the edge
                                                 crush of an orthographic one; the
                                                 neck continues straight down
SIDE  u 0.63-1.00     |lon| >= 80 deg,           cylindrical, seam-free across the
      v 0.26-1.00     b <= 50 deg                back (u runs lon 80 -> 180 -> 280)
                      (temples, ears' root,
                      back of head, nape)
CROWN u 0.63-0.87     b >= 50 deg                azimuthal from the top of the head
      v 0.00-0.25                                (front of the head at the bottom)
EAR.L u 0.88-1.00, v 0.00-0.12 / EAR.R u 0.88-1.00, v 0.13-0.25: planar side projection
====================  =========================  =================================

Seams: vertical lines just in front of the ears (lon = +-80 deg, from the
collar to the temple), the circle b = 50 deg (well inside the hair), and the
ear roots.  The eye / mouth / nostril cavities keep the chart of their own
points, so they fall next to the opening they belong to.

For painting: ``lonb_from_uv(u, v)`` inverts the layout (per texel), and
``landmark_uv(cfg)`` gives the UV of the facial landmarks (eyes, brows,
lips, nose, jaw ...) for a character, so features can be painted exactly.
"""
import math

import numpy as np

from . import face_chart as fc

SEAM = math.radians(80.0)
TOP = math.radians(50.0)
CENTER_B = math.radians(-14.0)

# island boxes (u0, v0, u1, v1)
FACE_BOX = (0.0, 0.0, 0.62, 1.0)
SIDE_BOX = (0.63, 0.26, 1.0, 1.0)
CROWN_BOX = (0.63, 0.0, 0.87, 0.25)
EAR_BOX = {1: (0.88, 0.0, 1.0, 0.12), -1: (0.88, 0.13, 1.0, 0.25)}

B_MIN = fc.B_NECK - 0.5            # the lowest neck row (the collar, z ~ -225 mm)


def _below(b):
    """Arc length (unit-sphere units) below the B_HEAD row for neck / blend rows."""
    b = np.asarray(b, np.float64)
    blend = np.clip(fc.B_HEAD - np.maximum(b, fc.B_NECK), 0.0, None)
    neck = np.clip(fc.B_NECK - b, 0.0, None)
    return 1.6 * blend + (fc.NECK_DZ_PER_RAD / 90.0) * neck


def _neck_shrink(b):
    """Horizontal texel scale of a row relative to the B_HEAD row (the neck is narrower)."""
    t = np.clip((fc.B_HEAD - np.asarray(b, np.float64)) / (fc.B_HEAD - fc.B_NECK), 0.0, 1.0)
    return 1.0 - 0.45 * t


_WARP = {}


def _warps():
    """Arc-length warps (lon -> lon', b -> b') measured on a reference head.

    The chart is angular, but the face is not a sphere: rays graze the chin,
    the nose underside and the cheeks' turn, so equal chart steps cover very
    different skin distances.  Re-spacing the chart by the average surface
    arc length (blended 80 % with the plain angle) keeps texel density even
    over the face.  The reference is the default young female head, so the
    warp is the same for every character (and for texture painters)."""
    if not _WARP:
        from . import face_landmarks as fl
        from . import face_surface as fs
        cfg = dict(name="", female=True, head_r=(0.072, 0.093, 0.108), jaw=0.4)
        surf = fs.HeadSurface(fl.params_for(cfg))
        bs = np.linspace(fc.B_HEAD, TOP, 181)
        lons = np.linspace(-0.55, 0.55, 9)
        L, B = np.meshgrid(lons, bs)
        P, _ = fc.cast(surf.F, L.ravel(), B.ravel())
        P = P.reshape(len(bs), len(lons), 3)
        ds = np.linalg.norm(np.diff(P, axis=0), axis=-1).mean(axis=1)
        S = np.concatenate([[0.0], np.cumsum(ds)])
        wb = fc.B_HEAD + S / S[-1] * (TOP - fc.B_HEAD)
        _WARP["b"] = (bs, 0.8 * wb + 0.2 * bs)
        ls = np.linspace(-SEAM, SEAM, 161)
        bl = np.radians(np.linspace(-45.0, 15.0, 7))
        L, B = np.meshgrid(ls, bl)
        P, _ = fc.cast(surf.F, L.ravel(), B.ravel())
        P = P.reshape(len(bl), len(ls), 3)
        ds = np.linalg.norm(np.diff(P, axis=1), axis=-1).mean(axis=0)
        S = np.concatenate([[0.0], np.cumsum(ds)])
        wl = -SEAM + S / S[-1] * 2 * SEAM
        _WARP["lon"] = (ls, 0.8 * wl + 0.2 * ls)
    return _WARP


def warp_b(b, inverse=False):
    bs, wb = _warps()["b"]
    b = np.asarray(b, np.float64)
    src, dst = (wb, bs) if inverse else (bs, wb)
    inside = (b >= fc.B_HEAD) & (b <= TOP)
    return np.where(inside, np.interp(b, src, dst), b)


def warp_lon(lon, inverse=False):
    ls, wl = _warps()["lon"]
    lon = np.asarray(lon, np.float64)
    src, dst = (wl, ls) if inverse else (ls, wl)
    return np.where(np.abs(lon) <= SEAM, np.interp(lon, src, dst), lon)


def _azimuthal(lon, b):
    sb0, cb0 = math.sin(CENTER_B), math.cos(CENTER_B)
    sb, cb = np.sin(b), np.cos(b)
    k = np.sqrt(2.0 / np.maximum(1.0 + sb0 * sb + cb0 * cb * np.cos(lon), 1e-6))
    return k * cb * np.sin(lon), k * (cb0 * sb - sb0 * cb * np.cos(lon))


def _face_xy(lon, b):
    lon = warp_lon(lon)
    b = np.asarray(b, np.float64)
    b = warp_b(b)
    head = b >= fc.B_HEAD
    x, y = _azimuthal(lon, np.maximum(b, fc.B_HEAD))
    x = np.where(head, x, x * _neck_shrink(b))
    y = np.where(head, y, y - _below(b))
    return x, y


def _side_xy(lon, b):
    lon = np.mod(np.asarray(lon, np.float64), 2 * math.pi)       # 80 deg .. 280 deg, continuous at the back
    b = warp_b(b)
    y = np.where(b >= fc.B_HEAD, b, fc.B_HEAD - _below(b))
    return (lon - math.pi) * 0.72, y


def _crown_xy(lon, b):
    rho = 2.0 * np.sin((math.pi / 2 - np.asarray(b, np.float64)) / 2.0)
    return rho * np.sin(lon), -rho * np.cos(lon)


def _fit(box, xr, yr):
    """Uniform scale + offset mapping the chart extents (xr, yr) into box, centred."""
    u0, v0, u1, v1 = box
    sx = (u1 - u0) / (xr[1] - xr[0])
    sy = (v1 - v0) / (yr[1] - yr[0])
    s = min(sx, sy)
    cx = 0.5 * (u0 + u1) - s * 0.5 * (xr[0] + xr[1])
    cy = 0.5 * (v0 + v1) - s * 0.5 * (yr[0] + yr[1])
    return s, cx, cy


def _extent(fn, lons, bs):
    L, B = np.meshgrid(lons, bs)
    x, y = fn(L, B)
    return (float(x.min()), float(x.max())), (float(y.min()), float(y.max()))


_FIT = {}


def _fits():
    if not _FIT:
        lons = np.linspace(-SEAM, SEAM, 161)
        bs = np.linspace(B_MIN, TOP, 161)
        _FIT["face"] = _fit(FACE_BOX, *_extent(_face_xy, lons, bs))
        _FIT["side"] = _fit(SIDE_BOX, *_extent(_side_xy, np.linspace(SEAM, 2 * math.pi - SEAM, 161), bs))
        _FIT["crown"] = _fit(CROWN_BOX, *_extent(_crown_xy, np.linspace(-math.pi, math.pi, 181),
                                                  np.linspace(TOP, math.pi / 2, 20)))
    return _FIT


def island_of(lon, b):
    """0 = face, 1 = side, 2 = crown for chart coordinates (arrays)."""
    lon = np.asarray(lon, np.float64)
    b = np.asarray(b, np.float64)
    isl = np.where(np.abs(lon) <= SEAM, 0, 1)
    return np.where(b >= TOP, 2, isl)


def uv_from_lonb(lon, b, island=None):
    """UV for chart coordinates.  island forces the island (per-face assignment near seams)."""
    f = _fits()
    lon = np.asarray(lon, np.float64)
    b = np.asarray(b, np.float64)
    isl = island_of(lon, b) if island is None else np.asarray(island)
    u = np.zeros(np.broadcast(lon, b).shape)
    v = np.zeros_like(u)
    for k, name, fn in ((0, "face", _face_xy), (1, "side", _side_xy), (2, "crown", _crown_xy)):
        m = isl == k
        if not np.any(m):
            continue
        s, cx, cy = f[name]
        x, y = fn(np.broadcast_to(lon, u.shape)[m], np.broadcast_to(b, u.shape)[m])
        u[m] = cx + s * x
        v[m] = cy + s * y
    return u, v


def lonb_from_uv(u, v):
    """Inverse layout: (lon, b, island) per UV (island -1 = unused texel / ear box)."""
    f = _fits()
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    lon = np.zeros(np.broadcast(u, v).shape)
    b = np.zeros_like(lon)
    isl = np.full(lon.shape, -1)
    # face: invert the azimuthal projection, then the neck continuation
    s, cx, cy = f["face"]
    x, y = (u - cx) / s, (v - cy) / s
    rho = np.hypot(x, y)
    c = 2 * np.arcsin(np.clip(rho / 2, 0, 1))
    sb0, cb0 = math.sin(CENTER_B), math.cos(CENTER_B)
    with np.errstate(invalid="ignore", divide="ignore"):
        bb = np.arcsin(np.clip(np.cos(c) * sb0 + np.where(rho > 0, y * np.sin(c) * cb0 / rho, 0), -1, 1))
        ll = np.arctan2(x * np.sin(c), rho * cb0 * np.cos(c) - y * sb0 * np.sin(c))
    ll = warp_lon(ll, inverse=True)
    head_face = bb >= fc.B_HEAD
    bb = warp_b(np.maximum(bb, fc.B_HEAD), inverse=True)
    # rows below B_HEAD: solve x = X_B(lon) * shrink(b), y = Y_B(lon) - below(b) by fixed-point steps
    tab_l = np.linspace(-SEAM, SEAM, 321)
    tab_x, tab_y = _azimuthal(warp_lon(tab_l), np.full_like(tab_l, fc.B_HEAD))
    blend_len = 1.6 * (fc.B_HEAD - fc.B_NECK)
    b_neck = np.full_like(x, fc.B_HEAD)
    for _ in range(8):
        ll_n = np.interp(x / _neck_shrink(b_neck), tab_x, tab_l)
        drop = np.interp(ll_n, tab_l, tab_y) - y
        b_neck = np.where(drop <= blend_len, fc.B_HEAD - drop / 1.6,
                          fc.B_NECK - (drop - blend_len) / (fc.NECK_DZ_PER_RAD / 90.0))
    in_face = (u >= FACE_BOX[0]) & (u <= FACE_BOX[2])
    lon = np.where(in_face, np.where(head_face, ll, ll_n), lon)
    b = np.where(in_face, np.where(head_face, bb, b_neck), b)
    isl = np.where(in_face, 0, isl)
    # side
    s, cx, cy = f["side"]
    x, y = (u - cx) / s, (v - cy) / s
    in_side = (u >= SIDE_BOX[0]) & (v >= SIDE_BOX[1])
    ls = x / 0.72 + math.pi
    drop = fc.B_HEAD - y
    bs = np.where(y >= fc.B_HEAD, warp_b(y, inverse=True), np.where(drop <= blend_len, fc.B_HEAD - drop / 1.6,
                                               fc.B_NECK - (drop - blend_len) / (fc.NECK_DZ_PER_RAD / 90.0)))
    lon = np.where(in_side, (ls + math.pi) % (2 * math.pi) - math.pi, lon)
    b = np.where(in_side, bs, b)
    isl = np.where(in_side, 1, isl)
    # crown
    s, cx, cy = f["crown"]
    x, y = (u - cx) / s, (v - cy) / s
    in_crown = (u >= CROWN_BOX[0]) & (u <= CROWN_BOX[2]) & (v <= CROWN_BOX[3])
    rho = np.hypot(x, y)
    lon = np.where(in_crown, np.arctan2(x, -y), lon)
    b = np.where(in_crown, math.pi / 2 - 2 * np.arcsin(np.clip(rho / 2, 0, 1)), b)
    isl = np.where(in_crown, 2, isl)
    return lon, b, isl


def ear_uv(side, local_up, local_back, size):
    """Planar UV inside the ear box for ear-local (up, back) millimetres."""
    u0, v0, u1, v1 = EAR_BOX[side]
    half = 0.5 * size
    uu = u0 + (u1 - u0) * (0.5 + np.asarray(local_back) / (2 * half))
    vv = v0 + (v1 - v0) * (0.5 + np.asarray(local_up) / (2 * half))
    return uu, vv


def landmark_uv(cfg):
    """{landmark name: (u, v)} for a character: where to paint brows, lips, liner, blush ..."""
    from . import face_landmarks as fl
    p = fl.params_for(cfg)
    out = {}
    for name, pt in fl.landmarks(p).items():
        lon, b = fl.chart_of(pt)
        if pt[2] < -100 and abs(lon) < 1.0 and name.startswith("cervic"):
            b = float(fc.b_of_neck_z(pt[2]))
        u, v = uv_from_lonb(np.array([lon]), np.array([b]))
        out[name] = (float(u[0]), float(v[0]))
    # contours useful for painting: lip borders and the brow line
    stom, upper, lower = fl.lip_curves(p, 21)
    fy = -0.905 * p.head[1]
    for key, curve in (("lip_upper", upper), ("lip_lower", lower), ("stomion_line", stom)):
        pts = []
        for x, z in curve:
            lon, b = fl.chart_of((x, fy - 2.0, z))
            u, v = uv_from_lonb(np.array([lon]), np.array([b]))
            pts.append((float(u[0]), float(v[0])))
        out[key] = pts
    return out

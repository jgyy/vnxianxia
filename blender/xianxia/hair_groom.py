"""Hair grooming: scalp and body colliders, guide strands, a small solver, children.

Coordinates are Blender world space (metres, character faces -Y, +Z up).  Arrays of
strands are numpy (S, N, 3): S strands of N points, point 0 at the root.

Pipeline used by hair_styles:
  1. Head - the real head mesh (plus ears / eyes / lids) is ray-cast into a table of
     outermost surface distance by direction, giving fast vectorised scalp points,
     normals and push-out collision.  Scalp positions are addressed by (lon, lat) in
     the head's radii-normalised space: lon = 0 at the face, lat = asin(z), matching
     the hairline tables and the skin texture's face coordinates.
  2. Body - superellipse torso rings taken from the character's robe profile, a neck
     cylinder and upper-arm capsules.
  3. comb()      - grows guides from scalp roots along a style's flow field, lying on
                   the scalp at a per-strand layer height, until they leave the head;
     gather()    - scalp strands pulled toward a tie point (ponytail / bun / crown);
     coil()      - strands wound around a bun;
     relax()     - position-based relaxation: gravity, inextensible segments with
                   bending memory (follow-the-leader), head and body collision.
  4. children()  - interpolate guide shapes to many child roots, clump the tips,
                   add frizz, cut layers, resample to card resolution.
"""
import math

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

DOWN = np.array([0.0, 0.0, -1.0], np.float32)


def norm(v, axis=-1):
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-9)


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------
# head collider / scalp
# --------------------------------------------------------------------------
class Head:
    """Star-shaped surface model of the head built by ray casting its meshes."""

    NT, NP = 256, 128        # table resolution: longitude x latitude of world directions
    FAR = 0.6

    def __init__(self, objs, centre, radii, hairline):
        self.c = np.array(centre, np.float32)
        self.radii = np.array(radii, np.float32)
        self.hairline = hairline               # |lon| -> unit-sphere z of the hairline
        verts, polys = [], []
        for o in objs:
            me = o.data
            mw = o.matrix_world
            base = len(verts)
            verts.extend(mw @ v.co for v in me.vertices)
            polys.extend([base + i for i in p.vertices] for p in me.polygons)
        self.bvh = BVHTree.FromPolygons(verts, polys)
        th = (np.arange(self.NT) + 0.5) / self.NT * 2 * math.pi - math.pi
        ph = (np.arange(self.NP) + 0.5) / self.NP * math.pi - math.pi / 2
        table = np.zeros((self.NP, self.NT), np.float32)
        c = Vector(self.c.tolist())
        for j, p in enumerate(ph):
            for i, t in enumerate(th):
                d = Vector((math.sin(t) * math.cos(p), -math.cos(t) * math.cos(p), math.sin(p)))
                hit = self.bvh.ray_cast(c + d * self.FAR, -d, self.FAR)
                table[j, i] = self.FAR - hit[3] if hit[0] is not None else 0.0
        # directions that miss (under the jaw, into the neck) fall back to the ellipsoid
        miss = table <= 0
        if miss.any():
            tt, pp = np.meshgrid(th, ph)
            d = np.stack([np.sin(tt) * np.cos(pp), -np.cos(tt) * np.cos(pp), np.sin(pp)], -1)
            table[miss] = 1.0 / np.linalg.norm(d / self.radii, axis=-1)[miss]
        self.table = table

    # -- lookups ---------------------------------------------------------
    def radius(self, d):
        """Outermost surface distance along unit world directions d (..., 3)."""
        t = np.arctan2(d[..., 0], -d[..., 1])
        p = np.arcsin(np.clip(d[..., 2], -1, 1))
        x = (t + math.pi) / (2 * math.pi) * self.NT - 0.5
        y = np.clip((p + math.pi / 2) / math.pi * self.NP - 0.5, 0, self.NP - 1.001)
        x0 = np.floor(x).astype(int)
        y0 = np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        x0m, x1m = x0 % self.NT, (x0 + 1) % self.NT
        tb = self.table
        a = tb[y0, x0m] * (1 - fx) + tb[y0, x1m] * fx
        b = tb[y0 + 1, x0m] * (1 - fx) + tb[y0 + 1, x1m] * fx
        return a * (1 - fy) + b * fy

    def dir_of(self, lon, lat):
        e = np.stack([np.sin(lon) * np.cos(lat), -np.cos(lon) * np.cos(lat), np.sin(lat)], -1)
        return norm(e * self.radii)

    def point(self, lon, lat, h=0.0):
        """Scalp point at head coordinates (lon, lat), lifted h metres off the surface."""
        d = self.dir_of(np.asarray(lon, np.float32), np.asarray(lat, np.float32))
        return self.c + d * (self.radius(d) + h)[..., None]

    def normal(self, lon, lat, eps=0.01):
        lon = np.asarray(lon, np.float32)
        lat = np.asarray(lat, np.float32)
        a = self.point(lon + eps, lat) - self.point(lon - eps, lat)
        b = self.point(lon, lat + eps) - self.point(lon, lat - eps)
        n = norm(np.cross(b, a))
        out = self.dir_of(lon, lat)
        return np.where((np.sum(n * out, -1) < 0)[..., None], -n, n)

    def lonlat(self, p):
        e = norm((p - self.c) / self.radii)
        return np.arctan2(e[..., 0], -e[..., 1]), np.arcsin(np.clip(e[..., 2], -1, 1))

    def height(self, p):
        """Signed distance above the outer surface along the ray from the centre."""
        d = p - self.c
        r = np.linalg.norm(d, axis=-1)
        return r - self.radius(d / np.maximum(r, 1e-9)[..., None])

    def push(self, p, off=0.003):
        d = p - self.c
        r = np.linalg.norm(d, axis=-1)
        dn = d / np.maximum(r, 1e-9)[..., None]
        rs = self.radius(dn) + off
        inside = r < rs
        return np.where(inside[..., None], self.c + dn * rs[..., None], p)

    def in_scalp(self, lon, lat, margin=0.0):
        """True where (lon, lat) lies above the hairline."""
        return np.sin(lat) > self.hairline(np.abs(lon)) + margin

    def sample(self, rng, n, lon_range=(-math.pi, math.pi), lat_range=(-1.2, 1.5), accept=None,
               hairline_margin=0.0):
        """Area-uniform random scalp roots in a lon/lat window (above the hairline)."""
        out_lon, out_lat = [], []
        got = 0
        z0, z1 = math.sin(lat_range[0]), math.sin(lat_range[1])
        for _ in range(60):
            m = max(64, (n - got) * 3)
            lon = rng.uniform(*lon_range, m).astype(np.float32)
            lat = np.arcsin(rng.uniform(z0, z1, m)).astype(np.float32)
            ok = self.in_scalp(lon, lat, hairline_margin)
            if accept is not None:
                ok &= accept(lon, lat)
            out_lon.append(lon[ok])
            out_lat.append(lat[ok])
            got += int(ok.sum())
            if got >= n:
                break
        lon = np.concatenate(out_lon)[:n]
        lat = np.concatenate(out_lat)[:n]
        return lon, lat


# --------------------------------------------------------------------------
# body collider
# --------------------------------------------------------------------------
class Body:
    """Robe torso (superellipse rings), neck cylinder and upper-arm capsules."""

    def __init__(self, cfg, joints, s):
        rings = np.array(cfg["robe"], np.float32)
        self.z = rings[:, 0] * s
        self.hw = rings[:, 1] * s
        self.hd = rings[:, 2] * s
        self.yc = rings[:, 3] * s
        self.sq = rings[:, 4]
        nh, nt, _ = joints["neck"]
        self.neck = (np.array(nh, np.float32), np.array(nt, np.float32), cfg["neck_r"] * s * 1.15)
        self.arms = []
        for side in ("L", "R"):
            h, t, _ = joints[f"upper_arm.{side}"]
            self.arms.append((np.array(h, np.float32), np.array(t, np.float32), 0.07 * s))

    def _torso(self, p, off):
        z = p[..., 2]
        top = self.z[-1]
        hw = np.interp(z, self.z, self.hw) + off
        hd = np.interp(z, self.z, self.hd) + off
        yc = np.interp(z, self.z, self.yc)
        sq = np.interp(z, self.z, self.sq)
        x = p[..., 0] / hw
        y = (p[..., 1] - yc) / hd
        n = (np.abs(x) ** sq + np.abs(y) ** sq) ** (1 / sq)
        inside = (n < 1) & (z < top) & (z > self.z[0])
        k = 1 / np.maximum(n, 1e-6)
        q = np.stack([p[..., 0] * k, yc + (p[..., 1] - yc) * k, z], -1)
        return np.where(inside[..., None], q, p)

    @staticmethod
    def _capsule(p, a, b, r):
        ab = b - a
        t = np.clip(np.sum((p - a) * ab, -1) / float(ab @ ab), 0, 1)
        c = a + t[..., None] * ab
        d = p - c
        dist = np.linalg.norm(d, axis=-1)
        inside = dist < r
        q = c + d / np.maximum(dist, 1e-9)[..., None] * r
        return np.where(inside[..., None], q, p)

    def push(self, p, off=0.01):
        p = self._torso(p, off)
        a, b, r = self.neck
        p = self._capsule(p, a, b, r + off)
        for a, b, r in self.arms:
            p = self._capsule(p, a, b, r + off)
        return p


# --------------------------------------------------------------------------
# strand construction
# --------------------------------------------------------------------------
def tangent_project(v, n):
    return v - np.sum(v * n, -1, keepdims=True) * n


def comb(head, lon, lat, lengths, flow, n_pts=24, lift=0.004, layer=None, root_lift=0.35):
    """Grow strands over the scalp along a flow field, then straight on when they leave it.

    flow(p, lon, lat) -> (S, 3) desired direction (projected to the scalp tangent plane).
    layer: (S,) height above the scalp each strand lies at (volume).
    root_lift: how much the first segment points away from the scalp (root volume).
    """
    S = lon.shape[0]
    layer = np.full(S, 0.006, np.float32) if layer is None else layer
    seg = (lengths / (n_pts - 1)).astype(np.float32)
    P = np.zeros((S, n_pts, 3), np.float32)
    P[:, 0] = head.point(lon, lat, lift)
    nrm = head.normal(lon, lat)
    d = norm(tangent_project(flow(P[:, 0], lon, lat), nrm) + nrm * root_lift)
    on = np.ones(S, bool)
    for i in range(1, n_pts):
        p = P[:, i - 1] + d * seg[:, None]
        la, lt = head.lonlat(p)
        h = head.height(p)
        target = np.minimum(layer * smooth(i / 3.0), layer)
        ride = on & (h < target + 0.02)
        pn = head.normal(la, lt)
        # ride the scalp: clamp to the layer height while the strand is over the head
        lifted = head.point(la, lt, target)
        p = np.where(ride[:, None], lifted, p)
        f = flow(p, la, lt)
        nd = norm(np.where(ride[:, None], tangent_project(f, pn), f))
        # once past the widest part (strand heading down and outward) it leaves the scalp
        on &= ~((nd[:, 2] < -0.75) & (lt < 0.25))
        d = norm(d * 0.35 + nd * 0.65)
        P[:, i] = p
    return P


def gather(head, lon, lat, tie, rng, n_pts=12, lift=0.003, bulge=0.012, tight=0.004, tie_radius=0.012):
    """Scalp strands pulled from their roots to a tie point (hair combed up / back).

    Each point is the chord root->tie pushed out to the scalp plus a height that is
    `bulge` at mid-way (soft volume at the crown) and falls to `tight` at the band.
    Roots arrive spread over a small disc around the tie (the gathered bundle).
    """
    S = lon.shape[0]
    root = head.point(lon, lat, lift)
    t = np.linspace(0, 1, n_pts, dtype=np.float32)
    ends = np.asarray(tie, np.float32) + norm(rng.normal(0, 1, (S, 3)).astype(np.float32)) \
        * tie_radius * np.sqrt(rng.random((S, 1)))
    chord = root[:, None, :] * (1 - t[None, :, None]) + ends[:, None, :] * t[None, :, None]
    la, lt = head.lonlat(chord)
    band = smooth((t - 0.75) / 0.25)[None, :]
    h = lift + bulge * np.sin(np.pi * np.clip(t * 1.15, 0, 1))[None, :] * rng.uniform(0.5, 1.3, (S, 1))
    h = h * (1 - band) + tight * band
    on_surface = head.point(la, lt, h)
    # near the tie the bundle leaves the scalp: keep the straight chord where it is outside
    outside = head.height(chord) > h
    P = np.where(outside[..., None], chord, on_surface)
    P[:, -1] = ends
    return P.astype(np.float32)


def coil(centre, axis, radius, height, turns, S, n_pts, rng):
    """Strands wound around a bun: helices around `axis` with jittered phase and radius."""
    axis = norm(np.asarray(axis, np.float32))
    ref = np.array([1, 0, 0], np.float32) if abs(axis[0]) < 0.9 else np.array([0, 1, 0], np.float32)
    u = norm(np.cross(axis, ref))
    v = np.cross(axis, u)
    t = np.linspace(0, 1, n_pts, dtype=np.float32)[None, :]
    ph = rng.uniform(0, 2 * math.pi, (S, 1)).astype(np.float32)
    tw = turns * rng.uniform(0.7, 1.1, (S, 1))
    r = radius * rng.uniform(0.55, 1.05, (S, 1)) * (1 - 0.35 * t)
    hgt = (rng.uniform(-0.5, 0.5, (S, 1)) * height) * (1 - 0.4 * t) + height * 0.25 * t
    a = ph + 2 * math.pi * tw * t
    P = (np.asarray(centre, np.float32)[None, None, :] + (np.cos(a) * r)[..., None] * u
         + (np.sin(a) * r)[..., None] * v + hgt[..., None] * axis)
    return P.astype(np.float32)


def hang(start, dirs, lengths, n_pts=20):
    """Straight initial strands from `start` points along dirs (relaxed afterwards)."""
    t = np.linspace(0, 1, n_pts, dtype=np.float32)[None, :, None]
    return (start[:, None, :] + norm(dirs)[:, None, :] * (lengths[:, None, None] * t)).astype(np.float32)


def braid(axis, width, crossings, rng, cards_per_lock=4, taper=0.55):
    """Three-strand plait around a centre curve.

    axis: (N, 3) draped centre line.  Each lock follows the classic figure-eight: across
    the plait sin(theta) and front/back 0.5 sin(2 theta), a third of a turn apart, so the
    outer lock is always crossed over the middle one.  Every lock is a small clump of
    card centre-lines.  Returns (3 * cards_per_lock, N, 3).
    """
    N = len(axis)
    T = norm(np.gradient(axis, axis=0))
    ref = np.where(np.abs(T[:, 2:3]) > 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 0, 1.0]])).astype(np.float32)
    side = norm(np.cross(T, ref))
    depth = np.cross(T, side)
    t = np.linspace(0, 1, N, dtype=np.float32)
    w = width * (1 - (1 - taper) * t)[:, None]
    out = []
    for k in range(3):
        th = 2 * math.pi * (crossings * 0.5 * t + k / 3.0)
        centre = axis + side * (np.sin(th) * w[:, 0] * 0.5)[:, None] + depth * (np.sin(2 * th) * w[:, 0] * 0.22)[:, None]
        for _ in range(cards_per_lock):
            jitter = side * rng.normal(0, 0.12) * w + depth * rng.normal(0, 0.08) * w
            out.append(centre + jitter)
    return np.stack(out).astype(np.float32)


# --------------------------------------------------------------------------
# solver
# --------------------------------------------------------------------------
def _ftl(P, rest, seg, bend):
    """Follow-the-leader inextensibility with bending memory of the rest directions."""
    for i in range(1, P.shape[1]):
        d = P[:, i] - P[:, i - 1]
        dr = rest[:, i] - rest[:, i - 1]
        k = bend[i]
        d = d * (1 - k) + dr * k
        P[:, i] = P[:, i - 1] + norm(d) * seg[:, i - 1, None]
    return P


def relax(P, head, body, iters=36, gravity=0.004, stiff_root=0.55, stiff_tip=0.04, pin=1, head_off=0.004,
          body_off=0.012, force=None):
    """Drape strands: gravity + inextensible segments + bending memory + collisions.

    P: (S, N, 3) initial ("combed") shape, also used as the bending rest state.
    force(P) -> (S, N, 3) optional extra displacement per iteration (wind, sweep).
    """
    rest = P.copy()
    seg = np.linalg.norm(np.diff(rest, axis=1), axis=2)
    n = P.shape[1]
    bend = stiff_tip + (stiff_root - stiff_tip) * (1 - np.linspace(0, 1, n)) ** 2
    P = P.copy()
    for _ in range(iters):
        P[:, pin:, 2] -= gravity
        if force is not None:
            P[:, pin:] += force(P)[:, pin:]
        P = _ftl(P, rest, seg, bend)
        P[:, pin:] = head.push(P[:, pin:], head_off)
        if body is not None:
            P[:, pin:] = body.push(P[:, pin:], body_off)
    P = _ftl(P, rest, seg, bend * 0.5)
    P[:, pin:] = head.push(P[:, pin:], head_off)
    if body is not None:
        P[:, pin:] = body.push(P[:, pin:], body_off)
    return P


# --------------------------------------------------------------------------
# children
# --------------------------------------------------------------------------
def resample(P, n_pts, keep=None):
    """Resample strands to n_pts points evenly by arc length (optionally the first `keep` fraction)."""
    S, N, _ = P.shape
    seg = np.linalg.norm(np.diff(P, axis=1), axis=2)
    cum = np.concatenate([np.zeros((S, 1), np.float32), np.cumsum(seg, 1)], 1)
    total = cum[:, -1:]
    frac = np.ones((S, 1), np.float32) if keep is None else np.asarray(keep, np.float32).reshape(S, 1)
    target = np.linspace(0, 1, n_pts, dtype=np.float32)[None, :] * total * frac
    out = np.zeros((S, n_pts, 3), np.float32)
    idx = np.clip(np.array([np.searchsorted(cum[i], target[i]) for i in range(S)]), 1, N - 1)
    c0 = np.take_along_axis(cum, idx - 1, 1)
    c1 = np.take_along_axis(cum, idx, 1)
    f = ((target - c0) / np.maximum(c1 - c0, 1e-9))[..., None]
    a = np.take_along_axis(P, (idx - 1)[..., None].repeat(3, 2), 1)
    b = np.take_along_axis(P, idx[..., None].repeat(3, 2), 1)
    out[:] = a + (b - a) * f
    return out


def lengths(P):
    return np.linalg.norm(np.diff(P, axis=1), axis=2).sum(1)


def children(guides, g_roots, c_roots, rng, k=3, clump=0.5, clump_size=6, frizz=0.0, head=None, body=None,
             head_off=0.004, body_off=0.012):
    """Child strands interpolated from guides and clumped.

    guides: (G, N, 3) simulated guides; g_roots / c_roots: (G, 3) / (C, 3) root positions.
    Each child copies the root-relative shape of its k nearest guides (inverse distance
    weights), then every `clump_size` neighbouring children share a clump leader whose
    tip they are pulled toward (tapered clumps with gaps between them).
    """
    C = c_roots.shape[0]
    d = np.linalg.norm(c_roots[:, None, :] - g_roots[None, :, :], axis=-1)
    kk = min(k, guides.shape[0])
    nn = np.argpartition(d, kk - 1, axis=1)[:, :kk]
    dn = np.take_along_axis(d, nn, 1)
    w = 1.0 / (dn + 1e-3) ** 2
    w /= w.sum(1, keepdims=True)
    rel = guides - guides[:, :1]
    shape = np.einsum("ck,ckns->cns", w, rel[nn])
    P = c_roots[:, None, :] + shape
    N = P.shape[1]
    t = np.linspace(0, 1, N, dtype=np.float32)[None, :, None]
    if clump > 0 and C > clump_size:
        n_clumps = max(1, C // clump_size)
        leaders = rng.choice(C, n_clumps, replace=False)
        dl = np.linalg.norm(c_roots[:, None, :] - c_roots[leaders][None, :, :], axis=-1)
        own = leaders[np.argmin(dl, 1)]
        strength = (clump * rng.uniform(0.6, 1.2, C)).clip(0, 0.95)[:, None, None]
        prof = smooth((t - 0.15) / 0.85) ** 1.2
        target = P[own] + (P[:, :1] - P[own][:, :1]) * (1 - prof)
        P = P + (target - P) * strength * prof
    if frizz > 0:
        L = lengths(P)[:, None, None]
        low = rng.normal(0, 1, (C, 4, 3)).astype(np.float32)
        tt = np.linspace(0, 3, N, dtype=np.float32)
        i0 = np.floor(tt).astype(int).clip(0, 2)
        f = (tt - i0)[None, :, None]
        wave = low[:, i0] * (1 - f) + low[:, i0 + 1] * f
        P = P + wave * frizz * L * 0.06 * t ** 1.5
    if head is not None:
        P[:, 1:] = head.push(P[:, 1:], head_off)
    if body is not None:
        P[:, 1:] = body.push(P[:, 1:], body_off)
    return P

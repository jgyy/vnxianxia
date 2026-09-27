"""Shared ground model of the exterior maps (pure Python, no dependencies).

A map module builds one ``Ground``: a base height function, then *pads* that
level, raise or dig the ground inside 2D shapes (terraces, building plots,
roads, ramps under stairways, lakes), then *regions* that give parts of the
ground a surface material (paving, road, dirt, crops...), and *waters* (flat
liquid surfaces). The map builder uses ``Ground.height`` to seat every prop and
marker; the Blender terrain builder (blender/xianxia/lands.py ``ground_terrain``)
meshes the same height field and splits every triangle exactly along the region
outlines, so paving, roads and grass are one continuous surface: nothing is laid
on top of the terrain, and nothing can z-fight with it.

Coordinates are Godot's (x east, z south, y up).
"""
import math

# --------------------------------------------------------------------------
# noise / geometry helpers (bit-identical to the ones the first maps used)
# --------------------------------------------------------------------------


def _hash(ix, iz, seed):
    h = (ix * 73856093 ^ iz * 19349663 ^ seed * 83492791) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 32767.5 - 1.0


def noise2(x, z, seed=0):
    """Smooth value noise in [-1, 1]."""
    ix, iz = math.floor(x), math.floor(z)
    fx, fz = x - ix, z - iz
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a = _hash(ix, iz, seed)
    b = _hash(ix + 1, iz, seed)
    c = _hash(ix, iz + 1, seed)
    d = _hash(ix + 1, iz + 1, seed)
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fz


def fbm2(x, z, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * noise2(x, z, seed + o * 17)
        norm += amp
        amp *= 0.5
        x, z = x * 2.03 + 11.7, z * 2.03 - 5.3
    return total / norm


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def catmull(points, samples=6):
    """Catmull-Rom smoothing of a 2D (or 3D) poly-line."""
    out = []
    n = len(points)
    dim = len(points[0])
    for i in range(n - 1):
        p0, p1 = points[max(i - 1, 0)], points[i]
        p2, p3 = points[i + 1], points[min(i + 2, n - 1)]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(dim)))
    out.append(tuple(points[-1]))
    return out


class Polyline:
    """A smoothed 2D poly-line with a fast distance query."""

    def __init__(self, points, width=3.0, samples=6):
        self.pts = catmull(points, samples)
        self.width = width
        xs = [p[0] for p in self.pts]
        zs = [p[1] for p in self.pts]
        self.bbox = (min(xs), min(zs), max(xs), max(zs))

    def distance(self, x, z, reach=1e9):
        """(distance, t along the line 0..1). Returns (reach, 0) if clearly far."""
        x0, z0, x1, z1 = self.bbox
        if x < x0 - reach or x > x1 + reach or z < z0 - reach or z > z1 + reach:
            return reach, 0.0
        best, bt = 1e18, 0.0
        n = len(self.pts) - 1
        for i in range(n):
            ax, az = self.pts[i]
            bx, bz = self.pts[i + 1]
            dx, dz = bx - ax, bz - az
            ll = dx * dx + dz * dz
            t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / ll))
            px, pz = ax + dx * t - x, az + dz * t - z
            d = px * px + pz * pz
            if d < best:
                best, bt = d, (i + t) / n
        return math.sqrt(best), bt

    def point(self, t):
        f = t * (len(self.pts) - 1)
        i = min(int(f), len(self.pts) - 2)
        k = f - i
        (ax, az), (bx, bz) = self.pts[i], self.pts[i + 1]
        return ax + (bx - ax) * k, az + (bz - az) * k

    def tangent(self, t):
        f = t * (len(self.pts) - 1)
        i = min(int(f), len(self.pts) - 2)
        (ax, az), (bx, bz) = self.pts[i], self.pts[i + 1]
        ln = math.hypot(bx - ax, bz - az) or 1.0
        return (bx - ax) / ln, (bz - az) / ln


def yaw_facing(x, z, tx, tz):
    """Yaw (degrees) that turns a +Z-facing asset at (x, z) toward (tx, tz)."""
    return math.degrees(math.atan2(tx - x, tz - z))


# --------------------------------------------------------------------------
# 2D shapes with signed distance (negative inside)
# --------------------------------------------------------------------------
class Shape:
    bbox = (0.0, 0.0, 0.0, 0.0)

    def sdf(self, x, z):
        raise NotImplementedError

    def inflate(self, pad):
        x0, z0, x1, z1 = self.bbox
        return (x0 - pad, z0 - pad, x1 + pad, z1 + pad)


class Rect(Shape):
    """Rectangle centred on (cx, cz), half sizes hw (along local x) and hd, turned by yaw degrees
    (same sense as a map item's yaw), with rounded corners of radius r."""

    def __init__(self, cx, cz, hw, hd, yaw=0.0, r=0.0):
        self.cx, self.cz, self.hw, self.hd, self.r = cx, cz, hw, hd, r
        a = math.radians(yaw)
        self.c, self.s = math.cos(a), math.sin(a)
        ext = math.hypot(hw, hd)
        ex = abs(hw * self.c) + abs(hd * self.s) if yaw else hw
        ez = abs(hw * self.s) + abs(hd * self.c) if yaw else hd
        ex, ez = min(ex, ext), min(ez, ext)
        self.bbox = (cx - ex, cz - ez, cx + ex, cz + ez)

    def local(self, x, z):
        dx, dz = x - self.cx, z - self.cz
        # inverse of the item rotation: item local (lx, lz) -> world (c*lx + s*lz, -s*lx + c*lz)
        return self.c * dx - self.s * dz, self.s * dx + self.c * dz

    def sdf(self, x, z):
        lx, lz = self.local(x, z)
        qx = abs(lx) - self.hw + self.r
        qz = abs(lz) - self.hd + self.r
        out = math.hypot(max(qx, 0.0), max(qz, 0.0))
        return out + min(max(qx, qz), 0.0) - self.r


def box(x0, z0, x1, z1, r=0.0):
    """Axis-aligned Rect from corner coordinates."""
    return Rect((x0 + x1) / 2, (z0 + z1) / 2, abs(x1 - x0) / 2, abs(z1 - z0) / 2, 0.0, r)


class Disc(Shape):
    def __init__(self, cx, cz, r, sx=1.0, sz=1.0, wobble=0.0, seed=0):
        self.cx, self.cz, self.r, self.sx, self.sz = cx, cz, r, sx, sz
        self.wobble, self.seed = wobble, seed
        rr = r * max(sx, sz) * (1 + wobble)
        self.bbox = (cx - rr, cz - rr, cx + rr, cz + rr)

    def sdf(self, x, z):
        ex, ez = (x - self.cx) / self.sx, (z - self.cz) / self.sz
        d = math.hypot(ex, ez)
        r = self.r
        if self.wobble:
            a = math.atan2(ez, ex)
            r *= 1.0 + self.wobble * noise2(math.cos(a) * 1.7 + self.seed * 3.1, math.sin(a) * 1.7, self.seed)
        return (d - r) * min(self.sx, self.sz)


class Path(Shape):
    """A band of the given width around a poly-line (smoothed with Catmull-Rom when samples > 1).

    Points may carry a height, (x, z, y): ``level`` then interpolates it along the line, which makes
    the path usable as a ramp pad (a road or the bed of a stairway climbing a slope). ``wobble``
    roughens the edges (dirt tracks)."""

    def __init__(self, points, width, samples=1, wobble=0.0, seed=0, flat_ends=False):
        pts = catmull(points, samples) if samples > 1 else [tuple(p) for p in points]
        self.pts = [(p[0], p[1]) for p in pts]
        self.ys = [p[2] for p in pts] if len(pts[0]) > 2 else None
        self.hw = width / 2
        self.wobble, self.seed = wobble, seed
        self.flat_ends = flat_ends
        xs = [p[0] for p in self.pts]
        zs = [p[1] for p in self.pts]
        pad = self.hw * (1 + wobble) + 0.5
        self.bbox = (min(xs) - pad, min(zs) - pad, max(xs) + pad, max(zs) + pad)
        # cumulative lengths, for points along the path
        self.cum = [0.0]
        for a, b in zip(self.pts[:-1], self.pts[1:]):
            self.cum.append(self.cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.cum[-1]

    def nearest(self, x, z):
        """(distance, segment index, t in the segment, projection outside the ends)."""
        best, bi, bt, out = 1e18, 0, 0.0, 0.0
        for i in range(len(self.pts) - 1):
            ax, az = self.pts[i]
            bx, bz = self.pts[i + 1]
            dx, dz = bx - ax, bz - az
            ll = dx * dx + dz * dz
            tr = 0.0 if ll == 0 else ((x - ax) * dx + (z - az) * dz) / ll
            t = max(0.0, min(1.0, tr))
            px, pz = ax + dx * t - x, az + dz * t - z
            d = px * px + pz * pz
            if d < best:
                best, bi, bt = d, i, t
                out = (tr - t) * math.sqrt(ll)
        return math.sqrt(best), bi, bt, out

    def sdf(self, x, z):
        d, i, t, out = self.nearest(x, z)
        if self.flat_ends and out != 0.0:
            # square ends: distance across the band only, and how far past the end
            ax, az = self.pts[i]
            bx, bz = self.pts[i + 1]
            ln = math.hypot(bx - ax, bz - az) or 1.0
            across = abs((x - ax) * (bz - az) - (z - az) * (bx - ax)) / ln
            q = (across - self.hw, abs(out))
            return math.hypot(max(q[0], 0), max(q[1], 0)) + min(max(q[0], q[1]), 0)
        w = self.hw
        if self.wobble:
            w *= 1.0 + self.wobble * noise2(x * 0.25 + self.seed, z * 0.25, self.seed + 7)
        return d - w

    def level(self, x, z):
        _, i, t, _ = self.nearest(x, z)
        return self.ys[i] + (self.ys[i + 1] - self.ys[i]) * t

    def at(self, s):
        """Point (x, z) and unit tangent at distance s along the path."""
        s = max(0.0, min(self.length, s))
        for i in range(len(self.pts) - 1):
            if s <= self.cum[i + 1] or i == len(self.pts) - 2:
                seg = self.cum[i + 1] - self.cum[i] or 1.0
                f = (s - self.cum[i]) / seg
                (ax, az), (bx, bz) = self.pts[i], self.pts[i + 1]
                return (ax + (bx - ax) * f, az + (bz - az) * f), ((bx - ax) / seg, (bz - az) / seg)
        return self.pts[-1], (1.0, 0.0)


class Poly(Shape):
    """Simple polygon (any winding)."""

    def __init__(self, pts):
        self.pts = [tuple(p) for p in pts]
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        self.bbox = (min(xs), min(zs), max(xs), max(zs))

    def sdf(self, x, z):
        pts = self.pts
        n = len(pts)
        d = 1e18
        inside = False
        for i in range(n):
            ax, az = pts[i]
            bx, bz = pts[(i + 1) % n]
            dx, dz = bx - ax, bz - az
            ll = dx * dx + dz * dz
            t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / ll))
            px, pz = ax + dx * t - x, az + dz * t - z
            d = min(d, px * px + pz * pz)
            if (az > z) != (bz > z) and x < ax + (z - az) * dx / dz:
                inside = not inside
        d = math.sqrt(d)
        return -d if inside else d


class Union(Shape):
    def __init__(self, *shapes):
        self.shapes = shapes
        bb = [s.bbox for s in shapes]
        self.bbox = (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb))

    def sdf(self, x, z):
        return min(s.sdf(x, z) for s in self.shapes)


class Ring(Shape):
    """Annulus between radii r0 and r1."""

    def __init__(self, cx, cz, r0, r1):
        self.cx, self.cz, self.r0, self.r1 = cx, cz, r0, r1
        self.bbox = (cx - r1, cz - r1, cx + r1, cz + r1)

    def sdf(self, x, z):
        d = math.hypot(x - self.cx, z - self.cz)
        return max(self.r0 - d, d - self.r1)


# --------------------------------------------------------------------------
# the ground
# --------------------------------------------------------------------------
class _Bins:
    """Spatial hash of shapes by bounding box (cells of `cell` metres)."""

    def __init__(self, cell=24.0):
        self.cell = cell
        self.cells = {}
        self.count = 0

    def add(self, bbox, item):
        c = self.cell
        idx = self.count
        self.count += 1
        for i in range(math.floor(bbox[0] / c), math.floor(bbox[2] / c) + 1):
            for j in range(math.floor(bbox[1] / c), math.floor(bbox[3] / c) + 1):
                self.cells.setdefault((i, j), []).append((idx, item))

    def near(self, x, z):
        return self.cells.get((math.floor(x / self.cell), math.floor(z / self.cell)), ())


class Ground:
    """Height field + surface regions + water surfaces of one exterior map.

    base(x, z) -> height before pads. Pads are applied in the order they were added:
      op "set": blend toward level inside the shape (smoothly over `blend` metres outside it)
      op "max": raise to at least level;  op "min": dig down to at most level
    level is a number or a callable (x, z) -> height (a sloped Path's ``level`` makes ramps).
    after(x, z, h) -> h runs last (outer cliffs, valley walls).
    Regions are (material key, shape); the first region containing a point wins.
    classify(x, z, h, slope_nz) -> material key for ground outside every region.
    """

    def __init__(self, bounds, step, base, classify, after=None, chunk=40):
        self.bounds = bounds            # (x0, z0, x1, z1)
        self.step = step
        self.base = base
        self.classify = classify
        self.after = after
        self.chunk = chunk              # grid cells per terrain chunk (mesh + collision)
        self._pads = []
        self._pad_bins = _Bins(24.0)
        self.regions = []
        self._reg_bins = _Bins(24.0)
        self.waters = []                # (material key, shape, level)
        self.floor = None               # triangles entirely below this height are left out of the mesh

    # -- building the ground -------------------------------------------------------------
    def pad(self, shape, level, blend=6.0, op="set"):
        self._pad_bins.add(shape.inflate(blend), (shape, level, blend, op))
        self._pads.append((shape, level, blend, op))
        return shape

    def region(self, mat, shape):
        self._reg_bins.add(shape.bbox, (mat, shape))
        self.regions.append((mat, shape))
        return shape

    def water(self, mat, shape, level):
        self.waters.append((mat, shape, level))
        return shape

    # -- queries -------------------------------------------------------------------------
    def height(self, x, z):
        h = self.base(x, z)
        for _, (shape, level, blend, op) in self._pad_bins.near(x, z):
            d = shape.sdf(x, z)
            if d >= blend:
                continue
            lv = level(x, z) if callable(level) else level
            w = 1.0 if d <= 0 else smoothstep(blend, 0.0, d)
            if op == "set":
                h = h + (lv - h) * w
            elif op == "max":
                if lv > h:
                    h = h + (lv - h) * w
            elif op == "min":
                if lv < h:
                    h = h + (lv - h) * w
        if self.after is not None:
            h = self.after(x, z, h)
        return h

    def surface(self, x, z):
        """Material key of the region at (x, z), or None outside every region."""
        best = None
        for idx, (mat, shape) in self._reg_bins.near(x, z):
            if (best is None or idx < best[0]) and shape.sdf(x, z) <= 0:
                best = (idx, mat)
        return best[1] if best else None

    def regions_near(self, bbox):
        """Regions (index, mat, shape) whose bins touch bbox, in priority order."""
        c = self._reg_bins.cell
        seen = {}
        for i in range(math.floor(bbox[0] / c), math.floor(bbox[2] / c) + 1):
            for j in range(math.floor(bbox[1] / c), math.floor(bbox[3] / c) + 1):
                for idx, (mat, shape) in self._reg_bins.cells.get((i, j), ()):
                    seen[idx] = (mat, shape)
        return [(i, *seen[i]) for i in sorted(seen)]

    def slope_nz(self, x, z, e=1.0):
        """Up component of the ground normal (1 = flat)."""
        hx = self.height(x + e, z) - self.height(x - e, z)
        hz = self.height(x, z + e) - self.height(x, z - e)
        return 2 * e / math.sqrt(hx * hx + hz * hz + 4 * e * e)

    def flat_spot(self, x, z, r=1.5):
        """Height spread under a disc (for checking a spot is level)."""
        hs = [self.height(x + r * math.cos(a), z + r * math.sin(a)) for a in (0, 1.57, 3.14, 4.71)]
        hs.append(self.height(x, z))
        return max(hs) - min(hs)

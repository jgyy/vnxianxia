"""Topology-driven head mesh: a structured quad grid with O-grid edge loops.

Topology
--------
* A global grid of rows x columns over the head chart (``face_chart``):
  88 columns (dense in front: 2.25 deg to 36 deg, 3.1 deg to 80 deg, then
  coarser toward the back) and 71 rows (neck, jaw blend, 1.8 deg through the
  face, coarser on the scalp).  Every row is a closed horizontal edge loop, so
  the jaw line, lip and brow rows run around the head.
* Rectangles of the grid around each eye, the mouth and each nostril are
  replaced by O-grids: concentric edge loops from the rectangle's border down
  to the opening.  The eye loops follow the lid margins (lash line, crease or
  pretarsal roll), the mouth loops follow the stomion, the vermilion and the
  white roll, then continue *into* the openings as the conjunctival tuck, the
  mouth vestibule / mouth bag and the nasal vestibules.  That gives the
  eye / mouth / nasolabial loop structure an animator expects.
* The crown is closed by a (cols/4)^2 quad patch (no pole).
* Everything is quads except the fans that close the mouth bag and nostrils.

Shape
-----
Grid vertices sit on the rays of the chart and are ray-cast onto the implicit
head (``face_surface``).  The lid rings are placed explicitly on the lid
ellipsoid (``face_eyes``) and the lip rings on the lip height field, then the
loops in between are cast and relaxed with a few Laplacian passes.

UV layout
---------
One texture for the head, neck and ears (slot ``face``); see ``face_uv`` for
the islands: a front-projected FACE island (Lambert azimuthal centred on the
face, the neck continuing below), a cylindrical SIDE island (lon 80..280 deg,
seam-free at the back), a CROWN island above b = 50 deg and two EAR boxes.
Mouth bag, nasal and conjunctival cavity faces use slot ``Mouth_Inner``.

The O-grid loops (vertex ids per loop, the loop parameter s of each radial
line: 0..1 around the opening) stay in ``HeadMesh.ogrids``; face_shapes
drives the lid and lip keys from them.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector

from . import face_chart as fc
from . import face_eyes, face_uv
from . import face_landmarks as fl
from . import face_surface as fs

# lid ring index -> (weight of the sculpted surface, extra weight at the canthi)
EYE_SURFACE_BLEND = {4: (0.0, 0.3), 5: (0.0, 0.6), 6: (0.15, 0.9), 7: (0.55, 1.0)}

SLOT_FACE = 0
SLOT_INNER = 1


# --------------------------------------------------------------------------
# chart sampling
# --------------------------------------------------------------------------
def _spans(parts):
    """[(start, end, steps), ...] -> sorted unique stations."""
    out = []
    for a, b, n in parts:
        out.extend(np.linspace(a, b, n + 1)[:-1].tolist())
    out.append(parts[-1][1])
    return np.array(out)


def columns():
    d = math.radians
    half = _spans([(0.0, d(12), 6), (d(12), d(36), 10), (d(36), d(80), 12), (d(80), d(115), 5), (d(115), d(180), 7)])
    # -180 .. 180 (exclusive): mirror the positive side
    neg = -half[1:-1][::-1]
    return np.concatenate([[-math.pi], neg, half[:-1]])


def rows():
    d = math.radians
    b_min = face_uv.B_MIN
    return _spans([(b_min, fc.B_NECK, 6), (fc.B_NECK, fc.B_HEAD, 4), (fc.B_HEAD, d(22), 48),
                   (d(22), face_uv.TOP, 7), (face_uv.TOP, d(68), 3)])


# --------------------------------------------------------------------------
# builder
# --------------------------------------------------------------------------
class Builder:
    def __init__(self):
        self.pos = []           # np.array(3) or None (to be cast)
        self.chart = []         # (lon, b) for cast vertices
        self.faces = []         # (verts, slot, group)
        self.groups = []        # (outward reference fn(centroid) -> vector, representative face index)
        self.group = self.new_group(lambda c: c)

    def new_group(self, ref):
        """Faces added after this share one winding, fixed by the first valid face against ref."""
        self.groups.append([ref, None])
        self.group = len(self.groups) - 1
        return self.group

    def mark_representative(self):
        """The next face added is used to decide the current group's winding."""
        self.groups[self.group][1] = len(self.faces)

    def vert(self, pos=None, chart=None):
        self.pos.append(None if pos is None else np.asarray(pos, np.float64))
        self.chart.append(chart)
        return len(self.pos) - 1

    def face(self, vs, slot=SLOT_FACE):
        self.faces.append((tuple(vs), slot, self.group))

    def fix_winding(self):
        """Flip whole groups whose representative face points against its outward reference."""
        flip = {}
        for g, (ref, rep) in enumerate(self.groups):
            cands = [rep] if rep is not None else [k for k, f in enumerate(self.faces) if f[2] == g][:50]
            for k in cands:
                P = [self.pos[v] for v in self.faces[k][0]]
                n = np.cross(P[1] - P[0], P[-1] - P[0])
                if np.linalg.norm(n) < 1e-8:
                    continue
                flip[g] = np.dot(n, ref(sum(P) / len(P))) < 0
                break
        self.faces = [(vs[::-1] if flip.get(g) else vs, slot, g) for vs, slot, g in self.faces]

    def cast_pending(self, surf, band_top=None, head_only=False):
        idx = [i for i, p in enumerate(self.pos) if p is None and (not head_only or self.chart[i][1] >= fc.B_HEAD)]
        if not idx:
            return
        ch = np.array([self.chart[i] for i in idx])
        pts, _ = fc.cast(surf.F, ch[:, 0], ch[:, 1], band_top)
        for k, i in enumerate(idx):
            self.pos[i] = pts[k]


def _nearest(arr, value):
    return int(np.argmin(np.abs(arr - value)))


def _perimeter(grid_idx, i0, i1, j0, j1, lateral_high):
    """Rectangle border of the grid as a closed loop starting on the 'lateral' side.

    lateral_high: True if the lateral / anchor side is the i1 column.  The loop
    runs up that side, across the top, down the other side, back along the
    bottom.  Returns the vertex list and the loop parameter s of each vertex
    (0 at the middle of the anchor side, 0.5 at the middle of the other)."""
    cols = list(range(i0, i1 + 1))
    if lateral_high:
        a, b = i1, i0
        top = cols[::-1]
        bottom = cols
    else:
        a, b = i0, i1
        top = cols
        bottom = cols[::-1]
    pts = []
    for j in range(j0, j1):                 # anchor side going up
        pts.append((a, j))
    for i in top[:-1]:
        pts.append((i, j1))
    for j in range(j1, j0, -1):             # other side going down
        pts.append((b, j))
    for i in bottom[:-1]:
        pts.append((i, j0))
    verts = [grid_idx[j][i] for i, j in pts]
    return verts, pts


def _smooth01(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _loop_params(uv, col):
    """Arc-length loop parameter with s = 0 at the anchor mid-side and 0.5 at the opposite mid-side.

    uv: (M, 2) points of the loop in a planar parameterisation, col: grid column
    of each point; the loop starts on the anchor column, runs up it, across the
    top, down the far column and back along the bottom."""
    M = len(uv)
    seg = np.linalg.norm(np.diff(np.vstack([uv, uv[:1]]), axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    ymid = 0.5 * (uv[:, 1].min() + uv[:, 1].max())
    col = np.asarray(col)
    first = np.nonzero(col == col[0])[0]
    far = np.nonzero(col == col[np.argmax(np.abs(col - col[0]))])[0]
    ya, yb = uv[first, 1], uv[far, 1]
    ca = np.interp(ymid, ya[np.argsort(ya)], cum[first][np.argsort(ya)])
    cb = np.interp(ymid, yb[np.argsort(yb)], cum[far][np.argsort(yb)])
    s = np.zeros(M)
    for k in range(M):
        c = cum[k]
        if ca <= c < cb:
            s[k] = 0.5 * (c - ca) / (cb - ca)
        else:
            cc = c if c >= cb else c + total
            s[k] = 0.5 + 0.5 * (cc - cb) / (ca + total - cb)
    return s % 1.0


def _chart_plane(lon, b):
    """Local planar chart coordinates (for arc lengths): (lon cos b, b)."""
    return np.stack([np.asarray(lon) * np.cos(np.asarray(b)), np.asarray(b)], axis=-1)


class HeadMesh:
    """Builds the head skin for FaceParams p.  Coordinates are head millimetres."""

    def __init__(self, p: fl.FaceParams):
        self.p = p
        self.surf = fs.HeadSurface(p)
        self.lids = {1: face_eyes.EyeLids(p, 1), -1: face_eyes.EyeLids(p, -1)}
        self.B = Builder()
        self.cols = columns()
        self.rows = rows()
        self.ogrids = []           # (kind, data) for later shape work
        self._build()

    # ------------------------------------------------------------------ layout
    def _rects(self, G):
        """Grid rectangles replaced by O-grids, chosen from the cast grid G (rows, cols, 3)."""
        cols = self.cols
        p = self.p
        L = fl.landmarks(p)
        front = np.nonzero(np.abs(cols) < math.radians(85))[0]

        def col_at(j, x):          # front column whose point on row j is nearest to x
            return int(front[np.argmin(np.abs(G[j, front, 0] - x))])

        def row_at(i, z):   # row whose point on column i is nearest to height z (head rows only)
            js = np.nonzero(self.rows >= fc.B_HEAD)[0]
            return int(js[np.argmin(np.abs(G[js, i, 2] - z))])

        mid = _nearest(cols, 0.0)

        def mirror(i):              # the columns are symmetric about the midline column
            return 2 * mid - i

        rect = {}
        # left-side rectangles are chosen on the surface; the right ones are their mirror images
        en, ex = L["endocanthion.L"], L["exocanthion.L"]
        c = fl.eye_geometry(p, 1)["centre"]
        ic = col_at(row_at(mid, c[2]), c[0])
        jr = row_at(ic, c[2])
        lid = self.lids[1].rings(np.linspace(0.0, 1.0, 97))[0][-1]
        i0 = max(col_at(jr, min(en[0] - 8.0, lid[:, 0].min() - 4.5)), mid + 2)
        i1 = col_at(jr, max(ex[0] + 7.5, lid[:, 0].max() + 6.0))
        # the rectangle must leave room for the blend loops beyond the outermost lid loop
        js = np.nonzero(self.rows >= fc.B_HEAD)[0]
        j0 = row_at(ic, min(c[2] - 14.5, lid[:, 2].min() - 4.0))
        top = max(c[2] + p.brow_gap - 3.0, lid[:, 2].max() + 4.0)
        j1 = int(js[np.nonzero(G[js, ic, 2] >= top)[0].min()]) if (G[js, ic, 2] >= top).any() else row_at(ic, top)
        rect["eye_L"] = (i0, i1, j0, j1, 1)
        rect["eye_R"] = (mirror(i1), mirror(i0), j0, j1, -1)
        jst = row_at(mid, L["stomion"][2])
        i1 = col_at(jst, p.mouth_w * 0.5 + 10.0)
        rect["mouth"] = (mirror(i1), i1, row_at(mid, L["labrale_inferius"][2] - 15.0),
                         row_at(mid, p.subnasale - 5.0), 1)
        d = np.linalg.norm(G - np.array(self.nostril_centre(1)), axis=-1)
        d[:, (cols < 0) | (cols > math.radians(40))] = 1e9
        jc, ic = np.unravel_index(np.argmin(d), d.shape)
        i0, i1 = max(ic - 1, mid + 1), ic + 2
        j0 = max(jc - 1, rect["mouth"][3] + 1)
        rect["nostril_L"] = (i0, i1, j0, j0 + 2, 1)
        rect["nostril_R"] = (mirror(i1), mirror(i0), j0, j0 + 2, -1)
        return rect

    def nostril_centre(self, side):
        p = self.p
        L = fl.landmarks(p)
        return (side * (p.alar_w * 0.5 - 9.2), L["pronasale"][1] + 8.4, p.subnasale + 1.0)

    # ------------------------------------------------------------------ build
    def _build(self):
        B = self.B
        cols, rws = self.cols, self.rows
        NC, NR = len(cols), len(rws)
        # cast the full grid: head rays first, the lowest head row then seeds the neck band
        LON, BB = np.meshgrid(cols, rws)
        head = BB >= fc.B_HEAD
        G = np.zeros((NR, NC, 3))
        G[head], _ = fc.cast(self.surf.F, LON[head], BB[head])
        jh = _nearest(rws, fc.B_HEAD)
        self.band_top = fc.band_top_from(cols, G[jh, :, 2])
        G[~head], _ = fc.cast(self.surf.F, LON[~head], BB[~head], self.band_top)
        rects = self._rects(G)
        self.rects = rects
        inside = np.zeros((NR, NC), bool)          # vertex removed
        cell_off = np.zeros((NR, NC), bool)        # cell (i, j) -> (i+1, j+1) removed
        for (i0, i1, j0, j1, _) in rects.values():
            inside[j0 + 1:j1, i0 + 1:i1] = True
            cell_off[j0:j1, i0:i1] = True
        grid = [[None] * NC for _ in range(NR)]
        for j in range(NR):
            for i in range(NC):
                if not inside[j, i]:
                    grid[j][i] = B.vert(pos=G[j, i])
                    B.chart[-1] = (cols[i], rws[j])
        self.grid = grid
        for j in range(NR - 1):
            for i in range(NC):
                if cell_off[j, i]:
                    continue
                i2 = (i + 1) % NC
                B.face((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
        B.new_group(lambda c: c)
        self._crown(grid[NR - 1])
        B.new_group(lambda c: c)
        B.cast_pending(self.surf, self.band_top)
        # the O-grids
        for side, sx in ((1, "L"), (-1, "R")):
            self._eye_ogrid(side, rects[f"eye_{sx}"])
        self._mouth_ogrid(rects["mouth"])
        for side, sx in ((1, "L"), (-1, "R")):
            self._nostril_ogrid(side, rects[f"nostril_{sx}"])
        B.cast_pending(self.surf, self.band_top)
        self._relax()
        B.fix_winding()

    def _crown(self, top_ring):
        """Close the top of the head with an n x n quad patch (Coons interpolation on the polar disc)."""
        B = self.B
        NC = len(top_ring)
        n = NC // 4
        b_top = self.rows[-1]
        # boundary walk of the (n+1) x (n+1) grid, matched to the ring in order
        walk = [(k, 0) for k in range(n)] + [(n, k) for k in range(n)] + \
               [(n - k, n) for k in range(n)] + [(0, n - k) for k in range(n)]
        # rotate so that the patch corners sit at +-45 deg around the head
        shift = NC // 8
        P = {}
        for k, (a, bq) in enumerate(walk):
            lon = self.cols[(k + shift) % NC]
            P[(a, bq)] = (np.array([math.sin(lon), -math.cos(lon)]), top_ring[(k + shift) % NC])
        idx = {key: v for key, (_, v) in P.items()}
        for a in range(1, n):
            for bq in range(1, n):
                s_, t_ = a / n, bq / n
                pt = ((1 - t_) * P[(a, 0)][0] + t_ * P[(a, n)][0] + (1 - s_) * P[(0, bq)][0] + s_ * P[(n, bq)][0]
                      - ((1 - s_) * (1 - t_) * P[(0, 0)][0] + s_ * (1 - t_) * P[(n, 0)][0]
                         + (1 - s_) * t_ * P[(0, n)][0] + s_ * t_ * P[(n, n)][0]))
                rho = min(np.linalg.norm(pt), 0.999)
                lon = math.atan2(pt[0], -pt[1])
                b = b_top + (math.pi / 2 - b_top) * (1 - rho) ** 0.9
                idx[(a, bq)] = B.vert(chart=(lon, b))
        for a in range(n):
            for bq in range(n):
                B.face((idx[(a, bq)], idx[(a, bq + 1)], idx[(a + 1, bq + 1)], idx[(a + 1, bq)]))

    # ------------------------------------------------------------------ O-grid helpers
    def _perimeter(self, rect):
        i0, i1, j0, j1, side = rect
        verts, ij = _perimeter(self.grid, i0, i1, j0, j1, lateral_high=side > 0)
        ch = np.array([(self.cols[i], self.rows[j]) for i, j in ij])
        plane = _chart_plane(ch[:, 0] * (1 if side > 0 else -1), ch[:, 1])
        return verts, _loop_params(plane, [i for i, _ in ij]), ch

    def _connect(self, ring_list, slots, ref_out, rep_band, fan_centre=None):
        """Quads between consecutive loops (inner -> outer) in one winding group.

        The group's winding is decided on band rep_band (a band on the visible
        surface) against ref_out(centroid).  fan_centre closes the innermost
        loop with triangles."""
        B = self.B
        B.new_group(ref_out)
        M = len(ring_list[0])
        for k in range(len(ring_list) - 1):
            a, b = ring_list[k], ring_list[k + 1]
            for m in range(M):
                if k == rep_band and m == M // 4:
                    B.mark_representative()
                m2 = (m + 1) % M
                B.face((a[m], a[m2], b[m2], b[m]), slots[k])
        if fan_centre is not None:
            inner = ring_list[0]
            for m in range(M):
                B.face((inner[m], fan_centre, inner[(m + 1) % M]), SLOT_INNER)
        B.new_group(lambda c: c)

    # ------------------------------------------------------------------ eyes
    def eye_rings(self, side, s, state=None):
        """Explicit lid loops for loop params s; the outer ones ease onto the sculpted
        surface so the lids have no rim (fully so toward the canthi)."""
        rings, _ = self.lids[side].rings(s, state)
        corner = np.exp(-((np.minimum(s, 1 - s) / 0.07) ** 2)) + np.exp(-(((s - 0.5) / 0.07) ** 2))
        for k, (wgt, wc) in EYE_SURFACE_BLEND.items():
            r = rings[k]
            fy = self.surf.front_y(r[:, 0], r[:, 2])
            wk = 1 - (1 - wgt) * (1 - wc * corner)
            # a lid ring that has slipped deep under the sculpted surface (past the globe the lid
            # ellipsoid falls away faster than the orbit rim) is eased up to it, or the next
            # blend ring would have to step forward by several mm (a visible box around the eye)
            wk = np.maximum(wk, _smooth01((r[:, 1] - fy - 1.0) / 4.0) * min(1.0, (k - 3) / 3.0))
            rings[k] = np.stack([r[:, 0], r[:, 1] + (fy - r[:, 1]) * wk, r[:, 2]], axis=-1)
        return rings

    def _eye_ogrid(self, side, rect):
        B = self.B
        per, s, per_chart = self._perimeter(rect)
        rings = self.eye_rings(side, s)
        n_exp = len(rings)
        ring_ids = []
        for pts in rings:
            ring_ids.append([B.vert(pos=q) for q in pts])
        # blend loops: chart interpolation from the last lid loop to the rectangle
        last = rings[-1]
        lon_e, b_e = fc.chart_of_points(last)
        n_blend = 3
        for k in range(1, n_blend + 1):
            f = (k / (n_blend + 1)) ** 1.15
            lon = lon_e + (per_chart[:, 0] - lon_e) * f
            b = b_e + (per_chart[:, 1] - b_e) * f
            ring_ids.append([B.vert(chart=(lon[m], b[m])) for m in range(len(s))])
        ring_ids.append(per)
        slots = [SLOT_INNER] + [SLOT_FACE] * (len(ring_ids) - 2)
        c = np.array(fl.eye_geometry(self.p, side)["centre"])
        self._connect(ring_ids, slots, lambda cen: cen - c, face_eyes.EyeLids.LASH_RING)
        self.ogrids.append(("eye", dict(side=side, rings=ring_ids, s=s, n_exp=n_exp)))

    # ------------------------------------------------------------------ mouth
    def mouth_loops(self, s, state=None):
        """Explicit mouth loops (inner cavity -> white roll) for loop params s.

        s = 0 at the left mouth corner, 0..0.5 along the upper lip, 0.5 the right
        corner, 0.5..1 the lower lip.  Returns [(M, 3) arrays], index of the
        contact loop, upperness."""
        p = self.p
        S = self.surf
        xc = p.mouth_w * 0.5
        x = xc * np.cos(2 * math.pi * s)
        upper = (np.sin(2 * math.pi * s) > 1e-9).astype(np.float64)       # both corners count as lower
        corner = np.exp(-((np.minimum(np.abs(s), np.abs(1 - s)) / 0.05) ** 2)) + \
            np.exp(-(((s - 0.5) / 0.05) ** 2))
        sgn = np.where(upper > 0, 1.0, -1.0)
        st, up, lo = S.lips_at(x)
        edge = np.where(upper > 0, up, lo)          # vermilion border for this half
        height = np.abs(edge - st)
        loops = []
        # cavity: (inset toward the midline, z opening, depth behind the contact)
        for shrink, dz, dy in ((0.52, 6.5, 26.0), (0.72, 8.0, 15.0), (0.86, 5.5, 8.0), (0.95, 2.6, 4.2),
                               (0.99, 0.9, 1.9)):
            y0 = S.front_y(x, st)
            loops.append(np.stack([x * shrink, y0 + dy, st + sgn * dz * (1 - 0.7 * corner)], axis=-1))
        contact = len(loops)
        y0 = S.front_y(x, st)
        loops.append(np.stack([x, y0 + 0.35, st + sgn * 0.1], axis=-1))
        # vermilion loops, then the white roll just outside the border and the skin beyond
        for f, dmin in ((0.22, 0.3), (0.5, 0.6), (0.8, 0.9), (1.0, 1.15), (None, 1.6), (None, 2.6)):
            if f is not None:
                dz = np.maximum(height * f, dmin)
            else:
                dz = height + dmin - 0.6
            zz = st + sgn * dz * (1 - corner) + sgn * dmin * 0.3 * corner
            xx = x + np.sign(x) * dmin * corner * 1.4
            loops.append(np.stack([xx, S.front_y(xx, zz), zz], axis=-1))
        return loops, contact, upper

    def _mouth_ogrid(self, rect):
        B = self.B
        per, s, per_chart = self._perimeter(rect)
        loops, contact, upper = self.mouth_loops(s)
        ring_ids = []
        for pts in loops:
            ring_ids.append([B.vert(pos=q) for q in pts])
        lon_e, b_e = fc.chart_of_points(loops[-1])
        n_blend = 3
        for k in range(1, n_blend + 1):
            f = (k / (n_blend + 1)) ** 1.1
            lon = lon_e + (per_chart[:, 0] - lon_e) * f
            b = b_e + (per_chart[:, 1] - b_e) * f
            ring_ids.append([B.vert(chart=(lon[m], b[m])) for m in range(len(s))])
        ring_ids.append(per)
        # close the mouth bag with a fan
        inner = ring_ids[0]
        cen = np.mean([B.pos[v] for v in inner], axis=0) + np.array([0.0, 4.0, 0.0])
        cv = B.vert(pos=cen)
        slots = [SLOT_INNER] * contact + [SLOT_FACE] * (len(ring_ids) - 1 - contact)
        self._connect(ring_ids, slots, lambda c: np.array([0.0, -1.0, 0.0]), contact + 2, fan_centre=cv)
        self.ogrids.append(("mouth", dict(rings=ring_ids, s=s, contact=contact, upper=upper, centre=cv,
                                          n_exp=len(loops))))

    # ------------------------------------------------------------------ nostrils
    def _nostril_ogrid(self, side, rect):
        B = self.B
        per, s, _ = self._perimeter(rect)
        c = np.array(self.nostril_centre(side))
        # the opening: an oblique ellipse in the (x, y) plane of the nose underside
        ang = 2 * math.pi * s
        rl, rw = 3.5, 1.9
        rot = math.radians(22.0)          # the front of each nostril converges toward the columella
        ex = rw * np.cos(ang)
        ey = -rl * np.sin(ang)
        px = c[0] + side * (ex * math.cos(rot) - ey * math.sin(rot))
        py = c[1] + ex * math.sin(rot) + ey * math.cos(rot)
        pts = np.stack([px, py, np.full_like(px, c[2])], axis=-1)
        lon_c, b_c = fc.chart_of_points(pts)
        opening = [B.vert(chart=(lon_c[m], b_c[m])) for m in range(len(s))]
        B.cast_pending(self.surf, self.band_top)
        op = np.array([B.pos[v] for v in opening])
        cen = op.mean(axis=0)
        tunnel = []
        for sh, up, back in ((0.55, 7.0, 3.5), (0.8, 3.0, 1.0)):
            tunnel.append([B.vert(pos=cen + (op[m] - cen) * sh + np.array([0, back, up])) for m in range(len(s))])
        ring_ids = tunnel + [opening]
        # blend loops: straight 3-D interpolation to the rectangle, pulled onto the surface
        # along its gradient (rays from the head centre graze the nose underside, so chart
        # interpolation there lands points out of order and the loops fold over)
        pp = np.array([B.pos[v] for v in per])
        for f in (0.36, 0.68):
            q = self.surf.project(op + (pp - op) * f)
            ring_ids.append([B.vert(pos=q[m]) for m in range(len(s))])
        ring_ids.append(per)
        cv = B.vert(pos=cen + np.array([0, 5.0, 10.0]))
        slots = [SLOT_INNER, SLOT_FACE] + [SLOT_FACE] * (len(ring_ids) - 3)
        B.cast_pending(self.surf, self.band_top)
        self._connect(ring_ids, slots, lambda cc: np.array([0.0, -0.3, -1.0]), 2, fan_centre=cv)
        self.ogrids.append(("nostril", dict(side=side, rings=ring_ids, s=s, n_exp=3)))

    # ------------------------------------------------------------------ relaxation
    def _relax(self, iters=4):
        """Laplacian smoothing of the blend loops of every O-grid, re-projected onto the
        sculpted surface after each pass (smoothing alone pulls them inside it)."""
        B = self.B
        for kind, d in self.ogrids:
            rings = d["rings"]
            first = d["n_exp"]
            movable = rings[first:-1]
            for _ in range(iters):
                new = {}
                for r, ring in enumerate(movable):
                    k = first + r
                    M = len(ring)
                    for m in range(M):
                        nb = [B.pos[rings[k - 1][m]], B.pos[rings[k + 1][m]],
                              B.pos[ring[(m - 1) % M]], B.pos[ring[(m + 1) % M]]]
                        new[ring[m]] = 0.5 * B.pos[ring[m]] + 0.5 * (sum(nb) / 4.0)
                ids = list(new)
                proj = self.surf.project(np.array([new[v] for v in ids]))
                for v, q in zip(ids, proj):
                    B.pos[v] = q

    # ------------------------------------------------------------------ output
    def to_bmesh(self, scale, centre):
        """bmesh in world units: world = centre + pos_mm * 0.001 * scale; with UVs and fx attributes."""
        B = self.B
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.verify()
        pos = np.array(B.pos)
        # chart per vertex for UVs
        charts = np.zeros((len(pos), 2))
        for i, ch in enumerate(B.chart):
            if ch is not None:
                charts[i] = ch
        free = [i for i, ch in enumerate(B.chart) if ch is None]
        if free:
            lon, b = fc.chart_of_points(pos[free])
            charts[free, 0] = lon
            charts[free, 1] = b
        vs = []
        k = 0.001 * scale
        for i, q in enumerate(pos):
            vs.append(bm.verts.new(Vector(centre) + Vector(q) * k))
        bm.verts.ensure_lookup_table()
        for verts, slot, _ in B.faces:
            if len(set(verts)) < len(verts):
                continue
            try:
                f = bm.faces.new([vs[i] for i in verts])
            except ValueError:
                continue
            f.material_index = slot
            ch = charts[list(verts)]
            lon = ch[:, 0].copy()
            if lon.max() - lon.min() > math.pi:          # the face straddles the back seam
                lon = np.where(lon < 0, lon + 2 * math.pi, lon)
            isl = int(face_uv.island_of(np.array([lon.mean()]), np.array([ch[:, 1].mean()]))[0])
            if isl == 0 and np.any(np.abs(lon) > face_uv.SEAM + 1e-6):
                isl = 1
            u, v = face_uv.uv_from_lonb(lon, ch[:, 1], np.full(len(lon), isl))
            for lp, uu, vv in zip(f.loops, u, v):
                lp[uvl].uv = (uu, vv)
        return bm

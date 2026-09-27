"""Eyes: eyelid geometry (used by face_mesh for the lid edge loops) and the eyeball parts.

Eye-local frontal coordinates (u, w) in mm: u = lateral distance from the
eyeball centre (+ toward the ear, mirrored for the right eye), w = height above
the eyeball centre.  The lids lie on a "lid ellipsoid": the eyeball sphere
stretched medially over the caruncle and a little laterally past the equator,
so the lid margins wrap the globe with no gap and the canthi sit where the
fissure measurements put them.

A lid *state* dict drives every eye shape key by re-running the same geometry:
``close`` (blink), ``squint``, ``look`` (-1 down .. +1 up, lids follow gaze),
``wide``.  Missing keys default to 0.

Eyeball parts (all weighted to the eye.L / eye.R bones by face_rig):
* sclera sphere with the corneal window cut out (slot Eye_Sclera, azimuthal
  UV centred on the visual axis: uv = 0.5 + 0.5 * (angle / 90 deg) * (cos, sin));
* iris: a shallow cone from the limbus to the pupil with radial fibre ridges
  and a limbal groove (slot Eye_Iris, planar polar UV: the limbus is the circle
  of radius 0.5 around (0.5, 0.5), the pupil edge sits at radius 0.5 * PUPIL / LIMBUS);
* cornea: a transparent wet shell - the 7.8 mm corneal cap blended into a thin
  film over the sclera (slot Eye_Cornea);
* tear line: a strip along the lower lid margin meniscus (slot Eye_Tearline);
* caruncle: the pink mound in the medial canthus (slot Mouth_Inner).
"""
import math

import numpy as np
from mathutils import Vector

from . import face_landmarks as fl

LIMBUS = 6.1          # corneal radius at the limbus, mm (12.2 mm iris: large, youthful)
PUPIL = 1.9           # resting pupil radius, mm
CORNEA_R = 7.8        # corneal radius of curvature, mm


def _sstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class EyeLids:
    """Lid margin curves and lid surface rings for one eye (side +1 = left)."""

    def __init__(self, p: fl.FaceParams, side):
        self.p = p
        self.side = side
        g = fl.eye_geometry(p, side)
        self.c = np.array(g["centre"], np.float64)
        self.R = g["R"]
        en, ex = g["en"], g["ex"]
        self.u_en = -abs(en[0] - self.c[0])
        self.u_ex = abs(ex[0] - self.c[0])
        self.w_en = en[2] - self.c[2]
        self.w_ex = ex[2] - self.c[2]
        self.a_med = abs(self.u_en) / 0.93
        self.a_lat = self.R * 1.03       # past the equator the lateral lids fold back around the globe
        pupil_w = g["apex"][2] - self.c[2]
        self.t_pupil = -self.u_en / (self.u_ex - self.u_en)
        w0p = self.w_en + (self.w_ex - self.w_en) * self.t_pupil
        self.au, self.bu = math.log(0.5) / math.log(0.44), 0.78      # upper peak slightly medial
        self.al, self.bl = math.log(0.5) / math.log(0.56), 0.9       # lower lowest point lateral
        self.Hu = (pupil_w + 0.47 * p.pfh - w0p) / self._fu(self.t_pupil)
        self.Hl = (w0p - (pupil_w - 0.53 * p.pfh)) / self._fl(self.t_pupil)

    # ------------------------------------------------------------------ margins
    def _fu(self, t):
        return np.sin(math.pi * np.clip(t, 0, 1) ** self.au) ** self.bu

    def _fl(self, t):
        return np.sin(math.pi * np.clip(t, 0, 1) ** self.al) ** self.bl

    def margins(self, t, state=None):
        """(u, w_upper, w_lower) along the fissure, t = 0 medial .. 1 lateral."""
        st = state or {}
        p = self.p
        t = np.asarray(t, np.float64)
        u = self.u_en + (self.u_ex - self.u_en) * t
        w0 = self.w_en + (self.w_ex - self.w_en) * t
        wu = w0 + self.Hu * self._fu(t)
        wl = w0 - self.Hl * self._fl(t)
        # epicanthal fold: the upper lid's medial end sweeps down over the canthus
        wu -= p.epicanthus * 1.3 * (1 - _sstep(0.0, 0.3, t)) * self._fu(t) / max(self._fu(0.3), 1e-6)
        # age: the lateral third of the upper lid droops
        wu -= p.hood * 0.9 * _sstep(0.5, 0.95, t) * self._fu(t)
        look = st.get("look", 0.0)
        span = self._fu(t)
        wu += np.where(look > 0, 2.3, 3.2) * look * span
        wl += np.where(look > 0, 1.0, 1.5) * look * self._fl(t)
        wide = st.get("wide", 0.0)
        wu += 1.4 * wide * span
        wl -= 0.6 * wide * self._fl(t)
        sq = st.get("squint", 0.0)
        gap = wu - wl
        wl += sq * 0.32 * gap
        wu -= sq * 0.12 * gap
        close = st.get("close", 0.0)
        if close:
            line = wl + 0.24 * (wu - wl)
            k = close
            wu = wu + (line + 0.06 - wu) * k
            wl = wl + (line - 0.06 - wl) * min(1.0, k * 1.2)
        return u, wu, wl

    def lid_y(self, u, w, th):
        """Depth of the lid surface at frontal (u, w) for thickness th above the globe."""
        R = self.R
        # the conjunctival tuck (th < 0) hugs the true globe; the lids ride on the lid ellipsoid
        a = np.where(th < 0, R, np.where(u < 0, self.a_med, self.a_lat))
        q = (1.0 + th / R) ** 2 - (u / a) ** 2 - (w / R) ** 2
        # past the lid ellipsoid's rim the surface folds back behind the globe (a few mm at most)
        return self.c[1] - R * np.sqrt(np.clip(q, 0.0, None)) + np.minimum(3.0 * R * np.clip(-q, 0.0, None), 5.0)

    def to_head(self, u, w, y):
        """Eye-local frontal coordinates -> head mm."""
        x = self.c[0] + self.side * np.asarray(u)
        z = self.c[2] + np.asarray(w)
        return np.stack([x, np.asarray(y) + 0 * x, z], axis=-1)

    # ------------------------------------------------------------------ the opening loop
    def loop(self, s, state=None, dense=240):
        """Opening contour sampled at loop parameters s in [0, 1).

        s = 0 lateral canthus, 0..0.5 along the upper margin to the medial
        canthus (s = 0.5), 0.5..1 along the lower margin back.  Returns
        (u, w, upperness, outward normal (nu, nw))."""
        s = np.asarray(s, np.float64) % 1.0
        uu, ww = self._pt(s, state, dense)
        upper = _sstep(0.035, 0.1, s) * _sstep(0.5 - 0.035, 0.5 - 0.1, s)
        # outward normals from the parametric neighbours (loop runs CCW in (u, w))
        eps = 1e-3
        pu, pw = self._pt(s + eps, state, dense)
        mu, mw = self._pt(s - eps, state, dense)
        tu, tw = pu - mu, pw - mw
        nrm = np.hypot(tu, tw) + 1e-12
        nu, nw = tw / nrm, -tu / nrm
        # at the canthi the outward direction is horizontal
        lat = np.exp(-((np.minimum(s, 1 - s) / 0.03) ** 2))
        med = np.exp(-(((s - 0.5) / 0.03) ** 2))
        nu = nu * (1 - lat - med) + lat - med
        nw = nw * (1 - lat - med)
        nn = np.hypot(nu, nw) + 1e-12
        return uu, ww, upper, (nu / nn, nw / nn)

    def _pt(self, s, state, dense):
        t = np.linspace(0.0, 1.0, dense)
        u, wu, wl = self.margins(t, state)
        up = np.stack([u[::-1], wu[::-1]], axis=-1)
        lo = np.stack([u, wl], axis=-1)
        s = np.asarray(s, np.float64) % 1.0
        res_u = np.zeros_like(s)
        res_w = np.zeros_like(s)
        for poly, lo_s, hi_s in ((up, 0.0, 0.5), (lo, 0.5, 1.0)):
            seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
            cum = np.concatenate([[0.0], np.cumsum(seg)]) / max(seg.sum(), 1e-9)
            m = (s >= lo_s) & (s < hi_s)
            q = (s[m] - lo_s) * 2.0
            res_u[m] = np.interp(q, cum, poly[:, 0])
            res_w[m] = np.interp(q, cum, poly[:, 1])
        return res_u, res_w

    # ------------------------------------------------------------------ rings
    def ring_table(self, s, upper):
        """Per explicit ring: (offset along the outward normal, thickness) arrays.

        Index 0, 1 are hidden conjunctival tuck rings behind the margin, 2 is
        the posterior lid margin (the opening), 3 the lash line, then the
        pretarsal skin, the crease fold (upper) / aegyo-sal roll (lower)."""
        p = self.p
        # t along the fissure for crease tapering (s -> 0 lateral, 0.5 medial)
        t_fis = np.where(s < 0.5, 1.0 - 2.0 * s, 2.0 * (s - 0.5))
        if p.crease == "inout":
            ch = p.crease_h * (0.25 + 0.75 * _sstep(0.05, 0.5, t_fis))
        else:
            ch = p.crease_h * (0.8 + 0.2 * _sstep(0.05, 0.4, t_fis))
        a = p.aegyo * _sstep(0.08, 0.35, t_fis) * _sstep(1.0, 0.8, t_fis)
        hood = p.hood * _sstep(0.4, 0.9, t_fis)
        if p.crease == "none":
            U = [(1.8, -1.7), (0.35, -0.25), (0.0, 0.15), (0.3, 1.55), (1.1, 1.8),
                 (2.4, 2.1 + 0.4 * hood), (3.8, 2.5 + 0.6 * hood), (5.0, 2.9 + 0.5 * hood)]
        else:
            U = [(1.8, -1.7), (0.35, -0.25), (0.0, 0.15), (0.3, 1.55), (0.45 * ch + 0.55, 1.72),
                 (ch + 0.9 - 0.5 * hood, 1.8), (ch + 1.15 - 0.4 * hood, 1.4 + 0.2 * hood),
                 (ch + 2.3 - 1.0 * hood, 2.85 + 1.0 * hood)]
        Lw = [(1.8, -1.7), (0.35, -0.25), (0.0, 0.15), (0.25, 1.05), (1.15, 1.72 + 0.55 * a),
              (2.5, 2.1 + 1.25 * a), (3.9, 1.95 + 0.8 * a), (5.1, 1.75 + 0.1 * p.tear_trough)]
        out = []
        for (du, tu), (dl, tl) in zip(U, Lw):
            du = np.broadcast_to(du, s.shape)
            dl = np.broadcast_to(dl, s.shape)
            tu = np.broadcast_to(tu, s.shape)
            tl = np.broadcast_to(tl, s.shape)
            out.append((du * upper + dl * (1 - upper), tu * upper + tl * (1 - upper)))
        return out

    MARGIN_RING = 2     # index of the posterior margin (the opening) in ring_table
    LASH_RING = 3

    def rings(self, s, state=None):
        """Explicit rings as head-mm points: list of (M, 3) arrays, plus (u, w) of the margin."""
        u, w, upper, (nu, nw) = self.loop(s, state)
        rings = []
        for off, th in self.ring_table(np.asarray(s, np.float64) % 1.0, upper):
            ru = u + nu * off
            rw = w + nw * off
            rings.append(self.to_head(ru, rw, self.lid_y(ru, rw, th)))
        return rings, upper


# --------------------------------------------------------------------------
# eyeball meshes (built in head mm, converted by the caller's transform)
# --------------------------------------------------------------------------
def _frame(axis):
    f = Vector(axis).normalized()
    up = Vector((0, 0, 1))
    r = f.cross(up).normalized()
    u = r.cross(f).normalized()
    return f, r, u


def eyeball(bm, centre, R, fwd=(0.0, -1.0, 0.0), segs=32, rings=10, uv=None, mats=(0, 1, 2)):
    """Sclera (slot mats[0]) + iris (mats[1]) + cornea shell (mats[2]) into bm (head mm)."""
    c = Vector(centre)
    f, r, u = _frame(fwd)
    uvl = uv or bm.loops.layers.uv.verify()
    lim_ang = math.asin(LIMBUS / R)                   # angular radius of the limbus
    # ---- sclera: polar rings from just outside the limbus to 130 deg (the rest sits
    # deep in the orbit behind the lids and is never seen)
    back = math.radians(130.0)
    angs = [lim_ang + (back - lim_ang) * (k / rings) ** 1.2 for k in range(rings + 1)]
    grid = []
    for a in angs:
        row = []
        for i in range(segs):
            ph = 2 * math.pi * i / segs
            d = f * math.cos(a) + (r * math.cos(ph) + u * math.sin(ph)) * math.sin(a)
            row.append(bm.verts.new(c + d * R))
        grid.append(row)
    for j in range(rings):
        for i in range(segs):
            i2 = (i + 1) % segs
            fa = bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i2], grid[j][i2]))
            fa.material_index = mats[0]
            for lp, (jj, ii) in zip(fa.loops, ((j, i), (j + 1, i), (j + 1, i2 if i2 else segs), (j, i2 if i2 else segs))):
                rr = 0.5 * angs[jj] / (0.5 * math.pi)
                ph = 2 * math.pi * ii / segs
                lp[uvl].uv = (0.5 + rr * math.cos(ph), 0.5 + rr * math.sin(ph))
    # ---- iris: from the limbus (slightly inside the sclera) to the pupil, a shallow cone
    depth0 = R * math.cos(lim_ang) - 0.25               # the iris sits ~0.6 mm behind the limbus plane
    iris_rings = 7
    irows = []
    for k in range(iris_rings + 1):
        t = k / iris_rings
        rad = LIMBUS * (1 - t) + PUPIL * t
        rad = LIMBUS - 0.02 if k == 0 else rad
        dome = 0.35 * math.sin(math.pi * t) + 0.1 * t    # the pupillary zone bulges forward slightly
        groove = -0.18 if k == 1 else 0.0                # limbal groove just inside the edge
        row = []
        for i in range(segs):
            ph = 2 * math.pi * i / segs
            fib = 0.035 * math.sin(ph * 8 + 3 * t) * math.sin(math.pi * t)    # radial fibre ridges
            d = f * (depth0 + dome + groove + fib) + (r * math.cos(ph) + u * math.sin(ph)) * rad
            row.append(bm.verts.new(c + d))
        irows.append(row)
    # the pupil: a short tunnel then a dark cap
    back = []
    for i in range(segs):
        ph = 2 * math.pi * i / segs
        d = f * (depth0 - 0.4) + (r * math.cos(ph) + u * math.sin(ph)) * PUPIL * 0.92
        back.append(bm.verts.new(c + d))
    irows.append(back)
    for j in range(len(irows) - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            fa = bm.faces.new((irows[j][i], irows[j][i2], irows[j + 1][i2], irows[j + 1][i]))
            fa.material_index = mats[1]
            for lp in fa.loops:
                q = lp.vert.co - c
                x, y = q.dot(r), q.dot(u)
                rr = min(math.hypot(x, y), LIMBUS) / LIMBUS * 0.5
                ph = math.atan2(y, x)
                lp[uvl].uv = (0.5 + rr * math.cos(ph), 0.5 + rr * math.sin(ph))
    cap = bm.faces.new(list(reversed(back)))
    cap.material_index = mats[1]
    for lp in cap.loops:
        lp[uvl].uv = (0.5, 0.5)
    # close the gap between the sclera window and the iris edge (the limbus wall)
    for i in range(segs):
        i2 = (i + 1) % segs
        fa = bm.faces.new((grid[0][i], grid[0][i2], irows[0][i2], irows[0][i]))
        fa.material_index = mats[0]
        for lp, ii in zip(fa.loops, (i, i2 or segs, i2 or segs, i)):
            ph = 2 * math.pi * ii / segs
            rr = 0.5 * lim_ang / (0.5 * math.pi)
            lp[uvl].uv = (0.5 + rr * math.cos(ph), 0.5 + rr * math.sin(ph))
    # ---- cornea: a corneal cap blended into a thin tear film over the front of the sclera
    cz = R * math.cos(lim_ang) - math.sqrt(CORNEA_R ** 2 - LIMBUS ** 2)
    film = R + 0.06
    crow = []
    n_c = 10
    for k in range(n_c + 1):
        a = (lim_ang + math.radians(68)) * (k / n_c) ** 1.1     # angle from the visual axis
        # radius along direction a from the eye centre: corneal sphere inside the limbus, film outside
        dx, dz = math.sin(a), math.cos(a)
        disc = (dz * cz) ** 2 - (cz * cz - CORNEA_R ** 2)
        rc = dz * cz + math.sqrt(max(disc, 0.0))
        w = _sstep(lim_ang - 0.06, lim_ang + 0.1, a)
        rad = rc * (1 - w) + film * w
        row = []
        for i in range(segs):
            ph = 2 * math.pi * i / segs
            d = f * dz + (r * math.cos(ph) + u * math.sin(ph)) * dx
            row.append(bm.verts.new(c + d * rad))
        crow.append(row)
    tipv = bm.verts.new(c + f * (cz + CORNEA_R))
    for j in range(n_c):
        for i in range(segs):
            i2 = (i + 1) % segs
            fa = bm.faces.new((crow[j][i], crow[j + 1][i], crow[j + 1][i2], crow[j][i2]))
            fa.material_index = mats[2]
    for i in range(segs):
        i2 = (i + 1) % segs
        fa = bm.faces.new((tipv, crow[0][i], crow[0][i2]))
        fa.material_index = mats[2]
    for fa in bm.faces:
        if fa.material_index == mats[2]:
            for lp in fa.loops:
                q = lp.vert.co - c
                lp[uvl].uv = (0.5 + q.dot(r) / (2 * R), 0.5 + q.dot(u) / (2 * R))


def caruncle(bm, lids: EyeLids, mat_index, uv=None):
    """The caruncle / plica: a small wet mound filling the medial canthus behind the lids."""
    uvl = uv or bm.loops.layers.uv.verify()
    u_c = lids.u_en * 0.82
    _, wu, wl = lids.margins(np.array([0.06]))
    w_c = float(wu[0] + wl[0]) * 0.5
    y_c = float(lids.lid_y(np.array([u_c]), np.array([w_c]), -0.9)[0])
    ctr = lids.to_head(np.array([u_c]), np.array([w_c]), np.array([y_c]))[0]
    rad = (2.3, 2.6, 1.6)      # lateral, vertical, depth
    n, m = 12, 7
    rows = []
    for j in range(m + 1):
        th = math.pi * j / m
        row = []
        for i in range(n):
            ph = 2 * math.pi * i / n
            x = math.sin(th) * math.cos(ph) * rad[0]
            z = math.sin(th) * math.sin(ph) * rad[1]
            y = -math.cos(th) * rad[2]
            row.append(bm.verts.new(Vector((ctr[0] + lids.side * x, ctr[1] + y, ctr[2] + z))))
        rows.append(row)
    for j in range(m):
        for i in range(n):
            i2 = (i + 1) % n
            fa = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            fa.material_index = mat_index
            for lp in fa.loops:
                lp[uvl].uv = (0.5, 0.5)
    return ctr


TEAR_N = 36


def tearline_points(lids: EyeLids, state=None):
    """Wet meniscus strips along the lower lid margin (and a thinner one under the upper lid).

    Returns (verts (N, 3) head mm, faces, uvs); a pure function of the lid state."""
    verts, faces, uvs = [], [], []
    M = TEAR_N
    for lo_s, hi_s, width in ((0.53, 0.985, 0.75), (0.03, 0.47, 0.35)):
        s = np.linspace(lo_s, hi_s, M)
        u, w, _, (nu, nw) = lids.loop(s, state)
        taper = np.sin(np.pi * np.arange(M) / (M - 1)) ** 0.5
        ua, wa = u + nu * 0.12, w + nw * 0.12
        ub, wb = u - nu * width * taper, w - nw * width * taper
        pa = lids.to_head(ua, wa, lids.lid_y(ua, wa, 0.35))
        pb = lids.to_head(ub, wb, lids.lid_y(ub, wb, 0.07))
        b = len(verts)
        for k in range(M):
            verts += [pa[k], pb[k]]
            uvs += [(k / (M - 1), 1.0), (k / (M - 1), 0.0)]
        for k in range(M - 1):
            faces.append((b + 2 * k, b + 2 * k + 1, b + 2 * k + 3, b + 2 * k + 2))
    return np.array(verts), faces, uvs

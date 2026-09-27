"""The sculpted head as an implicit surface (numpy, head millimetres).

``HeadSurface(p).F(X, Y, Z)`` is negative inside the head+neck and positive
outside.  It is built like a sculptor blocks a head:

* cranium: an egg-shaped ellipsoid (flatter occiput, rounder forehead);
* face mass: a front height field ``front_y(x, z)`` (the soft-tissue profile
  and its lateral curvature, row by row) bounded by the side planes of the
  cheeks / ramus and by the inclined mandibular plane underneath (so the jaw
  line, the V-line taper and the gonial angle come from a few parameters);
* the neck: an elliptic column with sternocleidomastoids and a laryngeal
  prominence, blended into the skull base and under the jaw with a smooth
  union whose radius (``jaw_soft``) is small for a crisp young jaw line and
  large for an old one;
* features: the nose (dorsum, tip lobule, alae with an alar crease, columella),
  lips (Cupid's bow, vermilion with a white roll, philtral columns), chin pad,
  eye domes inside orbits, brow ridge, malar fat pads, nasolabial and
  marionette folds, jowls, tear trough and temples - each a height-field term
  or a smooth min/max against the base, so creases stay crisp.

Only the zero set matters (``face_mesh`` ray-casts it), so the pieces are
"distance-like" rather than exact distances.
"""
import numpy as np

from . import face_landmarks as fl


# --------------------------------------------------------------------------
# small numeric helpers
# --------------------------------------------------------------------------
def smin(a, b, k):
    """Polynomial smooth minimum (union) with blend radius k."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def gauss(x, z, cx, cz, sx, sz):
    return np.exp(-(((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))


class Curve:
    """Monotone cubic (Fritsch-Carlson) interpolation through (t, v) stations; clamps outside."""

    def __init__(self, pts):
        pts = sorted(pts)
        self.t = np.array([a for a, _ in pts], np.float64)
        self.v = np.array([b for _, b in pts], np.float64)
        d = np.diff(self.v) / np.diff(self.t)
        m = np.zeros_like(self.v)
        m[1:-1] = np.where(d[:-1] * d[1:] > 0, 2.0 / (1.0 / np.where(d[:-1] == 0, 1e-9, d[:-1]) +
                                                    1.0 / np.where(d[1:] == 0, 1e-9, d[1:])), 0.0)
        m[0], m[-1] = d[0], d[-1]
        self.m = m

    def __call__(self, x):
        x = np.asarray(x, np.float64)
        xc = np.clip(x, self.t[0], self.t[-1])
        i = np.clip(np.searchsorted(self.t, xc) - 1, 0, len(self.t) - 2)
        h = self.t[i + 1] - self.t[i]
        s = (xc - self.t[i]) / h
        s2, s3 = s * s, s * s * s
        return ((2 * s3 - 3 * s2 + 1) * self.v[i] + (s3 - 2 * s2 + s) * h * self.m[i] +
                (-2 * s3 + 3 * s2) * self.v[i + 1] + (s3 - s2) * h * self.m[i + 1])


def _polyline_sdist(px, pz, line):
    """Signed-ish distance from points to a polyline in the (x, z) plane.

    Returns (distance, side sign (+ = right of travel), arc fraction 0..1)."""
    line = np.asarray(line, np.float64)
    a = line[:-1]
    b = line[1:]
    seg = b - a
    L = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(L)])
    best = np.full(px.shape, 1e9)
    sign = np.ones(px.shape)
    frac = np.zeros(px.shape)
    for k in range(len(a)):
        dx, dz = px - a[k, 0], pz - a[k, 1]
        t = np.clip((dx * seg[k, 0] + dz * seg[k, 1]) / (L[k] ** 2), 0.0, 1.0)
        ex, ez = dx - t * seg[k, 0], dz - t * seg[k, 1]
        d = np.hypot(ex, ez)
        m = d < best
        best = np.where(m, d, best)
        cr = seg[k, 0] * dz - seg[k, 1] * dx
        sign = np.where(m, np.where(cr < 0, 1.0, -1.0), sign)
        frac = np.where(m, (cum[k] + t * L[k]) / cum[-1], frac)
    return best, sign, frac


# --------------------------------------------------------------------------
# the head
# --------------------------------------------------------------------------
class HeadSurface:
    def __init__(self, p: fl.FaceParams):
        self.p = p
        rx = p.head[0]
        self.fy = fy = fl.face_plane(p)            # facial plane (glabella / cheeks / lips)
        L = self.L = fl.landmarks(p)
        self.eyeL = fl.eye_geometry(p, 1)
        st = L["stomion"][2]
        self.st_z = st
        # ---- midline soft-tissue profile (without nose and lips), z -> y
        self.mid = Curve([
            (p.trichion + 30.0, fy + 20.0),
            (p.trichion, fy + 5.5 - 0.6 * p.forehead_round),
            (p.glabella + 24.0, fy + 1.0 - p.forehead_round),
            (p.glabella, L["glabella"][1] + 1.0),
            (L["nasion"][2], L["nasion"][1] + 5.0),
            (p.canthus - 10.0, fy + 3.0),
            (p.subnasale, L["subnasale"][1] + 1.5),
            (st, fy + 2.5),
            (L["labrale_inferius"][2], fy + 2.0),
            (L["sublabiale"][2], L["sublabiale"][1]),
            (L["pogonion"][2], L["pogonion"][1] + 1.5),
            (p.menton + 6.0, L["gnathion"][1] + 1.0),
            (p.menton - 4.0, L["menton"][1] + 8.0),
        ])
        # ---- lateral shape per height: half width, side depth, flatness exponent
        zg, zt = p.gonion_z, p.canthus
        # horizontal cross-sections: the front is a superellipse quadrant from the
        # midline (y = mid(z)) to the widest point (x = width, y = mid + depth)
        self.width = Curve([
            (p.glabella + 30.0, rx * 0.86),
            (p.glabella, rx * 0.88),
            (zt, rx * 0.90),
            (zt - 15.0, p.zygion),
            (p.subnasale, p.zygion - 5.5),
            (st, (p.zygion + p.gonion_w) * 0.5 - 8.5),
            (zg, p.gonion_w),
            (p.menton + 8.0, p.gonion_w * (0.6 if p.fem else 0.68)),         # V-line taper to the chin
        ])
        self.depth = Curve([
            (p.glabella + 30.0, 80.0),
            (p.glabella, 80.0),
            (zt, 76.0),
            (zt - 16.0, 74.0),
            (p.subnasale, 76.0),
            (st, 78.0),
            (zg, 84.0),
            (p.menton + 8.0, 84.0),
        ])
        self.back = Curve([
            (p.glabella + 30.0, 60.0),
            (zt, 55.0),
            (zt - 16.0, 42.0),
            (p.subnasale, 36.0),
            (st, 30.0),
            (zg, 26.0),
            (p.menton + 8.0, 10.0),
        ])
        self.flat = Curve([
            (p.glabella + 30.0, 2.0),
            (p.glabella, 2.3),
            (zt, 2.5),
            (zt - 16.0, 2.5),
            (p.subnasale, 2.4),
            (st, 1.85),
            (zg, 1.75 if p.fem else 2.0),
            (p.menton + 8.0, 1.6 if p.fem else 1.9),
        ])
        # the mandibular plane (under the jaw), rises from menton to the gonion
        y_men = L["menton"][1]
        self.jaw_b = 18.0 if p.fem else 13.0          # front-view jaw line: V-line rises faster
        self.jaw_a = (p.gonion_z - p.menton - self.jaw_b) / (6.0 - y_men)
        self.y_men = y_men
        # lips
        stom, upper, lower = fl.lip_curves(p)
        self.lip_x = np.array([a for a, _ in stom])
        self.lip_st = np.array([b for _, b in stom])
        self.lip_up = np.array([b for _, b in upper])
        self.lip_lo = np.array([b for _, b in lower])
        # nasolabial / marionette paths (x, z), traced top -> bottom on the left side
        al = L["alare.L"]
        ch = L["cheilion.L"]
        self.nlf = [(al[0] + 2.5, al[2] + 3.5), (al[0] + 6.0, p.subnasale - 7.0),
                    (ch[0] + 5.0, st - 2.0), (ch[0] + 6.5, st - 9.0)]
        self.mar = [(ch[0] + 1.5, ch[2] - 2.5), (ch[0] + 4.5, st - 12.0), (ch[0] + 7.0, p.menton + 14.0)]
        # nose profile at the midline: z -> y of the dorsum / tip / columella
        n = L["nasion"]
        prn = L["pronasale"]
        sn = L["subnasale"]
        zr = n[2] + (prn[2] - n[2]) * 0.55
        self.nose_z = (n[2], prn[2], sn[2])
        self.dorsum = Curve([
            (n[2] + 8.0, n[1] + 3.0),
            (n[2], n[1]),
            (zr, n[1] + (prn[1] - n[1]) * 0.58 - p.hump),
            (prn[2] + 5.0, prn[1] + 2.4),
            (prn[2], prn[1]),
            (prn[2] - 4.5, prn[1] + 3.2),
            (sn[2] + 1.2, sn[1] - 3.0),
            (sn[2], sn[1]),
        ])
        self.bridge_hw = Curve([
            (n[2] + 8.0, p.bridge_w * 0.75),
            (n[2], p.bridge_w * 0.5),
            (zr, p.bridge_w * 0.48),
            (prn[2] + 6.0, p.tip_w * 0.44),
            (prn[2], p.tip_w * 0.5),
            (sn[2] + 2.0, p.tip_w * 0.36),
            (sn[2], 3.0),
        ])

    # ------------------------------------------------------------------ pieces
    def lips_at(self, x):
        ax = np.abs(x)
        xc = self.p.mouth_w * 0.5
        xs = np.clip(ax, 0.0, xc)
        st = np.interp(xs, self.lip_x[len(self.lip_x) // 2:], self.lip_st[len(self.lip_st) // 2:])
        up = np.interp(xs, self.lip_x[len(self.lip_x) // 2:], self.lip_up[len(self.lip_up) // 2:])
        lo = np.interp(xs, self.lip_x[len(self.lip_x) // 2:], self.lip_lo[len(self.lip_lo) // 2:])
        return st, up, lo

    def lip_mask(self, x, z):
        """1 inside the vermilion (either lip), 0 on skin; soft over ~0.6 mm."""
        _, up, lo = self.lips_at(x)
        inside = np.minimum(sstep(up + 0.5, up - 0.3, z), sstep(lo - 0.5, lo + 0.3, z))
        return inside * sstep(self.p.mouth_w * 0.5 + 0.5, self.p.mouth_w * 0.5 - 1.5, np.abs(x))

    def _lips(self, x, z):
        """Forward (negative y) displacement of the lips and the perioral skin."""
        p = self.p
        ax = np.abs(x)
        xc = p.mouth_w * 0.5
        st, up, lo = self.lips_at(x)
        across = np.clip(1.0 - (ax / (xc + 0.5)) ** 2, 0.0, 1.0)
        # upper lip: pouts most ~40 % down from the border, rolls back into the stomion
        hu = np.maximum(up - st, 0.3)
        tu = np.clip((z - st) / hu, 0.0, 1.0)
        pu = np.sin(np.pi * np.clip(tu * 0.82 + 0.1, 0, 1)) ** 0.7 * (1 - 0.35 * tu)
        upper = p.lip_proj * pu * across ** 0.55 * sstep(st - 0.15, st + 0.15, z)
        hl = np.maximum(st - lo, 0.3)
        tl = np.clip((st - z) / hl, 0.0, 1.0)
        pl = np.sin(np.pi * np.clip(tl * 0.8 + 0.12, 0, 1)) ** 0.65
        lower = (p.lip_proj + 0.3) * pl * across ** 0.5 * sstep(st + 0.15, st - 0.15, z)
        verm = self.lip_mask(x, z)
        d = (upper + lower) * verm
        # the white roll: a thin ridge just outside the vermilion border
        roll_u = np.exp(-(((z - up - 0.45) / 0.55) ** 2)) * across ** 0.8
        roll_l = np.exp(-(((z - lo + 0.5) / 0.6) ** 2)) * across ** 0.8 * 0.6
        d += 0.7 * (roll_u + roll_l)
        # the skin above the upper lip leans forward toward the border (the lip "sits" on the teeth)
        ab = np.clip((z - up) / (p.subnasale - up), 0.0, 1.0)
        d += p.lip_proj * 0.3 * (1 - ab) ** 1.5 * sstep(xc + 6.0, xc - 4.0, ax) * sstep(up - 0.3, up + 0.3, z)
        # philtral columns and the groove between them
        colx = 5.0 - 1.2 * ab
        above = sstep(up - 0.6, up + 0.4, z) * sstep(p.subnasale, p.subnasale - 3, z)
        col = np.exp(-(((ax - colx) / 1.3) ** 2)) * above
        d += 0.55 * col - 0.35 * np.exp(-((x / 2.2) ** 2)) * above
        # the lower lip sits on a soft rounded shelf above the mentolabial sulcus
        d += (p.lip_proj * 0.2) * np.exp(-(((z - lo + 2.5) / 3.0) ** 2)) * sstep(xc + 2, xc - 6, ax)
        # modiolus: the small knot of muscle just lateral to each mouth corner
        d += 0.9 * gauss(ax, z, xc + 3.5, st + p.corner_up * 0.5, 3.0, 4.0)
        d -= 0.9 * gauss(ax, z, xc + 0.8, st + p.corner_up, 1.2, 1.5)   # the corner itself tucks in
        return d

    def _nose(self, x, z):
        """y of the nose surface (nan where there is no nose)."""
        p = self.p
        zn, zt, zs = self.nose_z
        ax = np.abs(x)
        yd = self.dorsum(z)
        hw = self.bridge_hw(z)
        # cross-section: a flat-topped dorsum that turns into steep side walls
        t = ax / hw
        # rounded dorsum, then side walls sloping back into the cheeks
        prof = np.where(t < 1.0, 0.45 * t * t, 0.45 + 0.9 * (t - 1.0) + 0.25 * (t - 1.0) ** 2)
        y = yd + prof * hw
        # the tip lobule: two domes (the lower lateral cartilages) and a softer supratip
        dome = gauss(ax, z, p.tip_w * 0.18, zt + 0.3, p.tip_w * 0.32, 4.4)
        y -= 1.0 * dome
        y += 0.5 * gauss(ax, z, 0.0, zt + 5.5, 3.0, 2.5) * (p.tip_up > 0)
        # beyond the root and below the base the nose recedes smoothly (keeps the field continuous)
        y += 40.0 * (np.clip(z - (zn + 6.0), 0, None) / 10.0) ** 2
        y += 60.0 * (np.clip(zs - z, 0, None) / 2.5) ** 2
        return y

    def _alae(self, x, z):
        """y of the alar lobes (the nostril wings)."""
        p = self.p
        zs = self.nose_z[2]
        ax = np.abs(x)
        cx = p.alar_w * 0.5 - 5.0
        cz = zs + 4.0
        # teardrop lobe: widest low, tapering up into the nasal side wall
        rz_ = np.where(z > cz, 6.5, 4.4)
        r2 = ((ax - cx) / 4.5) ** 2 + ((z - cz) / rz_) ** 2
        tip_y = self.L["pronasale"][1]
        cy = tip_y + 11.0
        return cy - 7.5 * np.sqrt(np.clip(1.0 - r2, 0.0, None)) + 4.0 * np.clip(r2 - 1.0, 0.0, None)

    def eye_dome(self, x, z, extra=0.0):
        """y of the lidded eyeball bulge for both eyes (nan outside)."""
        e = self.eyeL
        cx, cy, cz = e["centre"]
        R = e["R"] + 1.7 + extra
        dx = np.abs(x) - cx
        dz = z - cz
        r2 = R * R - dx * dx - dz * dz
        return np.where(r2 > 0, cy - np.sqrt(np.clip(r2, 0, None)), np.nan)

    def front_y(self, x, z):
        """Depth of the face surface (the front height field)."""
        p = self.p
        ax = np.abs(x)
        w = self.width(z)
        t = np.clip(ax / w, 0.0, 1.0)
        y = self.mid(z) + self.depth(z) * (1.0 - np.sqrt(1.0 - t ** self.flat(z)))
        e = self.eyeL
        ecx, _, ecz = e["centre"]
        # ---- bone and fat masses
        y -= p.forehead_round * gauss(ax, z, 22.0, p.glabella + 30.0, 26.0, 22.0)
        y -= p.brow_ridge * gauss(ax, z, ecx - 4.0, ecz + p.brow_gap + 1.0, 17.0, 5.5)
        y -= p.brow_ridge * 0.5 * gauss(ax, z, 0.0, p.glabella, 9.0, 6.0)
        y += p.temple * gauss(ax, z, w * 0.86, p.glabella + 8.0, 10.0, 16.0)
        # orbits: sink the eye region so the lidded eyeball dome sits in it
        orb = gauss(ax, z, ecx + 0.5, ecz + 0.5, 15.5, 11.5)
        y += 13.5 * orb
        y += 2.0 * gauss(ax, z, ecx - 8.0, ecz + 6.5, 6.0, 4.0) * (1.0 - 0.6 * p.fem)   # upper-lid sulcus
        mal = self.L["malar.L"]
        y -= p.malar * gauss(ax, z, mal[0], mal[2], 13.0, 9.0)
        y -= p.cheek_fat * gauss(ax, z, ecx - 1.0, ecz - 21.0, 16.0, 11.0)
        y += p.buccal * gauss(ax, z, w * 0.72, self.st_z + 6.0, 11.0, 14.0)
        y += p.tear_trough * gauss(ax, z, ecx - 5.0, ecz - 12.5, 7.0, 2.4) * sstep(ecx + 8, ecx - 2, ax)
        # the chin pad (mentalis), mentolabial sulcus
        pg = self.L["pogonion"]
        y -= (2.2 + max(p.chin_proj, 0.0) * 0.4) * gauss(ax, z, 0.0, pg[2] - 1.0,
                                                        p.chin_w * (1.2 if p.fem else 1.35), 9.0) ** 1.5
        y += 1.3 * gauss(ax, z, 0.0, self.L["sublabiale"][2] + 1.0, 14.0, 2.6)
        # jowls hang over the jaw line
        y -= p.jowl * gauss(ax, z, p.chin_w + 20.0, p.menton + 14.0, 11.0, 9.0)
        # ---- folds: nasolabial and marionette (cheek overhang lateral of a groove)
        if p.nasolabial > 0:
            d, sg, fr = _polyline_sdist(ax, z, self.nlf)
            env = sstep(0.0, 0.08, fr) * sstep(1.0, 0.7, fr)
            s = d * -sg       # + lateral
            y -= p.nasolabial * (0.5 + 0.5 * np.tanh(s / 2.2)) * env * np.exp(-((d / 14.0) ** 2))
            y += p.nasolabial * 0.35 * np.exp(-((d / 1.4) ** 2)) * env
        if p.marionette > 0:
            d, sg, fr = _polyline_sdist(ax, z, self.mar)
            env = sstep(0.0, 0.15, fr) * sstep(1.0, 0.6, fr)
            s = d * -sg
            y -= p.marionette * (0.5 + 0.5 * np.tanh(s / 2.0)) * env * np.exp(-((d / 12.0) ** 2))
        # ---- lips
        y -= self._lips(x, z)
        # ---- nose and alae: smooth unions so the alar crease stays sharp
        nose = smin(self._nose(x, z), self._alae(x, z), 2.4)
        y = smin(y, nose, 1.3)
        # alar crease: a groove hugging the back of each ala
        cx = p.alar_w * 0.5 - 5.2
        cz = self.nose_z[2] + 4.2
        ring = np.sqrt(((ax - cx) / 6.9) ** 2 + ((z - cz) / 6.6) ** 2)
        y += 0.9 * np.exp(-(((ring - 1.0) / 0.12) ** 2)) * (ax > cx - 1.0) * (z > cz - 5.0)
        # ---- the lidded eyeballs
        ye = self.eye_dome(x, z)
        y = np.where(np.isnan(ye), y, smin(y, ye, 2.6))
        return y

    # ------------------------------------------------------------------ volumes
    def F_face(self, X, Y, Z):
        """The face mass: the front height field closed by the cheek/ramus sides and the jaw."""
        p = self.p
        w = self.width(Z)
        y_w = self.mid(Z) + self.depth(Z)             # depth of the widest point of the section
        front = smax(self.front_y(X, Z) - Y, np.abs(X) - w, 6.0)
        # behind the widest point the cheek / ramus rounds off toward the ear and the neck
        yb = self.back(Z)
        v = np.clip((Y - y_w) / np.maximum(yb - y_w, 1.0), 0.0, None)
        back = w * ((np.abs(X) / w) ** 3 + v ** 3) ** (1.0 / 3.0) - w
        f = np.where(Y < y_w, front, back)
        zlow = p.menton + self.jaw_a * (Y - self.y_men) + \
            self.jaw_b * np.clip(np.abs(X) / p.gonion_w, 0, 1.3) ** 2
        f = smax(f, zlow - Z, 11.0)                   # the lower border of the mandible
        f = smax(f, Z - (p.glabella + 34.0), 16.0)    # the cranium takes over on the forehead
        return f

    def F_cranium(self, X, Y, Z):
        rx, ry, rz = self.p.head
        cz = rz * 0.155
        Rz = rz - cz
        Ry = np.where(Y < 2.0, ry * 0.93, ry * 0.985)
        k0 = np.sqrt((X / (rx * 0.985)) ** 2 + ((Y - 2.0) / Ry) ** 2 + ((Z - cz) / Rz) ** 2)
        d = (k0 - 1.0) * min(rx, Rz)
        # the occiput is flatter (brachycephalic), the temporal planes flatter still
        d += 2.5 * np.exp(-(((Y - ry * 0.85) / 16.0) ** 2) - (((Z - 5.0) / 30.0) ** 2))
        d += 2.0 * np.exp(-(((np.abs(X) - rx) / 10.0) ** 2) - ((Y / 30.0) ** 2) - (((Z + 15.0) / 22.0) ** 2))
        # the skull base: below the occiput the head gives way to the neck
        return smax(d, -Z - 0.36 * rz - 0.12 * np.clip(-Y, 0, None), 22.0)

    def F_neck(self, X, Y, Z):
        p = self.p
        r = p.neck_r
        zc = p.menton - 20.0
        ync = 7.0 + 0.012 * (Z - zc)
        grow = 1.0 + 0.18 * sstep(zc, zc - 110.0, Z)            # flares toward the shoulders
        rx_ = r * 1.09 * grow
        # the nape rises toward the occiput (cervical lordosis), the throat stays put
        ry_ = r * np.where(Y > ync, 1.0 + 0.45 * sstep(zc, zc + 95.0, Z), 0.98) * grow
        a = np.arctan2(X, -(Y - ync))
        scm = (0.07 if not p.fem else 0.035) * np.exp(-((np.abs(np.sin(a)) - 0.62) / 0.24) ** 2) * (np.cos(a) > 0)
        k = np.sqrt((X / rx_) ** 2 + ((Y - ync) / ry_) ** 2)
        d = (k - 1.0 - scm) * ry_
        d -= p.adam * np.exp(-((X / 7.0) ** 2) - (((Z - (zc - 22.0)) / 10.0) ** 2)) * (Y < ync)
        # the throat is flatter than the nape
        d += 2.0 * np.exp(-((X / 18.0) ** 2)) * (Y < ync) * sstep(zc + 10, zc - 20, Z)
        return smax(d, Z - (p.menton + 70.0), 10.0)            # ends inside the skull

    def F(self, X, Y, Z):
        back = smin(self.F_cranium(X, Y, Z), self.F_neck(X, Y, Z), 18.0)
        return smin(back, self.F_face(X, Y, Z), self.p.jaw_soft)

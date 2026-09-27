"""Facial shape keys (glTF morph targets) for the head built by face_head.

Keys (all 0..1):

    blink_L  blink_R  squint_L  squint_R  lid_look_up  lid_look_down  eyes_wide
    brow_up  brow_down  brow_inner_up
    smile  frown  sneer_L  sneer_R  cheek_puff  mouth_stretch
    jaw_open  viseme_AA  viseme_EE  viseme_OO  viseme_MM  viseme_FF

Three kinds of deformation are combined:

* lid states - the lid loops, lashes and tear lines are *regenerated* by the
  same geometry code with a changed lid state (close / squint / look / wide),
  so a blink slides the lid over the eyeball instead of cutting through it;
  the cast loops around the eye follow with a falloff;
* the jaw - a rotation about the temporomandibular axis weighted by how
  much of the lower face rides on the mandible (lower lip and teeth fully,
  the cheeks partly, the neck fading out, the upper lip not at all);
* muscle fields - smooth displacement fields of the rest position for the
  zygomaticus (smile), depressor anguli oris (frown), levator labii (sneer),
  frontalis (brow up), corrugator (brow down), orbicularis oris (visemes)...
  Brow hairs ride on the skin fields; eyeballs never move with keys.
"""
import math

import numpy as np

from . import face_cards, face_eyes, face_mouth
from . import face_landmarks as fl


def _sstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _g(x, z, cx, cz, sx, sz):
    """Gaussian muscle field, cut to zero past ~2.8 sigma so the morph targets stay sparse."""
    g = np.exp(-(((x - cx) / sx) ** 2 + ((z - cz) / sz) ** 2))
    return np.where(g < 0.02, 0.0, g)


def _rot_x(P, pivot, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    q = P - pivot
    y = q[:, 1] * c - q[:, 2] * s
    z = q[:, 1] * s + q[:, 2] * c
    return np.stack([q[:, 0], y, z], axis=-1) + pivot - P


class FaceShapes:
    JAW_MAX = 21.0          # degrees of mandible rotation at jaw_open = 1

    def __init__(self, fh):
        self.fh = fh
        self.p = p = fh.p
        self.P = fh.rest_mm
        self.N = len(self.P)
        self.L = fl.landmarks(p)
        self.st = self.L["stomion"][2]
        self.xc = p.mouth_w * 0.5
        H = fh.mesh
        n_skin = fh.parts["skin"][1]
        self.skin = np.zeros(self.N, bool)
        self.skin[:n_skin] = True
        for sx in ("L", "R"):
            self.skin[fh.range(f"brow_{sx}")] = True      # brow hairs ride on the skin fields
        # region bookkeeping from the head mesh O-grids
        self.lid_fixed = np.zeros(self.N, bool)        # explicit lid loops (driven by lid states)
        self.mouth_upper = np.full(self.N, np.nan)     # 1 upper lip side, 0 lower, 0.5 corners
        self.mouth_ring = np.full(self.N, np.nan)
        self.eye_grids = {}
        for kind, d in H.ogrids:
            if kind == "eye":
                self.eye_grids[d["side"]] = d
                for ring in d["rings"][:d["n_exp"]]:
                    self.lid_fixed[ring] = True
            elif kind == "mouth":
                s = d["s"]
                up = _sstep(-0.18, 0.18, np.sin(2 * math.pi * s))
                for k, ring in enumerate(d["rings"][:-1]):
                    self.mouth_upper[ring] = up
                    self.mouth_ring[ring] = k - d["contact"]
                self.mouth_upper[d["centre"]] = 0.5
                self.mouth_ring[d["centre"]] = -d["contact"] - 1
        x, z = self.P[:, 0], self.P[:, 2]
        st_x, _, _ = H.surf.lips_at(x)
        # above (1) / below (0) the mouth line for skin outside the mouth O-grid
        side = _sstep(st_x - 1.5, st_x + 1.5, z)
        # far from the mouth the lip side is irrelevant; keep the jaw logic simple there
        self.upper = np.where(np.isnan(self.mouth_upper), side, self.mouth_upper)
        self.pivot = face_mouth.jaw_pivot(p)

    # ------------------------------------------------------------------ building blocks
    def lid_delta(self, states):
        """Delta for the lid loops, their blend loops, lashes and tear lines for {side: state}."""
        fh = self.fh
        D = np.zeros((self.N, 3))
        for side, st in states.items():
            d = self.eye_grids[side]
            s = d["s"]
            new = fh.mesh.eye_rings(side, s, st)
            n_exp = d["n_exp"]
            last = None
            for k in range(n_exp):
                ids = d["rings"][k]
                D[ids] = new[k] - self.P[ids]
                last = D[ids].copy()
            n_blend = len(d["rings"]) - 1 - n_exp
            for k in range(n_blend):
                f = (1.0 - (k + 1) / (n_blend + 1)) ** 1.6
                D[d["rings"][n_exp + k]] = last * f
            sx = "L" if side > 0 else "R"
            lv, _ = face_cards.lash_points(fh.lids[side], st)
            ids = fh.range(f"lash_{sx}")
            D[ids] = lv - self.P[ids]
            tv, _, _ = face_eyes.tearline_points(fh.lids[side], st)
            ids = fh.range(f"tear_{sx}")
            D[ids] = tv - self.P[ids]
        return D

    def jaw_weight(self):
        """How much each vertex rides on the mandible."""
        p = self.p
        x, y, z = self.P[:, 0], self.P[:, 1], self.P[:, 2]
        ax = np.abs(x)
        below = 1.0 - self.upper
        lateral = 1.0 - 0.6 * _sstep(self.xc - 2.0, self.xc + 24.0, ax)
        back = 1.0 - 0.85 * _sstep(-15.0, 20.0, y)
        neck = _sstep(p.menton - 50.0, p.menton - 4.0, z) * (1.0 - _sstep(-30.0, 20.0, y) * _sstep(-60, -110, z))
        w = below * lateral * back * neck
        # the cheek skin beside and above the corners is stretched a little
        w += 0.22 * self.upper * _g(ax, z, self.xc + 6.0, self.st + 4.0, 8.0, 7.0)
        w = np.where(self.skin, w, 0.0)
        mp = self.fh.mouth_parts
        w[mp["lower"]] = 1.0
        w[mp["tongue"]] = 0.85
        w[mp["upper"]] = 0.0
        return np.clip(w, 0.0, 1.0)

    def jaw(self, amount):
        w = self.jaw_weight()
        D = _rot_x(self.P, self.pivot, self.JAW_MAX * amount) * w[:, None]
        # the lower lip lags a touch behind the chin and drops slightly more
        lower_lip = (self.mouth_ring >= 0) & (self.mouth_upper < 0.3)
        D[lower_lip, 2] -= 0.8 * amount
        return D

    def skin_only(self, D):
        D = np.where(self.skin[:, None] & ~self.lid_fixed[:, None], D, 0.0)
        return D

    def mouth_zone(self, sx=None, sz=None):
        """Weight of the perioral region (lips and the skin around them)."""
        x, z = self.P[:, 0], self.P[:, 2]
        return _g(x, z, 0.0, self.st, sx or self.xc + 9.0, sz or 16.0)

    def corner(self, side, rx=11.0, rz=10.0):
        x, z = self.P[:, 0], self.P[:, 2]
        ch = self.L["cheilion.L"]
        return _g(x, z, side * ch[0], ch[2], rx, rz) * _sstep(-self.xc * 0.3, 0.0, x * side)

    def lip_verm(self):
        """1 on the vermilion / contact loops of the mouth O-grid, fading out on the skin."""
        r = self.mouth_ring
        w = np.where(np.isnan(r), 0.0, np.clip(1.0 - (r - 4.0) / 5.0, 0.0, 1.0))
        return w

    # ------------------------------------------------------------------ the keys
    def keys(self):
        p = self.p
        x, y, z = self.P[:, 0], self.P[:, 1], self.P[:, 2]
        ax = np.abs(x)
        st = self.st
        K = {}
        e = fl.eye_geometry(p, 1)
        ecx, ecz = abs(e["centre"][0]), e["centre"][2]
        brow_z = ecz + p.brow_gap

        # ---- eyes
        for side, sx in ((1, "L"), (-1, "R")):
            D = self.lid_delta({side: {"close": 1.0}})
            # the brow and cheek skin barely follow a blink
            K[f"blink_{sx}"] = D
            D = self.lid_delta({side: {"squint": 1.0}})
            cheek = _g(x * side, z, ecx - 2.0, ecz - 20.0, 16.0, 11.0) * (x * side > 0)
            crow = _g(x * side, z, ecx + 16.0, ecz, 8.0, 10.0) * (x * side > 0)
            F = np.zeros_like(D)
            F[:, 2] += 2.2 * cheek
            F[:, 1] -= 0.8 * cheek
            F[:, 0] -= side * 1.2 * crow
            F[:, 2] -= 1.4 * _g(x * side, z, ecx, brow_z, 14.0, 5.0) * (x * side > 0)
            K[f"squint_{sx}"] = D + self.skin_only(F)
        K["lid_look_up"] = self.lid_delta({1: {"look": 1.0}, -1: {"look": 1.0}})
        K["lid_look_down"] = self.lid_delta({1: {"look": -1.0}, -1: {"look": -1.0}})
        D = self.lid_delta({1: {"wide": 1.0}, -1: {"wide": 1.0}})
        F = np.zeros_like(D)
        F[:, 2] += 1.2 * _g(ax, z, ecx, brow_z, 18.0, 6.0)
        K["eyes_wide"] = D + self.skin_only(F)

        # ---- brows (frontalis / corrugator / medial frontalis)
        fore = _sstep(ecz + 4.0, ecz + 12.0, z) * (1.0 - 0.75 * _sstep(brow_z + 8.0, p.trichion + 10.0, z))
        fore *= 1.0 - _sstep(55.0, 70.0, ax)
        F = np.zeros((self.N, 3))
        F[:, 2] += 5.0 * fore
        F[:, 1] += 0.6 * fore * _sstep(brow_z + 4, brow_z + 25, z)          # forehead skin bunches
        lid_sk = _g(ax, z, ecx, ecz + 7.5, 12.0, 3.5)
        F[:, 2] += 1.6 * lid_sk
        K["brow_up"] = self.skin_only(F) + 0.35 * self.lid_delta({1: {"wide": 1.0}, -1: {"wide": 1.0}})
        F = np.zeros((self.N, 3))
        knit = _g(ax, z, ecx - 10.0, brow_z, 16.0, 8.0)
        F[:, 2] -= 3.6 * knit
        F[:, 0] -= np.sign(x) * 2.6 * _g(ax, z, ecx - 14.0, brow_z, 12.0, 8.0)
        gl = _g(ax, z, 0.0, p.glabella, 12.0, 9.0)
        F[:, 1] -= 1.4 * gl
        F[:, 1] -= 1.0 * _g(ax, z, ecx - 12.0, brow_z + 1.0, 7.0, 4.0)       # the corrugator bulge
        K["brow_down"] = self.skin_only(F) + 0.3 * self.lid_delta({1: {"squint": 1.0}, -1: {"squint": 1.0}})
        F = np.zeros((self.N, 3))
        inner = _g(ax, z, ecx - 13.0, brow_z + 3.0, 11.0, 9.0) * (z > ecz + 5.0)
        F[:, 2] += 4.2 * inner
        F[:, 1] += 0.5 * _g(ax, z, 0.0, p.glabella + 20.0, 20.0, 10.0)
        K["brow_inner_up"] = self.skin_only(F)

        # ---- mouth (zygomaticus, depressors, levators, buccinator)
        F = np.zeros((self.N, 3))
        for side in (1, -1):
            c = self.corner(side, 14.0, 12.0)
            F[:, 0] += side * 4.2 * c
            F[:, 1] += 3.2 * c
            F[:, 2] += 6.0 * c
            cheek = _g(x * side, z, ecx - 4.0, ecz - 24.0, 18.0, 14.0) * (x * side > 0)
            F[:, 2] += 4.0 * cheek
            F[:, 1] -= 2.6 * cheek
            # the nasolabial fold deepens: the fat lateral of it bulges forward
            nl = _g(x * side, z, p.alar_w * 0.5 + 10.0, st + 10.0, 7.0, 12.0) * (x * side > 0)
            F[:, 1] -= 1.6 * nl
        F[:, 2] += 0.7 * self.lip_verm() * (self.upper > 0.5)                 # the upper lip lifts
        F[:, 1] += 0.6 * self.lip_verm()                                       # lips stretch over the teeth
        K["smile"] = self.skin_only(F) + 0.35 * self.lid_delta({1: {"squint": 1.0}, -1: {"squint": 1.0}}) \
            + self.jaw(0.06)
        F = np.zeros((self.N, 3))
        for side in (1, -1):
            c = self.corner(side, 12.0, 11.0)
            F[:, 2] -= 4.6 * c
            F[:, 0] += side * 1.2 * c
            F[:, 1] += 1.0 * c
        chin = _g(ax, z, 0.0, self.L["pogonion"][2], 14.0, 9.0)
        F[:, 2] += 1.6 * chin
        F[:, 1] -= 1.4 * chin
        low = self.lip_verm() * (self.upper < 0.5)
        F[:, 2] += 1.0 * low
        F[:, 1] -= 1.0 * low                                                   # the lower lip pouts
        K["frown"] = self.skin_only(F)
        for side, sx in ((1, "L"), (-1, "R")):
            F = np.zeros((self.N, 3))
            lev = _g(x * side, z, 11.0, st + 6.0, 9.0, 6.0) * (x * side > -2.0) * (self.upper > 0.4)
            F[:, 2] += 4.8 * lev
            F[:, 1] -= 1.0 * lev
            ala = _g(x * side, z, p.alar_w * 0.5 - 2.0, p.subnasale + 4.0, 7.0, 7.0) * (x * side > 0)
            F[:, 2] += 3.0 * ala
            F[:, 0] += side * 0.9 * ala
            nl = _g(x * side, z, p.alar_w * 0.5 + 8.0, st + 14.0, 7.0, 9.0) * (x * side > 0)
            F[:, 2] += 2.0 * nl
            F[:, 1] -= 1.4 * nl
            bridge = _g(x * side, z, 5.0, self.L["nasion"][2] - 8.0, 6.0, 5.0)
            F[:, 1] -= 0.6 * bridge                                              # nose wrinkle
            F[:, 2] -= 0.6 * bridge
            K[f"sneer_{sx}"] = self.skin_only(F) + 0.25 * self.lid_delta({side: {"squint": 1.0}})
        F = np.zeros((self.N, 3))
        puff = _g(ax, z, self.xc + 12.0, st + 2.0, 13.0, 15.0) * _sstep(-40.0, -65.0, y)
        F[:, 0] += np.sign(x) * 8.0 * puff
        F[:, 1] -= 3.5 * puff
        F[:, 1] -= 1.2 * self.lip_verm()
        F[:, 1] -= 1.4 * _g(ax, z, 0.0, st + 9.0, 12.0, 5.0)                   # air over the upper lip
        K["cheek_puff"] = self.skin_only(F)
        F = np.zeros((self.N, 3))
        for side in (1, -1):
            c = self.corner(side, 12.0, 12.0)
            F[:, 0] += side * 4.0 * c
            F[:, 2] -= 2.0 * c
            F[:, 1] += 1.0 * c
        neck = _sstep(p.menton - 10.0, p.menton - 60.0, z) * _g(ax, z, 30.0, p.menton - 40.0, 16.0, 30.0)
        F[:, 1] -= 1.5 * neck                                                  # platysma bands
        K["mouth_stretch"] = self.skin_only(F) + self.jaw(0.18)

        # ---- jaw and visemes
        K["jaw_open"] = self.jaw(1.0)
        verm = self.lip_verm()
        up_l = verm * (self.upper > 0.5)
        lo_l = verm * (self.upper < 0.5)
        F = np.zeros((self.N, 3))
        F[:, 2] += 0.8 * up_l
        K["viseme_AA"] = self.jaw(0.62) + self.skin_only(F)
        F = np.zeros((self.N, 3))
        for side in (1, -1):
            c = self.corner(side, 13.0, 10.0)
            F[:, 0] += side * 4.4 * c
            F[:, 1] += 2.0 * c
            F[:, 2] += 1.2 * c
        F[:, 2] += 1.2 * up_l
        F[:, 1] += 0.6 * verm
        K["viseme_EE"] = self.jaw(0.18) + self.skin_only(F)
        F = np.zeros((self.N, 3))
        zone = self.mouth_zone(self.xc + 6.0, 12.0)
        F[:, 0] -= x * 0.5 * zone                                              # purse toward the centre
        F[:, 1] -= 7.0 * zone * (0.35 + 0.65 * verm)
        F[:, 2] -= (z - st) * 0.18 * verm
        K["viseme_OO"] = self.jaw(0.12) + self.skin_only(F)
        F = np.zeros((self.N, 3))
        F[:, 1] += 0.9 * verm                                                  # lips press and roll in
        F[:, 2] -= 0.5 * up_l
        F[:, 2] += 0.5 * lo_l
        F[:, 1] -= 0.8 * _g(ax, z, 0.0, st, self.xc + 4.0, 9.0) * (1 - verm)   # the skin around bulges
        K["viseme_MM"] = self.skin_only(F)
        F = np.zeros((self.N, 3))
        tuck = verm * (self.upper < 0.5) + 0.5 * _g(ax, z, 0.0, st - 8.0, self.xc, 5.0) * (self.upper < 0.5)
        F[:, 2] += 3.0 * tuck
        F[:, 1] += 3.4 * tuck
        F[:, 2] += 0.8 * up_l
        K["viseme_FF"] = self.jaw(0.1) + self.skin_only(F)
        return K


MIN_DELTA_MM = 0.08

ORDER = ("blink_L", "blink_R", "squint_L", "squint_R", "lid_look_up", "lid_look_down", "eyes_wide",
         "brow_up", "brow_down", "brow_inner_up", "smile", "frown", "sneer_L", "sneer_R", "cheek_puff",
         "mouth_stretch", "jaw_open", "viseme_AA", "viseme_EE", "viseme_OO", "viseme_MM", "viseme_FF")


def build(fh):
    """Add the facial shape keys to fh.obj; returns their names in order."""
    obj = fh.obj
    K = FaceShapes(fh).keys()
    obj.shape_key_add(name="Basis", from_mix=False)
    rest = np.array([v.co for v in obj.data.vertices])
    k = 0.001 * fh.s
    for name in ORDER:
        kb = obj.shape_key_add(name=name, from_mix=False)
        D = K[name]
        D[np.linalg.norm(D, axis=1) < MIN_DELTA_MM] = 0.0      # keeps the glTF morph targets sparse
        co = rest + D * k
        kb.data.foreach_set("co", co.ravel())
        kb.value = 0.0
    obj.data.shape_keys.use_relative = True
    return list(ORDER)

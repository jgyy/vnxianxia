"""Skin textures: the painted head (face) texture and tileable body skin.

References for what real (not airbrushed) skin looks like in candid HD photos of
K-pop idols and actors, and for how it is rendered:
  - "Glass skin" is still skin: visible pores in the T-zone and on the nose/inner
    cheeks, fine cross-hatched skin lines, vellus hair catching rim light, a slightly
    redder nose tip, cheeks and ears, darker thinner skin under the eyes, lips with
    vertical lines and a wet highlight (Korean beauty guides; candid fan-cam stills).
  - Subsurface mean free path of skin ~3.7 / 1.4 / 0.7 mm (R/G/B) - Jensen et al. 2001,
    "A Practical Model for Subsurface Light Transport"; Blender manual (Random Walk Skin).
  - Two-lobe skin specular (d'Eon & Luebke, GPU Gems 3 ch. 14, "Advanced Techniques for
    Realistic Real-Time Skin Rendering"): oily, sharper T-zone versus matte cheeks.
  - Melanin / haemoglobin chromophore maps (Jimenez et al. 2010, "A Practical
    Appearance Model for Dynamic Facial Color"): melanin absorbs increasingly toward
    blue (browning), haemoglobin mostly green (reddening).
  - Skin tension (Langer) lines: pores and fine wrinkles stretch horizontally on the
    forehead, around the eyes concentrically, diagonally on the cheeks.
  - Korean makeup looks: gradient (inner-lip) tint, soft blush high on the cheek toward
    the nose, thin liner, "aegyo-sal" highlight under the eye.  Male: beard shadow of
    dark follicles under the skin.  Elders: solar lentigines, deep forehead lines,
    crow's feet, nasolabial folds.
No specific real person is copied: all features are parametric.

Texture channels produced (all per texel of the head UV layout):
  albedo (sRGB), roughness, ambient occlusion / cavity, height -> tangent normal.
"""
import math

import numpy as np

from . import skin_maps as SM
from . import skin_shading, tex

# default face landmarks in face coordinates (lon, lat radians) of the surface POSITION
# (skin_maps.FaceFrame), measured on the procedural head.  A head builder can override
# them per object with a custom property  obj["face_landmarks"] = {name: (x, y, z)}
# (world positions: eye, nose_tip, nostril, lip_line, upper_lip, lower_lip, chin, cheek,
# ear, mouth_corner) - see landmarks().
LANDMARKS = dict(
    eye=(0.5, 0.077), eye_w=0.16,
    brow=0.227, brow_w=0.24,
    nose_tip=(0.0, -0.252), nostril=(0.105, -0.344),
    lip_line=-0.515, upper_lip=-0.495, lower_lip=-0.547, mouth_w=0.19,
    chin=-0.655, cheek=(0.555, -0.26), ear=(1.27, -0.158),
)
MELANIN = np.array([0.42, 0.62, 0.95], np.float32)       # absorption per unit melanin (browning)
HAEMO = np.array([0.04, 0.55, 0.42], np.float32)         # absorption per unit haemoglobin (reddening)
VENOUS = np.array([0.30, 0.26, 0.10], np.float32)        # deoxygenated blood / thin skin (purple-blue)


def lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb_of(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(np.float32)


def landmarks(cfg, eye_centres=None, frame_of=None, points=None):
    """Landmarks: defaults, then world points given by the head builder, then measured eyes."""
    lm = dict(LANDMARKS, **cfg.get("face_landmarks", {}))
    for k, p in (points or {}).items():
        lon, lat = frame_of(np.array([p], np.float32))
        lon, lat = float(abs(lon[0])), float(lat[0])
        if k == "mouth_corner":
            lm["mouth_w"] = lon
        elif isinstance(lm.get(k), tuple):
            lm[k] = (lon, lat)
        elif k in lm:
            lm[k] = lat
    if eye_centres and frame_of is not None:
        lon, lat = frame_of(np.array(eye_centres, np.float32))
        e_lon, e_lat = float(np.abs(lon).mean()), float(lat.mean())
        d = e_lat - lm["eye"][1]
        lm["eye"] = (e_lon, e_lat)
        lm["brow"] = lm["brow"] + d
    return lm


# --------------------------------------------------------------------------
# face
# --------------------------------------------------------------------------
class FacePainter:
    """Paints albedo / roughness / AO / height for texels given their surface positions."""

    def __init__(self, pos, nrm, cover, centre, radii, cfg, lm, seed=11):
        self.cfg = cfg
        self.c = cfg["colors"]
        self.fem = cfg["female"]
        self.age = cfg.get("age", 0.0)
        self.lm = lm
        self.f = SM.FaceFrame(pos, centre, radii)
        self.pos = pos
        self.nrm = nrm
        self.cover = cover
        self.idx = np.nonzero(cover)
        self.seed = seed
        shape = cover.shape
        self.mel = np.ones(shape, np.float32)
        self.hb = np.ones(shape, np.float32)
        self.ven = np.zeros(shape, np.float32)
        self.height = np.zeros(shape, np.float32)
        self.rough = np.full(shape, 0.5, np.float32)
        self.ao = np.ones(shape, np.float32)
        self.paint = []                   # (colour sRGB (3,), mask) layers applied after the skin model

    def solid(self, fn, mask=None):
        """Evaluate fn(positions, index) on covered texels (inside mask > 0.01 if given); zeros elsewhere."""
        idx = self.idx if mask is None else np.nonzero(self.cover & (mask > 0.01))
        out = np.zeros(self.cover.shape, np.float32)
        if len(idx[0]):
            out[idx] = fn(self.pos[idx], idx)
        return out

    def coarse(self, fn, k=4):
        """Evaluate a smooth solid function at 1/k resolution and upsample."""
        n = self.cover.shape[0]
        pos = skin_shading.resize(self.pos, n // k)
        return skin_shading.resize(fn(pos), n)

    def dir_at(self, ang, idx):
        """World tangent direction at `ang` (per covered texel) from east toward north."""
        a = ang[..., None]
        return self.f.east[idx] * np.cos(a) + self.f.north[idx] * np.sin(a)

    # -- region masks ---------------------------------------------------
    def regions(self):
        f, lm = self.f, self.lm
        el, et = lm["eye"]
        r = {}
        r["face"] = f.blob(0, -0.3, 1.25, 0.95, 4)
        r["forehead"] = f.blob(0, lm["brow"] + 0.22, 0.55, 0.16, 2.5)
        r["tzone"] = np.clip(r["forehead"] + f.blob(0, -0.1, 0.1, 0.24) + f.blob(0, lm["chin"], 0.2, 0.1), 0, 1)
        r["nose"] = np.clip(f.blob(*lm["nose_tip"], 0.12, 0.08) + f.pair(lm["nostril"][0], lm["nostril"][1] + 0.02,
                                                                          0.06, 0.05), 0, 1)
        r["cheeks"] = f.pair(*lm["cheek"], 0.26, 0.2)
        r["ears"] = f.pair(*lm["ear"], 0.2, 0.3)
        r["lid_up"] = f.pair(el, et + 0.065, lm["eye_w"] * 0.95, 0.05)
        r["under_eye"] = f.pair(el + 0.01, et - 0.075, lm["eye_w"] * 0.95, 0.04)
        up = np.exp(-((f.lon / lm["mouth_w"]) ** 2) * 0.9 - ((f.lat - lm["upper_lip"]) / 0.022) ** 2)
        lo = np.exp(-((f.lon / (lm["mouth_w"] * 1.05)) ** 2) - ((f.lat - lm["lower_lip"]) / 0.03) ** 2)
        cupid = np.exp(-((f.lon / 0.05) ** 2) - ((f.lat - lm["upper_lip"] - 0.02) / 0.009) ** 2)
        r["upper_lip"] = np.clip(up * 1.6 - cupid * 0.8, 0, 1)
        r["lower_lip"] = np.clip(lo * 1.5, 0, 1)
        r["lips"] = np.clip(r["upper_lip"] + r["lower_lip"], 0, 1)
        r["mouth_line"] = np.exp(-((f.lon / (lm["mouth_w"] * 0.92)) ** 4) - ((f.lat - lm["lip_line"]) / 0.006) ** 2)
        # beard area: jaw, chin and upper lip, not on the lips, fading up the cheeks
        jaw = tex.sstep(lm["lip_line"] + 0.16, lm["lip_line"] - 0.04, f.lat) * np.exp(-((f.lon / 1.3) ** 6))
        jaw *= tex.sstep(-1.0, -0.8, f.lat)              # fade out under the jaw (no line at the neck seam)
        stache = np.exp(-((f.lon / 0.3) ** 2) - ((f.lat - lm["upper_lip"] - 0.07) / 0.035) ** 2)
        r["beard"] = np.clip(jaw + stache, 0, 1) * (1 - r["lips"])
        r["neck"] = tex.sstep(-1.0, -1.25, f.lat)
        hz = self.cfg["_hairline"](np.abs(f.lon))
        r["scalp"] = tex.sstep(hz - 0.01, hz + 0.05, np.sin(f.lat))
        r["hairline"] = np.exp(-((np.sin(f.lat) - hz) / 0.03) ** 2)
        return r

    # -- layers -----------------------------------------------------------
    def micro(self, r):
        """Pores (two scales, stretched along tension lines), skin lines, mottling."""
        p, f, cov = self.pos, self.f, self.cover
        # tension lines: horizontal on the forehead, circles around the eyes, diagonal on cheeks
        ang = np.zeros_like(f.lon)
        el, et = self.lm["eye"]
        for side in (1, -1):
            dl, dt = f.lon - side * el, f.lat - et
            around = np.arctan2(dt, dl) + math.pi / 2
            w = np.exp(-(dl ** 2 + dt ** 2) / 0.03)
            ang = ang * (1 - w) + around * w
        cheek = r["cheeks"] * np.sign(f.lon) * -0.6
        ang = ang + cheek
        ang = np.where(np.abs(f.lon) < 0.12, ang + (math.pi / 2) * f.blob(0, -0.15, 0.12, 0.2), ang)
        idx = self.idx
        q = p[idx]
        ang = ang[idx]
        td = self.dir_at(ang, idx)
        out = {}
        big_d, big_id = SM.worley3(SM.stretch(q, td, 1.6), 0.00105, self.seed)
        fine_d, _ = SM.worley3(SM.stretch(q, td, 1.3), 0.00052, self.seed + 5)
        size = 0.2 + 0.25 * big_id
        out["pore"] = np.exp(-(big_d / size) ** 2)
        out["fine"] = np.exp(-(fine_d / 0.22) ** 2)
        # cross-hatched skin lines: ridged noise squashed along two directions +-40 deg
        la = SM.value3(SM.stretch(q, self.dir_at(ang + 0.7, idx), 7.0), 0.0009, self.seed + 9)
        lb = SM.value3(SM.stretch(q, self.dir_at(ang - 0.7, idx), 7.0), 0.0009, self.seed + 10)
        out["lines"] = np.maximum(1 - np.abs(la - 0.5) * 7, 0) + np.maximum(1 - np.abs(lb - 0.5) * 7, 0) * 0.8
        out["vellus"] = SM.value3(SM.stretch(q, f.north[idx], 6.0), 0.0005, self.seed + 15)
        maps = {}
        for k, v in out.items():
            m = np.zeros(cov.shape, np.float32)
            m[idx] = v
            maps[k] = m
        maps["mottle"] = self.coarse(lambda q: SM.fbm3(q, 0.012, 3, 0.5, self.seed + 13), 4)
        maps["cap"] = self.coarse(lambda q: SM.fbm3(q, 0.0035, 2, 0.5, self.seed + 14), 2)   # fine redness
        return maps

    def skin_model(self, r, m):
        f, fem, age = self.f, self.fem, self.age
        mel, hb = self.mel, self.hb
        mel += (m["mottle"] - 0.5) * 0.16
        hb += (m["cap"] - 0.5) * 0.35 + (m["mottle"] - 0.5) * 0.15
        hb += r["cheeks"] * (0.55 if fem else 0.4) + r["nose"] * 0.75 + r["ears"] * 0.7
        hb += r["lid_up"] * 0.35 + f.blob(0, self.lm["chin"], 0.22, 0.1) * 0.25
        hb -= r["forehead"] * 0.1
        mel += r["forehead"] * 0.05 + r["lid_up"] * 0.12 + r["mouth_line"] * 0.25
        self.ven += r["under_eye"] * (0.55 + 0.4 * age)
        # lips: blood-rich, low melanin contrast; natural lips darken toward the edge
        mel += r["lips"] * 0.1
        hb += r["lips"] * (2.0 if fem else 1.1)
        # freckles and a mole or two (sparse, stable per character)
        rng = np.random.default_rng(self.seed + 3)
        spots = np.zeros_like(mel)
        n_spots = 3 + int(age * 14)
        for _ in range(n_spots):
            lon = rng.uniform(-1.1, 1.1)
            lat = rng.uniform(-0.9, 0.55)
            size = rng.uniform(0.006, 0.012) * (1 + 2.5 * age * rng.random())
            spots += f.blob(lon, lat, size, size * rng.uniform(0.8, 1.3)) * rng.uniform(0.25, 0.9)
        mel += np.clip(spots, 0, 1.0) * (0.7 + 0.6 * age) * (1 - r["lips"])
        if age > 0.3:   # solar lentigines on cheekbones and temples
            lent = SM.blur(tex.sstep(0.62, 0.8, m["mottle"]), 1) * (r["cheeks"] + f.pair(0.9, 0.25, 0.25, 0.2))
            mel += np.clip(lent, 0, 1) * 0.9 * (age - 0.3)
        mel += m["pore"] * 0.08 * r["face"]

    def features(self, r, m):
        """Brows, beard shadow, hairline, nostrils, wrinkles, makeup."""
        f, c, lm, fem, age = self.f, self.c, self.lm, self.fem, self.age
        h = self.height
        el, et = lm["eye"]
        # eyebrows: soft base plus directional hair strokes growing outward and up
        for side in (1, -1):
            rel = (f.lon - side * el) * side
            peak = 0.07 if fem else 0.1
            k = np.where(rel < peak, 0.55 if fem else 0.3, 2.4 if fem else 1.3)
            arch = lm["brow"] - k * (rel - peak) ** 2
            width = (0.022 if fem else 0.03) * (1 - 0.45 * tex.sstep(0.0, 0.26, rel))
            span = np.exp(-(((f.lon - side * el) / lm["brow_w"]) ** 6))
            brow = np.exp(-((f.lat - arch) / width) ** 2) * span
            head_start = tex.sstep(-0.19, -0.12, rel)          # soft, sparse inner start
            strokes = tex.sstep(0.35, 0.8, m["vellus"] * 0.6 + 0.6 * self.solid(lambda q, i: SM.value3(
                SM.stretch(q, self.dir_at(np.full(len(q), side * 0.35, np.float32), i), 5.0), 0.0006,
                self.seed + 21), mask=brow))
            dens = np.clip(brow * (0.5 + 0.8 * strokes) * (0.45 + 0.55 * head_start), 0, 1)
            self.paint.append((tex.srgb(c["brow"]), dens * (0.85 if fem else 0.95)))
            self.rough += dens * 0.1
        # beard shadow: dark follicles and blue-grey hair under the skin
        stub = self.cfg.get("stubble", 0.0 if fem else 0.35)
        if stub > 0:
            fol = self.solid(lambda q, i: np.exp(-(SM.worley3(q, 0.0009, self.seed + 31)[0] / 0.22) ** 2),
                             mask=r["beard"])
            area = r["beard"] * stub
            self.paint.append((tex.srgb(c["hair"]) * 0.6 + np.array([0.08, 0.09, 0.11], np.float32),
                               area * (0.22 + 0.55 * fol)))
            self.ven += area * 0.25
            h += area * fol * 0.25
            self.rough += area * 0.06
        # hairline: fine baby hairs fading into the skin under the scalp cap
        hz = self.cfg["_hairline"](np.abs(f.lon))
        z = np.sin(f.lat)
        edge = tex.sstep(hz - 0.045, hz + 0.01, z)
        streak = tex.sstep(0.45, 0.85, self.solid(
            lambda q, i: SM.value3(SM.stretch(q, f.north[i], 8.0), 0.00045, self.seed + 41), mask=edge * (1 - edge)))
        self.paint.append((tex.srgb(c["hair"]) * 0.8, np.clip(edge * (0.1 + 0.8 * streak) * (1 - r["neck"]), 0, 1)
                           * 0.9))
        self.paint.append((tex.srgb(c["hair"]) * 0.7 + 0.05, r["scalp"] * 0.75))
        # nostrils and nose shadows
        nost = f.pair(lm["nostril"][0], lm["nostril"][1], 0.034, 0.018)
        self.paint.append((np.array([0.18, 0.08, 0.07], np.float32), nost * 0.8))
        self.ao *= 1 - nost * 0.6
        # wrinkles and folds (age; a hint of expression lines even when young)
        wr = 0.15 + age
        fh = 0.5 + 0.5 * np.sin(f.lat * 150 + self.coarse(lambda q: SM.value3(q, 0.02, self.seed + 51)) * 4)
        h -= r["forehead"] * tex.sstep(0.75, 1.0, fh) * 0.5 * age
        for side in (1, -1):
            crow = f.blob(side * (el + 0.25), et - 0.01, 0.07, 0.08)
            ray = 0.5 + 0.5 * np.sin((f.lat - et + (f.lon - side * (el + 0.2)) * side * 0.5) * 200)
            h -= crow * tex.sstep(0.6, 1.0, ray) * 0.6 * age
            wing = lm["nostril"]
            run = np.clip(wing[1] - 0.01 - f.lat, 0, 0.22)          # from the nose wing past the mouth corner
            nlf = np.exp(-(((f.lon - side * (wing[0] + 0.04 + 0.5 * run)) / 0.02) ** 2))
            nlf *= np.exp(-(((f.lat - wing[1] + 0.1) / 0.1) ** 2))
            h -= nlf * 0.5 * wr
            self.ao *= 1 - nlf * 0.25 * wr
            bag = f.blob(side * el, et - 0.11, 0.13, 0.03)
            h -= bag * 0.4 * age
        self.ao *= 1 - r["mouth_line"] * 0.6
        # lips: vertical lines, wetter centre, defined edge
        lines = 0.5 + 0.5 * np.sin(f.lon * 210 + self.solid(lambda q, i: SM.value3(q, 0.002, self.seed + 61), mask=r["lips"]) * 5)
        h -= r["lips"] * tex.sstep(0.55, 1.0, lines) * 0.35
        wet = np.clip(r["lower_lip"] * np.exp(-((f.lat - lm["lower_lip"] - 0.008) / 0.03) ** 2) * 1.3
                      + r["upper_lip"] * 0.6, 0, 1)
        self.rough -= r["lips"] * 0.12 + wet * (0.18 if fem else 0.08)
        # makeup (heroines): gradient lip tint, soft blush, liner, shadow, aegyo-sal
        mk = self.cfg.get("_makeup", 0.0)
        if mk > 0:
            inner = np.exp(-((f.lon / (lm["mouth_w"] * 0.55)) ** 2) - ((f.lat - lm["lip_line"]) / 0.03) ** 2)
            self.paint.append((tex.srgb(c["lip"]), np.clip(r["lips"] * (0.25 + 0.75 * inner), 0, 1) * 0.8 * mk))
            blush = f.pair(lm["cheek"][0] - 0.08, lm["cheek"][1] + 0.08, 0.2, 0.12)
            self.paint.append((tex.srgb(c["blush"]), blush * 0.28 * mk))
            for side in (1, -1):
                rel = (f.lon - side * el) * side
                lid_line = et + 0.045 * np.cos(np.clip(rel / lm["eye_w"], -1.5, 1.5) * 1.1) + 0.012 * rel
                liner = np.exp(-((f.lat - lid_line) / 0.009) ** 2) * np.exp(-((rel - 0.02) / (lm["eye_w"] * 1.05)) ** 6)
                wing = np.exp(-((rel - lm["eye_w"] * 1.05) / 0.035) ** 2 - ((f.lat - et - 0.035) / 0.01) ** 2)
                self.paint.append((tex.srgb(c["liner"]), np.clip(liner + wing * 0.8, 0, 1) * 0.75 * mk))
                shadow = f.blob(side * el, et + 0.07, lm["eye_w"] * 0.95, 0.04)
                self.paint.append((tex.srgb(c["blush"]) * np.array([0.95, 0.82, 0.78], np.float32),
                                   shadow * 0.25 * mk))
                aegyo = f.blob(side * el, et - 0.06, lm["eye_w"] * 0.8, 0.018)
                self.paint.append((np.array([1.0, 0.9, 0.86], np.float32), aegyo * 0.12 * mk))
            if self.cfg.get("forehead_mark", fem):
                mark = np.exp(-((f.lon / 0.028) ** 2) - ((f.lat - lm["brow"] - 0.18) / 0.055) ** 2)
                self.paint.append((tex.srgb("#b8182b"), np.clip(mark * 1.4, 0, 1)))
        self.height = h

    def compose(self, r, m):
        tone = lin(tex.srgb(self.c["skin"]))
        mel = self.mel[..., None] - 1
        hb = self.hb[..., None] - 1
        col = tone * np.exp(-mel * MELANIN) * np.exp(-hb * HAEMO) * np.exp(-self.ven[..., None] * VENOUS)
        col = col * (1 - 0.35 * m["pore"][..., None] * r["face"][..., None] * 0.3)
        col = srgb_of(col)
        for colour, mask in self.paint:
            col = tex.lerp(col, colour, np.clip(mask, 0, 1))
        # micro relief -> height (pores dip, lines are fine furrows)
        pore_k = 0.35 + 0.65 * np.clip(r["nose"] + r["cheeks"] * 0.8 + r["tzone"] * 0.7, 0, 1)
        h = self.height - m["pore"] * pore_k * 0.55 - m["fine"] * 0.18 - m["lines"] * 0.08 * (1 - r["lips"])
        h += (m["mottle"] - 0.5) * 0.3
        rough = (self.rough - r["tzone"] * 0.1 - r["nose"] * 0.06 + r["cheeks"] * 0.05
                 + m["pore"] * 0.05 + m["lines"] * 0.02 + r["scalp"] * 0.1 + 0.04 * self.age)
        cavity = np.clip(0.5 + (h - SM.blur(h, 3)) * 1.2, 0, 1)
        # surfaces facing down (under the brow ridge, nose and jaw) see less of the sky
        sky = 0.88 + 0.12 * np.clip(self.nrm[..., 2] * 0.5 + 0.5, 0, 1)
        ao = self.ao * (0.75 + 0.25 * cavity) * sky
        return col, np.clip(rough, 0.18, 0.85), np.clip(ao, 0, 1), h

    def run(self):
        r = self.regions()
        m = self.micro(r)
        self.skin_model(r, m)
        self.features(r, m)
        return self.compose(r, m)


def paint_head(cfg, material, head_parts, centre, radii, size, hairline, makeup=0.0, eye_mats=()):
    """Paint the head skin texture into `material`'s images from the head meshes."""
    tris = SM.mesh_triangles(head_parts, {material})
    if tris is None:
        return None
    pos, nrm, cover = SM.rasterize(tris, size)
    pos, nrm = SM.dilate([pos, nrm], cover)
    eyes = []
    for o in head_parts:
        if o.data.vertices and any(m in eye_mats for m in o.data.materials):
            co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices], np.float32)
            eyes.append(co.mean(0))

    def frame_of(p):
        fr = SM.FaceFrame(p, centre, radii)
        return fr.lon, fr.lat
    points = {}
    for o in head_parts:
        points.update({k: tuple(v) for k, v in o.get("face_landmarks", {}).items()})
    lm = landmarks(cfg, eyes if len(eyes) == 2 else None, frame_of, points)
    cfg = dict(cfg, _hairline=hairline, _makeup=makeup)
    painter = FacePainter(pos, nrm, cover, centre, radii, cfg, lm)
    col, rough, ao, h = painter.run()
    # the gutters take the colour of their island edge (no dark seams under mip-mapping)
    col, rough, ao, h = SM.dilate([col, rough, ao, h], cover)
    return col, rough, ao, h


def paint(cfg, mats, head_parts, centre, radii, hairline):
    """Paint the head skin ("Skin"/"face" material) from the built head meshes."""
    mat = mats["Skin"]
    size = int(mat["tex_size"])
    fem, age = cfg["female"], cfg.get("age", 0.0)
    makeup = (1.0 if age < 0.25 else 0.35) if fem else 0.0
    if cfg.get("beard"):
        cfg = dict(cfg, stubble=max(cfg.get("stubble", 0.0), 0.45))
    eye_mats = {mats[k] for k in ("eye", "Eye_Sclera", "Eye_Iris") if k in mats}
    maps = paint_head(cfg, mat, head_parts, centre, radii, size, hairline, makeup, eye_mats)
    if maps is not None:
        paint_face_into(mat, maps, size)


def normal_map(h, strength):
    """Tangent-space normal (OpenGL / glTF convention: +v up) from a height field."""
    return tex.normal_from_height(h, strength)


# --------------------------------------------------------------------------
# body skin (hands, neck, ears on box UVs): tileable
# --------------------------------------------------------------------------
def body(tone, size=512, seed=12, age=0.0):
    """Tileable skin with pores, fine lines and chromophore mottling."""
    u, v = tex.grid(size)
    c = max(8, int(size * 0.18))
    pores = tex.sstep(0.6, 0.85, tex.fbm(size, c, 2, 0.45, seed + 1))
    la = tex.fbm(size, max(4, c // 3), 3, 0.5, seed + 3, stretch=6)
    lb = np.rot90(tex.fbm(size, max(4, c // 3), 3, 0.5, seed + 4, stretch=6))
    lines = np.maximum(1 - np.abs(la - 0.5) * 7, 0) + np.maximum(1 - np.abs(lb - 0.5) * 7, 0) * 0.8
    mottle = tex.fbm(size, 8, 5, 0.55, seed)
    red = tex.fbm(size, 6, 4, 0.5, seed + 2)
    mel = 1 + (mottle - 0.5) * 0.16
    hb = 1 + (red - 0.5) * 0.4
    col = lin(tex.srgb(tone)) * np.exp(-(mel - 1)[..., None] * MELANIN) * np.exp(-(hb - 1)[..., None] * HAEMO)
    col = srgb_of(col * (1 - 0.06 * pores)[..., None])
    h = 0.5 - pores * 0.3 - lines * 0.08 * (1 + age) + mottle * 0.1
    rough = 0.52 + pores * 0.06 + lines * 0.02 + 0.04 * age
    ao = 0.85 + 0.15 * np.clip(0.5 + (h - SM.blur(h, 2)) * 2, 0, 1)
    return col, rough, ao, h


def eyelid(skin_hex, liner_hex, size=64):
    """Eyelid shell: v = 0 at the lid rim (lash line), 1 away from the opening."""
    u, v = tex.grid(size)
    base = srgb_of(lin(tex.srgb(skin_hex)) * np.exp(-0.25 * HAEMO))
    col = tex.lerp(tex.srgb(liner_hex), base, tex.sstep(0.04, 0.18, v))
    return col, np.full((size, size), 0.45, np.float32)


def nail(tone, size=64):
    """Fingernail: pink plate over the nail bed, lighter free edge (v = 1), lunula."""
    u, v = tex.grid(size)
    bed = srgb_of(lin(tex.srgb(tone)) * np.exp(-0.9 * HAEMO))
    col = tex.lerp(bed, np.array([0.95, 0.91, 0.87], np.float32), tex.sstep(0.8, 0.95, v))
    col = tex.lerp(col * 1.06, col, tex.sstep(0.0, 0.22, v))
    ridges = 0.5 + 0.5 * np.sin(u * math.pi * 14)
    return col, np.full((size, size), 0.28, np.float32), ridges * 0.1


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def face_material(name, tone_hex, size):
    """Head skin material with placeholder images, painted later by paint_face_into()."""
    flat = np.broadcast_to(tex.srgb(tone_hex), (8, 8, 3)).astype(np.float32)
    alb = skin_shading.image(name + "_albedo", flat)
    orm = skin_shading.image(name + "_orm", skin_shading.orm(np.ones((8, 8)), np.full((8, 8), 0.5)), data=True)
    nrm = skin_shading.image(name + "_normal", np.broadcast_to(np.array([0.5, 0.5, 1.0], np.float32), (8, 8, 3)),
                             data=True)
    mat = skin_shading.skin_material(name, alb, orm, nrm, normal_strength=1.0)
    mat["tex_size"] = size
    return mat


def paint_face_into(mat, maps, size, normal_strength=1.6):
    """Write painted maps into the face material's images.

    Albedo at full size; ORM and the normal map at half size (the normal is derived at
    full size and then averaged down, so pores still tilt the shading on average while
    the JPEG in the GLB stays small - noise-like normal detail compresses badly).
    """
    col, rough, ao, h = maps
    imgs = {n.image.name: n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE"}
    half = max(256, size // 2)
    nrm = skin_shading.resize(normal_map(h, normal_strength) * 2 - 1, half)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-6)
    skin_shading.fill_image(imgs[mat.name + "_albedo"], col)
    skin_shading.fill_image(imgs[mat.name + "_orm"],
                            skin_shading.orm(skin_shading.resize(ao, half), skin_shading.resize(rough, half)))
    skin_shading.fill_image(imgs[mat.name + "_normal"], nrm * 0.5 + 0.5)


def body_material(name, tone_hex, size=512, age=0.0):
    col, rough, ao, h = body(tone_hex, size, age=age)
    return skin_shading.skin_material(
        name, skin_shading.image(name + "_albedo", col),
        skin_shading.image(name + "_orm", skin_shading.orm(ao, rough), data=True),
        skin_shading.image(name + "_normal", normal_map(h, 1.2), data=True), normal_strength=0.8)


def eyelid_material(name, skin_hex, liner_hex):
    col, rough = eyelid(skin_hex, liner_hex)
    return skin_shading.skin_material(name, skin_shading.image(name + "_albedo", col),
                                      skin_shading.image(name + "_orm", skin_shading.orm(np.ones_like(rough), rough),
                                                         data=True), None, sss=0.6, oil=0.0)


def nail_material(name, tone_hex):
    col, rough, h = nail(tone_hex)
    return skin_shading.simple_material(
        name, skin_shading.image(name + "_albedo", col),
        skin_shading.image(name + "_orm", skin_shading.orm(np.ones_like(rough), rough), data=True),
        skin_shading.image(name + "_normal", normal_map(h, 0.6), data=True), normal_strength=0.3, coat=0.3)

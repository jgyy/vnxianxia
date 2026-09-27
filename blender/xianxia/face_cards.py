"""Hair cards for the eyelashes and eyebrows (head millimetres).

Eyelashes grow in clumps from the lash line (the anterior lid margin loop of
``face_eyes``): upper lashes leave the lid almost perpendicular, sweep forward
and curl upward, longest over the lateral third; lower lashes are short, sparse
and point down.  ``lash_points(lids, state)`` is a pure function of the lid
state, so blink / squint / look shape keys regenerate the lashes exactly where
the lid margin goes.

Brows are ~80 (women) / ~108 (men) short cards per side scattered over the brow band (head ->
peak -> tail from the landmarks): hairs at the head stand up and lean
laterally, the body lies at 20-30 deg, the tail points down and out, and the
upper-edge hairs angle downward to make the natural herringbone.  Each card
hugs the skin (projected on the sculpted surface) with a slight lift.

Card UVs: u runs along the lid / brow (each card takes the slice of the
strip texture at its position), v from the root (0) to the tip (1).
"""
import math
import random

import numpy as np

from . import face_chart as fc
from . import face_landmarks as fl
from .face_eyes import EyeLids

LASH_SEGS = 4
BROW_SEGS = 3


def _lash_layout(p: fl.FaceParams, side):
    """Deterministic clump parameters: (s, length, width, splay, curl) for upper and lower lashes."""
    rng = random.Random(p.seed * 7 + (1 if side > 0 else 2))
    out = []
    n_up, n_lo = 32, 15
    for k in range(n_up):
        s = 0.035 + 0.43 * (k + rng.uniform(0.2, 0.8)) / n_up          # lateral -> medial along the upper lid
        t_fis = 1.0 - 2.0 * s                                           # 1 lateral .. 0 medial
        base = (8.6 if p.fem else 7.0) * (1.0 - 0.3 * p.age)
        length = base * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.15 + 0.95 * t_fis)) ** 0.8)
        length *= rng.uniform(0.85, 1.08)
        out.append(dict(s=s, upper=True, length=length, width=rng.uniform(0.55, 0.75),
                        splay=rng.uniform(-0.12, 0.12) + 0.35 * (t_fis - 0.5),
                        curl=(1.05 if p.fem else 0.7) * rng.uniform(0.85, 1.1)))
    for k in range(n_lo):
        s = 0.58 + 0.36 * (k + rng.uniform(0.2, 0.8)) / n_lo
        t_fis = 2.0 * (s - 0.5)
        length = (3.6 if p.fem else 3.0) * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t_fis * 1.1))) * rng.uniform(0.8, 1.1)
        out.append(dict(s=s, upper=False, length=length, width=rng.uniform(0.35, 0.5),
                        splay=rng.uniform(-0.1, 0.1) + 0.25 * (t_fis - 0.5), curl=0.25))
    return out


def lash_points(lids: EyeLids, state=None):
    """Card vertices (N, 3) head mm, plus per-vertex (s, t root -> tip, u along the lid)."""
    p = lids.p
    layout = _lash_layout(p, lids.side)
    s_all = np.array([c["s"] for c in layout])
    u, w, upper, (nu, nw) = lids.loop(s_all, state)
    tab = lids.ring_table(s_all, upper)
    off, th = tab[EyeLids.LASH_RING]
    ru, rw = u + nu * off, w + nw * off
    roots = lids.to_head(ru, rw, lids.lid_y(ru, rw, th))
    # a second, slightly offset point gives the margin tangent in 3-D
    u2, w2, _, (nu2, nw2) = lids.loop(s_all + 0.004, state)
    ru2, rw2 = u2 + nu2 * off, w2 + nw2 * off
    roots2 = lids.to_head(ru2, rw2, lids.lid_y(ru2, rw2, th))
    c = lids.c
    verts, meta = [], []
    for k, cl in enumerate(layout):
        r = roots[k]
        tang = roots2[k] - r
        tang /= np.linalg.norm(tang) + 1e-9
        radial = (r - c) / (np.linalg.norm(r - c) + 1e-9)
        up = np.array([0.0, 0.0, 1.0 if cl["upper"] else -1.0])
        grow = radial * 0.3 + up * 0.12 + np.array([0.0, -0.85, 0.0])      # out of the lid, mostly forward
        grow += tang * cl["splay"]
        grow /= np.linalg.norm(grow)
        L = cl["length"]
        for j in range(LASH_SEGS + 1):
            t = j / LASH_SEGS
            # sweep forward, then curl up (upper) / down (lower)
            q = r + grow * L * t + up * L * cl["curl"] * 0.55 * t * t
            half = 0.5 * cl["width"] * (1.0 - 0.35 * t)
            for sd in (-1, 1):
                verts.append(q + tang * half * sd)
                along = (cl["s"] - 0.035) / 0.43 if cl["upper"] else (cl["s"] - 0.58) / 0.36
                meta.append((cl["s"], t, along + 0.022 * sd))
    return np.array(verts), np.array(meta)


def lash_faces(n_cards):
    """Quad indices for n_cards lash cards laid out by lash_points."""
    faces = []
    per = (LASH_SEGS + 1) * 2
    for c in range(n_cards):
        b = c * per
        for j in range(LASH_SEGS):
            a0, a1 = b + 2 * j, b + 2 * j + 1
            b0, b1 = a0 + 2, a1 + 2
            faces.append((a0, a1, b1, b0))
    return faces


def lash_count(p: fl.FaceParams, side):
    return len(_lash_layout(p, side))


# --------------------------------------------------------------------------
# brows
# --------------------------------------------------------------------------
def brow_band(p: fl.FaceParams):
    """The brow in the frontal plane (left side): centre(t) -> (|x|, z) and half_h(t), t = 0 head .. 1 tail."""
    L = fl.landmarks(p)
    head, peak, tail = L["brow_head.L"], L["brow_peak.L"], L["brow_tail.L"]
    ctrl = [(abs(head[0]), head[2] + 1.0), (abs(peak[0]), peak[2]), (abs(tail[0]), tail[2])]

    def centre(t):
        if t < 0.66:
            a, b, q = ctrl[0], ctrl[1], t / 0.66
        else:
            a, b, q = ctrl[1], ctrl[2], (t - 0.66) / 0.34
        x = a[0] + (b[0] - a[0]) * q
        z = a[1] + (b[1] - a[1]) * q
        # soft arch: the straight Korean brow bends only a little
        z += p.brow_arch * 1.5 * math.sin(math.pi * min(1.0, t / 0.9))
        return x, z

    def half_h(t):
        th = p.brow_thick * 0.5
        return th * (1.05 - 0.2 * t) * (1.0 if t < 0.72 else max(0.25, 1.0 - (t - 0.72) / 0.28 * 0.75))
    return centre, half_h


def brow_cards(p: fl.FaceParams, surf, side):
    """Brow hair cards: (verts (N,3) head mm, faces, uv list per vertex)."""
    centre, half_h = brow_band(p)
    rng = random.Random(p.seed * 13 + (5 if side > 0 else 9))

    n = int(96 * (1.0 + 0.2 * (not p.fem)) * (1 - 0.25 * p.age))
    cards = []                       # per card: list of (x, z, lift), width
    for k in range(n):
        t = min(0.999, (k + rng.random()) / n) ** 1.05
        x, z = centre(t)
        v = rng.uniform(-1.0, 1.0)
        z += v * half_h(t) * 0.9
        x += rng.uniform(-0.6, 0.6)
        # hair direction (in the frontal plane, x = lateral): up at the head, flat, then down at the tail
        base_ang = 75.0 * (1 - min(1.0, t / 0.28)) + 22.0 * min(1.0, t / 0.28) - 38.0 * max(0.0, (t - 0.6) / 0.4)
        base_ang -= 22.0 * v * min(1.0, t / 0.2)        # upper-edge hairs lean down, lower-edge up (herringbone)
        ang = math.radians(base_ang + rng.uniform(-8, 8))
        d2 = (math.cos(ang), math.sin(ang))
        length = (4.6 if p.fem else 6.8) * (1.0 - 0.25 * t) * rng.uniform(0.8, 1.15)
        pts = []
        for j in range(BROW_SEGS + 1):
            q = j / BROW_SEGS
            lift = 0.25 + 0.55 * math.sin(math.pi * min(1.0, q * 0.9)) - 0.25 * q * q
            pts.append((side * (x + d2[0] * length * q), z + d2[1] * length * q, lift))
        cards.append((pts, rng.uniform(0.7, 1.0), t))
    # put every hair point on the real sculpted surface (cast from the head centre), lifted along the ray
    flat = np.array([q for pts, _, _ in cards for q in pts])
    guess = np.stack([flat[:, 0], surf.front_y(flat[:, 0], flat[:, 1]), flat[:, 1]], axis=-1)
    lon, b = fc.chart_of_points(guess)
    hit, t_hit = fc.cast(surf.F, lon, b)
    ray = (hit - fc.ORIGIN) / np.maximum(t_hit, 1e-6)[:, None]
    surf_pts = hit + ray * flat[:, 2:3]
    verts, faces, uvs = [], [], []
    per = BROW_SEGS + 1
    for c, (_, width, tb) in enumerate(cards):
        pts = surf_pts[c * per:(c + 1) * per]
        b0 = len(verts)
        for j, q3 in enumerate(pts):
            tv = pts[min(j + 1, BROW_SEGS)] - pts[max(j - 1, 0)]
            tv /= np.linalg.norm(tv) + 1e-9
            wdir = np.cross(tv, np.array([0.0, -1.0, 0.0]))
            wdir /= np.linalg.norm(wdir) + 1e-9
            half = 0.5 * width * (1 - 0.5 * j / BROW_SEGS)
            verts.append(q3 - wdir * half)
            verts.append(q3 + wdir * half)
            uvs.append((tb - 0.02, j / BROW_SEGS))
            uvs.append((tb + 0.02, j / BROW_SEGS))
        for j in range(BROW_SEGS):
            a0, a1 = b0 + 2 * j, b0 + 2 * j + 1
            faces.append((a0, a1, a1 + 2, a0 + 2))
    return np.array(verts), faces, uvs

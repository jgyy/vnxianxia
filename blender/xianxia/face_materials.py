"""Default materials for the face slots that the skin workstream may override.

``face_slots(cfg, mats)`` returns {slot name: material}.  If ``mats`` (from
characters.make_materials) already holds a material under a slot name it is
used as-is, so skin / eye texture work can target these names:

    Eye_Sclera  Eye_Iris  Eye_Cornea  Eye_Tearline  Teeth  Tongue
    Mouth_Inner  Lashes  Brows

UV conventions (see face_eyes / face_mouth / face_cards):
* Eye_Sclera - azimuthal around the visual axis: uv = 0.5 + 0.5*(angle/pi)*(cos, sin);
* Eye_Iris   - planar polar: limbus = circle r 0.5 about (0.5, 0.5), pupil edge
  at r = 0.5 * PUPIL / LIMBUS (~0.16);
* Lashes / Brows - one card per clump: u across the card, v from root (0) to tip (1);
* Teeth / Tongue / Mouth_Inner - flat colour is enough (they live in shadow).

The textures here are small procedural defaults (numpy), not the skin
workstream's job; they only make the head read correctly on its own.
"""
import math

import numpy as np

from . import face_eyes, tex, util

SLOTS = ("Eye_Sclera", "Eye_Iris", "Eye_Cornea", "Eye_Tearline", "Teeth", "Tongue", "Mouth_Inner", "Lashes",
         "Brows")


def _grid(n):
    v, u = np.mgrid[0:n, 0:n].astype(np.float32)
    return (u + 0.5) / n, (v + 0.5) / n


def _noise(n, cells, seed, octaves=3):
    return tex.fbm(n, cells, octaves, 0.5, seed)


def iris_maps(color, glow=None, n=512, seed=3):
    """Iris: radial fibres, crypts, a lighter collarette, a dark limbal ring, the pupil."""
    u, v = _grid(n)
    x, y = (u - 0.5) * 2, (v - 0.5) * 2
    r = np.hypot(x, y)                         # 1 = limbus
    a = np.arctan2(y, x)
    base = tex.srgb(color)
    pr = face_eyes.PUPIL / face_eyes.LIMBUS
    t = np.clip((r - pr) / (1 - pr), 0, 1)      # 0 at the pupil edge .. 1 at the limbus
    n1 = _noise(n, 24, seed)
    fib = 0.5 + 0.5 * np.sin(a * 90 + n1 * 9) * np.sin(a * 37 + 1.3)
    streak = 0.55 + 0.45 * fib * (0.6 + 0.4 * _noise(n, 64, seed + 1, 2))
    crypt = (_noise(n, 40, seed + 2, 2) > 0.66) * np.exp(-((t - 0.45) / 0.25) ** 2)
    col = base[None, None, :] * (0.55 + 0.75 * t ** 0.8)[..., None] * streak[..., None]
    collar = np.exp(-((t - 0.28) / 0.07) ** 2) * (0.7 + 0.3 * np.sin(a * 11 + n1 * 4))
    col = tex.lerp(col, np.minimum(base * 2.0 + 0.1, 1.0), collar * 0.45)
    col = col * (1 - 0.35 * crypt)[..., None]
    limbal = tex.sstep(0.82, 0.97, t)
    col = tex.lerp(col, base * 0.18, limbal * 0.85)
    pupil = 1 - tex.sstep(pr - 0.02, pr + 0.015, r)
    col = tex.lerp(col, np.array([0.008, 0.008, 0.01], np.float32), pupil)
    col = tex.lerp(col, np.array([0.9, 0.86, 0.82], np.float32), tex.sstep(1.0, 1.02, r))
    out = tex.result(col.astype(np.float32), 0.08, 0.0, (streak * 0.3 + 0.35 * (1 - t)).astype(np.float32))
    if glow:
        out["emission"] = (tex.srgb(glow)[None, None, :] * ((1 - pupil) * (1 - limbal) * streak)[..., None]
                           ).astype(np.float32)
    return out


def sclera_maps(n=256, seed=7):
    """Sclera: warm white, pinker toward the corners, a few fine vessels."""
    u, v = _grid(n)
    r = np.hypot(u - 0.5, v - 0.5) * 2      # 0 = visual axis, 1 = back of the eye
    col = np.ones((n, n, 3), np.float32) * np.array([0.93, 0.9, 0.87], np.float32)
    col = tex.lerp(col, np.array([0.9, 0.78, 0.74], np.float32), tex.sstep(0.25, 0.6, r) * 0.6)
    ves = tex.sstep(0.63, 0.7, _noise(n, 20, seed, 4)) * tex.sstep(0.22, 0.5, r)
    col = tex.lerp(col, np.array([0.75, 0.3, 0.3], np.float32), ves * 0.45)
    return tex.result(col, 0.1, 0.0, None)


def strand_maps(color, n=128, strands=3, seed=11, taper=0.9):
    """Alpha texture for hair cards: a few tapered strands running along v."""
    u, v = _grid(n)
    rng = np.random.default_rng(seed)
    alpha = np.zeros((n, n), np.float32)
    shade = np.zeros((n, n), np.float32)
    for k in range(strands):
        c = (k + 0.5) / strands + rng.uniform(-0.08, 0.08)
        bend = rng.uniform(-0.08, 0.08)
        w = rng.uniform(0.26, 0.34) / strands * 3
        cx = c + bend * v ** 2
        width = w * (1 - taper * v) * 0.5
        d = np.abs(u - cx) / np.maximum(width, 1e-4)
        a = np.clip(1.3 - d, 0, 1) * tex.sstep(0.0, 0.04, v) * (1 - tex.sstep(0.9, 1.0, v))
        alpha = np.maximum(alpha, a)
        shade = np.maximum(shade, a * (0.7 + 0.3 * np.cos(np.clip(d, 0, 1) * math.pi / 2)))
    c = tex.srgb(color)
    col = c[None, None, :] * (0.7 + 0.5 * shade)[..., None] * (1.0 + 0.25 * v)[..., None]
    return tex.result(np.clip(col, 0, 1).astype(np.float32), 0.45, 0.0, None), alpha


def face_slots(cfg, mats):
    """{slot: material} for the head, creating defaults for slots missing from mats."""
    c = cfg["colors"]
    out = {}

    def get(name, make):
        out[name] = mats.get(name) or make()

    get("Eye_Sclera", lambda: util.material("Eye_Sclera", sclera_maps(), normal_strength=0.0))
    iris = iris_maps(c["iris"], cfg.get("eye_glow"))
    get("Eye_Iris", lambda: util.material("Eye_Iris", iris, normal_strength=0.3, normal_bump=1.0,
                                          emission_map=iris.get("emission"), emission_strength=4.0))
    get("Eye_Cornea", lambda: util.material("Eye_Cornea", color="#ffffff", rough=0.02, alpha=0.06))
    get("Eye_Tearline", lambda: util.material("Eye_Tearline", color="#f4dcd6", rough=0.03, alpha=0.3))
    get("Teeth", lambda: util.material("Teeth", color="#e9e3d6", rough=0.28))
    get("Tongue", lambda: util.material("Tongue", color="#b4555c", rough=0.45))
    get("Mouth_Inner", lambda: util.material("Mouth_Inner", color="#b4646a", rough=0.3))
    lash, la = strand_maps(c.get("liner", c["brow"]), seed=11, strands=3, taper=0.95)
    lash["albedo"] *= 0.6
    lash["rough"][:] = 0.65
    get("Lashes", lambda: util.material("Lashes", lash, alpha=la, normal_strength=0.0, double_sided=True))
    brow, ba = strand_maps(c["brow"], seed=13, strands=3, taper=0.85)
    get("Brows", lambda: util.material("Brows", brow, alpha=ba, normal_strength=0.0, double_sided=True))
    for name in ("Lashes", "Brows"):              # hair cards: no plastic sheen
        b = next((n for n in out[name].node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b is not None and not mats.get(name):
            b.inputs["Specular IOR Level"].default_value = 0.15
    return out

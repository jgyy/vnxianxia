"""Eye, mouth and facial-hair-card materials.

UV conventions (for the head meshes that use these slots):
  Eye_Iris     square polar map: UV (0.5, 0.5) = pupil centre, UV radius 0.5 = limbus.
  Eye_Sclera   square polar map: UV (0.5, 0.5) = visual axis, UV radius 0.5 = 90 degrees
               from it (the eye's equator); the iris area in the middle is painted too so
               a single-sphere eye can use this texture alone.
  eye (legacy) UV-sphere eye whose v = 1 pole faces forward (current head).
  Lashes/Brows alpha-tested cards: u along the lid / brow, v root (0) -> tip (1).
  Teeth/Tongue any UVs (texture is nearly uniform, detail is fine noise).
  Eye_Cornea / Eye_Tearline untextured wet films (alpha blended, very low roughness).

The iris follows real anatomy seen in macro photographs: radial trabecular fibres,
Fuchs' crypts near the collarette, a lighter zig-zag collarette ring (hazel / amber in
dark brown eyes), contraction furrows in the ciliary zone and a dark limbal ring.
The sclera is warm off-white, pinker toward the canthi, with fine branching vessels
that thin out toward the cornea.
"""
import math

import numpy as np

from . import hair_tex, skin_shading, tex

IRIS_R = 0.13          # angular radius of the iris on the legacy sphere map (v units)
PUPIL = 0.3            # pupil radius as a fraction of the iris radius


def _polar(size):
    u, v = tex.grid(size)
    x, y = u - 0.5, v - 0.5
    return np.sqrt(x * x + y * y) * 2, np.arctan2(y, x)


def _ang_noise(theta, rho, freq, seed, rings=4):
    """Noise periodic in theta: random smooth values on a (freq x rings) polar lattice."""
    rng = np.random.default_rng(seed)
    g = rng.random((rings + 2, freq)).astype(np.float32)
    a = (theta / (2 * math.pi) % 1.0) * freq
    r = np.clip(rho, 0, 1) * rings
    a0, r0 = np.floor(a).astype(int), np.floor(r).astype(int)
    fa, fr = a - a0, r - r0
    fa, fr = fa * fa * (3 - 2 * fa), fr * fr * (3 - 2 * fr)
    a1 = (a0 + 1) % freq
    a0 %= freq
    top = g[r0, a0] * (1 - fa) + g[r0, a1] * fa
    bot = g[r0 + 1, a0] * (1 - fa) + g[r0 + 1, a1] * fa
    return top * (1 - fr) + bot * fr


def iris_rt(rho, theta, iris_hex, seed=3, glow=None):
    """Iris colour / height at normalised radius rho (0 centre .. 1 limbus) and angle theta."""
    base = tex.srgb(iris_hex)
    hazel = np.clip(base * np.array([2.3, 1.9, 1.1], np.float32) + np.array([0.08, 0.05, 0.0], np.float32), 0, 1)
    dark = base * 0.45
    fib = sum(_ang_noise(theta, rho, f, seed + k, 6) * w for k, (f, w) in enumerate(((180, 0.5), (90, 0.3), (40, 0.2))))
    fib = np.clip((fib - 0.5) * 2.2 + 0.5, 0, 1)
    coll_r = 0.5 + 0.05 * np.sin(theta * 13 + _ang_noise(theta, rho, 20, seed + 7) * 4)
    collar = np.exp(-((rho - coll_r) / 0.06) ** 2)
    inner = tex.sstep(coll_r, coll_r - 0.12, rho)                     # pupillary zone
    col = tex.lerp(base, hazel, np.clip(inner * 0.45 + collar * 0.35, 0, 1) * (0.55 + 0.45 * fib))
    col = col * (0.72 + 0.5 * fib)[..., None]
    crypt_n = _ang_noise(theta, rho, 24, seed + 11, 8)
    crypts = tex.sstep(0.72, 0.85, crypt_n) * np.exp(-((rho - coll_r - 0.1) / 0.1) ** 2)
    col = tex.lerp(col, dark * 0.6, crypts * 0.7)
    furrow = tex.sstep(0.6, 1.0, 0.5 + 0.5 * np.sin(rho * 60 + _ang_noise(theta, rho, 12, seed + 13) * 3))
    col = col * (1 - 0.15 * furrow * tex.sstep(0.6, 0.8, rho))[..., None]
    limbal = tex.sstep(0.78, 1.0, rho)
    col = tex.lerp(col, dark * 0.35, limbal * 0.85)
    pupil = 1 - tex.sstep(PUPIL - 0.02, PUPIL + 0.015, rho)
    col = tex.lerp(col, np.array([0.012, 0.01, 0.012], np.float32), pupil)
    height = fib * 0.25 * (1 - pupil) - crypts * 0.3 + collar * 0.25
    emit = None
    if glow:
        emit = (tex.srgb(glow)[None, None, :] * ((1 - pupil) * (1 - limbal) * (0.5 + 0.6 * fib))[..., None])
    return np.clip(col, 0, 1), height, emit


def sclera_rt(rho_eq, theta, seed=5):
    """Sclera colour at angular distance rho_eq (0 = visual axis, 1 = 90 degrees)."""
    base = np.array([0.93, 0.9, 0.86], np.float32)
    col = np.broadcast_to(base, rho_eq.shape + (3,)).astype(np.float32)
    corners = np.abs(np.cos(theta)) ** 3                             # toward the canthi
    col = tex.lerp(col, np.array([0.9, 0.72, 0.68], np.float32), corners * tex.sstep(0.25, 0.8, rho_eq) * 0.45)
    col = tex.lerp(col, np.array([0.92, 0.86, 0.72], np.float32), tex.sstep(0.5, 1.0, rho_eq) * 0.4)
    v1 = _ang_noise(theta, rho_eq, 50, seed, 10)
    v2 = _ang_noise(theta, rho_eq, 110, seed + 1, 16)
    veins = (np.maximum(1 - np.abs(v1 - 0.5) * 18, 0) + 0.6 * np.maximum(1 - np.abs(v2 - 0.5) * 22, 0))
    veins = veins * tex.sstep(0.3, 0.85, rho_eq)
    col = tex.lerp(col, np.array([0.72, 0.22, 0.2], np.float32), np.clip(veins, 0, 1) * 0.55)
    return col


def iris_texture(iris_hex, size=512, glow=None):
    rho, theta = _polar(size)
    col, h, emit = iris_rt(rho, theta, iris_hex, glow=glow)
    return col, h, emit


def sclera_texture(iris_hex, size=512):
    """Polar sclera (equator at the edge) with the iris painted in the middle."""
    rho, theta = _polar(size)
    col = sclera_rt(np.clip(rho, 0, 1.2), theta)
    ir = IRIS_R * 2 / 1.0        # iris angular radius in rho units (90 deg = 1 = 0.5 v on the sphere)
    icol, ih, _ = iris_rt(rho / ir, theta, iris_hex)
    m = 1 - tex.sstep(ir * 0.97, ir * 1.03, rho)
    return tex.lerp(col, icol, m), ih * m


def sphere_eye_texture(iris_hex, size=512, glow=None):
    """Legacy UV-sphere eye: v = 1 pole forward, u around the axis."""
    u, v = tex.grid(size)
    r = 1.0 - v
    theta = u * 2 * math.pi
    col = sclera_rt(r * 2, theta)
    icol, h, emit = iris_rt(r / IRIS_R, theta, iris_hex, glow=glow)
    m = 1 - tex.sstep(IRIS_R * 0.97, IRIS_R * 1.03, r)
    col = tex.lerp(col, icol, m)
    rough = tex.lerp(0.3, 0.12, m)
    if emit is not None:
        emit = emit * m[..., None]
    return col, rough, h * m, emit


def teeth_texture(size=256, seed=7):
    u, v = tex.grid(size)
    n = tex.fbm(size, 8, 3, 0.5, seed)
    enamel = np.array([0.93, 0.9, 0.82], np.float32)
    col = tex.lerp(enamel * 0.92, enamel, n)
    edge = 0.5 + 0.5 * np.cos(u * 2 * math.pi * 8)                # darker gaps between teeth
    col = col * (1 - 0.18 * tex.sstep(0.85, 1.0, edge))[..., None]
    col = tex.lerp(col, np.array([0.8, 0.83, 0.86], np.float32), tex.sstep(0.8, 1.0, v) * 0.35)   # translucent tips
    return col, np.full((size, size), 0.22, np.float32) + n * 0.06, n * 0.2


def tongue_texture(size=256, seed=8):
    u, v = tex.grid(size)
    pap = tex.sstep(0.55, 0.8, tex.fbm(size, 48, 2, 0.5, seed))
    base = np.array([0.72, 0.33, 0.33], np.float32)
    col = tex.lerp(base, base * np.array([1.1, 1.25, 1.2], np.float32), pap * 0.5)
    mid = np.exp(-((u - 0.5) / 0.03) ** 2)                            # median groove
    col = col * (1 - 0.2 * mid)[..., None]
    return col, 0.42 + 0.15 * pap, pap * 0.4 - mid * 0.3


def strand_card_texture(colour_hex, size=256, count=60, curl=0.25, seed=17, length=(0.6, 1.0), radius=1.4):
    """Alpha strip of curved, tapered hairs (lashes / brows): u along the edge, v root->tip."""
    rng = np.random.default_rng(seed)
    cv = hair_tex.Canvas(size, size)
    v = (np.arange(size, dtype=np.float32) + 0.5) / size
    c = tex.srgb(colour_hex)
    for _ in range(count):
        x0 = rng.uniform(0.04, 0.96) * size
        L = rng.uniform(*length)
        bend = curl * size * rng.uniform(0.6, 1.3) * (1 if x0 > size / 2 else -1) * 0.3
        xs = x0 + bend * (v / L) ** 2
        rad = radius * (size / 256) * (1 - 0.8 * tex.sstep(0.3 * L, L, v))
        op = tex.sstep(0.0, 0.03, v) * (1 - tex.sstep(L * 0.9, L, v))
        colv = np.broadcast_to(c * rng.uniform(0.8, 1.2), (size, 3)).astype(np.float32)
        cv.strand(xs.astype(np.float32), v, rad.astype(np.float32), op.astype(np.float32), colv, rng.random(),
                  rng.random())
    a = cv.alpha
    col = cv.col / np.maximum(a, 1e-4)[..., None]
    col = np.where((a > 0.01)[..., None], col, c)
    return np.concatenate([col, a[..., None]], -1)


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def _img(name, arr, data=False):
    return skin_shading.image(name, arr, data)


def materials(prefix, colors, glow=None, eye_size=512):
    """All eye / mouth / lash / brow materials of a character (dict keyed by slot name)."""
    m = {}
    iris = colors["iris"]
    col, rough, h, emit = sphere_eye_texture(iris, eye_size, glow)
    m["eye"] = skin_shading.simple_material(
        prefix + "eye", _img(prefix + "eye_albedo", col),
        _img(prefix + "eye_orm", skin_shading.orm(np.ones_like(rough), rough), True),
        _img(prefix + "eye_normal", tex.normal_from_height(h, 1.0), True), normal_strength=0.4,
        emission_img=_img(prefix + "eye_emit", emit) if emit is not None else None, emission_strength=3.0,
        coat=1.0, sss=0.3, sss_radius=(1.0, 0.5, 0.35), sss_scale=0.001)
    col, h, emit = iris_texture(iris, eye_size, glow)
    # the iris lies under the aqueous humour: its own surface is matte (the gloss is the
    # cornea's); a specular iris washes a dark brown iris out to grey under a soft key light
    rough = np.full(h.shape, 0.7, np.float32)
    m["Eye_Iris"] = skin_shading.simple_material(
        prefix + "eye_iris", _img(prefix + "eye_iris_albedo", col),
        _img(prefix + "eye_iris_orm", skin_shading.orm(np.ones_like(rough), rough), True),
        _img(prefix + "eye_iris_normal", tex.normal_from_height(h, 1.5), True), normal_strength=0.6, spec=0.05,
        emission_img=_img(prefix + "eye_iris_emit", emit) if emit is not None else None, emission_strength=3.0)
    col, h = sclera_texture(iris, eye_size)
    rough = np.full(h.shape, 0.3, np.float32)
    m["Eye_Sclera"] = skin_shading.simple_material(
        prefix + "eye_sclera", _img(prefix + "eye_sclera_albedo", col),
        _img(prefix + "eye_sclera_orm", skin_shading.orm(np.ones_like(rough), rough), True),
        None, sss=0.4, sss_radius=(1.0, 0.45, 0.3), sss_scale=0.002)
    m["Eye_Cornea"] = skin_shading.film_material(prefix + "eye_cornea", "#000000", 0.1, rough=0.02)
    m["Eye_Tearline"] = skin_shading.film_material(prefix + "eye_tearline", "#e8d0cc", 0.35, rough=0.04, ior=1.33)
    col, rough, h = teeth_texture()
    m["Teeth"] = skin_shading.simple_material(
        prefix + "teeth", _img(prefix + "teeth_albedo", col),
        _img(prefix + "teeth_orm", skin_shading.orm(np.ones_like(rough), rough), True),
        _img(prefix + "teeth_normal", tex.normal_from_height(h, 0.8), True), normal_strength=0.3,
        sss=0.35, sss_radius=(1.0, 0.8, 0.6), sss_scale=0.001, spec=0.6)
    col, rough, h = tongue_texture()
    m["Tongue"] = skin_shading.simple_material(
        prefix + "tongue", _img(prefix + "tongue_albedo", col),
        _img(prefix + "tongue_orm", skin_shading.orm(np.ones_like(rough), rough), True),
        _img(prefix + "tongue_normal", tex.normal_from_height(h, 1.0), True), normal_strength=0.5,
        sss=0.6, sss_radius=(1.0, 0.3, 0.2), sss_scale=0.003)
    # a card is one mascara'd clump ~0.65 mm wide: a few lashes ~0.07 mm thick, dense at the
    # root; hair-thin strands (the old 70 x 1.3 px) averaged with the skin into a brown haze
    lash = strand_card_texture(colors["liner"], 256, 34, curl=0.35, seed=19, length=(0.55, 1.0), radius=4.2)
    m["Lashes"] = skin_shading.simple_material(prefix + "lashes", _img(prefix + "lashes_albedo", lash),
                                               double_sided=True, alpha_cutoff=0.35, spec=0.12)
    brow = strand_card_texture(colors["brow"], 256, 60, curl=0.15, seed=23, length=(0.4, 0.95), radius=2.4)
    m["Brows"] = skin_shading.simple_material(prefix + "brows", _img(prefix + "brows_albedo", brow),
                                              double_sided=True, alpha_cutoff=0.35, spec=0.15)
    return m

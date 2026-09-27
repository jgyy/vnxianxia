"""Procedural hair-card texture atlas.

Real-time hair is a stack of alpha-tested ribbons ("cards"), each textured with a
strip of rendered strands.  This module paints such an atlas with numpy:

* Vertical strips, one per card type (dense base clumps, medium clumps, see-through
  wisps, pointed tip clumps, flyaways, coarse beard hair).  Inside a strip the
  texture v runs root (v = 0, row 0) to tip (v = 1); u runs across the card.
* Every strand is an anti-aliased curve with its own root position, length, taper,
  waviness, depth, colour jitter and a clump attractor pulling the tips together.
  Strands are composited back to front, producing
    colour  - root-to-tip gradient (roots darker, sun-faded tips), per-strand hue/value
              jitter, optional salt-and-pepper greys,
    alpha   - strand coverage with tapered tips,
    normal  - each strand shaded as a tiny cylinder (x across the strand) plus its flow,
    flow    - local strand direction (drives the Cycles anisotropy rotation),
    depth   - front/back position of the top-most strand -> ambient occlusion,
    id      - a random value per strand (roughness and colour variation).
* Transparent texels get the dilated colour of nearby strands so mip-mapping and
  bilinear filtering never bleed black halos into the card edges.

Hair references (candid / HD photographs, grooming guides and real-time hair
breakdowns) the look is based on:
  - Marschner et al. 2003 "Light Scattering from Human Hair Fibers" (R lobe white and
    shifted toward the root, TRT lobe tinted and shifted toward the tip);
    Kajiya & Kay 1989 (tangent-based anisotropic highlight);
  - realtimehair.com "8 techniques to create textures for real-time hair" and
    ArtStation "Real-time hair creation workflow" (M. Zatorska): atlas of strips with
    alpha, root-tip gradient, ID, AO/depth and flow maps; alpha clip, not blend;
  - Korean salon guides on see-through bangs, the hush cut, comma hair and two-block
    cuts (miinhair.com, kyliestudiosalon.com, forteseries.com): wispy sparse fringes,
    layered face-framing pieces, volume at the crown, clean short sides for men.
  In candid photos even the glossiest black hair shows warm brown in the light,
  separate clumps with gaps, a few stray flyaways and uneven tips.
"""
import math
from dataclasses import dataclass

import numpy as np

from . import skin_shading, tex


@dataclass(frozen=True)
class Strip:
    name: str
    width: float      # fraction of the atlas width
    strands: int      # strands at a 1024 px atlas
    clump: float      # 0 = parallel strands, 1 = tips meet at the strip centre
    wave: float       # waviness amplitude in px (at 1024)
    min_len: float    # shortest strand as a fraction of the strip height
    radius: float     # strand half width in px (at 1024)
    fill: float       # fraction of the strip width used by the roots


STRIPS = (
    Strip("dense", 0.15, 150, 0.20, 0.8, 0.86, 0.75, 0.94),
    Strip("dense2", 0.13, 120, 0.30, 1.2, 0.80, 0.75, 0.92),
    Strip("medium", 0.12, 64, 0.45, 1.4, 0.70, 0.7, 0.88),
    Strip("medium2", 0.11, 52, 0.55, 2.0, 0.66, 0.7, 0.85),
    Strip("wisp", 0.11, 16, 0.25, 2.4, 0.55, 0.65, 0.9),
    Strip("wisp2", 0.08, 10, 0.15, 3.0, 0.50, 0.65, 0.9),
    Strip("tip", 0.10, 48, 0.85, 1.2, 0.72, 0.7, 0.8),
    Strip("fly", 0.06, 4, 0.0, 5.0, 0.45, 0.6, 0.7),
    Strip("coarse", 0.09, 26, 0.5, 3.5, 0.55, 0.95, 0.85),
)
GUTTER = 0.004


def layout(size=1024):
    """{strip name: (u0, u1)} in UV units, strips left to right with small gutters."""
    out = {}
    u = GUTTER
    total = sum(s.width for s in STRIPS) + GUTTER * (len(STRIPS) + 1)
    k = 1.0 / total
    for s in STRIPS:
        w = s.width * k
        out[s.name] = (u, u + w)
        u += w + GUTTER * k
    return out


# --------------------------------------------------------------------------
# colour model
# --------------------------------------------------------------------------
def palette(hair_hex, hl_hex, grey=0.0):
    """Root, mid and tip colours (sRGB) from a character's hair colours.

    Very dark hair is lifted to a real albedo (black hair photographs as a deep
    warm brown-black, never pure #000); grey hair keeps a few darker strands.
    """
    base = tex.srgb(hair_hex)
    hl = tex.srgb(hl_hex)
    lum = float(base @ np.array([0.2126, 0.7152, 0.0722], np.float32))
    if lum < 0.12:
        warm = np.array([0.105, 0.078, 0.066], np.float32)
        base = base * 0.45 + warm * 0.55
    root = base * (0.78 if lum < 0.5 else 0.93)
    tip = base * 0.72 + hl * 0.28
    if lum < 0.12:
        tip = tip + np.array([0.035, 0.02, 0.008], np.float32)   # sun-faded warm ends
    elif lum > 0.5:
        tip = tip * np.array([1.0, 0.985, 0.94], np.float32)     # grey hair yellows at the ends
    return root, base, tip, grey


def _strand_colour(rng, pal, n):
    root, mid, tip, grey = pal
    val = rng.normal(1.0, 0.10, n).clip(0.7, 1.35)
    hue = rng.normal(0.0, 0.025, (n, 3))
    cols = []
    for i in range(n):
        j = (1 + hue[i]) * val[i]
        c = np.stack([root * j, mid * j, tip * j])
        if grey > 0 and rng.random() < grey:
            dark = rng.uniform(0.25, 0.55)                        # salt and pepper
            c = c * dark
        cols.append(np.clip(c, 0, 1))
    return cols


def _gradient(cols, v):
    """Colour along a strand: root -> mid (by 25 %) -> tip."""
    root, mid, tip = cols
    a = tex.sstep(0.0, 0.25, v)[:, None]
    b = tex.sstep(0.35, 1.0, v)[:, None]
    return (root * (1 - a) + mid * a) * (1 - b) + tip * b


# --------------------------------------------------------------------------
# strand rasteriser
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.col = np.zeros((h, w, 3), np.float32)
        self.alpha = np.zeros((h, w), np.float32)
        self.nx = np.zeros((h, w), np.float32)       # across-strand normal component
        self.flow = np.zeros((h, w), np.float32)     # dx/dv of the strand (px per row)
        self.depth = np.zeros((h, w), np.float32)
        self.ident = np.zeros((h, w), np.float32)

    def strand(self, xs, v, radius, opacity, colour, depth, ident):
        """Composite one strand over the canvas.

        xs: (H,) centre column per row, radius / opacity: (H,), colour (H, 3).
        """
        rows = np.nonzero(opacity > 0.004)[0]
        if rows.size == 0:
            return
        xc = xs[rows]
        r = radius[rows]
        k = int(math.ceil(float(r.max()))) + 2
        offs = np.arange(-k, k + 1)
        cols = np.floor(xc)[:, None].astype(int) + offs[None, :]
        valid = (cols >= 0) & (cols < self.w)
        cols_c = np.clip(cols, 0, self.w - 1)
        d = (cols + 0.5) - xc[:, None]
        cov = np.clip(r[:, None] - np.abs(d) + 0.5, 0.0, 1.0) * opacity[rows][:, None] * valid
        rr = np.repeat(rows[:, None], cols.shape[1], axis=1)
        a0 = self.alpha[rr, cols_c]
        self.alpha[rr, cols_c] = cov + a0 * (1 - cov)
        c3 = cov[..., None]
        self.col[rr, cols_c] = colour[rows][:, None, :] * c3 + self.col[rr, cols_c] * (1 - c3)
        nx = np.clip(d / np.maximum(r[:, None], 0.5), -1, 1)
        self.nx[rr, cols_c] = nx * cov + self.nx[rr, cols_c] * (1 - cov)
        dx = np.gradient(xs)[rows][:, None]
        self.flow[rr, cols_c] = dx * cov + self.flow[rr, cols_c] * (1 - cov)
        self.depth[rr, cols_c] = depth * cov + self.depth[rr, cols_c] * (1 - cov)
        self.ident[rr, cols_c] = ident * cov + self.ident[rr, cols_c] * (1 - cov)


def _paint_strip(cv, strip, x0, x1, rng, pal, scale):
    w = x1 - x0
    h = cv.h
    v = (np.arange(h, dtype=np.float32) + 0.5) / h
    n = max(2, int(strip.strands * scale))
    colours = _strand_colour(rng, pal, n)
    order = np.argsort(rng.random(n))                 # depth order: first = deepest
    centre = x0 + w * 0.5
    for rank, i in enumerate(order):
        depth = rank / max(n - 1, 1)
        # outer strands are shorter (natural taper of a clump), with random spread
        root = centre + (rng.random() - 0.5) * w * strip.fill
        edge = abs(root - centre) / (w * 0.5)
        length = rng.uniform(strip.min_len, 1.0) * (1 - 0.18 * edge ** 2)
        clump = strip.clump * rng.uniform(0.6, 1.2)
        pull = tex.sstep(0.2, 1.0, v / max(length, 1e-3)) * clump
        xs = root + (centre - root) * pull
        # gentle waves and a slow random drift (strands cross each other)
        amp = strip.wave * scale * rng.uniform(0.4, 1.3)
        f1, f2 = rng.uniform(0.6, 2.2), rng.uniform(2.5, 6.0)
        p1, p2 = rng.uniform(0, 2 * math.pi, 2)
        xs = xs + amp * (np.sin(2 * math.pi * f1 * v + p1) + 0.35 * np.sin(2 * math.pi * f2 * v + p2))
        xs = xs + np.cumsum(rng.normal(0, 0.02 * scale, h)).astype(np.float32) * (strip.wave > 2.5)
        xs = np.clip(xs, x0 + 1, x1 - 2)
        # taper: full width to 70 % length, then to a fine point
        rad = strip.radius * max(scale, 0.75) * rng.uniform(0.8, 1.2)
        taper = 1 - 0.75 * tex.sstep(length * 0.7, length, v)
        radius = rad * taper
        start = rng.uniform(0.0, 0.07) ** 2 / 0.07           # most strands start at the root, some later
        opacity = (tex.sstep(start, start + 0.02, v) * (1 - tex.sstep(length * 0.92, length, v))
                   * rng.uniform(0.75, 1.0))
        colour = _gradient(colours[i], v)
        cv.strand(xs.astype(np.float32), v, radius.astype(np.float32), opacity.astype(np.float32), colour,
                  depth, rng.random())


def _dilate_colour(col, alpha, passes=12):
    """Push strand colour into transparent texels (no dark fringes after filtering)."""
    w = np.clip(alpha, 0, 1)[..., None]
    acc = col * w
    wsum = w.copy()
    out = col.copy()
    for _ in range(passes):
        acc = (acc + np.roll(acc, 1, 1) + np.roll(acc, -1, 1) + np.roll(acc, 1, 0) + np.roll(acc, -1, 0)) / 5
        wsum = (wsum + np.roll(wsum, 1, 1) + np.roll(wsum, -1, 1) + np.roll(wsum, 1, 0) + np.roll(wsum, -1, 0)) / 5
    fill = acc / np.maximum(wsum, 1e-5)
    empty = wsum[..., 0] < 1e-5
    fill[empty] = col[alpha > 0.5].mean(axis=0) if (alpha > 0.5).any() else 0.1
    t = np.clip(alpha * 1.5, 0, 1)[..., None]
    out = col / np.maximum(w, 1e-4) * t + fill * (1 - t)
    return np.clip(out, 0, 1)


def atlas(hair_hex, hl_hex, size=1024, seed=21, grey=0.0):
    """Paint the full atlas. Returns dict of maps (all row 0 = bottom = strand roots)."""
    rng = np.random.default_rng(seed)
    pal = palette(hair_hex, hl_hex, grey)
    w = h = size
    scale = size / 1024.0
    cv = Canvas(w, h)
    for s in STRIPS:
        u0, u1 = layout(size)[s.name]
        _paint_strip(cv, s, int(u0 * w), int(u1 * w), rng, pal, scale)
    a = cv.alpha
    straight = cv.col / np.maximum(a, 1e-4)[..., None] * (a > 0)[..., None]
    col = _dilate_colour(straight * np.minimum(a, 1)[..., None], a)
    ao = (0.45 + 0.55 * cv.depth) * np.clip(a * 1.4, 0, 1) + 0.45 * (1 - np.clip(a * 1.4, 0, 1))
    v = ((np.arange(h) + 0.5) / h)[:, None]
    ao = ao * (0.72 + 0.28 * tex.sstep(0.0, 0.3, v))            # roots sit deeper in the volume
    rough = 0.36 + 0.12 * cv.ident + 0.10 * (1 - cv.depth) + 0.06 * tex.sstep(0.6, 1.0, v)
    # normal: strand cylinders across u, tilted by the local flow
    ny = np.clip(-cv.flow * 0.6, -0.5, 0.5)
    nx = cv.nx * 0.55
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0.05, 1))
    normal = np.stack([nx, ny, nz], axis=-1) * 0.5 + 0.5
    flow_angle = np.arctan(cv.flow) / math.pi + 0.5                # 0.5 = straight along v
    return {
        "albedo": np.concatenate([col, a[..., None]], axis=-1).astype(np.float32),
        "alpha": a,
        "ao": ao.astype(np.float32),
        "rough": np.clip(rough, 0, 1).astype(np.float32),
        "normal": normal.astype(np.float32),
        "flow": flow_angle.astype(np.float32),
        "depth": cv.depth,
        "id": cv.ident,
    }


def scalp_texture(hair_hex, hl_hex, size=256, seed=27):
    """Tileable fine-strand texture for the opaque scalp cap (streaks along v)."""
    rng = np.random.default_rng(seed)
    root, mid, tip, _ = palette(hair_hex, hl_hex)
    u, v = tex.grid(size)
    streak = np.zeros((size, size), np.float32)
    for cells, amp in ((size // 2, 0.5), (size // 4, 0.3), (size // 12, 0.2)):
        line = rng.random(cells).astype(np.float32)
        x = u[0] * cells
        i0 = np.floor(x).astype(int)
        f = x - i0
        streak += amp * (line[i0 % cells] * (1 - f) + line[(i0 + 1) % cells] * f)[None, :]
    wav = tex.fbm(size, 4, 3, 0.5, seed + 1, stretch=4)
    col = tex.lerp(root * 0.78, mid * 0.95, streak ** 2 * 0.8 + wav * 0.2)   # close to the cards: no dark rim
    rough = 0.5 + 0.1 * streak
    ao = 0.6 + 0.3 * streak
    return col, rough, ao, streak


def materials(prefix, hair_hex, hl_hex, size=1024, seed=21, grey=0.0, suffix="hair"):
    """Card material (alpha-tested atlas) and the opaque scalp-cap material."""
    maps = atlas(hair_hex, hl_hex, size, seed, grey)
    half = max(256, size // 2)
    alb = skin_shading.image(f"{prefix}{suffix}_albedo", maps["albedo"])
    orm = skin_shading.image(f"{prefix}{suffix}_orm",
                             skin_shading.orm(skin_shading.resize(maps["ao"], half),
                                              skin_shading.resize(maps["rough"], half)), data=True)
    nrm = skin_shading.image(f"{prefix}{suffix}_normal", maps["normal"], data=True)
    card = skin_shading.hair_material(prefix + suffix, alb, orm, nrm, hair_hex)
    # Cycles: the flow map rotates the anisotropic highlight with each strand
    t = card.node_tree
    bsdf = next(n for n in t.nodes if n.type == "BSDF_PRINCIPLED")
    flow = t.nodes.new("ShaderNodeTexImage")
    flow.image = skin_shading.image(f"{prefix}{suffix}_flow", skin_shading.resize(maps["flow"], half), data=True)
    flow.location = (-700, -1200)
    t.links.new(flow.outputs["Color"], bsdf.inputs["Anisotropic Rotation"])
    cap = None
    if suffix == "hair":
        col, rough, ao, streak = scalp_texture(hair_hex, hl_hex)
        cap = skin_shading.simple_material(
            prefix + "hair_scalp", skin_shading.image(prefix + "hair_scalp_albedo", col),
            skin_shading.image(prefix + "hair_scalp_orm", skin_shading.orm(ao, rough), data=True),
            skin_shading.image(prefix + "hair_scalp_normal", tex.normal_from_height(streak, 1.5), data=True),
            normal_strength=0.5, spec=0.4)
    return card, cap, maps

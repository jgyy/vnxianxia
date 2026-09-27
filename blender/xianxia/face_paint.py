"""Facial feature masks in the head UV layout (pure numpy) - the interface for skin painters.

``feature_masks(cfg, size)`` returns {name: (size, size) float32 in 0..1}
computed from the *same* landmark model and sculpted surface the head mesh is
built from, so a painter never has to guess where the lips or brows landed:

    lips        vermilion (1 inside, soft 0.4 mm border)   lip_inner  darker toward the stomion
    brows       the brow band (for a painted base under the brow cards)
    liner_up    upper lash line        liner_lo   lower lash line
    lid         upper lid between the lash line and the crease (eye shadow)
    under_eye   thin lower-lid / tear-trough skin (cooler, darker)
    aegyo       the pretarsal roll (a highlight)
    cheeks      malar fat pads (blush)          nose   nose tip and alae (flush)
    nostrils    nostril openings (dark)         ears   the ear boxes
    beard       moustache / chin / jaw / cheek beard area (stubble)
    nasolabial  the nasolabial folds            marionette  folds from the mouth corners
    crows_feet  lateral canthus fans            forehead    forehead (lines, T-zone)
    face        the facial skin (hairline to jaw, ear to ear)

``preview_maps(cfg, size)`` composes a complete skin albedo / roughness /
height from those masks on top of ``tex.skin`` (without its lat/long
features).  render_portraits can use it (``--face-maps``) to preview the head
before a skin texture painted for this UV layout exists.
"""
import numpy as np

from . import face_cards, face_chart as fc, face_eyes, face_rig, face_uv, tex
from . import face_landmarks as fl
from . import face_surface as fs


def _sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def texel_points(p: fl.FaceParams, surf, size):
    """Head-mm surface point for every texel of the FACE island (nan elsewhere), plus the island map."""
    u, v = tex.grid(size)
    lon, b, isl = face_uv.lonb_from_uv(u, v)
    table = face_rig.SurfaceTable(surf, 181, 121)
    P = np.full((size, size, 3), np.nan)
    ok = (isl == 0) & (b >= fc.B_HEAD) & (np.abs(lon) <= face_uv.SEAM)
    lo, bb = lon[ok], b[ok]
    r = table.radius_v(lo, bb)
    P[ok] = np.stack([np.sin(lo) * np.cos(bb), -np.cos(lo) * np.cos(bb), np.sin(bb)], axis=-1) * r[:, None]
    return P, isl, u, v


def feature_masks(cfg, size=1024):
    p = fl.params_for(cfg)
    S = fs.HeadSurface(p)
    P, _, u, v = texel_points(p, S, size)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    valid = ~np.isnan(x)
    x = np.nan_to_num(x, nan=1e3)
    y = np.nan_to_num(y, nan=1e3)
    z = np.nan_to_num(z, nan=1e3)
    ax = np.abs(x)
    L = fl.landmarks(p)
    fy = fl.face_plane(p)
    front = _sstep(fy + 40.0, fy + 20.0, y) * valid
    M = {}
    st, up, lo = S.lips_at(x)
    M["lips"] = S.lip_mask(x, z) * front
    M["lip_inner"] = M["lips"] * np.exp(-((z - st) / (0.45 * np.maximum(up - st, 2.0) + 0.5 * (z < st) *
                                                       np.maximum(st - lo, 2.0))) ** 2)
    # brows
    centre, half_h = face_cards.brow_band(p)
    ts = np.linspace(0, 1, 60)
    line = [centre(t) for t in ts]
    d, _, frac = fs._polyline_sdist(ax, z, line)
    hh = np.interp(frac, ts, [half_h(t) for t in ts])
    ends = _sstep(0.0, 0.06, frac) * _sstep(1.0, 0.9, frac)
    M["brows"] = _sstep(hh + 0.9, hh - 0.6, d) * front * (0.45 + 0.55 * ends)
    # eyes: distances to the lid margins in each eye's frontal frame
    lids = face_eyes.EyeLids(p, 1)
    t = np.linspace(0, 1, 80)
    mu, wu, wl = lids.margins(t)
    uu = ax - lids.c[0]
    ww = z - lids.c[2]
    du, _, fu = fs._polyline_sdist(uu, ww, np.stack([mu, wu], axis=-1))
    dl, _, fl_ = fs._polyline_sdist(uu, ww, np.stack([mu, wl], axis=-1))
    above = ww > np.interp(uu, mu, wu)
    below = ww < np.interp(uu, mu, wl)
    inside_x = _sstep(lids.u_en - 1.0, lids.u_en + 2.0, uu) * _sstep(lids.u_ex + 4.0, lids.u_ex - 1.0, uu)
    wing = _sstep(0.75, 1.0, fu) * p.fem
    M["liner_up"] = np.exp(-(du / (0.55 + 0.5 * wing)) ** 2) * above * (inside_x + wing).clip(0, 1) * front
    M["liner_lo"] = np.exp(-(dl / 0.5) ** 2) * below * inside_x * _sstep(0.15, 0.45, fl_) * front
    crease = p.crease_h + 1.2
    M["lid"] = _sstep(crease + 3.0, crease, du) * above * inside_x * front
    M["aegyo"] = np.exp(-((dl - 2.4) / 1.6) ** 2) * below * inside_x * p.aegyo * front
    M["under_eye"] = np.exp(-((dl - 5.5) / 3.0) ** 2) * below * inside_x * front
    ex = L["exocanthion.L"]
    M["crows_feet"] = np.exp(-(((ax - abs(ex[0]) - 9.0) / 6.0) ** 2 + ((z - ex[2]) / 8.0) ** 2)) * front
    # cheeks, nose, nostrils
    M["cheeks"] = np.exp(-(((ax - lids.c[0] + 1.0) / 15.0) ** 2 + ((z - (lids.c[2] - 24.0)) / 11.0) ** 2)) * front
    prn = L["pronasale"]
    al = L["alare.L"]
    M["nose"] = np.clip(np.exp(-((x / 8.0) ** 2 + ((z - prn[2]) / 8.0) ** 2)) +
                        0.8 * np.exp(-(((ax - al[0] + 3.0) / 6.0) ** 2 + ((z - al[2]) / 6.0) ** 2)), 0, 1) * front
    nc = (p.alar_w * 0.5 - 9.2, prn[1] + 9.5, p.subnasale + 1.0)
    M["nostrils"] = np.exp(-(((ax - nc[0]) / 2.2) ** 2 + ((y - nc[1]) / 4.0) ** 2 + ((z - nc[2]) / 2.5) ** 2)) * valid
    # beard area: upper lip, chin and jaw (not the lips), sideburns toward the ears
    jaw_zone = _sstep(p.subnasale - 1.0, p.subnasale - 5.0, z) * (1.0 - M["lips"])
    cheek_cut = _sstep(lids.c[2] - 24.0, lids.c[2] - 34.0, z + 0.25 * (ax - 30.0))
    M["beard"] = np.clip(jaw_zone * cheek_cut * valid, 0, 1)
    # folds
    for key, path in (("nasolabial", S.nlf), ("marionette", S.mar)):
        d, _, fr = fs._polyline_sdist(ax, z, path)
        M[key] = np.exp(-(d / 2.0) ** 2) * _sstep(0.0, 0.1, fr) * _sstep(1.0, 0.75, fr) * front
    M["forehead"] = _sstep(p.glabella + 6.0, p.glabella + 16.0, z) * _sstep(p.trichion + 6.0, p.trichion - 4.0, z) * \
        _sstep(55.0, 40.0, ax) * valid
    M["face"] = valid * _sstep(p.trichion + 4.0, p.trichion - 2.0, z) * _sstep(-5.0, -20.0, y)
    ears = np.zeros((size, size))
    for box in face_uv.EAR_BOX.values():
        ears = np.maximum(ears, (u >= box[0]) & (u <= box[2]) & (v >= box[1]) & (v <= box[3]))
    M["ears"] = ears
    return {k: np.clip(val, 0, 1).astype(np.float32) for k, val in M.items()}


def preview_maps(cfg, size=1024):
    """A full skin texture set (albedo, rough, metal, height) for the head in this UV layout."""
    c = cfg["colors"]
    fem = cfg["female"]
    age = cfg.get("age", 0.0)
    base = tex.skin(c["skin"], size, 11, None)
    M = feature_masks(cfg, size)
    col, rough = base["albedo"].copy(), base["rough"].copy()
    height = 0.55 + (base["height"] - 0.55) * 0.45          # the generic skin relief is coarse at face scale
    col = col * np.array([1.0, 0.95, 0.92], np.float32)     # living skin: a warm, rosy cast
    skin = tex.srgb(c["skin"])
    lerp = tex.lerp
    # blood flow: redder nose, cheeks, ears and lips' surroundings; slightly sallow forehead
    col = lerp(col, col * np.array([1.06, 0.84, 0.82], np.float32), np.clip(M["nose"] * 0.6 + M["ears"] * 0.45 + M["cheeks"] * 0.35, 0, 1))
    col = lerp(col, srgb_mix(c.get("blush", "#d4908a"), skin, 0.5), M["cheeks"] * (0.42 if fem else 0.16))
    col = lerp(col, col * np.array([1.02, 1.0, 0.93], np.float32), M["forehead"] * 0.25)
    # eyes: cool thin skin under the eye, a soft liner (women), a hint of lid shadow
    col = lerp(col, col * np.array([0.84, 0.8, 0.86], np.float32), M["under_eye"] * (0.35 + 0.35 * age))
    col = lerp(col, col * 1.06, M["aegyo"] * 0.5)
    liner = tex.srgb(c.get("liner", "#1a1010"))
    col = lerp(col, liner, M["liner_up"] * (0.85 if fem else 0.5))
    col = lerp(col, liner, M["liner_lo"] * (0.35 if fem else 0.15))
    if fem:
        col = lerp(col, srgb_mix(c.get("blush", "#d4908a"), skin, 0.35) * 0.92, M["lid"] * 0.35)
    col = lerp(col, tex.srgb(c["brow"]), M["brows"] * 0.35)
    # lips: colour gradient (darker and more saturated toward the inner lip), glossy, fine vertical lines
    lip = tex.srgb(c["lip"])
    lip_c = lerp(srgb_mix(c["lip"], c["skin"], 0.55 if not fem else 0.3), lip * 0.8, M["lip_inner"])
    col = lerp(col, lip_c, M["lips"] * (0.95 if fem else 0.75))
    u, v = tex.grid(size)
    lines = 0.5 + 0.5 * np.sin(u * 2400.0 + tex.fbm(size, 16, 2, 0.5, 5) * 6)
    height = height + M["lips"] * (lines * 0.12 - 0.04)
    rough = rough - M["lips"] * (0.28 if fem else 0.15) - M["nose"] * 0.08 - M["forehead"] * 0.08
    col = lerp(col, col * np.array([0.35, 0.25, 0.25], np.float32), M["nostrils"] * 0.8)
    # beard shadow
    beard = cfg.get("stubble", 0.0 if fem else 0.35)
    if beard:
        stub = tex.fbm(size, max(8, size // 5), 2, 0.5, 31)
        col = lerp(col, col * np.array([0.7, 0.72, 0.78], np.float32), M["beard"] * beard * (0.5 + 0.5 * stub))
        height = height + M["beard"] * beard * stub * 0.2
    # age: fold shading and lines
    if age > 0:
        col = lerp(col, col * 0.86, np.clip(M["nasolabial"] + M["marionette"], 0, 1) * 0.5 * age)
        wr = 0.5 + 0.5 * np.sin((v * 700.0) + tex.fbm(size, 8, 2, 0.5, 7) * 3)
        height = height - M["forehead"] * _sstep(0.7, 1.0, wr) * 0.35 * age
        cf = 0.5 + 0.5 * np.sin((u + v) * 900.0)
        height = height - M["crows_feet"] * cf * 0.4 * age
    return tex.result(col, np.clip(rough, 0.25, 0.8), 0.0, height)


def srgb_mix(a, b, t):
    """Mix two colours (hex strings or rgb arrays)."""
    ca = tex.srgb(a) if isinstance(a, str) else np.asarray(a, np.float32)
    cb = tex.srgb(b) if isinstance(b, str) else np.asarray(b, np.float32)
    return ca * (1 - t) + cb * t

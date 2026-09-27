"""Parametric anthropometric face model: per-character parameters and landmarks.

Everything here is pure Python (no bpy) and works in *head millimetres*:
origin at the head centre ``characters.build_head`` uses (between the ears,
at eye height), +x = the character's left, +y = backwards, +z = up, so the
face looks down -y.  ``face_mesh`` scales the result by 0.001 * cfg scale.

Research notes (population proportions, not any real person's likeness)
------------------------------------------------------------------------
Numbers are rounded means for Korean adults aged ~20-30 unless noted; the
"idol" look is a mild push toward the attractive-group results, not a caricature.

* Farkas LG et al., "International anthropometric study of facial morphology in
  various ethnic groups/races", J Craniofac Surg 16(4), 2005 - intercanthal
  width ~ alar width in East Asians; wider intercanthal / flatter radix than
  North American Caucasians.
* Choe KS et al., "Analysis of the midface, focusing on the nose: an
  anthropometric study in young Koreans", J Craniofac Surg 21(6), 2010
  (2,065 subjects): female intercanthal distance ~ nasal dorsum length ~
  nasal width; male values 5-10 % larger; nasal length : tip projection :
  dorsal height : radix height ~ 2 : 0.97 : 0.61 : 0.28.
* Kim SY et al., "Comparison of periorbital anthropometry between beauty
  pageant contestants and ordinary young women with Korean ethnicity",
  Aesth Plast Surg 41, 2017: palpebral fissure width 27.7 vs 26.3 mm,
  intercanthal 34.3 vs 36.7 mm (attractive group: longer fissure, closer eyes).
* Kim SY et al., "Comparison of facial proportions between beauty pageant
  contestants and ordinary young women of Korean ethnicity", Aesth Plast Surg
  42, 2018: attractive faces have a shorter / narrower lower face and smaller
  nasal and mouth widths relative to face width ("V-line", small chin).
* Kim DW et al., "Three-dimensional photogrammetric study on age-related facial
  characteristics in Korean females", Ann Dermatol 33(1), 2021: horizontal
  thirds 0.73 : 1 : 0.73 (young) vs 0.66 : 1 : 0.66 (60-79 y); older faces lose
  upper-face height and volume.
* Lip literature (JCAD review "Lip measurements and preferences in Asians and
  Hispanics"): Korean women upper : lower vermilion 1 : 1.11 (caliper) -
  1 : 1.25 (surface); men ~1 : 1.25; ideal philtrum 11-13 mm (F), 13-15 mm (M).
* Nasofrontal / nasolabial angles in young Koreans ~ 130-140 / 85-100 deg
  (CT studies, e.g. Nasal anthropometry on facial CT for rhinoplasty in
  Koreans, 2013); low radix but a defined dorsum and a rounded, non-pointed tip.
* Periocular: pretarsal roll ("aegyo-sal", orbicularis in front of the tarsus)
  3-5 mm tall, most visible when smiling; Asian upper-lid crease 6-8 mm on the
  tarsus but the visible pretarsal show is only 1-3 mm (in-out / parallel
  crease); 50-90 % of Koreans have some epicanthal fold (Zoumalan, Asian eye
  anatomy; PMC4536060 "Evolution of looks ... of Asian eyelid").
* Jaw: V-line = narrow bigonial width with a soft (obtuse, ~125-130 deg)
  gonial angle and a small, slightly pointed chin; male jaws squarer (gonial
  ~118-122 deg) with a wider chin.
* Ageing (Korean and general 3-D photogrammetry): midface fat descent,
  deeper nasolabial and marionette folds, tear trough, jowls, thinner and
  longer upper lip, lid hooding, temple hollowing, ears and nose lengthen.
* General sculpting references: Loomis / Bridgman facial thirds and fifths;
  ear from brow line to nose base, set behind the jaw's mid-line.

Head frame used by the mesh: the chart of "rays from the head centre" used by
face_mesh gives every landmark a (lon, lat) too (``chart_of``).
"""
import math
import random
from dataclasses import dataclass, field, replace

# --------------------------------------------------------------------------
# parameters
# --------------------------------------------------------------------------


@dataclass
class FaceParams:
    fem: bool
    age: float                      # 0 = early twenties .. 1 = seventies
    head: tuple                     # (rx, ry, rz) half extents in mm
    # vertical layout (z of landmarks, mm)
    menton: float
    subnasale: float
    glabella: float
    trichion: float
    canthus: float                  # endocanthion height
    # eyes
    icw: float                      # intercanthal width
    pfl: float                      # palpebral fissure length
    pfh: float                      # palpebral fissure height (at the pupil)
    tilt: float                     # exocanthion - endocanthion height, mm
    crease: str                     # "none" | "inout" | "parallel"
    crease_h: float                 # visible pretarsal show, mm
    aegyo: float                    # pretarsal roll strength 0..1
    epicanthus: float               # medial fold coverage 0..1
    eye_r: float                    # eyeball radius
    hood: float                     # upper-lid hooding (age) 0..1
    # brows
    brow_gap: float                 # brow bottom above the pupil
    brow_arch: float                # 0 straight .. 1 arched
    brow_ridge: float               # supraorbital projection, mm
    brow_len: float
    brow_thick: float
    # nose
    radix: float                    # nasion depth in front of the cornea, mm
    tip_proj: float                 # pronasale in front of the alar crease
    alar_w: float                   # full alar width
    bridge_w: float                 # bony bridge width at the eyes
    tip_w: float                    # tip lobule width
    hump: float                     # dorsal hump (mm, + = convex)
    tip_up: float                   # tip rotation (mm, + = upturned)
    # mouth
    mouth_w: float
    philtrum: float
    up_verm: float
    lo_verm: float
    lip_proj: float                 # lips in front of the dental arch
    cupid: float                    # cupid's bow depth
    corner_up: float                # mouth corners above the stomion midline
    # lower face / jaw
    zygion: float                   # half bizygomatic width
    gonion_w: float                 # half bigonial width
    gonion_z: float
    chin_w: float                   # half width of the chin pad
    chin_proj: float                # pogonion relative to the lower lip, mm (+ = forward)
    chin_h: float                   # labiomental fold -> menton
    jaw_soft: float                 # jaw-to-neck blend radius (mm)
    # soft tissue
    cheek_fat: float                # malar fat pad fullness (mm)
    malar: float                    # zygomatic prominence (mm)
    buccal: float                   # cheek hollow under the zygoma (mm)
    nasolabial: float               # nasolabial fold depth (mm)
    marionette: float
    jowl: float
    temple: float                   # temporal hollow (mm)
    forehead_round: float           # frontal bossing (mm)
    tear_trough: float
    # ears / neck
    ear_len: float
    ear_out: float                  # protrusion angle, deg
    neck_r: float
    adam: float                     # laryngeal prominence (mm)
    seed: int = 0
    extra: dict = field(default_factory=dict)


# young adult means (idol-leaning), mm - see the research notes above
_FEMALE = dict(
    fem=True, age=0.0, head=(72.0, 93.0, 108.0),
    menton=-104.0, subnasale=-45.5, glabella=8.0, trichion=63.0, canthus=-2.5,
    icw=32.0, pfl=28.5, pfh=11.6, tilt=2.6, crease="inout", crease_h=1.6, aegyo=0.9, epicanthus=0.55,
    eye_r=12.0, hood=0.0,
    brow_gap=13.5, brow_arch=0.2, brow_ridge=1.2, brow_len=37.0, brow_thick=6.4,
    radix=8.0, tip_proj=17.0, alar_w=32.5, bridge_w=9.5, tip_w=12.0, hump=-0.3, tip_up=1.4,
    mouth_w=42.5, philtrum=12.0, up_verm=8.0, lo_verm=10.0, lip_proj=2.4, cupid=1.3, corner_up=1.0,
    zygion=67.5, gonion_w=51.0, gonion_z=-79.0, chin_w=12.5, chin_proj=2.4, chin_h=26.0, jaw_soft=9.0,
    cheek_fat=6.0, malar=2.2, buccal=0.8, nasolabial=0.6, marionette=0.0, jowl=0.0, temple=1.2,
    forehead_round=3.0, tear_trough=0.3,
    ear_len=55.0, ear_out=16.0, neck_r=45.0, adam=0.0,
)
_MALE = dict(
    fem=False, age=0.0, head=(75.0, 97.0, 114.0),
    menton=-110.0, subnasale=-47.5, glabella=11.0, trichion=70.0, canthus=-1.5,
    icw=33.5, pfl=29.0, pfh=10.0, tilt=1.6, crease="inout", crease_h=1.1, aegyo=0.55, epicanthus=0.45,
    eye_r=11.9, hood=0.0,
    brow_gap=12.5, brow_arch=0.08, brow_ridge=2.8, brow_len=41.0, brow_thick=7.0,
    radix=9.0, tip_proj=20.5, alar_w=37.5, bridge_w=11.0, tip_w=14.0, hump=0.2, tip_up=0.4,
    mouth_w=47.5, philtrum=13.5, up_verm=7.0, lo_verm=9.2, lip_proj=2.0, cupid=1.0, corner_up=0.4,
    zygion=71.0, gonion_w=57.0, gonion_z=-82.0, chin_w=18.0, chin_proj=3.2, chin_h=30.0, jaw_soft=8.0,
    cheek_fat=2.0, malar=2.6, buccal=1.8, nasolabial=0.8, marionette=0.0, jowl=0.0, temple=1.6,
    forehead_round=1.2, tear_trough=0.4,
    ear_len=60.0, ear_out=18.0, neck_r=53.0, adam=3.5,
)

# Per-character build: (dict of overrides applied after sex defaults)
_CHARACTER = {
    "cultivator_female": dict(pfh=11.4, epicanthus=0.35, crease="parallel", crease_h=1.9),
    "cultivator_male": dict(),
    "sect_master": dict(pfl=27.5, crease="parallel", crease_h=2.0, aegyo=0.6, malar=2.8, cheek_fat=2.6,
                        brow_arch=0.35, tilt=3.2, chin_proj=-0.5, gonion_w=49.0),
    "disciple_female": dict(pfl=27.0, pfh=10.8, cheek_fat=4.0, chin_w=14.0, gonion_w=50.0, tip_proj=15.0,
                            crease="inout", crease_h=1.2, mouth_w=44.0, brow_arch=0.18),
    "disciple_male": dict(crease="none", pfh=8.4, epicanthus=0.8, aegyo=0.4, cheek_fat=2.6,
                          gonion_w=53.0, tip_proj=17.0, radix=7.5, brow_ridge=2.0),
    "villager_female": dict(crease="none", pfh=9.0, epicanthus=0.85, cheek_fat=4.4, zygion=67.0,
                            gonion_w=52.0, chin_w=15.0, alar_w=36.0, tip_proj=14.5, radix=6.5,
                            aegyo=0.5, mouth_w=47.0),
    "villager_male": dict(crease="none", pfh=8.2, epicanthus=0.9, zygion=71.0, gonion_w=60.0, chin_w=21.0,
                          alar_w=40.0, tip_proj=16.0, radix=6.0, bridge_w=13.0, tip_w=16.0, aegyo=0.3,
                          brow_ridge=3.0),
    "bandit": dict(crease="none", pfh=8.0, zygion=72.0, gonion_w=63.0, gonion_z=-86.0, chin_w=22.0,
                   chin_proj=2.5, alar_w=41.0, bridge_w=13.0, tip_w=16.5, hump=1.4, brow_ridge=4.6,
                   brow_gap=10.5, brow_thick=8.5, aegyo=0.15, buccal=2.6, lip_proj=2.2),
    "demon_cultivator": dict(pfh=8.2, tilt=3.6, crease="parallel", crease_h=0.8, zygion=69.0, malar=4.2,
                             buccal=3.6, cheek_fat=0.8, gonion_w=54.0, chin_w=14.0, chin_proj=1.5,
                             up_verm=5.4, lo_verm=7.2, brow_arch=0.55, brow_ridge=3.4, temple=2.6,
                             aegyo=0.1, hump=0.8),
    "blood_patriarch": dict(pfh=8.4, tilt=2.4, crease="none", zygion=74.0, malar=4.4, buccal=3.0,
                            gonion_w=62.0, chin_w=21.0, chin_proj=3.5, brow_ridge=6.0, brow_gap=10.0,
                            brow_thick=9.0, alar_w=40.0, hump=1.8, bridge_w=12.5, up_verm=5.8,
                            lo_verm=7.6, temple=3.0, aegyo=0.1),
    "elder_male": dict(crease="parallel", crease_h=0.6, pfh=8.2, aegyo=0.2, alar_w=41.0, tip_proj=19.5,
                       hump=0.8, brow_arch=0.2, brow_thick=8.0),
}


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _age(p: FaceParams, a: float) -> FaceParams:
    """Apply ageing (a = 0..1) to a young-adult parameter set.

    Bone changes are small (orbits widen, midface retrudes); most of the
    change is soft tissue descending and thinning.
    """
    if a <= 0:
        return p
    k = _smoothstep(a)
    return replace(
        p, age=a,
        pfh=p.pfh * (1 - 0.18 * k),              # lids hood and droop
        hood=p.hood + 0.9 * k,
        crease_h=p.crease_h * (1 - 0.6 * k),
        aegyo=p.aegyo * (1 - 0.7 * k),
        tilt=p.tilt - 1.6 * k,                    # the lateral canthus drops
        brow_gap=p.brow_gap - 2.0 * k,            # brow ptosis
        brow_arch=p.brow_arch * (1 - 0.4 * k),
        up_verm=p.up_verm * (1 - 0.38 * k),       # thinner, longer upper lip
        lo_verm=p.lo_verm * (1 - 0.3 * k),
        philtrum=p.philtrum + 3.0 * k,
        lip_proj=p.lip_proj * (1 - 0.45 * k),
        corner_up=p.corner_up - 1.8 * k,          # down-turned mouth corners
        tip_up=p.tip_up - 2.2 * k,                # the tip droops
        tip_proj=p.tip_proj + 1.0 * k,
        cheek_fat=p.cheek_fat * (1 - 0.35 * k),
        buccal=p.buccal + 2.2 * k,
        nasolabial=p.nasolabial + 3.4 * k,
        marionette=p.marionette + 2.2 * k,
        jowl=p.jowl + 3.2 * k,
        jaw_soft=p.jaw_soft + 9.0 * k,            # the jaw line blurs into the neck
        temple=p.temple + 2.0 * k,
        tear_trough=p.tear_trough + 2.4 * k,
        forehead_round=p.forehead_round * (1 - 0.3 * k),
        ear_len=p.ear_len * (1 + 0.08 * k),       # ears keep growing
        alar_w=p.alar_w * (1 + 0.05 * k),
    )


def params_for(cfg) -> FaceParams:
    """FaceParams for a character config from characters.py."""
    fem = cfg["female"]
    base = dict(_FEMALE if fem else _MALE)
    base.update(_CHARACTER.get(cfg["name"], {}))
    # cfg-level multipliers kept from the old head model (face=dict(nose=, brow=, cheek=, chin=, lips=, age=))
    f = cfg.get("face") or {}
    nose = f.get("nose", 1.0)
    base["tip_proj"] *= 1 + 0.9 * (nose - 1)
    base["alar_w"] *= 1 + 0.5 * (nose - 1)
    base["radix"] *= 1 + 0.8 * (nose - 1)
    brow = f.get("brow", 1.0)
    base["brow_ridge"] *= brow
    cheek = f.get("cheek", 1.0)
    base["malar"] *= cheek
    base["zygion"] *= 1 + 0.06 * (cheek - 1)
    chin = f.get("chin", 1.0)
    base["chin_proj"] += 3.0 * (chin - 1)
    base["chin_w"] *= 1 + 0.4 * (chin - 1)
    lips = f.get("lips", 1.0)
    base["up_verm"] *= lips
    base["lo_verm"] *= lips
    jaw = cfg.get("jaw", 0.55 if not fem else 0.40)
    ref = 0.55 if not fem else 0.40
    base["gonion_w"] *= 1 + 0.35 * (jaw - ref)
    if "neck_r" in cfg:          # the body's collar is sized from cfg neck_r; keep the neck just inside it
        base["neck_r"] = cfg["neck_r"] * 1000.0 * 0.97
    rx, ry, rz = (r * 1000.0 for r in cfg["head_r"])
    base["head"] = (rx, ry, rz)
    base["menton"] = base["menton"] * rz / (108.0 if fem else 114.0)   # chin below the centre, per head size
    # small deterministic individuality so NPCs of the same sex do not share one face
    rng = random.Random(sum(ord(c) * (i + 7) for i, c in enumerate(cfg["name"])))
    base["seed"] = rng.randrange(1 << 30)
    if not cfg["name"].startswith("cultivator_"):
        for key, amt in (("icw", 0.03), ("pfl", 0.03), ("alar_w", 0.04), ("mouth_w", 0.04),
                         ("tip_proj", 0.06), ("zygion", 0.02), ("philtrum", 0.06), ("chin_h", 0.04)):
            base[key] *= 1 + rng.uniform(-amt, amt)
    p = FaceParams(**base)
    age = max(cfg.get("age", 0.0), f.get("age", 0.0))
    return _age(p, age)


# --------------------------------------------------------------------------
# derived landmarks
# --------------------------------------------------------------------------
def face_plane(p: FaceParams):
    """Depth (y) of the facial plane: glabella, cheeks and lips sit close to it."""
    return -0.905 * p.head[1]


def eye_geometry(p: FaceParams, side=1):
    """Eyeball centre, radius, corneal apex and the canthi for one eye (side +1 = left).

    The fissure is longer than the globe is wide: the lateral canthus wraps
    just past the globe's equator and the medial canthus lies over the
    caruncle, several mm medial of the visible sclera."""
    en_x = p.icw * 0.5
    ex_x = en_x + p.pfl
    R = p.eye_r
    cx = ex_x - 1.05 * R            # the lateral canthus sits just past the globe's equator
    en_z = p.canthus
    ex_z = p.canthus + p.tilt
    pupil_z = p.canthus + 0.5 * p.tilt + 0.9
    apex_y = face_plane(p) + p.radix + 1.5
    cy = apex_y + R + 1.05          # the cornea bulges ~1 mm past the scleral sphere
    return dict(centre=(side * cx, cy, pupil_z), R=R, apex=(side * cx, apex_y, pupil_z),
                en=(side * en_x, cy - 8.0, en_z), ex=(side * ex_x, cy + 1.5, ex_z))


def nasion(p: FaceParams):
    e = eye_geometry(p)
    return (0.0, e["apex"][1] - p.radix, p.canthus + 3.5 + 0.2 * (p.glabella - p.canthus))


def landmarks(p: FaceParams):
    """Named anatomical landmarks (mm, head frame). Bilateral points get .L/.R."""
    L = {}
    rx, ry, rz = p.head
    fy = face_plane(p)
    nz = nasion(p)
    st_z = p.subnasale - p.philtrum - p.up_verm
    L["vertex"] = (0.0, 4.0, rz)
    L["opisthocranion"] = (0.0, ry, 20.0)
    L["trichion"] = (0.0, fy + 4.0, p.trichion)
    L["glabella"] = (0.0, fy - p.brow_ridge * 0.6, p.glabella)
    L["nasion"] = nz
    L["rhinion"] = (0.0, nz[1] - p.tip_proj * 0.45, (nz[2] + p.subnasale) * 0.5 + 4.0)
    L["pronasale"] = (0.0, fy + 2.0 - p.tip_proj, p.subnasale + 6.5 + p.tip_up)
    L["subnasale"] = (0.0, fy + 1.0, p.subnasale)
    L["labrale_superius"] = (0.0, fy - p.lip_proj + 0.5, p.subnasale - p.philtrum)
    L["stomion"] = (0.0, fy + 2.5, st_z)
    L["labrale_inferius"] = (0.0, fy - p.lip_proj + 1.2, st_z - p.lo_verm)
    lf_z = st_z - p.lo_verm - 5.0
    L["sublabiale"] = (0.0, fy + 7.0, lf_z)
    L["pogonion"] = (0.0, fy + 1.0 - p.chin_proj, lf_z - p.chin_h * 0.45)
    L["gnathion"] = (0.0, fy + 12.0 - p.chin_proj, p.menton + 5.0)
    L["menton"] = (0.0, fy + 26.0, p.menton)
    L["cervicale"] = (0.0, -p.neck_r * 0.62, p.menton + 8.0)
    for side, sx in ((1, "L"), (-1, "R")):
        g = eye_geometry(p, side)
        L[f"eye_centre.{sx}"] = g["centre"]
        L[f"endocanthion.{sx}"] = g["en"]
        L[f"exocanthion.{sx}"] = g["ex"]
        L[f"pupil.{sx}"] = g["apex"]
        L[f"brow_head.{sx}"] = (side * (p.icw * 0.5 - 1.0), fy - p.brow_ridge + 2.0, g["apex"][2] + p.brow_gap - 1.0)
        L[f"brow_peak.{sx}"] = (side * (p.icw * 0.5 + p.pfl * 0.68), fy + 6.0,
                               g["apex"][2] + p.brow_gap + 2.0 + 3.0 * p.brow_arch)
        L[f"brow_tail.{sx}"] = (side * (p.icw * 0.5 + p.brow_len), fy + 22.0, g["ex"][2] + p.brow_gap - 1.0)
        L[f"alare.{sx}"] = (side * p.alar_w * 0.5, fy + 2.0, p.subnasale + 4.0)
        L[f"subalare.{sx}"] = (side * (p.alar_w * 0.5 - 2.0), fy + 4.0, p.subnasale + 0.5)
        L[f"cheilion.{sx}"] = (side * p.mouth_w * 0.5, fy + 9.0, st_z + p.corner_up)
        L[f"crista_philtri.{sx}"] = (side * 5.2, fy - p.lip_proj + 1.0, p.subnasale - p.philtrum + p.cupid * 0.4)
        L[f"zygion.{sx}"] = (side * p.zygion, -8.0, -12.0)
        L[f"malar.{sx}"] = (side * p.zygion * 0.64, fy + 12.0 - p.malar, g["en"][2] - 20.0)
        L[f"gonion.{sx}"] = (side * p.gonion_w, 6.0, p.gonion_z)
        L[f"tragion.{sx}"] = (side * (rx - 1.0), 10.0, p.canthus - 11.0)
        L[f"otobasion_sup.{sx}"] = (side * (rx - 2.0), 9.0, p.glabella + 2.0)
        L[f"eurion.{sx}"] = (side * rx, 18.0, 30.0)
        L[f"frontotemporale.{sx}"] = (side * rx * 0.76, fy + 26.0, p.glabella + 20.0)
        L[f"chin_lat.{sx}"] = (side * p.chin_w, fy + 8.0 - p.chin_proj, lf_z - p.chin_h * 0.5)
    return L


def lip_curves(p: FaceParams, n=41):
    """Stomion line, upper and lower vermilion borders as (x, z) lists (x from -corner to +corner).

    The upper border carries the Cupid's bow: two peaks over the philtral
    columns and a V dip at the midline; the lower border is a fuller arc.
    """
    xc = p.mouth_w * 0.5
    st = p.subnasale - p.philtrum - p.up_verm
    stom, upper, lower = [], [], []
    for i in range(n):
        x = -xc + 2 * xc * i / (n - 1)
        t = abs(x) / xc
        zs = st + p.corner_up * t ** 2.2 - 0.35 * (1 - t ** 2)          # a slight downward bow at the centre
        peak = 5.2
        if abs(x) <= peak:
            bow = p.cupid * (1 - (abs(x) / peak) ** 1.4)                 # the V dip toward the midline
            zu = st + p.up_verm - bow + p.cupid * 0.35 * (abs(x) / peak) ** 6
        else:
            q = (abs(x) - peak) / (xc - peak)
            zu = st + p.up_verm + p.cupid * 0.35 - (p.up_verm + p.cupid * 0.35 - p.corner_up) * q ** 1.55
        zl = st - p.lo_verm * max(0.0, 1 - t ** 2.3) ** 0.62 + p.corner_up * t ** 2.2
        stom.append((x, zs))
        upper.append((x, max(zu, zs)))
        lower.append((x, min(zl, zs)))
    return stom, upper, lower


def ear_frame(p: FaceParams, side):
    """Ear attachment point (tragus root) and size."""
    rx = p.head[0]
    return dict(loc=(side * (rx - 3.0), 12.0, p.canthus - 14.0), size=p.ear_len / 60.0, out=p.ear_out)


def chart_of(pt):
    """(lon, lat) in radians of a point seen from the head centre (lon 0 = front, + = left)."""
    x, y, z = pt
    lon = math.atan2(x, -y)
    lat = math.atan2(z, math.hypot(x, y))
    return lon, lat

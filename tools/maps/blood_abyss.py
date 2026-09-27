"""Blood Moon Abyss: a crimson crater canyon under a blood-red moon.

The walkable ground is carved out of solid rock by capsules (``CARVES``): each
one is a flat (or linearly ramped) floor, and rock rises steeply everywhere
outside them. ``ground_height`` is pure Python so the Blender terrain builder
(blender/xianxia/realms.py, asset ``abyss_terrain``) and this layout share one
definition of the ground, and props and markers sit exactly on it.

Route (Godot coordinates, -Z = north): the canyon rim in the south-east
(PlayerSpawn, TeleportArray) -> two switchback ledges down the south wall ->
the canyon mouth -> the basin (BoneField, BloodPools, ObeliskRing, PrisonCages,
DemonCamp) -> the gorge closed by the fortress wall and DemonGate ->
FortressCourt, AltarOfBlood, PatriarchThrone. A narrow passage west of the
prison cages leads to the HeartMirror grotto; a spiral ledge east of the war
camp descends to the AbyssDepths.
"""
import math
import random

from . import common
from .layout import Sites, check_markers
from .terrain import Disc, Ground, Path, Rect, box

RIM_Y = 0.0
FLOOR_Y = -28.0
DEPTH_Y = -46.0
CAP_Y = 16.0
# terrain mesh extent (x0, z0, x1, z1) and grid step, used by the Blender builder
BOUNDS = (-300.0, -300.0, 292.0, 200.0)
STEP = 2.5

# Carved floors: (radius, [(x, z, y), ...]). A single point is a round floor, a
# poly-line a flat or ramped path whose height follows its nearest segment.
F = FLOOR_Y
CARVES = [
    # canyon rim ledge (south-east)
    (12.0, [(26, 104, RIM_Y), (44, 100, RIM_Y)]),
    # switchback descent: upper ledge heading west, turn, lower ledge heading east
    (4.4, [(22, 94, RIM_Y), (-40, 85, -12.0)]),
    (7.0, [(-44, 79, -12.0)]),
    (4.4, [(-44, 73, -12.0), (28, 76, -26.5), (36, 62, F)]),
    # trench at the foot of the descent and the canyon mouth
    (7.0, [(-38, 34, F), (-40, 58, F), (24, 64, F)]),
    (7.5, [(36, 62, F), (30, 40, F)]),
    # the basin
    (36.0, [(4, 16, F)]),
    (17.0, [(-38, 30, F)]),                       # bone field
    (18.0, [(36, 20, F)]),                        # blood pools
    (13.0, [(-40, -10, F), (-30, -16, F)]),       # prison cages
    (16.0, [(36, -20, F), (42, -30, F)]),         # war camp
    # gorge to the fortress, the court and the throne
    (15.0, [(0, -18, F), (0, -62, F)]),
    (24.0, [(-4, -80, F), (6, -80, F)]),
    (19.0, [(0, -86, F), (0, -110, F)]),
    # hidden passage to the heart mirror grotto
    (3.6, [(-46, -18, F), (-64, -26, F), (-70, -42, F)]),
    (13.0, [(-72, -56, F)]),
]
# the abyss: a pit ringed by a spiral ledge that starts east of the war camp
PIT = (84.0, -64.0)
PIT_R = 17.0
SPIRAL_R = 30.0
SPIRAL_A = (215.0, 40.0)        # start/end angle in degrees (x = cos, z = -sin): south-west, round the north
SPIRAL_Y = (FLOOR_Y, DEPTH_Y)


def _spiral():
    a0, a1 = SPIRAL_A
    n = 14
    pts = []
    for k in range(n + 1):
        t = k / n
        a = math.radians(a0 + (a1 - a0) * t)
        r = SPIRAL_R + 1.5 * math.sin(math.pi * t)
        pts.append((PIT[0] + r * math.cos(a), PIT[1] - r * math.sin(a),
                    SPIRAL_Y[0] + (SPIRAL_Y[1] - SPIRAL_Y[0]) * t))
    a = math.radians(a1 - 25.0)
    pts.append((PIT[0] + 12 * math.cos(a), PIT[1] - 12 * math.sin(a), DEPTH_Y))
    return [(6.5, [(58.0, -42.0, F)]), (4.6, pts), (PIT_R, [(PIT[0], PIT[1], DEPTH_Y)])]


CARVES += _spiral()

# -- the expanded abyss: new floors and the passages between them -------------------------------------
ASH_Y = -24.0
RIVER_Y = -30.0
CARVES += [
    # west: the blood river canyon, reached from the bone field; the corpse forest at its south end
    (8.0, [(-38, 30, F), (-70, 28, F), (-96, 30, RIVER_Y)]),
    (22.0, [(-112, 120, RIVER_Y), (-114, 60, RIVER_Y), (-112, 0, RIVER_Y), (-116, -60, RIVER_Y), (-120, -110, RIVER_Y)]),
    (34.0, [(-160, 118, RIVER_Y)]),                                  # the corpse forest
    (14.0, [(-44, 79, -12.0), (-96, 92, -12.0)]),                    # the wailing cliffs' ledge
    # north-west: the ash plains, the seal stones, the ghost village, the cave of echoes
    (10.0, [(-120, -110, RIVER_Y), (-140, -130, ASH_Y)]),
    (74.0, [(-190, -170, ASH_Y)]),
    (8.0, [(-230, -110, ASH_Y), (-248, -60, -22.0)]),
    (30.0, [(-250, -40, -22.0)]),
    (6.0, [(-262, -64, -22.0), (-276, -104, -22.0)]),
    (8.0, [(-276, -110, -22.0)]),
    # the shadow market beside the grotto passage, and the slave mines in the canyon wall
    (6.0, [(-64, -26, F), (-100, -46, F)]),
    (22.0, [(-112, -52, F)]),
    (12.0, [(-148, 30, RIVER_Y), (-160, 30, RIVER_Y)]),
    (14.0, [(-150, -20, RIVER_Y), (-164, -30, RIVER_Y)]),
    # north: the elders' palace behind the throne, the forge, the sacrifice pit, library and shrine,
    # the red moon terrace (raised), the first patriarch's bone throne
    (9.0, [(0, -108, F), (0, -136, F)]),
    (36.0, [(0, -166, F)]),
    (8.0, [(-30, -160, F), (-66, -128, F)]),
    (22.0, [(-70, -120, F)]),
    (8.0, [(-30, -176, F), (-70, -176, F)]),
    (26.0, [(-78, -176, F)]),
    (8.0, [(30, -170, F), (52, -164, F)]),
    (14.0, [(56, -164, F)]),
    (8.0, [(30, -190, F), (46, -206, F)]),
    (14.0, [(50, -210, F)]),
    (6.0, [(0, -202, F), (0, -222, -18.0), (0, -234, -12.0)]),
    (18.0, [(0, -250, -12.0)]),
    (6.0, [(-26, -196, F), (-56, -236, F)]),
    (22.0, [(-66, -246, F)]),
    # north-east: the barracks of black tents, the training pit, the beast pens
    (8.0, [(42, -30, F), (100, -60, F), (118, -100, F)]),
    (36.0, [(110, -140, F)]),
    # east: sulphur vents, the skull tower's spur, the obsidian spires, the lava falls, the watch spire
    (7.0, [(52, 22, F), (100, 26, F), (140, 30, F)]),
    (16.0, [(148, 30, F)]),
    (6.0, [(100, 26, F), (110, 52, -22.0), (112, 64, -18.0)]),
    (12.0, [(114, 66, -18.0)]),
    (36.0, [(184, -14, F)]),
    (28.0, [(236, 34, F)]),
    (8.0, [(160, 44, F), (190, 70, F)]),
    (26.0, [(196, 78, F)]),
    # across the bottomless chasm: the ruined sect, the Blood Moon's first conquest
    (34.0, [(196, 150, F)]),
    (7.0, [(170, 118, F), (196, 124, F)]),
    # the canyon rim: the watch spire, and the poison garden at the canyon mouth
    (10.0, [(44, 100, RIM_Y), (70, 110, RIM_Y)]),
    (8.0, [(44, 58, F), (70, 76, F)]),
    (15.0, [(80, 82, F)]),
]
CHASM = Path([(140, 102), (180, 100), (220, 102), (270, 100)], 22.0, samples=3)
CHASM_Y = -140.0

# raised daises: (x, z, flat radius, outer radius, height)
BUMPS = [
    (0.0, 4.0, 9.0, 13.5, 1.2),          # obelisk ring
    (-16.0, -85.0, 7.0, 11.0, 1.1),      # altar of blood
]
# blood pool depressions: (x, z, rx, rz, depth, seed)
POOLS = [
    (46.0, 12.0, 6.5, 4.8, 1.5, 1),
    (28.0, 30.0, 5.0, 4.2, 1.4, 2),
    (48.0, 30.0, 4.2, 3.5, 1.3, 3),
    (24.0, 8.0, 3.6, 3.0, 1.2, 4),
    (91.0, -49.0, 5.0, 4.0, 1.5, 5),     # abyss depths
    (72.0, -74.0, 4.8, 4.0, 1.4, 6),
    (-12.0, 60.0, 3.8, 3.2, 1.2, 7),     # below the descent
]


# --------------------------------------------------------------------------
# deterministic noise (pure Python so the map builder needs no dependencies)
# --------------------------------------------------------------------------
def _hash(ix, iz, seed):
    h = (ix * 374761393 + iz * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, z, seed=0):
    """Value noise in [0, 1]."""
    ix, iz = math.floor(x), math.floor(z)
    fx, fz = x - ix, z - iz
    sx, sz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a, b = _hash(ix, iz, seed), _hash(ix + 1, iz, seed)
    c, d = _hash(ix, iz + 1, seed), _hash(ix + 1, iz + 1, seed)
    top = a + (b - a) * sx
    bot = c + (d - c) * sx
    return top + (bot - top) * sz


def fbm(x, z, octaves=4, seed=0):
    """Fractal noise in about [-1, 1]."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * (vnoise(x, z, seed + o * 31) * 2 - 1)
        norm += amp
        amp *= 0.5
        x, z = x * 2.03 + 17.1, z * 2.03 - 9.7
    return total / norm


def _sstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


_CARVE_BOX = []


def _carve_boxes():
    for r, pts in CARVES:
        xs = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        _CARVE_BOX.append((min(xs), min(zs), max(xs), max(zs), min(p[2] for p in pts)))


def carve(x, z):
    """(height of the carved ground, distance outside the nearest carved floor)."""
    if len(_CARVE_BOX) != len(CARVES):
        _CARVE_BOX.clear()
        _carve_boxes()
    best, dist = 1e9, 0.0
    for (r, pts), (bx0, bz0, bx1, bz1, ymin) in zip(CARVES, _CARVE_BOX):
        # skip a carve whose nearest possible floor is already higher than the best found
        db = max(math.hypot(max(bx0 - x, 0.0, x - bx1), max(bz0 - z, 0.0, z - bz1)) - r, 0.0)
        if ymin + 2.7 * db + 0.06 * db * db > best:
            continue
        dmin, y = 1e9, pts[0][2]
        if len(pts) == 1:
            dmin = math.hypot(x - pts[0][0], z - pts[0][1])
        for (ax, az, ya), (bx, bz, yb) in zip(pts[:-1], pts[1:]):
            dx, dz = bx - ax, bz - az
            t = min(1.0, max(0.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)))
            dd = math.hypot(x - ax - dx * t, z - az - dz * t)
            if dd < dmin:
                dmin, y = dd, ya + (yb - ya) * t
        d = dmin - r
        v = y + (2.7 * d + 0.06 * d * d if d > 0 else 0.0)
        if v < best:
            best, dist = v, d
    return best, dist


def pool_shape(x, z, pool):
    """Normalised distance to a pool centre (1 = pool edge), with a noisy outline."""
    px, pz, rx, rz, _, seed = pool
    ex, ez = (x - px) / rx, (z - pz) / rz
    a = math.atan2(ez, ex)
    wob = 1.0 + 0.16 * fbm(math.cos(a) * 1.3 + seed * 5.1, math.sin(a) * 1.3, 3, seed)
    return math.hypot(ex, ez) / wob


def ground_height(x, z):
    """Walkable ground height (Godot y) at Godot (x, z); rock walls outside the carves."""
    h, d = carve(x, z)
    wall = _sstep(0.4, 4.0, d)
    # gentle undulation on the floors, jagged strata on the walls
    h += 0.3 * fbm(x / 26.0, z / 26.0, 3, 11)
    h += wall * (3.2 * fbm(x / 7.0, z / 7.0, 4, 23) + 1.6 * abs(fbm(x / 3.0, z / 3.0, 2, 29)))
    # basalt strata: terrace the cliffs into ledges and risers
    t = h / 3.2
    terr = 3.2 * (math.floor(t) + _sstep(0.6, 1.0, t - math.floor(t)))
    h += (terr - h) * 0.75 * wall
    cap = CAP_Y + 5.0 * fbm(x / 20.0, z / 20.0, 3, 41)
    spike = vnoise(x / 8.0, z / 8.0, 43)
    cap += 14.0 * max(0.0, spike - 0.58) / 0.42
    h = min(h, cap)
    for bx, bz, r0, r1, bh in BUMPS:
        h += bh * _sstep(r1, r0, math.hypot(x - bx, z - bz))
    for pool in POOLS:
        h -= pool[4] * _sstep(1.0, 0.5, pool_shape(x, z, pool))
    return h


def pool_level(pool):
    """Height of a pool's liquid surface: below the lowest point of its rim."""
    px, pz, rx, rz, depth, _ = pool
    rim = min(ground_height(px + rx * 0.85 * math.cos(a), pz + rz * 0.85 * math.sin(a))
              for a in [2 * math.pi * k / 24 for k in range(24)])
    return rim - 0.12


# --------------------------------------------------------------------------
# the ground of the whole abyss (terrain.Ground: building plots, the chasm, regions, liquids)
# --------------------------------------------------------------------------
def _classify(x, z, h, nz):
    if nz < 0.74 or carve(x, z)[1] > 2.5:
        return "abyss_rock"
    return "abyss_soil"


G = Ground(BOUNDS, STEP, ground_height, _classify, chunk=40)
G.floor = None
G.pad(CHASM, CHASM_Y, blend=4, op="min")
BLOOD_RIVER = Path([(-112, 150), (-112, 118), (-114, 60), (-112, 0), (-116, -60), (-120, -112), (-140, -135)], 11.0,
                   samples=3)
G.pad(BLOOD_RIVER, RIVER_Y - 2.2, blend=2.5, op="min")
SACRIFICE = Disc(-78, -176, 8.0)
G.pad(SACRIFICE, F - 7.0, blend=3.0, op="min")
TRAINING = Rect(128, -150, 10, 10, 0, 2)
G.pad(TRAINING, F - 2.4, blend=3.0)
LAVA_POOL = Disc(240, 24, 11.0, wobble=0.1, seed=5)
G.pad(LAVA_POOL, F - 1.0, blend=3.0, op="min")
BONE_BRIDGE = (-112.0, 24.0)
CHAIN_BRIDGE = (196.0, 101.0)

S = Sites(G)
S.add("demon_palace", 0, -176, 0, F, name="ElderPalaceHall")
S.add("demon_library", 56, -166, -90, F, name="DemonLibraryTower")
S.add("blood_moon_shrine", 50, -212, 0, F, name="BloodMoonShrineDais", solid=False)
S.add("soul_forge", -70, -126, 60, F, name="SoulForge")
S.add("mine_entrance", -168, 28, 90, RIVER_Y, name="SlaveMineAdit", flatten=False)
S.add("mine_entrance", -170, -30, 70, RIVER_Y, name="DeepShaftAdit", flatten=False)
S.add("ruined_hall", 196, 168, 180, F, name="RuinedSectHallBuilding")
S.add("ruined_gate", 196, 130, 0, F, name="RuinedSectGateArch")
S.add("watch_spire", 70, 114, 0, RIM_Y, name="WatchSpireTower")
S.add("bone_throne", -66, -252, 0, F, name="FirstPatriarchThrone")
S.add("skull_tower", 114, 72, 0, -18.0, name="SkullTowerSpire")
S.add("iron_pens", 100, -126, 0, F, name="BeastPensIron")
for _i, (_x, _z) in enumerate(((-236, -50), (-262, -30), (-250, -18), (-226, -28), (-262, -52))):
    S.add("ghost_house", _x, _z, (_i * 71) % 360, -22.0, name=f"GhostHouse{_i + 1}")
for _i, (_x, _z, _yw) in enumerate(((-122, -40, 90), (-100, -62, 0), (-124, -62, 30), (-98, -40, 200))):
    S.add("shadow_stall", _x, _z, _yw, F, name=f"ShadowStall{_i + 1}")

# regions
G.region("abyss_blocks", Rect(0, -85, 14, 12, 0, 3))                 # the fortress court
G.region("abyss_blocks", Disc(0, -166, 24))                          # the palace terrace
G.region("abyss_blocks", Disc(-112, -52, 16))                        # the shadow market
G.region("abyss_blocks", Disc(0, -250, 14))                          # the red moon terrace
G.region("abyss_blocks", Disc(-66, -246, 10))
G.region("abyss_blocks", Disc(196, 150, 22, wobble=0.2, seed=7))     # the ruined sect's courtyard
G.region("bone_ground", Disc(-38, 30, 15, wobble=0.2, seed=2))
G.region("ash", Disc(-190, -170, 70, wobble=0.1, seed=3))
G.region("ash", Disc(-250, -40, 24))
G.region("bone_ground", Disc(-160, 118, 30, wobble=0.2, seed=4))
G.region("abyss_rock", Path(BLOOD_RIVER.pts, 13.0))
G.region("abyss_rock", SACRIFICE)
G.region("abyss_rock", TRAINING)
G.region("abyss_rock", LAVA_POOL)
G.water("blood", Path(BLOOD_RIVER.pts, 12.5), RIVER_Y - 0.6)
G.water("lava", Disc(240, 24, 12.0), F - 0.3)
G.water("blood", Disc(-78, -176, 5.5), F - 5.5)
for _pool in POOLS:
    G.water("blood", Disc(_pool[0], _pool[1], _pool[2] * 1.02, sz=_pool[3] / _pool[2]), pool_level(_pool))


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------
MARKERS = {
    "PlayerSpawn": (30.0, 101.0),
    "TeleportArray": (38.0, 106.0),
    "CanyonEntrance": (33.0, 47.0),
    "BoneField": (-38.0, 30.0),
    "BloodPools": (37.0, 21.0),
    "ObeliskRing": (0.0, 4.0),
    "PrisonCages": (-34.0, -12.0),
    "DemonCamp": (38.0, -24.0),
    "DemonGate": (0.0, -40.0),
    "FortressCourt": (0.0, -64.0),
    "AltarOfBlood": (-16.0, -79.0),
    "PatriarchThrone": (0.0, -99.0),
    "HeartMirror": (-72.0, -49.0),
    "AbyssDepths": (84.0, -64.0),
}
GATE_Z = -50.0
THRONE = (0.0, -99.0)            # patriarch_throne origin = centre of its arena


def along(pts, t, off):
    """Point at fraction t (by length) of a carve poly-line, offset sideways by off metres
    (positive = to the right of the direction of travel, in Godot x/z)."""
    segs = [(p, q, math.hypot(q[0] - p[0], q[1] - p[1])) for p, q in zip(pts[:-1], pts[1:])]
    target = t * sum(s[2] for s in segs)
    for p, q, ln in segs:
        if target <= ln or (p, q, ln) == segs[-1]:
            f = min(1.0, target / ln)
            dx, dz = (q[0] - p[0]) / ln, (q[1] - p[1]) / ln
            return p[0] + (q[0] - p[0]) * f - dz * off, p[1] + (q[1] - p[1]) * f + dx * off
        target -= ln
    return pts[-1][0], pts[-1][1]


def face(x, z, tx, tz):
    """Yaw (common.xform, where Godot rotation.y = -yaw) turning a model's front (+Z) toward (tx, tz)."""
    return math.degrees(math.atan2(-(tx - x), tz - z))


def build():
    rnd = random.Random(13)
    items = []

    def gy(x, z):
        return G.height(x, z)

    def add(asset, x, z, yaw=0.0, scale=1.0, name=None, dy=-0.1, y=None):
        items.append((asset, name, (x, gy(x, z) + dy if y is None else y, z), yaw, scale))

    items.append(("abyss_terrain", "Terrain", (0.0, 0.0, 0.0), 0.0, 1.0))

    # --- canyon rim -------------------------------------------------------
    tx, tz = MARKERS["TeleportArray"]
    add("teleport_array", tx, tz, yaw=-10, name="TeleportArray", dy=0.0)
    for x, z, yaw in ((22, 108, 90), (48, 96, -80)):
        add("demon_banner", x, z, yaw=yaw)
    for x, z in ((20, 100), (46, 108), (34, 113)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(1.0, 1.5))
    add("dead_tree", 44, 92, yaw=40, scale=1.1)
    add("bone_pile", 26, 94, yaw=20)
    add("demon_obelisk", 16, 95, yaw=-15, scale=0.8)
    # --- the descent: banners and rocks against the cliff side of the ledges ------
    upper, lower = CARVES[1][1], CARVES[3][1]
    for t in (0.3, 0.62, 0.9):
        x, z = along(upper, t, -3.4)
        add("demon_banner", x, z, yaw=180, scale=0.85)
    for t in (0.18, 0.47, 0.77):
        x, z = along(upper, t, -6.2)
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.2))
    for t in (0.15, 0.45, 0.72):
        x, z = along(lower, t, 3.4)
        add("demon_banner", x, z, yaw=180, scale=0.85)
    for t in (0.3, 0.6):
        x, z = along(lower, t, 6.0)
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.8, 1.1))
    add("dead_tree", -50, 82, yaw=120)
    add("bone_pile", -48, 77, yaw=80, scale=0.8)
    # --- canyon mouth -----------------------------------------------------
    for x, z, s in ((24, 50, 1.6), (42, 44, 1.8), (22, 38, 1.3), (40, 60, 1.2)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=s)
    add("demon_obelisk", 26, 44, yaw=30)
    add("demon_obelisk", 40, 50, yaw=-40)
    add("dead_tree", 38, 38, yaw=200, scale=1.2)
    # --- bone field -------------------------------------------------------
    bx, bz = MARKERS["BoneField"]
    for k in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(7, 15)
        add("bone_pile", bx + math.cos(a) * r, bz + math.sin(a) * r, yaw=rnd.uniform(0, 360),
            scale=rnd.uniform(0.8, 1.4))
    for x, z, s in ((-47, 38, 1.3), (-30, 40, 1.0), (-48, 22, 1.15), (-24, 35, 0.9), (-44, 16, 1.1)):
        add("dead_tree", x, z, yaw=rnd.uniform(0, 360), scale=s)
    add("spiky_rocks", -52, 32, yaw=10, scale=1.6)
    # --- blood pools ------------------------------------------------------
    for x, z in ((54, 20), (30, 4), (18, 20)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(1.0, 1.4))
    add("dead_tree", 52, 36, yaw=70)
    add("bone_pile", 42, 24, yaw=10, scale=0.7)
    # --- obelisk ring on its dais -------------------------------------------
    ox, oz = MARKERS["ObeliskRing"]
    for k in range(6):
        a = 2 * math.pi * k / 6
        x, z = ox + math.cos(a) * 7.5, oz + math.sin(a) * 7.5
        add("demon_obelisk", x, z, yaw=face(x, z, ox, oz), dy=-0.15)
    # --- prison cages -----------------------------------------------------
    px, pz = MARKERS["PrisonCages"]
    for dx, dz, yaw in ((-7, -6, 30), (-9, 2, 80), (-2, -9, -10), (6, -8, -40), (-10, -7, 50)):
        add("prison_cage", px + dx, pz + dz, yaw=yaw)
    add("dead_tree", px - 14, pz + 6, yaw=10, scale=1.1)
    add("bone_pile", px + 3, pz + 8, yaw=60, scale=0.7)
    add("demon_banner", px + 8, pz - 3, yaw=-90, scale=0.9)
    # --- war camp: tents in a ring, open toward the basin (NW) and the spiral (SE) ---
    cx, cz = MARKERS["DemonCamp"]
    for deg in (200, 245, 280, 25, 65, 100):
        a = math.radians(deg)
        x, z = cx + 11.0 * math.cos(a), cz + 11.0 * math.sin(a)
        add("demon_tent", x, z, yaw=face(x, z, cx, cz))
    for deg in (180, 270, 0, 90):
        a = math.radians(deg + 20)
        x, z = cx + 6.5 * math.cos(a), cz + 6.5 * math.sin(a)
        add("demon_banner", x, z, yaw=face(x, z, cx, cz), scale=0.9)
    a = math.radians(45)
    add("blood_altar", cx + 9.0 * math.cos(a), cz + 9.0 * math.sin(a), yaw=-45, scale=0.55, name="CampAltar")
    add("bone_pile", cx + 15, cz + 2, yaw=90)
    # --- gorge, fortress wall and gate ------------------------------------
    add("demon_gate", 0.0, GATE_Z, name="DemonGate", dy=-0.4)
    for x in (-14.0, -22.0, 14.0, 22.0):
        add("fortress_wall", x, GATE_Z, dy=-0.6)
    for x in (-8.0, 8.0):
        add("demon_banner", x, GATE_Z + 7.0, yaw=0)
    for x, z in ((-11, -30), (12, -34), (-13, -22), (13, -18)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(1.0, 1.4))
    add("dead_tree", 10, -26, yaw=150)
    # --- fortress court ---------------------------------------------------
    for x, z in ((-12, -60), (12, -60), (-20, -70), (20, -70)):
        add("demon_banner", x, z, yaw=0 if x < 0 else 0, scale=1.0)
    for x, z in ((-25, -66), (24, -86), (26, -72), (-24, -100), (18, -108)):
        add("demon_obelisk", x, z, yaw=rnd.uniform(0, 360))
    for x, z in ((22, -62), (-28, -84), (28, -94)):
        add("bone_pile", x, z, yaw=rnd.uniform(0, 360))
    for x, z in ((-26, -58), (27, -58)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=1.4)
    ax, az = MARKERS["AltarOfBlood"]
    add("blood_altar", ax, az - 8.0, yaw=0, name="BloodAltar")
    add("patriarch_throne", THRONE[0], THRONE[1], name="PatriarchThrone", dy=-0.2)
    # --- heart mirror grotto ----------------------------------------------
    hx, hz = MARKERS["HeartMirror"]
    add("heart_pool", hx, hz - 11.0, name="HeartPool", dy=-0.05)
    for x, z, s in ((-80, -60, 1.3), (-64, -62, 1.2), (-66, -46, 0.9), (-80, -48, 1.0), (-59, -30, 1.1)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=s)
    add("dead_tree", -82, -52, yaw=200, scale=0.8)
    # --- abyss depths -----------------------------------------------------
    dx, dz = MARKERS["AbyssDepths"]
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.6
        x, z = dx + math.cos(a) * 14.5, dz + math.sin(a) * 14.5
        add("demon_obelisk", x, z, yaw=face(x, z, dx, dz))
    for x, z, s in ((70, -54, 1.2), (101, -64, 1.5), (97, -46, 1.0), (78, -80, 1.3)):
        add("spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=s)
    for x, z in ((74, -64), (92, -76)):
        add("bone_pile", x, z, yaw=rnd.uniform(0, 360), scale=1.2)
    add("dead_tree", 60, -34, yaw=30)

    build_districts(add, gy, rnd)

    markers = {n: (x, gy(x, z) + 1.0, z) for n, (x, z) in MARKERS.items()}
    markers["TeleportArray"] = (tx, gy(tx, tz) + 0.9, tz)
    tpx, tpz = THRONE
    markers["PatriarchThrone"] = (tpx, gy(tpx, tpz) + 2.4, tpz)
    markers.update({n: (x, gy(x, z) + 1.0, z) for n, (x, z) in NEW_MARKERS.items()})
    markers["BoneBridge"] = (BONE_BRIDGE[0], RIVER_Y + 1.2 + 1.0, BONE_BRIDGE[1])
    markers["ChainBridge"] = (CHAIN_BRIDGE[0], F + 1.0, CHAIN_BRIDGE[1])
    problems = check_markers("blood_abyss", {k: markers[k] for k in NEW_MARKERS}, G.height, S.solids,
                             exempt=("BoneBridge", "ChainBridge"))
    if problems:
        raise SystemExit("blood_abyss marker problems:" + "".join("\n  " + p for p in problems))

    env = common.Env(
        sky=common.Sky(top=(0.07, 0.025, 0.04), horizon=(0.5, 0.13, 0.09),
                       ground_bottom=(0.22, 0.1, 0.09), ground_horizon=(0.4, 0.14, 0.11),
                       curve=0.22, sun_angle_max=30.0),
        ambient_energy=3.2, exposure=1.32,
        fog_color=(0.26, 0.08, 0.07), fog_density=0.0026, fog_height=-32.0,
        fog_height_density=0.02, fog_sun_scatter=0.3, fog_sky_affect=0.2,
        glow_intensity=0.8, saturation=0.95, contrast=1.08,
        sun_pitch=-58.0, sun_yaw=160.0, sun_color=(1.0, 0.55, 0.46), sun_energy=1.35,
        shadow_distance=160.0,
    )
    return common.MapDef("blood_abyss", "Blood Moon Abyss", "abyss", items, markers, env=env,
                         ambient="embers", kill_y=-75.0)


NEW_MARKERS = {
    "BloodRiver": (-100.0, 64.0),
    "BoneBridge": BONE_BRIDGE,
    "SlaveMines": (-146.0, 30.0),
    "MineShaft": (-152.0, -22.0),
    "ForgeOfSouls": (-54.0, -116.0),
    "Barracks": (122.0, -128.0),
    "TrainingPit": (128.0, -150.0),
    "BeastPens": (100.0, -114.0),
    "PoisonGarden": (80.0, 82.0),
    "SkullTower": (108.0, 62.0),
    "WailingCliffs": (-70.0, 85.0),
    "AshPlains": (-190.0, -170.0),
    "LavaFalls": (222.0, 40.0),
    "ObsidianSpires": (184.0, -14.0),
    "SacrificePit": (-78.0, -160.0),
    "DemonLibrary": (42.0, -166.0),
    "ElderPalace": (0.0, -150.0),
    "ShadowMarket": (-112.0, -51.0),
    "BloodMoonShrine": (50.0, -212.0),
    "CorpseForest": (-160.0, 118.0),
    "RuinedSectGate": (196.0, 122.0),
    "RuinedSectHall": (196.0, 148.0),
    "ChainBridge": CHAIN_BRIDGE,
    "WatchSpire": (58.0, 106.0),
    "SealStones": (-172.0, -146.0),
    "GhostVillage": (-246.0, -38.0),
    "RedMoonTerrace": (0.0, -250.0),
    "CaveOfEchoes": (-274.0, -106.0),
    "SulphurVents": (148.0, 30.0),
    "BoneThrone": (-66.0, -236.0),
}


def build_districts(add, gy, rnd):
    for asset, name, x, z, yaw, level, scale in S.items:
        add(asset, x, z, yaw=yaw, scale=scale, name=name, y=level - 0.05)
    # bridges
    add("bone_bridge", BONE_BRIDGE[0], BONE_BRIDGE[1], yaw=90, name="BoneBridgeSpan", y=RIVER_Y + 0.1)
    add("chain_bridge_dark", CHAIN_BRIDGE[0], CHAIN_BRIDGE[1], yaw=0, name="ChainBridgeSpan", y=F)
    # the blood river's banks
    for z in range(-90, 140, 22):
        for side in (-1, 1):
            x = -113 + side * rnd.uniform(15, 20)
            add("spiky_rocks", x, z + rnd.uniform(-5, 5), yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.4))
    for k in range(10):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(6, 26)
        x, z = -160 + r * math.cos(a), 118 + r * math.sin(a)
        add("hanged_tree" if k % 3 == 0 else "dead_tree", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.3))
    for k in range(6):
        add("bone_pile", -160 + rnd.uniform(-24, 24), 118 + rnd.uniform(-24, 24), yaw=rnd.uniform(0, 360))
    # the wailing cliffs: bones and banners on the ledge
    for x in (-70, -98):
        add("demon_banner", x, 97, yaw=180, scale=0.9)
    add("bone_pile", -100, 86, yaw=30, scale=0.8)
    # the ash plains: seal stones in a ring, dead trees, spikes
    for k in range(7):
        a = 2 * math.pi * k / 7
        x, z = -172 + 9 * math.cos(a), -146 + 9 * math.sin(a)
        add("seal_stone", x, z, yaw=math.degrees(-a) + 90, name=f"SealStone{k + 1}")
    for k in range(18):
        x, z = -190 + rnd.uniform(-60, 60), -170 + rnd.uniform(-60, 60)
        if math.hypot(x + 172, z + 146) < 16 or math.hypot(x + 190, z + 170) < 8:
            continue
        add("dead_tree" if k % 3 else "spiky_rocks", x, z, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.8, 1.4))
    for k in range(5):
        x, z = -250 + rnd.uniform(-20, 20), -40 + rnd.uniform(-20, 20)
        if math.hypot(x + 246, z + 38) < 7:
            continue
        add("dead_tree", x, z, yaw=rnd.uniform(0, 360), scale=0.8)
    add("cave_mouth", -284, -112, yaw=70, scale=1.2, name="CaveOfEchoesMouth")
    # the elders' palace precinct
    for x in (-14, 14):
        add("demon_obelisk", x, -150, yaw=0)
    add("blood_altar", -30, -170, yaw=90, scale=0.6, name="PalaceAltar")
    add("sacrifice_ring", -78, -176, name="SacrificeRing", y=F)
    for x, z in ((-40, -196), (40, -196), (-30, -140), (30, -140)):
        add("demon_banner", x, z, yaw=0)
    add("demon_obelisk", -10, -250 - 8, yaw=0)
    add("demon_obelisk", 10, -250 - 8, yaw=0)
    add("blood_altar", 0, -262, yaw=0, scale=0.8, name="RedMoonAltar")
    # barracks and the training pit
    for k in range(7):
        a = math.radians(200 + k * 24)
        x, z = 110 + 22 * math.cos(a), -140 + 22 * math.sin(a)
        add("demon_tent", x, z, yaw=face(x, z, 110, -140))
    for x, z in ((118, -142), (138, -158), (138, -142), (118, -158)):
        add("demon_banner", x, z, yaw=face(x, z, 128, -150), scale=0.8)
    # the east: sulphur vents, spires, lava falls
    for k in range(5):
        a = 2 * math.pi * k / 5
        add("sulphur_vent", 148 + 8 * math.cos(a), 30 + 8 * math.sin(a), yaw=rnd.uniform(0, 360),
            scale=rnd.uniform(0.8, 1.2))
    for k in range(16):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(9, 32)
        x, z = 184 + r * math.cos(a), -14 + r * math.sin(a)
        add("obsidian_spire" if k % 3 == 0 else "obsidian_spire_small", x, z, yaw=rnd.uniform(0, 360),
            scale=rnd.uniform(0.8, 1.3))
    add("lava_fall", 252, 16, yaw=-50, name="LavaFallsCurtain", y=F - 0.5)
    add("poison_flowers", 86, 92, yaw=0, name="PoisonFlowerBed")
    add("poison_flowers", 70, 72, yaw=90, scale=0.8)
    # the ruined sect across the chasm
    for x, z in ((180, 146), (212, 146), (176, 164), (214, 168)):
        add("broken_pillar", x, z, yaw=rnd.uniform(0, 360))
    for x, z in ((170, 136), (222, 136)):
        add("ruin_wall", x, z, yaw=90)
    # the first patriarch's bone throne, the shadow market's lanterns
    add("bone_pile", -80, -250, yaw=40)
    add("bone_pile", -52, -252, yaw=120)
    add("demon_banner", -112, -34, yaw=180)

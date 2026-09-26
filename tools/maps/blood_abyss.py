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

RIM_Y = 0.0
FLOOR_Y = -28.0
DEPTH_Y = -46.0
CAP_Y = 16.0
# terrain mesh extent (x0, z0, x1, z1) and grid step, used by the Blender builder
BOUNDS = (-112.0, -142.0, 140.0, 128.0)
STEP = 1.5

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


def carve(x, z):
    """(height of the carved ground, distance outside the nearest carved floor)."""
    best, dist = 1e9, 0.0
    for r, pts in CARVES:
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
        return ground_height(x, z)

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

    markers = {n: (x, gy(x, z) + 1.0, z) for n, (x, z) in MARKERS.items()}
    markers["TeleportArray"] = (tx, gy(tx, tz) + 0.9, tz)
    tpx, tpz = THRONE
    markers["PatriarchThrone"] = (tpx, gy(tpx, tpz) + 2.4, tpz)

    env = common.Env(
        sky=common.Sky(top=(0.07, 0.025, 0.04), horizon=(0.5, 0.13, 0.09),
                       ground_bottom=(0.22, 0.1, 0.09), ground_horizon=(0.4, 0.14, 0.11),
                       curve=0.22, sun_angle_max=30.0),
        ambient_energy=2.6, exposure=1.25,
        fog_color=(0.26, 0.08, 0.07), fog_density=0.0026, fog_height=-32.0,
        fog_height_density=0.02, fog_sun_scatter=0.3, fog_sky_affect=0.2,
        glow_intensity=0.8, saturation=0.95, contrast=1.08,
        sun_pitch=-58.0, sun_yaw=160.0, sun_color=(1.0, 0.55, 0.46), sun_energy=1.35,
        shadow_distance=160.0,
    )
    return common.MapDef("blood_abyss", "Blood Moon Abyss", "abyss", items, markers, env=env,
                         ambient="embers", kill_y=DEPTH_Y - 25.0)

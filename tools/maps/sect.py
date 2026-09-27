"""Azure Cloud Sect: the mountain-top sect and the terraces of the whole massif around it.

The walled sect of the first map (its layout, random seeds and markers) is untouched in the middle;
around it the mountain now carries the rest of the sect, about ten times the old area:

* south, 14 m lower: the outer sect terrace (outer sect hall, mission hall, contribution pavilion,
  refectory, rows of dormitories above the laundry stream), reached from the processional way by the
  long stone stairway; the mountain road winds up to it from a landing far below
* east, level with the plaza: the martial arena (stage and stands) between the bell and drum towers,
  the formation hall in its ring of rune pillars, the nine-storey treasure tower, the sunrise terrace
* north, 14 m higher, behind the inner sect gate and its stairway: the core disciples' cottages, the
  ancestral tombs among cypresses, the Cliff of Reflection, and the switchback path to a spur from which
  the chain bridge crosses the gorge to Sword Peak (the sword tomb and the sword-washing pool)
* below the east terrace's cliff, 22 m lower: the medicine valley with its pill kilns, the spirit beast
  garden and the crane roost, fed by the Hundred-Chi waterfall (a meditation cave behind it)
* south-east, stepping down: the spirit tea terraces and the peach orchard

Everything stands on one ``terrain.Ground`` (built into the sect_terrain GLB by
blender/xianxia/lands.py): the terraces are pads over a chasm floor far below the clouds, so a fall off
the edge is a fall into the sea of clouds (kill_y).
"""
import math
import random

from . import common
from .layout import Sites, check_markers
from .terrain import Disc, Ground, Path, Rect, box, fbm2, smoothstep

TELEPORT = (12.0, 0.0, 41.5)
WALL_HALF_X = 29.0
WALL_NORTH = -50.0
WALL_SOUTH = 30.0
SEGMENT = 8.0

# terrace levels
S_Y, N_Y, V_Y = -14.0, 14.0, -22.0
PEAK_Y = 40.0
CHASM = -110.0
KILL_Y = -70.0

POND = (18.0, 2.0, 7.0, 6.0, 1.3)     # Godot x, z, rx, rz, depth (as the first terrain)


def _base(x, z):
    return CHASM + 10.0 * fbm2(x * 0.012, z * 0.012, 3, 5)


def _classify(x, z, h, nz):
    if nz < 0.74 or h < -45:
        return "cliff_sect"
    return "grass_sect"


def _core_level(x, z):
    """The plateau of the first map: level, with a gentle roll outside the walled area."""
    inner = math.hypot(max(abs(x) - 44.0, 0), max(abs(z) - 70.0, 0))
    if inner <= 0:
        return 0.0
    return 0.6 * fbm2(x * 0.03, z * 0.03, 3, 7) * min(1.0, inner / 10.0)


def _pond_level(x, z):
    px, pz, rx, rz, depth = POND
    pr = math.hypot((x - px) / rx, (z - pz) / rz)
    k = max(0.0, min(1.0, (1.25 - pr) / 0.45))
    return -depth * (k * k * (3 - 2 * k))


def _roll(level, amp=0.5, seed=9):
    return lambda x, z: level + amp * fbm2(x * 0.04, z * 0.04, 2, seed)


def _tea_level(x, z):
    """Contour terraces stepping down southward from the outer terrace to the orchard."""
    t = max(0.0, (z - 186.0) / 7.0)
    k = math.floor(t)
    return S_Y - 2.0 - 1.4 * (k + smoothstep(0.8, 1.0, t - k))


G = Ground((-300.0, -300.0, 300.0, 330.0), 2.5, _base, _classify, chunk=40)
G.floor = -80.0

# ---- the districts (later pads override earlier ones) ---------------------------------------------
G.pad(box(-196, 70, 88, 224, r=18), _roll(S_Y, 0.4, 11), blend=16)            # south: the outer sect
G.pad(box(52, -78, 214, 58, r=16), _roll(0.0, 0.3, 12), blend=16)              # east: arena and towers
G.pad(box(-124, -218, 124, -60, r=18), _roll(N_Y, 0.4, 13), blend=18)          # north: inner sect
G.pad(Disc(-150, -172, 30), _roll(22.0, 1.5, 14), blend=18)                    # the spur below Sword Peak
G.pad(Disc(-252, -195, 27, wobble=0.12, seed=3), _roll(PEAK_Y, 0.6, 15), blend=10)   # Sword Peak
G.pad(box(92, 62, 240, 198, r=20), _roll(V_Y, 0.5, 16), blend=8)               # medicine valley
G.pad(box(58, 184, 176, 262, r=12), _tea_level, blend=10)                      # tea terraces
G.pad(box(40, 258, 178, 300, r=16), _roll(-36.0, 0.5, 17), blend=10)           # peach orchard
G.pad(Disc(-40, 316, 20), -36.0, blend=10)                                     # road landing below
G.pad(Rect(0, 0, 62, 78, 0, 10), _core_level, blend=26)                        # the plateau of the first map
# raised bits and hollows
G.pad(Disc(92, -40, 19), 3.0, blend=9)                                         # the bell tower's ridge
G.pad(Disc(222, 136, 11), V_Y + 6.0, blend=9)                                  # the crane roost knoll
G.pad(Disc(-172, -195, 10), PEAK_Y, blend=8)                                   # the bridgehead platform

# ---- roads, ramps and stairs (level callables follow the path) ---------------------------------------
STEPS_S = Path([(0, 112.5, S_Y - 0.3), (0, 108.0, S_Y - 0.3), (0, 81.4, -0.3), (0, 77.0, 0.0)], 9.0)
STEPS_N = Path([(0, -79.0, -0.3), (0, -80.5, -0.3), (0, -107.1, N_Y - 0.3), (0, -111.5, N_Y)], 11.0)
G.pad(STEPS_S, STEPS_S.level, blend=4)
G.pad(STEPS_N, STEPS_N.level, blend=4)
SWITCHBACK = Path([(-112, -150, N_Y), (-132, -150, 17.0), (-150, -150, 20.0), (-152, -158, 21.5),
                   (-150, -166, 23.0), (-128, -166, 26.5), (-120, -174, 28.0), (-128, -182, 29.5),
                   (-150, -184, 33.0), (-162, -190, 37.0), (-168, -195, PEAK_Y)], 6.0)
G.pad(SWITCHBACK, SWITCHBACK.level, blend=6)
MOUNTAIN_ROAD = Path([(-40, 312, -36.0), (-8, 300, -33.0), (22, 284, -29.5), (18, 266, -26.5), (-24, 256, -22.0),
                      (-52, 244, -18.0), (-60, 226, S_Y - 0.2), (-60, 214, S_Y)], 7.0, samples=4)
G.pad(MOUNTAIN_ROAD, MOUNTAIN_ROAD.level, blend=8)
VALLEY_RAMP = Path([(196, 44, 0.0), (214, 56, -4.0), (220, 76, -12.0), (214, 98, V_Y)], 7.0, samples=4)
G.pad(VALLEY_RAMP, VALLEY_RAMP.level, blend=6)
TEA_ROAD = Path([(70, 150, S_Y), (84, 168, S_Y - 1.0), (96, 186, S_Y - 2.0), (100, 230, -26.0), (104, 262, -36.0)],
                5.0, samples=3)
G.pad(TEA_ROAD, TEA_ROAD.level, blend=5)
VALLEY_LINK = Path([(84, 116, S_Y), (100, 116, -18.0), (116, 116, V_Y)], 6.0)
G.pad(VALLEY_LINK, VALLEY_LINK.level, blend=6)

# ---- hollows: the lotus pond of the first map, the plunge pool, the sword pool, the laundry stream ------
G.pad(Disc(POND[0], POND[1], POND[2] * 1.25, POND[3] / POND[2]), _pond_level, blend=0.1)
PLUNGE = Disc(150, 74, 8.0)
G.pad(PLUNGE, V_Y - 1.6, blend=4, op="min")
SWORD_POOL = Disc(-236, -199, 5.0)
G.pad(SWORD_POOL, PEAK_Y - 1.2, blend=2.5, op="min")
LAUNDRY = Path([(-58, 215), (-100, 216), (-150, 214), (-200, 216)], 4.0, samples=3)
G.pad(LAUNDRY, S_Y - 1.6, blend=2.5, op="min")
BEAST_POND = Disc(214, 176, 6.0, sx=1.3)
G.pad(BEAST_POND, V_Y - 1.2, blend=3, op="min")

# ---- buildings (each levels its own pad) -----------------------------------------------------------
S = Sites(G)
# outer sect terrace
S.add("outer_sect_hall", -110, 118, 0, S_Y, name="OuterSectHallBuilding")
S.add("mission_hall", -40, 126, 0, S_Y, name="MissionHallBuilding")
S.add("contribution_pavilion", 34, 126, 0, S_Y, name="ContributionPavilionBuilding")
S.add("sect_refectory", -112, 168, 0, S_Y, name="RefectoryBuilding")
for i, x in enumerate((-176, -150, -114, -88)):
    S.add("dormitory_row", x, 199, 0, S_Y, name=f"OuterDormitory{i + 1}")
S.add("dormitory_row", -40, 172, 0, S_Y, name="OuterDormitory5")
# east terrace
S.add("martial_stage", 125, -5, 0, 0.0, name="MartialStageBuilding", solid=False)
S.add("arena_stands", 125, -23, 0, 0.0, name="StandsNorth")
S.add("arena_stands", 125, 13.5, 180, 0.0, name="StandsSouth")
S.add("arena_stands", 143.5, -5, -90, 0.0, name="StandsEast")
S.add("arena_stands", 106.5, -5, 90, 0.0, name="StandsWest")
S.add("bell_tower", 92, -46, 0, 3.0, name="BellTowerBuilding")
S.add("drum_tower", 92, 42, 180, 0.0, name="DrumTowerBuilding")
S.add("formation_hall", 162, -52, 0, 0.0, name="FormationHallBuilding")
S.add("treasure_tower", 170, 30, 0, 0.0, name="TreasureTowerBuilding")
S.add("pavilion", 205, -8, 90, 0.0, name="SunrisePavilion")
# north terrace
S.add("inner_sect_gate", 0, -72, 0, 0.0, name="InnerSectGateBuilding")
for i, (x, z, yaw) in enumerate(((-70, -140, 90), (-70, -160, 90), (-30, -140, -90), (-30, -160, -90), (-50, -178, 0))):
    S.add("sect_cottage", x, z, yaw, N_Y, name=f"CoreCottage{i + 1}")
for i, x in enumerate((58, 80, 102)):
    S.add("ancestral_tomb", x, -186, 0, N_Y, name=f"AncestorTomb{i + 1}")
# medicine valley
for i, (x, z, yaw) in enumerate(((118, 96, 0), (142, 96, 0), (130, 114, 180))):
    S.add("pill_kiln", x, z, yaw, V_Y, name=f"PillKiln{i + 1}")
for i, (x, z, yaw) in enumerate(((188, 160, 0), (200, 184, 90), (182, 186, 0))):
    S.add("beast_pen", x, z, yaw, V_Y, name=f"BeastPen{i + 1}")
S.add("mission_hall", 172, 104, 180, V_Y, name="MedicineHall", pad=2.0)

# ---- paving, roads and fields (first region containing a point wins) ---------------------------------
PAVE = "paving"
# the first map's plaza, processional way, hall forecourt and paths
for r in ((-3.5, 30, 3.5, 68), (-10, -12, 10, 30), (-12, -30, 12, -12), (-42, -9, -10, -3), (10, 10.5, 19.5, 13.5),
          (10, -9.5, 19.5, -6.5)):
    G.region(PAVE, box(*r))
G.region(PAVE, box(-5, 68, 5, 78))
G.region(PAVE, STEPS_S)
G.region(PAVE, STEPS_N)
G.region(PAVE, box(-6, -80, 6, -60))
# outer sect terrace: a flagstone court before the halls and walks between them
G.region(PAVE, box(-70, 108, 60, 148, r=4))
G.region(PAVE, box(-128, 136, -92, 148))
G.region(PAVE, box(-160, 148, -60, 158))
G.region(PAVE, box(-190, 184, -70, 190))
G.region("gravel", Path([(-60, 214), (-60, 190)], 5.0))
G.region("gravel", MOUNTAIN_ROAD)
# east terrace: the arena court and the plaza road between the towers
G.region(PAVE, Disc(125, -5, 30))
G.region(PAVE, Path([(8, 50), (40, 50), (70, 40), (92, 20), (92, -30), (104, -5)], 6.0))
G.region(PAVE, Disc(162, -52, 17))
G.region(PAVE, Disc(170, 30, 12))
G.region("gravel", Path([(104, -5), (150, -30), (162, -40)], 4.0))
G.region("gravel", Path([(150, 5), (170, 20)], 4.0))
G.region("gravel", Path([(140, -5), (196, -8)], 4.0))
G.region("gravel", VALLEY_RAMP)
# north terrace
G.region(PAVE, box(-8, -130, 8, -110))
G.region(PAVE, box(-62, -170, -38, -130))
G.region("gravel", Path([(0, -120), (-40, -150)], 4.0))
G.region("gravel", Path([(0, -120), (80, -150), (80, -170)], 4.0))
G.region("gravel", Path([(-40, -150), (-112, -150)], 4.0))
G.region("gravel", SWITCHBACK)
G.region(PAVE, Disc(-252, -195, 16))
# the medicine valley's herb terraces, the tea terraces, the orchard
G.region("dirt", Disc(130, 104, 16))
G.region("crops", box(150, 120, 200, 145))
G.region("crops", box(110, 140, 170, 170))
G.region("tea", box(62, 188, 172, 256, r=8))
G.region("gravel", TEA_ROAD)
G.region("gravel", VALLEY_LINK)
G.region("moss", Disc(214, 176, 10, sx=1.3))
G.region("pebbles", LAUNDRY)
G.region("pebbles", PLUNGE)
G.region("pebbles", SWORD_POOL)
G.region("pebbles", Disc(POND[0], POND[1], POND[2] * 1.1, POND[3] / POND[2]))
G.region("dirt", Disc(-40, 316, 18))

# water surfaces: (material key, shape, level)
G.water("pond", Disc(POND[0], POND[1], POND[2] * 1.2, POND[3] / POND[2]), -0.45)
G.water("stream", Path([(-58, 215), (-100, 216), (-150, 214), (-200, 216)], 5.0, samples=3), S_Y - 0.55)
G.water("stream", Disc(150, 74, 9.0), V_Y - 0.5)
G.water("pond", Disc(-236, -199, 5.8), PEAK_Y - 0.4)
G.water("pond", Disc(214, 176, 7.2, sx=1.3), V_Y - 0.45)


def height(x, z):
    return G.height(x, z)


# --------------------------------------------------------------------------
# the first map's walled sect (unchanged layout and seeds)
# --------------------------------------------------------------------------
def build_layout():
    rnd = random.Random(7)
    items = []  # (asset, node name, pos, yaw, scale)

    def add(asset, pos, yaw=0.0, scale=1.0, name=None):
        items.append((asset, name, pos, yaw, scale))

    add("terrain", (0, 0, 0), name="Terrain")
    add("cloud_sea", (0, -62, 0), name="CloudSea")
    add("main_hall", (0, 0, -38), name="MainHall")
    add("sect_gate", (0, 0, WALL_SOUTH), name="SectGate")
    add("pagoda", (20, 0, -38), name="Pagoda")
    add("pavilion", (-18, 0, -20), yaw=20, name="Pavilion")
    # side halls (reusing the main hall model at a smaller scale, as the town yamen does)
    add("main_hall", (-24, 0, -8), yaw=90, scale=0.4, name="AlchemyPavilion")
    add("main_hall", (-24, 0, 12), yaw=90, scale=0.4, name="WeaponsHall")
    add("main_hall", (24, 0, 20), yaw=180, scale=0.4, name="ElderQuarters")
    add("main_hall", (14, 0, 22), yaw=180, scale=0.45, name="DiscipleDormitory")
    add("formation_array", (0, 0.0, 8), name="FormationArray")
    add("incense_burner", (0, 0.0, -22), name="IncenseBurner")
    add("stone_bridge", (18, -0.15, 2), name="StoneBridge")
    add("lotus_cluster", (14.5, -0.44, -1.5))
    add("lotus_cluster", (21.5, -0.44, 5.5), yaw=70)

    # courtyard walls: the south side leaves room for the gate, the west side has a moon gate
    def run(x0, z0, x1, z1, gap=None, moon_at=None):
        length = math.hypot(x1 - x0, z1 - z0)
        n = max(1, math.ceil(length / SEGMENT))
        yaw = math.degrees(math.atan2(-(z1 - z0), x1 - x0))
        for k in range(n):
            t = (k + 0.5) / n
            x = x0 + (x1 - x0) * t
            z = z0 + (z1 - z0) * t
            if gap and gap[0] < x < gap[1]:
                continue
            asset = "moon_gate_wall" if moon_at is not None and k == moon_at else "courtyard_wall"
            add(asset, (x, 0, z), yaw=yaw)

    run(-WALL_HALF_X, WALL_NORTH, WALL_HALF_X, WALL_NORTH)
    run(-WALL_HALF_X, WALL_SOUTH, -5.0, WALL_SOUTH)
    run(5.0, WALL_SOUTH, WALL_HALF_X, WALL_SOUTH)
    run(-WALL_HALF_X, WALL_NORTH, -WALL_HALF_X, WALL_SOUTH, moon_at=5)
    run(WALL_HALF_X, WALL_NORTH, WALL_HALF_X, WALL_SOUTH)

    # lanterns along the processional way and the plaza
    for z in (38, 46, 54, 62):
        for x in (-5.5, 5.5):
            add("stone_lantern", (x, 0.0, z))
    for z in (-14, -2, 12, 24):
        for x in (-11.5, 11.5):
            add("stone_lantern", (x, 0.0, z))
    # red paper lanterns hanging under the hall eaves and the gate beams
    for x in (-3.6, -1.2, 1.2, 3.6):
        add("red_lantern", (x, 6.2, -31.9), yaw=rnd.uniform(0, 90))
    for x in (-2.9, 2.9):
        add("red_lantern", (x, 3.7, WALL_SOUTH + 0.05))
    # banners
    for x in (-8, 8):
        add("sect_banner", (x, 0.0, WALL_SOUTH - 4), yaw=180 if x > 0 else 0)
    for x in (-13, 13):
        add("sect_banner", (x, 0.0, -26), yaw=180 if x > 0 else 0)
    # training ground (west of the plaza)
    add("weapon_rack", (-22.5, 0, 17), yaw=90)
    for pos in ((-17, 0, 12), (-15, 0, 17), (-17.5, 0, 22)):
        add("training_dummy", pos, yaw=rnd.uniform(-30, 30) + 90)
    # garden: trees, rocks, bamboo
    for pos in ((-14, 0, -30), (14, 0, -30), (-23, 0, 5), (8.5, 0, 16), (25, 0, -20)):
        add("plum_blossom_tree", pos, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.15))
    inside_pines = ((-25, 0, -44), (26, 0, -47), (-25, 0, 27), (25, 0, 26), (-9, 0, -46))
    for pos in inside_pines:
        add("pine_tree", pos, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.1))
    outside_pines = ((-12, 0, 44), (12, 0, 50), (-14, 0, 60), (15, 0, 64), (-40, 0, 20), (40, 0, -8),
                     (-44, 0, -30), (42, 0, 38), (-38, 0, 52), (46, 0, -52), (-48, 0, -60), (0, 0, -60),
                     (36, 0, 60), (-52, 0, 10))
    for i, pos in enumerate(outside_pines):
        add("pine_tree_tall" if i % 2 else "pine_tree", pos, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.3))
    for pos in ((-35, 0, -2), (-37, 0, 9), (-33, 0, -12), (-26, 0, 26.5), (26, 0, -30)):
        add("bamboo_cluster", pos, yaw=rnd.uniform(0, 360))
    # scatter extra vegetation between the walls and the cliffs
    placed = 0
    while placed < 34:
        x, z = rnd.uniform(-50, 50), rnd.uniform(-66, 66)
        inside = abs(x) < 33 and -54 < z < 34
        on_way = abs(x) < 9 and z > 28
        if inside or on_way:
            continue
        kind = rnd.random()
        if kind < 0.55:
            add("pine_tree" if rnd.random() < 0.5 else "pine_tree_tall", (x, 0, z), yaw=rnd.uniform(0, 360),
                scale=rnd.uniform(0.8, 1.3))
        elif kind < 0.75:
            add("boulders", (x, 0, z), yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.6, 1.4))
        elif kind < 0.88:
            add("plum_blossom_tree", (x, 0, z), yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.2))
        else:
            add("bamboo_cluster", (x, 0, z), yaw=rnd.uniform(0, 360))
        placed += 1
    add("scholar_rock", (26, 0, 10), yaw=30)
    add("scholar_rock", (-12, 0, -14), yaw=200, scale=0.8)
    for pos in ((-45, 0, 40), (47, 0, 18), (30, 0, 56), (-30, 0, -58), (50, 0, -35), (-52, 0, -12)):
        add("boulders", pos, yaw=rnd.uniform(0, 360), scale=rnd.uniform(0.8, 1.6))
    # the sky: floating islets and distant karst pillars rising from the cloud sea
    for pos, sc, yaw in (((-120, 22, -90), 1.4, 10), ((150, 38, -60), 1.8, 80), ((-95, 48, 125), 1.1, 200),
                         ((110, 14, 120), 1.3, 140), ((20, 65, -170), 2.2, 300), ((-170, 30, 30), 1.0, 45)):
        add("floating_island", pos, yaw=yaw, scale=sc)
    for pos, sc in (((-230, -40, -160), 1.2), ((250, -60, -210), 1.5), ((-280, -50, 110), 1.3),
                    ((215, -40, 230), 1.1), ((0, -60, -330), 1.8), ((330, -50, 40), 1.4),
                    ((-160, -70, 290), 1.6), ((120, -55, -320), 1.2), ((-330, -40, -60), 1.1)):
        add("karst_peak", pos, yaw=rnd.uniform(0, 360), scale=sc)
    return items


# the first map's islets would now float inside the new terraces: they move out over the clouds
_ISLET_MOVES = {(-120, -90): (-150, -40), (150, -60): (260, -130), (-95, 125): (-250, 60), (110, 120): (270, 250),
                (20, -170): (40, -290), (-170, 30): (-290, -80)}
_KARST_MOVES = {(-230, -160): (-420, -260), (250, -210): (420, -300), (-280, 110): (-440, 180),
                (215, 230): (420, 360), (0, -330): (60, -470), (330, 40): (470, 60), (-160, 290): (-300, 440),
                (120, -320): (220, -480), (-330, -60): (-480, -60)}


# --------------------------------------------------------------------------
# the enlarged mountain
# --------------------------------------------------------------------------
def build_districts(add, rnd):
    """Place the new districts' buildings, props and vegetation. add(asset, x, z, yaw, scale, name, y)."""
    gy = G.height
    for asset, name, x, z, yaw, level, scale in S.items:
        add(asset, x, z, yaw, scale, name, level)

    # --- the long stairways and the inner gate's lanterns
    add("stone_stairs_14", 0, 108.0 - 0.0, 0, 1.0, "StoneStepsSouth", S_Y)
    add("stone_stairs_14", 0, -80.5, 0, 1.0, "StoneStepsNorth", 0.0)
    for x in (-5.5, 5.5):
        add("stone_lantern", x, 114, 0, 1.0, None, S_Y)
        add("stone_lantern", x, -64, 0, 1.0, None, 0.0)
    # --- outer sect terrace
    for x in (-66, -20, 20, 56):
        add("sect_banner", x, 146, 180, 1.0, None, S_Y)
    for (x, z) in ((-70, 112), (-10, 146), (10, 146), (58, 112)):
        add("stone_lantern", x, z, 0, 1.0, None, S_Y)
    add("incense_burner", 0, 128, 0, 0.9, "IncenseBurnerOuter", S_Y)
    add("weapon_rack", -150, 140, 90, 1.0, None, S_Y)
    for (x, z) in ((-156, 128), (-160, 136), (-154, 146)):
        add("training_dummy", x, z, rnd.uniform(60, 120), 1.0, None, S_Y)
    for (x, z) in ((-40, 158), (-80, 150), (-140, 175), (-175, 140), (60, 170), (40, 190), (-10, 200)):
        add("plum_blossom_tree", x, z, rnd.uniform(0, 360), rnd.uniform(0.9, 1.15), None, gy(x, z))
    # laundry stream: wash stones, drying lines (banners), a little footbridge
    for k in range(10):
        x = -65 - k * 13
        add("boulders", x, 214.5 + rnd.uniform(-1.8, 1.8), rnd.uniform(0, 360), 0.3, None, S_Y - 1.0)
    add("wooden_bridge", -60, 215, 90, 0.5, "LaundryBridge", S_Y)
    for x in (-98, -164):
        add("sect_banner", x, 209, 0, 0.8, None, S_Y)
    # the mountain road: lanterns and a gate at the landing
    add("sect_gate", -40, 305, 200, 0.8, "RoadGate", -36.0)
    for t in range(0, 110, 14):
        (x, z), (tx, tz) = MOUNTAIN_ROAD.at(t)
        for side in (-1, 1):
            px, pz = x - tz * side * 4.6, z + tx * side * 4.6
            if side > 0:
                add("stone_lantern", px, pz, 0, 0.8, None, gy(px, pz))
    # --- east terrace
    for k in range(8):
        a = 2 * math.pi * k / 8
        add("formation_pillar", 162 + math.cos(a) * 15.5, -52 + math.sin(a) * 15.5, math.degrees(a), 1.0, None, 0.0)
    for (x, z) in ((104, -18), (104, 8), (146, -18), (146, 8)):
        add("sect_banner", x, z, 0 if x < 125 else 180, 1.1, None, 0.0)
    for (x, z) in ((80, 30), (80, -30), (100, 30), (100, -34)):
        add("stone_lantern", x, z, 0, 1.0, None, gy(x, z))
    add("weapon_rack", 138, -40, 0, 1.0, None, 0.0)
    add("scholar_rock", 190, -30, 60, 1.1, None, 0.0)
    for (x, z) in ((186, 20), (186, 40), (150, 45), (70, -60), (190, -60), (110, -65)):
        add("pine_tree_tall", x, z, rnd.uniform(0, 360), rnd.uniform(1.0, 1.3), None, gy(x, z) - 0.2)
    # --- north terrace
    for (x, z) in ((-8, -114), (8, -114)):
        add("stone_lantern", x, z, 0, 1.0, None, N_Y)
    for i, x in enumerate((58, 80, 102)):
        add("stone_stele", x, -176.5, 0, 1.2, f"AncestorStele{i + 1}", N_Y)
    for k in range(10):
        x = 46 + k * 7
        for z in (-200, -160):
            add("cypress_tree", x, z, rnd.uniform(0, 360), rnd.uniform(0.9, 1.2), None, N_Y - 0.1)
    add("incense_burner", 80, -168, 0, 0.8, "IncenseBurnerTombs", N_Y)
    for (x, z) in ((-50, -150),):
        add("village_well", x - 6, z + 4, 0, 0.8, None, N_Y)
    for (x, z) in ((-86, -130), (-86, -175), (-14, -176), (-16, -128)):
        add("plum_blossom_tree", x, z, rnd.uniform(0, 360), 1.0, None, N_Y)
    # the Cliff of Reflection: a bare ledge, a meditation rock
    add("scholar_rock", -110, -207, 140, 1.2, "ReflectionRock", N_Y)
    add("pine_tree", -98, -210, 40, 1.2, None, N_Y - 0.2)
    # switchback and bridge to Sword Peak
    for t in range(4, 190, 22):
        (x, z), (tx, tz) = SWITCHBACK.at(t)
        px, pz = x - tz * 3.8, z + tx * 3.8
        add("stone_lantern", px, pz, 0, 0.8, None, gy(px, pz))
    add("chain_bridge", -201, -195, 90, 1.0, "CableBridgeSpan", PEAK_Y)
    add("sword_tomb", -264, -206, 0, 1.0, "SwordTombField", gy(-264, -206))
    for k in range(6):
        a = 2 * math.pi * k / 6
        add("boulders", -236 + math.cos(a) * 6.2, -199 + math.sin(a) * 6.2, k * 60, 0.45, None, PEAK_Y - 0.3)
    for (x, z) in ((-270, -180), (-240, -216), (-266, -190)):
        add("pine_tree", x, z, rnd.uniform(0, 360), 1.2, None, gy(x, z) - 0.2)
    add("sect_banner", -236, -198, 90, 1.2, None, PEAK_Y)
    # --- medicine valley: herbs, the waterfall and its cave, the beast garden, the crane roost
    add("waterfall", 150, 62.5, 0, 1.0, "HundredChiFall", V_Y - 0.6)
    add("cave_mouth", 136, 64, 20, 0.8, "WaterfallCaveMouth", V_Y)
    for k in range(18):
        x, z = rnd.uniform(152, 198), rnd.uniform(122, 143)
        add("spirit_herb", x, z, rnd.uniform(0, 360), 1.1, None, gy(x, z))
    for k in range(10):
        x, z = rnd.uniform(112, 168), rnd.uniform(142, 168)
        add("spirit_herb", x, z, rnd.uniform(0, 360), 1.0, None, gy(x, z))
    for (x, z) in ((220, 132), (226, 140), (216, 142), (228, 131)):
        add("pine_tree_tall", x, z, rnd.uniform(0, 360), 1.2, None, gy(x, z) - 0.2)
    for (x, z, yaw) in ((219, 137, 30), (224, 136, 200), (206, 170, 80), (212, 182, 250), (196, 172, 120)):
        add("crane_figure", x, z, yaw, 1.0, None, gy(x, z))
    for (x, z) in ((108, 80), (230, 100), (230, 190), (110, 185)):
        add("bamboo_cluster", x, z, rnd.uniform(0, 360), 1.1, None, gy(x, z))
    # --- tea terraces and the peach orchard
    for k in range(9):
        x, z = 60 + k * 14, 265 + (k % 2) * 6
        add("stone_lantern", x, z, 0, 0.7, None, gy(x, z)) if k % 4 == 0 else None
    for k in range(16):
        x, z = 55 + (k % 8) * 15 + rnd.uniform(-2, 2), 270 + (k // 8) * 14 + rnd.uniform(-2, 2)
        add("peach_tree", x, z, rnd.uniform(0, 360), rnd.uniform(0.9, 1.1), None, gy(x, z))
    add("pavilion", 150, 198, 0, 0.9, "TeaPavilion", gy(150, 198))
    # --- vegetation scatter on the new terraces (away from buildings, roads and markers)
    clear = [(r.cx, r.cz, max(r.hw, r.hd) + 3) for _, _, r in S.solids]
    placed = []
    tries = 0
    while len(placed) < 260 and tries < 30000:
        tries += 1
        x, z = rnd.uniform(-280, 280), rnd.uniform(-280, 310)
        if abs(x) < 64 and abs(z) < 80:
            continue
        h = gy(x, z)
        if h < -45 or G.slope_nz(x, z) < 0.85 or G.surface(x, z) is not None:
            continue
        if any(math.hypot(x - a, z - b) < r for (a, b, r) in clear) or any(math.hypot(x - a, z - b) < 6 for a, b in placed):
            continue
        if any(math.hypot(x - mx, z - mz) < 7 for (mx, _, mz) in MARKERS.values()):
            continue
        k = rnd.random()
        yaw = rnd.uniform(0, 360)
        if k < 0.45:
            add("pine_tree_tall" if rnd.random() < 0.5 else "pine_tree", x, z, yaw, rnd.uniform(0.9, 1.3), None, h - 0.25)
        elif k < 0.62:
            add("plum_blossom_tree", x, z, yaw, rnd.uniform(0.85, 1.15), None, h - 0.1)
        elif k < 0.78:
            add("bamboo_cluster", x, z, yaw, rnd.uniform(0.9, 1.2), None, h - 0.1)
        else:
            add("boulders", x, z, yaw, rnd.uniform(0.6, 1.4), None, h - 0.3)
        placed.append((x, z))


def _m(x, z, lift=1.0):
    return (x, round(G.height(x, z) + lift, 3), z)


MARKERS = {
    # the first map's markers (unchanged)
    "PlayerSpawn": (3.0, 1.0, 43.0),
    "TeleportArray": (TELEPORT[0], 0.9, TELEPORT[2]),
    "SectGate": (0.0, 1.0, 26.0),
    "GateGuardPost": (-8.0, 1.0, 35.0),
    "FormationArray": (0.0, 1.2, 8.0),
    "IncenseBurner": (0.0, 1.0, -18.5),
    "HallSteps": (0.0, 1.0, -27.5),
    "MainHall": (0.0, 2.0, -33.5),
    "TrainingGround": (-14.5, 1.0, 14.5),
    "WeaponRack": (-20.5, 1.0, 20.5),
    "Pavilion": (-16.3, 1.0, -15.3),
    "Pagoda": (20.0, 1.0, -31.0),
    "LotusPond": (8.0, 1.0, 4.0),
    "StoneBridge": (18.0, 2.0, 2.0),
    "PlumGarden": (21.0, 1.0, -20.5),
    "HerbGarden": (-39.0, 1.0, -6.0),
    "MoonGate": (-26.0, 1.0, -6.0),
    "CliffEdge": (-55.0, 1.2, 4.0),
    "ScholarRock": (23.0, 1.0, 11.5),
    "OuterPines": (34.0, 1.0, 46.0),
    "AlchemyPavilion": (-20.5, 1.0, -8.0),
    "WeaponsHall": (-20.5, 1.0, 12.0),
    "ElderQuarters": (24.0, 1.0, 16.5),
    "DiscipleDormitory": (14.0, 1.0, 18.0),
    # the enlarged mountain
    "InnerSectGate": _m(0, -65),
    "OuterSectHall": _m(-110, 136),
    "MissionHall": _m(-40, 142),
    "ContributionPavilion": _m(34, 140),
    "Refectory": _m(-112, 182),
    "OuterDormitories": _m(-132.5, 204),
    "LaundryStream": _m(-100, 211),
    "MartialStage": (125.0, 2.2, -5.0),
    "ArenaStands": _m(143, -24),
    "BellTower": _m(92, -32),
    "DrumTower": _m(92, 30),
    "FormationHall": _m(162, -34),
    "TreasureTower": _m(170, 45),
    "SwordPeakPath": _m(-150, -160),
    "CableBridge": _m(-172, -197),
    "SwordPeak": _m(-252, -186),
    "SwordTomb": _m(-252, -213),
    "SwordWashPool": _m(-236, -207),
    "MedicineValley": _m(165, 130),
    "PillKilnYard": _m(130, 104),
    "SpiritBeastGarden": _m(196, 171),
    "CraneRoost": _m(222, 136),
    "Waterfall": _m(150, 88),
    "WaterfallCave": _m(128, 70),
    "AncestorTombs": _m(80, -168),
    "ReflectionCliff": _m(-104, -200),
    "TeaTerraces": _m(110, 214),
    "SpiritOrchard": _m(110, 283),
    "SunriseTerrace": _m(196, -8),
    "CoreDisciplesCourt": _m(-50, -150),
    "MountainRoad": _m(-40, 312),
    "StoneSteps": _m(0, 116),
}


def build() -> common.MapDef:
    items = build_layout()
    # keep the arrival platform clear of the scattered vegetation
    tx, _, tz = TELEPORT
    items = [it for it in items if it[0] in ("terrain", "cloud_sea") or math.hypot(it[2][0] - tx, it[2][2] - tz) > 5.0]
    items.append(("teleport_array", "TeleportArray", TELEPORT, 0.0, 1.0))
    # a denser plum grove by the pagoda and spirit herbs on the terraces outside the moon gate
    for (x, z, yaw, s) in ((26.0, -25.5, 40, 1.0), (15.5, -24.5, 160, 0.9), (25.0, -13.5, 280, 0.95)):
        items.append(("plum_blossom_tree", None, (x, 0, z), yaw, s))
    for (x, z) in ((-36.5, -9.5), (-41.5, -8.5), (-43.0, -3.5), (-38.0, -1.0), (-44.5, -11.0), (-40.0, -12.5)):
        items.append(("spirit_herb", None, (x, 0, z), (x * 37) % 360, 1.1))
    # move the islets and karst pillars of the first map out beyond the new terraces
    moved = []
    for asset, name, pos, yaw, scale in items:
        key = (round(pos[0]), round(pos[2]))
        if asset == "floating_island" and key in _ISLET_MOVES:
            nx, nz = _ISLET_MOVES[key]
            pos = (nx, pos[1], nz)
        elif asset == "karst_peak" and key in _KARST_MOVES:
            nx, nz = _KARST_MOVES[key]
            pos = (nx, pos[1] - 20, nz)
        moved.append((asset, name, pos, yaw, scale))
    items = moved

    rnd = random.Random(77)

    def add(asset, x, z, yaw=0.0, scale=1.0, name=None, y=None):
        yy = G.height(x, z) if y is None else y
        items.append((asset, name, (round(x, 3), round(yy, 3), round(z, 3)), round(yaw, 2), scale))

    build_districts(add, rnd)
    markers = dict(MARKERS)
    problems = check_markers("sect", {k: v for k, v in markers.items() if k in NEW_MARKERS}, G.height, S.solids,
                             exempt=("CableBridge",))
    if problems:
        raise SystemExit("sect marker problems:\n  " + "\n  ".join(problems))
    env = common.Env(shadow_distance=160.0)
    return common.MapDef("sect", "Azure Cloud Sect", "sect", items, markers, env=env, ambient="motes", kill_y=KILL_Y)


NEW_MARKERS = [k for k in MARKERS if k not in (
    "PlayerSpawn", "TeleportArray", "SectGate", "GateGuardPost", "FormationArray", "IncenseBurner", "HallSteps",
    "MainHall", "TrainingGround", "WeaponRack", "Pavilion", "Pagoda", "LotusPond", "StoneBridge", "PlumGarden",
    "HerbGarden", "MoonGate", "CliffEdge", "ScholarRock", "OuterPines", "AlchemyPavilion", "WeaponsHall",
    "ElderQuarters", "DiscipleDormitory")]

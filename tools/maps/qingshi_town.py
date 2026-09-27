"""Qingshi Town: a walled county town on a river, now a whole river valley (about ten times the old area).

The walled old town of the first map (streets, houses, yamen, market, temple, well, docks, graveyard,
farms) is unchanged in the middle. Around it a new outer wall encloses the grown county town:

* north, through a lane cut in the old north wall: the drum-and-bell pavilion over the crossroads, the
  City God temple with its incense court and the temple orphanage, the temple-fair square with its opera
  stage, the county academy and its examination cells, the merchant guild master's manor and garden,
  the Wang family pharmacy, the pawnshop, the bathhouse, the granary on its plinth, the militia barracks
  and the North Gate
* south of the old walls: the willow-lined canal and its humpbacked stone bridge, the lantern-hung night
  market street, the silk workshop and dye yard, the brewery, the South Gate
* on the river: the riverside tavern, the execution ground, the lower docks, the boat yard, the watermill
  at the river bend, and outside the walls downstream the pottery kilns on the clay bank and the tannery
* east: the East Gate toward new farmland, and the post station with its stables

Coordinates are Godot's (x east, z south). The ground is a ``terrain.Ground`` built into the
town_terrain GLB (blender/xianxia/lands.py); streets, squares, fields and the river bed are regions of
that one mesh.
"""
import math
import random

from . import common
from .layout import Sites, check_markers
from .terrain import Disc, Ground, Path, Polyline, Rect, box, fbm2, lerp, smoothstep

WALL_W, WALL_E, WALL_N, WALL_S = -48.0, 48.0, -48.0, 40.0
WALL_T = 1.8                         # town_wall thickness
GATE_W = 11.0                        # town_gate footprint along the wall
CROSS_Z = -4.0                       # the east-west cross street
PLAY = 282.0                         # valley walls rise beyond this
SPAN = 320.0

# the new outer wall
OUT_W, OUT_E, OUT_N, OUT_S = -66.0, 150.0, -212.0, 150.0
NORTH_X = 28.0                       # the north street, through a lane in the old north wall

RIVER = Polyline([(-96, -330), (-92, -280), (-86, -225), (-72, -180), (-80, -140), (-79, -95), (-82, -45), (-80, 0),
                  (-78, 45), (-81, 95), (-80, 140), (-84, 190), (-92, 240), (-98, 290), (-104, 340)], 18.0, 8)
BANK = 8.3                           # embankment distance from the river centre line
WATER_Y = -1.4
DOCK_Z = -4.0

STREETS = {  # paved: (points, width) -- the old town
    "main": ([(0, 45), (0, 20), (0, -23)], 7.0),
    "cross": ([(-53, CROSS_Z), (0, CROSS_Z), (53, CROSS_Z)], 6.0),
    "riverside": ([(-53, CROSS_Z), (-71.5, CROSS_Z)], 6.0),
    "alley": ([(-17, -1), (-17, 38.5)], 4.0),
    "lane": ([(-29, -1), (-29, 38.5)], 4.0),
    "well": ([(-21, -7), (-21, -14)], 4.0),
}
ROADS = {  # dirt
    "south": Polyline([(0, 44), (1, 62), (-2, 80), (1, 96), (0, 120)], 5.0),
    "east": Polyline([(52, CROSS_Z), (62, -4), (68, -14), (69, -30), (67, -46), (68, -56)], 4.0),
    "fields": Polyline([(62, -3), (66, 8), (72, 12), (86, 13)], 3.0),
    "bank": Polyline([(-60, -40), (-62, -20), (-62, 10), (-60, 36)], 3.0),
}
SQUARES = {  # paved rectangles: (x0, z0, x1, z1)
    "market": (6, -21, 30, -8),
    "yamen": (-12, -36, 12, -22),
    "well": (-29, -24, -14, -9),
    "temple": (24, -46, 44, -30),
}
GRAVE_HILL = (80, -74, 9.0, 32.0)    # x, z, height, radius
GRAVEYARD = (68, -58, 11.0)           # flattened terrace on the hill
FARM = (56, 0, 90, 40)               # terraced fields x0, z0, x1, z1
FARM_STEP = (7.0, 0.55)              # terrace width, riser height
TELEPORT = (10.0, 61.0)
SPAWN = (2.0, 57.0)
CANAL_Z = 86.0
MILL = (-58.0, -164.0)


def boundary(x, z):
    e = 8.0 * fbm2(x * 0.02, z * 0.02, 2, 61)
    ox = max(x - PLAY + e, -x - PLAY - 2 + e, 0.0)
    oz = max(abs(z) - PLAY + e, 0.0)
    return math.hypot(ox, oz)


def _in_rect(x, z, r, pad):
    x0, z0, x1, z1 = r
    dx = max(x0 - x, 0.0, x - x1)
    dz = max(z0 - z, 0.0, z - z1)
    return smoothstep(pad, 0.0, math.hypot(dx, dz))


def _hill(x, z):
    hx, hz, hh, hr = GRAVE_HILL
    return hh * smoothstep(hr, 6.0, math.hypot(x - hx, z - hz))


def _terrace(x):
    w, rise = FARM_STEP
    t = max(0.0, (x - FARM[0]) / w)
    k = math.floor(t)
    return rise * (k + smoothstep(0.78, 1.0, t - k))


def _terrace_far(z):
    """New terraced fields east of the East Gate climb gently northward in 0.6 m steps."""
    t = max(0.0, (40.0 - z) / 12.0)
    k = math.floor(t)
    return 0.6 * (k + smoothstep(0.8, 1.0, t - k))


def river_distance(x, z):
    return RIVER.distance(x, z, 30.0)[0]


def _base(x, z):
    h = 0.7 * fbm2(x * 0.02, z * 0.02, 3, 51) + 0.2 * fbm2(x * 0.08, z * 0.08, 2, 52)
    far = math.hypot(x - 40, z)
    h += 7.0 * (0.5 + 0.5 * fbm2(x * 0.007, z * 0.007, 3, 57)) * smoothstep(170, 260, far)
    return h


def _after(x, z, h):
    out = boundary(x, z)
    if out > 0:
        crag = abs(fbm2(x * 0.045, z * 0.045, 4, 62)) * 9.0 + 2.5 * fbm2(x * 0.12, z * 0.12, 2, 63)
        h += 30.0 * (1 - math.exp(-out / 8.0)) + out * 0.55 + crag * min(1.0, out / 6)
    # the river channel, walled on the town side
    dr, t = RIVER.distance(x, z, 30.0)
    if dr < 12:
        east = x > RIVER.point(t)[0]
        if east:
            h = lerp(h, -3.2, smoothstep(BANK - 0.3, BANK - 1.5, dr))
        else:
            h = lerp(h, -3.2, smoothstep(11.5, 7.5, dr))
    return h


def _classify(x, z, h, nz):
    if nz < 0.74:
        return "cliff"
    if h < -1.0:
        return "pebbles"
    return "grass"


G = Ground((-SPAN, -SPAN, SPAN, SPAN), 2.5, _base, _classify, after=_after, chunk=40)
G.floor = None

# ---- level ground: the old town, the new walled districts, the riverside --------------------------------
G.pad(box(WALL_W - 5, WALL_N - 5, WALL_E + 5, WALL_S + 6), 0.0, blend=8)
G.pad(box(OUT_W - 4, OUT_N - 6, OUT_E + 6, WALL_N - 5), 0.0, blend=10)             # north district
G.pad(box(OUT_W - 4, WALL_S + 6, OUT_E + 6, OUT_S + 6), 0.0, blend=10)             # south district
G.pad(box(WALL_E + 5, WALL_N - 5, OUT_E + 6, WALL_S + 6), 0.0, blend=10)           # east of the old walls
G.pad(box(-74, -200, -48, 190), 0.0, blend=6)                                      # the east river bank
G.pad(box(-74, 156, -10, 250, r=8), 0.0, blend=10)                                # the clay bank downstream
G.pad(box(TELEPORT[0] - 7, TELEPORT[1] - 7, TELEPORT[0] + 7, TELEPORT[1] + 7), 0.0, blend=6)
# terraced fields, the graveyard hill and its terrace (as the first map)
G.pad(box(*FARM), lambda x, z: _terrace(x), blend=5)
G.pad(Disc(GRAVE_HILL[0], GRAVE_HILL[1], 6.0), lambda x, z: _hill(x, z), blend=26, op="max")
G.pad(Disc(GRAVEYARD[0], GRAVEYARD[1], GRAVEYARD[2]), _hill(GRAVEYARD[0], GRAVEYARD[1]), blend=7)
G.pad(box(162, -150, 262, 60, r=10), lambda x, z: _terrace_far(z), blend=12)       # new fields east
G.pad(box(-270, -150, -110, 180, r=20), lambda x, z: 0.8 * fbm2(x * 0.03, z * 0.03, 2, 58), blend=20)  # west bank
# the canal from the river east along the south district, the manor's pond, the mill race
CANAL = Path([(-78, CANAL_Z), (-40, CANAL_Z), (60, CANAL_Z), (122, CANAL_Z)], 9.0, flat_ends=True)
G.pad(CANAL, -2.6, blend=1.2, op="min")
MANOR_POND = Disc(136, -182, 8.0, sx=1.4, wobble=0.1, seed=4)
G.pad(MANOR_POND, -1.4, blend=2.5, op="min")
MILL_RACE = Path([(-76, -184), (-61, -176), (-61, -152), (-76, -144)], 3.4, samples=3)
G.pad(MILL_RACE, -2.2, blend=1.2, op="min")
# roads out of the valley
SOUTH_ROAD = Path([(0, 150), (4, 190), (-6, 230), (2, 290)], 6.0, samples=3)
NORTH_ROAD = Path([(NORTH_X, -212), (32, -250), (20, -300)], 6.0, samples=3)
EAST_ROAD = Path([(150, -4), (200, -6), (260, 4), (300, 10)], 6.0, samples=3)
for p in (SOUTH_ROAD, NORTH_ROAD, EAST_ROAD):
    G.pad(p, lambda x, z, p=p: _base(x, z) * 0.3, blend=6)

# ---- buildings --------------------------------------------------------------------------------------
S = Sites(G)
# north district
S.add("bell_pavilion", NORTH_X, -110, 0, 0.0, name="BellPavilionTower")
S.add("city_god_temple", 0, -156, 0, 0.0, name="CityGodTempleHall")
S.add("town_hall_small", -40, -128, 0, 0.0, name="OrphanageHall")
S.add("opera_stage", 60, -162, 0, 0.0, name="OperaStageBuilding")
S.add("academy_hall", 100, -150, 0, 0.0, name="AcademyHall")
S.add("exam_cells", 100, -176, 0, 0.0, name="ExamCellsA")
S.add("exam_cells", 100, -190, 0, 0.0, name="ExamCellsB")
S.add("manor_gate", 136, -126, 0, 0.0, name="ManorGateHouse")
S.add("manor_hall", 136, -150, 0, 0.0, name="ManorHall")
S.add("pharmacy", 46, -76, -90, 0.0, name="PharmacyHall")
S.add("pawnshop", 6, -62, 90, 0.0, name="PawnshopHall")
S.add("bathhouse", 0, -86, 90, 0.0, name="BathhouseHall")
S.add("granary", -40, -92, 0, 0.0, name="GranaryHall")
S.add("barracks", -20, -198, 0, 0.0, name="BarracksHall")
# south of the old town
S.add("tavern", -60, 55, 0, 0.0, name="TavernHall")
S.add("silk_workshop", 50, 112, 0, 0.0, name="SilkWorkshopShed")
S.add("dye_racks", 92, 108, 0, 0.0, name="DyeRacks", flatten=False)
S.add("dye_vats", 92, 122, 0, 0.0, name="DyeVats", flatten=False)
S.add("tavern", -28, 118, 90, 0.0, name="BreweryHall")
S.add("shophouse_c", -30, 58, 0, 0.0, name="ShopSouth1")
S.add("shophouse_a", 34, 58, 0, 0.0, name="ShopSouth2")
S.add("shophouse_b", -18, 136, 0, 0.0, name="NightShop1")
S.add("shophouse_a", 22, 136, 0, 0.0, name="NightShop2")
# the river
S.add("execution_platform", -60, -40, 90, 0.0, name="ExecutionPlatform")
S.add("boat_on_stocks", -60, 132, 0, 0.0, name="BoatOnStocks")
S.add("watermill", -54, -164, 180, 0.0, name="WatermillHouse", flatten=False)
S.add("pottery_kiln", -40, 200, 0, 0.0, name="PotteryKiln")
S.add("tannery_racks", -52, 236, 0, 0.0, name="TanneryRacks")
# east
S.add("post_station", 128, 22, 180, 0.0, name="PostStationStables")
S.add("city_gate", NORTH_X, OUT_N, 0, 0.0, name="NorthGateHouse")
S.add("city_gate", OUT_E, -4, 90, 0.0, name="EastGateHouse")
S.add("city_gate", 0, OUT_S, 0, 0.0, name="SouthGateHouse")

# ---- regions --------------------------------------------------------------------------------------------
for name, (pts, w) in STREETS.items():
    G.region("street", Path(pts, w, flat_ends=name not in ("main", "cross")))
for name, r in SQUARES.items():
    G.region("street", box(*r))
G.region("street", Path([(NORTH_X, -40), (NORTH_X, -212)], 7.0, flat_ends=True))
G.region("street", Path([(-60, -110), (145, -110)], 6.0, flat_ends=True))
G.region("street", box(-12, -142, 12, -124))                       # the City God temple's incense court
G.region("street", box(34, -154, 86, -124))                        # the temple fair square
G.region("street", Path([(0, 44), (0, 150)], 7.0, flat_ends=True))  # the night market street
G.region("street", Path([(-60, 70), (122, 70)], 4.0, flat_ends=True))
G.region("street", Path([(-66, 100), (122, 100)], 4.0, flat_ends=True))
G.region("street", Path([(53, CROSS_Z), (OUT_E, CROSS_Z)], 6.0, flat_ends=True))
G.region("street", box(-72, -10, -52, 2))                            # the docks' quay
G.region("earth", box(-70, -52, -50, -28))                           # the execution ground
G.region("earth", Disc(-60, 132, 14))                                # the boat yard
G.region("earth", Disc(-42, 205, 16))                                # the clay bank
G.region("earth", Disc(-52, 236, 10))
G.region("earth", box(112, 8, 146, 36))                              # the post station's yard
G.region("earth", box(80, 102, 106, 130))                            # the dye yard
G.region("earth", box(-34, -212, -6, -186))                          # the barracks' drill yard
G.region("paving", Disc(136, -176, 18))                              # the manor garden walks
G.region("pebbles", CANAL)
G.region("pebbles", MANOR_POND)
G.region("pebbles", MILL_RACE)
for p in ROADS.values():
    G.region("road", Path(p.pts, p.width, wobble=0.15, seed=3))
for p in (SOUTH_ROAD, NORTH_ROAD, EAST_ROAD):
    G.region("road", Path(p.pts, p.hw * 2, wobble=0.15, seed=4))
G.region("road", Path([(-60, -40), (-62, -120), (-60, -164)], 3.0, wobble=0.15, seed=5))
G.region("road", Path([(-60, 40), (-62, 132), (-50, 236)], 3.0, wobble=0.15, seed=6))
G.region("crops", box(FARM[0] + 1, FARM[1] + 1, FARM[2] - 1, FARM[3] - 1))
for k in range(4):
    G.region("crops", box(166, -146 + k * 50, 258, -146 + k * 50 + 42))
for k in range(3):
    G.region("crops", box(-250, -120 + k * 90, -130, -120 + k * 90 + 70))

G.water("river", Path(RIVER.pts, 20.0), WATER_Y)
G.water("stream", Path([(-80, CANAL_Z), (122, CANAL_Z)], 10.0), -1.7)
G.water("pond", Disc(136, -182, 9.5, sx=1.4), -0.7)
G.water("stream", Path(MILL_RACE.pts, 5.0), -1.5)


def height(x, z):
    return G.height(x, z)


def wall_run(add, x0, z0, x1, z1, gaps=(), asset="town_wall"):
    """Town wall segments from (x0, z0) to (x1, z1), leaving gaps (centre, half width)."""
    length = math.hypot(x1 - x0, z1 - z0)
    ux, uz = (x1 - x0) / length, (z1 - z0) / length
    yaw = math.degrees(math.atan2(-uz, ux))
    cuts = [(0.0, length)]
    for (c, hw) in gaps:
        new = []
        for (a, b) in cuts:
            if c - hw > a:
                new.append((a, min(b, c - hw)))
            if c + hw < b:
                new.append((max(a, c + hw), b))
        cuts = new
    for (a, b) in cuts:
        n = max(1, math.ceil((b - a) / 8.0 - 0.15))
        seg = (b - a) / n
        for k in range(n):
            t = a + seg * (k + 0.5)
            add(asset, x0 + ux * t, z0 + uz * t, yaw, (seg / 8.0, 1.0, 1.0))


def build() -> common.MapDef:
    rnd = random.Random(31)
    items = []

    def add(asset, x, z, yaw=0.0, scale=1.0, name=None, dy=0.0, y=None):
        yy = height(x, z) + dy if y is None else y
        items.append((asset, name, (round(x, 3), round(yy, 3), round(z, 3)), round(yaw, 2), scale))

    add("town_terrain", 0, 0, name="Terrain", y=0.0)

    # --- walls, gates and the watchtower ---------------------------------------------------
    h = WALL_T / 2
    wall_run(add, WALL_W - h, WALL_S, WALL_E + h, WALL_S, gaps=[(WALL_E + h, GATE_W / 2)])
    # the old north wall now has a lane cut through it toward the new north district
    wall_run(add, WALL_W - h, WALL_N, WALL_E + h, WALL_N, gaps=[(NORTH_X - (WALL_W - h), 5.0)])
    wall_run(add, WALL_W, WALL_N + h, WALL_W, WALL_S - h, gaps=[(CROSS_Z - WALL_N - h, GATE_W / 2)])
    wall_run(add, WALL_E, WALL_N + h, WALL_E, WALL_S - h, gaps=[(CROSS_Z - WALL_N - h, GATE_W / 2)])
    add("town_gate", 0, WALL_S, 0, name="SouthGate")
    add("town_gate", WALL_W, CROSS_Z, -90, name="WestGate")
    add("town_gate", WALL_E, CROSS_Z, 90, name="EastGate")
    add("watchtower", 43.2, 35.2, 0, name="Watchtower")
    add("watchtower", -43.2, -43.2, 180, name="WatchtowerNW")

    # --- the main street -----------------------------------------------------------------------
    west, east = -9.25, 9.25
    for z in (33.0, 24.5, 3.0):
        add("town_house", west, z, 90)
    add("town_house_large", -10.0, 13.0, 90, name="DrunkenCraneInn")
    for z in (33.0, 24.5):
        add("town_house", east, z, -90)
    add("town_house_large", 10.0, 13.0, -90, name="GeneralStore")
    add("town_house", east, 2.5, -90)
    add("town_house", west, -12.5, 90)
    # back-alley row (backs to the main street houses)
    for z in (33.0, 24.5, 13.0, 3.0):
        add("town_house", -23.25, z, -90)
    # warehouse yard (south-west)
    add("town_house_large", -39.5, 33.5, 0, name="GuildWarehouse")
    add("crates", -44.0, 22.0, 20)
    add("crates", -34.5, 25.5, -60, 0.9)
    add("crates", -44.5, 12.0, 95)
    add("cart", -35.5, 13.5, 35)
    add("market_stall", -45.0, 6.5, 90, 0.9)
    # well square (north-west)
    add("village_well", -21.5, -17.5, 20, name="TownWell")
    add("town_house", -22.0, -30.5, 0)
    add("town_house", -35.0, -16.0, 90)
    add("town_house", -36.0, -34.5, 45)
    add("plum_blossom_tree", -27.0, -12.0, 40, 0.8)
    # yamen: a scaled-down main hall in a walled courtyard, with the petition bell
    add("main_hall", 0, -41.0, 0, 0.6, name="Yamen")
    yard_walls = ((-13.0, -26.0, 90), (-13.0, -34.0, 90), (-13.0, -42.0, 90), (13.0, -26.0, 90),
                  (13.0, -34.0, 90), (13.0, -42.0, 90), (-8.5, -22.0, 0), (8.5, -22.0, 0))
    for (x, z, yaw) in yard_walls:
        add("courtyard_wall", x, z, yaw)
    add("bronze_bell", -7.0, -30.0, 90, name="PetitionBell")
    for x in (-4.5, 4.5):
        add("stone_lantern", x, -23.5, 0, 0.9)
        add("sect_banner", x * 1.5, -34.5, 0 if x < 0 else 180, 0.8)
    # market square
    for (x, z, yaw) in ((9.5, -18.5, 0), (15.5, -19.0, 0), (21.5, -18.5, 0), (27.0, -18.0, -20), (27.5, -11.0, -90),
                        (9.0, -10.0, 150), (14.5, -9.0, 180)):
        add("market_stall", x, z, yaw)
    add("cart", 22.0, -10.0, 200)
    add("crates", 29.0, -23.5, 10, 0.8)
    add("town_house", 38.5, -14.5, -90)
    # temple (north-east)
    add("pavilion", 34.0, -40.0, 0, name="TempleShrine")
    add("pagoda", 26.5, -42.5, 45, 0.42, name="TemplePagoda")
    add("incense_burner", 34.0, -34.0, 0, 0.7, name="IncenseBurnerTemple")
    for x in (29.5, 38.5):
        add("stone_lantern", x, -33.0, 0, 0.9)
    add("plum_blossom_tree", 41.5, -44.0, 70, 0.95)
    add("plum_blossom_tree", 43.0, -30.0, 200, 0.9)
    add("stone_stele", 42.0, -41.5, -35, 0.9, name="TempleStele")
    # south-east block and around the east gate
    add("town_house", 22.0, 8.0, 0, name="Blacksmith")
    add("town_house", 32.0, 8.0, 0, name="HerbShop")
    add("town_house", 22.0, 20.5, 180)
    add("town_house_large", 34.0, 21.0, 180, name="TeaHouse")
    add("plum_blossom_tree", 16.5, 33.0, 10, 0.85)
    add("village_well", 27.0, 30.5, 0, 0.9)
    # lanterns hung along the main street
    for z in (31.0, 21.0, 11.0, 1.0):
        for x in (-6.0, 6.0):
            add("red_lantern", x, z, rnd.uniform(0, 90), y=3.3)

    # --- outside: the south road, teleport array, river, farms, graveyard -------------------------
    tx, tz = TELEPORT
    ty = height(tx, tz)
    add("teleport_array", tx, tz, 0, name="TeleportArray", y=ty)
    for (x, z) in ((5.5, 54.0), (-4.5, 54.0)):
        add("stone_lantern", x, z, 0, 0.9)
    add("stone_stele", -6.5, 64.0, 60, 1.0, name="TownStele")
    bank_x = RIVER.point(RIVER.distance(-72, DOCK_Z)[1])[0] + BANK
    add("river_dock", bank_x, DOCK_Z, -90, name="Docks", y=0.0)
    add("crates", -66.0, -12.0, 30, 0.9)
    add("crates", -65.5, 5.0, -15)
    add("cart", -58.0, -14.0, 80)
    for z in (-34.0, -22.0, 16.0, 30.0):
        add("plum_blossom_tree", -66.5, z, rnd.uniform(0, 360), rnd.uniform(0.8, 1.0))
    # graveyard
    gx, gz, gr = GRAVEYARD
    for (dx, dz, yaw) in ((-5.0, -5.5, 190), (4.0, -6.5, 170), (6.5, 1.5, 250), (-6.5, 3.0, 120)):
        add("tombstones", gx + dx, gz + dz, yaw, dy=-0.05)
    add("pine_tree", gx - 9, gz - 9, 30, 1.1, dy=-0.2)
    add("pine_tree_tall", gx + 11, gz - 4, 200, 1.0, dy=-0.2)
    add("incense_burner", gx + 0.5, gz - 4.0, 0, 0.5, name="IncenseBurnerGrave")
    # farmland: fences, a scarecrow-less field hut and carts
    add("hermit_hut", 59.5, 34.0, -100, 0.85, name="FieldHut")
    add("cart", 72.5, 18.0, 60)

    build_districts(add, rnd)

    # distant karst pillars above the valley walls
    for k in range(13):
        a = math.radians(k * 360 / 13 + rnd.uniform(-10, 10))
        r = rnd.uniform(390, 460)
        add("karst_peak", math.cos(a) * r, math.sin(a) * r, rnd.uniform(0, 360), rnd.uniform(1.3, 1.9),
            y=rnd.uniform(-20, 0))
    scatter(add, rnd, items)

    def at(x, z, lift=1.0):
        return (x, round(height(x, z) + lift, 3), z)

    markers = {
        "PlayerSpawn": at(*SPAWN),
        "TeleportArray": (tx, round(ty + 0.9, 3), tz),
        "TownGate": at(0, 34.5),
        "MainStreet": at(1.5, 22.0),
        "MarketSquare": at(18.0, -14.0),
        "Inn": at(-2.0, 11.0),
        "Well": at(-18.5, -14.0),
        "MagistrateHall": at(0, -28.5),
        "Temple": at(34.0, -28.5),
        "Riverside": at(-63.0, 6.0),
        "BackAlley": at(-17.0, 20.0),
        "Warehouse": at(-39.5, 18.0),
        "Graveyard": at(gx, gz),
        "Farmland": at(72.0, 12.0),
        "WatchTower": at(37.5, 30.0),
        "TeaHouse": at(34.0, 13.5),
        "Blacksmith": at(22.0, 11.5),
        "HerbShop": at(32.0, 11.5),
    }
    markers.update({k: at(x, z) for k, (x, z) in NEW_MARKERS.items()})
    markers["StoneBridgeTown"] = (0.0, 4.2, CANAL_Z)       # the crown of the bridge
    problems = check_markers("qingshi_town", {k: markers[k] for k in NEW_MARKERS}, height, S.solids,
                             exempt=("StoneBridgeTown",))
    if problems:
        raise SystemExit("qingshi_town marker problems:\n  " + "\n  ".join(problems))
    env = common.Env(
        sky=common.Sky(top=(0.36, 0.5, 0.72), horizon=(0.98, 0.82, 0.62), ground_bottom=(0.5, 0.44, 0.38),
                       ground_horizon=(0.92, 0.78, 0.62), curve=0.14, sun_angle_max=22.0),
        ambient_energy=1.0, exposure=1.08, fog_color=(0.94, 0.82, 0.68), fog_density=0.0009,
        fog_height=-5.0, fog_height_density=0.02, fog_sun_scatter=0.45, fog_sky_affect=0.2,
        glow_intensity=0.6, saturation=1.1, contrast=1.06, sun_pitch=-33.0, sun_yaw=-55.0,
        sun_color=(1.0, 0.84, 0.66), sun_energy=1.9, shadow_distance=150.0,
    )
    return common.MapDef("qingshi_town", "Qingshi Town", "town", items, markers, env=env, ambient="petals")


NEW_MARKERS = {
    "NorthGate": (NORTH_X, -196.0),
    "EastGate": (136.0, -4.0),
    "SouthMarket": (0.0, 118.0),
    "Granary": (-40.0, -76.0),
    "SilkWorkshop": (50.0, 127.0),
    "DyeYard": (80.0, 116.0),
    "Pharmacy": (31.0, -76.0),
    "Academy": (100.0, -130.0),
    "ExamHall": (84.0, -183.0),
    "MerchantManor": (136.0, -114.0),
    "ManorGarden": (118.0, -176.0),
    "OperaStage": (60.0, -148.0),
    "TempleFair": (45.0, -134.0),
    "CityGodTemple": (0.0, -125.0),
    "BellPavilion": (NORTH_X, -98.0),
    "Bathhouse": (16.0, -94.0),
    "Pawnshop": (19.0, -55.0),
    "Tavern": (-60.0, 70.0),
    "Brewery": (-12.0, 107.0),
    "Mill": (-35.0, -168.0),
    "BoatYard": (-50.0, 146.0),
    "LowerDocks": (-66.0, 108.0),
    "StoneBridgeTown": (0.0, CANAL_Z),
    "Canal": (30.0, 97.0),
    "Orphanage": (-40.0, -114.0),
    "PostStation": (128.0, 4.0),
    "Barracks": (-20.0, -178.0),
    "ExecutionGround": (-58.0, -26.0),
    "Tannery": (-40.0, 238.0),
    "Kilns": (-26.0, 196.0),
}


def build_districts(add, rnd):
    gy = height
    for asset, name, x, z, yaw, level, scale in S.items:
        add(asset, x, z, yaw, scale, name, y=level)
    # the outer wall (city_wall segments), gaps for the three gates and the river bank
    for (x0, z0, x1, z1, gaps) in ((OUT_W, OUT_N, OUT_E, OUT_N, [(NORTH_X - OUT_W, 11.5)]),
                                   (OUT_E, OUT_N, OUT_E, OUT_S, [(-4 - OUT_N, 11.5)]),
                                   (OUT_W, OUT_S, OUT_E, OUT_S, [(0 - OUT_W, 11.5)])):
        wall_run(add, x0, z0, x1, z1, gaps=gaps, asset="city_wall")
    for (x, z) in ((OUT_E, OUT_N), (OUT_E, OUT_S)):
        add("watchtower", x - 4, z + (4 if z < 0 else -4), 0, 1.0)
    # the humpbacked bridge and the canal's willows and boats
    add("arch_bridge", 0, CANAL_Z, 0, 1.0, "StoneBridgeTownSpan", y=0.0)
    add("arch_bridge", 60, CANAL_Z, 0, 0.9, "CanalBridgeEast", y=0.0)
    for x in range(-50, 120, 16):
        if abs(x) < 8 or abs(x - 60) < 8:
            continue
        add("willow_tree", x, CANAL_Z - 7.5, rnd.uniform(0, 360), rnd.uniform(0.9, 1.1), None, y=-0.1)
        add("willow_tree", x + 8, CANAL_Z + 7.5, rnd.uniform(0, 360), rnd.uniform(0.9, 1.1), None, y=-0.1)
    for x in (-30, 30, 90):
        add("sampan", x, CANAL_Z + 1.5, 90, 0.8, None, y=-1.7)
    # the night market: lantern lines across the street and stalls
    for z in range(96, 148, 10):
        add("lantern_line", 0, z, 0, 1.0, None, y=0.0)
    for z in (100, 112, 124, 140):
        add("market_stall", -8.5, z, 90, 1.0, None, y=0.0)
        add("market_stall", 8.5, z + 5, -90, 1.0, None, y=0.0)
    # temple fair: stalls, lanterns, incense
    for (x, z, yaw) in ((38, -130, 0), (46, -128, 0), (72, -128, 0), (80, -130, 0), (84, -140, -90), (36, -142, 90)):
        add("market_stall", x, z, yaw, 1.0, None, y=0.0)
    add("lantern_line", 60, -128, 90, 1.0, None, y=0.0)
    add("incense_burner", 0, -137, 0, 1.0, "IncenseBurnerCityGod", y=0.0)
    for x in (-8, 8):
        add("stone_lantern", x, -126, 0, 1.0, None, y=0.0)
    add("bronze_bell", NORTH_X + 10, -118, 0, 0.9, None, y=0.0)
    # academy and manor: walls, rocks, garden pavilion
    for (x, z) in ((126, -180), (146, -186), (140, -170)):
        add("scholar_rock", x, z, rnd.uniform(0, 360), rnd.uniform(0.8, 1.2), None, y=gy(x, z))
    add("pavilion", 150, -192, 200, 0.9, "ManorGardenPavilion", y=gy(150, -192))
    for (x, z) in ((120, -196), (152, -168), (124, -164)):
        add("plum_blossom_tree", x, z, rnd.uniform(0, 360), 1.0, None, y=gy(x, z))
    for z in (-120, -135, -150, -165, -180, -195):
        add("courtyard_wall", 116, z, 90, 1.0, None, y=0.0)
        add("courtyard_wall", 147, z + 3, 90, 1.0, None, y=0.0) if z < -135 else None
    for x in (88, 112):
        add("stone_lantern", x, -136, 0, 1.0, None, y=0.0)
    # barracks yard
    add("weapon_rack", -30, -184, 0, 1.0, None, y=0.0)
    for (x, z) in ((-12, -190), (-8, -186), (-4, -190)):
        add("training_dummy", x, z, rnd.uniform(-20, 20), 1.0, None, y=0.0)
    add("sect_banner", -34, -176, 0, 1.0, None, y=0.0)
    # granary sacks, the pawnshop's cart, the bathhouse's jars
    add("crates", -52, -80, 20, 1.0, None, y=0.0)
    add("cart", -28, -76, 80, 1.0, None, y=0.0)
    add("brewery_jars", -28, 132, 0, 1.0, "BreweryJars", y=0.0)
    # river: the lower docks, sampans, the mill wheel's race, kilns' pots, the tannery
    bank_x = RIVER.point(RIVER.distance(-72, 108)[1])[0] + BANK
    add("river_dock", bank_x, 108, -90, 1.0, "LowerDocksPier", y=0.0)
    add("sampan", bank_x - 6, 104, 10, 1.0, None, y=WATER_Y)
    add("sampan", bank_x - 5, 120, -8, 1.0, None, y=WATER_Y)
    add("crates", -62, 100, 40, 1.0, None, y=0.0)
    add("cart", -58, 114, 10, 1.0, None, y=0.0)
    add("crates", -54, 140, 80, 1.0, None, y=0.0)
    # east: post road milestones, field huts
    for (x, z) in ((190, -30), (230, 30), (210, -90)):
        add("hermit_hut", x, z, rnd.uniform(0, 360), 0.85, None, y=gy(x, z))
    add("cart", 138, 6, 30, 1.0, None, y=0.0)
    add("village_well", 110, 30, 0, 0.9, None, y=0.0)
    # west bank: a ferry landing, huts and fields
    for (x, z) in ((-150, -60), (-160, 40), (-200, 120)):
        add("hermit_hut", x, z, rnd.uniform(0, 360), 0.9, None, y=gy(x, z))


def scatter(add, rnd, items):
    """Trees and rocks on the valley slopes and the far fields, clear of buildings, roads and markers."""
    clear = [(r.cx, r.cz, max(r.hw, r.hd) + 4) for _, _, r in S.solids]
    clear += [(x, z, 8) for (x, z) in NEW_MARKERS.values()]
    clear += [(0, 60, 14), (TELEPORT[0], TELEPORT[1], 8), (GRAVEYARD[0], GRAVEYARD[1], GRAVEYARD[2] + 6), (72, 12, 6),
              (59.5, 34, 6)]
    placed = []
    tries = 0
    while len(placed) < 420 and tries < 40000:
        tries += 1
        x, z = rnd.uniform(-SPAN + 8, SPAN - 8), rnd.uniform(-SPAN + 8, SPAN - 8)
        out = boundary(x, z)
        if out > 34 or river_distance(x, z) < 13:
            continue
        if OUT_W - 4 < x < OUT_E + 8 and OUT_N - 8 < z < OUT_S + 8 and not (_in_rect(x, z, (56, -110, 112, -40), 0.01)):
            continue
        if G.surface(x, z) is not None:
            continue
        if any(math.hypot(x - a, z - b) < r for (a, b, r) in clear) or any(math.hypot(x - a, z - b) < 7 for a, b in placed):
            continue
        r = rnd.random()
        yaw = rnd.uniform(0, 360)
        if r < 0.42:
            add("pine_tree_tall" if rnd.random() < 0.5 else "pine_tree", x, z, yaw, rnd.uniform(0.9, 1.35), dy=-0.3)
        elif r < 0.58:
            add("plum_blossom_tree", x, z, yaw, rnd.uniform(0.8, 1.1), dy=-0.2)
        elif r < 0.72:
            add("bamboo_cluster", x, z, yaw, rnd.uniform(0.9, 1.2), dy=-0.1)
        elif r < 0.8:
            add("willow_tree", x, z, yaw, rnd.uniform(0.9, 1.1), dy=-0.1)
        else:
            add("boulders", x, z, yaw, rnd.uniform(0.7, 1.6), dy=-0.3)
        placed.append((x, z))

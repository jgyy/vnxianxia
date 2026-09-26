"""Qingshi Town: a walled mortal town on a river, with farms and a hillside graveyard.

As for the forest, the height field lives here in pure Python and the Blender
town terrain (blender/xianxia/lands.py) is built from it. Coordinates are
Godot's (x east, z south). A road from the south reaches the main gate; the
main street runs north to the magistrate's yamen and a cross street joins the
west gate (river docks) and the east gate (farms, graveyard).
"""
import math
import random

from . import common
from .bamboo_forest import Polyline, fbm2, lerp, smoothstep

WALL_W, WALL_E, WALL_N, WALL_S = -48.0, 48.0, -48.0, 40.0
WALL_T = 1.8                         # town_wall thickness
GATE_W = 11.0                        # town_gate footprint along the wall
CROSS_Z = -4.0                       # the east-west cross street
PLAY = 92.0                          # valley walls rise beyond this (north, south, east)
SPAN = 124.0

RIVER = Polyline([(-80, -140), (-79, -95), (-82, -45), (-80, 0), (-78, 45), (-81, 95), (-80, 140)], 18.0, 8)
BANK = 8.3                           # embankment distance from the river centre line
WATER_Y = -1.4
DOCK_Z = -4.0

STREETS = {  # paved: (points, width)
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


def boundary(x, z):
    e = 5.0 * fbm2(x * 0.03, z * 0.03, 2, 61)
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


def river_distance(x, z):
    return RIVER.distance(x, z, 30.0)[0]


def height(x, z):
    """Ground height at Godot (x, z)."""
    h = 0.7 * fbm2(x * 0.02, z * 0.02, 3, 51) + 0.2 * fbm2(x * 0.08, z * 0.08, 2, 52)
    # the walled town and its forecourts are level
    h = lerp(h, 0.0, _in_rect(x, z, (WALL_W - 5, WALL_N - 5, WALL_E + 5, WALL_S + 6), 8.0))
    for p in ROADS.values():
        d = p.distance(x, z, 6.0)[0]
        if d < 6:
            h = lerp(h, h * 0.3, smoothstep(6.0, 2.0, d))
    h = lerp(h, 0.0, _in_rect(x, z, (-74, -60, -48, 50), 6.0))
    h = lerp(h, 0.0, _in_rect(x, z, (TELEPORT[0] - 7, TELEPORT[1] - 7, TELEPORT[0] + 7, TELEPORT[1] + 7), 6.0))
    # terraced fields east of the wall
    w = _in_rect(x, z, FARM, 5.0)
    if w > 0:
        h = lerp(h, _terrace(x), w)
    # graveyard hill with a level terrace
    h += _hill(x, z)
    gx, gz, gr = GRAVEYARD
    d = math.hypot(x - gx, z - gz)
    if d < gr + 7:
        h = lerp(h, _hill(gx, gz), smoothstep(gr + 7, gr, d))
    out = boundary(x, z)
    if out > 0:
        crag = abs(fbm2(x * 0.045, z * 0.045, 4, 62)) * 9.0 + 2.5 * fbm2(x * 0.12, z * 0.12, 2, 63)
        h += 30.0 * (1 - math.exp(-out / 8.0)) + out * 0.55 + crag * min(1.0, out / 6)
    # the river channel, walled on the town side
    dr = river_distance(x, z)
    if dr < 12:
        east = x > RIVER.point(RIVER.distance(x, z)[1])[0]
        if east:
            h = lerp(h, -3.2, smoothstep(BANK - 0.3, BANK - 1.5, dr))
        else:
            h = lerp(h, -3.2, smoothstep(11.5, 7.5, dr))
    return h


def wall_run(add, x0, z0, x1, z1, gaps=()):
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
            add("town_wall", x0 + ux * t, z0 + uz * t, yaw, (seg / 8.0, 1.0, 1.0))


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
    wall_run(add, WALL_W - h, WALL_N, WALL_E + h, WALL_N)
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
    add("town_house", 22.0, 8.0, 0)
    add("town_house", 32.0, 8.0, 0)
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
    # distant karst pillars above the valley walls
    for k in range(11):
        a = math.radians(k * 360 / 11 + rnd.uniform(-10, 10))
        r = rnd.uniform(190, 250)
        add("karst_peak", math.cos(a) * r, math.sin(a) * r, rnd.uniform(0, 360), rnd.uniform(1.1, 1.6),
            y=rnd.uniform(-30, -10))
    # trees and rocks on the valley slopes
    keep = [(0, 60, 12), (tx, tz, 8), (gx, gz, gr + 6), (72, 12, 6), (59.5, 34, 6)]
    placed = []
    tries = 0
    while len(placed) < 150 and tries < 20000:
        tries += 1
        x, z = rnd.uniform(-SPAN + 6, SPAN - 6), rnd.uniform(-SPAN + 6, SPAN - 6)
        out = boundary(x, z)
        if out > 30 or river_distance(x, z) < 12:
            continue
        if WALL_W - 6 < x < WALL_E + 6 and WALL_N - 6 < z < WALL_S + 8:
            continue
        if _in_rect(x, z, FARM, 3.0) > 0 or _in_rect(x, z, (-74, -60, -48, 50), 3.0) > 0:
            continue
        if min(p.distance(x, z, 8.0)[0] for p in ROADS.values()) < 6:
            continue
        if any(math.hypot(x - a, z - b) < r for (a, b, r) in keep):
            continue
        if any(math.hypot(x - a, z - b) < 7.0 for (a, b) in placed):
            continue
        r = rnd.random()
        yaw = rnd.uniform(0, 360)
        if r < 0.45:
            add("pine_tree_tall" if rnd.random() < 0.5 else "pine_tree", x, z, yaw, rnd.uniform(0.9, 1.35), dy=-0.3)
        elif r < 0.62:
            add("plum_blossom_tree", x, z, yaw, rnd.uniform(0.8, 1.1), dy=-0.2)
        elif r < 0.8:
            add("bamboo_cluster", x, z, yaw, rnd.uniform(0.9, 1.2), dy=-0.1)
        else:
            add("boulders", x, z, yaw, rnd.uniform(0.7, 1.6), dy=-0.3)
        placed.append((x, z))

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
    }
    env = common.Env(
        sky=common.Sky(top=(0.36, 0.5, 0.72), horizon=(0.98, 0.82, 0.62), ground_bottom=(0.5, 0.44, 0.38),
                       ground_horizon=(0.92, 0.78, 0.62), curve=0.14, sun_angle_max=22.0),
        ambient_energy=1.0, exposure=1.08, fog_color=(0.94, 0.82, 0.68), fog_density=0.0016,
        fog_height=-5.0, fog_height_density=0.02, fog_sun_scatter=0.45, fog_sky_affect=0.2,
        glow_intensity=0.6, saturation=1.1, contrast=1.06, sun_pitch=-33.0, sun_yaw=-55.0,
        sun_color=(1.0, 0.84, 0.66), sun_energy=1.9, shadow_distance=130.0,
    )
    return common.MapDef("qingshi_town", "Qingshi Town", "town", items, markers, env=env, ambient="petals")

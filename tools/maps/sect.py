"""Azure Cloud Sect: the mountain-top sect, ported from the original level layout.

The layout (and its random seeds) is identical to the first sect scene; the map
adds a teleport array beside the processional way outside the gate, a few plum
trees and spirit herbs, and the named markers from tools/world_spec.py.
"""
import math
import random

from . import common

WALL_HALF_X = 29.0
WALL_NORTH = -50.0
WALL_SOUTH = 30.0
SEGMENT = 8.0

TELEPORT = (12.0, 0.0, 41.5)


def build_layout():
    rnd = random.Random(7)
    items = []  # (asset, node name, pos, yaw, scale)

    def add(asset, pos, yaw=0.0, scale=1.0, name=None):
        items.append((asset, name, pos, yaw, scale))

    add("terrain", (0, 0, 0), name="Terrain")
    add("cloud_sea", (0, -45, 0), name="CloudSea")
    add("main_hall", (0, 0, -38), name="MainHall")
    add("sect_gate", (0, 0, WALL_SOUTH), name="SectGate")
    add("pagoda", (20, 0, -38), name="Pagoda")
    add("pavilion", (-18, 0, -20), yaw=20, name="Pavilion")
    add("formation_array", (0, 0.04, 8), name="FormationArray")
    add("incense_burner", (0, 0.04, -22), name="IncenseBurner")
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
            add("stone_lantern", (x, 0.04, z))
    for z in (-14, -2, 12, 24):
        for x in (-11.5, 11.5):
            add("stone_lantern", (x, 0.04, z))
    # red paper lanterns hanging under the hall eaves and the gate beams
    for x in (-3.6, -1.2, 1.2, 3.6):
        add("red_lantern", (x, 6.2, -31.9), yaw=rnd.uniform(0, 90))
    for x in (-2.9, 2.9):
        add("red_lantern", (x, 3.7, WALL_SOUTH + 0.05))
    # banners
    for x in (-8, 8):
        add("sect_banner", (x, 0.04, WALL_SOUTH - 4), yaw=180 if x > 0 else 0)
    for x in (-13, 13):
        add("sect_banner", (x, 0.04, -26), yaw=180 if x > 0 else 0)
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
    markers = {
        "PlayerSpawn": (3.0, 1.0, 43.0),
        "TeleportArray": (tx, 0.9, tz),
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
    }
    return common.MapDef("sect", "Azure Cloud Sect", "sect", items, markers, env=common.Env(), ambient="motes")

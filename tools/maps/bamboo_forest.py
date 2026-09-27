"""Whispering Bamboo Forest: a misty valley of bamboo, a stream and old ruins, now a whole forest
(about ten times the old area).

The first map's forest (paths, stream, bridge, hermit hut, herb grove, spirit spring, wolf den,
bandit camp and lookout, ruins and shrine, clearing) is untouched in the middle. Around it:

* west: the bamboo cutters' stilt-house village and its earth-god shrine, the walled sacred spring,
  the mill waterwheel on the stream, the old battlefield
* north-west: the misty lake with its pavilion on stilts and fishing jetty, the alchemist's cottage
* north: the temple half-buried by earth and roots before its sunken courtyard, and against the valley
  wall the cliff of weathered stone buddhas with a narrow path along its foot
* east: the stream falls into a gorge (the rope bridge crosses it), the banyan giant, the smugglers'
  trail through the thickest bamboo, the spider hollow, the tiger ridge, the echo cave
* south: the forest crossroads and its wayside shrine, the woodcutters' camp, the charcoal kilns in
  their smoky hollow, the hunter's lodge, the sect's watchpost on stilts, the ring of lingzhi, the
  panda grove of giant bamboo, the poison marsh, the hidden valley of wild plum, and the forest gate
  where the road leaves for the south

The height field lives here in pure Python (a ``terrain.Ground``) so the Blender terrain builder
(blender/xianxia/lands.py) and this layout agree on every ground height. Coordinates are Godot's
(x east, z south).
"""
import math
import random

from . import common
from .layout import Sites, check_markers
from .terrain import (Disc, Ground, Path, Polyline, Rect, box, catmull, fbm2, lerp, noise2,  # noqa: F401
                      smoothstep, yaw_facing)

# --------------------------------------------------------------------------
# layout of the first map
# --------------------------------------------------------------------------
PLAY_X, PLAY_Z = 280.0, 285.0        # walkable half extents before the valley walls rise
SPAN = 320.0                         # terrain half size

PATHS = {
    # main path: forest edge (south) -> bridge -> clearing
    "main": Polyline([(-4, 112), (-1, 96), (1, 84), (-3, 70), (-8, 57), (-6, 44), (0, 32), (6, 20),
                      (8, 10), (8, 4), (8, -3), (10, -15), (12, -28)], 3.4),
    # clearing -> ruins gate -> inner courtyard -> shrine
    "ruins": Polyline([(12, -28), (0, -33), (-14, -35), (-28, -36), (-40, -40), (-41, -50),
                       (-42, -60), (-44, -70)], 3.0),
    # clearing -> bandit camp
    "camp": Polyline([(12, -28), (24, -33), (36, -39), (47, -44)], 2.6),
    # side trail to the hermit's hut, continuing to the wolf den
    "hermit": Polyline([(3, 26), (16, 28), (30, 31), (44, 33), (58, 36), (63, 46), (66, 56), (68, 63)], 2.2),
    # side trail west to the herb grove and the spirit spring
    "herbs": Polyline([(-7, 50), (-20, 45), (-34, 38), (-48, 31), (-50, 40), (-44, 50), (-36, 58)], 2.2),
    # camp -> lookout
    "lookout": Polyline([(47, -44), (58, -38), (66, -31), (72, -26)], 1.8),
    # --- the enlarged forest
    "south": Polyline([(-4, 112), (-2, 140), (0, 170), (4, 210), (-2, 250), (0, 282)], 3.6),
    "village": Polyline([(0, 170), (-40, 160), (-90, 120), (-130, 70), (-165, 52)], 3.0),
    "west": Polyline([(-165, 52), (-160, 10), (-150, -30), (-128, -70), (-120, -110)], 2.8),
    "lake": Polyline([(-120, -110), (-150, -112), (-190, -115)], 2.6),
    "north": Polyline([(-44, -70), (-40, -110), (-20, -150), (0, -178)], 3.0),
    "buddhas": Polyline([(0, -178), (30, -210), (60, -236), (100, -240)], 2.4),
    "east": Polyline([(72, -26), (110, -40), (150, -90), (172, -120), (210, -150), (228, -190)], 2.4),
    "gorge": Polyline([(68, 63), (110, 60), (150, 50), (190, 44), (232, 44), (252, 38)], 2.6),
    "southeast": Polyline([(0, 170), (60, 150), (100, 140), (150, 160), (185, 188)], 2.6),
    "hunter": Polyline([(100, 140), (130, 110), (175, 96)], 2.2),
    "ridge": Polyline([(150, -90), (200, -80), (228, -70)], 2.0),
    "alchemist": Polyline([(-40, -110), (-78, -140)], 2.0),
    "hidden": Polyline([(-90, 120), (-150, 170), (-200, 220), (-222, 238)], 2.0),
    "panda": Polyline([(-40, 160), (-90, 196), (-112, 204)], 2.0),
}
STREAM = Polyline([(-330, -26), (-260, -22), (-190, -14), (-122, -10), (-96, -8), (-75, -4), (-55, 4), (-35, 2),
                   (-18, 8), (-2, 6), (8, 4), (22, 0), (38, -6), (55, -2), (72, 6), (96, 10), (122, 14),
                   (150, 16), (180, 18), (204, 20)], 6.0)
GORGE = Path([(204, 21), (230, 24), (262, 20), (300, 24), (340, 22)], 28.0, samples=3)
FALLS_X = 206.0
GORGE_Y = -13.0

# flattened places: name -> (x, z, radius)
ZONES = {
    "spawn": (0.5, 76, 8), "teleport": (-7.5, 81, 6), "forest_path": (-6, 44, 6), "herb_grove": (-50, 31, 9),
    "spring": (-38, 62, 8), "hermit": (58, 31, 9), "clearing": (12, -28, 15), "ruins_gate": (-40, -38, 7),
    "ruins_inner": (-42, -61, 17), "camp": (50, -46, 13),
    # the enlarged forest
    "village": (-165, 45, 26), "sacred": (-208, 84, 13), "waterwheel": (-150, 2, 9), "battlefield": (-110, -40, 20),
    "lake_shore": (-190, -112, 12), "alchemist": (-84, -146, 12), "crossroads": (0, 170, 12),
    "woodcut": (96, 146, 16), "lodge": (180, 94, 12), "watchpost": (112, 62, 10), "mushroom": (-50, 132, 9),
    "panda": (-115, 204, 20), "hidden": (-232, 236, 26), "banyan": (140, -150, 22), "smugglers": (172, -118, 6),
    "gate": (0, 272, 12), "gorge_rim": (240, 48, 12),
}
LOOKOUT = (74, -24)                  # rocky rise: flat top, walkable flanks
WOLF_DEN = (70, 66)                  # hollow before the cave mouth
POOL = (-44, 69, 6.5)                # spirit spring pool (x, z, radius)
LAKE = (-190, -162, 40.0, 1.3)       # misty lake centre, radius (z), x stretch
TIGER = (228, -76)
SPIDER = (224, -204)
KILNS = (152, 186)
MARSH = (206, 214, 26.0)
TEMPLE = (0, -206)                   # buried temple (front at the courtyard)
UNDERCROFT = (0, -188, 13, 9)        # sunken courtyard x, z, half sizes
UNDER_Y = -3.5
BUDDHAS = (70, -262)                 # the cliff face (faces south)


def stream_level(x):
    """Water surface height of the stream (flows east, then falls into the gorge)."""
    if x > FALLS_X:
        return GORGE_Y + 0.3
    return 0.9 - 1.6 * (x + 128.0) / 256.0


def _low(x, z):
    return 2.8 * fbm2(x * 0.016, z * 0.016, 3, 11)


def boundary(x, z):
    """Distance past the walkable area (0 inside)."""
    e = 10.0 * fbm2(x * 0.02, z * 0.02, 2, 31)
    ox = abs(x) - PLAY_X + e
    oz = abs(z) - PLAY_Z + e
    return math.hypot(max(ox, 0.0), max(oz, 0.0))


def _path_distance(x, z, reach=8.0):
    return min(p.distance(x, z, reach)[0] for p in PATHS.values())


def height(x, z):
    """Ground height at Godot (x, z)."""
    return G.height(x, z)


def _base(x, z):
    low = _low(x, z)
    detail = 0.7 * fbm2(x * 0.07, z * 0.07, 2, 12)
    h = low + detail
    far = math.hypot(x, z * 0.9)
    h += 5.0 * fbm2(x * 0.008, z * 0.008, 3, 13) * smoothstep(120, 220, far)
    # paths: smooth out the small bumps and sink a little
    dp = _path_distance(x, z)
    w = smoothstep(5.0, 1.2, dp)
    h -= (detail + 0.12) * w
    for (cx, cz, r) in ZONES.values():
        d = math.hypot(x - cx, z - cz)
        if d < r + 8:
            h = lerp(h, _low(cx, cz), smoothstep(r + 8, r, d))
    return h


def _after(x, z, h):
    # the rocky lookout rise, the tiger ridge and the wolves' hollow
    d = math.hypot(x - LOOKOUT[0], z - LOOKOUT[1])
    if d < 20:
        h = lerp(h, _low(*LOOKOUT) + 6.0, smoothstep(19, 5.5, d))
    d = math.hypot(x - WOLF_DEN[0], z - WOLF_DEN[1])
    if d < 18:
        h = lerp(h, _low(*WOLF_DEN) - 2.4, smoothstep(17, 8, d))
    # spirit spring pool
    d = math.hypot(x - POOL[0], z - POOL[1])
    if d < POOL[2] + 4:
        h = lerp(h, _low(POOL[0], POOL[1]) - 1.3, smoothstep(POOL[2] + 1.5, POOL[2] - 2.5, d))
    # stream: level banks, then the bed (not in the gorge: that is its own pad)
    ds, _ = STREAM.distance(x, z, 16.0)
    if ds < 16 and x < FALLS_X - 2:
        lvl = stream_level(x)
        h = lerp(h, lvl + 0.9, smoothstep(16, 7, ds))
        h = lerp(h, lvl - 0.55, smoothstep(5.5, 1.8, ds))
    # valley walls
    out = boundary(x, z)
    if out > 0:
        crag = abs(fbm2(x * 0.045, z * 0.045, 4, 41)) * 9.0 + 2.5 * fbm2(x * 0.12, z * 0.12, 2, 42)
        h += 30.0 * (1 - math.exp(-out / 8.0)) + out * 0.55 + crag * min(1.0, out / 6)
    return h


def _classify(x, z, h, nz):
    if nz < 0.74:
        return "cliff"
    if boundary(x, z) > 3:
        return "moss"
    return "forest"


G = Ground((-SPAN, -SPAN, SPAN, SPAN), 2.5, _base, _classify, after=None, chunk=40)
# pads applied before the old-map features (_after runs last, through the final pad below)
G.pad(Disc(TIGER[0], TIGER[1], 16, sx=1.8), 7.0, blend=16)                         # tiger ridge
G.pad(Disc(SPIDER[0], SPIDER[1], 16), -3.5, blend=12, op="min")                   # the spider hollow
G.pad(Disc(KILNS[0], KILNS[1], 15), -2.0, blend=10, op="min")                      # the smoky kiln hollow
G.pad(Disc(MARSH[0], MARSH[1], MARSH[2], sx=1.3, wobble=0.15, seed=6), -0.6, blend=8)  # the poison marsh
G.pad(Disc(-232, 236, 30), 1.0, blend=12)                                          # the hidden valley floor
G.pad(Disc(LAKE[0], LAKE[1], LAKE[2], sx=LAKE[3], wobble=0.12, seed=2), -3.0, blend=12, op="min")
G.pad(Disc(-208, 84, 12), 0.6, blend=6)                                            # the sacred spring terrace
SACRED_POOL = Disc(-208, 84, 5.0)
G.pad(SACRED_POOL, -0.6, blend=2.0, op="min")
UNDER = Rect(UNDERCROFT[0], UNDERCROFT[1], UNDERCROFT[2], UNDERCROFT[3], 0, 2)
UNDER_RAMP = Path([(0, -164, 0.0), (0, -170, 0.0), (0, -179, UNDER_Y)], 6.0, flat_ends=True)
G.pad(Rect(TEMPLE[0], TEMPLE[1], 13, 12), UNDER_Y, blend=8)                        # the temple's sunken site
G.pad(UNDER, UNDER_Y, blend=2.5)
G.pad(UNDER_RAMP, UNDER_RAMP.level, blend=2.0)
G.pad(Rect(BUDDHAS[0], BUDDHAS[1] + 16, 26, 7), 1.0, blend=8)                      # ledge below the buddhas
# the gorge and the plunge pool below the falls, and the path down into it
G.pad(GORGE, GORGE_Y, blend=5)
G.pad(Disc(FALLS_X + 10, 22, 9), GORGE_Y - 1.2, blend=3, op="min")
GORGE_PATH = Path([(226, 60, 0.0), (218, 48, -3.5), (230, 40, -7.0), (220, 32, -10.5), (228, 26, GORGE_Y)], 4.0)
G.pad(GORGE_PATH, GORGE_PATH.level, blend=3)
G.after = _after


# ---- buildings --------------------------------------------------------------------------------------
S = Sites(G)
_VILLAGE = [(-180, 26, 40), (-150, 24, -30), (-188, 56, 100), (-142, 60, -100), (-170, 72, 180)]
for i, (x, z, yaw) in enumerate(_VILLAGE):
    S.add("stilt_house" if i % 2 == 0 else "stilt_house_small", x, z, yaw, _low(-165, 45),
          name=f"StiltHouse{i + 1}")
S.add("earth_shrine", -165, 38, 0, _low(-165, 45), name="VillageEarthShrine")
S.add("rustic_hut", -84, -154, 20, _low(-84, -146), name="AlchemistHut")
S.add("hunter_lodge", 180, 88, 0, _low(180, 94), name="HunterLodgeHouse")
S.add("forest_watchpost", 112, 58, 0, _low(112, 62), name="WatchpostTower")
S.add("woodcutter_camp", 100, 150, 0, _low(96, 146), name="WoodcutterYard")
S.add("buried_temple", TEMPLE[0], TEMPLE[1] - 4, 0, UNDER_Y, name="BuriedTempleHall", flatten=False)
S.add("buddha_cliff", BUDDHAS[0], BUDDHAS[1], 0, 1.0, name="BuddhaCliffFace", flatten=False)
S.add("forest_gate", 0, 276, 0, _low(0, 272), name="ForestGateArch")


def _stream_x(z_target):
    return None


def build() -> common.MapDef:
    rnd = random.Random(23)
    items = []

    def add(asset, x, z, yaw=0.0, scale=1.0, name=None, dy=0.0, y=None):
        yy = height(x, z) + dy if y is None else y
        items.append((asset, name, (round(x, 3), round(yy, 3), round(z, 3)), round(yaw, 2), scale))

    add("forest_terrain", 0, 0, name="Terrain", y=0.0)

    # --- arrival: the teleport array at the forest edge -----------------------------------
    tx, tz = ZONES["teleport"][:2]
    ty = height(tx, tz)
    add("teleport_array", tx, tz, yaw=0, name="TeleportArray", y=ty)
    for (dx, dz, yw, s) in ((-5.5, 3.5, 30, 0.7), (5.0, 4.0, 200, 0.8), (-4.5, -4.8, 100, 0.9)):
        add("fern_cluster", tx + dx, tz + dz, yw, s)
    add("boulders", tx - 7.5, tz + 1.5, 40, 0.8, dy=-0.2)
    add("stone_lantern", tx + 4.2, tz - 3.8, 15, 0.9)
    add("stone_lantern", 4.5, 70, -20, 0.9)

    # --- the bridge over the stream ---------------------------------------------------------
    bx, bz = 8.0, 4.0
    _, t = STREAM.distance(bx, bz)
    sdx, sdz = STREAM.tangent(t)
    bridge_yaw = math.degrees(math.atan2(-sdz, sdx))  # deck runs across the stream
    bank = stream_level(bx) + 0.9
    add("wooden_bridge", bx, bz, bridge_yaw, name="OldBridge", y=bank)

    # --- the stream: river stones, reeds of bamboo on the banks ------------------------------
    for k in range(40):
        t = 0.05 + 0.9 * k / 39 + rnd.uniform(-0.005, 0.005)
        px, pz = STREAM.point(t)
        if math.hypot(px - bx, pz - bz) < 9 or px > FALLS_X - 6 or any(
                math.hypot(px - zx, pz - zz) < zr + 4 for (zx, zz, zr) in (ZONES["waterwheel"],)):
            continue
        nx, nz = STREAM.tangent(t)
        side = rnd.choice((-1, 1))
        off = rnd.uniform(4.5, 7.0) * side
        add("boulders", px - nz * off, pz + nx * off, rnd.uniform(0, 360), rnd.uniform(0.35, 0.8), dy=-0.25)

    # --- clearing, fallen logs ----------------------------------------------------------------
    add("fallen_log", 26, -22, 70, 1.0, dy=0.05)
    add("fallen_log", -2, -16, 150, 0.8, dy=0.05)
    add("broken_pillar", 22, -38, 30, 0.9)
    add("stone_stele", 3, -21, 150, 1.0, name="WaysideStele")

    # --- ruins: archway, walls, inner court, shrine --------------------------------------------
    gx, gz = -40.0, -46.0
    add("stone_archway", gx, gz, 0, name="RuinsArchway")
    for (x, z, yaw, s) in ((-49.5, -46.5, 0, 1.0), (-57.5, -46.0, 4, 0.8), (-31.0, -46.3, -3, 1.0),
                           (-23.5, -47.0, 8, 0.7), (-63.0, -54.0, 90, 1.0), (-63.5, -63.0, 86, 0.9),
                           (-62.5, -72.5, 93, 1.0), (-21.0, -56.0, 92, 1.0), (-21.5, -66.5, 88, 0.8),
                           (-22.0, -76.0, 95, 1.0), (-55.0, -85.0, 180, 1.0), (-30.0, -85.5, 176, 0.9)):
        add("ruin_wall", x, z, yaw, s)
    for (x, z) in ((-34.5, -52), (-49.5, -52), (-34.5, -70), (-49.5, -70), (-28.0, -61.5), (-56.0, -61.5)):
        add("broken_pillar", x, z, rnd.uniform(0, 360), rnd.uniform(0.85, 1.15))
    add("ruined_shrine", -42, -81, 0, name="AncientShrine")
    add("stone_stele", -33.5, -75.5, -25, 1.0, name="ShrineStele")
    add("stone_lantern", -47.5, -73.5, 10, 0.9)
    add("incense_burner", -42, -71.5, 0, 0.55, name="IncenseBurnerShrine")
    add("scholar_rock", -58, -79, 60, 0.9)
    add("fallen_log", -56, -58, 20, 0.7, dy=0.05)

    # --- bandit camp and lookout ------------------------------------------------------------
    cx, cz = ZONES["camp"][:2]
    add("campfire", cx - 4.5, cz - 1.5, 0, name="BanditFire")
    for (dx, dz) in ((-11, -7), (5.5, -10), (10.5, 2.5), (-9.5, 6.5)):
        add("bandit_tent", cx + dx, cz + dz, yaw_facing(cx + dx, cz + dz, cx - 4.5, cz - 1.5))
    add("crates", cx + 11, cz - 7, -30)
    add("crates", cx - 13, cz - 0.5, 75, 0.9)
    add("treasure_chest", cx + 2.5, cz - 11.5, 190, name="BanditChest")
    add("cart", cx - 2.5, cz + 10.5, 110)
    lx, lz = LOOKOUT
    for (dx, dz, s) in ((6.5, -3.0, 1.2), (-2.5, -7.5, 1.0), (3.0, 7.0, 0.9), (8, 4, 1.3), (-7.5, 3.5, 0.8)):
        add("boulders", lx + dx, lz + dz, rnd.uniform(0, 360), s, dy=-0.4)
    add("scholar_rock", lx + 3.5, lz - 2.5, 200, 0.8)

    # --- hermit's hut ---------------------------------------------------------------------------
    hx, hz = ZONES["hermit"][:2]
    add("hermit_hut", hx + 1, hz - 6.5, -10, name="HermitHut")
    add("campfire", hx - 5.5, hz - 3.5, 0, 0.7)
    add("plum_blossom_tree", hx + 9, hz - 2, 40, 0.9)
    add("scholar_rock", hx - 8, hz - 9, 120, 0.7)

    # --- wolf den -----------------------------------------------------------------------------
    wx, wz = WOLF_DEN
    add("cave_mouth", wx + 9.5, wz + 8.5, yaw_facing(wx + 9.5, wz + 8.5, wx, wz), name="WolfCave")
    for (dx, dz, s) in ((-9, 3, 1.1), (-4, 10, 1.3), (7, -7, 1.0), (-10, -6, 0.9), (2, -11, 1.2)):
        add("boulders", wx + dx, wz + dz, rnd.uniform(0, 360), s, dy=-0.3)
    add("fallen_log", wx - 7, wz - 1, 160, 0.8, dy=0.05)

    # --- herb grove and the spirit spring ---------------------------------------------------------
    gx2, gz2 = ZONES["herb_grove"][:2]
    for k in range(9):
        a = k * 2.4 + 0.3
        r = 3.0 + (k % 3) * 2.2
        add("spirit_herb", gx2 + math.cos(a) * r, gz2 + math.sin(a) * r, rnd.uniform(0, 360), rnd.uniform(0.8, 1.3))
    add("plum_blossom_tree", gx2 - 9, gz2 - 6, 10, 1.0)
    add("scholar_rock", gx2 + 7.5, gz2 - 7, 300, 0.7)
    px_, pz_, pr_ = POOL
    add("spring_pool", px_, pz_, 0, name="SpiritSpring", y=pool_level())
    add("lotus_cluster", px_ - 1.5, pz_ + 1, 30, 0.8, y=pool_level() + 0.05)
    add("lotus_cluster", px_ + 2.0, pz_ - 1.5, 200, 0.6, y=pool_level() + 0.05)
    for k in range(9):
        a = k * 0.7 + 1.2
        add("boulders", px_ + math.cos(a) * (pr_ + 1.2), pz_ + math.sin(a) * (pr_ + 1.2), k * 40, 0.45, dy=-0.25)
    add("spirit_stone", px_ - 5.5, pz_ - 4.0, 20, 1.2)
    add("spirit_stone", px_ + 6.0, pz_ + 2.5, 140, 0.9)

    build_districts(add, rnd)

    # distant karst pillars above the valley walls
    for k in range(13):
        a = math.radians(k * 360 / 13 + rnd.uniform(-10, 10))
        r = rnd.uniform(380, 450)
        add("karst_peak", math.cos(a) * r, math.sin(a) * r, rnd.uniform(0, 360), rnd.uniform(1.3, 1.8),
            y=rnd.uniform(-20, 0))
    vegetation(add, rnd, items)

    def at(x, z, lift=1.0):
        return (x, round(height(x, z) + lift, 3), z)

    markers = {
        "PlayerSpawn": at(0.5, 76),
        "TeleportArray": (tx, round(ty + 0.4 + 0.5, 3), tz),
        "ForestPath": at(-6, 44),
        "OldBridge": (bx, round(bank + 0.6 + 0.6, 3), bz),
        "Stream": at(-24, 14.5),
        "HermitHut": at(hx - 1, hz + 3),
        "HerbGrove": at(gx2, gz2),
        "SpiritSpring": at(-35, 59),
        "WolfDen": at(wx - 1, wz - 1),
        "BanditCamp": at(cx + 1, cz + 1.5),
        "BanditLookout": at(lx, lz, 1.2),
        "RuinsGate": at(-40, -38.5),
        "AncientShrine": at(-42, -69),
        "RuinsInner": at(-42, -58),
        "Clearing": at(12, -28),
    }
    markers.update({k: at(x, z) for k, (x, z) in NEW_MARKERS.items()})
    markers["RopeBridge"] = (ROPE[0], 1.0 + height(ROPE[0], ROPE[1] - 21), ROPE[1])
    markers["FishingJetty"] = (JETTY[0], 0.6 + 1.0 + LAKE_Y + 0.9, JETTY[1] + 8.0)
    problems = check_markers("bamboo_forest", {k: markers[k] for k in NEW_MARKERS}, height, S.solids,
                             exempt=("RopeBridge", "FishingJetty", "LakePavilion", "Waterwheel"))
    if problems:
        raise SystemExit("bamboo_forest marker problems:\n  " + "\n  ".join(problems))
    env = common.Env(
        sky=common.Sky(top=(0.42, 0.58, 0.66), horizon=(0.82, 0.88, 0.8), ground_bottom=(0.36, 0.4, 0.32),
                       ground_horizon=(0.74, 0.8, 0.72), curve=0.1, sun_angle_max=25.0),
        ambient_energy=1.15, exposure=1.18, fog_color=(0.7, 0.8, 0.72), fog_density=0.0016,
        fog_height=-3.0, fog_height_density=0.035, fog_sun_scatter=0.35, fog_sky_affect=0.3,
        glow_intensity=0.7, saturation=1.05, contrast=1.04, sun_pitch=-52.0, sun_yaw=-25.0,
        sun_color=(1.0, 0.96, 0.86), sun_energy=1.8, shadow_distance=130.0,
    )
    return common.MapDef("bamboo_forest", "Whispering Bamboo Forest", "forest", items, markers, env=env,
                         ambient="fireflies", kill_y=-40.0)


def pool_level():
    return _low(POOL[0], POOL[1]) - 0.45


LAKE_Y = -1.3
ROPE = (262.0, 21.0)                 # rope bridge centre (spans the gorge north-south)
JETTY = (-190.0, -210.0)             # jetty root on the lake's north shore (runs south into the lake)
WHEEL = (-150.0, -9.5)               # the waterwheel, on the stream's north bank

NEW_MARKERS = {
    "WoodcutterCamp": (96.0, 138.0),
    "CharcoalKilns": (KILNS[0], KILNS[1] - 1.0),
    "BambooVillage": (-165.0, 45.0),
    "VillageShrine": (-165.0, 32.0),
    "MistyLake": (-128.0, -150.0),
    "LakePavilion": (-190.0, -113.0),
    "Waterwheel": (-150.0, 6.0),
    "FishingJetty": (-190.0, -212.0),
    "PandaGrove": (-115.0, 204.0),
    "TigerRidge": (TIGER[0], TIGER[1]),
    "BanyanGiant": (126.0, -150.0),
    "SpiderHollow": (SPIDER[0], SPIDER[1]),
    "PoisonMarsh": (180.0, 200.0),
    "MushroomRing": (-50.0, 132.0),
    "ForestWatchpost": (112.0, 72.0),
    "HunterLodge": (180.0, 100.0),
    "BuriedTemple": (0.0, -193.0),
    "TempleUndercroft": (0.0, -184.0),
    "StoneBuddhas": (70.0, -240.0),
    "CliffPath": (40.0, -244.0),
    "WaterfallGorge": (232.0, 16.0),
    "ForestCrossroads": (4.0, 164.0),
    "OldBattlefield": (-110.0, -40.0),
    "HiddenValley": (-232.0, 236.0),
    "EchoCave": (238.0, -230.0),
    "SmugglersTrail": (172.0, -118.0),
    "RopeBridge": ROPE,
    "AlchemistCottage": (-84.0, -140.0),
    "SacredSpring": (-208.0, 95.0),
    "ForestGate": (0.0, 266.0),
}

# regions (after the markers table: the region list is part of the ground)
for _name, _p in PATHS.items():
    G.region("dirt", Path(_p.pts, _p.width, wobble=0.18, seed=len(_name)))
for _k in ("camp", "clearing", "hermit", "teleport", "village", "woodcut", "crossroads", "lodge", "watchpost", "gate",
           "alchemist", "gorge_rim"):
    _x, _z, _r = ZONES[_k]
    G.region("dirt", Disc(_x, _z, _r * 0.75, wobble=0.2, seed=len(_k)))
G.region("paving_old", Disc(ZONES["ruins_inner"][0], ZONES["ruins_inner"][1], ZONES["ruins_inner"][2] + 1))
G.region("paving_old", UNDER)
G.region("paving_old", UNDER_RAMP)
G.region("paving_old", Disc(-208, 84, 9.0))
G.region("pebbles", Path(STREAM.pts, 6.8))
G.region("pebbles", GORGE)
G.region("pebbles", Disc(LAKE[0], LAKE[1], LAKE[2] * 0.96, sx=LAKE[3], wobble=0.12, seed=2))
G.region("mud", Disc(MARSH[0], MARSH[1], MARSH[2] * 1.05, sx=1.3, wobble=0.15, seed=6))
G.region("gravel", Rect(BUDDHAS[0], BUDDHAS[1] + 16, 24, 5))
G.region("moss", Disc(SPIDER[0], SPIDER[1], 20))
G.region("moss", Disc(-232, 236, 24, wobble=0.2, seed=8))
G.region("dirt", GORGE_PATH)
G.region("dirt", Disc(KILNS[0], KILNS[1], 13))
G.water("stream", Path([p for p in STREAM.pts if p[0] < FALLS_X], 9.5),
        lambda x, z: stream_level(min(x, FALLS_X - 0.5)) - 0.1)
G.water("stream", GORGE, GORGE_Y + 0.35)
G.water("lake", Disc(LAKE[0], LAKE[1], LAKE[2] + 6, sx=LAKE[3]), LAKE_Y)
G.water("marsh", Disc(MARSH[0], MARSH[1], MARSH[2] * 0.9, sx=1.3, wobble=0.12, seed=6), -0.45)
G.water("pond", Disc(-208, 84, 5.6), 0.15)


def build_districts(add, rnd):
    gy = height
    for asset, name, x, z, yaw, level, scale in S.items:
        add(asset, x, z, yaw, scale, name, y=level)
    # the village: shrine, drying racks, jars, bamboo, a well
    add("drying_racks", -140, 40, 90, 1.0, None, y=gy(-140, 40))
    add("village_well", -178, 44, 0, 0.8, None, y=gy(-178, 44))
    add("campfire", -158, 50, 0, 0.7, None, y=gy(-158, 50))
    add("stone_wall_low", -208, 72, 0, 1.0, None, y=gy(-208, 72))
    for k in range(6):
        a = math.radians(40 + k * 56)
        x, z = -208 + 11 * math.cos(a), 84 + 11 * math.sin(a)
        if 70 < k * 56 + 40 < 110:
            continue
        add("stone_wall_low", x, z, -math.degrees(a) + 90, 1.0, None, y=gy(x, z))
    add("earth_shrine", -208, 76, 180, 0.8, "SpringShrine", y=gy(-208, 76))
    add("lotus_cluster", -208, 84, 0, 0.8, None, y=0.2)
    # the waterwheel on the stream
    add("waterwheel", WHEEL[0], WHEEL[1], 0, 1.0, "MillWaterwheel", y=stream_level(WHEEL[0]) - 0.2)
    # the misty lake: pavilion, jetty, reeds (bamboo) and boats
    add("lake_pavilion", -190, -136, 180, 1.0, "LakePavilionHouse", y=LAKE_Y)
    add("fishing_jetty", JETTY[0], JETTY[1], 0, 1.0, "FishingJettyPier", y=LAKE_Y)
    add("sampan", -170, -176, 30, 0.9, None, y=LAKE_Y)
    add("sampan", -216, -150, 120, 0.8, None, y=LAKE_Y)
    # the old battlefield, the alchemist's cottage
    add("battlefield_debris", -110, -40, 0, 1.0, "BattlefieldDebris", y=gy(-110, -40))
    add("burial_mounds", -112, -58, 10, 1.0, "BattleMounds", y=gy(-112, -58))
    add("drying_racks", -94, -140, 90, 0.9, None, y=gy(-94, -140))
    add("campfire", -76, -138, 0, 0.6, None, y=gy(-76, -138))
    # the buried temple, its sunken court, the stone buddhas and the cliff path
    for (x, z) in ((-9, -184), (9, -184)):
        add("stone_lantern", x, z, 0, 0.9, None, y=UNDER_Y)
    add("incense_burner", 0, -180, 0, 0.6, "IncenseBurnerUndercroft", y=UNDER_Y)
    for (x, z) in ((-16, -196), (16, -198), (-18, -214)):
        add("fallen_log", x, z, rnd.uniform(0, 360), 0.9, None, y=gy(x, z) + 0.05)
    for k in range(5):
        add("stone_lantern", 44 + k * 13, -246, 0, 0.8, None, y=gy(44 + k * 13, -246))
    # the gorge: the falls, the rope bridge, the path down
    add("waterfall", FALLS_X - 1.5, 21, -90, (1.3, 0.55, 1.0), "GorgeFalls", y=GORGE_Y - 0.4)
    add("rope_bridge_long", ROPE[0], ROPE[1], 0, 1.0, "RopeBridgeSpan", y=gy(ROPE[0], ROPE[1] - 21))
    # the south: crossroads shrine, woodcutters, kilns, lodge, watchpost, mushrooms, pandas, marsh, gate
    add("earth_shrine", 12, 176, -45, 0.7, "WaysideShrine", y=gy(12, 176))
    for k in range(3):
        a = 2 * math.pi * k / 3
        x, z = KILNS[0] + 7 * math.cos(a), KILNS[1] + 7 * math.sin(a) + 6
        add("charcoal_kiln", x, z, rnd.uniform(0, 360), 1.0, f"CharcoalKiln{k + 1}", y=gy(x, z))
    add("lingzhi_ring", -50, 132, 0, 1.0, "MushroomRingCircle", y=gy(-50, 132))
    for k in range(5):
        a = 2 * math.pi * k / 5
        x, z = -115 + 11 * math.cos(a), 204 + 11 * math.sin(a)
        add("giant_bamboo", x, z, rnd.uniform(0, 360), 1.0, None, y=gy(x, z) - 0.1)
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        x, z = MARSH[0] + MARSH[2] * 1.3 * 1.05 * math.cos(a), MARSH[1] + MARSH[2] * 1.05 * math.sin(a)
        add("dead_tree", x, z, rnd.uniform(0, 360), 0.8, None, y=gy(x, z) - 0.2)
    add("poison_flowers", MARSH[0] - 22, MARSH[1] - 8, 0, 1.0, None, y=gy(MARSH[0] - 22, MARSH[1] - 8))
    # the east: banyan, smugglers' crates, spider webs, tiger ridge rocks, the echo cave
    add("banyan_giant", 140, -150, 0, 1.0, "BanyanGiantTree", y=gy(140, -150) - 0.3)
    add("crates", 168, -126, 30, 1.0, None, y=gy(168, -126))
    add("cart", 178, -112, 70, 1.0, None, y=gy(178, -112))
    add("spider_webs", SPIDER[0], SPIDER[1], 0, 1.0, "SpiderWebs", y=gy(SPIDER[0], SPIDER[1]))
    for (dx, dz, s) in ((-18, -6, 1.8), (-8, 8, 1.4), (6, -9, 1.6), (18, 5, 1.9), (26, -4, 1.3)):
        add("boulders", TIGER[0] + dx, TIGER[1] + dz, rnd.uniform(0, 360), s, None, y=gy(TIGER[0] + dx, TIGER[1] + dz) - 0.4)
    add("scholar_rock", TIGER[0] + 10, TIGER[1] - 3, 30, 1.4, None, y=gy(TIGER[0] + 10, TIGER[1] - 3))
    add("cave_mouth", 246, -244, -30, 1.3, "EchoCaveMouth", y=gy(246, -244))
    # the hidden valley of wild plum
    for k in range(14):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(9, 22)
        x, z = -232 + r * math.cos(a), 236 + r * math.sin(a)
        add("plum_blossom_tree", x, z, rnd.uniform(0, 360), rnd.uniform(0.9, 1.25), None, y=gy(x, z) - 0.1)
    add("lotus_cluster", -60, 60, 0, 0.1, None, y=-50.0) if False else None


def vegetation(add, rnd, items):
    keep_clear = [(x, z, r + 2.5) for (x, z, r) in ZONES.values()]
    keep_clear += [(LOOKOUT[0], LOOKOUT[1], 14), (WOLF_DEN[0], WOLF_DEN[1], 12), (POOL[0], POOL[1], POOL[2] + 4),
                   (-42, -65, 26), (-40, -46, 8), (8.0, 4.0, 10), (79.5, 74.5, 9)]
    keep_clear += [(r.cx, r.cz, max(r.hw, r.hd) + 3) for _, _, r in S.solids]
    keep_clear += [(x, z, 8) for (x, z) in NEW_MARKERS.values()]
    keep_clear += [(LAKE[0], LAKE[1], LAKE[2] * LAKE[3] + 4), (MARSH[0], MARSH[1], MARSH[2] * 1.3 + 2),
                   (SPIDER[0], SPIDER[1], 12), (KILNS[0], KILNS[1], 12), (TEMPLE[0], TEMPLE[1] + 8, 24),
                   (BUDDHAS[0], BUDDHAS[1] + 12, 28), (ROPE[0], ROPE[1], 26), (-208, 84, 14), (WHEEL[0], WHEEL[1], 10)]
    placed = [(x, z) for (_, _, (x, _, z), _, _) in items[1:]]
    tries = 0
    count = 0
    while count < 1100 and tries < 90000:
        tries += 1
        x, z = rnd.uniform(-SPAN + 10, SPAN - 10), rnd.uniform(-SPAN + 10, SPAN - 10)
        out = boundary(x, z)
        if out > 34:
            continue
        dp = _path_distance(x, z)
        ds, _ = STREAM.distance(x, z, 10.0)
        if dp < 6.5 or ds < 7.5 or GORGE.sdf(x, z) < 6:
            continue
        if any(math.hypot(x - a, z - b) < r + 3.0 for (a, b, r) in keep_clear):
            continue
        if any(math.hypot(x - a, z - b) < 5.0 for (a, b) in placed[-400:]):
            continue
        r = rnd.random()
        yaw = rnd.uniform(0, 360)
        if out > 2 and r < 0.35:
            add("pine_tree_tall" if rnd.random() < 0.5 else "pine_tree", x, z, yaw, rnd.uniform(1.0, 1.4), dy=-0.3)
        elif r < 0.74:
            add("bamboo_grove", x, z, yaw, rnd.uniform(0.85, 1.2), dy=-0.1)
        elif r < 0.84:
            add("bamboo_cluster", x, z, yaw, rnd.uniform(0.9, 1.2), dy=-0.1)
        elif r < 0.93 and out == 0:
            add("fern_cluster", x, z, yaw, rnd.uniform(0.8, 1.3), dy=-0.05)
        elif r < 0.96:
            add("fallen_log", x, z, yaw, rnd.uniform(0.7, 1.0), dy=0.05)
        else:
            add("boulders", x, z, yaw, rnd.uniform(0.6, 1.5), dy=-0.3)
        placed.append((x, z))
        count += 1
    # the smugglers' trail runs through the thickest bamboo
    trail = PATHS["east"]
    for k in range(0, len(trail.pts), 2):
        x, z = trail.pts[k]
        if x < 150 or x > 215:
            continue
        nx, nz = trail.tangent(k / (len(trail.pts) - 1))
        for side in (-1, 1):
            fx, fz = x - nz * side * 4.2, z + nx * side * 4.2
            if math.hypot(fx - 172, fz + 118) > 7:
                add("bamboo_grove", fx, fz, rnd.uniform(0, 360), 1.1, dy=-0.1)
    # ferns softening the path edges
    for name, p in PATHS.items():
        for k in range(0, len(p.pts), 3):
            x, z = p.pts[k]
            nx, nz = p.tangent(k / (len(p.pts) - 1))
            side = rnd.choice((-1, 1))
            fx, fz = x - nz * side * rnd.uniform(3.2, 4.5), z + nx * side * rnd.uniform(3.2, 4.5)
            if boundary(fx, fz) > 0 or any(math.hypot(fx - a, fz - b) < r for (a, b, r) in keep_clear):
                continue
            if STREAM.distance(fx, fz, 8.0)[0] < 7:
                continue
            add("fern_cluster", fx, fz, rnd.uniform(0, 360), rnd.uniform(0.6, 1.0), dy=-0.05)

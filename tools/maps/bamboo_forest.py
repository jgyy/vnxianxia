"""Whispering Bamboo Forest: a misty valley of bamboo, a stream and old ruins.

The height field lives here in pure Python so the Blender terrain builder
(blender/xianxia/lands.py) and this layout agree on every ground height.
Coordinates are Godot's (x east, z south). The forest path enters from the
south, crosses the stream on a wooden bridge and forks at a clearing: west to
the ruins and the shrine, east to the bandit camp.
"""
import math
import random

from . import common

# --------------------------------------------------------------------------
# small pure-Python noise / geometry helpers (also used by qingshi_town)
# --------------------------------------------------------------------------


def _hash(ix, iz, seed):
    h = (ix * 73856093 ^ iz * 19349663 ^ seed * 83492791) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 32767.5 - 1.0


def noise2(x, z, seed=0):
    """Smooth value noise in [-1, 1]."""
    ix, iz = math.floor(x), math.floor(z)
    fx, fz = x - ix, z - iz
    fx, fz = fx * fx * (3 - 2 * fx), fz * fz * (3 - 2 * fz)
    a = _hash(ix, iz, seed)
    b = _hash(ix + 1, iz, seed)
    c = _hash(ix, iz + 1, seed)
    d = _hash(ix + 1, iz + 1, seed)
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fz


def fbm2(x, z, octaves=4, seed=0):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * noise2(x, z, seed + o * 17)
        norm += amp
        amp *= 0.5
        x, z = x * 2.03 + 11.7, z * 2.03 - 5.3
    return total / norm


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def catmull(points, samples=6):
    """Catmull-Rom smoothing of a 2D poly-line."""
    out = []
    n = len(points)
    for i in range(n - 1):
        p0, p1 = points[max(i - 1, 0)], points[i]
        p2, p3 = points[i + 1], points[min(i + 2, n - 1)]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(tuple(points[-1]))
    return out


class Polyline:
    """A smoothed 2D poly-line with a fast distance query."""

    def __init__(self, points, width=3.0, samples=6):
        self.pts = catmull(points, samples)
        self.width = width
        xs = [p[0] for p in self.pts]
        zs = [p[1] for p in self.pts]
        self.bbox = (min(xs), min(zs), max(xs), max(zs))

    def distance(self, x, z, reach=1e9):
        """(distance, t along the line 0..1). Returns (reach, 0) if clearly far."""
        x0, z0, x1, z1 = self.bbox
        if x < x0 - reach or x > x1 + reach or z < z0 - reach or z > z1 + reach:
            return reach, 0.0
        best, bt = 1e18, 0.0
        n = len(self.pts) - 1
        for i in range(n):
            ax, az = self.pts[i]
            bx, bz = self.pts[i + 1]
            dx, dz = bx - ax, bz - az
            ll = dx * dx + dz * dz
            t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / ll))
            px, pz = ax + dx * t - x, az + dz * t - z
            d = px * px + pz * pz
            if d < best:
                best, bt = d, (i + t) / n
        return math.sqrt(best), bt

    def point(self, t):
        f = t * (len(self.pts) - 1)
        i = min(int(f), len(self.pts) - 2)
        k = f - i
        (ax, az), (bx, bz) = self.pts[i], self.pts[i + 1]
        return ax + (bx - ax) * k, az + (bz - az) * k

    def tangent(self, t):
        f = t * (len(self.pts) - 1)
        i = min(int(f), len(self.pts) - 2)
        (ax, az), (bx, bz) = self.pts[i], self.pts[i + 1]
        ln = math.hypot(bx - ax, bz - az) or 1.0
        return (bx - ax) / ln, (bz - az) / ln


def yaw_facing(x, z, tx, tz):
    """Yaw (degrees) that turns a +Z-facing asset at (x, z) toward (tx, tz)."""
    return math.degrees(math.atan2(tx - x, tz - z))


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------
PLAY_X, PLAY_Z = 86.0, 94.0          # walkable half extents before the valley walls rise
SPAN = 128.0                         # terrain half size

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
}
STREAM = Polyline([(-122, -10), (-96, -8), (-75, -4), (-55, 4), (-35, 2), (-18, 8), (-2, 6), (8, 4),
                   (22, 0), (38, -6), (55, -2), (72, 6), (96, 10), (122, 14)], 6.0)

# flattened places: name -> (x, z, radius)
ZONES = {
    "spawn": (0.5, 76, 8), "teleport": (-7.5, 81, 6), "forest_path": (-6, 44, 6), "herb_grove": (-50, 31, 9),
    "spring": (-38, 62, 8), "hermit": (58, 31, 9), "clearing": (12, -28, 15), "ruins_gate": (-40, -38, 7),
    "ruins_inner": (-42, -61, 17), "camp": (50, -46, 13),
}
LOOKOUT = (74, -24)                  # rocky rise: flat top, walkable flanks
WOLF_DEN = (70, 66)                  # hollow before the cave mouth
POOL = (-44, 69, 6.5)                # spirit spring pool (x, z, radius)


def stream_level(x):
    """Water surface height of the stream (flows east)."""
    return 0.9 - 1.6 * (x + 128.0) / 256.0


def _low(x, z):
    return 2.8 * fbm2(x * 0.016, z * 0.016, 3, 11)


def boundary(x, z):
    """Distance past the walkable area (0 inside)."""
    e = 6.0 * fbm2(x * 0.03, z * 0.03, 2, 31)
    ox = abs(x) - PLAY_X + e
    oz = abs(z) - PLAY_Z + e
    return math.hypot(max(ox, 0.0), max(oz, 0.0))


def height(x, z):
    """Ground height at Godot (x, z)."""
    low = _low(x, z)
    detail = 0.7 * fbm2(x * 0.07, z * 0.07, 2, 12)
    h = low + detail
    # paths: smooth out the small bumps and sink a little
    dp = min(p.distance(x, z, 6.0)[0] for p in PATHS.values())
    w = smoothstep(5.0, 1.2, dp)
    h -= (detail + 0.12) * w
    for (cx, cz, r) in ZONES.values():
        d = math.hypot(x - cx, z - cz)
        if d < r + 8:
            h = lerp(h, _low(cx, cz), smoothstep(r + 8, r, d))
    # the rocky lookout rise and the wolves' hollow
    d = math.hypot(x - LOOKOUT[0], z - LOOKOUT[1])
    if d < 20:
        top = _low(*LOOKOUT) + 6.0
        h = lerp(h, top, smoothstep(19, 5.5, d))
    d = math.hypot(x - WOLF_DEN[0], z - WOLF_DEN[1])
    if d < 18:
        h = lerp(h, _low(*WOLF_DEN) - 2.4, smoothstep(17, 8, d))
    # spirit spring pool
    d = math.hypot(x - POOL[0], z - POOL[1])
    if d < POOL[2] + 4:
        h = lerp(h, _low(POOL[0], POOL[1]) - 1.3, smoothstep(POOL[2] + 1.5, POOL[2] - 2.5, d))
    # stream: level banks, then the bed
    ds, _ = STREAM.distance(x, z, 16.0)
    if ds < 16:
        lvl = stream_level(x)
        h = lerp(h, lvl + 0.9, smoothstep(16, 7, ds))
        h = lerp(h, lvl - 0.55, smoothstep(5.5, 1.8, ds))
    # valley walls
    out = boundary(x, z)
    if out > 0:
        crag = abs(fbm2(x * 0.045, z * 0.045, 4, 41)) * 9.0 + 2.5 * fbm2(x * 0.12, z * 0.12, 2, 42)
        h += 30.0 * (1 - math.exp(-out / 8.0)) + out * 0.55 + crag * min(1.0, out / 6)
    return h


def pool_level():
    return _low(POOL[0], POOL[1]) - 0.45


# --------------------------------------------------------------------------
# map
# --------------------------------------------------------------------------
def _clear_of(x, z, spots, pad):
    return all(math.hypot(x - sx, z - sz) > r + pad for (sx, sz, r) in spots)


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
    for k in range(26):
        t = 0.08 + 0.84 * k / 25 + rnd.uniform(-0.01, 0.01)
        px, pz = STREAM.point(t)
        if math.hypot(px - bx, pz - bz) < 9 or abs(px) > 96:
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
    add("lotus_cluster", px_ - 1.5, pz_ + 1, 30, 0.8, y=pool_level() + 0.02)
    add("lotus_cluster", px_ + 2.0, pz_ - 1.5, 200, 0.6, y=pool_level() + 0.02)
    for k in range(9):
        a = k * 0.7 + 1.2
        add("boulders", px_ + math.cos(a) * (pr_ + 1.2), pz_ + math.sin(a) * (pr_ + 1.2), k * 40, 0.45, dy=-0.25)
    add("spirit_stone", px_ - 5.5, pz_ - 4.0, 20, 1.2)
    add("spirit_stone", px_ + 6.0, pz_ + 2.5, 140, 0.9)

    # distant karst pillars above the valley walls
    for k in range(11):
        a = math.radians(k * 360 / 11 + rnd.uniform(-10, 10))
        r = rnd.uniform(190, 250)
        add("karst_peak", math.cos(a) * r, math.sin(a) * r, rnd.uniform(0, 360), rnd.uniform(1.1, 1.6),
            y=rnd.uniform(-30, -10))
    # --- vegetation ---------------------------------------------------------------------------
    keep_clear = [(x, z, r + 2.5) for (x, z, r) in ZONES.values()]
    keep_clear += [(LOOKOUT[0], LOOKOUT[1], 14), (WOLF_DEN[0], WOLF_DEN[1], 12), (POOL[0], POOL[1], POOL[2] + 4),
                   (-42, -65, 26), (-40, -46, 8), (bx, bz, 10), (wx + 9.5, wz + 8.5, 9)]
    placed = [(x, z) for (_, _, (x, _, z), _, _) in items[1:]]
    tries = 0
    count = 0
    while count < 470 and tries < 40000:
        tries += 1
        x, z = rnd.uniform(-118, 118), rnd.uniform(-122, 122)
        out = boundary(x, z)
        if out > 34:
            continue
        dp = min(p.distance(x, z, 8.0)[0] for p in PATHS.values())
        ds, _ = STREAM.distance(x, z, 10.0)
        if dp < 6.5 or ds < 7.5:
            continue
        if not _clear_of(x, z, keep_clear, 3.0):
            continue
        if any(math.hypot(x - a, z - b) < 5.0 for (a, b) in placed):
            continue
        r = rnd.random()
        yaw = rnd.uniform(0, 360)
        if out > 2 and r < 0.35:
            add("pine_tree_tall" if rnd.random() < 0.5 else "pine_tree", x, z, yaw, rnd.uniform(1.0, 1.4), dy=-0.3)
        elif r < 0.78:
            add("bamboo_grove", x, z, yaw, rnd.uniform(0.85, 1.2), dy=-0.1)
        elif r < 0.88:
            add("bamboo_cluster", x, z, yaw, rnd.uniform(0.9, 1.2), dy=-0.1)
        elif r < 0.95 and out == 0:
            add("fern_cluster", x, z, yaw, rnd.uniform(0.8, 1.3), dy=-0.05)
        else:
            add("boulders", x, z, yaw, rnd.uniform(0.6, 1.5), dy=-0.3)
        placed.append((x, z))
        count += 1
    # ferns softening the path edges
    for name, p in PATHS.items():
        for k in range(0, len(p.pts), 3):
            x, z = p.pts[k]
            nx, nz = p.tangent(k / (len(p.pts) - 1))
            side = rnd.choice((-1, 1))
            fx, fz = x - nz * side * rnd.uniform(3.2, 4.5), z + nx * side * rnd.uniform(3.2, 4.5)
            if boundary(fx, fz) > 0 or not _clear_of(fx, fz, keep_clear, 0.0):
                continue
            if STREAM.distance(fx, fz, 8.0)[0] < 7:
                continue
            add("fern_cluster", fx, fz, rnd.uniform(0, 360), rnd.uniform(0.6, 1.0), dy=-0.05)

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
    env = common.Env(
        sky=common.Sky(top=(0.42, 0.58, 0.66), horizon=(0.82, 0.88, 0.8), ground_bottom=(0.36, 0.4, 0.32),
                       ground_horizon=(0.74, 0.8, 0.72), curve=0.1, sun_angle_max=25.0),
        ambient_energy=1.15, exposure=1.18, fog_color=(0.7, 0.8, 0.72), fog_density=0.0024,
        fog_height=-3.0, fog_height_density=0.035, fog_sun_scatter=0.35, fog_sky_affect=0.3,
        glow_intensity=0.7, saturation=1.05, contrast=1.04, sun_pitch=-52.0, sun_yaw=-25.0,
        sun_color=(1.0, 0.96, 0.86), sun_energy=1.8, shadow_distance=110.0,
    )
    return common.MapDef("bamboo_forest", "Whispering Bamboo Forest", "forest", items, markers, env=env,
                         ambient="fireflies", kill_y=-30.0)

"""Celestial Sky Isles: floating islands above an endless sea of clouds.

Walkable isles (sky_platform_large / _small, top surface at the isle's y) are
chained by level jade bridges and floating stairs (sky_steps: +10 m,
ascension_stair: +26 m). Bridge ends sit 0.85 r inside each isle; a stair
starts 0.85 r inside the lower isle and its top landing rests on the upper one
from 1.1 r out, so no lip is left where they meet.

Route (Godot coordinates, -Z = north): Arrival isle (PlayerSpawn,
TeleportArray, CloudGate) -> long jade bridge with a belvedere (JadeBridge) ->
IsleOfWinds -> east steps up to the StarPavilion / west bridge to the
CelestialRuins -> steps down to the SpiritVein and up to the ImmortalGarden ->
bridge to the SerpentLair -> bridge to the foot of the AscensionStair -> the
stair up to TribulationPeak.
"""
import math
import random

from . import common

LARGE, SMALL = 20.0, 9.0          # nominal isle radii of sky_platform_large / _small
BRIDGE, BRIDGE_LONG = 30.0, 60.0
BELVEDERE_RISE = 1.5
STEPS = (10.0, 22.0)              # sky_steps (rise, run)
ASCENT = (26.0, 56.0)             # ascension_stair (rise, run)


class Isle:
    def __init__(self, name, asset, radius, scale, pos):
        self.name, self.asset, self.scale = name, asset, scale
        self.r = radius * scale
        self.x, self.y, self.z = pos

    def at(self, dx=0.0, dz=0.0):
        return (self.x + dx, self.y, self.z + dz)


def _unit(dx, dz):
    n = math.hypot(dx, dz)
    return dx / n, dz / n


def _yaw(dx, dz):
    """Yaw (common.xform, where Godot rotation.y = -yaw) that turns a model's local -Z
    (Blender +Y: the direction a bridge runs and a stair climbs) toward (dx, dz)."""
    return math.degrees(math.atan2(dx, -dz))


def _face(dx, dz):
    """Yaw that turns a model's front (local +Z, Blender -Y) toward (dx, dz)."""
    return math.degrees(math.atan2(-dx, dz))


def build():
    rnd = random.Random(21)
    items = []

    def add(asset, pos, yaw=0.0, scale=1.0, name=None):
        items.append((asset, name, tuple(pos), yaw, scale))

    isles = {}

    def isle(name, asset, radius, scale, pos):
        isles[name] = Isle(name, asset, radius, scale, pos)
        return isles[name]

    def bridge_to(a, direction, name, length=BRIDGE, scale=1.0, radius=LARGE, asset_scale=1.0, dy=0.0):
        """Place a level bridge from isle a toward direction and the isle at its far end."""
        ux, uz = _unit(*direction)
        r_b = radius * scale
        ea, eb = 0.85 * a.r, 0.85 * r_b
        c = (a.x + ux * (ea + length / 2), a.y, a.z + uz * (ea + length / 2))
        add("jade_bridge_long" if length > 40 else "jade_bridge", c, _yaw(ux, uz))
        d = ea + length + eb
        return isle(name, "sky_platform_large" if radius == LARGE else "sky_platform_small", radius, scale,
                    (a.x + ux * d, a.y + dy, a.z + uz * d)), c

    def stair_to(lower, direction, name, radius, scale, big=False):
        """Stairs up from isle lower toward direction; returns the upper isle."""
        rise, run = ASCENT if big else STEPS
        ux, uz = _unit(*direction)
        r_up = radius * scale
        e0 = 0.85 * lower.r
        start = (lower.x + ux * e0, lower.y, lower.z + uz * e0)
        add("ascension_stair" if big else "sky_steps", start, _yaw(ux, uz), name="AscensionStair" if big else None)
        d = e0 + run + 1.1 * r_up
        return isle(name, "sky_platform_large" if radius == LARGE else "sky_platform_small", radius, scale,
                    (lower.x + ux * d, lower.y + rise, lower.z + uz * d))

    def stair_from(upper, direction, name, radius, scale):
        """Stairs down from isle upper toward direction; returns the lower isle."""
        rise, run = STEPS
        ux, uz = _unit(*direction)
        r_low = radius * scale
        d = 1.1 * upper.r + run + 0.85 * r_low
        low = isle(name, "sky_platform_large" if radius == LARGE else "sky_platform_small", radius, scale,
                   (upper.x + ux * d, upper.y - rise, upper.z + uz * d))
        e0 = 0.85 * low.r
        start = (low.x - ux * e0, low.y, low.z - uz * e0)
        add("sky_steps", start, _yaw(-ux, -uz))
        return low

    arrival = isle("Arrival", "sky_platform_large", LARGE, 1.0, (0.0, 0.0, 60.0))
    winds, belv = bridge_to(arrival, (0, -1), "IsleOfWinds", BRIDGE_LONG)
    stars = stair_to(winds, (1, 0), "StarIsle", SMALL, 1.5)
    ruins, _ = bridge_to(winds, (-1, 0), "RuinsIsle")
    vein = stair_from(ruins, (-0.6, 0.8), "VeinIsle", SMALL, 1.35)
    garden = stair_to(ruins, (0, -1), "GardenIsle", LARGE, 1.0)
    lair, _ = bridge_to(garden, (1, 0), "LairIsle", scale=1.3)
    foot, _ = bridge_to(lair, (0.6, -0.8), "StairFoot", radius=SMALL, scale=1.35)
    peak = stair_to(foot, (0.8, -0.6), "PeakIsle", LARGE, 1.1, big=True)

    for i in isles.values():
        add(i.asset, (i.x, i.y, i.z), rnd.uniform(0, 360), i.scale, name=i.name)

    def g(i, dx, dz, dy=-0.05):
        return (i.x + dx, i.y + dy, i.z + dz)

    # --- arrival isle: teleport array, lantern-lined path to the cloud gate --
    tp = (-7.0, 8.0)
    spawn = (2.0, 5.0)
    add("teleport_array", g(arrival, *tp, dy=0.0), name="TeleportArray")
    add("cloud_gate", g(arrival, 0.0, -13.5), 0.0, name="CloudGate")
    for dz in (-3.0, 3.0):
        for sx in (-1, 1):
            add("stone_lantern", g(arrival, sx * 6.5, dz - 4.0))
    for dx, dz in ((-14.0, 2.0), (-12.0, -8.0), (13.0, 9.0)):
        add("plum_blossom_tree", g(arrival, dx, dz), rnd.uniform(0, 360), rnd.uniform(0.9, 1.1))
    add("pine_tree", g(arrival, 15.0, -8.0), rnd.uniform(0, 360))
    add("incense_burner", g(arrival, 10.0, -3.0))
    # --- the long bridge's belvedere ------------------------------------------
    # --- isle of winds: wind-bent pines around the rim --------------------------
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.35
        if abs(math.cos(a)) > 0.93 or abs(math.sin(a)) > 0.93:
            continue  # keep the bridge and stair heads clear
        r = rnd.uniform(13.5, 16.5)
        add("pine_tree_tall" if k % 2 else "pine_tree", g(winds, math.cos(a) * r, math.sin(a) * r),
            rnd.uniform(0, 360), rnd.uniform(0.9, 1.25))
    add("boulders", g(winds, -6.0, 12.0), 40.0, 1.2)
    add("scholar_rock", g(winds, 9.0, -11.0), 200.0)
    # --- star isle: pavilion, lanterns ------------------------------------------
    add("star_pavilion", g(stars, 0.0, -4.5), _face(0, 1), name="StarPavilion")
    for sx in (-1, 1):
        add("stone_lantern", g(stars, sx * 5.5, 2.0))
    add("plum_blossom_tree", g(stars, -8.5, 7.0), 30.0, 0.9)
    # --- ruins isle ----------------------------------------------------------
    add("celestial_ruins", g(ruins, 0.0, 0.0, 0.0), 0.0, name="CelestialRuins")
    add("pine_tree", g(ruins, -15.0, 9.0), 70.0)
    # --- spirit vein ---------------------------------------------------------
    ux, uz = _unit(-0.6, 0.8)
    for k, (off, s) in enumerate(((0.0, 1.3), (1.0, 1.0), (-1.0, 0.8))):
        ang = math.atan2(uz, ux) + off * 0.6
        add("crystal_cluster", g(vein, math.cos(ang) * 7.5, math.sin(ang) * 7.5), rnd.uniform(0, 360), s)
    add("boulders", g(vein, -math.cos(math.atan2(uz, ux) + 1.8) * 8.5, -math.sin(math.atan2(uz, ux) + 1.8) * 8.5),
        10.0, 0.8)
    # --- immortal garden -----------------------------------------------------
    for k in range(8):
        a = 2 * math.pi * k / 8 + 0.2
        if abs(math.sin(a)) > 0.9 or math.cos(a) > 0.9:
            continue
        r = rnd.uniform(9.5, 14.0)
        add("plum_blossom_tree", g(garden, math.cos(a) * r, math.sin(a) * r), rnd.uniform(0, 360),
            rnd.uniform(1.0, 1.3))
    add("pavilion", g(garden, -12.0, -9.0), 130.0)
    add("scholar_rock", g(garden, 6.0, 12.0), 20.0)
    for dx, dz in ((-5.0, 6.0), (5.0, -6.0)):
        add("stone_lantern", g(garden, dx, dz))
    # --- serpent lair: an open arena ringed by crystals and broken stones ---------
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.5
        add("crystal_cluster" if k % 2 else "boulders", g(lair, math.cos(a) * 21.0, math.sin(a) * 21.0),
            rnd.uniform(0, 360), rnd.uniform(0.9, 1.3))
    # --- stair foot ------------------------------------------------------------
    ux, uz = _unit(0.8, -0.6)
    for sx in (-1, 1):
        add("stone_lantern", g(foot, ux * 6.5 - uz * sx * 3.8, uz * 6.5 + ux * sx * 3.8))
    add("incense_burner", g(foot, -ux * 8.0, -uz * 8.0))
    # --- tribulation peak --------------------------------------------------------
    add("tribulation_altar", g(peak, 0.0, 0.0, 0.0), 0.0, name="TribulationAltar")
    # --- the sky ---------------------------------------------------------------
    add("cloud_sea", (0.0, -55.0, -60.0), 0.0, name="CloudSea")
    for pos, sc, yaw in (((-170, 5, 60), 1.2, 30), ((150, -8, 30), 1.4, 120), ((-40, 20, -250), 1.6, 200),
                         ((190, 40, -110), 1.1, 300), ((-160, 30, -170), 1.3, 80), ((60, -15, 150), 1.0, 10),
                         ((-60, 50, 150), 0.9, 250), ((230, 60, -260), 1.8, 150)):
        add("floating_island", pos, yaw, sc)
    for pos, sc in (((-320, -70, -150), 1.5), ((330, -60, -280), 1.8), ((-300, -80, 180), 1.4),
                    ((250, -70, 230), 1.3), ((40, -90, -430), 2.0), ((380, -70, 20), 1.6),
                    ((-150, -90, 330), 1.7), ((-420, -60, -30), 1.2), ((150, -80, -470), 1.5)):
        add("karst_peak", pos, rnd.uniform(0, 360), sc)

    def top(i, dx=0.0, dz=0.0, h=1.0):
        return (i.x + dx, i.y + h, i.z + dz)

    markers = {
        "PlayerSpawn": top(arrival, *spawn),
        "TeleportArray": top(arrival, *tp, h=0.9),
        "CloudGate": top(arrival, 0.0, -7.0),
        "JadeBridge": (belv[0], belv[1] + BELVEDERE_RISE + 1.0, belv[2]),
        "IsleOfWinds": top(winds),
        "StarPavilion": top(stars, 0.0, 7.5),
        "CelestialRuins": top(ruins, h=1.5),
        "SerpentLair": top(lair),
        "SpiritVein": top(vein),
        "ImmortalGarden": top(garden),
        "TribulationPeak": top(peak, h=1.75),
        "AscensionStair": top(foot),
    }
    env = common.Env(
        sky=common.Sky(top=(0.26, 0.5, 0.88), horizon=(0.98, 0.9, 0.72), ground_bottom=(0.82, 0.86, 0.94),
                       ground_horizon=(0.97, 0.92, 0.8), curve=0.1, sun_angle_max=20.0),
        ambient_energy=1.15, exposure=1.08,
        fog_color=(0.96, 0.92, 0.84), fog_density=0.0005, fog_height=-38.0, fog_height_density=0.02,
        fog_sun_scatter=0.35, fog_sky_affect=0.1, glow_intensity=0.7, saturation=1.1, contrast=1.04,
        sun_pitch=-58.0, sun_yaw=-25.0, sun_color=(1.0, 0.95, 0.84), sun_energy=1.9, shadow_distance=180.0,
    )
    new = expand(isles, add, markers)
    # background islets and pillars that the new isles would collide with drift farther out
    kept = []
    for it in items:
        if it[0] in ("floating_island", "karst_peak") and any(
                math.hypot(it[2][0] - i.x, it[2][2] - i.z) < i.r + 45 for i in new.values()):
            x, y, z = it[2]
            d = math.hypot(x, z) or 1.0
            it = (it[0], it[1], (x / d * (d + 260), y - 20, z / d * (d + 260)), it[3], it[4])
        kept.append(it)
    items[:] = kept
    lowest = min(i.y for i in list(isles.values()) + list(new.values()))
    return common.MapDef("sky_isles", "Celestial Sky Isles", "sky", items, markers, env=env, ambient="motes",
                         kill_y=lowest - 30.0)


# --------------------------------------------------------------------------
# the expanded sky isles
# --------------------------------------------------------------------------
HUGE, MID, PALACE = 38.0, 28.0, 46.0
RAINBOW, CHAIN = 44.0, 48.0
STONE_GAP = 18.0


def expand(old, add, markers):
    """Thirty new isles grown from the first ones by bridges, stairs and stepping stones, with their
    landmarks and markers (updates `markers`). Returns the new isles by name."""
    from .layout import FOOT, check_markers, footprint
    rnd = random.Random(99)
    isles = {}
    solids = []
    stones = []

    def isle(name, asset, radius, scale, pos):
        isles[name] = Isle(name, asset, radius, scale, pos)
        return isles[name]

    def link(a, direction, kind, name, asset, radius, scale=1.0):
        ux, uz = _unit(*direction)
        rb = radius * scale
        if kind in ("bridge30", "bridge60", "rainbow", "chain"):
            length = {"bridge30": BRIDGE, "bridge60": BRIDGE_LONG, "rainbow": RAINBOW, "chain": CHAIN}[kind]
            ea, eb = 0.85 * a.r, 0.85 * rb
            if kind == "chain":
                ea, eb = 0.8 * a.r, 0.8 * rb
            c = (a.x + ux * (ea + length / 2), a.y, a.z + uz * (ea + length / 2))
            conn = {"bridge30": "jade_bridge", "bridge60": "jade_bridge_long", "rainbow": "rainbow_bridge",
                    "chain": "chain_bridge"}[kind]
            add(conn, c, _yaw(ux, uz), name=name + "Bridge" if kind != "rainbow" else "RainbowBridgeSpan")
            b = isle(name, asset, radius, scale, (a.x + ux * (ea + length + eb), a.y, a.z + uz * (ea + length + eb)))
            b.link = c
            return b
        if kind in ("up", "ascend"):
            rise, run = ASCENT if kind == "ascend" else STEPS
            e0 = 0.85 * a.r
            add("ascension_stair" if kind == "ascend" else "sky_steps", (a.x + ux * e0, a.y, a.z + uz * e0),
                _yaw(ux, uz), name=name + "Stair")
            d = e0 + run + 1.1 * rb
            return isle(name, asset, radius, scale, (a.x + ux * d, a.y + rise, a.z + uz * d))
        if kind == "down":
            rise, run = STEPS
            d = 1.1 * a.r + run + 0.85 * rb
            b = isle(name, asset, radius, scale, (a.x + ux * d, a.y - rise, a.z + uz * d))
            e0 = 0.85 * b.r
            add("sky_steps", (b.x - ux * e0, b.y, b.z - uz * e0), _yaw(-ux, -uz), name=name + "Stair")
            return b
        if kind == "stones":
            start = 0.93 * a.r
            k = 0
            while True:
                t = start + 1.9 + k * 4.4
                if t > start + STONE_GAP - 1.9:
                    break
                p = (a.x + ux * t, a.y, a.z + uz * t)
                add("stepping_stone", p, rnd.uniform(0, 360), name=f"{name}Stone{k + 1}")
                stones.append(p)
                k += 1
            d = start + STONE_GAP + 0.93 * rb
            return isle(name, asset, radius, scale, (a.x + ux * d, a.y, a.z + uz * d))
        raise ValueError(kind)

    arrival, vein, garden, lair, peak = old["Arrival"], old["VeinIsle"], old["GardenIsle"], old["LairIsle"], old["PeakIsle"]
    harbour = link(arrival, (1, 0), "bridge60", "CloudHarbourIsle", "sky_platform_huge", HUGE)
    lantern = link(arrival, (0, 1), "rainbow", "LanternIsle", "sky_platform_mid", MID)
    wreck = link(harbour, (0, 1), "stones", "WreckIsle", "sky_platform_mid", MID)
    crane = link(harbour, (1, 0), "bridge30", "CraneIsle", "sky_platform_huge", HUGE)
    thunder = link(crane, (0, -1), "up", "ThunderIsle", "sky_platform_mid", MID)
    storm = link(thunder, (0, -1), "ascend", "StormIsle", "sky_platform_huge", HUGE)
    sword = link(crane, (1, 0), "bridge60", "SwordIsle", "sky_platform_mid", MID)
    peach = link(lantern, (-1, 0), "bridge30", "PeachIsle", "sky_platform_huge", HUGE)
    dragon = link(lantern, (0, 1), "bridge60", "DragonIsle", "sky_platform_huge", HUGE)
    terraces = link(peach, (0, 1), "down", "TerraceIsle", "sky_platform_terraces", HUGE)
    hermit = link(peach, (-1, 0), "stones", "HermitIsle", "sky_platform_small", SMALL)
    moon = link(terraces, (-1, 0), "bridge30", "MoonIsle", "sky_platform_moon", HUGE)
    forest = link(dragon, (1, 0), "bridge60", "ForestIsle", "sky_platform_huge", HUGE)
    tree = link(forest, (1, 0), "bridge30", "TreeIsle", "sky_platform_huge", HUGE, 1.2)
    crystal = link(vein, (-1, 0), "bridge30", "CrystalIsle", "sky_platform_crystal", MID)
    chain1 = link(crystal, (-1, 0), "stones", "ChainIsle1", "sky_platform_small", SMALL, 1.3)
    chain2 = link(chain1, (-1, 0), "stones", "ChainIsle2", "sky_platform_small", SMALL, 1.3)
    chain3 = link(chain2, (-1, 0), "stones", "ChainIsle3", "sky_platform_small", SMALL, 1.3)
    falls = link(chain2, (0, 1), "stones", "WaterfallIsle", "sky_platform_mid", MID)
    elixir = link(garden, (-1, 0), "bridge30", "ElixirIsle", "sky_platform_mid", MID)
    phoenix = link(elixir, (-1, 0), "up", "PhoenixIsle", "sky_platform_burnt", MID)
    mirror = link(elixir, (0, -1), "bridge30", "MirrorIsle", "sky_platform_mid", MID)
    lotus = link(mirror, (0, -1), "up", "LotusIsle", "sky_platform_huge", HUGE)
    winds = link(lair, (-0.5, -1), "up", "WindTempleIsle", "sky_platform_huge", HUGE)
    palace = link(peak, (0, -1), "bridge60", "PalaceIsle", "sky_platform_palace", PALACE)
    observatory = link(palace, (-1, 0), "bridge30", "ObservatoryIsle", "sky_platform_mid", MID)
    records = link(palace, (1, 0), "bridge30", "RecordsIsle", "sky_platform_mid", MID)
    heaven = link(palace, (0, -1), "ascend", "HeavenGateIsle", "sky_platform_huge", HUGE)
    seal = link(heaven, (-1, 0), "bridge30", "SealIsle", "sky_platform_mid", MID)
    sun = link(heaven, (1, 0), "chain", "SunIsle", "sky_platform_mid", MID)

    # no two isles may touch
    every = list(old.values()) + list(isles.values())
    for i, a in enumerate(every):
        for b in every[i + 1:]:
            if math.hypot(a.x - b.x, a.z - b.z) < a.r + b.r + 4 and abs(a.y - b.y) < 12:
                raise SystemExit(f"sky_isles: isles {a.name} and {b.name} overlap")
    for i in isles.values():
        add(i.asset, (i.x, i.y, i.z), rnd.uniform(0, 360), i.scale, name=i.name)

    def g(i, dx, dz, dy=-0.05):
        return (i.x + dx, i.y + dy, i.z + dz)

    def site(asset, i, dx, dz, yaw=0.0, name=None, scale=1.0, dy=0.0):
        add(asset, g(i, dx, dz, dy), yaw, scale, name=name)
        if asset in FOOT:
            solids.append((asset, name, footprint(asset, i.x + dx, i.z + dz, yaw, 0.3)))

    # --- the immortal palace, its court, the hall of records, the observatory, the gate of heaven
    site("immortal_palace_gate", palace, 0, 17, 0, "ImmortalPalaceGate")
    site("jade_palace_hall", palace, 0, -21, 0, "JadePalaceHall")
    for dx in (-10, 10):
        site("stone_lantern", palace, dx, 3)
        site("stone_lantern", palace, dx, -4)
    site("incense_burner", palace, 0, 0, 0, "PalaceIncense")
    for k in range(6):
        a = math.radians(-30 - k * 24)
        site("peach_tree", palace, math.cos(a) * 36, math.sin(a) * 36 + 4, rnd.uniform(0, 360))
    site("hall_of_records", records, 0, -8, 0, "HallOfRecordsBuilding")
    site("observatory", observatory, 0, -5, 0, "ObservatorySpire")
    site("gate_of_heaven", heaven, 0, -8, 0, "GateOfHeavenArch")
    for dx in (-16, 16):
        site("thunder_rods", heaven, dx, -16, 0, scale=0.5)
    site("seal_of_heaven", seal, 0, -2, 0, "SealOfHeavenDisc")
    site("sun_altar", sun, 0, -4, 0, "SunAltarDais")
    # --- harbour and wreck, cranes, thunder, storm, swords
    for (dx, dz, yaw) in ((0, HUGE * 0.9, 0), (HUGE * 0.9, 12, -90)):
        site("cloud_pier", harbour, dx, dz, yaw, "CloudPier")
    site("sky_lanterns", harbour, 0, 0, 0, None, 1.0, 4.0)
    site("sky_ship_wreck", wreck, 4, 0, 20, "SkyShipWreckHull")
    for k in range(7):
        a = 2 * math.pi * k / 7 + 0.3
        site("pine_tree_tall" if k % 2 else "pine_tree", crane, math.cos(a) * 28, math.sin(a) * 28, rnd.uniform(0, 360),
             scale=rnd.uniform(1.0, 1.3))
        site("crane_statue", crane, math.cos(a + 0.4) * 14, math.sin(a + 0.4) * 14, rnd.uniform(0, 360))
    site("thunder_rods", thunder, 0, -9, 0, "ThunderRods")
    for k in range(8):
        a = 2 * math.pi * k / 8
        site("boulders" if k % 2 else "pine_tree", storm, math.cos(a) * 30, math.sin(a) * 30, rnd.uniform(0, 360),
             scale=rnd.uniform(0.9, 1.3))
    site("sword_spire", sword, 0, -4, 0, "SwordSpire")
    # --- lanterns, peaches, dragon, terraces, hermit, moon, forest, the tree of ages
    for k in range(3):
        site("sky_lanterns", lantern, rnd.uniform(-12, 12), rnd.uniform(-12, 12), 0, None, 1.0, 2.0)
    for (dx, dz) in ((-8, -6), (8, -6), (-8, 8), (8, 8)):
        site("stone_lantern", lantern, dx, dz)
    for k in range(14):
        a = 2 * math.pi * k / 14
        rr = 26 if k % 2 else 16
        site("peach_tree", peach, math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(0, 360), scale=rnd.uniform(0.9, 1.2))
    site("dragon_bones", dragon, -6, 0, 10, "DragonSkeleton")
    for k in range(10):
        site("spirit_herb", terraces, rnd.uniform(-24, 24), rnd.uniform(-24, 24), rnd.uniform(0, 360))
    for (dx, dz) in ((-20, 12), (22, -14)):
        site("rustic_hut", terraces, dx, dz, rnd.uniform(0, 360), None, 0.9)
    site("rustic_hut", hermit, 0, -3, 180, "HermitHutSky", 0.9)
    for k in range(6):
        a = 2 * math.pi * k / 6
        site("crystal_cluster", moon, math.cos(a) * 24, math.sin(a) * 24, rnd.uniform(0, 360), scale=1.2)
    for k in range(22):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(10, 33)
        site("pine_tree_tall" if k % 3 else "pine_tree", forest, math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(0, 360),
             scale=rnd.uniform(0.9, 1.3))
    for k in range(5):
        a = 2 * math.pi * k / 5
        add("floating_island", (forest.x + math.cos(a) * 20, forest.y + 14 + 3 * k, forest.z + math.sin(a) * 20),
            rnd.uniform(0, 360), 0.18)
    site("tree_of_ages", tree, 0, -6, 0, "TreeOfAgesTrunk")
    # --- crystals, chain isles, falls, elixir, phoenix, mirror, lotus, the wind temple
    for k in range(8):
        a = 2 * math.pi * k / 8
        site("crystal_cluster", crystal, math.cos(a) * 17, math.sin(a) * 17, rnd.uniform(0, 360), scale=rnd.uniform(1.0, 1.8))
    for i in (chain1, chain2, chain3):
        site("crystal_cluster", i, 3, -3, rnd.uniform(0, 360), scale=0.8)
    add("waterfall", (falls.x, falls.y - 24.0, falls.z + MID * 0.97), 0, (1.4, 1.0, 1.0), name="SkyFalls")
    site("elixir_spring", elixir, 0, -5, 0, "ElixirSpringBasin")
    site("phoenix_nest", phoenix, 0, -4, 0, "PhoenixNestTwigs")
    site("mirror_pool", mirror, 0, -6, 0, "MirrorLakePool")
    site("elixir_spring", lotus, 0, -8, 0, "LotusBasin", 2.1)
    for (dx, dz) in ((-4, -10), (3, -6), (5, -11), (-2, -5)):
        site("lotus_cluster", lotus, dx, dz, rnd.uniform(0, 360), None, 1.0, 0.9)
    site("wind_temple", winds, 0, -6, 0, "WindTempleHall")

    def top(i, dx=0.0, dz=0.0, h=1.0):
        return (i.x + dx, i.y + h, i.z + dz)

    new = {
        "CrystalIsle": top(crystal, 0, 6), "LotusLake": top(lotus, 0, 16), "WaterfallIsle": top(falls, 0, 6),
        "PhoenixNest": top(phoenix, 0, 10), "CraneIsle": top(crane), "MoonIsle": top(moon),
        "SunAltar": top(sun, 0, 11), "ThunderIsle": top(thunder, 0, 6),
        "RainbowBridge": (lantern.link[0], lantern.link[1] + 1.0, lantern.link[2]),
        "ChainIsles": top(chain2, -2, 2), "ImmortalPalace": top(palace, 0, 32), "PalaceCourt": top(palace, 0, 4),
        "HallOfRecords": top(records, 0, 12), "StarObservatory": top(observatory, 0, 11),
        "WindTemple": top(winds, 0, 16), "CloudHarbour": top(harbour, -8, 0), "SkyShipWreck": top(wreck, -12, 4),
        "DragonBones": top(dragon, 14, 0), "PeachGarden": top(peach), "JadeTerraces": top(terraces),
        "HermitIsle": top(hermit, 3, 4), "MirrorLake": top(mirror, 0, 9), "FloatingForest": top(forest, 0, 4),
        "SealOfHeaven": top(seal, 0, 15), "GateOfHeaven": top(heaven, 0, 4), "SwordIsle": top(sword, 0, 10),
        "ElixirSpring": top(elixir, 0, 7), "StormCloudPlateau": top(storm), "LanternIsle": top(lantern),
        "TreeOfAges": top(tree, 0, 16),
    }
    markers.update(new)

    def ground(x, z):
        best = -1000.0
        for i in every:
            if math.hypot(x - i.x, z - i.z) < 0.93 * i.r:
                best = max(best, i.y)
        for (sx, sy, sz) in stones:
            if math.hypot(x - sx, z - sz) < 2.2:
                best = max(best, sy)
        return best
    problems = check_markers("sky_isles", new, ground, solids, exempt=("RainbowBridge", "HermitIsle", "ChainIsles"))
    if problems:
        raise SystemExit("sky_isles marker problems:" + "".join("\n  " + p for p in problems))
    return isles

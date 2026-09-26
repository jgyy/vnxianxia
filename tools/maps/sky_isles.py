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
    lowest = min(i.y for i in isles.values())
    return common.MapDef("sky_isles", "Celestial Sky Isles", "sky", items, markers, env=env, ambient="motes",
                         kill_y=lowest - 30.0)

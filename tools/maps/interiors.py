"""Building interiors, entered through a door on one of the five exterior maps.

Each interior is a single small map: one instance of its own GLB (built by
blender/xianxia/interiors.py, same asset name as the map id) plus PlayerSpawn/
ExitDoor/TeleportArray markers and one feature marker for the room's centrepiece.
The door link (which exterior marker leads in, and where ExitDoor leads back
to) lives in godot/scripts/world/doors.gd, not here; this module only has to
agree with it on map ids and marker names.

Blender builds each room Z-up with the doorway centred on local -Y (so a
Blender point (x, y, z) lands, once exported Y-up, at Godot (x, z, -y) — see
blender/xianxia/arch.py's "buildings face -Y" note). The marker positions
below are that conversion applied to the coordinates used in interiors.py.
"""
from . import common

INTERIOR_ENV = common.Env(
    ambient_energy=1.55, exposure=1.12, fog_density=0.0, fog_height_density=0.0,
    glow_intensity=0.35, sun_energy=1.0, shadow_distance=40.0, saturation=1.05, contrast=1.03,
)


def _room(map_id, name, music, asset, half_depth, feature_name, feature_pos, ambient="none"):
    """A one-asset interior: the room's own GLB plus PlayerSpawn/ExitDoor/
    TeleportArray at the doorway and one feature marker inside."""
    door = (0.0, 1.0, half_depth - 0.15)
    spawn = (0.0, 1.0, half_depth - 1.05)
    items = [(asset, None, (0, 0, 0), 0.0, 1.0)]
    markers = {
        "PlayerSpawn": spawn,
        "ExitDoor": door,
        "TeleportArray": door,
        feature_name: feature_pos,
    }
    return common.MapDef(map_id, name, music, items, markers, env=INTERIOR_ENV, ambient=ambient, kill_y=-20.0)


def build_sect_main_hall():
    return _room("sect_main_hall", "Sect Main Hall", "sect", "sect_main_hall", 4.0,
                "ThroneDais", (0.0, 1.0, -2.2), ambient="motes")


def build_elder_quarters():
    return _room("elder_quarters", "Elder's Quarters", "sect", "elder_quarters", 2.5,
                "MeditationMat", (0.0, 0.9, -1.55), ambient="motes")


def build_scripture_pavilion():
    return _room("scripture_pavilion", "Scripture Pavilion", "sect", "scripture_pavilion", 3.5,
                "BookShelves", (0.0, 1.0, -2.6), ambient="motes")


def build_alchemy_pavilion():
    return _room("alchemy_pavilion", "Alchemy Pavilion", "sect", "alchemy_pavilion", 3.0,
                "PillFurnace", (0.0, 1.4, -1.6), ambient="embers")


def build_weapons_hall():
    return _room("weapons_hall", "Weapons Hall", "sect", "weapons_hall", 3.25,
                "ArmoryRacks", (0.0, 1.0, 0.0), ambient="none")


def build_disciple_dormitory():
    return _room("disciple_dormitory", "Disciple Dormitory", "sect", "disciple_dormitory", 3.0,
                "Dormitory", (0.0, 1.0, -2.2), ambient="none")


def build_qingshi_inn():
    return _room("qingshi_inn", "Drunken Crane Inn", "town", "qingshi_inn", 3.5,
                "BarCounter", (0.0, 1.0, -2.4), ambient="motes")


def build_qingshi_teahouse():
    return _room("qingshi_teahouse", "Teahouse", "town", "qingshi_teahouse", 3.0,
                "TeaCounter", (0.0, 1.0, -2.1), ambient="motes")


def build_qingshi_blacksmith():
    return _room("qingshi_blacksmith", "Blacksmith", "town", "qingshi_blacksmith", 2.75,
                "Forge", (0.0, 1.0, -2.2), ambient="embers")


def build_qingshi_herb_shop():
    return _room("qingshi_herb_shop", "Herb Shop", "town", "qingshi_herb_shop", 2.5,
                "HerbCounter", (0.0, 1.0, -1.9), ambient="motes")


def build_hidden_vault():
    return _room("hidden_vault", "Hidden Vault", "forest", "hidden_vault", 3.0,
                "VaultTreasure", (0.0, 1.0, -1.0), ambient="motes")


def build_celestial_pavilion():
    return _room("celestial_pavilion", "Celestial Sanctum", "sky", "celestial_pavilion", 3.25,
                "StarChart", (0.0, 1.0, 0.0), ambient="motes")


def build_blood_abyss_shrine():
    return _room("blood_abyss_shrine", "Ancient Shrine", "abyss", "blood_abyss_shrine", 3.5,
                "RelicAltar", (0.0, 1.2, -2.2), ambient="embers")


BUILDERS = {
    "sect_main_hall": build_sect_main_hall,
    "elder_quarters": build_elder_quarters,
    "scripture_pavilion": build_scripture_pavilion,
    "alchemy_pavilion": build_alchemy_pavilion,
    "weapons_hall": build_weapons_hall,
    "disciple_dormitory": build_disciple_dormitory,
    "qingshi_inn": build_qingshi_inn,
    "qingshi_teahouse": build_qingshi_teahouse,
    "qingshi_blacksmith": build_qingshi_blacksmith,
    "qingshi_herb_shop": build_qingshi_herb_shop,
    "hidden_vault": build_hidden_vault,
    "celestial_pavilion": build_celestial_pavilion,
    "blood_abyss_shrine": build_blood_abyss_shrine,
}

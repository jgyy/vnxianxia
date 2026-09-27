"""Placement helpers shared by the enlarged exterior maps.

FOOT gives every building asset's footprint in its own frame (Godot: x across, z toward the front;
(hw, back, front) = half width, depth behind and in front of the origin, stairs included). A map
declares its buildings as sites: each site levels a pad of ground under the footprint (so the building
never floats or sinks), and later the site's footprint is used to check that no marker stands inside a
building and that every marker has open, level ground around it.
"""
import math

from .terrain import Rect


def _hall(w, d, ph, v, margin=1.4):
    run = (math.ceil(ph / 0.17 - 1e-6) * 0.32 + 0.1) if ph > 0 else 0.0
    pw = w / 2 + margin
    pdd = d / 2 + margin + v / 2
    return (pw, pdd - v / 2, pdd + v / 2 + run)


FOOT = {
    # arch / lands / realms (the first maps)
    "main_hall": (10.0, 7.0, 9.5),
    "pagoda": (3.6, 3.6, 5.0),
    "pavilion": (3.2, 3.0, 4.2),
    "sect_gate": (5.0, 1.0, 1.0),
    "town_house": (4.5, 3.2, 3.6),
    "town_house_large": (6.0, 4.0, 4.4),
    "hermit_hut": (3.5, 3.5, 4.5),
    "teleport_array": (3.5, 3.5, 3.5),
    # buildings.py
    "outer_sect_hall": _hall(22, 13, 1.5, 2.2),
    "mission_hall": _hall(16, 10, 1.0, 2.0),
    "sect_refectory": _hall(26, 9, 0.6, 1.6),
    "contribution_pavilion": _hall(12, 9, 1.0, 1.6),
    "dormitory_row": _hall(18, 7, 0.5, 1.4),
    "sect_cottage": _hall(8, 6, 0.45, 1.2),
    "bell_tower": (5.4, 5.4, 5.4),
    "drum_tower": (5.4, 5.4, 5.4),
    "treasure_tower": (7.2, 7.2, 9.9),
    "formation_hall": (9.7, 9.7, 12.4),
    "inner_sect_gate": (6.8, 1.0, 1.0),
    "martial_stage": (12.8, 12.8, 12.8),
    "arena_stands": (12.2, 2.4, 4.9),
    "formation_pillar": (0.9, 0.9, 0.9),
    "pill_kiln": (3.1, 3.1, 3.1),
    "beast_pen": (6.2, 4.2, 4.2),
    "ancestral_tomb": (4.7, 4.7, 6.6),
    "stone_stairs_6": (2.9, 0.0, 0.0),       # special: along -z, see stairs()
    "stone_stairs_14": (3.9, 0.0, 0.0),
    # buildings_town.py
    "city_gate": (11.2, 6.2, 6.2),
    "city_wall": (4.0, 1.1, 1.1),
    "shophouse_a": _hall(8, 6.5, 0.34, 1.3, 0.6),
    "shophouse_b": _hall(9, 7.0, 0.34, 1.3, 0.6),
    "shophouse_c": _hall(10, 7.0, 0.34, 1.3, 0.6),
    "tavern": _hall(14, 9, 0.45, 1.6),
    "pharmacy": _hall(13, 9, 0.6, 1.6),
    "pawnshop": _hall(8, 8, 0.9, 0.0),
    "granary": _hall(16, 10, 1.6, 0.0),
    "silk_workshop": _hall(14, 9, 0.3, 0.0),
    "dye_racks": (5.4, 3.3, 3.3),
    "dye_vats": (3.6, 2.4, 2.4),
    "academy_hall": _hall(16, 10, 1.0, 2.0),
    "exam_cells": (8.4, 1.2, 1.4),
    "manor_gate": (10.0, 3.5, 6.6),
    "manor_hall": _hall(15, 10, 0.8, 1.8),
    "opera_stage": (6.2, 7.2, 4.6),
    "city_god_temple": _hall(18, 12, 1.4, 2.2),
    "bell_pavilion": (5.6, 5.6, 5.6),
    "bathhouse": _hall(14, 10, 0.45, 1.4),
    "watermill": (11.2, 4.9, 4.9),
    "boat_on_stocks": (4.0, 7.2, 7.2),
    "arch_bridge": (2.2, 8.5, 8.5),
    "post_station": (7.2, 3.2, 5.0),
    "barracks": _hall(24, 8, 0.45, 1.4),
    "execution_platform": (5.2, 4.2, 6.4),
    "tannery_racks": (6.2, 2.2, 2.2),
    "pottery_kiln": (2.0, 8.5, 10.5),
    "brewery_jars": (4.4, 2.3, 2.3),
    "town_hall_small": _hall(12, 8, 0.45, 1.4),
    # buildings_wild.py
    "stilt_house": (3.8, 3.0, 7.0),
    "stilt_house_small": (2.8, 2.6, 4.4),
    "earth_shrine": (1.4, 1.0, 1.6),
    "rustic_hut": (2.8, 2.5, 2.8),
    "hunter_lodge": (5.2, 3.0, 4.8),
    "charcoal_kiln": (2.8, 2.8, 2.8),
    "woodcutter_camp": (4.2, 5.0, 4.0),
    "buried_temple": (9.0, 6.5, 9.0),
    "buddha_cliff": (18.5, 6.5, 2.5),
    "forest_gate": (3.6, 1.0, 1.0),
    "forest_watchpost": (2.8, 2.3, 6.5),
    "banyan_giant": (3.0, 3.0, 3.0),
    # buildings_abyss.py
    "demon_palace": _hall(24, 14, 2.2, 2.4),
    "demon_library": (7.2, 7.2, 9.4),
    "ruined_hall": _hall(18, 11, 1.2, 2.0),
    "ruined_gate": (6.8, 1.0, 3.0),
    "ghost_house": _hall(8, 6, 0.34, 1.3, 0.6),
    "shadow_stall": _hall(6, 4, 0.34, 1.3, 0.6),
    "soul_forge": (5.2, 5.2, 10.5),
    "skull_tower": (2.5, 2.5, 2.5),
    "watch_spire": (4.2, 4.2, 6.6),
    "mine_entrance": (9.0, 10.0, 12.0),
    "bone_throne": (4.2, 3.7, 5.6),
    "blood_moon_shrine": (8.6, 8.6, 8.6),
    "iron_pens": (10.2, 3.2, 3.2),
    # buildings_sky.py
    "immortal_palace_gate": (12.2, 6.2, 6.2),
    "jade_palace_hall": _hall(26, 16, 2.0, 2.6),
    "hall_of_records": _hall(18, 11, 1.4, 2.0),
    "observatory": (6.2, 6.2, 8.5),
    "wind_temple": (9.2, 9.2, 11.5),
    "gate_of_heaven": (11.2, 1.0, 1.0),
    "sun_altar": (7.4, 7.4, 7.4),
    "elixir_spring": (4.7, 4.7, 4.7),
    "seal_of_heaven": (11.0, 11.0, 11.0),
}


def footprint(asset, x, z, yaw, pad=0.0):
    """World Rect of an asset's footprint (plus pad metres all round)."""
    hw, back, front = FOOT[asset]
    a = math.radians(yaw)
    # local centre offset along +z (front) is (front - back) / 2 -> world (sin a, cos a)
    off = (front - back) / 2
    cx, cz = x + math.sin(a) * off, z + math.cos(a) * off
    return Rect(cx, cz, hw + pad, (front + back) / 2 + pad, yaw)


class Sites:
    """Buildings declared before the ground is finalised: they level their pads and remember their
    footprints for the marker checks."""

    def __init__(self, ground):
        self.G = ground
        self.items = []        # (asset, name, x, z, yaw, level, scale)
        self.solids = []       # footprint Rects that markers must stay out of

    def add(self, asset, x, z, yaw=0.0, level=0.0, name=None, pad=2.5, blend=5.0, scale=1.0, solid=True,
            flatten=True):
        if flatten and asset in FOOT:
            self.G.pad(footprint(asset, x, z, yaw, pad), level, blend)
        if solid and asset in FOOT:
            self.solids.append((asset, name, footprint(asset, x, z, yaw, 0.3)))
        self.items.append((asset, name, x, z, yaw, level, scale))
        return (x, z)


def check_markers(map_id, markers, ground, solids, reach=9.0, tolerance=2.5, exempt=(), clear=4.0):
    """Every marker: outside all building footprints, and ground within `tolerance` metres of the
    marker's own ground at 9 m to the south (where the walkthrough stands the player for a fight) and
    at 5 m around it. Returns a list of problems."""
    problems = []
    for name, (x, y, z) in markers.items():
        for asset, sname, rect in solids:
            d = rect.sdf(x, z)
            if d < (0 if name in exempt else clear):
                problems.append(f"{map_id}/{name} {'inside' if d < 0 else f'{d:.1f} m from'} {sname or asset}")
        if name in exempt:
            continue
        g = ground(x, z)
        pts = [(x, z + reach)] + [(x + 5 * math.cos(a), z + 5 * math.sin(a)) for a in (0, 1.57, 3.14, 4.71)]
        for (px, pz) in pts:
            gh = ground(px, pz)
            if abs(gh - g) > tolerance:
                problems.append(f"{map_id}/{name}: ground at ({px:.0f},{pz:.0f}) is {gh - g:+.1f} m off")
                break
    return problems

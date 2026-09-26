#!/usr/bin/env python3
"""Generate godot/scenes/main.tscn: the Azure Cloud Sect level.

Positions are Godot coordinates (Y up, -Z = north). Every environment GLB
faces +Z, so rotation 0 means "front facing south, toward the sect gate".

    python tools/build_sect_scene.py
"""
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "godot" / "scenes" / "main.tscn"

WALL_HALF_X = 29.0
WALL_NORTH = -50.0
WALL_SOUTH = 30.0
SEGMENT = 8.0


def xform(pos, yaw_deg=0.0, scale=1.0):
    a = math.radians(yaw_deg)
    c, s = math.cos(a) * scale, math.sin(a) * scale
    # Basis columns: x = (c, 0, -s), y = (0, scale, 0), z = (s, 0, c)
    vals = [c, 0.0, -s, 0.0, scale, 0.0, s, 0.0, c, *pos]
    return "Transform3D(" + ", ".join(f"{v:.6g}" for v in vals) + ")"


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


def pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def main():
    items = build_layout()
    assets = sorted({a for a, *_ in items})
    ids = {a: f"{i + 1}_{a}" for i, a in enumerate(assets)}
    lines = ['[gd_scene format=3]', '']
    for a in assets:
        lines.append(f'[ext_resource type="PackedScene" path="res://assets/environment/{a}.glb" id="{ids[a]}"]')
    lines += [
        '[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="player"]',
        '[ext_resource type="Script" path="res://scripts/main.gd" id="main_script"]',
        '',
        '[sub_resource type="ProceduralSkyMaterial" id="sky_material"]',
        'sky_top_color = Color(0.22, 0.45, 0.78, 1)',
        'sky_horizon_color = Color(0.9, 0.84, 0.76, 1)',
        'sky_curve = 0.12',
        'ground_bottom_color = Color(0.72, 0.76, 0.82, 1)',
        'ground_horizon_color = Color(0.86, 0.82, 0.78, 1)',
        'sun_angle_max = 18.0',
        '',
        '[sub_resource type="Sky" id="sky"]',
        'sky_material = SubResource("sky_material")',
        '',
        '[sub_resource type="Environment" id="environment"]',
        'background_mode = 2',
        'sky = SubResource("sky")',
        'ambient_light_source = 3',
        'ambient_light_energy = 1.0',
        'reflected_light_source = 2',
        'tonemap_mode = 4',
        'tonemap_exposure = 1.1',
        'tonemap_white = 6.0',
        'ssao_enabled = true',
        'ssao_radius = 1.4',
        'ssao_intensity = 1.6',
        'glow_enabled = true',
        'glow_intensity = 0.55',
        'glow_bloom = 0.08',
        'glow_hdr_threshold = 1.1',
        'fog_enabled = true',
        'fog_light_color = Color(0.8, 0.85, 0.92, 1)',
        'fog_sun_scatter = 0.25',
        'fog_density = 0.0011',
        'fog_sky_affect = 0.15',
        'fog_height = -20.0',
        'fog_height_density = 0.035',
        'adjustment_enabled = true',
        'adjustment_saturation = 1.12',
        'adjustment_contrast = 1.05',
        '',
        '[node name="Main" type="Node3D"]',
        'script = ExtResource("main_script")',
        '',
        '[node name="WorldEnvironment" type="WorldEnvironment" parent="."]',
        'environment = SubResource("environment")',
        '',
        '[node name="Sun" type="DirectionalLight3D" parent="."]',
        f'transform = {sun_transform(-38, -35)}',
        'light_color = Color(1, 0.93, 0.82, 1)',
        'light_energy = 1.8',
        'shadow_enabled = true',
        'shadow_blur = 1.5',
        'directional_shadow_max_distance = 140.0',
        '',
        '[node name="Level" type="Node3D" parent="."]',
        '',
    ]
    counts = {}
    for asset, name, pos, yaw, scale in items:
        if name is None:
            counts[asset] = counts.get(asset, 0) + 1
            name = f"{pascal(asset)}{counts[asset]}"
        lines.append(f'[node name="{name}" parent="Level" instance=ExtResource("{ids[asset]}")]')
        lines.append(f"transform = {xform(pos, yaw, scale)}")
        lines.append("")
    lines += [
        '[node name="Player" parent="." instance=ExtResource("player")]',
        f"transform = {xform((0, 0.3, 60))}",
        '',
    ]
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.relative_to(ROOT)} with {len(items)} placed assets ({len(assets)} unique GLBs)")


def sun_transform(pitch_deg, yaw_deg):
    p, y = math.radians(pitch_deg), math.radians(yaw_deg)
    # Basis = Ry(yaw) * Rx(pitch)
    cy, sy, cp, sp = math.cos(y), math.sin(y), math.cos(p), math.sin(p)
    xa = (cy, 0.0, -sy)
    ya = (sy * sp, cp, cy * sp)
    za = (sy * cp, -sp, cy * cp)
    vals = [*xa, *ya, *za, 0.0, 30.0, 0.0]
    return "Transform3D(" + ", ".join(f"{v:.6g}" for v in vals) + ")"


if __name__ == "__main__":
    main()

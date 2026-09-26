"""Shared writer for generated Godot map scenes.

A map module exposes ``build() -> MapDef``. The writer turns it into
``godot/scenes/maps/<map_id>.tscn`` with this node layout, which the runtime
(godot/scripts/map.gd, game.gd) relies on:

    Map (Node3D, map.gd: map_id, display_name, music, ambient, kill_y)
      WorldEnvironment
      Sun (DirectionalLight3D)
      Level (Node3D)            instanced environment GLBs
      Markers (Node3D)          Marker3D per named location (see tools/world_spec.py)

Positions are Godot coordinates (Y up, -Z = north). Environment GLBs face +Z,
so yaw 0 means "front facing south".
"""
import math
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "godot" / "scenes" / "maps"


@dataclass
class Sky:
    top: tuple = (0.22, 0.45, 0.78)
    horizon: tuple = (0.9, 0.84, 0.76)
    ground_bottom: tuple = (0.72, 0.76, 0.82)
    ground_horizon: tuple = (0.86, 0.82, 0.78)
    curve: float = 0.12
    sun_angle_max: float = 18.0


@dataclass
class Env:
    sky: Sky = field(default_factory=Sky)
    ambient_energy: float = 1.0
    exposure: float = 1.1
    fog_color: tuple = (0.8, 0.85, 0.92)
    fog_density: float = 0.0011
    fog_height: float = -20.0
    fog_height_density: float = 0.035
    fog_sun_scatter: float = 0.25
    fog_sky_affect: float = 0.15
    glow_intensity: float = 0.55
    saturation: float = 1.12
    contrast: float = 1.05
    sun_pitch: float = -38.0
    sun_yaw: float = -35.0
    sun_color: tuple = (1.0, 0.93, 0.82)
    sun_energy: float = 1.8
    shadow_distance: float = 140.0
    volumetric_fog: bool = False


@dataclass
class MapDef:
    map_id: str
    display_name: str
    music: str
    items: list                       # (asset, node name | None, (x, y, z), yaw_deg, scale)
    markers: dict                     # marker name -> (x, y, z)
    env: Env = field(default_factory=Env)
    ambient: str = "motes"            # map.gd particle preset: motes|fireflies|petals|embers|snow|none
    kill_y: float = -30.0             # the player respawns when falling below this height
    asset_dir: dict = field(default_factory=dict)  # asset -> res:// dir override


def xform(pos, yaw_deg=0.0, scale=1.0):
    a = math.radians(yaw_deg)
    if isinstance(scale, (tuple, list)):
        sx, sy, sz = scale
    else:
        sx = sy = sz = scale
    c, s = math.cos(a), math.sin(a)
    # Basis columns: x = (c, 0, -s) * sx, y = (0, 1, 0) * sy, z = (s, 0, c) * sz
    vals = [c * sx, 0.0, -s * sx, 0.0, sy, 0.0, s * sz, 0.0, c * sz, *pos]
    return "Transform3D(" + ", ".join(f"{v:.6g}" for v in vals) + ")"


def sun_transform(pitch_deg, yaw_deg):
    p, y = math.radians(pitch_deg), math.radians(yaw_deg)
    cy, sy, cp, sp = math.cos(y), math.sin(y), math.cos(p), math.sin(p)
    xa = (cy, 0.0, -sy)
    ya = (sy * sp, cp, cy * sp)
    za = (sy * cp, -sp, cy * cp)
    vals = [*xa, *ya, *za, 0.0, 30.0, 0.0]
    return "Transform3D(" + ", ".join(f"{v:.6g}" for v in vals) + ")"


def pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def _c(rgb):
    return "Color(%s, 1)" % ", ".join(f"{v:.4g}" for v in rgb)


def render(m: MapDef) -> str:
    assets = sorted({a for a, *_ in m.items})
    ids = {a: f"{i + 1}_{a}" for i, a in enumerate(assets)}
    e = m.env
    lines = ['[gd_scene format=3]', '']
    for a in assets:
        d = m.asset_dir.get(a, "res://assets/environment")
        lines.append(f'[ext_resource type="PackedScene" path="{d}/{a}.glb" id="{ids[a]}"]')
    lines += [
        '[ext_resource type="Script" path="res://scripts/map.gd" id="map_script"]',
        '',
        '[sub_resource type="ProceduralSkyMaterial" id="sky_material"]',
        f'sky_top_color = {_c(e.sky.top)}',
        f'sky_horizon_color = {_c(e.sky.horizon)}',
        f'sky_curve = {e.sky.curve:.4g}',
        f'ground_bottom_color = {_c(e.sky.ground_bottom)}',
        f'ground_horizon_color = {_c(e.sky.ground_horizon)}',
        f'sun_angle_max = {e.sky.sun_angle_max:.4g}',
        '',
        '[sub_resource type="Sky" id="sky"]',
        'sky_material = SubResource("sky_material")',
        '',
        '[sub_resource type="Environment" id="environment"]',
        'background_mode = 2',
        'sky = SubResource("sky")',
        'ambient_light_source = 3',
        f'ambient_light_energy = {e.ambient_energy:.4g}',
        'reflected_light_source = 2',
        'tonemap_mode = 4',
        f'tonemap_exposure = {e.exposure:.4g}',
        'tonemap_white = 6.0',
        'ssao_enabled = true',
        'ssao_radius = 1.4',
        'ssao_intensity = 1.6',
        'glow_enabled = true',
        f'glow_intensity = {e.glow_intensity:.4g}',
        'glow_bloom = 0.08',
        'glow_hdr_threshold = 1.1',
        'fog_enabled = true',
        f'fog_light_color = {_c(e.fog_color)}',
        f'fog_sun_scatter = {e.fog_sun_scatter:.4g}',
        f'fog_density = {e.fog_density:.4g}',
        f'fog_sky_affect = {e.fog_sky_affect:.4g}',
        f'fog_height = {e.fog_height:.4g}',
        f'fog_height_density = {e.fog_height_density:.4g}',
    ]
    if e.volumetric_fog:
        lines += ['volumetric_fog_enabled = true', 'volumetric_fog_density = 0.012',
                  f'volumetric_fog_albedo = {_c(e.fog_color)}']
    lines += [
        'adjustment_enabled = true',
        f'adjustment_saturation = {e.saturation:.4g}',
        f'adjustment_contrast = {e.contrast:.4g}',
        '',
        '[node name="Map" type="Node3D"]',
        'script = ExtResource("map_script")',
        f'map_id = "{m.map_id}"',
        f'display_name = "{m.display_name}"',
        f'music = "{m.music}"',
        f'ambient = "{m.ambient}"',
        f'kill_y = {m.kill_y:.4g}',
        '',
        '[node name="WorldEnvironment" type="WorldEnvironment" parent="."]',
        'environment = SubResource("environment")',
        '',
        '[node name="Sun" type="DirectionalLight3D" parent="."]',
        f'transform = {sun_transform(e.sun_pitch, e.sun_yaw)}',
        f'light_color = {_c(e.sun_color)}',
        f'light_energy = {e.sun_energy:.4g}',
        'shadow_enabled = true',
        'shadow_blur = 1.5',
        f'directional_shadow_max_distance = {e.shadow_distance:.4g}',
        '',
        '[node name="Level" type="Node3D" parent="."]',
        '',
    ]
    counts = {}
    for asset, name, pos, yaw, scale in m.items:
        if name is None:
            counts[asset] = counts.get(asset, 0) + 1
            name = f"{pascal(asset)}{counts[asset]}"
        lines.append(f'[node name="{name}" parent="Level" instance=ExtResource("{ids[asset]}")]')
        lines.append(f"transform = {xform(pos, yaw, scale)}")
        lines.append("")
    lines += ['[node name="Markers" type="Node3D" parent="."]', '']
    for name, pos in m.markers.items():
        lines.append(f'[node name="{name}" type="Marker3D" parent="Markers"]')
        lines.append(f"transform = {xform(pos)}")
        lines.append("")
    return "\n".join(lines)


def check_markers(m: MapDef):
    """Every marker named in tools/world_spec.py must be placed (and nothing else)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import world_spec
    want = set(world_spec.MAPS[m.map_id]["markers"])
    have = set(m.markers)
    missing, extra = want - have, have - want
    if missing or extra:
        raise SystemExit(f"{m.map_id}: marker mismatch, missing={sorted(missing)} extra={sorted(extra)}")


def write(m: MapDef):
    check_markers(m)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{m.map_id}.tscn"
    out.write_text(render(m))
    n_assets = len({a for a, *_ in m.items})
    print(f"wrote {out.relative_to(ROOT)}: {len(m.items)} placed ({n_assets} unique GLBs), "
          f"{len(m.markers)} markers")
    return out

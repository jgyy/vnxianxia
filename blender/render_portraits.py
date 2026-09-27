"""Cycles dialogue portraits: head-and-shoulders character art in a 3/4 view.

    python blender/render_portraits.py [--out godot/ui/portraits] [--only name,name]
                                       [--samples 192] [--size 256]

Photographic set-up: an 85 mm lens at about a metre, three-quarter view with
the far eye on the thirds line, shallow depth of field focused on the near
eye (f/2.2), a large soft key light high on the camera side, a dim fill, a
coloured rim / hair light from behind and a studio backdrop with a soft
radial falloff tinted per character.  Render-time material upgrades that
glTF cannot carry: subsurface scattering on skin, a refractive cornea and
tear line, and a hint of subsurface in the sclera.  Each character wears a
quiet expression suited to its role through the face shape keys.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from xianxia import characters, preview  # noqa: E402

ROOT = os.path.dirname(HERE)

# expression (shape key -> value), backdrop (inner, outer) and rim colour per character
LOOKS = {
    "cultivator_male": (dict(smile=0.12, brow_up=0.05), ((0.22, 0.26, 0.31), (0.05, 0.06, 0.08)), (0.75, 0.85, 1.0)),
    "cultivator_female": (dict(smile=0.2, eyes_wide=0.1), ((0.28, 0.24, 0.27), (0.07, 0.055, 0.065)),
                          (1.0, 0.82, 0.78)),
    "elder_male": (dict(smile=0.1, brow_inner_up=0.12), ((0.2, 0.24, 0.21), (0.05, 0.06, 0.05)), (1.0, 0.9, 0.7)),
    "sect_master": (dict(smile=0.1), ((0.27, 0.25, 0.2), (0.07, 0.06, 0.04)), (1.0, 0.9, 0.7)),
    "disciple_male": (dict(smile=0.18), ((0.2, 0.25, 0.3), (0.05, 0.06, 0.08)), (0.8, 0.9, 1.0)),
    "disciple_female": (dict(smile=0.28), ((0.22, 0.27, 0.22), (0.05, 0.07, 0.05)), (0.9, 1.0, 0.85)),
    "villager_male": (dict(smile=0.1), ((0.27, 0.22, 0.17), (0.07, 0.05, 0.04)), (1.0, 0.85, 0.6)),
    "villager_female": (dict(smile=0.22), ((0.27, 0.22, 0.17), (0.07, 0.05, 0.04)), (1.0, 0.85, 0.6)),
    "bandit": (dict(brow_down=0.35, sneer_L=0.2), ((0.22, 0.18, 0.15), (0.05, 0.04, 0.035)), (1.0, 0.7, 0.45)),
    "demon_cultivator": (dict(brow_down=0.25, squint_L=0.2, squint_R=0.2, smile=0.08),
                         ((0.2, 0.06, 0.07), (0.04, 0.01, 0.015)), (1.0, 0.3, 0.25)),
    "blood_patriarch": (dict(brow_down=0.4, frown=0.15), ((0.22, 0.05, 0.05), (0.04, 0.01, 0.01)), (1.0, 0.35, 0.2)),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "godot", "ui", "portraits"))
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=192)
    ap.add_argument("--size", type=int, default=256)
    return ap.parse_args(argv)


def _bsdf(mat):
    if mat is None or not mat.use_nodes:
        return None
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def upgrade_materials(cfg):
    """Render-only shading that the glTF materials cannot express."""
    s = cfg["scale"]
    for mat in bpy.data.materials:
        b = _bsdf(mat)
        if b is None:
            continue
        mname = mat.name.lower()
        sss = b.inputs["Subsurface Weight"]
        if mname.endswith(("_face", "_skin")) and sss.default_value == 0.0 and not sss.links:
            sss.default_value = 0.32                     # skin materials without their own SSS set-up
            b.inputs["Subsurface Radius"].default_value = (1.0, 0.42, 0.24)
            b.inputs["Subsurface Scale"].default_value = 0.0035 * s
        elif mname.endswith(("cornea", "tearline")):
            # glTF can only carry an alpha film; in Cycles the cornea refracts the iris like a lens
            b.inputs["Transmission Weight"].default_value = 1.0
            b.inputs["Alpha"].default_value = 1.0
            b.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            b.inputs["Roughness"].default_value = 0.0
            b.inputs["IOR"].default_value = 1.376
            mat.surface_render_method = "DITHERED"
        elif mname.endswith(("eye_sclera", "teeth", "tongue", "mouth_inner")) and sss.default_value == 0.0:
            sss.default_value = 0.25
            b.inputs["Subsurface Scale"].default_value = 0.002 * s


def pose(arm, meshes, expression):
    arm.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.frame_set(1)
    head = next((m for m in meshes if m.name == "Head"), None)
    if head is not None and head.data.shape_keys:
        # portraits hold a designed expression: mute the face track of the idle clip
        ad = head.data.shape_keys.animation_data
        if ad:
            for tr in ad.nla_tracks:
                tr.mute = True
        for kb in head.data.shape_keys.key_blocks[1:]:
            kb.value = expression.get(kb.name, 0.0)
    for bone in ("eye.L", "eye.R"):
        pb = arm.pose.bones.get(bone)
        if pb is not None:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def bone_world(arm, name, tail=False):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.tail if tail else pb.head)


def portrait(cfg, args):
    arm, meshes, _ = characters.build_character(cfg)
    expr, (bg_in, bg_out), rim = LOOKS.get(cfg["name"], (dict(), ((0.2, 0.22, 0.25), (0.05, 0.055, 0.065)),
                                                          (1.0, 0.9, 0.8)))
    pose(arm, meshes, expr)
    upgrade_materials(cfg)
    s = cfg["scale"]
    scene = preview.setup(res=(args.size * 2, args.size * 2), samples=args.samples, sky=(0.1, 0.11, 0.13),
                          strength=0.35, look="AgX - Medium High Contrast")
    scene.view_settings.exposure = -0.35
    scene.cycles.max_bounces = 8
    scene.cycles.transmission_bounces = 8
    scene.cycles.use_denoising = True
    eye_l = bone_world(arm, "eye.L")
    eye_r = bone_world(arm, "eye.R")
    mid = (eye_l + eye_r) * 0.5
    face = mid + Vector((0.0, -0.01 * s, -0.045 * s))
    # three-quarter view from the character's left, slightly above eye level
    az = math.radians(28.0)
    dist = 0.82 * s
    cam_loc = face + Vector((math.sin(az) * dist, -math.cos(az) * dist, 0.02 * s))
    target = mid + Vector((0.012 * s, 0.0, -0.035 * s))
    preview.camera(cam_loc, target, lens=85, focus=eye_l + Vector((0.0, -0.012 * s, 0.0)), fstop=2.2)
    # short lighting: the big soft key comes from the far side of the face (the side turned away
    # from the camera) and high, so the visible cheek falls into gentle shadow and the face models;
    # a broad dim fill from the camera side lifts the shadows; rim + hair lights from behind
    preview.area(face + Vector((-0.55 * s, -0.85 * s, 0.5 * s)), face, energy=42, size=1.0, color=(1.0, 0.95, 0.9))
    preview.area(face + Vector((0.95 * s, -0.5 * s, 0.1 * s)), face, energy=12, size=1.6, color=(0.92, 0.95, 1.0))
    preview.area(face + Vector((0.5 * s, 0.7 * s, 0.35 * s)), face + Vector((0, 0, 0.03 * s)), energy=70, size=0.4,
                 color=rim)
    preview.area(face + Vector((0.2 * s, 0.45 * s, 0.9 * s)), face, energy=40, size=0.5, color=(1.0, 0.95, 0.9))
    # a small soft light beside the lens puts the catchlight in the eyes
    preview.area(cam_loc + Vector((0.12 * s, 0.0, 0.1 * s)), eye_l, energy=4, size=0.25, color=(1.0, 1.0, 1.0))
    back = face + Vector((-math.sin(az), math.cos(az), 0.0)) * 1.4 * s
    preview.backdrop(back, cam_loc - back, size=(2.6 * s, 2.0 * s), inner=bg_in, outer=bg_out)
    path = os.path.join(args.out, cfg["name"] + ".png")
    preview.render(path)
    # rendered at twice the size and filtered down: cleaner edges on lashes and hair
    img = bpy.data.images.load(path)
    img.scale(args.size, args.size)
    img.save()
    print("wrote", path)
    return path


def main():
    args = parse_args()
    only = {s for s in args.only.split(",") if s}
    os.makedirs(args.out, exist_ok=True)
    for cfg in characters.HUMANOIDS:
        if only and cfg["name"] not in only:
            continue
        portrait(cfg, args)


if __name__ == "__main__":
    main()

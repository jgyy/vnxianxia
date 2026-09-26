"""Render a contact sheet of protagonist animation poses (Cycles, CPU).

    python blender/render_animation_sheet.py [--out docs/screenshots/animations_sheet.jpg]
        [--poses action:frame,...] [--blend cached.blend] [--cols 8] [--cell 240x320]

Without --blend the protagonist is built from scratch (takes ~30 s).  A frame
of -1 means the middle of the action, -2 its last frame.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from xianxia import characters, preview  # noqa: E402

ROOT = os.path.dirname(HERE)

SHEET = [
    "combat_idle:10", "palm_1:8", "palm_3:9", "palm_5:14", "kick_1:10", "kick_3:12", "spin_kick:14",
    "flying_kick:14", "uppercut:10", "sword_1:10", "sword_3:12", "sword_5:16", "charge_hold:10",
    "charge_release:8", "blast_two_hand:16", "blast_rain:20", "block_idle:10", "parry:8", "dodge_l:8",
    "roll_forward:10", "backflip:12", "stagger_back:6", "knockdown:30", "getup:20", "death_forward:-2",
    "walk_back:8", "strafe_l:8", "sprint:6", "crouch_walk:10", "sneak:12", "jump_start:8", "jump_air:10",
    "double_jump_flip:12", "glide:10", "landing_hard:6", "slide:12", "climb_up:20", "ledge_hang:10",
    "meditate_levitate:30", "breakthrough:40", "mudra_sequence:40", "sword_ride_idle:20",
    "bow_deep:30", "bow_fist_palm:24", "wave:20", "point:18", "laugh:20", "cry:30", "shrug:16",
    "clap:12", "cheer:20", "facepalm:26", "thinking:20", "arms_crossed:20", "bashful:30",
    "surprised:10", "yawn:30", "stretch:40", "sit_ground_idle:20", "sit_chair:20", "sleep:20",
    "drink_tea:30", "read_scroll:20", "write_calligraphy:20", "play_flute:20", "play_guqin:20",
    "sweep_floor:20", "pick_up:20", "pray_incense:30", "dance_1:30", "dance_3:30", "victory_1:30",
    "victory_2:30", "idle_adjust_sleeve:30", "talk_emphatic:30",
]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "screenshots", "animations_sheet.jpg"))
    ap.add_argument("--poses", default="")
    ap.add_argument("--blend", default="")
    ap.add_argument("--female", action="store_true")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--cell", default="220x300")
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--view", default="front", help="front | side | back")
    return ap.parse_args(argv)


def build(args):
    cfg = characters.FEMALE if args.female else characters.MALE
    if args.blend:
        bpy.ops.wm.open_mainfile(filepath=args.blend)
        arm = bpy.data.objects["Armature"]
        from xianxia import moves
        s = cfg["scale"]
        J = {n: (h * s, t * s, p) for n, (h, t, p) in characters.joints(cfg).items()}
        moves.build_player_actions(arm, J, cfg, s)
    else:
        characters.build_character(cfg)
    return bpy.data.objects["Armature"]


def label(text, loc):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = text
    cu.size = 0.11
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("Label", cu)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("LabelMat")
    mat.use_nodes = True
    em = mat.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.03, 1)
    mat.node_tree.links.new(em.outputs[0], mat.node_tree.nodes["Material Output"].inputs[0])
    cu.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def main():
    args = parse_args()
    arm = build(args)
    cw, ch = (int(v) for v in args.cell.split("x"))
    poses = [p for p in (args.poses.split(",") if args.poses else SHEET) if p]
    scene = preview.setup(res=(cw, ch), samples=args.samples, sky=(0.86, 0.87, 0.86), strength=1.0)
    scene.cycles.use_denoising = False
    preview.sun((55, 0, 30), 3.0)
    preview.ground(30, (0.62, 0.6, 0.56))
    view = {"front": ((2.6, -7.2, 1.35), 0), "side": ((7.6, 0.0, 1.35), 0), "back": ((-2.6, 7.2, 1.35), 0)}
    cam_loc = Vector(view[args.view][0])
    cam = preview.camera(cam_loc, (0, 0, 0.95), ortho=2.6)
    lab_dir = (Vector((0, 0, 0.95)) - cam_loc).normalized()
    tmp = os.path.join(os.path.dirname(args.out), "_cells")
    os.makedirs(tmp, exist_ok=True)
    cells = []
    for i, p in enumerate(poses):
        name, fr = p.split(":")
        act = bpy.data.actions.get(name)
        if act is None:
            print("missing action", name)
            continue
        arm.animation_data.action = act
        f0, f1 = act.frame_range
        fr = int(fr)
        frame = int(f0 + fr) if fr >= 0 else (int((f0 + f1) / 2) if fr == -1 else int(f1))
        scene.frame_set(frame)
        lab = label(name, (0, 0, 0))
        lab.rotation_euler = lab_dir.to_track_quat("-Z", "Y").to_euler()
        lab.location = Vector((0, 0, -0.27)) - lab_dir * 6.5
        path = os.path.join(tmp, f"{i:03d}.png")
        preview.render(path)
        bpy.data.objects.remove(lab, do_unlink=True)
        cells.append(path)
    cols = min(args.cols, len(cells))
    rows = (len(cells) + cols - 1) // cols
    sheet = np.ones((rows * ch, cols * cw, 4), dtype=np.float32)
    for i, path in enumerate(cells):
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(ch, cw, 4)
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * ch
        sheet[y0:y0 + ch, c * cw:(c + 1) * cw] = px
        bpy.data.images.remove(img)
        os.remove(path)
    os.rmdir(tmp)
    out = bpy.data.images.new("sheet", cols * cw, rows * ch, alpha=False)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = args.out
    out.file_format = "JPEG"
    scene.render.image_settings.quality = 85
    out.save()
    print("wrote", args.out, len(cells), "poses")


if __name__ == "__main__":
    main()

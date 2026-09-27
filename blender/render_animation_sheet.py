"""Render contact sheets of character animations (Cycles CPU or Workbench).

Pose sheet (one cell per action:frame):
    python blender/render_animation_sheet.py [--out docs/screenshots/animations_sheet.jpg]
        [--poses action:frame,...] [--blend cached.blend] [--cols 8] [--cell 240x320]

Gait strips (one row per clip, N evenly spaced frames over the cycle):
    python blender/render_animation_sheet.py --name cultivator_female --strips walk,run
        --frames 8 --view side --engine workbench --travel --out /tmp/strip.jpg

With --travel the body is moved along the ground at the clip's authored speed
(blender/xianxia/gait.py) over striped floor markers, so a planted foot stays
on the same stripe from cell to cell.  Without --blend the character is built
from scratch.  A pose frame of -1 means the middle of the action, -2 its last
frame.  --save-blend writes the built scene for later --blend runs.
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

from xianxia import characters, creatures, preview  # noqa: E402

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

# authored ground speed (m/s) and travel direction (left, forward) per clip
TRAVEL = {"walk": (1.6, (0, 1)), "run": (4.6, (0, 1)), "sprint": (6.2, (0, 1)), "sneak": (1.0, (0, 1)),
          "crouch_walk": (0.8, (0, 1)), "walk_back": (1.0, (0, -1)), "strafe_l": (1.0, (1, 0)),
          "strafe_r": (1.0, (-1, 0))}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "screenshots", "animations_sheet.jpg"))
    ap.add_argument("--poses", default="")
    ap.add_argument("--blend", default="")
    ap.add_argument("--save-blend", default="")
    ap.add_argument("--female", action="store_true")
    ap.add_argument("--name", default="", help="any humanoid config name (default: the male hero)")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--cell", default="220x300")
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--view", default="front", help="front | side | back | three_quarter")
    ap.add_argument("--engine", default="cycles", help="cycles | workbench | eevee")
    ap.add_argument("--strips", default="", help="comma separated clips, one row each")
    ap.add_argument("--frames", type=int, default=8, help="cells per strip")
    ap.add_argument("--travel", action="store_true", help="move the body at the clip's authored speed")
    ap.add_argument("--ortho", type=float, default=0.0, help="orthographic frame size (m)")
    ap.add_argument("--target-z", type=float, default=0.0, help="camera aim height (m)")
    ap.add_argument("--skeleton", action="store_true", help="add capsule proxies on the bones (L red, R blue)")
    ap.add_argument("--hide", default="", help="comma separated meshes to leave out (e.g. Outfit)")
    return ap.parse_args(argv)


def config(args):
    if args.name:
        cfgs = {c["name"]: c for c in characters.HUMANOIDS}
        cfgs["stone_golem"] = creatures.GOLEM
        return cfgs[args.name]
    return characters.FEMALE if args.female else characters.MALE


def build(args):
    cfg = config(args)
    if args.blend:
        # the cached scene already holds every action (rebuilding the move set
        # here used to add "*.001" duplicates and render the stale originals)
        bpy.ops.wm.open_mainfile(filepath=args.blend)
    elif cfg["name"] == "stone_golem":
        creatures.build_golem()
    else:
        characters.build_character(cfg)
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.save_blend)
    return cfg, bpy.data.objects["Armature"]


def label(text, loc, size=0.11):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("Label", cu)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    mat = bpy.data.materials.new("LabelMat")
    mat.use_nodes = True
    mat.diffuse_color = (0.02, 0.02, 0.03, 1)
    em = mat.node_tree.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.03, 1)
    mat.node_tree.links.new(em.outputs[0], mat.node_tree.nodes["Material Output"].inputs[0])
    cu.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def stripes(length=60.0, step=0.25):
    """Floor markers across the travel line: alternating light / dark bands."""
    import bmesh
    bm = bmesh.new()
    n = int(length / step)
    for i in range(-n // 2, n // 2):
        if i % 2:
            continue
        y0 = i * step
        v = [bm.verts.new(p) for p in ((-3.0, y0, 0.001), (3.0, y0, 0.001), (3.0, y0 + step, 0.001),
                                        (-3.0, y0 + step, 0.001))]
        bm.faces.new(v)
    me = bpy.data.meshes.new("Stripes")
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("StripeMat")
    mat.use_nodes = True
    mat.diffuse_color = (0.33, 0.31, 0.29, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.33, 0.31, 0.29, 1)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Stripes", me)
    bpy.context.scene.collection.objects.link(ob)
    # the same bands turned 90 degrees, for sideways travel
    ob2 = ob.copy()
    ob2.rotation_euler = (0, 0, math.radians(90))
    bpy.context.scene.collection.objects.link(ob2)
    return ob


def skeleton(arm):
    """Capsule proxies riding the body bones: left limbs red, right blue."""
    import bmesh
    cols = {"L": (0.85, 0.2, 0.15, 1), "R": (0.15, 0.35, 0.9, 1), "C": (0.85, 0.8, 0.7, 1)}
    mats = {}
    for k, c in cols.items():
        m = bpy.data.materials.new("Proxy" + k)
        m.diffuse_color = c
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = c
        mats[k] = m
    names = ["hips", "spine", "chest", "neck"]
    for sd in ("L", "R"):
        names += [f"{b}.{sd}" for b in ("upper_arm", "forearm", "hand", "thigh", "shin", "foot", "toe")]
    for n in names:
        b = arm.data.bones.get(n)
        if b is None:
            continue
        r = 0.035 if n.split(".")[0] in ("thigh", "shin", "upper_arm", "forearm") else 0.03
        if n in ("hips", "spine", "chest"):
            r = 0.08
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r * 0.8, depth=b.length)
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, b.length / 2))
        me = bpy.data.meshes.new("Proxy_" + n)
        bm.to_mesh(me)
        bm.free()
        side = n[-1] if n[-2:] in (".L", ".R") else "C"
        me.materials.append(mats[side])
        ob = bpy.data.objects.new("Proxy_" + n, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = n
        # bone space: y along the bone; the cone was built along z from the head
        ob.matrix_parent_inverse.identity()
        ob.rotation_euler = (math.radians(-90), 0, 0)
        ob.location = (0, -b.length, 0)


def setup_engine(args, cw, ch):
    scene = preview.setup(res=(cw, ch), samples=args.samples, sky=(0.86, 0.87, 0.86), strength=1.0)
    scene.cycles.use_denoising = False
    if args.engine == "workbench":
        scene.render.engine = "BLENDER_WORKBENCH"
        sh = scene.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL" if args.skeleton else "TEXTURE"
        sh.show_shadows = True
        sh.show_cavity = True
        sh.background_type = "VIEWPORT"
        sh.background_color = (0.80, 0.82, 0.84)
        scene.view_settings.view_transform = "Standard"
    elif args.engine == "eevee":
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = eng
                break
            except TypeError:
                continue
    preview.sun((55, 0, 30), 3.0)
    g = preview.ground(80, (0.62, 0.6, 0.56))
    g.data.materials[0].diffuse_color = (0.72, 0.70, 0.66, 1)
    return scene


VIEWS = {"front": (2.6, -7.2, 1.35), "side": (7.6, 0.0, 1.05), "back": (-2.6, 7.2, 1.35), "face": (0.0, -8.0, 1.0),
         "three_quarter": (5.4, -5.4, 1.2)}


def render_cells(scene, arm, cells, cw, ch, cam_off, tmp, travel, ortho=0.0, aim=0.0):
    """cells: [(action, frame, text)]; returns the list of image paths."""
    cam = preview.camera(Vector(cam_off), (0, 0, 0.95), ortho=ortho or (2.6 if not travel else 2.3))
    paths = []
    for i, (name, frame, text) in enumerate(cells):
        act = bpy.data.actions.get(name)
        if act is None:
            print("missing action", name)
            continue
        arm.animation_data.action = act
        f0 = act.frame_range[0]
        shift = Vector((0, 0, 0))
        if travel and name in TRAVEL:
            v, (dx, df) = TRAVEL[name]
            t = (frame - f0) / scene.render.fps
            shift = Vector((dx, -df, 0.0)) * (v * t)
        arm.location = shift
        target = shift + Vector((0, 0, aim or (0.95 if not travel else 0.85)))
        cam.location = target + Vector(cam_off) - Vector((0, 0, 0.95))
        preview.look_at(cam, target)
        scene.frame_set(int(math.floor(frame)), subframe=frame - math.floor(frame))
        lab = None
        if text:
            lab = label(text, (0, 0, 0), 0.09)
            d = (target - cam.location).normalized()
            lab.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
            lab.location = target + Vector((0, 0, -0.47 * cam.data.ortho_scale + 0.05)) - d * 3.0
            lab.scale = (cam.data.ortho_scale / 2.3,) * 3
        path = os.path.join(tmp, f"{i:03d}.png")
        preview.render(path)
        if lab:
            bpy.data.objects.remove(lab, do_unlink=True)
        paths.append(path)
    return paths


def assemble(paths, cols, cw, ch, out, scene):
    cols = min(cols, len(paths))
    rows = (len(paths) + cols - 1) // cols
    sheet = np.ones((rows * ch, cols * cw, 4), dtype=np.float32)
    for i, path in enumerate(paths):
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(ch, cw, 4)
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * ch
        sheet[y0:y0 + ch, c * cw:(c + 1) * cw] = px
        bpy.data.images.remove(img)
        os.remove(path)
    img = bpy.data.images.new("sheet", cols * cw, rows * ch, alpha=False)
    img.pixels[:] = sheet.ravel()
    img.filepath_raw = out
    img.file_format = "JPEG"
    scene.render.image_settings.quality = 85
    img.save()


def main():
    args = parse_args()
    cfg, arm = build(args)
    if args.skeleton:
        skeleton(arm)
    for name in filter(None, args.hide.split(",")):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_render = True
    cw, ch = (int(v) for v in args.cell.split("x"))
    scene = setup_engine(args, cw, ch)
    if args.travel:
        stripes()
    tmp = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_cells")
    os.makedirs(tmp, exist_ok=True)
    cells = []
    cols = args.cols
    if args.strips:
        for name in args.strips.split(","):
            act = bpy.data.actions.get(name)
            if act is None:
                print("missing action", name)
                continue
            f0, f1 = act.frame_range
            n = args.frames
            for k in range(n):
                fr = f0 + (f1 - f0) * k / n
                cells.append((name, fr, f"{name} {k}/{n}" if k == 0 else f"{k}/{n}"))
        cols = args.frames
    else:
        for p in (args.poses.split(",") if args.poses else SHEET):
            if not p:
                continue
            name, fr = p.split(":")
            act = bpy.data.actions.get(name)
            if act is None:
                print("missing action", name)
                continue
            f0, f1 = act.frame_range
            fr = int(fr)
            frame = int(f0 + fr) if fr >= 0 else (int((f0 + f1) / 2) if fr == -1 else int(f1))
            cells.append((name, frame, name))
    paths = render_cells(scene, arm, cells, cw, ch, VIEWS[args.view], tmp, args.travel, args.ortho, args.target_z)
    assemble(paths, cols, cw, ch, args.out, scene)
    os.rmdir(tmp)
    print("wrote", args.out, len(paths), "cells")


if __name__ == "__main__":
    main()

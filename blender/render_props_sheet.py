"""Cycles contact sheet of built prop / item GLBs (documentation + visual QA).

    python blender/render_props_sheet.py --kind props --out docs/screenshots/quest_props.jpg
    python blender/render_props_sheet.py --kind items --out docs/screenshots/items.jpg
    python blender/render_props_sheet.py --dir godot/assets/environment --names a,b --out /tmp/x.jpg

Every tile imports one GLB (collision-only nodes hidden), frames it from the
front three-quarter view (fronts face -Y in Blender = +Z in Godot), labels it
with its name and size in metres and, for props, stands a 1.75 m grey figure
beside it for scale. Prints each asset's visual bounds and collider bounds.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from xianxia import items, preview, quest_props, util  # noqa: E402

ROOT = os.path.dirname(HERE)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", choices=["props", "items", "dressing", "quest"], default="props")
    ap.add_argument("--dir", default="")
    ap.add_argument("--names", default="")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "screenshots", "quest_props.jpg"))
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--tile", type=int, default=300)
    ap.add_argument("--samples", type=int, default=12)
    return ap.parse_args(argv)


def _bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def _label(text, cam, dist, fov, aspect=1.0):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = text
    cu.size = 1.0
    cu.align_x = "CENTER"
    ob = bpy.data.objects.new("Label", cu)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("LabelMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.03, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    cu.materials.append(mat)
    half = math.tan(fov / 2) * dist
    ob.scale = (half * 0.085,) * 3
    ob.parent = cam
    ob.location = (0, -half * 0.9, -dist)
    return ob


def _figure(x, color=(0.45, 0.45, 0.47)):
    """1.75 m capsule person for scale."""
    bm = bmesh.new()
    util.cylinder(bm, 0.2, 0.17, 1.45, loc=(0, 0, 0.725), segs=12)
    util.sphere(bm, 0.12, loc=(0, 0, 1.63), segs=12, rings=8)
    me = bpy.data.meshes.new("Figure")
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("FigureMat")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Figure", me)
    ob.location = (x, 0.3, 0)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def render_tile(path, out_png, tile, samples, figure):
    util.reset_scene()
    preview.setup(res=(tile, tile), samples=samples, sky=(0.78, 0.8, 0.84), strength=0.8)
    bpy.context.scene.cycles.max_bounces = 4
    bpy.ops.import_scene.gltf(filepath=path)
    vis, cols = [], []
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        if "colonly" in o.name:
            o.hide_render = True
            cols.append(o)
        else:
            vis.append(o)
    lo, hi = _bounds(vis)
    size = hi - lo
    info = f"{os.path.basename(path)[:-4]}: vis {size.x:.2f} x {size.y:.2f} x {size.z:.2f} (z {lo.z:.2f}..{hi.z:.2f})"
    if cols:
        clo, chi = _bounds(cols)
        cs = chi - clo
        info += f" | col {cs.x:.2f} x {cs.y:.2f} x {cs.z:.2f} ({len(cols)})"
    else:
        info += " | no collider"
    print(info, flush=True)
    objs = []
    if figure:
        objs.append(_figure(lo.x - 0.45))
        lo.x -= 0.7
        lo.z = min(lo.z, 0.0)
        hi.z = max(hi.z, 1.75)
    c = (lo + hi) / 2
    r = max((hi - lo).length / 2, 0.05)
    preview.ground(max(40, r * 20), color=(0.55, 0.53, 0.5)).location.z = min(lo.z, 0.0)
    preview.sun(rot=(50, 0, 30), energy=3.2)
    preview.area((c.x - r * 2.5, c.y - r * 3, c.z + r * 3), c, energy=60 * r * r + 20, size=r * 2)
    fov = 2 * math.atan(36 / 2 / 50)
    d = r / math.sin(fov / 2) * 1.02
    dirv = Vector((0.55, -1.0, 0.5)).normalized()
    cam = preview.camera(c + dirv * d, c + Vector((0, 0, -r * 0.06)), lens=50)
    cam.data.clip_start = d * 0.01
    name = os.path.basename(path)[:-4]
    _label(f"{name}  {size.x:.2f}x{size.y:.2f}x{size.z:.2f}m", cam, d * 0.5, fov)
    preview.render(out_png)


def contact_sheet(paths, out, cols):
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = np.ones((rows * h, cols * w, 4), np.float32)
    for i, img in enumerate(imgs):
        px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
        r, c = rows - 1 - i // cols, i % cols
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = px
    res = bpy.data.images.new("sheet", cols * w, rows * h, alpha=False)
    res.pixels.foreach_set(sheet.ravel())
    res.filepath_raw = out
    res.file_format = "JPEG" if out.lower().endswith((".jpg", ".jpeg")) else "PNG"
    bpy.context.scene.render.image_settings.quality = 88
    res.save(quality=88) if res.file_format == "JPEG" else res.save()
    return out


def main():
    args = parse_args()
    if args.names:
        names = [n for n in args.names.split(",") if n]
    elif args.kind == "items":
        names = list(items.ITEMS)
    elif args.kind == "quest":
        names = list(quest_props.QUEST)
    elif args.kind == "dressing":
        names = list(quest_props.DRESSING)
    else:
        names = list(quest_props.ASSETS)
    d = args.dir or os.path.join(ROOT, "godot", "assets", "items" if args.kind == "items" else "environment")
    tmp = os.path.join(os.path.dirname(os.path.abspath(args.out)), "_tiles")
    os.makedirs(tmp, exist_ok=True)
    tiles = []
    for n in names:
        p = os.path.join(d, n + ".glb")
        if not os.path.exists(p):
            print("missing", p)
            continue
        png = os.path.join(tmp, n + ".png")
        render_tile(p, png, args.tile, args.samples, figure=args.kind != "items")
        tiles.append(png)
    util.reset_scene()
    out = contact_sheet(tiles, args.out, min(args.cols, len(tiles)))
    for t in tiles:
        os.remove(t)
    os.rmdir(tmp)
    print("wrote", out)


if __name__ == "__main__":
    main()

"""Cycles turnaround renders of both cultivators (documentation screenshots).

    python blender/render_previews.py [--out docs/screenshots] [--samples 48]
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


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "screenshots"))
    ap.add_argument("--samples", type=int, default=48)
    return ap.parse_args(argv)


def contact_sheet(paths, out, cols):
    """Tile PNGs into one image using Blender's image API (no PIL needed)."""
    import numpy as np
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    rows = math.ceil(len(imgs) / cols)
    sheet = np.zeros((rows * h, cols * w, 4), np.float32)
    for i, img in enumerate(imgs):
        px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
        r, c = rows - 1 - i // cols, i % cols
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = px
    res = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    res.pixels.foreach_set(sheet.ravel())
    res.filepath_raw = out
    res.file_format = "PNG"
    res.save()
    for p in paths:
        os.remove(p)
    return out


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    tiles = []
    views = [("front", 0), ("three_quarter", 35), ("side", 90), ("back", 180)]
    for cfg in (characters.MALE, characters.FEMALE):
        arm, meshes, actions = characters.build_character(cfg)
        preview.setup(res=(480, 720), samples=args.samples, sky=(0.72, 0.78, 0.86))
        preview.sun(rot=(52, 0, 28), energy=3.2)
        preview.area((2.5, -3, 3), (0, 0, 1.2), energy=250)
        preview.ground(30, color=(0.52, 0.5, 0.47))
        arm.animation_data.action = bpy.data.actions["idle"]
        bpy.context.scene.frame_set(1)
        h = cfg["scale"]
        for name, deg in views:
            a = math.radians(deg)
            d = 4.3
            cam = preview.camera((math.sin(a) * d, -math.cos(a) * d, 1.05 * h), (0, 0, 0.88 * h), lens=50)
            path = os.path.join(args.out, f"_{cfg['name']}_{name}.png")
            preview.render(path)
            tiles.append(path)
            preview.remove([cam])
    out = contact_sheet(tiles, os.path.join(args.out, "characters_turnaround.png"), 4)
    print("wrote", out)


if __name__ == "__main__":
    main()

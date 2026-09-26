"""Cycles head-and-shoulders portraits for the dialogue box.

    python blender/render_portraits.py [--out godot/ui/portraits] [--only name,name] [--samples 48]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from xianxia import characters, preview  # noqa: E402

ROOT = os.path.dirname(HERE)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "godot", "ui", "portraits"))
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--size", type=int, default=256)
    return ap.parse_args(argv)


def main():
    args = parse_args()
    only = {s for s in args.only.split(",") if s}
    os.makedirs(args.out, exist_ok=True)
    for cfg in characters.HUMANOIDS:
        if only and cfg["name"] not in only:
            continue
        arm, meshes, actions = characters.build_character(cfg)
        preview.setup(res=(args.size, args.size), samples=args.samples, sky=(0.09, 0.1, 0.13), strength=0.6)
        s = cfg["scale"]
        head = (0.0, 0.0, 1.62 * s)
        # key, fill and a warm rim light
        preview.area((1.0 * s, -0.75 * s, 1.95 * s), head, energy=34, size=0.9, color=(1.0, 0.95, 0.9))
        preview.area((-0.9 * s, -0.8 * s, 1.6 * s), head, energy=9, size=1.2, color=(0.8, 0.88, 1.0))
        preview.area((-0.3 * s, 0.9 * s, 2.0 * s), head, energy=30, size=0.6, color=(1.0, 0.8, 0.55))
        arm.animation_data.action = bpy.data.actions["idle"]
        bpy.context.scene.frame_set(1)
        preview.camera((0.36 * s, -0.88 * s, 1.66 * s), (0.0, 0.0, 1.6 * s), lens=85)
        path = os.path.join(args.out, cfg["name"] + ".png")
        preview.render(path)
        print("wrote", path)


if __name__ == "__main__":
    main()

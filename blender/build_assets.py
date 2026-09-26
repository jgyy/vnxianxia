"""Build every xianxia GLB with headless Blender.

Run either with the Blender Python module (pip install bpy==5.2.2):
    python blender/build_assets.py [--only name,name] [--out godot/assets]
or with a Blender binary:
    blender --background --factory-startup --python blender/build_assets.py -- [args]
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from xianxia import catalog, characters, util  # noqa: E402

ROOT = os.path.dirname(HERE)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "godot", "assets"))
    ap.add_argument("--only", default="", help="comma separated asset names")
    ap.add_argument("--skip-characters", action="store_true")
    ap.add_argument("--skip-environment", action="store_true")
    return ap.parse_args(argv)


def main():
    args = parse_args()
    only = {s for s in args.only.split(",") if s}
    print(f"Blender {bpy.app.version_string}")
    t0 = time.time()
    built = []
    if not args.skip_characters:
        for cfg in (characters.MALE, characters.FEMALE):
            if only and cfg["name"] not in only:
                continue
            t = time.time()
            characters.build_character(cfg)
            path = util.export_glb(os.path.join(args.out, "characters", cfg["name"] + ".glb"), animations=True)
            built.append(path)
            print(f"  character {cfg['name']:<22} {time.time() - t:5.1f}s")
    if not args.skip_environment:
        for name, fn in catalog.ENVIRONMENT.items():
            if only and name not in only:
                continue
            t = time.time()
            util.reset_scene()
            fn()
            path = util.export_glb(os.path.join(args.out, "environment", name + ".glb"))
            built.append(path)
            print(f"  environment {name:<20} {time.time() - t:5.1f}s")
    print(f"built {len(built)} GLB files in {time.time() - t0:.1f}s -> {args.out}")


if __name__ == "__main__":
    main()

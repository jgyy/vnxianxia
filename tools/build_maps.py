#!/usr/bin/env python3
"""Generate every map scene under godot/scenes/maps/.

    python tools/build_maps.py [map_id ...]
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from maps import common, interiors  # noqa: E402

MAPS = ["sect", "bamboo_forest", "qingshi_town", "blood_abyss", "sky_isles"]


def main(argv):
    wanted = argv[1:] or (MAPS + list(interiors.BUILDERS))
    for map_id in wanted:
        if map_id in interiors.BUILDERS:
            common.write(interiors.BUILDERS[map_id]())
        else:
            mod = importlib.import_module(f"maps.{map_id}")
            common.write(mod.build())


if __name__ == "__main__":
    main(sys.argv)

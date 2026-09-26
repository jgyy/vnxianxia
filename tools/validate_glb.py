#!/usr/bin/env python3
"""Validate the generated GLB files (pure Python, no dependencies).

Checks the binary container, that every mesh has materials with textures, and
for characters that a skin and the required animations are present.

    python tools/validate_glb.py godot/assets
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_spec  # noqa: E402

MAX_BYTES = 12 * 1024 * 1024


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("not a glTF 2.0 binary")
    clen, ctype = struct.unpack_from("<I4s", data, 12)
    if ctype != b"JSON":
        raise ValueError("first chunk is not JSON")
    return json.loads(data[20:20 + clen]), len(data)


def check(path):
    gltf, size = read_glb(path)
    errors = []
    meshes = gltf.get("meshes", [])
    if not meshes:
        errors.append("no meshes")
    tris = 0
    for m in meshes:
        if "colonly" in m.get("name", ""):
            continue  # Godot import hint: collision-only mesh, no material needed
        for p in m["primitives"]:
            if "material" not in p:
                errors.append(f"mesh {m.get('name')} has a primitive without material")
            idx = p.get("indices")
            if idx is not None:
                tris += gltf["accessors"][idx]["count"] // 3
    textured = sum(1 for mat in gltf.get("materials", [])
                   if "baseColorTexture" in mat.get("pbrMetallicRoughness", {}))
    anims = {a["name"] for a in gltf.get("animations", [])}
    info = {
        "file": path.name,
        "kb": size // 1024,
        "meshes": len(meshes),
        "tris": tris,
        "materials": len(gltf.get("materials", [])),
        "textured": textured,
        "images": len(gltf.get("images", [])),
        "skins": len(gltf.get("skins", [])),
        "joints": sum(len(s["joints"]) for s in gltf.get("skins", [])),
        "animations": sorted(anims),
    }
    if textured == 0:
        errors.append("no textured materials")
    if size > MAX_BYTES:
        errors.append(f"file too large ({size} bytes)")
    if "characters" in path.parts:
        if not gltf.get("skins"):
            errors.append("character has no skin")
        required = set(world_spec.CREATURE_ANIMS.get(path.stem, world_spec.HUMANOID_ANIMS))
        missing = required - anims
        if missing:
            errors.append(f"missing animations: {sorted(missing)}")
        if path.stem in world_spec.PROTAGONISTS and len(anims) < world_spec.PROTAGONIST_MIN_ANIMS:
            errors.append(f"protagonist has {len(anims)} animations (< {world_spec.PROTAGONIST_MIN_ANIMS})")
    return info, errors


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else "godot/assets")
    files = sorted(root.rglob("*.glb"))
    if not files:
        print(f"no .glb files under {root}")
        return 1
    failed = 0
    for f in files:
        try:
            info, errors = check(f)
        except Exception as exc:  # noqa: BLE001
            info, errors = {"file": f.name}, [str(exc)]
        status = "OK  " if not errors else "FAIL"
        extra = f" anims={','.join(info['animations'])}" if info.get("animations") else ""
        print(f"{status} {f.relative_to(root)}  {info.get('kb', '?')} KB  "
              f"tris={info.get('tris', '?')} mats={info.get('materials', '?')} "
              f"joints={info.get('joints', 0)}{extra}")
        for e in errors:
            print(f"     - {e}")
        failed += bool(errors)
    print(f"{len(files) - failed}/{len(files)} GLB files valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

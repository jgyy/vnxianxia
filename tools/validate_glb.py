#!/usr/bin/env python3
"""Validate the generated GLB files (pure Python, no dependencies).

Checks the binary container, that every mesh has materials with textures, and
for characters that a skin and the required animations are present. Quest props
(world_spec.PROPS) must exist, carry collision, stand on their origin and stay
within a size budget; collectible item models (world_spec.ITEMS, under items/)
must exist, be collision-free, small, and rest on a bottom-centre origin.

    python tools/validate_glb.py godot/assets
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_spec  # noqa: E402

MAX_BYTES = 16 * 1024 * 1024  # heroes: 136 actions + 22 facial morph targets + 2k skin maps
PROP_MAX_BYTES = 1536 * 1024   # interactable quest props
PROP_STEP_OVER = 0.5           # props lower than this may be walked over without collision
ITEM_MAX_BYTES = 512 * 1024    # hand-held pickups
ITEM_MAX_SIZE = 0.6            # metres, any axis
QUEST_PROPS = {glb for glb in world_spec.PROPS.values() if glb}


def _qmat(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def _node_bounds(gltf):
    """World-space AABBs (glTF Y-up) of visible and collision-only mesh nodes."""
    nodes = gltf.get("nodes", [])
    out = {"visible": None, "collision": None, "collision_nodes": 0}

    def grow(key, pts):
        lo, hi = out[key] or ([1e9] * 3, [-1e9] * 3)
        for p in pts:
            lo = [min(a, b) for a, b in zip(lo, p)]
            hi = [max(a, b) for a, b in zip(hi, p)]
        out[key] = (lo, hi)

    def visit(i, rot, off, scl):
        n = nodes[i]
        t = n.get("translation", [0, 0, 0])
        r = _qmat(n.get("rotation", [0, 0, 0, 1]))
        sc = n.get("scale", [1, 1, 1])
        # compose parent (rot, off, uniform-ish scale) with this node
        t_w = [off[k] + sum(rot[k][j] * t[j] * scl[j] for j in range(3)) for k in range(3)]
        rot_w = [[sum(rot[a][k] * r[k][b] for k in range(3)) for b in range(3)] for a in range(3)]
        scl_w = [scl[k] * sc[k] for k in range(3)]
        if "mesh" in n:
            mesh = gltf["meshes"][n["mesh"]]
            col = "colonly" in n.get("name", "") or "colonly" in mesh.get("name", "")
            if col:
                out["collision_nodes"] += 1
            for prim in mesh["primitives"]:
                acc = gltf["accessors"][prim["attributes"]["POSITION"]]
                if "min" not in acc:
                    continue
                corners = [[acc["min"][0] if a else acc["max"][0], acc["min"][1] if b else acc["max"][1],
                            acc["min"][2] if c else acc["max"][2]] for a in (0, 1) for b in (0, 1) for c in (0, 1)]
                pts = [[t_w[k] + sum(rot_w[k][j] * p[j] * scl_w[j] for j in range(3)) for k in range(3)]
                       for p in corners]
                grow("collision" if col else "visible", pts)
        for c in n.get("children", []):
            visit(c, rot_w, t_w, scl_w)

    ident = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    scene = gltf.get("scenes", [{}])[gltf.get("scene", 0)] if gltf.get("scenes") else {"nodes": range(len(nodes))}
    for i in scene.get("nodes", []):
        visit(i, ident, [0, 0, 0], [1, 1, 1])
    return out


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("not a glTF 2.0 binary")
    clen, ctype = struct.unpack_from("<I4s", data, 12)
    if ctype != b"JSON":
        raise ValueError("first chunk is not JSON")
    return json.loads(data[20:20 + clen]), len(data)


def _buffer_refs(gltf):
    """Every bufferView an accessor (sparse data included) or image points at must exist
    and lie inside its buffer; a post-export rewrite that drops a view corrupts the file
    (Godot then fails the import with 'Sparse indices ... out of bounds')."""
    errors = []
    views, buffers = gltf.get("bufferViews", []), gltf.get("buffers", [])
    for vi, bv in enumerate(views):
        if bv.get("byteOffset", 0) + bv["byteLength"] > buffers[bv.get("buffer", 0)]["byteLength"]:
            errors.append(f"bufferView {vi} runs past the end of its buffer")
    refs = []
    for ai, a in enumerate(gltf.get("accessors", [])):
        if "bufferView" in a:
            refs.append((f"accessor {ai}", a["bufferView"]))
        if "sparse" in a:
            refs.append((f"accessor {ai} sparse indices", a["sparse"]["indices"]["bufferView"]))
            refs.append((f"accessor {ai} sparse values", a["sparse"]["values"]["bufferView"]))
    refs += [(f"image {i}", img["bufferView"]) for i, img in enumerate(gltf.get("images", [])) if "bufferView" in img]
    bad = [what for what, v in refs if not 0 <= v < len(views)]
    if bad:
        errors.append(f"{len(bad)} dangling bufferView references (first: {bad[0]})")
    return errors


def check(path):
    gltf, size = read_glb(path)
    errors = _buffer_refs(gltf)
    meshes = gltf.get("meshes", [])
    if not meshes:
        errors.append("no meshes")
    tris = 0
    col_meshes = {n["mesh"] for n in gltf.get("nodes", []) if "mesh" in n and "colonly" in n.get("name", "")}
    for mi, m in enumerate(meshes):
        if "colonly" in m.get("name", "") or mi in col_meshes:
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
    if "items" in path.parts:
        errors += _check_item(gltf, size)
    elif "environment" in path.parts and path.stem in QUEST_PROPS:
        errors += _check_quest_prop(gltf, size)
    return info, errors


def _check_item(gltf, size):
    errors = []
    b = _node_bounds(gltf)
    if b["collision_nodes"]:
        errors.append("item model has collision nodes (pickups must not block the player)")
    if size > ITEM_MAX_BYTES:
        errors.append(f"item model too large ({size // 1024} KB > {ITEM_MAX_BYTES // 1024} KB)")
    if b["visible"]:
        lo, hi = b["visible"]
        ext = [h - l for l, h in zip(lo, hi)]
        if max(ext) > ITEM_MAX_SIZE:
            errors.append(f"item model is {max(ext):.2f} m across (> {ITEM_MAX_SIZE} m hand-held)")
        if lo[1] < -0.03 or lo[1] > 0.05:
            errors.append(f"item origin is not at its bottom (lowest point y = {lo[1]:.3f})")
        cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
        if abs(cx) > 0.1 or abs(cz) > 0.1:
            errors.append(f"item origin is off-centre by ({cx:.2f}, {cz:.2f})")
    return errors


def _check_quest_prop(gltf, size):
    errors = []
    b = _node_bounds(gltf)
    tall = b["visible"] and b["visible"][1][1] - b["visible"][0][1] > PROP_STEP_OVER
    if tall and not b["collision_nodes"]:
        errors.append("quest prop has no '-colonly'/'-convcolonly' collision (the player walks through it)")
    if size > PROP_MAX_BYTES:
        errors.append(f"quest prop too large ({size // 1024} KB > {PROP_MAX_BYTES // 1024} KB)")
    if b["visible"] and b["visible"][0][1] > 0.05:
        errors.append(f"quest prop floats: lowest point y = {b['visible'][0][1]:.2f} m above its origin")
    return errors


def missing_models(root):
    """Quest-prop and item GLBs the world spec expects but the asset tree lacks."""
    missing = []
    if (root / "environment").is_dir():
        missing += [f"environment/{g}.glb" for g in sorted(QUEST_PROPS)
                    if not (root / "environment" / f"{g}.glb").exists()]
        missing += [f"items/{i}.glb" for i in sorted(world_spec.ITEMS)
                    if not (root / "items" / f"{i}.glb").exists()]
    return missing


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
    missing = missing_models(root)
    for m in missing:
        print(f"FAIL {m}  missing (named in tools/world_spec.py)")
    print(f"{len(files) - failed}/{len(files)} GLB files valid, {len(missing)} missing")
    return 1 if failed or missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

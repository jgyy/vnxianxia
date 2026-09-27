#!/usr/bin/env python3
"""Find z-fighting inside GLB files: coplanar, overlapping triangles.

Two visible triangles z-fight when they lie in the same plane (within --eps
metres), face the same way (or either material is double-sided), and overlap
by more than --area square metres. Collision-only nodes are ignored.

    python tools/zfight_glb.py godot/assets/environment/notice_board.glb ...
    python tools/zfight_glb.py --names notice_board,letter godot/assets

Prints per file: the number of overlapping pairs and, per material pair, the
count, total overlap area and one example location (Blender coordinates:
x, -z, y of glTF, so it matches the builder source).
"""
import argparse
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

CTYPES = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    data = Path(path).read_bytes()
    clen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + clen])
    off = 20 + clen
    blen = struct.unpack_from("<I", data, off)[0]
    return gltf, data[off + 8:off + 8 + blen]


def accessor(gltf, binary, i):
    acc = gltf["accessors"][i]
    view = gltf["bufferViews"][acc["bufferView"]]
    dt = np.dtype(CTYPES[acc["componentType"]])
    n = NCOMP[acc["type"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", 0)
    if stride and stride != dt.itemsize * n:
        raw = np.frombuffer(binary, np.uint8, stride * acc["count"], start).reshape(acc["count"], stride)
        return raw[:, :dt.itemsize * n].copy().view(dt).reshape(acc["count"], n)
    return np.frombuffer(binary, dt, acc["count"] * n, start).reshape(acc["count"], n)


def _local(node):
    if "matrix" in node:
        return np.array(node["matrix"], np.float64).reshape(4, 4).T
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * np.array(node.get("scale", [1, 1, 1]))
    m[:3, 3] = node.get("translation", [0, 0, 0])
    return m


def triangles(gltf, binary):
    """World-space triangles (N, 3, 3), material index per triangle, double-sided flags per material."""
    nodes = gltf.get("nodes", [])
    tris, mats, owner = [], [], []

    def visit(i, parent):
        n = nodes[i]
        m = parent @ _local(n)
        if "mesh" in n and "colonly" not in n.get("name", ""):
            mesh = gltf["meshes"][n["mesh"]]
            if "colonly" not in mesh.get("name", ""):
                for prim in mesh["primitives"]:
                    if prim.get("mode", 4) != 4:
                        continue
                    pos = accessor(gltf, binary, prim["attributes"]["POSITION"]).astype(np.float64)
                    pos = pos @ m[:3, :3].T + m[:3, 3]
                    idx = (accessor(gltf, binary, prim["indices"]).ravel() if "indices" in prim
                           else np.arange(len(pos)))
                    t = pos[idx.reshape(-1, 3)]
                    tris.append(t)
                    mats.append(np.full(len(t), prim.get("material", -1)))
                    owner.extend([n.get("name", "?")] * len(t))
        for c in n.get("children", []):
            visit(c, m)

    scene = gltf["scenes"][gltf.get("scene", 0)]
    for i in scene["nodes"]:
        visit(i, np.eye(4))
    if not tris:
        return np.zeros((0, 3, 3)), np.zeros(0, int), [], []
    ds = [bool(mm.get("doubleSided")) for mm in gltf.get("materials", [])]
    return np.concatenate(tris), np.concatenate(mats), ds, owner


def _clip(poly, a, b):
    """Clip polygon by the half-plane left of edge a->b (2-D)."""
    out = []
    ex, ey = b - a
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        sp = ex * (p[1] - a[1]) - ey * (p[0] - a[0])
        sq = ex * (q[1] - a[1]) - ey * (q[0] - a[0])
        if sp >= 0:
            out.append(p)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append(p + (q - p) * t)
    return out


def _area(poly):
    if len(poly) < 3:
        return 0.0
    p = np.array(poly)
    return 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))


def overlap_area(t1, t2, u, v):
    a = [np.array([p @ u, p @ v]) for p in t1]
    b = [np.array([p @ u, p @ v]) for p in t2]
    # make both counter-clockwise
    for tri in (a, b):
        if (tri[1] - tri[0])[0] * (tri[2] - tri[0])[1] - (tri[1] - tri[0])[1] * (tri[2] - tri[0])[0] < 0:
            tri.reverse()
    poly = list(a)
    for i in range(3):
        poly = _clip(poly, b[i], b[(i + 1) % 3])
        if not poly:
            return 0.0
    return _area(poly)


def scan(path, eps=0.001, min_area=1e-5, detail=0):
    gltf, binary = read_glb(path)
    tris, mats, ds, owner = triangles(gltf, binary)
    if len(tris) == 0:
        return 0, {}
    e1, e2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    area = np.linalg.norm(nrm, axis=1) * 0.5
    ok = area > min_area
    nrm[ok] /= (2 * area[ok])[:, None]
    # canonical plane key: flip so the first significant component is positive
    sign = np.where(np.abs(nrm[:, 0]) > 1e-6, np.sign(nrm[:, 0]),
                    np.where(np.abs(nrm[:, 1]) > 1e-6, np.sign(nrm[:, 1]), np.sign(nrm[:, 2])))
    cn = nrm * sign[:, None]
    d = np.einsum("ij,ij->i", cn, tris[:, 0])
    lo, hi = tris.min(axis=1), tris.max(axis=1)
    buckets = defaultdict(list)
    for i in np.nonzero(ok)[0]:
        key = tuple(np.round(cn[i] * 50).astype(int)) + (int(np.floor(d[i] / (eps * 4))),)
        buckets[key].append(i)
    pairs = 0
    report = {}
    seen = set()
    keys = list(buckets)
    for key in keys:
        cand = list(buckets[key])
        nb = key[:3] + (key[3] + 1,)
        cand_n = buckets.get(nb, [])
        group = cand + list(cand_n)
        if len(group) < 2:
            continue
        g = np.array(group)
        for ii, i in enumerate(cand):
            js = g[ii + 1:]
            js = js[(np.abs(d[js] - d[i]) < eps) & (np.einsum("ij,j->i", cn[js], cn[i]) > 0.9995)]
            js = js[np.all(lo[js] <= hi[i] + 1e-6, axis=1) & np.all(hi[js] >= lo[i] - 1e-6, axis=1)]
            for j in js:
                if (i, j) in seen or i == j:
                    continue
                seen.add((i, j))
                same_facing = np.dot(nrm[i], nrm[j]) > 0
                mi, mj = int(mats[i]), int(mats[j])
                dbl = (mi >= 0 and ds[mi]) or (mj >= 0 and ds[mj])
                if not same_facing and not dbl:
                    continue
                u = e1[i] / np.linalg.norm(e1[i])
                v = np.cross(cn[i], u)
                a = overlap_area(tris[i], tris[j], u, v)
                if a <= min_area:
                    continue
                pairs += 1
                names = sorted(f"{owner[t]}[{gltf['materials'][m]['name'] if m >= 0 else '-'}]"
                               for t, m in ((i, mi), (j, mj)))
                k = " | ".join(names)
                c = tris[i].mean(axis=0)
                r = report.setdefault(k, [0, 0.0, (round(float(c[0]), 3), round(float(-c[2]), 3),
                                                   round(float(c[1]), 3))])
                r[0] += 1
                r[1] += a
                if detail and pairs <= detail:
                    print(f"      pair at {tuple(round(float(x), 3) for x in (c[0], -c[2], c[1]))} "
                          f"normal {tuple(round(float(x), 2) for x in (nrm[i][0], -nrm[i][2], nrm[i][1]))} "
                          f"area {a * 1e4:.1f} cm2  {k}")
    return pairs, report


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--names", default="", help="comma separated GLB stems to pick under the given directories")
    ap.add_argument("--eps", type=float, default=0.001)
    ap.add_argument("--area", type=float, default=1e-5)
    ap.add_argument("--detail", type=int, default=0, help="print the first N pairs (Blender coordinates)")
    ap.add_argument("-q", "--quiet", action="store_true", help="one line per file")
    args = ap.parse_args(argv)
    names = {n for n in args.names.split(",") if n}
    files = []
    for p in map(Path, args.paths):
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*.glb")) if not names or f.stem in names]
        else:
            files.append(p)
    total = 0
    for f in files:
        pairs, rep = scan(f, args.eps, args.area, args.detail)
        total += pairs
        print(f"{'ZFIGHT' if pairs else 'ok    '} {f.name:<28} {pairs} pairs")
        if not args.quiet:
            for k, (n, a, c) in sorted(rep.items(), key=lambda kv: -kv[1][1]):
                print(f"         {n:4d} pairs {a * 1e4:8.1f} cm2  {k}  e.g. at {c}")
    print(f"total {total} coplanar overlapping pairs in {len(files)} files")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

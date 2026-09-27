"""Classify tools/zfight_glb.py pairs into hidden / invisible (same texel) / visible.

    python tools/maps/zfight_visible.py [--detail N] godot/assets/environment/<asset>.glb ...

hidden:    down-facing at the asset's ground plane or resting within 3 cm on an up-facing surface, or
           the point 2 cm in front of the overlap lies
           inside a closed solid of the asset (ray parity on 3 axes, majority)
same:      same material, same UV (mod 1) and same normal at the overlap centre: identical pixels
visible:   everything else
"""
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import zfight_glb as Z  # noqa: E402


def tris_uv(gltf, binary):
    nodes = gltf.get("nodes", [])
    T, U, M, O = [], [], [], []

    def visit(i, parent):
        n = nodes[i]
        m = parent @ Z._local(n)
        if "mesh" in n and "colonly" not in n.get("name", ""):
            mesh = gltf["meshes"][n["mesh"]]
            if "colonly" not in mesh.get("name", ""):
                for prim in mesh["primitives"]:
                    if prim.get("mode", 4) != 4:
                        continue
                    pos = Z.accessor(gltf, binary, prim["attributes"]["POSITION"]).astype(np.float64)
                    pos = pos @ m[:3, :3].T + m[:3, 3]
                    uv = (Z.accessor(gltf, binary, prim["attributes"]["TEXCOORD_0"]).astype(np.float64)
                          if "TEXCOORD_0" in prim["attributes"] else np.zeros((len(pos), 2)))
                    idx = (Z.accessor(gltf, binary, prim["indices"]).ravel() if "indices" in prim
                           else np.arange(len(pos))).reshape(-1, 3)
                    T.append(pos[idx])
                    U.append(uv[idx])
                    M.append(np.full(len(idx), prim.get("material", -1)))
                    O.extend([n.get("name", "?")] * len(idx))
        for c in n.get("children", []):
            visit(c, m)

    for i in gltf["scenes"][gltf.get("scene", 0)]["nodes"]:
        visit(i, np.eye(4))
    return np.concatenate(T), np.concatenate(U), np.concatenate(M), O


def bary(t, p):
    v0, v1, v2 = t[1] - t[0], t[2] - t[0], p - t[0]
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return np.array([1 / 3, 1 / 3, 1 / 3])
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return np.array([1 - v - w, v, w])


def inside(tris, p):
    """Majority of 3 axis rays with odd crossing counts."""
    votes = 0
    for ax in range(3):
        a, b = [k for k in range(3) if k != ax]
        # triangles whose projection on (a, b) contains (p[a], p[b]) and lie beyond p on ax
        x0, y0 = tris[:, 0, a] - p[a], tris[:, 0, b] - p[b]
        x1, y1 = tris[:, 1, a] - p[a], tris[:, 1, b] - p[b]
        x2, y2 = tris[:, 2, a] - p[a], tris[:, 2, b] - p[b]
        c0 = x0 * y1 - x1 * y0
        c1 = x1 * y2 - x2 * y1
        c2 = x2 * y0 - x0 * y2
        hit = ((c0 > 0) & (c1 > 0) & (c2 > 0)) | ((c0 < 0) & (c1 < 0) & (c2 < 0))
        s = c0 + c1 + c2
        s = np.where(np.abs(s) < 1e-15, 1e-15, s)
        depth = (c1 * tris[:, 0, ax] + c2 * tris[:, 1, ax] + c0 * tris[:, 2, ax]) / s
        n = int(np.count_nonzero(hit & (depth > p[ax])))
        votes += n % 2
    return votes >= 2


def resting(tris, nrm, p):
    """True when an up-facing surface lies within 3 cm below p (a face resting on something)."""
    a, b, ax = 0, 2, 1
    x0, y0 = tris[:, 0, a] - p[a], tris[:, 0, b] - p[b]
    x1, y1 = tris[:, 1, a] - p[a], tris[:, 1, b] - p[b]
    x2, y2 = tris[:, 2, a] - p[a], tris[:, 2, b] - p[b]
    c0 = x0 * y1 - x1 * y0
    c1 = x1 * y2 - x2 * y1
    c2 = x2 * y0 - x0 * y2
    hit = ((c0 >= 0) & (c1 >= 0) & (c2 >= 0)) | ((c0 <= 0) & (c1 <= 0) & (c2 <= 0))
    s = c0 + c1 + c2
    s = np.where(np.abs(s) < 1e-15, 1e-15, s)
    depth = (c1 * tris[:, 0, ax] + c2 * tris[:, 1, ax] + c0 * tris[:, 2, ax]) / s
    return bool(np.any(hit & (nrm[:, 1] > 0.5) & (depth <= p[ax] + 0.002) & (depth >= p[ax] - 0.03)))


def classify(path, detail=0, eps=0.001, min_area=1e-5):
    gltf, binary = Z.read_glb(path)
    tris, uvs, mats, owner = tris_uv(gltf, binary)
    e1, e2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    area = np.linalg.norm(nrm, axis=1) * 0.5
    ok = area > min_area
    nrm[ok] /= (2 * area[ok])[:, None]
    sign = np.where(np.abs(nrm[:, 0]) > 1e-6, np.sign(nrm[:, 0]),
                    np.where(np.abs(nrm[:, 1]) > 1e-6, np.sign(nrm[:, 1]), np.sign(nrm[:, 2])))
    cn = nrm * sign[:, None]
    d = np.einsum("ij,ij->i", cn, tris[:, 0])
    lo, hi = tris.min(axis=1), tris.max(axis=1)
    ground = tris[:, :, 1].min()
    buckets = defaultdict(list)
    for i in np.nonzero(ok)[0]:
        buckets[tuple(np.round(cn[i] * 50).astype(int)) + (int(np.floor(d[i] / (eps * 4))),)].append(i)
    counts = defaultdict(int)
    vis = defaultdict(lambda: [0, 0.0, None])
    seen = set()
    for key, cand in buckets.items():
        group = cand + buckets.get(key[:3] + (key[3] + 1,), [])
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
                mi, mj = int(mats[i]), int(mats[j])
                ds = [bool(mm.get("doubleSided")) for mm in gltf.get("materials", [])]
                dbl = (mi >= 0 and ds[mi]) or (mj >= 0 and ds[mj])
                if np.dot(nrm[i], nrm[j]) <= 0 and not dbl:
                    continue
                u = e1[i] / np.linalg.norm(e1[i])
                v = np.cross(cn[i], u)
                # overlap polygon centroid
                a2 = [np.array([p @ u, p @ v]) for p in tris[i]]
                b2 = [np.array([p @ u, p @ v]) for p in tris[j]]
                for tri in (a2, b2):
                    if (tri[1] - tri[0])[0] * (tri[2] - tri[0])[1] - (tri[1] - tri[0])[1] * (tri[2] - tri[0])[0] < 0:
                        tri.reverse()
                poly = list(a2)
                for k in range(3):
                    poly = Z._clip(poly, b2[k], b2[(k + 1) % 3])
                    if not poly:
                        break
                ar = Z._area(poly) if poly else 0.0
                if ar <= min_area:
                    continue
                c2 = np.mean(poly, axis=0)
                c = cn[i] * d[i] + u * c2[0] + v * c2[1]
                if nrm[i][1] < -0.9 and (c[1] < max(ground, 0.0) + 0.03 or resting(tris, nrm, c)):
                    counts["hidden"] += 1
                    continue
                if inside(tris, c + nrm[i] * 0.02):
                    counts["hidden"] += 1
                    continue
                if mi == mj:
                    ua = bary(tris[i], c) @ uvs[i]
                    ub = bary(tris[j], c) @ uvs[j]
                    du = (ua - ub) - np.round(ua - ub)
                    if np.all(np.abs(du) < 0.004):
                        counts["same"] += 1
                        continue
                counts["visible"] += 1
                mn = lambda m: gltf["materials"][m]["name"] if m >= 0 else "-"
                k = " | ".join(sorted([f"{owner[i]}[{mn(mi)}]", f"{owner[j]}[{mn(mj)}]"]))
                r = vis[k]
                r[0] += 1
                r[1] += ar
                if r[2] is None:
                    r[2] = (tuple(round(float(x), 2) for x in (c[0], -c[2], c[1])),
                            tuple(round(float(x), 2) for x in (nrm[i][0], -nrm[i][2], nrm[i][1])))
    return counts, vis


if __name__ == "__main__":
    args = sys.argv[1:]
    detail = 0
    if args and args[0] == "--detail":
        detail = int(args[1])
        args = args[2:]
    tot = defaultdict(int)
    for f in args:
        counts, vis = classify(f)
        for k, v in counts.items():
            tot[k] += v
        name = f.split("/")[-1]
        print(f"{name:<30} visible {counts['visible']:5d}  same {counts['same']:5d}  hidden {counts['hidden']:5d}")
        if detail:
            for k, (n, a, ex) in sorted(vis.items(), key=lambda kv: -kv[1][1])[:detail]:
                print(f"      {n:4d} {a * 1e4:9.1f} cm2  {k}  at {ex}")
    print("TOTAL", dict(tot))

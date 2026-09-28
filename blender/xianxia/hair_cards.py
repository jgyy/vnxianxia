"""Hair cards: strands -> alpha-tested ribbons, the scalp cap, and hair skinning.

A card is a ribbon following a (child) strand.  Its face points away from the hair
volume (radially from the head near the scalp, from the bundle's axis further out),
it is randomly twisted a little so the stack does not read as flat shingles, and it
tapers toward the tip.  Vertex normals are overridden to the volume's outward
direction, so the cards shade like one continuous mass of hair rather than a set
of flat planes (the standard trick for card hair), in Cycles and in Godot alike.

UVs: u spans the card's atlas strip (randomly mirrored), v runs root (0) -> tip (1).

Skinning is computed per vertex from its rest position, with the same bone set the
animations drive (head, hair.1-3, neck, chest): see `hair_weights`.
"""
import math

import bmesh
import bpy
import numpy as np

from . import hair_groom as G
from . import util

BONES = ("head", "hair.1", "hair.2", "hair.3", "neck", "chest")


class Bundle:
    """A batch of card centre-lines sharing a strip family, width and skinning kind."""

    def __init__(self, P, width, strips, kind="free", tip=0.55, root=0.8, twist=0.35, axis=None,
                 v0=0.0):
        self.P = np.asarray(P, np.float32)
        C = self.P.shape[0]
        self.width = np.broadcast_to(np.asarray(width, np.float32), (C,)).copy()
        self.strips = [strips] * C if isinstance(strips, str) else list(strips)
        self.kind = kind
        self.tip, self.root, self.twist = tip, root, twist
        self.axis = axis          # optional (M, 3) centre curve the cards face away from
        self.v0 = v0              # texture v at the root (short cards use the strip's ends)


def card_mesh(bundles, head, layout, rng, name="HairCards", mat=None):
    """Build one mesh object from bundles. Returns (object, per-vertex kind array, rest positions)."""
    pos, nrm, uvs, faces, kinds = [], [], [], [], []
    base = 0
    for b in bundles:
        P = b.P
        C, M, _ = P.shape
        if C == 0:
            continue
        T = G.norm(np.gradient(P, axis=1))
        # outward reference: radial from the head near the scalp, from the bundle axis further out
        axis = b.axis if b.axis is not None else P.mean(axis=0)
        o_axis = P - axis[None]
        o_head = P - head.c
        near = G.smooth(1 - head.height(P) / 0.05)[..., None]
        O = G.norm(o_head * near + G.norm(o_axis) * np.linalg.norm(o_head, axis=-1, keepdims=True) * (1 - near))
        side = np.cross(T, O)
        bad = np.linalg.norm(side, axis=-1) < 1e-4
        side[bad] = np.cross(T[bad], np.array([0, 0, 1.0], np.float32))
        side = G.norm(side)
        ang = rng.normal(0, b.twist, (C, 1, 1)).astype(np.float32)
        side = side * np.cos(ang) + np.cross(T, side) * np.sin(ang)
        face = G.norm(np.cross(side, T))
        t = np.linspace(0, 1, M, dtype=np.float32)[None, :]
        prof = (b.root + (1 - b.root) * G.smooth(t / 0.25)) * (1 - (1 - b.tip) * G.smooth((t - 0.45) / 0.55))
        w = (b.width[:, None] * prof)[..., None]
        left = P - side * w * 0.5
        right = P + side * w * 0.5
        V = np.stack([left, right], axis=2).reshape(-1, 3)
        n_out = G.norm(O * 0.7 + face * 0.3)
        N = np.repeat(n_out[:, :, None, :], 2, axis=2).reshape(-1, 3)
        # uv: strip columns (randomly mirrored), v root -> tip
        u0 = np.array([layout[s][0] for s in b.strips], np.float32)
        u1 = np.array([layout[s][1] for s in b.strips], np.float32)
        flip = rng.random(C) < 0.5
        ua, ub = np.where(flip, u1, u0), np.where(flip, u0, u1)
        vt = np.broadcast_to(b.v0 + t * (1 - b.v0), (C, M))
        UV = np.stack([np.stack([np.repeat(ua[:, None], M, 1), vt], -1),
                       np.stack([np.repeat(ub[:, None], M, 1), vt], -1)], axis=2).reshape(-1, 2)
        idx = base + np.arange(C * M * 2).reshape(C, M, 2)
        q = np.stack([idx[:, :-1, 0], idx[:, :-1, 1], idx[:, 1:, 1], idx[:, 1:, 0]], -1).reshape(-1, 4)
        pos.append(V)
        nrm.append(N)
        uvs.append(UV)
        faces.append(q)
        kinds.append(np.full(len(V), b.kind, dtype=object))
        base += len(V)
    V = np.concatenate(pos)
    Q = np.concatenate(faces)
    obj = _mesh(name, V, Q, np.concatenate(uvs), np.concatenate(nrm), mat)
    return obj, np.concatenate(kinds), V


def bmesh_uv_name():
    """Name bmesh gives a new UV layer (the rest of the character is built with bmesh).

    The card mesh must use the same name, or joining it with the other parts leaves
    two UV layers and the cards sample the wrong (empty) one.
    """
    bm = bmesh.new()
    bm.loops.layers.uv.verify()
    me = bpy.data.meshes.new("uvname")
    bm.to_mesh(me)
    bm.free()
    name = me.uv_layers[0].name if me.uv_layers else "UVMap"
    bpy.data.meshes.remove(me)
    return name


def _mesh(name, V, Q, UV, N, mat):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.loops.add(Q.size)
    me.loops.foreach_set("vertex_index", Q.astype(np.int32).ravel())
    me.polygons.add(len(Q))
    me.polygons.foreach_set("loop_start", (np.arange(len(Q)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(Q), 4, np.int32))
    uv = me.uv_layers.new(name=bmesh_uv_name())
    uv.data.foreach_set("uv", UV[Q.ravel()].astype(np.float32).ravel())
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices([tuple(n) for n in N])
    obj = bpy.data.objects.new(name, me)
    util.link(obj)
    if mat is not None:
        me.materials.append(mat)
    return obj


# --------------------------------------------------------------------------
# scalp cap
# --------------------------------------------------------------------------
def scalp_cap(head, mat, lift=0.0015, margin=0.03, lo=None, cols=96, rows=20, name="HairCap"):
    """Opaque dark shell over the scalp, just inside the hairline, under the cards.

    lo(lon) optionally overrides the lower edge (unit-sphere z) e.g. for a headscarf.
    UV u = longitude, v = height, so the cap's streak texture runs toward the crown.
    """
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    lon = np.linspace(-math.pi, math.pi, cols, endpoint=False).astype(np.float32)
    z0 = head.hairline(np.abs(lon)) + margin if lo is None else np.array([lo(a) for a in lon], np.float32)
    grid = []
    for j in range(rows + 1):
        t = j / rows
        z = np.minimum(z0 + (0.995 - z0) * t ** 0.85, 0.995)
        p = head.point(lon, np.arcsin(z), lift + 0.002 * t)
        grid.append([bm.verts.new(tuple(q)) for q in p])
    for j in range(rows):
        for i in range(cols):
            i2 = (i + 1) % cols
            f = bm.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[uv].uv = (a / cols * 6.0, b / rows * 1.5)
    # close the crown with a fan of triangles (each with real UVs, no degenerate n-gon)
    top = bm.verts.new(tuple(head.point(np.float32(0), np.float32(math.pi / 2), lift + 0.002)))
    for i in range(cols):
        i2 = (i + 1) % cols
        f = bm.faces.new((grid[rows][i], grid[rows][i2], top))
        for loop, co in zip(f.loops, ((i / cols * 6.0, 1.5), ((i + 1) / cols * 6.0, 1.5),
                                      ((i + 0.5) / cols * 6.0, 1.62))):
            loop[uv].uv = co
    return util.mesh_object(name, bm, mat)


# --------------------------------------------------------------------------
# skinning
# --------------------------------------------------------------------------
def _chain(z, chain):
    """Piecewise smooth blend along [(z, bone index), ...] (z descending)."""
    W = np.zeros((len(z), len(BONES)), np.float32)
    zs = np.array([c[0] for c in chain], np.float32)
    for k, (zk, bk) in enumerate(chain):
        if k == 0:
            w = G.smooth((z - zs[1]) / (zk - zs[1]))
        elif k == len(chain) - 1:
            w = G.smooth((zs[k - 1] - z) / (zs[k - 1] - zk))
        else:
            up = G.smooth((zs[k - 1] - z) / (zs[k - 1] - zk))
            down = G.smooth((z - zs[k + 1]) / (zk - zs[k + 1]))
            w = np.where(z > zk, up, down)
        W[:, bk] += w
    return W


def hair_weights(V, kinds, s, head_c):
    """(V, len(BONES)) weights.

    head  - rigid with the head (scalp cards, bangs, buns, beards).
    free  - hanging hair and ponytail tails: head down to the nape, then the hair.1-3
            chain by height (so it swings with the existing hair animation); strands that
            fall in FRONT of the shoulders follow the chest instead of the back chain, which
            would otherwise drag them through the torso.
    side  - face-framing locks: head blending to chest toward the collarbone.
    """
    z = V[:, 2] / s
    y = V[:, 1] / s
    W = np.zeros((len(V), len(BONES)), np.float32)
    W[:, 0] = 1.0
    chain = _chain(z, [(1.62, 0), (1.47, 1), (1.29, 2), (1.10, 3)])
    side_f = (G.smooth((1.56 - z) / 0.2) * 0.65)
    side = np.zeros_like(W)
    side[:, 0] = 1 - side_f
    side[:, 5] = side_f
    front = G.smooth((head_c[1] / s - 0.035 - y) / 0.05) * G.smooth((1.56 - z) / 0.08)
    free = chain * (1 - front[:, None]) + side * front[:, None]
    W = np.where((kinds == "free")[:, None], free, W)
    W = np.where((kinds == "side")[:, None], side, W)
    # glTF / Godot skin with at most 4 influences: keep the strongest four
    drop = np.argsort(W, axis=1)[:, :-4]
    np.put_along_axis(W, drop, 0.0, axis=1)
    return W / W.sum(1, keepdims=True)


def assign_weights(obj, W):
    """Write a (V, B) weight matrix into vertex groups, batching equal weights."""
    q = np.round(W * 64) / 64
    for b, name in enumerate(BONES):
        col = q[:, b]
        if not (col > 0).any():
            continue
        vg = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        for val in np.unique(col[col > 0]):
            vg.add(np.nonzero(col == val)[0].tolist(), float(val), "REPLACE")

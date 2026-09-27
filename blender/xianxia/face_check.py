"""Geometric self-checks of a built head (run by face_head after every build).

The head is procedural, so a parameter tweak for one NPC can silently break
another; these checks catch the defects that are easy to miss in a portrait:

* lid seal   - the posterior lid margin must hug the globe (no air gap, no
               eyeball poking through), measured where the margin lies over it;
* blink seal - with blink = 1 the upper and lower margins must meet;
* teeth      - no tooth or gum vertex may stand in front of the closed lips / skin;
* symmetry   - the skin mesh must mirror across x = 0 (shape keys rely on it);
* winding    - skin faces must face away from the head's inside, eyeballs outward;
* folds      - no skin edge may fold sharply outside the explicit lid / lip loops.

``check(fh)`` returns a list of human-readable problems (empty = fine);
face_head prints them as warnings so a build never fails on a cosmetic issue.
"""
import numpy as np

from . import face_chart as fc
from . import face_landmarks as fl
from .face_eyes import EyeLids

LID_GAP_MM = 0.45
BLINK_GAP_MM = 0.6
TOOTH_CLEARANCE_MM = 0.3
MIRROR_MM = 0.05
FOLD_DEG = 110.0      # the folds found were 115-179 deg; a big nose tip on the coarse grid bends ~100


def lid_seal(fh):
    """Largest gap between the posterior lid margin and the eyeball sphere (mm), per eye."""
    out = {}
    for kind, d in fh.mesh.ogrids:
        if kind != "eye":
            continue
        side = d["side"]
        g = fl.eye_geometry(fh.p, side)
        c = np.array(g["centre"])
        margin = fh.rest_mm[d["rings"][EyeLids.MARGIN_RING]]
        rel = margin - c
        # only where the margin lies over the globe (the canthi fold past its silhouette)
        over = np.hypot(rel[:, 0], rel[:, 2]) < g["R"] * 0.9
        gap = np.abs(np.linalg.norm(rel[over], axis=1) - g["R"])
        out[side] = float(gap.max()) if len(gap) else 0.0
    return out


def blink_seal(fh, shapes):
    """Largest distance between the closed upper and lower margins (mm), per eye."""
    out = {}
    for kind, d in fh.mesh.ogrids:
        if kind != "eye":
            continue
        side = d["side"]
        key = shapes[f"blink_{'L' if side > 0 else 'R'}"]
        ids = np.array(d["rings"][EyeLids.MARGIN_RING])
        closed = fh.rest_mm[ids] + key[ids]
        s = np.asarray(d["s"])
        upper = closed[(s > 0.08) & (s < 0.42)]
        # lower margin as a polyline from the medial to the lateral canthus (both included)
        order = np.argsort(np.where(s == 0.0, 1.0, s))
        low = closed[order][s[order] >= 0.5]
        low = np.vstack([low, closed[s == 0.0]])
        a, b = low[:-1], low[1:]
        ab = b - a
        t = np.einsum("pk,sk->ps", upper, ab) - np.einsum("sk,sk->s", a, ab)
        t = np.clip(t / np.maximum(np.einsum("sk,sk->s", ab, ab), 1e-12), 0.0, 1.0)
        near = a[None] + t[..., None] * ab[None]
        out[side] = float(np.linalg.norm(upper[:, None] - near, axis=-1).min(axis=1).max())
    return out


def teeth_clearance(fh):
    """Most negative clearance (mm) of the teeth / gums behind the sculpted face surface."""
    mp = fh.mouth_parts
    ids = np.concatenate([mp["upper"], mp["lower"]])
    P = fh.rest_mm[ids]
    front = fh.surf.front_y(P[:, 0], P[:, 2])
    return float((P[:, 1] - front).min())


def mirror_error(fh):
    """Largest distance from a skin vertex to the nearest vertex of the mirrored skin (mm)."""
    from mathutils import kdtree
    skin = fh.rest_mm[fh.range("skin")]
    tree = kdtree.KDTree(len(skin))
    for i, q in enumerate(skin):
        tree.insert(q.tolist(), i)
    tree.balance()
    return max(tree.find((-q[0], q[1], q[2]))[2] for q in skin)


def inward_faces(fh):
    """Number of skin faces (outside the O-grid cavities) whose normal points into the head."""
    B = fh.mesh.B
    bad = 0
    for verts, slot, group in B.faces:
        if slot != 0 or group != 0:
            continue
        P = [B.pos[v] for v in verts]
        n = sum(np.cross(P[k], P[(k + 1) % len(P)]) for k in range(len(P)))    # Newell normal
        cen = sum(P) / len(P)
        if cen[2] < fc.NECK_TOP_Z:                   # neck rows face away from the neck axis
            out = np.array([cen[0], cen[1] - fc.neck_axis_y(cen[2]), 0.0])
        else:
            out = cen - fc.ORIGIN
        if np.dot(n, out) < 0:
            bad += 1
    return bad


def folds(fh):
    """Skin edges between two faces bent by more than FOLD_DEG, away from the explicit
    lid / lip / nostril loops (which crease on purpose).  Returns (count, worst angle, where).

    Catches overlapping blend loops: a fold is invisible in wireframe counts but reads as a
    hard-edged box in any lit render."""
    B = fh.mesh.B
    P = np.asarray(B.pos)
    explicit = set()
    for kind, d in fh.mesh.ogrids:
        # the nostril O-grid sits in the alar-base crease, where the sculpted surface itself
        # turns through > 90 deg within a millimetre: it is exempt as a whole
        rings = d["rings"] if kind == "nostril" else d["rings"][:d["n_exp"]]
        for ring in rings:
            explicit.update(ring)
    edges = {}
    for verts, slot, _ in B.faces:
        if slot != 0:
            continue
        Q = P[list(verts)]
        n = sum(np.cross(Q[k], Q[(k + 1) % len(Q)]) for k in range(len(Q)))
        n = n / (np.linalg.norm(n) + 1e-12)
        for k in range(len(verts)):
            e = (min(verts[k], verts[(k + 1) % len(verts)]), max(verts[k], verts[(k + 1) % len(verts)]))
            edges.setdefault(e, []).append(n)
    bad, worst, where = 0, 0.0, None
    for (a, b), ns in edges.items():
        if len(ns) != 2 or (a in explicit and b in explicit):
            continue
        ang = float(np.degrees(np.arccos(np.clip(np.dot(ns[0], ns[1]), -1.0, 1.0))))
        if ang > FOLD_DEG:
            bad += 1
            if ang > worst:
                worst, where = ang, (P[a] + P[b]) / 2
    return bad, worst, where


def eyes_outward(fh):
    """Fraction of eyeball faces (sclera / cornea) whose normal points into the eye."""
    from .face_head import SLOT
    shell = (SLOT["Eye_Sclera"], SLOT["Eye_Cornea"])
    me = fh.obj.data
    bad = tot = 0
    for side, sx in ((1, "L"), (-1, "R")):
        g = fl.eye_geometry(fh.p, side)
        c = np.array(g["centre"])
        cos_lim = np.cos(np.arcsin(fh.p.iris_r / g["R"])) - 0.02
        ids = set(fh.range(f"eye_{sx}").tolist())
        for poly in me.polygons:
            if poly.vertices[0] not in ids or poly.material_index not in shell:
                continue
            q = fh.rest_mm[list(poly.vertices)]
            r = q.mean(0) - c
            if -r[1] / (np.linalg.norm(r) + 1e-9) > cos_lim:
                continue                      # the limbus wall faces forward on purpose
            n = sum(np.cross(q[k], q[(k + 1) % len(q)]) for k in range(len(q)))
            tot += 1
            bad += np.dot(n, q.mean(0) - c) < 0
    return bad / max(tot, 1)


def check(fh, shapes=None):
    problems = []
    for side, gap in lid_seal(fh).items():
        if gap > LID_GAP_MM:
            problems.append(f"lid margin {'L' if side > 0 else 'R'} stands {gap:.2f} mm off the eyeball")
    if shapes is not None:
        for side, gap in blink_seal(fh, shapes).items():
            if gap > BLINK_GAP_MM:
                problems.append(f"blink {'L' if side > 0 else 'R'} leaves a {gap:.2f} mm slit")
    clear = teeth_clearance(fh)
    if clear < TOOTH_CLEARANCE_MM:
        problems.append(f"teeth / gums come within {clear:.2f} mm of the face surface")
    err = mirror_error(fh)
    if err > MIRROR_MM:
        problems.append(f"skin is asymmetric by {err:.3f} mm")
    bad = inward_faces(fh)
    if bad:
        problems.append(f"{bad} grid faces point into the head")
    n, worst, where = folds(fh)
    if n:
        problems.append(f"{n} folded skin edges (worst {worst:.0f} deg at {np.round(where, 1).tolist()} mm)")
    inv = eyes_outward(fh)
    if inv > 0.02:
        problems.append(f"{inv:.0%} of the eyeball faces point into the eye")
    return problems

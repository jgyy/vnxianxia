"""Geometric self-checks of a built head (run by face_head after every build).

The head is procedural, so a parameter tweak for one NPC can silently break
another; these checks catch the defects that are easy to miss in a portrait:

* lid seal   - the posterior lid margin must hug the globe (no air gap, no
               eyeball poking through), measured where the margin lies over it;
* blink seal - with blink = 1 the upper and lower margins must meet;
* teeth      - no tooth or gum vertex may stand in front of the closed lips / skin;
* symmetry   - the skin mesh must mirror across x = 0 (shape keys rely on it);
* winding    - skin faces must face away from the head's inside.

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
    return problems

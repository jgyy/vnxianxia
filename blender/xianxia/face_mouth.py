"""Inside the mouth: teeth on a dental arch, gums and a tongue (head millimetres).

The arch is a parabola behind the lips whose front sits ``LIP_TO_TEETH`` mm
behind the upper lip and whose width follows the mouth width; upper incisors
overlap the lowers by ~2 mm (overjet and overbite).  Each tooth is a small
rounded block oriented along the arch: central / lateral incisor, canine,
two premolars and the first molar per quadrant (the back molars are never seen), crown sizes from standard dental
tables (upper 8.5 6.6 7.6 7 6.6 10 mm, lower 5.4 5.9 6.9 7 7.1 11 mm wide).
With the lips closed everything is hidden; jaw_open / visemes reveal the
lower teeth and tongue, which follow the jaw rotation (face_shapes).
"""
import math

import numpy as np
from mathutils import Vector

from . import face_landmarks as fl

UPPER = [(8.5, 10.2), (6.6, 8.8), (7.6, 10.0), (7.0, 8.2), (6.6, 7.8), (10.0, 7.0)]
LOWER = [(5.4, 9.0), (5.9, 8.8), (6.9, 10.0), (7.0, 8.0), (7.1, 7.6), (11.0, 7.0)]
LIP_TO_TEETH = 11.5        # soft-tissue thickness of the upper lip at labrale superius


def jaw_pivot(p: fl.FaceParams):
    """The temporomandibular joint axis (x axis through this point), head mm."""
    return np.array([0.0, 4.0, p.canthus - 22.0])


def arch(p: fl.FaceParams, lower=False):
    """Dental arch: (x, y) of the arch centre-line as a function of arc length from the midline."""
    L = fl.landmarks(p)
    y0 = L["labrale_superius"][1] + LIP_TO_TEETH + (3.5 if lower else 0.0)
    half_w = p.mouth_w * 0.5 + (4.0 if not lower else 2.5)          # at the second molar
    depth = 38.0 if p.fem else 41.0

    def pt(t):
        """t in [-1, 1] across the arch: -1/1 at the last molars."""
        x = half_w * math.sin(t * math.pi * 0.5) * (0.62 + 0.38 * abs(t))
        y = y0 + depth * abs(t) ** 1.65
        return x, y
    return pt


def _tooth(bm, base, fwd, side_ax, up, w, h, d, mat, uvl, incisal_up):
    """Rounded tooth crown: a box lofted in 5 slices with a bulged labial face."""
    rows = []
    n = 4
    for k in range(n + 1):
        t = k / n
        # crowns taper toward the incisal / occlusal edge and toward the neck (cervix)
        s = 0.72 + 0.28 * math.sin(math.pi * min(1.0, 0.25 + 0.85 * t))
        z = (t - 0.15) * h
        ring = []
        for ang in range(8):
            a = 2 * math.pi * ang / 8 + math.pi / 8
            cx, cy = math.cos(a), math.sin(a)
            px = math.copysign(abs(cx) ** 0.55, cx) * w * 0.5 * s
            py = math.copysign(abs(cy) ** 0.55, cy) * d * 0.5 * s * (0.75 if cy < 0 else 1.0)
            off = side_ax * px + fwd * py + up * (z if incisal_up else -z)
            ring.append(bm.verts.new(base + off))
        rows.append(ring)
    for k in range(n):
        for i in range(8):
            i2 = (i + 1) % 8
            f = bm.faces.new((rows[k][i], rows[k][i2], rows[k + 1][i2], rows[k + 1][i]))
            f.material_index = mat
            for lp in f.loops:
                lp[uvl].uv = (i / 8, k / n)
    cap = bm.faces.new(rows[-1][::-1] if incisal_up else rows[-1])
    cap.material_index = mat
    return [v for r in rows for v in r]


def build(bm, p: fl.FaceParams, slots, uv=None):
    """Teeth, gums and tongue into bm.  slots: dict name -> material index.

    Returns {"upper": verts, "lower": verts, "tongue": verts} for weighting / shape keys."""
    uvl = uv or bm.loops.layers.uv.verify()
    L = fl.landmarks(p)
    st = L["stomion"][2]
    out = {"upper": [], "lower": [], "tongue": []}
    for lower in (False, True):
        pt = arch(p, lower)
        sizes = LOWER if lower else UPPER
        total = sum(w for w, _ in sizes)
        z_edge = st - 1.2 if not lower else st - 3.0          # incisal edges (overbite)
        for side in (1, -1):
            acc = 0.0
            for k, (w, h) in enumerate(sizes):
                t = (acc + w * 0.5) / total
                acc += w
                x, y = pt(t)
                x2, y2 = pt(min(1.0, t + 0.01))
                tang = Vector((x2 - x, y2 - y, 0.0)).normalized()
                fwd = Vector((tang.y, -tang.x, 0.0))            # labial / buccal direction
                if fwd.y > 0:
                    fwd = -fwd
                base = Vector((side * x, y, 0.0))
                side_ax = Vector((side * tang.x, tang.y, 0.0))
                fwd = Vector((side * fwd.x, fwd.y, 0.0))
                depth = w * (0.72 if k < 3 else 1.0)
                if not lower:
                    base.z = z_edge + h * 0.85 + (0.6 if k in (1,) else 0.0) + k * 0.25
                    vs = _tooth(bm, base, fwd, side_ax, Vector((0, 0, -1)), w * 0.94, h, depth, slots["Teeth"],
                                uvl, True)
                else:
                    base.z = z_edge - h * 0.85 - k * 0.25
                    vs = _tooth(bm, base, fwd, side_ax, Vector((0, 0, 1)), w * 0.94, h, depth, slots["Teeth"],
                                uvl, True)
                out["lower" if lower else "upper"].extend(vs)
        # gum ridge: a tube along the arch over the tooth necks
        rows = []
        n = 24
        for i in range(n + 1):
            t = -1 + 2 * i / n
            x, y = pt(abs(t))
            x *= 1 if t >= 0 else -1
            zc = (z_edge + 11.0) if not lower else (z_edge - 11.0)
            ring = []
            for a in range(8):
                ang = 2 * math.pi * a / 8
                ring.append(bm.verts.new(Vector((x * (1 + 0.06 * math.cos(ang)), y + 3.6 * math.cos(ang),
                                                 zc + 3.2 * math.sin(ang)))))
            rows.append(ring)
        for i in range(n):
            for a in range(8):
                a2 = (a + 1) % 8
                f = bm.faces.new((rows[i][a], rows[i][a2], rows[i + 1][a2], rows[i + 1][a]))
                f.material_index = slots["Mouth_Inner"]
        out["lower" if lower else "upper"].extend(v for r in rows for v in r)
    # tongue: lofted sections from the tip (behind the lower incisors) to the root
    pt = arch(p, True)
    _, y0 = pt(0.0)
    tip_y = y0 + 3.5
    secs = []
    for k in range(9):
        t = k / 8
        y = tip_y + 44.0 * t
        hw = (p.mouth_w * 0.36) * math.sin(math.pi * 0.5 * min(1.0, 0.25 + 1.4 * t)) * (1 - 0.25 * t ** 3)
        top = st - 4.5 + 1.5 * math.sin(math.pi * t)
        thick = 4.0 + 9.0 * t
        ring = []
        for a in range(14):
            ang = 2 * math.pi * a / 14
            cx, cy = math.cos(ang), math.sin(ang)
            groove = -0.8 * math.exp(-(cx / 0.25) ** 2) if cy > 0 else 0.0
            z = top - thick * 0.5 + (thick * 0.5) * cy + groove
            ring.append(bm.verts.new(Vector((hw * cx, y, z))))
        secs.append(ring)
    for k in range(8):
        for a in range(14):
            a2 = (a + 1) % 14
            f = bm.faces.new((secs[k][a], secs[k][a2], secs[k + 1][a2], secs[k + 1][a]))
            f.material_index = slots["Tongue"]
            for lp, (uu, vv) in zip(f.loops, ((a, k), (a + 1, k), (a + 1, k + 1), (a, k + 1))):
                lp[uvl].uv = (uu / 14, vv / 8)
    cap = bm.faces.new(secs[0][::-1])
    cap.material_index = slots["Tongue"]
    out["tongue"] = [v for r in secs for v in r]
    return out

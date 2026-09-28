"""Assembles the complete head object: skin, eyes, mouth interior, lashes, brows and ears.

``FaceHead(cfg, mats, s, centre)`` builds one mesh object "Head" (head
millimetres are converted to world metres at the end) with material slots

    0 face (mats["face"])  1 Mouth_Inner  2 Eye_Sclera  3 Eye_Iris  4 Eye_Cornea
    5 Eye_Tearline  6 Teeth  7 Tongue  8 Lashes  9 Brows

and remembers which vertex range each part occupies, which the shape keys
(face_shapes) and the weights (face_rig) need.  The head is its own object so
its morph targets do not bloat the body mesh in the glTF.
"""
import bpy
import numpy as np
from mathutils import Vector

from . import anatomy, face_cards, face_eyes, face_materials, face_mesh, face_mouth, face_rig, face_uv, util
from . import face_landmarks as fl
from . import face_surface as fsu

SLOT_NAMES = ("face", "Mouth_Inner", "Eye_Sclera", "Eye_Iris", "Eye_Cornea", "Eye_Tearline", "Teeth", "Tongue",
              "Lashes", "Brows")
SLOT = {n: i for i, n in enumerate(SLOT_NAMES)}


class FaceHead:
    def __init__(self, cfg, mats, s, centre):
        self.cfg = cfg
        self.p = p = fl.params_for(cfg)
        self.s = s
        self.centre = Vector(centre)
        self.mesh = face_mesh.HeadMesh(p)
        self.surf = self.mesh.surf
        self.lids = self.mesh.lids
        rx, ry, rz = p.head
        self.radii = (rx * 0.001 * s, ry * 0.001 * s, rz * 0.001 * s)
        slots = face_materials.face_slots(cfg, mats)
        self.materials = [mats["face"]] + [slots[n] for n in SLOT_NAMES[1:]]
        self.parts = {}
        bm = self.mesh.to_bmesh(1000.0, (0.0, 0.0, 0.0))      # head millimetres, like the other parts
        self.parts["skin"] = (0, len(bm.verts))
        uvl = bm.loops.layers.uv.verify()
        # ---- eyes
        for side, sx in ((1, "L"), (-1, "R")):
            g = fl.eye_geometry(p, side)
            self._part(bm, f"eye_{sx}", lambda: face_eyes.eyeball(
                bm, g["centre"], g["R"], uv=uvl, mats=(SLOT["Eye_Sclera"], SLOT["Eye_Iris"], SLOT["Eye_Cornea"]), limbus=p.iris_r))
            self._part(bm, f"caruncle_{sx}", lambda: face_eyes.caruncle(bm, self.lids[side], SLOT["Mouth_Inner"], uvl))
            tv, tf, tuv = face_eyes.tearline_points(self.lids[side])
            self._cards(bm, f"tear_{sx}", tv, tf, tuv, SLOT["Eye_Tearline"], uvl)
            lv, meta = face_cards.lash_points(self.lids[side])
            luv = [(m[2], m[1]) for m in meta]         # u along the lid, v root -> tip
            self._cards(bm, f"lash_{sx}", lv, face_cards.lash_faces(face_cards.lash_count(p, side)), luv,
                        SLOT["Lashes"], uvl)
            bv, bf, buv = face_cards.brow_cards(p, self.surf, side)
            self._cards(bm, f"brow_{sx}", bv, bf, buv, SLOT["Brows"], uvl)
        # ---- mouth interior
        start = len(bm.verts)
        out = face_mouth.build(bm, p, SLOT, uvl)
        bm.verts.ensure_lookup_table()
        self.mouth_parts = {k: np.array([v.index for v in vs]) for k, vs in out.items()}
        self.parts["mouth_inner"] = (start, len(bm.verts))
        # ---- ears
        for side, sx in ((1, "L"), (-1, "R")):
            ef = fl.ear_frame(p, side)
            uvf = (lambda sd: (lambda up, back: face_uv.ear_uv(sd, up, back, 70.0)))(side)
            self._part(bm, f"ear_{sx}", lambda: anatomy.ear(bm, Vector(ef["loc"]), side, ef["size"], ef["out"],
                                                            uv_fn=uvf, mat_index=SLOT["face"]))
        # ---- to world units
        k = 0.001 * s
        for v in bm.verts:
            v.co = self.centre + v.co * k
        self.obj = util.mesh_object("Head", bm, self.materials)
        self.obj["face_landmarks"] = self.landmarks_world()
        self.rest_mm = self.world_to_mm(np.array([v.co for v in self.obj.data.vertices]))
        self._weights()

    # ------------------------------------------------------------------ helpers
    def _part(self, bm, name, fn):
        start = len(bm.verts)
        fn()
        self.parts[name] = (start, len(bm.verts))

    def _cards(self, bm, name, verts, faces, uvs, slot, uvl):
        start = len(bm.verts)
        vs = [bm.verts.new(Vector(q)) for q in verts]
        for f in faces:
            face = bm.faces.new([vs[i] for i in f])
            face.material_index = slot
            for lp, i in zip(face.loops, f):
                lp[uvl].uv = uvs[i]
        self.parts[name] = (start, len(bm.verts))

    def range(self, name):
        a, b = self.parts[name]
        return np.arange(a, b)

    def world_to_mm(self, P):
        return (np.asarray(P) - np.array(self.centre)) / (0.001 * self.s)

    def mm_to_world(self, P):
        return np.array(self.centre) + np.asarray(P) * (0.001 * self.s)

    def landmarks_world(self):
        """World landmark points the skin painter (skin.landmarks) consumes."""
        L = fl.landmarks(self.p)
        cheek = fl.eye_geometry(self.p, 1)["centre"]
        st = np.array(L["stomion"])
        # the painter's lip bands are centred on these: the middle of each vermilion
        up = (st + np.array(L["labrale_superius"])) * 0.5
        lo = (st + np.array(L["labrale_inferius"])) * 0.5
        pts = dict(eye=L["pupil.L"], nose_tip=L["pronasale"], lip_line=L["stomion"],
                   upper_lip=up, lower_lip=lo, chin=L["pogonion"],
                   mouth_corner=L["cheilion.L"], brow=L["brow_peak.L"], ear=fl.ear_frame(self.p, 1)["loc"],
                   cheek=(cheek[0] - 1.0, L["malar.L"][1] - 4.0, cheek[2] - 25.0),
                   nostril=self.mesh.nostril_centre(1))
        return {k: [float(c) for c in self.mm_to_world(np.array(v))] for k, v in pts.items()}

    def trichion_z(self):
        """Unit-sphere z (seen from the head centre) of the front hairline point."""
        t = np.array(fl.landmarks(self.p)["trichion"], np.float64)
        return float(t[2] / np.linalg.norm(t))

    def paint_masks(self, pos):
        """Exact feature masks for the skin painter at world positions pos (..., 3).

        The painter's own masks are soft blobs in its lon/lat frame; the lips must
        follow the sculpted vermilion border exactly (Cupid's bow included) or the
        tint bleeds onto the skin.  Returns upper_lip / lower_lip (0..1, ~0.3 mm
        soft edge), lip_inner (1 at the stomion centre, 0 at the border: the
        gradient-lip falloff) and philtrum (the groove between the columns)."""
        P = self.world_to_mm(pos)
        x, y, z = P[..., 0], P[..., 1], P[..., 2]
        p = self.p
        front = y < fl.face_plane(p) + 25.0                    # only the face front, not the nape
        st, up, lo = self.surf.lips_at(x)
        ax = np.abs(x)
        xc = p.mouth_w * 0.5
        across = fsu.sstep(xc + 0.2, xc - 1.0, ax) * front
        upper = fsu.sstep(up + 0.3, up - 0.3, z) * fsu.sstep(st - 0.6, st + 0.2, z) * across
        lower = fsu.sstep(lo - 0.3, lo + 0.3, z) * fsu.sstep(st + 0.6, st - 0.2, z) * across
        # depth into the vermilion: 0 on the border, 1 on the stomion line
        du = np.clip((up - z) / np.maximum(up - st, 0.5), 0, 1)
        dl = np.clip((z - lo) / np.maximum(st - lo, 0.5), 0, 1)
        depth = np.where(z > st, du, dl)
        inner = depth ** 0.8 * np.exp(-((ax / (xc * 0.62)) ** 2))
        colx = 5.0
        above = fsu.sstep(up - 0.3, up + 0.8, z) * fsu.sstep(p.subnasale - 1.0, p.subnasale - 3.5, z) * front
        philtrum = np.exp(-((x / 2.4) ** 2)) * above
        columns = np.exp(-(((ax - colx) / 1.2) ** 2)) * above
        liner, lower_liner = self._liner_masks(P)
        return dict(upper_lip=upper.astype(np.float32), lower_lip=lower.astype(np.float32),
                    lip_inner=(inner * (upper + lower)).astype(np.float32),
                    philtrum=philtrum.astype(np.float32), columns=columns.astype(np.float32),
                    liner=liner, lower_liner=lower_liner)

    def _liner_masks(self, P):
        """Tight-line liner along the real upper lash line (thicker laterally, with a short
        lifted wing past the outer canthus) and a faint lower one - painted from the lid
        geometry, so it sits exactly at the lash roots and never floats on the lid."""
        from scipy.spatial import cKDTree
        B = self.mesh.B
        up_pts, up_w, lo_pts, lo_w = [], [], [], []
        for kind, d in self.mesh.ogrids:
            if kind != "eye":
                continue
            ring = np.array([B.pos[v] for v in d["rings"][face_eyes.EyeLids.LASH_RING]])
            s = np.asarray(d["s"])
            order = np.argsort(s)
            ring, s = ring[order], s[order]
            up = (s > 0.0) & (s < 0.5)
            q = np.linspace(0.005, 0.495, 160)
            pts = np.stack([np.interp(q, s[up], ring[up, k]) for k in range(3)], -1)
            up_pts.append(pts)
            up_w.append(0.6 + 0.7 * (1 - q / 0.5) ** 1.5)                # 0.6 mm medial .. 1.3 lateral
            # the wing: continue the lateral end outward and up for ~3.5 mm, tapering
            a, b = pts[0], pts[6]
            t = (a - b) / (np.linalg.norm(a - b) + 1e-9)
            t = t + np.array([0.0, 0.0, 0.35])
            t /= np.linalg.norm(t)
            k = np.linspace(0.0, 3.5, 24)[:, None]
            up_pts.append(a + t * k)
            up_w.append(1.1 * (1 - k[:, 0] / 3.8))
            lo = s > 0.5
            ql = np.linspace(0.62, 0.99, 80)
            lo_pts.append(np.stack([np.interp(ql, s[lo], ring[lo, k]) for k in range(3)], -1))
            lo_w.append(np.full(len(ql), 0.45))
        out = []
        for pts, w in ((up_pts, up_w), (lo_pts, lo_w)):
            pts, w = np.concatenate(pts), np.concatenate(w)
            dist, idx = cKDTree(pts).query(P.reshape(-1, 3), distance_upper_bound=4.0)
            ok = np.isfinite(dist)
            m = np.zeros(len(dist), np.float32)
            m[ok] = np.exp(-(dist[ok] / w[idx[ok]]) ** 2)
            out.append(m.reshape(P.shape[:-1]))
        return out

    def scalp_proxy(self):
        """A temporary copy of the skin, eyeballs and ears (no cards) for surface ray casts."""
        keep = [self.range("skin")] + [self.range(f"{k}_{sx}") for k in ("eye", "ear") for sx in ("L", "R")]
        keep = set(np.concatenate(keep).tolist())
        me = self.obj.data
        verts = [tuple(v.co) for v in me.vertices]
        polys = [list(p.vertices) for p in me.polygons if all(i in keep for i in p.vertices)]
        pm = bpy.data.meshes.new("HeadScalpProxy")
        pm.from_pydata(verts, [], polys)
        o = bpy.data.objects.new("HeadScalpProxy", pm)
        util.link(o)
        return o

    def eye_centres_world(self):
        return [self.mm_to_world(np.array(fl.eye_geometry(self.p, sd)["centre"])) for sd in (1, -1)]

    # ------------------------------------------------------------------ weights
    def _weights(self):
        n = len(self.obj.data.vertices)
        skin = self.range("skin")
        head_w, neck_w, chest_w = face_rig.neck_weights(self.rest_mm[skin], self.p)
        groups = {"head": ([], []), "neck": ([], []), "chest": ([], []), "eye.L": ([], []), "eye.R": ([], [])}

        def put(name, idx, w):
            groups[name][0].extend(np.asarray(idx).tolist())
            groups[name][1].extend(np.broadcast_to(w, np.shape(idx)).tolist())

        put("head", skin, head_w)
        put("neck", skin, neck_w)
        put("chest", skin, chest_w)
        eyes = set()
        for sx, bone in (("L", "eye.L"), ("R", "eye.R")):
            idx = self.range(f"eye_{sx}")
            put(bone, idx, 1.0)
            eyes.update(idx.tolist())
        rest = np.array([i for i in range(skin[-1] + 1, n) if i not in eyes])
        put("head", rest, 1.0)
        face_rig.assign_weights(self.obj, {k: (np.array(a, int), np.array(b)) for k, (a, b) in groups.items()})

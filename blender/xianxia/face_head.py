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
                bm, g["centre"], g["R"], uv=uvl, mats=(SLOT["Eye_Sclera"], SLOT["Eye_Iris"], SLOT["Eye_Cornea"])))
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

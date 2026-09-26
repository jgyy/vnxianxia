"""Enemy creatures: stone golem (humanoid rig), spirit wolf and the Jiao serpent.

Each builder resets the scene and returns (armature, meshes, actions) like
characters.build_character, with the actions idle/walk/run/attack/hit/death.
Creatures face -Y in Blender (+Z in Godot).
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector, noise

from . import characters, tex, util
from .characters import Poser, qa, util_smooth

V = Vector
R = math.radians
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def rigid(obj, bone):
    vg = obj.vertex_groups.new(name=bone)
    vg.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")


def weigh(obj, bones, names, power=5.0, top=2):
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        w = characters.seg_weights(p, bones, names, power=power, top=top)
        for n, val in w.items():
            if val < 1e-3:
                continue
            vg = obj.vertex_groups.get(n) or obj.vertex_groups.new(name=n)
            vg.add([v.index], val, "REPLACE")


def finish(arm, groups):
    meshes = []
    for name, objs in groups:
        objs = [o for o in objs if o is not None]
        if not objs:
            continue
        o = util.join(objs, name)
        o.parent = arm
        mod = o.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        meshes.append(o)
    return meshes


def start(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    return act


def fur(base, dark, glow=None, size=512, seed=401):
    """Fur: fine strands along v, darker saddle, optional glowing spirit markings."""
    b, d = tex.srgb(base), tex.srgb(dark)
    u, v = tex.grid(size)
    strands = tex.fbm(size, 128, 3, 0.55, seed, stretch=8)
    clump = tex.fbm(size, 24, 3, 0.5, seed + 1, stretch=3)
    saddle = tex.sstep(0.3, 0.05, np.abs(u - 0.25) + (tex.fbm(size, 6, 3, 0.5, seed + 2) - 0.5) * 0.15)
    col = tex.lerp(b, d, saddle * 0.7) * (0.75 + 0.35 * strands)[..., None] * (0.9 + 0.15 * clump)[..., None]
    out = tex.result(col, 0.75 - strands * 0.15, 0.0, strands * 0.7 + clump * 0.3)
    if glow:
        marks = np.zeros((size, size), np.float32)
        rng = np.random.default_rng(seed + 3)
        for _ in range(9):
            cx, cy = rng.random(), rng.uniform(0.35, 0.9)
            pts = tex.cloud_curl(cx, cy, 0.05, 1.3, rng.choice([-1.0, 1.0]), rng.uniform(0, 6.28))
            tex.stamp_curve(marks, pts, 0.004, size)
        out["emission"] = (tex.srgb(glow)[None, None, :] * marks[..., None]).astype(np.float32)
        out["albedo"] = tex.lerp(out["albedo"], tex.srgb(glow), marks * 0.6)
    return out


def scales(base, belly, edge, size=512, seed=421, glow=None):
    """Overlapping dragon scales in rows along u, lighter belly plates at v near 0/1."""
    b, bl, e = tex.srgb(base), tex.srgb(belly), tex.srgb(edge)
    u, v = tex.grid(size)
    rows, cols = 18, 40
    su = u * cols
    sv = v * rows + 0.5 * (np.floor(su) % 2)
    fu, fv = su - np.floor(su) - 0.5, sv - np.floor(sv)
    d = np.sqrt(fu ** 2 + (fv - 0.1) ** 2 * 1.6)
    scale = tex.sstep(0.62, 0.4, d)
    rim = np.exp(-((d - 0.55) / 0.06) ** 2)
    n = tex.fbm(size, 8, 4, 0.5, seed)
    belly_m = tex.sstep(0.2, 0.1, np.abs(u - 0.75))
    col = tex.lerp(b * (0.8 + 0.4 * n)[..., None], e, rim * 0.6)
    col = col * (0.75 + 0.35 * scale)[..., None]
    plates = (np.abs(((u * 60) % 1.0) - 0.5) < 0.45).astype(np.float32)
    col = tex.lerp(col, bl * (0.85 + 0.15 * plates)[..., None], belly_m)
    out = tex.result(col, 0.35 + 0.2 * (1 - scale), 0.15 * scale * (1 - belly_m), scale * 0.8 + rim * 0.2)
    if glow:
        out["emission"] = (tex.srgb(glow)[None, None, :] * (rim * (1 - belly_m) * 0.5)[..., None]).astype(np.float32)
    return out


def glow_stone(color, glow, size=512, seed=441):
    """Weathered stone with glowing rune cracks (emission)."""
    t = tex.stone(color, size, seed, 0.4)
    u, v = tex.grid(size)
    n = tex.fbm(size, 10, 5, 0.55, seed + 1)
    cracks = np.exp(-((n - 0.5) / 0.012) ** 2) * tex.sstep(0.3, 0.7, tex.fbm(size, 4, 3, 0.5, seed + 2))
    moss = tex.sstep(0.55, 0.75, tex.fbm(size, 12, 4, 0.5, seed + 3)) * tex.sstep(0.4, 0.8, v)
    t["albedo"] = tex.lerp(t["albedo"], tex.srgb("#4f6a35"), moss * 0.8)
    t["albedo"] = tex.lerp(t["albedo"], tex.srgb(glow) * 0.6, cracks)
    t["height"] = t["height"] - cracks * 0.5 + moss * 0.2
    t["emission"] = (tex.srgb(glow)[None, None, :] * cracks[..., None]).astype(np.float32)
    return t


def rock_blob(bm, loc, size, seed, amount=0.22):
    verts = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)["verts"]
    off = V((seed * 13.1, seed * 7.7, seed * 3.3))
    for vt in verts:
        nrm = vt.co.normalized()
        d = noise.fractal(vt.co * 1.6 + off, 0.9, 2.0, 4)
        # flatten into facets so the rock reads as chiselled stone
        k = 1 + d * amount
        vt.co = V((nrm.x * size[0] * k, nrm.y * size[1] * k, nrm.z * size[2] * k)) + V(loc)
    return verts


# --------------------------------------------------------------------------
# stone golem: rock chunks riding the humanoid skeleton
# --------------------------------------------------------------------------
GOLEM = characters.variant(characters.MALE, "stone_golem", scale=1.3, shoulder=0.23, hip=0.12)


def build_golem():
    util.reset_scene()
    cfg = GOLEM
    s = cfg["scale"]
    J = {n: (h * s, t * s, p) for n, (h, t, p) in characters.joints(cfg).items()}
    arm = characters.build_armature(cfg, J)
    stone_maps = glow_stone("#8d8a83", "#58e6ff")
    stone = util.material("golem_stone_glow", stone_maps, normal_strength=1.4,
                          emission_map=stone_maps["emission"], emission_strength=2.5)
    core = util.material("golem_core", color="#7ff4ff", rough=0.1, emission="#5ce8ff", emission_strength=6.0)
    objs = []
    # (bone, radius x/y/z as fraction of bone length or absolute, count along)
    spec = {
        "hips": ((0.2, 0.15, 0.13), 1), "spine": ((0.21, 0.16, 0.12), 1), "chest": ((0.3, 0.2, 0.17), 1),
        "neck": ((0.07, 0.07, 0.06), 1), "head": ((0.12, 0.13, 0.11), 1),
    }
    rnd = random.Random(3)
    for side in ("L", "R"):
        spec[f"shoulder.{side}"] = ((0.14, 0.13, 0.12), 1)
        spec[f"upper_arm.{side}"] = ((0.1, 0.1, 0.1), 2)
        spec[f"forearm.{side}"] = ((0.11, 0.11, 0.11), 2)
        spec[f"hand.{side}"] = ((0.1, 0.09, 0.11), 1)
        spec[f"thigh.{side}"] = ((0.13, 0.13, 0.13), 2)
        spec[f"shin.{side}"] = ((0.12, 0.12, 0.12), 2)
        spec[f"foot.{side}"] = ((0.1, 0.14, 0.06), 1)
    for k, (bone, (r, n)) in enumerate(spec.items()):
        h, t, _ = J[bone]
        for i in range(n):
            c = h.lerp(t, (i + 0.5) / n)
            if bone.startswith("shoulder"):
                c = t
            if bone == "head":
                c = h.lerp(t, 0.4)
            bm = bmesh.new()
            rock_blob(bm, c, tuple(x * s * rnd.uniform(0.9, 1.1) for x in r), k * 3 + i, 0.3)
            if bone == "chest":   # a crown of smaller rocks on the shoulders/back
                for j in range(5):
                    a = j / 4 * math.pi
                    rock_blob(bm, c + V((math.cos(a) * 0.22 * s, 0.12 * s, 0.1 * s + math.sin(a) * 0.08 * s)),
                              (0.07 * s, 0.06 * s, 0.06 * s), 50 + j, 0.4)
            o = util.mesh_object(f"Rock_{bone}_{i}", bm, stone, smooth=False)
            util.box_uv(o, 1.2)
            rigid(o, bone)
            objs.append(o)
    # glowing heart crystal and eyes
    h, t, _ = J["chest"]
    bm = bmesh.new()
    util.sphere(bm, 0.07 * s, loc=h.lerp(t, 0.5) + V((0, -0.2 * s, 0)), segs=6, rings=4, scale=(1, 0.7, 1.3))
    hd, ht, _ = J["head"]
    for side in (1, -1):
        util.sphere(bm, 0.018 * s, loc=hd.lerp(ht, 0.45) + V((side * 0.045 * s, -0.12 * s, 0)), segs=8, rings=5)
    o = util.mesh_object("Core", bm, core)
    rigid(o, "chest")
    objs.append(o)
    meshes = finish(arm, [("Body", objs)])
    actions = characters.build_actions(arm, J, cfg, s)
    return arm, meshes, actions


# --------------------------------------------------------------------------
# spirit wolf
# --------------------------------------------------------------------------
def wolf_bones(s):
    b = {
        "hips": (V((0, 0.40, 0.92)), V((0, 0.14, 0.95)), None),
        "spine": (V((0, 0.14, 0.95)), V((0, -0.16, 0.98)), "hips"),
        "chest": (V((0, -0.16, 0.98)), V((0, -0.42, 1.02)), "spine"),
        "neck": (V((0, -0.42, 1.02)), V((0, -0.62, 1.2)), "chest"),
        "head": (V((0, -0.62, 1.2)), V((0, -0.98, 1.14)), "neck"),
        "jaw": (V((0, -0.66, 1.1)), V((0, -0.94, 1.06)), "head"),
        "tail.1": (V((0, 0.42, 0.92)), V((0, 0.62, 0.86)), "hips"),
        "tail.2": (V((0, 0.62, 0.86)), V((0, 0.82, 0.74)), "tail.1"),
        "tail.3": (V((0, 0.82, 0.74)), V((0, 1.0, 0.6)), "tail.2"),
    }
    for side, sg in (("L", 1), ("R", -1)):
        x = 0.13 * sg
        b[f"ear.{side}"] = (V((0.07 * sg, -0.66, 1.3)), V((0.09 * sg, -0.64, 1.44)), "head")
        b[f"upperarm.{side}"] = (V((x, -0.38, 0.88)), V((x, -0.33, 0.52)), "chest")
        b[f"foreleg.{side}"] = (V((x, -0.33, 0.52)), V((x, -0.37, 0.12)), f"upperarm.{side}")
        b[f"forepaw.{side}"] = (V((x, -0.37, 0.12)), V((x, -0.48, 0.03)), f"foreleg.{side}")
        b[f"thigh.{side}"] = (V((x, 0.36, 0.86)), V((x, 0.2, 0.54)), "hips")
        b[f"shin.{side}"] = (V((x, 0.2, 0.54)), V((x, 0.40, 0.22)), f"thigh.{side}")
        b[f"hock.{side}"] = (V((x, 0.40, 0.22)), V((x, 0.36, 0.05)), f"shin.{side}")
        b[f"hindpaw.{side}"] = (V((x, 0.36, 0.05)), V((x, 0.25, 0.03)), f"hock.{side}")
    return {n: (h * s, t * s, p) for n, (h, t, p) in b.items()}


def build_wolf():
    util.reset_scene()
    s = 1.0
    B = wolf_bones(s)
    cfg = dict(name="spirit_wolf")
    arm = characters.build_armature(cfg, B)
    fmaps = fur("#c9d2dc", "#5e6b7c", glow="#6fe3ff")
    furm = util.material("wolf_fur", fmaps, normal_strength=1.0, emission_map=fmaps["emission"],
                         emission_strength=2.0)
    nose = util.material("wolf_nose", color="#1a1618", rough=0.3)
    teeth = util.material("wolf_teeth", color="#efe8d8", rough=0.35)
    eye = util.material("wolf_eye", color="#9ff6ff", rough=0.05, emission="#6fe3ff", emission_strength=5.0)
    claw = util.material("wolf_claw", color="#2a2628", rough=0.4)
    parts = []

    # body: rings along a spine curve from rump to neck
    spine = [V((0, 0.5, 0.9)), V((0, 0.36, 0.93)), V((0, 0.14, 0.95)), V((0, -0.1, 0.97)), V((0, -0.3, 0.99)),
             V((0, -0.46, 1.04)), V((0, -0.58, 1.16)), V((0, -0.66, 1.24))]
    radii = [(0.10, 0.10), (0.16, 0.17), (0.15, 0.18), (0.14, 0.19), (0.17, 0.24), (0.16, 0.2), (0.12, 0.13),
             (0.1, 0.11)]
    pts = util.catmull(spine, 4)
    rr = util.catmull([V((a, b_, 0)) for a, b_ in radii], 4)
    bm = bmesh.new()

    def rad(t):
        i = min(int(t * (len(rr) - 1)), len(rr) - 1)
        return (rr[i].x, rr[i].y)

    def belly(t):   # the chest keel hangs lower than the tucked-up belly
        k = math.exp(-((t - 0.62) / 0.14) ** 2) * 0.05 - math.exp(-((t - 0.3) / 0.12) ** 2) * 0.02
        return (0.0, -k)
    util.tube(bm, pts, rad, n=20, up=(0, 0, 1), uv_scale=(1.0, 1.5), profile=belly)
    body = util.mesh_object("Body", bm, furm)
    util.subdivide(body, 1)
    weigh(body, B, ["hips", "spine", "chest", "neck", "tail.1"], power=4.0)
    parts.append(body)

    # head: skull, muzzle, jaw, ears, eyes, nose, fangs
    bm = bmesh.new()
    skull = [V((0, -0.58, 1.22)), V((0, -0.68, 1.24)), V((0, -0.76, 1.22)), V((0, -0.86, 1.18)), V((0, -0.97, 1.15))]
    srad = [(0.12, 0.11), (0.135, 0.12), (0.1, 0.085), (0.065, 0.06), (0.045, 0.038)]
    util.tube(bm, util.catmull(skull, 3), lambda t: srad[min(int(t * 4.99), 4)], n=14, up=(0, 0, 1))
    head = util.mesh_object("Head", bm, furm)
    util.subdivide(head, 1)
    rigid(head, "head")
    parts.append(head)
    bm = bmesh.new()
    jaw_pts = [V((0, -0.64, 1.1)), V((0, -0.78, 1.1)), V((0, -0.93, 1.09))]
    util.tube(bm, jaw_pts, lambda t: (0.07 * (1 - 0.45 * t), 0.035 * (1 - 0.4 * t)), n=10, up=(0, 0, 1))
    jaw = util.mesh_object("Jaw", bm, furm)
    rigid(jaw, "jaw")
    parts.append(jaw)
    bm = bmesh.new()
    for side in (1, -1):
        for k, y in enumerate((-0.9, -0.84)):
            util.cylinder(bm, 0.006, 0.0005, 0.035, loc=(side * 0.02, y, 1.1 - 0.01 * k), segs=6)
    o = util.mesh_object("Fangs", bm, teeth)
    rigid(o, "head")
    parts.append(o)
    bm = bmesh.new()
    util.sphere(bm, 0.02, loc=(0, -0.985, 1.16), segs=10, rings=6, scale=(1.2, 0.8, 0.8))
    o = util.mesh_object("Nose", bm, nose)
    rigid(o, "head")
    parts.append(o)
    bm = bmesh.new()
    for side in (1, -1):
        util.sphere(bm, 0.014, loc=(side * 0.052, -0.8, 1.235), segs=10, rings=6, scale=(1.0, 0.6, 0.7))
    o = util.mesh_object("Eyes", bm, eye)
    rigid(o, "head")
    parts.append(o)
    for side, sg in (("L", 1), ("R", -1)):
        bm = bmesh.new()
        util.cylinder(bm, 0.045, 0.004, 0.13, loc=(0.075 * sg, -0.66, 1.36), segs=8,
                      rot=Matrix.Rotation(R(-12 * sg), 4, "Y") @ Matrix.Diagonal((1, 0.45, 1, 1)))
        o = util.mesh_object(f"Ear.{side}", bm, furm)
        util.box_uv(o, 4)
        rigid(o, f"ear.{side}")
        parts.append(o)
        # legs
        for chain, rads in (([f"upperarm.{side}", f"foreleg.{side}", f"forepaw.{side}"], (0.1, 0.055, 0.04)),
                            ([f"thigh.{side}", f"shin.{side}", f"hock.{side}", f"hindpaw.{side}"],
                             (0.14, 0.08, 0.045, 0.04))):
            path = [B[chain[0]][0] + V((0, 0, 0.06))] + [B[n][1] for n in chain]
            bm = bmesh.new()
            rl = list(rads) + [rads[-1]]
            util.tube(bm, util.catmull(path, 3), lambda t, rl=rl: rl[min(int(t * (len(rl) - 1)), len(rl) - 1)],
                      n=10, up=(0, -1, 0))
            o = util.mesh_object(f"Leg.{side}", bm, furm)
            util.subdivide(o, 1)
            weigh(o, B, chain + (["chest"] if "upperarm" in chain[0] else ["hips"]), power=6.0)
            parts.append(o)
            paw = B[chain[-1]][1]
            bm = bmesh.new()
            util.sphere(bm, 0.045, loc=paw + V((0, 0.02, 0.02)), segs=10, rings=6, scale=(0.9, 1.3, 0.55))
            o = util.mesh_object("Paw", bm, furm)
            util.box_uv(o, 4)
            rigid(o, chain[-1])
            parts.append(o)
            bm = bmesh.new()
            for k in range(4):
                util.cylinder(bm, 0.008, 0.001, 0.03, loc=paw + V(((k - 1.5) * 0.02, -0.04, 0.005)),
                              rot=Matrix.Rotation(R(-70), 4, "X"), segs=5)
            o = util.mesh_object("Claws", bm, claw)
            rigid(o, chain[-1])
            parts.append(o)
    # bushy tail
    bm = bmesh.new()
    tail = [B["tail.1"][0], B["tail.2"][0], B["tail.3"][0], B["tail.3"][1] + V((0, 0.08, -0.08))]
    util.tube(bm, util.catmull(tail, 4), lambda t: 0.05 + 0.07 * math.sin(math.pi * min(1.0, t * 1.1)), n=12)
    o = util.mesh_object("Tail", bm, furm)
    util.subdivide(o, 1)
    weigh(o, B, ["hips", "tail.1", "tail.2", "tail.3"], power=5.0)
    parts.append(o)
    # neck ruff: a fuller collar of fur
    bm = bmesh.new()
    util.tube(bm, [V((0, -0.44, 1.0)), V((0, -0.56, 1.14))], lambda t: (0.17 - 0.03 * t, 0.2 - 0.04 * t), n=16,
              up=(0, 0, 1))
    o = util.mesh_object("Ruff", bm, furm)
    util.subdivide(o, 1)
    weigh(o, B, ["chest", "neck"], power=4.0)
    parts.append(o)

    meshes = finish(arm, [("Wolf", parts)])
    actions = wolf_actions(arm, B)
    return arm, meshes, actions


def wolf_actions(arm, B):
    poser = Poser(arm, B)
    arm.animation_data_create()
    acts = []

    def legs(dl, ph, stride, lift, pairs):
        for name, off in pairs.items():
            p = ph + off
            sw = stride * math.sin(p)
            up = lift * max(0.0, math.cos(p))
            if name.startswith("f"):
                side = name[-1]
                dl[f"upperarm.{side}"] = qa(X, -sw)
                dl[f"foreleg.{side}"] = qa(X, up * 1.2)
                dl[f"forepaw.{side}"] = qa(X, -up * 0.8)
            else:
                side = name[-1]
                dl[f"thigh.{side}"] = qa(X, -sw)
                dl[f"shin.{side}"] = qa(X, -up * 0.8)
                dl[f"hock.{side}"] = qa(X, up * 1.0)
        return dl

    act = start(arm, "idle")
    T = 60
    for f in range(0, T + 1, 2):
        ph = 2 * math.pi * f / T
        dl = {"chest": qa(X, 1.5 * math.sin(ph)), "neck": qa(X, 3 * math.sin(ph + 0.5)),
              "head": qa(Z, 8 * math.sin(ph * 0.5)) @ qa(X, 2 * math.sin(ph)),
              "jaw": qa(X, 4 + 3 * math.sin(ph)),
              "tail.1": qa(Z, 10 * math.sin(ph)), "tail.2": qa(Z, 12 * math.sin(ph - 0.6)),
              "tail.3": qa(Z, 14 * math.sin(ph - 1.2)),
              "ear.L": qa(Y, 4 * math.sin(ph * 2)), "ear.R": qa(Y, -4 * math.sin(ph * 2 + 1))}
        poser.key(f + 1, dl, V((0, 0, 0.005 * math.sin(ph))))
    acts.append(act)

    for name, T, stride, lift, bob, pairs, flex in (
            ("walk", 30, 22, 30, 0.02, {"fL": 0, "hR": 0.3, "fR": math.pi, "hL": math.pi + 0.3}, 2),
            ("run", 16, 40, 55, 0.06, {"fL": 0, "fR": 0.5, "hL": math.pi, "hR": math.pi + 0.5}, 12)):
        act = start(arm, name)
        for f in range(0, T + 1):
            ph = 2 * math.pi * f / T
            dl = {"spine": qa(X, flex * math.sin(ph)), "chest": qa(X, -flex * 0.6 * math.sin(ph)),
                  "neck": qa(X, -6 + 4 * math.sin(2 * ph)), "head": qa(X, 4 * math.sin(2 * ph + 1)),
                  "tail.1": qa(X, -8 - 6 * math.sin(ph)), "tail.2": qa(Z, 8 * math.sin(ph)),
                  "tail.3": qa(Z, 10 * math.sin(ph - 0.8)), "jaw": qa(X, 10 if name == "run" else 4)}
            legs(dl, ph, stride, lift, pairs)
            poser.key(f + 1, dl, V((0, 0, -bob * (0.5 + 0.5 * math.cos(2 * ph)))))
        acts.append(act)

    act = start(arm, "attack")
    T = 24
    for f in range(0, T + 1, 2):
        t = f / T
        crouch = util_smooth(t / 0.35) * (1 - util_smooth((t - 0.35) / 0.1))
        lunge = util_smooth((t - 0.35) / 0.15) * (1 - util_smooth((t - 0.65) / 0.35))
        bite = util_smooth((t - 0.3) / 0.1) * (1 - util_smooth((t - 0.55) / 0.1))
        dl = {"hips": qa(X, 6 * crouch - 8 * lunge), "spine": qa(X, 6 * crouch),
              "neck": qa(X, -20 * crouch + 10 * lunge), "head": qa(X, 12 * crouch - 12 * lunge),
              "jaw": qa(X, 38 * bite), "tail.1": qa(X, -20 * crouch)}
        for side in ("L", "R"):
            dl[f"upperarm.{side}"] = qa(X, 10 * crouch + 30 * lunge)
            dl[f"foreleg.{side}"] = qa(X, 20 * crouch)
            dl[f"thigh.{side}"] = qa(X, -20 * crouch - 25 * lunge)
            dl[f"shin.{side}"] = qa(X, -20 * crouch)
            dl[f"hock.{side}"] = qa(X, 25 * crouch)
        poser.key(f + 1, dl, V((0, -0.35 * lunge, -0.12 * crouch + 0.12 * lunge)))
    acts.append(act)

    act = start(arm, "hit")
    T = 12
    for f in range(0, T + 1, 2):
        k = math.sin(math.pi * f / T)
        dl = {"hips": qa(Y, 6 * k), "neck": qa(X, 15 * k) @ qa(Z, 10 * k), "head": qa(X, 10 * k),
              "jaw": qa(X, 20 * k), "tail.1": qa(X, 15 * k)}
        poser.key(f + 1, dl, V((0, 0.06 * k, 0)))
    acts.append(act)

    act = start(arm, "death")
    T = 40
    for f in range(0, T + 1, 2):
        t = f / T
        k = util_smooth(t / 0.6)
        dl = {"hips": qa(Y, 82 * k), "neck": qa(X, 20 * k) @ qa(Z, 15 * k), "head": qa(X, 10 * k),
              "jaw": qa(X, 16 * k), "tail.1": qa(Z, 20 * k)}
        for side in ("L", "R"):
            dl[f"upperarm.{side}"] = qa(X, 20 * k)
            dl[f"thigh.{side}"] = qa(X, -20 * k)
            dl[f"foreleg.{side}"] = qa(X, 25 * k)
            dl[f"shin.{side}"] = qa(X, -25 * k)
        poser.key(f + 1, dl, V((0.35 * k, 0, -0.72 * util_smooth((t - 0.1) / 0.5))))
    acts.append(act)
    arm.animation_data.action = acts[0]
    return acts


# --------------------------------------------------------------------------
# Jiao serpent (flood dragon)
# --------------------------------------------------------------------------
SEG = 16


def serpent_bones(s):
    """A chain from the tail tip (+Y) to the head (-Y); the body lies 0.7 m above ground."""
    b = {}
    length = 13.0
    y0 = length * 0.55
    prev = None
    z = 0.7
    for i in range(SEG):
        a = V((0, y0 - length * i / SEG, z))
        c = V((0, y0 - length * (i + 1) / SEG, z))
        name = f"body.{i:02d}"
        b[name] = (a, c, prev)
        prev = name
    head_base = b[prev][1]
    b["head"] = (head_base, head_base + V((0, -1.1, 0.05)), prev)
    b["jaw"] = (head_base + V((0, -0.2, -0.18)), head_base + V((0, -1.0, -0.22)), "head")
    return {n: (h * s, t * s, p) for n, (h, t, p) in b.items()}


def serpent_radius(t):
    """Body radius from the tail tip (t = 0) to the neck (t = 1)."""
    return 0.08 + 0.52 * math.sin(math.pi * min(1.0, t * 0.62 + 0.08)) ** 0.8 * (1 - 0.35 * t ** 3)


def build_serpent():
    util.reset_scene()
    s = 1.0
    B = serpent_bones(s)
    cfg = dict(name="jiao_serpent")
    arm = characters.build_armature(cfg, B)
    smaps = scales("#1f5a5a", "#d9c78f", "#7fe0c8", glow="#58ffd8")
    scale_m = util.material("jiao_scales", smaps, normal_strength=1.2, emission_map=smaps["emission"],
                            emission_strength=1.5)
    horn = util.material("jiao_horn", tex.lacquer("#d8cfb4", 256, 53, wear=0.5), normal_strength=0.5)
    fin_maps = tex.sheer("#58d0b8")
    fin = util.material("jiao_fin", fin_maps, alpha=0.85, double_sided=True, normal_strength=0.2)
    eye = util.material("jiao_eye", color="#ffd84a", rough=0.05, emission="#ffb020", emission_strength=6.0)
    teeth = util.material("jiao_teeth", color="#f2ecdc", rough=0.3)
    parts = []
    names = [f"body.{i:02d}" for i in range(SEG)]
    path = [B[names[0]][0]] + [B[n][1] for n in names]
    pts = util.catmull(path, 3)
    bm = bmesh.new()
    util.tube(bm, pts, lambda t: (serpent_radius(t) * 1.05, serpent_radius(t)), n=18, up=(0, 0, 1),
              uv_scale=(1.0, 0.35))
    body = util.mesh_object("Body", bm, scale_m)
    weigh(body, B, names + ["head"], power=4.0)
    parts.append(body)
    # dorsal fin / mane running along the back
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    rows = []
    for k, p in enumerate(pts):
        t = k / (len(pts) - 1)
        r = serpent_radius(t)
        h = 0.12 + 0.28 * math.sin(math.pi * t) + 0.1 * abs(math.sin(k * 0.9))
        rows.append((bm.verts.new(p + V((0, 0, r * 0.92))), bm.verts.new(p + V((0, 0.08, r + h)))))
    for k in range(len(rows) - 1):
        f = bm.faces.new((rows[k][0], rows[k + 1][0], rows[k + 1][1], rows[k][1]))
        for loop, (uu, vv) in zip(f.loops, ((k, 0), (k + 1, 0), (k + 1, 1), (k, 1))):
            loop[uvl].uv = (uu * 0.3, vv)
    o = util.mesh_object("Fin", bm, fin)
    weigh(o, B, names, power=4.0)
    parts.append(o)
    # head: long snout, brow ridges, antler horns, whiskers, glowing eyes
    hb, ht, _ = B["head"]
    bm = bmesh.new()
    util.tube(bm, util.catmull([hb + V((0, 0.2, 0)), hb, hb + V((0, -0.5, 0.05)), ht], 3),
              lambda t: (0.42 * (1 - 0.55 * t), 0.36 * (1 - 0.6 * t)), n=16, up=(0, 0, 1))
    for side in (1, -1):
        util.sphere(bm, 0.14, loc=hb + V((side * 0.22, -0.3, 0.22)), segs=10, rings=6, scale=(0.8, 1.6, 0.6))
    head = util.mesh_object("Head", bm, scale_m)
    util.subdivide(head, 1)
    rigid(head, "head")
    parts.append(head)
    bm = bmesh.new()
    jb, jt, _ = B["jaw"]
    util.tube(bm, [jb, jb.lerp(jt, 0.5), jt], lambda t: (0.3 * (1 - 0.6 * t), 0.12 * (1 - 0.5 * t)), n=12,
              up=(0, 0, 1))
    o = util.mesh_object("Jaw", bm, scale_m)
    rigid(o, "jaw")
    parts.append(o)
    bm = bmesh.new()
    for side in (1, -1):
        root = hb + V((side * 0.2, 0.05, 0.3))
        horn_path = [root, root + V((side * 0.15, 0.2, 0.35)), root + V((side * 0.2, 0.55, 0.55)),
                     root + V((side * 0.15, 0.95, 0.6))]
        util.tube(bm, util.catmull(horn_path, 4), lambda t: 0.07 * (1 - 0.85 * t), n=8)
        tine = [root + V((side * 0.17, 0.35, 0.45)), root + V((side * 0.35, 0.4, 0.75))]
        util.tube(bm, tine, lambda t: 0.035 * (1 - 0.8 * t), n=6)
    o = util.mesh_object("Horns", bm, horn)
    util.box_uv(o, 3)
    rigid(o, "head")
    parts.append(o)
    bm = bmesh.new()
    for side in (1, -1):
        base = ht + V((side * 0.1, 0.12, 0.05))
        wh = [base, base + V((side * 0.3, 0.1, 0.1)), base + V((side * 0.7, 0.4, -0.2)), base + V((side * 0.9, 0.9, -0.5))]
        util.tube(bm, util.catmull(wh, 4), lambda t: 0.018 * (1 - 0.8 * t), n=5)
        for k in range(5):   # fangs
            util.cylinder(bm, 0.025, 0.002, 0.12, loc=hb + V((side * (0.1 + 0.03 * k), -0.35 - 0.12 * k, -0.08)), segs=5)
    o = util.mesh_object("Whiskers", bm, teeth)
    rigid(o, "head")
    parts.append(o)
    bm = bmesh.new()
    for side in (1, -1):
        util.sphere(bm, 0.07, loc=hb + V((side * 0.27, -0.28, 0.2)), segs=10, rings=6, scale=(0.7, 1.2, 0.6))
    o = util.mesh_object("Eyes", bm, eye)
    rigid(o, "head")
    parts.append(o)
    meshes = finish(arm, [("Serpent", parts)])
    actions = serpent_actions(arm, B)
    return arm, meshes, actions


def serpent_actions(arm, B):
    poser = Poser(arm, B)
    arm.animation_data_create()
    names = [f"body.{i:02d}" for i in range(SEG)]
    acts = []

    def pose(dl, ph, amp, rear, travel=True, head_pitch=0.0):
        """Lateral S-wave along the body plus the front third reared up like a cobra."""
        for i, n in enumerate(names):
            t = i / (SEG - 1)
            wave = amp * math.sin((ph if travel else 0.0) - t * 2 * math.pi * 1.2 + (0 if travel else ph * 0.2))
            lift = 0.0
            if t > 0.55:
                lift = rear * math.sin(math.pi * (t - 0.55) / 0.45 * 0.5)
            if t > 0.8:
                lift -= rear * 0.9 * (t - 0.8) / 0.2
            dl[n] = qa(Z, wave * (0.3 + 0.7 * (1 - t))) @ qa(X, -lift)
        dl["head"] = qa(X, head_pitch)
        return dl

    act = start(arm, "idle")
    T = 90
    for f in range(0, T + 1, 3):
        ph = 2 * math.pi * f / T
        dl = pose({}, ph, 12, 22 + 4 * math.sin(ph), travel=False, head_pitch=8 + 6 * math.sin(ph))
        dl["jaw"] = qa(X, 6 + 4 * math.sin(ph * 2))
        poser.key(f + 1, dl)
    acts.append(act)
    for name, T, amp in (("walk", 60, 16), ("run", 30, 22)):
        act = start(arm, name)
        for f in range(0, T + 1, 2):
            ph = 2 * math.pi * f / T
            dl = pose({}, ph, amp, 14, head_pitch=6)
            dl["jaw"] = qa(X, 5)
            poser.key(f + 1, dl)
        acts.append(act)
    act = start(arm, "attack")
    T = 36
    for f in range(0, T + 1, 2):
        t = f / T
        coil = util_smooth(t / 0.4) * (1 - util_smooth((t - 0.4) / 0.1))
        strike = util_smooth((t - 0.4) / 0.12) * (1 - util_smooth((t - 0.7) / 0.3))
        dl = pose({}, 0.0, 10, 30 + 25 * coil - 20 * strike, travel=False, head_pitch=-10 * coil + 30 * strike)
        dl["jaw"] = qa(X, 10 + 45 * max(coil * 0.5, strike))
        poser.key(f + 1, dl, V((0, -2.2 * strike + 0.6 * coil, 0)))
    acts.append(act)
    act = start(arm, "hit")
    T = 18
    for f in range(0, T + 1, 2):
        k = math.sin(math.pi * f / T)
        dl = pose({}, 0.0, 12 + 10 * k, 22 + 12 * k, travel=False, head_pitch=-20 * k)
        dl["jaw"] = qa(X, 30 * k)
        poser.key(f + 1, dl, V((0, 0.4 * k, 0)))
    acts.append(act)
    act = start(arm, "death")
    T = 60
    for f in range(0, T + 1, 2):
        t = f / T
        k = util_smooth(t / 0.7)
        dl = pose({}, 0.0, 12 * (1 - k) + 25 * k, 22 * (1 - k), travel=False, head_pitch=-30 * k)
        dl["jaw"] = qa(X, 25 * k)
        dl[names[0]] = dl[names[0]] @ qa(Y, 70 * k)
        poser.key(f + 1, dl, V((0, 0, -0.35 * k)))
    acts.append(act)
    arm.animation_data.action = acts[0]
    return acts


CREATURES = {
    "stone_golem": build_golem,
    "spirit_wolf": build_wolf,
    "jiao_serpent": build_serpent,
}

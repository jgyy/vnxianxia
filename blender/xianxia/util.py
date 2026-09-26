"""Blender helpers shared by the character and environment builders."""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

from . import tex

_TEX_CACHE = {}
_MAT_CACHE = {}


# --------------------------------------------------------------------------
# scene
# --------------------------------------------------------------------------
def reset_scene():
    """Start from an empty file (keeps data-block caches consistent)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _TEX_CACHE.clear()
    _MAT_CACHE.clear()
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.unit_settings.system = "METRIC"
    return scene


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


# --------------------------------------------------------------------------
# images & materials
# --------------------------------------------------------------------------
def image_from_array(name, arr, non_color=False):
    """(H, W, 3|4) float array -> packed Blender image (row 0 = bottom)."""
    h, w = arr.shape[:2]
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=2)
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    img.pixels.foreach_set(np.ascontiguousarray(arr, np.float32).ravel())
    img.pack()
    img.file_format = "PNG"
    return img


def material(name, maps=None, color=None, rough=0.5, metal=0.0, normal_strength=1.0,
             emission=None, emission_strength=1.0, alpha=None, double_sided=False,
             normal_bump=2.0, emission_map=None, detail_div=1):
    """Principled material built in the node layout the glTF exporter understands.

    maps: dict from tex.* (albedo/rough/metal/height) or None for flat colour.
    detail_div: bake the metal/roughness map at 1/n and the normal map at 1/sqrt(n)...
    of the albedo resolution (keeps file sizes sane for large face textures).
    """
    key = name
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if maps is not None:
        alb = maps["albedo"]
        if alpha is not None and np.ndim(alpha) == 2:
            alb = np.concatenate([alb, alpha[..., None]], axis=2)
        img = image_from_array(name + "_albedo", alb)
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = img
        tn.location = (-400, 200)
        nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha is not None and np.ndim(alpha) == 2:
            nt.links.new(tn.outputs["Alpha"], bsdf.inputs["Alpha"])
        # packed metallic/roughness (glTF: G = roughness, B = metallic)
        rough_m, metal_m = maps["rough"], maps["metal"]
        if detail_div > 1:
            rough_m, metal_m = _downsample(rough_m, detail_div * 2), _downsample(metal_m, detail_div * 2)
        s = rough_m.shape[0]
        mr = np.stack([np.ones((s, s), np.float32), rough_m, metal_m], axis=-1)
        mimg = image_from_array(name + "_mr", mr, non_color=True)
        mn = nt.nodes.new("ShaderNodeTexImage")
        mn.image = mimg
        mn.location = (-400, -100)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.location = (-100, -100)
        nt.links.new(mn.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        if maps.get("height") is not None and normal_strength > 0:
            height = maps["height"]
            if detail_div > 1:
                height = _downsample(height, detail_div)
            nimg = image_from_array(name + "_normal",
                                    tex.normal_from_height(height, normal_bump),
                                    non_color=True)
            nn = nt.nodes.new("ShaderNodeTexImage")
            nn.image = nimg
            nn.location = (-400, -400)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-100, -400)
            nm.inputs["Strength"].default_value = normal_strength
            nt.links.new(nn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        c = tex.srgb(color) if isinstance(color, str) else color
        lin = [srgb_to_linear(x) for x in c]
        bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
    if emission_map is not None:
        eimg = image_from_array(name + "_emit", emission_map)
        en = nt.nodes.new("ShaderNodeTexImage")
        en.image = eimg
        en.location = (-400, -700)
        nt.links.new(en.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if emission is not None:
        c = tex.srgb(emission)
        bsdf.inputs["Emission Color"].default_value = (*[srgb_to_linear(x) for x in c], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if alpha is not None:
        if np.ndim(alpha) == 0:
            bsdf.inputs["Alpha"].default_value = float(alpha)
        mat.surface_render_method = "BLENDED" if np.ndim(alpha) == 0 else "DITHERED"
    mat.use_backface_culling = not double_sided
    _MAT_CACHE[key] = mat
    return mat


def _downsample(a, n):
    """Box-filter a square 2-D array by an integer factor."""
    h = a.shape[0] // n
    return a[:h * n, :h * n].reshape(h, n, h, n).mean(axis=(1, 3)).astype(np.float32)


def srgb_to_linear(c):
    c = float(c)
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# --------------------------------------------------------------------------
# mesh construction
# --------------------------------------------------------------------------
def mesh_object(name, bm, mat=None, smooth=True, collection=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    link(obj, collection)
    if mat is not None:
        if isinstance(mat, (list, tuple)):
            for m in mat:
                me.materials.append(m)
        else:
            me.materials.append(mat)
    if smooth:
        me.shade_smooth()
    else:
        me.shade_flat()
    return obj


def ring(center, xa, ya, rx, ry, n, start=0.0, power=2.0):
    """Superellipse ring of n points in the plane spanned by xa, ya."""
    pts = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / power
        cx = math.copysign(abs(c) ** e, c)
        sy = math.copysign(abs(s) ** e, s)
        pts.append(Vector(center) + Vector(xa) * (rx * cx) + Vector(ya) * (ry * sy))
    return pts


def loft(bm, rings, closed=True, cap_start=False, cap_end=False, uv_scale=(1.0, 1.0),
         v_values=None, uv_offset=(0.0, 0.0)):
    """Skin a list of equal-length point rings into quads with cylindrical UVs.

    UV u follows the ring (0..1 * uv_scale[0]); v follows cumulative length.
    Returns list of vert rows.
    """
    rows = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    uv = bm.loops.layers.uv.verify()
    # cumulative length along the loft (average ring centre distance)
    if v_values is None:
        v_values = [0.0]
        for a, b in zip(rings[:-1], rings[1:]):
            ca = sum(a, Vector()) / len(a)
            cb = sum(b, Vector()) / len(b)
            v_values.append(v_values[-1] + (cb - ca).length)
    m = n if closed else n - 1
    for j in range(len(rows) - 1):
        for i in range(m):
            i2 = (i + 1) % n
            f = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            us = (i / n, (i + 1) / n) if closed else (i / (n - 1), (i + 1) / (n - 1))
            coords = ((us[0], v_values[j]), (us[1], v_values[j]),
                      (us[1], v_values[j + 1]), (us[0], v_values[j + 1]))
            for loop, (uu, vv) in zip(f.loops, coords):
                loop[uv].uv = (uu * uv_scale[0] + uv_offset[0], vv * uv_scale[1] + uv_offset[1])
    if cap_start:
        f = bm.faces.new(list(reversed(rows[0])))
        _planar_uv(f, uv)
    if cap_end:
        f = bm.faces.new(rows[-1])
        _planar_uv(f, uv)
    return rows


def _planar_uv(face, uv, scale=1.0):
    n = face.normal if face.normal.length > 0 else Vector((0, 0, 1))
    ax = max(range(3), key=lambda k: abs(n[k]))
    a, b = [k for k in range(3) if k != ax]
    for loop in face.loops:
        co = loop.vert.co
        loop[uv].uv = (co[a] * scale, co[b] * scale)


def frames_along(path):
    """Parallel-transport frames (tangent, normal, binormal) along a poly-line."""
    tangents = []
    for i in range(len(path)):
        if i == 0:
            t = path[1] - path[0]
        elif i == len(path) - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        tangents.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tangents[0].cross(ref).normalized()
    frames = []
    for i, t in enumerate(tangents):
        if i > 0:
            q = tangents[i - 1].rotation_difference(t)
            nrm = (q @ nrm).normalized()
        b = t.cross(nrm).normalized()
        frames.append((t, nrm, b))
    return frames


def tube(bm, path, radius, n=12, closed_ends=True, profile=None, up=None, power=2.0,
         uv_scale=(1.0, 1.0)):
    """Sweep a (super)ellipse along a path.

    radius: float, callable t -> float or (rx, ry)
    profile: optional callable t -> (dx, dy) offset of ring centre in (n, b) frame.
    up: optional fixed 'up' vector so the ring x axis stays horizontal-ish.
    """
    path = [Vector(p) for p in path]
    frames = frames_along(path)
    rings = []
    total = len(path) - 1
    for i, (p, (t, nrm, b)) in enumerate(zip(path, frames)):
        s = i / total if total else 0
        if up is not None:
            b = t.cross(Vector(up)).normalized()
            if b.length < 1e-6:
                b = nrm
            nrm = b.cross(t).normalized()
        r = radius(s) if callable(radius) else radius
        rx, ry = (r, r) if not isinstance(r, (tuple, list)) else r
        c = p.copy()
        if profile is not None:
            dx, dy = profile(s)
            c += nrm * dx + b * dy
        rings.append(ring(c, b, nrm, rx, ry, n, power=power))
    return loft(bm, rings, closed=True, cap_start=closed_ends, cap_end=closed_ends,
                uv_scale=uv_scale)


def catmull(points, samples=8):
    """Catmull-Rom interpolate a list of points."""
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def box(bm, size, loc=(0, 0, 0), rot=None):
    """Axis-aligned (optionally rotated) box with per-face UVs."""
    m = Matrix.Translation(Vector(loc))
    if rot is not None:
        m = m @ (rot.to_matrix().to_4x4() if isinstance(rot, Quaternion) else rot)
    m = m @ Matrix.Diagonal((*size, 1.0))
    bm.loops.layers.uv.verify()
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=m, calc_uvs=True)
    return res["verts"]


def cylinder(bm, r1, r2, depth, loc=(0, 0, 0), segs=16, rot=None, cap=True):
    m = Matrix.Translation(Vector(loc))
    if rot is not None:
        m = m @ (rot.to_matrix().to_4x4() if isinstance(rot, Quaternion) else rot)
    bm.loops.layers.uv.verify()
    res = bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1,
                                radius2=r2, depth=depth, matrix=m, calc_uvs=True)
    return res["verts"]


def sphere(bm, r, loc=(0, 0, 0), segs=16, rings=10, scale=(1, 1, 1)):
    m = Matrix.Translation(Vector(loc)) @ Matrix.Diagonal((*scale, 1.0))
    bm.loops.layers.uv.verify()
    res = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r, matrix=m,
                                    calc_uvs=True)
    return res["verts"]


def lathe(bm, profile, segs=24, loc=(0, 0, 0), cap_top=False, cap_bottom=False, uv_v=1.0):
    """Revolve a list of (radius, z) about Z."""
    rings = []
    for (r, z) in profile:
        rings.append(ring((loc[0], loc[1], loc[2] + z), (1, 0, 0), (0, 1, 0), max(r, 1e-4),
                          max(r, 1e-4), segs))
    return loft(bm, rings, closed=True, cap_start=cap_bottom, cap_end=cap_top,
                uv_scale=(1.0, uv_v))


# --------------------------------------------------------------------------
# object level operations
# --------------------------------------------------------------------------
def apply_modifiers(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    return obj


def subdivide(obj, levels=1):
    mod = obj.modifiers.new("subd", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    mod.uv_smooth = "PRESERVE_BOUNDARIES"
    return apply_modifiers(obj)


def solidify(obj, thickness, offset=-1.0):
    mod = obj.modifiers.new("solid", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    return apply_modifiers(obj)


def box_uv(obj, scale=1.0, faces=None):
    """Tri-planar style box projection in object space (metres * scale)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        if faces is not None and f.index not in faces:
            continue
        n = f.normal
        ax = max(range(3), key=lambda k: abs(n[k]))
        if ax == 0:
            a, b, sa = 1, 2, (1 if n.x > 0 else -1)
        elif ax == 1:
            a, b, sa = 0, 2, (-1 if n.y > 0 else 1)
        else:
            a, b, sa = 0, 1, 1
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = (co[a] * scale * sa, co[b] * scale)
    bm.to_mesh(me)
    bm.free()


def join(objs, name):
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    with bpy.context.temp_override(active_object=objs[0], object=objs[0],
                                   selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def apply_transform(obj):
    me = obj.data
    me.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix.Identity(4)


def set_origin(obj, point):
    point = Vector(point)
    obj.data.transform(Matrix.Translation(-point))
    obj.location = obj.location + point


def delete_objects(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def collider(name, size, loc, rot_z=0.0, convex=True, collection=None):
    """Invisible collision box picked up by Godot's '-colonly' import hint."""
    bm = bmesh.new()
    box(bm, size, loc=(0, 0, 0))
    suffix = "-convcolonly" if convex else "-colonly"
    obj = mesh_object(name + suffix, bm, None, smooth=False, collection=collection)
    obj.location = loc
    obj.rotation_euler = (0, 0, rot_z)
    apply_transform(obj)
    return obj


def export_glb(path, objects=None, animations=False, jpeg=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if objects is not None:
        for o in bpy.context.view_layer.objects:
            o.select_set(o in objects)
    kwargs = dict(
        filepath=path,
        export_format="GLB",
        use_selection=objects is not None,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_image_format="JPEG" if jpeg else "AUTO",
        export_jpeg_quality=88,
        export_animations=animations,
        export_extras=False,
        export_cameras=False,
        export_lights=False,
    )
    if animations:
        kwargs.update(
            export_animation_mode="ACTIONS",
            export_frame_range=False,
            export_force_sampling=True,
            export_anim_single_armature=True,
            export_skins=True,
            export_all_influences=False,
            export_def_bones=True,
            export_optimize_animation_size=True,
        )
    bpy.ops.export_scene.gltf(**kwargs)
    return path

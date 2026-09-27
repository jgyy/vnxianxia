"""Primitives for the HUD kit (blender/render_hud.py).

Everything is laid out in *logical HUD pixels* (the size a piece occupies on a
1280x720 screen) with the origin at the top-left of the piece's canvas and y
pointing down, exactly like the Godot control that will show it. ``Canvas``
converts those coordinates to Blender space (1 px = ``U`` metres, y up) and
renders the piece with an orthographic camera looking straight down, so the
bevels, gold leaf, jade and lacquer are lit like small carved objects.

Materials: gilt (gold leaf with a faint crinkle bump), bronze (dark, with a
verdigris wash), lacquer (ink-black jade with a clear coat and an ink-wash
cloud pattern), jade (subsurface, faint veins), silk (indigo ink), and the
emissive "liquid" fills of the gauges.
"""
import math
import os

import bpy  # noqa: I001  (bpy must be imported before bmesh)
import bmesh
import numpy as np

U = 0.01  # Blender metres per logical pixel


# ---------------------------------------------------------------- scene setup

def reset_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def setup_render(samples=48, threads=3):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.seed = 7
    scene.render.threads_mode = "FIXED"
    scene.render.threads = threads
    scene.render.film_transparent = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 90
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    _world(scene)
    return scene


def _world(scene):
    """A studio 'sky': warm bright overhead, cool dim horizon. The gold and
    jade reflect it, which is what makes them read as metal and stone."""
    world = bpy.data.worlds.get("HudWorld") or bpy.data.worlds.new("HudWorld")
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.05, 0.06, 0.08, 1)
    # straight overhead stays dim so flat lacquer reads as deep black-jade;
    # the bright warm band just below it is what bevels and wires catch.
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.16, 0.15, 0.14, 1)
    e = cr.elements.new(0.45)
    e.color = (0.25, 0.3, 0.36, 1)
    e = cr.elements.new(0.62)
    e.color = (0.06, 0.06, 0.07, 1)
    e = cr.elements.new(0.8)
    e.color = (1.0, 0.86, 0.62, 1)
    e = cr.elements.new(0.93)
    e.color = (0.5, 0.45, 0.38, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    nt.links.new(bg.outputs[0], out.inputs[0])
    scene.world = world


def _sun(rot, energy, color=(1, 0.96, 0.9), angle=12.0):
    data = bpy.data.lights.new("Sun", "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(angle)
    ob = bpy.data.objects.new("Sun", data)
    ob.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(ob)
    return ob


class Canvas:
    """One HUD piece: w x h logical px, rendered at ``scale`` x."""

    def __init__(self, w, h, scale=2, shadow=True, key=3.2):
        reset_scene()
        self.w, self.h, self.scale = w, h, scale
        scene = bpy.context.scene
        scene.render.resolution_x = int(round(w * scale))
        scene.render.resolution_y = int(round(h * scale))
        cam = bpy.data.cameras.new("HudCam")
        cam.type = "ORTHO"
        cam.ortho_scale = max(w, h) * U
        cam.clip_start = 0.001
        cam.clip_end = 10
        ob = bpy.data.objects.new("HudCam", cam)
        ob.location = (0, 0, 2)
        scene.collection.objects.link(ob)
        scene.camera = ob
        # key light from the upper left (as seen on screen), a cool fill from
        # the lower right; long shadows would smear, so the key stays high.
        _sun((32, -26, 0), key)
        _sun((-38, 30, 0), 0.7, (0.75, 0.85, 1.0), 25)
        if shadow:
            bm = bmesh.new()
            bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=max(w, h) * U * 2)
            me = bpy.data.meshes.new("Catcher")
            bm.to_mesh(me)
            bm.free()
            cob = bpy.data.objects.new("Catcher", me)
            cob.is_shadow_catcher = True
            cob.location.z = -0.0005
            scene.collection.objects.link(cob)

    # canvas px (y down) -> blender metres (y up), centred
    def p(self, x, y, z=0.0):
        return ((x - self.w / 2) * U, (self.h / 2 - y) * U, z * U)

    def link(self, ob):
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def render(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("wrote", path)


# ---------------------------------------------------------------- materials

_MATS = {}


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    return m, nt, bsdf


def _noise(nt, scale, detail=4.0, rough=0.6, coord="Object", distortion=0.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = distortion
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    return n


def _ramp(nt, src, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(src, r.inputs[0])
    cr = r.color_ramp
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, col in stops[1:-1]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    return r


def _bump(nt, bsdf, height_src, strength):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = 0.0002
    nt.links.new(height_src, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def mat(kind, tint=None):
    key = (kind, tint)
    if key in _MATS and _MATS[key].name in bpy.data.materials:
        return _MATS[key]
    m = _make(kind, tint)
    _MATS[key] = m
    return m


def _make(kind, tint):
    if kind == "holdout":
        m = bpy.data.materials.new("holdout")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        h = nt.nodes.new("ShaderNodeHoldout")
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(h.outputs[0], o.inputs["Surface"])
        return m
    m, nt, bsdf = _principled(kind)
    if kind in ("gold", "gold_dim", "gold_grey"):
        base = {"gold": (1.0, 0.74, 0.34), "gold_dim": (0.72, 0.52, 0.26), "gold_grey": (0.5, 0.48, 0.44)}[kind]
        bsdf.inputs["Base Color"].default_value = (*base, 1)
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.26
        n = _noise(nt, 420.0, 3.0, 0.5)
        _bump(nt, bsdf, n.outputs["Fac"], 0.12)
    elif kind == "gold_bright":
        bsdf.inputs["Base Color"].default_value = (1.0, 0.86, 0.5, 1)
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.18
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.8, 0.45, 1)
        bsdf.inputs["Emission Strength"].default_value = 0.25
    elif kind == "bronze":
        n = _noise(nt, 90.0, 5.0, 0.65)
        r = _ramp(nt, n.outputs["Fac"], [(0.35, (0.34, 0.22, 0.12)), (0.55, (0.26, 0.2, 0.14)), (0.72, (0.18, 0.3, 0.26))])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Metallic"].default_value = 0.85
        bsdf.inputs["Roughness"].default_value = 0.42
        _bump(nt, bsdf, n.outputs["Fac"], 0.08)
    elif kind in ("lacquer", "lacquer_hover", "lacquer_press", "lacquer_grey", "lacquer_red"):
        base = {
            "lacquer": ((0.0006, 0.001, 0.0014), (0.0045, 0.0085, 0.0085)),
            "lacquer_hover": ((0.008, 0.02, 0.018), (0.03, 0.065, 0.052)),
            "lacquer_press": ((0.012, 0.008, 0.003), (0.04, 0.026, 0.01)),
            "lacquer_grey": ((0.006, 0.006, 0.007), (0.018, 0.018, 0.02)),
            "lacquer_red": ((0.03, 0.003, 0.003), (0.1, 0.012, 0.01)),
        }[kind]
        # ink-wash clouds: stretched, distorted noise
        n = _noise(nt, 2.2, 6.0, 0.62, distortion=0.8)
        r = _ramp(nt, n.outputs["Fac"], [(0.38, base[0]), (0.62, base[1])])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.5
        # the broad base highlight of the key light washes lacquer out to grey
        # (the camera looks straight down); keep only the tight clear coat.
        bsdf.inputs["Specular IOR Level"].default_value = 0.08
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat IOR"].default_value = 1.3
        bsdf.inputs["Coat Roughness"].default_value = 0.12
        fine = _noise(nt, 260.0, 2.0, 0.5)
        _bump(nt, bsdf, fine.outputs["Fac"], 0.04)
    elif kind == "silk":
        n = _noise(nt, 3.0, 6.0, 0.6, distortion=1.2)
        r = _ramp(nt, n.outputs["Fac"], [(0.35, (0.0015, 0.002, 0.0035)), (0.65, (0.007, 0.01, 0.014))])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.62
        bsdf.inputs["Specular IOR Level"].default_value = 0.12
        bsdf.inputs["Sheen Weight"].default_value = 0.35
        bsdf.inputs["Sheen Tint"].default_value = (0.7, 0.8, 0.75, 1)
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.inputs["Scale"].default_value = 180.0
        wave.inputs["Distortion"].default_value = 0.0
        _bump(nt, bsdf, wave.outputs["Fac"], 0.03)
    elif kind in ("jade", "jade_dark", "jade_pale", "rose_jade"):
        c1, c2 = {
            "jade": ((0.09, 0.42, 0.3), (0.35, 0.72, 0.55)),
            "jade_dark": ((0.03, 0.16, 0.12), (0.1, 0.32, 0.24)),
            "jade_pale": ((0.5, 0.78, 0.66), (0.82, 0.95, 0.86)),
            "rose_jade": ((0.75, 0.42, 0.45), (0.98, 0.82, 0.8)),
        }[kind]
        n = _noise(nt, 40.0, 6.0, 0.7, distortion=2.0)
        r = _ramp(nt, n.outputs["Fac"], [(0.3, c1), (0.7, c2)])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(r.outputs["Color"], bsdf.inputs["Subsurface Radius"])
        bsdf.inputs["Subsurface Weight"].default_value = 0.6
        bsdf.inputs["Subsurface Scale"].default_value = 0.02
        bsdf.inputs["Roughness"].default_value = 0.14
        bsdf.inputs["Coat Weight"].default_value = 0.6
        bsdf.inputs["Coat Roughness"].default_value = 0.05
    elif kind.startswith("liquid"):
        col, glow = {
            "liquid_hp": ((0.45, 0.01, 0.005), (0.95, 0.07, 0.02)),
            "liquid_qi": ((0.03, 0.2, 0.62), (0.2, 0.62, 1.0)),
            "liquid_xp": ((0.05, 0.45, 0.28), (0.45, 1.0, 0.7)),
            "liquid_boss": ((0.3, 0.005, 0.01), (0.8, 0.03, 0.06)),
            "liquid_ring": ((0.03, 0.3, 0.2), (0.2, 0.8, 0.55)),
        }[kind]
        # swirling liquid: distorted noise drives the emission
        n = _noise(nt, 14.0, 5.0, 0.55, distortion=3.0)
        r = _ramp(nt, n.outputs["Fac"], [(0.3, tuple(c * 0.55 for c in glow)), (0.55, glow), (0.8, tuple(min(1, c * 1.25 + 0.15) for c in glow))])
        bsdf.inputs["Base Color"].default_value = (*col, 1)
        nt.links.new(r.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.7
        bsdf.inputs["Roughness"].default_value = 0.08
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.02
    elif kind == "ink":
        bsdf.inputs["Base Color"].default_value = (0.01, 0.012, 0.014, 1)
        bsdf.inputs["Roughness"].default_value = 0.6
    else:
        raise ValueError(kind)
    return m


# ---------------------------------------------------------------- geometry

def rounded_rect_pts(x0, y0, x1, y1, r, seg=10):
    """Closed outline (clockwise on screen) of a rounded rectangle."""
    r = max(0.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = []
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    for cx, cy, a0 in corners:
        if r == 0:
            pts.append((cx, cy))
            continue
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle_pts(cx, cy, r, seg=64):
    return [(cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


def slab(cv, outlines, depth, bevel, material, z=0.0, bevel_res=4):
    """Extruded, bevelled 2D shape. ``outlines`` is a list of closed point
    lists (px); inner outlines become holes. Bevel grows the shape outward by
    ``bevel`` px, so callers inset their outlines by that much."""
    cu = bpy.data.curves.new("slab", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = max(0.0, depth / 2 - bevel) * U
    cu.bevel_depth = bevel * U
    cu.bevel_resolution = bevel_res
    for pts in outlines:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, (x, y) in enumerate(pts):
            bx, by, _ = cv.p(x, y)
            sp.points[i].co = (bx, by, 0, 1)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new("slab", cu)
    ob.location.z = (z + depth / 2) * U
    cu.materials.append(material)
    return cv.link(ob)


def tube(cv, pts, radius, material, z=0.0, closed=False, radii=None, res=3):
    """A round gilt wire along ``pts`` (px), optional per-point radius factors."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius * U
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, pt in enumerate(pts):
        x, y = pt[0], pt[1]
        zz = pt[2] if len(pt) > 2 else z
        sp.points[i].co = (*cv.p(x, y, zz), 1)
        sp.points[i].radius = radii[i] if radii else 1.0
    sp.use_cyclic_u = closed
    ob = bpy.data.objects.new("tube", cu)
    cu.materials.append(material)
    return cv.link(ob)


def sphere(cv, x, y, z, r, material, squash=1.0, sx=1.0, sy=1.0, rot=0.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r * U)
    me = bpy.data.meshes.new("sphere")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new("sphere", me)
    ob.location = cv.p(x, y, z)
    ob.scale = (sx, sy, squash)
    ob.rotation_euler = (0, 0, rot)
    me.materials.append(material)
    return cv.link(ob)


def cylinder_x(cv, x0, x1, y, z, r, material):
    """A horizontal rod (scroll roller) from x0 to x1 at canvas row y."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=r * U, radius2=r * U, depth=(x1 - x0) * U)
    me = bpy.data.meshes.new("rod")
    bm.to_mesh(me)
    bm.free()
    for poly in me.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    ob = bpy.data.objects.new("rod", me)
    ob.location = cv.p((x0 + x1) / 2, y, z)
    ob.rotation_euler = (0, math.radians(90), 0)
    me.materials.append(material)
    return cv.link(ob)


_FONTS = {}


def text(cv, body, font_path, size, x, y, material, z=1.0, extrude=0.6, bevel=0.35):
    """Bevelled gilt text centred on (x, y) px; ``size`` is the em height in px."""
    if font_path not in _FONTS:
        _FONTS[font_path] = bpy.data.fonts.load(font_path)
    cu = bpy.data.curves.new("text", "FONT")
    cu.body = body
    cu.font = _FONTS[font_path]
    cu.size = size * U
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude * U
    cu.bevel_depth = bevel * U
    cu.bevel_resolution = 2
    ob = bpy.data.objects.new("text", cu)
    ob.location = cv.p(x, y, z + extrude)
    cu.materials.append(material)
    return cv.link(ob)


def polygon_path(pts):
    return [(x, y) for x, y in pts]


# ---------------------------------------------------------------- ornaments

def xiangyun(size=1.0):
    """A ruyi cloud scroll: a large curl and a small counter-curl joined by a
    swelling base stroke, plus a tapering tail. Returns [(pts, radii), ...]
    in a unit frame (x right, y up) centred on the big curl."""
    main = []
    turns = 1.45
    n = 70
    for i in range(n + 1):
        t = i / n
        th = -math.pi / 2 - (1 - t) * turns * 2 * math.pi
        r = 0.5 * (0.18 + 0.82 * t)
        main.append((r * math.cos(th), r * math.sin(th)))
    small = []
    c2 = (1.02, -0.14)
    for i in range(1, 56):
        t = i / 55
        th = -math.pi / 2 + t * 1.25 * 2 * math.pi
        r = 0.36 * (1 - 0.72 * t)
        small.append((c2[0] + r * math.cos(th), c2[1] + r * math.sin(th)))
    path = main + small
    radii = []
    for i in range(len(path)):
        if i <= n:
            f = 0.35 + 0.65 * (i / n) ** 0.7
        else:
            f = 1.0 - 0.62 * ((i - n) / len(small)) ** 0.8
        radii.append(f)
    tail = []
    tr = []
    for i in range(25):
        t = i / 24
        tail.append((-0.05 - 0.95 * t, -0.5 - 0.1 * math.sin(t * math.pi) + 0.08 * t))
        tr.append(1.0 - 0.8 * t)
    return [(path, radii), (tail, tr)]


def place(strokes, cx, cy, size, angle=0.0, mirror=False):
    """Transform unit-frame strokes to canvas px (y down)."""
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    out = []
    for pts, radii in strokes:
        tp = []
        for x, y in pts:
            if mirror:
                x = -x
            rx, ry = x * ca - y * sa, x * sa + y * ca
            tp.append((cx + rx * size, cy - ry * size))
        out.append((tp, radii))
    return out


def draw_strokes(cv, strokes, radius, material, z):
    for pts, radii in strokes:
        tube(cv, pts, radius, material, z=z, radii=radii)


# ---------------------------------------------------------------- numpy images

def save_rgba(arr, path):
    """Save an (h, w, 4) float array (0..1, straight alpha, row 0 = top)."""
    h, w, _ = arr.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.alpha_mode = "STRAIGHT"
    img.pixels.foreach_set(np.ascontiguousarray(np.clip(arr[::-1], 0, 1), dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("wrote", path)


def load_rgba(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    bpy.data.images.remove(img)
    return arr.reshape(h, w, 4)[::-1].copy()


def over(top, bottom):
    """Straight-alpha 'over' composite."""
    ta, ba = top[..., 3:4], bottom[..., 3:4]
    oa = ta + ba * (1 - ta)
    rgb = (top[..., :3] * ta + bottom[..., :3] * ba * (1 - ta)) / np.maximum(oa, 1e-6)
    return np.concatenate([rgb, oa], axis=-1)


def box_blur(a, r, axis):
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    p = np.pad(a, pad, mode="edge")
    c = np.cumsum(p, axis=axis)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(a, r):
    """Approximate gaussian (three box passes per axis)."""
    for _ in range(3):
        a = box_blur(a, r, 0)
        a = box_blur(a, r, 1)
    return a


def value_noise(h, w, cell_y, cell_x, seed):
    """Smooth 2D value noise, 0..1, with independent x / y feature sizes."""
    rng = np.random.default_rng(seed)
    gy, gx = int(h / cell_y) + 3, int(w / cell_x) + 3
    g = rng.random((gy, gx))
    ys = np.arange(h) / cell_y
    xs = np.arange(w) / cell_x
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = ys - y0, xs - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    top = a + (b - a) * fx[None, :]
    bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def rounded_mask(h, w, x0, y0, x1, y1, r, aa=1.0):
    """Anti-aliased rounded-rectangle coverage on an (h, w) texel grid."""
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    cx = np.clip(xs, x0 + r, x1 - r)
    cy = np.clip(ys, y0 + r, y1 - r)
    d = np.hypot(xs - cx, ys - cy) - r
    return np.clip(0.5 - d / aa, 0, 1)

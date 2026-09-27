"""Cycles (CPU) preview renders used for documentation screenshots and portraits."""
import math

import bpy
from mathutils import Vector


def setup(res=(960, 960), samples=48, sky=(0.62, 0.72, 0.82), strength=0.9, look="AgX - Medium High Contrast"):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 64   # alpha-tested hair cards stack far deeper than 8
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = look
    world = bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*sky, 1.0)
    bg.inputs["Strength"].default_value = strength
    scene.world = world
    return scene


def sun(rot=(50, 0, 35), energy=3.5, color=(1.0, 0.95, 0.88), angle=3.0):
    data = bpy.data.lights.new("Sun", "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(angle)
    obj = bpy.data.objects.new("Sun", data)
    obj.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(obj)
    return obj


def area(loc, target, energy=150, size=2.0, color=(1, 1, 1), spread=180.0, size_y=None):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy = energy
    data.color = color
    data.spread = math.radians(spread)
    if size_y:
        data.shape = "RECTANGLE"
        data.size = size
        data.size_y = size_y
    else:
        data.size = size
    obj = bpy.data.objects.new("Area", data)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    look_at(obj, target)
    return obj


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=50, ortho=None, focus=None, fstop=None):
    """Camera looking at target; focus (a world point) and fstop enable depth of field."""
    data = bpy.data.cameras.new("Cam")
    data.lens = lens
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    data.clip_end = 2000
    data.clip_start = 0.01
    if focus is not None and fstop:
        data.dof.use_dof = True
        data.dof.focus_distance = (Vector(focus) - Vector(loc)).length
        data.dof.aperture_fstop = fstop
        data.dof.aperture_blades = 7
    obj = bpy.data.objects.new("Cam", data)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    look_at(obj, target)
    bpy.context.scene.camera = obj
    return obj


def ground(size=40, color=(0.35, 0.33, 0.3)):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    me = bpy.data.meshes.new("PreviewGround")
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("PreviewGround")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.9
    me.materials.append(mat)
    obj = bpy.data.objects.new("PreviewGround", me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def backdrop(centre, facing, size=(3.0, 2.2), inner=(0.2, 0.22, 0.25), outer=(0.05, 0.055, 0.065)):
    """A studio backdrop card at centre, facing the direction `facing`, with a soft radial falloff."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=(size[0], size[1], 1.0), verts=bm.verts)
    me = bpy.data.meshes.new("Backdrop")
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x / size[0] + 0.5, lp.vert.co.y / size[1] + 0.5)
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("Backdrop")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Location"].default_value = (0.5, 0.58, 0.0)
    mapn.inputs["Scale"].default_value = (1.6, 1.6, 1.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*outer, 1.0)
    ramp.color_ramp.elements[1].color = (*inner, 1.0)
    nt.links.new(tc.outputs["UV"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    me.materials.append(mat)
    obj = bpy.data.objects.new("Backdrop", me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = centre
    obj.rotation_euler = Vector(facing).to_track_quat("Z", "Y").to_euler()
    return obj


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

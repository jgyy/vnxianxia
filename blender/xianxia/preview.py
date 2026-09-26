"""Cycles (CPU) preview renders used for documentation screenshots."""
import math

import bpy
from mathutils import Vector


def setup(res=(960, 960), samples=48, sky=(0.62, 0.72, 0.82), strength=0.9):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
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


def area(loc, target, energy=150, size=2.0, color=(1, 1, 1)):
    data = bpy.data.lights.new("Area", "AREA")
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new("Area", data)
    obj.location = loc
    bpy.context.scene.collection.objects.link(obj)
    look_at(obj, target)
    return obj


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=50, ortho=None):
    data = bpy.data.cameras.new("Cam")
    data.lens = lens
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    data.clip_end = 2000
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


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

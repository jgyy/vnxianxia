"""Facial rig: eye bones and the head/neck skin weights.

Bones added to the character armature (children of ``head``; the game's
existing bones are untouched):

* ``eye.L`` / ``eye.R`` - at the eyeball centres, Y axis looking forward.  The
  eyeballs, irises and corneas are weighted 100 % to them, so a runtime
  look-at only has to rotate these two bones.  The lids follow gaze through
  the ``lid_look_up`` / ``lid_look_down`` shape keys: set them to
  max(0, pitch) / 25 deg and max(0, -pitch) / 25 deg when aiming the eyes.

Skin weights: the head mesh runs from the crown to the collar, so the neck is
one continuous surface with the jaw.  Weights blend head -> neck -> chest
down the neck along a cut line that follows the jaw in front and the skull
base behind, which keeps the under-chin with the head and spreads the twist
over the whole neck instead of tearing at a seam.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

from . import face_landmarks as fl

EYE_BONES = ("eye.L", "eye.R")


def add_eye_bones(arm, eye_centres, length):
    """Add eye.L / eye.R (parent head) at world eye centres; returns their names."""
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for name, c in zip(EYE_BONES, eye_centres):
        b = eb.new(name)
        b.head = Vector(c)
        b.tail = Vector(c) + Vector((0.0, -length, 0.0))
        b.align_roll(Vector((0.0, 0.0, 1.0)))
        b.parent = eb["head"]
        b.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")
    return EYE_BONES


def eye_rotation(arm, bone, yaw_deg, pitch_deg):
    """Pose-space quaternion turning an eye bone by yaw (+ = toward the character's left) and pitch (+ = up)."""
    rest = arm.data.bones[bone].matrix_local.to_3x3()
    fwd = Vector((0.0, -1.0, 0.0))
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    target = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p)))
    q_world = fwd.rotation_difference(target)
    q_rest = rest.to_quaternion()
    return q_rest.inverted() @ q_world @ q_rest


def _sstep(e0, e1, x):
    t = np.clip((np.asarray(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def neck_weights(P, p: fl.FaceParams):
    """(head, neck, chest) weights for head-mm points of the skin."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # the cut runs under the jaw at the front and at the skull base at the back
    front = _sstep(10.0, -40.0, y)
    cut = p.menton * front + (-38.0) * (1 - front) + 12.0 * _sstep(20.0, 40.0, np.abs(x)) * front
    head = _sstep(cut - 32.0, cut + 6.0, z)
    chest = _sstep(-178.0, -222.0, z)
    neck = np.clip(1.0 - head - chest, 0.0, 1.0)
    return head, neck, chest


def assign_weights(obj, groups):
    """groups: {name: (indices array, weights array)}; zero weights are skipped."""
    for name, (idx, w) in groups.items():
        vg = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
        for i, val in zip(np.asarray(idx).tolist(), np.asarray(w).tolist()):
            if val > 1e-3:
                vg.add([i], float(val), "REPLACE")

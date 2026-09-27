"""Materials for the face slots.

``face_slots(cfg, mats)`` returns {slot name: material}.  characters.make_materials
(hair+skin workstream, skin_eyes.materials) provides

    Eye_Sclera  Eye_Iris  Eye_Cornea  Eye_Tearline  Teeth  Tongue  Lashes  Brows

and those are used as they are; any slot it does not provide (Mouth_Inner:
the mouth bag, gums, conjunctiva and caruncle) gets a plain default here.

UV conventions of the meshes using these slots (face_eyes / face_mouth / face_cards):
* Eye_Sclera - polar about the visual axis: uv = 0.5 + 0.5 * (angle / 90 deg) * (cos, sin);
* Eye_Iris   - planar polar: (0.5, 0.5) = pupil centre, radius 0.5 = limbus;
* Lashes / Brows - u along the lid / brow (each card samples the slice of the strip
  texture at its position), v from the root (0) to the tip (1);
* Teeth / Tongue / Mouth_Inner - any (nearly uniform textures).
"""
from . import util

SLOTS = ("Eye_Sclera", "Eye_Iris", "Eye_Cornea", "Eye_Tearline", "Teeth", "Tongue", "Mouth_Inner", "Lashes",
         "Brows")
DEFAULTS = {
    "Eye_Sclera": dict(color="#ebe4dc", rough=0.2),
    "Eye_Iris": dict(color="#3a2414", rough=0.2),
    "Eye_Cornea": dict(color="#ffffff", rough=0.02, alpha=0.06),
    "Eye_Tearline": dict(color="#f4dcd6", rough=0.03, alpha=0.3),
    "Teeth": dict(color="#e9e3d6", rough=0.28),
    "Tongue": dict(color="#b4555c", rough=0.45),
    "Mouth_Inner": dict(color="#b4646a", rough=0.3),
    "Lashes": dict(color="#1a1010", rough=0.6),
    "Brows": dict(color="#2a1c1a", rough=0.6),
}


def face_slots(cfg, mats):
    """{slot: material} for the head: the character's own materials, plain defaults otherwise."""
    return {name: mats.get(name) or util.material(name, **DEFAULTS[name]) for name in SLOTS}

"""The main story of the Azure Cloud Sect: 10 volumes x 10 chapters x 20 quests.

Authored as Python data (see dsl.py, saga_gen.py) and compiled + validated into
godot/data/story.json by tools/build_story.py. The ten original chapters are
voiced (tools/gen_voices.py, casting in voices.py); the 90 chapters added for
the 2000-quest saga are text-only.
"""

from .cinematics import CINEMATICS
from .npcs import NPCS
from .saga import PREMISE, TITLE
from .voices import NARRATOR, PLAYER_F, PLAYER_M, NPC_VOICES, PRONOUNCE
from .volumes import VOLUMES

CHAPTERS = [c for v in VOLUMES for c in v["chapters"]]

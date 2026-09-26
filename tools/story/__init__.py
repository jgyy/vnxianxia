"""The main story of the Azure Cloud Sect: 10 chapters x 10 quests.

Authored as Python data (see dsl.py) and compiled + validated into
godot/data/story.json by tools/build_story.py. Voice lines are synthesised
by tools/gen_voices.py using the casting in voices.py.
"""

from . import (chapter01, chapter02, chapter03, chapter04, chapter05,
               chapter06, chapter07, chapter08, chapter09, chapter10)
from .cinematics import CINEMATICS
from .npcs import NPCS
from .saga import PREMISE, TITLE
from .voices import NARRATOR, PLAYER_F, PLAYER_M, NPC_VOICES, PRONOUNCE

CHAPTERS = [m.CHAPTER for m in (chapter01, chapter02, chapter03, chapter04, chapter05,
                                chapter06, chapter07, chapter08, chapter09, chapter10)]

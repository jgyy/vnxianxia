"""The saga's structure: 10 volumes, one per major stage of cultivation, each
of 10 chapters of 10 quests.

The ten hand-written chapters of the original story (chapter01..chapter10)
keep their text, voices and cinematics and are slotted in as chapters 1, 2, 3,
11, 12, 21, 22, 31, 41 and 100. The other 90 chapters are outlines in
vol01..vol10 expanded by saga_gen.
"""

import copy

from . import numbering as NB
from . import (chapter01, chapter02, chapter03, chapter04, chapter05,
               chapter06, chapter07, chapter08, chapter09, chapter10)
from . import vol01, vol02, vol03, vol04, vol05, vol06, vol07, vol08, vol09, vol10
from .saga_gen import build_chapter

LEGACY = [m.CHAPTER for m in (chapter01, chapter02, chapter03, chapter04, chapter05,
                              chapter06, chapter07, chapter08, chapter09, chapter10)]
NEW = [vol01.CHAPTERS, vol02.CHAPTERS, vol03.CHAPTERS, vol04.CHAPTERS, vol05.CHAPTERS,
       vol06.CHAPTERS, vol07.CHAPTERS, vol08.CHAPTERS, vol09.CHAPTERS, vol10.CHAPTERS]

# (subtitle, summary) per volume; the title is the realm reached in it.
VOLUME_INFO = [
    ("The Mountain and the Pendant",
     "An orphan climbs nine thousand steps, learns to breathe qi, and finds that red-eyed wolves, caged mortals and a "
     "kindly temple keeper all point to the same buried name: the Blood Moon."),
    ("The Traitor in the Law Hall",
     "The Verdant Lotus ruins open for their heir, the Inner Sect Tournament unmasks Elder Gu, and a sect that trusted "
     "its own law must learn to follow a traitor into the dark."),
    ("Blood Beneath the Earth",
     "A golden core forged in the Abyss, a town held against a siege, and a war of words and swords between the "
     "orthodox sects while the Sky Isles slowly turn toward their opening."),
    ("Isles Above the Clouds",
     "The Sky Isles give up star iron and a nascent soul. The Great Azure Formation rises, and a seven-star mark begins "
     "to appear wherever the Blood Moon is digging."),
    ("The Heart Demon",
     "Elder Mo gives his life to turn the formation back. The last blood moon does not break the seal; instead the "
     "Abyss folds its fortress into the void, and the sect learns to live with grief."),
    ("The Fold in the World",
     "Void rifts open over isle, forest and town. To reach a patriarch hiding between spaces, the Lotus heir learns to "
     "walk where there is nothing to walk on, and the Rungs of his Ladder start to fall."),
    ("A Body Worth Stealing",
     "The Patriarch needs a body clean enough to survive heaven. His Rungs go hunting for one; the answer is to make "
     "body and soul a single thing that cannot be borrowed."),
    ("The Great Vehicle",
     "No one climbs alone. The sects that once quarrelled over the Lotus Key gather into one alliance, and Lady Silk "
     "spins her web through the middle of it."),
    ("Heaven Takes Notice",
     "Clouds gather over every step. Thunder crystals, lightning rods, lesser tribulations and farewells said early: "
     "the long preparation for a sky that is coming to look."),
    ("The Last Blood Moon",
     "The moon turns red, the void unfolds, and the last Rung falls. The Azure Cloud marches into the Abyss, the "
     "Patriarch rides the lightning, and an orphan climbs the Ascension Stair."),
]

# minor stage granted at the end of these chapters: 1 Middle, 2 Late, 3 Peak
STAGE_AT = {4: 1, 7: 2, 10: 3, 14: 1, 17: 2, 20: 3, 24: 1, 27: 2, 30: 3, 34: 1, 37: 2, 40: 3,
            44: 1, 47: 2, 50: 3, 54: 1, 57: 2, 60: 3, 64: 1, 67: 2, 70: 3, 74: 1, 77: 2, 80: 3,
            84: 1, 88: 2, 95: 3}
# breakthroughs granted by new chapters (the legacy chapters grant the first five)
REALM_AT = {51: "Void Refinement", 61: "Body Integration", 71: "Mahayana", 81: "Tribulation Transcendence"}


def _legacy_chapter(k):
    ch = copy.deepcopy(LEGACY[k - 1])
    ch["number"] = NB.LEGACY_CHAPTERS[k]
    ch["legacy"] = k
    for i, q in enumerate(ch["quests"]):
        q["legacy"] = (k - 1) * 10 + i + 1
        q["rewards"].setdefault("stage", None)
    return ch


def build_volumes():
    from world_spec import REALMS
    vols = []
    new_iter = [iter(v) for v in NEW]
    for v in range(1, NB.VOLUMES + 1):
        chapters = []
        for c in range(1, NB.CHAPTERS_PER_VOLUME + 1):
            number = (v - 1) * NB.CHAPTERS_PER_VOLUME + c
            if number in NB.CHAPTER_OF_LEGACY:
                chapters.append(_legacy_chapter(NB.CHAPTER_OF_LEGACY[number]))
            else:
                spec = next(new_iter[v - 1])
                chapters.append(build_chapter(spec, number, realm=REALM_AT.get(number), stage=STAGE_AT.get(number)))
        for it in new_iter[v - 1]:
            raise ValueError("volume %d has too many new chapters (%r)" % (v, it["title"]))
        sub, summary = VOLUME_INFO[v - 1]
        vols.append({"number": v, "title": REALMS[v], "subtitle": sub, "summary": summary, "chapters": chapters})
    return vols


VOLUMES = build_volumes()

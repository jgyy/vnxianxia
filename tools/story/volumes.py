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
from . import morality as MO
from . import tribulations as TR
from .choices import LEGACY as LEGACY_CHOICES
from .saga_gen import attach_choice, build_chapter

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

def schedule(number):
    """(realm, stage) granted by the last quest of chapter ``number``.

    Chapter c of volume v ends at minor stage c of major realm v; chapter 1 is
    the breakthrough (realm and stage 1). The last chapter is the exception:
    its ninth quest reaches Great Perfection (stage 10) of Tribulation
    Transcendence and its tenth grants Immortal Ascension.
    """
    from world_spec import REALMS
    v = NB.volume_of_chapter(number)
    c = number - (v - 1) * NB.CHAPTERS_PER_VOLUME
    if number == NB.TOTAL_CHAPTERS:
        return REALMS[-1], None
    return (REALMS[v] if c == 1 else None), c


def _legacy_chapter(k):
    from world_spec import REALMS
    ch = copy.deepcopy(LEGACY[k - 1])
    number = NB.LEGACY_CHAPTERS[k]
    ch["number"] = number
    ch["legacy"] = k
    realm, stage = schedule(number)
    for i, q in enumerate(ch["quests"]):
        n = (k - 1) * 10 + i + 1
        q["legacy"] = n
        q["rewards"]["stage"] = None
        # hand-written choices after voiced objectives (their lines stay as they are)
        for (lq, oi), choice in LEGACY_CHOICES.items():
            if lq == n:
                attach_choice(q, choice, NB.legacy_to_new(n), at=oi)
    quests = ch["quests"]
    last = quests[-1]
    if last["rewards"]["realm"] != realm:
        raise ValueError("chapter %d should grant %r, grants %r" % (number, realm, last["rewards"]["realm"]))
    if number == NB.TOTAL_CHAPTERS:
        # Heavenly Tribulation: nine times nine before the nine bolts, then Great Perfection
        q = quests[-2]
        med = next(i for i, o in enumerate(q["objectives"]) if o["type"] == "meditate")
        mo = q["objectives"][med]
        m = next((o["map"] for o in reversed(q["objectives"][:med + 1]) if o.get("map")), None) or q["map"]
        q["objectives"].insert(med, _added(TR.make(10, REALMS[10], mo["marker"], m, final=True)))
        q["rewards"]["stage"] = 10
    else:
        last["rewards"]["stage"] = stage
        if realm:
            # the voiced breakthrough meditation is followed by its tribulation
            objs = last["objectives"]
            med = max(i for i, o in enumerate(objs) if o["type"] == "meditate")
            mo = objs[med]
            m = next((o["map"] for o in reversed(objs[:med + 1]) if o.get("map")), None) or last["map"]
            objs.insert(med + 1, _added(TR.make(REALMS.index(realm), realm, mo["marker"], m)))
    return ch


def _added(obj):
    """An objective added to a voiced quest: build_story keeps the voice keys of the others."""
    obj["added"] = True
    return obj


def build_volumes():
    from world_spec import REALMS
    vols = []
    new_iter = [iter(v) for v in NEW]
    for v in range(1, NB.VOLUMES + 1):
        chapters = []
        for c in range(1, NB.CHAPTERS_PER_VOLUME + 1):
            number = (v - 1) * NB.CHAPTERS_PER_VOLUME + c
            if number in NB.CHAPTER_OF_LEGACY:
                ch = _legacy_chapter(NB.CHAPTER_OF_LEGACY[number])
            else:
                spec = next(new_iter[v - 1])
                realm, stage = schedule(number)
                ch = build_chapter(spec, number, realm=realm, stage=stage)
            # the end of every chapter rewards the player's alignment a little
            ch["quests"][-1]["rewards"]["bonus"] = MO.chapter_bonus()
            chapters.append(ch)
        for it in new_iter[v - 1]:
            raise ValueError("volume %d has too many new chapters (%r)" % (v, it["title"]))
        sub, summary = VOLUME_INFO[v - 1]
        vols.append({"number": v, "title": REALMS[v], "subtitle": sub, "summary": summary, "chapters": chapters})
    return vols


VOLUMES = build_volumes()

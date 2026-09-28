"""Numbering of the 2000-quest saga: 10 volumes x 10 chapters x 20 quests.

The ten hand-written chapters of the original 100-quest story ("legacy"
chapters O1..O10) keep their text and voice files and are placed inside the
new structure. Everything here is pure arithmetic so that build_story, the
chapter generator and the runtime agree on ids.
"""

VOLUMES = 10
CHAPTERS_PER_VOLUME = 10
QUESTS_PER_CHAPTER = 20
TOTAL_CHAPTERS = VOLUMES * CHAPTERS_PER_VOLUME
TOTAL_QUESTS = TOTAL_CHAPTERS * QUESTS_PER_CHAPTER

# global chapter number of each legacy chapter O1..O10
LEGACY_CHAPTERS = {1: 1, 2: 2, 3: 3, 4: 11, 5: 12, 6: 21, 7: 22, 8: 31, 9: 41, 10: 100}
CHAPTER_OF_LEGACY = {v: k for k, v in LEGACY_CHAPTERS.items()}
LEGACY_QUESTS_PER_CHAPTER = 10
# Every legacy chapter's original quests must stay in place relative to the
# *end* of their chapter, so new quests can be inserted before them without
# disturbing their meaning (a breakthrough quest, or the game's ending).
# Nine of the ten chapters have a single such "tail" quest (the breakthrough);
# O10 (the finale, chapter 100) has two -- the Great Perfection meditation and
# the Heavenly Tribulation itself both have to land on the chapter's last two
# slots, in order, however many quests get inserted before them.
LEGACY_TAIL_QUESTS = {o: (2 if o == 10 else 1) for o in LEGACY_CHAPTERS}
LEGACY_LEAD_QUESTS = {o: LEGACY_QUESTS_PER_CHAPTER - t for o, t in LEGACY_TAIL_QUESTS.items()}


def qid(n):
    """Quest id of global quest number ``n`` (1..2000)."""
    return "q%04d" % n


def volume_of_chapter(ch):
    return (ch - 1) // CHAPTERS_PER_VOLUME + 1


def chapter_of_quest(n):
    return (n - 1) // QUESTS_PER_CHAPTER + 1


def volume_of_quest(n):
    return volume_of_chapter(chapter_of_quest(n))


def first_quest(ch):
    return (ch - 1) * QUESTS_PER_CHAPTER + 1


def legacy_to_new(n):
    """Global quest number of legacy quest ``n`` (1..100). Its lead quests
    (see LEGACY_LEAD_QUESTS) keep their original slot; its tail quest(s) --
    the breakthrough, or for the finale, the last two -- always land on the
    *last* slot(s) of the chapter, however many quests it now holds, in the
    same order, so new quests can be inserted before them freely."""
    o = (n - 1) // 10 + 1
    pos = (n - 1) % 10
    lead = LEGACY_LEAD_QUESTS[o]
    slot = pos if pos < lead else QUESTS_PER_CHAPTER - (LEGACY_QUESTS_PER_CHAPTER - pos)
    return first_quest(LEGACY_CHAPTERS[o]) + slot


def resolve_id(qref):
    """Quest number for an authored reference: ``q085`` (legacy, three digits)
    or ``q0405`` (new numbering, four digits). Returns None if malformed."""
    if not isinstance(qref, str) or not qref.startswith("q") or not qref[1:].isdigit():
        return None
    n = int(qref[1:])
    if len(qref) == 4:
        return legacy_to_new(n) if 1 <= n <= 100 else None
    if len(qref) == 5:
        return n if 1 <= n <= TOTAL_QUESTS else None
    return None

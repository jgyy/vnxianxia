"""Numbering of the 1000-quest saga: 10 volumes x 10 chapters x 10 quests.

The ten hand-written chapters of the original 100-quest story ("legacy"
chapters O1..O10) keep their text and voice files and are placed inside the
new structure. Everything here is pure arithmetic so that build_story, the
chapter generator and the runtime agree on ids.
"""

VOLUMES = 10
CHAPTERS_PER_VOLUME = 10
QUESTS_PER_CHAPTER = 10
TOTAL_CHAPTERS = VOLUMES * CHAPTERS_PER_VOLUME
TOTAL_QUESTS = TOTAL_CHAPTERS * QUESTS_PER_CHAPTER

# global chapter number of each legacy chapter O1..O10
LEGACY_CHAPTERS = {1: 1, 2: 2, 3: 3, 4: 11, 5: 12, 6: 21, 7: 22, 8: 31, 9: 41, 10: 100}
CHAPTER_OF_LEGACY = {v: k for k, v in LEGACY_CHAPTERS.items()}


def qid(n):
    """Quest id of global quest number ``n`` (1..1000)."""
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
    """Global quest number of legacy quest ``n`` (1..100)."""
    o = (n - 1) // 10 + 1
    return first_quest(LEGACY_CHAPTERS[o]) + (n - 1) % 10


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

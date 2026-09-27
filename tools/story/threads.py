"""Recurring plot threads that run across the ten volumes.

The 2000-quest saga already tells one continuous story (see docs/STORY.md),
but each of its 100 chapters is played on its own, well apart from its
neighbours. THREADS names the handful of throughlines a reader of a
serialised novel would recognise and pay off — the traitor, the pendant,
Elder Mo, the Patriarch's Ladder, the people around the heir — and tags the
quest at which each beat lands, so the game can show a running "story so
far" and the roaming monologue can look back on what it's already lived
through.

Every beat is a *recap*, written after the fact: it never spoils a beat that
hasn't happened yet, because build_story only ever exposes beats up to the
player's current quest (see tools/build_story.py compile of "threads" and
Story.gd's ``threads_so_far``).
"""

from . import numbering as NB


def _q(n):
    return NB.qid(n)


THREADS = [
    {
        "id": "traitor",
        "title": "The Traitor in the Law Hall",
        "beats": [
            (20, "The formation array answers Elder Gu's touch a little too well for comfort."),
            (240, "Under tournament banners, on the night of the final, the traitor's mask finally slips."),
            (400, "The Sect Master reads the Crimson Road report twice, then chooses two disciples to follow him down."),
            (820, "At the Heart Mirror, Gu Hanshan confesses everything, as the sky over the sect burns red."),
            (1860, "A prisoner for years, Gu Hanshan asks the Sect Master for three last things."),
            (2000, "The traitor spends the last thing he has opening the black gate."),
        ],
    },
    {
        "id": "pendant",
        "title": "The Lotus Key",
        "beats": [
            (20, "A dead mother's jade pendant, and nothing else — but the formation array notices it."),
            (220, "In the ruins of a forgotten sect, the hermit tells the truth: the pendant is the Lotus Key."),
            (920, "A seed planted before the descent into the Abyss finally flowers, green and gold."),
            (2000, "The last of the Verdant Lotus bloodline climbs the Ascension Stair, key and all."),
        ],
    },
    {
        "id": "mo",
        "title": "Elder Mo's Sacrifice",
        "beats": [
            (560, "Elder Mo starts teaching sword qi before the isles even open, and admits, gruffly, that he's proud."),
            (780, "Nine thousand nine hundred runes checked by hand, and one ring still to go."),
            (820, "Elder Mo burns his own life to turn the lit formation back."),
            (1000, "A tea set, a peach orchard, forty years of notes, and a locked box addressed to the heir."),
        ],
    },
    {
        "id": "rungs",
        "title": "The Patriarch's Ladder",
        "beats": [
            (680, "A pale man in a warehouse nobody owns calls himself the First Rung of the Patriarch's Ladder."),
            (980, "The First Rung falls at the obelisk ring, inside a circle of his own ash."),
            (1060, "A monk in rotting robes prays rust into every hinge, chain and spear in Qingshi."),
            (1140, "Madam Ninefold wears nine faces in one small town, and one of them is close."),
            (1300, "Brother Hollow has worn ten thousand bodies. He wants one more, and cannot have it."),
            (1380, "The Butcher of Wen weighs cultivators by the jin. He has never weighed one like this."),
            (1540, "Lady Silk attends the conclave's last feast as guest of honour, thread in hand."),
            (1960, "The Seventh Rung is also blood: a cousin from a village by a creek, wearing red eyes."),
        ],
    },
    {
        "id": "han_xue",
        "title": "Han Xue",
        "beats": [
            (180, "Senior Sister Han Xue leads into the Moonlit Grotto, food and grudges in tow."),
            (420, "Han Xue is taken at the obelisks — the first thing broken to get her back."),
            (1740, "A year from her own nascent soul, Han Xue finally asks the heir to stand guard the way she once did."),
            (2000, "Han Xue holds the bridge at the end of the world."),
        ],
    },
    {
        "id": "zhao_kang",
        "title": "Zhao Kang",
        "beats": [
            (240, "A forced pairing in the tournament turns rivalry into something like respect."),
            (720, "The Zhao clan wants its heir home. Zhao Kang has never been good at choosing anything but arguments."),
            (1540, "Zhao Kang stands sworn brother, not just rival, at the conclave's last feast."),
            (1760, "One last wager, for old times' sake, before the sky takes the heir somewhere he can't follow."),
        ],
    },
    {
        "id": "heart_demon",
        "title": "The Heart Demon",
        "beats": [
            (820, "A shadow of the self, faced at the Heart Mirror and not yet understood."),
            (960, "The Heart Mirror hums a name outside the fold, still black, still still."),
            (1999, "On the ninth bolt, the Patriarch rides the heart demon one last time."),
        ],
    },
    {
        "id": "alliance",
        "title": "The Great Vehicle",
        "beats": [
            (1420, "No one climbs alone: the Sect Master calls every orthodox sect to one conclave."),
            (1560, "Forty sects swear one oath on the formation plaza, then go home to wait."),
            (1600, "The alliance's first joint action seals the rifts leaking from the fold at the Abyss rim."),
            (1980, "Forty sects' armies gather at the teleport array for the march that finishes it."),
        ],
    },
]


def beats():
    """Every (thread id, quest number, text), sorted by quest number, for validation."""
    for t in THREADS:
        for n, text in t["beats"]:
            yield t["id"], n, text


def compiled():
    """THREADS as build_story emits them: quest ids instead of bare numbers."""
    return [
        {"id": t["id"], "title": t["title"],
         "beats": [{"quest": _q(n), "number": n, "text": text} for n, text in t["beats"]]}
        for t in THREADS
    ]

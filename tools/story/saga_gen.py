"""Deterministic chapter generator for the 90 new chapters of the saga.

A new chapter is authored as a compact outline (see vol01.py .. vol10.py):

    C(title, map, summary, cast=[...], foes=[...], items=[...], props=[...],
      boss=(enemy, display name, marker), beats=[B(...), ... ten beats])

and every beat becomes one quest:

    B(kind, title, summary, *script, **options)

``kind`` picks a quest pattern (a sequence of objective steps such as
talk-giver / reach / defeat / collect / talk-back). ``script`` holds the
hand-written heart of the quest: ``(speaker, text)`` lines, split into
segments by tags. A tag is a string:

    "@T"  "@R"  "@F"  "@X"  "@G"  "@M"  "@I"   (talk, reach, fight, boss fight,
                                                 gather, meditate, interact)
    "@R:WatchTower"          ... and pins that step to a marker
    "@T:qingshi_town/Inn"    ... on another map (later steps inherit the map)
    "|"                      a plain segment break (type inferred)
    ">Objective text"        overrides the objective text of the current step

Segments are matched in order to the pattern's steps; a segment that fits no
remaining step appends a new step. Steps without a segment get template text
from fillers.py (openers, replies, battle cries, arrival narration, ...), so
every quest has a hand-written core wrapped in varied connective tissue.

Everything is a pure function of the outline: there is no randomness, only
stable hashes, so a rebuild produces byte-identical story.json.
"""

import hashlib
import re

from . import ensemble as EN
from . import fillers as FL
from . import numbering as NB
from . import places as PL
from . import morality as MO
from . import tribulations as TR
from .choices import NEW as CHOICES
from .dsl import N, P, _lines, chapter, collect, defeat, interact, meditate, quest, reach, talk
from .dsl import speakers as dsl_speakers
from .npcs import DEMON as NP_DEMON
from .npcs import MINOR
from .npcs import NPCS

try:
    from world_spec import REALMS
except ImportError:  # imported as tools.story
    from tools.world_spec import REALMS

# ---------------------------------------------------------------- outline helpers


def B(kind, title, summary, *script, **kw):
    segs = []
    cur = None

    def new(tag=None, marker=None, map_id=None):
        s = {"tag": tag, "marker": marker, "map": map_id, "lines": [], "text": None}
        segs.append(s)
        return s

    for it in script:
        if isinstance(it, str) and it == "|":
            cur = new()
        elif isinstance(it, str) and it.startswith("@"):
            tag, _, where = it[1:].partition(":")
            mp = None
            if "/" in where:
                mp, where = where.split("/", 1)
            cur = new(tag, where or None, mp)
        elif isinstance(it, str) and it.startswith(">"):
            if cur is None:
                cur = new()
            cur["text"] = it[1:]
        elif isinstance(it, tuple) and len(it) in (2, 3):
            if cur is None:
                cur = new()
            cur["lines"].append(it)
        else:
            raise ValueError("bad script item in beat %r: %r" % (title, it))
    return {"kind": kind, "title": title, "summary": summary, "segs": segs, "kw": kw}


def C(title, map, summary, cast, foes, beats, items=("spirit_herb",), props=("seal",), boss=None, things=None,
      nouns=None, foe_names=None):
    return {"title": title, "map": map, "summary": summary, "cast": list(cast), "foes": list(foes),
            "items": list(items), "props": list(props), "boss": boss, "beats": list(beats),
            "things": dict(things or {}), "nouns": dict(nouns or {}), "foe_names": dict(foe_names or {})}


# ---------------------------------------------------------------- vocabulary

FOE_NAMES = {
    "spirit_wolf": "spirit wolves", "corrupted_wolf": "corrupted wolves", "wolf_king": "wolf king",
    "bandit": "bandits", "bandit_chief": "bandit chief", "training_puppet": "training puppets",
    "sparring_disciple": "sparring disciples", "tournament_champion": "champion",
    "demon_cultivator": "Blood Moon cultivators", "blood_guard": "Blood Guards", "demon_elder": "demon elder",
    "blood_patriarch": "Patriarch", "stone_golem": "stone golems", "ancient_guardian": "guardian",
    "jiao_serpent": "serpent", "heart_demon": "heart demon", "rogue_cultivator": "rogue cultivators",
    "iron_scale_disciple": "Iron Scale disciples", "void_wraith": "void wraiths", "thunder_wolf": "thunder wolves",
    "celestial_sentinel": "celestial sentinels", "rung_deacon": "Rung", "void_colossus": "colossus",
}
ITEM_NOUNS = {
    "spirit_herb": "spirit herbs", "spirit_stone": "spirit stones", "jade_slip": "jade slips",
    "wolf_fang": "wolf fangs", "blood_lotus": "blood lotus", "demon_core": "demon cores", "star_iron": "star iron",
    "thunder_crystal": "thunder crystals", "cloud_silk": "cloud silk", "phoenix_feather": "phoenix feathers",
    "medicine": "medicine bundles", "letter": "sealed letters", "lantern_oil": "lantern oil",
    "rune_fragment": "rune fragments", "void_shard": "void shards", "spirit_pill": "spirit pills",
    "incense": "incense bundles", "tribulation_jade": "tribulation jade",
}
THINGS = {
    "stone_stele": "the old stele", "treasure_chest": "the chest", "blood_altar": "the blood altar",
    "demon_obelisk": "the obelisk", "prison_cage": "the cage", "jade_slip": "the jade slip",
    "bronze_bell": "the bronze bell", "spirit_stone": "the spirit stone", "teleport_array": "the array",
    "seal": "the seal",
    "notice_board": "the notice board", "ancestral_tablet": "the ancestral tablets", "pill_furnace": "the pill furnace",
    "sword_in_stone": "the sword in the stone", "tortoise_stele": "the tortoise stele",
    "guardian_lion": "the guardian lion", "bronze_ding": "the bronze ding", "bronze_mirror": "the bronze mirror",
    "spirit_lamp": "the spirit lamp", "scroll_rack": "the scroll rack", "war_drum": "the war drum",
    "sealed_coffin": "the sealed coffin", "offering_table": "the offering table", "rune_pillar": "the rune pillar",
    "armillary_sphere": "the armillary sphere", "medicine_cabinet": "the medicine cabinet",
    "wine_jars": "the wine jars", "loom": "the loom", "map_table": "the map table", "crane_statue": "the crane statue",
    "spirit_fountain": "the spirit fountain", "puppet_frame": "the puppet frame",
    "herb_drying_rack": "the drying racks", "chain_anchor": "the chain anchor", "soul_lantern": "the soul lantern",
    "abacus_desk": "the abacus desk", "fishing_boat": "the fishing boat", "wishing_tree": "the wishing tree",
    "jade_screen": "the jade screen", "stone_tablet_array": "the stone tablets",
}
PROP_VERBS = {
    "stone_stele": ["Read {thing}", "Study {thing}", "Decipher {thing}"],
    "treasure_chest": ["Open {thing}", "Search {thing}", "Pry open {thing}"],
    "blood_altar": ["Cleanse {thing}", "Break {thing}"],
    "demon_obelisk": ["Shatter {thing}", "Break {thing}"],
    "prison_cage": ["Open {thing}", "Break open {thing}"],
    "jade_slip": ["Read {thing}", "Study {thing}"],
    "bronze_bell": ["Ring {thing}", "Sound {thing}"],
    "spirit_stone": ["Draw qi from {thing}", "Attune {thing}"],
    "teleport_array": ["Repair {thing}", "Realign {thing}"],
    "seal": ["Activate {thing}", "Inspect {thing}", "Trace {thing}"],
    "notice_board": ["Read {thing}", "Search {thing}", "Check {thing}"],
    "ancestral_tablet": ["Pay respects at {thing}", "Read {thing}", "Kneel before {thing}"],
    "pill_furnace": ["Tend {thing}", "Stoke {thing}", "Open {thing}"],
    "sword_in_stone": ["Grip {thing}", "Test {thing}", "Listen to {thing}"],
    "tortoise_stele": ["Read {thing}", "Decipher {thing}", "Study {thing}"],
    "guardian_lion": ["Examine {thing}", "Touch {thing}", "Wake {thing}"],
    "bronze_ding": ["Light incense in {thing}", "Examine {thing}", "Read the rim of {thing}"],
    "bronze_mirror": ["Look into {thing}", "Polish {thing}", "Study {thing}"],
    "spirit_lamp": ["Light {thing}", "Trim {thing}", "Refill {thing}"],
    "scroll_rack": ["Search {thing}", "Browse {thing}", "Sort {thing}"],
    "war_drum": ["Beat {thing}", "Sound {thing}"],
    "sealed_coffin": ["Inspect {thing}", "Check the seals of {thing}", "Open {thing}"],
    "offering_table": ["Leave an offering at {thing}", "Examine {thing}", "Light incense at {thing}"],
    "rune_pillar": ["Read {thing}", "Charge {thing}", "Trace {thing}"],
    "armillary_sphere": ["Turn {thing}", "Align {thing}", "Read {thing}"],
    "medicine_cabinet": ["Search {thing}", "Check {thing}", "Open {thing}"],
    "wine_jars": ["Check {thing}", "Search {thing}", "Taste {thing}"],
    "loom": ["Examine {thing}", "Check the thread on {thing}"],
    "map_table": ["Study {thing}", "Read {thing}", "Mark {thing}"],
    "crane_statue": ["Examine {thing}", "Touch {thing}"],
    "spirit_fountain": ["Drink from {thing}", "Examine {thing}", "Cleanse {thing}"],
    "puppet_frame": ["Test {thing}", "Repair {thing}", "Examine {thing}"],
    "herb_drying_rack": ["Search {thing}", "Turn {thing}", "Check {thing}"],
    "chain_anchor": ["Check {thing}", "Test {thing}", "Examine {thing}"],
    "soul_lantern": ["Examine {thing}", "Free the soul in {thing}", "Snuff {thing}"],
    "abacus_desk": ["Check the accounts at {thing}", "Search {thing}", "Read the ledgers at {thing}"],
    "fishing_boat": ["Search {thing}", "Check {thing}", "Examine {thing}"],
    "wishing_tree": ["Read the ribbons on {thing}", "Tie a wish to {thing}", "Search {thing}"],
    "jade_screen": ["Study {thing}", "Examine {thing}", "Look behind {thing}"],
    "stone_tablet_array": ["Read {thing}", "Study {thing}", "Compare {thing}"],
}

TXT = {
    "giver": ["Speak with {name}", "Answer {name}'s summons", "Find {name}", "See what {name} wants",
              "Report to {name}", "Go and see {name}", "Hear {name} out"],
    "ally": ["Talk with {name} at {place}", "Find {name} at {place}", "Join {name} at {place}",
             "Hear what {name} has to say", "Speak with {name}", "Meet {name} at {place}"],
    "after": ["Regroup with {name}", "Check on {name}", "Catch your breath with {name}", "Find {name} after the fight",
              "Look for {name} at {place}"],
    "found": ["Compare notes with {name}", "Tell {name} what you found", "Show {name} what you found",
              "Talk it over with {name}", "Share your findings with {name}"],
    "back": ["Return to {name}", "Report back to {name}", "Go back to {name}", "See {name} again",
             "Bring word to {name}"],
    "reach": ["Head to {place}", "Make your way to {place}", "Search {place}", "Scout {place}",
              "Investigate {place}", "Go to {place}", "Hurry to {place}"],
    "defeat": ["Drive the {foes} from {place}", "Defeat the {foes} at {place}", "Clear {place} of {foes}",
               "Break the {foes} at {place}", "Fight off the {foes}", "Stop the {foes} at {place}"],
    "defeat2": ["Face the next wave of {foes}", "Hold {place} against more {foes}", "Stop the {foes} regrouping",
                "Cut down the {foes} that follow", "Finish the {foes} at {place}"],
    "boss": ["Defeat {boss}", "Face {boss} at {place}", "Bring down {boss}"],
    "collect": ["Gather {noun} at {place}", "Collect {noun} around {place}", "Recover {noun} from {place}",
                "Pick up {noun} near {place}", "Find the {noun} at {place}"],
    "meditate": ["Meditate at {place}", "Cultivate at {place}", "Steady your qi at {place}",
                 "Sit in stillness at {place}", "Circulate your qi at {place}"],
    "break": ["Break through at {place}"],
    "stage": ["Consolidate your cultivation at {place}", "Refine your cultivation at {place}",
              "Temper your realm at {place}"],
}

PATTERNS = {
    "orders": [["T:giver", "R:p1", "T:ally@p1"], ["T:giver", "R:p1", "I:p1", "T:ally@p1"]],
    "gather": [["T:giver", "G:p1", "T:back"], ["T:giver", "G:p1", "F:p1", "T:back"], ["T:giver", "R:p1", "G:p1", "T:back"]],
    "hunt": [["R:p1", "F:p1", "G:p1", "T:ally@p1"], ["T:giver", "F:p1", "G:p1", "T:back"]],
    "battle": [["T:ally@p1", "F:p1", "F2:p2", "R:p3"], ["F:p1", "F2:p1", "T:ally@p2"]],
    "probe": [["R:p1", "I:p1", "T:ally@p1"], ["T:giver", "R:p1", "I:p1", "G:p2", "T:back"], ["R:p1", "I:p1", "G:p1", "T:ally@p2"]],
    "social": [["T:giver", "T:ally", "T:third"]],
    "train": [["T:giver", "F:p1", "T:back"], ["T:giver", "M:p1", "F:p2", "T:back"]],
    "cultivate": [["T:giver", "M:p1", "T:back"], ["R:p1", "M:p1", "T:ally@p1"]],
    "defend": [["T:giver", "I:p1", "F:p1", "F2:p2", "T:ally@p2"], ["T:giver", "F:p1", "F2:p1", "T:back"]],
    "delve": [["R:p1", "G:p1", "I:p1", "F:p2", "R:p3"], ["R:p1", "F:p1", "I:p2", "T:ally@p2"]],
    "rescue": [["R:p1", "F:p1", "I:p1", "T:ally@p1"]],
    "duel": [["T:giver", "F:p1", "T:back"]],
    "boss": [["R:p1", "X:p1", "I:p1", "T:ally@p2"], ["R:p1", "X:p1", "T:ally@p2"]],
    "break": [["T:giver", "G:p1", "M:p2", "T:third"]],
    "stage": [["T:giver", "M:p1", "T:back"], ["R:p1", "M:p1", "T:ally@p1"]],
    "journey": [["T:giver", "R:p1", "T:ally@p1"]],
    "festival": [["T:giver", "G:p1", "I:p2", "T:ally"]],
    "chase": [["R:p1", "F:p2", "R:p3", "T:ally@p3"]],
    "interlude": [["T:giver", "T:ally"], ["T:giver", "R:p1", "T:ally@p1"]],
    "council": [["R:p1", "T:ally@p1", "T:third@p1"]],
}

# blood_abyss markers that fold into the void after the failed blood moon (ch42) until the final march
FORTRESS = {"DemonGate", "FortressCourt", "AltarOfBlood", "PatriarchThrone", "PrisonCages"}
RESERVED = {"PlayerSpawn", "TeleportArray", "TribulationPeak", "AscensionStair"}
# the doors of the building interiors: walking onto one carries the player inside
DOORS = {"ElderQuarters", "AlchemyPavilion", "WeaponsHall", "DiscipleDormitory", "TeaHouse", "Blacksmith", "HerbShop",
         "Inn"}

NEAR_MAPS = {"sect", "bamboo_forest", "qingshi_town"}

KIND_OF = {"R": "reach", "F": "fight", "F2": "fight", "X": "fight", "G": "gather", "M": "med", "I": "prop"}

# spreading the saga over the map: a marker the scene's own words point at (or a character's
# haunt) counts this many uses fewer when the least-used place is chosen
PREFER_BONUS = 10
# an NPC is met at home at most this often; after that, only at their haunts
HOME_CAP = 30
# percentages of the deterministic hash
REACH_TO_INTERACT = 55   # an arrival at a place with a fitting prop becomes an investigation of it
LOCAL_PROP = 60          # an interact step examines the place's own prop rather than the chapter's
LOCAL_ITEM = 45          # a gather step collects what lies around the place rather than the chapter's item
TWO_COMPANIONS = 35      # a conversation has two companions, not one
COND_LINE = 30           # a companion reacts to who the player has become
ASIDE_RATE = 45          # a companion adds an aside to the reaction after a moral choice

XP_BASE = [0, 110, 280, 480, 760, 1060, 1450, 1900, 2450, 3100, 3800]

MAX_TEXT = 64


def h(*key):
    return int(hashlib.sha1(repr(key).encode("utf-8")).hexdigest()[:12], 16)


class Rotor:
    """Deterministic cycling through a pool, in a stable shuffled order."""

    def __init__(self, pool, salt):
        self.pool = sorted(pool, key=lambda s: h(salt, s))
        self.i = h(salt) % max(1, len(self.pool))

    def next(self, accept=None):
        for _ in range(len(self.pool)):
            v = self.pool[self.i % len(self.pool)]
            self.i += 1
            if accept is None or accept(v):
                return v
        return self.pool[0]


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def _low(s):
    if not s:
        return s
    # keep proper nouns: lower-case only a leading common verb
    return s[:1].lower() + s[1:]


def fmt(t, **slots):
    out = t
    for k, v in slots.items():
        out = out.replace("{%s}" % k, str(v)).replace("{%s}" % _cap(k), _cap(str(v)))
    return out


# ---------------------------------------------------------------- the generator


class Gen:
    def __init__(self):
        self.rot = {}
        self.used_titles = set()
        # how often each (map, marker) has hosted an objective so far, for spreading the saga out
        self.use = {}

    def rotor(self, name, pool):
        if name not in self.rot:
            self.rot[name] = Rotor(pool, name)
        return self.rot[name]

    def seed(self, chapters):
        """Count the markers of the hand-written chapters, which the generator cannot move."""
        for ch in chapters:
            cur = ch["map"]
            for q in ch["quests"]:
                cur = q["map"]
                for o in q["objectives"]:
                    cur = o.get("map") or cur
                    mk = o.get("marker") or o.get("at")
                    if o["type"] == "talk" and mk is None and NPCS[o["npc"]]["home"]:
                        mk = NPCS[o["npc"]]["home"]["marker"]
                    if mk and o["type"] != "cinematic":
                        self.count(cur, mk)

    def count(self, m, mk):
        self.use[(m, mk)] = self.use.get((m, mk), 0) + 1

    def best(self, m, cands, q, salt, prefer=(), bonus=PREFER_BONUS):
        """The least-used of ``cands`` on map ``m`` (a preferred one counts ``bonus`` uses fewer)."""
        prefer = set(prefer)
        return min(cands, key=lambda c: (self.use.get((m, c), 0) - (bonus if c in prefer else 0), h(q, salt, c)))

    # --- presence --------------------------------------------------------
    @staticmethod
    def window(nid):
        n = NPCS[nid]
        a = NB.resolve_id(n["appear_from"]) if n["appear_from"] else None
        hid = NB.resolve_id(n["hidden_after"]) if n["hidden_after"] else None
        return a, hid

    @staticmethod
    def active(nid, q):
        n = NPCS[nid]
        a = NB.resolve_id(n["appear_from"]) if n["appear_from"] else None
        gone = NB.resolve_id(n["gone_after"]) if n.get("gone_after") else None
        return not ((a and q < a) or (gone and q > gone))

    def at_home(self, nid, map_id, q):
        n = NPCS[nid]
        home = n["home"]
        if not home or home["map"] != map_id:
            return False
        a, hid = self.window(nid)
        return not ((a and q < a) or (hid and q > hid))

    def homes(self, map_id, q):
        return {NPCS[nid]["home"]["marker"]: nid for nid in NPCS if self.at_home(nid, map_id, q)}

    def allowed(self, map_id, marker, q, kind, explicit=False):
        if marker in RESERVED and not explicit:
            return False
        if marker in DOORS and not explicit:
            return False
        if map_id == "blood_abyss":
            if marker in FORTRESS and q > NB.legacy_to_new(90) and not explicit:
                return False
            if marker == "HeartMirror" and q < NB.legacy_to_new(84):
                return False
        if kind in ("fight", "gather") and marker in self.homes(map_id, q):
            return False
        return True

    # --- chapter ---------------------------------------------------------
    def chapter(self, spec, number, realm=None, stage=None):
        first = NB.first_quest(number)
        vol = NB.volume_of_chapter(number)
        if len(spec["beats"]) != NB.QUESTS_PER_CHAPTER:
            raise ValueError("chapter %d %r has %d beats" % (number, spec["title"], len(spec["beats"])))
        quests = []
        for i, beat in enumerate(spec["beats"]):
            q = first + i
            last = i == len(spec["beats"]) - 1
            qd = self.quest(spec, beat, q, vol, i, realm=realm if last else None, stage=stage if last else None)
            authored = CHOICES.get((number, i))
            if authored:
                attach_choice(qd, authored, q, spec, beat)
            else:
                fam = choice_family(qd, beat, q)
                if fam:
                    name, extra = fam
                    variants = MO.TEMPLATES[name]
                    # cycle through a family's variants across the saga, so the same dilemma rarely repeats nearby
                    tpl = variants[self.rotor("choice/" + name, list(range(len(variants)))).next()]
                    attach_choice(qd, tpl, q, spec, beat, **extra)
            # every quest offers a choice: whatever the beat's own kind couldn't
            # place, a plain reading of its objectives always can
            ensure_choice(qd, q, self.rotor)
            quests.append(qd)
        ch = chapter(number, spec["title"], spec["summary"], None, spec["map"], quests)
        ch["legacy"] = None
        return ch

    # --- quest -----------------------------------------------------------
    def quest(self, spec, beat, q, vol, qi, realm=None, stage=None):
        kw = beat["kw"]
        kind = beat["kind"]
        if kind not in PATTERNS:
            raise ValueError("q%04d: unknown beat kind %r" % (q, kind))
        segs = beat["segs"]
        if len(segs) >= 2 or kind == "script":
            # an authored script: its segments are the sequence of objectives
            # (an untagged segment is a talk if a character speaks in it, else an arrival)
            steps = []
            for i, s in enumerate(segs):
                if not s["tag"]:
                    s = dict(s, tag="T" if self._seg_type(s) == "T" else "R")
                if s["tag"] == "T":
                    st = {"t": "T", "role": "giver" if i == 0 else "ally", "place": None}
                else:
                    st = {"t": s["tag"], "role": None, "place": "p1"}
                st["seg"] = s
                steps.append(st)
            if len(steps) > 6:
                raise ValueError("q%04d %r: %d objectives (max 6)" % (q, beat["title"], len(steps)))
        else:
            variants = PATTERNS[kind]
            v = kw.get("v")
            pattern = variants[(v if v is not None else h(q, kind)) % len(variants)]
            steps = [self._parse_step(s) for s in pattern]
            self._assign(steps, segs, q)
            # a pattern's optional collect with nothing authored for it would be noise: drop it
            # (an optional interact is kept while its place may still turn out to hold a prop)
            keep = []
            for st in steps:
                if "seg" not in st and st["t"] == "G" and kind not in ("gather", "hunt", "festival", "break") \
                        and not (kw.get("item") or kw.get("noun")):
                    continue
                keep.append(st)
            if len(keep) >= 2:
                steps = keep
        base_map = kw.get("map", spec["map"])
        scene = " ".join([beat["title"], beat["summary"]] + [s["text"] or "" for s in segs]
                         + [ln[1] for s in segs for ln in s["lines"]]).lower()
        ctx = {"q": q, "vol": vol, "spec": spec, "beat": beat, "kw": kw, "roles": {}, "npcs": {},
               "fights": set(), "base_map": base_map, "reloc": {}, "scene": scene, "words": _words(scene)}
        # resolve maps and places in order
        cur_map = base_map
        for idx, st in enumerate(steps):
            seg = st.get("seg")
            if seg and seg["map"]:
                cur_map = seg["map"]
            st["map"] = cur_map
            if st["t"] == "T":
                st["npc"] = self._talk_npc(st, ctx, idx, steps)
            else:
                st["marker"] = self._place(st, ctx, steps)
                if st["t"] in ("F", "F2", "X"):
                    ctx["fights"].add((st["map"], st["marker"]))
        steps = self._props(steps, ctx)
        for idx, st in enumerate(steps):
            if st["t"] == "T":
                st["at"] = self._talk_at(st, ctx, steps, idx)
        objs = []
        for idx, st in enumerate(steps):
            objs.append(self._objective(st, ctx, steps, idx))
        # the opening talk may greet the player differently by alignment and realm
        if objs[0]["type"] == "talk" and kind in MO.GREET_KINDS:
            greet = MO.greeting_lines(objs[0]["npc"], q)
            if greet:
                objs[0]["dialogue"] = _lines(greet) + objs[0]["dialogue"]
        # everyone who is there takes part: companions join the conversations
        self._ensemble(objs, steps, ctx)
        for o in objs:
            mk = o.get("marker") or o.get("at") or (NPCS[o["npc"]]["home"]["marker"] if o["type"] == "talk" else None)
            self.count(o["map"], mk)
        if realm:
            # a major breakthrough calls down its heavenly tribulation, right after the breakthrough meditation
            med = [i for i, o in enumerate(objs) if o["type"] == "meditate"]
            at = med[-1] + 1 if med else len(objs) - 1
            base = objs[at - 1] if med else objs[-1]
            ri = REALMS.index(realm)
            tm = base.get("marker") or kw.get("at")
            talks_at = {(o["map"], o.get("at") or NPCS[o["npc"]]["home"]["marker"]) for o in objs if o["type"] == "talk"}
            if TR.params(ri)[1] and (base["map"], tm) in talks_at:
                # tribulation beasts must not land where someone stands to talk: move the storm aside
                tm = sorted((mk for mk in PL.POOLS[base["map"]]["fight"]
                             if (base["map"], mk) not in talks_at and self.allowed(base["map"], mk, q, "fight")),
                            key=lambda mk: h(q, mk, "storm"))[0]
            trib = TR.make(ri, realm, tm, base["map"])
            if len(objs) >= 6:
                # keep the quest at six objectives: the breakthrough's gathering step makes way,
                # but never the only group conversation of the quest
                drop = next((i for i, o in enumerate(objs) if o["type"] in ("collect", "interact", "reach")
                             and not is_group(o)), None)
                if drop is None:
                    raise ValueError("q%04d: no step can make way for the tribulation" % q)
                objs.pop(drop)
                if drop < at:
                    at -= 1
            objs.insert(at, trib)
        xp = kw.get("xp") or (XP_BASE[vol] + 12 * qi + (XP_BASE[vol] // 2 if kind == "boss" else 0)
                              + (XP_BASE[vol] if realm else 0))
        items = kw.get("reward")
        if items is None:
            items = {}
            if kind == "boss":
                items = {"medicine": 2}
            elif realm:
                items = {"spirit_pill": 1}
            elif h(q, "reward") % 3 == 0:
                items = {"spirit_stone": 1 + h(q, "n") % 3}
        qd = quest(beat["title"], beat["summary"], objs[0]["map"], objs, xp, items, realm)
        qd["rewards"]["stage"] = stage
        qd["legacy"] = None
        return qd

    @staticmethod
    def _parse_step(s):
        t, _, rest = s.partition(":")
        role, _, place = rest.partition("@")
        if t in ("T",):
            return {"t": t, "role": role, "place": place or None}
        return {"t": t, "role": None, "place": role or None}

    @staticmethod
    def _seg_type(seg):
        if seg["tag"]:
            return seg["tag"]
        has_npc = any(ln[0] not in (P, N) and len(ln) == 2 for ln in seg["lines"])
        return "T" if has_npc else "N"

    def _assign(self, steps, segs, q):
        """Match authored segments to pattern steps in order."""
        pos = 0
        for seg in segs:
            want = self._seg_type(seg)
            ok = {"T": ("T",), "N": ("R", "I", "M"), "R": ("R",), "I": ("I",), "M": ("M",),
                  "F": ("F", "F2"), "F2": ("F2", "F"), "X": ("X",), "G": ("G",)}.get(want)
            if ok is None:
                raise ValueError("q%04d: unknown segment tag %r" % (q, want))
            found = None
            for j in range(pos, len(steps)):
                if steps[j]["t"] in ok and "seg" not in steps[j]:
                    found = j
                    break
            if found is None:
                t = ok[0]
                st = {"t": t, "role": "seg" if t == "T" else None, "place": None if t == "T" else "p1"}
                if t in ("F", "X", "G"):
                    st["place"] = "p1"
                # keep the story order: the new step goes right after the last matched one
                steps.insert(pos, st)
                found = pos
            steps[found]["seg"] = seg
            pos = found + 1
        if len(steps) > 6:
            raise ValueError("q%04d: %d objectives (max 6); simplify the beat" % (q, len(steps)))

    # --- NPCs ------------------------------------------------------------
    def _talk_npc(self, st, ctx, idx, steps):
        seg = st.get("seg")
        if seg:
            for ln in seg["lines"]:
                if ln[0] not in (P, N) and len(ln) == 2:
                    return ln[0]
        kw, cast = ctx["kw"], ctx["spec"]["cast"]
        role = st["role"]
        if role == "back":
            for s in steps[:idx]:
                if s["t"] == "T":
                    return s["npc"]
            role = "giver"
        if role in kw:
            return kw[role]
        if role in ctx["npcs"]:
            return ctx["npcs"][role]
        taken = {s.get("npc") for s in steps[:idx]}
        order = {"giver": 0, "ally": 1, "third": 2}.get(role, 1)
        start = (h(ctx["q"], "cast") + order) % len(cast)
        for k in range(len(cast)):
            cand = cast[(start + k) % len(cast)]
            if cand not in taken:
                ctx["npcs"][role] = cand
                return cand
        return cast[start]

    def _talk_at(self, st, ctx, steps, idx):
        """Where a talk NPC stands. An outline's own marker is kept when its lines are tied
        to it (and otherwise moved within its district, see _pin); the ally met "at" the
        place of the action stands there; someone met again stands where they stood before.
        Everyone else is staged either at home or, more often, at one of the places the
        character haunts (Elder Hua in the medicine valley, Wei Tong in the refectory),
        spreading the saga's conversations over the whole map. Never on another present
        NPC's home, nor where this quest fights."""
        q, m, nid = ctx["q"], st["map"], st["npc"]
        home = NPCS[nid]["home"]
        home_mk = home["marker"] if home and home["map"] == m and self.at_home(nid, m, q) else None
        if home_mk and (m, home_mk) in ctx["fights"]:
            home_mk = None  # this quest fights on the doorstep: meet somewhere else
        homes = self.homes(m, q)

        def free(c, explicit=False):
            if (m, c) in ctx["fights"]:
                return False
            if c in homes and homes[c] != nid:
                return False
            return explicit or self.allowed(m, c, q, "meet")

        explicit = self._pin(st, ctx, "meet", accept=lambda c: free(c, True))
        if explicit and (explicit == home_mk or free(explicit, True)):
            return None if explicit == home_mk else explicit
        want = None
        if st["place"]:
            want = ctx["roles"].get((m, st["place"]))
        if want and free(want):
            return want
        # someone met again in the same quest stands where they stood before
        for s in steps[:idx]:
            if s["t"] == "T" and s.get("npc") == nid and s["map"] == m and "at" in s:
                if (s["at"] is None and home_mk) or (s["at"] and free(s["at"])):
                    return s["at"]
        prev = steps[idx - 1] if idx > 0 else None
        if prev and prev["map"] == m and prev.get("marker") and prev["t"] != "T" and h(ctx["q"], nid, "spot") % 2 \
                and free(prev["marker"]):
            # met on the spot, right where the action was
            return prev["marker"]
        if home_mk and self.use.get((m, home_mk), 0) < HOME_CAP and h(q, nid, "home") % 3 == 0:
            return None
        haunts = [c for c in PL.HAUNTS.get(nid, {}).get(m, []) if free(c)]
        pool = [c for c in PL.POOLS[m]["meet"] if free(c)]
        scene = self._scene_markers(m, ctx)
        if haunts or pool:
            return self.best(m, sorted(set(haunts + pool)), q, nid, prefer=set(haunts) | scene)
        if home_mk:
            return None
        raise ValueError("q%04d: no place for %s to stand on %s" % (q, nid, m))

    # --- places ----------------------------------------------------------
    def _scene_markers(self, m, ctx):
        """Markers of map ``m`` the beat's own words point at (a beat about kilns likes the kiln yard)."""
        key = ("scene", m)
        if key not in ctx:
            ctx[key] = {mk for mk in PL.NAMES.get(m, {}) if PL.keywords(m, mk) & ctx["words"]}
        return ctx[key]

    def _bound(self, m, marker, seg, ctx):
        """True when an outline's marker is part of the story: the step's own lines, its text or
        the beat's title name the place, or it is a place the plot reserves. (The summary is not
        enough: "the Great Azure Formation" in a summary does not nail every step to the plaza.)"""
        if marker in FORTRESS or marker in RESERVED or marker == "HeartMirror":
            return True
        b = ctx["spec"]["boss"]
        if b and marker == b[2]:
            return True
        text = " ".join([ctx["beat"]["title"], seg["text"] or ""] + [ln[1] for ln in seg["lines"]])
        return bool(PL.keywords(m, marker) & _words(text.lower()))

    def _pin(self, st, ctx, kind, accept=None):
        """The marker an outline pinned this step to, or where it moves: a pin the step's lines are
        not tied to may move to a less-used marker of the same character (sharing a tag), so the
        saga spreads over the enlarged maps. Every step of a quest pinned to the same marker moves
        together. None if the step is not pinned."""
        seg = st.get("seg")
        if not (seg and seg["marker"]):
            return None
        m, q, mk = st["map"], ctx["q"], seg["marker"]
        if (m, mk) in ctx["reloc"]:
            return ctx["reloc"][(m, mk)]
        if mk not in PL.TAGS.get(m, {}) or self._bound(m, mk, seg, ctx):
            ctx["reloc"][(m, mk)] = mk
            return mk
        tags = PL.TAGS[m][mk]
        used = set(ctx["roles"].values())
        cands = [c for c in PL.POOLS[m][kind] if PL.TAGS[m][c] & tags and c not in used
                 and (accept is None or accept(c)) and self.allowed(m, c, q, kind)]
        new = self.best(m, sorted(set(cands) | {mk}), q, ("pin", mk))
        ctx["reloc"][(m, mk)] = new
        return new

    def _place(self, st, ctx, steps):
        q, m = ctx["q"], st["map"]
        kind = KIND_OF[st["t"]]
        pinned = self._pin(st, ctx, kind, accept=lambda c: self.allowed(m, c, q, kind))
        if pinned:
            ctx["roles"].setdefault((m, st["place"] or "p1"), pinned)
            return pinned
        if st["t"] == "X":
            b = ctx["spec"]["boss"]
            mk = ctx["kw"].get("arena") or (b[2] if b else None)
            if mk:
                ctx["roles"][(m, st["place"] or "p1")] = mk
                return mk
        role = st["place"] or "p1"
        key = (m, role)
        kwkey = {"p1": "at", "p2": "at2", "p3": "at3"}.get(role)
        if key in ctx["roles"]:
            mk = ctx["roles"][key]
            if self._fits(st, m, mk, q):
                return mk
        if kwkey and ctx["kw"].get(kwkey) and m == ctx["base_map"]:
            mk = ctx["kw"][kwkey]
            ctx["roles"][key] = mk
            return mk
        used = set(ctx["roles"].values())
        cands = [c for c in PL.POOLS[m][kind] if c not in used and self.allowed(m, c, q, kind)]
        if not cands:
            cands = [c for c in PL.POOLS[m][kind] if self.allowed(m, c, q, kind)]
        prefer = set(self._scene_markers(m, ctx))
        # a place shared with an interact step (R:p1 then I:p1) should hold something to examine
        if any(s["t"] == "I" and (s["place"] or "p1") == role for s in steps):
            prefer |= {c for c in cands if c in PL.PROPS_AT.get(m, {})}
        if st["t"] == "G":
            item = ctx["kw"].get("item")
            if item:
                prefer |= {c for c in cands if item in PL.ITEMS_AT.get(m, {}).get(c, ())}
        mk = self.best(m, cands, q, ("place", st["t"], role), prefer=prefer)
        ctx["roles"].setdefault(key, mk)
        return mk

    def _fits(self, st, m, mk, q):
        return self.allowed(m, mk, q, KIND_OF[st["t"]], explicit=True)

    # --- props -------------------------------------------------------------
    def _props(self, steps, ctx):
        """Choose what each interact step examines, turn some arrivals at a place with a
        fitting prop into an investigation of it, and drop optional interact steps whose
        place holds nothing to examine."""
        q, kw, spec = ctx["q"], ctx["kw"], ctx["spec"]
        out = []
        has_i = {(s["map"], s.get("marker")) for s in steps if s["t"] == "I"}
        for idx, st in enumerate(steps):
            seg = st.get("seg")
            here = PL.PROPS_AT.get(st["map"], {}).get(st.get("marker"), [])
            if st["t"] == "R" and here and not (seg and seg["text"]) and (st["map"], st["marker"]) not in has_i \
                    and h(q, idx, "r2i") % 100 < REACH_TO_INTERACT:
                st = dict(st, t="I", prop=here[h(q, idx, "which") % len(here)], converted=True)
                has_i.add((st["map"], st["marker"]))
            if st["t"] == "I" and "prop" not in st:
                prop = infer_prop(seg["text"] if seg else None, st["map"]) or kw.get("prop")
                if prop is None and here and (spec["props"] == ["seal"] or h(q, idx, "local") % 100 < LOCAL_PROP):
                    prop = here[h(q, idx, "which") % len(here)]
                if prop is None:
                    if not seg and not kw.get("thing") and len(steps) > 2:
                        continue  # nothing authored and nothing there to examine: drop the step
                    prop = spec["props"][h(q, idx, "prop") % len(spec["props"])]
                st["prop"] = prop
            out.append(st)
        return out if len(out) >= 2 else steps

    # --- objectives --------------------------------------------------------
    def _text(self, pool_key, st, ctx, **slots):
        seg = st.get("seg")
        if seg and seg["text"]:
            return seg["text"]
        pool = TXT[pool_key]
        rot = self.rotor("txt/" + pool_key, pool)
        for _ in range(len(pool)):
            t = fmt(rot.next(), **slots)
            if len(t) <= MAX_TEXT and "clear the clearing" not in t.lower():
                return t
        return fmt(pool[0], **slots)[:MAX_TEXT]

    def _lines(self, st):
        seg = st.get("seg")
        return list(seg["lines"]) if seg else []

    def _item(self, st, ctx, idx):
        """The collectible of a gather step: the outline's, else something that lies around the
        place (spirit pills in the kiln yard, feathers at the phoenix nest), else the chapter's."""
        if "item" in st:
            return st["item"]
        kw, spec, q = ctx["kw"], ctx["spec"], ctx["q"]
        item = kw.get("item")
        if item is None:
            local = [it for it in PL.ITEMS_AT.get(st["map"], {}).get(st.get("marker"), [])
                     if ctx["vol"] >= PL.ITEM_FROM_VOLUME.get(it, 1)]
            if local and h(q, idx, "localitem") % 100 < LOCAL_ITEM:
                item = local[h(q, idx, "li") % len(local)]
            else:
                item = spec["items"][h(q, idx, "item") % len(spec["items"])]
        st["item"] = item
        return item

    def _noun(self, st, ctx, idx):
        item = self._item(st, ctx, idx)
        kw, spec = ctx["kw"], ctx["spec"]
        if kw.get("noun") and (kw.get("item") in (None, item)):
            return kw["noun"]
        return spec["nouns"].get(item) or ITEM_NOUNS[item]

    def _objective(self, st, ctx, steps, idx):
        t, m, q, spec, kw = st["t"], st["map"], ctx["q"], ctx["spec"], ctx["kw"]
        lines = self._lines(st)
        if t == "T":
            nid = st["npc"]
            name = SHORT.get(nid, NPCS[nid]["name"])
            place = PL.name(m, st["at"]) if st["at"] else PL.name(m, NPCS[nid]["home"]["marker"])
            role = st["role"]
            prev = steps[idx - 1]["t"] if idx > 0 else None
            earlier = [s.get("npc") for s in steps[:idx] if s["t"] == "T"]
            if idx == 0:
                key = "giver"
            elif role == "back" or (earlier and nid == earlier[0] and prev != "T"):
                key = "back"
            elif prev in ("F", "F2", "X"):
                key = "after"
            elif prev in ("I", "G", "R") and ctx["beat"]["kind"] in ("probe", "delve", "hunt", "chase", "rescue"):
                key = "found"
            else:
                key = "ally"
            st["key"] = key
            text = self._text(key, st, ctx, name=name, place=place)
            if not lines:
                lines = self._filler_talk(nid, {"after": "ally", "found": "ally"}.get(key, key), st, ctx, steps, idx)
            elif sum(1 for ln in lines if len(ln) == 2) == 1:
                lines.append(self._pad(nid, [ln for ln in lines if len(ln) == 2], ctx, first=idx == 0))
            return talk(nid, text, *lines, at=st["at"], map=m)
        place = PL.name(m, st["marker"])
        if t == "R":
            text = self._text("reach", st, ctx, place=place)
            if not lines:
                lines = [(N, self._arrive(m, st["marker"], ctx))]
            return reach(st["marker"], text, *lines, map=m)
        if t in ("F", "F2", "X"):
            if t == "X":
                b = spec["boss"]
                enemy, bname = kw.get("boss_enemy", b[0]), kw.get("boss_name", b[1])
                text = self._text("boss", st, ctx, boss=bname, place=place)
                o = defeat(enemy, 1, st["marker"], text, *lines, map=m)
                o["name"] = bname
                return o
            enemy = self._foe(st, ctx)
            foes = kw.get("foes_name") or spec["foe_names"].get(enemy) or FOE_NAMES[enemy]
            count = kw.get("count") or (2 + (h(q, idx, "n") % 3) + min(3, (ctx["vol"] + 1) // 3))
            count = max(1, min(8, count if t == "F" else max(2, count - 1)))
            text = self._text("defeat" if t == "F" else "defeat2", st, ctx, foes=foes, place=place)
            if not lines and t == "F":
                ally = self._companion(ctx, steps)
                if ally and h(q, "cry") % 3:
                    lines = [(ally, fmt(self.rotor("cry", FL.CRY).next(), foes=foes, player="{player}"))]
                else:
                    lines = [(N, fmt(self.rotor("cryn", FL.CRY_N).next(), foes=foes))]
            return defeat(enemy, count, st["marker"], text, *lines, map=m)
        if t == "G":
            item = self._item(st, ctx, idx)
            noun = self._noun(st, ctx, idx)
            count = kw.get("gcount") or (3 + h(q, idx, "g") % 4)
            text = self._text("collect", st, ctx, noun=noun, place=place)
            return collect(item, count, st["marker"], text, map=m)
        if t == "M":
            key = "meditate"
            if kind_is(ctx, "stage"):
                key = "stage"
            if kind_is(ctx, "break"):
                key = "break"
            text = self._text(key, st, ctx, place=place)
            secs = kw.get("secs") or (8 if key in ("break", "stage") else 6)
            if not lines:
                lines = [(N, self.rotor("med%d" % ctx["vol"], FL.MEDITATE[ctx["vol"]]).next())]
            return meditate(st["marker"], secs, text, *lines, map=m)
        if t == "I":
            seg = st.get("seg")
            prop = st["prop"]
            generic = st.get("converted") or prop not in (spec["props"] + [kw.get("prop")])
            thing = (None if generic else (kw.get("thing") or spec["things"].get(prop))) or THINGS[prop]
            if seg and seg["text"] and not st.get("converted"):
                text = seg["text"]
            else:
                verbs = PROP_VERBS[prop]
                text = fmt(verbs[h(q, idx, "verb") % len(verbs)], thing=thing)
                if st.get("converted") and len(text) + len(place) + 4 <= MAX_TEXT:
                    text += " at " + place
                if len(text) > MAX_TEXT:
                    text = fmt("Examine {thing}", thing=thing)[:MAX_TEXT]
            if not lines:
                lines = [(N, fmt(self.rotor("int/" + prop, FL.INTERACT[prop]).next(), thing=thing))]
            elif st.get("converted"):
                lines = lines + [(N, fmt(self.rotor("int/" + prop, FL.INTERACT[prop]).next(), thing=thing))]
            return interact(prop, st["marker"], text, *lines, map=m)
        raise ValueError(t)

    def _foe(self, st, ctx):
        kw, spec, q = ctx["kw"], ctx["spec"], ctx["q"]
        if st["t"] == "F" and kw.get("foe"):
            return kw["foe"]
        if st["t"] == "F2" and kw.get("foe2"):
            return kw["foe2"]
        if st["t"] == "F2" and kw.get("foe"):
            return kw["foe"]
        foes = spec["foes"]
        return foes[(h(q, st["t"], "foe")) % len(foes)]

    def _companion(self, ctx, steps):
        for s in steps:
            if s["t"] == "T" and s.get("npc") and MO.category(s["npc"], ctx["q"]) not in ("demonic", "prisoner"):
                return s["npc"]
        return None

    def _arrive(self, m, marker, ctx):
        pool = PL.ARRIVE.get(m, {}).get(marker, [])
        if pool and h(ctx["q"], marker, "arr") % 4:
            return self.rotor("arr/%s/%s" % (m, marker), pool).next()
        return fmt(self.rotor("arrany", PL.ARRIVE_ANY).next(), place=PL.name(m, marker))

    def _filler_talk(self, nid, key, st, ctx, steps, idx):
        q = ctx["q"]
        quirks = FL.QUIRKS.get(nid, [])
        if key == "giver":
            nxt = next((s for s in steps[idx + 1:]), None)
            task = None
            if nxt is not None:
                task = self._peek_text(nxt, ctx, steps, steps.index(nxt))
            if task:
                a = fmt(self.rotor("open", FL.OPEN).next(lambda t: len(fmt(t, task=task).split()) <= 32),
                        task=_low(task))
            else:
                a = self.rotor("close", FL.CLOSE).next()
            out = [(nid, a), (P, self.rotor("reply", FL.REPLY).next())]
            if quirks and h(q, "quirk") % 2:
                out.insert(1, (nid, self.rotor("q/" + nid, quirks).next()))
            return out
        if key == "back":
            out = [(nid, self.rotor("close", FL.CLOSE).next())]
            if quirks and h(q, "qb") % 2:
                out.append((nid, self.rotor("q/" + nid, quirks).next()))
            else:
                out.append((P, self.rotor("reply2", FL.REPLY2).next()))
            return out
        place = PL.name(st["map"], st["at"] or NPCS[nid]["home"]["marker"])
        prev = steps[idx - 1]["t"] if idx > 0 else None
        if prev in (None, "T"):
            # nothing has happened since the last conversation: a greeting, not an after-action regroup
            out = [(nid, fmt(self.rotor("meet", FL.MEET).next(), place=place))]
            reply = (P, self.rotor("meetreply", FL.MEET_REPLY).next())
        else:
            out = [(nid, fmt(self.rotor("regroup", FL.REGROUP).next(), place=place))]
            reply = (P, self.rotor("afterreply", FL.AFTER_REPLY).next())
        if quirks and h(q, "qa") % 2:
            out.append((nid, self.rotor("q/" + nid, quirks).next()))
        else:
            out.append(reply)
        return out

    def _peek_text(self, st, ctx, steps, idx):
        """The objective text the next step will get (for 'I need you to ...' openers)."""
        seg = st.get("seg")
        if seg and seg["text"]:
            return seg["text"]
        m = st["map"]
        if st["t"] == "T":
            return None
        place = PL.name(m, st["marker"])
        if st["t"] == "R":
            return "head to %s" % place
        if st["t"] in ("F", "F2"):
            enemy = self._foe(st, ctx)
            foes = ctx["kw"].get("foes_name") or ctx["spec"]["foe_names"].get(enemy) or FOE_NAMES[enemy]
            return "deal with the %s at %s" % (foes, place)
        if st["t"] == "G":
            return "bring me %s from %s" % (self._noun(st, ctx, idx), place)
        if st["t"] == "M":
            return "go and meditate at %s" % place
        if st["t"] == "I":
            return "take a look at %s" % place
        return None

    def _pad(self, nid, lines, ctx, first=False):
        if lines[0][0] == P:
            quirks = FL.QUIRKS.get(nid)
            if quirks:
                return (nid, self.rotor("q/" + nid, quirks).next())
            return (nid, self.rotor("close", FL.CLOSE).next())
        # the quest giver's line implies a task: answer it; later lines get a quiet acknowledgement
        if first:
            return (P, self.rotor("reply", FL.REPLY).next())
        return (P, self.rotor("ack", ACK).next())

    # --- group conversations -------------------------------------------------
    def _present(self, nid, m, q, ctx, near=False):
        """Can ``nid`` plausibly stand in a scene of quest ``q`` on map ``m``? With ``near``, someone
        from the sect, the forest or the town may also have walked over to one of the other two."""
        if nid == NP_DEMON or not self.active(nid, q):
            return False
        a, hid = self.window(nid)
        if (a and q < a) or (hid and q > hid):
            return False
        home = NPCS[nid]["home"]
        if home and home["map"] != m and nid not in EN.ROAM and nid not in ctx["speakers_on"].get(m, set()) \
                and not (near and home["map"] in NEAR_MAPS and m in NEAR_MAPS):
            return False
        if not home and nid not in EN.ROAM and nid not in ctx["speakers_on"].get(m, set()) \
                and nid not in ctx["spec"]["cast"]:
            return False
        return True

    def _absent(self, ctx):
        """Cast members the beat talks about but never lets speak: they are elsewhere."""
        if "absent" not in ctx:
            speak = {ln[0] for s in ctx["beat"]["segs"] for ln in s["lines"]}
            text = " ".join([ctx["beat"]["title"], ctx["beat"]["summary"]]
                            + [ln[1] for s in ctx["beat"]["segs"] for ln in s["lines"]])
            out = set()
            for nid in ctx["spec"]["cast"]:
                if nid in speak:
                    continue
                names = {SHORT.get(nid, ""), NPCS[nid]["name"]}
                names = {n.replace("the ", "") for n in names if n}
                if any(re.search(r"\b%s\b" % re.escape(n), text) for n in names if len(n) > 2):
                    out.add(nid)
            ctx["absent"] = out
        return ctx["absent"]

    def _companions(self, giver, m, mk, ctx, want, taken):
        """Up to ``want`` companions for a scene with ``giver`` (None: no quest giver) at ``mk``."""
        q = ctx["q"]
        gcat = MO.category(giver, q) if giver else None
        villain = gcat == "demonic"

        def ok(n, near=False):
            if n in taken or n == giver or n in self._absent(ctx) or not self._present(n, m, q, ctx, near):
                return False
            c = MO.category(n, q)
            if villain:
                return c in ("elder", "peer", "junior", "rogue")
            return c not in ("demonic", "prisoner")

        quest_npcs = [n for n in ctx["quest_npcs"] if ok(n)]
        local = [n for n, (dm, ds) in sorted(EN.DISTRICT.items()) if dm == m and mk in ds and ok(n)]
        cast = [n for n in ctx["spec"]["cast"] if ok(n)]
        rovers = [n for n in EN.ROVERS.get(m, []) if ok(n) and gcat in (None, "elder", "peer", "junior", "town")]
        # last resorts: anyone who lives on this map, then the cast from a neighbouring map
        map_minor = [n for n, (dm, ds) in sorted(EN.DISTRICT.items()) if dm == m and ok(n)]
        near_cast = [n for n in ctx["spec"]["cast"] if ok(n, near=True)]
        out = []
        salt = (q, giver, mk)
        for _ in range(want):
            tiers = []
            r = h(salt, len(out), "tier") % 100
            if local and r < 45:
                tiers.append(local)
            if quest_npcs and r % 2 == 0:
                tiers.append(quest_npcs)
            tiers += [cast, quest_npcs, local, rovers, map_minor, near_cast]
            pick = None
            for tier in tiers:
                cands = [n for n in tier if n not in out]
                if cands:
                    # every giver cycles through everyone in a stable order, so the same pair rarely repeats
                    pick = self.rotor("comp/%s" % giver, sorted(NPCS)).next(lambda n: n in cands)
                    break
            if pick is None:
                break
            out.append(pick)
        return out

    def _ensemble(self, objs, steps, ctx):
        """Bring companions into the quest's conversations (see ensemble.py)."""
        q = ctx["q"]
        ctx["quest_npcs"] = []
        ctx["speakers_on"] = {}
        for o in objs:
            for sp in dsl_speakers(o) + ([o["npc"]] if o["type"] == "talk" else []):
                ctx["speakers_on"].setdefault(o["map"], set()).add(sp)
                if sp not in ctx["quest_npcs"]:
                    ctx["quest_npcs"].append(sp)
        for oi, o in enumerate(objs):
            if o["type"] != "talk":
                continue
            st = steps[oi]
            already = len({ln["speaker"] for ln in o["dialogue"] if not ln.get("cond")} - {P, N}) >= 2
            if already and h(q, oi, "more") % 100 >= 40:
                continue
            mk = o["at"] or NPCS[o["npc"]]["home"]["marker"]
            want = 2 if h(q, oi, "two") % 100 < TWO_COMPANIONS else 1
            comps = self._companions(o["npc"], o["map"], mk, ctx, want, taken=set(dsl_speakers(o)))
            if comps:
                self._join(o, comps, st.get("key", "ally"), ctx, oi)
        if not any(is_group(o) for o in objs):
            self._field_scene(objs, ctx)

    def _join(self, o, comps, key, ctx, oi):
        q, giver = ctx["q"], o["npc"]
        scene = EN.END if key in ("back", "after", "found") else EN.START
        gcat = MO.category(giver, q)
        group = EN.GIVER_GROUP.get(gcat, "town")
        dl = o["dialogue"]
        plain = [i for i, ln in enumerate(dl) if not ln.get("cond")]
        room = 7 - len(plain)
        total_room = 10 - len(dl)
        if room < 1 or total_room < 1:
            return
        first = next((i for i in plain if dl[i]["speaker"] == giver), plain[0])
        new = []
        c1 = comps[0]
        gname, cname = short(giver), short(c1)
        pair = EN.PAIRS.get((c1, giver))
        if gcat == "demonic":
            pool = EN.CONFRONT.get(MO.category(c1, q), EN.CONFRONT["peer"])
            new.append((c1, fmt(self.rotor("confront/%s" % MO.category(c1, q), pool).next(), giver=gname)))
        elif pair and h(q, oi, "pair") % 100 < 55:
            a, b = self.rotor("pair/%s/%s" % (c1, giver), pair).next()
            new += [(c1, fmt(a, giver=gname, comp=cname)), (giver, fmt(b, giver=gname, comp=cname))]
        else:
            intent, line = self._chime(c1, scene, q, giver)
            new.append((c1, fmt(line, giver=gname, comp=cname, place=PL.name(o["map"], o["at"] or
                                                                            NPCS[giver]["home"]["marker"]))))
            r = h(q, oi, "resp") % 100
            # the player answers only if the next line isn't the player's already
            if 55 <= r < 85 and first + 1 < len(dl) and dl[first + 1]["speaker"] == P:
                r = 0
            if r < 55:
                pool = EN.RESP_GIVER[group].get(intent)
                if pool:
                    new.append((giver, fmt(self.rotor("rg/%s/%s" % (group, intent), pool).next(), comp=cname,
                                           giver=gname)))
            elif r < 85:
                new.append((P, self.rotor("rp/" + intent, EN.RESP_PLAYER[intent]).next()))
        for c2 in comps[1:]:
            if len(new) + 1 > room:
                break
            intent, line = self._chime(c2, scene, q, giver)
            new.append((c2, fmt(line, giver=gname, comp=short(c2), place=PL.name(o["map"], o["at"] or
                                                                                 NPCS[giver]["home"]["marker"]))))
        new = new[:room]
        cond = []
        ccat = MO.category(c1, q)
        if EN.COND.get(ccat) and h(q, oi, "cond") % 100 < COND_LINE and total_room - len(new) >= 1:
            c, text = self.rotor("cond/" + ccat, EN.COND[ccat]).next()
            cond = [(c1, fmt(text, giver=gname, comp=cname), c)]
        # companions speak once the person the player came to see has had a word
        at = first + 1
        ins = _lines(new + cond)
        o["dialogue"] = dl[:at] + ins + dl[at:]
        if not any(ln["speaker"] == P and not ln.get("cond") for ln in o["dialogue"]) and len(plain) + len(new) < 7 \
                and len(o["dialogue"]) < 10:
            o["dialogue"].append({"speaker": P, "text": self.rotor("reply", FL.REPLY).next()})

    def _chime(self, nid, scene, q, giver):
        """One of ``nid``'s own lines whose intent suits the scene (before or after the action)."""
        def fits(e):
            return e[0] in scene and _era_ok(e, q) and (giver or ("{giver}" not in e[1] and "{Giver}" not in e[1]))
        full = EN.CHIME.get(nid, [])
        if not any(fits(e) for e in full):
            full = GENERIC_CHIME.get(MO.category(nid, q), GENERIC_CHIME["town"])
        i = self.rotor("chime/%s/%d" % (nid, len(full)), list(range(len(full)))).next(lambda i: fits(full[i]))
        return full[i][0], full[i][1]

    def _field_scene(self, objs, ctx):
        """No conversation of the quest has two NPCs yet: two companions share the moment at a
        reach or interact objective (or a meditation, when there is nothing else)."""
        q = ctx["q"]
        hosts = [i for i, o in enumerate(objs) if o["type"] in ("reach", "interact")] + \
                [i for i, o in enumerate(objs) if o["type"] == "talk"] + \
                [i for i, o in enumerate(objs) if o["type"] == "meditate"]
        for i in hosts:
            o = objs[i]
            mk = o.get("marker") or o.get("at") or NPCS[o["npc"]]["home"]["marker"]
            giver = o.get("npc")
            taken = set(dsl_speakers(o))
            comps = self._companions(giver, o["map"], mk, ctx, 2 if giver is None else 1, taken)
            present = [sp for sp in dsl_speakers(o) if sp != giver]
            if giver:
                present = [giver] + present
            speakers_now = list(dict.fromkeys(present + comps))
            if len(speakers_now) < 2:
                continue
            a, b = speakers_now[0], speakers_now[1]
            lines = []
            if a not in dsl_speakers(o):
                lines.append((a, self.rotor("field/" + MO.category(a, q),
                                            EN.FIELD.get(MO.category(a, q), EN.FIELD["town"])).next()))
            lines.append((b, self.rotor("fieldans/" + MO.category(b, q),
                                        EN.FIELD_ANSWER.get(MO.category(b, q), EN.FIELD_ANSWER["town"])).next()))
            lines.append((P, self.rotor("fieldp", EN.FIELD_PLAYER).next()))
            dl = o.get("dialogue") or []
            plain = sum(1 for ln in dl if not ln.get("cond"))
            if plain + len(lines) > 7 or len(dl) + len(lines) > 10:
                continue
            o["dialogue"] = dl + _lines(lines)
            if is_group(o):
                return
        raise ValueError("q%04d %r: could not stage a group conversation (cast %s, objectives %s)"
                         % (q, ctx["beat"]["title"], ctx["spec"]["cast"],
                            [(o["type"], o.get("npc"), o["map"], len(o.get("dialogue") or [])) for o in objs]))


# the generic companion lines of a category, for characters without their own
GENERIC_CHIME = {
    "elder": [("advice", "Go carefully. Carelessness is the only enemy that never retreats."),
              ("agree", "Sound. Proceed."), ("praise", "Well done. Truly."), ("relief", "Good. Good.")],
    "peer": [("offer", "Need a hand? I've two. One's even clean."), ("tease", "Try not to trip."),
             ("praise", "Nice work."), ("relief", "About time.")],
    "junior": [("worry", "Be careful, {senior}!"), ("praise", "You're amazing, {senior}!"),
               ("question", "What was it like?")],
    "town": [("worry", "Heavens keep you safe, immortal."), ("praise", "Heaven bless you!"),
             ("agree", "That's right, that is."), ("relief", "Oh, thank the ancestors.")],
    "rogue": [("advice", "Watch your back."), ("praise", "Not bad."), ("doubt", "Smells like a trap.")],
    "demonic": [("tease", "The moon is watching."), ("praise", "Enjoy it, heir.")],
}


def kind_is(ctx, k):
    return ctx["beat"]["kind"] == k


def _words(text):
    return set(re.findall(r"[a-z]+", text))


def _era_ok(entry, q):
    if len(entry) < 3:
        return True
    lo, hi = entry[2]
    return lo <= q <= hi


def short(nid):
    return SHORT.get(nid, NPCS[nid]["name"])


def is_group(o):
    """Two or more NPCs speak (unconditionally) and the player takes part."""
    plain = [ln for ln in o.get("dialogue") or [] if not ln.get("cond")]
    npcs = {ln["speaker"] for ln in plain} - {P, N}
    return len(npcs) >= 2 and (any(ln["speaker"] == P for ln in plain) or bool(o.get("choices")))


# ---------------------------------------------------------------- moral choices

def choice_family(qd, beat, q):
    """Which template family of morality.TEMPLATES fits a built quest, with its
    slots, or None. Every quest must end up with a choice (see ensure_choice),
    so each branch only requires what its own templates actually need -- e.g.
    "find"/"gather"/"train"/"cultivate" don't need a talk objective at all."""
    objs = qd["objectives"]
    fam = MO.FAMILY_OF_KIND.get(beat["kind"])
    if fam is None:
        return None
    fights = [o for o in objs if o["type"] == "defeat"]
    if fam == "boss":
        return ("boss", {}) if fights else None
    if fam == "fight" or (fights and fam in ("find", "social")):
        for o in fights:
            if o["enemy"] in MO.HUMAN_FOES:
                return "fight_human", {"foes": FOE_NAMES[o["enemy"]]}
        for o in fights:
            if o["enemy"] in MO.BEAST_FOES:
                return "fight_beast", {"foes": FOE_NAMES[o["enemy"]]}
        if fam == "fight":
            return None
    if fam == "gather":
        got = [o for o in objs if o["type"] == "collect"]
        if not got:
            return None
        return "gather", {"noun": ITEM_NOUNS[got[0]["item"]], "item": got[0]["item"]}
    if fam == "find":
        return ("find", {}) if any(o["type"] in ("interact", "reach") for o in objs) else None
    if fam == "social":
        talks = [o for o in objs if o["type"] == "talk"]
        if not talks:
            return None
        last_talk = talks[-1]
        if last_talk["npc"] in MO.OFFICIALS:
            return "social_official", {}
        return MO.SOCIAL_BY_CATEGORY[MO.category(last_talk["npc"], q)], {}
    return fam, {}


## An objective can only host a choice if it has dialogue of its own (talk,
## reach and interact objectives all get at least one line; defeat, collect,
## meditate, tribulation and cinematic never do) -- see build_story.compile_choices.
_CHOICE_HOST_TYPES = ("talk", "reach", "interact")


def _last_choice_host(objs, q):
    """The last talk objective, or (failing that) the last reach/interact
    objective -- every generated quest pattern has at least one of these."""
    for want in _CHOICE_HOST_TYPES:
        hosts = [i for i, o in enumerate(objs) if o["type"] == want]
        if hosts:
            return hosts[-1]
    raise ValueError("q%04d: no talk/reach/interact objective to hang a choice on" % q)


def infer_family(qd, q):
    """Which TEMPLATES family fits a fully-built quest (any quest, hand-written
    or generated), read straight from its objectives -- used to guarantee
    every quest offers a choice even when it wasn't authored with one."""
    objs = qd["objectives"]
    fights = [o for o in objs if o["type"] == "defeat"]
    for o in fights:
        if o["enemy"] in MO.HUMAN_FOES:
            return "fight_human", {"foes": FOE_NAMES.get(o["enemy"], o["enemy"])}
    for o in fights:
        if o["enemy"] in MO.BEAST_FOES:
            return "fight_beast", {"foes": FOE_NAMES.get(o["enemy"], o["enemy"])}
    if fights:
        return "boss" if any(o.get("name") for o in fights) else "fight_human", {"foes": "enemies"}
    got = [o for o in objs if o["type"] == "collect"]
    if got:
        return "gather", {"noun": ITEM_NOUNS.get(got[0]["item"], got[0]["item"]), "item": got[0]["item"]}
    if any(o["type"] in ("meditate", "tribulation") for o in objs):
        return "cultivate", {}
    talks = [o for o in objs if o["type"] == "talk"]
    if talks:
        nid = talks[-1]["npc"]
        if nid in MO.OFFICIALS:
            return "social_official", {}
        return MO.SOCIAL_BY_CATEGORY[MO.category(nid, q)], {}
    if any(o["type"] in ("interact", "reach") for o in objs):
        return "find", {}
    return None


def ensure_choice(qd, q, rotor):
    """Attach a template choice to ``qd`` if it doesn't already have one
    (called after every fallback: hand-written and beat-family choices come
    first). ``rotor`` cycles a family's variants so nearby quests of the same
    family don't repeat a dilemma."""
    if any(o.get("choices") for o in qd["objectives"]):
        return
    fam = infer_family(qd, q)
    if fam is None:
        raise ValueError("q%04d: %r has no objective to hang a fallback choice on" % (q, qd["title"]))
    name, extra = fam
    variants = MO.TEMPLATES[name]
    tpl = variants[rotor("choice/" + name, list(range(len(variants)))).next()]
    attach_choice(qd, tpl, q, **extra)


def attach_choice(qd, choice, q, spec=None, beat=None, foes="", noun="", item=None, at=None):
    """Offer ``choice`` (morality.Ch) after the quest's last conversation (or objective ``at``).
    Every option gets the NPC's reaction as its reply."""
    objs = qd["objectives"]
    if at is None:
        at = choice.get("at", "last")
    if at == "last":
        at = _last_choice_host(objs, q)
    o = objs[at]
    nid = o.get("npc")
    name = SHORT.get(nid, NPCS[nid]["name"]) if nid else ""
    o["choice_prompt"] = _cap(fmt(choice["prompt"], foes=foes, noun=noun, name=name))
    # the others present react too: after the person the player answered, or on their own at a
    # reach / interact objective, where nobody else would
    others = [sp for sp in dsl_speakers(o) if sp != nid and MO.category(sp, q) != "prisoner"]
    opts = []
    for k, opt in enumerate(choice["options"]):
        law, good = opt["align"]["law"], opt["align"]["good"]
        reply = [tuple(r) for r in opt["reply"]]
        if nid:
            reply.append((nid, MO.reaction(nid, law, good, salt=(q, k), q=q)))
        if others and len(reply) < 3 and (nid is None or h(q, k, "aside") % 100 < ASIDE_RATE):
            comp = others[h(q, k, "who") % len(others)]
            ccat = MO.category(comp, q)
            direction = MO.direction(law, good)
            asides = [a for a in EN.ASIDE.get(ccat, {}).get(direction, []) if nid or "{giver}" not in a]
            # the minor cast always speaks in asides: the named cast's reactions mention their own lives
            if asides and (comp in MINOR or h(q, k, "asidekind") % 2):
                reply.append((comp, fmt(asides[h(q, k, comp) % len(asides)], giver=short(nid) if nid else "")))
            else:
                line = MO.reaction(comp, law, good, salt=(q, k, "c"), q=q)
                if not reply or line != reply[-1][1]:
                    reply.append((comp, line))
        items = {}
        for it, n in opt["reward"]["items"].items():
            items[item if it == "@item" else it] = n
        if None in items:
            items["spirit_stone"] = items.pop(None)
        opts.append({"text": opt["text"], "align": {"law": law, "good": good}, "reply": _lines(reply),
                     "reward": {"xp": opt["reward"]["xp"], "items": items}, "flag": opt["flag"],
                     "attitude": dict(opt["attitude"]), "cond": opt["cond"]})
    o["choices"] = opts
    return o


# objective text keyword -> the world_spec prop that should stand there
PROP_WORDS = [
    # (words, prop, maps it applies on or None); the first match wins, so specific words come first
    (("bell",), "bronze_bell", None),
    (("notice", "noticeboard", "posting", "bounty"), "notice_board", None),
    (("ancestral", "memorial", "spirit tablet"), "ancestral_tablet", None),
    (("tortoise",), "tortoise_stele", None),
    (("furnace", "kiln"), "pill_furnace", None),
    (("ding", "tripod", "censer", "cauldron"), "bronze_ding", None),
    (("mirror",), "bronze_mirror", None),
    (("soul lantern",), "soul_lantern", None),
    (("lamp", "lantern"), "spirit_lamp", None),
    (("drum",), "war_drum", None),
    (("coffin", "sarcophagus", "casket"), "sealed_coffin", None),
    (("offering", "offerings"), "offering_table", None),
    (("armillary", "orrery", "astrolabe", "star chart"), "armillary_sphere", None),
    (("medicine cabinet", "drawers", "apothecary"), "medicine_cabinet", None),
    (("wine", "jar"), "wine_jars", None),
    (("loom",), "loom", None),
    (("map", "chart"), "map_table", None),
    (("statue",), "crane_statue", None),
    (("fountain",), "spirit_fountain", None),
    (("puppet", "dummy", "dummies"), "puppet_frame", None),
    (("drying",), "herb_drying_rack", None),
    (("anchor", "winch"), "chain_anchor", None),
    (("abacus", "ledger", "accounts", "tallies", "tally"), "abacus_desk", None),
    (("boat", "barge", "nets"), "fishing_boat", None),
    (("wishing", "ribbon"), "wishing_tree", None),
    (("screen",), "jade_screen", None),
    (("lion",), "guardian_lion", None),
    (("shelf", "shelves", "archive", "library"), "scroll_rack", None),
    (("cage", "pen", "cell"), "prison_cage", None),
    (("obelisk",), "demon_obelisk", None),
    (("altar",), "blood_altar", ("blood_abyss",)),
    (("altar", "shrine"), "offering_table", None),
    (("chest", "strongbox", "coffer", "box", "crate", "sack", "hoard", "cache", "tent"), "treasure_chest", None),
    (("pillar",), "rune_pillar", None),
    (("tablets",), "stone_tablet_array", None),
    (("stele", "tablet", "mural", "inscription", "carving", "results", "question", "stone face", "plaque"),
     "stone_stele", None),
    (("slip", "scroll", "letter", "book", "chronicle", "notes", "manual", "records"), "jade_slip", None),
    (("teleport", "array"), "teleport_array", None),
    (("spirit stone", "crystal", "vein", "pillar-stone", "lodestone"), "spirit_stone", None),
]


def infer_prop(text, map_id=None):
    """The prop an objective's text names ("Read the notice board" -> notice_board), or None."""
    if not text:
        return None
    low = text.lower()
    for words, prop, maps in PROP_WORDS:
        if maps and map_id not in maps:
            continue
        for w in words:
            if re.search(r"\b%s(s|es)?\b" % re.escape(w), low):
                return prop
    return None


# how objective text refers to each character
SHORT = {
    "master_yun": "the Sect Master", "elder_mo": "Elder Mo", "elder_bai": "Elder Bai", "elder_gu": "Elder Gu",
    "elder_hua": "Elder Hua", "senior_han": "Han Xue", "senior_wei": "Wei Tong", "rival_zhao": "Zhao Kang",
    "gate_lu": "Lu Ping", "steward_qian": "Steward Qian", "xiao_man": "Xiao Man", "xiao_shi": "Xiao Shi",
    "hermit_lan": "the hermit", "wanderer_ye": "Ye Wuming", "bandit_tie": "Iron-Fang",
    "magistrate_zhou": "Magistrate Zhou", "innkeeper_fang": "Madam Fang", "constable_du": "Constable Du",
    "widow_liu": "Widow Liu", "keeper_hong": "Keeper Hong", "ferryman_pan": "Old Pan", "merchant_jin": "Merchant Jin",
    "patriarch_xue": "Xue Wuji", "crimson_xuemei": "Xue Mei", "star_sage": "Qing Luan", "heart_demon": "your heart demon",
    "yan_tie": "Yan Tie", "liu_er": "Liu Er", "bandit_gou": "Gou the Scarred", "young_ruan": "Ruan Jingtao",
    "master_ruan": "Sect Master Ruan", "abbess_jing": "Abbess Jing", "ancestor_zhao": "Ancestor Zhao",
    "rung_luo": "Luo Hui", "rung_shan": "the Rust Monk", "rung_rong": "Madam Ninefold", "rung_kong": "Brother Hollow",
    "rung_wen": "the Butcher", "rung_si": "Lady Silk", "rung_chen": "Xue Chen",
    "deacon_shen": "Deacon Shen", "kiln_tao": "Kiln-Mistress Tao", "cook_bao": "Old Bao", "keeper_ling": "Ling Qiu",
    "bell_zhong": "Zhong Ming", "warden_qiu": "Old Qiu", "fan_rui": "Fan Rui", "tang_ling": "Tang Ling",
    "auntie_ruo": "Auntie Ruo", "headman_kuang": "Headman Kuang", "woodcutter_shu": "Big Shu",
    "huntress_meng": "Meng Sanniang", "alchemist_qu": "Qu Wanqing", "watcher_pei": "Pei Yuan",
    "scholar_ouyang": "Scholar Ouyang", "weaver_qiao": "Qiao Niang", "apothecary_wang": "Wang Pu",
    "actress_yu": "Yu Hongxiu", "matron_bi": "Matron Bi", "captain_lei": "Captain Lei", "tavern_huo": "Huo Da",
    "broker_ku": "Ku the Broker", "acolyte_hei": "Hei Yan", "servant_qingyi": "Qingyi", "warden_he": "Warden He",
    "recorder_shu": "Scribe Shu",
}

# short acknowledgements that follow a closing line
ACK = ["...", "Mm.", "Yes.", "I know.", "I'll remember.", "Thank you.", "I hear you.", "All right.",
       "I won't forget it.", "Yes. I think so too."]


GEN = Gen()


def build_chapter(spec, number, realm=None, stage=None):
    return GEN.chapter(spec, number, realm=realm, stage=stage)


## Extra quests spliced into a *legacy* (voiced) chapter, between its original
## lead-in quests and its climax (see volumes._legacy_chapter). Reuses the same
## beat/pattern/choice machinery as a generated chapter, just without a
## fixed beat count and without ever granting a realm/stage itself -- the
## legacy chapter's own hand-written climax quest still does that.
## ``chapter_number`` keys into choices.NEW exactly like a generated chapter's
## (chapter_number, beat_index) -- legacy and generated chapter numbers never
## collide, so the same authored-choices dict serves both.
def build_extra(spec, chapter_number, first, vol):
    quests = []
    for i, beat in enumerate(spec["beats"]):
        q = first + i
        qd = GEN.quest(spec, beat, q, vol, i)
        authored = CHOICES.get((chapter_number, i))
        if authored:
            attach_choice(qd, authored, q, spec, beat)
        else:
            fam = choice_family(qd, beat, q)
            if fam:
                name, extra = fam
                variants = MO.TEMPLATES[name]
                tpl = variants[GEN.rotor("choice/" + name, list(range(len(variants)))).next()]
                attach_choice(qd, tpl, q, spec, beat, **extra)
        ensure_choice(qd, q, GEN.rotor)
        quests.append(qd)
    return quests

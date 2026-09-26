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

from . import fillers as FL
from . import numbering as NB
from . import places as PL
from .dsl import N, P, chapter, collect, defeat, interact, meditate, quest, reach, talk
from .npcs import NPCS

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
        elif isinstance(it, tuple) and len(it) == 2:
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

    def rotor(self, name, pool):
        if name not in self.rot:
            self.rot[name] = Rotor(pool, name)
        return self.rot[name]

    # --- presence --------------------------------------------------------
    @staticmethod
    def window(nid):
        n = NPCS[nid]
        a = NB.resolve_id(n["appear_from"]) if n["appear_from"] else None
        hid = NB.resolve_id(n["hidden_after"]) if n["hidden_after"] else None
        return a, hid

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
            quests.append(self.quest(spec, beat, q, vol, i,
                                     realm=realm if last else None, stage=stage if last else None))
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
            # a pattern's optional interact/collect with nothing authored for it would be noise: drop it
            keep = []
            for st in steps:
                if "seg" not in st and st["t"] == "I" and not (kw.get("prop") or kw.get("thing")):
                    continue
                if "seg" not in st and st["t"] == "G" and kind not in ("gather", "hunt", "festival", "break") \
                        and not (kw.get("item") or kw.get("noun")):
                    continue
                keep.append(st)
            if len(keep) >= 2:
                steps = keep
        base_map = kw.get("map", spec["map"])
        ctx = {"q": q, "vol": vol, "spec": spec, "beat": beat, "kw": kw, "roles": {}, "npcs": {},
               "fights": set(), "base_map": base_map}
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
                st["marker"] = self._place(st, ctx)
                if st["t"] in ("F", "F2", "X"):
                    ctx["fights"].add((st["map"], st["marker"]))
        for idx, st in enumerate(steps):
            if st["t"] == "T":
                st["at"] = self._talk_at(st, ctx, steps, idx)
        objs = []
        for idx, st in enumerate(steps):
            objs.append(self._objective(st, ctx, steps, idx))
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
        has_npc = any(sp not in (P, N) for sp, _ in seg["lines"])
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
            for sp, _ in seg["lines"]:
                if sp not in (P, N):
                    return sp
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
        """Where a talk NPC stands: the authored marker if it is free, else at
        home, else near the previous objective, else any free meeting place.
        Never on another present NPC's home, nor where this quest fights."""
        q, m, nid = ctx["q"], st["map"], st["npc"]
        seg = st.get("seg")
        explicit = seg["marker"] if seg and seg["marker"] else None
        home = NPCS[nid]["home"]
        home_mk = home["marker"] if home and home["map"] == m and self.at_home(nid, m, q) else None
        homes = self.homes(m, q)
        want = None
        if st["place"]:
            want = ctx["roles"].get((m, st["place"]))
        if want is None and idx > 0 and steps[idx - 1]["map"] == m and steps[idx - 1].get("marker"):
            want = steps[idx - 1]["marker"]
        pool = PL.POOLS[m]["meet"]
        cands = ([explicit] if explicit else []) + ([home_mk] if home_mk else []) + ([want] if want else []) \
            + sorted(pool, key=lambda k: h(q, nid, k))
        for c in cands:
            if (m, c) in ctx["fights"]:
                continue
            if c == home_mk:
                return None
            if c in homes and homes[c] != nid:
                continue
            if c != explicit and not self.allowed(m, c, q, "meet"):
                continue
            return c
        raise ValueError("q%04d: no place for %s to stand on %s" % (q, nid, m))

    # --- places ----------------------------------------------------------
    def _place(self, st, ctx):
        q, m = ctx["q"], st["map"]
        seg = st.get("seg")
        if seg and seg["marker"]:
            ctx["roles"].setdefault((m, st["place"] or "p1"), seg["marker"])
            return seg["marker"]
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
        kind = {"R": "reach", "F": "fight", "F2": "fight", "X": "fight", "G": "gather", "M": "med", "I": "prop"}[st["t"]]
        used = set(ctx["roles"].values())
        rot = self.rotor("%s/%s" % (m, kind), PL.POOLS[m][kind])
        mk = rot.next(lambda c: c not in used and self.allowed(m, c, q, kind))
        ctx["roles"].setdefault(key, mk)
        return mk

    def _fits(self, st, m, mk, q):
        kind = {"R": "reach", "F": "fight", "F2": "fight", "X": "fight", "G": "gather", "M": "med", "I": "prop"}[st["t"]]
        return self.allowed(m, mk, q, kind, explicit=True)

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
            text = self._text(key, st, ctx, name=name, place=place)
            if not lines:
                lines = self._filler_talk(nid, {"after": "ally", "found": "ally"}.get(key, key), st, ctx, steps, idx)
            elif len(lines) == 1:
                lines.append(self._pad(nid, lines, ctx, first=idx == 0))
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
            item = kw.get("item") or spec["items"][h(q, idx, "item") % len(spec["items"])]
            noun = kw.get("noun") or spec["nouns"].get(item) or ITEM_NOUNS[item]
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
            prop = infer_prop(seg["text"] if seg else None) or kw.get("prop") \
                or spec["props"][h(q, idx, "prop") % len(spec["props"])]
            thing = kw.get("thing") or spec["things"].get(prop) or THINGS[prop]
            if seg and seg["text"]:
                text = seg["text"]
            else:
                verbs = PROP_VERBS[prop]
                text = fmt(verbs[h(q, idx, "verb") % len(verbs)], thing=thing)
                if len(text) > MAX_TEXT:
                    text = fmt("Examine {thing}", thing=thing)[:MAX_TEXT]
            if not lines:
                lines = [(N, fmt(self.rotor("int/" + prop, FL.INTERACT[prop]).next(), thing=thing))]
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
            if s["t"] == "T" and s.get("npc") and NPCS[s["npc"]]["model"] not in ("demon_cultivator", "blood_patriarch"):
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
                out.append((P, self.rotor("reply2", ["Glad to help.", "Any time.", "It was nothing. Well, it was something.",
                                                     "Just doing my part.", "I learned a lot, actually.",
                                                     "Next time, maybe something easier?"]).next()))
            return out
        place = PL.name(st["map"], st["at"]) if st["at"] else "here"
        out = [(nid, fmt(self.rotor("regroup", FL.REGROUP).next(), place=place))]
        if quirks and h(q, "qa") % 2:
            out.append((nid, self.rotor("q/" + nid, quirks).next()))
        else:
            out.append((P, self.rotor("reply", FL.REPLY).next()))
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
            kw, spec, q = ctx["kw"], ctx["spec"], ctx["q"]
            item = kw.get("item") or spec["items"][h(q, idx, "item") % len(spec["items"])]
            noun = kw.get("noun") or spec["nouns"].get(item) or ITEM_NOUNS[item]
            return "bring me %s from %s" % (noun, place)
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
        text = lines[0][1].lower()
        asks = text.rstrip().endswith("?") or re.search(
            r"\b(go|come|find|bring|help|take|meet|follow|fetch|hurry|quickly|now)\b", text)
        if first and asks:
            return (P, self.rotor("reply", FL.REPLY).next())
        return (P, self.rotor("ack", ACK).next())


def kind_is(ctx, k):
    return ctx["beat"]["kind"] == k


# objective text keyword -> the world_spec prop that should stand there
PROP_WORDS = [
    (("bell",), "bronze_bell"),
    (("cage", "pen", "cell"), "prison_cage"),
    (("obelisk",), "demon_obelisk"),
    (("altar",), "blood_altar"),
    (("chest", "strongbox", "coffer", "box", "crate", "sack", "hoard", "cache", "tent"), "treasure_chest"),
    (("stele", "tablet", "mural", "inscription", "carving", "results", "question", "stone face", "plaque"),
     "stone_stele"),
    (("slip", "scroll", "letter", "ledger", "tallies", "book", "chronicle", "map", "notes", "manual", "records"),
     "jade_slip"),
    (("teleport", "array"), "teleport_array"),
    (("spirit stone", "crystal", "vein", "pillar-stone", "lodestone"), "spirit_stone"),
]


def infer_prop(text):
    if not text:
        return None
    low = text.lower()
    for words, prop in PROP_WORDS:
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
}

# short acknowledgements that follow a closing line
ACK = ["...", "Mm.", "Yes.", "I know.", "I'll remember.", "Thank you.", "I hear you.", "All right.",
       "I won't forget it.", "Yes. I think so too."]


GEN = Gen()


def build_chapter(spec, number, realm=None, stage=None):
    return GEN.chapter(spec, number, realm=realm, stage=stage)

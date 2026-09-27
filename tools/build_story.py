#!/usr/bin/env python3
"""Compile the main story (tools/story) into godot/data/story.json and validate it.

    python3 tools/build_story.py            # validate, write story.json, print stats
    python3 tools/build_story.py --check    # validate; exit 1 if story.json is out of date
    python3 tools/build_story.py --quiet    # no stats
    python3 tools/build_story.py --quests docs/QUESTS.md   # also write the quest list

The saga has 10 volumes (one per major cultivation stage) x 10 chapters x 10
quests = 1000 quests, ids q0001..q1000. The ten original chapters keep their
voice files under their original keys (q017_o2_l1 ...); lines of the 90 new
chapters are text-only ("voice": null).

Cultivation follows a fixed schedule (chapter c of volume v ends at minor stage
c of REALMS[v]; chapter 1 is the breakthrough, with a heavenly tribulation), and
the story's moral choices, conditional lines, NPC greetings and alignment
rewards are validated here too (see docs/STORY.md, "How it is stored").

Pure Python 3 standard library. Every map, marker, NPC model, enemy, item,
prop and realm is checked against tools/world_spec.py; any error exits 1.
"""

import argparse
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import world_spec as W  # noqa: E402
import story  # noqa: E402
from story import numbering as NB  # noqa: E402
from story import morality as MO  # noqa: E402
from story import threads as TH  # noqa: E402

OUT = os.path.join(ROOT, "godot", "data", "story.json")
VOICE_DIR = "res://audio/voice/"
TOKENS = ["player", "junior", "senior", "sibling", "they", "them", "their"]
TOKEN_RE = re.compile(r"\{([^{}]*)\}")
ANIMS = {"idle", "salute", "cast", "talk", "meditate", "attack"}
MAX_LINE_WORDS = 32
MAX_HUD_CHARS = 64
MAX_SUMMARY_CHARS = 240
MAX_BOSS_NAME = 40
# blood_abyss markers inside the fortress, which folds into the void after the
# failed blood moon (chapter 42) and returns only for the final march (chapter 100)
FORTRESS = {"DemonGate", "FortressCourt", "AltarOfBlood", "PatriarchThrone", "PrisonCages"}


class Errors:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def err(self, where, msg):
        self.errors.append("%s: %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("%s: %s" % (where, msg))


E = Errors()


def qid(n):
    return NB.qid(n)


def words(text):
    return len(text.split())


def is_gendered(speaker, text):
    return speaker == "player" or bool(TOKEN_RE.search(text or ""))


def est_duration(text):
    """Seconds a shot with this line lasts. Fitted to the synthesised cast (0.22-0.40 s/word);
    every cinematic line currently ends at least 0.6 s before its shot does."""
    return max(3.5, round(1.5 + 0.38 * words(text), 1))


def check_text(where, text, max_words=MAX_LINE_WORDS):
    if not isinstance(text, str) or not text.strip():
        E.err(where, "empty text")
        return
    if text != text.strip() or "  " in text:
        E.err(where, "stray whitespace in %r" % text)
    for tok in TOKEN_RE.findall(text):
        if tok not in TOKENS:
            E.err(where, "unknown token {%s}" % tok)
    stripped = TOKEN_RE.sub("", text)
    if "{" in stripped or "}" in stripped:
        E.err(where, "unbalanced brace in %r" % text)
    if max_words and words(text) > max_words:
        E.err(where, "%d words (max %d): %r" % (words(text), max_words, text))


def check_marker(where, map_id, marker, used):
    if map_id not in W.MAPS:
        E.err(where, "unknown map %r" % map_id)
        return False
    if marker not in W.MAPS[map_id]["markers"]:
        E.err(where, "unknown marker %r on map %r" % (marker, map_id))
        return False
    used.add((map_id, marker))
    return True


def valid_speaker(s):
    return s in ("player", "narrator") or s in story.NPCS


# ------------------------------------------------------------------ NPC timeline

def npc_window(npc_id, field):
    v = story.NPCS[npc_id].get(field)
    return NB.resolve_id(v) if v else None


def npc_present(npc_id, qnum):
    """True when the NPC stands at home during quest ``qnum``."""
    a, hid = npc_window(npc_id, "appear_from"), npc_window(npc_id, "hidden_after")
    if a and qnum < a:
        return False
    if hid and qnum > hid:
        return False
    return True


def npc_active(npc_id, qnum):
    """True when the character is alive and part of the story at all during quest ``qnum``."""
    a, gone = npc_window(npc_id, "appear_from"), npc_window(npc_id, "gone_after")
    return not ((a and qnum < a) or (gone and qnum > gone))


def present_homes(map_id, qnum):
    """marker -> npc id of NPCs standing at home on ``map_id`` during quest ``qnum``."""
    out = {}
    for nid, n in story.NPCS.items():
        h = n["home"]
        if h and h["map"] == map_id and npc_present(nid, qnum):
            out[h["marker"]] = nid
    return out


# ------------------------------------------------------------------ compile

ALIGN_OPS = re.compile(r"^(>=|<=|>|<|==)(-?\d+)$")
COND_KEYS = {"align", "align_law", "align_good", "min_realm", "max_realm", "min_stage", "max_stage", "flag",
             "not_flag", "likes", "dislikes"}
FLAG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def check_cond(where, cond, flags=None):
    """Validate a condition (all keys must hold):
    align: "lawful_good" / "chaotic_*" / "*_evil" (or a list: any of them);
    align_law / align_good: ">=30", "<=-25", ...; min_realm / max_realm: a realm name;
    min_stage / max_stage: 1-10; flag / not_flag: a flag some earlier choice sets
    (``flags``: the flags set so far, None to forbid flags); likes / dislikes: an NPC id."""
    if not isinstance(cond, dict) or not cond:
        E.err(where, "condition must be a non-empty dict")
        return
    for k, v in cond.items():
        if k not in COND_KEYS:
            E.err(where, "unknown condition %r" % k)
        elif k == "align":
            for pat in (v if isinstance(v, list) else [v]):
                parts = pat.split("_") if isinstance(pat, str) else []
                if len(parts) != 2 or parts[0] not in W.ALIGN_LAW + ["*"] or parts[1] not in W.ALIGN_MORAL + ["*"]:
                    E.err(where, "bad alignment pattern %r" % (pat,))
        elif k in ("align_law", "align_good"):
            m = ALIGN_OPS.match(v) if isinstance(v, str) else None
            if not m or abs(int(m.group(2))) > W.ALIGN_RANGE:
                E.err(where, "%s must look like '>=30' within +-%d, got %r" % (k, W.ALIGN_RANGE, v))
        elif k in ("min_realm", "max_realm"):
            if v not in W.REALMS:
                E.err(where, "unknown realm %r" % v)
        elif k in ("min_stage", "max_stage"):
            if not (isinstance(v, int) and 1 <= v <= 10):
                E.err(where, "%s must be 1-10" % k)
        elif k in ("flag", "not_flag"):
            if flags is None:
                E.err(where, "flags cannot be used here")
            elif v not in flags:
                E.err(where, "flag %r is not set by any earlier choice" % v)
        elif k in ("likes", "dislikes"):
            if v not in story.NPCS:
                E.err(where, "unknown npc %r" % v)


def compile_line(where, key, raw, voices, speakers_used, flags=None):
    """``key`` is the voice key of a line of the original story, None for a text-only line."""
    sp, text = raw["speaker"], raw["text"]
    if not valid_speaker(sp):
        E.err(where, "unknown speaker %r" % sp)
    speakers_used.add(sp)
    check_text(where, text)
    if raw.get("cond") is not None:
        if key is not None:
            E.err(where, "a voiced line cannot be conditional")
        check_cond(where, raw["cond"], flags)
        return {"speaker": sp, "text": text, "voice": None, "cond": raw["cond"]}
    if key is None:
        return {"speaker": sp, "text": text, "voice": None}
    if key in voices:
        E.err(where, "duplicate voice key %s" % key)
    voices.add(key)
    if sp in story.NPCS and story.NPCS[sp].get("voice") is None:
        E.err(where, "voiced line by %s, who has no voice casting" % sp)
    return {"speaker": sp, "text": text, "voice": VOICE_DIR + key + ".ogg",
            "gendered": is_gendered(sp, text)}


def compile_objective(where, qnum, raw, cur_map, voices, used, speakers_used, cin_uses, vkey=None, voi=None,
                      flags=None):
    """``vkey``/``voi``: voice key prefix and original objective index of a voiced quest;
    ``flags``: the flags earlier choices can have set (for conditions)."""
    t = raw.get("type")
    if t not in W.OBJECTIVE_TYPES:
        E.err(where, "unknown objective type %r" % t)
        return None, cur_map
    if t == "cinematic":
        cin = story.CINEMATICS.get(raw["id"])
        if cin is None:
            E.err(where, "unknown cinematic %r" % raw["id"])
            m = cur_map
        else:
            m = cin["map"]
            cin_uses.setdefault(raw["id"], []).append(qid(qnum))
    else:
        m = raw["map"] or cur_map
    if m not in W.MAPS:
        E.err(where, "unknown map %r" % m)
        return None, cur_map
    text = raw["text"]
    check_text(where + " text", text, max_words=0)
    if len(text) > MAX_HUD_CHARS:
        E.err(where, "tracker text longer than %d chars: %r" % (MAX_HUD_CHARS, text))

    o = {"type": t, "map": m}
    if t == "talk":
        npc = raw["npc"]
        at = raw["at"]
        if npc not in story.NPCS:
            E.err(where, "unknown npc %r" % npc)
        else:
            home = story.NPCS[npc]["home"]
            if at is None:
                if not home or home["map"] != m:
                    E.err(where, "talk 'at' is null but %s has no home on map %r" % (npc, m))
                elif not npc_present(npc, qnum):
                    E.err(where, "talk 'at' is null but %s is not present at home during %s" % (npc, qid(qnum)))
                else:
                    used.add((m, home["marker"]))
            else:
                if check_marker(where, m, at, used):
                    other = present_homes(m, qnum).get(at)
                    if other and other != npc:
                        E.err(where, "%s would stand on %s's home marker %s" % (npc, other, at))
        o.update(npc=npc, at=at)
    elif t == "reach":
        check_marker(where, m, raw["marker"], used)
        if not raw["radius"] > 0:
            E.err(where, "radius must be > 0")
        o.update(marker=raw["marker"], radius=raw["radius"])
    elif t == "defeat":
        enemy, count = raw["enemy"], raw["count"]
        if enemy not in W.ENEMIES:
            E.err(where, "unknown enemy %r" % enemy)
        if not (isinstance(count, int) and 1 <= count <= 8):
            E.err(where, "enemy count %r out of range 1-8" % count)
        if enemy in W.BOSSES and count != 1:
            E.err(where, "boss %s must have count 1" % enemy)
        check_marker(where, m, raw["marker"], used)
        o.update(enemy=enemy, count=count, marker=raw["marker"])
        if raw.get("name"):
            if enemy not in W.BOSSES:
                E.err(where, "only bosses take a display name")
            check_text(where + " name", raw["name"], max_words=8)
            if len(raw["name"]) > MAX_BOSS_NAME:
                E.err(where, "boss name longer than %d chars" % MAX_BOSS_NAME)
            o["name"] = raw["name"]
    elif t == "collect":
        item, count = raw["item"], raw["count"]
        if item not in W.ITEMS:
            E.err(where, "unknown item %r" % item)
        if not (isinstance(count, int) and 1 <= count <= 8):
            E.err(where, "item count %r out of range 1-8" % count)
        check_marker(where, m, raw["marker"], used)
        o.update(item=item, count=count, marker=raw["marker"])
    elif t == "meditate":
        check_marker(where, m, raw["marker"], used)
        if not (4 <= raw["seconds"] <= 12):
            E.err(where, "meditate seconds %r out of range 4-12" % raw["seconds"])
        o.update(marker=raw["marker"], seconds=raw["seconds"])
    elif t == "interact":
        if raw["object"] not in W.PROPS:
            E.err(where, "unknown prop %r" % raw["object"])
        check_marker(where, m, raw["marker"], used)
        o.update(object=raw["object"], marker=raw["marker"])
    elif t == "cinematic":
        o.update(id=raw["id"])
    elif t == "tribulation":
        check_marker(where, m, raw["marker"], used)
        bolts = raw["bolts"]
        if not (isinstance(bolts, int) and 3 <= bolts <= 81):
            E.err(where, "tribulation bolts %r out of range 3-81" % bolts)
            bolts = 3
        volleys = min(bolts, 9)
        waves = raw.get("waves") or []
        for wi, wv in enumerate(waves):
            ww = "%s wave %d" % (where, wi)
            if wv["enemy"] not in W.ENEMIES or wv["enemy"] in W.BOSSES:
                E.err(ww, "wave enemy %r must be a non-boss enemy" % wv["enemy"])
            if not (isinstance(wv["count"], int) and 1 <= wv["count"] <= 4):
                E.err(ww, "wave count %r out of range 1-4" % wv["count"])
            if not (isinstance(wv["after"], int) and 1 <= wv["after"] < volleys):
                E.err(ww, "wave must come after volley 1..%d, not %r" % (volleys - 1, wv["after"]))
        if [w["after"] for w in waves] != sorted({w["after"] for w in waves}):
            E.err(where, "waves must come after distinct, increasing volleys")
        o.update(marker=raw["marker"], bolts=bolts,
                 waves=[{"enemy": w["enemy"], "count": w["count"], "after": w["after"]} for w in waves])
    o["text"] = text

    lines = raw.get("dialogue")
    if lines is not None:
        plain = [ln for ln in lines if ln.get("cond") is None]
        lo = 2 if t == "talk" else 1
        if not (lo <= len(plain) <= 7):
            E.err(where, "dialogue needs %d-7 unconditional lines (every conversation must have a path), has %d"
                  % (lo, len(plain)))
        if len(lines) > 10:
            E.err(where, "dialogue has %d lines (max 10 with conditional ones)" % len(lines))
        # voice keys count only the unconditional lines of the objective's original index
        oi = int(where.rsplit("_o", 1)[1]) if voi is None else voi
        out, li = [], 0
        for n, ln in enumerate(lines):
            key = None
            if vkey and ln.get("cond") is None:
                key = "%s_o%d_l%d" % (vkey, oi, li)
                li += 1
            out.append(compile_line("%s_l%d" % (where, n), key, ln, voices, speakers_used, flags))
        o["dialogue"] = out
    elif t == "talk":
        E.err(where, "talk needs dialogue")
    if raw.get("choices") is not None:
        compile_choices(where, t, raw, o, voices, speakers_used, flags)
    return o, m


def compile_choices(where, t, raw, o, voices, speakers_used, flags):
    """A moral choice offered after the objective's dialogue: 2-4 options, each with
    alignment deltas, reply lines, an optional reward, flag, NPC attitudes and condition."""
    if t not in ("talk", "reach", "interact") or not o.get("dialogue"):
        E.err(where, "choices need a talk, reach or interact objective with dialogue")
    prompt = raw.get("choice_prompt")
    check_text(where + " prompt", prompt, max_words=0)
    if isinstance(prompt, str) and len(prompt) > 140:
        E.err(where, "choice prompt longer than 140 chars")
    opts = raw["choices"]
    if not (2 <= len(opts) <= 4):
        E.err(where, "choices need 2-4 options, has %d" % len(opts))
    if not any(op.get("cond") is None for op in opts):
        E.err(where, "at least one option must have no condition (every conversation must have a path)")
    out = []
    for k, op in enumerate(opts):
        w = "%s choice %d" % (where, k)
        check_text(w, op["text"], max_words=14)
        if len(op["text"]) > 64:
            E.err(w, "option text longer than 64 chars")
        a = op["align"]
        if set(a) != {"law", "good"} or not all(isinstance(a[x], int) and -20 <= a[x] <= 20 for x in a):
            E.err(w, "align needs law and good, each -20..20")
        rw = op["reward"]
        if not (isinstance(rw["xp"], int) and 0 <= rw["xp"] <= 500):
            E.err(w, "reward xp must be 0-500")
        for it, n in rw["items"].items():
            if it not in W.ITEMS:
                E.err(w, "unknown reward item %r" % it)
            if not (isinstance(n, int) and 1 <= n <= 5):
                E.err(w, "reward count must be 1-5")
        if op["flag"] is not None and not FLAG_RE.match(op["flag"]):
            E.err(w, "bad flag %r" % op["flag"])
        for nid, d in op["attitude"].items():
            if nid not in story.NPCS or not (isinstance(d, int) and -3 <= d <= 3 and d):
                E.err(w, "attitude %r: %r must be an NPC and -3..3" % (nid, d))
        if op.get("cond") is not None:
            check_cond(w, op["cond"], flags)
        reply = op["reply"]
        if len(reply) > 3:
            E.err(w, "at most 3 reply lines")
        d = {"text": op["text"], "align": {"law": a["law"], "good": a["good"]},
             "reply": [compile_line("%s_r%d" % (w, n), None, ln, voices, speakers_used, flags)
                       for n, ln in enumerate(reply)],
             "reward": {"xp": rw["xp"], "items": dict(sorted(rw["items"].items()))}}
        if op["flag"]:
            d["flag"] = op["flag"]
        if op["attitude"]:
            d["attitude"] = dict(sorted(op["attitude"].items()))
        if op.get("cond") is not None:
            d["cond"] = op["cond"]
        out.append(d)
    o["choice_prompt"] = prompt
    o["choices"] = out


def expected_cultivation(chapter, qi):
    """(realm, stage) the ``qi``-th quest (0-9) of ``chapter`` must grant: chapter c of volume v
    ends at minor stage c of REALMS[v], chapter 1 being the breakthrough into it; the last
    chapter reaches Great Perfection on its ninth quest and Immortal Ascension on its tenth."""
    v = NB.volume_of_chapter(chapter)
    c = chapter - (v - 1) * NB.CHAPTERS_PER_VOLUME
    last = NB.QUESTS_PER_CHAPTER - 1
    if chapter == NB.TOTAL_CHAPTERS:
        return {last - 1: (None, 10), last: (W.REALMS[-1], None)}.get(qi, (None, None))
    if qi != last:
        return None, None
    return (W.REALMS[v] if c == 1 else None), c


def check_generated(wq, qnum, objs):
    """Continuity rules for the generated (non-legacy) quests."""
    for oi, o in enumerate(objs):
        w = "%s_o%d" % (wq, oi)
        who = set()
        if o["type"] == "talk":
            who.add(o["npc"])
        replies = [ln for op in o.get("choices", []) for ln in op["reply"]]
        for ln in o.get("dialogue", []) + replies:
            if ln["speaker"] not in ("player", "narrator"):
                who.add(ln["speaker"])
        for nid in sorted(who):
            if nid in story.NPCS and not npc_active(nid, qnum):
                E.err(w, "%s is not in the story during %s (appear_from %s, gone_after %s)"
                      % (nid, wq, story.NPCS[nid]["appear_from"], story.NPCS[nid].get("gone_after")))
        if o["map"] == "sky_isles" and qnum < NB.legacy_to_new(71):
            E.err(w, "the Sky Isles have not opened yet")
        if o["map"] == "blood_abyss" and qnum < NB.legacy_to_new(51):
            E.err(w, "the Blood Moon Abyss is not reachable yet")
        mk = o.get("marker") or o.get("at")
        if o["map"] == "blood_abyss" and mk in FORTRESS and NB.legacy_to_new(90) < qnum:
            E.err(w, "%s is folded into the void until the final march" % mk)


def compile_cinematic(cid, raw, voices, used, speakers_used):
    where = "cinematic %s" % cid
    m = raw["map"]
    if m not in W.MAPS:
        E.err(where, "unknown map %r" % m)
        return None
    for k in ("title", "subtitle"):
        if raw[k] is not None:
            check_text(where + " " + k, raw[k], max_words=8)
    if raw["music"] is not None:
        music_dir = os.path.join(ROOT, "godot", "audio", "music")
        known = {v["music"] for v in W.MAPS.values()}
        if os.path.isdir(music_dir):
            known |= {os.path.splitext(f)[0] for f in os.listdir(music_dir) if f.endswith(".ogg")}
        if os.path.isdir(music_dir) and raw["music"] not in known:
            E.err(where, "unknown music id %r (known: %s)" % (raw["music"], ", ".join(sorted(known))))
    actors = []
    for i, a in enumerate(raw["actors"]):
        w = "%s actor %d" % (where, i)
        if a["npc"] != "player" and a["npc"] not in story.NPCS:
            E.err(w, "unknown npc %r" % a["npc"])
        check_marker(w, m, a["marker"], used)
        if a["anim"] not in ANIMS:
            E.err(w, "unknown anim %r" % a["anim"])
        if a["face"] is not None:
            check_marker(w, m, a["face"], used)
        actors.append({"npc": a["npc"], "marker": a["marker"], "anim": a["anim"], "face": a["face"]})
    seen = [a["npc"] for a in actors]
    if len(seen) != len(set(seen)):
        E.err(where, "an actor appears twice")
    spots = [a["marker"] for a in actors]
    if len(spots) != len(set(spots)):
        E.err(where, "two actors share a marker: %s" % ", ".join(sorted({m for m in spots if spots.count(m) > 1})))
    enemies = []
    for i, e in enumerate(raw["enemies"]):
        w = "%s enemy %d" % (where, i)
        if e["enemy"] not in W.ENEMIES:
            E.err(w, "unknown enemy %r" % e["enemy"])
        check_marker(w, m, e["marker"], used)
        if not (1 <= e["count"] <= 8):
            E.err(w, "count out of range")
        enemies.append({"enemy": e["enemy"], "marker": e["marker"], "count": e["count"]})
    shots = raw["shots"]
    if not (3 <= len(shots) <= 8):
        E.err(where, "needs 3-8 shots, has %d" % len(shots))
    out_shots = []
    for i, s in enumerate(shots):
        w = "%s shot %d" % (where, i)
        check_marker(w, m, s["marker"], used)
        for k in ("from", "to"):
            c = s[k]
            if not (0.5 <= c["distance"] <= 80 and -5 <= c["height"] <= 60 and -360 <= c["yaw"] <= 360):
                E.err(w, "camera %s out of range: %r" % (k, c))
        text = s["text"]
        key = "cin_%s_s%d" % (cid, i)
        if text:
            if not valid_speaker(s["speaker"]):
                E.err(w, "unknown speaker %r" % s["speaker"])
            speakers_used.add(s["speaker"])
            check_text(w, text)
            if key in voices:
                E.err(w, "duplicate voice key %s" % key)
            voices.add(key)
            dur = max(s["duration"] or 0.0, est_duration(text))
            voice, gendered = VOICE_DIR + key + ".ogg", is_gendered(s["speaker"], text)
        else:
            dur, voice, gendered = s["duration"] or 3.0, None, False
        out_shots.append({"marker": s["marker"], "from": s["from"], "to": s["to"],
                          "look_height": s["look_height"], "duration": round(float(dur), 1),
                          "speaker": s["speaker"] if text else None, "text": text or None,
                          "voice": voice, "gendered": gendered})
    return {"map": m, "title": raw["title"], "subtitle": raw["subtitle"], "music": raw["music"],
            "actors": actors, "enemies": enemies, "shots": out_shots}


def compile_npcs(used):
    out = {}
    homes = {}
    for nid, n in story.NPCS.items():
        where = "npc %s" % nid
        if not re.match(r"^[a-z][a-z0-9_]*$", nid):
            E.err(where, "bad id")
        if n["model"] not in W.NPC_MODELS:
            E.err(where, "model %r is not in NPC_MODELS" % n["model"])
        if n["tint"] is not None:
            if len(n["tint"]) != 3 or not all(0 <= c <= 1.5 for c in n["tint"]):
                E.err(where, "tint must be 3 values in 0..1.5")
        if not (0.85 <= n["scale"] <= 1.2):
            E.err(where, "scale %r out of range" % n["scale"])
        if n["home"]:
            h = n["home"]
            if check_marker(where, h["map"], h["marker"], used):
                if h["marker"] in ("PlayerSpawn", "TeleportArray"):
                    E.err(where, "home on %s would block arrivals" % h["marker"])
                k = (h["map"], h["marker"])
                if k in homes:
                    other = homes[k]
                    # two NPCs may share a home only if their presence windows never overlap
                    if not all(not (npc_present(nid, q) and npc_present(other, q))
                               for q in range(1, NB.TOTAL_QUESTS + 1)):
                        E.err(where, "home %s/%s already used by %s" % (k + (other,)))
                homes[k] = nid
        window = {}
        for k in ("appear_from", "hidden_after", "gone_after"):
            v = n.get(k)
            if v is not None:
                window[k] = NB.resolve_id(v)
                if window[k] is None:
                    E.err(where, "%s %r is not a quest id (q001..q100 legacy or q0001..q1000)" % (k, v))
        if window.get("appear_from") and window.get("hidden_after") and window["appear_from"] > window["hidden_after"]:
            E.err(where, "appear_from is after hidden_after")
        if window.get("appear_from") and window.get("gone_after") and window["appear_from"] > window["gone_after"]:
            E.err(where, "appear_from is after gone_after")
        if not (2 <= len(n["barks"]) <= 4):
            E.err(where, "needs 2-4 barks")
        for b in n["barks"]:
            check_text(where + " bark", b)
            if TOKEN_RE.search(b):
                E.err(where, "barks are unvoiced and must not use tokens")
        greetings = []
        for g in MO.bark_greetings(nid):
            check_text(where + " greeting", g["text"])
            check_cond(where + " greeting", g["cond"])
            greetings.append({"text": g["text"], "cond": g["cond"]})
        v = n["voice"]
        if v is not None and not os.path.basename(v["model"]) == v["model"]:
            E.err(where, "voice model must be a bare model name")
        ids = {k: (qid(window[k]) if window.get(k) else None) for k in ("appear_from", "hidden_after", "gone_after")}
        out[nid] = {"name": n["name"], "title": n["title"], "model": n["model"], "tint": n["tint"],
                    "scale": n["scale"], "home": n["home"], "appear_from": ids["appear_from"],
                    "hidden_after": ids["hidden_after"], "gone_after": ids["gone_after"], "barks": n["barks"],
                    "greetings": greetings,
                    "voice": None if v is None else {"model": v["model"], "speaker": v["speaker"],
                                                     "length_scale": v["length_scale"], "noise_scale": v["noise_scale"]}}
    return out


def check_threads():
    """Validate tools/story/threads.py: known quest ids, strictly increasing per
    thread (a recap must follow the events it recaps), each thread with 3+ beats."""
    seen_ids = set()
    for t in TH.THREADS:
        where = "thread %s" % t["id"]
        if t["id"] in seen_ids:
            E.err(where, "duplicate thread id")
        seen_ids.add(t["id"])
        check_text(where + " title", t["title"], max_words=8)
        if len(t["beats"]) < 3:
            E.err(where, "needs at least 3 beats, has %d" % len(t["beats"]))
        last = 0
        for n, text in t["beats"]:
            wb = "%s beat %s" % (where, qid(n))
            check_text(wb, text, max_words=40)
            if not (1 <= n <= NB.TOTAL_QUESTS):
                E.err(wb, "quest number %r out of range 1-%d" % (n, NB.TOTAL_QUESTS))
            elif n <= last:
                E.err(wb, "beats must land on strictly increasing quests (last was %s)" % qid(last))
            last = n


def build():
    used = set()
    voices = set()
    speakers_used = set()
    cin_uses = {}

    check_threads()
    npcs = compile_npcs(used)
    cinematics = {}
    for cid, raw in story.CINEMATICS.items():
        if not re.match(r"^[a-z0-9_]+$", cid):
            E.err("cinematic %s" % cid, "bad id")
        c = compile_cinematic(cid, raw, voices, used, speakers_used)
        if c:
            cinematics[cid] = c

    volumes, chapters, quests = [], [], []
    if len(story.VOLUMES) != NB.VOLUMES:
        E.err("story", "needs exactly %d volumes, has %d" % (NB.VOLUMES, len(story.VOLUMES)))
    realm_idx, stage = 0, 0
    last_end = (0, 0)
    last_bolts = 0
    flags_set = set()
    qnum = cnum = 0
    titles = {}
    for vi, vol in enumerate(story.VOLUMES, 1):
        wv = "volume %d" % vi
        if vol["title"] != W.REALMS[vi]:
            E.err(wv, "title %r should be the realm %r" % (vol["title"], W.REALMS[vi]))
        check_text(wv + " subtitle", vol["subtitle"], max_words=8)
        check_text(wv + " summary", vol["summary"], max_words=0)
        if len(vol["chapters"]) != NB.CHAPTERS_PER_VOLUME:
            E.err(wv, "needs exactly %d chapters, has %d" % (NB.CHAPTERS_PER_VOLUME, len(vol["chapters"])))
        vol_first = qnum
        vol_realm = None
        for ch in vol["chapters"]:
            cnum += 1
            ci = cnum
            where = "chapter %d" % ci
            legacy_ch = ch.get("legacy")
            if ch["number"] != ci:
                E.err(where, "number is %r" % ch["number"])
            if ch["map"] not in W.MAPS:
                E.err(where, "unknown map %r" % ch["map"])
            intro = None
            if ch["intro_cinematic"] is not None:
                intro = cinematics.get(ch["intro_cinematic"])
                if intro is None:
                    E.err(where, "intro cinematic %r does not exist" % ch["intro_cinematic"])
                elif intro["map"] != ch["map"]:
                    E.err(where, "intro cinematic is on %r, chapter map is %r" % (intro["map"], ch["map"]))
            elif legacy_ch:
                E.err(where, "a chapter of the original story lost its intro cinematic")
            check_text(where + " title", ch["title"], max_words=8)
            check_text(where + " summary", ch["summary"], max_words=0)
            chapters.append({"number": ci, "volume": vi, "title": ch["title"], "summary": ch["summary"],
                             "intro_cinematic": ch["intro_cinematic"], "map": ch["map"],
                             "first": qnum, "legacy": legacy_ch})
            if len(ch["quests"]) != NB.QUESTS_PER_CHAPTER:
                E.err(where, "needs exactly %d quests, has %d" % (NB.QUESTS_PER_CHAPTER, len(ch["quests"])))
            bosses_in_chapter = 0
            for qi, q in enumerate(ch["quests"]):
                qnum += 1
                wq = qid(qnum)
                legacy = q.get("legacy")
                flags_new = set()
                if legacy_ch:
                    n_lead = NB.LEGACY_LEAD_QUESTS[legacy_ch]
                    n_tail = NB.LEGACY_TAIL_QUESTS[legacy_ch]
                    tail_start = NB.LEGACY_QUESTS_PER_CHAPTER - n_tail
                    if qi < n_lead:
                        expected = (legacy_ch - 1) * 10 + qi + 1
                    elif qi < NB.QUESTS_PER_CHAPTER - n_tail:
                        expected = None
                    else:
                        pos_in_tail = qi - (NB.QUESTS_PER_CHAPTER - n_tail)
                        expected = (legacy_ch - 1) * 10 + tail_start + pos_in_tail + 1
                    if legacy != expected:
                        E.err(wq, "legacy quest number %r out of place" % legacy)
                if legacy and NB.legacy_to_new(legacy) != qnum:
                    E.err(wq, "legacy q%03d should be %s" % (legacy, qid(NB.legacy_to_new(legacy))))
                vkey = ("q%03d" % legacy) if legacy else None
                check_text(wq + " title", q["title"], max_words=8)
                if q["title"] in titles:
                    E.err(wq, "title %r already used by %s" % (q["title"], titles[q["title"]]))
                titles[q["title"]] = wq
                check_text(wq + " summary", q["summary"], max_words=0)
                if len(q["summary"]) > MAX_SUMMARY_CHARS:
                    E.err(wq, "summary longer than %d chars" % MAX_SUMMARY_CHARS)
                objs = q["objectives"]
                if not (2 <= len(objs) <= 6):
                    E.err(wq, "needs 2-6 objectives, has %d" % len(objs))
                cur = q["map"]
                out_objs = []
                voi = 0
                for oi, raw in enumerate(objs):
                    added = bool(raw.get("added"))
                    if added and not legacy:
                        E.err("%s_o%d" % (wq, oi), "only objectives added to a voiced quest are marked 'added'")
                    o, cur = compile_objective("%s_o%d" % (wq, oi), qnum, raw, cur, voices, used, speakers_used,
                                               cin_uses, vkey=None if added else vkey, voi=voi, flags=flags_set)
                    if not added:
                        voi += 1
                    if o:
                        out_objs.append(o)
                for o in out_objs:
                    for op in o.get("choices", []):
                        if op.get("flag"):
                            flags_new.add(op["flag"])
                if out_objs and out_objs[0]["map"] != q["map"]:
                    E.err(wq, "quest map %r differs from first objective map %r" % (q["map"], out_objs[0]["map"]))
                # talk NPCs must not stand where this quest's enemies spawn
                fights = {(o["map"], o["marker"]) for o in out_objs
                          if o["type"] == "defeat" or (o["type"] == "tribulation" and o["waves"])}
                for oi, o in enumerate(out_objs):
                    if o["type"] == "talk":
                        home = story.NPCS.get(o["npc"], {}).get("home")
                        mk = o["at"] or (home["marker"] if home else None)
                        if (o["map"], mk) in fights:
                            E.err("%s_o%d" % (wq, oi), "%s talks at %s where this quest spawns enemies" % (o["npc"], mk))
                    if o["type"] == "defeat" and o["enemy"] in W.BOSSES:
                        bosses_in_chapter += 1
                # every quest needs a choice, with one narrow exception: legacy
                # quest 99 ("Heavenly Tribulation") is cinematic/defeat/meditate
                # only, so it has no talk/reach/interact objective to hang one on
                # without adding new voiced dialogue to an already-recorded
                # legacy chapter -- which this repo can't (re-)synthesise without
                # the original voice cast. The finale's earlier and later quests
                # (98 and 100) both still offer choices.
                if not any(o.get("choices") for o in out_objs) and qnum != NB.legacy_to_new(99):
                    E.err(wq, "quest offers the player no choice (every quest must have one)")
                if not legacy:
                    check_generated(wq, qnum, out_objs)
                if qi == 0 and intro is not None and not any(
                        o["type"] == "cinematic" and o.get("id") == ch["intro_cinematic"] for o in out_objs):
                    E.err(wq, "chapter's opening quest must play the intro cinematic %s" % ch["intro_cinematic"])
                r = q["rewards"]
                if not (isinstance(r["xp"], int) and r["xp"] > 0):
                    E.err(wq, "xp must be a positive int")
                for it, n in r["items"].items():
                    if it not in W.ITEMS:
                        E.err(wq, "unknown reward item %r" % it)
                    if not (isinstance(n, int) and n > 0):
                        E.err(wq, "reward count must be a positive int")
                tier = realm_idx
                st = r.get("stage")
                want = expected_cultivation(ci, qi)
                if (r["realm"], st) != want:
                    E.err(wq, "grants realm %r stage %r; the stage schedule says realm %r stage %r"
                          % ((r["realm"], st) + want))
                if r["realm"] is not None:
                    if r["realm"] not in W.REALMS:
                        E.err(wq, "unknown realm %r" % r["realm"])
                    else:
                        idx = W.REALMS.index(r["realm"])
                        if idx <= realm_idx:
                            E.err(wq, "realm %r does not advance (current %r)" % (r["realm"], W.REALMS[realm_idx]))
                        realm_idx = idx
                        stage = st or 0
                        if idx < len(W.REALMS) - 1 and st != 1:
                            E.err(wq, "a breakthrough starts the realm at minor stage 1")
                        if idx == len(W.REALMS) - 1:
                            pass  # Immortal Ascension crowns the last volume
                        elif vol_realm is not None:
                            E.err(wq, "volume %d grants a second realm" % vi)
                        else:
                            vol_realm = (qnum, idx)
                elif st is not None:
                    if not (isinstance(st, int) and 1 <= st < len(W.STAGES)):
                        E.err(wq, "stage %r out of range 1-%d" % (st, len(W.STAGES) - 1))
                    elif realm_idx in (0, len(W.REALMS) - 1):
                        E.err(wq, "%s has no minor stages" % W.REALMS[realm_idx])
                    elif st <= stage:
                        E.err(wq, "stage %s does not advance within %s (current %s)"
                              % (W.STAGES[st], W.REALMS[realm_idx], W.STAGES[stage]))
                    else:
                        stage = st
                if qi == NB.QUESTS_PER_CHAPTER - 1:
                    # (realm, stage) strictly increases from one chapter's end to the next
                    if (realm_idx, stage) <= last_end:
                        E.err(wq, "chapter %d ends at %r, not beyond chapter %d's %r" % (ci, (realm_idx, stage),
                                                                                           ci - 1, last_end))
                    last_end = (realm_idx, stage)
                # a major breakthrough (and the final Great Perfection) is earned by surviving a tribulation
                tribs = [o for o in out_objs if o["type"] == "tribulation"]
                needs = (r["realm"] is not None and r["realm"] != W.REALMS[-1]) or (st == 10 and ci == NB.TOTAL_CHAPTERS)
                if needs and len(tribs) != 1:
                    E.err(wq, "a breakthrough quest needs exactly one tribulation objective, has %d" % len(tribs))
                if not needs and tribs:
                    E.err(wq, "tribulations belong to breakthrough quests")
                for o in tribs:
                    if o["bolts"] < last_bolts:
                        E.err(wq, "tribulation of %d bolts is weaker than the last one (%d)" % (o["bolts"], last_bolts))
                    last_bolts = o["bolts"]
                bonus = []
                for bi, bn in enumerate(r.get("bonus") or []):
                    wb = "%s bonus %d" % (wq, bi)
                    check_cond(wb, bn["cond"], flags_set)
                    check_text(wb + " note", bn["note"], max_words=16)
                    if not (isinstance(bn["xp"], int) and 0 <= bn["xp"] <= 500):
                        E.err(wb, "xp must be 0-500")
                    for it, n in bn["items"].items():
                        if it not in W.ITEMS or not (isinstance(n, int) and 1 <= n <= 5):
                            E.err(wb, "bad item reward %r x %r" % (it, n))
                    bonus.append({"cond": bn["cond"], "xp": bn["xp"], "items": dict(sorted(bn["items"].items())),
                                  "note": bn["note"]})
                rewards = {"xp": r["xp"], "items": dict(sorted(r["items"].items())), "realm": r["realm"], "stage": st}
                if bonus:
                    rewards["bonus"] = bonus
                quests.append({"id": wq, "volume": vi, "chapter": ci, "number": qnum, "legacy": legacy,
                               "title": q["title"], "summary": q["summary"], "map": q["map"], "tier": tier,
                               "objectives": out_objs, "rewards": rewards})
                flags_set |= flags_new
            if not legacy_ch and bosses_in_chapter > 1:
                E.err(where, "%d boss fights (max one, at the chapter's climax)" % bosses_in_chapter)
        # volume v breaks through into REALMS[v] at the end of its first chapter
        expect = vol_first + NB.QUESTS_PER_CHAPTER
        if vol_realm != (expect, vi):
            E.err(wv, "must grant %s at %s (got %r)" % (W.REALMS[vi], qid(expect), vol_realm))
        volumes.append({"number": vi, "title": vol["title"], "subtitle": vol["subtitle"], "summary": vol["summary"],
                        "first": vol_first, "chapters": [c["number"] for c in chapters[-NB.CHAPTERS_PER_VOLUME:]]})
    if qnum != NB.TOTAL_QUESTS:
        E.err("story", "needs exactly %d quests, has %d" % (NB.TOTAL_QUESTS, qnum))
    if cnum != NB.TOTAL_CHAPTERS:
        E.err("story", "needs exactly %d chapters, has %d" % (NB.TOTAL_CHAPTERS, cnum))
    if quests and quests[-1]["rewards"]["realm"] != W.REALMS[-1]:
        E.err(qid(NB.TOTAL_QUESTS), "the final quest must grant %s" % W.REALMS[-1])

    for cid in cinematics:
        if cid not in cin_uses:
            E.warn("cinematic %s" % cid, "never played by any quest")
        elif len(cin_uses[cid]) > 1:
            E.warn("cinematic %s" % cid, "played by several quests: %s" % ", ".join(cin_uses[cid]))
    for nid in story.NPCS:
        if nid not in speakers_used:
            E.warn("npc %s" % nid, "never speaks")
    for m, spec in W.MAPS.items():
        unused = [k for k in spec["markers"] if (m, k) not in used]
        if unused:
            E.warn("map %s" % m, "markers never used: %s" % ", ".join(unused))

    return {"version": 2, "title": story.TITLE, "premise": story.PREMISE, "volumes": volumes, "chapters": chapters,
            "npcs": npcs, "quests": quests, "cinematics": cinematics, "threads": TH.compiled()}


# ------------------------------------------------------------------ output

def dumps(obj, indent=0, width=110):
    """Pretty but compact JSON: containers that fit in ``width`` stay on one line."""
    flat = json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
    if len(flat) + indent <= width or not isinstance(obj, (dict, list)) or not obj:
        return flat
    pad = " " * (indent + 1)
    if isinstance(obj, dict):
        items = ["%s%s: %s" % (pad, json.dumps(k, ensure_ascii=False), dumps(v, indent + 1, width).lstrip())
                 for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"
    items = [pad + dumps(v, indent + 1, width).lstrip() for v in obj]
    return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"


def iter_lines(data, voiced=True):
    for q in data["quests"]:
        for o in q["objectives"]:
            for ln in o.get("dialogue", []):
                if bool(ln.get("voice")) == voiced:
                    yield ln
    if voiced:
        for c in data["cinematics"].values():
            for s in c["shots"]:
                if s["text"]:
                    yield s


def stats(data):
    from collections import Counter
    objs = [o for q in data["quests"] for o in q["objectives"]]
    by_type = Counter(o["type"] for o in objs)
    lines = list(iter_lines(data))
    gendered = sum(1 for ln in lines if ln["gendered"])
    n_words = sum(words(ln["text"]) for ln in lines)
    text_only = list(iter_lines(data, voiced=False))
    maps = Counter(o["map"] for o in objs)
    bosses = sum(1 for o in objs if o["type"] == "defeat" and o["enemy"] in W.BOSSES)
    out = []
    out.append("story.json: %d volumes, %d chapters, %d quests, %d objectives, %d cinematics, %d npcs"
               % (len(data["volumes"]), len(data["chapters"]), len(data["quests"]), len(objs),
                  len(data["cinematics"]), len(data["npcs"])))
    out.append("objectives by type: " + ", ".join("%s %d (%.0f%%)" % (t, by_type[t], 100.0 * by_type[t] / len(objs))
                                                   for t in W.OBJECTIVE_TYPES))
    out.append("objectives by map: " + ", ".join("%s %d" % (m, maps[m]) for m in W.MAPS))
    out.append("boss fights: %d" % bosses)
    out.append("voiced lines: %d (%d gendered) -> %d voice files; %d words"
               % (len(lines), gendered, len(lines) + gendered, n_words))
    out.append("text-only lines: %d; %d words" % (len(text_only), sum(words(ln["text"]) for ln in text_only)))
    out.append("unique quest titles: %d / %d; unique objective texts: %d / %d"
               % (len({q["title"] for q in data["quests"]}), len(data["quests"]),
                  len({o["text"] for o in objs}), len(objs)))
    out.append("breakthroughs: " + ", ".join("%s %s" % (q["id"], q["rewards"]["realm"])
                                              for q in data["quests"] if q["rewards"]["realm"]))
    out.append("minor stages granted: %d" % sum(1 for q in data["quests"] if q["rewards"].get("stage")))
    tribs = [o for o in objs if o["type"] == "tribulation"]
    out.append("tribulations: %d (%s bolts)" % (len(tribs), "/".join(str(o["bolts"]) for o in tribs)))
    choices = [o for o in objs if o.get("choices")]
    per_ch = Counter(q["chapter"] for q in data["quests"] for o in q["objectives"] if o.get("choices"))
    out.append("moral choices: %d (%d options, %d with flags), in %d of %d chapters"
               % (len(choices), sum(len(o["choices"]) for o in choices),
                  sum(1 for o in choices for op in o["choices"] if op.get("flag")), len(per_ch), len(data["chapters"])))
    cond = [ln for o in objs for ln in o.get("dialogue", []) if ln.get("cond")]
    out.append("conditional lines: %d; npc greetings: %d; alignment bonuses: %d"
               % (len(cond), sum(len(n["greetings"]) for n in data["npcs"].values()),
                  sum(len(q["rewards"].get("bonus", [])) for q in data["quests"])))
    return "\n".join(out)


def quest_table(data):
    """docs/QUESTS.md: every volume, chapter and quest."""
    realms = W.REALMS
    ch_by = {c["number"]: c for c in data["chapters"]}
    out = ["# All 1000 quests", "",
           "Generated by `python3 tools/build_story.py --quests docs/QUESTS.md`. Chapters marked *voiced* are the ten",
           "chapters of the original story; the rest are text-only. The plot is in [STORY.md](STORY.md).", ""]
    for v in data["volumes"]:
        out.append("## Volume %d · %s — *%s*" % (v["number"], v["title"], v["subtitle"]))
        out.append("")
        out.append(v["summary"])
        out.append("")
        for cn in v["chapters"]:
            c = ch_by[cn]
            out.append("### Chapter %d · %s%s" % (cn, c["title"], "  *(voiced)*" if c["legacy"] else ""))
            out.append("")
            out.append(c["summary"])
            out.append("")
            out.append("| # | Quest | Map | Objectives | Reward |")
            out.append("|---|---|---|---|---|")
            for q in data["quests"][c["first"]:c["first"] + 10]:
                boss = any(o["type"] == "defeat" and o["enemy"] in W.BOSSES for o in q["objectives"])
                r = q["rewards"]
                rew = "%d xp" % r["xp"]
                if r["realm"]:
                    rew += " · **%s**" % r["realm"]
                if r.get("stage") and not r["realm"]:
                    rew += " · *%s · %s*" % (realms[q["tier"]], W.STAGES[r["stage"]])
                objs = " → ".join(o["text"].replace("{player}", "Lin Feng/Su Yue").replace("|", "/")
                                  for o in q["objectives"])
                out.append("| %d | %s%s | %s | %s | %s |" % (q["number"], q["title"], " *(boss)*" if boss else "",
                                                             W.MAPS[q["map"]]["name"], objs, rew))
            out.append("")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if godot/data/story.json is stale")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--quests", default=None, help="also write a Markdown table of every quest to this path")
    args = ap.parse_args()

    data = build()
    for w in E.warnings:
        print("warning: " + w, file=sys.stderr)
    if E.errors:
        for e in E.errors[:200]:
            print("error: " + e, file=sys.stderr)
        print("build_story: %d error(s)" % len(E.errors), file=sys.stderr)
        return 1
    text = dumps(data) + "\n"
    if args.check:
        try:
            with open(args.out, encoding="utf-8") as f:
                current = f.read()
        except FileNotFoundError:
            current = None
        if current != text:
            print("build_story: %s is out of date; run python3 tools/build_story.py"
                  % os.path.relpath(args.out, ROOT), file=sys.stderr)
            return 1
        if not args.quiet:
            print("build_story: %s is up to date (%d quests)" % (os.path.relpath(args.out, ROOT), len(data["quests"])))
        return 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if args.quests:
        with open(args.quests, "w", encoding="utf-8", newline="\n") as f:
            f.write(quest_table(data))
    if not args.quiet:
        print(stats(data))
        print("wrote %s (%d bytes)" % (os.path.relpath(args.out, ROOT), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

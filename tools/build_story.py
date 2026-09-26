#!/usr/bin/env python3
"""Compile the main story (tools/story) into godot/data/story.json and validate it.

    python3 tools/build_story.py            # validate, write story.json, print stats
    python3 tools/build_story.py --check    # validate; exit 1 if story.json is out of date
    python3 tools/build_story.py --quiet    # no stats

Pure Python 3 standard library. Every map, marker, NPC model, enemy, item,
prop and realm is checked against tools/world_spec.py; any error exits 1.
"""

import argparse
import json
import math
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import world_spec as W  # noqa: E402
import story  # noqa: E402

OUT = os.path.join(ROOT, "godot", "data", "story.json")
VOICE_DIR = "res://audio/voice/"
TOKENS = ["player", "junior", "senior", "sibling", "they", "them", "their"]
TOKEN_RE = re.compile(r"\{([^{}]*)\}")
ANIMS = {"idle", "salute", "cast", "talk", "meditate", "attack"}
MAX_LINE_WORDS = 32
MAX_HUD_CHARS = 64
MAX_SUMMARY_CHARS = 240


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
    return "q%03d" % n


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


# ------------------------------------------------------------------ compile

def compile_line(where, key, raw, voices, speakers_used):
    sp, text = raw["speaker"], raw["text"]
    if not valid_speaker(sp):
        E.err(where, "unknown speaker %r" % sp)
    speakers_used.add(sp)
    check_text(where, text)
    if key in voices:
        E.err(where, "duplicate voice key %s" % key)
    voices.add(key)
    return {"speaker": sp, "text": text, "voice": VOICE_DIR + key + ".ogg",
            "gendered": is_gendered(sp, text)}


def npc_present(npc_id, qnum):
    n = story.NPCS[npc_id]
    if n["appear_from"] and qnum < int(n["appear_from"][1:]):
        return False
    if n["hidden_after"] and qnum > int(n["hidden_after"][1:]):
        return False
    return True


def present_homes(map_id, qnum):
    """marker -> npc id of NPCs standing at home on ``map_id`` during quest ``qnum``."""
    out = {}
    for nid, n in story.NPCS.items():
        h = n["home"]
        if h and h["map"] == map_id and npc_present(nid, qnum):
            out[h["marker"]] = nid
    return out


def compile_objective(where, qnum, raw, cur_map, voices, used, speakers_used, cin_uses):
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
    o["text"] = text

    lines = raw.get("dialogue")
    if t == "talk":
        if not lines or not (2 <= len(lines) <= 7):
            E.err(where, "talk needs 2-7 dialogue lines, has %d" % len(lines or []))
    elif lines is not None and not (1 <= len(lines) <= 7):
        E.err(where, "dialogue needs 1-7 lines")
    if lines is not None:
        oi = int(where.rsplit("_o", 1)[1])
        o["dialogue"] = [compile_line("%s_l%d" % (where, li), "%s_o%d_l%d" % (qid(qnum), oi, li),
                                      ln, voices, speakers_used)
                         for li, ln in enumerate(lines)]
    return o, m


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
                    E.err(where, "home %s/%s already used by %s" % (k + (homes[k],)))
                homes[k] = nid
        for k in ("appear_from", "hidden_after"):
            v = n[k]
            if v is not None and not (re.match(r"^q\d{3}$", v) and 1 <= int(v[1:]) <= 100):
                E.err(where, "%s %r is not a quest id" % (k, v))
        if n["appear_from"] and n["hidden_after"] and n["appear_from"] > n["hidden_after"]:
            E.err(where, "appear_from is after hidden_after")
        if not (2 <= len(n["barks"]) <= 4):
            E.err(where, "needs 2-4 barks")
        for b in n["barks"]:
            check_text(where + " bark", b)
            if TOKEN_RE.search(b):
                E.err(where, "barks are unvoiced and must not use tokens")
        v = n["voice"]
        if not os.path.basename(v["model"]) == v["model"]:
            E.err(where, "voice model must be a bare model name")
        out[nid] = {"name": n["name"], "title": n["title"], "model": n["model"], "tint": n["tint"],
                    "scale": n["scale"], "home": n["home"], "appear_from": n["appear_from"],
                    "hidden_after": n["hidden_after"], "barks": n["barks"],
                    "voice": {"model": v["model"], "speaker": v["speaker"],
                              "length_scale": v["length_scale"], "noise_scale": v["noise_scale"]}}
    return out


def build():
    used = set()
    voices = set()
    speakers_used = set()
    cin_uses = {}

    npcs = compile_npcs(used)
    cinematics = {}
    for cid, raw in story.CINEMATICS.items():
        if not re.match(r"^[a-z0-9_]+$", cid):
            E.err("cinematic %s" % cid, "bad id")
        c = compile_cinematic(cid, raw, voices, used, speakers_used)
        if c:
            cinematics[cid] = c

    chapters, quests = [], []
    if len(story.CHAPTERS) != 10:
        E.err("story", "needs exactly 10 chapters, has %d" % len(story.CHAPTERS))
    realm_idx = 0
    qnum = 0
    for ci, ch in enumerate(story.CHAPTERS, 1):
        where = "chapter %d" % ci
        if ch["number"] != ci:
            E.err(where, "number is %r" % ch["number"])
        if ch["map"] not in W.MAPS:
            E.err(where, "unknown map %r" % ch["map"])
        intro = cinematics.get(ch["intro_cinematic"])
        if intro is None:
            E.err(where, "intro cinematic %r does not exist" % ch["intro_cinematic"])
        elif intro["map"] != ch["map"]:
            E.err(where, "intro cinematic is on %r, chapter map is %r" % (intro["map"], ch["map"]))
        check_text(where + " title", ch["title"], max_words=8)
        check_text(where + " summary", ch["summary"], max_words=0)
        chapters.append({"number": ci, "title": ch["title"], "summary": ch["summary"],
                         "intro_cinematic": ch["intro_cinematic"], "map": ch["map"]})
        if len(ch["quests"]) != 10:
            E.err(where, "needs exactly 10 quests, has %d" % len(ch["quests"]))
        for qi, q in enumerate(ch["quests"]):
            qnum += 1
            wq = qid(qnum)
            check_text(wq + " title", q["title"], max_words=8)
            check_text(wq + " summary", q["summary"], max_words=0)
            if len(q["summary"]) > MAX_SUMMARY_CHARS:
                E.err(wq, "summary longer than %d chars" % MAX_SUMMARY_CHARS)
            objs = q["objectives"]
            if not (2 <= len(objs) <= 6):
                E.err(wq, "needs 2-6 objectives, has %d" % len(objs))
            cur = q["map"]
            out_objs = []
            for oi, raw in enumerate(objs):
                o, cur = compile_objective("%s_o%d" % (wq, oi), qnum, raw, cur, voices, used, speakers_used, cin_uses)
                if o:
                    out_objs.append(o)
            if out_objs and out_objs[0]["map"] != q["map"]:
                E.err(wq, "quest map %r differs from first objective map %r" % (q["map"], out_objs[0]["map"]))
            # talk NPCs must not stand where this quest's enemies spawn
            fights = {(o["map"], o["marker"]) for o in out_objs if o["type"] == "defeat"}
            for oi, o in enumerate(out_objs):
                if o["type"] == "talk":
                    home = story.NPCS.get(o["npc"], {}).get("home")
                    mk = o["at"] or (home["marker"] if home else None)
                    if (o["map"], mk) in fights:
                        E.err("%s_o%d" % (wq, oi), "%s talks at %s where this quest spawns enemies" % (o["npc"], mk))
            if qi == 0 and not any(o["type"] == "cinematic" and o.get("id") == ch["intro_cinematic"] for o in out_objs):
                E.err(wq, "chapter's opening quest must play the intro cinematic %s" % ch["intro_cinematic"])
            r = q["rewards"]
            if not (isinstance(r["xp"], int) and r["xp"] > 0):
                E.err(wq, "xp must be a positive int")
            for it, n in r["items"].items():
                if it not in W.ITEMS:
                    E.err(wq, "unknown reward item %r" % it)
                if not (isinstance(n, int) and n > 0):
                    E.err(wq, "reward count must be a positive int")
            if r["realm"] is not None:
                if r["realm"] not in W.REALMS:
                    E.err(wq, "unknown realm %r" % r["realm"])
                else:
                    idx = W.REALMS.index(r["realm"])
                    if idx <= realm_idx:
                        E.err(wq, "realm %r does not advance (current %r)" % (r["realm"], W.REALMS[realm_idx]))
                    realm_idx = idx
            quests.append({"id": wq, "chapter": ci, "number": qnum, "title": q["title"], "summary": q["summary"],
                           "map": q["map"], "objectives": out_objs,
                           "rewards": {"xp": r["xp"], "items": dict(sorted(r["items"].items())), "realm": r["realm"]}})
    if qnum != 100:
        E.err("story", "needs exactly 100 quests, has %d" % qnum)
    if quests and quests[-1]["rewards"]["realm"] != W.REALMS[-1]:
        E.err("q100", "the final quest must grant %s" % W.REALMS[-1])

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

    return {"version": 1, "chapters": chapters, "npcs": npcs, "quests": quests, "cinematics": cinematics}


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


def iter_lines(data):
    for q in data["quests"]:
        for o in q["objectives"]:
            for ln in o.get("dialogue", []):
                yield ln
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
    maps = Counter(o["map"] for o in objs)
    bosses = sum(1 for o in objs if o["type"] == "defeat" and o["enemy"] in W.BOSSES)
    out = []
    out.append("story.json: %d chapters, %d quests, %d objectives, %d cinematics, %d npcs"
               % (len(data["chapters"]), len(data["quests"]), len(objs), len(data["cinematics"]), len(data["npcs"])))
    out.append("objectives by type: " + ", ".join("%s %d (%.0f%%)" % (t, by_type[t], 100.0 * by_type[t] / len(objs))
                                                   for t in W.OBJECTIVE_TYPES))
    out.append("objectives by map: " + ", ".join("%s %d" % (m, maps[m]) for m in W.MAPS))
    out.append("boss fights: %d" % bosses)
    out.append("voiced lines: %d (%d gendered) -> %d voice files; %d words"
               % (len(lines), gendered, len(lines) + gendered, n_words))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if godot/data/story.json is stale")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    data = build()
    for w in E.warnings:
        print("warning: " + w, file=sys.stderr)
    if E.errors:
        for e in E.errors:
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
    if not args.quiet:
        print(stats(data))
        print("wrote %s (%d bytes)" % (os.path.relpath(args.out, ROOT), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

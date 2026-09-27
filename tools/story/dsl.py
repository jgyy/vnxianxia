"""A tiny DSL that keeps the chapter files readable.

Every helper returns a plain dict. Maps, voice keys and voice paths are
filled in by tools/build_story.py, which also validates everything against
tools/world_spec.py:

* an objective without ``map=`` inherits the map of the previous objective
  (the first one inherits the quest's map; a cinematic takes its own map);
* dialogue lines are written as ``(speaker, text)`` tuples, where speaker is
  an NPC id, ``P`` (the active protagonist) or ``N`` (the narrator).

Text tokens resolved at runtime by the active protagonist:
{player} {junior} {senior} {sibling} {they} {them} {their}

Group scenes: every objective helper takes ``with_=(npc, ...)`` (``with`` is a
Python keyword), the extra NPCs who are present for that objective's
conversation (story.json field ``"with"``, see CONTRACT). The story package
also adds every NPC who speaks in an objective (dialogue or choice replies)
and is not its ``npc`` to ``with`` (see ``fill_with``), so ``with_`` is only
needed for silent bystanders.

``added(speaker, text)`` marks a line written later into a *voiced* quest of
the original story: build_story gives it a voice key after the objective's
original lines (``q017_o2_l4`` if the objective had four), so the voice keys of
the original lines never move.
"""

P = "player"
N = "narrator"


class _Added(tuple):
    """A dialogue line added to a voiced quest after its recording (see ``added``)."""


def added(speaker, text):
    return _Added((speaker, text))


def _lines(lines):
    """``(speaker, text)`` or ``(speaker, text, cond)``: a conditional line is
    shown only when ``cond`` holds (see build_story.check_cond)."""
    out = []
    for item in lines:
        if not (isinstance(item, tuple) and len(item) in (2, 3)):
            raise ValueError("dialogue lines must be (speaker, text[, cond]) tuples, got %r" % (item,))
        d = {"speaker": item[0], "text": item[1]}
        if len(item) == 3:
            d["cond"] = dict(item[2])
        if isinstance(item, _Added):
            d["added"] = True
        out.append(d)
    return out


def _obj(kind, text, map, with_=(), **fields):
    d = {"type": kind, "map": map}
    d.update(fields)
    d["text"] = text
    if with_:
        d["with"] = list(with_)
    return d


def talk(npc, text, *lines, at=None, map=None, with_=()):
    """Walk up to ``npc`` (at their home, or standing at marker ``at``) and press E."""
    return _obj("talk", text, map, with_, npc=npc, at=at, dialogue=_lines(lines))


def reach(marker, text, *lines, radius=4.0, map=None, with_=()):
    """Arrive within ``radius`` metres of ``marker``; optional arrival dialogue."""
    d = _obj("reach", text, map, with_, marker=marker, radius=float(radius))
    if lines:
        d["dialogue"] = _lines(lines)
    return d


def defeat(enemy, count, marker, text, *lines, map=None, with_=()):
    """Enemies spawn around ``marker``; optional lines are spoken as the fight starts."""
    d = _obj("defeat", text, map, with_, enemy=enemy, count=count, marker=marker)
    if lines:
        d["dialogue"] = _lines(lines)
    return d


def collect(item, count, marker, text, map=None, with_=()):
    """Pickups scatter within 8 m of ``marker`` (collect objectives carry no dialogue)."""
    return _obj("collect", text, map, with_, item=item, count=count, marker=marker)


def meditate(marker, seconds, text, *lines, map=None, with_=()):
    """Press C at ``marker`` and cultivate for ``seconds``."""
    d = _obj("meditate", text, map, with_, marker=marker, seconds=float(seconds))
    if lines:
        d["dialogue"] = _lines(lines)
    return d


def interact(obj, marker, text, *lines, map=None, with_=()):
    """Inspect a world_spec.PROPS object placed at ``marker``."""
    d = _obj("interact", text, map, with_, object=obj, marker=marker)
    if lines:
        d["dialogue"] = _lines(lines)
    return d


def tribulation(marker, bolts, text, *lines, waves=(), map=None, with_=()):
    """A heavenly tribulation at ``marker``: ``bolts`` lightning strikes the
    player must survive, with optional waves ``(enemy, count, after_volley)``
    of tribulation beasts / heart shades. Optional lines open it."""
    d = _obj("tribulation", text, map, with_, marker=marker, bolts=bolts,
             waves=[{"enemy": e, "count": c, "after": a} for e, c, a in waves])
    if lines:
        d["dialogue"] = _lines(lines)
    return d


def speakers(obj):
    """NPC ids speaking in an objective's dialogue or choice replies, in order of first appearance."""
    out = []
    lines = list(obj.get("dialogue") or []) + [ln for op in obj.get("choices") or [] for ln in op["reply"]]
    for ln in lines:
        sp = ln["speaker"]
        if sp not in (P, N) and sp not in out:
            out.append(sp)
    return out


def fill_with(obj):
    """Complete ``obj["with"]``: the explicit bystanders, then every other NPC who speaks."""
    present = list(obj.get("with") or [])
    for sp in speakers(obj):
        if sp != obj.get("npc") and sp not in present:
            present.append(sp)
    if present:
        obj["with"] = present
    else:
        obj.pop("with", None)
    return obj


def cinematic(cin_id, text):
    """Play cinematic ``cin_id``; the objective's map is the cinematic's map."""
    return _obj("cinematic", text, None, id=cin_id)


def quest(title, summary, map, objectives, xp, items=None, realm=None):
    return {
        "title": title,
        "summary": summary,
        "map": map,
        "objectives": list(objectives),
        "rewards": {"xp": xp, "items": dict(items or {}), "realm": realm},
    }


def chapter(number, title, summary, intro_cinematic, map, quests):
    return {
        "number": number,
        "title": title,
        "summary": summary,
        "intro_cinematic": intro_cinematic,
        "map": map,
        "quests": list(quests),
    }


# ---------------------------------------------------------------- cinematics

def actor(who, marker, anim="idle", face=None):
    return {"npc": who, "marker": marker, "anim": anim, "face": face}


def foe(enemy, marker, count=1):
    return {"enemy": enemy, "marker": marker, "count": count}


def shot(marker, frm, to, speaker=None, text=None, look=1.6, dur=None):
    """A camera move around ``marker`` from ``frm`` to ``to`` = (yaw, distance, height)."""
    return {
        "marker": marker,
        "from": {"yaw": frm[0], "distance": frm[1], "height": frm[2]},
        "to": {"yaw": to[0], "distance": to[1], "height": to[2]},
        "look_height": look,
        "duration": dur,
        "speaker": speaker if text else None,
        "text": text,
    }


def cin(map, actors, shots, title=None, subtitle=None, music=None, enemies=()):
    return {
        "map": map,
        "title": title,
        "subtitle": subtitle,
        "music": music,
        "actors": list(actors),
        "enemies": list(enemies),
        "shots": list(shots),
    }

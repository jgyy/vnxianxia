"""Alignment, moral choices and interactions that depend on who the player
has become.

The player carries two scores, Law<->Chaos and Good<->Evil (-100..100 each,
see world_spec.ALIGN_*), giving the nine alignments ``lawful_good`` ..
``chaotic_evil``. Story data can depend on them in three ways:

* **choices** on an objective: 2-4 options, each with alignment deltas, reply
  lines, an optional reward, a flag and NPC attitude changes. Every option
  continues the story the same way; only the player's record differs.
* **conditional lines**: a dialogue line with ``cond`` is shown only when the
  condition holds (alignment, realm, minor stage, flags, attitude). Every
  conversation keeps at least one unconditional line, so no alignment can
  block the story.
* **alignment rewards** (``rewards.bonus``) and NPC **greetings**: idle barks
  and greetings that react to the player's alignment and realm.

This module holds the shared vocabulary: NPC temperaments, reactions,
greetings, choice templates for the generated chapters and chapter-end
bonuses. Hand-written choices live in choices.py.
"""

import hashlib

from . import npcs as NP
from .dsl import N, P

# ---------------------------------------------------------------- temperaments

CATEGORY = {}
for _nid in (NP.YUN, NP.MO, NP.BAI, NP.GU, NP.HUA, NP.SAGE, NP.JING, NP.RUANHAI, NP.TIANLU, NP.LAN):
    CATEGORY[_nid] = "elder"
for _nid in (NP.HAN, NP.WEI, NP.ZHAO, NP.YAN, NP.RUAN):
    CATEGORY[_nid] = "peer"
for _nid in (NP.LU, NP.MAN, NP.SHI, NP.LIUER):
    CATEGORY[_nid] = "junior"
for _nid in (NP.FANG, NP.DU, NP.LIU, NP.PAN, NP.JIN, NP.QIAN, NP.HONG, NP.ZHOU):
    CATEGORY[_nid] = "town"
for _nid in (NP.YE, NP.TIE, NP.GOU):
    CATEGORY[_nid] = "rogue"
for _nid in (NP.PATRIARCH, NP.XUEMEI, NP.DEMON, NP.RUNG1, NP.RUNG2, NP.RUNG3, NP.RUNG4, NP.RUNG5, NP.RUNG6,
             NP.RUNG7):
    CATEGORY[_nid] = "demonic"
# the minor cast of the enlarged world
for _nid in (NP.SHEN, NP.QIU, NP.HE, NP.SHUREC):
    CATEGORY[_nid] = "elder"
for _nid in (NP.TAO, NP.LING, NP.ZHONG, NP.QU):
    CATEGORY[_nid] = "peer"
for _nid in (NP.FAN, NP.TANG, NP.PEI, NP.QINGYI):
    CATEGORY[_nid] = "junior"
for _nid in (NP.BAO, NP.RUO, NP.KUANG, NP.SHU, NP.MENG, NP.OUYANG, NP.QIAO, NP.WANG, NP.YU, NP.BI, NP.LEI, NP.HUO):
    CATEGORY[_nid] = "town"
CATEGORY[NP.KU] = "rogue"
CATEGORY[NP.HEI] = "demonic"
# the traitor in chains, and your own heart demon: they react, but never greet
CATEGORY[NP.GU] = "prisoner"
CATEGORY[NP.DEMON] = "prisoner"


def category(nid, q=None):
    """``nid``'s temperament during quest ``q`` (None: the one used for idle greetings).
    Gu Hanshan is a respected Law Hall elder until he is unmasked at the tournament and only
    then a prisoner; before, reacting to a disciple's choices with a prisoner's regrets
    ("Kinder than I was, at your age") would give the traitor away in chapter one."""
    if nid == NP.GU and q is not None and q <= _gu_unmasked():
        return "elder"
    return CATEGORY.get(nid, "town")


def _gu_unmasked():
    from .numbering import resolve_id
    return resolve_id(NP.NPCS[NP.GU]["hidden_after"])


def h(*key):
    return int(hashlib.sha1(repr(key).encode("utf-8")).hexdigest()[:12], 16)


def direction(law, good):
    """The moral direction of an option: good / evil / lawful / chaotic / neutral."""
    if abs(good) >= abs(law) and abs(good) >= 5:
        return "good" if good > 0 else "evil"
    if abs(law) >= 5:
        return "lawful" if law > 0 else "chaotic"
    return "neutral"


REACT = {
    "elder": {
        "good": ["That was kindly done. Remember how it felt.", "Good. Heaven notices kindness, even when people don't.",
                 "Mercy costs something. You paid it without complaint. Well done."],
        "evil": ["(a long silence) I did not teach you that.", "I will remember this, {player}. So will heaven.",
                 "Power without a heart. We fought a war against exactly that."],
        "lawful": ["Correct. The precepts exist for moments like this.", "By the rules, and rightly so.",
                   "Order is a kindness too, when it is fair."],
        "chaotic": ["Hm. Unorthodox. It worked. Don't make a habit of it.", "The precepts weep. I'll pretend not to hear them.",
                    "You walk your own road. Mind it doesn't walk off a cliff."],
        "neutral": ["A careful choice. Neither soft nor cruel.", "Hm. Measured. I can live with measured."],
    },
    "peer": {
        "good": ["You're too nice. It's annoying. I like it.", "That's why people follow you, you know."],
        "evil": ["Remind me never to owe you money.", "(quietly) That was cold, {player}. Even for a war."],
        "lawful": ["By the book. The Law Hall would weep with joy.", "Rules, rules. Fine. You're right. Again."],
        "chaotic": ["Ha! The elders are going to hate that. I love it.", "Rules are for people without your luck."],
        "neutral": ["Fair enough. Can't argue with that.", "Sensible. Boring. Sensible."],
    },
    "junior": {
        "good": ["{senior}, that was... I want to be like that one day.", "I'm going to tell everyone at the gate about this."],
        "evil": ["(quietly) Is that... is that what seniors are supposed to do?", "(looking at the ground) Oh. Okay."],
        "lawful": ["That's exactly what the precepts say! I memorised them!", "The ninth precept! You did the ninth precept!"],
        "chaotic": ["Can you do that? Are we allowed to do that?", "I'm not going to tell anyone. Probably."],
        "neutral": ["Oh. Okay. I think that makes sense.", "Right. Yes. Good. I think."],
    },
    "town": {
        "good": ["Heaven bless you, immortal. We won't forget.", "Most cultivators wouldn't have. Thank you."],
        "evil": ["(nervously) Y-yes. Of course. Whatever the immortal wishes.", "(backing away) As you say, immortal."],
        "lawful": ["The magistrate would approve. So do I.", "Proper. Very proper. Good."],
        "chaotic": ["Well! That's one way to do it.", "Ha! Don't let the magistrate hear."],
        "neutral": ["Sensible. My mother would've done the same.", "Fair. Fair's all anyone asks."],
    },
    "rogue": {
        "good": ["Soft. Soft wins more fights than people think.", "You'd have been a terrible bandit. It's a compliment."],
        "evil": ["Now you're speaking my old language. I don't miss it.", "Careful. I know where that road ends."],
        "lawful": ["Rules. You sects and your rules. ...It was the right call.", "Proper as a magistrate. Hm."],
        "chaotic": ["Ha. Knew there was a bandit in you somewhere.", "Good. Rules are for people who've never been hungry."],
        "neutral": ["Hm. Practical.", "No argument here."],
    },
    "demonic": {
        "good": ["Mercy. How exhausting it must be, being you.", "Soft hands. They'll break on the Ladder."],
        "evil": ["Oh, you'd have done well in the Abyss. Think about it.", "There it is. The thing your elders pretend you don't have."],
        "lawful": ["Rules. The Patriarch had rules too. Ask his victims how they helped.", "Obedient little heir."],
        "chaotic": ["Wild. Unpredictable. Almost one of us.", "No rules. Careful. That's how it starts."],
        "neutral": ["Cold. Good. Cold survives.", "Hm. Harder to read than I'd like."],
    },
}


# more voices per temperament, so the same reaction rarely comes round twice in a chapter
for _cat, _more in {
    "elder": {"good": ["Hm. That is the kind of disciple the founders hoped for.",
                       "Kindness with a spine. Rarer than any spirit herb."],
              "evil": ["(sets down the cup, very carefully) No.", "We will speak of this again, and you will not enjoy it."],
              "lawful": ["Properly done. The precepts are older than all of us, for good reason.",
                         "Just so. Fairness first, feelings after."],
              "chaotic": ["A crooked road can still arrive. Mind that it does.", "I'll allow it. Once."],
              "neutral": ["Sensible. Neither the soft road nor the hard one.", "Hm. I would have done much the same."]},
    "peer": {"good": ["Of course you did. You always do. It's infuriating.", "Heart of a steamed bun, that one."],
             "evil": ["I'll pretend I didn't see that.", "(looks away) Right. Let's go."],
             "lawful": ["Proper as a stele, as always.", "You and the precepts. A love story."],
             "chaotic": ["I didn't see anything. Nobody saw anything.", "That's going to cause trouble. Good trouble. Probably."],
             "neutral": ["Hm. Fine.", "Reasonable. Annoyingly reasonable."]},
    "junior": {"good": ["(eyes shining) That was so kind.", "I'm going to try that too. The kind thing."],
               "evil": ["(very quietly) Is that allowed?", "(steps back) Right. Yes. Of course."],
               "lawful": ["Properly done! I'm writing that down.", "(nodding hard) Yes. The rules. Good."],
               "chaotic": ["(whispering) That was amazing. And terrifying.", "I'll pretend I was looking the other way."],
               "neutral": ["Hm. Yes. Probably right.", "(thinks very hard) Yes. I agree."]},
    "town": {"good": ["The whole street will hear of this.", "(wiping away tears) Most of your kind wouldn't have bothered."],
             "evil": ["(pales) Of course. Of course.", "(says nothing, very carefully)"],
             "lawful": ["That's the law, that is.", "The magistrate himself couldn't fault it."],
             "chaotic": ["Bold. Very bold.", "Ha! Don't let the constable hear."],
             "neutral": ["Sensible, that.", "Can't say fairer than that."]},
    "rogue": {"good": ["Kinder than the road ever was to me.", "Hm. Somebody raised you right."],
              "evil": ["Heh. Cold. I remember cold.", "That's the look I used to see in the water."],
              "lawful": ["By the book. Fine.", "Proper as a magistrate. Hm."],
              "chaotic": ["Now you're thinking like the road.", "The sect never tamed you, did it."],
              "neutral": ["No argument.", "Hm. Works."]},
}.items():
    for _d, _lines in _more.items():
        REACT[_cat][_d] = REACT[_cat][_d] + _lines


REACT["prisoner"] = {
    "good": ["(quietly) Kinder than I was, at your age.", "Hm. She would have liked you."],
    "evil": ["I know that look. I wore it for twenty years.", "Careful. That is how it started, for me."],
    "lawful": ["The law. I used to believe it mattered most.", "Correct. I taught that once. I should have listened."],
    "chaotic": ["Rules broke me too. From the other side.", "Hm. The Law Hall would have your hide."],
    "neutral": ["Hm.", "As you like."],
}


# Reactions in a character's own voice, for the people the player answers most often. They are
# mixed with the category's pool, so nobody says the same thing a hundred times over the saga.
REACT_NPC = {
    NP.HAN: {"good": ["Hm. Kind. Don't let it make you slow.", "You'd give away your own sword if someone looked cold.",
                      "That was the right thing. I'll deny saying so."],
             "evil": ["I'll pretend I didn't see that. Once.", "(her jaw tightens) We'll talk about that later. Alone.",
                      "That's not you. Or it didn't used to be."],
             "lawful": ["Correct. Clean. Like a good stance.", "By the precepts. Good. They're there for a reason."],
             "chaotic": ["Reckless. It worked. Don't tell me how.", "Breathe first, break rules second. You skipped a step."],
             "neutral": ["Sensible.", "Fine. Moving on."]},
    NP.WEI: {"good": ["That's the {player} I'd share my last bun with. Half of it.", "Good! Good. Elder Mo would grunt. That's a yes."],
             "evil": ["Oh. Oh, I didn't like that. My stomach didn't like that.", "Hey. That's not... we don't do that, do we?"],
             "lawful": ["The proper way! Very proper. I'd have done it improperly.", "Rules are like recipes. You followed it exactly."],
             "chaotic": ["Ha! Dumpling approves. Dumpling is a sword and has no morals.", "The Law Hall's going to write you a very long letter."],
             "neutral": ["Fair. Fair's good. Can we eat now?", "Right. That works."]},
    NP.ZHAO: {"good": ["Soft-hearted. It's a village thing. I'm... getting used to it.", "My brother would have done the same. Don't tell anyone I said that."],
              "evil": ["Even the Zhao clan has lines. You just stepped over one.", "(coldly) I expected better. That's new for me."],
              "lawful": ["Proper. The Zhao clan approves, grudgingly.", "By the book. How very outer-disciple of you."],
              "chaotic": ["Unorthodox. My grandfather would faint. I'm delighted.", "That's cheating. Brilliant cheating. Teach me later."],
              "neutral": ["Acceptable.", "Hmph. Reasonable. Annoyingly."]},
    NP.LAN: {"good": ["The lotus grows in mud and is not stained. You remembered.", "Kindness is slow tea. Worth the wait."],
             "evil": ["I ran from things like that once. Don't make me run again.", "(sets down his cup) That was not the lotus way."],
             "lawful": ["The old rules, kept well. My masters would have smiled.", "Orderly. The bamboo approves. It likes straight lines."],
             "chaotic": ["The bamboo bends. So did you. It is not always wrong.", "Unruly. The forest is unruly too, and it thrives."],
             "neutral": ["Hm. Balanced, like a good kettle.", "Neither here nor there. Like me, mostly."]},
    NP.YUN: {"good": ["That is the sect I want. Thank you for being it.", "Mercy from strength. The founders would be proud."],
             "evil": ["(very still) I will remember this, {player}. As your sect master.", "Power without a heart. We have buried that before."],
             "lawful": ["As the precepts ask. Good.", "Order, fairly kept. That is all I ever ask of anyone."],
             "chaotic": ["Unorthodox. I'll pretend I didn't hear the details.", "You bend rules like the wind bends pines. Mind you don't snap one."],
             "neutral": ["Measured. Sensible.", "Hm. A careful choice."]},
    NP.YE: {"good": ["Hm. Kinder than the Abyss would have been.", "...Good."],
            "evil": ["I was raised on that. I don't recommend it.", "The Patriarch would have liked that. Think about it."],
            "lawful": ["Rules. Hm. They kept you clean.", "Proper. You sect people."],
            "chaotic": ["Good. Rules are for people who've never been hunted.", "Hm. The road taught you that."],
            "neutral": ["Hm.", "..."]},
    NP.TIE: {"good": ["Soft. Soft saved my people. I'm not laughing.", "Ha. You'd have made a terrible bandit. Best compliment I've got."],
             "evil": ["I did things like that once. Ask me how that ended.", "Careful. That's how the hungry years start."],
             "lawful": ["The constable would weep. Proper tears.", "Rules. Fine. They're not always wrong."],
             "chaotic": ["Ha! Now you're talking like the old road.", "That's my kind of justice. The quick kind."],
             "neutral": ["Practical. I like practical.", "Hm. No arguing with it."]},
    NP.SAGE: {"good": ["A star just brightened. Coincidence, probably. Probably.", "Kindness. The stars notice more than they let on."],
              "evil": ["The stars dim a little when someone does that. I've counted.", "Heaven is watching, lotus child. It keeps very long records."],
              "lawful": ["Tidy. The heavens adore tidy.", "Proper. The celestial clerks would weep with joy."],
              "chaotic": ["Unruly! Like a comet. Comets are my favourite.", "The stars disagree. The stars often disagree. I side with you."],
              "neutral": ["Balanced, like a scale nobody is watching.", "Hm. The stars shrug."]},
    NP.YAN: {"good": ["THAT'S the spirit! Thunder Peak salutes kindness! Loudly!", "Heart first, fist second. Just like the peak teaches!"],
             "evil": ["(quietly, for once) That was ugly. I remember being ugly.", "Frenzy made me do worse. You had no excuse."],
             "lawful": ["By the rules! Clean as a duel!", "Proper! I'd shout about it but it seems improper."],
             "chaotic": ["HA! Thunder Peak would do exactly that!", "Wild! I like it. Don't tell the elders I said so."],
             "neutral": ["Fair! Fair and loud!", "Hm! Sensible! Loudly sensible!"]},
    NP.BAI: {"good": ["A kindness worth a footnote. Several footnotes.", "The chronicles are full of cruelty. Thank you for a better page."],
             "evil": ["I shall not write that down. Some things should not be copied.", "(takes off his spectacles) I didn't see that. I refuse to have seen that."],
             "lawful": ["Correctly done, per article three, subsection nine.", "Precedent followed. The shelves approve."],
             "chaotic": ["Irregular! Marvellously irregular. Unrecordable, even.", "No precedent for that at all. How exciting."],
             "neutral": ["A reasonable reading of the situation.", "Hm. Measured. Like a good index."]},
    NP.HUA: {"good": ["A gentle hand. That's the best medicine there is.", "Good. The heart heals slower than bones. Look after yours."],
             "evil": ["That's a wound that won't show. The worst kind.", "(stops mixing) I don't have a pill for that, {player}."],
             "lawful": ["Proper, like a correct dose.", "By the book. Books keep healers from killing people."],
             "chaotic": ["Unorthodox treatment. It may even work.", "Hm. Risky. Like my better remedies."],
             "neutral": ["Sensible. Drink some water.", "Balanced. Like a good tonic."]},
    NP.SHI: {"good": ["You didn't have to. That's why it matters.", "That's what you did for me. Thank you. Again."],
             "evil": ["(quietly) The guards in the cages said things like that.", "Oh. I... thought you were different."],
             "lawful": ["The proper way. I like proper. Proper has doors that open.", "Good. Rules mean someone comes looking for you."],
             "chaotic": ["Sometimes the rules are the cage. I know.", "Ha. I'd have done that too, if I were brave."],
             "neutral": ["That makes sense.", "Fair. I think."]},
    NP.LU: {"good": ["I'm telling the whole gate! Twice! With improvements!", "That's going in my stories. The good ones."],
            "evil": ["I'm... not going to tell anyone about that one.", "Oh. Oh, that's not a story I'm telling."],
            "lawful": ["By the precepts! I know those! Well, most of them!", "Very proper. I'd bet on you for proper."],
            "chaotic": ["Ha! I'd have lost money on that. Nobody saw it coming!", "Is that allowed? It is now, I suppose!"],
            "neutral": ["Right. Yes. Sensible. Boring, but sensible.", "Hm. I'll bet even on that one."]},
    NP.DU: {"good": ["Heaven bless you. I'll write that down too.", "Kindly done. The town remembers kindness."],
            "evil": ["I'll write it down. I write everything down, cultivator.", "(pen stops) That goes in the book. The bad page."],
            "lawful": ["By the law. That's all I ever ask.", "Proper. The magistrate will sleep better."],
            "chaotic": ["That's... not in the book. I'll invent a page.", "Unlawful, strictly. Effective, though."],
            "neutral": ["Fair enough. Noted.", "Reasonable. Written down."]},
    NP.GU: {"good": ["Mercy. I forgot how it looks.", "Kinder than the Law Hall ever was."],
            "evil": ["I know that road. I walked it for twenty years.", "Careful. That is how it starts."],
            "lawful": ["Correct. I taught that once. I should have listened.", "The law, kept. It matters more than I let it."],
            "chaotic": ["The precepts would object. I have lost the right to.", "Hm. Unorthodox."],
            "neutral": ["Hm.", "As you like."]},
}


def reaction(nid, law, good, salt=(), q=None):
    d = direction(law, good)
    pool = REACT[category(nid, q)][d]
    own = REACT_NPC.get(nid, {}).get(d, [])
    # Gu's own lines are a prisoner's: only after he is unmasked
    if nid == NP.GU and category(nid, q) != "prisoner":
        own = []
    pool = list(own) + list(pool)
    return pool[h(nid, law, good, *salt) % len(pool)]


# ---------------------------------------------------------------- greetings

# (condition, lines): a talk may open with one of these, shown only when the condition holds.
GREET = {
    "elder": [
        ({"align": "*_evil"}, ["(coldly) {player}. I have heard what you've been doing. Speak, and be brief.",
                               "(does not smile) {player}. The righteous path has a narrow gate. Mind you still fit."]),
        ({"align": "*_good"}, ["(warmly) {player}. The mountain speaks well of you. Come, sit.",
                               "There you are. Half the young ones want to be you. Try to deserve it."]),
        ({"align": "chaotic_*"}, ["You again. Which rule have you broken this week? No. Don't tell me. Later.",
                                  "(sighs) I can see the precepts sliding off you like rain."]),
        ({"align": "lawful_*"}, ["Punctual, correct, precepts in order. You make an old teacher's work easy.",
                                 "Word of your conduct travels. All of it good. Sit."]),
    ],
    "peer": [
        ({"align": "*_evil"}, ["(guarded) {player}. People are saying things. I'm not asking. Yet.",
                               "You've changed. I haven't decided if I like it."]),
        ({"align": "*_good"}, ["The hero of the hour! Stop blushing. Everyone's talking about you.",
                               "{player}! The juniors want to know if you're real. I told them barely."]),
        ({"align": "chaotic_*"}, ["Still breaking rules? Good. Someone has to keep the elders awake.",
                                  "If the Law Hall asks, I haven't seen you all week."]),
        ({"align": "lawful_*"}, ["Straight-backed as a precept stele, as always.",
                                 "You're so proper lately. It's unnerving. Do something wrong. Once."]),
    ],
    "junior": [
        ({"min_realm": "Nascent Soul"}, ["(bows so deeply it nearly ends in a tumble) {senior}! This junior greets... I mean, hello. Your qi makes my hair stand up.",
                                         "(bows three times, then a fourth to be safe) {senior}! Sorry. You're very high up now. It's hard not to bow."]),
        ({"align": "*_evil"}, ["(steps back half a pace) {senior}... people say things about you. I don't believe them. Mostly.",
                               "(quietly) Hello, {senior}. I'll be good. I promise."]),
        ({"align": "*_good"}, ["{senior}! The little ones at the gate tell stories about you now. Good ones!",
                               "{senior}! I tried to do a kind thing like you did. It went wrong. But I tried!"]),
    ],
    "town": [
        ({"min_realm": "Soul Transformation"}, ["(kneels in the road) Immortal one! Ah, sorry, it's you. Sorry. Habit. You shine a bit now.",
                                                "(starts to kneel, then thinks better of it) Heavens. You feel like weather now, did you know?"]),
        ({"align": "*_evil"}, ["(nervously) W-what can I do for you, immortal? Anything. Anything at all.",
                               "(forcing a smile) Immortal. We've paid, haven't we? We've paid."]),
        ({"align": "*_good"}, ["Everyone knows your kindness. Here, have a peach.",
                               "The immortal who helps! My grandmother lit incense for you."]),
    ],
    "rogue": [
        ({"align": "*_evil"}, ["Look at you. Wearing the sect's robes and the bandit's heart. Careful.",
                               "(grins without warmth) You've been busy. The wrong kind of busy."]),
        ({"align": "*_good"}, ["The soft-hearted immortal. Still alive. Surprises me every time.",
                               "Kind, and still breathing. You're rarer than spirit stones."]),
        ({"align": "chaotic_*"}, ["Ha. You break rules like someone raised on the road.",
                                  "The sect hasn't tamed you. Good."]),
    ],
    "demonic": [
        ({"align": "*_evil"}, ["Ah. You smell of the right things now. The Blood Moon has room for someone like you. Think on it.",
                               "Why fight us, heir? You already walk half our road. Walk the rest with me."]),
        ({"align": "*_good"}, ["Still playing the hero? Heroes die tired, heir.",
                               "The righteous heir. How sweet. How breakable."]),
        ({"align": "lawful_*"}, ["The sect's obedient blade. Do they let you think, or only strike?"]),
    ],
}

# kinds of beats whose opening talk may carry a greeting that depends on who the player has become
# (not the quiet or grieving scenes of social / interlude / council beats)
GREET_KINDS = {"orders", "gather", "hunt", "probe", "train", "cultivate", "journey", "festival", "duel", "delve",
               "rescue"}


def greeting_lines(nid, q):
    """0-2 conditional opening lines for a talk with ``nid`` in quest ``q``."""
    pool = GREET.get(category(nid, q))
    if not pool or h(q, nid, "greet") % 3:
        return []
    k = h(q, nid, "which") % len(pool)
    out = []
    for cond, texts in (pool[k], pool[(k + 1) % len(pool)]):
        # a pair only when the two conditions exclude each other (never two greetings at once)
        if out and not _exclusive(out[0][2], cond):
            break
        out.append((nid, texts[h(q, nid, repr(cond)) % len(texts)], cond))
    return out


def _exclusive(a, b):
    pats = {a.get("align"), b.get("align")}
    return pats in ({"*_evil", "*_good"}, {"chaotic_*", "lawful_*"})


def bark_greetings(nid):
    """Idle greetings (barks) of an NPC that depend on alignment and realm."""
    out = []
    for cond, texts in GREET.get(category(nid), []):
        out.append({"text": texts[h(nid, repr(cond)) % len(texts)], "cond": dict(cond)})
    return out


# ---------------------------------------------------------------- choices

def O(text, law=0, good=0, reply=(), xp=0, items=None, flag=None, att=None, cond=None):
    """One option of a choice. ``reply``: extra lines after it (the NPC's reaction is added)."""
    return {"text": text, "align": {"law": law, "good": good}, "reply": list(reply),
            "reward": {"xp": xp, "items": dict(items or {})}, "flag": flag, "attitude": dict(att or {}),
            "cond": dict(cond) if cond else None}


def Ch(prompt, *options, at="last"):
    return {"prompt": prompt, "options": list(options), "at": at}


HUMAN_FOES = {"bandit", "rogue_cultivator", "iron_scale_disciple", "demon_cultivator", "blood_guard"}
BEAST_FOES = {"spirit_wolf", "corrupted_wolf", "thunder_wolf", "tribulation_beast"}

TEMPLATES = {
    "fight_human": [
        Ch("One of the {foes} is still alive, clutching a wound and begging for his life.",
           O("Bind his wound and let him go", law=-5, good=10),
           O("Hand him over to face the law", law=10, good=2),
           O("End it. He would have killed you.", good=-10),
           O("Make him swear to serve you, then let him run", law=-10, good=-8, items={"spirit_stone": 1},
             cond={"align": "*_evil"})),
        Ch("The {foes} left a purse of spirit stones behind, and a wounded straggler.",
           O("Return the stones to the people they robbed", law=2, good=8),
           O("Turn stones and straggler over to the sect", law=10),
           O("Pocket the stones and leave the straggler", law=-6, good=-6, items={"spirit_stone": 2})),
        Ch("Among the fallen {foes}: a boy of fifteen, unhurt, too frightened to run.",
           O("Send him home to his mother", law=-4, good=10),
           O("Bring him to the sect to be judged", law=8),
           O("Make him carry your gear, unpaid", law=-2, good=-8)),
    ],
    "fight_beast": [
        Ch("One of the {foes} lies wounded, panting, its eyes clearing now that the fight is over.",
           O("Bind its leg and let it limp away", law=-2, good=8),
           O("Give it a clean, quick end", law=3),
           O("Cut out its core while it still breathes", good=-12, items={"demon_core": 1})),
        Ch("Behind the {foes} you drove off, a den of whimpering pups.",
           O("Carry them to the deep forest, far from people", good=8),
           O("Report the den to the sect's beast keepers", law=8),
           O("Sell the pups to a beast trader", law=-4, good=-8, items={"spirit_stone": 2})),
        Ch("The {foes} were driven mad by a demonic talisman nailed to a tree.",
           O("Burn the talisman and calm the beasts", good=6),
           O("Take it to the elders as evidence", law=8),
           O("Keep it. It could be useful.", law=-4, good=-8)),
    ],
    "gather": [
        Ch("You gathered more {noun} than the task needs.",
           O("Give the extra to the town's poor", good=8),
           O("Hand everything to the storehouse, as the rules say", law=8),
           O("Keep the extra for your own cultivation", law=-3, good=-5, items={"@item": 2})),
        Ch("An old herb-woman asks to share the {noun} you were sent to gather.",
           O("Leave her half", law=-3, good=8),
           O("Tell her the sect has claimed it", law=8, good=-2),
           O("Take it all and send her away hungry", good=-10, items={"@item": 2})),
        Ch("The {noun} came from a hermit's plot, and the hermit isn't home.",
           O("Leave payment and a note", law=4, good=4),
           O("Take only what the task needs", law=6),
           O("Take everything", good=-8, items={"@item": 2})),
    ],
    "find": [
        Ch("Something valuable lies here, unclaimed: a purse of spirit stones.",
           O("Report it to the sect", law=8),
           O("Leave it for whoever lost it", law=-2, good=5),
           O("Pocket it quietly", law=-6, good=-5, items={"spirit_stone": 2})),
        Ch("A sealed jade slip lies here, stamped with another sect's seal.",
           O("Return it to its sect unread", law=8, good=2),
           O("Read it first. Knowledge is knowledge.", law=-6, xp=60),
           O("Sell it to the highest bidder", law=-4, good=-8, items={"spirit_stone": 3})),
        Ch("A dead courier's satchel holds silver for Blood Moon informers, and their names.",
           O("Burn the names; they were desperate", law=-6, good=6),
           O("Give the names to the magistrate", law=8),
           O("Keep the silver", good=-8, items={"spirit_stone": 3})),
        Ch("A spirit crane is caught in a poacher's snare nearby.",
           O("Free it and bind its wing", good=8),
           O("Report the poachers to the sect", law=8),
           O("Take it for its feathers", good=-10, items={"phoenix_feather": 1})),
    ],
    "social_sect": [
        Ch("{name} quietly admits to breaking a sect rule to help someone.",
           O("Promise to keep the secret", law=-6, good=5),
           O("Urge them to confess to the elders", law=8),
           O("Remember it. Leverage is useful.", law=-2, good=-8)),
        Ch("{name} asks what you really think of the sect's precepts.",
           O("They keep us from becoming the Blood Moon", law=8),
           O("Kindness first. Precepts after.", law=-3, good=6),
           O("They're tools. Use them when they help you.", law=-6, good=-3)),
        Ch("{name} mentions a junior stealing food from the kitchens for a sick friend.",
           O("Cover the food yourself", law=-2, good=8),
           O("Report it; the kitchens have rules", law=8),
           O("Tell the junior you'll stay quiet, for a price", good=-10, items={"spirit_stone": 1})),
        Ch("{name} asks you to vouch for a friend's examination, though you've never seen their work.",
           O("Vouch anyway", law=-6, good=4),
           O("Refuse. Vouching must be honest.", law=8),
           O("Vouch, for a favour later", law=-4, good=-6)),
    ],
    "social_town": [
        Ch("{name} confides they're hiding a runaway from the Blood Moon's cages. The magistrate doesn't know.",
           O("Help hide them", law=-6, good=8),
           O("Tell the magistrate, gently", law=8),
           O("Report them for the reward", good=-10, items={"spirit_stone": 2})),
        Ch("{name} offers you a gift for the immortal's protection. The neighbours can't afford one.",
           O("Refuse it", good=6),
           O("Accept it, and record it with the magistrate", law=6),
           O("Accept, and ask the neighbours for theirs", good=-12, items={"spirit_stone": 3})),
    ],
    "social_official": [
        Ch("{name} admits the town's grain tally was fudged to feed the refugees.",
           O("Keep it quiet. It fed people.", law=-6, good=6),
           O("Insist the books be put right", law=8),
           O("Take a cut for your silence", good=-10, items={"spirit_stone": 2})),
        Ch("{name} asks you to settle a farmers' quarrel. One of them is your friend.",
           O("Judge it fairly", law=8),
           O("Favour the poorer one", law=-3, good=6),
           O("Favour whoever pays", good=-8, items={"spirit_stone": 2})),
    ],
    "social_rogue": [
        Ch("{name} still carries a blade taken in the old days. Its owner's family lives nearby.",
           O("Urge them to give it back", law=2, good=6),
           O("Let the magistrate decide", law=8),
           O("Offer to sell it for them, for a cut", law=-4, good=-6, items={"spirit_stone": 2})),
        Ch("{name} asks whether an old debt should be paid in coin or in blood.",
           O("Coin, and mercy", good=8),
           O("Whatever the law says", law=8),
           O("Blood. Debts are debts.", good=-10)),
    ],
    "social_demonic": [
        Ch("{name} makes you an offer: a rung on the Ladder, and power without waiting.",
           O("Refuse", good=6),
           O("Refuse, and report the offer to the Sect Master", law=8),
           O("Say you'll think about it", law=-4, good=-8)),
    ],
    "train": [
        Ch("Your sparring partner leaves an opening that would injure them badly.",
           O("Pull the blow", good=6),
           O("Strike exactly as the rules allow", law=6),
           O("Take it. Pain teaches.", law=-2, good=-8, xp=40)),
        Ch("A junior begs you to teach them a forbidden technique from the fourth floor.",
           O("Refuse, and tell the elders", law=8),
           O("Teach them something safer instead", good=5),
           O("Teach it. Rules are for the timid.", law=-10)),
        Ch("The training ledger says three puppets broke today. Nobody saw who broke them.",
           O("Own up and pay for them", law=8),
           O("Repair them yourself, quietly", law=-2, good=4),
           O("Blame the juniors", good=-10)),
    ],
    "cultivate": [
        Ch("Nearby, a junior's qi is running wild. Helping will cost you your meditation.",
           O("Stop and steady their qi", good=8),
           O("Send for the elders; it's their duty", law=5),
           O("Drink their stray qi to deepen your own", law=-4, good=-12, xp=80)),
        Ch("A wandering cultivator offers you a pill that 'skips the hard parts'.",
           O("Refuse. Your foundation must be honest.", law=6),
           O("Take it to the Medicine Hall to be tested", law=3, good=3),
           O("Swallow it. Power is power.", law=-8, good=-3, xp=60)),
        Ch("A rival's meditation is faltering beside you. One nudge of qi would break it.",
           O("Steady them instead", good=8),
           O("Leave them to their own path", law=4),
           O("Nudge it. One rival fewer.", good=-10, xp=40)),
    ],
    "boss": [
        Ch("The fallen enemy's followers throw down their weapons and kneel.",
           O("Let them go home", law=-3, good=8),
           O("Bring them to face the sect's judgement", law=8),
           O("Make an example of them", law=2, good=-12)),
        Ch("Among the fallen enemy's belongings: a manual of a forbidden blood technique.",
           O("Burn it", law=3, good=5),
           O("Seal it in the Scripture Pagoda", law=8),
           O("Keep it. Study it. Quietly.", law=-5, good=-10, xp=80)),
        Ch("The fallen enemy's hoard holds spirit stones stolen from Qingshi.",
           O("Return every stone to Qingshi", good=8),
           O("Give it all to the sect treasury", law=8),
           O("Keep a share for yourself", good=-8, items={"spirit_stone": 3})),
    ],
}

# the town's officials get dilemmas of office instead of townsfolk ones
OFFICIALS = {NP.ZHOU, NP.DU}
SOCIAL_BY_CATEGORY = {"elder": "social_sect", "peer": "social_sect", "junior": "social_sect",
                      "town": "social_town", "rogue": "social_rogue", "prisoner": "social_rogue",
                      "demonic": "social_demonic"}

FAMILY_OF_KIND = {
    "hunt": "fight", "battle": "fight", "defend": "fight", "rescue": "fight", "chase": "fight", "delve": "find",
    "gather": "gather", "festival": "gather", "probe": "find", "orders": "find", "journey": "social",
    "social": "social", "interlude": "social", "council": "social", "train": "train", "duel": "train",
    "cultivate": "cultivate", "stage": "cultivate", "boss": "boss", "break": "cultivate",
}


# ---------------------------------------------------------------- chapter-end bonuses

BONUS = [
    {"cond": {"align": "*_good"}, "items": {"medicine": 1}, "xp": 0,
     "note": "Grateful people press medicine into your hands."},
    {"cond": {"align": "*_evil"}, "items": {"spirit_stone": 2}, "xp": 0,
     "note": "Frightened people pay you to go away. You take it."},
    {"cond": {"align": "lawful_*"}, "items": {}, "xp": 60,
     "note": "The Law Hall records your conduct with approval."},
    {"cond": {"align": "chaotic_*"}, "items": {}, "xp": 60,
     "note": "Rules bent, lessons learned the hard way."},
]


def chapter_bonus():
    return [dict(b, cond=dict(b["cond"]), items=dict(b["items"])) for b in BONUS]


__all__ = ["CATEGORY", "category", "direction", "reaction", "greeting_lines", "bark_greetings", "O", "Ch",
           "TEMPLATES", "FAMILY_OF_KIND", "HUMAN_FOES", "BEAST_FOES", "chapter_bonus", "N", "P"]

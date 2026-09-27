"""The named cast. Ids are exported as constants so a typo in a chapter file
is a NameError instead of a silent bug."""

from .voices import NPC_VOICES

# --- ids -------------------------------------------------------------------
YUN = "master_yun"
MO = "elder_mo"
BAI = "elder_bai"
GU = "elder_gu"
HUA = "elder_hua"
HAN = "senior_han"
WEI = "senior_wei"
ZHAO = "rival_zhao"
LU = "gate_lu"
QIAN = "steward_qian"
MAN = "xiao_man"
SHI = "xiao_shi"
LAN = "hermit_lan"
YE = "wanderer_ye"
TIE = "bandit_tie"
ZHOU = "magistrate_zhou"
FANG = "innkeeper_fang"
DU = "constable_du"
LIU = "widow_liu"
HONG = "keeper_hong"
PAN = "ferryman_pan"
JIN = "merchant_jin"
PATRIARCH = "patriarch_xue"
XUEMEI = "crimson_xuemei"
SAGE = "star_sage"
DEMON = "heart_demon"
# --- introduced by the 1000-quest saga (text-only, unvoiced)
YAN = "yan_tie"
LIUER = "liu_er"
GOU = "bandit_gou"
RUAN = "young_ruan"
RUANHAI = "master_ruan"
JING = "abbess_jing"
TIANLU = "ancestor_zhao"
RUNG1 = "rung_luo"
RUNG2 = "rung_shan"
RUNG3 = "rung_rong"
RUNG4 = "rung_kong"
RUNG5 = "rung_wen"
RUNG6 = "rung_si"
RUNG7 = "rung_chen"


def npc(name, title, model, home=None, tint=None, scale=1.0, appear_from=None, hidden_after=None, barks=(),
        gone_after=None):
    """``appear_from`` / ``hidden_after`` bound when the NPC stands at ``home``.
    ``gone_after`` is the last quest in which the character may speak or be
    talked to at all (death or departure); it is enforced on generated quests.
    Quest ids of the original 100-quest story use three digits (``q085``) and
    are remapped to the 1000-quest numbering by build_story; new ids use four
    digits (``q0405``)."""
    return {"name": name, "title": title, "model": model, "tint": tint, "scale": scale,
            "home": {"map": home[0], "marker": home[1]} if home else None,
            "appear_from": appear_from, "hidden_after": hidden_after, "gone_after": gone_after,
            "barks": list(barks)}


NPCS = {
    # ------------------------------------------------------------ Azure Cloud Sect
    YUN: npc("Yun Qingyao", "Sect Master of the Azure Cloud", "sect_master", ("sect", "MainHall"), None, 1.05,
             barks=["The clouds are restless today. So am I.",
                    "Cultivate diligently, disciple. Heaven favours the stubborn.",
                    "Every stone of this mountain was laid by someone braver than me."]),
    MO: npc("Mo Changfeng", "Outer Court Elder", "elder_male", ("sect", "HallSteps"), None, 1.0,
            hidden_after="q085", gone_after="q085",
            barks=["Back straight! A crooked spine makes a crooked meridian.",
                   "Hmph. You're late. The mountain doesn't wait, and neither do I.",
                   "When I was your age I climbed these steps on my hands. Both ways.",
                   "Tea? No. Training. Tea is for people who have finished training."]),
    BAI: npc("Bai Qiu", "Keeper of the Scripture Pagoda", "elder_male", ("sect", "Pagoda"), [1.15, 1.05, 0.8], 0.95,
             barks=["Shh. The books are sleeping.",
                    "Seven floors, ten thousand scrolls, and nobody returns anything on time.",
                    "If you fold a page corner, I will fold you."]),
    GU: npc("Gu Hanshan", "Elder of the Law Hall", "elder_male", ("sect", "ScholarRock"), [0.5, 0.45, 0.55], 1.08,
            hidden_after="q049", gone_after="q094",
            barks=["The precepts are not suggestions, disciple.",
                   "The Law Hall sees everything. Remember that.",
                   "Move along. I am thinking."]),
    HUA: npc("Hua Lian", "Elder of the Medicine Hall", "sect_master", ("sect", "HerbGarden"), [0.7, 1.1, 0.8], 0.97,
             barks=["Mind the moonbell sprouts. They bite.",
                    "A pill is only as honest as the hand that refines it.",
                    "You look pale. Eat something green. No, not that."]),
    HAN: npc("Han Xue", "Inner Disciple, Frost Sword Peak", "disciple_female", ("sect", "Pavilion"), [0.85, 0.95, 1.25], 1.0,
             barks=["Your stance is sloppy. Fix it before someone fixes it for you.",
                    "I don't do small talk. Medium talk, perhaps.",
                    "Breathe in for four, hold for four. You'll thank me later."]),
    WEI: npc("Wei Tong", "Senior Outer Disciple", "disciple_male", ("sect", "WeaponRack"), [1.1, 0.9, 0.7], 1.15,
             barks=["Training's done when the dummies cry. They never cry. So we never stop.",
                    "Have you eaten? You should eat. I should eat.",
                    "My sword is called Dumpling. Don't laugh. It knows."]),
    ZHAO: npc("Zhao Kang", "Outer Disciple of the Zhao Clan", "disciple_male", ("sect", "PlumGarden"), [1.3, 1.1, 0.6], 1.03,
              barks=["The plum blossoms bloom for those worthy of them.",
                     "Hmph. Still here?",
                     "One day my name will be carved on the Sect Stele. Yours can go underneath."]),
    LU: npc("Lu Ping", "Gate Disciple", "disciple_male", ("sect", "GateGuardPost"), None, 0.97,
            barks=["Halt! Who goes... oh, it's you. Carry on.",
                   "I wasn't sleeping. I was meditating with my eyes closed. And snoring.",
                   "Heard the latest? No? Neither have I. Slow day."]),
    QIAN: npc("Qian Duo", "Treasury Steward", "villager_male", ("sect", "IncenseBurner"), [0.7, 0.75, 1.1], 0.95,
              barks=["Every spirit stone has a name. Mostly mine.",
                     "Requisitions go in triplicate. Quadruplicate if you smile.",
                     "Do not touch the cauldron. The incense costs more than you do."]),
    MAN: npc("Xiao Man", "Medicine Hall Apprentice", "disciple_female", ("sect", "LotusPond"), None, 0.9,
             barks=["The carp know my name! Well, they know my crumbs.",
                    "Elder Hua says I have a gift. For dropping things.",
                    "Do you think lotus flowers get lonely at night?"]),
    SHI: npc("Xiao Shi", "Outer Disciple, rescued from the Abyss", "disciple_male", ("sect", "StoneBridge"), [0.9, 1.0, 0.9], 0.95,
             appear_from="q059",
             barks=["I still count the bars of a cage when I close my eyes. Then I open them.",
                    "My sister won't stop feeding me. I'm not complaining.",
                    "Thank you. I'll keep saying it until you're sick of it."]),
    # ------------------------------------------------------------ Whispering Bamboo Forest
    LAN: npc("The Bamboo Hermit", "Recluse of the Whispering Forest", "elder_male", ("bamboo_forest", "HermitHut"), [0.85, 0.95, 0.6], 0.93,
             barks=["The bamboo bends, and so it survives three hundred winters.",
                    "Tea is steeping. It has been steeping for a decade. Patience.",
                    "Tread softly. The forest remembers footsteps."]),
    YE: npc("Ye Wuming", "Masked Wanderer", "cultivator_male", None, [0.35, 0.35, 0.4], 1.05,
            barks=["...", "Names are chains. I lost mine on purpose.",
                   "Keep walking, lotus-bearer."]),
    TIE: npc("Tie Hu, Iron-Fang", "Bandit Chief", "bandit", None, None, 1.15,
             barks=["What are you looking at?", "Iron-Fang pays his debts. Eventually."]),
    # ------------------------------------------------------------ Qingshi Town
    ZHOU: npc("Magistrate Zhou Wen", "Magistrate of Qingshi", "villager_male", ("qingshi_town", "MagistrateHall"), [1.2, 0.6, 0.5], 1.0,
              barks=["The yamen is open to all petitions. Between the second and fourth bell.",
                     "Order! Order! Oh, it's quiet. Carry on.",
                     "An honest magistrate sleeps poorly. I sleep very poorly."]),
    FANG: npc("Madam Fang", "Proprietor of the Drunken Crane Inn", "villager_female", ("qingshi_town", "Inn"), None, 1.0,
              barks=["Wine, noodles or gossip? The gossip is free, the rest is not.",
                     "Immortals drink like fish and pay like cats.",
                     "Wipe your boots! This floor has seen emperors. Well, a tax collector."]),
    DU: npc("Du Ming", "Constable of Qingshi", "villager_male", ("qingshi_town", "TownGate"), [0.6, 0.6, 0.7], 1.05,
            barks=["Gate closes at dusk. Always has. Always will.",
                   "Trouble? Tell me. I'll write it down. Then I'll deal with it.",
                   "Keep your sword sheathed in town, cultivator."]),
    LIU: npc("Widow Liu", "Townswoman", "villager_female", ("qingshi_town", "Well"), [0.7, 0.7, 0.75], 0.95,
             barks=["The water's sweet this season. Take a cup.",
                    "Every face that passes, I look twice.",
                    "Heaven keeps its accounts. I keep mine."]),
    HONG: npc("Keeper Hong", "Keeper of the Town Temple", "villager_male", ("qingshi_town", "Temple"), [1.1, 1.0, 0.9], 0.97,
              hidden_after="q028", gone_after="q029",
              barks=["May the ancestors watch over you.",
                     "Incense for the lost? Half a copper. The ancestors accept discounts.",
                     "Such a strong young cultivator. Such vigorous blood."]),
    PAN: npc("Old Pan", "Ferryman of the Qing River", "villager_male", ("qingshi_town", "Riverside"), [0.8, 0.9, 1.0], 0.93,
             barks=["River's high. Fares are higher.", "Forty years on this water. It never lies to me.",
                    "Mind the third plank. It has opinions."]),
    JIN: npc("Jin Baoshan", "Master of the Merchant Guild", "villager_male", ("qingshi_town", "Warehouse"), [1.3, 1.15, 0.6], 1.02,
             barks=["Everything has a price. Friendship especially.",
                    "Crates, crates, crates. Mind the stamp, it's imported.",
                    "Business is business, immortal. Nothing personal."]),
    # ------------------------------------------------------------ Blood Moon Sect
    PATRIARCH: npc("Xue Wuji", "Patriarch of the Blood Moon", "blood_patriarch", None, None, 1.12,
                   barks=["Kneel.", "Three hundred years is a long time to be hungry."]),
    XUEMEI: npc("Xue Mei", "Crimson Elder of the Blood Moon", "demon_cultivator", None, [1.3, 0.7, 0.7], 1.0,
                gone_after="q059", barks=["How delicious you look.", "Run, little lamb. I do love a chase."]),
    DEMON: npc("Heart Demon", "Your Own Shadow", "demon_cultivator", None, [0.3, 0.3, 0.35], 1.0,
               barks=["...", "Look closer. It's you."]),
    # ------------------------------------------------------------ Celestial Sky Isles
    SAGE: npc("Qing Luan", "Star-Gazing Sage of the Sky Isles", "sect_master", ("sky_isles", "StarPavilion"), [0.75, 0.9, 1.3], 1.0,
              appear_from="q071",
              barks=["The stars do not lie. They merely exaggerate.",
                     "Sixty years since the isles last opened. You took your time.",
                     "Sit. Look up. Try not to fall off."]),
}

# ---------------------------------------------------------------- new cast (text-only)
NPCS.update({
    YAN: npc("Yan Tie", "Champion of Thunder Peak", "disciple_male", ("sect", "CliffEdge"), [0.75, 0.8, 1.0], 1.1,
             appear_from="q0261",
             barks=["I owe you my life and a rematch. The rematch can wait.",
                    "Thunder Peak trains at dawn. Thunder Peak also naps at noon.",
                    "Some days I still taste that pill. Bitter, like losing."]),
    LIUER: npc("Liu Er", "Widow Liu's Son", "villager_male", ("qingshi_town", "Farmland"), [0.85, 0.8, 0.7], 0.9,
               appear_from="q0221",
               barks=["Mother makes me carry the water now. I don't mind.",
                      "I can swim across the river and back. Twice, if nobody's counting.",
                      "When I grow up I'm going to climb the nine thousand steps."]),
    GOU: npc("Gou the Scarred", "Iron-Fang's Lieutenant", "bandit", None, [0.8, 0.6, 0.5], 1.08,
             gone_after="q0115",
             barks=["Scar? I got it arguing with a tiger. The tiger lost.", "Move along, sect brat."]),
    RUAN: npc("Ruan Jingtao", "Young Master of the Iron Scale Sect", "disciple_male", None, [0.55, 0.7, 0.6], 1.04,
              appear_from="q0221",
              barks=["The Iron Scale bends to no one. Mostly.", "Your mountain is very tall. Ours is wider."]),
    RUANHAI: npc("Ruan Hai", "Sect Master of the Iron Scale", "elder_male", None, [0.5, 0.65, 0.55], 1.1,
                 appear_from="q0221",
                 barks=["Scales do not rust, boy. Neither do grudges.", "Speak plainly. I am too old for riddles."]),
    JING: npc("Jing Xuan", "Abbess of the Moon-Well Nunnery", "sect_master", None, [0.9, 0.92, 1.12], 1.0,
              appear_from="q0501",
              barks=["The well reflects the moon, not the other way round.", "Mercy is a discipline, not a mood."]),
    TIANLU: npc("Zhao Tianlu", "Ancestor of the Zhao Clan", "elder_male", None, [1.25, 1.1, 0.65], 1.02,
                appear_from="q0221",
                barks=["The Zhao clan counts in centuries. And in gold.", "My grandson has your stubbornness. Regrettably."]),
    # --- the Seven Rungs of the Patriarch's Ladder
    RUNG1: npc("Luo Hui", "First Rung of the Patriarch's Ladder", "demon_cultivator", None, [0.62, 0.6, 0.64], 1.02,
               appear_from="q0660", gone_after="q0970",
               barks=["Ash remembers every fire.", "One rung is nothing. Seven is a road to heaven."]),
    RUNG2: npc("Tie Shan", "Second Rung, the Rust Monk", "demon_cultivator", None, [0.9, 0.55, 0.35], 1.1,
               appear_from="q0720", gone_after="q1055",
               barks=["All iron rusts. All vows rust.", "Pray with me. It won't help."]),
    RUNG3: npc("Jiu Rong", "Third Rung, Madam Ninefold", "demon_cultivator", None, [0.82, 0.5, 0.9], 1.0,
               appear_from="q1120", gone_after="q1135",
               barks=["I have nine faces. You'll like at least one.", "Fold, and fold, and fold again."]),
    RUNG4: npc("Kong Yi", "Fourth Rung, Brother Hollow", "demon_cultivator", None, [0.4, 0.45, 0.62], 1.06,
               appear_from="q1280", gone_after="q1295",
               barks=["I am empty. It is very restful.", "Your body is a house. I am looking to rent."]),
    RUNG5: npc("Wen Tu", "Fifth Rung, the Butcher of Wen", "bandit", None, [0.8, 0.32, 0.3], 1.14,
               appear_from="q1360", gone_after="q1375",
               barks=["Meat is meat.", "I weigh cultivators by the jin."]),
    RUNG6: npc("Si Rou", "Sixth Rung, Lady Silk", "sect_master", None, [1.2, 0.62, 0.72], 0.98,
               appear_from="q1520", gone_after="q1535",
               barks=["Every alliance is a web. I merely spin faster.", "Such lovely manners. Such soft throats."]),
    RUNG7: npc("Xue Chen", "Seventh Rung, the Patriarch's Shadow", "demon_cultivator", None, [0.36, 0.2, 0.26], 1.08,
               appear_from="q1635", gone_after="q1950",
               barks=["I was born in his shadow. I will die in yours.", "The moon is almost full."]),
})

for _id, _npc in NPCS.items():
    _v = NPC_VOICES.get(_id)
    # NPCs added for the 1000-quest saga speak only in text (no Piper casting).
    _npc["voice"] = None if _v is None else {"model": _v["model"], "speaker": _v["speaker"],
                                             "length_scale": _v["length_scale"], "noise_scale": _v["noise_scale"]}

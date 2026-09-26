"""How the chapter generator talks about places.

For every map marker: a short phrase used in objective text ("the herb
terraces"), and a few arrival narrations. Pools list the markers that suit
each objective type (the ones the original 100 quests proved walkable, plus a
few open spaces). Markers that are NPC homes are filtered out at generation
time when the NPC is present.
"""

NAMES = {
    "sect": {
        "SectGate": "the sect gate", "GateGuardPost": "the gate post", "FormationArray": "the formation plaza",
        "IncenseBurner": "the incense cauldron", "HallSteps": "the hall steps", "MainHall": "the main hall",
        "TrainingGround": "the training ground", "WeaponRack": "the weapon rack", "Pavilion": "the quiet pavilion",
        "Pagoda": "the scripture pagoda", "LotusPond": "the lotus pond", "StoneBridge": "the stone bridge",
        "PlumGarden": "the plum garden", "HerbGarden": "the herb terraces", "MoonGate": "the moon gate",
        "CliffEdge": "the cliff edge", "ScholarRock": "the scholar rock", "OuterPines": "the outer pines",
        "TeleportArray": "the teleport array", "PlayerSpawn": "the processional way",
    },
    "bamboo_forest": {
        "ForestPath": "the forest path", "OldBridge": "the old bridge", "Stream": "the stream",
        "HermitHut": "the hermit's hut", "HerbGrove": "the herb grove", "SpiritSpring": "the spirit spring",
        "WolfDen": "the wolf den", "BanditCamp": "the old bandit camp", "BanditLookout": "the lookout rock",
        "RuinsGate": "the ruins gate", "AncientShrine": "the ruined shrine", "RuinsInner": "the ruins courtyard",
        "Clearing": "the clearing", "TeleportArray": "the mossy array", "PlayerSpawn": "the forest edge",
    },
    "qingshi_town": {
        "TownGate": "the town gate", "MainStreet": "the main street", "MarketSquare": "the market square",
        "Inn": "the Drunken Crane", "Well": "the town well", "MagistrateHall": "the yamen",
        "Temple": "the town temple", "Riverside": "the docks", "BackAlley": "the back alley",
        "Warehouse": "the guild warehouse", "Graveyard": "the hill graves", "Farmland": "the terraced fields",
        "WatchTower": "the watchtower", "TeleportArray": "the roadside array", "PlayerSpawn": "the town road",
    },
    "blood_abyss": {
        "CanyonEntrance": "the canyon mouth", "BoneField": "the field of bones", "BloodPools": "the blood pools",
        "ObeliskRing": "the obelisk ring", "PrisonCages": "the old cages", "DemonCamp": "the war camp",
        "DemonGate": "the black gate", "FortressCourt": "the fortress court", "AltarOfBlood": "the altar",
        "PatriarchThrone": "the throne", "HeartMirror": "the Heart Mirror", "AbyssDepths": "the abyss depths",
        "TeleportArray": "the cracked array", "PlayerSpawn": "the canyon rim",
    },
    "sky_isles": {
        "CloudGate": "the cloud gate", "JadeBridge": "the jade bridge", "IsleOfWinds": "the Isle of Winds",
        "StarPavilion": "the star pavilion", "CelestialRuins": "the celestial ruins", "SerpentLair": "the serpent's isle",
        "SpiritVein": "the spirit vein", "ImmortalGarden": "the immortal garden", "TribulationPeak": "the tribulation peak",
        "AscensionStair": "the Ascension Stair", "TeleportArray": "the floating array", "PlayerSpawn": "the arrival platform",
    },
}

# objective-type pools per map (ordered by preference)
POOLS = {
    "sect": {
        "meet": ["SectGate", "FormationArray", "MoonGate", "CliffEdge", "OuterPines", "TrainingGround", "StoneBridge",
                 "HallSteps", "ScholarRock"],
        "fight": ["TrainingGround", "FormationArray", "OuterPines", "SectGate"],
        "gather": ["HerbGarden", "PlumGarden", "OuterPines", "LotusPond", "SectGate", "FormationArray"],
        "med": ["StoneBridge", "CliffEdge", "PlumGarden", "FormationArray", "MoonGate"],
        "prop": ["SectGate", "FormationArray", "Pavilion", "MainHall", "Pagoda", "MoonGate", "CliffEdge"],
        "reach": ["SectGate", "HallSteps", "OuterPines", "FormationArray", "MoonGate", "Pavilion", "CliffEdge",
                  "TrainingGround", "LotusPond", "PlumGarden", "HerbGarden", "MainHall", "Pagoda"],
    },
    "bamboo_forest": {
        "meet": ["ForestPath", "Clearing", "Stream", "AncientShrine", "OldBridge", "SpiritSpring", "BanditLookout"],
        "fight": ["HerbGrove", "WolfDen", "BanditCamp", "Clearing", "OldBridge", "RuinsGate", "RuinsInner", "AncientShrine"],
        "gather": ["HerbGrove", "WolfDen", "SpiritSpring", "BanditCamp", "OldBridge", "RuinsGate"],
        "med": ["SpiritSpring", "BanditLookout", "Clearing", "AncientShrine"],
        "prop": ["AncientShrine", "SpiritSpring", "WolfDen", "BanditCamp", "RuinsGate", "RuinsInner"],
        "reach": ["ForestPath", "OldBridge", "Stream", "HerbGrove", "SpiritSpring", "WolfDen", "BanditLookout",
                  "RuinsGate", "AncientShrine", "RuinsInner", "Clearing", "BanditCamp", "HermitHut"],
    },
    "qingshi_town": {
        "meet": ["MainStreet", "MarketSquare", "Graveyard", "Temple", "BackAlley", "Farmland", "WatchTower"],
        "fight": ["BackAlley", "Graveyard", "Riverside", "Warehouse", "MarketSquare", "TownGate", "MainStreet", "Farmland"],
        "gather": ["BackAlley", "Graveyard", "Warehouse", "Riverside", "MarketSquare", "Farmland"],
        "med": ["Temple", "WatchTower", "Graveyard"],
        "prop": ["Well", "Warehouse", "Graveyard", "TownGate", "WatchTower", "Temple"],
        "reach": ["MainStreet", "Riverside", "MarketSquare", "BackAlley", "WatchTower", "Graveyard", "Temple",
                  "Farmland", "TownGate", "Well", "Inn"],
    },
    "blood_abyss": {
        "meet": ["CanyonEntrance", "BoneField", "AbyssDepths", "ObeliskRing", "BloodPools"],
        "fight": ["BoneField", "BloodPools", "ObeliskRing", "DemonCamp", "AbyssDepths", "HeartMirror"],
        "gather": ["BoneField", "BloodPools", "ObeliskRing", "DemonCamp"],
        "med": ["BloodPools", "AbyssDepths", "HeartMirror"],
        "prop": ["ObeliskRing", "BoneField", "DemonCamp", "HeartMirror"],
        "reach": ["CanyonEntrance", "BoneField", "BloodPools", "DemonCamp", "HeartMirror", "ObeliskRing", "AbyssDepths"],
    },
    "sky_isles": {
        "meet": ["CloudGate", "IsleOfWinds", "ImmortalGarden", "JadeBridge", "CelestialRuins"],
        "fight": ["JadeBridge", "CelestialRuins", "SpiritVein", "SerpentLair", "ImmortalGarden"],
        "gather": ["IsleOfWinds", "CelestialRuins", "SpiritVein", "ImmortalGarden"],
        "med": ["IsleOfWinds", "CloudGate", "CelestialRuins"],
        "prop": ["StarPavilion", "CelestialRuins", "SpiritVein", "SerpentLair"],
        "reach": ["JadeBridge", "IsleOfWinds", "CelestialRuins", "ImmortalGarden", "SerpentLair", "CloudGate",
                  "SpiritVein", "StarPavilion"],
    },
}

# Arrival narration, a few moods per marker. Used when a reach objective has no authored lines.
ARRIVE = {
    "sect": {
        "SectGate": ["The paifang gate throws a long shadow down the steps. Somewhere below, a new candidate is groaning at step four thousand.",
                     "Gate disciples straighten as you pass. A few of them bow. You are still not used to that."],
        "FormationArray": ["The formation plaza hums underfoot, a thousand runes breathing in slow blue light.",
                           "Disciples cross the plaza in twos and threes, lowering their voices as they pass the array."],
        "HallSteps": ["The hall steps are worn into shallow bowls by three hundred years of hurrying feet.",
                      "Incense drifts down the hall steps. Above, the double eaves hold up the sky with practised ease."],
        "MainHall": ["Inside the main hall, the founder's tablet gleams. The faded green lotus beside it seems a little brighter today."],
        "OuterPines": ["Beyond the wall the pines grow close and dark, and the wind in them sounds like distant surf.",
                       "Needles crunch underfoot in the outer pines. Something small and watchful freezes, then flees."],
        "MoonGate": ["The round moon gate frames the western courtyard like a painting someone forgot to finish.",
                     "Wind whistles through the moon gate. On the far side, the herb terraces shiver green."],
        "Pavilion": ["The hexagonal pavilion is empty except for a teapot, still warm, and a single fallen plum petal."],
        "CliffEdge": ["The sea of clouds rolls below the cliff edge, white and endless, as if the mountain were a ship.",
                      "At the cliff edge the wind tugs at your robe. The world below is only cloud and the calls of cranes."],
        "TrainingGround": ["The training ground smells of sweat, sawdust and Wei Tong's lunch.",
                           "Straw dummies lean at tired angles across the training ground. One of them is wearing a hat."],
        "LotusPond": ["Carp rise to the surface of the lotus pond, hoping you are someone with crumbs."],
        "PlumGarden": ["Plum petals drift across the path. The garden is so quiet you can hear them land."],
        "HerbGarden": ["The herb terraces step down the slope in green stripes, each labelled in Elder Hua's stern hand."],
        "Pagoda": ["Seven tiers of scripture rise above you. From the fourth floor comes the sound of someone sneezing on dust."],
        "StoneBridge": ["From the top of the stone bridge the pond reflects the whole sect upside down, calmer than the original."],
        "ScholarRock": ["The Taihu scholar rock stands full of holes, as if the wind had tried to read it."],
        "IncenseBurner": ["The great bronze cauldron smoulders. Someone has written 'donations welcome' on it in chalk."],
    },
    "bamboo_forest": {
        "ForestPath": ["The forest path winds between green columns of bamboo. Light falls in long, trembling bars.",
                       "Bamboo creaks overhead like an old house settling. The path ahead forks, and forks again."],
        "OldBridge": ["The old bridge sags over the stream. Every plank has a different opinion about your weight."],
        "Stream": ["The stream chatters over its stones, too busy to notice you."],
        "HerbGrove": ["Sun pools in the herb grove. Spirit herbs glow faintly among the ferns, like embers in green ash."],
        "SpiritSpring": ["The spirit spring lies still and clear. The lotus pads turn slowly toward you, then toward your pendant."],
        "WolfDen": ["The wolf den gapes in the rock. Old bones, older claw marks, and a smell that makes the neck prickle."],
        "BanditLookout": ["From the lookout rock the whole valley opens below, bamboo rolling like a green sea."],
        "RuinsGate": ["The lotus archway of the ruins rises from the bamboo, its carved petals furred with moss."],
        "AncientShrine": ["Broken pillars ring the old shrine. The stele at its heart has outlasted three hundred winters and one hermit."],
        "RuinsInner": ["The green stone courtyard of the ruins is silent. Even the birds seem to land more carefully here."],
        "Clearing": ["The clearing opens like a held breath. Tall grass bends in a wind you cannot feel."],
        "BanditCamp": ["The old bandit camp is ash and broken crates now. A rusted cage door creaks in the breeze."],
        "HermitHut": ["Tea steam curls from the hermit's hut. It always does. Nobody has ever seen the fire."],
    },
    "qingshi_town": {
        "MainStreet": ["Qingshi's main street bustles: noodle sellers, water carriers, a dog stealing a dumpling with great dignity.",
                       "Shutters are open on the main street today. People nod at your robes instead of hiding from them."],
        "MarketSquare": ["The market square is a riot of awnings and haggling. Somebody is selling 'genuine immortal sandals'."],
        "Riverside": ["The Qing River slides past the docks, brown and patient. Old Pan's ferry creaks at its rope."],
        "BackAlley": ["The back alley is narrow and damp, and every window in it is watching you."],
        "WatchTower": ["From the watchtower the fields stretch gold to the hills, and the road runs white toward the mountain."],
        "Graveyard": ["The hill graves are quiet now. Fresh flowers lie on the tablets, and the blood-ink is long gone."],
        "Temple": ["The town temple smells of clean incense. A sparrow nests in the eaves, bold as a magistrate."],
        "Farmland": ["The terraced fields step down to the river. Farmers straighten, shade their eyes, and wave."],
        "TownGate": ["The town gate is scarred and patched, and the gate guards salute a little too eagerly."],
        "Well": ["The town well is ringed with gossip and wet stones. Widow Liu's bucket hangs ready."],
        "Inn": ["Laughter and the smell of wine spill out of the Drunken Crane. Madam Fang is shouting at someone, lovingly."],
    },
    "blood_abyss": {
        "CanyonEntrance": ["The crimson canyon opens its mouth. Warm, wet air rises from below, tasting of copper."],
        "BoneField": ["Bones crunch underfoot on the old plain. Dead trees claw at a sky the colour of a bruise.",
                      "The field of bones is silent. Even the wind here walks carefully."],
        "BloodPools": ["The blood pools steam and bubble. Pale lotus grows in them, beautiful and wrong."],
        "ObeliskRing": ["The broken obelisks lean together like old men sharing a secret."],
        "DemonCamp": ["The war camp's banners hang slack. The drums are silent, but the stone remembers them."],
        "HeartMirror": ["The Heart Mirror lies still and black. You do not look into it for long."],
        "AbyssDepths": ["At the bottom of the abyss the darkness is so thick it feels like weather."],
    },
    "sky_isles": {
        "JadeBridge": ["The jade bridge stretches over nothing at all, and the wind tests every step."],
        "IsleOfWinds": ["The pines of the Isle of Winds bow and rise, bow and rise, as if in endless greeting."],
        "CelestialRuins": ["Broken palace columns tower into the clouds, still warm from a fall ten thousand years ago."],
        "ImmortalGarden": ["Blossom trees taller than pagodas drop petals like warm snow on the immortal garden."],
        "SerpentLair": ["The serpent's isle is scarred with old coils. Storm-grey scales glint in the grass."],
        "CloudGate": ["The stone cloud gate frames nothing but sky, as if heaven were a room next door."],
        "SpiritVein": ["Crystals jut from the spirit vein, humming a note just below hearing."],
        "StarPavilion": ["The star pavilion's jade floor is inlaid with constellations. Some of them are moving."],
        "TribulationPeak": ["The summit altar is scorched black in rings, each one a cultivator who stood here and was answered."],
        "AscensionStair": ["The Ascension Stair climbs into cloud, each step made of light, none of them for you. Not yet."],
    },
}

# Generic arrival lines for any marker; {place} is its phrase.
ARRIVE_ANY = [
    "You reach {place}. For a moment everything is quiet, and then you notice the tracks.",
    "{Place} looks exactly as it should, which is what makes you uneasy.",
    "At {place} the air changes, heavy with qi and something older underneath.",
    "You slow at {place}, letting your senses spread like ripples on a pond.",
    "Somebody was here at {place} not long ago. The grass has not finished standing up.",
    "The path to {place} is longer than you remember. The view is worth it.",
]


def name(map_id, marker):
    return NAMES.get(map_id, {}).get(marker, marker)

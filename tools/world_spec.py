"""Single source of truth for the game world's identifiers.

Maps, their named markers, character models, NPC-capable models, enemy types,
collectible items, interactable props and cultivation realms. The map
builders (tools/maps), the story compiler (tools/story) and the Godot runtime
tests all validate against this file, so a quest can never reference a marker
or enemy that does not exist.

Coordinates are never stored here: each map builder places its markers and the
runtime snaps every marker to the ground with a downward ray cast.
"""

MAPS = {
    "sect": {
        "name": "Azure Cloud Sect",
        "music": "sect",
        "markers": {
            "PlayerSpawn": "processional way south of the sect gate",
            "TeleportArray": "jade teleport array east of the processional way, outside the gate",
            "SectGate": "just inside the paifang gate",
            "GateGuardPost": "beside the gate, where the gate disciples stand watch",
            "FormationArray": "centre of the glowing formation array in the plaza",
            "IncenseBurner": "in front of the great incense cauldron",
            "HallSteps": "foot of the main hall's front steps",
            "MainHall": "on the main hall terrace, before the doors",
            "TrainingGround": "among the training dummies west of the plaza",
            "WeaponRack": "by the weapon rack of the training ground",
            "Pavilion": "hexagonal pavilion in the north-west garden",
            "Pagoda": "at the foot of the seven-tier pagoda (the scripture library)",
            "LotusPond": "on the pond shore near the arched bridge",
            "StoneBridge": "top of the arched stone bridge",
            "PlumGarden": "plum blossom grove north-east, near the pagoda",
            "HerbGarden": "bamboo and herb terraces outside the west moon gate",
            "MoonGate": "the moon gate in the west courtyard wall",
            "CliffEdge": "the western cliff edge above the sea of clouds",
            "ScholarRock": "the tall Taihu scholar rock east of the plaza",
            "OuterPines": "pine woods south-east, outside the walls",
            "ElderQuarters": "the elder's private hall, near the plum garden",
            "AlchemyPavilion": "the alchemy pavilion by the herb terraces",
            "WeaponsHall": "the weapons hall beside the training ground",
            "DiscipleDormitory": "the outer disciples' dormitory east of the plaza",
            # -- the expanded mountain (ten times the old area): districts beyond the old walls
            "InnerSectGate": "the carved inner gate between the outer and inner sect",
            "OuterSectHall": "the outer sect's assembly hall, south-west below the walls",
            "MissionHall": "the mission hall with its notice boards of sect tasks",
            "ContributionPavilion": "the contribution pavilion where merit is exchanged for pills",
            "Refectory": "the long refectory hall where disciples eat",
            "OuterDormitories": "the rows of outer-disciple dormitories on the lower terraces",
            "LaundryStream": "the stream below the dormitories where robes are washed",
            "MartialStage": "the raised sparring stage of the martial arena",
            "ArenaStands": "the stone stands around the martial arena",
            "BellTower": "the great bell tower on the east ridge",
            "DrumTower": "the drum tower facing the bell tower across the plaza road",
            "FormationHall": "the formation hall ringed by rune pillars",
            "TreasureTower": "the nine-storey treasure tower, the sect's armoury of artefacts",
            "SwordPeakPath": "the switchback path climbing toward Sword Peak",
            "CableBridge": "the chain bridge across the gorge to Sword Peak",
            "SwordPeak": "the summit of Sword Peak, a windswept platform",
            "SwordTomb": "the sword tomb, a field of old blades thrust into the rock",
            "SwordWashPool": "the pool where swords are washed after the sword trials",
            "MedicineValley": "the terraced medicine valley east of the sect",
            "PillKilnYard": "the yard of the great pill kilns",
            "SpiritBeastGarden": "the spirit beast garden with its pens and ponds",
            "CraneRoost": "the crane roost on the pines above the beast garden",
            "Waterfall": "the foot of the Hundred-Chi Waterfall",
            "WaterfallCave": "the meditation cave behind the waterfall",
            "AncestorTombs": "the ancestral tombs, tortoise steles among cypresses",
            "ReflectionCliff": "the Cliff of Reflection, where disciples serve confinement",
            "TeaTerraces": "the spirit tea terraces on the southern slope",
            "SpiritOrchard": "the spirit peach orchard below the tea terraces",
            "SunriseTerrace": "the sunrise terrace on the eastern edge of the mountain",
            "CoreDisciplesCourt": "the core disciples' courtyard of private cottages",
            "MountainRoad": "the mountain road winding up from the valley below",
            "StoneSteps": "the long stone stairway between the lower and upper terraces",
        },
    },
    "bamboo_forest": {
        "name": "Whispering Bamboo Forest",
        "music": "forest",
        "markers": {
            "PlayerSpawn": "forest edge where the path enters",
            "TeleportArray": "moss-covered teleport array at the forest edge",
            "ForestPath": "the winding dirt path halfway into the forest",
            "OldBridge": "wooden bridge across the forest stream",
            "Stream": "stream bank, shallow water and river stones",
            "HermitHut": "a thatched hermit's hut in a quiet clearing",
            "HerbGrove": "sun-dappled grove with glowing spirit herbs",
            "SpiritSpring": "a spring pool with lotus and glowing water",
            "WolfDen": "rocky hollow and cave mouth where spirit wolves lair",
            "BanditCamp": "bandit camp: tents, campfire, crates",
            "BanditLookout": "a rocky rise overlooking the bandit camp",
            "RuinsGate": "stone archway of the ancient ruins",
            "AncientShrine": "ruined shrine with broken pillars and a stone stele",
            "RuinsInner": "inner courtyard of the ruins, an open arena",
            "Clearing": "a wide open clearing in the bamboo",
            # -- the expanded forest (ten times the old area)
            "WoodcutterCamp": "a woodcutters' camp with stacked bamboo and a saw pit",
            "CharcoalKilns": "the domed charcoal kilns in a smoky hollow",
            "BambooVillage": "a small stilt-house village of bamboo cutters",
            "VillageShrine": "the earth-god shrine at the heart of the bamboo village",
            "MistyLake": "the shore of the misty lake",
            "LakePavilion": "a pavilion on stilts over the misty lake",
            "Waterwheel": "a creaking mill waterwheel on the stream",
            "FishingJetty": "a fishing jetty jutting into the lake",
            "PandaGrove": "a grove of giant bamboo where iron-eating bears feed",
            "TigerRidge": "a rocky ridge scarred by claw marks",
            "BanyanGiant": "the giant banyan tree whose roots form a hall",
            "SpiderHollow": "a dark hollow webbed with silk",
            "PoisonMarsh": "the poison marsh of bubbling green water",
            "MushroomRing": "a ring of glowing lingzhi mushrooms",
            "ForestWatchpost": "the sect's forest watchpost, a tower on stilts",
            "HunterLodge": "a hunter's lodge with drying pelts",
            "BuriedTemple": "a temple half-swallowed by the earth and roots",
            "TempleUndercroft": "the sunken courtyard before the buried temple's doors",
            "StoneBuddhas": "a cliff face carved with weathered stone buddhas",
            "CliffPath": "a narrow path along the cliff of carved buddhas",
            "WaterfallGorge": "the gorge where the stream falls into a pool",
            "ForestCrossroads": "a crossroads marked with a wayside shrine",
            "OldBattlefield": "an old battlefield of rusted weapons and mounds",
            "HiddenValley": "a hidden valley of blossoming wild plum",
            "EchoCave": "the mouth of the echo cave",
            "SmugglersTrail": "the smugglers' trail through the thickest bamboo",
            "RopeBridge": "a rope bridge over the waterfall gorge",
            "AlchemistCottage": "a wandering alchemist's cottage with drying racks",
            "SacredSpring": "a second spring, walled and sacred to the villagers",
            "ForestGate": "the far forest gate where the road leaves for the south",
        },
    },
    "qingshi_town": {
        "name": "Qingshi Town",
        "music": "town",
        "markers": {
            "PlayerSpawn": "the road outside the town gate",
            "TeleportArray": "a small teleport array by the road outside town",
            "TownGate": "the wooden town gate",
            "MainStreet": "middle of the main street",
            "MarketSquare": "market square among the stalls",
            "Inn": "in front of the Drunken Crane Inn",
            "Well": "the town well",
            "MagistrateHall": "the magistrate's yamen courtyard",
            "Temple": "the small town temple / shrine pavilion",
            "Riverside": "the river bank and docks",
            "BackAlley": "a narrow back alley between houses",
            "Warehouse": "the merchant guild warehouse yard with crates",
            "Graveyard": "the hillside graveyard outside the walls",
            "Farmland": "the terraced fields beyond the east wall",
            "WatchTower": "the wooden watchtower on the town wall",
            "TeaHouse": "the teahouse south-east of the market square",
            "Blacksmith": "the blacksmith's forge south-east of the market square",
            "HerbShop": "the herb shop south-east of the market square",
            # -- the expanded town (ten times the old area)
            "NorthGate": "the north gate of the enlarged walls",
            "EastGate": "the east gate toward the farmlands",
            "SouthMarket": "the southern night market of paper lanterns",
            "Granary": "the county granary on its stone plinth",
            "SilkWorkshop": "the silk workshop with its looms and dye vats",
            "DyeYard": "the dye yard hung with drying cloth",
            "Pharmacy": "the great pharmacy of the Wang family",
            "Academy": "the county academy where scholars sit the exams",
            "ExamHall": "the examination cells behind the academy",
            "MerchantManor": "the merchant guild master's manor gate",
            "ManorGarden": "the manor's garden with its rockery and pond",
            "OperaStage": "the open-air opera stage by the temple fair",
            "TempleFair": "the temple fair square of stalls and performers",
            "CityGodTemple": "the City God temple with its incense court",
            "BellPavilion": "the drum-and-bell pavilion over the crossroads",
            "Bathhouse": "the public bathhouse",
            "Pawnshop": "the pawnshop with its tall counter",
            "Tavern": "the rowdy riverside tavern",
            "Brewery": "the rice-wine brewery with its jars",
            "Mill": "the watermill at the river bend",
            "BoatYard": "the boat yard on the riverbank",
            "LowerDocks": "the lower docks where the grain barges tie up",
            "StoneBridgeTown": "the humpbacked stone bridge over the canal",
            "Canal": "the canal walk lined with willows",
            "Orphanage": "the temple orphanage and its courtyard",
            "PostStation": "the post station with its stables",
            "Barracks": "the county militia barracks",
            "ExecutionGround": "the execution ground outside the west wall",
            "Tannery": "the tannery downstream of everything else",
            "Kilns": "the pottery kilns on the clay bank",
        },
    },
    "blood_abyss": {
        "name": "Blood Moon Abyss",
        "music": "abyss",
        "markers": {
            "PlayerSpawn": "rim of the canyon where the descent begins",
            "TeleportArray": "a cracked teleport array on the canyon rim",
            "CanyonEntrance": "the mouth of the crimson canyon",
            "BoneField": "a plain of bones and dead trees",
            "BloodPools": "steaming pools of blood-red water",
            "ObeliskRing": "a ring of demonic obelisks with glowing runes",
            "PrisonCages": "iron cages holding captured cultivators",
            "DemonCamp": "Blood Moon Sect war camp with tents and banners",
            "DemonGate": "the black fortress gate of the Blood Moon Sect",
            "FortressCourt": "the courtyard inside the demon gate",
            "AltarOfBlood": "the great blood altar on a raised dais",
            "PatriarchThrone": "the patriarch's throne platform, a boss arena",
            "HeartMirror": "a still black pool that reflects one's heart demon",
            "AbyssDepths": "the deepest point of the abyss, a wide arena",
            # -- the expanded abyss (ten times the old area)
            "BloodRiver": "the bank of the river of blood",
            "BoneBridge": "a bridge built of giant bones across the blood river",
            "SlaveMines": "the slave mines cut into the canyon wall",
            "MineShaft": "the mouth of the deepest mine shaft",
            "ForgeOfSouls": "the soul forge with its screaming bellows",
            "Barracks": "the Blood Moon barracks of black tents",
            "TrainingPit": "the training pit where demon disciples fight",
            "BeastPens": "the pens of corrupted beasts",
            "PoisonGarden": "the garden of poison flowers",
            "SkullTower": "the tower of skulls on a spur of rock",
            "WailingCliffs": "the wailing cliffs where the wind screams",
            "AshPlains": "the grey ash plains under the red moon",
            "LavaFalls": "the falls where molten rock pours into the abyss",
            "ObsidianSpires": "a forest of obsidian spires",
            "SacrificePit": "the sacrificial pit ringed with chains",
            "DemonLibrary": "the forbidden library of the Blood Moon",
            "ElderPalace": "the palace of the demon elders",
            "ShadowMarket": "the shadow market where demonic cultivators trade",
            "BloodMoonShrine": "the shrine to the Blood Moon under the open sky",
            "CorpseForest": "the forest of hanged corpses and black trees",
            "RuinedSectGate": "the ruined gate of a sect the Blood Moon destroyed",
            "RuinedSectHall": "the burned hall of the destroyed sect",
            "ChainBridge": "a chain bridge over a bottomless chasm",
            "WatchSpire": "the watch spire on the canyon wall",
            "SealStones": "the old seal stones of the Verdant Lotus",
            "GhostVillage": "a village of ghosts and empty houses",
            "RedMoonTerrace": "the terrace where the red moon hangs largest",
            "CaveOfEchoes": "a cave whose walls repeat your worst thoughts",
            "SulphurVents": "yellow sulphur vents hissing steam",
            "BoneThrone": "the old bone throne of the first patriarch",
        },
    },
    "sky_isles": {
        "name": "Celestial Sky Isles",
        "music": "sky",
        "markers": {
            "PlayerSpawn": "arrival platform of the first isle",
            "TeleportArray": "a floating teleport array on the first isle",
            "CloudGate": "a stone gate framing the sea of clouds",
            "JadeBridge": "the long jade bridge between the first two isles",
            "IsleOfWinds": "a wind-swept isle with pines",
            "StarPavilion": "a pavilion used for star-gazing",
            "CelestialRuins": "broken palace columns and a dais",
            "SerpentLair": "a broad isle arena where the Jiao serpent dwells",
            "SpiritVein": "a crystal outcrop where spirit stones grow",
            "ImmortalGarden": "an overgrown garden of blossom trees",
            "TribulationPeak": "the summit altar where heavenly tribulation strikes",
            "AscensionStair": "the stair ascending toward the heavens",
            # -- the expanded sky isles (ten times the old area)
            "CrystalIsle": "an isle of singing crystal",
            "LotusLake": "a lake of golden lotus on a high isle",
            "WaterfallIsle": "an isle whose waterfall pours into the clouds",
            "PhoenixNest": "the great phoenix nest on a burnt crag",
            "CraneIsle": "the isle of the celestial cranes",
            "MoonIsle": "an isle of silver sand under a pale moon",
            "SunAltar": "the golden sun altar",
            "ThunderIsle": "the isle where lightning never stops",
            "RainbowBridge": "a bridge of seven-coloured light between isles",
            "ChainIsles": "a chain of small isles linked by stepping stones",
            "ImmortalPalace": "the gate of the Immortal Palace",
            "PalaceCourt": "the palace's inner court of white jade",
            "HallOfRecords": "the hall of heavenly records",
            "StarObservatory": "the armillary observatory at the top of a spire",
            "WindTemple": "the temple of the four winds",
            "CloudHarbour": "the cloud harbour where sky ships once docked",
            "SkyShipWreck": "the wreck of a sky ship on a lonely isle",
            "DragonBones": "the bleached bones of a true dragon",
            "PeachGarden": "the garden of the peaches of immortality",
            "JadeTerraces": "the jade rice terraces tended by spirit servants",
            "HermitIsle": "a tiny isle with a single hermit's hut",
            "MirrorLake": "a lake that mirrors the sky perfectly",
            "FloatingForest": "an isle forest of trees with roots in the air",
            "SealOfHeaven": "the seal of heaven, a great stone disc",
            "GateOfHeaven": "the southern gate of heaven, closed for an age",
            "SwordIsle": "an isle of flying swords circling a spire",
            "ElixirSpring": "the spring of the elixir of life",
            "StormCloudPlateau": "a plateau over the storm clouds",
            "LanternIsle": "an isle of floating sky lanterns",
            "TreeOfAges": "the tree of ages whose crown touches the stars",
        },
    },
    # -- building interiors, entered through a door on the map above (see
    # godot/scripts/world/doors.gd) -----------------------------------------
    "sect_main_hall": {
        "name": "Sect Main Hall",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the great doors", "ExitDoor": "the doors back to the plaza",
                    "TeleportArray": "the doors back to the plaza", "ThroneDais": "before the sect master's throne"},
    },
    "elder_quarters": {
        "name": "Elder's Quarters",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the quarters", "ExitDoor": "the door back to the sect",
                    "TeleportArray": "the door back to the sect", "MeditationMat": "the raised meditation mat"},
    },
    "scripture_pavilion": {
        "name": "Scripture Pavilion",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the pagoda", "ExitDoor": "the door back to the sect",
                    "TeleportArray": "the door back to the sect", "BookShelves": "the tall scroll shelves"},
    },
    "alchemy_pavilion": {
        "name": "Alchemy Pavilion",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the pavilion", "ExitDoor": "the door back to the sect",
                    "TeleportArray": "the door back to the sect", "PillFurnace": "the fire-lit pill furnace"},
    },
    "weapons_hall": {
        "name": "Weapons Hall",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the hall", "ExitDoor": "the door back to the training ground",
                    "TeleportArray": "the door back to the training ground",
                    "ArmoryRacks": "the sparring ring among the weapon racks"},
    },
    "disciple_dormitory": {
        "name": "Disciple Dormitory",
        "music": "sect",
        "markers": {"PlayerSpawn": "just inside the dormitory", "ExitDoor": "the door back to the sect",
                    "TeleportArray": "the door back to the sect", "Dormitory": "the row of disciple bunks"},
    },
    "qingshi_inn": {
        "name": "Drunken Crane Inn",
        "music": "town",
        "markers": {"PlayerSpawn": "just inside the inn", "ExitDoor": "the door back to the street",
                    "TeleportArray": "the door back to the street", "BarCounter": "the innkeeper's bar counter"},
    },
    "qingshi_teahouse": {
        "name": "Teahouse",
        "music": "town",
        "markers": {"PlayerSpawn": "just inside the teahouse", "ExitDoor": "the door back to the street",
                    "TeleportArray": "the door back to the street", "TeaCounter": "the tea serving counter"},
    },
    "qingshi_blacksmith": {
        "name": "Blacksmith",
        "music": "town",
        "markers": {"PlayerSpawn": "just inside the smithy", "ExitDoor": "the door back to the street",
                    "TeleportArray": "the door back to the street", "Forge": "the blacksmith's forge and anvil"},
    },
    "qingshi_herb_shop": {
        "name": "Herb Shop",
        "music": "town",
        "markers": {"PlayerSpawn": "just inside the shop", "ExitDoor": "the door back to the street",
                    "TeleportArray": "the door back to the street", "HerbCounter": "the apothecary's counter"},
    },
    "hidden_vault": {
        "name": "Hidden Vault",
        "music": "forest",
        "markers": {"PlayerSpawn": "just inside the vault", "ExitDoor": "the hidden door back to the shrine",
                    "TeleportArray": "the hidden door back to the shrine",
                    "VaultTreasure": "the piled chests and loose gold"},
    },
    "celestial_pavilion": {
        "name": "Celestial Sanctum",
        "music": "sky",
        "markers": {"PlayerSpawn": "just inside the sanctum", "ExitDoor": "the door back to the pavilion",
                    "TeleportArray": "the door back to the pavilion", "StarChart": "the floating jade star-dais"},
    },
    "blood_abyss_shrine": {
        "name": "Ancient Shrine",
        "music": "abyss",
        "markers": {"PlayerSpawn": "just inside the ruin", "ExitDoor": "the door back to the altar",
                    "TeleportArray": "the door back to the altar", "RelicAltar": "the smaller relic altar"},
    },
}

# Humanoids share the 24-bone cultivator rig and the full humanoid animation set.
HUMANOID_ANIMS = ["idle", "walk", "run", "salute", "cast", "attack", "hit", "death", "meditate", "talk"]
# The two protagonists carry the extended move set (blender/xianxia/moves.py).
PROTAGONISTS = ["cultivator_male", "cultivator_female"]
PROTAGONIST_MIN_ANIMS = 100
# Creatures have their own rigs.
CREATURE_ANIMS = {
    "spirit_wolf": ["idle", "walk", "run", "attack", "hit", "death"],
    "jiao_serpent": ["idle", "walk", "run", "attack", "hit", "death"],
}

# model id -> description. GLB lives at godot/assets/characters/<model>.glb
MODELS = {
    "cultivator_male": "player: Lin Feng, white disciple robe",
    "cultivator_female": "player: Su Yue, plum-blossom robe",
    "elder_male": "old man, grey hair and beard, dark teal elder robe",
    "sect_master": "dignified woman, white and gold robe, silver crown",
    "disciple_male": "outer disciple, grey-blue robe",
    "disciple_female": "outer disciple, pale green robe",
    "villager_male": "commoner, short brown robe, hat",
    "villager_female": "commoner woman, ochre robe, headscarf",
    "bandit": "rogue cultivator, dark leather, red headband",
    "demon_cultivator": "Blood Moon disciple, black and crimson robe, pale skin",
    "blood_patriarch": "towering demonic patriarch, horned crown, white hair",
    "stone_golem": "animated stone guardian (humanoid rig)",
    "spirit_wolf": "spirit wolf (quadruped rig)",
    "jiao_serpent": "flood dragon serpent (spine rig)",
}
NPC_MODELS = ["elder_male", "sect_master", "disciple_male", "disciple_female",
              "villager_male", "villager_female", "cultivator_male", "cultivator_female",
              "bandit", "demon_cultivator", "blood_patriarch"]

# enemy id -> model, the runtime scales/tints them and sets stats
ENEMIES = {
    "spirit_wolf": "spirit_wolf",
    "corrupted_wolf": "spirit_wolf",
    "wolf_king": "spirit_wolf",            # boss
    "bandit": "bandit",
    "bandit_chief": "bandit",              # boss
    "training_puppet": "stone_golem",
    "sparring_disciple": "disciple_male",
    "tournament_champion": "disciple_male",  # boss
    "demon_cultivator": "demon_cultivator",
    "blood_guard": "demon_cultivator",
    "demon_elder": "demon_cultivator",     # boss
    "blood_patriarch": "blood_patriarch",  # boss
    "stone_golem": "stone_golem",
    "ancient_guardian": "stone_golem",     # boss
    "jiao_serpent": "jiao_serpent",        # boss
    "heart_demon": "player",               # boss: a shadow of the player
    # --- added for the 1000-quest saga (volumes II-X)
    "rogue_cultivator": "bandit",
    "iron_scale_disciple": "disciple_male",
    "void_wraith": "demon_cultivator",
    "thunder_wolf": "spirit_wolf",
    "celestial_sentinel": "stone_golem",
    "rung_deacon": "demon_cultivator",     # boss: a Rung of the Patriarch's Ladder
    "void_colossus": "stone_golem",        # boss
    # --- waves of a heavenly tribulation (objective type "tribulation")
    "tribulation_beast": "spirit_wolf",    # a beast of lightning
    "heart_shade": "player",               # a lesser shadow of the player
}
BOSSES = {"wolf_king", "bandit_chief", "tournament_champion", "demon_elder", "blood_patriarch",
          "ancient_guardian", "jiao_serpent", "heart_demon", "rung_deacon", "void_colossus"}

# collectible item id -> display name
ITEMS = {
    "spirit_herb": "Spirit Herb",
    "spirit_stone": "Spirit Stone",
    "jade_slip": "Jade Slip",
    "wolf_fang": "Spirit Wolf Fang",
    "blood_lotus": "Blood Lotus",
    "demon_core": "Demon Core",
    "star_iron": "Star Iron",
    "thunder_crystal": "Thunder Crystal",
    "cloud_silk": "Cloud Silk",
    "phoenix_feather": "Phoenix Feather",
    "medicine": "Medicine Bundle",
    "letter": "Sealed Letter",
    "lantern_oil": "Lantern Oil",
    "rune_fragment": "Rune Fragment",
    "void_shard": "Void Shard",
    "spirit_pill": "Spirit Pill",
    "incense": "Incense Bundle",
    "tribulation_jade": "Tribulation Jade",
}

# interactable prop id -> GLB under godot/assets/environment (None = glowing seal only)
PROPS = {
    "stone_stele": "stone_stele",
    "treasure_chest": "treasure_chest",
    "blood_altar": "blood_altar",
    "demon_obelisk": "demon_obelisk",
    "prison_cage": "prison_cage",
    "jade_slip": "jade_slip",
    "bronze_bell": "bronze_bell",
    "spirit_stone": "spirit_stone",
    "teleport_array": "teleport_array",
    "seal": None,
    # -- quest props added with the expanded world (blender/xianxia/quest_props.py)
    "notice_board": "notice_board",
    "ancestral_tablet": "ancestral_tablet",
    "pill_furnace": "pill_furnace",
    "sword_in_stone": "sword_in_stone",
    "tortoise_stele": "tortoise_stele",
    "guardian_lion": "guardian_lion",
    "bronze_ding": "bronze_ding",
    "bronze_mirror": "bronze_mirror",
    "spirit_lamp": "spirit_lamp",
    "scroll_rack": "scroll_rack",
    "war_drum": "war_drum",
    "sealed_coffin": "sealed_coffin",
    "offering_table": "offering_table",
    "rune_pillar": "rune_pillar",
    "armillary_sphere": "armillary_sphere",
    "medicine_cabinet": "medicine_cabinet",
    "wine_jars": "wine_jars",
    "loom": "loom",
    "map_table": "map_table",
    "crane_statue": "crane_statue",
    "spirit_fountain": "spirit_fountain",
    "puppet_frame": "puppet_frame",
    "herb_drying_rack": "herb_drying_rack",
    "chain_anchor": "chain_anchor",
    "soul_lantern": "soul_lantern",
    "abacus_desk": "abacus_desk",
    "fishing_boat": "fishing_boat",
    "wishing_tree": "wishing_tree",
    "jade_screen": "jade_screen",
    "stone_tablet_array": "stone_tablet_array",
}

# Every collectible has its own model: godot/assets/items/<item id>.glb
# (blender/xianxia/items.py). Pickups fall back to a glowing primitive only if
# the GLB is missing.
ITEM_MODEL_DIR = "res://assets/items"

# Mortal, the ten major stages of cultivation, then Immortal Ascension. The
# main story has one volume per major stage (volume v breaks through into
# REALMS[v] at the end of its first chapter).
REALMS = [
    "Mortal",
    "Qi Condensation",
    "Foundation Establishment",
    "Core Formation",
    "Nascent Soul",
    "Soul Transformation",
    "Spirit Severing",
    "Void Refinement",
    "Body Integration",
    "Mahayana",
    "Tribulation Transcendence",
    "Immortal Ascension",
]
# Ten minor stages within every major realm: chapter c of a volume ends at
# minor stage c. STAGES[0] is unused (Mortal and Immortal Ascension have none).
STAGES = ["", "1st Layer", "2nd Layer", "3rd Layer", "4th Layer", "5th Layer", "6th Layer", "7th Layer",
          "8th Layer", "9th Layer", "Great Perfection"]
# how minor stages group in the UI: 1-3 Early, 4-6 Middle, 7-9 Late, 10 Great Perfection
STAGE_GROUPS = ["", "Early", "Early", "Early", "Middle", "Middle", "Middle", "Late", "Late", "Late",
                "Great Perfection"]

# The nine alignments: a Law<->Chaos axis and a Good<->Evil axis, each -100..100.
# A score of ALIGN_THRESHOLD or more leans lawful/good, -ALIGN_THRESHOLD or less chaotic/evil.
ALIGN_RANGE = 100
ALIGN_THRESHOLD = 25
ALIGN_LAW = ["lawful", "neutral", "chaotic"]
ALIGN_MORAL = ["good", "neutral", "evil"]
ALIGNMENTS = ["%s_%s" % (a, b) for a in ALIGN_LAW for b in ALIGN_MORAL]

OBJECTIVE_TYPES = ["talk", "reach", "defeat", "collect", "meditate", "interact", "cinematic", "tribulation"]

def as_dict():
    return {
        "maps": {k: {"name": v["name"], "music": v["music"], "markers": sorted(v["markers"])}
                 for k, v in MAPS.items()},
        "humanoid_anims": HUMANOID_ANIMS,
        "creature_anims": CREATURE_ANIMS,
        "models": sorted(MODELS),
        "enemies": ENEMIES,
        "bosses": sorted(BOSSES),
        "items": ITEMS,
        "props": PROPS,
        "item_model_dir": ITEM_MODEL_DIR,
        "realms": REALMS,
        "stages": STAGES,
        "stage_groups": STAGE_GROUPS,
        "alignments": ALIGNMENTS,
        "align_range": ALIGN_RANGE,
        "align_threshold": ALIGN_THRESHOLD,
    }


if __name__ == "__main__":
    # python tools/world_spec.py [--check]  ->  godot/data/world.json for the runtime
    import json
    import sys
    from pathlib import Path
    out = Path(__file__).resolve().parents[1] / "godot" / "data" / "world.json"
    text = json.dumps(as_dict(), indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text() != text:
            sys.exit(f"{out} is out of date: run python tools/world_spec.py")
        print("world.json up to date")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}")

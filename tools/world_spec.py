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
        },
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
}
BOSSES = {"wolf_king", "bandit_chief", "tournament_champion", "demon_elder", "blood_patriarch",
          "ancient_guardian", "jiao_serpent", "heart_demon"}

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
}

REALMS = [
    "Mortal",
    "Qi Condensation",
    "Foundation Establishment",
    "Core Formation",
    "Nascent Soul",
    "Soul Transformation",
    "Void Refinement",
    "Tribulation Transcendence",
    "Immortal Ascension",
]

OBJECTIVE_TYPES = ["talk", "reach", "defeat", "collect", "meditate", "interact", "cinematic"]


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
        "realms": REALMS,
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

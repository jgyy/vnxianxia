class_name Doors
extends RefCounted
## Static registry of door links between an exterior map and a building
## interior. Keyed by the map the player is standing on, then by the marker
## name that acts as the door; the value says which map/marker stepping
## through it leads to. Every interior links back with an "ExitDoor" marker.
##
## game.gd checks proximity to these markers the same way it checks the
## jade teleport array, and calls Game.load_map()/enter_door() rather than
## the travel menu, so interiors never appear as travel-menu destinations.

const LINKS := {
	"sect": {
		"MainHall": {"to": "sect_main_hall", "spawn": "PlayerSpawn", "label": "Enter the Main Hall"},
		"ElderQuarters": {"to": "elder_quarters", "spawn": "PlayerSpawn", "label": "Enter the Elder's Quarters"},
		"Pagoda": {"to": "scripture_pavilion", "spawn": "PlayerSpawn", "label": "Enter the Scripture Pavilion"},
		"AlchemyPavilion": {"to": "alchemy_pavilion", "spawn": "PlayerSpawn", "label": "Enter the Alchemy Pavilion"},
		"WeaponsHall": {"to": "weapons_hall", "spawn": "PlayerSpawn", "label": "Enter the Weapons Hall"},
		"DiscipleDormitory": {"to": "disciple_dormitory", "spawn": "PlayerSpawn", "label": "Enter the Disciple Dormitory"},
	},
	"qingshi_town": {
		"Inn": {"to": "qingshi_inn", "spawn": "PlayerSpawn", "label": "Enter the Drunken Crane Inn"},
		"TeaHouse": {"to": "qingshi_teahouse", "spawn": "PlayerSpawn", "label": "Enter the teahouse"},
		"Blacksmith": {"to": "qingshi_blacksmith", "spawn": "PlayerSpawn", "label": "Enter the blacksmith"},
		"HerbShop": {"to": "qingshi_herb_shop", "spawn": "PlayerSpawn", "label": "Enter the herb shop"},
	},
	"bamboo_forest": {
		"AncientShrine": {"to": "hidden_vault", "spawn": "PlayerSpawn", "label": "Push open the shrine's hidden door",
						  "min_realm": "Foundation Establishment"},
	},
	"sky_isles": {
		"StarPavilion": {"to": "celestial_pavilion", "spawn": "PlayerSpawn", "label": "Enter the celestial sanctum"},
	},
	"blood_abyss": {
		"AltarOfBlood": {"to": "blood_abyss_shrine", "spawn": "PlayerSpawn", "label": "Descend into the ancient shrine"},
	},
	"sect_main_hall": {"ExitDoor": {"to": "sect", "spawn": "MainHall", "label": "Leave the Main Hall"}},
	"elder_quarters": {"ExitDoor": {"to": "sect", "spawn": "ElderQuarters", "label": "Leave the Elder's Quarters"}},
	"scripture_pavilion": {"ExitDoor": {"to": "sect", "spawn": "Pagoda", "label": "Leave the Scripture Pavilion"}},
	"alchemy_pavilion": {"ExitDoor": {"to": "sect", "spawn": "AlchemyPavilion", "label": "Leave the Alchemy Pavilion"}},
	"weapons_hall": {"ExitDoor": {"to": "sect", "spawn": "WeaponsHall", "label": "Leave the Weapons Hall"}},
	"disciple_dormitory": {"ExitDoor": {"to": "sect", "spawn": "DiscipleDormitory", "label": "Leave the Dormitory"}},
	"qingshi_inn": {"ExitDoor": {"to": "qingshi_town", "spawn": "Inn", "label": "Leave the inn"}},
	"qingshi_teahouse": {"ExitDoor": {"to": "qingshi_town", "spawn": "TeaHouse", "label": "Leave the teahouse"}},
	"qingshi_blacksmith": {"ExitDoor": {"to": "qingshi_town", "spawn": "Blacksmith", "label": "Leave the blacksmith"}},
	"qingshi_herb_shop": {"ExitDoor": {"to": "qingshi_town", "spawn": "HerbShop", "label": "Leave the herb shop"}},
	"hidden_vault": {"ExitDoor": {"to": "bamboo_forest", "spawn": "AncientShrine", "label": "Leave the vault"}},
	"celestial_pavilion": {"ExitDoor": {"to": "sky_isles", "spawn": "StarPavilion", "label": "Leave the sanctum"}},
	"blood_abyss_shrine": {"ExitDoor": {"to": "blood_abyss", "spawn": "AltarOfBlood", "label": "Leave the shrine"}},
}

## Interior map ids: never shown in the teleport array's travel menu, and
## their jade-array marker (used only to orient the player on spawn) never
## responds to "use the teleport array".
const INTERIORS := [
	"sect_main_hall", "elder_quarters", "scripture_pavilion", "alchemy_pavilion", "weapons_hall",
	"disciple_dormitory", "qingshi_inn", "qingshi_teahouse", "qingshi_blacksmith", "qingshi_herb_shop",
	"hidden_vault", "celestial_pavilion", "blood_abyss_shrine",
]


## The door link (if any) starting at `marker` on `map_id`.
static func link_at(map_id: String, marker: String):
	var m: Dictionary = LINKS.get(map_id, {})
	return m.get(marker)


## Every door marker name placed on `map_id`.
static func doors_on(map_id: String) -> Array:
	return LINKS.get(map_id, {}).keys()

"""Heavenly tribulations: every major breakthrough (the last quest of each
volume's first chapter) calls down one, an objective of type "tribulation".

Lightning falls in volleys at the player, who survives by enduring (meditating
halves the damage), dodging the marked strike circles or spending qi to blunt
a bolt. From Nascent Soul on, tribulation beasts and heart shades attack
between the volleys. A tribulation that strikes the player down starts again.
The runtime is godot/scripts/world/tribulation.gd.
"""

from .dsl import N, tribulation

# bolts per major realm (index into world_spec.REALMS): 3 for Qi Condensation .. 9 for Tribulation Transcendence
BOLTS = {1: 3, 2: 4, 3: 4, 4: 5, 5: 6, 6: 6, 7: 7, 8: 8, 9: 8, 10: 9}
# the Heavenly Tribulation of the finale: nine volleys of nine
FINAL_BOLTS = 81
VOLLEY_MAX = 9

OPEN = {
    1: "The sky over you darkens and turns, slow as a millstone. Heaven has noticed a mortal becoming something else.",
    2: "Clouds pile up over the mountain, black at the heart. A foundation must be tested before anything is built on it.",
    3: "The clouds come down low and heavy. Somewhere inside them, heaven weighs the core you are forging.",
    4: "The clouds split into a slow spiral. The first beasts of lightning drop out of it, eyes crackling.",
    5: "Heaven's eye opens over you. Your soul is changing, and heaven wants to know into what.",
    6: "The storm reaches down with long fingers, feeling for every thread you have not cut.",
    7: "The spiral turns the colour of a bruise. Lightning walks inside it, looking for the gap between body and soul.",
    8: "The clouds cover the whole sky. Every bolt that falls will test whether your body is truly one thing.",
    9: "The storm is vast and oddly quiet. It falls on everyone you carry, and through them, on you.",
    10: "The red moon hangs behind the storm like an eye behind a veil. Heaven has been waiting for this for years.",
}
FINAL_OPEN = "Nine times nine. The storm over the peak is so large it has its own weather. The first volley is already falling."


def params(realm_idx, final=False):
    bolts = FINAL_BOLTS if final else BOLTS[realm_idx]
    volleys = min(bolts, VOLLEY_MAX)
    if final:
        waves = [("tribulation_beast", 3, 3), ("heart_shade", 3, 6)]
    elif realm_idx >= 10:
        waves = [("tribulation_beast", 3, volleys // 3), ("heart_shade", 2, 2 * volleys // 3)]
    elif realm_idx >= 7:
        waves = [("tribulation_beast", 2, volleys // 3), ("heart_shade", 2, 2 * volleys // 3)]
    elif realm_idx >= 4:
        waves = [("tribulation_beast", 2, volleys // 2)]
    else:
        waves = []
    return bolts, waves


def make(realm_idx, realm_name, marker, map_id, final=False):
    bolts, waves = params(realm_idx, final)
    if final:
        text = "Survive the nine-times-nine Heavenly Tribulation"
        line = FINAL_OPEN
    else:
        text = "Survive the tribulation of %s" % realm_name
        line = OPEN[realm_idx]
    return tribulation(marker, bolts, text, (N, line), waves=waves, map=map_id)

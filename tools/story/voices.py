"""Voice casting for every speaker, used by tools/gen_voices.py (Piper TTS).

Casting notes: the en-us-libritts-high model has 904 speakers. A survey
synthesised one test sentence for every 4th speaker and estimated the median
F0 by autocorrelation (male ~85-150 Hz, female ~195-260 Hz) and the speaking
rate; the picks below spread the cast over clearly different pitches and
tempos. Elders get a slower length_scale, the dedicated single-speaker models
(ryan, lessac, alan, southern_english_female, kathleen, danny) give the
narrator, the female protagonist and a few characters an unmistakable timbre.

``fx`` is applied by gen_voices only (it is not exported to story.json):
  room   - subtle short room reverb (default for everyone)
  hall   - larger, darker reverb (sect master, star sage)
  demon  - slightly detuned double + dark reverb (Blood Moon voices)
"""

def v(model, speaker=None, length_scale=1.0, noise_scale=0.667, fx="room", noise_w=0.8):
    return {"model": model, "speaker": speaker, "length_scale": length_scale,
            "noise_scale": noise_scale, "noise_w": noise_w, "fx": fx}


LIBRI = "en-us-libritts-high"

# protagonist + narrator (not NPCs)
NARRATOR = v("en-us-ryan-medium", None, 1.08, 0.6)
PLAYER_M = v(LIBRI, 92, 1.0, 0.6)                   # ~133 Hz, clear young man
PLAYER_F = v("en-us-lessac-medium", None, 1.0, 0.6)  # bright young woman

NPC_VOICES = {
    # --- Azure Cloud Sect
    "master_yun": v("en-gb-southern_english_female-low", None, 1.06, 0.6, "hall"),
    "elder_mo": v(LIBRI, 132, 1.1, 0.667),           # ~100 Hz gruff old mentor
    "elder_bai": v("en-gb-alan-low", None, 1.04, 0.667),
    "elder_gu": v(LIBRI, 400, 1.06, 0.55),           # ~93 Hz, cold and measured
    "elder_hua": v(LIBRI, 164, 1.08, 0.6),           # ~199 Hz, calm healer
    "senior_han": v(LIBRI, 4, 1.0, 0.6),             # ~208 Hz, crisp
    "senior_wei": v(LIBRI, 548, 0.98, 0.7),          # ~101 Hz, big warm voice
    "rival_zhao": v(LIBRI, 544, 0.97, 0.6),          # ~130 Hz, quick and proud
    "gate_lu": v(LIBRI, 668, 0.96, 0.7),             # ~147 Hz, chatty
    "steward_qian": v(LIBRI, 828, 1.02, 0.667),      # ~143 Hz, fussy
    "xiao_man": v(LIBRI, 448, 0.98, 0.667),          # ~259 Hz, very young
    "xiao_shi": v(LIBRI, 900, 1.0, 0.667),           # ~141 Hz, young man
    # --- Whispering Bamboo Forest
    "hermit_lan": v(LIBRI, 704, 1.12, 0.667),        # ~109 Hz, slow and ancient
    "wanderer_ye": v(LIBRI, 472, 1.04, 0.5),         # ~94 Hz, low and quiet
    "bandit_tie": v(LIBRI, 380, 0.96, 0.8),          # ~95 Hz, rough and fast
    # --- Qingshi Town
    "magistrate_zhou": v(LIBRI, 328, 1.02, 0.667),   # ~134 Hz, slow and pompous
    "innkeeper_fang": v("en-us-kathleen-low", None, 0.98, 0.667),
    "constable_du": v(LIBRI, 288, 1.0, 0.667),       # ~101 Hz, plain
    "widow_liu": v(LIBRI, 764, 1.05, 0.667),         # ~204 Hz, soft
    "keeper_hong": v(LIBRI, 116, 1.06, 0.667),       # ~111 Hz, kindly old man
    "ferryman_pan": v("en-us-danny-low", None, 1.1, 0.667),
    "merchant_jin": v(LIBRI, 176, 1.0, 0.667),       # ~141 Hz, oily
    # --- Blood Moon Sect
    "patriarch_xue": v(LIBRI, 800, 1.16, 0.5, "demon"),   # ~85 Hz, the deepest voice
    "crimson_xuemei": v(LIBRI, 100, 1.02, 0.6, "demon"),  # ~232 Hz
    "heart_demon": v(LIBRI, 232, 1.08, 0.5, "demon"),     # ~100 Hz, whispering shadow
    # --- Celestial Sky Isles
    "star_sage": v(LIBRI, 820, 1.08, 0.55, "hall"),       # ~220 Hz, serene
}

# Spoken-text substitutions so espeak pronounces the pinyin names sensibly.
# Applied (whole words, case-sensitive, in order) only to the text sent to the
# TTS, never to subtitles.
PRONOUNCE = [
    ("Su Yue", "Soo Yweh"),
    ("Lin Feng", "Lin Fung"),
    ("Qingshi", "Ching-shr"),
    ("Xiao Man", "Shyao Mahn"),
    ("Xiao Shi", "Shyao Shr"),
    ("Xue Mei", "Shweh May"),
    ("Xue Wuji", "Shweh Woo-jee"),
    ("Qing Luan", "Ching Lwahn"),
    ("Yun Qingyao", "Yoon Ching-yao"),
    ("Sect Master Yun", "Sect Master Yoon"),
    ("Master Yun", "Master Yoon"),
    ("Gu Hanshan", "Goo Hahn-shahn"),
    ("Elder Gu", "Elder Goo"),
    ("Gu Lan", "Goo Lahn"),
    ("Zhao Kang", "Jao Kahng"),
    ("Zhao Ming", "Jao Ming"),
    ("Zhao", "Jao"),
    ("Zhou", "Joe"),
    ("Qian", "Chyen"),
    ("Han Xue", "Hahn Shweh"),
    ("Wei Tong", "Way Tong"),
    ("Wei", "Way"),
    ("Hua", "Hwah"),
    ("Tie Hu", "Tyeh Hoo"),
    ("Lan Jue", "Lahn Jweh"),
    ("Ye Wuming", "Yeh Woo-ming"),
    ("Lu Ping", "Loo Ping"),
    ("Liu", "Lyoh"),
    ("Gu", "Goo"),
    ("Yun", "Yoon"),
    ("Ye", "Yeh"),
    ("Xiao", "Shyao"),
    ("Xue", "Shweh"),
    ("Du Ming", "Doo Ming"),
    ("Jiao", "Jyao"),
    ("qi", "chee"),
    ("Qi", "Chee"),
    ("dao", "dow"),
    ("Dao", "Dow"),
    ("jian", "jyen"),
    ("yamen", "yah-men"),
]

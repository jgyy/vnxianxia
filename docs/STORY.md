# The Main Story: *The Lotus and the Blood Moon*

The main quest line of **Azure Cloud Sect** is a journey from mortal to immortal in **1000 quests**: 10 volumes, one
per major stage of cultivation, each of 10 chapters of 10 quests. It has 20 cinematics and a cast of 40 named NPCs.

The ten chapters of the original story are voiced (every line, with the protagonist's lines recorded twice for Lin
Feng and Su Yue) and keep their cinematics. The other 90 chapters are text-only: each one is a hand-written outline
(title, summary, cast and ten quest beats with their key dialogue) that `tools/story/saga_gen.py` expands into
objectives, markers, enemies, pickups and connecting dialogue. A complete list of all 1000 quests is in
**[QUESTS.md](QUESTS.md)**.

| | |
|---|---|
| Source | `tools/story/`: the ten original chapters (`chapter01..10.py`, DSL in `dsl.py`) and the outlines of the 90 new ones (`vol01..vol10.py`) |
| Structure | `volumes.py` (which chapter goes where, breakthroughs, minor stages), `numbering.py` (quest ids `q0001..q1000`) |
| Generator | `saga_gen.py` (quest patterns, marker choice, NPC placement), `places.py`, `fillers.py` |
| Compiler / validator | `python3 tools/build_story.py` writes `godot/data/story.json` (`--check` is used in CI, `--quests docs/QUESTS.md` writes the quest list) |
| Morality | `morality.py` (alignment vocabulary, NPC temperaments and reactions, greetings, choice templates), `choices.py` (hand-written choices) |
| Tribulations | `tribulations.py` (bolts and waves per major stage); runtime in `godot/scripts/world/tribulation.gd` |
| Voices | `python3 tools/gen_voices.py` writes `godot/audio/voice/*.ogg` using Piper TTS for the voiced lines (`--check` lists missing or stale files) |
| Casting | `tools/story/voices.py` |

## Premise

Three hundred years ago the **Blood Moon Patriarch, Xue Wuji**, drowned three kingdoms in blood while trying to seize the
heavens. The **Azure Cloud Sect** and the **Verdant Lotus Sect** sealed him beneath the Blood Moon Abyss with the
**Azure Heaven Seal**. The seal has two keys: the *Azure Eye*, which is the sect's formation array, and the *Lotus Key*.
Every Verdant Lotus elder gave their life to make the seal. The Patriarch's servants hunted down the survivors, and the
world forgot the sect's name.

The protagonist is **Lin Feng** or **Su Yue**. Tab switches between them, and every line adapts to whoever is active.
They are an orphan who climbs nine thousand steps to join the Azure Cloud with nothing but their mother's jade pendant.
That pendant is the Lotus Key, and the protagonist is the last of the Verdant Lotus bloodline. The seal is weakening,
the Blood Moon is gathering blood to break it, and someone inside the sect is helping them.

The core of the story is what grief does to people. **Elder Gu Hanshan** of the Law Hall betrays the sect because the
Patriarch promised to return the soul of his dead daughter. The Patriarch's real goal is not simply freedom. His body is
too steeped in sin to survive a heavenly tribulation, so he needs a clean body with Verdant Lotus blood to wear to heaven:
the protagonist's.

## Main characters

| Character | Role | Arc |
|---|---|---|
| **Lin Feng / Su Yue** (player) | Outer disciple, bearer of the Lotus Key | Orphan, then heir of a forgotten sect, then the one who climbs the Ascension Stair |
| **Yun Qingyao** | Sect Master | Dry-witted and protective. She trusted Gu with the sect's children, and she ends the story leading the final march |
| **Mo Changfeng** | Outer Court Elder, the mentor | A gruff man who is proud of the protagonist and says only "adequate". He finds Gu's sabotage too late and gives his life to turn the formation back (ch. 9) |
| **Gu Hanshan** | Law Hall Elder, **the traitor** | His grief made him the Patriarch's tool. He is unmasked at the tournament (ch. 5), confesses at the Heart Mirror (ch. 9) and opens the black gate at the cost of his life (ch. 10) |
| **Han Xue** | Inner disciple, the protagonist's senior sister | Cool, blunt and loyal. She is the first to see the pattern pointing to the Law Hall, is captured in the Abyss, and holds the bridge at the end |
| **Wei Tong** | Senior outer disciple | Big, always hungry, and warm. He carries the comedy until Mo's death breaks him, then fights "for Elder Mo" |
| **Zhao Kang** | Rival from the rich Zhao clan | Arrogant and grieving his brother, whom Gu sent to die. He goes from rival to partner to sworn friend ("when you come back down, we fight") |
| **Bai Qiu** | Keeper of the Scripture Pagoda | Eccentric librarian. He finds the missing pages and decodes the Patriarch's plan |
| **Hua Lian** | Medicine Hall Elder | The healer who uncovers the Frenzy Pills |
| **Xiao Man / Xiao Shi** | Apprentice herbalist and her missing brother | His disappearance ties the sect to Qingshi. He is rescued from the cages in ch. 6 |
| **Lan Jue**, "the Bamboo Hermit" | The last Verdant Lotus disciple | Ran away three hundred years ago. He forgives himself and ends up teaching the sutra again |
| **Ye Wuming** | Masked wanderer | Raised by the Blood Moon and nameless. He deserted and hunts them. Red herring in ch. 3, guide in ch. 6, and he gets his name back |
| **Tie Hu, "Iron-Fang"** | Bandit chief | Burns villages because the Blood Moon holds his people's families hostage. Spared in ch. 7, he pays his debt in ch. 10 |
| **Keeper Hong** | Qingshi temple keeper | A Blood Moon deacon in disguise (ch. 3 boss) |
| **Xue Mei** | Crimson Elder of the Blood Moon | Captures Han Xue and guards the altar (ch. 6 boss) |
| **Qing Luan** | Star-gazing sage of the Sky Isles | A remnant soul with a sense of humour. She notices that the sect's formation design "turns outward" |
| **Xue Wuji** | Blood Moon Patriarch | The final antagonist, first on his throne and then as a remnant riding the tribulation lightning |
| Qingshi Town | Magistrate Zhou, Madam Fang, Constable Du, Widow Liu, Old Pan, Merchant Jin | The townsfolk. The cowardly magistrate finds his spine and the merchant who sold blood lotus redeems himself |

Added for the 1000-quest saga (text-only):

| Character | Role | Arc |
|---|---|---|
| **Yan Tie** | Thunder Peak's champion, poisoned in the tournament final | Owes the heir his life; Thunder Peak's loud, loyal friend, keeper of the lightning forge (vol. II-X) |
| **Liu Er** | Widow Liu's son, freed from the cages | Climbs the nine thousand steps at sixteen and teaches Qingshi to fight with brooms (vol. III-X) |
| **Gou the Scarred** | Iron-Fang's lieutenant | Raids the salt road because the Blood Moon holds his mother; spared, he writes down forty-one names (vol. I) |
| **Ruan Hai / Ruan Jingtao** | Master and heir of the Iron Scale Sect | Rivals at the Nine Banners, then allies; their southern peak falls into the void and becomes Remembering Hill (vol. III-X) |
| **Zhao Tianlu** | Ancestor of the Zhao clan, 112 and counting | Comes to take his great-grandson home and frames his monthly letters instead (vol. III-IX) |
| **Jing Xuan** | Abbess of the Moon-Well Nunnery | Tests the heir with a week of anonymous service; the Great Vehicle's conscience (vol. VI-X) |
| **The Seven Rungs** | Luo Hui, Tie Shan the Rust Monk, Jiu Rong (Madam Ninefold), Kong Yi (Brother Hollow), Wen Tu the Butcher, Si Rou (Lady Silk), Xue Chen | The Patriarch's Ladder: seven servants each holding one red star, a ladder for his soul to climb the heir's lightning. They fall one per arc, from the First Rung in vol. V to Xue Chen, the Patriarch's Shadow and the heir's cousin from Willow Creek, in vol. X |

## The ten volumes

The player starts as a **Mortal** and climbs ten major stages, one per volume, each divided into ten minor stages, then ascends. Chapter *c* of volume *v* ends with the player reaching minor stage *c* of major stage *v*, so the 100 chapters are the 100 minor stages. The first chapter of every volume ends with a **heavenly tribulation** and the breakthrough into the volume's realm at its 1st Layer; the last chapter reaches Great Perfection of Tribulation Transcendence on quest 999 and **Immortal Ascension** on quest 1000. Chapters in **bold** are the ten voiced chapters of the original story.

| Vol | Major stage | Subtitle | Chapters |
|---|---|---|---|
| 1 | Qi Condensation | *The Mountain and the Pendant* | **1 The Outer Disciple** · **2 Whispers in the Bamboo** · **3 Shadows over Qingshi** · 4 A Closed Door on the Mountain · 5 The Moonbell Harvest · 6 Bandits of the Salt Road · 7 The Outer Sect Examination · 8 Lanterns on the Qing River · 9 The Moonlit Grotto · 10 Heart of the Grotto |
| 2 | Foundation Establishment | *The Traitor in the Law Hall* | **11 Ruins of the Forgotten Sect** · **12 The Inner Sect Tournament** · 13 The Burned Array · 14 Robes of the Inner Sect · 15 The Cauldron's Temper · 16 The Beast Tide · 17 Tide at the Town Gate · 18 The Second Verse · 19 The Crimson Road · 20 Eve of the Descent |
| 3 | Core Formation | *Blood Beneath the Earth* | **21 Descent into the Blood Moon** · **22 Siege of Qingshi** · 23 Envoys of the Iron Scale · 24 The Nine Banners · 25 Smoke on the Border · 26 The Sunken Archive · 27 Tea at the Drunken Crane · 28 Sword Qi of the Golden Core · 29 Patrol of the Crimson Rim · 30 When the Sky Stair Descends |
| 4 | Nascent Soul | *Isles Above the Clouds* | **31 Isles Above the Clouds** · 32 The Cloud Road · 33 Nine Pillars · 34 The Seven-Star Crates · 35 The Soul Fog · 36 The Zhao Clan's Summons · 37 Duel Above the Clouds · 38 What the Stars Remember · 39 The Last Pillar · 40 Before the Lighting |
| 5 | Soul Transformation | *The Heart Demon* | **41 The Heart Demon** · 42 The Blood Moon That Did Not Break · 43 Grief Has Teeth · 44 Adequate · 45 The Empty Law Hall · 46 Where the Lotus Grew · 47 A Letter Signed With Ash · 48 The Mirror Within · 49 The Rung of Ash · 50 What the Old Man Left |
| 6 | Spirit Severing | *The Fold in the World* | 51 Cracks in the Sky · 52 The Fold in the Abyss · 53 The Rust Monk's Penance · 54 The Moon-Well Asks · 55 The Spring Runs Into Nothing · 56 Ye Wuming's Children · 57 Madam Ninefold · 58 Maps of Nothing · 59 The Iron Scale Remembers · 60 Still Water, Empty Sky |
| 7 | Void Refinement | *A Body Worth Stealing* | 61 A Body Worth Stealing · 62 Thunder Peak's Forge · 63 Hollow Men of Qingshi · 64 The Blood Pools, Again · 65 Brother Hollow · 66 The Butcher's Market · 67 Iron-Fang's Old Roads · 68 The Butcher's Larder · 69 The Butcher of Wen · 70 One Body, One Soul |
| 8 | Body Integration | *The Great Vehicle* | 71 The Great Vehicle · 72 The Sects Arrive · 73 A Week Without a Name · 74 The Conclave of Forty Sects · 75 Threads Between Sects · 76 The Web Unravels · 77 Lady Silk · 78 The Oath of the Great Vehicle · 79 Teaching the Many · 80 A Vehicle for Ten Thousand |
| 9 | Mahayana | *Heaven Takes Notice* | 81 Heaven Takes Notice · 82 Thunder Crystal Harvest · 83 The Seventh Rung · 84 Lightning Rods for a Sect · 85 The Lesser Tribulation · 86 Words for Those Left Behind · 87 Han Xue's Soul · 88 Zhao Kang's Wager · 89 The Red Star Aligns · 90 The Stair Remembers |
| 10 | Tribulation Transcendence | *The Last Blood Moon* | 91 The Moon Turns Red · 92 Forty Bandits, Washed and Fed · 93 A Traitor's Last Requests · 94 Xue Chen's Hunt · 95 The Shadow at the Stair · 96 The Last Evening · 97 The Void Unfolds · 98 The Patriarch's Shadow · 99 Eve of the Last Blood Moon · **100 Heavenly Tribulation** |

### Volume 1 · Qi Condensation — *The Mountain and the Pendant*

An orphan climbs nine thousand steps, learns to breathe qi, and finds that red-eyed wolves, caged mortals and a kindly temple keeper all point to the same buried name: the Blood Moon.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 1 | The Outer Disciple *(voiced)* | Azure Cloud Sect | **Qi Condensation** (tribulation) | An orphan with a jade pendant climbs nine thousand steps to the Azure Cloud Sect. Sect rules, sore muscles, a proud rival and a first taste of qi, until red-eyed wolves prowl the sect wall for the first time in three hundred years. |
| 2 | Whispers in the Bamboo *(voiced)* | Whispering Bamboo | 2nd Layer | A routine herb mission into the Whispering Bamboo Forest turns into a hunt for corrupted wolves, a meeting with a hermit and a masked wanderer, and a bandit camp caging mortals. In its chest lies a blood-red jade token that should not exist. |
| 3 | Shadows over Qingshi *(voiced)* | Qingshi Town | 3rd Layer | Mortals vanish from Qingshi Town every new moon. With Senior Sister Han Xue, you follow a trail of gossip, blood lotus and graveyard runes to a kindly temple keeper who is neither kindly nor a keeper. |
| 4 | A Closed Door on the Mountain | Azure Cloud Sect | 4th Layer | Home from Qingshi with a deacon's dying words, you find the main hall sealed: the Sect Master is in secluded cultivation, steadying the flickering Azure Eye. Until she emerges there are contribution points to earn, a treasury that keeps losing stones, and a mountain that has begun to notice you. |
| 5 | The Moonbell Harvest | Whispering Bamboo | 5th Layer | Elder Hua's autumn harvest takes you back into the Whispering Bamboo, where the herb grove is sickening and the spirit spring runs faintly red. The hermit pours tea, the wolves are gone, and something beneath the old den is still bleeding into the earth. |
| 6 | Bandits of the Salt Road | Qingshi Town | 6th Layer | Iron-Fang's scattered gang is raiding the salt caravans into Qingshi under his lieutenant, Gou the Scarred. Constable Du wants the road open, Magistrate Zhou wants to look brave, and the bandits want something no amount of salt can buy. |
| 7 | The Outer Sect Examination | Azure Cloud Sect | 7th Layer | Once a year every outer disciple is tested: the precepts before Elder Gu, the puppets before Wei Tong, a pill before Elder Hua and a sparring bout before the whole plaza. Zhao Kang intends to win. So do you. |
| 8 | Lanterns on the Qing River | Qingshi Town | 8th Layer | Qingshi keeps the Ghost Festival for everyone it lost to the new moon. You and Han Xue come down to help, and find the river restless: whatever Deacon Hong buried under the graves did not all stay buried. |
| 9 | The Moonlit Grotto | Whispering Bamboo | 9th Layer | Once a decade a secret realm opens beneath the bamboo, and the sect sends its best outer disciples in. Han Xue leads, Wei Tong carries the food, Zhao Kang carries a grudge, and the grotto carries everyone somewhere else. |
| 10 | Heart of the Grotto | Whispering Bamboo | Great Perfection | At the heart of the Moonlit Grotto waits its warden, a stone giant that has asked the same question for three hundred years. The rogues want what it guards, the grotto wants to close, and Wei Tong wants lunch. |

### Volume 2 · Foundation Establishment — *The Traitor in the Law Hall*

The Verdant Lotus ruins open for their heir, the Inner Sect Tournament unmasks Elder Gu, and a sect that trusted its own law must learn to follow a traitor into the dark.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 11 | Ruins of the Forgotten Sect *(voiced)* | Whispering Bamboo | **Foundation Establishment** (tribulation) | The library's Blood Moon records are missing. The Bamboo Hermit reveals who he really is and what your pendant really is. In the ruins of the Verdant Lotus Sect, a stone guardian waits for its heir, and you establish your foundation. |
| 12 | The Inner Sect Tournament *(voiced)* | Azure Cloud Sect | 2nd Layer | Banners rise over the Azure Cloud for the Inner Sect Tournament. Rivals become partners, a poisoned pill box points at the Law Hall, and on the night of the final the traitor finally shows his face. |
| 13 | The Burned Array | Azure Cloud Sect | 3rd Layer | The morning after the traitor fled, the teleport array's route to the Abyss is slag, the Azure Eye is cracked, and the Law Hall is a row of empty chairs. Before anyone can follow Gu Hanshan, the sect has to find out who else was helping him. |
| 14 | Robes of the Inner Sect | Azure Cloud Sect | 4th Layer | A tournament champion cannot stay an outer disciple. New robes, new duties, a champion from Thunder Peak who owes you his life, and a sect that looks at you differently now: some with hope, some with envy, all with questions. |
| 15 | The Cauldron's Temper | Azure Cloud Sect | 5th Layer | Gu's Frenzy Pills went into more than the tournament supplies: disciples on three peaks are waking with red at the edges of their eyes. Elder Hua needs a cure, the cure needs herbs from the bamboo, and the cauldron needs someone who can hold a fire steady without blowing up the Medicine Hall. |
| 16 | The Beast Tide | Whispering Bamboo | 6th Layer | The wards Gu kept on the bamboo forest were never wards at all, only leashes, and he has let go of them. Every beast the Blood Moon ever fed pours out of the deep forest at once, and the hermit's hut is directly in the way. |
| 17 | Tide at the Town Gate | Qingshi Town | 7th Layer | Half the beast tide has turned toward Qingshi, and the town has only its constable, its magistrate's new spine and a merchant who suddenly wants very badly to be liked. You have until nightfall. |
| 18 | The Second Verse | Whispering Bamboo | 8th Layer | The Heart Sutra has three verses. You learned the first in the ruins. The hermit says the second is harder: it can only be learned by someone who has forgiven something. He has been trying for three hundred years. |
| 19 | The Crimson Road | Qingshi Town | 9th Layer | The steered tide came from somewhere, and the blood lotus in Qingshi's crates goes somewhere. Follow the carts west along the river and you find a road nobody admits exists: the Crimson Road, down to the Abyss. |
| 20 | Eve of the Descent | Azure Cloud Sect | Great Perfection | The array masters have laid a new route to the Abyss's rim. The Sect Master reads the Crimson Road report twice, and makes her choice: not an army, but two disciples and whoever knows the way down. Before you go, the sect says goodbye in its own ways. |

### Volume 3 · Core Formation — *Blood Beneath the Earth*

A golden core forged in the Abyss, a town held against a siege, and a war of words and swords between the orthodox sects while the Sky Isles slowly turn toward their opening.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 21 | Descent into the Blood Moon *(voiced)* | Blood Moon Abyss | **Core Formation** (tribulation) | Guided by the masked wanderer, who was once one of them, you descend into the Blood Moon Abyss. Obelisks drink the blood of caged cultivators, Han Xue is taken, and at the Altar of Blood the traitor feeds the seal to its prisoner. |
| 22 | Siege of Qingshi *(voiced)* | Qingshi Town | 2nd Layer | The Blood Moon and Iron-Fang's bandits march on Qingshi. With Zhao Kang and Wei Tong at your side, you turn a frightened market town into a fortress, and learn that the siege was never really about the town. |
| 23 | Envoys of the Iron Scale | Azure Cloud Sect | 3rd Layer | The Iron Scale Sect lost eleven disciples to Blood Moon raids this year, and blames the Azure Cloud for the traitor who armed them. Its sect master climbs the nine thousand steps with a demand: surrender the Lotus Key to a council of sects. His son would rather settle it with swords. |
| 24 | The Nine Banners | Azure Cloud Sect | 4th Layer | Nine duels, nine banners, two sects and eighty years of dusty rules. The Iron Scale fights for its dead; the Azure Cloud fights for the right to keep carrying its own burden. And beneath the plaza, the cracked Azure Eye listens to every blow. |
| 25 | Smoke on the Border | Whispering Bamboo | 5th Layer | The duel settled the question, but not the border. Iron Scale raiders are burning herb groves on the forest's eastern edge, and Ruan Hai swears he never sent them. The raiders' eyes are red at the edges, and they are wearing borrowed armour. |
| 26 | The Sunken Archive | Whispering Bamboo | 6th Layer | The Verdant Lotus kept an archive beneath their ruins, flooded when the sect fell. The hermit has never dared go down. With a golden core, you can hold your breath long enough, and the archive may know how the Sky Isles open. |
| 27 | Tea at the Drunken Crane | Qingshi Town | 7th Layer | The four sects on the raiders' list agree to meet on neutral ground: Madam Fang's inn in Qingshi. There will be tea, and noodles, and Iron-Fang washing the dishes. There will also be an assassin, because there always is. |
| 28 | Sword Qi of the Golden Core | Azure Cloud Sect | 8th Layer | A golden core can throw qi like a blade. Elder Mo intends to teach you how before the isles open, whether you like it or not, and whether he likes admitting he's proud of you or not. Xiao Shi, meanwhile, still dreams of cages. |
| 29 | Patrol of the Crimson Rim | Blood Moon Abyss | 9th Layer | While the sect waits for winter, somebody has to watch the Abyss. Ye Wuming and the children he took from the Blood Moon already do. They ask for help: the Blood Moon has begun to dig, and whatever they are digging for is marked with seven dots. |
| 30 | When the Sky Stair Descends | Azure Cloud Sect | Great Perfection | In the first week of winter a stair of cloud unrolls from the sky above the sect, and the whole mountain comes out to stare. The Sky Isles are opening. Elder Bai finishes the Great Azure Formation's design from the Law Hall archive, the Sect Master chooses her three, and the sect sends them up with dumplings. |

### Volume 4 · Nascent Soul — *Isles Above the Clouds*

The Sky Isles give up star iron and a nascent soul. The Great Azure Formation rises, and a seven-star mark begins to appear wherever the Blood Moon is digging.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 31 | Isles Above the Clouds *(voiced)* | Sky Isles | **Nascent Soul** (tribulation) | The Celestial Sky Isles open once every sixty years. With Han Xue and Zhao Kang you gather star iron, thunder crystals and phoenix feathers for the Great Azure Formation, face the corrupted Jiao serpent, and hear a star-gazer doubt the sect's design. |
| 32 | The Cloud Road | Sky Isles | 2nd Layer | The full moon has closed the Sky Isles to mortal feet, but a paper crane from Qing Luan says a nascent soul can walk the cloud road anyway. She has things to teach: how to see with the soul, how to step with it, and what seven red stars really mean. |
| 33 | Nine Pillars | Azure Cloud Sect | 3rd Layer | The Great Azure Formation stands on nine pillars, and each pillar must be inscribed by a nascent soul. There is exactly one nascent soul on the mountain young enough to carry stone. Elder Mo builds, Steward Qian weeps, Wei Tong carries, and the mountain slowly rises into a new shape. |
| 34 | The Seven-Star Crates | Qingshi Town | 4th Layer | Crates stamped with seven stars have been passing through Qingshi's docks. Merchant Jin, who is now honest and hates it, has noticed. The crates lead to a warehouse nobody owns, and to a pale man who calls himself the First Rung of the Patriarch's Ladder. |
| 35 | The Soul Fog | Whispering Bamboo | 5th Layer | A grey fog has settled on the Whispering Bamboo, and everything it touches forgets itself: birds forget to sing, streams forget to run, and the hermit has forgotten your name. Only a soul that can see can find what is feeding on the forest's memories. |
| 36 | The Zhao Clan's Summons | Azure Cloud Sect | 6th Layer | Zhao Tianlu, ancestor of the Zhao clan, climbs the nine thousand steps to bring his great-grandson home: the clan needs an heir, not a sect disciple who picks fights with ladders. Zhao Kang must choose, and he has never been good at choosing anything but arguments. |
| 37 | Duel Above the Clouds | Sky Isles | 7th Layer | Qing Luan sends word that someone is poisoning the spirit vein with rust. You walk the cloud road again and find the Second Rung: a monk in rotting robes who prays over the crystals as they die. He is very polite, and he wants to see how strong your soul has grown. |
| 38 | What the Stars Remember | Sky Isles | 8th Layer | Qing Luan asks you up one last time before the isles close for good. She wants to show you the night Xue Wuji first climbed, and the night the founders pulled him down. The palace sentinels would prefer she didn't. |
| 39 | The Last Pillar | Azure Cloud Sect | 9th Layer | The ninth pillar goes up. The mountain holds a festival for the Great Azure Formation: lanterns, dumplings, Thunder Peak shouting, and Elder Mo, who has checked nine thousand nine hundred runes and has one ring left. |
| 40 | Before the Lighting | Azure Cloud Sect | Great Perfection | The formation's frame is finished. The star iron is set, the thunder crystals charged, the phoenix feathers laid in the outer ring. All that remains is for Elder Mo to finish checking, and for the Sect Master to light it. The mountain holds its breath, and nobody knows why. |

### Volume 5 · Soul Transformation — *The Heart Demon*

Elder Mo gives his life to turn the formation back. The last blood moon does not break the seal; instead the Abyss folds its fortress into the void, and the sect learns to live with grief.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 41 | The Heart Demon *(voiced)* | Azure Cloud Sect | **Soul Transformation** (tribulation) | On the eve of lighting the Great Azure Formation, a letter from the traitor lures you to the Heart Mirror, where you must defeat your own shadow. You return to a burning sky, and Elder Mo pays the price for the sect's trust. Now you know what the Patriarch truly wants: you. |
| 42 | The Blood Moon That Did Not Break | Blood Moon Abyss | 2nd Layer | Three days after the formation was mended, the blood moon rises and the Azure Cloud's vanguard stands at the rim of the Abyss. The seal holds. The Patriarch cannot break it. So, with the whole sect watching, he folds his black fortress into the void and vanishes, to wait for a better night. |
| 43 | Grief Has Teeth | Azure Cloud Sect | 3rd Layer | The sect comes home from a war that didn't happen to a teacher who isn't there. Disciples wake with red at the edge of their vision again, not from pills this time, but from grief. Heart demons are gathering on the mountain, and the one feeding on Wei Tong is the hungriest. |
| 44 | Adequate | Azure Cloud Sect | 4th Layer | The outer court has no elder, and twelve new disciples arrived at the gate this spring as if nothing had happened. Somebody has to teach them to stand up straight. Wei Tong would rather do anything else. He does it anyway. |
| 45 | The Empty Law Hall | Qingshi Town | 5th Layer | Magistrate Zhou writes to the sect: Qingshi's disputes used to go to the Law Hall of the Azure Cloud when the yamen couldn't settle them. The Law Hall is empty. The Sect Master sends you, with a warning, and with advice from the last man who sat in its chair. |
| 46 | Where the Lotus Grew | Azure Cloud Sect | 6th Layer | The Verdant Lotus seed you planted in the sect's pond before the descent has flowered, green and gold, beside the Azure Cloud's carp. The hermit promised he would visit when it did. After three hundred years in the bamboo, Lan Jue climbs the nine thousand steps. |
| 47 | A Letter Signed With Ash | Qingshi Town | 7th Layer | Every night a village near Qingshi burns, and in the ashes someone draws a ladder. Luo Hui, the First Rung, is healed and hungry and writing to you. The letters are polite. The fires are not. |
| 48 | The Mirror Within | Blood Moon Abyss | 8th Layer | Before you hunt Luo Hui at the rim, the Heart Mirror calls. It's outside the fold, still black, still still, and your transformed soul can hear it humming your name. There is one fear you haven't faced yet: not of dying, but of ascending, and leaving everyone behind. |
| 49 | The Rung of Ash | Blood Moon Abyss | 9th Layer | Luo Hui, the First Rung of the Patriarch's Ladder, waits at the obelisk ring in a circle of ash. He has healed twice. He intends to test you one last time. This time, with the fold at his back and his star overhead, he is not going anywhere, and neither are you. |
| 50 | What the Old Man Left | Azure Cloud Sect | Great Perfection | Elder Mo left very little: a tea set, a peach orchard, forty years of notes, and a locked box addressed to you. With the first rung broken and the long war begun, the Sect Master decides it's time you opened it. |

### Volume 6 · Spirit Severing — *The Fold in the World*

Void rifts open over isle, forest and town. To reach a patriarch hiding between spaces, the Lotus heir learns to walk where there is nothing to walk on, and the Rungs of his Ladder start to fall.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 51 | Cracks in the Sky | Sky Isles | **Spirit Severing** (tribulation) | The Sky Isles closed for sixty years. Something has torn them open again: rifts of purple nothing are eating the isles one pine at a time, and Qing Luan, who is a memory, is starting to forget herself. To save her, you must learn to stand in the void, and refine your soul in it. |
| 52 | The Fold in the Abyss | Blood Moon Abyss | 2nd Layer | With a refined soul you can step into the edge of the fold. Ye Wuming asks you to look for the black gate. What you find is worse and stranger: the fortress drifting in nothing, and behind its walls, the prisoners, held still as flies in amber. |
| 53 | The Rust Monk's Penance | Qingshi Town | 3rd Layer | Tie Shan, the Rust Monk and Second Rung, has taken Keeper Hong's old temple in Qingshi and begun to pray. Every prayer rusts something: the gate hinges, the ferry chain, the constable's spear, the town bell. By the end of the week there will be no iron left in Qingshi, and he will start on the people. |
| 54 | The Moon-Well Asks | Azure Cloud Sect | 4th Layer | The abbess of the Moon-Well Nunnery climbs the nine thousand steps: her nuns are vanishing into rifts one by one, and the girl you freed from a forgotten cage at the Abyss rim told her the Azure Cloud answers when you ask. |
| 55 | The Spring Runs Into Nothing | Whispering Bamboo | 5th Layer | A rift has opened in the bottom of the spirit spring, and the spring is draining into the void. Without it, the Verdant Lotus seeds won't grow, the forest will sicken, and the hermit, who has only just stopped running, will have nowhere to come home to. |
| 56 | Ye Wuming's Children | Whispering Bamboo | 6th Layer | Madam Ninefold, the Third Rung, raised Ye Wuming's children in the Blood Moon's cages and wants them back. She has taken River, and she is circling the others. Ye Wuming has hunted the Blood Moon for forty years. This is the first time he's been afraid. |
| 57 | Madam Ninefold | Qingshi Town | 7th Layer | Jiu Rong, Madam Ninefold, the Third Rung, is somewhere in Qingshi wearing one of nine faces. She could be anyone: the new cook, the widow's neighbour, the constable's cousin. The town has to learn to look twice, and so do you. |
| 58 | Maps of Nothing | Azure Cloud Sect | 8th Layer | Three Rungs gone, four to go, and nobody knows where the other four are. Xiao Shi's map of the rifts covers the pagoda's wall and has started on the ceiling. Elder Bai thinks the map can find the Rungs. The hermit thinks it can do something stranger: find the Patriarch. |
| 59 | The Iron Scale Remembers | Whispering Bamboo | 9th Layer | At the forest's far edge, the Iron Scale's border is melting into nothing. Ruan Jingtao meets you with his sword drawn and his father's banner on his back. The Iron Scale's southern peak is gone, and something enormous is walking out of the place where it used to be. |
| 60 | Still Water, Empty Sky | Sky Isles | Great Perfection | Qing Luan sends for you one more time before the isles' rifts close. She says your spirit severing is nearly complete, and that the next stage will be the hardest: not your soul, but your body. Before that, she wants to show you the tribulation peak, from a distance. |

### Volume 7 · Void Refinement — *A Body Worth Stealing*

The Patriarch needs a body clean enough to survive heaven. His Rungs go hunting for one; the answer is to make body and soul a single thing that cannot be borrowed.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 61 | A Body Worth Stealing | Azure Cloud Sect | **Void Refinement** (tribulation) | Brother Hollow's red star is sliding toward the Azure Cloud, and the first things he reaches for are empty ones: the training puppets stand up in the night and walk. Elder Hua has prepared the tempering baths. They will hurt. When they are done, no one will ever be able to wear you. |
| 62 | Thunder Peak's Forge | Azure Cloud Sect | 2nd Layer | An integrated body still has to learn what it can do. Thunder Peak has been waiting years to share its secret: the lightning forge at the summit, where they temper swords and, once a generation, people. Yan Tie wants you in it. Thunder Peak wants to shout while you're there. |
| 63 | Hollow Men of Qingshi | Qingshi Town | 3rd Layer | In Qingshi, the people who have given up are sitting in doorways with purple eyes and smiling. Brother Hollow lives in empty things, and despair is very empty. Liu Er comes home in blue robes to find his neighbours gone out behind their own faces. |
| 64 | The Blood Pools, Again | Blood Moon Abyss | 4th Layer | The purified blood pools at the Abyss rim can temper an integrated body further than any bath. Brother Hollow knows it, and is waiting there. So is Ye Wuming, with his children, and a warning: the Fourth Rung has found a body he likes, and it isn't yours. |
| 65 | Brother Hollow | Whispering Bamboo | 5th Layer | Kong Yi, Brother Hollow, the Fourth Rung, has come to the Whispering Bamboo, where every stalk is hollow and every hollow is a place to live. He has ten thousand bodies to wear, and he wants just one more. He cannot have it. |
| 66 | The Butcher's Market | Qingshi Town | 6th Layer | Wen Tu, the Butcher of Wen and Fifth Rung, has opened a market beneath Qingshi. He buys the bodies of dead cultivators by the jin, and keeps the best ones fresh in void-ice for a customer who needs a body heaven can't refuse. Merchant Jin has been offered a partnership. |
| 67 | Iron-Fang's Old Roads | Whispering Bamboo | 7th Layer | The bandit roads through the bamboo were Iron-Fang's once. The Butcher of Wen uses them now to move his frozen cargo. Tie Hu leads you down every one of them, and remembers, on each, something he did there that he'd rather have not. |
| 68 | The Butcher's Larder | Whispering Bamboo | 8th Layer | In the caves beneath the old wolf den, where the Moonlit Grotto once opened, the Butcher of Wen keeps his larder: rows of void-ice, twenty-one breathing people and nineteen who are only bodies, kept fresh for a fitting that must never happen. |
| 69 | The Butcher of Wen | Blood Moon Abyss | 9th Layer | Wen Tu, the Butcher of Wen, Fifth Rung of the Ladder, waits at the Abyss rim by the fold, sharpening his cleavers on the obelisk stumps. He weighs cultivators by the jin. He has never weighed one like you. |
| 70 | One Body, One Soul | Azure Cloud Sect | Great Perfection | Five Rungs have fallen. Your body and soul are almost one thing. Elder Hua says the last step of Void Refinement isn't tempering: it's rest, and home, and letting the people you love remind you what the body is for. |

### Volume 8 · Body Integration — *The Great Vehicle*

No one climbs alone. The sects that once quarrelled over the Lotus Key gather into one alliance, and Lady Silk spins her web through the middle of it.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 71 | The Great Vehicle | Azure Cloud Sect | **Body Integration** (tribulation) | Five Rungs have fallen and the fold at the Abyss grows thinner. When it opens, the Azure Cloud cannot march alone. The Sect Master decides to call every orthodox sect to one conclave, and the hermit says the heir must learn the realm that carries others: Body Integration, the first step of the Great Vehicle. |
| 72 | The Sects Arrive | Azure Cloud Sect | 2nd Layer | For a week the nine thousand steps are never empty. Iron Scale green, Zhao gold, Moon-Well white and the colours of sects nobody has heard of climb the mountain, argue about who goes first, and set up camp on every flat stone. |
| 73 | A Week Without a Name | Qingshi Town | 3rd Layer | Before the conclave begins, Abbess Jing of the Moon-Well sets you a test: a week in Qingshi, serving the poor, and nobody may know who you are. The Great Vehicle, she says, is carrying people who don't know your name. |
| 74 | The Conclave of Forty Sects | Azure Cloud Sect | 4th Layer | Forty sects in the main hall, the first conclave in three hundred years. The Sect Master speaks. The sect masters argue. Somewhere in the middle of it, a woman in pink silk smiles, and every argument gets a little worse. |
| 75 | Threads Between Sects | Azure Cloud Sect | 5th Layer | The conclave agrees on everything except the thing that matters: who holds the Lotus Key when the fold opens. Lady Silk has one thread left, and she ties it to the oldest wound in the room, the question the Iron Scale gave up at the Nine Banners. |
| 76 | The Web Unravels | Qingshi Town | 6th Layer | Qingshi has been quarrelling for a year. Neighbours of forty years aren't speaking; the magistrate and the constable have fallen out; even Madam Fang and Iron-Fang argued over a dish. Lady Silk has woven the whole town, and somewhere in it, she's hiding at the centre of her web. |
| 77 | Lady Silk | Azure Cloud Sect | 7th Layer | The conclave's last night is a feast for forty sects on the formation plaza. Lady Si Rou, Sixth Rung of the Ladder, has promised to attend as guest of honour, and nobody knows what face, what thread, or what knife she'll bring. |
| 78 | The Oath of the Great Vehicle | Azure Cloud Sect | 8th Layer | Forty sects swear one oath on the formation plaza: when the fold opens, they march together. Then they go home, to train, to wait, and to write monthly letters. The mountain empties slowly, like a tide going out. |
| 79 | Teaching the Many | Whispering Bamboo | 9th Layer | The alliance sends its young disciples to the Verdant Lotus ruins, to learn the Heart Sutra from the hermit and the Great Vehicle from you. The ruins, which held three hundred years of silence, are suddenly full of children arguing about roots, stems and blossoms. |
| 80 | A Vehicle for Ten Thousand | Blood Moon Abyss | Great Perfection | The alliance's first joint action: every sect sends fighters to the Abyss rim, to seal the rifts leaking from the fold before they reach anyone's home. Forty sects, one rim, one heir in the middle carrying all of them. |

### Volume 9 · Mahayana — *Heaven Takes Notice*

Clouds gather over every step. Thunder crystals, lightning rods, lesser tribulations and farewells said early: the long preparation for a sky that is coming to look.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 81 | Heaven Takes Notice | Sky Isles | **Mahayana** (tribulation) | The clouds over the Azure Cloud turn in a slow spiral, and one morning a stair of cloud unrolls from them without waiting for any sixty-year cycle. The Sky Isles have opened again, for one visitor. Qing Luan is waiting at the cloud gate, frowning at the sky like it's disappointed a constellation. |
| 82 | Thunder Crystal Harvest | Sky Isles | 2nd Layer | A tribulation can be survived, the old books say, if the lightning can be split: thunder crystals planted on the summit, like a river delta. The isles hold the only crystals strong enough, and the storm wolves, the sentinels and the Seventh Rung's shadows all want them too. |
| 83 | The Seventh Rung | Blood Moon Abyss | 3rd Layer | The Seventh Rung's shadows have been seen at the Abyss rim, gathering blood from the fold's edge. Ye Wuming asks you to come. At the obelisk ring, for the first time, the Patriarch's Shadow steps into the light: a young man with red eyes and your mother's cousin's village name on his lips. |
| 84 | Lightning Rods for a Sect | Azure Cloud Sect | 4th Layer | A tribulation strikes the cultivator, but lightning is careless: stray bolts can burn a mountain. The sect must be protected before heaven comes. Thunder Peak has opinions, Elder Bai has diagrams, and Steward Qian has a budget he's already crying over. |
| 85 | The Lesser Tribulation | Sky Isles | 5th Layer | Before the great tribulation comes a lesser one: three bolts, a warning shot from heaven. Qing Luan says every cultivator gets one, and most of them die of it. She says it cheerfully. Then she says your heart demon will flicker in the third bolt, and she isn't cheerful any more. |
| 86 | Words for Those Left Behind | Qingshi Town | 6th Layer | The Sect Master said start with Qingshi. So you walk down the nine thousand steps with a bag of warm tribulation jade, and say goodbye early to a town that has been saving your bowl of noodles for years. |
| 87 | Han Xue's Soul | Azure Cloud Sect | 7th Layer | Han Xue has been close to forming her nascent soul for a year, and has refused to try while you needed guarding. Now she asks you to do what she did for you, long ago in the plum garden: stand guard, and keep the trouble away. |
| 88 | Zhao Kang's Wager | Azure Cloud Sect | 8th Layer | Zhao Tianlu, a hundred and fifteen years old, climbs the steps one last time to name his great-grandson head of the Zhao clan. Zhao Kang doesn't want it. He wants something else: a wager with you, for old times' sake, before the sky takes you somewhere he can't follow. |
| 89 | The Red Star Aligns | Sky Isles | 9th Layer | Qing Luan calls you back to the isles. The seventh red star, Xue Chen's, is sliding into place over the tribulation peak, and the moon is redder every night. She has finally read the whole chart, and she wishes she hadn't. |
| 90 | The Stair Remembers | Sky Isles | Great Perfection | Qing Luan takes you to the foot of the Ascension Stair, the stair nobody has climbed since your founders pulled the Patriarch off it. You won't climb it today. She just wants the stair to meet you, and you to meet it, before the night when everything happens at once. |

### Volume 10 · Tribulation Transcendence — *The Last Blood Moon*

The moon turns red, the void unfolds, and the last Rung falls. The Azure Cloud marches into the Abyss, the Patriarch rides the lightning, and an orphan climbs the Ascension Stair.

| # | Chapter | Map | Reached at its end | Summary |
|---|---|---|---|---|
| 91 | The Moon Turns Red | Azure Cloud Sect | **Tribulation Transcendence** (tribulation) | Every night the moon rises a little redder. The fold at the Abyss has begun to breathe, the forty sects' wards are straining, and Steward Qian's ledger of monthly letters has turned into a ledger of armies. The last blood moon is weeks away, and everyone knows it. |
| 92 | Forty Bandits, Washed and Fed | Whispering Bamboo | 2nd Layer | Iron-Fang has gathered forty of his old men for the march on the Abyss: farmers now, mostly, with families behind the black gate. They are loyal, brave, badly armed and extremely dirty. Before they can storm a fortress, they need a bath, a meal, and a reason to believe they'll come home. |
| 93 | A Traitor's Last Requests | Azure Cloud Sect | 3rd Layer | Gu Hanshan has been a prisoner for years, and for years he has helped: advice in chains, warnings at the rim, confessions nobody asked for. Now, with the moon turning red, he asks the Sect Master for three last requests. He won't say why they're last. Everyone knows. |
| 94 | Xue Chen's Hunt | Qingshi Town | 4th Layer | The last blood moon needs blood. Xue Chen, the Seventh Rung, comes to Qingshi for it with every shadow-born he has. He doesn't want to. He does it anyway. Qingshi, which has held against bandits, beasts, rust and silk, holds again. |
| 95 | The Shadow at the Stair | Sky Isles | 5th Layer | Qing Luan's crane is frantic: Xue Chen is on the tribulation peak, setting his rung early, while the moon is not yet fully red. If the seventh rung is set before the night, the Patriarch's ladder will hold. You climb the cloud stair one last time before the last time. |
| 96 | The Last Evening | Azure Cloud Sect | 6th Layer | One evening left before the moon turns fully red. The Sect Master declares a holiday. There will be no training, no preparations, no war. Only dumplings, lanterns, and everyone you love, all together on one mountain, for one last ordinary night. |
| 97 | The Void Unfolds | Blood Moon Abyss | 7th Layer | The fold is opening. As the moon climbs toward red, the black fortress drifts back out of the void and settles, groaning, onto the Abyss floor where it stood before, gate shut, cages full, prisoners still mid-breath. Iron-Fang's army waits at the rim. Ye Wuming waits at the obelisks. And at the bottom of the world, a boy waits at a mirror. |
| 98 | The Patriarch's Shadow | Blood Moon Abyss | 8th Layer | At the Heart Mirror, at the bottom of the world, Xue Chen sits looking at a boy in a village by a creek. He is the Seventh Rung, the last step of the Patriarch's Ladder, the Patriarch's own shadow. He is also your cousin, and he has asked you to come alone. |
| 99 | Eve of the Last Blood Moon | Azure Cloud Sect | 9th Layer | The last day. Forty sects' armies climb the nine thousand steps and gather at the teleport array. The Sect Master makes her plans. Everyone you love says see you later. At dusk the moon will rise red, the black gate will be waiting, and the Azure Cloud will march into the Abyss to finish what its founders began. |
| 100 | Heavenly Tribulation *(voiced)* | Blood Moon Abyss | **Immortal Ascension** | Under the last blood moon the Azure Cloud marches into the Abyss. A traitor opens the black gate at the cost of his life, the Blood Moon Patriarch falls on his throne, and his remnant flees to the Sky Isles to steal your heavenly tribulation. At the summit, with lightning in your veins, you face your shadow one last time, and climb. |

## The original ten chapters

These are the ten voiced chapters the saga is built around, numbered as they now appear.

**1. The Outer Disciple** (Azure Cloud Sect). The orphan reaches the sect and learns the Nine Precepts, whose last one reads "guard the seal". They draw a pitiful allowance from a stingy steward, beat training puppets and Zhao Kang's attendants, breathe qi for the first time on the stone bridge and chase jade slips for the librarian. When the formation array flares at their touch, Elder Gu takes a keen interest in "that trinket". Red-eyed wolves at the wall are the first corruption in three centuries. The chapter ends with the breakthrough to **Qi Condensation** above the sea of clouds.

**2. Whispers in the Bamboo** (Whispering Bamboo Forest). Gu sends the protagonist and Wei Tong on an herb mission, straight into corrupted wolves and a wolf king driven mad by blood (boss). A hermit heals Wei, and a masked stranger warns them away. A bandit camp is caging Qingshi mortals, and Iron-Fang's strongbox holds a **blood-red Blood Moon command token**. Gu confiscates it "for investigation".

**3. Shadows over Qingshi** (Qingshi Town). With Han Xue, the protagonist investigates the new-moon disappearances through inn gossip, a grieving widow, a ferryman's story of lanterns on the far bank and a merchant's ledger of blood lotus. They fight demonic cultivators in a back alley and suspect the masked wanderer, who points them to the graveyard. The graves are empty and sit on a blood-gathering circle. The kindly temple keeper turns out to be **Deacon Hong of the Blood Moon** (cinematic, boss). His dying words: the taken are in the Abyss, and the Patriarch "has friends in high halls".

**11. Ruins of the Forgotten Sect** (Bamboo Forest ruins and the sect). The library's pages on the seal have been cut out with a Law Hall pass. The hermit reveals that he is **Lan Jue of the Verdant Lotus** and that the pendant is the Lotus Key (cinematic). Zhao Kang, sent by Gu to "keep an eye on" the protagonist, grudgingly fights beside them. The ruins open for their heir, the **Lotus Guardian** tests them (boss) and the reliquary yields the Verdant Lotus Heart Sutra. Gu asks for the sutra and is refused, and Mo explains Gu's grief over his daughter. The protagonist reaches **Foundation Establishment** in the plum garden.

**12. The Inner Sect Tournament** (Azure Cloud Sect). The chapter covers betting pools, a melee, and a semifinal fought as a forced pair with Zhao Kang, which turns the rivalry into respect. Zhao's brother died on a mission Gu assigned. Frenzy Pills are hidden in the tournament supplies under Gu's approval, and Gu demands the pendant "for inspection". In the final, champion **Yan Tie** is poisoned into a frenzy and the protagonist brings him down alive (boss). While everyone watches, Gu raids the pagoda for the master diagram of the seal. **The traitor is revealed** (cinematic) and flees to the Abyss.

**21. Descent into the Blood Moon** (Blood Moon Abyss). Ye Wuming, once a Blood Moon child, guides the protagonist and Han Xue down. They cross the bone field and the blood pools, and Xue Mei's ambush at the obelisks takes Han Xue. The protagonist breaks the obelisks, raids the war camp (and finds letters about a siege of Qingshi and Gu's promise to "Lan"), and frees the cages: Han Xue, Xiao Shi and Widow Liu's son. At the **Altar of Blood** Gu feeds the seal to the Patriarch (cinematic). **Crimson Elder Xue Mei** falls (boss) and the ritual is broken. The protagonist chooses mercy for captured child acolytes and forms a **Golden Core** in the abyss depths.

**22. Siege of Qingshi** (Qingshi Town). Qingshi is held with Zhao Kang and Wei Tong: oil from the redeemed merchant, wards on the gate, the alarm bell, farmers ferried to safety, the graveyard circle sealed for good and river raiders repelled. The merchant confesses that he opened a smuggling tunnel under threat. **Iron-Fang** falls in the market square (boss) and is spared to fight for the town he tried to burn. On the graveyard hill Gu explains himself: the siege was only there to soak the seal with blood. The chapter closes with mourning at the temple and a new plan to build the Great Azure Formation.

**31. Isles Above the Clouds** (Celestial Sky Isles). The Sky Isles open once every sixty years. The protagonist crosses the railing-less jade bridge (Zhao Kang objects), and Zhao apologises among the wind pines. They gather star iron, thunder crystals, cloud silk and phoenix feathers. The Blood Moon is mining the same crystals, which is odd. The corrupted **Jiao serpent** is freed rather than slain (boss). Qing Luan studies the sect's design and says "the stars disagree with it". The protagonist forms a **Nascent Soul** at the cloud gate. Mo promises to check every rune himself.

**41. The Heart Demon** (Blood Moon Abyss and the sect). Mo finds the altered runes (cinematic) and gives the protagonist his sword tassel. A letter from Gu brings the protagonist alone to the Abyss, where Gu confesses: he altered the archive copy twenty years ago, so the new formation is a key, not a lock, and his daughter's soul was fed to the Heart Mirror. The protagonist faces their **Heart Demon** (cinematic, boss) and frees the trapped souls, Gu Lan among them. Back home the sky is red and the formation is lit. **Elder Mo burns his life to turn it back** (cinematic). After the funeral, Bai decodes the Patriarch's true plan: to wear the protagonist's body through the tribulation. The captured Gu is offered redemption instead of execution, the allies swear their oaths, and the protagonist reaches **Soul Transformation** in the repaired formation.

**100. Heavenly Tribulation** (Blood Moon Abyss and the Sky Isles). The whole sect marches (cinematic). Wei Tong and Zhao Kang break the line, and Gu uses the old blood-red token to get inside the black gate and open it, dying in the attempt. Iron-Fang's people are freed and the altar is shattered. The **Blood Moon Patriarch** falls on his throne (cinematic, boss), but his remnant soul flees upward to steal the tribulation. On the summit the ninth bolt is the heart tribulation: the Patriarch rides the protagonist's **Heart Demon** one last time (boss), and heaven's lightning burns him to ash. Then come farewells, the Ascension Stair and **Immortal Ascension**. The epilogue shows the sect ten thousand years safe, the hermit teaching the sutra, Wei Tong shouting at puppets and a star that blinks twice.

## Cultivation, tribulations and alignment

### Realms and minor stages

`world_spec.REALMS` is Mortal, the ten major stages (Qi Condensation, Foundation Establishment, Core Formation, Nascent
Soul, Soul Transformation, Spirit Severing, Void Refinement, Body Integration, Mahayana, Tribulation Transcendence) and
Immortal Ascension. Every major stage has ten minor stages, the 1st to 9th Layer and Great Perfection, grouped in the UI
as Early (1-3), Middle (4-6), Late (7-9) and Great Perfection: "Core Formation · 7th Layer (Late)". The player's
strength (vitality, qi, strike and blast) grows by one step per major stage and a tenth of a step per minor stage.

### Heavenly tribulations

Every major breakthrough is earned by surviving a tribulation (objective type `tribulation`): dark clouds swirl over the
marker and lightning falls in volleys, from 3 bolts for Qi Condensation to 9 for Tribulation Transcendence and the
nine-times-nine (81) Heavenly Tribulation of the finale. Each volley is marked on the ground before it lands; the player
survives by meditating through it (half damage, and the storm does not break the meditation), stepping out of the
circle, or letting qi blunt the bolt. From Nascent Soul on, tribulation beasts and heart shades attack between volleys.
If the lightning would strike the player down, the tribulation starts again. In the ten voiced chapters the tribulation
is an added objective right after the breakthrough meditation; the voiced objectives keep their voice keys.

### Alignment and choices

The player has two scores, Law↔Chaos and Good↔Evil (-100..100 each, neutral between -25 and 25), which give the nine
alignments from Lawful Good to Chaotic Evil (shown on the journal's Cultivation page and in the HUD tooltip). They move
with **moral choices**: 278 of them, offered after a quest's last conversation, about three per chapter. Each chapter of
the new story has one hand-written choice (`choices.py`: spare Gou the Scarred or break his sword hand, give Gu Hanshan
water against orders, warn a demonic cultivator's family before the dam floods, bury Xue Chen or hang him at the gate)
and two from templates that fit the quest (a beggar-thief after a fight, spare herbs after a gathering, a forbidden
technique after training), and seven voiced quests offer one after their voiced lines. Every option continues the story;
options differ in alignment, small rewards, flags and NPC attitudes, and the NPC answers according to their temperament.

Who the player has become changes how the world talks back:

- **conditional lines**: a line can require an alignment (`{"align": "*_evil"}`), a score (`{"align_good": ">=30"}`), a
  realm or minor stage, a flag set by an earlier choice or an NPC's attitude. Righteous elders are cold to evil players,
  demonic cultivators try to recruit them and taunt good ones, juniors bow deeply once the player is a Nascent Soul, and
  townsfolk kneel to a Soul Transformation cultivator. Some lines remember choices (Gou the Scarred, Gu's cup of water);
- **greetings**: every NPC's idle barks are joined by greetings that depend on alignment and realm;
- **alignment rewards**: the end of every chapter gives something extra to good, evil, lawful or chaotic players.

No alignment can block the story: every conversation has unconditional lines and every choice an unconditional option.

### How it is stored

In `godot/data/story.json`:

| Field | Meaning |
|---|---|
| `quests[].rewards.realm`, `.stage` | a breakthrough quest has both (the realm, stage 1); a chapter's last quest has `stage` 2-10; quest 999 has stage 10, quest 1000 the realm Immortal Ascension |
| `quests[].rewards.bonus[]` | `{cond, xp, items, note}`: granted at the end of the quest when `cond` holds |
| `quests[].tier` | the realm index when the quest starts (enemy scaling) |
| objective `{"type": "tribulation", "marker", "bolts", "waves": [{enemy, count, after}]}` | a tribulation: `bolts` strikes in up to nine volleys, a wave spawns after volley `after` |
| dialogue line `cond` | the line shows only when the condition holds |
| objective `choice_prompt`, `choices[]` | `{text, align: {law, good}, reply: [lines], reward: {xp, items}, flag?, attitude?: {npc: delta}, cond?}` |
| `npcs[].greetings[]` | `{text, cond}` idle greetings |
| `threads[]` | `{id, title, beats: [{quest, number, text}]}`, recurring plot threads spanning several volumes (`tools/story/threads.py`); see below |

Condition keys (all must hold): `align` (`"lawful_good"`, `"chaotic_*"`, `"*_evil"`, or a list of them), `align_law` /
`align_good` (`">=30"`, `"<=-25"`), `min_realm` / `max_realm` (a realm name), `min_stage` / `max_stage` (1-10), `flag` /
`not_flag`, `likes` / `dislikes` (an NPC id).

In `Game` (`game_state.gd`): `realm` (0-11), `stage` (0 for Mortal and Immortal, else 1-10), `law`, `good`, `flags`,
`attitude`, `choices` (`"q0123/2"` → option index), signals `realm_changed(name)` (major breakthroughs),
`stage_changed(realm, stage)` (every minor stage, and stage 1 on a breakthrough) and `alignment_changed(id)`; helpers
`alignment()`, `alignment_name()`, `cond_ok(cond)`, `apply_choice()`, `power()`. `Story.stage_name(realm_idx, stage)`,
`Story.realm_label(realm, stage)` and `Story.visible_lines(lines)` do the naming and filtering. Saves are version 3 and
keep the alignment, flags and choices; older saves load with cultivation recomputed from the story.

### Threads: reading 1000 quests as one novel

Each chapter is written and played on its own, but eight named threads run underneath all ten volumes: the traitor
Gu Hanshan, the Lotus Key pendant, Elder Mo's sacrifice, the Patriarch's seven-runged Ladder, and the arcs of Han
Xue, Zhao Kang, the heart demon and the Great Vehicle alliance (`tools/story/threads.py`). Each thread is a handful
of *beats* — one-line recaps landed on the quest where that beat of the story happens. `Story.threads_so_far()`
exposes only the beats the player has already reached, so the journal's **Story So Far** page never spoils ahead of
where they are; `Story.latest_beat()` finds the single most recent one, which `quest_runner.gd` uses to open every
new chapter with a quiet "Previously..." recap, the way a serialised novel reminds its reader what came before.
The same continuity carries into exploration: `godot/scripts/world/monologue.gd` has the protagonist think out loud
while roaming — about wherever they are, what they're meant to be doing, who they're becoming, and (through its own
`CALLBACKS` list, unlocked as the saga advances) what they've already lived through. It never interrupts dialogue,
cinematics, combat, meditation or menus.

## Editing the story

```bash
python3 tools/build_story.py                            # validate + write godot/data/story.json, prints stats
python3 tools/build_story.py --check                    # CI: fails if story.json is stale or anything is invalid
python3 tools/build_story.py --quests docs/QUESTS.md    # also regenerate the list of all 1000 quests
python3 tools/gen_voices.py                             # (re)synthesise only voiced lines whose text/voice changed
python3 tools/gen_voices.py --check                     # CI: lists missing/stale voice files
```

### The original chapters

The chapter files use the helpers from `tools/story/dsl.py`. An objective inherits the map of the previous objective
unless it sets `map=`, and a cinematic objective takes its map from the cinematic. Dialogue lines are
`(speaker, text)` tuples, where `P` is the active protagonist and `N` is the narrator. Their voice keys keep the
original numbering (`q017_o2_l1` is original quest 17, objective 2, line 1; it is quest 17 of the saga), so editing a
line re-synthesises only that line. `appear_from` / `hidden_after` of the original cast use three-digit original ids
(`q085`), which `build_story` maps to the saga's numbering (`q0405`); new ids use four digits.

### The new chapters

A new chapter is an outline in `vol01.py .. vol10.py`:

```python
C("The Burned Array", "sect", "Summary...", cast=[YUN, HAN, ...], foes=["demon_cultivator"],
  items=[...], props=[...], boss=("rung_deacon", "Luo Hui, the First Rung", "Warehouse"),
  beats=[B("probe", "Title", "Quest summary.",
           (HAN, "A line."), (P, "A reply."),            # a segment of dialogue
           "@I:ScholarRock", ">Search the empty desk",   # a tagged step: interact at a marker, with its text
           (N, "Narration for that step."),
           "@T", (HAN, "Closing lines."), prop="treasure_chest"), ...ten beats])
```

Each beat becomes one quest. Its script is split into segments by tags (`@T` talk, `@R` reach, `@F`/`@F2` fight,
`@X` the chapter's boss, `@G` gather, `@M` meditate, `@I` interact; `@R:qingshi_town/TownGate` pins a marker on another
map, `>` sets the objective text, `|` starts a new segment). With two or more segments the script is the quest; a beat
with a single segment is wrapped in the pattern named by its kind (`orders`, `gather`, `hunt`, `battle`, `probe`,
`defend`, `delve`, `boss`, `break`, `stage`, ...). The generator fills everything left open (markers from per-map
pools, enemy counts, pickup counts, objective text from templates, and connecting dialogue from `fillers.py`) and
places every talking NPC at home or on a free marker. Everything is a pure function of the outlines, so a rebuild is
byte-identical. New lines are written to story.json with `"voice": null`; the runtime shows them as text that
advances by itself after a reading time.

A line written as `(speaker, text, cond)` is conditional, e.g. `(GU, "You gave me water once...", {"flag":
"gave_gu_water"})`. Hand-written choices are keyed by `(chapter, beat)` in `choices.py`
(`Ch(prompt, O(text, law=, good=, items=, xp=, flag=, att=, cond=), ...)`); the generator adds two template choices per
chapter, the NPC's reaction to every option, conditional greetings to some opening conversations, the tribulation of a
breakthrough quest and the chapter-end alignment rewards.

### Validation

The validator checks every id against `tools/world_spec.py`. It also enforces these rules:

- 10 volumes, each titled after its realm; 100 chapters; 1000 quests with unique titles;
- each volume breaks through into its realm at the end of its first chapter, with a tribulation objective; every other
  chapter ends at its minor stage (chapter c at stage c); quest 999 reaches Great Perfection and quest 1000 Immortal
  Ascension; (realm, stage) strictly increases from one chapter's end to the next; tribulations never weaken;
- conditions use known keys, alignments, realms and flags set by an earlier choice; every dialogue has at least one
  unconditional line (two for a talk) and every choice 2-4 options, one of them unconditional;
- boss fights have a count of 1, and a new chapter has at most one boss fight; other fights 1-8 enemies;
- `talk` with `at = null` needs the NPC's home to be on that map, with the NPC present at the time;
- a talk NPC never stands on another present NPC's home marker, or on a marker where the same quest spawns enemies;
- in new chapters, no character speaks before `appear_from` or after `gone_after` (Elder Mo stays gone after his
  sacrifice, the Rungs after they fall); the Sky Isles only after they open; the Blood Moon fortress is folded into
  the void between the failed blood moon and the final march;
- lines are at most 32 words, tracker text at most 64 characters; only the known tokens are allowed;
- every chapter of the original story still opens with its intro cinematic on the chapter's map.

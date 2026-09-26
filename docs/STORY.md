# The Main Story: *The Lotus and the Blood Moon*

The main quest line of **Azure Cloud Sect** has 100 quests in 10 chapters, 20 cinematics and a cast of 26 named NPCs.
Every line is voiced, and the protagonist's lines are recorded twice (Lin Feng and Su Yue).

| | |
|---|---|
| Source | `tools/story/`, authored as Python data with a small DSL (`dsl.py`) |
| Compiler / validator | `python3 tools/build_story.py` writes `godot/data/story.json` (`--check` is used in CI) |
| Voices | `python3 tools/gen_voices.py` writes `godot/audio/voice/*.ogg` using Piper TTS (`--check` lists missing or stale files) |
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

## Chapters

**1. The Outer Disciple** (Azure Cloud Sect). The orphan reaches the sect and learns the Nine Precepts, whose last one reads "guard the seal". They draw a pitiful allowance from a stingy steward, beat training puppets and Zhao Kang's attendants, breathe qi for the first time on the stone bridge and chase jade slips for the librarian. When the formation array flares at their touch, Elder Gu takes a keen interest in "that trinket". Red-eyed wolves at the wall are the first corruption in three centuries. The chapter ends with the breakthrough to **Qi Condensation** above the sea of clouds.

**2. Whispers in the Bamboo** (Whispering Bamboo Forest). Gu sends the protagonist and Wei Tong on an herb mission, straight into corrupted wolves and a wolf king driven mad by blood (boss). A hermit heals Wei, and a masked stranger warns them away. A bandit camp is caging Qingshi mortals, and Iron-Fang's strongbox holds a **blood-red Blood Moon command token**. Gu confiscates it "for investigation".

**3. Shadows over Qingshi** (Qingshi Town). With Han Xue, the protagonist investigates the new-moon disappearances through inn gossip, a grieving widow, a ferryman's story of lanterns on the far bank and a merchant's ledger of blood lotus. They fight demonic cultivators in a back alley and suspect the masked wanderer, who points them to the graveyard. The graves are empty and sit on a blood-gathering circle. The kindly temple keeper turns out to be **Deacon Hong of the Blood Moon** (cinematic, boss). His dying words: the taken are in the Abyss, and the Patriarch "has friends in high halls".

**4. Ruins of the Forgotten Sect** (Bamboo Forest ruins and the sect). The library's pages on the seal have been cut out with a Law Hall pass. The hermit reveals that he is **Lan Jue of the Verdant Lotus** and that the pendant is the Lotus Key (cinematic). Zhao Kang, sent by Gu to "keep an eye on" the protagonist, grudgingly fights beside them. The ruins open for their heir, the **Lotus Guardian** tests them (boss) and the reliquary yields the Verdant Lotus Heart Sutra. Gu asks for the sutra and is refused, and Mo explains Gu's grief over his daughter. The protagonist reaches **Foundation Establishment** in the plum garden.

**5. The Inner Sect Tournament** (Azure Cloud Sect). The chapter covers betting pools, a melee, and a semifinal fought as a forced pair with Zhao Kang, which turns the rivalry into respect. Zhao's brother died on a mission Gu assigned. Frenzy Pills are hidden in the tournament supplies under Gu's approval, and Gu demands the pendant "for inspection". In the final, champion **Yan Tie** is poisoned into a frenzy and the protagonist brings him down alive (boss). While everyone watches, Gu raids the pagoda for the master diagram of the seal. **The traitor is revealed** (cinematic) and flees to the Abyss.

**6. Descent into the Blood Moon** (Blood Moon Abyss). Ye Wuming, once a Blood Moon child, guides the protagonist and Han Xue down. They cross the bone field and the blood pools, and Xue Mei's ambush at the obelisks takes Han Xue. The protagonist breaks the obelisks, raids the war camp (and finds letters about a siege of Qingshi and Gu's promise to "Lan"), and frees the cages: Han Xue, Xiao Shi and Widow Liu's son. At the **Altar of Blood** Gu feeds the seal to the Patriarch (cinematic). **Crimson Elder Xue Mei** falls (boss) and the ritual is broken. The protagonist chooses mercy for captured child acolytes and forms a **Golden Core** in the abyss depths.

**7. Siege of Qingshi** (Qingshi Town). Qingshi is held with Zhao Kang and Wei Tong: oil from the redeemed merchant, wards on the gate, the alarm bell, farmers ferried to safety, the graveyard circle sealed for good and river raiders repelled. The merchant confesses that he opened a smuggling tunnel under threat. **Iron-Fang** falls in the market square (boss) and is spared to fight for the town he tried to burn. On the graveyard hill Gu explains himself: the siege was only there to soak the seal with blood. The chapter closes with mourning at the temple and a new plan to build the Great Azure Formation.

**8. Isles Above the Clouds** (Celestial Sky Isles). The Sky Isles open once every sixty years. The protagonist crosses the railing-less jade bridge (Zhao Kang objects), and Zhao apologises among the wind pines. They gather star iron, thunder crystals, cloud silk and phoenix feathers. The Blood Moon is mining the same crystals, which is odd. The corrupted **Jiao serpent** is freed rather than slain (boss). Qing Luan studies the sect's design and says "the stars disagree with it". The protagonist forms a **Nascent Soul** at the cloud gate. Mo promises to check every rune himself.

**9. The Heart Demon** (Blood Moon Abyss and the sect). Mo finds the altered runes (cinematic) and gives the protagonist his sword tassel. A letter from Gu brings the protagonist alone to the Abyss, where Gu confesses: he altered the archive copy twenty years ago, so the new formation is a key, not a lock, and his daughter's soul was fed to the Heart Mirror. The protagonist faces their **Heart Demon** (cinematic, boss) and frees the trapped souls, Gu Lan among them. Back home the sky is red and the formation is lit. **Elder Mo burns his life to turn it back** (cinematic). After the funeral, Bai decodes the Patriarch's true plan: to wear the protagonist's body through the tribulation. The captured Gu is offered redemption instead of execution, the allies swear their oaths, and the protagonist reaches **Soul Transformation** in the repaired formation.

**10. Heavenly Tribulation** (Blood Moon Abyss and the Sky Isles). The whole sect marches (cinematic). Wei Tong and Zhao Kang break the line, and Gu uses the old blood-red token to get inside the black gate and open it, dying in the attempt. Iron-Fang's people are freed, the altar is shattered and the protagonist reaches **Void Refinement**. The **Blood Moon Patriarch** falls on his throne (cinematic, boss), but his remnant soul flees upward to steal the tribulation. On the summit the ninth bolt is the heart tribulation: the Patriarch rides the protagonist's **Heart Demon** one last time (boss), and heaven's lightning burns him to ash. After **Tribulation Transcendence** come farewells, the Ascension Stair and **Immortal Ascension**. The epilogue shows the sect ten thousand years safe, the hermit teaching the sutra, Wei Tong shouting at puppets and a star that blinks twice.

### Realm progression

| Quest | Realm |
|---|---|
| q010 | Qi Condensation |
| q040 | Foundation Establishment |
| q060 | Core Formation |
| q080 | Nascent Soul |
| q090 | Soul Transformation |
| q095 | Void Refinement |
| q099 | Tribulation Transcendence |
| q100 | Immortal Ascension |

## All 100 quests

### Chapter 1 · The Outer Disciple

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 1 | The Mountain Gate | Azure Cloud Sect | Watch the mountain gate open → Speak with the gate disciple → Climb to the main hall → Present yourself to Elder Mo | 60 xp |
| 2 | Rules of the Azure Cloud | Azure Cloud Sect | Report to Elder Gu of the Law Hall → Read the Nine Precepts → Bow before the main hall → Collect your allowance from Steward Qian | 60 xp |
| 3 | Iron Body, Iron Will | Azure Cloud Sect | Find Senior Brother Wei at the weapon rack → Defeat the training puppets → Face the puppets' second wave → Report back to Wei Tong | 80 xp |
| 4 | A Rival's Sneer | Azure Cloud Sect | Answer Zhao Kang's summons in the plum garden → Defeat Zhao Kang's attendants → Tell Senior Brother Wei what happened | 90 xp |
| 5 | Breath of Heaven and Earth | Azure Cloud Sect | Meet Senior Sister Han Xue in the pavilion → Meditate on the stone bridge → Return to Han Xue | 90 xp |
| 6 | Herbs of the West Terrace | Azure Cloud Sect | Speak with Elder Hua at the herb terraces → Gather spirit herbs on the terraces → Find Xiao Man at the lotus pond → Deliver the herbs to Elder Hua | 100 xp |
| 7 | The Scripture Pagoda | Azure Cloud Sect | Visit Elder Bai at the scripture pagoda → Recover the jade slips in the plum garden → Peek at the slips in the quiet pavilion → Return the jade slips to Elder Bai | 100 xp |
| 8 | The Formation Array | Azure Cloud Sect | Meet Elder Mo at the formation array → Recover the lantern oil in the pine woods → Refill the lamps of the formation array → Elder Gu wants a word | 110 xp |
| 9 | Red Eyes in the Pines | Azure Cloud Sect | Investigate the howling in the pine woods → Drive off the red-eyed wolves → Ring the alarm bell at the gate → Wake the gate disciple → Report to Elder Mo | 130 xp |
| 10 | Qi Condensation | Azure Cloud Sect | Receive a Qi Gathering Pill from Elder Hua → Break through at the cliff edge → Present yourself to the Sect Master | 200 xp · **Qi Condensation** |

### Chapter 2 · Whispers in the Bamboo

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 11 | Beyond the Mountain Gate | Azure Cloud Sect | Receive your mission from Elder Gu → Watch your arrival in the bamboo forest → Join Wei Tong on the forest path | 120 xp |
| 12 | Moonshadow Grass | Whispering Bamboo Forest | Find the sunny herb grove → Gather moonshadow grass in the herb grove → Fight off the spirit wolves → Regroup with Wei Tong by the stream | 130 xp |
| 13 | Fangs in the Dark | Whispering Bamboo Forest | Scout the wolf den → Slay the corrupted wolves → Collect fangs from the corrupted wolves → Show the fangs to Wei Tong in the clearing | 140 xp |
| 14 | The King of the Den *(boss)* | Whispering Bamboo Forest | Return to the wolf den → Defeat the corrupted wolf king → Lay the wolf king to rest → Confront the masked stranger in the clearing | 220 xp |
| 15 | The Hermit of the Bamboo | Whispering Bamboo Forest | Carry Wei Tong to the hermit's hut → Beg the hermit for help → Draw water from the spirit spring → Pick lotus leaves by the spring for the poultice → Bring the spring water to the hermit | 150 xp |
| 16 | Smoke on the Ridge | Whispering Bamboo Forest | Meet Wei Tong on the old bridge → Scout the camp from the lookout → Wait for nightfall and steady your breath | 140 xp |
| 17 | Iron-Fang's Camp | Whispering Bamboo Forest | Raid the bandit camp → Free the caged mortals → Cover the prisoners' escape → Recover the stolen spirit stones | 200 xp |
| 18 | The Blood-Red Token | Whispering Bamboo Forest | Search the bandit chief's strongbox → Show the token to Wei Tong → Ask the hermit about the token | 180 xp |
| 19 | Ambush at the Old Bridge | Whispering Bamboo Forest | Survive the ambush on the old bridge → Search the fallen bandits for clues → Speak with the masked wanderer at the stream | 200 xp |
| 20 | Report to the Law Hall | Azure Cloud Sect | Return to the Azure Cloud Sect → Present the token to Elder Gu → Tell Elder Mo about the mission | 160 xp |

### Chapter 3 · Shadows over Qingshi

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 21 | The Town That Whispers | Azure Cloud Sect | Receive the Sect Master's orders → Watch your arrival at Qingshi Town → Speak with the constable at the town gate | 180 xp |
| 22 | The Drunken Crane | Qingshi Town | Walk the main street of Qingshi → Ask Madam Fang for gossip at the inn → Pay respects to Magistrate Zhou | 160 xp |
| 23 | A Mother's Grief | Qingshi Town | Comfort the widow at the well → Question the old ferryman at the docks → Search the river bank → Test the well water for blood qi | 170 xp |
| 24 | Market of Rumours | Qingshi Town | Listen to the gossip in the market square → Question Merchant Jin at the warehouse → Search the guild's crates | 190 xp |
| 25 | The Back Alley | Qingshi Town | Follow the scream into the back alley → Rescue the woman from the demonic cultivators → Pick up the talismans the attackers dropped → Regroup with Han Xue on the main street | 220 xp |
| 26 | The Masked Stranger | Qingshi Town | Ask Madam Fang about the masked guest → Climb the watchtower → Confront the masked wanderer in the fields | 190 xp |
| 27 | Lanterns Among the Graves | Qingshi Town | Search the hillside graveyard at night → Examine the rune circle beneath the graves → Gather the blood-ink rune stones as proof → Decide what to do with Han Xue | 210 xp |
| 28 | The Temple Keeper | Qingshi Town | Visit Keeper Hong at the temple → Watch the temple keeper reveal himself → Fight through Hong's acolytes on the main street | 240 xp |
| 29 | Blood Beneath the Graves *(boss)* | Qingshi Town | Rally the magistrate → Storm the graveyard → Defeat Deacon Hong of the Blood Moon → Follow the dying deacon to his temple | 320 xp |
| 30 | A Debt of Qingshi | Qingshi Town | Tell Widow Liu the truth → Accept Madam Fang's thanks → Cleanse the defiled temple → Head home with Han Xue | 240 xp |

### Chapter 4 · Ruins of the Forgotten Sect

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 31 | Missing Pages | Azure Cloud Sect | Report to the Sect Master → Ask Elder Bai for the Blood Moon records → Watch the journey to the forgotten ruins → Find the gate of the ancient ruins | 260 xp |
| 32 | The Hermit's Secret | Whispering Bamboo Forest | Return to the hermit's hut → Ask the hermit about the ruins → Hear the hermit's story → Accept the hermit's charge | 240 xp |
| 33 | Stones That Remember | Whispering Bamboo Forest | Gather the lotus rune stones around the gate → Deal with Zhao Kang on the forest path → Read the stele in the ruined shrine | 240 xp |
| 34 | Stone Guardians | Whispering Bamboo Forest | Defeat the stone sentinels at the gate → Set the rune stones into the archway → Step through the opened archway | 260 xp |
| 35 | The Guardian of the Lotus *(boss)* | Whispering Bamboo Forest | Find the hermit at the shrine → Stop the sentinels reforming at the gate → Pass the trial of the ancient guardian | 380 xp |
| 36 | Legacy of the Lotus | Whispering Bamboo Forest | Open the Verdant Lotus reliquary → Comprehend the Heart Sutra at the spirit spring → Return to the hermit | 300 xp |
| 37 | Blood in the Shrine | Whispering Bamboo Forest | Drive the Blood Moon scouts from the shrine → Check on Zhao Kang at the old bridge → Gather herbs to treat Zhao Kang's wound | 280 xp |
| 38 | The Law Hall's Interest | Azure Cloud Sect | Return to the sect with Zhao Kang → Show the Heart Sutra to Elder Bai → Answer Elder Gu's summons → Speak with Elder Mo | 240 xp |
| 39 | Preparing the Foundation | Azure Cloud Sect | Ask Elder Hua for a Foundation Pill → Negotiate with Steward Qian → Gather lotus root at the pond at dusk → Tell Xiao Man what you learned in Qingshi | 260 xp |
| 40 | Foundation Establishment | Azure Cloud Sect | Ask Han Xue to guard your breakthrough → Establish your foundation in the plum garden → Receive the Sect Master's news | 400 xp · **Foundation Establishment** |

### Chapter 5 · The Inner Sect Tournament

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 41 | Banners on the Mountain | Azure Cloud Sect | Watch the opening of the Inner Sect Tournament → Take in the tournament stage → Register with Steward Qian → Hear the gossip from Lu Ping | 260 xp |
| 42 | Sharpening the Blade | Azure Cloud Sect | Train with Wei Tong → Defeat four enhanced training puppets → Report back to Wei Tong | 260 xp |
| 43 | The Preliminary Round | Azure Cloud Sect | Report to Elder Mo, the referee → Win the preliminary round → Win the deciding bout of your bracket → Receive Elder Mo's verdict | 280 xp |
| 44 | Whispers at Night | Azure Cloud Sect | Follow Zhao Kang to the moon gate → Confront Zhao Kang at the cliff edge → Tell Han Xue what you found | 280 xp |
| 45 | The Hundred-Disciple Melee | Azure Cloud Sect | Console Wei Tong → Survive the melee → Help Lu Ping gather his scattered winnings → Collect Lu Ping's thanks | 300 xp |
| 46 | The Poisoned Cup | Azure Cloud Sect | Answer Elder Hua's urgent summons → Gather moonbell herbs for the antidote → Ask Xiao Man what she saw → Deliver the herbs to Elder Hua | 300 xp |
| 47 | Partners in the Semifinal | Azure Cloud Sect | Find your partner in the plum garden → Win the paired semifinal with Zhao Kang → Talk with Zhao Kang on the stone bridge | 320 xp |
| 48 | Eve of the Final | Azure Cloud Sect | Answer Elder Gu's summons → Ask Elder Mo about the rule → Steady your dao heart on the stone bridge → Speak with Han Xue in the pavilion | 300 xp |
| 49 | The Final Bout *(boss)* | Azure Cloud Sect | Step up for the final → Defeat the tournament champion → Receive the Sect Master's judgement | 500 xp |
| 50 | The Law Hall's Shadow | Azure Cloud Sect | Find Han Xue → Confront the traitor → Defeat the traitor's Blood Moon accomplices → Check on the wounded Elder Bai on the plaza → Report to the Sect Master at the teleport array | 500 xp |

### Chapter 6 · Descent into the Blood Moon

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 51 | An Unlikely Guide | Azure Cloud Sect | Receive your orders from the Sect Master → Meet the masked wanderer at the sect gate → Descend into the Blood Moon Abyss → Enter the crimson canyon | 400 xp |
| 52 | The Field of Bones | Blood Moon Abyss | Cross onto the field of bones → Clear the sentries on the field of bones → Collect the sentries' demon cores → Talk with Ye Wuming at the canyon mouth | 420 xp |
| 53 | The Blood Pools | Blood Moon Abyss | Harvest blood lotus from the steaming pools → Drive off the blood-fed wolves drinking at the pools → Purify the lotus and steady your qi → Share the purified lotus with Han Xue | 420 xp |
| 54 | Ambush at the Obelisks | Blood Moon Abyss | Examine the demonic obelisk → Fight off the Blood Guard ambush → Regroup with Ye Wuming by the blood pools | 460 xp |
| 55 | Shattering the Obelisks | Blood Moon Abyss | Collect rune fragments around the obelisks → Shatter the heart obelisk with the counter-rune → Deal with the guards drawn by the noise → Confer with Ye Wuming | 460 xp |
| 56 | The War Camp | Blood Moon Abyss | Approach the war camp → Break through the Blood Moon war camp → Seize the sealed letters from the command tent → Read the letters with Ye Wuming | 480 xp |
| 57 | The Iron Cages | Blood Moon Abyss | Reach the prison cages → Defeat the cage wardens → Break open the cages | 500 xp |
| 58 | What the Prisoners Saw | Blood Moon Abyss | Speak with Xiao Shi → Recover stolen medicine for the prisoners → Send the prisoners home with Han Xue | 460 xp |
| 59 | The Altar of Blood *(boss)* | Blood Moon Abyss | Witness the ritual at the Altar of Blood → Defeat Crimson Elder Xue Mei → Disrupt the blood ritual | 700 xp |
| 60 | Core Formation | Blood Moon Abyss | Decide the fate of the captured acolytes with Ye Wuming → Form your golden core in the abyss depths → Return Xiao Shi to his sister → Report to the Sect Master | 900 xp · **Core Formation** |

### Chapter 7 · Siege of Qingshi

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 61 | Smoke on the Horizon | Azure Cloud Sect | Receive the Sect Master's orders → Watch the Blood Moon host approach Qingshi → Meet Magistrate Zhou at the yamen | 500 xp |
| 62 | Walls and Wards | Qingshi Town | Plan the defence with Constable Du → Persuade Merchant Jin to open his warehouse → Carry the oil barrels to the wall → Paint warding talismans on the town gate | 500 xp |
| 63 | The Watchtower | Qingshi Town | Climb the watchtower → Ring the alarm bell → Take your positions with Zhao Kang | 500 xp |
| 64 | Raiders in the Fields | Qingshi Town | Ask Old Pan to ferry the farmers to safety → Drive the raiders from the fields → Report to Wei Tong at the market kitchens | 520 xp |
| 65 | The Graveyard Flank | Qingshi Town | Break the demonic cultivators at the graves → Slay the blood-fed wolves they brought → Seal the blood formation for good → Check on Zhao Kang | 540 xp |
| 66 | The Riverside Assault | Qingshi Town | Race to the docks → Repel the Blood Guards at the docks → Save the medicine crates washed up on the bank → Bring the medicine to Widow Liu at the well | 540 xp |
| 67 | Treachery at the Warehouse | Qingshi Town | Catch Merchant Jin in the back alley → Stop the bandits in the warehouse yard → Collapse the smugglers' tunnel | 560 xp |
| 68 | Iron-Fang Tie Hu *(boss)* | Qingshi Town | Cut down Iron-Fang's lieutenants → Defeat Iron-Fang Tie Hu → Decide Iron-Fang's fate at the temple | 800 xp |
| 69 | The Last Wave | Qingshi Town | Hold the town gate against the last wave → Confront Gu Hanshan on the graveyard hill → Chase Gu into the graves | 800 xp |
| 70 | Dawn over Qingshi | Qingshi Town | Accept the magistrate's thanks → Celebrate at the Drunken Crane → Mourn the fallen at the temple → Report to the Sect Master | 700 xp |

### Chapter 8 · Isles Above the Clouds

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 71 | Stairway of Clouds | Azure Cloud Sect | Receive the Sect Master's orders → Ascend to the Celestial Sky Isles → Meet the star-gazer at the cloud gate | 700 xp |
| 72 | The Jade Bridge | Celestial Sky Isles | Cross the jade bridge → Fight off the Blood Moon pursuers on the bridge → Catch your breath with Han Xue | 720 xp |
| 73 | Isle of Winds | Celestial Sky Isles | Gather cloud silk from the wind-swept pines → Listen to the wind → Talk with Zhao Kang among the pines | 720 xp |
| 74 | The Star-Gazer's Riddle | Celestial Sky Isles | Visit Qing Luan at the star pavilion → Study the star chart → Ask Qing Luan about the red stars | 700 xp |
| 75 | Star Iron of the Fallen Palace | Celestial Sky Isles | Reach the celestial ruins → Defeat the palace guardians → Gather the star iron → Read the palace inscription | 740 xp |
| 76 | The Spirit Vein | Celestial Sky Isles | Drive the Blood Moon miners from the spirit vein → Gather thunder crystals → Examine the miners' cache | 760 xp |
| 77 | Garden of Immortals | Celestial Sky Isles | Enter the overgrown garden → Gather phoenix feathers in the immortal garden → Heed Qing Luan in the garden | 700 xp |
| 78 | The Jiao's Lair *(boss)* | Celestial Sky Isles | Enter the serpent's lair → Defeat the corrupted Jiao serpent → Tend to your wounds with Han Xue | 1100 xp |
| 79 | The Stars Disagree | Celestial Sky Isles | Search the Jiao's hoard → Prepare to leave with Zhao Kang → Say farewell to Qing Luan | 800 xp |
| 80 | Nascent Soul | Celestial Sky Isles | Form your nascent soul at the cloud gate → Deliver the materials to Elder Mo at the formation array → Report to the Sect Master | 1500 xp · **Nascent Soul** |

### Chapter 9 · The Heart Demon

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 81 | The Great Azure Formation | Azure Cloud Sect | Watch Elder Mo inspect the Great Azure Formation → Inspect the Great Azure Formation → Speak with Elder Mo at the hall steps → Spend an evening with Wei Tong | 900 xp |
| 82 | A Letter from the Abyss | Azure Cloud Sect | Collect the letter from Lu Ping → Break the Law Hall seal on the letter → Show the letter to Han Xue | 800 xp |
| 83 | The Mirror Pool | Blood Moon Abyss | Slip past the scavengers on the field of bones → Hear the traitor out in the abyss depths → Approach the Heart Mirror | 900 xp |
| 84 | The Heart Demon *(boss)* | Blood Moon Abyss | Face the reflection in the Heart Mirror → Defeat your heart demon → Still the mirror and free the trapped souls → Return to Gu Hanshan | 1500 xp |
| 85 | Burning Sky over Azure Cloud | Azure Cloud Sect | Race back to the sect gate → Cut through the infiltrators at the gate → Clear the demonic cultivators guarding the array | 1200 xp |
| 86 | Elder Mo's Choice | Azure Cloud Sect | Witness Elder Mo's last stand → Stand with the Sect Master at the hall steps → Find Wei Tong | 1200 xp |
| 87 | Ashes and Incense | Azure Cloud Sect | Toll the great bell nine times → Speak with Elder Hua → Speak with Xiao Man at the lotus pond → Remember Elder Mo at the cliff edge | 1000 xp |
| 88 | What the Patriarch Wants | Azure Cloud Sect | Hear Elder Bai's findings → Compare the altered runes with the Heart Sutra → Face Gu Hanshan in chains at the moon gate | 1100 xp |
| 89 | The Five Oaths | Azure Cloud Sect | Hear Zhao Kang's oath → Hear Xiao Shi's oath → Hear Steward Qian's oath → Collect Xiao Man's medicine bundles for the army → Meet Ye Wuming at the sect gate | 1000 xp |
| 90 | Soul Transformation | Azure Cloud Sect | Set spirit stones into the repaired formation → Transform your soul at the heart of the formation → Receive the Sect Master's blessing | 2000 xp · **Soul Transformation** |

### Chapter 10 · Heavenly Tribulation

| # | Quest | Map | Objectives | Reward |
|---|---|---|---|---|
| 91 | The Last Blood Moon | Blood Moon Abyss | Watch the Azure Cloud Sect gather at the Abyss → Receive the battle plan from the Sect Master → Speak with Iron-Fang at the canyon rim → Stand with Han Xue at the canyon mouth | 2000 xp |
| 92 | Breaking the Line | Blood Moon Abyss | Break the Blood Guard line on the field of bones → Burn the Blood Moon war camp → Regroup with Wei Tong at the blood pools | 2200 xp |
| 93 | The Black Gate | Blood Moon Abyss | Meet Gu Hanshan at the obelisk ring → Wait before the black gate → Break the gate's last seal | 2200 xp |
| 94 | Court of Crimson | Blood Moon Abyss | Clear the fortress courtyard → Kneel beside Gu Hanshan at the gate → Break open the last cages → Find Iron-Fang at the cages | 2400 xp |
| 95 | Void Refinement | Blood Moon Abyss | Defeat the altar's last defenders → Shatter the Altar of Blood → Refine your soul in the void | 3000 xp · **Void Refinement** |
| 96 | The Blood Moon Patriarch *(boss)* | Blood Moon Abyss | Cut down the Patriarch's throne guards → Confront the Blood Moon Patriarch → Defeat the Blood Moon Patriarch → Find Ye Wuming in the abyss depths | 4000 xp |
| 97 | Pursuit to the Heavens | Celestial Sky Isles | Meet Qing Luan at the cloud gate → Fight through the possessed Blood Guards on the jade bridge → Speak with Han Xue on the Isle of Winds | 3000 xp |
| 98 | Remnants of the Blood Moon | Celestial Sky Isles | Purge the possessed cultivators in the garden → Gather thunder crystals to ground the tribulation → Charge the crystals at the spirit vein → Speak with Zhao Kang at the celestial ruins | 3000 xp |
| 99 | Heavenly Tribulation *(boss)* | Celestial Sky Isles | Ascend to the tribulation peak → Survive the heart tribulation and destroy the remnant → Endure the nine bolts of heavenly lightning | 6000 xp · **Tribulation Transcendence** |
| 100 | Immortal Ascension | Celestial Sky Isles | Say farewell to the Sect Master at the cloud gate → Say farewell to Qing Luan → Climb the Ascension Stair → Ascend → Epilogue: the Azure Cloud Sect | 10000 xp · **Immortal Ascension** |

## Editing the story

```bash
python3 tools/build_story.py          # validate + write godot/data/story.json, prints stats
python3 tools/build_story.py --check  # CI: fails if story.json is stale or anything is invalid
python3 tools/gen_voices.py           # (re)synthesise only lines whose text/voice changed
python3 tools/gen_voices.py --check   # CI: lists missing/stale voice files
python3 tools/gen_voices.py --prune   # also delete voice files no longer referenced
```

The chapter files use the helpers from `tools/story/dsl.py`. An objective inherits the map of the previous objective
unless it sets `map=`, and a cinematic objective takes its map from the cinematic. Dialogue lines are
`(speaker, text)` tuples, where `P` is the active protagonist and `N` is the narrator.

These text tokens are resolved at runtime: `{player}` `{junior}` `{senior}` `{sibling}` `{they}` `{them}` `{their}`.
Any line spoken by the player, or containing a token, is *gendered* and gets `<key>_m.ogg` and `<key>_f.ogg`.
Voice keys come from positions: `q017_o2_l1` is quest 17, objective 2, line 1, and `cin_ch05_traitor_s3` is shot 3 of
that cinematic. Inserting a line therefore renames the keys of the lines after it, and `gen_voices.py` re-synthesises
only the lines whose text actually changed.

The validator checks every id against `tools/world_spec.py`. It also enforces these rules:

- boss fights have a count of 1;
- `talk` with `at = null` needs the NPC's home to be on that map, with the NPC present at the time;
- a talk NPC never stands on another present NPC's home marker, or on a marker where the same quest spawns enemies;
- realms only move forward;
- lines are at most 32 words;
- only the known tokens are allowed;
- every chapter's opening quest plays its intro cinematic on the chapter's map.

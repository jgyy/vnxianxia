"""Group conversations: who else is present when the protagonist talks to someone,
and what they say.

Every conversation of the saga has at least two NPCs and the player in it. The
chapter generator (saga_gen) stages each talk objective with one or two
*companions* drawn from, in order of preference,

* the other people of the same quest (whoever the player meets next or met before),
* the chapter's cast (the outline's ``cast=[...]``),
* the *locals* of the place (the minor cast of npcs.MINOR: the deacon of the
  mission hall, the kiln-mistress, the headman of the bamboo village ...),

filtered by the story's timeline (appear_from / hidden_after / gone_after),
by geography (an elder of the sect does not wander the Blood Moon Abyss unless
the outline puts them there) and by the beat itself (a character the beat
talks *about* but never lets speak is somewhere else).

A companion's line has an *intent* (tease, advice, worry, offer, doubt, joke,
agree before the action; praise, relief, question, joke, tease after it), and
the quest giver or the protagonist answers that intent in their own register,
so the exchanges read as people reacting to each other rather than as
interleaved monologues. A companion may also react to who the player has become
(conditional lines on alignment and realm), and add an aside after the player's
moral choice. Signature relationships (Wei Tong and Han Xue, Zhao Kang and Wei
Tong, Madam Fang and Constable Du ...) have their own exchanges.

Slots: ``{giver}`` / ``{Giver}`` the other speaker's short name, ``{comp}`` the
companion's, ``{place}``; protagonist tokens ({player}, {junior}, {they} ...)
are resolved at runtime. Everything here is text-only.
"""

from . import npcs as NP

# characters who travel with the protagonist wherever the story is, when they are in the chapter's cast
ROAM = {NP.HAN, NP.WEI, NP.ZHAO, NP.YAN, NP.SHI, NP.MAN, NP.YE, NP.TIE, NP.RUAN, NP.LIUER, NP.YUN, NP.LU}

START = ("tease", "advice", "worry", "offer", "doubt", "joke", "agree")
END = ("praise", "relief", "question", "joke", "tease")

# ---------------------------------------------------------------- the named cast's interjections
# npc -> [(intent, text)] ; an optional third element (from_quest, to_quest) limits a line to a stretch
# of the saga (numbers in the 2000-quest numbering).
AFTER_MO = (806, 2000)     # Elder Mo gave his life at q0805
BEFORE_MO = (1, 805)

CHIME = {
    NP.YUN: [
        ("advice", "Listen to {giver}. And then listen to your own heart, which is louder and usually wrong. Choose carefully."),
        ("worry", "I will pretend I did not hear where you are going. A sect master should not have to worry about everyone."),
        ("agree", "{Giver} has my full confidence. Also my full attention, which is rarer these days."),
        ("joke", "I came out to look at the clouds. The clouds can wait. Go on, {giver}, I'm only listening."),
        ("tease", "Stand up straight, {player}. You are a disciple of the Azure Cloud, not a question mark."),
        ("praise", "The mountain heard you coming back. So did I. Well done."),
        ("relief", "One less thing on the list of things that keep me awake. Thank you."),
        ("question", "Tell me the part {giver} will leave out. There is always a part."),
        ("doubt", "Alone? Hm. I will allow it. I will also send someone to watch the road."),
        ("offer", "If the way is barred, use my name. It opens most doors and closes a few mouths."),
    ],
    NP.MO: [
        ("tease", "Hmph. Look at that stance. A strong wind would file a complaint."),
        ("advice", "Feet first, then eyes, then sword. In that order. Every time."),
        ("worry", "Come back with all your fingers. I've grown used to counting ten."),
        ("doubt", "Are you certain, {giver}? I've seen {them} trip over a doorstep."),
        ("agree", "Do as {giver} says. For once, someone is making sense."),
        ("joke", "In my day we did this uphill. Both ways. In the snow. With buckets."),
        ("praise", "Adequate. More than adequate. Don't make me say it twice."),
        ("relief", "Hmph. Still in one piece. I wasn't worried. I was sharpening things."),
        ("question", "Well? Did you keep your guard up, or did you just get lucky?"),
        ("tease", "You've got mud to the knees and a grin to the ears. Wipe off one of them."),
    ],
    NP.BAI: [
        ("advice", "If you find anything written down, bring it to me. Even a shopping list. Especially a shopping list."),
        ("joke", "Is this a meeting? Nobody told the pagoda. The pagoda likes to be told."),
        ("agree", "{Giver} is right, and I say so as someone who has read everything and agrees with very little."),
        ("worry", "Mind the old places. Old places have long memories and short tempers."),
        ("tease", "You have ink on your nose, {player}. At least I hope it's ink."),
        ("praise", "Splendid. A footnote in history, at the very least. Possibly a whole paragraph."),
        ("question", "And did you write it down? Nobody ever writes it down. Then I have to guess."),
        ("relief", "Good. I was about to go looking myself, and I would have got lost on the second floor."),
    ],
    NP.GU: [
        ("advice", "Mind the precepts on the way. The road does not excuse anyone from them."),
        ("doubt", "An outer disciple, for this? I will note it. The Law Hall notes everything."),
        ("agree", "Correct. Proceed."),
        ("worry", "Be careful what you touch, and what you carry. Some things are evidence."),
        ("praise", "Acceptable. The record will say so."),
        ("question", "What did you see? Leave nothing out. Small things matter most."),
    ],
    NP.HUA: [
        ("advice", "Take a medicine pouch, {player}. No, two. Heroes always think one is plenty."),
        ("worry", "Your colour is poor. Eat something green before you go. No, not that. That's a moss."),
        ("tease", "Hold still. You have the face of someone about to do something brave and stupid."),
        ("offer", "If anyone comes back bleeding, send them to me first, and to the elders second."),
        ("agree", "{Giver} is right. Also, drink water. Everyone always forgets water."),
        ("joke", "Mind the moonbell on your way out. It bit a deacon this morning. It seemed pleased."),
        ("praise", "Not a scratch? Let me check. Hm. One scratch. I'll allow it."),
        ("relief", "Back, and breathing evenly. That's all a healer asks for, and so rarely gets."),
        ("question", "Did anything bite you? Sting you? Look at you strangely? Tell me everything."),
    ],
    NP.HAN: [
        ("advice", "Watch the left. Everyone forgets the left."),
        ("advice", "Breathe in for four before you go. Your qi runs hot when you hurry."),
        ("tease", "Try not to trip over your own sword this time."),
        ("tease", "Close your mouth, {junior}. You look like a carp waiting for crumbs."),
        ("worry", "If anything feels wrong, turn back. Pride heals slower than bruises."),
        ("doubt", "I'd go myself. {Giver} thinks you're ready. I'm... inclined to agree. Don't gloat."),
        ("offer", "Want company? No? Good. I have forms to practise. Call if you need me."),
        ("agree", "Do what {giver} says. It's a sound plan. I checked it for holes."),
        ("joke", "I don't do small talk. {Giver} does enough for three."),
        ("praise", "Hm. Clean work. I'd have been faster. Not by much."),
        ("praise", "That's twice this month you've made me proud. Stop it. It's unsettling."),
        ("relief", "You're back. Good. I wasn't pacing. The ground needed flattening."),
        ("question", "Tell me the truth. Did you hesitate at any point? Where?"),
        ("tease", "Your sleeve is torn. Either you fought a wolf or a thornbush. I'm betting thornbush."),
    ],
    NP.WEI: [
        ("offer", "I'll come! I'll bring buns. Fighting is better with buns. Everything is better with buns."),
        ("joke", "Dumpling is ready. My sword, not my lunch. Although my lunch is also ready."),
        ("tease", "Look at {them}, all serious. Smile, {junior}! It confuses the enemy."),
        ("worry", "Be careful, all right? I don't want to eat your share of dinner. I'll do it, but I won't enjoy it."),
        ("agree", "What {giver} said. Also, eat first. Nobody wins on an empty stomach."),
        ("advice", "Hit first, apologise later. Actually, don't apologise. They were trying to hit you."),
        ("praise", "Ha! Knew it! I bet Lu Ping a bun you'd be back before dusk. That's my bun."),
        ("relief", "There you are! I was about to go looking with a torch and a very large spoon."),
        ("question", "Was it scary? Tell me it was scary. I need a good story for dinner."),
        ("joke", "I trained three puppets this morning. One of them cried. Well. Creaked sadly."),
        ("advice", "Fight for him too, {junior}. Elder Mo would say adequate. I'll say it louder.", AFTER_MO),
        ("worry", "Come back, all right? I've buried enough people this year. I don't want to be good at it.", AFTER_MO),
        ("praise", "He'd have grunted and looked away. That's how he said proud. I'll just say it. Proud!", AFTER_MO),
    ],
    NP.ZHAO: [
        ("tease", "Try to keep up, village brat. Village friend. Friend brat. Whatever you are."),
        ("doubt", "Why {them}? I'm right here. I'm better dressed and nearly as good."),
        ("offer", "I could come. Not because I'm worried. The Zhao clan simply enjoys being present at victories."),
        ("agree", "Fine. {Giver} is right. Write that down, nobody will believe it later."),
        ("worry", "Don't die. I haven't beaten you properly yet. It would ruin everything."),
        ("joke", "The Zhao clan does not panic. It becomes strategically alarmed."),
        ("advice", "Go around, not through. Only peasants go through. Heroes flank."),
        ("praise", "Not bad. For someone without a family crest. Actually, not bad at all."),
        ("relief", "You're late. I wasn't counting. It was a hundred and twelve breaths. I wasn't counting."),
        ("question", "Did anyone see you win? Witnesses matter. My grandfather says so."),
        ("tease", "You've dirt on your robe. The Zhao clan could lend you a tailor. At a friendly rate."),
    ],
    NP.LU: [
        ("joke", "I bet on you. I always bet on you. I've won four hats and a very confused duck."),
        ("tease", "Is that the famous {player}? The juniors at the gate want a signature. On a bun."),
        ("worry", "Be careful. If you die, who'll make my gossip interesting?"),
        ("agree", "Yes. Definitely. Whatever {giver} said. I was listening. Mostly."),
        ("offer", "I'll watch the road for you. With my eyes open, this time. Probably."),
        ("praise", "Ha! I'm telling everyone. I'm telling them twice, with improvements."),
        ("question", "Well? Details! How many? How big? Did anybody scream? Was it you?"),
        ("relief", "Oh good, you're back. I had a story ready about your tragic death. It was very moving."),
    ],
    NP.QIAN: [
        ("advice", "Keep receipts. For everything. Even for heroics. Especially for heroics."),
        ("doubt", "Is this going to cost the treasury anything? It always costs the treasury something."),
        ("joke", "Every spirit stone has a name. I'm naming the next one after your expenses."),
        ("worry", "Don't break anything that belongs to the sect. I will know. I always know."),
        ("praise", "Well done. I'll record it. In ink, even. That's how impressed I am."),
        ("question", "Did you spend anything? Lose anything? Borrow anything from anyone who writes things down?"),
    ],
    NP.MAN: [
        ("offer", "I made you a pill! It's probably a pill. It's round, anyway."),
        ("worry", "Be careful! If you come back hurt, Elder Hua will make me roll the bandages again."),
        ("joke", "I only dropped three things today. Well. Three things that I know of."),
        ("tease", "You've got the look you get before doing something heroic. It's a very silly look."),
        ("praise", "You did it! I knew you would. The carp knew too. They told me. With bubbles."),
        ("relief", "Oh thank heavens. I was so nervous I watered the lanterns twice."),
        ("question", "Did you see any rare herbs? Any at all? Even ugly ones? Especially ugly ones?"),
    ],
    NP.SHI: [
        ("advice", "Count the ways out before you go in. I always do now. It helps."),
        ("worry", "If it feels like a cage, it is one. Get out fast."),
        ("offer", "I drew a map of that place. It's rough, but the walls are in the right spots."),
        ("agree", "{Giver} knows the way of these things. I trust that. I don't trust much."),
        ("praise", "Thank you. I know you didn't do it for me. Thank you anyway."),
        ("relief", "You came back. People who go out don't always. I'm glad you did."),
        ("question", "Was there anyone else there? Anyone who needed help? You'd tell me?"),
    ],
    NP.LAN: [
        ("advice", "Walk softly. The ground remembers footsteps, and so do the things beneath it."),
        ("agree", "The young one is right. I have been wrong for three hundred years. I can tell."),
        ("joke", "Tea is steeping. It will be ready when you are. Possibly sooner. Possibly next spring."),
        ("worry", "Be careful, child. I have outlived too many brave people."),
        ("doubt", "Hmm. The bamboo would bend first. But you are not bamboo, are you?"),
        ("praise", "The forest noticed. So did I. We are both very old and very hard to impress."),
        ("relief", "Ah. The kettle can stop worrying. It has been worrying since you left."),
        ("question", "And your heart, while you did it? Still? Or thrashing like a fish?"),
    ],
    NP.YE: [
        ("advice", "Don't trust the quiet. It lies."),
        ("worry", "..."),
        ("agree", "Hm."),
        ("doubt", "It's a trap. They're always traps. Go anyway, lotus-bearer, but go sideways."),
        ("offer", "I'll watch the ridge. You won't see me. That's the point."),
        ("praise", "Clean. You didn't waste a step."),
        ("question", "Did anyone follow you back? Look again."),
        ("tease", "You walk like a sect disciple. Loud, and proud of it."),
    ],
    NP.TIE: [
        ("advice", "If they run, let them. If they come back, don't."),
        ("offer", "My boys owe you. Point them at something and they'll shout at it."),
        ("joke", "I wash dishes now. I'm very good at it. Tell no one."),
        ("tease", "You fight like someone who's never been hungry. It shows. It's not a bad thing."),
        ("doubt", "Hm. Sounds like the kind of job I'd have set up as an ambush. Just saying."),
        ("praise", "Ha! Clean work. My old crew would have taken twice as long and stolen the silverware."),
        ("relief", "Back in one piece. Iron-Fang pays his debts, and he doesn't like losing creditors."),
        ("question", "Anyone try to buy you off? They always do. What did they offer?"),
    ],
    NP.GOU: [
        ("tease", "Move along, sect brat. No. Stay. You're useful."),
        ("advice", "They hit from the ditch on the left. Always the left. I should know."),
    ],
    NP.ZHOU: [
        ("advice", "Do it lawfully, if you can. And if you can't, do it quietly."),
        ("worry", "The yamen will cover what it can. The yamen can cover very little."),
        ("agree", "Yes. The magistrate concurs. Formally. I'll have it written up."),
        ("joke", "An honest magistrate sleeps poorly. I haven't slept since spring. It's a very honest spring."),
        ("praise", "Qingshi owes you again. I'm running out of ways to write that in the ledger."),
        ("question", "Will there be a report? A written one? With dates? I love a report with dates."),
    ],
    NP.FANG: [
        ("tease", "Look at you. Like a cat who found the fish and the knife at once."),
        ("joke", "Gossip is free. Wine, noodles and advice are not. This is gossip."),
        ("advice", "Eat before you go. Nobody ever fought well on an empty stomach and a full head."),
        ("worry", "Come back and tell me everything, or I'll have to make it up. My version is worse."),
        ("praise", "The whole street will know by dusk. I'll make sure of it personally."),
        ("relief", "There you are. The noodles were getting cold, and so was my temper."),
        ("question", "Well? Was it who I said it was? I'm always right. I'm just not always paid."),
    ],
    NP.DU: [
        ("advice", "Keep your sword sheathed until it's needed. Then don't keep it sheathed."),
        ("doubt", "I'd rather handle it by the book. The book is thin, though. And the town is big."),
        ("agree", "Noted. Written down. Now it's official."),
        ("offer", "I'll take the militia round the back. They're not good, but they're loud."),
        ("praise", "Good. That's one less entry in my book. My book thanks you."),
        ("question", "Names? Faces? Anything I can write down, cultivator?"),
    ],
    NP.LIU: [
        ("worry", "Mind yourself. Every mother in Qingshi counts you as half a son now."),
        ("advice", "Take water. The well's sweet this season. Heaven keeps its accounts, but it forgets thirst."),
        ("agree", "Listen to {giver}. More sense there than in half this town."),
        ("praise", "Heaven keeps its accounts. I keep mine. You're well in credit, child."),
        ("relief", "Back. Good. I looked twice at every face on the road until it was yours."),
        ("question", "And the others? Did everyone come home? Tell me everyone came home."),
    ],
    NP.PAN: [
        ("advice", "Mind the third plank. And the fifth. The whole world is planks, if you think about it."),
        ("joke", "River's high. Fares are higher. But for you, only very high."),
        ("worry", "The water's restless. When the water's restless, I tie the boat twice."),
        ("praise", "Forty years on this river and I've never seen it look so pleased."),
        ("question", "Anything on the far bank? Lanterns? Faces? I still dream about the lanterns."),
    ],
    NP.JIN: [
        ("offer", "If you need anything bought, sold or quietly moved, you know where the warehouse is."),
        ("doubt", "Is this wise? I'm asking as a merchant. We are professionally cautious."),
        ("joke", "Everything has a price. I'm learning which things shouldn't. It's very expensive, learning."),
        ("praise", "A fine piece of business. I mean that as the highest praise I know."),
        ("question", "Any losses? Any damages? Anything the guild should be quietly paying for?"),
    ],
    NP.HONG: [
        ("advice", "May the ancestors watch over you. And mind the graves on the hill."),
        ("praise", "Such a strong young cultivator. Such vigorous blood. The ancestors smile."),
    ],
    NP.SAGE: [
        ("advice", "The stars say go. The stars also said that sixty years ago, so take it lightly."),
        ("joke", "I have been a memory for a very long time. It is restful. Mostly. You are not restful."),
        ("agree", "{Giver} is right. The stars agree, grudgingly. They hate being agreed with."),
        ("worry", "Don't fall off the isle. Falling takes much longer than you'd think up here."),
        ("tease", "Look up, not down. Down is where the clouds keep their opinions."),
        ("praise", "A star just blinked. It was about you. I'm almost certain."),
        ("question", "And what did the sky say while you were there? It always says something."),
    ],
    NP.YAN: [
        ("offer", "I'll come! Thunder Peak never misses a fight. We only miss breakfast, and that was once."),
        ("joke", "Thunder Peak has a saying: the bigger they are, the louder you shout. I'll shout for you."),
        ("tease", "Your stance is better. Still wrong, but better. I owe you a rematch, you know."),
        ("worry", "Come back. I owe you a life and a rematch. I can't pay either to a ghost."),
        ("agree", "YES. Good plan. I mean, yes. Good plan. Sorry, I get loud."),
        ("advice", "Hit with the whole body. Heart first, then fist. That's how we do it on the peak."),
        ("praise", "HA! That's how it's done! Thunder Peak salutes you! Loudly!"),
        ("relief", "Back already? I was about to shout for you. From here. You'd have heard."),
        ("question", "Did you use the move I showed you? The one with the elbow? Tell me you used the elbow."),
    ],
    NP.LIUER: [
        ("offer", "Can I come? I can swim across the river and back. Twice, if nobody's counting."),
        ("tease", "Mother says immortals don't need to eat. You eat more than me."),
        ("worry", "Be careful, all right? Mother lights incense for you. It's expensive incense."),
        ("praise", "I'm telling everyone! Well, I'm telling Mother. She'll tell everyone."),
        ("question", "Did you fly? Did you use a sword? Can I hold the sword? Just for a moment?"),
        ("joke", "When I grow up I'm going to climb the nine thousand steps. Maybe eight thousand. Then rest."),
    ],
    NP.RUAN: [
        ("doubt", "The Iron Scale would do it differently. Not better, necessarily. Differently."),
        ("agree", "The Iron Scale does not apologise. It reconsiders. I reconsider. {Giver} is right."),
        ("offer", "My sect owes yours. I'd rather pay in sword work than in words."),
        ("tease", "Your mountain is taller. Ours is wider. Both of us are proud of that for no good reason."),
        ("praise", "Well struck. At the Nine Banners I'd have paid money to see that."),
        ("question", "Any Iron Scale colours among them? Tell me honestly. I would rather know."),
    ],
    NP.RUANHAI: [
        ("advice", "Speak plainly and strike plainly. Clever is for people who can afford to lose."),
        ("agree", "Hm. Sound. Go."),
        ("doubt", "I have seen this kind of errand before. It had teeth. Mind them."),
        ("praise", "Well done. I don't say that often. Ask my son. Actually, don't."),
    ],
    NP.JING: [
        ("advice", "Mercy is a discipline, not a mood. Practise it on the way, whatever you meet."),
        ("agree", "The well reflects the moon. It does not argue with it. {Giver} is right."),
        ("worry", "Whatever you find there, do not let it make you smaller than you are."),
        ("praise", "You came back with your heart intact. That is the harder victory."),
        ("question", "Was anyone hungry, there? Was anyone afraid? Did you notice?"),
    ],
    NP.TIANLU: [
        ("joke", "The Zhao clan counts in centuries. And in gold. Mostly in gold."),
        ("tease", "My great-grandson says you're stubborn. He says it with admiration. Disgusting."),
        ("doubt", "In my day we sent servants for this kind of thing. We had wonderful servants."),
        ("praise", "Excellent. I shall mention you in my monthly letter. It is very long. You'll be in paragraph nine."),
    ],
    # ---------------------------------------------------------------- the minor cast
    NP.SHEN: [
        ("advice", "Sign the task off at the mission hall when you're done. Unsigned heroics earn no contribution."),
        ("doubt", "That task isn't on any board. If it isn't on a board, officially, it doesn't exist."),
        ("joke", "I have four thousand task slips and one brush. The brush and I are no longer friends."),
        ("praise", "Recorded, sealed and posted. Three hundred points, and my personal nod."),
    ],
    NP.TAO: [
        ("advice", "If it's hot, don't touch it. If it's glowing, don't even look at it."),
        ("joke", "The third kiln sneezed again. I lost an eyebrow. It'll grow back. Last time it did."),
        ("worry", "Mind the smoke from the east kilns. It's thicker than it looks and ruder than it smells."),
        ("praise", "Good. I'll fire a pill in your honour. Well, in the honour of whoever eats it."),
    ],
    NP.BAO: [
        ("offer", "Take a rice ball. Two. You look like somebody who forgets to eat until they fall over."),
        ("joke", "Wei Tong's been here three times today. It's not even noon. He calls it training."),
        ("praise", "Back? Then you're eating. Heroes eat first. That's the refectory rule. I made it."),
    ],
    NP.LING: [
        ("advice", "If anything with fur looks at you sideways, stand still and look bored. It works on most beasts."),
        ("joke", "The golden carp is two hundred years old and still insufferable. We get along."),
        ("worry", "The beasts were restless all night. Beasts know things before people do."),
    ],
    NP.ZHONG: [
        ("advice", "If you need the mountain awake, ring twice. Once is dinner. Three times is a very bad day."),
        ("joke", "I hear the bell in my sleep. I hear it when it isn't ringing. It's a calling."),
        ("worry", "I felt the bell hum last night, with nobody touching it. Old bells know things."),
    ],
    NP.QIU: [
        ("advice", "A blade is only a blade until someone makes it a promise. Mind which promises you carry."),
        ("worry", "The old swords were humming this morning. They only hum when trouble is walking."),
        ("praise", "The swords are quiet again. That means they approve. They rarely approve."),
    ],
    NP.FAN: [
        ("joke", "Did you hear? No? Well, I did. I'll tell you later. I'll tell everyone later."),
        ("tease", "The juniors are betting you'll come back with a new scar. I bet two. Don't let me down."),
        ("question", "Well? Is it true what they're saying? Which part? All the parts. I need all the parts."),
        ("praise", "Wait until the dormitories hear this. I'll add a dragon. Nobody checks."),
    ],
    NP.TANG: [
        ("advice", "I copied the old records on that place. The second page is useful. The first is mostly complaints."),
        ("question", "Can you describe it exactly? I'm writing it down. How exactly? More exactly than that."),
        ("joke", "Elder Bai called my handwriting adequate. I cried. Then I framed it."),
        ("agree", "{Giver} is right. I checked the annals. Twice."),
    ],
    NP.RUO: [
        ("offer", "Take a cup first. Tea steadies the hand and cools the head."),
        ("advice", "Two leaves and a bud, disciple. Take only what you need, whatever you're picking."),
        ("praise", "Back safe. Sit. Your face needs a cup more than your cultivation does."),
    ],
    NP.KUANG: [
        ("worry", "The village is grateful. The village is also very nervous. Mostly nervous."),
        ("offer", "Take one of our boys as a guide. The forest paths move when strangers walk them."),
        ("praise", "The earth god will hear of this. Loudly. We'll light the big incense."),
    ],
    NP.SHU: [
        ("advice", "Go by the woodcutters' path. The other one has a saw pit, and the saw pit is hungry."),
        ("joke", "Bamboo grows faster than I cut. I've made my peace with it. The bamboo hasn't."),
        ("offer", "I'll carry anything heavy. Heavier than a tree, I'll need a friend."),
    ],
    NP.MENG: [
        ("advice", "Walk upwind. Whatever's out there has a better nose than you."),
        ("doubt", "Those tracks weren't made by anything I have a name for. Be careful which ones you follow."),
        ("praise", "Clean tracking. You'd make a decent hunter, if you ever stop being a hero."),
    ],
    NP.QU: [
        ("advice", "If anything smells sweet in there, hold your breath. Sweet is how poison says hello."),
        ("joke", "I only explode things on purpose. Usually. Don't stand near the blue jar."),
        ("offer", "I'll brew something for the road. It tastes like boiled boots, but it works."),
    ],
    NP.PEI: [
        ("worry", "Nothing to report all week, then everything at once. I hate it when it's everything at once."),
        ("offer", "I'll light the watch lantern for you. If you see it go out, run."),
        ("praise", "I'll log it. 'Disciple returned. Victorious. Somewhat muddy.'"),
    ],
    NP.OUYANG: [
        ("advice", "The classics say a wise man walks around a river. The classics never had to cross this one."),
        ("joke", "My students fear the examination. I fear my students. Nobody fears the classics any more."),
        ("praise", "Remarkable. I'll set it as an essay question. The students will hate you."),
    ],
    NP.QIAO: [
        ("advice", "Follow the thread, not the knot. Anyone who's untangled silk knows that."),
        ("worry", "My weavers are frightened to walk home after dark. Please, make it stop."),
        ("praise", "I'll weave it into the autumn bolt. A little gold line, for you."),
    ],
    NP.WANG: [
        ("offer", "Take this salve. With rice, not wine. Never wine. People always ask about wine."),
        ("worry", "Half my shelves are empty since the trouble began. Medicine doesn't grow on shelves."),
        ("praise", "Good. My drawers will sleep easier. So will I."),
    ],
    NP.YU: [
        ("tease", "Look at that brooding face. I could use you in the second act. You'd die beautifully."),
        ("joke", "Tonight I die of heartbreak. Tomorrow, of poison. Sundays I rest."),
        ("praise", "Bravo! I'll put it in an opera. I'll make you taller. Everyone's taller in opera."),
    ],
    NP.BI: [
        ("worry", "The children ask about you, you know. Don't make me tell them anything sad."),
        ("advice", "Wipe your feet when you come back. Heroes track in the worst mud."),
        ("praise", "The little ones will want the story at bedtime. Keep it short. Keep the blood out."),
    ],
    NP.LEI: [
        ("offer", "The militia will hold the street. The militia will mostly hold the street."),
        ("doubt", "Should my men go first? They're very brave. From a distance."),
        ("praise", "Good work, cultivator. I'll have the lads cheer. They're good at cheering."),
    ],
    NP.HUO: [
        ("advice", "Boatmen talk after the third cup. Buy the third cup, not the first."),
        ("joke", "Fights outside, singing inside, paying always. You'd be amazed who forgets the third one."),
        ("praise", "A round on the house! No. Half a round. A quarter. Here, have a cup."),
    ],
    NP.KU: [
        ("advice", "Down here everything has a price. Especially directions. These ones are free. Once."),
        ("doubt", "I don't take sides. But if I did, I wouldn't take that one. Just saying."),
        ("praise", "You're still alive. That's worth more than anything I'm selling."),
    ],
    NP.HEI: [
        ("tease", "The moon is watching you, heir. It's very fond of you. Hungrily fond."),
    ],
    NP.QINGYI: [
        ("advice", "Please keep to the paths. The clouds between isles bruise, and they remember who stepped on them."),
        ("worry", "The isles have been restless. Even the rice leans away from the wind now."),
        ("praise", "The terraces sing a little louder. That is how the isles say thank you."),
    ],
    NP.HE: [
        ("advice", "Walk slowly on the isles. Haste offends the cranes, and the cranes carry grudges for centuries."),
        ("worry", "The cranes circled the wrong way this morning. They know weather before heaven does."),
        ("praise", "The cranes bowed to you. They bowed to the last immortal once, then took it back."),
    ],
    NP.SHUREC: [
        ("advice", "Everything is written somewhere. The trouble is finding which somewhere."),
        ("question", "May I record it? Every life is a line in a book. Yours is getting rather long."),
        ("praise", "I have written it down. In the good ink. The good ink is for rare things."),
    ],
}

# ---------------------------------------------------------------- answers to a companion
# the quest giver answers the companion's intent, in their own register
RESP_GIVER = {
    "elder": {
        "tease": ["Enough, {comp}. Let {them} go with some dignity left.", "Hm. {Comp} is not wrong. {Comp} is rarely wrong about posture."],
        "advice": ["Listen to {comp}. It is good advice, and rarer than it should be.", "Yes. Do that. {Comp} has earned the right to say it."],
        "worry": ["{player} will manage, {comp}. I would not send {them} otherwise.", "Worry is a fine servant, {comp}. A poor master."],
        "offer": ["No, {comp}. You have your own duties, and I need you where you are.", "Your offer is noted, {comp}, and declined. Kindly."],
        "doubt": ["I did not ask whether it was wise, {comp}. I asked who would go.", "Noted, {comp}. Overruled, but noted."],
        "joke": ["(sighs) Thank you, {comp}. That was very... something.", "Why do I let you near serious conversations, {comp}?"],
        "agree": ["Thank you, {comp}. Now, where was I.", "Just so."],
        "praise": ["Yes. Well done indeed.", "{Comp} says it louder than I would. I mean it just as much."],
        "relief": ["We were not worried, {comp}. We were attentive.", "Hm. Yes. Relief is permitted. Briefly."],
        "question": ["Answer {comp}, and then answer me. In that order.", "A fair question. I would like to hear the answer too."],
    },
    "peer": {
        "tease": ["Leave {them} alone, {comp}. That's my job.", "Ignore {comp}. Everyone else does."],
        "advice": ["Listen to {comp}. I hate saying it, but listen.", "What {comp} said. I was about to say it. Slower."],
        "worry": ["{player}'ll be fine, {comp}. Probably. Mostly.", "Stop fussing, {comp}. You're making {them} nervous. You're making me nervous."],
        "offer": ["No, {comp}. You'd just get in the way. Lovingly.", "You're staying here, {comp}. Someone has to guard the buns."],
        "doubt": ["Have a little faith, {comp}.", "You said the same last time, {comp}. And the time before."],
        "joke": ["Please stop talking, {comp}.", "That wasn't funny, {comp}. ...It was a little funny."],
        "agree": ["See? Even {comp} agrees. It must be true.", "Thank you, {comp}."],
        "praise": ["Don't encourage {them}, {comp}. The head's big enough already.", "Ha. {Comp}'s right. That was good."],
        "relief": ["You weren't worried, {comp}. You said so. Twice.", "We all were. Some of us hide it better."],
        "question": ["Go on, tell {comp}. {Comp} won't sleep otherwise.", "Yes, tell us. All of it."],
    },
    "town": {
        "tease": ["Oh, hush, {comp}. Let the immortal work.", "{Comp}! Manners!"],
        "advice": ["Listen to {comp}. We've lived here a long time.", "That's sound, that is."],
        "worry": ["{player} will be all right, {comp}. The immortal always is. Mostly.", "Don't frighten the immortal, {comp}."],
        "offer": ["You'll do no such thing, {comp}. Leave it to them.", "Thank you, {comp}, but it's cultivator's work."],
        "doubt": ["Have some faith, {comp}. {player} has never let us down.", "We've no one else to ask, {comp}."],
        "joke": ["(laughs despite herself) Oh, {comp}.", "Not now, {comp}. Later. Over wine."],
        "agree": ["There. {Comp} agrees. Settled.", "Just so, just so."],
        "praise": ["Heaven bless the immortal, {comp}. Heaven bless {them}.", "That's the truth, {comp}."],
        "relief": ["We all were, {comp}. We all were.", "Light some incense tonight, {comp}. For luck."],
        "question": ["Yes, tell us everything.", "Go on. The whole town will want to know anyway."],
    },
    "rogue": {
        "tease": ["Shut it, {comp}.", "Heh. {Comp}'s got a point."],
        "advice": ["Listen to {comp}. {Comp}'s survived worse.", "Good advice. Free, too. Rare."],
        "worry": ["{player}'ll live, {comp}.", "Worry later, {comp}. Move now."],
        "offer": ["No. Stay out of sight, {comp}.", "Not this time, {comp}."],
        "doubt": ["Maybe. Go anyway.", "Probably, {comp}. Doesn't change anything."],
        "joke": ["Heh.", "Not the time, {comp}."],
        "agree": ["Hm.", "Right."],
        "praise": ["Heh. Not bad.", "Told you, {comp}."],
        "relief": ["Hm. Good.", "Don't make a habit of it, {comp}."],
        "question": ["Tell it short.", "Go on."],
    },
    "villain": {
        "tease": ["Your friends are loud, heir. Loud things break first."],
        "advice": ["Advice from a dead sect's servant. How touching."],
        "worry": ["Worry is wise, little one. Keep it close."],
        "offer": ["Bring them all. The moon is hungry."],
        "doubt": ["Doubt. Good. Doubt is a door, and I have the key."],
        "joke": ["Laugh while you have breath for it."],
        "agree": ["Even your friends agree with me, heir. Think on that."],
        "praise": ["Enjoy it. Victories are short, down here."],
        "relief": ["Relief. How sweet. How brief."],
        "question": ["Ask, and I may even answer."],
    },
}
GIVER_GROUP = {"elder": "elder", "prisoner": "elder", "peer": "peer", "junior": "peer", "town": "town",
               "rogue": "rogue", "demonic": "villain"}

# the protagonist answers a companion
RESP_PLAYER = {
    "tease": ["I'm standing right here, you know.", "Very funny.", "One day I'll think of a comeback. Today is not that day.",
              "Thank you. I'll treasure that forever."],
    "advice": ["I'll remember that.", "Good advice. I'll try to take it.", "Noted. Carefully noted.", "Thank you. Truly."],
    "worry": ["I'll be careful. I promise.", "I'll come back. I always do.", "Don't worry. Worry for both of us, if you must."],
    "offer": ["Thank you. I'll call if I need you.", "Keep it ready. I might.", "That means more than you know."],
    "doubt": ["I'll prove you wrong. Politely.", "Fair. I have my doubts too.", "Then come and watch."],
    "joke": ["...", "I'm not laughing. I'm breathing strangely.", "Why are you like this?"],
    "agree": ["Then it's settled.", "Good. We're all agreed.", "Right. Then I'll go."],
    "praise": ["It wasn't only me.", "Thank you. I had help.", "Please stop. My ears are turning red."],
    "relief": ["I'm fine. Really. Mostly.", "I missed you too.", "Sorry I worried you."],
    "question": ["Later. Over tea. I promise.", "More or less. Mostly less.", "It's a long story. The short version: yes."],
}

# ---------------------------------------------------------------- reacting to who the player has become
# companion category -> [(condition, line)]; shown only when the condition holds
COND = {
    "elder": [
        ({"align": "*_evil"}, "(to {giver}, quietly) Watch this one. The eyes have changed."),
        ({"align": "*_good"}, "(to {giver}) The juniors want to be like {them}. I find I don't mind."),
        ({"align": "chaotic_*"}, "(dryly) Try to break only the rules that deserve it, {player}."),
        ({"align": "lawful_*"}, "The Law Hall speaks well of you. The Law Hall speaks well of almost no one."),
        ({"min_realm": "Nascent Soul"}, "(studying you) Your soul sits deep now. I can feel it from here."),
    ],
    "peer": [
        ({"align": "*_evil"}, "(to {giver}, low) Are we sure about this? You've heard what people are saying."),
        ({"align": "*_good"}, "People keep thanking me for things you did. It's getting embarrassing."),
        ({"align": "chaotic_*"}, "If the Law Hall asks, I wasn't here and neither were you."),
        ({"align": "lawful_*"}, "You and your precepts. One day you'll bow to a door for being properly shut."),
        ({"min_realm": "Core Formation"}, "Your core hums when you stand still. Did you know? It's very distracting."),
    ],
    "junior": [
        ({"min_realm": "Nascent Soul"}, "(bows three times, to be safe) Sorry, {senior}! It's hard not to bow now."),
        ({"align": "*_evil"}, "(half a step back) I'll be good, {senior}. I'm always good."),
        ({"align": "*_good"}, "The little ones tell stories about you, {senior}. Good ones!"),
    ],
    "town": [
        ({"min_realm": "Soul Transformation"}, "(starts to kneel, then stops) Heavens. You feel like weather now."),
        ({"align": "*_evil"}, "(nervously, to {giver}) Is it safe to talk in front of them?"),
        ({"align": "*_good"}, "My mother lights incense for you. She says it's the least she can do."),
    ],
    "rogue": [
        ({"align": "*_evil"}, "You've got the look now. I used to have it. Careful."),
        ({"align": "*_good"}, "Still soft. Still alive. Still surprises me."),
        ({"align": "chaotic_*"}, "Heh. The sect never did tame you."),
    ],
    "demonic": [
        ({"align": "*_evil"}, "(smiling) You smell of the right things now, heir."),
        ({"align": "*_good"}, "So righteous. So tired. It shows."),
    ],
}

# a companion's aside after the player's moral choice, by the choice's direction
ASIDE = {
    "elder": {"good": ["(to {giver}) Kind. Good. Kindness is a harder road than it looks.",
                       "(to {giver}) Remember this one, when the next choice is harder.",
                       "(to {giver}, softly) The founders chose well, whoever chose {them}."],
              "evil": ["(to {giver}, quietly) I did not like that. I will remember it.",
                       "(to {giver}, very quietly) That is how it begins. I have seen it begin before.",
                       "(to {giver}) Say nothing. My silence will say enough for both of us."],
              "lawful": ["(to {giver}) The Law Hall could not have ruled better.",
                         "(to {giver}) By every precept I know. Note it in the record."],
              "chaotic": ["(to {giver}) Unorthodox. I suppose we were young once.",
                          "(to {giver}) The precepts would object. The precepts are not here."],
              "neutral": ["(to {giver}) Measured. I would have chosen the same.", "(nods slowly to {giver}) A careful answer."]},
    "peer": {"good": ["(to {giver}) Told you. Soft as a steamed bun. Don't tell {them} I said so.",
                      "(to {giver}) That's the {player} I know.",
                      "(to {giver}) See? That's why I follow {them} into bad places."],
             "evil": ["(muttering, to {giver}) That was cold.",
                      "(to {giver}) Did that sit right with you? It didn't with me.",
                      "(to {giver}, low) We should talk about that. Later."],
             "lawful": ["(to {giver}) {player} and the precepts. Should we leave them alone together?",
                        "(to {giver}) Correct again. It's exhausting, isn't it?"],
             "chaotic": ["(to {giver}) The elders will hate that. I love it.",
                         "(grinning at {giver}) You didn't see that. I didn't see that."],
             "neutral": ["(to {giver}) Sensible. Boring, but sensible.", "(to {giver}) Can't argue with that. I tried."]},
    "junior": {"good": ["(beaming at {giver}) I'm going to tell everyone about that!",
                        "(whispering to {giver}) I want to be like that when I'm older."],
               "evil": ["(tugging {giver}'s sleeve) Is that allowed?", "(hiding behind {giver}) Oh."],
               "lawful": ["(to {giver}) That's exactly what the precepts say! I memorised them!",
                          "(to {giver}) Properly done! Somebody write it down!"],
               "chaotic": ["(to {giver}) Are we allowed to do that? I'm not telling anyone.",
                           "(whispering to {giver}) That was amazing."],
               "neutral": ["(to {giver}) That makes sense. I think.", "(to {giver}) Hm. Yes. Probably right."]},
    "town": {"good": ["(to {giver}) Heaven bless the immortal. Truly.", "(to {giver}) The whole street will hear of this kindness."],
             "evil": ["(to {giver}, nervously) Should we... say something?", "(to {giver}, whispering) Don't look at them. Just nod."],
             "lawful": ["(to {giver}) Proper. Very proper. The magistrate will be pleased.",
                        "(to {giver}) By the law. That's all anyone asks."],
             "chaotic": ["(to {giver}) Well! That's one way to do it.", "(to {giver}) Bold. Don't tell the constable."],
             "neutral": ["(to {giver}) Fair's fair.", "(to {giver}) Can't say fairer than that."]},
    "rogue": {"good": ["(to {giver}) Soft. Soft wins more than people think.", "(to {giver}) Terrible bandit, that one. A compliment."],
              "evil": ["(to {giver}) Careful. I know where that road ends.", "(to {giver}) Heh. Cold. The road teaches that."],
              "lawful": ["(to {giver}) Rules. Hm. It was the right call.", "(to {giver}) Proper as a magistrate."],
              "chaotic": ["(to {giver}) Heh. Knew it.", "(to {giver}) The sect never did tame {them}."],
              "neutral": ["(to {giver}) Practical.", "(to {giver}) No argument."]},
    "demonic": {"good": ["Mercy. How exhausting."], "evil": ["Oh, you'd do well down here."],
                "lawful": ["Obedient little heir."], "chaotic": ["Almost one of us."], "neutral": ["Cold. Good."]},
}

# ---------------------------------------------------------------- facing an enemy together
# an ally standing beside the player when the talk is with a demonic cultivator
CONFRONT = {
    "elder": ["Say what you came to say. Then leave this place, while you still have legs to leave on.",
              "Mind your tongue before the heir. My patience is older than your master's grudge."],
    "peer": ["Keep talking. I'm counting the ways this ends badly for you.",
             "Stand behind me, {player}. No? Fine. Beside me, then.",
             "Say one more word about {their} blood and you'll be picking up your teeth."],
    "junior": ["(voice shaking) We're not afraid of you. Well. I'm a little afraid. But we're not moving."],
    "town": ["(clutching a broom) The immortal isn't alone. Remember that."],
    "rogue": ["I know your kind. I used to take your money. Talk fast.",
              "Heh. Big words. Your master used to say those too. Look where he is."],
}

# ---------------------------------------------------------------- at the scene, without a quest giver
# two companions share a moment at a reach / interact objective
FIELD = {
    "elder": ["Look carefully. Old places keep their secrets in the corners.",
              "Someone was here before us. Not long ago, either.",
              "Mind where you step. This ground has seen worse than us."],
    "peer": ["I don't like this. It's too quiet. Quiet means someone is listening.",
             "Over there. See? Someone tried to hide their tracks and did it badly.",
             "Well. That's not something you see every day. I'd rather not see it again."],
    "junior": ["Is it supposed to look like that? It doesn't look like it's supposed to look like that.",
               "I'll hold the lantern. I'm very good at holding lanterns."],
    "town": ["My grandmother told stories about this place. I thought she made them up.",
             "Heavens. Nobody comes out here any more. Now I know why."],
    "rogue": ["Somebody's been using this place. Recently. Carefully.", "Keep your voice down. Voices carry out here."],
    "demonic": ["Our master's work. Admire it while you can."],
}
FIELD_ANSWER = {
    "elder": ["Agreed. Slowly, then.", "Yes. And they wanted it found. That worries me more."],
    "peer": ["Then we'd better be quick.", "I see it. Stay close.", "Right. Eyes open, everyone."],
    "junior": ["Right behind you! Well. Slightly behind you.", "I've got the lantern!"],
    "town": ["Heavens preserve us.", "Let's not stay long."],
    "rogue": ["Hm.", "Then let's be quieter than they were."],
    "demonic": ["Not for long."],
}
FIELD_PLAYER = ["Stay close. Both of you.", "Let me look first.", "Quietly, then.", "We'll go carefully.",
                "Whatever happens, we stay together.", "I see it too. Let's find out what it means."]

# ---------------------------------------------------------------- signature relationships
# (companion, giver) -> [(companion line, giver reply)]; used in both directions when written so
PAIRS = {
    (NP.WEI, NP.HAN): [("Han Xue says that to everyone. She told me my breathing was sloppy. I was asleep.",
                        "It was sloppy, Wei Tong. Even asleep."),
                       ("Senior Sister, did you eat? You never eat. Here, half a bun. The bigger half.",
                        "...Thank you. Don't tell anyone.")],
    (NP.HAN, NP.WEI): [("Wei Tong, you have crumbs on your sword.", "They're lucky crumbs. Dumpling likes them."),
                       ("If he offers you a bun before a fight, refuse. He'll share it anyway.",
                        "Everyone fights better with a bun, Senior Sister. It's science.")],
    (NP.ZHAO, NP.WEI): [("Must you always talk about food, Wei Tong?", "Must you always talk about your clan, Zhao Kang?"),
                        ("The Zhao clan would have sent a servant for this.", "The Zhao clan's servants would have eaten my lunch.")],
    (NP.WEI, NP.ZHAO): [("Zhao Kang's scared. Look, his ears are red.", "My ears are red because it's cold, you boiled dumpling."),
                        ("Don't mind Zhao Kang. He says rude things when he's fond of people.", "I say rude things when they're true.")],
    (NP.ZHAO, NP.HAN): [("Senior Sister, with respect, I could do this faster.", "With respect, Zhao Kang, you couldn't."),
                        ("I bow to no one. Except Senior Sister Han. Occasionally.", "Occasionally is correct.")],
    (NP.HAN, NP.ZHAO): [("Zhao Kang, stop posing. Nobody's painting you.", "Somebody should be. The light is excellent.")],
    (NP.LU, NP.QIAN): [("Steward, I need a new lantern for the gate.", "You needed a new lantern last month, Lu Ping. What did you do with it?")],
    (NP.QIAN, NP.LU): [("Lu Ping, have you been betting sect property again?", "Only my hat, Steward! And a duck. The duck was mine.")],
    (NP.MAN, NP.HUA): [("Elder, I only dropped one jar today!", "It was the jar of rare jars, Xiao Man.")],
    (NP.HUA, NP.MAN): [("Xiao Man, put that down before it explodes.", "It won't explode, Elder! ...Will it?")],
    (NP.SHI, NP.MAN): [("My sister's been feeding me since dawn. Please rescue me.", "You're too thin! Thin brothers get cold!")],
    (NP.MAN, NP.SHI): [("Brother, did you eat? You didn't eat. I can tell.", "I ate twice, Man. You watched me.")],
    (NP.BAI, NP.HUA): [("Elder Hua, have you seen my spectacles?", "On your head, Elder Bai. As they were yesterday.")],
    (NP.HUA, NP.BAI): [("Elder Bai, you've been in the pagoda for three days. Eat something.", "I had a very nourishing scroll.")],
    (NP.YUN, NP.MO): [("Elder Mo, you're scowling again.", "I'm thinking, Sect Master. It looks the same from outside.")],
    (NP.MO, NP.YUN): [("Sect Master, you should be resting.", "And you should be retired, Mo. We both make sacrifices.")],
    (NP.FANG, NP.DU): [("Constable, you owe me for three bowls of noodles.", "Put it on the magistrate's account, Madam Fang.")],
    (NP.DU, NP.FANG): [("Madam Fang, your gossip is faster than my runners.", "My gossip is paid in wine, Constable. Your runners aren't.")],
    (NP.FANG, NP.ZHOU): [("Magistrate, you look tired. Wine?", "Not on duty, Madam. ...Perhaps a small one.")],
    (NP.LIUER, NP.LIU): [("Mother, can I go too? Please?", "No, and don't ask again. ...Carry the water first.")],
    (NP.LIU, NP.LIUER): [("Er, stand up straight. You're talking to an immortal.", "Mother, it's only {player}!")],
    (NP.YAN, NP.ZHAO): [("Zhao Kang! When do we fight again?", "Never, Yan Tie. You shout during duels."),
                        ("Thunder Peak says hello! Loudly!", "Thunder Peak always says hello loudly, Yan Tie.")],
    (NP.ZHAO, NP.YAN): [("Yan Tie, lower your voice. The mountain is asleep.", "THE MOUNTAIN LIKES ME, ZHAO KANG.")],
    (NP.TIE, NP.DU): [("Constable. I've come to report myself for being useful.", "Noted, Iron-Fang. You're still on my list.")],
    (NP.DU, NP.TIE): [("I'm watching you, Iron-Fang.", "Good. Somebody should. I'm very watchable now.")],
    (NP.LAN, NP.YUN): [("The Sect Master looks tired. More tea?", "Your tea could wake the dead, hermit. Not tonight.")],
    (NP.YE, NP.HAN): [("...", "He means be careful. He always means be careful.")],
    (NP.HAN, NP.YE): [("Ye Wuming, say something useful for once.", "...Left."), ],
    (NP.PAN, NP.JIN): [("Merchant, your barges keep scraping my ferry.", "Old Pan, your ferry keeps being in the way of my barges.")],
    (NP.JIN, NP.ZHOU): [("Magistrate, the guild's accounts are open to you. All of them. Truly.", "Truly, Jin? Even the second set?")],
    (NP.RUAN, NP.ZHAO): [("Zhao Kang. Your clan's banner is crooked.", "Ruan Jingtao. Your sect's mountain is short.")],
    (NP.TIANLU, NP.ZHAO): [("Great-grandson, you're slouching.", "I am standing heroically, Ancestor.")],
    (NP.ZHAO, NP.TIANLU): [("Ancestor, please, not the letters again.", "The letters are a family tradition, boy.")],
    (NP.BAO, NP.WEI): [("Wei Tong, you've eaten your ration and mine.", "I'm training, Old Bao! Training is hungry work!")],
    (NP.WEI, NP.BAO): [("Old Bao makes the best rice balls on the mountain.", "I make the only rice balls on the mountain, Wei Tong.")],
    (NP.SHEN, NP.QIAN): [("Steward, the mission hall needs brushes.", "The mission hall needed brushes last year, Deacon.")],
    (NP.TAO, NP.HUA): [("Elder, the third kiln sneezed again.", "Then feed it less charcoal and more patience, Hongyu.")],
    (NP.LING, NP.MAN): [("Xiao Man, stop feeding the golden carp.", "He looked hungry! He always looks hungry!")],
    (NP.FAN, NP.LU): [("Lu Ping, did you hear about the Refectory?", "I heard it first, Fan Rui. I always hear it first.")],
    (NP.TANG, NP.BAI): [("Elder, I finished copying the third annal.", "Adequately? ...No. Well. Very well.")],
    (NP.JING, NP.YUN): [("Sect Master, you carry too much alone.", "So I'm told, Abbess. Usually by people carrying more.")],
}

# ---------------------------------------------------------------- the minor cast's districts
# where a local lives and which neighbouring places count as their district
DISTRICT = {
    NP.SHEN: ("sect", ["MissionHall", "ContributionPavilion", "OuterSectHall"]),
    NP.TAO: ("sect", ["PillKilnYard", "MedicineValley", "HerbGarden"]),
    NP.BAO: ("sect", ["Refectory", "OuterDormitories", "LaundryStream"]),
    NP.LING: ("sect", ["SpiritBeastGarden", "CraneRoost", "Waterfall"]),
    NP.ZHONG: ("sect", ["BellTower", "DrumTower", "SunriseTerrace"]),
    NP.QIU: ("sect", ["SwordTomb", "SwordWashPool", "SwordPeak", "SwordPeakPath", "CableBridge"]),
    NP.RUO: ("sect", ["TeaTerraces", "SpiritOrchard"]),
    NP.KUANG: ("bamboo_forest", ["BambooVillage", "VillageShrine", "Waterwheel", "SacredSpring"]),
    NP.SHU: ("bamboo_forest", ["WoodcutterCamp", "CharcoalKilns", "PandaGrove"]),
    NP.MENG: ("bamboo_forest", ["HunterLodge", "TigerRidge", "WolfDen", "SpiderHollow"]),
    NP.QU: ("bamboo_forest", ["AlchemistCottage", "MushroomRing", "PoisonMarsh", "HerbGrove"]),
    NP.PEI: ("bamboo_forest", ["ForestWatchpost", "ForestCrossroads", "ForestGate", "SmugglersTrail"]),
    NP.OUYANG: ("qingshi_town", ["Academy", "ExamHall", "BellPavilion"]),
    NP.QIAO: ("qingshi_town", ["SilkWorkshop", "DyeYard"]),
    NP.WANG: ("qingshi_town", ["Pharmacy", "SouthMarket"]),
    NP.YU: ("qingshi_town", ["OperaStage", "TempleFair"]),
    NP.BI: ("qingshi_town", ["Orphanage", "CityGodTemple", "Temple"]),
    NP.LEI: ("qingshi_town", ["Barracks", "NorthGate", "EastGate", "ExecutionGround", "TownGate"]),
    NP.HUO: ("qingshi_town", ["Tavern", "Brewery", "LowerDocks", "BoatYard"]),
    NP.KU: ("blood_abyss", ["ShadowMarket", "SlaveMines", "BloodRiver"]),
    NP.QINGYI: ("sky_isles", ["JadeTerraces", "PeachGarden", "LotusLake", "ImmortalPalace", "PalaceCourt"]),
    NP.HE: ("sky_isles", ["CraneIsle", "WindTemple", "MoonIsle"]),
    NP.SHUREC: ("sky_isles", ["HallOfRecords", "StarObservatory", "SealOfHeaven"]),
}
# outer disciples who turn up anywhere on the mountain
ROVERS = {"sect": [NP.FAN, NP.TANG]}

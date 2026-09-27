# Runtime bug log

Real behavioural defects found in the runtime (godot/scripts, tests, player/game/title scenes, project
settings) and fixed on this branch. One line each: **symptom** -> cause -> fix (file:line of the fix).

1. [Locomotion] **Feet slide during walk and run** -> walk/run speed_scale divided by 1.45 / 4.2 m/s while the hero moves at 1.6 / 4.6 m/s (and the clips are authored at 1.6 / 4.6) -> speed_scale = ground speed / authored speed, unclamped (AUTHORED_SPEED table: walk 1.6, run 4.6, sprint 6.2 ...) (`godot/scripts/player.gd:570`)
2. [Locomotion] **Same foot sliding in the extended move set (crouch, block, sneak, sprint)** -> player_moves.update_animation hard-coded 1.45 / 4.2 / 0.8 / 1.0 divisors and clamps -> all gaits go through player.stride_scale() (`godot/scripts/world/player_moves.gd:836`)
3. [Locomotion] **Walk and run flicker back and forth when moving near 2.8 m/s (slopes, stopping)** -> a single threshold chose the clip every frame -> gait_for() with hysteresis (run above 3.1, back to walk below 2.5) (`godot/scripts/player.gd:558`)
4. [Locomotion] **Footstep sounds out of step with the feet** -> fixed 0.5 / 0.31 s footstep interval regardless of speed_scale -> footfalls on the clip's own phase (two per cycle), whatever the character's cycle length (`godot/scripts/player.gd:601`)
5. [Locomotion] **Abrupt 0-to-full-speed starts and stops (55 m/s^2)** -> acceleration was 12 * speed per second -> separate ground accel / brake / air rates on the planar velocity (`godot/scripts/player.gd:38`)
6. [Stairs] **The hero cannot walk up stairs, terrace lips or curbs without jumping** -> a capsule meets a vertical riser with a steep contact normal and move_and_slide stops dead -> Stepper.step_up(): test_move lift (<= 0.45 m), forward and set-down probe before move_and_slide (`godot/scripts/world/stepper.gd:25`)
7. [Stairs] **Walking/running down stairs the hero falls off every step and plays the fall animation** -> floor snap never engages over a step nose (capsule edge contact is not floor) -> Stepper.step_down() + 'supported' state while the nose is crossed with ground just below (`godot/scripts/player.gd:528`)
8. [Stairs] **Space pressed on a stair edge does a mid-air somersault instead of a jump** -> moves.handle_input treated not is_on_floor() (a capsule on a step nose) as airborne -> is_grounded() everywhere the move set asks 'standing?' (`godot/scripts/world/player_moves.gd:286`)
9. [Stairs] **The body pops up/down by a whole step when stepping** -> instant vertical correction of the collision body -> model and camera ease over the step (visual offset decays) (`godot/scripts/player.gd:545`)
10. [Stairs] **Dodge rolls and slides stop dead at the first step** -> _motion_state used plain move_and_slide() -> uses player.move_body() (step handling) (`godot/scripts/world/player_moves.gd:644`)
11. [Stairs] **Floor snapping too short for a 0.45 m step, speed changes on slopes** -> floor_snap_length 0.4, floor_constant_speed off -> snap 0.5, constant speed on (`godot/scenes/player.tscn:15`)
12. [Enemies] **Enemies cannot follow the player up stairs or onto terraces** -> no step handling for enemy CharacterBody3D -> Stepper.step_up/step_down in the enemy's physics (`godot/scripts/world/enemy.gd:298`)
13. [Enemies] **Humanoid enemies' feet slide (a 3.4 m/s bandit plays the 4.6 m/s run at 1.0)** -> enemy gait clips were never speed-scaled -> _animate_gait(): humanoids speed_scale = ground speed / (authored * model scale); creatures by chase speed (`godot/scripts/world/enemy.gd:312`)
14. [Enemies] **Enemy attacks and flinches play slowed down / sped up and hit out of sync** -> attack/hit animations inherited the last locomotion speed_scale -> speed_scale reset to 1 for attack and hit (`godot/scripts/world/enemy.gd:357`)
15. [Enemies] **A defeat objective can become unwinnable** -> an enemy chasing the player over a cliff fell forever below kill_y -> enemies below the map's kill_y return to their spawn point (`godot/scripts/world/enemy.gd:256`)
16. [Enemies] **Enemy 'home' was always the map origin** -> recorded in _ready(), before the spawner positions the enemy -> recorded on the first physics frame (and set by the runner) (`godot/scripts/world/enemy.gd:242`)
17. [Enemies] **Enemies on the terrace below hit the player standing above them (and vice versa)** -> strike checks ignored the height difference -> vertical reach limit of 2.5 m on both sides (`godot/scripts/world/enemy.gd:275`)
18. [Combat] **The player's palm strike hits enemies on another floor level** -> planar reach test only -> skip enemies more than 2.5 m above / below (`godot/scripts/player.gd:336`)
19. [Enemies] **After the player dies, enemies' health bars still show the old damage and they stay aggroed where they were** -> only hp was reset -> reset_after_player_death(): hp, aggro, strike, bar, back to spawn (`godot/scripts/world/enemy.gd:336`)
20. [Dialogue] **Skipping sometimes removes the text and plays other text / the same text again** -> two conversations (e.g. an NPC bark and an objective conversation started by the runner) ran two play() loops on the same box -> play() waits its turn (`while active: await finished`) (`godot/scripts/ui/dialogue_ui.gd:202`)
21. [Dialogue] **Quest conversations started while another conversation was open** -> runner._process fired reach/defeat/meditate/collect conversations without checking dialogue/cinematic state -> runner waits while dialogue or a cinematic is active (`godot/scripts/quest_runner.gd:496`)
22. [Dialogue] **Clicking the dialogue box did not advance it (only clicks elsewhere did)** -> input read in _unhandled_input; the PanelContainer (mouse_filter STOP) swallowed clicks on it -> advance input read in _input() (`godot/scripts/ui/dialogue_ui.gd:142`)
23. [Dialogue] **E / Space pressed in the first 200 ms of a conversation leaked to the game (interact, jump)** -> the _ignore_until window returned without consuming the event -> every advance press while active is consumed; a 90 ms debounce only guards double events (`godot/scripts/ui/dialogue_ui.gd:156`)
24. [Dialogue] **A doubled / bounced key event skipped two lines** -> no per-line guard -> DEBOUNCE_MSEC per line; _advance cleared when a line appears (`godot/scripts/ui/dialogue_ui.gd:158`)
25. [Input] **A Space consumed by the dialogue could still make the hero jump** -> jump polled Input.is_action_just_pressed() in _physics_process, which ignores set_input_as_handled() -> event-driven jump buffer from _unhandled_input (plus coyote time); buffer cleared whenever controls change hands (`godot/scripts/player.gd:260`)
26. [Dialogue] **A hurried E after a conversation immediately started another one (felt like the conversation regenerating)** -> nothing separated the end of one conversation from the next interact -> 400 ms interact cooldown after a conversation scene ends (`godot/scripts/game.gd:424`)
27. [Choices] **Skipping the last line with Space/Enter picked moral choice 1** -> the first choice button grabbed keyboard focus, and ui_accept pressed it -> no auto-focus; keys armed 350 ms after the choices appear (`godot/scripts/ui/dialogue_ui.gd:297`)
28. [Choices] **'arrows + E' (as documented) did not confirm a choice** -> only digits and GUI ui_accept were handled -> arrows / W / S move focus, E / Enter / Space confirm (`godot/scripts/ui/dialogue_ui.gd:162`)
29. [Choices] **Clicking the background during a choice hid and captured the cursor** -> player._unhandled_input captured the mouse on any unhandled click, even with controls disabled -> capture only while the player has control (`godot/scripts/player.gd:244`)
30. [Dialogue UI] **Dialogue box cut off at the bottom / wider than a 1024 px window** -> fixed 1040 px minimum width and a fixed bottom offset -> _fit() sizes to the visible rect, pins the bottom 14 px above the edge and re-fits on content / window changes (`godot/scripts/ui/dialogue_ui.gd:112`)
31. [Conversation] **The hero never played talk / listen gestures** -> converse() played them but _update_animation replaced them with idle on the next physics frame -> hold_pose(): locomotion leaves a held pose alone while standing (`godot/scripts/player.gd:209`)
32. [Conversation] **An NPC moved home after a conversation kept turning toward an old point** -> ensure_npc() repositioned but kept the NPC's face() target -> face target cleared when an NPC is (re)placed (`godot/scripts/game.gd:271`)
33. [Conversation] **Controls were handed back while something else still held them** -> converse()/cinematic set controls_enabled = true unconditionally -> release_controls() checks busy / cinematic / dialogue / open scenes / death (`godot/scripts/game.gd:326`)
34. [Quests] **A conversation interrupted by a map change could complete the next objective** -> coroutines awaited converse() then called complete() on whatever objective was current -> _epoch counter bumped by clear(); stale coroutines stop (`godot/scripts/quest_runner.gd:438`)
35. [Quests] **Enemy killed during the pre-fight conversation was never counted: the defeat objective could not finish** -> _on_enemy_died ignored deaths while state was 'busy' -> counted while busy, completed when the conversation ends (`godot/scripts/quest_runner.gd:391`)
36. [Quests] **Inside a building the tracker said 'Travel by teleport array' and pointed at an array that does not work indoors** -> travel state ignored interiors -> 'Leave the building' pointing at the ExitDoor (`godot/scripts/quest_runner.gd:97`)
37. [Quests] **Latent crash on a talk objective whose NPC has no home and no `at`** -> Story.npc(id).home.marker on null -> _talk_marker() falls back to the arrival point (`godot/scripts/quest_runner.gd:163`)
38. [Quests] **Several pickups stacked on one spot (collected all at once)** -> open_spot() returns the centre when it finds nothing -> later pickups fan out instead of stacking (`godot/scripts/quest_runner.gd:351`)
39. [Quests] **Big quest props could not be used (E prompt never appeared)** -> fixed 3 m interaction reach from the prop origin -> reach measured to the prop outline (2 m), from its AABB (`godot/scripts/world/prop.gd:70`)
40. [Audio] **After a chapter's victory fanfare the map music cut in over a boss fight** -> 12 s timer switched music unconditionally (and referenced the game after quitting) -> only if no fight / newer track took over, and the game still exists (`godot/scripts/quest_runner.gd:670`)
41. [Audio] **Music could go silent after two quick track changes (map load, fights)** -> the first cross-fade's final callback stopped the player the second call had just started -> running cross-fade killed and settled before the next (`godot/scripts/autoload/audio.gd:62`)
42. [Audio] **Music volume slider had no effect on the track already playing** -> volume only applied when a track started -> music_volume setter updates the active player (`godot/scripts/autoload/audio.gd:11`)
43. [Audio] **Voice volume slider ignored until the next line** -> same -> voice_volume setter (`godot/scripts/autoload/audio.gd:15`)
44. [Game] **Pressing E twice at a door / teleport started two map loads** -> travel_to/enter_door waited 0.3-0.5 s before load_map set busy -> busy set immediately (`godot/scripts/game.gd:182`)
45. [Game] **After arriving on a map the camera looked in some old direction** -> only the model was turned away from the teleport array -> camera yaw set behind the hero (`godot/scripts/game.gd:161`)
46. [Game] **Interiors showed up as teleport destinations after loading a save made indoors** -> load_map(track_visited=true) added interiors to Game.visited -> interiors never tracked; travel menu filters them (`godot/scripts/game.gd:147`)
47. [Game] **E talked to the first NPC in the list, not the nearest** -> _near_npc returned the first within 2.4 m -> nearest NPC (`godot/scripts/game.gd:407`)
48. [Game] **E used the first door in range, not the nearest** -> same in _near_door -> nearest door (`godot/scripts/game.gd:392`)
49. [Game] **Respawn after death could run on a freed / changed map** -> _on_player_died awaited 3 s and then used `map` unguarded -> abort if the map changed, the game left the tree or the player is no longer dead (`godot/scripts/game.gd:455`)
50. [Game] **Falling off the world refilled health and qi (and played the revive)** -> kill_y used player.respawn() -> place_at(spawn_point) only (`godot/scripts/game.gd:364`)
51. [Game] **A dead hero could open conversations, swap character (standing up while dead) or interact** -> _unhandled_input only checked controls_enabled -> input ignored while dead; set_character keeps the death pose (`godot/scripts/player.gd:255`)
52. [Game] **Journal (J) could open over the travel menu; closing it unpaused the game with the menu still up** -> game._unhandled_input ignored travel.open -> no journal while travel / journal is open (`godot/scripts/game.gd:87`)
53. [Game] **NPCs placed at the world origin when their home marker is missing on the (regenerated) map** -> ensure_npc on a missing marker -> skip NPCs whose marker is missing (`godot/scripts/game.gd:231`)
54. [Input] **One mouse-wheel notch zoomed twice** -> wheel press and release both handled -> only the press (`godot/scripts/player.gd:246`)
55. [Input] **After closing the journal or travel menu the cursor stayed visible and the camera stopped following the mouse** -> mouse mode never restored -> previous mouse mode restored on close (`godot/scripts/ui/journal.gd:109`)
56. [Menus] **Travel menu offered interior maps** -> Game.visited listed as-is -> interiors filtered (`godot/scripts/ui/travel_menu.gd:46`)
57. [Cinematics] **Player's cinematic pose replaced by idle one frame later** -> locomotion overrode anim.play() -> hold_pose() for the actor pose, released at the end (`godot/scripts/ui/cinematic.gd:130`)
58. [Cinematics] **Keys and clicks during a cinematic leaked to the game (buffered jumps, mouse capture)** -> skip read in _unhandled_input, other input not consumed -> _input() consumes all keys/clicks while active (`godot/scripts/ui/cinematic.gd:83`)
59. [Cinematics] **A skipped title card could stay visible into the next cinematic** -> the fade-in tween kept running against the fade-out -> tweens killed on skip and at the end (`godot/scripts/ui/cinematic.gd:214`)
60. [Cinematics] **A cinematic's music kept playing afterwards** -> never switched back -> map music restored (`godot/scripts/ui/cinematic.gd:180`)
61. [Cinematics] **Actors / shots whose marker the map lacks were staged at the world origin** -> marker_position() returns ZERO for missing markers -> skipped (`godot/scripts/ui/cinematic.gd:121`)
62. [Cinematics] **Cinematic enemies floated or sank beside their marker** -> offset positions not grounded (physics disabled) -> ground_at() (`godot/scripts/ui/cinematic.gd:150`)
63. [Rendering] **Floors shimmer / flip between surfaces (z-fighting)** -> Camera3D near 0.08 / far 3000 (37 500:1) wastes depth precision -> near 0.15 / far 1500 on the player camera (and 0.1-0.15 / 1500 on cinematic, conversation, title cameras) (`godot/scenes/player.tscn:36`)
64. [Rendering] **Terrain and building floors pop / swap surfaces at distance** -> meshes/generate_lods=true made simplified LOD meshes of terrain, floors and buildings -> LODs disabled for 80 environment GLBs (vegetation keeps them) and by default for new scenes (`godot/project.godot:28`)
65. [Rendering] **Camera clipped through wall edges** -> SpringArm3D used a ray, not a shape -> 0.2 m sphere shape (`godot/scenes/player.tscn:9`)
66. [Rendering] **Objective ring flickered on uneven ground** -> ring lay 6 cm above the ground (z-fighting, dipping under slopes) -> lifted to 14 cm (`godot/scripts/world/beacon.gd:52`)
67. [Rendering] **Tribulation strike rings half-buried / flickering** -> same 6 cm offset -> 14 cm (`godot/scripts/world/tribulation.gd:226`)
68. [Pickups] **Pickup burst colour did not match the pickup** -> COLORS default used in take() -> the pickup's own colour (`godot/scripts/world/pickup.gd:111`)
69. [Props] **Quest props modelled centred or floating stood half-sunk / hovering; the player walked through large props** -> no grounding, no collision -> base aligned to the marker, cylinder body on the NPC layer (`godot/scripts/world/prop.gd:36`)
70. [Loading] **Loading screen vanished during a second quick load** -> the previous close() fade's callback hid the screen after open() -> fade tween killed on open() (`godot/scripts/ui/loading_screen.gd:71`)
71. [Title] **Title screen heroes floated / sank at the cliff edge** -> fixed height offset -> ground_at() (`godot/scripts/title.gd:36`)
72. [Title] **Returning to the title could leave a captured, invisible cursor or a paused tree** -> no reset on entering the title -> mouse visible, tree unpaused (`godot/scripts/title.gd:17`)
73. [NPCs] **The game crashed when a story NPC's model GLB was missing (a new NPC before its model is built)** -> load(path).instantiate() on null -> falls back to a disciple model with a warning (`godot/scripts/world/npc.gd:31`)
74. [Enemies] **Same crash for an enemy whose model is missing** -> unguarded load() -> falls back to the bandit model (`godot/scripts/world/enemy.gd:130`)
75. [Audio] **Quitting to the title while meditating left the meditation hum looping forever** -> the looping sound lives in the Audio autoload's pool and nothing stopped it when the player was freed -> stopped in the player's _exit_tree() (`godot/scripts/player.gd:122`)
76. [Combat] **A qi blast or technique cast just before opening the journal went off while the game was paused (AoE damage behind the menu)** -> SceneTreeTimer created with process_always = true -> game-time timers (process_always = false) (`godot/scripts/world/player_moves.gd:490`)
77. [Moves] **After a teleport (map load, falling off the world, a cinematic) the hero could stay hanging from a ledge, charging or blocking** -> move-set state (ledge / climb / dodge / charge with a 99 s action lock) survived place changes -> moves.reset_state() on every teleport (`godot/scripts/world/player_moves.gd:164`)

## Requested changes (not counted above)

- Dialogue text appears instantly (no typewriter); voiced lines move on 1.2 s after the voice, text-only lines after
  `Story.reading_time()`; one press = one line (`godot/scripts/ui/dialogue_ui.gd`).
- Group conversations: an objective's `with` NPCs (or, without `with`, the NPCs who speak in its lines and choice
  replies) stand in a circle with the talk target (talk) or around the marker (reach / meditate / interact / collect;
  a few metres back toward the player for defeat and tribulation), facing the middle; they leave when the objective
  ends unless the map is their home (`godot/scripts/quest_runner.gd`, `party_ids`, `_place_party`, `_dismiss_party`).
- Conversation camera: over-the-shoulder shot of the listener on the speaker, cut on every line, one side of the
  pair's axis (180 degree rule), pulled in front of walls; the speaker gestures and turns to whom they address, the
  others turn to the speaker; name plates hidden during the scene; the portrait moves to the right for the hero
  (`godot/scripts/world/conversation.gd`).
- Pickups load `res://assets/items/<item_id>.glb` when present (falls back to the old environment model, then to
  the glowing primitive), scaled to ~0.42 m and hovering (`godot/scripts/world/pickup.gd`).
- Slight lean into turns while running (max 4 degrees) (`godot/scripts/player.gd`).

## For the world workstream

Runtime causes of the "floor flipping between two textures" are fixed here (depth precision, LOD swaps, beacon
rings). Two causes live in files owned by the world workstream:

1. **Shadow cascades / acne.** `tools/maps/common.py` writes the Sun with default biases and hard cascade
   boundaries; on large flat floors the shadow texel density changes at each split and self-shadowing acne crawls
   as the camera moves, which reads as the floor switching texture. Proposed change in the Sun block of
   `tools/maps/common.py` (after `'shadow_blur = 1.5',`):

   ```python
   'shadow_bias = 0.04',
   'shadow_normal_bias = 1.6',
   'directional_shadow_blend_splits = true',
   'directional_shadow_fade_start = 0.85',
   'directional_shadow_pancake_size = 30',
   ```

   and, for the ~3.2x larger maps, keep `shadow_distance` at 120-180 m (the 4096 atlas is shared by four splits;
   more distance means coarser, crawling shadows on nearby floors).
2. **Coplanar geometry inside GLBs** (plaza / path / courtyard planes laid exactly on the terrain, floor tiles on
   platform tops): lift overlay floors 2-3 cm above what they cover or cut the terrain under them; the renderer
   cannot resolve two surfaces at the same depth, whatever the camera settings.

Import settings: `meshes/generate_lods` is now `false` in the `.import` of every environment GLB except vegetation
and rubble, and `project.godot` `[importer_defaults]` makes new scene imports default to no LODs. New building or
terrain GLBs therefore need no action; if a new vegetation GLB wants LODs, set `generate_lods=true` in its `.import`.

## For the HUD workstream (`godot/scripts/ui/hud.gd` is theirs now; not edited here)

- `quest_card()` and `title_card()` start a new fade tween without killing the previous one; two cards within ~7 s
  (first load + a quest completing, a volume ending) fight and the second card fades out early.
- `toast()` calls `free()` on the oldest toast while its tween is still running; the tween's `queue_free` callback
  then targets a freed instance. Prefer `queue_free()` + removing it from the container.

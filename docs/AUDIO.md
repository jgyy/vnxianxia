# Audio

All music and sound effects are synthesised from scratch by one deterministic script, with no
samples or downloads:

```sh
python tools/gen_audio.py                      # everything (about 3 min on 4 cores)
python tools/gen_audio.py --only title,thunder # selected cues
python tools/gen_audio.py --out /tmp/audio --verbose --jobs 4
```

Requires `numpy`, `scipy` and `soundfile` (libsndfile with Vorbis). Output goes to
`godot/audio/music/<id>.ogg` (stereo, 44.1 kHz, Vorbis q≈0.34) and `godot/audio/sfx/<id>.ogg`
(mono, 44.1 kHz, q≈0.75). The script ends with a verification table (duration, peak, RMS, LUFS,
size and a click test at the loop seam) and exits non-zero if anything fails. Current totals are
about 10.7 MB of music and 0.8 MB of effects.

**Looping.** Every music track except `victory`, plus `meditate_loop`, `wind_loop` and
`fire_loop`, loops seamlessly. The mix is built on a *cyclic* timeline exactly one loop long. Notes,
echoes and the convolution reverb that run past the end wrap onto the beginning, so the file's end
flows into its start. The game must still enable looping on the stream
(`AudioStreamOggVorbis.loop = true`, or *Loop* in the import dock).

## How it is made

| Part | Technique |
|---|---|
| Guzheng / guqin / pipa | Modal (additive) strings: stiff-string inharmonic partials, pluck-position comb, per-partial decay, pick noise, body-resonance EQ. Press-bends (`^`), releases (`v`), slide-ins (`s`, guqin *zou-yin* with finger squeak), rou-xian vibrato (`~`), fanyin harmonics (`h`), pipa lun-zhi tremolo (`t`), pentatonic glissandi. |
| Dizi / xiao | Continuous phrase synthesis: portamento pitch curve, delayed-onset vibrato, grace notes, tongued articulation dips. The dizi adds bright harmonics, *dimo* membrane buzz and chiff; the xiao is soft and breathy (band-passed breath noise). |
| Erhu / gehu | PolyBLEP band-limited sawtooth with bow jitter through erhu body formants (≈0.5/1.05/2.4 kHz), bow noise, wide expressive vibrato, slides, scoops and fall-offs. The gehu is its dark, low bowed-bass variant. |
| Choir | Three to five detuned saws through vowel formant filters (`ah`, `oo`), with voice-led chord lines; short "HA" stabs for the boss track. |
| Pads / drones | Detuned saws or sine-organ tones with slow envelopes; periodic filtered noise for wind and rumble. |
| Percussion | Taiko (pitch-swept membrane modes, skin slap, stick click, soft saturation), tanggu and bangu small drums, woodblock and muyu, cymbals (band-decaying noise plus inharmonic ring), tam-tam and opera gongs (dense inharmonic partials with slow high-partial bloom and falling or rising pitch), temple bell, bianzhong and small chimes (inharmonic partial doublets that beat). |
| Space & master | Synthetic stereo convolution reverb (band-wise decaying noise IR with early reflections), frequency-domain ping-pong echo, 28 Hz high-pass, BS.1770-style loudness normalisation (−13.5 to −18 LUFS depending on mood) and a look-ahead limiter at −1.2 dBFS. |

Melodies are written in **jianpu** (numbered notation) on pentatonic modes, for example
`3/1.5 5/0.5 6 1' | 6/1.5 5/0.5 3/2~`. The parser checks that every bar adds up.

## Music

| id | Length | Description |
|---|---|---|
| `title` | 80 s loop, 72 bpm | Majestic main theme in D *gong* mode. It opens with a guzheng glissando and a temple bell over open-fifth pads. The dizi states an 8-bar theme; guzheng and dizi then trade call and response over a choir and building taiko, reach a climax in octaves, and close with a falling glissando, gong and chimes. |
| `sect` | 80 s loop, 60 bpm | A serene mountain sect in F *zhi* mode. Guqin harmonics frame a slow xiao melody, while low guqin notes slide beneath. A guqin solo answers before the harmonics return. Birdsong, a distant sect bell and a faint breeze complete the scene. |
| `forest` | 77 s loop, 56 bpm | A mysterious bamboo forest in B *yu* mode. Sparse, echoing xiao phrases sit over a dark drone and wind. Short guzheng motifs (some in harmonics) and random hollow bamboo knocks drift through the dotted-eighth echo. |
| `town` | 86 s loop, 112 bpm | A lively market in G *gong* mode, built as a folk-dance tune. Pipa states it, then erhu; the two trade call and response, then play it together with a dizi. Woodblock, tanggu, bangu, small cymbals and rising *xiaoluo* gongs drive it along. |
| `abyss` | 88 s loop, 60 bpm | A dark demonic abyss centred on C#. Low drones with semitone and tritone rubs, a heartbeat that races in the middle section, distant muffled taiko, and a dissonant, sliding erhu against a low gehu. Deep "oo" choir swells, falling gongs and far thunder add to the dread. |
| `sky` | 80 s loop, 66 bpm | Ethereal celestial isles in E *gong* mode. Voice-led choir chords, a constant shimmer of echoing chimes, bianzhong arpeggios, zheng harmonics and a slow, high dizi line. |
| `battle` | 82 s loop, 140 bpm | Combat in D *yu* mode. A taiko 3-3-2 ostinato drives a 16th-note pipa riff and gehu pulse. An erhu melody leads into a pipa-run and erhu call and response. A half-time breakdown brings gongs, choir and a climbing erhu, then the full reprise with dizi and a drum fill back to the top. |
| `boss` | 78 s loop, 148 bpm | Boss fight in G minor pentatonic with a b2 (Ab). A gehu ostinato, heavy double taiko, choir "HA" stabs, gongs and crashes carry an angry erhu theme and a dissonant pipa tremolo. A heartbeat breakdown with a choir cluster and riser leads to the climax with dizi. |
| `tribulation` | 88 s loop, 120 bpm | The heavenly-tribulation finale. Thunder strikes open it, then a taiko ensemble, a C *yu* erhu theme and choir chords rising step by step. A dizi and erhu duet builds to a crescendo drum roll with the choir climbing an octave. It resolves into a triumphant Eb *gong*-mode phrase with gong and bells, and the storm returns on the loop. |
| `victory` | 12.8 s, no loop | Triumphant jingle: taiko, gong, dizi and erhu fanfare, rising zheng glissandi, a bell arpeggio and a ringing final chord. |
| `sorrow` | 89 s loop, 54 bpm | A slow, melancholic erhu solo in E *yu* mode with slides and deep vibrato, over soft guzheng arpeggios and a pad, closing with a quiet xiao echo. |

## Sound effects (mono)

| id | Description |
|---|---|
| `sword_swing` | Band-pass noise sweep with a faint blade whistle. |
| `sword_hit` | Metallic clang (inharmonic partials), spark transient and a low thump. |
| `hit_flesh` | Dull body thump with a short slap. |
| `hit_stone` | Low thud with gritty crunch grains and dust. |
| `qi_charge` | Rising detuned tone with accelerating tremolo, a swirling noise sweep and sparkles (1.6 s). |
| `qi_blast` | Short charged whoosh, then a boom, a burst with a falling filter, and sparkles. |
| `player_hurt` | Thump with a short, pained descending nasal tone. |
| `enemy_death` | Boom, descending dark chord and qi dispersing into sparkles. |
| `block` | Short metallic parry ring with a wooden knock. |
| `footstep_stone`, `footstep_grass` | Click and thump on stone; rustling bursts on grass. |
| `jump`, `land` | Upward cloth whoosh; thud with dust. |
| `pickup` | Three quick ascending chimes with shimmer. |
| `quest_accept` | Soft, slightly rising small gong. |
| `quest_complete` | Bright bianzhong arpeggio (1 3 5 1' 3'). |
| `objective_update` | Two small chimes. |
| `breakthrough` | 2.3 s rising shimmer (pad, noise sweep, cascading chimes), then gong, bell, cymbal and drum (3.8 s). |
| `ui_click`, `ui_hover`, `ui_open`, `ui_close` | Wood tick; soft sine blip; up-swish with chime; down-swish with tick. |
| `dialogue_next`, `typewriter` | Soft muyu wood tick; very short soft tick. |
| `teleport` | Flanged rising-then-falling noise sweep with a chime cascade (2 s). |
| `meditate_loop` | 6 s loop: a G drone with a fifth, a singing-bowl beat and inhale/exhale breath noise. |
| `wolf_howl`, `wolf_growl`, `wolf_attack` | Formant-shaped howl contour; rough jittery growl; snarl, bark and teeth snap. |
| `serpent_roar` | Hiss with a low rough roar. |
| `golem_rumble`, `golem_step` | Sub rumble with stone grinding and crackles; very low thud with debris. |
| `demon_laugh_ish` | Dark low cluster swelling open with rhythmic "ha" pulses and a reversed cymbal (no voice). |
| `thunder` | Lightning cracks followed by a rolling rumble (4 s). |
| `wind_loop`, `fire_loop` | 8 s gusting wind with a whistle; 4 s campfire roar, hiss and crackles (both loop). |
| `chest_open` | Latch click, creaking hinge (stick-slip), lid thunk and a sparkle. |
| `bell_toll` | Large temple bell (98 Hz strike, 49 Hz hum). |
| `drum_hit`, `heartbeat` | Single war taiko; lub-dub. |
| `chapter_title` | Big taiko, falling gong and cymbal (3 s). |
| `gameover` | Low gong with a slow descending bowed tone. |

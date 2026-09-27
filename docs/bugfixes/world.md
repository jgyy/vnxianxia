# World workstream: defects found and fixed

One line each: symptom -> cause -> fix (file:line). Line numbers are at commit time.

1. Floors in all five maps flickered between two textures as the camera moved -> paths, plazas and fields were flat overlay meshes laid a few mm above the terrain (coplanar with the ground at distance) -> terrain is now one heightfield whose triangles are split exactly on each region outline and textured per region, so there are no overlays (blender/xianxia/lands.py:2862).
2. White cracks along region seams after the split terrain landed -> split polygons reused vertices by id, which left T-junctions and duplicates -> dedupe by (x, z) mm, drop degenerate polygons, snap near-endpoint splits (blender/xianxia/lands.py:2695, blender/xianxia/lands.py:2818).
3. Terrain GLBs were 12 MB / 398k faces -> refinement split every triangle near an outline, including hidden ones under building floors -> refine only thin positive gaps with min_len 1.1 and skip faces below G.floor (blender/xianxia/lands.py:2716).
4. Shadow acne crawled over large floors and the shadow split seams popped across the ground -> the Sun used default bias and unblended PSSM splits -> shadow_bias 0.06, normal bias 1.6, directional_shadow_blend_splits (tools/maps/common.py:170).
5. Blender crashed building convex colliders ("duplicate vertex") -> lands.convex_mesh fed coincident points to convex_hull -> remove_doubles before the hull (blender/xianxia/lands.py:124).
6. Player could not walk up hall podium stairs without jumping -> each stair collider was the stepped visual mesh (risers the capsule cannot climb) -> 0.17 m risers with a smooth stair_ramp collider through the tread nosings (blender/xianxia/buildings.py:158).
7. Podium top step flickered against the terrace cap lip -> the flight's top tread and the cap were coplanar at the edge -> flight starts 11 cm in front of the edge (blender/xianxia/buildings.py:203).
8. Pavilion's three small steps could not be climbed -> its 0.5 m base was a box collider -> hexagonal frustum collider sloping to the ground (blender/xianxia/arch.py:262, blender/xianxia/arch.py:506).
9. Pagoda entrance could not be entered -> one 0.4 m step up a 0.8 m base with a box collider -> four 0.2 m steps and a PagodaRamp collider (blender/xianxia/arch.py:518, blender/xianxia/arch.py:570).
10. Formation array plinth blocked the player -> its 0.3 m + 0.16 m steps were one 0.46 m box collider -> 24-sided frustum collider (blender/xianxia/props.py:245).
11. Blood altar could not be approached -> two 0.48 m tier box colliders -> single walkable frustum collider (blender/xianxia/realms.py:699).
12. Player walked through the main-hall throne dais and the meditation mat -> they had no collider at all -> DaisCol + DaisRamp and MatCol + MatRamp (blender/xianxia/interiors.py:212, blender/xianxia/interiors.py:232).
13. Mirror pool and blood moon shrine rims stopped the player dead -> the cone colliders were too steep (risers > 0.3 m) -> wider cone bottoms (blender/xianxia/buildings_sky.py:496, blender/xianxia/buildings_abyss.py:454).
14. Formation disc shimmered on its plinth -> disc only 5 mm above the plinth top -> disc raised to 0.49 (blender/xianxia/props.py:212).
15. Platform stairs z-fought the platform base side -> base and stair block shared their top plane and face -> base 0.15 lower, stairs moved 10 cm out (blender/xianxia/arch.py:188, blender/xianxia/arch.py:200).
16. Hall plaques flickered -> board face sat 1 cm in front of the lintel -> face 7.5 cm proud (blender/xianxia/arch.py:280).
17. Pagoda window panels flickered on every tier -> panels coplanar with the wall face -> 12 cm inset reveal (blender/xianxia/arch.py:539).
18. Sky isle stair landings flickered with the isle tops -> landing slabs flush with the island surface -> landings 21 cm lower with matching colliders (blender/xianxia/realms.py:1742).
19. Ascension stair and sky steps showed gold striping noise on every riser -> gold nosing front only 1 cm ahead of the slab -> nosing 2.5 cm proud and 8 cm wider (blender/xianxia/realms.py:1722).
20. Jade bridge ends z-fought the isles and their gold edging flickered -> deck ends flush with the isle top, gold edge flush with the fascia -> deck +4 cm, gold edge 6 cm wider (blender/xianxia/realms.py:1586, blender/xianxia/realms.py:1600).
21. Belvedere platform and its inlay flickered -> top and inlay coplanar with the deck -> top +2 cm, inlay +7.5 cm (blender/xianxia/realms.py:1642).
22. Taiji, star and ruins isle discs shimmered -> discs 8 mm above the isle top -> +3 cm (blender/xianxia/realms.py:1779, blender/xianxia/realms.py:1856, blender/xianxia/realms.py:2004).
23. Demon gate passage walls flickered where the plinth met the gate block -> plinth inner end exactly on the passage wall plane -> plinth starts 3 cm inside the stone (blender/xianxia/realms.py:967).
24. Demon gate trim and fortress wall plinth ends flickered -> trim flush with the tower face, plinth ends flush with the wall ends -> trim +-12 cm, plinth 12 cm longer (blender/xianxia/realms.py:987, blender/xianxia/realms.py:1064).
25. Chain bridge, rainbow bridge, cloud pier and stepping stones flickered where they met isle tops -> decks exactly at isle top height -> +4 cm (blender/xianxia/buildings_sky.py:29, blender/xianxia/buildings_sky.py:84, blender/xianxia/buildings_sky.py:109, blender/xianxia/buildings_sky.py:387).
26. Town gate pier tops and town house posts/frames flickered -> pier caps and post faces coplanar with the timber and walls -> piers 0.62 m lower, posts 0.3, frames 0.32 deep, door jambs 2 cm into the opening (blender/xianxia/lands.py:1886, blender/xianxia/lands.py:2170).
27. Inn plaque and the corner sign were invisible or flickering -> plaque 1 cm behind its frame front; the vertical board sat inside its 8 cm frame -> both moved in front of the frame (blender/xianxia/lands.py:2004, blender/xianxia/lands.py:2007).
28. Stilt house frames and lake pavilion walkway flickered -> frame and walkway coplanar with deck/stilts -> frame 0.2 thick, walkway 3 cm lower (blender/xianxia/buildings_wild.py:75, blender/xianxia/buildings_wild.py:165).
29. Interior sparring ring, rune floor and rugs flickered against the floor -> 5 mm thick, coplanar at distance -> 3 cm (blender/xianxia/interiors.py:170, blender/xianxia/interiors.py:298).
30. Interior ceiling beams showed flickering squares on the outer walls -> beam ends coincided with the wall's outer face -> beams 6 cm shorter (blender/xianxia/interiors.py:59).
31. Pine root caps flickered with the ground -> trunk bottom exactly at z 0 -> trunk starts 0.35 m underground (blender/xianxia/nature.py:60).
32. Town canal embankment coping flickered with the street -> coping top 3 cm above the ground -> 12 cm curb, with gaps at the docks (blender/xianxia/lands.py:2489).
33. Sect courtyard walls z-fought where segments overlapped -> each run used whole 8 m segments that overlapped at the ends -> segments scaled to length/n/8 (tools/maps/sect.py:263).
34. Sect lotus pads shimmered on the pond -> pads 1 cm above the water -> placed at -0.41 against the lowered water (tools/maps/sect.py:248).
35. Scholar rock stood inside a lantern -> both placed at the same spot -> rock moved to (-14.5, -16.5) (tools/maps/sect.py:325).
36. Switchback lanterns ran past the end of the path and floated over the chasm -> loop used the old fixed path length -> loop to SWITCHBACK.length (tools/maps/sect.py:418).
37. Sect vista was a white wall of fog after the map grew -> fog density tuned for a 120 m plateau -> 0.0007 with the fog height below the terraces (tools/maps/sect.py:585).
38. MoonGate and TeaHouse NPCs spawned inside the buildings -> markers lay inside the new footprints -> moved to open ground in front (tools/maps/sect.py:504, tools/maps/qingshi_town.py:423).
39. The shadow market stood in the blood river: marker in the water, two stalls on the far bank, a banner in the channel -> market placed on the river centre line -> market, carve and stalls moved east onto dry floor (tools/maps/blood_abyss.py:102, tools/maps/blood_abyss.py:313, tools/maps/blood_abyss.py:552).
40. Forest vegetation grew on paths and camps -> the path-distance lookup gave up too close to the path, so far points read as clear -> _path_distance searches 8 m (tools/maps/bamboo_forest.py:120).
41. Forest pool lotus sank under the water -> placed at pool level -> +5 cm (tools/maps/bamboo_forest.py:326).
42. Abyss build crashed with ZeroDivisionError -> a carve with two identical points had a zero-length segment -> single-point carves are discs; carve bbox rejection added (tools/maps/blood_abyss.py:198, tools/maps/blood_abyss.py:208).
43. Two sky isles intersected (StairFoot / WindTempleIsle) -> the link direction put them on top of each other -> direction (-0.5, -1) and an overlap assertion (tools/maps/sky_isles.py:322, tools/maps/sky_isles.py:335).
44. Wrong ground was used for the sect -> catalog "terrain" still pointed to the old nature.terrain -> lands.ASSETS overrides it with sect_terrain (blender/xianxia/lands.py:2933).
45. Skull tower took 86 s and 44k faces, chain bridges 41k faces -> full-detail skulls and modelled chain links -> low-poly skulls and tube chains (blender/xianxia/buildings_abyss.py:37, blender/xianxia/buildings_abyss.py:93).
46. Walkthrough q1886 failed: the celestial sentinel at RainbowBridge could not be reached and the player fell off -> the marker stood mid-span on a 4 m wide arch, so enemies spawned at the rail and the free spot beside them was open sky -> marker moved onto the lantern-isle bridgehead and taken off the checker's exempt list (tools/maps/sky_isles.py:430).

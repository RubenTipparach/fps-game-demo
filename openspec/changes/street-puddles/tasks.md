# Tasks

The owner asked on 2026-09-29. Survey answers, 2026-09-29: L1 and L2 "recommended"; L3 "ripples
would be awesome, this should just be a shader effect, simple cheap" (design, Context).

## 1. Before

- [x] 1.1 Measure how today's puddles are made and where they fall (design sections 1 and 2):
  the texture masks, the tile repeats, the share under a roof, the kerb and drip-edge lengths.
- [x] 1.2 The mockup: one 48 x 30 m stretch, today's texture puddles and the rules' sketch
  (`tools/design/mockup_puddles.py`, the design page's F20).
- [ ] 1.3 Before stills from the four capture places, and the canal view (design section 3.8).

## 2. Textures and shaders

- [ ] 2.1 `generate_city_materials.py`: the puddle terms out of `asphalt` and `paving_wet`; the
  gully grate's decal maps; a test that the committed ground ORM maps hold no standing water.
- [ ] 2.2 `rain_ripples.gdshaderinc` from `water.gdshader`'s `ripples()`; the canal includes it; the
  canal capture is unchanged.
- [ ] 2.3 `city_ground.gdshader`: today's material, then the puddle term; `postprocess.py` writes
  the ground materials from `materials.json` (`"ripples_from": "water"`); the equivalence capture
  with no mask set.
- [ ] 2.4 The `tools/godot` test: one ripple function, one set of numbers.

## 3. The plan

- [ ] 3.1 `City.puddles()`: gutter, gully and drip rules, the exclusions, a stream of its own.
- [ ] 3.2 `check_puddles`, and `test_city_plan.py`: the hub passes; a puddle under the Skyway
  and one on a kerb are refused, named.
- [ ] 3.3 The mask writer (`hub_puddles.png`: distance and height), and its test against the
  plan.
- [ ] 3.4 The level data's puddles and mask rect; `ENT_gully` entities; the design map draws the
  puddles.

## 4. The game

- [ ] 4.1 The `puddle_mask` and `puddle_rect_m` globals in `project.godot`; the level sets them on
  load.
- [ ] 4.2 The gully decal scene (`gen_undercity_scenes.py`) and the importer's mapping.
- [ ] 4.3 `placement_test.tscn`: every puddle in the rain by the core's `Wetness.Sheltered`.
- [ ] 4.4 Rebuild the sectors and bake the lightmaps.

## 5. Records

- [ ] 5.1 After stills from the before places; the rain video; the heaviest view's clustered
  elements; whether screen-space reflections show the neon in a puddle.
- [ ] 5.2 A validation record; the design page's F20; archive.

# Tasks

The owner asked on 2026-09-29. Survey L1 to L3 are open; planning goes on with the
recommendations marked provisional.

## 1. Before

- [x] 1.1 Measure how today's puddles are made and where they fall (design sections 1 and 2):
  the texture masks, the tile repeats, the share under a roof, the kerb and drip-edge lengths.
- [x] 1.2 The mockup: one 48 x 30 m stretch, today's texture puddles and the rules' sketch
  (`tools/design/mockup_puddles.py`, the design page's F20).
- [ ] 1.3 Before stills from the four capture places (design section 3.7).

## 2. Textures

- [ ] 2.1 `generate_city_materials.py`: the puddle terms out of `asphalt` and `paving_wet`; the
  six puddle shapes and the gully grate as decal maps; a test that the committed ground ORM maps
  hold no standing water.

## 3. The plan

- [ ] 3.1 `City.puddles()`: gutter, gully and drip rules, the exclusions, a stream of its own.
- [ ] 3.2 `check_puddles`, and `test_city_plan.py`: the hub passes; a puddle under the Skyway
  and one on a kerb are refused, named.
- [ ] 3.3 `ENT_puddle` and `ENT_gully` entities; the design map draws them.

## 4. The game

- [ ] 4.1 The decal scenes (`gen_undercity_scenes.py`) and the importer's mapping.
- [ ] 4.2 `placement_test.tscn`: every puddle decal in the rain by the core's `Wetness.Sheltered`.
- [ ] 4.3 Rebuild the sectors and bake the lightmaps.

## 5. Records

- [ ] 5.1 After stills from the before places; the heaviest view's clustered elements; whether
  SSR sees the puddles.
- [ ] 5.2 A validation record; the design page's F20; archive.

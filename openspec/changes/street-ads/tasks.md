# Tasks

The owner asked on 2026-09-29 and answered survey M4 to M7 the same day: every kind of sign,
food, casino, shops and lingerie, Hong Kong at night; dense on the market streets; one in eight
pointing to the hub; some animated.

## 1. Before

- [x] 1.1 Count today's signs, frontage and roofs per sector, and the lights (design section 1).
- [x] 1.2 The Hong Kong reference, cited (design section 2).
- [ ] 1.3 Before stills from the five places (design section 9).

## 2. Content

- [ ] 2.1 `ads.json` with its schema and test: density, kind mix, story share, animation, icons,
  about 60 brands (today's `BLADE_WORDS` among them).
- [ ] 2.2 `fonts.json`: the three OFL fonts pinned and fetched; `--verify` checks them.
- [ ] 2.3 `build_ad_atlas.py`: the atlas and its layout JSON; a page of the faces for the owner.

## 3. The plan

- [ ] 3.1 `City.sign()` with the seven kinds; `put_sign` and the blade branch become its `name`
  and `blade` kinds. Every other prim in the hub must be unchanged (compare before and after).
- [ ] 3.2 Sign spots per kind and district, a stream of their own; `check_signs`;
  `test_city_plan.py` refusals.
- [ ] 3.3 The design map draws the signs.

## 4. Build and game

- [ ] 4.1 `build_undercity.py`: fonts on `text`, the `tube` primitive, the atlas UVs.
- [ ] 4.2 `sign.gdshader` and its materials; the import presets.
- [ ] 4.3 One sector first (Lantern Row), captured for the owner before the rest; then rebuild and
  bake every sector; `placement_test.tscn`.

## 5. Records

- [ ] 5.1 After stills and the night video; triangle and light counts; the bake time against the
  last.
- [ ] 5.2 A validation record; the design page's F22; move the requirement into
  `openspec/specs/street-signs`; archive.

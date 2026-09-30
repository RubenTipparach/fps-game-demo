# Tasks

The owner reported on 2026-09-30: the cars are dark, their wheels don't meet the ground, and there's
no shadow under them; and directed that cars be static meshes for the light baking. Survey O2 to O4
were left blank on 2026-09-30, the recommendations accepted: on the road beside the kerb, bake first
with the contact shadow only if the shadow measures faint, and the proposed paints. Which models
the hub uses is open again (O1, survey O5; openspec/changes/cc0-vehicles).

## 1. Before

- [x] 1.1 Measure: the ground under every car's wheels, the lightmaps' users, the lights reaching
  each car against its bake, the paints' albedo (design sections 1.1, 2.1, 3.1).
- [x] 1.2 Before stills (`docs/playtest/scripts/vehicle_fixes_before.json`): five, in
  `docs/screenshots/vehicle_fixes/`.

## 2. The wheels

- [x] 2.1 `check_vehicles`: one ground over a 5 x 3 grid across the footprint; the test that refuses a
  spot across the kerb.
- [x] 2.2 The six spots in `layouts/hub.py` onto the road, 0.2 m from the kerb (survey O2); Quay Road's
  five off the quay's edge; the MerSec beat off the cars (design section 1.3).

## 3. Static meshes (owner, 2026-09-30)

- [x] 3.1 The plan: each car's model in the sector that owns its ground (the streets; the kiln for
  the garage's bay): `Plan.model`, and its test.
- [x] 3.2 `build_undercity.py`: the car's committed glb imported into that sector's glb at its spot
  and heading, `car_<id>`, its own UVs, its `-colonly` boxes, `lightmap_texel_scale` 4.
- [x] 3.3 `blender_level_import.gd`: the `car` kind a marker; the placement test finds each car's
  static mesh in its ground's sector and in that sector's lightmap (it passes after the bake, 5.1).

## 4. The paint

- [x] 4.1 `vehicle_data.py`: the 0.03-0.8 range on each texture's mean albedo, and a test (design 3.2,
  built).
- [x] 4.2 ~~The builder divides out the texture's mean~~: withdrawn, a PSX texture is its own colour;
  the clear coat is in each car's material (`build_vehicles_cc0.py`).
- [ ] 4.3 ~~The paints re-specified~~: withdrawn, the generated cars leave the hub (cc0-vehicles);
  the range check (4.1) applies to the PSX textures instead.

## 5. The hub

- [ ] 5.1 Rebuild the props and the sectors, import, bake; `scripts/check.sh`.
- [ ] 5.2 After stills; the shadow measure (design section 2.3); the contact shadow if it's needed or
  O3 asks for it.
- [ ] 5.3 A validation record; the design page's F21; the spec delta into `openspec/specs`; archive.

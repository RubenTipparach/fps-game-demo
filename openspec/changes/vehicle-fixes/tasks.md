# Tasks

The owner reported on 2026-09-30: the cars are dark, their wheels don't meet the ground, and there's
no shadow under them. Survey O2 to O4 are open.

## 1. Before

- [x] 1.1 Measure: the ground under every car's wheels, the lightmaps' users, the lights reaching
  each car against its bake, the paints' albedo (design sections 1.1, 2.1, 3.1).
- [x] 1.2 Before stills (`docs/playtest/scripts/vehicle_fixes_before.json`): five, in
  `docs/screenshots/vehicle_fixes/`.

## 2. The wheels

- [ ] 2.1 `check_vehicles`: one ground under every wheel and corner; the test that refuses a spot
  across the kerb.
- [ ] 2.2 The six spots in `layouts/hub.py` onto the road, 0.2 m from the kerb (survey O2).

## 3. The shadows

- [ ] 3.1 `City.vehicle`: an outdoor car in the streets sector.
- [ ] 3.2 `gen_level_hub.py`: the vehicles' boxes count when lights are shared.
- [ ] 3.3 The placement test: each car's body a user of its ground's lightmap.

## 4. The paint

- [ ] 4.1 `vehicle_data.py`: paints as albedo, the 0.03-0.8 range and the tint check, and a test.
- [ ] 4.2 The builder divides out the texture's mean; the clear coat in the material writer.
- [ ] 4.3 The paints in `vehicles.json` re-specified (survey O4); the contact sheet again.

## 5. The hub

- [ ] 5.1 Rebuild the props and the sectors, import, bake; `scripts/check.sh`.
- [ ] 5.2 After stills; the shadow measure (design section 2.3); the contact shadow if it's needed or
  O3 asks for it.
- [ ] 5.3 A validation record; the design page's F21; the spec delta into `openspec/specs`; archive.

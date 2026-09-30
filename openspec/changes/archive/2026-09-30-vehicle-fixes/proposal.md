# Proposal: parked vehicles that sit on the ground, cast shadows under them and read in the dark

## Why

The owner, 2026-09-30, on the vehicles `street-vehicles` put in the hub: "theyre a little dark in
game, the wheels dont align, ... also they seem to be missing underside shadows".

**Measured** on the built hub at seed 7 (design sections 1 to 3; stills in
`docs/screenshots/vehicle_fixes/`):

| Fault | Measured | Cause |
|---|---|---|
| The wheels don't meet the ground | 5 of the 15 cars straddle a kerb: 1 or 2 wheels each hang 0.15 m over the road; a sixth stands wholly on the pavement | Wire Lane's and Lantern Row's spots lie on and across a 2 m pavement strip; a car stands at the height under its centre |
| No shadow under the cars | 14 of the 15 cars cast no baked shadow on the ground | each sector bakes only its own geometry; the ground is the streets sector's, the cars were in the district sectors |
| Dark paint | the paints' albedo is 0.006 (black) to 0.104 (grey); 7 of the 9 paints are darker than the brick walls (0.078) | dark table colours, then multiplied by the painted-metal texture, whose mean is 0.637 |
| Some lights miss the cars | 11 of the 81 lights that reach a car aren't in its bake; Wire Lane's vans get 2 of 5 and 2 of 6 | the hub scene shares a light with a sector by the sector's plan geometry, which doesn't count entities |

## What Changes

- **Every wheel on the ground.** The plan refuses a car spot whose footprint doesn't lie on one
  ground height, naming the spot and what it straddles. Wire Lane's four spots and Lantern Row's
  two move onto the road beside the kerb (survey O2).
- **Cars are static meshes of the level (owner, 2026-09-30: "cars should be static meshes so we
  get it nice light baking").** The level build puts each car's committed model into the glb of
  the sector that owns the ground under it, the streets (the garage's stays with the garage's
  floor), as a static mesh with its collision and 0.1 m lightmap texels. That sector's bake then
  shades the ground under and beside each car and lights the car with every street light. The
  `ENT_car` entity stays as a marker. If the 0.4 m street lightmap leaves the shadow too faint by
  the measure in design section 2.3, the ground under the spots bakes finer, then a contact shadow
  is added (survey O3).
- **Paint that reads at night.** A paint in `vehicles.json` names the albedo it has on the car, not
  a tint the texture darkens: the prop kit divides out the texture's mean. The paints are
  re-specified brighter (design section 3.2), a paint darker than 0.03 or brighter than 0.8 is
  refused, and the car paints get a clear coat, so the neon shows in them (survey O4).

## Capabilities

### Modified Capabilities

- `street-vehicles`: every wheel of a parked vehicle rests on the ground, and a parked vehicle is a
  static mesh of the level, baked with the ground under it.

## Impact

- `tools/levels/city_plan.py`: the one-ground rule in `check_vehicles`; the vehicle entity's
  sector; `test_city_plan.py`.
- `tools/levels/layouts/hub.py`: six spots moved.
- `tools/blender/build_undercity.py`: the cars' models built into their sector's glb;
  `blender_level_import.gd`: the `car` kind becomes a marker.
- `tools/blender/vehicle_data.py`, `vehicles.json`, `build_undercity_props.py`: paints as albedo,
  the range check, the clear coat.
- A hub rebuild and bake; the placement and door tests again.

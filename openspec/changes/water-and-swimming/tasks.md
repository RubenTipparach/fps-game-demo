# Tasks

## 1. Data and core

- [ ] 1.1 `data/water.json` (design section 7) with its loader and validation; `perception.json`
  gains `swimming: 6`.
- [ ] 1.2 `Undercity.Core/Vitals/Breath.cs`: drain, refill and drowning damage through the
  health rule; saved with the game. Tests for the two breath scenarios and the edges (zero
  refill time refused by validation, damage never below the death rule).
- [ ] 1.3 The belt refuses to draw while swimming (core rule, with a test).
- [ ] 1.4 `Undercity.Core/Vitals/Stamina.cs` (owner I3): drains while swimming, refills out of
  deep water, tired speed factor; saved. Tests for both stamina scenarios.

## 2. Layout and plan

- [ ] 2.1 `city_plan.py`: `ENT_water_<id>` entities from every water body (surface, bed, polygon).
- [ ] 2.2 Ladder placement along quay edges (every 30 m, 3 m clear of bridges, boats and
  pillars), railing gaps and grab hoops; the outfall's rungs become a ladder entity.
- [ ] 2.3 The exit rule: sample every surface on a 1 m grid; refuse a plan with any point more
  than 25 m from an exit. Regression: a canal with its ladders removed fails, naming the point.
- [ ] 2.4 `check_standing_room` keeps people and patrol legs out of water.
- [ ] 2.5 The drowned locker moves to the bed under the Tin Bridge (owner I5).

## 3. Godot

- [ ] 3.1 The importer turns `ENT_water_*` into `Water` volumes (Area3D, convex pieces).
- [ ] 3.2 `SwimMotor`: wading, swimming, floating, entry; `PlayerController` hands off to it.
- [ ] 3.3 `scenes/undercity/ladder.tscn` and its climb rules; the ladder prop in
  `build_undercity_props.py` (rails, rungs, hoops) with its `.blend`.
- [ ] 3.4 Mantling onto ledges 0.2-1.0 m above the water.
- [ ] 3.5 Buoyancy for ragdoll bones; items sink to the bed.
- [ ] 3.6 `shaders/water.gdshader`, Material Maker ripple and normal textures, the underwater
  tint and fog, the low-pass on the world bus, splash particles and sounds.
- [ ] 3.7 The breath meter, as approved in mockup D8 (owner I6); heavier breathing and slower
  strokes below 25 % stamina.

## 4. Checks and captures

- [ ] 4.1 Headless `swim_test.tscn`: float height and swim speed in a test pool; a ladder climb;
  a mantle onto a 0.5 m deck; a body floats; an item sinks.
- [ ] 4.2 The placement test also checks every ladder: bottom at least 0.5 m under the surface,
  top on walkable floor with room for the player's cylinder.
- [ ] 4.3 AutoTest input steps (hold an action for N frames) so a script can swim and climb.
- [ ] 4.4 Video: walk off the quay by the Tin Bridge, swim to a ladder, climb out; dive to the
  bed and surface; a body floating in the Cut. Validation record with the numbers.
- [ ] 4.5 Rebuild the affected sectors and rebake them; update the design page and archive.

# Tasks

## 1. Data and core

- [x] 1.1 `data/water.json` (design section 7) with its loader and validation; `perception.json`
  gains `swimming: 6`.
- [x] 1.2 Breath (`Undercity.Core/Vitals/Water.cs`): drain, refill and drowning damage through
  the health rule; saved with the game (save version 2). Tests for the two breath scenarios and
  the edges.
- [x] 1.3 The belt refuses to draw while swimming (core rule, with a test).
- [x] 1.4 Stamina (owner I3): drains while swimming, refills out of deep water, tired speed
  factor; saved. Tests for both stamina scenarios.
- [x] 1.5 The water bodies in the level's data and the one contact rule (`WaterRules`), with
  tests against the hub's exported data.

## 2. Layout and plan

- [x] 2.1 `export_level_data.py` writes every water body (id, surface, bed, polygon) into the
  level's data (design section 1: data, not an `ENT_water` volume).
- [x] 2.2 Ladder placement along quay edges (every 30 m, 3 m clear of bridges, boats and
  pillars), each with a landing on level ground; railing gaps and grab hoops; the outfall's
  rungs become a ladder; boarding ladders on the dry dock's ship.
- [x] 2.3 The exit rule: sample every surface on a 1 m grid; refuse a plan with any point more
  than 25 m of swimming from an exit. Regression: a canal with its ladders removed fails,
  naming the point (`tools/levels/test_city_plan.py`).
- [x] 2.4 `check_standing_room` keeps people and patrol legs out of water.
- [x] 2.5 The drowned locker moves to the bed under the Tin Bridge (owner I5).

## 3. Godot

- [x] 3.1 `LevelWater` answers where water is and how deep a body is in it, from the level's
  data through the core rule.
- [x] 3.2 `SwimMotor`: wading, swimming, floating, entry; `PlayerController` hands off to
  `PlayerWater`.
- [x] 3.3 `scenes/undercity/ladder.tscn` and its climb rules (`LadderMotor`); the ladder's
  stiles, rungs and hoops are built by the level plan.
- [x] 3.4 Mantling onto ledges 0.2-1.0 m above the water.
- [x] 3.5 Buoyancy for ragdoll bones; items fall and sink to the bed.
- [x] 3.6 `shaders/water.gdshader` (the material pipeline writes its material), the underwater
  tint and fog, the low-pass on the SFX bus, splash particles and sounds.
- [x] 3.7 The breath meter, as approved in mockup D8 (owner I6); heavier breathing and slower
  strokes below 25 % stamina.

## 4. Checks and captures

- [x] 4.1 Headless `swim_test.tscn`, in the hub: falling in and floating, swim speed, tired
  speed, the belt, a dive and breath, a quay ladder out, the ship's ladder, climbing down, a
  mantle onto a boat's deck, a body floats, an item sinks.
- [x] 4.2 The placement test also checks every ladder: its foot at least 0.5 m under the
  surface, the climb clear, and room to stand at its landing.
- [x] 4.3 AutoTest holds several actions at once, and sets and logs breath and stamina.
- [ ] 4.4 Video: walk off the quay by the Tin Bridge, swim to a ladder, climb out; dive to the
  bed and surface; a body floating in the Cut. Validation record with the numbers.
- [ ] 4.5 Rebake the rebuilt sectors; update the design page and archive.

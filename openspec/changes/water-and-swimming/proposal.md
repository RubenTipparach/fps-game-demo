# Proposal: water you can fall into, swim in and climb out of

## Why

The owner, playtesting on 2026-09-28: "Falling into the Bay there's no water physics, swimming,
and no way to get back out, need a ladder or something. And need water physics."

What happens today, measured:
- The hub's water (the Cut, the dry dock basin and the dock gate channel) is a flat, opaque,
  zero-thickness surface with no collider. A body falls through it to the bed, 2.3 m below the
  surface in the Cut and 3.8 m in the dry dock.
- The quay top is 2.2 m above the surface and 4.5 m above the Cut's bed. The player's jump
  peaks at 1.24 m (1.99 m with a crouch tuck). Nothing in the water is in reach, so a fall is a
  soft lock: the only way out is loading a save.
- There are unrailed stretches of the west quay beside both bridges and at the outfall, so
  falling in is easy.
- The one ladder, at the outfall, is decoration: 4 cm rungs that the step-up rule can't stand on.
- From under the surface nothing looks or sounds different: `docs/screenshots/water_and_swimming/baseline_fallen_in_the_cut.png`.

The owner answered the survey on 2026-09-28: the recommendations for I3 to I6 accepted, and to
I3 (drowning) they added "swimming consumes stamina but slowly". So drowning is on, the exits
are as designed, the drowned locker moves under water (I5), the breath meter D8 is approved
(I6), and swimming tires you. I1 puts this change first.

Swimming was a non-goal of the Drains (a scripted 35 s swim with a breath bar). A hub with a
canal down its middle makes it a system: the same rules serve the Cut, the dry dock and the
Drains' flooded bypass.

## What Changes

- **Water in the level's data.** Every water body in a layout goes into the level's data, with
  its surface and bed heights, from the same layout entry that draws it, and one core rule says
  how deep a body is in it.
- **Wading and swimming.** The player wades in water up to the chest and swims above that:
  buoyancy holds the eyes just above the surface, jump rises and crouch dives, and speeds, drag
  and noise come from `data/water.json`.
- **Breath.** 45 s under water, the Drains' number, then 8 damage a second. Breath refills in
  3 s at the surface. One rule in the core, shared with the Drains' bypass.
- **Stamina for swimming** (owner, I3): 100 points, draining 0.8 a second while swimming, so a
  runner can swim about 125 s before tiring. Tired, they swim at half speed. It refills in
  about 8 s out of deep water. Heavier breathing warns you; it adds no meter.
- **Ways out.** Climbable ladders on every quay and over the side of the dry dock's ship, no
  more than 25 m of swimming from anywhere, and a mantle onto any ledge up to 1.0 m above the
  water: boat decks, the outfall ledge. The outfall's decorative ladder becomes a real one.
- **Water physics for bodies and things.** Ragdolls float, with water drag; dropped items fall
  to the floor, sinking through water to the bed, and can be picked up there; splashes where
  things enter.
- **Seeing and hearing water.** A water shader (depth colour, scrolling normals, rain ripples,
  refraction, both faces drawn), an underwater fog and tint, and muffled sound below the
  surface.
- **A breath meter on the HUD**, shown only while it isn't full: mockup D8, approved (survey I6).
- **The drowned locker moves under water** (survey I5), to the bed under the Tin Bridge, as its
  map note always said.
- **People stay out of the water.** "People stand clear of the level" (level geometry) grows a
  clause: no standing spot or patrol leg in water.

## Capabilities

### New Capabilities
- `water-and-swimming`: water in the level's data, wading, swimming, breath, stamina, exits,
  and water physics for bodies and items.

### Modified Capabilities
- `level-geometry`: "People stand clear of the level" also keeps people out of water, and a
  new requirement says every water body has a way out.

## Impact

- **Layout and plan:** `tools/levels/city_plan.py` places ladders (quays, the outfall, the dry
  dock's ship), their landings and railing gaps from `tools/levels/layouts/hub.py`, and asserts
  the exit rule; `export_level_data.py` writes the water into the level's data. `the-drains`
  reuses all of it.
- **Core:** `Undercity.Core/Vitals/Water.cs` (the water table, breath, stamina) and
  `World/WaterBodies.cs` (the contact rule), with tests; the save carries breath and stamina.
- **Godot:** `PlayerWater` and its swim, ladder and mantle motors, handed the body by
  `PlayerController`; `scenes/undercity/ladder.tscn`; ragdoll buoyancy; falling and sinking
  items; the water and underwater shaders; a splash; the AIR bar.
- **Data:** `data/water.json`; `data/perception.json` gains a swimming noise (6 m).
- **Art:** the ladders are built by the level plan with the quays (their heights differ per
  quay), not a Blender prop; the water's normal map is the existing procedural one, and its
  rain ripples are computed in the shader.
- **Rebuild:** the hub's sectors are rebuilt and rebaked.

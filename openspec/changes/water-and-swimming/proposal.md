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

Swimming was a non-goal of the Drains (a scripted 35 s swim with a breath bar). A hub with a
canal down its middle makes it a system: the same rules serve the Cut, the dry dock and the
Drains' flooded bypass.

## What Changes

- **Water volumes.** Every water body in a layout becomes a volume the game knows about, with
  its surface and bed heights, built from the same layout entry that draws it.
- **Wading and swimming.** The player wades in water up to the chest and swims above that:
  buoyancy holds the eyes just above the surface, jump rises and crouch dives, and speeds, drag
  and noise come from `data/water.json`.
- **Breath.** 45 s under water, the Drains' number, then 8 damage a second. Breath refills in
  3 s at the surface. One rule in the core, shared with the Drains' bypass.
- **Ways out.** Climbable ladders on every quay, no more than 25 m of swimming from anywhere,
  and a mantle onto any ledge up to 1.0 m above the water: boat decks, the outfall ledge. The
  outfall's decorative ladder becomes a real one.
- **Water physics for bodies and things.** Ragdolls float face down, with water drag; dropped
  items sink to the bed and can be picked up there; splashes and ripples where things enter.
- **Seeing and hearing water.** A water shader (depth colour, scrolling normals, rain ripples,
  refraction, both faces drawn), an underwater fog and tint, and muffled sound below the
  surface.
- **A breath meter on the HUD**, shown only while it isn't full. It is new UI, so it waits for
  the owner's approval of mockup D8 (survey I6).
- **People stay out of the water.** "People stand clear of the level" (level geometry) grows a
  clause: no standing spot or patrol leg in water.

## Capabilities

### New Capabilities
- `water-and-swimming`: water volumes, wading, swimming, breath, exits, and water physics for
  bodies and items.

### Modified Capabilities
- `level-geometry`: "People stand clear of the level" also keeps people out of water, and a
  new requirement says every water body has a way out.

## Impact

- **Layout and plan:** `tools/levels/city_plan.py` places water volumes, ladders and railing gaps
  from `tools/levels/layouts/hub.py`, and asserts the exit rule. `the-drains` reuses all of it.
- **Core:** `Undercity.Core/Vitals/Breath.cs`, with tests.
- **Godot:** a swim motor used by `PlayerController`, `scenes/undercity/ladder.tscn`, the water
  shader, a buoyancy component for ragdolls and a sinking rule for world items.
- **Data:** `data/water.json`; `data/perception.json` gains a swimming noise (6 m).
- **Art:** a ladder prop (Blender), water normal and ripple textures (Material Maker).
- **Rebuild:** the hub's `streets` sector and the sectors that get ladders are rebuilt and
  rebaked.

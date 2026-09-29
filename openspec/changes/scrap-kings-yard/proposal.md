# Proposal: Scrap King's Yard and mission M2, Chop Job

## Why

The second mission is a robbery in a junkyard, which the owner named among the first
locations. Where the Drains teach disguise and patience, the Yard teaches tech: power,
searchlights, cameras, turrets, and robot dogs that no disguise fools. It's also the first
mission with a choice between two quest givers (S1 Kingmaker: kill Crusher for Jax, or expose
Jax to Crusher).

## What Changes

- **Scrap King's Yard,** 180 x 130 m at night:
  - car stacks and a fence gap;
  - a container maze with a three-high stack;
  - a crawler crane and the car crusher;
  - the chop shop warehouse with Crusher's office on a mezzanine;
  - the generator shed and fuel tanks;
  - the Kings' barracks;
  - the gatehouse on Scrapyard Road;
  - a rail gate from the hub's freight tunnel.
- **Mission M2, Chop Job.** Steal the prototype nav core from Crusher's office safe.
- **Side objectives:**
  - S1 Kingmaker (Jax): kill Crusher, expose Jax, or leave them both;
  - S2 The Ledger (Petra): take or copy the Kings' ledger.
- **Four routes:**
  - social: the gate, then talking to Crusher;
  - stealth: the fence gap, the stacks, the containers and the skylight;
  - tech: the rail gate, killing the generator, the back door;
  - force.
- **The plan is `tools/levels/layouts/yard.py`,** drawn as `docs/design/maps/yard.svg`.

## Capabilities

### New Capabilities
- `scrap-kings-yard`: the Yard level, the Chop Job mission, S1 and S2, and their outcomes.

### Modified Capabilities
None.

## Impact

- New level `game/levels/undercity/yard/`: an exterior with the sky shader, moonlight and three
  searchlights, built from a junk kit (crushed cars, containers, crane, fence).
- Dialog: Bolt, Dutch, Crusher; Jax's and Petra's lines.
- Robot dog rig; turret; searchlight.

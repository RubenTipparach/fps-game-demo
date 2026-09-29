## ADDED Requirements

### Requirement: Every water body has a way out
Every point of every water surface in a level SHALL be within 25 m of swimming (the shortest path
through the water, round hulls, buildings and pillars) of a way out: a ladder's foot, or a quay
whose top is within the mantle rise of `data/water.json` (0.2-1.0 m above the surface). Every
ladder SHALL reach at least 0.5 m under the surface and land its climber on level floor with
room for the player's collider. The city plan generator SHALL refuse a layout that breaks this,
naming the water body and the farthest point, and the placement test SHALL check each ladder in
the built level with the player's collider.

#### Scenario: A canal with no ladders
- **WHEN** a layout's canal has no ladder or low quay within 25 m of swimming of some point of
  its surface
- **THEN** the plan exits naming the canal and that point, and nothing is built

#### Scenario: A ladder by a kerb
- **WHEN** a quay has a raised strip narrower than a standing player between the water and the
  street
- **THEN** its ladders land their climbers on the street past the strip, not astride its kerb

## MODIFIED Requirements

### Requirement: People stand clear of the level
Every person a level places SHALL stand clear of it, measured with the collider the game gives
them: the NPC scene's capsule (`scenes/undercity/npc.tscn`, 0.35 x 1.8 m) for every NPC,
civilian and patrol stop, and the player scene's cylinder (`scenes/undercity/player.tscn`,
0.4 x 1.8 m) at every spawn point. Standing clear means the body overlaps no world collider
and no other person, the floor is within 0.05 m of its feet, it stands in no water, and
outdoors it stands on level ground. A patrol SHALL walk from stop to stop without its capsule
crossing a building, a fixture, a prop, a solid or water. The city plan generator
(`check_standing_room`) SHALL refuse a layout that breaks this for the solids the plan
describes (detail boxes, stall parts, Skyway pillars, fixture and prop footprints, walls,
building shells, curbs, water), reading both colliders from their scenes; the placement test
(`scenes/undercity/tests/placement_test.tscn`) SHALL check every placement in the built level
against the real physics.

Pinned by `check_standing_room`, which passes on the committed hub and on the old layout names
23 faults (Tank inside the Rusty Anchor's bar counter among them), and by the placement test:
96 of 96 placements pass on the committed hub, and the level before this fix fails 11,
recorded in `docs/validation/2026-09-28-npc-placement.md`.

#### Scenario: An NPC inside a counter
- **WHEN** the layout stands an NPC where their capsule overlaps a bar counter
- **THEN** the plan exits naming the NPC, the counter and how far in they stand, and nothing
  is built

#### Scenario: A vendor behind a stall
- **WHEN** a civilian stands in a stall's vendor space, between its counter and its back
- **THEN** the check passes

#### Scenario: A spawn point inside a prop
- **WHEN** a spawn marker in the built level puts the player's cylinder inside a container
- **THEN** the placement test prints FAIL naming the spawn and the container, and exits 1

#### Scenario: A patrol through a building
- **WHEN** a patrol leg, swept by the NPC's capsule, crosses a building or a pillar
- **THEN** the plan exits naming the patrol, the leg and what it runs through

#### Scenario: A patrol along the canal
- **WHEN** a patrol leg's capsule crosses the Cut's water
- **THEN** the plan exits naming the patrol, the leg and the water

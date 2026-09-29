## ADDED Requirements

### Requirement: Every doorway is framed
Every door a city level builds SHALL be built by E1M3's rules. This covers every door an
enterable building declares, and every closed door a building shows. Specifically:
- It SHALL be carved at its frame's `fits` size: its clear opening plus `detailing.REVEAL`
  (0.1 m) at each jamb and at the head.
- It SHALL have a frame from `detailing.door_frame`: liners filling the reveals, and an
  architrave or portal standing proud of each wall face that faces air.
- The frame's boxes SHALL be registered with the z-fighting check.
- An entrance 2.0 m wide or wider SHALL have a portal: pilasters with plinths and capitals, and
  a lintel with a lit downlight, whose light has a visible fixture and a corona.
- An exterior door 2.0 m wide or wider SHALL be a public entrance with a sliding door
  (requirement "Public entrances open as you walk up"). A door with a lock SHALL have a leaf
  in its frame. Any other door SHALL be an open, framed doorway.

The city plan generator (`tools/levels/city_plan.py`, `check_doors`) SHALL refuse a door that
is unframed, carved at other than its fits, or whose frame doesn't fit the wall it stands in.

#### Scenario: An interior door
- **WHEN** a building declares a 1.4 m door between two rooms
- **THEN** the opening is carved 1.6 x 2.5 m, the clear opening is 1.4 x 2.4 m, an architrave
  stands 0.1 m proud on both faces, and the z-fighting check passes

#### Scenario: A door too near a corner
- **WHEN** a door's frame would run past the end of the wall it stands in
- **THEN** the plan exits naming the building, the door and how far the frame overruns, and
  nothing is built

#### Scenario: An entrance
- **WHEN** a building declares a 3.0 m exterior door
- **THEN** it has a portal with pilasters on plinths, capitals and a lintel with a downlight,
  and the building's sign sits above the lintel

### Requirement: Every building on the street shows a door
Every building that faces walkable ground SHALL show at least one door on such an edge. Facing
walkable ground means having a facade edge at least 2.2 m long that looks at a street, lane,
square or paved passage. The door is either an enterable building's declared door or a closed
door built in the building's style:
- a glazed shop door in each shop bay;
- a residents' door on shop buildings of two floors or more;
- a plank or sheet door on a shanty;
- a steel man door on a workshop or dock building.

A closed door SHALL be built by the rules of "Every doorway is framed", SHALL be solid to
collision, and SHALL show no use prompt. The city plan generator (`check_building_doors`) SHALL refuse a plan in which such a
building shows no door, naming the building and the edge.

#### Scenario: A shop with no way in
- **WHEN** a lot's only street-facing openings are shop windows
- **THEN** the plan exits naming the lot, and nothing is built

#### Scenario: A shanty on a side passage
- **WHEN** a shanty's only walkable edge faces a paved side passage
- **THEN** it has a door on that edge

#### Scenario: A building with no walkable face
- **WHEN** a lot's every edge faces another building
- **THEN** it needs no door, and the check passes

### Requirement: Every door opens onto ground a person can reach
Every exterior door SHALL have a clear approach: ground clear of every building, lot, fixture,
prop footprint and water.
- **An entrance** (2.0 m wide or wider): a strip 0.6 m wider than its frame on each side,
  running straight out from the wall until it lies on open ground (a street, lane or square),
  at most 12 m.
- **A service door:** a 2.0 m landing 0.6 m wider than its frame on each side, joined to open
  ground by walkable ground at least 1.2 m wide.

The lot planner SHALL cut every approach from the lots after they are split, so that no other
lot changes. The city plan generator (`check_door_approaches`) SHALL refuse a plan in which an
approach is blocked or doesn't reach open ground. The placement test SHALL walk the built
level's navmesh from 1 m outside every exterior door to the runner's spawn.

#### Scenario: A building in front of an entrance
- **WHEN** a lot stands 1.35 m in front of the Harbor Fish Hall's 4 m north entrance
- **THEN** the plan exits naming the entrance, the lot and the clear depth

#### Scenario: A back door onto an alley
- **WHEN** a service door opens onto a 2.0 m landing in a passage 1.5 m wide that leads to a
  street
- **THEN** the check passes

#### Scenario: A door into a sealed pocket
- **WHEN** a door's approach is clear but the ground round it joins no street
- **THEN** the plan exits naming the door, and in a built level the placement test prints FAIL
  naming the door and exits 1

### Requirement: Public entrances open as you walk up
Every public entrance SHALL have an automatic sliding door: two leaves that slide apart along
the building's inside face when the runner, or a person in a group the door names, comes within
its trigger radius. It SHALL stay open while anyone is within that radius and close after its
wait. It SHALL never lock, and it SHALL hold no state a save records. The runner's and NPCs'
trigger radii, the wait and the leaves' speed SHALL come from `data/doors.json`. E1M3's
`Brushfire.Doorway` and `Brushfire.Door` SHALL be the one implementation, used by the reference
maps and the hub alike. The navmesh SHALL pass through a closed public entrance. The city plan
generator (`check_sliding_room`) SHALL refuse a leaf whose open position meets a wall, a fixture
or another door.

#### Scenario: The runner walks into the Rusty Anchor
- **WHEN** the runner walks up to the Anchor's 3.0 m entrance
- **THEN** its leaves slide apart before the runner reaches them, and close behind the runner
  after the wait

#### Scenario: A civilian flees through a closed entrance
- **WHEN** a fleeing civilian's navmesh path runs through the Fish Hall's closed north entrance
- **THEN** the door opens ahead of the civilian and the civilian walks through without stopping

#### Scenario: A leaf with no room
- **WHEN** a counter stands on the inside wall where a leaf would slide
- **THEN** the plan exits naming the entrance, the leaf and the counter, and nothing is built

## MODIFIED Requirements

### Requirement: People stand clear of the level
Every person a level places SHALL stand clear of it, measured with the collider the game gives
them: the NPC scene's capsule (`scenes/undercity/npc.tscn`, 0.35 x 1.8 m) for every NPC,
civilian and patrol stop, and the player scene's cylinder (`scenes/undercity/player.tscn`,
0.4 x 1.8 m) at every spawn point. Standing clear means the body overlaps no world collider
and no other person, the floor is within 0.05 m of its feet, it stands in no water, and
outdoors it stands on level ground. Every NPC and civilian SHALL also stand on the level's
baked navmesh, within 0.5 m of their feet, since whoever fights, flees or cowers moves on it. A
patrol SHALL walk from stop to stop without its capsule crossing a building, a fixture, a prop,
a solid or water. The city plan generator (`check_standing_room`) SHALL refuse a layout that
breaks this for the solids the plan describes (detail boxes, stall parts, Skyway pillars,
fixture and prop footprints, walls, building shells, curbs, water), reading both colliders from
their scenes; the placement test (`scenes/undercity/tests/placement_test.tscn`) SHALL check
every placement in the built level against the real physics and the navmesh.

Pinned by `check_standing_room`, which passes on the committed hub and on the old layout names
23 faults (Tank inside the Rusty Anchor's bar counter among them), and by the placement test:
96 of 96 placements pass on the committed hub, and the level before this fix fails 11,
recorded in `docs/validation/2026-09-28-npc-placement.md`. The navmesh check fails Tank on the
hub before the bar's leg was shortened (openspec/changes/hub-doorways, design section 3.11).

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

#### Scenario: An NPC in an aisle the navmesh dropped
- **WHEN** an NPC stands in an aisle too narrow for the navmesh's agent, so the nearest navmesh
  is more than 0.5 m from their feet
- **THEN** the placement test prints FAIL naming the NPC, the distance and the nearest navmesh
  point, and exits 1

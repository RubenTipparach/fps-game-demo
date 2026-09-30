# Level Geometry Specification

## Purpose
What every generated level's geometry guarantees today: no two surfaces z-fight, frame props
stand proud of the openings they sit in, every room is carved, and every person the level
places stands clear of it. Each requirement here is enforced by the level generators, which
refuse to write a level that breaks it; the last is also checked in the built level by the
placement test, with the game's own colliders.

## Requirements

### Requirement: No coplanar overlapping faces
A level generator SHALL refuse to write a level in which two faces share a plane (within
5 mm), face the same way and overlap. Faces pressed back to back are exempt. The generator
checks, per `tools/godot/detailing.py` `assert_no_zfighting`:
- prop against wall, prop against detail, and prop against prop;
- detail against wall and detail against detail, unless the details are CSG-merged with the
  walls.

#### Scenario: A trim flush with a wall face
- **WHEN** a generator registers a baseboard whose front face is coplanar with, and overlaps,
  another trim's front face
- **THEN** it exits with "z-fighting: N coplanar overlapping face pairs" naming both, and
  writes nothing

#### Scenario: A clean level
- **WHEN** `gen_map.py`, `build_cistern.py` or `gen_level_csg.py` runs on the committed sources
- **THEN** it prints "z-fighting check: clean" and writes the level

### Requirement: Frame props have an inset clear opening
A frame prop (a door frame or archway) SHALL be placed in an opening of its `fits` size and
SHALL have a `clear` opening smaller by `REVEAL` (0.1 m) at each jamb and at the lintel, so that it
stand proud of the walls and ceiling instead of sharing their planes. The frame's boxes SHALL
be registered with the z-fighting check as props.

#### Scenario: A doorway frame in a 3.2 x 3.3 m opening
- **WHEN** the doorway frame is placed in a carved 3.2 x 3.3 m opening
- **THEN** its clear opening is 3.0 x 3.2 m and the check passes

### Requirement: Every room is carved
Every room and doorway an enterable building declares SHALL be carved out of the building's
block. The city plan generator (`tools/levels/city_plan.py`, `check_rooms_carved`) SHALL
refuse a plan in which a room's or a door's interior box has no cutter. A building's sign
SHALL displace only the window recesses in its zone, never a room, a door, a parapet or a
landing.

Pinned by `check_rooms_carved`: the committed hub plans clean, and the plan with the old sign
rule (every cutter in the sign's zone dropped) exits naming the three rooms it left solid (the
Tsang Shrine's hall, the garage's bay and the MerSec checkpoint's room), recorded in
`docs/validation/2026-09-28-npc-placement.md`.

#### Scenario: A sign in front of a hall
- **WHEN** a building's sign zone overlaps the cutter of the room behind it
- **THEN** the room is carved, and only the window recesses in the zone are left out

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

### Requirement: Puddles lie where water gathers
A city level's standing water SHALL be placed by the level plan and drawn by the ground's shader
from a puddle mask the plan writes, never a pattern in the ground's textures: the ground
textures SHALL hold no texel with a roughness under 0.2. Every puddle SHALL lie on open ground in
the rain, by one of three rules:
- in a gutter, on the road along a kerb;
- round a kerb gully;
- just outside the drip edge of an awning or the Skyway's deck.

No puddle SHALL lie under a roof (a shelter with 1 m or more of headroom over the ground, the
rule the core's wetness uses), over a kerb top, a stair, a bridge deck or the rail tracks, within
0.3 m of a building, lot, fixture or prop footprint, or over another puddle. The choices SHALL
come from a seeded stream of their own, so that placing puddles moves nothing else in the level.
The city plan generator (`check_puddles`) SHALL refuse a plan that breaks any of this, naming
the puddle. The committed mask SHALL agree with the plan, and a core test SHALL check every
puddle of the level data against the core's shelter rule (`PuddleDef.InTheRain`).

#### Scenario: Under the Skyway
- **WHEN** a puddle would lie on the road under the Skyway's deck
- **THEN** the plan places none there, and a puddle forced there is refused, naming it and the
  deck

#### Scenario: A kerb in the rain
- **WHEN** a road runs 40 m or more along a kerb with nothing overhead
- **THEN** it has a gully with a round puddle and at least three gutter puddles along the kerb,
  none on the kerb's top

#### Scenario: The mask
- **WHEN** the mask test reads the committed puddle mask
- **THEN** every puddle's centre reads inside a puddle at its own height, and every point 0.3 m
  outside all puddles reads dry

#### Scenario: The textures
- **WHEN** the texture test reads the committed asphalt and paving ORM maps
- **THEN** no texel has a roughness under 0.2

#### Scenario: Drawn by the ground's shader
- **WHEN** the hub loads
- **THEN** it hands its puddle mask, its rect and the numbers it decodes with to the ground's
  shader, and the street's asphalt and paving are drawn by that shader

### Requirement: Standing water ripples with the rain
Rain SHALL ring the surface of every puddle and the canal alike: both SHALL draw their rings with
one shader function (`shaders/rain_ripples.gdshaderinc`) and one set of numbers (the water's, in
`materials.json`), so a drop reads the same wherever it lands.

#### Scenario: One ripple
- **WHEN** the shader test reads the ground and water shaders and their materials
- **THEN** both include the one ripple function, neither defines its own, and the ground
  materials' ripple numbers equal the water's

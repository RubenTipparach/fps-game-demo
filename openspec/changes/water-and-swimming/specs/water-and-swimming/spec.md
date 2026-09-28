## ADDED Requirements

### Requirement: Water volumes come from the layout
Every water body in a level's layout SHALL become a water volume in the built level, carrying
the body's surface and bed heights from the layout, so the water the map draws, the water the
level shows and the water the game simulates are one entry.

#### Scenario: The Cut
- **WHEN** the hub is built from `tools/levels/layouts/hub.py`
- **THEN** the level holds a water volume for the Cut with surface -2.2 m and bed -4.5 m, and
  one for each other water body in the layout

### Requirement: The player wades and swims
The player SHALL wade where the water at their feet is 0.1-1.2 m deep, at 0.6 x their ground
speed, and SHALL swim where it is deeper: no gravity, 3.0 m/s along the look direction, rising
at 2.0 m/s and diving at 2.4 m/s, floating with the eyes 0.15 m above the surface. The numbers
SHALL come from `data/water.json`.

#### Scenario: Falling in
- **WHEN** the runner walks off the quay into the Cut
- **THEN** within 2 s they float with their eyes 0.10-0.20 m above the surface, and swimming
  forward moves them at 2.9-3.1 m/s

### Requirement: Breath runs out under water
Breath SHALL drain one second per second while the player's eyes are under a water surface,
from `breath_s` (45 s), and SHALL refill to full in `breath_refill_s` (3 s) at the surface. With
no breath left the player SHALL take `drown_damage_per_s` (8) damage each second through the
health rule. One rule in `Undercity.Core` SHALL serve every water body, the Drains' bypass
included.

#### Scenario: Staying down too long
- **WHEN** a player with 100 health stays under water for 50 s
- **THEN** their breath is 0 and their health is 60

#### Scenario: Coming up for air
- **WHEN** a player with no breath left surfaces for 3 s
- **THEN** their breath is full again

### Requirement: Ladders and ledges lead out of the water
A ladder SHALL be climbable at 2.4 m/s by facing it and moving forward, and SHALL put the player
on the floor at its top. A ledge whose top is 0.2-1.0 m above the water surface, within 0.6 m in
front of a swimming player and with room to stand, SHALL be climbable by jumping.

#### Scenario: Out by the ladder
- **WHEN** the runner swims to a quay ladder in the Cut and holds forward while facing it
- **THEN** they climb out and stand on the quay within 2 s

#### Scenario: Onto a boat
- **WHEN** the runner swims up to a moored boat whose deck is 0.5 m above the surface and jumps
- **THEN** they end up standing on its deck

### Requirement: No weapon while swimming
Entering the swimming state SHALL holster a drawn weapon, and the belt SHALL refuse to draw one
until the player is wading or dry.

#### Scenario: Drawing in deep water
- **WHEN** the runner presses the Kestrel's belt key while swimming
- **THEN** nothing is drawn and the feed says "Not while swimming."

### Requirement: Bodies float and things sink
A ragdoll in water SHALL float, pushed up in proportion to how much of each bone is under the
surface, with water damping; a dropped item SHALL sink to the bed and stay usable there.

#### Scenario: A body in the Cut
- **WHEN** an NPC dies falling into the Cut
- **THEN** the body floats at the surface and comes to rest there

#### Scenario: A dropped medkit
- **WHEN** the runner drops a medkit while swimming
- **THEN** it sinks to the bed and can be picked up there

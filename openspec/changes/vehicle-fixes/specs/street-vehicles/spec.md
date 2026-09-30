## ADDED Requirements

### Requirement: A parked car stands on one ground and bakes with it
The plan SHALL refuse a parked car outdoors whose footprint doesn't lie on one ground: the ground
height over a 5 x 3 grid across the footprint, its corners among the points, SHALL agree within
0.01 m. A car indoors stands on its room's one floor. A parked car SHALL be a static mesh of the
level, built into the glb of the sector that owns the ground under it at the plan's place and
heading, with its collision, beside an `ENT_car` marker, and SHALL be a user of that sector's
baked lightmap at a quarter of the level's texel.

#### Scenario: Across a kerb
- **WHEN** a car spot lies partly on a 0.15 m pavement and partly on the road
- **THEN** the plan is refused, naming the car, its place and the two ground heights

#### Scenario: A static mesh baked with its ground
- **WHEN** the hub is built and baked
- **THEN** each parked car is a static mesh in the sector that owns the ground under it, with its
  static body, on that sector's ground, and a user of that sector's lightmap, so its shadow falls
  on that ground

### Requirement: A vehicle's albedo lies in range
Each vehicle variant's texture SHALL have a mean linear albedo from 0.03 to 0.8, from a very dark
paint to a very light one, and the table's check SHALL refuse one outside that range, naming the
variant and its albedo.

#### Scenario: A texture too dark
- **WHEN** a variant's texture has a mean albedo of 0.003
- **THEN** the check names the variant and its albedo, outside 0.03-0.8

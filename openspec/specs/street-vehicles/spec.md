# street-vehicles Specification

## Purpose
What a city level's parked vehicles are and where they stand: models converted from a pinned CC0
pack by a table, placed by the level plan on its car spots, standing on one ground and baked into
it as static meshes with a contact shadow each (openspec/changes/archive/2026-09-30-street-vehicles,
2026-09-30-cc0-vehicles, 2026-09-30-vehicle-fixes).

## Requirements

### Requirement: Parked vehicles are pack models placed by the plan
A city level's parked vehicles SHALL be models converted by `tools/blender/build_vehicles_cc0.py`
from the pack that `tools/blender/vehicles.json` names, one glb per variant, never boxes built in
the level plan. Each model SHALL stay within the table's triangle budget (2,500) and SHALL have no
two triangles that share a plane, face the same way and overlap. The plan SHALL place a vehicle on
every car spot, dealing its model from a seeded stream of its own so that each variant shows once
before any repeats, and SHALL refuse a plan whose model, read from the committed glb, doesn't fit
inside its spot's footprint.

#### Scenario: A car spot
- **WHEN** the hub's layout has a 5.6 x 2.6 m car spot
- **THEN** the built level has one vehicle there, a PSX Style Cars body in one of its own colours,
  whose glb fits inside the spot, with its own collision

#### Scenario: Over budget
- **WHEN** a body has more triangles than the budget
- **THEN** the converter stops, naming the body and its count

#### Scenario: Too long for the spot
- **WHEN** the 5.22 m full-size saloon is placed on a 4.6 x 2.0 m spot
- **THEN** the plan is refused, naming the spot and the model

#### Scenario: A face laid flush over another
- **WHEN** a body has a face lying over another in the same plane, facing the same way
- **THEN** the converter moves the vertex onto the face's edge when the overlap is a sliver under
  5 mm, and stops, naming the body, when it is larger

### Requirement: A vehicle taken from a CC0 pack is pinned and recorded
A vehicle model converted from a CC0 pack SHALL come from a pack pinned in
`tools/deps/vehicle_packs.json` by its SHA-256, with its URL, author and licence recorded there,
and the fetch SHALL refuse a download whose hash differs. The converted glb SHALL follow the prop
kit's conventions (its real length, front along +Y, origin at the floor centre of its footprint,
collision boxes, the triangle budget) and SHALL record its pack, author, licence and hash.

#### Scenario: A changed download
- **WHEN** a pack's download no longer matches its pinned SHA-256
- **THEN** the fetch stops, naming the pack and both hashes

#### Scenario: One style
- **WHEN** the hub is built
- **THEN** every parked vehicle is a model converted from the PSX Style Cars pack

#### Scenario: A converted car
- **WHEN** a PSX Style Cars saloon is converted
- **THEN** its glb is its table length long to 1 cm, faces +Y, stands on its origin's floor, has
  its collision, stays in the car budget and names its pack, author, licence and hash

#### Scenario: An unpinned pack
- **WHEN** the vehicle table names a pack no list in `tools/deps` pins
- **THEN** the table is refused, naming the pack

### Requirement: A parked car stands on one ground and bakes with it
The plan SHALL refuse a parked car outdoors whose footprint doesn't lie on one ground: the ground
height over a 5 x 3 grid across the footprint, its corners among the points, SHALL agree within
0.01 m. A car indoors stands on its room's one floor. A parked car SHALL be a static mesh of the
level, built into the glb of the sector that owns the ground under it at the plan's place and
heading, with its collision, and SHALL be a user of that sector's baked lightmap at a quarter of
the level's texel. Its `ENT_car` entity SHALL be its contact shadow: a decal centred under it,
0.3 m longer and wider than the committed model's footprint, that darkens the ground, makes it
matte and occludes it, as a road stays dry and hidden from the sky under a car parked in the rain.

#### Scenario: Across a kerb
- **WHEN** a car spot lies partly on a 0.15 m pavement and partly on the road
- **THEN** the plan is refused, naming the car, its place and the two ground heights

#### Scenario: A contact shadow
- **WHEN** the hub is built
- **THEN** each parked car's entity is a decal centred under it, the size of its model's footprint
  plus 0.3 m

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

## RENAMED Requirements

- FROM: `### Requirement: Parked vehicles are generated models placed by the plan`
- TO: `### Requirement: Parked vehicles are pack models placed by the plan`

## MODIFIED Requirements

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

## ADDED Requirements

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

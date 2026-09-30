## MODIFIED Requirements

### Requirement: Parked vehicles are generated models placed by the plan
A city level's parked vehicles SHALL be models built by the prop kit from
`tools/blender/vehicles.json`, one glb per variant, never boxes built in the level plan. Each
model SHALL stay within its type's triangle budget (2,500 for a car or van, 3,500 for a truck)
and pass the z-fighting check. The plan SHALL place a vehicle entity on every car spot, drawing
its model from a seeded stream of its own among the variants that fit the spot, and SHALL refuse
a plan whose model, read from the committed glb, doesn't fit inside its spot's footprint, or whose
spot doesn't lie on one ground height under every wheel and corner. A vehicle SHALL be baked with
the ground under it, in the sector that owns that ground.

#### Scenario: A car spot
- **WHEN** the hub's layout has a 4.6 x 2.0 m car spot
- **THEN** the built level has one vehicle there, a sedan, taxi or van whose glb fits inside the
  spot, with its own collision

#### Scenario: Over budget
- **WHEN** a variant's model has more triangles than its type's budget
- **THEN** the prop kit's build stops, naming the variant and its count

#### Scenario: Too long for the spot
- **WHEN** a model longer than 4.6 m is placed on a 4.6 x 2.0 m spot
- **THEN** the plan is refused, naming the spot and the model

#### Scenario: Across a kerb
- **WHEN** a car spot lies partly on a 0.15 m pavement and partly on the road
- **THEN** the plan is refused, naming the car, its spot and the two ground heights

#### Scenario: Baked with its ground
- **WHEN** the hub is baked
- **THEN** each parked car's body is a user of the lightmap of the sector that owns the ground under
  it, so its shadow falls on that ground

## ADDED Requirements

### Requirement: A vehicle's paint names the albedo it has on the car
A paint in `tools/blender/vehicles.json` SHALL give the car's average colour, which the prop kit
reaches by dividing out the paint texture's mean albedo. The table SHALL refuse a paint whose
albedo is under 0.03 or over 0.8, or which the texture can't reach.

#### Scenario: A paint too dark
- **WHEN** a paint's colour has an albedo of 0.006
- **THEN** the table is refused, naming the paint and its albedo

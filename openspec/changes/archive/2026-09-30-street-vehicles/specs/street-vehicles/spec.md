## ADDED Requirements

### Requirement: Parked vehicles are generated models placed by the plan
A city level's parked vehicles SHALL be models built by the prop kit from
`tools/blender/vehicles.json`, one glb per variant, never boxes built in the level plan. Each
model SHALL stay within its type's triangle budget (2,500 for a car or van, 3,500 for a truck)
and pass the z-fighting check. The plan SHALL place a vehicle entity on every car spot, drawing
its model from a seeded stream of its own among the variants that fit the spot, and SHALL refuse
a plan whose model, read from the committed glb, doesn't fit inside its spot's footprint.

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

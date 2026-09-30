## ADDED Requirements

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

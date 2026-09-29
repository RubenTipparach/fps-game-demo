## ADDED Requirements

### Requirement: Puddles lie where water gathers
A city level's standing water SHALL be decals the level plan places, never a pattern in the
ground's textures: the ground textures SHALL hold no texel with a roughness under 0.2. Every
puddle SHALL lie on open ground in the rain, by one of three rules:
- in a gutter, on the road along a kerb;
- round a kerb gully;
- just outside the drip edge of an awning or the Skyway's deck.

No puddle SHALL lie under a roof (a shelter with 1 m or more of headroom over the ground, the
rule the core's wetness uses), over a kerb top, a stair, a bridge deck or the rail tracks, within
0.3 m of a building, lot, fixture or prop footprint, or over another puddle. The choices SHALL
come from a seeded stream of their own, so that placing puddles moves nothing else in the level.
The city plan generator (`check_puddles`) SHALL refuse a plan that breaks any of this, naming
the puddle, and the placement test SHALL check every puddle in the built level against the
core's shelter rule.

#### Scenario: Under the Skyway
- **WHEN** a puddle would lie on the road under the Skyway's deck
- **THEN** the plan places none there, and a puddle forced there is refused, naming it and the
  deck

#### Scenario: A kerb in the rain
- **WHEN** a road runs 25 m along a kerb with nothing overhead
- **THEN** it has a gully with a round puddle, and gutter puddles along the kerb with gaps of 4 to
  9 m, none on the kerb's top

#### Scenario: The textures
- **WHEN** the texture test reads the committed asphalt and paving ORM maps
- **THEN** no texel has a roughness under 0.2

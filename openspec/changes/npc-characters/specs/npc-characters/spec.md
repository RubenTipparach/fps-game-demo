## ADDED Requirements

### Requirement: NPC bodies come from a committed generator and table
Every NPC body SHALL be built by a committed Blender script from a committed character table,
using only assets whose licence allows shipping in a closed game (CC0 or equivalent). The same
table and tool versions SHALL produce the same files.

#### Scenario: Rebuilding the characters
- **WHEN** the build script runs twice with the same table and pinned tools
- **THEN** it writes byte-identical glb files

#### Scenario: A non-CC0 asset in the table
- **WHEN** the character table names an asset outside the allowed licences
- **THEN** the build stops with the asset's name and licence

### Requirement: Every NPC shares one skeleton profile and one animation library
Every NPC body SHALL map to Godot's `SkeletonProfileHumanoid`, and every NPC SHALL play its clips
from one shared animation library, not from clips baked per character.

#### Scenario: A new character
- **WHEN** a new NPC is added to the table and built
- **THEN** it plays idle, walk, talk, aim, hit and death from the shared library with no
  per-character animation work

### Requirement: Deaths and knockouts are ragdolls that come to rest
An NPC that dies or is knocked out SHALL become a ragdoll, and the ragdoll SHALL come to rest and
stop simulating within 3 s.

#### Scenario: Shot on a step
- **WHEN** an NPC standing on a step is killed
- **THEN** the body falls with the physics, comes to rest, and is frozen 3 s later

### Requirement: NPC bodies meet their budget
Each NPC body SHALL stay within the budget in the design: triangles, materials, texture size and
bone count. A build that exceeds it SHALL fail.

#### Scenario: Too many triangles
- **WHEN** a character's body comes out over its triangle budget
- **THEN** the build fails and names the character and its triangle count

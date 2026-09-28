# npc-characters Specification

## Purpose
What the NPC bodies guarantee today: every body is generated from a committed table and pinned
CC0 packs and rebuilds byte for byte, every body plays one shared animation library through one
skeleton profile, a death or knockout is a ragdoll that freezes after its settle time, and every
body stays within its budget. Each requirement names the test or check that pins it. The design,
the measurement behind it and its history are in
`openspec/changes/archive/2026-09-28-npc-characters/`.

## Requirements

### Requirement: NPC bodies come from a committed generator and table
Every NPC body SHALL be built by a committed Blender script from a committed character table,
using only assets from the allowlisted packs in `tools/deps/character_packs.json`, each pinned
by SHA-256 and licensed CC0 or equivalent. The same table and pinned packs SHALL produce
byte-identical glb files.

Pinned by `blender -b --factory-startup --python tools/blender/build_npcs.py -- --verify` (all 22
bodies rebuild byte for byte) and by the build's own refusals (an asset outside the pinned zips,
a pack whose SHA-256 differs), recorded in `docs/validation/2026-09-28-npc-bodies.md`.

#### Scenario: Rebuilding the characters
- **WHEN** the build script runs twice with the same table and pinned packs
- **THEN** it writes byte-identical glb files

#### Scenario: An asset from outside the allowlist
- **WHEN** the character table names an asset that isn't in an allowlisted pack
- **THEN** the build stops, naming the asset and the NPC that uses it

#### Scenario: A pack that doesn't match its pin
- **WHEN** a fetched pack's SHA-256 differs from `character_packs.json`
- **THEN** the fetch stops, naming the pack, and nothing is built from it

### Requirement: Every NPC shares one skeleton profile and one animation library
Every NPC body SHALL map to Godot's `SkeletonProfileHumanoid` through a committed bone map,
and every NPC SHALL play its clips from one shared animation library, not from clips baked per
character.

Pinned by `tools/godot/gen_npc_scenes.gd`, which refuses a body without a retargeted
`GeneralSkeleton`; by `ragdoll_test.tscn`, which plays the library's `Idle` on every generated
body; by `NpcBodiesTests.Every_npc_model_has_a_generated_scene`; and by the capture
`docs/screenshots/npc_bodies/hub_02_tank_talking.png`.

#### Scenario: A new character
- **WHEN** a new NPC is added to the table and built
- **THEN** it plays idle, walk, talk, aim, hit and death from the shared library with no
  per-character animation work

### Requirement: Deaths and knockouts are ragdolls that come to rest
An NPC that dies or is knocked out SHALL become a ragdoll on the project's Jolt physics, and
the ragdoll SHALL stop simulating and freeze in its pose `ragdoll_settle_s` (3.0 s) after it
starts.

Pinned by `scenes/undercity/tests/ragdoll_test.tscn` (22 of 22 bodies off the 0.45 m step,
frozen at 3.02 s, peak 7.0-10.4 m/s) and `NpcBodiesTests.The_shipped_ragdoll_freezes_three_seconds_after_it_falls`.

#### Scenario: Shot on a step
- **WHEN** an NPC standing on a 0.45 m step is killed
- **THEN** the body falls with the physics, and 3 s later it is frozen in the pose it reached

### Requirement: NPC bodies meet their budget
Each NPC body SHALL stay within the budget in the character table: at most 16,000 triangles,
3 materials, textures of at most 1024 px (no more than 4) and 53 bones. A build that exceeds it
SHALL fail.

Pinned by the build's budget check (a 10,000-triangle budget stops it at tank, 11,994
triangles, and writes nothing) and `python3 tools/blender/npc_data.py`.

#### Scenario: Too many triangles
- **WHEN** a character's body comes out over its triangle budget
- **THEN** the build fails and names the character and its triangle count

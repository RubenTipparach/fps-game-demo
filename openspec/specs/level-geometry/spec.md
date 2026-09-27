# Level Geometry Specification

## Purpose
What every generated level's geometry guarantees today: no two surfaces z-fight, and frame
props stand proud of the openings they sit in. Each requirement here is enforced by the level
generators, which refuse to write a level that breaks it.

## Requirements

### Requirement: No coplanar overlapping faces
A level generator SHALL refuse to write a level in which two faces share a plane (within
5 mm), face the same way and overlap. Faces pressed back to back are exempt. The generator
checks, per `tools/godot/detailing.py` `assert_no_zfighting`:
- prop against wall, prop against detail, and prop against prop;
- detail against wall and detail against detail, unless the details are CSG-merged with the
  walls.

#### Scenario: A trim flush with a wall face
- **WHEN** a generator registers a baseboard whose front face is coplanar with, and overlaps,
  another trim's front face
- **THEN** it exits with "z-fighting: N coplanar overlapping face pairs" naming both, and
  writes nothing

#### Scenario: A clean level
- **WHEN** `gen_map.py`, `build_cistern.py` or `gen_level_csg.py` runs on the committed sources
- **THEN** it prints "z-fighting check: clean" and writes the level

### Requirement: Frame props have an inset clear opening
A frame prop (a door frame or archway) SHALL be placed in an opening of its `fits` size and
SHALL have a `clear` opening smaller by `REVEAL` (0.1 m) at each jamb and at the lintel, so that it
stand proud of the walls and ceiling instead of sharing their planes. The frame's boxes SHALL
be registered with the z-fighting check as props.

#### Scenario: A doorway frame in a 3.2 x 3.3 m opening
- **WHEN** the doorway frame is placed in a carved 3.2 x 3.3 m opening
- **THEN** its clear opening is 3.0 x 3.2 m and the check passes

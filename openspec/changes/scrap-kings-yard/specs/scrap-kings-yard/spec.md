# Scrap King's Yard

## Purpose

The Yard level and mission M2, Chop Job: the Scrap Kings' junkyard and chop shop, the nav core
robbery, and the Kingmaker and Ledger side objectives.

## ADDED Requirements

### Requirement: The Yard follows its layout
The level SHALL be built from `tools/levels/layouts/yard.py`, with every numbered POI at its
layout position. It SHALL have four entrances: the front gate, the fence gap, the rail gate and
the skylight or back door.

#### Scenario: The fence gap
- **WHEN** the player crouches through the gap in the south-west fence
- **THEN** they're in the car stacks behind the dog's patrol aisle, as drawn

### Requirement: M2 can be completed by social, stealth or tech without killing
Chop Job SHALL be completable with zero kills by the social route (the gate, then Crusher), the
stealth route (the fence gap to the skylight) and the tech route (the rail gate, the generator
and the back door). A force route SHALL also exist.

#### Scenario: Lights out
- **WHEN** the player hacks the generator
- **THEN** the searchlights, the gate and the gate turret go dark, and the foreman walks to the
  shed

### Requirement: The safe opens four ways
Crusher's safe SHALL open with Lockpicking 3, with the combination (from the terminal at
Hacking 3, or from Dutch), by Crusher's own hand for a "buyer" (cover 6 and [Deception 4]), or
as his reward for exposing Jax.

#### Scenario: Buying the combination
- **WHEN** the player pays Dutch 300 cr
- **THEN** the combination is a known code, and the safe prompts "Enter code"

### Requirement: Dogs ignore disguises
The robot dogs SHALL detect the player by scent within 8 m whatever they wear. EMP, the kennel
hack, noise makers and height SHALL all counter them.

#### Scenario: Up the crane
- **WHEN** the player climbs the crane with a dog below
- **THEN** the dog barks and circles but can't follow

### Requirement: Kingmaker changes who runs the Kings
Killing Crusher SHALL put Jax in charge (Kings reputation +10, Jax pays 500 cr). Exposing Jax
SHALL make Crusher open the safe (Kings reputation +30, Jax is gone). Doing neither SHALL fail
S1 quietly.

#### Scenario: Exposing Jax
- **WHEN** the player shows Crusher Jax's messages
- **THEN** Crusher opens the safe, the nav core objective can be completed without picking, and
  Jax is absent from the hub afterwards

### Requirement: Every skill is used at least twice
The level SHALL contain at least two distinct uses of each of the seven skills, as listed in the
design.

#### Scenario: Auditing the level data
- **WHEN** the level's checks, locks and devices are listed by skill
- **THEN** every skill appears at least twice

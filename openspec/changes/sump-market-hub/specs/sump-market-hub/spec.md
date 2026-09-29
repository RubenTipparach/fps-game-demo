# Sump Market Hub

## Purpose

Low Harbor, the hub the player returns to between missions: where contracts come from, what's
sold, who can be talked to, and the rules of a place that isn't a battlefield.

## ADDED Requirements

### Requirement: The hub follows its layout
The hub level SHALL be built from `tools/levels/layouts/hub.py`: six districts, its streets and
lots, and interiors for the Station, Golden Carp, the Rusty Anchor, Kessler's Pawn, Doc Vo's
Clinic, the Fish Hall, the Sanitation depot, the Kings' Garage, the Tsang Shrine, the
checkpoint and Mouse's den. Every numbered POI SHALL exist in the level at its layout position.

#### Scenario: Checking the POIs
- **WHEN** the level data export runs
- **THEN** it finds entities for POIs 1 to 29, each within 1 m of the layout position

### Requirement: Everyone in the hub can be talked to
Every NPC placed in the hub SHALL be talkable: the 13 named NPCs with authored trees, and
civilians with seeded small talk and a rumour.

#### Scenario: Talking to Officer Dace
- **WHEN** the player talks to Dace at the checkpoint with no pass
- **THEN** the choices include a 150 cr bribe, a [Persuasion 3] appeal and, once the evidence is
  held, a blackmail line

### Requirement: Each mission exit has an alternative
Each exit to a mission level SHALL have at least one alternative:
- the Drains: the storm drain and the canal outfall;
- the Yard: the checkpoint, the freight tunnel, and the jersey-block climb behind the
  checkpoint camera.

At least one way into each mission SHALL need no skill.

#### Scenario: No skills, no money
- **WHEN** a player with no Persuasion, no Hacking and 0 credits heads for the Yard
- **THEN** they can reach it by climbing past the checkpoint camera while the patrol is away

### Requirement: MerSec keeps the peace
A weapon drawn in view of MerSec in the hub SHALL draw one warning. A second offence within
60 s, or any shot fired, SHALL make MerSec hostile and call backup in 60 s.

#### Scenario: Drawing twice
- **WHEN** the player draws the Kestrel near a trooper, holsters, and draws again 20 s later
- **THEN** the trooper opens fire

### Requirement: The safehouse
The Golden Carp capsule 12 SHALL save the game on sleeping and SHALL provide a 10 x 10 stash
with no owner.

#### Scenario: Leaving the shotgun
- **WHEN** the player stores the Scattergun in the stash and later returns
- **THEN** it's still there

### Requirement: Mouse's Debt can be solved three ways
S3 SHALL be completable by paying 300 cr, by a [Persuasion 3] appeal to Dace, or by showing
evidence (the Precinct 9 bribe log or the dented badge) with [Persuasion 2].

#### Scenario: Blackmail
- **WHEN** the player holds the dented badge and has Persuasion 2
- **THEN** Dace drops the debt, and the checkpoint lets the player through without a pass

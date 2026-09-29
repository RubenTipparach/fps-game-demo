# The Drains

## Purpose

The Drains level and mission M1, Rat Trap: Drain Rats territory under the Sump, where two
sanitation workers are held hostage.

## ADDED Requirements

### Requirement: The Drains follow their layout
The level SHALL be built from `tools/levels/layouts/drains.py`, with its spaces on three levels
(-1 tunnels and halls, -2 the flooded bypass, +1 the catwalk ring and the nest). Every numbered
POI SHALL be at its layout position.

#### Scenario: The vent is where the map says
- **WHEN** the player enters the crawl vent in the break room
- **THEN** it leads over the collector and drops into the pump station behind the cage, as
  drawn

### Requirement: M1 can be completed four ways without killing
Rat Trap SHALL be completable with zero kills by each of:
- a Rat disguise;
- a parley;
- the flooded bypass;
- the crawl vent.

A force route SHALL also exist.

#### Scenario: The disguise route
- **WHEN** the player, in the full Rat outfit with Deception 1, talks past the checkpoint and
  frees the hostages with the pump room key
- **THEN** the mission completes with no combat and the Ghost and Merciful bonuses

### Requirement: Freed hostages escape on their own
Once the cage opens, the hostages SHALL walk out by the route the player came in, with no
escort. The "Get them out" objective SHALL complete when they reach that exit.

#### Scenario: Freed through the vent
- **WHEN** the player came in by the crawl vent and opens the cage
- **THEN** the hostages leave through the maintenance station and up the storm drain stairs

### Requirement: No skill gate is the only way
Every locked door, device or check in the Drains SHALL have an alternative that needs no skill.

#### Scenario: No Lockpicking at the cage
- **WHEN** the player has no Lockpicking at the cage
- **THEN** the pump room key on Mother Rat's desk, or talking her down, opens it

### Requirement: The Twitch rule
Twitch SHALL execute a hostage 8 s after he becomes Alerted unless incapacitated, at most twice.
The rule SHALL be warned of by Silk's briefing, a Twitch bark and Lug's dialog.

#### Scenario: A silent takedown
- **WHEN** the player drops from the vent and knocks Twitch out while he's Unaware
- **THEN** no hostage is harmed

### Requirement: Outcomes change the hub
The number of hostages saved SHALL set Silk's payment (800, 400 or 0 cr), Petra's attitude and
Sanitation reputation. Killing Mother Rat SHALL lower Drain Rats reputation by 40 and turn Skiv
hostile. Talking her down SHALL raise it by 10.

#### Scenario: One hostage lost
- **WHEN** the player returns with only Anil
- **THEN** Silk pays 400 cr and S2 is not offered

### Requirement: Every skill is used at least twice
The level SHALL contain at least two distinct uses of each of the seven skills, as listed in the
design.

#### Scenario: Auditing the level data
- **WHEN** the level's checks, locks and devices are listed by skill
- **THEN** every skill appears at least twice

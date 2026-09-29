# Character Progression

## Purpose

Skills, ranks, perks, skill checks, XP, levels, skill points and health: the numbers every
other Undercity system reads when it asks what the player can do.

## ADDED Requirements

### Requirement: Seven skills with five ranks
The character SHALL have seven skills (Firearms, Melee, Stealth, Hacking, Lockpicking,
Deception, Persuasion), each with ranks 0 to 5. Ranks 1 and 2 SHALL cost 1 skill point, and
ranks 3 to 5 SHALL cost 2. A rank SHALL require the previous rank.

#### Scenario: Buying rank 3
- **WHEN** a character with Lockpicking 2 and 1 skill point tries to raise Lockpicking
- **THEN** the raise is refused with the reason "needs 2 points"

#### Scenario: Skipping a rank
- **WHEN** a character with Hacking 0 tries to buy Hacking 2
- **THEN** the raise is refused

### Requirement: Each rank grants its perk
Buying a rank SHALL grant that rank's perk as defined in `data/skills.json`. Perks with a
cross-tree requirement SHALL NOT be bought until it is met: Deadeye needs Stealth 1, One-Punch
needs Stealth 2, Master of Disguise needs Stealth 2, and Kingmaker needs Deception 3.

#### Scenario: Master of Disguise without Stealth
- **WHEN** a character with Deception 2 and Stealth 1 tries to raise Deception
- **THEN** the raise is refused with the reason "needs Stealth 2"

### Requirement: Skill checks are deterministic
A skill check SHALL pass exactly when the check value (rank plus at most +1 from equipment,
capped at 6) is at least the DC. A check SHALL NOT use randomness, and its requirement SHALL
be shown before it is attempted.

#### Scenario: Meeting a DC exactly
- **WHEN** a character with Deception 3 faces a [Deception 3] choice
- **THEN** the choice is enabled and passes

#### Scenario: An item bonus
- **WHEN** a character with Persuasion 2 carries the Silver Lighter (+1 Persuasion)
- **THEN** a [Persuasion 3] choice is enabled

### Requirement: XP and levels follow the curve
Reaching the next level SHALL require 500 x the current level in XP, up to level 20. An award
that crosses several thresholds SHALL raise several levels and keep the remainder. Each level
SHALL grant 2 skill points and 10 maximum health.

#### Scenario: A large award
- **WHEN** a level 1 character with 0 XP gains 1,700 XP
- **THEN** they are level 3 with 200 XP toward level 4 and 8 skill points in total

### Requirement: A new runner starts with Deception 1
A new character SHALL start at level 1 with 100 maximum health, 4 unspent skill points,
Deception at rank 1 and every other skill at rank 0.

#### Scenario: New game
- **WHEN** a new game starts
- **THEN** the skills screen shows Deception 1 and 4 points to spend

### Requirement: Play style is paid
The XP table SHALL pay a non-lethal takedown at least double a kill. It SHALL pay each dialog
check at 25 x DC, once per choice, and each lock or hack at 20 x tier, once per device. Each
mission SHALL offer Ghost, Merciful and Smooth Operator bonuses.

#### Scenario: Retrying a lock
- **WHEN** the player stops picking a tier 2 lock halfway and then finishes it
- **THEN** 40 XP is paid once, when it opens

### Requirement: Neural chips add points
Using a neural chip SHALL add 1 skill point and consume the chip.

#### Scenario: Using a chip
- **WHEN** the player uses a neural chip from the inventory
- **THEN** unspent skill points rise by 1 and the chip is gone

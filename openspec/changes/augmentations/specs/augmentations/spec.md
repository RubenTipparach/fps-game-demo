# Augmentations

## Purpose

Active powers paid for in energy: slots, installing, toggling, and the two starter augs, Echo
Lens and Mimic.

## ADDED Requirements

### Requirement: Energy regenerates only to a floor
The runner SHALL have 100 maximum energy. Energy SHALL regenerate at 1 per second, starting 5 s
after the last use, only up to 25 % of maximum. A biocell SHALL restore 40.

#### Scenario: Running dry
- **WHEN** energy is 0 and no aug is on for 60 s
- **THEN** energy is 25

### Requirement: One aug per slot
Each slot (CRANIAL, EYES, ARMS) SHALL hold at most one aug. Installing into a full slot SHALL
replace the old aug.

#### Scenario: Replacing an aug
- **WHEN** an EYES aug is installed while Echo Lens is installed
- **THEN** Echo Lens is gone and the new aug is in the EYES slot

### Requirement: Echo Lens shows awareness through walls
While on, Echo Lens SHALL show the awareness state and vision cone of every NPC within 15 m,
through walls, and SHALL cost 3 energy per second. It SHALL switch off at 0 energy.

#### Scenario: A patrol behind a wall
- **WHEN** Echo Lens is on and a MerSec trooper walks 10 m away behind a wall
- **THEN** the trooper's cone and awareness icon are drawn through the wall

### Requirement: Mimic adds one Cover in conversation
While Mimic is installed and the player has at least 20 energy, a conversation in disguise SHALL
use Cover + 1, computed by the disguise rule. It SHALL cost 20 energy at the start of the
conversation.

#### Scenario: Mother Rat at Cover 4
- **WHEN** a player with Cover 4 and Mimic talks to Mother Rat (I 4, Cover 5 needed to be
  believed) with 60 energy
- **THEN** the conversation runs at Cover 5 and energy drops to 40

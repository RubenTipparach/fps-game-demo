# Dialog and Social

## Purpose

Conversations as a way through the game: data-driven trees with visible deterministic checks,
talking to hostiles in disguise or under parley, factions and reputation, and barks.

## ADDED Requirements

### Requirement: Dialog trees are data
Dialog SHALL be defined in `data/dialog/<tree>.json` as nodes with lines, choices, conditions,
checks and effects. A validation test SHALL fail if a link doesn't resolve, an id is unknown,
a node can't reach an exit, or a check lacks a pass or a fail.

#### Scenario: A broken link
- **WHEN** a choice's `next` names a node that doesn't exist
- **THEN** the validation test fails naming the tree, the node and the choice

### Requirement: Story conditions hide, build conditions show
A choice whose unmet condition is a story condition (flag, item, quest, objective, NPC status,
parley) SHALL be hidden. A choice whose unmet condition is a build condition (skill minimum,
credits, reputation) SHALL be shown disabled, with its requirement text.

#### Scenario: Not enough credits
- **WHEN** the player has 150 credits at a "[Give 200 cr]" choice
- **THEN** the choice is shown greyed, with "[200 cr]"

#### Scenario: An unknown secret
- **WHEN** the player hasn't read the incident log
- **THEN** the choice that quotes the Rats' password isn't shown

### Requirement: Checks are visible and deterministic
A skill check SHALL pass when the check value is at least the DC, and a cover check when Cover
is at least the number. The requirement SHALL be shown on the choice. Passing SHALL pay 25 x DC
XP once per choice.

#### Scenario: Passing a lie
- **WHEN** a player with Deception 2 picks "[Deception 2] Mother says let them go"
- **THEN** the pass node runs and 50 XP is paid

### Requirement: Every hub NPC can be talked to
Every NPC placed in the hub SHALL have a dialog tree: named characters an authored tree,
civilians a seeded small-talk pool with at least one rumour.

#### Scenario: A passer-by
- **WHEN** the player talks to a civilian in the Sump Market
- **THEN** they hear small talk and a rumour, the same ones on every load of that save

### Requirement: Hostiles can be talked to in disguise
A faction member in their own territory SHALL accept conversation only when the disguise
verdict at talking range is Accepted, or when a parley with that faction is in force. If the
judgement fails, the tree's blown start SHALL run.

#### Scenario: A good disguise on a grunt
- **WHEN** the player wears the Rat jacket and respirator (Q 3) with Deception 1 and talks to a
  Rat gunner (I 2)
- **THEN** the conversation starts normally

#### Scenario: Not good enough for Mother Rat
- **WHEN** the player wears only the Rat jacket (Q 2) with Deception 1 (Cover 3) and talks to
  Mother Rat (I 4)
- **THEN** she opens with "You ain't one of ours!" and the nest turns hostile

### Requirement: Parley makes a faction neutral while weapons are holstered
A parley SHALL make its faction treat the player as neutral in their territory while no weapon
is drawn. Drawing a weapon or attacking SHALL end it.

#### Scenario: Walking in under parley
- **WHEN** Skiv has arranged a parley and the player walks into the Rat camp unarmed
- **THEN** Rats bark but do not attack, and Mother Rat will talk

### Requirement: Reputation has stances
Each faction SHALL have a reputation from -100 to 100 with stances Hated (<= -50), Disliked
(-49 to -10), Neutral (-9 to 24), Liked (25 to 59) and Trusted (>= 60). Prices SHALL use x1.1
at Disliked and x0.9 at Liked. Hated SHALL make the faction hostile in the hub too.

#### Scenario: Killing Mother Rat
- **WHEN** the player kills Mother Rat with Drain Rats reputation at -20
- **THEN** it drops to -60 and Skiv attacks the player in the hub

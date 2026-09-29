# Combat and Enemies

## Purpose

Weapons, damage and resistances, non-lethal rules, takedowns and the enemy archetypes, each
with weaknesses the player can learn and exploit.

## ADDED Requirements

### Requirement: Stun, tranq and gas are non-lethal
Stun damage SHALL fill a stun pool equal to maximum health and knock the target out when full,
without reducing health. Tranq SHALL put the target to sleep 4 s after the hit, or 8 s if the
target is Alerted. Gas SHALL knock out anyone in the cloud for 3 s who has no respirator or
filter mask.

#### Scenario: Gas on Rats
- **WHEN** a knockout gas grenade lands among three Rat gunners wearing respirators
- **THEN** none of them is knocked out

### Requirement: EMP disables machines
EMP SHALL disable robot dogs for 20 s, turrets for 30 s and cameras for 60 s. It SHALL stagger
exo-arms for 8 s with their armour at 0. It SHALL do no damage to people.

#### Scenario: The Bruiser
- **WHEN** an EMP grenade catches the Bruiser
- **THEN** for 8 s he is staggered and takes full ballistic damage

### Requirement: Takedowns from behind
A takedown SHALL be available within 1.4 m, within 60 degrees of the target's back, on an
Unaware or Suspicious target. It is not available on robots, nor on heavies without Heavy
Hitter. A knock-out SHALL take 1.5 s and make 6 m of noise, and a kill 0.8 s and 4 m, before
perks.

#### Scenario: Behind Hatchet at Melee 2
- **WHEN** the player is behind the Unaware Hatchet with Melee 2
- **THEN** no takedown is offered

### Requirement: Every archetype has counters beyond damage
Each archetype in `data/enemies.json` SHALL list at least two counters that are not raw damage,
and at least one non-lethal answer. Each counter SHALL be hinted in the world before the level
that first requires it.

#### Scenario: Validating the roster
- **WHEN** the data validation test reads the archetypes
- **THEN** each has two or more non-damage counters and a non-lethal answer, or the test fails

### Requirement: Twitch executes a hostage on alarm
Twitch SHALL execute one hostage 8 s after he becomes Alerted, unless he is incapacitated
first. He SHALL NOT do so while Suspicious.

#### Scenario: A gunfight in the camp
- **WHEN** a gunfight in the Rat camp alerts Twitch and he is still standing 8 s later
- **THEN** one hostage dies and the M1 objective updates

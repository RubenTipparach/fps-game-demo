# Combat and Enemies

## Purpose

Weapons, damage and resistances, non-lethal rules, takedowns and the enemy archetypes, each
with weaknesses the player can learn and exploit.

## ADDED Requirements

### Requirement: Damage uses zones and capped resistances
Damage SHALL be base x hit-zone multiplier x (1 - resistance for its type). The zone multiplier
is head 2.0 (3.0 with Headhunter), torso 1.0 and limbs 0.7. Resistance SHALL be capped at 75 %
for NPCs and 60 % for the player.

#### Scenario: A headshot on a Rat gunner
- **WHEN** a Kestrel round (22) hits a Rat gunner (ballistic 10 %) in the head, without Headhunter
- **THEN** it deals 39.6 damage

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

### Requirement: Health regenerates only to a 25 % floor
The player's health SHALL regenerate at 2 per second, starting 5 s after the last damage, up to
25 % of maximum health and no further. Above 25 %, health SHALL be restored only by
consumables and healers.

#### Scenario: Waiting it out when badly hurt
- **WHEN** a player with 100 maximum health drops to 10 and takes no damage for 20 s
- **THEN** health is 25

#### Scenario: Waiting it out when lightly hurt
- **WHEN** the player at 40 of 100 health waits 60 s
- **THEN** health is still 40

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

### Requirement: Everyone can be shot
Every NPC, including civilians, vendors and quest givers, SHALL have health and hit zones, and
SHALL take damage by the same damage rule as enemies (owner, 2026-09-27: "any npc can be shot").

#### Scenario: Shooting a vendor
- **WHEN** the runner shoots Kessler in his shop
- **THEN** Kessler takes damage by the damage rule, and the shot is a crime to any witness

### Requirement: Those who can defend themselves do
Each NPC SHALL have a defence in `data/npcs.json`: `fight`, `flee`, `cower` or `surrender`. An NPC
with a weapon SHALL fight when attacked; one without SHALL flee, cower or surrender as its data
says.

#### Scenario: A gun drawn on the bar
- **WHEN** the runner shoots at Tank in the Rusty Anchor
- **THEN** Tank fights back with his baton
- **AND** the civilians in the bar flee or cower, each as its data says

### Requirement: A dead quest giver fails their quests
Killing an NPC SHALL fail every active or unstarted quest they give, SHALL close their vendor,
and the journal SHALL say why.

#### Scenario: Silk dies before paying
- **WHEN** Silk is killed while M1 is active
- **THEN** M1 fails, the journal names her death as the reason, and her dialog is gone

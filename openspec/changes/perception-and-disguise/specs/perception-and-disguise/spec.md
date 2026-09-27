# Perception and Disguise

## Purpose

How non-player characters notice the player (sight, hearing, bodies, alarms, cameras, scent)
and how a disguise changes what they see.

## ADDED Requirements

### Requirement: Visibility fills a detection meter
Each observer SHALL keep a detection value D from 0 to 1 for the player. While the player is in
its cone with line of sight, D SHALL rise at `V x 1.2 x (1 - distance / range) x cone_factor`
per second, where V = light x stance x motion x perks and cone_factor is 1 in the near cone and
0.4 in the far cone. D SHALL fall at 0.25 per second otherwise.

#### Scenario: Crouched in the dark
- **WHEN** the player is crouched (0.6) and still (0.6) at light 0.2 with Shadow, 10 m from a
  Rat gunner (range 22 m) in the near cone
- **THEN** D rises at 0.2 x 0.6 x 0.6 x 0.5 x 1.2 x (1 - 10/22), about 0.024 per second

### Requirement: Awareness states
An observer SHALL be Unaware, Suspicious, Alerted, Searching or Wary, with the transitions and
timers of the design:
- Suspicious at D >= 0.3 or a non-combat noise;
- Alerted at D = 1, a combat noise, a body or the alarm;
- Searching after 3 s without sight while Alerted, for 30 s (15 s with Vanish);
- Wary for 120 s after Suspicious or Searching ends.

#### Scenario: Losing a pursuer
- **WHEN** an Alerted guard loses sight of the player for 3 s
- **THEN** the guard walks to the last known position and searches for 30 s, then turns Wary

### Requirement: Noises have radii
Every player action and weapon SHALL emit a noise with the radius in `data/perception.json`.
Observers within the radius SHALL become Alerted for combat noises (weapons fire, explosions,
screams, body drops) and Suspicious for anything else.

#### Scenario: A suppressed shot
- **WHEN** the player fires the Whisper 10mm with a guard 7 m away out of sight
- **THEN** the guard hears nothing (radius 5 m)

### Requirement: Bodies and alarms
An observer that sees an unconscious or dead body SHALL become Alerted and raise the level
alarm. A level alarm SHALL put every member of that faction in the level zone into Searching
for 120 s and then Wary.

#### Scenario: A body in the collector
- **WHEN** the patrolling Rat scavenger walks past a knocked-out Rat left on the walkway
- **THEN** he is Alerted and the Drains alarm is raised

### Requirement: A disguise needs the outfit and Deception
A disguise for faction F SHALL require a worn BODY piece of faction F and Deception of at least
1. Quality Q SHALL be 2 for the BODY piece plus 1 each for HEAD and FACE pieces of faction F.
Cover SHALL be the Deception rank plus Q.

#### Scenario: Goggles alone
- **WHEN** the player wears Rat goggles and a street jacket
- **THEN** Rats treat the player as undisguised

### Requirement: Smarter observers need more Cover
Inside an observer's scrutiny range of (2 + 2 x I) m (halved with Doppelganger), and always
when talking, an observer of intelligence I SHALL accept the disguise only if Cover >= I;
otherwise the disguise SHALL be blown. Outside that range, a matching disguise SHALL be
accepted unless a suspicious state or act applies.

#### Scenario: Mother Rat up close
- **WHEN** the player with Deception 1 wears the Rat jacket only (Cover 3) and walks within 10 m
  of Mother Rat (I 4, scrutiny 10 m)
- **THEN** the disguise is blown and she attacks

#### Scenario: Mother Rat from the catwalk
- **WHEN** the same player is 16 m from her
- **THEN** she accepts the disguise

#### Scenario: A full outfit
- **WHEN** the player with Deception 1 wears the Rat jacket, goggles and respirator (Cover 5)
- **THEN** Mother Rat accepts the disguise even while talking

### Requirement: Suspicious acts blow a disguise
A disguised player SHALL be blown when seen by that faction doing any of these:
- holding a drawn weapon past the grace (0 s, 2 s with Master of Disguise);
- attacking;
- picking or hacking the faction's locks or devices;
- searching the faction's containers;
- carrying a body;
- staying in a restricted zone past its 3 s warning;
- changing clothes.

Foreign armour, and sprinting or crouching within scrutiny range, SHALL make the verdict
Suspicious.

#### Scenario: Drawing a pistol at the checkpoint
- **WHEN** a disguised player draws the Kestrel in view of the Rat checkpoint without Master of
  Disguise
- **THEN** the disguise is blown immediately

### Requirement: Some observers can't be fooled
Robot dogs, cameras, turrets, any NPC that has fought the player this mission, and any NPC
that saw the player change clothes SHALL ignore disguises.

#### Scenario: A dog in the car stacks
- **WHEN** a robot dog comes within 8 m of the player wearing a full Scrap Kings outfit
- **THEN** it detects the player by scent and attacks

### Requirement: The HUD shows what the AI uses
The detection arcs, awareness icons and disguise chip SHALL be computed from the same D values
and the same `Judge` results the AI uses.

#### Scenario: The chip turns red
- **WHEN** an I 4 observer inside scrutiny range looks at a player with Cover 3
- **THEN** the disguise chip shows "vs I 4" in red

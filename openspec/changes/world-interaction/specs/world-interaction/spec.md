# World Interaction

## Purpose

How the player uses the world: the use key, locks, hacking, terminals, containers, security
devices, level travel, and what each level remembers.

## ADDED Requirements

### Requirement: One use key, one rule per object
The use key SHALL target the nearest interactable within 2.4 m under the crosshair. The prompt,
the hold time, whether it's blocked, and the outcome SHALL come from the same core rule.
Releasing the key, taking damage or a detection state change SHALL cancel a hold without
consuming anything.

#### Scenario: Cancelling a pick
- **WHEN** the player releases use halfway through picking a tier 2 lock
- **THEN** the lock stays locked and no lockpick is consumed

### Requirement: Locks open four ways in a fixed order
A lock SHALL try, in order:
- its key;
- a known code;
- picking (Lockpicking >= tier, with a lockpick);
- hacking (Hacking >= tier, with a multitool).

It SHALL use the first that is possible. Picking SHALL take 1.0 s x tier and hacking
1.5 s x tier, before perk modifiers. A lockpick or multitool SHALL be consumed only when the
lock opens, except at rank 5 of the matching skill.

#### Scenario: A key beats a pick
- **WHEN** the player has the pump room key and Lockpicking 2 at the tier 2 cage
- **THEN** the prompt reads "Unlock cage (pump room key)" and opens instantly, using no lockpick

#### Scenario: Nothing works
- **WHEN** the player has Lockpicking 1 and no key at a tier 2 door
- **THEN** the prompt reads "Locked: needs the key, or Lockpicking 2" and use does nothing

### Requirement: Devices can be hacked, and have counters besides hacking
Cameras, turrets, alarm panels, kennels, generators and sluices SHALL expose their hacked
options at their hack tier. Each SHALL also have at least one counter that needs no Hacking:
EMP, power, cutting a wire, noise, or line of sight.

#### Scenario: Looping a camera
- **WHEN** the player hacks a tier 1 camera and chooses Loop
- **THEN** the camera reports nothing for 60 s and then resumes

#### Scenario: Turning a turret
- **WHEN** a player with Hacking 3 hacks the Yard's gate turret
- **THEN** they can set it to target Scrap Kings

### Requirement: Codes are flags
A code or password learned from a terminal, a note or dialog SHALL be stored as a flag. Once
known, it SHALL be offered as the Code way on every lock that accepts it, and listed in the
Notes tab.

#### Scenario: Reading the safe combination
- **WHEN** the player reads Crusher's terminal
- **THEN** Crusher's safe prompts "Enter code (hold 1.0 s)"

### Requirement: Containers have fixed contents and owners
A container's contents SHALL come from level data with no random rolls. Items taken from a
container with an owner faction SHALL be marked stolen by that owner. Searching SHALL take
what fits and leave the rest.

#### Scenario: A full pack at a locker
- **WHEN** the player searches a locker holding a 2 x 2 jacket with only 1 x 1 space free
- **THEN** the jacket stays in the locker and the prompt says so

### Requirement: Levels remember what happened
Each level SHALL persist, by stable id:
- taken items and emptied containers;
- opened locks and door states;
- dead and unconscious NPCs;
- device states.

It SHALL apply them before the first frame after loading.

#### Scenario: Coming back to the Drains
- **WHEN** the player knocks out Twitch, returns to the hub and goes back down
- **THEN** Twitch is still unconscious where he fell

### Requirement: Exits travel and save
A level exit SHALL name a target level and spawn, SHALL check its condition if it has one, and
SHALL save the game before loading the target.

#### Scenario: The storm drain
- **WHEN** the player uses the storm drain in the Pit
- **THEN** the game saves and the Drains load at the storm drain stairs

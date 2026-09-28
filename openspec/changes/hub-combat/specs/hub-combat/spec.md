## ADDED Requirements

### Requirement: The Kestrel fires from the pack's ammunition
A drawn weapon SHALL fire through the one weapon system with the numbers in `data/weapons.json`.
Its magazine SHALL hold the rounds loaded, and a reload SHALL take the rounds it needs from the
pack's ammunition stacks, whole or not at all. The HUD SHALL show the rounds loaded and the
rounds left in the pack.

#### Scenario: Emptying and reloading
- **WHEN** the runner fires all 12 rounds of a loaded Kestrel with 24 `ammo_10mm` in the pack and
  reloads
- **THEN** the magazine holds 12, the pack holds 12, and the HUD reads "12 / 12"

#### Scenario: A reload with too few rounds
- **WHEN** the runner reloads an empty Kestrel with 5 rounds in the pack
- **THEN** the magazine holds 5 and the pack holds none

### Requirement: Damage uses zones and capped resistances
Damage SHALL be base x hit-zone multiplier x (1 - resistance for its type). The zone multiplier
is head 2.0 (3.0 with Headhunter), torso 1.0 and limbs 0.7, the zone taken from the height of
the hit on the body's capsule. Resistance SHALL be capped at 75 % for NPCs and 60 % for the
player.

#### Scenario: A headshot on a MerSec trooper
- **WHEN** a Kestrel round (22) hits a MerSec trooper (ballistic 35 %) in the head, without
  Headhunter
- **THEN** it deals 28.6 damage

### Requirement: Everyone can be shot
Every NPC, including civilians, vendors and quest givers, SHALL have health and hit zones, and
SHALL take damage by the same damage rule as enemies (owner, 2026-09-27: "any npc can be shot").
An NPC's death SHALL be recorded under its stable id and SHALL collapse its body into its
ragdoll.

#### Scenario: Shooting a vendor
- **WHEN** the runner shoots Kessler in his shop
- **THEN** Kessler takes damage by the damage rule, and the shot is a crime to any witness

#### Scenario: A civilian dies
- **WHEN** a civilian is killed and the game is saved and loaded
- **THEN** that civilian is dead after the load, and every other civilian is alive

### Requirement: Those who can defend themselves do
Each NPC SHALL have a defence in `data/npcs.json`: `fight`, `flee`, `cower` or `surrender`. An NPC
with a weapon SHALL fight when attacked or when its faction turns hostile; one without SHALL
flee, cower or surrender as its data says.

#### Scenario: A gun drawn on the bar
- **WHEN** the runner shoots at Tank in the Rusty Anchor
- **THEN** Tank fights back with his baton
- **AND** the civilians in the bar flee or cower, each as its data says

### Requirement: Gunfire is a crime
A shot SHALL be heard by every NPC within the weapon's noise radius. A MerSec trooper who hears
one SHALL make MerSec hostile without a warning. Hurting a member of a faction SHALL cost 15
reputation with it, and killing one SHALL cost 50.

#### Scenario: A shot in the market
- **WHEN** the runner fires the Kestrel 15 m from a MerSec patrol
- **THEN** MerSec turn hostile at once, and every civilian within 20 m flees or cowers

### Requirement: A dead quest giver fails their quests
Killing an NPC SHALL fail every active or unstarted quest they give, SHALL close their vendor,
and the journal SHALL say why.

#### Scenario: Silk dies before paying
- **WHEN** Silk is killed while M1 is active
- **THEN** M1 fails, the journal names her death as the reason, and her dialog is gone

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

### Requirement: Death loads the newest save
When the player's health reaches 0, the screen SHALL fade to black, the feed SHALL say
"You died.", and the newest save SHALL load; with no save, the title screen SHALL open.

#### Scenario: Shot down after a quicksave
- **WHEN** the runner quicksaves, then dies to MerSec fire
- **THEN** the quicksave loads

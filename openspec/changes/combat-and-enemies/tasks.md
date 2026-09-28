# Tasks

## 1. Data

- [ ] 1.1 The other weapons in `data/weapons.json` (`hub-combat` creates it with the Kestrel) and `data/enemies.json` (archetypes: HP, resistances, I, senses, loadout, quirks, immunities).

## 2. Core

- [ ] 2.1 Extend `Damage.Resolve` (zones, resistances and caps come from `hub-combat`): stun pool, tranq timer, gas, EMP.
- [ ] 2.2 `Takedown.Available(attacker, target)` and its prompt; durations and noise from data and perks.
- [ ] 2.3 Archetype quirks as small behaviour components (flee, execute hostage, charge, repair, radio).
- [ ] 2.4 Knockout consequences (defences, deaths, crime and failed quests moved to `hub-combat`).

## 3. Tests

- [ ] 3.1 Damage table cases, including Headhunter, caps, EMP on the Bruiser, gas and respirators.
- [ ] 3.2 Takedown eligibility (angle, state, heavy, One-Punch).
- [ ] 3.3 Twitch's execution timer starts on Alerted, not on Suspicious.
- [ ] 3.4 Knockouts: an unconscious NPC wakes after 120 s unless moved (defence and death tests moved to `hub-combat`).

## 4. Godot

- [ ] 4.1 Bodies from `npc-characters`: generated humans, a shared animation library (idle, walk, run, crouch, aim, fire, hit, KO, death, talk, sit, cower, hands up), ragdolls.
- [ ] 4.2 Weapon scenes for the six player weapons after the Kestrel (`hub-combat` builds the adapter and the Kestrel).
- [ ] 4.3 Video: each archetype's two non-shooting counters, one shot each.

## 5. Performance

- [ ] 5.1 Frame time with 10 and 30 NPC bodies (npc-characters: 10-16k triangles, skinned) on
  screen, measured on a GPU in an exported release build, with and without import LODs
  (CLAUDE.md 9). Moved here from npc-characters task 5.2.

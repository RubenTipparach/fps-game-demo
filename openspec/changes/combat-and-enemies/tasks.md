# Tasks

## 1. Data

- [ ] 1.1 `data/weapons.json` (player and NPC weapons) and `data/enemies.json` (archetypes: HP, resistances, I, senses, loadout, quirks, immunities).

## 2. Core

- [ ] 2.1 `Damage.Resolve(hit, target)`: zones, resistances, caps, stun pool, tranq timer, gas, EMP.
- [ ] 2.2 `Takedown.Available(attacker, target)` and its prompt; durations and noise from data and perks.
- [ ] 2.3 Archetype quirks as small behaviour components (flee, execute hostage, charge, repair, radio).
- [ ] 2.4 Defences for everyone: `defence` and `weapon` in `data/npcs.json`; fight, flee, cower, surrender; death and knockout consequences (quests fail, vendors close, crime).

## 3. Tests

- [ ] 3.1 Damage table cases, including Headhunter, caps, EMP on the Bruiser, gas and respirators.
- [ ] 3.2 Takedown eligibility (angle, state, heavy, One-Punch).
- [ ] 3.3 Twitch's execution timer starts on Alerted, not on Suspicious.
- [ ] 3.4 Every NPC in the data has a defence; armed ones fight; a dead giver fails their quests and closes their shop.

## 4. Godot

- [ ] 4.1 Bodies from `npc-characters`: generated humans, a shared animation library (idle, walk, run, crouch, aim, fire, hit, KO, death, talk, sit, cower, hands up), ragdolls.
- [ ] 4.2 NPC adapter using the core; weapon adapters for the seven player weapons.
- [ ] 4.3 Video: each archetype's two non-shooting counters, one shot each.

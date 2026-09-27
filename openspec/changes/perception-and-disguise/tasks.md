# Tasks

## 1. Data

- [ ] 1.1 `data/perception.json`: cones, ranges, rates, state timers, noise radii, alarm timings.
- [ ] 1.2 `data/enemies.json` perception fields per archetype (I, cone, range, senses, alarm ability).

## 2. Core

- [ ] 2.1 `Visibility.Compute(light, stance, motion, perks)`.
- [ ] 2.2 `Awareness` state machine per NPC with D, timers, last known position and memory.
- [ ] 2.3 `NoiseEvent` and hearing; combat versus curiosity noises.
- [ ] 2.4 `LevelAlarm`: raise, propagate, expire.
- [ ] 2.5 `DisguiseRules`: Q, Cover, S(I), `Judge`, suspicious acts, restricted zones, Fast Talk.

## 3. Tests

- [ ] 3.1 Detection fill and drain rates against a table of cases.
- [ ] 3.2 State transitions and timers, including Vanish and Wary.
- [ ] 3.3 The intelligence table: for each I, the cheapest Cover that passes, and one that fails.
- [ ] 3.4 Unfoolable observers ignore disguises.
- [ ] 3.5 Deception 0 disables disguises; a disguise needs the BODY piece.

## 4. Godot

- [ ] 4.1 Light probe sampling at the player from the baked lightmap probes.
- [ ] 4.2 NPC adapter: vision raycasts, hearing, barks, animation of the states.
- [ ] 4.3 HUD: detection arcs, awareness icons, disguise chip, alarm bar (after mockup approval).
- [ ] 4.4 Video: a Rat gunner going Unaware, Suspicious, Searching and Wary; a disguise accepted at 10 m and blown at 3 m by Mother Rat.

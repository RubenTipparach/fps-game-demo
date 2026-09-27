# Proposal: how enemies notice you, and how a disguise fools them

## Why

"If you find a good disguise you can also talk to hostile dudes too, but you would need a
higher skill to fool more intelligent enemies" (owner, 2026-09-27). Disguise only means
something if perception is exact: who sees you, how fast they notice, what makes them look
twice, and what gives you away. The same rules drive stealth without a disguise, so they are
designed together.

## What Changes

- **Sight.** A two-zone vision cone per archetype. Visibility comes from light, stance, motion
  and gear, and fills a detection meter at a rate that falls with distance.
- **Awareness states.** Unaware, Suspicious, Searching, Alerted (combat) and Wary, with
  timers, investigation and memory.
- **Hearing.** Every action emits a noise with a radius from `data/perception.json`.
- **Other senses.** Bodies (a found body raises the alarm), a level alarm that spreads by
  radio, cameras, and robot dog scent.
- **Disguise.**
  - A disguise needs the faction's outfit (BODY).
  - Quality Q = BODY 2 + HEAD 1 + FACE 1 in matching gear.
  - Cover = Deception + Q.
  - Each observer has an intelligence I (1 to 5) and a scrutiny range of 2 + 2I m. Inside it,
    or when talking, they accept you only if Cover >= I.
  - Suspicious acts, restricted zones, foreign armour and drawn weapons break or strain a
    disguise.
- **What can't be fooled.** Robot dogs (scent), cameras and turrets (sensors), anyone who has
  fought you, and anyone who has seen you change clothes.
- **HUD readouts.** Detection arcs around the crosshair (Human Revolution style), an awareness
  icon over each NPC, and a disguise chip showing faction, Q and Cover.

## Capabilities

### New Capabilities
- `perception-and-disguise`: sight, hearing, awareness states, alarms, bodies, cameras, scent,
  the disguise verdict and its readouts.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Perception`, `Undercity.Core/Disguise`, `data/perception.json`, the
  intelligence and senses fields in `data/enemies.json`.
- Brushfire's `Enemy.cs` perception (a sight cone and hearing) stays for the reference maps.
  Undercity NPCs use the core rules through an adapter.
- The level bake exports light probes that the core samples for the player's light level.

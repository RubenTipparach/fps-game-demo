# Proposal: weapons, damage, takedowns and enemies you outsmart

## Why

The owner wants "various enemies they have to out smart with technical combat". An enemy you
outsmart has a weakness the player can learn and a tool that exploits it:
- Rats wear respirators, so gas doesn't work on them;
- robot dogs smell you through any disguise, so EMP them or lure them;
- the Bruiser's exo-arm shrugs off bullets until an EMP drops it.

Combat has to be possible and costly, and non-lethal has to be a full path.

## What Changes

- **Damage types.** Ballistic, blunt, shock, explosive, EMP, gas and tranq, with per-archetype
  resistances and immunities.
- **Hit zones.** Head x2 (x3 with Headhunter), torso x1, limbs x0.7.
- **Health.** Regenerates only up to 25 % (owner B1); above that, medkits, stims, food and
  Doc Vo.
- **Non-lethal.** Stun damage fills a stun pool equal to health. A full pool is a KO. Tranq darts
  sleep a target in 4 s (8 s if Alerted). Gas knocks out in 3 s.
- **Takedowns.** From behind, on an Unaware or Suspicious target: non-lethal (1.5 s, noise 6 m)
  or lethal (0.8 s, noise 4 m). Heavies need Melee 4.
- **Thirteen archetypes** for the slice, each with health, armour, intelligence, senses,
  loadout, a behaviour quirk and at least two counters that aren't "shoot it more".
- **Seven player weapons and four grenade types** with data-defined damage, rate, magazine,
  spread, recoil and noise.

## Capabilities

### New Capabilities
- `combat-and-enemies`: damage and resistances, hit zones, health, non-lethal rules,
  takedowns, weapons and the enemy archetypes.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Combat`, `data/weapons.json`, `data/enemies.json`.
- Brushfire's weapon and enemy code stays for the reference maps. Undercity NPCs use the core
  through `npc.tscn` and humanoid models from `tools/blender/build_characters.py`.

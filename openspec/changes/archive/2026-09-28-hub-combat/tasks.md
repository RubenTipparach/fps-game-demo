# Tasks

## 1. Data

- [x] 1.1 `data/weapons.json` (the Kestrel, the service pistol, the baton, the scattergun),
  `data/combat.json` (zones, caps, hit chance, flee and cower numbers), and `health`, `resist`,
  `defence`, `weapon` in `data/npcs.json` with the `civilian` profile. Loaders, validation and
  cross-checks (item weapon ids, NPC weapon ids).

## 2. Core

- [x] 2.1 `Combat/CombatRules.cs`: the damage rule with zones, resistances and caps, the zone
  bands, the NPCs' hit chance and a civilian's defence; `GameState.HurtNpc` and `TakeHit` apply
  it. The stun pool, tranq, gas and EMP stay in `combat-and-enemies`.
- [x] 2.2 `Kit/Magazine.cs`: loaded rounds per weapon, reload from the pack (whole or not at
  all), saved.
- [x] 2.3 NPC health, damage and death in `WorldState`, keyed by `Combat.NpcTarget` (a named
  NPC's id, a civilian's stable id): the core half of the civilian status fix, with its
  regression test. The Godot half (`NpcActor` using the same key) is 4.3.
- [x] 2.4 `Law.ShotFired`, faction reputation for assault and murder, quests failed and shops
  closed by a death.
- [x] 2.5 The player's health: damage, armour, the 25 % floor (`FloorPool`), death.

## 3. Tests

- [x] 3.1 The damage scenarios, the caps, and the zone bands.
- [x] 3.2 Magazine and reload cases, including a partial reload and an empty pack.
- [x] 3.3 The law and reputation rules; a dead giver fails their quests and closes the shop.
- [x] 3.4 Every NPC in the data has health and a defence; every armed one has a weapon in
  `weapons.json`.
- [x] 3.5 The health floor scenarios.

## 4. Godot

- [x] 4.1 `IAmmoSource` in Brushfire's `WeaponManager` (the reference maps keep their own
  counts); null-safe HUD calls in `Weapon.cs` and `Projectile.cs`.
- [x] 4.2 `WeaponAdapter`: draw and holster through `GameState.LoadoutChanged`; the Kestrel
  scene configured from data; the Kestrel viewmodel (`tools/blender/build_weapons.py`, glb and
  `.blend`); shot and reload sounds.
- [x] 4.3 `NpcActor` becomes `IDamageable`; zones from the hit height; hit reactions; deaths
  pushed along the shot.
- [x] 4.4 Defences: fight (ranged, melee), flee, cower and surrender on a `NavigationAgent3D`,
  with the UAL clips listed in the design.
- [x] 4.5 The HUD's loaded / reserve readout, "RELOADING", and the hit marker on the crosshair.
- [x] 4.6 Death: fade, "You died.", load the newest save (owner I15).

## 5. Checks and captures

- [x] 5.1 Headless `combat_test.tscn`: shots on a test NPC change its health by the rule; a
  shot heard by a trooper makes MerSec hostile; a fleeing civilian ends at least 25 m away.
- [x] 5.2 Video: draw and fire in the market, the patrol's response, civilians fleeing and
  cowering, Tank with his baton, a death and a reload. Validation record.
- [x] 5.3 Archive, moving the requirements into `openspec/specs/hub-combat`.

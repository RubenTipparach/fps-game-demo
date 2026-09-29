# Proposal: the Kestrel fires, in the hub

## Why

The owner, playtesting on 2026-09-28: "I don't have a gun yet, I wish I had a gun in the main hub
to actually do stuff."

The runner does carry one: the new-game kit puts the Kestrel 10mm on belt key 2, with 24 rounds.
It is a prop, though. Measured in the code:
- **Drawing only records the choice.** `GameState.UseBelt` sets `Drawn`, and only the HUD
  listens.
- **There is no weapon to fire.** The Undercity player scene has Brushfire's `WeaponManager`
  with an empty viewmodel root, so its current weapon is null and firing is skipped.
- **There are no numbers.** No `data/weapons.json` exists, although items point at it.
- **NPCs can't be hurt.** `NpcActor` isn't `IDamageable`, so a hit would only draw an impact.
- **The law half-exists.** A drawn weapon already blows disguises and makes MerSec warn, then
  turn hostile, but a hostile trooper only turns to face you. `LawWatch.ShotFired()` exists and
  nothing calls it.
- **A bug waits for the first death.** A killed civilian's status is written under the id
  "civ", so the level still counts them as alive.

The owner answered on 2026-09-28: I1 and I2 accepted (build this second, after water; the Kestrel
fires in the hub, everyone can be shot, gunfire is a crime, MerSec fight back), and I15 accepted
(death reloads the newest save, no death screen).

The owner decided on 2026-09-27 (survey G2) that combat comes with the Drains. This change takes
the part of `combat-and-enemies` that the hub needs and lands it first. Everything that needs the
Drains' enemies stays in `combat-and-enemies`: non-lethal tools, EMP, takedowns and the
archetypes. The owner confirmed the new order (I1, I2).

## What Changes

- **The Kestrel fires.** It uses Brushfire's weapon system, configured from
  `data/weapons.json`, with a Blender-built viewmodel, a muzzle flash and a shot sound. It takes
  its reserve from the pack's `ammo_10mm`, with a 12-round magazine and a 1.4 s reload. The
  approved HUD's "12 / 36" readout comes alive.
- **Everyone can be shot.** Every NPC has health, hit zones and resistances, by the one damage
  rule: base x zone x (1 - resistance), capped. Deaths use the ragdolls that are already built.
- **Those who can defend themselves do.**
  - MerSec fight with service pistols, Tank with his baton, and Kessler with the shotgun under
    his counter.
  - Everyone else flees along the navmesh, cowers or surrenders, as their data says.
- **Gunfire is a crime.**
  - A shot heard by MerSec makes them hostile with no warning.
  - Hurting or killing someone costs reputation with their faction.
  - A dead quest giver fails their quests and closes their shop.
- **The runner can die.** Health regenerates only to 25 % (owner B1). At 0 the screen fades and
  the newest save loads (survey I15).

## Capabilities

### New Capabilities
- `hub-combat`: the first combat slice: the Kestrel, damage, everyone can be shot, defences,
  crime and death.

### Modified Capabilities
- None in `openspec/specs/`. `combat-and-enemies` (a change, not yet a spec) gives five
  requirements to this change and keeps the rest.

## Impact

- **Core:** `Combat/Damage.cs` (zones, resistances, caps), `Kit/Magazine.cs` (magazine and
  reload from the pack), NPC health and status in `WorldState`, `Law.ShotFired`, and the health
  floor and death through `Vitals`.
- **Data:**
  - `data/weapons.json` (the Kestrel, the troopers' service pistol, Tank's baton, Kessler's
    shotgun);
  - `data/npcs.json` gains `health`, `resist`, `defence` and `weapon` per NPC;
  - `data/combat.json` holds the zones, caps, accuracy and flee distances.
- **Godot:**
  - a weapon adapter from `GameState.Drawn` to `WeaponManager`, and an ammo source interface so
    Brushfire's maps keep their own ammo;
  - `NpcActor` becomes `IDamageable`, with fight, flee, cower and surrender behaviours on a
    `NavigationAgent3D`;
  - the HUD's magazine readout.
- **Brushfire maintenance:** `Weapon.cs` and `Projectile.cs` stop assuming Brushfire's HUD
  exists.
- **Art:** the Kestrel viewmodel (Blender, with its `.blend`), and a gunshot and reload sound.
- **Fix:** civilians' deaths are recorded under their stable ids.

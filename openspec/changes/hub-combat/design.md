# Design: the Kestrel fires, in the hub

## Context

What exists, measured in the code (2026-09-28):

| Piece | State |
|---|---|
| The Kestrel | In the new-game kit (`progression.json`) on belt key 2 with 24 `ammo_10mm`. Kessler sells another pistol and 120 rounds. The Whisper and 10 rounds sit in the drowned locker. |
| Drawing | `GameState.UseBelt` sets `Drawn`, and the HUD shows "KESTREL 10MM · DRAWN". Nothing creates a weapon. |
| Brushfire's weapons | `WeaponManager`, hitscan and projectile `Weapon`s, `IDamageable`, `DamageInfo`, impact effects, and noise through `Events.EmitNoise`. Ammo lives inside `WeaponManager`. `Weapon.cs:152` and `Projectile.cs:78` call `player.Hud` without a null check; Undercity has no Brushfire HUD. |
| The Undercity player | `WeaponManager` with an empty `ViewmodelRoot`, so its current weapon is null and firing is skipped. |
| NPCs | `NpcActor` is on the Enemy layer, so rays hit it, but it isn't `IDamageable`. Deaths already collapse into Jolt ragdolls that freeze after 3 s. The hub's navmesh is baked (4,770 polygons). |
| Law | A drawn weapon seen by a trooper within 25 m warns first, then turns MerSec hostile; hostile NPCs only face the runner. `LawWatch.ShotFired()` exists and nothing calls it. |
| Core | No damage rule. The health floor exists as `FloorPool`, used only by a UI fixture. `NpcStatus` has Alive, Unconscious, Dead, Hostile and Gone. |
| Bug | A killed civilian's status is written under the id "civ", and `Status` reads Alive when there's no definition, so dead civilians count as alive. |
| Animation | UAL Standard has `Pistol_Aim_*`, `Pistol_Shoot`, `Pistol_Reload`, `Jog_Fwd`, `Sprint`, `Hit_Chest`, `Hit_Head`, punches and a sword swing. It has no rifle clips. |

`combat-and-enemies` holds the full combat design and its numbers. This change builds the part
the hub needs, with those numbers, and moves five of that change's requirements here.

## Goals / Non-Goals

**Goals**
- The runner can draw, fire and reload the Kestrel anywhere in the hub.
- Every NPC can be shot and reacts as a person would.
- Shooting has consequences that the systems already understand: law, reputation, quests,
  shops.
- The runner can die, and death costs something without a new screen.

**Non-Goals**
These stay in `combat-and-enemies`:
- non-lethal tools (stun pool, tranq, gas), EMP and takedowns;
- the Drains' and the Yard's archetypes and their counters;
- the other five player weapons.

Also out: cover-seeking AI and squad tactics.

## Decisions

### 1. One weapon system, two ammo sources

Brushfire's `WeaponManager` and `Weapon` fire every gun, the reference maps' and Undercity's
alike. Nothing is copied (CLAUDE.md 5.1). Two seams make that work:
- **`IAmmoSource`.** Brushfire's reference maps keep their built-in counts. Undercity supplies
  the pack through a magazine rule in the core.
- **`WeaponAdapter`** (the Godot layer) listens to `GameState.LoadoutChanged`. On a draw it
  instantiates the weapon scene named in `data/weapons.json` under `ViewmodelRoot`; on a holster
  it removes it. Brushfire's own weapon keys do nothing in Undercity; the belt is the only way
  to draw.

### 2. The Kestrel and the hub's other weapons

The Kestrel's numbers are from `combat-and-enemies`' weapons table. The troopers' pistol uses
the Kestrel's figures at 80 % damage, since UAL has no rifle clips.

| Weapon | Who | Damage | Type | Rate | Magazine | Reload | Spread | Noise |
|---|---|---|---|---|---|---|---|---|
| Kestrel 10mm | runner | 22 | ballistic | 3/s | 12 | 1.4 s | 2° | 20 m |
| MerSec service pistol | troopers, Dace | 18 | ballistic | bursts of 3 at 3/s, 1.5 s apart | 12 | 1.6 s | 3° | 20 m |
| Baton | Tank | 18 | blunt | 1 per 1.2 s | none | none | reach 1.6 m | 4 m |
| Scattergun (under the counter) | Kessler | 9 x 8 pellets | ballistic | 1 per 0.9 s | 6 | 3.0 s | 5° | 30 m |

`data/weapons.json` holds these, keyed by the `weapon` ids that `items.json` already names, plus
the NPC-only ones. It is validated on load, and the ids are cross-checked against the items.

**The magazine** (core, `Kit/Magazine.cs`) keeps the rounds loaded in each weapon, and saves
them.
- Reload takes `min(magazine - loaded, rounds in the pack)` from the pack's stacks: whole or not
  at all, per CLAUDE.md 5.6.
- The HUD shows loaded / pack, as the approved D3 mockup draws it ("12 / 36").

### 3. Damage (moved from `combat-and-enemies`)

`damage = base x zone x (1 - resist)`, with the resistance for the damage type capped at 75 %
for NPCs and 60 % for the player. Zones: head 2.0 (3.0 with Headhunter), torso 1.0, limbs 0.7.

The zone comes from the height of the hit on the NPC's 1.8 m capsule. The ragdoll bones are
disabled while a person lives, and the capsule is what the ray hits.
- Head: at 1.52 m or higher, the top 0.28 m.
- Legs: below 0.85 m.
- Torso: everything else.

`data/combat.json` holds the bands, the multipliers and the caps.

### 4. Everyone has health and a defence

`data/npcs.json` gains `health`, `resist`, `defence` (`fight`, `flee`, `cower`, `surrender`) and
`weapon`. Civilians share one profile, `civilian`, whose defence is flee (70 %) or cower (30 %),
drawn from the world seed and their stable id, so a save and a replay agree.

| NPC | Health | Resist | Defence | Weapon |
|---|---|---|---|---|
| MerSec troopers (5), Officer Dace | 120 | ballistic 35 % | fight | service pistol |
| Tank | 150 | ballistic 15 % (his vest) | fight | baton |
| Kessler | 80 | none | fight | scattergun |
| Silk | 90 | ballistic 10 % | surrender | none |
| Skiv (Drain Rats), Jax (Scrap Kings) | 90 | none | flee | none (armed in their own levels) |
| Mags, Doc Vo, Nguyen, Rivet, Lin, the Oracle, Petra | 70 | none | cower or flee, one each | none |
| Mouse | 50 | none | flee | none |
| Civilians (31) | 60 | none | flee 70 % / cower 30 % | none |

Shots to kill (torso, head), from the rule:

| Target | Kestrel torso | Kestrel head |
|---|---|---|
| Civilian | 3 (22 each) | 2 (44 each) |
| MerSec trooper | 9 (14.3 each) | 5 (28.6 each) |
| Tank | 9 (18.7 each) | 5 (37.4 each) |

A trooper takes most of a magazine, which is the point: the design wants the runner to outsmart
MerSec, not outshoot them.

### 5. How people react

| Defence | Behaviour |
|---|---|
| fight, ranged | Keep line of sight. Close to 18 m along the navmesh, back off inside 6 m, and fire bursts (`Pistol_Aim_Neutral`, `Pistol_Shoot`). Hit chance `p = clamp(0.55 - 0.02 d - 0.15 moving - 0.10 crouched, 0.08, 0.60)` at range `d` m. |
| fight, melee | Close in and swing (`Sword_Attack`) within 1.6 m. |
| flee | Run (`Jog_Fwd`, then `Sprint`) to a navmesh point at least 25 m from the shooter, then cower. |
| cower | `undercity/Cower` until 20 s after the last shot heard. |
| surrender | `undercity/Surrender`; stays put while the runner is within 15 m. |
| hit | `Hit_Chest` or `Hit_Head` on the upper body, then carry on. |
| death | The existing collapse, pushed along the shot. The status is saved under the NPC's stable id: this fixes the civilian bug. |

NPCs get a `NavigationAgent3D` on the baked navmesh. Hit chance, flee distance and cower time
live in `data/combat.json`.

### 6. Crime and consequences

- **A shot is heard** by every NPC within the weapon's noise radius (Kestrel 20 m).
  - Troopers who hear it: `Law.ShotFired()` makes MerSec hostile at once, skipping the warning
    a drawn weapon gets. Backup is due in 60 s, as for any hostility.
  - Civilians who hear it react by their defence.
- **Hurting** someone is assault: -15 reputation with their faction. **Killing** is murder: -50,
  and the faction's members who see it turn hostile if they can fight. `factions.json` already
  holds the reputation.
- **A dead quest giver** fails their quests and closes their shop, and the journal says why
  (the moved requirement).
- **Shooting while disguised** blows the disguise (the drawn-weapon rule already does).

### 7. The runner's health and death

- The health floor (owner B1, moved here): regeneration at 2/s, from 5 s after the last hit, up
  to 25 % and no further. `Vitals.FloorPool` already implements it; this change wires it to
  damage.
- Armour: worn items' `resist_pct` (already in `items.json`) through `Inventory.ResistPct`.
- **Death** (survey I15): the screen fades to black over 1.5 s, the feed says "You died.", and
  the newest save loads (quick, auto or named; title-and-pause's `SaveStore.Newest`). With no
  save, the title screen opens. No new screen is needed; a death screen would need a mockup.

### 8. What it looks and sounds like

- **The Kestrel viewmodel:** built in Blender (`tools/blender/build_weapons.py`, the `.glb`
  and its `.blend`), within 3,000 triangles and one 1024 px material from Material Maker's
  metals.
- **Effects:** Brushfire's muzzle flash and impact effects; a new gunshot and reload sound from
  the sound generator.
- **The HUD:** the approved D3 weapon panel shows loaded / reserve and "RELOADING". Brushfire's
  hit marker goes on the Undercity crosshair: a small change within an approved design.

## Walkthrough

1. The runner draws the Kestrel (key 2) in the Sump Market. A trooper 20 m away sees it:
   "Put it away." (the existing rule).
2. They fire at a bottle on a stall. The shot is heard within 20 m. The trooper turns hostile,
   and civilians within 20 m run 25 m away and cower. Nguyen ducks behind his counter.
3. The trooper closes to 18 m and fires bursts. At 15 m, standing still, the runner is hit
   25 % of the time (0.55 - 0.02 x 15), for 18 a hit with no armour: a burst of three costs
   13.5 on average.
4. The runner takes cover, drops to 18 health, and waits. Health climbs to 25 and stops.
5. The Kestrel came loaded (12, with 24 in the pack: "12 / 24"). Twelve shots later they
   reload, and the HUD reads "12 / 12".

## Risks / Trade-offs

- **Nine torso shots per trooper may feel spongy** to a player expecting an FPS. The numbers are
  data, and the survey asks whether combat should stay "outsmart, don't outshoot" (I2).
- **Navmesh fleeing through a dense market** can bunch people at chokepoints. Flee points are
  chosen in a fan away from the shooter, and a point whose path is blocked is skipped.
- **Brushfire's code predates the rules** (CLAUDE.md 13). The two seams (`IAmmoSource` and the
  HUD null checks) are the only changes inside it.

## Open Questions

For the owner, in the survey:
- I1: the build order;
- I2: the Kestrel fires in the hub now, shooting is a crime, and MerSec fight back (this revises
  G2);
- I15: death reloads the newest save, with no death screen.

# Design: combat and enemies

## Context

Deus Ex's combat is famously the weakest pillar of the three. That's acceptable, because
combat is a fallback that costs you. Undercity keeps combat short and dangerous: enemies hit
hard, health doesn't regenerate, and the tools that avoid fights (gas, EMP, darts, takedowns)
are cheap. What makes combat "technical" is that each archetype has a known weakness.

`hub-combat` builds sections 2 (without the stun pool, tranq, gas and EMP), 4 and 7 first, in
the hub, with the numbers below (owner, 2026-09-28). This change builds the rest on top of it.

## Goals / Non-Goals

**Goals:**
- Every archetype has at least two counters besides damage, and at least one non-lethal
  answer.
- A fair fight against three Rat gunners is winnable and costs about a medkit.
- A fight against a Bruiser or Crusher without preparation is a mistake.

**Non-Goals:**
- Cover systems and leaning. Leaning is a candidate after the slice.
- Weapon mods and upgrades.
- Limb damage effects on the player (the doll displays per-part health only).

## Decisions

### 1. Player weapons (`data/weapons.json`)

| Weapon | Damage | Type | Rate | Mag | Reload | Spread | Noise | Notes |
|---|---:|---|---:|---:|---:|---:|---:|---|
| Stun baton | 35 stun | shock | 1.2/s | - | - | - | 3 m | stagger 1.5 s; non-lethal |
| Combat knife | 40 | blunt/lethal | 1.6/s | - | - | - | 2 m | |
| Kestrel 10mm | 22 | ballistic | 3/s | 12 | 1.4 s | 2.0 deg | 20 m | |
| Whisper 10mm | 18 | ballistic | 2.5/s | 10 | 1.6 s | 1.5 deg | 5 m | suppressed |
| Sandman dart pistol | 5 + tranq | tranq | 1/s | 4 | 2.0 s | 1.0 deg | 3 m | sleep in 4 s (8 s Alerted) |
| Rattler SMG | 12 | ballistic | 10/s | 30 | 2.0 s | 4.5 deg | 25 m | |
| Scattergun | 9 x 8 | ballistic | 1.1/s | 6 | 0.5 s per shell | 7 deg | 30 m | |
| Frag grenade | 120 | explosive | - | - | - | - | 35 m | 5 m radius, 1 s fuse after landing |
| EMP grenade | - | EMP | - | - | - | - | 12 m | 6 m radius |
| Knockout gas | - | gas | - | - | - | - | 6 m | 4 m cloud for 8 s; KO in 3 s |
| Noise maker | - | - | - | - | - | - | 15 m | 3 s delay; lures |

### 2. Damage, hit zones and armour

- **Damage dealt** = `base x zone x (1 - resist[type])`, with the target's resistance capped at
  75 % (60 % for the player).
- **Hit zones:** head x2.0 (x3.0 Headhunter), torso x1.0, limbs x0.7. Robots have one zone.
- **Stun.** Stun damage doesn't reduce health. It fills a stun pool equal to max health; at
  full, the target is knocked out. The pool drains 10 per second after 3 s without stun.
- **Tranq** puts a target to sleep 4 s after the hit (8 s if Alerted, when it runs and shouts
  first).
- **Gas** knocks out anyone without a respirator or filter mask after 3 s in the cloud,
  including the player.
- **EMP** does no damage to people. It disables robots 20 s, turrets 30 s and cameras 60 s,
  and staggers exo-arms 8 s (setting their armour to 0).

### 3. Takedowns

- **Conditions:** within 1.4 m, behind the target (within 60 deg of its back), and the target
  Unaware or Suspicious.
- **The prompt** offers "Knock out" (use) and "Kill" (alt use).

| Takedown | Time (Quick Hands) | Noise (Silent Takedown) | Result |
|---|---|---|---|
| Knock out | 1.5 s (0.75 s) | 6 m (0) | unconscious body |
| Kill | 0.8 s (0.4 s) | 4 m (0) | dead body |

- **Heavies** (Bruiser, Hatchet, Crusher) can't be taken down without Heavy Hitter
  (Melee 4).
- **One-Punch** (Melee 5) allows a frontal knock-out on Unaware or Suspicious targets up to I 3.
- **Robots** can't be taken down.

### 4. Health

- **Player:** max health 100 + 10 per level.
- **Regeneration floor (owner B1, 2026-09-27):** "med kits, health minimal regen is 25%".
  Health regenerates at 2 per second, starting 5 s after the last damage, but only up to 25 %
  of maximum. Above that, only medkits, food, stims and Doc Vo heal. Numbers are in
  `data/progression.json` (`regen_floor_pct`, `regen_rate_per_s`, `regen_delay_s`).
- **Healing:** medkits (+40 over 1 s), stims (+25), noodles (+10), whisky (+5), and Doc Vo
  (full, 5 cr per point).
- **Death** loads the last save (autosaves at every level transition, plus quicksave).

### 5. Archetypes (`data/enemies.json`)

| Archetype | HP | Resist | I | Loadout | Quirk | Counters that aren't shooting |
|---|---:|---|---:|---|---|---|
| Rat scavenger | 60 | - | 1 | pipe (15 blunt) | flees at 25 % HP to warn others | takedown; darts; disguise; Intimidate makes him drop his weapon |
| Rat gunner | 70 | ballistic 10 % | 2 | Kestrel or Scattergun | respirator: gas-immune | takedown; darts; disguise; the scrap turret turned on them |
| Rat lookout | 50 | - | 1-2 | flare, whistle | whistle raises the alarm in 30 m | keep out of his long cone; darts from range; noise maker to turn him |
| Twitch | 90 | ballistic 10 % | 3 | Rattler SMG | executes a hostage 8 s after Alerted | take him down silently; talk ([Deception 2] with Cover 3); bribe 200 cr |
| Hatchet | 140 | ballistic 20 %, blunt 30 % | 3 | cleaver, charges | heavy: no takedown without Melee 4 | darts (sleeps in 8 s); gas if his respirator is off (hack the nest vents, Hacking 2); avoid |
| Mother Rat | 160 | ballistic 20 % | 4 | Scattergun, gas grenades | throws gas at range (her crew is immune; the player isn't) | wear a respirator; talk (cover 5; [Deception 3], [Persuasion 3] or 500 cr); parley |
| Kings mechanic | 80 | ballistic 15 % | 2 | wrench or Rattler | repairs disabled turrets and dogs in 20 s | gas (no respirators); takedown; disguise |
| Kings foreman | 110 | ballistic 25 % | 3 | Scattergun, radio | radio raises the alarm in 2 s | take him first; EMP kills the radio 20 s; lure him with the generator |
| Bruiser | 180 | ballistic 40 % (0 while EMP'd) | 2 | exo-arm, charge 12 m | charges in a line; hits walls and staggers himself 2 s | EMP then anything; sidestep a charge into a wall; gas |
| Robot dog | 90 | ballistic 50 %, EMP x3 | - | bite 20 | scent 8 m through walls; ignores disguises; pack of 2 | EMP (20 s); noise maker lure; kennel hack keeps it docked; climb (dogs can't) |
| Gate or scrap turret | 150 | ballistic 70 % | - | 10/s, 8 dmg | 120 deg arc; activates on alarm or camera detection | hack (disable at 2, turn at 3); EMP 30 s; flank; power off (gate turret) |
| Crusher | 260 | ballistic 40 %, blunt 50 % | 5 | heavy shotgun 9 x 12, ground slam 6 m | plated arm blocks frontal fire; can't be taken down | EMP the arm (8 s, armour 0); talk (cover 6, [Deception 4] for the safe; [Persuasion 4] to expose Jax); poison his whisky (S1, the paint thinner) |
| MerSec trooper | 120 | ballistic 35 % | 2-3 | assault rifle 16 dmg, 8/s | hub police: warns once, then fights; calls backup in 60 s | don't draw weapons in the hub; bribe; disguise (after the slice) |

**Group behaviour in the slice:**
- **Alarms.** Alerted NPCs radio an alarm if they have a radio (foreman, MerSec) or a whistle
  (lookouts).
- **Positioning.** They take the nearest navmesh position with line of sight, keeping 6 to 12 m
  from the player.
- **Healers.** Mechanics revive knocked-out allies they find, unless the body is hidden.

### 6. What the player learns, and where

Each counter is taught in the world before it's needed. The level changes list where:
- Skiv's rumour: "Rats all breathe through masks";
- the Yard's kennel manual on a terminal;
- the scrap turret's sticker: "DON'T HACK THIS, DUTCH".

### 7. Everyone can be shot (owner, 2026-09-27)

"Any npc can be shot, if they can defend themselves they will."

- **Health for everyone.** Named NPCs and civilians use the same damage rule (section 2) with
  the same zones. Their health comes from `data/npcs.json`, whose default is 80.
- **A defence per NPC.** `data/npcs.json` gains `defence` and `weapon`:

| Defence | Who | On being attacked or seeing a gun drawn on them |
|---|---|---|
| `fight` | anyone with a `weapon`: MerSec, gang members, Tank (baton), Dace (pistol), Kessler (a Scattergun under the counter), Silk (pistol), Jax (pistol), Skiv (pipe) | draws and fights, as their archetype |
| `flee` | most civilians, Nguyen, Mouse, Rivet, Lin | runs to the nearest exit point away from the threat; shouts an alarm bark |
| `cower` | some civilians (a seeded half of them), Doc Vo, Mags | drops and covers where they stand; can be talked to after 10 s ("Please...") |
| `surrender` | Petra, the Oracle, anyone at 25 % health or less whose Intimidate check fails | hands up; drops their weapon; can be talked to |

- **Consequences are data, not special cases.**
  - Killing an NPC sets `npc:<id>:dead` and `World.Npc(id) = Dead`.
  - Their quests fail (`QuestDef.Giver`), and their vendor closes.
  - A witness reports it as a crime (`GameState.ReportCrime`, the one crime rule), and MerSec
    turns hostile, as for any shot fired in the hub.
  - Hurting without killing is a crime too.
- **Knockouts.** A knocked-out NPC is `Unconscious`. They wake after 120 s unless moved. Dragging
  and hiding bodies is Stealth's job (perception-and-disguise, bodies).
- **Bodies.** Deaths and knockouts hand the body to a ragdoll (`openspec/specs/npc-characters`; npc-characters design section 7).
  The ragdoll settles within 3 s, then freezes, so a body costs nothing after it lands.

## Risks / Trade-offs

- **Brushfire's enemies are arena monsters.** Undercity needs humanoids that act, talk, sleep
  and fall. Their bodies are the npc-characters change: generated humans on Godot's humanoid
  profile, a shared animation library and ragdolls. They replaced the segmented rigs of decision
  C1 in the hub on 2026-09-28 (`openspec/specs/npc-characters`).
- **Shooting quest givers can dead-end the story.**
  - Every mission keeps a route that doesn't need a given NPC alive, and each design lists it.
  - The journal says which quest failed and why.
- **Undamped noise plus hard-hitting enemies can snowball.** Wary lasts only 120 s, and the
  alarm expires, so a mistake is survivable.

# Design: Low Harbor

## Context

The map is `docs/design/maps/hub.svg`, generated from `tools/levels/layouts/hub.py`. Numbers
in this document are the map's POI numbers.

**Art direction:**
- UT99 construction rules (trims, pillars with bases and capitals, visible fixtures).
- A neon-noir palette: warm sodium fixtures, a cool blue fill, and pink and cyan neon as the
  accent pair for the hub.
- Rain, puddles that reflect the neon, and steam from vents.
- Lighting is baked like the Brushfire levels.

## Goals / Non-Goals

**Goals:**
- **Deus Ex density.** The hub is "an inch wide and a mile deep" (80.lv). Every block has an
  address, most buildings are facades, and the enterable ones are furnished.
- **Walkable in 3 minutes end to end.** You pass something to talk to every 20 m.
- **A small infiltration of its own.** Precinct 9 (S3) teaches the verbs in a safe place.

**Non-Goals:**
- The Upper City. The station is sealed, and the U marker says "later".
- Day and night. It is always night.
- Fast travel.

## Decisions

### 1. Districts

| District | Character | Holds |
|---|---|---|
| Spire Foundations | the megatower's foundation wall, 400 m of tower above; a holo-billboard | Low Harbor Station (19), sealed, with MerSec |
| Lantern Row | the neon strip: bars, karaoke, pachinko, capsules | Golden Carp (5), Neon Koi, Pachinko Sunrise, the Rusty Anchor (1), Kessler's (2), Doc Vo's (3) |
| Tin Stacks | shanty stacks, 3 m alleys, fire escapes, burn barrels | Mouse (12), the roof run (23), the Pit and the storm drain (17), Skiv (14) |
| Sump Market | the square under the Skyway; stalls between the pillars | Nguyen (4), the Oracle (7), the service lift (20), the Fish Hall (6) |
| Kiln | workshops, the freight yard, the shrine | Kings' Garage and Jax (15), Tsang Shrine (16, 27), freight tunnel (22), checkpoint (18) |
| Drydock | across the Cut: the depot, the dry dock, MerSec's precinct | Petra (10), depot lockers (28), Precinct 9 (29), MV Anselm |

### 2. Named NPCs

| # | NPC | Where | Role | Checks and hooks |
|---:|---|---|---|---|
| 8 | Silk | Rusty Anchor back room | fixer; gives M1 and M2; pays | [Persuasion 3] +25 % fee; knows everyone |
| 9 | Tank | Anchor, back-room door | bouncer | [Persuasion 2] or 50 cr, or pick the back door (Lockpicking 1) from Market Street |
| 1 | Mags | Anchor bar | bartender, vendor (drinks), rumours | S4 Last Call; free drinks after it |
| 2 | Kessler | Kessler's Pawn | weapons, ammo, gear; buys loot (not stolen) | [Persuasion 2] Haggler prices; the office safe (Lockpicking 3, 400 cr, a bad idea) |
| 3 | Doc Vo | clinic | heals (5 cr per point), medkits, stims | pharmacy store (Lockpicking 1 or Hacking 1: theft) |
| 4 | Nguyen | noodle bar | noodles; gossip | knows the storm drain gate code (a free code flag if you eat) |
| 13 | Rivet | Fish Hall | scavenger; sells the Rat jacket (60 cr) | [Persuasion 1] 40 cr |
| 12 | Mouse | Tin Stacks den | street kid; roofs and vents | S3 Mouse's Debt; shows the roof run after S3 |
| 10 | Petra | Sanitation depot | her brother is a hostage | gives the sewer service key and the overalls; S2 after M1 |
| 11 | Officer Dace | checkpoint | MerSec sergeant, I 3 | the M2 gate: bribe 150 cr, [Persuasion 3], the gang pass, or blackmail (S3 evidence) |
| 14 | Skiv | the Pit | Drain Rats scout, I 1 | [Persuasion 2] or 100 cr: parley with the Rats; rumour: "Rats all breathe through masks" |
| 15 | Jax | Kings' Garage | Scrap Kings recruiter | [Deception 2] cons him out of the gang pass; S1 Kingmaker |
| 16 | Sister Lin | Tsang Shrine | shrine keeper; rumours | sells the Silver Lighter (250 cr); points to the offering box |

**Civilians.** About 25 residents, dock workers and night-market customers, each with seeded
small talk and one rumour. Three MerSec troopers: two patrol and one guards the station.

### 3. Vendors

| Vendor | Sells | Buy mult |
|---|---|---:|
| Kessler | Kestrel, Whisper (after M1), dart pistol, SMG (after M1), Scattergun (after M2), ammo, lockpicks, multitools, grenades (EMP, frag), kevlar vest | 1.0 |
| Doc Vo | medkits, stims; healing | 1.0 |
| Mags | synth-whisky, noodles | 1.0 |
| Nguyen | noodles | 0.8 |
| Fish Hall black market | knockout gas, noise makers, lockpicks, soft soles; buys stolen goods at 0.3 x value | 1.2 |
| Rivet | Rat jacket (one) | 1.0 |
| Sister Lin | Silver Lighter (one) | 1.0 |

### 4. Routes to the missions

| Mission | Main way | Alternatives |
|---|---|---|
| M1 The Drains | storm drain in the Pit (17), gate code from Nguyen or Lockpicking 1 | canal outfall grate (21), Lockpicking 1, arriving in the Drains' sluice room |
| M2 The Yard | the checkpoint (18): gang pass, 150 cr bribe, [Persuasion 3], or blackmail with S3 evidence | freight tunnel gate (22), Hacking 1, arriving at the Yard's rail gate; or wait for the patrol and climb the checkpoint's jersey blocks behind the camera (a stealth route with no skill) |

### 5. Hub rules

- **Weapons.** Drawing a weapon in view of MerSec gets one warning ("Put it away."). After a
  second offence within 60 s, or any shot, MerSec fights, and the hub alarm calls backup in
  60 s.
- **Crime.** Theft or lockpicking in view of a resident or MerSec is a crime: the resident
  reports it, and MerSec goes Suspicious. It costs 5 reputation with Sump residents.
- **The safehouse** (Golden Carp, capsule 12) is where you sleep (save), keep your stash
  (10 x 10) and read your notes.
- **Restock.** Vendors restock, and Doc Vo's prices reset, each time a mission is completed.

### 6. S3 Mouse's Debt (hub infiltration)

- **The setup.** Mouse owes Officer Dace 300 cr, and Dace is squeezing him.
- **Ways through:**
  - pay 300 cr;
  - [Persuasion 3] Dace lets it go;
  - blackmail with evidence (see below).
- **The evidence** is found either way:
  - Dace's bribe log on the Precinct 9 terminal (Hacking 2; the precinct is restricted, so
    enter in sanitation overalls to "check the drains", or through its roof hatch from the dry
    dock gantry with Lockpicking 2);
  - the dented MerSec badge from the crusher's last load in the Yard (secret 22).

  With it, [Persuasion 2] makes Dace drop the debt, and he waves you through the checkpoint
  for good.
- **Reward:** 250 XP. Mouse shows you the roof run (23) and tells you about the Drains' crawl
  vent (a revealed route in M1).

### 7. Skill uses in the hub

| Skill | Where |
|---|---|
| Persuasion | Tank, Silk's fee, Kessler, Rivet, Dace, Skiv's parley |
| Deception | Jax's gang pass; Dace ("I'm with Sanitation"); Precinct 9 in overalls |
| Hacking | service lift (20), freight tunnel gate (22), Precinct 9 terminal, Doc Vo's pharmacy |
| Lockpicking | Anchor back door, outfall grate (21), offering box (27), Kessler's safe |
| Stealth | Precinct 9; the roof run; getting past the checkpoint camera |
| Firearms and Melee | none: the hub is the safe place, and using them there costs you |

### 8. Sectors (owner C2, 2026-09-27)

"Recommended, we should sectorize these for rendering efficiency as well."
- **One glb and one lightmap per district,** plus `streets` and `skyway`. Bake one district
  first and time it.
- **Chunks for culling.** Geometry inside a sector is split into chunks of about 40 x 40 m, so
  Godot can frustum-cull them.
- **Visibility ranges.** Interiors are drawn within about 45 m and small props within about
  70 m.

## Risks / Trade-offs

- **Size.** 240 x 170 m of dense facades is the biggest level the pipeline has baked. The bake
  may need to be split by district (lightmap per district scene) and streamed as a whole.
  Measure first: the Blender level took about 15 minutes at a sixth of this area.
- **Facade count.** Most footprints are facades with no interior. They're built from a kit
  (storefront, fire escape, sign, awning) placed by the layout's lot polygons, so density
  costs no hand work.

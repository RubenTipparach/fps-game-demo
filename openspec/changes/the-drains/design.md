# Design: The Drains

## Context

The map is `docs/design/maps/drains.svg`, from `tools/levels/layouts/drains.py`. The
Brushfire Blender level (`cistern.glb`) already proves the kit: brick collectors, water
channels, trims, pillars with capitals. The Drains reuse it at a larger scale.

## Goals / Non-Goals

**Goals:**
- **Completable four ways,** each with no kills:
  - fighting (with knock-outs);
  - sneaking;
  - talking in disguise;
  - talking under parley.
- **Every skill has at least two uses.**
- **The Twitch rule** turns "go loud" into a real decision, not a default.

**Non-Goals:**
- Swimming rules of its own. The bypass is a 35 s swim, or a walk once it's drained, under
  the hub's water rules (`water-and-swimming`: the same breath, stamina, swim motor and AIR
  bar); the Drains only adds its water to its layout.
- Rat reinforcements from outside the level.

## Decisions

### 1. Spaces

| Space | Level | Size | What happens |
|---|---:|---|---|
| Storm drain stairs | -1 | 8 x 18 m | arrival from the Pit; the way out with the hostages |
| Sanitation maintenance | -1 | 28 x 21 m | lockers (overalls), office terminal (sewer map, the Rats' password), break room (crawl vent), service door (key or Lockpicking 2) |
| Collector tunnel | -1 | 72 x 14 m | walkways both sides of a 4 m channel (wading is noise 8 m); grate bridges; patrolling scavenger; tripwire shotgun trap; overflow pipe into the bypass |
| Drowned Chapel | -1 | 22 x 11 m | secret through a crack; data shard, credit chip, neural chip |
| The Junction | -1 | 26 m octagon | the Rat checkpoint: barricade, 2 gunners, scrap turret, lookout; ladder up to the catwalk ring |
| Sluice room | -1 | 16 x 26 m | sluice terminal (Hacking 1: drain the bypass); the outfall tunnel from the hub |
| Flooded bypass | -2 | 3 m pipe | 35 s swim with a breath bar (45 s), or a walk when drained; surfaces in the cistern pool |
| Rat camp | -1 | 62 x 36 m cistern | 12 pillars, the pool, tents, fires, shacks; Old Wick's counter; Lug; two sleepers; whisky crates (S4); Rat stash (respirator, goggles) |
| Catwalk ring | +1 | 2 m wide at 6 m | lookout patrol; catwalk cache; overlooks everything |
| Pump station | -1 | 44 x 46 m | three pumps; the hostage cage (pump room key or Lockpicking 2); Twitch; a gunner |
| Mother Rat's nest | +1 | 27 x 10 m mezzanine | Mother Rat and Hatchet; desk (pump room key); safe (Lockpicking 3 or code); terminal (Hacking 2) |

### 2. The mission

**Given by Silk** (hub) after the player gets past Tank: 800 cr for both hostages alive. Petra
(hub) adds her brother's name, the sewer service key and her spare overalls if asked.

| Objective | XP | Notes |
|---|---:|---|
| Get into the Drains | 100 | any entrance |
| Find the hostages | 150 | revealed by the office terminal, the Rats' talk, or seeing the cage |
| Free the hostages | 400 | open the cage |
| Get them out | 300 | freed, they escape on their own by the route you came in (owner A1); the objective completes when they reach it |
| Bonus: Mother Rat's safe | 150 | 400 cr, a data shard (the ransom emails), 2 EMP grenades |
| Optional: deal with Mother Rat | 0 to 300 | talked down 300; paid 100; left alone 0; knocked out 200; killed 0 |
| Mission bonuses | 500 / 300 / 200 | Ghost / Merciful / Smooth Operator |

**Outcomes:**

| Outcome | Silk pays | Petra | Reputation | Other |
|---|---:|---|---|---|
| Both hostages out | 800 cr | grateful: S2 opens, she gives 2 medkits | Sanitation +30 | Tomas knows a ledger exists (S2) |
| One dies | 400 cr | grieving: no S2 | Sanitation +5 | |
| Both die | 0 cr | hostile to you | Sanitation -20 | Silk: "Bad for business." |
| Mother Rat killed | - | - | Rats -40, residents +10 | Skiv turns hostile in the hub |
| Mother Rat talked down | - | - | Rats +10 | Rats neutral in the hub for good |

### 3. The Twitch rule

- **The execution.** If Twitch becomes Alerted, a countdown starts. Eight seconds later he
  shoots one hostage, unless he's knocked out, asleep or dead by then. It happens at most
  twice.
- **What doesn't trigger it:**
  - a Suspicious Twitch (who investigates, and doesn't execute);
  - a level alarm that doesn't reach the pump station zone;
  - noise from the Junction (too far: the pump station is 60 m away).
- **Warnings.** A bark ("Anyone comes in hot, the sanitation boys get it") and Lug's dialog
  both warn you.

### 4. Routes

| Route | Path | Skills that help | Skills required |
|---|---|---|---|
| **Force** | stairs, maintenance, collector, Junction (fight), camp (fight), pump station | Firearms, Melee, Stealth | none (take out Twitch first) |
| **Social: disguise** | Rat jacket (Rivet) plus the stash respirator and goggles; talk past the checkpoint (I 2); talk to Twitch or Mother Rat | Deception, Persuasion | Deception 1 and an outfit; Twitch's lie needs Deception 2, Mother Rat's cover 5 |
| **Social: parley** | Skiv (hub, [Persuasion 2] or 100 cr) arranges it; walk in unarmed; Mother Rat talks | Persuasion | none if you pay Skiv 100 cr |
| **Stealth: bypass** | overflow pipe (collector) or sluice room into the bypass; swim (or drain it, Hacking 1); surface in the cistern pool; the link to the pump station | Stealth, Hacking | none (a breath bar) |
| **Stealth: vent** | break room vent, over the collector, down into the pump station behind the cage (3 m drop); branch into the nest | Stealth, Melee | none; revealed by Mouse (S3) or the maintenance terminal |

**Mother Rat talked down (social):**
- [Deception 3] "The city paid. Check your account." It needs her not to have read the
  terminal first.
- [Persuasion 3] "MerSec is coming down those stairs in ten minutes."
- Pay 500 cr ransom.

Any of them opens the cage and turns the Rats neutral while you leave. Talking to her at all
needs Cover 5 in disguise, or the parley.

### 5. Skill uses (at least two each)

| Skill | Uses |
|---|---|
| Firearms | clearing the Junction; Deadeye on the lookout from the collector (28 m) |
| Melee | Twitch takedown from the vent drop; knocking out the patrolling scavenger; Heavy Hitter on Hatchet |
| Stealth | the vent; the catwalk ring past the lookout; crossing the camp between the fires |
| Hacking | sluice (1), tripwire shotgun trap (1), scrap turret (2), nest terminal (2) |
| Lockpicking | outfall grate from the hub (1), service door (2), cage (2), safe (3) |
| Deception | the checkpoint in disguise; Twitch [Deception 2]; Mother Rat [Deception 3] |
| Persuasion | Lug [Persuasion 1] for the patrol timing; Twitch [Persuasion 3]; Mother Rat [Persuasion 3]; Skiv's parley (hub) |

### 6. Enemy placement (see the map)

| Where | Who |
|---|---|
| Collector | 1 scavenger patrolling the walkways |
| Junction | 2 gunners, a scrap turret (Hacking 2 turns it on them), 1 lookout |
| Camp | 1 at a fire, 2 asleep, a lookout on the catwalk ring; Old Wick and Lug (talkable, I 2 and I 1) |
| Pump station | Twitch (I 3) and a gunner |
| Nest | Mother Rat (I 4) and Hatchet (I 3, heavy) |

That makes 11 hostiles, 2 turrets or traps, and 2 talkable Rats.

### 7. Lighting and mood

- **Fixtures.** Sodium work lamps on the walkways (warm); a cool blue fill from grates up to
  the street.
- **The accent** is the Rats' green chem-lights and the camp's fires.
- **Darkness is a tool.** The collector's east half and the catwalk ring are deliberately dark
  (light below 0.25) for Shadow.

## Risks / Trade-offs

- **Freed hostages leave on their own (owner A1, 2026-09-27).** They walk out by the route
  you came in, so there's no escort. If the level alarm is up when they pass Rats, those Rats
  turn on them, which keeps a loud run costly.
- **The Twitch rule can feel unfair** if the player doesn't know it. It's barked, it's in Lug's
  dialog, and it's in Silk's briefing ("Twitch is jumpy. Don't give him a reason.").

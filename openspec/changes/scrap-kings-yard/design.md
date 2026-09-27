# Design: Scrap King's Yard

## Context

The map is `docs/design/maps/yard.svg`, from `tools/levels/layouts/yard.py`. This is the first
Undercity exterior. It uses the Brushfire sky surfaces and a moon-aimed baked spotlight
(CLAUDE.md 7.3), plus three dynamic searchlights.

## Goals / Non-Goals

**Goals:**
- Tech is a full route: power, cameras, turrets and the kennel.
- The dogs make the disguise route harder without closing it.
- The Kingmaker choice has consequences in the hub.

**Non-Goals:**
- Driving the cars or operating the crane (the boom is a fixed walkway).
- Destroying the yard (the fuel tanks explode once, locally).

## Decisions

### 1. Spaces

| Space | Size | What happens |
|---|---|---|
| Gatehouse and gate | 10 x 10 m | Bolt and a guard; camera console (Hacking 1: loop the cameras); gate turret (Hacking 2 disables, 3 turns) |
| Car stacks | 40 x 72 m | rows of crushed cars one to three high; the fence gap in the SW; dog patrol through the aisles; car trunk stash (secret) |
| Kennel | 8 x 8 m | two dog docks; kennel terminal (Hacking 2 keeps the dogs docked) |
| Container maze | 50 x 58 m | 22 containers, some stacked; a dog patrol; a searchlight tower |
| Crane and crusher | - | climb the crane (no skill), walk the boom (+18 m) to the container stack; the crusher's last load (secret: a MerSec badge) |
| Container stack | 3 high | a lookout with a rifle; the catwalk to the warehouse roof and the skylight (Lockpicking 1) |
| Chop shop | 44 x 36 m | 4 car lifts, paint booth (shotgun crate), parts; 2 mechanics, the Bruiser, Dutch |
| Crusher's office | 18 x 12 m at +4 m | Crusher (I 5); desk (the ledger); safe (the nav core); terminal (Hacking 3) |
| Generator shed | 16 x 12 m | power off (Hacking 1, or a frag grenade) kills the searchlights, the gate and its turret; the foreman comes to look |
| Barracks | 5 trailers | two off-duty Kings (one asleep); Kings' lockers (vest, goggles, mask) |

### 2. The mission

**Given by Silk** after M1, or at once if the player asks: 1,200 cr for the nav core.

| Objective | XP | Notes |
|---|---:|---|
| Get into the Yard | 150 | any of four entrances |
| Find the nav core | 100 | Dutch, the office terminal, or looking in the safe |
| Steal the nav core | 600 | open the safe |
| Get out | 250 | any exit; the Kings hunt you if the alarm is up |
| S1 Kingmaker | 400 | kill Crusher, or expose Jax (either pays) |
| S2 The Ledger | 300 | take the book from the desk, or copy it at the terminal (Hacking 3) |
| Mission bonuses | 500 / 300 / 200 | Ghost / Merciful / Smooth Operator |

**Opening the safe:**
- Lockpicking 3 (hold 6 s, 3 s with Safecracker);
- the combination from Crusher's terminal (Hacking 3), or from Dutch ([Persuasion 3] or
  300 cr);
- talk Crusher into opening it for a "buyer": full Kings outfit at Deception 2 (cover 6) and
  [Deception 4];
- as his reward, if you expose Jax (S1).

### 3. S1 Kingmaker

**The pitch.** Jax (hub) wants Crusher dead so he can run the Kings, and pays 500 cr.

| Choice | How | Result |
|---|---|---|
| Kill Crusher | any way (poisoning his whisky with the paint booth's thinner is the quiet one) | Jax runs the Kings; Kings reputation +10 (Jax's friends); Jax pays 500 cr; the nav core still has to be taken from the safe |
| Expose Jax | [Persuasion 4], or show Crusher Jax's messages (Dutch has them, [Persuasion 3] or 300 cr) | Crusher opens the safe for you as thanks; Jax is found in the canal; Kings reputation +30; Jax's 500 cr is lost |
| Leave them be | do nothing | S1 fails quietly; Jax sulks |

### 4. Routes

| Route | Path | Needs |
|---|---|---|
| **Social** | the gate with the gang pass (conned from Jax, [Deception 2]), a Kings vest (I 2 guards), or 150 cr to Bolt; walk to the chop shop; talk to Crusher | an outfit and Deception 1, the pass, or credits; the safe talk needs cover 6 and [Deception 4] |
| **Stealth** | the fence gap (crouch), the car stack aisles (time the dog, or a noise maker), the container maze, the crane and boom or the container stack, the skylight (Lockpicking 1), dropping into the office when Crusher is on the shop floor | none; the dogs are the challenge |
| **Tech** | the rail gate from the freight tunnel (Hacking 1); the generator (Hacking 1): searchlights, the gate and its turret go dark, and the foreman comes; the back door (Lockpicking 2, or Dutch opens it) | Hacking 1 |
| **Force** | the gate, the yard, the roll-up door | EMP for the Bruiser and the dogs; gas for the mechanics (no respirators) |

**Disguise and the dogs.**
- A Kings outfit gets you past every human, but the dogs smell you.
- Answers: keep the dogs docked (kennel, Hacking 2), EMP them, lure them with a noise maker,
  or stay up high (dogs can't climb).
- Dutch warns you: "The dogs don't care what you're wearing."

### 5. Skill uses (at least two each)

| Skill | Uses |
|---|---|
| Firearms | shooting out searchlights (loud); the lookout with Deadeye; the force route |
| Melee | the barracks sleepers; mechanics; Heavy Hitter on the Bruiser |
| Stealth | the fence gap and stacks; the skylight drop; crossing under the searchlights |
| Hacking | rail gate (1), camera console (1), generator (1), kennel (2), gate turret (2/3), Crusher's terminal (3) |
| Lockpicking | skylight (1), back door (2), the safe (3) |
| Deception | the gate in a vest; the gang pass con (hub); Crusher's "buyer" [Deception 4] |
| Persuasion | Bolt ([Persuasion 2] instead of 150 cr); Dutch [Persuasion 3]; exposing Jax [Persuasion 4] |

### 6. Lighting and mood

- **Moonlight** is a cool blue key light, baked, from the sky's `moon_direction`.
- **Searchlights** are dynamic: 30 m beams sweeping 120 degrees in 8 s. Inside a beam, light
  is 1.
- **The warehouse** has warm sodium bays.
- **The accent** is the welding flashes in the chop shop (Kings' welding masks make them
  immune).

## Risks / Trade-offs

- **Dynamic searchlights** cost frame time on top of a baked scene. There are three at most,
  shadowless, with a volumetric cone faked by a mesh.
- **Kingmaker's "expose Jax" makes the safe free,** so the robbery becomes a conversation. That
  is the social route's reward. It still needs [Persuasion 4], or 300 cr plus finding Dutch.

# Design: perception and disguise

## Context

Thief made light and sound the whole game. Deus Ex and Human Revolution made awareness
readable (meters, icons, barks). Hitman made disguise a system with enforcers who see through
it. Undercity combines them: a Thief-style light and sound model, Human Revolution readouts,
and a Hitman-style disguise whose enforcer is *intelligence*, scaled by the owner's rule that
"you would need a higher skill to fool more intelligent enemies".

## Goals / Non-Goals

**Goals:**
- A player can predict what an NPC will notice from what the HUD shows.
- Disguise and stealth use the same meter, so a disguise feels like stealth in plain sight.
- The owner's rule holds exactly: a smarter observer needs a higher Cover.

**Non-Goals:**
- Squad tactics beyond the alarm and search patterns (flanking comes after the slice).
- Dynamic light from the player's flashlight beyond a flat "light = 1" while it's on.

## Decisions

### 1. Sight

| Archetype | Near cone (full rate) | Far cone (0.4 x rate) | Range | Intelligence | Notes |
|---|---|---|---:|---:|---|
| Civilian | 60 deg | 120 deg | 14 m | 1 | reports crimes to MerSec |
| Rat scavenger | 60 deg | 110 deg | 18 m | 1 | flees at 25 % health |
| Rat gunner | 60 deg | 110 deg | 22 m | 2 | |
| Rat lookout | 50 deg | 100 deg | 28 m | 1 or 2 | whistle: alarm radius 30 m |
| Twitch | 60 deg | 110 deg | 22 m | 3 | executes a hostage on Alerted |
| Mother Rat | 60 deg | 120 deg | 24 m | 4 | |
| Kings mechanic | 60 deg | 110 deg | 22 m | 2 | |
| Kings foreman | 60 deg | 120 deg | 26 m | 3 | radio: alarm in 2 s |
| Bruiser | 50 deg | 100 deg | 20 m | 2 | |
| Crusher | 60 deg | 120 deg | 26 m | 5 | |
| MerSec trooper | 60 deg | 120 deg | 26 m | 2 or 3 | |
| Robot dog | 90 deg | 180 deg | 16 m | - | scent 8 m through walls; ignores disguises |
| Camera | 60 deg | - | 14 m | - | sensor; ignores disguises |
| Searchlight | 34 deg beam | - | 30 m | - | sweeps 120 deg in 8 s |

**Visibility** `V = light x stance x motion x gear`:
- **light:** 0 to 1 at the player, from the baked light probes plus dynamic lights. The
  flashlight on counts as 1.
- **stance:** standing 1.0, crouched 0.6 (0.45 with Low Profile), prone (after the slice).
- **motion:** still 0.6, walking 1.0, sprinting 1.5, in a vent 0.
- **gear and perks:** Shadow x0.5 when light < 0.25.

**Detection meter** D from 0 to 1, per observer:
- It fills at `dD/dt = V x 1.2/s x (1 - d / range) x cone_factor` while the player is in a
  cone with line of sight (cone_factor 1 near, 0.4 far).
- It drains at 0.25/s when the player isn't seen.

### 2. Awareness states

| State | Enters when | Does | Leaves when |
|---|---|---|---|
| Unaware | start; after Wary ends | patrols, idles, barks greetings | D >= 0.3 or a noise is heard |
| Suspicious ("?") | 0.3 <= D < 1, or a non-combat noise | stops, turns, walks to the stimulus, 12 s look-around | D reaches 1 (Alerted) or 12 s pass (Wary) |
| Alerted ("!") | D = 1, combat noise nearby, a body, the alarm | fights; radios the alarm after 2 s if able | loses sight for 3 s (Searching) |
| Searching | lost sight while Alerted | goes to the last known position, searches a 12 m area for 30 s (Vanish: 15 s) | sees you (Alerted) or the time runs out (Wary) |
| Wary | after Suspicious or Searching | patrols 25 % faster; D fills 25 % faster; for 120 s | the timer ends (Unaware) |

- **Level alarm.** Raised by radio, a whistle, an alarm panel or a camera. It puts every
  faction member in the level zone into Searching for 120 s, and then Wary.
- **Bodies.** An unconscious or dead body in view makes an NPC Alerted and raises the alarm.
  Bodies can be carried (walk speed 3 m/s) and hidden in containers marked `stash`.
- **Unconscious NPCs** stay down for the mission unless a searching ally finds and revives
  them. Both are then Alerted.

### 3. Hearing (`perception.json`, radius in metres)

| Noise | Radius | Noise | Radius |
|---|---:|---|---:|
| Crouch walk | 1 | Kestrel 10mm shot | 20 |
| Walk | 4 (Soft Steps 2.8, soft soles x0.6) | Whisper 10mm shot | 5 |
| Sprint | 10 (Ghost: 4) | Sandman dart | 3 |
| Landing from 2 m+ | 6 | Rattler SMG | 25 |
| Wading water | 8 | Scattergun | 30 |
| Door | 5 | Frag grenade | 35 |
| Takedown | 6 (Silent Takedown 0) | EMP grenade | 12 |
| Body drop | 5 | Noise maker | 15 |
| Lockpicking | 3 | Glass break, shot lamp | 12 |
| Hacking | 2 | Can rattle tripwire | 18 |

- **Radius is not damped by walls in the slice.** Level design places noise-heavy areas with
  this in mind. Walls and doors will damp noise after the slice.
- **Weapons fire, explosions, a scream or a body drop** within the radius make the hearer
  Alerted (combat noises). Anything else makes them Suspicious and walk to the source.

### 4. Disguise

**Pieces and quality.**
- A piece matches faction F when its `faction` is F.
- A disguise **requires the BODY piece.** Without a matching outfit you're simply not
  disguised.
- `Q = 2 (BODY) + 1 (HEAD, if matching) + 1 (FACE, if matching)`, so Q is 2 to 4.
- `Cover = Deception rank + Q`, from 2 (Deception 0) up to 9.

**Deception 0 disables disguises.** At rank 0 every observer treats you as undisguised. The
runner starts at Deception 1.

**Scrutiny range** `S(I) = (2 + 2 I) m`, halved by Doppelganger (Deception 5).

**The verdict.** `Judge(observer faction, I, distance, talking)` returns one of:

| Verdict | When | Effect on D |
|---|---|---|
| NotDisguised | not wearing this observer's faction outfit, or Deception 0 | normal stealth rules |
| Blown | a suspicious act (below) seen; or (distance <= S(I) or talking) and Cover < I | D = 1 at once; the NPC remembers you (can't be fooled again this mission) |
| Suspicious | armour of another faction worn (not light armour with Master of Disguise); sprinting or crouching within S(I); in a restricted zone of this faction | fills at 0.35/s x V (Silver Tongue x0.75) |
| Accepted | otherwise | does not fill from sight |

**Suspicious acts that blow a disguise when seen:**
- a weapon drawn longer than the grace (0 s, or 2 s with Master of Disguise);
- attacking or firing;
- picking or hacking the faction's locks and devices;
- searching their containers;
- carrying a body;
- being in a restricted zone past its warning (3 s, with a bark);
- being seen changing clothes.

**Fast Talk** (Deception 2) offers, once per NPC per mission, a dialog beat when a disguise
is blown by distance or talking: "Relax, I'm new." It passes if Cover + 1 >= I. The NPC goes
back to Suspicious.

**Who can be fooled, at a glance and close up:**

| I | Examples | Cover needed | Cheapest way |
|---:|---|---:|---|
| 1 | Rat scavengers, lookouts, civilians | 1 | any outfit (Deception 1 + Q 2 = 3) |
| 2 | Rat gunners, Kings mechanics, Bruisers, MerSec troopers | 2 | any outfit |
| 3 | Twitch, Hatchet, the Kings foreman, Officer Dace | 3 | the outfit at Deception 1 |
| 4 | Mother Rat, MerSec officers | 4 | outfit plus one piece at Deception 1, or the outfit at Deception 2 |
| 5 | Crusher, corporate security chiefs (later) | 5 | full outfit (Q 4) at Deception 1, or the outfit plus one piece at Deception 2 |

Bosses also put `cover` checks in their dialog (Mother Rat: cover 5 to be believed; Crusher:
cover 6 and [Deception 4] to open the safe for a "buyer"). A disguise that gets you into the
room isn't automatically enough to carry the conversation.

**Unfoolable observers:**
- robot dogs (scent);
- cameras and turrets (sensors: hack, EMP or avoid them);
- any NPC who has been in combat with you this mission;
- anyone who saw you change clothes.

### 5. Readouts (mockups in the design page)

- **Detection arcs** around the crosshair point toward each observer whose D > 0. They fill
  with D and turn from white (filling) to amber (Suspicious) to red (Alerted). This is Human
  Revolution's convention.
- **An awareness icon** over each NPC's head: none, ?, !, or a search glass.
- **The disguise chip** under the health bar reads "DRAIN RATS  Q 3  COVER 4". When an
  observer inside scrutiny range is looking at you, it adds "vs I 3" in green or red. The same
  numbers show on the inventory screen's doll.
- **The level alarm** shows as a red bar at the top with a countdown.

## Risks / Trade-offs

- **Undamped hearing** is crude. It is predictable, and level design can plan around it.
  Damping is a later change.
- **Cover >= I is binary at close range.** That is intended and matches the owner's rule. The
  meter still gives the player time at a distance, and a Suspicious verdict gives warning
  before a Blown one.
- **Intelligence 5 enemies are rare by design.** A full outfit plus Deception 1 fools
  Crusher's eyes, but his dialog checks still gate the safe.

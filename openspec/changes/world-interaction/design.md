# Design: world interaction

## Goals / Non-Goals

**Goals:**
- Every lockable thing opens at least two ways, and every level offers a way around any lock.
- The prompt, the hold time and the outcome come from one function.
- A tool is consumed only when the action completes.

**Non-Goals:**
- Lockpicking or hacking minigames. Deus Ex used held timers; skill decides and time is the
  cost. A minigame can come later behind the same rule.
- Physics puzzles and object stacking. They come after the slice.

## Decisions

### 1. The use key

- **Target.** A ray from the camera, 2.4 m long, against the World, Enemy, Pickup and Interact
  layers. The nearest `IInteractable` in the hit node's ancestors is the target.
- **What the target answers.**
  - `Prompt(ctx)`: text, or null for nothing to do;
  - `HoldTime(ctx)`: seconds, 0 for a tap;
  - `Blocked(ctx)`: the prompt explains why;
  - `Interact(ctx)`.

  All four call core rules. `ctx` carries the character, the pack and the flags.
- **Holds.** A hold shows a progress ring. Releasing cancels with nothing consumed. Taking
  damage or being spotted (a detection state change) also cancels.

### 2. Locks (`data/locks.json`)

The ways to open are tried in this order, and the first that is possible is used.

| Way | Needs | Hold time | Consumes | XP | Noise |
|---|---|---|---|---:|---:|
| Key | the key item | 0 s | nothing | 0 | door 5 m |
| Code | the code flag (read, heard or hacked) | 1.0 s | nothing | 0 | 1 m |
| Pick | Lockpicking >= tier and a lockpick | 1.0 s x tier (x0.5 Fast Picks; safes x2, x0.5 Safecracker) | 1 lockpick (not at Lockpicking 5) | 20 x tier | 3 m |
| Hack | Hacking >= tier and a multitool | 1.5 s x tier (x0.8 at Hacking 2+) | 1 multitool (not at Hacking 5) | 20 x tier | 2 m |

- **The prompt names the way that will be used,** or says what's missing:
  - "Pick lock, tier 2 (hold 2.0 s)";
  - "Locked: needs the pump room key, or Lockpicking 2".
- **A lock opened once stays open,** persisted by stable id. Doors can be relocked by NPCs
  only if their level data says so (the hub pawn shop at night: after the slice).
- **Tier guide:**
  - 1: sheds, lockers, service doors;
  - 2: gang doors, cages, desk drawers;
  - 3: bosses' safes and offices, MerSec;
  - key-only: story gates, always with an alternative route.

### 3. Devices

| Device | Hack tier | Hacked options | Other counters |
|---|---:|---|---|
| Security camera | 1 | Loop 60 s; Disable | EMP 60 s; shoot (noise, and it raises alarm if seen by a guard); avoid its cone |
| Alarm panel | 1 | Disable | Cut the wire (multitool, no skill); kill the runner before they reach it |
| Door panel | tier of the lock | Open | Key, code, pick |
| Turret (gate, scrap) | 2 | Disable (Hacking 2); Turn on owners (Hacking 3) | EMP 30 s; flank (120 degree arc); power off |
| Robot dog kennel | 2 | Keep the dogs docked | EMP the dogs 20 s; noise makers |
| Searchlight | - | - | Power off at the generator; shoot the lamp (noise 12 m) |
| Generator | 1 | Power off: searchlights, gate and turret die; the foreman comes | Frag grenade (loud) |
| Sluice | 1 | Drain the bypass (walk it instead of a 35 s swim) | - |
| Terminal | 0 to 3 | Log in; read email; run its actions | Password from a note or dialog (a code flag) |

- **A device's owner faction** decides who notices. Hacking a device in view of its owners
  counts as a suspicious act even in disguise (perception-and-disguise).
- **Cameras** feed detection to the alarm system: a camera that fills its detection meter
  raises the level alarm.

### 4. Terminals

A terminal holds login (hack tier or password flag), then pages of email and logs as
diegetic text, then actions:

```json
{"id": "drains:MaintenanceTerminal", "title": "SANITATION NET // LOW HARBOR",
 "hack_tier": 0,
 "pages": [{"from": "D. Okafor", "subject": "Rats at J-7", "body": "..."}],
 "actions": [{"label": "Print sewer map", "do": [{"reveal": "m1/route_vent"}]},
             {"label": "Read incident log", "do": [{"flag": "knows_rat_password"}]}]}
```

Codes and passwords learned anywhere (a terminal, a note, dialog) are flags. Once known, they
appear as the Code way on every lock that accepts them, and in the Notes tab.

### 5. Containers

- **Contents** are fixed in the level data (`"items": ["medkit", "ammo_10mm:24"]`). There
  are no random rolls in the slice.
- **Owner faction.** A container with an owner marks what's taken from it as stolen. Searching
  it in view of the owner is a crime if you're undisguised, and suspicious if you're disguised.
- **Searching** takes everything that fits; the rest stays, and the container remembers it.
- **The safehouse stash** is a container with a 10 x 10 grid and no owner.

### 6. Level travel and persistence

- **Exits.** A level exit names its target level and spawn, and an optional condition (a flag,
  or an item for a gated exit). Using it saves the game and loads the target.
- **Per-level persistence,** by stable id:
  - `taken` (world items and containers emptied);
  - `opened` (locks);
  - `doors` (open or closed);
  - `dead` and `unconscious` (NPCs);
  - `devices` (camera looped or disabled, turret mode, generator off).
- **Returning.** A returning level applies these after it loads and before the first frame
  is shown.

## Risks / Trade-offs

- **Held timers are less tactile than a minigame.** They keep the rule single and
  deterministic, which matters more here. A minigame can wrap the same rule later without
  changing its outcomes.
- **Fixed loot is less replayable.** It is exactly what the level design and the design map
  promise, which matters more for a hand-built slice.

# Design: world interaction

## Goals / Non-Goals

**Goals:**
- Every lockable thing opens at least two ways, and every level offers a way around any lock.
- The prompt, the hold time and the outcome come from one function.
- A tool is consumed only when the action completes.

**Non-Goals:**
- Physics puzzles and object stacking beyond the slice.
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

### 7. Minigames (owner B2, 2026-09-27: "play minigame")

The skill still decides what you may attempt: a lock of tier T needs Lockpicking >= T, and a
device of tier T needs Hacking >= T (section 2). The minigame decides how quickly and how
quietly you get through. Every number is in `data/locks.json`.

**Lockpicking: the pin stack.**
- The lock shows a side view of its pins: 3 at tier 1, 5 at tier 2, 7 at tier 3. Each pin
  has a shear line.
- Hold tension and lift the pin under the pick. Release inside the shear window and it sets;
  it clicks, and the next pin binds. Release outside the window and the pin drops (1 m noise).
- The shear window is 12 % of the pin's travel, +4 % per rank above the tier. Fast Picks
  slows the pins' drop by half.
- Three drops in a row break the pick, and the lock remembers the pins still set. The pick is
  also used up when the lock opens, except at Lockpicking 5.
- Safes use the same stack with 1.5x the pins.

**Hacking: the trace.**
- The device shows a small node graph: entry, target, and 4 to 12 nodes between, by tier.
  Capturing a node takes 0.6 s; the target takes 1.2 s.
- A captured node opens its neighbours. Some nodes are firewalls: capturing one starts the
  trace, which runs back toward your entry at one node every 2.5 s (tier 1), 2.0 s (tier 2)
  or 1.5 s (tier 3).
- If the trace reaches the entry, you're locked out for 30 s and the device raises the alarm if
  it has an owner watching. Otherwise capture the target, then choose the action
  (loop, disable, turn, open).
- Hacking ranks above the tier add 20 % to the trace interval each. Operator (Hacking 2) makes
  captures 20 % faster. Ghost Login (Hacking 5) hides the first firewall.
- A multitool is used up when the hack succeeds, except at Hacking 5.

**Prompts and previews** keep coming from the same rule: "Pick lock, tier 2 (5 pins)".

**Until the minigame mockups are approved** (survey E1, E2), builds use the held timer from
section 2 as a stand-in, with the same skill gates and tool costs.

## Risks / Trade-offs

- **Minigames add player skill to a skill system.** The rank still gates what you may attempt,
  and it widens the windows and slows the trace, so a high rank feels easier without making
  a low rank impossible.
- **Fixed loot is less replayable.** It is exactly what the level design and the design map
  promise, which matters more for a hand-built slice.

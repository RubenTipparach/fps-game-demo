# Proposal: the use key, locks, hacking, containers, terminals, security devices and travel

## Why

Immersive sims are built from objects that answer to more than one tool. The 80.lv piece
calls it "a multitude of meaningful tools", with Thief's water arrow and Prey's Gloo cannon as
examples. In Undercity:
- a door opens with a key, a code, a lockpick or a multitool;
- a camera can be hacked, shot, EMP'd or walked around;
- a turret can be turned on its owners.

Those interactions need one set of rules, or each object type grows its own.

## What Changes

- **One use key.** It looks at the object under the crosshair and gets back a prompt and a
  hold time. Tapping or holding runs the action. The prompt comes from the rule that resolves
  it.
- **Locks.** Tiers 1 to 3, plus key-only. Four ways to open, in order: key, known code,
  lockpick (Lockpicking >= tier), multitool (Hacking >= tier). Each has a hold time, a tool
  cost, XP and a noise radius.
- **Hackable devices.**
  - Cameras: loop 60 s or disable.
  - Turrets: disable, or turn with Hacking 3.
  - Alarm panels, sluices, generators, doors, safes and terminals.
- **Terminals.** Diegetic email and log readers that also open doors, set flags (codes,
  passwords) and control devices.
- **Loot containers** with fixed contents from the level data, an owner faction, and a lock.
- **Level exits** with a target spawn, conditions, and a save on travel.
- **Persistence.** Taken, opened, dead, unconscious and door state per level, by stable id.

## Capabilities

### New Capabilities
- `world-interaction`: use, locks, hacking, containers, terminals, security devices, level
  travel and per-level persistence.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Locks`, `Undercity.Core/World`, `data/locks.json`,
  `data/levels/<id>.json`.
- Scene kit: `door`, `loot_container`, `terminal`, `security_camera`, `turret`, `level_exit`,
  `world_item`.
- Brushfire's `Doorway.cs` gains a lock through an adapter. Its auto-open behaviour stays for
  the reference maps.

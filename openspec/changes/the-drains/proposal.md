# Proposal: The Drains and mission M1, Rat Trap

## Why

The first mission teaches the whole game in one level: a disguise, a vent, a flooded bypass, a
checkpoint you can talk past, a guard who punishes noise, and a boss you can talk to. The
owner asked for sewers the player infiltrates. The Drains are Drain Rats territory under the
Sump, and the Rats hold two sanitation workers hostage.

## What Changes

- **The Drains,** a 160 x 110 m underground level on three levels:
  - **-1:** the Sanitation maintenance station, the collector tunnel, the Junction checkpoint,
    the sluice room, the Rat camp (an overflow cistern) and the pump station;
  - **-2:** the flooded bypass;
  - **+1:** the camp catwalk ring and Mother Rat's nest.
- **Mission M1, Rat Trap.**
  - **Objective:** free Tomas Petrov and Anil Das from the pump station cage and get them out.
  - **Rule:** Twitch executes a hostage 8 s after he's Alerted.
  - **Ways to deal with Mother Rat:** fight, talk, pay or parley.
  - **Bonus:** her safe.
  - **Side quest:** S4 Last Call (Mags' whisky in the camp).
- **Three routes:**
  - force, through the checkpoint;
  - social, in a Rat disguise or under parley;
  - stealth, through the flooded bypass or the crawl vent.

  Each is drawn on the map.
- **The plan is `tools/levels/layouts/drains.py`,** drawn as `docs/design/maps/drains.svg`.

## Capabilities

### New Capabilities
- `the-drains`: the Drains level, the Rat Trap mission and its outcomes.

### Modified Capabilities
None.

## Impact

- New level `game/levels/undercity/drains/`, a Blender build reusing the cistern level's brick,
  channel and trim kit.
- Dialog: Lug, Old Wick, Twitch, Mother Rat. Humanoids: Rats, hostages.

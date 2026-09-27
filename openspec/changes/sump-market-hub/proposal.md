# Proposal: Low Harbor, the Sump Market hub

## Why

"First design a hub ... which will be a seedy underbelly of a cyber punk city" (owner,
2026-09-27). The owner's reference is the Deus Ex: Mankind Divided Prague hub map: dense
footprints, named districts and buildings, numbered points of interest and mission markers.
The hub is where the player lives between missions: it sells, heals, gossips, hands out
contracts, and holds its own small infiltration.

## What Changes

- **Low Harbor**, a 240 x 170 m hub in six districts:
  - Spire Foundations;
  - Lantern Row;
  - the Tin Stacks;
  - the Sump Market;
  - Kiln;
  - Drydock across the Cut canal.

  It sits under the Meridian Skyway viaduct.
- **Enterable interiors:**
  - Low Harbor Station (sealed);
  - the Golden Carp capsule hotel (safehouse);
  - the Rusty Anchor bar;
  - Kessler's Pawn and Doc Vo's Clinic;
  - the Harbor Fish Hall night market;
  - the City Sanitation depot, the Kings' Garage and the Tsang Shrine;
  - the MerSec checkpoint and Mouse's den.
- **13 named NPCs**, all talkable, plus civilians with seeded small talk.
- **29 numbered points of interest and 7 mission markers:**
  - M1 Rat Trap and M2 Chop Job, both from Silk;
  - S1 Kingmaker (Jax), S2 The Ledger (Petra), S3 Mouse's Debt, S4 Last Call (Mags);
  - U, the Upper City, sealed until after the slice.
- **Two exits with alternatives:**
  - the storm drain or the canal outfall to the Drains;
  - the MerSec checkpoint or the freight tunnel to the Yard.
- **Hub rules:**
  - MerSec warns once about a drawn weapon, then fights;
  - theft in view is a crime;
  - the safehouse saves and stashes;
  - vendors restock after missions.
- **The plan is `tools/levels/layouts/hub.py`,** drawn as `docs/design/maps/hub.svg`.

## Capabilities

### New Capabilities
- `sump-market-hub`: the hub's layout, districts, NPCs, vendors, exits, side quests and hub
  rules.

### Modified Capabilities
None.

## Impact

- New level `game/levels/undercity/hub/`, built in Blender from the layout.
- Dialog trees for 13 NPCs and a civilian pool. Vendor stocks.
- Humanoid rigs for residents, MerSec, a Rat scout and a King recruiter.

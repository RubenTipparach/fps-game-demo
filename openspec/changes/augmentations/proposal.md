# Proposal: augmentations, with two starter augs in the slice

## Why

The owner answered survey B4 on 2026-09-27: yes, augmentations are in the first slice. Deus Ex
made augmentations the other half of a build, next to skills. They are powers you pay for in
energy, where skills are competences you pay for in points. Two starter augs are enough to
prove the system and to widen the routes the slice already has.

## What Changes

- **Energy.** 100 points, shown as a bar beside health. Like health, it regenerates only to a
  25 % floor (the owner's B1 rule, applied the same way). Biocells restore 40.
- **Aug slots.** CRANIAL, EYES and ARMS for the slice. One aug per slot. Augs are installed at
  Doc Vo's clinic from an aug canister, or come with the runner.
- **Two starter augs** (survey F1 to confirm):
  - **Echo Lens** (EYES): shows the awareness state and vision cone of every NPC within 15 m,
    through walls. Costs 3 energy per second while on.
  - **Mimic** (CRANIAL): a voice modulator. +1 Cover while talking in disguise. Costs 20 energy
    per conversation it is used in.
- **An Augs tab** in the character deck, and a small energy bar on the HUD. Mockups are in the
  design page, for approval (survey F2).

## Capabilities

### New Capabilities
- `augmentations`: energy, aug slots, installing, toggling and the two starter augs.

### Modified Capabilities
None. `perception-and-disguise` reads Mimic's bonus through the same Cover rule, so no
requirement there changes.

## Impact

- `Undercity.Core/Augs`, `data/augs.json`, a `biocell` item, and an `aug_canister` item.
- Deck and HUD scenes (after mockup approval).

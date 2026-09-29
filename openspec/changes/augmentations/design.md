# Design: augmentations

## Context

Deus Ex splits a build into skills (points) and augmentations (canisters and energy). Human
Revolution merged both into Praxis. Undercity keeps the Deus Ex split: skills decide what you
can attempt, and augs are active powers with a running cost, so they create decisions in the
moment instead of just larger numbers.

## Goals / Non-Goals

**Goals:**
- Augs open or ease routes. They never replace a skill check outright.
- Energy is a resource worth managing: two augs can't both run all the time.
- The rules exist once. Mimic's +1 Cover goes through the disguise rule, not beside it.

**Non-Goals:**
- Aug upgrades (levels within an aug). They come after the slice.
- Combat augs (arm blades, shields). Later changes.

## Decisions

### 1. Energy (`data/augs.json`)

| Value | Number |
|---|---:|
| Maximum | 100 |
| Regeneration floor | 25 % (the B1 rule) |
| Regeneration rate below the floor | 1 per s, 5 s after the last use |
| Biocell | +40 |

### 2. Slots and installing

- **Slots:** CRANIAL, EYES and ARMS. Later slices add TORSO and LEGS.
- **Installing.** An aug canister is installed by Doc Vo for 150 cr, or through her dialog at
  [Persuasion 2] for 75 cr. Installing into a full slot replaces the old aug, which is lost.
- **Keys.** Augs are toggled with F1 to F3 while playing (the deck uses the F keys only while
  it's open).

### 3. The starter augs

| Aug | Slot | Effect | Cost | Counter-play it opens |
|---|---|---|---|---|
| Echo Lens | EYES | awareness icons and vision cones of NPCs within 15 m, through walls | 3 energy/s | timing patrols, finding the dogs in the Yard, crossing the camp |
| Mimic | CRANIAL | +1 Cover in conversations while disguised | 20 energy per conversation | talking to Mother Rat at Cover 4, bluffing the foreman |

The runner starts with both installed, because the owner asked for augs in the slice.
Canisters for more augs come later.

### 4. Screens (mockups in the design page)

- **The Augs tab** in the deck: a figure with the slots marked, the installed aug per slot, its
  effect and cost, and the energy bar.
- **On the HUD,** a thin energy bar under the health bar, and a small icon per active aug.

## Risks / Trade-offs

- **Echo Lens could trivialise stealth.** It costs 3 energy per second, so 100 energy lasts
  33 s, and the regeneration floor refills only 25. Biocells are rare (three in the slice).
- **Mimic's +1** is exactly one intelligence tier. It matters, and it can't be stacked.

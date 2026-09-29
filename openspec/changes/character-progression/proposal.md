# Proposal: skills, perks, XP and levels

## Why

The owner wants "skill trees, xp, leveling up", and a disguise system where "you would need a
higher skill to fool more intelligent enemies". Progression is the spine of every other
system: dialog checks, locks, hacking, disguises and takedowns all read a skill rank. It
has to be designed first and designed exactly, because every other change quotes its numbers.

## What Changes

- **Seven skills**, each a five-rank tree: Firearms, Melee, Stealth, Hacking, Lockpicking,
  Deception and Persuasion.
- **Every rank unlocks one perk.** Its numbers live in `data/skills.json`, and four perks have
  cross-tree requirements.
- **Deterministic checks.** A check passes when `rank + item bonus >= DC`. The requirement is
  always visible.
- **XP.** The curve is `xp_to_next = 500 x level`, with a cap at level 20. Each level gives
  +2 skill points and +10 max health. The runner starts with 4 points and Deception 1.
- **More points than any one build needs, fewer than everything.** Maxing every skill costs
  56 points and the cap gives 42. Hidden neural chips add 1 each (3 in this slice).
- **An XP table that pays for play style.** Non-lethal takedowns pay more than kills, and
  ghost, merciful and no-alarm mission bonuses exist.
- **A skills screen.** Mockup in the design page. It is built only after approval.

## Capabilities

### New Capabilities
- `character-progression`: skills, ranks, perks, skill checks, XP, levels, points and
  health.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Character/` (`Character`, `SkillRules`, `XpTable`), `data/skills.json`,
  `data/progression.json`.
- Read by dialog, disguise, locks, combat and the HUD.

# Tasks

## 1. Data

- [ ] 1.1 `data/skills.json`: skills, rank costs, perks with numeric effects, cross-tree requirements.
- [ ] 1.2 `data/progression.json`: XP curve, cap, health per level, starting points and ranks, XP awards.
- [ ] 1.3 Schemas and validation tests (every perk effect names a known stat).

## 2. Core

- [ ] 2.1 `Character`: level, XP, points, ranks, events (LeveledUp, XpGained, RankRaised).
- [ ] 2.2 `SkillRules.CheckValue`, `CanRaise(skill)` returning the reason, `Raise`, `Cost`.
- [ ] 2.3 `XpTable.Award(source, context)`, which pays once per source id.
- [ ] 2.4 Perk effects as stat modifiers, queried by other systems (`Stats.Get("spread_mult")`).

## 3. Tests

- [ ] 3.1 Level curve table matches the design (levels 1-20, spill-over).
- [ ] 3.2 Rank costs, order, cross-tree requirements and the reason text.
- [ ] 3.3 Check value = rank + at most +1 item bonus, capped at 6.
- [ ] 3.4 Once-only XP for checks and locks.

## 4. Interface (after mockup approval)

- [ ] 4.1 Skills tab scene; level-up toast; XP feed line.
- [ ] 4.2 Capture: the skills tab at start and at level 5.

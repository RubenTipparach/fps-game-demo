# Design: character progression

## Context

References: Deus Ex (skills with four levels, plus augmentations), Human Revolution (Praxis
points into perk trees), System Shock 2 (cyber modules into stats and skills). Undercity takes
the Deus Ex shape: a few broad skills whose ranks read as numbers in checks. Each rank also
buys a perk, which is Human Revolution's strength. See 80.lv, "Five Pillars of Immersive Sims"
(Samoylenko, 2018): choices come from "sophisticated character progression" combined with
open levels.

## Goals / Non-Goals

**Goals:**
- Builds are real choices: a character can max about 5 of 7 skills by level 20.
- Every skill opens routes in every level (CLAUDE.md 7.1, three ways in).
- No dice. The player plans, and doesn't reload for a roll.

**Non-Goals:**
- Augmentations and energy. They are planned for after the slice, and the HUD reserves the
  space.
- Attributes (strength, agility). Skills carry everything.
- Respec. Choices stick (pillar 5).

## Decisions

### 1. Ranks and costs

| Rank | Cost (skill points) | Check value |
|---:|---:|---:|
| 0 | - | 0 |
| 1 | 1 | 1 |
| 2 | 1 | 2 |
| 3 | 2 | 3 |
| 4 | 2 | 4 |
| 5 | 2 | 5 |

- **A full skill costs 8 points.** All seven cost 56.
- **The check value** is the rank plus at most +1 from equipment (for example the Silver
  Lighter gives +1 Persuasion). It is capped at 6.
- **Ranks are bought in order.** A rank needs the previous one.

### 2. Perks

| Skill | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| **Firearms** | Steady Hands: spread -20 % | Quick Reload: reload time -25 % | Headhunter: headshots x3.0 (base x2.0) | Recoil Control: recoil -40 % | Deadeye*: crouched and still 1 s, next shot has zero spread and x1.5 damage |
| **Melee** | Clubber: melee damage +25 % | Silent Takedown: takedowns make no noise (base 6 m) | Quick Hands: takedown time -50 % | Heavy Hitter: can take down heavies from behind | One-Punch*: frontal takedown on unaware or suspicious I <= 3 |
| **Stealth** | Soft Steps: footstep radius -30 % | Low Profile: crouch speed 3.0 m/s (base 2.2), crouch visibility x0.45 (base x0.6) | Shadow: visibility x0.5 in light < 0.25 | Ghost: sprint is as quiet as a walk | Vanish: searchers lose you 2x faster once line of sight breaks |
| **Hacking** | Script Kiddie: tier 1 devices | Operator: tier 2, hack time -20 % | Root Access: tier 3, turn turrets | Loop Master: camera loops last 120 s (base 60) | Ghost Login: multitools no longer consumed; hack from 6 m |
| **Lockpicking** | Rake: tier 1 locks | Tension: tier 2 | Master Picks: tier 3 | Fast Picks: pick time -50 % | Safecracker: lockpicks no longer consumed; safes in half time |
| **Deception** | Passing Glance: disguises work (at a glance) | Fast Talk: one chance to talk down a blown disguise | Master of Disguise*: drawn weapon tolerated 2 s; light armour never clashes | Silver Tongue: suspicion fills 25 % slower; told lies stick | Doppelganger: scrutiny range halved |
| **Persuasion** | Friendly: rumour options; reputation gains +25 % | Haggler: buy -15 %, sell +15 % | Intimidate: threaten options; wounded enemies may surrender | Negotiator: bribes -40 %; retry a failed check once with a bribe | Kingmaker*: turn lieutenants against their bosses |

Perks marked * have cross-tree requirements:

| Perk | Also requires | Why |
|---|---|---|
| Deadeye (Firearms 5) | Stealth 1 | You must be still and unseen |
| One-Punch (Melee 5) | Stealth 2 | You must reach them unseen |
| Master of Disguise (Deception 3) | Stealth 2 | You move like one of them |
| Kingmaker (Persuasion 5) | Deception 3 | Turning a lieutenant is a lie as much as a pitch |

- **Rank N opens tier N.** Lockpicking and Hacking ranks 1 to 3 each open the next tier of
  locks and devices, so every level can say "Lockpicking 3" for a tier 3 safe, and the lock
  rule stays "rank >= tier". Speed and tool perks sit at ranks 4 and 5. (Corrected
  2026-09-27: the first table put tier 3 at rank 4, which the levels and the lock rule
  didn't match.)
- **Deception 0 means no disguise works at all.** "You wear it like a costume." That is why
  the runner starts at Deception 1, which is the trade.
- **Every numeric effect is a field in `skills.json`.** For example Steady Hands is
  `{"stat": "spread_mult", "value": 0.8}`, and the core applies it. The text in this table is
  written from those fields.

### 3. XP and levels

`xp_to_next(level) = 500 x level`, so the total XP needed to reach level L is
`250 x L x (L - 1)`.

| Level | XP to next | Total to reach | Max health | Skill points (cumulative) |
|---:|---:|---:|---:|---:|
| 1 | 500 | 0 | 100 | 4 |
| 2 | 1000 | 500 | 110 | 6 |
| 3 | 1500 | 1500 | 120 | 8 |
| 4 | 2000 | 3000 | 130 | 10 |
| 5 | 2500 | 5000 | 140 | 12 |
| 6 | 3000 | 7500 | 150 | 14 |
| 8 | 4000 | 14000 | 170 | 18 |
| 10 | 5000 | 22500 | 190 | 22 |
| 15 | 7500 | 52500 | 240 | 32 |
| 20 | cap | 95000 | 290 | 42 |

- **XP spills over.** One award can raise several levels, and the leftover carries.
- **The first slice** (the hub, M1, M2 and the four side quests) pays about 6,000 to 8,000 XP,
  so the player ends at level 5 or 6 with 12 to 14 points. That is two skills at rank 3, or
  one at 5.

### 4. XP awards (`progression.json`)

| Source | XP |
|---|---:|
| Main mission objective | 400 to 1,000 (per quest) |
| Side objective | 150 to 400 |
| Dialog skill check passed | 25 x DC |
| Lock picked or device hacked | 20 x tier |
| Non-lethal takedown or KO | 40 |
| Kill | 20 |
| Secret area found | 50 |
| Clue that opens a route (password, code, map) | 25 |
| Mission bonus: Ghost (never in combat) | 500 |
| Mission bonus: Merciful (no kills) | 300 |
| Mission bonus: Smooth Operator (no alarm raised) | 200 |

- **Non-lethal pays double a kill,** because it's harder and it keeps options open.
- **Each check and each lock pays once.** A check's XP is paid once per dialog choice; a lock's
  once per lock, not per attempt.

### 5. Skill points outside levelling

**Neural chips** are world items, one hidden in each slice map's secret area. Using one gives
+1 skill point. The chips exist so that exploration pays in progression, not just loot.

### 6. The skills screen

The screen is a tab of the character screen (Deus Ex's tabbed layout):
- seven columns, one per skill, with five rank nodes each;
- perk names on the nodes;
- the cost on the next node, and the reason a node is locked ("needs Stealth 2");
- points available in the header.

The mockup is in the design page (section "Screens"). It is built only after approval.

## Risks / Trade-offs

- **Deterministic checks can feel binary.** A check the player can't pass is a closed door
  they can see. That is intended: it points to another route. Every level spec guarantees one
  exists (no skill gate is the only way).
- **Seven skills at 8 points each is a lot of checks to design.** Every level must use every
  skill at least twice, or a skill feels wasted. The level changes list their checks per skill.

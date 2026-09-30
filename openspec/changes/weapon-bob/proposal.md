# Proposal: the gun sways gently while walking

## Why

The owner, 2026-09-29: "Huh gun is shaking up and down violently. That shouldn't happen. Gun
should maybe have a low frequency sine wave while walking".

The runner's view weapon is Brushfire's (`game/scripts/Player/WeaponManager.cs`), bobbed by a
phase the player controller advances with ground speed (`PlayerController.UpdateCamera`), tuned
for Brushfire's arena pace.

**Measured first** (design section 2). A measurement instrument, an AutoTest `trace` step,
records every rendered frame of a walk and a sprint in the hub: ground speed, the bob's phase and
weight, the camera's height over the feet, and the view weapon's offset and turn from the camera.
It is added only to produce these numbers (CLAUDE.md 3) and changes nothing the game does.

**What it found** (design section 2). Walking at Brushfire's 7.5 m/s with a 1.15 m step, the
runner takes 6.5 footsteps a second, three times a sprinter's pace. The view bobs 4.9 cm at
6.5 Hz with a sharp turn at every footstep (`|sin|`), 11.5 g at its peak, and the gun rides the
view and adds a 4 degree roll. At 30 frames a second that is a bounce every 4-5 frames. Sprinting
is worse: 6.5 cm at 8.7 Hz, 21.6 g.

**The owner's answers** (survey, 2026-09-30): N1 "very slightly, sine steps"; N2 "no view bobing
while moving"; N3 "recommended" (the pace stays for now).

## What Changes

- **Footsteps at a person's pace.** The gait keeps following ground speed but never takes more
  than 2.0 steps a second walking or 2.6 sprinting. The footstep sounds follow it.
- **The gun sways very slightly on slow sines (N1):** a figure-eight, 1.0 Hz side to side and 2.0 Hz
  up and down at a walk, 1.5 to 2.5 mm and under half a degree of roll, 1.5 times that sprinting.
  No corners.
- **The view doesn't bob (N2):** from 4.9 cm with a corner to none. The Options screen's head-bob
  row goes with it.
- **One gait function** for the gun and the footsteps, with its numbers in
  `game/data/view_motion.json`, validated by the core.
- **Checks** measure the motion the way this proposal did: footsteps a second, the sway's
  frequency, the view's offset, and no corners.

Not in this change: the runner's walking and sprinting speeds (N3: kept for now).

## Capabilities

### New Capabilities

- `view-motion`: how the view and the view weapon move while the runner walks and sprints.

## Impact

- `game/scripts/Player/PlayerController.cs` (`UpdateCamera`), `WeaponManager.cs`
  (`AnimateViewmodel`): both call the gait function.
- `game/scripts/Player/Gait.cs` (new), `game/data/view_motion.json` (new), its schema in
  `Undercity.Core` and a core test.
- An in-engine view test built on the `trace` instrument; the reference maps take the new gait.

# Design: the gun sways gently while walking

## Context

The owner, 2026-09-29: "Huh gun is shaking up and down violently. That shouldn't happen. Gun
should maybe have a low frequency sine wave while walking".

The runner is Brushfire's player (`game/scripts/Player/PlayerController.cs`) with Brushfire's
view weapon (`WeaponManager.cs`), which Undercity's `WeaponAdapter` fills with the belt's
firearm. Both bob from one gait phase the controller advances with ground speed:
`phase += speed / StrideLength * 2 pi * dt`, with `StrideLength` 2.3 m (two footsteps), and a
footstep sound plays each time the phase passes a low point.

## 1. How the view moves today

- **The view (head bob),** `UpdateCamera`: height `-|sin(phase)| * 0.05 + 0.025` m, side
  `sin(phase / 2) * 0.03` m, weighted by speed over walking speed (up to 1.3). `|sin|` has a
  sharp corner at every footstep: the view drops, then reverses at once.
- **The gun,** `AnimateViewmodel`, on top of the camera it hangs from: height
  `-|sin(phase)| * 0.016`, side `sin(phase / 2) * 0.018` and a roll of twice the side (in the
  gun's full-size units, scaled by 0.25), with look sway, recoil and a breathing sine.
- **The pace is Brushfire's arena pace:** walking 7.5 m/s, sprinting 10.5 m/s. At a 1.15 m step,
  that is 6.5 and 9.1 footsteps a second. People walk at about 2 steps a second and sprint at
  about 3.

## 2. Measured

A measurement instrument, the AutoTest `trace` step (`docs/playtest/scripts/weapon_bob_trace.json`,
headless, `--fixed-fps 60`, seed 7), records every frame of a walk and a sprint east along Lantern
Row with the Kestrel drawn, after the bob has settled:

| | Walk | Sprint |
|---|---|---|
| Ground speed | 7.5 m/s | 10.5 m/s |
| Footsteps | 6.5 a second | 9.1 a second |
| The view's height | 4.9 cm peak to peak, at 6.5 Hz | 6.5 cm, at 8.7 Hz |
| Its sharpest turn (peak acceleration) | 113 m/s², 11.5 g | 212 m/s², 21.6 g |
| The gun, from the camera | 4.6 mm up and down, 9.0 mm side to side, 4.1 degrees of roll | 5.7 mm, 11.7 mm, 5.4 degrees |
| Frames per bounce in a 30 fps video | 4.6 | 3.4 |
| The largest change in the view's vertical speed between two frames (60 fps) | 1.89 m/s | 3.53 m/s |

So what shakes is mostly **the view**, 5 cm at 6.5 Hz with an 11.5 g jolt at each footstep, and
the gun rides it. Seen at 30 frames a second, a bounce every 4-5 frames reads as shaking. The
gun's own bob adds a 4 degree roll at the same pace.

## Goals / Non-Goals

**Goals:**
- The gun sways on a slow, smooth sine while walking, and a little faster and wider while
  sprinting; it never jolts.
- The view barely moves: no corner at a footstep.
- The gun, the view and the footstep sounds stay in step with one another.
- The numbers are data, and a check measures the motion the way section 2 did.

**Non-Goals:**
- The walking and sprinting speeds. 7.5 m/s is fast for an immersive sim, but speed is movement
  tuning with its own consequences (patrols, doors' trigger radii, combat); a separate change.
- Look sway, recoil, the landing dip and breathing: they stay as they are.

## Decisions

### 3.1 One gait: footsteps at a person's pace

The phase keeps coming from ground speed, but a footstep is never quicker than a person's:

    cadence (steps a second) = min(speed / step_m, max cadence)
    phase += cadence * pi * dt          (one cycle is two footsteps)

| | `step_m` | Max cadence | At the game's pace |
|---|---|---|---|
| Walking | 1.15 m | 2.0 a second | 2.0 steps a second at 7.5 m/s (6.5 today) |
| Sprinting | 1.15 m | 2.6 a second | 2.6 at 10.5 m/s (9.1 today) |

At a slow walk (under 2.3 m/s) nothing changes: the cap only bites at the arena pace. The
footstep sounds follow the same phase, so they slow to match.

### 3.2 The gun: a slow figure-eight on sines

    side   = sin(phase)       * 5.0 mm  (one sway a stride: 1.0 Hz walking, 1.3 Hz sprinting)
    height = -cos(2 * phase)  * 3.0 mm  (one dip a footstep: 2.0 Hz, 2.6 Hz; smooth, no corner)
    roll   = sin(phase)       * 0.75 degrees

Sprinting scales all three by 1.5. The weight (speed over walking speed) fades them in and out
as today. Peak acceleration of the height at a walk: 0.003 m x (2 pi x 2.0 Hz)² = 0.47 m/s².

### 3.3 The view: small and smooth

    height = -cos(2 * phase) * 5 mm, side = sin(phase) * 3 mm   (1 cm peak to peak, from 4.9)

Peak acceleration at a walk: 0.79 m/s² (0.08 g), from 11.5 g. The Options screen's head bob
toggle still turns it off; the gun's sway stays, as it is part of holding a gun.

### 3.4 One implementation, in data

- **One gait function** (`Gait.cs`, a plain static class in the Godot layer) computes the phase
  step, the view's offset and the gun's offset from the phase, the weight and the numbers. The
  controller and the weapon both call it; neither keeps its own formula.
- **The numbers** go to `game/data/view_motion.json` (units in the keys: `step_m`,
  `max_cadence_walk_hz`, `max_cadence_sprint_hz`, `gun_side_m`, `gun_height_m`, `gun_roll_deg`,
  `sprint_scale`, `view_height_m`, `view_side_m`), validated on load by the core like every data
  file, with its schema class in `Undercity.Core`.
- **The reference maps** use the same player, so they take the new gait too. They are kept as
  level-building references (CLAUDE.md 1), not for their feel.

### 3.5 Checks

| Check | Where | Today | After |
|---|---|---|---|
| The data file loads, a misspelt key or a cadence of 0 is refused | `Undercity.Core.Tests` | | passes |
| Walking: footsteps at most 2.0 a second, the gun's height no faster than 2.1 Hz, the view's peak acceleration under 1 m/s² | an in-engine view test, the `trace` measurement headless | 6.5, 6.5 Hz, 113 m/s² | passes |
| Sprinting: at most 2.6 footsteps a second, under 1.5 m/s² | the same | 9.1, 212 m/s² | passes |
| Neither the gun nor the view has a corner: the largest change in the view's vertical speed between frames stays under 0.05 m/s at 60 fps | the same | 1.89 m/s walking, 3.53 sprinting | passes |

### 3.6 Captures

A video (CLAUDE.md 9: motion is the point) of the same walk and sprint along Lantern Row with
the Kestrel drawn, before and after, side by side, at 30 fps.

## Risks / Trade-offs

- **Floaty footsteps.** Two footsteps a second at 7.5 m/s is a 3.75 m stride, longer than any
  person's. The sounds and the sway will feel unhurried against the ground rushing past. That
  is the pace question (Non-Goals), and the survey asks it (N3).
- **The reference maps change feel.** Accepted: they are references for building levels.

## Owner questions (survey, section N)

- **N1** How the gun sways: slow and in step with footsteps capped at a person's pace
  (recommended) / a fixed slow sway whatever the pace / today's, smoothed.
- **N2** The view's own bob: small and smooth, 1 cm (recommended) / off by default / today's.
- **N3** The runner's pace: keep 7.5 and 10.5 m/s for now (recommended) / a slower, immersive
  sim pace, as its own change.

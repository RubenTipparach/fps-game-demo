# Tasks

The owner reported it on 2026-09-29. Survey N1 to N3 are open; the recommendations are marked
provisional.

## 1. Before

- [x] 1.1 The `trace` instrument in AutoTest, and the walk and sprint traced
  (`docs/playtest/scripts/weapon_bob_trace.json`, design section 2).
- [ ] 1.2 A before video of the same walk and sprint, at 30 fps.

## 2. The gait

- [ ] 2.1 `game/data/view_motion.json` and its schema in `Undercity.Core`, validated, with a
  core test.
- [ ] 2.2 `Gait.cs`: the capped cadence, the view's and the gun's offsets; `UpdateCamera` and
  `AnimateViewmodel` call it, and the footsteps follow its phase.

## 3. Checks and records

- [ ] 3.1 The in-engine view test: the walk and the sprint, against the spec's numbers.
- [ ] 3.2 The after video, side by side with the before; a validation record; archive.

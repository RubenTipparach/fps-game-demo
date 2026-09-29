# Validation: doorways in the hub

The owner, 2026-09-29: "a lot of buildings are missing door ways or doors, review guidelines for
level design that we did in e1 m3". The survey answered K1 to K3: no prompt on doors that never
open, automatic sliding doors on the public entrances, one room in each named shell. This record
covers `openspec/changes/hub-doorways`, built on branch `claude/elegant-gauss-qwjhk1`: the plan
(merged in RubenTipparach/fps-game-demo#3) and the rebuilt, rebaked hub.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb, 1280 x 720 for the stills |
| Blender | 5.2.2 LTS |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | the layout's seed 7; the stills and the video run at a fixed 30 fps |

## The checks

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core/Undercity.sln` | 205 of 205, 4 of them new: the sliding doors' timings and their validation, the hub's 24 approaches |
| Door frame | `python3 -m unittest discover -s tools/godot -p 'test_*.py'` | 16 of 16, 8 of them for `detailing.door_frame` |
| Plan | `python3 -m unittest discover -s tools/levels -p 'test_*.py'` | 30 of 30; the hub passes all three door checks, `check_sliding_room` and the z-fighting check, and a hub broken on purpose is named by each |
| Build | `blender -b --factory-startup -P tools/blender/build_undercity.py -- hub` | the eight sectors; 46 framed doors, 244 dressing doors and 7 roll-ups, 225 lights, 146,164 triangles |
| Bake | `BRUSHFIRE_BATCH=...:nav,lightmap@<each sector>` | the navmesh (5,064 polygons) and all eight sectors' lightmaps, 60 minutes; Lantern Row again after the bar's fix |
| Placement test | `placement_test.tscn` | 690 of 690: every NPC, civilian, patrol stop, spawn, ladder and accessory, the 24 approaches, and everyone on the navmesh |
| Door test | `door_test.tscn` | 10 of 10 (below) |
| Lighting, swim, UI tests | as `scripts/check.sh` | 24 of 24, 18 of 18, 312 of 312 |
| Combat test | `combat_test.tscn` | 23 of 23 (22 of 23 before the bar's fix: Tank never reached the runner) |
| Ragdoll test | `ragdoll_test.tscn` | 36 of 36 |
| OpenSpec | `openspec validate --all` | all valid |
| Dash check | CLAUDE.md section 4 | clean |

### The door test, in the hub

| Check | Result |
|---|---|
| Every public entrance has its sliding door | 18 of 18 |
| Every sliding door is timed from `data/doors.json` | trigger 3 m, wait 1.5 s, opens for `npcs` |
| Far from it, the Anchor's entrance is shut | both leaves 0.00 |
| Walking up, its leaves slide apart | both 1.00 a second after coming within 2.5 m |
| Walking away, they close behind the runner after the wait | both 0.00 |
| The Fish Hall's north entrance is shut before the walk | both 0.00 |
| The entrance is open before a person reaches it | leaves 1.00 open 0.6 m from the doorway |
| The person walks through without stopping | 0.28 m from the goal inside |

### What the tests on the built hub found

The first run on the rebuilt hub failed 24 placements, 2 door checks and 1 combat check.
- **The approach walks asked the map too soon.** Every approach read as 48-260 m off the
  navmesh: each distance was the door's own distance from the origin. Godot 4.7 syncs a
  navigation region on a worker thread, 12 frames for the hub's navmesh, and answers the origin
  until then; the test waited 3. It waits for the spawn's floor now: 24 of 24.
- **The door test's walker stopped at the first kerb,** against the kerb's edge with a normal
  55 degrees from up. It had the NPC's capsule but the default 45 degree floor and a steady
  2 m/s push down, which slides a capsule back off the edge. With the NPC scene's floor angle and
  an NPC's fall (none on the floor), 10 of 10.
- **Shot, Tank never reached the runner,** 4.9 m away. His spot behind the Anchor's bar had
  fallen off the navmesh: the aisle between the counter's short leg and the wall is 1.1 m,
  pinched to 0.9 m by a pilaster at one end and, with the back room's door framed, to 1.0 m by
  its architrave at the other, and the navmesh keeps its agent 0.4 m off everything. On the
  navmesh from before this change he stood on it and reached the street. The counter's leg ends
  at x 98.5 now, a 1.4 m aisle, and the placement test checks that every person stands on the
  navmesh.
- **Found, not this change's:** Silk in the back room behind Tank's locked door, and Skiv and
  civilian 25 on the Pit's floor, stand on the navmesh but can't walk from there to the spawn,
  on the navmesh from before this change as on this one.


## What the checks establish

- **Every door is framed, shown and reachable, by rule.** The plan refuses a door not carved at
  its frame's size, a building on walkable ground with no door, an approach that is blocked, and
  a sliding leaf with no room to open; the hub passes all of them, and each names its fault on a
  hub broken on purpose.
- **In the built level, the navmesh reaches the runner's spawn from outside every exterior
  door** (24 of 24), and every person stands on the navmesh.
- **The sliding entrances work as K2 asked:** they open as the runner walks up and close after
  the wait, and a person walking in finds the entrance open before reaching it.
- **Nothing else broke:** people's placement, combat (after the bar's fix), swimming, ragdolls,
  the character lighting and the UI pass on the rebuilt hub.

## Captures

To follow: the after stills from the before stills' viewpoints
(`docs/playtest/scripts/hub_doorways_after.json`) and the walk video
(`docs/playtest/scripts/hub_doorways_walk.json`), in `docs/screenshots/hub_doorways/`.

## What they don't

- **Frame time.** Lavapipe has no GPU, so nothing here measures what 46 frames, 244 dressing
  doors and 29 more lights cost to draw. The owner's machine is the place for that.
- **Every door by eye.** The stills show seven places and the video one walk. The checks cover
  every door by rule (framed, shown, reachable, room to open), not by look.

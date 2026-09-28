# Validation: people placed clear of the level

The owner reported Tank standing inside the Rusty Anchor's bar counter, and asked on 2026-09-28:
"npcs should have colliders on them, like capsule colliders for checking where they are in the
city, and so you should perform tests on that to ensure people are placed properly." This step
added two checks that use the game's own colliders, fixed what they found, and recorded the rule
(CLAUDE.md 7.4; `openspec/specs/level-geometry`, "People stand clear of the level" and "Every
room is carved").

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe, LLVM 20.1.2), Xvfb at 1920 x 1080 |
| Blender | 5.2.2 |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| Python | 3.11, shapely 2 |
| Seed | `BRUSHFIRE_SEED=7`; captures at `--fixed-fps 60` |

## The colliders

NPCs already had one: `scenes/undercity/npc.tscn` gives every NPC and civilian a
CharacterBody3D with a 0.35 x 1.8 m capsule, and the player a 0.4 x 1.8 m cylinder. Nothing
checked placements against them. Both checks below read those sizes from the scenes.

## The checks

| Check | What it does |
|---|---|
| `city_plan.py`, `check_standing_room` | At every NPC, civilian, patrol stop and spawn, the body's footprint against the plan's detail boxes, the stall parts and Skyway pillars (registered with `Plan.solid` where they are built), fixture and prop footprints, the rooms' air indoors, building shells and level ground outdoors; every patrol leg swept by the capsule. 2.4 s. |
| `city_plan.py`, `check_rooms_carved` | Every room and door box of an enterable building has its cutter. |
| `scenes/undercity/tests/placement_test.tscn` | Loads the eight sector glbs with the NPCs and spawn markers the importer placed, and queries each body's own collider against the physics (world and other people), then the floor under its feet (within 0.05 m). Patrol stops against the world only. Level trimeshes are one-sided, so the test counts back faces too: a body whose centre is inside a solid would otherwise touch nothing, which is how Tank first passed. |

Both run in `scripts/check.sh`: the plan checks in `--fast`, the placement test after the Godot
build.

## What they found in the committed hub

| Where | Fault | Fix |
|---|---|---|
| Tank, (97.8, 55) | Inside the Anchor's bar counter, 0.35 m deep (the owner's report) | Behind the bar beside the back-room door, (99.3, 55.5): 0.15 m clear of the counter and the wall |
| Sister Lin, the Tsang Shrine | No floor: the shrine's hall was never carved, so she stood inside a solid block | A building's sign dropped every cutter in its zone, rooms and doors included. Now only window recesses make way for a sign |
| The garage's bay, the MerSec checkpoint's room | The same sign rule left both solid | The same fix; `check_rooms_carved` now refuses an uncarved room |
| Jax, (181.5, 119.5) | In a Skyway pillar that stands inside the garage | (181.7, 119.2). The pillar inside the garage is a layout clash left as it is |
| MerSec station, (120, 31) | Astride the curb: ground 0.00-0.15 m under the capsule | (120, 30.4), on the sidewalk |
| Civilians 10, 11 and 21 | Inside stall counters and backs | Moved in front of the stalls (0.5-0.6 m) |
| Civilian 23, (60, 97) | 0.2 m into a building | (60, 97.6) |
| Spawn from the freight tunnel, (125, 162) | Inside a container stack | (125.6, 163) |
| The MerSec beat | Stop 10 in a Skyway pillar; 5 of 12 legs through buildings, a pillar or a stall | Rerouted by a grid search over the same obstacles: 19 stops, every leg clear. The beat is now read from the layout's patrol route (`hub.py`), which the design map draws, instead of a copy |

| Run | Plan check | Placement test |
|---|---|---|
| The committed hub before this step | 23 faults, and 3 uncarved rooms | 11 of 82 failed |
| After | clean | 96 of 96 passed |

The placement test's 11 failures on the old level are Tank, Lin, Jax, the station, civilians
10, 11, 21 and 23, the freight tunnel spawn, and patrol stop 10 for both patrols; with the
one-sided query it missed Tank and civilian 11, which is why it counts back faces.

## Rebuild and bake

`build_undercity.py` rebuilt the hub in 26 s. Four sector glbs changed: `lantern_row` and
`sump_market` only in their entity markers (their meshes are byte-identical), `kiln` and
`tin_stacks` in their meshes (the carved rooms). The navmesh and those two sectors' lightmaps
were baked again; the others keep their bakes.

## Captures

`docs/playtest/scripts/npc_placement.json` at 1280 x 720, on the rebaked hub. Stills in
`docs/screenshots/npc_placement/`:

| Still | Shows | Requirement |
|---|---|---|
| `01_tank_behind_the_bar.png` | Tank behind the counter beside the back-room door, the counter between him and the runner | People stand clear of the level |
| `02_tank_talking.png` | The same spot in conversation: the owner's report, fixed | People stand clear of the level |
| `03_lin_in_the_shrine_hall.png` | Sister Lin on the floor of the Tsang Shrine's hall, carved and lit | Every room is carved |
| `04_garage_bay.png` | The garage's bay, open for the first time, with its car and crates | Every room is carved |
| `05_checkpoint_room.png` | The MerSec checkpoint's room, open for the first time | Every room is carved |
| `06_civilian_at_a_stall.png` | Civilian 10 in front of a market stall instead of inside its counter | People stand clear of the level |

## What the checks establish

- Every NPC, civilian and spawn in the hub stands in free space with the floor under their
  feet, measured with their own collider, in the plan and in the built level's physics.
- Every patrol stop and leg of the MerSec beat is clear for an NPC's capsule.
- Every room and door the layout declares is carved.

## What they don't establish

- **Moving people.** The checks cover where people stand and the straight legs of a patrol; an
  NPC that turns hostile and chases, or flees, walks wherever the game sends it.
- **Props the plan doesn't describe as a box or a footprint** (lamps, railings, stairs) are only
  checked in the built level, by the placement test.
- **The pillar inside the garage.** Jax stands clear of it, but a Skyway pillar through a
  building's interior is a layout question for the level's owner.

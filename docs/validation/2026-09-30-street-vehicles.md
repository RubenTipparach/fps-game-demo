# Validation: parked vehicles in the hub

The owner, 2026-09-29: better car modelling; survey M1 to M3: our own generator, sedans, vans,
taxis and trucks, parked only. The owner, 2026-09-30: "Build them cars". This record covers
`openspec/changes/street-vehicles`, built on branch `claude/elegant-gauss-qwjhk1`
(RubenTipparach/fps-game-demo#6): the generator, the plan's placement, and the rebuilt, rebaked hub.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb, 1280 x 720 for the stills |
| Blender | 5.2.2 LTS |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | the layout's seed 7; the stills run at a fixed 30 fps |

## The checks

| Check | Command | Result |
|---|---|---|
| The table | `python3 tools/blender/vehicle_data.py` | 3 types, 10 variants, valid |
| The models | `blender -b --factory-startup -P tools/blender/build_undercity_props.py` | sedans 1,360 triangles, the taxi 1,476, vans 1,312, trucks 1,616 (budgets 2,500 and 3,500); every model clean of z-fighting; every other prop's glb byte for byte unchanged |
| Plan | `python3 -m unittest discover -s tools/levels -p 'test_*.py'` | 49 of 49, 9 of them new: every spot holds one vehicle of its size, every model parks, a truck on a car spot and a car turned across its spot are refused by name, every glb within its budget, dealing moves nothing else, and an entity named with a Godot type suffix is refused |
| Core tests | `dotnet test core/Undercity.sln` | 212 of 212, 2 of them new: the hub's 15 parked cars in its level data, and a car with no place refused |
| Build | `blender -b --factory-startup -P tools/blender/build_undercity.py -- hub` | the eight sectors and the skyline, 143,392 triangles (146,164 with the box cars); the 15 vehicles are instanced models, 21,208 triangles more |
| Bake | `BRUSHFIRE_BATCH=res://levels/undercity/hub/hub.tscn:nav,lightmap` | the navmesh (4,937 polygons; 5,064 before) and all eight sectors' lightmaps in 44 minutes |
| Placement test | `placement_test.tscn` | 705 of 705: the 690 placements of before, and all 15 parked cars where the plan put them, facing its way, with their collision |
| Every other check | `scripts/check.sh` | CHECK_RESULT |
| OpenSpec | `openspec validate --all` | all valid |
| Dash check | CLAUDE.md section 4 | clean |

## What the build found

- **Two overlaps in the first models,** refused by the z-fighting check before any glb was
  written: a truck's tail lamps on the plane of its roll-up door (the door now starts above them)
  and the taxi's chequer band 4 mm off the door seams' faces (the seams now break round it).
- **The first deal put four maroon sedans, three taxis and three rust vans on 12 car spots,** and
  no teal, grey, white or olive: one independent draw per spot. Each spot size now deals its
  variants like a shuffled deck, so all ten models park somewhere.
- **No parked vehicle reached the game on the first import.** Godot's scene importer reads
  `_vehicle` in a node's name as a node type: it imported `ENT_vehicle_008` as a VehicleBody3D
  named `ENT_008` with the empty under it, and the level importer freed both, stopping three
  sectors' import scripts with "previously freed". The entities are `ENT_car_<n>` now, and the plan
  refuses any entity name carrying one of Godot's type suffixes.
- **A headless `godot --import` imported the rebuilt sectors before the vehicles' new textures,**
  so loading a vehicle failed inside the sectors' import. The textures were imported by the next
  editor session; the sectors were then imported again, cleanly. A rebuild that adds prop textures
  should import the prop kit's output before building the level.
- **Rebuilding the prop kit rewrites every prop's import preset without the `path=` lines** Godot's
  runtime reads, so the game can't load the kit's props until the editor imports them again. The
  committed presets are the ones the editor wrote.

## Captures

In `docs/screenshots/street_vehicles/`:

- `vehicles_sheet.png`: the ten models (`render_undercity_props.py -- vehicles`).
- `look_gate_cars.png`, `look_gate_vans.png`: our sedan, taxi, van and truck beside Kenney Car
  Kit's (CC0), each scaled to ours, in one light. The Kenney models were used for this render only
  and are not in the repository; Quaternius's host is out of this container's reach. Survey O1.
- `before_01` to `before_05`: the box cars, from `docs/playtest/scripts/street_vehicles_before.json`
  on the hub as committed at f6cd25c.
- `after_01` to `after_05`: the same viewpoints on the rebuilt hub
  (`docs/playtest/scripts/street_vehicles_after.json`).

## What the checks establish

- **Every car spot holds one generated model that fits it,** read from the committed glb, by rule
  in the plan and in the built level: the placement test finds all 15, each where and as the plan
  put it, with its collision.
- **Each model keeps to its triangle budget and has no coplanar overlapping boxes.**
- **Nothing else in the hub moved:** against the committed plan only the box cars are gone, and
  people's placement, the doors, combat, swimming, the character lighting and the UI pass on the
  rebuilt hub.

## What they don't

- **Frame time.** Lavapipe has no GPU, so nothing here measures what 15 instanced vehicles, 21,208
  triangles in all, cost to draw. The owner's machine is the place for that.
- **The look.** The stills show five places and the sheet ten models; whether the owner keeps
  this look is survey O1.
- **The bake time is not a comparison.** The hub-doorways bake took 60 minutes on another day; this
  one took 44. Neither was timed against the other in one sitting.

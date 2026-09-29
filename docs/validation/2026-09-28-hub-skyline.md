# Validation: Meridian's towers around Low Harbor

The owner, playtesting the hub on 2026-09-28, found the sky over the slum empty: rooftops, then
fog. The survey settled that every tower is a mesh with its own haze (I7) and the scale as
designed, with searchlights (I8), and built this fourth (I1). This record covers
`openspec/changes/archive/2026-09-29-hub-skyline`, built on branch `claude/elegant-gauss-qwjhk1`.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb |
| Blender | 5.2.2 |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Python | 3.11, shapely 2, numpy |
| Seed | `BRUSHFIRE_SEED=7` for the capture; nothing in the skyline is random (tower seeds come from their ids) |

## The checks

| Check | Command | Result |
|---|---|---|
| Level plan | `python3 tools/levels/city_plan.py hub --stats` | passes: the skyline's four rules, z-fighting clean in the skyline sector (111 boxes) |
| Plan tests | `python3 -m unittest discover -s tools/levels -p 'test_*.py'` | 23 of 23, 10 of them the skyline's (below) |
| The rest of the hub | the plan's eight other sectors compared as JSON with the committed plan | identical: their glbs, lightmaps and navmesh stand |
| Skyline build | `blender -b --factory-startup -P tools/blender/build_undercity.py -- hub --sector skyline` | 2,556 triangles in 3 objects and 5 surfaces |
| Godot import | `godot --headless --path game --import` | clean; the skyline glb imports with no lightmap UVs (`light_baking=0`) |
| Project build | `dotnet build` in `game/` | 0 warnings, 0 errors |
| Placement, swim, combat, UI, lighting tests | as `scripts/check.sh` | 434 of 434, 18 of 18, 23 of 23, 312 of 312, 15 of 15, with the skyline sector and the searchlights in the hub |
| OpenSpec | `openspec validate --all` | all valid |

### The skyline's tests

| Test | Pins |
|---|---|
| The hub's skyline keeps every rule | bounds, coverage, overlaps, budget on the real layout |
| A tower inside the margin is refused by name | Pier Nine at its first place, 20 m off |
| A horizon without tall towers fails naming the bearings | the slice 0-30 degrees, with every tower bearing into it removed |
| Overlapping towers are refused | a tower laid over the Spire |
| A skyline over its triangle budget is refused | 260 extra arcologies |
| A neon the palette lacks is refused by name | Sable Mutual's band as "teal" |
| A searchlight above its tower is refused by name | the Spire's lamps at 460 m |
| The Spire's lamps stand off its needle | both 1.5 m off the needle's faces at 420 m |
| Every part and role survives 8-bit colour | all 4 parts x 8 roles decode after 8-bit quantisation |
| The shader decodes with the same numbers | reads `skyline_tower.gdshader`: the code scale, the role count, the palette's size, the parts it branches on |

## What building found

Each is in the design's "Found in building".

- **One material, not one per part.** A material per part came to 11 surfaces against the
  design's 6 draw calls. One `skyline` material, reading the part and neon role from the vertex
  colour, gives 5.
- **A tower's neon windows now use the tower's own neon**, which a material per part couldn't
  know.
- **Billboards are the skyline shader's**, not the foundation wall's material: the scene fog
  leaves 7-15 % of that at Harrow Tower's distance.
- **The hub scene's generator now keeps the last bake.** Writing `hub.tscn` again (for the
  skyline sector) would have dropped every sector's link to its `.lmbake` and the navmesh's to
  `hub_navmesh.res`, which the editor adds when it bakes. The generator links both when the
  files exist. Written again, the scene also drops two bake-only light copies that the water
  work's geometry no longer needs; they are never drawn, so nothing changes on screen until the
  next bake.

## Captures

`docs/screenshots/hub_skyline/hub_skyline.mp4` comes from `docs/playtest/scripts/hub_skyline.json`,
written with `--write-movie` at 30 fps with seed 7: 351 frames, 11.7 s, rendered in 17 minutes on
lavapipe at 1600 x 900 with the 3D view at 0.67 scale, encoded to H.264 at 1280 x 720. The run
quit with exit 0 and logged no errors. The stills beside it, with the baseline's two views from
the change's write-up:

| Still | Shows | Requirement |
|---|---|---|
| `baseline_north_from_market.png`, `01_north_from_market.png` | North from the Sump Market, before and after: empty fogged sky over the foundation wall, then towers with lit windows filling it | The skyline reads as dark towers with lit windows |
| `baseline_east_over_the_cut.png`, `02_east_over_the_cut.png` | East over the Cut, before and after: towers stand behind the Drydock's roofs | Towers surround the hub |
| `03_west_over_tin_stacks.png` | West from the market: a stall's awning and its lamp fill most of the frame; the western towers show at its left edge. The view isn't the design's "wall of lit windows"; still 04 is | Towers surround the hub |
| `04_skyway_deck_west.png` | From the Skyway deck, 14 m up: the Kosei Stacks' wall of lit windows | The skyline reads as dark towers with lit windows |
| `05_searchlights_a.png`, `06_searchlights_b.png` | Due south of the Spire, 8 s apart: its cyan halo, one beam rising, the other flaring at the crown where it points toward the camera | Searchlights sweep the sky |

The first run's west view faced a nearby wall and its searchlight view left the Spire's crown
above the frame; both views were moved and the whole video taken again.

**Draw calls.** The `render_stats` step logged the whole frame:

| View | Draw calls | Primitives | Objects |
|---|---|---|---|
| North from the market | 4,766 | 954,746 | 5,152 |
| East over the Cut | 6,883 | 1,106,936 | 7,153 |
| West from the market | 463 | 174,844 | 771 |
| The Skyway deck | 2,730 | 746,023 | 2,967 |

The skyline's own share is at most 7 draw calls per pass (5 surfaces and 2 beams, casting no
shadows) and 2,556 triangles; the rest is the hub as it was. There is no before count from the
baseline run, which predates the step.

## What the checks establish

- The layout's towers surround the hub by the four rules, and a layout that breaks one is
  refused before anything is built.
- The skyline sector is built from the layout, merged to 5 surfaces, and loads in the hub with
  no lightmap, no shadows, no collision and no navmesh, beside every existing system's tests.
- In the capture, towers fill the sky above the hub's roofs in every direction shown, and the
  Spire's searchlights rise and sweep.

## What they don't establish

- **The whole horizon, seen.** The coverage rule is checked on the layout for every 30-degree
  slice; the capture shows four directions.
- **How the windows hold up close.** The windows are procedural and the same size on every
  tower; seen from the Skyway deck they read as a dense field of lit cells.

- **Frame cost.** Lavapipe doesn't measure it. The skyline is 2,556 unshaded triangles in 5
  surfaces, and the two beams are two more draw calls; the far plane moved from 400 m to
  1,500 m.

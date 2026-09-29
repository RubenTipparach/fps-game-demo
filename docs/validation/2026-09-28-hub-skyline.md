# Validation: Meridian's towers around Low Harbor

The owner, playtesting the hub on 2026-09-28, found the sky over the slum empty: rooftops, then
fog. The survey settled that every tower is a mesh with its own haze (I7) and the scale as
designed, with searchlights (I8), and built this fourth (I1). This record covers
`openspec/changes/hub-skyline`, built on branch `claude/elegant-gauss-qwjhk1`.

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

(filled from the capture run)

## What the checks establish

- The layout's towers surround the hub by the four rules, and a layout that breaks one is
  refused before anything is built.
- The skyline sector is built from the layout, merged to 5 surfaces, and loads in the hub with
  no lightmap, no shadows, no collision and no navmesh, beside every existing system's tests.

## What they don't establish

- **Frame cost.** Lavapipe doesn't measure it. The skyline is 2,556 unshaded triangles in 5
  surfaces, and the two beams are two more draw calls; the far plane moved from 400 m to
  1,500 m.

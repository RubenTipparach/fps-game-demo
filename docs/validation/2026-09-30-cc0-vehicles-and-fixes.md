# Validation: the hub's cars from the PSX pack, parked on one ground and baked with it

The owner, 2026-09-30: the cars were "a little dark in game, the wheels dont align" and had no
shadow under them; "cars should be static meshes so we get it nice light baking"; "kenney is a
nogo"; "yea psx cars are nice, I'd want a consistent art style"; survey O7 "no need for trucks now,
just use vans" and O8 "smudge those textures, background cars can use bilinear filtering". This
record covers `openspec/changes/archive/2026-09-30-cc0-vehicles` and `openspec/changes/archive/2026-09-30-vehicle-fixes`, built on branch
`claude/elegant-gauss-qwjhk1` (RubenTipparach/fps-game-demo#6).

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb, 1280 x 720 for the stills |
| Blender | 5.2.2 LTS |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | the layout's seed 7 |

## The checks

| Check | Command | Result |
|---|---|---|
| The pack's pin | `python3 tools/deps/fetch_character_tools.py --verify` | 4 packs, PSX Style Cars among them, SHA-256 `db67b0b0...699e4` matches |
| The conversion | `blender -b --factory-startup -P tools/blender/build_vehicles_cc0.py` | 7 bodies, 22 variants, 312-476 triangles (budget 2,500); lengths to 1 cm of the table; the triangle-level z-fighting check clean after mending one 1.7 mm sliver under Car 5's bumper (4 vertices); the scale 0.70871 m a unit from the pack's wheel |
| The table | `python3 tools/blender/vehicle_data.py` | valid; every model and texture committed; texture albedo 0.041-0.327, inside 0.03-0.8 |
| Plan | `python3 -m unittest discover -s tools/levels -p 'test_*.py'` | 60 of 60, among them: every spot 5.6 x 2.6 m and holding one car, 15 different cars, each fitting its spot on one ground, a spot across a kerb and a too-long car refused by name, each car a model of its ground's sector with its contact shadow sized from the glb, the table's pin, bodies, folders and albedo |
| Tools | `python3 -m unittest discover -s tools/godot` | the coplanar triangle check's 5 tests among 21 |
| Core | `dotnet test core/Undercity.sln` | 212 of 212: the hub's 15 cars, 15 models |
| Build | `build_undercity.py -- hub` | 149,554 triangles; the 15 cars 6,162 of them (the generated cars were 21,208) |
| Bake | `BRUSHFIRE_BATCH=res://levels/undercity/hub/hub.tscn:nav,lightmap` | the navmesh (4,993 polygons) and all eight sectors in 43 minutes |
| Placement test | `placement_test.tscn` | 705 of 705: every car a static mesh of the sector that owns its ground (14 in the streets', the garage's van in the kiln's), where and as the plan put it, with its body, a ray under it landing on its own sector's ground, a user of that sector's lightmap, over its contact shadow sized to its mesh |
| Combat test | `combat_test.tscn` | 23 of 23 after a fix to the test (below) |
| Lighting test | `lighting_test.tscn` | 29 of 29 |
| Every check | `scripts/check.sh` | all passed on the rebaked hub (with street-puddles' ground): placement 705, UI 312, swimming 18, combat 23, lighting 29, sliding entrances 10 |
| OpenSpec | `openspec validate --all` | all valid |
| Dash check | CLAUDE.md section 4 | clean |

## What the build found

- **The pack had one flaw:** Car 5 and its taxi lap the ends of the front bumper's underside over
  its middle by 1.7 mm, facing the road. The new triangle-level check found it; the converter mends
  slivers under 5 mm and refuses anything larger.
- **The kerb rule moved two rows,** not one: Lantern Row's six spots onto the road as designed, and
  Quay Road's five, whose 2.6 m spots caught the quay's raised edge, 0.2 m off it.
- **On the road the cars stood in the MerSec pair's beat;** the standing-room check refused it, and
  the beat moved to Lantern Row's north half.
- **The combat test's kill check stood the runner behind a parked car.** It checked a clear line
  eye to eye, over the black sedan's roof, but shot at the chest, into the car (20 of 23). It now
  also requires a clear line from the runner's eye to the point it aims at.
- **The placement test couldn't tell sectors apart:** every sector glb's root is named after the
  level. It names each loaded sector after its file.
- **The bake held a shadow the picture didn't show.** In Godot's lighting-only view the ground
  under a car reads 0.47-0.67 of the ground beside it; in the finished picture the wet road's
  reflections hid it. So the contact shadow (survey O3), made for a wet street: a decal that
  darkens, dries and occludes the ground under each car.
- **The shadow instrument's first numbers were wrong.** A mean over a top-down still counted the
  HUD's crosshair, which sits right over the car; at night the ground is about 0.002 linear, so a
  few white pixels outweighed it (0.84-2.70). It takes medians since.

## The shadow, measured

`tools/measure/car_shadow.py` on stills from 7 m above each outdoor car, with the car and with it
hidden: the ground between the wheels over a band 0.3-1.3 m out, medians of linear luminance.

| | Lighting only (the bake, no decal) | Finished picture, first decal | Finished picture, the decal as built |
|---|---|---|---|
| Cars | 4 | 14 | 14 |
| Under over beside | 0.47-0.67 | 0.32-0.69 | 0.30-0.63, one 0.81 |

Under every car the ground reads at the darkest value a still holds, about 5 of 255. Where the
ratio is over 0.6 the road beside is itself about 7 of 255 (Quay Road, and the sedan by Pachinko
Sunrise), and the 0.81 is a capture in which the ground beside the car had changed with the
flickering signs. The design's 0.6 is met where the road is lit.

## Captures

In `docs/screenshots/cc0_vehicles/`: `vehicles_sheet.png`, the 22 converted models at night;
`cc0_candidates.jpg`, `cc0_gate_night.png`, `psx_pack_night.png`, the choice.

In `docs/screenshots/vehicle_fixes/`: `before_01` to `before_05`, the generated cars
(`docs/playtest/scripts/vehicle_fixes_before.json`); `after_01` to `after_08`, the same five places
and three more (Lantern Row's row, Quay Road's row, the garage's bay;
`docs/playtest/scripts/vehicle_fixes_after.json`); `before_after.jpg`; `contact_shadow.jpg`, four
cars from above, with the car and hidden, brightened threefold.

## What the checks establish

- **Every parked car is a PSX Style Cars model from the pinned pack,** converted by rule, within
  budget, without coplanar overlapping faces, recorded with its pack, author, licence and hash.
- **Every car fits its spot and stands on one ground,** by rule in the plan, and in the built level
  as a static mesh of the sector that owns its ground, baked in that sector's lightmap.
- **Each car has a contact shadow** sized to its own mesh.

## What they don't

- **Frame time.** Lavapipe has no GPU; nothing here measures what 15 cars and their decals cost.
- **The look,** beyond the owner's word on the stills (2026-09-30: "ok looks good", "new cars are
  dope"): the stills show eight places and the sheet 22 models.
- **The shadow's strength everywhere.** The measure covers the 14 outdoor cars from above, at seed
  7, in one sitting; the garage's van under its roof isn't measured.

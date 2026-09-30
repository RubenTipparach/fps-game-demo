# Validation: puddles where water gathers, drawn by the ground's shader

The owner, 2026-09-29: "can you make water puddles on the street less random? maybe use decals?";
survey L1 to L3: the recommended rules and amount, and "ripples would be awesome, this should just
be a shader effect, simple cheap"; 2026-09-30: "the street puddle pattern isn't fixed yet". This
record covers `openspec/changes/archive/2026-09-30-street-puddles`, built on branch `claude/elegant-gauss-qwjhk1`
(RubenTipparach/fps-game-demo#6): the plan's puddles (built earlier), the ground textures without
puddles, the ground's shader, the shared ripple, the gully decals, and the rebaked hub.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb, 1280 x 720 |
| Godot | 4.7.2 stable, mono |
| .NET | 8.0.425 |
| Seed | the layout's seed 7; the stills and the video at `--fixed-fps 30` |

## The checks

| Check | Command | Result |
|---|---|---|
| The ground holds no standing water | `python3 -m unittest discover -s tools/fx` (new in `scripts/check.sh`) | 2 of 2: no texel under roughness 0.2 (the least is 0.49 on asphalt, 0.34 on paving; before, 27.6 % and 10.6 % of texels); the means still read rain-wet |
| Where the puddles lie | `python3 -m unittest discover -s tools/levels` | 60 of 60, among them the plan's puddle rules (under the Skyway and on a kerb refused by name, every long kerb with a gully and three gutters, placing puddles moves nothing else) and the mask's 4 tests against the plan |
| In the rain | `dotnet test core/Undercity.sln` | 212 of 212, among them 5 on the puddles: every one of the hub's 253 in the rain by `Wetness.Sheltered` |
| One ripple | `python3 -m unittest discover -s tools/godot` | 21 of 21, among them 3 new: the canal and the ground include `rain_ripples.gdshaderinc` and define none of their own, the ground's .tres carry the water's numbers, and project.godot's rect is empty |
| The shader materials | `python3 -m unittest discover -s tools/material_maker` | 3 of 3: the ground's .tres are what `postprocess.py` writes from `materials.json` |
| The level hands the mask over | `lighting_test.tscn` | 29 of 29: the hub hands its puddles to the ground's shader as it loads, the mask loads (1920 x 1360 over 240 x 170 m), and the asphalt and paving are the ground shader's |
| The shader reproduces the material | the equivalence capture, puddles off | the same Lantern Row view with `city_ground.gdshader` and with the `ORMMaterial3D` it replaces, both on the new textures: 0.60 luma levels of mean difference (the design asks under 1); the 99th percentile, 14 levels, is the rain's streaks, random each run |
| The canal is unchanged | the canal view before and after its rings moved into the include | no difference in the water outside the rain's streaks; the quay and road round it changed with their textures, and the glow round the near lamp with the puddle spots it no longer reflects in |
| Bake | `BRUSHFIRE_BATCH=res://levels/undercity/hub/hub.tscn:nav,lightmap` | 43 minutes; the streets, kiln and skyway lightmaps changed with the ground's albedo, the other five byte for byte the same |
| Every check | `scripts/check.sh` | all passed on the rebaked hub: placement 705, UI 312, swimming 18, combat 23, lighting 29, sliding entrances 10 |
| OpenSpec | `openspec validate --all` | all valid |

## What the build found

- **Four globals, not two.** The mask's decoding numbers (`range_m`, `height_m`) go to the shader
  from the level data too, so the writer and the shader can't disagree.
- **A headless run keeps no shader globals:** Godot's dummy renderer returned zeros for every
  global the level set, so the lighting test reads what the level handed over (`PuddleShading.Applied`)
  and the captures show the renderer drawing it.
- **Scenes are generated:** the gully's decal and the car's contact shadow come from
  `gen_undercity_scenes.py`, as every scene under `scenes/` (CLAUDE.md 11).
- **253 puddles, not the 254 first built:** vehicle-fixes moved Lantern Row's parked cars onto the
  road, and one gutter puddle there no longer keeps 0.3 m from a car; 155 gutter, 41 gully and 57
  drip puddles, 431 m² (2.51 % of the ground).
- **The capture's crash at quit** (exit 139 after the last still, on lavapipe) cost nothing: every
  still and frame was written first.

## Captures

In `docs/screenshots/street_puddles/`, from `docs/playtest/scripts/street_puddles_{before,after}.json`
at seed 7 and 30 fps, before with the old ground materials and canal shader, after on the rebaked hub:

| Still | Shows | Requirement |
|---|---|---|
| `before_01` / `after_01_lantern_row.png` | before, the texture's puddles repeat across the whole road; after, the road is wet asphalt and the water lies along the gutters at both kerbs, mirroring the neon | Puddles lie where water gathers |
| `before_02` / `after_02_clinic_gully.png` | Clinic Lane's kerb; the gully isn't in the frame from street level (see below) | the same |
| `before_03` / `after_03_skyway_garage.png` | under the Skyway at the garage: dry after | the same (no puddle under a roof) |
| `before_04` / `after_04_market_drip.png` | the market's stall awnings | the same |
| `before_05` / `after_05_canal.png`, `canal_after_include.png` | the canal from Quay Road | Standing water ripples with the rain |
| `equivalence_ground_shader.png`, `equivalence_orm_material.png` | the ground shader and the material it replaces, puddles off | the shader reproduces the material |
| `rain_on_the_gutters.mp4` | 6.9 s, 1280 x 720, with sound (`street_puddles_rain.json`, `--write-movie`): the rain on Lantern Row's gutter puddles under the neon | Standing water ripples with the rain |

The screen-space reflections show the neon in a puddle: the cyan sign's reflection in the gutter
in the video and in `after_01`; `lantern_row_before_after.jpg` puts that pair side by side.

**No still shows a gully grate clearly.** Views from above failed: a puddle mirrors the dark night
sky and reads as black as the wet road round it. So did a low view of the Clinic Lane gully (a
faint reflection, the grate unreadable) and of the market's drip line (the camera stood inside an
awning). The gullies are checked by the plan's tests and the mask's; how a grate looks in the game
is not shown here.

## What the checks establish

- **The ground's textures hold no standing water,** and every puddle is one the plan placed by its
  rules, in the rain by the core's rule, and drawn where the mask says at its own height.
- **The ground shader draws the ground as its old material did** (0.60 luma levels), with the
  puddles on top.
- **One ripple function and one set of numbers** for the canal and the puddles.

## What they don't

- **Frame time.** Lavapipe has no GPU; the design's cost estimate (one texture read and a compare
  outside the puddles) is not measured, nor the heaviest view's clustered elements.
- **The ripples' look in motion at full size** beyond the one 6.9 s video; whether they read well
  is the owner's call.
- **The bake's darkening by the puddles.** The bake runs in the editor with no mask set, so it
  bounces the dry ground's albedo, as the design accepted.

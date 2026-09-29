# Proposal: puddles where water gathers, rippling in the rain

## Why

The owner, 2026-09-29: "can you make water puddles on the street less random? maybe use decals?"

**How puddles are made today.** They are not objects. `tools/fx/generate_city_materials.py`
paints them into the two ground textures, by thresholding seeded noise:
- `asphalt` (the roads): `puddle = clip((fbm - 0.56) * 9)` darkens the albedo and drops the
  roughness to 0.05;
- `paving_wet` (sidewalks and squares): the same with a 0.6 threshold.

Every street face takes world-space UVs (`tools/blender/blendkit.py`, `world_uv`). So the same
blobs repeat every texture tile, wherever the tile falls: on the crown of the road, on kerb tops,
against walls, and under roofs.

**Measured** on the committed textures and the hub's plan (design section 2):

| | Asphalt | Paving |
|---|---|---|
| Surface reading as standing water (roughness under 0.35 and 0.2) | 27.6 % | 10.6 % |
| The pattern repeats every | 4 m | 2 m |
| Ground it covers in the hub | 3,606 m² | 13,558 m² |
| Standing water | 995 m² | 1,437 m² |
| Of which under a roof, where no rain falls | 93 m² | 235 m² |

In all, 2,432 m² of the hub's ground, 14.2 %, is painted as standing water, in a grid. 328 m² of
it lies under the Skyway's deck, the awnings and the walkways, which since
`character-lighting` the game treats as dry (a character standing there dries).

So the puddles are not random so much as **placed by nothing**: a grid of blobs that ignores the
kerb, the walls and the roofs. The design mockup (the page's section F20) draws one 48 x 30 m
stretch round the garage both ways.

## What Changes

The survey's answers (2026-09-29): L1 and L2 "recommended"; L3 "ripples would be awesome, this
should just be a shader effect, simple cheap". A decal takes textures and runs no shader, so the
puddles are drawn by the ground's shader instead, and they ripple.

- **The ground textures lose their puddles.** Asphalt and paving keep a wet sheen with a little
  variation, and no standing water.
- **Puddles become a term in the ground's shader.** The two ground materials become one shader,
  `city_ground.gdshader`, which draws the ground as today's material does and, inside a puddle,
  darkens it, makes it a mirror and ripples it. It reads where the puddles are from a mask the
  level plan writes. There is no geometry to z-fight, and no repeat.
- **Rain rings, one for all the rain.** The canal's ripple code moves into one include that both
  the canal and the ground use, with the canal's numbers, so a drop reads the same wherever it
  lands (L3).
- **The level plan places them where water gathers,** by rule, from its own shapes (L1):
  - in the **gutters**, along the kerbs, in the rain;
  - under the **drip edges** of the awnings and the Skyway's deck;
  - round new **kerb gullies** (drain grates, drawn as decals), one every 25 m of kerb.

  Never under a roof, never over a kerb top or a stair, and never within reach of a wall. The
  choices come from a seeded stream of their own, so nothing else in the hub moves.
- **About 385 puddles, 451 m², 2.6 % of the ground** instead of 14.2 % (L2).
- **The design map** draws them, from the same plan, so the map and the level agree
  (CLAUDE.md 7.1).
- **Checks:**
  - the plan refuses a puddle under a roof, off the open ground, or overlapping another;
  - a texture test refuses standing water in the ground textures;
  - a test reads the committed mask against the plan;
  - a test pins the one ripple function and its one set of numbers;
  - the in-engine placement test checks every puddle against the core's shelter rule.

## Capabilities

### Modified Capabilities

- `level-geometry`: a requirement that puddles lie where water gathers and nowhere else, and one
  that standing water ripples with the rain.

## Impact

- `tools/fx/generate_city_materials.py`: the puddle terms leave `asphalt` and `paving_wet`; the
  gully grate's decal maps are added.
- `game/shaders/rain_ripples.gdshaderinc` (new, from `water.gdshader`) and
  `city_ground.gdshader` (new); `water.gdshader` includes the ripples.
- `tools/material_maker/postprocess.py` and `materials.json`: the ground materials become shader
  materials that name `"ripples_from": "water"`.
- `tools/levels/city_plan.py`: puddle placement, the gullies, `check_puddles`, the mask writer.
- `tools/levels/render_map.py`: puddles on the design map.
- `tools/levels/export_level_data.py`: the puddles and the mask's rect in the level data.
- `game/project.godot`: the `puddle_mask` and `puddle_rect_m` shader globals; the level sets them
  on load.
- `tools/godot/gen_undercity_scenes.py` and `blender_level_import.gd`: the gully decal.
- A rebuild of the hub's sectors; the lightmaps are baked again, since the ground textures'
  albedo changes what the bake bounces.
- `game/scripts/Undercity/Checks/PlacementTest.cs`: the puddles against the shelters.

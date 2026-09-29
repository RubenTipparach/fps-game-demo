# Proposal: puddles where water gathers, as decals

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

- **The ground textures lose their puddles.** Asphalt and paving keep a wet sheen with a little
  variation, and no standing water.
- **Puddles become decals** (Godot's `Decal` node): a small set of puddle shapes projected onto
  the ground. They darken it and make it glossy through the decal's albedo and ORM maps. There is
  no geometry to z-fight, and they fade out with distance.
- **The level plan places them where water gathers,** by rule, from its own shapes:
  - in the **gutters**, along the kerbs, in the rain;
  - under the **drip edges** of the awnings and the Skyway's deck;
  - round new **kerb gullies** (drain grates, also decals), one every 25 m of kerb.

  Never under a roof, never over a kerb top or a stair, and never within reach of a wall. The
  choices come from a seeded stream of their own, so nothing else in the hub moves.
- **About 385 puddles, 451 m², 2.6 % of the ground** instead of 14.2 % (the owner's survey L2
  asks about the amount).
- **The design map** draws them, from the same plan, so the map and the level agree
  (CLAUDE.md 7.1).
- **Checks:**
  - the plan refuses a puddle under a roof, off the open ground, or overlapping another;
  - a texture test refuses standing water in the ground textures;
  - the in-engine placement test checks every puddle against the core's shelter rule.

Not in this change: **animated rain ripples.** A decal can't run a shader, so a ripple needs
the ground shaders instead. Survey L3 asks whether to do that next.

## Capabilities

### Modified Capabilities

- `level-geometry`: a requirement that puddles lie where water gathers and nowhere else.

## Impact

- `tools/fx/generate_city_materials.py`: the puddle terms leave `asphalt` and `paving_wet`; the
  puddle and gully decal textures are added.
- `tools/levels/city_plan.py`: puddle placement, the gully decals, `check_puddles`.
- `tools/levels/render_map.py`: puddles on the design map.
- `tools/godot/gen_undercity_scenes.py`: a decal scene per puddle shape and one for a gully.
- `game/addons/brushfire_tools/blender_level_import.gd`: `ENT_puddle` and `ENT_gully` become
  decals.
- A rebuild of the hub's sectors; the lightmaps are baked again, since the ground textures'
  albedo changes what the bake bounces.
- `game/scripts/Undercity/Checks/PlacementTest.cs`: the puddles against the shelters.

# Design: puddles where water gathers, rippling in the rain

## Context

The owner, 2026-09-29: "can you make water puddles on the street less random? maybe use decals?"

The survey's answers, 2026-09-29:
- **L1** (where puddles form): "recommended". Gutters, drip edges and gullies.
- **L2** (how much): "recommended". About 2.6 % of the ground, by the rules.
- **L3** (ripples): "ripples would be awesome, this should just be a shader effect, simple cheap".

L3 decides the method. A Godot `Decal` projects texture maps and runs no shader, so a decal
puddle can't ripple (section 3.2). The puddles are therefore drawn by the ground's own shader,
from a mask the plan writes, and they ripple with the same rain rings the canal already has.
The placement rules and the amount are the ones proposed.

The hub always rains. Since `character-lighting`, a roof (a building, an awning, a kiosk, the
Skyway's deck, a walkway) keeps a character dry: the plan registers 414 of them
(`Plan.shelter`), and the core decides who stands under one. The street's puddles don't know
about any of that.

## 1. How puddles are made today

`tools/fx/generate_city_materials.py` writes the ground textures (seeded, so the same files every
run):

- **`asphalt`** (roads, `tile_m` 4.0): `puddle = clip((fbm(3, 6, 12) - 0.56) * 9, 0, 1)`. Inside a
  puddle, the albedo is 35 % darker and the roughness falls from about 0.6 to 0.05, and the
  normal loses its grain.
- **`paving_wet`** (sidewalks and squares, `tile_m` 2.0): `clip((fbm(2, 4, 8) - 0.6) * 8, 0, 1)`,
  30 % darker, roughness down by 0.28.

Every face takes world-space UVs (`blendkit.world_uv`: a top face's u is x / tile, v is y /
tile), so the mask repeats on a 4 m and a 2 m grid across the whole hub. Both are
`ORMMaterial3D`s (`game/materials/asphalt.tres`, `paving_wet.tres`), written by
`tools/material_maker/postprocess.py` from `materials.json`.

## 2. Measured

On the committed textures (`game/textures/asphalt_orm.png`, `paving_wet_orm.png`, the ORM green
channel), and on the hub's plan at seed 7 (`city_plan.build("hub")`: `street` less the rail for
the asphalt, `paved` and `plaza` for the paving, `Plan.shelters` for the roofs):

| | Asphalt | Paving | Hub |
|---|---|---|---|
| Reads as standing water | 27.6 % (roughness under 0.35) | 10.6 % (under 0.2) | |
| Ground | 3,606 m² | 13,558 m² | 17,164 m² |
| Standing water | 995 m² | 1,437 m² | **2,432 m², 14.2 %** |
| Ground under a roof | 336 m² (9.3 %) | 2,218 m² (16.4 %) | |
| Standing water under a roof | 93 m² | 235 m² | **328 m²** |

Where water would gather, from the same plan:

| Place | Length in the rain |
|---|---|
| Kerbs: the road's edge where it meets a sidewalk (1,856 m in all; 199 m under a roof) | 1,657 m |
| The Skyway deck's edges over open ground | 286 m |
| The awnings' outer edges over open ground (not the edge against the wall) | 322 m |

The mockup (`tools/design/mockup_puddles.py`, the page's F20) draws x 144-192, y 102-132 m round
the garage: today's grid runs straight under the deck; the rules below leave the deck dry and
put the water along the kerbs and the deck's edges.

**The canal already ripples.** `game/shaders/water.gdshader` (from `water-and-swimming`) draws
rain rings procedurally: one drop at a time in each 0.9 m cell, 0.7 drops a second, each ring a
damped sine that widens across its cell and fades as it ages (`ripples()`, a 3 x 3 loop over
the neighbouring cells, no texture read). Its five numbers are the water's `shader_params` in
`materials.json`.

## Goals / Non-Goals

**Goals:**
- A puddle is where rain would gather: in the gutters, under drip edges, round drains.
- None under a roof, on a kerb top, on a stair, or against a wall.
- No repeating pattern.
- Every puddle ripples in the rain, the same rain as the canal's.
- The map and the level agree, and a check refuses a puddle in the wrong place.

**Non-Goals:**
- Puddles in the other levels (the Drains, the Yard): they have no rain yet. With no mask set,
  the ground shader draws no puddles.
- Dry ground under roofs. The ground there keeps the wet sheen; the same mask could carry a
  "sheltered" channel later.
- Characters' footsteps splashing: a separate audio change.

## Decisions

### 3.1 Ground textures without puddles

`asphalt` and `paving_wet` lose their `puddle` term, and nothing else changes:
- the base colour, grain, cracks and slab joints stay;
- the roughness keeps its variation (asphalt 0.45-0.65, paving 0.30-0.44), so the ground still
  reads as rain-wet.

A texture test reads the committed ORM maps and refuses any texel under roughness 0.2 in either
(CLAUDE.md 5.6, "validate the real artifact").

### 3.2 Puddles are drawn by the ground's shader, not decals

Godot's `Decal` projects albedo, normal, ORM and emission maps onto whatever lies inside its box
(Godot manual, "Using decals"). It takes textures, not a shader, so a decal puddle is a still
mirror. A ripple would need its normal map animated from outside the decal, which is the
opposite of the owner's "just a shader effect, simple cheap" (L3).

So the two ground materials become one shader, `game/shaders/city_ground.gdshader`, and the
puddles are a term in it:

1. **It draws the ground exactly as the `ORMMaterial3D` does today:** the albedo map, the ORM map
   (roughness from green, metallic from blue, occlusion from red, `ao_light_affect` 0.2), the
   normal map at the material's `normal_scale` (0.8 asphalt, 0.9 paving), specular 0.5,
   anisotropic mipmapped filtering, the mesh's own UVs. A capture checks the two agree
   (section 3.7).
2. **It reads the puddle mask** at the fragment's world x and z (section 3.4). Inside a puddle,
   by `wet` from 0 to 1:
   - the albedo darkens to 0.65 of itself on asphalt and 0.7 on paving (today's texture numbers);
   - the roughness falls to 0.04, a mirror to the screen-space reflections and the probes;
   - the ground's normal fades to flat, and the rain rings are added (section 3.3).
3. **Only where the puddle lies:** the fragment must face up (its world normal's y over 0.9) and
   sit within 0.03 m of the puddle's own height (the mask's second channel). A kerb top
   (0.15 m up), a kerb face or a deck over the same x and z is drawn dry even where the mask's
   soft edge reaches it.
4. **An organic edge:** `wet` is a smoothstep over 0.04 m of the distance, after a small value
   noise (0.05 m, on a 0.3 m wavelength) moves the edge, so no puddle reads as a perfect ellipse.

Its numbers are the materials' `shader_params` in `materials.json`, written into the `.tres` by
`postprocess.py` as the water's already are; `write_shader_material` gains the albedo and ORM
maps for a shader that declares them. Nothing is tuned inline.

The shader does the puddle work only inside a puddle: outside, `wet` is 0 and it skips the
ripples' loop. Puddles cover 2.6 % of the ground, so for most of the ground the cost over today
is one texture read and a compare.

**The gully grate stays a decal.** It doesn't move, a decal can't z-fight, and it draws over the
puddle beneath it (Godot applies decals after the material's fragment). There are 66 of them;
with the lights and probes in view, far under the 512 clustered elements.

### 3.3 One ripple for all the rain

The canal's `ripples()` moves into `game/shaders/rain_ripples.gdshaderinc`, taking its numbers as
arguments, and both `water.gdshader` and `city_ground.gdshader` include it (CLAUDE.md 5.1: the
same behaviour, the same code). The canal's picture doesn't change; a capture of the canal before
and after is compared pixel for pixel.

The five numbers (`ripple_cell_m` 0.9, `ripple_rate_hz` 0.7, `ripple_strength` 0.35,
`ripple_wave_per_m` 40, `ripple_falloff_per_m` 18) stay once, in the water's entry. The ground
materials name `"ripples_from": "water"`, and `postprocess.py` copies them, so a drop on a
puddle and a drop on the canal can't drift apart.

### 3.4 The puddle mask

The plan writes it with the level: `game/levels/undercity/hub/hub_puddles.png`.

- **Grid:** 0.125 m a texel over the hub's 240 x 170 m: 1920 x 1360. Plan (x, y) is Godot
  (x, z) (the Blender build writes y as -y, and glTF turns Blender's -y into Godot's z).
- **Grey: the signed distance to the nearest puddle's edge,** negative inside, clamped to
  ±0.5 m, 3.9 mm a step. A distance, not a coverage: filtered between texels, it keeps a
  0.4 m gutter puddle's shape at any view distance (a coverage mask that fine would blur).
- **Alpha: the height of the ground the puddle lies on,** -1 to 3 m, 1.6 cm a step. Outside a
  puddle it holds the nearest puddle's height, so filtering never blends two heights at an
  edge.
- **Imported lossless, with mipmaps.** A VRAM-compressed distance would move the edges. It is
  5.2 MB in memory.

**Four shader globals** carry it: `puddle_mask` (the texture), `puddle_rect_m` (x, z, width,
depth), and the numbers its channels decode with, `puddle_range_m` and `puddle_height_m`, from the
level data, so the mask's writer and the shader can't disagree. (Built with four: this said two,
with the decoding numbers left implicit.) `project.godot` declares them with an empty rect, so the
editor and any level without puddles draw none. The level sets them when it loads, from its level
data (`PuddleShading.Apply`), the way `CharacterShading.Apply` sets the skin's globals. The lightmap bake runs in the editor and so sees no
puddles; they darken the ground by a few per cent, which the bounce wouldn't show.

### 3.5 Where water gathers

The plan places every puddle from its own shapes, after the ground is built. It uses a seeded
stream of its own (`f"{seed}:puddles:{place}"`), so nothing else in the hub moves (the lesson of
`hub-doorways`, design section 3.11).

| Rule | Where | Size | Spacing |
|---|---|---|---|
| **Gutter** | on the road, along a kerb in the rain, the kerb cutting off its side 0.05 m from the kerb face | 2-5 m long, 0.6-1.0 m of road wide, an ellipse turned along the kerb | a gap of 1.5-4 m between puddles |
| **Gully** | a grate on the road at the kerb, and a round puddle round it, cut off the same way | 1.2-1.8 m across | every 25 m of kerb, half a step in from each end |
| **Drip** | on open ground just outside an awning's edge that faces away from its building, or the Skyway deck's, 0.05-0.35 m out | 1.5-3 m long, 0.5-0.8 m wide, along the edge | a gap of 1-3 m |

Each kerb and each drip edge draws from its own stream, and every draw happens whether or not
its puddle is kept, so dropping one moves none of the others.

**Never:**
- under a roof (any `Plan.shelter` with 1 m or more of headroom over the ground, the same test
  the core's wetness rule uses);
- over a kerb top: gutter puddles stay on the road side, and the shader's height test keeps the
  kerb dry (section 3.2);
- on a stair tread, a bridge deck, the rail tracks or the Pit's floor;
- within 0.3 m of a building, a lot, a fixture or a prop's footprint;
- overlapping another puddle (the later one is dropped, never moved, so the rule stays
  predictable).

**Expected** (L2, the recommended amount), from section 2's lengths: 184 gutter puddles, 66
gullies and 135 drip puddles: **about 385 puddles, 451 m², 2.6 % of the ground**, against
2,432 m² and 14.2 % today.

**Measured on the built plan** (seed 7). The first spacing above (gutters 1.5-3.5 m long with
gaps of 4-9 m, gullies 1.0-1.4 m, drips with gaps of 1.5-4 m) placed only 205 puddles, 181 m²
(1.05 %). The estimate had counted every metre of kerb, but the rules then drop what they
should: 26 candidates under the Skyway's deck, 12 beside a parked car, 21 drip lines within
0.3 m of a building, 28 gutters touching a gully's puddle. L2 chose the amount, so the sizes and
gaps above are the ones that reach it: **254 puddles (156 gutter, 41 gully, 57 drip), 434 m²,
2.53 % of the ground**, and 41 gully grates. (253 and 431 m² since vehicle-fixes moved Lantern
Row's parked cars onto the road: one gutter puddle there no longer keeps 0.3 m from a car.) Every kerb of 40 m or more has
a gully and at least three gutter puddles.

### 3.6 One rule each

- **"Is there a roof over this spot":** the plan tests its own `Plan.shelters` with the core's
  headroom (1.0 m, `data/character_lighting.json`, read by the plan), the same shapes the core's
  `Wetness.Sheltered` tests at runtime. The in-engine check asks the core itself (section 3.7),
  so the two can't drift apart unnoticed.
- **The kerb:** the plan's `street` and `paved` shapes, which the ground's own kerb stones come
  from.
- **Placement:** one function, `City.puddles()`. The plan's check, the design map, the mask and
  the level data all read its output.

### 3.7 Checks

| Check | Where | On today's plan | After |
|---|---|---|---|
| The ground textures hold no standing water | `tools/fx` test on the committed ORM maps | fails: 27.6 % and 10.6 % of texels | passes |
| Every puddle is on open ground in the rain, clear of walls and kerbs, and overlaps no other | `city_plan.check_puddles` | (no puddles) | clean |
| A puddle forced under the Skyway, or onto a kerb, is refused, naming it | `test_city_plan.py` | | passes |
| The committed mask agrees with the plan: each puddle's centre reads inside at its height; 0.3 m outside every puddle reads dry | a `tools/levels` test on `hub_puddles.png` | | passes |
| The canal and the ground include the one ripple function, neither defines its own, and the ground's ripple numbers equal the water's | a `tools/godot` test on the shader and `.tres` files | | passes |
| Every puddle is in the rain by the core's rule | `Undercity.Core.Tests` (`PuddleDef.InTheRain`: `Wetness.Sheltered` at every point of each outline, from the level data) | | 254 of 254 |
| The level hands the mask to the ground's shader | `lighting_test.tscn` (the `puddle_rect_m` global after the hub loads) | | the hub's rect |
| The map and the level agree | the design map draws `City.puddles()` | | |

### 3.8 Captures

- **The shader reproduces the material.** The same street view with the old `ORMMaterial3D` and
  with `city_ground.gdshader` with no mask set (both on the new textures): the mean difference
  must be under 1 luma level.
- **The canal is unchanged.** A canal view before and after the ripple moves into its include:
  identical pixels at a fixed time step.
- **Before and after stills** from the same places, at seed 7:
  - Lantern Row at night;
  - Clinic Lane's kerb with a gully;
  - under the Skyway at the garage, which must read dry;
  - the drip line of a row of stall awnings in the market.
- **A video of the rain on the puddles** (a capture sequence encoded with ffmpeg, CLAUDE.md 9:
  motion is the point): Lantern Row's gutter under a neon sign, 6 s.

Whether screen-space reflections show the neon in a puddle is checked on the Lantern Row still;
the puddle is the ground itself now, so they should. The heaviest view's clustered elements are
counted and recorded.

### 3.9 Rebuild

The ground textures change, so every sector's lightmap is baked again; it is the ground's albedo
that the bake bounces. The puddles are drawn at runtime and need no bake. This change lands
after `hub-doorways`' rebuild, and its bake is one more pass of the same eight sectors (about
70 minutes on lavapipe).

## Risks / Trade-offs

- **The ground's cost.** Every ground pixel reads the mask; a puddle's pixels run the 3 x 3 ripple
  loop too. That is small next to the lighting, but lavapipe can't measure frame time; the
  owner's machine is the place for that.
- **A branch per pixel.** The shader skips the ripples outside a puddle. Puddles are whole
  regions of the screen, so neighbouring pixels take the same branch, which is what makes a
  branch cheap on a GPU.
- **The shader must match the material it replaces.** An `ORMMaterial3D` has defaults a
  hand-written shader could miss. The equivalence capture (section 3.8) is the check, and
  anything it finds is fixed before the puddles go in.
- **The mask is 2D.** A deck, a stair or a kerb over the same x and z would take the puddle
  without the height and facing tests (section 3.2, point 3).
- **Less water.** 2.6 % of the ground is far less than 14.2 %. The street may read drier as a
  whole even though each puddle reads better. The owner chose this amount (L2).

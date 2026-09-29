# Design: puddles where water gathers, as decals

## Context

The owner, 2026-09-29: "can you make water puddles on the street less random? maybe use decals?"

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
tile), so the mask repeats on a 4 m and a 2 m grid across the whole hub.

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

## Goals / Non-Goals

**Goals:**
- A puddle is where rain would gather: in the gutters, under drip edges, round drains.
- None under a roof, on a kerb top, on a stair, or against a wall.
- No repeating pattern.
- The map and the level agree, and a check refuses a puddle in the wrong place.

**Non-Goals:**
- Animated ripples (survey L3; a decal can't run a shader).
- Puddles in the other levels (the Drains, the Yard): they have no rain yet.
- Characters' footsteps splashing: a separate audio change.

## Decisions

### 3.1 Ground textures without puddles

`asphalt` and `paving_wet` lose their `puddle` term, and nothing else changes:
- the base colour, grain, cracks and slab joints stay;
- the roughness keeps its variation (asphalt 0.45-0.65, paving 0.30-0.44), so the ground still
  reads as rain-wet.

A texture test reads the committed ORM maps and refuses any texel under roughness 0.2 in either
(CLAUDE.md 5.6, "validate the real artifact").

### 3.2 Puddles are decals

Godot's `Decal` projects albedo, normal, ORM and emission maps onto whatever lies inside its box.
The ORM's effect is multiplied by the albedo's alpha (Godot manual, "Using decals"). Decals work
in Forward+, which the game uses (no `rendering_method` is set). They are counted with the
omni lights, spot lights and reflection probes against the view's clustered elements, 512 by
default.

Why decals rather than the alternatives:
- **No z-fighting by construction.** A decal is not a surface, so there is nothing to keep 1 cm
  off the road (CLAUDE.md 7.2). A puddle mesh would be a coplanar sheet over the asphalt.
- **No UV grid.** Each puddle has its own shape, size and angle.
- **Lightmaps stand.** The decal is drawn at runtime over the baked ground, so moving a puddle
  doesn't need a bake. (Removing the texture puddles does, once, section 3.8.)

**The puddle maps**, written by `generate_city_materials.py` (seeded):
- **6 shapes**, 512 x 512 px: 3 round (for gullies and drip ends), 3 elongated (for gutters and
  drip lines). Each is a soft-edged mask (a 6 % feather), with a thin darker rim where wet edges
  collect grime.
- **Albedo:** RGB near black-blue (the ground seen through 1-2 cm of water); alpha is the mask.
  With the decal's `albedo_mix` at 0.6, the ground shows through, darkened.
- **ORM:** roughness 0.04 inside the mask (a mirror to screen-space reflections and the
  probes); occlusion 1; metallic 0.
- **Normal:** flat, with a faint 1 % ripple noise, so the reflection isn't glass-perfect.
- **The gully grate:** a 0.45 x 0.25 m cast-iron grate (albedo, normal and ORM; metallic 0.8),
  drawn over the centre of its round puddle.

**Each decal:**
- `size` from the plan (x and z the puddle's footprint; y, the projection depth, 0.3 m);
- `normal_fade` 0.5, so walls and kerb faces inside the box are left alone;
- `upper_fade` and `lower_fade` 0.3;
- `distance_fade_enabled`, beginning at 35 m and fading over 10 m;
- `cull_mask` layer 1 only, so characters walking through a puddle aren't painted.

### 3.3 Where water gathers

The plan places every puddle from its own shapes, after the ground is built. It uses a seeded
stream of its own (`f"{seed}:puddles:{place}"`), so nothing else in the hub moves (the lesson of
`hub-doorways`, design section 3.11).

| Rule | Where | Size | Spacing |
|---|---|---|---|
| **Gutter** | on the road, along a kerb in the rain, its long side 0.05 m off the kerb face | 1.5-3.5 m long, 0.4-0.7 m wide, an elongated shape turned along the kerb | a gap of 4-9 m between puddles |
| **Gully** | a grate on the road at the kerb, and a round puddle round it | 1.0-1.4 m across | every 25 m of kerb, half a step in from each end |
| **Drip** | on open ground just outside the outer edge of an awning or the Skyway's deck, 0.05-0.35 m out | 1.0-2.5 m long, 0.4-0.6 m wide, along the edge | a gap of 1.5-4 m |

**Never:**
- under a roof (any `Plan.shelter` with 1 m or more of headroom over the ground, the same test
  the core's wetness rule uses);
- over a kerb top: gutter puddles stay on the road side, and every box's projection depth is
  0.3 m, lower than the 0.15 m kerb plus its fade;
- on a stair tread, a bridge deck, the rail tracks or the Pit's floor;
- within 0.3 m of a building, a lot, a fixture or a prop's footprint;
- overlapping another puddle (the later one is dropped, never moved, so the rule stays
  predictable).

**Expected**, from section 2's lengths: 184 gutter puddles, 66 gullies and 135 drip puddles:
**about 385 decals, 451 m², 2.6 % of the ground**, against 2,432 m² and 14.2 % today.

**In view:** the hub is 240 x 170 m; at about one puddle per 45 m² of open ground, a 45 m view
(the fade's end) holds about 30-40 puddles. With the lights and probes in the same view, that is
well under 512. The capture counts the clustered elements in its heaviest view (section 3.7).

### 3.4 One rule each

- **"Is there a roof over this spot":** the plan tests its own `Plan.shelters` with the core's
  headroom (1.0 m, `data/character_lighting.json`, read by the plan), the same shapes the core's
  `Wetness.Sheltered` tests at runtime. The in-engine check asks the core itself (section 3.6),
  so the two can't drift apart unnoticed.
- **The kerb:** the plan's `street` and `paved` shapes, which the ground's own kerb stones come
  from.
- **Placement:** one function, `City.puddles()`. The plan's check, the design map and the level's
  `ENT_puddle` empties all read its output.

### 3.5 In the pipeline

- The plan writes an entity per puddle, `ENT_puddle_<n>` (extras: `shape`, `size` "w,d", angle
  in the empty's heading), and per gully, `ENT_gully_<n>`.
- The importer (`blender_level_import.gd`) turns them into `scenes/undercity/decals/puddle_<k>.tscn`
  and `gully.tscn`, sizing the `Decal` from `size`.
- `gen_undercity_scenes.py` writes those scenes: a `Decal` with its maps and the settings above.

### 3.6 Checks

| Check | Where | On today's plan | After |
|---|---|---|---|
| The ground textures hold no standing water | `tools/fx` test on the committed ORM maps | fails: 27.6 % and 10.6 % of texels | passes |
| Every puddle is on open ground in the rain, clear of walls and kerbs, and overlaps no other | `city_plan.check_puddles` | (no puddles) | clean |
| A puddle forced under the Skyway, or onto a kerb, is refused, naming it | `test_city_plan.py` | | passes |
| Every puddle in the built level is in the rain by the core's rule | `placement_test.tscn` (`Wetness.Sheltered` on each `puddle` decal) | | about 385 of 385 |
| The map and the level agree | the design map draws `City.puddles()` | | |

### 3.7 Captures

Before and after stills from the same places:
- Lantern Row at night;
- Clinic Lane's kerb with a gully;
- under the Skyway at the garage, which must read dry;
- the drip line of a row of stall awnings in the market.

Each still is taken at seed 7. The heaviest view's clustered elements (lights, probes and
decals in the frustum) are counted and recorded. Whether screen-space reflections see a decal's
roughness is checked on the Lantern Row still: a puddle under a neon sign should show the sign.
If it doesn't, the reflection probes carry the puddles, and the record says so.

### 3.8 Rebuild

The ground textures change, so every sector's lightmap is baked again; it is the ground's albedo
that the bake bounces. The puddles themselves are runtime decals and need no bake. This change
lands after `hub-doorways`' rebuild, and its bake is one more pass of the same eight sectors
(about 70 minutes on lavapipe).

## Risks / Trade-offs

- **Screen-space reflections and decals.** If SSR doesn't see a decal's roughness, a puddle
  reflects only the probes. It still reads as wet, but it won't mirror a neon sign. This is
  checked on the first capture (section 3.7), not assumed.
- **Decal cost.** Each decal is per-pixel work where it overlaps the screen. About 30-40 in view,
  each a few square metres, is small, but lavapipe can't measure frame time; the owner's machine
  is the place for that.
- **Less water.** 2.6 % of the ground is far less than 14.2 %. The street may read drier as a
  whole even though each puddle reads better. Survey L2 lets the owner choose more.
- **Static water in constant rain.** Without ripples a puddle is a still mirror. Survey L3.

## Owner questions (survey, section L)

- **L1** Where puddles form: gutters, drip edges and gullies (recommended); also potholes in the
  road; also downpipe outfalls at building corners.
- **L2** How much: about 2.6 % of the ground by the rules (recommended); about double, with more
  gutter puddles and some potholes; today's 14 %, but placed by the rules.
- **L3** Ripples: static decals now, with ripples as a later change to the ground shaders
  (recommended); ripples in this change, which means ground shaders instead of decals.

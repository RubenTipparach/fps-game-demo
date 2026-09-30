# Design: parked vehicles on the ground, with shadows under them, that read in the dark

## Context

The owner, 2026-09-30: "theyre a little dark in game, the wheels dont align, why system are you
using to model cars? also they seem to be missing underside shadows". The cars are the ten models
`street-vehicles` built (openspec/changes/archive/2026-09-30-street-vehicles), placed on the hub's 15
car spots and baked with the hub.

**How the cars are modelled** (the owner's question). There is no car add-on and no bought kit: the
owner chose our own generator (survey M1). `vehicle()` in `tools/blender/build_undercity_props.py`
runs in Blender and builds each car from its row in `tools/blender/vehicles.json`:

- the lower body is a few prisms extruded across the car's width from its side profile
  (`body_top_m`), cut where the wheel arches are;
- the cabin is one tapered prism (`cabin_m`, `taper`), with glass panes on its faces;
- the wheels are 12-sided cylinders with hub discs;
- the bumpers, lamps, plates, door seams, the taxi's sign and band and the trucks' cargo boxes are
  bevelled boxes;
- the paint is the kit's chipped `painted_metal` texture tinted to the table's colour.

The result is exported as one glb per variant, with its collision boxes. The faults below are in
where the cars are placed, how they're baked and how the paint is specified, not in the modelling
method.

All measurements are on the built hub at seed 7, with scratch instruments that aren't committed:
the plan's ground height under every wheel, the hub's lightmaps' users read in Godot, the lights
that reach each car against those in its bake, and the paints' albedo.

## 1. The wheels

### 1.1 Measured

A car stands at the ground height under its centre (`City.fixture`, `ground_level(c.x, c.y)`). The
ground under each wheel's contact point, minus the car's height:

| Car | Where | Under its wheels | Straddles |
|---|---|---|---|
| car_002 van_olive | Wire Lane, x 12 | -0.15, 0, -0.15, 0 | yes, two wheels over the road |
| car_003 van_white | Wire Lane, x 23.5 | -0.15, 0, 0, 0 | yes, one wheel |
| car_004 sedan_teal | Wire Lane, x 35 | 0, 0, 0, 0 | no, but wholly on the pavement |
| car_005 sedan_black | Wire Lane, x 46.5 | 0, -0.15, 0, 0 | yes, one wheel |
| car_006 taxi | Lantern Row, x 150 | 0, -0.15, 0, -0.15 | yes, two wheels |
| car_007 sedan_grey | Lantern Row, x 168 | 0, -0.15, 0, 0 | yes, one wheel |
| the other nine | Clinic Lane, the depot, the garage | all 0 | no |

Wire Lane's and Lantern Row's spots sit on 2 m pavement strips (Wire Lane's kerb runs at y 41.7 to
42.6 on its north side and 43.7 to 46.9 on its south side; Lantern Row's at y 33.0 and 35.0 to 35.9),
and a 2.0 m spot centred at y 43.3 or 34.6 hangs over their edges. The box cars had the same fault;
their bodies started 0.32 m up, which hid it.

### 1.2 The rule

`check_vehicles` also refuses a spot whose footprint doesn't lie on one ground: the ground height
over a 5 x 3 grid across the footprint (its corners, the middles of its sides, and points between;
the wheels stand inside it) must agree within 0.01 m. (Built: the grid replaced "the four wheels'
contact points", because a converted pack model carries no axle data; the grid is a superset.) The
message names the car, its spot and the heights it found (`car_002 at (12.0, 43.3) straddles a
kerb: ground at 0.00 and 0.15 m under it`). A test breaks the hub on purpose and checks the name.

### 1.3 The spots

The six spots move off the pavement onto the road, their long side 0.2 m from the kerb: each
spot's y is set per spot in `layouts/hub.py` from the kerb line in 1.1, so the irregular strip on
Wire Lane doesn't force one y for the row. The rule checks the result; the standing-room and
puddle checks run on the new spots as on any fixture.

Built (2026-09-30), with the spots at 5.6 x 2.6 m (cc0-vehicles, 3.1). The kerb was measured at
1 cm steps across each spot's length, and the spot's long side put 0.2 m off where it comes
nearest:

| Spot | Road | Kerb, nearest | Spot centre |
|---|---|---|---|
| x 12 | Lantern Row, south kerb | y 42.49 | y 40.99 |
| x 23.5 | Lantern Row, south kerb | y 42.15 | y 40.65 |
| x 35 | Lantern Row, south kerb | y 41.91 | y 40.41 |
| x 46.5 | Lantern Row, south kerb | y 41.57 | y 40.07 |
| x 150 | Lantern Row, north kerb | y 35.00 | y 36.50 |
| x 168 | Lantern Row, north kerb | y 36.15 | y 37.65 |

(The "Wire Lane" of 1.1 is Lantern Row's stretch west of Wire Lane's mouth.) The rule found two
more: the five Quay Road spots, 2.0 m wide on a road that starts at the quay's raised edge (x 214.0),
caught that edge at 2.6 m, so they moved to x 215.5, 0.2 m off it. On the road, the south-kerb cars
stood in the MerSec pair's beat, which the standing-room check refused; the beat's stop at (40, 39)
moved to (40, 37.8) and its corner off Stair Lane from (56, 42.5) to (56, 38.2), so the pair walks
Lantern Row's north half, past the cars.

Survey O2 offers the other way: leave the cars half on the pavement and roll each one 5.7 degrees
(atan 0.15 / 1.5) onto its kerb, as cars in a slum are parked. That needs a tilted placement, a
roll in the entity, and the fit and one-ground checks rewritten for two grounds; recommended
against.

## 2. The shadows under the cars

### 2.1 Measured

The hub bakes one LightmapGI per sector, and a LightmapGI bakes only the meshes under its own
parent: they are its receivers and its occluders. Read from the lightmaps' users:

| Sector | Its lightmap's users | Cars among them |
|---|---|---|
| drydock | 25 | 8 (Clinic Lane's five, the depot's three trucks) |
| lantern_row | 43 | 6 (Wire Lane's four, Lantern Row's two) |
| kiln | 33 | 1 (the garage's van) |
| streets | 41 | 0 |

Every road, pavement and yard floor is the streets sector's (`City.ground`, objects
`streets_walk_*`). So 14 cars are baked in a district sector over ground baked in the streets
sector, where they neither cast a shadow nor darken the ground under them. Only the garage's van
stands on its own sector's floor.

The same rule decides which lights a sector bakes: `gen_level_hub.py` copies another sector's light
into a sector when it reaches that sector's plan geometry (`aabbs`), and entities aren't plan
geometry. Of the 81 lights that reach a car, 11 aren't in its bake; the Wire Lane vans get 2 of 5
and 2 of 6.

### 2.2 The fix: static meshes of the level

The owner, 2026-09-30: "cars should be static meshes so we get it nice light baking".

The cars were already static, lightmapped meshes: each glb imports with static light baking, its
own lightmap UVs and 0.05 m texels, and all 15 bodies are users of a lightmap (2.1). What spoiled
the baking is where they were: instanced scenes under the district sectors, whose bakes hold
neither the road under them nor every light that reaches them. So a parked car becomes a static
mesh of the level itself, baked with the ground it stands on:

- **In the ground's sector.** The plan lists each car as a model placed in the sector that owns the
  ground under it: the streets for every outdoor spot, the kiln for the garage's bay.
- **Built into that sector's glb.** `build_undercity.py` imports the car's committed glb (the prop
  kit's output, the one source of the model) into that sector at its spot and heading: its body as
  a static mesh named `car_<id>` with its own UVs (the level's world-UV projection leaves it alone),
  and its `-colonly` boxes beside it, so Godot gives it a static body like any level geometry. The
  level's import then gives it lightmap UVs and bakes it with the ground under it.
- **Fine texels on the car.** The body carries `lightmap_texel_scale` 4, so it bakes at 0.1 m
  against the level's 0.4 m, the way interiors ask for 0.15 m (`INTERIOR_EXTRAS`).
- **The entity stays as a marker.** `ENT_car_<n>` keeps the car's id, model and heading for the
  level data and the tests; the importer no longer instances a scene for it.
- **Every light reaches it.** The streets sector already bakes every light that reaches the ground,
  and the cars stand on it, so the light-sharing gap in 2.1 closes without counting entities.
- **A check.** The placement test finds each car's static mesh beside its marker, in the sector that
  owns the ground under it, and a user of that sector's lightmap.

### 2.3 Enough shadow?

The street lightmap's texel is 0.4 m (`UNDERCITY_TEXEL_M`), so a car's shadow spans about 11 x 4
texels: soft, but there. Measured on the after stills from the before viewpoints: the mean
brightness of the ground seen under a car between its wheels, against the ground 1 m beside it. If
the bake leaves the ground under a car at more than 60% of the ground beside it, the remedies come
in this order, staying with baked light as the owner asked:

1. the ground chunks under the car spots bake at 0.2 m (`lightmap_texel_scale` 2 on those chunks);
2. a contact shadow under each car: a projected decal of a soft dark rectangle, 0.3 m larger than
   the car's footprint.

Survey O3 asks whether to add the contact shadow regardless.

## 3. The paint

### 3.1 Measured

The prop kit's `paint(rgb)` tints the `painted_metal` texture, whose mean linear albedo is 0.637,
by the table's colour, so every paint comes out at 64% of its colour's albedo:

| Paint | Table colour | Albedo on the car |
|---|---|---|
| black | #17191c | 0.006 |
| maroon | #5c1a1f | 0.020 |
| truck red | #7a1f1a | 0.033 |
| rust | #7a3f24 | 0.050 |
| olive | #4f5532 | 0.053 |
| teal | #1d5c5e | 0.056 |
| grey | #6c7176 | 0.104 |
| taxi | #d9c27c | 0.349 |
| white | #c8c6bd | 0.359 |

For comparison, the level's own surfaces: concrete 0.192, rust metal 0.114, tech panel 0.106, brick
0.078, wet paving 0.031. Seven of the nine paints are darker than the brick walls round them. The
paint is a plain dielectric at roughness 0.35, so it doesn't catch the neon either.

### 3.2 The fix

- **A paint names the albedo it has on the car.** The builder divides the colour's linear value by
  the texture's mean (read from the committed texture, not typed) before tinting, so the table's
  colour is the car's average colour. `vehicle_data.py` refuses a paint whose albedo is under 0.03
  or over 0.8, the range from a very dark to a very light paint, and a colour the texture can't reach
  (a tint over 1).
- **The paints, re-specified** at the same hue:

| Paint | Albedo now | Albedo proposed | Colour |
|---|---|---|---|
| black | 0.006 | 0.04 | #35393e |
| maroon | 0.020 | 0.08 | #8f2d35 |
| truck red | 0.033 | 0.09 | #9d2b24 |
| rust | 0.050 | 0.10 | #894729 |
| olive | 0.053 | 0.10 | #565d37 |
| teal | 0.056 | 0.12 | #236b6d |
| grey | 0.104 | 0.22 | #7c8288 |
| taxi | 0.349 | 0.45 | #c7b271 |
| white | 0.359 | 0.60 | #ceccc2 |

- **A clear coat.** The car paints get Godot's clear coat (`clearcoat 1.0`, roughness 0.1): the
  wear stays in the base layer, and street lights and neon show in the gloss. The prop kit's
  material writer learns the two keys.

Survey O4 asks whether this is bright enough; the numbers are a first pass, tuned on the after stills.

**Built (2026-09-30), after cc0-vehicles.** The generated cars left the hub, and with them the
tinted paints: a PSX car's texture is its own colour, not a tint over a paint texture, so there is
nothing to divide out and no paint to re-specify. What stays is the range: `vehicle_data.py` reads
each committed texture's mean linear albedo (0.041 to 0.327 across the 22) and refuses one outside
0.03-0.8, naming it. The clear coat is on each car's material (`veh_psx_<id>.tres`: roughness 0.6,
clear coat 1.0 at roughness 0.1, from `vehicles.json`'s "material").

## 4. Checks

| Check | Where | Wanted |
|---|---|---|
| Every wheel on one ground | `check_vehicles`, `test_city_plan.py` | the hub passes; a spot moved back across the kerb is refused by name |
| A car is a static mesh baked with its ground | the placement test | each car's mesh beside its marker, in its ground's sector, a user of that sector's lightmap |
| Shadow under a car | the after stills, section 2.3 | the ground under a car at most 60% of the ground beside it |
| Paint in range | `vehicle_data.py`, a test | a paint under 0.03 or over 0.8 refused |
| Nothing else moved | `test_city_plan.py` | the plan equal but for the six spots and what avoids them (puddles) |

## 5. Captures

`docs/screenshots/vehicle_fixes/`: the before stills (`vehicle_fixes_before.json`: Wire Lane's and
Lantern Row's wheels at the kerb, Clinic Lane's and the depot's undersides, Wire Lane's paint), and
after stills from the same places. Lavapipe: the pictures show the look, not frame time.

## Risks

- **Moving six spots moves the puddles near them.** Puddles keep clear of fixtures, so the puddle
  list and mask change round the new spots; the puddle checks run as before.
- **The streets sector bakes longer.** It gains 14 cars, 21,000 triangles of occluders and their
  lightmaps at 0.1 m, and the drydock and Lantern Row bakes lose them. The bake records its time.
- **Each car is a copy in the sector's glb.** The streets glb grows by the 14 cars' meshes; the
  vehicle glbs stay the one source, and a rebuild of the level picks up a rebuilt car.

## Owner decisions (2026-09-30)

- "cars should be static meshes so we get it nice light baking": section 2.2.
- **O2, O3, O4** left blank (recommendation accepted): the six spots move onto the road beside the
  kerb; bake first, with finer ground or a contact shadow only if the shadow measures faint; the
  paints of section 3.2, tuned on the after stills.
- **O1** "I never approved kenneys. why quaternius doesnt work? look for more cco cars": Kenney is
  out. Which models the hub uses, ours or CC0 packs, is `openspec/changes/cc0-vehicles` and survey
  O5. The kerb, the static meshes and the one-ground rule hold whichever it is; the paint section
  applies to the models we generate.
- **O5, O6** (chat, 2026-09-30: "yea psx cars are nice, I'd want a consistent art style"): every
  vehicle comes from the PSX pack with its own textures (`cc0-vehicles`). The paint re-specification
  (section 3.2) is withdrawn with the generated cars; the range check stays and applies to every
  vehicle texture's mean albedo, which the PSX textures pass (0.035 to 0.362).

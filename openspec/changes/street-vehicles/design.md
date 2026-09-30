# Design: parked cars, vans, taxis and trucks from our own generator

## Context

The owner, 2026-09-29, asked for better car modelling, and answered survey M1 to M3 the same
day: our own generator, sedans, vans, taxis and trucks, parked only. The Yard's wrecks come later,
made from these same vehicles (M2: "junkyard will be retooling existing vehicles to make them
look wrecked").

## 1. Today

Measured on the committed plan at seed 7:

| Spot | Count | Built by | Triangles |
|---|---|---|---|
| 4.6 x 2.0 m | 11 | `City.car()`: body box z 0.32-0.95, cabin box 0.95-1.45 (its sides `window_dark`), 4 wheels of 10 sides, r 0.33 m | about 170 |
| 8.5 x 2.8 m | 3 | `City.truck()`: cargo box 0.9-3.4 m, cab 0.5-2.6 m, chassis, 6 wheels r 0.45 m | about 250 |
| Rail wagon | 2 | `City.wagon()` | unchanged by this change |

The paint is one of four wall materials, drawn from a seeded stream per spot.

## 2. Options looked at (survey M1)

| Option | For | Against |
|---|---|---|
| [Kenney Car Kit](https://kenney.nl/assets/car-kit) (CC0, 45+ models, 8 wheels) | many types, ready now | toy-like proportions next to the UT99 look |
| [Quaternius Cars](https://poly.pizza/bundle/Cars-Bundle-FE5IWe6OMk) (CC0, 8 cars) | closer to our look | few types; another pack to pin |
| Paid Geometry Nodes generators (Superhive) | many options | driven from Blender's UI; not scriptable or reproducible |
| **Our own generator in the prop kit (chosen)** | our materials and texel density, as many variants as the table asks, the Yard's wrecks from the same code | more work up front |

The owner took the recommendation. Before building out, the first sedan is rendered beside a
Kenney sedan and a Quaternius sedan, in the kit's studio light, so the choice can be overruled on
sight (task 1.2).

**As built (2026-09-30):** the gate compares ours with Kenney's only. Quaternius's pack is served
from poly.pizza, which this container's network can't reach. `look_gate_cars.png` and
`look_gate_vans.png` in `docs/screenshots/street_vehicles/` show our sedan, taxi, van and truck
beside Kenney's sedan, taxi, van and delivery truck, each scaled to ours, in one light: ours read as
grimy 1980s vehicles, Kenney's as toys (big wheels, fat bumpers, pastel paint). The Kenney models
were used for that render only, from the scratchpad, and are not in the repository.

## 3. The generator

### 3.1 In the prop kit

`build_undercity_props.py` already models the hub's props as low-poly, bevelled, UT99-era pieces
with `PropKit`: `box` (registered with the z-fighting check), `cyl`, `hull` (a convex hull with
coplanar faces merged), `obox`, `collision`, the kit's own materials and textures, the glTF export
and the per-prop triangle budget. Vehicles use exactly that. One new helper, `PropKit.prism(profile,
y0, y1, mat, taper)`, extrudes a side profile across the width with the far face scaled by
`taper`, as a convex hull of the two outlines; a body is a few of those.

### 3.2 A body, piece by piece

Axes are the kit's: metres, x right, y front, z up; the origin is the floor centre of the
footprint.

| Piece | How | Material |
|---|---|---|
| Lower body | three prisms from the side profile: nose (bumper to front wheel arch), sill (between the arches), tail; the gaps between them are the wheel arches | paint |
| Fenders | a prism over each wheel, 0.06 m clear of the tyre | paint |
| Greenhouse | a prism from the belt line to the roof, the windscreen and rear screen raked by the profile, `taper` 0.86 (tumblehome) | `car_glass` |
| Pillars and roof | thin `obox` strips 0.012 m proud of the greenhouse | paint |
| Wheels | tyre `cyl` of 12 sides; hub disc `cyl` 0.02 m proud | `rubber`, `gunmetal` |
| Bumpers | bevelled boxes, 0.04 m proud of the nose and tail | `rubber` or paint |
| Lights | `obox` lenses 0.01 m proud: head (clear), tail (red), unlit, since parked | `car_lens_head`, `car_lens_tail` |
| Plates | a box with a generated plate texture (invented codes, seeded) | `car_plate` |
| Extras | taxi roof sign (lit, `TAXI`), van sliding-door groove, truck cargo box with a roll-up rear door and a cab | per type |

Surfaces meant to stand proud stand at least 0.01 m off (CLAUDE.md 7.2). Boxes are registered
with `assert_no_zfighting`; hulls and cylinders are kept clear by those offsets.

### 3.3 The table: `tools/blender/vehicles.json`

Validated by `tools/blender/vehicle_data.py` on `tablekit.py` (unknown keys are errors, a missing
optional field takes its code default, numbers must be finite).

```json
{
  "budget": {"car_tris": 2500, "truck_tris": 3500},
  "types": {
    "sedan": {"length_m": 4.5, "width_m": 1.8, "wheelbase_m": 2.7, "track_m": 1.55, "wheel_r_m": 0.32,
              "profile_m": [[-2.25, 0.3], [-2.25, 0.62], [-1.3, 0.8], [2.1, 0.78], [2.25, 0.62], [2.25, 0.3]],
              "greenhouse_m": [[-1.25, 0.8], [-0.7, 1.38], [0.9, 1.4], [1.7, 0.82]], "taper": 0.86},
    "taxi":  {"like": "sedan", "roof_sign": {"text": "TAXI", "w_m": 0.7, "h_m": 0.22}},
    "van":   {"length_m": 4.55, "width_m": 1.9, "...": "..."},
    "truck": {"length_m": 8.3, "width_m": 2.6, "cargo_m": [5.6, 2.6, 2.5], "...": "..."}
  },
  "variants": [
    {"id": "sedan_maroon", "type": "sedan", "paint": "car_paint_maroon", "grime": 0.3},
    {"id": "taxi", "type": "taxi", "paint": "car_paint_taxi"}
  ]
}
```

The profile numbers above are a first draft, tuned on the first render.

**As built.** The committed table differs from the draft in shape, not in purpose:

| Draft | Built | Why |
|---|---|---|
| `profile_m`, one closed outline | `body_top_m`, the lower body's top line rear to front, and `clearance_m` under it | the builder cuts the lower body at the arches and needs its height at any y |
| `greenhouse_m` | `cabin_m`, four points, and `windows_y_m` for the side windows | the cabin is painted and the glass sits on it (section 3.2, as built) |
| `wheelbase_m` | `axles_m`, each axle's y | a truck has three axles |
| taxi, a type with `like` | taxi, a sedan variant with `roof_sign` and `chequer` | one body, two liveries; no inheritance to validate |
| `grime` per variant | none | the kit's `painted_metal` texture already carries chips and grime under every paint |
| lengths 4.5-4.55 m | 4.28 m | bumpers and plates bring a car to 4.38 m, inside the garage's 4.4 m spot |

It also carries `bumper_z_m`, `head_z_m`, `tail_z_m`, `lamp_w_m`, `seams_y_m`, `band_z_m` (the taxi's
band), `cargo` (a truck's box) and per variant `plate` (an invented code) and `livery` (a truck's
cargo sides). `vehicle_data.py` refuses, by path: a top line that doesn't run rear to front, a
wheel past the body, tyres past the sides, a lamp or bumper under the clearance, a door seam over an
arch, a band off the sides, a cargo box outside the vehicle, an unknown type or paint, and a
repeated id. The variants:

| Type | Variants | Fits a spot of |
|---|---|---|
| Sedan | maroon, teal, grey, black | 4.6 x 2.0 m |
| Taxi | one livery (cream with a chequer band) | 4.6 x 2.0 m |
| Compact van | white, olive, rust | 4.6 x 2.0 m |
| Box truck | two cargo liveries (invented firms) | 8.5 x 2.8 m |

**As built, a body piece by piece** (`vehicle()` in the prop kit):

| Piece | How | Material |
|---|---|---|
| Lower body | a prism under the top line for each run between the arches, full height; over each arch a prism from the arch's top (2r + 0.06 m) | paint, bevel 0.012 m |
| Wheel wells | a box inside each arch, between the tyres | `rubber` |
| Cabin | one prism of `cabin_m`, 0.03 m in from the sides, `taper` at the roof | paint |
| Glass | panes 3-10 mm proud of the cabin: windscreen and rear screen on its sloped faces, side windows the cabin's outline inset by `glass_margin_m` and cut to `windows_y_m` | `car_glass` |
| Wheels | tyre `cyl` of 12 sides, hub disc 0.02 m proud | `rubber`, `gunmetal` |
| Bumpers, lamps, plates | boxes: bumpers 0.04 m proud, lamps 0.012 m, plates 0.012 m proud of the bumper | `rubber`, `car_lens_*`, `car_plate_<id>` |
| Door seams | thin strips 4 mm proud down the lower body, broken where the taxi's band runs | `rubber` |
| Taxi | roof sign box with a lit `TAXI` panel 12 mm proud each way; a chequer band from arch to arch, 8 mm proud | `white_plastic`, `taxi_sign`, `taxi_chequer` |
| Truck | cargo box; livery panels on its sides 10 mm proud; a roll-up door 12 mm proud, above the tail lamps' sill; two chassis rails | paint, `truck_livery_<id>`, `rollup_door`, `gunmetal` |
| Collision | boxes: the lower body, the cabin; a truck's cargo box and rails | `-colonly` |

Triangles: sedans 1,360, the taxi 1,476, vans 1,312, trucks 1,616 (budgets 2,500 and 3,500). Every
model passes the z-fighting check. The first build found two overlaps the checker would have
refused, both fixed in the builder: the truck's tail lamps on the roll-up door's plane (the door
now starts above them) and the taxi's band 4 mm off the door seams' faces (the seams now break
round it).

### 3.4 Materials

The kit's own `MATERIALS`, written as `game/materials/props/*.tres` like the others:
`car_paint_maroon`, `car_paint_teal`, `car_paint_grey`, `car_paint_black`, `car_paint_white`,
`car_paint_olive`, `car_paint_taxi` (paint, roughness 0.35, the rain's wet look), `car_glass`
(near black, roughness 0.05), `car_lens_head`, `car_lens_tail`, `car_plate`, and `taxi_sign`
(emissive, `emission_operator` 1, CLAUDE.md 11). Grime is a darker, rougher band low on the body,
from a generated mask, so a variant's `grime` is a number in the table, not another material.

**As built:** paints are the kit's `paint()` (the `painted_metal` albedo tinted, roughness 0.35),
so wear comes with the texture and there is no grime number. `car_glass` is (0.07, 0.08, 0.09) at
roughness 0.06: at the first render's near black it read as flat black card. Each variant has its
own `car_plate_<id>`, each truck its `truck_livery_<id>`, all FITTED (UVs 0..1 across each face, the
text upright from outside).

## 4. In the hub

- `City.car()` and `City.truck()` are removed. A car spot writes `ENT_vehicle_<n>` at the spot's
  centre, heading along its long side, with extras `kind` "vehicle" and `model`.
- The model is drawn per spot from a stream of its own, `f"{seed}:vehicles:{spot}"`, among the
  variants that fit the spot, so no other draw in the hub moves (the lesson of `hub-doorways`,
  design section 3.11). Expected on today's 14 spots: 6 sedans, 2 taxis, 3 vans, 3 trucks.

  **As built:** `{spot}` is the spot's size, "car" or "truck". One draw per spot gave four maroon
  sedans, three taxis, three rust vans and no teal, grey, white or olive, so each size deals its
  variants like a deck, shuffled from its stream: every variant shows once before any repeats.
  There are 15 spots, the garage's bay among them. Seed 7 deals 6 sedans (every paint), 2 taxis,
  4 vans (every paint) and 3 trucks (both liveries). A vehicle faces along its spot's long side,
  toward the spot's angle, so the layout says which way a row faces. An outdoor spot still counts
  as a prop, so the props after it keep their names and every other stall its light: against the
  committed plan, only the 14 box cars and the garage's box car are gone, and nothing else moved.
- `blender_level_import.gd` maps `kind` "vehicle" to `models/undercity/props/vehicle_<model>.glb`.
  The glb carries its `-colonly` boxes, so Godot gives it a static body.
- `import_presets.py` imports the vehicle glbs as static lightmapped props (UV2, like the prop
  kit's static props), so they bake with the level.
- The spot's footprint stays the solid the people-placement check keeps people out of
  (CLAUDE.md 7.4).

## 5. Checks

| Check | Where | Result wanted |
|---|---|---|
| Each model within its triangle budget | the prop kit's build, from the exported mesh | refuses one over, naming it |
| No coplanar overlapping boxes in a model | `assert_no_zfighting` per model | clean |
| Every placed model fits its spot's footprint | `city_plan.check_vehicles`, reading each committed glb's POSITION bounds | all 14 fit |
| The table is valid | `python3 tools/blender/vehicle_data.py` | OK |
| A variant too long for a 4.6 m spot is refused | `test_city_plan.py` | refused, naming spot and model |
| A car turned across its spot is refused | `test_city_plan.py` | refused; either way round along it fits |
| Every committed glb within its budget | `test_city_plan.py`, counting the glb's indices | all ten |
| Dealing the vehicles moves nothing else | `test_city_plan.py`, the plan with and without them | equal but for the `ENT_vehicle` entities |
| People stand clear of every vehicle | `city_plan.py` standing checks and `placement_test.tscn` | clean |

## 6. Captures

- **The look gate** (task 1.2): our first sedan beside the Kenney and Quaternius sedans, three
  views each, same light. For the owner before the other types are built.
- A contact sheet of all ten models (`render_undercity_props.py -- vehicles`, which writes
  `docs/screenshots/street_vehicles/vehicles_sheet.png`; the prop sheet leaves the vehicles out).
- Before and after stills in the hub at seed 7: Lantern Row's kerb, the Kings' Garage forecourt,
  the depot yard's trucks, and Clinic Lane.
- Lavapipe: the pictures are proof of the look, not of frame time.

## Risks / Trade-offs

- **The look.** A low-poly generated car can read as a toy too. The look gate is first, so the
  owner sees it before nine more models are built on it.
- **Triangles.** 14 vehicles at up to 2,500 triangles (3,500 for trucks) is about 38,000 at most,
  against about 2,500 today; the hub's static geometry is about 122,000. Unmeasured on a GPU.
- **Lightmap texels.** Vehicles become separate baked instances; each needs UV2 and texel space.
  The first sector bake records the time against the last one.

## Owner decisions (survey M1 to M3, 2026-09-29)

- **M1** "recommended": our own generator, the packs rendered beside it first.
- **M2** "parked sedans, junkyard will be retooling existing vehicles to make them look wrecked
  (follow recommended)": sedans, vans, taxis and trucks; wrecks later, from these vehicles.
- **M3** "no, recommended": parked only; flying traffic in the skyline later.

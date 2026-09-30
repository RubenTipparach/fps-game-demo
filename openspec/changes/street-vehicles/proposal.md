# Proposal: parked cars, vans, taxis and trucks from our own generator

## Why

The owner, 2026-09-29: "is there any packages out there to help with improving the car modeling
in blender?" Answered in the survey the same day:
- M1 (where the models come from): "recommended": our own Blender generator, with the two CC0
  packs rendered beside it first so the look can be overruled on sight;
- M2 (which vehicles): "parked sedans, junkyard will be retooling existing vehicles to make them
  look wrecked (follow recommended)": sedans, vans, taxis and trucks in the hub, and the Yard's
  wrecks made later from these same vehicles;
- M3 (do they move): "no, recommended": parked only; flying traffic in the skyline is a later
  change.

**Measured** on the committed plan at seed 7 (`tools/levels/city_plan.py`, the hub):

| | Today |
|---|---|
| Car spots in the layout | 14: eleven 4.6 x 2.0 m, three 8.5 x 2.8 m |
| How a car is built | `City.car()`: two boxes (body 0.32-0.95 m, cabin 0.95-1.45 m) and four 10-sided wheels |
| Triangles per car | about 170 |
| How a truck is built | `City.truck()`: three boxes and six wheels |
| Variety | four paint materials drawn per spot (`gunmetal`, `gunmetal_light`, `rust_metal`, `tech_panel`) |

Every car in the hub is the same shoebox with a smaller shoebox on top. There are no windows,
lights, bumpers, arches or doors, and the paints are wall materials.

## What Changes

- **A vehicle generator in the prop kit.** `tools/blender/build_undercity_props.py` gains vehicle
  builders that use its own `PropKit` (bevelled boxes, convex hulls, cylinders, the kit's
  materials, `-colonly` collision, the z-fighting registration). There is no second modelling
  pipeline. A new table, `tools/blender/vehicles.json`, holds each body type's profile and sizes
  and each variant's paint and extras.
- **Four body types, ten models:** sedan (4 paints), taxi (1 livery, a lit roof sign), compact van
  (3 paints) and box truck (2 liveries). Each is one glb under
  `game/models/undercity/props/vehicle_<id>.glb` with its collision boxes. Budget: 2,500 triangles
  for a car or van, 3,500 for a truck.
- **The hub places models, not boxes.** `City.car()` and `City.truck()` go. Each car spot writes an
  `ENT_car_<n>` entity whose `model` extra names a variant, drawn from a seeded stream of its
  own, so nothing else in the hub moves. The importer instances the model's glb. The rail wagons
  (`City.wagon()`) stay as they are.
- **The look is checked before it's built out.** The first sedan is rendered beside a Kenney Car
  Kit sedan and a Quaternius sedan (both CC0), in the same light. The packs are downloaded for
  that render only and never enter the build. The owner can overrule the generator on that sheet.
- **Checks:** a model over its triangle budget is refused; every model must fit inside the
  footprint of the spot it is placed on (read from the committed glb); vehicles stay registered
  as solids for the people-placement check.

Not in this change: moving traffic (M3), flying traffic in the skyline (a later change), and the
Yard's wrecks (the scrap-kings-yard change retools these vehicles, per M2).

## Capabilities

### New Capabilities

- `street-vehicles`: parked vehicles in city levels are generated models, placed by the plan.

## Impact

- `tools/blender/build_undercity_props.py`: vehicle builders, their materials (paints, glass,
  lenses, plates) and textures (plates, the taxi sign), and the budget check.
- `tools/blender/vehicles.json` (new) and its schema in `tools/blender/vehicle_data.py` (new, on
  `tablekit.py`, so an unknown key is an error).
- `tools/levels/city_plan.py`: `City.car()` and `City.truck()` removed; `ENT_car` entities;
  `check_vehicles`.
- `game/addons/brushfire_tools/blender_level_import.gd`: `kind` "car" instances
  `models/undercity/props/vehicle_<model>.glb`.
- `tools/godot/import_presets.py`: the vehicle glbs as static lightmapped props.
- A rebuild of the hub's sectors and a lightmap bake.

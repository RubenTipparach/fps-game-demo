# Tasks

The owner asked on 2026-09-29 and answered survey M1 to M3 the same day: our own generator,
sedans, vans, taxis and trucks, parked only.

## 1. Before

- [x] 1.1 Measure today's cars in the hub plan: spots, how they're built, triangles, paints
  (design section 1).
- [x] 1.2 The look gate: `PropKit.prism`, `vehicles.json` with the sedan, and one sedan built;
  rendered beside a Kenney Car Kit sedan and a Quaternius sedan (downloaded for the render only).
  Stills in `docs/screenshots/street_vehicles/`, and a survey row for the owner.

  Built: Kenney only, since Quaternius's host is out of this container's reach (design
  section 2); the sedan, taxi, van and truck beside Kenney's. Survey M4.
- [ ] 1.3 Before stills from the four hub places (design section 6).

## 2. The generator

- [x] 2.1 `vehicle_data.py` on `tablekit.py`, and `vehicles.json` with the four types and ten
  variants.
- [x] 2.2 The vehicle builders in `build_undercity_props.py`: body pieces, wheels, lights, plates,
  the taxi sign, the van and truck extras; the materials and textures; the budgets.
- [x] 2.3 A contact sheet of the ten models.

  Built: 1,312-1,616 triangles; the table as built and its differences from the draft are in
  design section 3.3.

## 3. The hub

- [x] 3.1 `City.car()` and `City.truck()` out; `ENT_vehicle` entities with their own stream;
  `check_vehicles` reading the committed glbs; `test_city_plan.py` refuses a model that
  doesn't fit.
- [x] 3.2 The importer's `vehicle` kind; the import presets.

  Built: 15 spots dealt from a deck per spot size (design section 4); only the box cars left
  the plan. The presets are the prop kit's own (`import_presets.write`, static lightmaps).
- [ ] 3.3 Rebuild the sectors, bake, `placement_test.tscn`.

## 4. Records

- [ ] 4.1 After stills from the before places; triangle counts; the bake time against the last.
- [ ] 4.2 A validation record; the design page's F21; move the requirement into
  `openspec/specs/street-vehicles`; archive.

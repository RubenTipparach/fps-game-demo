# Tasks

## 1. Layout and plan

- [x] 1.1 `skyline` in `hub.py`: the eight named towers, the near ring's fillers and the far ring.
- [x] 1.2 `city_plan.py`: the `skyline` sector (massing by style, crowns, the Skyway's scenery
  extension) and the four assertions (bounds, coverage, overlaps, budget), each with a failing
  regression case.
- [x] 1.3 `build_undercity.py` meshes the sector, merged per material and ring: 5 surfaces,
  2,556 triangles (design, "Found in building").

## 2. Godot

- [x] 2.1 `shaders/skyline_tower.gdshader` (windows, crowns, beacons, haze) and the `skyline`
  material in the import presets.
- [x] 2.2 The player camera's far plane to 1,500 m; the skyline sector in `hub.tscn` with no
  LightmapGI.
- [x] 2.3 The Spire's two searchlights (owner I8): additive beam shader and sweep.

## 3. Map

- [x] 3.1 The locator inset in `render_map.py`'s legend.

## 4. Captures

- [x] 4.1 The baseline views again (north from the market, east over the Cut) plus west from Tin
  Stacks and one from the Skyway deck, before and after; triangle and draw-call counts;
  validation record; design page; archive.

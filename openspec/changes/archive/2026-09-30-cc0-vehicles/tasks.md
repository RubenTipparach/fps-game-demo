# Tasks

The owner answered O1 on 2026-09-30: "I never approved kenneys. why quaternius doesnt work? look for
more cco cars", and in chat: "kenney is a nogo", then "yea psx cars are nice, I'd want a consistent
art style": every vehicle from the PSX pack, with its own textures (O5, O6); O7 "no need for trucks
now, just use vans"; O8 "smudge those textures, background cars can use bilinear filtering, totally
fine".

## 1. Before

- [x] 1.1 Why Quaternius failed; which CC0 hosts answer (design section 1).
- [x] 1.2 The candidates downloaded, opened and measured; the night render beside ours
  (design section 2, `docs/screenshots/cc0_vehicles/`).
- [x] 1.3 The whole PSX pack rendered at night; its textures' albedo (design section 3).

## 2. The packs

- [x] 2.1 `tools/deps/vehicle_packs.json` and the fetch script, refusing a changed hash: the script now reads
  every `tools/deps/*_packs.json`, and each pin records its author.
- [x] 2.2 `build_vehicles_cc0.py`: the chosen bodies and colour variants to `vehicle_<id>.glb` by the
  kit's conventions, with provenance; the budget and z-fighting checks (a triangle-level check,
  `detailing.coplanar_triangle_report`, and its test).
- [x] 2.3 `vehicles.json`: the pack variants; `vehicle_data.py` and its test.
- [x] 2.4 CLAUDE.md 13: the PSX vehicles' textures (and 11: the converter's output is generated).
- [x] 2.5 The generator retired: `vehicle()`, its materials, textures and glbs out of the prop kit.
- [x] 2.6 The layout's car spots at 5.6 x 2.6 m (`CAR_L`, `CAR_W`); the depot's truck spots become car
  spots (O7).

## 3. The hub

- [x] 3.1 The contact sheet; the hub rebuilt and baked with `vehicle-fixes`; after stills. The owner,
  2026-09-30, on the stills: "ok looks good", "new cars are dope".
- [x] 3.2 A validation record; the design page's F21; the spec delta into `openspec/specs`; archive.

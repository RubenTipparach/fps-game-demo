# Tasks

The owner answered O1 on 2026-09-30: "I never approved kenneys. why quaternius doesnt work? look for
more cco cars", and in chat: "kenney is a nogo", then "yea psx cars are nice, I'd want a consistent
art style": every vehicle from the PSX pack, with its own textures (O5, O6). Survey O7 (the truck
spots) and O8 (the rest of the hub) are open.

## 1. Before

- [x] 1.1 Why Quaternius failed; which CC0 hosts answer (design section 1).
- [x] 1.2 The candidates downloaded, opened and measured; the night render beside ours
  (design section 2, `docs/screenshots/cc0_vehicles/`).
- [x] 1.3 The whole PSX pack rendered at night; its textures' albedo (design section 3).

## 2. The packs

- [ ] 2.1 `tools/deps/vehicle_packs.json` and the fetch script, refusing a changed hash.
- [ ] 2.2 `build_vehicles_cc0.py`: the chosen bodies and colour variants to `vehicle_<id>.glb` by the
  kit's conventions, with provenance; the budget and z-fighting checks.
- [ ] 2.3 `vehicles.json`: the pack variants; `vehicle_data.py` and its test.
- [ ] 2.4 CLAUDE.md 13: the PSX vehicles' textures.
- [ ] 2.5 The generator retired: `vehicle()`, its materials, textures and glbs out of the prop kit.
- [ ] 2.6 The truck spots as O7 decides (the layout's depot spots, or trucks built to match).

## 3. The hub

- [ ] 3.1 The contact sheet; the hub rebuilt and baked with `vehicle-fixes`; after stills.
- [ ] 3.2 A validation record; the design page's F21; the spec delta into `openspec/specs`; archive.

# Proposal: the hub's cars from CC0 packs, pinned and converted

## Why

The owner, 2026-09-30, survey O1: "I never approved kenneys. why quaternius doesnt work? look for
more cco cars", and in chat: "kenney is a nogo". Kenney's Car Kit is out, as a source and as a
comparison.

**Why Quaternius failed.** The first look gate reached for Quaternius's Cars bundle on poly.pizza,
which sits behind Cloudflare's bot challenge: every request from this container gets a 403 with
`cf-mitigated: challenge`, which only a browser can pass. quaternius.com itself answers, and its
packs download from Google Drive folders linked on each pack's page. Quaternius's Cars pack
downloads that way: 7 cars, CC0.

**More CC0 cars, measured** (design section 2; all CC0 on their pages, fetched and opened here):

| Pack | Author, source | What's in it | Triangles | Textures |
|---|---|---|---|---|
| Cars | Quaternius, quaternius.com (Google Drive) | 7 cars: 2 sedans, 2 sports cars, SUV, taxi, police car | 2,954-3,294 | flat colours |
| PSX Style Cars | GGBotNet, OpenGameArt | 8 bodies (sedans, hatchback, wagon, taxi, police, box and mail vans), colour variants, a car shadow mesh, sounds | 304-476 | 128 px pixel art |
| UAZ-452 van | Mehozavr, OpenGameArt | a utility van and a wrecked one | 1,014 | 256 px |
| 3D Vehicles Pack | mehrasaur, OpenGameArt | 5 trucks, a bus, cars, jeeps, a pickup | about 2,700 | none |
| LowPoly Cars, Public Transport | Quaternius, OpenGameArt | cartoon cars, a bus, a tram | | flat colours |
| Free Low Poly Vehicles, Vehicles Assets pt1, Vehicles | rgsdev, eracoon, RayB2, OpenGameArt | toy-proportioned cars and trucks | | |

Rendered on a wet street at night under sodium lamps and neon, beside our generated cars
(`docs/screenshots/cc0_vehicles/cc0_gate_night.png`): the PSX cars and the UAZ van read as worn
1980s vehicles with their own grilles, lights and trim painted in; Quaternius's cars are clean
modern cars in pastel colours; the rest read as toys, like Kenney's.

**The owner's choice**, 2026-09-30, in chat: "yea psx cars are nice, I'd want a consistent art
style". Every vehicle in the hub comes in the PSX look: GGBotNet's pack, and nothing beside it in
another style. So the UAZ-452 and our generated vehicles leave the hub, and the pack's own textures
stay (they are the look; survey O5 and O6 recorded from this answer).

## What Changes

- **Every vehicle from PSX Style Cars.** Sedans (Car 2, Car 5), a wagon (Car 1), a hatchback (Car 3),
  a minivan (Car 4), the taxi (Car 5) and box vans (Car 8), with the pack's colour variants
  (design section 3). The police car stays out (the hub's law is MerSec, not police), the 1930s car
  stays out, and the burnt-out wreck (Car 6) is kept for the Yard. Kenney, the UAZ-452 and our
  generated vehicles aren't used. The depot's truck spots take vans (O7: "no need for trucks now,
  just use vans"), and every car spot grows to fit the pack's bodies at one scale (design 3.1).
- **Pinned like the NPC packs.** `tools/deps/vehicle_packs.json` lists each pack's URL, page,
  author, licence and SHA-256; a fetch script downloads them into a cache outside the repository
  and refuses a pack whose hash differs (as `fetch_character_tools.py` does).
- **Converted into our models.** A Blender script turns each chosen model into
  `game/models/undercity/props/vehicle_<id>.glb` by our conventions: a real length, front along +Y,
  its origin at the floor centre of its footprint, its wheels in place, `-colonly` collision boxes,
  within the triangle budget, and a provenance note beside it. The table (`vehicles.json`) names
  each variant's source; the plan, the placement, the static meshes and the checks of
  `vehicle-fixes` stay as they are.
- **Their own textures, filtered bilinearly (O6, O8: "smudge those textures, background cars can
  use bilinear filtering, totally fine").** The PSX cars' detail is in their 128 px textures;
  CLAUDE.md 6.4 says textures come from Material Maker at our texel density, so the exception is
  written into CLAUDE.md 13.
- **Our vehicle generator retires.** With no generated vehicle left in the hub, the vehicle builders,
  their materials and textures and their ten glbs leave the prop kit; `vehicles.json` keeps its
  schema for pack variants.

## Capabilities

### Modified Capabilities

- `street-vehicles`: a vehicle model can come from a pinned CC0 pack, converted to our conventions.

## Impact

- `tools/deps/vehicle_packs.json` and a fetch script; a conversion script in `tools/blender/`.
- `tools/blender/vehicles.json` and `vehicle_data.py`: a variant's source; `build_undercity_props.py`
  keeps building the trucks.
- CLAUDE.md 13: the exception for the PSX vehicles' textures.
- `build_undercity_props.py`: the vehicle builders removed, with their materials, textures and glbs.
- The models, the contact sheet, the hub rebuild and bake (with `vehicle-fixes`).

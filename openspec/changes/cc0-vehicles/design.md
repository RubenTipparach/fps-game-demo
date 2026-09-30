# Design: the hub's cars from CC0 packs

## Context

Survey M1 (2026-09-29) chose our own generator, "the CC0 packs rendered beside it first". The first
look gate put our cars beside Kenney's only, because Quaternius's bundle wouldn't download. The
owner, O1 (2026-09-30): "I never approved kenneys. why quaternius doesnt work? look for more cco
cars"; in chat: "kenney is a nogo". This change answers both and proposes a source per vehicle
type. The fixes to how the cars stand and bake (`vehicle-fixes`) hold whichever models are used.

## 1. Why Quaternius didn't download

| Host | From this container | Why |
|---|---|---|
| poly.pizza (the bundle the first gate tried) | 403 | Cloudflare's bot challenge (`cf-mitigated: challenge`): only a browser that runs its script passes |
| quaternius.com | 200 | the packs' own pages, each linking a Google Drive folder |
| drive.google.com, drive.usercontent.google.com | 200 | folders list with `embeddedfolderview`; files download with `export=download` |
| opengameart.org | 200 | direct file links |
| polyhaven.com | 200 | one car in 521 models (a covered car) |

So Quaternius was never unavailable, only its mirror was. The pack downloads from quaternius.com's
Drive link: `Blends/`, `FBX/`, `OBJ/`, `License.txt` (CC0 1.0) and a preview.

## 2. The candidates

All CC0 1.0 on their pages (the licence field of each OpenGameArt page; Quaternius's
`License.txt`). Measured from the downloaded files; sizes are each pack's own units before scaling.

| Pack | Files | Models | Triangles | Textures | Downloaded |
|---|---|---|---|---|---|
| Quaternius, Cars | Blends (2.79), FBX, OBJ | Cop, NormalCar1, NormalCar2, SportsCar, SportsCar2, SUV, Taxi | 2,954 (car), 3,278 (taxi), 3,294 (SUV) | none: flat material colours | Drive folder `1fKlbDry77iY8KlEoxzUxIAZQL_XhzWlA` |
| GGBotNet, PSX Style Cars (Aug 2023) | Blends (2.83-2.92), OBJ + MTL | Car 01 to 08: sedans, a hatchback, a wagon, Car5's police and taxi, Car8's box and mail vans; colour, snow and snow-covered variants; a wheel; a flat car shadow with an alpha texture; 20 sound effects | 304-476 | 128 x 128 px, pixel art | `psx_style_cars_by_ggbot_august2023.zip`, SHA-256 `db67b0b0...699e4` |
| Mehozavr, UAZ-452 utility van | FBX | the van, a wrecked van | 1,014 | 256 x 256 px, a 128 px wheel | `uaz-452_onlymodelandtex.zip`, SHA-256 `adc0e41d...b46b0` |
| mehrasaur, 3D Vehicles Pack | Blends (2.78), FBX, OBJ | 5 trucks, a bus, 4 cars, 2 jeeps, a pickup, a bicycle | about 2,700 (truck_01) | none | `vehicle_pack.zip`, SHA-256 `083380cb...a52` |
| Quaternius, LowPoly Cars; Public Transport | OpenGameArt | cartoon cars; a bus, a tram, an ambulance | | flat colours | previews only |
| rgsdev, eracoon, RayB2 | OpenGameArt | toy-proportioned cars and trucks | | | previews only |

`docs/screenshots/cc0_vehicles/cc0_candidates.jpg` is the packs' own previews side by side;
`cc0_gate_night.png` renders ours, Quaternius's three, four PSX cars, the UAZ van and a mehrasaur
truck at their real lengths on a wet street at night, under sodium lamps and neon, in one light.

What the night render shows:

- **PSX Style Cars** read as worn 1980s cars: grilles, lamps, trim and rust are painted into the
  texture, so 300-480 triangles carry more detail than our 1,360. Point-sampled, the pixels suit
  the UT99 look. There are sedans, a hatchback, a wagon, a taxi, a police car and a box van.
- **The UAZ-452** is a worn utility van, and its wrecked twin is ready for the Yard (M2).
- **Quaternius's cars** are clean and modern, in pastel colours: good shapes, but they read new
  against the hub's grime; they'd need our paint to fit.
- **mehrasaur's trucks** are untextured shapes; our generated box trucks, with their liveries, do
  as well.

## 3. The owner's choice: the PSX pack, one style (2026-09-30)

"yea psx cars are nice, I'd want a consistent art style". Every vehicle comes from GGBotNet's PSX
Style Cars and nothing in another style stands beside them. `psx_pack_night.png` renders the whole
pack at night:

| Pack body | Is | Colour variants | Triangles | In the hub |
|---|---|---|---|---|
| Car 1 | a wagon | default, blue, grey, red | 438 | yes |
| Car 2 | a sedan | default, black, red | 312 | yes |
| Car 3 | a hatchback | default, red, yellow | 448 | yes |
| Car 4 | a minivan | default, grey, light grey, light orange | 476 | yes, a car spot's van |
| Car 5 | a sedan | default, green, grey | 454 | yes |
| Car 5 taxi | the taxi | | 440 | yes |
| Car 5 police | a police car | LA, default | 472 | no: the hub's law is MerSec, a private force (hub-combat) |
| Car 6 | a burnt-out wreck, no wheels | | 304 | not now: the Yard's wrecks (M2) |
| Car 7 | a 1930s car | six | 457 | no: out of place in Meridian |
| Car 8 | a box van | default, grey, mail, purple | 376 | yes |

The textures' mean albedo is 0.035 to 0.362 (median 0.081; the brick walls are 0.078): none needs
brightening, and every one passes `vehicle-fixes`' range check of 0.03 to 0.8.

The deal is unchanged (`street-vehicles`, design section 4): a car spot deals from the cars, the
minivan, the taxi and the box van with their colour variants.

**The truck spots (survey O7).** The pack has no truck, and GGBotNet has made none (their
OpenGameArt page: cars, a skeleton, houses, props, fonts, textures). The depot's three 8.5 m spots
can take the pack's box vans, the layout's spots cut to a van's size (recommended: one style, no new
art); or trucks we'd build to match, low-poly with a 128 px painted texture in the pack's palette,
which risks a near miss of the style.

**The rest of the hub (survey O8).** The PSX cars are point-sampled 128 px art; the hub's walls use
Material Maker sets at our texel density and the people are MakeHuman bodies. "A consistent art
style" is read here as the vehicles in one style; whether the rest of the hub moves toward the PSX
look is a larger question, asked on its own and judged on the after stills.

## 4. How a pack enters the game

- **Pinned.** `tools/deps/vehicle_packs.json`, beside `character_packs.json`: each pack's id, file,
  URL, page, author, licence, where the licence is stated, SHA-256 and size. A fetch script
  downloads into `~/.cache/undercity/deps/` and refuses a mismatched hash. The packs never enter the
  repository (CLAUDE.md 5.6: a reference checkout is never part of a build).
- **Converted.** `tools/blender/build_vehicles_cc0.py` reads the pinned pack and writes each chosen
  body and colour variant to `game/models/undercity/props/vehicle_<id>.glb` by the prop kit's
  conventions: scaled to the table's real length, front along +Y, its origin at the floor centre of
  its footprint, its wheels placed, its materials named `veh_psx_<name>` with point-sampled
  textures, `-colonly` collision boxes from its body and cabin, the triangle budget (the pack's
  304-476 are well inside 2,500) and the z-fighting check.
- **One table.** `vehicles.json` lists each variant's pack body, texture and real length;
  `vehicle_data.py` validates it; the plan, the deal, the fit and one-ground checks, the static
  meshes and the placement test don't change.
- **The generator retires.** `vehicle()` and its materials, textures and glbs leave the prop kit,
  and `vehicles.json` drops its generated types.
- **Provenance.** Each converted glb records its pack, author, licence, file and SHA-256 in its
  extras, and the README's Credits list the packs; CC0 asks for no credit, the rules ask for the
  record (CLAUDE.md 5.6, borrowed code keeps its provenance).

## 5. Their textures (O6, from the owner's choice)

CLAUDE.md 6.4: textures come from Material Maker at the texel density in `materials.json`. The PSX
cars' look is their painted textures, one 128 x 128 px image over a whole car, which no Material
Maker set at our density would reproduce; "psx cars are nice" is their look. So they keep their own
textures, point-sampled, and CLAUDE.md 13 lists the exception: "The CC0 PSX vehicles keep their own
textures, point-sampled, as GGBotNet painted them."

## 6. Checks

| Check | Where | Wanted |
|---|---|---|
| A pack's hash | the fetch script | a changed download refused, naming the pack |
| Each converted model | `build_vehicles_cc0.py` | within budget, no z-fighting, front +Y, origin at the footprint's floor centre, collision present |
| The table | `vehicle_data.py`, a test | a pack variant naming an unpinned pack or a missing model file refused |
| The hub | as `vehicle-fixes` | every car fits its spot, on one ground, a static mesh baked with its ground |

## Risks

- **Links move.** Drive folders and OpenGameArt files can change or vanish; the pinned hashes catch
  a change, and the converted glbs are committed, so the game never depends on the link.
- **One style among the vehicles, another in the walls.** Pixel-art cars beside Material Maker
  walls; the night renders suggest they sit well at street distance. Checked on the after stills,
  and asked as O8.

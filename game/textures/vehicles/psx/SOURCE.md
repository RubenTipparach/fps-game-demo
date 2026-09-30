# Where these textures came from

Written by `tools/blender/build_vehicles_cc0.py`; don't edit by hand.

- Pack: PSX Style Cars by GGBotNet, the August 2023 release
- Author: GGBotNet
- Licence: CC0 1.0 (The pack's OpenGameArt page, whose licence field reads CC0 (fetched 2026-09-30); the zip carries no licence file of its own, only a link to the author's itch.io page (GGBot - itch.io.URL).)
- Page: https://opengameart.org/content/psx-style-cars
- Download: https://opengameart.org/sites/default/files/psx_style_cars_by_ggbot_august2023.zip
- SHA-256: `db67b0b0fbaa02454a5d000dc9ec1cc53f360e8f41ab44f3fb1c7e8f71e699e4` (2610303 bytes), pinned in `tools/deps/vehicle_packs.json`
- Scale: the pack's wheel is 0.9172 units across, a 0.65 m wheel, so 0.70871 m per unit

Each texture is the pack's file copied byte for byte. Each model, `game/models/undercity/props/vehicle_<id>.glb`,
is the body's mesh from the blend, turned to face +Y and scaled.

| File | Pack texture | Pack body |
|---|---|---|
| `wagon_green.png` | `Car 01/car.png` | `Car 01/Car.blend` |
| `wagon_blue.png` | `Car 01/car_blue.png` | `Car 01/Car.blend` |
| `wagon_grey.png` | `Car 01/car_gray.png` | `Car 01/Car.blend` |
| `wagon_red.png` | `Car 01/car_red.png` | `Car 01/Car.blend` |
| `sedan_navy.png` | `Car 02/car2.png` | `Car 02/Car2.blend` |
| `sedan_black.png` | `Car 02/car2_black.png` | `Car 02/Car2.blend` |
| `sedan_maroon.png` | `Car 02/car2_red.png` | `Car 02/Car2.blend` |
| `hatchback_green.png` | `Car 03/car3.png` | `Car 03/Car3.blend` |
| `hatchback_red.png` | `Car 03/car3_red.png` | `Car 03/Car3.blend` |
| `hatchback_yellow.png` | `Car 03/car3_yellow.png` | `Car 03/Car3.blend` |
| `minivan_blue.png` | `Car 04/car4.png` | `Car 04/Car4.blend` |
| `minivan_grey.png` | `Car 04/car4_grey.png` | `Car 04/Car4.blend` |
| `minivan_silver.png` | `Car 04/car4_lightgrey.png` | `Car 04/Car4.blend` |
| `minivan_tan.png` | `Car 04/car4_lightorange.png` | `Car 04/Car4.blend` |
| `fullsize_red.png` | `Car 05/car5.png` | `Car 05/Car5.blend` |
| `fullsize_green.png` | `Car 05/car5_green.png` | `Car 05/Car5.blend` |
| `fullsize_grey.png` | `Car 05/car5_grey.png` | `Car 05/Car5.blend` |
| `taxi.png` | `Car 05/car5_taxi.png` | `Car 05/Car5_Taxi.blend` |
| `box_van_white.png` | `Car 08/Car8.png` | `Car 08/Car8.blend` |
| `box_van_grey.png` | `Car 08/Car8_grey.png` | `Car 08/Car8.blend` |
| `box_van_mail.png` | `Car 08/Car8_mail.png` | `Car 08/Car8.blend` |
| `box_van_purple.png` | `Car 08/Car8_purple.png` | `Car 08/Car8.blend` |

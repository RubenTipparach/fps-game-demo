## ADDED Requirements

### Requirement: No lookalikes nearby
On a level's placements, with any world seed, no two civilians within 15 m of each other SHALL
share both body and outfit palette, and no civilian body SHALL be used more than 3 times. The
choice SHALL be made by one rule in `Undercity.Core` from the world seed and each civilian's
stable id, so a save and a replay reproduce the crowd.

#### Scenario: The hub's crowd
- **WHEN** the crowd rule assigns the hub's 35 civilians with any seed from 1 to 100
- **THEN** no pair within 15 m shares body and palette, and no body is used more than 3 times

#### Scenario: Reloading
- **WHEN** a game is saved and loaded
- **THEN** every civilian has the same body, palette, accessories, scale, idle and partner as
  before

### Requirement: Civilians vary at runtime
Each civilian SHALL take, from its role in `data/crowd.json`, an outfit palette, zero to two
accessories hung from the mounts they name (`data/npc_bodies.json`, a node on every body), a
height scale of 0.95-1.05, and an idle. No two accessories SHALL fill the same slot. Skin, hair
and eyes SHALL never be recoloured.

#### Scenario: Rain in the market
- **WHEN** the hub's crowd is placed
- **THEN** about a third of the outdoor civilians carry open umbrellas, and the rest vary in
  accessories and idles by their roles

### Requirement: Civilians placed together talk
Two civilians placed within `talk_pair_radius_m` (2.0 m) of each other SHALL stand talking,
facing each other, each in one pair at most, whatever the world seed; an accessory that forces
its own idle (the umbrella held up) SHALL keep it.

#### Scenario: A pair in the market
- **WHEN** the hub is loaded with any seed
- **THEN** its four placed pairs face each other and talk

### Requirement: The body pool covers the CC0 range
The generator SHALL build 18 civilian bodies covering every age band, ethnicity and sex of the
CC0 skins, and 3 MerSec bodies, all within the body budget and rebuilding byte for byte.

#### Scenario: Verifying the bodies
- **WHEN** `build_npcs.py -- --verify` runs
- **THEN** all 18 civilian and 3 MerSec bodies rebuild byte for byte within budget

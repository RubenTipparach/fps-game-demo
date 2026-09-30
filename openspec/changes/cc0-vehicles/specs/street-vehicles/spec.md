## ADDED Requirements

### Requirement: A vehicle taken from a CC0 pack is pinned and recorded
A vehicle model converted from a CC0 pack SHALL come from a pack pinned in
`tools/deps/vehicle_packs.json` by its SHA-256, with its URL, author and licence recorded there,
and the fetch SHALL refuse a download whose hash differs. The converted glb SHALL follow the prop
kit's conventions (its real length, front along +Y, origin at the floor centre of its footprint,
collision boxes, the triangle budget) and SHALL record its pack, file and hash.

#### Scenario: A changed download
- **WHEN** a pack's download no longer matches its pinned SHA-256
- **THEN** the fetch stops, naming the pack and both hashes

#### Scenario: A converted car
- **WHEN** a PSX Style Cars sedan is converted
- **THEN** its glb is its table length long, faces +Y, stands on its origin's floor, has its
  collision, stays in the car budget and names its pack and hash

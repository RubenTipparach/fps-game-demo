# Design: every building shows a door, and every door is built the way E1M3 builds one

## Context

The owner, 2026-09-29: "a lot of buildings are missing door ways or doors, review guidelines
for level design that we did in e1 m3". E1M3 is The Cistern, the Blender reference level
(`tools/blender/build_cistern.py`). The hub is built by the same Blender pipeline from
`tools/levels/city_plan.py`.

### 1. E1M3's door rules, reviewed

The rules come from three places:
- `CLAUDE.md` 7.2 and 7.3;
- `docs/ut99_reference.md`, checklist items 2-4;
- the Cistern builder, `detailing.FRAMES` and `scenes/props/doorway.tscn`.

The review does not recall them: each row cites where the rule lives.

| # | E1M3's rule | Where E1M3 does it | The hub today |
|---|---|---|---|
| R1 | A doorway is its own carved volume. The rooms' trims stop at it and never run through it | `DoorS` and `DoorN`: 3.2 x 3.3 x 0.6 m cutters with `trims=False`; `detailing` subtracts openings from every wall's trims | **Kept.** Each door is an air box with `trims=False` (`door_boxes`) |
| R2 | The opening is carved at the frame's `fits` size. The frame's clear opening is REVEAL (0.1 m) smaller at each jamb and at the head, so it stands proud of walls and ceiling | `detailing.FRAMES["doorway"]`: fits 3.2 x 3.3, clear 3.0 x 3.2; spec `level-geometry`, "Frame props have an inset clear opening" | **Missing.** The opening is carved at the door's width and nothing stands in it |
| R3 | Every doorway has a thick framed jamb and a lintel, inset from the wall (checklist 2) | the doorway kit: jambs with leaf slots, pilasters with plinths and capitals, pistons, a heavy lintel with a sign plate, a threshold plate with a door track | **Missing.** The opening's sides are plain `tech_panel` |
| R4 | A door that closes has leaves in its frame. An open passage gets a passage frame on both faces | split sliding leaves in `doorway.tscn`; archway frames; voussoir rings on both faces of each side arch (`arch_ring`, called once per face) | **Partly.** 5 of 43 doors have a leaf (the locked ones); no open doorway is framed |
| R5 | Every doorway is lit, and every light has a visible fixture with a corona (checklist 4) | `doorway.tscn`'s baked downlights, status light bar and coronas; wall lamps flanking the tunnels | **Missing.** No light belongs to a door. Wall lamps land every 16 m on narrow lanes, wherever |
| R6 | Frame boxes are registered with the z-fighting check | `frame_solids` goes to `assert_no_zfighting` as props | **Nothing to register** |
| R7 | A doorway joins two spaces a person can use. Nothing stands in front of it | the tunnels run straight into the rooms | **Broken for 10 of 21 exterior doors** (section 2) |
| R8 | Pillars and pilasters have a base and a capital (checklist 3), and plinth heights differ from baseboard heights | `column(..., cap_mat)`, `arch_ring` plinths at 0.55 m, clear of 0.30, 0.35 and 0.45 | not applicable yet (no pilasters at doors) |
| R9 | Door size fits the player: 3.2 m, about 168 UU, for Brushfire's 1.8 m player in arena rooms | `ut99_reference.md` section 3, scale | **The hub's own sizes, and right for a city**: 1.4 x 2.4 m doors, 2.0-6.0 m x 3.0 m entrances (`DOOR_H`, `WIDE_DOOR_H`) |

**What carries over:** R1-R8 are rules about how a doorway is built, and they carry over
unchanged. R9 is a size, and the hub keeps its own, as CLAUDE.md 12 puts it: "Take the shape,
not the text".

### 2. The hub today (measured)

**The instrument.** A scratch script ran `city_plan.City(hub).build()` at seed 7 with
`City.facade`, `City.recess` and `City.named_building` wrapped:
- it recorded each building's ground-floor recesses (width, sill, head, depth, back and reveal
  material);
- it recorded each facade edge's length and what it faces (`street`, `side`, `water` or none).

It changed no output, and it is not committed. The checks in section 3.9 reproduce its numbers
on the old plan. A building "faces walkable ground" when a facade edge at least 2.2 m long looks
at `street` or `side`: room for a door frame (1.5 m) and 0.35 m to each end.

**Buildings**, 358 in all (343 lots, 15 named, the ship excluded). 225 face walkable ground.

| Kind | Face walkable ground | What they show there |
|---|---|---|
| Named, with rooms | 11 of 12 | a bare carved entrance (Precinct 9's front is hidden by lot 11, so it isn't counted) |
| Named, no rooms | 3 | a lit 3.0 x 2.85 m recess, 0.6 m deep, `window_lit_warm` behind |
| Shanty lots | 143 | 78: a dark 1.0 x 2.15 m recess, 0.25 m deep, `window_dark` behind; 65: a blank wall (their walkable edges face side passages, which get no front) |
| Strip and market lots | 34 | 28: 3-5 m shop bays (lit window, dark glass or a shutter) and no door; 6: a blank wall |
| Workshop and dock lots | 34 | 25: painted roll-up (3.6 x 3.8 m) or loading (3.2 x 3.4 m) recesses, 45 in all, with no door beside them; 9: a blank wall |

**Doors of the enterable buildings:** 43 (the layout's `doors`).
- 21 are exterior and 22 interior; widths are 1.4 m (24), 2.0 (4), 2.5 (1), 3.0 (7), 4.0 (5),
  5.0 (1) and 6.0 (1).
- None has a frame.
- 5 have a leaf, all locked doors:
  - the Anchor's back room and back door;
  - Kessler's office;
  - the clinic's pharmacy;
  - Precinct 9's records room.
- All 43 have wall enough for a frame. The tightest is 3.0 m from its door's centre to a room
  corner, against 1.05 m needed.

**What stands in front of the exterior doors.** Clear depth is how far a strip as wide as the
door runs out from the wall before it meets a building or water:

| Door | Width | Clear depth | In the way |
|---|---|---|---|
| Harbor Fish Hall, north entrance (174, 76) | 4.0 | 1.35 m | lot 242 |
| Harbor Fish Hall, west entrance (164, 94) | 4.0 | 1.35 m | lot 244 |
| Precinct 9, front (224, 134) | 2.0 | 1.20 m | lot 11, which also hides the precinct's whole west face from Quay Road |
| MerSec checkpoint (174, 157) | 2.0 | 1.20 m | lot 15 |
| Rusty Anchor, back door (112, 60) | 1.4 | 1.35 m | lot 226 |
| Rusty Anchor, west door (68, 65) | 1.4 | 1.20 m | lot 239 |
| Kessler's, back (128, 59) | 1.4 | 1.25 m | lot 257 |
| Doc Vo's, back (176, 58) | 1.4 | 1.20 m | lot 252 |
| Fish Hall, service (164, 108) | 1.4 | 1.25 m | lot 245 |
| Mouse's den (36, 115) | 1.4 | 1.25 m | lot 280 |

The other 11 exterior doors have 8.2 m or more of clear ground. **The cause:**
`render_map.city_blocked` keeps a 0.9 m margin round named buildings. `city_lots` then shrinks
each lot by 0.3, 0.35, 0.45 or 0.7 m, so a lot can stand 1.2-1.6 m from any wall of a named
building, doors included. The placement test passes only because nobody stands in those gaps.

**Before stills** (`docs/screenshots/hub_doorways/before_*.png`, AutoTest
`docs/playtest/scripts/hub_doorways_before.json`, seed 7, 1600 x 900, the committed hub):

| Still | Shows | Requirement it motivates |
|---|---|---|
| `before_01_lantern_row_shops_without_doors.png` | Lantern Row at Pachinko Sunrise: shop windows and parked cars, and not a door along the block | Every building on the street shows a door |
| `before_02_wire_lane_blank_recesses.png` | Wire Lane: a shanty's dark recess beside a lit window, and a blank rust wall opposite | Every building on the street shows a door |
| `before_03_anchor_entrance_unframed.png` | the Rusty Anchor's 3 m entrance under its sign: a rectangular hole in the stone, a thin `tech_panel` reveal, no jamb, lintel or lamp | Every doorway is framed |
| `before_04_fish_hall_entrance_hidden.png` | from Clinic Lane toward the Fish Hall's north entrance: what stands there is lot 242's dark shop window, 2.5 m away | Every door opens onto ground a person can reach |
| `before_05_fish_hall_entrance_slot.png` | the unlit 1.35 m slot between lot 242 and the hall, the only way to that entrance | Every door opens onto ground a person can reach |
| `before_06_precinct_door_hidden.png` | from Quay Road toward Precinct 9's front door: lot 11's rust wall and loading door, with the precinct's corner behind it | Every door opens onto ground a person can reach |
| `before_07_neon_koi_false_entrance.png` | Neon Koi's front under its sign: the lit 3 m recess in the middle stands in for an entrance, between a shutter and a lit shop window, and none of them opens | K3 |

## Goals / Non-Goals

**Goals:**
- Every doorway in the hub is built by E1M3's rules R1-R8.
- Every building that faces walkable ground shows at least one door.
- Every exterior door opens onto ground a person can reach.
- The plan refuses a layout that breaks any of these, and the placement test proves it in the
  built level.

**Non-Goals:**
- **Interiors for filler buildings.** Their doors are closed dressing.
- **Moving a door the layout places.** All 43 fit their walls as they are.
- **Lock rules, the lock prompt, the minigames.**
- **E1M3 and its doorway kit,** which stay as they are.
- **Frame-time numbers.** A cloud session renders on lavapipe.

## Decisions

### 3.1 Rules, not sizes

| Door | Clear opening (w x h) | Fits (carved) | Frame |
|---|---|---|---|
| Interior door, service door | layout width (1.4) x `DOOR_H` 2.4 | 1.6 x 2.5 | a liner and architrave |
| Entrance, 2.0-2.4 m | layout width x `DOOR_H` 2.4 | +0.2 x +0.1 | a portal |
| Entrance, 2.5 m and wider | layout width x `WIDE_DOOR_H` 3.0 | +0.2 x +0.1 | a portal |
| Shanty door (dressing) | 0.9 x 2.0 | 1.1 x 2.1 | a liner and architrave |
| Shop door, residents' door, man door (dressing) | 1.0 x 2.2 | 1.2 x 2.3 | a liner and architrave; the shop door shares its bay's frame |

**The layout's width is the clear opening,** the width a person walks through. The plan
carves the fits, REVEAL wider at each jamb and REVEAL taller. That means:
- `door_leaf.glb` (1.4 x 2.4 m) and every door entity keep their size;
- the placement test's door numbers stand;
- each wall loses 0.1 m more at each side of a door, which section 2 shows every wall has.

REVEAL is `detailing.REVEAL`, the same constant E1M3 uses: one source.

### 3.2 One frame builder

`detailing.door_frame(clear_w, clear_h, wall_t, kind, style)` returns boxes in the door's
local frame, and `city_plan` places them. It lives beside `FRAMES` and `frame_solids` because
it is the same rule, R2, at other sizes. E1M3's glb frames keep `frame_solids`.

- **Liner:** a box filling each REVEAL gap, 0.1 m thick, as deep as the wall. Its outer face is
  back to back with the carved side face, which is allowed. The head liner does the same under
  the lintel.
- **Architrave:** on each face of the wall that faces air:
  - 0.15 m wide beyond the fits edge, standing 0.1 m proud (R2);
  - a head piece 0.2 m tall over the jambs.

  The corners are owned by the head piece, as the rooms' inside corners are owned by the
  x-running walls (CLAUDE.md 7.2).
- **Portal** (entrances), in place of the outside architrave:
  - pilasters 0.35 m wide and 0.15 m proud;
  - plinths 0.55 m tall, the height E1M3's arch plinths use and clear of the 0.30, 0.35 and
    0.45 m baseboards (R8);
  - capitals 0.2 m tall;
  - a lintel 0.35 m tall projecting 0.25 m, with a `light_panel` downlight strip on its
    underside (R5).
- **Threshold plate:** 0.02 m tall, the plan's `STANDING_STEP_M`, so the placement rule counts
  it as underfoot and nobody trips on it.
- **Materials** from the existing library, by style:
  - tech and dock: `tech_panel`;
  - workshop and shanty: `rust_metal`;
  - brick streets: `stone_blocks`;
  - the shrine: `stone_blocks` with a `neon_pink` accent.

  No new material.
- **Triangle budget** per frame, counted by the plan:
  - at most 72 triangles for a liner and architrave, which is 6 boxes with their buried faces
    skipped;
  - at most 180 for a portal.
- **The z-fighting check:** every frame box is registered with `assert_no_zfighting` as a
  detail (R6). The check already covers details against walls and against each other.

The sign over an entrance reads the frame's top, not the door's height. That moves its bottom
to the lintel's top plus 0.2 m, so the two never share space.

### 3.3 Which doors close (K2)

The rule is **a door with a lock has a leaf, and a door without one is an open, framed
doorway**. The rule needs no new code in the core: `DoorDef.Lock` is required today, so
an unlocked door you open by hand doesn't exist. It gives:
- 5 leaves, the locked doors that have them now;
- 38 open doorways.

Owner question K2 asks whether public entrances should have doors the runner opens. That
would take a lockless `DoorDef` in the core and a door entity at each entrance. Civilians flee
along the navmesh, so each leaf would also need a navigation link that opens it.

### 3.4 Dressing doors on the filler buildings

A dressing door is geometry in the sector's lit mesh, not an entity: frame boxes, a leaf box
set 0.05 m behind the clear opening's plane, and its fittings. It is never opened (K1), and
it is collision, so a thrown body or a shot stops on it.

| Style | Where | The door | Fittings | Triangles |
|---|---|---|---|---|
| Strip, market | every shop bay: the bay's recess splits into a window and a door, one frame round both | glazed, 1.0 x 2.2: `glass` panel, `tech_panel` stiles | a push bar; a shuttered bay's shutter comes down over both | at most 60 |
| Strip, market, two floors or more | one per building, between bays, on the longest street edge | residents' door, 1.0 x 2.2, `tech_panel` | a buzzer panel (`light_panel`, 0.12 x 0.3 m) | at most 60 |
| Shanty | the dark recess becomes the door; a building without one gets one on its longest walkable edge | plank (`crate`) or sheet (`rust_metal`), 0.9 x 2.0 | 20 % boarded (two `crate` boards across), 25 % a padlocked hasp | at most 60 |
| Workshop, dock | beside a roll-up or loading door, or on the longest walkable edge if there is none | steel man door, 1.0 x 2.2, `rust_metal` | the roll-up recess gains a hood box (0.35 m) and guide rails, both `rust_metal`, as details | at most 60 per door, 36 per shutter |

**Placement.** A door takes a span of its edge, and that span goes into the facade's
`occupied` list, as shop bays do today.
- It keeps 0.35 m from an edge's ends and 0.3 m from any other opening.
- It never goes under a fire escape's drop ladder.
- **Which edge:** the longest edge facing `street`, else the longest facing `side`.
- **Randomness:** the choices (door kind, boarded, padlocked, which bay gets the residents'
  door) come from the lot's own seeded RNG, drawn after the facade's existing draws. Every
  window, shop bay and sign already in the hub therefore keeps its place and colour.

**Count:** 47 shop doors, 30 residents' doors, 143 shanty doors and 34 man doors: about 255,
at most 60 triangles each, about 15,000 triangles.

### 3.5 Lamps favour doors

`wall_lamps` already walks each narrow lane every 16 m and hangs a lamp on the nearest facade,
trying offsets of 0, 1 and 2 m. It will try the spot above a door first, when a door lies within
2 m of the lane point.
- The lamp stays at `WALL_LAMP_Z` (3.3 m), above every dressing door's head (2.2 + 0.1 + 0.2 =
  2.5 m, plus the 0.15 m floor).
- The lamp count is unchanged.
- The 15 entrances each get a baked downlight at the lintel, with its fixture (the downlight
  strip) and a corona, so the hub's baked lights go from 196 to 211.

### 3.6 Clear approaches

- **Entrance** (an exterior door 2.0 m wide or more, 15 doors): the approach is a strip as
  wide as the frame's outer width plus 0.6 m each side. It runs straight out from the wall
  until it lies on open ground (`O`: a street, lane or square), and it may run at most 12 m.
- **Service door** (1.4 m, 6 doors): the approach is a 2.0 m landing as wide as the frame
  plus 0.6 m each side. The 2.0 m is the leaf's swing (1.36 m) plus a body clear of it.
  Beyond it, the walkable ground eroded by 0.6 m must still join the landing to open ground:
  a way through at least 1.2 m wide, the player's 0.8 m cylinder with room to turn.

**Cut after splitting.** `render_map.city_lots` subtracts every approach from the lots after
subdividing and shrinking them. A lot left thinner than 1.5 m is paved, as slivers are today.
Blocking the approaches before subdividing would split a piece in two. That would renumber
every later piece, and each piece seeds its own RNG (`f"{seed}:{bi}:{district}"`), so the
whole hub's lots would reshuffle. Cutting after the split changes only the lots that stood in
front of a door: lots 11, 15, 226, 239, 242, 244, 245, 252, 257 and 280. The design map and
the build share `city_lots`, so they still agree (CLAUDE.md 7.1).

**Precinct 9:** cutting lot 11 back from the approach also opens the precinct's west face to
Quay Road. It gets its windows, and its sign's choice of face.

### 3.7 The three named shells (K3)

Neon Koi Karaoke (22 x 18 m), Pachinko Sunrise (26 x 18 m) and Bubble Wash (20 x 12 m) are
named, signed and lit, but have no rooms. Their front is a lit recess you walk into and stop.

K3 offers two options:
- **(a) One enterable ground-floor room each.** The recommendation. Layout data only:
  `rooms`, `doors` and `fixtures`. The pipeline carves, trims, lights and frames them like any
  enterable building:
  - Neon Koi: a lobby 10 m deep with a counter and closed booth doors;
  - Pachinko Sunrise: a floor with two rows of machines;
  - Bubble Wash: the machines and a bench.

  Nobody new stands in them.
- **(b) A framed entrance closed behind a lowered shutter.**

### 3.8 One implementation of each rule

- **The frame:** `detailing.door_frame`. City levels call it; E1M3's `frame_solids` shares
  REVEAL.
- **Door placement on a facade:** `City.facade`, the one place ground-floor openings are
  chosen, so shop bays, recesses and doors can't overlap.
- **The approach:** one function, `City.door_approach(b, door)`. The lot cut, the plan's check
  and the placement test's start points all read it; the placement test reads it from the
  exported level data, not a copy.

### 3.9 Checks

| Check | Where | On the old plan | On the new plan |
|---|---|---|---|
| Every declared door is carved at its fits and has a frame that fits its wall | `city_plan.check_doors` | names all 43 doors ("no frame") | clean |
| Every building that faces walkable ground (an edge of 2.2 m or more) shows a door | `city_plan.check_building_doors` | names 214 buildings: 80 blank walls, 78 dark recesses, 28 shop-only, 25 painted shutters, 3 false entrances | clean |
| Every exterior door's approach is clear, and reaches open ground | `city_plan.check_door_approaches` | names the 10 doors of section 2 | clean |
| The doors add at most 30,000 triangles | `city_plan` stats | 0 | about 22,000: 15,300 in dressing doors, 1,600 in shutter fittings, about 5,000 in the 43 frames |
| From 1 m outside every exterior door, the navmesh reaches the runner's spawn | `placement_test.tscn` | not run (no approaches exported) | 21 of 21, plus the shells' doors under K3 (a) |
| Frames do not z-fight | `detailing.assert_no_zfighting` | clean | clean, with every frame box registered |

`test_city_plan.py` pins each plan check twice:
- the committed hub passes it;
- a layout broken on purpose names the fault. The breaks are a door with no frame, a lot put
  back in front of the Fish Hall, and a lot with its door removed.

### 3.10 Rebuild

Every hub sector's mesh changes, so this means:
- a full rebuild;
- the lightmap bake of all eight sectors;
- a new navmesh;
- the placement, ragdoll, combat and swim tests again. Civilians, patrols and ladders stand
  near the changed lots, and a patrol leg may now pass an approach instead of a wall.

Captures: the before stills again from the same viewpoints, and a video walking the runner
through the Anchor's framed entrance, down Wire Lane and to the Fish Hall's north entrance.
The video is there because the point is how the street reads as you move.

## Risks / Trade-offs

- **Bake time.** Eight sectors on lavapipe take hours. The rebuild is one pass, run once the
  plan checks are clean.
- **Triangles.** About +22,000 on about 125,000. The doors sit in the sector meshes, so the
  draw calls don't change. Frame time is not measured here; the owner's machine is the place
  for that.
- **Lots change in front of 10 doors.** The civilians and patrols near them are re-checked by
  the plan and the placement test before anything is built. Wall lamps on those facades may
  move by a few metres.
- **Closed doors invite the use key (K1).** A dressing door with no prompt can read as broken.
  The recommendation keeps prompts for doors that open, so a prompt never lies. The real
  entrances are the lit, signed, framed ones.
- **Shops you can't enter.** A glazed door into a lit shop that never opens is a promise the
  hub doesn't keep. It is still better than a shop with no door. Enterable shops belong to
  later content.

## Alternatives considered

- **E1M3's glb doorway prop at hub sizes.** Rejected: the layout uses seven widths, and about
  300 prop instances would each be a scene and a draw call. Boxes in the sector mesh are
  lightmapped with the facade and cost nothing extra to draw.
- **Doors painted into the facade texture.** Rejected: no depth, no frame, and they fail R2 and
  R3. That is what the dark recesses already look like.
- **Blocking approaches before lots are split.** Rejected: it reshuffles every lot in the hub
  (section 3.6).
- **A wider margin round every named building.** Rejected: it would clear 0.6 m more round
  whole buildings and still not guarantee that an entrance reaches a street.

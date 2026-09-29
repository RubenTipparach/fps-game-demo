# Proposal: every building shows a door, and every door is built the way E1M3 builds one

## Why

The owner, 2026-09-29: "a lot of buildings are missing door ways or doors, review guidelines for
level design that we did in e1 m3".

E1M3, The Cistern (`tools/blender/build_cistern.py`), is the Blender reference level. Its door
rules are written down in three places: `CLAUDE.md` 7.2, checklist item 2 of
`docs/ut99_reference.md` ("Every doorway has a thick framed jamb and a lintel, inset from the
wall"), and `detailing.FRAMES`. The hub was built in the same Blender pipeline, but
`tools/levels/city_plan.py` took none of those door rules with it. Design section 1 reviews them
one by one.

**Measured** on the committed plan at seed 7: every building's ground-floor openings, recorded
by wrapping `city_plan.py`'s facade and recess builders. The instrument is described in design
section 2. The hub has 358 buildings: 343 generated filler lots and 15 named buildings (the MV
Anselm is a ship). Of these, 225 have a wall at least 2.2 m long facing ground a person can walk
on, which is room for a door. Here is what those 225 show that ground today:

| What the street sees | Buildings |
|---|---|
| A blank wall | 80 |
| A dark 1.0 x 2.15 m recess, no frame and no door in it | 78 |
| Shop windows and shutters, and no way into the shop | 28 |
| A roll-up or loading door painted on a recess, with no door beside it | 25 |
| A lit 3.0 x 2.85 m recess, 0.6 m deep, that can't be entered (Neon Koi, Pachinko Sunrise, Bubble Wash) | 3 |
| A real entrance that you can walk through, carved as a bare hole | 11 |

So 214 of 225 buildings show no way in, and the 11 that have one show it as a hole. The twelfth
enterable building, Precinct 9, doesn't make the list because its whole front is hidden (below).

**The doors that do exist:**
- **Exterior doors.** The 12 enterable buildings have 21 exterior doors. None of them has a
  frame, lintel or lamp, and 20 have no door leaf. The exception is the Rusty Anchor's back
  door, which is the only exterior door with a lock.
- **Interior doors.** There are 22, none framed; 4 have leaves.
- **Doors that face a wall.** 10 of the 21 exterior doors open onto a gap 1.20-1.35 m wide,
  facing the blank wall of a filler building:
  - both of the Harbor Fish Hall's 4 m main entrances;
  - Precinct 9's front door;
  - the MerSec checkpoint's door;
  - Mouse's den;
  - five back doors.

  The cause is the lot planner. It keeps a 0.9 m margin round named buildings, and each lot
  then shrinks by 0.3-0.7 m, so a filler building can stand 1.2 m in front of any door.

Why the hub reads as doorless:
- **Filler facades have no door kind.** Their four ground-floor kinds are shop windows, a dark
  recess, a painted shutter, and nothing at all on walls that face a side passage.
- **The named buildings carve their doors as holes.** No frame, no lintel, no lamp, and no leaf
  except where there is a lock.
- **Nothing keeps a door's approach clear,** and no check looks at one.

## What Changes

- **E1M3's door rules, at the hub's human scale.** Every door the hub builds keeps its clear
  opening (the layout's width: 1.4 m doors, 2.0-6.0 m entrances). It is carved at its frame's
  `fits` size, REVEAL (0.1 m) larger at each jamb and at the head. Its frame (jambs, a lintel
  and a threshold plate) stands proud of the wall, and it is registered with the z-fighting
  check.
  - One frame builder in `tools/godot/detailing.py` serves every city level, next to E1M3's
    `FRAMES`.
  - The Cistern and its doorway kit are unchanged.
- **The enterable buildings' 43 doors are framed.**
  - Entrances 2.0 m wide or more get a portal frame: pilasters with a plinth and a capital,
    and a lintel with a lit downlight and a corona. That is E1M3's doorway lighting and
    checklist items 3 and 4.
  - A door with a lock keeps its leaf; a door without one is an open, framed doorway (owner
    question K2).
  - A building's sign rises to clear its entrance frame.
- **Every building that faces walkable ground shows at least one door.** A closed door the
  runner can't open (K1), built from boxes in the sector mesh, in the building's style:
  - a glazed shop door in every shop bay;
  - a residents' street door on shop buildings of two or more floors;
  - a plank or sheet-metal door in each shanty, replacing the dark recess, some boarded and
    some padlocked;
  - a steel man door beside each workshop roll-up and dock loading door. Their painted
    recesses get a hood box and guide rails.

  About 250 doors in all.
- **Lamps favour doors.** The wall-lamp pass hangs its lamp over a door when one is within 2 m
  of the spot it would pick anyway, so doors are lit without adding a light.
- **Every exterior door has a clear approach.**
  - Entrances (2.0 m and wider): a strip 0.6 m wider than the frame on each side runs
    straight out to a street, lane or square, at most 12 m.
  - Service doors (1.4 m): a 2.0 m landing, and a way through to the street at least 1.2 m
    wide.
  - The approaches are cut from the lots after the lots are split, so only the lots that stood
    in front of a door change shape. The design map and the build share that code.
- **The three named shells.** Neon Koi, Pachinko Sunrise and Bubble Wash each get one enterable
  ground-floor room, or a framed door closed behind a shutter (K3).
- **Checks.**
  - `city_plan.py` refuses a door that is unframed, doesn't fit its wall, or has a blocked
    approach, and a building that faces walkable ground with no door.
  - It asserts the doors' triangle budget: at most 30,000 more, about a quarter of the hub's
    125,000.
  - The placement test walks the navmesh from outside every exterior door to the runner's
    spawn.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `level-geometry`: three requirements added: every doorway is framed, every building on the
  street shows a door, and every door opens onto ground a person can reach.

## Impact

- **Tools:**
  - `tools/godot/detailing.py`: the frame builder.
  - `tools/levels/render_map.py`: approaches cut from lots.
  - `tools/levels/city_plan.py`: frames, dressing doors, lamps over doors, approaches, the
    checks.
  - `tools/levels/layouts/hub.py`: the three shells' rooms if K3 says so.
  - `tools/levels/test_city_plan.py`: the regression tests.
- **Godot:** `placement_test.tscn` gains the approach walk. `LockedDoor` and `door_leaf.glb` are
  unchanged. Under K2's second option, the core also gets an unlocked door.
- **Rebuild:**
  - all eight hub sectors, since every sector's mesh changes;
  - a full lightmap rebake and a new navmesh;
  - the placement, ragdoll, combat and swim tests again, because civilians and patrols stand
    near doors;
  - the design map, since the lots in front of 10 doors change.
- **Owner questions:** K1, K2 and K3 in the survey.
- **Not in scope:**
  - interiors for filler buildings;
  - moving any door the layout places;
  - lock rules;
  - E1M3 itself.

# Tasks

The owner answered K1 to K3 on 2026-09-29: no prompt on doors that never open, automatic sliding
doors on the public entrances, and one room in each named shell.

## 1. Before

- [x] 1.1 Measure the committed hub: every building's ground-floor openings, and the clear
  depth in front of every exterior door (design section 2).
- [x] 1.2 Before stills from `docs/playtest/scripts/hub_doorways_before.json`, in
  `docs/screenshots/hub_doorways/`.

## 2. The rules in the plan

- [x] 2.1 `detailing.door_frame`: liners, architrave, portal and threshold, REVEAL from the one
  constant, the triangle counts; unit tests in `tools/godot`.
- [x] 2.2 `check_doors`, `check_building_doors` and `check_door_approaches` in `city_plan.py`.
  Run on the old plan, they must name 43 doors, 214 buildings and 10 doors; record their output.
  They name 43, 214 and 11 (design section 3.11: the frame-wide approach finds the garage's too).
- [x] 2.3 `City.door_approach`. `render_map.city_lots` cuts approaches after splitting, and
  only lots 11, 15, 226, 239, 242, 244, 245, 252, 257 and 280 may change. With frame-wide
  approaches, 15 change (design section 3.11).
- [x] 2.4 Named buildings: carve at the fits; frames and portals; lintel downlights; the sign
  above the lintel.
- [x] 2.5 Filler buildings: dressing doors by style in `City.facade`, drawn from each lot's RNG
  after its existing draws. Every other opening, sign and colour must be unchanged (compare
  the plan's other prims before and after). The doors take a stream of their own, placed after
  every other feature (design section 3.11).
- [x] 2.6 `wall_lamps` tries the spot over a door first.
- [x] 2.7 The three shells (owner K3): a room, an entrance and fixtures each in `hub.py`.
- [x] 2.8 `test_city_plan.py`: each check passes on the hub and names the fault on a layout
  broken on purpose. The triangle budget is asserted.

## 3. The sliding entrances (owner K2)

- [x] 3.1 `Doorway` opens for the groups it names (default "enemies", so the reference maps
  don't change); `data/doors.json` and its validation in the core; `SlidingDoorway` sets the
  timings from it.
- [x] 3.2 The sliding leaves in the Undercity prop kit, one pair per entrance size; the
  generator writes a scene per size (frame-free: the portal is in the sector mesh) and places
  one at each public entrance, leaves on the inside face.
- [x] 3.3 `check_sliding_room` in `city_plan.py`: each leaf's open position is clear of walls,
  fixtures and other doors.
- [x] 3.4 `door_test.tscn`: the runner walks up to the Anchor's entrance and it opens, walks
  away and it closes; a civilian walks through a closed entrance on the navmesh.

## 4. The built level

- [x] 4.1 Rebuild the eight sectors, the design map and the page; re-run the z-fighting check.
- [x] 4.2 Export the approaches in the level data. `placement_test.tscn` walks the navmesh from
  every exterior door to the spawn.
  It also checks that every person stands on the navmesh, which found Tank's aisle behind the
  Anchor's bar cut off (design section 3.11); the bar's short leg ends at x 98.5 now.
- [ ] 4.3 Rebake the lightmaps and the navmesh.
- [ ] 4.4 Placement, ragdoll, combat, swim, door and UI tests.

## 5. Records

- [ ] 5.1 After stills from the before viewpoints, and a video down Wire Lane, through the
  Anchor's sliding entrance and to the Fish Hall's north entrance.
- [ ] 5.2 A validation record; the design page section F19; archive.

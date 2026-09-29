# Tasks

Waiting on the owner's answers to survey K1-K3 before any source changes (CLAUDE.md 3). The
recommendations are provisional until then.

## 1. Before

- [x] 1.1 Measure the committed hub: every building's ground-floor openings, and the clear
  depth in front of every exterior door (design section 2).
- [x] 1.2 Before stills from `docs/playtest/scripts/hub_doorways_before.json`, in
  `docs/screenshots/hub_doorways/`.

## 2. The rules in the plan

- [ ] 2.1 `detailing.door_frame`: liners, architrave, portal and threshold, REVEAL from the one
  constant, the triangle counts; unit tests in `tools/godot`.
- [ ] 2.2 `check_doors`, `check_building_doors` and `check_door_approaches` in `city_plan.py`.
  Run on the old plan, they must name 43 doors, 214 buildings and 10 doors; record their output.
- [ ] 2.3 `City.door_approach`. `render_map.city_lots` cuts approaches after splitting, and
  only lots 11, 15, 226, 239, 242, 244, 245, 252, 257 and 280 may change.
- [ ] 2.4 Named buildings: carve at the fits; frames and portals; lintel downlights; the sign
  above the lintel.
- [ ] 2.5 Filler buildings: dressing doors by style in `City.facade`, drawn from each lot's RNG
  after its existing draws. Every other opening, sign and colour must be unchanged (compare
  the plan's other prims before and after).
- [ ] 2.6 `wall_lamps` tries the spot over a door first.
- [ ] 2.7 The three shells, as K3 decides.
- [ ] 2.8 `test_city_plan.py`: each check passes on the hub and names the fault on a layout
  broken on purpose. The triangle budget is asserted.

## 3. The built level

- [ ] 3.1 Rebuild the eight sectors, the design map and the page; re-run the z-fighting check.
- [ ] 3.2 Export the approaches in the level data. `placement_test.tscn` walks the navmesh from
  every exterior door to the spawn.
- [ ] 3.3 Rebake the lightmaps and the navmesh.
- [ ] 3.4 Placement, ragdoll, combat, swim and UI tests.

## 4. Records

- [ ] 4.1 After stills from the before viewpoints, and a video down Wire Lane, through the
  Anchor's entrance and to the Fish Hall's north entrance.
- [ ] 4.2 A validation record; the design page section F19; archive.

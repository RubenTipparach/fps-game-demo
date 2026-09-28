# Proposal: Meridian's towers around Low Harbor

## Why

The owner, playtesting on 2026-09-28: "There should be mega skyscrapers surrounding our little
slum area."

The hub's blurb calls it "the drowned bottom of Meridian, under the Skyway and the Halcyon
Spire". Nothing in the level shows the city it is the bottom of. Measured:
- **Nothing stands above 40 m.** The tallest thing is the Spire Foundations wall on the north
  edge. A map label promises "400 m of tower above" it, and there is no tower. The tallest
  building is 21 m.
- **Past the rooftops there is empty sky**, in every direction:
  `docs/screenshots/hub_skyline/baseline_north_from_market.png` and
  `baseline_east_over_the_cut.png`.
- **The Skyway stops 4 m past each edge** with closed ends, a bridge from nowhere to nowhere.
- **The view couldn't show towers even if they existed.**
  - The camera's far plane is 400 m.
  - The fog (exponential, 0.011) leaves 11 % of anything at 200 m and 1 % at 400 m.
  - The fog colour is lighter than the upper sky, so distant geometry would fade to pale ghosts,
    not dark silhouettes.

## What Changes

- **A skyline in the layout.** `hub.py` gains a `skyline` list: every tower's footprint, height,
  style and crown. The design map and the level both read it.
- **The Halcyon Spire:** 440 m, rising from beyond the north foundation wall. The label's
  promise, and the Upper City the U marker points at.
- **A near ring** of about a dozen megastructures, 120-320 m tall, 40-160 m beyond the edges:
  arcologies, residential stacks and corporate towers, eight of them named. **A far ring** of
  about 20 silhouettes, 200-650 m tall, 400-900 m out.
- **The Skyway carries on** into the city: its deck continues 200 m past each edge, as scenery.
- **A way to see them:**
  - a skyline shader that is unshaded, with procedural lit windows, neon crowns and blinking
    aircraft beacons;
  - it ignores the scene fog and applies its own darker haze, so towers read as dark masses with
    lit windows;
  - the camera's far plane goes from 400 m to 1,500 m.
- **A rule a check enforces:** from the hub's centre, every 30° of the horizon holds a tower
  rising at least 25° above it. No empty sky in any direction.
- **Searchlights** (owner, survey I8): two beams sweeping from the Halcyon Spire's crown.
- **The map shows it:** a locator inset in the legend draws Low Harbor inside the ring, with the
  named towers.

## Capabilities

### New Capabilities
- `hub-skyline`: the towers around a hub level, their coverage rule, and how they render.

### Modified Capabilities
- None.

## Impact

- **Layout and tools:** `tools/levels/layouts/hub.py` (`skyline`); `city_plan.py` plans a
  `skyline` sector and asserts coverage, bounds and budget; `build_undercity.py` meshes it;
  `render_map.py` draws the inset.
- **Godot:** `shaders/skyline_tower.gdshader`, the `skyline` material in the import presets,
  the player camera's far plane (`gen_undercity_scenes.py`), and a `skyline` sector in
  `hub.tscn` with no LightmapGI.
- **Budget:** at most 30,000 triangles and 6 draw calls for the whole skyline, no shadows, no
  collision. On a GPU its frame cost is measured with the rest (`combat-and-enemies` 5.1).

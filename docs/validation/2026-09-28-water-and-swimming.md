# Validation: water, swimming and ways out

The owner, playtesting the hub on 2026-09-28: "Falling into the Bay there's no water physics,
swimming, and no way to get back out, need a ladder or something. And need water physics." The
survey put this change first (I1) and settled drowning, stamina ("swimming consumes stamina but
slowly", I3), the exits (I4), the drowned locker (I5) and the breath meter D8 (I6). This record
covers `openspec/changes/archive/2026-09-29-water-and-swimming`, built on branch `claude/elegant-gauss-qwjhk1`.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb |
| Blender | 5.2.2 |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Python | 3.11, shapely 2, numpy, scipy |
| Seed | the swim and placement tests start a new run with a random seed; nothing they check depends on it |

## The checks

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core/Undercity.sln` | 109 of 109, 18 of them new: breath, stamina, the belt, saves, the water table's validation, the contact rule against the hub's exported water |
| Format | `dotnet format core/Undercity.sln --verify-no-changes` | clean |
| Level plan | `python3 tools/levels/city_plan.py hub --stats` | passes: z-fighting, carved rooms, the exit rule, people clear of the level and of the water |
| Plan tests | `python3 -m unittest discover -s tools/levels -p 'test_*.py'` | 13 of 13 (below) |
| Level data | `python3 tools/levels/export_level_data.py` | current: the hub's three water bodies |
| Placement test | `godot --headless --path game res://scenes/undercity/tests/placement_test.tscn` | 434 of 434: every person, spawn and patrol stop as before, and every ladder's foot, climb and landing with the player's collider |
| Swim test | `godot --headless --path game res://scenes/undercity/tests/swim_test.tscn` | 18 of 18 (below) |
| UI panel sizes | `godot --headless --path game res://ui/undercity/ui_size_test.tscn` | 312 of 312, the AIR panel among them (432 x 30) |
| OpenSpec | `openspec validate --all` | 19 of 19 |
| Dashes | CLAUDE.md 4 | none |

All of them run from `scripts/check.sh`; this change added the plan tests, the swim test and
the UI size test to it.

### The plan tests (`tools/levels/test_city_plan.py`)

| Test | What it pins |
|---|---|
| Every point of the hub's water is a short swim from a way out | the exit rule passes on the committed hub |
| A canal with its ladders removed fails, naming the canal and a point | the regression the spec names: `the_cut: ... the farthest is (x, y), with no way out at all` |
| A canal with one ladder fails at its far end | the rule measures a swim along the canal (more than 140 m), not across it |
| A quay low enough to climb onto needs no ladder | low quays count as ways out, read from `water.json`'s mantle rise |
| Quay ladders keep clear of bridges, boats and pillars | 3 m, the design's number |
| Every ladder reaches under the surface and tops out on a floor | 0.6 m under; the top clears the landing |
| A ladder steps off past a kerb onto level ground | the Cut's east quay |
| The outfall's rungs are a ladder | |
| A ladder opens the quay railing | proven to fail when the gaps are taken out |
| A civilian standing in the Cut is refused; one on the Tin Bridge is not | water in the standing check, bridge decks aside |
| A patrol across the Cut is refused naming the water; one over the Tin Bridge is allowed | water in the patrol-leg check |

### The swim test (`scenes/undercity/tests/swim_test.tscn`), in the hub, with the real keys

| Check | Requirement | Result |
|---|---|---|
| Walking off the quay by the Tin Bridge | The player wades and swims | into the Cut |
| Floating within 2 s, eyes 0.10-0.20 m above the surface | The player wades and swims | 0.149 m, swimming |
| Falling in doesn't hurt | | health 100 |
| Swimming forward at 2.9-3.1 m/s | The player wades and swims | 3.00 m/s |
| Looking level keeps a swimmer at the surface | | rose 0.000 m |
| With no stamina, 1.4-1.6 m/s | Swimming tires the swimmer | 1.50 m/s |
| The belt refuses to draw while swimming | No weapon while swimming | refused, nothing drawn |
| Crouch dives under | Breath runs out under water | submerged, eyes 0.68 m under |
| Breath drains under water | Breath runs out under water | 3.30 s used in 3.5 s |
| Jump rises to the surface | | yes |
| Breath refills in 3 s | Breath runs out under water | 45 of 45 |
| A quay ladder climbs out within 2 s | Ladders and ledges lead out of the water | 1.72 s, on the street past the kerb |
| The ship's boarding ladder climbs onto its deck | Ladders and ledges lead out of the water | on the deck at 1.2 m |
| "Climb down" is offered at a ladder's landing | Ladders and ledges lead out of the water | yes |
| Back climbs down and lets go floating | Ladders and ledges lead out of the water | swimming, eyes 0.13 m up |
| Jumping in front of a boat's deck climbs onto it | Ladders and ledges lead out of the water | on the deck at the surface + 0.50 m |
| A body in the Cut floats and comes to rest within 8 s | Bodies float and things sink | at the surface from about 4 s, bones 0.02-0.10 m under, still |
| An item dropped while swimming sinks to the bed | Bodies float and things sink | on the bed at -4.50 m |

## What building found

Each of these is in the design's "found in building" notes.

- **The dry dock is a moat.** The MV Anselm fills the basin, and buildings stand on its north and
  east walls, so the far corner was 42 m of swimming from a quay ladder. The ship hangs four
  boarding ladders.
- **A straight line was the wrong measure** for the exit rule: a Skyway pillar blocked it. The
  rule measures the swim.
- **Two quay ladders landed their climbers astride a kerb.** The placement test's first ladder run
  failed them; the plan now finds each ladder's landing on level ground.
- **Ladder speed 3.0 m/s** (designed 2.4): the first climb took 1.97 s of the 2 s allowed.
- **Buoyancy 1.8** (designed 1.15), and bodies in water aren't frozen: at 1.15 the settle-time
  freeze caught a rising body 1.5 m under the surface. At 1.3 it floated, but 77 % under: once
  the water was opaque (below), a body showed 5 cm above the surface and couldn't be seen from
  the quay. At 1.8 each bone rests half out, and the swim test's floating body settles with its
  bones 0.01 m under the surface on average.
- **Dropped items now fall to the floor** everywhere; before, a drop hung where it was dropped.

- **The first video showed black water from swimming height** (the design's named risk:
  transparent water gets no screen-space reflections, and no probe covered the water). A body
  floating 7.5 m away was lost in it. Six outdoor probes now cover the Cut, the dry dock and the
  gate channel, but the second video was still black: the water shader read the screen and
  depth textures, which made it transparent, and Godot skips screen-space reflections on
  transparent materials. The water is now opaque, its deep colour what murky water 2.3-4.5 m
  deep would show anyway, and it reflects the lit city. `tools/material_maker/
  test_shader_materials.py` pins it: the water shader reads no screen or depth texture and sets
  no alpha, and the material sets only parameters its shader declares.
  The body is now filmed from the quay's edge, looking down on it 6.4 m away.

The longest swim to a way out is 20.6 m in the Cut, 15.2 m in the dry dock and 15.3 m in the
dock gate channel. The hub has 17 ladders.

## Rebuild and bake

`build_undercity.py` rebuilt the hub's sectors (38 s). The navmesh was baked again (4,786
polygons), and every sector's lightmap with it, in one batch of 70 minutes on lavapipe:

| Sector | Bake | Changed |
|---|---|---|
| streets | 383 s | yes: ladders, railing gaps, landings |
| lantern_row | 1,463 s | yes |
| sump_market | 355 s | no (byte for byte) |
| drydock | 373 s | yes: the ship's boarding ladders |
| kiln | 379 s | no |
| tin_stacks | 826 s | no |
| spire_foundations | 136 s | no |
| skyway | 182 s | no |

The five sectors whose meshes didn't change baked to the same files.

## Captures

`docs/playtest/scripts/water_and_swimming.json`, run with `--write-movie` at `--fixed-fps 30`
(`BRUSHFIRE_SEED=7`), on the rebaked hub with the opaque water and buoyancy 1.8, from a clean
worktree of the branch's head (so nothing uncommitted from later work could show). The video is
`docs/screenshots/water_and_swimming/water_and_swimming.mp4` (27 s, 1280 x 720, with sound);
the stills beside it:

| Still | Shows | Requirement |
|---|---|---|
| `01_quay_by_the_tin_bridge.png` | the Cut from the quay: the water reflects the windows, lamps and the depot's neon | Water comes from the layout |
| `02_fallen_in.png` | from swimming height, the lights' reflections broken into streaks by the ripples, the quay wall 2.2 m above | The player wades and swims |
| `03_at_the_ladder.png` | a quay ladder's rungs from the water | Ladders and ledges lead out of the water |
| `04_climbed_out.png` | back on the quay, through the railing's gap | Ladders and ledges lead out of the water |
| `05_drowned_locker.png` | on the bed under the Tin Bridge, in the underwater tint, the locked locker's prompt | The player wades and swims |
| `06_air_running_out.png` | the AIR bar low and red under the health panel (D8) | Breath runs out under water |
| `07_body_floating.png` | a civilian's body floating spread out on the Cut, 6.4 m out from the quay's edge | Bodies float and things sink |
| `08_boarding_ladder.png` | the MV Anselm's boarding ladder from the dry dock's water | Every water body has a way out |
| `09_aboard_the_anselm.png` | on the ship's deck after the climb | Ladders and ledges lead out of the water |

The baselines from the owner's playtest stay beside them (`baseline_*.png`).

The body in `07` is small and dark: the hub is at night in the rain, and the corpse is in
dark clothes. It reads as a body from the quay but doesn't stand out, which is the scene more
than the rule.

## What the checks establish

- In the hub, a runner who falls in floats, swims at the designed speeds, tires slowly, holds
  their breath for 45 s and then drowns through the health rule, can't draw a weapon, and can
  always get out: every point of water is within 25 m of swimming of a ladder, and each ladder
  climbs out onto level floor with room to stand.
- Nobody the level places stands or patrols in water.
- A body in the water floats and settles at the surface; a dropped item sinks to the bed and can
  be taken there.

## What they don't establish

- **Frame cost.** Lavapipe doesn't measure it. The water reads the screen and depth textures,
  and the underwater view is a full-screen pass while the head is under; neither is measured on
  a GPU.
- **Wading.** No water in the hub is shallow enough to wade in; the wading rule is covered by the
  core's contact tests only.
- **Death by drowning.** Health reaches 0 through the health rule; what happens at 0 (the fade and
  the reload) is `hub-combat`'s, built next.
- **How it sounds.** The splash, stroke, tired stroke and gasp sounds and the low-pass under water
  were generated and wired, not listened to.

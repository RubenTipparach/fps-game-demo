# Validation: a crowd, not six twins

The owner, playtesting the hub on 2026-09-28, found the same six civilians everywhere. The
survey settled 18 civilian bodies, 3 MerSec faces and the runtime variation as designed (I13),
cyber-mod accessories on civilians (I14), and built this fifth (I1). This record covers
`openspec/changes/archive/2026-09-29-crowd-variety`, built on branch `claude/elegant-gauss-qwjhk1`.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb |
| Blender | 5.2.2 |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Python | 3.11, shapely 2, numpy |
| Seed | `BRUSHFIRE_SEED=7` for the hub capture; the core tests run seeds 1-100 |

## The checks

| Check | Command | Result |
|---|---|---|
| Bodies | `blender -b --factory-startup --python tools/blender/build_npcs.py -- --verify` | all 36 bodies rebuild byte for byte (run when the 14 new bodies were committed; no body changed since) |
| Accessories | `blender -b --factory-startup -P tools/blender/build_undercity_props.py` | 11 accessories, 52-244 triangles against the 800 budget, z-fighting clean; the kit's 17 other props rebuild byte for byte |
| Level plan | `python3 tools/levels/city_plan.py hub --stats` | passes, with the four talking partners placed |
| Level data | `python3 tools/levels/export_level_data.py` | 35 civilians in the crowd block, 9 of them sheltered |
| Hub build | `blender -b --factory-startup -P tools/blender/build_undercity.py -- hub` | three sector glbs changed, only in their new civilian markers: their meshes and binary buffers are byte-identical, so the lightmaps and navmesh stand |
| Import | `godot --headless --path game --import`, `setup_npc_import.gd`, `--import` | clean; the 22 older bodies' import options unchanged (after the fix below) |
| NPC scenes | `godot --headless --path game -s res://../tools/godot/gen_npc_scenes.gd` | 36 scenes, each with a 20-body ragdoll, the weapon grip (its transform unchanged) and the five mounts |
| Core tests | `dotnet test core` | 189 of 189 |
| Tool tests | `python3 -m unittest discover -s tools/{levels,godot,material_maker}` | 23, 4 and 3, all passing |
| Project build | `dotnet build` in `game/` | 0 warnings, 0 errors |
| Placement | `placement_test.tscn` | 612 of 612, 175 of them accessories |
| Ragdolls, combat, lighting, swimming, UI | `ragdoll_test.tscn`, `combat_test.tscn`, `lighting_test.tscn`, `swim_test.tscn`, `ui_size_test.tscn` | 36 of 36, 23 of 23, 15 of 15, 18 of 18, 312 of 312 |
| OpenSpec | `openspec validate --all` | all valid |

### The crowd's tests

| Test | Pins |
|---|---|
| The hub places every civilian | the crowd block has each of the hub's 35 civilians |
| No two civilians within 15 m share body and palette, seeds 1 to 100 | the lookalike rule on the hub's real places |
| No body is used more than three times, seeds 1 to 100 | the body cap |
| The same seed gives the same crowd whatever order the places come in | body, palette, accessories, scale, idle and partner; no hash order |
| A different seed gives a different crowd | more than half the civilians change body |
| Market civilians are shoppers and dock civilians dockhands | roles by district |
| About a third of the civilians in the open who may carry one hold an umbrella, and nobody sheltered | 0.35 within 0.05 over 100 seeds |
| An umbrella is held up and no slot carries two | the forced idle, the slots, the scale range |
| Civilians placed in a pair face each other and talk unless an accessory sets the idle | the four placed pairs, both directions |
| Nobody stands in two pairs | three civilians in a line: the closest two pair |
| Every accessory has its prop and a mount the bodies carry | the glb on disk and the mount in `npc_bodies.json` |
| A role naming a pool that isn't there is refused | validation |
| Every NPC model has a generated scene | now over the crowd's body pool too |
| Every body is retargeted by its skeleton's imported path (tools) | the import fix's regression test |

## Found and fixed while building

- **Re-running the import setup broke the older bodies' retarget.** `setup_npc_import.gd` read
  each body's skeleton path from its imported scene; once retargeted, that shows the new name
  `GeneralSkeleton`, and the options were rewritten under a key that matches nothing at import
  time. A clean import would have left those bodies un-retargeted. It now keeps the key a
  first pass wrote. `tools/godot/test_npc_imports.py` failed on the broken files and passes
  now.
- **`Idle_Torch` raises the left hand,** not the right (measured: the left palm at 1.27-1.32 m
  and 0.45 m forward, the right at the side), so the umbrella moved to a left-hand mount.
- **The head joint is at nose level.** The first visor, respirator, implant and headphones
  were fitted 4-6 cm too high; measured on eight bodies, the eyes are 0.03-0.06 m above the
  joint and 0.08-0.10 m forward.
- **Umbrellas pushed into market awnings.** The placement test's new accessory check failed
  civilians 10 and 11 by the stalls: an open canopy reaches about 1 m from its holder. The
  plan now registers every awning, and a civilian within that reach of one is sheltered and
  never opens an umbrella.
- **The combat test could miss its own trigger pull under load.** The weapon reads the trigger
  each drawn frame, and the test held it for two physics ticks; with another capture running,
  Silk's surrender check failed once ("Calm, 9.2 m away") and passed on a rerun. The test
  now holds the trigger through a whole drawn frame; it passed 23 of 23 under the same load.

## Captures

Two sets, in `docs/screenshots/crowd_variety/`. Stills, not a video: nothing here moves but the
idles.

**The lineup** (`scenes/undercity/tests/crowd_lineup.tscn`, `Checks/CrowdLineup.cs`), at
1600 x 900 under a plain three-light studio: every body in rows of seven, first as built, then
each civilian in a palette and two accessories so that all eleven are shown, dressed by the
game's own code (`CrowdDress`) and holding the idle their accessories set.

| Still | Shows | Requirement |
|---|---|---|
| `01_as_built_civ_a_to_civ_g.png` | civilians A to G as built: their own clothes, one idle | The body pool covers the CC0 range |
| `02_dressed_civ_a_to_civ_g.png` | the same seven recoloured (civilian B's red shirt reads yellow, her jeans purple) with an umbrella held up in the left hand, a cap and headphones, a bag, a briefcase, a beanie and a respirator, a lit prosthetic, a visor | Civilians vary at runtime |
| `03_dressed_civ_h_to_civ_n.png` | civilians H to N dressed: an afro under an umbrella, braids, the fedora body with a cigarette and a prosthetic | Civilians vary at runtime |
| `04_dressed_civ_o_to_mersec_c.png` | civilians O to R dressed, then MerSec's three faces under the one helmet | The body pool covers the CC0 range |

**The hub** (`docs/playtest/scripts/crowd_variety.json`, `BRUSHFIRE_SEED=7`, 1600 x 900):

| Still | Shows | Requirement |
|---|---|---|
| `05_market_crowd.png` | the Sump Market from its north side: shoppers, two lit umbrellas in the rain, one with a bag | No lookalikes nearby |
| `06_talking_pair.png` | civilians 10 and 32 by a stall, face to face, talking | Civilians placed together talk |
| `07_umbrella_in_the_rain.png` | civilian 14 (civ_o, olive) holding an umbrella up in the left hand | Civilians vary at runtime |
| `08_lantern_row_pair.png` | civilians 19 and 34 talking inside, no umbrellas under a roof | Civilians placed together talk |

The first run of the hub script framed the market pair from behind the stall, and it was
stopped by its own 30-minute timeout before the last two shots: the pair's viewpoint moved to
the stall's east side, and shots 2 to 4 were taken again in one run from a new load of the hub.

## What the checks establish

- The crowd rule holds on the hub's real placements for seeds 1-100: no lookalikes within
  15 m, no body over three times, roles by district, umbrellas only in the open, talking pairs
  where the layout places them.
- Every accessory a civilian's role allows clears the built level on every body of the pool at
  both ends of the height range, in its own pose.
- The body pool, the mounts and the props agree with the data (the real files are loaded).

## What they don't

- Clipping between an accessory and its wearer's own clothes and hair is checked by eye on
  the lineup, not by a test. A hat on a big hairstyle can still cut through it.
- A civilian's recolour is judged by eye; nothing measures whether a palette reads as dyed
  cloth.
- Frame time: a cloud session renders on lavapipe and doesn't measure it.

# Validation: generated NPC bodies, shared animation and ragdolls (npc-characters)

The owner answered survey H1-H3 on 2026-09-28: "Do recommend for now, conditionally I will
review again later." This step built the NPC pipeline the design describes and put its 22
bodies into the hub. It records what was checked and what wasn't.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe, LLVM 20.1.2), Xvfb at 1920 x 1080 |
| Blender | 5.2.2, with MPFB2 2.0.17 and the CC0 MakeHuman system assets, both SHA-pinned |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | `BRUSHFIRE_SEED=7`; captures at `--fixed-fps 60` |

## Checks

| Check | Command | Result |
|---|---|---|
| Table | `python3 tools/blender/npc_data.py` | OK: 22 bodies (16 named, 6 civilians), 40 gear pieces in 15 sets |
| Build | `blender -b --factory-startup --python tools/blender/build_npcs.py` | 22 bodies, 10,104-15,856 triangles (budget 16,000), 3 materials, four 1024 px WebP textures and 53 bones each; gear passes the poke-through test at rest and at the stress pose |
| Reproducible | `... build_npcs.py -- --verify` | "OK 22 bodies match their committed glbs" (126 s) |
| Refusals | the build with a planted asset, a 10,000-triangle budget, a zip with one extra byte | each exits 1 naming the NPC or the pack, and writes nothing |
| Clips | `blender ... build_npc_clips.py`, then Godot's import | Surrender and Cower, 2.0 s, looping, loop error under 3e-7; imported as `undercity/Surrender` and `undercity/Cower` |
| Import | `setup_npc_import.gd`, reimport, `gen_npc_scenes.gd` | 22 retargeted skeletons (`GeneralSkeleton`), 22 NPC scenes of 17 KB, each with a 20-body ragdoll |
| Ragdoll | `godot --headless --path game res://scenes/undercity/tests/ragdoll_test.tscn` | 22 of 22 passed: peak 7.0-10.4 m/s with a 40 N s chest push, every body frozen at 3.02 s and off the 0.45 m step |
| Core tests | `dotnet test core` | 91 passed (6 new: the body table, and every NPC model has a generated scene) |
| Scripted run | `BRUSHFIRE_AUTOTEST=docs/playtest/scripts/npc_bodies.json` | see below |

## The scripted run

`docs/playtest/scripts/npc_bodies.json` at `--fixed-fps 60`, in an empty save folder. Stills are
in `docs/screenshots/npc_bodies/hub_*.png` (downscaled to 1280 x 720); the Blender lineups and
faction close-ups beside them show every body in flat light.

| Step | Result | Still |
|---|---|---|
| Tank | The generated body at the Anchor door, idling | `hub_01_tank.png` |
| Talk to Tank | He turns to the runner and gestures (`Idle_Talking`) under the dialog | `hub_02_tank_talking.png` |
| Nguyen, Silk | Nguyen's paper cap at his stall; Silk's suit, magenta tie and glasses | `hub_03_nguyen.png`, `hub_04_silk.png` |
| Dace, Petra, Skiv, Jax | Each at their spot; Petra's orange overalls read at once, the others stand in the night's shadow | `hub_05` to `hub_08` |
| A civilian, killed by the test harness | The body collapses, falls and is at rest on the street | `hub_09` to `hub_11` |

The process exited 139 (a segfault) when it quit, after the last still, with no crash report.
The same happens on this branch before this change (a fresh clone quitting from the hub), and
two headless runs that load the hub, collapse a body and quit exit 0. It shows only with the
lavapipe Vulkan driver after a long rendered session, which points at the driver; it isn't
established either way on real hardware.

The video `docs/screenshots/npc_bodies/npc_motion.mp4` comes from
`docs/playtest/scripts/npc_motion.json`, written with `--write-movie` at 30 fps: a MerSec patrol
walking, Tank talking, and a civilian falling to rest.

## What the checks establish

- Every NPC body is generated from the committed table and pinned packs, rebuilds byte for
  byte, stays in budget, and takes no asset from outside the allowlist.
- Every body retargets onto the humanoid profile and plays the one shared library.
- Every body falls as a ragdoll without exploding and is frozen at the settle time.
- In the hub, the bodies stand at their spots, animate, face the runner in conversation, and
  fall when killed by the test harness.

## What they don't establish

- **Frame cost.** Lavapipe doesn't measure it. The hub now draws 25 skinned bodies of 10-16k
  triangles where the segmented figures had about a tenth of that; this needs a GPU (task 5.2).
- **Death in play.** No weapon fires yet, so only the test harness's `kill` step collapses a
  body. Combat (`combat-and-enemies`) is what will.
- **Clothes at extreme poses.** The authored gear is tested against the body; the CC0 clothes
  are not.
- **The look.** The owner judges it in the hub (survey H2, conditional).

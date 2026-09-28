# Spike: the NPC body pipeline (measurement, 2026-09-27/28)

The measurement behind `openspec/changes/archive/2026-09-28-npc-characters`. It checked whether MPFB2 can generate
game-ready NPC bodies headless in Blender, whether one CC0 animation library drives all of them
in Godot, and whether their ragdolls fall and settle. **It is reference only and part of no
build** (CLAUDE.md 5.6, "a reference checkout is never part of a build"). The change's tasks
turn it into `tools/blender/build_npcs.py`, `tools/deps/fetch_character_tools.py` and the
generated scenes.

The shell scripts name the measurement container's scratch folder; set `NPC` to your own
working folder to rerun them.

## Inputs, pinned

| Input | Version | Source | SHA-256 of the download | Licence |
|---|---|---|---|---|
| MPFB2 (Blender extension) | 2.0.17 | [extensions.blender.org/add-ons/mpfb](https://extensions.blender.org/add-ons/mpfb/) | `4f0a879d64a39bf646fbf5f53601ac678855da329d650617dca5737548239a87` | code GPLv3; its data CC0; output unclaimed ([LICENSE.md](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md)) |
| MakeHuman system assets | the `_cc0` pack | [files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip](https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip) | `b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107` | CC0, by the pack's name and the MPFB licence page; the 147 asset files carry no licence lines of their own |
| Universal Animation Library, Standard | 2025-03-25 build | [quaternius.com/packs/universalanimationlibrary.html](https://quaternius.com/packs/universalanimationlibrary.html) | `18ff1a7215f4852b320203e8aaf02a1578b5c8eef9027fbaedfcedc7b85a3ac2` | CC0 1.0, per the `License.txt` inside the zip |
| Blender | 5.2.2 | | | |
| Godot | 4.7.2 stable mono, Jolt Physics | | | |

## Files

| Path | Does |
|---|---|
| `blender/01_install_mpfb.py` | Installs and enables MPFB in an isolated Blender user folder, unzips the asset pack where MPFB looks |
| `blender/npc_specs.json` | The four test NPCs: three hand-specified, one from seed 1234 |
| `blender/build_npcs.py` | Spec to glb: MPFB's HumanService, the `game_engine` rig, low-poly proxies, decimation, the 3-material 1024 atlas |
| `blender/render_lineup.py`, `compose_sheets.py` | The lineup and stress-pose stills |
| `godot/bonemaps/*.tres` | Hand-written `BoneMap`s to `SkeletonProfileHumanoid` for MPFB's `game_engine` rig and UAL's rig (53 of 56 profile bones; no eyes or jaw) |
| `godot/tools/setup_import.gd` | Writes the retarget import options (bone map, `%GeneralSkeleton`, rest fixer) |
| `godot/tools/capture_anims.gd` | Plays UAL clips on each body and captures stills |
| `godot/tools/ragdoll.gd` | Builds the 20-capsule ragdoll and drops each body off a 0.45 m step, logging speed, joint gaps and sleep per frame |
| `metrics/*_metrics.csv` | Those logs: Jolt at 60 and 120 Hz, GodotPhysics3D at 60 and 120 Hz |

Stills: `docs/screenshots/npc_pipeline/`. Results and decisions: the change's `design.md`.

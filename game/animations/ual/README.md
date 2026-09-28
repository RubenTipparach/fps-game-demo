# Universal Animation Library, Standard (Quaternius)

`ual_standard.glb` is the shared animation library every Undercity NPC plays
(openspec/changes/npc-characters, design section 6). It is borrowed as is (CLAUDE.md 5.6,
provenance):

| | |
|---|---|
| Source | [quaternius.com/packs/universalanimationlibrary.html](https://quaternius.com/packs/universalanimationlibrary.html), the Standard download |
| Download | `ual_standard.zip`, SHA-256 `18ff1a7215f4852b320203e8aaf02a1578b5c8eef9027fbaedfcedc7b85a3ac2` (pinned in `tools/deps/character_packs.json`) |
| File in the zip | `Animation Library[Standard]/Godot/AnimationLibrary_Godot_Standard.glb`, dated 2025-03-25 |
| Licence | CC0 1.0, per `License.txt` (copied here from the zip) |
| Clips | 46; Godot strips the `_Loop` suffix and marks those clips looping |

`tools/godot/setup_npc_import.gd` writes its import options: imported as an `AnimationLibrary`,
retargeted to `SkeletonProfileHumanoid` through `game/animations/bonemaps/ual_rigify_def.tres`.
Don't edit the glb; replace it from the pinned zip.

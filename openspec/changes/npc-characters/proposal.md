# Proposal: NPC bodies from an open-source generator, a shared animation library and ragdolls

## Why

The owner, 2026-09-27: "npc design: use blender and find opensource npc character generator, and
use any systems you can find to rig, animate, and ragdoll NPCs". And: "any npc can be shot, if
they can defend themselves they will."

The hub's first characters are segmented UT99-style figures (decision C1,
`tools/blender/build_characters.py`). They read well from a distance but are faceless mannequins
up close, with five hand-keyed clips. Combat needs much more:
- NPCs that run, crouch, aim, fire, flinch, cower, surrender and die;
- bodies that fall like bodies.

Hand-keying all of that per character doesn't scale to the Drains and the Yard.

## What Changes

- **Bodies from MPFB2**, the MakeHuman plugin for Blender
  ([licence](https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md)):
  - GPLv3 code, CC0 assets;
  - the MakeHuman team claims nothing over its output;
  - it scripts from Python inside Blender.

  A committed build script turns a character table (body shape, skin, hair and clothes) into one
  `.glb` per NPC. The tools and asset packs stay outside the repository and are fetched by a
  script that pins their versions and checksums.
- **One skeleton profile.** Every NPC is rigged with MPFB's game-engine rig and mapped to
  Godot's `SkeletonProfileHumanoid` at import. Godot's retargeting then lets every body play the
  same animations
  ([Godot docs](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/retargeting_3d_skeletons.html)).
- **One animation library.** Quaternius' Universal Animation Library
  ([CC0](https://quaternius.com/packs/universalanimationlibrary.html)) has 120+ clips on a
  humanoid rig built for retargeting: locomotion, sitting, combat and guns, deaths and emotes.
  It becomes `AnimationLibrary` resources that every NPC shares. Clips it lacks, such as cower,
  hands up and talk gestures, are added in Blender on the same rig.
- **Ragdolls.** Each NPC scene has a `PhysicalBoneSimulator3D` with one `PhysicalBone3D` per
  major bone (capsules, joint limits), generated from a humanoid ragdoll profile. Death and
  knockout hand the body to physics. It settles, then freezes.
- **The segmented characters retire.** `build_characters.py` and its models stay only until the
  new bodies land, then go.

## Capabilities

### New Capabilities
- `npc-characters`: how an NPC's body is generated, rigged, animated and ragdolled, and the
  budgets it has to meet.

### Modified Capabilities
None. The segmented characters were never specified as a requirement.

## Impact

- `tools/blender/build_npcs.py` (new) and `tools/blender/npcs.json` (the character table).
- `tools/deps/fetch_character_tools.py` (new) fetches MPFB and the asset packs, pinned by version
  and SHA-256.
- `game/models/npcs/*.glb` and `game/animations/*.res` (the shared library).
- `game/scenes/undercity/npc.tscn` gains the ragdoll and the humanoid skeleton.
- The combat-and-enemies change consumes all of this (its task 4.1).
- The design is measured before it's settled: see `design.md`, which records what was tried in
  this container, with numbers.

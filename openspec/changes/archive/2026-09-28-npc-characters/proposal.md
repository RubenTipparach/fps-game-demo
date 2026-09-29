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

Then, on the design (survey H1-H3, 2026-09-28): "Do recommend for now, conditionally I will
review again later." So the pipeline is adopted, the look is judged once the bodies stand in the
hub, and the faction outfits are authored in Blender. All three stay open to the owner's review.

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
  ([CC0](https://quaternius.com/packs/universalanimationlibrary.html)) is a humanoid rig built
  for retargeting. Its CC0 Standard download holds 46 clips (measured; an earlier draft said
  120+): locomotion, crouching, sitting and talking, pistol and melee, hits and a death. It
  becomes one `AnimationLibrary` that every NPC shares. Clips it lacks, first surrender and
  cower, then rifle holds, are keyed in Blender on the same rig.
- **Ragdolls.** Each NPC scene has a `PhysicalBoneSimulator3D` with 20 capsules and joint
  limits, generated from a humanoid ragdoll profile, on the Jolt physics the project already
  uses (GodotPhysics3D exploded in the measurement). Death and knockout hand the body to
  physics; after 3 s it freezes in its pose.
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
  this container, with numbers. The measurement's scripts are in `docs/spikes/npc-pipeline/`.
- `tools/deps/character_packs.json` (new) is the allowlist of packs the build may take assets
  from, since the asset files carry no licence lines of their own.

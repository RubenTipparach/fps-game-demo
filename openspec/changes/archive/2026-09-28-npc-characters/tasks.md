# Tasks

## 0. Measurement (done)

- [x] 0.1 MPFB2 headless in Blender, the budget, the shared UAL library in Godot, and ragdolls
  on Jolt and GodotPhysics3D, measured. Scripts, bone maps and logs in
  `docs/spikes/npc-pipeline/`; stills in `docs/screenshots/npc_pipeline/`; results in `design.md`.

## 1. Tooling

- [x] 1.1 `tools/deps/character_packs.json` (URL, SHA-256, licence, where the licence is stated)
  and `tools/deps/fetch_character_tools.py`, which downloads outside the repository and refuses
  a hash mismatch.
- [x] 1.2 `tools/blender/npcs.json` (the table, `budget`, the civilian random range) and
  `tools/blender/build_npcs.py`, from the spike's `build_npcs.py`. It refuses an asset outside
  the allowlisted packs and a body over budget, naming the NPC and the number.
- [x] 1.3 A check that two builds write byte-identical glbs.
- [x] 1.4 Measure Godot 4.7's import of WebP textures inside a glb. It imports cleanly and
  extracts `.webp` files: WebP at quality 85 (design section 10).
- [x] 1.5 The bone maps as committed `.tres`, and a tool script that writes the retarget import
  options for every body glb and the UAL library.

## 2. First look (owner H2)

- [x] 2.1 Build Tank, Nguyen and one civilian. Put them in the hub at their spots, and capture
  them in daylight and neon for the owner.

## 3. Animation

- [x] 3.1 UAL Standard as the shared `AnimationLibrary`; an `AnimationPlayer` (design section 10:
  a tree comes with combat) on `NpcActor` with idle, walk, talk and sit from the clip map in
  `data/npc_bodies.json`.
- [x] 3.2 Key surrender (hands up) and cower in Blender on the UAL rig, and add them to the
  library. Rifle holds follow with MerSec.

## 4. Ragdolls

- [x] 4.1 A generated ragdoll profile (20 capsules, the joint table, the collision
  exceptions), built into `npc.tscn` by `gen_undercity_scenes.py`.
- [x] 4.2 Death and knockout hand the body to physics; after `ragdoll_settle_s` (3.0 s, in
  data) it freezes in its pose. A test drops a body off the 0.45 m step and checks it is frozen
  at 3 s.

## 5. The rest, and captures

- [x] 5.1 Every named NPC and the civilian seeds. Outfits as the owner decides (H3).
- [x] 5.2 Moved to `combat-and-enemies` (its task 5.1): frame time needs a GPU, and combat puts
  the most bodies on screen.
- [x] 5.3 Video: idle, talk, walk and a death to rest, on three bodies (CLAUDE.md 9).
  `docs/screenshots/npc_bodies/npc_motion.mp4`, 11.9 s.
- [x] 5.4 Retire `tools/blender/build_characters.py` and the segmented models.
- [x] 5.5 Move the requirements into `openspec/specs/npc-characters` with their checks, and
  archive the change.

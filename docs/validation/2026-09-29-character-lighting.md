# Validation: faces, skin and coloured gels

The owner, playtesting the hub on 2026-09-28: faces are too dark in conversation, skin needs
normal maps, the runner needs a light source, and coloured gels suit cyberpunk. The survey
accepted the design (I9 to I12) and built it third (I1). This record covers
`openspec/changes/character-lighting`, built on branch `claude/elegant-gauss-qwjhk1`.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe), Xvfb, 1280 x 720 for the face shots |
| Blender | 5.2.2, MPFB 2 and the SHA-pinned CC0 packs |
| Godot | 4.7.2 stable, mono, Jolt Physics at 60 Hz |
| .NET | 8.0.425 |
| Seed | `BRUSHFIRE_SEED=7`; the face shots run at a fixed 30 fps |

## The checks

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core/Undercity.sln` | 177 of 177, 4 of them new: the motivated key side twice, a district's gels, the nearest district |
| Bodies | `blender -b --factory-startup --python tools/blender/build_npcs.py -- --verify` | all 22 rebuild byte for byte: 3 materials and 5 textures of 1,024 px each |
| Materials | `python3 -m unittest discover -s tools/godot -p 'test_*.py'` | 3 of 3: the committed skin and outfit materials are what the generator writes, one of each per body, and the skin's F0 is 0.028 |
| Import | `setup_npc_import.gd`, then `godot --headless --path game --import` | clean; every body's skin and outfit take their generated materials, and the 44 normal maps stay lossless with 3D detection off |
| Lighting test | `godot --headless --path game res://scenes/undercity/tests/lighting_test.tscn` | 15 of 15 (below) |
| Placement, swim, combat, UI tests | as `scripts/check.sh` | 434 of 434, 18 of 18, 23 of 23, 312 of 312 |
| OpenSpec | `openspec validate --all` | all valid |

### The lighting test, in the hub, with the real use key

| Check | Result |
|---|---|
| Every person's meshes are on the world's layer and the characters' | 50 people |
| The runner's own view isn't on the characters layer | none of it |
| The runner carries the wrist light | on the camera |
| The wrist light lights characters only | cull mask 2 |
| It is always on and never baked | visible, bake mode disabled |
| Its energy and reach are the data's | 0.6, 4.5 m |
| Silk is in the hub, and stands in Lantern Row | `npc_silk`, `lantern_row` |
| A conversation opens one rig | 1 |
| The rig lights characters only | key, rim and accent: cull mask 2 |
| The rig ramps in to the data's energies | key, rim, accent at their data values |
| The rim and accent wear Lantern Row's gels | magenta and cyan |
| The key stands on the side the rig was given | right, as the rig says |
| The view narrows to the framing's width | 48 degrees, from 67.7 |
| The rig ramps out and is freed when the conversation ends | gone |

## What building found

Each is in the design's section 8.

- **The derived skin normal was far too strong as designed**, and the gels' signs contradicted
  their descriptions: both fixed before any capture.
- **The eyes share the outfit's material**, so their wet roughness rides in the outfit normal
  map's alpha rather than a material of their own.
- **The skin material had drifted from the design's table** and now writes its numbers.
- **The face box was in the wrong units**, and **the instrument was corrected** on the first
  captures: the face point is the eyes, the ratio is of light, the rim is what the rig adds to
  the head's edge, and the world is the frame outside the speaker.
- **One key can't meet the face target across skin tones** (survey J1, open): the key that
  takes Tank's dark face to 95 would take Petra's pale one to about 216.

## The faces

Measured with `tools/measure/face_luma.py` on 1280 x 720 shots at seed 7. The first run
(`docs/playtest/scripts/character_lighting.json`) took the rig off and on for Tank, Silk, Petra
and Nguyen before its 30-minute limit; the tuning run
(`docs/playtest/scripts/character_lighting_tune.json`) took the rig again with round 1's
energies, and Lin off and on. Rig-on shots are measured against the first run's rig-off shots
of the same speaker, except Lin's, from the same run.

| Speaker | Without the rig | Round 0 (the design's energies) | Round 1: key 2.2 at 55 degrees, rim 6.0 at -120 | Target |
|---|---|---|---|---|
| Tank, the Anchor's bar | 21 | 54 | 59; ratio 1.51; rim +66 | 95-150; 2-4; +20 |
| Silk, Lantern Row | 54 | 104 | 112; ratio 1.51; rim +86 | |
| Petra, the depot | 100 | 140 | 152; ratio 1.13; rim +99 | |
| Nguyen, his stall | 88 | | 180; ratio 1.15; rim +96 | |
| Lin, the shrine hall | 145 | | 189; ratio 1.05; rim +93 | |

The world outside the speaker changed by 0.00-0.40 % in every pair (target under 2 %). Round 0's
means are from the corrected face box laid over the first run's shots.

What round 1 shows:
- **The rim now shows on every speaker**, and **the world keeps its mood.**
- **Silk is in the band.** Tank is under it, at 59; Petra, Nguyen and Lin are over it.
- **No speaker reaches the 2:1 ratio.** In a dark place the wrist light, from the camera, fills
  the shadow side; in a lit place, the room's light is most of what a face gets.

One key can't meet the targets across skin tones and places: survey J1 (open) asks how to
expose each face. The energies stay at round 1 until the answer.

## What the checks establish

- Every person is on the characters layer, and the wrist light and the conversation rig light
  that layer and nothing else; the rig takes the side and the colours the rules give it, ramps in
  and out, and the view narrows as mockup D9 says.
- Every body's skin carries the derived normal, the roughness mask and the scattering the design
  gives it, the eyes their wet roughness, and every body rebuilds byte for byte within budget.

## What they don't establish

- **Frame cost.** Subsurface scattering is a screen-space pass and the rig adds three lights in
  conversation; lavapipe measures neither.

# Validation: faces, skin and coloured gels

The owner, playtesting the hub on 2026-09-28: faces are too dark in conversation, skin needs
normal maps, the runner needs a light source, and coloured gels suit cyberpunk. The survey
accepted the design (I9 to I12) and built it third (I1). This record covers
`openspec/changes/archive/2026-09-29-character-lighting`, built on branch `claude/elegant-gauss-qwjhk1`.

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
- **One key can't meet the face target across skin tones** (survey J1, since answered: the lighting stays, and skin follows where a character stands): the key that
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

One key can't meet the targets across skin tones and places: survey J1 asked how to
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

## Dry indoors, wet in the rain (owner J1)

The owner answered J1 on 2026-09-29: "tank looks fine with lighting, I think you made him too
shiny, he's not wet in doors.... so you might have to tweak shaders based on where characters
are." The energies stay at round 1; the face band and the ratio are recorded, not gated. Design
section 9 says what was built. Same machine, Godot, .NET and seed as above.

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core` | 201 of 201, 12 of them new: the shelter rule on the hub's real roofs (Tank at the bar dry, Dace at the checkpoint gate in the rain, a civilian under the Skyway and the middle of a shop awning dry, the Anchor's roof never sheltering the people on it), the step's rates (20 s to soak, 240 s to dry, a damaged value restarting from the place), and what validation refuses |
| Materials | `python3 -m unittest discover -s tools/godot -p 'test_*.py'` | 7 of 7 material tests, 4 of them new: every parameter the generator writes is a uniform of its shader, both shaders take `wetness`, an instance uniform the skin and the outfit share sits at the same index in both, and every global a shader reads is declared in `project.godot` and set by name from data |
| Level data | `python3 tools/levels/export_level_data.py`, then `git diff` | current: 414 shelters in `hub.json` |
| Lighting test | `godot --headless --path game res://scenes/undercity/tests/lighting_test.tscn` | 24 of 24, 9 of them new (below) |
| Fast checks | `scripts/check.sh --fast` | pass |
| OpenSpec | `openspec validate --all` | all valid |

### The lighting test's new checks

| Check | Result |
|---|---|
| Tank and Dace are in the hub with bodies | wetness 0.00 and 1.00 |
| Tank behind the Anchor's bar is under a roof and dry | sheltered, 0.00 at (99.3, 0.15, 55.5) |
| Dace at the checkpoint gate is in the rain and soaked | not sheltered, 1.00 at (169, 0, 155.5) |
| Every mesh of each body carries its wetness | 2 meshes each, at 0.00 and 1.00 |
| Each skin is drawn by the skin shader | `tank_skin` and `dace_skin` are ShaderMaterials of `character_skin.gdshader` |
| A soaked body under a roof dries at the data's rate | 0.9957 after 1 s (0.9948 to 0.9958 allowed, the step carrying up to one update's leftover time) |
| And its meshes follow | 0.9957 |

### What building found

- **All five capture speakers stand under a roof.** Silk is in the Anchor's back room, Petra in
  the depot, Lin in the shrine and Nguyen under the Skyway. Dace, at the checkpoint gate with
  nothing overhead, joined the captures as the rain case.
- **The first capture's skin ignored its wetness.** The skin and the outfit are surfaces of one
  mesh instance, and each shader declared `wetness` at its own instance index; Godot warned 108
  times that only the first would display correctly. Both now pin it at index 0, and a material
  test refuses a shared instance uniform without one index. The rerun logged no such warning.
- **Three civilians hold umbrellas under the Skyway** (civ_16, civ_26 and civ_27): the crowd's
  umbrella flag doesn't know the deck. They are dry by the roof rule. Left as a follow-up.

### The faces, before and after

`docs/playtest/scripts/character_wetness.json`: the five conversations and Dace, rig on, first
with the skin as it was (the AutoTest step `skin_before_wetness` sets the dry add to 0, which
is the roughness mask everywhere), then as built. 1280 x 720, seed 7, 30 fps fixed.
`tools/measure/face_luma.py` now also reports the highlight, the mean of the face box's
brightest tenth.

| Speaker | Wetness | Mean before / after | Highlight before / after | Lit/shadow before / after |
|---|---|---|---|---|
| Tank, the Anchor's bar | 0 | 59 / 53 | **148 / 101** | 1.51 / 1.23 |
| Silk, the Anchor's back room | 0 | 112 / 111 | 185 / 177 | 1.51 / 1.50 |
| Petra, the depot | 0 | 152 / 151 | 214 / 210 | 1.13 / 1.12 |
| Nguyen, under the Skyway | 0 | 180 / 180 | 233 / 233 | 1.15 / 1.15 |
| Lin, the shrine | 0 | 189 / 189 | 231 / 230 | 1.04 / 1.05 |
| Dace, the checkpoint gate, in the rain | 1 | 60 / 60 | 140 / 139 | 2.69 / 2.76 |

Stills: `docs/screenshots/character_lighting/wetness_<speaker>_before.png` and `_after.png`, and
`wetness_faces_before_after.png`, the heads side by side. The rig-off and round-1 rig-on shots
of the first captures are `rig_<speaker>_off.png` and `_on.png`.

What it shows:
- **Tank's shine is gone.** His highlight falls by a third with the key unchanged; the glint on
  his forehead in the before shot is a soft sheen after.
- **Faces lit near white barely move.** Nguyen's and Lin's brightest tenth sits near 230 under
  the stall's and the shrine's lights, where diffuse light, not the specular, sets it.
- **The rain case doesn't change.** Dace's face measures within a luma of before.

### What these checks establish, and what they don't

- They establish that the core decides who is under a roof from the plan's shapes, that every
  NPC's body carries the core's value to both shaders, and that a speaker indoors now reads
  matte while one in the rain reads as before.
- They don't show the cloth change against the old look: the before pass resets only the skin,
  so Dace's cloth is wet (darker, smoother) in both of Dace's shots, and the dry speakers' cloth
  is as it was in both.
- They don't show drying on screen. The drying rate is pinned by the core tests and the
  lighting test, not a capture.
- Frame cost is still unmeasured: the skin shader draws what the StandardMaterial3D drew, plus
  one mix.


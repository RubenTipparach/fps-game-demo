# Tasks

## 1. The instrument first

- [x] 1.1 The AutoTest `face_box` step and `tools/measure/face_luma.py`; re-measure the four
  baseline faces with projected boxes (they should agree with the hand-placed numbers within a
  few luma). Built and corrected on the first captures (design section 8). The projected boxes
  on the rig-off shots read Tank 21, Silk 54 and Petra 100 against the hand-placed 23, 60 and
  112; those shots already carry the new skin, so the comparison isn't like for like.
- [x] 1.2 The capture script: five conversations, rig on and off.

## 2. Skin

- [x] 2.1 `build_npcs.py`: the derived skin normal and the roughness in its alpha; the budget
  raised to 5 textures; `npc_skin_roughness.png` authored in MakeHuman UV; `--verify` passes.
- [x] 2.2 The import step and the `character_skin.tres` and `character_eye.tres` templates (the eye's
  numbers built into `character_outfit.tres`: design section 8).
- [x] 2.3 Dry indoors, wet in the rain (owner J1, design section 9):
  - the plan registers its roofs (`Plan.shelter`) and the export writes them; the core's
    `ShelterDef.Covers`, `Wetness.Sheltered` and the wetness step, with tests on the hub's real
    data (Tank at the bar dry, Dace at the checkpoint gate wet, a civilian under the Skyway dry,
    under a shop awning dry, on the Anchor's roof wet);
  - `character_skin.gdshader` with the skin's numbers and `wetness`; the import step writes it;
    the outfit shader's `wetness`; the globals declared in `project.godot` and set from data;
  - `wetness` in `character_lighting.json` and its validation;
  - `NpcActor` drives it through `BodyWetness`; `lighting_test.tscn` checks Tank at 0, Dace at
    1, the instance uniform on their meshes, the skin shader, and the drying rate.

## 3. Light

- [x] 3.1 `data/character_lighting.json`, its loader and validation.
- [x] 3.2 Characters on visual layer 2; the wrist light on the player scene.
- [x] 3.3 `conversation_rig.tscn`, placed and ramped by the dialog screen; the motivated key
  side; district gels.
- [x] 3.4 The energies: the owner accepted tuning round 1 as it looks ("tank looks fine with
  lighting", J1). The face band and the ratio are recorded per speaker, not gated.
- [x] 3.5 The framing, as approved in mockup D9 (owner I11): `framing` in the data, and the
  lighting test's "the view narrows to the framing's width".

## 4. Records

- [x] 4.1 Before and after stills of the five conversations with their measured numbers, the
  highlight (brightest tenth) among them; a validation record; the design page; archive.
  `docs/screenshots/character_lighting/`, `docs/validation/2026-09-29-character-lighting.md`:
  Tank's highlight 148 to 101, Dace in the rain 140 to 139.

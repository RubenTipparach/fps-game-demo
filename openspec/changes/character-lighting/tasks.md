# Tasks

## 1. The instrument first

- [ ] 1.1 The AutoTest `face_box` step and `tools/measure/face_luma.py`; re-measure the four
  baseline faces with projected boxes (they should agree with the hand-placed numbers within a
  few luma).
- [x] 1.2 The capture script: five conversations, rig on and off.

## 2. Skin

- [x] 2.1 `build_npcs.py`: the derived skin normal and the roughness in its alpha; the budget
  raised to 5 textures; `npc_skin_roughness.png` authored in MakeHuman UV; `--verify` passes.
- [x] 2.2 The import step and the `character_skin.tres` and `character_eye.tres` templates (the eye's
  numbers built into `character_outfit.tres`: design section 8).
- [ ] 2.3 Dry indoors, wet in the rain (owner J1, design section 9):
  - the plan exports the shelter shapes; the core's `Shelter.Covers` and the wetness step, with
    tests on the hub's real data (Tank at the bar dry, Silk on Lantern Row wet, a civilian
    under an awning dry);
  - `character_skin.gdshader` with the skin's numbers and `wetness`; the import step writes it;
    the outfit shader's `wetness`;
  - `wetness` in `character_lighting.json` and its validation;
  - `NpcActor` drives it; `lighting_test.tscn` checks an NPC indoors at 0 and one in the rain
    at 1, and the instance uniform on its meshes.

## 3. Light

- [x] 3.1 `data/character_lighting.json`, its loader and validation.
- [x] 3.2 Characters on visual layer 2; the wrist light on the player scene.
- [x] 3.3 `conversation_rig.tscn`, placed and ramped by the dialog screen; the motivated key
  side; district gels.
- [x] 3.4 The energies: the owner accepted tuning round 1 as it looks ("tank looks fine with
  lighting", J1). The face band and the ratio are recorded per speaker, not gated.
- [ ] 3.5 The framing, as approved in mockup D9 (owner I11).

## 4. Records

- [ ] 4.1 Before and after stills of the five conversations with their measured numbers, the
  highlight (brightest tenth) among them; a validation record; the design page; archive.

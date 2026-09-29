# Tasks

## 1. Bodies and accessories

- [ ] 1.1 12 civilian rows and 3 MerSec rows in `npcs.json`; build and verify; a lineup capture.
  (Built: civ_g to civ_r, mersec_b and mersec_c, with the age-band pin; all 36 bodies verify byte
  for byte. The Godot import and the lineup are to come.)
- [ ] 1.2 `build_npc_props.py`: the accessories, tagged by bone, fitted and stress-posed, with
  their `.blend`.

## 2. Core

- [x] 2.1 `CrowdPicker` and `data/crowd.json` with validation.
- [x] 2.2 Tests: the lookalike rule over the hub's placements with seeds 1-100; determinism
  across a save and a load; roles by district.

## 3. Godot

- [ ] 3.1 `character_outfit.gdshader` (hue and saturation instance uniforms) set by the import
  step on outfit materials.
- [ ] 3.2 `NpcActor` applies body, palette, accessories, scale and idle; talking pairs face
  each other.
- [ ] 3.3 The placement test still passes with scaled bodies and accessories.

## 4. Captures

- [ ] 4.1 The lineup of 18 civilians and 3 troopers; a market crowd still; a validation record;
  the design page; archive.

# Tasks

## 1. Bodies and accessories

- [x] 1.1 12 civilian rows and 3 MerSec rows in `npcs.json`; build and verify; a lineup capture.
  (civ_g to civ_r, mersec_b and mersec_c, with the age-band pin; all 36 bodies verify byte for
  byte, import and have their scenes; the lineup is `crowd_lineup.tscn`.)
- [x] 1.2 The accessories, each hung from a mount and fitted in its pose, with their `.blend`:
  in the Undercity prop kit (`build_undercity_props.py`, `undercity_props.blend`), not a new
  `build_npc_props.py` (design section 5).

## 2. Core

- [x] 2.1 `CrowdPicker` and `data/crowd.json` with validation.
- [x] 2.2 Tests: the lookalike rule over the hub's placements with seeds 1-100; determinism
  across a save and a load; roles by district.

## 3. Godot

- [x] 3.1 `character_outfit.gdshader` (hue and saturation instance uniforms) on every body's
  generated outfit material (`gen_character_materials.py`), which the import step maps.
- [x] 3.2 `NpcActor` applies body, palette, accessories, scale and idle (by `CrowdDress`, which
  the lineup uses too); talking pairs face each other.
- [x] 3.3 The placement test still passes with scaled bodies and accessories: every accessory a
  civilian's role allows, in its pose, on every body of the pool at both ends of the height
  range (612 of 612).

## 4. Captures

- [x] 4.1 The lineup of 18 civilians and 3 troopers; a market crowd still; a validation record;
  the design page; archive. (`docs/screenshots/crowd_variety/`, with the talking pairs and an
  umbrella in the hub; `docs/validation/2026-09-29-crowd-variety.md`.)

# RPG core spike (parked, not built)

An early sketch of the Undercity character, inventory, equipment, dialog, disguise, lock and
world-item code, written before the project adopted the rules in `CLAUDE.md`. It is kept as
reference for the OpenSpec changes under `openspec/changes/` and is **not part of any build**.

- **It doesn't compile.** It references members that were never written (`Doorway.OpenById`,
  `Layers.Interact`, `Game.Instance.TravelTo`, `DialogScreen`, `TextScreen` and others).
- **It breaks rules adopted since.**
  - It reaches through `Game.Instance.State` instead of taking injected services (section
    5.3).
  - It hardcodes tuning inline, such as `1.2f * tier` hold times and the 60 % armour cap
    (section 5.5).
  - It builds nodes and fallback meshes in code (section 6.1).
  - It depends on Godot in rules that belong in `Undercity.Core` (section 5.2).
- **What carries forward is the rules, not the code.** The changes restate them as
  requirements. Implementation starts from those changes, in the core library, with tests.

`tools/build_items.py` wrote `data/items.json` (39 items). The item catalogue in
`openspec/changes/inventory-and-equipment` supersedes it.

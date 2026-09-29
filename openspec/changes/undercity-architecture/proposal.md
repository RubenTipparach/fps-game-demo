# Proposal: an engine-independent core, data-driven tuning and one level layout source

## Why

Undercity's rules (skill checks, disguise verdicts, lock resolution, item stacking, dialog
conditions) will be read by the interface, the AI, the save system and later a balance tool.
If they live inside Godot node scripts they get copied into each of those places, and the
copies disagree. The first spike (`docs/spikes/rpg-core/`) showed the failure early: every
rule reached through `Game.Instance.State`, tuning sat inline (`1.2f * tier`), and nothing
could be tested without starting the engine.

The owner asked for "best practices and organization". This change sets the structure every
other Undercity change builds on.

## What Changes

- **`Undercity.Core`**, a plain C# class library (net8.0) with no Godot reference, owns every
  gameplay rule. **`Undercity.Core.Tests`** (xUnit) tests it headless with `dotnet test`.
- **The Godot project references the core.** Thin adapters in `game/scripts/Undercity/` turn
  engine events into core calls and core results into nodes, sound and UI.
- **Composition root.** The `Game` autoload builds the core services once. Nodes that need them
  implement `IWired` and are wired by the level loader; no node looks up a static singleton.
- **Tuning is data.** Every tuning value lives in `game/data/*.json` with units in the key
  names, a JSON schema beside it, and a validation test.
- **Stable identity and determinism.** Persistent objects have stable IDs from their level and
  node path. Randomness comes from one seeded source.
- **One layout source per level.** `tools/levels/layouts/<id>.py` feeds the design map
  (`tools/levels/render_map.py`, already built) and the Blender level build.
- **Small scenes.** Undercity is built from a kit of small `.tscn` scenes (NPC, door,
  container, terminal, camera, turret, exit, pickup) and authored UI scenes.

## Capabilities

### New Capabilities
- `core-architecture`: where rules live, how they are wired, tested, tuned, saved and
  identified; the layout source for levels.

### Modified Capabilities
None.

## Impact

- New projects `core/Undercity.Core` and `core/Undercity.Core.Tests`, and a `ProjectReference`
  from `game/Brushfire.csproj`.
- New `game/data/` with schemas, and `game/scripts/Undercity/` adapters.
- Brushfire's reference maps are unaffected. Their code-built UI is a documented exception
  (CLAUDE.md section 13) and is not extended.
- Every other Undercity change depends on this one.

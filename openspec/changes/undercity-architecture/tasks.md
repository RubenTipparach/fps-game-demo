# Tasks

## 1. Projects

- [ ] 1.1 Create `core/Undercity.Core` (net8.0 classlib, nullable on, warnings as errors) and `core/Undercity.Core.Tests` (xUnit).
- [ ] 1.2 Add the `ProjectReference` from `game/Brushfire.csproj`; confirm `dotnet build` in `game/` and `dotnet test core` both pass.
- [ ] 1.3 Add `scripts/check.sh`: every check in CLAUDE.md section 9, in order, stopping at the first failure.
- [ ] 1.4 `.editorconfig` as the one style source; `Nullable`, `TreatWarningsAsErrors` and `EnforceCodeStyleInBuild` in both core projects; `dotnet format --verify-no-changes` in the check script.

## 2. Data

- [ ] 2.1 `Data/JsonData.cs`: one loader (snake_case, enums as strings, comments allowed) used by every table.
- [ ] 2.2 Schemas in `game/data/schema/` for every table in design section 3.
- [ ] 2.3 `DataValidationTests`: schema, cross-references, ranges, for every file; a misspelt key is rejected.

## 3. State, identity, saves

- [ ] 3.1 `GameState` as a plain serializable graph; per-level persistence sets.
- [ ] 3.2 `StableId` rules and a test that two loads of a level produce the same ids.
- [ ] 3.3 `SaveStore`: versioned JSON written by temp file and rename, autosave on level travel, quicksave; tests for the round trip and for repairing a damaged save.
- [ ] 3.4 `IRandomSource` seeded per purpose; a test that the same seed gives the same small talk.

## 4. Wiring

- [ ] 4.1 `Services` built by the `Game` autoload; `IWired` called by the level loader.
- [ ] 4.2 The scene kit (design section 6) with thin scripts.

## 5. Levels

- [ ] 5.1 `tools/levels/render_map.py` and layouts for hub, drains and yard (done: design maps).
- [ ] 5.2 `tools/blender/build_undercity.py` reading a layout.
- [ ] 5.3 `export_level_data.py` writing `data/levels/<id>.json`.

## 6. Prove it

- [ ] 6.1 `dotnet test core` green in a cloud session; output in the PR.
- [ ] 6.2 A capture of an empty test level built from a layout, with its entities labelled.

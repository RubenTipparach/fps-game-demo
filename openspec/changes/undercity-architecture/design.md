# Design: core architecture

## Context

Godot 4.7 .NET builds one C# assembly from `game/`. Brushfire's gameplay (player, weapons,
enemies) lives there as node scripts. That is acceptable for an arena shooter and wrong for
an immersive sim whose rules must agree across the interface, AI, saves and tests.

## Goals / Non-Goals

**Goals:**
- Every gameplay rule exists once, in code that runs without the engine.
- Tuning is diffable data with units, validated before it can ship.
- A save, a replay and a test reproduce the same outcomes.
- The design map and the built level come from one layout.

**Non-Goals:**
- Multiplayer or a server. Nothing here prevents one, but nothing builds one.
- Porting Brushfire's arena code into the core. It stays as the reference maps.
- A mod loader or runtime data editing.

## Decisions

### 1. Solution layout

```text
core/
  Undercity.Core/            net8.0 class library, no Godot reference
    Character/  Items/  Inventory/  Dialog/  Perception/  Disguise/
    Locks/  Quests/  Factions/  World/  Save/  Data/
  Undercity.Core.Tests/      xUnit, runs with `dotnet test core`
game/
  Brushfire.csproj           + <ProjectReference Include="../core/Undercity.Core/Undercity.Core.csproj"/>
  scripts/Undercity/         adapters (namespace Undercity.Game)
  scenes/undercity/          the scene kit and UI scenes
  data/                      tuning and content JSON, schemas in data/schema/
tools/levels/                layouts and the map renderer
```

*Alternative considered:* folders inside `game/` with a convention of "no Godot using".
Rejected because nothing would enforce it. A project without a Godot reference cannot call
Godot by accident, so the boundary is enforced by the compiler.

### 2. Wiring: constructor injection in the core, `IWired` at the edge

- **Core services take their dependencies as constructor parameters.**
- **The composition root.** The `Game` autoload builds a `Services` object once per session:
  `ItemDb`, `SkillRules`, `DisguiseRules`, `LockRules`, `DialogRunner`, `QuestLog`,
  `GameState`, `IRandomSource`, `IClock`.
- **Nodes are wired by the loader.** Godot constructs nodes itself, so they can't take
  constructor arguments. A node that needs services implements
  `IWired { void Wire(Services s); }`, and the level loader calls it once after the level
  enters the tree.
- **No static lookups.** A node never reaches for `Game.Instance` to find a collaborator.

*Alternative considered:* a static service locator. Rejected: it hides dependencies, and tests
can't swap a service without global state.

### 3. Data and units

| File | Holds |
|---|---|
| `data/skills.json` | Skills, rank costs, perks and their numeric effects |
| `data/progression.json` | XP curve, level cap, XP awards, health per level |
| `data/items.json` | The item catalogue (ids, footprints, stacks, values, effects) |
| `data/weapons.json` | Damage, rate, magazine, noise radius, spread |
| `data/perception.json` | Sight, hearing, detection rates, state timers, noise radii |
| `data/enemies.json` | Archetypes: health, armour, intelligence, senses, loadout |
| `data/factions.json` | Factions, stances, reputation thresholds |
| `data/locks.json` | Lock and hack timings, tool use, XP per tier |
| `data/quests.json` | Quests and objectives with XP and credits |
| `data/dialog/<tree>.json` | Dialog trees |
| `data/levels/<id>.json` | Exported from the layout: POIs, spawns, persistent ids |

- **Keys are snake_case and carry units:** `range_m`, `time_s`, `rate_per_s`, `pct`,
  `radius_m`, `credits`.
- **Every file has a JSON schema** in `data/schema/`. `DataValidationTests` loads every file
  and checks:
  - it matches its schema;
  - every cross-reference resolves (item ids, flags, quests, skills, dialog nodes);
  - every value is in range.
- **One source for each default.** Defaults are declared in the schema. The loader never
  invents one, and zero is a value, not "unset".
- **Unknown keys are errors.** The loader sets `JsonUnmappedMemberHandling.Disallow`, so a
  misspelt knob fails at startup with its file and key instead of silently doing nothing
  (the failure Pale-Blue-Dot's config loader was written to prevent).
- **A file that fails to parse or validate stops startup** with its path and field. It never
  falls back to defaults.

### 4. Identity, persistence, determinism

- **Stable ids.** A persistent object's id is `<level_id>:<node path>` (for example
  `drains:Camp/LootStash`). Layout-generated entities get ids from the layout's POI numbers.
  An id never comes from instance order.
- **One serializable state.** `GameState` is a plain serializable object: character,
  inventory, flags, quests, faction reputation, and per-level `taken`, `opened`, `dead`,
  `unconscious` and `door` sets.
- **Damaged saves are repaired, not trusted.** A save is player data, not authored data.
  Out-of-range values load as the nearest legal state (a stack clamped to its limit, an
  unknown item id dropped), each with a logged warning.
- **Saves.** They are JSON at `user://saves/<slot>.json` with `"version"`, written to a temp
  file and renamed, so a crash mid-write leaves the old save intact. The game saves
  automatically on every level transition and on quicksave. Loading an older version runs an
  explicit migration or refuses; it never guesses.
- **Seeded randomness.** `IRandomSource` is seeded by
  `hash(save_seed, level_id, stable_id, purpose)`. Civilian small talk, rumour choice and loot
  variation use it. Skill checks never do (they are deterministic by design).

### 5. Previews call the resolver

The interface asks the same core function that resolves the outcome:
- `LockRules.Best(lock, character, inventory)` gives both the prompt and the result;
- `DialogRunner.Choices(...)` gives the enabled and disabled choices and the requirement text;
- `DisguiseRules.Judge(...)` drives the meter and the AI;
- `Vendor.Price(...)` is the shown price and the charged price.

### 6. Scene kit

Small scenes under `game/scenes/undercity/kit/`:

- `npc.tscn`, `door.tscn` (with frame per CLAUDE.md 7.2), `loot_container.tscn`,
  `terminal.tscn`, `security_camera.tscn`, `turret.tscn`, `searchlight.tscn`,
  `level_exit.tscn`, `world_item.tscn`, `restricted_zone.tscn`, `noise_source.tscn`.
- Each has a thin script: exported ids only (`npc_id`, `loot_table`, `lock_id`), and behaviour
  from the core.
- UI scenes live under `game/scenes/undercity/ui/`. Each is built only after its mockup is
  approved (CLAUDE.md section 8).

### 7. Layout to level

`tools/levels/layouts/<id>.py` is the plan. The pipeline:

1. `render_map.py` draws it (done).
2. `tools/blender/build_undercity.py <id>` builds the level from it: blocks, rooms, props and
   `ENT_` empties for every POI, NPC, container, exit and patrol point.
3. The import script writes the level `.tscn`.
4. `export_level_data.py` writes `data/levels/<id>.json`.

A POI's number is its entity id, so the map legend and the level's objects share names.

## Risks / Trade-offs

- **Two projects slow the first build.** `dotnet build` restores the core too. This is
  acceptable; it is seconds.
- **Adapter boilerplate.** Each core concept needs a thin node. The kit keeps that to about a
  dozen scenes.
- **Godot's C# hot reload** sometimes misses changes in referenced projects. If so, restart
  the editor after a core change. The README will say this.

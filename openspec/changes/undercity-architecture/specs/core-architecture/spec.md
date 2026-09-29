# Core Architecture

## Purpose

Where Undercity's gameplay rules live and how they are wired, tuned, identified, saved and
tested, so that each rule exists once and the interface, AI and saves agree.

## ADDED Requirements

### Requirement: Gameplay rules are engine-independent
Every gameplay rule SHALL be implemented in `Undercity.Core`, a C# library with no reference to
Godot, and SHALL be testable with `dotnet test` without starting the engine. This covers skills,
XP, items, inventory, equipment, dialog, disguise, perception, locks, quests, factions and save
state.

#### Scenario: Building the core alone
- **WHEN** `dotnet test core` runs on a machine without Godot
- **THEN** every core test builds and runs

#### Scenario: A rule needed by two callers
- **WHEN** the inventory screen and the pickup prompt both need to know whether an item fits
- **THEN** both call the same core method

### Requirement: Previews come from the resolving code
Any value the interface shows before an action SHALL be computed by the same function that
resolves the action. This covers a price, a lock prompt, a dialog requirement, a disguise
verdict and a hold time.

#### Scenario: A lock prompt
- **WHEN** the prompt reads "Pick lock, tier 2 (hold 2.0 s)"
- **THEN** holding use for 2.0 s opens it, consumes one lockpick, and awards the XP the same
  rule computes

### Requirement: Tuning lives in validated data with units
Tuning values SHALL be read from `game/data/*.json`, with units in the key names, and SHALL
NOT be written as literals in gameplay code. Every data file SHALL match a JSON schema, and its
cross-references SHALL resolve, as checked by a core test.

#### Scenario: A dangling reference
- **WHEN** a dialog tree gives an item id that `items.json` does not define
- **THEN** `DataValidationTests` fails and names the file, the node and the id

#### Scenario: A misspelt key
- **WHEN** `perception.json` contains `"rang_m"` instead of `"range_m"`
- **THEN** the game refuses to start and names the file and the key

#### Scenario: Zero is a value
- **WHEN** an item's `noise_radius_m` is 0
- **THEN** the item makes no noise, and no default replaces the 0

### Requirement: Nodes are wired, not self-locating
A node that needs a core service SHALL receive it through `IWired.Wire` from the level
loader. Node scripts SHALL NOT fetch collaborators through a static singleton.

#### Scenario: Swapping a service in a test scene
- **WHEN** a test scene wires a node with a fake `ItemDb`
- **THEN** the node uses the fake, with no global state changed

### Requirement: Persistent objects have stable ids
Every object whose state persists SHALL have an id derived from its level id and its node
path or layout POI number, never from instance order.

#### Scenario: Reloading a level
- **WHEN** the player loots a locker, leaves the level and returns
- **THEN** the locker has the same id and stays empty

### Requirement: Randomness is seeded and skill checks are not random
Every random choice SHALL come from `IRandomSource`, seeded by the save seed, the level id, the
object's stable id and the purpose. Skill checks SHALL be deterministic comparisons and SHALL
NOT draw random numbers.

#### Scenario: Replaying a save
- **WHEN** a save is loaded twice and the same civilian is spoken to
- **THEN** they say the same line both times

### Requirement: Saves are versioned
A save SHALL be JSON with a `version` field. Loading a save from an older version SHALL run an
explicit migration or refuse with a message. Loading SHALL NOT silently default missing
fields.

#### Scenario: A damaged save
- **WHEN** a save holds a stack of 90 medkits (stack limit 5)
- **THEN** it loads as a stack of 5 and the repair is logged

#### Scenario: A save from before a new field
- **WHEN** a version 1 save is loaded by a version 2 build that added faction reputation
- **THEN** the v1 to v2 migration sets reputation to each faction's declared starting value

### Requirement: A level's plan has one source
Each Undercity level SHALL have one layout module under `tools/levels/layouts/`. The design map
and the Blender level build SHALL both be generated from it. Each point of interest's number
SHALL be the id of the entity it places.

#### Scenario: Moving a locker
- **WHEN** a designer moves loot POI 15 in `drains.py`
- **THEN** the regenerated map and the rebuilt level both show it at the new position

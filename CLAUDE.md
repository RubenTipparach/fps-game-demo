# Undercity (Brushfire tech): rules for Claude

Undercity is a first-person immersive sim in Godot 4.7 .NET (C#). It is set in the flooded, neon-lit
underbelly of the megacity Meridian, and it has skills, XP, a grid inventory, equipment,
dialog trees, disguises and enemies you outsmart. It is built on the tech of **Brushfire**, an
old-school Quake 2 / Unreal 1 (UT99) style FPS. Brushfire's three arena levels stay in the
project as **reference maps**, one per tool: Godot CSG, TrenchBroom via func_godot, and Blender
boolean cutters.

These rules are binding. When a rule here conflicts with a general habit, a design doc or a
tool's default, this file wins.

**This file is the only copy of these rules.** `AGENTS.md` is a pointer to it and must stay
one. Write a rule here, never there. Two files that have to agree are two files that won't,
and the one that is wrong is always the one nobody is reading. `openspec/config.yaml` points
here for the same reason.

Contents:

1. Owner direction (standing instructions)
2. Spec-driven work: OpenSpec
3. Write it up before touching code
4. Writing style
5. Architecture and code quality
6. Godot rules
7. Level design rules
8. UI work
9. Verification
10. Working with the owner
11. Build workflow
12. Design references
13. Documented exceptions

---

## 1. Owner direction (standing instructions)

- **Undercity is the game (owner, 2026-09-27).** It is an immersive sim with:
  - skill trees, XP and levelling;
  - inventory and equipment;
  - dialog trees with NPCs;
  - varied enemies you outsmart with technical combat.
- **Hub and missions.** The hub is the seedy underbelly of a cyberpunk city. Missions
  infiltrate sewers, gang warehouses and junkyards, and later towers, malls and parks for
  assassinations, robberies and hostage situations.
- **Talk to anyone.** Every NPC in the hub can be talked to. A good disguise lets you talk to
  hostiles too, but fooling smarter enemies takes a higher skill.
- **Blender is the level pipeline.** It is "definitely" the winner. TrenchBroom "has some cool
  stuff" worth borrowing, and Godot CSG is "the weakest by far". New levels are built in
  Blender. The three Brushfire levels are kept, as reference only.
- **Fidelity (owner, 2026-09-27).** Level maps are drawn to the standard of Deus Ex hub maps,
  such as Mankind Divided's Prague map:
  - dense, organic building footprints;
  - named districts and buildings;
  - numbered points of interest, mission markers and a legend.

  Systems documents are deep: formulas, tuning tables, data schemas, UI mockups and
  walkthroughs. A sketch is not a design.
- **Use OpenSpec and these best practices (owner, 2026-09-27).** "I want this code to use best
  practices and organization." The rules below were adapted from the owner's other two
  projects, the-federation and Pale-Blue-Dot.
- **Pale-Blue-Dot's coding practices (owner, 2026-09-27).** "Add best coding practices from
  pale blue dot": they are sections 5.6 and 9 below.
- **Artifacts and surveys (owner, 2026-09-27).** "Always show new or updated artifacts at the end
  of each run", and "always ask questions inside of survey artifacts": see section 10.

## 2. Spec-driven work: OpenSpec

Requirements and in-flight design live in `openspec/`, driven by the OpenSpec CLI
(`npm install -g @fission-ai/openspec`, Node 20.19+; https://openspec.dev). The split is the
point:

- **`openspec/specs/<capability>/spec.md` is what the game DOES.** Every requirement in it is
  true today and pinned by a passing check: a unit test, a generator assertion, or an AutoTest
  capture. A requirement for behaviour the game doesn't have yet does not belong here, however
  certain the plan is.
- **`openspec/changes/<name>/` is what is designed but not built.** It holds:
  - `proposal.md`: why, and what changes;
  - `design.md`: how, with the numbers;
  - `tasks.md`: the checklist;
  - spec deltas under `specs/<capability>/spec.md`, using `## ADDED / MODIFIED / REMOVED
    Requirements`, with `### Requirement:` headings, SHALL statements and `#### Scenario:`
    WHEN/THEN blocks.
- **`openspec/changes/archive/`** takes a change once its deltas are merged into the main
  specs and its work is real.

The workflow:

| Command | Does |
|---|---|
| `/opsx:explore` | Think the problem through |
| `/opsx:propose` | Write the planning artifacts, then stop |
| `/opsx:apply` | Implement (a separate request) |
| `/opsx:archive` | Close the change when it lands |

- **Keep changes small and single-purpose.** Write one change per capability or per level,
  never an umbrella that holds everything.
- **Validate before every push.** `openspec validate --all` must pass.
- **Specs move with the code.** Move a requirement from a change into `openspec/specs/` in the
  same commit that makes it true and adds the check that proves it, never ahead of it.
- **The design page presents the changes; it is not a second source.**
  `docs/design/undercity_systems.html` shows the changes (maps, mockups, calculators), and each
  of its sections names the change it presents. When a change moves, update the page in the
  same commit.

## 3. Write it up before touching code

**Standing instruction.** The write-up comes first:

1. Investigate and measure.
2. Put the finding and the plan in `openspec/`: a proposal, a design and the spec deltas.
3. Stop there.

Editing source is a separate step, taken after the write-up exists and on a request to take
it. A change argued in a document can be read, disagreed with and redirected for the cost of
reading it. The same change argued in a diff has already been made.

**One exception: a measurement instrument**, meaning code whose only job is to produce a number
the write-up needs.
- Say in the write-up what is measured and why before writing it.
- Keep it to the instrument. Never let "I needed to measure" carry a behaviour change in with it.

Do not rename or rescale a tuning value, alter a default, or refactor toward a plan before the
plan is written down.

## 4. Writing style

**Never use em dashes (U+2014) or en dashes (U+2013), anywhere.** This covers docs, code
comments, commit messages, PR bodies, in-game text, UI strings, logs and chat replies. Use
these instead:

| Instead of a dash | Use |
|---|---|
| Introducing a definition or explanation | A colon |
| A parenthetical aside | Commas or parentheses |
| A hard break between two clauses | A period, and two sentences |
| A range of numbers | A plain hyphen: `10-25 m` |

The characters are named by codepoint here so the rule stays checkable. The repository holds
none of them outside tool-owned files (section 13):

```sh
LC_ALL=C.UTF-8 grep -rnIP '\x{2014}|\x{2013}' --exclude-dir=.git --exclude-dir=.godot \
  --exclude-dir=.claude . && echo FAIL
```

## 5. Architecture and code quality

### 5.1 One implementation of every rule

**Avoid divergent code paths that share functionality at all costs.** This is the
highest-priority engineering rule.

- **Same behaviour, same code.** If two places need the same behaviour, they call the same
  code: no copies, no near copies, no "this one is slightly different so I forked it".
- **Parameterize, don't clone.** A second caller that needs a variation parameterizes or
  extends the shared implementation.
- **Search first.** Before writing anything new, look for an existing implementation and extend
  it.
- **Report duplication.** If you find duplication while working, say so. Never add a third copy.

Concretely, each of these exists once:
- the skill-check rule;
- the disguise verdict;
- lock resolution (key, code, pick, hack);
- item stacking and placement;
- damage and armour;
- the XP curve.

What the interface previews is computed by the code that resolves it:
- the greyed-out dialog choice;
- the lock prompt;
- the disguise meter;
- a vendor's price.

A preview that disagrees with the outcome is the bug this rule prevents.

### 5.2 An engine-independent core

Gameplay rules live in **`Undercity.Core`**, a plain C# class library with no Godot reference.
Its tests are **`Undercity.Core.Tests`** (xUnit), which run headless with `dotnet test`.

- **Scope.** The core owns skills, XP, items, inventory, equipment, dialog evaluation,
  disguise and perception rules, locks, quests, factions and save state.
- **The Godot layer adapts it.** Node scripts turn engine events into core calls, and core
  results into nodes, sounds and UI. That direction never reverses: the core never calls into
  Godot.
- **Anything a future save, replay or balance tool must agree on lives in the core.**

The core does not exist yet. It is created by `openspec/changes/undercity-architecture`, and
this is the rule for all new gameplay code from then on.

### 5.3 SOLID, with injected dependencies

- **Single responsibility.** One class, one reason to change. Split anything that has grown a
  second job.
- **Open/closed.** Extend by adding types or data, not by growing a `switch` in the middle of
  existing logic.
- **Liskov substitution.** A subtype works anywhere its base type does, with no special casing
  at the call site.
- **Interface segregation.** Keep interfaces small; callers never depend on methods they don't
  use.
- **Dependency inversion.** Depend on interfaces. Inject dependencies through constructors.
  - A composition root (the `Game` autoload) wires the core services once.
  - New code does not reach through static singletons such as `Game.Instance.State` to find
    its collaborators.

### 5.4 Determinism and stable order

- **Checks are deterministic.** Skill checks compare numbers; they never roll.
- **Randomness is seeded and explicit.** Anything random (civilian small talk, loot variation)
  takes an explicit seed, so a save and a replay reproduce it.
- **Order is stable.** A dictionary used for keyed lookup is fine, but never let hash order
  choose an outcome, an ID or a save layout.

### 5.5 Tuning lives in data

- **No inline tuning.** Never hardcode a tuning value in gameplay code.
- **Data files carry units and are validated.** Tuning lives in committed, diffable data files
  under `game/data/` (JSON, snake_case keys) with units in the key or the schema (`range_m`,
  `time_s`). They are validated on load and by a core test.
- **One source for each default.** An optional override is explicit. Zero is a valid value,
  not a "use the default" sentinel.
- **Where settings live, in order of preference:**
  1. a config file;
  2. a Godot resource, where the engine requires one;
  3. a node's inspector field, only as a last resort.

### 5.6 Code conventions (from Pale-Blue-Dot)

- **Document the contract.**
  - Every file opens with a summary comment: what it owns, and why it lives where it
    lives. Example: "It lives in the core because how a stack merges is a rule a save has to
    agree about."
  - Every public type and member has an XML doc comment.
  - Units go in the name or the doc. Distances are metres, times seconds, angles radians in
    code; data files name their unit in the key (`range_m`, `angle_deg`).
- **Tests sit with the rule and read as sentences.**
  - Core tests live in `Undercity.Core.Tests`, mirroring the core's folders.
  - A test's name states the behaviour (`A_full_pack_leaves_the_jacket_in_the_locker`), one
    behaviour per test.
  - An assertion that isn't obvious carries a message saying why it matters.
- **A bug fix brings its regression test.** Commit the test that failed before the fix with
  the fix, and name the boundary it pins.
- **Defaults live in code, once.**
  - A shipped data file repeats them so a designer can turn a knob without a compiler.
  - A missing field inherits the code default. A present zero is zero.
  - An unknown key is an error, because a misspelt knob that silently does nothing is the
    worst kind of bug. Use `JsonUnmappedMemberHandling.Disallow`.
  - A data file that exists but fails to parse or validate stops the game at startup with its
    path and field. It never falls back to defaults silently.
- **Authored data fails loudly; player data is repaired.** A damaged save loads as the nearest
  legal state, such as a stack clamped to its limit, with a logged warning. It never loads as
  an illegal one.
- **Warnings are errors, and style is checked.**
  - New projects set `Nullable`, `TreatWarningsAsErrors` and `EnforceCodeStyleInBuild`.
  - `.editorconfig` is the one style source, checked by `dotnet format --verify-no-changes`.
- **Guard the edges.**
  - Check indices before use (grid cells, belt slots, dialog choices).
  - Reject non-finite numbers where they enter: data loads, physics results, saves.
  - A capacity limit is handled whole, never by writing half an operation. An add that doesn't
    fit reports what's left and changes nothing it can't finish.
- **Validate the real artifact.** When two things must agree (C# data classes and the JSON
  files, a scene and the core ids it names, a shader and its uniforms), a check loads the
  actual files and compares them. It never compares two hand-written copies of an expected
  value.
- **Borrowed code keeps its provenance.** Code or assets copied from another repository (the
  owner's other projects, a reference snapshot) record their source and revision beside them.
  A reference checkout is never part of a build.

## 6. Godot rules

### 6.1 No procedural scenes or meshes

- **Scenes are authored `.tscn` files, committed.** Don't build node trees in code as the
  normal way of making things. Instantiate and configure prebuilt scenes.
- **Meshes are files.** Models are `.glb` (or `.gltf` / `.obj` for simple static geometry),
  built by a committed Blender script whose editable `.blend` source is committed too. The
  Godot import is a build product, not the source.
- **Generators write files.** A Python generator that writes a `.tscn` or `.glb` into the repo
  is authoring, and it is fine: the committed file is what the game loads.
- **Exceptions are agreed first.** Anything that can't be statically authored is raised before
  it is built, agreed, and listed in section 13.

### 6.2 Scenes are structure, code is behaviour

- **A `.tscn` defines what exists and how it is arranged,** not what it does. No rules are
  encoded in inspector values beyond what data a node carries (an NPC's id, a container's
  loot table id).
- **Node scripts are thin.** They wire the node to a core system and nothing more.
- **The simulation runs without a scene.** It can be run and tested headless.

### 6.3 Small scenes that compose

- **Single-purpose scenes** (an NPC, a door, a loot locker, a terminal) are composed into
  levels.
- **Each scene works on its own** and is testable in isolation.
- **Prefer composition** to deep chains of inherited scenes.

### 6.4 Art

- **Textures and materials** come from Material Maker, at the texel density in
  `materials/materials.json`. Finished art is committed as `.png`.
- **Name colour roles, not hex values.** UI colours come from the theme's named roles
  (`accent`, `text_dim`, `danger`). Only the theme says what those are.

## 7. Level design rules

### 7.1 Pipeline and layout

- **New levels are Blender builds** (`tools/blender/build_*.py` produces a `.glb` with `ENT_`
  empties, and the import script produces `.tscn`). TrenchBroom ideas worth keeping, such as
  brush-style detailing and entity placement, are ported into that pipeline.
- **One layout source.** A level's layout (blocks, buildings, streets, rooms, POIs, patrols,
  mission markers) lives in one data module under `tools/levels/layouts/`. Both
  `tools/levels/render_map.py` (the design map) and the Blender build read it, so the map and
  the level cannot disagree.
- **Three ways in.** Every key room and objective can be reached by force, by stealth and by
  social means (talk, lie, bribe, disguise), and usually by tech (hack, lockpick) as well.

### 7.2 No z-fighting, ever

Two surfaces must never share a plane while overlapping and facing the same way. In practice:

- **Frame props need an inset clear opening.** A frame prop (door frame, archway) is placed in
  a level opening of its `fits` size and has a smaller `clear` opening (`detailing.FRAMES`,
  `REVEAL` = 0.1 m), so its reveals stand proud of the walls and ceiling.
  - Never size a prop to exactly match the opening it sits in. That is the classic bug: jambs
    flush with corridor walls and the lintel flush with the ceiling.
  - Carve door openings at the frame's `fits` size (doors 3.2 x 3.3 m).
- **Detail brushes and trims must not share planes with each other, or with floors, walls and
  ceilings, where they overlap.**
  - Inside corners are owned by the x-running walls; trims on z-running walls stop at their
    faces.
  - A girder is never as deep as the cornice or capital it meets, and never as wide as the
    pilaster it bears on.
  - Plinth heights differ from baseboard heights (0.30, 0.35 and 0.45 m are taken).
  - A bridge deck spans exactly its channel instead of lapping onto the floor at floor
    height.
  - No zero-height blocks: the last stair tread is the floor itself.
- **Faces pressed back to back are fine,** for example a trim's back against a wall or a
  beam's top against the ceiling. Keep deliberately parallel surfaces at least 1 cm apart: the
  checker treats anything within 5 mm as coplanar.
- **Every generator runs `detailing.assert_no_zfighting(...)`** and refuses to write a level
  that fails it. When you add geometry:
  - Register boxes with the check: `details` in `gen_map.py`, `L.block` in
    `build_cistern.py`, and trims plus `FRAME_PROPS` in `gen_level_csg.py`.
  - When you change a frame prop in `tools/blender/build_props.py`, change `detailing.FRAMES`
    and `frame_solids()` to match. Prop boxes are checked against each other too.
- **Godot CSG unions resolve overlaps between brushes,** so in the CSG level only separately
  rendered meshes (props, fixtures) can z-fight. TrenchBroom brushes and Blender detail blocks
  stay separate surfaces, so everything there is checked.
- **Check visually as well.** The checker only knows axis-aligned boxes. Cylinders, wedges and
  arch rings are not covered, so look at new geometry up close, unshaded: AutoTest
  `{"debug_draw": 1}`.

### 7.3 Style (see `docs/ut99_reference.md`)

- **Trims, pilasters and girders** come from `tools/godot/detailing.py`.
  - Rooms are axis-aligned air boxes.
  - Pass light fixtures as `keep_out` boxes so trims avoid them.
  - Put ceiling lights in the bays between girders.
- **Pillars** always have a base and a capital.
- **Every light has a visible fixture** with a corona.
- **Lighting.** Use warm fixtures, a cool blue fill and one accent colour (neon for Undercity).
  `add_zone_ambient` keeps shadows dark blue, not black.
- **Sky openings** use `sky_*` materials (`shaders/sky_surface.gdshader`). Aim the baked
  spotlight from the sky's `moon_direction`.

### 7.4 People stand clear of the level

The owner, 2026-09-28: "npcs should have colliders on them, like capsule colliders for checking
where they are in the city, and so you should perform tests on that to ensure people are placed
properly." (`openspec/specs/level-geometry`, "People stand clear of the level".)

- **Every placement is tested with the body's own collider:** the NPC scene's capsule for NPCs,
  civilians and patrol stops, the player scene's cylinder at spawns. Never a hand-typed size.
- **The plan checks it first.** `city_plan.py` refuses a layout whose people overlap a detail,
  a stall part, a pillar, a fixture or prop footprint, a wall or a building, stand on a curb
  edge, or walk a patrol leg through any of those. A solid that isn't an axis-aligned box
  registers its footprint with `Plan.solid(...)` where it is built.
- **The built level is checked with real physics.** `scenes/undercity/tests/placement_test.tscn`
  loads the sector glbs and tests every placement against the colliders. Run it after every
  level rebuild; `scripts/check.sh` does.
- **Every room is carved.** `city_plan.py` refuses a plan in which a room or a door has no cutter.

## 8. UI work

- **Mockup first.** Get the owner's approval of a mockup before implementing any new screen,
  panel or layout. HTML mockups go in the design page. Approval isn't needed for bug fixes,
  small changes to an approved UI, or text and spacing fixes within an approved design.
- **UI is authored scenes.** Screens are `.tscn` files styled by one `Theme` resource, and the
  theme owns every font size. New UI does not assemble controls in code (the existing code-built
  menus are listed in section 13).
- **Panels are a fixed size, and content never changes it.**
  - Pin each panel with `custom_minimum_size` equal to `custom_maximum_size`, plus
    `propagate_maximum_size` and `clip_contents`.
  - Runtime text uses `clip_text` and TRIM_ELLIPSIS.
  - Unbounded content (the inventory list, the quest log, a vendor's stock) scrolls inside an
    authored `ScrollContainer`; it never pushes.
  - A test writes an overlong string into every label and asserts every panel keeps its size
    after two frames.
- **Menus name things, they don't explain them.**
  - A row is a label and a control.
  - No keyboard hints and no "click here to".
  - Reasons belong in `docs/` and code comments.
  - An empty state gets one short line ("No items.").
  - The test: would this line still be worth reading the tenth time the screen is opened?
- **In-world text is diegetic where it can be:** terminals, signs and emails. The HUD stays
  minimal.

## 9. Verification

Before claiming anything is done, run what applies:

| Check | Command |
|---|---|
| Format | `dotnet format --verify-no-changes` (the core and new projects) |
| Build | `dotnet build` in `game/`, warnings as errors in the core |
| Core tests | `dotnet test core` |
| Specs | `openspec validate --all` |
| Dash check | Section 4 |
| Z-fighting | Every level generator asserts it |
| People placement | `city_plan.py` asserts it; `placement_test.tscn` in the built level (7.4) |
| Design maps and page | `python3 tools/levels/render_map.py && python3 tools/design/build_page.py` |
| Scripted playtests and screenshots | `BRUSHFIRE_AUTOTEST=script.json` |

- **One script runs every check.** `scripts/check.sh` runs the table above in order and stops at
  the first failure (Pale-Blue-Dot's `check_all`). Run it before every push. It's created by
  `undercity-architecture` task 1.3; until then, run the rows by hand.

- **Know what is proven.** Distinguish implemented, validated and proposed work in docs, PRs
  and replies. A design is not a feature, and a green test is not a visual sign-off.
- **Every major step ends in a capture the owner can check,** before the next step starts:
  - A video (a capture sequence encoded with ffmpeg) where motion is the point: AI, combat,
    doors, dialog flow.
  - Stills otherwise.

  Each shot names what it shows and which requirement it demonstrates.
- **Validation records say what was and wasn't proven.** A step's record
  (`docs/validation/<date>-<topic>.md`) states:
  - the environment: machine, GPU or lavapipe, Godot, .NET and the seed;
  - each check and its result;
  - what the checks establish, and what they don't.

  Passing checks establish the listed contracts, not a blanket acceptance.
- **Measure performance the repeatable way.**
  - Measure an exported release build, in real time, with nothing else running. Capture
    mode steps time and is for pictures only.
  - Compare the old build against the new, interleaved in the same sitting, never against a
    number from another day.
  - Report the machine, resolution, build, repeats, percentiles with warm-up excluded, and
    the spread between repeats. A difference smaller than that spread is not a result.
  - Never call an unmeasured design a speedup.
- **Cloud sessions.** A Claude Code cloud session renders on lavapipe without a GPU, so it
  doesn't measure frame time; say so in the PR. It does render the change: captures go in
  `docs/screenshots/` with the change.

## 10. Working with the owner

- **Show the new and updated artifacts at the end of every run (owner, 2026-09-27).** "Always
  show new or updated artifacts at the end of each run."
  - Every reply ends with a short list of links: each claude.ai artifact published,
    republished or edited since the owner's last message, with one line on what is new. That
    covers pages, maps, mockups, reports, the survey and any other Claude Doc.
  - A newly made artifact is also opened for the owner (the Artifact tool's `open`).
  - If nothing was published or edited, say so in one line, so a missing list is never
    mistaken for a forgotten one.
- **Ask the owner with a survey, never in chat (owner, 2026-09-27).** "Always ask questions
  inside of survey artifacts."
  - Every question for the owner goes into the survey Claude Doc, with its options, a
    recommendation and an answer column. That includes a single yes-or-no.
  - The reply gives the survey's link and the ids of the new questions, not the questions
    themselves.
  - The `owner-survey` skill (`.claude/skills/owner-survey`) says how.
  - The current survey is https://claude.ai/artifact/Bp34gDXJnZW3EP1uHVLM6J. Keep editing it
    rather than starting another.
  - Answers are folded back into the OpenSpec changes they shape, and the row moves to the
    survey's "Already decided".
  - If a session has no Claude Docs connector, say so, and publish the same tables as an
    artifact page with an answer field per question.
- **No self-scheduled check-ins.** Don't schedule recurring check-ins, polling loops or
  re-arming reminders unless the owner asks for them. Reacting to events that arrive on their
  own (PR webhooks, task notifications) is fine; a self-scheduled timer is off by default.

## 11. Build workflow

- **Regenerate, don't hand-edit.** These files are generated: `level_csg.tscn`,
  `slag_works.map`, `level_trenchbroom.tscn`, `cistern.glb`, `level_blender.tscn`,
  `scenes/**`, the design maps under `docs/design/maps/`, and the NPC pipeline's output
  (`models/characters/*.glb`, `animations/undercity_clips.glb`, `animations/bonemaps/*.tres`;
  README, "Undercity's NPC bodies").
- **Rebuild and bake** with the `BRUSHFIRE_BATCH=... godot --editor --path game` command in
  README.md.
  - It needs Xvfb (`DISPLAY=:99`) and Vulkan (lavapipe), and takes about 15 minutes per level.
  - Don't regenerate level files or run `dotnet build` while a bake is running: the editor
    reloads them mid-bake.
  - Commit the `.lmbake`, `.exr` and scene files a bake produces.
- **Emissive materials must use `emission_operator = 1` (Multiply).** Godot's default Add makes
  every texel glow when the emission colour is white; that is how the lava once rendered solid
  white. `tools/material_maker/postprocess.py` writes this for you.
- **Stale mesh files survive reimport.** Godot won't overwrite existing `save_to_file` meshes
  (`models/doorway/leaf_*.res`) on reimport, so delete them before reimporting a changed
  `door_leaves.glb`.
- **Keep CI thin.** When CI is added, build logic lives in scripts that developers run too;
  workflow YAML only calls them.

## 12. Design references

- **`docs/ut99_reference.md`** is the art direction: the UT99 top-100 style guide.
- **`docs/immersive_sim_reference.md`** covers the genre, the UI and the maps:
  - the 80.lv "Five Pillars of Immersive Sims";
  - the owner's inventory references: Deus Ex, Human Revolution and Peripeteia;
  - the Mankind Divided hub map standard;
  - the systems borrowed from Thief, Hitman and System Shock 2.

Two rules for using references:

- **Cite, don't recall.** When a decision rests on how a reference does something, name the
  source in the design doc rather than asserting it from memory.
- **Take the shape, not the text.** Names, text, maps and art belong to their owners. We
  inherit system design, never content.

## 13. Documented exceptions

Nothing is an exception until it is listed here with its reason.

- **Brushfire's code-built UI and effects predate these rules.** They are `Hud`, `MainMenu`,
  `PauseMenu`, `SettingsPanel`, `Intermission`, `UiTheme.MakeLabel`, the `Fx` particles and the
  enemy rigs assembled from parts in `Enemy.cs`.
  - They may be maintained for the reference maps, but not extended.
  - Undercity's UI replaces them with mockup-approved `.tscn` screens.
- **The CSG reference level** builds its meshes at runtime, because that is what Godot CSG
  nodes do. It is reference only, and no new level uses CSG.
- **Tool-owned files keep their tool's text.** The OpenSpec CLI writes
  `.claude/skills/openspec-*` and `.claude/commands/opsx/*`, and `openspec update` rewrites
  them. The dash check excludes `.claude/` for that reason. Don't hand-edit them.
- **Brushfire's project doesn't treat warnings as errors yet.** `game/Brushfire.csproj`
  predates section 5.6. Code there is cleaned up when it's touched, and the setting is turned
  on once it builds clean. `Undercity.Core` has it from its first commit.
- **Generated NPC bodies commit their table and glb, not a `.blend`.** `tools/blender/build_npcs.py`
  rebuilds every body byte for byte from `tools/blender/npcs.json` and the SHA-pinned packs, and
  each body's `.blend` is 12.5 MB, about 275 MB for the 22 bodies. The table is the editable
  source (owner, survey H1, 2026-09-28, approved conditionally).
- **The first RPG spike is parked, not built.** `docs/spikes/rpg-core/` holds an early sketch
  of the inventory, dialog and disguise code. It predates these rules and doesn't compile. It
  is kept as reference for the OpenSpec changes and is not part of any build.

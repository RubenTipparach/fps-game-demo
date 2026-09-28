# Validation: title screen, pause menu with saves, options (title-and-pause)

The step built the owner-approved mockups D5 (title), D6 (pause, with saves) and D7 (options)
(survey, 2026-09-27: "Approve"). This record says what was checked, how, and what the checks
do and don't establish.

## Environment

| Item | Value |
|---|---|
| Machine | Claude Code cloud container, 4-core Intel Xeon at 2.10 GHz, no GPU |
| Renderer | Vulkan on lavapipe (llvmpipe, LLVM 20.1.2), Xvfb `:99` at 1920 x 1080 |
| Godot | 4.7.2 stable, mono |
| .NET | 8.0.425 |
| Seed | `BRUSHFIRE_SEED=7` for the scripted run; the UI checks use `UiFixture.Seed` (7) |
| Lighting | Only Lantern Row is baked (commit 70b0c03); the other seven sectors aren't yet |

## Checks

| Check | Command | Result |
|---|---|---|
| Core tests | `dotnet test core` | 85 passed, 0 failed (12 of them new: save rule, slots, quit warning, save list order, Continue, damaged saves, objective rule) |
| Core format | `dotnet format --verify-no-changes` in `core/` | clean |
| Game build | `dotnet build` in `game/` | succeeded, 0 warnings |
| Panel sizes | `godot --headless --path game res://ui/undercity/ui_size_test.tscn` | 311 passed, 0 failed; now covers `pause`, `pause/load`, `options/0-2`, `title`, `title/load` |
| Specs | `openspec validate --all` | 14 passed, 0 failed |
| Dash check | CLAUDE.md section 4 | clean |
| UI captures | `godot --path game --resolution 1920x1080 res://ui/undercity/ui_capture.tscn` | `docs/screenshots/undercity_ui/`: `title`, `title_load`, `pause`, `pause_load`, `pause_refused`, `options_controls`, `options_video`, `options_audio` |
| Scripted run | `BRUSHFIRE_AUTOTEST=docs/playtest/scripts/title_and_pause.json godot --path game` | see below; stills in `docs/screenshots/title_and_pause/` |

## The scripted run

`docs/playtest/scripts/title_and_pause.json`, run in a save folder emptied first (the
container's earlier test saves were moved aside). Each line is from the run's log or a still:

| Step | Result | Still |
|---|---|---|
| The game starts | The title is the main scene; with no saves it offers New game, Options and Quit only | `01_title.png` |
| New game | The hub loads in capsule 12: level 1, 150 cr, the start kit | `02_new_game_hub.png` |
| Esc | The pause menu opens over the dimmed, paused hub; Resume is focused | `03_pause.png` |
| Slot 1, Save here | "Saved: slot 1."; slot 1 lists first, newest | `04_saved_slot_1.png` |
| Credits +500, then Load, slot 1 | The run had 650 cr; after the load it has 150 cr again | `05_pause_load.png`, `06_loaded.png` |
| Options | Opens over the pause menu on Controls; Back returns | `07_options.png` |
| Quit to title | The newest save was over 5 minutes old by the wall clock (lavapipe renders the hub slowly), so the first press asked: "QUIT ANYWAY", "Last save 5 m ago." | `08_quit_asks.png` |
| Quit to title again | Back at the title, where Continue now names the autosave | `09_back_to_title.png` |

An earlier run of the same script was killed by its 900 s timeout after step 4, and a second
one found slot 1 already written by it, so "Save here" was greyed and skipped. That is the
rule working (an existing slot is overwritten, not saved into), but it proved nothing about a
fresh save, hence the clean run above.

## What the checks establish

- The save rule, the slot list and its order, Continue's choice, damaged-save handling, the
  quit warning's 300 s boundary and the shared objective rule behave as the spec says
  (`openspec/specs/title-and-pause`), in the core, headless.
- Every new panel keeps its pinned size with overlong text in every label and button.
- In the real game, the title is the first screen, New game reaches the hub, Esc opens the
  pause menu over the paused game, a save goes into slot 1 and lists newest first, a load
  through the pause menu restores the run, Options opens from the pause menu, and Quit to
  title asks once when the newest save is over 5 minutes old.

## What they don't establish

- **Frame time.** Lavapipe doesn't measure it, and nothing here was timed.
- **The refusal in the real game.** The greyed save buttons with a hostile watching are shown
  on the UI fixture (`pause_refused.png`), and the rule is unit-tested. No scripted run turns
  MerSec hostile and then opens the pause menu.
- **Every option taking effect.** The options screen reads and writes Brushfire's
  `GameSettings`, whose file format is unchanged. The run opens it; it doesn't move each
  slider and check the effect.
- **A visual sign-off.** The captures are for the owner to compare with D5 to D7; a passing
  check is not approval.

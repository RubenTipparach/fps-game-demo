# Tasks

## 1. Approval

- [x] 1.1 Owner approves mockups D5, D6 and D7 (survey, 2026-09-27: "Approve").

## 2. Core

- [x] 2.1 `SaveStore` named slots (`slot_1`-`slot_3`) and a `SaveSummary` (place, play time, written) read from the save itself.
- [x] 2.2 `SaveRules.CanSave(situation, out reason)` (built in the core as a static rule; the design first named it `GameState.CanSave`): refused in conversation or while seen by a hostile; tests.

## 3. Godot

- [x] 3.1 `title.tscn`, `pause.tscn`, `options.tscn` in the Undercity theme; the size test covers them.
- [x] 3.2 The main scene becomes the title screen; Esc opens the pause menu.
- [x] 3.3 Captures: each screen (`docs/screenshots/undercity_ui/`), and a save and load through the pause menu (`docs/screenshots/title_and_pause/`, `docs/validation/2026-09-28-title-and-pause.md`).

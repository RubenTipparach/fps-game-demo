# Proposal: a title screen, a pause menu with saves, and options

## Why

The owner, 2026-09-27 (survey G1): mock up the title screen and the pause menu now. Then, on
the mockups (survey D5, D6, D7): "Approve". The hub
playtest starts straight in a new game. F5 and F9 save and load, and Esc only frees the mouse.
Nobody but the owner can playtest like that.

## What Changes

- **A title screen (mockup D5):** Continue (the newest save), New game, Load, Options, Quit.
- **A pause menu (mockup D6):**
  - on the left: Resume, Save, Load, Options, Quit to title, Quit game;
  - beside them: where you are, the current objective and the save slots.
- **Options (mockup D7):** Controls, Video and Audio tabs, one row per setting, each a label and
  a control. They are Brushfire's existing settings (`GameSettings`), in Undercity's theme. The
  settings file is unchanged.
- **Brushfire's menus stay for the reference maps.** The Brushfire main menu, pause menu and
  settings panel are code-built UI (CLAUDE.md 13); they stay only for those maps. Undercity gets
  authored scenes.

## Capabilities

### New Capabilities
- `title-and-pause`: the title screen, the pause menu, save slots in the UI, and options.

### Modified Capabilities
None.

## Impact

- `game/ui/undercity/title.tscn`, `pause.tscn` and `options.tscn`, styled by
  `undercity_theme.tres`.
- `SaveStore` gains named slots. Its temp-file-and-rename writing stays.
- The project's main scene becomes the title screen. It's the hub today.
- The mockups are on the design page (F12). They were approved on 2026-09-27 (survey D5, D6
  and D7), and building started the same day.

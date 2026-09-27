# Design: title, pause and options

## Context

The approved deck and dialog mockups (D1, D2) set the look: the wrist-deck frame, the palette and
the four fonts. The pause menu reuses that frame, and the title screen stands over a still of
the city. See the design page, section F12.

## Decisions

### 1. Title screen (D5)

| Item | Does | Shown when |
|---|---|---|
| Continue | loads the newest save of any slot | a save exists |
| New game | a new run in capsule 12, with a new seed | always |
| Load | the save list: slot, place, play time, time written; newest first | a save exists |
| Options | the options screen | always |
| Quit | quits | always |

Continue's line reads, for example, "auto · Low Harbor · 1 h 42 m". The data comes from
`SaveStore.List()` and the save's own `World.CurrentLevel` and `World.PlayTimeS`, so nothing is
stored twice.

### 2. Pause menu (D6)

- **Esc opens it** when no other screen is open. Esc again, or Resume, closes it.
- **The game pauses under it.** It doesn't under the deck, which is part of play.
- **The right side** shows the location, play time, credits and the first active objective. It
  uses the same objective rule as the HUD.
- **Save slots:** quick, auto and three named slots, `slot_1` to `slot_3`.
  - Save here writes the selected empty slot; Overwrite writes over the selected one.
  - Saving is refused during a conversation, or while a hostile can see the runner. The button
    is greyed with the reason, taken from the same rule that refuses the save.
- **Quit to title** asks once if the newest save is older than 5 minutes (300 s, a data value).

### 3. Options (D7)

Three tabs, with one row each, a label and a control:
- **Controls:** mouse sensitivity, invert look, field of view, head bob, controller sensitivity.
- **Video:** fullscreen, retro filtering.
- **Audio:** master, music and effects volume.

They read and write Brushfire's `GameSettings`, so the settings file keeps its format.

### 4. Where it lives

- Scenes are authored `.tscn` files; there is no code-built UI (CLAUDE.md 8).
- Panels are a fixed size, and the size test covers the new screens.
- The main scene becomes `ui/undercity/title.tscn`. A level opened directly (F6 in the editor)
  still starts a new game, as today.

## Risks / Trade-offs

- **Pausing the tree freezes the HUD's feed timers too.** That's intended: nothing happens while
  paused.
- **Named slots add a UI for naming.** For now they are three fixed slots, which avoids a text
  field.

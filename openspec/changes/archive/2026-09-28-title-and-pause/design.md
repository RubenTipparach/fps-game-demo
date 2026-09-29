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

### 5. As built (after the owner approved D5, D6 and D7 on 2026-09-27: "Approve")

- **The numbers are data:** `data/saves.json` holds `named_slots` (3), `quit_warn_after_s`
  (300) and `hostile_watch_m` (25). `SavesTable` validates them on load.
- **One save rule.** `SaveRules.CanSave(situation, out reason)` in the core. The level gathers
  the facts (a conversation is open; a hostile NPC can see the runner within
  `hostile_watch_m`) in `ILevelHost.SaveRefusal()`, and `TrySave` asks the same method before
  writing. The quicksave key and the pause menu both go through `TrySave`, so the greyed button
  and the refusal can't disagree (CLAUDE.md 5.1). The game's own autosaves (a level change, the
  capsule bed) aren't player saves and skip the rule.
- **Slots.** The player may write quick and the named slots, never auto: the game rewrites it
  at the next door.
- **Place is the level's title** ("Low Harbor"). A save holds the level, not the district, so
  the save rows show the level. The mockup's district names were illustrative.
- **Both quits ask.** Quit game loses unsaved play the same way Quit to title does, so it asks
  by the same rule. The button relabels to "QUIT ANYWAY" and the status line names the age of
  the newest save; a second press quits.
- **Options has a Back button.** The title screen is used with the mouse, and Esc is not
  named anywhere (CLAUDE.md 8), so Back is the one visible way out. It is the only addition to
  D7.
- **The objective rule moved into the core** as `QuestLog.Current()`; the HUD and the pause menu
  both call it.
- **The title's backdrop** is the approved mockup's city, exported from the design page to
  `ui/undercity/title_backdrop.svg`. A baked still of the hub can replace it later without
  touching the scene's structure.
- **Wiring.** The Game autoload implements `IShell` (new game, load, title, quit, settings)
  and hands it to the title screen and each level as they enter the tree. It subscribes in
  `_EnterTree`, because at startup the main scene enters the tree before any `_Ready`.

## Risks / Trade-offs

- **Pausing the tree freezes the HUD's feed timers too.** That's intended: nothing happens while
  paused.
- **Named slots add a UI for naming.** For now they are three fixed slots, which avoids a text
  field.

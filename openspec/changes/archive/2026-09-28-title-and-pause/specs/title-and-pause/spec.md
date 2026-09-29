## ADDED Requirements

### Requirement: The title screen continues the newest save
The title screen SHALL offer Continue and Load only when a loadable save exists, and Continue
SHALL load the newest loadable save of any slot. A file in the save folder that isn't a save
SHALL be listed as damaged and never continued.

Pinned by `SaveStoreTests` (`Continue_picks_the_quicksave_when_it_is_newer_than_the_autosave`,
`A_damaged_file_is_listed_as_damaged_and_never_continued`, `With_no_saves_there_is_nothing_to_continue`)
and the captures `docs/screenshots/title_and_pause/01_title.png` (no saves: no Continue) and `09_back_to_title.png` (Continue names the newest save).

#### Scenario: A player with saves
- **WHEN** the title screen opens and the quicksave is newer than the autosave
- **THEN** Continue shows the quicksave's place and play time, and loads it

#### Scenario: A damaged quicksave
- **WHEN** quick.json isn't a save and the autosave is readable
- **THEN** the list shows quick as damaged, and Continue loads the autosave

### Requirement: The save list puts the newest save first
The save list, on the title's Load and in the pause menu, SHALL show every slot (quick, auto
and the named slots from `data/saves.json`): the slots holding a save newest first, then the
empty slots in order. Each row SHALL be read from the save itself: place, play time, and when
it was written.

Pinned by `SaveStoreTests.The_save_list_puts_the_newest_save_first_and_empty_slots_last` and
`SaveRulesTests.The_slots_are_quick_auto_and_three_named_slots`.

#### Scenario: Two saves and three empty slots
- **WHEN** the quicksave is newer than the autosave and the named slots are empty
- **THEN** the list reads quick, auto, slot 1, slot 2, slot 3

### Requirement: Saving says why it can't
Saving SHALL be refused during a conversation or while a hostile can see the runner within
`hostile_watch_m`, by one rule (`SaveRules.CanSave`) that both the quicksave key and the pause
menu use. The pause menu SHALL grey its save buttons and show that rule's reason. The player
SHALL NOT write the autosave slot.

Pinned by `SaveRulesTests` (`A_watching_hostile_refuses_the_save_and_says_why`,
`A_conversation_refuses_the_save_and_says_why`, `The_player_may_write_every_slot_but_auto`)
and the capture `docs/screenshots/undercity_ui/pause_refused.png`.

#### Scenario: Saving in a fight
- **WHEN** MerSec is hostile and can see the runner
- **THEN** Save here and Overwrite are greyed, the reason reads "Not while hostiles can see
  you.", and no file is written

### Requirement: Quitting asks once when the last save is old
Quit to title and Quit game SHALL ask once, by relabelling the button and naming the age of the
newest save, when there is no save or the newest is older than `quit_warn_after_s` (300 s).
A second press SHALL quit.

Pinned by `SaveRulesTests.Quit_to_title_asks_only_once_the_newest_save_is_older_than_five_minutes`
and the scripted run `docs/playtest/scripts/title_and_pause.json` (capture `08_quit_asks.png`).

#### Scenario: A fresh save
- **WHEN** the newest save is exactly 300 s old
- **THEN** Quit to title leaves at once

#### Scenario: An old save
- **WHEN** the newest save is 301 s old
- **THEN** the first press relabels the button "Quit anyway" and names the age; the second quits

### Requirement: The HUD and the pause menu show the same objective
The HUD and the pause menu SHALL show the objective from one rule (`QuestLog.Current`): the first
active quest in table order and its first visible objective not yet done.

Pinned by `CurrentObjectiveTests`.

#### Scenario: The arrival
- **WHEN** only the arrival quest is active
- **THEN** both show its first visible objective

### Requirement: Menu panels keep their size
The pause menu, the options screen (each tab) and the title's Load panel SHALL keep their pinned
sizes whatever text they hold.

Pinned by `ui_size_test.tscn` (checks `pause`, `pause/load`, `options/0-2`, `title`, `title/load`).

#### Scenario: An overlong string
- **WHEN** every visible label and button holds an overlong string
- **THEN** every panel is the size it was two frames earlier

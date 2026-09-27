## ADDED Requirements

### Requirement: The title screen continues the newest save
The title screen SHALL offer Continue only when a save exists, and Continue SHALL load the newest
save of any slot.

#### Scenario: A player with saves
- **WHEN** the title screen opens and the quicksave is newer than the autosave
- **THEN** Continue shows the quicksave's place and play time, and loads it

### Requirement: Saving says why it can't
The pause menu SHALL refuse to save during a conversation or while a hostile can see the runner,
and SHALL show the reason, from the same rule that refuses the save.

#### Scenario: Saving in a fight
- **WHEN** MerSec is hostile and can see the runner
- **THEN** Save here is greyed and says why, and no file is written

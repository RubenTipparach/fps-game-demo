# Design: dialog and social

## Context

Deus Ex's conversations are linear exchanges with occasional choices, and its skills rarely
show up in them. Human Revolution added social "boss fights" against named characters.
Undercity keeps the Human Revolution shape but uses the skill ranks directly, deterministic
and visible: "[Deception 3] Mother says let them go."

## Goals / Non-Goals

**Goals:**
- A choice can do anything a mission needs: open a door, give or take an item, start a
  fight, end one, complete an objective.
- The player always sees what a choice needs, and whether they have it.
- Writers work in data. Nothing in a tree needs code.

**Non-Goals:**
- Voice acting and lip sync in the slice. Lines are subtitles with a speaker portrait camera.
- Timed choices.
- Romance.

## Decisions

### 1. Tree format

```json
{
  "id": "twitch", "name": "Twitch",
  "starts": [
    {"if": [{"npc": "twitch", "status": "suspicious"}], "node": "wary"},
    {"node": "intro"}
  ],
  "nodes": {
    "intro": {
      "say": ["Mother said nobody comes down here. So what are you?"],
      "choices": [
        {"text": "Mother says let them go. City paid.", "check": {"skill": "deception", "dc": 2},
         "pass": "released", "fail": "blown"},
        {"text": "You look tired. Go get a drink, I'll watch them.",
         "check": {"skill": "persuasion", "dc": 3}, "pass": "break", "fail": "wary"},
        {"text": "[Give 200 cr] For your trouble.", "if": [{"credits": 200}],
         "do": [{"credits": -200}], "next": "bribed"},
        {"text": "Nothing. Carry on.", "exit": true}
      ]
    },
    "released": {"say": ["...Fine. Your head, not mine."],
                 "do": [{"open": "drains:Cage"}, {"objective": "m1/free_hostages"}], "exit": true},
    "blown":    {"say": ["You ain't one of ours!"], "do": [{"npc": "twitch", "do": "hostile"}], "exit": true}
  },
  "barks": {"spotted": ["Oi!", "Who's that?"], "lost": ["Rats in the walls..."]}
}
```

### 2. Conditions (`if`)

Every condition in a list must hold (AND). A choice with alternatives is written as two
choices.

| Condition | Meaning |
|---|---|
| `flag` / `not_flag` | a story flag is set or not |
| `item` / `no_item` (+ `count`) | the pack holds an item |
| `credits` | at least N credits |
| `skill` + `min` | a check value of at least N (a build gate, shown greyed) |
| `disguise` | wearing a disguise accepted by this faction |
| `quest` + `state` | quest not started, active, done or failed |
| `objective` / `not_objective` | an objective is complete or not |
| `npc` + `status` | alive, unconscious, dead, hostile, suspicious |
| `rep` + `min` / `max` | faction reputation is in a range |
| `parley` | a truce with this faction is in force |

- **Story conditions hide a choice.** The player never sees a choice about a thing they
  don't know.
- **Build conditions show it greyed** with the requirement ("[Persuasion 3]", "[200 cr]"), so
  the player learns what a build would open.

### 3. Checks

`{"skill": "deception", "dc": 3}` or `{"cover": 4}`.
- **A skill check** passes if check value >= DC.
- **A cover check** passes if Cover (Deception + disguise quality) >= the number. Bosses use
  it.
- **Passing pays 25 x DC XP,** once per choice.
- **A failed lie to a hostile** goes to its `fail` node, which usually turns them hostile.
  Fast Talk (Deception 2) gives one retry per NPC per mission.

### 4. Effects (`do`)

| Effect | Does |
|---|---|
| `flag` / `unflag` | sets or clears a flag |
| `give` / `take` (+ `count`) | moves items; a full pack drops the item at the player's feet |
| `credits` (+/-) | pays or charges |
| `xp` | awards XP with a source id |
| `rep` (+/-, faction) | changes reputation (Friendly: gains +25 %) |
| `start_quest`, `objective`, `reveal`, `complete_quest`, `fail_quest` | quest log |
| `trade` | opens the trade screen with this NPC's vendor stock |
| `heal` | restores health (Doc Vo) |
| `open` | opens a door or container by stable id |
| `npc` + `do` | `hostile`, `calm`, `follow`, `flee`, `surrender`, `move_to <marker>`, `stand_down` |
| `parley` | starts a truce with a faction |
| `say` | queues a feed line |

### 5. Who can be talked to

| NPC | Talk when |
|---|---|
| Hub civilians and contacts | always (unless hostile to you) |
| Faction members in their territory | disguise verdict Accepted with talking = true, or parley in force |
| A suspicious guard | only with the `wary` start node: they want answers, and checks are harder (+1 DC) |
| A hostile in combat | never; Intimidate may force a surrender below 50 % health if Persuasion >= their I |

Talking starts with a disguise judgement at talking range (always inside scrutiny). If it
fails, the tree's `blown` start runs: "You ain't one of ours!"

### 6. Factions and reputation (`data/factions.json`)

| Faction | Start rep | Territory | Default stance | Notes |
|---|---:|---|---|---|
| Sump residents | +10 | hub | friendly | talkable; rumours; tip you off |
| Drain Rats | -20 | the Drains | hostile in territory, neutral in the hub | respirators: immune to gas |
| Scrap Kings | -10 | the Yard | hostile in territory, neutral in the hub | robot dogs; cyber-arms |
| MerSec | 0 | checkpoint, station, Precinct 9 | neutral; hostile if weapons are drawn in the hub after one warning | corrupt, bribable |
| City Sanitation | +5 | depot, maintenance | friendly | overalls get you into maintenance areas |

| Reputation | Stance | Effect |
|---:|---|---|
| <= -50 | Hated | hostile everywhere, even in the hub |
| -49 to -10 | Disliked | prices x1.1; some doors stay shut |
| -9 to 24 | Neutral | normal |
| 25 to 59 | Liked | prices x0.9; extra dialog |
| >= 60 | Trusted | faction doors open; members warn you of alarms |

Big swings come from story outcomes, for example saving both hostages (+30 Sanitation) and
killing Mother Rat (-40 Rats, +10 residents). Kills and theft in view move reputation in small
steps.

### 7. Civilians and barks

- **Small talk.** A civilian gets 3 small-talk lines and 1 rumour, chosen with
  `IRandomSource` seeded by their stable id, so a save always hears the same thing.
- **Rumours** are hints about routes ("They say the Rats come up through the canal outfall").
  Friendly (Persuasion 1) adds a second rumour.
- **Barks** have types: greeting, spotted, suspicious, lost, found_body, alarm, hurt, surrender.
  Each NPC's tree may override the faction's default barks.

### 8. The dialog screen (mockup in the design page)

- **Layout.** A letterbox, with the camera framing the speaker from the shoulder up. The
  speaker's name and faction sit at the bottom left, and the line appears as a subtitle.
- **Choices** are a numbered list (keys 1 to 9).
  - Requirement tags are in brackets.
  - Met requirements are tagged in the accent colour; unmet ones are greyed out and
    unselectable.
  - A check already passed shows "[Deception 2: passed]".
- **Fixed panel size.** Long lines scroll inside the subtitle panel; they never grow it.
- **Disguise talks show a cover readout** in the corner ("COVER 4 vs I 3"), from the same rule
  as the AI.

## Risks / Trade-offs

- **Visible requirements spoil some surprises.** That's the pillar ("deterministic checks"):
  it makes builds legible. Surprises come from outcomes, not from hidden gates.
- **Authoring cost.** Twelve named hub NPCs plus about 8 named hostiles is a lot of writing. The
  validation test keeps it from rotting, and the design page lists every named NPC with their
  purpose.

# Proposal: dialog trees, talking to hostiles, factions and reputation

## Why

The owner asked for "dialog trees with NPCs": "Every npc in hub area you can talk to, and if
you find a good disguise you can also talk to hostile dudes too, but you would need a higher
skill to fool more intelligent enemies." Social play is one of the three ways through every
objective (CLAUDE.md 7.1), so dialog has to be as capable as a gun. Its choices have to open
doors, move quests, start fights and end them.

## What Changes

- **Data-driven dialog trees** in `data/dialog/<tree>.json`: nodes, lines, choices,
  conditions, deterministic checks and effects. A validation test catches dangling links,
  unknown ids and dead ends.
- **Every hub NPC has a tree.** Named characters get authored content. Civilians get seeded
  small talk and a rumour pool.
- **Hostiles are talkable** when the disguise verdict is Accepted (perception-and-disguise).
  Talking always applies full scrutiny, and bosses add their own checks.
- **Parley.** A negotiated truce (through Skiv, for the Rats) makes a gang neutral while your
  weapons stay holstered. It is a social route that needs no disguise.
- **Factions and reputation.** Five factions, each with a reputation from -100 to 100 and
  stance thresholds. Reputation feeds prices, dialog conditions and hub behaviour.
- **Barks.** Short context lines (spotted, lost you, found a body, greeting) come from the same
  data, seeded per NPC.
- **The dialog screen:** a letterboxed camera on the speaker, the line as a subtitle, and
  numbered choices with visible requirements. Mockup in the design page.

## Capabilities

### New Capabilities
- `dialog-and-social`: dialog data and evaluation, checks, effects, talking to hostiles,
  parley, factions, reputation and barks.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Dialog`, `Undercity.Core/Factions`, `data/dialog/*.json`,
  `data/factions.json`, `data/barks.json`.
- Consumes `character-progression` (checks), `inventory-and-equipment` (items, trade) and
  `perception-and-disguise` (verdicts).

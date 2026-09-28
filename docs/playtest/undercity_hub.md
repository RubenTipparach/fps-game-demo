# Playtest: Low Harbor (the hub) and the systems

This is the first playable Undercity slice. It covers the hub and the systems. The Drains and the
Yard come next. Their exits are in the hub, but they tell you they're not in this build.

## Running it

- **In the editor.** Open `game/` in Godot 4.7 (.NET), then press Play. The game opens on the
  title screen: Continue loads your newest save, New game starts in capsule 12. Opening
  `levels/undercity/hub/hub.tscn` and pressing F6 skips the title and starts a new game.
- **From a terminal:**

  ```sh
  godot --path game
  ```

- **Fixed seed.** `BRUSHFIRE_SEED=<n>` fixes the new game's seed, which sets civilian looks, lines
  and barks.
- **The Brushfire reference levels** are still there. Open `scenes/ui/main_menu.tscn` and press
  F6.

## Controls

| Key | Does |
|---|---|
| WASD, mouse | Move, look |
| Shift, Ctrl, Space | Sprint, crouch, jump |
| E | Use: talk, open, search, read, take, travel. Hold it for locks (the timer stands in for the minigames, owner decision B2). |
| 1 to 0 | Belt slots: draw or holster a weapon, use a medkit or stim |
| Tab | The deck: Inventory, Skills, Journal (F1 to F3 switch tabs) |
| Esc | Close a screen; otherwise the pause menu (the game stops under it) |
| F5, F9 | Quicksave, quickload (no saving in a conversation or while a hostile can see you) |
| F | Flashlight |

In the deck:
- click an item to see it;
- use the buttons to Use, Equip or Drop it;
- while it's selected, press 1 to 0 to put it on the belt;
- click a worn item to take it off.

## Things to try

1. **Arrival.** Read the terminal in capsule 12 at the Golden Carp. Silk wants you at the Rusty
   Anchor's back room.
2. **Tank** guards the back room. He takes Persuasion 2 or 50 cr. The alternative is to pick the
   back door on Market Street (Lockpicking 1).
3. **Silk** gives M1 Rat Trap and M2 Chop Job. Persuasion 3 raises the fee by 25 %.
4. **Shops.**
   - Kessler sells weapons, ammo, tools and gear. Persuasion 2 gets you a box of rounds for
     loyalty.
   - Doc Vo heals at 5 cr a point and sells medkits.
   - Mags sells drinks and gives S4.
   - Nguyen sells noodles. Buy a bowl and he'll tell you the storm drain code.
   - Rivet runs the Fish Hall black market. He buys stolen goods, and sells his Rat jacket for 60,
     or 40 with Persuasion 1.
   - The Oracle buys data shards.
   - Sister Lin sells the Silver Lighter.
5. **S3 Mouse's Debt.** Mouse in the Tin Stacks owes Officer Dace 300 cr. You can:
   - pay it;
   - talk Dace down with Persuasion 3;
   - hack the Precinct 9 records terminal (Hacking 2) for his ledger, then lean on him with
     Persuasion 2. That also opens his checkpoint for good.
6. **The checkpoint to the Yard.** Dace lets you through for:
   - the gang pass, which Jax gives up to Deception 2;
   - 150 cr;
   - Persuasion 3;
   - Deception 2 ("City Sanitation").

   Or climb the jersey blocks behind the camera.
7. **Disguises.** Petra gives sanitation overalls once M1 is active, or you can take them from the
   depot lockers, which is theft. Wear them (deck, Equip) and watch the disguise chip bottom left.
   The depot is restricted: its staff warn you and then report you, unless your disguise holds.
8. **The law.** Draw the pistol (its belt key) where a MerSec trooper can see you, and you get one
   warning. A second time within 60 s and MerSec is hostile. Picking a lock or taking from
   someone's container in view of a resident or a trooper costs 5 reputation with the residents.
9. **Secrets.** These are:
   - the rooftop stash on the Golden Carp's roof;
   - the girder cache on the Skyway service deck (the service lift takes Hacking 1);
   - the drowned locker under the Tin Bridge;
   - the shrine's offering box (Lockpicking 2).
10. **Sleep** in capsule 12. It heals you and saves.
11. **The pause menu.** Esc. Save into slot 1 to 3 (or over the quicksave), load any slot, or
    open Options. Draw your pistol in front of MerSec twice first: with a hostile watching, the
    save buttons grey out and say why. Quit to title asks once if your last save is more than
    5 minutes old.

## What isn't in this build

- **Combat.** A drawn pistol can't fire yet, and hostile MerSec don't attack: they stop talking and
  watch you. Combat comes with `openspec/changes/combat-and-enemies`.
- **The lockpicking and hacking minigames.** A held timer stands in for both until mockups E1 and
  E2 are approved.
- **Missing screens.** There's no trade screen, stash screen, map, notes or conversation log,
  because none of them has an approved mockup yet. The title screen, the pause menu and options
  are in (mockups D5 to D7).
- **Missions.** The Drains and the Yard aren't built. The hub's lighting is baked, all eight
  sectors (stills in `docs/screenshots/hub_lit/`).

## Exporting

There is no export preset yet. When one is added, its include filter must list `data/*.json`: the
game reads its tables from `res://data` at start.

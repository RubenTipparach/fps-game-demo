# Immersive sim reference

Notes on the references Undercity's design leans on. The rule for using them is in CLAUDE.md
section 12: cite the source, and take the shape, not the text. Names, words, maps and art
belong to their owners.

## 1. "The Five Pillars of Immersive Sims"

Maxim Samoylenko, 80.lv, 27 May 2018. https://80.lv/articles/five-pillars-of-immersive-sims
(shared by the owner, 2026-09-27).

| Pillar | What the article says | Undercity |
|---|---|---|
| Choices | "vastly different ways of overcoming challenges": open levels (Thief), character progression (System Shock 2, BioShock), or both (Deus Ex, Dishonored) | Both. Every objective has force, stealth and social routes (CLAUDE.md 7.1), and seven skills open more (`character-progression`) |
| Tools | "a multitude of meaningful tools" that combine: Thief's water arrows put out torches, Prey's Gloo cannon makes paths | Tools that answer archetypes: gas versus the Kings (no respirators), EMP versus dogs and exo-arms, noise makers versus dogs, darts versus heavies (`combat-and-enemies`) |
| Systems | AI, physics and level design interplay; Dishonored's chaos changes the world; "each playthrough is unique" | Perception, disguise, alarms and reputation interact; outcomes change the hub (`perception-and-disguise`, level changes) |
| Focused design | believable spaces that are "actual places", "an inch wide and a mile deep" | Low Harbor is small and dense: every block has an address, and every NPC talks (`sump-market-hub`) |
| Message | mature storytelling without restricting agency: AI (System Shock), extremes (BioShock), socio-political critique (Deus Ex) | Private police for sale (MerSec), a city that pays gangs to fix what it neglects (the Rats' ransom), and who profits (the ledger) |

## 2. Inventory and character screens (owner, 2026-09-27)

Three screenshots were supplied by the owner.

**Deus Ex (Ion Storm, 2000), inventory tab.**
- A tab row: Inventory, Health, Augs, Skills, Goals/Notes, Conversations, Images, Logs, Exit.
- A grid of items in fixed footprints on the left, with credits in the header.
- A detail panel with weapon stats on the right: ammo, base damage, clip size, rate of fire,
  reload time, recoil, accuracy, range, mass.
- Unequip, Use, Drop and Change Ammo buttons.
- The belt: ten slots numbered 1 to 0, along the bottom.

Taken: the tab row, the grid with a detail panel of numbers, and the belt on 1 to 0.

**Deus Ex: Human Revolution (Eidos Montreal, 2011), inventory.**
- F1 Inventory and F2 Quest tabs.
- Credits, next Praxis and total XP in the header.
- A gold grid of items with stack counts in the corner, and a hotbar under it.

Taken: XP and progress in the header, stack counts on icons, and the F-key tabs.

**Peripeteia (2023), inventory and implants.**
- The inventory is a grid inside a hardware bezel wired into the world, which makes it
  diegetic.
- A body doll shows health per limb and implant slots around it.
- A compass strip runs along the top, and a hotbar numbered 1 to 0 along the bottom.
- The weapon and ammo readout sits bottom right.

Taken:
- the diegetic frame (Undercity's is the runner's wrist-deck);
- the doll, with equipment slots and per-part health;
- the compass strip, for the HUD.

## 3. Hub maps (owner, 2026-09-27)

**Deus Ex: Mankind Divided (Eidos Montreal, 2016), Prague hub map.** Supplied by the owner as
the standard for level maps:
- dense organic building footprints on a dark ground, with streets as negative space;
- district names in spaced capitals, and building names on the buildings;
- numbered points of interest in category colours, and mission markers;
- a legend beside the map listing every number.

Taken: all of it, drawn by `tools/levels/render_map.py` from each level's layout module. No
Prague geography, names or art are used.

## 4. Systems borrowed by shape

| From | Shape | Where in Undercity |
|---|---|---|
| Thief (Looking Glass, 1998) | light and sound as the stealth model | `perception-and-disguise` visibility and noise radii |
| Deus Ex | skills read as numbers; hacking and lockpicking as held timers with consumable tools; the belt | `character-progression`, `world-interaction`, `inventory-and-equipment` |
| Human Revolution | detection arcs around the crosshair; social "boss fights" | the HUD readouts; Mother Rat and Crusher conversations |
| Hitman (IO Interactive) | disguise with enforcers who see through it | intelligence and scrutiny range, where I is the enforcer's strength |
| System Shock 2 (Irrational, Looking Glass, 1999) | progression bought with a scarce resource | skill points versus the 56-point cost of everything |

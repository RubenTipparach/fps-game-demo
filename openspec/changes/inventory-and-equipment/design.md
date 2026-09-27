# Design: inventory and equipment

## Context

The reference screens (see proposal) agree on four things, and Undercity takes all four:
1. Items take space in a grid, so packing is a decision.
2. A detail panel explains the selected item with numbers.
3. A ten-slot belt maps keys to things you carry.
4. Credits and XP sit in the header.

Peripeteia adds a diegetic frame: the screen is a device in the world. Undercity's frame is
the runner's wrist-deck: a scratched, taped hardware bezel around the grid, in the neon-noir
palette.

## Goals / Non-Goals

**Goals:**
- Space as the limit: carrying a shotgun costs you a disguise's worth of room.
- Disguise pieces are ordinary items; wearing them is the whole mechanic.
- Every number on the detail panel comes from the item data.

**Non-Goals:**
- Weight, durability, crafting and weapon mods. These come after the slice; the data leaves
  room.
- Containers inside the pack (bags).
- A separate stash screen. The safehouse stash is a loot container with a big grid.

## Decisions

### 1. The pack

- **Grid and placement.** The pack is 10 columns by 6 rows. An item occupies a `w x h` rectangle
  at an integer cell; items can't overlap and don't rotate (Deus Ex didn't, and fixed shapes
  read faster).
- **Auto-placement** scans rows top to bottom and columns left to right for the first fit.
  Stackable items first top up existing stacks of the same id.
- **Stacks** have a per-item limit (`stack`). Splitting a stack puts the new half at the first
  fit.
- **Pickups that don't fit** stay in the world, and the prompt says "no room". A container
  keeps whatever didn't fit.
- **Dropping** places the item in the world in front of the player, settled on the floor.
  Dropped items persist like any other world item.

### 2. Equipment

| Slot | Takes | Disguise weight | Examples |
|---|---|---:|---|
| HEAD | hats, helmets, goggles | 1 | Rat goggles, Kings goggles, sanitation cap |
| FACE | masks, respirators | 1 | Rat respirator (gas immunity), Kings welding mask (flash immunity) |
| BODY | outfits | 2 | Street jacket, Rat jacket, Kings vest, sanitation overalls |
| ARMOR | vests, plates | 0 | Kevlar vest, Rat plates (count as Rat gear) |
| BOOTS | footwear | 0 | Soft soles (footsteps -40 %), steel toes |

- **Swapping.** Equipping moves the item out of the grid. The replaced item goes back into the
  grid; if it can't fit, the swap is refused.
- **Disguise quality Q** is the sum of the disguise weights of worn pieces that match one
  faction (perception-and-disguise).
- **Armour.** Its faction decides whether it clashes with a disguise. Resistances are percent
  per damage type, and the player's total is capped at 60 %.

### 3. The belt

- **Ten slots on 1 to 0.** Each slot points at a pack stack. An item keeps its grid space while
  belted.
- **Auto-belting.** Picking up a weapon or gadget belts it in the first free slot.
  Consumables are auto-belted only if they heal 25 or more.
- **Holstering.** Pressing the key of the drawn weapon holsters it (a drawn weapon blows
  disguises).
- **Empty slots.** When a belted stack is used up, its slot empties; the belt never points at
  nothing.

### 4. Credits and trade

- **Credits** are an integer. Credit chips (25 cr) convert when picked up.
- **Buy price** = `value x buy_mult(vendor) x (1 - 0.15 if Haggler) x rep_mult`.
- **Sell price** = `value x 0.4 x (1 + 0.15 if Haggler)`, rounded down.
- **`rep_mult`** is 1.1 at a Disliked reputation, 1.0 at Neutral and 0.9 at Liked
  (factions in `dialog-and-social`).
- **Stolen goods.** Items taken from an owned container carry `stolen: owner`. They sell only
  to the Fish Hall black market, at 0.3 x value.
- **Vendors restock** when the player returns from a mission (not on a timer). Stock lists are
  in `data/vendors.json`.

### 5. The item catalogue (slice)

| id | Name | Cat | Size | Stack | Value (cr) | Effect |
|---|---|---|---|---:|---:|---|
| stun_baton | Stun baton | weapon | 1x3 | 1 | 120 | melee, 35 stun, non-lethal |
| combat_knife | Combat knife | weapon | 1x2 | 1 | 80 | melee, 40 lethal |
| pistol | Kestrel 10mm | weapon | 2x2 | 1 | 300 | 22 dmg, mag 12, noise 20 m |
| whisper | Whisper 10mm (suppressed) | weapon | 3x2 | 1 | 650 | 18 dmg, mag 10, noise 5 m |
| dart_pistol | Sandman dart pistol | weapon | 2x2 | 1 | 450 | tranq, sleeps in 4 s, mag 4, noise 3 m |
| smg | Rattler SMG | weapon | 3x2 | 1 | 700 | 12 dmg, 10 rounds/s, mag 30, noise 25 m |
| shotgun | Scattergun | weapon | 4x2 | 1 | 800 | 9 x 8 dmg, mag 6, noise 30 m |
| ammo_10mm | 10mm rounds | ammo | 1x1 | 60 | 2 | pistol, Whisper, SMG |
| ammo_shells | Shotgun shells | ammo | 1x1 | 24 | 4 | Scattergun |
| ammo_darts | Tranq darts | ammo | 1x1 | 20 | 12 | Sandman |
| frag_grenade | Frag grenade | gadget | 1x1 | 5 | 120 | 120 blast dmg, 5 m radius, noise 35 m |
| emp_grenade | EMP grenade | gadget | 1x1 | 5 | 150 | disables robots 20 s, turrets 30 s, cameras 60 s, exo-arms 8 s |
| gas_grenade | Knockout gas | gadget | 1x1 | 5 | 140 | KO in 3 s in a 4 m cloud for 8 s; respirators immune |
| noise_maker | Noise maker | gadget | 1x1 | 5 | 40 | 15 m noise after 3 s, lures dogs |
| lockpick | Lockpick | tool | 1x1 | 20 | 30 | one lock (Lockpicking) |
| multitool | Multitool | tool | 1x1 | 20 | 50 | one hack (Hacking) |
| medkit | Medkit | consumable | 1x1 | 5 | 100 | +40 health over 1 s |
| stim | Stim | consumable | 1x1 | 5 | 70 | +25 health now, +20 % speed 10 s |
| noodles | Noodle cup | consumable | 1x1 | 10 | 8 | +10 health |
| synth_whisky | Synth-whisky | consumable | 1x2 | 3 | 25 | +5 health, blur 20 s, +1 Persuasion 60 s |
| neural_chip | Neural chip | consumable | 1x1 | 5 | 0 | +1 skill point |
| street_jacket | Street jacket | clothing BODY | 2x2 | 1 | 40 | no faction |
| rat_jacket | Patchwork hood | clothing BODY | 2x2 | 1 | 60 | Drain Rats, Q 2 |
| rat_goggles | Scavenger goggles | clothing HEAD | 2x1 | 1 | 30 | Drain Rats, Q 1; low-light vision |
| rat_respirator | Rat respirator | clothing FACE | 2x1 | 1 | 40 | Drain Rats, Q 1; gas immunity |
| kings_vest | Kings vest | clothing BODY | 2x2 | 1 | 90 | Scrap Kings, Q 2 |
| kings_goggles | Welder's goggles | clothing HEAD | 2x1 | 1 | 35 | Scrap Kings, Q 1 |
| kings_mask | Welding mask | clothing FACE | 2x1 | 1 | 45 | Scrap Kings, Q 1; flash immunity |
| sanitation_overalls | Sanitation overalls | clothing BODY | 2x2 | 1 | 30 | City Sanitation, Q 2 |
| sanitation_cap | Sanitation cap | clothing HEAD | 1x1 | 1 | 10 | City Sanitation, Q 1 |
| sanitation_mask | Filter mask | clothing FACE | 1x1 | 1 | 15 | City Sanitation, Q 1; gas immunity |
| kevlar_vest | Kevlar vest | armor | 2x2 | 1 | 400 | ballistic 30 %, blunt 10 %; clashes with every disguise |
| rat_plates | Rat plates | armor | 2x2 | 1 | 150 | ballistic 15 %; Drain Rats gear |
| soft_soles | Soft soles | boots | 2x1 | 1 | 200 | footstep radius -40 % |
| steel_toes | Steel toes | boots | 2x1 | 1 | 90 | kick +50 %, footsteps +20 % |
| silver_lighter | Silver lighter | trinket | 1x1 | 1 | 250 | +1 Persuasion while carried |
| sewer_service_key | Sewer service key | key | 1x1 | 1 | 0 | Drains service door |
| pump_room_key | Pump room key | key | 1x1 | 1 | 0 | hostage cage |
| gang_pass | Scrap Kings pass | key | 1x1 | 1 | 0 | yard gate, no questions |
| nav_core | Prototype nav core | quest | 2x2 | 1 | 0 | M2 objective |
| kings_ledger | The Kings' ledger | quest | 1x2 | 1 | 0 | S2 objective |
| mersec_badge | Dented MerSec badge | quest | 1x1 | 1 | 0 | S3 evidence |
| whisky_crate | Case of Mags' whisky | quest | 2x2 | 1 | 0 | S4 objective |
| credit_chip | Credit chip | valuable | - | - | 25 | becomes credits on pickup |
| scrap_electronics | Scrap electronics | valuable | 1x1 | 10 | 15 | sell |
| data_shard | Data shard | valuable | 1x1 | 10 | 60 | sell to the Oracle; some hold passwords |

The starting kit is a stun baton, a Kestrel 10mm with 24 rounds, 2 lockpicks, 1 multitool,
1 medkit and 150 credits. The street jacket is worn. It fills 11 of 60 cells.

### 6. The character screen (mockup in the design page)

- **Frame.** The runner's wrist-deck, a hardware bezel with screws, tape and a cable. It sits
  at a fixed 1280 x 720 reference size and scales as one panel (CLAUDE.md 8).
- **Tabs.** INVENTORY, SKILLS, JOURNAL, MAP, NOTES, CONVERSATIONS, on F1 to F6 (after Deus
  Ex's tab row). The header shows credits, level, XP and XP to next.
- **Inventory tab:**
  - **Left:** the 10 x 6 grid, 48 px cells, with item icons and stack counts.
  - **Middle:** the equipment doll.
    - It shows HEAD, FACE, BODY, ARMOR and BOOTS around a figure.
    - It shows per-part health: head, torso, arms, legs. This is Peripeteia's doll; health per
      part is display only in the slice.
    - The disguise readout under the doll reads "DRAIN RATS Q 3 / COVER 4", from the same rule
      the AI uses.
  - **Right:** the detail panel. It shows the icon, name, category and the numbers from data
    (damage, magazine, noise radius, armour %, faction, disguise weight, value), then the
    action buttons Use, Equip, Drop and Belt.
  - **Bottom:** the belt, ten slots numbered 1 to 0.
- **Panel sizes are fixed.** Names that are too long are truncated with an ellipsis; the
  item list never pushes the layout.

## Risks / Trade-offs

- **No rotation** means some shapes pack badly (a shotgun is 4 x 2). This is intended, and
  it's the same trade Deus Ex made.
- **46 icons must exist.** They're rendered from the item models by a Blender script, so they
  can't drift from the models. Until a model exists, the icon is a labelled placeholder PNG,
  generated too.

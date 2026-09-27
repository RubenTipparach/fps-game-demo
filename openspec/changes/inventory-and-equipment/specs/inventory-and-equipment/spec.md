# Inventory and Equipment

## Purpose

The item catalogue, the grid pack, equipment slots, the belt, credits and trade: what the
player carries, wears and pays with.

## ADDED Requirements

### Requirement: Items take their footprint in a 10 x 6 grid
The pack SHALL be a grid of 10 columns and 6 rows. Each item SHALL occupy its `w x h` cells
from `data/items.json` at an integer position, and items SHALL NOT overlap. Items SHALL NOT
rotate.

#### Scenario: Placing a shotgun
- **WHEN** a 4 x 2 shotgun is picked up into an empty pack
- **THEN** it occupies columns 0-3 of rows 0-1

#### Scenario: No room
- **WHEN** no 4 x 2 space is free
- **THEN** the shotgun stays in the world and the prompt reads "Scattergun: no room"

### Requirement: Stackable items stack to their limit
Picking up a stackable item SHALL first top up existing stacks of the same id, up to the item's
stack limit, and then place new stacks at the first fit. Anything that doesn't fit SHALL remain
in the world or the container.

#### Scenario: Topping up ammo
- **WHEN** the player holds 50 rounds of 10mm (stack 60) and picks up 24
- **THEN** the stack becomes 60 and a new stack of 14 is placed

### Requirement: Five equipment slots
The character SHALL have HEAD, FACE, BODY, ARMOR and BOOTS slots. Equipping SHALL move the item
out of the grid. If the slot was occupied, the old item SHALL return to the grid, and the swap
SHALL be refused, with no change, when the old item can't fit.

#### Scenario: Swapping jackets in a full pack
- **WHEN** the pack has no 2 x 2 space and the player equips a Rat jacket over the street jacket
- **THEN** the swap is refused and both items stay where they were

### Requirement: Armour is capped
The player's armour resistance for a damage type SHALL be the sum of worn items' resistances
for that type, capped at 60 %.

#### Scenario: Stacking resistances
- **WHEN** worn items total 75 % ballistic resistance
- **THEN** ballistic damage is reduced by 60 %

### Requirement: The belt points at pack items
The belt SHALL have ten slots bound to keys 1 to 0. Each slot SHALL reference a pack stack
without removing it from the grid. Picking up a weapon or a gadget SHALL belt it in the first
free slot. A slot whose stack is used up SHALL become empty. Pressing the key of the drawn
weapon SHALL holster it.

#### Scenario: Using the last medkit
- **WHEN** the player uses the last medkit from belt slot 4
- **THEN** slot 4 is empty

### Requirement: Credits and prices come from one rule
Credits SHALL be an integer counter; credit chips SHALL convert on pickup. A vendor's buy and
sell prices SHALL be computed by one function from item value, vendor multiplier, Haggler and
faction reputation, and the shown price SHALL equal the charged price. Stolen items SHALL sell
only to the black market.

#### Scenario: Haggler
- **WHEN** a character with Persuasion 2 buys a 300 cr pistol from Kessler at Neutral reputation
- **THEN** the price shown and charged is 255 cr

#### Scenario: Selling stolen goods
- **WHEN** the player offers Kessler a data shard taken from Mother Rat's safe
- **THEN** Kessler refuses it, and the Fish Hall black market offers 18 cr

### Requirement: The starting kit
A new game SHALL start with a stun baton, a Kestrel 10mm, 24 rounds of 10mm, 2 lockpicks,
1 multitool, 1 medkit and 150 credits, with the street jacket worn.

#### Scenario: New game inventory
- **WHEN** a new game starts
- **THEN** the pack holds those items in 11 cells and the belt holds the baton and the pistol

# Proposal: grid inventory, equipment slots, the belt, credits and vendors

## Why

The owner asked for "inventory, equipment" and sent three reference screens (2026-09-27):
- **Deus Ex (2000):** a tabbed character screen, an item grid on the left, an item detail
  panel with weapon stats on the right, and the ten-slot belt along the bottom.
- **Deus Ex: Human Revolution:** a gold grid of items with stack counts, F1 inventory and
  F2 quest tabs, credits, "next Praxis" and total XP in the header, and the hotbar below.
- **Peripeteia:** a grid mounted in a diegetic hardware frame, a body doll with health per
  limb, a compass strip, and a hotbar numbered 1 to 0.

The inventory is also where disguises live: what you wear decides who you can fool.

## What Changes

- **The pack.** A 10 x 6 grid where each item takes its footprint (a pistol 2 x 2, a shotgun
  4 x 2, a medkit 1 x 1). Stackable items stack to their limit. There is no weight: space is
  the limit.
- **Equipment slots.** HEAD, FACE, BODY, ARMOR and BOOTS. Worn items leave the grid. Clothing
  carries a faction and a disguise value; armour carries resistances.
- **The belt.** Ten quick slots on keys 1 to 0. Each points at a pack item (Deus Ex style), so
  the item still takes grid space. New weapons and gadgets go on the belt automatically.
- **Credits** are a counter, not an item. Credit chips convert on pickup.
- **Vendors** buy and sell through a trade screen. Prices come from one rule that reads value,
  Haggler and faction reputation. Stolen items sell only at the black market.
- **A catalogue of 46 items** for the slice, with footprints, stacks, values and effects, in
  `data/items.json`.
- **The character screen:**
  - tabs: Inventory, Skills, Journal, Map, Notes, Conversations;
  - the grid and a detail panel;
  - an equipment doll with per-part health;
  - the belt.

  Mockups are in the design page; each is built only after approval.

## Capabilities

### New Capabilities
- `inventory-and-equipment`: the item catalogue, grid placement and stacking, equipment slots,
  the belt, credits and trade.

### Modified Capabilities
None.

## Impact

- `Undercity.Core/Items`, `Undercity.Core/Inventory`, `data/items.json`, `data/vendors.json`.
- Brushfire's `WeaponManager` ammo dictionary is replaced, for Undercity, by ammo items in the
  pack. The reference maps keep theirs.
- Icons: `game/ui/icons/<id>.png`, rendered from each item's model by a Blender script, so
  the icon always matches the model.

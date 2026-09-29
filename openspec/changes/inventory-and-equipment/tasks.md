# Tasks

## 1. Data

- [ ] 1.1 `data/items.json` with the 46-item catalogue, and `data/vendors.json` (Kessler, Doc Vo, Mags, Nguyen, the black market, Old Wick). The catalogue and the hub vendors are done; Old Wick comes with the Drains.
- [x] 1.2 Schema: footprint 1-4 x 1-3, stack >= 1, slot matches category, faction ids exist, weapon ids exist.

## 2. Core

- [x] 2.1 `Pack`: place, first fit, top up stacks, split, move, remove, `RoomFor`.
- [x] 2.2 `Equipment`: equip and swap (refuse if the old item has no room), unequip, disguise pieces by faction, armour totals capped at 60 %.
- [x] 2.3 `Belt`: slots point at stacks; auto-belt rules; empties when a stack is used up.
- [x] 2.4 `Wallet` and `Vendor.Price(item, vendor, character, reputation)` used for both display and charge.

## 3. Tests

- [x] 3.1 First fit and stacking; a full pack refuses; leftovers are reported.
- [x] 3.2 Swap refused when the old item cannot fit; the pack is unchanged.
- [x] 3.3 Price rule including Haggler, reputation and stolen goods.
- [ ] 3.4 Starting kit fills 11 cells.

## 4. Interface (after mockup approval)

- [ ] 4.1 Character screen frame and tabs; inventory tab; trade screen; pickup prompt.
- [ ] 4.2 `tools/blender/render_icons.py`: icons from item models; placeholders for missing models.
- [ ] 4.3 Captures: the inventory with the starting kit; a full Rat disguise worn; a trade with Kessler.

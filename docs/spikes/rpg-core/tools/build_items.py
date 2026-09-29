#!/usr/bin/env python3
"""Undercity item database -> game/data/items.json (validated).

Sizes are inventory-grid cells (10 x 6 grid). Clothing carries a faction tag and a cover value
(disguise quality: body 2, head 1, face 1). Weapons name the viewmodel node they unlock;
ammo names the AmmoType it feeds. Icons are rendered by tools/blender/build_items.py.

    python3 tools/rpg/build_items.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "data", "items.json")

FACTIONS = {"", "drain_rats", "scrap_kings", "city_sanitation", "mersec"}
CATS = {"weapon", "ammo", "consumable", "gadget", "clothing", "armor", "key", "quest", "valuable"}
SLOTS = {"none", "head", "face", "body", "armor", "boots"}


def item(id, name, cat, w=1, h=1, desc="", **kw):
    d = dict(id=id, name=name, cat=cat, w=w, h=h, desc=desc, stack=1, value=0, slot="none",
             icon=f"res://ui/icons/{id}.png", model=f"res://models/items/{id}.glb")
    d.update(kw)
    return d


ITEMS = [
    # --- weapons (viewmodel node names in scenes/player/player.tscn)
    item("stun_baton", "Stun Baton", "weapon", 1, 3, "Non-lethal. Knocks targets out; a hit from behind on an unaware target drops them at once (Melee 2).",
         value=150, weapon="Baton"),
    item("pistol", "Silenced Pistol", "weapon", 2, 1, "10mm, suppressed. Quiet enough not to alert the next room.", value=300, weapon="Pistol"),
    item("shotgun", "Shotgun", "weapon", 4, 1, "Loud and brutal up close. Eight pellets.", value=450, weapon="Shotgun"),
    item("smg", "Rotary SMG", "weapon", 3, 2, "Spins up to a hail of 10mm. Loud.", value=600, weapon="Chaingun"),
    item("rocket_launcher", "Rocket Launcher", "weapon", 4, 2, "For when subtlety has failed completely.", value=1200, weapon="RocketLauncher"),
    # --- ammo
    item("ammo_10mm", "10mm Rounds", "ammo", desc="Pistol and SMG ammunition.", stack=120, value=2, ammo_type="bullets"),
    item("ammo_shells", "Shotgun Shells", "ammo", desc="12 gauge.", stack=40, value=4, ammo_type="shells"),
    item("ammo_rockets", "Rockets", "ammo", desc="Unguided 60mm rockets.", stack=12, value=40, ammo_type="rockets"),
    # --- consumables
    item("medkit", "Medkit", "consumable", desc="Restores 40 health.", stack=5, value=60, heal=40),
    item("stim", "Stim", "consumable", desc="Restores 25 health, instantly.", stack=5, value=45, heal=25),
    item("noodles", "Noodle Cup", "consumable", desc="Nguyen's. Warm. Restores 10 health.", stack=5, value=8, heal=10),
    item("synth_whisky", "Synth-Whisky", "consumable", desc="Restores 5 health and some courage.", stack=5, value=15, heal=5),
    # --- gadgets
    item("lockpick", "Lockpick", "gadget", desc="Used up on each lock. Needs Lockpicking at least the lock's tier.", stack=10, value=25, tool="lockpick"),
    item("multitool", "Multitool", "gadget", desc="Used up on each terminal or keypad. Needs Hacking at least the tier.", stack=10, value=40, tool="multitool"),
    item("emp_grenade", "EMP Grenade", "gadget", desc="Stuns robot dogs and cameras and kills searchlights for 10 s.", stack=5, value=120, tool="emp"),
    item("frag_grenade", "Frag Grenade", "gadget", desc="Loud. Messy.", stack=5, value=100, tool="frag"),
    item("noise_maker", "Noise Maker", "gadget", desc="Throw it: guards go to look.", stack=5, value=20, tool="noise"),
    # --- clothing (disguise pieces)
    item("street_jacket", "Street Jacket", "clothing", 2, 2, "Your own clothes. Nobody's colours.", slot="body", value=30),
    item("rat_jacket", "Drain Rats Jacket", "clothing", 2, 2, "Patchwork hood and oilskin. Drain Rats colours.", slot="body", faction="drain_rats", cover=2, value=80),
    item("rat_goggles", "Rat Goggles", "clothing", 2, 1, "Scratched brass goggles the Rats wear down in the dark.", slot="head", faction="drain_rats", cover=1, value=35),
    item("rat_respirator", "Rat Respirator", "clothing", 2, 1, "Filters the sewer air. Hides your face.", slot="face", faction="drain_rats", cover=1, value=40),
    item("kings_vest", "Scrap Kings Vest", "clothing", 2, 2, "Studded leather, chrome crown on the back.", slot="body", faction="scrap_kings", cover=2, armor=5, value=120),
    item("kings_goggles", "Welding Goggles", "clothing", 2, 1, "Scrap Kings shop goggles.", slot="head", faction="scrap_kings", cover=1, value=40),
    item("kings_mask", "Welding Mask", "clothing", 2, 1, "Hides your whole face. Hard to talk through.", slot="face", faction="scrap_kings", cover=1, value=55),
    item("sanitation_overalls", "Sanitation Overalls", "clothing", 2, 2, "City Sanitation hi-vis. Opens maintenance doors socially.", slot="body", faction="city_sanitation", cover=2, value=40),
    item("sanitation_cap", "Sanitation Cap", "clothing", 1, 1, "City Sanitation cap.", slot="head", faction="city_sanitation", cover=1, value=10),
    # --- armour and boots
    item("kevlar_vest", "Kevlar Vest", "armor", 2, 2, "Absorbs 30% of damage. No gang wears these.", slot="armor", armor=30, value=400),
    item("rat_plates", "Scrap Plates", "armor", 2, 2, "Hammered sign-metal plates. Rats wear them; so can you.", slot="armor", faction="drain_rats", armor=15, value=150),
    item("soft_soles", "Soft Soles", "armor", 2, 1, "Footsteps make 40% less noise.", slot="boots", noise=0.6, value=150),
    # --- keys and quest items (not droppable)
    item("sewer_service_key", "Sewer Service Key", "key", desc="City Sanitation key. Opens the maintenance doors in the Drains.", droppable=False),
    item("pump_room_key", "Pump Room Key", "key", desc="Opens the pump station cage.", droppable=False),
    item("yard_keycard", "Yard Keycard", "key", desc="Scrap Kings keycard for the yard gate and warehouse.", droppable=False),
    item("gang_pass", "Scrap Kings Pass", "quest", 2, 1, "A chrome token. The gate guards wave through whoever carries one.", droppable=False),
    item("nav_core", "Prototype Nav Core", "quest", 2, 2, "The target. Heavier than it looks.", droppable=False, value=0),
    item("kings_ledger", "Scrap Kings Ledger", "quest", 1, 2, "Who they sell to, and who they pay off.", droppable=False),
    item("rat_shard", "Skiv's Data Shard", "quest", desc="Messages between Skiv and the camp. Mentions tonight's password.", droppable=False),
    # --- valuables
    item("credit_chip", "Credit Chip", "valuable", desc="Worth 120 credits to Kessler.", stack=10, value=120),
    item("scrap_electronics", "Scrap Electronics", "valuable", desc="Salvage. Kessler pays 30 each.", stack=10, value=30),
    item("data_shard", "Data Shard", "valuable", desc="Encrypted. Someone will pay for it.", stack=5, value=60),
]


def validate(items):
    ids = set()
    for d in items:
        assert d["id"] not in ids, "duplicate " + d["id"]
        ids.add(d["id"])
        assert d["cat"] in CATS, d
        assert d["slot"] in SLOTS, d
        assert d.get("faction", "") in FACTIONS, d
        assert 1 <= d["w"] <= 4 and 1 <= d["h"] <= 3, d
        if d["cat"] == "clothing":
            assert d["slot"] in ("head", "face", "body"), d
        if d["cat"] == "ammo":
            assert d.get("ammo_type") in ("bullets", "shells", "rockets"), d
        if d["cat"] == "weapon":
            assert d.get("weapon"), d
    return ids


def main():
    validate(ITEMS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(ITEMS, f, indent=1)
    print(f"wrote {OUT}: {len(ITEMS)} items")


if __name__ == "__main__":
    main()

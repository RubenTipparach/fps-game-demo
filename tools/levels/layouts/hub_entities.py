"""Low Harbor's gameplay entities: who stands where, and every lock, container, terminal, exit,
zone and trigger the hub places. Metres, x east, y south, as in hub.py.

Single source (CLAUDE.md 7.1). The Blender build (tools/blender/build_undercity.py) places an
`ENT_<kind>_<id>` empty for each entry, carrying `props` as extras. tools/levels/export_level_data.py
writes each entry's `data` to game/data/levels/hub.json under the stable id `hub:<id>`, which is
what Undercity.Core reads. The scene says where a thing is; the data says what it is.

Entry keys:
- kind: npc, civ, exit, loot, item, terminal, door, zone, trigger, spawn, bed, stash.
- id: unique in the level; the stable id is "hub:<id>".
- at: (x, y) in layout metres.
- facing_deg: compass heading, 0 = north (-y), 90 = east. For an NPC, where they look; for a
  terminal, container or exit, the side the player uses it from faces this way.
- z: optional. Omitted means the ground or floor at that spot (the Pit's floor, a room's floor).
  "roof" means the roof of the building under the spot; "service_deck" means the Skyway service
  deck; a number is metres above the street.
- props: placement extras for the scene: an NPC's id, a zone's or trigger's size ("w,d" metres),
  a door's width and style (barrier), an exit's style (gate, grate, panel, none), a container's
  model (locker, safe, crate, tool_box, shelf, offering_box, stash_box), a patrol ("x,y;x,y").
- data: the core's record for it (ContainerDef, DoorDef, TerminalDef, ExitDef, ZoneDef,
  TriggerDef), in data-file form; for an item, the "item:count" spec.

The design is openspec/changes/sump-market-hub (sections 2 to 7).
"""

from .hub import MAP, viaduct_y

# The MerSec pair's beat, from the layout's patrol route (hub.py "patrols", which the design map
# draws), as the patrol prop: "x,y;x,y;...".
_BEAT = next(p["pts"] for p in MAP["patrols"] if p["who"].startswith("MerSec pair"))
PATROL = ";".join(f"{x:g},{y:g}" for x, y in _BEAT)


def _npc(npc_id, at, facing, **props):
    return {"kind": "npc", "id": npc_id, "at": at, "facing_deg": facing, "props": {"npc": npc_id, **props}}


def _lock(tier, kind="door", key=None, code_flag=None, pick=True, hack=False):
    lock = {"tier": tier, "kind": kind, "pick": pick, "hack": hack}
    if key:
        lock["key"] = key
    if code_flag:
        lock["code_flag"] = code_flag
    return lock


# A lock that only a conversation opens (Tank's door, the checkpoint barrier).
_BARRED = _lock(3, pick=False)

NPCS = [
    _npc("silk", (108.5, 51), 270),
    # behind the bar, beside the back-room door (100, 53): the strip between the counter (x 98.8)
    # and the wall (99.9) is 1.1 m wide, room for his 0.7 m capsule
    _npc("tank", (99.3, 55.5), 270),
    _npc("mags", (90, 51), 180),
    _npc("kessler", (138, 55.2), 0),
    _npc("doc_vo", (160, 49.5), 0),
    _npc("nguyen", (106.5, 99.95), 180),
    _npc("rivet", (179.75, 99.9), 180),
    _npc("mouse", (43, 115.5), 270),
    _npc("petra", (227, 108), 270),
    _npc("dace", (169, 155.5), 0),
    _npc("mersec_gate", (168, 161), 0),
    _npc("mersec_station", (120, 30.4), 180),
    _npc("mersec_desk", (228, 132.2), 270),
    _npc("mersec_patrol_a", (40, 39), 90, patrol=PATROL, patrol_start=0),
    _npc("mersec_patrol_b", (146, 96), 135, patrol=PATROL, patrol_start=3),
    _npc("skiv", (50, 146), 270),
    _npc("jax", (181.7, 119.2), 270),
    _npc("lin", (90, 141), 90),
    _npc("oracle", (142.4, 100), 90),
]

# About 35 residents, dock workers and night-market customers (design section 2).
_CIVS = [
    (20, 41, 90), (70, 40.5, 270), (100, 39.5, 180), (125, 38, 0), (150, 39, 90), (180, 40, 270),
    (119, 50, 180), (120, 65, 0),
    (95, 80, 135), (100, 92.5, 45), (112, 89.4, 270), (125, 85, 180), (135, 95, 90), (145, 85, 225),
    (150, 105, 315), (115, 110, 0), (100, 108, 90),
    (83, 57, 90), (90, 64.5, 0), (75, 68, 45),
    (170, 89.4, 180), (176, 103, 0),
    (60, 97.6, 90), (40, 101, 270),
    (32, 145, 45),
    (156, 122, 200), (170, 129.5, 270),
    (110, 142, 180),
    (188, 80, 0), (217.5, 90, 180), (230, 90, 270),
    # Talking partners, 1.4 m from civilians 10, 12, 19 and 31 and facing them: two civilians
    # this close stand talking, face to face (openspec/changes/archive/2026-09-29-crowd-variety, design section 2;
    # data/crowd.json talk_pair_radius_m).
    (101, 91.5, 225), (125, 86.4, 0), (90, 63.1, 180), (228.6, 90, 90),
]
CIVILIANS = [{"kind": "civ", "id": f"civ_{i + 1:02d}", "at": (x, y), "facing_deg": f, "props": {}}
             for i, (x, y, f) in enumerate(_CIVS)]

SPAWNS = [
    {"kind": "spawn", "id": "start", "at": (50, 30.5), "facing_deg": 180, "props": {}},
    {"kind": "spawn", "id": "capsule", "at": (52.2, 26.8), "facing_deg": 180, "props": {}},
    {"kind": "spawn", "id": "storm_drain", "at": (40, 152.5), "facing_deg": 0, "props": {}},
    {"kind": "spawn", "id": "outfall", "at": (189, 98.5), "facing_deg": 270, "props": {}},
    {"kind": "spawn", "id": "checkpoint", "at": (170, 165), "facing_deg": 0, "props": {}},
    {"kind": "spawn", "id": "freight_tunnel", "at": (125.6, 163), "facing_deg": 0, "props": {}},
    {"kind": "spawn", "id": "lift_bottom", "at": (130, 107), "facing_deg": 90, "props": {}},
    {"kind": "spawn", "id": "lift_top", "at": (123.5, viaduct_y(123.5) - 1.5), "facing_deg": 270,
     "z": "service_deck", "props": {}},
]

EXITS = [
    {"kind": "exit", "id": "storm_drain", "at": (40, 156.2), "facing_deg": 0, "props": {"style": "gate"},
     "data": {"label": "Go down the storm drain", "target": "drains", "spawn": "storm_drain",
              "lock": _lock(1, code_flag="code_storm_drain")}},
    {"kind": "exit", "id": "outfall", "at": (191.6, 98.5), "facing_deg": 270, "props": {"style": "grate"},
     "data": {"label": "Crawl into the outfall", "target": "drains", "spawn": "outfall", "lock": _lock(1)}},
    {"kind": "exit", "id": "scrapyard_road", "at": (170, 168.8), "facing_deg": 0, "props": {"style": "none", "size": "6,1.5"},
     "data": {"label": "Scrapyard Road", "target": "yard", "spawn": "checkpoint"}},
    {"kind": "exit", "id": "freight_tunnel", "at": (125, 165.4), "facing_deg": 0, "props": {"style": "panel"},
     "data": {"label": "Into the freight tunnel", "target": "yard", "spawn": "rail_gate",
              "lock": _lock(1, kind="device", pick=False, hack=True)}},
    {"kind": "exit", "id": "lift_up", "at": (128.6, 107), "facing_deg": 90, "props": {"style": "panel"},
     "data": {"label": "Take the service lift up", "target": "hub", "spawn": "lift_top",
              "lock": _lock(1, kind="device", pick=False, hack=True)}},
    {"kind": "exit", "id": "lift_down", "at": (125.5, viaduct_y(125.5) - 1.5), "facing_deg": 270,
     "z": "service_deck", "props": {"style": "panel"},
     "data": {"label": "Take the service lift down", "target": "hub", "spawn": "lift_bottom"}},
]

DOORS = [
    {"kind": "door", "id": "anchor_backroom", "at": (100, 53), "facing_deg": 270, "props": {"width": 1.4},
     "data": {"lock": _BARRED, "owner": "residents"}},
    {"kind": "door", "id": "anchor_back_door", "at": (112, 60), "facing_deg": 90, "props": {"width": 1.4},
     "data": {"lock": _lock(1), "owner": "residents"}},
    {"kind": "door", "id": "kessler_office", "at": (144, 56), "facing_deg": 0, "props": {"width": 1.4},
     "data": {"lock": _lock(2), "owner": "residents"}},
    {"kind": "door", "id": "clinic_pharmacy", "at": (168, 54), "facing_deg": 0, "props": {"width": 1.4},
     "data": {"lock": _lock(1, hack=True), "owner": "residents"}},
    {"kind": "door", "id": "records_door", "at": (232, 131), "facing_deg": 270, "props": {"width": 1.4},
     "data": {"lock": _lock(2, hack=True), "owner": "mersec"}},
    {"kind": "door", "id": "checkpoint_barrier", "at": (169.5, 157.8), "facing_deg": 0,
     "props": {"width": 9, "style": "barrier"}, "data": {"lock": _BARRED, "owner": "mersec"}},
]

LOOT = [
    {"kind": "loot", "id": "rooftop_stash", "at": (62, 18), "facing_deg": 180, "z": "roof", "props": {"model": "stash_box"},
     "data": {"noun": "stash", "items": ["neural_chip", "credit_chip:4"]}},
    {"kind": "loot", "id": "girder_cache", "at": (64, viaduct_y(64) - 2), "facing_deg": 90, "z": "service_deck",
     "props": {"model": "tool_box"}, "data": {"noun": "tool box", "items": ["data_shard", "stim", "ammo_10mm:12"]}},
    # on the Cut's bed under the Tin Bridge (owner, survey I5): a dive, with 45 s of breath
    {"kind": "loot", "id": "drowned_locker", "at": (203, 62.5), "z": -4.5, "facing_deg": 0, "props": {"model": "locker"},
     "data": {"noun": "locker", "items": ["whisper", "ammo_10mm:10"], "lock": _lock(1)}},
    {"kind": "loot", "id": "offering_box", "at": (95.5, 136.6), "facing_deg": 180, "props": {"model": "offering_box"},
     "data": {"noun": "offering box", "items": ["credit_chip:5"], "owner": "residents", "lock": _lock(2)}},
    {"kind": "loot", "id": "kessler_safe", "at": (146.8, 60.2), "facing_deg": 270, "props": {"model": "safe"},
     "data": {"noun": "safe", "items": ["credit_chip:16", "data_shard"], "owner": "residents",
              "lock": _lock(3, kind="safe")}},
    {"kind": "loot", "id": "pharmacy_shelf", "at": (170.5, 60.2), "facing_deg": 0, "props": {"model": "shelf"},
     "data": {"noun": "shelf", "items": ["medkit:2", "stim:2"], "owner": "residents"}},
    {"kind": "loot", "id": "depot_lockers", "at": (235.5, 106.2), "facing_deg": 180, "props": {"model": "locker"},
     "data": {"noun": "locker", "items": ["sanitation_overalls", "sanitation_cap", "sanitation_mask"],
              "owner": "sanitation"}},
    {"kind": "loot", "id": "anchor_store", "at": (106, 60), "facing_deg": 180, "props": {"model": "crate"},
     "data": {"noun": "crate", "items": ["synth_whisky:2", "noodles:2"], "owner": "residents"}},
    {"kind": "loot", "id": "garage_toolbox", "at": (174, 114.6), "facing_deg": 180, "props": {"model": "tool_box"},
     "data": {"noun": "tool box", "items": ["multitool", "scrap_electronics:2"], "owner": "scrap_kings"}},
    {"kind": "loot", "id": "stacks_crate", "at": (12, 127.5), "facing_deg": 180, "props": {"model": "crate"},
     "data": {"noun": "crate", "items": ["lockpick:2", "noodles"]}},
    {"kind": "loot", "id": "freight_crate", "at": (122, 149), "facing_deg": 90, "props": {"model": "crate"},
     "data": {"noun": "crate", "items": ["scrap_electronics:3", "ammo_darts:4"], "lock": _lock(1)}},
]

ITEMS = [
    {"kind": "item", "id": "pit_ammo", "at": (28, 152), "facing_deg": 0, "props": {}, "data": "ammo_10mm:12"},
    {"kind": "item", "id": "gutter_chip", "at": (6, 130.5), "facing_deg": 0, "props": {}, "data": "credit_chip"},
    {"kind": "item", "id": "ferry_scrap", "at": (229, 50), "facing_deg": 0, "props": {}, "data": "scrap_electronics:2"},
    {"kind": "item", "id": "yard_stim", "at": (117, 149), "facing_deg": 0, "props": {}, "data": "stim"},
    {"kind": "item", "id": "roof_noise", "at": (22, 88), "facing_deg": 0, "z": "roof", "props": {}, "data": "noise_maker:2"},
]

TERMINALS = [
    {"kind": "terminal", "id": "capsule_terminal", "at": (52.2, 25.4), "facing_deg": 180, "props": {},
     "data": {"title": "GOLDEN CARP: CAPSULE 12", "pages": [
         {"from": "Silk", "subject": "Welcome to the Sump",
          "body": "You made it down. Good. I have work, and it pays. The Rusty Anchor, on Lantern Row: "
                  "back room. Tank watches the door; tell him Silk sent for you, or don't, and see how "
                  "far that gets you.\n\nBuy what you need first. Kessler has hardware. Doc Vo patches holes."},
         {"from": "Golden Carp management", "subject": "House rules",
          "body": "Capsule 12 is yours while the rent clears. The locker is yours. The corridor is not. "
                  "No cooking. No weapons drawn in the lobby. MerSec does not come in here, and neither "
                  "do their problems."}],
              "on_read": [{"start_quest": "t0_arrival"}]}},
    {"kind": "terminal", "id": "kessler_terminal", "at": (141.2, 57.5), "facing_deg": 180, "props": {},
     "data": {"title": "KESSLER'S PAWN: OFFICE", "owner": "residents", "lock": _lock(1, kind="device", pick=False, hack=True),
              "pages": [
                  {"from": "Kessler", "subject": "Safe",
                   "body": "Moved the float to the office safe. If anybody's lifting the till again, it isn't "
                           "getting past a tier three. Remind me to stop telling Mags things."},
                  {"from": "Jax", "subject": "Re: the pistol order",
                   "body": "Crusher wants twelve. Put them on the account. He'll pay when the nav core sells."}]}},
    {"kind": "terminal", "id": "depot_terminal", "at": (227, 117.2), "facing_deg": 0, "props": {},
     "data": {"title": "CITY SANITATION: DEPOT 4", "owner": "sanitation", "pages": [
         {"from": "Depot manager", "subject": "Missing crew",
          "body": "Two of ours went into the pump station on Tuesday and didn't come back up. The Rats are "
                  "asking for money. The city is asking for patience. Service key's with Petra; nobody "
                  "else goes down."},
         {"from": "Maintenance", "subject": "Crawl vent",
          "body": "Break room vent in the pump station is loose again. Somebody keeps using it as a door."}],
              "on_read": [{"flag": "knows_crawl_vent"}]}},
    {"kind": "terminal", "id": "precinct_records", "at": (238.1, 131), "facing_deg": 270, "props": {},
     "data": {"title": "MERSEC PRECINCT 9: RECORDS", "owner": "mersec",
              "lock": _lock(2, kind="device", pick=False, hack=True), "pages": [
                  {"from": "Sgt. Dace", "subject": "Checkpoint ledger (private)",
                   "body": "Scrap Kings, weekly: 400. Kings, crates waved through: 12. Street debts "
                           "outstanding: Mouse (Tin Stacks), 300. Note to self: purge before audit."},
                  {"from": "Precinct 9 duty desk", "subject": "Standing orders",
                   "body": "Weapons drawn on Lantern Row or the market: one warning. Shots fired: "
                           "respond with force. Checkpoint traffic is at the sergeant's discretion."}],
              "on_read": [{"flag": "dace_evidence"}, {"objective": "s3_mouses_debt/evidence"}]}},
]

ZONES = [
    {"kind": "zone", "id": "checkpoint", "at": (179, 157), "facing_deg": 0, "props": {"size": "14,18"},
     "data": {"faction": "mersec", "name": "MerSec checkpoint", "allow": [{"flag": "dace_waves"}]}},
    # The depot's front desk is public (Petra works there); its lockers and manager's office aren't.
    {"kind": "zone", "id": "depot_back", "at": (235.5, 108), "facing_deg": 0, "props": {"size": "9,8"},
     "data": {"faction": "sanitation", "name": "the depot lockers"}},
    {"kind": "zone", "id": "depot_office", "at": (227, 117), "facing_deg": 0, "props": {"size": "8,10"},
     "data": {"faction": "sanitation", "name": "the depot office"}},
    # Sanitation overalls get you in to "check the drains" (design section 6).
    {"kind": "zone", "id": "precinct", "at": (232, 134), "facing_deg": 0, "props": {"size": "16,12"},
     "data": {"faction": "mersec", "name": "Precinct 9", "allow": [{"outfit": "sanitation"}]}},
    {"kind": "zone", "id": "station_gates", "at": (123, 9), "facing_deg": 0, "props": {"size": "34,10"},
     "data": {"faction": "mersec", "name": "the station gates"}},
]

TRIGGERS = [
    {"kind": "trigger", "id": "station_sealed", "at": (120, 16), "facing_deg": 0, "props": {"size": "12,3"},
     "data": {"once": False, "do": [{"say": "The gates are sealed. The board says the line reopens soon."}]}},
    {"kind": "trigger", "id": "found_roof_run", "at": (34, 98), "facing_deg": 0, "z": "roof", "props": {"size": "4,4"},
     "data": {"do": [{"say": "The roof run: fire escapes all the way to Lantern Row."},
                     {"xp": 50, "source": "hub:found_roof_run"}]}},
    {"kind": "trigger", "id": "found_girder_cache", "at": (66, viaduct_y(66) - 2), "facing_deg": 0,
     "z": "service_deck", "props": {"size": "4,3"},
     "data": {"do": [{"xp": 50, "source": "hub:found_girder_cache"}]}},
]

FURNITURE = [
    {"kind": "bed", "id": "capsule_12", "at": (52.2, 23.2), "facing_deg": 180, "props": {}},
    {"kind": "stash", "id": "capsule_locker", "at": (47, 29.8), "facing_deg": 180, "props": {}},
]

ENTITIES = NPCS + CIVILIANS + SPAWNS + EXITS + DOORS + LOOT + ITEMS + TERMINALS + ZONES + TRIGGERS + FURNITURE

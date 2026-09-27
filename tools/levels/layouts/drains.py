"""The Drains: Drain Rats territory under the Sump (mission M1, Rat Trap). Metres, x east, y south.

Single source for the level's plan (CLAUDE.md 7.1). Levels: -1 tunnels and halls (the plan),
-2 the flooded bypass (dashed water), +1 the camp catwalk ring and Mother Rat's nest (cyan).
The design is openspec/changes/the-drains.
"""
import math

W, H = 160, 110


def octagon(cx, cy, r):
    return [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i)))
            for i in range(8)]


PILLARS = [(x, y) for x in (80, 94, 108, 122) for y in (72, 84, 96) if not (90 <= x <= 112 and 76 <= y <= 90)]

MAP = {
    "id": "drains",
    "title": "THE DRAINS",
    "subtitle": "M1 RAT TRAP  ·  UNDER THE SUMP  ·  160 x 110 m",
    "blurb": [
        "Brick collectors, a flooded bypass and an overflow cistern the Drain Rats",
        "turned into a camp. Two sanitation workers are caged in the pump station.",
        "Levels: -1 tunnels (plan), -2 flooded bypass (dashed), +1 catwalks and nest (cyan).",
    ],
    "size": (W, H),
    "scale_px": 8,
    "seed": 11,
    "base": "rock",
    "legend_width": 560,
    "min_height": 1080,

    "open": [
        {"name": "STORM DRAIN STAIRS", "poly": [(6, 2), (14, 2), (14, 20), (6, 20)]},
        {"name": "COLLECTOR TUNNEL", "poly": [(34, 21), (106, 21), (106, 35), (34, 35)]},
        {"name": "alcove", "poly": [(50, 16), (56, 16), (56, 21), (50, 21)]},
        {"name": "alcove", "poly": [(80, 35), (86, 35), (86, 40), (80, 40)]},
        {"name": "THE JUNCTION", "poly": octagon(116, 42, 13)},
        {"name": "south run", "poly": [(112, 53), (120, 53), (120, 66), (112, 66)]},
        {"name": "east run", "poly": [(127, 37), (140, 37), (140, 45), (127, 45)]},
        {"name": "SLUICE ROOM", "poly": [(140, 28), (156, 28), (156, 54), (140, 54)]},
        {"name": "outfall", "poly": [(156, 38), (160, 38), (160, 45), (156, 45)]},
        {"name": "RAT CAMP", "poly": [(70, 66), (132, 66), (132, 102), (70, 102)]},
        {"name": "link", "poly": [(62, 78), (70, 78), (70, 86), (62, 86)]},
        {"name": "PUMP STATION", "poly": [(18, 58), (62, 58), (62, 104), (18, 104)]},
        {"name": "crack", "poly": [(86.5, 14), (89, 14), (89, 21), (86.5, 21)]},
        {"name": "DROWNED CHAPEL", "poly": [(76, 3), (98, 3), (98, 14), (76, 14)]},
    ],
    # doorways where a tunnel meets a building's rooms
    "wall_gaps": [(10, 20, 4), (34, 25, 1.8)],

    "water": [
        {"name": "", "poly": [(34, 26), (104, 26), (104, 30), (34, 30)]},              # collector channel
        {"name": "", "poly": octagon(116, 42, 4.5)},                                   # junction sump
        {"name": "", "poly": [(90, 76), (112, 76), (112, 90), (90, 90)]},              # cistern pool
        {"name": "", "poly": [(146, 28), (150, 28), (150, 54), (146, 54)]},            # sluice channel
        {"name": "", "poly": [(40, 92), (58, 92), (58, 102), (40, 102)]},              # pump sump
        {"name": "", "poly": [(79, 8), (86, 8), (86, 13), (79, 13)]},                  # chapel font
        # the flooded bypass, one level down
        {"name": "", "lower": True, "w": 3, "pts": [(66, 35), (66, 50), (96, 50), (98, 76)]},
        {"name": "", "lower": True, "w": 3, "pts": [(143, 54), (143, 60), (126, 62), (112, 78)]},
    ],

    "buildings": [
        {"id": "maintenance", "name": "SANITATION\nMAINTENANCE", "poly": [(6, 20), (34, 20), (34, 41), (6, 41)],
         "label_at": (20, 44.5),
         "rooms": [{"name": "LANDING", "rect": (6, 20, 20, 30)}, {"name": "LOCKERS", "rect": (20, 20, 34, 30)},
                   {"name": "BREAK ROOM", "rect": (6, 30, 18, 41)}, {"name": "OFFICE", "rect": (18, 30, 34, 41)}],
         "doors": [(10, 20, 4), (20, 25), (12, 30), (26, 30), (34, 25, 1.8)],
         "fixtures": [("rect", 21, 21, 33, 22.2, "fix"), ("rect", 28, 36, 33, 37.5, "fix-lt"),
                      ("rect", 8, 36, 12, 39, "fix"), ("rect", 13, 32, 16, 34, "fix-dark")]},
    ],

    "bridges": [
        ("rect", 58, 25, 62, 31, "bridge"), ("rect", 90, 25, 94, 31, "bridge"),
        ("rect", 145, 40, 151, 43, "bridge"),
    ],

    "props": (
        [("line", [(7, 4 + i * 1.6), (13, 4 + i * 1.6)], "stairs") for i in range(10)] +
        # camp: pillars, tents, fires, shacks, crates
        [("rect", x - 1, y - 1, x + 1, y + 1, "pillar") for x, y in PILLARS] +
        [("orect", x, y, 3.4, 2.6, a, "stall") for x, y, a in
         [(76, 70, 5), (76, 76, -8), (84, 92, 12), (88, 98, 0), (98, 96, -6), (118, 70, 4), (126, 76, 90), (126, 90, 80), (116, 98, 8)]] +
        [("circle", x, y, 0.9, "fix-hot") for x, y in [(86, 72), (100, 70), (120, 84), (80, 88)]] +
        [("rect", 72, 80, 80, 86, "fix"), ("rect", 122, 94, 130, 100, "fix"),        # shacks
         ("rect", 102, 68, 108, 70.5, "fix-lt"),                                      # Old Wick's counter
         ("rect", 124, 67, 130, 70, "crate")] +                                       # whisky crates (S4)
        # junction checkpoint: barricade, tripwire
        [("orect", 116, 57, 8, 1.2, 0, "fix-lt"), ("line", [(112.5, 61), (119.5, 61)], "trip"),
         ("line", [(40, 34.5), (44, 34.5)], "trip"), ("line", [(70.5, 88), (70.5, 94)], "trip")] +
        # pump station: pumps, pipes, the cage, stairs to the nest
        [("circle", x, 80, 4.5, "pump") for x in (28, 40, 52)] +
        [("line", [(x, 75.5), (x, 70)], "pipe") for x in (28, 40, 52)] +
        [("line", [(20, 70), (60, 70)], "pipe")] +
        [("rect", 21, 88, 33, 99, "cage")] +
        [("line", [(47 + i * 1.2, 60), (47 + i * 1.2, 68)], "stairs") for i in range(8)] +
        # sluice gates and terminal, chapel altar, maintenance lockers
        [("rect", 145, 34, 151, 35, "fix-hot"), ("rect", 145, 47, 151, 48, "fix-hot"),
         ("rect", 152, 30, 155, 32, "fix-cyan"), ("rect", 90, 4, 96, 6, "fix-hot"),
         ("rect", 138, 66, 140, 68, "fix-dark")]
    ),

    "elevated": [
        {"kind": "catwalk", "name": "Camp catwalk ring (+6 m)", "w": 2.2,
         "pts": [(72.5, 68.5), (129.5, 68.5), (129.5, 99.5), (72.5, 99.5), (72.5, 68.5)]},
        {"kind": "catwalk", "name": "Mother Rat's nest, mezzanine (+5 m)",
         "poly": [(19, 59), (46, 59), (46, 69), (19, 69)]},
        {"kind": "walkway", "name": "Junction ladder to the catwalk ring", "pts": [(105, 44), (106, 60), (110, 67.5)]},
        {"kind": "vent", "name": "Crawl vent: break room to the pump station (one way, a 3 m drop)",
         "pts": [(12, 35), (12, 50), (24, 54), (30, 58.5), (34, 64)]},
        {"kind": "vent", "name": "Vent branch to the nest", "pts": [(24, 54), (22, 58.5)]},
    ],

    "restricted": [
        {"name": "Mother Rat's nest", "shape": ("rect", 19, 59, 46, 69)},
        {"name": "Hostage cage", "shape": ("rect", 19.5, 86.5, 34.5, 100.5)},
    ],

    "cameras": [
        {"at": (116, 59), "dir": -90, "fov": 50, "range": 14, "name": "Scrap turret (Hacking 2 turns it)"},
    ],

    "patrols": [
        {"who": "Rat scavenger, collector walkways", "closed": True,
         "pts": [(40, 32.5), (102, 32.5), (102, 23.5), (40, 23.5)]},
        {"who": "Rat lookout, camp catwalk ring", "closed": True,
         "pts": [(73, 69), (129, 69), (129, 99), (73, 99)]},
        {"who": "Rat gunner, pump station", "closed": True,
         "pts": [(38, 92), (58, 88), (58, 64), (38, 86)]},
    ],

    "enemies": [
        {"at": (70, 32.5), "dir": 0, "kind": "grunt", "label": "Rat scavenger (I1), pipe"},
        {"at": (113.5, 55), "dir": -90, "kind": "grunt", "label": "Rat gunner (I2), checkpoint"},
        {"at": (118.5, 55), "dir": -90, "kind": "grunt", "label": "Rat gunner (I2), checkpoint"},
        {"at": (116, 60), "dir": -90, "kind": "turret", "label": "Scrap turret (Hacking 2)"},
        {"at": (126, 42), "dir": 180, "kind": "lookout", "label": "Rat lookout (I1), whistle"},
        {"at": (100, 72), "dir": 90, "kind": "grunt", "label": "Rat at the fire (I1)"},
        {"at": (84, 95), "dir": 0, "kind": "grunt", "label": "Rat asleep (I1)", "tag": "zzz"},
        {"at": (124, 88), "dir": 180, "kind": "grunt", "label": "Rat asleep (I1)", "tag": "zzz"},
        {"at": (105, 71), "dir": 90, "kind": "civ", "label": "Old Wick, Rat trader (I2): trades with anyone"},
        {"at": (78, 72), "dir": 0, "kind": "civ", "label": "Lug, Skiv's cousin (I1): talkable"},
        {"at": (120, 69), "dir": 180, "kind": "lookout", "label": "Rat lookout on the catwalk (I2)"},
        {"at": (36, 86), "dir": 180, "kind": "heavy", "label": "Twitch (I3), SMG: executes a hostage on alarm", "tag": "TWITCH"},
        {"at": (50, 90), "dir": 180, "kind": "grunt", "label": "Rat gunner (I2)"},
        {"at": (30, 63), "dir": 90, "kind": "boss", "label": "Mother Rat (I4), shotgun and gas", "tag": "MOTHER RAT"},
        {"at": (42, 64), "dir": 180, "kind": "heavy", "label": "Hatchet, bodyguard (I3)"},
        {"at": (25, 92), "dir": 0, "kind": "hostage", "label": "Tomas Petrov, sanitation worker"},
        {"at": (28, 95.5), "dir": 0, "kind": "hostage", "label": "Anil Das, sanitation worker"},
    ],

    "routes": [
        {"type": "force", "name": "Force: through the checkpoint and the camp",
         "pts": [(10, 6), (10, 24), (30, 24.5), (100, 24.5), (112, 36), (116, 50), (116, 64), (100, 94), (68, 83), (44, 88)]},
        {"type": "social", "name": "Social: Rat disguise, talk past the checkpoint, then Twitch or Mother Rat",
         "pts": [(12, 26), (33, 25.5), (104, 33), (120, 48), (119, 65), (88, 76), (66, 80), (38, 82)]},
        {"type": "stealth", "name": "Stealth: the flooded bypass, or the crawl vent",
         "pts": [(64, 36), (64, 48), (94, 48), (96, 74)]},
    ],

    "labels": [
        {"text": "up to the Pit (hub)", "at": (10, 1.6), "cls": "lbl-note"},
        {"text": "to the hub's canal outfall", "at": (152, 36.5), "cls": "lbl-note"},
        {"text": "FLOODED BYPASS  (level -2, swim 35 s, or drain it at the sluice)", "at": (80, 53.2), "cls": "lbl-note"},
        {"text": "CHECKPOINT", "at": (107, 58.5), "cls": "lbl-warn", "rot": -90},
        {"text": "NEST (+5 m)", "at": (26, 61.3), "cls": "lbl-note"},
        {"text": "HOSTAGE CAGE", "at": (27, 86.8), "cls": "lbl-warn"},
        {"text": "RAT CAMP", "at": (101, 104.8), "cls": "lbl-district"},
        {"text": "PUMP STATION", "at": (40, 55.4), "cls": "lbl-district"},
        {"text": "COLLECTOR TUNNEL", "at": (70, 19.2), "cls": "lbl-street"},
        {"text": "THE JUNCTION", "at": (116, 27.5), "cls": "lbl-street"},
        {"text": "SLUICE ROOM", "at": (148, 26.6), "cls": "lbl-street"},
        {"text": "DROWNED CHAPEL", "at": (87, 1.8), "cls": "lbl-street"},
        {"text": "cistern pool", "at": (101, 84), "cls": "lbl-note"},
        {"text": "pump sump", "at": (49, 98), "cls": "lbl-note"},
    ],

    "pois": [
        {"n": 1, "cat": "objective", "at": (37, 95), "name": "The hostages", "note": "Tomas and Anil, in the cage"},
        {"n": 2, "cat": "objective", "at": (34, 66), "name": "Mother Rat", "note": "pump room key on her desk; talk, pay or fight"},
        {"n": 3, "cat": "access", "at": (4, 12), "name": "Storm drain stairs", "note": "from the Pit; the way out with the hostages"},
        {"n": 4, "cat": "access", "at": (37, 22.5), "name": "Service door", "note": "sewer service key (Petra) or Lockpicking 2"},
        {"n": 5, "cat": "access", "at": (9, 33), "name": "Crawl vent", "note": "break room ceiling to the pump station"},
        {"n": 6, "cat": "access", "at": (66, 38.5), "name": "Overflow pipe", "note": "into the flooded bypass"},
        {"n": 7, "cat": "access", "at": (102, 46), "name": "Junction ladder", "note": "up to the camp catwalk ring"},
        {"n": 8, "cat": "access", "at": (157, 48), "name": "Outfall tunnel", "note": "from the hub canal (grate, Lockpicking 1)"},
        {"n": 9, "cat": "lock", "at": (30.5, 38.5), "name": "Maintenance terminal", "note": "sewer map; the Rats' password"},
        {"n": 10, "cat": "lock", "at": (153.5, 34), "name": "Sluice terminal", "note": "Hacking 1: drain the bypass"},
        {"n": 11, "cat": "lock", "at": (122, 60), "name": "Scrap turret", "note": "Hacking 2: turn it on the checkpoint"},
        {"n": 12, "cat": "lock", "at": (35, 91), "name": "Cage lock", "note": "pump room key or Lockpicking 2"},
        {"n": 13, "cat": "lock", "at": (21, 62), "name": "Mother Rat's safe", "note": "Lockpicking 3, or the code (nest terminal)"},
        {"n": 14, "cat": "lock", "at": (43, 61.5), "name": "Nest terminal", "note": "Hacking 2: safe code, ransom emails"},
        {"n": 15, "cat": "loot", "at": (24, 23.5), "name": "Sanitation locker", "note": "overalls and cap: City Sanitation disguise"},
        {"n": 16, "cat": "loot", "at": (76, 83), "name": "Rat stash", "note": "respirator and goggles: the full Rat outfit"},
        {"n": 17, "cat": "loot", "at": (127, 72.5), "name": "Whisky crates", "note": "S4 Last Call: tag them or carry one out"},
        {"n": 18, "cat": "loot", "at": (53, 18.5), "name": "Alcove", "note": "medkit, 10mm rounds"},
        {"n": 19, "cat": "contact", "at": (78, 75.5), "name": "Lug", "note": "Skiv's cousin; talks if you name Skiv"},
        {"n": 20, "cat": "contact", "at": (105, 74.5), "name": "Old Wick", "note": "Rat trader; sells to the disguised"},
        {"n": 21, "cat": "contact", "at": (40, 83), "name": "Twitch", "note": "I3; [Deception 2] 'Mother says let them go'"},
        {"n": 22, "cat": "secret", "at": (88, 9.5), "name": "Drowned Chapel", "note": "through the crack; data shard, neural chip"},
        {"n": 23, "cat": "secret", "at": (131, 66.5), "name": "Catwalk cache", "note": "frag grenade, stim"},
        {"n": 24, "cat": "security", "at": (110, 62.5), "name": "Tripwire", "note": "can rattle: noise 18 m; step over or cut"},
        {"n": 25, "cat": "security", "at": (41.5, 37), "name": "Tripwire", "note": "shotgun trap: Hacking 1 or multitool"},
    ],

    "missions": [
        {"code": "M1", "name": "Free the hostages", "kind": "Rat Trap", "at": (12, 94), "anchor": (22, 93)},
        {"code": "X", "name": "Get them out", "kind": "the stairs or the outfall", "at": (22, 8), "anchor": (14, 8),
         "colour": "#f2b33d"},
        {"code": "B", "name": "Mother Rat's safe", "kind": "bonus", "at": (8, 64), "anchor": (19.5, 62)},
        {"code": "S4", "name": "Last Call", "kind": "Mags' whisky", "at": (138, 76), "anchor": (130, 70)},
    ],

    "key": ["route-force", "route-social", "route-stealth", "patrol", "enemy", "boss", "turret", "hostage",
            "civ", "cone", "catwalk", "vent", "walkway", "water", "water-lower", "trip", "cage", "restricted"],
}

"""Scrap King's Yard: the Scrap Kings' junkyard and chop shop (mission M2, Chop Job).

Metres, x east, y south, 180 x 130 m. Single source for the level's plan (CLAUDE.md 7.1).
Levels: 0 the yard (plan), +4 the office mezzanine, +8 the container stack catwalk,
+18 the crane boom. The design is openspec/changes/scrap-kings-yard.
"""
import random

W, H = 180, 130
FENCE = (8, 8, 172, 114)          # x0, y0, x1, y1


def car_stacks():
    """Rows of crushed-car stacks in the west yard, one to three cars high."""
    rng = random.Random("yard-cars")
    out = []
    for row, y in enumerate(range(16, 86, 7)):
        x = 14.0
        while x < 50:
            if (row, int(x)) in ((6, 14),):          # the aisle behind the fence gap
                x += 6
                continue
            w = rng.uniform(4.2, 5.2)
            h = rng.choice(("stack1", "stack2", "stack2", "stack3"))
            out.append(("orect", x + w / 2, y + rng.uniform(-0.4, 0.4), w, 2.3, rng.uniform(-6, 6), h))
            x += w + (rng.uniform(3.5, 5.0) if rng.random() < 0.25 else rng.uniform(0.4, 1.0))
    return out


def containers():
    """The container maze: 12 x 2.5 m boxes in a loose grid, some stacked two or three high."""
    rng = random.Random("yard-boxes")
    colours = ["#5b3a2e", "#2f4a5a", "#4a5a2f", "#6a5a2a", "#3a3f4a", "#6b2f2f"]
    out = []
    for gy in range(0, 7):
        for gx in range(0, 4):
            if rng.random() < 0.22:
                continue
            cx = 74 + gx * 13 + rng.uniform(-1, 1)
            cy = 44 + gy * 8 + rng.uniform(-0.8, 0.8)
            ang = 0 if rng.random() < 0.7 else 90
            if ang == 90 and gy == 6:
                ang = 0
            out.append((cx, cy, ang, rng.choice(colours), rng.choice((1, 1, 1, 2, 2, 3))))
    return out


BOXES = containers()

MAP = {
    "id": "yard",
    "title": "SCRAP KING'S YARD",
    "subtitle": "M2 CHOP JOB  ·  SCRAPYARD ROAD  ·  180 x 130 m",
    "blurb": [
        "The Scrap Kings' walled scrapyard and chop shop, at night. Searchlights sweep,",
        "robot dogs hunt by scent, and Crusher keeps the nav core in his office safe.",
        "Levels: 0 the yard, +4 office mezzanine, +8 container catwalk, +18 crane boom.",
    ],
    "size": (W, H),
    "scale_px": 7,
    "seed": 23,
    "base": "ground",
    "legend_width": 560,
    "min_height": 1080,

    "ground": [
        {"poly": [(FENCE[0], FENCE[1]), (FENCE[2], FENCE[1]), (FENCE[2], FENCE[3]), (FENCE[0], FENCE[3])],
         "fill": "#12171c"},
    ],
    "open": [
        {"name": "SCRAPYARD ROAD", "w": 9, "label": True, "label_offset": "22%", "pts": [(0, 123), (W, 123)]},
        {"name": "gate apron", "poly": [(84, 114), (100, 114), (100, 119), (84, 119)]},
        {"name": "rail siding", "w": 4, "pts": [(0, 100), (8, 100), (40, 98), (60, 96)]},
    ],

    "buildings": [
        {"id": "warehouse", "name": "CHOP SHOP", "poly": [(124, 12), (168, 12), (168, 48), (124, 48)],
         "label_at": (138, 44.6),
         "rooms": [{"name": "SHOP FLOOR", "rect": (124, 20, 168, 48), "label_at": (146, 36)},
                   {"name": "PAINT BOOTH", "rect": (124, 12, 136, 20)},
                   {"name": "PARTS", "rect": (136, 12, 150, 20)},
                   {"name": "STAIRS", "rect": (150, 12, 156, 20)},
                   {"name": "", "rect": (156, 12, 168, 20)}],
         "doors": [(146, 48, 10), (124, 40, 2), (130, 20, 2.5), (143, 20, 2.5), (153, 20, 2.5), (168, 16, 2), (162, 20, 2)],
         "fixtures": [("rect", 128 + i * 9, 24, 132 + i * 9, 30, "fix") for i in range(4)] +
                     [("orect", 130 + i * 9, 27, 2, 4.4, 0, "car") for i in range(4)] +
                     [("rect", 126, 42, 138, 46, "fix-lt"), ("rect", 137, 13, 149, 14.2, "fix"),
                      ("rect", 137, 17.5, 149, 18.7, "fix")] +
                     [("line", [(150.6 + i * 0.7, 13), (150.6 + i * 0.7, 19)], "stairs") for i in range(8)]},
        {"id": "gatehouse", "name": "GATEHOUSE", "poly": [(100, 104), (110, 104), (110, 114), (100, 114)],
         "label_at": (105, 102),
         "rooms": [{"name": "", "rect": (100, 104, 110, 114)}], "doors": [(100, 110, 1.6)],
         "fixtures": [("rect", 102, 105, 108, 106.2, "fix-cyan")]},
        {"id": "generator", "name": "GENERATOR\nSHED", "poly": [(150, 58), (166, 58), (166, 70), (150, 70)],
         "label_at": (158, 54.6),
         "rooms": [{"name": "", "rect": (150, 58, 166, 70)}], "doors": [(150, 64, 2)],
         "fixtures": [("rect", 153, 60, 163, 67, "fix-hot"), ("rect", 164, 60, 165.5, 62, "fix-cyan")]},
        {"id": "kennel", "name": "KENNEL", "poly": [(54, 50), (62, 50), (62, 58), (54, 58)],
         "label_at": (58, 48.3),
         "rooms": [{"name": "", "rect": (54, 50, 62, 58)}], "doors": [(62, 54, 3)],
         "fixtures": [("rect", 55, 51, 58, 54, "fix-cyan"), ("rect", 55, 54.5, 58, 57, "fix-cyan")]},
        {"id": "crusher", "name": "CAR CRUSHER", "poly": [(58, 12), (78, 12), (78, 24), (58, 24)],
         "label_at": (68, 10.2),
         "fixtures": [("rect", 61, 14, 75, 22, "fix-dark"), ("rect", 62, 15, 74, 21, "fix-hot")]},
    ],

    "props": (
        car_stacks() +
        # containers: a shadow box per extra height so stacks read taller
        [("orect", cx, cy, 12, 2.5, a, col) for cx, cy, a, col, n in BOXES] +
        # the three-high stack by the warehouse, the crane base
        [("orect", 116, 34, 12, 2.5, 90, "#5b3a2e"), ("orect", 119, 34, 12, 2.5, 90, "#2f4a5a"),
         ("orect", 116, 34, 11, 1.7, 90, "lid3"), ("orect", 119, 34, 11, 1.7, 90, "lid3"),
         ("rect", 74, 30, 82, 38, "fix-lt")] +
        # fuel tanks, transformer, trailers, fire pit, parked trucks
        [("circle", x, y, 2.6, "pump") for x, y in [(155, 77), (162, 77), (155, 84), (162, 84)]] +
        [("rect", 166, 74, 170, 80, "fix-cyan")] +
        [("orect", 142 + (i % 3) * 11, 92 + (i // 3) * 10, 10, 3.6, (i % 2) * 6 - 3, "car") for i in range(5)] +
        [("circle", 150, 106, 1.1, "fix-hot"), ("rect", 154, 104, 158, 106, "crate")] +
        [("orect", 118 + i * 7, 108, 2.6, 7.5, 0, "car") for i in range(3)] +
        [("orect", 90, 106, 2.4, 6, 90, "car")] +
        # perimeter: corrugated wall north and east, chain-link west and south, the fence gap
        [("line", [(8, 8), (172, 8), (172, 114)], "wallsolid"),
         ("line", [(8, 8), (8, 86)], "fence"), ("line", [(8, 91), (8, 97.5)], "fence"),
         ("line", [(8, 102.5), (8, 114), (84, 114)], "fence"), ("line", [(100, 114), (172, 114)], "fence"),
         ("rect", 84, 113.6, 100, 114.4, "fix-hot"),                   # the gate
         ("rect", 7, 97.5, 9, 102.5, "fix-hot"),                       # rail gate
         ("line", [(0, 100), (60, 96)], "rail")] +
        # searchlight towers
        [("rect", x - 1.5, y - 1.5, x + 1.5, y + 1.5, "fix-lt") for x, y in [(60, 98), (120, 58), (30, 10.5)]]
    ),

    "elevated": [
        {"kind": "boom", "name": "Crane boom (+18 m): walk it to the container stack", "w": 2.2,
         "pts": [(78, 34), (112, 26)]},
        {"kind": "catwalk", "name": "Container stack catwalk (+8 m) to the skylight", "w": 1.8,
         "pts": [(117.5, 28), (124, 28), (140, 30)]},
        {"kind": "catwalk", "name": "Crusher's office, mezzanine (+4 m)",
         "poly": [(150, 20.5), (168, 20.5), (168, 32), (150, 32)]},
        {"kind": "walkway", "name": "Warehouse roof", "pts": [(124.5, 30), (140, 30), (146, 26)]},
    ],

    "restricted": [
        {"name": "Crusher's office", "shape": ("rect", 150, 20.5, 168, 32)},
        {"name": "Generator shed", "shape": ("rect", 149, 57, 167, 71)},
    ],

    "cameras": [
        {"at": (60, 98), "dir": -60, "fov": 34, "range": 30, "light": True, "name": "Searchlight (sweeps 120 deg)"},
        {"at": (120, 58), "dir": 150, "fov": 34, "range": 30, "light": True, "name": "Searchlight (sweeps 120 deg)"},
        {"at": (30, 10.5), "dir": 70, "fov": 34, "range": 30, "light": True, "name": "Searchlight (sweeps 120 deg)"},
        {"at": (124, 48), "dir": 135, "fov": 60, "range": 12, "name": "Warehouse camera"},
        {"at": (168, 48), "dir": 110, "fov": 60, "range": 12, "name": "Warehouse camera"},
        {"at": (100, 104), "dir": 200, "fov": 60, "range": 12, "name": "Gate camera"},
        {"at": (96, 111), "dir": -90, "fov": 50, "range": 14, "name": "Gate turret (Hacking 2)"},
    ],

    "patrols": [
        {"who": "Robot dog: through the car stacks", "closed": True,
         "pts": [(12, 12.5), (52, 12.5), (53, 33), (12, 33.5), (11, 54), (53, 54.5), (54, 75.5), (12, 75.5)]},
        {"who": "Robot dog: through the container maze", "closed": True,
         "pts": [(68, 40), (122, 40), (122, 60), (86, 60), (86, 76), (122, 76), (122, 98), (68, 98)]},
        {"who": "Kings foreman: generator, gate, warehouse", "closed": True,
         "pts": [(146, 64), (146, 100), (104, 100), (112, 52), (146, 52)]},
    ],

    "enemies": [
        {"at": (88, 110), "dir": 90, "kind": "grunt", "label": "Gate guard (I2)"},
        {"at": (97, 117), "dir": 90, "kind": "civ", "label": "Bolt, gate guard (I2): bribable, talkable"},
        {"at": (96, 111), "dir": -90, "kind": "turret", "label": "Gate turret (Hacking 2)"},
        {"at": (12, 50), "dir": 0, "kind": "dog", "label": "Robot dog: scent, can't be fooled by clothes"},
        {"at": (96, 96), "dir": 180, "kind": "dog", "label": "Robot dog: scent, can't be fooled by clothes"},
        {"at": (146, 76), "dir": 90, "kind": "heavy", "label": "Kings foreman (I3), shotgun, radio"},
        {"at": (132, 34), "dir": 0, "kind": "grunt", "label": "Kings mechanic (I2), wrench"},
        {"at": (150, 26), "dir": 180, "kind": "grunt", "label": "Kings mechanic (I2), SMG"},
        {"at": (160, 42), "dir": 180, "kind": "heavy", "label": "Bruiser (I2), exo-arm: EMP it"},
        {"at": (141, 40), "dir": -90, "kind": "civ", "label": "Dutch, mechanic (I2): hates Crusher"},
        {"at": (160, 26), "dir": 180, "kind": "boss", "label": "Crusher (I5), boss of the Scrap Kings", "tag": "CRUSHER"},
        {"at": (118, 30), "dir": 180, "kind": "lookout", "label": "Lookout on the stack (I2), rifle"},
        {"at": (146, 98), "dir": 0, "kind": "grunt", "label": "Off-duty King, asleep", "tag": "zzz"},
        {"at": (160, 108), "dir": 180, "kind": "grunt", "label": "Off-duty King at the fire (I1)"},
    ],

    "routes": [
        {"type": "social", "name": "Social: gang pass, a Kings vest, or a bribe at the gate; talk Crusher into opening the safe",
         "pts": [(60, 121), (92, 118), (92, 104), (104, 90), (140, 56), (146, 49), (154, 34), (158, 28)]},
        {"type": "stealth", "name": "Stealth: the fence gap, the car stacks, the containers, the stack and the skylight",
         "pts": [(2, 88.5), (12, 88.5), (30, 86), (56, 66), (68, 44), (100, 38), (116, 36), (118, 29), (138, 29), (152, 27)]},
        {"type": "tech", "name": "Tech: in by the rail gate, kill the generator, the back door",
         "pts": [(2, 100), (40, 97), (100, 92), (140, 70), (150, 64), (170, 52), (170, 18), (168, 16)]},
        {"type": "force", "name": "Force: through the gate and the roll-up door",
         "pts": [(40, 125), (88, 121), (88, 100), (130, 76), (146, 50)]},
    ],

    "labels": [
        {"text": "CAR STACKS", "at": (32, 92.6), "cls": "lbl-district"},
        {"text": "CONTAINER MAZE", "at": (65.6, 70), "cls": "lbl-district", "rot": -90},
        {"text": "KINGS' BARRACKS", "at": (152, 88.2), "cls": "lbl-street"},
        {"text": "fuel tanks", "at": (158.5, 90), "cls": "lbl-note"},
        {"text": "fence gap", "at": (2, 85.8), "cls": "lbl-warn", "anchor": "start"},
        {"text": "rail gate", "at": (1, 104.4), "cls": "lbl-note", "anchor": "start"},
        {"text": "from Low Harbor (hub)", "at": (1, 119.4), "cls": "lbl-note", "anchor": "start"},
        {"text": "from the freight tunnel", "at": (1, 96.2), "cls": "lbl-note", "anchor": "start"},
        {"text": "CRANE", "at": (78, 41), "cls": "lbl-street"},
        {"text": "OFFICE (+4 m)", "at": (159, 31), "cls": "lbl-note"},
        {"text": "skylight", "at": (140, 34.2), "cls": "lbl-note"},
    ],

    "pois": [
        {"n": 1, "cat": "objective", "at": (166, 23), "name": "The nav core", "note": "in Crusher's office safe"},
        {"n": 2, "cat": "objective", "at": (156, 30), "name": "Crusher", "note": "S1 Kingmaker: kill, expose, or leave him"},
        {"n": 3, "cat": "objective", "at": (152, 23), "name": "The ledger", "note": "S2: on his desk; Hacking 3 for the copy"},
        {"n": 4, "cat": "access", "at": (80, 111), "name": "Front gate", "note": "gang pass, a Kings vest (I2), or 150 cr"},
        {"n": 5, "cat": "access", "at": (4, 91.5), "name": "Fence gap", "note": "crouch; behind the car stacks"},
        {"n": 6, "cat": "access", "at": (12, 104), "name": "Rail gate", "note": "from the freight tunnel; Hacking 1"},
        {"n": 7, "cat": "access", "at": (72, 40), "name": "Crane ladder", "note": "climb to the boom (+18 m)"},
        {"n": 8, "cat": "access", "at": (112, 30), "name": "Container stack", "note": "catwalk to the warehouse roof"},
        {"n": 9, "cat": "access", "at": (140, 26.5), "name": "Skylight", "note": "drop into the office; Lockpicking 1"},
        {"n": 10, "cat": "access", "at": (171, 12), "name": "Back door", "note": "Lockpicking 2, or Dutch opens it"},
        {"n": 11, "cat": "lock", "at": (160, 72.5), "name": "Generator", "note": "off: searchlights and the gate die; the foreman comes"},
        {"n": 12, "cat": "lock", "at": (100, 118), "name": "Gate turret", "note": "Hacking 2"},
        {"n": 13, "cat": "lock", "at": (166, 29), "name": "Crusher's safe", "note": "Lockpicking 3, the combination, or [Deception 4]"},
        {"n": 14, "cat": "lock", "at": (151.5, 29.5), "name": "Crusher's terminal", "note": "Hacking 3: the combination, the ledger"},
        {"n": 15, "cat": "lock", "at": (106, 108), "name": "Camera console", "note": "Hacking 1: loop the cameras"},
        {"n": 16, "cat": "loot", "at": (137, 102), "name": "Kings' lockers", "note": "vest, goggles and mask: Scrap Kings outfit"},
        {"n": 17, "cat": "loot", "at": (130, 16), "name": "Paint booth crate", "note": "shotgun, shells"},
        {"n": 18, "cat": "loot", "at": (153, 67), "name": "Shed shelf", "note": "EMP grenades x2"},
        {"n": 19, "cat": "contact", "at": (136, 40), "name": "Dutch", "note": "mechanic; turns on Crusher for 300 cr or [Persuasion 3]"},
        {"n": 20, "cat": "contact", "at": (102, 119), "name": "Bolt", "note": "gate guard; bribe or bluff"},
        {"n": 21, "cat": "secret", "at": (22, 54), "name": "Car trunk stash", "note": "neural chip, lockpicks"},
        {"n": 22, "cat": "secret", "at": (68, 20), "name": "The crusher's last load", "note": "a MerSec badge: evidence for S3"},
        {"n": 23, "cat": "security", "at": (58, 60.5), "name": "Kennel", "note": "Hacking 2 keeps the dogs docked"},
        {"n": 24, "cat": "security", "at": (123, 61), "name": "Searchlights", "note": "three towers; the generator runs them"},
    ],

    "missions": [
        {"code": "M2", "name": "Steal the nav core", "kind": "Chop Job", "at": (176, 32), "anchor": (167, 24)},
        {"code": "S1", "name": "Kingmaker", "kind": "Crusher", "at": (176, 42), "anchor": (160, 30)},
        {"code": "S2", "name": "The Ledger", "kind": "Petra", "at": (143, 6), "anchor": (152, 21)},
        {"code": "X", "name": "Get out", "kind": "any way in is a way out", "at": (22, 118), "anchor": (8, 100)},
    ],

    "key": ["route-social", "route-stealth", "route-tech", "route-force", "patrol", "enemy", "dog", "boss",
            "turret", "civ", "cone", "cone-light", "crane", "catwalk", "walkway", "wallsolid", "fence", "restricted"],
}

# containers stacked higher get a lighter lid so height reads on the plan
for cx, cy, a, col, n in BOXES:
    if n > 1:
        MAP["props"].append(("orect", cx, cy, 11, 1.7, a, f"lid{n}"))

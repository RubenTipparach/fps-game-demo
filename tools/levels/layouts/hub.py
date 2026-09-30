"""Low Harbor, the Sump: the Undercity hub. Metres, x east, y south, 240 x 170 m.

Single source for the hub's plan (CLAUDE.md 7.1): tools/levels/render_map.py draws it, and the
Blender build reads it. The design is openspec/changes/sump-market-hub.
"""

W, H = 240, 170


def viaduct_y(x):
    """Centreline of the Meridian Skyway viaduct, which crosses the hub north-west to south-east."""
    return 64 + 82 * x / W


# A car spot, length x width: the longest body the deal places (the full-size saloon, 5.22 m) and the
# widest (the minivan, 2.41 m with its mirrors), with room round them (openspec/changes/cc0-vehicles,
# design section 3.1).
CAR_L, CAR_W = 5.6, 2.6

MAP = {
    "id": "hub",
    "title": "LOW HARBOR",
    "subtitle": "THE SUMP  ·  HUB  ·  240 x 170 m",
    "blurb": [
        "The drowned bottom of Meridian, under the Skyway and the Halcyon Spire.",
        "Every NPC here can be talked to. Two exits lead to this slice's missions,",
        "each with more than one way through.",
    ],
    "size": (W, H),
    "scale_px": 6,
    "seed": 7,
    "base": "city",
    "legend_width": 540,

    # Streets, lanes and squares: everything you can walk at street level.
    "open": [
        {"name": "LANTERN ROW", "w": 9, "label": True, "label_offset": "16%",
         "pts": [(0, 40), (40, 39), (80, 38), (118, 37), (160, 38), (192, 41)]},
        {"name": "MARKET STREET", "w": 10, "label": True, "pts": [(118, 37), (119, 58), (121, 76)]},
        {"name": "CANAL WALK", "w": 6, "label": True, "label_offset": "30%",
         "pts": [(189, 12), (189, 60), (188, 100), (188, 140), (189, 170)]},
        {"name": "QUAY ROAD", "w": 7, "label": True, "label_offset": "62%", "pts": [(217.5, 10), (217.5, 170)]},
        {"name": "JOSS ALLEY", "w": 4, "label": True,
         "pts": [(86, 96), (68, 95), (56, 102), (44, 99), (30, 107), (14, 105), (0, 109)]},
        {"name": "WIRE LANE", "w": 3, "label": True, "pts": [(30, 40), (32, 64), (27, 86), (30, 107)]},
        {"name": "STAIR LANE", "w": 3, "pts": [(58, 40), (55, 62), (60, 80), (56, 102)]},
        {"name": "PIT LANE", "w": 3.5, "pts": [(30, 107), (34, 126), (38, 140)]},
        {"name": "GUTTER ROW", "w": 3, "label": True, "pts": [(0, 131), (18, 129), (34, 126)]},
        {"name": "DROP ALLEY", "w": 3, "pts": [(56, 102), (66, 120), (62, 138), (54, 146)]},
        {"name": "NEEDLE ALLEY", "w": 3, "label": True, "pts": [(55, 62), (66, 72), (84, 82)]},
        {"name": "INCENSE LANE", "w": 4, "pts": [(104, 116), (106, 128), (108, 138)]},
        {"name": "KILN STREET", "w": 8, "label": True,
         "pts": [(152, 110), (160, 132), (167, 152), (170, 170)]},
        {"name": "ROPE WALK", "w": 5, "label": True, "pts": [(158, 130), (174, 129.5), (188, 129)]},
        {"name": "CLINIC LANE", "w": 4, "pts": [(121, 68), (150, 68), (170, 68), (188, 67)]},
        {"name": "FREIGHT LANE", "w": 5, "pts": [(132, 116), (133, 132), (134, 148)]},
        {"name": "rail", "w": 5, "pts": [(186, 142), (170, 145), (150, 152), (132, 162), (124, 170)]},
        {"name": "SUMP MARKET", "poly": [(86, 76), (118, 74), (150, 72), (162, 94), (152, 116),
                                         (120, 118), (98, 118), (82, 102)]},
        {"name": "STATION FORECOURT", "poly": [(102, 29), (138, 29), (138, 36), (102, 36)]},
        {"name": "THE PIT", "label": True, "label_at": (40, 138.6), "floor_m": -2.5,
         "poly": [(26, 138), (52, 136), (58, 152), (46, 164), (26, 162), (20, 150)]},
        {"name": "SHRINE COURT", "poly": [(98, 136), (120, 134), (122, 150), (100, 152)]},
        {"name": "KILN FREIGHT YARD", "label": True, "label_at": (136, 167.5),
         "poly": [(114, 148), (156, 146), (162, 170), (112, 170)]},
        {"name": "DEPOT YARD", "poly": [(222, 72), (240, 72), (240, 103), (222, 103)]},
        {"name": "DRYDOCK APRON", "poly": [(221, 62), (240, 62), (240, 70), (221, 70)]},
    ],

    "water": [
        {"id": "the_cut", "name": "THE CUT", "label_at": (203.5, 112), "rot": 90, "surface_m": -2.2, "bed_m": -4.5,
         "poly": [(194, 10), (213.5, 10), (214, 60), (213, 100), (214, 170), (193, 170), (192, 120), (193, 60)]},
        {"id": "dry_dock", "name": "", "poly": [(223, 20), (239, 20), (239, 60), (223, 60)], "surface_m": -2.2, "bed_m": -6.0},  # dry dock basin
        {"id": "dock_gate", "name": "", "poly": [(213, 36), (224, 36), (224, 44), (213, 44)], "surface_m": -2.2, "bed_m": -4.5},  # dock gate channel
    ],

    "districts": [
        {"name": "SPIRE FOUNDATIONS", "poly": [(0, 0), (W, 0), (W, 13), (0, 13)], "lot": (500, 1300), "style": "foundation", "height_m": (40, 40),
         "label_at": (60, 8.5), "shade": ["#161c23", "#181f27"], "roof_n": 1},
        {"name": "LANTERN ROW", "poly": [(0, 13), (192, 13), (192, 70), (60, 70), (60, 44), (0, 44)],
         "lot": (60, 190), "style": "strip", "height_m": (9, 22), "label_at": (152, 40.3), "roof_n": 3},
        {"name": "TIN STACKS", "poly": [(0, 44), (60, 44), (60, 70), (84, 82), (84, 118), (96, 120), (90, 170), (0, 170)],
         "lot": (22, 70), "jitter": 9, "style": "shanty", "height_m": (5, 14), "label_at": (18, 82), "rot": -90, "roof_n": 2},
        {"name": "SUMP MARKET", "poly": [(84, 70), (192, 70), (192, 116), (96, 120), (84, 118)],
         "lot": (55, 170), "style": "market", "height_m": (8, 16), "label_at": (118, 88.5)},
        {"name": "KILN", "poly": [(96, 120), (192, 116), (192, 170), (90, 170)], "lot": (60, 190), "style": "workshop", "height_m": (6, 11),
         "court_min": 170, "court_p": 0.35, "label_at": (146, 140.5), "rot": 0},
        {"name": "DRYDOCK", "poly": [(213, 10), (W, 10), (W, H), (213, H)], "lot": (100, 320), "style": "dock", "height_m": (8, 14),
         "court_min": 240, "court_p": 0.3, "label_at": (229.5, 152), "rot": -90},
    ],

    # Named buildings. Rooms make a floor plan (enterable); fixtures are furniture and machines.
    # Meridian's towers around the slum (openspec/changes/archive/2026-09-29-hub-skyline): scenery beyond the hub's
    # edges, drawn by the skyline sector and the map's locator inset. Layout metres like the rest,
    # so towers sit at negative or beyond-edge coordinates. "style" picks the massing (spire,
    # arcology, slab, corporate, civic, cluster), "crown" the top (halo, neon, billboard, beacons),
    # "lit" the share of windows lit, "neon" the crown's colour role. The near ring is named; the
    # far ring is silhouettes 400-900 m out. city_plan.py asserts the bounds, the horizon's
    # coverage, no overlaps and the triangle budget. "searchlights" (owner I8) are beams off the
    # tower's faces at height_m, each sweeping one turn per period_s (negative: the other way)
    # from phase_deg, tilted between tilt_deg's two angles from vertical.
    "skyline": [
        {"id": "halcyon_spire", "name": "HALCYON SPIRE", "at": (170, -70), "size": (100, 80), "height_m": 440,
         "style": "spire", "crown": "halo", "neon": "cyan", "lit": 0.35, "setbacks_m": [120, 260, 380],
         "searchlights": {"height_m": 420, "tilt_deg": (20, 35),
                          "beams": [{"face": "west", "period_s": 47.0, "phase_deg": 0.0},
                                    {"face": "east", "period_s": -61.0, "phase_deg": 180.0}]}},
        {"id": "castellan_arcology", "name": "CASTELLAN ARCOLOGY", "at": (40, -60), "size": (90, 70), "height_m": 260,
         "style": "arcology", "crown": "neon", "neon": "magenta", "lit": 0.3},
        {"id": "kosei_stacks", "name": "KOSEI STACKS", "at": (-60, 60), "size": (40, 120), "height_m": 150,
         "style": "slab", "crown": "beacons", "lit": 0.55},
        {"id": "harrow_tower", "name": "HARROW TOWER", "at": (-70, 150), "size": (50, 50), "height_m": 230,
         "style": "corporate", "crown": "billboard", "neon": "amber", "lit": 0.3},
        {"id": "the_pylons", "name": "THE PYLONS", "at": (20, 258), "size": (50, 50), "height_m": 260,
         "style": "cluster", "crown": "beacons", "lit": 0.25,
         "parts": [{"at": (5, 245), "size": (20, 20), "height_m": 260}, {"at": (35, 255), "size": (20, 20), "height_m": 190},
                   {"at": (20, 275), "size": (20, 20), "height_m": 220}]},
        {"id": "sable_mutual", "name": "SABLE MUTUAL", "at": (120, 240), "size": (60, 40), "height_m": 320,
         "style": "corporate", "crown": "neon", "neon": "cyan", "lit": 0.3},
        {"id": "pier_nine", "name": "PIER NINE ARCOLOGY", "at": (310, 180), "size": (80, 80), "height_m": 210,
         "style": "arcology", "crown": "neon", "neon": "amber", "lit": 0.35},
        {"id": "water_authority", "name": "MERIDIAN WATER AUTHORITY", "at": (300, 40), "size": (60, 60), "height_m": 180,
         "style": "civic", "crown": "neon", "neon": "blue", "lit": 0.25},
        # the near ring's gaps
        {"id": "stack_ne", "at": (275, -45), "size": (40, 40), "height_m": 160, "style": "slab", "crown": "beacons", "lit": 0.4},
        {"id": "stack_se", "at": (215, 235), "size": (40, 40), "height_m": 140, "style": "slab", "lit": 0.45},
        {"id": "stack_w", "at": (-55, -25), "size": (40, 40), "height_m": 170, "style": "slab", "crown": "beacons", "lit": 0.4},
        {"id": "stack_sw", "at": (-60, 235), "size": (40, 40), "height_m": 130, "style": "slab", "lit": 0.45},
        # the far ring
        {"id": "far_01", "at": (772, 133), "size": (70, 60), "height_m": 590, "style": "corporate", "lit": 0.18, "ring": "far"},
        {"id": "far_02", "at": (584, 194), "size": (100, 80), "height_m": 640, "style": "slab", "lit": 0.19, "ring": "far"},
        {"id": "far_03", "at": (775, 649), "size": (70, 70), "height_m": 270, "style": "spire", "lit": 0.22, "ring": "far"},
        {"id": "far_04", "at": (600, 791), "size": (70, 100), "height_m": 220, "style": "slab", "lit": 0.26, "ring": "far"},
        {"id": "far_05", "at": (281, 656), "size": (60, 100), "height_m": 200, "style": "corporate", "lit": 0.35, "ring": "far"},
        {"id": "far_06", "at": (146, 748), "size": (80, 70), "height_m": 200, "style": "corporate", "lit": 0.17, "ring": "far"},
        {"id": "far_07", "at": (-76, 614), "size": (90, 60), "height_m": 330, "style": "slab", "lit": 0.26, "ring": "far"},
        {"id": "far_08", "at": (-310, 674), "size": (80, 60), "height_m": 560, "style": "slab", "lit": 0.21, "ring": "far"},
        {"id": "far_09", "at": (-493, 544), "size": (60, 70), "height_m": 570, "style": "slab", "lit": 0.34, "ring": "far"},
        {"id": "far_10", "at": (-411, 222), "size": (80, 90), "height_m": 220, "style": "arcology", "lit": 0.2, "ring": "far"},
        {"id": "far_11", "at": (-565, 64), "size": (90, 100), "height_m": 270, "style": "corporate", "lit": 0.24, "ring": "far"},
        {"id": "far_12", "at": (-564, -138), "size": (90, 60), "height_m": 550, "style": "arcology", "lit": 0.23, "ring": "far"},
        {"id": "far_13", "at": (-377, -319), "size": (80, 70), "height_m": 360, "style": "spire", "lit": 0.16, "ring": "far"},
        {"id": "far_14", "at": (-308, -636), "size": (80, 60), "height_m": 440, "style": "corporate", "lit": 0.34, "ring": "far"},
        {"id": "far_15", "at": (-131, -679), "size": (90, 90), "height_m": 510, "style": "corporate", "lit": 0.28, "ring": "far"},
        {"id": "far_16", "at": (65, -671), "size": (70, 80), "height_m": 550, "style": "corporate", "lit": 0.21, "ring": "far"},
        {"id": "far_17", "at": (335, -726), "size": (60, 90), "height_m": 610, "style": "slab", "lit": 0.16, "ring": "far"},
        {"id": "far_18", "at": (418, -382), "size": (60, 100), "height_m": 360, "style": "corporate", "lit": 0.18, "ring": "far"},
        {"id": "far_19", "at": (595, -310), "size": (80, 70), "height_m": 350, "style": "corporate", "lit": 0.32, "ring": "far"},
        {"id": "far_20", "at": (878, -207), "size": (100, 90), "height_m": 430, "style": "spire", "lit": 0.22, "ring": "far"},
    ],
    "buildings": [
        {"id": "station", "name": "LOW HARBOR STATION", "poly": [(100, 5), (140, 5), (140, 29), (100, 29)], "height_m": 16,
         "label_at": (120, 2.6),
         "rooms": [{"name": "CONCOURSE", "rect": (100, 14, 140, 29)},
                   {"name": "SEALED GATES", "rect": (108, 5, 132, 14)},
                   {"name": "MERSEC POST", "rect": (132, 5, 140, 14)},
                   {"name": "TICKETS", "rect": (100, 5, 108, 14)}],
         "doors": [(114, 29, 4), (126, 29, 4), (120, 14, 6), (136, 14), (104, 14)],
         "fixtures": [("rect", 110, 9, 130, 10, "fix-cyan"), ("rect", 103, 20, 106, 26, "fix"),
                      ("rect", 134, 20, 137, 26, "fix")]},
        {"id": "golden_carp", "name": "GOLDEN CARP\nCAPSULES", "poly": [(40, 15), (66, 15), (66, 34), (40, 34)], "height_m": 9,
         "label_at": (53, 20),
         "rooms": [{"name": "LOBBY", "rect": (40, 26, 58, 34)}, {"name": "STAIRS", "rect": (58, 26, 66, 34)},
                   {"name": "", "rect": (40, 15, 66, 26)}],
         "doors": [(50, 34, 3), (58, 30), (53, 26, 3)],
         "fixtures": [("rect", 42 + i * 3, 16, 44.4 + i * 3, 19.5, "fix") for i in range(8)] +
                     [("rect", 42 + i * 3, 21.5, 44.4 + i * 3, 25, "fix") for i in range(8)] +
                     [("rect", 42, 29, 48, 30.2, "fix-lt")]},
        # The three shells have one room each (owner K3, openspec/changes/hub-doorways, design section 3.7).
        {"id": "neon_koi", "name": "NEON KOI\nKARAOKE", "poly": [(72, 15), (94, 15), (94, 33), (72, 33)], "height_m": 12,
         "rooms": [{"name": "LOBBY", "rect": (72, 23, 94, 33)}], "doors": [(83, 33, 3)],
         "fixtures": [("rect", 73, 32, 93, 32.6, "fix-band"), ("rect", 74, 25, 80, 26.2, "fix-lt"),
                      ("circle", 85, 27, 1.2, "fix"), ("circle", 90, 27, 1.2, "fix"),
                      ("rect", 76, 23.3, 90, 23.5, "fix-neon")]},
        {"id": "pachinko", "name": "PACHINKO\nSUNRISE", "poly": [(150, 15), (176, 15), (176, 33), (150, 33)], "height_m": 14,
         "rooms": [{"name": "FLOOR", "rect": (150, 21, 176, 33)}], "doors": [(162.5, 33, 3)],
         "fixtures": [("rect", 151, 32.2, 175, 32.8, "fix-band")] +
                     [("rect", 153 + i * 2.2, y, 154 + i * 2.2, y + 0.7, "fix-cyan") for y in (24, 28) for i in range(10)]},
        {"id": "rusty_anchor", "name": "THE RUSTY ANCHOR", "poly": [(68, 44), (112, 44), (112, 70), (68, 70)], "height_m": 10,
         "label_at": (84, 73.4),
         "rooms": [{"name": "MAIN HALL", "rect": (68, 50, 100, 70), "label_at": (88, 64.5)},
                   {"name": "VESTIBULE", "rect": (84, 44, 96, 50)},
                   {"name": "COATS", "rect": (68, 44, 84, 50)},
                   {"name": "BACK ROOM", "rect": (100, 44, 112, 56)},
                   {"name": "STORE", "rect": (100, 56, 112, 64)},
                   {"name": "WC", "rect": (100, 64, 112, 70)}],
         "doors": [(90, 44, 3), (90, 50, 3), (100, 53), (106, 56), (112, 60), (100, 67), (68, 65), (80, 50)],
         # The bar's short leg stops at x 98.5, leaving Tank a 1.4 m aisle to the wall: at 1.1 m the
         # navmesh (agent 0.4 m) lost it once the back room's door was framed beside it.
         "fixtures": [("rect", 84, 52, 98, 54, "fix-lt"), ("rect", 97, 52, 98.5, 58, "fix-lt"),
                      ("rect", 69, 56, 76, 66, "fix"), ("circle", 80, 58, 1.1, "fix"), ("circle", 86, 60, 1.1, "fix"),
                      ("circle", 92, 62, 1.1, "fix"), ("circle", 80, 66, 1.1, "fix"), ("circle", 88, 67, 1.1, "fix"),
                      ("rect", 102, 46, 110, 49, "fix"), ("rect", 69, 51, 70, 69, "fix-neon"),
                      ("rect", 102, 58, 110, 59.5, "fix"), ("rect", 102, 61, 110, 62.5, "fix")]},
        {"id": "kessler", "name": "KESSLER'S PAWN", "poly": [(128, 44), (148, 44), (148, 62), (128, 62)], "height_m": 9.5,
         "label_at": (138, 52.5),
         "rooms": [{"name": "SHOP", "rect": (128, 44, 148, 56), "label_at": (138, 48.5)},
                   {"name": "STOCK", "rect": (128, 56, 140, 62)}, {"name": "OFFICE", "rect": (140, 56, 148, 62)}],
         "doors": [(138, 44, 3), (134, 56), (144, 56), (128, 59)],
         "fixtures": [("rect", 131, 53, 145, 54.4, "fix-lt"), ("rect", 129, 45, 130, 52, "fix"),
                      ("rect", 146, 45, 147, 52, "fix"), ("rect", 146, 59, 147.5, 61.5, "fix-hot")]},
        {"id": "clinic", "name": "DOC VO'S CLINIC", "poly": [(154, 44), (176, 44), (176, 62), (154, 62)], "height_m": 11,
         "label_at": (165, 55.5),
         "rooms": [{"name": "WAITING", "rect": (154, 44, 164, 52)}, {"name": "SURGERY", "rect": (164, 44, 176, 54)},
                   {"name": "RECOVERY", "rect": (154, 52, 164, 62)}, {"name": "PHARMACY", "rect": (164, 54, 176, 62)}],
         "doors": [(159, 44, 3), (164, 48), (159, 52), (168, 54), (176, 58)],
         "fixtures": [("rect", 168, 47, 173, 49, "fix-lt"), ("rect", 156, 55, 158, 60, "fix"),
                      ("rect", 160, 55, 162, 60, "fix"), ("rect", 166, 60, 175, 61.2, "fix")]},
        {"id": "fish_hall", "name": "HARBOR\nFISH HALL", "poly": [(164, 76), (184, 76), (184, 112), (164, 112)], "height_m": 11,
         "label_at": (174, 80),
         "rooms": [{"name": "", "rect": (164, 76, 184, 112)}],
         "doors": [(174, 76, 4), (164, 94, 4), (184, 104, 3), (164, 108)],
         "fixtures": [("rect", 167 + (i % 3) * 5.5, 84 + (i // 3) * 6, 170.5 + (i % 3) * 5.5, 87 + (i // 3) * 6, "stall")
                      for i in range(12)]},
        {"id": "depot", "leaves": "steel", "name": "CITY SANITATION\nDEPOT", "poly": [(223, 104), (240, 104), (240, 122), (223, 122)], "height_m": 8.5,
         "label_at": (231.5, 126),
         "rooms": [{"name": "FRONT DESK", "rect": (223, 104, 231, 112)}, {"name": "LOCKERS", "rect": (231, 104, 240, 112)},
                   {"name": "MANAGER", "rect": (223, 112, 231, 122)}, {"name": "BAY", "rect": (231, 112, 240, 122)}],
         "doors": [(223, 108, 2), (231, 108), (227, 112), (235.5, 104, 4), (231, 117)],
         "fixtures": [("rect", 232, 106, 239, 107, "fix"), ("rect", 225, 116, 229, 118, "fix-lt")]},
        {"id": "garage", "leaves": "hazard", "name": "KINGS' GARAGE", "poly": [(162, 113), (184, 113), (184, 126), (162, 126)], "height_m": 7.5,
         "label_at": (171, 116.2),
         "rooms": [{"name": "", "rect": (162, 113, 178, 126)}, {"name": "OFFICE", "rect": (178, 113, 184, 126)}],
         "doors": [(162, 119, 5), (178, 120)],
         "fixtures": [("orect", 170, 119.5, CAR_L, CAR_W, 90, "car"), ("rect", 165, 114, 175, 115, "fix")]},
        {"id": "shrine", "name": "TSANG SHRINE", "poly": [(86, 134), (98, 134), (98, 150), (86, 150)], "height_m": 7,
         "frame_style": "shrine",
         "label_at": (92, 131.5),
         "rooms": [{"name": "HALL", "rect": (86, 138, 98, 150)}, {"name": "", "rect": (86, 134, 98, 138)}],
         "doors": [(98, 144, 2.5), (92, 138, 2)],
         "fixtures": [("rect", 89, 135, 95, 136.5, "fix-hot"), ("circle", 92, 146, 1.2, "fix-hot")]},
        {"id": "checkpoint", "leaves": "steel", "name": "MERSEC\nCHECKPOINT", "poly": [(174, 150), (184, 150), (184, 164), (174, 164)], "height_m": 4.5,
         "label_at": (190.5, 158), "rot": -90,
         # the door stands south of the boom, which meets the wall at y 157.4-158.2 (openspec/changes/hub-doorways)
         "rooms": [{"name": "", "rect": (174, 150, 184, 164)}], "doors": [(174, 154, 2)],
         "fixtures": [("rect", 176, 152, 182, 153.2, "fix-lt")]},
        {"id": "precinct", "leaves": "steel", "name": "PRECINCT 9", "poly": [(224, 128), (240, 128), (240, 140), (224, 140)], "height_m": 9,
         "label_at": (232, 125.2),
         "rooms": [{"name": "FRONT DESK", "rect": (224, 128, 232, 140)}, {"name": "RECORDS", "rect": (232, 128, 240, 134)},
                   {"name": "CELLS", "rect": (232, 134, 240, 140)}],
         "doors": [(224, 134, 2), (232, 131), (232, 137)],
         "fixtures": [("rect", 226, 130, 230, 131.2, "fix-lt"), ("rect", 238.2, 129, 239.6, 133, "fix-cyan")]},
        {"id": "mouse_den", "name": "", "label": False, "poly": [(36, 111), (46, 111), (46, 120), (36, 120)], "height_m": 5,
         "rooms": [{"name": "MOUSE'S DEN", "rect": (36, 111, 46, 120)}], "doors": [(36, 115, 1.4)]},
        {"id": "laundromat", "name": "BUBBLE\nWASH", "poly": [(4, 46), (24, 46), (24, 58), (4, 58)], "height_m": 7,
         "rooms": [{"name": "", "rect": (4, 46, 24, 58)}], "doors": [(17.5, 46, 3)],    # between the parked cars
         "fixtures": [("rect", 6 + i * 1.6, 56.3, 7.2 + i * 1.6, 57.5, "fix") for i in range(10)] +
                     [("rect", 8, 50.5, 16, 51.3, "fix")]},
        {"id": "ferry", "name": "MV ANSELM", "label_at": (231, 40), "rot": -90,
         "poly": [(226, 24), (236, 24), (237, 46), (231, 57), (225, 46)]},
    ],

    # Kept clear of lots: the station's service yard behind the pachinko, the stair to the Skyway.
    "keep_clear": [],

    "bridges": [
        ("rect", 191, 60, 216, 64.5, "bridge"),                 # Tin Bridge
        ("rect", 191, 136, 216, 146, "bridge"),                 # Freight Bridge
        ("rect", 212, 37, 225, 43, "bridge"),                   # dock gate swing bridge
    ],

    "props": (
        # Sump Market stalls, in rows between the Skyway's pillars
        [("orect", 92 + (i % 5) * 6.5, 84 + (i // 5) * 7, 3.2, 2.2, -4 + (i % 3) * 3, "stall") for i in range(10)] +
        [("orect", 128 + (i % 3) * 6.5, 104 + (i // 3) * 6, 3.2, 2.2, 3 - (i % 2) * 5, "stall") for i in range(6)] +
        [("rect", 103, 96.5, 110, 99.5, "fix-hot"),              # Nguyen's noodle bar
         ("rect", 138.5, 98.5, 141.5, 101.5, "fix-cyan"),        # Oracle kiosk
         ("circle", 120, 96, 3.5, "fix-dark"),                   # drain well under the viaduct
         ("rect", 125, 105, 128, 108.5, "fix-lt")] +             # Skyway service lift
        # parked cars on Lantern Row's road, each spot's long side 0.2 m off the kerb where the kerb
        # comes nearest (the pavement strips are irregular), on its south side and on its north
        # (openspec/changes/vehicle-fixes, design section 1.3; survey O2), and none in front of
        # Pachinko Sunrise's entrance (openspec/changes/hub-doorways)
        [("orect", x, y, CAR_L, CAR_W, 0, "car") for x, y in ((12, 40.99), (23.5, 40.65), (35, 40.41), (46.5, 40.07))] +
        [("orect", x, y, CAR_L, CAR_W, 0, "car") for x, y in ((150, 36.5), (168, 37.65))] +
        # on Quay Road, 0.2 m off the quay's raised edge at x 214.0
        [("orect", 215.5, 80 + i * 8, CAR_W, CAR_L, 0, "car") for i in range(5)] +
        # the depot yard's spots take what every car spot deals, the vans among it (survey O7)
        [("orect", 228, 80 + i * 7, CAR_L, CAR_W, 0, "car") for i in range(3)] +
        # freight wagons on the siding, crates in the freight yard
        [("orect", 140 - i * 13.5, 153 + i * 7.2, 12, 3, -28, "container") for i in range(2)] +
        [("rect", 116 + (i % 4) * 3.1, 150 + (i // 4) * 3.1, 118.6 + (i % 4) * 3.1, 152.6 + (i // 4) * 3.1, "crate") for i in range(8)] +
        # burn barrels and a moored boat
        [("circle", x, y, 0.8, "fix-hot") for x, y in [(33, 128), (44, 150), (51, 104), (22, 106)]] +
        [("poly", [(194, 80), (197.5, 78), (197.5, 90), (194, 88)], "fix"),
         ("poly", [(194, 116), (197.5, 114), (197.5, 124), (194, 122)], "fix"),
         # checkpoint barrier and jersey blocks
         ("rect", 165, 157.4, 174, 158.2, "fix-hot"),
         ("rect", 158, 161, 162, 162.2, "fix-lt"), ("rect", 176, 167, 182, 168.2, "fix-lt"),
         # storm drain mouth in the Pit, outfall grate in the canal wall
         ("rect", 36, 155, 44, 159, "fix-dark"), ("rect", 192.2, 96.5, 193.6, 100.5, "fix-dark"),
         # freight tunnel portal
         ("rect", 119, 166, 131, 170, "fix-dark")]
    ),

    "elevated": [
        {"kind": "viaduct", "name": "Meridian Skyway (14 m up)", "w": 16, "pillar_every": 26, "deck_m": 14,
         "pts": [(-4, viaduct_y(-4)), (W + 4, viaduct_y(W + 4))]},
        {"kind": "walkway", "name": "Skyway service deck", "hung": True, "z_m": 10.9, "pts": [(126, 106.5), (100, viaduct_y(100)), (60, viaduct_y(60))]},
        {"kind": "walkway", "name": "Roof run: fire escapes over the Tin Stacks",
         # walk heights per point: 5 cm above Mouse's den roof, then clear of the capped roofs to the Golden Carp's
         "z_m": [5.05, 9.05, 9.05, 9.05, 9.05, 9.05, 9.05],
         "pts": [(41, 115), (34, 98), (22, 88), (20, 70), (28, 52), (44, 40), (58, 22)]},
        {"kind": "walkway", "name": "Gallery over the market", "z_m": 4.5,
         "pts": [(104, 70), (112, 72), (128, 71.5), (150, 70), (160, 72)]},
    ],

    "restricted": [
        {"name": "MerSec checkpoint", "shape": ("rect", 172, 148, 186, 166)},
        {"name": "Depot lockers and manager", "shape": ("rect", 223, 104, 240, 122)},
        {"name": "Precinct 9", "shape": ("rect", 222, 126, 240, 142)},
        {"name": "Station gates", "shape": ("rect", 106, 4, 140, 14)},
    ],

    "cameras": [
        {"at": (132, 14), "dir": 120, "fov": 60, "range": 12, "name": "Station camera"},
        {"at": (108, 14), "dir": 60, "fov": 60, "range": 12, "name": "Station camera"},
        {"at": (174, 151), "dir": 200, "fov": 70, "range": 14, "name": "Checkpoint camera"},
        {"at": (184, 164), "dir": 110, "fov": 60, "range": 12, "name": "Checkpoint camera"},
        {"at": (129, 45), "dir": 40, "fov": 60, "range": 8, "name": "Kessler's shop camera"},
        {"at": (239, 73), "dir": 135, "fov": 60, "range": 14, "name": "Depot yard camera"},
    ],

    "patrols": [
        {"who": "MerSec pair: Lantern Row, Market Street, the market, Kiln Street",
         # every leg clear of buildings, stalls, the Skyway's pillars and the parked cars for an
         # NPC's capsule (city_plan.check_standing_room); the pair walks straight from stop to stop,
         # along Lantern Row's north half, clear of the cars at its south kerb (vehicle-fixes)
         "closed": True, "pts": [(40, 37.8), (118, 37), (120, 72), (146, 96), (156, 118), (166, 148),
                                 (158, 130), (156.5, 120.5), (150, 112), (126.5, 116.6), (100, 110), (84, 96),
                                 (86.7, 86), (85.5, 80.5), (79.5, 78.5), (64.5, 69), (56, 61.5), (56.5, 44),
                                 (56, 38.2)]},
    ],

    "enemies": [
        {"at": (171, 155), "dir": 180, "kind": "civ", "label": "Officer Dace (MerSec, I3)"},
        {"at": (168, 160), "dir": 90, "kind": "civ", "label": "MerSec trooper (I2)"},
        {"at": (120, 31), "dir": 90, "kind": "civ", "label": "MerSec trooper at the station (I2)"},
        {"at": (97.8, 55), "dir": 180, "kind": "civ", "label": "Tank, bouncer"},
    ],

    "routes": [
        {"type": "main", "name": "M1 Rat Trap: down the storm drain",
         "pts": [(90, 43), (84, 80), (70, 95), (56, 102), (44, 99), (31, 108), (34, 126), (40, 150)]},
        {"type": "stealth", "name": "M1 alternative: the canal outfall (Lockpicking 1)",
         "pts": [(186, 70), (187, 90), (193, 98)]},
        {"type": "social", "name": "M2 Chop Job: through the checkpoint (pass, bribe, talk or disguise)",
         "pts": [(152, 112), (160, 132), (167, 152), (170, 168)]},
        {"type": "stealth", "name": "M2 alternative: over the jersey blocks behind the checkpoint camera (no skill)",
         "pts": [(157, 136), (156, 152), (160, 161.5), (166, 168.5)]},
        {"type": "stealth", "name": "M2 alternative: the freight tunnel (Hacking 1 gate)",
         "pts": [(133, 118), (134, 146), (130, 160), (125, 168)]},
    ],

    "labels": [
        {"text": "Halcyon Spire foundation wall, 400 m of tower above", "at": (182, 8), "cls": "lbl-note"},
        {"text": "storm drain", "at": (40, 161.8), "cls": "lbl-note"},
        {"text": "outfall", "at": (197, 103.5), "cls": "lbl-note", "rot": -90},
        {"text": "TIN BRIDGE", "at": (203.5, 67), "cls": "lbl-street"},
        {"text": "FREIGHT BRIDGE", "at": (203.5, 149), "cls": "lbl-street"},
        {"text": "to SCRAPYARD ROAD", "at": (170, 169), "cls": "lbl-warn"},
        {"text": "freight tunnel", "at": (125, 164.5), "cls": "lbl-note"},
        {"text": "dry dock", "at": (231, 18), "cls": "lbl-note"},
    ],

    "pois": [
        # services
        {"n": 1, "cat": "service", "at": (94, 47), "name": "The Rusty Anchor", "note": "bar; Mags sells drinks and rumours"},
        {"n": 2, "cat": "service", "at": (138, 47.5), "name": "Kessler's Pawn", "note": "weapons, ammo, gear; buys loot"},
        {"n": 3, "cat": "service", "at": (159, 47.5), "name": "Doc Vo's Clinic", "note": "healing, medkits, stims"},
        {"n": 4, "cat": "service", "at": (106.5, 101.5), "name": "Nguyen's Noodle Bar", "note": "food; knows the drain gate code"},
        {"n": 5, "cat": "service", "at": (49, 30), "name": "Golden Carp Capsules", "note": "safehouse: capsule 12, stash locker, sleep"},
        {"n": 6, "cat": "service", "at": (170, 100), "name": "Harbor Fish Hall", "note": "night market; black-market stalls"},
        {"n": 7, "cat": "service", "at": (144, 100), "name": "Oracle kiosk", "note": "data broker; buys data shards"},
        # contacts
        {"n": 8, "cat": "contact", "at": (106, 51.5), "name": "Silk, the fixer", "note": "back room of the Anchor; gives M1 and M2"},
        {"n": 9, "cat": "contact", "at": (97.8, 55), "name": "Tank, the bouncer", "note": "guards the back room; Persuasion 2 or 50 cr"},
        {"n": 10, "cat": "contact", "at": (227, 107.5), "name": "Petra", "note": "sanitation worker; her brother is a hostage"},
        {"n": 11, "cat": "contact", "at": (167, 155), "name": "Officer Dace", "note": "runs the checkpoint; bribable"},
        {"n": 12, "cat": "contact", "at": (41, 117.5), "name": "Mouse", "note": "street kid; vents, rooftops, gossip"},
        {"n": 13, "cat": "contact", "at": (177.5, 96), "name": "Rivet", "note": "scavenger; sells a Drain Rats jacket"},
        {"n": 14, "cat": "contact", "at": (50, 146), "name": "Skiv", "note": "Drain Rats scout watching the Pit"},
        {"n": 15, "cat": "contact", "at": (181, 119.5), "name": "Jax", "note": "Scrap Kings recruiter; gang pass"},
        {"n": 16, "cat": "contact", "at": (90, 143), "name": "Sister Lin", "note": "shrine keeper; rumours, S3"},
        # access
        {"n": 17, "cat": "access", "at": (33, 157), "name": "Storm drain: The Drains", "note": "level exit to M1"},
        {"n": 18, "cat": "access", "at": (163.5, 166), "name": "Scrapyard Road: the Yard", "note": "level exit to M2, past the checkpoint"},
        {"n": 19, "cat": "access", "at": (120, 22), "name": "Low Harbor Station", "note": "sealed; the Upper City later"},
        {"n": 20, "cat": "access", "at": (131, 108), "name": "Skyway service lift", "note": "up to the service deck (Hacking 1)"},
        {"n": 21, "cat": "access", "at": (197.5, 94), "name": "Outfall grate", "note": "into the Drains' flooded bypass; Lockpicking 1"},
        {"n": 22, "cat": "access", "at": (117, 162), "name": "Freight tunnel gate", "note": "to the Yard's rail siding; Hacking 1"},
        {"n": 23, "cat": "access", "at": (16, 88), "name": "Roof run", "note": "fire escapes; Mouse shows the way"},
        # secrets
        {"n": 24, "cat": "secret", "at": (62, 18), "name": "Rooftop stash", "note": "neural chip; on the Golden Carp's roof"},
        {"n": 25, "cat": "secret", "at": (64, viaduct_y(64) - 2), "name": "Girder cache", "note": "end of the Skyway service deck"},
        {"n": 26, "cat": "secret", "at": (203, 62.5), "name": "Drowned locker", "note": "on the bed under the Tin Bridge; dive"},
        {"n": 27, "cat": "secret", "at": (95.5, 136), "name": "Offering box", "note": "shrine; Lockpicking 2"},
        # restricted
        {"n": 28, "cat": "restricted", "at": (236, 110), "name": "Depot lockers", "note": "sanitation overalls; workers only"},
        {"n": 29, "cat": "restricted", "at": (236, 131), "name": "Precinct 9", "note": "MerSec; evidence terminal, Hacking 2"},
    ],

    "missions": [
        {"code": "M1", "name": "Rat Trap", "kind": "hostage rescue", "at": (22, 146), "anchor": (38, 155),
         "note": "Silk: free two sanitation workers held in the Drains' pump station."},
        {"code": "M2", "name": "Chop Job", "kind": "robbery", "at": (156, 164), "anchor": (168, 164),
         "note": "Silk: steal the prototype nav core from the Scrap Kings' office safe."},
        {"code": "S1", "name": "Kingmaker", "kind": "assassination", "at": (192, 122.5), "anchor": (183, 121),
         "note": "Jax wants Crusher, the Scrap Kings' boss, dead. Or does he?"},
        {"code": "S2", "name": "The Ledger", "kind": "theft", "at": (218.5, 98), "anchor": (224, 106),
         "note": "Petra: the Kings' ledger names the MerSec officers on their payroll."},
        {"code": "S3", "name": "Mouse's Debt", "kind": "hub infiltration", "at": (27, 116), "anchor": (37, 116),
         "note": "Mouse owes Dace 300 cr. Pay, persuade, or take the evidence from Precinct 9."},
        {"code": "S4", "name": "Last Call", "kind": "retrieval", "at": (74, 76), "anchor": (80, 68),
         "note": "Mags: her whisky shipment went down the drain. The Rats are drinking it."},
        {"code": "U", "name": "Upper City", "kind": "later: towers, malls, parks", "at": (148, 22), "anchor": (140, 20),
         "colour": "#7d8e9e", "note": "The station reopens after the first slice."},
    ],

    "key": ["viaduct", "walkway", "route-main", "route-social", "route-stealth", "patrol", "cone",
            "restricted", "civ", "water", "ladder", "puddle"],
}

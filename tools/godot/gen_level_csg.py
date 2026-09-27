#!/usr/bin/env python3
"""E1M1 "Pump Station" - a level blocked out with Godot CSG nodes.

The level is built the way Unreal 1 / Quake levels were: start from a solid block of "rock"
and subtract rooms out of it, then add pillars, stairs, catwalks and trims as additive
brushes. Every brush is a plain CSGBox3D / CSGCylinder3D / CSGPolygon3D node in
level_csg.tscn under "CSGSource", so you can move and resize them in the Godot editor.

Then "compile" it like an old-school map: Project > Tools > "Brushfire: Bake CSG Level" turns
the CSG into a single UV-mapped mesh (world-aligned box projection, texel density from
materials.json), generates tangents and a lightmap UV2, and bakes a trimesh collider.
Finally bake the LightmapGI node.

    python3 tools/godot/gen_level_csg.py   # regenerates the scene (overwrites edits!)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detailing  # noqa: E402
import level_common as lc  # noqa: E402
from tscn import Raw, Scene, v2, v3  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "game")
UNION, INTERSECT, SUBTRACT = 0, 1, 2

s = Scene("LevelCSG", "Node3D")
lc.setup_root(s, "E1M1: Pump Station")


def mat(name):
    return s.ext_res("Material", f"res://materials/{name}.tres")


_count = {}


def _name(prefix):
    _count[prefix] = _count.get(prefix, 0) + 1
    return f"{prefix}{_count[prefix]}"


def box(parent, x, y, z, m, op=UNION, name=None):
    """Axis-aligned box brush from coordinate ranges."""
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
    return s.node(name or _name("Box"), "CSGBox3D", parent,
                  position=v3((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                  size=v3(x1 - x0, y1 - y0, z1 - z0), operation=op, material=mat(m))


def cyl(parent, x, z, y0, y1, r, m, op=UNION, sides=16, rot=None, name=None, pos=None):
    props = dict(position=v3(x, (y0 + y1) / 2, z) if pos is None else v3(*pos), radius=float(r),
                 height=float(y1 - y0), sides=sides, smooth_faces=True, operation=op, material=mat(m))
    if rot:
        props["rotation_degrees"] = v3(*rot)
    return s.node(name or _name("Cyl"), "CSGCylinder3D", parent, **props)


def ramp(parent, x, z, y_low, y_high, m, axis="z", name=None):
    """Wedge ramp: rises from y_low at the first end of `z` (or `x`) to y_high at the second."""
    (x0, x1), (z0, z1) = x, z
    if axis == "z":
        # polygon in the node's local XY plane, extruded along local Z (depth); rotate so the
        # profile lies in the ZY plane and extrudes along X.
        length = z1 - z0
        poly = [v2(0, y_low), v2(length, y_high), v2(length, y_low - 0.4), v2(0, y_low - 0.4)] \
            if y_high > y_low else [v2(0, y_low), v2(length, y_high), v2(length, y_high - 0.4), v2(0, y_high - 0.4)]
        return s.node(name or _name("Ramp"), "CSGPolygon3D", parent,
                      position=v3(x0, 0, z0), rotation_degrees=v3(0, -90, 0),
                      polygon=Raw("PackedVector2Array(" + ", ".join(p[8:-1] for p in poly) + ")"),
                      depth=float(x1 - x0), mode=0, operation=UNION, material=mat(m))
    raise ValueError(axis)


ROOMS = []  # air volumes, used for automatic UT99-style trims
STYLE = {"tech_panel": "tech", "concrete": "tech", "rust_metal": "tech", "brick_wall": "brick", "stone_blocks": "stone"}


def room(parent, name, x, z, h, walls, floor, ceiling, y0=0.0, trims=True):
    """Carve a room (walls take the carve's material) then add floor/ceiling slabs."""
    ROOMS.append(detailing.Room(name, x, (y0, y0 + h), z, STYLE.get(walls, "tech"), trims, ceiling=ceiling))
    box(parent, x, (y0 - 0.3, y0 + h + 0.3), z, walls, SUBTRACT, name=f"{name}_Carve")
    box(parent, x, (y0 - 0.35, y0), z, floor, name=f"{name}_Floor")
    box(parent, x, (y0 + h, y0 + h + 0.35), z, ceiling, name=f"{name}_Ceiling")


def opening(parent, name, x, y, z, m="tech_panel", floor="diamond_plate"):
    ROOMS.append(detailing.Room(name, x, y, z, trims=False))
    box(parent, x, (y[0] - 0.3, y[1]), z, m, SUBTRACT, name=f"{name}_Carve")
    box(parent, x, (y[0] - 0.35, y[0]), z, floor, name=f"{name}_Floor")


# ----------------------------------------------------------------------------- brushes

csg = s.node("CSGSource", "CSGCombiner3D", ".", groups=["csg_source", "editor_only"], visible=False,
             use_collision=False)
# The solid block everything is carved from.
box(csg, (-34, 20), (-1.5, 12), (-40, 46), "concrete", name="Rock")

# --- start room
room(csg, "Start", (-6, 6), (30, 42), 4.5, "tech_panel", "floor_tiles", "ceiling_tiles")
box(csg, (-6, -4), (0, 1), (39, 41), "crate", name="StartCrateA")
box(csg, (-5.5, -4.5), (1, 2), (39.5, 40.5), "crate", name="StartCrateB")
box(csg, (4, 5), (0, 1), (31, 32), "crate", name="StartCrateC")

# --- corridor A (start -> pump hall)
room(csg, "CorridorA", (-2, 2), (16.3, 30.01), 4.0, "brick_wall", "diamond_plate", "ceiling_tiles")
opening(csg, "DoorSouth", (-1.5, 1.5), (0, 3.2), (15.7, 16.4))

# --- pump hall
room(csg, "Hall", (-14, 14), (-14, 15.8), 10.0, "concrete", "concrete", "rust_metal")
# (baseboards, cornices, bands and pilasters are generated from the room list, see below)
# pumps
for i, (x, z) in enumerate(((-7, -6), (7, -6), (-7, 6), (7, 6))):
    cyl(csg, x, z, 0, 7.0, 1.4, "rust_metal", name=f"Pump{i}")
    cyl(csg, x, z, 7.0, 7.5, 1.65, "tech_panel", name=f"PumpCap{i}")
    cyl(csg, x, z, 0, 0.5, 1.7, "tech_panel", name=f"PumpBase{i}")
    # pipe from the cap into the ceiling
    cyl(csg, x, z, 7.5, 10.2, 0.45, "rust_metal", sides=12, name=f"PumpPipe{i}")
# horizontal pipes between pumps
cyl(csg, 0, -6, 0, 14, 0.35, "rust_metal", sides=12, rot=(0, 0, 90), pos=(0, 5.5, -6), name="PipeNorth")
cyl(csg, 0, 6, 0, 14, 0.35, "rust_metal", sides=12, rot=(0, 0, 90), pos=(0, 5.5, 6), name="PipeSouth")
# central platform with a ramp to the south
box(csg, (-4, 4), (0, 1.0), (-3, 3), "diamond_plate", name="Platform")
box(csg, (-4, 4), (0, 1.0), (-3.2, -3), "hazard_stripes", name="PlatformEdgeN")
ramp(csg, (-2, 2), (3, 7), 1.0, 0.0, "diamond_plate", name="PlatformRamp")
# east stairs up to the catwalk (10 steps of 0.4 m)
for i in range(10):
    top = 0.4 * (i + 1)
    z1 = 14 - 0.8 * i
    box(csg, (10, 14), (0, top), (z1 - 0.8, z1), "diamond_plate", name=f"Step{i}")
# catwalk
box(csg, (10, 14), (3.7, 4.0), (-14, 6), "diamond_plate", name="Catwalk")
box(csg, (9.85, 10.05), (4.0, 5.0), (-14, 6), "hazard_stripes", name="CatwalkRail")
for i, z in enumerate((-12, -6, 0)):
    box(csg, (10.1, 10.5), (0, 3.7), (z - 0.2, z + 0.2), "rust_metal", name=f"CatwalkPost{i}")

# openings out of the hall
opening(csg, "DoorNorth", (-1.5, 1.5), (0, 3.2), (-14.5, -13.9))
opening(csg, "ArchWest", (-14.5, -13.9), (0, 3.5), (0, 4), "tech_panel", "concrete")

# --- storage room (west)
room(csg, "Storage", (-26, -14.4), (-6, 10), 5.0, "brick_wall", "concrete", "ceiling_tiles")
box(csg, (-24, -23), (0, 1), (1, 2), "crate", name="CrateStepA")
box(csg, (-26, -24), (0, 2), (0, 2), "crate_large", name="CrateStepB")
box(csg, (-19, -17), (0, 2), (-5, -3), "crate_large", name="CrateC")
box(csg, (-18.5, -17.5), (2, 3), (-4.5, -3.5), "crate", name="CrateD")
box(csg, (-23, -21), (0, 2), (7, 9), "crate_large", name="CrateE")
box(csg, (-21, -20), (0, 1), (8, 9), "crate", name="CrateF")
box(csg, (-16, -15), (0, 1), (6, 7), "crate", name="CrateG")
# secret alcove, above the crates
room(csg, "Secret", (-29.5, -25.9), (0, 3), 2.2, "stone_blocks", "stone_blocks", "stone_blocks", y0=2.0, trims=False)

# --- corridor B (hall -> exit)
room(csg, "CorridorB", (-2, 2), (-26.01, -14.4), 4.0, "brick_wall", "diamond_plate", "ceiling_tiles")

# --- exit chamber
room(csg, "Exit", (-7, 7), (-38, -26), 6.0, "stone_blocks", "floor_tiles", "ceiling_tiles")
for i, (x, z) in enumerate(((-5.5, -36.5), (5.5, -36.5), (-5.5, -27.5), (5.5, -27.5))):
    # pillars always get a base and a capital (UT99 checklist item 3)
    box(csg, (x - 0.6, x + 0.6), (0, 6), (z - 0.6, z + 0.6), "tech_panel", name=f"ExitPillar{i}")
    box(csg, (x - 0.8, x + 0.8), (0, 0.6), (z - 0.8, z + 0.8), "stone_blocks", name=f"ExitPillarBase{i}")
    box(csg, (x - 0.78, x + 0.78), (5.55, 6), (z - 0.78, z + 0.78), "stone_blocks", name=f"ExitPillarCap{i}")
    box(csg, (x - 0.66, x + 0.66), (0.6, 0.75), (z - 0.66, z + 0.66), "rust_metal", name=f"ExitPillarRing{i}")
box(csg, (-2.5, 2.5), (0, 0.3), (-35.5, -30.5), "hazard_stripes", name="ExitDais")

# --- skylight: a shaft through the hall roof onto a Quake-style sky surface (UT99 checklist 6/15:
# a view onto the sky that doubles as the hall's landmark; cf. DM-Distinctive's central skylight)
box(csg, (-3, 3), (9.9, 11.7), (-3, 3), "rust_metal", SUBTRACT, name="SkylightShaft")
box(csg, (-3.01, 3.01), (11.6, 11.75), (-3.01, 3.01), "sky_night", name="SkylightSky")
for i, (x0, x1, z0, z1) in enumerate(((-3.4, 3.4, -3.4, -3.0), (-3.4, 3.4, 3.0, 3.4),
                                      (-3.4, -3.0, -3.0, 3.0), (3.0, 3.4, -3.0, 3.0))):
    box(csg, (x0, x1), (9.75, 10.0), (z0, z1), "hazard_stripes", name=f"SkylightFrame{i}")
for i, x in enumerate((-1.0, 1.0)):     # grate bars across the girders
    box(csg, (x - 0.08, x + 0.08), (9.8, 10.0), (-3, 3), "rust_metal", name=f"SkylightBar{i}")

# light fixtures (placed in the bays between the ceiling girders)
CEILING_LIGHTS = [(0, 4.43, 33), (0, 4.43, 39.5),                                  # start
                  (-7, 9.93, -7.6), (7, 9.93, -7.6), (-7, 9.93, 9.4), (7, 9.93, 9.4),  # hall
                  (-20, 4.93, -4), (-20, 4.93, 4),                                  # storage
                  (-3.5, 5.93, -32), (3.5, 5.93, -32)]                              # exit
WALL_LAMPS = [(-1.95, 3.0, 23, -90), (1.95, 3.0, 23, 90),         # corridor A
              (-13.95, 4.0, -8, -90), (-13.95, 4.0, 10, -90),     # hall west
              (13.95, 6.2, -10, 90), (13.95, 6.2, -2, 90),        # catwalk
              (-1.95, 3.0, -20, -90), (1.95, 3.0, -20, 90),       # corridor B
              (-27.7, 3.9, 2.95, 0)]                               # secret
KEEP_OUT = [detailing.keep_out((x, y, z), (1.1, 0.3, 0.45) if y > 9 else (0.7, 0.3, 0.3)) for x, y, z in CEILING_LIGHTS]
KEEP_OUT += [detailing.keep_out((x, y, z), (0.3, 0.35, 0.3)) for x, y, z, _ in WALL_LAMPS]

# --- UT99-style trims generated from the room list: baseboards, cornices, bands, pilasters with
# plinths and capitals, and ceiling girders lined up with the pilasters (docs/ut99_reference.md)
trim_group = s.node("Trims", "CSGCombiner3D", csg)
for i, (lo, hi, m) in enumerate(detailing.all_trims(ROOMS, avoid=KEEP_OUT)):
    box(trim_group, (lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2]), m, name=f"Trim{i}")

# ----------------------------------------------------------------------------- compiled geometry

nav = lc.add_navigation(s)
geo = s.node("Geometry", "StaticBody3D", nav, collision_layer=1, collision_mask=0)
s.node("Mesh", "MeshInstance3D", geo, gi_mode=1)
s.node("Collision", "CollisionShape3D", geo)

# ----------------------------------------------------------------------------- lighting

lc.add_environment(s, fog_color="#2a2622", fog_density=0.004)
lc.add_lightmap(s, texel_scale=1.0)
lc.add_fill_lights(s, [((-9, 8.5, 2), "#4f7dff", 0.9, 16), ((9, 8.5, 2), "#4f7dff", 0.9, 16),
                       ((-20, 4, 2), "#ff9a4a", 0.6, 10), ((0, 5, -32), "#50ff90", 0.5, 9)])
s.node("Lights", "Node3D", ".")
for i, (x, y, z) in enumerate(CEILING_LIGHTS):
    props = dict(position=v3(x, y, z))
    if y > 9:
        props["scale"] = v3(1.6, 1.0, 1.6)
    s.instance(f"CeilingLight{i}", lc.ENTITY_SCENES["ceiling_light"], "Lights", **props)
for i, (x, y, z, yaw) in enumerate(WALL_LAMPS):
    s.instance(f"WallLamp{i}", lc.ENTITY_SCENES["wall_lamp"], "Lights", position=v3(x, y, z),
               rotation_degrees=v3(0, yaw, 0))
# cold "moonlight" through the skylight grate, from the direction of the planet drawn by sky_night
s.node("SkylightSpot", "SpotLight3D", "Lights", position=v3(0, 11.45, 0),
       rotation_degrees=v3(-75.2, 36.9, 0), light_color=lc.hexcolor("#9db4ff"), light_energy=9.0,
       light_indirect_energy=1.0, light_size=0.3, spot_range=16.0, spot_angle=32.0, spot_attenuation=0.6,
       light_bake_mode=1, shadow_enabled=True)
# UT99 zone ambient: shadows fall to dark blue, never black
lc.add_zone_ambient(s, [(r.x, r.y, r.z) for r in ROOMS if r.trims])

lc.add_probes(s, [
    (0, 1.5, 36), (0, 1.5, 23), (0, 1.5, 16), (-8, 1.5, 10), (8, 1.5, 10), (0, 2.5, 0), (-8, 1.5, -10),
    (8, 1.5, -10), (0, 5, 0), (12, 5.5, -4), (12, 5.5, -12), (12, 2.5, 10), (-20, 1.5, 2), (-20, 3.5, -2),
    (-27.5, 3.2, 1.5), (0, 1.5, -20), (0, 1.5, -32), (-4, 3, -32), (4, 3, -32),
])
lc.add_reflection_probes(s, [
    ("RefStart", (-6, 6), (0, 4.5), (30, 42)),
    ("RefCorridorA", (-2, 2), (0, 4), (16.3, 30)),
    ("RefHall", (-14, 14), (0, 10), (-14, 15.8)),
    ("RefStorage", (-26, -14.4), (0, 5), (-6, 10)),
    ("RefCorridorB", (-2, 2), (0, 4), (-26, -14.4)),
    ("RefExit", (-7, 7), (0, 6), (-38, -26)),
])

# ----------------------------------------------------------------------------- gameplay

lc.add_entities(s, [
    ("player_start", (0, 0, 38), 0),
    # Q2/Unreal-style split doors in Blender-made frames, and framed archways
    ("doorway", (0, 0, 16.05), 0),
    ("doorway", (0, 0, -14.2), 0),
    ("archway_400x400", (0, 0, 30.0), 0),
    ("archway_400x400", (0, 0, -26.0), 0),
    ("archway_400x350", (-14.2, 0, 2.0), 90),
    # enemies
    ("grunt", (0, 0, 19.5), 180),
    ("grunt", (-8, 0, 11), 180), ("grunt", (8, 0, -2), 160), ("grunt", (2, 1, -1.5), 180),
    ("grunt", (12, 4, -9), 180), ("drone", (-6, 4.5, -8), 180), ("drone", (6, 5.5, 9), 180),
    ("brute", (0, 0, -11), 180, {"Ambush": True}),
    ("grunt", (-20, 0, -2), -90), ("grunt", (-22, 0, 5), -120), ("drone", (-18, 3.5, 2), -90),
    ("brute", (-3, 0, -31), 180), ("grunt", (4, 0, -35), 200),
    # pickups
    ("shells", (3, 0, 34), 0), ("armor", (-3, 0, 34), 0), ("health", (4.5, 1, 31.5), 0),
    ("health", (0, 0, 24), 0),
    ("chaingun", (0, 1, 0.5), 0), ("bullets", (-11, 0, -11), 0), ("health", (11, 0, 13), 0),
    ("health", (-12, 0, 13), 0), ("shells", (-6, 0, -12), 0),
    ("rocket_launcher", (12, 4, -12), 0), ("rockets", (12, 4, -10), 0),
    ("bullets", (-16, 0, 8), 0), ("shells", (-24.5, 0, -4), 0), ("health", (-16, 0, -4), 0),
    ("megahealth", (-28, 2, 1.5), 0),
    ("health", (5, 0, -28.5), 0), ("rockets", (-5, 0, -28.5), 0),
    # hazards
    ("barrel", (-4.8, 0, -4.2), 0), ("barrel", (-4.2, 0, 4.4), 0), ("barrel", (9.2, 0, 3.2), 0),
    ("barrel", (-20, 0, 0.5), 0), ("barrel", (-19.2, 0, 1.2), 0),
    ("exit", (0, 0.3, -33), 0),
])
lc.add_trigger(s, "SecretAlcove", 3, (-29.4, 2.0, 0.1), (-26.2, 4.0, 2.9))
lc.add_trigger(s, "HintStart", 4, (-2, 0, 27), (2, 3, 29), Message="Doors open when you get close.")

out = os.path.join(GAME, "levels", "csg", "level_csg.tscn")
s.save(out)
print("wrote", out)

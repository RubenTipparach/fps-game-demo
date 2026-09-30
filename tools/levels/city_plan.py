"""Plan the 3D build of a city layout: sectors, chunks, primitives, lights and entities.

The layout (tools/levels/layouts/<id>.py) is the level's single source (CLAUDE.md 7.1). The
design map (render_map.py) draws it; this module turns the same shapes into a build plan, and
tools/blender/build_undercity.py meshes the plan in Blender. Lots, pillars and shapes come from
render_map's own functions, so the level cannot disagree with the map. It is pure Python with
shapely, so it runs outside Blender (whose Python has no shapely) and its rules stay testable.

    python3 tools/levels/city_plan.py hub            # the plan as JSON on stdout
    python3 tools/levels/city_plan.py hub --stats    # counts per sector

Coordinates are layout metres: x east, y south, z up. Blender maps them to X = x, Y = -y, Z = z,
and the glTF export to Godot x = x, y = z, z = y.

The plan (JSON):
    {"level", "chunk_m", "sectors": [{"name", "objects": [...], "entities": [...]}], "stats"}
    object:  {"name", "col": null | "col" | "colonly", "extras": {}, "origin": [x, y, z] | null,
              "prims": [...]}
    entity:  {"name": "ENT_<kind>_<id>", "pos": [x, y, z], "heading": compass degrees,
              "extras": {}, "preview": light preview or null}
    prims (world coordinates; materials are names from game/materials/materials.json):
      prism  {"rings": [ring, hole...], "tris": the caps' triangles, "z0", "z1", "mat": {"top", "bottom", "side"},
              "caps": ["top", "bottom"], "edges": per ring, per edge [z0, z1] or null (no side),
              "flip": inverted (a pit or a canal seen from inside)}
      hexa   {"p": 8 corners (bottom 4, then top 4 in the same order), "mat": [bottom, top,
              side0..side3] (side i joins corners i and i+1), "skip": face indices}
      cyl    {"c": [x, y, z0], "r", "h", "seg", "mat": {"side", "cap"}, "caps": bool, "axis": [x, y, z]}
      quad   {"p": 4 corners, "mat"}
      text   {"s", "p": [x, y, z] (bottom centre), "heading": the way the text faces, "size",
              "depth", "mat"}
      loft   {"rings": [ring per level], "z": [z per level], "mat": {"top", "bottom", "side"}}
      bool   {"solid": prism, "cutters": [hexa...], "interior": {"object", "boxes"} | null}
             The solid minus the cutters (carved faces take the cutter's face materials).
             Faces inside an interior box go to the interior object.
"""
import argparse
import contextlib
import heapq
import importlib
import json
import math
import os
import random
import re
import sys

import shapely
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import linemerge, nearest_points, split, unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
import render_map as RM  # noqa: E402
import detailing  # noqa: E402
import skyline  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import vehicle_data  # noqa: E402  (the parked vehicles' table and their committed models)

# ----------------------------------------------------------------------------- the city kit
# Generic construction rules shared by every city level. Level-specific numbers (district
# heights and styles, building heights, water levels, walkway heights) live in the layout.

STREET_Z = 0.0        # asphalt
PLAZA_Z = 0.05        # paved squares
PAVED_Z = 0.15        # sidewalks and every other paved strip; the curb is its edge
SIDEWALK_M = 2.0      # sidewalk width along building fronts
FLOOR_Z = 0.15        # interior floors sit at sidewalk level: no step at a door
ROOM_H = 3.5          # interior floor to ceiling
WALL_T = 0.2          # interior walls
CHUNK_M = 40.0        # sector chunks, so the engine can frustum-cull them
QUAY_Z = 0.0          # canal and pit walls rise to street level; paving sits on top
BRIDGE_DECK = 0.6     # bridge deck thickness
WALK_DECK = 0.15      # walkway deck thickness
RAIL_H = 1.0          # railing height
LAMP_EVERY = 18.0     # street lamps, metres along a street
LAMP_H = 5.6
WALL_LAMP_EVERY = 16.0
WALL_LAMP_Z = 3.3     # plate 3.1-3.5 m: above shop fronts (3.05), below the string course (3.55)
DOOR_H = 2.4          # interior doors; openings 2.5 m wide or more get WIDE_DOOR_H
WIDE_DOOR_H = 3.0
PILLAR_BASE_HALF_M = 1.2  # a viaduct pillar's base, half its side
SKYWAY_SCENERY_M = 200.0  # the Skyway runs on this far past each edge, as scenery (hub-skyline)
SKYWAY_SCENERY_SPAN_M = 36.0  # ... in spans about this long, as over the hub
SKYWAY_PIER_DEPTH_M = 40.0    # ... on piers down into the haze below the hub's ground
# Ways out of the water (openspec/changes/archive/2026-09-29-water-and-swimming, design section 4). How a ladder
# or a ledge is climbed is the game's (data/water.json); where they are is level construction.
LADDER_EVERY_M = 30.0   # a quay ladder every this many metres of open quay
EXIT_REACH_M = 25.0     # every point of water is this close to a way out, in a straight swim
EXIT_GRID_M = 1.0       # the exit rule samples each water surface on this grid
LADDER_CLEAR_M = 3.0    # no quay ladder this close to a bridge deck, a boat or a pillar
LADDER_SPACING_M = 10.0  # nor this close to another ladder
LADDER_W_M = 0.6        # between the stiles' centres
LADDER_STAND_OFF_M = 0.15  # the stiles' outer faces stand this far off the wall (a climber holds here)
LADDER_UNDER_M = 0.6    # a ladder reaches this far under the surface
LADDER_HOOP_M = 1.0     # its grab hoops rise this far above the quay
LADDER_HOOP_REACH_M = 0.5  # and come down this far in from the edge
RUNG_EVERY_M = 0.3
RAIL_GAP_M = 1.2        # the quay railing's opening at a ladder
LADDER_LAND_MAX_M = 2.0  # a climber steps off a ladder at most this far in from the edge
SHIP_DECK_ABOVE_M = 3.4  # a derelict ship's deck above its water's surface
WATER_JSON = os.path.join(ROOT, "game", "data", "water.json")
# Layout shape classes a person may stand inside: neon strips hang on walls, and the dark
# features (culverts, the outfall, tunnel portals) are hollow. A stall's footprint holds its
# vendor's space, so stalls register their counter, back and posts as solids instead.
WALK_THROUGH_CLASSES = ("fix-neon", "fix-band", "fix-dark", "stall")
STANDING_STEP_M = 0.02  # a detail whose top is this close to a person's feet is underfoot, not in the way
NPC_SCENE = os.path.join(ROOT, "game", "scenes", "undercity", "npc.tscn")
PLAYER_SCENE = os.path.join(ROOT, "game", "scenes", "undercity", "player.tscn")
PLAYER_SCRIPT = os.path.join(ROOT, "game", "scripts", "Player", "PlayerController.cs")
# Puddles (openspec/changes/street-puddles, design section 3.5). Where rain water gathers is level
# construction, so its numbers live here; how a puddle looks is the ground shader's (materials.json),
# and whether a roof keeps the rain off is the core's (data/character_lighting.json, headroom_m).
CHARACTER_LIGHTING_JSON = os.path.join(ROOT, "game", "data", "character_lighting.json")
PUDDLE_KERB_OFF_M = 0.05   # a puddle's edge stays this far in from its own ground's edge (a kerb face)
PUDDLE_CLEAR_M = 0.3       # and this far from a building, a lot, a fixture, a prop, a solid or a stair
PUDDLE_LOW_M = 0.5         # a detail box or solid whose bottom is below this stands on the ground
PUDDLE_GAP_M = 0.1         # two puddles are at least this far apart
PUDDLE_FIT = 0.5           # a puddle keeps at least this share of its ellipse after its ground's edge clips it
# Sizes and gaps give the amount the owner chose (survey L2, about 2.6 % of the ground; design 3.5)
GUTTER_LEN_M, GUTTER_WIDE_M, GUTTER_GAP_M = (2.0, 5.0), (0.6, 1.0), (1.5, 4.0)
GULLY_EVERY_M, GULLY_ACROSS_M, GULLY_GRATE_M = 25.0, (1.2, 1.8), (0.45, 0.25)   # grate: along, across the kerb
DRIP_LEN_M, DRIP_WIDE_M, DRIP_GAP_M, DRIP_OUT_M = (1.5, 3.0), (0.5, 0.8), (1.0, 3.0), (0.05, 0.35)
DRIP_ROOFS = ("awning", "Skyway deck")   # the shelters whose edges drip onto open ground

# Light colours (linear-ish RGB) and settings: (color, energy, range_m, corona material, corona size)
LIGHTS = {
    "sodium": ((1.0, 0.6, 0.28), 2.4, 16.0, "corona_warm", 1.5),
    "viaduct": ((1.0, 0.62, 0.3), 2.6, 18.0, "corona_warm", 1.6),
    "pink": ((1.0, 0.31, 0.64), 1.5, 7.0, "corona_pink", 1.3),
    "cyan": ((0.21, 0.88, 1.0), 1.5, 7.0, "corona_cyan", 1.3),
    "fire": ((1.0, 0.45, 0.15), 1.8, 8.0, "corona_warm", 1.1),
    "stall": ((1.0, 0.76, 0.46), 1.1, 6.5, "corona_warm", 0.8),
    "cool": ((0.55, 0.75, 1.0), 1.2, 8.0, "corona_cool", 0.9),
    "billboard": ((0.3, 0.85, 1.0), 3.0, 26.0, "corona_cyan", 4.0),
    "warm_sign": ((1.0, 0.7, 0.4), 1.4, 7.0, "corona_warm", 1.2),
    "door": ((1.0, 0.78, 0.55), 1.2, 6.0, "corona_warm", 0.7),    # an entrance's lintel downlight
}
# A door frame's material by facade style (openspec/changes/hub-doorways, design section 3.2):
# no new material. A named building may name its own "frame_style": the shrine's is stone with
# neon capitals.
FRAME_MATS = {"dock": "tech_panel", "workshop": "rust_metal", "shanty": "rust_metal",
              "strip": "stone_blocks", "market": "stone_blocks", "shrine": "stone_blocks"}
FRAME_ACCENTS = {"shrine": {"capital": "neon_pink"}}
# The closed doors a filler building shows (openspec/changes/hub-doorways, design section 3.4): the
# clear opening (w, h) and the leaf's material, which is the back of a DRESS_DEPTH recess carved at
# the fits. A shop door stands inside its bay; the rest take a span of their own.
DRESS_DOORS = {"shop": {"clear": (1.0, 2.2), "leaf": ("tech_panel",)},
               "residents": {"clear": (1.0, 2.2), "leaf": ("tech_panel",)},
               "shanty": {"clear": (0.9, 2.0), "leaf": ("crate", "rust_metal")},
               "man": {"clear": (1.0, 2.2), "leaf": ("rust_metal",)}}
DRESS_DEPTH = 0.08
STYLE_DOOR = {"shanty": "shanty", "strip": "residents", "market": "residents", "workshop": "man", "dock": "man"}
SHANTY_BOARDED, SHANTY_PADLOCKED = 0.20, 0.25
DOOR_FACES = {"-z": 0, "+z": 1, "+v": 2, "+u": 3, "-v": 4, "-u": 5}   # edge_box's faces, v into the wall
SIGN_COLOURS = [("neon_pink", "pink"), ("neon_cyan", "cyan"), ("lamp_glow", "warm_sign")]
CORONA_EXTRAS = {"gi_mode": 0, "cast_shadow": 0, "visibility_range_end_m": 110.0}
PROP_EXTRAS = {"visibility_range_end_m": 70.0}
# the water's surface refracts and reflects what is around it (shaders/water.gdshader): it takes no
# baked light and casts no shadow
WATER_EXTRAS = {"gi_mode": 0, "cast_shadow": 0}
# the skyline is unshaded scenery past the hub's edges (openspec/changes/archive/2026-09-29-hub-skyline, design
# section 3): no baked light, no shadows
SKYLINE_EXTRAS = {"gi_mode": 0, "cast_shadow": 0}
# Lightmap texels: the import bakes at 0.4 m (import_presets.py); interiors ask for 0.15 m.
EXTERIOR_TEXEL_M = 0.4
INTERIOR_TEXEL_M = 0.15
INTERIOR_EXTRAS = {"visibility_range_end_m": 45.0, "lightmap_texel_scale": round(EXTERIOR_TEXEL_M / INTERIOR_TEXEL_M, 3)}

# Facade kit per district style. facade: wall materials to pick from; roof/cap: roof and parapet
# coping; parapet: height above the roof (0 = none); ground_h: ground storey; floor_h: upper
# storeys; win: (w, h); sill: above the storey floor; pitch: window spacing range; lit: share of
# lit windows; front: ground floor treatment on street fronts; the rest are probabilities.
STYLES = {
    "shanty": dict(facade=("rust_metal", "brick_wall", "concrete", "rust_metal", "tech_panel"), roof="rust_metal",
                   cap="rust_metal", parapet=0.0, ground_h=3.0, floor_h=2.8, win=(0.9, 1.1), sill=0.8,
                   pitch=(2.0, 2.8), lit=0.45, band=False, front="shanty", awning=0.25, blade=0.05,
                   fire_escape=0.3, stack=0.45),
    "strip": dict(facade=("brick_wall", "concrete", "tech_panel", "brick_wall"), roof="concrete", cap="tech_panel",
                  parapet=0.9, ground_h=3.9, floor_h=3.2, win=(1.2, 1.6), sill=0.8, pitch=(2.4, 3.2), lit=0.5,
                  band=True, front="shop", awning=0.55, blade=0.5, fire_escape=0.3, stack=0.0),
    "market": dict(facade=("concrete", "brick_wall", "stone_blocks"), roof="concrete", cap="tech_panel",
                   parapet=0.9, ground_h=3.9, floor_h=3.2, win=(1.2, 1.6), sill=0.8, pitch=(2.4, 3.2), lit=0.4,
                   band=True, front="shop", awning=0.6, blade=0.3, fire_escape=0.1, stack=0.0),
    "workshop": dict(facade=("rust_metal", "concrete", "brick_wall"), roof="rust_metal", cap="concrete",
                     parapet=0.6, ground_h=4.6, floor_h=3.4, win=(1.6, 1.0), sill=1.2, pitch=(2.6, 3.4), lit=0.3,
                     band=False, front="rollup", awning=0.0, blade=0.05, fire_escape=0.0, stack=0.0),
    "dock": dict(facade=("concrete", "tech_panel", "rust_metal"), roof="concrete", cap="tech_panel", parapet=0.9,
                 ground_h=4.2, floor_h=3.3, win=(1.4, 1.2), sill=1.0, pitch=(2.6, 3.4), lit=0.35, band=True,
                 front="loading", awning=0.0, blade=0.0, fire_escape=0.0, stack=0.0),
    "foundation": dict(facade=("stone_blocks",), roof="concrete", cap="stone_blocks", parapet=0.0, ground_h=4.0,
                       floor_h=4.0, win=(1.2, 1.6), sill=1.0, pitch=(3.0, 3.0), lit=0.0, band=False, front="none",
                       awning=0.0, blade=0.0, fire_escape=0.0, stack=0.0),
}
# Interior finishes by style: (walls, floor, ceiling, trim style for tools/godot/detailing.py)
FINISH = {
    "shanty": ("brick_wall", "concrete", "rust_metal", "brick"),
    "strip": ("brick_wall", "floor_tiles", "ceiling_tiles", "brick"),
    "market": ("concrete", "floor_tiles", "ceiling_tiles", "tech"),
    "workshop": ("rust_metal", "concrete", "rust_metal", "tech"),
    "dock": ("tech_panel", "floor_tiles", "ceiling_tiles", "tech"),
    "foundation": ("stone_blocks", "floor_tiles", "ceiling_tiles", "stone"),
}
BLADE_WORDS = ["BAR", "HOTEL", "RAMEN", "SAKE", "PAWN", "NOODLE", "LIQUOR", "CLUB", "TATTOO", "CYBER", "SUSHI",
               "OPEN", "DINER", "DOLL", "LUCKY", "JADE", "KARAOKE", "BOOKS", "REPAIR", "PHO"]


def scene_collider(path):
    """A body's collider as (radius, height) in metres, read from the scene the game spawns
    (tools/godot/gen_undercity_scenes.py writes them: a capsule for an NPC, a cylinder for the
    player), so the placement check can't drift from the game."""
    with open(path) as f:
        text_ = f.read()
    starts = [i for i in (text_.find('[sub_resource type="CapsuleShape3D"'), text_.find('[sub_resource type="CylinderShape3D"'))
              if i >= 0]
    if not starts:
        raise SystemExit(f"{path}: no capsule or cylinder collider; the placement check needs the body's size")
    block = text_[min(starts):].split("\n\n", 1)[0]
    values = dict(line.split(" = ", 1) for line in block.splitlines()[1:] if " = " in line)
    try:
        radius, height = float(values["radius"]), float(values["height"])
    except (KeyError, ValueError):
        raise SystemExit(f"{path}: the collider needs a radius and a height, found {values}")
    if not (math.isfinite(radius) and math.isfinite(height) and 0 < 2 * radius <= height):
        raise SystemExit(f"{path}: a collider of r {radius} m, h {height} m isn't a standing body")
    return radius, height


def player_step_m():
    """The highest step the player walks up, metres: the player scene's MaxStepHeight, or the
    controller's default for it, read from the files the game runs."""
    with open(PLAYER_SCENE) as f:
        m = re.search(r"^MaxStepHeight = ([0-9.]+)", f.read(), re.M)
    if not m:
        with open(PLAYER_SCRIPT) as f:
            m = re.search(r"public float MaxStepHeight = ([0-9.]+)f;", f.read())
    if not m:
        raise SystemExit(f"{PLAYER_SCRIPT}: no MaxStepHeight; the ladder landings need the player's step")
    return float(m.group(1))


def water_data():
    """The game's own data/water.json, so the plan and the game can't disagree about how a
    swimmer climbs out."""
    with open(WATER_JSON) as f:
        # the game's data files allow whole-line // comments (Undercity.Core JsonData)
        return json.loads("".join(line for line in f if not line.lstrip().startswith("//")))


VEHICLES = vehicle_data.load()   # tools/blender/vehicles.json: the variants a car spot draws from


def wetness_data():
    """The core's wetness rule's numbers (data/character_lighting.json "wetness"), so a puddle and
    a character agree about which roofs keep the rain off."""
    with open(CHARACTER_LIGHTING_JSON) as f:
        return json.loads("".join(line for line in f if not line.lstrip().startswith("//")))["wetness"]


def ellipse(cx, cy, length, width, angle):
    """An ellipse length x width metres round (cx, cy), its long axis at angle radians."""
    e = affinity.scale(Point(0, 0).buffer(1.0, quad_segs=8), length / 2, width / 2)
    return affinity.translate(affinity.rotate(e, angle, origin=(0, 0), use_radians=True), cx, cy)


def mantle_rise():
    """The ledge heights above a water surface a swimmer can climb onto, (min, max) metres."""
    w = water_data()
    return w["mantle_min_rise_m"], w["mantle_max_rise_m"]


def r4(v):
    return round(float(v), 4)


def p3(x, y, z):
    return [r4(x), r4(y), r4(z)]


def ring_xy(coords):
    pts = list(coords)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return [[r4(x), r4(y)] for x, y in pts]


def polys(g):
    return RM.polygons(g)


def oriented(pg):
    """Exterior clockwise in layout (y south) coordinates, so counter-clockwise in Blender."""
    return orient(pg, sign=-1.0)


def unit(dx, dy):
    L = math.hypot(dx, dy)
    return (dx / L, dy / L) if L > 1e-9 else (1.0, 0.0)


# Godot's scene importer turns a node whose name carries one of these words after "-", "_" or "$"
# into another type ("Node type customization using name suffixes"; the presets set
# nodes/use_node_type_suffixes). Godot 4.7.2 made "ENT_vehicle_008" a VehicleBody3D named "ENT_008"
# with the empty under it, and the level importer then freed both (openspec/changes/street-vehicles,
# design section 4). An entity's name must not carry one.
GODOT_TYPE_SUFFIXES = ("colonly", "convcolonly", "convcol", "col", "navmesh", "rigid", "vehicle", "wheel",
                       "occonly", "occ", "noimp")


def godot_type_suffix(name):
    """The type suffix Godot's importer would read in a node name, or None."""
    m = re.search(r"[-_$](" + "|".join(GODOT_TYPE_SUFFIXES) + r")(?=$|[-_.\d])", name.lower())
    return m.group(0) if m else None


def heading_of(dx, dy):
    """Compass heading (0 = north = -y, 90 = east) of a layout direction."""
    return (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0


# ----------------------------------------------------------------------------- primitives

def mats6(bottom, top, s0, s1=None, s2=None, s3=None):
    s1 = s1 or s0
    s2 = s2 or s0
    s3 = s3 or s1
    return [bottom, top, s0, s1, s2, s3]


def hexa(corners4_bottom, z0, z1, mat, skip=(), corners4_top=None):
    """Prism over a quad: 4 (x, y) corners, from z0 to z1 (or explicit top corners)."""
    top = corners4_top or [(x, y, z1) for x, y in corners4_bottom]
    bot = [(x, y, z0) for x, y in corners4_bottom]
    m = mat if isinstance(mat, list) else [mat] * 6
    return {"t": "hexa", "p": [p3(*c) for c in bot] + [p3(*c) for c in top], "mat": m, "skip": list(skip)}


def hexa_pts(pts8, mat, skip=()):
    m = mat if isinstance(mat, list) else [mat] * 6
    return {"t": "hexa", "p": [p3(*c) for c in pts8], "mat": m, "skip": list(skip)}


def quad(pts4, mat):
    """One face through 4 points (3D), wound as given."""
    return {"t": "quad", "p": [p3(*c) for c in pts4], "mat": mat}


def box_prim(lo, hi, mat, skip=()):
    """Axis-aligned box, layout coordinates."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    return hexa([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, mat, skip)


def viaduct_span(Q, s0, s1, half, d0, d1, g0, skip_ends=()):
    """One span of the Skyway between stations s0 and s1 along its line (Q(s, v) is the point s
    along it and v across): the deck, its parapets and the girders under it. The one span the
    viaduct and its scenery past the hub's edges share."""
    prims = [hexa([Q(s0, -half), Q(s1, -half), Q(s1, half), Q(s0, half)], d0, d1,
                  ["concrete", "asphalt", "concrete", "concrete", "concrete", "concrete"], skip=list(skip_ends))]
    for side in (-1, 1):
        v0, v1 = sorted((side * half, side * (half - 0.4)))
        prims.append(hexa([Q(s0, v0), Q(s1, v0), Q(s1, v1), Q(s0, v1)], d1, d1 + 1.1, "concrete", skip=[0] + list(skip_ends)))
        for gv in (4.8, 7.2):
            va, vb = sorted((side * (gv - 0.35), side * (gv + 0.35)))
            prims.append(hexa([Q(s0, va), Q(s1, va), Q(s1, vb), Q(s0, vb)], g0, d0, "rust_metal", skip=[1] + list(skip_ends)))
    return prims


def frame(A, t, n):
    """A local frame on a facade edge: s along the edge from A, o outward, z up."""
    def P(s, o):
        return (A[0] + t[0] * s + n[0] * o, A[1] + t[1] * s + n[1] * o)
    return P


def edge_box(P, s0, s1, o0, o1, z0, z1, mat, skip=()):
    """Box in an edge frame. Sides: 0 at o0, 1 at s1, 2 at o1, 3 at s0."""
    return hexa([P(s0, o0), P(s1, o0), P(s1, o1), P(s0, o1)], z0, z1, mat, skip)


def obox_corners(cx, cy, ux, uy, half_u, half_v):
    """The four corners of a rectangle centred on (cx, cy) whose local u axis is (ux, uy)."""
    vx, vy = -uy, ux
    return [(cx - ux * half_u - vx * half_v, cy - uy * half_u - vy * half_v),
            (cx + ux * half_u - vx * half_v, cy + uy * half_u - vy * half_v),
            (cx + ux * half_u + vx * half_v, cy + uy * half_u + vy * half_v),
            (cx - ux * half_u + vx * half_v, cy - uy * half_u + vy * half_v)]


def obox(cx, cy, ux, uy, half_u, half_v, z0, z1, mat, skip=()):
    """Box centred on (cx, cy) whose local u axis is (ux, uy); v is u turned 90 degrees."""
    return hexa(obox_corners(cx, cy, ux, uy, half_u, half_v), z0, z1, mat, skip)


def beam(a, b, width, thick, mat):
    """A straight bar from point a to point b (3D), width across, thick up."""
    ux, uy = unit(b[0] - a[0], b[1] - a[1])
    vx, vy = -uy, ux
    w = width / 2
    pts = []
    for z_off in (0.0, thick):
        for (s, side) in ((0, -1), (1, -1), (1, 1), (0, 1)):
            base = a if s == 0 else b
            pts.append((base[0] + vx * w * side, base[1] + vy * w * side, base[2] + z_off))
    return hexa_pts(pts, mat)


def cap_tris(pg):
    """The polygon's cap as triangles (constrained Delaunay: holes and pinch points are safe)."""
    return [ring_xy(t.exterior.coords) for t in shapely.constrained_delaunay_triangles(pg).geoms if t.area > 1e-9]


def prism(pg, z0, z1, mat, caps=("top",), edges=None, flip=False):
    pg = oriented(pg)
    rings = [ring_xy(pg.exterior.coords)] + [ring_xy(i.coords) for i in pg.interiors]
    d = {"t": "prism", "rings": rings, "z0": r4(z0), "z1": r4(z1), "mat": mat, "caps": list(caps), "flip": flip,
         "tris": cap_tris(pg) if caps else []}
    if edges is not None:
        d["edges"] = edges
    return d


def cyl(x, y, z0, r, h, mat, seg=12, caps=True, axis=(0.0, 0.0, 1.0), cap_mat=None):
    return {"t": "cyl", "c": p3(x, y, z0), "r": r4(r), "h": r4(h), "seg": seg,
            "mat": {"side": mat, "cap": cap_mat or mat}, "caps": caps, "axis": [r4(a) for a in axis]}


def text(s, x, y, z, heading, size, mat, depth=0.08):
    return {"t": "text", "s": s, "p": p3(x, y, z), "heading": r4(heading), "size": r4(size), "depth": r4(depth),
            "mat": mat}


# ----------------------------------------------------------------------------- the plan

class Plan:
    def __init__(self, m, entities=None):
        self.m = m
        self.W, self.H = m["size"]
        self.seed = m["seed"]
        self.sectors = {}
        self.order = []
        self.lights = 0
        self.zboxes = {}          # z-fighting groups: name -> {"airs": [], "details": []}
        self.solids = []          # (label, footprint, z0, z1): solids that aren't boxes
        self.covers = []          # (label, footprint, z0): awnings people shelter under
        self.shelters = []        # (label, footprint, z0): every roof, by the height of its underside
        self.entity_list = entities or []
        self.districts = [(d, Polygon(d["poly"])) for d in m["districts"]]
        self.probes = []          # reflection probe boxes for the scene generator
        self.rooms_out = []       # interior rooms (zone ambient)

    # sectors, chunks, objects -----------------------------------------------
    def sector_id(self, name):
        return name.lower().replace(" ", "_")

    def sector(self, name):
        if name not in self.sectors:
            self.sectors[name] = {"name": name, "objects": {}, "entities": []}
            self.order.append(name)
        return self.sectors[name]

    def district_at(self, x, y):
        pt = Point(x, y)
        for d, pg in self.districts:
            if pg.contains(pt):
                return d
        best = min(self.districts, key=lambda dp: dp[1].distance(pt))
        return best[0]

    def district_sector(self, x, y):
        return self.sector_id(self.district_at(x, y)["name"])

    def cell(self, x, y):
        i = min(max(int(math.floor(x / CHUNK_M)), 0), int(math.ceil(self.W / CHUNK_M)) - 1)
        j = min(max(int(math.floor(y / CHUNK_M)), 0), int(math.ceil(self.H / CHUNK_M)) - 1)
        return i, j

    def obj(self, sector, kind, x=None, y=None, col=None, extras=None, origin=None, name=None):
        """The object a primitive goes into. Chunked by (x, y) unless a name is given."""
        s = self.sector(sector)
        if name is None:
            i, j = self.cell(x, y)
            name = f"{sector}_{kind}_{i}_{j}"
        full = name + ("-" + col if col else "")
        if full not in s["objects"]:
            s["objects"][full] = {"name": full, "col": col, "extras": dict(extras or {}),
                                  "origin": p3(*origin) if origin else None, "prims": []}
        return s["objects"][full]["prims"]

    def add(self, sector, kind, x, y, prim, col=None):
        self.obj(sector, kind, x, y, col=col).append(prim)

    def zgroup(self, name):
        return self.zboxes.setdefault(name, {"airs": [], "details": []})

    def solid(self, corners, z0, z1, label):
        """Register a solid that isn't an axis-aligned box (a stall's counter, a pillar) by its
        footprint corners and height, for the standing-room check."""
        self.solids.append((label, Polygon(corners), z0, z1))

    def cover(self, corners, z0, label):
        """Register an awning by its footprint corners and its underside's lowest height: a
        civilian under it is sheltered, and doesn't open an umbrella (export_level_data.py). An
        awning is a shelter too."""
        self.covers.append((label, Polygon(corners), z0))
        self.shelter(Polygon(corners), z0, label)

    def shelter(self, g, z0, label):
        """Register a roof the rain can't pass by its footprint (a polygon or a multipolygon) and
        its underside's lowest height: anyone standing inside the footprint below that height is
        dry (openspec/changes/archive/2026-09-29-character-lighting, design section 9; export_level_data.py)."""
        for pg in polys(g):
            self.shelters.append((label, pg, z0))

    def zdetail(self, group, lo, hi, label):
        """Register an axis-aligned box (layout coordinates) for the z-fighting check."""
        self.zgroup(group)["details"].append(((lo[0], lo[2], lo[1]), (hi[0], hi[2], hi[1]), label))

    def entity(self, sector, name, x, y, z, heading=0.0, extras=None, preview=None):
        suffix = godot_type_suffix(name)
        if suffix:
            raise SystemExit(f"entity {name}: Godot's importer reads '{suffix}' in a node name as a node type "
                             f"and rebuilds the node (GODOT_TYPE_SUFFIXES); name the kind another way")
        self.sector(sector)["entities"].append({"name": name, "pos": p3(x, y, z), "heading": r4(heading),
                                                "extras": extras or {}, "preview": preview})

    def light(self, sector, kind, x, y, z, corona_at=None, energy=None, rng=None):
        """A baked light (ENT_light) with its corona. The caller builds the visible fixture."""
        color, e, rg, cmat, csize = LIGHTS[kind]
        self.lights += 1
        n = self.lights
        e = energy if energy is not None else e
        extras = {"energy": e, "range": rg, "color": list(color), "kind": "light", "id": f"{n:03d}", "style": kind}
        self.entity(sector, f"ENT_light_{n:03d}", x, y, z, 0.0, extras,
                    preview={"color": list(color), "energy": e, "range": rg})
        self.corona(sector, kind, *(corona_at or (x, y, z)), name=f"corona_{n:03d}")
        return n

    def corona(self, sector, kind, cx, cy, cz, name=None):
        """A light's glow billboard (UT99 corona), its own object so Godot can billboard it."""
        _, _, _, cmat, csize = LIGHTS[kind]
        if name is None:
            self.ncorona = getattr(self, "ncorona", 0) + 1
            name = f"corona_x{self.ncorona:03d}"
        prims = self.obj(sector, "corona", col=None, extras=CORONA_EXTRAS, origin=(cx, cy, cz), name=name)
        s = csize / 2
        # a flat square round the origin; the corona material billboards it in Godot
        prims.append(quad([(cx - s, cy, cz - s), (cx + s, cy, cz - s), (cx + s, cy, cz + s), (cx - s, cy, cz + s)], cmat))

    def lamp_entity(self, sector, kind, x, y, z, heading):
        """A light that is one of the game's fixture scenes (wall_lamp, ceiling_light)."""
        self.lights += 1
        n = self.lights
        warm = (1.0, 0.71, 0.42) if kind == "wall_lamp" else (1.0, 0.89, 0.72)
        self.entity(sector, f"ENT_{kind}_{n:03d}", x, y, z, heading, {"kind": kind, "id": f"{n:03d}"},
                    preview={"color": list(warm), "energy": 1.6 if kind == "wall_lamp" else 2.6,
                             "range": 8.0 if kind == "wall_lamp" else 11.0,
                             "offset": [0, 0, -0.35] if kind == "ceiling_light" else "forward"})
        return n

    # output --------------------------------------------------------------------
    def to_json(self):
        out = {"level": self.m["id"], "chunk_m": CHUNK_M, "sectors": []}
        for name in self.order:
            s = self.sectors[name]
            objs = [o for o in s["objects"].values() if o["prims"]]
            out["sectors"].append({"name": name, "objects": objs, "entities": s["entities"]})
        out["stats"] = self.stats()
        out["probes"] = self.probes
        out["rooms"] = self.rooms_out
        return out

    def stats(self):
        st = {}
        for name in self.order:
            s = self.sectors[name]
            objs = [o for o in s["objects"].values() if o["prims"]]
            st[name] = {"objects": len(objs), "prims": sum(len(o["prims"]) for o in objs),
                        "entities": len(s["entities"]),
                        "lights": sum(1 for e in s["entities"] if e["preview"])}
        st["_lights"] = self.lights
        return st


# ----------------------------------------------------------------------------- the city

class City:
    """Builds the plan for a "city" layout, one part of the level at a time."""

    def __init__(self, m, entities=()):
        self.m = m
        self.P = Plan(m)
        self.entities_in = list(entities)
        self.geo = RM.base_geometry(m)
        self.R = box(0, 0, self.P.W, self.P.H)
        opens = m.get("open", [])
        self.streets = [o for o in opens if "pts" in o]
        self.S = unary_union([o["_g"] for o in self.streets])
        self.rail_geom = unary_union([o["_g"] for o in self.streets if o["name"] == "rail"])
        self.pits = [o for o in opens if "poly" in o and "floor_m" in o]
        self.PIT = unary_union([o["_g"] for o in self.pits]) if self.pits else Polygon()
        self.pit_floor = self.pits[0]["floor_m"] if self.pits else 0.0
        self.PLZ = unary_union([o["_g"] for o in opens if "poly" in o and "floor_m" not in o])
        self.O = self.geo["open"]
        self.W = self.geo["water"]
        # water bodies, deepest first, cut so they don't overlap
        bodies = sorted([w for w in m.get("water", [])], key=lambda w: w.get("bed_m", -4.5))
        self.waters = []
        self.vehicles = []          # the parked vehicles, as City.vehicle() places them
        self.vehicle_decks = {}     # per spot size, the variants still to deal
        taken = Polygon()
        for w in bodies:
            g = RM.water_geom(w).difference(taken)
            taken = taken.union(RM.water_geom(w))
            self.waters.append({"id": w["id"], "g": g, "surface": w.get("surface_m", -2.2), "bed": w.get("bed_m", -4.5)})
        self.named = [b for b in m.get("buildings", [])]
        self.viaduct = next((e for e in m.get("elevated", []) if e["kind"] == "viaduct"), None)
        self.walkways = [e for e in m.get("elevated", []) if e["kind"] == "walkway" and "z_m" in e]
        for i, wk in enumerate(self.walkways):
            wk["_i"] = i
            wk["_line"] = LineString(wk["pts"])
            zs = wk["z_m"] if isinstance(wk["z_m"], list) else [wk["z_m"]] * len(wk["pts"])
            wk["_z"] = zs
            wk["_w"] = 1.6 if wk.get("hung") else (1.4 if len(zs) > 2 and len(set(zs)) > 1 else 2.0)
        if self.viaduct:
            self.vline = LineString(self.viaduct["pts"])
            self.vfoot = self.vline.buffer(self.viaduct["w"] / 2, cap_style=2, join_style=2)
            self.deck_top = self.viaduct.get("deck_m", 14.0)
        self.lots = []
        self.slivers = []       # lots too thin to build on (paved instead)
        self.closed_ends = []    # walkway ends against a wall (no stairs)
        self.facades = []       # (sector, A, t, n, length, z_top, occupied spans) for wall lamps
        self.stair_boxes = []   # pit stair treads (floor lookups)
        self.ladders = []       # ways out of the water: {"id", "water", "at", "foot", "n", "top", "bottom"}
        self.frames = {}        # framed doors by (building, door): {"door", "clear", "carved", "kind", "tris", "wall"}
        self.shown_doors = []   # doors a building shows on its facade: (building, x, y)
        self.door_counts = {}   # dressing doors by kind
        self.door_tris = {}     # the doors' triangles by what they are
        self.door_zfights = []  # dressing doors that z-fight in their own frame
        self.edge_doors = {}    # a facade edge's own doors, by id of its occupied list: [s along the edge]
        self.sliding = []       # public entrances' sliding doors: {"building", "door", "tag", "sweeps", "keep", "airs"}
        self.flights = []       # open stair flights' footprints, which puddles keep clear of
        self.puddle_list = []   # the puddles (City.puddles()): {"id", "kind", "at", "ground_m", "g"}
        self.gullies = []       # the kerb gullies' grates: {"id", "at", "heading"}

    # geometry lookups ------------------------------------------------------
    def walk_z(self, wk, x, y):
        """Deck top of a walkway at the point on its line nearest (x, y)."""
        line = wk["_line"]
        d = line.project(Point(x, y))
        acc = 0.0
        pts, zs = wk["pts"], wk["_z"]
        for k in range(len(pts) - 1):
            seg = math.dist(pts[k], pts[k + 1])
            if d <= acc + seg or k == len(pts) - 2:
                f = min(max((d - acc) / seg, 0.0), 1.0) if seg > 0 else 0.0
                return zs[k] + (zs[k + 1] - zs[k]) * f
            acc += seg
        return zs[-1]

    def walk_poly(self, wk):
        g = wk["_line"].buffer(wk["_w"] / 2, cap_style=2, join_style=2, mitre_limit=3)
        for extra in wk.get("_extra", []):
            g = g.union(extra)
        return g

    def ground_level(self, x, y):
        """Top of the walkable ground (not roofs) at a point."""
        pt = Point(x, y)
        for tb in self.stair_boxes:
            (x0, y0, _), (x1, y1, z1) = tb
            if x0 <= x <= x1 and y0 <= y <= y1:
                return z1
        if getattr(self, "_ground_p", None) is None:
            # prepared once the bridges exist; the water and the Pit never change
            self._ground_p = (prep(self.bridge_u), [(prep(w["g"]), w["bed"]) for w in self.waters], prep(self.PIT))
        bridge_p, waters_p, pit_p = self._ground_p
        if bridge_p.contains(pt):
            return STREET_Z
        for wp, bed in waters_p:
            if wp.contains(pt):
                return bed
        if pit_p.contains(pt):
            return self.pit_floor
        if self.paved_p.contains(pt):
            return PAVED_Z
        if self.plaza_p.contains(pt):
            return PLAZA_Z
        return STREET_Z

    def level_class(self, x, y):
        """Neighbour level for side-face decisions: +inf for buildings and off-map, -inf for water."""
        if not (0 <= x <= self.P.W and 0 <= y <= self.P.H):
            return math.inf
        pt = Point(x, y)
        if self.B_p.contains(pt):
            return math.inf
        if self.bridge_u.contains(pt):
            return STREET_Z
        if self.W_p.contains(pt):
            return -math.inf
        if self.PIT.contains(pt):
            return self.pit_floor
        if self.paved_p.contains(pt):
            return PAVED_Z
        if self.plaza_p.contains(pt):
            return PLAZA_Z
        return STREET_Z

    def water_bed(self, x, y):
        pt = Point(x, y)
        for w in self.waters:
            if w["g"].contains(pt):
                return w["bed"]
        return None

    def roof_at(self, x, y):
        pt = Point(x, y)
        for lot in self.lots:
            if lot["poly"].contains(pt):
                return lot["roof_z"]
        for b in self.named:
            if b.get("_h") is not None and b["_g"].contains(pt):
                return b["_roof_z"]
        return None

    def outward(self, pg, a, b, d=0.05):
        """Outward unit normal of edge a->b of polygon pg."""
        tx, ty = unit(b[0] - a[0], b[1] - a[1])
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        n1 = (ty, -tx)
        if pg.contains(Point(mx + n1[0] * d, my + n1[1] * d)):
            return (-n1[0], -n1[1])
        return n1

    def ring_edges(self, pg, ring):
        pts = ring_xy(ring)
        out = []
        for k in range(len(pts)):
            a, b = pts[k], pts[(k + 1) % len(pts)]
            if math.dist(a, b) < 1e-6:
                continue
            out.append((a, b))
        return out

    # prism with neighbour-aware sides ----------------------------------------
    def ground_prism(self, pg, z0, z1, mat, flip=False, side_top=None):
        """A ground piece. A side face is built only where the neighbour is lower (or, for
        flipped pits and canals, up to the neighbour's level via side_top)."""
        pg = oriented(pg)
        edges = []
        for ring in [pg.exterior] + list(pg.interiors):
            pts = ring_xy(ring.coords)
            spec = []
            for k in range(len(pts)):
                a, b = pts[k], pts[(k + 1) % len(pts)]
                if math.dist(a, b) < 1e-6:
                    spec.append(None)
                    continue
                n = self.outward(pg, a, b)
                mx, my = (a[0] + b[0]) / 2 + n[0] * 0.06, (a[1] + b[1]) / 2 + n[1] * 0.06
                if side_top:
                    spec.append(side_top(mx, my))
                else:
                    lv = self.level_class(mx, my)
                    spec.append([r4(z0), r4(z1)] if lv < z1 - 1e-6 else None)
            edges.append(spec)
        d = {"t": "prism", "rings": [ring_xy(pg.exterior.coords)] + [ring_xy(i.coords) for i in pg.interiors],
             "z0": r4(z0), "z1": r4(z1), "mat": mat, "caps": ["bottom"] if flip else ["top"], "flip": flip,
             "edges": edges, "tris": cap_tris(pg)}
        return d

    def chunked(self, g):
        """Split geometry by the chunk grid: [(i, j, polygon)]. Pieces come back without holes
        (cut open through each hole), because a cap with many holes is where triangulators fail."""
        out = []
        nx, ny = int(math.ceil(self.P.W / CHUNK_M)), int(math.ceil(self.P.H / CHUNK_M))
        for i in range(nx):
            for j in range(ny):
                cb = box(i * CHUNK_M, j * CHUNK_M, (i + 1) * CHUNK_M, (j + 1) * CHUNK_M)
                if not g.intersects(cb):
                    continue
                for pg in polys(g.intersection(cb)):
                    for q in self.open_holes(pg):
                        if q.area > 0.01:
                            out.append((i, j, q))
        return out

    @staticmethod
    def open_holes(pg):
        if not pg.interiors:
            return [pg]
        x0, y0, x1, y1 = pg.bounds
        cuts = [LineString([(h.centroid.x, y0 - 1), (h.centroid.x, y1 + 1)]) for h in (Polygon(r) for r in pg.interiors)]
        parts = polys(split(pg, MultiLineString(cuts)))
        out = []
        for q in parts:
            out += City.open_holes(q) if q.interiors and len(parts) > 1 else [q]
        return out

    # the foundation band and the lots ------------------------------------------
    def foundation(self):
        """The district whose style is "foundation": one massive wall along it, with buttresses."""
        self.F = Polygon()
        self.buttresses = []
        fd = next((d for d in self.m["districts"] if d.get("style") == "foundation"), None)
        if not fd:
            return
        band = Polygon(fd["poly"])
        self.fband = band
        x0, y0, x1, y1 = band.bounds
        face = y1 - 2.0
        named = unary_union([b["_g"].buffer(0.3, join_style=2) for b in self.named if b["id"] != "ferry"])
        self.F = box(x0, y0, x1, face).difference(self.W).difference(self.O).difference(named)
        self.fheight = fd.get("height_m", (40, 40))[1]
        self.fsector = self.P.sector_id(fd["name"])
        # buttresses every 14 m where the face is continuous behind them
        spans = []
        x = x0 + 7.0
        clear = self.W.union(self.O).union(named)
        while x < x1 - 2:
            bt = box(x - 1.45, face, x + 1.45, y1 + 0.25)
            if not bt.intersects(clear) and self.F.contains(box(x - 1.45, face - 0.5, x + 1.45, face - 0.01)):
                spans.append(x)
            x += 14.0
        self.fface = face
        self.bspans = spans

    def plan_lots(self):
        m = self.m
        blocked = RM.city_blocked(m, self.geo)
        clip = self.fband.buffer(0.3, join_style=2) if hasattr(self, "fband") else Polygon()
        vbuf = self.vfoot.buffer(1.0, join_style=2) if self.viaduct else Polygon()
        for i, lot in enumerate(RM.city_lots(m, blocked, RM.approach_cut(m, self.geo))):
            pg0 = lot["poly"]
            pieces = polys(pg0.difference(clip)) if pg0.intersects(clip) else polys(pg0)
            for k, pg in enumerate(pieces):
                if pg.area < 3:
                    continue
                if pg.buffer(-0.75, join_style=2).is_empty:
                    # a sliver under 1.5 m wide is a subdivision leftover, not a building: pave it
                    self.slivers.append(pg)
                    continue
                rp = pg.representative_point()
                d = self.P.district_at(rp.x, rp.y)
                style = d.get("style", "strip")
                if style == "foundation":
                    continue
                st = STYLES[style]
                rng = random.Random(f"{self.P.seed}:lot:{i}:{k}")
                lo, hi = d.get("height_m", (8, 14))
                h = round(rng.uniform(lo, hi) / 0.05) * 0.05
                parapet = st["parapet"]
                # clearances: under the Skyway and under walkways
                limit = math.inf
                if pg.intersects(vbuf):
                    limit = min(limit, 10.8 - 0.3)
                for wk in self.walkways:
                    corr = wk["_line"].buffer(wk["_w"] / 2 + 1.0, cap_style=2, join_style=2)
                    if pg.intersects(corr):
                        zs = [self.walk_z(wk, p.x, p.y) for p in self.samples(wk["_line"], 0.5)
                              if p.distance(pg) < wk["_w"] / 2 + 1.0]
                        if zs:
                            limit = min(limit, min(zs) - WALK_DECK - 0.3)
                            parapet = 0.0
                coping = 0.12 if parapet > 0 else 0.0
                if h + parapet + coping > limit:
                    h = max(3.2, round((limit - parapet - coping) / 0.05) * 0.05)
                roof = [it for it in lot["roof"] if pg.contains(Point(it[1], it[2]))]
                self.lots.append({"i": i, "k": k, "id": f"{i}" + (f"_{k}" if k else ""), "poly": pg, "district": d,
                                  "style": style, "h": h, "parapet": parapet, "roof_z": h, "limit": limit,
                                  "roof": roof, "rng": rng,
                                  "sector": self.P.sector_id(d["name"])})

    @staticmethod
    def samples(line, step):
        n = max(1, int(line.length / step))
        return [line.interpolate(line.length * q / n) for q in range(n + 1)]

    def buildings_union(self):
        parts = [lot["poly"] for lot in self.lots] + [b["_g"] for b in self.named if b["id"] != "ferry"]
        parts.append(self.F)
        for x in self.bspans:
            parts.append(box(x - 1.2, self.fface, x + 1.2, self.fband.bounds[3]))
        self.B = unary_union(parts)
        self.B_p = prep(self.B)

    # ground --------------------------------------------------------------------
    def bridges(self):
        self.bridge_list = []
        decks = []
        for sh in self.m.get("bridges", []):
            r = RM.shape_geom(sh)
            x0, y0, x1, y1 = r.bounds
            ext = {}
            for side, (mx, my, dx, dy) in {"n": ((x0 + x1) / 2, y0, 0, -1), "s": ((x0 + x1) / 2, y1, 0, 1),
                                          "w": (x0, (y0 + y1) / 2, -1, 0), "e": (x1, (y0 + y1) / 2, 1, 0)}.items():
                ext[side] = 0.0
                if self.W.contains(Point(mx, my)):
                    for q in range(1, 31):
                        if not self.W.contains(Point(mx + dx * q * 0.05, my + dy * q * 0.05)):
                            ext[side] = q * 0.05
                            break
            rb = box(x0 - ext["w"], y0 - ext["n"], x1 + ext["e"], y1 + ext["s"])
            deck = rb.intersection(self.W)
            # the axis the bridge crosses: both ends of it land on the bank
            bx0, by0, bx1, by1 = rb.bounds
            land = lambda x, y: not self.W.contains(Point(x, y))  # noqa: E731
            cross_x = land(bx0 - 0.4, (by0 + by1) / 2) and land(bx1 + 0.4, (by0 + by1) / 2)
            self.bridge_list.append({"rect": rb, "deck": deck, "cross_x": cross_x, "wide": min(bx1 - bx0, by1 - by0) > 6})
            decks.append(deck)
        self.bridge_u = unary_union(decks) if decks else Polygon()

    def pit_stairs(self):
        """Stairs from the lanes that end in the Pit: 0.25 m risers, the last tread is the floor."""
        self.pit_stair_list = []
        if self.PIT.is_empty:
            return
        drop = -self.pit_floor
        risers = int(round(drop / 0.25))
        rise = drop / risers
        for o in self.streets:
            ls = LineString(o["pts"])
            if not ls.intersects(self.PIT) or o["name"] == "rail":
                continue
            inter = ls.intersection(self.PIT.exterior)
            pts = [inter] if inter.geom_type == "Point" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "Point"]
            if not pts:
                continue
            E = pts[0]
            # direction of the lane where it enters the pit
            d_at = ls.project(E)
            a, b = ls.interpolate(max(d_at - 1.0, 0)), ls.interpolate(min(d_at + 1.0, ls.length))
            if self.PIT.contains(a):
                a, b = b, a
            dx, dy = b.x - a.x, b.y - a.y
            if abs(dx) >= abs(dy):
                ax, sgn = 0, (1 if dx > 0 else -1)
            else:
                ax, sgn = 1, (1 if dy > 0 else -1)
            width = min(o["w"], 3.5)
            c = (E.x, E.y)
            lat = 1 - ax
            lat0, lat1 = c[lat] - width / 2, c[lat] + width / 2
            # rim positions (along the stair axis) across the width
            rims = []
            for q in range(11):
                lv = lat0 + (lat1 - lat0) * q / 10
                probe = [0, 0]
                probe[lat] = lv
                for step in range(-60, 61):
                    probe[ax] = c[ax] + sgn * step * 0.05
                    if self.PIT.contains(Point(*probe)):
                        rims.append(sgn * (probe[ax] - c[ax]))
                        break
            if not rims:
                continue
            a_near, a_far = min(rims), max(rims)
            treads = []
            spans = [(a_near - 0.35, a_far + 0.3)] + [(a_far + 0.3 + 0.3 * (k - 1), a_far + 0.3 + 0.3 * k)
                                                      for k in range(1, risers - 1)]
            for k, (s0, s1) in enumerate(spans):
                top = -rise * (k + 1)
                u0, u1 = sorted((c[ax] + sgn * s0, c[ax] + sgn * s1))
                lo = [0, 0, self.pit_floor]
                hi = [0, 0, top]
                lo[ax], hi[ax] = u0, u1
                lo[lat], hi[lat] = lat0, lat1
                treads.append((tuple(lo), tuple(hi)))
            self.pit_stair_list.append({"treads": treads, "lat": (lat0, lat1), "ax": ax, "c": c, "name": o["name"]})
            self.stair_boxes += treads

    def ground(self):
        B = self.B
        band = B.buffer(SIDEWALK_M, join_style=2, mitre_limit=2).difference(B)
        walk_open = self.S.union(self.PLZ).difference(band)
        solid = self.R.difference(self.W).difference(self.PIT).difference(B)
        self.paved = solid.difference(walk_open)
        self.plaza = self.PLZ.difference(band).difference(self.W).difference(self.PIT).difference(B)
        self.street = self.S.difference(self.PLZ).difference(band).difference(self.W).difference(self.PIT).difference(B)
        self.paved_p, self.plaza_p, self.W_p = prep(self.paved), prep(self.plaza), prep(self.W)
        P = self.P
        flat = lambda x, y: None  # noqa: E731
        rail = self.street.intersection(self.rail_geom)
        road = self.street.difference(self.rail_geom)
        for g, z1, top, fn in ((road, STREET_Z, "asphalt", flat), (rail, STREET_Z, "concrete", flat),
                               (self.plaza, PLAZA_Z, "paving_wet", None), (self.paved, PAVED_Z, "paving_wet", None)):
            for i, j, pg in self.chunked(g):
                P.obj("streets", "walk", name=f"streets_walk_{i}_{j}", col="col").append(
                    self.ground_prism(pg, 0.0, z1, {"top": top, "side": "concrete", "bottom": "concrete"},
                                      side_top=fn))
        # the Pit: floor and walls up to street level
        pit = self.PIT
        pit_p = prep(pit)

        def pit_side(x, y):
            return None if pit_p.contains(Point(x, y)) else [r4(self.pit_floor), QUAY_Z]
        for i, j, pg in self.chunked(pit):
            P.obj("streets", "walk", name=f"streets_walk_{i}_{j}", col="col").append(
                self.ground_prism(pg, self.pit_floor, QUAY_Z, {"top": "concrete", "bottom": "concrete",
                                                               "side": "stone_blocks"}, flip=True, side_top=pit_side))
        for st in self.pit_stair_list:
            for lo, hi in st["treads"]:
                P.add("streets", "walk", lo[0], lo[1], box_prim(lo, hi, ["concrete", "diamond_plate", "concrete"]
                                                                + ["concrete"] * 3, skip=[0]), col="col")
                P.zdetail("exterior", lo, hi, f"pit stair {st['name']}")

    def water(self):
        P = self.P
        for wi, w in enumerate(self.waters):
            gp = prep(w["g"])

            def side(x, y, w=w, gp=gp):
                pt = Point(x, y)
                if gp.contains(pt) or not (0 <= x <= self.P.W and 0 <= y <= self.P.H):
                    return None     # the backdrop wall closes the canal at the map edge
                for o in self.waters:
                    if o is not w and o["g"].contains(pt):
                        return [r4(w["bed"]), r4(o["bed"])] if o["bed"] > w["bed"] + 1e-6 else None
                return [r4(w["bed"]), QUAY_Z]
            for i, j, pg in self.chunked(w["g"]):
                P.obj("streets", "walk", name=f"streets_walk_{i}_{j}", col="col").append(
                    self.ground_prism(pg, w["bed"], QUAY_Z, {"top": "concrete", "bottom": "stone_blocks",
                                                             "side": "stone_blocks"}, flip=True, side_top=side))
                P.obj("streets", "water", name=f"streets_water_{i}_{j}", extras=WATER_EXTRAS).append(
                    prism(pg, w["surface"], w["surface"], {"top": "water", "side": "water", "bottom": "water"}))

    def bridge_geometry(self):
        P = self.P
        for bi, br in enumerate(self.bridge_list):
            top = "concrete" if br["wide"] else "diamond_plate"
            for i, j, pg in self.chunked(br["deck"]):
                P.obj("streets", "walk", name=f"streets_walk_{i}_{j}", col="col").append(
                    self.ground_prism(pg, -BRIDGE_DECK, STREET_Z, {"top": top, "side": "rust_metal", "bottom": "rust_metal"}))
            x0, y0, x1, y1 = br["rect"].bounds
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            # two girders under the deck along the crossing, bearing on the quay walls
            for f in (0.25, 0.75):
                if br["cross_x"]:
                    gy = y0 + (y1 - y0) * f
                    P.add("streets", "walk", cx, cy, box_prim((x0 - 0.4, gy - 0.25, -BRIDGE_DECK - 0.7),
                                                              (x1 + 0.4, gy + 0.25, -BRIDGE_DECK), "rust_metal"), col="col")
                else:
                    gx = x0 + (x1 - x0) * f
                    P.add("streets", "walk", cx, cy, box_prim((gx - 0.25, y0 - 0.4, -BRIDGE_DECK - 0.7),
                                                              (gx + 0.25, y1 + 0.4, -BRIDGE_DECK), "rust_metal"), col="col")
            # railings where the deck edge faces water
            dg = oriented(br["deck"]) if br["deck"].geom_type == "Polygon" else None
            if dg is None:
                continue
            for a, b in self.ring_edges(dg, dg.exterior.coords):
                n = self.outward(dg, a, b)
                mx, my = (a[0] + b[0]) / 2 + n[0] * 0.3, (a[1] + b[1]) / 2 + n[1] * 0.3
                if self.W.contains(Point(mx, my)):
                    self.railing("streets", a, b, (-n[0], -n[1]), STREET_Z, "gunmetal")

    def railing(self, sector, a, b, inward, z, mat, inset=0.12, kind="walk", ends=True):
        """Posts and two rails along a->b, inset from the edge, standing at height z."""
        P = self.P
        L = math.dist(a, b)
        if L < 0.4:
            return
        t = unit(b[0] - a[0], b[1] - a[1])
        ax, ay = a[0] + inward[0] * inset, a[1] + inward[1] * inset
        bx, by = b[0] + inward[0] * inset, b[1] + inward[1] * inset
        mx, my = (ax + bx) / 2, (ay + by) / 2
        prims = P.obj(sector, kind, mx, my, col="col")
        n = max(1, int(math.ceil(L / 2.5)))
        for q in range(n + 1):
            if not ends and q in (0, n):
                continue
            f = q / n
            px, py = ax + (bx - ax) * f, ay + (by - ay) * f
            prims.append(obox(px, py, t[0], t[1], 0.035, 0.035, z, z + RAIL_H - 0.06, mat))
        for zz, th in ((z + RAIL_H - 0.06, 0.06), (z + 0.48, 0.04)):
            prims.append(beam((ax, ay, zz), (bx, by, zz), 0.06, th, mat))

    # facades ---------------------------------------------------------------------
    def facing(self, x, y):
        """What a facade point looks at: 'street' (open ground), 'water' or None (another building)."""
        pt = Point(x, y)
        if self.O.contains(pt) and not self.PIT.contains(pt):
            return "street"
        if self.W.contains(pt) or self.PIT.contains(pt):
            return "water"
        if self.paved_p.contains(pt) and not self.B_p.contains(pt):
            return "side"
        return None

    def window_mat(self, rng, st):
        if rng.random() < st["lit"]:
            return "window_lit_warm" if rng.random() < 0.6 else "window_lit_cool"
        if st is STYLES["shanty"] and rng.random() < 0.15:
            return "rust_metal"   # boarded up
        return "window_dark"

    def recess(self, P, s0, s1, z0, z1, depth, back, reveal):
        """Cutter for a recess in a facade: 0.3 m proud of the wall, `depth` into it.
        Faces: bottom = sill, top = head, side0 outside, side1/side3 jambs, side2 = the back."""
        return edge_box(P, s0, s1, 0.3, -depth, z0, z1, [reveal, reveal, reveal, reveal, back, reveal])

    def facade(self, sector, pg, z0, h, st, rng, key, cutters, rooms=False, doors=(), bid=None,
               allow=("windows", "front", "awning", "blade", "fire_escape"), openings=None):
        """Windows, shop fronts, awnings, blade signs and fire escapes on every edge of a building
        that faces open ground. Recesses are cutters (carved by the Blender boolean); the rest are
        additive details in the chunk's visual object. Returns the street edges. `openings`, when
        given, collects the ground floor's shop bays, shanty doors and roll-up and loading doors
        for dressing_doors ({"edge": index in the returned edges, "kind", "c", "w", "h", "back"});
        a shanty's door is left to it, where its dark recess once was."""
        Pn = self.P
        cx, cy = pg.representative_point().x, pg.representative_point().y
        vis = Pn.obj(sector, "vis", cx, cy)
        top_z = z0 + h
        reveal = "concrete"
        street_edges = []
        pgo = oriented(pg)
        for a, b in self.ring_edges(pgo, pgo.exterior.coords):
            L = math.dist(a, b)
            if L < 1.6:
                continue
            t = unit(b[0] - a[0], b[1] - a[1])
            n = self.outward(pgo, a, b)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            look = self.facing(mx + n[0] * 2.6, my + n[1] * 2.6) if z0 < 1 else "street"
            if look is None:
                continue
            P = frame(a, t, n)
            occupied = []
            edge_doors = []
            for d in doors:
                s = (d[0] - a[0]) * t[0] + (d[1] - a[1]) * t[1]
                off = (d[0] - a[0]) * n[0] + (d[1] - a[1]) * n[1]
                if -0.05 <= s <= L + 0.05 and abs(off) < 0.05:
                    w = d[2] if len(d) > 2 else 1.4
                    edge_doors.append((s - w / 2, s + w / 2))
            occupied += [(s0 - 0.3, s1 + 0.3, 3.2) for s0, s1 in edge_doors]
            ground = z0 < 1
            front = ground and look == "street" and "front" in allow
            # ground floor ------------------------------------------------------
            if front and not rooms and L >= 3.0:
                kind = st["front"]
                if kind == "shop" and L >= 4.0:
                    nshop = max(1, int(L // 7.5))
                    seg = L / nshop
                    for q in range(nshop):
                        w = min(seg - 1.4, rng.uniform(3.0, 5.0))
                        if w < 2.0:
                            continue
                        c = seg * (q + 0.5)
                        lit = rng.random() < 0.65
                        dark = "glass" if rng.random() < 0.5 else "rust_metal"   # a dark shop window or a shutter
                        back = ("window_lit_warm" if rng.random() < 0.6 else "window_lit_cool") if lit else dark
                        cutters.append(self.recess(P, c - w / 2, c + w / 2, FLOOR_Z, 3.05, 0.35, back, reveal))
                        occupied.append((c - w / 2 - 0.2, c + w / 2 + 0.2, 3.1))
                        if openings is not None:
                            openings.append({"edge": len(street_edges), "kind": "bay", "c": c, "w": w, "h": 3.05, "back": back})
                        if lit and "awning" in allow and rng.random() < st["awning"]:
                            s0, s1 = c - w / 2 - 0.2, c + w / 2 + 0.2
                            vis.append(hexa_pts([(*P(s0, 0.03), 3.29), (*P(s1, 0.03), 3.29), (*P(s1, 1.5), 2.94),
                                                 (*P(s0, 1.5), 2.94), (*P(s0, 0.03), 3.35), (*P(s1, 0.03), 3.35),
                                                 (*P(s1, 1.5), 3.0), (*P(s0, 1.5), 3.0)], "awning"))
                            Pn.cover([P(s0, 0.03), P(s1, 0.03), P(s1, 1.5), P(s0, 1.5)], 2.94, "shop awning")
                elif kind == "shanty":
                    c = rng.uniform(0.9, L - 0.9)
                    if openings is not None:
                        openings.append({"edge": len(street_edges), "kind": "shanty", "c": c})
                    else:
                        cutters.append(self.recess(P, c - 0.5, c + 0.5, FLOOR_Z, 2.3, 0.25, "window_dark", reveal))
                    occupied.append((c - 0.8, c + 0.8, 2.4))
                    if L >= 4.5:
                        c2 = c + 2.0 if c + 3.4 < L else c - 2.0
                        if 1.3 < c2 < L - 1.3:
                            lit = rng.random() < 0.5
                            cutters.append(self.recess(P, c2 - 1.1, c2 + 1.1, 0.9, 2.3, 0.2,
                                                       "window_lit_warm" if lit else "rust_metal", reveal))
                            occupied.append((c2 - 1.3, c2 + 1.3, 2.4))
                            if lit and "awning" in allow and rng.random() < st["awning"]:
                                s0, s1 = c2 - 1.3, c2 + 1.3
                                vis.append(hexa_pts([(*P(s0, 0.03), 2.59), (*P(s1, 0.03), 2.59), (*P(s1, 1.2), 2.29),
                                                     (*P(s0, 1.2), 2.29), (*P(s0, 0.03), 2.65), (*P(s1, 0.03), 2.65),
                                                     (*P(s1, 1.2), 2.35), (*P(s0, 1.2), 2.35)], "awning"))
                                Pn.cover([P(s0, 0.03), P(s1, 0.03), P(s1, 1.2), P(s0, 1.2)], 2.29, "shanty awning")
                elif kind in ("rollup", "loading") and L >= 5.0:
                    wd, hd = (3.6, 3.95) if kind == "rollup" else (3.2, 3.55)
                    nd = max(1, int(L // 6.5))
                    seg = L / nd
                    for q in range(nd):
                        c = seg * (q + 0.5)
                        cutters.append(self.recess(P, c - wd / 2, c + wd / 2, FLOOR_Z, hd, 0.25, "rust_metal", "hazard_stripes"))
                        occupied.append((c - wd / 2 - 0.2, c + wd / 2 + 0.2, hd + 0.1))
                        if openings is not None:
                            openings.append({"edge": len(street_edges), "kind": kind, "c": c, "w": wd, "h": hd})
            street_edges.append((a, b, t, n, L, occupied, look))
        # upper floor windows on every edge that looks at open ground ----------------
        for a, b in self.ring_edges(pgo, pgo.exterior.coords):
            L = math.dist(a, b)
            if L < 1.6:
                continue
            t = unit(b[0] - a[0], b[1] - a[1])
            n = self.outward(pgo, a, b)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            look = self.facing(mx + n[0] * 2.6, my + n[1] * 2.6) if z0 < 1 else "street"
            if look is None or "windows" not in allow:
                continue
            P = frame(a, t, n)
            ww, wh = st["win"]
            if z0 >= 1:     # a box stacked on a roof: one row
                ww, wh = min(ww, 0.9), 0.9
            pitch = rng.uniform(*st["pitch"])
            ncol = int((L - 1.2) // pitch)
            if ncol == 0 and L - 1.2 >= ww + 0.2:
                ncol = 1
            if ncol == 0:
                continue
            if z0 >= 1:
                sills = [z0 + 0.9]
            else:
                sills = []
                k = 1
                while True:
                    zf = st["ground_h"] + (k - 1) * st["floor_h"]
                    sill = zf + st["sill"]
                    if rooms:
                        sill = max(sill, FLOOR_Z + ROOM_H + 0.35)
                    if sill + wh > top_z - 0.4:
                        break
                    sills.append(sill)
                    k += 1
            for sill in sills:
                for q in range(ncol):
                    c = L / 2 + (q - (ncol - 1) / 2) * pitch
                    cutters.append(self.recess(P, c - ww / 2, c + ww / 2, sill, sill + wh, 0.18,
                                               self.window_mat(rng, st), reveal))
        return street_edges

    def building_details(self, sector, pg, z0, h, st, rng, edges, cap_mat, parapet, allow_blade=True,
                         allow_fire=True, limit=math.inf):
        """String course, coping, blade signs and fire escapes."""
        Pn = self.P
        cx, cy = pg.representative_point().x, pg.representative_point().y
        vis = Pn.obj(sector, "vis", cx, cy)
        if st["band"] and z0 < 1 and h > st["ground_h"] + 1:
            zb = st["ground_h"] - 0.35
            ring = pg.buffer(0.12, join_style=2, mitre_limit=2).difference(pg)
            for rp in polys(ring):
                vis.append(prism(rp, zb, zb + 0.25, {"top": cap_mat, "bottom": cap_mat, "side": cap_mat},
                                 caps=["top", "bottom"]))
        if parapet > 0:
            inner = pg.buffer(-0.36, join_style=2)
            ring = pg.buffer(0.08, join_style=2, mitre_limit=2).difference(inner)
            zc = z0 + h + parapet
            for rp in polys(ring):
                vis.append(prism(rp, zc, zc + 0.12, {"top": cap_mat, "bottom": cap_mat, "side": cap_mat},
                                 caps=["top", "bottom"]))
        fronts = [e for e in edges if e[6] == "street" and e[4] >= 4.0]
        if not fronts or z0 >= 1:
            return
        # a blade sign or a fire escape, one feature per building
        e = fronts[int(rng.random() * len(fronts))]
        a, b, t, n, L, occupied, _ = e
        P = frame(a, t, n)
        roll = rng.random()
        if allow_blade and roll < st["blade"] and h >= 8.5:
            word = BLADE_WORDS[int(rng.random() * len(BLADE_WORDS))]
            size = 0.62
            zs = st["ground_h"] + 0.5
            hs = min(len(word) * size * 1.12 + 0.5, z0 + h - 0.6 - zs)
            if hs < 1.6:
                return
            nletters = max(1, min(len(word), int((hs - 0.5) / (size * 1.12))))
            word = word[:nletters]
            s = 0.9 if rng.random() < 0.5 else L - 0.9
            col = "pink" if rng.random() < 0.5 else "cyan"
            neon = "neon_pink" if col == "pink" else "neon_cyan"
            vis.append(edge_box(P, s - 0.12, s + 0.12, 0.08, 1.3, zs, zs + hs, "gunmetal"))
            # neon border on both faces
            for side in (-1, 1):
                sf = s + side * 0.12
                s_out = sf + side * 0.04
                s0, s1 = sorted((sf, s_out))
                for (o0, o1, za, zb) in ((0.12, 1.26, zs + 0.04, zs + 0.1), (0.12, 1.26, zs + hs - 0.1, zs + hs - 0.04),
                                         (1.2, 1.26, zs + 0.1, zs + hs - 0.1)):
                    vis.append(edge_box(P, s0, s1, o0, o1, za, zb, neon))
                letters = "\n".join(word)
                px, py = P(s_out, 0.66)
                heading = heading_of(t[0] * side, t[1] * side)
                vis.append(text(letters, px, py, zs + hs - 0.3 - nletters * size * 1.12, heading, size, neon, 0.05))
            lx, ly = P(s, 1.55)
            Pn.light(sector, col, lx, ly, zs + hs / 2)
            vis.append(edge_box(P, s - 0.06, s + 0.06, 1.3, 1.36, zs + hs / 2 - 0.25, zs + hs / 2 + 0.25, neon))
        elif allow_fire and roll < st["blade"] + st["fire_escape"] and h >= 7.5 and L >= 4.6:
            s0 = rng.uniform(0.6, L - 4.0)
            s1 = s0 + 3.2
            tops = []
            k = 1
            while True:
                zf = st["ground_h"] + (k - 1) * st["floor_h"] + 0.1
                if zf > z0 + h - 1.2 or zf + 1.1 > limit:
                    break
                tops.append(zf)
                k += 1
            for qi, zt in enumerate(tops):
                vis.append(edge_box(P, s0, s1, 0.16, 1.26, zt - 0.08, zt, ["diamond_plate", "diamond_plate"] + ["rust_metal"] * 4))
                vis.append(edge_box(P, s0, s1, 1.2, 1.26, zt + 0.94, zt + 1.0, "rust_metal"))
                for sp in (s0 + 0.03, (s0 + s1) / 2, s1 - 0.03):
                    vis.append(edge_box(P, sp - 0.03, sp + 0.03, 1.2, 1.26, zt, zt + 0.94, "rust_metal"))
                for sp, lo_, hi_ in ((s0, s0 + 0.04, s0 + 0.06), (s1, s1 - 0.06, s1 - 0.04)):
                    vis.append(edge_box(P, lo_, hi_, 0.16, 1.2, zt + 0.94, zt + 1.0, "rust_metal"))
                if qi + 1 < len(tops):
                    zn = tops[qi + 1]
                    a3 = (*P(s1 - 0.4, 0.95), zt)
                    b3 = (*P(s0 + 0.9, 0.95), zn - 0.06)
                    vis.append(beam(a3, b3, 0.55, 0.06, "rust_metal"))
            if tops:
                zt = tops[0]
                for off in (0.72, 1.18):
                    vis.append(edge_box(P, s1 - 0.5, s1 - 0.46, off - 0.02, off + 0.02, max(2.4, zt - 2.2), zt - 0.08, "rust_metal"))
                return {"edge": e, "s": (s1 - 0.5, s1 - 0.46)}   # the drop ladder, for dressing_doors
        return None

    # named buildings ---------------------------------------------------------------
    def clearance(self, pg):
        """Highest a building's top may reach: under the Skyway's pier caps, and under any
        walkway that crosses it. A walkway that starts or ends on the building lands on it
        instead, so it doesn't lower it."""
        limit = math.inf
        if self.viaduct and pg.intersects(self.vfoot.buffer(1.0, join_style=2)):
            limit = 10.8 - 0.3
        for wk in self.walkways:
            corr = wk["_line"].buffer(wk["_w"] / 2 + 1.0, cap_style=2, join_style=2)
            lands = any(pg.buffer(0.5).contains(Point(*e)) for e in (wk["pts"][0], wk["pts"][-1]))
            if pg.intersects(corr) and not lands:
                zs = [self.walk_z(wk, p.x, p.y) for p in self.samples(wk["_line"], 0.5)
                      if p.distance(pg) < wk["_w"] / 2 + 1.0]
                if zs:
                    limit = min(limit, min(zs) - WALK_DECK - 0.3)
        return limit

    def named_buildings(self):
        self.named_info = {}
        for bi, b in enumerate(self.named):
            if b["id"] == "ferry":
                self.ferry(b)
            else:
                self.named_building(bi, b)

    def door_boxes(self, b):
        """Door openings as air boxes, carved at each door's fits (its clear opening plus REVEAL at
        the jambs and the head; openspec/changes/hub-doorways, design section 3.1):
        (x0, x1, y0, y1, carved height, exterior, (x, y, w), door), the door as
        render_map.named_doors classifies it."""
        pg = b["_g"]
        fx0, fy0, fx1, fy1 = pg.bounds
        out = []
        for d in RM.named_doors(b):
            x, y, w, ext = d["x"], d["y"], d["w"], d["exterior"]
            fw, fh = detailing.door_fits(w, self.clear_h(w))
            if d["along"] == "x":
                if ext:
                    y0, y1 = (fy0 - 0.4, fy0 + WALL_T + 0.05) if abs(y - fy0) < 0.01 else (fy1 - WALL_T - 0.05, fy1 + 0.4)
                else:
                    y0, y1 = y - WALL_T / 2 - 0.05, y + WALL_T / 2 + 0.05
                out.append((x - fw / 2, x + fw / 2, y0, y1, fh, ext, (x, y, w), d))
            else:
                if ext:
                    x0, x1 = (fx0 - 0.4, fx0 + WALL_T + 0.05) if abs(x - fx0) < 0.01 else (fx1 - WALL_T - 0.05, fx1 + 0.4)
                else:
                    x0, x1 = x - WALL_T / 2 - 0.05, x + WALL_T / 2 + 0.05
                out.append((x0, x1, y - fw / 2, y + fw / 2, fh, ext, (x, y, w), d))
        return out

    @staticmethod
    def clear_h(w):
        """A door's clear height: DOOR_H, or WIDE_DOOR_H for an opening 2.5 m wide or wider."""
        return WIDE_DOOR_H if w >= 2.5 else DOOR_H

    def frame_door(self, b, sector, dd, airs, cx, cy):
        """Frames one of a named building's doors by detailing.door_frame (openspec/changes/
        hub-doorways, design section 3.2): liners, the threshold and the inside architrave go in
        the interior object, the outside face's architrave, or an entrance's portal and its lit
        downlight, in the building's own; every box is a z-fighting detail of the building."""
        P = self.P
        x0, x1, y0, y1, fh, ext, (x, y, w), d = dd
        bid = b["id"]
        ch = self.clear_h(w)
        fx0, fy0, fx1, fy1 = b["_g"].bounds
        horiz = d["along"] == "x"
        if ext:
            v0 = (fy0 if d["n"][1] < 0 else fy1) if horiz else (fx0 if d["n"][0] < 0 else fx1)
            vdir = -(d["n"][1] if horiz else d["n"][0])
        else:
            v0, vdir = ((y if horiz else x) - WALL_T / 2), 1.0
        out = "portal" if d["entrance"] else "architrave"
        style = b.get("frame_style") or self.style_of(b)
        boxes = detailing.door_frame(w, ch, WALL_T, out=out, inside="architrave", step=STANDING_STEP_M,
                                     mat=FRAME_MATS[style])
        accents = FRAME_ACCENTS.get(style, {})
        u_axis, v_axis = (0, 1) if horiz else (1, 0)
        face_of = {"-z": 0, "+z": 1, "-y": 2, "+x": 3, "+y": 4, "-x": 5}
        inner = P.obj(sector, "interior", name=f"interior_{bid}", col="col")
        outer = P.obj(sector, "walk", cx, cy, col="col")
        tris = 0
        for k, bx in enumerate(boxes):
            lo, hi = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
            lo[u_axis], hi[u_axis] = (x if horiz else y) + bx["lo"][0], (x if horiz else y) + bx["hi"][0]
            va, vb = v0 + vdir * bx["lo"][1], v0 + vdir * bx["hi"][1]
            lo[v_axis], hi[v_axis] = min(va, vb), max(va, vb)
            lo[2], hi[2] = FLOOR_Z + bx["lo"][2], FLOOR_Z + bx["hi"][2]
            skip = []
            for dirn in bx["buried"]:
                sign, ax = dirn[0], dirn[1]
                if ax == "z":
                    skip.append(face_of[dirn])
                    continue
                world = "xy"[u_axis] if ax == "u" else "xy"[v_axis]
                if ax == "v" and vdir < 0:
                    sign = "-" if sign == "+" else "+"
                skip.append(face_of[sign + world])
            outside = ext and bx["hi"][1] <= 1e-9
            mat = accents.get(bx["part"], bx["mat"])
            (outer if outside else inner).append(box_prim(tuple(lo), tuple(hi), mat, skip=sorted(skip)))
            P.zdetail(bid, tuple(lo), tuple(hi), f"{bid} door {d['i']} {bx['part']} {k}")
            tris += 2 * (6 - len(skip))
            if bx["part"] == "downlight":
                lx, ly = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
                P.light(sector, "door", lx, ly, lo[2] - 0.3, corona_at=(lx, ly, lo[2] - 0.03))
        # Wall enough for the frame, on each face: to the room's corner inside, the footprint's outside.
        half = {f: detailing.frame_outer_width(w, kind) / 2 for f, kind in (("out", out), ("in", "architrave"))}
        spans = []
        along = x if horiz else y
        for a in airs:
            ar_u = a.x if horiz else a.z
            ar_v = a.z if horiz else a.x
            wall = y if horiz else x
            if ar_u[0] - 0.01 <= along <= ar_u[1] + 0.01 and min(abs(ar_v[0] - wall), abs(ar_v[1] - wall)) <= WALL_T + 0.01:
                spans.append((min(along - ar_u[0], ar_u[1] - along), half["in"]))
        if ext:
            spans.append((min(along - (fx0 if horiz else fy0), (fx1 if horiz else fy1) - along), half["out"]))
        margin = min((room - need for room, need in spans), default=-math.inf)
        self.frames[(bid, d["i"])] = {"door": (x, y, w), "clear": (w, ch), "carved": (x1 - x0 if horiz else y1 - y0, fh),
                                      "kind": out, "tris": tris, "wall": margin}
        if ext:
            self.shown_doors.append((bid, x, y))

    def sliding_entrance(self, b, sector, dd):
        """A public entrance's automatic sliding door (owner K2; openspec/changes/hub-doorways,
        design section 3.3): the game's scene for its size and face (detailing.SLIDING_LEAVES), at
        the building's inside face, and where its two leaves stand when open, which the room's
        trims keep clear of and check_sliding_room checks."""
        x, y, w = dd[6]
        d = dd[7]
        ch = self.clear_h(w)
        face = b.get("leaves", "glazed")
        if (w, ch, face) not in detailing.SLIDING_LEAVES:
            raise SystemExit(f"{b['id']} door {d['i']}: no {face} sliding door {w:g} x {ch:g} m in detailing.SLIDING_LEAVES")
        nx, ny = d["n"]
        ix, iy = x - nx * WALL_T, y - ny * WALL_T          # the inside face, the door's middle
        tx, ty = -ny, nx
        sweeps, keep = [], []
        for u0, u1, v0, v1, z0, z1 in detailing.sliding_sweep(w, ch):
            xs = [ix + tx * u - nx * v for u in (u0, u1) for v in (v0, v1)]
            ys = [iy + ty * u - ny * v for u in (u0, u1) for v in (v0, v1)]
            sweeps.append((min(xs), min(ys), FLOOR_Z + z0, max(xs), max(ys), FLOOR_Z + z1))
            keep.append(((min(xs), FLOOR_Z + z0, min(ys)), (max(xs), FLOOR_Z + z1, max(ys))))
        tag = detailing.sliding_tag(w, ch, face)
        self.P.entity(sector, f"ENT_sliding_door_{b['id']}_{d['i']}", ix, iy, FLOOR_Z, heading_of(nx, ny),
                      {"kind": "sliding_door", "id": f"{b['id']}_{d['i']}", "leaf": tag})
        return {"building": b, "door": d, "tag": tag, "sweeps": sweeps, "keep": keep}

    def sliding_room_problems(self):
        """Every sliding leaf has room to open ("Public entrances open as you walk up"): where it
        stands open lies inside the building's rooms, and meets no fixture and no detail (a trim,
        a counter, another door's frame)."""
        problems = []
        for sl in self.sliding:
            b, d = sl["building"], sl["door"]
            room_air = unary_union([box(a.x[0], a.z[0], a.x[1], a.z[1]) for a in sl["airs"]]).buffer(1e-6)
            height = max(a.y[1] for a in sl["airs"])
            fixtures = [(fx[-1], RM.shape_geom(fx)) for fx in b.get("fixtures", []) if fx[-1] not in WALK_THROUGH_CLASSES]
            details = self.P.zboxes.get(b["id"], {"details": []})["details"]
            for k, (x0, y0, z0, x1, y1, z1) in enumerate(sl["sweeps"]):
                name = f"{b['id']} door {d['i']} at ({d['x']:g}, {d['y']:g}), its {'left' if k == 0 else 'right'} leaf"
                fp = box(x0, y0, x1, y1)
                if not room_air.contains(fp) or z1 > height:
                    over = fp.difference(room_air)
                    problems.append(f"{name} meets a wall: {max(over.bounds[2] - over.bounds[0], over.bounds[3] - over.bounds[1]):.2f} m "
                                    "of its open position is outside the rooms" if not over.is_empty else f"{name} is taller than the room")
                hits = [cls for cls, g in fixtures if g.intersection(fp).area > 1e-6]
                for lo, hi, label in details:
                    # stored as (x, up, y)
                    if min(hi[0], x1) - max(lo[0], x0) > 1e-4 and min(hi[2], y1) - max(lo[2], y0) > 1e-4 \
                            and min(hi[1], z1) - max(lo[1], z0) > 1e-4:
                        hits.append(label)
                if hits:
                    problems.append(f"{name} meets {', '.join(sorted(set(hits))[:4])}")
        return problems

    def style_of(self, b):
        """The facade style of a named building's district."""
        rp = b["_g"].representative_point()
        style = self.P.district_at(rp.x, rp.y).get("style", "strip")
        return "strip" if style == "foundation" else style

    def named_building(self, bi, b):
        P = self.P
        pg = b["_g"]
        bid = b["id"]
        rp = pg.representative_point()
        d = P.district_at(rp.x, rp.y)
        style = d.get("style", "strip")
        if style == "foundation":
            style = "strip"
        st = STYLES[style]
        sector = P.sector_id(d["name"])
        rng = random.Random(f"{P.seed}:bld:{bid}")
        h = float(b.get("height_m", 9))
        parapet = st["parapet"] if st["parapet"] > 0 else 0.0
        limit = self.clearance(pg)
        if h + parapet + 0.12 > limit:
            h = round((limit - parapet - 0.12) / 0.05) * 0.05
            if b.get("rooms") and h < FLOOR_Z + ROOM_H + 0.6:
                raise SystemExit(f"{bid}: something overhead caps it at {h:.2f} m, below its own ceiling")
        b["_h"] = h
        b["_roof_z"] = h
        P.shelter(pg, h, bid)
        facade_mat = b.get("facade") or st["facade"][int(rng.random() * len(st["facade"]))]
        cap = st["cap"]
        cx, cy = pg.centroid.x, pg.centroid.y
        rooms = b.get("rooms", [])
        walls, floor_m, ceil_m, trim = b.get("finish") or FINISH[style]
        cutters = []
        solid = prism(pg, 0.0, h + parapet, {"side": facade_mat, "top": cap, "bottom": facade_mat},
                      caps=["top", "bottom"])
        if parapet > 0:
            inner = pg.buffer(-0.3, join_style=2)
            cutters.append(prism(inner, h, h + parapet + 2.0, {"top": "concrete", "bottom": st["roof"], "side": "concrete"},
                                 caps=["top", "bottom"]))
        # roof run landings: a gap in the parapet where a walkway arrives
        for wk in self.walkways:
            if wk.get("hung"):
                continue
            line = wk["_line"]
            if line.intersects(pg.exterior) and parapet > 0:
                for q in polys(line.buffer(wk["_w"] / 2 + 0.15, cap_style=2).intersection(pg.buffer(0.5).difference(pg.buffer(-0.6)))):
                    cutters.append(prism(q, h, h + parapet + 2.0, {"top": "concrete", "bottom": st["roof"], "side": "concrete"},
                                         caps=["top", "bottom"]))
        doors = self.door_boxes(b)
        interior = None
        airs, door_airs = [], []
        if rooms:
            fx0, fy0, fx1, fy1 = pg.bounds
            for ri, r in enumerate(rooms):
                x0, y0, x1, y1 = r["rect"]
                ax0 = x0 + (WALL_T if abs(x0 - fx0) < 0.01 else WALL_T / 2)
                ax1 = x1 - (WALL_T if abs(x1 - fx1) < 0.01 else WALL_T / 2)
                ay0 = y0 + (WALL_T if abs(y0 - fy0) < 0.01 else WALL_T / 2)
                ay1 = y1 - (WALL_T if abs(y1 - fy1) < 0.01 else WALL_T / 2)
                room = detailing.Room(f"{bid}:{r.get('name') or ri}", (ax0, ax1), (FLOOR_Z, FLOOR_Z + ROOM_H), (ay0, ay1),
                                      trim, trims=True, beams=True, ceiling=ceil_m)
                airs.append(room)
                cutters.append(box_prim((ax0, ay0, FLOOR_Z), (ax1, ay1, FLOOR_Z + ROOM_H),
                                        [floor_m, ceil_m, walls, walls, walls, walls]))
            for di, (x0, x1, y0, y1, dh, ext, _, _) in enumerate(doors):
                door_airs.append(detailing.Room(f"{bid}:door{di}", (x0, x1), (FLOOR_Z, FLOOR_Z + dh), (y0, y1), trim,
                                                trims=False, beams=False))
                cutters.append(box_prim((x0, y0, FLOOR_Z), (x1, y1, FLOOR_Z + dh),
                                        [floor_m, walls, "tech_panel", "tech_panel", "tech_panel", "tech_panel"]))
            iname = f"interior_{bid}"
            interior = {"object": iname + "-col",
                        "boxes": [[p3(a.x[0] - 0.02, a.z[0] - 0.02, a.y[0] - 0.02), p3(a.x[1] + 0.02, a.z[1] + 0.02, a.y[1] + 0.02)]
                                  for a in airs + door_airs]}
            P.obj(sector, "interior", col="col", extras=INTERIOR_EXTRAS, origin=(cx, cy, FLOOR_Z), name=iname)
            self.P.rooms_out.append({"building": bid, "sector": sector,
                                     "rooms": [[a.x[0], a.x[1], a.y[0], a.y[1], a.z[0], a.z[1]] for a in airs]})
            self.P.probes.append({"name": f"Ref_{bid}", "sector": sector, "box": [pg.bounds[0], pg.bounds[2], FLOOR_Z,
                                                                               FLOOR_Z + ROOM_H, pg.bounds[1], pg.bounds[3]]})
        # sign over the main entrance (or the longest street front)
        ext_doors = [dd for dd in doors if dd[5]]
        sign = None
        name = b.get("name", "")
        if name and b.get("label", True) is not False:
            sign = self.sign_spot(b, pg, ext_doors, st, h)
        ext_door_pts = [dd[6] for dd in ext_doors]
        # The parapet, landings, rooms and doors are structure; only the facade's own recesses
        # (windows) make way for a sign. (Dropping every cutter in the sign's zone once left the
        # Tsang Shrine's hall uncarved: a solid block with Sister Lin standing inside it.)
        structure = len(cutters)
        edges = self.facade(sector, pg, 0.0, h, st, rng, bid, cutters, rooms=bool(rooms), doors=ext_door_pts, bid=bid,
                            allow=("windows",) if rooms else ("windows", "front"))
        if sign:
            cutters[structure:] = [c for c in cutters[structure:] if not self.cutter_hits(c, sign["zone"])]
        ext_obj = P.obj(sector, "walk", cx, cy, col="col")
        ext_obj.append({"t": "bool", "solid": solid, "cutters": cutters, "interior": interior})
        self.building_details(sector, pg, 0.0, h, st, rng, edges, cap, parapet, allow_blade=False, allow_fire=False)
        if sign:
            self.put_sign(sector, sign, bi)
        # fixtures and interior detail
        if rooms:
            sliding = [self.sliding_entrance(b, sector, dd) for dd in doors if dd[7]["entrance"]]
            self.interior_detail(b, sector, airs, door_airs, trim, ceil_m, avoid=[k for sl in sliding for k in sl["keep"]])
            for dd in doors:
                self.frame_door(b, sector, dd, airs, cx, cy)
            self.sliding += [{**sl, "airs": airs} for sl in sliding]
        for fx in b.get("fixtures", []):
            self.fixture(sector, fx, b if rooms else None, bid)
        self.P.zgroup(bid)["airs"] += airs + door_airs
        self.named_info[bid] = {"sector": sector, "h": h, "edges": edges}
        for e in edges:
            self.facades.append((sector, e, h))

    @staticmethod
    def cutter_hits(c, zone):
        if c.get("t") != "hexa":
            return False
        xs = [p[0] for p in c["p"]]
        ys = [p[1] for p in c["p"]]
        zs = [p[2] for p in c["p"]]
        x0, y0, z0, x1, y1, z1 = zone
        return min(xs) < x1 and max(xs) > x0 and min(ys) < y1 and max(ys) > y0 and min(zs) < z1 and max(zs) > z0

    def sign_spot(self, b, pg, ext_doors, st, h):
        pgo = oriented(pg)
        cands = []
        for a, bb in self.ring_edges(pgo, pgo.exterior.coords):
            L = math.dist(a, bb)
            t = unit(bb[0] - a[0], bb[1] - a[1])
            n = self.outward(pgo, a, bb)
            mx, my = (a[0] + bb[0]) / 2, (a[1] + bb[1]) / 2
            look = self.facing(mx + n[0] * 2.6, my + n[1] * 2.6)
            door = None
            for dd in ext_doors:
                x, y, w = dd[6]
                s = (x - a[0]) * t[0] + (y - a[1]) * t[1]
                off = (x - a[0]) * n[0] + (y - a[1]) * n[1]
                if -0.05 <= s <= L + 0.05 and abs(off) < 0.05 and (door is None or w > door[1]):
                    top = detailing.frame_top(self.clear_h(w), "portal" if dd[7]["entrance"] else "architrave")
                    door = (s, w, top)
            score = (door[1] + 100 if door else 0) + (L if look == "street" else L * 0.1)
            cands.append((score, a, bb, t, n, L, door))
        score, a, bb, t, n, L, door = max(cands, key=lambda c: c[0])
        lines = b["name"].split("\n")
        chars = max(len(x) for x in lines)
        size = min(1.0, max(0.45, (L - 1.5) / (0.72 * chars)))
        z0 = max(st["ground_h"] + 0.2 if st["band"] else 0.0, (FLOOR_Z + door[2] + 0.2) if door else 3.2, 3.3)
        tall = len(lines) * size * 1.2
        if z0 + tall > h - 0.3:
            size = max(0.4, (h - 0.3 - z0) / (len(lines) * 1.2))
            tall = len(lines) * size * 1.2
        s = door[0] if door else L / 2
        width = chars * size * 0.72
        s = min(max(s, width / 2 + 0.4), L - width / 2 - 0.4)
        P = frame(a, t, n)
        x0, y0 = P(s - width / 2 - 0.3, -0.5)
        x1, y1 = P(s + width / 2 + 0.3, 0.5)
        zone = (min(x0, x1), min(y0, y1), z0 - 0.2, max(x0, x1), max(y0, y1), z0 + tall + 0.2)
        return {"lines": lines, "size": size, "z0": z0, "s": s, "a": a, "t": t, "n": n, "zone": zone,
                "heading": heading_of(*n)}

    def put_sign(self, sector, sg, bi):
        mat, light = SIGN_COLOURS[bi % len(SIGN_COLOURS)]
        P = frame(sg["a"], sg["t"], sg["n"])
        px, py = P(sg["s"], 0.06)
        vis = self.P.obj(sector, "vis", px, py)
        vis.append(text("\n".join(sg["lines"]), px, py, sg["z0"], sg["heading"], sg["size"], mat, 0.08))
        tall = len(sg["lines"]) * sg["size"] * 1.2
        lx, ly = P(sg["s"], 1.3)
        self.P.light(sector, light, lx, ly, sg["z0"] + tall / 2)

    def interior_detail(self, b, sector, airs, door_airs, trim, ceil_m, avoid=()):
        """UT99 trims from tools/godot/detailing.py, and ceiling lights in the bays between girders."""
        P = self.P
        prims = P.obj(sector, "interior", name=f"interior_{b['id']}", col="col")
        keep = []
        for room in airs:
            (x0, x1), (_, y1), (z0, z1) = room.x, room.y, room.z
            area = (x1 - x0) * (z1 - z0)
            nl = 1 if area < 50 else (2 if area < 200 else 3)
            span_x = x1 - x0 <= z1 - z0
            walls4 = detailing.walls(room)
            long_wall = walls4[2] if span_x else walls4[0]
            ts = detailing.pilaster_positions(room, long_wall)
            t0, t1 = long_wall[4]
            cuts = [t0] + ts + [t1]
            bays = [((cuts[k] + cuts[k + 1]) / 2) for k in range(len(cuts) - 1)]
            if len(bays) > nl:
                pick = [bays[int((q + 0.5) * len(bays) / nl)] for q in range(nl)]
            else:
                pick = bays if len(bays) <= nl else bays[:nl]
                if len(bays) == 1 and nl > 1:
                    L = t1 - t0
                    pick = [t0 + L * (q + 0.5) / nl for q in range(nl)]
            for tpos in pick:
                gx, gz = (((x0 + x1) / 2, tpos) if span_x else (tpos, (z0 + z1) / 2))
                heading = 90.0 if span_x else 0.0
                P.lamp_entity(sector, "ceiling_light", gx, gz, y1 - 0.07, heading)
                half = (0.2, 0.1, 0.8) if span_x else (0.8, 0.1, 0.2)
                keep.append(detailing.keep_out((gx, y1 - 0.05, gz), half))
        for lo, hi, mat in detailing.all_trims(airs, airs + door_airs, keep + list(avoid)):
            L0, L1 = (lo[0], lo[2], lo[1]), (hi[0], hi[2], hi[1])
            prims.append(box_prim(L0, L1, mat))
            P.zdetail(b["id"], L0, L1, f"trim {mat}")

    def ferry(self, b):
        """A derelict ship in a basin: a lofted hull, a deckhouse, a bridge and a funnel."""
        P = self.P
        pg = oriented(b["_g"])
        c = pg.centroid
        w = next((wb for wb in self.waters if wb["g"].contains(c)), self.waters[0])
        s = w["surface"]
        sector = P.district_sector(c.x, c.y)
        prims = P.obj(sector, "walk", c.x, c.y, col="col")
        top = ring_xy(pg.exterior.coords)
        mid = ring_xy(affinity.scale(pg, 0.97, 0.97, origin=c).exterior.coords)
        bot = ring_xy(affinity.scale(pg, 0.72, 0.85, origin=c).exterior.coords)
        deck = s + SHIP_DECK_ABOVE_M
        prims.append({"t": "loft", "rings": [bot, mid, top], "z": [r4(s - 2.0), r4(s + 0.4), r4(deck)],
                      "mat": {"top": "diamond_plate", "bottom": "rust_metal", "side": "rust_metal"}})
        x0, y0, x1, y1 = pg.bounds
        # the deckhouse sits aft (the end away from the bow point), two storeys and a funnel
        stern_y = y0 if abs(c.y - y0) < abs(c.y - y1) else y1
        sgn = 1 if stern_y == y0 else -1
        ya, yb = sorted((stern_y + sgn * 2.0, stern_y + sgn * 10.0))
        house = box(x0 + 2.2, ya, x1 - 2.2, yb)
        cutters = []
        rng = random.Random(f"{P.seed}:ferry")
        self.facade(sector, house, deck, 3.0, STYLES["dock"], rng, "ferry", cutters, allow=("windows",))
        prims.append({"t": "bool", "solid": prism(house, deck, deck + 3.0, {"side": "tech_panel", "top": "rust_metal",
                                                                          "bottom": "rust_metal"}, caps=["top", "bottom"]),
                      "cutters": cutters, "interior": None})
        bridge = box(x0 + 3.0, ya + (1.0 if sgn > 0 else 3.0), x1 - 3.0, yb - (3.0 if sgn > 0 else 1.0))
        cutters = []
        self.facade(sector, bridge, deck + 3.0, 2.4, STYLES["dock"], rng, "ferry_b", cutters, allow=("windows",))
        prims.append({"t": "bool", "solid": prism(bridge, deck + 3.0, deck + 5.4, {"side": "tech_panel", "top": "rust_metal",
                                                                                 "bottom": "rust_metal"}, caps=["top", "bottom"]),
                      "cutters": cutters, "interior": None})
        fy = yb + sgn * 2.2 if sgn > 0 else ya - 2.2
        prims.append(cyl(c.x, fy, deck, 0.9, 7.5, "rust_metal", seg=14))
        prims.append(cyl(c.x, fy, deck + 7.5, 0.95, 0.5, "hazard_stripes", seg=14))
        b["_h"] = None
        # boarding ladders over the side, so a swimmer in the basin can climb onto the deck
        # (2 m from the quay, a jump ashore): the deck is clear of the deckhouse and the funnel
        clutter = house.union(Point(c.x, fy).buffer(0.9)).buffer(0.1)
        hull = prep(pg)

        def boardable(x, y, n):
            if not self.W_p.contains(Point(x - n[0] * 0.4, y - n[1] * 0.4)):
                return False
            return all(hull.contains(Point(x + n[0] * d, y + n[1] * d)) and not clutter.contains(Point(x + n[0] * d, y + n[1] * d))
                       for d in (0.4, LADDER_HOOP_REACH_M + 0.1, 1.2))
        runs = self.edge_runs(pg, boardable, inward=True)
        for i, sp in enumerate(sorted(self.spread_ladders(runs), key=lambda sp: (round(sp["at"][1], 2), round(sp["at"][0], 2))), 1):
            self.ladder(f"{w['id']}_hull_{i}", w, sp["at"][0], sp["at"][1], sp["n"], water_data()["ladder_top_step_m"], deck, deck)

    # fixtures and props (from the layout's shapes) -----------------------------------
    def fixture(self, sector, fx, room_building, owner):
        """One layout shape ("rect", "circle", "orect", "poly" with a class) as a mesh. Inside an
        enterable building it goes into the interior object; outside it is a prop object."""
        P = self.P
        kind = fx[0]
        cls = fx[-1]
        g = RM.shape_geom(fx)
        c = g.centroid
        inside = room_building is not None
        if not inside:
            # counted for every outdoor fixture, a vehicle's spot too, so the props after it keep
            # their names and their draws (every other stall has a light)
            self.nprop = getattr(self, "nprop", 0) + 1
        if cls == "car":
            self.vehicle(sector, fx, FLOOR_Z if inside else self.ground_level(c.x, c.y))
            return
        if inside:
            z = FLOOR_Z
            prims = P.obj(sector, "interior", name=f"interior_{room_building['id']}", col="col")
        else:
            z = self.ground_level(c.x, c.y)
            pname = f"prop_{cls.replace('-', '_')}_{self.nprop:03d}"
            prims = P.obj(sector, "prop", col="col", extras=PROP_EXTRAS, origin=(c.x, c.y, z), name=pname)
        zg = owner if inside else "exterior"
        x0, y0, x1, y1 = g.bounds
        w, d = x1 - x0, y1 - y0
        if cls == "stall":
            if kind == "orect":
                cx, cy, sw, sh, ang = fx[1:6]
            else:
                cx, cy, sw, sh, ang = (x0 + x1) / 2, (y0 + y1) / 2, max(w, d), min(w, d), 0.0 if w >= d else 90.0
            self.stall(sector, prims, cx, cy, z, sw, sh, ang, light=(not inside and self.nprop % 2 == 0))
            return
        if cls == "container":
            self.wagon(prims, *fx[1:3], z, *fx[3:6])
            return
        if cls == "crate":
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            lo, hi = (cx - 1.0, cy - 1.0, z), (cx + 1.0, cy + 1.0, z + 2.0)
            prims.append(box_prim(lo, hi, "crate_large", skip=[0]))
            P.zdetail(zg, lo, hi, "crate")
            if int(cx * 7 + cy * 3) % 2 == 0:
                lo2, hi2 = (cx - 0.35, cy - 0.3, z + 2.0), (cx + 0.65, cy + 0.7, z + 3.0)
                prims.append(box_prim(lo2, hi2, "crate", skip=[0]))
                P.zdetail(zg, lo2, hi2, "crate top")
            return
        if kind == "circle":
            r = fx[3]
            if cls == "fix-hot":
                self.fire(sector, prims, c.x, c.y, z, r)
            elif cls == "fix-dark":
                ring = Point(c.x, c.y).buffer(r, 16).difference(Point(c.x, c.y).buffer(r - 0.4, 16))
                prims.append(prism(ring, z, z + 0.6, {"top": "concrete", "side": "concrete", "bottom": "concrete"}))
                prims.append(prism(Point(c.x, c.y).buffer(r - 0.4, 16), z + 0.02, z + 0.02,
                                   {"top": "rust_metal", "side": "rust_metal", "bottom": "rust_metal"}))
            else:   # a round booth: bench ring and table
                prims.append(cyl(c.x, c.y, z, r, 0.5, "gunmetal", seg=16, cap_mat="rubber"))
                prims.append(cyl(c.x, c.y, z + 0.5, r * 0.55, 0.32, "gunmetal_light", seg=16))
            return
        if kind == "poly":
            if self.W.contains(c):
                self.boat(prims, g, c)
            return
        if kind == "orect":
            cx, cy, sw, sh, ang = fx[1:6]
            ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            prims.append(obox(cx, cy, ux, uy, sw / 2, sh / 2, z, z + 0.9, "tech_panel"))
            return
        # axis-aligned rects
        thin = min(w, d)
        long_ = max(w, d)
        lo, hi = (x0, y0, z), (x1, y1, z)
        if cls == "fix-band":
            # a neon band on the facade over a frontage, whether or not the building has rooms
            self.neon_band(sector, fx, g)
            return
        if cls == "fix-neon":
            if inside:
                # a neon strip on the nearest wall
                rb = room_building["_g"].bounds
                if w < d:
                    xw = rb[0] + WALL_T if abs(x0 - rb[0]) < abs(x1 - rb[2]) else rb[2] - WALL_T
                    xs = (xw + 0.01, xw + 0.11) if xw < (rb[0] + rb[2]) / 2 else (xw - 0.11, xw - 0.01)
                    lo, hi = (xs[0], y0, z + 2.3), (xs[1], y1, z + 2.45)
                else:
                    yw = rb[1] + WALL_T if abs(y0 - rb[1]) < abs(y1 - rb[3]) else rb[3] - WALL_T
                    ys = (yw + 0.01, yw + 0.11) if yw < (rb[1] + rb[3]) / 2 else (yw - 0.11, yw - 0.01)
                    lo, hi = (x0, ys[0], z + 2.3), (x1, ys[1], z + 2.45)
                prims.append(box_prim(lo, hi, "neon_pink"))
                P.zdetail(zg, lo, hi, "neon strip")
            else:
                self.neon_band(sector, fx, g)
            return
        if cls == "fix-cyan":
            if long_ / max(thin, 0.1) > 4:
                n = max(2, int(long_ / 2.5))
                for q in range(n):
                    f = (q + 0.5) / n
                    if w >= d:
                        px, py = x0 + w * f, (y0 + y1) / 2
                        blo, bhi = (px - 0.15, py - 0.5, z), (px + 0.15, py + 0.5, z + 1.05)
                    else:
                        px, py = (x0 + x1) / 2, y0 + d * f
                        blo, bhi = (px - 0.5, py - 0.15, z), (px + 0.5, py + 0.15, z + 1.05)
                    prims.append(box_prim(blo, bhi, ["gunmetal", "neon_cyan"] + ["gunmetal"] * 4))
                    P.zdetail(zg, blo, bhi, "gate")
                return
            ht = 1.9 if inside else 2.6
            hi = (x1, y1, z + ht)
            prims.append(box_prim(lo, hi, ["tech_panel", "tech_panel", "neon_cyan", "tech_panel", "neon_cyan", "tech_panel"]))
            P.zdetail(zg, lo, hi, "kiosk")
            if not inside:
                roof_lo, roof_hi = (x0 - 0.4, y0 - 0.4, z + ht), (x1 + 0.4, y1 + 0.4, z + ht + 0.12)
                prims.append(box_prim(roof_lo, roof_hi, "tech_panel"))
                P.zdetail(zg, roof_lo, roof_hi, "kiosk roof")
                P.shelter(box(roof_lo[0], roof_lo[1], roof_hi[0], roof_hi[1]), roof_lo[2], "kiosk roof")
                P.light(sector, "cyan", c.x, y1 + 0.9, z + ht - 0.3)
            return
        if cls == "fix-hot":
            if not inside and long_ / max(thin, 0.1) >= 5:
                # a barrier across a street (the checkpoint): the game's door entity brings the
                # posts and the arm, so the level leaves the street open
                return
            if long_ / max(thin, 0.1) >= 3:
                hi = (x1, y1, z + 1.1)
                prims.append(box_prim(lo, hi, "stone_blocks", skip=[0]))
                P.zdetail(zg, lo, hi, "altar")
                cl, ch = (x0 + 0.2, y0 + 0.2, z + 1.1), (x1 - 0.2, y1 - 0.2, z + 1.28)
                prims.append(box_prim(cl, ch, "lamp_glow", skip=[0]))
                P.zdetail(zg, cl, ch, "candles")
                P.light(sector, "fire", c.x, c.y, z + 1.8, energy=1.2)
                return
            if w * d <= 5:
                hi = (x1, y1, z + 1.4)
                prims.append(box_prim(lo, hi, "gunmetal", skip=[0]))
                P.zdetail(zg, lo, hi, "safe")
                return
            self.food_counter(sector, prims, x0, y0, x1, y1, z, zg)
            return
        if cls == "fix-dark":
            self.dark_feature(sector, fx, g, z)
            return
        if cls == "fix-lt":
            if not inside and 6 < w * d < 16 and thin > 2:
                self.lift(sector, x0, y0, x1, y1, z)
                return
            if not inside and thin < 1.5:
                self.jersey(prims, x0, y0, x1, y1, z, zg)
                return
            hi = (x1, y1, z + 1.05)
            prims.append(box_prim(lo, hi, ["tech_panel", "diamond_plate"] + ["tech_panel"] * 4, skip=[0]))
            P.zdetail(zg, lo, hi, "counter")
            return
        # plain "fix": capsules, shelves, platforms, tables
        if owner == "golden_carp" and 7 < w * d < 10:
            for lvl in (0, 1):
                zl = z + 0.02 + lvl * 1.25
                blo, bhi = (x0, y0, zl), (x1, y1, zl + 1.18)
                prims.append(box_prim(blo, bhi, ["tech_panel", "tech_panel", "gunmetal_light", "tech_panel",
                                                 "window_lit_warm" if (lvl + int(x0)) % 3 == 0 else "gunmetal", "tech_panel"]))
                P.zdetail(zg, blo, bhi, "capsule")
            return
        if thin <= 1.6 and long_ >= 3:
            hi = (x1, y1, z + 2.0)
            prims.append(box_prim(lo, hi, ["rust_metal", "rust_metal", "crate", "rust_metal", "crate", "rust_metal"], skip=[0]))
            P.zdetail(zg, lo, hi, "shelf")
            return
        if w * d >= 6:
            hi = (x1, y1, z + 0.4)
            prims.append(box_prim(lo, hi, ["diamond_plate", "diamond_plate"] + ["tech_panel"] * 4, skip=[0]))
            P.zdetail(zg, lo, hi, "platform")
            return
        hi = (x1, y1, z + 0.78)
        prims.append(box_prim(lo, hi, "gunmetal_light", skip=[0]))
        P.zdetail(zg, lo, hi, "table")

    def stall(self, sector, prims, cx, cy, z, sw, sh, ang, light=False):
        P = self.P
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        vx, vy = -uy, ux

        def L(u, v):
            return (cx + ux * u + vx * v, cy + uy * u + vy * v)
        hw, hd = sw / 2, sh / 2
        # the counter at the front, the back shelf, and the vendor's space between them
        counter = [L(-hw, hd - 0.7), L(hw, hd - 0.7), L(hw, hd), L(-hw, hd)]
        prims.append(hexa(counter, z, z + 1.0, ["crate", "diamond_plate", "crate", "crate", "crate", "crate"], skip=[0]))
        P.solid(counter, z, z + 1.0, "stall counter")
        back = [L(-hw, -hd), L(hw, -hd), L(hw, -hd + 0.45), L(-hw, -hd + 0.45)]
        prims.append(hexa(back, z, z + 1.5, "crate", skip=[0]))
        P.solid(back, z, z + 1.5, "stall back")
        for pu, pv in ((-hw + 0.05, -hd + 0.05), (hw - 0.05, -hd + 0.05), (-hw + 0.05, hd - 0.05), (hw - 0.05, hd - 0.05)):
            px, py = L(pu, pv)
            prims.append(obox(px, py, ux, uy, 0.04, 0.04, z, z + 2.45, "gunmetal", skip=[0]))
            P.solid(obox_corners(px, py, ux, uy, 0.04, 0.04), z, z + 2.45, "stall post")
        c4 = [L(-hw - 0.15, -hd - 0.15), L(hw + 0.15, -hd - 0.15), L(hw + 0.15, hd + 0.45), L(-hw - 0.15, hd + 0.45)]
        prims.append(hexa_pts([(*c4[0], z + 2.6), (*c4[1], z + 2.6), (*c4[2], z + 2.3), (*c4[3], z + 2.3),
                               (*c4[0], z + 2.66), (*c4[1], z + 2.66), (*c4[2], z + 2.36), (*c4[3], z + 2.36)], "awning"))
        P.cover(c4, z + 2.3, "stall awning")
        gx, gy = L(0, hd - 0.35)
        prims.append(obox(gx, gy, ux, uy, 0.3, 0.08, z + 2.1, z + 2.18, "lamp_glow"))
        if light:
            P.light(sector, "stall", gx, gy, z + 1.95, corona_at=(gx, gy, z + 2.05))

    def vehicle(self, sector, fx, z):
        """A parked vehicle on a car spot (openspec/changes/street-vehicles, design section 4): an
        ENT_car the importer turns into the variant's model, its front along the spot's long
        side, toward the spot's angle (the layout says which way a row faces). The variants made
        for the spot's size are dealt like a deck, shuffled from a stream of that size's own, so
        each shows once before any repeats and no other draw in the level moves."""
        cx, cy, sw, sh, ang = fx[1:6]
        spot = "truck" if sw * sh > 16 or max(sw, sh) > 7 else "car"
        deck = self.vehicle_decks.setdefault(spot, {"rng": random.Random(f"{self.P.seed}:vehicles:{spot}"), "left": []})
        if not deck["left"]:
            deck["left"] = sorted(v["id"] for v in VEHICLES["variants"] if VEHICLES["types"][v["type"]]["spot"] == spot)
            deck["rng"].shuffle(deck["left"])
        model = deck["left"].pop()
        a = math.radians(ang if sw >= sh else ang + 90.0)
        heading = heading_of(math.cos(a), math.sin(a))
        self.vehicles.append({"name": f"ENT_car_{len(self.vehicles) + 1:03d}", "model": model, "at": (cx, cy, z),
                              "heading": heading, "spot": fx})
        v = self.vehicles[-1]
        self.P.entity(sector, v["name"], cx, cy, z, heading,
                      {"kind": "car", "id": v["name"][len("ENT_car_"):], "model": model})

    @staticmethod
    def vehicle_problems(v, models=vehicle_data.MODELS):
        """What's wrong with one placed vehicle: its committed model's footprint, turned to its
        heading, must lie inside its spot's footprint."""
        (x0, y0, _), (x1, y1, _) = vehicle_data.model_bounds(v["model"], models)
        h = math.radians(v["heading"])
        fx_, fy_ = math.sin(h), -math.cos(h)            # the front, in layout axes (heading_of's inverse)
        rx, ry = -fy_, fx_                              # its right: the model's +x
        cx, cy, _ = v["at"]
        corners = [(cx + rx * x + fx_ * y, cy + ry * x + fy_ * y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        spot = RM.shape_geom(v["spot"])
        if spot.buffer(1e-6).contains(Polygon(corners)):
            return []
        _, _, _, sw, sh, _ = v["spot"][:6]
        return [f"{v['name']} ({v['model']}, {y1 - y0:.2f} x {x1 - x0:.2f} m) doesn't fit its {max(sw, sh):g} x "
                f"{min(sw, sh):g} m spot at ({cx:.1f}, {cy:.1f})"]

    def check_vehicles(self):
        """Every parked vehicle fits its spot (openspec/changes/street-vehicles, "Parked vehicles
        are generated models placed by the plan"), read from the committed glb. Refuses the plan,
        naming each spot and model."""
        problems = [p for v in self.vehicles for p in self.vehicle_problems(v)]
        if problems:
            raise SystemExit(f"{self.m['id']}: {len(problems)} vehicles don't fit their spots:\n  " + "\n  ".join(problems))

    def wagon(self, prims, cx, cy, z, sw, sh, ang):
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        vx, vy = -uy, ux

        def Lp(u, v):
            return (cx + ux * u + vx * v, cy + uy * u + vy * v)
        hl, hw = sw / 2, sh / 2
        prims.append(hexa([Lp(-hl, -hw + 0.2), Lp(hl, -hw + 0.2), Lp(hl, hw - 0.2), Lp(-hl, hw - 0.2)], z + 0.8, z + 1.1, "gunmetal"))
        for bu in (-hl + 1.6, hl - 1.6):
            prims.append(hexa([Lp(bu - 1.1, -hw + 0.45), Lp(bu + 1.1, -hw + 0.45), Lp(bu + 1.1, hw - 0.45), Lp(bu - 1.1, hw - 0.45)],
                              z + 0.12, z + 0.8, "rust_metal"))
        prims.append(hexa([Lp(-hl + 0.1, -hw + 0.28), Lp(hl - 0.1, -hw + 0.28), Lp(hl - 0.1, hw - 0.28), Lp(-hl + 0.1, hw - 0.28)],
                          z + 1.1, z + 3.7, "rust_metal"))

    def boat(self, prims, g, c):
        w = next((wb for wb in self.waters if wb["g"].contains(c)), None)
        s = w["surface"] if w else -2.2
        pg = oriented(g)
        top = ring_xy(pg.exterior.coords)
        bot = ring_xy(affinity.scale(pg, 0.7, 0.8, origin=c).exterior.coords)
        prims.append({"t": "loft", "rings": [bot, top], "z": [r4(s - 0.7), r4(s + 0.5)],
                      "mat": {"top": "diamond_plate", "bottom": "rust_metal", "side": "rust_metal"}})
        cab = affinity.scale(pg, 0.35, 0.3, origin=c)
        prims.append(prism(cab, s + 0.5, s + 1.6, {"top": "rust_metal", "side": "window_dark", "bottom": "rust_metal"}))

    def fire(self, sector, prims, x, y, z, r):
        """A burn barrel (small) or a brazier (large), with a fire light."""
        br = 0.35 if r <= 1.0 else 0.6
        prims.append(cyl(x, y, z, br, 0.9, "rust_metal", seg=12, caps=False))
        prims.append(cyl(x, y, z + 0.78, br - 0.03, 0.02, "lamp_glow", seg=12))
        self.P.light(sector, "fire", x, y, z + 1.5, corona_at=(x, y, z + 1.1))

    def food_counter(self, sector, prims, x0, y0, x1, y1, z, zg):
        P = self.P
        prims.append(box_prim((x0, y1 - 1.0, z), (x1, y1, z + 1.05), ["crate", "diamond_plate"] + ["crate"] * 4, skip=[0]))
        P.zdetail(zg, (x0, y1 - 1.0, z), (x1, y1, z + 1.05), "counter")
        prims.append(box_prim((x0, y0, z), (x1, y0 + 0.6, z + 1.3), "rust_metal", skip=[0]))
        P.zdetail(zg, (x0, y0, z), (x1, y0 + 0.6, z + 1.3), "kitchen")
        prims.append(box_prim((x0, y0, z + 1.3), (x1, y0 + 0.6, z + 2.2), ["rust_metal", "rust_metal", "tech_panel", "rust_metal",
                                                                           "window_lit_warm", "rust_metal"]))
        P.zdetail(zg, (x0, y0, z + 1.3), (x1, y0 + 0.6, z + 2.2), "menu board")
        for q in range(4):
            sx = x0 + (x1 - x0) * (q + 0.5) / 4
            prims.append(cyl(sx, y1 + 0.55, z, 0.2, 0.72, "gunmetal", seg=10))
        clo, chi = (x0 - 0.3, y0 - 0.3, z + 2.75), (x1 + 0.3, y1 + 1.2, z + 2.87)
        prims.append(box_prim(clo, chi, "awning"))
        P.zdetail(zg, clo, chi, "canopy")
        for px in (x0 + 0.08, x1 - 0.08):
            for py in (y0 + 0.08, y1 + 1.0):
                prims.append(box_prim((px - 0.05, py - 0.05, z), (px + 0.05, py + 0.05, z + 2.75), "gunmetal", skip=[0, 1]))
        prims.append(text("NOODLES", (x0 + x1) / 2, y1 + 1.23, z + 2.88, 180.0, 0.5, "neon_pink", 0.05))
        P.light(sector, "warm_sign", (x0 + x1) / 2, y1 + 0.6, z + 2.4)

    def jersey(self, prims, x0, y0, x1, y1, z, zg):
        w, d = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if w >= d:
            hs = [(x0, cy - 0.3), (x1, cy - 0.3), (x1, cy + 0.3), (x0, cy + 0.3)]
            ts = [(x0, cy - 0.12), (x1, cy - 0.12), (x1, cy + 0.12), (x0, cy + 0.12)]
        else:
            hs = [(cx - 0.3, y0), (cx + 0.3, y0), (cx + 0.3, y1), (cx - 0.3, y1)]
            ts = [(cx - 0.12, y0), (cx + 0.12, y0), (cx + 0.12, y1), (cx - 0.12, y1)]
        prims.append(hexa_pts([(*p, z) for p in hs] + [(*p, z + 0.82) for p in ts], "concrete", skip=[0]))

    def neon_band(self, sector, fx, g):
        """A neon strip along the facade next to a no-interior building's frontage rect."""
        x0, y0, x1, y1 = g.bounds
        b = next((bb for bb in self.named if bb["_g"].buffer(0.05).contains(g)), None)
        if not b:
            return
        fb = b["_g"].bounds
        vis = self.P.obj(sector, "vis", (x0 + x1) / 2, (y0 + y1) / 2)
        if x1 - x0 >= y1 - y0:
            if abs(y1 - fb[3]) < abs(y0 - fb[1]):
                lo, hi = (x0, fb[3] + 0.02, 3.85), (x1, fb[3] + 0.16, 4.02)
                ly = fb[3] + 1.2
            else:
                lo, hi = (x0, fb[1] - 0.16, 3.85), (x1, fb[1] - 0.02, 4.02)
                ly = fb[1] - 1.2
            vis.append(box_prim(lo, hi, "neon_pink"))
            self.P.zdetail("exterior", lo, hi, "neon band")
            self.P.light(sector, "pink", (x0 + x1) / 2, ly, 3.6)

    def dark_feature(self, sector, fx, g, z):
        """The storm drain culvert (in the Pit), the outfall (at the canal) or a tunnel portal (at the map edge)."""
        P = self.P
        x0, y0, x1, y1 = g.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        prims = P.obj("streets", "walk", cx, cy, col="col")
        if self.PIT.contains(Point(cx, cy)):
            # culvert headwall against the pit's far wall, opening towards the pit
            yb = y1 + 0.4
            yw = y1 + 3.6
            solid = prism(box(x0 - 0.8, yb, x1 + 0.8, yw), self.pit_floor, 0.6,
                          {"top": "concrete", "side": "concrete", "bottom": "concrete"}, caps=["top", "bottom"])
            cut = box_prim((x0 + 0.6, yb - 0.4, self.pit_floor), (x1 - 0.6, yw - 0.6, self.pit_floor + 2.4),
                           ["concrete", "stone_blocks", "stone_blocks", "stone_blocks", "window_dark", "stone_blocks"])
            prims.append({"t": "bool", "solid": solid, "cutters": [cut], "interior": None})
            for q in range(9):
                bx = x0 + 0.7 + (x1 - x0 - 1.4) * q / 8
                prims.append(box_prim((bx - 0.03, yb - 0.1, self.pit_floor), (bx + 0.03, yb - 0.04, self.pit_floor + 2.4), "rust_metal"))
            P.lamp_entity(sector, "wall_lamp", cx, yb - 0.07, self.pit_floor + 2.85, 0.0)
            return
        if self.W.buffer(0.5).contains(Point(cx, cy)) or g.intersects(self.W):
            # outfall: a mouth in the quay wall above the water, a ledge and a ladder up to the walk
            w = next((wb for wb in self.waters if wb["g"].intersects(g)), self.waters[0])
            s = w["surface"]
            # find the quay line: the water edge crossing this rect
            xq = x0
            for q in range(0, 60):
                xx = x0 + (x1 - x0) * q / 59
                if self.W.contains(Point(xx, cy)):
                    xq = xx
                    break
            # the mouth reads as a dark plate on the wall, barred by the grate
            prims.append(box_prim((xq + 0.05, y0, s + 0.3), (xq + 0.07, y1, QUAY_Z - 0.35), "window_dark"))
            for q in range(7):
                by = y0 + 0.2 + (y1 - y0 - 0.4) * q / 6
                prims.append(box_prim((xq + 0.09, by - 0.03, s + 0.3), (xq + 0.14, by + 0.03, QUAY_Z - 0.35), "rust_metal"))
            prims.append(box_prim((xq + 0.16, y0 - 0.6, s + 0.1), (xq + 1.4, y1 + 0.6, s + 0.22), "diamond_plate"))
            # the ladder up from the ledge's end to the quay walk (land is west of the quay line)
            ly = y1 + 0.9 + LADDER_W_M / 2
            landing = self.ladder_landing(xq, ly, (-1.0, 0.0))
            if landing is None:
                raise SystemExit(f"{self.m['id']}: the outfall's ladder at ({xq:g}, {ly:g}) has nowhere to step off at the top")
            self.ladder(f"{w['id']}_outfall", w, xq, ly, (-1.0, 0.0), *landing)
            self.outfall = (xq, y0, y1)
            return
        # a tunnel portal at the map edge
        solid = prism(box(x0 - 2, y0, x1 + 2, y1), 0.0, 8.0, {"top": "concrete", "side": "concrete", "bottom": "concrete"},
                      caps=["top", "bottom"])
        cut = box_prim((x0 + 1.0, y0 - 0.4, 0.0), (x1 - 1.0, y1 - 0.3, 5.6),
                       ["concrete", "stone_blocks", "stone_blocks", "stone_blocks", "window_dark", "stone_blocks"])
        prims.append({"t": "bool", "solid": solid, "cutters": [cut], "interior": None})
        prims.append(box_prim((x0 + 1.0, y1 - 0.34, 0.0), (x1 - 1.0, y1 - 0.3, 5.6), "rust_metal"))
        P.lamp_entity(sector, "wall_lamp", cx, y0 - 0.07, 6.4, 0.0)

    # lot buildings -------------------------------------------------------------------
    def lot_buildings(self):
        P = self.P
        for lot in self.lots:
            pg = lot["poly"]
            st = STYLES[lot["style"]]
            rng = lot["rng"]
            sector = lot["sector"]
            h = lot["h"]
            parapet = lot["parapet"]
            facade_mat = st["facade"][int(rng.random() * len(st["facade"]))]
            cutters = []
            solid = prism(pg, 0.0, h + parapet, {"side": facade_mat, "top": st["cap"] if parapet else st["roof"],
                                                "bottom": facade_mat}, caps=["top", "bottom"])
            if parapet > 0:
                inner = pg.buffer(-0.3, join_style=2)
                if inner.area > 3:
                    cutters += [prism(q, h, h + parapet + 2.0, {"top": "concrete", "bottom": st["roof"], "side": "concrete"},
                                      caps=["top", "bottom"]) for q in polys(inner)]
                else:
                    parapet = 0.0
                    lot["parapet"] = 0.0
                    solid = prism(pg, 0.0, h, {"side": facade_mat, "top": st["roof"], "bottom": facade_mat}, caps=["top", "bottom"])
            P.shelter(pg, h, f"lot {lot['id']}")
            thick = not pg.buffer(-0.5).is_empty
            openings = []
            edges = self.facade(sector, pg, 0.0, h, st, rng, lot["id"], cutters,
                                allow=("windows", "front", "awning") if thick else (), openings=openings)
            rp = pg.representative_point()
            P.obj(sector, "vis", rp.x, rp.y).append({"t": "bool", "solid": solid, "cutters": cutters, "interior": None})
            # simplified collision: the plain block
            P.obj(sector, "hull", rp.x, rp.y, col="colonly").append(
                prism(pg, 0.0, h + parapet, {"side": facade_mat, "top": st["roof"], "bottom": facade_mat}))
            ladder = self.building_details(sector, pg, 0.0, h, st, rng, edges, st["cap"], parapet,
                                           allow_blade=thick, allow_fire=thick, limit=lot["limit"])
            self.dressing_doors(lot, st, edges, openings, ladder, cutters)
            for e in edges:
                self.facades.append((sector, e, h))
            self.roof_clutter(lot, st, rng)

    # dressing doors (openspec/changes/hub-doorways, design section 3.4) ---------------------
    def dressing_doors(self, lot, st, edges, openings, ladder, cutters):
        """The closed doors a filler building shows: a glazed door in every shop bay, a
        residents' door on a shop building of two floors or more, the shanty's plank or sheet
        door where its dark recess was, a steel man door beside a roll-up or loading door, and
        for a building still showing none, its style's door on its longest walkable edge. They
        never open and show no use prompt (owner K1); each is framed by detailing.door_frame and
        solid behind its leaf. Every choice comes from the lot's own door RNG, drawn after the
        facade's, so no window, bay, sign or colour already in the hub moves."""
        key = f"lot {lot['id']}"
        drng = random.Random(f"{self.P.seed}:doors:{lot['id']}")
        rp = lot["poly"].representative_point()
        vis = self.P.obj(lot["sector"], "vis", rp.x, rp.y)
        mat = FRAME_MATS[lot["style"]]
        shown = 0
        for op in openings:
            e = edges[op["edge"]]
            if op["kind"] == "bay":
                self.shop_door(vis, key, e, op, drng, mat)
                shown += 1
            elif op["kind"] == "shanty":
                e[5].remove((op["c"] - 0.8, op["c"] + 0.8, 2.4))    # the span facade kept for this door
                shown += self.leaf_door(vis, key, e, op["c"], "shanty", drng, cutters, mat, ladder, reserved=True)
            else:
                self.shutter_fittings(vis, key, e, op)
        rollups = [op for op in openings if op["kind"] in ("rollup", "loading")]
        walkable = sorted([e for e in edges if e[4] >= 2.2 and e[6] in ("street", "side")],
                          key=lambda e: (e[6] != "street", -e[4]))    # the longest street edge first
        if not walkable:
            return
        style = lot["style"]
        if style in ("strip", "market") and lot["h"] >= st["ground_h"] + st["floor_h"]:
            fronts = [e for e in walkable if e[6] == "street"]
            if fronts:
                shown += self.leaf_door(vis, key, max(fronts, key=lambda e: e[4]), None, "residents", drng, cutters, mat, ladder)
        if style in ("workshop", "dock"):
            need = detailing.frame_outer_width(DRESS_DOORS["man"]["clear"][0], "architrave")
            placed = 0
            for op in [o for o in openings if o["kind"] in ("rollup", "loading")]:
                e = edges[op["edge"]]
                for side in (1, -1):
                    want = op["c"] + side * (op["w"] / 2 + 0.3 + need / 2)
                    placed = self.leaf_door(vis, key, e, want, "man", drng, cutters, mat, ladder, prefer_only=True)
                    if placed:
                        break
                if placed:
                    break
            if not placed and rollups:
                # A front the roll-up fills has no room for a man door: the fitted roll-up is its door.
                e, op = edges[rollups[0]["edge"]], rollups[0]
                self.shown_doors.append((key, *frame(e[0], e[2], e[3])(op["c"], 0.0)))
                self.door_counts["roll-up as door"] = self.door_counts.get("roll-up as door", 0) + 1
                placed = 1
            shown += placed
        for e in walkable if not shown else ():
            if self.leaf_door(vis, key, e, None, STYLE_DOOR[style], drng, cutters, mat, ladder):
                break

    def free_spot(self, e, need, ladder, prefer=None, only=False, reserved=False):
        """Where on edge `e` a door frame `need` wide stands clear: 0.35 m from the edge's ends,
        clear of its other openings (their occupied spans, padded 0.1 m more) and of a fire
        escape's drop ladder. Nearest `prefer` (the middle by default); with `only`, just there.
        A `reserved` door takes a span the facade already kept for it (a shanty's recess, drawn
        0.9 m or more from a corner): only 0.15 m from the ends and the ladder apply."""
        a, b, t, n, L, occupied, look = e
        end = 0.15 if reserved else 0.35
        lo, hi = end + need / 2, L - end - need / 2
        if hi < lo:
            return None
        blocks = [] if reserved else [(s0 - 0.1, s1 + 0.1) for s0, s1, _ in occupied]
        if ladder and ladder["edge"] is e:
            blocks.append((ladder["s"][0] - 0.3, ladder["s"][1] + 0.3))
        target = L / 2 if prefer is None else prefer
        cands = [target] if only else sorted({round(target + k * 0.1, 3) for k in range(-int(L * 10) - 1, int(L * 10) + 2)},
                                             key=lambda q: (abs(q - target), q))
        for q in cands:
            if lo - 1e-9 <= q <= hi + 1e-9 and all(q + need / 2 <= b0 or q - need / 2 >= b1 for b0, b1 in blocks):
                return q
        return None

    def leaf_door(self, vis, key, e, s, kind, drng, cutters, mat, ladder, prefer_only=False, reserved=False):
        """A closed door of its own: a recess carved at the fits with the leaf as its back, the
        frame's liners, threshold and architrave, and the kind's fittings. Returns 1 when it
        found room (at `s`, or with `prefer_only` false the free spot nearest it), else 0."""
        a, b, t, n, L, occupied, look = e
        cw, ch = DRESS_DOORS[kind]["clear"]
        fw, fh = detailing.door_fits(cw, ch)
        need = detailing.frame_outer_width(cw, "architrave")
        s = self.free_spot(e, need, ladder, s, only=(prefer_only or reserved) and s is not None, reserved=reserved)
        if s is None:
            return 0
        leaves = DRESS_DOORS[kind]["leaf"]
        leaf = leaves[int(drng.random() * len(leaves))]
        Pf = frame(a, t, n)
        cutters.append(self.recess(Pf, s - fw / 2, s + fw / 2, FLOOR_Z, FLOOR_Z + fh, DRESS_DEPTH, leaf, "concrete"))
        boxes = detailing.door_frame(cw, ch, DRESS_DEPTH, out="architrave", inside=None, step=STANDING_STEP_M, mat=mat)
        for bx in boxes:
            if bx["part"] in ("liner", "threshold"):
                bx["buried"].add("+v")      # pressed against the leaf
        cu, fu = cw / 2, fw / 2
        arch = fu + detailing.ARCHITRAVE["width"]
        if kind == "residents":
            boxes.append({"lo": (arch + 0.1, -0.03, 1.2), "hi": (arch + 0.22, 0.0, 1.5), "mat": "light_panel",
                          "part": "buzzer", "buried": {"+v"}})
        if kind == "shanty":
            if drng.random() < SHANTY_BOARDED:
                for z0 in (0.8, 1.5):
                    boxes.append({"lo": (-cu, 0.02, z0), "hi": (cu, DRESS_DEPTH, z0 + 0.15), "mat": "crate",
                                  "part": "board", "buried": {"+v", "-u", "+u"}})
            if drng.random() < SHANTY_PADLOCKED:
                boxes.append({"lo": (cu - 0.2, 0.04, 1.0), "hi": (cu - 0.08, DRESS_DEPTH, 1.12), "mat": "gunmetal",
                              "part": "hasp", "buried": {"+v"}})
        self.dress(vis, key, Pf, s, boxes, [("recess", (-fu, fu), (0.0, fh), (-0.3, DRESS_DEPTH))], f"{kind} door")
        occupied.append((s - need / 2 - 0.1, s + need / 2 + 0.1, FLOOR_Z + detailing.frame_top(ch, "architrave")))
        self.edge_doors.setdefault(id(occupied), []).append(s)
        self.shown_doors.append((key, *Pf(s, 0.0)))
        self.door_counts[kind] = self.door_counts.get(kind, 0) + 1
        return 1

    def shop_door(self, vis, key, e, op, drng, mat):
        """A shop bay split into a window and a glazed door, one frame round both: the bay's
        recess is the frame's fits, so the carve is unchanged. A shuttered bay's shutter comes
        down over both, so it shows only the frame."""
        a, b, t, n, L, occupied, look = e
        Pf = frame(a, t, n)
        w, depth = op["w"], 0.35
        bay_h = op["h"] - FLOOR_Z
        cw, ch = w - 2 * detailing.REVEAL, bay_h - detailing.REVEAL
        boxes = detailing.door_frame(cw, ch, depth, out="architrave", inside=None, step=STANDING_STEP_M, mat=mat)
        for bx in boxes:
            if bx["part"] in ("liner", "threshold"):
                bx["buried"].add("+v")      # pressed against the window or the shutter
        if op["back"] != "rust_metal":
            dw, dh = DRESS_DOORS["shop"]["clear"]
            cu = cw / 2
            side = 1 if drng.random() < 0.5 else -1
            d0, d1 = (cu - dw, cu) if side > 0 else (-cu, -cu + dw)
            m0, m1 = (d0 - 0.08, d0) if side > 0 else (d1, d1 + 0.08)
            step = STANDING_STEP_M
            boxes += [
                {"lo": (d0, 0.30, step), "hi": (d1, depth, dh), "mat": "tech_panel", "part": "leaf",
                 "buried": {"+v", "-z", "+z", "-u", "+u"}},
                {"lo": (m0, 0.27, step), "hi": (m1, depth, ch), "mat": mat, "part": "mullion", "buried": {"+v", "-z", "+z"}},
                {"lo": (d0, 0.27, dh), "hi": (d1, depth, dh + 0.08), "mat": mat, "part": "transom", "buried": {"+v", "-u", "+u"}},
                {"lo": (d0 + 0.12, 0.29, 0.95), "hi": (d1 - 0.12, 0.30, dh - 0.15), "mat": "glass", "part": "glass",
                 "buried": {"+v", "-u", "+u", "-z", "+z"}},
                {"lo": (d0 + 0.15, 0.25, 1.0), "hi": (d1 - 0.15, 0.29, 1.04), "mat": "gunmetal", "part": "push bar",
                 "buried": {"+v"}},
            ]
            door_s = op["c"] + (d0 + d1) / 2
        else:
            door_s = op["c"]
        self.dress(vis, key, Pf, op["c"], boxes, [("bay", (-w / 2, w / 2), (0.0, bay_h), (-0.3, depth))], "shop door")
        self.shown_doors.append((key, *Pf(door_s, 0.0)))
        self.door_counts["shop"] = self.door_counts.get("shop", 0) + 1

    def shutter_fittings(self, vis, key, e, op):
        """A roll-up or loading door's hood box over it and guide rails in its jambs, so the
        painted shutter reads as one."""
        a, b, t, n, L, occupied, look = e
        Pf = frame(a, t, n)
        w, depth, top = op["w"], 0.25, op["h"] - FLOOR_Z
        boxes = [{"lo": (-w / 2 - 0.1, -0.35, top), "hi": (w / 2 + 0.1, 0.0, top + 0.35), "mat": "rust_metal",
                  "part": "hood", "buried": {"+v"}}]
        for side in (-1, 1):
            u0, u1 = sorted((side * (w / 2 - 0.08), side * w / 2))
            boxes.append({"lo": (u0, 0.0, 0.0), "hi": (u1, depth, top), "mat": "rust_metal", "part": "guide rail",
                          "buried": {"+v", "-z", "+z", "+u" if side > 0 else "-u"}})
        self.dress(vis, key, Pf, op["c"], boxes, [("shutter", (-w / 2, w / 2), (0.0, top), (-0.3, depth))], "shutter")

    def dress(self, vis, key, Pf, s, boxes, recesses, what):
        """Puts a dressing door's boxes, in its own frame (u along the edge from `s`, v into the
        wall, z up from the floor), on the facade with their buried faces left out, registers what
        stands proud of the wall as solids for the standing-room check, and checks the door for
        z-fighting in its own frame: against the facade, the recess it stands in and itself (the
        plan's check knows axis-aligned boxes only, and a lot's edges run any way)."""
        tris = 0
        for bx in boxes:
            (u0, v0, z0), (u1, v1, z1) = bx["lo"], bx["hi"]
            skip = sorted(DOOR_FACES[d] for d in bx["buried"])
            vis.append(edge_box(Pf, s + u0, s + u1, -v1, -v0, FLOOR_Z + z0, FLOOR_Z + z1, bx["mat"], skip=skip))
            tris += 2 * (6 - len(skip))
            if v0 < 0:
                self.P.solid([Pf(s + u0, -v1), Pf(s + u1, -v1), Pf(s + u1, -v0), Pf(s + u0, -v0)],
                             FLOOR_Z + z0, FLOOR_Z + z1, f"{key} {what} {bx['part']}")
        airs = [detailing.Room("facade", (-8.0, 8.0), (0.0, 9.0), (-4.0, 0.0))]
        airs += [detailing.Room(name, u, z, v) for name, u, z, v in recesses]
        details = [((bx["lo"][0], bx["lo"][2], bx["lo"][1]), (bx["hi"][0], bx["hi"][2], bx["hi"][1]), f"{bx['part']} {i}")
                   for i, bx in enumerate(boxes)]
        report = detailing.zfight_report(airs, details)
        if report:
            x, y = Pf(s, 0.0)
            self.door_zfights.append(f"{key} {what} at ({x:.1f}, {y:.1f}): {report[0]}")
        self.door_tris[what] = self.door_tris.get(what, 0) + tris

    def roof_clutter(self, lot, st, rng):
        """The map's rooftop plant (render_map's lots), plus stacked shanty boxes and antennas."""
        P = self.P
        pg = lot["poly"]
        h = lot["h"]
        rz = lot["roof_z"]
        sector = lot["sector"]
        room = lot["limit"] - rz
        inner = pg.buffer(-0.4, join_style=2)
        rp = pg.representative_point()
        cprims = lambda: P.obj(sector, "roofprops", rp.x, rp.y, extras=PROP_EXTRAS)  # noqa: E731
        taken = Polygon()
        # a smaller box stacked on a shanty roof
        if st["stack"] and rng.random() < st["stack"] and room > 4.0 and h < 12:
            mrr = pg.buffer(-0.8, join_style=2)
            if not mrr.is_empty and mrr.area > 6:
                q = RM.random_point_in(mrr, rng)
                if q is not None:
                    f = rng.uniform(0.5, 0.72)
                    fp = affinity.scale(pg.minimum_rotated_rectangle, f, f, origin=q).intersection(pg.buffer(-0.6, join_style=2))
                    fp = max(polys(fp), key=lambda g: g.area, default=None)
                    if fp is not None and fp.area >= 4:
                        hs = min(rng.uniform(2.4, 3.2), room - 0.5)
                        mat = st["facade"][int(rng.random() * len(st["facade"]))]
                        cutters = []
                        self.facade(sector, fp, rz, hs, st, rng, lot["id"] + "s", cutters, allow=("windows",))
                        P.obj(sector, "vis", rp.x, rp.y).append(
                            {"t": "bool", "solid": prism(fp, rz, rz + hs, {"side": mat, "top": st["roof"], "bottom": mat},
                                                         caps=["top", "bottom"]), "cutters": cutters, "interior": None})
                        P.obj(sector, "hull", rp.x, rp.y, col="colonly").append(
                            prism(fp, rz, rz + hs, {"side": mat, "top": mat, "bottom": mat}))
                        taken = fp.buffer(0.3)
        for k, it in enumerate(lot["roof"]):
            if it[0] == "box":
                _, x, y, w, d = it
                fp = box(x - w / 2, y - d / 2, x + w / 2, y + d / 2)
                if not inner.contains(fp):
                    fp = fp.intersection(inner)
                    if fp.is_empty or fp.area < 0.5 or fp.geom_type != "Polygon":
                        continue
                    bx0, by0, bx1, by1 = fp.bounds
                    fp = box(bx0 + 0.05, by0 + 0.05, bx1 - 0.05, by1 - 0.05)
                    if not inner.contains(fp):
                        continue
                if fp.intersects(taken):
                    continue
                hb = round(rng.uniform(0.8, 1.4), 2)
                if hb > room - 0.2:
                    continue
                bx0, by0, bx1, by1 = fp.bounds
                cprims().append(box_prim((bx0, by0, rz), (bx1, by1, rz + hb),
                                         ["gunmetal_light", "tech_panel", "gunmetal_light", "gunmetal_light",
                                          "gunmetal_light", "gunmetal_light"], skip=[0]))
                cprims().append(cyl((bx0 + bx1) / 2, (by0 + by1) / 2, rz + hb, min(bx1 - bx0, by1 - by0) * 0.32, 0.06,
                                    "gunmetal", seg=12))
                taken = taken.union(fp.buffer(0.2))
            else:
                _, x, y, r = it
                tall = rng.uniform(2.0, 2.8)
                if 1.2 + tall > room - 0.2 or not inner.contains(Point(x, y).buffer(r)) or Point(x, y).buffer(r).intersects(taken):
                    continue
                for a in (45, 135, 225, 315):
                    lx, ly = x + math.cos(math.radians(a)) * r * 0.7, y + math.sin(math.radians(a)) * r * 0.7
                    cprims().append(box_prim((lx - 0.06, ly - 0.06, rz), (lx + 0.06, ly + 0.06, rz + 1.2), "rust_metal", skip=[0]))
                cprims().append(cyl(x, y, rz + 1.2, r, tall, "rust_metal", seg=14))
                cprims().append(cyl(x, y, rz + 1.2 + tall, r * 0.6, 0.35, "rust_metal", seg=14))
                taken = taken.union(Point(x, y).buffer(r + 0.2))
        if h > 9 and room > 7 and rng.random() < 0.3:
            q = RM.random_point_in(inner, rng)
            if q is not None and not taken.contains(q):
                mh = rng.uniform(3.0, 6.0)
                cprims().append(cyl(q.x, q.y, rz, 0.06, mh, "gunmetal", seg=6))
                for k in range(2):
                    zz = rz + mh * (0.55 + 0.3 * k)
                    cprims().append(box_prim((q.x - 0.5, q.y - 0.03, zz), (q.x + 0.5, q.y + 0.03, zz + 0.05), "gunmetal"))

    # the foundation wall ---------------------------------------------------------------
    def foundation_geometry(self):
        if self.F.is_empty:
            return
        P = self.P
        sec = self.fsector
        H = self.fheight
        top = self.fband.bounds[3]
        for i, j, pg in self.chunked(self.F):
            P.obj(sec, "walk", name=f"{sec}_walk_{i}_{j}", col="col").append(
                prism(pg, 0.0, H, {"top": "concrete", "side": "stone_blocks", "bottom": "stone_blocks"}))
        # a holo-billboard over the widest stretch without buttresses
        W = self.P.W
        bx0, bx1 = 0.68 * W - 13, 0.68 * W + 13
        for x in self.bspans:
            if bx0 - 2 < x < bx1 + 2:
                continue
            lo, hi = (x - 1.2, self.fface, 0.0), (x + 1.2, top, 30.0)
            P.add(sec, "walk", x, top, box_prim(lo, hi, "stone_blocks", skip=[0]), col="col")
            P.zdetail("exterior", lo, hi, "buttress")
            lo2, hi2 = (x - 1.45, self.fface, 30.0), (x + 1.45, top + 0.25, 31.2)
            P.add(sec, "walk", x, top, box_prim(lo2, hi2, "concrete"), col="col")
            P.zdetail("exterior", lo2, hi2, "buttress cap")
        cx = (bx0 + bx1) / 2
        f = self.fface
        vis = P.obj(sec, "vis", cx, f)
        lo, hi = (bx0, f, 19.5), (bx1, f + 0.35, 30.5)
        vis.append(box_prim(lo, hi, ["tech_panel", "tech_panel", "tech_panel", "tech_panel", "window_lit_cool", "tech_panel"]))
        P.zdetail("exterior", lo, hi, "billboard")
        for (a, b) in (((bx0 - 0.4, f, 19.1), (bx1 + 0.4, f + 0.5, 19.5)), ((bx0 - 0.4, f, 30.5), (bx1 + 0.4, f + 0.5, 30.9))):
            vis.append(box_prim(a, b, "gunmetal"))
            P.zdetail("exterior", a, b, "billboard frame")
        P.light(sec, "billboard", cx, f + 6.0, 25.0, corona_at=(cx, f + 0.8, 25.0))

    # the Skyway viaduct -------------------------------------------------------------
    def viaduct_geometry(self):
        """Deck, parapets, girders, pier caps and pillars (base and capital), underside lights."""
        if not self.viaduct:
            return
        P = self.P
        e = self.viaduct
        (ax, ay), (bx, by) = e["pts"][0], e["pts"][-1]
        L = math.dist((ax, ay), (bx, by))
        ux, uy = unit(bx - ax, by - ay)
        vx, vy = -uy, ux
        half = e["w"] / 2
        top = self.deck_top
        d0, d1 = top - 1.0, top
        g0 = d0 - 1.2
        c0 = g0 - 1.0

        def Q(s, v):
            return (ax + ux * s + vx * v, ay + uy * s + vy * v)
        pillars = RM.viaduct_pillars(e)
        stations = sorted({round(p["station_m"], 4) for p in pillars})
        cuts = [0.0] + stations + [L]
        for k in range(len(cuts) - 1):
            s0, s1 = cuts[k], cuts[k + 1]
            mx, my = Q((s0 + s1) / 2, 0)
            prims = P.obj("skyway", "walk", mx, my, col="col")
            skip_ends = ([] if k == 0 else [5]) + ([] if k == len(cuts) - 2 else [3])
            prims += viaduct_span(Q, s0, s1, half, d0, d1, g0, skip_ends)
            # an underside light in the middle of each span, alternating sides
            if 0 < k < len(cuts) - 1 or (s1 - s0) > 10:
                sm = (s0 + s1) / 2
                side = 1 if k % 2 else -1
                lx, ly = Q(sm, side * 3.0)
                prims.append(obox(lx, ly, ux, uy, 0.3, 0.3, d0 - 0.2, d0, "gunmetal"))
                prims.append(obox(lx, ly, ux, uy, 0.24, 0.24, d0 - 0.23, d0 - 0.2, "lamp_glow"))
                if 0 <= lx <= self.P.W and 0 <= ly <= self.P.H:
                    P.light("skyway", "viaduct", lx, ly, d0 - 0.5, corona_at=(lx, ly, d0 - 0.35))
        # deck lamps over every pier, alternating sides; every other one lights the deck
        for k, s in enumerate(stations):
            side = 1 if k % 2 else -1
            lx, ly = Q(s, side * (half - 0.9))
            self.lamp_post(lx, ly, -vx * side, -vy * side, sector="skyway", z=d1, height=7.0, light=(k % 2 == 0))
        # pier caps: two halves, leaving a gap on the centreline for the service catwalk
        for s in stations:
            mx, my = Q(s, 0)
            prims = P.obj("skyway", "walk", mx, my, col="col")
            for va, vb in ((-half, -1.9), (1.9, half)):
                prims.append(hexa([Q(s - 1.0, va), Q(s + 1.0, va), Q(s + 1.0, vb), Q(s - 1.0, vb)], c0, g0, "concrete"))
        for pl in pillars:
            x, y = pl["x"], pl["y"]
            bed = self.water_bed(x, y)
            z0 = bed if bed is not None else self.ground_level(x, y) - 0.15
            prims = P.obj("skyway", "walk", x, y, col="col")
            base_top = (self.waters[0]["surface"] + 0.8) if bed is not None else z0 + 0.15 + 0.9
            prims.append(obox(x, y, ux, uy, PILLAR_BASE_HALF_M, PILLAR_BASE_HALF_M, z0, base_top, "stone_blocks"))
            P.solid(obox_corners(x, y, ux, uy, PILLAR_BASE_HALF_M, PILLAR_BASE_HALF_M), z0, c0, "Skyway pillar")
            prims.append(obox(x, y, ux, uy, 1.02, 1.02, base_top, base_top + 0.3, "concrete"))
            prims.append(obox(x, y, ux, uy, 0.8, 0.8, base_top + 0.3, c0 - 0.7, "concrete", skip=[0, 1]))
            prims.append(obox(x, y, ux, uy, 1.02, 1.02, c0 - 0.7, c0 - 0.4, "concrete"))
            prims.append(obox(x, y, ux, uy, 1.15, 1.15, c0 - 0.4, c0, "stone_blocks"))
        self.v_frame = (ax, ay, ux, uy, vx, vy, d0, g0, c0)
        P.shelter(self.vfoot.intersection(self.R), d0, "Skyway deck")

    # walkways --------------------------------------------------------------------------
    def walkway_geometry(self):
        """Elevated walkways: decks at their layout heights, railings, posts or hangers,
        and stairs down at the ends of a walkway that doesn't land on a roof or a lift."""
        P = self.P
        for wk in self.walkways:
            line = wk["_line"]
            zs = wk["_z"]
            W = wk["_w"]
            pts = wk["pts"]
            hung = wk.get("hung")
            if hung and self.viaduct:
                ax, ay, ux, uy, vx, vy, d0, g0, c0 = self.v_frame
                # landings at both ends (the lift and the girder cache)
                for pt in (pts[0], pts[-1]):
                    sx = (pt[0] - ax) * ux + (pt[1] - ay) * uy
                    cxy = (ax + ux * sx, ay + uy * sx)
                    c4 = [(cxy[0] + ux * a + vx * b, cxy[1] + uy * a + vy * b)
                          for a, b in ((-4.0, -3.2), (4.0, -3.2), (4.0, 3.2), (-4.0, 3.2))]
                    wk.setdefault("_extra", []).append(Polygon(c4))
            deck = self.walk_poly(wk)
            # constant-height runs become one flat deck; slopes are ramps
            flat_z = None
            for k in range(len(pts) - 1):
                a, b = pts[k], pts[k + 1]
                za, zb = zs[k], zs[k + 1]
                if abs(za - zb) > 1e-6:
                    t = unit(b[0] - a[0], b[1] - a[1])
                    n = (-t[1], t[0])
                    c = [(a[0] + n[0] * W / 2, a[1] + n[1] * W / 2), (a[0] - n[0] * W / 2, a[1] - n[1] * W / 2),
                         (b[0] - n[0] * W / 2, b[1] - n[1] * W / 2), (b[0] + n[0] * W / 2, b[1] + n[1] * W / 2)]
                    ztop = [za, za, zb, zb]
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    sec = P.district_sector(mx, my) if not hung else "skyway"
                    P.add(sec, "walk", mx, my, hexa_pts([(*c[q], ztop[q] - WALK_DECK) for q in range(4)] +
                                                        [(*c[q], ztop[q]) for q in range(4)],
                                                        ["rust_metal", "diamond_plate"] + ["rust_metal"] * 4), col="col")
                    P.shelter(Polygon(c), min(za, zb) - WALK_DECK, f"walkway {wk.get('name')}")
                    seg_poly = LineString([a, b]).buffer(W / 2, cap_style=2)
                    deck = deck.difference(seg_poly)
                else:
                    flat_z = za
            if flat_z is not None:
                P.shelter(deck, flat_z - WALK_DECK, f"walkway {wk.get('name')}")
                for i, j, pg in self.chunked(deck) if not hung else [(0, 0, deck)]:
                    rp = pg.representative_point()
                    sec = "skyway" if hung else P.district_sector(rp.x, rp.y)
                    P.add(sec, "walk", rp.x, rp.y, prism(pg, flat_z - WALK_DECK, flat_z,
                                                         {"top": "diamond_plate", "side": "rust_metal", "bottom": "rust_metal"},
                                                         caps=["top", "bottom"]), col="col")
            # railings along both sides
            full = self.walk_poly(wk)
            ring = oriented(full) if full.geom_type == "Polygon" else None
            if ring is not None:
                for a, b in self.ring_edges(ring, ring.exterior.coords):
                    if math.dist(a, b) < 0.3:
                        continue
                    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                    # open ends of the walkway (where it meets a roof, stairs or a lift)
                    endish = min(math.dist(mid, pts[0]), math.dist(mid, pts[-1])) < W / 2 + 0.2 and math.dist(a, b) <= W + 0.3
                    open_end = self.roof_at(*mid) is not None or self.B.distance(Point(*mid)) > 0.6
                    if endish and not hung and open_end:
                        continue    # it lands on a roof or meets its stairs
                    za = self.walk_z(wk, a[0], a[1])
                    zb = self.walk_z(wk, b[0], b[1])
                    n = self.outward(ring, a, b)
                    self.rail_sloped(("skyway" if hung else P.district_sector(*mid)), a, b, (-n[0], -n[1]), za, zb)
            # supports
            if hung and self.viaduct:
                ax, ay, ux, uy, vx, vy, d0, g0, c0 = self.v_frame
                for p in self.samples(line, 4.0):
                    zt = self.walk_z(wk, p.x, p.y)
                    t = unit(ux, uy)
                    for side in (-1, 1):
                        hx, hy = p.x + vx * side * (W / 2 - 0.05), p.y + vy * side * (W / 2 - 0.05)
                        P.add("skyway", "walk", hx, hy, obox(hx, hy, ux, uy, 0.03, 0.03, zt + RAIL_H, d0, "gunmetal"), col="col")
            else:
                for p in self.samples(line, 6.5):
                    zt = self.walk_z(wk, p.x, p.y)
                    d = line.project(p)
                    q = line.interpolate(min(d + 0.3, line.length))
                    q0 = line.interpolate(max(d - 0.3, 0))
                    t = unit(q.x - q0.x, q.y - q0.y)
                    for side in (-1, 1):
                        hx, hy = p.x - t[1] * side * (W / 2 - 0.15), p.y + t[0] * side * (W / 2 - 0.15)
                        roof = self.roof_at(hx, hy)
                        pt = Point(hx, hy)
                        if roof is None and self.O.contains(pt) and len(zs) > 2 and len(set(zs)) > 1:
                            continue     # the roof run doesn't post into the street
                        zb = roof if roof is not None else self.ground_level(hx, hy)
                        if zt - WALK_DECK - zb < 0.3:
                            continue
                        sec = P.district_sector(hx, hy)
                        P.add(sec, "walk", hx, hy, obox(hx, hy, t[0], t[1], 0.1, 0.1, zb, zt - WALK_DECK, "rust_metal"), col="col")
            # stairs down at ends that are over open ground: straight on if that lands clear,
            # else off to the side that does
            if not hung:
                for end, nxt in ((pts[0], pts[1]), (pts[-1], pts[-2])):
                    zt = self.walk_z(wk, *end)
                    if self.roof_at(*end) is not None:
                        continue
                    if self.B.distance(Point(*end)) < 0.5:
                        # it ends against a building's wall: a closed end (railed), no stairs
                        self.closed_ends.append((wk.get("name"), end))
                        continue
                    g = self.ground_level(*end)
                    t0 = unit(end[0] - nxt[0], end[1] - nxt[1])
                    run = int(round((zt - g) / 0.25)) * 0.28
                    for t in (t0, (-t0[1], t0[0]), (t0[1], -t0[0])):
                        n = (-t[1], t[0])
                        w = min(W, 1.8) / 2 + 0.3
                        foot = Polygon([(end[0] + n[0] * w, end[1] + n[1] * w), (end[0] - n[0] * w, end[1] - n[1] * w),
                                        (end[0] - n[0] * w + t[0] * run, end[1] - n[1] * w + t[1] * run),
                                        (end[0] + n[0] * w + t[0] * run, end[1] + n[1] * w + t[1] * run)])
                        if not foot.intersects(self.B) and not foot.intersects(self.W) and self.R.contains(foot):
                            self.stair_flight(P.district_sector(*end), end, t, W, zt, g)
                            break
                    else:
                        raise SystemExit(f"walkway {wk.get('name')}: no clear ground for stairs at {end}")

    def rail_sloped(self, sector, a, b, inward, za, zb, mat="rust_metal", inset=0.1):
        P = self.P
        L = math.dist(a, b)
        t = unit(b[0] - a[0], b[1] - a[1])
        A = (a[0] + inward[0] * inset, a[1] + inward[1] * inset)
        Bp = (b[0] + inward[0] * inset, b[1] + inward[1] * inset)
        mx, my = (A[0] + Bp[0]) / 2, (A[1] + Bp[1]) / 2
        prims = P.obj(sector, "walk", mx, my, col="col")
        n = max(1, int(math.ceil(L / 2.0)))
        for q in range(n + 1):
            f = q / n
            px, py = A[0] + (Bp[0] - A[0]) * f, A[1] + (Bp[1] - A[1]) * f
            z = za + (zb - za) * f
            prims.append(obox(px, py, t[0], t[1], 0.03, 0.03, z, z + RAIL_H - 0.05, mat))
        prims.append(beam((A[0], A[1], za + RAIL_H - 0.05), (Bp[0], Bp[1], zb + RAIL_H - 0.05), 0.05, 0.05, mat))
        prims.append(beam((A[0], A[1], za + 0.5), (Bp[0], Bp[1], zb + 0.5), 0.04, 0.04, mat))

    def stair_flight(self, sector, start, t, width, z_top, z_bottom):
        """Open steel stairs from a walkway end down to the ground, running along t.
        Treads are floating slabs, 0.25 m risers; the last tread is the ground."""
        P = self.P
        risers = max(1, int(round((z_top - z_bottom) / 0.25)))
        rise = (z_top - z_bottom) / risers
        run = 0.28
        n = (-t[1], t[0])
        w = min(width, 1.8)
        for k in range(1, risers):
            s0, s1 = (k - 1) * run, k * run
            ztop = z_top - rise * k
            c = [(start[0] + t[0] * s + n[0] * v, start[1] + t[1] * s + n[1] * v) for s, v in
                 ((s0, -w / 2), (s1, -w / 2), (s1, w / 2), (s0, w / 2))]
            mx, my = (c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2
            P.add(sector, "walk", mx, my, hexa(c, ztop - 0.06, ztop, ["rust_metal", "diamond_plate"] + ["rust_metal"] * 4), col="col")
        end = (start[0] + t[0] * run * risers, start[1] + t[1] * run * risers)
        self.flights.append(Polygon([(start[0] + n[0] * v, start[1] + n[1] * v) for v in (-w / 2, w / 2)]
                                    + [(end[0] + n[0] * v, end[1] + n[1] * v) for v in (w / 2, -w / 2)]))
        for side in (-1, 1):
            a = (start[0] + n[0] * side * (w / 2 + 0.05), start[1] + n[1] * side * (w / 2 + 0.05), z_top - 0.3)
            b = (end[0] + n[0] * side * (w / 2 + 0.05), end[1] + n[1] * side * (w / 2 + 0.05), z_bottom)
            P.add(sector, "walk", (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, beam(a, b, 0.08, 0.25, "rust_metal"), col="col")
            self.rail_sloped(sector, (a[0], a[1]), (b[0], b[1]), (0.0, 0.0), z_top, z_bottom + rise)

    # the service lift ---------------------------------------------------------------------
    def lift(self, sector, x0, y0, x1, y1, z):
        """An open lift tower from the ground to the Skyway's underside; the car waits at the bottom."""
        P = self.P
        top = self.v_frame[6] if self.viaduct else z + 11.0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            lo, hi = (px - 0.14, py - 0.14, z), (px + 0.14, py + 0.14, top)
            P.add("skyway", "walk", px, py, box_prim(lo, hi, "hazard_stripes", skip=[0]), col="col")
        for zz in (3.2, 6.4, 9.6):
            for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
                P.add("skyway", "walk", cx, cy, beam((a[0], a[1], zz), (b[0], b[1], zz), 0.12, 0.12, "rust_metal"), col="col")
        car = P.obj("skyway", "prop", col="col", extras=PROP_EXTRAS, origin=(cx, cy, z), name="prop_lift_car")
        car.append(box_prim((x0 + 0.2, y0 + 0.2, z), (x1 - 0.2, y1 - 0.2, z + 0.12), ["rust_metal", "diamond_plate"] + ["rust_metal"] * 4, skip=[0]))
        for (a, b) in (((x0 + 0.25, y0 + 0.25), (x1 - 0.25, y0 + 0.25)), ((x0 + 0.25, y1 - 0.25), (x1 - 0.25, y1 - 0.25))):
            car.append(beam((a[0], a[1], z + 1.05), (b[0], b[1], z + 1.05), 0.05, 0.05, "hazard_stripes"))
        P.lamp_entity("skyway", "wall_lamp", x0 - 0.21, cy, 2.8, 270.0)

    def mouse_stairs(self):
        """A fire-escape flight up the side of a low roof where a walkway starts."""
        P = self.P
        for wk in self.walkways:
            if wk.get("hung"):
                continue
            for end in (wk["pts"][0], wk["pts"][-1]):
                b = next((bb for bb in self.named if bb["id"] != "ferry" and bb["_g"].contains(Point(*end))), None)
                if b is None or b.get("_h") is None or b["_h"] > 6.5 or STYLES.get("shanty") is None:
                    continue
                pg = oriented(b["_g"])
                h = b["_h"]
                risers = int(round(h / 0.25))
                run = risers * 0.28
                door_pts = [dd[6] for dd in self.door_boxes(b) if dd[5]]
                best = None
                for a, bb in self.ring_edges(pg, pg.exterior.coords):
                    L = math.dist(a, bb)
                    if L < run + 0.8:
                        continue
                    t = unit(bb[0] - a[0], bb[1] - a[1])
                    n = self.outward(pg, a, bb)
                    # the flight is 0.85 m wide, 0.15 m off the wall: neighbouring lots stand 1.2 m or more away
                    strip = Polygon([(a[0] + n[0] * 0.1, a[1] + n[1] * 0.1), (bb[0] + n[0] * 0.1, bb[1] + n[1] * 0.1),
                                     (bb[0] + n[0] * 1.15, bb[1] + n[1] * 1.15), (a[0] + n[0] * 1.15, a[1] + n[1] * 1.15)])
                    if strip.intersects(self.B) or strip.intersects(self.W) or strip.intersects(self.PIT):
                        continue
                    has_door = any(abs((d[0] - a[0]) * n[0] + (d[1] - a[1]) * n[1]) < 0.05 for d in door_pts)
                    score = (0 if has_door else 10) + L
                    if best is None or score > best[0]:
                        best = (score, a, bb, t, n, L)
                if best is None:
                    continue
                _, a, bb, t, n, L = best
                sector = P.district_sector(*b["_g"].representative_point().coords[0])
                w = 0.85
                top = (bb[0] - t[0] * 0.4 + n[0] * (0.15 + w / 2), bb[1] - t[1] * 0.4 + n[1] * (0.15 + w / 2))
                g = self.ground_level(top[0] + n[0] * 0.5, top[1] + n[1] * 0.5)
                self.stair_flight(sector, top, (-t[0], -t[1]), w, h + 0.05, g)
                # landing from the top tread onto the roof
                P.add(sector, "walk", top[0], top[1],
                      edge_box(frame(bb, (-t[0], -t[1]), n), 0.0, 1.2, -0.6, 0.15 + w + 0.05, h - 0.02, h + 0.05,
                               ["rust_metal", "diamond_plate"] + ["rust_metal"] * 4), col="col")

    # layout props, the rail line -----------------------------------------------------------
    def props(self):
        P = self.P
        for fx in self.m.get("props", []):
            g = RM.shape_geom(fx)
            c = g.centroid
            sector = P.district_sector(c.x, c.y)
            self.fixture(sector, fx, None, None)
        rail = next((o for o in self.streets if o["name"] == "rail"), None)
        if rail:
            line = LineString(rail["pts"])
            vis = lambda x, y: P.obj("streets", "rails", x, y)  # noqa: E731
            for p in self.samples(line, 0.9):
                d = line.project(p)
                q = line.interpolate(min(d + 0.2, line.length))
                q0 = line.interpolate(max(d - 0.2, 0))
                t = unit(q.x - q0.x, q.y - q0.y)
                vis(p.x, p.y).append(obox(p.x, p.y, -t[1], t[0], 1.25, 0.13, STREET_Z, STREET_Z + 0.12, "rust_metal", skip=[0]))
            for side in (-1, 1):
                off = line.offset_curve(side * 0.75, join_style=2)
                coords = list(off.coords)
                for k in range(len(coords) - 1):
                    a, b = coords[k], coords[k + 1]
                    vis((a[0] + b[0]) / 2, (a[1] + b[1]) / 2).append(
                        beam((a[0], a[1], STREET_Z + 0.12), (b[0], b[1], STREET_Z + 0.12), 0.08, 0.1, "gunmetal"))
            # buffer stop at the line's first point
            a, b = rail["pts"][0], rail["pts"][1]
            t = unit(b[0] - a[0], b[1] - a[1])
            P.add("streets", "walk", a[0], a[1], obox(a[0] + t[0] * 0.6, a[1] + t[1] * 0.6, t[0], t[1], 0.5, 1.3,
                                                     STREET_Z, STREET_Z + 1.1, ["rust_metal", "hazard_stripes"] + ["hazard_stripes"] * 4), col="col")

    # street lighting --------------------------------------------------------------------------
    def lamp_post(self, x, y, ax, ay, sector="streets", z=None, height=LAMP_H, light=True):
        """A sodium street lamp at (x, y) whose arm reaches along (ax, ay). Without a light it
        is a fixture with a corona only (the Skyway's deck lamps, which nobody walks under)."""
        P = self.P
        z = self.ground_level(x, y) if z is None else z
        prims = P.obj(sector, "walk", x, y, col="col")
        prims.append(cyl(x, y, z, 0.18, 0.45, "gunmetal", seg=10))
        prims.append(cyl(x, y, z + 0.45, 0.08, height - 0.45, "gunmetal", seg=8))
        hx, hy = x + ax * 1.3, y + ay * 1.3
        prims.append(beam((x, y, z + height - 0.08), (hx, hy, z + height - 0.08), 0.08, 0.08, "gunmetal"))
        prims.append(obox(hx, hy, ax, ay, 0.32, 0.16, z + height - 0.2, z + height + 0.02, "gunmetal"))
        prims.append(obox(hx, hy, ax, ay, 0.26, 0.11, z + height - 0.23, z + height - 0.2, "lamp_glow"))
        if light:
            P.light(sector, "sodium", hx, hy, z + height - 0.5, corona_at=(hx, hy, z + height - 0.35))
        else:
            P.corona(sector, "sodium", hx, hy, z + height - 0.35)
        if sector == "streets":
            self.lamps.append((x, y))

    def near_lamp(self, x, y, d):
        return any(math.dist((x, y), q) < d for q in self.lamps)

    def street_lamps(self):
        self.lamps = []
        pillars = [(p["x"], p["y"]) for p in RM.viaduct_pillars(self.viaduct)] if self.viaduct else []
        for o in self.streets:
            if o["name"] == "rail" or o["w"] < 5:
                continue
            line = LineString(o["pts"])
            side = 1
            d = 7.0
            def spot(dd, s):
                """The lamp's place dd along the street on side s, and the way its arm reaches."""
                p = line.interpolate(dd)
                q = line.interpolate(min(dd + 0.5, line.length))
                t = unit(q.x - p.x, q.y - p.y)
                n = (-t[1], t[0])
                return p.x + n[0] * s * (o["w"] / 2 + 0.9), p.y + n[1] * s * (o["w"] / 2 + 0.9), -n[0] * s, -n[1] * s
            while d < line.length - 2:
                for s in (side, -side):
                    x, y, ax, ay = spot(d, s)
                    # a lamp at a ladder's top steps along the street, out of the climber's way
                    for shift in (2.5, -2.5):
                        if any(math.dist((x, y), ld["at"]) < 2.0 for ld in self.ladders) and 0 < d + shift < line.length:
                            x, y, ax, ay = spot(d + shift, s)
                    pt = Point(x, y)
                    if not self.paved_p.contains(pt) or self.B.distance(pt) < 0.5 or self.near_lamp(x, y, 7.0):
                        continue
                    if any(math.dist((x, y), pp) < 2.0 for pp in pillars) or self.bridge_u.distance(pt) < 1.0:
                        continue
                    if any(math.dist((x, y), ld["at"]) < 2.0 for ld in self.ladders):
                        continue
                    self.lamp_post(x, y, ax, ay)
                    break
                side = -side
                d += LAMP_EVERY
        for o in self.m.get("open", []):
            if "poly" not in o or "floor_m" in o:
                continue
            pg = oriented(o["_g"])
            ring = LineString(list(pg.exterior.coords))
            d = 4.0
            while d < ring.length:
                p = ring.interpolate(d)
                q = ring.interpolate(min(d + 0.5, ring.length))
                t = unit(q.x - p.x, q.y - p.y)
                for s in (1, -1):
                    n = (-t[1] * s, t[0] * s)
                    x, y = p.x + n[0] * 1.0, p.y + n[1] * 1.0
                    pt = Point(x, y)
                    if not o["_g"].contains(pt):
                        continue
                    if not (self.plaza_p.contains(pt) or self.paved_p.contains(pt)) or self.B.distance(pt) < 0.5:
                        continue
                    if self.near_lamp(x, y, 12.0) or any(math.dist((x, y), pp) < 2.5 for pp in pillars):
                        continue
                    if self.viaduct and self.vfoot.contains(pt):
                        continue
                    self.lamp_post(x, y, n[0], n[1])
                    break
                d += LAMP_EVERY

    def wall_lamps(self):
        """Wall lamps (the game's wall_lamp scene) on facades along the narrow lanes."""
        P = self.P
        placed = []
        for o in self.streets:
            if o["name"] == "rail" or o["w"] >= 5:
                continue
            line = LineString(o["pts"])
            d = 5.0
            while d < line.length:
                p = line.interpolate(d)
                best = None
                for sector, e, h in self.facades:
                    a, b, t, n, L, occupied, look = e
                    if look != "street":
                        continue
                    s = (p.x - a[0]) * t[0] + (p.y - a[1]) * t[1]
                    if s < 0.8 or s > L - 0.8:
                        continue
                    off = (p.x - a[0]) * n[0] + (p.y - a[1]) * n[1]
                    if off < 0 or off > o["w"] / 2 + 2.5:
                        continue
                    if best is None or off < best[0]:
                        best = (off, sector, e, s)
                if best is not None:
                    off, sector, e, s = best
                    a, b, t, n, L, occupied, _ = e
                    # a door within 2 m gets the lamp over it (openspec/changes/hub-doorways, design section 3.5)
                    near = sorted((q - s for q in self.edge_doors.get(id(occupied), []) if abs(q - s) <= 2.0), key=abs)
                    for ds in near[:1] + [0, 1.0, -1.0, 2.0, -2.0]:
                        ss = s + ds
                        if ss < 0.8 or ss > L - 0.8:
                            continue
                        if any(s0 - 0.35 < ss < s1 + 0.35 and top >= WALL_LAMP_Z - 0.3 for s0, s1, top in occupied):
                            continue
                        x, y = a[0] + t[0] * ss + n[0] * 0.07, a[1] + t[1] * ss + n[1] * 0.07
                        if any(math.dist((x, y), q) < 7.0 for q in placed):
                            break
                        P.lamp_entity(sector, "wall_lamp", x, y, WALL_LAMP_Z, heading_of(*n))
                        placed.append((x, y))
                        break
                d += WALL_LAMP_EVERY

    # the edge of the map -----------------------------------------------------------------------
    def boundary(self):
        """An invisible wall round the map, and a backdrop of blank city walls where open ground
        or water meets the edge (except at exits, which get a short street stub)."""
        P = self.P
        W, H = P.W, P.H
        for lo, hi in (((-1.0, -1.0, -8.0), (0.0, H + 1.0, 45.0)), ((W, -1.0, -8.0), (W + 1.0, H + 1.0, 45.0)),
                       ((-1.0, -1.0, -8.0), (W + 1.0, 0.0, 45.0)), ((-1.0, H, -8.0), (W + 1.0, H + 1.0, 45.0))):
            P.obj("streets", "bounds", name="streets_bounds", col="colonly").append(box_prim(lo, hi, "concrete"))
        exits = [e for e in self.entities_in if e["kind"] == "exit"]
        edges = [((0, 0), (W, 0), (0, -1)), ((W, 0), (W, H), (1, 0)), ((W, H), (0, H), (0, 1)), ((0, H), (0, 0), (-1, 0))]
        for a, b, n in edges:
            L = math.dist(a, b)
            t = unit(b[0] - a[0], b[1] - a[1])
            runs = []
            cur = None
            steps = int(L / 0.5)
            for q in range(steps + 1):
                s = L * q / steps
                x, y = a[0] + t[0] * s - n[0] * 0.3, a[1] + t[1] * s - n[1] * 0.3
                free = not self.B_p.contains(Point(x, y))
                gap = any(math.dist((x, y), e["at"][:2]) < 5.5 for e in exits)
                if free and not gap:
                    cur = [s, s] if cur is None else [cur[0], s]
                else:
                    if cur and cur[1] - cur[0] > 0.9:
                        runs.append(cur)
                    cur = None
            if cur and cur[1] - cur[0] > 0.9:
                runs.append(cur)
            for s0, s1 in runs:
                Pf = frame(a, t, n)
                mid = Pf((s0 + s1) / 2, 0.3)
                bed = min([w["bed"] for w in self.waters if w["g"].intersects(LineString([Pf(s0, -0.3), Pf(s1, -0.3)]))] or [0.0])
                zb = bed if bed < 0 else -0.5
                hgt = 10.0
                rng = random.Random(f"{P.seed}:edge:{a}:{s0:.1f}")
                mat = ["brick_wall", "concrete", "stone_blocks"][int(rng.random() * 3)]
                solid = prism(Polygon([Pf(s0, 0.0), Pf(s1, 0.0), Pf(s1, 1.0), Pf(s0, 1.0)]), zb, hgt,
                              {"side": mat, "top": "concrete", "bottom": mat}, caps=["top", "bottom"])
                cutters = []
                inward = frame(b, (-t[0], -t[1]), (-n[0], -n[1]))
                for zr in (4.6, 7.4):
                    s = s0 + 1.5
                    while s < s1 - 1.5:
                        cutters.append(self.recess(inward, L - s - 0.6, L - s + 0.6, zr, zr + 1.4, 0.18,
                                                   self.window_mat(rng, STYLES["strip"]), "concrete"))
                        s += 3.0
                sec = P.district_sector(min(max(mid[0], 0.5), W - 0.5), min(max(mid[1], 0.5), H - 0.5))
                P.obj(sec, "vis", mid[0], mid[1]).append({"t": "bool", "solid": solid, "cutters": cutters, "interior": None})
        # a street stub beyond each exit on the edge
        for e in exits:
            x, y = e["at"][:2]
            for a, b, n in edges:
                t = unit(b[0] - a[0], b[1] - a[1])
                off = (x - a[0]) * n[0] + (y - a[1]) * n[1]
                s = (x - a[0]) * t[0] + (y - a[1]) * t[1]
                if -3.0 < off <= 0 and 0 < s < math.dist(a, b):
                    Pf = frame(a, t, n)
                    sec = P.district_sector(x, y)
                    stub = P.obj(sec, "vis", x, y)
                    stub.append(prism(Polygon([Pf(s - 5.5, 0), Pf(s + 5.5, 0), Pf(s + 5.5, 14), Pf(s - 5.5, 14)]),
                                      STREET_Z, STREET_Z, {"top": "asphalt", "side": "concrete", "bottom": "concrete"}))
                    for s_, w_ in ((s - 5.5, -1.0), (s + 5.5, 1.0)):
                        stub.append(prism(Polygon([Pf(s_, 0), Pf(s_ + w_, 0), Pf(s_ + w_, 14), Pf(s_, 14)]), -0.5, 10.0,
                                          {"side": "brick_wall", "top": "concrete", "bottom": "concrete"}, caps=["top"]))
                    stub.append(prism(Polygon([Pf(s - 6.5, 14), Pf(s + 6.5, 14), Pf(s + 6.5, 15), Pf(s - 6.5, 15)]), -0.5, 10.0,
                                      {"side": "rust_metal", "top": "concrete", "bottom": "concrete"}, caps=["top"]))
                    lx, ly = Pf(s, 13.0)
                    P.light(sec, "sodium", lx, ly, 5.0, corona_at=Pf(s, 13.93) + (5.2,))
                    stub.append(obox(*Pf(s, 13.95), t[0], t[1], 0.3, 0.05, 5.0, 5.4, "lamp_glow"))

    # entities ----------------------------------------------------------------------------------
    def in_room(self, x, y):
        for b in self.named:
            for r in b.get("rooms", []):
                x0, y0, x1, y1 = r["rect"]
                if x0 <= x <= x1 and y0 <= y <= y1:
                    return b
        return None

    def service_deck_z(self, x, y):
        for wk in self.walkways:
            if wk.get("hung"):
                return self.walk_z(wk, x, y)
        return None

    def marker_z(self, x, y):
        """Height for map markers: a room's floor, a walkway over a roof, the roof, or the ground."""
        if self.in_room(x, y):
            return FLOOR_Z
        pt = Point(x, y)
        if self.B_p.contains(pt):
            for wk in self.walkways:
                if self.walk_poly(wk).contains(pt):
                    return self.walk_z(wk, x, y)
            r = self.roof_at(x, y)
            if r is not None:
                return r
        return self.ground_level(x, y)

    def entity_z(self, e):
        x, y = e["at"][0], e["at"][1]
        z = e.get("z")
        if isinstance(z, (int, float)):
            return float(z)
        if z == "roof":
            r = self.roof_at(x, y)
            if r is not None:
                return r
            for wk in self.walkways:
                if not wk.get("hung") and self.walk_poly(wk).buffer(0.5).contains(Point(x, y)):
                    return self.walk_z(wk, x, y)
            raise SystemExit(f"entity {e['kind']}:{e['id']} asks for a roof at {x}, {y} and there is none")
        if z == "service_deck":
            zz = self.service_deck_z(x, y)
            if zz is None:
                raise SystemExit(f"entity {e['kind']}:{e['id']} asks for the service deck and the layout has none")
            return zz
        if z is not None:
            raise SystemExit(f"entity {e['kind']}:{e['id']}: unknown z {z!r}")
        if self.in_room(x, y):
            return FLOOR_Z
        return self.ground_level(x, y)

    def place_entities(self):
        P = self.P
        m = self.m
        # the player start: the safehouse lobby, facing south
        start = next((e for e in self.entities_in if e["kind"] == "spawn" and e["id"] == "start"), None)
        sx, sy = (start["at"] if start else next(p["at"] for p in m["pois"] if p["n"] == 5))[:2]
        P.entity(P.district_sector(sx, sy), "ENT_player_start", sx, sy, self.entity_z({"at": (sx, sy), "kind": "spawn", "id": "start"}),
                 start["facing_deg"] if start else 180.0, {"kind": "player_start", "id": "player_start"})
        for p in m.get("pois", []):
            x, y = p["at"]
            P.entity(P.district_sector(x, y), f"ENT_poi_{p['n']}", x, y, self.marker_z(x, y), 0.0,
                     {"kind": "poi", "id": str(p["n"]), "poi": p["n"], "category": p["cat"], "name": p["name"]})
        for ms in m.get("missions", []):
            x, y = ms.get("anchor") or ms["at"]
            P.entity(P.district_sector(x, y), f"ENT_mission_{ms['code']}", x, y, self.marker_z(x, y), 0.0,
                     {"kind": "mission", "id": ms["code"], "code": ms["code"], "name": ms["name"],
                      "map_at": [float(v) for v in ms["at"]]})
        seen = set()
        for e in self.entities_in:
            kind, eid = e["kind"], str(e["id"])
            safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in eid)
            if safe.isdigit():
                raise SystemExit(f"entity id {eid!r}: ids must not be bare numbers (ENT_{kind}_{eid} would read as a numbered {kind})")
            name = f"ENT_{kind}_{safe}"
            if name in seen:
                raise SystemExit(f"duplicate entity {name}")
            seen.add(name)
            x, y = e["at"][0], e["at"][1]
            extras = {k: v for k, v in e.get("props", {}).items()}
            extras.update({"kind": kind, "id": eid, "facing_deg": float(e.get("facing_deg", 0.0))})
            P.entity(P.district_sector(x, y), name, x, y, self.entity_z(e), e.get("facing_deg", 0.0), extras)

    # checks and the whole build ----------------------------------------------------------------------
    def check_zfighting(self):
        """CLAUDE.md 7.2: every axis-aligned box the build makes, per building and outside."""
        for name, grp in sorted(self.P.zboxes.items()):
            detailing.assert_no_zfighting(f"{self.m['id']}:{name}", grp["airs"], grp["details"])

    def check_rooms_carved(self):
        """Every room and doorway of an enterable building is carved out of its block: each
        interior box has its cutter. (A sign once took the cutters in its zone with it, and left
        the Tsang Shrine's hall, the garage's bay and the checkpoint's room solid.)"""
        problems = []
        for sec in self.P.order:
            for obj in self.P.sectors[sec]["objects"].values():
                for pr in obj["prims"]:
                    if pr.get("t") != "bool" or not pr.get("interior"):
                        continue
                    cut = set()
                    for c in pr["cutters"]:
                        if c.get("t") == "hexa":
                            xs, ys = [q[0] for q in c["p"]], [q[1] for q in c["p"]]
                            cut.add((round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)))
                    for lo, hi in pr["interior"]["boxes"]:
                        # interior boxes are the airs grown by 0.02 m, in (x, y, up)
                        key = (round(lo[0] + 0.02, 2), round(lo[1] + 0.02, 2), round(hi[0] - 0.02, 2), round(hi[1] - 0.02, 2))
                        if key not in cut:
                            problems.append(f"{pr['interior']['object']}: the room or door at x {key[0]}-{key[2]}, "
                                            f"y {key[1]}-{key[3]} has no cutter, so it stays solid")
        if problems:
            raise SystemExit(f"{self.m['id']}: {len(problems)} rooms aren't carved:\n  " + "\n  ".join(problems))

    # doors (openspec/changes/hub-doorways) -------------------------------------------
    def door_problems(self):
        """Every door an enterable building declares is framed by detailing.door_frame, carved at
        its fits, and has wall enough for its frame ("Every doorway is framed")."""
        problems = []
        for b in self.named:
            for d in RM.named_doors(b) if b.get("doors") else []:
                name = f"{b['id']} door {d['i']} at ({d['x']:g}, {d['y']:g}), {d['w']:g} m"
                f = self.frames.get((b["id"], d["i"]))
                if f is None:
                    problems.append(f"{name}: no frame")
                    continue
                want = detailing.door_fits(*f["clear"])
                if any(abs(c - w) > 1e-6 for c, w in zip(f["carved"], want)):
                    problems.append(f"{name}: carved {f['carved'][0]:.2f} x {f['carved'][1]:.2f} m, not its fits "
                                    f"{want[0]:.2f} x {want[1]:.2f}")
                if f["wall"] < 0:
                    problems.append(f"{name}: its {f['kind']} overruns the wall it stands in by {-f['wall']:.2f} m")
        return problems

    def walkable_edges(self, pg):
        """A building's facade edges that face walkable ground: 2.2 m or longer (room for a door
        frame and 0.35 m to each end), looking at a street or a paved side passage."""
        pgo = oriented(pg)
        out = []
        for a, b in self.ring_edges(pgo, pgo.exterior.coords):
            if math.dist(a, b) < 2.2:
                continue
            n = self.outward(pgo, a, b)
            look = self.facing((a[0] + b[0]) / 2 + n[0] * 2.6, (a[1] + b[1]) / 2 + n[1] * 2.6)
            if look in ("street", "side"):
                out.append((a, b, look))
        return out

    def building_door_problems(self):
        """Every building that faces walkable ground shows a door on such an edge: a declared
        entrance, or a dressing door ("Every building on the street shows a door")."""
        buildings = [(f"lot {lot['id']}", lot["poly"]) for lot in self.lots]
        buildings += [(b["id"], b["_g"]) for b in self.named if b["id"] != "ferry"]
        shown = {}
        for key, x, y in self.shown_doors:
            shown.setdefault(key, []).append(Point(x, y))
        problems = []
        for key, pg in buildings:
            edges = self.walkable_edges(pg)
            if not edges:
                continue
            if any(LineString([a, b]).distance(pt) < 0.05 for a, b, _ in edges for pt in shown.get(key, [])):
                continue
            a, b, look = max(edges, key=lambda e: math.dist(e[0], e[1]))
            problems.append(f"{key}: no door on its {len(edges)} walkable edge{'s' if len(edges) > 1 else ''}; "
                            f"the longest runs ({a[0]:.1f}, {a[1]:.1f}) to ({b[0]:.1f}, {b[1]:.1f}) on a {look}")
        return problems

    def door_approach_problems(self):
        """Every exterior door opens onto ground a person can reach ("Every door opens onto ground
        a person can reach"): its approach (render_map.door_approach) is clear of buildings, lots,
        fixtures, props, solids and water; an entrance's reaches open ground; a service door's
        landing joins open ground by walkable ground 1.2 m wide or more."""
        room = self.standing_room()
        solids = [(name, fp) for name, fp, z0, z1 in self.P.solids if z1 > STANDING_STEP_M + PAVED_Z and z0 < 2.0]
        blockers = room["footprints"] + solids
        problems = []
        walk = None
        for b, d, ap in RM.door_approaches(self.m, self.geo):
            name = f"{b['id']} door {d['i']} at ({d['x']:g}, {d['y']:g}), a {d['w']:g} m {ap['kind']}"
            strip = ap["poly"]
            in_way = []
            for lot in self.lots:
                if strip.intersection(lot["poly"]).area > 1e-3:
                    nx, ny = d["n"]
                    depth = min(((q[0] - d["x"]) * nx + (q[1] - d["y"]) * ny)
                                for q in polys(strip.intersection(lot["poly"]))[0].exterior.coords)
                    in_way.append(f"lot {lot['id']} ({depth:.2f} m out)")
            others = [bb for bb in self.named if bb is not b and bb["id"] != "ferry"]
            in_way += [bb["id"] for bb in others if strip.intersection(bb["_g"]).area > 1e-3]
            in_way += [nm for nm, fp in blockers if strip.intersection(fp).area > 1e-3]
            if strip.intersection(room["water"]).area > 1e-3:
                in_way.append("water")
            if in_way:
                problems.append(f"{name}: its approach is blocked by {', '.join(sorted(set(in_way)))}")
                continue
            if ap["kind"] == "entrance" and not ap["reached"]:
                problems.append(f"{name}: its approach doesn't reach open ground within {RM.ENTRANCE_REACH_M:g} m")
            elif ap["kind"] == "service":
                if walk is None:
                    ground = box(0, 0, self.P.W, self.P.H).difference(self.B).difference(room["water"])
                    ground = ground.difference(unary_union([fp for _, fp in blockers]))
                    walk = ground.buffer(-0.6, join_style=2)
                nx, ny = d["n"]
                probe = Point(d["x"] + nx * (RM.LANDING_M - 0.7), d["y"] + ny * (RM.LANDING_M - 0.7))
                part = next((g for g in polys(walk) if g.buffer(1e-6).contains(probe)), None)
                if part is None or not part.intersects(self.O):
                    problems.append(f"{name}: its landing joins no street by ground 1.2 m wide")
        return problems

    def check_doors(self):
        for fn, what in ((self.door_problems, "doors aren't framed"),
                         (self.sliding_room_problems, "sliding leaves have no room to open"),
                         (self.building_door_problems, "buildings on the street show no door"),
                         (self.door_approach_problems, "doors open onto ground nobody can reach")):
            problems = fn()
            if problems:
                raise SystemExit(f"{self.m['id']}: {len(problems)} {what}:\n  " + "\n  ".join(problems))

    def standing_spots(self):
        """Where the level stands a person: every NPC and civilian, every stop on a patrol and
        every spawn point, as (label, x, y, z, place, body). place is "indoors", "outdoors" or
        "raised" (an explicit z: a roof or the service deck, checked against details only, since
        it stands above walls and shells); body is "npc" or "player", whose collider it takes."""
        spots = []
        for e in self.entities_in:
            if e["kind"] not in ("npc", "civ", "spawn"):
                continue
            x, y = e["at"][0], e["at"][1]
            place = "raised" if e.get("z") is not None else ("indoors" if self.in_room(x, y) else "outdoors")
            body = "player" if e["kind"] == "spawn" else "npc"
            spots.append((f"{e['kind']}:{e['id']}", x, y, self.entity_z(e), place, body))
            patrol = e.get("props", {}).get("patrol")
            for i, stop in enumerate(patrol.split(";") if patrol else []):
                px, py = (float(v) for v in stop.split(","))
                pz = self.entity_z({"kind": e["kind"], "id": e["id"], "at": (px, py)})
                spots.append((f"{e['kind']}:{e['id']} patrol stop {i}", px, py, pz,
                              "indoors" if self.in_room(px, py) else "outdoors", body))
        return spots

    def standing_room(self):
        """What a standing spot is checked against, built once per plan: the detail boxes, the
        footprints of the layout's fixtures and props, the rooms' air and the colliders' sizes."""
        if getattr(self, "_standing", None) is None:
            details = []
            for grp in self.P.zboxes.values():
                for lo, hi, label in grp["details"]:
                    # stored as (x, up, y), for the z-fighting check
                    details.append((label, min(lo[0], hi[0]), min(lo[2], hi[2]), min(lo[1], hi[1]),
                                    max(lo[0], hi[0]), max(lo[2], hi[2]), max(lo[1], hi[1])))
            footprints = [(f"{fx[-1]} prop", RM.shape_geom(fx)) for fx in self.m.get("props", [])
                          if fx[-1] not in WALK_THROUGH_CLASSES]
            footprints += [(f"{b['id']} {fx[-1]}", RM.shape_geom(fx)) for b in self.m["buildings"]
                           for fx in b.get("fixtures", []) if fx[-1] not in WALK_THROUGH_CLASSES]
            air = unary_union([box(a.x[0], a.z[0], a.x[1], a.z[1])
                               for grp in self.P.zboxes.values() for a in grp["airs"]]).buffer(1e-6)
            self._standing = {"details": details, "footprints": footprints, "air": air,
                              "water": self.W.difference(self.bridge_u.buffer(0.05)),   # a bridge deck is walked on
                              "bodies": {"npc": scene_collider(NPC_SCENE), "player": scene_collider(PLAYER_SCENE)}}
        return self._standing

    def standing_problems(self, label, x, y, z, place, body):
        """Why a person of this body can't stand here, or [] when they can (see check_standing_room)."""
        room = self.standing_room()
        radius, height = room["bodies"][body]
        foot = Point(x, y).buffer(radius, quad_segs=16)
        problems = []

        def into(fp):
            return radius - fp.distance(Point(x, y))
        for name, x0, y0, z0, x1, y1, z1 in room["details"]:
            if z1 <= z + STANDING_STEP_M or z0 >= z + height:
                continue    # underfoot, or overhead
            gap = math.hypot(max(x0 - x, 0.0, x - x1), max(y0 - y, 0.0, y - y1)) - radius
            if gap < 0:
                problems.append(f"{label} at ({x:g}, {y:g}) is {-gap:.2f} m inside a {name} "
                                f"(x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f}, z {z0:.2f}-{z1:.2f})")
        for name, fp, z0, z1 in self.P.solids:
            if z1 > z + STANDING_STEP_M and z0 < z + height and foot.intersects(fp):
                problems.append(f"{label} at ({x:g}, {y:g}) stands in a {name} ({into(fp):.2f} m into it)")
        if place == "raised":
            return problems
        for name, fp in room["footprints"]:
            if foot.intersects(fp):
                problems.append(f"{label} at ({x:g}, {y:g}) stands in a {name} ({into(fp):.2f} m into it)")
        if place == "indoors":
            if not room["air"].contains(foot):
                problems.append(f"{label} at ({x:g}, {y:g}) reaches into a wall: "
                                f"{foot.difference(room['air']).area:.3f} m2 of its footprint is outside the rooms")
            return problems
        if foot.intersects(self.B):
            problems.append(f"{label} at ({x:g}, {y:g}) is {into(self.B):.2f} m inside a building")
        if foot.intersects(room["water"]):
            wid = next((w["id"] for w in self.waters if foot.intersects(w["g"])), "water")
            problems.append(f"{label} at ({x:g}, {y:g}) stands in the water of {wid} ({into(room['water']):.2f} m into it)")
        # level ground: a person astride a curb or a stair edge has a foot in it
        ring = [(x + radius * math.cos(a * math.pi / 4), y + radius * math.sin(a * math.pi / 4)) for a in range(8)]
        levels = [self.ground_level(px, py) for px, py in ring + [(x, y)]]
        if max(levels) - min(levels) > STANDING_STEP_M:
            problems.append(f"{label} at ({x:g}, {y:g}) stands on an edge: the ground under it runs "
                            f"{min(levels):.2f}-{max(levels):.2f} m")
        return problems

    def patrol_leg_problems(self):
        """A patrol walks straight from stop to stop: each leg, swept by the NPC's footprint,
        stays out of buildings, fixtures, props, solids at street level and water."""
        room = self.standing_room()
        radius, height = room["bodies"]["npc"]
        problems = []
        for e in self.entities_in:
            patrol = e.get("props", {}).get("patrol")
            if not patrol:
                continue
            stops = [tuple(float(v) for v in stop.split(",")) for stop in patrol.split(";")]
            for i, a in enumerate(stops):
                b = stops[(i + 1) % len(stops)]
                sweep = LineString([a, b]).buffer(radius, quad_segs=8)
                hits = [name for name, fp in room["footprints"] if sweep.intersects(fp)]
                hits += [name for name, fp, z0, z1 in self.P.solids
                         if z1 > STANDING_STEP_M + PAVED_Z and z0 < height and sweep.intersects(fp)]
                if sweep.intersects(self.B):
                    hits.append("building")
                if sweep.intersects(room["water"]):
                    hits.append("water")
                if hits:
                    problems.append(f"{e['kind']}:{e['id']} patrol leg {i} ({a[0]:g}, {a[1]:g}) to ({b[0]:g}, {b[1]:g}) "
                                    f"runs through: {', '.join(sorted(set(hits)))}")
        return problems

    def check_standing_room(self):
        """Every person stands clear of the level (openspec/specs/level-geometry, "People stand
        clear of the level"). The body is the collider the game gives it, read from the scene
        (scene_collider(): npc.tscn for NPCs, player.tscn at spawn points), so the check and the
        game agree on how big a person is. At each standing spot the body must not overlap a
        registered detail box (a counter, a table, a trim) anywhere in its height, a registered
        solid (a stall's counter, a Skyway pillar), or the footprint of a fixture or prop;
        indoors it must stay inside the rooms' air; outdoors it must stay out of every building
        and all water (bridge decks aside), and stand on level ground. Each patrol leg must stay
        clear too. What the plan doesn't
        describe as a box or a footprint (lamps, railings, stairs) is the in-engine placement
        test's job (game/scenes/undercity/tests/placement_test.tscn), which uses the real colliders."""
        problems = [p for spot in self.standing_spots() for p in self.standing_problems(*spot)]
        problems += self.patrol_leg_problems()
        if problems:
            raise SystemExit(f"{self.m['id']}: {len(problems)} placements put a person inside the level:\n  "
                             + "\n  ".join(problems))

    # puddles (openspec/changes/street-puddles) --------------------------------------------
    def puddle_ground(self):
        """What a puddle is checked against, built once, after the rest of the level: the ground
        it may lie on by height (inset from its edges), the roofs, and what it keeps clear of. The
        roofs are Plan.shelters under the core's own headroom (wetness_data()), the same shapes
        and the same test as the core's Wetness.Sheltered, so a puddle and a character agree
        about where the rain falls."""
        if getattr(self, "_puddle_ground", None) is None:
            road = self.street.difference(self.rail_geom)
            ground = {STREET_Z: ("road", road), PLAZA_Z: ("square", self.plaza), PAVED_Z: ("sidewalk", self.paved)}
            room = self.standing_room()
            clear = [("building", self.B)] + list(room["footprints"])
            clear += [(name, fp) for name, fp, z0, z1 in self.P.solids if z0 < PUDDLE_LOW_M]
            clear += [(name or "detail", box(x0, y0, x1, y1)) for name, x0, y0, z0, x1, y1, z1 in room["details"]
                      if z0 < PUDDLE_LOW_M and z1 > STREET_Z]
            clear += [("stair", fp) for fp in self.flights]
            roofs = self.P.shelters
            self._puddle_ground = {
                # (name, the ground, what a puddle is clipped to, what the check holds it to: a
                # millimetre wider, so a clipped edge lying on the line isn't refused for rounding)
                "ground": {z: (name, g, g.buffer(-PUDDLE_KERB_OFF_M, join_style=2),
                               g.buffer(-PUDDLE_KERB_OFF_M + 1e-3, join_style=2)) for z, (name, g) in ground.items()},
                "not_on": [("bridge deck", self.bridge_u), ("rail tracks", self.rail_geom), ("Pit", self.PIT),
                           ("water", self.W)],
                "roofs": roofs, "roof_tree": shapely.STRtree([g for _, g, _ in roofs]),
                "headroom": wetness_data()["headroom_m"],
                "clear": clear, "clear_tree": shapely.STRtree([g for _, g in clear])}
        return self._puddle_ground

    def puddle_problems(self, label, g, z, others=()):
        """Why a puddle can't lie here, or [] when it can (openspec/changes/street-puddles, design
        section 3.5). g is its outline, z the height of the ground it lies on, others the puddles it
        must keep PUDDLE_GAP_M from. The placement and the check both ask this, so they can't
        disagree about the rule."""
        pg = self.puddle_ground()
        if z not in pg["ground"]:
            return [f"{label} lies at {z:g} m, where there is no open ground"]
        name, _, _, inset = pg["ground"][z]
        problems = []
        if not inset.contains(g):
            problems.append(f"{label} runs off its {name}: {g.difference(inset).area:.2f} m2 of it lies within "
                            f"{PUDDLE_KERB_OFF_M:g} m of a kerb or an edge, or past it")
        problems += [f"{label} lies on the {what}" for what, geom in pg["not_on"] if g.intersects(geom)]
        for i in pg["roof_tree"].query(g):
            rl, rg, under = pg["roofs"][i]
            if under - z >= pg["headroom"] and g.intersects(rg):
                problems.append(f"{label} lies under a roof, the {rl} ({g.intersection(rg).area:.2f} m2 of it)")
        for i in pg["clear_tree"].query(g, predicate="dwithin", distance=PUDDLE_CLEAR_M):
            what, geom = pg["clear"][i]
            problems.append(f"{label} is {g.distance(geom):.2f} m from a {what} (it keeps {PUDDLE_CLEAR_M:g} m clear)")
        problems += [f"{label} is {o['g'].distance(g):.2f} m from {o['id']} (puddles keep {PUDDLE_GAP_M:g} m apart)"
                     for o in others if o["g"].distance(g) < PUDDLE_GAP_M]
        return problems

    def kerbs(self):
        """The kerbs in the rain's path: the road's edges where it meets a sidewalk, as lines,
        each with a stable key (its start, rounded) for its puddles' seeded stream."""
        road = self.puddle_ground()["ground"][STREET_Z][1]
        edge = linemerge(road.boundary.intersection(self.paved.buffer(0.05)))
        lines = [ln for ln in getattr(edge, "geoms", [edge]) if ln.geom_type == "LineString" and ln.length >= 1.0]
        return sorted(((f"{ln.coords[0][0]:.1f},{ln.coords[0][1]:.1f}", ln) for ln in lines), key=lambda kl: kl[0])

    def kerb_frame(self, line, s):
        """The point s metres along a kerb, its unit tangent, and the unit normal into the road."""
        road = self.puddle_ground()["ground"][STREET_Z][1]
        p = line.interpolate(s)
        a, b = line.interpolate(max(s - 0.2, 0.0)), line.interpolate(min(s + 0.2, line.length))
        t = unit(b.x - a.x, b.y - a.y)
        n = (-t[1], t[0])
        if not road.contains(Point(p.x + n[0] * 0.3, p.y + n[1] * 0.3)):
            n = (-n[0], -n[1])
        return (p.x, p.y), t, n

    def drip_edges(self):
        """The edges rain drips from onto open ground: each awning's edges that face away from its
        building (not the edge on the wall, nor the sides running back to it), and every edge of
        the Skyway's deck. Each comes with a stable key for its puddles' seeded stream."""
        out = []
        for label, g, _ in self.P.shelters:
            if not any(k in label for k in DRIP_ROOFS):
                continue
            pg = oriented(g)
            c = pg.centroid
            for a, b in self.ring_edges(pg, pg.exterior.coords):
                if math.dist(a, b) < 1.0:
                    continue
                n = self.outward(pg, a, b)
                mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if "awning" in label and self.B.distance(Point(mid.x + n[0] * 0.5, mid.y + n[1] * 0.5)) \
                        < self.B.distance(mid) + 0.25:
                    continue
                out.append((f"{label}:{c.x:.1f},{c.y:.1f}:{a[0]:.1f},{a[1]:.1f}", a, b, n))
        return sorted(out, key=lambda e: e[0])

    def puddles(self):
        """Every puddle in the level, where rain water gathers (openspec/changes/street-puddles,
        design section 3.5): round a kerb gully every GULLY_EVERY_M of kerb, in the gutters between,
        and just outside the drip edges of the awnings and the Skyway's deck. A candidate that
        breaks a rule (puddle_problems) is dropped, never moved, so the rest stay where they are.
        Each kerb and each drip edge draws from its own seeded stream ("{seed}:puddles:..."), so
        placing puddles moves nothing else in the level, and the draws happen whether or not a
        candidate is kept. Returns (puddles, gullies)."""
        grounds = self.puddle_ground()["ground"]
        road_inset = grounds[STREET_Z][2]
        kept, gullies, cells, counts = [], [], {}, {}

        def near(g):
            x0, y0, x1, y1 = g.bounds
            seen = {}
            for i in range(int(x0 // 4) - 1, int(x1 // 4) + 2):
                for j in range(int(y0 // 4) - 1, int(y1 // 4) + 2):
                    for o in cells.get((i, j), ()):
                        seen[id(o)] = o
            return list(seen.values())

        def keep(kind, full, z, at):
            g = full.intersection(grounds[z][2]) if z in grounds else Polygon()
            g = max(polys(g), key=lambda q: q.area) if not g.is_empty else g
            if g.is_empty or g.area < PUDDLE_FIT * full.area:
                return None
            if self.puddle_problems(f"{kind} at ({at[0]:.1f}, {at[1]:.1f})", g, z, near(g)):
                return None
            counts[kind] = counts.get(kind, 0) + 1
            p = {"id": f"{kind}_{counts[kind]:03d}", "kind": kind, "at": (r4(at[0]), r4(at[1])), "ground_m": z, "g": g}
            kept.append(p)
            x0, y0, x1, y1 = g.bounds
            for i in range(int(x0 // 4), int(x1 // 4) + 1):
                for j in range(int(y0 // 4), int(y1 // 4) + 1):
                    cells.setdefault((i, j), []).append(p)
            return p

        kerbs = self.kerbs()
        for key, line in kerbs:                         # the gullies first: they are the fixed points
            rng = random.Random(f"{self.P.seed}:puddles:gully:{key}")
            for q in range(1, int(line.length // GULLY_EVERY_M) + 1):
                (px, py), t, n = self.kerb_frame(line, q * GULLY_EVERY_M - GULLY_EVERY_M / 2)
                off = PUDDLE_KERB_OFF_M + GULLY_GRATE_M[1] / 2
                cx, cy = px + n[0] * off, py + n[1] * off
                d = rng.uniform(*GULLY_ACROSS_M)
                if keep("gully", Point(cx, cy).buffer(d / 2, quad_segs=8), STREET_Z, (cx, cy)):
                    # heading into the road: the decal's -Z crosses the kerb, its X runs along it
                    gullies.append({"id": f"gully_{len(gullies) + 1:03d}", "at": (r4(cx), r4(cy)),
                                    "heading": r4(heading_of(*n))})
        for key, line in kerbs:
            rng = random.Random(f"{self.P.seed}:puddles:gutter:{key}")
            s = rng.uniform(1.0, GUTTER_GAP_M[1])
            while s < line.length - 1.0:
                length, wide = rng.uniform(*GUTTER_LEN_M), rng.uniform(*GUTTER_WIDE_M)
                (px, py), t, n = self.kerb_frame(line, min(s + length / 2, line.length))
                # an ellipse whose kerb side the kerb cuts off: wide / 0.7 across, its centre 0.4 of
                # its half-width in from the kerb's inset, so the water shows `wide` metres of road
                full_w = wide / 0.7
                off = PUDDLE_KERB_OFF_M + 0.4 * full_w / 2
                cx, cy = px + n[0] * off, py + n[1] * off
                keep("gutter", ellipse(cx, cy, length, full_w, math.atan2(t[1], t[0])), STREET_Z, (cx, cy))
                s += length + rng.uniform(*GUTTER_GAP_M)
        for key, a, b, n in self.drip_edges():
            rng = random.Random(f"{self.P.seed}:puddles:drip:{key}")
            edge = math.dist(a, b)
            t = unit(b[0] - a[0], b[1] - a[1])
            s = rng.uniform(0.0, DRIP_GAP_M[1])
            while s < edge - 0.5:
                length = min(rng.uniform(*DRIP_LEN_M), edge - s)
                wide, out = rng.uniform(*DRIP_WIDE_M), rng.uniform(*DRIP_OUT_M)
                m = s + length / 2
                cx, cy = a[0] + t[0] * m + n[0] * (out + wide / 2), a[1] + t[1] * m + n[1] * (out + wide / 2)
                z = self.ground_level(cx, cy)
                keep("drip", ellipse(cx, cy, length, wide, math.atan2(t[1], t[0])), z, (cx, cy))
                s += length + rng.uniform(*DRIP_GAP_M)
        return kept, gullies

    def place_puddles(self):
        """The level's puddles (City.puddles()) and a grate entity for each kerb gully, which the
        importer turns into the gully decal (openspec/changes/street-puddles, design section 3.2)."""
        self.puddle_list, self.gullies = self.puddles()
        for gl in self.gullies:
            self.P.entity("streets", f"ENT_{gl['id']}", gl["at"][0], gl["at"][1], STREET_Z, gl["heading"],
                          {"kind": "gully", "id": gl["id"]})

    def check_puddles(self, puddles=None):
        """Every puddle lies where rain water gathers and nowhere else (openspec/changes/street-puddles,
        "Puddles lie where water gathers"): on open ground in the rain, within its own ground and
        PUDDLE_KERB_OFF_M in from a kerb, off the bridges, the rails, the Pit and the water, clear
        of buildings, lots, fixtures, props, solids and stairs by PUDDLE_CLEAR_M, and apart from
        every other puddle. Refuses the plan, naming each puddle and what it breaks."""
        puddles = self.puddle_list if puddles is None else puddles
        tree = shapely.STRtree([p["g"] for p in puddles])
        problems = []
        for i, p in enumerate(puddles):
            others = [puddles[j] for j in tree.query(p["g"], predicate="dwithin", distance=PUDDLE_GAP_M) if j != i]
            problems += self.puddle_problems(p["id"], p["g"], p["ground_m"], others)
        if problems:
            raise SystemExit(f"{self.m['id']}: {len(problems)} puddle problems:\n  " + "\n  ".join(problems))

    def build(self):
        self.foundation()
        self.plan_lots()
        # walkways need their landing platforms before anything asks for their outline
        for wk in self.walkways:
            wk["_extra"] = []
        self.buildings_union()
        self.bridges()
        # the outfall's ledge and ladder need the quay railing left open
        self.outfall_zone = unary_union([RM.shape_geom(fx).buffer(2.5) for fx in self.m.get("props", [])
                                         if fx[-1] == "fix-dark" and RM.shape_geom(fx).intersects(self.W)])
        self.pit_stairs()
        self.ground()
        self.water()
        self.bridge_geometry()
        self.pit_railings()
        self.plan_ladders()
        self.quay_railings()
        self.named_buildings()
        self.lot_buildings()
        self.foundation_geometry()
        self.viaduct_geometry()
        self.walkway_geometry()
        self.mouse_stairs()
        self.props()
        self.street_lamps()
        self.wall_lamps()
        self.boundary()
        self.skyline_geometry()
        self.skyway_scenery()
        self.place_entities()
        self.check_skyline()
        self.check_zfighting()
        self.check_rooms_carved()
        self.check_doors()
        self.check_exits()
        self.check_standing_room()
        self.check_vehicles()
        self.place_puddles()
        self.check_puddles()
        return self.P

    def pit_railings(self):
        pg = oriented(self.PIT) if self.PIT.geom_type == "Polygon" else None
        if pg is None:
            return
        gaps = []
        for st in self.pit_stair_list:
            lat0, lat1 = st["lat"]
            gaps.append((st["ax"], lat0 - 0.2, lat1 + 0.2, st["c"]))
        for a, b in self.ring_edges(pg, pg.exterior.coords):
            n = self.outward(pg, a, b)
            L = math.dist(a, b)
            t = unit(b[0] - a[0], b[1] - a[1])
            # split the edge around stair openings
            cuts = [(0.0, L)]
            for ax, l0, l1, c in gaps:
                lat = 1 - ax
                for sgn in (1,):
                    ts = [(v - a[lat]) / (t[lat]) for v in (l0, l1)] if abs(t[lat]) > 0.2 else None
                    if ts is None:
                        continue
                    s0, s1 = sorted(ts)
                    mid = ((a[0] + t[0] * (s0 + s1) / 2), (a[1] + t[1] * (s0 + s1) / 2))
                    if math.dist(mid, c) > 3.0:
                        continue
                    nc = []
                    for u0, u1 in cuts:
                        if s1 <= u0 or s0 >= u1:
                            nc.append((u0, u1))
                        else:
                            if s0 > u0:
                                nc.append((u0, s0))
                            if s1 < u1:
                                nc.append((s1, u1))
                    cuts = nc
            for u0, u1 in cuts:
                if u1 - u0 < 0.5:
                    continue
                A = (a[0] + t[0] * u0, a[1] + t[1] * u0)
                Bq = (a[0] + t[0] * u1, a[1] + t[1] * u1)
                mx, my = (A[0] + Bq[0]) / 2 + n[0] * 0.3, (A[1] + Bq[1]) / 2 + n[1] * 0.3
                z = self.ground_level(mx, my)
                self.railing("streets", A, Bq, n, z, "gunmetal", inset=0.12)

    def quay_railings(self):
        """Railings along canal edges where a walk meets the water (not at bridges or the
        outfall), open RAIL_GAP_M wide at each ladder."""
        for w in self.waters:
            for pg in polys(w["g"]):
                pg = oriented(pg)
                for a, b in self.ring_edges(pg, pg.exterior.coords):
                    L = math.dist(a, b)
                    t = unit(b[0] - a[0], b[1] - a[1])
                    n = self.outward(pg, a, b)
                    k = max(1, int(math.ceil(L / 12.0)))
                    for q in range(k):
                        s0, s1 = L * q / k, L * (q + 1) / k
                        A = (a[0] + t[0] * s0, a[1] + t[1] * s0)
                        Bq = (a[0] + t[0] * s1, a[1] + t[1] * s1)
                        mx, my = (A[0] + Bq[0]) / 2 + n[0] * 0.4, (A[1] + Bq[1]) / 2 + n[1] * 0.4
                        if not (0.5 < mx < self.P.W - 0.5 and 0.5 < my < self.P.H - 0.5):
                            continue
                        pt = Point(mx, my)
                        if self.W_p.contains(pt) or self.B_p.contains(pt):
                            continue
                        piece = LineString([A, Bq])
                        if self.bridge_u.buffer(1.0).intersects(piece):
                            continue
                        if self.outfall_zone.intersects(piece):
                            continue
                        z = self.ground_level(mx, my)
                        # the pieces left either side of each ladder's opening
                        spans = [(0.0, s1 - s0)]
                        for ld in self.ladders:
                            if piece.distance(Point(ld["at"])) > 0.05:
                                continue
                            u = piece.project(Point(ld["at"]))
                            g0, g1 = u - RAIL_GAP_M / 2, u + RAIL_GAP_M / 2
                            spans = [part for u0, u1 in spans
                                     for part in ((u0, min(u1, g0)), (max(u0, g1), u1)) if part[1] - part[0] > 0.4]
                        for u0, u1 in spans:
                            self.railing("streets", (A[0] + t[0] * u0, A[1] + t[1] * u0),
                                         (A[0] + t[0] * u1, A[1] + t[1] * u1), n, z, "gunmetal", inset=0.12)

    # ways out of the water (openspec/changes/archive/2026-09-29-water-and-swimming, design section 4) ------------------
    def water_pillars(self):
        """The footprints of the Skyway pillars that stand in water."""
        if not self.viaduct:
            return []
        out = []
        for pl in RM.viaduct_pillars(self.viaduct):
            a = math.radians(pl["angle_deg"])
            fp = Polygon(obox_corners(pl["x"], pl["y"], math.cos(a), math.sin(a), PILLAR_BASE_HALF_M, PILLAR_BASE_HALF_M))
            if fp.intersects(self.W):
                out.append(fp)
        return out

    def ladder_landing(self, x, y, n):
        """Where a climber steps off a ladder at (x, y) on a quay edge whose land lies towards n:
        (step_in_m, top_m, floor_m), or None when there is nowhere. The landing is the first spot
        from data/water.json's ladder_top_step_m to LADDER_LAND_MAX_M in from the edge where a
        standing player (their collider, from player.tscn) is on level ground, with open paving
        (no water, building or pit) all the way, and no rise on the way more than a step above it.
        top_m is the highest ground crossed (a kerb along the quay), which the climb clears."""
        if getattr(self, "_player_r", None) is None:
            self._player_r, _ = scene_collider(PLAYER_SCENE)
            self._step_min = water_data()["ladder_top_step_m"]
            self._player_step = player_step_m()
            self._landings = {}
        key = (round(x, 3), round(y, 3), round(n[0], 4), round(n[1], 4))
        if key not in self._landings:
            self._landings[key] = self._find_landing(x, y, n)
        return self._landings[key]

    def _find_landing(self, x, y, n):
        r = self._player_r
        t = (-n[1], n[0])

        def ground(d, u=0.0):
            px, py = x + n[0] * d + t[0] * u, y + n[1] * d + t[1] * u
            if not (0.5 < px < self.P.W - 0.5 and 0.5 < py < self.P.H - 0.5):
                return None
            pt = Point(px, py)
            if self.W_p.contains(pt) or self.B_p.contains(pt) or self.PIT.contains(pt):
                return None
            return self.ground_level(px, py)
        top = -math.inf
        sampled = 0.0
        land = self._step_min
        while land <= LADDER_LAND_MAX_M + 1e-9:
            # the way in, every 0.2 m to the landing's far side, across the player's width
            while sampled + 0.2 <= land + r + 1e-9:
                sampled += 0.2
                zs = [ground(sampled, u) for u in (-r, 0.0, r)]
                if None in zs:
                    return None
                top = max(top, *zs)
            ring = [ground(land + r * math.cos(a * math.pi / 4), r * math.sin(a * math.pi / 4)) for a in range(8)]
            if None not in ring and max(ring) - min(ring) <= STANDING_STEP_M:
                top = max(top, *ring)
                return (round(land, 3), top, ring[0]) if top - ring[0] <= self._player_step else None
            land += 0.1
        return None

    def quay_open(self, x, y, n):
        """True when the quay at (x, y) on a water edge, whose land lies towards n, has somewhere
        for a climber to step off a ladder (ladder_landing())."""
        return self.ladder_landing(x, y, n) is not None

    def edge_runs(self, pg, open_at, inward=False):
        """The stretches of pg's rings where open_at(x, y, n) holds, sampled every 0.5 m: runs of
        {"at", "n", "d" (metres along the run), "ok" (a ladder may stand here)}. n points from
        the water to the climb-out side: out of pg (a quay), or into it with inward (a hull)."""
        runs = []
        pg = oriented(pg)
        for ring in [pg.exterior] + list(pg.interiors):
            run = []
            for a, b in self.ring_edges(pg, ring.coords):
                L = math.dist(a, b)
                t = unit(b[0] - a[0], b[1] - a[1])
                n = self.outward(pg, a, b)
                if inward:
                    n = (-n[0], -n[1])
                for q in range(int(L / 0.5) + 1):
                    sq = min(q * 0.5, L)
                    x, y = a[0] + t[0] * sq, a[1] + t[1] * sq
                    if not open_at(x, y, n):
                        if run:
                            runs.append(run)
                        run = []
                        continue
                    d = run[-1]["d"] + math.dist(run[-1]["at"], (x, y)) if run else 0.0
                    # a ladder needs its railing opening on one straight edge
                    ok = (RAIL_GAP_M / 2 + 0.3 <= sq <= L - RAIL_GAP_M / 2 - 0.3
                          and not self.ladder_keep_out.contains(Point(x, y)))
                    run.append({"at": (x, y), "n": n, "d": d, "ok": ok})
            if run:
                runs.append(run)
        return runs

    def spread_ladders(self, runs):
        """round(length / LADDER_EVERY_M) ladders per run (at least one), spread evenly, each moved
        to the nearest spot a ladder may stand that is LADDER_SPACING_M from every other ladder."""
        placed = []
        for run in runs:
            length = run[-1]["d"]
            count = max(1, int(round(length / LADDER_EVERY_M)))
            for k in range(count):
                target = length * (k + 0.5) / count
                spots = sorted((sp for sp in run if sp["ok"]
                                and all(math.dist(sp["at"], o) >= LADDER_SPACING_M
                                        for o in [p["at"] for p in placed] + [ld["at"] for ld in self.ladders])),
                               key=lambda sp: abs(sp["d"] - target))
                if spots:
                    placed.append(spots[0])
        return placed

    def plan_ladders(self):
        """Quay ladders: along each open stretch of quay (quay_open), spread by spread_ladders(),
        at least LADDER_CLEAR_M from a bridge deck, a moored boat and a pillar, and clear of the
        outfall (which has its own). A derelict ship hangs its own (ferry()). check_exits() then
        proves they are enough."""
        boats = [RM.shape_geom(fx) for fx in self.m.get("props", [])
                 if fx[0] == "poly" and fx[-1] == "fix" and RM.shape_geom(fx).intersects(self.W)]
        keep_out = unary_union([self.bridge_u, *boats, *self.water_pillars()]).buffer(LADDER_CLEAR_M)
        self.ladder_keep_out = prep(keep_out.union(self.outfall_zone))
        placed = []
        for pg in polys(self.W):
            placed += self.spread_ladders(self.edge_runs(pg, self.quay_open))
        # stable ids: per water body, north to south, then west to east
        by_water = {}
        for sp in placed:
            x, y = sp["at"]
            w = next(wb for wb in self.waters if wb["g"].buffer(0.05).contains(Point(x - sp["n"][0] * 0.3, y - sp["n"][1] * 0.3)))
            by_water.setdefault(w["id"], (w, []))[1].append(sp)
        for wid in sorted(by_water):
            w, sps = by_water[wid]
            for i, sp in enumerate(sorted(sps, key=lambda sp: (round(sp["at"][1], 2), round(sp["at"][0], 2))), 1):
                x, y = sp["at"]
                self.ladder(f"{wid}_{i}", w, x, y, sp["n"], *self.ladder_landing(x, y, sp["n"]))

    def ladder(self, lid, water, x, y, n, step_in, z_top, floor):
        """A ladder at (x, y) on a quay's edge, climbing towards n (the land): two stiles standing
        off the wall, from LADDER_UNDER_M under the water's surface, rungs every RUNG_EVERY_M up
        to the top z_top, and two grab hoops over the coping, painted so a swimmer can find them.
        The climb ends step_in metres in from the edge, on the floor at height floor
        (ladder_landing()). It is visual only, since rungs would snag a swimmer; the ENT_ladder
        entity (scenes/undercity/ladder.tscn, Ladder.cs) carries what the game climbs."""
        P = self.P
        t = (-n[1], n[0])
        z0 = water["surface"] - LADDER_UNDER_M
        hoop = z_top + LADDER_HOOP_M
        prims = P.obj("streets", "ladders", x, y)

        def at(u, v):
            return x + t[0] * u + n[0] * v, y + t[1] * u + n[1] * v
        for side in (-1, 1):
            u = side * LADDER_W_M / 2
            # the stile stands 0.09-0.15 m off the wall and runs up into the hoop
            prims.append(obox(*at(u, 0.03 - LADDER_STAND_OFF_M), t[0], t[1], 0.03, 0.03, z0, hoop - 0.03, "rust_metal"))
            # the hoop: over the coping, narrower than the stile and the post it joins
            reach = LADDER_HOOP_REACH_M
            prims.append(obox(*at(u, (reach + 0.02 - 0.14) / 2), n[0], n[1], (reach + 0.02 + 0.14) / 2, 0.025,
                              hoop - 0.06, hoop, "hazard_stripes"))
            prims.append(obox(*at(u, reach), t[0], t[1], 0.03, 0.03, z_top, hoop - 0.03, "hazard_stripes", skip=[0]))
        rz = z0 + 0.15
        while rz <= z_top - 0.1:
            # rungs end inside the stiles, 1 cm inside their faces
            prims.append(obox(*at(0, -0.12), t[0], t[1], LADDER_W_M / 2, 0.02, rz, rz + 0.04, "rust_metal"))
            rz += RUNG_EVERY_M
        facing = heading_of(n[0], n[1])
        P.entity(P.district_sector(x, y), f"ENT_ladder_{lid}", x, y, z_top, facing,
                 {"kind": "ladder", "id": lid, "water": water["id"], "top_m": r4(z_top), "bottom_m": r4(z0),
                  "width_m": LADDER_W_M, "stand_off_m": LADDER_STAND_OFF_M, "step_in_m": r4(step_in),
                  "floor_m": r4(floor), "facing_deg": r4(facing)})
        self.ladders.append({"id": lid, "water": water["id"], "at": (x, y), "n": n, "top": z_top, "bottom": z0,
                             "step_in": step_in, "floor": floor, "foot": (x - n[0] * 0.3, y - n[1] * 0.3)})

    def low_quays(self):
        """Quay points a swimmer climbs straight onto, without a ladder: open quay whose top is
        within data/water.json's mantle rise of the water's surface. The hub has none (its quays
        stand 2.2 m and more above the water), but a level with a low quay needs no ladder there."""
        lo, hi = mantle_rise()
        out = []
        for w in self.waters:
            for pg in polys(w["g"]):
                for run in self.edge_runs(pg, self.quay_open):
                    for sp in run:
                        x, y = sp["at"]
                        rise = self.ground_level(x + sp["n"][0] * 0.4, y + sp["n"][1] * 0.4) - w["surface"]
                        if lo <= rise <= hi:
                            out.append((x - sp["n"][0] * 0.3, y - sp["n"][1] * 0.3))
        return out

    def exit_problems(self, ladders=None):
        """How far a swimmer is from a way out, from every point of every water surface on an
        EXIT_GRID_M grid: the length of the shortest swim through the water, around hulls,
        buildings and pillars, to a ladder's foot or a low quay (low_quays()). Returns one message
        per water body with points farther than EXIT_REACH_M, naming its farthest point."""
        ladders = self.ladders if ladders is None else ladders
        blocked = unary_union([self.B, *self.water_pillars()])
        swim = self.W.difference(blocked)
        swim_p = prep(swim)
        g = EXIT_GRID_M
        x0, y0, x1, y1 = swim.bounds
        cells = {}
        for i in range(int(math.floor(x0 / g)), int(math.ceil(x1 / g)) + 1):
            for j in range(int(math.floor(y0 / g)), int(math.ceil(y1 / g)) + 1):
                if swim_p.contains(Point((i + 0.5) * g, (j + 0.5) * g)):
                    cells[(i, j)] = math.inf
        # each way out seeds the cells a short straight swim away
        heap = []
        for ex, ey in [ld["foot"] for ld in ladders] + self.low_quays():
            ci, cj = int(math.floor(ex / g)), int(math.floor(ey / g))
            for di in range(-2, 3):
                for dj in range(-2, 3):
                    key = (ci + di, cj + dj)
                    if key not in cells:
                        continue
                    cx, cy = (key[0] + 0.5) * g, (key[1] + 0.5) * g
                    d = math.dist((cx, cy), (ex, ey))
                    if d < cells[key] and swim_p.contains(LineString([(cx, cy), (ex, ey)])):
                        cells[key] = d
                        heapq.heappush(heap, (d, key))
        steps = [(di, dj, math.hypot(di, dj) * g) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]
        while heap:
            d, (i, j) = heapq.heappop(heap)
            if d > cells[(i, j)]:
                continue
            for di, dj, step in steps:
                key = (i + di, j + dj)
                if key not in cells or d + step >= cells[key]:
                    continue
                if di and dj and ((i + di, j) not in cells or (i, j + dj) not in cells):
                    continue    # no cutting a corner of a pillar or a hull
                cells[key] = d + step
                heapq.heappush(heap, (d + step, key))
        problems = []
        for w in self.waters:
            gp = prep(w["g"])
            far = sorted(((d, (i + 0.5) * g, (j + 0.5) * g) for (i, j), d in cells.items()
                          if d > EXIT_REACH_M and gp.contains(Point((i + 0.5) * g, (j + 0.5) * g))), reverse=True)
            if far:
                d, fx, fy = far[0]
                how = "with no way out at all" if math.isinf(d) else f"{d:.1f} m from the nearest"
                problems.append(f"{w['id']}: {len(far)} points of water are more than {EXIT_REACH_M:g} m of swimming "
                                f"from a way out; the farthest is ({fx:g}, {fy:g}), {how}")
        return problems

    # ------------------------------------------------------------------ the skyline

    def skyline_geometry(self):
        """Meridian's towers beyond the hub's edges (openspec/changes/archive/2026-09-29-hub-skyline): each tower's
        massing and crown (skyline.py), merged into one object per ring in the skyline sector,
        with no collision. Every box is registered with the z-fighting check."""
        towers = self.m.get("skyline", [])
        centre = (self.P.W / 2, self.P.H / 2)
        for t in towers:
            ring = t.get("ring", "near")
            prims = self.P.obj("skyline", "sky", name=f"skyline_{ring}", extras=SKYLINE_EXTRAS)
            # what each box is rides in its colour, for the one skyline shader (skyline.vertex_color)
            for k, (lo, hi, part) in enumerate(skyline.massing(t, centre)):
                prims.append({**box_prim(lo, hi, skyline.MATERIAL), "color": skyline.vertex_color(t, part)})
                self.P.zdetail("skyline", lo, hi, f"{t['id']}#{k}")

    def skyway_scenery(self):
        """The Skyway runs on past each edge as scenery, 200 m of deck, parapets, girders, pier
        caps and piers in the skyline sector, with no collision: the viaduct's own span."""
        if not self.viaduct:
            return
        e = self.viaduct
        (ax, ay), (bx, by) = e["pts"][0], e["pts"][-1]
        L = math.dist((ax, ay), (bx, by))
        ux, uy = unit(bx - ax, by - ay)
        vx, vy = -uy, ux
        half = e["w"] / 2
        d0, d1 = self.deck_top - 1.0, self.deck_top
        g0 = d0 - 1.2
        c0 = g0 - 1.0

        def Q(s, v):
            return (ax + ux * s + vx * v, ay + uy * s + vy * v)
        prims = self.P.obj("skyline", "sky", name="skyline_skyway", extras=SKYLINE_EXTRAS)
        for s_from, s_to in ((-SKYWAY_SCENERY_M, 0.0), (L, L + SKYWAY_SCENERY_M)):
            n = max(1, round((s_to - s_from) / SKYWAY_SCENERY_SPAN_M))
            cuts = [s_from + (s_to - s_from) * i / n for i in range(n + 1)]
            for k in range(n):
                prims += viaduct_span(Q, cuts[k], cuts[k + 1], half, d0, d1, g0)
            for s in cuts[1:-1]:
                x, y = Q(s, 0)
                for va, vb in ((-half, -1.9), (1.9, half)):
                    prims.append(hexa([Q(s - 1.0, va), Q(s + 1.0, va), Q(s + 1.0, vb), Q(s - 1.0, vb)], c0, g0, "concrete"))
                prims.append(obox(x, y, ux, uy, PILLAR_BASE_HALF_M - 0.3, PILLAR_BASE_HALF_M - 0.3,
                                  -SKYWAY_PIER_DEPTH_M, c0, "concrete"))

    def check_skyline(self):
        """The skyline's four rules (skyline.py): bounds, the horizon's coverage, no overlaps and
        the triangle budget."""
        found = skyline.problems(self.m.get("skyline", []), self.P.W, self.P.H)
        if found:
            raise SystemExit(f"{self.m['id']}: the skyline breaks its rules:\n  " + "\n  ".join(found))

    def check_exits(self):
        """Falling in is never a soft lock (openspec/changes/archive/2026-09-29-water-and-swimming, "Every water body
        has a way out"): exit_problems() finds nothing."""
        problems = self.exit_problems()
        if problems:
            raise SystemExit(f"{self.m['id']}: water with no way out:\n  " + "\n  ".join(problems))


def load(level_id):
    mod = importlib.import_module(f"layouts.{level_id}")
    try:
        ents = importlib.import_module(f"layouts.{level_id}_entities").ENTITIES
    except ModuleNotFoundError:
        ents = []
    return mod.MAP, ents


def build(level_id):
    m, ents = load(level_id)
    if m.get("base", "city") != "city":
        raise SystemExit(f"{level_id}: only city layouts are planned so far")
    return City(m, ents).build()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("level")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    with contextlib.redirect_stdout(sys.stderr):   # the checks report on stderr; stdout is the plan
        plan = build(a.level)
    data = plan.to_json()
    if a.stats:
        print(json.dumps(data["stats"], indent=1))
        return
    text_ = json.dumps(data, separators=(",", ":"))
    if a.out:
        with open(a.out, "w") as f:
            f.write(text_)
    else:
        sys.stdout.write(text_)


if __name__ == "__main__":
    main()

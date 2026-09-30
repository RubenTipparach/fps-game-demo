"""The parked vehicles' table (tools/blender/vehicles.json): its schema and loader.

It owns what a vehicle table may say (openspec/changes/street-vehicles, design section 3.3):
body types with their measurements and side profiles, the paints, the variants the hub places,
and the triangle budgets. It lives in tools/blender as plain Python with no bpy, on tablekit.py,
the one validator the Blender tables share, so the level plan (tools/levels/city_plan.py) and the
prop kit (build_undercity_props.py) read the same checked table, and a misspelt key stops both
(CLAUDE.md 5.6).

    python3 tools/blender/vehicle_data.py            # validates the committed table

Axes are the prop kit's: metres, x right, y front, z up; a model's origin is the floor centre of
its footprint, and its front faces +y.
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "..", "game", "models", "undercity", "props")   # vehicle_<id>.glb
sys.path.insert(0, HERE)
from tablekit import Bool, DataError, Int, List, Map, Num, Obj, Str, Vec, parse_hex  # noqa: E402

TABLE = os.path.join(HERE, "vehicles.json")
SPOTS = ("car", "truck")        # the layout's two sizes of parking spot (city_plan.py, a "car" fixture)

POINT = Vec(2)                  # [y, z], metres

TYPE = Obj({
    "spot": Str(choices=SPOTS),
    "length_m": Num(lo=1.0, hi=12.0),
    "width_m": Num(lo=1.0, hi=3.0),
    "wheel_r_m": Num(lo=0.15, hi=0.7),
    "tyre_w_m": Num(lo=0.1, hi=0.5),
    "track_m": Num(lo=0.8, hi=2.6),
    "axles_m": List(Num(), min_len=2),                 # each axle's y
    "clearance_m": Num(lo=0.05, hi=1.0),                # the lower body's underside
    "arch_gap_m": Num(0.06, lo=0.0, hi=0.3),            # a wheel arch's clearance round the tyre
    "body_top_m": List(POINT, min_len=2),               # the lower body's top line, rear to front
    "cabin_m": List(POINT, min_len=4),                  # rear-bottom, rear-top, front-top, front-bottom
    "taper": Num(1.0, lo=0.5, hi=1.0),                  # the cabin's width at its top over at its belt
    "windows_y_m": List(Vec(2), min_len=1),             # each side window's [y0, y1]
    "glass_margin_m": Num(0.07, lo=0.02, hi=0.3),       # a pane's inset from the cabin's edges (the pillars)
    "bumper_z_m": Vec(2),
    "head_z_m": Vec(2),
    "tail_z_m": Vec(2),
    "lamp_w_m": Num(0.3, lo=0.1, hi=0.8),
    "seams_y_m": List(Num(), default=[]),               # dark door seams down the lower body's sides
    "band_z_m": Vec(2, default=None),                   # where a taxi's chequer band runs, or null
    "cargo": Obj({                                      # a box truck's body, or null
        "y_m": Vec(2), "z_m": Vec(2), "width_m": Num(lo=1.0, hi=3.0),
    }, default=None),
})

VARIANT = Obj({
    "id": Str(),
    "type": Str(),
    "paint": Str(),
    "plate": Str(),                                     # an invented plate code
    "roof_sign": Str(None, nullable=True),              # the taxi's lit roof sign
    "chequer": Bool(False),                             # the taxi's band
    "livery": Obj({"text": Str(), "ground": Str(), "ink": Str()}, default=None),   # a truck's cargo sides
})

SCHEMA = Obj({
    "budget": Obj({"car_tris": Int(lo=100), "truck_tris": Int(lo=100)}),
    "paints": Map(Str()),
    "types": Map(TYPE),
    "variants": List(VARIANT, min_len=1),
})


def validate(raw, path="vehicles.json"):
    """The table with defaults filled in, or DataError naming the first bad field."""
    t = SCHEMA.check(raw, path, {})
    for name, hexcode in t["paints"].items():
        parse_hex(hexcode, f"{path}.paints.{name}")
    for name, ty in t["types"].items():
        p = f"{path}.types.{name}"
        half = ty["length_m"] / 2
        ys = [pt[0] for pt in ty["body_top_m"]]
        starts_at_rear = abs(ys[0] + half) < 1e-6 or ty["cargo"] is not None   # a truck's cab starts at its cargo
        if ys != sorted(ys) or not starts_at_rear or abs(ys[-1] - half) > 1e-6:
            raise DataError(f"{p}.body_top_m: runs rear to front, from y {-half:g} (or a cargo box) to the front, y {half:g}")
        if len(ty["cabin_m"]) != 4:
            raise DataError(f"{p}.cabin_m: four points, rear-bottom, rear-top, front-top, front-bottom")
        for axle in ty["axles_m"]:
            if abs(axle) + ty["wheel_r_m"] > half:
                raise DataError(f"{p}.axles_m: the wheel at y {axle:g} sticks out past the body")
        if ty["track_m"] / 2 + ty["tyre_w_m"] / 2 > ty["width_m"] / 2:
            raise DataError(f"{p}.track_m: the tyres stick out past the body's sides")
        for key in ("bumper_z_m", "head_z_m", "tail_z_m"):
            lo, hi = ty[key]
            if not ty["clearance_m"] <= lo < hi:
                raise DataError(f"{p}.{key}: needs clearance <= low < high")
        if ty["cargo"] is not None:
            y0, y1 = ty["cargo"]["y_m"]
            if not -half - 1e-6 <= y0 < y1 < half:
                raise DataError(f"{p}.cargo.y_m: inside the vehicle, rear to front")
        gap = ty["wheel_r_m"] + ty["arch_gap_m"]
        for i, y in enumerate(ty["seams_y_m"]):
            if not ys[0] < y < ys[-1] or any(abs(y - a) <= gap for a in ty["axles_m"]):
                raise DataError(f"{p}.seams_y_m[{i}]: {y:g} is off the doors, over a wheel arch or past the body")
        if ty["band_z_m"] is not None:                  # the band runs between the first and last arch
            lo, hi = ty["band_z_m"]
            y0, y1 = min(ty["axles_m"]) + gap, max(ty["axles_m"]) - gap
            top = min([top_z(ty["body_top_m"], y) for y in (y0, y1)]
                      + [z for y, z in ty["body_top_m"] if y0 < y < y1])
            if not ty["clearance_m"] < lo < hi < top:
                raise DataError(f"{p}.band_z_m: on the lower body's sides between the arches, low < high")
    seen = set()
    for i, v in enumerate(t["variants"]):
        p = f"{path}.variants[{i}]"
        if v["id"] in seen:
            raise DataError(f"{p}.id: '{v['id']}' is used twice")
        seen.add(v["id"])
        if v["type"] not in t["types"]:
            raise DataError(f"{p}.type: no type '{v['type']}'")
        if v["paint"] not in t["paints"]:
            raise DataError(f"{p}.paint: no paint '{v['paint']}'")
        if v["chequer"] and t["types"][v["type"]]["band_z_m"] is None:
            raise DataError(f"{p}.chequer: its type '{v['type']}' has no band_z_m to run a band along")
        if v["livery"] is not None:
            for key in ("ground", "ink"):
                parse_hex(v["livery"][key], f"{p}.livery.{key}")
    return t


def top_z(chain, y):
    """The height of a top line ([y, z] points, rear to front) at y."""
    for (y0, z0), (y1, z1) in zip(chain, chain[1:]):
        if y0 - 1e-9 <= y <= y1 + 1e-9:
            return z0 + (z1 - z0) * ((y - y0) / (y1 - y0) if y1 > y0 else 0.0)
    raise DataError(f"y {y:g} is off the body's top line")


def load(path=TABLE):
    with open(path) as f:
        return validate(json.load(f), os.path.basename(path))


def model_bounds(variant_id, models=MODELS):
    """The committed model's box as (lo, hi) in the kit's axes (x right, y front, z up), from its
    glb's POSITION bounds, which glTF requires, so a check reads what the game loads rather than
    what the table meant (CLAUDE.md 5.6). The glb is y up with its front toward -z."""
    path = os.path.join(models, f"vehicle_{variant_id}.glb")
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        raise DataError(f"{path}: not a glb")
    j = json.loads(data[20:20 + struct.unpack("<I", data[12:16])[0]])
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for node in j["nodes"]:
        if "mesh" not in node:
            continue
        if node.get("rotation", [0, 0, 0, 1]) != [0, 0, 0, 1] or node.get("scale", [1, 1, 1]) != [1, 1, 1]:
            raise DataError(f"{path}: node {node.get('name')} is turned or scaled; a vehicle's parts sit at its origin")
        t = node.get("translation", [0.0, 0.0, 0.0])
        for prim in j["meshes"][node["mesh"]]["primitives"]:
            acc = j["accessors"][prim["attributes"]["POSITION"]]
            lo = [min(a, m + d) for a, m, d in zip(lo, acc["min"], t)]
            hi = [max(a, m + d) for a, m, d in zip(hi, acc["max"], t)]
    return (lo[0], -hi[2], lo[1]), (hi[0], -lo[2], hi[1])


def budget(table, type_name):
    """The triangle budget of a type's models: a truck's, or a car's (cars and vans)."""
    spot = table["types"][type_name]["spot"]
    return table["budget"]["truck_tris" if spot == "truck" else "car_tris"]


if __name__ == "__main__":
    t = load()
    print(f"vehicles.json OK: {len(t['types'])} types, {len(t['variants'])} variants")

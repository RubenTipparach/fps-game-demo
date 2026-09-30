"""The parked vehicles' table (tools/blender/vehicles.json): its schema, loader and checks.

It owns what the vehicle table may say (openspec/changes/cc0-vehicles, design section 4): the pinned
pack every vehicle is converted from, the pack's scale, each body's file and real length, the
variants the hub places (a body in one of its own colour textures), the triangle budget, and the
range a vehicle's albedo must fall in (openspec/changes/vehicle-fixes, design section 3.2). It
lives in tools/blender as plain Python with no bpy, on tablekit.py, the one validator the Blender
tables share, so the level plan (tools/levels/city_plan.py) and the converter
(build_vehicles_cc0.py) read the same checked table, and a misspelt key stops both (CLAUDE.md 5.6).

    python3 tools/blender/vehicle_data.py            # validates the table and the committed files

Axes are the prop kit's: metres, x right, y front, z up; a model's origin is the floor centre of
its footprint, and its front faces +y.
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, "..", "..", "game")
MODELS = os.path.join(GAME, "models", "undercity", "props")          # vehicle_<id>.glb
TEXTURES = os.path.join(GAME, "textures", "vehicles", "psx")         # <id>.png, the variant's own texture
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "deps"))
from tablekit import DataError, Int, List, Map, Num, Obj, Str  # noqa: E402
import fetch_character_tools as deps  # noqa: E402  (the pinned packs: tools/deps/*_packs.json)

TABLE = os.path.join(HERE, "vehicles.json")

# A vehicle's mean albedo, linear: from a very dark paint to a very light one. The texture a car
# wears is its colour, so a texture outside this range is a car that reads black or glows in the
# baked light (openspec/changes/vehicle-fixes, design section 3.2).
ALBEDO_RANGE = (0.03, 0.8)

BODY = Obj({
    "is": Str(),                                        # what the body is, for the table's reader
    "blend": Str(),                                     # the pack's .blend, relative to the pack's root
    "length_m": Num(lo=2.0, hi=12.0),                   # its real length at the pack's scale, checked by the converter
})

VARIANT = Obj({
    "id": Str(),
    "body": Str(),
    "texture": Str(),                                   # one of the body's own colour textures, relative to the pack's root
})

LOOK = Obj({                                            # the material over the pack's texture
    "roughness": Num(0.6, lo=0.0, hi=1.0),
    "clearcoat": Num(1.0, lo=0.0, hi=1.0),              # the rain's gloss over the paint (vehicle-fixes, 3.2)
    "clearcoat_roughness": Num(0.1, lo=0.0, hi=1.0),
})

SCHEMA = Obj({
    "pack": Str(),                                      # a pack id pinned in tools/deps/*_packs.json
    "wheel_blend": Str(),                               # the pack's one wheel, which sets its scale
    "wheel_d_m": Num(lo=0.3, hi=1.5),                   # that wheel's real diameter
    "budget_tris": Int(lo=100),                         # a vehicle's drawn triangles
    "material": LOOK,
    "bodies": Map(BODY),
    "variants": List(VARIANT, min_len=1),
})


def validate(raw, path="vehicles.json", packs=None):
    """The table with defaults filled in, or DataError naming the first bad field."""
    t = SCHEMA.check(raw, path, {})
    try:
        deps.pack_by_id(t["pack"], packs)
    except deps.PackError as e:
        raise DataError(f"{path}.pack: {e}") from None
    seen = set()
    for i, v in enumerate(t["variants"]):
        p = f"{path}.variants[{i}]"
        if v["id"] in seen:
            raise DataError(f"{p}.id: '{v['id']}' is used twice")
        if not v["id"].replace("_", "").isalnum() or v["id"] != v["id"].lower():
            raise DataError(f"{p}.id: '{v['id']}' names files; lower case, digits and underscores")
        seen.add(v["id"])
        if v["body"] not in t["bodies"]:
            raise DataError(f"{p}.body: no body '{v['body']}'")
        folder = os.path.dirname(t["bodies"][v["body"]]["blend"])
        if os.path.dirname(v["texture"]) != folder or not v["texture"].lower().endswith(".png"):
            raise DataError(f"{p}.texture: '{v['texture']}' is not a .png beside its body's blend in '{folder}'")
    return t


def load(path=TABLE):
    with open(path) as f:
        return validate(json.load(f), os.path.basename(path))


def model_path(variant_id, models=MODELS):
    return os.path.join(models, f"vehicle_{variant_id}.glb")


def texture_path(variant_id, textures=TEXTURES):
    return os.path.join(textures, f"{variant_id}.png")


def model_bounds(variant_id, models=MODELS):
    """The committed model's box as (lo, hi) in the kit's axes (x right, y front, z up), from its
    glb's POSITION bounds, which glTF requires, so a check reads what the game loads rather than
    what the table meant (CLAUDE.md 5.6). The glb is y up with its front toward -z."""
    path = model_path(variant_id, models)
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


def png_rgb(path):
    """An 8-bit, non-interlaced RGB or RGBA PNG's pixels as rows of (r, g, b) bytes. The standard
    library's own reader, because the check runs inside Blender too, whose Python has no imaging
    library; any other PNG is refused by name."""
    import zlib
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise DataError(f"{path}: not a PNG")
    pos, idat, head = 8, [], None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        pos += 12 + n
    w, h, depth, colour, _, _, interlace = head
    if depth != 8 or colour not in (2, 6) or interlace:
        raise DataError(f"{path}: an 8-bit RGB or RGBA PNG without interlacing, please (depth {depth}, colour type {colour})")
    bpp = 3 if colour == 2 else 4
    raw, stride, prev, rows = zlib.decompress(b"".join(idat)), w * bpp, bytearray(w * bpp), []
    for y in range(h):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):                             # undo the row's filter (PNG spec, section 9)
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], prev[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x * bpp:x * bpp + 3]) for x in range(w)])
        prev = line
    return rows


def mean_albedo(path):
    """A texture's mean linear albedo: its pixels' sRGB values decoded and averaged over the
    image and its three channels."""
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in (i / 255.0 for i in range(256))]
    rows = png_rgb(path)
    return sum(linear[c] for row in rows for px in row for c in px) / (3 * len(rows) * len(rows[0]))


def committed_problems(table, models=MODELS, textures=TEXTURES):
    """What's wrong with the committed files a table names: each variant's glb and texture must
    exist, and the texture's albedo must lie in ALBEDO_RANGE (openspec/changes/cc0-vehicles, design
    section 6). An empty list when they're all there and in range."""
    lo, hi = ALBEDO_RANGE
    problems = []
    for v in table["variants"]:
        for what, path in (("model", model_path(v["id"], models)), ("texture", texture_path(v["id"], textures))):
            if not os.path.isfile(path):
                problems.append(f"{v['id']}: its {what} {os.path.relpath(path)} is missing")
        tex = texture_path(v["id"], textures)
        if os.path.isfile(tex):
            albedo = mean_albedo(tex)
            if not lo <= albedo <= hi:
                problems.append(f"{v['id']}: its texture's mean albedo {albedo:.3f} is outside {lo:g}-{hi:g}")
    return problems


if __name__ == "__main__":
    t = load()
    bad = committed_problems(t)
    if bad:
        raise SystemExit("vehicles.json: " + "; ".join(bad))
    print(f"vehicles.json OK: {len(t['bodies'])} bodies, {len(t['variants'])} variants, every model and texture committed")

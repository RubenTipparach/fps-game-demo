"""Loads and validates tools/blender/npcs.json, the table the NPC body build reads.

It owns the schema of that table: which keys each block and row may carry, the code default of
every optional field, and the cross-checks (palette colours, gear pieces and sets, the budget)
that stop the build with the file, the path and the field when the table is wrong. Authored data
fails loudly (CLAUDE.md 5.6): an unknown key is an error, a missing optional field inherits its
code default, a present zero is zero, and a number must be finite. The generic field types come
from tablekit.py, the one validator the Blender tables share. It is plain Python with
no Blender import, so the table can be checked anywhere:

    python3 tools/blender/npc_data.py
"""
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tablekit import DataError, Field, Int, List, Map, Num, Obj, Str, Vec, parse_hex  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "npcs.json")

SEXES = ("male", "female")
RACES = ("african", "asian", "caucasian")
ASSET_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
POSE_AXES = ("X", "Y", "Z")
ORIGINS = ("bone_head", "bone_tail", "centroid", "eyes", "eye_l", "eye_r")


class Asset(Str):
    """An MPFB asset name (a folder name in a pack, such as male_worksuit01), never a path."""

    def check(self, value, path, ctx):
        value = super().check(value, path, ctx)
        if value is not None and not ASSET_NAME.match(value):
            raise DataError(f"{path}: {value!r} is not an asset name (lower case, no slashes)")
        return value


class Colour(Str):
    """A colour name from the palette block."""

    def check(self, value, path, ctx):
        value = super().check(value, path, ctx)
        if value is not None:
            ctx.setdefault("colour_refs", []).append((path, value))
        return value


class Raw(Field):
    """A value checked later by its own schema (a field whose type depends on another field)."""

    def check(self, value, path, ctx):
        return value


class Hex(Field):
    """A "#rrggbb" sRGB colour, returned as (r, g, b) in 0..1."""

    def check(self, value, path, ctx):
        return parse_hex(value, path)


BUDGET = Obj({
    "triangles": Int(lo=1), "materials": Int(lo=1), "texture_px": Int(lo=1), "textures": Int(lo=1),
    "bones": Int(lo=1),
})

CLOTH = Obj({
    "asset": Asset(),
    "tint": Colour(None, nullable=True),
    "top": Colour(None, nullable=True),
    "bottom": Colour(None, nullable=True),
})

NAMED = Obj({
    "id": Str(),
    "role": Str(""),
    "sex": Str(choices=SEXES),
    "age_years": Num(lo=12.0, hi=90.0),
    "height_m": Num(lo=1.2, hi=2.3),
    "muscle": Num(0.5, 0.0, 1.0),
    "weight": Num(0.5, 0.0, 1.0),
    "proportions": Num(0.5, 0.0, 1.0),
    "cupsize": Num(0.5, 0.0, 1.0),
    "firmness": Num(0.5, 0.0, 1.0),
    "race": Obj({r: Num(lo=0.0, hi=1.0) for r in RACES}),
    "skin": Asset(),
    "skin_tone": Colour(None, nullable=True),
    "eyes": Asset(),
    "eyebrows": Asset(),
    "eyelashes": Asset("eyelashes01"),
    "hair": Asset(None, nullable=True),
    "hair_tint": Colour(None, nullable=True),
    "brow_tint": Colour(None, nullable=True),
    "clothes": List(CLOTH, min_len=1),
    "gear": List(Str(), []),
})

AGE_BANDS = ("young", "middleage", "old")

CIVILIAN = Obj({
    "id": Str(),
    "role": Str(""),
    "seed": Int(lo=0, hi=(1 << 31) - 1),
    "sex": Str(choices=SEXES),
    "race": Str(choices=RACES),
    # openspec/changes/crowd-variety: draw the age inside one of MPFB's skin bands (the table's
    # civilian_range.age_bands_years), so the rows can cover the CC0 skin grid; unset, the age is
    # drawn over the whole civilian range as before.
    "age_band": Str(None, choices=AGE_BANDS, nullable=True),
    "skin_tone": Colour(None, nullable=True),
    "eyelashes": Asset("eyelashes01"),
    "hair": Asset(None, nullable=True),
    "hair_tint": Colour(None, nullable=True),
    "brow_tint": Colour(None, nullable=True),
    "clothes": List(CLOTH, min_len=1),
    "gear": List(Str(), []),
})


class Body(Field):
    """A body row: a civilian when it carries a "seed", a named NPC otherwise."""

    def check(self, value, path, ctx):
        if not isinstance(value, dict):
            raise DataError(f"{path}: expected an object")
        if "seed" in value:
            out = CIVILIAN.check(value, path, ctx)
            out["kind"] = "civilian"
        else:
            out = NAMED.check(value, path, ctx)
            out["kind"] = "named"
        return out


PIECE = Obj({
    "bone": Str(),
    "shape": Str(choices=("cylinder", "sphere")),
    "frame": Str("world", choices=("world", "bone")),
    "origin": Str("bone_head", choices=ORIGINS),
    "offset_m": Vec(3, [0.0, 0.0, 0.0], lo=-1.0, hi=1.0),
    "angle_deg": Vec(2, lo=-360.0, hi=360.0),
    "along_m": Raw(None),
    "elevation_deg": Raw(None),
    "segments": Vec(2, lo=1, hi=64),
    "clearance_m": Num(lo=0.001, hi=0.3),
    "thickness_m": Num(lo=0.001, hi=0.3),
    "reach_m": Num(lo=0.01, hi=1.0),
    "fit_bones": Raw(None),
    "over": List(Str(), []),
    "colour": Colour(),
    "colour2": Colour(None, nullable=True),
    "mix": Num(0.0, 0.0, 1.0),
    "stripe": Raw(None),
})
SPAN = Vec(2, lo=-1.0, hi=1.0)
ELEVATION = Vec(2, lo=-90.0, hi=90.0)
STRIPE = Obj({"colour": Colour(), "v": Vec(2, lo=0.0, hi=1.0)})
FIT_BONES = List(Str(), min_len=1)

TABLE_SCHEMA = Obj({
    "out_dir": Str(),
    "rig": Str("game_engine", choices=("game_engine",)),
    "seed": Int(lo=0, hi=(1 << 31) - 1),
    "atlas_px": Int(lo=64, hi=4096),
    "texture_format": Str("png", choices=("png", "webp")),
    "webp_quality": Int(85, 1, 100),
    "budget": BUDGET,
    "height_fit": Obj({"tolerance_m": Num(0.001, 0.0001, 0.05), "max_iterations": Int(30, 1, 80)}),
    "civilian_range": Obj({
        "height_m": Vec(2, lo=1.0, hi=2.3),
        "height_mean_m": Obj({"male": Num(lo=1.0, hi=2.3), "female": Num(lo=1.0, hi=2.3)}),
        "height_sd_m": Num(lo=0.0, hi=0.5),
        "age_years": Vec(2, lo=18.0, hi=90.0),
        "age_bands_years": Obj({b: Vec(2, lo=18.0, hi=90.0) for b in AGE_BANDS}),
        "race_pin_weight": Num(lo=0.0, hi=1.0),
        "eyebrows": List(Asset(), min_len=1),
        "eyes": List(Asset(), min_len=1),
    }),
    "proxies": Obj({"male": Asset(), "female": Asset()}),
    "eyes_model": Asset("low-poly"),
    "decimate": Map(Num(lo=0.05, hi=1.0)),
    "tint": Obj({"contrast": Num(0.85, 0.0, 2.0), "split_height_frac": Num(0.5, 0.2, 0.8),
                 "legwear_below_frac": Num(0.3, 0.0, 0.6), "max_ratio": Num(2.0, 1.0, 20.0),
                 "mask_dilate_px": Int(3, 0, 32)}),
    "skin_tone_strength": Num(1.0, 0.0, 1.0),
    # openspec/changes/character-lighting, design section 1 (and its found-in-building notes)
    "skin_normal": Obj({"blur_px": Num(6.0, 0.5, 64.0), "strength": Num(16.0, 0.0, 200.0)}),
    "skin_roughness": Obj({"t_zone": Num(0.42, 0.0, 1.0), "cheeks": Num(0.55, 0.0, 1.0), "body": Num(0.62, 0.0, 1.0),
                           "blur_px": Num(6.0, 0.0, 64.0)}),
    "outfit_roughness": Obj({"cloth": Num(0.7, 0.0, 1.0), "eyes": Num(0.08, 0.0, 1.0)}),
    "texture_fixes": Map(Obj({"paint_out_uv": List(Vec(4, lo=0.0, hi=1.0), min_len=1)}), {}),
    "gear_style": Obj({"noise": Num(0.06, 0.0, 0.5), "noise_cells": Int(6, 1, 64), "swatches_per_row": Int(8, 1, 32),
                       "sample_m": Num(0.01, 0.002, 0.1)}),
    "palette": Map(Hex()),
    "gear_pieces": Map(Raw(None)),
    "gear_sets": Map(List(Str(), min_len=1)),
    "stress_pose": Map(Obj({"axis": Str(choices=POSE_AXES), "deg": Num(lo=-180.0, hi=180.0)})),
    "bodies": List(Body(), min_len=1),
})


def _resolve_like(name, raw, path, seen=()):
    """A piece with "like": <other piece> inherits every field of that piece it doesn't set."""
    piece = raw[name]
    if not isinstance(piece, dict):
        raise DataError(f"{path}.{name}: expected an object")
    base = piece.get("like")
    if base is None:
        return {k: v for k, v in piece.items() if k != "like"}
    if base not in raw:
        raise DataError(f"{path}.{name}.like: {base!r} is not a gear piece")
    if base in seen or base == name:
        raise DataError(f"{path}.{name}.like: the chain {' -> '.join(seen + (name, base))} loops")
    out = copy.deepcopy(_resolve_like(base, raw, path, seen + (name,)))
    out.update({k: v for k, v in piece.items() if k != "like"})
    return out


def _check_piece(name, piece, path, ctx):
    out = PIECE.check(piece, f"{path}.{name}", ctx)
    if out["shape"] == "cylinder":
        if piece.get("along_m") is None or "elevation_deg" in piece:
            raise DataError(f"{path}.{name}: a cylinder takes along_m and no elevation_deg")
        out["along_m"] = SPAN.check(piece["along_m"], f"{path}.{name}.along_m", ctx)
    else:
        if piece.get("elevation_deg") is None or "along_m" in piece:
            raise DataError(f"{path}.{name}: a sphere takes elevation_deg and no along_m")
        out["elevation_deg"] = ELEVATION.check(piece["elevation_deg"], f"{path}.{name}.elevation_deg", ctx)
    for key, span in (("angle_deg", out["angle_deg"]), ("along_m", out.get("along_m")),
                      ("elevation_deg", out.get("elevation_deg"))):
        if span is not None and not span[0] < span[1]:
            raise DataError(f"{path}.{name}.{key}: the first value must be below the second")
    if out["angle_deg"][1] - out["angle_deg"][0] > 360.0:
        raise DataError(f"{path}.{name}.angle_deg: spans more than 360 degrees")
    out["segments"] = [int(s) for s in out["segments"]]
    if out["segments"] != [s for s in piece["segments"]]:
        raise DataError(f"{path}.{name}.segments: expected whole numbers")
    out["fit_bones"] = (FIT_BONES.check(piece["fit_bones"], f"{path}.{name}.fit_bones", ctx)
                        if piece.get("fit_bones") is not None else [out["bone"]])
    out["stripe"] = (STRIPE.check(piece["stripe"], f"{path}.{name}.stripe", ctx)
                     if piece.get("stripe") is not None else None)
    if out["colour2"] is None and out["mix"] != 0.0:
        raise DataError(f"{path}.{name}.mix: needs a colour2 to mix with")
    return out


def load(path=TABLE):
    """Read, validate and normalise the table. Raises DataError naming the file and field."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DataError(f"{path}: {e}") from None
    ctx = {}
    try:
        table = TABLE_SCHEMA.check(raw, "npcs.json", ctx)
        raw_pieces = {k: v for k, v in raw.get("gear_pieces", {}).items() if not k.startswith("_comment")}
        table["gear_pieces"] = {name: _check_piece(name, _resolve_like(name, raw_pieces, "npcs.json.gear_pieces"),
                                                   "npcs.json.gear_pieces", ctx)
                                for name in raw_pieces}
        for ref_path, name in ctx.get("colour_refs", []):
            if name not in table["palette"]:
                raise DataError(f"{ref_path}: colour {name!r} is not in the palette block")
        for set_name, pieces in table["gear_sets"].items():
            for i, piece in enumerate(pieces):
                if piece not in table["gear_pieces"]:
                    raise DataError(f"npcs.json.gear_sets.{set_name}[{i}]: {piece!r} is not a gear piece")
        for asset, fix in table["texture_fixes"].items():
            for i, (u0, v0, u1, v1) in enumerate(fix["paint_out_uv"]):
                if not (u0 < u1 and v0 < v1):
                    raise DataError(f"npcs.json.texture_fixes.{asset}.paint_out_uv[{i}]: expected [u0, v0, u1, v1] "
                                    f"with u0 < u1 and v0 < v1")
        lo, hi = table["civilian_range"]["height_m"]
        if not lo < hi:
            raise DataError("npcs.json.civilian_range.height_m: the first value must be below the second")
        a_lo, a_hi = table["civilian_range"]["age_years"]
        if not a_lo < a_hi:
            raise DataError("npcs.json.civilian_range.age_years: the first value must be below the second")
        if table["budget"]["texture_px"] < table["atlas_px"]:
            raise DataError(f"npcs.json.atlas_px: {table['atlas_px']} px is over the budget's texture_px "
                            f"{table['budget']['texture_px']}")
        ids = [b["id"] for b in table["bodies"]]
        for i, body in enumerate(table["bodies"]):
            where = f"npcs.json.bodies[{i}]"
            if ids.index(body["id"]) != i:
                raise DataError(f"{where}.id: duplicate id {body['id']!r}")
            if not re.match(r"^[a-z][a-z0-9_]*$", body["id"]):
                raise DataError(f"{where}.id: {body['id']!r} must be lower-case snake_case")
            for j, set_name in enumerate(body["gear"]):
                if set_name not in table["gear_sets"]:
                    raise DataError(f"{where}.gear[{j}]: {set_name!r} is not a gear set")
            worn = []
            for name, piece in pieces_of(table, body):
                for under in piece["over"]:
                    if under not in worn:
                        raise DataError(f"{where}.gear: piece {name} goes over {under!r}, which this body "
                                        f"doesn't wear before it")
                    if table["gear_pieces"][under]["bone"] != piece["bone"]:
                        raise DataError(f"npcs.json.gear_pieces.{name}.over: {under!r} follows another bone")
                worn.append(name)
            for j, cloth in enumerate(body["clothes"]):
                if cloth["tint"] is not None and (cloth["top"] is not None or cloth["bottom"] is not None):
                    raise DataError(f"{where}.clothes[{j}]: give either tint or top/bottom, not both")
            if body["kind"] == "named" and sum(body["race"].values()) <= 0.0:
                raise DataError(f"{where}.race: the weights must not all be zero")
            if body["hair"] is None and body["hair_tint"] is not None:
                raise DataError(f"{where}.hair_tint: no hair to tint")
    except DataError as e:
        raise DataError(f"{path}: {e}") from None
    return table


def pieces_of(table, body):
    """The gear pieces a body wears, as (name, piece) in the order its sets list them, once each."""
    out, seen = [], set()
    for set_name in body["gear"]:
        for name in table["gear_sets"][set_name]:
            if name not in seen:
                seen.add(name)
                out.append((name, table["gear_pieces"][name]))
    return out


if __name__ == "__main__":
    try:
        t = load(sys.argv[1] if len(sys.argv) > 1 else TABLE)
    except DataError as e:
        print("FAIL", e)
        sys.exit(1)
    kinds = [b["kind"] for b in t["bodies"]]
    print(f"OK {len(kinds)} bodies ({kinds.count('named')} named, {kinds.count('civilian')} civilians), "
          f"{len(t['gear_pieces'])} gear pieces in {len(t['gear_sets'])} sets, {len(t['palette'])} colours")

"""Loads and validates tools/blender/characters.json, the table the character build reads.

It owns the schema of that table: which keys a block or a row may carry, the code default of
every optional field, and the checks that stop the build with the file, the path and the field
when the table is wrong. Authored data fails loudly (CLAUDE.md 5.6): an unknown key is an error,
a missing optional field inherits its code default, a present zero is zero, and a number must be
finite. It is plain Python with no Blender import, so the table can be checked anywhere:

    python3 tools/blender/character_data.py
"""
import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, "characters.json")

REQUIRED = object()


class DataError(ValueError):
    """A problem in characters.json, reported with the path of the offending field."""


class Field:
    """One schema node: validates a JSON value and returns it with defaults filled in."""

    def __init__(self, default=REQUIRED):
        self.default = default

    def fill(self, path):
        if self.default is REQUIRED:
            raise DataError(f"{path}: required field is missing")
        return copy.deepcopy(self.default)

    def check(self, value, path, ctx):
        raise NotImplementedError


class Num(Field):
    """A finite number within [lo, hi]."""

    def __init__(self, default=REQUIRED, lo=-math.inf, hi=math.inf, nullable=False):
        super().__init__(default)
        self.lo, self.hi, self.nullable = lo, hi, nullable

    def check(self, value, path, ctx):
        if value is None and self.nullable:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DataError(f"{path}: expected a number, got {value!r}")
        if not math.isfinite(value):
            raise DataError(f"{path}: {value!r} is not finite")
        if not self.lo <= value <= self.hi:
            raise DataError(f"{path}: {value} is outside [{self.lo}, {self.hi}]")
        return float(value)


class Int(Num):
    def check(self, value, path, ctx):
        if isinstance(value, bool) or not isinstance(value, int):
            raise DataError(f"{path}: expected an integer, got {value!r}")
        return int(super().check(value, path, ctx))


class Bool(Field):
    def check(self, value, path, ctx):
        if not isinstance(value, bool):
            raise DataError(f"{path}: expected true or false, got {value!r}")
        return value


class Str(Field):
    """A string, optionally one of a fixed set, optionally null."""

    def __init__(self, default=REQUIRED, choices=None, nullable=False):
        super().__init__(default)
        self.choices, self.nullable = choices, nullable

    def check(self, value, path, ctx):
        if value is None and self.nullable:
            return None
        if not isinstance(value, str) or not value:
            raise DataError(f"{path}: expected a non-empty string, got {value!r}")
        if self.choices is not None and value not in self.choices:
            raise DataError(f"{path}: {value!r} is not one of {sorted(self.choices)}")
        return value


class Mat(Str):
    """A material name from the table's materials block ("skin" means the row's skin)."""

    def check(self, value, path, ctx):
        value = super().check(value, path, ctx)
        if value is not None:
            ctx.setdefault("mat_refs", []).append((path, value))
        return value


class Vec(Field):
    """A fixed-length list of finite numbers."""

    def __init__(self, n, default=REQUIRED, lo=-math.inf, hi=math.inf):
        super().__init__(default)
        self.n, self.item = n, Num(lo=lo, hi=hi)

    def check(self, value, path, ctx):
        if not isinstance(value, list) or len(value) != self.n:
            raise DataError(f"{path}: expected a list of {self.n} numbers, got {value!r}")
        return [self.item.check(v, f"{path}[{i}]", ctx) for i, v in enumerate(value)]


class List(Field):
    def __init__(self, item, default=REQUIRED, min_len=0):
        super().__init__(default)
        self.item, self.min_len = item, min_len

    def check(self, value, path, ctx):
        if not isinstance(value, list) or len(value) < self.min_len:
            raise DataError(f"{path}: expected a list of at least {self.min_len} items")
        return [self.item.check(v, f"{path}[{i}]", ctx) for i, v in enumerate(value)]


class Obj(Field):
    """A JSON object with a closed set of keys. Keys starting with "_comment" are notes."""

    def __init__(self, fields, default=REQUIRED):
        super().__init__(default)
        self.fields = fields

    def fill(self, path):
        if self.default is not REQUIRED:
            return copy.deepcopy(self.default)
        return {k: f.fill(f"{path}.{k}") for k, f in self.fields.items()}

    def check(self, value, path, ctx):
        if not isinstance(value, dict):
            raise DataError(f"{path}: expected an object")
        for k in value:
            if k not in self.fields and not k.startswith("_comment"):
                raise DataError(f"{path}.{k}: unknown key (known: {', '.join(self.fields)})")
        out = {}
        for k, f in self.fields.items():
            out[k] = f.check(value[k], f"{path}.{k}", ctx) if k in value else f.fill(f"{path}.{k}")
        return out


class Map(Field):
    """A JSON object whose keys are names chosen by the table (materials, holds)."""

    def __init__(self, item, default=REQUIRED):
        super().__init__(default)
        self.item = item

    def check(self, value, path, ctx):
        if not isinstance(value, dict):
            raise DataError(f"{path}: expected an object")
        return {k: self.item.check(v, f"{path}.{k}", ctx) for k, v in value.items() if not k.startswith("_comment")}


class Part(Field):
    """One outfit part row: {"part": <type>, ...params}; the params are checked per type."""

    def check(self, value, path, ctx):
        if not isinstance(value, dict) or "part" not in value:
            raise DataError(f"{path}: an outfit part needs a \"part\" key")
        kind = value["part"]
        if kind not in PART_SCHEMAS:
            raise DataError(f"{path}.part: unknown part {kind!r} (known: {', '.join(PART_SCHEMAS)})")
        body = {k: v for k, v in value.items() if k != "part"}
        out = Obj(PART_SCHEMAS[kind]).check(body, f"{path}({kind})", ctx)
        out["part"] = kind
        return out


# ----------------------------------------------------------------------------- schema

SEGMENTS = ("head", "neck", "chest", "pelvis", "upperarm", "forearm", "hand", "thigh", "shin", "foot")
HAIR_STYLES = ("crop", "short", "slick", "messy", "mohawk", "bun", "ponytail", "bob", "horseshoe")
BAND_PLACES = ("chest", "chest_low", "hem", "upperarm", "elbow_roll", "forearm", "cuff", "thigh", "knee", "shin")
PATCH_TARGETS = ("chest", "pelvis", "upperarm", "forearm", "thigh", "shin", "hood")
ARMOUR_PIECES = ("shoulder", "bracer", "thigh", "knee", "shin")
SIDES = ("l", "r")

# Parameters of every outfit part type, with their code defaults. The builders in
# build_characters.py read exactly these keys; that script checks both lists name the same types.
PART_SCHEMAS = {
    "hair": {"style": Str("short", choices=HAIR_STYLES), "mat": Mat("hair_black")},
    "ears": {},
    "glasses": {"lens": Mat("lens_tint"), "frame": Mat("metal")},
    "goggles": {"on": Str("eyes", choices=("eyes", "forehead")), "lens": Mat("lens_dark"),
                "rim": Mat("brass"), "strap": Mat("leather")},
    "loupe": {"side": Str("r", choices=SIDES), "body": Mat("metal_dark"), "lens": Mat("led_amber")},
    "respirator": {"mat": Mat("rubber"), "filter": Mat("metal_dark"), "led": Mat("led_green")},
    "mask_down": {"mat": Mat("cloth_paleblue")},
    "earpiece": {"side": Str("r", choices=SIDES), "mat": Mat("rubber"), "led": Mat("led_cyan")},
    "cap": {"style": Str("baseball", choices=("baseball", "peaked", "paper", "beanie")),
            "mat": Mat("cloth_black"), "trim": Mat(None, nullable=True)},
    "helmet": {"mat": Mat("armour_greyblue"), "visor": Mat("visor_red")},
    "hood": {"mat": Mat("cloth_grey"), "up": Bool(True)},
    "collar": {"mat": Mat("cloth_black"), "edge": Mat(None, nullable=True), "height_m": Num(0.06, 0.01, 0.2),
               "open_deg": Num(70.0, 0.0, 180.0), "flare_m": Num(0.02, 0.0, 0.1)},
    "coat": {"mat": Mat("cloth_charcoal"), "edge": Mat(None, nullable=True), "hem_z": Num(0.3, 0.05, 0.55),
             "flare_m": Num(0.08, 0.0, 0.4), "open_deg": Num(80.0, 30.0, 180.0)},
    "chest_strip": {"mat": Mat("metal"), "width_m": Num(0.015, 0.004, 0.12)},
    "apron": {"mat": Mat("cloth_black"), "bib": Bool(True), "hem_z": Num(0.33, 0.1, 0.5)},
    "vest": {"mat": Mat("armour_black"), "plates": Mat(None, nullable=True), "open_deg": Num(0.0, 0.0, 120.0),
             "top_z": Num(0.8, 0.7, 0.83)},
    "armour": {"mat": Mat("armour_greyblue"), "pieces": List(Str(choices=ARMOUR_PIECES), [])},
    "belt": {"mat": Mat("leather"), "buckle": Mat("metal")},
    "holster": {"side": Str("r", choices=SIDES), "mat": Mat("leather_black"), "gun": Mat("metal_dark")},
    "backpack": {"mat": Mat("cloth_olive"), "scrap": Mat("metal"), "scrap2": Mat("metal_rust")},
    "rifle_back": {"mat": Mat("metal_dark"), "stock": Mat("armour_black"), "sling": Mat("cloth_black")},
    "shoulder_light": {"side": Str("l", choices=SIDES), "mat": Mat("metal_dark"), "lens": Mat("led_white")},
    "towel": {"side": Str("l", choices=SIDES), "mat": Mat("cloth_towel")},
    "beads": {"mat": Mat("wood")},
    "cyber_arm": {"side": Str("r", choices=SIDES), "mat": Mat("metal"), "joint": Mat("metal_dark"),
                  "led": Mat("led_amber")},
    "wrist_scanner": {"side": Str("l", choices=SIDES), "mat": Mat("armour_black"), "screen": Mat("screen_cyan")},
    "bands": {"mat": Mat("reflective"), "on": List(Str(choices=BAND_PLACES), min_len=1),
              "width_m": Num(0.03, 0.005, 0.12)},
    "patchwork": {"mats": List(Mat(), min_len=1), "on": List(Str(choices=PATCH_TARGETS), min_len=1),
                  "share": Num(0.4, 0.0, 1.0), "seed": Int(1, 0, 1 << 30)},
    "umbrella": {"canopy": Mat("plastic_clear"), "rim": Mat("neon_blue"), "shaft": Mat("metal"),
                 "radius_m": Num(0.45, 0.2, 0.8), "shaft_m": Num(0.8, 0.3, 1.2)},
}

MATERIAL = Obj({
    "color": Str(),
    "roughness": Num(0.6, 0.0, 1.0),
    "metallic": Num(0.0, 0.0, 1.0),
    "emission": Str(None, nullable=True),
    "emission_strength": Num(0.0, 0.0, 50.0),
    "alpha": Num(1.0, 0.0, 1.0),
})

RING4 = Vec(4)
RING5 = Vec(5)
RING3 = Vec(3)

ANATOMY = Obj({
    "ankle_z": Num(lo=0, hi=1), "knee_z": Num(lo=0, hi=1), "hip_z": Num(lo=0, hi=1), "waist_z": Num(lo=0, hi=1),
    "chest_z": Num(lo=0, hi=1), "neck_z": Num(lo=0, hi=1), "skull_z": Num(lo=0, hi=1), "chin_z": Num(lo=0, hi=1),
    "hip_x": Num(lo=0, hi=0.2), "shoulder_x": Num(lo=0, hi=0.3), "shoulder_z": Num(lo=0, hi=1),
    "upperarm_len": Num(lo=0.05, hi=0.3), "forearm_len": Num(lo=0.05, hi=0.3), "hand_len": Num(lo=0.03, hi=0.2),
    "heel_y": Num(lo=0, hi=0.1), "ball_y": Num(lo=0, hi=0.2), "toe_y": Num(lo=0, hi=0.2), "ball_z": Num(lo=0, hi=0.05),
    "sole_h": Num(lo=0.001, hi=0.05), "arm_splay_deg": Num(lo=0, hi=45),
    "torso_rings": List(RING5, min_len=2), "pelvis_rings": List(RING4, min_len=2),
    "neck_rings": List(RING4, min_len=2), "head_rings": List(RING4, min_len=2),
    "upperarm_rings": List(RING3, min_len=2), "forearm_rings": List(RING3, min_len=2),
    "hand_rings": List(RING3, min_len=2), "thigh_rings": List(RING3, min_len=2),
    "shin_rings": List(RING4, min_len=2), "foot_rings": List(RING3, min_len=2),
    "eye_band": Vec(2, lo=0.0, hi=1.0),
    "shoulder_cap": Num(lo=0.005, hi=0.1), "elbow_cap": Num(lo=0.005, hi=0.1), "knee_cap": Num(lo=0.005, hi=0.1),
    "sides": Obj({"torso": Int(lo=6, hi=16), "pelvis": Int(lo=6, hi=16), "head": Int(lo=6, hi=16),
                  "limb": Int(lo=6, hi=16)}),
})

ANIMATIONS = Obj({
    "fps": Int(lo=10, hi=120),
    "idle": Obj({"length_s": Num(lo=0.1), "loop": Bool(), "breath_deg": Num(lo=0, hi=10),
                 "sway_m": Num(lo=0, hi=0.1), "sway_roll_deg": Num(lo=0, hi=10), "knee_drop_m": Num(lo=0, hi=0.1),
                 "head_turn_deg": Num(lo=-60, hi=60), "head_turn_s": Vec(4, lo=0), "elbow_deg": Num(lo=0, hi=90)}),
    "walk": Obj({"loop": Bool(), "speed_m_s": Num(lo=0.1, hi=10), "cycle_s": Num(lo=0.3, hi=3),
                 "stance_fraction": Num(lo=0.3, hi=0.7), "front_fraction": Num(lo=0.2, hi=0.8),
                 "step_width": Num(lo=0.3, hi=1.5), "foot_lift_m": Num(lo=0, hi=0.4),
                 "heel_strike_deg": Num(lo=0, hi=40), "heel_peel_deg": Num(lo=0, hi=60),
                 "peel_fraction": Num(lo=0, hi=0.6), "knee_margin_m": Num(lo=0, hi=0.1),
                 "hip_yaw_deg": Num(lo=0, hi=20), "hip_roll_deg": Num(lo=0, hi=20), "hip_sway_m": Num(lo=0, hi=0.1),
                 "lean_deg": Num(lo=-20, hi=20), "arm_swing_deg": Num(lo=0, hi=60),
                 "elbow_deg": Vec(2, lo=0, hi=150)}),
    "talk": Obj({"length_s": Num(lo=0.1), "loop": Bool(), "nod_deg": Num(lo=0, hi=30), "turn_deg": Num(lo=0, hi=30),
                 "sway_m": Num(lo=0, hi=0.1), "gesture_deg": Num(lo=0, hi=60), "elbow_deg": Num(lo=0, hi=150),
                 "twist_deg": Num(lo=0, hi=90)}),
    "guard": Obj({"length_s": Num(lo=0.1), "loop": Bool(), "stance_widen_m": Num(lo=0, hi=0.3),
                  "breath_deg": Num(lo=0, hi=10), "scan_deg": Num(lo=0, hi=60), "knee_drop_m": Num(lo=0, hi=0.1)}),
    "sit": Obj({"length_s": Num(lo=0.1), "loop": Bool(), "seat_height_m": Num(lo=0.1, hi=1.2),
                "slouch_deg": Num(lo=-20, hi=30)}),
    "holds": Map(Obj({b: Vec(3, [0.0, 0.0, 0.0], lo=-180, hi=180)
                      for b in ("upperarm_r", "forearm_r", "hand_r", "upperarm_l", "forearm_l", "hand_l")})),
})

MODEL = Obj({
    "out_dir": Str(),
    "layer_gap_m": Num(lo=0.01, hi=0.1),
    "cloth_thick_m": Num(lo=0.002, hi=0.05),
    "plate_thick_m": Num(lo=0.002, hi=0.05),
    "smooth_angle_deg": Num(lo=0, hi=180),
    "lineup_spacing_m": Num(lo=0.5, hi=5),
    "lineup_per_row": Int(lo=1, hi=100),
})

# Optional fields of a character row, with their code defaults.
ROW = Obj({
    "id": Str(),
    "name": Str(""),
    "role": Str(""),
    "height_m": Num(1.78, 1.0, 2.5),
    "build": Obj({"shoulders": Num(1.0, 0.6, 1.6), "hips": Num(1.0, 0.6, 1.6), "girth": Num(1.0, 0.6, 1.8),
                  "belly": Num(0.0, 0.0, 1.0), "head": Num(1.0, 0.8, 1.3)}),
    "skin": Mat("skin_tan"),
    "clothes": Obj({"top": Mat("cloth_grey"), "sleeves": Mat(None, nullable=True),
                    "forearms": Mat(None, nullable=True), "hands": Mat("skin"), "neck": Mat("skin"),
                    "bottom": Mat("cloth_denim"), "shoes": Mat("leather"), "soles": Mat("rubber")}),
    "fit": Obj({"top": Num(1.0, 0.8, 1.5), "bottom": Num(1.0, 0.8, 1.5)}),
    "pose": Obj({"stoop_deg": Num(0.0, -10.0, 40.0), "guard": Str("hips", choices=("hips", "clasped")),
                 "hold": Str(None, nullable=True), "arm_splay_deg": Num(None, 0.0, 45.0, nullable=True)}),
    "walk_cycle_s": Num(None, 0.3, 3.0, nullable=True),
    "parts": List(Part(), []),
})

TABLE_SCHEMA = Obj({
    "model": MODEL,
    "anatomy": ANATOMY,
    "animations": ANIMATIONS,
    "materials": Map(MATERIAL),
    "characters": List(ROW, min_len=1),
})


def parse_hex(text, path):
    """"#rrggbb" -> (r, g, b) in 0..1 (sRGB)."""
    if not (isinstance(text, str) and len(text) == 7 and text[0] == "#"):
        raise DataError(f"{path}: expected a colour like \"#a1b2c3\", got {text!r}")
    try:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    except ValueError:
        raise DataError(f"{path}: {text!r} is not a hex colour") from None


def load(path=TABLE):
    """Read, validate and normalise the table. Raises DataError naming the file and field."""
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DataError(f"{path}: {e}") from None
    ctx = {}
    try:
        table = TABLE_SCHEMA.check(raw, "characters.json", ctx)
        for name, m in table["materials"].items():
            m["color"] = parse_hex(m["color"], f"characters.json.materials.{name}.color")
            if m["emission"] is not None:
                m["emission"] = parse_hex(m["emission"], f"characters.json.materials.{name}.emission")
        for ref_path, name in ctx.get("mat_refs", []):
            if name != "skin" and name not in table["materials"]:
                raise DataError(f"{ref_path}: material {name!r} is not in the materials block")
        ids = [row["id"] for row in table["characters"]]
        for i, cid in enumerate(ids):
            if ids.index(cid) != i:
                raise DataError(f"characters.json.characters[{i}].id: duplicate id {cid!r}")
            if not cid.replace("_", "").isalnum() or cid.lower() != cid:
                raise DataError(f"characters.json.characters[{i}].id: {cid!r} must be lower-case snake_case")
        holds = table["animations"]["holds"]
        for i, row in enumerate(table["characters"]):
            hold = row["pose"]["hold"]
            if hold is not None and hold not in holds:
                raise DataError(f"characters.json.characters[{i}].pose.hold: {hold!r} is not in animations.holds")
    except DataError as e:
        raise DataError(f"{path}: {e}") from None
    return table


if __name__ == "__main__":
    try:
        t = load(sys.argv[1] if len(sys.argv) > 1 else TABLE)
    except DataError as e:
        print("FAIL", e)
        sys.exit(1)
    print(f"OK {len(t['characters'])} characters, {len(t['materials'])} materials")

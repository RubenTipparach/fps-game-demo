"""Field types for validating the tables the Blender builds read (tools/blender/npcs.json).

It owns the one schema checker the character table uses: typed fields with ranges and required
keys, lists, objects that refuse unknown keys, and maps, each failing with the path of the
offending field (CLAUDE.md 5.6: an unknown key is an error, authored data fails loudly). It lives
in tools/blender as plain Python with no bpy, so a table can be checked without Blender. It was
split out of the retired segmented-character table's loader (character_data.py) when the
generated NPC bodies replaced those characters (openspec/changes/archive/2026-09-28-npc-characters, task 5.4).
"""
import copy
import math


REQUIRED = object()


class DataError(ValueError):
    """A problem in a table, reported with the path of the offending field."""


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


def parse_hex(text, path):
    """"#rrggbb" -> (r, g, b) in 0..1 (sRGB)."""
    if not (isinstance(text, str) and len(text) == 7 and text[0] == "#"):
        raise DataError(f"{path}: expected a colour like \"#a1b2c3\", got {text!r}")
    try:
        return tuple(int(text[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    except ValueError:
        raise DataError(f"{path}: {text!r} is not a hex colour") from None

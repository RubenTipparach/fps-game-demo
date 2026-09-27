"""Room auto-detailing shared by the three level generators (CSG, TrenchBroom, Blender).

Unreal 1 / UT99 rooms read as "Unreal" largely because of their trim vocabulary: a baseboard at
the floor, a cornice or light trough at the ceiling line, pilasters that break long walls into
bays, beams across ceilings. Every room here is an axis-aligned "air" box, so trims can be
generated: walk each wall, cut out every place where another air volume (corridor, doorway,
arch, connected room) pierces that wall, and emit boxes. Each generator then turns the boxes
into its own primitives (CSG boxes, Quake brushes, bevelled Blender blocks), so all three
levels share one design language without sharing geometry.

Coordinates are Godot metres (x right, y up, -z north). Pure Python, no dependencies.
"""


class Room:
    def __init__(self, name, x, y, z, style="tech", trims=True, beams=True, ceiling=None):
        self.name, self.x, self.y, self.z = name, x, y, z
        self.style = style
        self.trims = trims
        self.beams = beams  # structural ceiling beams (off for vaulted rooms)
        self.ceiling = ceiling  # ceiling material, so girders can contrast with it


# Trim vocabulary per style (see docs/ut99_reference.md, checklist items 1, 3 and 9):
#   base/cornice: (height, depth, material); band: (height, depth, material, height above floor)
#   pilaster: (width, depth, material, spacing); cap: (height, extra depth, material) - also used
#   for the plinth at the pilaster's foot; beam: (material,) - ceiling girders spanning the room
#   between opposite pilasters. Metres (1 m = 52.5 Unreal units).
STYLES = {
    "tech": dict(base=(0.35, 0.10, "rust_metal"), cornice=(0.30, 0.18, "tech_panel"),
                 band=(0.12, 0.06, "hazard_stripes", 1.15),
                 pilaster=(0.6, 0.16, "tech_panel", 4.0), cap=(0.18, 0.08, "rust_metal"), beam=("rust_metal",)),
    "stone": dict(base=(0.45, 0.14, "tech_panel"), cornice=(0.35, 0.22, "stone_blocks"),
                  band=None, pilaster=(0.8, 0.22, "stone_blocks", 5.0), cap=(0.22, 0.10, "tech_panel"),
                  beam=("rust_metal",)),
    "brick": dict(base=(0.30, 0.08, "stone_blocks"), cornice=(0.25, 0.14, "stone_blocks"),
                  band=None, pilaster=(0.5, 0.14, "stone_blocks", 3.5), cap=(0.15, 0.06, "stone_blocks"),
                  beam=("rust_metal",)),
}


def keep_out(center, half):
    """A box that trims must not touch, e.g. a light fixture: keep_out((x, y, z), (hx, hy, hz))."""
    return (tuple(c - h for c, h in zip(center, half)), tuple(c + h for c, h in zip(center, half)))


def _box_hits(lo, hi, boxes, margin=0.0):
    for blo, bhi in boxes:
        if all(lo[i] - margin < bhi[i] and blo[i] < hi[i] + margin for i in range(3)):
            return True
    return False


def _overlaps(a0, a1, b0, b1, eps=1e-6):
    return a0 < b1 - eps and b0 < a1 - eps


def _subtract(intervals, cut):
    out = []
    c0, c1 = cut
    for a0, a1 in intervals:
        if c1 <= a0 or c0 >= a1:
            out.append((a0, a1))
            continue
        if c0 > a0:
            out.append((a0, c0))
        if c1 < a1:
            out.append((c1, a1))
    return out


def walls(room):
    """(axis_along, fixed_axis, fixed_value, inward_sign, (t0, t1)) for the 4 walls."""
    (x0, x1), (z0, z1) = room.x, room.z
    return [("x", "z", z0, +1, (x0, x1)),   # north wall, faces +z
            ("x", "z", z1, -1, (x0, x1)),   # south wall
            ("z", "x", x0, +1, (z0, z1)),   # west wall, faces +x
            ("z", "x", x1, -1, (z0, z1))]   # east wall


def _coord(axis_along, fixed_axis, t, fixed, y):
    p = {"y": y}
    p[axis_along] = t
    p[fixed_axis] = fixed
    return p["x"], p["y"], p["z"]


def openings_on_wall(room, wall, airs, margin=0.15):
    """Intervals along the wall (with their y ranges) where another air volume pierces it."""
    along, fixed_axis, fixed, inward, _ = wall
    ax = {"x": 0, "y": 1, "z": 2}
    res = []
    for a in airs:
        if a is room:
            continue
        rng = {"x": a.x, "y": a.y, "z": a.z}
        f0, f1 = rng[fixed_axis]
        # it pierces the wall if it spans across the wall plane (or touches it from outside)
        if not (f0 - 0.02 <= fixed <= f1 + 0.02):
            continue
        t0, t1 = rng[along]
        y0, y1 = a.y
        if _overlaps(y0, y1, room.y[0], room.y[1]):
            res.append(((t0 - margin, t1 + margin), (y0, y1)))
    return res


def room_trims(room, airs, avoid=()):
    """Return a list of (lo, hi, material) boxes decorating the room's walls and ceiling.

    `avoid` is a list of keep_out() boxes (light fixtures, skylights, ...): pilasters and beams
    that would touch one are left out."""
    if not room.trims:
        return []
    st = STYLES[room.style]
    y0, y1 = room.y
    out = []
    for wall in walls(room):
        along, fixed_axis, fixed, inward, (t0, t1) = wall
        ops = openings_on_wall(room, wall, airs)

        def emit(yb0, yb1, depth, mat, segs):
            for s0, s1 in segs:
                if s1 - s0 < 0.25:
                    continue
                a = _coord(along, fixed_axis, s0, fixed, yb0)
                b = _coord(along, fixed_axis, s1, fixed + inward * depth, yb1)
                out.append((tuple(min(p, q) for p, q in zip(a, b)), tuple(max(p, q) for p, q in zip(a, b)), mat))

        def free_segments(yb0, yb1):
            segs = [(t0, t1)]
            for (c0, c1), (oy0, oy1) in ops:
                if _overlaps(yb0, yb1, oy0, oy1):
                    segs = _subtract(segs, (c0, c1))
            return segs

        bh, bd, bm = st["base"]
        emit(y0, y0 + bh, bd, bm, free_segments(y0, y0 + bh))
        ch, cd, cm = st["cornice"]
        if y1 - y0 > 3.0:
            emit(y1 - ch, y1, cd, cm, free_segments(y1 - ch, y1))
        if st.get("band") and y1 - y0 > 3.0:
            h, d, m, at = st["band"]
            emit(y0 + at, y0 + at + h, d, m, free_segments(y0 + at, y0 + at + h))
        # pilasters dividing long walls into bays: plinth, shaft, capital (never a bare prism)
        pw, pd, pm, spacing = st["pilaster"]
        cap_h, cap_d, cap_m = st["cap"]
        for t in pilaster_positions(room, wall):
            span = (t - pw / 2 - 0.1, t + pw / 2 + 0.1)
            blocked = any(_overlaps(span[0], span[1], c0, c1) and oy0 < y1 - 0.5 for (c0, c1), (oy0, oy1) in ops)
            a = _coord(along, fixed_axis, span[0], fixed, y0)
            b = _coord(along, fixed_axis, span[1], fixed + inward * (pd + cap_d), y1)
            lo, hi = tuple(map(min, a, b)), tuple(map(max, a, b))
            if blocked or _box_hits(lo, hi, avoid, 0.2):
                continue
            top = y1 - (ch if y1 - y0 > 3.0 else 0.0)
            plinth = bh + 0.15
            emit(y0, y0 + plinth, pd + cap_d, cap_m, [(t - pw / 2 - 0.08, t + pw / 2 + 0.08)])
            emit(y0 + plinth, top - cap_h, pd, pm, [(t - pw / 2, t + pw / 2)])
            emit(top - cap_h, top, pd + cap_d, cap_m, [(t - pw / 2 - 0.08, t + pw / 2 + 0.08)])
    out += ceiling_beams(room, airs, avoid)
    return out


def pilaster_positions(room, wall):
    _, _, _, _, (t0, t1) = wall
    spacing = STYLES[room.style]["pilaster"][3]
    length = t1 - t0
    if length < spacing * 1.5 or room.y[1] - room.y[0] < 3.0:
        return []
    n = int(length // spacing)
    return [t0 + i * length / n for i in range(1, n)]


def ceiling_beams(room, airs, avoid=()):
    """Girders across the short span of the room, lined up with the pilasters of the long walls,
    so wall and ceiling read as one structural frame (UT99 checklist item 9)."""
    if not room.beams or room.y[1] - room.y[0] < 3.0:
        return []
    (x0, x1), (y0, y1), (z0, z1) = room.x, room.y, room.z
    span_x = x1 - x0 <= z1 - z0          # beams run along x, spaced along z
    span = (x1 - x0) if span_x else (z1 - z0)
    long_wall = walls(room)[2] if span_x else walls(room)[0]
    depth = min(0.8, max(0.3, 0.2 + span * 0.022))
    width = depth * 0.75
    mat = STYLES[room.style]["beam"][0]
    if mat == room.ceiling:  # trims must contrast with what they sit on
        mat = "tech_panel"
    out = []
    for t in pilaster_positions(room, long_wall):
        if span_x:
            lo, hi = (x0, y1 - depth, t - width / 2), (x1, y1, t + width / 2)
        else:
            lo, hi = (t - width / 2, y1 - depth, z0), (t + width / 2, y1, z1)
        others = [((a.x[0], a.y[0], a.z[0]), (a.x[1], a.y[1], a.z[1])) for a in airs if a is not room]
        if _box_hits(lo, hi, avoid, 0.25) or _box_hits(lo, hi, [o for o in others if o[0][1] < y1 - 0.01], -0.02):
            continue
        out.append((lo, hi, mat))
    return out


def all_trims(rooms, airs=None, avoid=()):
    airs = airs or rooms
    boxes = []
    for r in rooms:
        boxes += room_trims(r, airs, avoid)
    return boxes

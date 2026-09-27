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
    def __init__(self, name, x, y, z, style="tech", trims=True):
        self.name, self.x, self.y, self.z = name, x, y, z
        self.style = style
        self.trims = trims


# Trim vocabulary per style: (height, depth, material) for baseboard/cornice/band, and
# pilaster (width, depth, material, spacing). Heights in metres.
STYLES = {
    "tech": dict(base=(0.35, 0.10, "rust_metal"), cornice=(0.30, 0.18, "tech_panel"),
                 band=(0.12, 0.06, "hazard_stripes", 1.15),
                 pilaster=(0.6, 0.16, "tech_panel", 4.0), cap=(0.18, 0.08, "rust_metal")),
    "stone": dict(base=(0.45, 0.14, "tech_panel"), cornice=(0.35, 0.22, "stone_blocks"),
                  band=None, pilaster=(0.8, 0.22, "stone_blocks", 5.0), cap=(0.22, 0.10, "tech_panel")),
    "brick": dict(base=(0.30, 0.08, "stone_blocks"), cornice=(0.25, 0.14, "stone_blocks"),
                  band=None, pilaster=(0.5, 0.14, "stone_blocks", 3.5), cap=(0.15, 0.06, "stone_blocks")),
}


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


def room_trims(room, airs):
    """Return a list of (lo, hi, material) boxes decorating the room's walls."""
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
        # pilasters dividing long walls into bays
        pw, pd, pm, spacing = st["pilaster"]
        length = t1 - t0
        if length >= spacing * 1.5 and y1 - y0 >= 3.0:
            n = int(length // spacing)
            step = length / n
            cap_h, cap_d, cap_m = st["cap"]
            for i in range(1, n):
                t = t0 + i * step
                span = (t - pw / 2 - 0.1, t + pw / 2 + 0.1)
                blocked = any(_overlaps(span[0], span[1], c0, c1) and oy0 < y1 - 0.5 for (c0, c1), (oy0, oy1) in ops)
                if blocked:
                    continue
                top = y1 - (ch if y1 - y0 > 3.0 else 0.0)
                emit(y0, top - cap_h, pd, pm, [(t - pw / 2, t + pw / 2)])
                emit(top - cap_h, top, pd + cap_d, cap_m, [(t - pw / 2 - 0.08, t + pw / 2 + 0.08)])
    return out


def all_trims(rooms, airs=None):
    airs = airs or rooms
    boxes = []
    for r in rooms:
        boxes += room_trims(r, airs)
    return boxes

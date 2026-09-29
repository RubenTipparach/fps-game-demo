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
    all_walls = walls(room)
    all_ops = [openings_on_wall(room, w, airs) for w in all_walls]

    def corner_trimmed(wall_index, pos, yb0, yb1):
        """Does wall `wall_index` carry a trim (in the band yb0..yb1) at `pos` along it?"""
        return not any(_overlaps(yb0, yb1, oy0, oy1) and c0 <= pos <= c1 for (c0, c1), (oy0, oy1) in all_ops[wall_index])

    for wi, wall in enumerate(all_walls):
        along, fixed_axis, fixed, inward, (t0, t1) = wall
        ops = all_ops[wi]

        def emit(yb0, yb1, depth, mat, segs, corners=True):
            for s0, s1 in segs:
                # No z-fighting at inside corners: the x-running walls own the corner, so trims
                # on the z-running walls stop where those trims' faces begin (otherwise their
                # top/front faces would overlap in the same plane).
                if corners and along == "z":
                    if s0 <= t0 + 1e-6 and corner_trimmed(0, fixed, yb0, yb1):
                        s0 = t0 + depth
                    if s1 >= t1 - 1e-6 and corner_trimmed(1, fixed, yb0, yb1):
                        s1 = t1 - depth
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
            emit(y0, y0 + plinth, pd + cap_d, cap_m, [(t - pw / 2 - 0.08, t + pw / 2 + 0.08)], False)
            emit(y0 + plinth, top - cap_h, pd, pm, [(t - pw / 2, t + pw / 2)], False)
            emit(top - cap_h, top, pd + cap_d, cap_m, [(t - pw / 2 - 0.08, t + pw / 2 + 0.08)], False)
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
    st = STYLES[room.style]
    depth = min(0.8, max(0.3, 0.2 + span * 0.022))
    # never flush with the cornice or capital undersides (coplanar faces z-fight)
    for bad in (st["cornice"][0], st["cornice"][0] + st["cap"][0]):
        if abs(depth - bad) < 0.03:
            depth = bad + 0.06
    width = st["pilaster"][0] * 0.75   # narrower than the pilaster it bears on: no shared side planes
    mat = st["beam"][0]
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


# ----------------------------------------------------------------------------- frame props

# Frame props built by tools/blender/build_props.py. `fits` is the level opening (width, height)
# the prop is placed in; `clear` is the prop's own clear opening. Clear is always smaller than
# fits (REVEAL per side and at the top), so the prop's reveals stand proud of the walls and
# ceiling around them instead of sharing their planes (which z-fights).
REVEAL = 0.1
FRAMES = {
    "doorway": dict(fits=(3.2, 3.3), clear=(3.0, 3.2), depth=0.5),
    "archway_400x400": dict(fits=(4.0, 4.0), clear=(3.8, 3.9), depth=0.5),
    "archway_400x350": dict(fits=(4.0, 3.5), clear=(3.8, 3.4), depth=0.5),
}


def frame_solids(kind, pos, yaw=0.0):
    """Approximate boxes of a frame prop in level space (for the z-fighting check)."""
    f = FRAMES[kind]
    W, H = f["clear"][0] / 2, f["clear"][1]
    D = f["depth"]
    boxes = []
    for sx in (-1, 1):
        def X(a, b):
            return (min(sx * a, sx * b), max(sx * a, sx * b))
        if kind == "doorway":
            boxes.append((X(W, W + 0.65), (0, H + 0.1), (-D, D)))
            for sz in (-1, 1):
                def Z(a, b):
                    return (min(sz * a, sz * b), max(sz * a, sz * b))
                boxes += [(X(W + 0.05, W + 0.85), (0, 0.35), Z(D, D + 0.2)),
                          (X(W + 0.13, W + 0.77), (0.35, H + 0.05), Z(D, D + 0.12)),
                          (X(W + 0.02, W + 0.88), (H + 0.05, H + 0.3), Z(D, D + 0.18))]
        else:
            boxes.append((X(W, f["fits"][0] / 2 + 0.5), (0, H), (-D, D)))
            for sz in (-1, 1):
                def Z(a, b):
                    return (min(sz * a, sz * b), max(sz * a, sz * b))
                boxes += [(X(W - 0.05, W + 0.7), (0, 0.4), Z(D, D + 0.16)),
                          (X(W + 0.05, W + 0.6), (0.4, H - 0.25), Z(D, D + 0.16)),
                          (X(W - 0.09, W + 0.74), (H - 0.25, H), Z(D, D + 0.21))]
    if kind == "doorway":
        boxes += [((-(W + 0.95), W + 0.95), (H, H + 1.0), (-(D + 0.14), D + 0.14)),
                  ((-(W + 1.0), W + 1.0), (H + 0.9, H + 1.08), (-(D + 0.2), D + 0.2))]
    else:
        boxes += [((-(W + 0.75), W + 0.75), (H, H + 0.8), (-(D + 0.16), D + 0.16)),
                  ((-(W + 0.85), W + 0.85), (H + 0.7, H + 0.9), (-(D + 0.26), D + 0.26))]
    turned = round(yaw / 90.0) % 2 == 1
    out = []
    for bx, by, bz in boxes:
        if turned:
            bx, bz = bz, bx
        out.append(((pos[0] + bx[0], pos[1] + by[0], pos[2] + bz[0]), (pos[0] + bx[1], pos[1] + by[1], pos[2] + bz[1])))
    return out


# ----------------------------------------------------------------------------- framed doorways

# A doorway built into a level's walls by E1M3's rules (openspec/changes/hub-doorways, design
# section 3.2): carved at its fits, the clear opening plus REVEAL at each jamb and at the head;
# liners fill the reveals, so the opening a person walks through is the clear one; an
# architrave, or on an entrance a portal, stands proud of each wall face that faces air. It is
# FRAMES' rule (R2) at any size, for levels whose doors are boxes in their own mesh rather than a
# frame prop. Metres.
ARCHITRAVE = dict(width=0.15, proud=0.1, head=0.2)      # beyond the fits edge; the head over the jambs
PORTAL = dict(pilaster=0.35, pilaster_proud=0.15, plinth=0.55, capital=0.2, cap_proud=0.2, cap_over=0.05,
              lintel=0.35, lintel_proud=0.25, lintel_over=0.1, light_inset=0.2, light_t=0.02)
FRAME_KINDS = ("architrave", "portal")


def door_fits(clear_w, clear_h):
    """The opening a framed door is carved at: its clear opening plus REVEAL at each jamb and at the head."""
    return clear_w + 2 * REVEAL, clear_h + REVEAL


def door_frame(clear_w, clear_h, wall_t, out="architrave", inside="architrave", step=0.02,
               mat="tech_panel", light="light_panel"):
    """The boxes of a framed doorway, in the door's own frame: u along the wall from the
    opening's middle, v through the wall from its outside face (0) to its inside face (wall_t),
    z up from the floor. `out` and `inside` say what stands on each face: "architrave", "portal"
    (an entrance: plinths, pilasters, capitals and a lintel with a downlight strip) or None (the
    face is against solid, or isn't built). `step` is the threshold plate's height, the level's
    underfoot step.

    Returns dicts {"lo": (u, v, z), "hi": (u, v, z), "mat", "part", "buried"}: "buried" names
    the box's faces ("-u", "+u", "-v", "+v", "-z", "+z") pressed against the carved wall, the
    floor or another part of the frame, which a mesh can leave out. Faces pressed back to back
    are allowed (CLAUDE.md 7.2); no two faces share a plane facing the same way where they
    overlap, which assert_no_zfighting checks for the level."""
    for face, kind in (("out", out), ("inside", inside)):
        if kind is not None and kind not in FRAME_KINDS:
            raise ValueError(f"door_frame: {face} is {kind!r}, not one of {FRAME_KINDS} or None")
    cu = clear_w / 2
    fu, fh = cu + REVEAL, clear_h + REVEAL
    boxes = []

    def add(u0, u1, v0, v1, z0, z1, part, buried, m=mat):
        boxes.append({"lo": (u0, v0, z0), "hi": (u1, v1, z1), "mat": m, "part": part, "buried": set(buried)})

    # Where a face has a frame, it covers the liners' ends from the clear edge outward.
    ends = ({"-v"} if out else set()) | ({"+v"} if inside else set())
    for side in (-1, 1):
        lo, hi = sorted((side * cu, side * fu))
        add(lo, hi, 0.0, wall_t, 0.0, clear_h, "liner", {"+u" if side > 0 else "-u", "-z", "+z"} | ends)
    add(-fu, fu, 0.0, wall_t, clear_h, fh, "liner", {"-u", "+u", "+z"} | ends)
    add(-cu, cu, 0.0, wall_t, 0.0, step, "threshold", {"-u", "+u", "-z"})
    for kind, sign in ((out, -1), (inside, 1)):
        if kind is None:
            continue
        back = "+v" if sign < 0 else "-v"

        def V(proud):
            return (-proud, 0.0) if sign < 0 else (wall_t, wall_t + proud)
        if kind == "architrave":
            a = ARCHITRAVE
            for side in (-1, 1):
                lo, hi = sorted((side * cu, side * (fu + a["width"])))
                add(lo, hi, *V(a["proud"]), 0.0, clear_h, "architrave", {back, "-z", "+z"})
            add(-(fu + a["width"]), fu + a["width"], *V(a["proud"]), clear_h, fh + a["head"], "architrave", {back})
            continue
        q = PORTAL
        outer = fu + q["pilaster"]
        for side in (-1, 1):
            lo, hi = sorted((side * cu, side * (outer + q["cap_over"])))
            add(lo, hi, *V(q["cap_proud"]), 0.0, q["plinth"], "plinth", {back, "-z"})
            lo, hi = sorted((side * cu, side * outer))
            add(lo, hi, *V(q["pilaster_proud"]), q["plinth"], clear_h - q["capital"], "pilaster", {back, "-z", "+z"})
            lo, hi = sorted((side * cu, side * (outer + q["cap_over"])))
            add(lo, hi, *V(q["cap_proud"]), clear_h - q["capital"], clear_h, "capital", {back, "+z"})
        span = outer + q["cap_over"] + q["lintel_over"]
        add(-span, span, *V(q["lintel_proud"]), clear_h, clear_h + q["lintel"], "lintel", {back})
        v0, v1 = V(q["lintel_proud"])
        mid, half = (v0 + v1) / 2, (q["lintel_proud"] - 2 * 0.04) / 2
        add(-(cu - q["light_inset"]), cu - q["light_inset"], mid - half, mid + half, clear_h - q["light_t"], clear_h,
            "downlight", {"+z"}, light)
    return boxes


# A public entrance's sliding door (openspec/changes/hub-doorways, design section 3.3; owner K2):
# two leaves, each half the clear width plus half LEAF_OVERLAP, so they overlap when shut, hanging
# on the building's inside face at LEAF_OFF_M (the two leaves' faces nearest the wall; they pass in
# front of the inside architrave, ARCHITRAVE["proud"]) and sliding apart by their own width. The
# catalogue is every size and face the kit builds; the prop kit, the scene generator and the plan
# all read it, and the plan refuses an entrance it lacks.
LEAF_T_M = 0.05
LEAF_OVERLAP_M = 0.1
LEAF_OFF_M = (0.15, 0.21)
LEAF_OVER_HEAD_M = 0.05
SLIDING_FACES = ("glazed", "steel", "hazard")
SLIDING_LEAVES = ((2.0, 2.4, "steel"), (2.5, 3.0, "glazed"), (3.0, 3.0, "glazed"), (4.0, 3.0, "glazed"),
                  (4.0, 3.0, "steel"), (5.0, 3.0, "hazard"))


def sliding_leaf(clear_w, clear_h):
    """One leaf of a sliding entrance: {"w", "h", "t"} metres."""
    return {"w": clear_w / 2 + LEAF_OVERLAP_M / 2, "h": clear_h + LEAF_OVER_HEAD_M, "t": LEAF_T_M}


def sliding_tag(clear_w, clear_h, face):
    """The catalogue name of a sliding entrance: "glazed_300x300"."""
    return f"{face}_{round(clear_w * 100)}x{round(clear_h * 100)}"


def sliding_sweep(clear_w, clear_h):
    """Where the two leaves stand when open, in the door's frame on the inside face: (u0, u1, v0,
    v1, z0, z1) per leaf, u along the wall from the opening's middle, v into the room, z up."""
    leaf = sliding_leaf(clear_w, clear_h)
    cu = clear_w / 2
    v0, v1 = LEAF_OFF_M[0], LEAF_OFF_M[1] + leaf["t"]
    return [(-(cu + leaf["w"]), -cu, v0, v1, 0.0, leaf["h"]), (cu, cu + leaf["w"], v0, v1, 0.0, leaf["h"])]


def frame_top(clear_h, kind):
    """The top of a frame over its opening, metres above the floor: a sign starts above it."""
    return clear_h + PORTAL["lintel"] if kind == "portal" else clear_h + REVEAL + ARCHITRAVE["head"]


def frame_triangles(boxes):
    """Triangles a frame's boxes draw with their buried faces left out: two per visible face."""
    return sum(2 * (6 - len(b["buried"])) for b in boxes)


def frame_outer_width(clear_w, kind):
    """How wide a frame stands on a wall face, metres: what a wall needs beside the opening."""
    fu = clear_w / 2 + REVEAL
    if kind == "portal":
        return 2 * (fu + PORTAL["pilaster"] + PORTAL["cap_over"] + PORTAL["lintel_over"])
    return 2 * (fu + ARCHITRAVE["width"])


# ----------------------------------------------------------------------------- z-fighting check

PLANE_TOL = 0.005   # faces closer than 5 mm to each other's plane count as coplanar


def _rect_overlap(r, q, eps=1e-4):
    return all(min(r[i][1], q[i][1]) - max(r[i][0], q[i][0]) > eps for i in range(2))


def _rect_sub(r, q):
    if not _rect_overlap(r, q, 0.0):
        return [r]
    (u0, u1), (v0, v1) = r
    (a0, a1), (b0, b1) = q
    out = []
    if a0 > u0:
        out.append(((u0, a0), (v0, v1)))
    if a1 < u1:
        out.append(((a1, u1), (v0, v1)))
    cu = (max(u0, a0), min(u1, a1))
    if b0 > v0:
        out.append((cu, (v0, b0)))
    if b1 < v1:
        out.append((cu, (b1, v1)))
    return out


def _box_faces(lo, hi, label, inward=False):
    faces = []
    for a in range(3):
        u, v = [i for i in range(3) if i != a]
        rect = ((lo[u], hi[u]), (lo[v], hi[v]))
        faces.append((a, lo[a], 1 if inward else -1, rect, label))
        faces.append((a, hi[a], -1 if inward else 1, rect, label))
    return faces


def _air_faces(airs):
    """Exposed inner faces of the air volumes (openings into other volumes cut out)."""
    boxes = [((a.x[0], a.y[0], a.z[0]), (a.x[1], a.y[1], a.z[1]), a.name) for a in airs]
    out = []
    for i, (lo, hi, name) in enumerate(boxes):
        for a, c, n, rect, label in _box_faces(lo, hi, f"air {name}", inward=True):
            u, v = [k for k in range(3) if k != a]
            rects = [rect]
            for j, (blo, bhi, _) in enumerate(boxes):
                if j == i:
                    continue
                outside = blo[a] < c - 1e-3 if n > 0 else bhi[a] > c + 1e-3
                if outside and blo[a] <= c + 1e-3 and bhi[a] >= c - 1e-3:
                    q = ((blo[u], bhi[u]), (blo[v], bhi[v]))
                    rects = [piece for r in rects for piece in _rect_sub(r, q)]
            out += [(a, c, n, r, label) for r in rects if (r[0][1] - r[0][0]) > 1e-3 and (r[1][1] - r[1][0]) > 1e-3]
    return out


def zfight_report(airs, details=(), props=(), merged=False):
    """Find pairs of faces that share a plane, face the same way and overlap: they z-fight.

    airs:    Room-like air volumes (their exposed inner faces are the walls, floors, ceilings)
    details: (lo, hi, label) solid boxes that stay separate surfaces (trims, detail brushes)
    props:   (lo, hi, label) solid boxes of separately rendered props (frame_solids())
    merged:  the details are CSG-unioned with the walls (Godot CSG), so detail-vs-detail and
             detail-vs-wall overlaps are resolved by the boolean and only props are checked.
    Returns a list of human-readable conflicts (empty = clean)."""
    walls_ = _air_faces(airs)
    hidden = {(f[0], round(f[1], 3), -f[2]) for f in walls_}   # detail faces pressed against a wall

    def solid_faces(boxes):
        fs = []
        for lo, hi, label in boxes:
            fs += [f for f in _box_faces(lo, hi, label) if (f[0], round(f[1], 3), f[2]) not in hidden]
        return fs

    det, prp = solid_faces(details), solid_faces(props)
    groups = [(prp, walls_), (prp, det), (prp, prp)]
    if not merged:
        groups += [(det, walls_), (det, det)]
    conflicts = set()
    for A, B in groups:
        for i, fa in enumerate(A):
            for j, fb in enumerate(B):
                if A is B and j <= i:
                    continue
                if fa[4] == fb[4] or fa[0] != fb[0] or fa[2] != fb[2] or abs(fa[1] - fb[1]) > PLANE_TOL:
                    continue
                if _rect_overlap(fa[3], fb[3], 1e-3):
                    axis = "xyz"[fa[0]]
                    conflicts.add(f"{fa[4]} / {fb[4]}: coplanar {'+' if fa[2] > 0 else '-'}{axis} faces at "
                                  f"{axis}={fa[1]:.3f}")
    return sorted(conflicts)


def assert_no_zfighting(level, airs, details=(), props=(), merged=False):
    conflicts = zfight_report(airs, details, props, merged)
    if conflicts:
        raise SystemExit(f"[{level}] z-fighting: {len(conflicts)} coplanar overlapping face pairs\n  "
                         + "\n  ".join(conflicts[:40]))
    print(f"[{level}] z-fighting check: clean ({len(airs)} air volumes, {len(details)} detail boxes, "
          f"{len(props)} prop boxes)")

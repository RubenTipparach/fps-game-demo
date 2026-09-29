"""Meridian's towers around the hub (openspec/changes/archive/2026-09-29-hub-skyline): each tower's massing as boxes,
and the four rules the plan asserts on the layout's "skyline" list.

It lives beside city_plan.py because the plan builds the skyline sector from it and the map's
locator inset draws the same footprints (CLAUDE.md 7.1: one layout source). Pure Python: the
layout's towers in, boxes and problems out.

Coordinates are layout metres (x east, y south) and heights metres up; a box is
((x0, y0, z0), (x1, y1, z1), part). Bearings in messages are compass degrees from the hub's
centre, 0 north and 90 east.

Every box is drawn by one material, MATERIAL (shaders/skyline_tower.gdshader), so the skyline
costs a draw call per ring. What a face is rides in its vertex colour (vertex_color): red the
tower's lit share, green its window seed, blue a code for the part and the tower's neon role.
"""
import math
import zlib

from shapely.geometry import box as rect

BOUNDS_M = 25.0         # every footprint stands at least this far outside the hub's rectangle
EYE_M = 1.6             # the coverage rule looks from the hub's centre at eye height
SECTOR_DEG = 30         # ... in slices of the horizon this wide
MIN_ELEVATION_DEG = 25.0  # ... each of which holds a tower whose top rises at least this far
MAX_TRIANGLES = 30000   # the skyline's budget
TRIS_PER_BOX = 12

MATERIAL = "skyline"
# The parts, in the order of their codes; the shader reads the same numbers.
FACADE, NEON, BEACON, BILLBOARD = "facade", "neon", "beacon", "billboard"
PARTS = (FACADE, NEON, BEACON, BILLBOARD)
# The neon roles a tower may name, in the order of the shader's palette. Their colours are the
# colour roles of data/character_lighting.json (tools/godot/gen_skyline_materials.py).
NEON_ROLES = ("cyan", "magenta", "amber", "blue", "violet", "ember", "sodium", "deck_glow")
CODE_SCALE = 32.0       # blue = (part * 8 + neon role) / 32: steps of 1/32 survive 8-bit colour
NEON_PROUD_M = 0.3      # a crown's band stands off the facade (over 1 cm: no z-fighting, CLAUDE.md 7.2)


def neon_role(tower):
    return tower.get("neon", "cyan")


def vertex_color(tower, part):
    """The colour a box of this tower's part carries: (lit share, seed, part and neon code)."""
    code = PARTS.index(part) * len(NEON_ROLES) + NEON_ROLES.index(neon_role(tower))
    return [float(tower.get("lit", 0.3)), seed(tower["id"]), code / CODE_SCALE]


def parts(tower):
    """The tower's blocks: a cluster's parts, or the tower itself; each (x0, y0, x1, y1, height)."""
    for p in tower.get("parts", [tower]):
        (x, y), (w, d) = p["at"], p["size"]
        yield x - w / 2, y - d / 2, x + w / 2, y + d / 2, p["height_m"]


def _scaled(x0, y0, x1, y1, k):
    cx, cy, hw, hd = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 * k, (y1 - y0) / 2 * k
    return cx - hw, cy - hd, cx + hw, cy + hd


def _tiers(tower, h):
    """(scale, top) per tier, bottom up, by style."""
    style = tower["style"]
    if style == "spire":
        cuts = tower.get("setbacks_m") or [0.3 * h, 0.6 * h, 0.85 * h]
        scales = [1.0, 0.75, 0.55, 0.35]
        tops = list(cuts) + [0.92 * h]
        return list(zip(scales, tops)) + [(0.12, h)]      # the needle
    if style == "arcology":
        return [(1.0 - 0.2 * i, h * (i + 1) / 4) for i in range(4)]
    if style == "corporate":
        return [(1.0, 0.7 * h), (0.8, h)]
    if style == "civic":
        return [(1.0, 0.2 * h), (0.65, h)]
    return [(1.0, h)]                                       # slab, and each part of a cluster


def massing(tower, hub_centre):
    """The tower's boxes: its tiers of facade, then its crown."""
    boxes = []
    shape = {"style": "slab"} if "parts" in tower else tower    # a cluster's parts are slabs
    for x0, y0, x1, y1, h in parts(tower):
        z, k = 0.0, 1.0
        for k, top in _tiers(shape, h):
            bx0, by0, bx1, by1 = _scaled(x0, y0, x1, y1, k)
            boxes.append(((bx0, by0, z), (bx1, by1, top), FACADE))
            z = top
        boxes += _crown(tower, _scaled(x0, y0, x1, y1, k), z, hub_centre)
    return boxes


def _crown(tower, top_rect, h, hub_centre):
    x0, y0, x1, y1 = top_rect
    crown, out = tower.get("crown"), []
    if crown == "neon":
        p = NEON_PROUD_M
        out.append(((x0 - p, y0 - p, h - 6.0), (x1 + p, y1 + p, h - 4.5), NEON))
    elif crown == "halo":
        # a square ring 3 m out from the needle's base, 1 m tall
        r, t = 3.0, 1.2
        for lo, hi in (((x0 - r, y0 - r), (x1 + r, y0 - r + t)), ((x0 - r, y1 + r - t), (x1 + r, y1 + r)),
                       ((x0 - r, y0 - r + t), (x0 - r + t, y1 + r - t)), ((x1 + r - t, y0 - r + t), (x1 + r, y1 + r - t))):
            out.append(((lo[0], lo[1], h * 0.97), (hi[0], hi[1], h * 0.97 + 1.0), NEON))
    elif crown == "billboard":
        # a holo panel on the face toward the hub, a quarter of the tower tall, 0.3 m off it
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = hub_centre[0] - cx, hub_centre[1] - cy
        z0, z1 = h * 0.55, h * 0.8
        if abs(dx) > abs(dy):
            fx = x1 if dx > 0 else x0
            s = 1 if dx > 0 else -1
            w = (y1 - y0) * 0.3
            out.append(((min(fx, fx + s * 0.6), cy - w, z0), (max(fx, fx + s * 0.6), cy + w, z1), BILLBOARD))
        else:
            fy = y1 if dy > 0 else y0
            s = 1 if dy > 0 else -1
            w = (x1 - x0) * 0.3
            out.append(((cx - w, min(fy, fy + s * 0.6), z0), (cx + w, max(fy, fy + s * 0.6), z1), BILLBOARD))
    if crown in ("beacons", "halo"):
        for bx, by in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            out.append(((bx - 0.6, by - 0.6, h), (bx + 0.6, by + 0.6, h + 1.2), BEACON))
    return out


LAMP_OFF_M = 1.5        # a searchlight's lamp stands this far off the face it is mounted on


def searchlights(tower):
    """The tower's searchlights as dicts: "at" (x, y, z) layout metres, "period_s", "phase_deg" and
    "tilt_deg". Each lamp stands LAMP_OFF_M off the named face of the tier at its height."""
    spec = tower.get("searchlights")
    if not spec:
        return []
    z = spec["height_m"]
    tier = next(((lo, hi) for lo, hi, part in massing(tower, (0.0, 0.0)) if part == FACADE and lo[2] <= z < hi[2]),
                None)
    if tier is None:
        raise ValueError(f"{tower['id']}: no tier at the searchlights' height {z:g} m")
    (x0, y0, _), (x1, y1, _) = tier
    cx, cy, o = (x0 + x1) / 2, (y0 + y1) / 2, LAMP_OFF_M
    at = {"west": (x0 - o, cy), "east": (x1 + o, cy), "north": (cx, y0 - o), "south": (cx, y1 + o)}
    return [{"at": (*at[b["face"]], z), "period_s": b["period_s"], "phase_deg": b["phase_deg"],
             "tilt_deg": tuple(spec["tilt_deg"])} for b in spec["beams"]]


def seed(tower_id):
    """A tower's seed for its windows, 0 to 1, from its id (stable across runs: CLAUDE.md 5.4)."""
    return (zlib.crc32(tower_id.encode()) % 1000) / 1000.0


def _bearing(cx, cy, x, y):
    return math.degrees(math.atan2(x - cx, -(y - cy))) % 360.0


def _arc(cx, cy, x0, y0, x1, y1):
    """The bearings a footprint spans from (cx, cy): (start, length), clockwise."""
    b = sorted(_bearing(cx, cy, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
    gaps = [((b[(i + 1) % 4] - b[i]) % 360.0, i) for i in range(4)]
    widest, i = max(gaps)
    return b[(i + 1) % 4], 360.0 - widest


def _overlaps(start, length, s0, s1):
    """True when the arc [start, start + length] meets the slice [s0, s1)."""
    for k in (-360.0, 0.0, 360.0):
        a0, a1 = start + k, start + length + k
        if a0 < s1 and a1 > s0:
            return True
    return False


def problems(towers, width, height):
    """What breaks the four rules, as messages naming the tower or the slice of the horizon; and
    a neon role the shader's palette doesn't hold."""
    out = [f"skyline: {t['id']} names neon {neon_role(t)!r}, not one of {', '.join(NEON_ROLES)}"
           for t in towers if neon_role(t) not in NEON_ROLES]
    hub = rect(0, 0, width, height)
    cx, cy = width / 2, height / 2
    for t in towers:
        try:
            searchlights(t)
        except ValueError as e:
            out.append(f"skyline: {e}")
    blocks = [(t["id"], b) for t in towers for b in parts(t)]
    for tid, (x0, y0, x1, y1, _) in blocks:
        d = hub.distance(rect(x0, y0, x1, y1))
        if d < BOUNDS_M - 1e-9:
            out.append(f"skyline: {tid} stands {d:.1f} m from the hub's edge (at least {BOUNDS_M:g})")
    for i, (ta, a) in enumerate(blocks):
        for tb, b in blocks[i + 1:]:
            if ta != tb and rect(*a[:4]).intersection(rect(*b[:4])).area > 0:
                out.append(f"skyline: {ta} overlaps {tb}")
    for s0 in range(0, 360, SECTOR_DEG):
        best = 0.0
        for _, (x0, y0, x1, y1, h) in blocks:
            start, length = _arc(cx, cy, x0, y0, x1, y1)
            if _overlaps(start, length, s0, s0 + SECTOR_DEG):
                near = rect(x0, y0, x1, y1).distance(rect(cx, cy, cx, cy))
                best = max(best, math.degrees(math.atan2(h - EYE_M, max(near, 1e-6))))
        if best < MIN_ELEVATION_DEG:
            out.append(f"skyline: bearings {s0}-{s0 + SECTOR_DEG} have no tower {MIN_ELEVATION_DEG:g} degrees up "
                       f"(the highest reaches {best:.1f})")
    tris = sum(TRIS_PER_BOX * len(massing(t, (cx, cy))) for t in towers)
    if tris > MAX_TRIANGLES:
        out.append(f"skyline: {tris} triangles (budget {MAX_TRIANGLES})")
    return out


def triangles(towers, width, height):
    """The skyline's triangle count, as the budget rule counts it."""
    return sum(TRIS_PER_BOX * len(massing(t, (width / 2, height / 2))) for t in towers)

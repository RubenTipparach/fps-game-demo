#!/usr/bin/env python3
"""E1M2 "Slag Works" - generates a Quake/TrenchBroom .map (Valve 220 format).

This produces an ordinary TrenchBroom map: open game/levels/trenchbroom/slag_works.map in
TrenchBroom (with the Brushfire game config) and keep editing it by hand. The generator only
exists so the starting layout is reproducible; once you edit the map in TrenchBroom, stop
running it (it would overwrite your changes).

How the brushwork is made: rooms are described as "air" boxes. The space around them is split
on a rectilinear grid, every solid cell touching air becomes a brush, and adjacent cells are
greedily merged into bigger brushes. Faces that touch air get the room's wall/floor/ceiling
texture; faces buried in rock get "skip" (removed from the mesh by func_godot), so no
lightmap space is wasted on geometry nobody can see. Detail brushes (stairs, pillars,
ramps, crates, bridges) are added on top as regular brushes.

Coordinates below are Godot metres (x right, y up, -z north); they are converted to Quake
units (32 per metre, x/y/z swizzled) on output.

    python3 tools/trenchbroom/gen_map.py
"""
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.path.join(ROOT, "game")
SCALE = 32.0
TEX_PX = 1024.0

sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
import detailing  # noqa: E402

TILES = {k: v.get("tile_m", 2.0) for k, v in json.load(open(os.path.join(GAME, "materials", "materials.json"))).items()
         if isinstance(v, dict)}


def q(p):
    """Godot metres (x, y, z) -> Quake units (x_q, y_q, z_q)."""
    x, y, z = p
    return (z * SCALE, x * SCALE, y * SCALE)


def sub(a, b):
    return tuple(i - j for i, j in zip(a, b))


def add(a, b):
    return tuple(i + j for i, j in zip(a, b))


def mul(a, s):
    return tuple(i * s for i in a)


def dot(a, b):
    return sum(i * j for i, j in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    l = math.sqrt(dot(a, a))
    return tuple(i / l for i in a)


# ----------------------------------------------------------------------------- brush output

def num(v):
    r = round(v, 6)
    if abs(r - round(r)) < 1e-6:
        return str(int(round(r)))
    return f"{r:.6f}".rstrip("0").rstrip(".")


def face_line(n_q, d_q, tex):
    """A plane (outward normal n, distance d, Quake space) as a Valve 220 face line."""
    p1 = mul(n_q, d_q)
    # two tangents so that (p0 - p1) x (p2 - p1) points along n (outward)
    ref = (0, 0, 1) if abs(n_q[2]) < 0.9 else (1, 0, 0)
    t1 = norm(cross(ref, n_q))
    t2 = norm(cross(n_q, t1))
    L = 64.0
    p0 = add(p1, mul(t1, L))
    p2 = add(p1, mul(t2, L))
    # ensure winding: (p0-p1) x (p2-p1) = t1 x t2 = n
    if dot(cross(sub(p0, p1), sub(p2, p1)), n_q) < 0:
        p0, p2 = p2, p0
    # Paraxial (TrenchBroom default) texture axes.
    ax = [abs(c) for c in n_q]
    if ax[2] >= ax[0] and ax[2] >= ax[1]:
        u, v = (1, 0, 0), (0, -1, 0)
    elif ax[0] >= ax[1]:
        u, v = (0, 1, 0), (0, 0, -1)
    else:
        u, v = (1, 0, 0), (0, 0, -1)
    scale = TILES.get(tex, 2.0) * SCALE / TEX_PX
    pts = " ".join(f"( {num(p[0])} {num(p[1])} {num(p[2])} )" for p in (p0, p1, p2))
    return (f"{pts} {tex} [ {u[0]} {u[1]} {u[2]} 0 ] [ {v[0]} {v[1]} {v[2]} 0 ] 0 "
            f"{num(scale)} {num(scale)}")


class Brush:
    def __init__(self, planes):
        self.planes = planes   # list of (normal_godot, point_on_plane_godot, texture)

    def lines(self):
        out = []
        for n, p, tex in self.planes:
            nq = norm(q(n))
            dq = dot(nq, q(p))
            out.append(face_line(nq, dq, tex))
        return out


DIRS = {"-x": (-1, 0, 0), "+x": (1, 0, 0), "-y": (0, -1, 0), "+y": (0, 1, 0), "-z": (0, 0, -1), "+z": (0, 0, 1)}


def box_brush(lo, hi, tex):
    """tex: a texture name, or dict with keys -x +x -y +y -z +z (missing -> 'default')."""
    if isinstance(tex, str):
        tex = {k: tex for k in DIRS}
    planes = []
    for k, n in DIRS.items():
        p = hi if sum(n) > 0 else lo
        planes.append((n, p, tex.get(k, tex.get("default", "skip"))))
    return Brush(planes)


def hull_brush(points, tex_fn):
    """Convex hull of points -> brush; tex_fn(normal) picks the texture per face."""
    planes = []
    for a, b, c in itertools.combinations(points, 3):
        n = cross(sub(b, a), sub(c, a))
        if dot(n, n) < 1e-9:
            continue
        n = norm(n)
        d = dot(n, a)
        side = [dot(n, p) - d for p in points]
        if all(s <= 1e-6 for s in side):
            pass
        elif all(s >= -1e-6 for s in side):
            n, d = mul(n, -1), -d
        else:
            continue
        if any(abs(dot(n, m) - 1) < 1e-6 and abs(dot(m, pp) - dot(n, a)) < 1e-4 for m, pp, _ in planes):
            continue
        planes.append((n, a, tex_fn(n)))
    return Brush(planes)


def prism_brush(cx, cz, radius, y0, y1, sides, side_tex, top_tex=None, bottom_tex="skip", rot=0.0):
    pts = []
    for i in range(sides):
        a = rot + i / sides * 2 * math.pi
        x, z = cx + math.cos(a) * radius, cz + math.sin(a) * radius
        pts += [(x, y0, z), (x, y1, z)]
    top_tex = top_tex or side_tex

    def tex(n):
        if n[1] > 0.9:
            return top_tex
        if n[1] < -0.9:
            return bottom_tex
        return side_tex
    return hull_brush(pts, tex)


def ramp_brush(x0, x1, z_low, z_high, y0, y_top, top_tex, side_tex):
    """Wedge rising from y0 at z_low to y_top at z_high (z_low/z_high in either order)."""
    pts = [(x, y0, z) for x in (x0, x1) for z in (z_low, z_high)] + [(x, y_top, z_high) for x in (x0, x1)]

    def tex(n):
        if n[1] > 0.2:
            return top_tex
        if n[1] < -0.9:
            return "skip"
        return side_tex
    return hull_brush(pts, tex)


# ----------------------------------------------------------------------------- room shell generator

STYLE = {"tech_panel": "tech", "concrete": "tech", "rust_metal": "tech", "brick_wall": "brick", "stone_blocks": "stone"}


class Air:
    def __init__(self, lo, hi, floor, wall, ceiling, trims=True):
        self.lo, self.hi = lo, hi
        self.tex = {"floor": floor, "wall": wall, "ceiling": ceiling}
        self.trims = trims

    def room(self):
        return detailing.Room("air", (self.lo[0], self.hi[0]), (self.lo[1], self.hi[1]), (self.lo[2], self.hi[2]),
                              STYLE.get(self.tex["wall"], "tech"), self.trims, ceiling=self.tex["ceiling"])


def shell_brushes(airs, pad=1.0):
    xs, ys, zs = set(), set(), set()
    for a in airs:
        for i, s in enumerate((xs, ys, zs)):
            s.add(a.lo[i])
            s.add(a.hi[i])
    lo = [min(s) - pad for s in (xs, ys, zs)]
    hi = [max(s) + pad for s in (xs, ys, zs)]
    xs.update([lo[0], hi[0]]); ys.update([lo[1], hi[1]]); zs.update([lo[2], hi[2]])
    X, Y, Z = sorted(xs), sorted(ys), sorted(zs)
    nx, ny, nz = len(X) - 1, len(Y) - 1, len(Z) - 1

    owner = {}
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                c = ((X[i] + X[i + 1]) / 2, (Y[j] + Y[j + 1]) / 2, (Z[k] + Z[k + 1]) / 2)
                for idx, a in enumerate(airs):
                    if all(a.lo[t] < c[t] < a.hi[t] for t in range(3)):
                        owner[(i, j, k)] = idx
                        break

    def is_air(i, j, k):
        return (i, j, k) in owner

    def face_tex(i, j, k, d):
        """Texture for the face of solid cell (i,j,k) in direction d, looking into a neighbour."""
        di, dj, dk = DIRS[d]
        nb = (i + di, j + dj, k + dk)
        if nb not in owner:
            return "skip"
        a = airs[owner[nb]]
        if d == "+y":
            return a.tex["floor"]
        if d == "-y":
            return a.tex["ceiling"]
        return a.tex["wall"]

    solid = set()
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                if is_air(i, j, k):
                    continue
                if any(is_air(i + di, j + dj, k + dk) for di, dj, dk in DIRS.values()):
                    solid.add((i, j, k))

    sig = {c: tuple(face_tex(*c, d) for d in DIRS) for c in solid}
    used = set()
    brushes = []
    for c in sorted(solid, key=lambda t: (t[1], t[2], t[0])):
        if c in used:
            continue
        i0, j0, k0 = c
        s0 = sig[c]
        # grow along x (only faces facing the growth axis may differ at the ends: require equal sig)
        i1 = i0
        while (i1 + 1, j0, k0) in solid and (i1 + 1, j0, k0) not in used and sig[(i1 + 1, j0, k0)] == s0:
            i1 += 1
        k1 = k0
        while all((i, j0, k1 + 1) in solid and (i, j0, k1 + 1) not in used and sig[(i, j0, k1 + 1)] == s0
                  for i in range(i0, i1 + 1)):
            k1 += 1
        j1 = j0
        while all((i, j1 + 1, k) in solid and (i, j1 + 1, k) not in used and sig[(i, j1 + 1, k)] == s0
                  for i in range(i0, i1 + 1) for k in range(k0, k1 + 1)):
            j1 += 1
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                for k in range(k0, k1 + 1):
                    used.add((i, j, k))
        lo_p = (X[i0], Y[j0], Z[k0])
        hi_p = (X[i1 + 1], Y[j1 + 1], Z[k1 + 1])
        brushes.append(box_brush(lo_p, hi_p, dict(zip(DIRS.keys(), s0))))
    return brushes


# ----------------------------------------------------------------------------- the level

def air_volumes():
    """The level's rooms as air volumes (also read by gen_level_scene.py for zone ambient)."""
    A = Air
    return [
        A((-5, 0, 36), (5, 4, 46), "concrete", "stone_blocks", "ceiling_tiles"),          # start
        A((-2, 0, 24.5), (2, 4, 36), "diamond_plate", "brick_wall", "ceiling_tiles"),      # corridor
        A((-1.5, 0, 24), (1.5, 3.2, 24.5), "diamond_plate", "tech_panel", "tech_panel", trims=False),   # door 1
        A((-16, 0, -8), (16, 12, 24), "concrete", "stone_blocks", "rust_metal"),           # foundry hall
        A((-16, -0.9, 4), (16, 0, 10), "lava", "stone_blocks", "stone_blocks", trims=False),            # lava channel
        A((-16.4, 0, 16), (-16, 3.5, 20), "concrete", "tech_panel", "tech_panel", trims=False),         # west arch
        A((-30, 0, 10), (-16.4, 6, 26), "floor_tiles", "brick_wall", "ceiling_tiles"),     # crucible
        A((-33, 0, 17), (-30, 3, 19), "stone_blocks", "stone_blocks", "stone_blocks", trims=False),     # secret niche
        A((-1.5, 4, -8.4), (1.5, 7.2, -8), "diamond_plate", "tech_panel", "tech_panel", trims=False),   # door 2
        A((-2, 4, -20), (2, 8, -8.4), "diamond_plate", "brick_wall", "ceiling_tiles"),     # exit corridor
        A((-6, 4, -32), (6, 10, -20), "floor_tiles", "tech_panel", "ceiling_tiles"),       # exit room
        # smoke vent in the foundry roof, capped by a Quake-style sky face (UT99 checklist 6)
        A((-8, 12, 3.2), (8, 14.5, 7.6), "rust_metal", "rust_metal", "sky_storm", trims=False),
    ]


# Light fixtures (Godot metres). Ceiling lights sit in the bays between the roof girders.
CEILING_LIGHTS = [(0, 3.95, 39), (0, 3.95, 43.5),
                  (-8, 11.95, 16), (8, 11.95, 16), (-8, 11.95, 0), (8, 11.95, 0), (0, 11.95, 10.67),
                  (-26, 5.95, 14), (-20, 5.95, 22), (-3, 9.95, -26), (3, 9.95, -26)]
WALL_LIGHTS = [((-1.95, 3.0, 30), -90), ((1.95, 3.0, 30), 90), ((-2.67, 7.5, -7.95), 180), ((2.67, 7.5, -7.95), 180),
               ((-8, 7.5, -7.95), 180), ((8, 7.5, -7.95), 180), ((-1.95, 6.8, -14), -90), ((1.95, 6.8, -14), 90),
               ((-15.95, 4.0, 18), -90), ((-31.5, 2.4, 18.95), 0)]


def build():
    airs = air_volumes()
    world = shell_brushes(airs)
    # UT99-style trims (baseboards, cornices, bands, pilasters with plinths and capitals, roof
    # girders) as detail brushes; see docs/ut99_reference.md.
    rooms = [a.room() for a in airs]
    keep_out = [detailing.keep_out(p, (0.8, 0.3, 0.45)) for p in CEILING_LIGHTS]
    keep_out += [detailing.keep_out(p, (0.3, 0.35, 0.3)) for p, _ in WALL_LIGHTS]
    for lo, hi, tex in detailing.all_trims(rooms, avoid=keep_out):
        world.append(box_brush(lo, hi, tex))

    def box(lo, hi, tex, bottom="skip"):
        t = {k: tex for k in DIRS}
        t["-y"] = bottom
        world.append(box_brush(lo, hi, t))

    # gallery block along the north wall of the hall, ramp up from the west
    world.append(box_brush((-16, 0, -8), (16, 4, -3),
                           {"+y": "diamond_plate", "+z": "tech_panel", "-y": "skip", "-z": "skip", "-x": "skip", "+x": "skip"}))
    box((-13, 4, -3.3), (11.5, 4.9, -3), "hazard_stripes", "hazard_stripes")      # gallery parapet (gaps at ramp + jump pad)
    world.append(ramp_brush(-16, -13, 3, -3, 0, 4, "diamond_plate", "stone_blocks"))
    # jump pad base on the east side
    box((12, 0, -2.2), (14.4, 0.2, 0.2), "hazard_stripes")
    # bridges over the lava
    for x0, x1 in ((-10, -7), (5, 8)):
        box((x0, -0.3, 3.8), (x1, 0, 10.2), "diamond_plate", "rust_metal")
        box((x0, 0, 3.8), (x0 + 0.25, 0.6, 10.2), "rust_metal")
        box((x1 - 0.25, 0, 3.8), (x1, 0.6, 10.2), "rust_metal")
    # channel curbs
    box((-16, 0, 3.6), (-10, 0.25, 4), "hazard_stripes")
    box((-7, 0, 3.6), (5, 0.25, 4), "hazard_stripes")
    box((8, 0, 3.6), (16, 0.25, 4), "hazard_stripes")
    box((-16, 0, 10), (-10, 0.25, 10.4), "hazard_stripes")
    box((-7, 0, 10), (5, 0.25, 10.4), "hazard_stripes")
    box((8, 0, 10), (16, 0.25, 10.4), "hazard_stripes")
    # octagonal pillars with a base and a capital
    for x, z in ((-10, 14), (10, 14), (-10, 20), (10, 20)):
        world.append(prism_brush(x, z, 1.1, 0, 12, 8, "stone_blocks", "skip", "skip", rot=math.pi / 8))
        world.append(prism_brush(x, z, 1.35, 0, 0.6, 8, "tech_panel", "tech_panel", "skip", rot=math.pi / 8))
        world.append(prism_brush(x, z, 1.25, 0.6, 0.75, 8, "rust_metal", "rust_metal", "rust_metal", rot=math.pi / 8))
        world.append(prism_brush(x, z, 1.4, 11.3, 12, 8, "tech_panel", "skip", "tech_panel", rot=math.pi / 8))
    # smoke vent: frame and grate bars under the sky face
    box((-8.4, 11.75, 2.8), (8.4, 12, 3.2), "hazard_stripes", "hazard_stripes")
    box((-8.4, 11.75, 7.6), (8.4, 12, 8.0), "hazard_stripes", "hazard_stripes")
    box((-8.4, 11.75, 3.2), (-8, 12, 7.6), "hazard_stripes", "hazard_stripes")
    box((8, 11.75, 3.2), (8.4, 12, 7.6), "hazard_stripes", "hazard_stripes")
    for x in (-5.6, -2.8, 0, 2.8, 5.6):
        box((x - 0.1, 11.8, 3.2), (x + 0.1, 12, 7.6), "rust_metal", "rust_metal")
    # crucible: the vat, crates, a raised grate walkway
    world.append(prism_brush(-23, 18, 2.6, 0, 2.2, 8, "rust_metal", "lava", "skip", rot=math.pi / 8))
    world.append(prism_brush(-23, 18, 2.9, 0, 0.5, 8, "tech_panel", "tech_panel", "skip", rot=math.pi / 8))
    for lo, hi, t in (((-29, 0, 11), (-27, 2, 13), "crate"), ((-27, 0, 11), (-26, 1, 12), "crate"),
                      ((-19, 0, 24), (-17, 2, 26), "crate"), ((-20, 0, 25), (-19, 1, 26), "crate"),
                      ((-29.5, 0, 23), (-28.5, 1, 24), "crate")):
        box(lo, hi, t)
    # exit room dais and pillars (hexagonal shafts on plinths, with capitals)
    box((-2.5, 4, -30), (2.5, 4.3, -25), "hazard_stripes")
    for x, z in ((-4.8, -30.8), (4.8, -30.8), (-4.8, -21.2), (4.8, -21.2)):
        world.append(prism_brush(x, z, 0.6, 4, 10, 6, "tech_panel", "skip", "skip"))
        world.append(prism_brush(x, z, 0.82, 4, 4.5, 6, "stone_blocks", "stone_blocks", "skip"))
        world.append(prism_brush(x, z, 0.8, 9.5, 10, 6, "stone_blocks", "skip", "stone_blocks"))

    ents = []

    def ent(classname, pos=None, angle=None, **kv):
        e = {"classname": classname}
        if pos is not None:
            ox, oy, oz = q(pos)
            e["origin"] = f"{num(ox)} {num(oy)} {num(oz)}"
        if angle is not None:
            e["angle"] = num((angle - 180) % 360)  # our yaw (0 = facing -z) -> Quake angle
        e.update({k: str(v) for k, v in kv.items()})
        ents.append((e, []))

    def brush_ent(classname, brushes, **kv):
        e = {"classname": classname}
        e.update({k: str(v) for k, v in kv.items()})
        ents.append((e, brushes))

    ent("info_player_start", (0, 0.05, 42), 0)
    # doors
    # Split doors in framed doorways (Blender-made kit), framed archways for open passages.
    # Classic brush doors still work: make a brush, tie it to func_door (see the FGD).
    ent("misc_doorway", (0, 0, 24.25), 0)
    ent("misc_doorway", (0, 4, -8.2), 0)
    ent("misc_archway_4x4", (0, 0, 36), 0)
    ent("misc_archway_4x4", (0, 4, -20), 0)
    ent("misc_archway_4x35", (-16.2, 0, 18), 90)
    # lava damage, jump pad, secret, messages
    brush_ent("trigger_hurt", [box_brush((-16, -0.9, 4), (16, -0.5, 10), "trigger")], dmg=45)
    brush_ent("trigger_hurt", [box_brush((-25.6, 2.2, 15.4), (-20.4, 2.8, 20.6), "trigger")], dmg=60)
    brush_ent("trigger_push", [box_brush((12.1, 0.2, -2.1), (14.3, 1.2, 0.1), "trigger")], speed=480, angle=180)
    brush_ent("trigger_secret", [box_brush((-32.8, 0, 17.1), (-30.6, 2.8, 18.9), "trigger")])
    brush_ent("trigger_message", [box_brush((-2, 0, 30), (2, 3, 31), "trigger")],
              message="The lava is hot. Use the jump pad to reach the gallery.")
    # the fake wall hiding the secret niche
    brush_ent("func_illusionary", [box_brush((-30.35, 0, 17), (-30, 3, 19),
                                             {"+x": "brick_wall", "-x": "stone_blocks", "+y": "skip", "-y": "skip",
                                              "+z": "skip", "-z": "skip"})])

    # lights
    for p in CEILING_LIGHTS:
        ent("light_fixture", p)
    for p, yaw in WALL_LIGHTS:
        ent("light_wall", p, yaw)
    ent("light", (0, 13.6, 5.4), light=160, _color="255 96 40", range=14, shadows=1)   # furnace sky glow
    for x in (-12, -4, 4, 12):
        ent("light", (x, 0.6, 7), light=200, _color="255 110 40", range=9, shadows=0)
    ent("light", (-23, 3.2, 18), light=220, _color="255 120 50", range=8, shadows=0)

    # monsters
    for p, yaw, cls in (((0, 0, 27.5), 180, "grunt"),
                        ((-6, 0, 18), 180, "grunt"), ((6, 0, 16), 160, "grunt"), ((0, 0, 1), 180, "grunt"),
                        ((-6, 4, -5.5), 180, "grunt"), ((9, 4, -5.5), 200, "grunt"),
                        ((-4, 3.5, 7), 180, "drone"), ((6, 4.5, 12), 180, "drone"), ((-12, 0, 0.5), 150, "brute"),
                        ((-22, 0, 13), -90, "grunt"), ((-26, 0, 22), -120, "grunt"), ((-19, 0, 20.5), -90, "brute"),
                        ((-24, 4, 24), -90, "drone"),
                        ((0, 4, -17), 180, "grunt"), ((-3, 4, -29), 180, "brute"), ((3, 7, -24), 180, "drone")):
        ent(f"monster_{cls}", p, yaw)

    # items
    for p, cls in (((3, 0, 38), "item_shells"), ((-3, 0, 38), "item_armor"), ((0, 0, 32), "item_health"),
                   ((-8.5, 0, 12.5), "weapon_chaingun"), ((12, 0, 22), "item_bullets"), ((-14, 0, 22), "item_health"),
                   ((14, 0, 12), "item_shells"), ((0, 0, 2), "item_health"),
                   ((14, 4, -5.5), "weapon_rocketlauncher"), ((12, 4, -5.5), "item_rockets"), ((-14, 4, -5.5), "item_armor"),
                   ((-28, 0, 14.5), "item_bullets"), ((-18, 0, 12), "item_health"), ((-28, 2, 12), "item_rockets"),
                   ((-31.8, 0, 18), "item_megahealth"), ((0, 4, -12), "item_health"),
                   ((-4.5, 4, -23), "item_shells"), ((4.5, 4, -23), "item_bullets")):
        ent(cls, p)
    for p in ((-14, 0, 13), (-13.2, 0, 12.3), (13.5, 0, 16), (-18, 0, 17.5), (-17.4, 0, 18.4)):
        ent("misc_explobox", p)
    ent("info_exit", (0, 4.3, -27.5))
    return world, ents


def write_map(path):
    world, ents = build()
    lines = ["// Game: Brushfire", "// Format: Valve",
             "// Generated by tools/trenchbroom/gen_map.py - open and edit freely in TrenchBroom.",
             "// entity 0", "{", '"classname" "worldspawn"', '"mapversion" "220"', '"_cull_interior_faces" "1"']
    for bi, b in enumerate(world):
        lines.append(f"// brush {bi}")
        lines.append("{")
        lines += b.lines()
        lines.append("}")
    lines.append("}")
    for ei, (e, brushes) in enumerate(ents, 1):
        lines.append(f"// entity {ei}")
        lines.append("{")
        for k, v in e.items():
            lines.append(f'"{k}" "{v}"')
        for bi, b in enumerate(brushes):
            lines.append(f"// brush {bi}")
            lines.append("{")
            lines += b.lines()
            lines.append("}")
        lines.append("}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {path}: {len(world)} world brushes, {len(ents)} entities")


if __name__ == "__main__":
    write_map(os.path.join(GAME, "levels", "trenchbroom", "slag_works.map"))

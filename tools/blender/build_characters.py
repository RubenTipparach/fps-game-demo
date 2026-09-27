"""Undercity NPC characters: UT99-era segmented rigs, built from tools/blender/characters.json.

It owns the character models. CLAUDE.md 6.1 says models are .glb files built by a committed
Blender script, with the editable .blend committed too. Every row of the table becomes:
  - an armature with the shared 18-bone layout scaled to the row's proportions;
  - rigid low-poly segments (beveled boxes, 8- to 12-sided tapered prisms, joint caps), each its
    own object parented to exactly one bone (no weights);
  - outfit parts as extra segments;
  - flat PBR materials named by role;
  - the five looping clips of character_rig.py, keyed on the bones and exported as glTF
    animations named idle, walk, talk, guard and sit.
A new character is a new row, not new code. A new kind of outfit part is a new builder in PARTS
plus its parameters in character_data.PART_SCHEMAS.

Run:   blender -b --factory-startup -P tools/blender/build_characters.py [-- --only silk,mags]
Writes:
  game/models/characters/<id>.glb    one per character
  tools/blender/characters.blend     editable source with every character in a lineup (a partial
                                     run with --only leaves it alone)
Axes: Blender X = the character's left, -Y = its front, Z = up, feet at Z = 0. The export is +Y
up, so in glTF and in Godot a character faces +Z (Godot's Vector3.MODEL_FRONT).
Layered surfaces (hair over head, cloth over body, plates over cloth) sit at least
model.layer_gap_m apart, or the outer layer replaces the body segment it covers.
"""
import math
import os
import sys
import zlib

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_data  # noqa: E402
from blendkit import HERE, ROOT, collection, project_uvs, save_reproducible  # noqa: E402
from character_rig import BONES, CLIPS, SIGN, SOLE_MARGIN, Motion, Pose, Skeleton, apply_hold, fk  # noqa: E402

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
WORLD = (Vector((0, 0, 0)), X, Y, Z)
TRUNK_BONES = ("pelvis", "spine", "chest", "thigh_l", "thigh_r")


# ----------------------------------------------------------------------------- mesh primitives

def ring_pts(sides, rx, ry, power):
    """Superellipse ring (power 2 = ellipse, higher = boxier with chamfered corners). With an
    even number of sides divisible by 4 it has flat faces toward +-x and +-y."""
    e = 2.0 / power
    out = []
    for k in range(sides):
        a = 2.0 * math.pi * (k + 0.5) / sides
        c, s = math.cos(a), math.sin(a)
        out.append((rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s)))
    return out


def arc_pt(a, rx, ry, power):
    e = 2.0 / power
    c, s = math.cos(a), math.sin(a)
    return rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s)


def front_open(deg):
    """Arc limits (radians, 0 = +x, pi/2 = +y = back) for a C-shape open at the front."""
    o = math.radians(deg)
    return -math.pi / 2 + o / 2, 3 * math.pi / 2 - o / 2


def back_open(deg):
    o = math.radians(deg)
    return math.pi / 2 + o / 2, 5 * math.pi / 2 - o / 2


def at(fr, x, y, t):
    o, xa, ya, za = fr
    return o + xa * x + ya * y + za * t


def axis_frame(origin, za, up=Z):
    """Frame at origin whose t axis is za; x is the part of up x za that exists."""
    za = za.normalized()
    xa = up.cross(za)
    if xa.length < 1e-6:
        xa = X.copy()
    xa.normalize()
    return (origin.copy(), xa, za.cross(xa).normalized() * -1.0, za)


def bone_frame(sk, name):
    za, xa = sk.dir(name), sk.hinge(name)
    return (sk.head[name].copy(), xa, xa.cross(za), za)


class MB:
    """One segment: bmesh geometry in armature space, its bone and its material slots."""

    def __init__(self, name, bone):
        self.name, self.bone = name, bone
        self.bm = bmesh.new()
        self.mats = []

    def slot(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _face(self, verts, mat):
        f = self.bm.faces.new(verts)
        f.material_index = self.slot(mat)
        return f

    def loft(self, rings, fr, sides, power, mat, cap_mats=(None, None), caps=(True, True)):
        """Closed prism through rings (t, rx, ry[, cx, cy[, tilt]]) along the frame's t axis."""
        loops = []
        for r in rings:
            t, rx, ry = r[0], r[1], r[2]
            cx = r[3] if len(r) > 3 else 0.0
            cy = r[4] if len(r) > 4 else 0.0
            tt = math.tan(r[5]) if len(r) > 5 else 0.0
            loops.append([self.bm.verts.new(at(fr, cx + x, cy + y, t + tt * (cy + y)))
                          for x, y in ring_pts(sides, rx, ry, power)])
        for a, b in zip(loops, loops[1:]):
            for k in range(sides):
                self._face((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]), mat)
        if caps[0]:
            self._face(list(reversed(loops[0])), cap_mats[0] or mat)
        if caps[1]:
            self._face(loops[-1], cap_mats[1] or mat)

    def cshell(self, rings, fr, a0, a1, segs, thick, power, mat, edge=None, hem=None, top=None):
        """Thick partial shell: for each ring (t, rx, ry, cx, cy) an arc from a0 to a1 with an
        inner arc `thick` inside it. Closed solid; the arc ends take `edge`, the first ring's
        rim `hem` and the last ring's rim `top`."""
        outer, inner = [], []
        for t, rx, ry, cx, cy in rings:
            o_l, i_l = [], []
            for j in range(segs + 1):
                a = a0 + (a1 - a0) * j / segs
                ox, oy = arc_pt(a, rx, ry, power)
                ix, iy = arc_pt(a, rx - thick, ry - thick, power)
                o_l.append(self.bm.verts.new(at(fr, cx + ox, cy + oy, t)))
                i_l.append(self.bm.verts.new(at(fr, cx + ix, cy + iy, t)))
            outer.append(o_l)
            inner.append(i_l)
        for i in range(len(rings) - 1):
            for j in range(segs):
                self._face((outer[i][j], outer[i][j + 1], outer[i + 1][j + 1], outer[i + 1][j]), mat)
                self._face((inner[i][j + 1], inner[i][j], inner[i + 1][j], inner[i + 1][j + 1]), mat)
            self._face((outer[i][0], outer[i + 1][0], inner[i + 1][0], inner[i][0]), edge or mat)
            self._face((outer[i][segs], inner[i][segs], inner[i + 1][segs], outer[i + 1][segs]), edge or mat)
        for j in range(segs):
            self._face((outer[0][j], inner[0][j], inner[0][j + 1], outer[0][j + 1]), hem or mat)
            self._face((outer[-1][j + 1], inner[-1][j + 1], inner[-1][j], outer[-1][j]), top or mat)

    def hull(self, pts, mat):
        verts = [self.bm.verts.new(Vector(p)) for p in pts]
        res = bmesh.ops.convex_hull(self.bm, input=verts)
        m = self.slot(mat)
        for g in res["geom"]:
            if isinstance(g, bmesh.types.BMFace):
                g.material_index = m
        dead = []
        for g in res["geom_interior"] + res["geom_unused"]:
            if isinstance(g, bmesh.types.BMVert) and g not in dead:
                dead.append(g)
        if dead:
            bmesh.ops.delete(self.bm, geom=dead, context="VERTS")

    def box(self, fr, lo, hi, mat):
        """Box between frame coordinates lo and hi (x, y, t)."""
        self.hull([at(fr, x, y, t) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for t in (lo[2], hi[2])], mat)

    def tube(self, pts, radius, sides, power, mat, ref=Y):
        """Prism swept through points, cross-section perpendicular to the path."""
        loops = []
        for i, p in enumerate(pts):
            tan = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            xa = ref.cross(tan).normalized()
            ya = tan.cross(xa).normalized()
            r = radius[i] if isinstance(radius, (list, tuple)) else radius
            loops.append([self.bm.verts.new(p + xa * x + ya * y) for x, y in ring_pts(sides, r, r, power)])
        for a, b in zip(loops, loops[1:]):
            for k in range(sides):
                self._face((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]), mat)
        self._face(list(reversed(loops[0])), mat)
        self._face(loops[-1], mat)

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)


def interp(rings, z):
    """Linear interpolation in a list of tuples sorted by their first value."""
    if z <= rings[0][0]:
        return rings[0]
    for a, b in zip(rings, rings[1:]):
        if z <= b[0]:
            f = (z - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * f for i in range(len(a)))
    return rings[-1]


# ----------------------------------------------------------------------------- body

class Body:
    """Ring tables of one character in armature space (metres), from anatomy fractions, the
    row's build and fit, and the chest overhang its outfit needs."""

    def __init__(self, table, row, splay, chest_clear):
        A, H, b, fit = table["anatomy"], row["height_m"], row["build"], row["fit"]
        self.A, self.H, self.row = A, H, row
        self.sk = Skeleton(A, row, splay)
        g = b["girth"]

        def belly(z):
            return b["belly"] * 0.03 * H * max(0.0, 1.0 - abs(z - 0.6) / 0.09) / 2.0

        k = g * fit["bottom"]
        self.pelvis = [(z * H, hw * H * k * b["hips"], hd * H * k + belly(z), cy * H - belly(z))
                       for z, hw, hd, cy in A["pelvis_rings"]]
        k = g * fit["top"]
        self.torso = []
        for z, hw, hd, cy, w in A["torso_rings"]:
            wide = max(1.0, b["hips"]) * (1.0 - w) + b["shoulders"] * w
            self.torso.append((z * H, hw * H * k * wide, hd * H * k + belly(z), cy * H - belly(z)))
        # The chest's bottom edge overhangs the pelvis (and anything worn between them).
        z0, hw0, hd0, cy0 = self.torso[0]
        _, phw, phd, pcy = self.pelvis_at(z0)
        sw = max(1.0, (phw + chest_clear) / hw0)
        sd = max(1.0, (phd - pcy + chest_clear) / (hd0 - cy0), (phd + pcy + chest_clear) / (hd0 + cy0))
        self.torso = [(z, hw * sw, hd * sd, cy * sd) for z, hw, hd, cy in self.torso]
        hs = b["head"]
        self.hh = (1.0 - A["chin_z"]) * H * hs
        self.chin_z = H - self.hh
        self.head = [(self.chin_z + u * self.hh, hw * H * hs, hd * H * hs, cy * H * hs) for u, hw, hd, cy in A["head_rings"]]
        sg = math.sqrt(g)
        self.neck = [(z * H, hw * H * sg, hd * H * sg, cy * H) for z, hw, hd, cy in A["neck_rings"]]
        ka, kl = g * fit["top"], g * fit["bottom"]
        self.limb_rings = {"upperarm": [(t, rx * H * ka, ry * H * ka) for t, rx, ry in A["upperarm_rings"]],
                           "forearm": [(t, rx * H * ka, ry * H * ka) for t, rx, ry in A["forearm_rings"]],
                           "hand": [(t, rx * H * sg, ry * H * sg) for t, rx, ry in A["hand_rings"]],
                           "thigh": [(t, rx * H * kl, ry * H * kl, 0.0) for t, rx, ry in A["thigh_rings"]],
                           "shin": [(t, rx * H * kl, ry * H * kl, cy * H * kl) for t, rx, ry, cy in A["shin_rings"]]}
        self.caps = {"shoulder": A["shoulder_cap"] * H * ka, "elbow": A["elbow_cap"] * H * ka,
                     "knee": A["knee_cap"] * H * kl}

    def pelvis_at(self, z):
        return interp(self.pelvis, z)

    def torso_at(self, z):
        return interp(self.torso, z)

    def neck_at(self, z):
        return interp(self.neck, z)

    def head_z(self, u):
        return self.chin_z + u * self.hh

    def head_at(self, u):
        return interp(self.head, self.head_z(u))

    def head_max(self, u0, u1):
        """Largest half-width and half-depth of the head between two heights (0 chin, 1 crown)."""
        samples = [self.head_at(u0 + (u1 - u0) * i / 8.0) for i in range(9)]
        return max(s[1] for s in samples), max(s[2] for s in samples)

    def limb(self, kind, t):
        """(rx, ry) of a limb kind at fraction t along its bone."""
        r = interp(self.limb_rings[kind], t)
        return r[1], r[2]

    def limb_loft(self, kind, name):
        L = self.sk.length(name)
        return [(t * L, rx, ry, 0.0, r[3] if len(r) > 3 else 0.0) for r in self.limb_rings[kind] for t, rx, ry in [r[:3]]]


class Ctx:
    """What part builders read: the table, the row, its body and resolved clothing."""

    def __init__(self, table, row, body):
        self.table, self.row, self.body = table, row, body
        self.A, self.H = table["anatomy"], body.H
        m = table["model"]
        self.gap, self.cloth, self.plate = m["layer_gap_m"], m["cloth_thick_m"], m["plate_thick_m"]
        parts = row["parts"]
        self.head_covered = any(p["part"] == "helmet" or (p["part"] == "hood" and p["up"]) for p in parts)
        hair = next((p for p in parts if p["part"] == "hair"), None)
        self.hair_extra = 0.0 if hair is None or self.head_covered else HAIR_SHELL.get(hair["style"], (0, 0, 0.0))[2] * self.hk
        self.capped = any(p["part"] == "cap" and p["style"] in CAPS_OVER_HAIR for p in parts)
        vest = next((p for p in parts if p["part"] == "vest"), None)
        self.vest_extra = self.gap + self.cloth if vest else 0.0
        self.replaced = {"body_head"} if any(p["part"] == "helmet" for p in parts) else set()
        for p in parts:
            if p["part"] == "cyber_arm":
                self.replaced |= {f"forearm_{p['side']}", f"hand_{p['side']}"}

    @property
    def hk(self):
        return self.H * self.row["build"]["head"]

    def mat(self, name):
        return self.row["skin"] if name == "skin" else name

    def clothes(self, key):
        c = self.row["clothes"]
        if key == "sleeves":
            v = c["sleeves"] or c["top"]
        elif key == "forearms":
            v = c["forearms"] or c["sleeves"] or c["top"]
        else:
            v = c[key]
        return self.mat(v)


def build_body(ctx):
    body, sk, A, H = ctx.body, ctx.body.sk, ctx.A, ctx.H
    sides = A["sides"]
    k = ctx.hk
    out = []

    if "body_head" not in ctx.replaced:     # a closed helmet replaces the head it would hide
        m = MB("body_head", "head")
        m.loft([(z, hw, hd, 0.0, cy) for z, hw, hd, cy in body.head], WORLD, sides["head"], 2.4, ctx.mat("skin"))
        e0, e1 = (body.head_z(u) for u in A["eye_band"])
        for f in m.bm.faces:          # the eyes: the two front faces of the band, flush with the head
            c = f.calc_center_median()
            cy = body.head_at((c.z - body.chin_z) / body.hh)[3]
            if e0 < c.z < e1 and len(f.verts) == 4 and Vector((c.x, c.y - cy, 0.0)).normalized().y < -0.85:
                f.material_index = m.slot("eyes")

        def yf(u):
            _, _, hd, cy = body.head_at(u)
            return cy - hd

        z = body.head_z
        m.hull([(sx * 0.010 * k, yf(0.36) + 0.008 * k, z(0.34)) for sx in (-1, 1)] +
               [(sx * 0.006 * k, yf(0.62) + 0.008 * k, z(0.64)) for sx in (-1, 1)] +
               [(0.0, yf(0.40) - 0.011 * k, z(0.37)), (0.0, yf(0.58) - 0.004 * k, z(0.61))], ctx.mat("skin"))
        out.append(m)

    m = MB("body_neck", "neck")
    m.loft([(z_, hw, hd, 0.0, cy) for z_, hw, hd, cy in body.neck], WORLD, sides["limb"], 2.0, ctx.clothes("neck"))
    out.append(m)

    m = MB("body_chest", "chest")
    m.loft([(z_, hw, hd, 0.0, cy) for z_, hw, hd, cy in body.torso], WORLD, sides["torso"], 2.6, ctx.clothes("top"))
    out.append(m)

    m = MB("body_pelvis", "pelvis")
    m.loft([(z_, hw, hd, 0.0, cy) for z_, hw, hd, cy in body.pelvis], WORLD, sides["pelvis"], 2.8, ctx.clothes("bottom"))
    out.append(m)

    n = sides["limb"]
    for s in SIGN:
        ua, fa, hd_, th, sh, ft = (f"{b}_{s}" for b in ("upperarm", "forearm", "hand", "thigh", "shin", "foot"))
        m = MB(f"body_{ua}", ua)
        m.loft(body.limb_loft("upperarm", ua), bone_frame(sk, ua), n, 2.0, ctx.clothes("sleeves"))
        r = body.caps["shoulder"]
        m.loft([(-0.75 * r, 0.7 * r, 0.7 * r), (0.0, r, r), (0.75 * r, 0.7 * r, 0.7 * r)], bone_frame(sk, ua), n, 2.0,
               ctx.clothes("sleeves"))
        out.append(m)
        if fa not in ctx.replaced:
            m = MB(f"body_{fa}", fa)
            m.loft(body.limb_loft("forearm", fa), bone_frame(sk, fa), n, 2.0, ctx.clothes("forearms"))
            r = body.caps["elbow"]
            fr = bone_frame(sk, fa)
            m.loft([(-0.95 * r, r, r), (0.95 * r, r, r)], (fr[0], fr[3], fr[2], fr[1]), n, 2.0, ctx.clothes("forearms"))
            out.append(m)
        if hd_ not in ctx.replaced:
            m = MB(f"body_{hd_}", hd_)
            fr = bone_frame(sk, hd_)
            L = sk.length(hd_)
            m.loft([(t * L, rx, ry) for t, rx, ry in body.limb_rings["hand"]], fr, n, 4.0, ctx.clothes("hands"))
            rx, ry = body.limb("hand", 0.4)
            m.hull([at(fr, x * rx, -y * ry, t * L) for x in (-0.5, 0.5) for y, t in ((0.4, 0.12), (1.15, 0.2), (1.1, 0.55),
                                                                                      (0.5, 0.5))], ctx.clothes("hands"))
            out.append(m)
        m = MB(f"body_{th}", th)
        m.loft(body.limb_loft("thigh", th), bone_frame(sk, th), n, 2.0, ctx.clothes("bottom"))
        out.append(m)
        m = MB(f"body_{sh}", sh)
        m.loft(body.limb_loft("shin", sh), bone_frame(sk, sh), n, 2.0, ctx.clothes("bottom"))
        r = body.caps["knee"]
        fr = bone_frame(sk, sh)
        m.loft([(-0.9 * r, r, r), (0.9 * r, r, r)], (fr[0], fr[3], fr[2], fr[1]), n, 2.0, ctx.clothes("bottom"))
        out.append(m)
        m = MB(f"body_{ft}", ft)
        ank = sk.head[ft]
        fr = (Vector((ank.x, ank.y, 0.0)), X, -Z, -Y)
        sole = A["sole_h"] * H
        kf = H * math.sqrt(ctx.row["build"]["girth"])
        rings = [(-y * H, hw * kf, (top * H - sole) / 2, 0.0, -(top * H + sole) / 2) for y, hw, top in A["foot_rings"]]
        m.loft(rings, fr, n, 4.0, ctx.clothes("shoes"))
        pts = []
        for y, hw, _ in (A["foot_rings"][0], A["foot_rings"][len(A["foot_rings"]) // 2], A["foot_rings"][-1]):
            yy = -y * H + (SOLE_MARGIN * H if y == A["foot_rings"][-1][0] else (-SOLE_MARGIN * H if y == A["foot_rings"][0][0] else 0.0))
            for sx in (-1, 1):
                for zz in (0.0, sole):
                    pts.append(Vector((ank.x + sx * (hw * kf + SOLE_MARGIN * H), -yy, zz)))
        m.hull(pts, ctx.clothes("soles"))
        out.append(m)
    return out


# ----------------------------------------------------------------------------- outfit parts
# Every builder takes (ctx, params) and returns a list of MB segments. Sizes below are the
# shape of each kind of part, in fractions of the head size (k) or the height (H).

HAIR_SHELL = {  # style: (hairline height on the head 0 chin..1 crown, hairline tilt deg, extra volume / head size)
    "crop": (0.6, 26.0, 0.0), "short": (0.55, 28.0, 0.004), "slick": (0.6, 28.0, 0.0),
    "messy": (0.55, 26.0, 0.006), "mohawk": (0.64, 22.0, 0.0), "bun": (0.55, 28.0, 0.004),
    "ponytail": (0.55, 28.0, 0.004), "bob": (0.66, 10.0, 0.006),
}
CAPS_OVER_HAIR = ("baseball", "beanie", "peaked")


def head_shell(m, body, u0, tilt_deg, d, mat, sides, back=0.0, tucked=False):
    """Closed cap over the head from height u0 up, d outside it. The hairline tilts so the back
    sits lower than the front; a second, half-tilted ring keeps the shell off the skull. With
    tucked (hair under a cap) the shell stops inside the cap with a flat top."""
    rings = []
    t = math.tan(math.radians(tilt_deg))
    for uu, tt in ((u0, t), ((u0 + 0.9) / 2.0, t / 2.0)):
        z0, _, hd0, cy0 = body.head_at(uu)
        span = tt * (hd0 + d) / body.hh
        hw, hd = body.head_max(max(uu - span, 0.0), min(uu + span, 0.95))
        rings.append((z0, hw + d, hd + d, 0.0, cy0, -math.atan(tt)))
        if tucked:
            break
    if tucked:
        z, _, _, cy = body.head_at(0.86)
        hw, hd = body.head_max(0.5, 0.9)
        rings.append((z, hw + d, hd + d, 0.0, cy))
    else:
        z, rw, rd, cy = body.head_at(0.92)
        rings.append((z, rw + d, rd + d + back, 0.0, cy + back))
        z, rw, rd, cy = body.head_at(1.0)
        rings.append((z + d, rw + d, rd + d, 0.0, cy + back * 0.5))
    m.loft(rings, WORLD, sides, 2.4, mat)


def part_hair(ctx, p):
    if ctx.head_covered:
        return []
    b, d, k, sides, mat, style = ctx.body, ctx.gap, ctx.hk, ctx.A["sides"]["head"], p["mat"], p["style"]
    m = MB("hair", "head")
    if style == "horseshoe":
        hw, hd = b.head_max(0.25, 0.65)
        _, _, _, cy = b.head_at(0.45)
        rings = [(b.head_z(0.33), hw + d + 0.005 * k, hd + d + 0.005 * k, 0.0, cy),
                 (b.head_z(0.6), hw + d + 0.003 * k, hd + d + 0.003 * k, 0.0, cy)]
        m.cshell(rings, WORLD, *front_open(150.0), 8, 0.008 * k, 2.4, mat)
        return [m]
    u0, tilt, extra = HAIR_SHELL[style]
    head_shell(m, b, u0, tilt, d + extra * k, mat, sides, back=0.005 * k if style == "slick" else 0.0,
               tucked=ctx.capped)
    if ctx.capped:
        return [m]
    if style == "bob":
        hw, hd = b.head_max(0.15, 0.8)
        _, _, _, cy = b.head_at(0.45)
        e = d + 0.012 * k
        m.cshell([(b.head_z(0.2), hw + e, hd + e, 0.0, cy), (b.head_z(0.7), hw + e, hd + e, 0.0, cy)], WORLD,
                 *front_open(130.0), 8, 0.012 * k, 2.4, mat)
    elif style == "mohawk":
        _, hw, hd, cy = b.head_at(0.82)
        _, _, hdb, cyb = b.head_at(0.45)
        m.hull([(sx * 0.010 * k, cy - (hd + d) * 0.85, b.head_z(0.84)) for sx in (-1, 1)] +
               [(sx * 0.010 * k, cyb + hdb + d, b.head_z(0.42)) for sx in (-1, 1)] +
               [(sx * 0.008 * k, cy + dy * hd, ctx.H + d + 0.034 * k) for sx in (-1, 1) for dy in (-0.55, 0.45)] +
               [(sx * 0.008 * k, cyb + hdb + d + 0.03 * k, b.head_z(0.62)) for sx in (-1, 1)], mat)
    elif style == "bun":
        _, hw, hd, cy = b.head_at(0.86)
        c = Vector((0.0, cy + hd + d + 0.006 * k, b.head_z(0.86)))
        r = 0.028 * k
        m.loft([(-0.8 * r, 0.6 * r, 0.6 * r), (0.0, r, r), (0.8 * r, 0.6 * r, 0.6 * r)], axis_frame(c, Y, Z), 8, 2.0, mat)
    elif style == "ponytail":
        _, hw, hd, cy = b.head_at(0.62)
        o = Vector((0.0, cy + hd + d - 0.004 * k, b.head_z(0.62)))
        m.loft([(0.0, 0.016 * k, 0.016 * k), (0.05 * k, 0.02 * k, 0.018 * k), (0.17 * k, 0.008 * k, 0.008 * k)],
               axis_frame(o, Vector((0.0, 0.35, -1.0)), Y), 8, 2.0, mat)
    elif style == "messy":
        for u, ang in ((0.95, 0.0), (0.88, 70.0), (0.88, 200.0), (0.8, 130.0), (0.8, 300.0)):
            z_, hw, hd, cy = b.head_at(u)
            a = math.radians(ang)
            base = Vector((math.cos(a) * (hw + d) * 0.7, cy + math.sin(a) * (hd + d) * 0.7, z_ + d))
            tip = base + Vector((math.cos(a) * 0.02 * k, math.sin(a) * 0.02 * k, 0.03 * k))
            w = 0.012 * k
            m.hull([base + Vector((w, 0, -w)), base + Vector((-w, 0, -w)), base + Vector((0, w, -w)),
                    base + Vector((0, -w, -w)), tip], mat)
    return [m]


def part_ears(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("ears", "head")
    _, hw, hd, cy = b.head_at(0.5)
    z0, z1 = b.head_z(0.36), b.head_z(0.62)
    for sx in (-1, 1):
        xi, xo = sx * (hw * 0.9), sx * (hw + 0.007 * k)
        m.hull([(xi, cy + 0.002 * k, z0), (xi, cy + 0.014 * k, z1), (xi, cy - 0.01 * k, z1 - 0.01 * k),
                (xo, cy + 0.006 * k, z0 + 0.01 * k), (xo, cy + 0.016 * k, z1), (xo, cy - 0.004 * k, z1 - 0.012 * k)],
               ctx.mat("skin"))
    return [m]


def part_glasses(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("glasses", "head")
    u = 0.58
    z = b.head_z(u)
    _, hw, hd, cy = b.head_at(u)
    front = cy - hd
    r, ex = 0.011 * k, 0.0175 * k
    y = front - 0.012
    for sx in (-1, 1):
        m.loft([(0.0, r, r), (0.004 * k, r, r)], axis_frame(Vector((sx * ex, y, z)), -Y), 8, 2.0, p["frame"],
               cap_mats=(p["lens"], p["lens"]))
        m.hull([Vector((sx * (ex + r * 0.9), y + dy, z + dz)) for dy in (-0.002 * k, 0.002 * k) for dz in (-0.002 * k, 0.003 * k)] +
               [Vector((sx * (hw * 0.96 + 0.012), cy + 0.1 * hd + dy, z + dz)) for dy in (-0.002 * k, 0.002 * k)
                for dz in (-0.002 * k, 0.003 * k)], p["frame"])
    m.hull([Vector((sx * (ex - r * 0.9), y + dy, z + dz)) for sx in (-1, 1) for dy in (-0.002 * k, 0.002 * k)
            for dz in (0.0, 0.004 * k)], p["frame"])
    return [m]


def part_goggles(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("goggles", "head")
    eyes = p["on"] == "eyes"
    u = 0.57 if eyes else 0.84
    d2 = 2.0 * ctx.gap + ctx.hair_extra
    hw, hd = b.head_max(u - 0.08, min(u + 0.08, 1.0))
    z = b.head_z(u)
    cy = b.head_at(u)[3]
    w = 0.02 * k
    m.loft([(z - w / 2, hw + d2, hd + d2, 0.0, cy), (z + w / 2, hw + d2, hd + d2, 0.0, cy)], WORLD, 10, 2.4, p["strap"])
    axis = Vector((0.0, -1.0, 0.0)) if eyes else Vector((0.0, -math.cos(0.7), math.sin(0.7)))
    for sx in (-1, 1):
        c = Vector((sx * 0.019 * k, cy - hd - d2 + 0.004 * k, z))
        m.loft([(-0.006 * k, 0.014 * k, 0.013 * k), (0.016 * k, 0.014 * k, 0.013 * k)], axis_frame(c, axis), 8, 2.0,
               p["rim"], cap_mats=(None, p["lens"]))
    return [m]


def part_loupe(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("loupe", "head")
    _, hw, hd, cy = b.head_at(0.58)
    c = Vector((SIGN[p["side"]] * 0.0175 * k, cy - hd + 0.006 * k, b.head_z(0.58)))
    m.loft([(0.0, 0.012 * k, 0.012 * k), (0.02 * k, 0.012 * k, 0.012 * k), (0.034 * k, 0.009 * k, 0.009 * k)],
           axis_frame(c, -Y), 8, 2.0, p["body"], cap_mats=(None, p["lens"]))
    return [m]


def part_respirator(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("respirator", "head")

    def yf(u):
        _, _, hd, cy = b.head_at(u)
        return cy - hd

    z = b.head_z
    m.hull([(sx * 0.022 * k, yf(0.12) + 0.008 * k, z(0.1)) for sx in (-1, 1)] +
           [(sx * 0.03 * k, yf(0.48) + 0.008 * k, z(0.48)) for sx in (-1, 1)] +
           [(sx * 0.016 * k, yf(0.14) - 0.016 * k, z(0.12)) for sx in (-1, 1)] +
           [(sx * 0.02 * k, yf(0.45) - 0.014 * k, z(0.46)) for sx in (-1, 1)] +
           [(0.0, yf(0.3) - 0.026 * k, z(0.28))], p["mat"])
    for sx in (-1, 1):
        c = Vector((sx * 0.03 * k, yf(0.26) - 0.006 * k, z(0.24)))
        m.loft([(-0.006 * k, 0.013 * k, 0.013 * k), (0.02 * k, 0.013 * k, 0.013 * k)],
               axis_frame(c, Vector((sx * 0.8, -1.0, -0.3))), 8, 2.0, p["filter"], cap_mats=(None, p["led"]))
    return [m]


def part_mask_down(ctx, p):
    b, k, d = ctx.body, ctx.hk, ctx.gap
    m = MB("mask", "head")
    rings = [(b.chin_z - 0.014 * k, 0.038 * k + d, 0.042 * k + d, 0.0, -0.012 * k),
             (b.chin_z + 0.02 * k, 0.038 * k + d, 0.042 * k + d, 0.0, -0.012 * k)]
    m.cshell(rings, WORLD, *back_open(170.0), 6, 0.004 * k, 2.2, p["mat"])
    return [m]


def part_earpiece(ctx, p):
    b, k = ctx.body, ctx.hk
    m = MB("earpiece", "head")
    _, hw, hd, cy = b.head_at(0.5)
    sx, z = SIGN[p["side"]], b.head_z(0.5)
    x0 = sx * hw * 0.9
    x1 = sx * (hw * 0.96 + 0.012)
    m.hull([Vector((x, cy + dy, z + dz)) for x in (x0, x1) for dy in (-0.007 * k, 0.009 * k) for dz in (-0.009 * k, 0.009 * k)],
           p["mat"])
    x2 = x1 + sx * 0.004 * k
    m.hull([Vector((x, cy + dy, z + dz)) for x in (x1 - sx * 0.002 * k, x2) for dy in (-0.003 * k, 0.003 * k)
            for dz in (-0.003 * k, 0.003 * k)], p["led"])
    return [m]


def part_cap(ctx, p):
    b, k, sides = ctx.body, ctx.hk, ctx.A["sides"]["head"]
    d2 = 2.0 * ctx.gap + ctx.hair_extra
    m = MB("cap", "head")
    style, mat, trim = p["style"], p["mat"], p["trim"] or p["mat"]
    hw, hd = b.head_max(0.5, 0.85)
    z = b.head_z
    cy = b.head_at(0.6)[3]
    if style in ("baseball", "beanie"):
        u0, tilt = (0.66, 14.0) if style == "baseball" else (0.6, 8.0)
        extra = 0.0 if style == "baseball" else 0.006 * k
        t = math.tan(math.radians(tilt))
        z0, _, hd0, cy0 = b.head_at(u0)
        span = t * (hd0 + d2) / b.hh
        hw, hd = b.head_max(u0 - span, min(u0 + span, 0.95))
        _, mw, md, mcy = b.head_at(0.9)
        _, tw, td, tcy = b.head_at(1.0)
        m.loft([(z0, hw + d2, hd + d2, 0.0, cy0, -math.radians(tilt)), (z(0.9), mw + d2 + extra, md + d2 + extra, 0.0, mcy),
                (ctx.H + d2 + extra, tw + d2, td + d2, 0.0, tcy + extra)], WORLD, sides, 2.4, mat)
        if style == "baseball":
            y0 = cy0 - (hd + d2) + 0.01 * k
            y1 = y0 - 0.075 * k
            zb = z0 + t * (hd + d2 - cy0) - 0.004 * k
            drop = 0.075 * k * math.tan(math.radians(12.0))
            m.hull([Vector((sx * w, y, zz + tk)) for sx in (-1, 1) for w, y, zz in ((0.05 * k, y0, zb), (0.042 * k, y1, zb - drop))
                    for tk in (0.0, 0.004 * k)], trim)
        else:
            e = 0.006 * k
            m.loft([(z0 - 0.002 * k, hw + d2 + e, hd + d2 + e, 0.0, cy0, -math.radians(tilt)),
                    (z0 + 0.024 * k, hw + d2 + e, hd + d2 + e, 0.0, cy0, -math.radians(tilt))], WORLD, sides, 2.4, trim)
    elif style == "peaked":
        zb, zt = z(0.58), z(0.78)
        m.loft([(zb, hw + d2, hd + d2, 0.0, cy), (zt, hw + d2, hd + d2, 0.0, cy)], WORLD, sides, 2.4, mat)
        e = 0.014 * k
        m.loft([(zt - 0.004 * k, hw + d2, hd + d2, 0.0, cy), (zt + 0.012 * k, hw + d2 + e, hd + d2 + e * 1.3, 0.0, cy - 0.006 * k),
                (zt + 0.036 * k, hw + d2 + e, hd + d2 + e * 1.3, 0.0, cy - 0.006 * k, math.radians(-8.0))],
               WORLD, sides, 2.4, mat)
        y0 = cy - (hd + d2) + 0.008 * k
        y1 = y0 - 0.05 * k
        drop = 0.05 * k * math.tan(math.radians(28.0))
        m.hull([Vector((sx * w, y, zz + t)) for sx in (-1, 1) for w, y, zz in ((0.046 * k, y0, zb + 0.004 * k), (0.036 * k, y1, zb - drop))
                for t in (0.0, 0.004 * k)], trim)
        yb = cy - (hd + d2 + e * 1.3) - 0.004 * k
        m.hull([Vector((sx * 0.009 * k, y, zt + zz)) for sx in (-1, 1) for y in (yb, yb + 0.012 * k)
                for zz in (0.006 * k, 0.026 * k)], "metal")
    else:  # paper boat cap, sitting on the hair
        _, mw, md, mcy = b.head_at(0.8)
        zb = z(0.8)
        ridge = ctx.H + d2 + 0.016 * k
        m.hull([Vector((sx * (mw + d2) * 0.96, mcy, zb)) for sx in (-1, 1)] +
               [Vector((sx * 0.01 * k, mcy + sy * (md + d2) * 1.3, zb - 0.01 * k)) for sx in (-1, 1) for sy in (-1, 1)] +
               [Vector((sx * 0.006 * k, mcy + sy * (md + d2) * 1.15, ridge)) for sx in (-1, 1) for sy in (-1, 1)], mat)
    return [m]


def part_helmet(ctx, p):
    b, k, sides = ctx.body, ctx.hk, ctx.A["sides"]["head"]
    d2 = 2.0 * ctx.gap
    m = MB("helmet", "head")
    w0, d0 = b.head_max(0.0, 0.4)
    w1, d1 = b.head_max(0.3, 0.9)
    e = 0.006 * k
    _, tw, td, tcy = b.head_at(1.0)
    cy = b.head_at(0.5)[3]
    rings = [(b.head_z(0.12), w0 + d2 + e, d0 + d2 + e, 0.0, cy, math.radians(8.0)),
             (b.head_z(0.55), w1 + d2 + e, d1 + d2 + e, 0.0, cy), (b.head_z(0.86), w1 + d2 + e * 0.6, d1 + d2 + e * 0.6, 0.0, cy),
             (ctx.H + d2 + e, tw + d2 + e, td + d2 + e, 0.0, tcy)]
    m.loft(rings, WORLD, sides, 2.6, p["mat"])
    v = MB("visor", "head")
    rw, rd = w1 + d2 + e + ctx.gap, d1 + d2 + e + ctx.gap
    v.cshell([(b.head_z(0.5), rw, rd, 0.0, cy), (b.head_z(0.64), rw, rd, 0.0, cy)], WORLD, *back_open(200.0), 6,
             0.006 * k + ctx.gap, 2.6, p["visor"])
    return [m, v]


def part_hood(ctx, p):
    b, k, sides, d = ctx.body, ctx.hk, ctx.A["sides"]["head"], ctx.gap
    if not p["up"]:
        m = MB("hood", "chest")
        z0, hw, hd, cy = b.torso[-1]
        back = cy + hd
        m.hull([Vector((sx * 0.05 * ctx.H, back - 0.02 * ctx.H, z0 - 0.03 * ctx.H)) for sx in (-1, 1)] +
               [Vector((sx * 0.055 * ctx.H, back + 0.01 * ctx.H, z0 - 0.02 * ctx.H)) for sx in (-1, 1)] +
               [Vector((sx * 0.04 * ctx.H, back + 0.02 * ctx.H, z0 + 0.012 * ctx.H)) for sx in (-1, 1)] +
               [Vector((sx * 0.03 * ctx.H, cy + 0.2 * hd, z0 + 0.02 * ctx.H)) for sx in (-1, 1)], p["mat"])
        return [m]
    dh = 2.0 * d
    m = MB("hood", "head")
    head_shell(m, b, 0.62, 20.0, dh + 0.004 * k, p["mat"], sides)
    w0, d0 = b.head_max(0.0, 0.4)
    w1, d1 = b.head_max(0.3, 0.9)
    cy = b.head_at(0.5)[3]
    top = dh + 0.004 * k + d + ctx.cloth      # one layer outside the crown it overlaps
    m.cshell([(b.head_z(-0.06), w0 + dh + 0.004 * k, d0 + dh + 0.008 * k, 0.0, cy + 0.006 * k),
              (b.head_z(0.42), w1 + dh + 0.012 * k + d, d1 + dh + 0.016 * k + d, 0.0, cy + 0.006 * k),
              (b.head_z(0.8), w1 + top, d1 + top, 0.0, cy)],
             WORLD, *front_open(120.0), 8, ctx.cloth, 2.4, p["mat"])
    return [m]


def part_collar(ctx, p):
    b, d, t, H = ctx.body, ctx.gap, ctx.cloth, ctx.H
    m = MB("collar", "chest")
    zb = b.torso[-1][0]
    z0, z1 = zb - 0.03 * H, zb + p["height_m"]

    def extents(z):
        _, hw, hd, cy = b.neck_at(z)
        fw, fr, bk = hw, hd - cy, hd + cy
        if z > b.chin_z:
            _, jw, jd, jcy = b.head_at((z - b.chin_z) / b.hh)
            fw, fr, bk = max(fw, jw), max(fr, jd - jcy), max(bk, jd + jcy)
        return fw, fr, bk

    rings = []
    for z, flare in ((z0, 0.0), (z1, p["flare_m"])):
        fw, fr, bk = extents(z)
        if z == z1:
            fw2, fr2, bk2 = extents(z1 - 0.3 * p["height_m"])
            fw, fr, bk = max(fw, fw2), max(fr, fr2), max(bk, bk2)
        e = d + t + flare
        rings.append((z, fw + e, (fr + bk) / 2 + e, 0.0, (bk - fr) / 2))
    m.cshell(rings, WORLD, *front_open(p["open_deg"]), 8, t, 2.2, p["mat"], edge=p["edge"], top=p["edge"])
    return [m]


def hip_extent(ctx):
    """Half-width and front/back extent of the hips, legs included, at rest."""
    b, sk = ctx.body, ctx.body.sk
    w = max(max(r[1] for r in b.pelvis), abs(sk.head["thigh_l"].x) + max(b.limb("thigh", t)[0] for t in (0.0, 0.2, 0.4)))
    fr = max(r[2] - r[3] for r in b.pelvis)
    bk = max(r[2] + r[3] for r in b.pelvis)
    return w, fr, bk


def part_coat(ctx, p):
    b, d, t, H = ctx.body, ctx.gap, ctx.cloth, ctx.H
    m = MB("coat", "pelvis")
    z0, hw0, hd0, cy0 = b.torso[0]
    w, fr, bk = hip_extent(ctx)
    e = d + t + ctx.vest_extra * 0.0
    f = p["flare_m"]
    hip_w, hip_d, hip_cy = w + e + 0.2 * f, (fr + bk) / 2 + e + 0.2 * f, (bk - fr) / 2
    rings = [(z0 + 0.012 * H, hw0 - 0.003 * H, hd0 - 0.003 * H, 0.0, cy0),
             (0.49 * H, hip_w, hip_d, 0.0, hip_cy),
             (p["hem_z"] * H, hip_w + f, hip_d + 0.9 * f, 0.0, hip_cy + 0.6 * f)]   # the back kicks out so the legs clear it
    m.cshell(rings, WORLD, *front_open(p["open_deg"]), 8, t, 2.3, p["mat"], edge=p["edge"], hem=p["edge"])
    return [m]


def part_chest_strip(ctx, p):
    b, H = ctx.body, ctx.H
    m = MB("chest_strip", "chest")
    z0 = b.torso[0][0] + 0.004 * H
    zs = [z0] + [r[0] for r in b.torso if z0 < r[0] < 0.8 * H] + [0.8 * H]
    rings = []
    for z in zs:
        _, hw, hd, cy = b.torso_at(z)
        front = cy - hd
        yb, yf = front + 0.004 * H, front - 0.011
        rings.append((z, p["width_m"] / 2, (yb - yf) / 2, 0.0, (yb + yf) / 2))
    m.loft(rings, WORLD, 4, 8.0, p["mat"])
    return [m]


def front_panel(m, zs, front_at, half_w, gap, thick, mat, x0=None, x1=None):
    """Flat panel following a surface's front profile, gap in front of it."""
    rings = []
    for z in zs:
        yf = front_at(z) - gap
        if x0 is None:
            rings.append((z, half_w, thick / 2, 0.0, yf - thick / 2))
        else:
            rings.append((z, (x1 - x0) / 2, thick / 2, (x0 + x1) / 2, yf - thick / 2))
    m.loft(rings, WORLD, 4, 8.0, mat)


def part_apron(ctx, p):
    b, d, t, H, sk = ctx.body, ctx.gap, ctx.cloth, ctx.H, ctx.body.sk
    out = []
    g = ctx.row["build"]["girth"]

    def tfront(z):
        _, _, hd, cy = b.torso_at(z)
        return cy - hd

    def pfront(z):
        _, _, hd, cy = b.pelvis_at(z)
        return cy - hd

    z0 = b.torso[0][0]
    if p["bib"]:
        m = MB("apron_bib", "chest")
        front_panel(m, (z0 + 0.002 * H, 0.68 * H, 0.77 * H), tfront, 0.05 * H * g, d, t, p["mat"])
        yt = tfront(0.77 * H) - d
        zt = b.torso[-1][0]
        cyn = b.torso[-1][3]
        for sx in (-1, 1):
            m.hull([Vector((sx * xx, y, z)) for xx in (0.036 * H * g, 0.044 * H * g) for y, z in
                    ((yt - t, 0.77 * H), (yt, 0.77 * H), (cyn - 0.005 * H, zt + 0.004 * H), (cyn + 0.005 * H, zt))], p["mat"])
        out.append(m)
    m = MB("apron_waist", "pelvis")
    w = max(r[1] for r in b.pelvis) * 0.92
    zh = sk.head["thigh_l"].z
    front_panel(m, (zh + 0.0, 0.56 * H, z0 + 0.006 * H), pfront, w, d, t, p["mat"])
    out.append(m)
    yw = pfront(zh + 0.01 * H) - d - t      # front face of the waist panel at its bottom
    for s, sx in SIGN.items():
        m = MB(f"apron_{s}", f"thigh_{s}")
        rings = []
        for z in (p["hem_z"] * H, zh + 0.02 * H):
            yf = yw + d
            rings.append((z, (w - 0.003) / 2, t / 2, sx * (w + 0.003) / 2, yf + t / 2))
        m.loft(rings, WORLD, 4, 8.0, p["mat"])
        out.append(m)
    return out


def part_vest(ctx, p):
    b, d, t, H = ctx.body, ctx.gap, ctx.cloth, ctx.H
    m = MB("vest", "chest")
    zb, zt = b.torso[0][0] + 0.006 * H, p["top_z"] * H
    zs = [zb] + [r[0] for r in b.torso if zb < r[0] < zt] + [zt]
    rings = [(z, hw + d + t, hd + d + t, 0.0, cy) for z in zs for _, hw, hd, cy in [b.torso_at(z)]]
    if p["open_deg"] > 0:
        m.cshell(rings, WORLD, *front_open(p["open_deg"]), 10, t, 2.6, p["mat"])
    else:
        m.loft(rings, WORLD, ctx.A["sides"]["pelvis"], 2.6, p["mat"])
    if p["plates"]:
        g = ctx.row["build"]["girth"] * ctx.row["build"]["shoulders"]
        for sy, z0, z1 in ((-1, 0.64, 0.775), (1, 0.66, 0.79)):
            pts = []
            for z in (z0 * H, z1 * H):
                _, hw, hd, cy = b.torso_at(z)
                surf = cy + sy * (hd + d + t)
                for y in (surf - sy * 0.004 * H, surf + sy * ctx.plate):
                    for sx in (-1, 1):
                        pts.append(Vector((sx * 0.06 * H * g, y, z)))
            m.hull(pts, p["plates"])
    return [m]


def part_armour(ctx, p):
    b, sk, d, t = ctx.body, ctx.body.sk, ctx.gap, ctx.plate
    out = []
    for s in SIGN:
        for piece in p["pieces"]:
            if piece == "shoulder":
                m = MB(f"pauldron_{s}", f"upperarm_{s}")
                R = b.caps["shoulder"] + d + t
                m.loft([(-0.85 * R, 0.5 * R, 0.5 * R), (-0.35 * R, 0.95 * R, 0.95 * R), (0.95 * R, 1.02 * R, R)],
                       bone_frame(sk, f"upperarm_{s}"), 8, 2.4, p["mat"])
            elif piece == "bracer":
                fa = f"forearm_{s}"
                if fa in ctx.replaced:
                    continue
                m = MB(f"bracer_{s}", fa)
                L = sk.length(fa)
                m.loft([(tt * L, rx + d + t, ry + d + t) for tt in (0.4, 0.88) for rx, ry in [b.limb("forearm", tt)]],
                       bone_frame(sk, fa), 8, 3.0, p["mat"])
            elif piece == "shin":
                sh = f"shin_{s}"
                m = MB(f"greave_{s}", sh)
                L = sk.length(sh)
                m.loft([(tt * L, rx + d + t, ry + d + t, 0.0, interp(b.limb_rings["shin"], tt)[3]) for tt in (0.3, 0.82)
                        for rx, ry in [b.limb("shin", tt)]], bone_frame(sk, sh), 8, 3.0, p["mat"])
            elif piece == "knee":
                sh = f"shin_{s}"
                m = MB(f"kneepad_{s}", sh)
                fr = bone_frame(sk, sh)
                r = b.caps["knee"]
                m.box(fr, (-0.8 * r, -(r + 0.4 * t + d), -1.1 * r), (0.8 * r, -(r - 0.25 * r), 1.3 * r), p["mat"])
            else:  # thigh plate
                th = f"thigh_{s}"
                m = MB(f"tasset_{s}", th)
                fr = bone_frame(sk, th)
                L = sk.length(th)
                pts = []
                for tt in (0.12, 0.62):
                    rx, ry = b.limb("thigh", tt)
                    for y in (-(ry - 0.004 * ctx.H), -(ry + d + t)):
                        for x in (-0.75 * rx, 0.75 * rx):
                            pts.append(at(fr, x, y, tt * L))
                m.hull(pts, p["mat"])
            out.append(m)
    return out


def part_belt(ctx, p):
    b, d, H = ctx.body, ctx.gap, ctx.H
    m = MB("belt", "pelvis")
    z0, z1 = b.torso[0][0] - 0.039 * H, b.torso[0][0] - 0.011 * H
    rings = [(z, hw + d, hd + d, 0.0, cy) for z in (z0, z1) for _, hw, hd, cy in [b.pelvis_at(z)]]
    m.loft(rings, WORLD, ctx.A["sides"]["pelvis"], 2.8, p["mat"])
    _, hw, hd, cy = b.pelvis_at((z0 + z1) / 2)
    yf = cy - hd - d
    m.hull([Vector((sx * 0.018 * H, y, z)) for sx in (-1, 1) for y in (yf + 0.004 * H, yf - 0.011)
            for z in (z0 - 0.003 * H, z1 + 0.003 * H)], p["buckle"])
    return [m]


def part_holster(ctx, p):
    b, d, H = ctx.body, ctx.gap, ctx.H
    m = MB("holster", "pelvis")
    w, _, _ = hip_extent(ctx)
    sx = SIGN[p["side"]]
    x0, x1 = sx * (w + d), sx * (w + d + 0.026 * H)
    m.hull([Vector((x, y, z)) for x in (x0, x1) for y in (-0.024 * H, 0.02 * H) for z in (0.47 * H, 0.565 * H)], p["mat"])
    xm0, xm1 = sx * (w + d + 0.005 * H), sx * (w + d + 0.021 * H)
    m.hull([Vector((x, y, z)) for x in (xm0, xm1) for y, z in ((-0.012 * H, 0.56 * H), (0.012 * H, 0.56 * H),
                                                              (0.004 * H, 0.61 * H), (0.024 * H, 0.605 * H))], p["gun"])
    return [m]


def back_at(ctx, z):
    _, hw, hd, cy = ctx.body.torso_at(z)
    return cy + hd + ctx.vest_extra


def front_at(ctx, z):
    _, hw, hd, cy = ctx.body.torso_at(z)
    return cy - hd - ctx.vest_extra


def part_backpack(ctx, p):
    b, d, H = ctx.body, ctx.gap, ctx.H
    g = ctx.row["build"]["girth"] * ctx.row["build"]["shoulders"]
    m = MB("backpack", "chest")
    z0, z1 = 0.63 * H, 0.8 * H
    back = max(back_at(ctx, z0 + (z1 - z0) * i / 6) for i in range(7))
    depth, hw = 0.08 * H * g ** 0.5, 0.066 * H * g
    yc = back + d + depth / 2
    m.loft([(z0, hw, depth / 2, 0.0, yc), (z1, hw * 0.94, depth / 2 * 0.9, 0.0, yc - 0.004 * H)], WORLD, 8, 6.0, p["mat"])
    for sx in (-1, 1):
        x0, x1 = sx * 0.045 * H * g, sx * 0.067 * H * g
        yf_lo, yf_hi = front_at(ctx, 0.67 * H), front_at(ctx, 0.815 * H)
        m.hull([Vector((x, y, z)) for x in (x0, x1) for y, z in ((yf_lo + 0.004 * H, 0.67 * H), (yf_lo - 0.011, 0.67 * H),
                                                                  (yf_hi + 0.004 * H, 0.815 * H), (yf_hi - 0.011, 0.815 * H))],
               p["mat"])
        zt = b.torso[-1][0]
        m.hull([Vector((x, y, z)) for x in (x0, x1) for y, z in ((yf_hi - 0.011, 0.815 * H), (yf_hi + 0.01 * H, 0.815 * H),
                                                                  (0.0, zt + 0.012 * H), (0.0, zt - 0.01 * H),
                                                                  (yc - 0.01 * H, z1), (back - 0.004 * H, 0.8 * H))], p["mat"])
    top = Vector((0.0, yc, z1))
    m.loft([(0.0, 0.012 * H, 0.012 * H), (0.13 * H, 0.012 * H, 0.012 * H)],
           axis_frame(top + Vector((0.035 * H, 0.0, -0.02 * H)), Vector((0.35, 0.25, 1.0))), 8, 2.0, p["scrap"],
           cap_mats=(None, p["scrap2"]))
    m.hull([top + Vector(v) * H for v in ((-0.05, -0.02, -0.01), (-0.01, -0.02, -0.01), (-0.06, 0.02, 0.07),
                                          (-0.02, 0.02, 0.08), (-0.05, -0.012, -0.01), (-0.02, 0.028, 0.08))], p["scrap2"])
    m.box(axis_frame(top + Vector((-0.012 * H, 0.012 * H, -0.01 * H)), Vector((-0.2, 0.1, 1.0))),
          (-0.004 * H, -0.004 * H, 0.0), (0.004 * H, 0.004 * H, 0.12 * H), p["scrap"])
    return [m]


def part_rifle_back(ctx, p):
    b, d, H = ctx.body, ctx.gap, ctx.H
    m = MB("rifle", "chest")
    back = max(back_at(ctx, z * H) for z in (0.64, 0.7, 0.76))
    c = Vector((0.0, back + d + 0.03, 0.71 * H))
    axis = Vector((0.55, 0.0, 1.0)).normalized()
    fr = (c, axis.cross(Y).normalized(), Y.copy(), axis)
    m.box(fr, (-0.035, -0.022, -0.17), (0.035, 0.022, 0.17), p["mat"])
    m.box(fr, (-0.03, -0.018, -0.4), (0.028, 0.018, -0.17), p["stock"])
    m.box(fr, (0.035, -0.016, -0.02), (0.12, 0.016, 0.06), p["mat"])
    m.loft([(0.17, 0.012, 0.012), (0.46, 0.011, 0.011)], (c + fr[1] * 0.012, fr[1], fr[2], fr[3]), 8, 2.0, p["mat"])
    pts = []
    for z, x in ((0.81, 0.075), (0.71, 0.0), (0.61, -0.078)):
        pts.append(Vector((x * H, front_at(ctx, z * H) - 0.004, z * H)))
    m.tube(pts, 0.008, 4, 8.0, p["sling"])
    return [m]


def part_shoulder_light(ctx, p):
    H = ctx.H
    m = MB("shoulder_light", "chest")
    sx = SIGN[p["side"]]
    g = ctx.row["build"]["shoulders"] * ctx.row["build"]["girth"]
    x = sx * 0.064 * H * g
    yf = front_at(ctx, 0.8 * H)
    z = 0.8 * H
    m.hull([Vector((x + dx, y, z + dz)) for dx in (-0.014 * H, 0.014 * H) for y in (yf + 0.006 * H, yf - 0.014)
            for dz in (-0.014 * H, 0.012 * H)], p["mat"])
    m.loft([(0.0, 0.011 * H, 0.009 * H), (0.02 * H, 0.011 * H, 0.009 * H)],
           axis_frame(Vector((x, yf - 0.012, z + 0.006 * H)), -Y), 8, 4.0, p["mat"], cap_mats=(None, p["lens"]))
    return [m]


def part_towel(ctx, p):
    b, H = ctx.body, ctx.H
    m = MB("towel", "chest")
    sx = SIGN[p["side"]]
    g = ctx.row["build"]["shoulders"] * ctx.row["build"]["girth"]
    xs = (sx * 0.04 * H * g, sx * 0.084 * H * g)
    zt = b.torso[-1][0]
    for sy, z0 in ((-1, 0.69), (1, 0.74)):
        pts = []
        for z in (z0 * H, 0.815 * H):
            surf = front_at(ctx, z) if sy < 0 else back_at(ctx, z)
            for y in (surf - sy * 0.004 * H, surf + sy * 0.012):
                for x in xs:
                    pts.append(Vector((x, y, z)))
        m.hull(pts, p["mat"])
    yf, yb = front_at(ctx, 0.815 * H), back_at(ctx, 0.815 * H)
    cy = b.torso[-1][3]
    m.hull([Vector((x, y, z)) for x in xs for y, z in ((yf - 0.012, 0.815 * H), (yb + 0.012, 0.815 * H),
                                                       (cy - 0.02 * H, zt + 0.014 * H), (cy + 0.02 * H, zt + 0.014 * H),
                                                       (cy, 0.8 * H))], p["mat"])
    return [m]


def part_beads(ctx, p):
    b, H = ctx.body, ctx.H
    m = MB("beads", "chest")
    zt = b.torso[-1][0]
    pts = []
    for a in (-100, -80, -55, -30, 0, 30, 55, 80, 100):
        s = math.sin(math.radians(min(abs(a), 90))) * (1 if a >= 0 else -1)
        z = 0.745 * H + (zt - 0.745 * H) * abs(s) ** 1.6
        x = 0.042 * H * s * (0.85 if abs(a) > 90 else 1.0)
        y = front_at(ctx, z) - 0.014 if abs(a) <= 90 else b.torso[-1][3]
        if abs(a) > 90:
            z = zt - 0.004 * H
        pts.append(Vector((x, y, z)))
    m.tube(pts, [0.005 * H if i % 2 else 0.0065 * H for i in range(len(pts))], 4, 2.0, p["mat"])
    bot = pts[4]
    m.hull([bot + Vector((dx, dy, dz)) for dx in (-0.006 * H, 0.006 * H) for dy in (-0.003 * H, 0.003 * H)
            for dz in (-0.004 * H, -0.035 * H)], p["mat"])
    return [m]


def part_cyber_arm(ctx, p):
    b, sk, H = ctx.body, ctx.body.sk, ctx.H
    s = p["side"]
    fa, hd = f"forearm_{s}", f"hand_{s}"
    m = MB(f"{fa}_cyber", fa)
    fr = bone_frame(sk, fa)
    L = sk.length(fa)
    r = max(b.limb("forearm", 0.25))
    m.loft([(0.06 * L, 0.8 * r, 0.85 * r), (0.4 * L, 1.1 * r, 1.05 * r), (1.0 * L, 0.7 * r, 0.7 * r)], fr, 8, 4.0, p["mat"])
    rc = b.caps["elbow"] * 1.12
    m.loft([(-0.95 * rc, rc, rc), (0.95 * rc, rc, rc)], (fr[0], fr[3], fr[2], fr[1]), 8, 2.0, p["joint"])
    out = SIGN[s]
    for y in (-0.55 * r, 0.55 * r):
        m.box(fr, (out * 1.0 * r, y - 0.18 * r, 0.12 * L), (out * 1.35 * r, y + 0.18 * r, 0.85 * L), p["joint"])
    m.box(fr, (-0.25 * r, -1.25 * r, 0.3 * L), (0.25 * r, -0.95 * r, 0.7 * L), p["led"])
    out_segs = [m]
    m = MB(f"{hd}_cyber", hd)
    fr = bone_frame(sk, hd)
    L = sk.length(hd)
    rx, ry = b.limb("hand", 0.5)
    m.loft([(0.0, rx * 1.1, ry * 0.9), (0.5 * L, rx * 1.2, ry * 1.1)], fr, 8, 5.0, p["mat"])
    for i, y in enumerate((-0.7 * ry, 0.0, 0.7 * ry)):
        m.box(fr, (-0.8 * rx, y - 0.28 * ry, 0.48 * L), (0.8 * rx, y + 0.28 * ry, (1.0 - 0.05 * i) * L), p["joint"])
    m.box(fr, (-0.7 * rx, -1.6 * ry, 0.1 * L), (0.7 * rx, -0.9 * ry, 0.55 * L), p["joint"])
    out_segs.append(m)
    return out_segs


def part_wrist_scanner(ctx, p):
    b, sk, d, H = ctx.body, ctx.body.sk, ctx.gap, ctx.H
    s = p["side"]
    fa = f"forearm_{s}"
    m = MB("wrist_scanner", fa)
    fr = bone_frame(sk, fa)
    L = sk.length(fa)
    rings = [(tt * L, rx + d, ry + d) for tt in (0.62, 0.9) for rx, ry in [b.limb("forearm", tt)]]
    m.loft(rings, fr, 8, 3.0, p["mat"])
    out = SIGN[s]
    rx, ry = b.limb("forearm", 0.76)
    x0 = out * (rx + d - 0.002 * H)
    m.box(fr, (x0, -0.6 * ry, 0.66 * L), (x0 + out * (0.006 * H + 0.012), 0.6 * ry, 0.86 * L), p["screen"])
    return [m]


BAND_PLACES = {  # place: (bone kind, fraction along the bone or height fraction for the torso)
    "chest": ("torso", 0.72), "chest_low": ("torso", 0.66), "hem": ("torso", None),
    "upperarm": ("upperarm", 0.5), "elbow_roll": ("upperarm", 0.9), "forearm": ("forearm", 0.5),
    "cuff": ("forearm", 0.88), "thigh": ("thigh", 0.5), "knee": ("shin", 0.12), "shin": ("shin", 0.62),
}


def part_bands(ctx, p):
    b, sk, d, H = ctx.body, ctx.body.sk, ctx.gap, ctx.H
    out = []
    w = p["width_m"]
    for place in p["on"]:
        kind, f = BAND_PLACES[place]
        if kind == "torso":
            z = (b.torso[0][0] + w / 2 + 0.002 * H) if f is None else f * H
            m = MB(f"band_{place}", "chest")
            rings = [(zz, hw + d + ctx.vest_extra, hd + d + ctx.vest_extra, 0.0, cy)
                     for zz in (z - w / 2, z + w / 2) for _, hw, hd, cy in [b.torso_at(zz)]]
            m.loft(rings, WORLD, ctx.A["sides"]["torso"], 2.6, p["mat"])
            out.append(m)
            continue
        for s in SIGN:
            name = f"{kind}_{s}"
            if name in ctx.replaced:
                continue
            m = MB(f"band_{place}_{s}", name)
            L = sk.length(name)
            rings = []
            for tt in (f - w / (2 * L), f + w / (2 * L)):
                r = interp(b.limb_rings[kind], tt)
                cy = r[3] if len(r) > 3 else 0.0
                rings.append((tt * L, r[1] + d, r[2] + d, 0.0, cy))
            m.loft(rings, bone_frame(sk, name), 8, 2.0, p["mat"])
            out.append(m)
    return out


def part_umbrella(ctx, p):
    sk = ctx.body.sk
    hold = ctx.table["animations"]["holds"].get(ctx.row["pose"]["hold"] or "", None)
    side = "r"
    if hold is None or not any(hold[f"forearm_{side}"]):
        side = "l"
    hd = f"hand_{side}"
    pose = Pose()
    apply_hold(pose, hold)
    D, _ = fk(sk, pose)
    up = D[hd].inverted() @ Vector((0.0, 0.18, 1.0)).normalized()
    grip = sk.head[hd] + sk.dir(hd) * sk.length(hd) * 0.5
    m = MB("umbrella", hd)
    R, S = p["radius_m"], p["shaft_m"]
    fr = axis_frame(grip, up, sk.hinge(hd))
    m.loft([(-0.1, 0.008, 0.008), (S + 0.05, 0.008, 0.008)], fr, 8, 2.0, p["shaft"])
    top = S + 0.06
    drop = 0.35 * R
    m.loft([(top, 0.02, 0.02), (top - drop, R, R), (top - drop + 0.006, R - 0.006, R - 0.006), (top - 0.004, 0.012, 0.012)],
           fr, 8, 2.0, p["canopy"])
    m.loft([(top - drop - 0.012, R + 0.008, R + 0.008), (top - drop + 0.004, R + 0.008, R + 0.008)], fr, 8, 2.0, p["rim"])
    return [m]


PARTS = {
    "hair": part_hair, "ears": part_ears, "glasses": part_glasses, "goggles": part_goggles, "loupe": part_loupe,
    "respirator": part_respirator, "mask_down": part_mask_down, "earpiece": part_earpiece, "cap": part_cap,
    "helmet": part_helmet, "hood": part_hood, "collar": part_collar, "coat": part_coat,
    "chest_strip": part_chest_strip, "apron": part_apron, "vest": part_vest, "armour": part_armour,
    "belt": part_belt, "holster": part_holster, "backpack": part_backpack, "rifle_back": part_rifle_back,
    "shoulder_light": part_shoulder_light, "towel": part_towel, "beads": part_beads, "cyber_arm": part_cyber_arm,
    "wrist_scanner": part_wrist_scanner, "bands": part_bands, "patchwork": None, "umbrella": part_umbrella,
}
assert set(PARTS) == set(character_data.PART_SCHEMAS), "PARTS and PART_SCHEMAS must name the same part types"


def patchwork(segs, p):
    """Recolour some faces of the named segments with patch materials (seeded, deterministic)."""
    for m in segs:
        base = m.name[5:] if m.name.startswith("body_") else m.name
        base = base.rsplit("_", 1)[0] if base.endswith(("_l", "_r")) else base
        if base not in p["on"]:
            continue
        keep = m.mats[0]
        for i, f in enumerate(m.bm.faces):
            if m.mats[f.material_index] != keep:
                continue
            h = zlib.crc32(f"{p['seed']}:{m.name}:{i}".encode())
            if (h % 1000) / 1000.0 < p["share"]:
                f.material_index = m.slot(p["mats"][(h // 1000) % len(p["mats"])])


def chest_clearance(table, row):
    m = table["model"]
    if any(p["part"] in ("coat", "apron") for p in row["parts"]):
        return m["layer_gap_m"] + m["cloth_thick_m"] + 0.004 * row["height_m"]
    return 0.012


def build_segments(table, row, splay):
    body = Body(table, row, splay, chest_clearance(table, row))
    ctx = Ctx(table, row, body)
    segs = build_body(ctx)
    for p in row["parts"]:
        if PARTS[p["part"]] is not None:
            segs += PARTS[p["part"]](ctx, p)
    for p in row["parts"]:
        if p["part"] == "patchwork":
            patchwork(segs, p)
    seen = {}
    for m in segs:
        n = seen.get(m.name, 0)
        seen[m.name] = n + 1
        if n:
            m.name = f"{m.name}_{n + 1}"
    return body, ctx, segs


def free(segs):
    for m in segs:
        m.bm.free()


def arm_reach(body, s, dist):
    """Lateral half-thickness of the hanging arm at a distance below the shoulder."""
    sk = body.sk
    Lu, Lf = sk.length(f"upperarm_{s}"), sk.length(f"forearm_{s}")
    if dist < Lu:
        return body.limb("upperarm", dist / Lu)[0]
    if dist < Lu + Lf:
        return body.limb("forearm", (dist - Lu) / Lf)[0] * 1.15
    return body.limb("hand", 0.5)[0]


def auto_splay(table, row):
    """Smallest outward tilt of each hanging arm that keeps the forearm and hand off the hips,
    the thighs and everything worn on them (coats, holsters), by one layer gap. Above the elbow
    the upper arm may rest against the torso, as a real arm does."""
    base = table["anatomy"]["arm_splay_deg"]
    if row["pose"]["arm_splay_deg"] is not None:
        return {s: row["pose"]["arm_splay_deg"] for s in SIGN}
    body, ctx, segs = build_segments(table, row, {s: base for s in SIGN})
    sk, H, gap = body.sk, body.H, ctx.gap
    out = {}
    for s, sg in SIGN.items():
        sh = sk.head[f"upperarm_{s}"]
        top = sk.head[f"forearm_{s}"].z + 0.01 * H     # the upper arm may touch the torso side
        bottom = sk.tail[f"hand_{s}"].z - 0.02 * H
        need = math.radians(base)
        for m in segs:
            if m.bone not in TRUNK_BONES:
                continue
            for v in m.bm.verts:
                P = v.co
                if P.x * sg <= 0 or not bottom < P.z < top:
                    continue
                dist = sh.z - P.z
                t = (abs(P.x) + gap + arm_reach(body, s, dist) - abs(sh.x)) / dist
                need = max(need, math.atan(t))
        out[s] = round(math.degrees(need), 2)
    free(segs)
    return out


def body_metrics(body, ctx, segs):
    """Sizes the clips need to place hands on the hips, on the belt buckle or on the thighs."""
    H, sk = body.H, body.sk
    hip_side = {}
    for s, sg in SIGN.items():
        xs = [abs(v.co.x) for m in segs if m.bone in ("pelvis", "spine", "chest") for v in m.bm.verts
              if v.co.x * sg > 0 and 0.54 * H < v.co.z < 0.63 * H and abs(v.co.y) < 0.06 * H]
        hip_side[s] = max(xs) if xs else body.pelvis[1][1]
    front = [-v.co.y for m in segs if m.bone in ("pelvis", "spine", "chest") for v in m.bm.verts
             if 0.46 * H < v.co.z < 0.6 * H and abs(v.co.x) < 0.07 * H]
    return {"hip_side": hip_side, "hand_half": body.limb("hand", 0.5)[0], "hand_z": 0.605 * H,
            "belt_front": max(front), "clasp_z": 0.52 * H, "forearm_r": max(body.limb("forearm", 0.3)),
            "thigh_r": body.limb("thigh", 0.55)[1], "seat_to_hip": sk.head["thigh_l"].z - body.pelvis[0][0]}


# ----------------------------------------------------------------------------- Blender objects

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_materials(table):
    for name, spec in table["materials"].items():
        mat = bpy.data.materials.new(name)
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        lin = tuple(srgb_to_linear(c) for c in spec["color"])
        bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
        bsdf.inputs["Roughness"].default_value = spec["roughness"]
        bsdf.inputs["Metallic"].default_value = spec["metallic"]
        if spec["emission"] is not None and spec["emission_strength"] > 0:
            bsdf.inputs["Emission Color"].default_value = (*(srgb_to_linear(c) for c in spec["emission"]), 1.0)
            bsdf.inputs["Emission Strength"].default_value = spec["emission_strength"]
        if spec["alpha"] < 1.0:
            bsdf.inputs["Alpha"].default_value = spec["alpha"]
            mat.surface_render_method = "BLENDED"
        mat.diffuse_color = (*lin, spec["alpha"])


def make_armature(cid, sk, coll):
    data = bpy.data.armatures.new(f"{cid}.rig")
    arm = bpy.data.objects.new(cid, data)
    coll.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, parent in BONES:
        eb = data.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = sk.head[name], sk.tail[name], 0.0
        eb.use_connect = False
        if parent:
            eb.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for name, _ in BONES:
        sk.rest_q[name] = data.bones[name].matrix_local.to_quaternion()
    return arm


def make_segment_objects(cid, arm, segs, coll, smooth_deg):
    limit = math.radians(smooth_deg)
    tris = 0
    for m in sorted(segs, key=lambda s: s.name):
        bm = m.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) != 2 or lf[0].material_index != lf[1].material_index or e.calc_face_angle(math.pi) > limit:
                e.smooth = False
        tris += m.tris()
        bone = arm.data.bones[m.bone]
        head = bone.head_local.copy()
        bmesh.ops.translate(bm, verts=bm.verts, vec=-head)
        me = bpy.data.meshes.new(f"{cid}.{m.name}")
        bm.to_mesh(me)
        bm.free()
        for mat in m.mats:
            me.materials.append(bpy.data.materials[mat])
        project_uvs(me)
        ob = bpy.data.objects.new(f"{cid}.{m.name}", me)
        coll.objects.link(ob)
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = m.bone
        ob.matrix_parent_inverse = (bone.matrix_local @ Matrix.Translation((0.0, bone.length, 0.0))).inverted()
        ob.matrix_basis = Matrix.Translation(head)
    return tris


def key_clip(arm, sk, cid, clip, poses):
    """One action per clip, every bone keyed on every frame (linear), pelvis location too."""
    act = bpy.data.actions.new(f"{cid}.{clip}")
    slot = act.slots.new(id_type="OBJECT", name=cid)
    strip = act.layers.new("Layer").strips.new(type="KEYFRAME")
    bag = strip.channelbag(slot, ensure=True)
    n = len(poses)

    def curve(path, index, group, values):
        fc = bag.fcurves.new(path, index=index, group_name=group)
        fc.keyframe_points.add(n)
        fc.keyframe_points.foreach_set("co", [c for f, v in enumerate(values) for c in (float(f), v)])
        fc.keyframe_points.foreach_set("interpolation", [1] * n)  # LINEAR
        fc.update()

    for name, _ in BONES:
        B = sk.rest_q[name]
        Bi = B.inverted()
        qs = []
        for p in poses:
            q = Bi @ p.rot[name] @ B
            if q.w < 0.0:
                q.negate()
            qs.append(q)
        for i in range(4):
            curve(f'pose.bones["{name}"].rotation_quaternion', i, name, [q[i] for q in qs])
        if name == "pelvis":
            locs = [Bi @ p.offset for p in poses]
            for i in range(3):
                curve(f'pose.bones["{name}"].location', i, name, [v[i] for v in locs])
    return act


def export_character(arm, path, gltf_opts):
    kids = sorted(arm.children, key=lambda o: o.name)
    names = [o.name for o in kids]
    arm_name, loc = arm.name, arm.location.copy()
    arm.location = (0.0, 0.0, 0.0)
    for o in kids:
        o.name = o.name.split(".", 1)[1]
    arm.name = "rig"
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for o in kids:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, **gltf_opts)
    arm.name = arm_name
    for o, n in zip(kids, names):
        o.name = n
    arm.location = loc


GLTF = dict(export_format="GLB", use_selection=True, export_extras=True, export_image_format="NONE",
            export_materials="EXPORT", export_yup=True, export_apply=False, export_lights=False,
            export_cameras=False, export_texcoords=True, export_normals=True, export_tangents=False,
            export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
            export_frame_step=1, export_optimize_animation_size=False, export_reset_pose_bones=True,
            export_def_bones=False, export_skins=True, export_morph=False)


def floor_check(sk, segs_verts, poses, step=3):
    """Lowest point any segment reaches in a clip (metres; the floor is Z = 0)."""
    low = math.inf
    for p in poses[::step]:
        D, P = fk(sk, p)
        for bone, verts in segs_verts:
            d, o, h = D[bone], P[bone], sk.head[bone]
            for v in verts:
                z = (o + d @ (v - h)).z
                if z < low:
                    low = z
    return low


def build_character(table, row, index, parent_coll, out_dir):
    cid = row["id"]
    splay = auto_splay(table, row)
    body, ctx, segs = build_segments(table, row, splay)
    metrics = body_metrics(body, ctx, segs)
    low_verts = [(m.bone, [v.co.copy() for v in m.bm.verts if v.co.z < 0.6 * body.H]) for m in segs]
    coll = collection(cid, parent_coll)
    arm = make_armature(cid, body.sk, coll)
    tris = make_segment_objects(cid, arm, segs, coll, table["model"]["smooth_angle_deg"])
    motion = Motion(body.sk, table["animations"], row, metrics)
    ad = arm.animation_data_create()
    fps = table["animations"]["fps"]
    lengths, floor = {}, {}
    for clip in reversed(CLIPS):    # idle ends on top, so the viewport shows it
        poses = motion.poses(clip)
        floor[clip] = floor_check(body.sk, low_verts, poses)
        act = key_clip(arm, body.sk, cid, clip, poses)
        track = ad.nla_tracks.new()
        track.name = clip
        track.strips.new(clip, 0, act)
        lengths[clip] = (len(poses) - 1) / fps
    ad.action = None
    anims = table["animations"]
    arm["undercity"] = {
        "id": cid, "name": row["name"], "role": row["role"], "height_m": row["height_m"],
        "facing": "+Z", "walk_speed_m_s": anims["walk"]["speed_m_s"],
        "animations": {c: {"length_s": round(lengths[c], 4), "loop": anims[c]["loop"]} for c in CLIPS},
    }
    per_row, spacing = table["model"]["lineup_per_row"], table["model"]["lineup_spacing_m"]
    path = os.path.join(out_dir, f"{cid}.glb")
    export_character(arm, path, GLTF)
    arm.location = ((index % per_row - (per_row - 1) / 2.0) * spacing, (index // per_row) * 3.0, 0.0)
    return {"id": cid, "tris": tris, "segments": len(segs), "splay": splay, "lengths": lengths, "floor": floor}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1].split(",")
    return only


def main():
    only = parse_args()
    table = character_data.load()
    rows = table["characters"]
    if only:
        unknown = [c for c in only if c not in [r["id"] for r in rows]]
        if unknown:
            raise SystemExit(f"[characters] unknown ids: {unknown}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Characters"
    scene.render.fps = table["animations"]["fps"]
    scene.frame_start, scene.frame_end = 0, round(table["animations"]["idle"]["length_s"] * scene.render.fps)
    make_materials(table)
    out_dir = os.path.join(ROOT, table["model"]["out_dir"])
    root = collection("Characters")
    report = []
    for i, row in enumerate(rows):
        if only and row["id"] not in only:
            continue
        info = build_character(table, row, i, root, out_dir)
        report.append(info)
        print(f"[characters] {info['id']:12s} {info['tris']:5d} tris  {info['segments']:2d} segments  "
              f"splay l {info['splay']['l']:.1f} r {info['splay']['r']:.1f}  "
              + " ".join(f"{c} {info['lengths'][c]:.3f}s" for c in CLIPS)
              + "  lowest " + " ".join(f"{c} {info['floor'][c] * 100:.1f}cm" for c in CLIPS))
    if only:
        print("[characters] --only given: characters.blend left unchanged")
    else:
        save_reproducible(os.path.join(HERE, "characters.blend"))
        print("[characters] saved characters.blend")
    sunk = [f"{r['id']} {c} {z * 100:.1f} cm" for r in report for c, z in r["floor"].items() if z < -0.005]
    if sunk:
        print("[characters] WARNING below the floor:", ", ".join(sunk))
    bad = [r for r in report if not 600 <= r["tris"] <= 1600]
    if bad:
        print("[characters] WARNING triangle budget (600-1600) exceeded by:", ", ".join(f"{r['id']} {r['tris']}" for r in bad))


if __name__ == "__main__":
    main()

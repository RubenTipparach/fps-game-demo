"""Build an Undercity level in Blender from its layout, one glb per sector.

    blender -b --factory-startup -P tools/blender/build_undercity.py -- hub
    blender -b --factory-startup -P tools/blender/build_undercity.py -- hub --sector lantern_row

The layout (tools/levels/layouts/<id>.py) is the single source (CLAUDE.md 7.1).
tools/levels/city_plan.py turns it into a plan: sectors, 40 m chunks, primitives, lights and
entities. That step runs in the system python3, because it needs shapely and reuses the design
map's own geometry (render_map.py); Blender's Python has neither. This script meshes the plan:
boxes, prisms, cylinders, lofts, neon text, and booleans (buildings are solid blocks with their
windows, doors and rooms carved out, as in tools/blender/build_cistern.py). It writes:

  game/levels/undercity/<id>/<id>_<sector>.glb   what Godot imports (tools/godot/import_presets.py)
  tools/blender/undercity_<id>.blend             the whole level, for inspection (full builds only)

Object naming in each glb (Godot's import suffixes decide collision):
  <sector>_walk_<i>_<j>-col       walkable and blocking geometry, trimesh collision
  <sector>_vis_<i>_<j>            facades and details, no collision
  <sector>_hull_<i>_<j>-colonly   simplified building collision (the plain blocks)
  interior_<building>-col         an enterable interior; extras: visibility range, lightmap texel scale
  prop_<kind>_<n>-col             a small prop; extras: visibility range
  corona_<n>                      a light's corona; extras: no GI, no shadow, visibility range
  car_<n>, car_<n>_box-colonly    a parked car: a committed model placed by the plan (Plan.model),
                                  its own UVs and materials, its collision boxes; extras: visibility
                                  range, lightmap texel scale, and the model's provenance
  ENT_<kind>_<id>                 entity empties; extras arrive in Godot (blender_level_import.gd)

Set UNDERCITY_PYTHON to the python3 that has shapely if it isn't the one on PATH.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import GAME, HERE, ROOT, material, project_uvs  # noqa: E402

CITY_PLAN = os.path.join(ROOT, "tools", "levels", "city_plan.py")


def V(p):
    """Layout (x east, y south, z up) to Blender (X east, Y north, Z up)."""
    return (p[0], -p[1], p[2])


# ----------------------------------------------------------------------------- mesh building

class Acc:
    """Accumulates faces for one object: vertices in Blender space, a material per face, and an
    optional colour per face (the skyline's towers carry their lit share and seed in it)."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.smooth = []
        self.colors = []

    def add(self, verts, faces, mats, smooth=None, colors=None):
        base = len(self.verts)
        self.verts += verts
        for k, f in enumerate(faces):
            self.faces.append([base + i for i in f])
            self.mats.append(mats[k])
            self.smooth.append(bool(smooth[k]) if smooth else False)
            self.colors.append(tuple(colors[k]) if colors and colors[k] is not None else None)

    def extend(self, other):
        self.add(other.verts, other.faces, other.mats, other.smooth, other.colors)

    def to_mesh(self, name, origin=None):
        me = bpy.data.meshes.new(name)
        verts = self.verts
        if origin is not None:
            ox, oy, oz = origin
            verts = [(x - ox, y - oy, z - oz) for x, y, z in verts]
        me.from_pydata(verts, [], self.faces)
        names = sorted(set(self.mats))
        index = {n: i for i, n in enumerate(names)}
        for n in names:
            me.materials.append(material(n))
        me.polygons.foreach_set("material_index", [index[m] for m in self.mats])
        me.polygons.foreach_set("use_smooth", self.smooth)
        if any(c is not None for c in self.colors):
            # One colour per face, on its corners (glTF COLOR_0); faces without one are white.
            attr = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
            per_loop = []
            for f, c in zip(self.faces, self.colors):
                rgba = (*(c or (1.0, 1.0, 1.0))[:3], 1.0)
                per_loop += list(rgba) * len(f)
            attr.data.foreach_set("color", per_loop)
        me.validate(clean_customdata=False)
        me.update()
        return me


def newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a[1] - b[1]) * (a[2] + b[2])
        n.y += (a[2] - b[2]) * (a[0] + b[0])
        n.z += (a[0] - b[0]) * (a[1] + b[1])
    return n


def mesh_hexa(p):
    pts = [V(c) for c in p["p"]]
    mats = p["mat"] if isinstance(p["mat"], list) else [p["mat"]] * 6
    faces = [[0, 3, 2, 1], [4, 5, 6, 7]] + [[i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i] for i in range(4)]
    centre = Vector((sum(q[0] for q in pts) / 8, sum(q[1] for q in pts) / 8, sum(q[2] for q in pts) / 8))
    acc = Acc()
    keep, keep_m = [], []
    for fi, f in enumerate(faces):
        if fi in p.get("skip", []):
            continue
        fp = [pts[i] for i in f]
        n = newell(fp)
        if n.length < 1e-9:
            continue
        fc = Vector((sum(q[0] for q in fp) / 4, sum(q[1] for q in fp) / 4, sum(q[2] for q in fp) / 4))
        if n.dot(fc - centre) < 0:
            f = list(reversed(f))
        keep.append(f)
        keep_m.append(mats[fi])
    acc.add(pts, keep, keep_m, colors=[p["color"]] * len(keep) if p.get("color") else None)
    return acc


def mesh_quad(p):
    acc = Acc()
    acc.add([V(c) for c in p["p"]], [[0, 1, 2, 3]], [p["mat"]])
    return acc


def cap_triangles(rings2d, z, up, tris2d=None):
    """A polygon's cap at height z, facing up (or down): the plan's triangles when it has them
    (city_plan.py triangulates with holes), else Blender's tessellator."""
    loops = [[(x, -y, z) for x, y in r] for r in rings2d]
    if tris2d:
        flat = [(x, -y, z) for t in tris2d for x, y in t]
        tris = [(3 * k, 3 * k + 1, 3 * k + 2) for k in range(len(tris2d))]
    else:
        flat = [v for lp in loops for v in lp]
        tris = tessellate_polygon([[Vector(v) for v in lp] for lp in loops])
    # a cap that loses or gains area has holes filled or regions dropped: stop, don't ship it
    def area(r):
        return abs(sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))) / 2
    want = area(loops[0]) - sum(area(lp) for lp in loops[1:])
    got = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
              for a, b, c in ((flat[t[0]], flat[t[1]], flat[t[2]]) for t in tris))
    if abs(got - want) > 0.01 * max(want, 1.0):
        raise SystemExit(f"cap triangulation lost area ({got:.2f} of {want:.2f} m2) at z {z}, "
                         f"{len(loops)} rings from {loops[0][0][:2]}")
    faces = []
    for t in tris:
        a, b, c = flat[t[0]], flat[t[1]], flat[t[2]]
        nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        f = [t[0], t[1], t[2]]
        if (nz > 0) != up:
            f.reverse()
        faces.append(f)
    return flat, faces


def mesh_prism(p):
    acc = Acc()
    rings = p["rings"]
    z0, z1 = p["z0"], p["z1"]
    flip = p.get("flip", False)
    mat = p["mat"]
    caps = p.get("caps", ["top"])
    if "top" in caps:
        verts, faces = cap_triangles(rings, z1, up=not flip, tris2d=p.get("tris"))
        acc.add(verts, faces, [mat["top"]] * len(faces))
    if "bottom" in caps:
        verts, faces = cap_triangles(rings, z0, up=flip, tris2d=p.get("tris"))
        acc.add(verts, faces, [mat.get("bottom", mat["top"])] * len(faces))
    edges = p.get("edges")
    for ri, ring in enumerate(rings):
        n = len(ring)
        for k in range(n):
            spec = edges[ri][k] if edges else [z0, z1]
            if spec is None:
                continue
            za, zb = spec
            if zb - za < 1e-6:
                continue
            a, b = ring[k], ring[(k + 1) % n]
            q = [(a[0], -a[1], za), (b[0], -b[1], za), (b[0], -b[1], zb), (a[0], -a[1], zb)]
            f = [0, 1, 2, 3] if not flip else [3, 2, 1, 0]
            acc.add(q, [f], [mat["side"]])
    return acc


def mesh_loft(p):
    acc = Acc()
    rings, zs, mat = p["rings"], p["z"], p["mat"]
    verts, faces = cap_triangles([rings[-1]], zs[-1], up=True)
    acc.add(verts, faces, [mat["top"]] * len(faces))
    verts, faces = cap_triangles([rings[0]], zs[0], up=False)
    acc.add(verts, faces, [mat["bottom"]] * len(faces))
    n = len(rings[0])
    for li in range(len(rings) - 1):
        ra, rb = rings[li], rings[li + 1]
        za, zb = zs[li], zs[li + 1]
        for k in range(n):
            q = [(ra[k][0], -ra[k][1], za), (ra[(k + 1) % n][0], -ra[(k + 1) % n][1], za),
                 (rb[(k + 1) % n][0], -rb[(k + 1) % n][1], zb), (rb[k][0], -rb[k][1], zb)]
            acc.add(q, [[0, 1, 2, 3]], [mat["side"]])
    return acc


def mesh_cyl(p):
    acc = Acc()
    c = Vector(V(p["c"]))
    ax = Vector(V(p["axis"]))
    ax = ax.normalized() if ax.length > 1e-9 else Vector((0, 0, 1))
    h = p["h"]
    if h < 0:
        c = c + ax * h
        h = -h
    u = ax.orthogonal().normalized()
    w = ax.cross(u).normalized()
    seg, r = p["seg"], p["r"]
    ring0 = [c + (u * math.cos(2 * math.pi * i / seg) + w * math.sin(2 * math.pi * i / seg)) * r for i in range(seg)]
    ring1 = [v + ax * h for v in ring0]
    verts = [tuple(v) for v in ring0 + ring1]
    faces, mats, smooth = [], [], []
    for i in range(seg):
        j = (i + 1) % seg
        faces.append([i, j, seg + j, seg + i])
        mats.append(p["mat"]["side"])
        smooth.append(True)
    if p.get("caps", True):
        faces.append(list(reversed(range(seg))))
        faces.append(list(range(seg, 2 * seg)))
        mats += [p["mat"]["cap"]] * 2
        smooth += [False, False]
    # orient the side faces outward
    fixed = []
    for f, sm in zip(faces, smooth):
        pts = [verts[i] for i in f]
        n = newell(pts)
        fc = Vector((sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts), sum(q[2] for q in pts) / len(pts)))
        mid = c + ax * (h / 2)
        if n.dot(fc - mid) < 0:
            f = list(reversed(f))
        fixed.append(f)
    acc.add(verts, fixed, mats, smooth)
    return acc


def mesh_text(p):
    cu = bpy.data.curves.new("sign", "FONT")
    cu.body = p["s"]
    cu.align_x = "CENTER"
    cu.size = p["size"]
    cu.extrude = p["depth"] / 2
    cu.resolution_u = 2
    cu.space_line = 1.1
    ob = bpy.data.objects.new("sign", cu)
    bpy.context.scene.collection.objects.link(ob)
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    ys = [v.co.y for v in me.vertices]
    ymin = min(ys) if ys else 0.0
    h = math.radians(p["heading"])
    F = Vector((math.sin(h), math.cos(h), 0.0))
    U = Vector((0.0, 0.0, 1.0))
    R = U.cross(F)
    base = Vector(V(p["p"]))
    verts = []
    for v in me.vertices:
        x, y, z = v.co.x, v.co.y - ymin, v.co.z + p["depth"] / 2
        verts.append(tuple(base + R * x + U * y + F * z))
    faces = [list(poly.vertices) for poly in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    acc = Acc()
    acc.add(verts, faces, [p["mat"]] * len(faces))
    return acc


def temp_object(acc, name, coll):
    me = acc.to_mesh(name)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def mesh_bool(p, interior_accs):
    """Solid minus cutters (Exact boolean, materials transferred from the cutters). Faces inside
    an interior box go to that interior's accumulator."""
    work = bpy.data.collections.new("bool_work")
    bpy.context.scene.collection.children.link(work)
    cuts = bpy.data.collections.new("bool_cuts")
    work.children.link(cuts)
    solid = temp_object(mesh_prim(p["solid"], None), "solid", work)
    for i, c in enumerate(p["cutters"]):
        temp_object(mesh_prim(c, None), f"cut{i}", cuts)
    if p["cutters"]:
        mod = solid.modifiers.new("carve", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.operand_type = "COLLECTION"
        mod.collection = cuts
        mod.solver = "EXACT"
        mod.material_mode = "TRANSFER"
        mod.use_hole_tolerant = True
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(solid.evaluated_get(deps))
    z0 = p["solid"]["z0"]
    names = [m.name.split(".")[0] if m else "concrete" for m in me.materials]
    boxes = []
    if p.get("interior"):
        boxes = [(Vector(V(lo)), Vector(V(hi))) for lo, hi in p["interior"]["boxes"]]
        boxes = [(Vector((min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))), Vector((max(a.x, b.x), max(a.y, b.y), max(a.z, b.z))))
                 for a, b in boxes]
    out, inner = Acc(), Acc()
    verts = [tuple(v.co) for v in me.vertices]
    for poly in me.polygons:
        n = poly.normal
        vz = [verts[i][2] for i in poly.vertices]
        if n.z < -0.99 and max(vz) < z0 + 1e-4:
            continue   # the block's underside
        c = poly.center
        tgt = out
        for lo, hi in boxes:
            if lo.x <= c.x <= hi.x and lo.y <= c.y <= hi.y and lo.z <= c.z <= hi.z:
                tgt = inner
                break
        tgt.add([verts[i] for i in poly.vertices], [list(range(len(poly.vertices)))],
                [names[poly.material_index] if poly.material_index < len(names) else names[0]])
    for ob in list(work.all_objects):
        m = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(m)
    bpy.data.meshes.remove(me)
    bpy.data.collections.remove(cuts)
    bpy.data.collections.remove(work)
    if p.get("interior"):
        interior_accs.setdefault(p["interior"]["object"], Acc()).extend(inner)
    return out


def mesh_prim(p, interior_accs):
    t = p["t"]
    if t == "hexa":
        return mesh_hexa(p)
    if t == "prism":
        return mesh_prism(p)
    if t == "cyl":
        return mesh_cyl(p)
    if t == "quad":
        return mesh_quad(p)
    if t == "loft":
        return mesh_loft(p)
    if t == "text":
        return mesh_text(p)
    if t == "bool":
        return mesh_bool(p, interior_accs)
    raise ValueError(t)


# ----------------------------------------------------------------------------- the level

def run_plan(level):
    py = os.environ.get("UNDERCITY_PYTHON") or shutil.which("python3")
    if not py:
        raise SystemExit("no python3 for tools/levels/city_plan.py; set UNDERCITY_PYTHON")
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        r = subprocess.run([py, CITY_PLAN, level, "--out", path], stderr=subprocess.PIPE, text=True)
        sys.stderr.write(r.stderr)
        if r.returncode != 0:
            raise SystemExit(f"city_plan.py failed ({r.returncode})")
        with open(path) as f:
            return json.load(f)
    finally:
        os.remove(path)


def build_model(m, coll):
    """A committed model the plan placed in this sector (Plan.model): its glb imported as it is,
    at its point and heading, and built into the sector as static geometry. Its drawn mesh is named
    after the placement, its "-colonly" object "<name>_box-colonly" so Godot makes it the mesh's
    static body, and the placement's extras go on the drawn mesh. Its UVs and materials are its own:
    no world UVs. A material the import had to rename (a name the scene already has) is the
    scene's, so the sector's import preset maps it by name."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GAME, m["path"]))
    objs = sorted((o for o in bpy.data.objects if o not in before), key=lambda o: o.name)
    drawn = [o for o in objs if "-colonly" not in o.name]
    if len(drawn) != 1 or any(o.type != "MESH" or o.parent is not None for o in objs):
        raise SystemExit(f"[undercity] {m['path']}: expected one drawn mesh and its collision, loose, got "
                         f"{[(o.name, o.type) for o in objs]}")
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.name = o.data.name = m["name"] if o in drawn else f"{m['name']}_box-colonly"
        o.location = V(m["pos"])
        o.rotation_mode = "XYZ"
        o.rotation_euler = (0.0, 0.0, math.radians(-m["heading"]))
        for slot in o.material_slots:
            base = slot.material.name.rsplit(".", 1)[0] if slot.material else None
            if base and base != slot.material.name and base in bpy.data.materials:
                slot.material = bpy.data.materials[base]
    for k, v in m["extras"].items():
        drawn[0][k] = v
    return drawn[0]


def build_sector(sec, root):
    coll = bpy.data.collections.new(f"sector_{sec['name']}")
    root.children.link(coll)
    interior_accs = {}
    made = []
    pending = {}
    for o in sec["objects"]:
        acc = Acc()
        for p in o["prims"]:
            acc.extend(mesh_prim(p, interior_accs))
        pending[o["name"]] = (o, acc)
    for name, iacc in interior_accs.items():
        if name in pending:
            pending[name][1].extend(iacc)
        else:
            pending[name] = ({"name": name, "col": "col", "extras": {}, "origin": None, "prims": []}, iacc)
    for name in sorted(pending):
        o, acc = pending[name]
        if not acc.faces:
            continue
        origin = V(o["origin"]) if o.get("origin") else None
        me = acc.to_mesh(name, origin)
        ob = bpy.data.objects.new(name, me)
        if origin is not None:
            ob.location = origin
        for k, v in (o.get("extras") or {}).items():
            ob[k] = v
        coll.objects.link(ob)
        project_uvs(me, ob.matrix_world)
        made.append(ob)
    for m in sec.get("models", []):
        made.append(build_model(m, coll))
    ents = []
    for e in sec["entities"]:
        em = bpy.data.objects.new(e["name"], None)
        em.empty_display_type = "ARROWS"
        em.empty_display_size = 0.5
        em.location = V(e["pos"])
        em.rotation_euler = (0.0, 0.0, math.radians(-e["heading"]))
        for k, v in e["extras"].items():
            em[k] = v
        coll.objects.link(em)
        ents.append(em)
        if e.get("preview"):
            pv = e["preview"]
            ld = bpy.data.lights.new(e["name"] + "_preview", "POINT")
            ld.color = pv["color"][:3]
            ld.energy = pv["energy"] * 150.0
            ld.use_custom_distance = True
            ld.cutoff_distance = pv["range"]
            ld.shadow_soft_size = 0.25
            lo = bpy.data.objects.new(e["name"] + "_preview", ld)
            loc = Vector(V(e["pos"]))
            off = pv.get("offset")
            if off == "forward":
                h = math.radians(e["heading"])
                loc += Vector((math.sin(h), math.cos(h), 0.0)) * 0.35
            elif off:
                loc += Vector(off)
            lo.location = loc
            bpy.data.collections["Preview"].objects.link(lo)
    return coll, made, ents


def export_sector(level, name, coll):
    out = os.path.join(GAME, "levels", "undercity", level, f"{level}_{name}.glb")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in coll.objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(coll.objects), None)
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True, export_extras=True,
                              export_image_format="NONE", export_materials="EXPORT", export_yup=True,
                              export_apply=False, export_lights=False, export_cameras=False,
                              export_texcoords=True, export_normals=True, export_tangents=False,
                              export_vertex_color="ACTIVE", export_animations=False)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    level = argv[0] if argv else "hub"
    only = argv[argv.index("--sector") + 1] if "--sector" in argv else None
    t0 = time.time()
    plan = run_plan(level)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = level
    scene.unit_settings.system = "METRIC"
    root = bpy.data.collections.new("Level")
    scene.collection.children.link(root)
    prev = bpy.data.collections.new("Preview")
    scene.collection.children.link(prev)
    stats = {}
    names = [s["name"] for s in plan["sectors"]]
    if only and only not in names:
        raise SystemExit(f"no sector {only!r}; sectors: {', '.join(names)}")
    for sec in plan["sectors"]:
        if only and sec["name"] != only:
            continue
        ts = time.time()
        coll, made, ents = build_sector(sec, root)
        tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in made)
        out = export_sector(level, sec["name"], coll)
        stats[sec["name"]] = {"triangles": tris, "objects": len(made), "entities": len(ents),
                              "lights": sum(1 for e in sec["entities"] if e.get("preview")),
                              "seconds": round(time.time() - ts, 1), "glb": os.path.relpath(out, ROOT)}
        print(f"[undercity] {sec['name']}: {tris} triangles, {len(made)} objects, {len(ents)} entities -> {out}")
    if not only:
        blend = os.path.join(HERE, f"undercity_{level}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend, relative_remap=True, compress=True)
        print("[undercity] saved", blend)
    print("[undercity] stats " + json.dumps(stats))
    print(f"[undercity] total {sum(s['triangles'] for s in stats.values())} triangles, "
          f"{plan['stats']['_lights']} lights, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()

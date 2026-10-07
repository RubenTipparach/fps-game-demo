"""The hub's parked vehicles, converted from the pinned CC0 pack (GGBotNet's PSX Style Cars) by the
prop kit's conventions.

Run (the pack first, then the conversion):
  python3 tools/deps/fetch_character_tools.py --only psx_style_cars
  blender -b --factory-startup -P tools/blender/build_vehicles_cc0.py
Writes, for every variant in tools/blender/vehicles.json:
  game/models/undercity/props/vehicle_<id>.glb          the body in its colour, with its collision
  game/models/undercity/props/vehicle_<id>.glb.import   its import preset (tools/godot/import_presets.py)
  game/textures/vehicles/psx/<id>.png (+ .import)       the pack's own texture, copied byte for byte
  game/materials/props/veh_psx_<id>.tres                its material: the texture, filtered bilinearly
  game/textures/vehicles/psx/SOURCE.md                  where every file came from

It lives in tools/blender because a model is a file built by a committed script (CLAUDE.md 6.1),
and it is separate from the prop kit (build_undercity_props.py) because it converts a mesh
someone else made rather than modelling one: it reads the pack only through
tools/deps/fetch_character_tools.py, which refuses a download whose SHA-256 differs from its pin
(openspec/changes/archive/2026-09-30-cc0-vehicles, design section 4). The pack's .blend files, pinned by hash, are
the editable source; the repository keeps the table, this script and what it writes (CLAUDE.md 13).

What a converted vehicle is (the prop kit's brief, build_undercity_props.py):
  * Metres; x right, y front, z up. The front faces +Y, which the glTF export turns into Godot -Z.
    The pack's cars face -Y, so each turns 180 degrees about z.
  * One scale for the pack, from its wheel: the pack's one wheel (Wheel/Wheel.blend) is wheel_d_m
    across. Each body keeps its own proportions, and its length must be the table's to 1 cm.
  * The origin is the floor centre of the footprint: the lowest point on z 0, the box's middle on
    x and y.
  * Its material is "veh_psx_<id>", the pack's texture filtered bilinearly with mipmaps (owner O8,
    "smudge those textures"), and a clear coat for the rain (openspec/changes/archive/2026-09-30-vehicle-fixes, design
    section 3.2).
  * Collision is a "BodyCollision-colonly" object of plain boxes: the lower body over the whole
    footprint up to the belt line, and the cabin above it, both read from the mesh.
  * Checks: the triangle budget, and no two faces of the mesh coplanar, facing the same way and
    overlapping (detailing.coplanar_triangle_report, CLAUDE.md 7.2).
  * Provenance: the pack, author, licence, page, SHA-256 and source files, in the glb's node
    extras and in SOURCE.md beside the textures (CLAUDE.md 5.6).
"""
import math
import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import GAME, G  # noqa: E402
from build_props import Kit, export, reset  # noqa: E402  (also puts tools/godot on sys.path)

import detailing  # noqa: E402  (tools/godot: the z-fighting checks)
import import_presets  # noqa: E402  (tools/godot: the one writer of .glb.import presets)
import vehicle_data  # noqa: E402  (tools/blender/vehicles.json, validated)
from vehicle_data import deps  # noqa: E402  (tools/deps/fetch_character_tools.py: the pinned packs)

sys.path.insert(0, os.path.join(GAME, "..", "tools", "material_maker"))
import postprocess  # noqa: E402  (the one writer of texture import presets)

MAT_DIR = os.path.join(GAME, "materials", "props")
TEX_RES = "res://textures/vehicles/psx"
STATIC = 2                      # Godot's meshes/light_baking: static lightmaps (parked cars bake with the level)
MEND_MAX_M = 0.005              # the furthest the converter moves a vertex to end a coplanar overlap (a sliver)
BONNET = 0.2                    # the belt line is the highest point within this share of the length from the front
LINEAR_WITH_MIPMAPS = 3         # Godot's BaseMaterial3D.texture_filter: bilinear, mipmapped (owner O8)


def material_name(variant_id):
    return f"veh_psx_{variant_id}"


def unpacked(pack):
    """The pinned pack, verified and extracted into the cache (never into the repository)."""
    return deps.unpack(pack, os.path.join(deps.cache_dir(), "unpacked", pack["id"]))


def pack_file(root, rel):
    """A file of the pack by its table path. The pack's own blends name some textures in another
    case than the files have, so the table's paths are the files' and are checked here."""
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        raise SystemExit(f"[vehicles_cc0] {rel}: not in the pack at {root}")
    return path


def load_mesh(path):
    """The one mesh object in a pack .blend, as a new mesh with its object's transform applied."""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    meshes = [o for o in dst.objects if o is not None and o.type == "MESH"]
    if len(meshes) != 1:
        raise SystemExit(f"[vehicles_cc0] {path}: expected one mesh, found {[o.name for o in meshes]}")
    if meshes[0].parent is not None:
        raise SystemExit(f"[vehicles_cc0] {path}: {meshes[0].name} has a parent; expected a loose mesh")
    me = meshes[0].data.copy()
    me.transform(meshes[0].matrix_basis)            # its own transform: matrix_world is unset outside a scene
    for o in dst.objects:
        if o is not None:
            bpy.data.objects.remove(o)
    return me


def bounds(me):
    xs, ys, zs = zip(*(v.co for v in me.vertices))
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def pack_scale(table, root):
    """Metres per pack unit: the wheel's real diameter over its diameter in the pack (the larger
    of its extents across the axle)."""
    me = load_mesh(pack_file(root, table["wheel_blend"]))
    lo, hi = bounds(me)
    size = sorted(hi - lo)
    bpy.data.meshes.remove(me)
    return table["wheel_d_m"] / size[2], size[2]


def body_mesh(table, root, name, scale):
    """A body in the kit's frame: turned to face +Y, scaled, its footprint centred and its lowest
    point on the floor; refused if its length isn't the table's."""
    body = table["bodies"][name]
    me = load_mesh(pack_file(root, body["blend"]))
    me.transform(Matrix.Scale(scale, 4) @ Matrix.Rotation(math.pi, 4, "Z"))
    lo, hi = bounds(me)
    me.transform(Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)))
    length = hi.y - lo.y
    if abs(length - body["length_m"]) > 0.01:
        raise SystemExit(f"[vehicles_cc0] {name}: {length:.3f} m long at the pack's scale, the table says "
                         f"{body['length_m']:g} m; the pack changed or the table is wrong")
    return me


def collision_boxes(me):
    """The lower body over the whole footprint up to the belt line, and the cabin above it: the
    belt line is the bonnet's highest point (every body has one; an estate's roof runs to its
    tail), and the cabin is the box of every point above it."""
    lo, hi = bounds(me)
    belt = max(v.co.z for v in me.vertices if v.co.y > hi.y - BONNET * (hi.y - lo.y))
    boxes = [((lo.x, lo.y, 0.0), (hi.x, hi.y, belt))]
    above = [v.co for v in me.vertices if v.co.z > belt + 0.05]
    if above:
        xs, ys, zs = zip(*above)
        boxes.append(((min(xs), min(ys), belt), (max(xs), max(ys), hi.z)))
    return boxes


def triangles(me):
    """The mesh's triangles as Blender tessellates them (the glTF export's), in metres, with the
    polygon each came from."""
    me.calc_loop_triangles()
    return [(tuple(me.vertices[i].co for i in t.vertices), t.polygon_index) for t in me.loop_triangles]


def mend_slivers(me, name):
    """Move each vertex that pokes into a coplanar face of the same facing onto that face's nearest
    edge, so the pair no longer overlaps (the pack's Car 5 laps its bumper's underside by 1.3 mm).
    A move is a repair, not a remodel: over MEND_MAX_M is refused. Returns the moves made."""
    moves = []
    for _ in range(4):                                  # a move can uncover another; a few passes settle it
        tris = triangles(me)
        pairs = detailing.coplanar_triangle_report([t for t, _ in tris])
        if not pairs:
            return moves
        for i, j in pairs:
            for a, b in ((i, j), (j, i)):
                face = [Vector(c) for c in tris[a][0]]
                n = (face[1] - face[0]).cross(face[2] - face[0]).normalized()
                for vi in me.polygons[tris[b][1]].vertices:
                    co = me.vertices[vi].co
                    edges = [(face[k], face[(k + 1) % 3]) for k in range(3)]
                    inside = min((co - p0).cross(p1 - p0).dot(-n) / (p1 - p0).length for p0, p1 in edges)
                    if inside <= 0.0005:                # on or outside every edge
                        continue
                    to = min((p0 + (p1 - p0) * max(0.0, min(1.0, (co - p0).dot(p1 - p0) / (p1 - p0).length_squared))
                              for p0, p1 in edges), key=lambda q: (q - co).length)
                    to += (to - co).normalized() * 0.0005
                    if (to - co).length > MEND_MAX_M:
                        raise SystemExit(f"[vehicles_cc0] {name}: a vertex at {tuple(round(c, 3) for c in co)} sits "
                                         f"{(to - co).length * 1000:.1f} mm inside a coplanar face; over {MEND_MAX_M * 1000:g} mm "
                                         f"is a modelling fault, not a sliver")
                    moves.append((tuple(round(c, 4) for c in co), round((to - co).length * 1000, 2)))
                    me.vertices[vi].co = to
    raise SystemExit(f"[vehicles_cc0] {name}: coplanar overlaps remain after mending: {detailing.coplanar_triangle_report([t for t, _ in triangles(me)])}")


def blender_material(name, texture):
    """The Blender side of the material: the committed texture, bilinear, so the contact sheet
    draws what Godot will. The game's material is the .tres (write_tres)."""
    m = bpy.data.materials.new(name)
    if hasattr(m, "use_nodes") and not m.use_nodes:
        m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(texture, check_existing=True)
    tex.interpolation = "Linear"
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def write_tres(name, variant_id, look):
    """game/materials/props/veh_psx_<id>.tres: the pack's texture, bilinear with mipmaps, and the
    table's roughness and clear coat. No emission: the pack paints its lamps unlit."""
    text = "\n".join([
        '[gd_resource type="StandardMaterial3D" format=3]', "",
        f'[ext_resource type="Texture2D" path="{TEX_RES}/{variant_id}.png" id="1"]', "",
        "[resource]",
        f'resource_name = "{name}"',
        f"texture_filter = {LINEAR_WITH_MIPMAPS}",
        'albedo_texture = ExtResource("1")',
        "metallic = 0.0",
        f"roughness = {look['roughness']}",
        "clearcoat_enabled = true",
        f"clearcoat = {look['clearcoat']}",
        f"clearcoat_roughness = {look['clearcoat_roughness']}",
    ]) + "\n"
    os.makedirs(MAT_DIR, exist_ok=True)
    with open(os.path.join(MAT_DIR, name + ".tres"), "w") as f:
        f.write(text)


def provenance(pack, table, v):
    """What the glb records of where it came from (its Body node's extras)."""
    return {"source_pack": pack["id"], "source_name": pack["name"], "source_author": pack["author"],
            "source_licence": pack["licence"], "source_page": pack["page"], "source_sha256": pack["sha256"],
            "source_blend": table["bodies"][v["body"]]["blend"], "source_texture": v["texture"]}


def write_source_md(pack, table, scale, wheel_units):
    rows = "\n".join(f"| `{v['id']}.png` | `{v['texture']}` | `{table['bodies'][v['body']]['blend']}` |"
                     for v in table["variants"])
    text = f"""# Where these textures came from

Written by `tools/blender/build_vehicles_cc0.py`; don't edit by hand.

- Pack: {pack['name']}
- Author: {pack['author']}
- Licence: {pack['licence']} ({pack['licence_stated_in']})
- Page: {pack['page']}
- Download: {pack['url']}
- SHA-256: `{pack['sha256']}` ({pack['size_bytes']} bytes), pinned in `tools/deps/vehicle_packs.json`
- Scale: the pack's wheel is {wheel_units:.4f} units across, a {table['wheel_d_m']:g} m wheel, so {scale:.5f} m per unit

Each texture is the pack's file copied byte for byte. Each model, `game/models/undercity/props/vehicle_<id>.glb`,
is the body's mesh from the blend, turned to face +Y and scaled.

| File | Pack texture | Pack body |
|---|---|---|
{rows}
"""
    with open(os.path.join(vehicle_data.TEXTURES, "SOURCE.md"), "w") as f:
        f.write(text)


def build(table, pack, root, body_name, me, v):
    """One variant: its texture copied, its material written, its glb and import preset exported."""
    tex = vehicle_data.texture_path(v["id"])
    shutil.copyfile(pack_file(root, v["texture"]), tex)
    postprocess.write_import(vehicle_data.TEXTURES, os.path.basename(tex), lossless=True, res_dir=TEX_RES)
    name = material_name(v["id"])
    write_tres(name, v["id"], table["material"])
    coll = bpy.data.collections.new(f"vehicle_{v['id']}")
    bpy.context.scene.collection.children.link(coll)
    body_me = me.copy()
    body_me.name = "Body"
    body_me.materials.clear()
    body_me.materials.append(blender_material(name, tex))
    body = bpy.data.objects.new("Body", body_me)
    coll.objects.link(body)
    for k, val in provenance(pack, table, v).items():
        body[k] = val
    c = Kit("BodyCollision", coll)
    for lo, hi in collision_boxes(me):
        c.box(G(lo), G(hi), "rubber", bevel=0.0)
    col = c.finish("BodyCollision-colonly")
    rel = f"models/undercity/props/vehicle_{v['id']}.glb"
    export([body, col], os.path.join(GAME, rel))
    import_presets.write(rel, STATIC, 0.05, "res://addons/brushfire_tools/prop_import.gd")
    for o in (body, col):                   # Blender names are global: the next variant's keep theirs
        o.name = o.data.name = f"vehicle_{v['id']}:{o.name}"


def main():
    reset()
    bpy.context.scene.name = "VehiclesCC0"
    table = vehicle_data.load()
    pack = deps.pack_by_id(table["pack"])
    root = unpacked(pack)
    scale, wheel_units = pack_scale(table, root)
    os.makedirs(vehicle_data.TEXTURES, exist_ok=True)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []     # variant id prefixes, to build a few
    for body_name, body in table["bodies"].items():
        variants = [v for v in table["variants"] if v["body"] == body_name
                    and (not only or any(v["id"].startswith(o) for o in only))]
        if not variants:
            continue
        me = body_mesh(table, root, body_name, scale)
        mended = mend_slivers(me, body_name)
        tris = [t for t, _ in triangles(me)]
        if len(tris) >= table["budget_tris"]:
            raise SystemExit(f"[vehicles_cc0] {body_name}: {len(tris)} triangles, over the {table['budget_tris']} budget")
        flush = detailing.coplanar_triangle_report(tris)
        if flush:
            polys = [p for _, p in triangles(me)]
            raise SystemExit(f"[vehicles_cc0] {body_name}: z-fighting: {len(flush)} coplanar overlapping triangle pairs: "
                             + "; ".join(f"polygons {polys[i]} and {polys[j]} at {tuple(round(c, 3) for c in tris[i][0])}"
                                         for i, j in flush[:6]))
        lo, hi = bounds(me)
        print(f"[vehicles_cc0] {body_name}: {len(tris)} triangles, {hi.y - lo.y:.3f} x {hi.x - lo.x:.3f} x "
              f"{hi.z:.3f} m, collision {len(collision_boxes(me))} boxes, slivers mended {mended}, "
              f"variants {[v['id'] for v in variants]}")
        for v in variants:
            build(table, pack, root, body_name, me, v)
    if not only:
        write_source_md(pack, table, scale, wheel_units)
    bad = vehicle_data.committed_problems(table) if not only else []
    if bad:
        raise SystemExit("[vehicles_cc0] " + "; ".join(bad))
    print(f"[vehicles_cc0] scale {scale:.5f} m per unit (the wheel {wheel_units:.4f} units, {table['wheel_d_m']:g} m)")


if __name__ == "__main__":
    main()

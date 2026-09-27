"""Shared helpers for the Blender level/prop build scripts (Godot <-> Blender axes, materials
that preview the game's Material Maker textures, bmesh primitives with per-face materials,
world-aligned UV projection at the texel density from materials.json)."""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.path.join(ROOT, "game")
MANIFEST = json.load(open(os.path.join(GAME, "materials", "materials.json")))
TILES = {k: v.get("tile_m", 2.0) for k, v in MANIFEST.items() if isinstance(v, dict)}


def B(x, y, z):
    """Godot (x right, y up, -z north) -> Blender (x right, y north, z up). glTF export maps it back."""
    return Vector((x, -z, y))


# ----------------------------------------------------------------------------- scene setup

def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    if hasattr(m, "use_nodes") and not m.use_nodes:
        m.use_nodes = True
    tex_dir = os.path.join(GAME, "textures")  # made relative to the .blend on save
    albedo = os.path.join(GAME, "textures", name + ".png")
    if name == "crate_large":
        albedo = os.path.join(GAME, "textures", "crate.png")
    if not os.path.exists(albedo):
        return m
    base = os.path.basename(albedo)[:-4]
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    # Viewport preview uses the same Material Maker textures the game uses.
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(tex_dir, base + ".png"), check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(os.path.join(tex_dir, base + "_orm.png"), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nrm_img = nt.nodes.new("ShaderNodeTexImage")
    nrm_img.image = bpy.data.images.load(os.path.join(tex_dir, base + "_normal.png"), check_existing=True)
    nrm_img.image.colorspace_settings.name = "Non-Color"
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nrm_img.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    emission = os.path.join(GAME, "textures", base + "_emission.png")
    if os.path.exists(emission):
        e = nt.nodes.new("ShaderNodeTexImage")
        e.image = bpy.data.images.load(os.path.join(tex_dir, base + "_emission.png"), check_existing=True)
        nt.links.new(e.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = MANIFEST.get(base, {}).get("emission_energy", 1.0)
    return m


def mesh_object(name, bm, coll, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(material(m))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------- brush helpers

def box_bm(lo, hi, mats_by_dir, skip=()):
    """lo/hi in Godot coordinates. mats_by_dir: index per 'floor','ceiling','wall' (as seen from
    inside a carved room: the cutter's bottom face becomes the floor)."""
    bm = bmesh.new()
    a, b = B(*lo), B(*hi)
    mn = Vector((min(a.x, b.x), min(a.y, b.y), min(a.z, b.z)))
    mx = Vector((max(a.x, b.x), max(a.y, b.y), max(a.z, b.z)))
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((mn.x if v.co.x < 0 else mx.x, mn.y if v.co.y < 0 else mx.y, mn.z if v.co.z < 0 else mx.z))
    bm.normal_update()
    dead = []
    for f in bm.faces:
        n = f.normal
        if n.z < -0.9:
            key = "bottom"
        elif n.z > 0.9:
            key = "top"
        else:
            key = "side"
        f.material_index = mats_by_dir[key]
        if key in skip:
            dead.append(f)
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="FACES")
    return bm


def cylinder_bm(center, radius, length, axis, side_index, cap_index, segments=32, caps=True, smooth=True):
    """Cylinder in Godot coordinates; axis in {'x','y','z'} (Godot axes)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segments, radius1=radius, radius2=radius,
                          depth=length)
    # created along Blender Z; rotate to the requested Godot axis
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    elif axis == "z":  # Godot Z = Blender -Y
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=B(*center))
    bm.normal_update()
    axis_vec = {"x": Vector((1, 0, 0)), "y": Vector((0, 0, 1)), "z": Vector((0, 1, 0))}[axis]
    for f in bm.faces:
        is_cap = abs(f.normal.dot(axis_vec)) > 0.9
        f.material_index = cap_index if is_cap else side_index
        f.smooth = smooth and not is_cap
    return bm


def world_uv(co, n, tile):
    ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
    if az >= ax and az >= ay:
        u, v = co.x, co.y if n.z > 0 else -co.y
    elif ax >= ay:
        u, v = (co.y if n.x > 0 else -co.y), co.z
    else:
        u, v = (-co.x if n.y > 0 else co.x), co.z
    return (u / tile, v / tile)


def project_uvs(me, space_matrix=None):
    """Box-project UVs for every face using its material's tile size (metres per repeat)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    bm.normal_update()
    for f in bm.faces:
        mat = me.materials[f.material_index].name if f.material_index < len(me.materials) else ""
        tile = TILES.get(mat.split(".")[0], 2.0)
        n = f.normal if space_matrix is None else (space_matrix.to_3x3() @ f.normal).normalized()
        for loop in f.loops:
            co = loop.vert.co if space_matrix is None else space_matrix @ loop.vert.co
            loop[uv].uv = world_uv(co, n, tile)
    bm.to_mesh(me)
    bm.free()


def world_uv_nodegroup():
    """Geometry Nodes group that writes world-aligned UVs (same projection and per-material tile
    sizes as project_uvs), so the live boolean level previews correctly in Blender."""
    ng = bpy.data.node_groups.get("WorldUV")
    if ng:
        return ng
    ng = bpy.data.node_groups.new("WorldUV", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, Lk = ng.nodes, ng.links

    def node(kind, x, y, **attrs):
        n = N.new(kind)
        n.location = (x, y)
        for k, v in attrs.items():
            setattr(n, k, v)
        return n

    def math(op, a, b=None, x=0, y=0):
        n = node("ShaderNodeMath", x, y, operation=op)
        Lk.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, (int, float)):
                n.inputs[1].default_value = b
            else:
                Lk.new(b, n.inputs[1])
        return n.outputs[0]

    gin = node("NodeGroupInput", -1400, 0)
    gout = node("NodeGroupOutput", 900, 0)
    pos = node("GeometryNodeInputPosition", -1400, -200)
    nrm = node("GeometryNodeInputNormal", -1400, -400)
    sp = node("ShaderNodeSeparateXYZ", -1200, -200)
    sn = node("ShaderNodeSeparateXYZ", -1200, -400)
    Lk.new(pos.outputs[0], sp.inputs[0])
    Lk.new(nrm.outputs[0], sn.inputs[0])
    px, py, pz = sp.outputs[0], sp.outputs[1], sp.outputs[2]
    nx, ny, nz = sn.outputs[0], sn.outputs[1], sn.outputs[2]
    ax, ay, az = math("ABSOLUTE", nx), math("ABSOLUTE", ny), math("ABSOLUTE", nz)

    def ge(a, b):
        n = node("FunctionNodeCompare", -800, -600, data_type="FLOAT", operation="GREATER_EQUAL")
        Lk.new(a, n.inputs[0])
        Lk.new(b, n.inputs[1])
        return n.outputs[0]
    band = node("FunctionNodeBooleanMath", -600, -600, operation="AND")
    Lk.new(ge(az, ax), band.inputs[0])
    Lk.new(ge(az, ay), band.inputs[1])
    z_dom = band.outputs[0]
    x_dom = ge(ax, ay)

    def combine(u, v):
        n = node("ShaderNodeCombineXYZ", -400, -800)
        Lk.new(u, n.inputs[0])
        Lk.new(v, n.inputs[1])
        return n.outputs[0]
    uv_z = combine(px, math("MULTIPLY", py, math("SIGN", nz)))
    uv_x = combine(math("MULTIPLY", py, math("SIGN", nx)), pz)
    uv_y = combine(math("MULTIPLY", math("MULTIPLY", px, -1.0), math("SIGN", ny)), pz)

    def switch(kind, cond, false, true):
        n = node("GeometryNodeSwitch", -200, -600, input_type=kind)
        Lk.new(cond, n.inputs[0])
        for sock, val in ((n.inputs[1], false), (n.inputs[2], true)):
            if isinstance(val, (int, float)):
                sock.default_value = val
            else:
                Lk.new(val, sock)
        return n.outputs[0]
    uv = switch("VECTOR", z_dom, switch("VECTOR", x_dom, uv_y, uv_x), uv_z)

    tile = None
    for i, (name, t) in enumerate(sorted(TILES.items())):
        sel = node("GeometryNodeMaterialSelection", -600, 400 + i * 120)
        sel.inputs["Material"].default_value = material(name)
        tile = switch("FLOAT", sel.outputs[0], 2.0 if tile is None else tile, float(t))
    scale = node("ShaderNodeVectorMath", 200, -600, operation="SCALE")
    Lk.new(uv, scale.inputs[0])
    Lk.new(math("POWER", tile, -1.0), scale.inputs["Scale"])
    store = node("GeometryNodeStoreNamedAttribute", 600, 0, data_type="FLOAT2", domain="CORNER")
    store.inputs["Name"].default_value = "UVMap"
    Lk.new(gin.outputs[0], store.inputs["Geometry"])
    Lk.new(scale.outputs[0], store.inputs["Value"])
    Lk.new(store.outputs[0], gout.inputs[0])
    return ng


def add_world_uv(ob):
    m = ob.modifiers.new("WorldUV", "NODES")
    m.node_group = world_uv_nodegroup()
    return m


def export_level(glb):
    """Export a level .blend that follows the conventions (object "Shell" with the boolean
    modifier, collections "Detail" and "Entities") to a Godot-ready .glb."""
    shell = bpy.data.objects["Shell"]
    deps = bpy.context.evaluated_depsgraph_get()
    export_coll = collection("Export")
    parts = []
    for ob in [shell] + list(bpy.data.collections["Detail"].objects):
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
        me.transform(ob.matrix_world)
        tmp = bpy.data.objects.new(ob.name + "_x", me)
        export_coll.objects.link(tmp)
        parts.append(tmp)

    # Cull the outside of the shell: nobody sees it, no lightmap texels for it.
    sh = parts[0].data
    bm = bmesh.new()
    bm.from_mesh(sh)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    lo, hi = Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))
    dead = []
    for f in bm.faces:
        for i in range(3):
            if all(abs(v.co[i] - lo[i]) < 1e-3 for v in f.verts) or all(abs(v.co[i] - hi[i]) < 1e-3 for v in f.verts):
                dead.append(f)
                break
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    bm.to_mesh(sh)
    bm.free()

    # Join everything into one static mesh.
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    level = bpy.context.view_layer.objects.active
    level.name = "Level-col"

    # World-aligned UVs at each material's texel density.
    me = level.data
    project_uvs(me)
    for i, m in enumerate(me.materials):  # the exporter needs the Blender names to be clean
        if "." in m.name:
            me.materials[i] = bpy.data.materials.get(m.name.split(".")[0]) or m

    bpy.ops.object.select_all(action="DESELECT")
    level.select_set(True)
    for e in bpy.data.collections["Entities"].objects:
        e.select_set(True)
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True, export_extras=True,
                              export_image_format="NONE", export_materials="EXPORT", export_yup=True,
                              export_apply=False, export_lights=False, export_cameras=False,
                              export_texcoords=True, export_normals=True, export_tangents=False,
                              export_animations=False)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    print(f"[cistern] exported {glb}: ~{tris} triangles, {len(me.materials)} materials")

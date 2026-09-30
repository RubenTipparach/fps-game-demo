"""Contact sheet of Undercity's prop kit, rendered from the exported .glb files.

It owns the picture that shows the prop models: every prop in a row on a wet street floor at
night, then one close view per prop with its name and triangle count, plus the barrier's arm
raised and the door leaf swung open the way the game turns them (barrier.tscn lifts "arm" 80
degrees about Godot Z; door.tscn swings the hinge about Godot Y). It imports the committed
game/models/undercity/props/<name>.glb files, not undercity_props.blend, so the sheet and the
printed pivots check what the game loads (CLAUDE.md 5.6, validate the real artifact).

Run:  blender -b --factory-startup -P tools/blender/render_undercity_props.py [-- vehicles]
Writes docs/screenshots/undercity/props_sheet.png and prints each moving part's pivot; with
"vehicles", the parked vehicles' sheet instead (openspec/changes/street-vehicles, task 2.3),
docs/screenshots/street_vehicles/vehicles_sheet.png.
"""
import math
import os
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_undercity_props as kit  # noqa: E402
from blendkit import GAME, ROOT  # noqa: E402

# The two sheets: which props each shows, where it goes and its title.
SHEETS = {
    "props": (lambda name: not name.startswith("vehicle_"),
              os.path.join(ROOT, "docs", "screenshots", "undercity", "props_sheet.png"), "undercity prop kit"),
    "vehicles": (lambda name: name.startswith("vehicle_"),
                 os.path.join(ROOT, "docs", "screenshots", "street_vehicles", "vehicles_sheet.png"), "parked vehicles"),
}
CELL_W, CELL_H, LABEL_H, COLS = 480, 400, 34, 4
STRIP_W, STRIP_H = CELL_W * COLS, 300
WALL_Y = -0.5            # the back wall's face: wall-mounted props hang on it
GAP = 0.6                # between props in the row, metres
# Where a prop stands in the row when it isn't on the floor: (height of its origin, on the wall).
MOUNT = {"wall_panel": (1.3, True), "grate": (0.1, True)}
# The game's open poses (barrier.tscn, LockedDoor.cs), as Blender rotations of the moving node
# (Godot Z = Blender -Y, Godot Y = Blender Z), each with the direction the camera looks from.
POSES = {"barrier": ("arm", (0.0, -80.0, 0.0), "arm raised", (0.2, 1.0, 0.35)),
         "door_leaf": ("Leaf", (0.0, 0.0, 95.0), "open", (1.0, 0.35, 0.45))}


def setup():
    """An empty EEVEE scene with a night sky colour."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 32
    sc.eevee.use_raytracing = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.resolution_percentage = 100
    world = bpy.data.worlds.new("Night")
    sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.008, 0.011, 0.022, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    return sc


def light(name, kind, color, energy, loc=(0, 0, 0), rot=(0, 0, 0), size=1.0):
    """A light object; rot in degrees."""
    data = bpy.data.lights.new(name, kind)
    data.color, data.energy = color, energy
    if kind == "AREA":
        data.size = size
    elif kind == "SUN":
        data.angle = math.radians(2.0)
    ob = bpy.data.objects.new(name, data)
    ob.location, ob.rotation_euler = loc, [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(ob)
    return ob


def aim(ob, target):
    """Point a camera or light (looking down its -Z) at target."""
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


def slab(name, lo, hi, mat, tile=4.0):
    """A box with world UVs (floor, wall, trim), for the set around the props."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(tuple(lo[i] if v.co[i] < 0 else hi[i] for i in range(3)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    uv = me.uv_layers.new()
    for poly in me.polygons:
        n = poly.normal
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.5:
                uv.data[li].uv = (co.x / tile, co.y / tile)
            elif abs(n.y) > 0.5:
                uv.data[li].uv = (co.x / tile, co.z / tile)
            else:
                uv.data[li].uv = (co.y / tile, co.z / tile)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def wet(name, base, darken, roughness):
    """A darkened, glossy copy of a Material Maker preview: rain-wet street surfaces."""
    m = kit.preview_material(base).copy()
    m.name = name
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    src = bsdf.inputs["Base Color"].links[0].from_socket
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    nt.links.new(src, mul.inputs[0])
    mul.inputs[1].default_value = (darken, darken, darken)
    nt.links.new(mul.outputs[0], bsdf.inputs["Base Color"])
    for link in list(bsdf.inputs["Roughness"].links):
        nt.links.remove(link)
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def emissive(name, rgb, strength):
    """A plain glowing material for the set's neon tubes."""
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def import_prop(name):
    """Import one prop's .glb; returns its top-level objects (children follow their parents)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GAME, "models", "undercity", "props", name + ".glb"))
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        o.rotation_mode = "XYZ"
        if "Collision" in o.name:
            o.hide_render = True
    return objs


def remap_materials(imported):
    """Swap the glTF importer's untextured materials for the game-material previews, by name."""
    for m in imported:
        m.name = "gltf:" + m.name
    for o in bpy.data.objects:
        if o.type == "MESH":
            for slot in o.material_slots:
                if slot.material and slot.material.name.startswith("gltf:"):
                    slot.material = kit.preview_material(slot.material.name[5:].split(".")[0])


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" and not o.hide_render for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def godot(v):
    """Blender (x, y, z) -> Godot (x, y up, z back): what the node reads after import."""
    return (round(v.x, 4) + 0.0, round(v.z, 4) + 0.0, round(-v.y, 4) + 0.0)


def report(name, objs):
    """Print each node, its parent and its origin in Godot axes; moving parts must have an
    identity rotation so the game's rotation is about the pivot's own axes."""
    for o in objs:
        if o.type != "MESH":
            continue
        parent = o.parent.name if o.parent else "(root)"
        rot = tuple(round(math.degrees(a), 3) for a in o.rotation_euler)
        print(f"[props_sheet] {name}: {o.name:<26} parent {parent:<8} origin (Godot) {godot(o.matrix_world.translation)}"
              f" rotation {rot}")


def frame(lo, hi, view, lens, margin=1.08):
    """Distance along `view` from the box's centre at which a camera with this lens (36 mm sensor
    across CELL_W) sees every corner of the box."""
    c = (lo + hi) / 2
    back = -view.normalized()
    right = back.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(back)
    tan_x = 18.0 / lens
    tan_y = tan_x * CELL_H / CELL_W
    d = 0.0
    for i in range(8):
        p = Vector(tuple((hi if i >> k & 1 else lo)[k] for k in range(3))) - c
        toward = p.dot(view)                  # how much nearer the camera the corner is
        d = max(d, toward + abs(p.dot(right)) / tan_x, toward + abs(p.dot(up)) / tan_y)
    return d * margin


def render(sc, path, w, h):
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return kit.load_png(path)


def label(img, text):
    """The cell's name strip under the picture, in the kit's pixel font."""
    strip = np.zeros((LABEL_H, img.shape[1], 3), np.float32) + np.array((0.05, 0.06, 0.09), np.float32)
    m = kit.text_mask(text, 3)
    kit.stamp(strip, m, (LABEL_H - m.shape[0]) // 2, 12, (0.55, 0.9, 1.0))
    return np.concatenate([img, strip], 0)


def main():
    """Import, lay out, light and render the row and every cell, then compose the sheet."""
    which = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "props"
    shows, out, title = SHEETS[which]
    sc = setup()
    props = {}
    for name in kit.PROPS:
        if shows(name):
            props[name] = import_prop(name)
    remap_materials(set(bpy.data.materials))

    # Lay the props out in a row, left to right as the camera sees it (toward -X, since the
    # props face +Y), each on the floor or on the back wall.
    x = 0.0
    tris = {}
    for name, objs in props.items():
        roots = [o for o in objs if o.parent is None]
        report(name, objs)
        lo, hi = bounds(objs)
        z, on_wall = MOUNT.get(name, (0.0, False))
        dy = WALL_Y - lo.y if on_wall else 0.0
        for o in roots:
            o.location += Vector((x - hi.x, dy, z))
        x -= (hi.x - lo.x) + GAP
        tris[name] = sum(len(p.vertices) - 2 for o in objs if o.type == "MESH" and not o.hide_render
                         for p in o.data.polygons)
    length = -x - GAP
    x0 = -length                         # the row spans x0..0

    # The set: a wet street, a brick back wall with a kerb, and neon tubes on the wall.
    slab("Floor", (x0 - 6, WALL_Y - 0.4, -0.2), (6, 12, 0.0), wet("wet_street", "concrete", 0.35, 0.18))
    slab("Wall", (x0 - 6, WALL_Y - 0.4, 0.0), (6, WALL_Y, 6.0), wet("wet_brick", "brick_wall", 0.45, 0.45),
         tile=2.0)
    for i, (rgb, at) in enumerate((((1.0, 0.15, 0.6), 0.25), ((0.1, 0.85, 1.0), 0.65))):
        a, b = x0 + length * at, x0 + length * at + 3.0
        slab(f"Neon{i}", (a, WALL_Y - 0.04 + 0.0, 3.1 + i * 0.25), (b, WALL_Y + 0.04, 3.16 + i * 0.25),
             emissive(f"neon{i}", rgb, 12.0))
        light(f"NeonGlow{i}", "AREA", rgb, 260.0, ((a + b) / 2, WALL_Y + 0.4, 3.1 + i * 0.25), (90, 0, 0), size=3.0)
    light("Moon", "SUN", (0.55, 0.65, 1.0), 0.35, rot=(55, 0, 25))
    lamps = [light(f"Sodium{i}", "AREA", (1.0, 0.72, 0.42), 700.0, (lx, 4.0, 5.0), size=1.2)
             for i, lx in enumerate(np.linspace(x0, 0, 5))]
    for lp in lamps:
        aim(lp, (lp.location.x, 0.0, 0.8))
    key = light("Key", "AREA", (1.0, 0.74, 0.46), 0.0, size=1.0)
    rim = light("Rim", "AREA", (0.85, 0.3, 1.0), 0.0, size=1.0)
    fill = light("Fill", "AREA", (0.3, 0.75, 1.0), 0.0, size=1.0)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tmp = tempfile.mkdtemp(prefix="props_sheet_")

    # 1. The whole row, orthographic, from the front and a little above.
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = length + 1.0
    cam.location = (x0 + length / 2, 30.0, 5.0)
    aim(cam, (x0 + length / 2, 0.0, 1.45))
    strip = render(sc, os.path.join(tmp, "row.png"), STRIP_W, STRIP_H)
    for lp in lamps:
        lp.data.energy = 0.0

    # 2. One close view per prop (and the two open poses), the others hidden.
    cam.data.type = "PERSP"
    cam.data.lens = 50.0
    shots = [(name, None) for name in props] + [(name, pose) for name, pose in POSES.items() if name in props]
    cells = []
    for name, pose in shots:
        for other, objs in props.items():
            for o in objs:
                o.hide_render = other != name or "Collision" in o.name
        moved = None
        if pose:
            moved = next(o for o in props[name] if o.name.split(".")[0] == pose[0])
            moved.rotation_euler = [math.radians(a) for a in pose[1]]
            bpy.context.view_layer.update()
        lo, hi = bounds(props[name])
        c = (lo + hi) / 2
        r = max((hi - lo).length / 2, 0.25)
        view = Vector(pose[3] if pose else (0.2, 1.0, 0.35) if name == "barrier" else (0.55, 1.0, 0.5)).normalized()
        cam.location = c + view * frame(lo, hi, view, cam.data.lens)
        aim(cam, c)
        key.location, key.data.energy, key.data.size = c + Vector((-1.2, 1.4, 1.6)) * r * 1.6, 380.0 * r * r, r
        rim.location, rim.data.energy, rim.data.size = c + Vector((1.6, -0.2, 1.2)) * r * 1.6, 200.0 * r * r, r
        fill.location, fill.data.energy, fill.data.size = c + Vector((1.2, 1.5, -0.2)) * r * 1.6, 60.0 * r * r, r
        for lt in (key, rim, fill):
            aim(lt, c)
        img = render(sc, os.path.join(tmp, f"{name}_{len(cells)}.png"), CELL_W, CELL_H)
        short = name.removeprefix("vehicle_")         # the sheet's title says they're vehicles
        text = short if not pose else f"{short} {pose[2]}"
        cells.append(label(img, f"{text}  {tris[name]} tris" if not pose else text))
        if moved:
            moved.rotation_euler = (0.0, 0.0, 0.0)

    rows = [np.concatenate(cells[i:i + COLS] + [np.zeros_like(cells[0])] * (COLS - len(cells[i:i + COLS])), 1)
            for i in range(0, len(cells), COLS)]
    sheet = np.concatenate([label(strip, f"{title}: {len(props)} models at night")] + rows, 0)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    kit.save_png(out, sheet)
    print("[props_sheet] wrote", out)


if __name__ == "__main__":
    main()

"""Doorway kit in the Quake 2 / Unreal 1 style, modelled in Blender.

Run:  blender -b --factory-startup -P tools/blender/build_props.py
Writes:
  tools/blender/props.blend                         editable source
  game/models/doorway/door_frame.glb                heavy tech door frame (static, lightmapped)
  game/models/doorway/door_leaves.glb               split sliding door leaves (LeafL, LeafR)
  game/models/doorway/arch_<w>x<h>.glb              framed archways for open passages

Sizes come from detailing.FRAMES: each frame is placed in a level opening of its "fits" size but
has a smaller clear opening, so its reveals stand proud of the walls and ceiling and never share
a plane with them (no z-fighting). Frames are 1.0 m deep plus pilasters, so they cover the wall
thickness of any of the three levels. Everything gets bevelled (chamfered) edges, world-
aligned UVs at the shared texel density and the game's material names, which the Godot import
settings map onto res://materials/*.tres.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import GAME, HERE, ROOT, B, box_bm, collection, cylinder_bm, material, project_uvs  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
from detailing import FRAMES  # noqa: E402  (shared frame sizes; the levels' z-fighting check uses them too)

OUT = os.path.join(GAME, "models", "doorway")


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.name = "Props"


class Kit:
    """Accumulates parts (with materials) into one object per exported piece."""

    def __init__(self, name, coll):
        self.name = name
        self.coll = coll
        self.parts = []

    def box(self, lo, hi, mat, bevel=0.03, skip=()):
        bm = box_bm(lo, hi, {"side": 0, "bottom": 0, "top": 0}, skip)
        self._add(bm, mat, bevel)

    def cyl(self, center, r, length, axis, mat, bevel=0.0, segments=16, caps=True):
        bm = cylinder_bm(center, r, length, axis, 0, 0, segments=segments, caps=caps)
        self._add(bm, mat, bevel)

    def wedge(self, pts, mat, bevel=0.0):
        """Convex hull of Godot-space points (for gussets, chamfer blocks, keystones)."""
        bm = bmesh.new()
        for p in pts:
            bm.verts.new(B(*p))
        bmesh.ops.convex_hull(bm, input=bm.verts)
        bm.normal_update()
        self._add(bm, mat, bevel)

    def _add(self, bm, mat, bevel):
        me = bpy.data.meshes.new(f"{self.name}_part")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(material(mat))
        ob = bpy.data.objects.new(f"{self.name}_part", me)
        self.coll.objects.link(ob)
        if bevel > 0:
            m = ob.modifiers.new("Bevel", "BEVEL")
            m.width = bevel
            m.segments = 1
            m.limit_method = "ANGLE"
            m.harden_normals = True
        self.parts.append(ob)

    def finish(self, name=None):
        """Apply modifiers, join parts into one object, project UVs. Returns the object."""
        deps = bpy.context.evaluated_depsgraph_get()
        objs = []
        for ob in self.parts:
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
            new = bpy.data.objects.new(ob.name + "_x", me)
            self.coll.objects.link(new)
            objs.append(new)
        for ob in self.parts:
            bpy.data.objects.remove(ob)
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = name or self.name
        ob.data.name = ob.name
        project_uvs(ob.data)
        return ob


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_extras=True,
                              export_image_format="NONE", export_materials="EXPORT", export_yup=True,
                              export_apply=False, export_lights=False, export_cameras=False,
                              export_texcoords=True, export_normals=True, export_tangents=False,
                              export_animations=False)
    print("[props] exported", path)


# ----------------------------------------------------------------------------- door frame

def door_frame(coll):
    f = FRAMES["doorway"]
    W, H, D = f["clear"][0] / 2, f["clear"][1], f["depth"]   # half clear width, clear height, half depth
    k = Kit("Frame", coll)
    for s in (-1, 1):
        x0, x1 = sorted((s * W, s * (W + 0.65)))
        # jamb block with a slot the leaf slides into, lined with hazard stripes
        k.box((x0, 0, -D), (x1, H + 0.1, D), "tech_panel", bevel=0.05)
        xi = s * (W - 0.012)
        k.box((min(xi, s * W), 0.25, -0.36), (max(xi, s * W), H - 0.1, -0.13), "hazard_stripes", bevel=0.0)
        k.box((min(xi, s * W), 0.25, 0.13), (max(xi, s * W), H - 0.1, 0.36), "hazard_stripes", bevel=0.0)
        k.box((min(xi, s * W) - 0.001, 0, -0.11), (max(xi, s * W) + 0.001, H, 0.11), "rubber", bevel=0.0)
        for f in (-1, 1):
            def Z(a, b):
                return sorted((f * a, f * b))
            # pilaster on each face: plinth, shaft, capital (classic Unreal mouldings). The shaft
            # stops 2 cm behind the lintel's face so the two never share a plane (z-fighting).
            px0, px1 = sorted((s * (W + 0.05), s * (W + 0.85)))
            z0, z1 = Z(D, D + 0.2)
            k.box((px0, 0, z0), (px1, 0.35, z1), "rust_metal", bevel=0.04)
            z0, z1 = Z(D, D + 0.12)
            k.box((px0 + 0.08, 0.35, z0), (px1 - 0.08, H + 0.05, z1), "tech_panel", bevel=0.04)
            z0, z1 = Z(D, D + 0.18)
            k.box((px0 - 0.03, H + 0.05, z0), (px1 + 0.03, H + 0.3, z1), "rust_metal", bevel=0.04)
            # hydraulic piston on the pilaster
            px = s * (W + 0.45)
            pz = f * (D + 0.24)
            k.cyl((px, 2.6, pz), 0.085, 0.9, "y", "gunmetal_light", segments=12)
            k.cyl((px, 1.3, pz), 0.04, 1.8, "y", "brass", segments=10)
            k.box((px - 0.12, 0.35, pz - 0.1), (px + 0.12, 0.47, pz + 0.1), "gunmetal", bevel=0.02)
            k.box((px - 0.12, 3.02, pz - 0.1), (px + 0.12, 3.12, pz + 0.1), "gunmetal", bevel=0.02)
            # corner gusset plates inside the opening (don't cross the leaf slot)
            zg0, zg1 = sorted((f * 0.18, f * (D - 0.02)))
            gx = s * W
            k.wedge([(gx, H - 0.45, zg0), (gx, H - 0.45, zg1), (gx, H, zg0), (gx, H, zg1),
                     (gx - s * 0.45, H, zg0), (gx - s * 0.45, H, zg1)], "rust_metal")
    # lintel with a chamfered underside and a sign plate on both faces
    k.box((-(W + 0.95), H, -(D + 0.14)), (W + 0.95, H + 1.0, D + 0.14), "tech_panel", bevel=0.07)
    k.box((-(W + 1.0), H + 0.9, -(D + 0.2)), (W + 1.0, H + 1.08, D + 0.2), "rust_metal", bevel=0.04)
    for f in (-1, 1):
        z0, z1 = sorted((f * (D + 0.14), f * (D + 0.19)))
        k.box((-1.05, H + 0.22, z0), (1.05, H + 0.78, z1), "gunmetal", bevel=0.02)
        z0, z1 = sorted((f * (D + 0.14), f * (D + 0.22)))
        k.box((-1.45, H + 0.02, z0), (1.45, H + 0.1, z1), "lamp_glow", bevel=0.0)   # downlight strip
    # threshold plate with the door track
    k.box((-(W + 0.1), 0, -D), (W + 0.1, 0.04, D), "diamond_plate", bevel=0.02, skip=("bottom",))
    k.box((-(W + 0.1), 0.0, -0.1), (W + 0.1, 0.05, 0.1), "rubber", bevel=0.0, skip=("bottom",))
    frame = k.finish("Frame")

    # status lights (separate object: the game swaps red/green as the door opens)
    s = Kit("Status", coll)
    for f in (-1, 1):
        z0, z1 = sorted((f * (D + 0.19), f * (D + 0.23)))
        s.box((-0.8, H + 0.42, z0), (0.8, H + 0.58, z1), "status_light", bevel=0.0)
    status = s.finish("Status")

    # simple collision: jambs + lintel (Godot builds a trimesh from the -colonly object)
    c = Kit("FrameCollision", coll)
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * W, sgn * (W + 0.85)))
        c.box((x0, 0, -(D + 0.14)), (x1, H + 0.1, D + 0.14), "tech_panel", bevel=0.0)
    c.box((-(W + 0.95), H, -(D + 0.14)), (W + 0.95, H + 1.0, D + 0.14), "tech_panel", bevel=0.0)
    col = c.finish("FrameCollision-colonly")
    export([frame, status, col], os.path.join(OUT, "door_frame.glb"))


def door_leaves(coll):
    """Two leaves meeting in the middle, each 1.5 x 3.2 x 0.2 m with raised panels."""
    out = []
    for name, s in (("LeafL", -1), ("LeafR", 1)):
        k = Kit(name, coll)

        def X(a, b):
            return sorted((s * a, s * b))
        # the slab and rib start 2 cm in from the meeting edge, behind the hazard strip, so their
        # end faces don't share its plane (visible z-fighting while the door is open)
        x0, x1 = X(0.02, 1.5)
        k.box((x0, 0.02, -0.08), (x1, 3.2, 0.08), "tech_panel", bevel=0.025)
        for f in (-1, 1):
            z0, z1 = sorted((f * 0.08, f * 0.115))
            for y0, y1 in ((0.3, 1.35), (1.8, 2.95)):
                px0, px1 = X(0.25, 1.3)
                k.box((px0, y0, z0), (px1, y1, z1), "tech_panel", bevel=0.02)
            rx0, rx1 = X(0.02, 1.5)
            k.box((rx0, 1.45, -0.125), (rx1, 1.7, 0.125), "rust_metal", bevel=0.02)
            vx0, vx1 = X(0.5, 1.0)
            k.box((vx0, 2.25, -0.13), (vx1, 2.4, 0.13), "rubber", bevel=0.01)
        hx0, hx1 = X(0.0, 0.14)
        k.box((hx0, 0.03, -0.1), (hx1, 3.19, 0.1), "hazard_stripes", bevel=0.01)
        out.append(k.finish(name))
    export(out, os.path.join(OUT, "door_leaves.glb"))


def archway(coll, kind):
    """Framed opening (no door): pilasters, capitals, a lintel with keystone and cornice."""
    frame = FRAMES[kind]
    w, h = frame["clear"]
    depth = frame["depth"]
    W = w / 2
    k = Kit("Arch", coll)
    for s in (-1, 1):
        # jamb from the (inset) clear opening back into the wall behind the level opening
        x0, x1 = sorted((s * W, s * (frame["fits"][0] / 2 + 0.5)))
        k.box((x0, 0, -depth), (x1, h, depth), "stone_blocks", bevel=0.05)
        for f in (-1, 1):
            z0, z1 = sorted((f * depth, f * (depth + 0.16)))
            px0, px1 = sorted((s * (W - 0.05), s * (W + 0.7)))
            k.box((px0, 0, z0), (px1, 0.4, z1), "tech_panel", bevel=0.04)
            k.box((px0 + 0.1, 0.4, z0), (px1 - 0.1, h - 0.25, z1), "stone_blocks", bevel=0.05)
            zc0, zc1 = sorted((f * depth, f * (depth + 0.21)))
            k.box((px0 - 0.04, h - 0.25, zc0), (px1 + 0.04, h, zc1), "tech_panel", bevel=0.04)
            # chamfer brace under the lintel
            gx = s * W
            zz0, zz1 = sorted((f * depth, f * (depth - 0.3)))
            k.wedge([(gx, h - 0.4, zz0), (gx, h - 0.4, zz1), (gx, h, zz0), (gx, h, zz1),
                     (gx - s * 0.4, h, zz0), (gx - s * 0.4, h, zz1)], "rust_metal")
    k.box((-(W + 0.75), h, -(depth + 0.16)), (W + 0.75, h + 0.8, depth + 0.16), "stone_blocks", bevel=0.06)
    k.box((-(W + 0.85), h + 0.7, -(depth + 0.26)), (W + 0.85, h + 0.9, depth + 0.26), "tech_panel", bevel=0.04)
    for f in (-1, 1):
        # keystone
        z0, z1 = sorted((f * (depth + 0.16), f * (depth + 0.3)))
        k.wedge([(-0.35, h + 0.05, z0), (0.35, h + 0.05, z0), (-0.45, h + 0.75, z0), (0.45, h + 0.75, z0),
                 (-0.35, h + 0.05, z1), (0.35, h + 0.05, z1), (-0.45, h + 0.75, z1), (0.45, h + 0.75, z1)],
                "rust_metal", bevel=0.03)
        z0, z1 = sorted((f * (depth + 0.16), f * (depth + 0.22)))
        k.box((-W + 0.2, h + 0.02, z0), (W - 0.2, h + 0.08, z1), "lamp_glow", bevel=0.0)
    arch = k.finish("Arch")
    c = Kit("ArchCollision", coll)
    for s in (-1, 1):
        x0, x1 = sorted((s * W, s * (W + 0.7)))
        c.box((x0, 0, -(depth + 0.16)), (x1, h, depth + 0.16), "stone_blocks", bevel=0.0)
    col = c.finish("ArchCollision-colonly")
    export([arch, col], os.path.join(OUT, f"arch_{kind.split('_')[1]}.glb"))


def extra_materials():
    # Small helper materials that exist only as Godot .tres files (no texture set).
    for name, rgb, emit in (("rubber", (0.02, 0.02, 0.02), 0), ("gunmetal", (0.03, 0.03, 0.035), 0),
                            ("gunmetal_light", (0.1, 0.1, 0.11), 0), ("brass", (0.45, 0.3, 0.1), 0),
                            ("lamp_glow", (1.0, 0.7, 0.4), 6), ("status_light", (1.0, 0.1, 0.05), 5)):
        m = bpy.data.materials.new(name)
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        if emit:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
            bsdf.inputs["Emission Strength"].default_value = emit


def main():
    reset()
    extra_materials()
    door_frame(collection("DoorFrame"))
    door_leaves(collection("DoorLeaves"))
    for kind in ("archway_400x350", "archway_400x400"):
        archway(collection(kind.title().replace("_", "")), kind)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "props.blend"), relative_remap=True, compress=True)
    print("[props] saved props.blend")


if __name__ == "__main__":
    main()

"""Render check images of a built Undercity level (Eevee, night lighting approximated).

    blender -b --factory-startup -P tools/blender/render_undercity.py -- hub [shot ...]
    ... -- hub "name@x,y,z@tx,ty,tz@lens"      # an ad-hoc camera, layout metres

Opens tools/blender/undercity_<id>.blend (written by build_undercity.py) and renders the shots
below into docs/screenshots/undercity/. They check the geometry against the design map; they
are not the game's lighting, which is baked in Godot. Preview lights stand in for the baked
ENT_ lights; the collision hulls and the coronas (billboards in Godot) are hidden.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blendkit import HERE, ROOT  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots", "undercity")

# name: (eye (layout x, y, z), target (layout x, y, z), lens mm, what it shows)
SHOTS = {
    "hub_overview_aerial": ((120, 262, 150), (120, 88, 0), 26, "the whole hub from the south, high"),
    "hub_lantern_row_street": ((46, 40.5, 1.6), (150, 37.5, 4.0), 24, "Lantern Row looking east at eye height"),
    "hub_sump_market": ((96, 112, 1.65), (138, 86, 5.0), 22, "the market under the Skyway"),
    "hub_anchor_interior": ((98.8, 68.8, 1.75), (74, 54, 1.4), 18, "the Rusty Anchor's main hall"),
    "hub_plan_top": ((120, 85, 300), (120, 85, 0), 0, "orthographic plan, to lay over the design map"),
}

GLOW = {  # preview emission for materials that have no emission texture
    "lamp_glow": ((1.0, 0.76, 0.48), 12.0),
}
BASE = {  # preview colour and roughness for the game's untextured prop materials
    "gunmetal": ((0.03, 0.032, 0.036), 0.4), "gunmetal_light": ((0.1, 0.104, 0.11), 0.45),
    "rubber": ((0.008, 0.008, 0.008), 0.85), "lamp_cage": ((0.035, 0.035, 0.04), 0.5),
}


def V(p):
    return Vector((p[0], -p[1], p[2]))


def setup():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.eevee.taa_render_samples = 24
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = 0.9
    world = bpy.data.worlds.new("night")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.035, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    for ob in bpy.data.objects:
        n = ob.name
        if n.startswith("corona_") or "-colonly" in n or n.startswith("streets_bounds"):
            ob.hide_render = True
    sc.eevee.shadow_pool_size = "1024"
    for m in bpy.data.materials:
        if m.name in BASE and m.use_nodes:
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            col, rough = BASE[m.name]
            bsdf.inputs["Base Color"].default_value = (*col, 1.0)
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = 1.0
        if m.name in GLOW and m.use_nodes:
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            col, strength = GLOW[m.name]
            bsdf.inputs["Emission Color"].default_value = (*col, 1.0)
            bsdf.inputs["Emission Strength"].default_value = strength
    # a dim blue-violet moon fill so shadows read blue, not black (UT99 zone ambient)
    sun = bpy.data.lights.new("cityglow", "SUN")
    sun.color = (0.45, 0.5, 1.0)
    sun.energy = 0.08
    so = bpy.data.objects.new("cityglow", sun)
    so.rotation_euler = (math.radians(35), 0, math.radians(30))
    sc.collection.objects.link(so)


def shoot(name):
    """A named shot, or an ad-hoc one: "name@x,y,z@tx,ty,tz@lens" in layout metres."""
    if "@" in name:
        name, eye, target, lens = name.split("@")
        eye, target, lens = [float(v) for v in eye.split(",")], [float(v) for v in target.split(",")], float(lens)
    else:
        eye, target, lens, _ = SHOTS[name]
    sc = bpy.context.scene
    cam = bpy.data.cameras.new(name)
    ob = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(ob)
    ob.location = V(eye)
    d = V(target) - V(eye)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if lens == 0:
        cam.type = "ORTHO"
        cam.ortho_scale = 320      # 5 px per metre at 1600 px: the whole 240 x 170 m map
        cam.clip_end = 1000
    else:
        cam.lens = lens
        cam.clip_end = 800
    cam.clip_start = 0.05
    sc.camera = ob
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[render]", sc.render.filepath)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    level = argv[0] if argv else "hub"
    shots = argv[1:] or [s for s in SHOTS if s != "hub_plan_top"]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, f"undercity_{level}.blend"))
    setup()
    for s in shots:
        shoot(s)


if __name__ == "__main__":
    main()

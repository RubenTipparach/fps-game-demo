"""Studio helpers for the Blender stills of Undercity's bodies (tools/blender/render_npcs.py).

It owns the look of those pictures: an EEVEE scene with the game's lighting palette (warm key,
cool blue fill, a rim; CLAUDE.md 7.3), flat materials, floor planes, text labels, an orthographic
camera, playing one clip at a frame, and writing a still. It lives in tools/blender beside the
builds it pictures. It was split out of the retired segmented-character renderer
(render_characters.py) when the generated NPC bodies replaced those characters
(openspec/changes/npc-characters, task 5.4).
"""
import math
import os

import bpy
from mathutils import Vector


def reset(res_x, res_y):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.eevee.taa_render_samples = 32
    sc.view_settings.view_transform = "AgX"
    sc.render.fps = 30
    world = bpy.data.worlds.new("World")
    sc.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.018, 0.021, 0.03, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    return sc


def light(name, rot_deg, energy, color):
    data = bpy.data.lights.new(name, "SUN")
    data.energy, data.color = energy, color
    data.angle = math.radians(8.0)
    ob = bpy.data.objects.new(name, data)
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    bpy.context.scene.collection.objects.link(ob)


def studio():
    """Warm key, cool blue fill and a rim, the game's lighting palette (CLAUDE.md 7.3)."""
    light("Key", (52.0, 0.0, -32.0), 3.2, (1.0, 0.9, 0.78))
    light("Fill", (70.0, 0.0, 60.0), 1.1, (0.55, 0.68, 1.0))
    light("Rim", (60.0, 0.0, 175.0), 2.2, (0.85, 0.55, 1.0))


def flat_material(name, rgb, emit=0.0):
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.8
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


def plane(name, center, size, mat):
    me = bpy.data.meshes.new(name)
    cx, cy, cz = center
    sx, sy = size
    me.from_pydata([(cx - sx / 2, cy - sy / 2, cz), (cx + sx / 2, cy - sy / 2, cz), (cx + sx / 2, cy + sy / 2, cz),
                    (cx - sx / 2, cy + sy / 2, cz)], [], [(0, 1, 2, 3)])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def label(text, loc, size, mat, rot=(90.0, 0.0, 0.0), align="CENTER"):
    cu = bpy.data.curves.new(f"label_{text}", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = align
    cu.materials.append(mat)
    ob = bpy.data.objects.new(f"label_{text}", cu)
    ob.location = loc
    ob.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(ob)
    return ob


def play(arm, clips, clip, frame):
    """Show one clip at a frame (fractional frames allowed) through a single NLA strip."""
    ad = arm.animation_data
    ad.action = None
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    act = clips[clip]
    length = act.frame_range[1] - act.frame_range[0]
    track = ad.nla_tracks.new()
    strip = track.strips.new(clip, 0, act)
    strip.repeat = 3.0
    strip.frame_start = -frame
    strip.frame_end = -frame + 3 * length
    strip.extrapolation = "HOLD"


def ortho_camera(center, scale, rot_deg, dist=30.0):
    cam = bpy.data.cameras.new("Camera")
    cam.type = "ORTHO"
    cam.ortho_scale = scale
    cam.clip_end = 200.0
    ob = bpy.data.objects.new("Camera", cam)
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    ob.location = Vector(center) + (ob.rotation_euler.to_matrix() @ Vector((0, 0, 1))) * dist
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.frame_set(0)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", path)

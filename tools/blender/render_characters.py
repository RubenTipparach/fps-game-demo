"""Contact sheet and walk strip of the Undercity NPCs, rendered from the exported .glb files.

It owns the pictures that show the character models: every character side by side in the
first frame of its idle loop with its id under it, and four frames of one character's walk
cycle seen from the side. It imports the committed game/models/characters/<id>.glb files, not
characters.blend, so the pictures check what the game loads: the bone parenting, the
materials and the animations as exported (CLAUDE.md 5.6, validate the real artifact).

Run:  blender -b --factory-startup -P tools/blender/render_characters.py [-- options]
  (no options)                    writes docs/screenshots/undercity/characters_sheet.png
                                  and docs/screenshots/undercity/characters_walk.png
  --walk-id <id>                  the character of the walk strip (default petra)
  --qa <clip> <phase> <view> <out.png> [ids|all] [body|head]
                                  a review render of one clip at a phase (0..1) from
                                  front, side, back or three (three-quarter), for checking
                                  interpenetration; ids is a comma list, head frames the
                                  heads only
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_data  # noqa: E402
from blendkit import ROOT  # noqa: E402

SHOTS = os.path.join(ROOT, "docs", "screenshots", "undercity")


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


def import_character(cid):
    """Import game/models/characters/<cid>.glb; returns the root armature and its clips."""
    path = os.path.join(ROOT, "game", "models", "characters", f"{cid}.glb")
    before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.context.selected_objects if o.type == "ARMATURE")
    arm.rotation_mode = "XYZ"          # the importer leaves quaternions; the layouts turn by Euler
    clips = {a.name.split(".")[0]: a for a in bpy.data.actions if a not in before}
    return arm, clips


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


def sheet(ids, per_row=11, spacing=1.25, row_gap=3.0):
    rows = math.ceil(len(ids) / per_row)
    width = per_row * spacing + 0.6
    height = rows * row_gap + 0.2
    reset(3200, int(3200 * height / width))
    studio()
    ground = flat_material("ground", (0.045, 0.048, 0.056))
    text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
    for r in range(rows):
        z = -r * row_gap
        plane(f"ground_{r}", (0.0, 0.3, z), (width + 2.0, 1.4), ground)
    for i, cid in enumerate(ids):
        r, c = divmod(i, per_row)
        x = (c - (per_row - 1) / 2.0) * spacing
        z = -r * row_gap
        arm, clips = import_character(cid)
        arm.location = (x, 0.0, z)
        arm.rotation_euler = (0.0, 0.0, math.radians(-22.0))
        play(arm, clips, "idle", 0.0)
        label(cid, (x, -0.45, z - 0.2), 0.15, text)
    top = 2.15
    ortho_camera((0.0, 0.0, (top + -(rows - 1) * row_gap - 0.35) / 2.0), width, (86.0, 0.0, 0.0))
    render(os.path.join(SHOTS, "characters_sheet.png"))


def walk_strip(cid, table):
    reset(2400, 900)
    studio()
    ground = flat_material("ground", (0.045, 0.048, 0.056))
    line = flat_material("line", (0.25, 0.27, 0.3))
    text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
    spacing = 1.25
    plane("ground", (0.0, 0.0, 0.0), (1.6, 4 * spacing + 1.0), ground)
    for k in range(-10, 11):
        plane(f"tick_{k}", (0.0, k * 0.25, 0.0005), (1.6, 0.006), line)
    row = next(r for r in table["characters"] if r["id"] == cid)
    fps = table["animations"]["fps"]
    cycle = row["walk_cycle_s"] or table["animations"]["walk"]["cycle_s"]
    n = round(cycle * fps)
    for k in range(4):
        y = (k - 1.5) * spacing
        arm, clips = import_character(cid)
        arm.location = (0.0, y, 0.0)
        frame = k * n / 4.0
        play(arm, clips, "walk", frame)
        label(f"{cid} walk  t = {frame / fps:.3f} s", (0.5, y, -0.2), 0.09, text, rot=(90.0, 0.0, 90.0))
    ortho_camera((0.0, 0.0, 0.85), 4 * spacing + 0.2, (88.0, 0.0, 90.0))
    render(os.path.join(SHOTS, "characters_walk.png"))


def qa(ids, clip, phase, view, out, table, zoom="body"):
    per_row = min(11, len(ids)) if zoom == "body" else len(ids)
    rows = math.ceil(len(ids) / per_row)
    spacing = 1.3 if zoom == "body" else 0.6
    width = per_row * spacing + 0.4
    row_h = 3.0 if zoom == "body" else 0.7
    height = rows * row_h
    res_x = 3200 if height <= width else max(800, int(1600 * width / height))
    reset(res_x, max(400, int(res_x * height / width)))
    studio()
    ground = flat_material("ground", (0.045, 0.048, 0.056))
    text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
    rot = {"front": 0.0, "side": -90.0, "back": 180.0, "three": -35.0}[view]
    for i, cid in enumerate(ids):
        r, c = divmod(i, per_row)
        x, z = (c - (per_row - 1) / 2.0) * spacing, -r * (3.0 if zoom == "body" else 0.0)
        if zoom == "body":
            plane(f"ground_{i}", (x, 0.0, z), (1.2, 1.4), ground)
        arm, clips = import_character(cid)
        arm.location = (x, 0.0, z)
        if zoom != "body":      # line the heads up: each crown 0.15 m above the row centre
            height = next(row["height_m"] for row in table["characters"] if row["id"] == cid)
            arm.location.z = -r * row_h + 0.15 - height
        arm.rotation_euler = (0.0, 0.0, math.radians(rot))
        length = clips[clip].frame_range[1] - clips[clip].frame_range[0]
        play(arm, clips, clip, phase * length)
        label(cid, (x, -0.7, z - 0.2) if zoom == "body" else (x, -0.7, -0.3), 0.14 if zoom == "body" else 0.05, text)
    if zoom == "body":
        ortho_camera((0.0, 0.0, (2.15 - (rows - 1) * 3.0 - 0.35) / 2.0), width, (84.0, 0.0, 0.0))
    else:
        ortho_camera((0.0, 0.0, -(rows - 1) * row_h / 2.0), width, (88.0, 0.0, 0.0))
    render(out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    table = character_data.load()
    ids = [r["id"] for r in table["characters"]]
    if "--qa" in argv:
        i = argv.index("--qa")
        clip, phase, view, out = argv[i + 1], float(argv[i + 2]), argv[i + 3], argv[i + 4]
        sel = argv[i + 5].split(",") if len(argv) > i + 5 and argv[i + 5] != "all" else ids
        zoom = argv[i + 6] if len(argv) > i + 6 else "body"
        qa(sel, clip, phase, view, out, table, zoom)
        return
    walk_id = argv[argv.index("--walk-id") + 1] if "--walk-id" in argv else "petra"
    sheet(ids)
    walk_strip(walk_id, table)


if __name__ == "__main__":
    main()

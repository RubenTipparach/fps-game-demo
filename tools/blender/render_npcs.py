"""Stills of the Undercity NPC bodies, rendered from the exported glbs.

It owns the pictures that show the generated bodies (openspec/changes/archive/2026-09-28-npc-characters): every
body of tools/blender/npcs.json front on in rows with its id under it, the three faction outfits
close up from three-quarters, and the same outfits at the stress pose the build checks gear
against, and a strip of the Surrender and Cower clips. It imports the committed
game/models/characters/<id>.glb files and game/animations/undercity_clips.glb, not a .blend, so
the pictures show what the game loads: the rig, the skinning, the atlases and the keys as
exported (CLAUDE.md 5.6, validate the real artifact). The clips play on the Universal Animation
Library's own mannequin, from the pinned pack in the dependency cache, since they are keyed on
its rig. The studio, labels and camera come from studiokit.py.

Run (EEVEE needs a display; in a container use Xvfb):
  xvfb-run -a -s "-screen 0 1920x1080x24" blender -b --factory-startup -P tools/blender/render_npcs.py
Writes docs/screenshots/npc_bodies/lineup_<n>.png (per_row bodies each), faction_<name>.png,
faction_stress_pose.png and clips.png.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_npc_clips  # noqa: E402
import npc_data  # noqa: E402
from build_npcs import apply_pose, deps  # noqa: E402
from studiokit import flat_material, label, ortho_camera, plane, play, render, reset, studio  # noqa: E402
from blendkit import ROOT  # noqa: E402

SHOTS = os.path.join(ROOT, "docs", "screenshots", "npc_bodies")
PER_ROW = 8
SPACING_M = 1.1
# Close-ups: the faction outfits, two bodies each, and what they show.
FACTIONS = [("mersec", ["mersec", "dace"]), ("drain_rats", ["rat_grunt", "skiv"]),
            ("scrap_kings", ["kings_grunt", "jax"])]


def import_body(npc_id, table):
    path = os.path.join(ROOT, table["out_dir"], f"{npc_id}.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    top = arm
    while top.parent:
        top = top.parent
    top.rotation_mode = "XYZ"
    return top, arm


def png_settings():
    s = bpy.context.scene.render.image_settings
    s.file_format = "PNG"
    s.color_mode = "RGB"
    s.compression = 100


def lineups(table):
    ids = [b["id"] for b in table["bodies"]]
    rows = [ids[i:i + PER_ROW] for i in range(0, len(ids), PER_ROW)]
    for n, row in enumerate(rows, 1):
        width = PER_ROW * SPACING_M + 0.4
        reset(2400, int(2400 * 2.75 / width))
        png_settings()
        studio()
        ground = flat_material("ground", (0.045, 0.048, 0.056))
        text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
        plane("ground", (0.0, 0.3, 0.0), (width + 2.0, 1.6), ground)
        for i, npc_id in enumerate(row):
            x = (i - (PER_ROW - 1) / 2.0) * SPACING_M
            top, _ = import_body(npc_id, table)
            top.location = (x, 0.0, 0.0)
            label(npc_id, (x, -0.55, -0.24), 0.13, text)
        ortho_camera((0.0, 0.0, 2.2 / 2.0 - 0.22), width, (90.0, 0.0, 0.0))
        render(os.path.join(SHOTS, f"lineup_{n}.png"))


def closeup(name, ids, table, pose=None, out=None):
    reset(1600, 1000)
    png_settings()
    studio()
    ground = flat_material("ground", (0.045, 0.048, 0.056))
    text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
    plane("ground", (0.0, 0.0, 0.0), (6.0, 6.0), ground)
    for i, npc_id in enumerate(ids):
        x = (i - (len(ids) - 1) / 2.0) * 1.0
        top, arm = import_body(npc_id, table)
        top.location = (x, 0.0, 0.0)
        top.rotation_euler = (0.0, 0.0, math.radians(-30.0))
        if pose:
            apply_pose(arm, pose)
        label(npc_id, (x, -0.5, 0.02), 0.08, text, rot=(0.0, 0.0, 0.0))
    cam = bpy.data.cameras.new("Camera")
    cam.lens = 55.0 if not pose else 40.0
    ob = bpy.data.objects.new("Camera", cam)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    at = Vector((0.0, 0.0, 1.3 if not pose else 1.15))
    ob.location = at + (Vector((1.1, -3.4, 0.35)) if not pose else Vector((1.2, -4.4, 0.3)))
    ob.rotation_euler = (at - ob.location).to_track_quat("-Z", "Y").to_euler()
    render(out or os.path.join(SHOTS, f"faction_{name}.png"))


def clip_strip():
    """Surrender and Cower at four times each, side on and three-quarters, on UAL's mannequin."""
    clips_table = build_npc_clips.load()
    pack = deps.pack_by_id(clips_table["source"]["pack"])
    deps.verify(pack)
    folder = deps.unpack(pack, os.path.join(deps.cache_dir(), "unpacked", pack["id"]))
    reset(2400, 760)
    png_settings()
    studio()
    sc = bpy.context.scene
    sc.render.fps = clips_table["fps"]
    ground = flat_material("ground", (0.045, 0.048, 0.056))
    text = flat_material("text", (0.85, 0.87, 0.9), emit=1.0)
    bpy.ops.import_scene.gltf(filepath=os.path.join(folder, clips_table["source"]["glb"]))
    mannequin = bpy.data.objects["Mannequin"]
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o is not mannequin:
            bpy.data.objects.remove(o, do_unlink=True)
    before, acts_before = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, clips_table["out"]))
    rig = next(o for o in bpy.data.objects if o not in before and o.type == "ARMATURE")
    clips = {a.name.split(".")[0]: a for a in bpy.data.actions if a not in acts_before}
    for o in bpy.data.objects:
        if o not in before and o.type == "MESH":
            o.hide_render = True
    mannequin.hide_render = True
    times = (0.0, 0.5, 1.0, 1.5)
    n = 0
    for name in sorted(clips_table["clips"]):
        for c, t in enumerate(times):
            x = (n - (2 * len(times) - 1) / 2.0) * 1.2
            arm = rig.copy()
            sc.collection.objects.link(arm)
            body = mannequin.copy()
            sc.collection.objects.link(body)
            body.hide_render = False
            body.parent = arm
            for mod in body.modifiers:
                if mod.type == "ARMATURE":
                    mod.object = arm
            arm.location = (x, 0.0, 0.0)
            arm.rotation_mode = "XYZ"
            arm.rotation_euler = (0.0, 0.0, math.radians(-90.0 if c % 2 == 0 else -35.0))
            arm.animation_data_create()
            play(arm, clips, name, t * clips_table["fps"])
            label(f"{name} {t:.1f} s", (x, -0.6, -0.2), 0.1, text)
            n += 1
    plane("ground", (0.0, 0.3, 0.0), (12.0, 1.6), ground)
    ortho_camera((0.0, 0.0, 0.8), 2 * len(times) * 1.2 + 0.3, (90.0, 0.0, 0.0))
    render(os.path.join(SHOTS, "clips.png"))


def main():
    table = npc_data.load()
    lineups(table)
    for name, ids in FACTIONS:
        closeup(name, ids, table)
    reset(100, 100)
    closeup("stress", [ids[0] for _, ids in FACTIONS], table, pose=table["stress_pose"],
            out=os.path.join(SHOTS, "faction_stress_pose.png"))
    clip_strip()


if __name__ == "__main__":
    main()

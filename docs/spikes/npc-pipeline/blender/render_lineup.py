"""Measurement instrument: import the exported NPC glbs back into Blender and render
(1) the rest-pose lineup and (2) a stress pose that bends shoulders, elbows, spine, hips and
knees, to check the exported skin weights. Uses EEVEE (needs DISPLAY=:99, lavapipe).

Usage: blender -b --factory-startup --python render_lineup.py -- <build_dir> <stills_dir>
"""
import bpy, os, sys, math
from mathutils import Matrix, Vector, Euler

ARGS = sys.argv[sys.argv.index("--") + 1:]
BUILD, STILLS = ARGS[0], ARGS[1]
os.makedirs(STILLS, exist_ok=True)
ORDER = ["bouncer", "coat_woman", "old_civilian", "random_civilian"]

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

rigs = []
for i, name in enumerate(ORDER):
    glb = os.path.join(BUILD, name, name + ".glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in new if o.type == 'ARMATURE'][0]
    top = arm
    while top.parent:
        top = top.parent
    top.location.x = (i - 1.5) * 1.3
    rigs.append(arm)

# ground, lights, camera
bpy.ops.mesh.primitive_plane_add(size=30)
ground = bpy.context.active_object
gm = bpy.data.materials.new("ground")
gm.diffuse_color = (0.25, 0.25, 0.27, 1)
ground.data.materials.append(gm)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
sun.data.energy = 3.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(-30)))
bpy.context.scene.collection.objects.link(sun)
fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", 'AREA'))
fill.data.energy = 600
fill.data.size = 6
fill.location = (0, -6, 4)
fill.rotation_euler = Euler((math.radians(55), 0, 0))
bpy.context.scene.collection.objects.link(fill)
world = bpy.data.worlds.new("w")
world.color = (0.08, 0.09, 0.12)
bpy.context.scene.world = world
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 50
bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = 'Standard'


def look(frm, at):
    cam.location = Vector(frm)
    d = Vector(at) - Vector(frm)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render(name):
    sc.render.filepath = os.path.join(STILLS, name)
    bpy.ops.render.render(write_still=True)
    print("wrote", sc.render.filepath)


look((0, -8.0, 1.1), (0, 0, 0.9))
render("01_lineup_rest.png")

# Stress pose: rotations about armature-space axes, applied in each bone's rest frame.
POSE = {
    "upperarm_l": ('Y', -75), "lowerarm_l": ('Z', 70),
    "upperarm_r": ('X', -80), "lowerarm_r": ('X', -70),
    "spine_02": ('Z', 20), "neck_01": ('Z', 15), "head": ('X', 12),
    "thigh_l": ('X', -70), "calf_l": ('X', 95),
    "thigh_r": ('X', 20), "calf_r": ('X', 25),
    "hand_l": ('X', 40), "index_01_r": ('X', 60), "middle_01_r": ('X', 60),
}
for arm in rigs:
    for bname, (axis, deg) in POSE.items():
        pb = arm.pose.bones.get(bname)
        if not pb:
            print("missing bone", bname)
            continue
        pb.rotation_mode = 'QUATERNION'
        rest = pb.bone.matrix_local.to_3x3()
        r = Matrix.Rotation(math.radians(deg), 3, axis)
        pb.rotation_quaternion = (rest.inverted() @ r @ rest).to_quaternion()
bpy.context.view_layer.update()
look((3.2, -7.4, 1.5), (0, 0, 0.95))
render("02_lineup_stress_pose.png")
sc.render.resolution_x, sc.render.resolution_y = 900, 900
look((-1.95 + 1.3, -2.4, 1.75), (-1.95, 0, 1.3))
render("03_bouncer_stress_closeup.png")

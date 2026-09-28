"""Undercity's own NPC clips, keyed on the Universal Animation Library's rig: Surrender and Cower.

It owns game/animations/undercity_clips.glb (openspec/changes/npc-characters, design section 6,
task 3.2): the clips UAL Standard lacks that combat-and-enemies needs, authored from
tools/blender/npc_clips.json. The glb holds UAL's own armature (imported from the pinned pack,
same bone names and rest pose), one tiny triangle skinned to it so Godot builds a Skeleton3D,
and one action per clip, so the bone map that retargets UAL retargets these too and every NPC
body plays them. It lives in tools/blender because it is a Blender build of a committed asset;
the glb is generated, never hand-edited (CLAUDE.md 6.1, 11).

Poses are solved per frame: a bone either turns by rotations about armature axes after its
parent, or aims its head-to-tail direction at a vector given in a frame bone's posed frame (with
a twist about that direction); legs are two-bone IK that keeps each ankle where it rests, so the
feet stay planted while the hips move. Motions are sines with a whole number of cycles per clip,
so each clip's last frame equals its first. The output is byte-identical on rebuild, and the
build checks the written glb: the clip names and lengths, the joints against UAL's own glb, and
that every channel ends where it starts.

Run:
  python3 tools/deps/fetch_character_tools.py && \
  blender -b --factory-startup --python tools/blender/build_npc_clips.py
glTF has no loop flag: Godot's import options mark these clips looping.
"""
import hashlib
import json
import math
import os
import struct
import sys
import traceback

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "deps"))
import fetch_character_tools as deps  # noqa: E402
from tablekit import Bool, DataError, Int, List, Map, Num, Obj, Str, Vec  # noqa: E402

TABLE = os.path.join(HERE, "npc_clips.json")
AXES = ("X", "Y", "Z")
LEGS = (("DEF-thigh.L", "DEF-shin.L", "DEF-foot.L"), ("DEF-thigh.R", "DEF-shin.R", "DEF-foot.R"))
HIPS = "DEF-hips"
LOOP_TOLERANCE = 1e-5

ROT = Obj({"axis": Str(choices=AXES), "deg": Num(lo=-180.0, hi=180.0)})
BONE = Obj({"bone": Str(), "rot": List(ROT, []), "frame": Str(None, nullable=True),
            "aim": Vec(3, None, lo=-10.0, hi=10.0), "twist_deg": Num(0.0, -180.0, 180.0)})
MOTION = Obj({"bone": Str(), "axis": Str(choices=AXES), "deg": Num(lo=-45.0, hi=45.0),
              "cycles": Int(lo=1, hi=100), "phase_deg": Num(0.0, -360.0, 360.0)})
CLIP = Obj({"length_s": Num(lo=0.1, hi=60.0), "hips_offset_m": Vec(3, [0.0, 0.0, 0.0], lo=-1.0, hi=1.0),
            "plant_feet": Bool(True), "knee_forward": Num(1.0, -1.0, 1.0),
            "bones": List(BONE, []), "motions": List(MOTION, [])})
SCHEMA = Obj({
    "source": Obj({"pack": Str(), "glb": Str(), "armature": Str()}),
    "out": Str(),
    "fps": Int(lo=1, hi=240),
    "placeholder": Obj({"bone": Str(), "size_m": Num(lo=0.0001, hi=0.1)}),
    "clips": Map(CLIP),
})


class ClipError(RuntimeError):
    """A clip the build can't make as the table asks. The message names the clip."""


def load(path=TABLE):
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        table = SCHEMA.check(raw, "npc_clips.json", {})
    except (OSError, json.JSONDecodeError, DataError) as e:
        raise DataError(f"{path}: {e}") from None
    for name, clip in table["clips"].items():
        for i, b in enumerate(clip["bones"]):
            if (b["aim"] is None) != (b["frame"] is None):
                raise DataError(f"{path}: clips.{name}.bones[{i}]: an aim and its frame bone go together")
            if b["aim"] is not None and b["rot"]:
                raise DataError(f"{path}: clips.{name}.bones[{i}]: give an aim or rot, not both")
        steps = clip["length_s"] * table["fps"]
        if abs(steps - round(steps)) > 1e-9:
            raise DataError(f"{path}: clips.{name}.length_s: {clip['length_s']} s is not a whole number of frames "
                            f"at {table['fps']} fps")
    return table


def lfu(v):
    """[left, front, up] -> armature space (the body faces -Y, its left is +X)."""
    return Vector((v[0], -v[1], v[2]))


def axis_rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, axis)


def hierarchy(arm):
    """Bones parents first, siblings by name, so the solve and the keys come in a fixed order."""
    out, todo = [], sorted([b for b in arm.data.bones if b.parent is None], key=lambda b: b.name)
    while todo:
        b = todo.pop(0)
        out.append(b)
        todo = sorted(b.children, key=lambda c: c.name) + todo
    return out


def solve(arm, clip, t, bones):
    """Local pose (location, rotation) per bone at time t, from the clip's spec."""
    spec = {b["bone"]: b for b in clip["bones"]}
    motions = {}
    for m in clip["motions"]:
        a = m["deg"] * math.sin(2.0 * math.pi * m["cycles"] * t / clip["length_s"] + math.radians(m["phase_deg"]))
        motions.setdefault(m["bone"], []).append(axis_rot(m["axis"], a))
    rest = {b.name: b.matrix_local.copy() for b in bones}
    world_rot, posed, local = {}, {}, {}
    leg_targets = {}
    for b in bones:
        r_rest = rest[b.name].to_3x3()
        p = b.parent
        w_p = world_rot[p.name] if p else Matrix.Identity(3)
        s = spec.get(b.name)
        if b.name in leg_targets:
            direction = leg_targets[b.name]
            d_rest = (b.tail_local - b.head_local).normalized()
            w = (w_p @ d_rest).rotation_difference(direction).to_matrix() @ w_p
        elif b.name in [leg[2] for leg in LEGS] and clip["plant_feet"]:
            w = Matrix.Identity(3)
        elif s and s["aim"] is not None:
            if s["frame"] not in world_rot:
                raise ClipError(f"bone {b.name}: frame bone {s['frame']!r} must be one of its ancestors")
            target = (world_rot[s["frame"]] @ lfu(s["aim"])).normalized()
            d_rest = (b.tail_local - b.head_local).normalized()
            w = (Quaternion(target, math.radians(s["twist_deg"])).to_matrix()
                 @ (w_p @ d_rest).rotation_difference(target).to_matrix() @ w_p)
        else:
            w = w_p
            for r in (s["rot"] if s else []):
                w = axis_rot(r["axis"], r["deg"]) @ w
        for r in motions.get(b.name, []):
            w = r @ w
        world_rot[b.name] = w
        basis_rot = r_rest.inverted() @ w_p.inverted() @ w @ r_rest
        loc = Vector((0.0, 0.0, 0.0))
        if b.name == HIPS:
            loc = r_rest.inverted() @ lfu(clip["hips_offset_m"])
        local[b.name] = (loc, basis_rot.to_quaternion())
        basis = Matrix.Translation(loc) @ basis_rot.to_4x4()
        parent_m = posed[p.name] @ rest[p.name].inverted() if p else Matrix.Identity(4)
        posed[b.name] = parent_m @ rest[b.name] @ basis
        if b.name == HIPS and clip["plant_feet"]:
            leg_targets.update(leg_ik(arm, posed, rest, clip["knee_forward"]))
    return local


def leg_ik(arm, posed, rest, knee_forward):
    """Thigh and shin directions that put each ankle back at rest, knees bending to the front."""
    out = {}
    for thigh, shin, foot in LEGS:
        tb, sb, fb = arm.data.bones[thigh], arm.data.bones[shin], arm.data.bones[foot]
        hip = (posed[HIPS] @ rest[HIPS].inverted() @ rest[thigh]).to_translation()
        ankle = fb.head_local.copy()
        a, b = (tb.tail_local - tb.head_local).length, (sb.tail_local - sb.head_local).length
        d_vec = ankle - hip
        d = min(d_vec.length, a + b - 1e-6)
        u = d_vec.normalized()
        front = Vector((0.0, -knee_forward, 0.0))
        n = (front - front.dot(u) * u).normalized()
        cos_a = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2.0 * a * d)))
        knee = hip + a * (cos_a * u + math.sqrt(1.0 - cos_a * cos_a) * n)
        out[thigh] = (knee - hip).normalized()
        out[shin] = (ankle - knee).normalized()
    return out


def placeholder(arm, spec):
    """One tiny triangle at the bone's head, skinned 100 % to it."""
    bone = arm.data.bones[spec["bone"]]
    h, s = bone.head_local, spec["size_m"]
    me = bpy.data.meshes.new("SkeletonAnchor")
    me.from_pydata([tuple(h), tuple(h + Vector((s, 0.0, 0.0))), tuple(h + Vector((0.0, 0.0, s)))], [], [(0, 1, 2)])
    obj = bpy.data.objects.new("SkeletonAnchor", me)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = arm
    grp = obj.vertex_groups.new(name=bone.name)
    grp.add([0, 1, 2], 1.0, 'REPLACE')
    obj.modifiers.new("Armature", 'ARMATURE').object = arm
    return obj


def read_glb(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    blob = data[20 + jlen + 8:]

    def accessor(i):
        acc = j["accessors"][i]
        bv = j["bufferViews"][acc["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[acc["type"]]
        off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        vals = struct.unpack_from("<%df" % (acc["count"] * n), blob, off)
        return [vals[k:k + n] for k in range(0, len(vals), n)]
    return data, j, accessor


def check_output(path, table, ual_glb):
    """Check the written glb itself: clip names and lengths, joints named as in UAL's glb, loops."""
    data, j, accessor = read_glb(path)
    _, uj, _ = read_glb(ual_glb)
    ual_joints = sorted(uj["nodes"][i]["name"] for i in uj["skins"][0]["joints"])
    joints = sorted(j["nodes"][i]["name"] for i in j["skins"][0]["joints"])
    if joints != ual_joints:
        raise ClipError(f"{path}: the skin's joints differ from UAL's ({len(joints)} vs {len(ual_joints)})")
    names = sorted(a["name"] for a in j.get("animations", []))
    if names != sorted(table["clips"]):
        raise ClipError(f"{path}: animations {names}, the table has {sorted(table['clips'])}")
    report = {}
    for anim in j["animations"]:
        clip = table["clips"][anim["name"]]
        worst, length = 0.0, 0.0
        for ch in anim["channels"]:
            sampler = anim["samplers"][ch["sampler"]]
            times, values = accessor(sampler["input"]), accessor(sampler["output"])
            length = max(length, times[-1][0])
            worst = max(worst, max(abs(x - y) for x, y in zip(values[0], values[-1])))
        if abs(length - clip["length_s"]) > 1e-4:
            raise ClipError(f"{anim['name']}: {length:.4f} s long in the glb, the table says {clip['length_s']} s")
        if worst > LOOP_TOLERANCE:
            raise ClipError(f"{anim['name']}: its last frame differs from its first by {worst:.2e}; it won't loop")
        report[anim["name"]] = {"channels": len(anim["channels"]), "length_s": round(length, 4),
                                "loop_error": worst}
    meshes = j.get("meshes", [])
    tris = sum(j["accessors"][p["indices"]]["count"] // 3 for m in meshes for p in m["primitives"])
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "joints": len(joints),
            "meshes": len(meshes), "triangles": tris, "clips": report}


def main():
    try:
        table = load()
        pack = deps.pack_by_id(table["source"]["pack"])
        deps.verify(pack)
        folder = deps.unpack(pack, os.path.join(deps.cache_dir(), "unpacked", pack["id"]))
        ual_glb = os.path.join(folder, table["source"]["glb"])
        if deps.Allowlist({pack["id"]: folder}).pack_of(ual_glb) is None:
            raise ClipError(f"{ual_glb} is not a file of the pinned pack {pack['id']}")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = bpy.context.scene
        sc.render.fps = table["fps"]
        bpy.ops.import_scene.gltf(filepath=ual_glb)
        arm = bpy.data.objects.get(table["source"]["armature"])
        if arm is None or arm.type != 'ARMATURE':
            raise ClipError(f"{ual_glb} has no armature named {table['source']['armature']!r}")
        for o in list(bpy.data.objects):
            if o is not arm:
                bpy.data.objects.remove(o, do_unlink=True)
        arm.animation_data_clear()
        for a in list(bpy.data.actions):
            bpy.data.actions.remove(a)
        bones = hierarchy(arm)
        names = {b.name for b in bones}
        for cname, clip in table["clips"].items():
            for b in clip["bones"] + clip["motions"]:
                if b["bone"] not in names:
                    raise ClipError(f"{cname}: bone {b['bone']!r} is not in UAL's rig")
        anchor = placeholder(arm, table["placeholder"])
        arm.animation_data_create()
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        for cname in sorted(table["clips"]):
            clip = table["clips"][cname]
            action = bpy.data.actions.new(cname)
            arm.animation_data.action = action
            frames = int(round(clip["length_s"] * table["fps"]))
            prev = {}
            for f in range(frames + 1):
                try:
                    local = solve(arm, clip, f / table["fps"], bones)
                except ClipError as e:
                    raise ClipError(f"{cname}: {e}") from None
                for b in bones:
                    loc, q = local[b.name]
                    if b.name in prev:
                        q.make_compatible(prev[b.name])
                    prev[b.name] = q
                    pb = arm.pose.bones[b.name]
                    pb.rotation_quaternion = q
                    pb.keyframe_insert("rotation_quaternion", frame=f)
                    if b.name == HIPS:
                        pb.location = loc
                        pb.keyframe_insert("location", frame=f)
            track = arm.animation_data.nla_tracks.new()
            track.name = cname
            track.strips.new(cname, 0, action)
            track.mute = True
            arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            pb.location = (0.0, 0.0, 0.0)
        out = os.path.join(ROOT, table["out"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        for o in bpy.data.objects:
            o.select_set(o in (arm, anchor))
        bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_yup=True,
                                  export_skins=True, export_animations=True, export_animation_mode='ACTIONS',
                                  export_force_sampling=True, export_frame_range=False, export_morph=False,
                                  export_materials='NONE', export_rest_position_armature=True,
                                  export_def_bones=False)
        result = check_output(out, table, ual_glb)
    except (ClipError, DataError, deps.PackError) as e:
        print("FAIL", e, flush=True)
        sys.exit(1)
    except Exception:  # Blender would print the traceback and still exit 0
        traceback.print_exc()
        print("FAIL the build stopped on the error above", flush=True)
        sys.exit(1)
    print("[clips]", json.dumps(result, sort_keys=True), flush=True)
    print(f"OK {len(result['clips'])} clips written to {table['out']}", flush=True)


if __name__ == "__main__":
    main()

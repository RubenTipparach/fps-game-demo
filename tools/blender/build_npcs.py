"""Undercity NPC bodies: MPFB 2 humans made game-ready, one glb per body, from tools/blender/npcs.json.

It owns the NPC body models (openspec/changes/archive/2026-09-28-npc-characters, design sections 1-4 and 8). Every
row of the table becomes game/models/characters/<id>.glb:
  - a human built by MPFB's own services (HumanService, RandomizationService for civilians), with
    the game_engine rig (53 bones), a low-poly proxy body, eyes, brows, lashes, hair and the CC0
    clothes, its height fitted to the row's height_m;
  - the proxy replaces the base mesh, the clothes' delete groups are applied, and the heavy
    pieces are decimated;
  - faction gear authored here (owner, survey H3): rigid low-poly shells that wrap the body with a
    clearance, each skinned 100 % to one bone of the rig;
  - three materials (skin, outfit, alpha-clipped hair) on four atlas textures at atlas_px: the
    skin toned, the clothes tinted to the row's colours, the gear painted into the outfit atlas;
  - one skinned mesh and the rig, with no animations: the game plays one shared library.
The build refuses an asset that isn't a file of an allowlisted pack (tools/deps/character_packs.json),
a body over its budget, and gear that pokes through the body at rest or at the stress pose,
naming the NPC and the number. The same table and packs give byte-identical glbs.

It lives in tools/blender because it is a Blender build that writes committed models; the
generated glbs are never hand-edited (CLAUDE.md 6.1, 11). The table is the editable source: the
.blend is not committed (CLAUDE.md 13).

Run:
  python3 tools/deps/fetch_character_tools.py && \
  blender -b --factory-startup --python tools/blender/build_npcs.py [-- --only tank,nguyen] [--report stats.json]
  (--verify rebuilds every body and fails unless each matches its committed glb byte for byte,
   writing nothing: the reproducibility check)
  (--save-blend <dir> also saves each body, gear included, as a .blend before the checks, for debugging;
   --table <file> reads another table, for checking the build's refusals)
The script restarts Blender once with BLENDER_USER_RESOURCES in the dependency cache
($UNDERCITY_DEPS, default ~/.cache/undercity/deps), unpacks MPFB and the CC0 assets there from the
verified zips, and never touches the user's own Blender settings.

Axes: MPFB builds in Blender with the character facing -Y, its left at +X and Z up; the glTF
export is +Y up, so in Godot a body faces +Z. Lengths are metres, angles in the table degrees.
"""
import hashlib
import json
import math
import os
import random
import struct
import subprocess
import sys
import time
import traceback
import zlib

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools", "deps"))
import fetch_character_tools as deps  # noqa: E402
import npc_data  # noqa: E402

MPFB_PACK = "mpfb"
ASSET_PACK = "makehuman_system_assets_cc0"
MPFB_MODULE = "bl_ext.user_default.mpfb"
# The uuid of the low-poly eyes mhclo; MPFB keys an eye colour by it (alternative_materials).
EYES_UUID = "1cc97a30-85a1-42e6-a9f7-b3e753732baa"
PAD_PX = 4  # gutter around each atlas tile, edge-extended so mip levels don't bleed
FRONT = Vector((0.0, -1.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))
# Atlas templates: pixel rects (x0, y0, size) at 1024 px, origin bottom-left like UVs, in fill order.
T768 = [(0, 256, 768), (768, 768, 256), (768, 512, 256), (768, 256, 256),
        (0, 0, 256), (256, 0, 256), (512, 0, 256), (768, 0, 256)]
T1024 = [(0, 0, 1024)]
HAIR_KINDS = ("Hair", "Eyebrows", "Eyelashes")


class BuildError(RuntimeError):
    """A body that can't be built as the table asks. The message names the NPC."""


# ----------------------------------------------------------------------------- environment

def private_blender_dir():
    """The Blender user folder the build runs with: in the dependency cache, per Blender version."""
    return os.path.join(deps.cache_dir(), "blender", "%d.%d" % bpy.app.version[:2])


def ensure_private_blender():
    """Restart Blender once with the private user folder, so MPFB never lands in the user's own."""
    want = private_blender_dir()
    if os.path.realpath(os.environ.get("BLENDER_USER_RESOURCES", "")) == os.path.realpath(want):
        return
    os.makedirs(want, exist_ok=True)
    env = dict(os.environ, BLENDER_USER_RESOURCES=want, PYTHONHASHSEED="0")
    code = subprocess.run([bpy.app.binary_path] + sys.argv[1:], env=env).returncode
    sys.exit(code)


def install_packs(packs):
    """Unpack the verified MPFB and CC0 packs into the private folder, enable MPFB, and return the
    allowlist that says which pack a file on disk comes from."""
    import addon_utils
    for pack in packs:
        deps.verify(pack)
    repo = next(r for r in bpy.context.preferences.extensions.repos if r.module == "user_default")
    mpfb_dir = deps.unpack(deps.pack_by_id(MPFB_PACK, packs), os.path.join(repo.directory, "mpfb"))
    addon_utils.enable(MPFB_MODULE, default_set=True)
    from bl_ext.user_default.mpfb.services import AssetService, LocationService
    data_dir = LocationService.get_user_data()
    deps.unpack(deps.pack_by_id(ASSET_PACK, packs), data_dir)
    AssetService.rescan_pack_metadata()
    AssetService.update_all_asset_lists()
    return deps.Allowlist({MPFB_PACK: mpfb_dir, ASSET_PACK: data_dir}, packs)


def mpfb():
    """MPFB's service modules (imported once MPFB is enabled)."""
    from bl_ext.user_default.mpfb.entities.objectproperties import GeneralObjectProperties, HumanObjectProperties
    from bl_ext.user_default.mpfb.services import (AssetService, HumanService, LocationService,
                                                   RandomizationService, TargetService)
    return {"AssetService": AssetService, "HumanService": HumanService, "LocationService": LocationService,
            "RandomizationService": RandomizationService, "TargetService": TargetService,
            "GeneralObjectProperties": GeneralObjectProperties, "HumanObjectProperties": HumanObjectProperties}


# ----------------------------------------------------------------------------- table to MPFB

def age_slider(years):
    """MakeHuman's age slider for an age in years: 0 = 1 y, 0.1875 = 11 y, 0.5 = 25 y, 1 = 90 y,
    linear between those anchors (MPFB's macro convention)."""
    anchors = [(1.0, 0.0), (11.0, 0.1875), (25.0, 0.5), (90.0, 1.0)]
    years = min(max(years, anchors[0][0]), anchors[-1][0])
    for (y0, s0), (y1, s1) in zip(anchors, anchors[1:]):
        if years <= y1:
            return s0 + (years - y0) / (y1 - y0) * (s1 - s0)
    return 1.0


def body_seed(table, body):
    """A per-body seed derived from the table seed and the id (stable across runs and machines)."""
    return zlib.crc32(f"{table['seed']}:{body['id']}".encode()) & 0x7FFFFFFF


def resolve_body(table, body, m):
    """The row as MPFB inputs: macro sliders, asset names and the target height. Civilians draw
    everything the row doesn't pin from their seed, inside civilian_range."""
    spec = {k: body[k] for k in ("id", "sex", "eyelashes", "hair", "hair_tint", "brow_tint", "skin_tone",
                                 "clothes", "gear")}
    male = body["sex"] == "male"
    if body["kind"] == "named":
        total = sum(body["race"].values())
        spec["macro"] = {
            "gender": 1.0 if male else 0.0, "age": age_slider(body["age_years"]), "muscle": body["muscle"],
            "weight": body["weight"], "height": 0.5, "proportions": body["proportions"],
            "cupsize": body["cupsize"], "firmness": body["firmness"],
            "race": {r: body["race"][r] / total for r in npc_data.RACES}}
        spec.update(height_m=body["height_m"], age_years=body["age_years"], skin=body["skin"],
                    eyes=body["eyes"], eyebrows=body["eyebrows"])
        return spec
    cr = table["civilian_range"]
    rng = random.Random(body["seed"])
    rs = m["RandomizationService"]
    rspec = rs.get_default_phenotype_spec()
    rspec["phenotype"]["attributes"]["gender"]["allowed"] = [body["sex"]]
    macro = rs.randomize_macro_info_dict(rspec, rng)
    # One draw either way, so a row without a band rebuilds byte for byte.
    age_years = rng.uniform(*(cr["age_bands_years"][body["age_band"]] if body.get("age_band") else cr["age_years"]))
    macro["age"] = age_slider(age_years)
    w = cr["race_pin_weight"]
    race = {r: (1.0 - w) * macro["race"][r] + (w if r == body["race"] else 0.0) for r in npc_data.RACES}
    total = sum(race.values())
    macro["race"] = {r: race[r] / total for r in npc_data.RACES}
    h = rng.gauss(cr["height_mean_m"][body["sex"]], cr["height_sd_m"])
    height_m = min(max(h, cr["height_m"][0]), cr["height_m"][1])
    eyebrows = cr["eyebrows"][rng.randrange(len(cr["eyebrows"]))]
    eyes = cr["eyes"][rng.randrange(len(cr["eyes"]))]
    band = rs.skin_age_label(macro)
    if band not in ("young", "middleage", "old"):
        raise BuildError(f"{body['id']}: seed {body['seed']} gives skin age band {band!r}; adults only")
    if body.get("age_band") and band != body["age_band"]:
        raise BuildError(f"{body['id']}: age {age_years:.1f} gives MPFB's skin band {band!r}, not the row's "
                         f"{body['age_band']!r}: npcs.json civilian_range.age_bands_years is off MPFB's bands")
    spec.update(macro=macro, height_m=height_m, age_years=age_years, skin=f"{band}_{body['race']}_{body['sex']}",
                eyes=eyes, eyebrows=eyebrows, seed=body["seed"])
    return spec


def asset_fragments(table, spec):
    """(what, subdir, fragment) of every asset file the body loads, in a fixed order."""
    out = [("proxy", "proxymeshes", "{0}/{0}.proxy".format(table["proxies"][spec["sex"]])),
           ("skin", "skins", "{0}/{0}.mhmat".format(spec["skin"])),
           ("eyes", "eyes", "{0}/{0}.mhclo".format(table["eyes_model"])),
           ("eye colour", "eyes", "materials/{0}.mhmat".format(spec["eyes"])),
           ("eyebrows", "eyebrows", "{0}/{0}.mhclo".format(spec["eyebrows"])),
           ("eyelashes", "eyelashes", "{0}/{0}.mhclo".format(spec["eyelashes"]))]
    if spec["hair"]:
        out.append(("hair", "hair", "{0}/{0}.mhclo".format(spec["hair"])))
    for c in spec["clothes"]:
        out.append(("clothes", "clothes", "{0}/{0}.mhclo".format(c["asset"])))
    return out


SIBLING_EXTS = (".mhclo", ".mhmat", ".obj", ".proxy", ".png", ".jpg", ".mhpxy")


def resolve_assets(table, spec, m, allow):
    """Absolute paths of the body's assets, each proven to be a file of an allowlisted pack, with
    the files beside it that MPFB reads (the mesh, the material, its textures)."""
    paths = {}
    for what, subdir, frag in asset_fragments(table, spec):
        path = m["AssetService"].find_asset_absolute_path(frag, asset_subdir=subdir)
        if not path:
            raise BuildError(f"{spec['id']}: {what} asset {frag!r} is in no allowlisted pack")
        check_allowed(spec["id"], path, allow)
        folder = os.path.dirname(path)
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(SIBLING_EXTS) and name != os.path.basename(path):
                check_allowed(spec["id"], os.path.join(folder, name), allow)
        paths[frag] = path
    rig_dir = os.path.join(m["LocationService"].get_mpfb_data("rigs"), "standard")
    for name in (f"rig.{table['rig']}.json", f"weights.{table['rig']}.json"):
        if os.path.exists(os.path.join(rig_dir, name)):
            check_allowed(spec["id"], os.path.join(rig_dir, name), allow)
    return paths


def check_allowed(npc_id, path, allow):
    if allow.pack_of(path) is None:
        raise BuildError(f"{npc_id}: asset {path} is not a file of an allowlisted pack "
                         f"(tools/deps/character_packs.json); refused")


# ----------------------------------------------------------------------------- MPFB human

def clean_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images,
                 bpy.data.node_groups, bpy.data.actions):
        for d in list(coll):
            coll.remove(d)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def mesh_height(obj):
    """Standing height of a mesh as evaluated now (shape keys and masks applied), in metres."""
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    z = co[2::3] * obj.matrix_world.to_scale().z
    return float(z.max() - z.min())


def fit_height(spec, table, m):
    """MPFB's height slider that gives the row's height_m, by bisection on a bare base mesh
    (the slider is monotonic in height; everything else in the phenotype stays as drawn)."""
    hs, props, ts = m["HumanService"], m["HumanObjectProperties"], m["TargetService"]
    macro = dict(spec["macro"])
    macro["race"] = dict(spec["macro"]["race"])
    base = hs.create_human(macro_detail_dict=macro)

    def at(v):
        props.set_value("height", v, entity_reference=base)
        ts.reapply_macro_details(base)
        return mesh_height(base)

    target, tol = spec["height_m"], table["height_fit"]["tolerance_m"]
    lo, hi = 0.0, 1.0
    h_lo, h_hi = at(lo), at(hi)
    if not h_lo - tol <= target <= h_hi + tol:
        raise BuildError(f"{spec['id']}: height_m {target:.3f} is outside what this phenotype reaches "
                         f"({h_lo:.3f}-{h_hi:.3f} m)")
    best = None
    for _ in range(table["height_fit"]["max_iterations"]):
        v = 0.5 * (lo + hi)
        h = at(v)
        if best is None or abs(h - target) < abs(best[1] - target):
            best = (v, h)
        if abs(h - target) <= tol:
            break
        lo, hi = (v, hi) if h < target else (lo, v)
    v, h = best
    if abs(h - target) > tol:
        raise BuildError(f"{spec['id']}: height fit ended at {h:.4f} m for a target of {target:.4f} m "
                         f"(tolerance {tol} m)")
    mesh = base.data
    bpy.data.objects.remove(base, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return round(v, 6), h


def build_human(spec, table, m):
    hs = m["HumanService"]
    info = hs._create_default_human_info_dict()
    info["name"] = spec["id"]
    info["phenotype"] = spec["macro"]
    info["rig"] = table["rig"]
    info["proxy"] = "{0}/{0}.proxy".format(table["proxies"][spec["sex"]])
    info["eyes"] = "{0}/{0}.mhclo".format(table["eyes_model"])
    info["eyebrows"] = "{0}/{0}.mhclo".format(spec["eyebrows"])
    info["eyelashes"] = "{0}/{0}.mhclo".format(spec["eyelashes"])
    info["hair"] = "{0}/{0}.mhclo".format(spec["hair"]) if spec["hair"] else ""
    info["skin_mhmat"] = "{0}/{0}.mhmat".format(spec["skin"])
    info["skin_material_type"] = "GAMEENGINE"
    info["clothes"] = ["{0}/{0}.mhclo".format(c["asset"]) for c in spec["clothes"]]
    info["alternative_materials"] = {EYES_UUID: "materials/{0}.mhmat".format(spec["eyes"])}
    settings = hs.get_default_deserialization_settings()
    settings["subdiv_levels"] = 0
    settings["override_clothes_model"] = "GAMEENGINE"
    settings["override_eyes_model"] = "GAMEENGINE"
    return hs.deserialize_from_dict(info, settings)


def with_obj(obj, fn, **kw):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        return fn(**kw)


def apply_masks(obj):
    for mod in list(obj.modifiers):
        if mod.type == 'MASK':
            with_obj(obj, bpy.ops.object.modifier_move_to_index, modifier=mod.name, index=0)
            with_obj(obj, bpy.ops.object.modifier_apply, modifier=mod.name)
        elif mod.type == 'SUBSURF':
            obj.modifiers.remove(mod)


def decimate(obj, ratio):
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.ratio = ratio
    mod.use_symmetry = True
    with_obj(obj, bpy.ops.object.modifier_move_to_index, modifier=mod.name, index=0)
    with_obj(obj, bpy.ops.object.modifier_apply, modifier=mod.name)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def image_of(mat, node_name):
    if not mat or not mat.node_tree:
        return None
    n = mat.node_tree.nodes.get(node_name)
    return bpy.path.abspath(n.image.filepath) if n and n.image else None


def asset_name(obj):
    """The MPFB asset an object was loaded from (its object name ends in the asset name)."""
    return obj.name.split(".")[-1]


# ----------------------------------------------------------------------------- geometry queries

def world_coords(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world, np.float64)
    return co @ mw[:3, :3].T + mw[:3, 3]


def dominant_bones(obj, bone_names):
    """Per vertex, the name of the bone with the largest weight ('' when none)."""
    names = {g.index: g.name for g in obj.vertex_groups if g.name in bone_names}
    out = []
    for v in obj.data.vertices:
        best, bw = "", 0.0
        for g in v.groups:
            if g.group in names and g.weight > bw:
                best, bw = names[g.group], g.weight
        out.append(best)
    return np.array(out, dtype=object)


def cloud(parts, bone_names, spacing_m):
    """Points on every body part's surface at rest, no farther than spacing_m apart along each
    triangle's edges, with the bone that dominates each, for fitting gear around the body.
    Sampling the triangles, not only the vertices, keeps a long thin triangle from slipping
    through a band of gear between its corners."""
    pts, bones = [], []
    for o in parts:
        co = world_coords(o)
        dom = dominant_bones(o, bone_names)
        me = o.data
        me.calc_loop_triangles()
        tv = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", tv)
        tv = tv.reshape(-1, 3)
        a, b, c = co[tv[:, 0]], co[tv[:, 1]], co[tv[:, 2]]
        longest = np.maximum(np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1)),
                             np.linalg.norm(a - c, axis=1))
        steps = np.maximum(1, np.ceil(longest / spacing_m)).astype(np.int64)
        for n in sorted(set(steps.tolist())):
            sel = steps == n
            ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], np.float64) / n
            w = np.stack([1.0 - ij[:, 0] - ij[:, 1], ij[:, 0], ij[:, 1]], axis=1)
            p = (w[None, :, 0, None] * a[sel][:, None, :] + w[None, :, 1, None] * b[sel][:, None, :]
                 + w[None, :, 2, None] * c[sel][:, None, :])
            pts.append(p.reshape(-1, 3))
            bones.append(np.repeat(dom[tv[sel, 0]], len(ij)))
    return np.concatenate(pts), np.concatenate(bones)


def landmarks(rig, skin, eyes_obj, bone_names):
    """Named points at rest: per-bone centroids of the body mesh, and the eyes."""
    co = world_coords(skin)
    dom = dominant_bones(skin, bone_names)
    cent = {}
    for b in sorted(set(dom) - {""}):
        cent[b] = Vector(co[dom == b].mean(axis=0))
    eco = world_coords(eyes_obj)
    left, right = eco[eco[:, 0] > 0.0], eco[eco[:, 0] < 0.0]
    if not len(left) or not len(right):
        raise BuildError(f"{rig.name}: the eyes mesh has no left or right half")
    eye_l, eye_r = Vector(left.mean(axis=0)), Vector(right.mean(axis=0))
    return {"centroid": cent, "eye_l": eye_l, "eye_r": eye_r, "eyes": 0.5 * (eye_l + eye_r)}


# ----------------------------------------------------------------------------- gear

def gear_frame(piece, rig, marks, npc_id, name):
    """(origin, front, left, up) of a piece at rest, in world space."""
    bone = rig.data.bones.get(piece["bone"])
    if bone is None:
        raise BuildError(f"{npc_id}: gear piece {name} names bone {piece['bone']!r}, not in the {rig.name} rig")
    mw = rig.matrix_world
    head, tail = mw @ bone.head_local, mw @ bone.tail_local
    if piece["frame"] == "bone":
        up = (tail - head).normalized()
    else:
        up = UP.copy()
    front = FRONT - FRONT.dot(up) * up
    if front.length < 1e-6:
        front = UP - UP.dot(up) * up
    front.normalize()
    left = up.cross(front)
    o = piece["origin"]
    if o == "bone_head":
        base = head
    elif o == "bone_tail":
        base = tail
    elif o == "centroid":
        if piece["bone"] not in marks["centroid"]:
            raise BuildError(f"{npc_id}: gear piece {name}: no body vertices follow {piece['bone']}")
        base = marks["centroid"][piece["bone"]]
    else:
        base = marks[o]
    ol, of, ou = piece["offset_m"]
    return base + ol * left + of * front + ou * up, front, left, up


def fit_shell(piece, frame, pts, bones, npc_id, name):
    """Inner radius per grid node: the farthest body point near the node's direction (within the
    neighbouring cells, within reach), raised to a smooth, never lower surface, plus clearance."""
    origin, front, left, up = (np.array(v, np.float64) for v in frame)
    na, nb = piece["segments"]
    a0, a1 = piece["angle_deg"]
    closed = a1 - a0 >= 360.0 - 1e-6
    sphere = piece["shape"] == "sphere"
    b0, b1 = piece["elevation_deg"] if sphere else piece["along_m"]
    keep = np.isin(bones, piece["fit_bones"])
    d = pts[keep] - origin
    xf, xl, xu = d @ front, d @ left, d @ up
    ang = np.degrees(np.arctan2(xl, xf))
    ang = a0 + np.mod(ang - a0, 360.0)
    if sphere:
        horiz = np.hypot(xf, xl)
        b = np.degrees(np.arctan2(xu, horiz))
        rad = np.sqrt(horiz ** 2 + xu ** 2)
    else:
        b = xu
        rad = np.hypot(xf, xl)
    da, db = (a1 - a0) / na, (b1 - b0) / nb
    fi, fj = (ang - a0) / da, (b - b0) / db
    ok = (rad <= piece["reach_m"]) & (fj >= -1.0) & (fj <= nb + 1.0)
    if not closed:
        ok &= (fi >= -1.0) & (fi <= na + 1.0)
    fi, fj, rad = fi[ok], fj[ok], rad[ok]
    ni = na if closed else na + 1
    grid = np.full((ni, nb + 1), -1.0)
    base_i, base_j = np.floor(fi).astype(np.int64), np.floor(fj).astype(np.int64)
    for di in (-1, 0, 1, 2):
        for dj in (-1, 0, 1, 2):
            i, j = base_i + di, base_j + dj
            near = (np.abs(fi - i) <= 1.0) & (np.abs(fj - j) <= 1.0) & (j >= 0) & (j <= nb)
            if closed:
                i = np.mod(i, na)
            else:
                near &= (i >= 0) & (i <= na)
            np.maximum.at(grid, (i[near], j[near]), rad[near])
    if (grid < 0).all():
        raise BuildError(f"{npc_id}: gear piece {name} finds no body within reach_m {piece['reach_m']} "
                         f"of its origin; check bone, origin and fit_bones")
    for _ in range(4 * (ni + nb)):  # fill cells with no body behind them from their neighbours
        empty = grid < 0
        if not empty.any():
            break
        acc, cnt = np.zeros_like(grid), np.zeros_like(grid)
        for sh, ax in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            nb_ = np.roll(grid, sh, axis=ax)
            valid = nb_ >= 0
            if not closed and ax == 0:
                valid[0 if sh == 1 else -1, :] = False
            if ax == 1:
                valid[:, 0 if sh == 1 else -1] = False
            acc += np.where(valid, nb_, 0.0)
            cnt += valid
        grid = np.where(empty & (cnt > 0), acc / np.maximum(cnt, 1), grid)
    for _ in range(2):  # smooth upward only: a node never drops below what it covers
        pad = np.pad(grid, ((0, 0), (1, 1)), mode="edge")
        pad = np.pad(pad, ((1, 1), (0, 0)), mode="wrap" if closed else "edge")
        mean = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]) / 4.0
        grid = np.maximum(grid, mean)
    if sphere:
        for j, e in ((0, b0), (nb, b1)):
            if abs(e) >= 90.0 - 1e-6:
                grid[:, j] = grid[:, j].max()
    return grid + piece["clearance_m"], closed


def shell_mesh(piece, frame, inner, closed, name):
    """A closed solid: the inner and outer surfaces of the wrap and the walls along its borders.
    Returns (verts, faces, uvs per face corner) with UVs in 0..1 over the wrap's grid."""
    origin, front, left, up = frame
    na, nb = piece["segments"]
    a0, a1 = piece["angle_deg"]
    sphere = piece["shape"] == "sphere"
    b0, b1 = piece["elevation_deg"] if sphere else piece["along_m"]
    ni = na if closed else na + 1
    thick = piece["thickness_m"]
    verts, index = [], {}

    def point(i, j, r):
        a = math.radians(a0 + (a1 - a0) * i / na)
        if sphere:
            e = math.radians(b0 + (b1 - b0) * j / nb)
            dirv = (math.cos(e) * (math.cos(a) * front + math.sin(a) * left) + math.sin(e) * up)
            return origin + r * dirv
        h = b0 + (b1 - b0) * j / nb
        return origin + h * up + r * (math.cos(a) * front + math.sin(a) * left)

    def pole(j):
        return sphere and abs((b0 if j == 0 else b1 if j == nb else 0.0)) >= 90.0 - 1e-6 and j in (0, nb)

    def vid(i, j, side):
        i = i % na if closed else i
        key = (0 if pole(j) else i, j, side)
        if key not in index:
            r = float(inner[key[0] % ni, j]) + (thick if side else 0.0)
            index[key] = len(verts)
            verts.append(point(key[0], j, r))
        return index[key]

    faces, uvs = [], []

    def add(corners):
        ids, uv, seen = [], [], set()
        for (i, j, side) in corners:
            k = vid(i, j, side)
            if k in seen:
                continue
            seen.add(k)
            ids.append(k)
            uv.append((i / na, j / nb))
        if len(ids) >= 3:
            faces.append(ids)
            uvs.append(uv)

    icount = na
    for i in range(icount):
        for j in range(nb):
            add([(i, j, 1), (i + 1, j, 1), (i + 1, j + 1, 1), (i, j + 1, 1)])
            add([(i, j + 1, 0), (i + 1, j + 1, 0), (i + 1, j, 0), (i, j, 0)])
    for j in (0, nb):
        if pole(j):
            continue
        for i in range(icount):
            add([(i, j, 0), (i + 1, j, 0), (i + 1, j, 1), (i, j, 1)])
    if not closed:
        for i in (0, na):
            for j in range(nb):
                add([(i, j, 0), (i, j + 1, 0), (i, j + 1, 1), (i, j, 1)])
    return verts, faces, uvs


def make_gear_object(name, piece, verts, faces, uvs, rig, uv_name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in verts]
    uvl = bm.loops.layers.uv.new(uv_name)
    for f_ids, f_uv in zip(faces, uvs):
        f = bm.faces.new([bv[k] for k in f_ids])
        for loop, uv in zip(f.loops, f_uv):
            loop[uvl].uv = uv
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(50.0))
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    grp = obj.vertex_groups.new(name=piece["bone"])
    grp.add(list(range(len(verts))), 1.0, 'REPLACE')
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = rig
    return obj


def build_gear(table, spec, rig, parts, skin, eyes_obj, uv_name):
    """Every gear piece the body wears, as objects skinned to one bone each, and the swatch each uses."""
    pieces = npc_data.pieces_of(table, spec)
    if not pieces:
        return [], {}
    bone_names = {b.name for b in rig.data.bones}
    pts, bones = cloud(parts, bone_names, table["gear_style"]["sample_m"])
    marks = landmarks(rig, skin, eyes_obj, bone_names)
    objs, swatch_of, built = [], {}, {}
    for name, piece in pieces:
        for b in piece["fit_bones"]:
            if b not in bone_names:
                raise BuildError(f"{spec['id']}: gear piece {name} fits to bone {b!r}, not in the rig")
        frame = gear_frame(piece, rig, marks, spec["id"], name)
        fit_pts, fit_bones = pts, bones
        if piece["over"]:  # a layered piece clears the pieces under it as it clears the body
            under_pts, _ = cloud([built[u] for u in piece["over"]], bone_names, table["gear_style"]["sample_m"])
            fit_pts = np.concatenate([pts, under_pts])
            fit_bones = np.concatenate([bones, np.full(len(under_pts), piece["fit_bones"][0], dtype=object)])
        inner, closed = fit_shell(piece, frame, fit_pts, fit_bones, spec["id"], name)
        verts, faces, uvs = shell_mesh(piece, frame, inner, closed, name)
        obj = make_gear_object(f"{spec['id']}.gear_{name}", piece, verts, faces, uvs, rig, uv_name)
        obj["gear_piece"] = name
        objs.append(obj)
        built[name] = obj
        key = swatch_key(piece)
        swatch_of.setdefault(key, len(swatch_of))
        obj["swatch"] = swatch_of[key]
    room = table["gear_style"]["swatches_per_row"] ** 2
    if len(swatch_of) > room:
        raise BuildError(f"{spec['id']}: its gear uses {len(swatch_of)} colour schemes, the gear tile holds {room} "
                         f"(gear_style.swatches_per_row)")
    return objs, swatch_of


def swatch_key(piece):
    stripe = piece["stripe"]
    return (piece["colour"], piece["colour2"], round(piece["mix"], 4),
            (stripe["colour"], tuple(round(v, 4) for v in stripe["v"])) if stripe else None)


# ----------------------------------------------------------------------------- stress pose check

def apply_pose(rig, pose):
    """Rotations about armature-space axes, applied in each bone's rest frame; {} resets to rest."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    for bname in sorted(pose):
        pb = rig.pose.bones.get(bname)
        if pb is None:
            raise BuildError(f"{rig.name}: stress_pose names bone {bname!r}, not in the rig")
        rest = pb.bone.matrix_local.to_3x3()
        r = Matrix.Rotation(math.radians(pose[bname]["deg"]), 3, pose[bname]["axis"])
        pb.rotation_quaternion = (rest.inverted() @ r @ rest).to_quaternion()
    bpy.context.view_layer.update()


def posed_tree(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        mw = o.matrix_world
        verts += [mw @ v.co for v in me.vertices]
        polys += [[base + k for k in p.vertices] for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False, epsilon=0.0)


def poke_through(gear, body_parts, rig, pose):
    """Pairs of intersecting triangles between each gear piece and the body, and between gear
    pieces on the same bone (they never move apart, so they must never cross), at rest and posed."""
    found = {}
    for label, p in (("rest", {}), ("stress pose", pose)):
        apply_pose(rig, p)
        body = posed_tree(body_parts)
        trees = [(g["gear_piece"], g.vertex_groups[0].name, posed_tree([g])) for g in gear]
        for i, (name, bone, tree) in enumerate(trees):
            n = len(tree.overlap(body))
            if n:
                found[(label, name)] = n
            for other, other_bone, other_tree in trees[i + 1:]:
                n = len(tree.overlap(other_tree)) if bone == other_bone else 0
                if n:
                    found[(label, f"{name} x {other}")] = n
    apply_pose(rig, {})
    return found


# ----------------------------------------------------------------------------- textures

def load_pixels(path, size):
    """An image file resized to size x size, float32 (size, size, 4), bottom-left origin, raw values."""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    img.scale(size, size)
    buf = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(size, size, 4)


def luminance(px):
    return px[..., 0] * 0.2126 + px[..., 1] * 0.7152 + px[..., 2] * 0.0722


def recolour(px, mask, rgb, contrast, max_ratio):
    """Pixels under mask take the colour rgb, keeping their light and dark relative to the mean.
    The ratio to the mean is held within 1/max_ratio..max_ratio, so a part far lighter than the
    rest (a white sock on a black shoe) doesn't turn bright."""
    if not mask.any():
        return px
    lum = luminance(px)
    mean = max(float(lum[mask].mean()), 1e-4)
    ratio = np.clip(lum / mean, 1.0 / max_ratio, max_ratio)
    k = 1.0 + contrast * (ratio - 1.0)
    out = px.copy()
    for c in range(3):
        out[..., c] = np.where(mask, np.clip(rgb[c] * k, 0.0, 1.0), px[..., c])
    return out


def uv_triangles(obj):
    """Per triangle, its three UVs (clamped to 0..1) from the active UV map."""
    me = obj.data
    me.calc_loop_triangles()
    uvl = me.uv_layers.active.data
    uv = np.empty(len(uvl) * 2, np.float64)
    uvl.foreach_get("uv", uv)
    uv = np.clip(uv.reshape(-1, 2), 0.0, 1.0)
    loops = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", loops)
    polys = np.empty(len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get("polygon_index", polys)
    return uv[loops.reshape(-1, 3)], polys


def raster_mask(tris, size):
    """Pixels whose centres lie in any of the UV triangles, as a bool (size, size) mask."""
    mask = np.zeros((size, size), bool)
    for tri in tris * size - 0.5:
        x0, y0 = np.floor(tri.min(axis=0)).astype(int)
        x1, y1 = np.ceil(tri.max(axis=0)).astype(int)
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = tri
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue
        w0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / det
        w1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / det
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (1.0 - w0 - w1 >= -1e-6)
        mask[y0:y1 + 1, x0:x1 + 1] |= inside
    return mask


def dilate(mask, px):
    for _ in range(px):
        m = mask.copy()
        m[1:, :] |= mask[:-1, :]
        m[:-1, :] |= mask[1:, :]
        m[:, 1:] |= mask[:, :-1]
        m[:, :-1] |= mask[:, 1:]
        mask = m
    return mask


def components(obj):
    """Connected pieces of a mesh (faces sharing a vertex), as a component id per polygon."""
    me = obj.data
    parent = list(range(len(me.vertices)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for e in me.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[max(a, b)] = min(a, b)
    return np.array([find(p.vertices[0]) for p in me.polygons], np.int64)


def paint_out(px, rects):
    """Fill each UV rect (u0, v0, u1, v1) from its border: the mean of a left-right and a
    bottom-top blend of the texels just outside it. Takes a print off a garment, keeps the shading."""
    size = px.shape[0]
    for u0, v0, u1, v1 in rects:
        x0, x1 = max(int(u0 * size), 1), min(int(math.ceil(u1 * size)), size - 2)
        y0, y1 = max(int(v0 * size), 1), min(int(math.ceil(v1 * size)), size - 2)
        tx = ((np.arange(x0, x1 + 1) - (x0 - 1)) / (x1 - x0 + 2))[None, :, None]
        ty = ((np.arange(y0, y1 + 1) - (y0 - 1)) / (y1 - y0 + 2))[:, None, None]
        left, right = px[y0:y1 + 1, x0 - 1][:, None, :], px[y0:y1 + 1, x1 + 1][:, None, :]
        bottom, top = px[y0 - 1, x0:x1 + 1][None, :, :], px[y1 + 1, x0:x1 + 1][None, :, :]
        px[y0:y1 + 1, x0:x1 + 1] = 0.5 * ((1 - tx) * left + tx * right) + 0.5 * ((1 - ty) * bottom + ty * top)
    return px


def garment_pixels(obj, path, cloth, size, height, tint_cfg, palette, fixes):
    """A garment's albedo at size px, tinted as the row asks: the whole garment, or its top and
    bottom, told apart by connected piece. A piece is bottom when its mean height is under
    split_height_frac of the body's height, or when it reaches below legwear_below_frac (trousers
    and overalls, whose bib pulls their mean up); every other piece is top."""
    px = load_pixels(path, size)
    if asset_name(obj) in fixes:
        px = paint_out(px, fixes[asset_name(obj)]["paint_out_uv"])
    if cloth is None or (cloth["tint"] is None and cloth["top"] is None and cloth["bottom"] is None):
        return px
    tris, polys = uv_triangles(obj)
    contrast = tint_cfg["contrast"]
    if cloth["tint"] is not None:
        mask = dilate(raster_mask(tris, size), tint_cfg["mask_dilate_px"])
        return recolour(px, mask, palette[cloth["tint"]], contrast, tint_cfg["max_ratio"])
    comp = components(obj)
    co = world_coords(obj)
    split_z, legs_z = tint_cfg["split_height_frac"] * height, tint_cfg["legwear_below_frac"] * height
    is_top = {}
    for c in sorted(set(comp.tolist())):
        idx = sorted({v for p, pc in zip(obj.data.polygons, comp) if pc == c for v in p.vertices})
        z = co[idx, 2]
        is_top[c] = bool(z.mean() >= split_z and z.min() >= legs_z)
    top_poly = np.array([is_top[c] for c in comp])
    for want, key in ((True, "top"), (False, "bottom")):
        if cloth[key] is None:
            continue
        sel = top_poly[polys] == want
        mask = dilate(raster_mask(tris[sel], size), tint_cfg["mask_dilate_px"])
        other = raster_mask(tris[~sel], size)
        px = recolour(px, mask & ~other, palette[cloth[key]], contrast, tint_cfg["max_ratio"])
    return px


def blur(a, sigma):
    """A Gaussian blur of sigma pixels, by FFT (Blender's Python has numpy and no scipy). It wraps
    at the edges, where a MakeHuman skin's UV islands don't reach."""
    h, w = a.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2.0 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))))


SKIN_ROUGHNESS = os.path.join(HERE, "npc_skin_roughness.png")   # make_skin_roughness.py authors it


def skin_normal_pixels(path, size, cfg):
    """The skin's tangent-space normal map, derived from its own colour map at full resolution
    (openspec/changes/character-lighting, design section 1): the luminance less its blur is the
    height (pores and creases are darker, so lower), its slope scaled by cfg["strength"] tilts
    the normal, and the result is resampled to size x size and renormalised. OpenGL convention
    (+Y up the texture), as glTF's normalTexture wants. The alpha carries the skin's roughness
    (npc_skin_roughness.png, in the MakeHuman UV layout every skin shares)."""
    if not os.path.exists(SKIN_ROUGHNESS):
        raise BuildError(f"{SKIN_ROUGHNESS} is missing: run tools/blender/make_skin_roughness.py")
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    buf = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(buf)
    px = buf.reshape(h, w, 4)
    lum = luminance(px).astype(np.float64)
    height = -(lum - blur(lum, cfg["blur_px"]))
    k = cfg["strength"]
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    n = np.stack([-k * dx, -k * dy, np.ones_like(height)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    enc = np.concatenate([n * 0.5 + 0.5, np.ones((h, w, 1))], axis=-1).astype(np.float32)
    img.pixels.foreach_set(enc.ravel())
    img.scale(size, size)
    out = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(out)
    bpy.data.images.remove(img)
    out = out.reshape(size, size, 4)
    v = out[..., :3] * 2.0 - 1.0
    v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
    out[..., :3] = v * 0.5 + 0.5
    out[..., 3] = load_pixels(SKIN_ROUGHNESS, size)[..., 0]
    return out


def skin_pixels(path, size, tone, strength):
    """The skin texture with its mean colour moved to the row's skin tone (a per-channel gain)."""
    px = load_pixels(path, size)
    if tone is None or strength == 0.0:
        return px
    lum = luminance(px)
    used = lum > 0.05
    mean = px[used][:, :3].mean(axis=0)
    gain = 1.0 + strength * (np.array(tone, np.float32) / np.maximum(mean, 1e-4) - 1.0)
    out = px.copy()
    out[..., :3] = np.clip(px[..., :3] * gain, 0.0, 1.0)
    return out


def hair_pixels(path, size, tint, tint_cfg):
    px = load_pixels(path, size)
    if tint is None:
        return px
    return recolour(px, px[..., 3] > 0.5, tint, tint_cfg["contrast"], tint_cfg["max_ratio"])


def value_noise(rng, cells, size):
    """Smooth noise in 0..1: a cells x cells random lattice, bilinearly upsampled to size x size."""
    lat = rng.random((cells + 1, cells + 1))
    t = np.linspace(0.0, cells, size, endpoint=False) + cells / (2.0 * size)
    i = np.floor(t).astype(int)
    f = t - i
    f = f * f * (3.0 - 2.0 * f)
    a = lat[i][:, i] * (1 - f)[None, :] + lat[i][:, i + 1] * f[None, :]
    b = lat[i + 1][:, i] * (1 - f)[None, :] + lat[i + 1][:, i + 1] * f[None, :]
    return a * (1 - f)[:, None] + b * f[:, None]


def swatch_span(k, per, size):
    """Pixel range [lo, hi) of swatch column or row k of per, in a tile of size px."""
    return int(round(k * size / per)), int(round((k + 1) * size / per))


def gear_tile(swatch_of, size, style, palette, seed):
    """The gear's part of the outfit atlas: one square swatch per colour scheme, with a little
    seeded noise, a second colour mixed in patches, and an optional stripe across v."""
    per = style["swatches_per_row"]
    tile = np.zeros((size, size, 4), np.float32)
    tile[..., 3] = 1.0
    for key, k in sorted(swatch_of.items(), key=lambda kv: kv[1]):
        colour, colour2, mix, stripe = key
        x0, x1 = swatch_span(k % per, per, size)
        y0, y1 = swatch_span(k // per, per, size)
        cell = max(x1 - x0, y1 - y0)
        rng = np.random.default_rng(zlib.crc32(f"{seed}:{key}".encode()))
        shade = (1.0 + style["noise"] * (2.0 * value_noise(rng, style["noise_cells"], cell) - 1.0))[..., None]
        rgb = np.array(palette[colour], np.float32)[None, None, :] * shade
        if colour2 is not None:
            patches = value_noise(rng, style["noise_cells"], cell) < mix
            rgb = np.where(patches[..., None], np.array(palette[colour2], np.float32)[None, None, :] * shade, rgb)
        if stripe is not None:
            s_col, (v0, v1) = stripe
            v = (np.arange(cell) + 0.5) / cell
            rgb[(v >= v0) & (v <= v1), :, :] = np.array(palette[s_col], np.float32)
        tile[y0:y1, x0:x1, :3] = np.clip(rgb[:y1 - y0, :x1 - x0], 0.0, 1.0)
    return tile


def set_gear_uvs(gear, style):
    """Put each gear piece's 0..1 grid UVs inside its swatch, a tenth of a swatch in from its edges
    so filtering and mip levels don't reach the neighbouring swatch."""
    per = style["swatches_per_row"]
    for g in gear:
        k = g["swatch"]
        cx, cy = (k % per) / per, (k // per) / per
        margin = 0.1 / per
        uvl = g.data.uv_layers.active.data
        uv = np.empty(len(uvl) * 2, np.float64)
        uvl.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        uv = np.stack([cx + margin + uv[:, 0] * (1.0 / per - 2 * margin),
                       cy + margin + uv[:, 1] * (1.0 / per - 2 * margin)], axis=1)
        uvl.foreach_set("uv", uv.ravel())


def build_atlas(items, tpl, atlas_px, out_png, fill, remap):
    """items: (objects, pixels(size)) per tile, in fill order. Writes the atlas PNG and, with
    remap, moves each object's UVs into its tile."""
    k = atlas_px / 1024.0
    rects = [(int(x * k), int(y * k), int(s * k)) for x, y, s in tpl]
    if len(items) > len(rects):
        raise BuildError(f"{os.path.basename(out_png)}: {len(items)} tiles, the template has {len(rects)}")
    atlas = np.tile(np.array(fill, np.float32), (atlas_px, atlas_px, 1))
    for (objs, pixels), (x0, y0, s) in zip(items, rects):
        inner = s - 2 * PAD_PX
        px = np.pad(pixels(inner), ((PAD_PX, PAD_PX), (PAD_PX, PAD_PX), (0, 0)), mode='edge')
        atlas[y0:y0 + s, x0:x0 + s] = px
        if remap:
            for obj in objs:
                uvl = obj.data.uv_layers.active.data
                uv = np.empty(len(uvl) * 2, np.float64)
                uvl.foreach_get("uv", uv)
                uv = np.clip(uv.reshape(-1, 2), 0.0, 1.0)
                uv[:, 0] = (x0 + PAD_PX + uv[:, 0] * inner) / atlas_px
                uv[:, 1] = (y0 + PAD_PX + uv[:, 1] * inner) / atlas_px
                uvl.foreach_set("uv", uv.ravel())
    img = bpy.data.images.new(os.path.basename(out_png)[:-4], atlas_px, atlas_px, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.ascontiguousarray(atlas, np.float32).ravel())
    img.filepath_raw = out_png
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return out_png


def make_material(name, albedo, normal=None, alpha_clip=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.7
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(albedo)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_clip:
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = 'ROUND'  # the glTF exporter reads this as alphaMode MASK, cutoff 0.5
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    if normal:
        ntex = nt.nodes.new("ShaderNodeTexImage")
        ntex.image = bpy.data.images.load(normal)
        ntex.image.colorspace_settings.name = 'Non-Color'
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ----------------------------------------------------------------------------- glb and budget

def image_size(blob):
    """(width, height) of a PNG or WebP (lossy VP8, lossless VP8L or extended VP8X), else (None, None)."""
    if blob[:4] == b"\x89PNG":
        return struct.unpack(">II", blob[16:24])
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        kind = blob[12:16]
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", blob[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L":
            bits = int.from_bytes(blob[21:25], "little")
            return 1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)
        if kind == b"VP8X":
            return 1 + int.from_bytes(blob[24:27], "little"), 1 + int.from_bytes(blob[27:30], "little")
    return None, None


def glb_stats(path):
    """What a glb holds, read from the file itself: triangles, vertices, materials, images, bones."""
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    tris = sum(j["accessors"][p["indices"]]["count"] // 3 for mesh in j["meshes"] for p in mesh["primitives"])
    verts = sum(j["accessors"][p["attributes"]["POSITION"]]["count"] for m in j["meshes"] for p in m["primitives"])
    imgs = []
    for im in j.get("images", []):
        bv = j["bufferViews"][im["bufferView"]]
        off = 20 + jlen + 8 + bv.get("byteOffset", 0)
        blob = data[off:off + bv["byteLength"]]
        w, h = image_size(blob)
        imgs.append({"name": im.get("name"), "mime": im["mimeType"], "px": [w, h], "bytes": bv["byteLength"]})
    return {"glb_bytes": len(data), "triangles": tris, "vertices": verts,
            "materials": len(j.get("materials", [])), "images": imgs,
            "bones": len(j["skins"][0]["joints"]) if j.get("skins") else 0,
            "animations": len(j.get("animations", [])),
            "uv_sets": max(sum(1 for k in p["attributes"] if k.startswith("TEXCOORD"))
                           for m in j["meshes"] for p in m["primitives"]),
            "sha256": hashlib.sha256(data).hexdigest()}


def check_budget(npc_id, stats, budget):
    """Fail naming the NPC and the number when the glb is over any line of the budget."""
    over = []
    if stats["triangles"] > budget["triangles"]:
        over.append(f"{stats['triangles']} triangles (budget {budget['triangles']})")
    if stats["materials"] > budget["materials"]:
        over.append(f"{stats['materials']} materials (budget {budget['materials']})")
    if len(stats["images"]) > budget["textures"]:
        over.append(f"{len(stats['images'])} textures (budget {budget['textures']})")
    for im in stats["images"]:
        if im["px"][0] is None or max(im["px"]) > budget["texture_px"]:
            over.append(f"texture {im['name']} at {im['px']} px (budget {budget['texture_px']})")
    if stats["bones"] > budget["bones"]:
        over.append(f"{stats['bones']} bones (budget {budget['bones']})")
    if stats["animations"]:
        over.append(f"{stats['animations']} animations (bodies carry none)")
    if over:
        raise BuildError(f"{npc_id}: over budget: " + "; ".join(over))


# ----------------------------------------------------------------------------- one body

def prepare_body(table, body, m, allow):
    """A body's parts at rest, before gear and textures: the fitted MakeHuman body, its rig, the
    meshes by kind with their source textures, the skin and the eyes. build_body goes on from
    here; make_skin_roughness.py reads the skin's UVs and shape from it."""
    clean_scene()
    spec = resolve_body(table, body, m)
    resolve_assets(table, spec, m, allow)
    spec["macro"]["height"], fitted_h = fit_height(spec, table, m)
    basemesh = build_human(spec, table, m)
    rig = basemesh.parent
    for img in bpy.data.images:
        if img.filepath:
            check_allowed(spec["id"], bpy.path.abspath(img.filepath), allow)
    gop = m["GeneralObjectProperties"]
    parts = sorted([o for o in bpy.data.objects if o.type == 'MESH' and o is not basemesh], key=lambda o: o.name)
    kinds = {o.name: str(gop.get_value("object_type", entity_reference=o)) for o in parts}
    src = {o.name: {"diffuse": image_of(o.active_material, "DiffuseTexture"),
                    "normal": image_of(o.active_material, "NormalMapTextue")} for o in parts}
    bpy.data.objects.remove(basemesh, do_unlink=True)
    for o in parts:
        apply_masks(o)
        ratio = table["decimate"].get(asset_name(o))
        if ratio:
            decimate(o, ratio)
    skin = next(o for o in parts if kinds[o.name] == "Proxymeshes")
    eyes = next(o for o in parts if kinds[o.name] == "Eyes")
    return {"spec": spec, "fitted_h": fitted_h, "rig": rig, "parts": parts, "kinds": kinds, "src": src,
            "skin": skin, "eyes": eyes}


def build_body(table, body, m, allow, work, save_blend=None, verify=False):
    t0 = time.time()
    b = prepare_body(table, body, m, allow)
    spec, fitted_h, rig, parts, kinds, src, skin, eyes = (b[k] for k in ("spec", "fitted_h", "rig", "parts", "kinds",
                                                                          "src", "skin", "eyes"))
    height = float(world_coords(skin)[:, 2].max())
    uv_name = skin.data.uv_layers.active.name

    gear, swatch_of = build_gear(table, spec, rig, parts, skin, eyes, uv_name)
    if save_blend:  # for looking at a body in Blender before the checks; never committed
        os.makedirs(save_blend, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(save_blend, spec["id"] + ".blend"), copy=True)
    found = poke_through(gear, parts, rig, table["stress_pose"]) if gear else {}
    if found:
        worst = ", ".join(f"{piece} at {pose}: {n} triangle pairs" for (pose, piece), n in sorted(found.items()))
        raise BuildError(f"{spec['id']}: gear intersects the body or other gear ({worst})")

    # atlases: skin | outfit (clothes by size, eyes, gear) + its normals | hair, brows, lashes
    tex = os.path.join(work, spec["id"])
    os.makedirs(tex, exist_ok=True)
    pal, tint = table["palette"], table["tint"]
    atlas_px = table["atlas_px"]
    cloth_of = {c["asset"]: c for c in spec["clothes"]}
    clothes = sorted([o for o in parts if kinds[o.name] == "Clothes"], key=lambda o: (-tri_count(o), o.name))
    hair = sorted([o for o in parts if kinds[o.name] in HAIR_KINDS], key=lambda o: HAIR_KINDS.index(kinds[o.name]))
    tone = pal[spec["skin_tone"]] if spec["skin_tone"] else None

    def garment(o):
        return lambda s: garment_pixels(o, src[o.name]["diffuse"], cloth_of.get(asset_name(o)), s, height, tint, pal,
                                        table["texture_fixes"])

    def plain(path, fill):
        return (lambda s: load_pixels(path, s)) if path else (lambda s: np.tile(np.array(fill, np.float32), (s, s, 1)))

    def hair_px(o):
        want = {"Hair": spec["hair_tint"], "Eyebrows": spec["brow_tint"]}.get(kinds[o.name])
        return lambda s: hair_pixels(src[o.name]["diffuse"], s, pal[want] if want else None, tint)

    flat_n = (0.5, 0.5, 1.0, 1.0)
    rough = table["outfit_roughness"]

    def with_roughness(pixels, r):
        """The outfit normal's alpha is its roughness: the eyes wet, the clothes and gear cloth."""
        def px(s):
            out = np.array(pixels(s), np.float32)
            out[..., 3] = r
            return out
        return px

    outfit_items = ([([o], garment(o)) for o in clothes]
                    + [([eyes], plain(src[eyes.name]["diffuse"], (0.2, 0.2, 0.2, 1)))])
    normal_items = ([([o], with_roughness(plain(src[o.name]["normal"], flat_n), rough["cloth"])) for o in clothes]
                    + [([eyes], with_roughness(plain(None, flat_n), rough["eyes"]))])
    if gear:
        set_gear_uvs(gear, table["gear_style"])
        outfit_items.append((gear, lambda s: gear_tile(swatch_of, s, table["gear_style"], pal, body_seed(table, body))))
        normal_items.append((gear, with_roughness(plain(None, flat_n), rough["cloth"])))
    def skin_px(s):
        return skin_pixels(src[skin.name]["diffuse"], s, tone, table["skin_tone_strength"])

    def skin_n(s):
        return skin_normal_pixels(src[skin.name]["diffuse"], s, table["skin_normal"])

    a_skin = build_atlas([([skin], skin_px)],
                         T1024, atlas_px, os.path.join(tex, "skin_albedo.png"), (0.5, 0.4, 0.35, 1), True)
    n_skin = build_atlas([([skin], skin_n)], T1024, atlas_px, os.path.join(tex, "skin_normal.png"), flat_n, False)
    n_out = build_atlas(normal_items, T768, atlas_px, os.path.join(tex, "outfit_normal.png"), flat_n, False)
    a_out = build_atlas(outfit_items, T768, atlas_px, os.path.join(tex, "outfit_albedo.png"), (0.2, 0.2, 0.2, 1), True)
    a_hair = build_atlas([([o], hair_px(o)) for o in hair], T768, atlas_px, os.path.join(tex, "hair_albedo.png"),
                         (0.1, 0.08, 0.06, 0), True)
    m_skin = make_material(spec["id"] + "_skin", a_skin, normal=n_skin)
    m_out = make_material(spec["id"] + "_outfit", a_out, normal=n_out)
    m_hair = make_material(spec["id"] + "_hair", a_hair, alpha_clip=True)
    for group, mat in (([skin], m_skin), (clothes + [eyes] + gear, m_out), (hair, m_hair)):
        for o in group:
            o.data.materials.clear()
            o.data.materials.append(mat)

    gear_tris = sum(tri_count(g) for g in gear)
    gear_names = [g["gear_piece"] for g in gear]
    # one skinned mesh, only bone groups left
    objs = [skin] + [o for o in parts + gear if o is not skin]
    with bpy.context.temp_override(object=skin, active_object=skin, selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    skin.name = skin.data.name = spec["id"] + "_mesh"
    rig.name = spec["id"]
    for mod in skin.modifiers:
        if mod.type == 'ARMATURE':
            mod.object = rig
    bones = {b.name for b in rig.data.bones}
    for g in list(skin.vertex_groups):
        if g.name not in bones:
            skin.vertex_groups.remove(g)
    while len(skin.data.uv_layers) > 1:
        skin.data.uv_layers.remove(next(u for u in skin.data.uv_layers if u.name != uv_name))

    out_dir = os.path.join(ROOT, table["out_dir"])
    os.makedirs(out_dir, exist_ok=True)
    glb = os.path.join(out_dir, spec["id"] + ".glb")
    tmp = os.path.join(tex, spec["id"] + ".glb")
    for o in bpy.data.objects:
        o.select_set(o in (rig, skin))
    bpy.context.view_layer.objects.active = rig
    fmt = {"png": "AUTO", "webp": "WEBP"}[table["texture_format"]]
    bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB', use_selection=True, export_yup=True,
                              export_skins=True, export_animations=False, export_morph=False,
                              export_image_format=fmt, export_image_quality=table["webp_quality"],
                              export_image_webp_fallback=False, export_materials='EXPORT',
                              export_rest_position_armature=True, export_def_bones=False)
    stats = glb_stats(tmp)
    check_budget(spec["id"], stats, table["budget"])
    if verify:
        # The rebuild must match the committed glb byte for byte (the spec's "same table, same files").
        with open(glb, "rb") as f:
            have = hashlib.sha256(f.read()).hexdigest()
        os.remove(tmp)
        if have != stats["sha256"]:
            raise BuildError(f"{spec['id']}: the rebuild differs from the committed glb "
                             f"({stats['sha256'][:12]} built, {have[:12]} committed)")
    else:
        os.replace(tmp, glb)
    stats.update({"id": spec["id"], "kind": body["kind"], "height_m": round(spec["height_m"], 3),
                  "height_fitted_m": round(fitted_h, 4), "height_slider": spec["macro"]["height"],
                  "age_years": round(spec["age_years"], 1), "skin": spec["skin"], "eyes": spec["eyes"],
                  "eyebrows": spec["eyebrows"], "gear_pieces": gear_names,
                  "gear_triangles": gear_tris,
                  "build_s": round(time.time() - t0, 2)})
    return stats


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    report = argv[argv.index("--report") + 1] if "--report" in argv else None
    save_blend = argv[argv.index("--save-blend") + 1] if "--save-blend" in argv else None
    table_path = argv[argv.index("--table") + 1] if "--table" in argv else npc_data.TABLE
    verify = "--verify" in argv
    try:
        ensure_private_blender()
        table = npc_data.load(table_path)
        packs = deps.load_packs()
        allow = install_packs([deps.pack_by_id(MPFB_PACK, packs), deps.pack_by_id(ASSET_PACK, packs)])
        m = mpfb()
        bodies = [b for b in table["bodies"] if only is None or b["id"] in only]
        if only and len(bodies) != len(only):
            raise BuildError(f"--only names ids not in npcs.json: {sorted(only - {b['id'] for b in bodies})}")
        work = os.path.join(deps.cache_dir(), "work", "npcs")
        rows = []
        for body in bodies:
            s = build_body(table, body, m, allow, work, save_blend, verify)
            rows.append(s)
            print(f"[npc] {s['id']:12s} tris {s['triangles']:6d} verts {s['vertices']:6d} mats {s['materials']} "
                  f"tex {len(s['images'])}x{s['images'][0]['px'][0]} bones {s['bones']} glb {s['glb_bytes']:8d} "
                  f"height {s['height_fitted_m']:.3f} m  {s['build_s']:5.2f} s  {s['sha256'][:12]}", flush=True)
    except (BuildError, deps.PackError, npc_data.DataError) as e:
        print("FAIL", e, flush=True)
        sys.exit(1)
    except Exception:  # Blender would print the traceback and still exit 0
        traceback.print_exc()
        print("FAIL the build stopped on the error above", flush=True)
        sys.exit(1)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1, sort_keys=True)
    print(f"OK {len(rows)} bodies {'match their committed glbs' if verify else 'written to ' + table['out_dir']}", flush=True)


if __name__ == "__main__":
    main()

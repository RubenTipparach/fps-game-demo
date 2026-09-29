"""Measurement instrument: MPFB 2.0.17 human -> game-ready skinned glb, headless.

Builds each NPC in npc_specs.json through MPFB's services layer (no UI operators), then turns
it into a game asset:
  1. HumanService.deserialize_from_dict: macro targets, game_engine rig, low-poly proxy,
     eyes/brows/lashes/hair, clothes, GAMEENGINE skin + clothes materials.
  2. Delete the basemesh (helpers included); the proxy replaces it.
  3. Apply every MASK modifier (clothes delete groups) so hidden body faces are removed.
  4. Optional decimation per part.
  5. Atlas textures into 3 materials (skin / outfit / hair) at atlas_px, remap UVs.
  6. Join all meshes into one skinned mesh, export GLB (Y up).
It writes <out>/<id>/<id>.glb, <id>_source.blend and <id>_stats.json.

Usage:
  source env.sh
  blender -b --factory-startup --python build_npcs.py -- npc_specs.json <out_dir> [only_id]
"""
import bpy, bmesh, os, sys, json, time, random, hashlib, struct
import addon_utils
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:]
SPEC_PATH, OUT_DIR = ARGS[0], ARGS[1]
ONLY = ARGS[2] if len(ARGS) > 2 else None

addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
from bl_ext.user_default.mpfb.services import (HumanService, AssetService, ObjectService,
                                               RandomizationService, TargetService)
from bl_ext.user_default.mpfb.entities.objectproperties import GeneralObjectProperties

SPEC = json.load(open(SPEC_PATH))
ATLAS = int(SPEC.get("atlas_px", 1024))
PAD = 4  # px gutter around each atlas tile, edge-extended

# Atlas templates, pixel rects (x0, y0, size) with origin bottom-left (= UV origin).
# Slot order is the fill order.
T768 = [(0, 256, 768), (768, 768, 256), (768, 512, 256), (768, 256, 256),
        (0, 0, 256), (256, 0, 256), (512, 0, 256), (768, 0, 256)]
T1024 = [(0, 0, 1024)]


def scaled_template(tpl):
    k = ATLAS / 1024.0
    return [(int(x * k), int(y * k), int(s * k)) for x, y, s in tpl]


def clean_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images,
                 bpy.data.node_groups, bpy.data.actions):
        for d in list(coll):
            coll.remove(d)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def resolve_random(npc, seed):
    """Seeded NPC via MPFB's pure RandomizationService plus sorted asset lists."""
    rng = random.Random(seed)
    spec = RandomizationService.get_default_phenotype_spec()
    # adults only: the default discrete age anchors include baby (0.0) and child (0.1875)
    spec["phenotype"]["attributes"]["age"]["allowed"] = ["young", "middleage", "old"]
    # the default height deviation (0.5) yields 2 m+ civilians; keep them plausible
    spec["phenotype"]["attributes"]["height"]["deviation"] = 0.15
    macro = RandomizationService.randomize_macro_info_dict(spec, rng)
    male = macro["gender"] >= 0.5
    agel = "young" if macro["age"] < 0.6 else ("middleage" if macro["age"] < 0.8 else "old")
    race = max(sorted(macro["race"]), key=lambda r: macro["race"][r])
    skin = f"{agel}_{race}_{'male' if male else 'female'}"
    pick = lambda xs: xs[rng.randrange(len(xs))]
    hair_m = ["short01", "short02", "short04", "afro01"]
    hair_f = ["bob01", "bob02", "long01", "ponytail01", "braid01", "short03"]
    tops_m = ["male_casualsuit02", "male_casualsuit03", "male_casualsuit04", "male_casualsuit06"]
    tops_f = ["female_casualsuit01", "female_sportsuit01"]
    h = pick(hair_m if male else hair_f)
    top = pick(tops_m if male else tops_f)
    shoes = pick(["shoes01", "shoes02", "shoes04", "shoes05", "shoes06"])
    brow = "eyebrow%03d" % (1 + rng.randrange(12))
    eyes = pick(["blue", "brown", "brownlight", "green", "grey", "lightblue"])
    return {
        "id": npc["id"], "phenotype": macro,
        "skin": f"{skin}/{skin}.mhmat", "eye_material": f"materials/{eyes}.mhmat",
        "eyebrows": f"{brow}/{brow}.mhclo", "eyelashes": "eyelashes01/eyelashes01.mhclo",
        "hair": f"{h}/{h}.mhclo", "proxy": "male1591/male1591.proxy" if male else "female1605/female1605.proxy",
        "clothes": [f"{top}/{top}.mhclo", f"{shoes}/{shoes}.mhclo"], "random_seed": seed,
    }


def build_human(npc):
    info = HumanService._create_default_human_info_dict()
    info["name"] = npc["id"]
    info["phenotype"] = npc["phenotype"]
    info["rig"] = SPEC.get("rig", "game_engine")
    info["proxy"] = npc["proxy"]
    info["eyes"] = "low-poly/low-poly.mhclo"
    info["eyebrows"] = npc["eyebrows"]
    info["eyelashes"] = npc["eyelashes"]
    info["hair"] = npc.get("hair", "")
    info["skin_mhmat"] = npc["skin"]
    info["skin_material_type"] = "GAMEENGINE"
    info["clothes"] = list(npc["clothes"])
    # Eye colour is an alternative material keyed by the eyes mhclo uuid.
    info["alternative_materials"] = {"1cc97a30-85a1-42e6-a9f7-b3e753732baa": npc["eye_material"]}
    settings = HumanService.get_default_deserialization_settings()
    settings["subdiv_levels"] = 0
    settings["override_clothes_model"] = "GAMEENGINE"
    settings["override_eyes_model"] = "GAMEENGINE"
    return HumanService.deserialize_from_dict(info, settings)


def with_obj(obj, fn, **kw):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        return fn(**kw)


def apply_masks(obj):
    for m in list(obj.modifiers):
        if m.type == 'MASK':
            with_obj(obj, bpy.ops.object.modifier_move_to_index, modifier=m.name, index=0)
            with_obj(obj, bpy.ops.object.modifier_apply, modifier=m.name)
        elif m.type == 'SUBSURF':
            obj.modifiers.remove(m)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def image_of(mat, node_name):
    if not mat or not mat.node_tree:
        return None
    n = mat.node_tree.nodes.get(node_name)
    return bpy.path.abspath(n.image.filepath) if n and n.image else None


def load_pixels(path, size, fill):
    """Load an image file, resize to size x size, return float32 (size, size, 4), bottom-left origin."""
    if path is None:
        return np.tile(np.array(fill, np.float32), (size, size, 1))
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'  # raw values, no conversion
    img.scale(size, size)
    buf = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(size, size, 4)


def build_atlas(items, tpl, out_png, key, fill, uv_report):
    """items: list of (obj, image_path). Writes atlas, remaps each obj's active UV map."""
    atlas = np.tile(np.array(fill, np.float32), (ATLAS, ATLAS, 1))
    rects = scaled_template(tpl)
    if len(items) > len(rects):
        raise RuntimeError(f"atlas {out_png}: {len(items)} items, template has {len(rects)} slots")
    for (obj, path), (x0, y0, s) in zip(items, rects):
        inner = s - 2 * PAD
        px = load_pixels(path, inner, fill)
        px = np.pad(px, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='edge')
        atlas[y0:y0 + s, x0:x0 + s] = px
        if key == "diffuse":  # remap UVs once, on the diffuse pass
            uvl = obj.data.uv_layers.active
            uv = np.empty(len(uvl.data) * 2, np.float32)
            uvl.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            uv_report[obj.name] = [round(float(uv.min()), 4), round(float(uv.max()), 4)]
            uv = np.clip(uv, 0.0, 1.0)
            uv[:, 0] = (x0 + PAD + uv[:, 0] * inner) / ATLAS
            uv[:, 1] = (y0 + PAD + uv[:, 1] * inner) / ATLAS
            uvl.data.foreach_set("uv", uv.ravel())
    img = bpy.data.images.new(os.path.basename(out_png)[:-4], ATLAS, ATLAS, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.ascontiguousarray(atlas).ravel())
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
        rnd.operation = 'ROUND'  # glTF exporter reads this as alphaMode MASK, cutoff 0.5
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


def glb_stats(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    tris_by_mat = {}
    for mesh in j["meshes"]:
        for p in mesh["primitives"]:
            name = j["materials"][p["material"]]["name"] if "material" in p else "none"
            tris_by_mat[name] = tris_by_mat.get(name, 0) + j["accessors"][p["indices"]]["count"] // 3
    imgs = []
    for im in j.get("images", []):
        bv = j["bufferViews"][im["bufferView"]]
        off = 20 + jlen + 8 + bv.get("byteOffset", 0)
        blob = data[off:off + bv["byteLength"]]
        w, h = struct.unpack(">II", blob[16:24]) if blob[:4] == b"\x89PNG" else (None, None)
        imgs.append({"name": im.get("name"), "mime": im["mimeType"], "px": [w, h], "bytes": bv["byteLength"]})
    verts = sum(j["accessors"][p["attributes"]["POSITION"]]["count"] for m in j["meshes"] for p in m["primitives"])
    return {
        "glb_bytes": len(data), "triangles": sum(tris_by_mat.values()), "triangles_by_material": tris_by_mat,
        "vertices": verts, "materials": len(j.get("materials", [])),
        "alpha_modes": {m["name"]: m.get("alphaMode", "OPAQUE") for m in j.get("materials", [])},
        "images": imgs, "texture_bytes": sum(i["bytes"] for i in imgs),
        "bones": len(j["skins"][0]["joints"]) if j.get("skins") else 0,
        "bone_names": [j["nodes"][i]["name"] for i in j["skins"][0]["joints"]] if j.get("skins") else [],
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def process(npc):
    t0 = time.time()
    clean_scene()
    if "random_seed" in npc and "phenotype" not in npc:
        npc = resolve_random(npc, npc["random_seed"])
    out = os.path.join(OUT_DIR, npc["id"])
    os.makedirs(os.path.join(out, "tex"), exist_ok=True)

    basemesh = build_human(npc)
    t_build = time.time() - t0
    rig = basemesh.parent
    parts = sorted([o for o in bpy.data.objects if o.type == 'MESH' and o is not basemesh], key=lambda o: o.name)
    kinds = {o.name: str(GeneralObjectProperties.get_value("object_type", entity_reference=o)) for o in parts}
    raw = {o.name: {"kind": kinds[o.name], "tris": tri_count(o),
                    "diffuse": image_of(o.active_material, "DiffuseTexture"),
                    "normal": image_of(o.active_material, "NormalMapTextue")} for o in parts}
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, npc["id"] + "_source.blend"), compress=False)

    # 2. the proxy replaces the basemesh (and with it all helper geometry)
    base_tris = tri_count(basemesh)
    bpy.data.objects.remove(basemesh, do_unlink=True)
    # 3. clothes delete groups -> real deletion on the proxy
    for o in parts:
        apply_masks(o)
    # 4. decimation (spec: {"decimate": {"Clothes": 0.5}} keyed by kind or object suffix)
    for o in parts:
        dec = dict(SPEC.get("decimate", {}))
        dec.update(npc.get("decimate", {}))
        ratio = dec.get(kinds[o.name]) or dec.get(o.name.split(".")[-1])
        if ratio:
            m = o.modifiers.new("Decimate", 'DECIMATE')
            m.ratio = ratio
            m.use_symmetry = True
            with_obj(o, bpy.ops.object.modifier_move_to_index, modifier=m.name, index=0)
            with_obj(o, bpy.ops.object.modifier_apply, modifier=m.name)
    after_mask = {o.name: tri_count(o) for o in parts}

    # 5. atlases
    skin = [o for o in parts if kinds[o.name] == "Proxymeshes"]
    hair = [o for o in parts if kinds[o.name] in ("Hair", "Eyebrows", "Eyelashes")]
    hair.sort(key=lambda o: ["Hair", "Eyebrows", "Eyelashes"].index(kinds[o.name]))
    clothes = sorted([o for o in parts if kinds[o.name] == "Clothes"], key=lambda o: -after_mask[o.name])
    eyes = [o for o in parts if kinds[o.name] == "Eyes"]
    outfit = clothes + eyes
    uvr = {}
    tex = os.path.join(out, "tex")
    a_skin = build_atlas([(o, raw[o.name]["diffuse"]) for o in skin], T1024, os.path.join(tex, "skin_albedo.png"), "diffuse", (0.5, 0.4, 0.35, 1), uvr)
    a_out = build_atlas([(o, raw[o.name]["diffuse"]) for o in outfit], T768, os.path.join(tex, "outfit_albedo.png"), "diffuse", (0.2, 0.2, 0.2, 1), uvr)
    n_out = build_atlas([(o, raw[o.name]["normal"]) for o in outfit], T768, os.path.join(tex, "outfit_normal.png"), "normal", (0.5, 0.5, 1.0, 1), uvr)
    a_hair = build_atlas([(o, raw[o.name]["diffuse"]) for o in hair], T768, os.path.join(tex, "hair_albedo.png"), "diffuse", (0.1, 0.08, 0.06, 0), uvr)
    m_skin = make_material(npc["id"] + "_skin", a_skin)
    m_out = make_material(npc["id"] + "_outfit", a_out, normal=n_out)
    m_hair = make_material(npc["id"] + "_hair", a_hair, alpha_clip=True)
    for group, mat in ((skin, m_skin), (outfit, m_out), (hair, m_hair)):
        for o in group:
            o.data.materials.clear()
            o.data.materials.append(mat)

    # 6. join into one skinned mesh
    target = skin[0]
    objs = [target] + [o for o in parts if o is not target]
    with bpy.context.temp_override(object=target, active_object=target, selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    target.name = npc["id"] + "_mesh"
    target.data.name = npc["id"] + "_mesh"
    rig.name = npc["id"]
    for m in list(target.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig
    # keep only groups that are bones (MPFB leaves Delete.* and body-part groups behind)
    bones = set(b.name for b in rig.data.bones)
    for g in list(target.vertex_groups):
        if g.name not in bones:
            target.vertex_groups.remove(g)

    glb = os.path.join(out, npc["id"] + ".glb")
    for o in bpy.data.objects:
        o.select_set(o in (rig, target))
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_yup=True,
                              export_skins=True, export_animations=False, export_morph=False,
                              export_image_format='AUTO', export_materials='EXPORT',
                              export_rest_position_armature=True, export_def_bones=False)
    stats = glb_stats(glb)
    if os.environ.get("NPC_WEBP") == "1":  # size comparison only: same asset, WebP textures
        wglb = os.path.join(out, npc["id"] + "_webp.glb")
        bpy.ops.export_scene.gltf(filepath=wglb, export_format='GLB', use_selection=True, export_yup=True,
                                  export_skins=True, export_animations=False, export_morph=False,
                                  export_image_format='WEBP', export_image_quality=85, export_materials='EXPORT',
                                  export_rest_position_armature=True, export_def_bones=False)
        stats["webp_glb_bytes"] = os.path.getsize(wglb)
    stats.update({
        "id": npc["id"], "spec": npc, "basemesh_tris_with_helpers": base_tris,
        "parts_raw": raw, "parts_tris_after_masks": after_mask, "uv_bounds_before_atlas": uvr,
        "deform_bones_in_rig": sum(1 for b in rig.data.bones if b.use_deform),
        "build_s": round(t_build, 2), "total_s": round(time.time() - t0, 2),
        "atlas_png_bytes": {os.path.basename(p): os.path.getsize(p) for p in (a_skin, a_out, n_out, a_hair)},
    })
    json.dump(stats, open(os.path.join(out, npc["id"] + "_stats.json"), "w"), indent=1, sort_keys=True)
    print("NPC", npc["id"], "tris", stats["triangles"], "mats", stats["materials"], "bones", stats["bones"],
          "glb", stats["glb_bytes"], "time", stats["total_s"])


for npc in SPEC["npcs"]:
    if ONLY and npc["id"] != ONLY:
        continue
    process(npc)

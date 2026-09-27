#!/usr/bin/env python3
"""Writes Godot import presets (.glb.import) for the Blender-made assets:

  * maps every glTF material name onto the shared res://materials/*.tres (so Blender assets use
    exactly the same Material Maker PBR materials as the CSG and TrenchBroom levels),
  * static level/prop geometry -> "Static Lightmaps" (UV2 unwrap, GI static) at 0.1 m texels,
  * door leaves -> dynamic GI (lit by light probes), meshes saved as .res for reuse,
  * post-import scripts that turn Blender empties into game entities.

    python3 tools/godot/import_presets.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME = os.path.join(ROOT, "game")

LEVEL_MATS = ["tech_panel", "concrete", "ceiling_tiles", "floor_tiles", "crate", "crate_large", "hazard_stripes",
              "light_panel", "rust_metal", "brick_wall", "stone_blocks", "diamond_plate", "lava"]
PROP_MATS = ["rubber", "gunmetal", "gunmetal_light", "brass", "lamp_glow", "status_light"]


def material_map():
    m = {n: f"res://materials/{n}.tres" for n in LEVEL_MATS}
    m.update({n: f"res://materials/props/{n}.tres" for n in PROP_MATS})
    return m


def fmt_subresources(materials, meshes=None):
    parts = []
    mat_items = []
    for name, path in materials.items():
        mat_items.append(f'"{name}": {{\n"use_external/enabled": true,\n"use_external/path": "{path}"\n}}')
    parts.append('"materials": {\n' + ",\n".join(mat_items) + "\n}")
    if meshes:
        mesh_items = []
        for name, path in meshes.items():
            mesh_items.append(f'"{name}": {{\n"save_to_file/enabled": true,\n"save_to_file/path": "{path}"\n}}')
        parts.append('"meshes": {\n' + ",\n".join(mesh_items) + "\n}")
    return "{\n" + ",\n".join(parts) + "\n}"


def write(rel, light_baking, texel=0.1, script="", meshes=None):
    path = os.path.join(GAME, rel)
    uid_line = ""
    if os.path.exists(path + ".import"):
        m = re.search(r'^uid="([^"]+)"', open(path + ".import").read(), re.M)
        if m:
            uid_line = f'uid="{m.group(1)}"\n'
    text = f"""[remap]

importer="scene"
importer_version=1
type="PackedScene"
{uid_line}
[deps]

source_file="res://{rel}"

[params]

nodes/root_type=""
nodes/root_name=""
nodes/root_script=null
mesh_library/use_node_names_as_mesh_names=false
array_mesh/deduplicate_surfaces=true
nodes/apply_root_scale=true
nodes/root_scale=1.0
nodes/import_as_skeleton_bones=false
nodes/use_name_suffixes=true
nodes/use_node_type_suffixes=true
meshes/ensure_tangents=true
meshes/generate_lods=false
meshes/create_shadow_meshes=true
meshes/light_baking={light_baking}
meshes/lightmap_texel_size={texel}
meshes/force_disable_compression=false
skins/use_named_skins=true
animation/import=false
animation/fps=30
animation/trimming=false
animation/remove_immutable_tracks=true
animation/import_rest_as_RESET=false
import_script/path="{script}"
materials/extract=0
materials/extract_format=0
materials/extract_path=""
_subresources={fmt_subresources(material_map(), meshes)}
gltf/naming_version=2
gltf/embedded_image_handling=1
gltf/texture_map_mode=1
"""
    with open(path + ".import", "w") as f:
        f.write(text)
    print("wrote", rel + ".import")


def main():
    STATIC_LIGHTMAPS, DYNAMIC = 2, 3
    write("levels/blender/cistern.glb", STATIC_LIGHTMAPS, 0.1,
          "res://addons/brushfire_tools/blender_level_import.gd")
    write("models/doorway/door_frame.glb", STATIC_LIGHTMAPS, 0.05, "res://addons/brushfire_tools/prop_import.gd")
    write("models/doorway/door_leaves.glb", DYNAMIC, 0.1, "",
          {"Props_LeafL": "res://models/doorway/leaf_l.res", "Props_LeafR": "res://models/doorway/leaf_r.res"})
    for f in sorted(os.listdir(os.path.join(GAME, "models", "doorway"))):
        if f.startswith("arch_") and f.endswith(".glb"):
            write(f"models/doorway/{f}", STATIC_LIGHTMAPS, 0.05, "res://addons/brushfire_tools/prop_import.gd")


if __name__ == "__main__":
    main()

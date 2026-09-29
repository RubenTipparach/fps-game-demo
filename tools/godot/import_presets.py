#!/usr/bin/env python3
"""Writes Godot import presets (.glb.import) for the Blender-made assets:

  * maps every glTF material name onto the shared res://materials/*.tres (so Blender assets use
    exactly the same Material Maker PBR materials as the CSG and TrenchBroom levels),
  * static level/prop geometry -> "Static Lightmaps" (UV2 unwrap, GI static) at 0.1 m texels,
  * door leaves -> dynamic GI (lit by light probes), meshes saved as .res for reuse,
  * post-import scripts that turn Blender empties into game entities.

    python3 tools/godot/import_presets.py              # everything
    python3 tools/godot/import_presets.py undercity    # just the Undercity sector glbs
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME = os.path.join(ROOT, "game")

LEVEL_MATS = ["tech_panel", "concrete", "ceiling_tiles", "floor_tiles", "crate", "crate_large", "hazard_stripes",
              "light_panel", "rust_metal", "brick_wall", "stone_blocks", "diamond_plate", "lava",
              "sky_night", "sky_storm", "sky_moon",
              # the city kit (tools/fx/generate_city_materials.py)
              "asphalt", "paving_wet", "window_lit_warm", "window_lit_cool", "window_dark", "glass",
              "neon_pink", "neon_cyan", "water", "awning"]


def prop_materials():
    """Every material file in game/materials/props. Read from the folder rather than listed, so a
    prop kit that adds materials (tools/blender/build_undercity_props.py writes its own, and
    calls write() for each prop it exports) is mapped without a second list to keep in step."""
    folder = os.path.join(GAME, "materials", "props")
    return sorted(f[:-len(".tres")] for f in os.listdir(folder) if f.endswith(".tres"))


def skyline_materials():
    """Every material in game/materials/skyline (tools/godot/gen_skyline_materials.py writes them),
    read from the folder like the prop kit's."""
    folder = os.path.join(GAME, "materials", "skyline")
    return sorted(f[:-len(".tres")] for f in os.listdir(folder) if f.endswith(".tres")) if os.path.isdir(folder) else []


FX_MATS = ["corona_warm", "corona_cool", "corona_pink", "corona_cyan"]

# Undercity levels bake exterior lightmaps at 0.4 m texels; interiors ask for 0.15 m through the
# lightmap_texel_scale extra (tools/levels/city_plan.py, applied by blender_level_import.gd).
UNDERCITY_TEXEL_M = 0.4


def material_map():
    m = {n: f"res://materials/{n}.tres" for n in LEVEL_MATS}
    m.update({n: f"res://materials/props/{n}.tres" for n in prop_materials()})
    m.update({n: f"res://materials/fx/{n}.tres" for n in FX_MATS})
    m.update({n: f"res://materials/skyline/{n}.tres" for n in skyline_materials()})
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


NO_BAKING, STATIC_LIGHTMAPS, DYNAMIC = 0, 2, 3
# Sectors that are only scenery bake nothing, so they need no lightmap UVs (hub-skyline).
SCENERY_SECTORS = ("skyline",)


def undercity():
    """Every sector glb build_undercity.py wrote under levels/undercity/."""
    base = os.path.join(GAME, "levels", "undercity")
    for level in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        for f in sorted(os.listdir(os.path.join(base, level))):
            if f.endswith(".glb"):
                scenery = any(f == f"{level}_{s}.glb" for s in SCENERY_SECTORS)
                write(f"levels/undercity/{level}/{f}", NO_BAKING if scenery else STATIC_LIGHTMAPS, UNDERCITY_TEXEL_M,
                      "res://addons/brushfire_tools/blender_level_import.gd")


def main(which=("brushfire", "undercity")):
    if "undercity" in which:
        undercity()
    if "brushfire" not in which:
        return
    write("levels/blender/cistern.glb", STATIC_LIGHTMAPS, 0.1,
          "res://addons/brushfire_tools/blender_level_import.gd")
    write("models/doorway/door_frame.glb", STATIC_LIGHTMAPS, 0.05, "res://addons/brushfire_tools/prop_import.gd")
    write("models/doorway/door_leaves.glb", DYNAMIC, 0.1, "",
          {"Props_LeafL": "res://models/doorway/leaf_l.res", "Props_LeafR": "res://models/doorway/leaf_r.res"})
    for f in sorted(os.listdir(os.path.join(GAME, "models", "doorway"))):
        if f.startswith("arch_") and f.endswith(".glb"):
            write(f"models/doorway/{f}", STATIC_LIGHTMAPS, 0.05, "res://addons/brushfire_tools/prop_import.gd")


if __name__ == "__main__":
    main(sys.argv[1:] or ("brushfire", "undercity"))

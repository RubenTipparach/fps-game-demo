#!/usr/bin/env python3
"""Convert Material Maker exports into Godot-ready textures and ORM PBR materials.

Material Maker's command-line exporter always renders at 2048px and writes a Godot 3
style .tres, so this step:
  * downsamples each map to TEXTURE_SIZE with a Lanczos filter (supersampled result),
  * re-normalises the normal map after filtering (OpenGL / Y+ convention, what Godot expects),
  * writes albedo as textures/<name>.png so TrenchBroom, func_godot and Godot all see the
    same image (and therefore agree on texel density), plus <name>_normal/_orm/_emission,
  * writes .import presets (VRAM compression, mipmaps, BC5 normal maps),
  * writes materials/<name>.tres as ORMMaterial3D with PBR settings from materials.json.

Usage: postprocess.py <raw_export_dir> <godot_project_dir>
"""
import json
import os
import sys

import numpy as np
from PIL import Image

TEXTURE_SIZE = 1024


def load(path):
    return Image.open(path).convert("RGB")


def resize(img):
    if img.size == (TEXTURE_SIZE, TEXTURE_SIZE):
        return img
    return img.resize((TEXTURE_SIZE, TEXTURE_SIZE), Image.LANCZOS)


def renormalize(img):
    a = np.asarray(img).astype(np.float32) / 255.0 * 2.0 - 1.0
    a[..., 2] = np.clip(a[..., 2], 0.0, 1.0)
    length = np.linalg.norm(a, axis=2, keepdims=True)
    a = a / np.maximum(length, 1e-6)
    return Image.fromarray(np.clip((a + 1.0) * 0.5 * 255.0 + 0.5, 0, 255).astype(np.uint8))


IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://textures/{file}"

[params]

compress/mode=2
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map={normal}
compress/channel_pack=0
mipmaps/generate=true
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def write_import(tex_dir, file, normal=False):
    path = os.path.join(tex_dir, file + ".import")
    # Only seed the import preset; Godot owns the file afterwards.
    if os.path.exists(path):
        return
    with open(path, "w") as f:
        f.write(IMPORT_TEMPLATE.format(file=file, normal=1 if normal else 0))


def write_material(mat_dir, name, spec, has_emission):
    lines = ['[gd_resource type="ORMMaterial3D" format=3]', ""]
    res = [("albedo", f"res://textures/{name}.png"),
           ("orm", f"res://textures/{name}_orm.png"),
           ("normal", f"res://textures/{name}_normal.png")]
    if has_emission:
        res.append(("emission", f"res://textures/{name}_emission.png"))
    for i, (_, path) in enumerate(res, 1):
        lines.append(f'[ext_resource type="Texture2D" path="{path}" id="{i}"]')
    lines += ["", "[resource]", f'resource_name = "{name}"',
              "texture_filter = 5",
              'albedo_texture = ExtResource("1")',
              # ORM: R = ambient occlusion, G = roughness, B = metallic. The scalar
              # roughness/metallic values multiply the texture, so both stay at 1.
              "roughness = 1.0",
              "metallic = 1.0",
              "metallic_specular = 0.5",
              'orm_texture = ExtResource("2")',
              "ao_light_affect = 0.2",
              "normal_enabled = true",
              f"normal_scale = {spec.get('normal_scale', 1.0)}",
              'normal_texture = ExtResource("3")']
    if has_emission:
        lines += ["emission_enabled = true",
                  "emission = Color(1, 1, 1, 1)",
                  f"emission_energy_multiplier = {spec.get('emission_energy', 1.0)}",
                  'emission_texture = ExtResource("4")']
    with open(os.path.join(mat_dir, name + ".tres"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    raw, game = sys.argv[1], sys.argv[2]
    manifest = json.load(open(os.path.join(game, "materials", "materials.json")))
    tex_dir = os.path.join(game, "textures")
    mat_dir = os.path.join(game, "materials")
    os.makedirs(tex_dir, exist_ok=True)
    for name, spec in manifest.items():
        if name.startswith("_") or "alias" in spec:
            continue
        src = os.path.join(raw, name)
        if not os.path.exists(src + "_albedo.png"):
            print(f"skip {name}: no export in {raw}")
            continue
        resize(load(src + "_albedo.png")).save(os.path.join(tex_dir, f"{name}.png"), optimize=True)
        write_import(tex_dir, f"{name}.png")

        if os.path.exists(src + "_normal.png"):
            nrm = renormalize(resize(load(src + "_normal.png")))
        else:
            nrm = Image.new("RGB", (TEXTURE_SIZE, TEXTURE_SIZE), (128, 128, 255))
        nrm.save(os.path.join(tex_dir, f"{name}_normal.png"), optimize=True)
        write_import(tex_dir, f"{name}_normal.png", normal=True)

        if os.path.exists(src + "_orm.png"):
            orm = resize(load(src + "_orm.png"))
        else:  # no roughness/metal/AO connected in the graph: plain dielectric
            orm = Image.new("RGB", (TEXTURE_SIZE, TEXTURE_SIZE), (255, 204, 0))
        orm.save(os.path.join(tex_dir, f"{name}_orm.png"), optimize=True)
        write_import(tex_dir, f"{name}_orm.png")

        has_emission = os.path.exists(src + "_emission.png")
        if has_emission:
            resize(load(src + "_emission.png")).save(os.path.join(tex_dir, f"{name}_emission.png"), optimize=True)
            write_import(tex_dir, f"{name}_emission.png")
        write_material(mat_dir, name, spec, has_emission)
        print(f"{name}: ok{' (emissive)' if has_emission else ''}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Convert Material Maker exports into Godot-ready textures and ORM PBR materials.

Material Maker's command-line exporter always renders at 2048px and writes a Godot 3
style .tres, so this step:
  * downsamples each map to TEXTURE_SIZE with a Lanczos filter (supersampled result),
  * re-normalises the normal map after filtering (OpenGL / Y+ convention, what Godot expects),
  * writes albedo as textures/<name>.png so TrenchBroom, func_godot and Godot all see the
    same image (and therefore agree on texel density), plus <name>_normal/_orm/_emission,
  * writes .import presets (VRAM compression, mipmaps, BC5 normal maps),
  * writes materials/<name>.tres as ORMMaterial3D with PBR settings from materials.json, or as a
    ShaderMaterial for a material that names its own "shader" (the canal water).

Usage: postprocess.py <raw_export_dir> <godot_project_dir> [material ...]

materials.json may also set "albedo_ramp": [[dark r,g,b], [light r,g,b]] to remap the albedo's
luminance onto a colour ramp, and "albedo_under_emission": k to darken the albedo where the
material glows. The lava uses both: Material Maker's example lava graph outputs a light-grey
cloud as albedo, which any light washes out to white, where lava needs a near-black crust with
only the emissive cracks glowing.
"""
import json
import os
import re
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

source_file="{res_dir}/{file}"

[params]

compress/mode={mode}
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


def write_import(tex_dir, file, normal=False, lossless=False, res_dir="res://textures"):
    """Seed a texture's import preset: VRAM-compressed, or lossless (mode 0) for a map whose exact
    values matter (a decal, the puddle mask's distances). Godot owns the file afterwards."""
    path = os.path.join(tex_dir, file + ".import")
    if os.path.exists(path):
        return
    with open(path, "w") as f:
        f.write(IMPORT_TEMPLATE.format(file=file, normal=1 if normal else 0, mode=0 if lossless else 2, res_dir=res_dir))


def shader_value(v):
    """A materials.json shader parameter as a .tres value: a number, [x, y], or a "#rrggbb" colour."""
    if isinstance(v, str) and v.startswith("#") and len(v) == 7:
        r, g, b = (int(v[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return f"Color({r:.4f}, {g:.4f}, {b:.4f}, 1)"
    if isinstance(v, list) and len(v) == 2:
        return f"Vector2({float(v[0])}, {float(v[1])})"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(float(v))
    raise SystemExit(f"materials.json: shader parameter {v!r} is not a number, [x, y] or #rrggbb")


def shader_uniforms(game, res_path):
    """The uniform names a shader declares, read from the shader file itself."""
    with open(os.path.join(game, res_path[len("res://"):])) as f:
        return set(re.findall(r"^\s*(?:instance\s+)?uniform\s+\w+\s+(\w+)", f.read(), re.M))


# The rain's ring numbers (shaders/rain_ripples.gdshaderinc). They are set once, on the water; a
# material that names "ripples_from" takes that material's (openspec/changes/street-puddles, design
# section 3.3: one set of numbers for all the rain).
RIPPLES = ("ripple_cell_m", "ripple_rate_hz", "ripple_strength", "ripple_wave_per_m", "ripple_falloff_per_m")


def shader_params(name, spec, manifest):
    """A shader material's parameters: its own "shader_params", and, when it names "ripples_from",
    that material's ripple numbers and its normal depth as ripple_normal_depth. A material that
    takes its ripples from another may not also set them itself, or the two would drift."""
    params = dict(spec.get("shader_params", {}))
    src = spec.get("ripples_from")
    if src is None:
        return params
    other = (manifest or {}).get(src, {})
    if not all(k in other.get("shader_params", {}) for k in RIPPLES):
        raise SystemExit(f"materials.json {name}: ripples_from '{src}' names no material with the ripple numbers")
    clash = sorted(set(params) & {*RIPPLES, "ripple_normal_depth"})
    if clash:
        raise SystemExit(f"materials.json {name}: sets {', '.join(clash)} itself, but takes its ripples from {src}")
    params.update({k: other["shader_params"][k] for k in RIPPLES})
    params["ripple_normal_depth"] = other.get("normal_scale", 1.0)
    return params


def write_shader_material(mat_dir, name, spec, manifest=None):
    """A material drawn by its own shader (materials.json "shader"). Its maps go to the uniforms
    the shader declares for them (albedo_map, orm_map; normal_map always), tile_m when the shader
    tiles its own maps, normal_scale to normal_strength, and "shader_params" (with any
    "ripples_from", shader_params()) set the rest by uniform name. A parameter the shader doesn't
    declare is refused (CLAUDE.md 5.6: a misspelt or stale knob would silently do nothing)."""
    declared = shader_uniforms(os.path.dirname(mat_dir), spec["shader"])
    params = shader_params(name, spec, manifest)
    maps = [(u, f"res://textures/{f}") for u, f in (("albedo_map", f"{name}.png"), ("orm_map", f"{name}_orm.png"),
                                                    ("normal_map", f"{name}_normal.png"))
            if u in declared or u == "normal_map"]
    unknown = sorted({"normal_map", "normal_strength", *params} - declared)
    if unknown:
        raise SystemExit(f"materials.json {name}: {spec['shader']} has no uniform {', '.join(unknown)}")
    lines = ['[gd_resource type="ShaderMaterial" format=3]', "",
             f'[ext_resource type="Shader" path="{spec["shader"]}" id="1"]']
    lines += [f'[ext_resource type="Texture2D" path="{path}" id="{i}"]' for i, (_, path) in enumerate(maps, 2)]
    lines += ["", "[resource]", f'resource_name = "{name}"', 'shader = ExtResource("1")']
    lines += [f'shader_parameter/{u} = ExtResource("{i}")' for i, (u, _) in enumerate(maps, 2)]
    if "tile_m" in declared:
        lines.append(f"shader_parameter/tile_m = {float(spec.get('tile_m', 1.0))}")
    lines.append(f"shader_parameter/normal_strength = {float(spec.get('normal_scale', 1.0))}")
    for key, value in sorted(params.items()):
        lines.append(f"shader_parameter/{key} = {shader_value(value)}")
    with open(os.path.join(mat_dir, name + ".tres"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_material(mat_dir, name, spec, has_emission, manifest=None):
    if "shader" in spec:
        write_shader_material(mat_dir, name, spec, manifest)
        return
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
        # Multiply: emission = colour * texture * energy. Godot's default operator is Add,
        # (colour + texture) * energy, which with a white colour makes every texel glow - lava
        # rendered solid white and light-panel grilles glowed.
        lines += ["emission_enabled = true",
                  "emission = Color(1, 1, 1, 1)",
                  "emission_operator = 1",
                  f"emission_energy_multiplier = {spec.get('emission_energy', 1.0)}",
                  'emission_texture = ExtResource("4")']
    with open(os.path.join(mat_dir, name + ".tres"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    process(sys.argv[1], sys.argv[2], set(sys.argv[3:]))


def process(raw, game, only=()):
    """Convert the maps in `raw` (<name>_albedo/_normal/_orm/_emission.png) for every material in
    materials.json (or just `only`). tools/fx/generate_city_materials.py calls this too, so
    procedural materials get the same textures, import presets and emission rules."""
    manifest = json.load(open(os.path.join(game, "materials", "materials.json")))
    tex_dir = os.path.join(game, "textures")
    mat_dir = os.path.join(game, "materials")
    os.makedirs(tex_dir, exist_ok=True)
    only = set(only)
    for name, spec in manifest.items():
        if name.startswith("_") or "alias" in spec or (only and name not in only):
            continue
        src = os.path.join(raw, name)
        if not os.path.exists(src + "_albedo.png"):
            print(f"skip {name}: no export in {raw}")
            continue
        albedo = resize(load(src + "_albedo.png"))
        if "albedo_ramp" in spec or "albedo_under_emission" in spec:
            a = np.asarray(albedo, dtype=np.float32) / 255.0
            if "albedo_ramp" in spec:
                lum = (a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32))[..., None]
                dark, light = (np.array(c, dtype=np.float32) for c in spec["albedo_ramp"])
                a = dark + (light - dark) * lum
            if "albedo_under_emission" in spec and os.path.exists(src + "_emission.png"):
                e = np.asarray(resize(load(src + "_emission.png")), dtype=np.float32) / 255.0
                a *= 1.0 - spec["albedo_under_emission"] * e.max(axis=2, keepdims=True)
            albedo = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
        albedo.save(os.path.join(tex_dir, f"{name}.png"), optimize=True)
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
        write_material(mat_dir, name, spec, has_emission, manifest)
        print(f"{name}: ok{' (emissive)' if has_emission else ''}")


if __name__ == "__main__":
    main()

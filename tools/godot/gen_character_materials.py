#!/usr/bin/env python3
"""Generate the NPC skin and outfit materials (openspec/changes/archive/2026-09-29-character-lighting, design
sections 1 and 8).

    python3 tools/godot/gen_character_materials.py

Writes game/materials/characters/character_skin.tres and character_outfit.tres, the templates
(every setting, no textures), and one <id>_skin.tres and <id>_outfit.tres per body in
tools/blender/npcs.json: a template's settings with that body's textures, which the NPC import
step (setup_npc_import.gd) maps onto the glb's "<id>_skin" and "<id>_outfit" materials. The
settings live once, in SKIN and OUTFIT below, so the templates and the bodies can't disagree.

- The skin is drawn by shaders/character_skin.gdshader (design section 9: a StandardMaterial3D
  can't take a per-character wetness). The albedo is the body's skin atlas; the normal is the one
  derived from it (build_npcs.py), and its alpha is the roughness (npc_skin_roughness.png), the
  wet look, which dry skin roughens.
- Subsurface scattering in skin mode, strength 0.30, with transmittance (depth 0.2, boost 0.3),
  so ears glow against a rim gel.
- Specular 0.42: Godot's F0 is 0.16 x specular squared, so 0.028, MakeHuman's skins' 0.027.
- The outfit (clothes, gear and the eyes, which share its atlas) is drawn by
  shaders/character_outfit.gdshader: its roughness is its normal map's alpha (npcs.json
  "outfit_roughness"), the eyes' 0.08 giving them the key's catchlight, and a civilian's palette
  shifts the clothes per instance (openspec/changes/archive/2026-09-29-crowd-variety).

It lives in tools because it is authoring (CLAUDE.md 6.1): the committed .tres files are what the
game loads, and re-running overwrites them.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME = os.path.join(ROOT, "game")
OUT = os.path.join(GAME, "materials", "characters")
TABLE = os.path.join(ROOT, "tools", "blender", "npcs.json")
TEXTURES = "res://models/characters/"

# The skin is drawn by shaders/character_skin.gdshader: the numbers the StandardMaterial3D skin
# had, one for one, and a wetness per instance (design section 9). Its parameters, in the order
# Godot writes them.
SKIN_SHADER = "res://shaders/character_skin.gdshader"
SKIN = {
    "shader_parameter/specular": 0.42,
    "shader_parameter/normal_strength": 1.0,
    "shader_parameter/sss_strength": 0.3,
    "shader_parameter/transmittance_color": "Color(0.9, 0.35, 0.25, 1)",
    "shader_parameter/transmittance_depth": 0.2,
    "shader_parameter/transmittance_boost": 0.3,
}

# The outfit is drawn by shaders/character_outfit.gdshader (openspec/changes/archive/2026-09-29-crowd-variety): the
# same roughness from the normal map's alpha, and a civilian's palette per instance, the eyes left
# as they are. Its parameters, in the order Godot writes them.
OUTFIT_SHADER = "res://shaders/character_outfit.gdshader"
OUTFIT = {
    "shader_parameter/specular": 0.5,
    "shader_parameter/normal_strength": 1.0,
    "shader_parameter/eye_roughness_below": 0.3,
}
MATERIALS = {"skin": SKIN, "outfit": OUTFIT}
SHADERS = {"skin": SKIN_SHADER, "outfit": OUTFIT_SHADER}


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return v
    return repr(float(v)) if isinstance(v, float) else str(v)


def write(path, part, body_id=None):
    ext = [f"[ext_resource type=\"Shader\" path=\"{SHADERS[part]}\" id=\"0_shader\"]"]
    props = []
    if body_id is not None:
        albedo, normal = f"{TEXTURES}{body_id}_{part}_albedo.webp", f"{TEXTURES}{body_id}_{part}_normal.webp"
        ext += [f"[ext_resource type=\"Texture2D\" path=\"{albedo}\" id=\"1_albedo\"]",
                f"[ext_resource type=\"Texture2D\" path=\"{normal}\" id=\"2_normal\"]"]
        props = ["shader_parameter/albedo_texture = ExtResource(\"1_albedo\")",
                 "shader_parameter/normal_texture = ExtResource(\"2_normal\")"]
    head = f"[gd_resource type=\"ShaderMaterial\" load_steps={len(ext) + 1} format=3]\n\n" + "\n".join(ext) + "\n\n"
    body = [f"resource_name = \"{body_id}_{part}\"" if body_id else f"resource_name = \"character_{part}\""]
    body.append("shader = ExtResource(\"0_shader\")")
    body += [f"{k} = {fmt(v)}" for k, v in MATERIALS[part].items()] + props
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "[resource]\n" + "\n".join(body) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(TABLE, encoding="utf-8") as f:
        ids = [b["id"] for b in json.load(f)["bodies"]]
    for part in MATERIALS:
        write(os.path.join(OUT, f"character_{part}.tres"), part)
        for body_id in ids:
            write(os.path.join(OUT, f"{body_id}_{part}.tres"), part, body_id)
    print(f"wrote {len(MATERIALS)} templates and {len(MATERIALS) * len(ids)} body materials to game/materials/characters")


if __name__ == "__main__":
    main()

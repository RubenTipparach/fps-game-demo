#!/usr/bin/env python3
"""Generate the NPC skin and outfit materials (openspec/changes/character-lighting, design
sections 1 and 8).

    python3 tools/godot/gen_character_materials.py

Writes game/materials/characters/character_skin.tres and character_outfit.tres, the templates
(every setting, no textures), and one <id>_skin.tres and <id>_outfit.tres per body in
tools/blender/npcs.json: a template's settings with that body's textures, which the NPC import
step (setup_npc_import.gd) maps onto the glb's "<id>_skin" and "<id>_outfit" materials. The
settings live once, in SKIN and OUTFIT below, so the templates and the bodies can't disagree.

- The albedo is the body's skin atlas; the normal is the one derived from it (build_npcs.py), and
  its alpha is the roughness (npc_skin_roughness.png), read through roughness_texture_channel.
- Subsurface scattering in skin mode, strength 0.30, with transmittance (depth 0.2, boost 0.3),
  so ears glow against a rim gel.
- Specular 0.42: Godot's F0 is 0.16 x specular squared, so 0.028, MakeHuman's skins' 0.027.
- The outfit (clothes, gear and the eyes, which share its atlas) takes its roughness from its
  normal map's alpha (npcs.json "outfit_roughness"): the eyes' 0.08 gives them the key's
  catchlight, the design's character_eye.tres folded into the outfit.

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

# StandardMaterial3D properties, in the order Godot writes them.
SKIN = {
    "roughness": 1.0,
    "roughness_texture_channel": 3,          # the normal map's alpha
    "metallic_specular": 0.42,
    "normal_enabled": True,
    "normal_scale": 1.0,
    "subsurf_scatter_enabled": True,
    "subsurf_scatter_strength": 0.3,
    "subsurf_scatter_skin_mode": True,
    "subsurf_scatter_transmittance_enabled": True,
    "subsurf_scatter_transmittance_color": "Color(0.9, 0.35, 0.25, 1)",
    "subsurf_scatter_transmittance_depth": 0.2,
    "subsurf_scatter_transmittance_boost": 0.3,
}

OUTFIT = {
    "roughness": 1.0,
    "roughness_texture_channel": 3,          # the normal map's alpha
    "metallic_specular": 0.5,
    "normal_enabled": True,
    "normal_scale": 1.0,
}
MATERIALS = {"skin": SKIN, "outfit": OUTFIT}


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return v
    return repr(float(v)) if isinstance(v, float) else str(v)


def write(path, part, body_id=None):
    head, props = "[gd_resource type=\"StandardMaterial3D\" format=3]\n\n", []
    if body_id is not None:
        albedo, normal = f"{TEXTURES}{body_id}_{part}_albedo.webp", f"{TEXTURES}{body_id}_{part}_normal.webp"
        head = ("[gd_resource type=\"StandardMaterial3D\" load_steps=3 format=3]\n\n"
                f"[ext_resource type=\"Texture2D\" path=\"{albedo}\" id=\"1_albedo\"]\n"
                f"[ext_resource type=\"Texture2D\" path=\"{normal}\" id=\"2_normal\"]\n\n")
        props = ["albedo_texture = ExtResource(\"1_albedo\")", "roughness_texture = ExtResource(\"2_normal\")",
                 "normal_texture = ExtResource(\"2_normal\")"]
    body = [f"resource_name = \"{body_id}_{part}\"" if body_id else f"resource_name = \"character_{part}\""]
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

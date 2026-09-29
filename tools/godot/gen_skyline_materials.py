#!/usr/bin/env python3
"""Generate the skyline's material (openspec/changes/hub-skyline, design section 3).

    python3 tools/godot/gen_skyline_materials.py

Writes game/materials/skyline/skyline.tres, the one ShaderMaterial of shaders/skyline_tower.gdshader
that draws every tower (tools/levels/skyline.py: a face's part and neon role ride in its vertex
colour). It fills the shader's neon palette in skyline.NEON_ROLES order from the colour roles of
data/character_lighting.json, the one palette of the districts' neon, so a tower's crown and a
conversation's gel agree. import_presets.py maps the glb's "skyline" material onto the file.

It lives in tools because it is authoring (CLAUDE.md 6.1): re-running overwrites the file.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME = os.path.join(ROOT, "game")
OUT = os.path.join(GAME, "materials", "skyline")
SHADER = "res://shaders/skyline_tower.gdshader"
sys.path.insert(0, os.path.join(ROOT, "tools", "levels"))
import skyline  # noqa: E402


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.loads("\n".join(line for line in f if not line.lstrip().startswith("//")))


def linear(hexcode):
    """An sRGB hex colour as linear floats: the palette uniform has no source_color hint."""
    h = hexcode.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def main():
    palette = load_json(os.path.join(GAME, "data", "character_lighting.json"))["colors"]
    missing = [r for r in skyline.NEON_ROLES if r not in palette]
    if missing:
        raise SystemExit(f"skyline neon roles {missing} aren't colours in data/character_lighting.json")
    values = ", ".join(f"{c:.4f}" for role in skyline.NEON_ROLES for c in linear(palette[role]))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".tres"):
            os.remove(os.path.join(OUT, f))
    lines = ['[gd_resource type="ShaderMaterial" load_steps=2 format=3]', "",
             f'[ext_resource type="Shader" path="{SHADER}" id="1"]', "", "[resource]",
             f'resource_name = "{skyline.MATERIAL}"', 'shader = ExtResource("1")',
             f"shader_parameter/neon_palette = PackedVector3Array({values})"]
    with open(os.path.join(OUT, skyline.MATERIAL + ".tres"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {skyline.MATERIAL}.tres with {len(skyline.NEON_ROLES)} neon colours to game/materials/skyline")


if __name__ == "__main__":
    main()

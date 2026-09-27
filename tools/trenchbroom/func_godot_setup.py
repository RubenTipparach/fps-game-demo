#!/usr/bin/env python3
"""Writes the func_godot resources that connect TrenchBroom to the game:

  game/levels/trenchbroom/fgd/*.tres          entity definitions (monsters, items, lights, doors, triggers)
  game/levels/trenchbroom/brushfire_fgd.tres  the FGD file (func_godot's base classes + ours)
  game/levels/trenchbroom/brushfire_map_settings.tres
  game/levels/trenchbroom/brushfire_tb_config.tres   TrenchBroom game config (export it from the inspector)
  game/textures/{skip,clip,trigger,origin}.png       editor-only tool textures

    python3 tools/trenchbroom/func_godot_setup.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
from tscn import Raw, Resource, color, v2  # noqa: E402

GAME = os.path.join(ROOT, "game")
TB = "levels/trenchbroom"
FG = "res://addons/func_godot"


def aabb(x0, y0, z0, x1, y1, z1):
    # func_godot writes meta "size" as size(pos, size) = (mins, maxs) in Quake units
    return Raw(f"AABB({x0}, {y0}, {z0}, {x1}, {y1}, {z1})")


def dict_sv(d):
    items = ",\n".join(f'"{k}": {fmt_val(v)}' for k, v in d.items())
    return Raw("Dictionary[String, Variant]({\n" + items + "\n})")


def fmt_val(v):
    from tscn import fmt
    if isinstance(v, dict):
        return "{" + ", ".join(f'"{k}": {fmt_val(x)}' for k, x in v.items()) + "}"
    return fmt(v)


def point_class(name, desc, scene=None, size=(-16, -16, 0, 16, 16, 56), col=(0.9, 0.4, 0.1), props=None,
                prop_desc=None, node_class="", script=None, rotate=True):
    r = Resource("Resource")
    r.props = dict(script=r.ext_res("Script", f"{FG}/src/fgd/func_godot_fgd_point_class.gd"),
                   classname=name, description=desc)
    if props:
        r.props["class_properties"] = dict_sv(props)
    if prop_desc:
        r.props["class_property_descriptions"] = dict_sv(prop_desc)
    r.props["meta_properties"] = dict_sv({"size": aabb(*size), "color": color(*col)})
    if node_class:
        r.props["node_class"] = node_class
    if scene:
        r.props["scene_file"] = r.ext_res("PackedScene", scene)
    if script:
        r.props["script_class"] = r.ext_res("Script", script)
    r.props["apply_rotation_on_map_build"] = rotate
    r.save(os.path.join(GAME, TB, "fgd", name + ".tres"))
    return f"res://{TB}/fgd/{name}.tres"


def solid_class(name, desc, node_class, script=None, props=None, prop_desc=None, col=(0.6, 0.6, 0.8),
                build_visuals=True, gi_mode=1, collision_layer=1, collision_mask=0, shape_type=1, origin_type=4):
    r = Resource("Resource")
    r.props = dict(script=r.ext_res("Script", f"{FG}/src/fgd/func_godot_fgd_solid_class.gd"),
                   spawn_type=2, origin_type=origin_type, build_visuals=build_visuals,
                   global_illumination_mode=gi_mode, collision_shape_type=shape_type,
                   collision_layer=collision_layer, collision_mask=collision_mask,
                   classname=name, description=desc)
    if props:
        r.props["class_properties"] = dict_sv(props)
    if prop_desc:
        r.props["class_property_descriptions"] = dict_sv(prop_desc)
    r.props["meta_properties"] = dict_sv({"color": color(*col)})
    r.props["node_class"] = node_class
    if script:
        r.props["script_class"] = r.ext_res("Script", script)
    r.save(os.path.join(GAME, TB, "fgd", name + ".tres"))
    return f"res://{TB}/fgd/{name}.tres"


def main():
    defs = []
    red, blue, green, yellow = (0.9, 0.2, 0.15), (0.2, 0.5, 1.0), (0.2, 0.9, 0.3), (1.0, 0.8, 0.2)
    defs.append(point_class("info_player_start", "Player spawn point.", "res://scenes/props/player_start.tscn",
                            (-16, -16, 0, 16, 16, 56), green))
    ambush = {"ambush": {"No": 0, "Yes (ignore noise until it sees you)": 1}}
    defs.append(point_class("monster_grunt", "Grunt: robot rifleman, 3-round bursts.", "res://scenes/enemies/grunt.tscn",
                            (-14, -14, 0, 14, 14, 60), red, ambush))
    defs.append(point_class("monster_brute", "Brute: heavy melee charger.", "res://scenes/enemies/brute.tscn",
                            (-22, -22, 0, 22, 22, 80), red, ambush))
    defs.append(point_class("monster_drone", "Drone: hovering plasma turret. Place it in the air.",
                            "res://scenes/enemies/drone.tscn", (-16, -16, -16, 16, 16, 16), red, ambush))
    amount = {"amount": 0}
    amount_desc = {"amount": "Override the amount given (0 = default)."}
    items = [
        ("item_health", "Medkit (+25 health).", "health"),
        ("item_megahealth", "Megahealth (+100, overheal to 200).", "megahealth"),
        ("item_armor", "Green armor (+50).", "armor"),
        ("item_armor_heavy", "Red armor (+100).", "armor_heavy"),
        ("item_shells", "Box of shotgun shells.", "shells"),
        ("item_bullets", "Box of bullets.", "bullets"),
        ("item_rockets", "Rockets.", "rockets"),
        ("weapon_chaingun", "Chaingun (slot 2).", "weapon_chaingun"),
        ("weapon_rocketlauncher", "Rocket launcher (slot 3).", "weapon_rocket_launcher"),
    ]
    for cls, desc, scene in items:
        defs.append(point_class(cls, desc, f"res://scenes/pickups/{scene}.tscn", (-12, -12, 0, 12, 12, 24), blue,
                                amount, amount_desc))
    defs.append(point_class("misc_explobox", "Explosive barrel.", "res://scenes/props/explosive_barrel.tscn",
                            (-12, -12, 0, 12, 12, 38), yellow))
    defs.append(point_class("misc_doorway", "Split sliding door in a tech frame (fits a 96x102 unit opening). Face along 'angle'.",
                            "res://scenes/props/doorway.tscn", (-80, -24, 0, 80, 24, 136), (0.4, 0.8, 1.0)))
    defs.append(point_class("misc_archway_4x35", "Framed archway for a 128x112 unit opening.",
                            "res://scenes/props/archway_400x350.tscn", (-88, -24, 0, 88, 24, 144), (0.4, 0.8, 1.0)))
    defs.append(point_class("misc_archway_4x4", "Framed archway for a 128x128 unit opening.",
                            "res://scenes/props/archway_400x400.tscn", (-88, -24, 0, 88, 24, 160), (0.4, 0.8, 1.0)))
    defs.append(point_class("info_exit", "Level exit pad.", "res://scenes/props/exit.tscn",
                            (-32, -32, 0, 32, 32, 16), green))
    defs.append(point_class("light_fixture", "Ceiling light fixture: emissive panel + baked omni light. Origin = ceiling.",
                            "res://scenes/props/ceiling_light.tscn", (-20, -8, -4, 20, 8, 2), yellow))
    defs.append(point_class("light_wall", "Caged wall lamp (baked). Faces along 'angle'.",
                            "res://scenes/props/wall_lamp.tscn", (-6, -6, -6, 6, 6, 6), yellow))
    defs.append(point_class(
        "light", "Quake-style point light, baked into lightmaps.", None, (-8, -8, -8, 8, 8, 8), yellow,
        {"light": 300, "_color": color(1.0, 0.86, 0.7), "range": 0.0, "shadows": {"Yes": 1, "No": 0}},
        {"light": "Brightness (Quake scale, 300 = normal).", "_color": "Light colour.",
         "range": "Radius in metres (0 = derived from brightness).", "shadows": "Cast baked shadows."},
        node_class="OmniLight3D", script="res://addons/brushfire_tools/light_entity.gd", rotate=False))

    defs.append(solid_class(
        "func_door", "Sliding door. 'angle' sets the direction it opens (-1 = up, -2 = down).",
        "AnimatableBody3D", "res://scripts/World/Door.cs",
        {"angle": -1, "speed": 110, "wait": 2.5, "lip": 4},
        {"angle": "Open direction (Quake yaw, -1 up, -2 down).", "speed": "Units per second.",
         "wait": "Seconds before closing.", "lip": "Units left visible when open."},
        col=(0.4, 0.8, 1.0), gi_mode=2, collision_layer=64))
    trig = dict(build_visuals=False, gi_mode=0, collision_layer=0, collision_mask=0, col=(0.9, 0.6, 0.2))
    defs.append(solid_class("trigger_exit", "Ends the level when the player enters.", "Area3D",
                            "res://scripts/World/Trigger.cs", **trig))
    defs.append(solid_class("trigger_hurt", "Damages anything inside (lava, crushers).", "Area3D",
                            "res://scripts/World/Trigger.cs", {"dmg": 40}, {"dmg": "Damage per second."}, **trig))
    defs.append(solid_class("trigger_push", "Jump pad: launches the player upward.", "Area3D",
                            "res://scripts/World/Trigger.cs", {"speed": 352}, {"speed": "Launch speed (units/s)."}, **trig))
    defs.append(solid_class("trigger_secret", "Counts a secret area when entered.", "Area3D",
                            "res://scripts/World/Trigger.cs", **trig))
    defs.append(solid_class("trigger_message", "Shows 'message' once.", "Area3D",
                            "res://scripts/World/Trigger.cs", {"message": ""}, {"message": "Text to show."}, **trig))

    # FGD file: func_godot's base definitions (worldspawn, func_detail, func_illusionary...) + ours.
    r = Resource("Resource")
    base = [f"{FG}/fgd/phong_base.tres", f"{FG}/fgd/vertex_merge_distance_base.tres",
            f"{FG}/fgd/cull_interior_faces.tres", f"{FG}/fgd/worldspawn.tres", f"{FG}/fgd/func_geo.tres",
            f"{FG}/fgd/func_detail.tres", f"{FG}/fgd/func_detail_illusionary.tres", f"{FG}/fgd/func_illusionary.tres"]
    entries = [r.ext_res("Resource", p) for p in base + defs]
    r.props = dict(script=r.ext_res("Script", f"{FG}/src/fgd/func_godot_fgd_file.gd"), fgd_name="Brushfire",
                   entity_definitions=Raw("Array[Resource]([" + ", ".join(entries) + "])"))
    r.save(os.path.join(GAME, TB, "brushfire_fgd.tres"))

    # Map settings: 32 units per metre, textures/materials shared with the other levels.
    r = Resource("Resource")
    r.props = dict(script=r.ext_res("Script", f"{FG}/src/map/func_godot_map_settings.gd"),
                   inverse_scale_factor=32.0,
                   entity_fgd=r.ext_res("Resource", f"res://{TB}/brushfire_fgd.tres"),
                   uv_unwrap_texel_size=3.2,   # 3.2 / 32 = 0.1 m per lightmap texel, same as the CSG level
                   base_texture_dir="res://textures",
                   base_material_dir="res://materials",
                   save_generated_materials=False)
    r.save(os.path.join(GAME, TB, "brushfire_map_settings.tres"))

    # TrenchBroom game configuration. Select it in Godot and press "Export GameConfig" (after
    # setting your TrenchBroom games folder in func_godot's local config), or copy
    # tools/trenchbroom/Brushfire into TrenchBroom's games directory.
    r = Resource("Resource")
    tags = [r.ext_res("Resource", f"{FG}/game_config/trenchbroom/{t}.tres")
            for t in ("tb_face_tag_clip", "tb_face_tag_skip", "tb_face_tag_origin")]
    btags = [r.ext_res("Resource", f"{FG}/game_config/trenchbroom/{t}.tres") for t in ("tb_brush_tag_func", "tb_brush_tag_trigger")]
    r.props = dict(script=r.ext_res("Script", f"{FG}/src/trenchbroom/trenchbroom_game_config.gd"),
                   game_name="Brushfire",
                   icon=r.ext_res("Texture2D", "res://icon.svg"),
                   textures_root_folder="textures",
                   fgd_file=r.ext_res("Resource", f"res://{TB}/brushfire_fgd.tres"),
                   entity_scale="32",
                   brush_tags=Raw("Array[Resource]([" + ", ".join(btags) + "])"),
                   brushface_tags=Raw("Array[Resource]([" + ", ".join(tags) + "])"),
                   default_uv_scale=v2(0.0625, 0.0625))  # 1024 px textures = 2 m (64 units)
    r.save(os.path.join(GAME, TB, "brushfire_tb_config.tres"))

    make_tool_textures()
    print("func_godot resources written")


def make_tool_textures():
    """Tiny labelled textures so TrenchBroom can show tool brushes."""
    from PIL import Image, ImageDraw
    for name, rgb in (("skip", (200, 40, 160)), ("clip", (160, 40, 40)), ("trigger", (220, 140, 30)),
                      ("origin", (40, 120, 220))):
        img = Image.new("RGB", (64, 64), rgb)
        d = ImageDraw.Draw(img)
        for i in range(-64, 64, 16):
            d.line([(i, 0), (i + 64, 64)], fill=tuple(int(c * 0.7) for c in rgb), width=4)
        d.text((6, 26), name.upper(), fill=(255, 255, 255))
        img.save(os.path.join(GAME, "textures", name + ".png"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Writes game/levels/trenchbroom/level_trenchbroom.tscn: the Godot scene that hosts the
TrenchBroom map (FuncGodotMap node) plus environment, LightmapGI, probes and navigation.

    python3 tools/trenchbroom/gen_level_scene.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "godot"))
import level_common as lc  # noqa: E402
from tscn import Raw, Scene, v3  # noqa: E402

s = Scene("LevelTrenchBroom", "Node3D")
lc.setup_root(s, "E1M2: Slag Works")
nav = lc.add_navigation(s)
s.node("Map", "Node3D", nav,
       script=s.ext_res("Script", "res://addons/func_godot/src/map/func_godot_map.gd"),
       local_map_file="res://levels/trenchbroom/slag_works.map",
       map_settings=s.ext_res("Resource", "res://levels/trenchbroom/brushfire_map_settings.tres"),
       build_flags=1)
# Keep enemies out of the lava channel: carve it out of the navmesh.
s.node("LavaObstacle", "NavigationObstacle3D", nav, position=v3(0, -1.0, 7),
       vertices=Raw("PackedVector3Array(-16.5, 0, -3.3, 16.5, 0, -3.3, 16.5, 0, 3.3, -16.5, 0, 3.3)"),
       height=2.0, affect_navigation_mesh=True, carve_navigation_mesh=True, avoidance_enabled=False)

lc.add_environment(s, fog_color="#3a2418", fog_density=0.005)
lc.add_lightmap(s, texel_scale=1.0)
lc.add_fill_lights(s, [((0, 10, 18), "#4f7dff", 1.0, 18), ((0, 10, -2), "#4f7dff", 0.8, 16),
                       ((-23, 5, 18), "#ff7a3a", 0.7, 10), ((0, 9, -26), "#50ff90", 0.5, 9)])
lc.add_probes(s, [
    (0, 1.5, 41), (0, 1.5, 30), (0, 1.5, 22), (-8, 1.5, 17), (8, 1.5, 17), (0, 1.5, 12), (-8.5, 1.2, 7),
    (6.5, 1.2, 7), (0, 3.5, 7), (0, 1.5, 1), (-12, 1.5, 0), (13, 2.5, -1), (-8, 5.5, -5.5), (8, 5.5, -5.5),
    (0, 7, 8), (-22, 1.5, 13), (-26, 1.5, 22), (-20, 3.5, 18), (-31.5, 1.5, 18), (0, 5.5, -14),
    (0, 5.5, -26), (-4, 7, -26), (4, 7, -26),
])
lc.add_reflection_probes(s, [
    ("RefStart", (-5, 5), (0, 4), (36, 46)),
    ("RefCorridor", (-2, 2), (0, 4), (24.5, 36)),
    ("RefHallSouth", (-16, 16), (0, 12), (10, 24)),
    ("RefHallNorth", (-16, 16), (-0.9, 12), (-8, 10)),
    ("RefCrucible", (-30, -16.4), (0, 6), (10, 26)),
    ("RefExitCorridor", (-2, 2), (4, 8), (-20, -8.4)),
    ("RefExit", (-6, 6), (4, 10), (-32, -20)),
])
out = os.path.join(ROOT, "game", "levels", "trenchbroom", "level_trenchbroom.tscn")
s.save(out)
print("wrote", out)

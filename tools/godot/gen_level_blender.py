#!/usr/bin/env python3
"""Writes game/levels/blender/level_blender.tscn: hosts the Blender-made Cistern (cistern.glb,
entities are converted on import) plus environment, LightmapGI, probes and navigation.

    python3 tools/godot/gen_level_blender.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import level_common as lc  # noqa: E402
from tscn import Scene  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
s = Scene("LevelBlender", "Node3D")
lc.setup_root(s, "E1M3: The Cistern")
nav = lc.add_navigation(s)
s.instance("Cistern", "res://levels/blender/cistern.glb", nav)
lc.add_environment(s, fog_color="#1a2630", fog_density=0.007)
lc.add_lightmap(s, texel_scale=1.0)
lc.add_fill_lights(s, [((-8, 9, 9), "#4f7dff", 0.9, 18), ((8, 9, 9), "#4f7dff", 0.9, 18),
                       ((0, 6, 45), "#ffb070", 0.5, 10), ((-25, 4.5, 7), "#ff8a40", 0.6, 10),
                       ((24, 6, 6), "#4f7dff", 0.6, 12), ((0, 7, -28), "#50ff90", 0.5, 10)])
lc.add_probes(s, [
    (0, 1.5, 46), (0, 4.5, 45), (0, 1.5, 34), (0, 1.5, 29.5), (-14, 1.5, 24), (14, 1.5, 24), (-14, 1.5, -6),
    (14, 1.5, -6), (0, 1.5, -7), (-6, -1.5, 12), (6, -1.5, 2), (0, -1.5, 6), (-6, -1.5, 0), (6, -1.5, 18),
    (0, 5, 9), (-8, 8, 1), (8, 8, 17), (16, -2, 9), (16, 1.5, 12), (-25, 1.5, 7), (-25, 4, 11), (24, 3.5, 6),
    (24, 3.5, -4), (24, 6, 14), (0, 1.5, -16), (0, 1.5, -28), (0, 5, -28), (-4, 2, -32),
])
lc.add_reflection_probes(s, [
    ("RefEntry", (-5, 5), (0, 10.2), (40, 50)),
    ("RefTunnelS", (-2, 2), (0, 5), (28.4, 40)),
    ("RefCistern", (-18, 18), (-3, 11), (-10, 28)),
    ("RefPump", (-32, -18.4), (0, 6), (0, 14)),
    ("RefOverflow", (18.4, 30), (2, 8), (-8, 20)),
    ("RefTunnelN", (-2, 2), (0, 5), (-22, -10.4)),
    ("RefExit", (-6, 6), (0, 12.2), (-34, -22)),
])
out = os.path.join(ROOT, "game", "levels", "blender", "level_blender.tscn")
s.save(out)
print("wrote", out)

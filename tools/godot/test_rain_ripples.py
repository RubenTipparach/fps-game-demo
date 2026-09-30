"""One ripple for all the rain (openspec/changes/street-puddles, design section 3.3): the canal's
water and the street's ground both include game/shaders/rain_ripples.gdshaderinc, neither defines
a ripple of its own, and the ground's committed materials carry the water's ripple numbers, so a
drop on a puddle and a drop on the canal can't drift apart (CLAUDE.md 5.1). It reads the committed
shaders and .tres files.

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import json
import os
import re
import unittest

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "game")
INCLUDE = '#include "res://shaders/rain_ripples.gdshaderinc"'
RIPPLES = ("ripple_cell_m", "ripple_rate_hz", "ripple_strength", "ripple_wave_per_m", "ripple_falloff_per_m")


def read(rel):
    with open(os.path.join(GAME, rel)) as f:
        return f.read()


def tres_params(name):
    return {k: float(v) for k, v in re.findall(r"^shader_parameter/(\w+) = ([-\d.]+)$", read(f"materials/{name}.tres"), re.M)}


class OneRippleForAllTheRain(unittest.TestCase):
    def test_the_canal_and_the_ground_include_the_one_ripple(self):
        for shader in ("shaders/water.gdshader", "shaders/city_ground.gdshader"):
            src = read(shader)
            self.assertIn(INCLUDE, src, shader)
            self.assertNotRegex(src, r"\bvec2\s+\w*ripples\s*\(", f"{shader} defines a ripple of its own")
            self.assertNotRegex(src, r"\bfloat\s+\w*hash12\s*\(", f"{shader} defines its own drop hash")
        self.assertRegex(read("shaders/rain_ripples.gdshaderinc"), r"vec2 rain_ripples\(")

    def test_the_ground_draws_with_the_water_s_numbers(self):
        with open(os.path.join(GAME, "materials", "materials.json")) as f:
            water = json.load(f)["water"]["shader_params"]
        for name in ("asphalt", "paving_wet"):
            params = tres_params(name)
            for key in RIPPLES:
                self.assertEqual(float(water[key]), params[key], f"{name}.{key}: the water's own, copied by postprocess.py")

    def test_the_ground_draws_no_puddle_until_a_level_sets_its_mask(self):
        project = read("project.godot")
        self.assertRegex(project, r'puddle_rect_m=\{\n"type": "vec4",\n"value": Vector4\(0, 0, 0, 0\)\n\}',
                         "an empty rect: the editor and the lightmap bake draw no puddles")
        self.assertIn("puddle_rect_m.z <= 0.0", read("shaders/city_ground.gdshader"))


if __name__ == "__main__":
    unittest.main()

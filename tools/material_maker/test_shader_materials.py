"""Materials drawn by their own shader (materials.json "shader"): the committed .tres is what
postprocess.py writes, a parameter the shader doesn't declare is refused, and the canal water
stays opaque so Godot's screen-space reflections reach it (openspec/changes/archive/2026-09-29-water-and-swimming,
design section 6: transparent, it reflected nothing and read black from swimming height).

    python3 -m unittest discover -s tools/material_maker -p 'test_*.py'
"""
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import postprocess  # noqa: E402

GAME = os.path.join(os.path.dirname(os.path.dirname(HERE)), "game")
MATERIALS = os.path.join(GAME, "materials")


def manifest():
    with open(os.path.join(MATERIALS, "materials.json")) as f:
        return json.load(f)


def shader_materials():
    return {n: s for n, s in manifest().items() if not n.startswith("_") and "shader" in s}


class ShaderMaterials(unittest.TestCase):
    def test_the_committed_materials_are_what_the_generator_writes(self):
        for name, spec in shader_materials().items():
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "materials")
                os.makedirs(out)
                os.symlink(os.path.join(GAME, "shaders"), os.path.join(tmp, "shaders"))
                postprocess.write_shader_material(out, name, spec, manifest())
                with open(os.path.join(out, name + ".tres")) as want, open(os.path.join(MATERIALS, name + ".tres")) as got:
                    self.assertEqual(want.read(), got.read(), f"{name}.tres differs: regenerate it with postprocess.py")

    def test_a_parameter_the_shader_lacks_is_refused(self):
        spec = dict(shader_materials()["water"])
        spec["shader_params"] = dict(spec["shader_params"], clarity=0.55)
        with self.assertRaises(SystemExit) as refused:
            postprocess.write_shader_material(MATERIALS, "water_stale", spec)
        self.assertIn("no uniform clarity", str(refused.exception))
        self.assertFalse(os.path.exists(os.path.join(MATERIALS, "water_stale.tres")), "a refused material is not written")

    def test_the_water_stays_opaque(self):
        with open(os.path.join(GAME, "shaders", "water.gdshader")) as f:
            src = re.sub(r"//.*", "", f.read())
        for transparent in ("hint_screen_texture", "hint_depth_texture", "ALPHA", "blend_"):
            self.assertNotIn(transparent, src, f"{transparent} makes the water transparent, and screen-space "
                                               "reflections skip transparent materials")


if __name__ == "__main__":
    unittest.main()

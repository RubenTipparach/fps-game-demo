"""The NPC skin and outfit materials (openspec/changes/character-lighting, "Skin has normals,
roughness and scattering"): the committed .tres files are what gen_character_materials.py writes,
one skin and one outfit per body in npcs.json, and the skin's specular gives MakeHuman's F0.

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_character_materials as G  # noqa: E402


class CharacterMaterials(unittest.TestCase):
    def test_the_committed_materials_are_what_the_generator_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, G.OUT = G.OUT, tmp
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    G.main()
            finally:
                G.OUT = out
            for name in sorted(os.listdir(tmp)):
                with open(os.path.join(tmp, name), encoding="utf-8") as want, \
                        open(os.path.join(G.OUT, name), encoding="utf-8") as got:
                    self.assertEqual(want.read(), got.read(), f"{name} differs: run tools/godot/gen_character_materials.py")

    def test_every_body_has_a_skin_and_an_outfit(self):
        with open(G.TABLE, encoding="utf-8") as f:
            ids = [b["id"] for b in json.load(f)["bodies"]]
        missing = [f"{i}_{part}.tres" for i in ids for part in G.MATERIALS
                   if not os.path.exists(os.path.join(G.OUT, f"{i}_{part}.tres"))]
        self.assertEqual([], missing)

    def test_the_skin_reflects_like_makehumans(self):
        f0 = 0.16 * G.SKIN["metallic_specular"] ** 2
        self.assertAlmostEqual(0.028, f0, delta=0.001, msg="Godot's F0 is 0.16 x specular squared; skin's is 0.028")


if __name__ == "__main__":
    unittest.main()

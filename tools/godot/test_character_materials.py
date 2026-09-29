"""The NPC skin and outfit materials (openspec/changes/archive/2026-09-29-character-lighting, "Skin has normals,
roughness and scattering" and "Characters are dry under a roof and wet in the rain"): the
committed .tres files are what gen_character_materials.py writes, one skin and one outfit per body
in npcs.json; the skin's specular gives MakeHuman's F0; every parameter the generator writes is a
uniform of its shader; both shaders take a per-instance wetness; and every global they read is
declared in project.godot and set by name from data (CharacterShading.cs).

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import contextlib
import io
import json
import os
import re
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
        f0 = 0.16 * G.SKIN["shader_parameter/specular"] ** 2
        self.assertAlmostEqual(0.028, f0, delta=0.001, msg="Godot's F0 is 0.16 x specular squared; skin's is 0.028")

    def test_every_parameter_the_generator_writes_is_a_uniform_of_its_shader(self):
        for part, shader in G.SHADERS.items():
            uniforms = set(re.findall(r"^uniform \w+ (\w+)", read_shader(shader), re.M))
            written = {k.split("/", 1)[1] for k in G.MATERIALS[part]} | {"albedo_texture", "normal_texture"}
            self.assertEqual(set(), written - uniforms,
                             f"{part}: a parameter its shader lacks would be dropped silently on load")

    def test_skin_and_cloth_take_a_wetness_per_character(self):
        for part, shader in G.SHADERS.items():
            self.assertIn("wetness", instance_uniforms(read_shader(shader)),
                          f"{part}: BodyWetness sets 'wetness' on every mesh of a body (design section 9)")

    def test_instance_uniforms_the_shaders_share_sit_at_the_same_index(self):
        # The skin and the outfit are surfaces of one mesh instance. A uniform both declare at
        # different indices is read by only one of them: the first capture's skin ignored its
        # wetness this way, with Godot warning 108 times.
        found = {part: instance_uniforms(read_shader(shader)) for part, shader in G.SHADERS.items()}
        for name in set.intersection(*(set(u) for u in found.values())):
            indices = {part: u[name] for part, u in found.items()}
            self.assertEqual(1, len(set(indices.values())), f"'{name}' sits at {indices}")
            self.assertIsNotNone(next(iter(indices.values())), f"'{name}' needs an explicit instance_index")

    def test_every_global_the_shaders_read_is_declared_and_set_from_data(self):
        with open(os.path.join(G.GAME, "project.godot"), encoding="utf-8") as f:
            project = f.read()
        declared = set(re.findall(r"(?m)^(\w+)=\{\n\"type\"", project.split("[shader_globals]", 1)[-1]))
        with open(os.path.join(G.GAME, "scripts", "Undercity", "Lighting", "CharacterShading.cs"), encoding="utf-8") as f:
            set_by_name = set(re.findall(r'const string \w+ = "(\w+)"', f.read()))
        read = set()
        for shader in G.SHADERS.values():
            read |= set(re.findall(r"(?m)^global uniform \w+ (\w+);", read_shader(shader)))
        self.assertTrue(read, "the character shaders read their dry and wet numbers as globals")
        self.assertEqual(set(), read - declared, "a global a shader reads must be declared in project.godot, or it won't compile")
        self.assertEqual(read, set_by_name, "every global is set from data/character_lighting.json at start, and nothing else is")


def instance_uniforms(text):
    """Each instance uniform's name and its instance_index, or None when it has none."""
    return {m.group(1): (int(m.group(2)) if m.group(2) else None)
            for m in re.finditer(r"(?m)^instance uniform \w+ (\w+)(?:\s*:[^=;]*?instance_index\((\d+)\))?", text)}


def read_shader(res_path):
    with open(os.path.join(G.GAME, res_path.removeprefix("res://")), encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    unittest.main()

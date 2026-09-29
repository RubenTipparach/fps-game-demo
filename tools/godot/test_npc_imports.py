"""The NPC bodies' import options (openspec/changes/archive/2026-09-28-npc-characters, design
section 5): every body glb's retarget options are keyed by its skeleton's path before the
retarget renames it. A key naming "GeneralSkeleton", the name the retarget gives, matches no node
at import time, so a clean import would leave that body un-retargeted and its NPC scene broken.
setup_npc_import.gd once wrote such keys when it was run a second time.

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import glob
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BODIES = os.path.join(HERE, "..", "..", "game", "models", "characters")


class NpcImports(unittest.TestCase):
    def test_every_body_is_retargeted_by_its_skeletons_imported_path(self):
        imports = sorted(glob.glob(os.path.join(BODIES, "*.glb.import")))
        self.assertTrue(imports, "no body imports found")
        for path in imports:
            with open(path, encoding="utf-8") as f:
                keys = re.findall(r'"PATH:([^"]+)": \{\n"retarget/bone_map"', f.read())
            name = os.path.basename(path)
            self.assertEqual(1, len(keys), f"{name}: one skeleton with retarget options, found {keys}")
            self.assertNotIn("GeneralSkeleton", keys[0],
                             f"{name}: the options name the retargeted skeleton; run tools/godot/setup_npc_import.gd")


if __name__ == "__main__":
    unittest.main()

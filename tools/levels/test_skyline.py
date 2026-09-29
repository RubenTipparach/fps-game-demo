"""The skyline's four rules (openspec/changes/hub-skyline, design section 2), on the hub's own
layout and on layouts broken on purpose, each failing case naming what it breaks.

    python3 -m unittest discover -s tools/levels -p 'test_*.py'
"""
import copy
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skyline  # noqa: E402
from layouts.hub import MAP, H, W  # noqa: E402


def towers():
    return copy.deepcopy(MAP["skyline"])


class SkylineRules(unittest.TestCase):
    def test_the_hubs_skyline_keeps_every_rule(self):
        self.assertEqual([], skyline.problems(towers(), W, H))

    def test_a_tower_inside_the_margin_is_refused_by_name(self):
        t = towers()
        next(x for x in t if x["id"] == "pier_nine")["at"] = (300, 170)     # the design's first place: 20 m off
        found = skyline.problems(t, W, H)
        self.assertTrue(any("pier_nine stands 20.0 m" in p for p in found), found)

    def test_a_horizon_without_tall_towers_fails_naming_the_bearings(self):
        # without every tower north-east of north, near ring and far, that slice is open sky
        cx, cy = W / 2, H / 2
        t = [x for x in towers() if not (-45 < (skyline._bearing(cx, cy, *x["at"]) + 180) % 360 - 180 < 75)]
        found = skyline.problems(t, W, H)
        self.assertTrue(any("bearings 0-30 have no tower" in p for p in found), found)

    def test_overlapping_towers_are_refused(self):
        t = towers()
        t.append({"id": "twin", "at": (170, -60), "size": (40, 40), "height_m": 100, "style": "slab"})
        found = skyline.problems(t, W, H)
        self.assertTrue(any("halcyon_spire overlaps twin" in p for p in found), found)

    def test_a_skyline_over_its_triangle_budget_is_refused(self):
        t = towers()
        t += [{"id": f"extra_{i}", "at": (2000 + 30 * i, 2000), "size": (20, 20), "height_m": 100, "style": "arcology",
               "crown": "halo"} for i in range(260)]
        found = skyline.problems(t, W, H)
        self.assertTrue(any("triangles (budget 30000)" in p for p in found), found)


    def test_a_neon_the_palette_lacks_is_refused_by_name(self):
        t = towers()
        next(x for x in t if x["id"] == "sable_mutual")["neon"] = "teal"
        found = skyline.problems(t, W, H)
        self.assertTrue(any("sable_mutual names neon 'teal'" in p for p in found), found)

    def test_a_searchlight_above_its_tower_is_refused_by_name(self):
        t = towers()
        next(x for x in t if x["id"] == "halcyon_spire")["searchlights"]["height_m"] = 460
        found = skyline.problems(t, W, H)
        self.assertTrue(any("halcyon_spire: no tier at the searchlights' height 460 m" in p for p in found), found)

    def test_the_spires_lamps_stand_off_its_needle(self):
        spire = next(x for x in towers() if x["id"] == "halcyon_spire")
        lamps = skyline.searchlights(spire)
        needle = [(lo, hi) for lo, hi, part in skyline.massing(spire, (0, 0)) if part == skyline.FACADE][-1]
        self.assertEqual(2, len(lamps))
        for lamp in lamps:
            x, y, z = lamp["at"]
            gap = max(needle[0][0] - x, x - needle[1][0], needle[0][1] - y, y - needle[1][1])
            self.assertAlmostEqual(skyline.LAMP_OFF_M, gap, msg="a lamp stands off the needle's face, not in it")
            self.assertEqual(420, z)


class SkylineColours(unittest.TestCase):
    """A face's part and neon role ride in its vertex colour's blue; the shader decodes them."""

    SHADER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "game", "shaders", "skyline_tower.gdshader")

    def test_every_part_and_role_survives_8_bit_colour(self):
        tower = {"id": "t", "lit": 0.3}
        for part in skyline.PARTS:
            for role in skyline.NEON_ROLES:
                blue = skyline.vertex_color({**tower, "neon": role}, part)[2]
                code = round(round(blue * 255) / 255 * skyline.CODE_SCALE)
                self.assertEqual((part, role), (skyline.PARTS[code // len(skyline.NEON_ROLES)],
                                                skyline.NEON_ROLES[code % len(skyline.NEON_ROLES)]),
                                 "an 8-bit colour must still decode to the face's part and neon")
                self.assertLess(blue, 1.0, "the codes must fit under full blue")

    def test_the_shader_decodes_with_the_same_numbers(self):
        with open(self.SHADER, encoding="utf-8") as f:
            src = f.read()
        self.assertIn(f"const float CODE_SCALE = {skyline.CODE_SCALE};", src)
        self.assertIn(f"const int ROLES = {len(skyline.NEON_ROLES)};", src)
        self.assertRegex(src, rf"uniform vec3 neon_palette\[{len(skyline.NEON_ROLES)}\];",
                         "the palette uniform holds one colour per neon role")
        parts = re.findall(r"part == (\d)", src)
        self.assertEqual(sorted({int(p) for p in parts}), [1, 2, 3], "the shader branches on parts 1-3, 0 is the facade")


if __name__ == "__main__":
    unittest.main()

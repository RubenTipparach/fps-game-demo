"""Tests that the committed puddle mask agrees with the level plan (openspec/changes/archive/2026-09-30-street-puddles,
"Puddles lie where water gathers", scenario "The mask"). It reads the real file the game loads
(CLAUDE.md 5.6, "validate the real artifact"), not a copy of what the writer meant to write.

    python3 -m unittest discover -s tools/levels -p 'test_*.py'
"""
import contextlib
import io
import os
import sys
import unittest

import numpy as np
from PIL import Image
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import city_plan as CP  # noqa: E402
import puddle_mask as PM  # noqa: E402


class TheHubsMaskAgreesWithItsPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m, ents = CP.load("hub")
        cls.city = CP.City(m, ents)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.city.build()
        cls.mask = np.asarray(Image.open(PM.path("hub")))

    def texel(self, x, y):
        """The (distance, height) the mask holds at the texel under a layout point."""
        j, i = int(y / PM.TEXEL_M), int(x / PM.TEXEL_M)
        return PM.decode_distance(self.mask[j, i, 0]), PM.decode_height(self.mask[j, i, 1])

    def test_it_is_the_mask_the_plan_writes_now(self):
        dist, height = PM.rasterize(self.city.puddle_list, (self.city.P.W, self.city.P.H))
        self.assertEqual(self.mask.shape, dist.shape + (2,), "a texel is TEXEL_M over the whole level")
        self.assertTrue(np.array_equal(self.mask[..., 0], PM.encode_distance(dist)),
                        "the committed mask is stale: run tools/levels/export_level_data.py")
        self.assertTrue(np.array_equal(self.mask[..., 1], PM.encode_height(height)))

    def test_every_puddle_reads_as_water_at_its_own_height(self):
        for p in self.city.puddle_list:
            c = p["g"].representative_point()
            d, z = self.texel(c.x, c.y)
            self.assertLess(d, 0.0, f"{p['id']} at ({c.x:.2f}, {c.y:.2f})")
            self.assertAlmostEqual(z, p["ground_m"], delta=0.03, msg=f"{p['id']}: the shader tests the height to 0.03 m")

    def test_ground_clear_of_every_puddle_reads_dry(self):
        tree = CP.shapely.STRtree([p["g"] for p in self.city.puddle_list])
        checked = 0
        for p in self.city.puddle_list:
            ring = p["g"].buffer(0.3).exterior
            for k in range(16):
                pt = ring.interpolate(k / 16, normalized=True)
                if not (0 <= pt.x < self.city.P.W and 0 <= pt.y < self.city.P.H):
                    continue    # past the level's edge, where the mask has no texel
                if any(self.city.puddle_list[i]["g"].distance(pt) < 0.3 for i in tree.query(pt.buffer(0.3))):
                    continue
                d, _ = self.texel(pt.x, pt.y)
                # the texel's centre is up to 0.09 m from the point, and a step is 4 mm
                self.assertGreater(d, 0.2, f"0.3 m outside {p['id']}, at ({pt.x:.2f}, {pt.y:.2f})")
                checked += 1
        self.assertGreater(checked, 1000)

    def test_the_skyways_road_reads_dry(self):
        deck = next(g for label, g, _ in self.city.P.shelters if label == "Skyway deck")
        road = self.city.puddle_ground()["ground"][CP.STREET_Z][2]
        under = deck.intersection(road).buffer(-0.5)
        wet = 0
        x0, y0, x1, y1 = under.bounds
        for x in np.arange(x0, x1, 0.5):
            for y in np.arange(y0, y1, 0.5):
                if under.contains(Point(x, y)) and self.texel(x, y)[0] < 0.0:
                    wet += 1
        self.assertEqual(wet, 0, "no rain falls under the deck")


if __name__ == "__main__":
    unittest.main()

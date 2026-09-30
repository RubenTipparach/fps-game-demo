"""The city ground's committed textures hold no standing water (openspec/changes/street-puddles,
design sections 3.1 and 3.7): the level plan places the puddles and the ground's shader draws them,
so a texture that still carried its own would repeat a puddle every tile. It reads the committed
ORM maps (CLAUDE.md 5.6, validate the real artifact).

    python3 -m unittest discover -s tools/fx -p 'test_*.py'
"""
import os
import unittest

import numpy as np
from PIL import Image

GAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "game")
STANDING_WATER_ROUGHNESS = 0.2    # a texel under this is a mirror: standing water, not a wet surface


def roughness(name):
    return np.asarray(Image.open(os.path.join(GAME, "textures", f"{name}_orm.png")).convert("RGB"))[..., 1] / 255.0


class TheGroundHoldsNoStandingWater(unittest.TestCase):
    def test_no_texel_of_the_ground_is_a_puddle(self):
        for name in ("asphalt", "paving_wet"):
            r = roughness(name)
            self.assertFalse((r < STANDING_WATER_ROUGHNESS).any(),
                             f"{name}: {(r < STANDING_WATER_ROUGHNESS).mean():.1%} of its texels are standing water; "
                             "the ground shader draws the plan's puddles")

    def test_the_ground_still_reads_rain_wet(self):
        for name, lo, hi in (("asphalt", 0.45, 0.65), ("paving_wet", 0.30, 0.44)):
            r = roughness(name)
            self.assertTrue(lo - 0.05 <= r.mean() <= hi, f"{name}: mean roughness {r.mean():.3f}, the design's {lo}-{hi}")


if __name__ == "__main__":
    unittest.main()

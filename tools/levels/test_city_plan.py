"""Tests of the city plan's level rules that a layout alone can't show: ways out of the water
(openspec/changes/water-and-swimming, "Every water body has a way out") and people kept out of
it ("People stand clear of the level"). Each test builds on the committed hub.

    python3 -m unittest discover -s tools/levels -p 'test_*.py'
"""
import contextlib
import io
import math
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import city_plan as CP  # noqa: E402
import render_map as RM  # noqa: E402


def built_hub():
    m, ents = CP.load("hub")
    city = CP.City(m, ents)
    with contextlib.redirect_stdout(io.StringIO()):
        city.build()
    return city


class WaysOutOfTheWater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_every_point_of_the_hubs_water_is_a_short_swim_from_a_way_out(self):
        self.assertEqual(self.city.exit_problems(), [])

    def test_a_canal_with_its_ladders_removed_fails_naming_the_canal_and_a_point(self):
        problems = self.city.exit_problems(ladders=[])
        cut = [p for p in problems if p.startswith("the_cut:")]
        self.assertEqual(len(cut), 1, f"the Cut must fail with no ladders: {problems}")
        self.assertRegex(cut[0], r"the farthest is \(\d+(\.\d+)?, \d+(\.\d+)?\), with no way out at all")

    def test_a_canal_with_one_ladder_fails_at_its_far_end(self):
        one = [ld for ld in self.city.ladders if ld["id"] == "the_cut_1"]
        problems = [p for p in self.city.exit_problems(ladders=one) if p.startswith("the_cut:")]
        self.assertEqual(len(problems), 1)
        # the_cut_1 is at the north end: the farthest water is at the south end, 140 m and more away
        far = float(problems[0].split("), ")[1].split(" m")[0])
        self.assertGreater(far, 140, "the swim is measured the length of the canal, not across it")

    def test_a_quay_low_enough_to_climb_onto_needs_no_ladder(self):
        # were the game to let a swimmer climb 3 m, every quay of the Cut would be a way out
        with mock.patch.object(CP, "mantle_rise", return_value=(0.2, 3.0)):
            problems = self.city.exit_problems(ladders=[])
        self.assertFalse([p for p in problems if p.startswith("the_cut:")], problems)

    def test_quay_ladders_keep_clear_of_bridges_boats_and_pillars(self):
        boats = [RM.shape_geom(fx) for fx in self.city.m["props"] if fx[0] == "poly" and fx[-1] == "fix"
                 and RM.shape_geom(fx).intersects(self.city.W)]
        for ld in self.city.ladders:
            if ld["id"].endswith("_outfall"):
                continue
            pt = CP.Point(ld["at"])
            for what, g in [("a bridge", self.city.bridge_u)] + [("a boat", b) for b in boats] + \
                    [("a pillar", p) for p in self.city.water_pillars()]:
                self.assertGreaterEqual(g.distance(pt), CP.LADDER_CLEAR_M - 1e-6, f"{ld['id']} is too close to {what}")

    def test_every_ladder_reaches_under_the_surface_and_tops_out_on_a_floor(self):
        for ld in self.city.ladders:
            water = next(w for w in self.city.waters if w["id"] == ld["water"])
            self.assertAlmostEqual(ld["bottom"], water["surface"] - CP.LADDER_UNDER_M, 6)
            self.assertGreater(ld["top"], water["surface"], f"{ld['id']} must top out above the water")
            self.assertGreaterEqual(ld["top"], ld["floor"], f"{ld['id']} climbs over anything between the edge and its landing")

    def test_a_ladder_steps_off_past_a_kerb_onto_level_ground(self):
        # the Cut's east quay has a raised strip under a metre wide between the water and Quay Road
        kerbed = [ld for ld in self.city.ladders if ld["top"] > ld["floor"]]
        self.assertTrue(kerbed, "some ladders land past the quay's kerb")
        for ld in kerbed:
            x, y = ld["at"]
            n = ld["n"]
            lx, ly = x + n[0] * ld["step_in"], y + n[1] * ld["step_in"]
            self.assertAlmostEqual(self.city.ground_level(lx, ly), ld["floor"], 6, f"{ld['id']} lands on its floor")

    def test_the_outfalls_rungs_are_a_ladder(self):
        self.assertIn("the_cut_outfall", [ld["id"] for ld in self.city.ladders])

    def test_a_ladder_opens_the_quay_railing(self):
        # railing posts are 0.07 m boxes inset 0.12 m from the quay edge
        for ld in self.city.ladders:
            if ld["id"].endswith("_outfall") or "_hull_" in ld["id"]:
                continue
            x, y = ld["at"]
            n = ld["n"]
            px, py = x + n[0] * 0.12, y + n[1] * 0.12
            posts = [pr for sec in self.city.P.sectors.values() for obj in sec["objects"].values()
                     if obj["name"].startswith("streets_walk") for pr in obj["prims"]
                     if pr.get("t") == "hexa" and self.is_post(pr, px, py)]
            self.assertEqual(posts, [], f"{ld['id']}: a railing post stands in its opening")

    @staticmethod
    def is_post(pr, px, py):
        xs, ys = [q[0] for q in pr["p"]], [q[1] for q in pr["p"]]
        small = max(xs) - min(xs) < 0.1 and max(ys) - min(ys) < 0.1
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        return small and math.dist((cx, cy), (px, py)) < CP.RAIL_GAP_M / 2 - 0.05


class PeopleStayOutOfTheWater(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city = built_hub()

    def test_a_civilian_standing_in_the_cut_is_refused(self):
        problems = self.city.standing_problems("civ:test", 203, 100, -4.5, "outdoors", "npc")
        self.assertTrue(any("stands in the water of the_cut" in p for p in problems), problems)

    def test_a_civilian_on_the_tin_bridge_is_not_in_the_water(self):
        problems = self.city.standing_problems("civ:test", 203, 62.2, 0.0, "outdoors", "npc")
        self.assertFalse(any("water" in p for p in problems), problems)

    def test_a_patrol_across_the_cut_is_refused_naming_the_water(self):
        saved = self.city.entities_in
        self.city.entities_in = [{"kind": "npc", "id": "swimmer", "at": (185, 100),
                                  "props": {"patrol": "185,100;220,100"}}]
        try:
            problems = self.city.patrol_leg_problems()
        finally:
            self.city.entities_in = saved
        self.assertTrue(problems and "water" in problems[0], problems)

    def test_a_patrol_over_the_tin_bridge_is_allowed(self):
        saved = self.city.entities_in
        self.city.entities_in = [{"kind": "npc", "id": "walker", "at": (188, 62.2),
                                  "props": {"patrol": "188,62.2;218,62.2"}}]
        try:
            problems = self.city.patrol_leg_problems()
        finally:
            self.city.entities_in = saved
        self.assertFalse([p for p in problems if "water" in p], problems)


if __name__ == "__main__":
    unittest.main()

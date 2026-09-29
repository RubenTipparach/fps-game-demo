"""The framed doorway (openspec/changes/hub-doorways, "Every doorway is framed", design section
3.2): detailing.door_frame keeps the clear opening a person walks through, is carved at its fits,
stands proud of the wall, stays in its triangle budget and never z-fights with the walls it sits
in.

    python3 -m unittest discover -s tools/godot -p 'test_*.py'
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import detailing as D  # noqa: E402

WALL_T = 0.2
BASEBOARDS_M = (0.30, 0.35, 0.45)   # CLAUDE.md 7.2: plinth heights taken by baseboards


def airs_round(clear_w, clear_h):
    """Two rooms either side of a wall along x at z 0-0.2 (Godot axes: y up), and the door's
    carved air through it at its fits, as city_plan carves an interior door."""
    fw, fh = D.door_fits(clear_w, clear_h)
    return [D.Room("north", (-6, 6), (0, 4), (-6, 0)), D.Room("south", (-6, 6), (0, 4), (WALL_T, 6)),
            D.Room("door", (-fw / 2, fw / 2), (0, fh), (-0.05, WALL_T + 0.05))]


def as_details(boxes):
    """The frame's (u, v, z-up) boxes as the checker's (x, y-up, z) details."""
    return [((b["lo"][0], b["lo"][2], b["lo"][1]), (b["hi"][0], b["hi"][2], b["hi"][1]), f"{b['part']}{i}")
            for i, b in enumerate(boxes)]


class DoorFrame(unittest.TestCase):
    def test_an_interior_door_is_carved_at_its_fits_and_keeps_its_clear_opening(self):
        self.assertEqual((1.6, 2.5), tuple(round(v, 6) for v in D.door_fits(1.4, 2.4)),
                         "the spec's interior door: 1.4 x 2.4 clear, carved 1.6 x 2.5")
        boxes = D.door_frame(1.4, 2.4, WALL_T)
        jambs = [b for b in boxes if b["part"] == "liner" and b["hi"][2] == 2.4]
        self.assertEqual([-0.7, 0.7], sorted(b["hi"][0] if b["lo"][0] < 0 else b["lo"][0] for b in jambs),
                         "the liners' inner faces are the clear opening's jambs")
        head = [b for b in boxes if b["part"] == "liner" and b["lo"][2] == 2.4]
        self.assertEqual(1, len(head), "one head liner, under the lintel, at the clear height")
        self.assertAlmostEqual(2.5, head[0]["hi"][2], msg="the head liner fills the reveal up to the fits")

    def test_the_architrave_stands_a_reveal_proud_on_both_faces(self):
        arch = [b for b in D.door_frame(1.4, 2.4, WALL_T) if b["part"] == "architrave"]
        self.assertEqual(6, len(arch))
        self.assertEqual({round(-D.REVEAL, 6), round(WALL_T + D.REVEAL, 6)},
                         {round(b["lo"][1] if b["lo"][1] < 0 else b["hi"][1], 6) for b in arch})

    def test_an_entrance_has_a_portal_outside_and_an_architrave_inside(self):
        parts = [b["part"] for b in D.door_frame(3.0, 3.0, WALL_T, out="portal")]
        for part, n in (("plinth", 2), ("pilaster", 2), ("capital", 2), ("lintel", 1), ("downlight", 1), ("architrave", 3)):
            self.assertEqual(n, parts.count(part), part)
        light = next(b for b in D.door_frame(3.0, 3.0, WALL_T, out="portal") if b["part"] == "downlight")
        self.assertEqual("light_panel", light["mat"], "the lintel's downlight strip is the lit fixture (R5)")

    def test_plinths_clear_every_baseboard_height(self):
        self.assertNotIn(D.PORTAL["plinth"], BASEBOARDS_M)

    def test_frames_stay_in_their_triangle_budgets(self):
        for w, h in ((1.4, 2.4), (2.0, 2.4), (5.0, 3.0)):
            self.assertLessEqual(D.frame_triangles(D.door_frame(w, h, WALL_T)), 72, f"a liner and architrave, {w} m")
            self.assertLessEqual(D.frame_triangles(D.door_frame(w, h, WALL_T, out="portal")), 180, f"a portal, {w} m")

    def test_no_frame_z_fights_with_its_walls_or_itself(self):
        for w, h in ((1.4, 2.4), (2.0, 2.4), (3.0, 3.0), (4.0, 3.0)):
            for out in ("architrave", "portal"):
                report = D.zfight_report(airs_round(w, h), as_details(D.door_frame(w, h, WALL_T, out=out)))
                self.assertEqual([], report, f"{w} x {h} with a {out} outside")

    def test_a_frame_the_size_of_its_opening_is_caught(self):
        # The classic bug the rule prevents: a jamb flush with the opening's side, facing the same way.
        boxes = D.door_frame(1.4, 2.4, WALL_T)
        flush = as_details(boxes) + [((-0.8, 0, -0.05), (-0.7, 2.4, WALL_T + 0.05), "flush jamb")]
        self.assertTrue(D.zfight_report(airs_round(1.4, 2.4), flush), "a box sharing the liner's face must be reported")

    def test_an_unknown_frame_kind_is_refused(self):
        with self.assertRaises(ValueError):
            D.door_frame(1.4, 2.4, WALL_T, out="arch")


if __name__ == "__main__":
    unittest.main()
